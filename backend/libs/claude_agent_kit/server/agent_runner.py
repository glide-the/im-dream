# [Input] Consume IClaudeAgentSDKClient, AgentStreamingCallbacks, AgentRunOptions,
#         AgentRunResult, ToolEventPayload from types.py;
#         build_user_message_content from messages/;
#         SimpleClaudeAgentSDKClient from simple_cas_client.py;
# [Output] Provide ClaudeAgentRunner and create_agent_runner to application layers.
# [Pos] core runner node in libs/claude_agent_kit/server
# [Sync] 2026-05-09: forward stdio MCP tool input and result events for frontend traces.
# [Sync] 2026-05-09: merge project .env SDK injection, stderr capture, and PreToolUse confirmation hooks while keeping Pet Chat's narrow stdio MCP surface.
# [Sync] 2026-05-09: expose zero-argument necklace intent tools while keeping server-owned upstream parameters.
# [Sync] 2026-05-09: guard ExceptionGroup checks on Python runtimes that lack PEP 654 builtins.
# [Sync] 2026-05-09: expose app Mem0 memory recall through zero-argument stdio MCP.
# [Sync] 2026-05-10: keep Claude Code Mem0 hooks on the server-bound Pawkeyland memory index instead of a thread namespace.
# [Sync] 2026-05-10: keep app memory MCP on the server-bound Mem0 API host.
# [Sync] 2026-05-24: prefer INK_AGENT_MEM0_* env names while accepting PAWKEYLAND_* aliases.
# [Sync] 2026-05-10: bridge PreToolUse confirmation through the FastAPI loop so the SDK control task never blocks the worker, even if a future SDK release moves hook dispatch off the running loop.
# [Sync] 2026-05-10: forward include_runtime_context to message building for app-owned runtime prompts.
# [Sync] 2026-05-10: forward app local time into the SDK runtime_context block.
# [Sync] 2026-05-11: stream thinking_delta from delta.thinking through an index-keyed thinking block accumulator and retain signature_delta metadata.
# [Sync] 2026-05-11: include Claude Code interleaved-thinking disable env in SDK propagation diagnostics.
# [Sync] 2026-05-24: diagnose direct ANTHROPIC_AUTH_TOKEN auth.
# [Sync] 2026-05-12: enrich the on_error path with SDK-call context **without changing the exception type** — the SDK's Query._read_messages strips the original ProcessError(message, exit_code, stderr) down to ``str(e)`` before re-raising, so by the time the runner's ``except Exception`` runs we only have a generic "Command failed with exit code 1" string.  The except block now (a) keeps the original exception object untouched (``run_error = exc`` for non-group exceptions, preserving downstream ``isinstance`` checks like ``test_sdk_error_sets_success_false``'s ``assertIsInstance(errors[0], RuntimeError)``); (b) attaches a structured ``[claude_agent_kit] sdk_call_context: resume=… thread_id=… cwd=… model=…`` PEP-678 note via ``run_error.add_note(...)`` so formatted tracebacks and ``getattr(exc, '__notes__', [])`` consumers see the failing session; (c) attaches a second ``[claude_agent_kit] cli_stderr: …`` note when the SDK ``debug_stderr`` buffer captured anything; (d) emits a single ``logger.exception`` with all the structured fields plus traceback for log aggregators.  ``ExceptionGroup`` is the only case that still gets re-wrapped into a plain Exception (its default ``str()`` is unreadable and downstream typed handlers gain nothing from the group wrapper).  The Service-side ``on_error`` SSE frame composes the user-facing ``errorText`` by joining ``str(error)`` with the notes via ``" | "`` so the rich context surfaces through the existing SSE schema unchanged.
# [Sync] 2026-05-12: widen run_streaming's exception catch from ``except Exception`` to ``except BaseException`` so anyio TaskGroup ``BaseExceptionGroup`` wrappers actually fire ``callbacks.on_error`` and surface as ``AgentRunResult(success=False)``.  Root cause: ``claude_code_sdk._internal.query.Query._read_messages`` catches the CLI failure, logs ``ERROR Fatal error in message reader: Command failed with exit code 1``, and reshapes it into a synthetic ``{"type":"error"}`` stream message; ``Query.receive_messages`` raises a plain ``Exception`` from that sentinel; ``async with ClaudeSDKClient`` ``__aexit__`` then cancels the still-running write / control sibling tasks, raising ``CancelledError`` (a ``BaseException`` subclass), and the SDK's TaskGroup packages everything into a ``BaseExceptionGroup``.  ``BaseExceptionGroup`` is **not** an ``Exception`` subclass, so the previous ``except Exception`` silently let the failure propagate past the runner — ``on_error`` never fired, ``success`` kept its default ``True``, and the caller saw a half-finished stream with no error frame.  New ``_is_pure_cancellation(exc)`` helper distinguishes "every leaf is ``CancelledError``" (true outer cancel — re-raise so the FastAPI / pytest task hierarchy still unwinds) from "at least one non-cancelled leaf" (the typical CLI-failure-plus-sibling-cancel group — fall through to the existing diagnostic-enrichment + ``on_error`` path).  The group-flattening branch is also widened from ``_EXCEPTION_GROUP_TYPES`` to ``_BASE_EXCEPTION_GROUP_TYPES`` so ``BaseExceptionGroup`` (which ``ExceptionGroup`` is now a subclass of, per PEP 654) gets the same readable-message treatment instead of leaving the ugly default group ``str()`` in the SSE error frame.  Bare non-cancelled ``BaseException`` leaves (``KeyboardInterrupt`` / ``SystemExit``) are wrapped into a plain ``Exception`` for the same SSE-serialisation reason.  No service-side change required: ``execute_session`` already routes ``result.success is False`` to a ``{"type":"error","errorText":...}`` SSE frame, and the existing ``except BaseException`` + ``_exception_group_contains_cancelled`` re-raise stays as the *outer* cancel safety net for cases the runner re-raises from ``_is_pure_cancellation``.
# [Sync] 2026-05-24: keep run_streaming's BaseException diagnostic log on logger.exception so backend logs include the caught traceback while on_error still receives the enriched run_error.
# [Sync] 2026-05-24: rename _REQUEST_MODEL_OVERRIDE_ENV_KEY from PAWKEYLAND_CLAUDE_AGENT_ALLOW_REQUEST_MODEL_OVERRIDE to INK_AGENT_ALLOW_REQUEST_MODEL_OVERRIDE; keep legacy key as fallback in _apply_request_model_override_if_allowed for zero-downtime migration.
# [Sync] 2026-05-24: move _inject_mem0_session_hook_env and _verify_claude_sdk_env_for_query_stream calls inside run_streaming's try/except BaseException block so any raised exception is caught and routed to callbacks.on_error → SSE error frame; raise RuntimeError in _verify_claude_sdk_env_for_query_stream when no auth key is present instead of silently returning.
# [Sync] 2026-05-27: migrate _pre_tool_use_hook hookSpecificOutput from old {"tool_input":...} format to CLI ≥2.1 format: hookEventName + permissionDecision:"allow" + updatedInput for input override; permissionDecision:"deny" + permissionDecisionReason for all block paths. The old "tool_input" key is silently ignored by the CLI, leaving AskUserQuestion without answers and returning isError:true / output:null.
# [Sync] 2026-05-27: add _ALWAYS_CONFIRM_TOOL_NAMES constant; in auto mode, AskUserQuestion/mcp__user__ask_user still go through on_tool_confirmation_request so the frontend form collects answers before execution; all other tools are auto-approved.
# [Sync] 2026-05-28: implement .editor/ virtual index read interception in _pre_tool_use_hook — detect is_editor_index_path, write tempfile from editor_state, return updatedInput redirect (CLI ≥2.1 format); cleanup tempfiles in finally block.
# [Sync] 2026-05-29: extract .editor/ redirect block into module-level _apply_editor_index_redirect for unit-testability; _pre_tool_use_hook delegates to it.
# [Sync] 2026-05-29: _editor_mcp_stdio_config now accepts editor_state dict and passes it
#                    as INK_EDITOR_STATE_JSON env var (session-inline, no tempfile);
#                    removes tempfile creation/cleanup for editor MCP in run_streaming.
# [Sync] 2026-05-29: switch editor MCP from read-only tools to write-only tools; replace
#                    INK_EDITOR_STATE_JSON injection with INK_AGENT_SESSION_ID +
#                    INK_AGENT_USER_ID so write handlers call database directly; add all
#                    four write tool names to _ALWAYS_CONFIRM_TOOL_NAMES; editor MCP
#                    startup condition now checks mcp_env for INK_AGENT_SESSION_ID.
# [Sync] 2026-05-29: remove env-var session injection; _editor_mcp_stdio_config is
#                    zero-argument — session_id flows via MCP tool arguments from prompt;
#                    editor MCP startup condition restored to opts.editor_state is not None.
# [Sync] 2026-05-29: remove env-var session context injection; session_id flows through
#                    MCP tool call arguments (agent reads from <workspace_context> prompt);
#                    _editor_mcp_stdio_config reverts to zero-arg form; editor MCP startup
#                    condition restored to opts.editor_state is not None.

"""Claude Agent Runner.

Python translation of TypeScript:
  server/server/agent-runner.ts

Unified interface for running the Claude agent with streaming support.
Wraps ``SimpleClaudeAgentSDKClient`` to provide a clean streaming-callback
interface for the AI worker.
"""
from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Optional
from uuid import uuid4

from claude_code_sdk.types import (  # type: ignore[import-untyped]
    AssistantMessage,
    ClaudeCodeOptions,
    HookContext,
    HookJSONOutput,
    HookMatcher,
    McpServerConfig,
    McpStdioServerConfig,
    ResultMessage,
    StreamEvent,
    SystemMessage,
    UserMessage,
)

from ..types import (
    AgentRunOptions,
    AgentRunResult,
    AgentStreamingCallbacks,
    IClaudeAgentSDKClient,
    ToolChoiceMode,
    ToolEventPayload,
)
from .simple_cas_client import SimpleClaudeAgentSDKClient
from .memory_tool import allowed_memory_tool_names
from .necklace_tool import allowed_necklace_tool_names
from .editor_tool import allowed_editor_tool_names
from .sdk_env import apply_project_sdk_runtime_options, apply_user_sdk_env_to_options

logger = logging.getLogger(__name__)

try:
    _BASE_EXCEPTION_GROUP_TYPES: tuple[type[BaseException], ...] = (BaseExceptionGroup,)  # type: ignore[name-defined]
    _EXCEPTION_GROUP_TYPES: tuple[type[BaseException], ...] = (ExceptionGroup,)  # type: ignore[name-defined]
except NameError:
    _BASE_EXCEPTION_GROUP_TYPES = ()
    _EXCEPTION_GROUP_TYPES = ()

# ---------------------------------------------------------------------------
# Default tool allowlist.
#
# Pet chat is the product-facing path, so the default surface is intentionally
# narrow: expose only the user MCP touch-animation tool and no built-in
# filesystem/web/Bash-style tools.
# ---------------------------------------------------------------------------

DEFAULT_ALLOWED_TOOLS: list[str] = [
    "mcp__user__touch_animation",
    *allowed_memory_tool_names(),
    *allowed_necklace_tool_names(),
    *allowed_editor_tool_names(),
]
_USER_MCP_TOOL_PREFIX = "mcp__user__"
_MEMORY_MCP_TOOL_PREFIX = "mcp__memory__"
_NECKLACE_MCP_TOOL_PREFIX = "mcp__necklace__"
_EDITOR_MCP_TOOL_PREFIX = "mcp__editor__"

# Tools that must always go through the on_tool_confirmation_request side-channel
# regardless of tool_choice mode (i.e. even in "auto" mode).  These are
# interactive Q&A tools whose answers can only come from the user — they cannot
# be auto-approved because they need the frontend form to collect answers.
# Note: mcp__user__touch_animation is intentionally excluded; in auto mode the
# animation runs without user interaction.
# Editor write tools are always confirmed: all document mutations require explicit
# human approval before the MCP subprocess applies them to the database.
_ALWAYS_CONFIRM_TOOL_NAMES: frozenset[str] = frozenset({
    "AskUserQuestion",
    "mcp__user__ask_user",
    # Editor write tools — all require human confirmation (see mcp-tools.md §4)
    "mcp__editor__write_segment",
    "mcp__editor__delete_segment",
    "mcp__editor__insert_widget",
    "mcp__editor__reply_to_comment",
})
_TRUE_ENV_VALUES = {"1", "true", "yes", "on"}
_FALSE_ENV_VALUES = {"0", "false", "no", "off"}
_REPO_ROOT = Path(__file__).resolve().parents[3]
_NECKLACE_ENV_NAMES: tuple[str, ...] = (
    "PAWKEYLAND_AGENT_PET_ID",
    "PAWKEYLAND_AGENT_PET_SPECIES",
    "PAWKEYLAND_AGENT_PET_TYPE",
    "PAWKEYLAND_QIALG_BASE_URL",
    "PAWKEYLAND_QIALG_LOGIN_URL",
    "PAWKEYLAND_QIALG_LOGIN_MOBILE",
    "PAWKEYLAND_QIALG_LOGIN_SMS_CODE",
    "PAWKEYLAND_QIALG_LOGIN_CAPTCHA",
    "PAWKEYLAND_QIALG_LOGIN_THIRD_ID",
    "PAWKEYLAND_QIALG_NECKLACE_ACCESS_TOKEN",
    "PAWKEYLAND_NECKLACE_FETCH_TIMEOUT_S",
    "PAWKEYLAND_NECKLACE_RECENT_WINDOW_MINUTES",
    "PAWKEYLAND_NECKLACE_USE_REFERENCE_TIME",
    "PAWKEYLAND_NECKLACE_REFERENCE_TIME",
    "PAWKEYLAND_NECKLACE_REFERENCE_DATE",
)
_MEMORY_ENV_ALIASES: tuple[tuple[str, str], ...] = (
    ("INK_AGENT_MEM0_ENABLED", "PAWKEYLAND_MEM0_ENABLED"),
    ("INK_AGENT_MEM0_API_KEY", "PAWKEYLAND_MEM0_API_KEY"),
    ("INK_AGENT_MEM0_API_HOST", "PAWKEYLAND_MEM0_API_HOST"),
    ("INK_AGENT_MEM0_CONNECT_TIMEOUT_MS", "PAWKEYLAND_MEM0_CONNECT_TIMEOUT_MS"),
    ("INK_AGENT_MEM0_READ_TIMEOUT_MS", "PAWKEYLAND_MEM0_READ_TIMEOUT_MS"),
    ("INK_AGENT_MEM0_TOP_K", "PAWKEYLAND_MEM0_TOP_K"),
    ("INK_AGENT_MEM0_USER_ID", "PAWKEYLAND_MEM0_USER_ID"),
    ("INK_AGENT_USER_MESSAGE", "PAWKEYLAND_AGENT_USER_MESSAGE"),
)
_MEMORY_USER_ID_ENV_NAMES = ("INK_AGENT_MEM0_USER_ID", "PAWKEYLAND_MEM0_USER_ID")
_CLAUDE_SDK_ENV_KEYS: tuple[str, ...] = (
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "API_TIMEOUT_MS",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC",
    "DISABLE_INTERLEAVED_THINKING",
)
_CLAUDE_SDK_AUTH_ENV_KEYS: tuple[str, ...] = (
    "ANTHROPIC_AUTH_TOKEN",
)
# Primary key (Ink & Memory prefix); legacy Pawkeyland key is accepted as
# fallback so deployments with the old .env survive until they migrate.
_REQUEST_MODEL_OVERRIDE_ENV_KEY = "INK_AGENT_ALLOW_REQUEST_MODEL_OVERRIDE"
_REQUEST_MODEL_OVERRIDE_ENV_KEY_LEGACY = (
    "PAWKEYLAND_CLAUDE_AGENT_ALLOW_REQUEST_MODEL_OVERRIDE"
)


def _verify_claude_sdk_env_for_query_stream(sdk_options: ClaudeCodeOptions) -> None:
    """Log Claude SDK subprocess env propagation status without exposing secrets."""

    existing_env = getattr(sdk_options, "env", None)
    if isinstance(existing_env, dict):
        env = existing_env
    else:
        env = dict(existing_env or {})
        sdk_options.env = env

    present_keys = [key for key in _CLAUDE_SDK_ENV_KEYS if bool(env.get(key))]
    missing_keys = [key for key in _CLAUDE_SDK_ENV_KEYS if not env.get(key)]
    has_auth_key = any(bool(env.get(key)) for key in _CLAUDE_SDK_AUTH_ENV_KEYS)

    if not has_auth_key:
        logger.warning(
            "Claude SDK env check before query_stream has no auth key; "
            "present_keys=%s missing_keys=%s env_count=%d",
            present_keys,
            missing_keys,
            len(env),
        )
        raise RuntimeError(
            f"Claude SDK has no auth key in subprocess env; "
            f"expected one of {_CLAUDE_SDK_AUTH_ENV_KEYS!r}. "
            f"present_keys={present_keys!r} env_count={len(env)}"
        )

    logger.debug(
        "Claude SDK env check before query_stream; present_keys=%s "
        "missing_keys=%s env_count=%d",
        present_keys,
        missing_keys,
        len(env),
    )


def _env_flag_enabled(value: Optional[str]) -> bool:
    return (value or "").strip().lower() in _TRUE_ENV_VALUES


def _first_env_value(*names: str) -> str:
    for name in names:
        value = str(os.getenv(name, "") or "").strip()
        if value:
            return value
    return ""


def _first_mapping_value(mapping: dict[str, str], *names: str) -> str:
    for name in names:
        value = str(mapping.get(name, "") or "").strip()
        if value:
            return value
    return ""


def _set_env_aliases(
    env: dict[str, str],
    canonical_name: str,
    legacy_name: str,
    value: str,
) -> None:
    if not value:
        return
    env[canonical_name] = value
    env[legacy_name] = value


def _apply_request_model_override_if_allowed(
    sdk_options: ClaudeCodeOptions,
    requested_model: Optional[str],
) -> None:
    """Apply request-level model only when explicitly enabled by project env."""

    model_name = (requested_model or "").strip()
    if not model_name:
        return

    existing_env = getattr(sdk_options, "env", None)
    if isinstance(existing_env, dict):
        env = existing_env
    else:
        env = dict(existing_env or {})
        sdk_options.env = env

    # Accept both new (INK_AGENT_*) and legacy (PAWKEYLAND_*) key names.
    override_enabled = _env_flag_enabled(
        env.get(_REQUEST_MODEL_OVERRIDE_ENV_KEY)
        or env.get(_REQUEST_MODEL_OVERRIDE_ENV_KEY_LEGACY)
    )
    if override_enabled:
        sdk_options.model = model_name
        logger.debug("Claude SDK request model override enabled; model=%s", model_name)
        return

    logger.info(
        "Ignoring request-level Claude SDK model override; requested_model=%s "
        "configured_model_present=%s override_env_key=%s",
        model_name,
        bool(env.get("ANTHROPIC_MODEL")),
        _REQUEST_MODEL_OVERRIDE_ENV_KEY,
    )


def _inject_mem0_session_hook_env(
    sdk_options: ClaudeCodeOptions,
    request_env: Optional[dict[str, str]],
) -> None:
    """Expose the app-resolved Mem0 binding to Claude Code lifecycle hooks."""

    existing_env = getattr(sdk_options, "env", None)
    if isinstance(existing_env, dict):
        env = existing_env
    else:
        env = dict(existing_env or {})
        sdk_options.env = env

    scoped_env = request_env or {}
    app_mem0_user_id = _first_mapping_value(scoped_env, *_MEMORY_USER_ID_ENV_NAMES)
    if not app_mem0_user_id:
        # Project .env is allowed to carry Mem0 service config, but not a
        # request-scoped memory identity. Avoid leaking a stale or legacy hook key.
        env.pop("INK_AGENT_MEM0_USER_ID", None)
        env.pop("PAWKEYLAND_MEM0_USER_ID", None)
        env.pop("INK_AGENT_USER_MESSAGE", None)
        env.pop("PAWKEYLAND_AGENT_USER_MESSAGE", None)
        env.pop("MEM0_USER_ID", None)
        return

    for canonical_name, legacy_name in _MEMORY_ENV_ALIASES:
        if canonical_name == "INK_AGENT_MEM0_USER_ID":
            continue
        value = _first_mapping_value(scoped_env, canonical_name, legacy_name)
        if not value:
            value = _first_env_value(canonical_name, legacy_name)
        if value:
            _set_env_aliases(env, canonical_name, legacy_name, str(value))
    env.pop("INK_AGENT_MEM0_USER_ID", None)
    env.pop("PAWKEYLAND_MEM0_USER_ID", None)
    # Follow the claude-runner hook contract: lifecycle hooks read MEM0_USER_ID.
    # The value is the app memory key, never the Claude SDK thread id.
    env["MEM0_USER_ID"] = app_mem0_user_id


class _StderrSentinelArgs(dict):  # type: ignore[type-arg]
    """Enable SDK stderr capture without adding an unsupported CLI flag."""

    def __contains__(self, item: object) -> bool:  # type: ignore[override]
        return item == "debug-to-stderr" or super().__contains__(item)


def _iter_exception_leaves(exc: BaseException) -> list[BaseException]:
    if _BASE_EXCEPTION_GROUP_TYPES and isinstance(exc, _BASE_EXCEPTION_GROUP_TYPES):
        leaves: list[BaseException] = []
        for child in exc.exceptions:
            leaves.extend(_iter_exception_leaves(child))
        return leaves
    return [exc]


def _format_exception_message(exc: BaseException) -> str:
    leaves = _iter_exception_leaves(exc)
    if len(leaves) == 1 and leaves[0] is exc:
        return str(exc)
    return "; ".join(f"{type(leaf).__name__}: {leaf}" for leaf in leaves)


def _is_pure_cancellation(exc: BaseException) -> bool:
    """Return True when *exc* represents *only* task cancellation.

    The Claude Code SDK runs its CLI subprocess inside an ``anyio.TaskGroup``.
    When the message-reader task fails the SDK re-shapes the failure into a
    synthetic ``{"type": "error"}`` stream message; ``Query.receive_messages``
    raises a plain ``Exception`` from that sentinel.  As the failure unwinds,
    ``ClaudeSDKClient.__aexit__`` cancels the still-running write / control
    sibling tasks, which raise ``CancelledError`` (a ``BaseException`` subclass).
    The TaskGroup then packages the original ``Exception`` together with the
    sibling ``CancelledError`` instances into a ``BaseExceptionGroup`` —
    which is *not* an ``Exception`` subclass, so a bare ``except Exception``
    silently lets it through and ``callbacks.on_error`` never fires.

    To restore correct error reporting we widen the runner's catch to
    ``BaseException`` and use this predicate to decide whether to re-raise
    the group: only re-raise when *every* leaf is a cancellation, which is
    the signature of a true outer cancel (FastAPI shutdown, client
    disconnect, explicit ``task.cancel()``).  Mixed groups — the typical
    "CLI exit 1 + sibling cancellations" case — are treated as a regular
    runner failure so ``on_error`` fires and the service emits the SSE
    ``error`` frame.
    """

    leaves = _iter_exception_leaves(exc)
    if not leaves:
        return False
    return all(isinstance(leaf, asyncio.CancelledError) for leaf in leaves)


def _csv_env_values(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _default_allowed_tools() -> list[str]:
    """Resolve the default chat tool allowlist from env.

    ``PAWKEYLAND_AGENT_ALLOWED_TOOLS`` may override this with a comma-separated
    list. Leave the env var unset to use the default touch-animation tool.
    """

    return _csv_env_values("PAWKEYLAND_AGENT_ALLOWED_TOOLS") or list(DEFAULT_ALLOWED_TOOLS)


def _user_mcp_enabled() -> bool:
    raw = os.getenv("PAWKEYLAND_ENABLE_AGENT_USER_MCP", "").strip().lower()
    if raw in _FALSE_ENV_VALUES:
        return False
    if raw in _TRUE_ENV_VALUES:
        return True
    return True


def _necklace_mcp_enabled() -> bool:
    raw = os.getenv("PAWKEYLAND_ENABLE_AGENT_NECKLACE_MCP", "").strip().lower()
    if raw in _FALSE_ENV_VALUES:
        return False
    if raw in _TRUE_ENV_VALUES:
        return True
    return True


def _memory_mcp_enabled() -> bool:
    raw = _first_env_value(
        "INK_AGENT_ENABLE_MEMORY_MCP",
        "PAWKEYLAND_ENABLE_AGENT_MEMORY_MCP",
    ).lower()
    if raw in _FALSE_ENV_VALUES:
        return False
    if raw in _TRUE_ENV_VALUES:
        return True
    return True


def _pythonpath_with_repo_root() -> str:
    """Return a PYTHONPATH that lets Claude-spawned MCP subprocesses import this repo."""

    repo_root = str(_REPO_ROOT)
    current = os.getenv("PYTHONPATH", "")
    if not current:
        return repo_root
    parts = [item for item in current.split(os.pathsep) if item]
    if repo_root in parts:
        return current
    return os.pathsep.join([repo_root, *parts])


def _stdio_env(
    *,
    extra_env: Optional[dict[str, str]] = None,
    include_memory_config: bool = False,
    include_necklace_config: bool = False,
) -> dict[str, str]:
    env = {
        "PYTHONPATH": _pythonpath_with_repo_root(),
        "PYTHONUNBUFFERED": "1",
    }
    if include_necklace_config:
        for name in _NECKLACE_ENV_NAMES:
            value = os.getenv(name, "")
            if value:
                env[name] = value
    if include_memory_config:
        for canonical_name, legacy_name in _MEMORY_ENV_ALIASES:
            value = _first_env_value(canonical_name, legacy_name)
            if value:
                _set_env_aliases(env, canonical_name, legacy_name, value)
    for key, value in (extra_env or {}).items():
        if value is not None:
            env[str(key)] = str(value)
    return env


def _user_mcp_stdio_config() -> McpStdioServerConfig:
    """Build the external stdio MCP config for the user animation tool server."""

    return McpStdioServerConfig(
        type="stdio",
        command=sys.executable,
        args=["-m", "libs.claude_agent_kit.server.user_mcp_stdio"],
        env=_stdio_env(),
    )


def _necklace_mcp_stdio_config(extra_env: Optional[dict[str, str]] = None) -> McpStdioServerConfig:
    """Build the external stdio MCP config for the necklace live-context server."""

    return McpStdioServerConfig(
        type="stdio",
        command=sys.executable,
        args=["-m", "libs.claude_agent_kit.server.necklace_mcp_stdio"],
        env=_stdio_env(extra_env=extra_env, include_necklace_config=True),
    )


def _memory_mcp_stdio_config(extra_env: Optional[dict[str, str]] = None) -> McpStdioServerConfig:
    """Build the external stdio MCP config for the Mem0 shared-story server."""

    return McpStdioServerConfig(
        type="stdio",
        command=sys.executable,
        args=["-m", "libs.claude_agent_kit.server.memory_mcp_stdio"],
        env=_stdio_env(extra_env=extra_env, include_memory_config=True),
    )


def _editor_mcp_stdio_config() -> McpStdioServerConfig:
    """Build the external stdio MCP config for the EditorState write-only server.

    Session context (session_id) is supplied by the Claude agent at tool-call
    time — the agent reads it from the ``<workspace_context>`` prompt block and
    includes it as a required argument in every write tool call.  No session
    data needs to be injected into the subprocess environment here.
    """
    return McpStdioServerConfig(
        type="stdio",
        command=sys.executable,
        args=["-m", "libs.claude_agent_kit.server.editor_mcp_stdio"],
        env=_stdio_env(),
    )


# ---------------------------------------------------------------------------
# .editor/ virtual index redirect helper
# ---------------------------------------------------------------------------


def _apply_editor_index_redirect(
    tool_name: str,
    tool_input: dict[str, Any],
    editor_state: Optional[dict[str, Any]],
    tmp_paths: list[str],
) -> Optional[HookJSONOutput]:
    """Apply `.editor/` virtual-index redirect for a PreToolUse Read call.

    Returns a :class:`HookJSONOutput` whose ``updatedInput`` points to a freshly
    written tempfile when all three conditions are satisfied:

    1. ``tool_name == "Read"``
    2. ``editor_state`` is not ``None``
    3. The ``file_path`` input targets a recognised ``.editor/`` resource

    Returns ``None`` when any condition is not met (fall-through).

    Side effects:
    - On success, appends the tempfile path to *tmp_paths* so the caller can
      clean it up in a ``finally`` block.

    On any exception the error is logged at WARNING level and ``None`` is
    returned so the caller falls through to the unmodified read path (the
    agent sees the on-disk placeholder ``{}``).

    This function is module-level so it can be tested in isolation without
    running a real Claude Code SDK subprocess.

    Design reference: ``docs/design/claude-agent/edit-point/workspace-adapter.md``
    §4.2 Interception conditions, §4.3 Interception flow.
    """
    if tool_name != "Read" or editor_state is None:
        return None

    raw_path: str = tool_input.get("file_path", "")

    try:
        from .editor_index import is_editor_index_path, get_editor_resource_data  # noqa: PLC0415

        if not is_editor_index_path(raw_path):
            return None

        resource_data = get_editor_resource_data(raw_path, editor_state)
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            prefix="editor_",
            encoding="utf-8",
        ) as tmp:
            json.dump(resource_data, tmp, ensure_ascii=False)
            tmp_path = tmp.name

        tmp_paths.append(tmp_path)
        logger.debug(
            "PreToolUse: redirected .editor read %r → %r",
            raw_path,
            tmp_path,
        )
        return HookJSONOutput(
            hookSpecificOutput={
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "updatedInput": {"file_path": tmp_path},
            }
        )
    except Exception:  # noqa: BLE001
        logger.warning(
            "Failed to intercept .editor/ read for %r; falling through.",
            raw_path,
            exc_info=True,
        )
        return None


# ---------------------------------------------------------------------------
# Async helper
# ---------------------------------------------------------------------------


async def _call(fn: Optional[Callable[..., Any]], *args: Any) -> None:
    """Invoke *fn* with *args*, awaiting it if it returns a coroutine."""
    if fn is None:
        return
    result = fn(*args)
    if inspect.isawaitable(result):
        await result


async def _await_confirmation(
    callback: Callable[..., Any],
    payload: dict[str, Any],
    *,
    host_loop: Optional[asyncio.AbstractEventLoop],
) -> Optional[dict[str, Any]]:
    """Run a tool-confirmation callback on the host (FastAPI) event loop.

    The Claude Code SDK invokes PreToolUse hooks from a control-protocol task
    inside its anyio TaskGroup. Today that task runs on the same loop as
    ``run_streaming``, so a direct ``await`` is fine. Future SDK changes (or
    custom transports) may move hook dispatch to a worker thread or a sub-loop;
    in those cases we must hop back to the loop that owns the
    ToolConfirmationStore Future before awaiting it, otherwise the FastAPI
    worker is starved while the confirmation Future is unreachable.

    The bridge stays on the same loop when caller and host already match, so
    auto-mode and existing tests pay no cost.
    """

    raw = callback(payload)

    if not inspect.isawaitable(raw):
        return raw  # type: ignore[return-value]

    coro = raw  # An awaitable; usually a coroutine

    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        running_loop = None

    if host_loop is None or running_loop is host_loop:
        return await coro  # type: ignore[no-any-return]

    if not host_loop.is_running():
        # The host loop disappeared (server shutdown). Best-effort: drop the
        # awaitable and let the caller fall through to the default deny path.
        if hasattr(coro, "close"):
            try:
                coro.close()  # type: ignore[union-attr]
            except Exception:  # noqa: BLE001
                pass
        return None

    future = asyncio.run_coroutine_threadsafe(coro, host_loop)  # type: ignore[arg-type]
    try:
        return await asyncio.wrap_future(future)
    except asyncio.CancelledError:
        future.cancel()
        raise


def _block_value(block: Any, key: str, default: Any = None) -> Any:
    """Read a content-block field from SDK objects or raw dict blocks."""

    if isinstance(block, dict):
        return block.get(key, default)
    return getattr(block, key, default)


def _block_type(block: Any) -> Optional[str]:
    """Infer SDK content-block type from dict fields or SDK class names."""

    explicit = _block_value(block, "type")
    if isinstance(explicit, str) and explicit:
        return explicit

    block_name = type(block).__name__
    if block_name == "TextBlock":
        return "text"
    if block_name == "ThinkingBlock":
        return "thinking"
    if block_name == "ToolUseBlock":
        return "tool_use"
    if block_name == "ToolResultBlock":
        return "tool_result"
    return None


def _maybe_json(value: str) -> Any:
    text = str(value or "").strip()
    if not text:
        return value
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def _normalize_tool_result_output(content: Any) -> Any:
    """Return tool_result content in the most useful SSE shape.

    Claude Code may surface MCP results as SDK block objects or raw dicts. For
    JSON text results, parse to a dict so the frontend can inspect fields
    without re-parsing a text blob.
    """

    if isinstance(content, str):
        return _maybe_json(content)
    if not isinstance(content, list):
        return content

    text_parts: list[str] = []
    for item in content:
        if _block_type(item) == "text":
            text = _block_value(item, "text", "")
            if isinstance(text, str):
                text_parts.append(text)

    if text_parts:
        combined = "".join(text_parts).strip()
        return _maybe_json(combined)
    return content


# ---------------------------------------------------------------------------
# ClaudeAgentRunner
# ---------------------------------------------------------------------------


class ClaudeAgentRunner:
    """Unified streaming runner for the Claude Agent SDK.

    Maps to TypeScript ``ClaudeAgentRunner`` in agent-runner.ts.
    """

    def __init__(self, sdk_client: Optional[IClaudeAgentSDKClient] = None) -> None:
        self._sdk_client: IClaudeAgentSDKClient = (
            sdk_client or SimpleClaudeAgentSDKClient()
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_streaming(
        self,
        opts: AgentRunOptions,
        callbacks: AgentStreamingCallbacks,
    ) -> AgentRunResult:
        """Run the agent and deliver events via *callbacks*.

        Maps to TypeScript ``runStreaming``.
        """
        thread_id = opts.thread_id
        user_message = opts.user_message
        resume = opts.resume
        model = opts.model
        cwd = opts.cwd
        max_turns = opts.max_turns
        allowed_tools = (
            list(opts.allowed_tools)
            if opts.allowed_tools is not None
            else _default_allowed_tools()
        )
        tool_choice: ToolChoiceMode = opts.tool_choice
        system_prompt = opts.system_prompt
        mcp_env = dict(opts.mcp_env or {})
        turn_runtime = dict(opts.turn_runtime or {})

        include_partial_messages = True

        # Accumulators
        messages: list[Any] = []
        text_parts: list[str] = []
        # Initialise to None so that a run that fails before the SDK emits any
        # ResultMessage does not return the conversation_id as the session_id.
        # If the run succeeds the SDK always emits a ResultMessage whose
        # session_id is a real UUID, which overwrites this value below.
        current_session_id: Optional[str] = None
        success = True
        run_error: Optional[Exception] = None
        usage: dict[str, Optional[int]] = {}

        # Pending tool-call tracker (tool_call_id → {tool_name, input})
        pending_tool_calls: dict[str, dict[str, Any]] = {}
        emitted_tool_input_ids: set[str] = set()
        # Streaming tool-call tracker keyed by content block index. Claude
        # streams tool arguments as input_json_delta chunks after an initially
        # empty content_block_start; emit one complete tool event at block stop.
        pending_stream_tools: dict[int, dict[str, Any]] = {}
        pending_stream_thinking: dict[int, dict[str, Any]] = {}

        # Build user message content blocks for the SDK.
        # When the caller (e.g. ClaudeAgentContextBuilder.build_user_message) has
        # already produced a list of content blocks, use them directly.
        # For plain-string messages (e.g. in tests) wrap the text in a single block.
        if isinstance(user_message, list):
            user_msg_content = user_message
        else:
            user_msg_content = [{"type": "text", "text": user_message}]
        user_msg_dict: dict[str, Any] = {
            "type": "user",
            "uuid": str(uuid4()),
            "session_id": thread_id,
            "parent_tool_use_id": None,
            "message": {
                "role": "user",
                "content": user_msg_content,
            },
        }

        # Disable all tools when tool_choice == "none"
        effective_allowed_tools = [] if tool_choice == "none" else allowed_tools

        async def _generate_messages():
            yield user_msg_dict

        # ------------------------------------------------------------------
        # PreToolUse hook
        # Fired by the SDK before tool execution. Auto mode returns immediately
        # so animation and necklace tools remain agent-autonomous; manual mode
        # uses the frontend confirmation side-channel.
        #
        # Loop / thread contract (manual mode)
        # -----------------------------------
        # Capture the FastAPI worker loop here, while ``run_streaming`` is
        # still on the awaiting coroutine. Whatever loop or thread the SDK
        # later uses to dispatch the hook, we must run the application's
        # ``on_tool_confirmation_request`` coroutine on this loop so the
        # ToolConfirmationStore Future that gets registered is owned by it.
        # That keeps ``POST /api/claude-agent/tool-confirm`` resolvable from
        # the same loop and prevents the worker from being blocked by a
        # cross-loop wakeup.
        # ------------------------------------------------------------------
        try:
            host_loop: Optional[asyncio.AbstractEventLoop] = (
                asyncio.get_running_loop()
            )
        except RuntimeError:  # pragma: no cover — run_streaming is async
            host_loop = None

        # Collects paths of per-read tempfiles created by the .editor/ redirect
        # logic inside _pre_tool_use_hook. Cleaned up in the finally block.
        _editor_redirect_tmp_paths: list[str] = []

        async def _pre_tool_use_hook(
            hook_input: dict[str, Any],
            tool_use_id: Optional[str],
            context: HookContext,
        ) -> HookJSONOutput:
            del context
            tool_name = str(hook_input.get("tool_name") or "")
            tool_input: dict[str, Any] = hook_input.get("tool_input") or {}
            tool_call_id = tool_use_id or str(uuid4())
            pending_tool_calls[tool_call_id] = {
                "tool_name": tool_name,
                "input": tool_input,
            }

            # ----------------------------------------------------------
            # .editor/ virtual index interception (Read tool only)
            # When the agent reads a file under .editor/, redirect to a
            # tempfile populated with live editor_state data so the agent
            # gets real content instead of the placeholder `{}`.
            # This must run before the tool_choice / manual-confirm checks
            # so virtual-index reads are always served in all modes.
            # Delegated to the module-level _apply_editor_index_redirect
            # helper so it can be unit-tested without a real SDK subprocess.
            # ----------------------------------------------------------
            redirect_result = _apply_editor_index_redirect(
                tool_name, tool_input, opts.editor_state, _editor_redirect_tmp_paths
            )
            if redirect_result is not None:
                return redirect_result

            # In auto mode, let all tools run immediately EXCEPT
            # _ALWAYS_CONFIRM_TOOL_NAMES (AskUserQuestion and equivalents).
            # Those must collect user answers through the frontend form before
            # the SDK executes them, so they fall through to the confirmation path.
            if tool_choice != "manual" and tool_name not in _ALWAYS_CONFIRM_TOOL_NAMES:
                return HookJSONOutput()

            if callbacks.on_tool_confirmation_request:
                confirmation_payload = {
                    "tool_call_id": tool_call_id,
                    "tool_name": tool_name,
                    "input": tool_input,
                }
                try:
                    confirmation_result = await _await_confirmation(
                        callbacks.on_tool_confirmation_request,
                        confirmation_payload,
                        host_loop=host_loop,
                    )
                except asyncio.CancelledError:
                    pending_tool_calls.pop(tool_call_id, None)
                    raise
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "Tool confirmation callback failed: tool_call_id=%s tool_name=%s",
                        tool_call_id,
                        tool_name,
                    )
                    pending_tool_calls.pop(tool_call_id, None)
                    return HookJSONOutput(
                        hookSpecificOutput={
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": "工具确认回调异常",
                        }
                    )

                if (
                    confirmation_result
                    and isinstance(confirmation_result, dict)
                    and "approved" in confirmation_result
                ):
                    if confirmation_result["approved"] is True:
                        pending_tool_calls.pop(tool_call_id, None)
                        updated_input: dict[str, Any] = tool_input

                        # For AskUserQuestion-style tools, merge answers with the
                        # full original input so Claude sees the complete context.
                        # Supports both the classic Q&A format
                        #   { questions: [...], answers: {...} }
                        # and the animation event format
                        #   { act, duration, interaction, answers: {...} }
                        # (defined in docs/app/design/LLM驱动动画事件图设计方案.md)
                        # Note: tool_input originates from Claude (LLM-generated),
                        # not from external HTTP requests, so spreading it is safe.
                        has_answers = bool(confirmation_result.get("answers"))
                        if has_answers and tool_name in (
                            "AskUserQuestion",
                            "mcp__user__ask_user",
                            # Animation event tool — merge frontend answers per §9.5
                            "mcp__user__touch_animation",
                        ):
                            updated_input = {
                                **tool_input,
                                "answers": confirmation_result["answers"],
                            }
                            # CLI ≥ 2.1 expects the PreToolUse hookSpecificOutput
                            # shape: hookEventName + permissionDecision:"allow" +
                            # updatedInput (the old {"tool_input": ...} key is no
                            # longer recognised and causes the override to be silently
                            # ignored, leaving AskUserQuestion without answers and
                            # returning isError:true / output:null).
                            return HookJSONOutput(
                                hookSpecificOutput={
                                    "hookEventName": "PreToolUse",
                                    "permissionDecision": "allow",
                                    "updatedInput": updated_input,
                                }
                            )

                        return HookJSONOutput()

                    if confirmation_result["approved"] is False:
                        pending_tool_calls.pop(tool_call_id, None)
                        reason = (
                            confirmation_result.get("reason")
                            or "用户拒绝执行该工具"
                        )
                        return HookJSONOutput(
                            hookSpecificOutput={
                                "hookEventName": "PreToolUse",
                                "permissionDecision": "deny",
                                "permissionDecisionReason": reason,
                            }
                        )

            # No callback or no result — deny by default
            pending_tool_calls.pop(tool_call_id, None)
            return HookJSONOutput(
                hookSpecificOutput={
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "需要用户确认但未收到响应",
                }
            )

        # ------------------------------------------------------------------
        # Build SDK options
        # ------------------------------------------------------------------
        mcp_servers: dict[str, McpServerConfig] = {}
        if _user_mcp_enabled() and any(
            tool.startswith(_USER_MCP_TOOL_PREFIX) for tool in effective_allowed_tools
        ):
            # Use an external stdio MCP process instead of SDK in-process MCP.
            # The Python SDK multiplexes prompt input, permission responses, and
            # SDK MCP messages over the Claude CLI stdin stream; once the prompt
            # reaches EOF, later control writes can fail with
            # "ProcessTransport is not ready for writing".  Stdio MCP gives the
            # tool protocol its own child-process stdin/stdout.
            mcp_servers["user"] = _user_mcp_stdio_config()
        if _memory_mcp_enabled() and any(
            tool.startswith(_MEMORY_MCP_TOOL_PREFIX) for tool in effective_allowed_tools
        ):
            mcp_servers["memory"] = _memory_mcp_stdio_config(mcp_env)
        if _necklace_mcp_enabled() and any(
            tool.startswith(_NECKLACE_MCP_TOOL_PREFIX) for tool in effective_allowed_tools
        ):
            mcp_servers["necklace"] = _necklace_mcp_stdio_config(mcp_env)

        # Start the editor MCP subprocess when editor_state is active and at least one
        # write tool is in the effective allowlist.  Session context (session_id) flows
        # through the MCP protocol: the agent reads it from <workspace_context> and
        # passes it as a required argument in every write tool call — no env-var injection.
        if (
            opts.editor_state is not None
            and any(
                tool.startswith(_EDITOR_MCP_TOOL_PREFIX) for tool in effective_allowed_tools
            )
        ):
            mcp_servers["editor"] = _editor_mcp_stdio_config()
            logger.debug("Editor MCP enabled; session context flows via tool arguments.")

        _stderr_buf = tempfile.TemporaryFile()
        sdk_options = apply_project_sdk_runtime_options(
            ClaudeCodeOptions(
                max_turns=max_turns,
                allowed_tools=effective_allowed_tools,
                include_partial_messages=include_partial_messages,
                hooks={
                    "PreToolUse": [HookMatcher(matcher=None, hooks=[_pre_tool_use_hook])]
                },
                cwd=cwd or os.getcwd(),
                mcp_servers=mcp_servers,
            )
        )
        # Overlay user-scoped SDK env vars (higher priority than backend/.env).
        apply_user_sdk_env_to_options(sdk_options, opts.user_sdk_env or {})
        existing_extra_args = getattr(sdk_options, "extra_args", None)
        sdk_options.extra_args = _StderrSentinelArgs(
            existing_extra_args if existing_extra_args is not None else {}
        )
        if tool_choice == "none":
            sdk_options.extra_args["tools"] = ""
        sdk_options.debug_stderr = _stderr_buf
        if resume:
            sdk_options.resume = thread_id
        _apply_request_model_override_if_allowed(sdk_options, model)
        if system_prompt:
            sdk_options.system_prompt = system_prompt
        # ------------------------------------------------------------------
        # Stream processing
        # ------------------------------------------------------------------
        def _accumulate(delta: str) -> None:
            text_parts.append(delta)

        try:
            _inject_mem0_session_hook_env(sdk_options, mcp_env)
            _verify_claude_sdk_env_for_query_stream(sdk_options)
            async for message in self._sdk_client.query_stream(
                _generate_messages(), sdk_options
            ):
                messages.append(message)

                # Track session ID
                if isinstance(message, (ResultMessage, StreamEvent)):
                    if message.session_id:
                        current_session_id = message.session_id
                elif isinstance(message, SystemMessage):
                    sid = (message.data or {}).get("session_id")
                    if sid:
                        current_session_id = sid

                # Raw message callback
                await _call(callbacks.on_message, message)

                # Route to typed handler
                await self._process_message(
                    message=message,
                    callbacks=callbacks,
                    pending_tool_calls=pending_tool_calls,
                    emitted_tool_input_ids=emitted_tool_input_ids,
                    pending_stream_tools=pending_stream_tools,
                    pending_stream_thinking=pending_stream_thinking,
                    on_text_accumulate=_accumulate,
                    include_partial_messages=include_partial_messages,
                    usage_accumulator=usage,
                )

            full_text = "".join(text_parts)

            if full_text and callbacks.on_text_done:
                await _call(callbacks.on_text_done, full_text)

        except BaseException as exc:  # noqa: BLE001
            # ----------------------------------------------------------
            # Why ``except BaseException`` (not ``except Exception``)
            # ----------------------------------------------------------
            # ``ClaudeSDKClient`` runs its CLI subprocess + control
            # protocol inside an ``anyio.TaskGroup``.  When the CLI exits
            # non-zero, the message-reader task raises a plain
            # ``Exception`` (the SDK reshapes ``ProcessError`` into a
            # synthetic ``{"type":"error"}`` stream message; see
            # ``claude_code_sdk._internal.query.Query._read_messages`` —
            # the same place that emits the visible
            # ``ERROR Fatal error in message reader: Command failed with
            # exit code 1`` log line).  As that failure unwinds, the
            # ``async with ClaudeSDKClient(...)`` ``__aexit__`` cancels
            # the still-running write / control sibling tasks, which
            # raise ``CancelledError`` — and the TaskGroup packages the
            # original ``Exception`` together with the sibling
            # ``CancelledError`` instances into a ``BaseExceptionGroup``.
            # ``BaseExceptionGroup`` is *not* an ``Exception`` subclass,
            # so a plain ``except Exception`` silently lets the failure
            # propagate past the runner: ``callbacks.on_error`` never
            # fires, ``success`` keeps its default ``True``, and the
            # caller sees a half-finished stream with no error frame.
            # We catch ``BaseException`` and use ``_is_pure_cancellation``
            # to re-raise only the genuine cancel cases (FastAPI
            # shutdown, client disconnect, explicit ``task.cancel()``)
            # while routing the typical CLI-failure-plus-sibling-cancel
            # group through the normal ``on_error`` path.
            # ----------------------------------------------------------
            if _is_pure_cancellation(exc):
                raise
            success = False
            stderr_snippet = ""
            try:
                _stderr_buf.seek(0)
                stderr_snippet = (
                    _stderr_buf.read(8192)
                    .decode("utf-8", errors="replace")
                    .strip()
                )
            except Exception:  # noqa: BLE001
                pass
            # ----------------------------------------------------------
            # SDK-side diagnostic enrichment.
            #
            # claude_code_sdk's ``Query._read_messages`` catches the
            # original ``ProcessError`` from the CLI subprocess and
            # forwards only ``str(e)`` through its in-process message
            # stream — every structured field (``exit_code`` / actual
            # ``stderr`` / which session was being resumed) is dropped
            # before the consumer chain re-raises ``Exception(str(e))``.
            # By the time we reach this except block we have only a
            # generic "Command failed with exit code 1" string and no
            # way to tell which run it came from.
            #
            # Two-pronged enrichment that *preserves* the original
            # exception type so downstream ``isinstance`` checks keep
            # working:
            #   * ``run_error.__notes__`` (PEP 678) carries the SDK-call
            #     context as a structured note, visible in formatted
            #     tracebacks and accessible via ``getattr(exc, '__notes__', [])``.
            #   * a logger.exception emits the same fields as a structured
            #     log line plus traceback so backend logs can correlate the
            #     failure with a specific session / cwd / model without grepping.
            # ExceptionGroup *and* BaseExceptionGroup are both re-wrapped
            # (into a plain Exception carrying the joined leaf messages),
            # because exception groups are rarely useful to downstream
            # typed handlers and their default ``str()`` is unreadable.
            # The ``isinstance(exc, _BASE_EXCEPTION_GROUP_TYPES)`` test
            # also covers ``ExceptionGroup`` because PEP 654 makes it a
            # subclass of ``BaseExceptionGroup``.
            # Bare ``BaseException`` leaves that are *not* a cancellation
            # (e.g. ``KeyboardInterrupt`` / ``SystemExit``) are also
            # wrapped so SSE serialisation and ``isinstance(_, Exception)``
            # consumers downstream do not choke on them.
            # ----------------------------------------------------------
            if _BASE_EXCEPTION_GROUP_TYPES and isinstance(
                exc, _BASE_EXCEPTION_GROUP_TYPES
            ):
                run_error = Exception(_format_exception_message(exc))
            elif isinstance(exc, Exception):
                run_error = exc
            else:
                run_error = Exception(_format_exception_message(exc))
            ctx_note = (
                f"[claude_agent_kit] sdk_call_context: "
                f"resume={resume} thread_id={thread_id or 'None'} "
                f"cwd={cwd or 'None'} model={model or 'default'}"
            )
            try:
                run_error.add_note(ctx_note)
                if stderr_snippet:
                    run_error.add_note(f"[claude_agent_kit] cli_stderr: {stderr_snippet}")
            except AttributeError:
                # PEP 678 add_note requires Python 3.11+; ignore on older runtimes.
                pass
            logger.exception(
                "Claude SDK run failed: error_type=%s error=%r resume=%s "
                "thread_id=%s cwd=%s model=%s stderr_snippet=%s",
                type(run_error).__name__,
                str(run_error),
                resume,
                thread_id or None,
                cwd or None,
                model or None,
                stderr_snippet or None,
            )
            await _call(callbacks.on_error, run_error)
            full_text = "".join(text_parts)
        finally:
            try:
                _stderr_buf.close()
            except Exception:  # noqa: BLE001
                pass
            # Clean up per-read .editor/ redirect tempfiles.
            for _rpath in _editor_redirect_tmp_paths:
                try:
                    os.unlink(_rpath)
                except Exception:  # noqa: BLE001
                    pass
        return AgentRunResult(
            full_text=full_text,  # type: ignore[possibly-undefined]
            session_id=current_session_id,
            success=success,
            error=run_error,
            messages=messages,
            usage=(
                usage
                if (usage.get("input_tokens") or usage.get("output_tokens"))
                else None
            ),
        )

    async def load_messages(self, session_id: str) -> list[Any]:
        """Load message history for a session.

        Maps to TypeScript ``loadMessages``.
        """
        result = await self._sdk_client.load_messages(session_id)
        return result["messages"]

    # ------------------------------------------------------------------
    # Internal message-processing dispatcher
    # ------------------------------------------------------------------

    async def _process_message(
        self,
        message: Any,
        callbacks: AgentStreamingCallbacks,
        pending_tool_calls: dict[str, dict[str, Any]],
        emitted_tool_input_ids: set[str],
        on_text_accumulate: Callable[[str], None],
        include_partial_messages: bool = False,
        usage_accumulator: Optional[dict[str, Optional[int]]] = None,
        pending_stream_tools: Optional[dict[int, dict[str, Any]]] = None,
        pending_stream_thinking: Optional[dict[int, dict[str, Any]]] = None,
    ) -> None:
        """Dispatch a single SDK message to the appropriate callback(s).

        Maps to TypeScript ``processMessage`` (private method).
        """
        if usage_accumulator is None:
            usage_accumulator = {}

        # ------------------------------------------------------------------
        # assistant message — full content snapshot
        # ------------------------------------------------------------------
        if isinstance(message, AssistantMessage):
            content = message.content or []
            if isinstance(content, list):
                for block in content:
                    block_type = _block_type(block)

                    if block_type == "text":
                        # When include_partial_messages is on, text was already
                        # delivered via stream_event text_deltas — skip to avoid
                        # duplicating output.
                        if not include_partial_messages:
                            text = _block_value(block, "text", "")
                            if isinstance(text, str):
                                on_text_accumulate(text)
                                await _call(callbacks.on_text_delta, text)

                    elif block_type == "thinking":
                        thinking = _block_value(block, "thinking")
                        if isinstance(thinking, str) and callbacks.on_tool_event:
                            await _call(
                                callbacks.on_tool_event,
                                ToolEventPayload(type="thinking", output=thinking),
                            )

                    elif block_type == "tool_use":
                        tool_call_id = _block_value(block, "id")
                        tool_name = _block_value(block, "name")
                        tool_input = _block_value(block, "input", {}) or {}
                        if include_partial_messages and tool_call_id in emitted_tool_input_ids:
                            continue
                        if not include_partial_messages or tool_call_id:
                            if callbacks.on_tool_event:
                                await _call(
                                    callbacks.on_tool_event,
                                    ToolEventPayload(
                                        type="tool_use",
                                        tool_name=tool_name,
                                        tool_call_id=tool_call_id,
                                        input=tool_input,
                                    ),
                                )

            elif isinstance(content, str):
                if not include_partial_messages:
                    on_text_accumulate(content)
                    await _call(callbacks.on_text_delta, content)

        # ------------------------------------------------------------------
        # stream_event — incremental SSE events
        # See docs/app/design/Claude SDK Message 事件类型层级.md for full taxonomy.
        # ------------------------------------------------------------------
        elif isinstance(message, StreamEvent):
            event: dict[str, Any] = message.event or {}
            event_type = event.get("type", "")

            if event_type == "content_block_delta":
                delta = event.get("delta") or {}
                delta_type = delta.get("type", "")

                if delta_type == "text_delta":
                    text = delta.get("text", "")
                    if isinstance(text, str):
                        on_text_accumulate(text)
                        await _call(callbacks.on_text_delta, text)

                elif delta_type == "thinking_delta":
                    block_index = event.get("index")
                    thinking_text = delta.get("thinking")
                    if thinking_text is None:
                        thinking_text = delta.get("text", "")
                    active_thinking: Optional[dict[str, Any]] = None
                    if (
                        pending_stream_thinking is not None
                        and isinstance(block_index, int)
                    ):
                        active_thinking = pending_stream_thinking.setdefault(
                            block_index,
                            {"parts": [], "signature": ""},
                        )
                    if isinstance(thinking_text, str) and callbacks.on_tool_event:
                        if active_thinking is not None:
                            # Keep SDK text chunks as Python str values; no byte
                            # slicing/decoding means multibyte characters remain
                            # intact across delta boundaries.
                            active_thinking.setdefault("parts", []).append(
                                thinking_text
                            )
                        await _call(
                            callbacks.on_tool_event,
                            ToolEventPayload(
                                type="thinking_delta", output=thinking_text
                            ),
                        )

                elif delta_type == "signature_delta":
                    block_index = event.get("index")
                    signature = delta.get("signature")
                    if (
                        isinstance(signature, str)
                        and pending_stream_thinking is not None
                        and isinstance(block_index, int)
                    ):
                        active_thinking = pending_stream_thinking.setdefault(
                            block_index,
                            {"parts": [], "signature": ""},
                        )
                        # signature_delta is block metadata, not display text.
                        # If repeated, the latest complete signature wins.
                        active_thinking["signature"] = signature

                elif delta_type == "input_json_delta":
                    block_index = event.get("index")
                    partial_json = delta.get("partial_json") or ""
                    active_tool: Optional[dict[str, Any]] = None
                    if (
                        pending_stream_tools is not None
                        and isinstance(block_index, int)
                        and block_index in pending_stream_tools
                    ):
                        active_tool = pending_stream_tools[block_index]
                        active_tool.setdefault("parts", []).append(partial_json)

                    if callbacks.on_tool_event:
                        await _call(
                            callbacks.on_tool_event,
                            ToolEventPayload(
                                type="tool_input_delta",
                                tool_name=(
                                    active_tool.get("name")
                                    if active_tool
                                    else None
                                ),
                                tool_call_id=(
                                    active_tool.get("id")
                                    if active_tool
                                    else None
                                ),
                                output=partial_json,
                            ),
                        )

            elif event_type == "content_block_start":
                content_block = event.get("content_block") or {}
                cb_type = content_block.get("type", "")

                if cb_type == "tool_use":
                    tool_call_id = content_block.get("id")
                    tool_name = content_block.get("name")
                    block_index = event.get("index")
                    if (
                        pending_stream_tools is not None
                        and isinstance(block_index, int)
                        and tool_call_id
                        and tool_name
                    ):
                        pending_stream_tools[block_index] = {
                            "id": tool_call_id,
                            "name": tool_name,
                            "parts": [],
                        }
                    elif callbacks.on_tool_event:
                        await _call(
                            callbacks.on_tool_event,
                            ToolEventPayload(
                                type="tool_use_start",
                                tool_name=tool_name,
                                tool_call_id=tool_call_id,
                                input={},
                                state=None,
                            ),
                        )

                elif cb_type == "text" and callbacks.on_tool_event:
                    await _call(
                        callbacks.on_tool_event,
                        ToolEventPayload(
                            type="text_block_start",
                            output={"index": event.get("index")},
                        ),
                    )

                elif cb_type == "thinking":
                    block_index = event.get("index")
                    thinking = content_block.get("thinking")
                    signature = content_block.get("signature")
                    if (
                        pending_stream_thinking is not None
                        and isinstance(block_index, int)
                    ):
                        pending_stream_thinking[block_index] = {
                            "parts": (
                                [thinking]
                                if isinstance(thinking, str) and thinking
                                else []
                            ),
                            "signature": (
                                signature if isinstance(signature, str) else ""
                            ),
                        }
                    if (
                        isinstance(thinking, str)
                        and thinking
                        and callbacks.on_tool_event
                    ):
                        await _call(
                            callbacks.on_tool_event,
                            ToolEventPayload(
                                type="thinking_delta", output=thinking
                            ),
                        )

            elif event_type == "content_block_stop":
                block_index = event.get("index")
                active_tool = (
                    pending_stream_tools.pop(block_index, None)
                    if pending_stream_tools is not None and isinstance(block_index, int)
                    else None
                )
                if active_tool and callbacks.on_tool_event:
                    input_json = "".join(active_tool.get("parts") or [])
                    try:
                        parsed_input: dict[str, Any] = (
                            json.loads(input_json) if input_json else {}
                        )
                        if not isinstance(parsed_input, dict):
                            parsed_input = {"_raw_input_json": input_json}
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(
                            "content_block_stop: failed to parse tool input JSON "
                            "for block %s (tool=%s): %r",
                            block_index,
                            active_tool.get("name"),
                            input_json,
                        )
                        parsed_input = {"_raw_input_json": input_json}

                    tool_call_id = active_tool.get("id")
                    tool_name = active_tool.get("name")
                    if tool_call_id:
                        pending_tool_calls[tool_call_id] = {
                            "tool_name": tool_name,
                            "input": parsed_input,
                        }
                        emitted_tool_input_ids.add(tool_call_id)
                    if tool_call_id and tool_name:
                        await _call(
                            callbacks.on_tool_event,
                            ToolEventPayload(
                                type="tool_input_available",
                                tool_name=tool_name,
                                tool_call_id=tool_call_id,
                                input=parsed_input,
                                state="input-available",
                            ),
                        )

                active_thinking = (
                    pending_stream_thinking.pop(block_index, None)
                    if pending_stream_thinking is not None and isinstance(block_index, int)
                    else None
                )
                stop_output: dict[str, Any] = {"index": event.get("index")}
                if active_thinking:
                    stop_output["content_block"] = {
                        "type": "thinking",
                        "thinking": "".join(active_thinking.get("parts") or []),
                        "signature": active_thinking.get("signature") or "",
                    }

                if callbacks.on_tool_event:
                    await _call(
                        callbacks.on_tool_event,
                        ToolEventPayload(
                            type="content_block_stop",
                            output=stop_output,
                        ),
                    )

            elif event_type == "message_start":
                msg_meta = event.get("message") or {}
                msg_usage = msg_meta.get("usage") or {}
                if msg_usage.get("input_tokens"):
                    usage_accumulator["input_tokens"] = (
                        usage_accumulator.get("input_tokens") or 0
                    ) + msg_usage["input_tokens"]

                if callbacks.on_tool_event:
                    await _call(
                        callbacks.on_tool_event,
                        ToolEventPayload(
                            type="message_start",
                            output={
                                "model": msg_meta.get("model"),
                                "usage": msg_usage,
                            },
                        ),
                    )

            elif event_type == "message_delta":
                event_usage = event.get("usage") or {}
                if event_usage.get("output_tokens"):
                    usage_accumulator["output_tokens"] = (
                        usage_accumulator.get("output_tokens") or 0
                    ) + event_usage["output_tokens"]

                if callbacks.on_tool_event:
                    delta = event.get("delta") or {}
                    await _call(
                        callbacks.on_tool_event,
                        ToolEventPayload(
                            type="message_delta",
                            output={
                                "stop_reason": delta.get("stop_reason"),
                                "usage": event_usage,
                            },
                            stop_reason=delta.get("stop_reason"),
                        ),
                    )

            elif event_type == "message_stop":
                if callbacks.on_tool_event:
                    await _call(
                        callbacks.on_tool_event, ToolEventPayload(type="message_stop")
                    )

        # ------------------------------------------------------------------
        # result — session end (subtype: success / error)
        # ------------------------------------------------------------------
        elif isinstance(message, ResultMessage):
            # Cumulative usage in the result event overrides stream-level values
            result_usage = message.usage or {}
            if result_usage.get("input_tokens"):
                usage_accumulator["input_tokens"] = result_usage["input_tokens"]
            if result_usage.get("output_tokens"):
                usage_accumulator["output_tokens"] = result_usage["output_tokens"]

            if callbacks.on_tool_event:
                await _call(
                    callbacks.on_tool_event,
                    ToolEventPayload(
                        type="result",
                        output={
                            "subtype": message.subtype,
                            "result": message.result,
                            "is_error": message.is_error,
                            "duration_ms": message.duration_ms,
                            "num_turns": message.num_turns,
                            "total_cost_usd": message.total_cost_usd,
                            "usage": result_usage,
                        },
                        state=(
                            "output-error" if message.is_error else "output-available"
                        ),
                        is_error=message.is_error,
                    ),
                )

        # ------------------------------------------------------------------
        # user message — contains tool_result content blocks
        # ------------------------------------------------------------------
        elif isinstance(message, UserMessage):
            content = message.content
            if isinstance(content, list):
                for block in content:
                    block_type = _block_type(block)
                    if block_type == "tool_result":
                        tool_use_id = _block_value(block, "tool_use_id") or _block_value(
                            block,
                            "toolUseId",
                        )
                        pending_call = (
                            pending_tool_calls.pop(tool_use_id, None)
                            if tool_use_id
                            else None
                        )
                        if callbacks.on_tool_event:
                            is_err = bool(
                                _block_value(
                                    block,
                                    "is_error",
                                    _block_value(block, "isError", False),
                                )
                            )
                            output = _normalize_tool_result_output(
                                _block_value(block, "content")
                            )
                            await _call(
                                callbacks.on_tool_event,
                                ToolEventPayload(
                                    type="tool_result",
                                    tool_name=(
                                        pending_call.get("tool_name")
                                        if pending_call
                                        else None
                                    ),
                                    tool_call_id=tool_use_id,
                                    output=output,
                                    is_error=is_err,
                                    state=(
                                        "output-error"
                                        if is_err
                                        else "output-available"
                                    ),
                                ),
                            )

        # ------------------------------------------------------------------
        # system — init, hook_started, hook_response (informational only)
        # ------------------------------------------------------------------
        elif isinstance(message, SystemMessage):
            pass  # Not streamed to callbacks

        # ------------------------------------------------------------------
        # Fallback for any other message types from the SDK
        # ------------------------------------------------------------------
        else:
            msg_type = getattr(message, "type", type(message).__name__)

            if msg_type == "tool_progress" and callbacks.on_tool_event:
                await _call(
                    callbacks.on_tool_event,
                    ToolEventPayload(
                        type="tool_progress",
                        tool_name=getattr(message, "tool_name", None),
                        tool_call_id=getattr(message, "tool_use_id", None),
                        output={
                            "elapsed_time_seconds": getattr(
                                message, "elapsed_time_seconds", None
                            )
                        },
                    ),
                )

            elif msg_type == "tool_use_summary" and callbacks.on_tool_event:
                await _call(
                    callbacks.on_tool_event,
                    ToolEventPayload(
                        type="tool_use_summary",
                        output={
                            "summary": getattr(message, "summary", None),
                            "preceding_tool_use_ids": getattr(
                                message, "preceding_tool_use_ids", None
                            ),
                        },
                    ),
                )


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------


def create_agent_runner(
    sdk_client: Optional[IClaudeAgentSDKClient] = None,
) -> ClaudeAgentRunner:
    """Create a new :class:`ClaudeAgentRunner` instance.

    Maps to TypeScript ``createAgentRunner``.
    """
    return ClaudeAgentRunner(sdk_client)
