# [Input] Actual six Admin Session capability hashes and explicit authenticated OAuth actor.
# [Output] Typed Session domain operations with original request IDs and exact reply identity checks.
# [Pos] Session consumer; Admin owns persistence/ownership, Dream retains metrics and edit events.
# [Sync] 2026-09-15: migrate public writing Session reads/writes without database or delegated scope expansion.
from __future__ import annotations

from .client import AdminDataClient, DomainOperation
from .errors import invalid_response
from .models import OperationCapabilityDTO
from . import session_models as dto

SAVE_SESSION = DomainOperation(
    OperationCapabilityDTO(name="session.save", kind="write", user_scope="dream:write", background_scope=None,
        input_schema_version=1, output_schema_version=1,
        contract_sha256="8396bb5cbcc3e2dda60ba582b22583b5b11249f9dd2286757a7597b4cb134118"),
    dto.SessionSaveInputDTO, dto.SessionSavedDTO,
)
GET_SESSION = DomainOperation(
    OperationCapabilityDTO(name="session.get", kind="read", user_scope="dream:read", background_scope=None,
        input_schema_version=1, output_schema_version=1,
        contract_sha256="f29a43501af8cf3b1d91192bf5bd455d90a36d4b89c7150b453185b41c5a0929"),
    dto.SessionIdInputDTO, dto.SessionResultDTO,
)
BATCH_SESSIONS = DomainOperation(
    OperationCapabilityDTO(name="session.batch", kind="read", user_scope="dream:read", background_scope=None,
        input_schema_version=1, output_schema_version=1,
        contract_sha256="4b161454c28f6d9dcf8579c7bc595b1515a7d64d906726e24cee063fbe95ea21"),
    dto.SessionBatchInputDTO, dto.SessionBatchResultDTO,
)
LIST_SESSIONS = DomainOperation(
    OperationCapabilityDTO(name="session.list", kind="read", user_scope="dream:read", background_scope=None,
        input_schema_version=1, output_schema_version=1,
        contract_sha256="1936970e27a8b854dd08cd785b0da6534656aa5af0e652750693f86e88860435"),
    dto.SessionListInputDTO, dto.SessionListResultDTO,
)
TEXT_SESSIONS = DomainOperation(
    OperationCapabilityDTO(name="session.text-list", kind="read", user_scope="dream:read", background_scope=None,
        input_schema_version=1, output_schema_version=1,
        contract_sha256="d9b0dcc776bb52e4e482f51a060ea14a99f66a309bdbc02f8e7ebeb764ca20f7"),
    dto.SessionTextListInputDTO, dto.SessionTextListResultDTO,
)
DELETE_SESSION = DomainOperation(
    OperationCapabilityDTO(name="session.delete", kind="write", user_scope="dream:write", background_scope=None,
        input_schema_version=1, output_schema_version=1,
        contract_sha256="2a88124addd2979908d9f601816c8577677f2fb21b241b21bda05cbf505bfa1e"),
    dto.SessionIdInputDTO, dto.SessionDeletedDTO,
)
SESSION_OPERATIONS = (SAVE_SESSION, GET_SESSION, BATCH_SESSIONS, LIST_SESSIONS, TEXT_SESSIONS, DELETE_SESSION)


class AdminSessionData:
    def __init__(self, client: AdminDataClient):
        self._client = client

    def save(self, input_dto: dto.SessionSaveInputDTO, request_id: str, *, access_token: str) -> dto.SessionSavedDTO:
        result = self._client.execute(SAVE_SESSION, input_dto, request_id, access_token=access_token)
        if result.session.id != input_dto.session_id:
            raise invalid_response(request_id, write=True)
        return result

    def get(self, input_dto: dto.SessionIdInputDTO, request_id: str, *, access_token: str) -> dto.SessionResultDTO:
        result = self._client.execute(GET_SESSION, input_dto, request_id, access_token=access_token)
        if result.session is not None and result.session.id != input_dto.session_id:
            raise invalid_response(request_id)
        return result

    def batch(self, input_dto: dto.SessionBatchInputDTO, request_id: str, *, access_token: str) -> dto.SessionBatchResultDTO:
        result = self._client.execute(BATCH_SESSIONS, input_dto, request_id, access_token=access_token)
        ids = [item.id for item in result.sessions]
        if len(set(ids)) != len(ids) or not set(ids) <= set(input_dto.session_ids):
            raise invalid_response(request_id)
        return result

    def list(self, input_dto: dto.SessionListInputDTO, request_id: str, *, access_token: str) -> dto.SessionListResultDTO:
        result = self._client.execute(LIST_SESSIONS, input_dto, request_id, access_token=access_token)
        if not input_dto.include_text and any(item.text is not None for item in result.sessions):
            raise invalid_response(request_id)
        return result

    def text_list(self, input_dto: dto.SessionTextListInputDTO, request_id: str, *, access_token: str) -> dto.SessionTextListResultDTO:
        return self._client.execute(TEXT_SESSIONS, input_dto, request_id, access_token=access_token)

    def delete(self, input_dto: dto.SessionIdInputDTO, request_id: str, *, access_token: str) -> dto.SessionDeletedDTO:
        return self._client.execute(DELETE_SESSION, input_dto, request_id, access_token=access_token)
