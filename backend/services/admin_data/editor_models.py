# [Sync] 2026-09-15: reuse present-fields serialization; Editor optional-null validation remains domain-owned.
# [Input] Actual Admin editorSessionDto.ts and existing strict JSON/time validators.
# [Output] Closed EditorEngine state DTOs shared by Session HTTP and future Editor delegation consumers.
# [Pos] Editor business schema boundary; no database entities or editor mutation algorithm.
# [Sync] 2026-09-15: preserve optional wire fields, finite numbers and precise ISO timestamps.
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, JsonValue, field_validator, model_validator

from .chat_models import PresentFieldsDTO, EntityId, validate_timestamp_text

Number = int | float


class EditorDTO(PresentFieldsDTO):
    @model_validator(mode="before")
    @classmethod
    def reject_null_optional_fields(cls, value):
        if isinstance(value, dict):
            for key, item in value.items():
                field = cls.model_fields.get(key)
                if field is not None and not field.is_required() and item is None and key != "selectedState":
                    raise ValueError("Optional Editor field cannot be null")
        return value


class EditorTextCellDTO(EditorDTO):
    id: EntityId
    type: Literal["text"]
    content: str


class EditorWidgetCellDTO(EditorDTO):
    id: EntityId
    type: Literal["widget"]
    widgetType: Literal["chat", "greeting", "other"]
    data: JsonValue


class EditorSuggestionAnchorDTO(EditorDTO):
    textCellId: EntityId
    textSnapshot: str


class EditorSuggestionErrorDTO(EditorDTO):
    code: str
    message: str
    retryable: bool


class EditorSuggestionCellDTO(EditorDTO):
    id: EntityId
    type: Literal["writing-suggestion"]
    content: str
    status: Literal["idle", "streaming", "completed", "failed"]
    anchor: EditorSuggestionAnchorDTO
    createdAt: str
    updatedAt: str
    error: EditorSuggestionErrorDTO | None = None
    requestId: str | None = None
    previousContent: str | None = None
    _timestamps = field_validator("createdAt", "updatedAt")(validate_timestamp_text)


EditorCell = Annotated[EditorTextCellDTO | EditorWidgetCellDTO | EditorSuggestionCellDTO, Field(discriminator="type")]


class EditorCommentMessageDTO(EditorDTO):
    role: Literal["assistant", "user"]
    content: str
    timestamp: Number


class EditorCommentorDTO(EditorDTO):
    id: EntityId
    phrase: str
    comment: str
    voiceId: str | None = None
    voice: str
    icon: str
    color: str
    appliedAt: Number | None = None
    computedAt: Number
    textSnapshot: str
    chatHistory: list[EditorCommentMessageDTO] | None = None
    feedback: Literal["star", "kill"] | None = None


class EditorTaskDTO(EditorDTO):
    id: EntityId
    type: Literal["searching", "thinking", "other"]
    message: str
    startedAt: Number
    completedAt: Number | None = None


class EditorWeightDTO(EditorDTO):
    timestamp: Number
    text: str
    weight: Number
    delta: Number
    energy: Number


class EditorStateDTO(EditorDTO):
    id: EntityId
    cells: list[EditorCell]
    commentors: list[EditorCommentorDTO]
    tasks: list[EditorTaskDTO]
    weightPath: list[EditorWeightDTO]
    overlappedPhrases: list[str]
    notFoundPhrases: list[str]
    writingThreadId: EntityId | None = None
    selectedState: str | None = None
    createdAt: str | None = None
    _timestamp = field_validator("createdAt")(validate_timestamp_text)
