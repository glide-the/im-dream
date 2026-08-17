"""Chat-specific adapter from normalized Agent events to public SSE frames."""
from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator
import json

from claude_agent.sse import encode_json_sse
from claude_agent.stream_events import NormalizedAgentEvent


class ChatStreamAdapter:
    """Encode the stable ``/api/claude-agent`` Chat event contract.

    This adapter deliberately performs no filtering.  In particular, every
    normalized ``text-delta`` produces exactly one Chat SSE frame.
    """

    @staticmethod
    def encode(event: NormalizedAgentEvent) -> str:
        if event.is_keepalive:
            return ": keepalive\n\n"
        return encode_json_sse(event.type, dict(event.data))

    @staticmethod
    def decode(frame: str) -> NormalizedAgentEvent:
        """Decode one complete frame emitted by :meth:`encode`.

        This is the shared Chat contract decoder for server-owned drains. It is
        intentionally strict: internal callers must consume the same public
        stream as HTTP clients and cannot introduce a Dream-specific parser.
        """

        if not isinstance(frame, str) or not frame:
            raise TypeError("Chat SSE frame must be non-empty text")
        if frame.startswith(":"):
            return NormalizedAgentEvent.keepalive()
        data_lines = [
            line[5:].lstrip()
            for line in frame.splitlines()
            if line.startswith("data:")
        ]
        if not data_lines:
            raise ValueError("Chat SSE frame has no data field")
        try:
            payload = json.loads("\n".join(data_lines))
        except json.JSONDecodeError as exc:
            raise ValueError("Chat SSE frame contains invalid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("Chat SSE payload must be an object")
        event_type = payload.pop("type", None)
        if not isinstance(event_type, str) or not event_type:
            raise ValueError("Chat SSE payload has no event type")
        return NormalizedAgentEvent.create(event_type, payload)

    async def iter_frames(
        self,
        events: AsyncIterable[NormalizedAgentEvent],
    ) -> AsyncIterator[str]:
        async for event in events:
            yield self.encode(event)
