# [Input] Published Reflections section-config DTOs, exact schemas and current request OAuth.
# [Output] Closed get/save/delete operations with raw JSON and original write receipt recovery.
# [Pos] Reflections custom-config data consumer; defaults, display, filtering, Agent and filesystem remain in Dream.
# [Sync] 2026-09-15: recover unknown writes from the original Admin receipt without a second POST.
# [Sync] 2026-09-15: consume registered83 section config contracts without Dream database fallback.
"""Typed Admin operations for user-owned Reflections prompt configuration."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import Field, field_validator

from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import CommittedReceiptDTO, OperationCapabilityDTO, StrictDTO
from .workflow_data import require_workflow_capabilities


ReflectionsSection = Literal["echoes", "traits", "patterns"]
PROMPT_FILE_NAMES = frozenset({
    "WORKFLOW.md",
    "MEMORY_QUERY_PROMPT.md",
    "MEMORY_Distiller_PROMPT.md",
    "MEMORY_ANSWER_PROMPT.md",
    "DEFAULT_UPDATE_MEMORY_PROMPT.md",
})


def decode_prompt_files(
    raw: str | None,
    request_id: str | None = None,
) -> dict[str, Any] | None:
    if raw is None:
        return None
    try:
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("Prompt configuration must be an object")
    except (TypeError, ValueError, RecursionError):
        raise invalid_response(request_id) from None
    return value


class ReflectionsSectionInputDTO(StrictDTO):
    section: ReflectionsSection


class ReflectionsSectionSaveInputDTO(ReflectionsSectionInputDTO):
    prompt_files_json: str = Field(min_length=1)

    @field_validator("prompt_files_json")
    @classmethod
    def validate_prompt_files(cls, raw: str) -> str:
        value = decode_prompt_files(raw)
        if not value:
            raise ValueError("Prompt configuration must not be empty")
        for name, content in value.items():
            if (
                name not in PROMPT_FILE_NAMES
                or not isinstance(content, str)
                or not content
                or content.strip() != content
            ):
                raise ValueError("Invalid prompt configuration")
        return raw


class ReflectionsSectionGetOutputDTO(StrictDTO):
    prompt_files_json: str | None

    def prompt_files(self, request_id: str) -> dict[str, Any] | None:
        return decode_prompt_files(self.prompt_files_json, request_id)


class ReflectionsSectionSavedDTO(StrictDTO):
    saved: Literal[True]

    @field_validator("saved", mode="before")
    @classmethod
    def require_true_bool(cls, value):
        if value is not True:
            raise ValueError("Reflections configuration was not saved")
        return value


class ReflectionsSectionDeletedDTO(StrictDTO):
    deleted: bool

    @field_validator("deleted", mode="before")
    @classmethod
    def require_bool(cls, value):
        if type(value) is not bool:
            raise ValueError("Reflections deletion result must be boolean")
        return value


GET_REFLECTIONS_SECTION_CONFIG = DomainOperation(
    OperationCapabilityDTO(
        name="reflections-section-config.get",
        kind="read",
        user_scope="dream:read",
        background_scope=None,
        input_schema_version=1,
        output_schema_version=1,
        contract_sha256="2e1057f1cdd9248c2dbd603057310399e7ea5a51c90c601405ebb86868ccb640",
    ),
    ReflectionsSectionInputDTO,
    ReflectionsSectionGetOutputDTO,
)
SAVE_REFLECTIONS_SECTION_CONFIG = DomainOperation(
    OperationCapabilityDTO(
        name="reflections-section-config.save",
        kind="write",
        user_scope="dream:write",
        background_scope=None,
        input_schema_version=1,
        output_schema_version=1,
        contract_sha256="dc2ba4ee442618b4fd39d75b8ddf9ca834b25913d85e4bee0cba76d20b4b047f",
    ),
    ReflectionsSectionSaveInputDTO,
    ReflectionsSectionSavedDTO,
)
DELETE_REFLECTIONS_SECTION_CONFIG = DomainOperation(
    OperationCapabilityDTO(
        name="reflections-section-config.delete",
        kind="write",
        user_scope="dream:write",
        background_scope=None,
        input_schema_version=1,
        output_schema_version=1,
        contract_sha256="8b03792f711e79c1d12343a93980da91d7675d280f9713ab454e6369b2b45967",
    ),
    ReflectionsSectionInputDTO,
    ReflectionsSectionDeletedDTO,
)
REFLECTIONS_SECTION_CONFIG_OPERATIONS = (
    GET_REFLECTIONS_SECTION_CONFIG,
    SAVE_REFLECTIONS_SECTION_CONFIG,
    DELETE_REFLECTIONS_SECTION_CONFIG,
)


class AdminReflectionsSectionConfigData:
    def __init__(self, client: AdminDataClient):
        self._client = client

    def _execute(self, operation, input_dto, request_id: str, access_token: str):
        require_workflow_capabilities(self._client, request_id)
        return self._client.execute(
            operation,
            input_dto,
            request_id,
            access_token=access_token,
        )

    def get(
        self,
        input_dto: ReflectionsSectionInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> dict[str, Any] | None:
        result = self._execute(
            GET_REFLECTIONS_SECTION_CONFIG,
            input_dto,
            request_id,
            access_token,
        )
        return result.prompt_files(request_id)

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

    def save(
        self,
        input_dto: ReflectionsSectionSaveInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> ReflectionsSectionSavedDTO:
        return self._write(
            SAVE_REFLECTIONS_SECTION_CONFIG,
            input_dto,
            request_id,
            access_token,
        )

    def delete(
        self,
        input_dto: ReflectionsSectionInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> ReflectionsSectionDeletedDTO:
        return self._write(
            DELETE_REFLECTIONS_SECTION_CONFIG,
            input_dto,
            request_id,
            access_token,
        )
