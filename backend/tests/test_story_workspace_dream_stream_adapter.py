"""Contract tests for the protocol-isolated Dream stream adapter."""
from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from claude_agent.stream_events import NormalizedAgentEvent  # noqa: E402
from services.story_workspace.dream_stream_adapter import (  # noqa: E402
    DreamStreamAdapter,
    iter_dream_run_events,
    iter_dream_subscription_events,
)


def _adapter() -> DreamStreamAdapter:
    return DreamStreamAdapter(
        turn_id="turn-1",
        public_text_projection=lambda value: (value, False, False),
        public_text_is_sensitive=lambda _value: False,
        incremental_text_split=lambda value: (value, ""),
        redaction_text="[redacted]",
        max_text_length=100_000,
        max_pending_length=100_000,
    )


def _payload(frame: str) -> dict:
    data_line = next(line for line in frame.splitlines() if line.startswith("data: "))
    return json.loads(data_line.removeprefix("data: "))


class TestDreamStreamAdapter(unittest.TestCase):
    def test_dream_has_its_own_event_contract_and_preserves_all_deltas(self) -> None:
        adapter = _adapter()
        frames: list[str] = []

        for ordinal in range(334):
            adaptation = adapter.adapt(
                NormalizedAgentEvent.create(
                    "text-delta",
                    {"id": "chat-private", "delta": f"梦境-{ordinal}🙂\n"},
                ),
                ordinal=ordinal,
                cursor_consumed=lambda _ordinal, _subevent=None: False,
            )
            frames.extend(adaptation.frames)

        self.assertEqual(len(frames), 334)
        self.assertTrue(all("event: assistant_text_delta" in frame for frame in frames))
        self.assertTrue(all('"type":"text-delta"' not in frame for frame in frames))
        self.assertEqual(
            [_payload(frame)["delta"] for frame in frames],
            [f"梦境-{ordinal}🙂\n" for ordinal in range(334)],
        )

    def test_message_final_flushes_pending_text_and_is_the_only_terminal(self) -> None:
        adapter = DreamStreamAdapter(
            turn_id="turn-1",
            public_text_projection=lambda value: (value, False, False),
            public_text_is_sensitive=lambda _value: False,
            incremental_text_split=lambda value: ("", value),
            redaction_text="[redacted]",
            max_text_length=100,
            max_pending_length=100,
        )
        adapter.adapt(
            NormalizedAgentEvent.create("text-delta", {"delta": "最后一段"}),
            ordinal=0,
            cursor_consumed=lambda _ordinal, _subevent=None: False,
        )

        final = adapter.adapt(
            NormalizedAgentEvent.create("message-final"),
            ordinal=1,
            cursor_consumed=lambda _ordinal, _subevent=None: False,
        )

        self.assertTrue(final.handled)
        self.assertTrue(final.terminal)
        self.assertEqual(len(final.frames), 2)
        self.assertIn("event: assistant_text_delta", final.frames[0])
        self.assertIn("event: assistant_message_committed", final.frames[1])

    def test_unknown_chat_event_is_not_exposed_by_dream(self) -> None:
        result = _adapter().adapt(
            NormalizedAgentEvent.create("reasoning-delta", {"delta": "private"}),
            ordinal=0,
            cursor_consumed=lambda _ordinal, _subevent=None: False,
        )

        self.assertFalse(result.handled)
        self.assertEqual(result.frames, ())

    def test_error_is_one_safe_terminal_without_raw_details(self) -> None:
        result = _adapter().adapt(
            NormalizedAgentEvent.create(
                "error",
                {"errorText": "/private/path provider-secret stack trace"},
            ),
            ordinal=4,
            cursor_consumed=lambda _ordinal, _subevent=None: False,
        )

        self.assertTrue(result.handled)
        self.assertTrue(result.terminal)
        self.assertEqual(len(result.frames), 1)
        self.assertIn("event: agent_turn_failed", result.frames[0])
        self.assertEqual(_payload(result.frames[0]), {
            "turnId": "turn-1",
            "code": "DREAM_AGENT_TURN_FAILED",
        })
        self.assertNotIn("provider-secret", result.frames[0])
        self.assertNotIn("/private/path", result.frames[0])

    def test_finish_without_message_final_projects_cancelled(self) -> None:
        result = _adapter().adapt(
            NormalizedAgentEvent.create("finish", {"finishReason": "stop"}),
            ordinal=5,
            cursor_consumed=lambda _ordinal, _subevent=None: False,
        )

        self.assertTrue(result.terminal)
        self.assertEqual(len(result.frames), 1)
        self.assertIn("event: agent_turn_cancelled", result.frames[0])
        self.assertEqual(_payload(result.frames[0]), {"turnId": "turn-1"})

    def test_finish_error_without_error_frame_still_projects_failed(self) -> None:
        result = _adapter().adapt(
            NormalizedAgentEvent.create("finish", {"finishReason": "error"}),
            ordinal=6,
            cursor_consumed=lambda _ordinal, _subevent=None: False,
        )

        self.assertTrue(result.terminal)
        self.assertEqual(len(result.frames), 1)
        self.assertIn("event: agent_turn_failed", result.frames[0])

    def test_dream_execution_prefers_normalized_api_and_never_calls_chat(self) -> None:
        class Factory:
            async def run_events(self, _request):
                yield NormalizedAgentEvent.create("message-final")
                yield NormalizedAgentEvent.create("finish", {"finishReason": "stop"})

            def run_streaming(self, _request):
                raise AssertionError("Dream must not consume Chat SSE")

        async def collect():
            return [event async for event in iter_dream_run_events(Factory(), object())]

        events = asyncio.run(collect())
        self.assertEqual([event.type for event in events], ["message-final", "finish"])

    def test_dream_subscription_prefers_normalized_api_and_never_calls_chat(self) -> None:
        class Factory:
            async def subscribe_expected_events(self, thread_id, turn_id):
                self.args = (thread_id, turn_id)
                yield NormalizedAgentEvent.create("text-delta", {"delta": "ok"})

            def subscribe_expected_stream(self, _thread_id, _turn_id):
                raise AssertionError("Dream must not consume Chat SSE")

        factory = Factory()

        async def collect():
            return [
                event
                async for event in iter_dream_subscription_events(
                    factory,
                    thread_id="thread-1",
                    expected_turn_id="turn-1",
                )
            ]

        events = asyncio.run(collect())
        self.assertEqual(factory.args, ("thread-1", "turn-1"))
        self.assertEqual(events[0].data["delta"], "ok")


if __name__ == "__main__":
    unittest.main()
