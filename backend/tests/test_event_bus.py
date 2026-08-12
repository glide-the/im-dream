# [Input] Consume InMemoryEventBus, BusProxyQueue, create_event_bus from event_bus.py.
# [Output] Verify publish/subscribe replay, multi-consumer fan-out, sentinel semantics.
# [Pos] test node in backend/tests
# [Sync] 2026-06-09: memory-mode EventBus unit tests.

from __future__ import annotations

import asyncio
import builtins
import os
import re
import sys
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util
from claude_agent.stream_events import NormalizedAgentEvent
from claude_agent.event_bus_redis import (
    RedisStreamEventBus,
    _PUBLISH_EVENT_LUA,
    _PUBLISH_TERMINAL_LUA,
)

_EVENT_BUS_PATH = ROOT / "claude_agent" / "event_bus.py"
_spec = importlib.util.spec_from_file_location("claude_agent_event_bus", _EVENT_BUS_PATH)
assert _spec and _spec.loader
_event_bus = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_event_bus)
BusProxyQueue = _event_bus.BusProxyQueue
InMemoryEventBus = _event_bus.InMemoryEventBus
create_event_bus = _event_bus.create_event_bus


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


async def _read_n(bus, token, count: int) -> list[NormalizedAgentEvent]:
    events: list[NormalizedAgentEvent] = []
    reader = bus.read(token)
    try:
        async for event in reader:
            events.append(event)
            if len(events) >= count:
                break
    finally:
        await reader.aclose()
    return events


class TestInMemoryEventBus(unittest.TestCase):
    def test_publish_and_read_until_sentinel(self):
        async def _case():
            bus = InMemoryEventBus()
            token = await bus.subscribe()
            event = NormalizedAgentEvent.create("text-delta")
            await bus.publish(event)
            await bus.publish(None)
            events = [item async for item in bus.read(token)]
            self.assertEqual(events, [event])
            self.assertTrue(bus.is_done)

        _run(_case())

    def test_late_subscriber_replays_buffer(self):
        async def _case():
            bus = InMemoryEventBus()
            first = NormalizedAgentEvent.create("test", {"value": "frame-1"})
            second = NormalizedAgentEvent.create("test", {"value": "frame-2"})
            await bus.publish(first)
            await bus.publish(second)
            token = await bus.subscribe()
            events = await _read_n(bus, token, 2)
            self.assertEqual(events, [first, second])

        _run(_case())

    def test_unsubscribe_does_not_stop_bus(self):
        async def _case():
            bus = InMemoryEventBus()
            token = await bus.subscribe()
            await bus.unsubscribe(token)
            event = NormalizedAgentEvent.create("test", {"value": "after-unsub"})
            await bus.publish(event)
            token2 = await bus.subscribe()
            events = await _read_n(bus, token2, 1)
            self.assertEqual(events, [event])
            await bus.publish(None)

        _run(_case())

    def test_two_subscribers_receive_live_frames(self):
        async def _case():
            bus = InMemoryEventBus()
            t1 = await bus.subscribe()
            t2 = await bus.subscribe()

            async def _collect(token):
                out = []
                async for frame in bus.read(token):
                    out.append(frame)
                return out

            task = asyncio.create_task(_collect(t1))

            event = NormalizedAgentEvent.create("test", {"value": "live-1"})
            await bus.publish(event)
            await bus.publish(None)

            events1 = await task
            events2 = [item async for item in bus.read(t2)]
            self.assertEqual(events1, [event])
            self.assertEqual(events2, [event])

        _run(_case())

    def test_bus_proxy_queue_forwards_to_bus(self):
        async def _case():
            bus = InMemoryEventBus()
            proxy = BusProxyQueue(bus)
            token = await bus.subscribe()
            event = NormalizedAgentEvent.create("test", {"value": "via-proxy"})
            await proxy.put(event)
            await proxy.put(None)
            events = [item async for item in bus.read(token)]
            self.assertEqual(events, [event])

        _run(_case())

    def test_concurrent_terminal_publish_has_one_finish_and_one_sentinel(self):
        async def _case():
            bus = InMemoryEventBus()
            token = await bus.subscribe()
            first = NormalizedAgentEvent.create(
                "finish", {"finishReason": "stop"}
            )
            second = NormalizedAgentEvent.create(
                "finish", {"finishReason": "error"}
            )
            await asyncio.gather(
                bus.publish_terminal(first),
                bus.publish_terminal(second),
            )
            events = [item async for item in bus.read(token)]
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].type, "finish")
            self.assertIn(events[0], (first, second))

        _run(_case())

    def test_plain_finish_is_atomic_and_rejects_late_frames(self):
        async def _case():
            bus = InMemoryEventBus()
            token = await bus.subscribe()
            terminal = NormalizedAgentEvent.create(
                "finish", {"finishReason": "stop"}
            )
            await bus.publish(terminal)
            await bus.publish(NormalizedAgentEvent.create("text-delta"))
            await bus.publish_terminal(
                NormalizedAgentEvent.create(
                    "finish", {"finishReason": "error"}
                )
            )
            self.assertEqual(
                [item async for item in bus.read(token)],
                [terminal],
            )

        _run(_case())

    def test_bus_proxy_terminal_uses_atomic_contract(self):
        async def _case():
            bus = InMemoryEventBus()
            proxy = BusProxyQueue(bus)
            token = await bus.subscribe()
            terminal = NormalizedAgentEvent.create(
                "finish", {"finishReason": "stop"}
            )
            await proxy.put_terminal(terminal)
            self.assertEqual(
                [item async for item in bus.read(token)],
                [terminal],
            )

        _run(_case())

    def test_reader_cancellation_is_not_converted_to_clean_eof(self):
        async def _case():
            bus = InMemoryEventBus()
            token = await bus.subscribe()
            reader = bus.read(token)
            pending = asyncio.create_task(anext(reader))
            await asyncio.sleep(0)
            pending.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await pending
            await reader.aclose()
            await bus.unsubscribe(token)

        _run(_case())

    def test_create_event_bus_defaults_to_memory(self):
        old = os.environ.pop("INK_AGENT_EVENT_BUS_BACKEND", None)
        try:
            bus = create_event_bus("thread-1", "turn-1")
            self.assertIsInstance(bus, InMemoryEventBus)
        finally:
            if old is not None:
                os.environ["INK_AGENT_EVENT_BUS_BACKEND"] = old

    def test_create_event_bus_selects_packaged_redis_adapter(self):
        old = os.environ.get("INK_AGENT_EVENT_BUS_BACKEND")
        os.environ["INK_AGENT_EVENT_BUS_BACKEND"] = "redis"
        try:
            bus = create_event_bus("thread-redis", "turn-redis")
            self.assertIsInstance(bus, RedisStreamEventBus)
        finally:
            if old is None:
                os.environ.pop("INK_AGENT_EVENT_BUS_BACKEND", None)
            else:
                os.environ["INK_AGENT_EVENT_BUS_BACKEND"] = old

    def test_configured_redis_dependency_failure_is_not_silent_memory_fallback(self):
        old_backend = os.environ.get("INK_AGENT_EVENT_BUS_BACKEND")
        os.environ["INK_AGENT_EVENT_BUS_BACKEND"] = "redis"
        real_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name == "redis.asyncio":
                raise ImportError("simulated missing redis runtime")
            return real_import(name, *args, **kwargs)

        try:
            with mock.patch("builtins.__import__", side_effect=guarded_import):
                with self.assertRaisesRegex(RuntimeError, "requires the redis runtime"):
                    create_event_bus("thread-missing-redis", "turn-missing-redis")
        finally:
            if old_backend is None:
                os.environ.pop("INK_AGENT_EVENT_BUS_BACKEND", None)
            else:
                os.environ["INK_AGENT_EVENT_BUS_BACKEND"] = old_backend

    def test_unknown_backend_does_not_silently_fall_back_to_memory(self):
        old_backend = os.environ.get("INK_AGENT_EVENT_BUS_BACKEND")
        os.environ["INK_AGENT_EVENT_BUS_BACKEND"] = "redsi"
        try:
            with self.assertRaisesRegex(RuntimeError, "either 'memory' or 'redis'"):
                create_event_bus("thread-typo", "turn-typo")
        finally:
            if old_backend is None:
                os.environ.pop("INK_AGENT_EVENT_BUS_BACKEND", None)
            else:
                os.environ["INK_AGENT_EVENT_BUS_BACKEND"] = old_backend

    def test_redis_ttl_must_be_positive(self):
        previous = __import__(
            "claude_agent.event_bus_redis",
            fromlist=["_STREAM_TTL"],
        )._STREAM_TTL
        module = __import__("claude_agent.event_bus_redis", fromlist=["_STREAM_TTL"])
        module._STREAM_TTL = 0
        try:
            with self.assertRaisesRegex(RuntimeError, "must be greater than zero"):
                RedisStreamEventBus("thread-ttl", "turn-ttl")
        finally:
            module._STREAM_TTL = previous


class _FakeRedis:
    def __init__(self) -> None:
        self.marker = False
        self.frames: list[str] = []
        self.calls: list[tuple[str, int, tuple[object, ...]]] = []

    @staticmethod
    def _frame_is_finish(script: str, frame: str) -> bool:
        """Model only the two anchored wire shapes encoded by the Lua."""

        has_anchored_legacy = (
            "^%s*data:%s*{%s*\"type\"%s*:%s*\"finish\"" in script
        )
        has_anchored_normalized = (
            "^%s*{%s*\"version\"%s*:%s*1%s*,%s*\"type\"%s*:%s*\"finish\""
            in script
        )
        return (
            has_anchored_legacy
            and re.match(
                r'^\s*data:\s*\{\s*"type"\s*:\s*"finish"',
                frame,
            )
            is not None
        ) or (
            has_anchored_normalized
            and re.match(
                r'^\s*\{\s*"version"\s*:\s*1\s*,\s*"type"\s*:\s*"finish"',
                frame,
            )
            is not None
        )

    async def eval(self, script: str, key_count: int, *values: object) -> int:
        self.calls.append((script, key_count, values))
        argv = values[key_count:]
        if script == _PUBLISH_TERMINAL_LUA:
            if self.marker:
                return 0
            if (
                self.frames
                and self.frames[-1] == "__sentinel__"
                and "fields[index + 1] == ARGV[3]" in script
            ):
                self.marker = True
                return 0
            finish_seen = bool(
                self.frames
                and self._frame_is_finish(script, self.frames[-1])
            )
            self.marker = True
            if argv[1] == "1" and not finish_seen:
                self.frames.append(str(argv[0]))
            self.frames.append(str(argv[2]))
            return 1
        if script == _PUBLISH_EVENT_LUA:
            if self.marker:
                return 0
            if self.frames and self.frames[-1] == "__sentinel__":
                self.marker = True
                return 0
            if self.frames and self._frame_is_finish(script, self.frames[-1]):
                self.marker = True
                if (
                    "'frame', ARGV[2], 'terminal', 'done'"
                    in script
                ):
                    self.frames.append(str(argv[1]))
                return 0
            self.frames.append(str(argv[0]))
            return 1
        raise AssertionError("unexpected Redis script")


class TestRedisEventBusTerminalContract(unittest.TestCase):
    def test_cross_instance_marker_rejects_late_frame_and_second_terminal(self):
        async def _case():
            fake = _FakeRedis()
            previous = RedisStreamEventBus._client
            RedisStreamEventBus._client = fake
            try:
                producer = RedisStreamEventBus("thread-redis", "turn-redis")
                contender = RedisStreamEventBus("thread-redis", "turn-redis")
                terminal = NormalizedAgentEvent.create(
                    "finish", {"finishReason": "stop"}
                )
                await producer.publish(terminal)
                await contender.publish(
                    NormalizedAgentEvent.create(
                        "text-delta", {"delta": "late"}
                    )
                )
                await contender.publish_terminal(
                    NormalizedAgentEvent.create(
                        "finish", {"finishReason": "error"}
                    )
                )

                self.assertEqual(fake.frames, [terminal.to_wire_json(), "__sentinel__"])
                self.assertEqual(len(fake.calls), 2)
                self.assertEqual(fake.calls[0][1], 2)
                self.assertEqual(fake.calls[1][1], 2)
                self.assertEqual(
                    fake.calls[0][2][:2],
                    (
                        "ink:sse:thread-redis:turn-redis",
                        "{ink:sse:thread-redis:turn-redis}:terminal",
                    ),
                )
            finally:
                RedisStreamEventBus._client = previous

        _run(_case())

    def test_legacy_sentinel_blocks_new_cross_instance_terminal(self):
        async def _case():
            legacy_terminal = NormalizedAgentEvent.create(
                "finish", {"finishReason": "stop"}
            )
            fake = _FakeRedis()
            fake.frames.extend([
                legacy_terminal.to_wire_json(),
                "__sentinel__",
            ])
            previous = RedisStreamEventBus._client
            RedisStreamEventBus._client = fake
            try:
                contender = RedisStreamEventBus(
                    "thread-legacy-redis",
                    "turn-legacy-redis",
                )
                await contender.publish_terminal(
                    NormalizedAgentEvent.create(
                        "finish", {"finishReason": "error"}
                    )
                )

                self.assertTrue(fake.marker)
                self.assertEqual(
                    fake.frames,
                    [legacy_terminal.to_wire_json(), "__sentinel__"],
                )
                self.assertEqual(len(fake.calls), 1)
            finally:
                RedisStreamEventBus._client = previous

        _run(_case())

    def test_whitespace_legacy_finish_crash_window_adds_only_sentinel(self):
        async def _case():
            legacy_finish = (
                'data: {"type": "finish", "finishReason": "stop"}\n\n'
            )
            fake = _FakeRedis()
            # Simulate XADD(finish) succeeding before the old producer could
            # append its sentinel or the new marker key.
            fake.frames.append(legacy_finish)
            previous = RedisStreamEventBus._client
            RedisStreamEventBus._client = fake
            try:
                contender = RedisStreamEventBus(
                    "thread-legacy-crash",
                    "turn-legacy-crash",
                )
                await contender.publish_terminal(
                    NormalizedAgentEvent.create(
                        "finish",
                        {"finishReason": "error"},
                    )
                )

                self.assertTrue(fake.marker)
                self.assertEqual(fake.frames, [legacy_finish, "__sentinel__"])
            finally:
                RedisStreamEventBus._client = previous

        _run(_case())

    def test_late_publish_repairs_legacy_finish_before_terminal_contender(self):
        async def _case():
            legacy_finish = (
                'data: {"type": "finish", "finishReason": "stop"}\n\n'
            )
            late_event = NormalizedAgentEvent.create(
                "text-delta",
                {"delta": "must-not-publish"},
            )
            fake = _FakeRedis()
            fake.frames.append(legacy_finish)
            previous = RedisStreamEventBus._client
            RedisStreamEventBus._client = fake
            try:
                late_writer = RedisStreamEventBus(
                    "thread-legacy-event-repair",
                    "turn-legacy-event-repair",
                )
                terminal_contender = RedisStreamEventBus(
                    "thread-legacy-event-repair",
                    "turn-legacy-event-repair",
                )

                await late_writer.publish(late_event)
                await terminal_contender.publish_terminal(
                    NormalizedAgentEvent.create(
                        "finish",
                        {"finishReason": "error"},
                    )
                )

                self.assertTrue(fake.marker)
                self.assertEqual(fake.frames, [legacy_finish, "__sentinel__"])
                self.assertNotIn(late_event.to_wire_json(), fake.frames)
                self.assertEqual(len(fake.calls), 2)
                self.assertIn(
                    "'frame', ARGV[2], 'terminal', 'done'",
                    fake.calls[0][0],
                )
            finally:
                RedisStreamEventBus._client = previous

        _run(_case())

    def test_nested_finish_data_is_not_misclassified_as_terminal(self):
        async def _case():
            non_terminal = (
                'data: {"type":"message-final","data":{"type":"finish"}}\n\n'
            )
            terminal = NormalizedAgentEvent.create(
                "finish",
                {"finishReason": "stop"},
            )
            fake = _FakeRedis()
            fake.frames.append(non_terminal)
            previous = RedisStreamEventBus._client
            RedisStreamEventBus._client = fake
            try:
                contender = RedisStreamEventBus(
                    "thread-nested-data",
                    "turn-nested-data",
                )
                await contender.publish_terminal(terminal)
                self.assertEqual(
                    fake.frames,
                    [non_terminal, terminal.to_wire_json(), "__sentinel__"],
                )
            finally:
                RedisStreamEventBus._client = previous

        _run(_case())

    def test_shared_client_aclose_is_idempotent_and_resets_before_await(self):
        async def _case():
            class Client:
                def __init__(self) -> None:
                    self.calls = 0
                    self.entered = asyncio.Event()
                    self.release = asyncio.Event()

                async def aclose(self) -> None:
                    self.calls += 1
                    self.entered.set()
                    await self.release.wait()

            client = Client()
            previous = RedisStreamEventBus._client
            RedisStreamEventBus._client = client
            try:
                first = asyncio.create_task(RedisStreamEventBus.aclose())
                await asyncio.wait_for(client.entered.wait(), timeout=0.2)
                self.assertIsNone(RedisStreamEventBus._client)
                second = asyncio.create_task(RedisStreamEventBus.aclose())
                await asyncio.wait_for(second, timeout=0.2)
                client.release.set()
                await asyncio.wait_for(first, timeout=0.2)
                self.assertEqual(client.calls, 1)
            finally:
                RedisStreamEventBus._client = previous

        _run(_case())


if __name__ == "__main__":
    unittest.main()
