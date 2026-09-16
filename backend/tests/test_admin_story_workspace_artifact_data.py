# [Input] Registry185-191 Pydantic consumer plus fake Admin capabilities, replies and receipts.
# [Output] Exact DTO hashes, actor/run validation and original-request write recovery evidence.
# [Pos] Provider-free Dream data-boundary test; no PostgreSQL, Runtime or shared filesystem.
# [Sync] 2026-09-16: validate the Story Workspace Artifact Admin consumer.
from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.admin_data.errors import AdminDataError
from services.admin_data.models import AbsentReceiptDTO, CommittedReceiptDTO
from services.admin_data.story_workspace_artifact_data import (
    AdminStoryWorkspaceArtifactData,
    READ_STORY_WORKSPACE_ARTIFACT_AUTHORITY,
    RECONCILE_STORY_WORKSPACE_ARTIFACT_INDEX,
    STORY_WORKSPACE_ARTIFACT_OPERATIONS,
    StoryWorkspaceArtifactAuthorityInputDTO,
    StoryWorkspaceArtifactAuthorityOutputDTO,
    StoryWorkspaceArtifactIndexOutputDTO,
    StoryWorkspaceArtifactIndexReconcileInputDTO,
    StoryWorkspaceArtifactProjectionDTO,
)
from services.admin_data.workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS


ACTOR = "42"
RUN = "run_" + "a" * 32
HASH_A = "sha256:" + "a" * 64
HASH_B = "sha256:" + "b" * 64


def run_value() -> dict:
    return {
        "workflow_run_id": RUN,
        "deck_plugin_id": "plugin",
        "deck_plugin_version": "1.0.0",
        "workflow_definition_ref": "flow",
        "deck_runtime_snapshot_id": "snapshot",
        "status": "queued",
        "failed_step": None,
        "error_code": None,
        "retry_of_run_id": None,
        "deck_plugin_manifest_hash": HASH_A,
        "deck_plugin_binding_id": "binding",
        "binding_revision": 1,
        "runtime_plugin_lock_id": "lock",
        "runtime_load_receipt_id": None,
        "workflow_preflight_id": "pf_" + "c" * 32,
        "agent_session_id": None,
        "source_voice_thread_id": "thread-one",
        "source_message_id": "message-one",
        "source_message_time": "2026-09-16T00:00:00.123456+00:00",
        "workspace_id": "workspace-one",
        "idempotency_key": "launch-one",
        "input_hash": HASH_A,
        "semantic_fingerprint": HASH_B,
        "status_version": 1,
        "created_by": ACTOR,
        "created_at": "2026-09-16T00:00:00.123456+00:00",
        "started_at": None,
        "completed_at": None,
    }


def authority_output() -> StoryWorkspaceArtifactAuthorityOutputDTO:
    return StoryWorkspaceArtifactAuthorityOutputDTO.model_validate({
        "authority": {
            "run": run_value(),
            "thread_id": "thread-one",
            "thread_updated_at": "2026-09-16T00:01:00.123456+00:00",
            "deck_id": "deck-one",
            "deck_display_name": "Dream Deck",
            "launch_agent_id": "voice-one",
            "goal": "Write the first episode",
            "project_story_slug": "project-one",
            "episode_authority": None,
            "project_title": None,
            "confirmation_accepted": False,
            "confirmation_dispatched": False,
        }
    })


def projection() -> StoryWorkspaceArtifactProjectionDTO:
    return StoryWorkspaceArtifactProjectionDTO(
        source_project_id="project-one",
        title="Project One",
        episode_count=1,
        artifact_manifest_revision=HASH_A,
        script_revision=HASH_B,
        script_size_bytes=12,
        artifact_status="available",
    )


def index_output() -> StoryWorkspaceArtifactIndexOutputDTO:
    return StoryWorkspaceArtifactIndexOutputDTO.model_validate({
        "observation": {
            "run_id": RUN,
            "project_id": "project-one",
            "project_title": "Project One",
            "story_id": "story-one",
            "status": "indexed",
            "observed_manifest_revision": HASH_A,
            "observed_script_revision": HASH_B,
            "indexed_manifest_revision": HASH_A,
            "indexed_script_revision": HASH_B,
            "episode_count": 1,
            "last_indexed_at": "2026-09-16T00:02:00+00:00",
            "error_code": None,
            "retryable": False,
            "etag": HASH_A,
        },
        "write_status": "same_revision",
    })


class FakeClient:
    def __init__(self, reply) -> None:
        self.reply = reply
        self.execute_calls = []
        self.receipt_calls = []
        self.execute_error: AdminDataError | None = None
        self.receipt_reply = None

    def capabilities(self, _request_id):
        return SimpleNamespace(schema_capabilities=list(WORKFLOW_SCHEMA_REQUIREMENTS))

    def execute(self, operation, input_dto, request_id, *, access_token):
        self.execute_calls.append((operation, input_dto, request_id, access_token))
        if self.execute_error:
            raise self.execute_error
        return self.reply

    def receipt(self, operation, request_id, *, access_token):
        self.receipt_calls.append((operation, request_id, access_token))
        return self.receipt_reply or AbsentReceiptDTO(
            status="absent",
            operation=operation.capability.name,
            request_id=request_id,
        )


def test_registry185_191_are_closed_actor_free_contracts() -> None:
    assert len(STORY_WORKSPACE_ARTIFACT_OPERATIONS) == 7
    assert [item.capability.name for item in STORY_WORKSPACE_ARTIFACT_OPERATIONS] == [
        "story-workspace-artifact.runs",
        "story-workspace-artifact.authority",
        "story-workspace-artifact.episode-authority.ensure",
        "story-workspace-artifact.output-ready",
        "story-workspace-artifact.index.inspect",
        "story-workspace-artifact.index.materialize",
        "story-workspace-artifact.index.reconcile",
    ]
    with pytest.raises(ValueError):
        StoryWorkspaceArtifactAuthorityInputDTO.model_validate({
            "workflow_run_id": RUN,
            "actor_id": ACTOR,
        })


def test_authority_requires_exact_actor_run_and_thread_projection() -> None:
    client = FakeClient(authority_output())
    data = AdminStoryWorkspaceArtifactData(client, canonical_user_id=ACTOR)
    output = data.authority(
        StoryWorkspaceArtifactAuthorityInputDTO(workflow_run_id=RUN),
        "request-authority",
        access_token="oauth",
    )
    assert output.authority.workflow_run().workflow_run_id == RUN
    assert len(client.execute_calls) == 1

    client.reply = authority_output().model_copy(update={
        "authority": authority_output().authority.model_copy(update={
            "thread_id": "thread-forged",
        })
    })
    with pytest.raises(AdminDataError, match="ADMIN_RESPONSE_INVALID"):
        data.authority(
            StoryWorkspaceArtifactAuthorityInputDTO(workflow_run_id=RUN),
            "request-invalid",
            access_token="oauth",
        )


def test_reconcile_recovers_only_the_original_committed_receipt() -> None:
    client = FakeClient(index_output())
    client.execute_error = AdminDataError(
        "ADMIN_UNAVAILABLE",
        503,
        "request-reconcile",
        True,
    )
    client.receipt_reply = CommittedReceiptDTO[StoryWorkspaceArtifactIndexOutputDTO](
        status="committed",
        operation=RECONCILE_STORY_WORKSPACE_ARTIFACT_INDEX.capability.name,
        request_id="request-reconcile",
        result=index_output(),
    )
    data = AdminStoryWorkspaceArtifactData(client, canonical_user_id=ACTOR)
    input_dto = StoryWorkspaceArtifactIndexReconcileInputDTO(
        workflow_run_id=RUN,
        projection=projection(),
        expected_etag=HASH_A,
    )
    recovered = data.reconcile_index(
        input_dto,
        "request-reconcile",
        access_token="oauth",
    )
    assert recovered.write_status == "same_revision"
    assert client.receipt_calls == [(
        RECONCILE_STORY_WORKSPACE_ARTIFACT_INDEX,
        "request-reconcile",
        "oauth",
    )]
    assert len(client.execute_calls) == 1


def test_wrong_operation_or_missing_capability_fails_before_transport() -> None:
    client = FakeClient(authority_output())
    data = AdminStoryWorkspaceArtifactData(client, canonical_user_id=ACTOR)
    with pytest.raises(AdminDataError, match="ADMIN_OPERATION_INPUT_INVALID"):
        data.execute(
            READ_STORY_WORKSPACE_ARTIFACT_AUTHORITY,
            object(),
            "request-wrong-input",
            access_token="oauth",
        )
    client.capabilities = lambda _request_id: SimpleNamespace(schema_capabilities=[])
    with pytest.raises(AdminDataError, match="ADMIN_CAPABILITY_UNAVAILABLE"):
        data.authority(
            StoryWorkspaceArtifactAuthorityInputDTO(workflow_run_id=RUN),
            "request-capability",
            access_token="oauth",
        )
    assert client.execute_calls == []
