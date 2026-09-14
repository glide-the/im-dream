# [Input] Five actual Admin Deck content-version hashes, schema capabilities and typed request OAuth.
# [Output] Capability-gated original-ID consumers with entity checks and raw snapshot projection.
# [Pos] Deck content-version HTTP adapter; Admin owns all CAS, canonicalization and durable transactions.
# [Sync] 2026-09-15: move public content state/preview/commit/history/detail to Admin.
from __future__ import annotations

from . import deck_version_models as dto
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import OperationCapabilityDTO, SchemaCapabilityDTO
from .workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS

DECK_VERSION_SCHEMA_REQUIREMENTS = (*WORKFLOW_SCHEMA_REQUIREMENTS,
    SchemaCapabilityDTO(capability="dream.deck-content-canonical-storage.v1", version=1,
        contract_sha256="97a95f92efecf3435890fcb3f9c1ce46e33fbed8a3de4dca3a632484de4f1c76"),
    SchemaCapabilityDTO(capability="dream.deck-content-versions.v1", version=1,
        contract_sha256="ca7ad5914895d6aa9e8c7d576b9af3ed65b44f34318e068d2fc10c90e351e4c3"),
)
CONTENT_STATE = DomainOperation(OperationCapabilityDTO(name="deck-content.state", kind="read", user_scope="dream:read", background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256="6dc30c2fde89523296bab823affd10aebaaa03464ccda22745281ba48c18ddab"), dto.DeckIdInputDTO, dto.DeckVersionStateDTO)
CONTENT_PREVIEW = DomainOperation(OperationCapabilityDTO(name="deck-content.preview", kind="read", user_scope="dream:read", background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256="e1419743c76a99de067a6d5e6ead228de22f8cefa97b85e43cc8d42ae7182600"), dto.DeckVersionMutationInputDTO, dto.DeckVersionPreviewDTO)
CONTENT_COMMIT = DomainOperation(OperationCapabilityDTO(name="deck-content.commit", kind="write", user_scope="dream:write", background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256="5840f1efd1d250e6324c77206b6c9173edcb3651d5d097ae16bdc4a561ee20a4"), dto.DeckVersionCommitInputDTO, dto.DeckVersionCommitDTO)
CONTENT_HISTORY = DomainOperation(OperationCapabilityDTO(name="deck-content.history", kind="read", user_scope="dream:read", background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256="1cb1fcc13aba4f852eaa3f0cca5e8322832645d98dd52baa629412ecb9633382"), dto.DeckVersionHistoryInputDTO, dto.DeckVersionHistoryDTO)
CONTENT_DETAIL = DomainOperation(OperationCapabilityDTO(name="deck-content.detail", kind="read", user_scope="dream:read", background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256="5f1068c64da340aa85a7096d32577099340a1ffd09b1f1b1ea1dbe0fb66edd82"), dto.DeckVersionDetailInputDTO, dto.DeckVersionDetailDTO)
DECK_VERSION_OPERATIONS = (CONTENT_STATE, CONTENT_PREVIEW, CONTENT_COMMIT, CONTENT_HISTORY, CONTENT_DETAIL)


class AdminDeckVersionData:
    def __init__(self, client: AdminDataClient):
        self._client = client

    def _execute(self, operation, input_dto, request_id, access_token):
        capabilities = self._client.capabilities(request_id)
        schemas = {item.capability: item for item in capabilities.schema_capabilities}
        if len(schemas) != len(capabilities.schema_capabilities) or any(schemas.get(item.capability) != item for item in DECK_VERSION_SCHEMA_REQUIREMENTS):
            raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)
        result = self._client.execute(operation, input_dto, request_id, access_token=access_token)
        if result.deck_id != input_dto.deck_id:
            raise invalid_response(request_id, write=operation.capability.kind == "write")
        if operation is CONTENT_COMMIT and result.state.deck_id != input_dto.deck_id:
            raise invalid_response(request_id, write=True)
        if operation is CONTENT_HISTORY and result.current.deck_id != input_dto.deck_id:
            raise invalid_response(request_id)
        if operation is CONTENT_DETAIL and (result.version != input_dto.version or result.public_projection()["snapshot"]["deck"]["id"] != input_dto.deck_id):
            raise invalid_response(request_id)
        return result

    def state(self, input_dto: dto.DeckIdInputDTO, request_id: str, *, access_token: str) -> dto.DeckVersionStateDTO:
        return self._execute(CONTENT_STATE, input_dto, request_id, access_token)

    def preview(self, input_dto: dto.DeckVersionMutationInputDTO, request_id: str, *, access_token: str) -> dto.DeckVersionPreviewDTO:
        return self._execute(CONTENT_PREVIEW, input_dto, request_id, access_token)

    def commit(self, input_dto: dto.DeckVersionCommitInputDTO, request_id: str, *, access_token: str) -> dto.DeckVersionCommitDTO:
        return self._execute(CONTENT_COMMIT, input_dto, request_id, access_token)

    def history(self, input_dto: dto.DeckVersionHistoryInputDTO, request_id: str, *, access_token: str) -> dto.DeckVersionHistoryDTO:
        return self._execute(CONTENT_HISTORY, input_dto, request_id, access_token)

    def detail(self, input_dto: dto.DeckVersionDetailInputDTO, request_id: str, *, access_token: str) -> dto.DeckVersionDetailDTO:
        return self._execute(CONTENT_DETAIL, input_dto, request_id, access_token)
