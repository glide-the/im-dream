# [Input] Consume exact Admin resource/Runtime capabilities, one fixed system_settings
#         row, JSON-safe admission defaults, and an injected PostgreSQL lease factory.
# [Output] Provide a public admission/global-effort provider and isolated periodic
#          refresher with applied/not-configured/invalid/unavailable LKG status.
# [Pos] PostgreSQL-only Claude Agent resource-policy boundary composed by agent_factory.
# [Sync] 2026-08-28: add optional SDK-backed global effort; a higher revision atomically
#                    replaces admission and Runtime policy while failures retain both LKGs.

"""Load and periodically refresh one validated Claude Agent admission policy."""
from __future__ import annotations

import asyncio
import json
import logging
import math
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from claude_agent.admission import (
    AGENT_RESOURCE_JSON_SAFE_INTEGER_MAX,
    AgentAdmissionConfig,
    validate_agent_admission_config,
)
from schema.capabilities import (
    claude_agent_resource_observer_capability_available,
    claude_code_runtime_config_capability_available,
)

logger = logging.getLogger(__name__)

ResourcePolicyStatus = Literal[
    "applied",
    "not_configured",
    "invalid",
    "unavailable",
]

RESOURCE_POLICY_CATEGORY = "claude_agent"
RESOURCE_POLICY_KEY = "resource_policy"
RESOURCE_POLICY_SCHEMA_VERSION = 1
RESOURCE_POLICY_REFRESH_INTERVAL_SECONDS = 5.0
RESOURCE_POLICY_REFRESH_INTERVAL_ENV = "INK_AGENT_RESOURCE_POLICY_REFRESH_INTERVAL_S"
_RESOURCE_POLICY_REFRESH_INTERVAL_MIN_SECONDS = 1.0
_RESOURCE_POLICY_REFRESH_INTERVAL_MAX_SECONDS = 300.0
RESOURCE_POLICY_BOUNDS = {
    "maxConcurrentRuns": (1, AGENT_RESOURCE_JSON_SAFE_INTEGER_MAX),
    "runMemoryBudgetMib": (1, AGENT_RESOURCE_JSON_SAFE_INTEGER_MAX),
    "memoryReserveMib": (1, AGENT_RESOURCE_JSON_SAFE_INTEGER_MAX),
    "retryAfterSeconds": (1, AGENT_RESOURCE_JSON_SAFE_INTEGER_MAX),
}
RESOURCE_POLICY_DEFAULTS = AgentAdmissionConfig(
    max_concurrent_runs=1,
    run_memory_budget_mib=512,
    memory_reserve_mib=128,
    retry_after_seconds=60,
)
CLAUDE_CODE_EFFORT_LEVELS = frozenset({"low", "medium", "high", "xhigh", "max"})
_LEGACY_POLICY_FIELDS = frozenset(
    {
        "schemaVersion",
        "revision",
        *RESOURCE_POLICY_BOUNDS,
    }
)
_POLICY_FIELDS = _LEGACY_POLICY_FIELDS | {"claudeCodeEffortLevel"}


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def resource_policy_refresh_interval_from_env() -> float:
    """Resolve the bounded process-local poll interval; invalid input uses 5s."""

    raw = os.getenv(RESOURCE_POLICY_REFRESH_INTERVAL_ENV)
    if raw is None or not raw.strip():
        return RESOURCE_POLICY_REFRESH_INTERVAL_SECONDS
    try:
        parsed = float(raw)
    except ValueError:
        return RESOURCE_POLICY_REFRESH_INTERVAL_SECONDS
    if (
        not math.isfinite(parsed)
        or parsed < _RESOURCE_POLICY_REFRESH_INTERVAL_MIN_SECONDS
        or parsed > _RESOURCE_POLICY_REFRESH_INTERVAL_MAX_SECONDS
    ):
        return RESOURCE_POLICY_REFRESH_INTERVAL_SECONDS
    return parsed


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


def _parse_policy(
    value: Any,
) -> tuple[AgentAdmissionConfig, int, str | None] | None:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return None
    if not isinstance(value, Mapping):
        return None
    observed_fields = frozenset(value)
    if observed_fields not in {_LEGACY_POLICY_FIELDS, _POLICY_FIELDS}:
        return None
    schema_version = value.get("schemaVersion")
    revision = value.get("revision")
    if (
        isinstance(schema_version, bool)
        or schema_version != RESOURCE_POLICY_SCHEMA_VERSION
        or isinstance(revision, bool)
        or not isinstance(revision, int)
        or revision < 1
        or revision > AGENT_RESOURCE_JSON_SAFE_INTEGER_MAX
    ):
        return None
    parsed: dict[str, int] = {}
    for key, (minimum, maximum) in RESOURCE_POLICY_BOUNDS.items():
        raw = value.get(key)
        if (
            isinstance(raw, bool)
            or not isinstance(raw, int)
            or raw < minimum
            or (maximum is not None and raw > maximum)
        ):
            return None
        parsed[key] = raw
    effort_level = value.get("claudeCodeEffortLevel")
    if effort_level is not None and effort_level not in CLAUDE_CODE_EFFORT_LEVELS:
        return None
    try:
        config = validate_agent_admission_config(
            AgentAdmissionConfig(
                max_concurrent_runs=parsed["maxConcurrentRuns"],
                run_memory_budget_mib=parsed["runMemoryBudgetMib"],
                memory_reserve_mib=parsed["memoryReserveMib"],
                retry_after_seconds=parsed["retryAfterSeconds"],
            )
        )
    except (TypeError, ValueError):
        return None
    return config, revision, effort_level


def _bounded_fallback(config: AgentAdmissionConfig) -> AgentAdmissionConfig:
    try:
        return validate_agent_admission_config(config)
    except (TypeError, ValueError):
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
    claude_code_effort_level: str | None = None


class ClaudeCodeRuntimePolicyStore:
    """Public immutable replacement boundary for the effective global Runtime policy."""

    def __init__(self, initial_result: ResourcePolicyLoadResult) -> None:
        self._effort_level = (
            initial_result.claude_code_effort_level
            if initial_result.status == "applied"
            else None
        )

    def replace(self, result: ResourcePolicyLoadResult) -> None:
        if result.status != "applied":
            raise ValueError("only an applied policy may replace Runtime config")
        self._effort_level = result.claude_code_effort_level

    def snapshot_env(self) -> dict[str, str]:
        effort_level = self._effort_level
        return (
            {"CLAUDE_CODE_EFFORT_LEVEL": effort_level}
            if effort_level is not None
            else {}
        )


class ClaudeAgentResourcePolicyProvider:
    """Read and validate one Admin-owned desired policy without mutating schema."""

    def __init__(self, db_factory: Callable[[], Any]) -> None:
        self._db_factory = db_factory

    def load(self, fallback: AgentAdmissionConfig) -> ResourcePolicyLoadResult:
        loaded_at = _utc_now_text()
        connection: Any | None = None
        try:
            connection = self._db_factory()
            if (
                not claude_agent_resource_observer_capability_available(connection)
                or not claude_code_runtime_config_capability_available(connection)
            ):
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
        config, revision, effort_level = parsed
        return ResourcePolicyLoadResult(
            config=config,
            defaults=RESOURCE_POLICY_DEFAULTS,
            status="applied",
            revision=revision,
            updated_at=updated_at,
            loaded_at=loaded_at,
            claude_code_effort_level=effort_level,
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


class ClaudeAgentResourcePolicyRefresher:
    """Periodically load desired policy off-path and hand off an immutable result."""

    def __init__(
        self,
        *,
        provider: ClaudeAgentResourcePolicyProvider,
        current_config: Callable[[], AgentAdmissionConfig],
        apply_result: Callable[[ResourcePolicyLoadResult, bool], None],
        initial_result: ResourcePolicyLoadResult,
        interval_seconds: float = RESOURCE_POLICY_REFRESH_INTERVAL_SECONDS,
    ) -> None:
        self._provider = provider
        self._current_config = current_config
        self._apply_result = apply_result
        self._interval_seconds = max(0.01, float(interval_seconds))
        self._last_applied = (
            initial_result if initial_result.status == "applied" else None
        )
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(
                self._run(),
                name="claude-agent-resource-policy-refresher",
            )

    async def stop(self) -> None:
        task = self._task
        self._task = None
        if task is None or task.done():
            return
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def refresh_once(self) -> ResourcePolicyLoadResult:
        """Load off the Agent path; cancellation drains the database operation."""

        fallback = self._current_config()
        operation = asyncio.create_task(
            asyncio.to_thread(self._provider.load, fallback)
        )
        try:
            result = await asyncio.shield(operation)
        except asyncio.CancelledError:
            try:
                await operation
            except Exception:
                pass
            raise
        resolved, replace_required = self._resolve_monotonic(result, fallback)
        self._apply_result(resolved, replace_required)
        if resolved.status == "applied":
            self._last_applied = resolved
        return resolved

    def _resolve_monotonic(
        self,
        result: ResourcePolicyLoadResult,
        fallback: AgentAdmissionConfig,
    ) -> tuple[ResourcePolicyLoadResult, bool]:
        previous = self._last_applied
        if result.status != "applied":
            return self._retain_last_applied(result, previous), False
        if previous is None:
            return result, True
        assert result.revision is not None
        assert previous.revision is not None
        if result.revision > previous.revision:
            return result, True
        if (
            result.revision == previous.revision
            and result.config == previous.config
            and result.claude_code_effort_level
            == previous.claude_code_effort_level
        ):
            return result, False
        return (
            self._retain_last_applied(
                ResourcePolicyLoadResult(
                    config=_bounded_fallback(fallback),
                    defaults=result.defaults,
                    status="invalid",
                    revision=None,
                    updated_at=None,
                    loaded_at=result.loaded_at,
                ),
                previous,
            ),
            False,
        )

    @staticmethod
    def _retain_last_applied(
        result: ResourcePolicyLoadResult,
        previous: ResourcePolicyLoadResult | None,
    ) -> ResourcePolicyLoadResult:
        if previous is None:
            return result
        return ResourcePolicyLoadResult(
            config=previous.config,
            defaults=result.defaults,
            status=result.status,
            revision=previous.revision,
            updated_at=previous.updated_at,
            loaded_at=result.loaded_at,
            claude_code_effort_level=previous.claude_code_effort_level,
        )

    async def _run(self) -> None:
        while True:
            try:
                await self.refresh_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning(
                    "Claude Agent resource policy refresh failed: code=refresh_error"
                )
            await asyncio.sleep(self._interval_seconds)

__all__ = [
    "ClaudeAgentResourcePolicyProvider",
    "ClaudeAgentResourcePolicyRefresher",
    "RESOURCE_POLICY_BOUNDS",
    "RESOURCE_POLICY_CATEGORY",
    "RESOURCE_POLICY_DEFAULTS",
    "RESOURCE_POLICY_KEY",
    "RESOURCE_POLICY_REFRESH_INTERVAL_SECONDS",
    "RESOURCE_POLICY_REFRESH_INTERVAL_ENV",
    "RESOURCE_POLICY_SCHEMA_VERSION",
    "CLAUDE_CODE_EFFORT_LEVELS",
    "ClaudeCodeRuntimePolicyStore",
    "ResourcePolicyLoadResult",
    "ResourcePolicyStatus",
    "resource_policy_refresh_interval_from_env",
]
