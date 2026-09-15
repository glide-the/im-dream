# [Input] Registry115 Guidance Pydantic consumer and fake Admin transport/capability/receipt outcomes.
# [Output] Exact hash, identity, dispatch and original-receipt-only recovery assertions.
# [Pos] Provider-free Dream data-boundary test; no PostgreSQL, Runtime or HTTP server.
# [Sync] 2026-09-15: validate the Story Workspace guidance Admin consumer.
from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace

import pytest

from services.admin_data.errors import AdminDataError
from services.admin_data.models import AbsentReceiptDTO, CommittedReceiptDTO
from services.admin_data.story_workspace_guidance_data import (
    AdminStoryWorkspaceGuidanceData,
    STORY_WORKSPACE_GUIDANCE_OPERATIONS,
    SUBMIT_STORY_WORKSPACE_GUIDANCE,
    StoryWorkspaceGuidanceInputDTO,
    StoryWorkspaceGuidanceMetadataDTO,
    StoryWorkspaceGuidanceResultDTO,
)
from services.admin_data.workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS

RUN_ID = "run_" + "a" * 32
THREAD_ID = "thread-guidance"
ACTOR_ID = "42"
REQUEST_ID = "guidance-original"


def command() -> StoryWorkspaceGuidanceInputDTO:
    return StoryWorkspaceGuidanceInputDTO(
        workflow_run_id=RUN_ID,
        kind="free-text",
        text="第二集节奏放慢",
        step_id=None,
        idempotency_key="key-1",
    )


def fingerprint(input_dto: StoryWorkspaceGuidanceInputDTO) -> str:
    raw = json.dumps(
        {
            "story_workspace_run_id": input_dto.workflow_run_id,
            "actor": ACTOR_ID,
            "command_kind": input_dto.kind,
            "text": input_dto.text,
            "step_id": input_dto.step_id,
        },
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


def result(input_dto: StoryWorkspaceGuidanceInputDTO | None = None):
    input_dto = input_dto or command()
    metadata = StoryWorkspaceGuidanceMetadataDTO(
        kind="story-workspace-guidance",
        story_workspace_run_id=RUN_ID,
        actor=ACTOR_ID,
        request_id=REQUEST_ID,
        idempotency_key=input_dto.idempotency_key,
        command_kind=input_dto.kind,
        step_id=input_dto.step_id,
        text_summary=input_dto.text or "",
        review_action="guide",
        command_fingerprint=fingerprint(input_dto),
    )
    return StoryWorkspaceGuidanceResultDTO.model_validate({
        "message_id": "guide_key-1",
        "story_workspace_run_id": RUN_ID,
        "review_action": "guide",
        "status": "accepted",
        "replayed": False,
        "request_id": REQUEST_ID,
        "dispatch": {
            "thread_id": THREAD_ID,
            "message_id": "guide_key-1",
            "parts": [{
                "type": "text",
                "text": f"[story-workspace guidance · run {RUN_ID}] 第二集节奏放慢",
            }],
            "metadata": metadata,
        },
    })


class FakeClient:
    def __init__(self, reply=None) -> None:
        self.reply = reply or result()
        self.execute_calls = []
        self.receipt_calls = []
        self.execute_error: AdminDataError | None = None
        self.receipt_reply = None

    def capabilities(self, request_id):
        return SimpleNamespace(schema_capabilities=list(WORKFLOW_SCHEMA_REQUIREMENTS))

    def execute(self, operation, input_dto, request_id, *, access_token):
        self.execute_calls.append((operation, input_dto, request_id, access_token))
        if self.execute_error:
            raise self.execute_error
        return self.reply

    def receipt(self, operation, request_id, *, access_token):
        self.receipt_calls.append((operation, request_id, access_token))
        return self.receipt_reply or AbsentReceiptDTO(
            status="absent", operation=operation.capability.name, request_id=request_id
        )


def test_exact_registry115_contract_and_actor_free_input():
    assert STORY_WORKSPACE_GUIDANCE_OPERATIONS == (SUBMIT_STORY_WORKSPACE_GUIDANCE,)
    assert SUBMIT_STORY_WORKSPACE_GUIDANCE.capability.contract_sha256 == (
        "a061ed38d2ca10073bbb7fd078e679f072f0cbd4ff1ce900792fbf8725223727"
    )
    assert SUBMIT_STORY_WORKSPACE_GUIDANCE.capability.user_scope == "dream:write"
    with pytest.raises(ValueError):
        StoryWorkspaceGuidanceInputDTO.model_validate(
            {**command().model_dump(mode="json"), "actor": ACTOR_ID}
        )


def test_submit_validates_exact_server_derived_dispatch():
    client = FakeClient()
    data = AdminStoryWorkspaceGuidanceData(client, canonical_user_id=ACTOR_ID)
    accepted = data.submit(command(), REQUEST_ID, access_token="oauth")
    assert accepted.dispatch is not None
    assert accepted.dispatch.metadata.actor == ACTOR_ID
    assert accepted.dispatch.metadata.command_fingerprint == fingerprint(command())
    assert len(client.execute_calls) == 1

    for invalid in [
        result().model_copy(update={"message_id": "guide_other"}),
        result().model_copy(update={
            "dispatch": result().dispatch.model_copy(update={
                "metadata": result().dispatch.metadata.model_copy(update={"actor": "43"})
            })
        }),
        result().model_copy(update={
            "dispatch": result().dispatch.model_copy(update={
                "parts": [result().dispatch.parts[0].model_copy(update={"text": "forged"})]
            })
        }),
    ]:
        client.reply = invalid
        with pytest.raises(AdminDataError) as raised:
            data.submit(command(), REQUEST_ID, access_token="oauth")
        assert raised.value.code == "ADMIN_RESPONSE_INVALID"
        assert raised.value.outcome_unknown


def test_unknown_write_queries_only_original_receipt_and_never_resends():
    client = FakeClient()
    client.execute_error = AdminDataError("ADMIN_UNAVAILABLE", 503, REQUEST_ID, True)
    client.receipt_reply = CommittedReceiptDTO[StoryWorkspaceGuidanceResultDTO](
        status="committed",
        operation="story-workspace-guidance.submit",
        request_id=REQUEST_ID,
        result=result(),
    )
    data = AdminStoryWorkspaceGuidanceData(client, canonical_user_id=ACTOR_ID)
    recovered = data.submit_recovering(command(), REQUEST_ID, access_token="oauth")
    assert recovered.dispatch is not None
    assert len(client.execute_calls) == 1
    assert client.receipt_calls == [(SUBMIT_STORY_WORKSPACE_GUIDANCE, REQUEST_ID, "oauth")]


def test_absent_or_invalid_original_receipt_stays_unknown():
    client = FakeClient()
    client.execute_error = AdminDataError("ADMIN_UNAVAILABLE", 503, REQUEST_ID, True)
    data = AdminStoryWorkspaceGuidanceData(client, canonical_user_id=ACTOR_ID)
    with pytest.raises(AdminDataError) as absent:
        data.submit_recovering(command(), REQUEST_ID, access_token="oauth")
    assert absent.value.code == "ADMIN_WRITE_RESULT_UNKNOWN"
    assert absent.value.outcome_unknown

    client.receipt_reply = CommittedReceiptDTO[StoryWorkspaceGuidanceResultDTO](
        status="committed",
        operation="story-workspace-guidance.submit",
        request_id=REQUEST_ID,
        result=result().model_copy(update={
            "dispatch": result().dispatch.model_copy(update={
                "metadata": result().dispatch.metadata.model_copy(update={"actor": "43"})
            })
        }),
    )
    with pytest.raises(AdminDataError) as invalid:
        data.submit_recovering(command(), REQUEST_ID, access_token="oauth")
    assert invalid.value.code == "ADMIN_RESPONSE_INVALID"
    assert invalid.value.outcome_unknown
