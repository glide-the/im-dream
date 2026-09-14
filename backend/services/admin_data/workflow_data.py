# [Input] Actual Admin Workflow context contract and explicit request OAuth/actor.
# [Output] Strict ten-field context and immutable server-owned turn snapshot.
# [Pos] Workflow read consumer; Admin alone validates retry/source/binding/database facts.
# [Sync] 2026-09-15: connect public Chat provenance without duplicating the old PG mapper.
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from pydantic import Field, TypeAdapter, field_validator

from story_workspace.contracts import StoryWorkspaceDreamRunContext
from .chat_models import EntityId, PositiveSafeInteger
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import CanonicalUserId, OperationCapabilityDTO, PrincipalDTO, SchemaCapabilityDTO, StrictDTO

ContextId = Annotated[str, Field(min_length=1, max_length=255)]
WORKFLOW_SCHEMA_REQUIREMENTS = (
    SchemaCapabilityDTO(capability="identity.better-auth.v1", version=1, contract_sha256="1dc05e229d3f4147923fcdfe117c4c4930a43bf9f31439d7b4bc83d2a0d04cd3"),
    SchemaCapabilityDTO(capability="dream.schema.unified.v1", version=1, contract_sha256="8b71cf5687f61dee884c3e6f2fb109c7a951b0789066a0f13583a7b67757fa71"),
)


class WorkflowContextInputDTO(StrictDTO):
    thread_id: EntityId


class WorkflowRunContextDTO(StrictDTO):
    workflow_run_id: Annotated[str, Field(pattern=r"^run_[0-9a-f]{32}$")]
    thread_id: ContextId
    deck_id: ContextId
    agent_id: ContextId | None
    deck_plugin_id: ContextId
    deck_plugin_version: ContextId
    deck_plugin_binding_id: ContextId
    binding_revision: PositiveSafeInteger
    deck_runtime_snapshot_id: ContextId
    runtime_plugin_lock_id: ContextId

    @field_validator("thread_id", "deck_id", "agent_id", "deck_plugin_id", "deck_plugin_version", "deck_plugin_binding_id", "deck_runtime_snapshot_id", "runtime_plugin_lock_id", mode="before")
    @classmethod
    def strip_context_id(cls, value):
        return value.strip() if isinstance(value, str) else value


class WorkflowContextOutputDTO(StrictDTO):
    context: WorkflowRunContextDTO | None


RESOLVE_WORKFLOW_CONTEXT = DomainOperation(
    OperationCapabilityDTO(name="workflow-context.resolve", kind="read", user_scope="dream:read", background_scope=None,
        input_schema_version=1, output_schema_version=1,
        contract_sha256="f395682ec6cf8f308df652a1aa2792cca86d102eb1fff62a4c6a59792bfc1e66"),
    WorkflowContextInputDTO, WorkflowContextOutputDTO,
)


@dataclass(frozen=True, slots=True)
class AdminWorkflowResolution:
    canonical_user_id: str
    thread_id: str
    context: StoryWorkspaceDreamRunContext | None

    def __post_init__(self):
        PrincipalDTO.validate_canonical_id(TypeAdapter(CanonicalUserId).validate_python(self.canonical_user_id, strict=True))
        if not isinstance(self.thread_id, str) or not self.thread_id:
            raise ValueError("Invalid Workflow snapshot thread")
        if self.context is not None and (not isinstance(self.context, StoryWorkspaceDreamRunContext) or self.context.thread_id != self.thread_id):
            raise ValueError("Workflow snapshot context does not match its thread")

    def context_for(self, *, actor_id: str, thread_id: str) -> StoryWorkspaceDreamRunContext | None:
        if self.canonical_user_id != str(actor_id) or self.thread_id != thread_id:
            raise AdminDataError("DREAM_DELEGATION_ENTITY_DENIED", 403)
        return self.context


class AdminWorkflowData:
    def __init__(self, client: AdminDataClient):
        self._client = client

    def resolve(self, thread_id: str, request_id: str, *, access_token: str, canonical_user_id: str) -> AdminWorkflowResolution:
        capabilities = self._client.capabilities(request_id)
        schemas = {item.capability: item for item in capabilities.schema_capabilities}
        if len(schemas) != len(capabilities.schema_capabilities) or any(schemas.get(item.capability) != item for item in WORKFLOW_SCHEMA_REQUIREMENTS):
            raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)
        result = self._client.execute(RESOLVE_WORKFLOW_CONTEXT, WorkflowContextInputDTO(thread_id=thread_id), request_id, access_token=access_token)
        if result.context is not None and result.context.thread_id != thread_id:
            raise invalid_response(request_id)
        context = StoryWorkspaceDreamRunContext.model_validate(result.context.model_dump()) if result.context is not None else None
        return AdminWorkflowResolution(canonical_user_id, thread_id, context)
