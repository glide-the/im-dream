# [Input] Current request OAuth/canonical actor, published Thread lookup and default Workspace ensure.
# [Output] Validated Thread ownership and original text default Workspace result/receipt.
# [Pos] File metadata consumer; no filesystem, configuration or database access.
# [Sync] 2026-09-15: reuse registered76 empty-input default operation and original two-state receipt.
# [Sync] 2026-09-15: reuse strict Chat DTO and exact schema gate before any file access.
# [Sync] 2026-09-15: share the unchanged four-schema gate with bound assistant persistence.
from __future__ import annotations

from .chat_data import AdminChatData
from .chat_models import ThreadIdInputDTO
from pydantic import Field

from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import OperationCapabilityDTO, SchemaCapabilityDTO, StrictDTO
from .workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS, require_workflow_capabilities


class WorkspaceDefaultInputDTO(StrictDTO):
    pass


class WorkspaceDefaultOutputDTO(StrictDTO):
    workspace_id: str = Field(min_length=1)


ENSURE_DEFAULT_WORKSPACE = DomainOperation(
    OperationCapabilityDTO(name="workspace-default.ensure", kind="write", user_scope="dream:write", background_scope=None,
        input_schema_version=1, output_schema_version=1,
        contract_sha256="5fb0f70b1790979687090e6c04dd837f24ff0a4c0598d95d5085117e65aa2b95"),
    WorkspaceDefaultInputDTO, WorkspaceDefaultOutputDTO,
)

WORKSPACE_SCHEMA_REQUIREMENTS = (
    *WORKFLOW_SCHEMA_REQUIREMENTS,
    SchemaCapabilityDTO(capability="dream.chat-history-keyset-pagination.v1", version=1, contract_sha256="a0dfe5f8d4b4330a9e17db07a8716d5d2bc25e291f3624f09005e79c01fc8ab0"),
    SchemaCapabilityDTO(capability="dream.chat-history-final-projection.v1", version=1, contract_sha256="50c27f86113c170064b0913bf052f9bd12884d3345c920d7b11468a768e0a432"),
)


def require_workspace_capabilities(client: AdminDataClient, request_id: str) -> None:
    capabilities = client.capabilities(request_id)
    schemas = {item.capability: item for item in capabilities.schema_capabilities}
    if len(schemas) != len(capabilities.schema_capabilities) or any(schemas.get(item.capability) != item for item in WORKSPACE_SCHEMA_REQUIREMENTS):
        raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)


class AdminWorkspaceData:
    def __init__(self, client: AdminDataClient, *, canonical_user_id: str):
        self._client = client
        self._chat = AdminChatData(client)
        self._canonical_user_id = canonical_user_id

    def ensure_default(self, input_dto: WorkspaceDefaultInputDTO, request_id: str, *, access_token: str) -> WorkspaceDefaultOutputDTO:
        require_workflow_capabilities(self._client, request_id)
        return self._client.execute(ENSURE_DEFAULT_WORKSPACE, input_dto, request_id, access_token=access_token)

    def default_receipt(self, request_id: str, *, access_token: str):
        require_workflow_capabilities(self._client, request_id)
        return self._client.receipt(ENSURE_DEFAULT_WORKSPACE, request_id, access_token=access_token)

    def exists_owned(self, input_dto: ThreadIdInputDTO, request_id: str, *, access_token: str) -> bool:
        require_workspace_capabilities(self._client, request_id)
        result = self._chat.get_thread(input_dto, request_id, access_token=access_token)
        if result.thread is None:
            return False
        if result.thread.id != input_dto.thread_id or result.thread.user_id != self._canonical_user_id:
            raise invalid_response(request_id)
        return True
