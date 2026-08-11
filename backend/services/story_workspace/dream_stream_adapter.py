"""Dream-specific projection from normalized Agent events to Dream SSE.

Unlike Chat, Dream exposes a deliberately smaller public contract.  All state
and policy required for that projection lives here so it cannot affect the Chat
adapter or the shared EventBus.
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Callable

from agent_stream_events import (
    NormalizedAgentEvent,
    coerce_normalized_event,
)


CursorConsumed = Callable[[int, int | None], bool]
PublicTextProjection = Callable[[str], tuple[str, bool, bool]]
PublicTextPredicate = Callable[[str], bool]
IncrementalTextSplit = Callable[[str], tuple[str, str]]


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class DreamAdaptation:
    handled: bool = False
    terminal: bool = False
    frames: tuple[str, ...] = ()


class DreamStreamAdapter:
    """Stateful adapter for the public Dream text/lifecycle contract."""

    def __init__(
        self,
        *,
        turn_id: str,
        public_text_projection: PublicTextProjection,
        public_text_is_sensitive: PublicTextPredicate,
        incremental_text_split: IncrementalTextSplit,
        redaction_text: str,
        max_text_length: int,
        max_pending_length: int,
    ) -> None:
        self.turn_id = turn_id
        self._public_text_projection = public_text_projection
        self._public_text_is_sensitive = public_text_is_sensitive
        self._incremental_text_split = incremental_text_split
        self._redaction_text = redaction_text
        self._max_text_length = max_text_length
        self._max_pending_length = max_pending_length
        self._pending = ""
        self._redacted = False
        self._redaction_emitted = False
        self._emitted_chars = 0

    @staticmethod
    def _frame(event: str, data: dict[str, Any], cursor: str | None = None) -> str:
        prefix = f"id: {cursor}\n" if cursor else ""
        return f"{prefix}event: {event}\ndata: {_json(data)}\n\n"

    def adapt(
        self,
        event: NormalizedAgentEvent,
        *,
        ordinal: int,
        cursor_consumed: CursorConsumed,
    ) -> DreamAdaptation:
        if event.is_keepalive:
            return DreamAdaptation(handled=True, frames=(": keepalive\n\n",))

        if event.type == "error":
            # Raw Chat/SDK error text can contain paths, provider diagnostics,
            # or request context. Dream exposes only a stable safe code.
            if cursor_consumed(ordinal, None):
                return DreamAdaptation(handled=True, terminal=True)
            return DreamAdaptation(
                handled=True,
                terminal=True,
                frames=(
                    self._frame(
                        "agent_turn_failed",
                        {
                            "turnId": self.turn_id,
                            "code": "DREAM_AGENT_TURN_FAILED",
                        },
                        f"{self.turn_id}:{ordinal}",
                    ),
                ),
            )

        if event.type == "finish":
            failed = event.data.get("finishReason") == "error"
            if cursor_consumed(ordinal, None):
                return DreamAdaptation(handled=True, terminal=True)
            return DreamAdaptation(
                handled=True,
                terminal=True,
                frames=(
                    self._frame(
                        "agent_turn_failed" if failed else "agent_turn_cancelled",
                        {
                            "turnId": self.turn_id,
                            **(
                                {"code": "DREAM_AGENT_TURN_FAILED"}
                                if failed
                                else {}
                            ),
                        },
                        f"{self.turn_id}:{ordinal}",
                    ),
                ),
            )

        if event.type == "message-final":
            frames: list[str] = []
            final_text = ""
            if not self._redacted:
                public_text, _truncated, text_is_redacted = self._public_text_projection(
                    self._pending
                )
                if text_is_redacted:
                    self._redacted = True
                    self._pending = ""
                    if not self._redaction_emitted:
                        final_text = self._redaction_text
                        self._redaction_emitted = True
                else:
                    remaining = max(0, self._max_text_length - self._emitted_chars)
                    final_text = public_text[:remaining]
                    self._emitted_chars += len(final_text)
                    self._pending = ""
            payload = {"turnId": self.turn_id}
            if final_text:
                if not cursor_consumed(ordinal, 0):
                    frames.append(
                        self._frame(
                            "assistant_text_delta",
                            {"turnId": self.turn_id, "delta": final_text},
                            f"{self.turn_id}:{ordinal}:0",
                        )
                    )
                if not cursor_consumed(ordinal, 1):
                    frames.append(
                        self._frame(
                            "assistant_message_committed",
                            payload,
                            f"{self.turn_id}:{ordinal}:1",
                        )
                    )
            elif not cursor_consumed(ordinal, None):
                frames.append(
                    self._frame(
                        "assistant_message_committed",
                        payload,
                        f"{self.turn_id}:{ordinal}",
                    )
                )
            return DreamAdaptation(handled=True, terminal=True, frames=tuple(frames))

        if event.type != "text-delta" or not isinstance(event.data.get("delta"), str):
            return DreamAdaptation()
        if self._redacted:
            return DreamAdaptation(handled=True)

        self._pending += str(event.data["delta"])
        if (
            len(self._pending) > self._max_pending_length
            or self._public_text_is_sensitive(self._pending)
        ):
            self._redacted = True
            self._pending = ""
            if self._redaction_emitted or cursor_consumed(ordinal, None):
                return DreamAdaptation(handled=True)
            self._redaction_emitted = True
            return DreamAdaptation(
                handled=True,
                frames=(
                    self._frame(
                        "assistant_text_delta",
                        {"turnId": self.turn_id, "delta": self._redaction_text},
                        f"{self.turn_id}:{ordinal}",
                    ),
                ),
            )

        public_prefix, self._pending = self._incremental_text_split(self._pending)
        remaining = max(0, self._max_text_length - self._emitted_chars)
        public_prefix = public_prefix[:remaining]
        self._emitted_chars += len(public_prefix)
        if not public_prefix or cursor_consumed(ordinal, None):
            return DreamAdaptation(handled=True)
        return DreamAdaptation(
            handled=True,
            frames=(
                self._frame(
                    "assistant_text_delta",
                    {"turnId": self.turn_id, "delta": public_prefix},
                    f"{self.turn_id}:{ordinal}",
                ),
            ),
        )


async def iter_dream_subscription_events(
    factory: Any,
    *,
    thread_id: str,
    expected_turn_id: str,
) -> AsyncIterator[NormalizedAgentEvent]:
    """Read Dream source events without routing production through Chat SSE.

    The legacy string fallback is intentionally isolated here.  It supports
    rolling deployments and older test doubles; current factories expose the
    protocol-neutral ``*_events`` methods and never take this path.
    """

    subscribe_expected_events = getattr(factory, "subscribe_expected_events", None)
    if callable(subscribe_expected_events):
        stream = subscribe_expected_events(thread_id, expected_turn_id)
    else:
        subscribe_events = getattr(factory, "subscribe_events", None)
        if callable(subscribe_events):
            stream = subscribe_events(thread_id)
        else:
            subscribe_expected_stream = getattr(
                factory,
                "subscribe_expected_stream",
                None,
            )
            stream = (
                subscribe_expected_stream(thread_id, expected_turn_id)
                if callable(subscribe_expected_stream)
                else factory.subscribe_stream(thread_id)
            )
    async for value in stream:
        try:
            yield coerce_normalized_event(value)
        except (TypeError, ValueError):
            # Non-event bytes/log lines from a legacy double are not part of
            # the Dream protocol and must never leak into its public SSE.  A
            # malformed legacy ``data:`` frame still consumes one ordinal so
            # Last-Event-ID remains stable across a rolling deployment.
            if isinstance(value, str) and any(
                line.startswith("data:") for line in value.splitlines()
            ):
                yield NormalizedAgentEvent.create("legacy-invalid-event")


async def iter_dream_run_events(
    factory: Any,
    request: Any,
) -> AsyncIterator[NormalizedAgentEvent]:
    """Execute a Dream turn on the normalized API, with legacy compatibility."""

    run_events = getattr(factory, "run_events", None)
    stream = run_events(request) if callable(run_events) else factory.run_streaming(request)
    async for value in stream:
        try:
            yield coerce_normalized_event(value)
        except (TypeError, ValueError):
            continue
