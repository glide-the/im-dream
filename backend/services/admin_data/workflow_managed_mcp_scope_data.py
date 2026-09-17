# [Input] Admin Registry107 Run/Thread scope response and an exact server persistence grant.
# [Output] Strict actor-bound managed MCP workspace identifier.
# [Pos] Managed MCP scope consumer; Admin owns ORM/access and Dream owns snapshot use and Runtime.
# [Sync] 2026-09-15: pin Registry107 and expose no PostgreSQL, query or physical Runtime selector.
"""Typed Registry107 consumer for the managed MCP workspace scope."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from pydantic import Field, TypeAdapter

from .chat_models import ChatStrictDTO, EntityId
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import CanonicalUserId, OperationCapabilityDTO, PrincipalDTO
from .workflow_data import require_workflow_capabilities

RunId = Annotated[str, Field(pattern=r"^run_[0-9a-f]{32}$")]


class WorkflowManagedMcpScopeInputDTO(ChatStrictDTO):
    thread_id: Annotated[str, Field(min_length=1, max_length=255)]
    workflow_run_id: RunId


class WorkflowManagedMcpScopeOutputDTO(WorkflowManagedMcpScopeInputDTO):
    workspace_id: Annotated[EntityId, Field(max_length=255)]


RESOLVE_WORKFLOW_MANAGED_MCP_SCOPE = DomainOperation(
    OperationCapabilityDTO(
        name="workflow-managed-mcp-scope.resolve",
        kind="read",
        user_scope="dream:read",
        background_scope=None,
        input_schema_version=1,
        output_schema_version=1,
        contract_sha256=(
            "c996f3bf5fc2bfcc8fa9a7c3b90ae039"
            "800109a56ec2159882cfd921d6f74bdc"
        ),
    ),
    WorkflowManagedMcpScopeInputDTO,
    WorkflowManagedMcpScopeOutputDTO,
)
WORKFLOW_MANAGED_MCP_SCOPE_OPERATIONS = (
    RESOLVE_WORKFLOW_MANAGED_MCP_SCOPE,
)


@dataclass(frozen=True, slots=True)
class AdminWorkflowManagedMcpScopeResolution:
    canonical_user_id: str
    snapshot: WorkflowManagedMcpScopeOutputDTO

    def __post_init__(self) -> None:
        PrincipalDTO.validate_canonical_id(
            TypeAdapter(CanonicalUserId).validate_python(
                self.canonical_user_id,
                strict=True,
            )
        )

    def workspace_for(
        self,
        *,
        actor_id: str,
        thread_id: str,
        workflow_run_id: str,
    ) -> str:
        if (
            self.canonical_user_id != str(actor_id)
            or self.snapshot.thread_id != thread_id
            or self.snapshot.workflow_run_id != workflow_run_id
        ):
            raise AdminDataError("DREAM_DELEGATION_ENTITY_DENIED", 403)
        return self.snapshot.workspace_id


class AdminWorkflowManagedMcpScopeProvider:
    """Marker for server owners that resolve Registry107 scope."""

    def managed_mcp_workspace_scope(
        self,
        *,
        actor_id: str,
        thread_id: str,
        workflow_run_id: str,
    ) -> AdminWorkflowManagedMcpScopeResolution:
        raise NotImplementedError


class AdminWorkflowManagedMcpScopeData:
    def __init__(
        self,
        client: AdminDataClient,
        *,
        canonical_user_id: str,
    ) -> None:
        self._client = client
        self._canonical_user_id = PrincipalDTO.validate_canonical_id(
            TypeAdapter(CanonicalUserId).validate_python(
                canonical_user_id,
                strict=True,
            )
        )

    def resolve(
        self,
        input_dto: WorkflowManagedMcpScopeInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> AdminWorkflowManagedMcpScopeResolution:
        require_workflow_capabilities(self._client, request_id)
        result = self._client.execute(
            RESOLVE_WORKFLOW_MANAGED_MCP_SCOPE,
            input_dto,
            request_id,
            access_token=access_token,
        )
        if (
            result.thread_id != input_dto.thread_id
            or result.workflow_run_id != input_dto.workflow_run_id
        ):
            raise invalid_response(request_id)
        return AdminWorkflowManagedMcpScopeResolution(
            canonical_user_id=self._canonical_user_id,
            snapshot=result,
        )
