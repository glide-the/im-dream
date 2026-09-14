# [Input] Published owner-only Preflight contract and the current authenticated OAuth actor.
# [Output] Strict original seventeen-field Preflight projection and safe identity validation.
# [Pos] Read consumer; Admin owns stored state, clock and token issuance.
# [Sync] 2026-09-15: reuse original lifecycle validation without Workspace initialization or SQL.
# [Sync] 2026-09-15: reuse the extracted identity/unified gate without changing the read projection.
from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from models.workflow_preflight import WorkflowPreflight
from .chat_models import ChatStrictDTO, EntityId, NonnegativeSafeInteger, validate_timestamp_text
from .client import AdminDataClient, DomainOperation
from .errors import invalid_response
from .models import OperationCapabilityDTO
from .workflow_data import require_workflow_capabilities

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
