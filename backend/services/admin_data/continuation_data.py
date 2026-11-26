# [Input] Versioned Admin continuation DTOs, exact operation hashes and physical capability.
# [Output] Authenticated history snapshots, immutable claim/progress writes and origin creation.
# [Pos] Internal HTTP consumer; no SQL, filesystem or automatic mutation replay.
# [Sync] 2026-11-04: pin Admin same-session continuation contract.
from __future__ import annotations

import sys
from typing import Annotated, Literal
from pydantic import Field
from .models import StrictDTO, OperationCapabilityDTO, SchemaCapabilityDTO
from .client import DomainOperation
from .chat_models import ChatThreadDTO, ChatMessageDTO, ThreadCreateInputDTO, ThreadCreateResultDTO, QueueEntryResultDTO
from .errors import AdminDataError

class SnapshotInput(StrictDTO):
    thread_id: str
    message_id: str | None
    dispatch_turn_id: str | None

class Snapshot(StrictDTO):
    thread: ChatThreadDTO
    messages: list[ChatMessageDTO]
    history_digest: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]

class ClaimInput(StrictDTO):
    thread_id: str
    message_id: str
    parts_json: str
    metadata_json: str | None
    title_candidate: str
    history_digest: str
    claude_session_id: str | None
    owner: str
    dispatch_turn_id: str

class ProgressInput(StrictDTO):
    thread_id: str
    message_id: str
    owner: str
    dispatch_turn_id: str
    expected_revision: int
    action: Literal["arm_query", "complete", "fail_before_query", "fail_after_query", "mark_unknown"]

class OriginCreateInput(ThreadCreateInputDTO):
    created_execution_origin: Literal["web_cloud", "mobile_ios", "mobile_android"]


def execution_origin():
    if sys.platform == "ios":
        return "mobile_ios"
    if hasattr(sys, "getandroidapilevel") or sys.platform == "android":
        return "mobile_android"
    return "web_cloud"

CREATE_WITH_ORIGIN = DomainOperation(OperationCapabilityDTO(**{'name': 'chat-thread.create-with-origin', 'kind': 'write', 'user_scope': 'dream:write', 'background_scope': None, 'input_schema_version': 1, 'output_schema_version': 1, 'contract_sha256': '9634a3bdf7bd906f264180d35e50adc1c692289fdc092da56eabb31f6f257540'}), OriginCreateInput, ThreadCreateResultDTO)
RESUME_SNAPSHOT = DomainOperation(OperationCapabilityDTO(**{'name': 'chat-message.resume-snapshot', 'kind': 'read', 'user_scope': 'dream:read', 'background_scope': None, 'input_schema_version': 1, 'output_schema_version': 1, 'contract_sha256': '6a10afccfbafb8d01d9f5a5102b71331676bec580652d0b216efc1433f9a343a'}), SnapshotInput, Snapshot)
CLAIM_CONTINUATION = DomainOperation(OperationCapabilityDTO(**{'name': 'chat-input.claim-continuation', 'kind': 'write', 'user_scope': 'dream:write', 'background_scope': None, 'input_schema_version': 1, 'output_schema_version': 1, 'contract_sha256': '58addda0a57e9ea3956eb74d5a29e88944c37759fd498592227b8903c9ac7537'}), ClaimInput, QueueEntryResultDTO)
CONTINUATION_PROGRESS = DomainOperation(OperationCapabilityDTO(**{'name': 'chat-input.continuation-progress', 'kind': 'write', 'user_scope': 'dream:write', 'background_scope': None, 'input_schema_version': 1, 'output_schema_version': 1, 'contract_sha256': '4d04ae28a8070fffc29d5988ca3b88b3b83478ac22b2f02567714e0348e15d85'}), ProgressInput, QueueEntryResultDTO)
CONTINUATION_SCHEMA = SchemaCapabilityDTO(capability='dream.chat-continuation.v1', version=1, contract_sha256='86bc59653c2f5d68a77cc4d922f1f4ebb670599411af6e4d3a64a93db814c3a8')
CONTINUATION_OPERATIONS = (CREATE_WITH_ORIGIN, RESUME_SNAPSHOT, CLAIM_CONTINUATION, CONTINUATION_PROGRESS)


def execute(client, operation, input_dto, request_id, *, access_token):
    if not client.supports((operation,), schema_requirements=(CONTINUATION_SCHEMA,)):
        client.capabilities(request_id)
    if not client.supports((operation,), schema_requirements=(CONTINUATION_SCHEMA,)):
        raise AdminDataError("CHAT_CONTINUATION_CAPABILITY_UNAVAILABLE", 503, request_id)
    return client.execute(operation, input_dto, request_id, access_token=access_token)
