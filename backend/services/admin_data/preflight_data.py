# [Sync] 2026-09-17: reuse the validated immutable Admin capability snapshot instead of repeating discovery per domain call.
# [Input] Published Preflight read/execute/original-receipt contracts and current OAuth actor.
# [Output] Original projection, raw JSON execution and bounded original-receipt recovery.
# [Pos] Domain consumer; Admin owns stored state, checks, clock and token issuance.
# [Sync] 2026-09-15: reuse original lifecycle validation without Workspace initialization or SQL.
# [Sync] 2026-09-15: reuse the extracted identity/unified gate without changing the read projection.
# [Sync] 2026-09-16: recover an unknown execute only from its original committed receipt.
from __future__ import annotations

import json
import re
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, StringConstraints, field_validator, model_validator

from models.workflow_preflight import WorkflowPreflight
from .chat_models import ChatStrictDTO, EntityId, NonnegativeSafeInteger, validate_timestamp_text
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import Identifier, OperationCapabilityDTO, SchemaCapabilityDTO
from .workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS, require_workflow_capabilities

PreflightId = Annotated[str, Field(pattern=r"^pf_[0-9a-f]{32}$")]


class PreflightInputDTO(ChatStrictDTO):
    model_config = ConfigDict(str_strip_whitespace=True)
    workflow_preflight_id: PreflightId


class PreflightDTO(ChatStrictDTO):
    model_config = ConfigDict(str_strip_whitespace=True)
    workflow_preflight_id: PreflightId
    deck_id: EntityId
    binding_revision: NonnegativeSafeInteger
    deck_plugin_id: EntityId
    deck_plugin_version: EntityId
    runtime_plugin_lock_id: EntityId
    deck_runtime_profile_id: EntityId
    deck_runtime_snapshot_id: str | None
    deck_runtime_snapshot_summary_hash: str | None
    input_hash: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    status: Literal["checking", "passed", "failed", "expired"]
    error_code: str | None
    failed_check: Literal["identity_workspace_permission", "binding_release", "manifest_workflow_schema", "host_agent_runtime_compatibility", "capability_source_policy", "deck_runtime_snapshot", "runtime_materialization", "token_issuance"] | None
    expires_at: str
    preflight_token: str | None = Field(repr=False)
    created_by: EntityId
    created_at: str

    @field_validator("expires_at", "created_at", mode="before")
    @classmethod
    def validate_workflow_time(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        validate_timestamp_text(value)
        fraction = re.search(r"\.([0-9]+)", value)
        if fraction and len(fraction.group(1)) > 6:
            raise ValueError("Workflow timestamp exceeds microsecond precision")
        return value

    @model_validator(mode="after")
    def validate_original_lifecycle(self):
        WorkflowPreflight.model_validate(self.model_dump())
        return self


class PreflightOutputDTO(ChatStrictDTO):
    preflight: PreflightDTO


READ_PREFLIGHT = DomainOperation(OperationCapabilityDTO(name="workflow-preflight.read", kind="read", user_scope="dream:read", background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256="ddb0cf666b0dc24fcc4df3ef84be42232b5f907d3361c165eb4c6244bc912d73"),
    PreflightInputDTO, PreflightOutputDTO)

PREFLIGHT_EXECUTION_SCHEMA_REQUIREMENTS = (
    *WORKFLOW_SCHEMA_REQUIREMENTS,
    SchemaCapabilityDTO(capability="dream.workflow-preflight-request.v1", version=1, contract_sha256="7123babb03535e0a0c7a818e902c331cefbe73c660b46395136dcc9a5b19f3da"),
)
PREFLIGHT_ORIGINAL_RECEIPT_SHA256 = "ad144287942f6f3ad2db82dda7c7b0f20cdf3578e68df4bd8e8b86e8dbbec2f2"


class PreflightExecutionInputDTO(ChatStrictDTO):
    workspace_id: Annotated[EntityId, StringConstraints(strip_whitespace=True)]
    deck_id: Annotated[EntityId, StringConstraints(strip_whitespace=True)]
    binding_revision: NonnegativeSafeInteger
    input_json: str = Field(repr=False)

    @field_validator("workspace_id", "deck_id")
    @classmethod
    def strip_identifier(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Preflight scope is empty")
        return value

    @field_validator("input_json")
    @classmethod
    def validate_object_json(cls, value: str) -> str:
        def reject_constant(_constant):
            raise ValueError("Object JSON is invalid")
        try:
            parsed = json.loads(value, parse_constant=reject_constant)
        except (ValueError, RecursionError):
            raise ValueError("Object JSON is invalid") from None
        if not isinstance(parsed, dict):
            raise ValueError("Preflight input must be object JSON")
        return value


class PreflightExecutionOutputDTO(ChatStrictDTO):
    request_state: Literal["in_progress", "committed"]
    preflight: PreflightDTO

    @model_validator(mode="after")
    def validate_request_state(self):
        if self.request_state == "in_progress" and self.preflight.status != "checking":
            raise ValueError("Executing Preflight request must retain checking state")
        return self


class PreflightAbsentReceiptDTO(ChatStrictDTO):
    status: Literal["absent"]
    operation: Literal["workflow-preflight.execute"]
    request_id: Identifier


class PreflightInProgressReceiptDTO(ChatStrictDTO):
    status: Literal["in_progress"]
    operation: Literal["workflow-preflight.execute"]
    request_id: Identifier
    result: PreflightExecutionOutputDTO

    @model_validator(mode="after")
    def validate_receipt_state(self):
        if self.result.request_state != self.status:
            raise ValueError("Receipt must match original request state")
        return self


class PreflightCommittedReceiptDTO(PreflightInProgressReceiptDTO):
    status: Literal["committed"]


PreflightOriginalReceiptDTO = Annotated[PreflightAbsentReceiptDTO | PreflightInProgressReceiptDTO | PreflightCommittedReceiptDTO, Field(discriminator="status")]
EXECUTE_PREFLIGHT = DomainOperation(OperationCapabilityDTO(name="workflow-preflight.execute", kind="write", user_scope="dream:write", background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256="413db72b5d4bfc1fdf572d801aec4339a7b00549ea19ebc4025c67f5ae2cf494"),
    PreflightExecutionInputDTO, PreflightExecutionOutputDTO)


def require_preflight_execution_capabilities(client: AdminDataClient, request_id: str):
    capabilities = client.capabilities_snapshot(request_id)
    schemas = {item.capability: item for item in capabilities.schema_capabilities}
    if len(schemas) != len(capabilities.schema_capabilities) or any(schemas.get(item.capability) != item for item in PREFLIGHT_EXECUTION_SCHEMA_REQUIREMENTS):
        raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)


class AdminPreflightData:
    def __init__(self, client: AdminDataClient, *, canonical_user_id: str):
        self._client = client
        self._canonical_user_id = canonical_user_id

    def read(self, input_dto: PreflightInputDTO, request_id: str, *, access_token: str):
        require_workflow_capabilities(self._client, request_id)
        result = self._client.execute(READ_PREFLIGHT, input_dto, request_id, access_token=access_token)
        if result.preflight.workflow_preflight_id != input_dto.workflow_preflight_id or result.preflight.created_by != self._canonical_user_id:
            raise invalid_response(request_id)
        return WorkflowPreflight.model_validate(result.preflight.model_dump()).model_dump(mode="json")

    def execute(self, input_dto: PreflightExecutionInputDTO, request_id: str, *, access_token: str):
        require_preflight_execution_capabilities(self._client, request_id)
        result = self._client.execute(EXECUTE_PREFLIGHT, input_dto, request_id, access_token=access_token)
        if result.preflight.created_by != self._canonical_user_id or result.preflight.deck_id != input_dto.deck_id or result.preflight.binding_revision != input_dto.binding_revision:
            raise invalid_response(request_id, write=True)
        return WorkflowPreflight.model_validate(result.preflight.model_dump()).model_dump(mode="json")

    def receipt(self, request_id: str, *, access_token: str):
        require_preflight_execution_capabilities(self._client, request_id)
        result = self._client.preflight_original_receipt(request_id, access_token=access_token)
        if result.status != "absent" and result.result.preflight.created_by != self._canonical_user_id:
            raise invalid_response(request_id)
        return result

    def execute_recovering(self, input_dto: PreflightExecutionInputDTO, request_id: str, *, access_token: str):
        try:
            return self.execute(input_dto, request_id, access_token=access_token)
        except AdminDataError as error:
            if not error.outcome_unknown:
                raise
            receipt = self.receipt(request_id, access_token=access_token)
            if receipt.status == "committed":
                result = receipt.result
                if result.preflight.created_by != self._canonical_user_id or result.preflight.deck_id != input_dto.deck_id or result.preflight.binding_revision != input_dto.binding_revision:
                    raise invalid_response(request_id, write=True)
                return WorkflowPreflight.model_validate(result.preflight.model_dump()).model_dump(mode="json")
            raise error
