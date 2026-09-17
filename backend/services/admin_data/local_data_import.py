# [Input] Registry101 local-data/first-login contracts, normalized legacy JSON text and current OAuth.
# [Output] Strict aggregate DTOs and two write consumers with original-receipt recovery.
# [Pos] Local-data Admin consumer; Dream parses localStorage while Admin owns validation and one-UOW persistence.
# [Sync] 2026-09-15: consume Admin c051a58e Registry101 without Dream PostgreSQL fallback.
"""Typed Registry101 consumer for local data import and first-login completion."""

from __future__ import annotations

from datetime import date
import json
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from .chat_models import (
    ChatStrictDTO,
    EntityId,
    NonnegativeSafeInteger,
    validate_timestamp_text,
)
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import CommittedReceiptDTO, OperationCapabilityDTO
from .workflow_data import require_workflow_capabilities


def _reject_json_constant(_value: str):
    raise ValueError("JSON constants are not supported")


def require_json_object_text(raw: str) -> str:
    try:
        value = json.loads(raw, parse_constant=_reject_json_constant)
    except (TypeError, ValueError, RecursionError):
        raise ValueError("Value must be JSON object text") from None
    if not isinstance(value, dict):
        raise ValueError("Value must be JSON object text")
    return raw


class LocalDataSessionDTO(ChatStrictDTO):
    id: EntityId
    name: str | None
    editor_state: str
    _json = field_validator("editor_state")(require_json_object_text)


class LocalDataPictureDTO(ChatStrictDTO):
    date: str
    image_base64: str = Field(min_length=1)
    prompt: str | None

    @field_validator("date")
    @classmethod
    def require_date(cls, value: str) -> str:
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            raise ValueError("Picture date is invalid") from None
        if parsed.isoformat() != value:
            raise ValueError("Picture date must be canonical ISO text")
        return value


class LocalDataPreferencesDTO(ChatStrictDTO):
    voice_configs: str | None
    meta_prompt: str | None
    state_config: str | None
    selected_state: str | None

    @field_validator("voice_configs", "state_config")
    @classmethod
    def require_optional_json_object(cls, value: str | None) -> str | None:
        return require_json_object_text(value) if value is not None else None


class LocalDataReportDTO(ChatStrictDTO):
    type: EntityId
    data: str
    all_notes: str
    timestamp: str
    _json = field_validator("data")(require_json_object_text)
    _timestamp = field_validator("timestamp")(validate_timestamp_text)


class LocalDataImportInputDTO(ChatStrictDTO):
    sessions: list[LocalDataSessionDTO]
    pictures: list[LocalDataPictureDTO]
    preferences: LocalDataPreferencesDTO | None
    reports: list[LocalDataReportDTO]

    @model_validator(mode="after")
    def require_unique_session_ids(self):
        session_ids = [item.id for item in self.sessions]
        if len(session_ids) != len(set(session_ids)):
            raise ValueError("Session identifiers must be unique")
        return self


class LocalDataImportCountsDTO(ChatStrictDTO):
    sessions: NonnegativeSafeInteger
    pictures: NonnegativeSafeInteger
    preferences: Annotated[int, Field(ge=0, le=4)]
    reports: NonnegativeSafeInteger

    @field_validator("preferences", mode="before")
    @classmethod
    def require_integer_count(cls, value):
        if type(value) is not int:
            raise ValueError("Preference count must be an integer")
        return value


class LocalDataImportOutputDTO(ChatStrictDTO):
    success: Literal[True]
    imported: LocalDataImportCountsDTO


class FirstLoginCompleteInputDTO(ChatStrictDTO):
    pass


class FirstLoginCompleteOutputDTO(ChatStrictDTO):
    success: Literal[True]
    first_login_completed: Literal[1]

    @field_validator("first_login_completed", mode="before")
    @classmethod
    def require_one_integer(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("First login completion must be integer one")
        return value


IMPORT_LOCAL_DATA = DomainOperation(
    OperationCapabilityDTO(
        name="local-data.import",
        kind="write",
        user_scope="dream:write",
        background_scope=None,
        input_schema_version=1,
        output_schema_version=1,
        contract_sha256="f2f13ac392be415b42bb9532d42e20bf04fef2400551cd2f528991f4f6de271d",
    ),
    LocalDataImportInputDTO,
    LocalDataImportOutputDTO,
)
COMPLETE_FIRST_LOGIN = DomainOperation(
    OperationCapabilityDTO(
        name="first-login.complete",
        kind="write",
        user_scope="dream:write",
        background_scope=None,
        input_schema_version=1,
        output_schema_version=1,
        contract_sha256="f06bbfd87fd905139b40df61eccdda6726678adda304dcd141a0bf52cf874cb0",
    ),
    FirstLoginCompleteInputDTO,
    FirstLoginCompleteOutputDTO,
)
LOCAL_DATA_IMPORT_OPERATIONS = (IMPORT_LOCAL_DATA, COMPLETE_FIRST_LOGIN)


class AdminLocalDataImportData:
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

    def _write(self, operation, input_dto, request_id: str, access_token: str):
        try:
            return self._execute(operation, input_dto, request_id, access_token)
        except AdminDataError as error:
            if not error.outcome_unknown:
                raise
        try:
            receipt = self._client.receipt(
                operation,
                request_id,
                access_token=access_token,
            )
        except AdminDataError as error:
            raise AdminDataError(
                error.code,
                error.status_code,
                request_id,
                True,
                error.details,
            ) from None
        if not isinstance(receipt, CommittedReceiptDTO):
            raise AdminDataError(
                "ADMIN_WRITE_RESULT_UNKNOWN",
                503,
                request_id,
                True,
            )
        if type(receipt.result) is not operation.output_dto:
            raise invalid_response(request_id, write=True)
        return receipt.result

    def import_data(
        self,
        input_dto: LocalDataImportInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> LocalDataImportOutputDTO:
        return self._write(
            IMPORT_LOCAL_DATA,
            input_dto,
            request_id,
            access_token,
        )

    def complete_first_login(
        self,
        input_dto: FirstLoginCompleteInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> FirstLoginCompleteOutputDTO:
        return self._write(
            COMPLETE_FIRST_LOGIN,
            input_dto,
            request_id,
            access_token,
        )
