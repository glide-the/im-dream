# [Input] Registry170-174 capability catalog, current OAuth bearer and closed Deck Plugin commands.
# [Output] Strict control DTOs plus original-request receipt recovery for Admin-owned persistence.
# [Pos] Dream wire boundary; Admin owns permissions, Drizzle repositories, locks and transactions.
# [Sync] 2026-09-17: match Admin's write-authorized plan capability while keeping plan itself read-only.
# [Sync] 2026-09-16: consume the Admin Deck Plugin control aggregate without SQL or actor selectors.
"""Typed Admin consumer for Deck Plugin lifecycle control operations."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator, model_validator

from .chat_models import ChatStrictDTO, PresentFieldsDTO
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import CommittedReceiptDTO, OperationCapabilityDTO, SchemaCapabilityDTO
from .workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS


Identifier = Annotated[str, Field(min_length=1, max_length=255)]
PluginId = Annotated[
    str,
    Field(
        min_length=3,
        pattern=(
            r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"
            r"(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$"
        ),
    ),
]
PluginVersion = Annotated[
    str,
    Field(
        min_length=5,
        pattern=(
            r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
            r"(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
            r"(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?"
            r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
        ),
    ),
]
Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
InstallationId = Annotated[str, Field(pattern=r"^dpi_[0-9a-f]{32}$")]
RuntimeLockId = Annotated[str, Field(pattern=r"^rpl_[0-9a-f]{32}$")]
Revision = Annotated[int, Field(ge=0, le=9_007_199_254_740_991)]
ScopeType = Literal["instance", "workspace"]
ControlAction = Literal[
    "install",
    "enable",
    "disable",
    "upgrade",
    "rollback",
    "approve_upgrade",
    "reject_upgrade",
    "uninstall",
    "reconcile",
]


class DeckPluginControlListInputDTO(ChatStrictDTO):
    scope_type: ScopeType
    scope_id: Identifier


class DeckPluginControlVersionInputDTO(DeckPluginControlListInputDTO):
    deck_plugin_id: PluginId
    deck_plugin_version: PluginVersion


class DeckPluginControlReadinessInputDTO(DeckPluginControlListInputDTO):
    deck_plugin_id: PluginId


class DeckPluginControlCommandDTO(PresentFieldsDTO):
    """One wire model whose serializer preserves the Admin discriminated union."""

    action: ControlAction
    scope_type: ScopeType
    scope_id: Identifier
    deck_plugin_id: PluginId
    deck_plugin_version: PluginVersion | None = None
    source_type: Literal["marketplace", "controlled", "local"] | None = None
    source: Annotated[str, Field(min_length=1, max_length=2048)] | None = None
    reason: Annotated[str, Field(min_length=1, max_length=500)] | None = None
    target_version: PluginVersion | None = None
    purge: bool | None = None

    @model_validator(mode="after")
    def require_exact_action_fields(self):
        common = {"action", "scope_type", "scope_id", "deck_plugin_id"}
        required = {
            "install": {"deck_plugin_version", "source_type", "source"},
            "disable": {"reason"},
            "upgrade": {"target_version"},
            "rollback": {"target_version"},
            "uninstall": {"purge"},
        }.get(self.action, set())
        if self.model_fields_set != common | required:
            raise ValueError("Deck Plugin command fields do not match its action")
        return self


class DeckPluginControlCapabilityDiffDTO(ChatStrictDTO):
    added: list[str]
    removed: list[str]


class DeckPluginControlRuntimeEntryDTO(ChatStrictDTO):
    claude_code_plugin_id: Identifier
    resolved_version: PluginVersion
    source_ref: Annotated[str, Field(min_length=1, max_length=2048)]
    artifact_digest: Digest
    required: bool


class DeckPluginControlRuntimeTargetDTO(ChatStrictDTO):
    runtime_plugin_lock_id: RuntimeLockId
    deck_plugin_manifest_hash: Digest
    artifact_set_hash: Digest
    entries: list[DeckPluginControlRuntimeEntryDTO]


class DeckPluginControlPlanDTO(ChatStrictDTO):
    command: DeckPluginControlCommandDTO
    expected_revision: Revision | None
    deck_plugin_installation_id: InstallationId | None
    target_version: PluginVersion | None
    source_policy_id: Annotated[str, Field(min_length=1, max_length=2304)] | None
    capability_diff: DeckPluginControlCapabilityDiffDTO
    requires_runtime_evidence: bool
    runtime_target: DeckPluginControlRuntimeTargetDTO | None

    @model_validator(mode="after")
    def validate_plan_state(self):
        if self.requires_runtime_evidence != (self.runtime_target is not None):
            raise ValueError("Runtime target must match evidence requirement")
        if (self.expected_revision is None) != (
            self.deck_plugin_installation_id is None
        ):
            raise ValueError("Installation identity and revision must match")
        if self.command.action != "install" and self.expected_revision is None:
            raise ValueError("Existing installation identity is required")
        return self


class DeckPluginControlEvidenceDTO(ChatStrictDTO):
    claude_code_plugin_id: Identifier
    resolved_version: PluginVersion
    artifact_digest: Digest
    materialized_digest: Digest
    cache_ref: Annotated[str, Field(min_length=1, max_length=4096)]
    has_manifest: Literal[True]


class DeckPluginControlApplyInputDTO(ChatStrictDTO):
    plan: DeckPluginControlPlanDTO
    evidence: list[DeckPluginControlEvidenceDTO]

    @model_validator(mode="after")
    def require_evidence_shape(self):
        target = self.plan.runtime_target
        expected = (
            [
                (item.claude_code_plugin_id, item.resolved_version, item.artifact_digest)
                for item in target.entries
            ]
            if target is not None
            else []
        )
        actual = [
            (item.claude_code_plugin_id, item.resolved_version, item.artifact_digest)
            for item in self.evidence
        ]
        if actual != expected:
            raise ValueError("Runtime evidence must match the immutable plan order")
        return self


class DeckPluginRuntimeViewDTO(ChatStrictDTO):
    claude_code_plugin_id: Identifier
    resolved_version: PluginVersion
    version_constraint: PluginVersion
    artifact_digest: Digest
    declaration_status: Literal["undeclared", "declared", "disabled"]
    materialization_status: Literal[
        "missing", "materializing", "materialized", "failed"
    ]
    activation_status: Literal["inactive", "loadable", "loaded", "load_failed"]
    health_status: Literal["healthy", "failed", "unknown"]
    last_error_code: Identifier | None
    last_error_summary: str | None
    updated_at: datetime | None

    @field_validator("updated_at")
    @classmethod
    def require_timestamp_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Runtime timestamp requires timezone")
        return value


class DeckPluginRuntimeReadinessDTO(ChatStrictDTO):
    declaration_status: Literal["undeclared", "declared", "disabled"]
    materialization_status: Literal[
        "missing", "materializing", "materialized", "failed"
    ]
    activation_status: Literal["inactive", "loadable", "loaded", "load_failed"]


class DeckPluginControlSourceDTO(ChatStrictDTO):
    type: Literal["controlled"]
    label: str = Field(min_length=1)
    verified: Literal[True]


class DeckPluginControlCapabilitiesDTO(ChatStrictDTO):
    manifest_requested: list[str]
    effective: list[str]


class DeckPluginControlCompatibilityDTO(ChatStrictDTO):
    passed: bool
    status: Literal["compatible", "pending"]
    effective_capabilities: list[str]


class DeckPluginControlManifestDTO(ChatStrictDTO):
    schema_version: Literal["deck-plugin/v1"]
    author: str
    workflow_references: list[str]
    input_schema_version: str = Field(min_length=1)
    output_schema_version: str = Field(min_length=1)
    deck_runtime_contract: str = Field(min_length=1)
    capabilities: list[str]


class DeckPluginControlViewDTO(ChatStrictDTO):
    deck_plugin_installation_id: str = Field(
        pattern=r"^(?:dpi_[0-9a-f]{32}|preview:.+)$"
    )
    deck_plugin_id: PluginId
    display_name: str
    deck_plugin_version: PluginVersion
    installed_versions: list[PluginVersion]
    default_version: PluginVersion | None
    available_version: PluginVersion | None
    status: Literal[
        "installing", "ready", "disabled", "error", "upgrade_pending", "uninstalled"
    ]
    source: DeckPluginControlSourceDTO
    approved_capabilities: list[str]
    capabilities: DeckPluginControlCapabilitiesDTO
    compatibility: DeckPluginControlCompatibilityDTO
    runtime_readiness: DeckPluginRuntimeReadinessDTO
    health_status: Literal["healthy", "unknown"]
    last_error_code: Identifier | None
    last_error_summary: str | None
    updated_at: datetime
    rollback_versions: list[PluginVersion]
    manifest: DeckPluginControlManifestDTO
    runtime_plugins: list[DeckPluginRuntimeViewDTO]
    history: list[dict[str, Any]]
    recent_runs: list[dict[str, Any]]
    operation_logs: list[dict[str, Any]]
    is_system: bool

    @field_validator("updated_at")
    @classmethod
    def require_updated_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Installation timestamp requires timezone")
        return value

    @field_validator("history", "recent_runs", "operation_logs", mode="before")
    @classmethod
    def require_empty_legacy_lists(cls, value):
        if value != []:
            raise ValueError("Legacy control projections must remain empty")
        return value


class DeckPluginControlListDTO(ChatStrictDTO):
    installations: list[DeckPluginControlViewDTO]
    runtime_plugins: list[DeckPluginRuntimeViewDTO]


class DeckPluginControlOperationDTO(ChatStrictDTO):
    operation_id: Annotated[str, Field(pattern=r"^op_[0-9a-f]{32}$")]
    deck_plugin_id: PluginId
    target_version: PluginVersion | None
    status: Literal["completed"]
    phase: Literal["ready", "upgrade_pending"]
    progress: Literal[100]
    message: str = Field(min_length=1)
    updated_at: datetime

    @field_validator("updated_at")
    @classmethod
    def require_updated_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Operation timestamp requires timezone")
        return value


def _operation(
    name,
    kind,
    input_dto,
    output_dto,
    hash_value,
    *,
    user_scope: Literal["dream:read", "dream:write"] | None = None,
):
    return DomainOperation(
        OperationCapabilityDTO(
            name=name,
            kind=kind,
            user_scope=user_scope or (
                "dream:read" if kind == "read" else "dream:write"
            ),
            background_scope=None,
            input_schema_version=1,
            output_schema_version=1,
            contract_sha256=hash_value,
        ),
        input_dto,
        output_dto,
    )


LIST_DECK_PLUGIN_CONTROL = _operation(
    "deck-plugin-control.list",
    "read",
    DeckPluginControlListInputDTO,
    DeckPluginControlListDTO,
    "580809db8126d3f45cc233a7a4c32f38cfd19daa6cb5ccd2154cbec10ba359b2",
)
READ_DECK_PLUGIN_CONTROL_VERSION = _operation(
    "deck-plugin-control.version",
    "read",
    DeckPluginControlVersionInputDTO,
    DeckPluginControlViewDTO,
    "8fb594490a7766bc81aa273c2aee17e4616d22d0f0c724c718f5797d435ca589",
)
READ_DECK_PLUGIN_CONTROL_READINESS = _operation(
    "deck-plugin-control.readiness",
    "read",
    DeckPluginControlReadinessInputDTO,
    DeckPluginRuntimeReadinessDTO,
    "8c41de9052a5036d48f52a0945174d654b0442dd43159953978310cca0fc5fa3",
)
PLAN_DECK_PLUGIN_CONTROL = _operation(
    "deck-plugin-control.plan",
    "read",
    DeckPluginControlCommandDTO,
    DeckPluginControlPlanDTO,
    "2e11a56d2e3efb491762cfc5559bd7a2cf1f2aee527632243424a62ef0e38df8",
    user_scope="dream:write",
)
APPLY_DECK_PLUGIN_CONTROL = _operation(
    "deck-plugin-control.apply",
    "write",
    DeckPluginControlApplyInputDTO,
    DeckPluginControlOperationDTO,
    "fba707edfdad4ed88f82b8325d2cfd90a7f52f9ad24a34e07e05021c0978573e",
)
DECK_PLUGIN_CONTROL_OPERATIONS = (
    LIST_DECK_PLUGIN_CONTROL,
    READ_DECK_PLUGIN_CONTROL_VERSION,
    READ_DECK_PLUGIN_CONTROL_READINESS,
    PLAN_DECK_PLUGIN_CONTROL,
    APPLY_DECK_PLUGIN_CONTROL,
)
DECK_PLUGIN_CONTROL_SCHEMA_REQUIREMENTS = (
    *WORKFLOW_SCHEMA_REQUIREMENTS,
    SchemaCapabilityDTO(
        capability="dream.runtime.local-placement.v1",
        version=1,
        contract_sha256=(
            "87fbd3c28bc077992bfa0e12674e71b5"
            "9182ea08934314c02560c8b577c50983"
        ),
    ),
)


def require_deck_plugin_control_capabilities(
    client: AdminDataClient,
    request_id: str,
) -> None:
    capabilities = client.capabilities(request_id)
    schemas = {item.capability: item for item in capabilities.schema_capabilities}
    if len(schemas) != len(capabilities.schema_capabilities) or any(
        schemas.get(item.capability) != item
        for item in DECK_PLUGIN_CONTROL_SCHEMA_REQUIREMENTS
    ):
        raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)


class AdminDeckPluginControlData:
    def __init__(self, client: AdminDataClient) -> None:
        self._client = client

    def _execute(self, operation, input_dto, request_id: str, access_token: str):
        require_deck_plugin_control_capabilities(self._client, request_id)
        result = self._client.execute(
            operation,
            input_dto,
            request_id,
            access_token=access_token,
        )
        if operation is READ_DECK_PLUGIN_CONTROL_VERSION and (
            result.deck_plugin_id != input_dto.deck_plugin_id
            or result.deck_plugin_version != input_dto.deck_plugin_version
        ):
            raise invalid_response(request_id)
        if operation is PLAN_DECK_PLUGIN_CONTROL and result.command != input_dto:
            raise invalid_response(request_id)
        if operation is APPLY_DECK_PLUGIN_CONTROL and (
            result.deck_plugin_id != input_dto.plan.command.deck_plugin_id
            or result.target_version != input_dto.plan.target_version
        ):
            raise invalid_response(request_id, write=True)
        return result

    def list(
        self,
        input_dto: DeckPluginControlListInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> DeckPluginControlListDTO:
        return self._execute(
            LIST_DECK_PLUGIN_CONTROL, input_dto, request_id, access_token
        )

    def version(
        self,
        input_dto: DeckPluginControlVersionInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> DeckPluginControlViewDTO:
        return self._execute(
            READ_DECK_PLUGIN_CONTROL_VERSION, input_dto, request_id, access_token
        )

    def readiness(
        self,
        input_dto: DeckPluginControlReadinessInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> DeckPluginRuntimeReadinessDTO:
        return self._execute(
            READ_DECK_PLUGIN_CONTROL_READINESS,
            input_dto,
            request_id,
            access_token,
        )

    def plan(
        self,
        input_dto: DeckPluginControlCommandDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> DeckPluginControlPlanDTO:
        return self._execute(
            PLAN_DECK_PLUGIN_CONTROL, input_dto, request_id, access_token
        )

    def apply(
        self,
        input_dto: DeckPluginControlApplyInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> DeckPluginControlOperationDTO:
        try:
            return self._execute(
                APPLY_DECK_PLUGIN_CONTROL, input_dto, request_id, access_token
            )
        except AdminDataError as error:
            if not error.outcome_unknown:
                raise
        try:
            receipt = self._client.receipt(
                APPLY_DECK_PLUGIN_CONTROL,
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
        if (
            not isinstance(receipt, CommittedReceiptDTO)
            or type(receipt.result) is not DeckPluginControlOperationDTO
        ):
            raise AdminDataError(
                "ADMIN_WRITE_RESULT_UNKNOWN", 503, request_id, True
            )
        result = receipt.result
        if (
            result.deck_plugin_id != input_dto.plan.command.deck_plugin_id
            or result.target_version != input_dto.plan.target_version
        ):
            raise invalid_response(request_id, write=True)
        return result
