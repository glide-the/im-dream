"""Strict task_008 contracts for runtime plugin reconcile and load receipts."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

try:
    from backend.models.deck_plugin import DeckRuntimePluginLock
except ModuleNotFoundError:  # Support the backend directory on PYTHONPATH.
    from models.deck_plugin import DeckRuntimePluginLock


SHA256_PATTERN = r"^sha256:[0-9a-f]{64}$"


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )


class DeclarationStatus(str, Enum):
    UNDECLARED = "undeclared"
    DECLARED = "declared"
    DISABLED = "disabled"


class MaterializationStatus(str, Enum):
    MISSING = "missing"
    MATERIALIZING = "materializing"
    MATERIALIZED = "materialized"
    FAILED = "failed"


class ActivationStatus(str, Enum):
    INACTIVE = "inactive"
    LOADABLE = "loadable"
    LOADED = "loaded"
    LOAD_FAILED = "load_failed"


class RuntimePlacementContext(_StrictFrozenModel):
    """Trusted placement resolved by runtime/preflight infrastructure."""

    workflow_run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    runtime_environment_id: str = Field(min_length=1)
    runtime_pool_id: str = Field(min_length=1)
    distribution_mode: Literal["local_persistent"]
    runtime_node_id: str = Field(min_length=1)
    artifact_set_hash: str = Field(pattern=SHA256_PATTERN)
    policy_revision: str = Field(min_length=1)
    deployment_tier: Literal["local"]

    @model_validator(mode="after")
    def is_supported_single_node_placement(self) -> "RuntimePlacementContext":
        if self.runtime_pool_id != self.runtime_environment_id:
            raise ValueError("runtime pool must equal runtime environment")
        return self


class RuntimePluginMaterialization(_StrictFrozenModel):
    runtime_materialization_id: str = Field(pattern=r"^rm_[0-9a-f]{32}$")
    runtime_environment_id: str = Field(min_length=1)
    runtime_pool_id: str = Field(min_length=1)
    runtime_node_id: str = Field(min_length=1)
    claude_code_plugin_id: str = Field(min_length=1)
    resolved_version: str = Field(min_length=1)
    artifact_digest: str = Field(pattern=SHA256_PATTERN)
    materialized_digest: str | None = Field(default=None, pattern=SHA256_PATTERN)
    artifact_set_hash: str = Field(pattern=SHA256_PATTERN)
    policy_revision: str = Field(min_length=1)
    declaration_status: DeclarationStatus
    materialization_status: MaterializationStatus
    activation_status: ActivationStatus
    materialization_key: str = Field(pattern=SHA256_PATTERN)
    attempt_id: str = Field(pattern=r"^rpa_[0-9a-f]{32}$")
    attempt_count: int = Field(ge=1)
    verification_status: Literal["verified", "legacy_unverified"] | None = None
    signature_bundle_ref: str | None = None
    retention_state: str | None = None
    restore_source_ref: str | None = None
    cache_ref: str | None = None
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def dimensions_remain_consistent(self) -> "RuntimePluginMaterialization":
        if self.runtime_pool_id != self.runtime_environment_id:
            raise ValueError("materialization must remain single-node scoped")
        if self.materialization_status is MaterializationStatus.MATERIALIZED:
            if self.materialized_digest is None or self.cache_ref is None:
                raise ValueError("materialized state requires digest and cache reference")
        if self.activation_status in {ActivationStatus.LOADABLE, ActivationStatus.LOADED}:
            if self.materialization_status is not MaterializationStatus.MATERIALIZED:
                raise ValueError("loadable or loaded state requires materialized bytes")
        if self.materialization_status is MaterializationStatus.FAILED and not self.last_error:
            raise ValueError("failed materialization requires a sanitized error")
        return self


class HeadlessPluginState(_StrictFrozenModel):
    claude_code_plugin_id: str = Field(min_length=1)
    resolved_version: str = Field(min_length=1)
    artifact_digest: str = Field(pattern=SHA256_PATTERN)
    loaded_capabilities: list[str] = Field(default_factory=list)
    load_status: Literal["loaded", "load_failed", "skipped"]
    loaded_at: datetime

    @field_validator("loaded_capabilities")
    @classmethod
    def capabilities_are_canonical(cls, value: list[str]) -> list[str]:
        if value != sorted(set(value)):
            raise ValueError("loaded capabilities must be sorted and unique")
        return value


class ReconcileResult(_StrictFrozenModel):
    attempt_id: str = Field(pattern=r"^rpa_[0-9a-f]{32}$")
    workflow_run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    runtime_node_id: str = Field(min_length=1)
    policy_revision: str = Field(min_length=1)
    settings_intent: dict[str, object]
    plugins: list[HeadlessPluginState]
    completed_before_first_query: Literal[True]
    created_at: datetime


class CliResult(_StrictFrozenModel):
    claude_code_plugin_id: str = Field(min_length=1)
    resolved_version: str = Field(min_length=1)
    status: Literal["installed"]


class MaterializationResult(_StrictFrozenModel):
    materialization: RuntimePluginMaterialization
    reused: bool


class LoadReceiptEntry(_StrictFrozenModel):
    claude_code_plugin_id: str = Field(min_length=1)
    resolved_version: str = Field(min_length=1)
    artifact_digest: str = Field(pattern=SHA256_PATTERN)
    materialized_digest: str = Field(pattern=SHA256_PATTERN)
    verification_status: Literal["verified", "legacy_unverified"]
    signature_bundle_ref: str | None = None
    retention_state: str = Field(min_length=1)
    restore_source_ref: str | None = None
    required: bool
    loaded_capabilities: list[str] = Field(default_factory=list)
    load_status: Literal["loaded", "load_failed", "skipped"]
    loaded_at: datetime

    @field_validator("loaded_capabilities")
    @classmethod
    def capabilities_are_canonical(cls, value: list[str]) -> list[str]:
        if value != sorted(set(value)):
            raise ValueError("loaded capabilities must be sorted and unique")
        return value


class RuntimeLoadReceipt(_StrictFrozenModel):
    receipt_id: str = Field(pattern=r"^rlr_[0-9a-f]{32}$")
    workflow_run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    runtime_plugin_lock_id: str = Field(min_length=1)
    runtime_plugin_lock_digest: str = Field(pattern=SHA256_PATTERN)
    runtime_environment_id: str = Field(min_length=1)
    runtime_pool_id: str = Field(min_length=1)
    distribution_mode: Literal["local_persistent"]
    runtime_node_id: str = Field(min_length=1)
    artifact_set_hash: str = Field(pattern=SHA256_PATTERN)
    policy_revision: str = Field(min_length=1)
    deployment_tier: Literal["local"]
    scope: Literal["session"]
    readiness_state: Literal["session_loaded"]
    required_entries_ready: bool
    entries: list[LoadReceiptEntry]
    created_at: datetime

    @model_validator(mode="after")
    def readiness_is_server_consistent(self) -> "RuntimeLoadReceipt":
        if self.runtime_pool_id != self.runtime_environment_id:
            raise ValueError("receipt placement is not single-node")
        required_entries = [entry for entry in self.entries if entry.required]
        computed_ready = bool(required_entries) and all(
            entry.load_status == "loaded"
            and entry.materialized_digest == entry.artifact_digest
            for entry in required_entries
        )
        if self.required_entries_ready != computed_ready:
            raise ValueError("required_entries_ready must be server-computed")
        plugin_ids = [entry.claude_code_plugin_id for entry in self.entries]
        if len(plugin_ids) != len(set(plugin_ids)):
            raise ValueError("receipt entries must be unique by plugin ID")
        return self


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_digest(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def runtime_lock_digest(lock_json: str) -> str:
    return sha256_digest(canonical_json(json.loads(lock_json)))


def compute_artifact_set_hash(runtime_lock: DeckRuntimePluginLock) -> str:
    entries = [
        {
            "artifact_digest": entry.artifact_digest,
            "claude_code_plugin_id": entry.claude_code_plugin_id,
            "resolved_version": entry.resolved_version,
        }
        for entry in runtime_lock.claude_code_plugins
        if entry.required
    ]
    entries.sort(key=lambda item: item["claude_code_plugin_id"])
    return sha256_digest(canonical_json(entries))


def compute_materialization_key(
    placement_context: RuntimePlacementContext,
    claude_code_plugin_id: str,
    resolved_version: str,
    artifact_digest: str,
) -> str:
    return sha256_digest(
        canonical_json(
            {
                "artifact_digest": artifact_digest,
                "claude_code_plugin_id": claude_code_plugin_id,
                "policy_revision": placement_context.policy_revision,
                "resolved_version": resolved_version,
                "runtime_environment_id": placement_context.runtime_environment_id,
                "runtime_node_id": placement_context.runtime_node_id,
            }
        )
    )
