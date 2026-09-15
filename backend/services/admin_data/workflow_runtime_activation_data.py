# [Input] Admin Registry108 activation contract and one exact server-persistence grant.
# [Output] Strict Runtime activation DTOs with original-request receipt recovery.
# [Pos] Dream consumer boundary; Admin owns ORM/transaction and Dream owns verified workspace bytes/Runtime/SSE.
# [Sync] 2026-09-15: pin workflow-runtime.activate without PostgreSQL, path or placement selectors.
"""Typed Registry108 consumer for atomic Story Workspace Runtime activation."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator

from .chat_models import ChatStrictDTO, EntityId
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import OperationCapabilityDTO, SchemaCapabilityDTO
from .workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS

RunId = Annotated[str, Field(pattern=r"^run_[0-9a-f]{32}$")]
RuntimeLockId = Annotated[str, Field(pattern=r"^rpl_[0-9a-f]{32}$")]
RuntimeReceiptId = Annotated[str, Field(pattern=r"^rlr_[0-9a-f]{32}$")]
AgentSessionId = Annotated[str, Field(pattern=r"^as_[0-9a-f]{32}$")]
ArtifactDigest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


class WorkflowRuntimeVerifiedPluginDTO(ChatStrictDTO):
    package_spec: Annotated[EntityId, Field(max_length=255)]
    resolved_version: Annotated[EntityId, Field(max_length=255)]
    artifact_digest: ArtifactDigest
    has_manifest: bool


class WorkflowRuntimeActivationInputDTO(ChatStrictDTO):
    thread_id: Annotated[EntityId, Field(max_length=255)]
    workflow_run_id: RunId
    remote_session_ref: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
    ]
    verified_plugins: list[WorkflowRuntimeVerifiedPluginDTO]


class WorkflowRuntimeActivationOutputDTO(ChatStrictDTO):
    thread_id: Annotated[EntityId, Field(max_length=255)]
    workflow_run_id: RunId
    workspace_id: Annotated[EntityId, Field(max_length=255)]
    runtime_plugin_lock_id: RuntimeLockId
    runtime_load_receipt_id: RuntimeReceiptId
    agent_session_id: AgentSessionId
    status: Literal["running", "output_validating", "pending_review", "confirmed"]
    replayed: bool

    @field_validator("replayed", mode="before")
    @classmethod
    def require_boolean_replay(cls, value):
        if type(value) is not bool:
            raise ValueError("Runtime activation replay flag must be boolean")
        return value


ACTIVATE_WORKFLOW_RUNTIME = DomainOperation(
    OperationCapabilityDTO(
        name="workflow-runtime.activate",
        kind="write",
        user_scope="dream:write",
        background_scope=None,
        input_schema_version=1,
        output_schema_version=1,
        contract_sha256=(
            "50a35aa706efc3f9515b5ff72b52b49c"
            "9a7ab2f5e34de959377c2c67fb054d1f"
        ),
    ),
    WorkflowRuntimeActivationInputDTO,
    WorkflowRuntimeActivationOutputDTO,
)
WORKFLOW_RUNTIME_ACTIVATION_OPERATIONS = (ACTIVATE_WORKFLOW_RUNTIME,)
WORKFLOW_RUNTIME_ACTIVATION_SCHEMA_REQUIREMENTS = (
    *WORKFLOW_SCHEMA_REQUIREMENTS,
    SchemaCapabilityDTO(
        capability="dream.runtime.local-placement.v1",
        version=1,
        contract_sha256=(
            "87fbd3c28bc077992bfa0e12674e71b5"
            "9182ea08934314c02560c8b577c50983"
        ),
    ),
)


def require_workflow_runtime_activation_capabilities(
    client: AdminDataClient,
    request_id: str,
) -> None:
    capabilities = client.capabilities(request_id)
    schemas = {
        item.capability: item for item in capabilities.schema_capabilities
    }
    if (
        len(schemas) != len(capabilities.schema_capabilities)
        or any(
            schemas.get(item.capability) != item
            for item in WORKFLOW_RUNTIME_ACTIVATION_SCHEMA_REQUIREMENTS
        )
    ):
        raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)


class AdminWorkflowRuntimeActivationProvider:
    """Marker for server owners that activate one verified Story Runtime."""

    def activate_workflow_runtime(
        self,
        *,
        actor_id: str,
        thread_id: str,
        workflow_run_id: str,
        remote_session_ref: str,
        verified_plugins: list[dict],
    ) -> WorkflowRuntimeActivationOutputDTO:
        raise NotImplementedError


class AdminWorkflowRuntimeActivationData:
    def __init__(self, client: AdminDataClient) -> None:
        self._client = client

    @staticmethod
    def validate_reply(
        input_dto: WorkflowRuntimeActivationInputDTO,
        result: WorkflowRuntimeActivationOutputDTO,
        request_id: str,
        *,
        write: bool,
    ) -> WorkflowRuntimeActivationOutputDTO:
        if (
            result.thread_id != input_dto.thread_id
            or result.workflow_run_id != input_dto.workflow_run_id
        ):
            raise invalid_response(request_id, write=write)
        return result

    def activate(
        self,
        input_dto: WorkflowRuntimeActivationInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> WorkflowRuntimeActivationOutputDTO:
        if type(input_dto) is not WorkflowRuntimeActivationInputDTO:
            raise AdminDataError("ADMIN_OPERATION_INPUT_INVALID", 400, request_id)
        require_workflow_runtime_activation_capabilities(
            self._client,
            request_id,
        )
        result = self._client.execute(
            ACTIVATE_WORKFLOW_RUNTIME,
            input_dto,
            request_id,
            access_token=access_token,
        )
        return self.validate_reply(input_dto, result, request_id, write=True)

    def receipt(
        self,
        input_dto: WorkflowRuntimeActivationInputDTO,
        request_id: str,
        *,
        access_token: str,
    ):
        if type(input_dto) is not WorkflowRuntimeActivationInputDTO:
            raise AdminDataError("ADMIN_OPERATION_INPUT_INVALID", 400, request_id)
        require_workflow_runtime_activation_capabilities(
            self._client,
            request_id,
        )
        result = self._client.receipt(
            ACTIVATE_WORKFLOW_RUNTIME,
            request_id,
            access_token=access_token,
        )
        if result.status == "committed":
            self.validate_reply(input_dto, result.result, request_id, write=True)
        return result
