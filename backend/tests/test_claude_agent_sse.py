"""Regression tests for Claude Agent SSE framing and anti-buffering headers."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from claude_agent.sse import (  # noqa: E402
    SSE_RESPONSE_HEADERS,
    encode_json_sse,
    streaming_sse_response,
)
from claude_agent.chat_stream_adapter import ChatStreamAdapter  # noqa: E402
from claude_agent.stream_events import NormalizedAgentEvent  # noqa: E402


class TestClaudeAgentSseEncoding(unittest.TestCase):
    def test_chat_adapter_preserves_every_normalized_text_delta(self) -> None:
        events = [
            NormalizedAgentEvent.create(
                "text-delta",
                {"id": "text-1", "delta": f"片段-{index}🙂\n"},
            )
            for index in range(334)
        ]

        frames = [ChatStreamAdapter.encode(event) for event in events]
        payloads = [json.loads(frame.removeprefix("data: ").strip()) for frame in frames]

        self.assertEqual(len(frames), 334)
        self.assertEqual(
            [payload["delta"] for payload in payloads],
            [event.data["delta"] for event in events],
        )

    def test_chat_adapter_uses_a_comment_for_internal_keepalive(self) -> None:
        self.assertEqual(
            ChatStreamAdapter.encode(NormalizedAgentEvent.keepalive()),
            ": keepalive\n\n",
        )

    def test_normalized_event_rejects_non_json_data_at_producer_boundary(self) -> None:
        with self.assertRaises(TypeError):
            NormalizedAgentEvent.create("text-delta", {"delta": object()})

    def test_unicode_quotes_newlines_and_special_characters_round_trip(self) -> None:
        frame = encode_json_sse(
            "text-delta",
            {
                "id": "text-1",
                "delta": "中文🙂\nquoted: \"ok\"\\path",
            },
        )

        self.assertTrue(frame.startswith("data: "))
        self.assertTrue(frame.endswith("\n\n"))
        self.assertEqual(frame.count("\n"), 2)
        payload = json.loads(frame.removeprefix("data: ").strip())
        self.assertEqual(payload["type"], "text-delta")
        self.assertEqual(payload["delta"], "中文🙂\nquoted: \"ok\"\\path")

    def test_each_call_encodes_exactly_one_complete_frame(self) -> None:
        first = encode_json_sse("text-delta", {"id": "1", "delta": "a"})
        second = encode_json_sse("finish", {"finishReason": "stop"})

        self.assertEqual((first + second).count("\n\n"), 2)
        self.assertEqual(json.loads(first[6:].strip())["type"], "text-delta")
        self.assertEqual(json.loads(second[6:].strip())["type"], "finish")


class TestClaudeAgentSseResponse(unittest.TestCase):
    def test_response_has_utf8_streaming_and_anti_buffering_headers(self) -> None:
        async def content():
            yield encode_json_sse("finish", {"finishReason": "stop"})

        response = streaming_sse_response(content())

        self.assertEqual(
            response.headers["content-type"],
            "text/event-stream; charset=utf-8",
        )
        for name, value in SSE_RESPONSE_HEADERS.items():
            self.assertEqual(response.headers[name], value)
        self.assertNotIn("content-length", response.headers)
        self.assertNotIn("content-encoding", response.headers)


if __name__ == "__main__":
    unittest.main()
