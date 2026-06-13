# [Input] Consume ClaudeAgentService callback factories and ToolEventPayload.
# [Output] Verify service-level SSE event mapping for Claude Agent turns.
# [Pos] service test node in backend/tests
# [Sync] 2026-06-13: cover tool_input_delta -> tool-input-delta SSE forwarding
#                    for built-in Write terminal previews.

"""Tests for ClaudeAgentService SSE event mapping."""
from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # backend/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tests._sdk_stubs  # noqa: F401 — stub claude_code_sdk before service import

from claude_agent.service import ClaudeAgentService, _TurnContext
from claude_agent.tool_confirmation_store import ToolConfirmationStore
from libs.claude_agent_kit.types import ToolEventPayload


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def _parse_sse(frame: str) -> dict:
    assert frame.startswith("data: ")
    return json.loads(frame[len("data: "):].strip())


class TestClaudeAgentServiceToolInputDelta(unittest.TestCase):
    def test_tool_input_delta_emits_start_then_delta_without_collecting(self):
        async def scenario():
            queue: asyncio.Queue[str] = asyncio.Queue()
            turn_ctx = _TurnContext(
                queue=queue,
                confirmation_store=ToolConfirmationStore(),
            )
            callback = ClaudeAgentService._make_tool_event_cb(queue, turn_ctx)

            await callback(
                ToolEventPayload(
                    type="tool_input_delta",
                    tool_name="Write",
                    tool_call_id="call-write",
                    output='{"file_path":"files/note.md"',
                )
            )

            first = _parse_sse(queue.get_nowait())
            second = _parse_sse(queue.get_nowait())

            return first, second, turn_ctx

        first, second, turn_ctx = _run(scenario())

        self.assertEqual(first["type"], "tool-input-start")
        self.assertEqual(first["toolCallId"], "call-write")
        self.assertEqual(first["toolName"], "Write")
        self.assertEqual(second["type"], "tool-input-delta")
        self.assertEqual(second["toolCallId"], "call-write")
        self.assertEqual(second["toolName"], "Write")
        self.assertEqual(second["delta"], '{"file_path":"files/note.md"')
        self.assertEqual(turn_ctx.collected_parts, [])


if __name__ == "__main__":
    unittest.main()
