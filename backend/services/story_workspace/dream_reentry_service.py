# [Input] Admin-authorized Story Workspace Artifact authority DTOs, Dream stage files, and live shared-thread status.
# [Output] Ordered re-entry rows with canonical titles and Dream's two-state initial/in-progress projection.
# [Pos] Pure Story Workspace Dream re-entry projector; Admin owns every relational query and permission join.
# [Sync] 2026-09-16: replace Dream SQL/title/confirmation reads with Registry185 authority DTOs.

"""Project Admin-authorized Story Workspace runs into the Dream re-entry list."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
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


_StoryWorkspaceDreamProjectionLoader = Callable[[Any], Any]
_StoryWorkspaceDreamLiveTurnLookup = Callable[[str], bool]
_STORY_WORKSPACE_DREAM_REENTRY_RECENT_LIMIT = 20
_STORY_WORKSPACE_DREAM_GOAL_PREFIX_MAX = 80


class StoryWorkspaceDreamReentryWorkspaceMissing(Exception):
    """One authorized historical Run no longer has its Thread workspace."""


class StoryWorkspaceDreamReentryService:
    """Build the durable list solely from Admin-authorized authority DTOs."""

    def __init__(
        self,
        *,
        dream_files_loader: _StoryWorkspaceDreamProjectionLoader,
        live_turn_lookup: _StoryWorkspaceDreamLiveTurnLookup | None = None,
    ) -> None:
        self._dream_files_loader = dream_files_loader
        self._live_turn_lookup = live_turn_lookup or self._default_live_turn_lookup

    def list_dream_runs(
        self,
        *,
        authorities: Sequence[Any],
    ) -> StoryWorkspaceDreamReentryCollection:
        items = [
            item
            for authority in authorities
            if (item := self._project_authority(authority)) is not None
        ]
        items.sort(key=self._sort_tuple)
        in_progress = [item for item in items if item.group == "in_progress"]
        recent = [item for item in items if item.group == "recent"]
        return StoryWorkspaceDreamReentryCollection(
            runs=in_progress + recent[:_STORY_WORKSPACE_DREAM_REENTRY_RECENT_LIMIT]
        )

    def _project_authority(self, authority: Any) -> StoryWorkspaceDreamReentryItem | None:
        try:
            workflow_run = authority.workflow_run()
            run_id = workflow_run.workflow_run_id
            thread_id = authority.thread_id
            if thread_id != workflow_run.source_voice_thread_id:
                raise ApiRouteError("OUTPUT_CONTRACT_INVALID", status_code=422)
            projection = self._dream_files_loader(authority)
            stages = getattr(projection, "stages", {})
            stage_activity_at = getattr(projection, "stage_activity_at", None)
        except StoryWorkspaceDreamReentryWorkspaceMissing:
            return None
        if not isinstance(stages, dict):
            raise ApiRouteError("OUTPUT_CONTRACT_INVALID", status_code=422)
        stage_revisions: dict[StoryWorkspaceDreamStage, int] = {}
        for stage in STORY_WORKSPACE_DREAM_REQUIRED_STAGES:
            value = stages.get(stage) or stages.get(stage.value)
            revision = getattr(value, "revision", None)
            if isinstance(revision, int) and not isinstance(revision, bool) and revision >= 0:
                stage_revisions[stage] = revision
        if stage_activity_at is not None and not isinstance(stage_activity_at, datetime):
            raise ApiRouteError("OUTPUT_CONTRACT_INVALID", status_code=422)
        if isinstance(stage_activity_at, datetime) and stage_activity_at.tzinfo is None:
            stage_activity_at = stage_activity_at.replace(tzinfo=UTC)

        lifecycle = self._lifecycle(
            stage_revisions=stage_revisions,
            confirmation_accepted=authority.confirmation_accepted,
            confirmation_dispatched=authority.confirmation_dispatched,
            live_turn=self._safe_live_turn_lookup(thread_id),
        )
        created_at = self._parse_datetime(workflow_run.created_at)
        last_activity_at = max(
            created_at,
            self._parse_datetime(authority.thread_updated_at),
            stage_activity_at or datetime.min.replace(tzinfo=UTC),
        )
        goal_prefix = authority.goal[:_STORY_WORKSPACE_DREAM_GOAL_PREFIX_MAX]
        group = (
            "recent"
            if lifecycle is StoryWorkspaceDreamRunLifecycle.RECENT
            else "in_progress"
        )
        outcome = (
            "initial"
            if lifecycle in {
                StoryWorkspaceDreamRunLifecycle.GENERATING,
                StoryWorkspaceDreamRunLifecycle.WAITING_CONFIRMATION,
            }
            else "in_progress"
        )
        return StoryWorkspaceDreamReentryItem(
            story_workspace_run_id=run_id,
            display_title=authority.project_title or goal_prefix,
            goal_prefix=goal_prefix,
            deck_id=authority.deck_id,
            deck_display_name=authority.deck_display_name,
            deck_plugin_version=workflow_run.deck_plugin_version,
            lifecycle=lifecycle,
            outcome=outcome,
            group=group,
            stage_revisions=stage_revisions,
            confirmation_accepted=authority.confirmation_accepted,
            confirmation_dispatched=authority.confirmation_dispatched,
            last_activity_at=last_activity_at,
            created_at=created_at,
            sort_key=(
                f"{self._group_rank(lifecycle):02d}:"
                f"{last_activity_at.isoformat()}:"
                f"{created_at.isoformat()}:{run_id}"
            ),
            href=(
                f"/story-workspace/runs/{run_id}/execution"
                if authority.confirmation_accepted
                else f"/story-workspace/dream?run={run_id}"
            ),
        )

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
            return StoryWorkspaceDreamRunLifecycle.RUNNING
        return StoryWorkspaceDreamRunLifecycle.RECENT

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
            StoryWorkspaceDreamRunLifecycle.RUNNING: 2,
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
            return False

    @staticmethod
    def _default_live_turn_lookup(thread_id: str) -> bool:
        try:
            from agent_factory import claude_agent_thread_factory

            snapshot = claude_agent_thread_factory.session_snapshot(thread_id)
            return bool(snapshot and snapshot.get("lifecycle") == "running")
        except Exception:
            return False


__all__ = [
    "StoryWorkspaceDreamReentryService",
    "StoryWorkspaceDreamReentryWorkspaceMissing",
]
