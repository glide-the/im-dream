# [Input] Registry122-132 binding/Agent-type/launch contracts, current OAuth bearer and default Workspace identity.
# [Output] Strict owner-bound binding and current/frozen Runtime DTOs with receipt recovery.
# [Pos] Dream consumer; SQL, ORM, Runtime metadata, CAS and transactions stay in Admin.
# [Sync] 2026-09-16: add launch scope plus current/replay Runtime plan and preparation.
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
Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
RuntimeLockId = Annotated[str, Field(pattern=r"^rpl_[0-9a-f]{32}$")]
WorkflowRunId = Annotated[str, Field(pattern=r"^run_[0-9a-f]{32}$")]


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


class BindingClearInputDTO(BindingScopeInputDTO):
    expected_binding_revision: Revision


class AgentTypeRuntimeCandidateDTO(ChatStrictDTO):
    deck_plugin_id: PluginId
    deck_plugin_version: PluginVersion
    runtime_plugin_lock_id: RuntimeLockId
    plugin_installation_id: Identifier
    package_spec: Identifier
    package_name: Identifier
    marketplace: Identifier
    resolved_version: PluginVersion
    artifact_digest: Digest
    compatibility_json: str


class AgentTypeRuntimePlanDTO(ChatStrictDTO):
    deck_id: Identifier
    current_binding_revision: Revision
    target: AgentTypeRuntimeCandidateDTO


class AgentTypeVerifiedPluginDTO(ChatStrictDTO):
    plugin_installation_id: Identifier
    package_spec: Identifier
    resolved_version: PluginVersion
    artifact_digest: Digest
    has_manifest: Literal[True]


class AgentTypeRuntimePrepareInputDTO(BindingScopeInputDTO):
    expected_binding_revision: Revision
    verified_plugin: AgentTypeVerifiedPluginDTO


class AgentTypeRuntimePreparedDTO(ChatStrictDTO):
    deck_id: Identifier
    deck_plugin_id: PluginId
    deck_plugin_version: PluginVersion
    current_binding_revision: Revision
    runtime_ready: Literal[True]


class AgentTypeChatDTO(ChatStrictDTO):
    deck_id: Identifier
    agent_type: Literal["chat"]
    binding_revision: Revision


class DreamLaunchRuntimeScopeInputDTO(BindingScopeInputDTO):
    agent_id: Identifier | None


class DreamLaunchRuntimeScopeDTO(DreamLaunchRuntimeScopeInputDTO):
    authorized: Literal[True]


class DreamLaunchRuntimePlanInputDTO(DreamLaunchRuntimeScopeInputDTO):
    mode: Literal["current", "replay"]
    workflow_run_id: WorkflowRunId | None
    thread_id: Identifier | None

    @model_validator(mode="after")
    def require_mode_identity(self):
        replay = self.workflow_run_id is not None and self.thread_id is not None
        if (
            (self.mode == "current" and (self.workflow_run_id is not None or self.thread_id is not None))
            or (self.mode == "replay" and not replay)
        ):
            raise ValueError("Launch Runtime mode and replay identity must match")
        return self


class DreamLaunchRuntimeBindingDTO(ChatStrictDTO):
    deck_plugin_binding_id: BindingId
    deck_plugin_id: PluginId
    deck_plugin_version: PluginVersion
    binding_revision: PositiveRevision


class DreamLaunchRuntimePlanDTO(DreamLaunchRuntimePlanInputDTO):
    binding: DreamLaunchRuntimeBindingDTO
    target: AgentTypeRuntimeCandidateDTO


class DreamLaunchRuntimePrepareInputDTO(DreamLaunchRuntimePlanInputDTO):
    expected_binding_revision: PositiveRevision
    verified_plugin: AgentTypeVerifiedPluginDTO


class DreamLaunchRuntimePreparedDTO(DreamLaunchRuntimePlanInputDTO):
    binding: DreamLaunchRuntimeBindingDTO
    runtime_ready: Literal[True]


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
CLEAR_BINDING = _operation("deck-plugin-binding.clear", "write", BindingClearInputDTO, AgentTypeChatDTO, "9a89ec380e280fc64b67b9725a68edf3244df0f76e41df8db5fd89b3e3fd44fc")
PLAN_AGENT_TYPE_RUNTIME = _operation("deck-agent-type.runtime-plan", "read", BindingScopeInputDTO, AgentTypeRuntimePlanDTO, "87a3f0497e3927aa8c8048e6bc79de1b042631f096f85184568201dce378e5f7")
PREPARE_AGENT_TYPE_RUNTIME = _operation("deck-agent-type.runtime-prepare", "write", AgentTypeRuntimePrepareInputDTO, AgentTypeRuntimePreparedDTO, "9cc1a08d15e0279ed977bb5b7ee25a5ab270cf32a4f67ded719c23e33d000716")
AUTHORIZE_DREAM_LAUNCH_RUNTIME = _operation("dream-launch.runtime-scope", "read", DreamLaunchRuntimeScopeInputDTO, DreamLaunchRuntimeScopeDTO, "67dbe0a6eb7ddfd9bd1fa668e38f143add53201b725b19506af976319bba2b92")
PLAN_DREAM_LAUNCH_RUNTIME = _operation("dream-launch.runtime-plan", "read", DreamLaunchRuntimePlanInputDTO, DreamLaunchRuntimePlanDTO, "efd986cef6f891202c4d3ceb889d7491e8227dc097eeb009202a2be92549e9a6")
PREPARE_DREAM_LAUNCH_RUNTIME = _operation("dream-launch.runtime-prepare", "write", DreamLaunchRuntimePrepareInputDTO, DreamLaunchRuntimePreparedDTO, "d9c2faeb03b86cf562286f283e5bfcd3098e1da81c1b628c2e9aaa5a7b897882")
DECK_PLUGIN_BINDING_OPERATIONS = (
    READ_BINDING,
    READ_BINDING_HISTORY,
    LIST_BINDING_OPTIONS,
    VALIDATE_BINDING,
    SAVE_BINDING,
    CLEAR_BINDING,
    PLAN_AGENT_TYPE_RUNTIME,
    PREPARE_AGENT_TYPE_RUNTIME,
    AUTHORIZE_DREAM_LAUNCH_RUNTIME,
    PLAN_DREAM_LAUNCH_RUNTIME,
    PREPARE_DREAM_LAUNCH_RUNTIME,
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
        if isinstance(input_dto, BindingClearInputDTO) and (
            result.agent_type != "chat"
            or result.binding_revision != input_dto.expected_binding_revision
        ):
            raise invalid_response(request_id, write=write)
        if isinstance(input_dto, AgentTypeRuntimePrepareInputDTO) and (
            result.current_binding_revision != input_dto.expected_binding_revision
        ):
            raise invalid_response(request_id, write=write)
        if isinstance(input_dto, DreamLaunchRuntimeScopeInputDTO) and (
            result.deck_id != input_dto.deck_id
            or result.workspace_id != input_dto.workspace_id
            or result.agent_id != input_dto.agent_id
        ):
            raise invalid_response(request_id, write=write)
        if isinstance(input_dto, DreamLaunchRuntimePlanInputDTO) and (
            result.mode != input_dto.mode
            or result.workflow_run_id != input_dto.workflow_run_id
            or result.thread_id != input_dto.thread_id
        ):
            raise invalid_response(request_id, write=write)
        if isinstance(input_dto, DreamLaunchRuntimePrepareInputDTO) and (
            result.binding.binding_revision != input_dto.expected_binding_revision
        ):
            raise invalid_response(request_id, write=write)
        return result

    def _execute(self, operation, input_dto, request_id: str, access_token: str):
        require_workflow_capabilities(self._client, request_id)
        result = self._client.execute(operation, input_dto, request_id, access_token=access_token)
        return self._validate_identity(
            input_dto,
            result,
            request_id,
            write=operation.capability.kind == "write",
        )

    def _write(self, operation, input_dto, request_id: str, access_token: str):
        try:
            return self._execute(operation, input_dto, request_id, access_token)
        except AdminDataError as error:
            if not error.outcome_unknown:
                raise
        try:
            receipt = self._client.receipt(
                operation, request_id, access_token=access_token
            )
        except AdminDataError as error:
            raise AdminDataError(
                error.code,
                error.status_code,
                request_id,
                True,
                error.details,
            ) from None
        if (
            not isinstance(receipt, CommittedReceiptDTO)
            or type(receipt.result) is not operation.output_dto
        ):
            raise AdminDataError(
                "ADMIN_WRITE_RESULT_UNKNOWN", 503, request_id, True
            )
        return self._validate_identity(
            input_dto, receipt.result, request_id, write=True
        )

    def current(self, input_dto: BindingScopeInputDTO, request_id: str, *, access_token: str):
        return self._execute(READ_BINDING, input_dto, request_id, access_token)

    def history(self, input_dto: BindingHistoryInputDTO, request_id: str, *, access_token: str):
        return self._execute(READ_BINDING_HISTORY, input_dto, request_id, access_token)

    def options(self, input_dto: BindingScopeInputDTO, request_id: str, *, access_token: str):
        return self._execute(LIST_BINDING_OPTIONS, input_dto, request_id, access_token)

    def validate(self, input_dto: BindingSelectionInputDTO, request_id: str, *, access_token: str):
        return self._execute(VALIDATE_BINDING, input_dto, request_id, access_token)

    def save(self, input_dto: BindingSaveInputDTO, request_id: str, *, access_token: str):
        return self._write(SAVE_BINDING, input_dto, request_id, access_token)

    def clear(self, input_dto: BindingClearInputDTO, request_id: str, *, access_token: str):
        return self._write(CLEAR_BINDING, input_dto, request_id, access_token)

    def runtime_plan(self, input_dto: BindingScopeInputDTO, request_id: str, *, access_token: str):
        return self._execute(
            PLAN_AGENT_TYPE_RUNTIME, input_dto, request_id, access_token
        )

    def runtime_prepare(self, input_dto: AgentTypeRuntimePrepareInputDTO, request_id: str, *, access_token: str):
        return self._write(
            PREPARE_AGENT_TYPE_RUNTIME, input_dto, request_id, access_token
        )

    def launch_runtime_scope(self, input_dto: DreamLaunchRuntimeScopeInputDTO, request_id: str, *, access_token: str):
        return self._execute(
            AUTHORIZE_DREAM_LAUNCH_RUNTIME, input_dto, request_id, access_token
        )

    def launch_runtime_plan(self, input_dto: DreamLaunchRuntimePlanInputDTO, request_id: str, *, access_token: str):
        return self._execute(
            PLAN_DREAM_LAUNCH_RUNTIME, input_dto, request_id, access_token
        )

    def launch_runtime_prepare(self, input_dto: DreamLaunchRuntimePrepareInputDTO, request_id: str, *, access_token: str):
        return self._write(
            PREPARE_DREAM_LAUNCH_RUNTIME, input_dto, request_id, access_token
        )
