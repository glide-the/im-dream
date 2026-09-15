# [Input] Registry122-126 binding contract, current OAuth bearer and default Workspace identity.
# [Output] Strict owner-bound binding state/history/options/validation/save DTOs and receipt recovery.
# [Pos] Dream consumer; SQL, ORM, compatibility facts, CAS and transactions stay in Admin.
# [Sync] 2026-09-16: replace five public Deck Plugin binding database paths.
"""Typed Admin client for Deck Plugin binding operations."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from .chat_models import ChatStrictDTO
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import (
    BindingRevisionConflictDetailsDTO,
    BindingSelectionRecoveryDTO,
    BindingSelectionRejectedDetailsDTO,
    BindingSelectionSummaryDTO,
    CommittedReceiptDTO,
    OperationCapabilityDTO,
)
from .workflow_data import require_workflow_capabilities

Identifier = Annotated[str, Field(min_length=1)]
PluginId = Annotated[str, Field(min_length=3)]
PluginVersion = Annotated[str, Field(min_length=5)]
BindingId = Annotated[str, Field(pattern=r"^dpb_[0-9a-f]{32}$")]
Revision = Annotated[int, Field(ge=0, le=9_007_199_254_740_991)]
PositiveRevision = Annotated[int, Field(ge=1, le=9_007_199_254_740_991)]


class BindingScopeInputDTO(ChatStrictDTO):
    deck_id: Identifier
    workspace_id: Identifier


class BindingHistoryInputDTO(BindingScopeInputDTO):
    limit: Annotated[int, Field(ge=1, le=100)]


class BindingSelectionInputDTO(BindingScopeInputDTO):
    deck_plugin_id: PluginId
    deck_plugin_version: PluginVersion
    apply_to: Literal["next_run"] = "next_run"


class BindingSaveInputDTO(BindingSelectionInputDTO):
    expected_binding_revision: Revision


class BindingResponseDTO(ChatStrictDTO):
    deck_plugin_binding_id: BindingId
    deck_id: Identifier
    deck_plugin_id: PluginId
    deck_plugin_version: PluginVersion
    binding_revision: PositiveRevision
    status: Literal["active", "stale"]
    applied_to: Literal["next_run"]
    selection_validation_summary: BindingSelectionSummaryDTO


class BindingStateDTO(ChatStrictDTO):
    deck_id: Identifier
    binding_revision: Revision
    applied_to: Literal["next_run"]
    binding: BindingResponseDTO | None

    @model_validator(mode="after")
    def bind_identity(self):
        if self.binding is not None and (
            self.binding.deck_id != self.deck_id
            or self.binding.binding_revision != self.binding_revision
        ):
            raise ValueError("Binding state identity mismatch")
        return self


class BindingHistoryEntryDTO(ChatStrictDTO):
    deck_plugin_binding_id: BindingId
    deck_plugin_id: PluginId
    deck_plugin_version: PluginVersion
    binding_revision: PositiveRevision
    status: Literal["active", "stale"]
    applied_to: Literal["next_run"]
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Binding timestamp requires timezone")
        return value


class BindingHistoryDTO(ChatStrictDTO):
    deck_id: Identifier
    current_binding_revision: Revision
    entries: list[BindingHistoryEntryDTO]

    @model_validator(mode="after")
    def require_descending_unique_revisions(self):
        revisions = [entry.binding_revision for entry in self.entries]
        if revisions != sorted(set(revisions), reverse=True):
            raise ValueError("Binding history revisions must be unique and descending")
        if revisions and revisions[0] > self.current_binding_revision:
            raise ValueError("Binding history exceeds current revision")
        return self


class BindingOptionDTO(ChatStrictDTO):
    display_name: str
    deck_plugin_id: PluginId
    deck_plugin_version: PluginVersion
    release_status: Identifier
    installation_status: Identifier
    compatibility: Literal["passed", "failed", "unknown"]
    runtime_readiness: Identifier
    selectable: bool
    reason_code: Identifier | None
    recovery: BindingSelectionRecoveryDTO | None
    capability_summary: list[str]

    @model_validator(mode="after")
    def validate_summary_fields(self):
        BindingSelectionSummaryDTO.model_validate({
            "selectable": self.selectable,
            "release_status": self.release_status,
            "installation_status": self.installation_status,
            "compatibility": self.compatibility,
            "runtime_readiness": self.runtime_readiness,
            "reason_code": self.reason_code,
            "recovery": self.recovery,
            "capability_summary": self.capability_summary,
        })
        return self


class BindingOptionsDTO(ChatStrictDTO):
    deck_id: Identifier
    applied_to: Literal["next_run"]
    options: list[BindingOptionDTO]


class BindingValidationDTO(ChatStrictDTO):
    deck_id: Identifier
    deck_plugin_id: PluginId
    deck_plugin_version: PluginVersion
    applied_to: Literal["next_run"]
    validation: BindingSelectionSummaryDTO


def _operation(name, kind, input_dto, output_dto, hash_value):
    return DomainOperation(
        OperationCapabilityDTO(
            name=name,
            kind=kind,
            user_scope="dream:read" if kind == "read" else "dream:write",
            background_scope=None,
            input_schema_version=1,
            output_schema_version=1,
            contract_sha256=hash_value,
        ),
        input_dto,
        output_dto,
    )


READ_BINDING = _operation("deck-plugin-binding.current", "read", BindingScopeInputDTO, BindingStateDTO, "4b66af7888ed17e16f7e7aa38aded821ad3ecfe148663001dd6c4a66c714fb93")
READ_BINDING_HISTORY = _operation("deck-plugin-binding.history", "read", BindingHistoryInputDTO, BindingHistoryDTO, "568bb2ad097382510919eb230e20b1e7d5e6e2dfd9c66c83384cbf3e52ede0e8")
LIST_BINDING_OPTIONS = _operation("deck-plugin-binding.options", "read", BindingScopeInputDTO, BindingOptionsDTO, "aca3a55ce01d9e7754d5cd9be07320cb4240d3d26928c8ff24ba3ea9675fa770")
VALIDATE_BINDING = _operation("deck-plugin-binding.validate", "read", BindingSelectionInputDTO, BindingValidationDTO, "55fc0175170183fc1d5fc5162ef6be15bb863ef43261902c8edda5614bbcdb70")
SAVE_BINDING = _operation("deck-plugin-binding.save", "write", BindingSaveInputDTO, BindingResponseDTO, "cf91b567af3ae207d0c009947d98fb0dcb2335d3abcbf7e8194f95a02ceeddb2")
DECK_PLUGIN_BINDING_OPERATIONS = (
    READ_BINDING,
    READ_BINDING_HISTORY,
    LIST_BINDING_OPTIONS,
    VALIDATE_BINDING,
    SAVE_BINDING,
)


class AdminDeckPluginBindingData:
    def __init__(self, client: AdminDataClient):
        self._client = client

    @staticmethod
    def _validate_identity(input_dto, result, request_id: str, *, write: bool = False):
        if result.deck_id != input_dto.deck_id:
            raise invalid_response(request_id, write=write)
        if isinstance(input_dto, BindingSelectionInputDTO) and (
            result.deck_plugin_id != input_dto.deck_plugin_id
            or result.deck_plugin_version != input_dto.deck_plugin_version
            or result.applied_to != input_dto.apply_to
        ):
            raise invalid_response(request_id, write=write)
        return result

    def _execute(self, operation, input_dto, request_id: str, access_token: str):
        require_workflow_capabilities(self._client, request_id)
        result = self._client.execute(operation, input_dto, request_id, access_token=access_token)
        return self._validate_identity(input_dto, result, request_id, write=operation is SAVE_BINDING)

    def current(self, input_dto: BindingScopeInputDTO, request_id: str, *, access_token: str):
        return self._execute(READ_BINDING, input_dto, request_id, access_token)

    def history(self, input_dto: BindingHistoryInputDTO, request_id: str, *, access_token: str):
        return self._execute(READ_BINDING_HISTORY, input_dto, request_id, access_token)

    def options(self, input_dto: BindingScopeInputDTO, request_id: str, *, access_token: str):
        return self._execute(LIST_BINDING_OPTIONS, input_dto, request_id, access_token)

    def validate(self, input_dto: BindingSelectionInputDTO, request_id: str, *, access_token: str):
        return self._execute(VALIDATE_BINDING, input_dto, request_id, access_token)

    def save(self, input_dto: BindingSaveInputDTO, request_id: str, *, access_token: str):
        try:
            return self._execute(SAVE_BINDING, input_dto, request_id, access_token)
        except AdminDataError as error:
            if not error.outcome_unknown:
                raise
        try:
            receipt = self._client.receipt(SAVE_BINDING, request_id, access_token=access_token)
        except AdminDataError as error:
            raise AdminDataError(error.code, error.status_code, request_id, True, error.details) from None
        if not isinstance(receipt, CommittedReceiptDTO):
            raise AdminDataError("ADMIN_WRITE_RESULT_UNKNOWN", 503, request_id, True)
        return self._validate_identity(input_dto, receipt.result, request_id, write=True)
