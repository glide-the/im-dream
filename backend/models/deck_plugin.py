"""Deck Plugin manifest, release, binding, and product Agent-type models.

[Sync 2026-08-16] Expose sanitized append-only binding history for Deck version UI.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SEMVER_PATTERN = re.compile(
    r"^(?:0|[1-9]\d*)\."
    r"(?:0|[1-9]\d*)\."
    r"(?:0|[1-9]\d*)"
    r"(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
STABLE_ID_PATTERN = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$"
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DeckPluginReleaseStatus(str, Enum):
    DRAFT = "draft"
    VALIDATING = "validating"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    REVOKED = "revoked"


class WorkflowStepSpec(_StrictModel):
    step_id: str = Field(min_length=1)
    required_capabilities: list[str] = Field(default_factory=list)


class WorkflowSpec(_StrictModel):
    workflow_definition_ref: str = Field(min_length=1)
    input_schema_ref: str = Field(min_length=1)
    output_schema_ref: str = Field(min_length=1)
    steps: list[WorkflowStepSpec] = Field(min_length=1)


class CompatibilitySpec(_StrictModel):
    deck_host_api: str = Field(min_length=1)
    claude_agent_contract: str = Field(min_length=1)
    claude_code: str = Field(min_length=1)
    story_output_schema: str = Field(min_length=1)
    deck_runtime_snapshot_contract: str = Field(min_length=1)


class DeckPluginRuntimeConfigSpec(_StrictModel):
    profile_contract: str = Field(min_length=1)
    required_config_keys: list[str]
    secret_ref_kinds: list[str]
    allow_profile_versions: str = Field(min_length=1)


class ClaudeCodePluginSpec(_StrictModel):
    claude_code_plugin_id: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    version_constraint: str = Field(min_length=1)
    required: bool
    capability_bindings: list[str] = Field(default_factory=list)


class RuntimeSpec(_StrictModel):
    claude_code_plugins: list[ClaudeCodePluginSpec]
    degraded_modes: list[str] = Field(default_factory=list)


class DependenciesSpec(_StrictModel):
    deck_plugin_releases: list[str] = Field(default_factory=list)


class DeckPluginManifestV1(_StrictModel):
    schema_version: Literal["deck-plugin/v1"]
    deck_plugin_id: str = Field(min_length=3)
    deck_plugin_version: str = Field(min_length=5)
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    author: str = Field(min_length=1)
    status: DeckPluginReleaseStatus
    workflow: WorkflowSpec
    compatibility: CompatibilitySpec
    runtime_configuration: DeckPluginRuntimeConfigSpec
    capabilities: list[str] = Field(min_length=1)
    runtime: RuntimeSpec
    dependencies: DependenciesSpec

    @field_validator("deck_plugin_id")
    @classmethod
    def stable_identifier(cls, value: str) -> str:
        if not STABLE_ID_PATTERN.fullmatch(value):
            raise ValueError("deck_plugin_id must be a stable dotted lowercase identifier")
        return value

    @field_validator("deck_plugin_version")
    @classmethod
    def semantic_version(cls, value: str) -> str:
        if not SEMVER_PATTERN.fullmatch(value):
            raise ValueError("deck_plugin_version must follow SemVer 2.0.0")
        return value

    @field_validator("capabilities")
    @classmethod
    def capabilities_are_unique(cls, value: list[str]) -> list[str]:
        if any(not capability.strip() for capability in value):
            raise ValueError("capabilities must not contain blank values")
        if len(value) != len(set(value)):
            raise ValueError("capabilities must be unique")
        return value


class DeckPluginRelease(_StrictModel):
    id: str
    deck_plugin_id: str
    deck_plugin_version: str
    display_name: str
    description: str | None = None
    author: str | None = None
    status: DeckPluginReleaseStatus
    manifest: DeckPluginManifestV1
    manifest_hash: str
    workflow_definition_ref: str
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None


class RuntimePluginLockEntry(_StrictModel):
    claude_code_plugin_id: str = Field(min_length=1)
    resolved_version: str = Field(min_length=5)
    source_ref: str = Field(min_length=1)
    artifact_digest: str
    required: bool
    capability_bindings: list[str] = Field(default_factory=list)

    @field_validator("resolved_version")
    @classmethod
    def resolved_version_is_exact_semver(cls, value: str) -> str:
        if not SEMVER_PATTERN.fullmatch(value):
            raise ValueError("resolved_version must follow exact SemVer 2.0.0")
        return value

    @field_validator("artifact_digest")
    @classmethod
    def artifact_digest_is_immutable_or_empty(cls, value: str) -> str:
        if value and not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
            raise ValueError("artifact_digest must be an immutable sha256 digest")
        return value


class DeckRuntimePluginLock(_StrictModel):
    runtime_plugin_lock_id: str = Field(pattern=r"^rpl_[0-9a-f]{32}$")
    deck_plugin_id: str
    deck_plugin_version: str
    deck_plugin_manifest_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    claude_code_plugins: list[RuntimePluginLockEntry]
    created_at: datetime
    production_ready: bool = False
    production_readiness_reasons: list[str] = Field(default_factory=list)


class InstallationStatus(str, Enum):
    """Deck-domain installation state; deliberately separate from PluginStatus."""

    INSTALLING = "installing"
    READY = "ready"
    DISABLED = "disabled"
    ERROR = "error"
    UPGRADE_PENDING = "upgrade_pending"
    UNINSTALLED = "uninstalled"


class DeckPluginInstallation(_StrictModel):
    deck_plugin_installation_id: str = Field(pattern=r"^dpi_[0-9a-f]{32}$")
    scope_type: Literal["instance", "workspace"]
    scope_id: str = Field(min_length=1)
    deck_plugin_id: str = Field(min_length=3)
    installed_versions: list[str] = Field(default_factory=list)
    default_version: str | None = None
    status: InstallationStatus
    approved_capabilities: list[str] = Field(default_factory=list)
    source_policy_id: str = Field(min_length=1)
    last_error_code: str | None = None
    last_error_summary: str | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("installed_versions")
    @classmethod
    def installed_versions_are_exact_and_unique(cls, value: list[str]) -> list[str]:
        if any(not SEMVER_PATTERN.fullmatch(version) for version in value):
            raise ValueError("installed_versions must contain exact SemVer values")
        if len(value) != len(set(value)):
            raise ValueError("installed_versions must be unique")
        return value

    @field_validator("default_version")
    @classmethod
    def default_version_is_exact_semver(cls, value: str | None) -> str | None:
        if value is not None and not SEMVER_PATTERN.fullmatch(value):
            raise ValueError("default_version must follow exact SemVer 2.0.0")
        return value

    @field_validator("approved_capabilities")
    @classmethod
    def approved_capabilities_are_unique(cls, value: list[str]) -> list[str]:
        if any(not capability.strip() for capability in value):
            raise ValueError("approved_capabilities must not contain blank values")
        if len(value) != len(set(value)):
            raise ValueError("approved_capabilities must be unique")
        return value

    @model_validator(mode="after")
    def default_version_is_installed(self) -> "DeckPluginInstallation":
        if self.default_version is not None and self.default_version not in self.installed_versions:
            raise ValueError("default_version must be present in installed_versions")
        if self.status in {InstallationStatus.READY, InstallationStatus.DISABLED}:
            if self.default_version is None:
                raise ValueError("ready or disabled installations require a default_version")
        return self


class CompatibilityCheck(str, Enum):
    RELEASE_AVAILABLE = "release_available"
    DECK_HOST_COMPATIBLE = "deck_host_compatible"
    CLAUDE_AGENT_COMPATIBLE = "claude_agent_compatible"
    STORY_SCHEMA_COMPATIBLE = "story_schema_compatible"
    DECK_RUNTIME_CONFIG_COMPATIBLE = "deck_runtime_config_compatible"
    RUNTIME_PLUGIN_RESOLVED = "runtime_plugin_resolved"
    WORKFLOW_PERMISSION = "workflow_permission"
    RUNTIME_PLUGIN_READY = "runtime_plugin_ready"


class CompatibilityResult(_StrictModel):
    passed: bool
    failed_check: CompatibilityCheck | None = None
    error_code: str | None = None
    recovery_action: str | None = None
    effective_capabilities: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def failure_fields_are_consistent(self) -> "CompatibilityResult":
        failure_fields = (
            self.failed_check,
            self.error_code,
            self.recovery_action,
        )
        if self.passed and any(value is not None for value in failure_fields):
            raise ValueError("passed compatibility results cannot include failure fields")
        if not self.passed and any(value is None for value in failure_fields):
            raise ValueError("failed compatibility results require structured failure fields")
        if not self.passed and self.effective_capabilities:
            raise ValueError("failed compatibility results cannot expose capabilities")
        if self.effective_capabilities != sorted(set(self.effective_capabilities)):
            raise ValueError("effective_capabilities must be sorted and unique")
        return self


class CapabilityDiff(_StrictModel):
    added: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    requires_approval: bool

    @model_validator(mode="after")
    def capability_diff_is_canonical(self) -> "CapabilityDiff":
        if self.added != sorted(set(self.added)):
            raise ValueError("added capabilities must be sorted and unique")
        if self.removed != sorted(set(self.removed)):
            raise ValueError("removed capabilities must be sorted and unique")
        if set(self.added) & set(self.removed):
            raise ValueError("a capability cannot be both added and removed")
        if self.requires_approval != bool(self.added):
            raise ValueError("requires_approval must reflect capability expansion")
        return self


class DeckPluginBindingStatus(str, Enum):
    ACTIVE = "active"
    STALE = "stale"


class DeckAgentType(str, Enum):
    """Product interaction selected for a Deck; display copy stays client-owned."""

    CHAT = "chat"
    DREAM = "dream"


class BindingApplyTo(str, Enum):
    NEXT_RUN = "next_run"


class SelectionCompatibility(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    UNKNOWN = "unknown"


class SelectionRecovery(_StrictModel):
    owner: str = Field(min_length=1)
    action: str = Field(min_length=1)


class SelectionValidationSummary(_StrictModel):
    selectable: bool
    release_status: str
    installation_status: str
    compatibility: SelectionCompatibility
    runtime_readiness: str
    reason_code: str | None = None
    recovery: SelectionRecovery | None = None
    capability_summary: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def selection_fields_are_consistent(self) -> "SelectionValidationSummary":
        if self.selectable:
            if self.reason_code is not None or self.recovery is not None:
                raise ValueError("selectable results cannot include failure recovery")
        elif self.reason_code is None or self.recovery is None:
            raise ValueError("unselectable results require a reason and recovery")
        if self.capability_summary != sorted(set(self.capability_summary)):
            raise ValueError("capability_summary must be sorted and unique")
        return self


class DeckPluginBinding(_StrictModel):
    deck_plugin_binding_id: str = Field(pattern=r"^dpb_[0-9a-f]{32}$")
    deck_id: str = Field(min_length=1)
    workspace_id: str = Field(min_length=1)
    creator_id: str = Field(min_length=1)
    deck_plugin_id: str = Field(min_length=3)
    deck_plugin_version: str = Field(min_length=5)
    binding_revision: int = Field(ge=1)
    status: DeckPluginBindingStatus
    applied_to: BindingApplyTo
    created_at: datetime
    updated_at: datetime

    @field_validator("deck_plugin_id")
    @classmethod
    def binding_plugin_identifier_is_stable(cls, value: str) -> str:
        if not STABLE_ID_PATTERN.fullmatch(value):
            raise ValueError("deck_plugin_id must be a stable dotted lowercase identifier")
        return value

    @field_validator("deck_plugin_version")
    @classmethod
    def binding_version_is_exact_semver(cls, value: str) -> str:
        if not SEMVER_PATTERN.fullmatch(value):
            raise ValueError("deck_plugin_version must follow exact SemVer 2.0.0")
        return value


class DeckPluginSelectionRequest(_StrictModel):
    deck_plugin_id: str = Field(min_length=3)
    deck_plugin_version: str = Field(min_length=5)
    apply_to: Literal[BindingApplyTo.NEXT_RUN] = BindingApplyTo.NEXT_RUN

    @field_validator("deck_plugin_id")
    @classmethod
    def selection_plugin_identifier_is_stable(cls, value: str) -> str:
        if not STABLE_ID_PATTERN.fullmatch(value):
            raise ValueError("deck_plugin_id must be a stable dotted lowercase identifier")
        return value

    @field_validator("deck_plugin_version")
    @classmethod
    def selection_version_is_exact_semver(cls, value: str) -> str:
        if not SEMVER_PATTERN.fullmatch(value):
            raise ValueError("deck_plugin_version must follow exact SemVer 2.0.0")
        return value


class DeckPluginBindingUpdateRequest(DeckPluginSelectionRequest):
    expected_binding_revision: int = Field(ge=0)


class DeckPluginBindingResponse(_StrictModel):
    deck_plugin_binding_id: str = Field(pattern=r"^dpb_[0-9a-f]{32}$")
    deck_id: str
    deck_plugin_id: str
    deck_plugin_version: str
    binding_revision: int = Field(ge=1)
    status: DeckPluginBindingStatus
    applied_to: BindingApplyTo
    selection_validation_summary: SelectionValidationSummary


class DeckPluginBindingState(_StrictModel):
    deck_id: str
    binding_revision: int = Field(ge=0)
    applied_to: BindingApplyTo = BindingApplyTo.NEXT_RUN
    binding: DeckPluginBindingResponse | None = None

    @model_validator(mode="after")
    def revision_matches_binding(self) -> "DeckPluginBindingState":
        if self.binding is not None and self.binding.binding_revision != self.binding_revision:
            raise ValueError("binding state revision must match the current binding")
        return self


class DeckPluginBindingHistoryEntry(_StrictModel):
    """One immutable Deck runtime-configuration binding revision."""

    deck_plugin_binding_id: str = Field(pattern=r"^dpb_[0-9a-f]{32}$")
    deck_plugin_id: str = Field(min_length=3)
    deck_plugin_version: str = Field(min_length=5)
    binding_revision: int = Field(ge=1)
    status: DeckPluginBindingStatus
    applied_to: BindingApplyTo
    created_at: datetime
    updated_at: datetime


class DeckPluginBindingHistoryResponse(_StrictModel):
    deck_id: str = Field(min_length=1)
    current_binding_revision: int = Field(ge=0)
    entries: list[DeckPluginBindingHistoryEntry]


class DeckAgentTypeUpdateRequest(_StrictModel):
    agent_type: DeckAgentType
    expected_binding_revision: int = Field(ge=0)


class DeckAgentTypeResponse(_StrictModel):
    deck_id: str = Field(min_length=1)
    agent_type: DeckAgentType
    binding_revision: int = Field(ge=0)


class DeckPluginOption(_StrictModel):
    display_name: str
    deck_plugin_id: str
    deck_plugin_version: str
    release_status: str
    installation_status: str
    compatibility: SelectionCompatibility
    runtime_readiness: str
    selectable: bool
    reason_code: str | None = None
    recovery: SelectionRecovery | None = None
    capability_summary: list[str] = Field(default_factory=list)


class DeckPluginOptionsResponse(_StrictModel):
    deck_id: str
    applied_to: BindingApplyTo = BindingApplyTo.NEXT_RUN
    options: list[DeckPluginOption]


class DeckPluginSelectionValidationResponse(_StrictModel):
    deck_id: str
    deck_plugin_id: str
    deck_plugin_version: str
    applied_to: BindingApplyTo = BindingApplyTo.NEXT_RUN
    validation: SelectionValidationSummary


class BindingRevisionConflictResponse(_StrictModel):
    error_code: Literal["BINDING_REVISION_CONFLICT"]
    current_revision: int = Field(ge=0)
    message: str
