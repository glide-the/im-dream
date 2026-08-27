# [Input] Consume the public startup resource-policy provider with injected PostgreSQL fakes.
# [Output] Verify exact capability gating, strict bounds/schema, provenance, and Admin-bounded fallback states.
# [Pos] Provider-free Claude Agent resource policy tests in backend/tests.
# [Sync] 2026-08-27: prove invalid environment fallbacks collapse to finite policy defaults.

from __future__ import annotations

from datetime import datetime, timezone

from claude_agent.admission import AgentAdmissionConfig
from claude_agent.resource_policy import ClaudeAgentResourcePolicyProvider
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
