# [Input] Consume the public startup resource-policy provider with injected PostgreSQL fakes.
# [Output] Verify capability gating, strict bounds/schema, bounded refresh timing,
#          and monotonic last-known-good refresh behavior.
# [Pos] Provider-free Claude Agent resource policy tests in backend/tests.
# [Sync] 2026-08-27: prove positive concurrency has no product ceiling and invalid refreshes preserve LKG.

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tests._sdk_stubs  # noqa: F401
from claude_agent.admission import AgentAdmissionConfig
from claude_agent.resource_policy import (
    RESOURCE_POLICY_DEFAULTS,
    RESOURCE_POLICY_REFRESH_INTERVAL_SECONDS,
    ClaudeAgentResourcePolicyProvider,
    ClaudeAgentResourcePolicyRefresher,
    ResourcePolicyLoadResult,
    resource_policy_refresh_interval_from_env,
)
from schema.capabilities import (
    CLAUDE_AGENT_RESOURCE_OBSERVER_CAPABILITY,
    CLAUDE_AGENT_RESOURCE_OBSERVER_CONTRACT_SHA256,
    CLAUDE_AGENT_RESOURCE_OBSERVER_VERSION,
)


class _Cursor:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _Connection:
    def __init__(self, policy_row, *, capability_hash=None):
        self.policy_row = policy_row
        self.capability_hash = capability_hash
        self.queries: list[str] = []
        self.closed = False

    def execute(self, query, parameters=()):
        self.queries.append(query)
        if "drizzle.schema_capabilities" in query:
            assert parameters == (CLAUDE_AGENT_RESOURCE_OBSERVER_CAPABILITY,)
            if self.capability_hash is None:
                return _Cursor(None)
            return _Cursor(
                (
                    CLAUDE_AGENT_RESOURCE_OBSERVER_VERSION,
                    self.capability_hash,
                )
            )
        if "FROM system_settings" in query:
            assert parameters == ("claude_agent", "resource_policy")
            return _Cursor(self.policy_row)
        raise AssertionError(query)

    def close(self):
        self.closed = True


_FALLBACK = AgentAdmissionConfig(
    max_concurrent_runs=2,
    run_memory_budget_mib=640,
    memory_reserve_mib=192,
    retry_after_seconds=90,
)
_POLICY = {
    "schemaVersion": 1,
    "revision": 7,
    "maxConcurrentRuns": 3,
    "runMemoryBudgetMib": 768,
    "memoryReserveMib": 256,
    "retryAfterSeconds": 120,
}


def test_valid_policy_applies_exact_values_and_provenance() -> None:
    connection = _Connection(
        (_POLICY, datetime(2026, 8, 27, tzinfo=timezone.utc)),
        capability_hash=CLAUDE_AGENT_RESOURCE_OBSERVER_CONTRACT_SHA256,
    )

    loaded = ClaudeAgentResourcePolicyProvider(lambda: connection).load(_FALLBACK)

    assert loaded.status == "applied"
    assert loaded.revision == 7
    assert loaded.updated_at == "2026-08-27T00:00:00Z"
    assert loaded.config == AgentAdmissionConfig(3, 768, 256, 120)
    assert connection.closed is True
    assert all(query.lstrip().upper().startswith("SELECT") for query in connection.queries)


def test_arbitrarily_large_concurrency_policy_is_valid_without_product_cap() -> None:
    large_value = 10**30
    policy = {**_POLICY, "maxConcurrentRuns": large_value}
    connection = _Connection(
        (policy, datetime(2026, 8, 27, tzinfo=timezone.utc)),
        capability_hash=CLAUDE_AGENT_RESOURCE_OBSERVER_CONTRACT_SHA256,
    )

    loaded = ClaudeAgentResourcePolicyProvider(lambda: connection).load(_FALLBACK)

    assert loaded.status == "applied"
    assert loaded.config.max_concurrent_runs == large_value


def test_missing_policy_retains_finite_fallback() -> None:
    connection = _Connection(
        None,
        capability_hash=CLAUDE_AGENT_RESOURCE_OBSERVER_CONTRACT_SHA256,
    )

    loaded = ClaudeAgentResourcePolicyProvider(lambda: connection).load(_FALLBACK)

    assert loaded.status == "not_configured"
    assert loaded.config is _FALLBACK
    assert loaded.revision is None


def test_invalid_policy_never_partially_applies() -> None:
    invalid_values = (
        {**_POLICY, "unknown": 1},
        {**_POLICY, "maxConcurrentRuns": 0},
        {**_POLICY, "maxConcurrentRuns": -1},
        {**_POLICY, "maxConcurrentRuns": 1.5},
        {**_POLICY, "maxConcurrentRuns": "2"},
        {**_POLICY, "maxConcurrentRuns": True},
        {**_POLICY, "maxConcurrentRuns": None},
        {**_POLICY, "runMemoryBudgetMib": 8193},
        {**_POLICY, "revision": True},
        {**_POLICY, "schemaVersion": 2},
    )
    for value in invalid_values:
        connection = _Connection(
            (value, "2026-08-27T00:00:00Z"),
            capability_hash=CLAUDE_AGENT_RESOURCE_OBSERVER_CONTRACT_SHA256,
        )
        loaded = ClaudeAgentResourcePolicyProvider(lambda: connection).load(_FALLBACK)
        assert loaded.status == "invalid"
        assert loaded.config is _FALLBACK
        assert loaded.revision is None


def test_capability_drift_and_database_failure_are_unavailable() -> None:
    drifted = _Connection((_POLICY, "2026-08-27T00:00:00Z"), capability_hash="a" * 64)
    drifted_load = ClaudeAgentResourcePolicyProvider(lambda: drifted).load(_FALLBACK)
    failed_load = ClaudeAgentResourcePolicyProvider(
        lambda: (_ for _ in ()).throw(OSError("database unavailable"))
    ).load(_FALLBACK)

    assert drifted_load.status == "unavailable"
    assert failed_load.status == "unavailable"
    assert drifted_load.config is _FALLBACK
    assert failed_load.config is _FALLBACK


def test_out_of_contract_environment_fallback_uses_safe_defaults() -> None:
    unsafe = AgentAdmissionConfig(
        max_concurrent_runs=100,
        run_memory_budget_mib=1,
        memory_reserve_mib=0,
        retry_after_seconds=1,
    )
    connection = _Connection(
        None,
        capability_hash=CLAUDE_AGENT_RESOURCE_OBSERVER_CONTRACT_SHA256,
    )

    loaded = ClaudeAgentResourcePolicyProvider(lambda: connection).load(unsafe)

    assert loaded.status == "not_configured"
    assert loaded.config == AgentAdmissionConfig(1, 512, 128, 60)


def test_large_bounded_environment_fallback_is_not_product_capped() -> None:
    high_concurrency = AgentAdmissionConfig(
        max_concurrent_runs=1_000_000,
        run_memory_budget_mib=640,
        memory_reserve_mib=192,
        retry_after_seconds=90,
    )
    connection = _Connection(
        None,
        capability_hash=CLAUDE_AGENT_RESOURCE_OBSERVER_CONTRACT_SHA256,
    )

    loaded = ClaudeAgentResourcePolicyProvider(lambda: connection).load(
        high_concurrency
    )

    assert loaded.status == "not_configured"
    assert loaded.config is high_concurrency


def test_invalid_dynamic_concurrency_refresh_retains_last_known_good() -> None:
    valid_connection = _Connection(
        (
            {**_POLICY, "maxConcurrentRuns": 10**30},
            "2026-08-27T00:00:00Z",
        ),
        capability_hash=CLAUDE_AGENT_RESOURCE_OBSERVER_CONTRACT_SHA256,
    )
    initial = ClaudeAgentResourcePolicyProvider(lambda: valid_connection).load(
        _FALLBACK
    )
    invalid_connection = _Connection(
        (
            {
                **_POLICY,
                "revision": 8,
                "maxConcurrentRuns": 0,
            },
            "2026-08-27T00:01:00Z",
        ),
        capability_hash=CLAUDE_AGENT_RESOURCE_OBSERVER_CONTRACT_SHA256,
    )
    provider = ClaudeAgentResourcePolicyProvider(lambda: invalid_connection)
    observed: list[ResourcePolicyLoadResult] = []
    refresher = ClaudeAgentResourcePolicyRefresher(
        provider=provider,
        current_config=lambda: initial.config,
        apply_result=observed.append,
        initial_result=initial,
        interval_seconds=1,
    )

    resolved = asyncio.run(refresher.refresh_once())

    assert resolved.status == "invalid"
    assert resolved.config == initial.config
    assert resolved.revision == initial.revision == 7
    assert resolved.updated_at == initial.updated_at == "2026-08-27T00:00:00Z"
    assert observed == [resolved]


def test_refresh_interval_is_bounded_and_invalid_values_use_safe_default() -> None:
    for raw in (None, "", "0", "301", "nan", "inf", "invalid"):
        environment = {} if raw is None else {
            "INK_AGENT_RESOURCE_POLICY_REFRESH_INTERVAL_S": raw
        }
        with mock.patch.dict(os.environ, environment, clear=True):
            assert (
                resource_policy_refresh_interval_from_env()
                == RESOURCE_POLICY_REFRESH_INTERVAL_SECONDS
            )
    with mock.patch.dict(
        os.environ,
        {"INK_AGENT_RESOURCE_POLICY_REFRESH_INTERVAL_S": "12.5"},
        clear=True,
    ):
        assert resource_policy_refresh_interval_from_env() == 12.5


def _load_result(
    *,
    config: AgentAdmissionConfig,
    status: str,
    revision: int | None,
    updated_at: str | None,
    loaded_at: str,
) -> ResourcePolicyLoadResult:
    return ResourcePolicyLoadResult(
        config=config,
        defaults=RESOURCE_POLICY_DEFAULTS,
        status=status,  # type: ignore[arg-type]
        revision=revision,
        updated_at=updated_at,
        loaded_at=loaded_at,
    )


def test_refresher_rejects_rollback_and_retains_last_applied_provenance() -> None:
    initial = _load_result(
        config=_FALLBACK,
        status="applied",
        revision=7,
        updated_at="2026-08-27T00:00:00Z",
        loaded_at="2026-08-27T00:00:01Z",
    )
    changed = AgentAdmissionConfig(1, 512, 128, 60)
    pending = [
        _load_result(
            config=changed,
            status="applied",
            revision=6,
            updated_at="2026-08-27T00:01:00Z",
            loaded_at="2026-08-27T00:01:01Z",
        ),
        _load_result(
            config=changed,
            status="applied",
            revision=7,
            updated_at="2026-08-27T00:02:00Z",
            loaded_at="2026-08-27T00:02:01Z",
        ),
        _load_result(
            config=_FALLBACK,
            status="unavailable",
            revision=None,
            updated_at=None,
            loaded_at="2026-08-27T00:03:01Z",
        ),
        _load_result(
            config=_FALLBACK,
            status="applied",
            revision=7,
            updated_at="2026-08-27T00:04:00Z",
            loaded_at="2026-08-27T00:04:01Z",
        ),
        _load_result(
            config=changed,
            status="applied",
            revision=8,
            updated_at="2026-08-27T00:05:00Z",
            loaded_at="2026-08-27T00:05:01Z",
        ),
    ]

    class _Provider:
        def load(self, _fallback):
            return pending.pop(0)

    current = initial.config
    observed: list[ResourcePolicyLoadResult] = []

    def apply_result(result: ResourcePolicyLoadResult) -> None:
        nonlocal current
        observed.append(result)
        if result.status == "applied":
            current = result.config

    refresher = ClaudeAgentResourcePolicyRefresher(
        provider=_Provider(),  # type: ignore[arg-type]
        current_config=lambda: current,
        apply_result=apply_result,
        initial_result=initial,
        interval_seconds=1,
    )

    async def exercise() -> None:
        for _ in range(5):
            await refresher.refresh_once()

    asyncio.run(exercise())

    assert [result.status for result in observed] == [
        "invalid",
        "invalid",
        "unavailable",
        "applied",
        "applied",
    ]
    assert [result.revision for result in observed] == [7, 7, 7, 7, 8]
    assert [result.updated_at for result in observed[:3]] == [
        "2026-08-27T00:00:00Z",
        "2026-08-27T00:00:00Z",
        "2026-08-27T00:00:00Z",
    ]
    assert all(result.config == _FALLBACK for result in observed[:4])
    assert observed[-1].config == changed


def test_refresher_start_repeats_until_stop() -> None:
    initial = _load_result(
        config=_FALLBACK,
        status="applied",
        revision=7,
        updated_at="2026-08-27T00:00:00Z",
        loaded_at="2026-08-27T00:00:01Z",
    )

    class _Provider:
        def load(self, _fallback):
            return initial

    async def exercise() -> int:
        applied_count = 0
        repeated = asyncio.Event()

        def apply_result(_result: ResourcePolicyLoadResult) -> None:
            nonlocal applied_count
            applied_count += 1
            if applied_count >= 2:
                repeated.set()

        refresher = ClaudeAgentResourcePolicyRefresher(
            provider=_Provider(),  # type: ignore[arg-type]
            current_config=lambda: _FALLBACK,
            apply_result=apply_result,
            initial_result=initial,
            interval_seconds=0.01,
        )
        refresher.start()
        await asyncio.wait_for(repeated.wait(), timeout=0.5)
        await refresher.stop()
        return applied_count

    assert asyncio.run(exercise()) >= 2
