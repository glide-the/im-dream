# [Input] None — defines standalone type contracts for ClaudeAgentKit.
# [Output] Provide AgentRunOptions, AgentRunResult, AgentStreamingCallbacks, ToolEventPayload,
#          IClaudeAgentSDKClient to server and application layers.
# [Pos] type-contract node in libs/claude_agent_kit
# [Sync] 2026-05-09: add MCP subprocess env bindings for current pet context.
# [Sync] 2026-05-10: add include_runtime_context for specialized callers; pet chat uses the default SDK runtime block.
# [Sync] 2026-05-10: add turn_runtime for app local time enrichment in SDK runtime_context.
# [Sync] 2026-06-09: add im_full_access_enabled to allow Settings-controlled
#                    explicit PreToolUse approval for exposed tools.
# [Sync] 2026-06-13: im_full_access_enabled excludes AskUserQuestion-style tools
#                    because they must collect frontend answers before allow.
# [Sync] 2026-06-21: add sandbox_network_mode so the runner can enforce
#                    Settings "disabled" network policy in PreToolUse hooks.
# [Sync] 2026-07-20: add on_plan_file_changed streaming callback — fires after
#                    built-in Write/Edit/MultiEdit lands in the thread workspace
#                    plans dir (claude-plan §5.3).
# [Sync] 2026-07-20: add on_tasks_changed streaming callback — fires after
#                    TaskCreate/TaskUpdate PostToolUse with the full TodoItem
#                    list re-read from the thread workspace tasks dir
#                    (claude-todo §5.3).
# [Sync] 2026-07-23: add sandbox_network_allowed_domains to AgentRunOptions —
#                    Settings allowlist consumed by the PreToolUse
#                    SandboxPermissionRequest step (claude-agent-sandbox-network-
#                    permission-tool.md §6).
# [Sync] 2026-07-26: remove sandbox_network_allowed_domains again — the
#                    PreToolUse network gate was wrong-layer duplication;
#                    allowlists are enforced by the CLI sandbox
#                    (sandbox.network via workspace.py) and asks arrive via
#                    can_use_tool.
# [Sync] 2026-07-26: SDK migration — guarded re-export now sources
#                    ClaudeAgentOptions from claude_agent_sdk (renamed
#                    package, 0.2.128); the old claude_code_sdk /
#                    ClaudeCodeOptions names are gone.
# [Sync] 2026-08-20: carry a server-owned user secure-storage home separately
#                    from the thread-scoped Claude config home, and carry
#                    opaque user MCP definitions for public SDK injection.

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

from .messages.build_user_message_content import AttachmentPayload

# ---------------------------------------------------------------------------
# Convenience re-export so callers can import the SDK Message type from here.
# ---------------------------------------------------------------------------
try:
    from claude_agent_sdk.types import (  # type: ignore[import-untyped]
        ClaudeAgentOptions as _ClaudeAgentOptions,
    )
    from claude_agent_sdk import query as _sdk_query  # noqa: F401  (ensure importable)

    SDKMessage = Any  # SDK message union type (resolved at runtime)
    ClaudeAgentOptions = _ClaudeAgentOptions
except ImportError:  # pragma: no cover
    SDKMessage = Any
    ClaudeAgentOptions = Any

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
# Plan file observer: payload is the resolved plan file path (str).
_PlanFileChangedCallback = Callable[[str], Union[Awaitable[None], None]]
# Task v2 observer: payload is the full TodoItem dict list re-read from the
# thread workspace tasks dir (claude-todo §5.2 field shape: id/content/
# status/active_form/owner/blocked_by).
_TasksChangedCallback = Callable[[list], Union[Awaitable[None], None]]


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
    # Fires after a built-in Write/Edit/MultiEdit tool call whose resolved
    # path lands inside the thread workspace plans dir (claude-plan §5.3).
    # Debounced per file per turn via INK_AGENT_PLAN_EMIT_DEBOUNCE_MS.
    on_plan_file_changed: Optional[_PlanFileChangedCallback] = None
    # Fires after a TaskCreate/TaskUpdate tool call once the tasks dir has
    # been re-read and derived into TodoItem dicts (claude-todo §5.3).
    # Debounced per tasks dir per turn via INK_AGENT_TODO_EMIT_DEBOUNCE_MS.
    on_tasks_changed: Optional[_TasksChangedCallback] = None


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
    # User's message: either a plain string or a pre-built list of content
    # blocks (as returned by ClaudeAgentContextBuilder.build_user_message).
    # When a list is provided the runner uses it directly without further
    # context processing; when a plain string is provided the runner wraps it
    # in a single text block.
    user_message: Union[str, list[dict[str, Any]]]
    # Canonical PostgreSQL users.id bound by the authenticated Dream session.
    # Required when the Admin Gateway Claude canary is enabled; never accepted
    # from a browser header or model payload.
    canonical_user_id: Optional[str] = None
    # Server-derived stable key that correlates one persisted Dream message
    # with exactly one Admin Gateway settlement. Never accept the raw header
    # value from a browser request.
    gateway_idempotency_key: Optional[str] = None
    # Whether to resume an existing conversation.
    resume: bool = False
    # Model to use.
    model: Optional[str] = None
    # Working directory for the agent.
    cwd: Optional[str] = None
    # Server-resolved Claude config home for this thread (2026-08-03).
    # Resolved by the service layer via sdk_env.resolve_claude_config_home()
    # right after workspace/cwd resolution — BEFORE any claude module
    # (resume probe, plugin pack, plan/tasks readers) touches the
    # filesystem — so the redirect decision is not buried in the
    # run_streaming lifecycle.  The runner applies it as the FIRST
    # options-build step (CLAUDE_CONFIG_DIR), relocating the CLI's entire
    # config home (plans/, tasks/, projects/ transcripts, plugins/, agents/,
    # caches) into the per-thread workspace.  When None the runner falls
    # back to resolving from ``cwd`` itself.
    claude_config_home: Optional[str] = None
    # macOS Claude Code stores OAuth credentials in a Keychain item selected
    # independently from CLAUDE_CONFIG_DIR.  The service resolves this path
    # from the authenticated platform user; the runner injects it as
    # CLAUDE_SECURESTORAGE_CONFIG_DIR while retaining the thread config home.
    # Linux leaves this unset and receives a minimal `.credentials.json`
    # projection on every turn.
    claude_secure_storage_home: Optional[str] = None
    # Opaque remote MCP definitions resolved from the authenticated
    # platform user's Claude config on every turn.  The runner injects these
    # through the public Agent SDK `mcp_servers` option because its deliberate
    # project-only setting source does not load user-scope `.claude.json`.
    # Kept out of repr because an externally authored config may contain
    # opaque headers even though the Resources UI never creates them.
    claude_mcp_servers: dict[str, dict[str, Any]] = field(
        default_factory=dict,
        repr=False,
    )
    # Maximum turns for the agent.
    max_turns: int = 100
    # Allowed tools for the agent.
    allowed_tools: Optional[list[str]] = None
    # Tool choice mode.
    tool_choice: ToolChoiceMode = "auto"
    # Settings-controlled full access mode. When true, the runner returns an
    # explicit PreToolUse permissionDecision:"allow" for exposed tools after
    # safe virtual-index redirects, except AskUserQuestion-style tools that
    # must collect frontend answers first.
    im_full_access_enabled: bool = False
    # Settings-controlled sandbox network mode. ``disabled`` is enforced by
    # runner PreToolUse hooks before full-access or low-sensitivity allows;
    # ``allowlist``/``open`` are enforced by Claude Code's own sandbox
    # (sandbox.network in per-thread .claude/settings.json) whose runtime asks
    # arrive via the SDK can_use_tool channel — there is no PreToolUse-layer
    # network gate (removed 2026-07-26 as wrong-layer duplication).
    sandbox_network_mode: Literal["disabled", "allowlist", "open"] = "allowlist"
    # System prompt override.
    system_prompt: Optional[str] = None
    # NOTE (2026-08-02, deck-integration-delta): ``settings_json`` and
    # ``local_plugin_paths`` were removed.  Per-run options must never carry
    # workspace configuration or plugin artifact paths: settings belong to
    # the per-thread workspace (``.claude-home`` / CLAUDE_CONFIG_DIR), and
    # plugins are packed into the workspace and loaded through the
    # server-controlled launch manifest at the CLI launcher boundary
    # (plugin_launcher.apply_plugin_launch_options → literal --plugin-dir).
    # Deprecated: context processing is now owned by ClaudeAgentContextBuilder.
    # Kept for backward compatibility with callers that set it; ignored by runner.
    include_runtime_context: bool = True
    # Deprecated: local time/timezone should be passed to build_user_message instead.
    # Kept for backward compatibility; ignored by runner when user_message is a list.
    turn_runtime: dict[str, Any] = field(default_factory=dict)
    # Environment passed to project-owned MCP subprocesses for current-session bindings.
    mcp_env: dict[str, str] = field(default_factory=dict)
    # User-scoped SDK env vars from system_config.env_vars.
    # Allowlist-filtered before injection into ClaudeAgentOptions.env.
    # Priority: higher than backend/.env, lower than explicit options.env.
    user_sdk_env: dict[str, str] = field(default_factory=dict)
    # Deprecated: attachments should be passed to build_user_message instead.
    # Kept for backward compatibility; ignored by runner when user_message is a list.
    attachments: Optional[list[AttachmentPayload]] = None
    # Current EditorState snapshot for the session.  When set, the runner:
    #   (a) intercepts ``Read`` tool calls targeting ``.editor/<resource>.json``
    #       and redirects them to a temporary file containing the extracted
    #       resource slice (see ``editor_index.py``);
    #   (b) starts the editor MCP write subprocess so the agent can call write
    #       tools (session_id is supplied by the agent from its prompt context).
    # None means no editor context is active (e.g. pure chat turns).
    editor_state: Optional[dict[str, Any]] = None
    # Optional live getter that returns the current editor_state from the
    # AgentRunState flyweight.  When provided, the PreToolUse hook reads from
    # this callable so it always sees the latest value — including updates that
    # the tool-event callback writes back after a confirmed MCP write-tool
    # result.  Falls back to ``editor_state`` when not set (e.g. unit tests).
    editor_state_getter: Optional[Any] = None
    # Optional setter that writes a new editor_state into the AgentRunState
    # flyweight.  Called by the PostToolUse hook after a successful
    # ``switch_editor`` tool call: the hook loads the target session's
    # editor_state from the database and passes it to this setter so that
    # subsequent .editor/ reads via ``editor_state_getter`` reflect the new
    # document context.
    # Signature: ``(new_editor_state: dict) -> None``.
    editor_state_setter: Optional[Any] = None


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
        cwd: Optional[str] = None,
    ) -> dict[str, list[Any]]:
        """Load message history for a session. Returns ``{"messages": [...]}``.

        *cwd* is the thread workspace in Workspace Mode; it locates
        transcripts under ``{cwd}/.claude-home/projects`` instead of the
        global ``~/.claude/projects``.
        """
        ...
