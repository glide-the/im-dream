# [Input] Consume the capacity-one publisher/sink with strict DTO and injected PostgreSQL fakes.
# [Output] Verify latest replacement, timeout isolation/serialization, DB-clock upsert/TTL, and snapshot privacy.
# [Pos] Provider-free PostgreSQL resource synchronization tests in backend/tests.
# [Sync] 2026-08-27: prove timed-out writes remain single-file and database time owns freshness columns.

from __future__ import annotations

import asyncio
import json
import time
from uuid import UUID

import pytest
from pydantic import ValidationError

from claude_agent.resource_diagnostics import ClaudeAgentResourceDiagnosticsDTO
from claude_agent.resource_postgres_sink import (
    ClaudeAgentResourcePostgresSink,
    ResourcePipelineMetrics,
)
from schema.capabilities import (
    CLAUDE_AGENT_RESOURCE_OBSERVER_CAPABILITY,
    CLAUDE_AGENT_RESOURCE_OBSERVER_CONTRACT_SHA256,
    CLAUDE_AGENT_RESOURCE_OBSERVER_VERSION,
)


def _snapshot(*, started: int = 0) -> ClaudeAgentResourceDiagnosticsDTO:
    values = {
        "max_concurrent_runs": 1,
        "run_memory_budget_mib": 512,
        "memory_reserve_mib": 128,
        "retry_after_seconds": 60,
        "required_headroom_bytes": 671088640,
    }
    return ClaudeAgentResourceDiagnosticsDTO.model_validate(
        {
            "schema_version": 1,
            "backend_status": "ok",
            "scope": {
                "active_runs": "process",
                "counters": "process_lifetime",
                "reset_on_restart": True,
            },
            "config": {
                "defaults": values,
                "effective": values,
                "effective_version": "a" * 64,
                "loaded_at": "2026-08-27T00:00:00Z",
                "policy_status": "not_configured",
                "policy_revision": None,
                "policy_updated_at": None,
            },
            "turns": {
                "started_total": started,
                "completed_total": 0,
                "failed_total": 0,
                "cancelled_total": 0,
            },
            "admission": {
                "active_runs": 0,
                "max_concurrent_runs": 1,
                "granted_total": 0,
                "capacity_denials_total": 0,
                "memory_pressure_denials_total": 0,
                "last_denial_type": None,
                "last_denial_at": None,
                "can_start_new_agent": None,
            },
            "claude_processes": {
                "available": False,
                "count": None,
                "total_rss_bytes": None,
            },
            "memory": {
                "host_available_bytes": None,
                "cgroup_current_bytes": None,
                "cgroup_max_bytes": None,
                "cgroup_raw_headroom_bytes": None,
                "inactive_file_bytes": None,
                "slab_reclaimable_bytes": None,
                "cgroup_reclaimable_bytes": None,
                "cgroup_effective_headroom_bytes": None,
                "required_headroom_bytes": 671088640,
                "events": {"low": None, "high": None, "max": None, "oom": None, "oom_kill": None},
            },
            "sample": {
                "status": "starting",
                "sampled_at": None,
                "stale": True,
                "error_code": None,
            },
            "pipeline": {
                "queue_dropped_total": 0,
                "write_errors_total": 0,
                "last_write_error_at": None,
            },
        }
    )


class _Cursor:
    def __init__(self, row=None):
        self._row = row

    def fetchone(self):
        return self._row


class _Connection:
    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, query, parameters=()):
        self.calls.append((query, parameters))
        if "drizzle.schema_capabilities" in query:
            assert parameters == (CLAUDE_AGENT_RESOURCE_OBSERVER_CAPABILITY,)
            return _Cursor(
                (
                    CLAUDE_AGENT_RESOURCE_OBSERVER_VERSION,
                    CLAUDE_AGENT_RESOURCE_OBSERVER_CONTRACT_SHA256,
                )
            )
        return _Cursor()

    def close(self):
        self.closed = True


def test_capacity_one_queue_replaces_oldest_without_backpressure() -> None:
    metrics = ResourcePipelineMetrics()
    sink = ClaudeAgentResourcePostgresSink(db_factory=lambda: None, metrics=metrics)

    sink.submit(_snapshot(started=1))
    sink.submit(_snapshot(started=2))

    queued = sink._queue.get_nowait()
    assert queued.snapshot.turns.started_total == 2
    assert metrics.snapshot().queue_dropped_total == 1


def test_producer_dto_rejects_consumer_contract_drift() -> None:
    payload = _snapshot().model_dump(mode="json")
    with pytest.raises(ValidationError):
        ClaudeAgentResourceDiagnosticsDTO.model_validate(
            {**payload, "scope": {**payload["scope"], "reset_on_restart": False}}
        )
    with pytest.raises(ValidationError):
        ClaudeAgentResourceDiagnosticsDTO.model_validate(
            {**payload, "turns": {**payload["turns"], "started_total": -1}}
        )
    with pytest.raises(ValidationError):
        ClaudeAgentResourceDiagnosticsDTO.model_validate(
            {**payload, "config": {**payload["config"], "loaded_at": "not-a-timestamp"}}
        )


def test_upsert_and_ttl_use_exact_capability_and_closed_json() -> None:
    connection = _Connection()
    metrics = ResourcePipelineMetrics()
    sink = ClaudeAgentResourcePostgresSink(
        db_factory=lambda: connection,
        metrics=metrics,
    )
    UUID(sink.instance_id)
    snapshot = _snapshot(started=4)
    sink.submit(snapshot)
    envelope = sink._queue.get_nowait()

    sink._write_sync(envelope)

    assert connection.closed is True
    statements = [query for query, _ in connection.calls]
    assert any("set_config('statement_timeout'" in query for query in statements)
    assert any("ON CONFLICT (instance_id) DO UPDATE" in query for query in statements)
    assert any("heartbeat_at = CURRENT_TIMESTAMP" in query for query in statements)
    assert any("CASE WHEN %s IS NULL THEN NULL ELSE CURRENT_TIMESTAMP END" in query for query in statements)
    assert any("make_interval(days => %s)" in query for query in statements)
    upsert_parameters = next(
        parameters
        for query, parameters in connection.calls
        if query.startswith("INSERT INTO claude_agent_resource_snapshots")
    )
    stored = json.loads(upsert_parameters[3])
    assert stored == snapshot.model_dump(mode="json")
    serialized = json.dumps(stored).lower()
    for forbidden in (
        "instance_id",
        "hostname",
        "pid",
        "session_id",
        "thread_id",
        "authorization",
        "token",
        "prompt",
    ):
        assert forbidden not in serialized


def test_slow_database_timeout_is_counted_and_does_not_escape() -> None:
    async def exercise() -> None:
        metrics = ResourcePipelineMetrics()
        sink = ClaudeAgentResourcePostgresSink(
            db_factory=lambda: None,
            metrics=metrics,
            write_timeout_seconds=0.05,
        )

        def slow_write(_envelope):
            time.sleep(0.2)

        sink._write_sync = slow_write
        sink.submit(_snapshot())
        envelope = sink._queue.get_nowait()
        started = time.monotonic()
        await sink._write_with_timeout(envelope)
        elapsed = time.monotonic() - started
        health = metrics.snapshot()
        assert elapsed < 0.12
        assert health.write_errors_total == 1
        assert health.last_write_error_at is not None

    asyncio.run(exercise())


def test_timed_out_driver_calls_never_overlap_or_overtake() -> None:
    async def exercise() -> None:
        metrics = ResourcePipelineMetrics()
        sink = ClaudeAgentResourcePostgresSink(
            db_factory=lambda: None,
            metrics=metrics,
            write_timeout_seconds=0.02,
        )
        active = 0
        maximum_active = 0
        completed: list[int] = []

        def slow_write(envelope):
            nonlocal active, maximum_active
            active += 1
            maximum_active = max(maximum_active, active)
            try:
                time.sleep(0.08)
                completed.append(envelope.snapshot.turns.started_total)
            finally:
                active -= 1

        sink._write_sync = slow_write
        sink.start()
        sink.submit(_snapshot(started=1))
        await asyncio.sleep(0.03)
        sink.submit(_snapshot(started=2))
        await asyncio.sleep(0.2)
        await sink.stop()

        assert maximum_active == 1
        assert completed == [1, 2]
        assert metrics.snapshot().write_errors_total == 2

    asyncio.run(exercise())


def test_database_error_isolated_by_worker_boundary() -> None:
    async def exercise() -> None:
        metrics = ResourcePipelineMetrics()
        sink = ClaudeAgentResourcePostgresSink(
            db_factory=lambda: (_ for _ in ()).throw(OSError("secret DSN")),
            metrics=metrics,
        )
        sink.submit(_snapshot())
        envelope = sink._queue.get_nowait()
        await sink._write_with_timeout(envelope)
        assert metrics.snapshot().write_errors_total == 1

    asyncio.run(exercise())
