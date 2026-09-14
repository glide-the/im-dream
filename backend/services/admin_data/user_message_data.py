# [Input] Actual atomic user-turn DTO, Python JSON business values and original pure text projection.
# [Output] Typed raw-JSON user message/title/confirmation command with exact reply identity.
# [Pos] User-turn domain consumer; Admin owns the transaction and durable control-record guard.
# [Sync] 2026-09-15: preserve Python numeric lexemes and avoid split message/title/guard writes.
from __future__ import annotations

import json

from pydantic import field_validator

from libs.claude_agent_kit.messages.message_parts import extract_text_from_parts
from .chat_models import EntityId
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import OperationCapabilityDTO, StrictDTO


def _reject_constant(value):
    raise ValueError("Non-JSON number")


class UserMessageInputDTO(StrictDTO):
    thread_id: EntityId
    message_id: EntityId
    parts_json: str
    metadata_json: str | None
    title_candidate: str

    @field_validator("parts_json", "metadata_json")
    @classmethod
    def validate_raw_json(cls, value, info):
        if value is None:
            return value
        try:
            parsed = json.loads(value, parse_constant=_reject_constant)
        except (ValueError, TypeError):
            raise ValueError("Invalid business JSON") from None
        expected = list if info.field_name == "parts_json" else dict
        if not isinstance(parsed, expected):
            raise ValueError("Invalid business JSON shape")
        return value


class UserMessageOutputDTO(StrictDTO):
    message_id: EntityId
    confirmation_preserved: bool


PERSIST_USER_MESSAGE = DomainOperation(
    OperationCapabilityDTO(name="chat-user-message.persist", kind="write", user_scope="dream:write", background_scope=None,
        input_schema_version=1, output_schema_version=1,
        contract_sha256="2c5b20900ef867a237613e49a89b4073f4c0c89cd1d2161962f7132084696c37"),
    UserMessageInputDTO, UserMessageOutputDTO,
)


def user_message_input(thread_id: str, message_id: str, parts: list, metadata: dict | None) -> UserMessageInputDTO:
    try:
        parts_json = json.dumps(parts, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        metadata_json = json.dumps(metadata, ensure_ascii=False, separators=(",", ":"), allow_nan=False) if metadata is not None else None
        candidate = extract_text_from_parts(parts)
    except (ValueError, TypeError, OverflowError):
        raise AdminDataError("ADMIN_OPERATION_INPUT_INVALID", 400) from None
    return UserMessageInputDTO(thread_id=thread_id, message_id=message_id, parts_json=parts_json, metadata_json=metadata_json, title_candidate=candidate)


class AdminUserMessageData:
    def __init__(self, client: AdminDataClient):
        self._client = client

    def persist(self, input_dto: UserMessageInputDTO, request_id: str, *, access_token: str) -> UserMessageOutputDTO:
        result = self._client.execute(PERSIST_USER_MESSAGE, input_dto, request_id, access_token=access_token)
        if result.message_id != input_dto.message_id:
            raise invalid_response(request_id, write=True)
        return result
