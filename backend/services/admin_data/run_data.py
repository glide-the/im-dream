# [Input] Published full Workflow Run read/create/retry contracts and the current OAuth actor.
# [Output] Original twenty-eight-field model, scoped atomic commands and explicit bounded receipts.
# [Pos] Domain consumer; Admin owns Run state, token consumption, hashes and database commits.
# [Sync] 2026-09-15: retain original lifecycle/time/key semantics without local SQL or runtime dispatch.
from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from models.workflow_run import WorkflowRun
from .chat_models import ChatStrictDTO, EntityId, PositiveSafeInteger, validate_timestamp_text
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import OperationCapabilityDTO
from .workflow_data import require_workflow_capabilities

RunId = Annotated[str, Field(pattern=r"^run_[0-9a-f]{32}$")]
PreflightId = Annotated[str, Field(pattern=r"^pf_[0-9a-f]{32}$")]
RunKey = Annotated[str, Field(min_length=1, max_length=255)]
Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


class RunDTO(ChatStrictDTO):
    model_config = ConfigDict(str_strip_whitespace=True)
    workflow_run_id: RunId
    deck_plugin_id: EntityId
    deck_plugin_version: EntityId
    workflow_definition_ref: EntityId
    deck_runtime_snapshot_id: EntityId
    status: Literal["preflight", "queued", "running", "output_validating", "pending_review", "confirmed", "rejected", "completed", "failed", "cancelled"]
    failed_step: str | None
    error_code: str | None
    retry_of_run_id: RunId | None
    deck_plugin_manifest_hash: Digest
    deck_plugin_binding_id: EntityId
    binding_revision: PositiveSafeInteger
    runtime_plugin_lock_id: EntityId
    runtime_load_receipt_id: str | None
    workflow_preflight_id: PreflightId
    agent_session_id: Annotated[str, Field(pattern=r"^as_[0-9a-f]{32}$")] | None
    source_voice_thread_id: str | None
    source_message_id: str | None
    source_message_time: str | None
    workspace_id: EntityId
    idempotency_key: RunKey
    input_hash: Digest
    semantic_fingerprint: Digest
    status_version: PositiveSafeInteger
    created_by: EntityId
    created_at: str
    started_at: str | None
    completed_at: str | None

    @field_validator("source_message_time", "created_at", "started_at", "completed_at", mode="before")
    @classmethod
    def validate_workflow_time(cls, value):
        if value is not None and isinstance(value, str):
            validate_timestamp_text(value)
            fraction = re.search(r"\.([0-9]+)", value)
            if fraction and len(fraction.group(1)) > 6:
                raise ValueError("Workflow timestamp exceeds microsecond precision")
        return value

    @model_validator(mode="after")
    def validate_original_lifecycle(self):
        WorkflowRun.model_validate(self.model_dump())
        return self


class RunLookupInputDTO(ChatStrictDTO):
    model_config = ConfigDict(str_strip_whitespace=True)
    workspace_id: EntityId
    workflow_run_id: RunId


class RunCreationCommonDTO(ChatStrictDTO):
    model_config = ConfigDict(str_strip_whitespace=True)
    workspace_id: EntityId
    workflow_preflight_id: PreflightId
    preflight_token: EntityId = Field(repr=False)
    idempotency_key: RunKey

    @field_validator("idempotency_key")
    @classmethod
    def reject_python_blank_key(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Run key is empty")
        return value


class RunCreateInputDTO(RunCreationCommonDTO):
    source_voice_thread_id: str | None
    source_message_id: str | None
    source_message_time: str | None
    _source_time = field_validator("source_message_time", mode="before")(validate_timestamp_text)

    @model_validator(mode="after")
    def validate_source_tuple(self):
        count = sum(v is not None for v in (self.source_voice_thread_id, self.source_message_id, self.source_message_time))
        if count not in {0, 3}:
            raise ValueError("Voice source requires its complete tuple")
        return self


class RunRetryInputDTO(RunCreationCommonDTO):
    workflow_run_id: RunId


class RunOutputDTO(ChatStrictDTO):
    run: RunDTO


READ_RUN = DomainOperation(OperationCapabilityDTO(name="workflow-run.read", kind="read", user_scope="dream:read", background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256="caf17aab8bb1bdf49fa7a38e8f4ff4e257246adcb3f8c4dea6ea8b5991328f32"), RunLookupInputDTO, RunOutputDTO)
CREATE_RUN = DomainOperation(OperationCapabilityDTO(name="workflow-run.create", kind="write", user_scope="dream:write", background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256="531d41a45a7a745b120a83c57a88bdb0cf40ffcdc52d245d56bc0d372342eb08"), RunCreateInputDTO, RunOutputDTO)
RETRY_RUN = DomainOperation(OperationCapabilityDTO(name="workflow-run.retry", kind="write", user_scope="dream:write", background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256="01c72910ed713ce10c86e03c426f98549c81d1991cbaf05415b6bbcdbb8e9bd7"), RunRetryInputDTO, RunOutputDTO)
RUN_OPERATIONS = (READ_RUN, CREATE_RUN, RETRY_RUN)


class AdminRunData:
    def __init__(self, client: AdminDataClient, *, canonical_user_id: str):
        self._client = client
        self._canonical_user_id = canonical_user_id

    def _validate_reply(self, operation, input_dto, result, request_id, *, write=False):
        run = result.run
        original_run = WorkflowRun.model_validate(run.model_dump())
        invalid = run.created_by != self._canonical_user_id or run.workspace_id != input_dto.workspace_id
        if operation is READ_RUN:
            invalid |= run.workflow_run_id != input_dto.workflow_run_id
        else:
            invalid |= run.idempotency_key != input_dto.idempotency_key
            invalid |= run.retry_of_run_id != (input_dto.workflow_run_id if operation is RETRY_RUN else None)
            if operation is CREATE_RUN:
                source_time = datetime.fromisoformat(input_dto.source_message_time.replace("Z", "+00:00")) if input_dto.source_message_time is not None else None
                invalid |= run.source_voice_thread_id != input_dto.source_voice_thread_id or run.source_message_id != input_dto.source_message_id or original_run.source_message_time != source_time
        if invalid:
            raise invalid_response(request_id, write=write)
        # Same-key replay may retain an older semantically equal Preflight ID.
        return original_run.model_dump(mode="json")

    def execute(self, operation, input_dto, request_id: str, *, access_token: str):
        if not any(operation is item for item in RUN_OPERATIONS):
            raise AdminDataError("ADMIN_OPERATION_CONTRACT_INVALID", 503, request_id)
        require_workflow_capabilities(self._client, request_id)
        result = self._client.execute(operation, input_dto, request_id, access_token=access_token)
        return self._validate_reply(operation, input_dto, result, request_id, write=operation.capability.kind == "write")

    def read(self, input_dto: RunLookupInputDTO, request_id: str, *, access_token: str):
        return self.execute(READ_RUN, input_dto, request_id, access_token=access_token)

    def create(self, input_dto: RunCreateInputDTO, request_id: str, *, access_token: str):
        return self.execute(CREATE_RUN, input_dto, request_id, access_token=access_token)

    def retry(self, input_dto: RunRetryInputDTO, request_id: str, *, access_token: str):
        return self.execute(RETRY_RUN, input_dto, request_id, access_token=access_token)

    def receipt(self, operation, input_dto, request_id: str, *, access_token: str):
        if operation is not CREATE_RUN and operation is not RETRY_RUN:
            raise AdminDataError("ADMIN_OPERATION_CONTRACT_INVALID", 503, request_id)
        if type(input_dto) is not operation.input_dto:
            raise AdminDataError("ADMIN_OPERATION_INPUT_INVALID", 400, request_id)
        require_workflow_capabilities(self._client, request_id)
        result = self._client.receipt(operation, request_id, access_token=access_token)
        if result.status == "committed":
            self._validate_reply(operation, input_dto, result.result, request_id)
        return result
