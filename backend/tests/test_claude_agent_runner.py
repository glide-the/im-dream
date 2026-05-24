# [Input] Consume ClaudeAgentRunner, AgentRunOptions, AgentStreamingCallbacks,
#         AgentRunResult from backend/libs/claude_agent_kit/runner.py and types.py.
# [Output] Verify streaming callbacks, session_id extraction, error handling,
#          on_text_done, on_tool_event, tool confirmation flow, env aliases.
# [Pos] test node in backend/tests
# [Sync] 2026-05-22: migrated from Pawkeyland scripts/test_claude_agent_runner.py.
#                    Removed: necklace/memory/touch_animation MCP tests,
#                    PAWKEYLAND_AGENT_* env mapping tests, thinking proxy tests.
#                    Adapted: module import path backend/libs/claude_agent_kit/runner.py.
# [Sync] 2026-05-24: cover INK_AGENT_MEM0_* aliases for memory MCP/hook env.
# [Sync] 2026-05-24: cover direct ANTHROPIC_AUTH_TOKEN SDK auth diagnostics.

"""Tests for ClaudeAgentRunner (Ink & Memory).

Exercises the major callback paths without calling the real Claude subprocess.

Key differences from Pawkeyland:
- ClaudeAgentRunner() — original Pawkeyland API (no session_id in constructor).
- Text arrives via AssistantMessage content blocks, not StreamEvent text_delta.
- Tool confirmation is triggered by tool_use blocks (not PreToolUse hooks).
- No MCP subprocess setup; no pet/persona/necklace/memory-specific paths.
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Optional
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]  # backend/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Minimal SDK stubs so tests run without claude_code_sdk installed.
# These must be injected before importing libs.claude_agent_kit.server.agent_runner so that
# isinstance() checks in the runner resolve to the same stub classes.
# ---------------------------------------------------------------------------

import types as _types


def _make_sdk_stubs() -> None:
    """Inject lightweight stubs for claude_code_sdk into sys.modules."""

    sdk = _types.ModuleType("claude_code_sdk")
    sdk_types = _types.ModuleType("claude_code_sdk.types")

    class AssistantMessage:
        def __init__(self, content=None):
            self.content = content or []

    class UserMessage:
        def __init__(self, content=None):
            self.content = content or []

    class ResultMessage:
        def __init__(self, subtype="success", session_id=None, usage=None):
            self.subtype = subtype
            self.session_id = session_id
            self.usage = usage or {}

    class StreamEvent:
        def __init__(self, event=None, session_id=None):
            self.event = event or {}
            self.session_id = session_id

    class ClaudeCodeOptions:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    # Additional stub classes required by the original Pawkeyland agent_runner.py
    class SystemMessage:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class HookContext:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class HookJSONOutput:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class HookMatcher:
        def __init__(self, matcher=None, hooks=None, **kwargs):
            self.matcher = matcher
            self.hooks = hooks or []
            for k, v in kwargs.items():
                setattr(self, k, v)

    class McpServerConfig:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class McpStdioServerConfig:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    for _cls in [
        AssistantMessage,
        UserMessage,
        ResultMessage,
        StreamEvent,
        ClaudeCodeOptions,
        SystemMessage,
        HookContext,
        HookJSONOutput,
        HookMatcher,
        McpServerConfig,
        McpStdioServerConfig,
    ]:
        setattr(sdk_types, _cls.__name__, _cls)

    async def _noop_query(*args, **kwargs):
        return
        yield  # make it an async generator  # noqa: unreachable

    sdk.query = _noop_query
    sdk.ClaudeSDKClient = object
    sdk.types = sdk_types
    sys.modules["claude_code_sdk"] = sdk
    sys.modules["claude_code_sdk.types"] = sdk_types


_make_sdk_stubs()

# ---------------------------------------------------------------------------
# Now import the modules under test (after stubs are in place)
# ---------------------------------------------------------------------------

import libs.claude_agent_kit.server.agent_runner as agent_runner_module  # noqa: E402
import libs.claude_agent_kit.server.sdk_env as sdk_env_module  # noqa: E402
from libs.claude_agent_kit.server.agent_runner import ClaudeAgentRunner  # noqa: E402
from libs.claude_agent_kit.types import (  # noqa: E402
    AgentRunOptions,
    AgentStreamingCallbacks,
    AgentRunResult,
    ToolEventPayload,
)

# ---------------------------------------------------------------------------
# Message factory helpers — wrap stub classes for test convenience.
# Grabbed after runner import so the classes match the runner's isinstance refs.
# ---------------------------------------------------------------------------

_SDK_ASSISTANT = sys.modules["claude_code_sdk.types"].AssistantMessage
_SDK_OPTIONS = sys.modules["claude_code_sdk.types"].ClaudeCodeOptions
_SDK_RESULT = sys.modules["claude_code_sdk.types"].ResultMessage
_SDK_STREAM_EVENT = sys.modules["claude_code_sdk.types"].StreamEvent
_SDK_USER = sys.modules["claude_code_sdk.types"].UserMessage


def AssistantMessage(content=None):
    return _SDK_ASSISTANT(content or [])


def ResultMessage(session_id=None, subtype="success", usage=None):
    return _SDK_RESULT(subtype=subtype, session_id=session_id, usage=usage)


def StreamEvent(event=None, session_id=None):
    return _SDK_STREAM_EVENT(event=event or {}, session_id=session_id)


def UserMessage(content=None):
    return _SDK_USER(content or [])


def _text_block(text: str):
    """Return a minimal text content block stub (for AssistantMessage)."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _text_delta_event(text: str, index: int = 0):
    """Return a StreamEvent carrying a content_block_delta text_delta.

    Original agent_runner.py dispatches on_text_delta from StreamEvent
    content_block_delta events (include_partial_messages=True by default).
    """
    return StreamEvent(event={
        "type": "content_block_delta",
        "index": index,
        "delta": {"type": "text_delta", "text": text},
    })


def _tool_use_block(tool_name: str, tool_input: dict, tool_id: str = "tu-1"):
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.input = tool_input
    block.id = tool_id
    return block


def _make_fake_query(messages: list):
    """Return an async generator function that yields the given messages."""
    async def _fake(*args, **kwargs):
        for msg in messages:
            yield msg
    return _fake


# ---------------------------------------------------------------------------
# Mock SDK client — injected into ClaudeAgentRunner(sdk_client=...) so no
# real subprocess is launched during tests.
# ---------------------------------------------------------------------------

_FAKE_WORKSPACE = Path("/tmp/ink-agent-tests")


class _MockSDKClient:
    """Minimal IClaudeAgentSDKClient implementation for testing.

    Call ``set_messages()`` before each ``run_streaming`` to configure
    what the fake query stream should yield.
    """

    def __init__(self):
        self._messages: list = []

    def set_messages(self, messages: list) -> None:
        self._messages = list(messages)

    async def query_stream(self, prompt, options=None):
        for msg in self._messages:
            yield msg

    async def load_messages(self, session_id=None):
        return {"messages": []}


# ---------------------------------------------------------------------------
# Base test class
# ---------------------------------------------------------------------------


class _RunnerBase(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self._mock_client = _MockSDKClient()

    def make_runner(self, session_id: str = "test-session") -> ClaudeAgentRunner:
        return ClaudeAgentRunner(sdk_client=self._mock_client)

    def set_query(self, messages: list) -> None:
        """Configure the mock SDK client to yield the given messages."""
        self._mock_client.set_messages(messages)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestClaudeAgentRunnerBasicText(_RunnerBase):
    """Basic text streaming — text arrives via StreamEvent content_block_delta.

    Original runner uses include_partial_messages=True by default, so text is
    dispatched from StreamEvent text_delta events, not AssistantMessage blocks.
    """

    async def test_on_text_delta_called_and_result_contains_full_text(self):
        self.set_query([
            _text_delta_event("Hello"),
            _text_delta_event(" World"),
        ])
        runner = self.make_runner()
        received: list[str] = []

        result = await runner.run_streaming(
            opts=AgentRunOptions(
                thread_id="test-session-001",
                user_message="请用 Python 写一个 Hello World",
                max_turns=10,
                tool_choice="none",
            ),
            callbacks=AgentStreamingCallbacks(
                on_text_delta=lambda d: received.append(d),
            ),
        )

        self.assertTrue(result.success)
        self.assertEqual(result.full_text, "Hello World")
        self.assertEqual(received, ["Hello", " World"])


class TestClaudeAgentRunnerOnTextDone(_RunnerBase):
    """on_text_done receives the concatenated full text after streaming."""

    async def test_on_text_done_receives_full_text(self):
        self.set_query([
            _text_delta_event("foo"),
            _text_delta_event("bar"),
        ])
        runner = self.make_runner()
        done_texts: list[str] = []

        result = await runner.run_streaming(
            opts=AgentRunOptions(
                thread_id="td-001",
                user_message="hi",
                tool_choice="none",
            ),
            callbacks=AgentStreamingCallbacks(
                on_text_delta=lambda d: None,
                on_text_done=lambda t: done_texts.append(t),
            ),
        )

        self.assertEqual(done_texts, ["foobar"])
        self.assertEqual(result.full_text, "foobar")


class TestClaudeAgentRunnerSessionId(_RunnerBase):
    """session_id is extracted from ResultMessage."""

    async def test_session_id_from_result_message(self):
        self.set_query([ResultMessage(session_id="sess-xyz")])
        runner = self.make_runner()

        result = await runner.run_streaming(
            opts=AgentRunOptions(
                thread_id="any",
                user_message="ping",
                tool_choice="none",
            ),
            callbacks=AgentStreamingCallbacks(on_text_delta=lambda d: None),
        )

        self.assertEqual(result.session_id, "sess-xyz")


class TestClaudeAgentRunnerOnToolEvent(_RunnerBase):
    """on_tool_event is fired for tool_use blocks in AssistantMessage."""

    async def test_tool_use_fires_on_tool_event(self):
        self.set_query([
            AssistantMessage([
                _tool_use_block("Bash", {"command": "ls"}, tool_id="tu-42"),
            ]),
        ])
        runner = self.make_runner()
        tool_events: list[ToolEventPayload] = []

        result = await runner.run_streaming(
            opts=AgentRunOptions(
                thread_id="te-001",
                user_message="list files",
                tool_choice="auto",
            ),
            callbacks=AgentStreamingCallbacks(
                on_text_delta=lambda d: None,
                on_tool_event=lambda e: tool_events.append(e),
            ),
        )

        self.assertTrue(result.success)
        tool_use_events = [e for e in tool_events if e.type == "tool_use"]
        self.assertEqual(len(tool_use_events), 1)
        ev = tool_use_events[0]
        self.assertEqual(ev.tool_name, "Bash")
        self.assertEqual(ev.tool_call_id, "tu-42")
        self.assertEqual(ev.input, {"command": "ls"})

    async def test_multiple_tool_use_blocks_all_fire_events(self):
        """Multiple tool_use blocks in one AssistantMessage each fire on_tool_event."""
        self.set_query([
            AssistantMessage([
                _tool_use_block("Bash", {"command": "ls"}, tool_id="tu-1"),
                _tool_use_block("Read", {"file_path": "/tmp/x.txt"}, tool_id="tu-2"),
            ]),
        ])
        runner = self.make_runner()
        tool_events: list[ToolEventPayload] = []

        result = await runner.run_streaming(
            opts=AgentRunOptions(
                thread_id="te-multi-001",
                user_message="list and read",
                tool_choice="auto",
            ),
            callbacks=AgentStreamingCallbacks(
                on_text_delta=lambda d: None,
                on_tool_event=lambda e: tool_events.append(e),
            ),
        )

        self.assertTrue(result.success)
        tool_use_events = [e for e in tool_events if e.type == "tool_use"]
        self.assertEqual(len(tool_use_events), 2)
        names = {e.tool_name for e in tool_use_events}
        self.assertEqual(names, {"Bash", "Read"})


class TestClaudeAgentRunnerStreamEvent(_RunnerBase):
    """StreamEvent handling — original runner dispatches text from StreamEvents.

    Original Pawkeyland agent_runner.py uses include_partial_messages=True by
    default, so text_delta StreamEvents are the primary text dispatch path.
    """

    async def test_stream_event_text_delta_is_dispatched(self):
        """Runner dispatches on_text_delta from StreamEvent content_block_delta.

        Original runner with include_partial_messages=True dispatches text
        via StreamEvent text_delta, not via AssistantMessage text blocks.
        """
        self.set_query([
            StreamEvent(
                event={
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": "streamed text"},
                },
                session_id="stream-sess",
            ),
        ])
        runner = self.make_runner()
        received: list[str] = []

        result = await runner.run_streaming(
            opts=AgentRunOptions(
                thread_id="se-001",
                user_message="hello",
                tool_choice="none",
            ),
            callbacks=AgentStreamingCallbacks(
                on_text_delta=lambda d: received.append(d),
            ),
        )

        self.assertTrue(result.success)
        self.assertEqual(received, ["streamed text"])

    async def test_stream_event_thinking_delta_fires_tool_event(self):
        """thinking_delta StreamEvents are dispatched as thinking_delta tool events.

        Original runner accumulates thinking blocks by index and dispatches
        them as ToolEventPayload(type='thinking_delta').
        """
        self.set_query([
            StreamEvent(event={
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "thinking", "thinking": "", "signature": ""},
            }),
            StreamEvent(event={
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "thinking_delta", "thinking": "The"},
            }),
            StreamEvent(event={
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "thinking_delta", "thinking": " user"},
            }),
            StreamEvent(event={
                "type": "content_block_delta",
                "index": 0,
                "delta": {
                    "type": "signature_delta",
                    "signature": "3f1a1344-dece-4409-8d44-097891e0cd01",
                },
            }),
            StreamEvent(event={"type": "content_block_stop", "index": 0}),
        ])
        runner = self.make_runner()
        tool_events: list[ToolEventPayload] = []

        result = await runner.run_streaming(
            opts=AgentRunOptions(
                thread_id="se-thinking-001",
                user_message="hello",
                tool_choice="none",
            ),
            callbacks=AgentStreamingCallbacks(
                on_text_delta=lambda d: None,
                on_tool_event=lambda e: tool_events.append(e),
            ),
        )

        self.assertTrue(result.success)
        # thinking_delta StreamEvents are dispatched as tool events by the original runner
        thinking_events = [e for e in tool_events if e.type == "thinking_delta"]
        self.assertGreater(len(thinking_events), 0, "Expected thinking_delta tool events")


def _runner_with_error_query(exc):
    """Return a ClaudeAgentRunner whose SDK client raises *exc* on query_stream."""

    class _ErrorClient(_MockSDKClient):
        async def query_stream(self, prompt, options=None):
            raise exc
            yield  # pragma: no cover

    return ClaudeAgentRunner(sdk_client=_ErrorClient())


def _runner_with_exception_group(exceptions):
    """Return a runner that raises a BaseExceptionGroup from query_stream."""

    class _GroupClient(_MockSDKClient):
        async def query_stream(self, prompt, options=None):
            raise BaseExceptionGroup("test group", list(exceptions))
            yield  # pragma: no cover

    return ClaudeAgentRunner(sdk_client=_GroupClient())


class TestClaudeAgentRunnerErrorHandling(_RunnerBase):
    """Errors from the SDK are caught and reported via on_error."""

    async def test_sdk_error_sets_success_false(self):
        boom = RuntimeError("sdk exploded")
        runner = _runner_with_error_query(boom)
        errors: list[Exception] = []

        result = await runner.run_streaming(
            opts=AgentRunOptions(
                thread_id="err-001",
                user_message="explode",
                tool_choice="none",
            ),
            callbacks=AgentStreamingCallbacks(
                on_text_delta=lambda d: None,
                on_error=lambda e: errors.append(e),
            ),
        )

        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], RuntimeError)

    async def test_base_exception_group_with_cli_failure_fires_on_error(self):
        """anyio TaskGroup wraps CLI failure + sibling CancelledError into a
        BaseExceptionGroup; runner must fire on_error and return success=False.
        """
        cli_failure = Exception("Command failed with exit code 1")
        runner = _runner_with_exception_group([cli_failure, asyncio.CancelledError()])
        errors: list[Exception] = []

        result = await runner.run_streaming(
            opts=AgentRunOptions(
                thread_id="err-base-group-001",
                user_message="explode",
                tool_choice="none",
            ),
            callbacks=AgentStreamingCallbacks(
                on_text_delta=lambda d: None,
                on_error=lambda e: errors.append(e),
            ),
        )

        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)
        self.assertEqual(len(errors), 1)
        # Group is flattened to a readable plain Exception (not a group).
        self.assertNotIsInstance(errors[0], BaseExceptionGroup)
        self.assertIsInstance(errors[0], Exception)
        self.assertIn("Command failed with exit code 1", str(errors[0]))

    async def test_pure_cancellation_group_is_reraised(self):
        """A BaseExceptionGroup whose every leaf is CancelledError is a true outer
        cancel (FastAPI shutdown / client disconnect / explicit task.cancel()) and
        must propagate so the surrounding task hierarchy unwinds correctly.
        on_error must NOT fire and run_streaming must NOT return an AgentRunResult.

        The current runner's ``except Exception`` does not catch BaseExceptionGroup,
        so pure-cancellation groups already propagate correctly.
        """

        runner = _runner_with_exception_group([asyncio.CancelledError(), asyncio.CancelledError()])
        errors: list[Exception] = []

        with self.assertRaises(BaseExceptionGroup):
            await runner.run_streaming(
                opts=AgentRunOptions(
                    thread_id="cancel-001",
                    user_message="cancel",
                    tool_choice="none",
                ),
                callbacks=AgentStreamingCallbacks(
                    on_text_delta=lambda d: None,
                    on_error=lambda e: errors.append(e),
                ),
            )

        self.assertEqual(errors, [])

    async def test_bare_cancelled_error_is_reraised(self):
        """A bare CancelledError (legacy cancellation path) must propagate untouched.
        The runner's ``except Exception`` does not catch CancelledError (BaseException),
        so it re-raises correctly.
        """

        runner = _runner_with_error_query(asyncio.CancelledError())
        errors: list[Exception] = []

        with self.assertRaises(asyncio.CancelledError):
            await runner.run_streaming(
                opts=AgentRunOptions(
                    thread_id="cancel-bare-001",
                    user_message="cancel",
                    tool_choice="none",
                ),
                callbacks=AgentStreamingCallbacks(
                    on_text_delta=lambda d: None,
                    on_error=lambda e: errors.append(e),
                ),
            )

        self.assertEqual(errors, [])


class TestClaudeAgentRunnerToolConfirmation(_RunnerBase):
    """Tool confirmation callback is invoked when tool_choice='manual'."""

    @unittest.skip(
        "Tool confirmation uses PreToolUse SDK hooks which require a real Claude Code "
        "SDK subprocess. Mock query_stream yields AssistantMessage snapshots (post-execution) "
        "and cannot trigger PreToolUse hooks. Test requires real SDK integration."
    )
    async def test_tool_confirmation_callback_is_called(self):
        """on_tool_confirmation_request is wired to the PreToolUse SDK hook.

        This test is skipped in unit testing because PreToolUse fires before tool
        execution inside the real Claude Code SDK subprocess; a mock client that
        yields AssistantMessage snapshots cannot trigger it.
        See libs/claude_agent_kit/server/agent_runner.py _pre_tool_use_hook for
        the implementation.
        """
        pass  # skipped

    async def test_tool_confirmation_not_called_when_tool_choice_is_auto(self):
        """on_tool_confirmation_request is NOT invoked when tool_choice != 'manual'."""
        self.set_query([
            AssistantMessage([
                _tool_use_block("Bash", {"command": "ls"}, tool_id="tu-auto-1"),
            ]),
        ])
        runner = self.make_runner()
        confirmation_requests: list[dict] = []

        result = await runner.run_streaming(
            opts=AgentRunOptions(
                thread_id="tc-auto-001",
                user_message="list",
                tool_choice="auto",
            ),
            callbacks=AgentStreamingCallbacks(
                on_text_delta=lambda d: None,
                on_tool_confirmation_request=lambda p: confirmation_requests.append(p),
            ),
        )

        self.assertTrue(result.success)
        self.assertEqual(confirmation_requests, [])


class TestClaudeAgentRunnerMemoryEnvAliases(unittest.TestCase):
    """Memory MCP env uses Ink-owned names with Pawkeyland aliases as fallback."""

    def test_ink_memory_mcp_disable_flag_takes_precedence(self):
        with patch.dict(
            os.environ,
            {
                "INK_AGENT_ENABLE_MEMORY_MCP": "0",
                "PAWKEYLAND_ENABLE_AGENT_MEMORY_MCP": "1",
            },
            clear=True,
        ):
            self.assertFalse(agent_runner_module._memory_mcp_enabled())

    def test_mem0_hook_env_maps_ink_names_and_legacy_aliases(self):
        options = _SDK_OPTIONS(env={})
        request_env = {
            "INK_AGENT_MEM0_USER_ID": "ink-memory-user",
            "INK_AGENT_USER_MESSAGE": "remember this",
        }

        with patch.dict(
            os.environ,
            {
                "INK_AGENT_MEM0_API_KEY": "ink-mem0-key",
                "INK_AGENT_MEM0_API_HOST": "https://mem0.example",
                "INK_AGENT_MEM0_TOP_K": "7",
            },
            clear=True,
        ):
            agent_runner_module._inject_mem0_session_hook_env(options, request_env)

        self.assertEqual(options.env["MEM0_USER_ID"], "ink-memory-user")
        self.assertNotIn("INK_AGENT_MEM0_USER_ID", options.env)
        self.assertNotIn("PAWKEYLAND_MEM0_USER_ID", options.env)
        self.assertEqual(options.env["INK_AGENT_MEM0_API_KEY"], "ink-mem0-key")
        self.assertEqual(options.env["PAWKEYLAND_MEM0_API_KEY"], "ink-mem0-key")
        self.assertEqual(options.env["INK_AGENT_USER_MESSAGE"], "remember this")
        self.assertEqual(options.env["PAWKEYLAND_AGENT_USER_MESSAGE"], "remember this")


class TestClaudeAgentRunnerSdkEnvDiagnostics(unittest.TestCase):
    """SDK env diagnostics use direct Anthropic credentials."""

    def test_anthropic_auth_token_counts_as_auth(self):
        options = _SDK_OPTIONS(env={"ANTHROPIC_AUTH_TOKEN": "sk-test"})

        with patch.object(agent_runner_module.logger, "warning") as warning:
            agent_runner_module._verify_claude_sdk_env_for_query_stream(options)

        warning.assert_not_called()

    def test_missing_auth_warns_for_anthropic_auth_token(self):
        options = _SDK_OPTIONS(env={})

        with patch.object(agent_runner_module.logger, "warning") as warning:
            agent_runner_module._verify_claude_sdk_env_for_query_stream(options)

        warning.assert_called_once()
        warning_args = warning.call_args.args
        self.assertIn("has no auth key", warning_args[0])
        self.assertIn("ANTHROPIC_AUTH_TOKEN", warning_args[2])


class TestClaudeSdkEnvHelper(unittest.TestCase):
    """Project dotenv loading only forwards SDK-level keys."""

    def test_project_dotenv_env_filters_non_sdk_keys(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text(
                "\n".join(
                    [
                        "ANTHROPIC_AUTH_TOKEN=sk-test",
                        "ANTHROPIC_API_KEY=legacy-test",
                        "API_TIMEOUT_MS=1000",
                        "INK_AGENT_MEM0_API_KEY=mem0-test",
                        "INK_AGENT_TTL_S=600",
                    ]
                ),
                encoding="utf-8",
            )

            loaded = sdk_env_module.project_dotenv_env(env_file)

        self.assertEqual(
            loaded,
            {
                "ANTHROPIC_AUTH_TOKEN": "sk-test",
                "API_TIMEOUT_MS": "1000",
            },
        )

    def test_merge_project_dotenv_env_removes_legacy_api_key_override(self):
        loaded = sdk_env_module.merge_project_dotenv_env(
            {"ANTHROPIC_API_KEY": "legacy-test", "ANTHROPIC_AUTH_TOKEN": "sk-test"},
            env_file=Path("/tmp/does-not-exist"),
        )

        self.assertEqual(loaded, {"ANTHROPIC_AUTH_TOKEN": "sk-test"})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
