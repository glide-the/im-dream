"""Opt-in live Redis contract for the shared Claude Agent EventBus.

Set ``INK_AGENT_REDIS_RUNTIME_URL`` to an isolated test Redis endpoint. The
suite deletes only its random per-test stream and terminal keys; it never uses
FLUSHDB and is skipped during ordinary unit runs.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import sys
import textwrap
import unittest
import uuid


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from claude_agent.event_bus_redis import RedisStreamEventBus
from claude_agent.stream_events import NormalizedAgentEvent
import claude_agent.event_bus_redis as redis_bus_module


RUNTIME_URL = os.getenv("INK_AGENT_REDIS_RUNTIME_URL", "").strip()


@unittest.skipUnless(RUNTIME_URL, "requires INK_AGENT_REDIS_RUNTIME_URL")
class RedisStreamEventBusRuntimeTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        await RedisStreamEventBus.aclose()
        redis_bus_module._REDIS_URL = RUNTIME_URL
        import redis.asyncio as redis

        self.redis = redis.from_url(RUNTIME_URL, decode_responses=True)
        self.assertTrue(await self.redis.ping())
        await RedisStreamEventBus.validate_connection()
        nonce = uuid.uuid4().hex
        self.session_id = f"runtime-{nonce}"
        self.turn_id = f"turn-{nonce}"
        self.stream_key = f"ink:sse:{self.session_id}:{self.turn_id}"
        self.terminal_key = f"{{{self.stream_key}}}:terminal"

    async def asyncTearDown(self) -> None:
        await RedisStreamEventBus.aclose()
        await self.redis.delete(self.stream_key, self.terminal_key)
        await self.redis.aclose()

    async def _run_isolated_writer(self, body: str) -> None:
        script = textwrap.dedent(
            f"""
            import asyncio
            from claude_agent.event_bus_redis import RedisStreamEventBus
            from claude_agent.stream_events import NormalizedAgentEvent

            async def main():
                bus = RedisStreamEventBus({self.session_id!r}, {self.turn_id!r})
                {body}
                await RedisStreamEventBus.aclose()

            asyncio.run(main())
            """
        )
        env = os.environ.copy()
        env["PYTHONPATH"] = str(BACKEND_ROOT)
        env["INK_AGENT_REDIS_URL"] = RUNTIME_URL
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            script,
            cwd=BACKEND_ROOT,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10)
            self.assertEqual(
                process.returncode,
                0,
                f"writer failed\nstdout={stdout.decode()}\nstderr={stderr.decode()}",
            )
        finally:
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=2)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()

    async def test_cross_process_replay_and_exactly_one_terminal(self) -> None:
        await self._run_isolated_writer(
            "await bus.publish(NormalizedAgentEvent.create('text-delta', "
            "{'delta': '你好\\nRedis'}))"
        )
        await self._run_isolated_writer(
            "await bus.publish_terminal(NormalizedAgentEvent.create('finish', "
            "{'finishReason': 'stop'}))"
        )
        await self._run_isolated_writer(
            "await bus.publish(NormalizedAgentEvent.create('text-delta', "
            "{'delta': 'late'})); "
            "await bus.publish_terminal(NormalizedAgentEvent.create('finish', "
            "{'finishReason': 'error'}))"
        )

        reader = RedisStreamEventBus(self.session_id, self.turn_id)
        token = await reader.subscribe()
        replay = [event async for event in reader.read(token)]
        self.assertEqual([event.type for event in replay], ["text-delta", "finish"])
        self.assertEqual(replay[0].data["delta"], "你好\nRedis")
        self.assertEqual(replay[1].data["finishReason"], "stop")

        entries = await self.redis.xrange(self.stream_key)
        frames = [fields["frame"] for _, fields in entries]
        self.assertEqual(frames.count("__sentinel__"), 1)
        self.assertEqual(
            sum(
                NormalizedAgentEvent.from_wire_json(frame).type == "finish"
                for frame in frames
                if frame != "__sentinel__"
            ),
            1,
        )
        self.assertEqual(await self.redis.get(self.terminal_key), "done")

    async def test_live_xread_supports_resp2_and_resp3_and_marks_done(self) -> None:
        separator = "&" if "?" in RUNTIME_URL else "?"
        for protocol_url in (RUNTIME_URL, f"{RUNTIME_URL}{separator}protocol=3"):
            with self.subTest(url=protocol_url):
                await RedisStreamEventBus.aclose()
                redis_bus_module._REDIS_URL = protocol_url
                nonce = uuid.uuid4().hex
                session_id = f"live-{nonce}"
                turn_id = f"turn-{nonce}"
                stream_key = f"ink:sse:{session_id}:{turn_id}"
                terminal_key = f"{{{stream_key}}}:terminal"
                producer = RedisStreamEventBus(session_id, turn_id)
                reader = RedisStreamEventBus(session_id, turn_id)
                token = await reader.subscribe()
                stream = reader.read(token)
                try:
                    await producer.publish(
                        NormalizedAgentEvent.create("text-delta", {"delta": "first"})
                    )
                    first = await asyncio.wait_for(anext(stream), timeout=2)
                    self.assertEqual(first.data["delta"], "first")
                    pending = asyncio.create_task(anext(stream))
                    await asyncio.sleep(0)
                    await producer.publish(
                        NormalizedAgentEvent.create("text-delta", {"delta": "live"})
                    )
                    live = await asyncio.wait_for(pending, timeout=2)
                    self.assertEqual(live.data["delta"], "live")
                    await producer.publish_terminal(
                        NormalizedAgentEvent.create(
                            "finish",
                            {"finishReason": "stop"},
                        )
                    )
                    terminal = await asyncio.wait_for(anext(stream), timeout=2)
                    self.assertEqual(terminal.type, "finish")
                    with self.assertRaises(StopAsyncIteration):
                        await asyncio.wait_for(anext(stream), timeout=2)
                    self.assertTrue(reader.is_done)
                finally:
                    await stream.aclose()
                    await RedisStreamEventBus.aclose()
                    await self.redis.delete(stream_key, terminal_key)

    async def test_legacy_finish_without_sentinel_terminates_reader(self) -> None:
        terminal = NormalizedAgentEvent.create(
            "finish",
            {"finishReason": "stop"},
        )
        await self.redis.xadd(self.stream_key, {"frame": terminal.to_wire_json()})
        await self.redis.expire(self.stream_key, 60)
        reader = RedisStreamEventBus(self.session_id, self.turn_id)
        token = await reader.subscribe()
        events = [event async for event in reader.read(token)]
        self.assertEqual(events, [terminal])
        self.assertTrue(reader.is_done)

    async def test_concurrent_terminal_writers_have_one_finish_and_positive_ttl(
        self,
    ) -> None:
        first = RedisStreamEventBus(self.session_id, self.turn_id)
        second = RedisStreamEventBus(self.session_id, self.turn_id)
        await asyncio.gather(
            first.publish_terminal(
                NormalizedAgentEvent.create("finish", {"finishReason": "stop"})
            ),
            second.publish_terminal(
                NormalizedAgentEvent.create("finish", {"finishReason": "error"})
            ),
        )

        reader = RedisStreamEventBus(self.session_id, self.turn_id)
        token = await reader.subscribe()
        events = [event async for event in reader.read(token)]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].type, "finish")
        entries = await self.redis.xrange(self.stream_key)
        frames = [fields["frame"] for _, fields in entries]
        self.assertEqual(frames.count("__sentinel__"), 1)
        self.assertGreater(await self.redis.ttl(self.stream_key), 0)
        self.assertGreater(await self.redis.ttl(self.terminal_key), 0)


if __name__ == "__main__":
    unittest.main()
