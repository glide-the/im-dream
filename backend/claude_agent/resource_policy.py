# [Input] Consume the exact Admin resource-observer capability, one fixed system_settings row,
#         a bounded environment/default AgentAdmissionConfig, and an injected PostgreSQL lease factory.
# [Output] Provide a public, one-shot desired-policy provider with applied/not-configured/invalid/unavailable status.
# [Pos] PostgreSQL-only Claude Agent resource-policy boundary used solely by the composition root.
# [Sync] 2026-08-27: clamp unavailable/invalid startup fallbacks to the same finite Admin safety contract.

"""Load one bounded Claude Agent admission policy at process construction time."""
from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from claude_agent.admission import AgentAdmissionConfig
from schema.capabilities import (
    claude_agent_resource_observer_capability_available,
)

ResourcePolicyStatus = Literal[
    "applied",
    "not_configured",
    "invalid",
    "unavailable",
]

RESOURCE_POLICY_CATEGORY = "claude_agent"
RESOURCE_POLICY_KEY = "resource_policy"
RESOURCE_POLICY_SCHEMA_VERSION = 1
RESOURCE_POLICY_BOUNDS = {
    "maxConcurrentRuns": (1, 16),
    "runMemoryBudgetMib": (128, 8_192),
    "memoryReserveMib": (64, 4_096),
    "retryAfterSeconds": (5, 3_600),
}
RESOURCE_POLICY_DEFAULTS = AgentAdmissionConfig(
    max_concurrent_runs=1,
    run_memory_budget_mib=512,
    memory_reserve_mib=128,
    retry_after_seconds=60,
)
_POLICY_FIELDS = frozenset(
    {
        "schemaVersion",
        "revision",
        *RESOURCE_POLICY_BOUNDS,
    }
)


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _row_value(row: Any, key: str, index: int) -> Any:
    if isinstance(row, Mapping):
        return row.get(key)
    return row[index]


def _updated_at_text(value: Any) -> str | None:
    if isinstance(value, datetime):
        normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        return normalized.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_policy(value: Any) -> tuple[AgentAdmissionConfig, int] | None:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return None
    if not isinstance(value, Mapping) or set(value) != _POLICY_FIELDS:
        return None
    schema_version = value.get("schemaVersion")
    revision = value.get("revision")
    if (
        isinstance(schema_version, bool)
        or schema_version != RESOURCE_POLICY_SCHEMA_VERSION
        or isinstance(revision, bool)
        or not isinstance(revision, int)
        or revision < 1
    ):
        return None
    parsed: dict[str, int] = {}
    for key, (minimum, maximum) in RESOURCE_POLICY_BOUNDS.items():
        raw = value.get(key)
        if (
            isinstance(raw, bool)
            or not isinstance(raw, int)
            or raw < minimum
            or raw > maximum
        ):
            return None
        parsed[key] = raw
    return (
        AgentAdmissionConfig(
            max_concurrent_runs=parsed["maxConcurrentRuns"],
            run_memory_budget_mib=parsed["runMemoryBudgetMib"],
            memory_reserve_mib=parsed["memoryReserveMib"],
            retry_after_seconds=parsed["retryAfterSeconds"],
        ),
        revision,
    )


def _bounded_fallback(config: AgentAdmissionConfig) -> AgentAdmissionConfig:
    values = {
        "maxConcurrentRuns": config.max_concurrent_runs,
        "runMemoryBudgetMib": config.run_memory_budget_mib,
        "memoryReserveMib": config.memory_reserve_mib,
        "retryAfterSeconds": config.retry_after_seconds,
    }
    if all(
        minimum <= values[key] <= maximum
        for key, (minimum, maximum) in RESOURCE_POLICY_BOUNDS.items()
    ):
        return config
    return RESOURCE_POLICY_DEFAULTS


@dataclass(frozen=True, slots=True)
class ResourcePolicyLoadResult:
    """Immutable effective configuration and safe desired-policy provenance."""

    config: AgentAdmissionConfig
    defaults: AgentAdmissionConfig
    status: ResourcePolicyStatus
    revision: int | None
    updated_at: str | None
    loaded_at: str


class ClaudeAgentResourcePolicyProvider:
    """Read and validate one Admin-owned desired policy without mutating schema."""

    def __init__(self, db_factory: Callable[[], Any]) -> None:
        self._db_factory = db_factory

    def load(self, fallback: AgentAdmissionConfig) -> ResourcePolicyLoadResult:
        loaded_at = _utc_now_text()
        connection: Any | None = None
        try:
            connection = self._db_factory()
            if not claude_agent_resource_observer_capability_available(connection):
                return self._fallback(fallback, "unavailable", loaded_at)
            row = connection.execute(
                "SELECT value, updated_at FROM system_settings "
                "WHERE category = %s AND key = %s",
                (RESOURCE_POLICY_CATEGORY, RESOURCE_POLICY_KEY),
            ).fetchone()
        except Exception:
            return self._fallback(fallback, "unavailable", loaded_at)
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass
        if row is None:
            return self._fallback(fallback, "not_configured", loaded_at)
        updated_at = _updated_at_text(_row_value(row, "updated_at", 1))
        parsed = _parse_policy(_row_value(row, "value", 0))
        if parsed is None or updated_at is None:
            return self._fallback(fallback, "invalid", loaded_at)
        config, revision = parsed
        return ResourcePolicyLoadResult(
            config=config,
            defaults=RESOURCE_POLICY_DEFAULTS,
            status="applied",
            revision=revision,
            updated_at=updated_at,
            loaded_at=loaded_at,
        )

    @staticmethod
    def _fallback(
        config: AgentAdmissionConfig,
        status: Literal["not_configured", "invalid", "unavailable"],
        loaded_at: str,
    ) -> ResourcePolicyLoadResult:
        return ResourcePolicyLoadResult(
            config=_bounded_fallback(config),
            defaults=RESOURCE_POLICY_DEFAULTS,
            status=status,
            revision=None,
            updated_at=None,
            loaded_at=loaded_at,
        )


__all__ = [
    "ClaudeAgentResourcePolicyProvider",
    "RESOURCE_POLICY_BOUNDS",
    "RESOURCE_POLICY_CATEGORY",
    "RESOURCE_POLICY_DEFAULTS",
    "RESOURCE_POLICY_KEY",
    "RESOURCE_POLICY_SCHEMA_VERSION",
    "ResourcePolicyLoadResult",
    "ResourcePolicyStatus",
]
