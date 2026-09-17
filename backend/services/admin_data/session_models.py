# [Input] Actual Admin Session DTO and reusable EditorEngine state business schema.
# [Output] Six closed Session operation inputs/results with required nullable fields and exact timestamps.
# [Pos] Writing Session wire projections; metrics and event streaming remain in Dream.
# [Sync] 2026-09-15: preserve session IDs, UTC date ranges and existing metadata/full-state projections.
from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from .chat_models import ChatStrictDTO, EntityId, validate_timestamp_text
from .editor_models import EditorStateDTO

DateText = Annotated[str, Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")]


def validate_date_text(value):
    if value is not None:
        date.fromisoformat(value)
    return value


class SessionIdInputDTO(ChatStrictDTO):
    session_id: EntityId


class SessionSaveInputDTO(SessionIdInputDTO):
    editor_state: EditorStateDTO
    name: str | None
    labels: list[str] | None
    created_at: str | None
    _timestamp = field_validator("created_at")(validate_timestamp_text)

    @model_validator(mode="after")
    def require_state_identity(self):
        if self.editor_state.id != self.session_id:
            raise ValueError("Editor state ID does not match Session")
        return self


class SessionBatchInputDTO(ChatStrictDTO):
    session_ids: list[EntityId]


class SessionListInputDTO(ChatStrictDTO):
    start_date: DateText | None
    end_date: DateText | None
    include_text: bool
    _dates = field_validator("start_date", "end_date")(validate_date_text)


class SessionTextListInputDTO(ChatStrictDTO):
    pass


class SessionMetadataDTO(ChatStrictDTO):
    id: EntityId
    name: str | None
    labels: list[str]
    created_at: str | None
    updated_at: str | None
    _timestamps = field_validator("created_at", "updated_at")(validate_timestamp_text)


class SessionDTO(SessionMetadataDTO):
    editor_state: EditorStateDTO

    @model_validator(mode="after")
    def require_state_identity(self):
        if self.editor_state.id != self.id:
            raise ValueError("Editor state ID does not match Session")
        return self


class SessionPreviewDTO(SessionMetadataDTO):
    first_line: str
    text: str | None


class SessionTextDTO(ChatStrictDTO):
    id: EntityId
    name: str | None
    created_at: str | None
    updated_at: str | None
    text: str | None
    _timestamps = field_validator("created_at", "updated_at")(validate_timestamp_text)


class SessionResultDTO(ChatStrictDTO):
    session: SessionDTO | None


class SessionSavedDTO(ChatStrictDTO):
    session: SessionDTO


class SessionBatchResultDTO(ChatStrictDTO):
    sessions: list[SessionDTO]


class SessionListResultDTO(ChatStrictDTO):
    sessions: list[SessionPreviewDTO]


class SessionTextListResultDTO(ChatStrictDTO):
    sessions: list[SessionTextDTO]


class SessionDeletedDTO(ChatStrictDTO):
    deleted: Literal[True]

    @field_validator("deleted", mode="before")
    @classmethod
    def require_true_boolean(cls, value):
        if value is not True:
            raise ValueError("Delete result must be true")
        return value
