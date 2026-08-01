"""Canonical, sanitized event contracts for Deck Plugin workflows."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CanonicalEventType(str, Enum):
    DECK_PLUGIN_RELEASE_PUBLISHED = "deck_plugin.release.published"
    DECK_PLUGIN_INSTALLATION_STATUS_CHANGED = (
        "deck_plugin.installation.status_changed"
    )
    RUNTIME_PLUGIN_MATERIALIZATION_STATUS_CHANGED = (
        "runtime_plugin.materialization.status_changed"
    )
    DECK_PLUGIN_BINDING_CHANGED = "deck.plugin_binding.changed"
    WORKFLOW_PREFLIGHT_STATUS_CHANGED = "workflow.preflight.status_changed"
    WORKFLOW_RUN_CREATED = "workflow.run.created"
    WORKFLOW_RUN_STATUS_CHANGED = "workflow.run.status_changed"
    WORKFLOW_RUN_STEP_PROGRESSED = "workflow.run.step_progressed"
    WORKFLOW_RESULT_PERSISTED = "workflow.result.persisted"
    WORKFLOW_RUN_SECURITY_CANCELLED = "workflow.run.security_cancelled"


CANONICAL_EVENT_TYPES = frozenset(item.value for item in CanonicalEventType)

REQUIRED_PAYLOAD_FIELDS: dict[CanonicalEventType, frozenset[str]] = {
    CanonicalEventType.DECK_PLUGIN_RELEASE_PUBLISHED: frozenset(
        {
            "plugin_id",
            "plugin_version",
            "manifest_hash",
            "runtime_plugin_lock_id",
        }
    ),
    CanonicalEventType.DECK_PLUGIN_INSTALLATION_STATUS_CHANGED: frozenset(
        {"installation_id", "old_status", "new_status", "error_code"}
    ),
    CanonicalEventType.RUNTIME_PLUGIN_MATERIALIZATION_STATUS_CHANGED: frozenset(
        {
            "materialization_id",
            "runtime_plugin_id",
            "runtime_plugin_version",
            "declared_status",
            "materialized_status",
        }
    ),
    CanonicalEventType.DECK_PLUGIN_BINDING_CHANGED: frozenset(
        {
            "deck_id",
            "old_exact_release",
            "new_exact_release",
            "binding_revision",
            "actor_id",
        }
    ),
    CanonicalEventType.WORKFLOW_PREFLIGHT_STATUS_CHANGED: frozenset(
        {
            "workflow_preflight_id",
            "status",
            "failed_check",
            "error_code",
            "expires_at",
        }
    ),
    CanonicalEventType.WORKFLOW_RUN_CREATED: frozenset(
        {
            "workflow_run_id",
            "source_voice_thread_id",
            "source_message_id",
            "source_message_time",
            "runtime_plugin_lock_id",
            "runtime_load_receipt_id",
        }
    ),
    CanonicalEventType.WORKFLOW_RUN_STATUS_CHANGED: frozenset(
        {
            "workflow_run_id",
            "old_status",
            "new_status",
            "failed_step",
            "error_code",
        }
    ),
    CanonicalEventType.WORKFLOW_RUN_STEP_PROGRESSED: frozenset(
        {"workflow_run_id", "step_id", "progress", "safe_summary"}
    ),
    CanonicalEventType.WORKFLOW_RESULT_PERSISTED: frozenset(
        {"workflow_run_id", "result_refs", "result_schema_version"}
    ),
    CanonicalEventType.WORKFLOW_RUN_SECURITY_CANCELLED: frozenset(
        {"workflow_run_id", "revocation_policy_ref", "safe_reason"}
    ),
}

_SENSITIVE_KEY_MARKERS = (
    "prompt",
    "secret",
    "password",
    "passwd",
    "api_key",
    "token",
    "credential",
    "authorization",
    "cookie",
    "access_token",
    "refresh_token",
    "private_key",
    "settings",
    "email",
)
_SAFE_REFERENCE_SUFFIXES = ("_id", "_ref", "_hash", "_digest")
_EMAIL_PATTERN = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])")


def _assert_sanitized(value: Any, path: str = "payload") -> None:
    if isinstance(value, dict):
        for raw_key, child in value.items():
            key = str(raw_key).strip().lower().replace("-", "_")
            safe_reference = key.endswith(_SAFE_REFERENCE_SUFFIXES)
            if any(marker in key for marker in _SENSITIVE_KEY_MARKERS) and not (
                safe_reference and ("prompt" in key or "secret" in key or "settings" in key)
            ):
                raise ValueError(f"sensitive event payload field is forbidden: {path}.{raw_key}")
            _assert_sanitized(child, f"{path}.{raw_key}")
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _assert_sanitized(child, f"{path}[{index}]")
        return
    if isinstance(value, str) and _EMAIL_PATTERN.search(value):
        raise ValueError(f"email-like event payload value is forbidden: {path}")


class EventEnvelope(BaseModel):
    """Immutable event envelope whose payload is safe for audit and projection."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )

    event_id: str = Field(pattern=r"^evt_[0-9a-f]{32}$")
    event_type: CanonicalEventType
    event_version: int = Field(ge=1)
    occurred_at: datetime
    workspace_id: str = Field(min_length=1)
    aggregate_id: str = Field(min_length=1)
    aggregate_version: int = Field(ge=1)
    correlation_id: str = Field(min_length=1)
    causation_id: str | None = Field(
        default=None,
        pattern=r"^evt_[0-9a-f]{32}$",
    )
    payload: dict[str, Any]

    @field_validator("payload")
    @classmethod
    def payload_is_json_and_sanitized(cls, payload: dict[str, Any]) -> dict[str, Any]:
        _assert_sanitized(payload)
        try:
            json.dumps(payload, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("event payload must be finite JSON data") from exc
        return payload

    @model_validator(mode="after")
    def canonical_contract_is_complete(self) -> "EventEnvelope":
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone")
        required = REQUIRED_PAYLOAD_FIELDS[self.event_type]
        missing = sorted(required.difference(self.payload))
        if missing:
            raise ValueError(
                f"{self.event_type.value} payload is missing fields: {', '.join(missing)}"
            )
        return self

    def sanitized_projection(self) -> dict[str, Any]:
        """Return the JSON-safe projection consumed by SSE/WebSocket adapters."""

        return self.model_dump(mode="json")
