# [Input] Registry103 current-user picture-history contracts and current request OAuth.
# [Output] Strict list/full DTOs and capability-gated read consumers.
# [Pos] Picture-history Admin consumer; Admin owns actor scoping, ordering and image selection.
# [Sync] 2026-09-15: consume Admin 547e898 Registry103 without Dream PostgreSQL fallback.
"""Typed Registry103 consumer for current-user picture history reads."""

from __future__ import annotations

from datetime import date

from pydantic import field_validator

from .chat_models import (
    ChatStrictDTO,
    NonnegativeSafeInteger,
    validate_timestamp_text,
)
from .client import AdminDataClient, DomainOperation
from .models import OperationCapabilityDTO
from .workflow_data import require_workflow_capabilities


def require_iso_date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError("Date must be valid YYYY-MM-DD text") from None
    if parsed.isoformat() != value:
        raise ValueError("Date must be canonical YYYY-MM-DD text")
    return value


class PictureHistoryListInputDTO(ChatStrictDTO):
    start_date: str | None
    end_date: str | None
    limit: NonnegativeSafeInteger

    @field_validator("start_date", "end_date")
    @classmethod
    def require_optional_date(cls, value: str | None) -> str | None:
        return require_iso_date(value) if value is not None else None


class PictureHistoryFullInputDTO(ChatStrictDTO):
    date: str
    _date = field_validator("date")(require_iso_date)


class PictureHistoryItemDTO(ChatStrictDTO):
    date: str
    base64: str
    prompt: str | None
    created_at: str | None
    _timestamp = field_validator("created_at")(validate_timestamp_text)


class PictureHistoryListOutputDTO(ChatStrictDTO):
    pictures: list[PictureHistoryItemDTO]


class PictureHistoryFullOutputDTO(ChatStrictDTO):
    image_base64: str | None


LIST_PICTURE_HISTORY = DomainOperation(
    OperationCapabilityDTO(
        name="picture-history.list",
        kind="read",
        user_scope="dream:read",
        background_scope=None,
        input_schema_version=1,
        output_schema_version=1,
        contract_sha256="d03993f15860caadba56b6788a4c1b1d0fa086e949f1831b6e805a2eabee028d",
    ),
    PictureHistoryListInputDTO,
    PictureHistoryListOutputDTO,
)
READ_PICTURE_FULL = DomainOperation(
    OperationCapabilityDTO(
        name="picture-history.full",
        kind="read",
        user_scope="dream:read",
        background_scope=None,
        input_schema_version=1,
        output_schema_version=1,
        contract_sha256="e35e76d3425641660da361f2671f0004042a3600b2f3d4072386233c0d90efa3",
    ),
    PictureHistoryFullInputDTO,
    PictureHistoryFullOutputDTO,
)
PICTURE_HISTORY_OPERATIONS = (LIST_PICTURE_HISTORY, READ_PICTURE_FULL)


class AdminPictureHistoryData:
    def __init__(self, client: AdminDataClient) -> None:
        self._client = client

    def _execute(self, operation, input_dto, request_id: str, access_token: str):
        require_workflow_capabilities(self._client, request_id)
        return self._client.execute(
            operation,
            input_dto,
            request_id,
            access_token=access_token,
        )

    def list(
        self,
        input_dto: PictureHistoryListInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> PictureHistoryListOutputDTO:
        return self._execute(
            LIST_PICTURE_HISTORY,
            input_dto,
            request_id,
            access_token,
        )

    def full(
        self,
        input_dto: PictureHistoryFullInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> PictureHistoryFullOutputDTO:
        return self._execute(
            READ_PICTURE_FULL,
            input_dto,
            request_id,
            access_token,
        )
