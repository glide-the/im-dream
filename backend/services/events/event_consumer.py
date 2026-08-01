"""Idempotent aggregate-ordered consumption for canonical events."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
import inspect
import time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.models.events import EventEnvelope


EventHandler = Callable[[EventEnvelope], None | Awaitable[None]]


class EventGapAlert(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    aggregate_id: str
    expected_version: int = Field(ge=1)
    next_buffered_version: int = Field(ge=1)
    waited_seconds: float = Field(ge=0)


GapAlertHandler = Callable[[EventGapAlert], None | Awaitable[None]]


class AggregateOrderError(RuntimeError):
    pass


class EventConsumer:
    """Deduplicate IDs, buffer gaps, and process each aggregate in order."""

    def __init__(
        self,
        handler: EventHandler,
        *,
        initial_versions: Mapping[str, int] | None = None,
        gap_timeout_seconds: float = 30.0,
        alert_handler: GapAlertHandler | None = None,
        monotonic_clock: Callable[[], float] | None = None,
    ) -> None:
        if gap_timeout_seconds < 0:
            raise ValueError("gap_timeout_seconds cannot be negative")
        self._handler = handler
        self._next_versions = dict(initial_versions or {})
        if any(version < 1 for version in self._next_versions.values()):
            raise ValueError("initial versions must be at least 1")
        self._gap_timeout_seconds = gap_timeout_seconds
        self._alert_handler = alert_handler
        self._clock = monotonic_clock or time.monotonic
        self._processed_event_ids: set[str] = set()
        self._buffered_event_ids: set[str] = set()
        self._buffers: dict[str, dict[int, tuple[EventEnvelope, float]]] = {}
        self._alerted_gaps: set[tuple[str, int]] = set()
        self._lock = asyncio.Lock()

    @property
    def processed_event_ids(self) -> frozenset[str]:
        return frozenset(self._processed_event_ids)

    def next_expected_version(self, aggregate_id: str) -> int:
        return self._next_versions.get(aggregate_id, 1)

    async def consume(self, envelope: EventEnvelope | dict[str, Any]) -> bool:
        """Return true when this call processes the event, false when held/deduped."""

        event = EventEnvelope.model_validate(envelope)
        async with self._lock:
            if event.event_id in self._processed_event_ids:
                return False
            if event.event_id in self._buffered_event_ids:
                return False

            expected = self.next_expected_version(event.aggregate_id)
            if event.aggregate_version < expected:
                raise AggregateOrderError(
                    "unseen event_id has a stale aggregate_version"
                )
            if event.aggregate_version > expected:
                aggregate_buffer = self._buffers.setdefault(event.aggregate_id, {})
                if event.aggregate_version in aggregate_buffer:
                    raise AggregateOrderError(
                        "different event_id already occupies aggregate_version"
                    )
                aggregate_buffer[event.aggregate_version] = (event, self._clock())
                self._buffered_event_ids.add(event.event_id)
                await self._check_timeouts_locked()
                return False

            await self._handle(event)
            self._mark_processed(event)
            await self._drain(event.aggregate_id)
            return True

    async def check_timeouts(self) -> list[EventGapAlert]:
        """Emit one alert per unresolved expected version after its timeout."""

        async with self._lock:
            return await self._check_timeouts_locked()

    async def _drain(self, aggregate_id: str) -> None:
        aggregate_buffer = self._buffers.get(aggregate_id)
        while aggregate_buffer:
            expected = self.next_expected_version(aggregate_id)
            buffered = aggregate_buffer.pop(expected, None)
            if buffered is None:
                break
            event, buffered_at = buffered
            self._buffered_event_ids.discard(event.event_id)
            try:
                await self._handle(event)
            except Exception:
                aggregate_buffer[expected] = (event, buffered_at)
                self._buffered_event_ids.add(event.event_id)
                raise
            self._mark_processed(event)
        if not aggregate_buffer:
            self._buffers.pop(aggregate_id, None)

    def _mark_processed(self, event: EventEnvelope) -> None:
        self._processed_event_ids.add(event.event_id)
        self._next_versions[event.aggregate_id] = event.aggregate_version + 1
        self._alerted_gaps = {
            gap
            for gap in self._alerted_gaps
            if gap[0] != event.aggregate_id or gap[1] >= event.aggregate_version + 1
        }

    async def _handle(self, event: EventEnvelope) -> None:
        result = self._handler(event)
        if inspect.isawaitable(result):
            await result

    async def _check_timeouts_locked(self) -> list[EventGapAlert]:
        now = self._clock()
        emitted: list[EventGapAlert] = []
        for aggregate_id, aggregate_buffer in self._buffers.items():
            expected = self.next_expected_version(aggregate_id)
            gap_key = (aggregate_id, expected)
            if gap_key in self._alerted_gaps or not aggregate_buffer:
                continue
            next_version = min(aggregate_buffer)
            _, buffered_at = aggregate_buffer[next_version]
            waited = max(0.0, now - buffered_at)
            if waited < self._gap_timeout_seconds:
                continue
            alert = EventGapAlert(
                aggregate_id=aggregate_id,
                expected_version=expected,
                next_buffered_version=next_version,
                waited_seconds=waited,
            )
            self._alerted_gaps.add(gap_key)
            emitted.append(alert)
            if self._alert_handler is not None:
                result = self._alert_handler(alert)
                if inspect.isawaitable(result):
                    await result
        return emitted

