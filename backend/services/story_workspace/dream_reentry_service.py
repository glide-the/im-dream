"""Actor-scoped durable projection for the Dream workbench re-entry list."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
import json
from typing import Any

try:
    from services.errors.error_registry import ApiRouteError
    from story_workspace.contracts import (
        STORY_WORKSPACE_DREAM_REQUIRED_STAGES,
        StoryWorkspaceDreamReentryCollection,
        StoryWorkspaceDreamReentryItem,
        StoryWorkspaceDreamRunLifecycle,
        StoryWorkspaceDreamStage,
    )
except ModuleNotFoundError:  # Support repository-root package imports.
    from backend.services.errors.error_registry import ApiRouteError
    from backend.story_workspace.contracts import (
        STORY_WORKSPACE_DREAM_REQUIRED_STAGES,
        StoryWorkspaceDreamReentryCollection,
        StoryWorkspaceDreamReentryItem,
        StoryWorkspaceDreamRunLifecycle,
        StoryWorkspaceDreamStage,
    )


_StoryWorkspaceDreamProjectionLoader = Callable[[Any, dict[str, str], Any], Any]
_StoryWorkspaceDreamLiveTurnLookup = Callable[[str], bool]
_STORY_WORKSPACE_DREAM_REENTRY_CONFIRMATION_BATCH_SIZE = 400
_STORY_WORKSPACE_DREAM_REENTRY_RECENT_LIMIT = 20
_STORY_WORKSPACE_DREAM_GOAL_PREFIX_MAX = 80
_STORY_WORKSPACE_DREAM_CONTEXT_REQUIRED_KEYS = frozenset({
    "workflow_run_id",
    "thread_id",
    "deck_id",
    "deck_plugin_id",
    "deck_plugin_version",
    "deck_plugin_binding_id",
    "binding_revision",
    "deck_runtime_snapshot_id",
    "runtime_plugin_lock_id",
})
_STORY_WORKSPACE_DREAM_CONTEXT_AGENT_KEY = "agent_id"
_STORY_WORKSPACE_DREAM_LAUNCH_SCHEMA = "story-workspace-dream-launch/v1"
_STORY_WORKSPACE_DREAM_LAUNCH_ALLOWED_KEYS = frozenset({
    "kind",
    "schemaVersion",
    "visibility",
    "actorId",
    "workspaceId",
    "deckId",
    "agentId",
    "goal",
    "idempotencyKey",
    "requestFingerprint",
    "dispatchStatus",
    "dispatchClaimId",
    "dispatchClaimedAt",
    "workflowRunId",
    "threadId",
    "dreamContext",
    "story_workspace_episode_identity",
})
_STORY_WORKSPACE_DREAM_AGENT_NOT_PROVIDED = object()


class StoryWorkspaceDreamReentryService:
    """Build the sole durable run discovery projection for Dream.

    The query deliberately verifies each provenance edge before producing a
    user-visible row.  A malformed source message or a broken Deck/thread
    relationship is omitted rather than exposed as a partially-authorized run.
    """

    def __init__(
        self,
        *,
        db_factory: Callable[[], Any],
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
        try:
            rows = self._query_authorized_rows(db, actor_id)
            confirmation_facts = self._confirmation_facts(db, rows, actor_id)
            items = [
                item
                for row in rows
                if (item := self._project_row(
                    db,
                    row,
                    actor_id,
                    confirmation_facts.get(str(row["run_id"]), (False, False)),
                )) is not None
            ]
            items.sort(key=self._sort_tuple)
            in_progress = [item for item in items if item.group == "in_progress"]
            recent = [item for item in items if item.group == "recent"]
            return StoryWorkspaceDreamReentryCollection(
                runs=in_progress + recent[:_STORY_WORKSPACE_DREAM_REENTRY_RECENT_LIMIT]
            )
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
        db: Any,
        actor_id: int,
        *,
        workflow_run_id: str | None = None,
        limit: int | None = None,
    ) -> list[Any]:
        """Select only DB-consistent candidates before file projection.

        Workflow run status is intentionally absent: legacy status is not a
        durable Dream lifecycle fact (DEC-034/035).
        """

        if limit is not None and (
            isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000
        ):
            raise ValueError("authorized Dream row limit is invalid")
        run_filter = "AND run.id = %s " if workflow_run_id is not None else ""
        limit_clause = " LIMIT %s" if limit is not None else ""
        parameters: list[Any] = [
            str(actor_id),
            actor_id,
            actor_id,
            actor_id,
            _STORY_WORKSPACE_DREAM_LAUNCH_SCHEMA,
        ]
        if workflow_run_id is not None:
            parameters.append(workflow_run_id)
        if limit is not None:
            parameters.append(limit)

        return db.execute(
            "SELECT "
            "run.*, run.id AS run_id, "
            "run.workspace_id, run.deck_plugin_id, "
            "run.deck_plugin_version, run.deck_plugin_binding_id AS binding_id, "
            "run.binding_revision, run.deck_runtime_snapshot_id, "
            "run.runtime_plugin_lock_id, "
            "run.source_voice_thread_id AS thread_id, "
            "run.source_message_id AS source_message_id, "
            "run.created_at AS run_created_at, "
            "deck.id AS deck_id, deck.name AS deck_name, "
            "thread.updated_at AS thread_updated_at, "
            "thread.voice_id AS thread_voice_id, source.metadata AS source_metadata "
            "FROM workflow_runs AS run "
            "JOIN story_workspace_workspaces AS workspace "
            "ON workspace.id = run.workspace_id "
            "JOIN workflow_preflights AS preflight "
            "ON preflight.workflow_preflight_id = run.workflow_preflight_id "
            "JOIN deck_plugin_bindings AS binding "
            "ON binding.deck_plugin_binding_id = run.deck_plugin_binding_id "
            "JOIN deck_plugin_releases AS release "
            "ON release.deck_plugin_id = run.deck_plugin_id "
            "AND release.deck_plugin_version = run.deck_plugin_version "
            "AND release.workflow_definition_ref = run.workflow_definition_ref "
            "AND release.manifest_hash = run.deck_plugin_manifest_hash "
            "AND ("
            "EXISTS (SELECT 1 FROM jsonb_array_elements("
            "COALESCE(release.manifest_json::jsonb -> 'surfaces', '[]'::jsonb)) AS surface(value) "
            "WHERE surface.value ->> 'name' = 'dream') "
            "OR EXISTS (SELECT 1 FROM jsonb_array_elements_text("
            "COALESCE(release.manifest_json::jsonb -> 'capabilities', '[]'::jsonb)) AS capability(value) "
            "WHERE capability.value = 'story.workspace.propose') "
            "OR EXISTS (SELECT 1 FROM jsonb_array_elements("
            "COALESCE(release.manifest_json::jsonb #> '{runtime,claude_code_plugins}', "
            "'[]'::jsonb)) AS plugin(value) "
            "CROSS JOIN LATERAL jsonb_array_elements_text("
            "COALESCE(plugin.value -> 'capability_bindings', '[]'::jsonb)) "
            "AS binding_capability(value) "
            "WHERE binding_capability.value = 'story.workspace.propose')"
            ") "
            "JOIN deck_runtime_plugin_locks AS runtime_lock "
            "ON runtime_lock.id = run.runtime_plugin_lock_id "
            "AND runtime_lock.deck_plugin_id = run.deck_plugin_id "
            "AND runtime_lock.deck_plugin_version = run.deck_plugin_version "
            "AND runtime_lock.deck_plugin_manifest_hash = run.deck_plugin_manifest_hash "
            "JOIN deck_runtime_snapshots AS runtime_snapshot "
            "ON runtime_snapshot.deck_runtime_snapshot_id = run.deck_runtime_snapshot_id "
            "AND runtime_snapshot.deck_id = binding.deck_id "
            "AND runtime_snapshot.deck_plugin_binding_id = binding.deck_plugin_binding_id "
            "AND runtime_snapshot.binding_revision = run.binding_revision "
            "JOIN decks AS deck ON deck.id = binding.deck_id "
            "JOIN chat_thread AS thread ON thread.id = run.source_voice_thread_id "
            "JOIN chat_message AS source "
            "ON source.id = run.source_message_id AND source.thread_id = thread.id "
            "WHERE run.created_by = %s "
            "AND workspace.owner_id = %s "
            "AND deck.owner_id = %s AND deck.enabled IS TRUE "
            "AND thread.user_id = %s AND thread.deck_id = binding.deck_id "
            "AND source.role = 'user' "
            "AND preflight.created_by = run.created_by "
            "AND preflight.deck_id = binding.deck_id "
            "AND preflight.binding_revision = run.binding_revision "
            "AND preflight.deck_plugin_id = run.deck_plugin_id "
            "AND preflight.deck_plugin_version = run.deck_plugin_version "
            "AND preflight.runtime_plugin_lock_id = run.runtime_plugin_lock_id "
            "AND preflight.deck_runtime_snapshot_id = run.deck_runtime_snapshot_id "
            "AND binding.workspace_id = run.workspace_id "
            "AND binding.creator_id = run.created_by "
            "AND binding.deck_plugin_id = run.deck_plugin_id "
            "AND binding.deck_plugin_version = run.deck_plugin_version "
            "AND binding.binding_revision = run.binding_revision "
            "AND ("
            "((COALESCE(NULLIF(BTRIM(source.metadata), ''), '{}')::jsonb ->> 'schemaVersion') IS NULL "
            "AND (COALESCE(NULLIF(BTRIM(source.metadata), ''), '{}')::jsonb ->> 'agentId') IS NULL "
            "AND (COALESCE(NULLIF(BTRIM(source.metadata), ''), '{}')::jsonb "
            "#>> '{dreamContext,agent_id}') IS NULL) "
            "OR ((COALESCE(NULLIF(BTRIM(source.metadata), ''), '{}')::jsonb "
            "->> 'schemaVersion') = %s "
            "AND (COALESCE(NULLIF(BTRIM(source.metadata), ''), '{}')::jsonb "
            "->> 'agentId') IS NOT DISTINCT FROM thread.voice_id "
            "AND (COALESCE(NULLIF(BTRIM(source.metadata), ''), '{}')::jsonb "
            "#>> '{dreamContext,agent_id}') IS NOT DISTINCT FROM thread.voice_id)) "
            + run_filter
            + "ORDER BY run.created_at DESC, run.id ASC"
            + limit_clause,
            tuple(parameters),
        ).fetchall()

    def _project_row(
        self,
        db: Any,
        row: Any,
        actor_id: int,
        confirmation_facts: tuple[bool, bool],
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
            thread_agent_id=row["thread_voice_id"],
            deck_id=deck_id,
            deck_plugin_id=str(row["deck_plugin_id"]),
            deck_plugin_version=str(row["deck_plugin_version"]),
            binding_id=str(row["binding_id"]),
            binding_revision=int(row["binding_revision"]),
            runtime_snapshot_id=str(row["deck_runtime_snapshot_id"]),
            runtime_lock_id=str(row["runtime_plugin_lock_id"]),
        ):
            return None

        confirmation_accepted, confirmation_dispatched = confirmation_facts
        stage_revisions, stage_activity_at = self._stage_snapshot(db, row, actor_id)
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
            stage_activity_at or datetime.min.replace(tzinfo=UTC),
        )
        created_at = self._parse_datetime(row["run_created_at"])
        group = "recent" if lifecycle is StoryWorkspaceDreamRunLifecycle.RECENT else "in_progress"
        deck_display_name = str(row["deck_name"] or deck_id)
        return StoryWorkspaceDreamReentryItem(
            story_workspace_run_id=run_id,
            goal_prefix=self._source_goal_prefix(
                row["source_metadata"],
                fallback=deck_display_name,
            ),
            deck_id=deck_id,
            deck_display_name=deck_display_name,
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

    def _stage_snapshot(
        self,
        db: Any,
        row: Any,
        actor_id: int,
    ) -> tuple[dict[StoryWorkspaceDreamStage, int], datetime | None]:
        """Read stage truth through the established Dream files adapter only."""

        try:
            projection = self._dream_files_loader(
                row,
                {"actor_id": str(actor_id)},
                db,
            )
        except FileNotFoundError:
            # A missing stage file is the only legal empty-stage condition.
            return {}, None
        stages = getattr(projection, "stages", {})
        if not isinstance(stages, dict):
            raise ApiRouteError("OUTPUT_CONTRACT_INVALID", status_code=422)
        revisions: dict[StoryWorkspaceDreamStage, int] = {}
        for stage in STORY_WORKSPACE_DREAM_REQUIRED_STAGES:
            value = stages.get(stage) or stages.get(stage.value)
            revision = getattr(value, "revision", None)
            if isinstance(revision, int) and not isinstance(revision, bool) and revision >= 0:
                revisions[stage] = revision
        stage_activity_at = getattr(projection, "stage_activity_at", None)
        if stage_activity_at is not None and not isinstance(stage_activity_at, datetime):
            raise ApiRouteError("OUTPUT_CONTRACT_INVALID", status_code=422)
        if isinstance(stage_activity_at, datetime) and stage_activity_at.tzinfo is None:
            stage_activity_at = stage_activity_at.replace(tzinfo=UTC)
        return revisions, stage_activity_at

    @staticmethod
    def _confirmation_facts(
        db: Any,
        rows: list[Any],
        actor_id: int,
    ) -> dict[str, tuple[bool, bool]]:
        """Read at most one durable confirmation per re-entry candidate.

        This is intentionally a single bounded batch query, rather than the
        unbounded per-run audit scan used by the confirmation coordinator.
        Duplicate matching facts are treated as a diagnostic error so a page
        never silently derives lifecycle from a truncated audit history.
        """

        if not rows:
            return {}
        by_thread = {str(row["thread_id"]): str(row["run_id"]) for row in rows}
        facts = {run_id: (False, False) for run_id in by_thread.values()}
        seen_threads: set[str] = set()
        thread_ids = list(by_thread)
        for start in range(0, len(thread_ids), _STORY_WORKSPACE_DREAM_REENTRY_CONFIRMATION_BATCH_SIZE):
            batch = thread_ids[start:start + _STORY_WORKSPACE_DREAM_REENTRY_CONFIRMATION_BATCH_SIZE]
            placeholders = ", ".join("%s" for _ in batch)
            matches = db.execute(
                "SELECT thread_id, metadata FROM chat_message "
                "WHERE role = 'user' AND thread_id IN (" + placeholders + ") "
                "AND (COALESCE(NULLIF(BTRIM(metadata), ''), '{}')::jsonb ->> 'kind') = %s "
                "ORDER BY thread_id ASC, created_at ASC, id ASC LIMIT %s",
                (*batch, "story-workspace-dream-confirmation", len(batch) + 1),
            ).fetchall()
            if len(matches) > len(batch):
                raise ApiRouteError("DECK_RUNTIME_CONFIG_UNAVAILABLE", status_code=503)
            for match in matches:
                thread_id = str(match["thread_id"])
                run_id = by_thread.get(thread_id)
                if run_id is None or thread_id in seen_threads:
                    raise ApiRouteError("DECK_RUNTIME_CONFIG_UNAVAILABLE", status_code=503)
                seen_threads.add(thread_id)
                try:
                    metadata = json.loads(match["metadata"])
                except (TypeError, ValueError) as exc:
                    raise ApiRouteError("DECK_RUNTIME_CONFIG_UNAVAILABLE", status_code=503) from exc
                valid = (
                    isinstance(metadata, dict)
                    and metadata.get("actor") == str(actor_id)
                    and metadata.get("thread_id") == thread_id
                    and metadata.get("story_workspace_run_id") == run_id
                )
                if not valid:
                    raise ApiRouteError("DECK_RUNTIME_CONFIG_UNAVAILABLE", status_code=503)
                facts[run_id] = (
                    True,
                    metadata.get("dispatch_status") == "dispatched",
                )
        return facts


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
        deck_plugin_id: str,
        deck_plugin_version: str,
        binding_id: str,
        binding_revision: int,
        runtime_snapshot_id: str,
        runtime_lock_id: str,
        thread_agent_id: Any = _STORY_WORKSPACE_DREAM_AGENT_NOT_PROVIDED,
    ) -> bool:
        try:
            metadata = json.loads(raw_metadata) if isinstance(raw_metadata, str) else {}
        except (TypeError, ValueError):
            return False
        if not isinstance(metadata, dict):
            return False
        if not set(metadata).issubset(_STORY_WORKSPACE_DREAM_LAUNCH_ALLOWED_KEYS):
            return False
        dream_context = metadata.get("dreamContext")
        if not isinstance(dream_context, dict):
            return False
        context_keys = set(dream_context)
        allowed_context_keys = (
            _STORY_WORKSPACE_DREAM_CONTEXT_REQUIRED_KEYS
            | {_STORY_WORKSPACE_DREAM_CONTEXT_AGENT_KEY}
        )
        if (
            not _STORY_WORKSPACE_DREAM_CONTEXT_REQUIRED_KEYS.issubset(context_keys)
            or not context_keys.issubset(allowed_context_keys)
        ):
            return False
        expected_context = {
            "workflow_run_id": run_id,
            "thread_id": thread_id,
            "deck_id": deck_id,
            "deck_plugin_id": deck_plugin_id,
            "deck_plugin_version": deck_plugin_version,
            "deck_plugin_binding_id": binding_id,
            "binding_revision": binding_revision,
            "deck_runtime_snapshot_id": runtime_snapshot_id,
            "runtime_plugin_lock_id": runtime_lock_id,
        }
        if any(dream_context.get(key) != value for key, value in expected_context.items()):
            return False
        top_agent_present = "agentId" in metadata
        context_agent_present = _STORY_WORKSPACE_DREAM_CONTEXT_AGENT_KEY in dream_context
        schema_present = "schemaVersion" in metadata
        if schema_present:
            if (
                metadata["schemaVersion"] != _STORY_WORKSPACE_DREAM_LAUNCH_SCHEMA
                or not top_agent_present
                or not context_agent_present
            ):
                return False
        elif top_agent_present or context_agent_present:
            return False
        if thread_agent_id is not _STORY_WORKSPACE_DREAM_AGENT_NOT_PROVIDED:
            if thread_agent_id is not None and (
                not isinstance(thread_agent_id, str) or not thread_agent_id
            ):
                return False
        if top_agent_present:
            top_agent = metadata["agentId"]
            context_agent = dream_context[_STORY_WORKSPACE_DREAM_CONTEXT_AGENT_KEY]
            if top_agent is not None and (
                not isinstance(top_agent, str)
                or not top_agent
                or top_agent != top_agent.strip()
            ):
                return False
            if top_agent != context_agent:
                return False
            if (
                thread_agent_id is not _STORY_WORKSPACE_DREAM_AGENT_NOT_PROVIDED
                and top_agent != thread_agent_id
            ):
                return False
        return (
            metadata.get("kind") == "story-workspace-dream-launch"
            and metadata.get("actorId") == str(actor_id)
            and metadata.get("workspaceId") == workspace_id
            and metadata.get("deckId") == deck_id
            and metadata.get("workflowRunId") == run_id
            and metadata.get("threadId") == thread_id
        )

    @staticmethod
    def _source_goal_prefix(raw_metadata: Any, *, fallback: str) -> str:
        try:
            metadata = json.loads(raw_metadata) if isinstance(raw_metadata, str) else {}
        except (TypeError, ValueError):
            metadata = {}
        goal = metadata.get("goal") if isinstance(metadata, dict) else None
        if (
            isinstance(goal, str)
            and goal == goal.strip()
            and 1 <= len(goal) <= 12000
        ):
            return goal[:_STORY_WORKSPACE_DREAM_GOAL_PREFIX_MAX]
        return fallback[:_STORY_WORKSPACE_DREAM_GOAL_PREFIX_MAX]

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
