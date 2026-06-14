# [Input] Consume ClaudeAgentService, ClaudeAgentRunRequest, AgentRunState,
#         service callback factories, and ToolEventPayload.
# [Output] Verify context assembly maps system_config into AgentRunOptions and
#          service-level SSE event mapping remains correct.
# [Pos] test node in backend/tests
# [Sync] 2026-06-14: combine system_config assembly coverage with tool_input_delta
#                    -> tool-input-delta SSE forwarding coverage.
# [Sync] 2026-06-14: cover Edit Session event publication after successful
#                    editor MCP write tool results.

"""Tests for ClaudeAgentService context assembly and SSE event mapping."""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]  # backend/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tests._sdk_stubs  # noqa: F401 — stub claude_code_sdk before service import

import claude_agent.service as service_module
from claude_agent.service import ClaudeAgentRunRequest, ClaudeAgentService, _TurnContext
from claude_agent.thread_pool import AgentRunState
from claude_agent.tool_confirmation_store import ToolConfirmationStore
from libs.claude_agent_kit.types import ToolEventPayload


class _FakeContextBuilder:
    async def build_system_prompt(self, user_id: str) -> str:
        return f"system-prompt:{user_id}"

    def build_user_message(self, message_parts: list | None, **kwargs: Any) -> list[dict[str, Any]]:
        return [{"type": "text", "text": "assembled"}]


class _FakeBus:
    async def publish(self, frame: str | None) -> None:
        pass


class TestClaudeAgentServiceAssembleContext(unittest.IsolatedAsyncioTestCase):
    async def test_system_config_is_loaded_before_resume_db_lookup(self):
        service = ClaudeAgentService(context_builder=_FakeContextBuilder())
        state = AgentRunState(session_id="thread_service_config")
        request = ClaudeAgentRunRequest(
            user_id="7",
            thread_id="thread_service_config",
            message_parts=[{"type": "text", "text": "hello"}],
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_path = Path(tmp_dir) / "thread_service_config"
            with (
                unittest.mock.patch.object(
                    service_module._db,
                    "get_system_config",
                    return_value={
                        "im_full_access_enabled": True,
                        "workspace_enabled": False,
                        "env_vars": {
                            "ANTHROPIC_AUTH_TOKEN": "user-token",
                            "EMPTY": None,
                            "  CUSTOM_KEY  ": "custom-value",
                        },
                    },
                ) as get_system_config,
                unittest.mock.patch.object(
                    service_module._db,
                    "get_chat_thread",
                    return_value=None,
                ) as get_chat_thread,
                unittest.mock.patch.object(
                    service_module,
                    "get_or_create_workspace",
                    return_value=workspace_path,
                ) as get_or_create_workspace,
            ):
                execution = await service.assemble_context(
                    request,
                    state=state,
                    bus=_FakeBus(),
                    runner=unittest.mock.Mock(),
                )

        get_system_config.assert_called_once_with(7)
        get_chat_thread.assert_called_once_with("thread_service_config", 7)
        get_or_create_workspace.assert_called_once_with(
            "thread_service_config",
            sandbox_enabled=False,
        )

        self.assertTrue(execution.run_options.im_full_access_enabled)
        self.assertEqual(str(workspace_path), execution.run_options.cwd)
        self.assertEqual(
            execution.run_options.mcp_env,
            {
                "ANTHROPIC_AUTH_TOKEN": "user-token",
                "CUSTOM_KEY": "custom-value",
                "INK_AGENT_USER_ID": "7",
            },
        )
        self.assertEqual(
            execution.run_options.user_sdk_env["ANTHROPIC_AUTH_TOKEN"],
            "user-token",
        )


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


class TestClaudeAgentServiceEditorWriteEvents(unittest.TestCase):
    def test_editor_write_tool_result_publishes_session_event(self):
        async def scenario():
            queue: asyncio.Queue[str] = asyncio.Queue()
            turn_ctx = _TurnContext(
                queue=queue,
                confirmation_store=ToolConfirmationStore(),
            )
            state = AgentRunState(session_id="thread-editor-write")
            state.with_editor_state({"id": "session-editor-write"}, 7)
            callback = ClaudeAgentService._make_tool_event_cb(queue, turn_ctx, state)
            subscription = await service_module.session_event_bus.subscribe("7")

            try:
                with unittest.mock.patch.object(
                    service_module._db,
                    "get_session",
                    return_value={
                        "id": "session-editor-write",
                        "editor_state": {
                            "id": "session-editor-write",
                            "cells": [{"id": "cell-1", "type": "text", "content": "new"}],
                        },
                    },
                ) as get_session:
                    await callback(
                        ToolEventPayload(
                            type="tool_result",
                            tool_name="mcp__editor__write_segment",
                            tool_call_id="tool-call-1",
                            output={"ok": True, "cellId": "cell-1"},
                            is_error=False,
                        )
                    )

                event = await asyncio.wait_for(subscription.get(), timeout=1.0)
            finally:
                await service_module.session_event_bus.unsubscribe("7", subscription)

            self.assertEqual(get_session.call_args.args, (7, "session-editor-write"))
            self.assertEqual(event.type, "session_updated")
            self.assertEqual(event.session_id, "session-editor-write")
            self.assertEqual(event.source, "agent")
            self.assertEqual(event.tool_call_id, "tool-call-1")
            self.assertEqual(event.tool_name, "mcp__editor__write_segment")
            self.assertEqual(state.editor_state["cells"][0]["content"], "new")

        _run(scenario())


if __name__ == "__main__":
    unittest.main()
