"""Strict run-scoped ClaudeAgent session contracts for task_009."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SHA256_PATTERN = r"^sha256:[0-9a-f]{64}$"


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )


class AgentSessionStatus(str, Enum):
    CREATING = "creating"
    ACTIVE = "active"
    TERMINATED = "terminated"
    FAILED = "failed"


TERMINAL_SESSION_STATUSES = frozenset(
    {AgentSessionStatus.TERMINATED, AgentSessionStatus.FAILED}
)


class SessionStartResult(_StrictFrozenModel):
    """Sanitized adapter acknowledgement; it never contains query content."""

    agent_session_id: str = Field(pattern=r"^as_[0-9a-f]{32}$")
    session_request_key: str = Field(pattern=SHA256_PATTERN)
    active: Literal[True]
    remote_session_ref: str | None = Field(default=None, max_length=255)


class AgentSession(_StrictFrozenModel):
    agent_session_id: str = Field(pattern=r"^as_[0-9a-f]{32}$")
    workflow_run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    runtime_load_receipt_id: str = Field(pattern=r"^rlr_[0-9a-f]{32}$")
    runtime_environment_id: str = Field(min_length=1)
    runtime_pool_id: str = Field(min_length=1)
    distribution_mode: Literal["local_persistent"]
    runtime_node_id: str = Field(min_length=1)
    artifact_set_hash: str = Field(pattern=SHA256_PATTERN)
    policy_revision: str = Field(min_length=1)
    deployment_tier: Literal["development", "test"]
    runtime_plugin_lock_id: str = Field(min_length=1)
    runtime_plugin_lock_digest: str = Field(pattern=SHA256_PATTERN)
    settings_json: str = Field(min_length=2)
    settings_hash: str = Field(pattern=SHA256_PATTERN)
    plugin_set_hash: str = Field(pattern=SHA256_PATTERN)
    session_request_key: str = Field(pattern=SHA256_PATTERN)
    attempt_number: int = Field(ge=1)
    status: AgentSessionStatus
    error_code: str | None = Field(default=None, max_length=128)
    termination_reason_code: str | None = Field(default=None, max_length=128)
    created_at: datetime
    started_at: datetime | None = None
    terminated_at: datetime | None = None
    lease_expires_at: datetime | None = None
    remote_session_ref: str | None = Field(default=None, max_length=255)

    @field_validator("settings_json")
    @classmethod
    def settings_are_canonical_and_sanitized(cls, value: str) -> str:
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("settings_json must be valid JSON") from exc
        if not isinstance(parsed, dict) or set(parsed) != {
            "enabledPlugins",
            "extraKnownMarketplaces",
            "pluginPolicy",
        }:
            raise ValueError("settings_json contains unsupported keys")
        enabled = parsed["enabledPlugins"]
        marketplaces = parsed["extraKnownMarketplaces"]
        policy = parsed["pluginPolicy"]
        if (
            not isinstance(enabled, dict)
            or not enabled
            or any(not isinstance(key, str) or not key or flag is not True for key, flag in enabled.items())
        ):
            raise ValueError("enabledPlugins must be a non-empty boolean map")
        if not isinstance(marketplaces, dict) or not marketplaces:
            raise ValueError("extraKnownMarketplaces must be a non-empty map")
        for alias, reference in marketplaces.items():
            if (
                not isinstance(alias, str)
                or not alias
                or not isinstance(reference, dict)
                or set(reference) != {"source"}
                or not isinstance(reference["source"], str)
                or not reference["source"]
                or any(
                    marker in reference["source"].lower()
                    for marker in ("secret", "token", "credential", "password")
                )
            ):
                raise ValueError("marketplace references must be trusted source projections")
        if not isinstance(policy, dict) or set(policy) != {"allowedCapabilities"}:
            raise ValueError("pluginPolicy contains unsupported keys")
        capabilities = policy["allowedCapabilities"]
        if (
            not isinstance(capabilities, list)
            or any(not isinstance(item, str) or not item for item in capabilities)
            or capabilities != sorted(set(capabilities))
        ):
            raise ValueError("allowedCapabilities must be sorted and unique")
        canonical = canonical_json(parsed).decode("utf-8")
        if value != canonical:
            raise ValueError("settings_json must use canonical JSON")
        return value

    @model_validator(mode="after")
    def bindings_and_lifecycle_are_consistent(self) -> "AgentSession":
        if self.runtime_pool_id != self.runtime_environment_id:
            raise ValueError("agent session must remain single-node scoped")
        if sha256_digest(self.settings_json.encode("utf-8")) != self.settings_hash:
            raise ValueError("settings_hash does not match settings_json")
        expected_request_key = compute_session_request_key(
            self.workflow_run_id,
            self.runtime_load_receipt_id,
            self.settings_hash,
        )
        if self.session_request_key != expected_request_key:
            raise ValueError("session_request_key does not match frozen inputs")
        if self.status is AgentSessionStatus.CREATING:
            if self.started_at is not None or self.terminated_at is not None:
                raise ValueError("creating sessions cannot carry lifecycle completion times")
            if (
                self.error_code is not None
                or self.termination_reason_code is not None
                or self.lease_expires_at is None
            ):
                raise ValueError("creating sessions require a lease and no error")
        elif self.status is AgentSessionStatus.ACTIVE:
            if self.started_at is None or self.terminated_at is not None:
                raise ValueError("active sessions require started_at only")
            if self.error_code is not None or self.termination_reason_code is not None:
                raise ValueError("active sessions cannot carry an error")
        elif self.status is AgentSessionStatus.TERMINATED:
            if self.started_at is None or self.terminated_at is None:
                raise ValueError("terminated sessions require start and termination times")
            if self.error_code is not None or self.termination_reason_code is None:
                raise ValueError("normal termination cannot carry an error")
        elif self.status is AgentSessionStatus.FAILED:
            if (
                self.error_code is None
                or self.termination_reason_code is None
                or self.terminated_at is None
            ):
                raise ValueError("failed sessions require an error and termination time")
        if self.started_at is not None and self.started_at < self.created_at:
            raise ValueError("started_at cannot precede created_at")
        if self.terminated_at is not None:
            baseline = self.started_at or self.created_at
            if self.terminated_at < baseline:
                raise ValueError("terminated_at cannot precede session lifecycle")
        return self


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def compute_session_request_key(
    workflow_run_id: str,
    runtime_load_receipt_id: str,
    settings_hash: str,
) -> str:
    return sha256_digest(
        canonical_json(
            {
                "runtime_load_receipt_id": runtime_load_receipt_id,
                "settings_hash": settings_hash,
                "workflow_run_id": workflow_run_id,
            }
        )
    )


def compute_plugin_set_hash(entries: list[dict[str, Any]]) -> str:
    canonical_entries = sorted(
        entries,
        key=lambda item: (
            str(item["claude_code_plugin_id"]),
            str(item["resolved_version"]),
        ),
    )
    return sha256_digest(canonical_json(canonical_entries))


def validate_session_transition(
    current: AgentSessionStatus,
    target: AgentSessionStatus,
) -> None:
    allowed = {
        AgentSessionStatus.CREATING: {
            AgentSessionStatus.ACTIVE,
            AgentSessionStatus.FAILED,
        },
        AgentSessionStatus.ACTIVE: {
            AgentSessionStatus.TERMINATED,
            AgentSessionStatus.FAILED,
        },
    }
    if target not in allowed.get(current, set()):
        raise ValueError("agent session transition is not allowed")
