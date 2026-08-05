"""Actor-scoped durable projection for the Dream workbench re-entry list."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
import json
import sqlite3
from typing import Any

try:
    from services.errors.error_registry import ApiRouteError
    from services.story_workspace.dream_confirmation_service import (
        story_workspace_read_dream_confirmation_fact,
    )
    from story_workspace.contracts import (
        STORY_WORKSPACE_DREAM_REQUIRED_STAGES,
        StoryWorkspaceDreamReentryCollection,
        StoryWorkspaceDreamReentryItem,
        StoryWorkspaceDreamRunLifecycle,
        StoryWorkspaceDreamStage,
    )
except ModuleNotFoundError:  # Support repository-root package imports.
    from backend.services.errors.error_registry import ApiRouteError
    from backend.services.story_workspace.dream_confirmation_service import (
        story_workspace_read_dream_confirmation_fact,
    )
    from backend.story_workspace.contracts import (
        STORY_WORKSPACE_DREAM_REQUIRED_STAGES,
        StoryWorkspaceDreamReentryCollection,
        StoryWorkspaceDreamReentryItem,
        StoryWorkspaceDreamRunLifecycle,
        StoryWorkspaceDreamStage,
    )


_StoryWorkspaceDreamProjectionLoader = Callable[[str, dict[str, str]], Any]
_StoryWorkspaceDreamLiveTurnLookup = Callable[[str], bool]


class StoryWorkspaceDreamReentryService:
    """Build the sole durable run discovery projection for Dream.

    The query deliberately verifies each provenance edge before producing a
    user-visible row.  A malformed source message or a broken Deck/thread
    relationship is omitted rather than exposed as a partially-authorized run.
    """

    def __init__(
        self,
        *,
        db_factory: Callable[[], sqlite3.Connection],
        dream_files_loader: _StoryWorkspaceDreamProjectionLoader,
        live_turn_lookup: _StoryWorkspaceDreamLiveTurnLookup | None = None,
        close_connections: bool = True,
    ) -> None:
        self._db_factory = db_factory
        self._dream_files_loader = dream_files_loader
        self._live_turn_lookup = live_turn_lookup or self._default_live_turn_lookup
        self._close_connections = close_connections

    def list_dream_runs(
        self,
        *,
        actor: dict[str, str],
    ) -> StoryWorkspaceDreamReentryCollection:
        actor_id = self._actor_id(actor)
        db = self._db_factory()
        db.row_factory = sqlite3.Row
        try:
            rows = self._query_authorized_rows(db, actor_id)
            items = [
                item
                for row in rows
                if (item := self._project_row(db, row, actor_id)) is not None
            ]
            items.sort(key=self._sort_tuple)
            return StoryWorkspaceDreamReentryCollection(runs=items)
        finally:
            if self._close_connections:
                db.close()

    @staticmethod
    def _actor_id(actor: dict[str, str]) -> int:
        try:
            actor_id = int(actor["actor_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403) from exc
        if actor_id < 1:
            raise ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403)
        return actor_id

    @staticmethod
    def _query_authorized_rows(
        db: sqlite3.Connection,
        actor_id: int,
    ) -> list[sqlite3.Row]:
        """Select only DB-consistent candidates before file projection.

        Workflow run status is intentionally absent: legacy status is not a
        durable Dream lifecycle fact (DEC-034/035).
        """

        return db.execute(
            "SELECT "
            "run.id AS run_id, run.workspace_id, run.deck_plugin_version, "
            "run.source_voice_thread_id AS thread_id, "
            "run.source_message_id AS source_message_id, "
            "run.created_at AS run_created_at, "
            "deck.id AS deck_id, deck.name AS deck_name, "
            "thread.updated_at AS thread_updated_at, source.metadata AS source_metadata "
            "FROM workflow_runs AS run "
            "JOIN story_workspace_workspaces AS workspace "
            "ON workspace.id = run.workspace_id "
            "JOIN workflow_preflights AS preflight "
            "ON preflight.workflow_preflight_id = run.workflow_preflight_id "
            "JOIN deck_plugin_bindings AS binding "
            "ON binding.deck_plugin_binding_id = run.deck_plugin_binding_id "
            "JOIN decks AS deck ON deck.id = binding.deck_id "
            "JOIN chat_thread AS thread ON thread.id = run.source_voice_thread_id "
            "JOIN chat_message AS source "
            "ON source.id = run.source_message_id AND source.thread_id = thread.id "
            "WHERE run.created_by = ? "
            "AND workspace.owner_id = ? "
            "AND deck.owner_id = ? AND deck.enabled = 1 "
            "AND thread.user_id = ? AND thread.deck_id = binding.deck_id "
            "AND preflight.created_by = run.created_by "
            "AND preflight.deck_id = binding.deck_id "
            "AND preflight.deck_plugin_id = run.deck_plugin_id "
            "AND preflight.deck_plugin_version = run.deck_plugin_version "
            "AND preflight.runtime_plugin_lock_id = run.runtime_plugin_lock_id "
            "AND binding.workspace_id = run.workspace_id "
            "AND binding.creator_id = run.created_by "
            "AND binding.deck_plugin_id = run.deck_plugin_id "
            "AND binding.deck_plugin_version = run.deck_plugin_version "
            "AND binding.binding_revision = run.binding_revision",
            (str(actor_id), actor_id, actor_id, actor_id),
        ).fetchall()

    def _project_row(
        self,
        db: sqlite3.Connection,
        row: sqlite3.Row,
        actor_id: int,
    ) -> StoryWorkspaceDreamReentryItem | None:
        run_id = str(row["run_id"])
        thread_id = str(row["thread_id"])
        deck_id = str(row["deck_id"])
        if not self._source_metadata_matches(
            row["source_metadata"],
            actor_id=actor_id,
            workspace_id=str(row["workspace_id"]),
            run_id=run_id,
            thread_id=thread_id,
            deck_id=deck_id,
        ):
            return None

        confirmation_accepted, confirmation_dispatched = (
            story_workspace_read_dream_confirmation_fact(
                db,
                actor_id=str(actor_id),
                thread_id=thread_id,
                run_id=run_id,
            )
        )
        stage_revisions = self._stage_revisions(run_id, actor_id)
        live_turn = self._safe_live_turn_lookup(thread_id)
        lifecycle = self._lifecycle(
            stage_revisions=stage_revisions,
            confirmation_accepted=confirmation_accepted,
            confirmation_dispatched=confirmation_dispatched,
            live_turn=live_turn,
        )
        last_activity_at = max(
            self._parse_datetime(row["run_created_at"]),
            self._parse_datetime(row["thread_updated_at"]),
        )
        created_at = self._parse_datetime(row["run_created_at"])
        group = "recent" if lifecycle is StoryWorkspaceDreamRunLifecycle.RECENT else "in_progress"
        return StoryWorkspaceDreamReentryItem(
            story_workspace_run_id=run_id,
            deck_id=deck_id,
            deck_display_name=str(row["deck_name"] or deck_id),
            deck_plugin_version=str(row["deck_plugin_version"]),
            lifecycle=lifecycle,
            group=group,
            stage_revisions=stage_revisions,
            confirmation_accepted=confirmation_accepted,
            confirmation_dispatched=confirmation_dispatched,
            last_activity_at=last_activity_at,
            created_at=created_at,
            sort_key=(
                f"{self._group_rank(lifecycle):02d}:"
                f"{last_activity_at.isoformat()}:"
                f"{created_at.isoformat()}:{run_id}"
            ),
            href=f"/story-workspace/dream?run={run_id}",
        )

    def _stage_revisions(
        self,
        run_id: str,
        actor_id: int,
    ) -> dict[StoryWorkspaceDreamStage, int]:
        """Read stage truth through the established Dream files adapter only."""

        try:
            projection = self._dream_files_loader(run_id, {"actor_id": str(actor_id)})
        except ApiRouteError as exc:
            if exc.status_code in {403, 404}:
                return {}
            raise
        except Exception:
            # Runtime files can legitimately be absent immediately after launch.
            # The DB-provenanced run remains recoverable as ``generating``.
            return {}
        stages = getattr(projection, "stages", {})
        if not isinstance(stages, dict):
            return {}
        revisions: dict[StoryWorkspaceDreamStage, int] = {}
        for stage in STORY_WORKSPACE_DREAM_REQUIRED_STAGES:
            value = stages.get(stage) or stages.get(stage.value)
            revision = getattr(value, "revision", None)
            if isinstance(revision, int) and not isinstance(revision, bool) and revision >= 0:
                revisions[stage] = revision
        return revisions

    @staticmethod
    def _lifecycle(
        *,
        stage_revisions: dict[StoryWorkspaceDreamStage, int],
        confirmation_accepted: bool,
        confirmation_dispatched: bool,
        live_turn: bool,
    ) -> StoryWorkspaceDreamRunLifecycle:
        stages_complete = set(stage_revisions) == set(STORY_WORKSPACE_DREAM_REQUIRED_STAGES)
        if not confirmation_accepted and (not stages_complete or live_turn):
            return StoryWorkspaceDreamRunLifecycle.GENERATING
        if not confirmation_accepted:
            return StoryWorkspaceDreamRunLifecycle.WAITING_CONFIRMATION
        if not confirmation_dispatched or live_turn:
            return StoryWorkspaceDreamRunLifecycle.CONTINUING
        return StoryWorkspaceDreamRunLifecycle.RECENT

    @staticmethod
    def _source_metadata_matches(
        raw_metadata: Any,
        *,
        actor_id: int,
        workspace_id: str,
        run_id: str,
        thread_id: str,
        deck_id: str,
    ) -> bool:
        try:
            metadata = json.loads(raw_metadata) if isinstance(raw_metadata, str) else {}
        except (TypeError, ValueError):
            return False
        return (
            isinstance(metadata, dict)
            and metadata.get("kind") == "story-workspace-dream-launch"
            and metadata.get("actorId") == str(actor_id)
            and metadata.get("workspaceId") == workspace_id
            and metadata.get("deckId") == deck_id
            and metadata.get("workflowRunId") == run_id
            and metadata.get("threadId") == thread_id
        )

    @staticmethod
    def _parse_datetime(value: Any) -> datetime:
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                parsed = datetime.min.replace(tzinfo=UTC)
        else:
            parsed = datetime.min.replace(tzinfo=UTC)
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)

    @staticmethod
    def _group_rank(lifecycle: StoryWorkspaceDreamRunLifecycle) -> int:
        return {
            StoryWorkspaceDreamRunLifecycle.GENERATING: 0,
            StoryWorkspaceDreamRunLifecycle.WAITING_CONFIRMATION: 1,
            StoryWorkspaceDreamRunLifecycle.CONTINUING: 2,
            StoryWorkspaceDreamRunLifecycle.RECENT: 3,
        }[lifecycle]

    @classmethod
    def _sort_tuple(
        cls,
        item: StoryWorkspaceDreamReentryItem,
    ) -> tuple[int, float, float, str]:
        return (
            cls._group_rank(item.lifecycle),
            -item.last_activity_at.timestamp(),
            -item.created_at.timestamp(),
            item.story_workspace_run_id,
        )

    def _safe_live_turn_lookup(self, thread_id: str) -> bool:
        try:
            return bool(self._live_turn_lookup(thread_id))
        except Exception:
            # In-memory state is an enhancement only; durable facts stay valid
            # across a process restart or a thread-pool eviction.
            return False

    @staticmethod
    def _default_live_turn_lookup(thread_id: str) -> bool:
        try:
            from agent_factory import claude_agent_thread_factory

            snapshot = claude_agent_thread_factory.session_snapshot(thread_id)
            return bool(snapshot and snapshot.get("lifecycle") == "running")
        except Exception:
            return False


__all__ = ["StoryWorkspaceDreamReentryService"]
