# [Input] Consume InMemoryEventBus, BusProxyQueue, create_event_bus from event_bus.py.
# [Output] Verify publish/subscribe replay, multi-consumer fan-out, sentinel semantics.
# [Pos] test node in backend/tests
# [Sync] 2026-06-09: memory-mode EventBus unit tests.

from __future__ import annotations

import asyncio
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util
from claude_agent.stream_events import NormalizedAgentEvent

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
    async for event in bus.read(token):
        events.append(event)
        if len(events) >= count:
            break
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

    def test_create_event_bus_defaults_to_memory(self):
        old = os.environ.pop("INK_AGENT_EVENT_BUS_BACKEND", None)
        try:
            bus = create_event_bus("thread-1", "turn-1")
            self.assertIsInstance(bus, InMemoryEventBus)
        finally:
            if old is not None:
                os.environ["INK_AGENT_EVENT_BUS_BACKEND"] = old


if __name__ == "__main__":
    unittest.main()
