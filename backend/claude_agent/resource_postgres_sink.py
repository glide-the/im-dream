# [Input] Consume strict resource DTO snapshots, the exact Admin capability, and an injected database.get_db lease factory.
# [Output] Provide a capacity-one latest publisher and isolated single-worker PostgreSQL upsert/TTL sink.
# [Pos] Off-path PostgreSQL synchronization boundary for Claude Agent resource observation; owns no schema.
# [Sync] 2026-08-27: use DB-clock heartbeat/sample columns and serialize timed-out
#                    driver work so an older write cannot overtake a newer snapshot.

"""Publish the latest content-free Claude Agent resource snapshot to PostgreSQL."""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import UUID, uuid4

from claude_agent.resource_diagnostics import (
    ClaudeAgentResourceDiagnosticsDTO,
    ResourcePipelineSnapshot,
)
from schema.capabilities import claude_agent_resource_observer_capability_available

logger = logging.getLogger(__name__)

_PUBLISH_INTERVAL_SECONDS = 5.0
_WRITE_TIMEOUT_SECONDS = 1.0
_STATEMENT_TIMEOUT_MILLISECONDS = 900
_INSTANCE_TTL_DAYS = 7


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_text() -> str:
    return _utc_now().isoformat().replace("+00:00", "Z")


class ResourcePipelineMetrics:
    """Thread-safe, closed health counters shared with the diagnostics projector."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._queue_dropped_total = 0
        self._write_errors_total = 0
        self._last_write_error_at: str | None = None

    def record_queue_drop(self) -> None:
        with self._lock:
            self._queue_dropped_total += 1

    def record_write_error(self) -> None:
        with self._lock:
            self._write_errors_total += 1
            self._last_write_error_at = _utc_now_text()

    def snapshot(self) -> ResourcePipelineSnapshot:
        with self._lock:
            return ResourcePipelineSnapshot(
                queue_dropped_total=self._queue_dropped_total,
                write_errors_total=self._write_errors_total,
                last_write_error_at=self._last_write_error_at,
            )


@dataclass(frozen=True, slots=True)
class ResourceSnapshotEnvelope:
    sampled_at: datetime | None
    snapshot: ClaudeAgentResourceDiagnosticsDTO


class ClaudeAgentResourcePostgresSink:
    """Consume only the latest snapshot and write it through one isolated worker."""

    def __init__(
        self,
        *,
        db_factory: Callable[[], Any],
        metrics: ResourcePipelineMetrics,
        instance_id: UUID | None = None,
        process_started_at: datetime | None = None,
        write_timeout_seconds: float = _WRITE_TIMEOUT_SECONDS,
        statement_timeout_milliseconds: int = _STATEMENT_TIMEOUT_MILLISECONDS,
        ttl_days: int = _INSTANCE_TTL_DAYS,
    ) -> None:
        self._db_factory = db_factory
        self._metrics = metrics
        self._instance_id = str(instance_id or uuid4())
        self._process_started_at = process_started_at or _utc_now()
        self._write_timeout_seconds = max(0.05, float(write_timeout_seconds))
        self._statement_timeout_milliseconds = max(1, int(statement_timeout_milliseconds))
        self._ttl_days = max(1, int(ttl_days))
        self._queue: asyncio.Queue[ResourceSnapshotEnvelope] = asyncio.Queue(maxsize=1)
        self._task: asyncio.Task[None] | None = None
        self._inflight_operation: asyncio.Task[None] | None = None

    @property
    def instance_id(self) -> str:
        return self._instance_id

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(
                self._run(),
                name="claude-agent-resource-postgres-sink",
            )

    async def stop(self) -> None:
        task = self._task
        self._task = None
        if task is None or task.done():
            return
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    def submit(self, snapshot: ClaudeAgentResourceDiagnosticsDTO) -> None:
        """Replace a queued stale value synchronously; never await or backpressure."""

        envelope = ResourceSnapshotEnvelope(
            sampled_at=snapshot.sample.sampled_at,
            snapshot=snapshot,
        )
        try:
            self._queue.put_nowait(envelope)
            return
        except asyncio.QueueFull:
            pass
        try:
            self._queue.get_nowait()
            self._queue.task_done()
        except asyncio.QueueEmpty:
            pass
        self._metrics.record_queue_drop()
        self._queue.put_nowait(envelope)

    async def _run(self) -> None:
        while True:
            await self._finish_inflight_operation()
            envelope = await self._queue.get()
            try:
                await self._write_with_timeout(envelope)
            finally:
                self._queue.task_done()

    async def _finish_inflight_operation(self) -> None:
        """Keep at most one driver call active without blocking Agent execution."""

        operation = self._inflight_operation
        if operation is None:
            return
        try:
            await asyncio.shield(operation)
        except asyncio.CancelledError:
            operation.add_done_callback(self._discard_background_result)
            raise
        except Exception:
            # The timeout was already counted and safely logged when detached.
            pass
        finally:
            if operation.done():
                self._inflight_operation = None

    async def _write_with_timeout(self, envelope: ResourceSnapshotEnvelope) -> None:
        operation = asyncio.create_task(asyncio.to_thread(self._write_sync, envelope))
        try:
            await asyncio.wait_for(
                asyncio.shield(operation),
                timeout=self._write_timeout_seconds,
            )
        except asyncio.TimeoutError:
            self._metrics.record_write_error()
            logger.warning("Claude Agent resource snapshot write failed: code=write_timeout")
            self._inflight_operation = operation
        except asyncio.CancelledError:
            operation.add_done_callback(self._discard_background_result)
            raise
        except Exception:
            self._metrics.record_write_error()
            logger.warning("Claude Agent resource snapshot write failed: code=write_error")

    @staticmethod
    def _discard_background_result(operation: asyncio.Task[None]) -> None:
        """Consume a detached driver result without logging payloads or credentials."""

        if operation.cancelled():
            return
        try:
            operation.exception()
        except asyncio.CancelledError:
            pass

    def _write_sync(self, envelope: ResourceSnapshotEnvelope) -> None:
        connection: Any | None = None
        try:
            connection = self._db_factory()
            with connection:
                connection.execute(
                    "SELECT set_config('statement_timeout', %s, true)",
                    (f"{self._statement_timeout_milliseconds}ms",),
                )
                if not claude_agent_resource_observer_capability_available(connection):
                    raise RuntimeError("resource_observer_capability_unavailable")
                payload = json.dumps(
                    envelope.snapshot.model_dump(mode="json"),
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                connection.execute(
                    "INSERT INTO claude_agent_resource_snapshots "
                    "(instance_id, process_started_at, heartbeat_at, sampled_at, snapshot) "
                    "VALUES (%s, LEAST(%s, CURRENT_TIMESTAMP), CURRENT_TIMESTAMP, "
                    "CASE WHEN %s IS NULL THEN NULL ELSE CURRENT_TIMESTAMP END, %s::jsonb) "
                    "ON CONFLICT (instance_id) DO UPDATE SET "
                    "heartbeat_at = CURRENT_TIMESTAMP, "
                    "sampled_at = EXCLUDED.sampled_at, "
                    "snapshot = EXCLUDED.snapshot, updated_at = CURRENT_TIMESTAMP",
                    (
                        self._instance_id,
                        self._process_started_at,
                        envelope.sampled_at,
                        payload,
                    ),
                )
                connection.execute(
                    "DELETE FROM claude_agent_resource_snapshots "
                    "WHERE instance_id <> %s "
                    "AND heartbeat_at < CURRENT_TIMESTAMP - make_interval(days => %s)",
                    (self._instance_id, self._ttl_days),
                )
        finally:
            if connection is not None:
                connection.close()


class ClaudeAgentResourcePublisher:
    """Take one immutable closed snapshot every interval and hand it off synchronously."""

    def __init__(
        self,
        *,
        snapshot_provider: Callable[[], ClaudeAgentResourceDiagnosticsDTO],
        sink: ClaudeAgentResourcePostgresSink,
        interval_seconds: float = _PUBLISH_INTERVAL_SECONDS,
    ) -> None:
        self._snapshot_provider = snapshot_provider
        self._sink = sink
        self._interval_seconds = max(0.01, float(interval_seconds))
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(
                self._run(),
                name="claude-agent-resource-publisher",
            )

    async def stop(self) -> None:
        task = self._task
        self._task = None
        if task is None or task.done():
            return
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def _run(self) -> None:
        while True:
            try:
                self.publish_once()
            except Exception:
                logger.warning("Claude Agent resource snapshot projection failed")
            await asyncio.sleep(self._interval_seconds)

    def publish_once(self) -> None:
        self._sink.submit(self._snapshot_provider())


__all__ = [
    "ClaudeAgentResourcePostgresSink",
    "ClaudeAgentResourcePublisher",
    "ResourcePipelineMetrics",
    "ResourceSnapshotEnvelope",
]
