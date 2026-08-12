"""Off-path Dream business observations for canonical Claude Agent turns.

This module deliberately does not encode SSE, persist conversation events, or
control ``ClaudeAgentService``.  A coordinator owns one bounded subscriber per
trusted Dream turn and hands only content-free lifecycle/activity hints to an
injectable business sink.  The Chat EventBus remains the sole conversation
stream and existing domain services remain the sole workflow truth owners.
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from enum import Enum
import hashlib
import inspect
import logging
from collections import OrderedDict
from typing import Any, Callable, Literal, Protocol

from agent_stream_events import NormalizedAgentEvent


logger = logging.getLogger(__name__)

_QUEUE_STOP = object()
_ACTIVITY_START_EVENTS = frozenset({"tool-input-start", "tool-input-available"})
_ACTIVITY_END_EVENTS = frozenset(
    {"tool-output-available", "tool-output-error", "tool-error"}
)
_SUBAGENT_TOOL_NAMES = frozenset({"agent", "task"})
_DREAM_CONTENT_TOOL_NAMES = frozenset(
    {
        "mcp__story_workspace__write_dream_run",
        "write_dream_run",
    }
)


class NormalizedTurnOutcome(str, Enum):
    """Canonical terminal classification for one normalized Agent turn."""

    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INCOMPLETE = "incomplete"


@dataclass(frozen=True, slots=True)
class NormalizedTurnResult:
    outcome: NormalizedTurnOutcome
    saw_message_final: bool
    saw_finish: bool
    finish_reason: str | None

    @property
    def completed(self) -> bool:
        return self.outcome is NormalizedTurnOutcome.COMPLETED


class NormalizedAgentTurnClassifier:
    """Pure first-terminal classifier shared by internal Dream dispatchers.

    ``message-final`` is deliberately not terminal: the service persists the
    assistant after that event and emits ``finish`` only when the turn is
    settled.  The first ``finish`` wins and every later event is ignored.
    """

    def __init__(self) -> None:
        self.saw_message_final = False
        self.saw_finish = False
        self.finish_reason: str | None = None
        self.outcome = NormalizedTurnOutcome.INCOMPLETE

    def observe(self, event: NormalizedAgentEvent) -> NormalizedTurnOutcome | None:
        if self.saw_finish or event.is_keepalive:
            return None
        if event.type == "message-final":
            self.saw_message_final = True
            return None
        if event.type != "finish":
            return None
        self.saw_finish = True
        self.finish_reason = str(event.data.get("finishReason") or "") or None
        if event.data.get("cancelled") is True:
            self.outcome = NormalizedTurnOutcome.CANCELLED
        elif self.finish_reason == "error":
            self.outcome = NormalizedTurnOutcome.FAILED
        elif self.saw_message_final:
            self.outcome = NormalizedTurnOutcome.COMPLETED
        else:
            self.outcome = NormalizedTurnOutcome.CANCELLED
        return self.outcome

    def result(self) -> NormalizedTurnResult:
        return NormalizedTurnResult(
            outcome=self.outcome,
            saw_message_final=self.saw_message_final,
            saw_finish=self.saw_finish,
            finish_reason=self.finish_reason,
        )


async def drain_normalized_agent_turn(
    factory: Any,
    request: Any,
    *,
    on_event: Callable[[NormalizedAgentEvent], Any] | None = None,
) -> NormalizedTurnResult:
    """Drain the canonical normalized stream through its sentinel.

    Internal launch/confirmation/episode owners use the result only to settle
    their existing claims.  They do not expose this drain as a browser stream.
    Legacy encoded-string fallbacks are intentionally unsupported.
    """

    classifier = NormalizedAgentTurnClassifier()
    async for event in factory.run_events(request):
        if not isinstance(event, NormalizedAgentEvent):
            raise TypeError("ClaudeAgentThreadFactory.run_events must yield normalized events")
        if on_event is not None:
            observed = on_event(event)
            if inspect.isawaitable(observed):
                await observed
        classifier.observe(event)
    return classifier.result()


@dataclass(frozen=True, slots=True)
class DreamTurnIdentity:
    run_id: str
    thread_id: str
    turn_id: str
    actor_id: str
    generation: int


@dataclass(frozen=True, slots=True)
class DreamLifecycleObservation:
    """A bounded, content-free hint; never a workflow transition proof."""

    event_id: str
    run_id: str
    thread_id: str
    turn_id: str
    actor_id: str
    sequence: int
    kind: Literal[
        "activity_started_hint",
        "activity_settled_hint",
        "waiting_confirmation_hint",
        "turn_settled_hint",
        "reconcile_requested",
    ]
    terminal_outcome: Literal["completed", "failed", "cancelled"] | None = None
    operation_scope: Literal[
        "tool",
        "subagent",
        "content_generation",
        "workflow_operation",
    ] | None = None
    operation_state: Literal[
        "started",
        "waiting_confirmation",
        "succeeded",
        "failed",
    ] | None = None
    operation_id: str | None = None


class DreamTurnLease:
    """Revocable generation lease checked immediately before sink work."""

    __slots__ = ("identity", "_closed")

    def __init__(self, identity: DreamTurnIdentity) -> None:
        self.identity = identity
        self._closed = False

    @property
    def active(self) -> bool:
        return not self._closed

    def revoke(self) -> None:
        self._closed = True


class DreamBusinessSink(Protocol):
    """Injection port implemented only by existing business owners."""

    async def project(
        self,
        observation: DreamLifecycleObservation,
        lease: DreamTurnLease,
    ) -> None: ...

    async def reconcile(
        self,
        run_id: str,
        actor_id: str,
        lease: DreamTurnLease,
    ) -> None: ...


class NullDreamBusinessSink:
    """Default sink: runtime hints are optional and never become workflow truth."""

    async def project(
        self,
        observation: DreamLifecycleObservation,
        lease: DreamTurnLease,
    ) -> None:
        del observation, lease

    async def reconcile(
        self,
        run_id: str,
        actor_id: str,
        lease: DreamTurnLease,
    ) -> None:
        del run_id, actor_id, lease


@dataclass(frozen=True, slots=True)
class DreamWorkflowActivityProjection:
    """Latest derived hint for a run/thread, not a durable lifecycle record."""

    run_id: str
    thread_id: str
    turn_id: str
    actor_id: str
    generation: int
    event_id: str
    sequence: int
    activity: str
    terminal_outcome: str | None
    needs_reconcile: bool = False
    operation_scope: str | None = None
    operation_state: str | None = None
    operation_id: str | None = None


class DreamWorkflowActivityProjectionSink:
    """Bounded production projection of latest content-free Dream activity.

    This stores one latest value per trusted run/thread/actor scope rather than
    an event log. The existing authorized Dream-files REST projection may expose
    its content-free latest hint for display. It survives no restart and cannot
    mutate Claude or a durable Workflow Run; existing business owners remain
    responsible for transitions.
    """

    def __init__(self, *, max_entries: int = 256) -> None:
        self._max_entries = max(1, int(max_entries))
        self._latest: OrderedDict[
            tuple[str, str, str], DreamWorkflowActivityProjection
        ] = OrderedDict()

    async def project(
        self,
        observation: DreamLifecycleObservation,
        lease: DreamTurnLease,
    ) -> None:
        identity = lease.identity
        if not (
            lease.active
            and identity.run_id == observation.run_id
            and identity.thread_id == observation.thread_id
            and identity.turn_id == observation.turn_id
            and identity.actor_id == observation.actor_id
        ):
            return
        key = (
            observation.run_id,
            observation.thread_id,
            observation.actor_id,
        )
        current = self._latest.get(key)
        if current is not None:
            if current.generation > identity.generation:
                return
            if current.generation == identity.generation:
                if current.turn_id != observation.turn_id:
                    return
                if current.sequence >= observation.sequence:
                    return
        self._latest[key] = DreamWorkflowActivityProjection(
            run_id=observation.run_id,
            thread_id=observation.thread_id,
            turn_id=observation.turn_id,
            actor_id=observation.actor_id,
            generation=identity.generation,
            event_id=observation.event_id,
            sequence=observation.sequence,
            activity=observation.kind,
            terminal_outcome=observation.terminal_outcome,
            needs_reconcile=False,
            operation_scope=observation.operation_scope,
            operation_state=observation.operation_state,
            operation_id=observation.operation_id,
        )
        self._latest.move_to_end(key)
        self._trim()

    async def reconcile(
        self,
        run_id: str,
        actor_id: str,
        lease: DreamTurnLease,
    ) -> None:
        identity = lease.identity
        if not (
            lease.active
            and identity.run_id == run_id
            and identity.actor_id == actor_id
        ):
            return
        key = (run_id, identity.thread_id, actor_id)
        current = self._latest.get(key)
        if current is not None:
            if current.generation > identity.generation:
                return
            if (
                current.generation == identity.generation
                and current.turn_id != identity.turn_id
            ):
                return
        same_turn = (
            current is not None
            and current.generation == identity.generation
            and current.turn_id == identity.turn_id
        )
        self._latest[key] = DreamWorkflowActivityProjection(
            run_id=run_id,
            thread_id=identity.thread_id,
            turn_id=identity.turn_id,
            actor_id=actor_id,
            generation=identity.generation,
            event_id=current.event_id if same_turn else "",
            sequence=current.sequence if same_turn else -1,
            activity="reconcile_requested",
            terminal_outcome=None,
            needs_reconcile=True,
            operation_scope=None,
            operation_state=None,
            operation_id=None,
        )
        self._latest.move_to_end(key)
        self._trim()

    def snapshot(self) -> list[DreamWorkflowActivityProjection]:
        return list(self._latest.values())

    def _trim(self) -> None:
        while len(self._latest) > self._max_entries:
            self._latest.popitem(last=False)


@dataclass(slots=True)
class DreamObserverDiagnostics:
    accepted: int = 0
    duplicates: int = 0
    out_of_order: int = 0
    sequence_gaps: int = 0
    late_events: int = 0
    queue_overflow: int = 0
    sink_errors: int = 0
    missing_terminal: int = 0
    detached_tasks: int = 0
    reader_errors: int = 0
    reader_restarts: int = 0

    def add(self, other: "DreamObserverDiagnostics") -> None:
        for field_name in self.__dataclass_fields__:
            setattr(self, field_name, getattr(self, field_name) + getattr(other, field_name))

    def snapshot(self) -> dict[str, int]:
        return {
            field_name: int(getattr(self, field_name))
            for field_name in self.__dataclass_fields__
        }


def _event_id(identity: DreamTurnIdentity, sequence: int) -> str:
    raw = f"{identity.thread_id}\n{identity.turn_id}\n{sequence}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _reader_error_event_id(identity: DreamTurnIdentity, attempt: int) -> str:
    raw = (
        f"{identity.thread_id}\n{identity.turn_id}\nreader-error\n{attempt}"
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _operation_id(identity: DreamTurnIdentity, tool_call_id: str) -> str:
    """Return a stable correlation hash without projecting the raw tool ID."""

    raw = f"{identity.thread_id}\n{identity.turn_id}\n{tool_call_id}".encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


def _operation_scope(tool_name: str) -> str:
    normalized = tool_name.strip().lower()
    if normalized in _SUBAGENT_TOOL_NAMES:
        return "subagent"
    if normalized in _DREAM_CONTENT_TOOL_NAMES:
        return "content_generation"
    if normalized.startswith("mcp__story_workspace__"):
        return "workflow_operation"
    return "tool"


class DreamLifecycleObserver:
    """Validate order/dedup and derive non-authoritative business hints."""

    def __init__(
        self,
        identity: DreamTurnIdentity,
        *,
        max_dedup_entries: int = 4096,
    ) -> None:
        self.identity = identity
        self._max_dedup_entries = max(1, int(max_dedup_entries))
        self._seen_event_ids: dict[str, None] = {}
        self._tool_operations: OrderedDict[str, tuple[str, str]] = OrderedDict()
        self._next_sequence = 0
        self._saw_message_final = False
        self._terminal_outcome: str | None = None
        self.diagnostics = DreamObserverDiagnostics()

    @property
    def terminal_outcome(self) -> str | None:
        return self._terminal_outcome

    @property
    def next_sequence(self) -> int:
        return self._next_sequence

    def observe(
        self,
        event: NormalizedAgentEvent,
        *,
        sequence: int,
    ) -> DreamLifecycleObservation | None:
        if event.is_keepalive:
            return None
        event_id = _event_id(self.identity, sequence)
        if self._terminal_outcome is not None:
            self.diagnostics.late_events += 1
            return None
        if event_id in self._seen_event_ids:
            self.diagnostics.duplicates += 1
            return None
        if sequence < self._next_sequence:
            self.diagnostics.out_of_order += 1
            return None
        if sequence > self._next_sequence:
            self.diagnostics.sequence_gaps += 1
            self._remember(event_id)
            self._next_sequence = sequence + 1
            self.diagnostics.accepted += 1
            return self._observation(
                event_id=event_id,
                sequence=sequence,
                kind="reconcile_requested",
            )

        self._remember(event_id)
        self._next_sequence += 1
        self.diagnostics.accepted += 1

        if event.type == "message-final":
            self._saw_message_final = True
            return None
        if event.type == "finish":
            if event.data.get("cancelled") is True:
                outcome = "cancelled"
            elif event.data.get("finishReason") == "error":
                outcome = "failed"
            elif self._saw_message_final:
                outcome = "completed"
            else:
                outcome = "cancelled"
            self._terminal_outcome = outcome
            return self._observation(
                event_id=event_id,
                sequence=sequence,
                kind="turn_settled_hint",
                terminal_outcome=outcome,
            )
        if event.type == "tool-approval-request":
            operation_scope, operation_id = self._remember_tool_operation(event)
            return self._observation(
                event_id=event_id,
                sequence=sequence,
                kind="waiting_confirmation_hint",
                operation_scope=operation_scope,
                operation_state="waiting_confirmation",
                operation_id=operation_id,
            )
        if event.type in _ACTIVITY_START_EVENTS:
            operation_scope, operation_id = self._remember_tool_operation(event)
            return self._observation(
                event_id=event_id,
                sequence=sequence,
                kind="activity_started_hint",
                operation_scope=operation_scope,
                operation_state="started",
                operation_id=operation_id,
            )
        if event.type in _ACTIVITY_END_EVENTS:
            operation_scope, operation_id = self._recall_tool_operation(event)
            return self._observation(
                event_id=event_id,
                sequence=sequence,
                kind="activity_settled_hint",
                operation_scope=operation_scope,
                operation_state=(
                    "failed"
                    if event.type in {"tool-output-error", "tool-error"}
                    or event.data.get("isError") is True
                    else "succeeded"
                ),
                operation_id=operation_id,
            )
        return None

    def eof_observation(self) -> DreamLifecycleObservation | None:
        if self._terminal_outcome is not None:
            return None
        self.diagnostics.missing_terminal += 1
        sequence = self._next_sequence
        event_id = _event_id(self.identity, sequence)
        self._remember(event_id)
        self._next_sequence += 1
        return self._observation(
            event_id=event_id,
            sequence=sequence,
            kind="reconcile_requested",
        )

    def _remember(self, event_id: str) -> None:
        self._seen_event_ids[event_id] = None
        while len(self._seen_event_ids) > self._max_dedup_entries:
            self._seen_event_ids.pop(next(iter(self._seen_event_ids)))

    def _remember_tool_operation(
        self,
        event: NormalizedAgentEvent,
    ) -> tuple[str, str | None]:
        tool_call_id = event.data.get("toolCallId")
        tool_name = event.data.get("toolName")
        scope = _operation_scope(tool_name if isinstance(tool_name, str) else "")
        if not isinstance(tool_call_id, str) or not tool_call_id:
            return scope, None
        correlation_id = _operation_id(self.identity, tool_call_id)
        self._tool_operations[tool_call_id] = (scope, correlation_id)
        self._tool_operations.move_to_end(tool_call_id)
        while len(self._tool_operations) > self._max_dedup_entries:
            self._tool_operations.popitem(last=False)
        return scope, correlation_id

    def _recall_tool_operation(
        self,
        event: NormalizedAgentEvent,
    ) -> tuple[str, str | None]:
        tool_call_id = event.data.get("toolCallId")
        if isinstance(tool_call_id, str) and tool_call_id:
            remembered = self._tool_operations.get(tool_call_id)
            if remembered is not None:
                self._tool_operations.move_to_end(tool_call_id)
                return remembered
            return self._remember_tool_operation(event)
        return "tool", None

    def _observation(
        self,
        *,
        event_id: str,
        sequence: int,
        kind: Any,
        terminal_outcome: Any = None,
        operation_scope: Any = None,
        operation_state: Any = None,
        operation_id: str | None = None,
    ) -> DreamLifecycleObservation:
        return DreamLifecycleObservation(
            event_id=event_id,
            run_id=self.identity.run_id,
            thread_id=self.identity.thread_id,
            turn_id=self.identity.turn_id,
            actor_id=self.identity.actor_id,
            sequence=sequence,
            kind=kind,
            terminal_outcome=terminal_outcome,
            operation_scope=operation_scope,
            operation_state=operation_state,
            operation_id=operation_id,
        )


@dataclass(slots=True)
class DreamTurnHandle:
    identity: DreamTurnIdentity
    bus: Any
    token: object
    observer: DreamLifecycleObserver
    lease: DreamTurnLease
    queue: asyncio.Queue[Any]
    reader_task: asyncio.Task[None] | None = None
    worker_task: asyncio.Task[None] | None = None
    close_started: bool = False
    archived: bool = False
    cleanup_done: asyncio.Event | None = None


class DreamLifecycleCoordinator:
    """Own per-turn Observer resources without entering the Chat critical path."""

    def __init__(
        self,
        sink: DreamBusinessSink | None = None,
        *,
        queue_size: int = 128,
        graceful_sink_timeout_s: float = 0.1,
    ) -> None:
        self._sink = sink or DreamWorkflowActivityProjectionSink()
        self._queue_size = max(1, int(queue_size))
        self._graceful_sink_timeout_s = max(0.0, float(graceful_sink_timeout_s))
        self._handles: dict[tuple[str, str], DreamTurnHandle] = {}
        self._generation = 0
        self._archived = DreamObserverDiagnostics()
        self._detached_tasks: set[asyncio.Task[Any]] = set()

    async def attach_before_session_execution(
        self,
        *,
        context: Any,
        actor_id: str,
        turn_id: str,
        bus: Any,
    ) -> DreamTurnHandle:
        """Subscribe after assembly and before Session Execution publishes."""

        thread_id = str(getattr(context, "thread_id", "") or "")
        run_id = str(getattr(context, "workflow_run_id", "") or "")
        actor_id = str(actor_id or "")
        if not thread_id or not run_id or not turn_id or not actor_id:
            raise ValueError("trusted Dream turn identity is incomplete")
        key = (thread_id, turn_id)
        existing = self._handles.get(key)
        if existing is not None:
            return existing

        self._generation += 1
        identity = DreamTurnIdentity(
            run_id=run_id,
            thread_id=thread_id,
            turn_id=turn_id,
            actor_id=actor_id,
            generation=self._generation,
        )
        token = await bus.subscribe()
        observer = DreamLifecycleObserver(identity)
        handle = DreamTurnHandle(
            identity=identity,
            bus=bus,
            token=token,
            observer=observer,
            lease=DreamTurnLease(identity),
            queue=asyncio.Queue(maxsize=self._queue_size),
            cleanup_done=asyncio.Event(),
        )
        self._handles[key] = handle
        handle.worker_task = asyncio.create_task(
            self._run_sink(handle),
            name=f"dream-lifecycle-sink-{thread_id}-{turn_id}",
        )
        handle.reader_task = asyncio.create_task(
            self._read_bus(handle),
            name=f"dream-lifecycle-reader-{thread_id}-{turn_id}",
        )
        return handle

    async def close_turn(
        self,
        thread_id: str,
        turn_id: str,
        *,
        reason: str,
    ) -> None:
        handle = self._handles.get((thread_id, turn_id))
        if handle is None:
            return
        if handle.bus.is_done and not handle.close_started:
            cleanup_done = handle.cleanup_done
            if cleanup_done is not None:
                try:
                    await asyncio.wait_for(
                        cleanup_done.wait(),
                        timeout=max(self._graceful_sink_timeout_s * 2, 0.05),
                    )
                    return
                except asyncio.TimeoutError:
                    pass
        await self._close_external(handle, reason=reason)

    async def close_session(self, thread_id: str, *, reason: str) -> None:
        handles = [
            handle
            for key, handle in tuple(self._handles.items())
            if key[0] == thread_id
        ]
        if handles:
            await asyncio.gather(
                *(self._close_external(handle, reason=reason) for handle in handles),
                return_exceptions=True,
            )

    async def aclose(self) -> None:
        handles = list(self._handles.values())
        if handles:
            await asyncio.gather(
                *(self._close_external(handle, reason="coordinator_aclose") for handle in handles),
                return_exceptions=True,
            )
        await self._drain_detached_tasks()

    def diagnostics(self) -> dict[str, int]:
        totals = DreamObserverDiagnostics()
        totals.add(self._archived)
        for handle in self._handles.values():
            totals.add(handle.observer.diagnostics)
        return {
            **totals.snapshot(),
            "active_handles": len(self._handles),
            "active_tasks": sum(
                int(task is not None and not task.done())
                for handle in self._handles.values()
                for task in (handle.reader_task, handle.worker_task)
            ),
            "live_detached_tasks": len(self._detached_tasks),
        }

    def projection_snapshot(self) -> list[DreamWorkflowActivityProjection]:
        snapshot = getattr(self._sink, "snapshot", None)
        return list(snapshot()) if callable(snapshot) else []

    async def _read_bus(self, handle: DreamTurnHandle) -> None:
        try:
            # One resubscription is sufficient to recover a transient reader
            # failure. Both EventBus adapters replay from the beginning, so the
            # same Observer deliberately restarts its local sequence at zero;
            # stable derived event IDs suppress already projected events.
            for attempt in range(2):
                sequence = 0
                try:
                    async for event in handle.bus.read(handle.token):
                        if event.is_keepalive:
                            continue
                        observation = handle.observer.observe(
                            event,
                            sequence=sequence,
                        )
                        sequence += 1
                        if observation is not None:
                            self._offer(handle, observation)
                    missing_terminal = handle.observer.eof_observation()
                    if missing_terminal is not None:
                        self._offer(handle, missing_terminal)
                    break
                except asyncio.CancelledError:
                    raise
                except Exception:
                    handle.observer.diagnostics.reader_errors += 1
                    self._offer_reader_reconcile(handle, attempt=attempt)
                    logger.exception(
                        "Dream lifecycle reader failed run_id=%s "
                        "thread_id=%s turn_id=%s attempt=%d",
                        handle.identity.run_id,
                        handle.identity.thread_id,
                        handle.identity.turn_id,
                        attempt + 1,
                    )
                    if attempt > 0 or not handle.lease.active:
                        break
                    old_token = handle.token
                    with contextlib.suppress(Exception):
                        await handle.bus.unsubscribe(old_token)
                    try:
                        handle.token = await handle.bus.subscribe()
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        handle.observer.diagnostics.reader_errors += 1
                        logger.exception(
                            "Dream lifecycle reader restart failed run_id=%s "
                            "thread_id=%s turn_id=%s",
                            handle.identity.run_id,
                            handle.identity.thread_id,
                            handle.identity.turn_id,
                        )
                        break
                    handle.observer.diagnostics.reader_restarts += 1
        finally:
            await self._close_from_reader(handle)

    def _offer_reader_reconcile(
        self,
        handle: DreamTurnHandle,
        *,
        attempt: int,
    ) -> None:
        """Clear a possibly stale business hint after a reader failure."""

        identity = handle.identity
        self._offer(
            handle,
            DreamLifecycleObservation(
                event_id=_reader_error_event_id(identity, attempt),
                run_id=identity.run_id,
                thread_id=identity.thread_id,
                turn_id=identity.turn_id,
                actor_id=identity.actor_id,
                sequence=max(handle.observer.next_sequence - 1, -1),
                kind="reconcile_requested",
            ),
        )

    async def _run_sink(self, handle: DreamTurnHandle) -> None:
        while True:
            item = await handle.queue.get()
            if item is _QUEUE_STOP:
                return
            if not isinstance(item, DreamLifecycleObservation) or not handle.lease.active:
                continue
            try:
                if item.kind == "reconcile_requested":
                    await self._sink.reconcile(
                        item.run_id,
                        item.actor_id,
                        handle.lease,
                    )
                else:
                    await self._sink.project(item, handle.lease)
            except asyncio.CancelledError:
                raise
            except Exception:
                handle.observer.diagnostics.sink_errors += 1
                logger.exception(
                    "Dream lifecycle sink failed run_id=%s thread_id=%s turn_id=%s",
                    handle.identity.run_id,
                    handle.identity.thread_id,
                    handle.identity.turn_id,
                )

    def _offer(
        self,
        handle: DreamTurnHandle,
        observation: DreamLifecycleObservation,
    ) -> None:
        try:
            handle.queue.put_nowait(observation)
            return
        except asyncio.QueueFull:
            handle.observer.diagnostics.queue_overflow += 1
        # Terminal/reconciliation hints are higher value than activity hints.
        if observation.kind not in {"turn_settled_hint", "reconcile_requested"}:
            return
        with contextlib.suppress(asyncio.QueueEmpty):
            handle.queue.get_nowait()
        with contextlib.suppress(asyncio.QueueFull):
            handle.queue.put_nowait(observation)

    async def _close_from_reader(self, handle: DreamTurnHandle) -> None:
        if not self._begin_close(handle):
            return
        try:
            with contextlib.suppress(Exception):
                await handle.bus.unsubscribe(handle.token)
            worker = handle.worker_task
            if worker is not None:
                try:
                    if self._graceful_sink_timeout_s <= 0:
                        raise asyncio.TimeoutError
                    # FIFO placement preserves a queued terminal with
                    # queue_size=1. The bounded put prevents a hung sink plus
                    # full queue from trapping teardown before its timeout.
                    await asyncio.wait_for(
                        handle.queue.put(_QUEUE_STOP),
                        timeout=self._graceful_sink_timeout_s,
                    )
                    await asyncio.wait_for(
                        asyncio.shield(worker),
                        timeout=self._graceful_sink_timeout_s,
                    )
                except asyncio.TimeoutError:
                    handle.lease.revoke()
                    self._force_queue_stop(handle)
                    worker.cancel()
                    await self._await_cancelled_or_detach(handle, [worker])
        finally:
            handle.lease.revoke()
            self._finish_close(handle)

    async def _close_external(self, handle: DreamTurnHandle, *, reason: str) -> None:
        del reason
        if not self._begin_close(handle):
            cleanup_done = handle.cleanup_done
            if cleanup_done is not None:
                try:
                    await asyncio.wait_for(
                        cleanup_done.wait(),
                        timeout=max(self._graceful_sink_timeout_s * 2, 0.05),
                    )
                except asyncio.TimeoutError:
                    pass
                if cleanup_done.is_set():
                    return
            # The original closer exceeded its bounded window.  This caller
            # performs an idempotent takeover: lease revoke, unsubscribe,
            # cancellation and _finish_close are all safe to repeat.
        try:
            handle.lease.revoke()
            self._force_queue_stop(handle)
            with contextlib.suppress(Exception):
                await handle.bus.unsubscribe(handle.token)
            current = asyncio.current_task()
            tasks = [
                task
                for task in (handle.reader_task, handle.worker_task)
                if task is not None and task is not current and not task.done()
            ]
            for task in tasks:
                task.cancel()
            if tasks:
                await self._await_cancelled_or_detach(handle, tasks)
        finally:
            self._finish_close(handle)

    @staticmethod
    def _force_queue_stop(handle: DreamTurnHandle) -> None:
        """Ensure a cancellation-swallowing worker exits after its sink returns."""

        while True:
            try:
                handle.queue.put_nowait(_QUEUE_STOP)
                return
            except asyncio.QueueFull:
                with contextlib.suppress(asyncio.QueueEmpty):
                    handle.queue.get_nowait()

    async def _await_cancelled_or_detach(
        self,
        handle: DreamTurnHandle,
        tasks: list[asyncio.Task[Any]],
    ) -> None:
        """Never let a sink that swallows cancellation trap Agent teardown."""

        if not tasks:
            return
        timeout = max(self._graceful_sink_timeout_s, 0.01)
        done, pending = await asyncio.wait(tasks, timeout=timeout)
        for task in done:
            self._consume_task_result(task)
        for task in pending:
            if task in self._detached_tasks:
                continue
            handle.observer.diagnostics.detached_tasks += 1
            self._detached_tasks.add(task)
            task.add_done_callback(self._detached_task_done)

    def _detached_task_done(self, task: asyncio.Task[Any]) -> None:
        self._detached_tasks.discard(task)
        self._consume_task_result(task)

    @staticmethod
    def _consume_task_result(task: asyncio.Task[Any]) -> None:
        if task.cancelled():
            return
        with contextlib.suppress(asyncio.CancelledError, Exception):
            task.exception()

    async def _drain_detached_tasks(self) -> None:
        """Give isolated cancellation-swallowing tasks one final bounded drain."""

        tasks = [task for task in self._detached_tasks if not task.done()]
        if not tasks:
            return
        for task in tasks:
            task.cancel()
        done, pending = await asyncio.wait(
            tasks,
            timeout=max(self._graceful_sink_timeout_s, 0.01),
        )
        for task in done:
            self._detached_task_done(task)
        if pending:
            logger.error(
                "Dream lifecycle detached sink tasks remain after bounded close: count=%d",
                len(pending),
            )

    def _begin_close(self, handle: DreamTurnHandle) -> bool:
        if handle.close_started:
            return False
        handle.close_started = True
        return True

    def _finish_close(self, handle: DreamTurnHandle) -> None:
        current = self._handles.get(
            (handle.identity.thread_id, handle.identity.turn_id)
        )
        if current is handle:
            self._handles.pop(
                (handle.identity.thread_id, handle.identity.turn_id),
                None,
            )
        if not handle.archived:
            self._archived.add(handle.observer.diagnostics)
            handle.archived = True
        cleanup_done = handle.cleanup_done
        if cleanup_done is not None:
            cleanup_done.set()


class DreamObserver:
    """Session lifecycle Observer that owns all Dream event resources.

    ``ClaudeAgentThreadFactory`` interacts only with
    ``SessionObserverRegistry``. Internal coordinator/classifier details stay
    behind this standard class and remain off the Agent/SSE critical path.
    """

    def __init__(
        self,
        coordinator: DreamLifecycleCoordinator | None = None,
    ) -> None:
        self._coordinator = coordinator or DreamLifecycleCoordinator()
        self._turn_by_session: dict[str, str] = {}

    async def on_after_context_assembly(
        self,
        session_id: str,
        metadata: dict[str, Any],
    ) -> None:
        context = metadata.get("dream_context")
        if context is None:
            return
        turn_id = str(metadata.get("turn_id") or "")
        actor_id = str(metadata.get("actor_id") or "")
        bus = metadata.get("event_bus")
        if not turn_id or not actor_id or bus is None:
            raise ValueError("Dream Observer metadata is incomplete")
        # Record cleanup ownership before attach; a partially attached
        # implementation is still closed by the post-session hook.
        self._turn_by_session[session_id] = turn_id
        await self._coordinator.attach_before_session_execution(
            context=context,
            actor_id=actor_id,
            turn_id=turn_id,
            bus=bus,
        )

    async def on_after_session_started(self, session_id: str) -> None:
        turn_id = self._turn_by_session.pop(session_id, None)
        if turn_id is None:
            return
        await self._coordinator.close_turn(
            session_id,
            turn_id,
            reason="session_execution_finished",
        )

    async def on_before_session_ended(self, session_id: str) -> None:
        self._turn_by_session.pop(session_id, None)
        await self._coordinator.close_session(
            session_id,
            reason="session_ended",
        )

    async def aclose(self) -> None:
        self._turn_by_session.clear()
        await self._coordinator.aclose()

    def diagnostics(self) -> dict[str, int]:
        return self._coordinator.diagnostics()

    def projection_snapshot(self) -> list[DreamWorkflowActivityProjection]:
        return self._coordinator.projection_snapshot()

__all__ = [
    "DreamBusinessSink",
    "DreamObserver",
    "DreamLifecycleCoordinator",
    "DreamLifecycleObservation",
    "DreamLifecycleObserver",
    "DreamObserverDiagnostics",
    "DreamTurnHandle",
    "DreamTurnIdentity",
    "DreamTurnLease",
    "DreamWorkflowActivityProjection",
    "DreamWorkflowActivityProjectionSink",
    "NormalizedAgentTurnClassifier",
    "NormalizedTurnOutcome",
    "NormalizedTurnResult",
    "NullDreamBusinessSink",
    "drain_normalized_agent_turn",
]
