# [Input] Registry120 DTO fakes, immutable Workflow Run facts and shared-file projections.
# [Output] Provider-free proof for validation, Admin handoff and same-Thread delivery recovery.
# [Pos] Deterministic confirmation contract/application/coordinator test stage; no database fixture.
# [Sync] 2026-09-16: replace legacy SQLite/SQL tests with Admin DTO boundary coverage.
"""Focused tests for the Admin-owned Dream confirmation state machine."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from claude_agent.service import ClaudeAgentRunRequest
from models.workflow_run import RunStatus, WorkflowRun
from services.admin_data.story_workspace_confirmation_data import (
    StoryWorkspaceConfirmationAckOutputDTO,
    StoryWorkspaceConfirmationClaimOutputDTO,
    StoryWorkspaceConfirmationDispatchDTO,
    StoryWorkspaceConfirmationLeaseOutputDTO,
    StoryWorkspaceConfirmationSubmitOutputDTO,
)
from services.deck.story_workflow_application import DreamConfirmationApplicationService
import services.story_workspace.dream_confirmation_service as confirmation_module
from services.story_workspace.dream_confirmation_service import (
    StoryWorkspaceDreamConfirmationCoordinator,
    StoryWorkspaceDreamConfirmationDispatch,
    StoryWorkspaceDreamConfirmationError,
    story_workspace_build_dream_confirmation_turn_dispatcher,
    story_workspace_confirmation_command_json,
    story_workspace_dream_confirmation_message_id,
    story_workspace_validate_confirmation_projection,
)
from story_workspace.contracts import (
    StoryWorkspaceDreamConfirmationCommand,
    StoryWorkspaceDreamFilesResponse,
    StoryWorkspaceDreamSourceResponse,
    StoryWorkspaceDreamStage,
    StoryWorkspaceDreamStageResponse,
)


RUN_ID = "run_" + "a" * 32
THREAD_ID = "thread-dream-confirmation"
WORKSPACE_ID = "workspace-dream-confirmation"
ACTOR_ID = "41"
REQUEST_ID = "request-confirmation-1"
CLAIM_ID = "claim-confirmation-1"
NOW = datetime(2026, 8, 4, 12, 0, tzinfo=UTC)


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":"), sort_keys=True)


def make_run() -> WorkflowRun:
    return WorkflowRun(
        workflow_run_id=RUN_ID,
        deck_plugin_id="ink.dream.story-workflow",
        deck_plugin_version="1.0.0",
        workflow_definition_ref="deck://ink.dream/workflow.json",
        deck_runtime_snapshot_id="drs_" + "5" * 32,
        status=RunStatus.RUNNING,
        deck_plugin_manifest_hash="sha256:" + "c" * 64,
        deck_plugin_binding_id="dpb_" + "2" * 32,
        binding_revision=1,
        runtime_plugin_lock_id="rpl_" + "1" * 32,
        runtime_load_receipt_id="rlr_" + "4" * 32,
        workflow_preflight_id="pf_" + "3" * 32,
        agent_session_id="as_" + "6" * 32,
        workspace_id=WORKSPACE_ID,
        idempotency_key="run-key",
        input_hash="sha256:" + "d" * 64,
        semantic_fingerprint="sha256:" + "e" * 64,
        status_version=2,
        created_by=ACTOR_ID,
        created_at=NOW,
        started_at=NOW,
        source_voice_thread_id=THREAD_ID,
    )


def complete_projection(
    *, revisions: tuple[int, int, int] = (2, 3, 4)
) -> StoryWorkspaceDreamFilesResponse:
    source_files = {
        StoryWorkspaceDreamStage.CHARACTERS: "assets/characters/lead.md",
        StoryWorkspaceDreamStage.SCENES: "assets/scenes/opening.md",
        StoryWorkspaceDreamStage.STORYBOARDS: "stories/demo/episodes/EP01/storyboard.yaml",
    }
    titles = {
        StoryWorkspaceDreamStage.CHARACTERS: "人物",
        StoryWorkspaceDreamStage.SCENES: "场景",
        StoryWorkspaceDreamStage.STORYBOARDS: "分镜",
    }
    routes = {
        StoryWorkspaceDreamStage.CHARACTERS: f"/story-workspace/characters?run={RUN_ID}",
        StoryWorkspaceDreamStage.SCENES: f"/story-workspace/scenes?run={RUN_ID}",
        StoryWorkspaceDreamStage.STORYBOARDS: f"/story-workspace/runs/{RUN_ID}/execution",
    }
    stages = {}
    for stage, revision in zip(StoryWorkspaceDreamStage, revisions):
        stages[stage] = StoryWorkspaceDreamStageResponse(
            stage=stage,
            revision=revision,
            source_files=[source_files[stage]],
            page={"title": titles[stage], "entry_route": routes[stage]},
            items=[{
                "entity_id": f"{stage.value}-entity",
                "display_name": stage.value,
                "summary": "summary",
                "source_file": source_files[stage],
                "relations": [],
            }],
        )
    return StoryWorkspaceDreamFilesResponse(
        story_workspace_run_id=RUN_ID,
        thread_id=THREAD_ID,
        source=StoryWorkspaceDreamSourceResponse(
            deck_plugin_binding_id="dpb_" + "2" * 32,
            binding_revision=1,
            deck_plugin_version="1.0.0",
            deck_runtime_snapshot_id="drs_" + "5" * 32,
            runtime_plugin_lock_id="rpl_" + "1" * 32,
        ),
        required_stages=list(StoryWorkspaceDreamStage),
        run_revision=1,
        stages=stages,
        can_confirm=True,
    )


def command(**overrides: object) -> StoryWorkspaceDreamConfirmationCommand:
    body: dict[str, object] = {
        "storyWorkspaceRunId": RUN_ID,
        "threadId": THREAD_ID,
        "baseRevisions": {"characters": 2, "scenes": 3, "storyboards": 4},
        "edits": [{
            "stage": "characters",
            "entityId": "characters-entity",
            "fields": {
                "displayName": "新主角",
                "summary": None,
                "relations": ["scenes-entity"],
            },
        }],
        "idempotencyKey": "swc_test-key",
    }
    body.update(overrides)
    return StoryWorkspaceDreamConfirmationCommand.model_validate(body)


def claimed_dispatch() -> StoryWorkspaceConfirmationDispatchDTO:
    payload = command()
    command_value = payload.model_dump(mode="json", by_alias=True)
    fingerprint = "sha256:" + hashlib.sha256(
        canonical({"actor": ACTOR_ID, "command": command_value}).encode()
    ).hexdigest()
    metadata = {
        "kind": "story-workspace-dream-confirmation",
        "actor": ACTOR_ID,
        "story_workspace_run_id": RUN_ID,
        "thread_id": THREAD_ID,
        "base_revisions": {"characters": 2, "scenes": 3, "storyboards": 4},
        "edit_count": 1,
        "command_fingerprint": fingerprint,
        "idempotency_key": "swc_test-key",
        "request_id": REQUEST_ID,
        "dispatch_status": "dispatching",
        "dispatch_claim_id": CLAIM_ID,
        "dispatch_claim_lease_until": 100.0,
    }
    return StoryWorkspaceConfirmationDispatchDTO(
        thread_id=THREAD_ID,
        actor_id=ACTOR_ID,
        message_id=story_workspace_dream_confirmation_message_id(
            ACTOR_ID, RUN_ID, "swc_test-key"
        ),
        parts_json=canonical([{"type": "text", "text": canonical({
            "kind": "story-workspace-dream-confirmation",
            "instruction": "continue",
            "command": command_value,
        })}]),
        metadata_json=canonical(metadata),
    )


def test_projection_requires_exact_revisions_and_scoped_edit_entities() -> None:
    story_workspace_validate_confirmation_projection(complete_projection(), command())
    with pytest.raises(StoryWorkspaceDreamConfirmationError) as drift:
        story_workspace_validate_confirmation_projection(
            complete_projection(revisions=(3, 3, 4)), command()
        )
    assert (drift.value.code, drift.value.status_code) == ("CONFIG_VERSION_DRIFT", 409)
    with pytest.raises(StoryWorkspaceDreamConfirmationError) as invalid:
        story_workspace_validate_confirmation_projection(
            complete_projection(),
            command(edits=[{
                "stage": "characters", "entityId": "missing-entity",
                "fields": {"displayName": "unknown"},
            }]),
        )
    assert (invalid.value.code, invalid.value.status_code) == (
        "OUTPUT_CONTRACT_INVALID", 422
    )


def test_command_json_is_canonical_and_lossless_for_admin_transport() -> None:
    value = story_workspace_confirmation_command_json(command())
    assert value == canonical(json.loads(value))
    assert json.loads(value)["baseRevisions"]["characters"] == 2
    assert "新主角" in value


class RecordingWorker:
    def __init__(self, dispatch: StoryWorkspaceConfirmationDispatchDTO) -> None:
        self.dispatch = dispatch
        self.claims = []
        self.leases = []
        self.acks = []

    def claim(self, input_dto, request_id):
        self.claims.append((input_dto, request_id))
        return StoryWorkspaceConfirmationClaimOutputDTO(dispatch=self.dispatch)

    def lease(self, input_dto, request_id):
        self.leases.append((input_dto, request_id))
        return StoryWorkspaceConfirmationLeaseOutputDTO(
            renewed=True, lease_until=200.0
        )

    def ack(self, input_dto, request_id):
        self.acks.append((input_dto, request_id))
        return StoryWorkspaceConfirmationAckOutputDTO(acked=True)


@pytest.mark.asyncio
async def test_coordinator_claims_exact_message_and_acks_after_runtime_completion() -> None:
    raw_dispatch = claimed_dispatch()
    worker = RecordingWorker(raw_dispatch)
    delivered = []

    def dispatcher_factory():
        async def dispatch(thread_id, actor_id, message_id, parts, metadata):
            delivered.append((thread_id, actor_id, message_id, parts, metadata))
            return True
        return dispatch

    coordinator = StoryWorkspaceDreamConfirmationCoordinator(
        worker,
        dispatcher_factory=dispatcher_factory,
        lease_renew_interval_s=60,
        claim_id_factory=lambda: CLAIM_ID,
        request_id_factory=lambda: REQUEST_ID,
    )
    assert coordinator.schedule(
        StoryWorkspaceDreamConfirmationDispatch.from_admin(raw_dispatch)
    )
    await coordinator.wait_for_idle()
    assert worker.claims[0][0].message_id == raw_dispatch.message_id
    assert worker.claims[0][0].claim_id == CLAIM_ID
    assert delivered[0][:3] == (THREAD_ID, ACTOR_ID, raw_dispatch.message_id)
    assert worker.acks[0][0].claim_id == CLAIM_ID


@pytest.mark.asyncio
async def test_dispatcher_marks_admin_persisted_user_turn_without_rewriting_it() -> None:
    created = []

    def request_factory(**kwargs):
        created.append(kwargs)
        return ClaudeAgentRunRequest(**kwargs)

    async def drain(_factory, request):
        assert request.user_message_pre_persisted is True
        return SimpleNamespace(completed=True)

    dispatcher = story_workspace_build_dream_confirmation_turn_dispatcher(
        factory=object(), request_factory=request_factory
    )
    parsed = StoryWorkspaceDreamConfirmationDispatch.from_admin(claimed_dispatch())
    with patch.object(confirmation_module, "drain_chat_agent_turn", drain):
        assert await dispatcher(
            parsed.thread_id, parsed.actor_id, parsed.message_id,
            parsed.parts, parsed.metadata,
        )
    assert created[0]["resume"] is True
    assert created[0]["user_message_pre_persisted"] is True


@pytest.mark.asyncio
async def test_application_reads_projection_twice_then_uses_admin_submit(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / THREAD_ID
    workspace.mkdir()
    reader = Mock()
    reader.workspace_root = workspace.resolve()
    reader.read.side_effect = [complete_projection(), complete_projection()]
    run_data = Mock()
    run_data.read.return_value = make_run().model_dump(mode="json")
    result = StoryWorkspaceConfirmationSubmitOutputDTO(
        message_id=story_workspace_dream_confirmation_message_id(
            ACTOR_ID, RUN_ID, "swc_test-key"
        ),
        story_workspace_run_id=RUN_ID,
        thread_id=THREAD_ID,
        status="accepted",
        replayed=True,
        dispatched=True,
        request_id=REQUEST_ID,
        dispatch=None,
    )
    confirmation_data = Mock()
    confirmation_data.submit_recovering.return_value = result
    coordinator = Mock()
    service = DreamConfirmationApplicationService(
        dream_confirmation_coordinator=coordinator
    )
    with (
        patch.object(service, "_thread_workspace", return_value=workspace),
        patch(
            "services.deck.story_workflow_application.StoryWorkspaceDreamFileReader",
            return_value=reader,
        ),
        patch(
            "services.deck.story_workflow_application.database.get_db",
            side_effect=AssertionError("confirmation path must not access PostgreSQL"),
        ),
    ):
        accepted = await service.submit_dream_confirmation(
            RUN_ID,
            command(),
            actor={"actor_id": ACTOR_ID, "workspace_id": WORKSPACE_ID},
            run_data=run_data,
            confirmation_data=confirmation_data,
            access_token="oauth-access-token",
        )
    assert accepted.dispatched is True
    assert reader.read.call_count == 2
    assert confirmation_data.submit_recovering.call_count == 1
    assert coordinator.schedule.call_count == 0
