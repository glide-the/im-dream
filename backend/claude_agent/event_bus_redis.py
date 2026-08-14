# [Input] redis.asyncio (redis-py >= 5.0), claude_agent/event_bus.py IEventBus.
# [Output] RedisStreamEventBus adapter for shared standalone-Redis event storage.
# [Pos] event-bus-redis adapter node in backend/claude_agent
# [Sync] 2026-08-11: Redis Streams adapter with atomic terminal and live runtime coverage.

"""Redis Streams EventBus Adapter.

Activated when INK_AGENT_EVENT_BUS_BACKEND=redis.

Environment variables
---------------------
INK_AGENT_REDIS_URL         redis://localhost:6379/0  (default)
INK_AGENT_EVENT_BUS_TTL_S   3600                     (stream key expiry, seconds)

Redis key pattern
-----------------
ink:sse:{session_id}:{turn_id}  (name retained for rolling compatibility)

Scope
-----
The adapter gives callers that already know ``(session_id, turn_id)`` shared
stream replay and atomic terminal arbitration. The current Chat active-turn
registry and Stop/confirmation control plane remain process-local, so this is
not by itself cross-worker or cross-pod HTTP reconnect support.

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
import inspect
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

_PUBLISH_EVENT_LUA = """
local function frame_is_finish(frame)
  if type(frame) ~= 'string' then
    return false
  end
  return string.find(
           frame,
           '^%s*data:%s*{%s*"type"%s*:%s*"finish"'
         ) ~= nil or
         string.find(
           frame,
           '^%s*{%s*"version"%s*:%s*1%s*,%s*"type"%s*:%s*"finish"'
         ) ~= nil
end
if redis.call('GET', KEYS[2]) then
  return 0
end
local entries = redis.call('XREVRANGE', KEYS[1], '+', '-', 'COUNT', 1)
if #entries > 0 then
  local fields = entries[1][2]
  local terminal_done = false
  local finish_seen = false
  for index = 1, #fields, 2 do
    if (fields[index] == 'terminal' and fields[index + 1] == 'done') or
       (fields[index] == 'frame' and fields[index + 1] == ARGV[2]) then
      terminal_done = true
    elseif (fields[index] == 'terminal' and fields[index + 1] == 'finish') or
           (fields[index] == 'frame' and frame_is_finish(fields[index + 1])) then
      finish_seen = true
    end
  end
  if terminal_done then
    redis.call('SET', KEYS[2], 'done', 'EX', tonumber(ARGV[3]))
    redis.call('EXPIRE', KEYS[1], tonumber(ARGV[3]))
    return 0
  end
  if finish_seen then
    redis.call('SET', KEYS[2], 'done', 'EX', tonumber(ARGV[3]))
    redis.call('XADD', KEYS[1], '*', 'frame', ARGV[2], 'terminal', 'done')
    redis.call('EXPIRE', KEYS[1], tonumber(ARGV[3]))
    return 0
  end
end
redis.call('XADD', KEYS[1], '*', 'frame', ARGV[1])
redis.call('EXPIRE', KEYS[1], tonumber(ARGV[3]))
return 1
"""

_PUBLISH_TERMINAL_LUA = """
local function frame_is_finish(frame)
  if type(frame) ~= 'string' then
    return false
  end
  return string.find(
           frame,
           '^%s*data:%s*{%s*"type"%s*:%s*"finish"'
         ) ~= nil or
         string.find(
           frame,
           '^%s*{%s*"version"%s*:%s*1%s*,%s*"type"%s*:%s*"finish"'
         ) ~= nil
end
if redis.call('GET', KEYS[2]) then
  return 0
end
local entries = redis.call('XREVRANGE', KEYS[1], '+', '-', 'COUNT', 1)
if #entries > 0 then
  local fields = entries[1][2]
  for index = 1, #fields, 2 do
    if (fields[index] == 'terminal' and fields[index + 1] == 'done') or
       (fields[index] == 'frame' and fields[index + 1] == ARGV[3]) then
      redis.call('SET', KEYS[2], 'done', 'EX', tonumber(ARGV[4]))
      redis.call('EXPIRE', KEYS[1], tonumber(ARGV[4]))
      return 0
    end
  end
end
local finish_seen = false
if #entries > 0 then
  local fields = entries[1][2]
  for index = 1, #fields, 2 do
    if fields[index] == 'terminal' and fields[index + 1] == 'finish' then
      finish_seen = true
    elseif fields[index] == 'frame' and frame_is_finish(fields[index + 1]) then
      finish_seen = true
    end
  end
end
redis.call('SET', KEYS[2], 'done', 'EX', tonumber(ARGV[4]))
if ARGV[2] == '1' and not finish_seen then
  redis.call('XADD', KEYS[1], '*', 'frame', ARGV[1], 'terminal', 'finish')
end
redis.call('XADD', KEYS[1], '*', 'frame', ARGV[3], 'terminal', 'done')
redis.call('EXPIRE', KEYS[1], tonumber(ARGV[4]))
return 1
"""


class RedisStreamEventBus(IEventBus):
    """Redis Streams EventBus for shared replay and terminal arbitration.

    Each (session_id, turn_id) pair maps to one Redis Stream key.
    Callers with the same explicit turn identity can receive full history (via
    XRANGE) plus live events (via XREAD BLOCK). HTTP routing/control ownership
    is deliberately outside this adapter and remains process-local today.

    Activate with ``INK_AGENT_EVENT_BUS_BACKEND=redis``. The deployment must
    provide the configured Redis service; dependency selection fails fast.
    """

    def __init__(self, session_id: str, turn_id: str) -> None:
        if _STREAM_TTL <= 0:
            raise RuntimeError("INK_AGENT_EVENT_BUS_TTL_S must be greater than zero")
        # Keep the historical key name during the wire-format migration so an
        # in-flight turn remains reconnectable across a rolling deployment.
        self._key = f"ink:sse:{session_id}:{turn_id}"
        # Hash the marker using exactly the stream-key bytes. This preserves the
        # historical stream key while keeping both Lua KEYS in one Cluster slot.
        self._terminal_key = f"{{{self._key}}}:terminal"
        self._done_flag: bool = False
        self._finish_published: bool = False
        self._lock = asyncio.Lock()

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

    @classmethod
    async def validate_connection(cls) -> None:
        """Fail application startup before accepting turns if Redis is unusable."""

        if _STREAM_TTL <= 0:
            raise RuntimeError("INK_AGENT_EVENT_BUS_TTL_S must be greater than zero")
        client = await cls._redis()
        if not await asyncio.wait_for(client.ping(), timeout=5.0):
            raise RuntimeError("configured Agent Redis EventBus did not answer PING")

    @classmethod
    async def aclose(cls) -> None:
        """Close and reset the process-wide Redis client exactly once.

        Resetting the class slot before the first await makes concurrent close
        calls idempotent and ensures a failed client close cannot leave a
        poisoned connection cached for a later application lifecycle.
        """

        client = cls._client
        if client is None:
            return
        cls._client = None
        close = getattr(client, "aclose", None)
        if not callable(close):
            close = getattr(client, "close", None)
        if not callable(close):
            return
        result = close()
        if inspect.isawaitable(result):
            await result

    # ------------------------------------------------------------------
    # IEventBus
    # ------------------------------------------------------------------

    async def publish(self, event: Optional[NormalizedAgentEvent]) -> None:
        if event is None:
            async with self._lock:
                if self._done_flag:
                    return
                await self._publish_terminal_script(None)
                self._done_flag = True
            return
        normalized = coerce_normalized_event(event)
        if normalized.type == "finish":
            await self.publish_terminal(normalized)
            return
        async with self._lock:
            if self._done_flag:
                return
            r = await self._redis()
            published = await r.eval(
                _PUBLISH_EVENT_LUA,
                2,
                self._key,
                self._terminal_key,
                normalized.to_wire_json(),
                _SENTINEL_PAYLOAD,
                str(_STREAM_TTL),
            )
            if not published:
                self._done_flag = True

    async def publish_terminal(self, event: NormalizedAgentEvent) -> None:
        normalized = coerce_normalized_event(event)
        if normalized.type != "finish":
            raise ValueError("terminal EventBus event must have type=finish")
        async with self._lock:
            if self._done_flag:
                return
            await self._publish_terminal_script(normalized)
            self._finish_published = True
            self._done_flag = True

    async def _publish_terminal_script(
        self,
        event: NormalizedAgentEvent | None,
    ) -> None:
        r = await self._redis()
        await r.eval(
            _PUBLISH_TERMINAL_LUA,
            2,
            self._key,
            self._terminal_key,
            event.to_wire_json() if event is not None else "",
            "1" if event is not None else "0",
            _SENTINEL_PAYLOAD,
            str(_STREAM_TTL),
        )

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
                self._done_flag = True
                return
            event = self._decode_event(frame)
            yield event
            if event.type == "finish":
                self._finish_published = True
                self._done_flag = True
                return

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
            # redis-py returns a list of pairs for RESP2 and a mapping for
            # RESP3. Normalize both without changing the public EventBus shape.
            if isinstance(results, dict):
                stream_results = (
                    (
                        stream_key,
                        nested_messages[0]
                        if len(nested_messages) == 1
                        and isinstance(nested_messages[0], list)
                        else nested_messages,
                    )
                    for stream_key, nested_messages in results.items()
                )
            else:
                stream_results = results
            for _stream_key, messages in stream_results:
                for msg_id, data in messages:
                    last_id = msg_id
                    frame = data.get("frame")
                    if frame == _SENTINEL_PAYLOAD:
                        self._done_flag = True
                        return
                    event = self._decode_event(frame)
                    yield event
                    if event.type == "finish":
                        self._finish_published = True
                        self._done_flag = True
                        return

    @property
    def is_done(self) -> bool:
        return self._done_flag
