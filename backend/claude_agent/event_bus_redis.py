# [Input] redis.asyncio (redis-py >= 5.0), claude_agent/event_bus.py IEventBus.
# [Output] RedisStreamEventBus Adapter for multi-process / multi-pod deployment.
# [Pos] event-bus-redis adapter node in backend/claude_agent
# [Sync] 2026-06-09: initial implementation — Redis Streams adapter.
#                    Not tested in this release; activated via
#                    INK_AGENT_EVENT_BUS_BACKEND=redis.

"""Redis Streams EventBus Adapter.

Activated when INK_AGENT_EVENT_BUS_BACKEND=redis.

Environment variables
---------------------
INK_AGENT_REDIS_URL         redis://localhost:6379/0  (default)
INK_AGENT_EVENT_BUS_TTL_S   3600                     (stream key expiry, seconds)

Redis key pattern
-----------------
ink:sse:{session_id}:{turn_id}  (name retained for rolling compatibility)

Protocol
--------
- publish  → XADD the existing compatibility key with a versioned event payload
             and refresh its TTL
- subscribe → XRANGE (replay) + XREAD BLOCK (live)
- sentinel  → published as the magic string "__sentinel__"
- unsubscribe → no-op (stateless consumers)
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from typing import AsyncIterator, Optional

from claude_agent.event_bus import IEventBus
from claude_agent.stream_events import (
    NormalizedAgentEvent,
    coerce_normalized_event,
    normalized_event_from_legacy_chat_frame,
)

logger = logging.getLogger(__name__)

_REDIS_URL: str = os.getenv("INK_AGENT_REDIS_URL", "redis://localhost:6379/0") or "redis://localhost:6379/0"
_STREAM_TTL: int = int(os.getenv("INK_AGENT_EVENT_BUS_TTL_S", "3600") or "3600")
_SENTINEL_PAYLOAD: str = "__sentinel__"
_BLOCK_MS: int = 5000   # XREAD BLOCK timeout in milliseconds


class RedisStreamEventBus(IEventBus):
    """Redis Streams EventBus — supports multi-process / multi-pod reconnect.

    Each (session_id, turn_id) pair maps to one Redis Stream key.
    Multiple workers can subscribe to the same stream and receive the full
    history (via XRANGE) plus live events (via XREAD BLOCK).

    Note
    ----
    This adapter is implemented but NOT tested in the 2026-06-09 release.
    Activate with ``INK_AGENT_EVENT_BUS_BACKEND=redis``.
    """

    def __init__(self, session_id: str, turn_id: str) -> None:
        # Keep the historical key name during the wire-format migration so an
        # in-flight turn remains reconnectable across a rolling deployment.
        self._key = f"ink:sse:{session_id}:{turn_id}"
        self._done_flag: bool = False

    # ------------------------------------------------------------------
    # Lazy Redis client (class-level singleton)
    # ------------------------------------------------------------------

    _client: Optional[object] = None

    @classmethod
    async def _redis(cls):
        if cls._client is None:
            import redis.asyncio as aioredis  # type: ignore[import-not-found]
            cls._client = aioredis.from_url(_REDIS_URL, decode_responses=True)
        return cls._client

    # ------------------------------------------------------------------
    # IEventBus
    # ------------------------------------------------------------------

    async def publish(self, event: Optional[NormalizedAgentEvent]) -> None:
        if self._done_flag:
            return
        r = await self._redis()
        payload = (
            coerce_normalized_event(event).to_wire_json()
            if event is not None
            else _SENTINEL_PAYLOAD
        )
        await r.xadd(self._key, {"frame": payload})
        await r.expire(self._key, _STREAM_TTL)
        if event is None:
            self._done_flag = True

    async def subscribe(self) -> str:
        """Return a unique consumer ID (UUID string).

        Redis Streams are stateless from the consumer perspective; the ID
        is used only to identify log messages.
        """
        return str(uuid.uuid4())

    async def unsubscribe(self, token: object) -> None:
        # Stateless — no server-side cleanup required.
        pass

    @staticmethod
    def _decode_event(raw: str) -> NormalizedAgentEvent:
        try:
            return NormalizedAgentEvent.from_wire_json(raw)
        except ValueError:
            # Rolling-deploy compatibility for streams started by the previous
            # Chat-SSE-as-EventBus implementation.
            return normalized_event_from_legacy_chat_frame(raw)

    async def read(self, token: object) -> AsyncIterator[NormalizedAgentEvent]:  # type: ignore[override]
        r = await self._redis()

        # 1. Replay history (XRANGE 0 +)
        entries = await r.xrange(self._key)
        last_id = "0-0"
        for entry_id, data in entries:
            last_id = entry_id
            frame = data.get("frame")
            if frame == _SENTINEL_PAYLOAD:
                return
            yield self._decode_event(frame)

        # 2. Live delivery (XREAD BLOCK)
        while True:
            results = await r.xread(
                {self._key: last_id}, count=50, block=_BLOCK_MS
            )
            if not results:
                # Timeout → emit keepalive
                if self._done_flag:
                    break
                yield NormalizedAgentEvent.keepalive()
                continue
            for _stream_key, messages in results:
                for msg_id, data in messages:
                    last_id = msg_id
                    frame = data.get("frame")
                    if frame == _SENTINEL_PAYLOAD:
                        return
                    yield self._decode_event(frame)

    @property
    def is_done(self) -> bool:
        return self._done_flag
