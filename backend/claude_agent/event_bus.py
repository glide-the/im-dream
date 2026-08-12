# [Input] None — standalone EventBus Port/Adapter.
# [Output] Normalized-event IEventBus, InMemoryEventBus, BusProxyQueue, create_event_bus
#          consumed by thread_factory.py and service.py.
# [Pos] event-bus node in backend/claude_agent
# [Sync] 2026-06-09: initial implementation — Port/Adapter pattern for event broadcast.
#                    IEventBus defines publish/subscribe/unsubscribe/read.
#                    InMemoryEventBus: asyncio-based, supports replay buffer + fan-out.
#                    BusProxyQueue: adapts IEventBus.publish to asyncio.Queue.put interface
#                    so execute_session callbacks require zero changes.
#                    create_event_bus: factory selecting backend via INK_AGENT_EVENT_BUS_BACKEND.

"""Claude Agent normalized EventBus — Port/Adapter implementation.

Port
----
``IEventBus`` — stable broadcast interface used by thread_factory and service.
  publish(event)   — push a NormalizedAgentEvent (None = sentinel, stream done).
  subscribe()      — return an opaque token; internally replays history buffer
                     then live-delivers subsequent frames.
  unsubscribe(tok) — remove a consumer (does not cancel the producer task).
  read(tok)        — async-iterate normalized events until sentinel.
  is_done          — True after sentinel has been published.

Adapters
--------
``InMemoryEventBus``  — asyncio asyncio.Queue fan-out with replay buffer.
                        Default backend for single-process deployment.
``RedisStreamEventBus``  — imported lazily from event_bus_redis when
                           INK_AGENT_EVENT_BUS_BACKEND=redis.

Proxy
-----
``BusProxyQueue``  — wraps IEventBus.publish() as an asyncio.Queue-like .put()
                     so ClaudeAgentService.execute_session needs no changes.

Factory
-------
``create_event_bus(session_id, turn_id)``  — selects implementation from env.
"""
from __future__ import annotations

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional

from claude_agent.stream_events import NormalizedAgentEvent, coerce_normalized_event

logger = logging.getLogger(__name__)

# SSE keepalive comment sent when no event arrives within _READ_TIMEOUT_S.
_READ_TIMEOUT_S: float = 15.0


# ---------------------------------------------------------------------------
# Port
# ---------------------------------------------------------------------------


class IEventBus(ABC):
    """Stable broadcast interface — does not depend on any queue implementation.

    Contract
    --------
    - ``publish(None)`` is the sentinel that marks the stream as complete.
    - ``publish`` is idempotent after the sentinel: subsequent calls are no-ops.
    - ``subscribe`` replays the history buffer *then* registers for live events.
    - ``unsubscribe`` removes a consumer but does not affect the producer.
    - ``read`` is an async generator; it finishes when the sentinel is received.
    """

    @abstractmethod
    async def publish(self, event: Optional[NormalizedAgentEvent]) -> None:
        """Emit one normalized event. Pass ``None`` to signal completion."""
        ...

    @abstractmethod
    async def publish_terminal(self, event: NormalizedAgentEvent) -> None:
        """Atomically publish the first ``finish`` event and stream sentinel."""
        ...

    @abstractmethod
    async def subscribe(self) -> object:
        """Register a new consumer. Returns an opaque subscription token."""
        ...

    @abstractmethod
    async def unsubscribe(self, token: object) -> None:
        """Deregister a consumer. Safe to call multiple times."""
        ...

    @abstractmethod
    def read(self, token: object) -> AsyncIterator[NormalizedAgentEvent]:
        """Async-iterate normalized events until the sentinel."""
        ...

    @property
    @abstractmethod
    def is_done(self) -> bool:
        """True once the sentinel has been published."""
        ...


# ---------------------------------------------------------------------------
# Adapter A: InMemoryEventBus (default, single-process)
# ---------------------------------------------------------------------------


class InMemoryEventBus(IEventBus):
    """asyncio-based fan-out bus with replay buffer.

    - Replay buffer: every event (including sentinel) is appended to
      ``_buffer``.  New subscribers receive the full history immediately.
    - Fan-out: each subscriber gets its own ``asyncio.Queue`` so one slow
      consumer cannot block another.
    - Idempotent sentinel: once ``done=True``, further ``publish`` calls
      are silently ignored.
    - Thread-safe within a single asyncio event loop (uses asyncio.Lock).
    """

    def __init__(self) -> None:
        self._buffer: list[Optional[NormalizedAgentEvent]] = []
        self._subscribers: list[asyncio.Queue] = []
        self._done: bool = False
        self._finish_published: bool = False
        self._lock: asyncio.Lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # IEventBus
    # ------------------------------------------------------------------

    async def publish(self, event: Optional[NormalizedAgentEvent]) -> None:
        normalized = None if event is None else coerce_normalized_event(event)
        if normalized is not None and normalized.type == "finish":
            await self.publish_terminal(normalized)
            return
        async with self._lock:
            if self._done:
                return  # idempotent after sentinel
            self._buffer.append(normalized)
            if normalized is None:
                self._done = True
            for q in list(self._subscribers):
                q.put_nowait(normalized)

    async def publish_terminal(self, event: NormalizedAgentEvent) -> None:
        normalized = coerce_normalized_event(event)
        if normalized.type != "finish":
            raise ValueError("terminal EventBus event must have type=finish")
        async with self._lock:
            if self._done:
                return
            terminal_items: list[Optional[NormalizedAgentEvent]] = []
            if not self._finish_published:
                self._finish_published = True
                self._buffer.append(normalized)
                terminal_items.append(normalized)
            self._buffer.append(None)
            terminal_items.append(None)
            self._done = True
            for q in list(self._subscribers):
                for item in terminal_items:
                    q.put_nowait(item)

    async def subscribe(self) -> asyncio.Queue:
        """Return a new queue pre-loaded with the replay buffer."""
        q: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            for event in self._buffer:       # replay history
                await q.put(event)
            if not self._done:               # register for live events
                self._subscribers.append(q)
        return q

    async def unsubscribe(self, token: object) -> None:
        q = token
        async with self._lock:
            try:
                self._subscribers.remove(q)  # type: ignore[arg-type]
            except ValueError:
                pass

    async def read(self, token: object) -> AsyncIterator[NormalizedAgentEvent]:  # type: ignore[override]
        q: asyncio.Queue = token  # type: ignore[assignment]
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=_READ_TIMEOUT_S)
                if event is None:
                    break
                yield event
            except asyncio.TimeoutError:
                # No event within timeout window — emit SSE keepalive comment.
                if self._done:
                    break
                yield NormalizedAgentEvent.keepalive()
            except asyncio.CancelledError:
                # Cancellation belongs to the caller.  Treating it like the
                # stream sentinel makes shutdown/stop races look like a clean
                # EOF and can let outer owners skip their cancellation path.
                raise

    @property
    def is_done(self) -> bool:
        return self._done


# ---------------------------------------------------------------------------
# Proxy: asyncio.Queue-compatible shim for execute_session
# ---------------------------------------------------------------------------


class BusProxyQueue:
    """Adapts IEventBus.publish() to the asyncio.Queue.put() interface.

    ``ClaudeAgentService.execute_session`` and its streaming callbacks call
    ``await queue.put(event)`` throughout.  Replacing ``_TurnContext.queue``
    with a ``BusProxyQueue`` forwards every ``put`` to ``bus.publish``,
    routing normalized events to the EventBus without changing callback code.
    """

    __slots__ = ("_bus",)

    def __init__(self, bus: IEventBus) -> None:
        self._bus = bus

    async def put(self, event: Optional[NormalizedAgentEvent]) -> None:
        await self._bus.publish(event)

    async def put_terminal(self, event: NormalizedAgentEvent) -> None:
        await self._bus.publish_terminal(event)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_event_bus(session_id: str, turn_id: str) -> IEventBus:
    """Return an IEventBus implementation selected by environment variable.

    INK_AGENT_EVENT_BUS_BACKEND
        ``memory`` (default) — InMemoryEventBus (single-process, zero deps)
        ``redis``            — RedisStreamEventBus (multi-process, requires Redis)
    """
    backend = (os.getenv("INK_AGENT_EVENT_BUS_BACKEND") or "memory").strip().lower()
    if backend == "redis":
        try:
            # Import the lazy runtime dependency here so a configured Redis
            # deployment cannot construct an adapter that fails only on its
            # first publish (or silently diverges into process memory).
            import redis.asyncio as _redis_runtime  # noqa: F401, PLC0415
        except ImportError as exc:
            raise RuntimeError(
                "INK_AGENT_EVENT_BUS_BACKEND=redis requires the redis runtime dependency"
            ) from exc
        from claude_agent.event_bus_redis import RedisStreamEventBus  # noqa: PLC0415

        logger.debug(
            "EventBus backend=redis session_id=%s turn_id=%s", session_id, turn_id
        )
        return RedisStreamEventBus(session_id, turn_id)
    if backend != "memory":
        raise RuntimeError(
            "INK_AGENT_EVENT_BUS_BACKEND must be either 'memory' or 'redis'"
        )
    logger.debug(
        "EventBus backend=memory session_id=%s turn_id=%s", session_id, turn_id
    )
    return InMemoryEventBus()
