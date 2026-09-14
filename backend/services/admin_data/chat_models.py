# [Input] Admin chatThreadDto.ts closed wire projections and the shared final-history validator.
# [Output] Strict Thread/message DTOs, preserving ISO microseconds and decimal canonical IDs.
# [Pos] Chat domain consumer schema boundary; no ORM row, SQL or runtime state machine.
# [Sync] 2026-09-14: consume the 14 published-shape candidates without changing Dream public response projection.

from __future__ import annotations

from datetime import datetime
import re
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, JsonValue, field_validator, model_validator

from chat_message_projection import validate_chat_history_final_projection
from .models import CanonicalUserId, PrincipalDTO, StrictDTO

EntityId = Annotated[str, Field(min_length=1)]
PositiveSafeInteger = Annotated[int, Field(ge=1, le=9_007_199_254_740_991)]
NonnegativeSafeInteger = Annotated[int, Field(ge=0, le=9_007_199_254_740_991)]


class ChatStrictDTO(StrictDTO):
    model_config = ConfigDict(allow_inf_nan=False)


def validate_timestamp_text(value: str | None) -> str | None:
    if value is None:
        return None
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(?::[0-9]{2}(?:\.[0-9]+)?)?(?:Z|[+-][0-9]{2}:[0-9]{2})", value) is None:
        raise ValueError("Timestamp must be an ISO string with a timezone")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Timestamp is invalid") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Timestamp must have a timezone")
    return value


class ChatThreadSummaryDTO(ChatStrictDTO):
    id: EntityId
    title: str | None
    deck_id: str | None
    voice_id: str | None
    created_at: str | None
    updated_at: str | None
    _timestamps = field_validator("created_at", "updated_at")(validate_timestamp_text)


class ChatThreadDTO(ChatThreadSummaryDTO):
    user_id: CanonicalUserId
    claude_session_id: str | None
    agent_contract_version: str | None

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, value: str) -> str:
        return PrincipalDTO.validate_canonical_id(value)


class ChatThreadSearchItemDTO(ChatThreadSummaryDTO):
    messages_text: str


class ChatMessageDTO(ChatStrictDTO):
    id: EntityId
    role: Literal["user", "assistant"]
    parts: list[JsonValue]
    metadata: dict[str, JsonValue] | None
    metadata_decode_error: bool
    created_at: str | None
    history_final_text: str | None
    history_process_available: bool
    history_projection_version: Literal[1] | None
    _timestamp = field_validator("created_at")(validate_timestamp_text)

    @field_validator("history_projection_version", mode="before")
    @classmethod
    def require_integer_projection_version(cls, value):
        if value is not None and type(value) is not int:
            raise ValueError("History projection version must be an integer")
        return value


class ThreadCreateInputDTO(ChatStrictDTO):
    deck_id: str | None
    voice_id: str | None
    title: str | None

    @model_validator(mode="after")
    def require_voice_deck(self) -> ThreadCreateInputDTO:
        if self.voice_id is not None and self.deck_id is None:
            raise ValueError("A selected Voice requires its Deck")
        return self


class ThreadIdInputDTO(ChatStrictDTO):
    thread_id: EntityId


class ThreadListInputDTO(ChatStrictDTO):
    deck_id: str | None
    limit: PositiveSafeInteger | None
    offset: NonnegativeSafeInteger


class ThreadSearchInputDTO(ChatStrictDTO):
    deck_id: str | None


class ThreadBindDeckInputDTO(ThreadIdInputDTO):
    deck_id: EntityId


class ThreadSelectVoiceInputDTO(ThreadBindDeckInputDTO):
    voice_id: EntityId
    expected_voice_id: str | None


class ThreadTitleInputDTO(ThreadIdInputDTO):
    title: str


class ThreadSessionInputDTO(ThreadIdInputDTO):
    claude_session_id: EntityId
    agent_contract_version: EntityId


class MessagePersistInputDTO(ThreadIdInputDTO):
    message_id: EntityId
    role: Literal["user", "assistant"]
    parts: list[JsonValue]
    metadata: dict[str, JsonValue] | None
    history_final_text: str | None
    history_process_available: bool
    history_projection_version: Literal[1] | None

    @field_validator("history_projection_version", mode="before")
    @classmethod
    def require_integer_projection_version(cls, value):
        if value is not None and type(value) is not int:
            raise ValueError("History projection version must be an integer")
        return value

    @model_validator(mode="after")
    def require_final_projection(self) -> MessagePersistInputDTO:
        validate_chat_history_final_projection(
            role=self.role, parts=self.parts, metadata=self.metadata,
            history_final_text=self.history_final_text,
            history_process_available=self.history_process_available,
            history_projection_version=self.history_projection_version,
        )
        return self


class MessageBeforeDTO(ChatStrictDTO):
    id: EntityId
    created_at: str | None
    _timestamp = field_validator("created_at")(validate_timestamp_text)


class MessagePageInputDTO(ThreadIdInputDTO):
    limit: int = Field(ge=1, le=100)
    before: MessageBeforeDTO | None


class MessageDetailInputDTO(ThreadIdInputDTO):
    message_id: EntityId


class ThreadResultDTO(ChatStrictDTO):
    thread: ChatThreadDTO | None


class ThreadCreateResultDTO(ChatStrictDTO):
    thread_id: EntityId
    deck_id: str | None
    voice_id: str | None


class ThreadListResultDTO(ChatStrictDTO):
    threads: list[ChatThreadSummaryDTO]


class ThreadSearchResultDTO(ChatStrictDTO):
    threads: list[ChatThreadSearchItemDTO]


class ChangedResultDTO(ChatStrictDTO):
    changed: bool


class MessagePersistResultDTO(ChatStrictDTO):
    message_id: EntityId


class MessageListResultDTO(ChatStrictDTO):
    messages: list[ChatMessageDTO]


class MessagePageResultDTO(MessageListResultDTO):
    has_more: bool
    latest_message_id: EntityId | None


class MessageDetailResultDTO(ChatStrictDTO):
    message: ChatMessageDTO | None


class LatestMessageResultDTO(ChatStrictDTO):
    message_id: EntityId | None
