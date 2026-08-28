# [Input] Consume the public startup resource-policy provider with injected PostgreSQL fakes.
# [Output] Verify capability gating, safe-integer/combined-memory schema, bounded refresh timing,
#          and monotonic last-known-good refresh behavior.
# [Pos] Provider-free Claude Agent resource policy tests in backend/tests.
# [Sync] 2026-08-28: prove exact technical boundaries, nullable Runtime effort,
#                    monotonic LKG, and background refresh exception isolation.

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
from claude_agent.admission import (
    AGENT_RESOURCE_JSON_SAFE_INTEGER_MAX,
    AGENT_RESOURCE_MAX_COMBINED_MEMORY_MIB,
    AgentAdmissionConfig,
)
from claude_agent.resource_policy import (
    RESOURCE_POLICY_DEFAULTS,
    RESOURCE_POLICY_REFRESH_INTERVAL_SECONDS,
    ClaudeAgentResourcePolicyProvider,
    ClaudeAgentResourcePolicyRefresher,
    ClaudeCodeRuntimePolicyStore,
    ResourcePolicyLoadResult,
    resource_policy_refresh_interval_from_env,
)
from schema.capabilities import (
    CLAUDE_AGENT_RESOURCE_OBSERVER_CAPABILITY,
    CLAUDE_AGENT_RESOURCE_OBSERVER_CONTRACT_SHA256,
    CLAUDE_AGENT_RESOURCE_OBSERVER_VERSION,
    CLAUDE_CODE_RUNTIME_CONFIG_CAPABILITY,
    CLAUDE_CODE_RUNTIME_CONFIG_CONTRACT_SHA256,
    CLAUDE_CODE_RUNTIME_CONFIG_VERSION,
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
            if self.capability_hash is None:
                return _Cursor(None)
            if parameters == (CLAUDE_CODE_RUNTIME_CONFIG_CAPABILITY,):
                return _Cursor(
                    (
                        CLAUDE_CODE_RUNTIME_CONFIG_VERSION,
                        CLAUDE_CODE_RUNTIME_CONFIG_CONTRACT_SHA256,
                    )
                )
            assert parameters == (CLAUDE_AGENT_RESOURCE_OBSERVER_CAPABILITY,)
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


def test_global_effort_is_optional_validated_and_projected_as_env() -> None:
    configured = _Connection(
        ({**_POLICY, "claudeCodeEffortLevel": "high"}, "2026-08-27T00:00:00Z"),
        capability_hash=CLAUDE_AGENT_RESOURCE_OBSERVER_CONTRACT_SHA256,
    )
    loaded = ClaudeAgentResourcePolicyProvider(lambda: configured).load(_FALLBACK)
    assert loaded.status == "applied"
    assert loaded.claude_code_effort_level == "high"
    store = ClaudeCodeRuntimePolicyStore(loaded)
    assert store.snapshot_env() == {"CLAUDE_CODE_EFFORT_LEVEL": "high"}

    invalid = _Connection(
        ({**_POLICY, "claudeCodeEffortLevel": "ultra"}, "2026-08-27T00:00:00Z"),
        capability_hash=CLAUDE_AGENT_RESOURCE_OBSERVER_CONTRACT_SHA256,
    )
    rejected = ClaudeAgentResourcePolicyProvider(lambda: invalid).load(_FALLBACK)
    assert rejected.status == "invalid"
    assert ClaudeCodeRuntimePolicyStore(rejected).snapshot_env() == {}


def test_higher_revision_effort_only_change_requires_public_replacement() -> None:
    initial = ResourcePolicyLoadResult(
        config=_FALLBACK,
        defaults=RESOURCE_POLICY_DEFAULTS,
        status="applied",
        revision=7,
        updated_at="2026-08-27T00:00:00Z",
        loaded_at="2026-08-27T00:00:01Z",
        claude_code_effort_level="medium",
    )

    class _Provider:
        def load(self, _fallback):
            return ResourcePolicyLoadResult(
                config=_FALLBACK,
                defaults=RESOURCE_POLICY_DEFAULTS,
                status="applied",
                revision=8,
                updated_at="2026-08-27T00:01:00Z",
                loaded_at="2026-08-27T00:01:01Z",
                claude_code_effort_level="high",
            )

    observed: list[tuple[ResourcePolicyLoadResult, bool]] = []
    refresher = ClaudeAgentResourcePolicyRefresher(
        provider=_Provider(),  # type: ignore[arg-type]
        current_config=lambda: _FALLBACK,
        apply_result=lambda result, replace_required: observed.append(
            (result, replace_required)
        ),
        initial_result=initial,
    )
    resolved = asyncio.run(refresher.refresh_once())
    assert resolved.claude_code_effort_level == "high"
    assert observed == [(resolved, True)]


def test_values_above_historical_product_caps_are_valid() -> None:
    policy = {
        **_POLICY,
        "maxConcurrentRuns": 17,
        "runMemoryBudgetMib": 8_193,
        "memoryReserveMib": 4_097,
        "retryAfterSeconds": 3_601,
    }
    connection = _Connection(
        (policy, datetime(2026, 8, 27, tzinfo=timezone.utc)),
        capability_hash=CLAUDE_AGENT_RESOURCE_OBSERVER_CONTRACT_SHA256,
    )

    loaded = ClaudeAgentResourcePolicyProvider(lambda: connection).load(_FALLBACK)

    assert loaded.status == "applied"
    assert loaded.config == AgentAdmissionConfig(17, 8_193, 4_097, 3_601)


def test_safe_integer_and_combined_memory_exact_boundaries() -> None:
    exact = {
        **_POLICY,
        "maxConcurrentRuns": AGENT_RESOURCE_JSON_SAFE_INTEGER_MAX,
        "runMemoryBudgetMib": AGENT_RESOURCE_MAX_COMBINED_MEMORY_MIB - 1,
        "memoryReserveMib": 1,
        "retryAfterSeconds": AGENT_RESOURCE_JSON_SAFE_INTEGER_MAX,
    }
    connection = _Connection(
        (exact, datetime(2026, 8, 27, tzinfo=timezone.utc)),
        capability_hash=CLAUDE_AGENT_RESOURCE_OBSERVER_CONTRACT_SHA256,
    )

    loaded = ClaudeAgentResourcePolicyProvider(lambda: connection).load(_FALLBACK)

    assert loaded.status == "applied"
    assert loaded.config.max_concurrent_runs == AGENT_RESOURCE_JSON_SAFE_INTEGER_MAX
    assert loaded.config.required_headroom_bytes <= AGENT_RESOURCE_JSON_SAFE_INTEGER_MAX

    over_combined = {
        **exact,
        "runMemoryBudgetMib": AGENT_RESOURCE_MAX_COMBINED_MEMORY_MIB,
    }
    overflow_connection = _Connection(
        (over_combined, "2026-08-27T00:00:00Z"),
        capability_hash=CLAUDE_AGENT_RESOURCE_OBSERVER_CONTRACT_SHA256,
    )
    overflow = ClaudeAgentResourcePolicyProvider(
        lambda: overflow_connection
    ).load(_FALLBACK)

    assert overflow.status == "invalid"
    assert overflow.config is _FALLBACK


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
        {**_POLICY, "runMemoryBudgetMib": 0},
        {**_POLICY, "memoryReserveMib": 0},
        {**_POLICY, "retryAfterSeconds": 0},
        {**_POLICY, "retryAfterSeconds": None},
        {**_POLICY, "runMemoryBudgetMib": False},
        {**_POLICY, "memoryReserveMib": "128"},
        {**_POLICY, "retryAfterSeconds": 1.5},
        {
            **_POLICY,
            "maxConcurrentRuns": AGENT_RESOURCE_JSON_SAFE_INTEGER_MAX + 1,
        },
        {
            **_POLICY,
            "runMemoryBudgetMib": AGENT_RESOURCE_JSON_SAFE_INTEGER_MAX + 1,
        },
        {
            **_POLICY,
            "memoryReserveMib": AGENT_RESOURCE_JSON_SAFE_INTEGER_MAX + 1,
        },
        {
            **_POLICY,
            "retryAfterSeconds": AGENT_RESOURCE_JSON_SAFE_INTEGER_MAX + 1,
        },
        {**_POLICY, "revision": AGENT_RESOURCE_JSON_SAFE_INTEGER_MAX + 1},
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


def test_large_valid_environment_fallback_is_not_product_capped() -> None:
    large_valid = AgentAdmissionConfig(
        max_concurrent_runs=17,
        run_memory_budget_mib=8_193,
        memory_reserve_mib=4_097,
        retry_after_seconds=3_601,
    )
    connection = _Connection(
        None,
        capability_hash=CLAUDE_AGENT_RESOURCE_OBSERVER_CONTRACT_SHA256,
    )

    loaded = ClaudeAgentResourcePolicyProvider(lambda: connection).load(
        large_valid
    )

    assert loaded.status == "not_configured"
    assert loaded.config is large_valid


def test_invalid_dynamic_concurrency_refresh_retains_last_known_good() -> None:
    valid_connection = _Connection(
        (
            {**_POLICY, "maxConcurrentRuns": AGENT_RESOURCE_JSON_SAFE_INTEGER_MAX},
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
    observed: list[tuple[ResourcePolicyLoadResult, bool]] = []
    refresher = ClaudeAgentResourcePolicyRefresher(
        provider=provider,
        current_config=lambda: initial.config,
        apply_result=lambda result, replace_required: observed.append(
            (result, replace_required)
        ),
        initial_result=initial,
        interval_seconds=1,
    )

    resolved = asyncio.run(refresher.refresh_once())

    assert resolved.status == "invalid"
    assert resolved.config == initial.config
    assert resolved.revision == initial.revision == 7
    assert resolved.updated_at == initial.updated_at == "2026-08-27T00:00:00Z"
    assert observed == [(resolved, False)]


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
    observed: list[tuple[ResourcePolicyLoadResult, bool]] = []

    def apply_result(
        result: ResourcePolicyLoadResult,
        replace_required: bool,
    ) -> None:
        nonlocal current
        observed.append((result, replace_required))
        if replace_required:
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

    results = [result for result, _replace_required in observed]
    assert [result.status for result in results] == [
        "invalid",
        "invalid",
        "unavailable",
        "applied",
        "applied",
    ]
    assert [result.revision for result in results] == [7, 7, 7, 7, 8]
    assert [result.updated_at for result in results[:3]] == [
        "2026-08-27T00:00:00Z",
        "2026-08-27T00:00:00Z",
        "2026-08-27T00:00:00Z",
    ]
    assert all(result.config == _FALLBACK for result in results[:4])
    assert results[-1].config == changed
    assert [replace_required for _result, replace_required in observed] == [
        False,
        False,
        False,
        False,
        True,
    ]


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

        def apply_result(
            _result: ResourcePolicyLoadResult,
            _replace_required: bool,
        ) -> None:
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


def test_refresher_background_callback_exception_is_isolated_and_retried() -> None:
    initial = _load_result(
        config=_FALLBACK,
        status="applied",
        revision=7,
        updated_at="2026-08-27T00:00:00Z",
        loaded_at="2026-08-27T00:00:01Z",
    )

    class _Provider:
        def load(self, _fallback):
            return _load_result(
                config=AgentAdmissionConfig(1, 768, 256, 120),
                status="applied",
                revision=8,
                updated_at="2026-08-27T00:01:00Z",
                loaded_at="2026-08-27T00:01:01Z",
            )

    async def exercise() -> tuple[int, list[bool]]:
        attempts = 0
        current = initial.config
        replace_attempts: list[bool] = []
        recovered = asyncio.Event()

        def apply_result(
            result: ResourcePolicyLoadResult,
            replace_required: bool,
        ) -> None:
            nonlocal attempts, current
            attempts += 1
            replace_attempts.append(replace_required)
            if replace_required:
                current = result.config
            if attempts == 1:
                raise RuntimeError("injected callback failure")
            recovered.set()

        refresher = ClaudeAgentResourcePolicyRefresher(
            provider=_Provider(),  # type: ignore[arg-type]
            current_config=lambda: current,
            apply_result=apply_result,
            initial_result=initial,
            interval_seconds=0.01,
        )
        refresher.start()
        await asyncio.wait_for(recovered.wait(), timeout=0.5)
        await refresher.stop()
        return attempts, replace_attempts

    attempts, replace_attempts = asyncio.run(exercise())
    assert attempts >= 2
    # A callback failure must not advance the committed revision. Retrying the
    # same higher revision re-enters the public replacement boundary so an
    # admission-only partial callback cannot strand the Runtime effort store.
    assert replace_attempts[:2] == [True, True]
