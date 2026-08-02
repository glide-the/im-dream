"""Static contract tests for the AgentRunOptions / Deck Chat boundary.

deck-integration-delta §Acceptance: per-run agent options and Deck Chat
requests must never carry settings JSON, plugin paths, package installation
paths, or ``--plugin-dir`` values.  Plugin loading is a server-side workspace
bootstrap concern (pack → launch manifest → literal --plugin-dir argv).
"""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import tests._sdk_stubs  # noqa: F401 — must precede libs.claude_agent_kit imports

from libs.claude_agent_kit.types import AgentRunOptions
from claude_agent.service import ClaudeAgentRunRequest
from services.deck.chat_context import DeckChatContext
from routers.claude_agent import ClaudeAgentRequestBody


_BANNED_RUN_OPTION_FIELDS = {
    "settings_json",
    "claude_settings_json",
    "local_plugin_paths",
    "claude_plugin_paths",
    "enabled_plugins",
    "enabledPlugins",
    "plugin_package_spec",
    "plugin_installation_path",
    "plugin_artifact_path",
    "plugin_dir",
}

_BANNED_REQUEST_KEYS = {
    "settings_json",
    "claude_settings_json",
    "local_plugin_paths",
    "claude_plugin_paths",
    "plugin_dir",
    "plugin-dir",
    "pluginInstallationPath",
    "package_installation_path",
    "enabledPlugins",
    "plugins",
}


class AgentRunOptionsContractTests(unittest.TestCase):
    def test_run_options_have_no_settings_or_plugin_fields(self) -> None:
        field_names = set(AgentRunOptions.__dataclass_fields__)
        for banned in _BANNED_RUN_OPTION_FIELDS:
            self.assertNotIn(banned, field_names)

    def test_run_options_keep_only_true_run_parameters(self) -> None:
        field_names = set(AgentRunOptions.__dataclass_fields__)
        for expected in (
            "thread_id",
            "user_message",
            "resume",
            "model",
            "cwd",
            "max_turns",
            "tool_choice",
            "system_prompt",
        ):
            self.assertIn(expected, field_names)

    def test_service_request_has_no_plugin_fields(self) -> None:
        field_names = set(ClaudeAgentRunRequest.__dataclass_fields__)
        for banned in _BANNED_RUN_OPTION_FIELDS:
            self.assertNotIn(banned, field_names)

    def test_deck_chat_context_has_no_settings_or_plugin_path_fields(self) -> None:
        field_names = set(DeckChatContext.__dataclass_fields__)
        self.assertNotIn("claude_settings_json", field_names)
        self.assertNotIn("claude_plugin_paths", field_names)
        self.assertNotIn("settings_json", field_names)
        self.assertNotIn("local_plugin_paths", field_names)


class DeckChatRequestContractTests(unittest.TestCase):
    def _body(self, **extra):
        payload = {"thread_id": "t-1", "message": "hello", **extra}
        return ClaudeAgentRequestBody.model_validate(payload)

    def test_ordinary_request_still_validates(self) -> None:
        body = self._body(deck_id="deck-1", model="sonnet")
        self.assertEqual(body.get_thread_id(), "t-1")

    def test_request_rejects_plugin_and_settings_controls(self) -> None:
        for key in sorted(_BANNED_REQUEST_KEYS):
            with self.subTest(key=key):
                with self.assertRaises(Exception):
                    self._body(**{key: "anything"})

    def test_request_rejects_plugin_dir_cli_flag_value(self) -> None:
        with self.assertRaises(Exception):
            self._body(**{"plugin_dir": "./.ink/plugins/x@y@sha256-0"})


if __name__ == "__main__":
    unittest.main()
