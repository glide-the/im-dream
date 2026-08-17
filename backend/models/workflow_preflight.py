"""Data models for the authoritative Story Workspace workflow preflight."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PreflightStatus(str, Enum):
    CHECKING = "checking"
    PASSED = "passed"
    FAILED = "failed"
    EXPIRED = "expired"


class PreflightCheck(str, Enum):
    IDENTITY_WORKSPACE_PERMISSION = "identity_workspace_permission"
    BINDING_RELEASE = "binding_release"
    MANIFEST_WORKFLOW_SCHEMA = "manifest_workflow_schema"
    HOST_AGENT_RUNTIME_COMPATIBILITY = "host_agent_runtime_compatibility"
    CAPABILITY_SOURCE_POLICY = "capability_source_policy"
    DECK_RUNTIME_SNAPSHOT = "deck_runtime_snapshot"
    RUNTIME_MATERIALIZATION = "runtime_materialization"
    TOKEN_ISSUANCE = "token_issuance"


class WorkflowPreflight(_StrictModel):
    workflow_preflight_id: str = Field(pattern=r"^pf_[0-9a-f]{32}$")
    deck_id: str = Field(min_length=1)
    binding_revision: int = Field(ge=0)
    deck_plugin_id: str = Field(min_length=1)
    deck_plugin_version: str = Field(min_length=1)
    runtime_plugin_lock_id: str = Field(min_length=1)
    deck_runtime_profile_id: str = Field(min_length=1)
    deck_runtime_snapshot_id: str | None = None
    deck_runtime_snapshot_summary_hash: str | None = None
    input_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    status: PreflightStatus
    error_code: str | None = None
    failed_check: PreflightCheck | None = None
    expires_at: datetime
    preflight_token: str | None = Field(default=None, repr=False)
    created_by: str = Field(min_length=1)
    created_at: datetime

    @model_validator(mode="after")
    def status_fields_are_consistent(self) -> "WorkflowPreflight":
        failure_fields = (self.error_code, self.failed_check)
        if self.status is PreflightStatus.FAILED:
            if any(value is None for value in failure_fields):
                raise ValueError("failed preflights require error_code and failed_check")
            if self.preflight_token is not None:
                raise ValueError("failed preflights cannot expose a token")
        elif any(value is not None for value in failure_fields):
            raise ValueError("non-failed preflights cannot include failure fields")

        if self.status is PreflightStatus.PASSED:
            if self.deck_runtime_snapshot_id is None:
                raise ValueError("passed preflights require a Deck runtime snapshot")
            if self.deck_runtime_snapshot_summary_hash is None:
                raise ValueError("passed preflights require a sanitized snapshot summary hash")
        elif self.preflight_token is not None:
            raise ValueError("only passed preflights may expose a token")

        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be later than created_at")
        return self
