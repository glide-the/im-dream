# [Input] Current request OAuth/canonical actor and the published Chat Thread lookup.
# [Output] Validated Thread ownership for existing Workspace content/download reads.
# [Pos] File metadata consumer; no filesystem, configuration or database access.
# [Sync] 2026-09-15: reuse strict Chat DTO and exact schema gate before any file access.
from __future__ import annotations

from .chat_data import AdminChatData
from .chat_models import ThreadIdInputDTO
from .client import AdminDataClient
from .errors import AdminDataError, invalid_response
from .models import SchemaCapabilityDTO
from .workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS

WORKSPACE_SCHEMA_REQUIREMENTS = (
    *WORKFLOW_SCHEMA_REQUIREMENTS,
    SchemaCapabilityDTO(capability="dream.chat-history-keyset-pagination.v1", version=1, contract_sha256="a0dfe5f8d4b4330a9e17db07a8716d5d2bc25e291f3624f09005e79c01fc8ab0"),
    SchemaCapabilityDTO(capability="dream.chat-history-final-projection.v1", version=1, contract_sha256="50c27f86113c170064b0913bf052f9bd12884d3345c920d7b11468a768e0a432"),
)


class AdminWorkspaceData:
    def __init__(self, client: AdminDataClient, *, canonical_user_id: str):
        self._client = client
        self._chat = AdminChatData(client)
        self._canonical_user_id = canonical_user_id

    def exists_owned(self, input_dto: ThreadIdInputDTO, request_id: str, *, access_token: str) -> bool:
        capabilities = self._client.capabilities(request_id)
        schemas = {item.capability: item for item in capabilities.schema_capabilities}
        if len(schemas) != len(capabilities.schema_capabilities) or any(schemas.get(item.capability) != item for item in WORKSPACE_SCHEMA_REQUIREMENTS):
            raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)
        result = self._chat.get_thread(input_dto, request_id, access_token=access_token)
        if result.thread is None:
            return False
        if result.thread.id != input_dto.thread_id or result.thread.user_id != self._canonical_user_id:
            raise invalid_response(request_id)
        return True
