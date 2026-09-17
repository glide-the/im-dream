# [Input] Consume strict resource snapshots and an injected typed Admin observer writer.
# [Output] Provide a capacity-one latest publisher and isolated single-worker Admin API sink.
# [Pos] Off-path resource synchronization boundary; historical module/class names remain internal compatibility identifiers.
# [Sync] 2026-09-14: replace SQL with typed Admin observer writes and original request IDs;
#                    retain latest queue, timeout isolation and single-worker ordering.

"""Publish the latest content-free resource snapshot through the Admin domain API."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from uuid import UUID, uuid4

from claude_agent.resource_diagnostics import (
    ClaudeAgentResourceDiagnosticsDTO,
    ResourcePipelineSnapshot,
)

logger = logging.getLogger(__name__)

_PUBLISH_INTERVAL_SECONDS = 5.0
_WRITE_TIMEOUT_SECONDS = 1.0


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
    request_id: str = field(default_factory=lambda: str(uuid4()))


class ClaudeAgentResourcePostgresSink:
    """Consume only the latest snapshot and write it through one isolated worker."""

    def __init__(
        self,
        *,
        writer: Callable[[ResourceSnapshotEnvelope, str, datetime], None],
        metrics: ResourcePipelineMetrics,
        instance_id: UUID | None = None,
        process_started_at: datetime | None = None,
        write_timeout_seconds: float = _WRITE_TIMEOUT_SECONDS,
    ) -> None:
        self._writer = writer
        self._metrics = metrics
        self._instance_id = str(instance_id or uuid4())
        self._process_started_at = process_started_at or _utc_now()
        self._write_timeout_seconds = max(0.05, float(write_timeout_seconds))
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
        self._writer(envelope, self._instance_id, self._process_started_at)


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
