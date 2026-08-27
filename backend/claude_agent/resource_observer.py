# [Input] Consume the public Claude Agent admission controller contract, Session lifecycle hooks,
#         and normalized per-turn EventBus exposed after context assembly.
# [Output] Provide an admission decorator and content-free, process-lifetime resource counters.
# [Pos] Off-path resource Observer in backend/claude_agent; never controls Agent execution.
# [Sync] 2026-08-27: expose closed reader-error counts while preserving no-I/O hooks and identity-free state.

"""Content-free resource observations for canonical Claude Agent turns."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from claude_agent.admission import (
    AgentAdmissionConfig,
    AgentAdmissionLease,
    ClaudeAgentAdmissionController,
    ClaudeAgentAdmissionError,
)
from services.story_workspace.dream_lifecycle_observer import (
    NormalizedAgentTurnClassifier,
    NormalizedTurnOutcome,
)

logger = logging.getLogger(__name__)


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class ClaudeAgentResourceCounters:
    """One immutable process-lifetime counter snapshot."""

    admission_granted_total: int
    capacity_denials_total: int
    memory_pressure_denials_total: int
    turn_started_total: int
    turn_completed_total: int
    turn_failed_total: int
    turn_cancelled_total: int
    last_denial_type: str | None
    last_denial_at: str | None
    reader_errors_total: int


class ClaudeAgentResourceObserver:
    """Observe normalized lifecycle events outside the Agent execution path.

    Lifecycle hooks perform only constant-time validation, counter mutation, and
    task creation. EventBus subscription and reads happen in independently owned
    tasks. No session, thread, actor, prompt, or event payload is retained.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._admission_granted_total = 0
        self._capacity_denials_total = 0
        self._memory_pressure_denials_total = 0
        self._turn_started_total = 0
        self._turn_completed_total = 0
        self._turn_failed_total = 0
        self._turn_cancelled_total = 0
        self._last_denial_type: str | None = None
        self._last_denial_at: str | None = None
        self._reader_errors = 0
        self._reader_sequence = 0
        self._reader_tasks: set[asyncio.Task[None]] = set()
        self._closed = False

    def record_admission_granted(self) -> None:
        with self._lock:
            self._admission_granted_total += 1

    def record_admission_denied(self, code: str) -> None:
        denial_type: str | None = None
        if code == "CLAUDE_AGENT_CAPACITY_EXHAUSTED":
            denial_type = "capacity"
        elif code == "CLAUDE_AGENT_MEMORY_PRESSURE":
            denial_type = "memory_pressure"
        if denial_type is None:
            return
        with self._lock:
            if denial_type == "capacity":
                self._capacity_denials_total += 1
            else:
                self._memory_pressure_denials_total += 1
            self._last_denial_type = denial_type
            self._last_denial_at = _utc_now_text()

    def on_after_context_assembly(
        self,
        _session_id: str,
        metadata: dict[str, Any],
    ) -> None:
        """Attach one replay-safe EventBus reader without awaiting any I/O."""

        if self._closed:
            return
        bus = metadata.get("event_bus")
        if bus is None:
            with self._lock:
                self._reader_errors += 1
            return
        with self._lock:
            self._turn_started_total += 1
            self._reader_sequence += 1
            sequence = self._reader_sequence
        task = asyncio.create_task(
            self._read_turn(bus),
            name=f"claude-agent-resource-observer-{sequence}",
        )
        self._reader_tasks.add(task)
        task.add_done_callback(self._reader_done)

    async def _read_turn(self, bus: Any) -> None:
        token: object | None = None
        classifier = NormalizedAgentTurnClassifier()
        try:
            token = await bus.subscribe()
            async for event in bus.read(token):
                classifier.observe(event)
            outcome = classifier.result().outcome
            with self._lock:
                if outcome is NormalizedTurnOutcome.COMPLETED:
                    self._turn_completed_total += 1
                elif outcome is NormalizedTurnOutcome.FAILED:
                    self._turn_failed_total += 1
                elif outcome is NormalizedTurnOutcome.CANCELLED:
                    self._turn_cancelled_total += 1
                else:
                    self._reader_errors += 1
        except asyncio.CancelledError:
            raise
        except Exception:
            with self._lock:
                self._reader_errors += 1
            logger.exception("Claude Agent resource EventBus reader failed")
        finally:
            if token is not None:
                try:
                    await bus.unsubscribe(token)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    with self._lock:
                        self._reader_errors += 1
                    logger.exception("Claude Agent resource EventBus unsubscribe failed")

    def _reader_done(self, task: asyncio.Task[None]) -> None:
        self._reader_tasks.discard(task)
        if task.cancelled():
            return
        try:
            task.exception()
        except asyncio.CancelledError:
            return

    async def aclose(self) -> None:
        self._closed = True
        tasks = list(self._reader_tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._reader_tasks.clear()

    def snapshot(self) -> ClaudeAgentResourceCounters:
        with self._lock:
            return ClaudeAgentResourceCounters(
                admission_granted_total=self._admission_granted_total,
                capacity_denials_total=self._capacity_denials_total,
                memory_pressure_denials_total=self._memory_pressure_denials_total,
                turn_started_total=self._turn_started_total,
                turn_completed_total=self._turn_completed_total,
                turn_failed_total=self._turn_failed_total,
                turn_cancelled_total=self._turn_cancelled_total,
                last_denial_type=self._last_denial_type,
                last_denial_at=self._last_denial_at,
                reader_errors_total=self._reader_errors,
            )


class ObservedClaudeAgentAdmissionController:
    """Transparent admission decorator that records only public outcomes."""

    def __init__(
        self,
        delegate: ClaudeAgentAdmissionController,
        observer: ClaudeAgentResourceObserver,
    ) -> None:
        self._delegate = delegate
        self._observer = observer

    @property
    def config(self) -> AgentAdmissionConfig:
        return self._delegate.config

    def try_acquire(self, session_id: str) -> AgentAdmissionLease:
        try:
            lease = self._delegate.try_acquire(session_id)
        except ClaudeAgentAdmissionError as exc:
            try:
                self._observer.record_admission_denied(exc.code)
            except Exception:
                logger.exception("Claude Agent admission denial observation failed")
            raise
        try:
            self._observer.record_admission_granted()
        except Exception:
            logger.exception("Claude Agent admission grant observation failed")
        return lease

    def stats(self) -> dict[str, Any]:
        return self._delegate.stats()


__all__ = [
    "ClaudeAgentResourceCounters",
    "ClaudeAgentResourceObserver",
    "ObservedClaudeAgentAdmissionController",
]
