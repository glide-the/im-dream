# [Input] Admin-authorized Registry185 authority DTOs, validated Dream stage projections and live-turn hints.
# [Output] Stable re-entry lifecycle, ordering, title, truncation and missing-workspace assertions.
# [Pos] Pure Dream re-entry projector test; relational authorization belongs to Admin service tests.
# [Sync] 2026-09-16: replace the retired Dream SQLite/SQL fixture with strict Admin DTO fixtures.
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from services.admin_data.story_workspace_artifact_data import (
    StoryWorkspaceArtifactAuthorityDTO,
)
from services.errors.error_registry import ApiRouteError
from services.story_workspace.dream_reentry_service import (
    StoryWorkspaceDreamReentryService,
    StoryWorkspaceDreamReentryWorkspaceMissing,
)
from story_workspace.contracts import StoryWorkspaceDreamStage


ACTOR = "42"
BASE = datetime(2026, 9, 16, tzinfo=UTC)
HASH = "sha256:" + "a" * 64


def authority(
    number: int,
    *,
    accepted: bool = False,
    dispatched: bool = False,
    project_title: str | None = None,
    created_at: datetime | None = None,
) -> StoryWorkspaceArtifactAuthorityDTO:
    created = created_at or BASE + timedelta(minutes=number)
    run_id = f"run_{number:032x}"
    thread_id = f"thread-{number}"
    return StoryWorkspaceArtifactAuthorityDTO.model_validate({
        "run": {
            "workflow_run_id": run_id,
            "deck_plugin_id": "plugin",
            "deck_plugin_version": "1.0.0",
            "workflow_definition_ref": "flow",
            "deck_runtime_snapshot_id": "snapshot",
            "status": "queued",
            "failed_step": None,
            "error_code": None,
            "retry_of_run_id": None,
            "deck_plugin_manifest_hash": HASH,
            "deck_plugin_binding_id": "binding",
            "binding_revision": 1,
            "runtime_plugin_lock_id": "lock",
            "runtime_load_receipt_id": None,
            "workflow_preflight_id": "pf_" + f"{number:032x}",
            "agent_session_id": None,
            "source_voice_thread_id": thread_id,
            "source_message_id": f"message-{number}",
            "source_message_time": created.isoformat(),
            "workspace_id": "workspace",
            "idempotency_key": f"launch-{number}",
            "input_hash": HASH,
            "semantic_fingerprint": HASH,
            "status_version": 1,
            "created_by": ACTOR,
            "created_at": created.isoformat(),
            "started_at": None,
            "completed_at": None,
        },
        "thread_id": thread_id,
        "thread_updated_at": (created + timedelta(seconds=30)).isoformat(),
        "deck_id": "deck",
        "deck_display_name": "Dream Deck",
        "launch_agent_id": "voice",
        "goal": f"Write story {number}",
        "project_story_slug": f"project-{number}",
        "episode_authority": None,
        "project_title": project_title,
        "confirmation_accepted": accepted,
        "confirmation_dispatched": dispatched,
    })


def stage_projection(*, complete: bool, activity: datetime | None = None):
    stages = {}
    if complete:
        stages = {
            stage: SimpleNamespace(revision=index)
            for index, stage in enumerate(StoryWorkspaceDreamStage, start=1)
        }
    return SimpleNamespace(stages=stages, stage_activity_at=activity)


def test_projects_lifecycle_title_href_and_live_turn_without_database() -> None:
    values = [
        authority(1),
        authority(2, project_title="Canonical Project"),
        authority(3, accepted=True),
        authority(4, accepted=True, dispatched=True),
    ]
    projections = {
        values[0].thread_id: stage_projection(complete=False),
        values[1].thread_id: stage_projection(complete=True),
        values[2].thread_id: stage_projection(complete=True),
        values[3].thread_id: stage_projection(complete=True),
    }
    service = StoryWorkspaceDreamReentryService(
        dream_files_loader=lambda item: projections[item.thread_id],
        live_turn_lookup=lambda thread_id: thread_id == values[3].thread_id,
    )
    result = service.list_dream_runs(authorities=values)
    by_id = {item.story_workspace_run_id: item for item in result.runs}
    assert by_id[values[0].run.workflow_run_id].lifecycle.value == "generating"
    assert by_id[values[1].run.workflow_run_id].lifecycle.value == "waiting_confirmation"
    assert by_id[values[2].run.workflow_run_id].lifecycle.value == "running"
    assert by_id[values[3].run.workflow_run_id].lifecycle.value == "running"
    assert by_id[values[1].run.workflow_run_id].display_title == "Canonical Project"
    assert by_id[values[2].run.workflow_run_id].href.endswith("/execution")


def test_keeps_all_in_progress_and_only_twenty_recent() -> None:
    in_progress = authority(1)
    recent = [authority(index, accepted=True, dispatched=True) for index in range(2, 32)]
    service = StoryWorkspaceDreamReentryService(
        dream_files_loader=lambda _item: stage_projection(complete=True),
        live_turn_lookup=lambda _thread_id: False,
    )
    result = service.list_dream_runs(authorities=[in_progress, *recent])
    assert len(result.runs) == 21
    assert result.runs[0].story_workspace_run_id == in_progress.run.workflow_run_id
    assert all(item.group == "recent" for item in result.runs[1:])
    assert result.runs[1].created_at > result.runs[-1].created_at


def test_stage_activity_participates_in_stable_sort() -> None:
    older = authority(10, accepted=True)
    newer = authority(11, accepted=True)
    service = StoryWorkspaceDreamReentryService(
        dream_files_loader=lambda item: stage_projection(
            complete=True,
            activity=(BASE + timedelta(days=1)) if item is older else None,
        ),
        live_turn_lookup=lambda _thread_id: False,
    )
    result = service.list_dream_runs(authorities=[newer, older])
    assert [item.story_workspace_run_id for item in result.runs] == [
        older.run.workflow_run_id,
        newer.run.workflow_run_id,
    ]


def test_missing_historical_workspace_is_omitted_without_hiding_other_runs() -> None:
    missing = authority(1)
    visible = authority(2)

    def loader(item):
        if item is missing:
            raise StoryWorkspaceDreamReentryWorkspaceMissing(item.thread_id)
        return stage_projection(complete=False)

    result = StoryWorkspaceDreamReentryService(
        dream_files_loader=loader,
    ).list_dream_runs(authorities=[missing, visible])
    assert [item.story_workspace_run_id for item in result.runs] == [
        visible.run.workflow_run_id
    ]


def test_contract_and_permission_errors_remain_fail_closed() -> None:
    item = authority(1)
    for error in [
        ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403),
        ApiRouteError("OUTPUT_CONTRACT_INVALID", status_code=422),
    ]:
        service = StoryWorkspaceDreamReentryService(
            dream_files_loader=lambda _item, error=error: (_ for _ in ()).throw(error)
        )
        with pytest.raises(ApiRouteError) as raised:
            service.list_dream_runs(authorities=[item])
        assert raised.value.code == error.code
