# [Input] Registry186 authority DTO, authenticated OAuth actor, validated Dream file projections and observer hints.
# [Output] Public route wiring, authority-first filesystem access, confirmation merge and safe failure assertions.
# [Pos] Dream Artifact application test; Admin tests own relational authorization and transactions.
# [Sync] 2026-09-16: replace retired Dream SQL fixtures with a strict Admin authority fake.
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from routers import story_workspace
from services.admin_data.story_workspace_artifact_data import (
    StoryWorkspaceArtifactAuthorityDTO,
)
from services.admin_data.request_auth import AdminRequestActor
from services.deck.story_workflow_application import DreamArtifactApplicationService
from services.errors.error_registry import ApiRouteError
from services.story_workspace.dream_file_service import (
    StoryWorkspaceDreamContractError,
    StoryWorkspaceDreamDurabilityIndeterminate,
    StoryWorkspaceDreamFileError,
    StoryWorkspaceDreamIOError,
    StoryWorkspaceDreamPathError,
    StoryWorkspaceDreamPlatformUnsupported,
)
from story_workspace.contracts import (
    StoryWorkspaceDreamFilesResponse,
    StoryWorkspaceDreamSourceResponse,
    StoryWorkspaceDreamStage,
    StoryWorkspaceDreamStageResponse,
)


RUN_ID = "run_0123456789abcdef0123456789abcdef"
THREAD_ID = "thread-1"
ACTOR_ID = "7"
HASH = "sha256:" + "1" * 64
REQUEST_ACTOR = AdminRequestActor(
    subject="subject-7",
    canonical_user_id=ACTOR_ID,
    client_id="dream-browser",
    scopes=frozenset({"dream:read", "dream:write"}),
    issued_at=1,
    expires_at=2,
    access_token="oauth-access-token",
)


def authority(*, actor_id: str = ACTOR_ID, status: str = "queued",
              accepted: bool = False, dispatched: bool = False):
    started = status not in {"preflight", "queued"}
    terminal = status in {"rejected", "completed", "failed", "cancelled"}
    return StoryWorkspaceArtifactAuthorityDTO.model_validate({
        "run": {
            "workflow_run_id": RUN_ID,
            "deck_plugin_id": "plugin-1",
            "deck_plugin_version": "1.2.3",
            "workflow_definition_ref": "workflow-1",
            "deck_runtime_snapshot_id": "snapshot-1",
            "status": status,
            "failed_step": "runtime" if status == "failed" else None,
            "error_code": "AGENT_FAILED" if status == "failed" else None,
            "retry_of_run_id": None,
            "deck_plugin_manifest_hash": HASH,
            "deck_plugin_binding_id": "binding-1",
            "binding_revision": 3,
            "runtime_plugin_lock_id": "lock-1",
            "runtime_load_receipt_id": "receipt-1" if started else None,
            "workflow_preflight_id": "pf_" + "2" * 32,
            "agent_session_id": "as_" + "3" * 32 if started else None,
            "source_voice_thread_id": THREAD_ID,
            "source_message_id": "message-1",
            "source_message_time": "2026-09-16T00:00:00+00:00",
            "workspace_id": "workspace-1",
            "idempotency_key": "launch-1",
            "input_hash": HASH,
            "semantic_fingerprint": HASH,
            "status_version": 1,
            "created_by": actor_id,
            "created_at": "2026-09-16T00:00:00+00:00",
            "started_at": "2026-09-16T00:00:01+00:00" if started else None,
            "completed_at": "2026-09-16T00:00:02+00:00" if terminal else None,
        },
        "thread_id": THREAD_ID,
        "thread_updated_at": "2026-09-16T00:01:00+00:00",
        "deck_id": "deck-1",
        "deck_display_name": "Dream Deck",
        "launch_agent_id": "voice-1",
        "goal": "Write a story",
        "project_story_slug": "project-one",
        "episode_authority": None,
        "project_title": None,
        "confirmation_accepted": accepted,
        "confirmation_dispatched": dispatched,
    })


def waiting_response() -> StoryWorkspaceDreamFilesResponse:
    return StoryWorkspaceDreamFilesResponse(
        story_workspace_run_id=RUN_ID,
        thread_id=THREAD_ID,
        source=StoryWorkspaceDreamSourceResponse(
            deck_plugin_binding_id="binding-1",
            binding_revision=3,
            deck_plugin_version="1.2.3",
            deck_runtime_snapshot_id="snapshot-1",
            runtime_plugin_lock_id="lock-1",
        ),
        required_stages=list(StoryWorkspaceDreamStage),
        run_revision=0,
        stages={},
        can_confirm=False,
    )


def complete_response() -> StoryWorkspaceDreamFilesResponse:
    sources = {
        StoryWorkspaceDreamStage.CHARACTERS: "assets/characters/lead.md",
        StoryWorkspaceDreamStage.SCENES: "assets/scenes/opening.md",
        StoryWorkspaceDreamStage.STORYBOARDS: "stories/demo/episodes/EP01/storyboard.yaml",
    }
    titles = {
        StoryWorkspaceDreamStage.CHARACTERS: "人物",
        StoryWorkspaceDreamStage.SCENES: "场景",
        StoryWorkspaceDreamStage.STORYBOARDS: "分镜",
    }
    stages = {
        stage: StoryWorkspaceDreamStageResponse(
            stage=stage,
            revision=index,
            source_files=[sources[stage]],
            page={
                "title": titles[stage],
                "entry_route": (
                    f"/story-workspace/characters?run={RUN_ID}"
                    if stage is StoryWorkspaceDreamStage.CHARACTERS
                    else f"/story-workspace/scenes?run={RUN_ID}"
                    if stage is StoryWorkspaceDreamStage.SCENES
                    else f"/story-workspace/runs/{RUN_ID}/execution"
                ),
            },
            items=[{
                "entity_id": f"entity-{index}",
                "display_name": f"Entity {index}",
                "summary": "summary",
                "source_file": sources[stage],
                "relations": [],
            }],
        )
        for index, stage in enumerate(StoryWorkspaceDreamStage, start=1)
    }
    return StoryWorkspaceDreamFilesResponse(
        story_workspace_run_id=RUN_ID,
        thread_id=THREAD_ID,
        source=waiting_response().source,
        required_stages=list(StoryWorkspaceDreamStage),
        run_revision=1,
        stages=stages,
        can_confirm=True,
    )


class ArtifactDataFake:
    def __init__(self, value=None):
        self.value = value or authority()
        self.calls = []

    def authority(self, input_dto, request_id, *, access_token):
        self.calls.append((input_dto, request_id, access_token))
        return SimpleNamespace(authority=self.value)


@pytest.mark.asyncio
async def test_route_passes_authenticated_actor_oauth_and_artifact_client() -> None:
    calls = []

    class Gateway:
        async def get_dream_files(self, workflow_run_id, **kwargs):
            calls.append((workflow_run_id, kwargs))
            return waiting_response()

    data = object()
    result = await story_workspace.story_workspace_get_workflow_run_dream_files(
        RUN_ID,
        current_user={"user_id": int(ACTOR_ID), "_admin_actor": REQUEST_ACTOR},
        service=Gateway(),
        artifact_data=data,
    )
    assert result["storyWorkspaceRunId"] == RUN_ID
    assert calls == [(RUN_ID, {
        "actor": {"actor_id": ACTOR_ID},
        "artifact_data": data,
        "access_token": REQUEST_ACTOR.access_token,
    })]


@pytest.mark.asyncio
async def test_authority_is_checked_before_any_workspace_probe() -> None:
    gateway = DreamArtifactApplicationService()
    data = ArtifactDataFake(authority(actor_id="8"))
    with patch.object(
        gateway,
        "_read_dream_files_for_authorized_run",
        side_effect=AssertionError("unauthorized filesystem probe"),
    ) as reader:
        with pytest.raises(ApiRouteError) as raised:
            await gateway.get_dream_files(
                RUN_ID,
                actor={"actor_id": ACTOR_ID},
                artifact_data=data,
                access_token="oauth",
            )
    assert raised.value.code == "WORKFLOW_PERMISSION_DENIED"
    reader.assert_not_called()


@pytest.mark.asyncio
async def test_complete_projection_merges_admin_confirmation_fact() -> None:
    gateway = DreamArtifactApplicationService()
    data = ArtifactDataFake(authority(accepted=True, dispatched=True))
    with patch.object(
        gateway,
        "_read_dream_files_for_authorized_run",
        return_value=complete_response(),
    ):
        result = await gateway.get_dream_files(
            RUN_ID,
            actor={"actor_id": ACTOR_ID},
            artifact_data=data,
            access_token="oauth",
        )
    assert result.confirmation_accepted is True
    assert result.confirmation_dispatched is True
    assert result.can_confirm is False


@pytest.mark.asyncio
async def test_missing_workspace_is_waiting_only_before_output_required() -> None:
    gateway = DreamArtifactApplicationService()
    missing = ApiRouteError("AGENT_EXECUTION_FAILED", status_code=404)
    with patch.object(
        gateway,
        "_read_dream_files_for_authorized_run",
        side_effect=missing,
    ):
        result = await gateway.get_dream_files(
            RUN_ID,
            actor={"actor_id": ACTOR_ID},
            artifact_data=ArtifactDataFake(authority(status="queued")),
            access_token="oauth",
        )
        assert result.run_revision == 0
        with pytest.raises(ApiRouteError) as raised:
            await gateway.get_dream_files(
                RUN_ID,
                actor={"actor_id": ACTOR_ID},
                artifact_data=ArtifactDataFake(authority(status="completed")),
                access_token="oauth",
            )
    assert raised.value.code == "AGENT_EXECUTION_FAILED"


@pytest.mark.parametrize(
    ("error", "code", "status"),
    [
        (StoryWorkspaceDreamContractError("bad"), "OUTPUT_CONTRACT_INVALID", 422),
        (StoryWorkspaceDreamPathError("bad"), "WORKFLOW_PERMISSION_DENIED", 403),
        (StoryWorkspaceDreamDurabilityIndeterminate(1, "bad"), "RESULT_COMMIT_FAILED", 409),
        (StoryWorkspaceDreamIOError("bad"), "DECK_RUNTIME_CONFIG_UNAVAILABLE", 503),
        (StoryWorkspaceDreamPlatformUnsupported("bad"), "AGENT_EXECUTION_FAILED", 501),
        (StoryWorkspaceDreamFileError("bad"), "AGENT_EXECUTION_FAILED", 422),
    ],
)
def test_reader_errors_keep_allowlisted_public_mappings(error, code, status) -> None:
    with pytest.raises(ApiRouteError) as raised:
        DreamArtifactApplicationService._raise_dream_file_error(error)
    assert (raised.value.code, raised.value.status_code) == (code, status)


def test_observer_hint_is_scoped_and_optional() -> None:
    gateway = DreamArtifactApplicationService()
    projection = waiting_response()
    matching = SimpleNamespace(
        run_id=RUN_ID,
        thread_id=THREAD_ID,
        actor_id=ACTOR_ID,
        generation=1,
        sequence=2,
        activity="activity_started_hint",
        terminal_outcome=None,
        needs_reconcile=False,
        operation_scope="content_generation",
        operation_state="started",
        operation_id="a" * 64,
    )
    factory = SimpleNamespace(dream_workflow_activity_projection=lambda: [matching])
    with patch.object(gateway, "_dream_agent_thread_factory", return_value=factory):
        result = gateway._attach_dream_agent_activity(
            projection,
            workflow_run_id=RUN_ID,
            actor_id=ACTOR_ID,
        )
    assert result.agent_activity is not None
    assert result.agent_activity.sequence == 2

    failing = Mock()
    failing.dream_workflow_activity_projection.side_effect = RuntimeError("observer")
    with patch.object(gateway, "_dream_agent_thread_factory", return_value=failing):
        assert gateway._attach_dream_agent_activity(
            projection,
            workflow_run_id=RUN_ID,
            actor_id=ACTOR_ID,
        ).agent_activity is None
