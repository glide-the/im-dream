"""Chat-specific adapter from normalized Agent events to public SSE frames."""
from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator

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

    async def iter_frames(
        self,
        events: AsyncIterable[NormalizedAgentEvent],
    ) -> AsyncIterator[str]:
        async for event in events:
            yield self.encode(event)
