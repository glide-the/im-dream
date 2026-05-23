# [Input] None — defines standalone type contracts for ClaudeAgentKit.
# [Output] Provide AgentRunOptions, AgentRunResult, AgentStreamingCallbacks, ToolEventPayload,
#          IClaudeAgentSDKClient to server and application layers.
# [Pos] type-contract node in libs/claude_agent_kit
# [Sync] 2026-05-09: add MCP subprocess env bindings for current pet context.
# [Sync] 2026-05-10: add include_runtime_context for specialized callers; pet chat uses the default SDK runtime block.
# [Sync] 2026-05-10: add turn_runtime for app local time enrichment in SDK runtime_context.

"""Type definitions for ClaudeAgentKit.

Python translation of the TypeScript interfaces from:
- server/types/client.ts
- server/types/session.ts
- server/server/agent-runner.ts  (ToolEventPayload, AgentStreamingCallbacks, etc.)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Awaitable
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Optional, Union

# ---------------------------------------------------------------------------
# Convenience re-export so callers can import the SDK Message type from here.
# ---------------------------------------------------------------------------
try:
    from claude_code_sdk.types import (  # type: ignore[import-untyped]
        ClaudeCodeOptions as _ClaudeCodeOptions,
    )
    from claude_code_sdk import query as _sdk_query  # noqa: F401  (ensure importable)

    SDKMessage = Any  # SDK message union type (resolved at runtime)
    ClaudeCodeOptions = _ClaudeCodeOptions
except ImportError:  # pragma: no cover
    SDKMessage = Any
    ClaudeCodeOptions = Any

# Tool choice mode — determines how tool calls are handled
ToolChoiceMode = Literal["auto", "none", "manual"]


# ---------------------------------------------------------------------------
# Tool event payload
# ---------------------------------------------------------------------------


@dataclass
class ToolEventPayload:
    """Tool event payload for streaming.

    Extended to include all parameters that might be present in tool calls.
    Maps to TypeScript ``ToolEventPayload`` in agent-runner.ts.
    """

    type: str
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None
    input: Optional[Any] = None
    output: Optional[Any] = None
    state: Optional[
        Literal[
            "input-available",
            "input-streaming",
            "output-available",
            "output-error",
            "error",
        ]
    ] = None
    is_error: Optional[bool] = None
    title: Optional[str] = None
    provider_executed: Optional[bool] = None
    # Stop reason from message_delta events (e.g. "end_turn", "tool_use")
    stop_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Streaming callbacks
# ---------------------------------------------------------------------------

# Callback type aliases for readability
_TextCallback = Callable[[str], Union[Awaitable[None], None]]
_ToolEventCallback = Callable[[ToolEventPayload], Union[Awaitable[None], None]]
_ToolConfirmationCallback = Callable[
    [dict[str, Any]],
    Union[
        Awaitable[Optional[dict[str, Any]]],
        Optional[dict[str, Any]],
    ],
]
_ErrorCallback = Callable[[Exception], Union[Awaitable[None], None]]
_MessageCallback = Callable[[Any], Union[Awaitable[None], None]]


@dataclass
class AgentStreamingCallbacks:
    """Callbacks for streaming responses.

    Maps to TypeScript ``AgentStreamingCallbacks`` in agent-runner.ts.
    """

    # Required
    on_text_delta: _TextCallback

    # Optional
    on_text_done: Optional[_TextCallback] = None
    on_tool_event: Optional[_ToolEventCallback] = None
    on_tool_confirmation_request: Optional[_ToolConfirmationCallback] = None
    on_error: Optional[_ErrorCallback] = None
    on_message: Optional[_MessageCallback] = None


# ---------------------------------------------------------------------------
# Run options & result
# ---------------------------------------------------------------------------


@dataclass
class AgentRunOptions:
    """Options for running the agent.

    Maps to TypeScript ``AgentRunOptions`` in agent-runner.ts.
    Note: ``thread_id`` in Claude Agent SDK is the same as ``session_id``.
    """

    # Thread ID for conversation context — same as session_id in the SDK.
    thread_id: str
    # User's message text.
    user_message: str
    # Whether to resume an existing conversation.
    resume: bool = False
    # Model to use.
    model: Optional[str] = None
    # Working directory for the agent.
    cwd: Optional[str] = None
    # Maximum turns for the agent.
    max_turns: int = 100
    # Allowed tools for the agent.
    allowed_tools: Optional[list[str]] = None
    # Tool choice mode.
    tool_choice: ToolChoiceMode = "auto"
    # System prompt override.
    system_prompt: Optional[str] = None
    # Whether the SDK message builder should prepend its lightweight runtime block.
    include_runtime_context: bool = True
    # App-provided turn runtime metadata, e.g. local time and timezone.
    turn_runtime: dict[str, Any] = field(default_factory=dict)
    # Environment passed to project-owned MCP subprocesses for current-session bindings.
    mcp_env: dict[str, str] = field(default_factory=dict)
    # Live EditorState snapshot for the current writing session.
    # When provided, ``Read`` calls against ``.editor/`` virtual paths are
    # intercepted by the ``PreToolUse`` hook and redirected to transient
    # tempfiles populated from this dict.
    editor_state: Optional[dict[str, Any]] = None


@dataclass
class AgentRunResult:
    """Result from agent run.

    Maps to TypeScript ``AgentRunResult`` in agent-runner.ts.
    """

    # Full text response.
    full_text: str
    # Session ID — same as thread_id in the SDK.
    session_id: Optional[str]
    # Whether the run completed successfully.
    success: bool
    # Error if any.
    error: Optional[Exception] = None
    # All messages from the run.
    messages: list[Any] = field(default_factory=list)
    # Token usage statistics.
    usage: Optional[dict[str, Optional[int]]] = None


# ---------------------------------------------------------------------------
# SDK client interface
# ---------------------------------------------------------------------------


class IClaudeAgentSDKClient(ABC):
    """Interface for Claude Agent SDK Client.

    Maps to TypeScript ``IClaudeAgentSDKClient`` in server/types/client.ts.
    """

    @abstractmethod
    def query_stream(
        self,
        prompt: Any,
        options: Optional[Any] = None,
    ) -> AsyncIterator[Any]:
        """Stream messages from the Claude agent subprocess."""
        ...

    @abstractmethod
    async def load_messages(
        self,
        session_id: Optional[str],
    ) -> dict[str, list[Any]]:
        """Load message history for a session. Returns ``{"messages": [...]}``. """
        ...
