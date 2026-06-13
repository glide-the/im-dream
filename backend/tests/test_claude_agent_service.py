# [Input] Consume ClaudeAgentService, ClaudeAgentRunRequest, AgentRunState.
# [Output] Verify service context assembly maps system_config into AgentRunOptions.
# [Pos] test node in backend/tests
# [Sync] 2026-06-13: cover assemble_context system_config lookup so module-level
#                    database alias is not shadowed by local imports.

"""Tests for ClaudeAgentService context assembly."""
from __future__ import annotations

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
from claude_agent.service import ClaudeAgentRunRequest, ClaudeAgentService
from claude_agent.thread_pool import AgentRunState


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


if __name__ == "__main__":
    unittest.main()
