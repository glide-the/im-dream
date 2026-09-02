# [Input] Consume libs/claude_agent_kit/types.py, libs/claude_agent_kit/runner.py,
#         claude_agent/context_builder.py, claude_agent/tool_confirmation_store.py.
#         Reads database module for session persistence.
# [Output] Provide ClaudeAgentRunRequest, ClaudeAgentService to thread_factory.py.
# [Pos] core-business node in backend/claude_agent
# [Sync] 2026-08-28: assemble immutable model/global Claude Code Runtime env snapshots
#                    without reading PostgreSQL from the turn path or changing SSE semantics.
# [Sync] 2026-08-30: resolve the server-owned INK_AGENT_SANDBOX_ENABLED
#                    capability for every full Chat/Dream workspace without
#                    coupling sandbox enablement to Workspace Mode.
# [Sync] 2026-09-01: convert allowlisted Dream workspace identity/schema
#                    failures into one persisted user message and normal resume
#                    continuation; the second Hook failure remains terminal.
# [Sync] 2026-09-01: bind visible auto-repair instructions, persisted metadata,
#                    .dream workbench facts, and Bash cleanup permission to one
#                    freshly revalidated trusted/stale project-root scope.
# [Sync] 2026-09-01: commit every successful Claude logical Turn, including its
#                    reasoning/tool/text parts, before any Dream post-turn Hook;
#                    Hook continuation or failure can no longer erase the reply.
# [Sync] 2026-09-02: persist server-owned turn/final/duration metadata and expose
#                    the same turn identity in live message metadata for history folding.
# [Sync] 2026-09-02: write the strict completed assistant final projection beside
#                    canonical process parts for lightweight history hydration.
# [Sync] 2026-05-22: adapted from Pawkeyland application/claude_agent/service.py.
#                    Removed: pet/persona/mem0/sticker_filter/IdentityService.
#                    Session context provided by ClaudeAgentContextBuilder.
# [Sync] 2026-05-24: align SSE frame format with Pawkeyland protocol:
#                    text-delta.delta (was .text), text-start/end (was text-done),
#                    tool-input-start + tool-input-available + tool-output-available
#                    (was unified tool-event), error.errorText (was .message),
#                    finish.finishReason (was .reason).
# [Sync] 2026-05-24: migrate on_tool_event to Pawkeyland event.type dispatch:
#                    registered_tool_call_ids + emitted_tool_input_ids dedup sets added
#                    to _TurnContext; handles tool_use/tool_use_start, tool_input_available,
#                    tool_result with defensive auto-register fallback.
# [Sync] 2026-05-24: enable thinking mode — migrate thinking_delta/thinking/content_block_stop
#                    branches from Pawkeyland on_tool_event; _TurnContext gains
#                    current_reasoning_id/has_thinking_delta/completed_streamed_reasoning_texts;
#                    emits reasoning-start/delta/end SSE frames.
# [Sync] 2026-05-25: fix tool-invocation persistence for non-streaming AssistantMessage path:
#                    tool_use/tool_use_start now collect tool-input-available SSE event into
#                    collected_parts (superceded by full SSE-event-collection refactor below).
# [Sync] 2026-05-27: _make_tool_confirm_cb: (1) dedup start/available with registered/emitted
#                    sets; (2) idempotent begin_pending — join existing Future on duplicate hook
#                    invocation to prevent immediate-deny via exception path; (3) include answers
#                    in confirmation return dict so Claude receives user responses for AskUserQuestion.
# [Sync] 2026-05-25: align _persist_turn with better-chatbot schema (parts list, NOT NULL):
#                    use new database.save_chat_message(parts=list, metadata=dict) signature;
#                    user message always has parts (text fallback when message_parts is None);
#                    JSON serialisation moved into database layer.
# [Sync] 2026-05-29: pass editor_session_id (extracted from request.editor_state["id"])
#                    to build_user_message so the agent receives it in <workspace_context>
#                    and can pass it as the required first argument to MCP write tool calls.
# [Sync] 2026-05-29: migrate existing_session design from Pawkeyland assemble_context:
#                    load chat_thread to get claude_session_id; gate resume on
#                    _has_usable_claude_resume (contract version check) + local file probe
#                    via locate_session_file; set thread_id_for_agent=None on first turn,
#                    claude_session_id on resume; _persist_turn writes back claude_session_id
#                    + agent_contract_version so DB self-heals across deployments.
#                    Added _AGENT_RUNTIME_CONTRACT_VERSION constant and
#                    _has_usable_claude_resume helper. resume_existing_session added to
#                    _TurnExecution carrier. DB columns claude_session_id /
#                    agent_contract_version added to chat_thread table.
# [Sync] 2026-05-29: move editor_state into AgentRunState flyweight (soft-cache):
#                    assemble_context calls state.with_editor_state() so the snapshot
#                    survives across turns; AgentRunOptions receives state.editor_state
#                    (not raw request.editor_state) via active_editor_state.
#                    editor_state_getter=lambda: state.editor_state injected into
#                    AgentRunOptions so agent_runner._pre_tool_use_hook always reads the
#                    live flyweight value via opts.editor_state_getter().
#                    _make_tool_event_cb gains state param; on tool_result for
#                    _EDITOR_WRITE_TOOL_NAMES it reloads editor_state from DB and updates
#                    state.editor_state — getter propagates change to PreToolUse instantly.
#                    _TurnContext gains tool_name_by_id dict for tool_result name lookup.
# [Sync] 2026-06-06: remove implicit Memory workspace initialization from
#                    assemble_context. Memory is initialized only via the
#                    workspace file interface before agent analysis starts.
# [Sync] 2026-06-09: read system_config.im_full_access_enabled and pass it to
#                    AgentRunOptions so Settings can enable full-access tool approval.
# [Sync] 2026-06-13: read workspace_enabled before cwd resolution and force
#                    Claude Code cwd to the server-owned thread workspace whose
#                    .claude/settings.json carries the sandbox block.
# [Sync] 2026-08-03: Phase 1 (assemble_context) — resolve the per-thread
#                    Claude config home together with cwd establishment
#                    (sdk_env.resolve_claude_config_home), before the resume
#                    transcript probe, Deck plugin pack, and any other claude
#                    module; carried into the runner via
#                    AgentRunOptions.claude_config_home, so CLAUDE_CONFIG_DIR
#                    is no longer decided inside the run_streaming lifecycle.
# [Sync] 2026-08-12: shared Chat/Dream Session persistence now writes the
#                    SDK-native session_id from the existing on_message callback
#                    as soon as the stream exposes it, before Stop/error can
#                    bypass successful-turn persistence. Resume resolution and
#                    claude_session_id semantics remain unchanged.
# [Sync] 2026-08-14: trusted Dream bindings select the Deck workspace-file
#                    prompt in assemble_context; ordinary Chat keeps proposal mode.
# [Sync] 2026-08-22: restore actor-owned Claude MCP definition/credential projection
#                    while retaining the current thread TMPDIR and workspace boundaries.
# [Sync] 2026-08-22: always bind CLAUDE_CODE_TMPDIR to the server-owned thread
#                    runtime workspace; Workspace Mode still exclusively gates
#                    cwd, context injection, sandbox settings, and file surfaces.
# [Sync] 2026-08-22: synchronize authenticated user MCP definitions before each
#                    workspace turn and fail closed when Workspace Mode cannot
#                    protect an existing user MCP credential projection.
# [Sync] 2026-08-25: replace per-turn Claude CLI credential/config synchronization
#                    with the managed PostgreSQL MCP snapshot for both new and
#                    resumed turns; Workspace Mode off still uses only the exact
#                    thread runtime root for the runner's ephemeral 0600 projection.
# [Sync] 2026-06-13: remove assemble_context local database import that shadowed
#                    module-level _db before system_config lookup.
# [Sync] 2026-06-09: P2 fix — split _persist_turn into _persist_user_message (called
#                    before inference), _persist_assistant_turn (called on success),
#                    and _persist_partial_assistant (called on CancelledError/error).
#                    execute_session saves user message immediately so thread-switches
#                    do not lose the user's turn; partial assistant content is flushed
#                    when the SSE stream is cancelled mid-flight.
# [Sync] 2026-06-09: EventBus — assemble_context accepts bus param; BusProxyQueue
#                    adapts IEventBus.publish to _TurnContext.queue.put.
# [Sync] 2026-06-13: forward runner tool_input_delta events as SSE tool-input-delta
#                    frames so frontend can render built-in Write tool terminal
#                    previews while input_json_delta chunks stream.
# [Sync] 2026-06-14: publish Edit Session session_updated events after successful
#                    editor MCP write tool results so the frontend can reload
#                    without a fixed 2000ms wait.
# [Sync] 2026-08-13: normalize structured editor MCP {ok:false} results to
#                    tool errors before live SSE, history persistence, and side effects.
# [Sync] 2026-08-29: unwrap stdio MCP text envelopes, retain tool input identity,
#                    refresh the single AgentRunState cache after every actor/session-
#                    matched Editor result, and publish edit events only on success.
# [Sync] 2026-06-17: include runner exception notes in SSE errorText so sandbox
#                    startup diagnostics (e.g. seccomp-denied hints) reach UI.
# [Sync] 2026-06-21: pass Settings sandbox network policy to workspace init
#                    and AgentRunOptions PreToolUse enforcement.
# [Sync] 2026-06-22: load Settings SYSTEM_PROMPT during Phase 1 via get_system_config,
#                    pass it to ContextBuilder as lower-priority configurable prompt,
#                    and rebuild cached system_prompt when that setting changes.
# [Sync] 2026-06-22: honor Settings Workspace Mode as the workspace lifecycle
#                    gate; when disabled, Phase 1 does not initialize thread
#                    workspace or pass cwd/workspace context to the runner.
# [Sync] 2026-06-25: frontend stop requests cancel the current turn; CancelledError
#                    now flushes partial assistant parts and closes EventBus with finish.
# [Sync] 2026-07-04: materialize connector-owned Notion snapshots into the
#                    workspace-local `.notion/` files before user-message
#                    assembly so workspace_context can read the canonical files.
# [Sync] 2026-07-20: claude-plan — add memory-only PlanState on AgentRunState;
#                    observe tool-input-available for EnterPlanMode/ExitPlanMode
#                    and emit plan-mode-changed (not collected); wire runner
#                    on_plan_file_changed to read the plan file (capped by
#                    INK_AGENT_PLAN_MAX_CONTENT_BYTES) and emit plan-updated
#                    (not collected); add build_thread_plan_payload() REST
#                    helper backed by get_plans_dir().
# [Sync] 2026-07-20: claude-todo — add memory-only TodoState on AgentRunState;
#                    observe tool-input-available for TodoWrite (v1) and emit
#                    todo-updated (not collected, capped by
#                    INK_AGENT_TODO_MAX_ITEMS with truncated:true); wire runner
#                    on_tasks_changed (v2) to the same frame; add
#                    build_thread_todos_payload() REST helper backed by
#                    get_tasks_dir()/read_task_items() with memory fallback.
# [Sync] 2026-07-23: SandboxPermissionRequest — transparently forward
#                    confirmationKind/networkRequest from the runner
#                    confirmation payload onto the SSE tool-approval-request
#                    frame so the frontend can render the network-variant
#                    confirmation card
#                    (claude-agent-sandbox-network-permission-tool.md §5/§5A).
# [Sync] 2026-07-26: drop the AgentRunOptions sandbox_network_allowed_domains
#                    pass-through — the PreToolUse network gate was removed as
#                    wrong-layer duplication; the domains value stays in scope
#                    only for workspace initialization (get_or_create_workspace
#                    → CLI sandbox settings.json).  The confirmationKind /
#                    networkRequest SSE pass-through stays (can_use_tool path).
# [Sync] 2026-07-26: read system_config sandbox_fs_allowed_write_paths and
#                    pass it into get_or_create_workspace so per-thread
#                    settings.json filesystem.allowWrite gains the user's extra
#                    writable paths (mirrors the sandbox_network_allowed_domains
#                    plumbing pattern).
# [Sync] 2026-08-13: assemble a server-scoped DreamArtifactTurnTicket and invoke
#                    the named after-turn Hook only after a successful root turn;
#                    runner/session/SSE entry points remain unchanged.
# [Sync] 2026-08-13: refresh the host-owned Dream workbench context and inject
#                    its validated actual path plus current run/project facts
#                    on every Dream turn.
# [Sync] 2026-08-28: project actor-owned Notion credentials into the current
#                    thread and pass only that private path to the lazy Read hook.
# [Sync] 2026-08-28: consume only actor-agentdata current index snapshots during
#                    Chat assembly and clear stale thread content when projection fails.
# [Sync] 2026-09-01: enable Notion platform builtin Skills only after the
#                    current actor/thread credential projection is available;
#                    common Skills remain owned by workspace initialization.
# [Sync] 2026-09-01: persist and publish one allowlisted Dream auto-repair user
#                    message, then return a normal resume Turn continuation.
# [Sync] 2026-09-01: derive one fresh server-owned stale-project cleanup scope
#                    for the marked repair Turn and pass it only to PreToolUse.

"""Claude Agent Service — core business logic for Ink & Memory.

Responsibilities:
- ``assemble_context``: Phase 1 — build system prompt + run options for the turn.
- ``execute_session``: Phase 3 — stream the agent turn, emit SSE events, persist (optional).

SSE event schema (aligned with Pawkeyland)::

    data: {"type": "message-metadata", "sessionId": "...", "turnIndex": 0}
    data: {"type": "text-start",     "id": "..."}
    data: {"type": "text-delta",     "id": "...", "delta": "..."}
    data: {"type": "text-end",       "id": "..."}
    data: {"type": "tool-input-start",     "toolCallId": "...", "toolName": "..."}
    data: {"type": "tool-input-delta",     "toolCallId": "...", "toolName": "...", "delta": "..."}
    data: {"type": "tool-input-available", "toolCallId": "...", "toolName": "...", "input": {...}}
    data: {"type": "tool-output-available","toolCallId": "...", "output": ..., "isError": false}
    data: {"type": "tool-approval-request","toolCallId": "...", "toolName": "...", "input": {...}}
    data: {"type": "plan-mode-changed", "planMode": "planning"|"exited", "toolCallId": "..."}
    data: {"type": "plan-updated", "slug": "...", "fileName": "...", "content": "...",
           "contentBytes": 1832, "truncated": false, "updatedAt": "..."}
    data: {"type": "todo-updated", "source": "todo_write"|"task_v2", "todos": [...],
           "truncated": false, "updatedAt": "..."}
    data: {"type": "chat-message", "message": {"id": "...", "role": "user",
           "parts": [...], "metadata": {...}}}
    data: {"type": "message-final",  "text": "...", "usage": {...}, "sessionId": "..."}
    data: {"type": "finish",         "finishReason": "stop"|"error"}
    data: {"type": "error",          "errorText": "..."}
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Any, AsyncGenerator, Awaitable, Callable, Mapping, Optional
from uuid import uuid4

import database as _db
from claude_agent.context_builder import ClaudeAgentContextBuilder
from libs.claude_agent_kit.server.agent_runner import ClaudeAgentRunner
from libs.claude_agent_kit.server.sdk_env import resolve_claude_config_home
from claude_agent.thread_pool import AgentRunState
from libs.claude_agent_kit.server.workspace import (
    get_or_create_workspace,
    get_or_create_thread_runtime_workspace,
    get_plans_dir,
    get_tasks_dir,
    get_workspace_root,
    read_task_items,
    resolve_sandbox_enabled,
    sync_builtin_workspace_skills,
    sync_workspace_sandbox_settings,
)
from claude_agent.tool_confirmation_store import (
    ToolConfirmationNotPending,
    ToolConfirmationPolicyConflict,
    ToolConfirmationResolution,
    ToolConfirmationResult,
    ToolConfirmationStore,
)
from libs.claude_agent_kit.messages.build_user_message_content import AttachmentPayload
from libs.claude_agent_kit.messages.message_parts import extract_text_from_parts
from services.story_workspace.agent_integration import (
    get_or_create_default_workspace,
    parse_agent_story_output,
    store_agent_story_output,
)
from services.story_workspace.dream_thread_binding import DreamThreadContextMapper
from services.story_workspace.dream_artifact_turn_hook import (
    DreamArtifactRepairability,
    DreamArtifactTurnHook,
    DreamArtifactTurnHookError,
    DreamArtifactTurnTicket,
)
from services.story_workspace.dream_auto_repair_service import (
    DREAM_AUTO_REPAIR_DISPATCHED,
    DREAM_AUTO_REPAIR_FAILED,
    DREAM_AUTO_REPAIR_METADATA_KIND,
    DreamAutoRepairError,
    DreamAutoRepairExhaustedError,
    build_dream_auto_repair_message,
    dream_auto_repair_metadata_is_valid,
    dream_auto_repair_project_cleanup_from_metadata,
    persist_dream_auto_repair_message,
    settle_dream_auto_repair_message,
)
from story_workspace.dream_workbench_context import DreamWorkbenchContext
from story_workspace.contracts import (
    StoryWorkspaceAgentStoryPayload,
    StoryWorkspaceDreamRunContext,
)
from libs.claude_agent_kit.types import (
    AgentRunOptions,
    AgentStreamingCallbacks,
    DREAM_AUTO_REPAIR_EXECUTION_SCHEMA_VERSION,
    DreamAutoRepairExecutionScope,
    ToolEventPayload,
)
from services.claude_plugin.workspace_packer import pack_workspace_plugins
from services.deck.chat_context import DeckChatContextService
from services.admin_gateway import GatewayModel, resolve_platform_model
from session_events import EditSessionEvent, session_event_bus
from claude_agent.chat_stream_adapter import ChatStreamAdapter
from claude_agent.stream_events import NormalizedAgentEvent

logger = logging.getLogger(__name__)

_TRUSTED_STORY_WORKSPACE_ENV_KEYS = frozenset({
    "INK_AGENT_USER_ID",
    "INK_AGENT_THREAD_ID",
    "INK_AGENT_WORKFLOW_RUN_ID",
    "INK_AGENT_STORY_WORKSPACE_MESSAGE_ID",
})
def _pack_thread_workspace_plugins(
    cwd: str,
    deck_id: Optional[str],
    *,
    dream_mode: bool = False,
) -> None:
    """Pack the thread-locked Deck's plugins into the thread workspace.

    Runs on the service executor thread (SQLite + filesystem work).  Errors
    propagate to the chat turn: a workspace whose Deck references unverifiable
    plugins must fail closed, never launch with a partial plugin set.  A
    thread without a locked Deck is a full no-op (no DB connection, no
    filesystem writes).
    """

    if not deck_id:
        return
    db = _db.get_db()
    try:
        pack_workspace_plugins(
            db,
            workspace=Path(cwd),
            deck_id=deck_id,
            server_adapter_package_specs=(
                ("ink-dream-story@platform-builtin",) if dream_mode else ()
            ),
        )
    finally:
        db.close()


async def _resolve_story_workspace_dream_deck_prompt(
    *,
    context: StoryWorkspaceDreamRunContext,
    actor_id: str | int,
) -> str:
    """Resolve the current Deck prompt in workspace-file mode.

    The browser and public Chat request cannot claim Dream authority. Only the
    server-trusted binding resolved by ``assemble_context`` selects this mode,
    preventing the ordinary standalone proposal contract from entering a
    Dream asset turn.
    """

    db = _db.get_db()
    try:
        resolved = await DeckChatContextService(db).resolve(
            deck_id=context.deck_id,
            actor_id=str(actor_id),
            voice_id=context.agent_id,
            dream_mode=True,
        )
        return resolved.system_prompt
    finally:
        db.close()


def _resolve_managed_mcp_workspace_scope_sync(
    *,
    actor_id: str,
    context: StoryWorkspaceDreamRunContext | None,
) -> str | None:
    """Resolve the actor-owned Dream workspace scope for one managed snapshot."""

    if context is None:
        return None
    db = _db.get_db()
    try:
        row = db.execute(
            "SELECT workspace_id FROM workflow_runs "
            "WHERE id = %s AND created_by = %s",
            (context.workflow_run_id, actor_id),
        ).fetchone()
        if db.in_transaction:
            db.rollback()
        if row is None or not row["workspace_id"]:
            raise PermissionError("Dream managed MCP workspace scope is unavailable")
        return str(row["workspace_id"])
    finally:
        db.close()


async def _activate_story_workspace_dream_runtime(
    *,
    context: StoryWorkspaceDreamRunContext,
    actor_id: str,
    cwd: str,
    remote_session_ref: str,
) -> None:
    """Bind verified assembled workspace facts to the Workflow Run."""

    from libs.claude_agent_kit.server.plugin_launcher import (
        read_workspace_launch_manifest,
    )
    from models.workflow_run import AuthenticatedActorContext
    from services.story_workspace.workflow_security import (
        story_workspace_workflow_token_secret,
    )
    from services.story_workspace.dream_launch_infrastructure import (
        DreamLaunchApplicationError,
        DreamRuntimeProvisioningService,
    )
    from services.story_workspace.dream_runtime_activation_service import (
        DREAM_RUNTIME_NOT_READY,
        StoryWorkspaceDreamRuntimeActivationError,
        StoryWorkspaceDreamRuntimeActivationService,
    )

    verified_plugins = read_workspace_launch_manifest(cwd)
    db = _db.get_db()
    try:
        row = db.execute(
            "SELECT workspace_id, source_voice_thread_id FROM workflow_runs "
            "WHERE id = %s AND created_by = %s",
            (context.workflow_run_id, actor_id),
        ).fetchone()
        if db.in_transaction:
            db.rollback()
        if row is None or row["source_voice_thread_id"] != context.thread_id:
            raise PermissionError("Dream runtime actor/run/thread scope mismatch")
        try:
            # A queued Run may outlive an older materialization identity
            # algorithm. Rebuild only the server-frozen lock's evidence from
            # the verified immutable installation before enforcing the exact
            # activation join. Never accept the stale row as equivalent.
            try:
                DreamRuntimeProvisioningService(
                    db
                ).ensure_frozen_runtime_evidence(
                    context.runtime_plugin_lock_id
                )
            except DreamLaunchApplicationError as exc:
                raise StoryWorkspaceDreamRuntimeActivationError(
                    DREAM_RUNTIME_NOT_READY,
                    "Dream runtime materialization could not be refreshed",
                ) from exc
            await StoryWorkspaceDreamRuntimeActivationService(
                db,
                token_secret=story_workspace_workflow_token_secret(),
            ).activate_from_assembled_context(
                workflow_run_id=context.workflow_run_id,
                actor_context=AuthenticatedActorContext(
                    actor_id=actor_id,
                    workspace_id=str(row["workspace_id"]),
                ),
                remote_session_ref=remote_session_ref,
                verified_plugins=verified_plugins,
            )
        except StoryWorkspaceDreamRuntimeActivationError:
            logger.warning(
                "Dream assembled runtime rejected: run=%s verified_plugins=%s",
                context.workflow_run_id,
                len(verified_plugins),
            )
            raise
    finally:
        db.close()


def _store_story_workspace_output_sync(
    user_id: int,
    thread_id: str,
    payload: StoryWorkspaceAgentStoryPayload,
) -> dict[str, Any]:
    """Run Story Workspace SQLite persistence on the service executor thread."""

    db = _db.get_db()
    try:
        workspace_id = get_or_create_default_workspace(db, user_id)
        result = store_agent_story_output(
            db,
            user_id,
            workspace_id,
            thread_id,
            payload,
        )
        source = db.execute(
            """
            SELECT thread.id AS chat_thread_id, thread.deck_id,
                   deck.name AS deck_name, deck.name_zh AS deck_name_zh,
                   deck.name_en AS deck_name_en
            FROM chat_thread AS thread
            LEFT JOIN decks AS deck ON deck.id = thread.deck_id
            WHERE thread.id = %s AND thread.user_id = %s
            """,
            (thread_id, user_id),
        ).fetchone()
        result["chat_thread_id"] = thread_id
        if source is not None:
            result.update(
                {
                    "deck_id": source["deck_id"],
                    "deck_name": source["deck_name"],
                    "deck_name_zh": source["deck_name_zh"],
                    "deck_name_en": source["deck_name_en"],
                }
            )
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# Keepalive interval for SSE comments (seconds).
_SSE_KEEPALIVE_S: float = float(os.getenv("INK_AGENT_SSE_KEEPALIVE_S", "15") or "15")

# Maximum characters to use when auto-titling a thread from the first user message.
MAX_THREAD_TITLE_LENGTH: int = 50

# Agent contract version — bump when the system prompt or tool set changes in a
# way that makes old SDK transcripts incompatible with the current runtime.
_AGENT_RUNTIME_CONTRACT_VERSION: str = os.getenv(
    "INK_AGENT_CONTRACT_VERSION", "2026-05-29-ink-and-memory-v1"
) or "2026-05-29-ink-and-memory-v1"

# MCP editor write tools that require human confirmation AND trigger an
# editor_state DB-reload after successful execution (see mcp-tools.md §4).
_EDITOR_WRITE_TOOL_NAMES: frozenset[str] = frozenset({
    "mcp__editor__write_segment",
    "mcp__editor__delete_segment",
    "mcp__editor__insert_widget",
    "mcp__editor__reply_to_comment",
})

_SANDBOX_NETWORK_MODES: frozenset[str] = frozenset({"disabled", "allowlist", "open"})

# ---------------------------------------------------------------------------
# Plan Mode capture (claude-plan §5.2–§5.5)
# ---------------------------------------------------------------------------

# Plan Mode tool → plan_mode transition (§5.2 state machine).
_PLAN_MODE_BY_TOOL: dict[str, str] = {
    "EnterPlanMode": "planning",
    "ExitPlanMode": "exited",
}

_PLAN_MAX_CONTENT_BYTES_DEFAULT: int = 262144


def _plan_max_content_bytes() -> int:
    """Return the plan content cap (bytes) from env config.

    Oversized plan content is truncated in plan-updated frames / REST
    responses and flagged ``truncated:true`` (claude-plan §5.4).
    """

    try:
        raw = os.getenv("INK_AGENT_PLAN_MAX_CONTENT_BYTES", "") or ""
        value = int(raw) if raw else _PLAN_MAX_CONTENT_BYTES_DEFAULT
        return value if value > 0 else _PLAN_MAX_CONTENT_BYTES_DEFAULT
    except (TypeError, ValueError):
        return _PLAN_MAX_CONTENT_BYTES_DEFAULT


@dataclass
class PlanState:
    """In-memory Plan Mode state for a thread (claude-plan §5.2).

    Memory-only, attached to the AgentRunState flyweight — the workspace
    plans directory is the sole persistent layer; refresh/reconnect always
    rebuilds via the REST endpoint.
    """

    plan_mode: str = "none"  # "none" | "planning" | "exited"
    slug: Optional[str] = None
    file_name: Optional[str] = None
    updated_at: Optional[str] = None
    content_bytes: int = 0


def _ensure_plan_state(state: Optional[Any]) -> PlanState:
    """Return the live PlanState for *state*, creating it on first use."""

    plan_state = getattr(state, "plan_state", None) if state is not None else None
    if plan_state is None:
        plan_state = PlanState()
        if state is not None:
            state.plan_state = plan_state
    return plan_state


def _read_plan_file_payload(path: Path) -> Optional[dict[str, Any]]:
    """Read a plan markdown file into the plan-updated / REST payload shape.

    Returns ``None`` on IO/encoding errors — callers log and skip the
    plan-updated emission (claude-plan §5.4 error boundary).  Content is
    capped at ``INK_AGENT_PLAN_MAX_CONTENT_BYTES`` (default 262144);
    oversized files are truncated with ``truncated:true`` so the frontend
    can fetch full content via REST.  ``contentBytes`` always reports the
    on-disk byte size.
    """

    try:
        stat = path.stat()
        size = stat.st_size
        cap = _plan_max_content_bytes()
        with open(path, "rb") as fh:
            data = fh.read(min(size, cap))
        updated_at = (
            datetime.fromtimestamp(stat.st_mtime, timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )
        return {
            "slug": path.stem,
            "fileName": path.name,
            "content": data.decode("utf-8", errors="replace"),
            "contentBytes": size,
            "truncated": size > cap,
            "updatedAt": updated_at,
        }
    except (OSError, ValueError):
        return None


def _find_newest_plan_file(plans_dir: Path) -> Optional[Path]:
    """Return the most recently modified ``.md`` file in *plans_dir*.

    Non-``.md`` suffixes and entries that resolve outside the plans dir
    (symlink escape) are rejected (claude-plan §5.1 constraints).
    """

    try:
        resolved_dir = plans_dir.resolve(strict=False)
        candidates: list[Path] = []
        for entry in plans_dir.iterdir():
            if entry.suffix.lower() != ".md":
                continue
            try:
                resolved = entry.resolve(strict=False)
                resolved.relative_to(resolved_dir)
            except (OSError, RuntimeError, ValueError):
                continue
            if resolved.is_file():
                candidates.append(resolved)
    except OSError:
        return None
    if not candidates:
        return None
    try:
        return max(candidates, key=lambda p: p.stat().st_mtime)
    except OSError:
        return None


def _thread_workspace_exists(thread_id: str) -> bool:
    """Return True when the per-thread workspace directory exists.

    Uses the same traversal guard as ``get_or_create_workspace``.  A missing
    workspace means Workspace Mode is disabled (or the thread never ran), so
    the plan endpoint must not probe the global ``~/.claude/plans``.
    """

    if not thread_id or "/" in thread_id or "\\" in thread_id or ".." in thread_id:
        return False
    try:
        root = get_workspace_root().resolve(strict=False)
        workspace = (root / thread_id).resolve(strict=False)
        workspace.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return False
    return workspace.is_dir()


def build_thread_plan_payload(thread_id: str, plan_mode: str = "none") -> dict[str, Any]:
    """Build the ``GET /threads/{thread_id}/plan`` response body (claude-plan §5.5).

    The filesystem is the source of truth: scan ``get_plans_dir(thread_id)``
    for the newest ``.md`` plan file.  *plan_mode* comes from in-memory run
    state when the thread is running, else ``"none"``.  Missing workspace
    (Workspace Mode disabled) → fixed ``exists:false`` + ``plan_mode:"none"``;
    an existing workspace without plans keeps the in-memory *plan_mode*.
    """

    payload: dict[str, Any] = {
        "thread_id": thread_id,
        "plan_mode": plan_mode or "none",
        "exists": False,
        "slug": None,
        "file_name": None,
        "content": None,
        "content_bytes": None,
        "truncated": False,
        "updated_at": None,
    }
    if not _thread_workspace_exists(thread_id):
        payload["plan_mode"] = "none"
        return payload
    plans_dir = get_plans_dir(thread_id)
    newest = _find_newest_plan_file(plans_dir) if plans_dir is not None else None
    if newest is None:
        return payload
    data = _read_plan_file_payload(newest)
    if data is None:
        logger.warning("build_thread_plan_payload: failed to read plan file %s", newest)
        return payload
    payload.update(
        {
            "exists": True,
            "slug": data["slug"],
            "file_name": data["fileName"],
            "content": data["content"],
            "content_bytes": data["contentBytes"],
            "truncated": data["truncated"],
            "updated_at": data["updatedAt"],
        }
    )
    return payload


async def _emit_plan_updated(
    queue: Any, plan_state: PlanState, path: Path
) -> None:
    """Read *path* and emit a plan-updated frame; update *plan_state*.

    Lifecycle frame — NOT collected into ``collected_parts`` (claude-plan
    §5.4).  IO/read failures skip the emission and only log.
    """

    data = _read_plan_file_payload(path)
    if data is None:
        logger.warning("plan file read failed; skipping plan-updated: %s", path)
        return
    plan_state.slug = data["slug"]
    plan_state.file_name = data["fileName"]
    plan_state.updated_at = data["updatedAt"]
    plan_state.content_bytes = data["contentBytes"]
    await queue.put(_event("plan-updated", data))


async def _observe_plan_mode_transition(
    queue: Any,
    state: Optional[Any],
    tool_call_id: Optional[str],
    tool_name: Optional[str],
) -> None:
    """Transition PlanState on EnterPlanMode/ExitPlanMode tool-input-available.

    Emits ``plan-mode-changed`` (lifecycle frame — not collected).  On
    ExitPlanMode also performs the final plan-file read so the panel freezes
    on the approved version (claude-plan §5.3/§6.2).  Plan mode transitions
    are decoupled from file reads: a failed read never blocks
    ``plan-mode-changed``.
    """

    plan_mode = _PLAN_MODE_BY_TOOL.get(tool_name or "")
    if plan_mode is None:
        return
    plan_state = _ensure_plan_state(state)
    plan_state.plan_mode = plan_mode
    await queue.put(
        _event("plan-mode-changed", {"planMode": plan_mode, "toolCallId": tool_call_id})
    )
    if tool_name == "ExitPlanMode" and state is not None:
        plans_dir = get_plans_dir(getattr(state, "session_id", "") or "")
        newest = _find_newest_plan_file(plans_dir) if plans_dir is not None else None
        if newest is not None:
            await _emit_plan_updated(queue, plan_state, newest)


# ---------------------------------------------------------------------------
# Todo capture — v1 TodoWrite stream observation + v2 file tasks (claude-todo §5.2–§5.5)
# ---------------------------------------------------------------------------

_TODO_MAX_ITEMS_DEFAULT: int = 200

_TODO_STATUSES: frozenset[str] = frozenset({"pending", "in_progress", "completed"})


def _todo_max_items() -> int:
    """Return the todo list cap from env config.

    Lists larger than the cap are truncated in todo-updated frames / REST
    responses and flagged ``truncated:true`` (claude-todo §5.4).
    """

    try:
        raw = os.getenv("INK_AGENT_TODO_MAX_ITEMS", "") or ""
        value = int(raw) if raw else _TODO_MAX_ITEMS_DEFAULT
        return value if value > 0 else _TODO_MAX_ITEMS_DEFAULT
    except (TypeError, ValueError):
        return _TODO_MAX_ITEMS_DEFAULT


def _utc_now_iso() -> str:
    """Return the current UTC time in the SSE/REST ISO-8601 Z format."""

    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


@dataclass
class TodoState:
    """In-memory todo list state for a thread (claude-todo §5.2).

    Memory-only, attached to the AgentRunState flyweight — same pattern as
    PlanState.  ``source`` records which capture path produced the current
    list (``"todo_write"`` for v1 stream capture, ``"task_v2"`` for file
    tasks); a later capture overwrites the earlier one.  There is no v1
    persistent layer: refresh/reconnect rebuilds v2 from the workspace
    tasks directory and falls back to this memory state for v1.
    """

    source: Optional[str] = None  # None | "todo_write" | "task_v2"
    todos: list = field(default_factory=list)
    updated_at: Optional[str] = None


def _ensure_todo_state(state: Optional[Any]) -> TodoState:
    """Return the live TodoState for *state*, creating it on first use."""

    todo_state = getattr(state, "todo_state", None) if state is not None else None
    if todo_state is None:
        todo_state = TodoState()
        if state is not None:
            state.todo_state = todo_state
    return todo_state


def _truncate_todos(todos: list) -> tuple[list, bool]:
    """Apply the INK_AGENT_TODO_MAX_ITEMS cap; return (items, truncated)."""

    cap = _todo_max_items()
    if len(todos) <= cap:
        return list(todos), False
    return list(todos[:cap]), True


async def _emit_todo_updated(queue: Any, todo_state: TodoState) -> None:
    """Emit a todo-updated frame from *todo_state*.

    Lifecycle frame — NOT collected into ``collected_parts`` (claude-todo
    §5.4).  Payload: ``source`` / ``todos`` / ``updatedAt``; lists beyond
    ``INK_AGENT_TODO_MAX_ITEMS`` (default 200) are truncated with
    ``truncated:true``.
    """

    todos, truncated = _truncate_todos(todo_state.todos)
    await queue.put(
        _event(
            "todo-updated",
            {
                "source": todo_state.source,
                "todos": todos,
                "truncated": truncated,
                "updatedAt": todo_state.updated_at,
            },
        )
    )


async def _observe_todo_write(
    queue: Any,
    state: Optional[Any],
    tool_name: Optional[str],
    tool_input: Optional[dict[str, Any]],
) -> None:
    """Capture the v1 TodoWrite full list from tool-input-available (§5.3).

    ``input.todos`` is the complete replacement list; each entry maps to a
    TodoItem with ``id`` = 1-based array index, ``content``/``status``/
    ``activeForm`` taken directly, ``owner`` = None and ``blocked_by`` = [].
    Schema mismatches skip the emission and only log (§5.4 error boundary).
    """

    if tool_name != "TodoWrite":
        return
    raw_todos = (tool_input or {}).get("todos")
    if not isinstance(raw_todos, list):
        logger.warning(
            "TodoWrite capture skipped: input.todos missing or not a list."
        )
        return
    todos: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_todos):
        if not isinstance(raw, dict) or not isinstance(raw.get("content"), str):
            logger.warning(
                "TodoWrite capture skipped: todos[%d] schema mismatch.", index
            )
            return
        status = str(raw.get("status") or "pending")
        if status not in _TODO_STATUSES:
            status = "pending"
        todos.append(
            {
                "id": str(index + 1),
                "content": raw["content"],
                "status": status,
                "active_form": (
                    str(raw["activeForm"]) if raw.get("activeForm") else None
                ),
                "owner": None,
                "blocked_by": [],
            }
        )
    todo_state = _ensure_todo_state(state)
    todo_state.source = "todo_write"
    todo_state.todos = todos
    todo_state.updated_at = _utc_now_iso()
    await _emit_todo_updated(queue, todo_state)


def build_thread_todos_payload(
    thread_id: str, todo_state: Optional[TodoState] = None
) -> dict[str, Any]:
    """Build the ``GET /threads/{thread_id}/todos`` response body (claude-todo §5.5).

    Priority: when the v2 tasks directory holds task JSON, the filesystem is
    the source of truth — the list is rebuilt via ``read_task_items`` and the
    in-memory *todo_state* (when provided) is corrected to match.  Otherwise
    the in-memory state (v1 TodoWrite capture) is returned.  Missing
    workspace (Workspace Mode disabled) → fixed ``exists:false``; the global
    ``~/.claude/tasks`` is never probed.
    """

    payload: dict[str, Any] = {
        "thread_id": thread_id,
        "source": None,
        "exists": False,
        "todos": [],
        "truncated": False,
        "updated_at": None,
    }
    if not _thread_workspace_exists(thread_id):
        return payload

    tasks_dir = get_tasks_dir(thread_id)
    if tasks_dir is not None:
        items, newest_mtime = read_task_items(tasks_dir)
        if items:
            updated_at = (
                datetime.fromtimestamp(newest_mtime, timezone.utc)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z")
                if newest_mtime is not None
                else _utc_now_iso()
            )
            if todo_state is not None:
                # Filesystem wins — correct the in-memory state (§5.5).
                todo_state.source = "task_v2"
                todo_state.todos = items
                todo_state.updated_at = updated_at
            todos, truncated = _truncate_todos(items)
            payload.update(
                {
                    "source": "task_v2",
                    "exists": True,
                    "todos": todos,
                    "truncated": truncated,
                    "updated_at": updated_at,
                }
            )
            return payload

    if todo_state is not None and todo_state.source:
        todos, truncated = _truncate_todos(todo_state.todos)
        payload.update(
            {
                "source": todo_state.source,
                "exists": True,
                "todos": todos,
                "truncated": truncated,
                "updated_at": todo_state.updated_at,
            }
        )
    return payload



def _coerce_sandbox_network_mode(value: object) -> str:
    """Return the persisted sandbox network mode or the product default."""

    mode = str(value or "").strip().lower()
    return mode if mode in _SANDBOX_NETWORK_MODES else "allowlist"


def _coerce_settings_system_prompt(value: object) -> str:
    """Normalize Settings SYSTEM_PROMPT from system_config for cache comparison."""

    return str(value).strip() if value is not None else ""


def _coerce_string_list(value: object) -> list[str]:
    """Return non-empty strings from a stored list-like config value."""

    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


# ---------------------------------------------------------------------------
# Resume helpers
# ---------------------------------------------------------------------------


def _extract_editor_tool_result(output: Any) -> Optional[dict[str, Any]]:
    """Return an Editor MCP business result from direct or stdio envelopes."""

    candidates: list[Any] = [output]
    if isinstance(output, dict):
        content = output.get("content")
        if isinstance(content, list):
            candidates.extend(content)
    for candidate in candidates:
        if isinstance(candidate, dict) and isinstance(candidate.get("ok"), bool):
            return candidate
        text = candidate.get("text") if isinstance(candidate, dict) else candidate
        if not isinstance(text, str):
            continue
        try:
            decoded = json.loads(text)
        except (TypeError, ValueError):
            continue
        if isinstance(decoded, dict) and isinstance(decoded.get("ok"), bool):
            return decoded
    return None


def _tool_result_ok(output: Any) -> bool:
    """Return False only for a decoded Editor MCP ``{"ok": false}`` result."""

    result = _extract_editor_tool_result(output)
    return result is None or result.get("ok") is not False


def _is_editor_tool_result_error(tool_name: str, output: Any) -> bool:
    """Return whether an editor write result is an explicit business failure.

    The SDK's transport-level ``is_error`` flag does not describe MCP handlers
    that successfully return a structured ``{"ok": false}`` payload.  Normalize
    only the named editor write tools so unrelated tool output remains unchanged.
    """

    return tool_name in _EDITOR_WRITE_TOOL_NAMES and not _tool_result_ok(output)


def _has_usable_claude_resume(existing_session: Optional[Mapping[str, Any]]) -> bool:
    """Return True when the saved chat_thread has a resumable Claude SDK session.

    A session is resumable when:
    - ``claude_session_id`` is non-empty, AND
    - ``agent_contract_version`` matches the current runtime version (schema/tool
      compatibility guard).

    The transcript JSONL file existence check is performed separately by the
    caller (``assemble_context``) because it requires async I/O.
    """
    if not existing_session or not existing_session.get("claude_session_id"):
        return False
    stored_version = str(existing_session.get("agent_contract_version") or "").strip()
    return stored_version == _AGENT_RUNTIME_CONTRACT_VERSION


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_text_from_parts(parts: Optional[list]) -> str:
    """Extract text from AI-SDK UIMessage parts for use as a plain string.

    Delegates to ``extract_text_from_parts`` (full UIMessage parts protocol:
    text + file + source-url + workspace-file).  Used for thread title
    auto-fill where a compact string representation is needed.
    """
    return extract_text_from_parts(parts)


def _format_exception_for_sse(exc: BaseException | None) -> str:
    """Return SSE-safe error text, including PEP-678 notes when available."""

    if exc is None:
        return "Unknown error"
    base = str(exc)
    notes = getattr(exc, "__notes__", None)
    if not isinstance(notes, list) or not notes:
        return base
    rendered_notes = [str(note).strip() for note in notes if str(note).strip()]
    if not rendered_notes:
        return base
    return " | ".join([base, *rendered_notes])


def _attach_story_workspace_dream_assistant_source(
    assistant_metadata: dict[str, Any],
    request: "ClaudeAgentRunRequest",
    context: StoryWorkspaceDreamRunContext | None,
) -> None:
    """Persist server-authenticated Dream business correlation on the reply.

    Generic Chat rows intentionally receive no marker.  The metadata supports
    canonical persistence and workflow projection after ownership validation;
    it does not alter the shared Chat message-visibility contract or create a
    Dream-specific transport.
    """

    source_metadata = request.message_metadata or {}
    source_kind = (
        source_metadata.get("kind")
        if isinstance(source_metadata, dict)
        else None
    )
    if not (
        context is not None
        and isinstance(request.message_id, str)
        and request.message_id
        and source_kind in {
            "story-workspace-dream-launch",
            "story-workspace-dream-confirmation",
            "story-workspace-dream-agent-user",
            "story-workspace-dream-auto-repair",
        }
    ):
        return
    assistant_metadata["story_workspace_dream_source"] = {
        "run_id": context.workflow_run_id,
        "thread_id": context.thread_id,
        "actor_id": str(request.user_id),
        "message_id": request.message_id,
        "kind": source_kind,
    }


# Request model
# ---------------------------------------------------------------------------


@dataclass
class ClaudeAgentRunRequest:
    """Validated request for a single Claude Agent turn.

    All string IDs are validated by the factory before this dataclass is built.
    ``message_parts`` carries the AI-SDK UIMessage parts list (e.g.
    ``[{"type": "text", "text": "..."}]``); plain text is derived from it as
    needed — the raw ``message_text`` string is never stored here.

    When ``reconnect`` is True the factory subscribes to an in-flight EventBus
    instead of starting a new inference turn.
    """

    user_id: str
    thread_id: str
    reconnect: bool = False
    resume: bool = False
    tool_choice: str = "auto"
    model: Optional[str] = None
    # Server-owned model Runtime projection. Public request DTOs never expose
    # this field; the authenticated Gateway catalog populates it.
    model_runtime_env: dict[str, str] = field(default_factory=dict)
    max_turns: int = int(os.getenv("INK_AGENT_MAX_TURNS", "100") or "100")
    cwd: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)
    # AI-SDK message fields (for context assembly and DB persistence)
    message_id: Optional[str] = None
    message_parts: Optional[list] = None
    # Optional AI-SDK message metadata persisted with the user row. Server-side
    # turn injectors (e.g. Story Workspace guidance) pass their audit metadata
    # here so the per-turn re-save (INSERT OR REPLACE) preserves it instead of
    # wiping a previously persisted metadata payload.
    message_metadata: Optional[dict[str, Any]] = None
    # File attachments to be passed as content blocks to Claude.
    attachments: Optional[list[AttachmentPayload]] = None
    # Current EditorState for the .editor/ virtual index (optional).
    editor_state: Optional[dict[str, Any]] = None
    # Voice / deck system prompt injected as context into each user message.
    system_prompt: Optional[str] = None
    # NOTE (2026-08-02, deck-integration-delta): ``claude_settings_json`` and
    # ``claude_plugin_paths`` were removed.  Per-turn requests must never
    # carry settings JSON or plugin paths: plugins are resolved from the
    # thread-locked Deck, packed into the thread workspace by the server, and
    # loaded via the workspace launch manifest (--plugin-dir) at the CLI
    # launcher boundary.


@dataclass(frozen=True)
class ClaudeAgentTurnContinuation:
    """One server-owned next Turn that remains inside the canonical factory."""

    request: ClaudeAgentRunRequest


class ClaudeAgentAssistantPersistenceError(RuntimeError):
    """Safe terminal error raised before a Dream Hook can outpace Chat truth."""

    code = "CHAT_ASSISTANT_PERSISTENCE_FAILED"
    public_message = (
        "Agent 已完成本轮，但回复未能安全保存；"
        "后置同步未执行。请重新加载后重试。"
    )
    retryable = True

    def __init__(self) -> None:
        super().__init__(self.public_message)


# ---------------------------------------------------------------------------
# Turn context (extrinsic state bundle)
# ---------------------------------------------------------------------------


_TEXT_PART_ID = "text-0"


@dataclass
class _TurnContext:
    """Mutable state bundle for a single agent turn.

    ``collected_parts`` collects the raw SSE event dicts **as they are emitted**
    to the frontend (§4.5.2).  The subset that carries UIMessage-relevant data:

      collected event types     → UIMessage part (after _sse_events_to_ui_parts)
      ───────────────────────── ────────────────────────────────────────────────
      text-start/delta/end      → {"type":"text", "text":"..."}
      reasoning-start/delta/end → {"type":"reasoning", "id":"...", "text":"..."}
      tool-input-available      → {"type":"tool-invocation", "state":"call", ...}
      tool-output-available     → patches matching invocation → "output-available"

    NOT collected (lifecycle / aggregate, no UIMessage equivalent):
      message-metadata, tool-input-start, tool-approval-request,
      message-final, finish, error.

    ``_TurnContext`` is created fresh each turn — no explicit clearing needed.
    ``_persist_turn`` calls ``_sse_events_to_ui_parts(collected_parts)`` once.
    """

    queue: Any  # asyncio.Queue or BusProxyQueue
    confirmation_store: ToolConfirmationStore
    pending_tool_call_ids: set = field(default_factory=set)
    turn_start_ts: float = field(default_factory=time.monotonic)
    # Dedup sets for SSE emission.
    registered_tool_call_ids: set = field(default_factory=set)
    emitted_tool_input_ids: set = field(default_factory=set)
    # Confirmation callbacks can be duplicated by the SDK. The first callback
    # owns policy registration; identical duplicates join the same pending
    # decision without introducing another public Agent event.
    confirmation_policy_fingerprints: dict[str, str] = field(default_factory=dict)
    # tool_call_id → tool_name mapping built as tool_use* events arrive.
    # Used by the tool_result branch to identify editor write tools when the
    # result event itself does not carry tool_name.
    tool_name_by_id: dict = field(default_factory=dict)
    # tool_call_id → complete tool input. Editor result handling uses this
    # immutable identity to refresh only the actor's live Editor session.
    tool_input_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Thinking / reasoning tracking (for SSE reasoning-start/end emission).
    current_reasoning_id: Optional[str] = None
    has_thinking_delta: bool = False
    completed_streamed_reasoning_texts: list = field(default_factory=list)
    current_reasoning_text: list = field(default_factory=list)
    # Raw SSE event dicts collected as they are emitted; converted at persist time.
    collected_parts: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ClaudeAgentService:
    """Core business service for the Claude Agent module.

    One shared instance is created by ``ClaudeAgentThreadFactory`` at startup.
    """

    def __init__(
        self,
        context_builder: Optional[ClaudeAgentContextBuilder] = None,
        platform_model_resolver: (
            Callable[[int | str, str | None], GatewayModel | str] | None
        ) = None,
        claude_code_runtime_env_provider: (
            Callable[[], Mapping[str, str]] | None
        ) = None,
        dream_context_mapper: DreamThreadContextMapper | None = None,
        dream_runtime_init_activator: (
            Callable[..., Awaitable[None]] | None
        ) = None,
        dream_artifact_turn_hook: DreamArtifactTurnHook | None = None,
        dream_workbench_context: DreamWorkbenchContext | None = None,
        managed_mcp_runtime_snapshot_loader: Any | None = None,
    ) -> None:
        self._context_builder = context_builder or ClaudeAgentContextBuilder()
        self._platform_model_resolver = (
            platform_model_resolver or resolve_platform_model
        )
        self._claude_code_runtime_env_provider = (
            claude_code_runtime_env_provider or (lambda: {})
        )
        self._dream_context_mapper = dream_context_mapper or DreamThreadContextMapper()
        self._dream_runtime_init_activator = (
            dream_runtime_init_activator
            or _activate_story_workspace_dream_runtime
        )
        self._dream_artifact_turn_hook = (
            dream_artifact_turn_hook or DreamArtifactTurnHook()
        )
        self._dream_workbench_context = (
            dream_workbench_context or DreamWorkbenchContext()
        )
        self._managed_mcp_runtime_snapshot_loader = (
            managed_mcp_runtime_snapshot_loader
        )

    # ------------------------------------------------------------------
    # Phase 1: Context Assembly
    # ------------------------------------------------------------------

    async def assemble_context(
        self,
        request: ClaudeAgentRunRequest,
        *,
        state: AgentRunState,
        bus: "Any",
        runner: ClaudeAgentRunner,
    ) -> "_TurnExecution":
        """Build context for the upcoming turn.

        On the first turn of a session: loads DB context and constructs the
        system prompt (expensive).  On subsequent turns within the keepalive
        window: reuses the cached ``state.system_prompt``.

        Returns a ``_TurnExecution`` ready to pass to ``execute_session``.
        """
        # Dream authority is derived from the authenticated actor + canonical
        # Thread during Phase 1. The request and public Chat protocol never
        # carry a Dream Run selector or context object.
        dream_context = await asyncio.to_thread(
            self._dream_context_mapper.resolve,
            actor_id=request.user_id,
            thread_id=request.thread_id,
        )

        # Load user-configured agent settings from system config before system
        # prompt and cwd resolution.  Settings SYSTEM_PROMPT participates in the
        # cached system_prompt, while the remaining flags feed AgentRunOptions
        # and per-thread workspace sandbox settings.
        sys_cfg: dict[str, Any] = {}
        system_config_loaded = False
        settings_system_prompt = ""
        user_env_vars: dict[str, str] = {}
        im_full_access_enabled = False
        workspace_enabled = True
        sandbox_network_mode = "allowlist"
        sandbox_network_allowed_domains: list[str] = []
        sandbox_fs_allowed_write_paths: list[str] = []
        try:
            sys_cfg = _db.get_system_config(int(request.user_id))
            system_config_loaded = True
            settings_system_prompt = _coerce_settings_system_prompt(
                sys_cfg.get("system_prompt")
            )
            raw_env = sys_cfg.get("env_vars") or {}
            if isinstance(raw_env, dict):
                user_env_vars = {
                    str(k).strip(): str(v)
                    for k, v in raw_env.items()
                    if (
                        str(k).strip()
                        and str(k).strip() not in _TRUSTED_STORY_WORKSPACE_ENV_KEYS
                        and v is not None
                    )
                }
            im_full_access_enabled = bool(sys_cfg.get("im_full_access_enabled"))
            workspace_enabled = bool(sys_cfg.get("workspace_enabled", True))
            sandbox_network_mode = _coerce_sandbox_network_mode(
                sys_cfg.get("sandbox_network_mode")
            )
            sandbox_network_allowed_domains = _coerce_string_list(
                sys_cfg.get("sandbox_network_allowed_domains")
            )
            sandbox_fs_allowed_write_paths = _coerce_string_list(
                sys_cfg.get("sandbox_fs_allowed_write_paths")
            )
        except Exception as e:
            logger.warning(
                "Failed to load user agent settings from system_config; skipping. Error: %s",
                e,
            )

        if dream_context is not None:
            # Internal Dream dispatchers bypass the public Chat router. Resolve
            # the live server-owned alias here so every Dream turn is subject
            # to the same catalog/entitlement boundary immediately before the
            # runner is assembled. Errors intentionally propagate fail-closed.
            selected_model = await asyncio.to_thread(
                self._platform_model_resolver,
                request.user_id,
                request.model,
            )
            if isinstance(selected_model, GatewayModel):
                request.model = selected_model.model_alias
                request.model_runtime_env = selected_model.claude_code_runtime_env()
            else:
                # Compatibility for injected test/custom resolvers that return
                # only an alias. They cannot supply Runtime configuration.
                request.model = selected_model

        settings_prompt_changed = (
            system_config_loaded
            and state.is_context_initialized
            and state.system_config_system_prompt != settings_system_prompt
        )
        if not state.is_context_initialized or settings_prompt_changed:
            if settings_prompt_changed:
                logger.debug(
                    "Phase 1: rebuilding system_prompt after Settings SYSTEM_PROMPT "
                    "change for session_id=%s",
                    state.session_id,
                )
            else:
                logger.debug(
                    "Phase 1: building system_prompt for session_id=%s",
                    state.session_id,
                )
            system_prompt = await self._context_builder.build_system_prompt(
                request.user_id,
                configured_system_prompt=settings_system_prompt or None,
            )
            state.with_system_prompt(
                system_prompt,
                system_config_system_prompt=settings_system_prompt,
            )
            state.is_context_initialized = True
        else:
            logger.debug(
                "Phase 1: reusing cached system_prompt for session_id=%s",
                state.session_id,
            )

        claude_secure_storage_home: str | None = None
        claude_mcp_servers: dict[str, dict[str, Any]] = {}
        notion_credential_home: str | None = None
        if workspace_enabled:
            workspace_path = get_or_create_workspace(
                state.session_id,
                sandbox_enabled=resolve_sandbox_enabled(),
                sandbox_network_mode=sandbox_network_mode,
                sandbox_network_allowed_domains=sandbox_network_allowed_domains,
                sandbox_fs_allowed_write_paths=sandbox_fs_allowed_write_paths,
            )
            cwd = str(workspace_path)
            if request.cwd and os.path.abspath(request.cwd) != os.path.abspath(cwd):
                logger.warning(
                    "Ignoring client-provided Claude Agent cwd outside the "
                    "server-owned thread workspace. requested=%s resolved=%s",
                    request.cwd,
                    cwd,
                )
            state.with_cwd(cwd)
            enabled_builtin_skill_platforms: set[str] = set()

            # Phase 1: establish the per-thread Claude config home together
            # with cwd — BEFORE any claude module (resume transcript probe,
            # Deck plugin pack, plan/tasks readers, agent run) touches the
            # filesystem (2026-08-03 scope correction — CLAUDE_CONFIG_DIR
            # relocates plans/, tasks/, projects/ transcripts, plugins/,
            # agents/ and caches, not just Plan Mode files).  Carried into
            # the runner via AgentRunOptions.claude_config_home below.
            claude_config_home = resolve_claude_config_home(cwd)
            claude_tmp_workspace = cwd

            try:
                from notion import (  # noqa: PLC0415
                    NotionCredentialStore,
                    build_notion_facade,
                    clear_workspace_snapshot,
                )
                from notion.errors import (  # noqa: PLC0415
                    NotionConnectorNotFoundError,
                    NotionCredentialError,
                )
            except Exception:  # noqa: BLE001
                # A connector package failure is local to the capability and
                # must not change the Agent conversation state machine.
                logger.warning(
                    "Notion capability initialization failed safely for session_id=%s.",
                    state.session_id,
                )
            else:
                try:
                    notion_facade = build_notion_facade(int(request.user_id))
                    try:
                        notion_facade.materialize_workspace(
                            workspace_path,
                            workspace_id=state.session_id,
                        )
                    except Exception:  # noqa: BLE001
                        try:
                            clear_workspace_snapshot(workspace_path)
                        except Exception:
                            pass
                        logger.debug(
                            "Notion snapshot materialization skipped safely for session_id=%s.",
                            state.session_id,
                        )

                    try:
                        projection = notion_facade.project_runtime_credentials(
                            workspace_path,
                        )
                        if projection.available and projection.thread_home is not None:
                            notion_credential_home = str(projection.thread_home)
                            enabled_builtin_skill_platforms.add("notion")
                    except NotionCredentialError:
                        # Missing/invalid credentials fail closed for Notion only.
                        try:
                            NotionCredentialStore().clear_thread_projection(workspace_path)
                        except Exception:
                            pass
                except NotionConnectorNotFoundError:
                    try:
                        clear_workspace_snapshot(workspace_path)
                        NotionCredentialStore().clear_thread_projection(workspace_path)
                    except Exception:
                        pass
                except Exception:  # noqa: BLE001
                    try:
                        clear_workspace_snapshot(workspace_path)
                        NotionCredentialStore().clear_thread_projection(workspace_path)
                    except Exception:
                        pass
                    # Raw filesystem/CLI exception text is intentionally omitted.
                    logger.warning(
                        "Notion Runtime projection failed safely for session_id=%s.",
                        state.session_id,
                    )

            builtin_sync_result = sync_builtin_workspace_skills(
                workspace_path,
                enabled_platforms=enabled_builtin_skill_platforms,
                prune_inactive_platforms=True,
            )
            if builtin_sync_result is not None:
                sync_workspace_sandbox_settings(
                    workspace_path,
                    enabled=resolve_sandbox_enabled(),
                    network_mode=sandbox_network_mode,
                    network_allowed_domains=sandbox_network_allowed_domains,
                    fs_allowed_write_paths=sandbox_fs_allowed_write_paths,
                    builtin_skill_read_paths=builtin_sync_result.linked_source_paths,
                )
        else:
            cwd = ""
            if request.cwd:
                logger.warning(
                    "Ignoring client-provided Claude Agent cwd because Workspace "
                    "Mode is disabled. requested=%s",
                    request.cwd,
                )
            if state.cwd:
                logger.debug(
                    "Phase 1: clearing cached cwd because Workspace Mode is "
                    "disabled for session_id=%s",
                    state.session_id,
                )
            state.with_cwd("")

            # Phase 1: Workspace Mode disabled — no per-thread config home;
            # resolution falls back to an explicit CLAUDE_CONFIG_DIR process
            # env var or the CLI's official default (~/.claude).
            claude_config_home = resolve_claude_config_home(None)
            claude_tmp_workspace = str(
                get_or_create_thread_runtime_workspace(state.session_id)
            )

        try:
            loader = self._managed_mcp_runtime_snapshot_loader
            if loader is None:
                from claude_mcp.service import (  # noqa: PLC0415
                    get_default_managed_mcp_runtime_snapshot_loader,
                )

                loader = get_default_managed_mcp_runtime_snapshot_loader()
            managed_workspace_id = await asyncio.to_thread(
                _resolve_managed_mcp_workspace_scope_sync,
                actor_id=str(request.user_id),
                context=dream_context,
            )
            snapshot = await loader.load(
                str(request.user_id),
                managed_workspace_id,
            )
            claude_mcp_servers = {
                str(name): dict(config)
                for name, config in snapshot.items()
                if isinstance(name, str) and isinstance(config, dict)
            }
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "Managed Claude MCP snapshot loading failed safely."
            ) from exc

        # ---------------------------------------------------------------
        # Resolve resume: load existing chat_thread to get claude_session_id.
        #
        # First turn:  thread_id_for_agent=None  → SDK allocates new session.
        # Resume turn: thread_id_for_agent=claude_session_id from DB → SDK
        #              resumes the existing transcript.
        #
        # Cross-environment safety: probe the local JSONL file before
        # committing to resume.  A fresh deployment or CLI retention reaping
        # will cause the subprocess to exit 1 ("Fatal error in message reader")
        # if we pass a stale claude_session_id.  On a miss we fall back to a
        # fresh SDK session; _persist_turn will write the new claude_session_id
        # so the DB self-heals for the next turn.
        # ---------------------------------------------------------------
        from libs.claude_agent_kit.server.session_files import (
            get_projects_root,
            locate_session_file,
        )

        existing_session: Optional[dict] = None
        try:
            existing_session = await asyncio.to_thread(
                _db.get_chat_thread, request.thread_id, int(request.user_id)
            )
        except Exception:
            logger.warning(
                "Failed to load existing chat_thread for resume check; thread_id=%s",
                request.thread_id,
            )

        resume_existing_session: Optional[dict] = (
            existing_session
            if request.resume and _has_usable_claude_resume(existing_session)
            else None
        )
        if resume_existing_session is not None:
            candidate_session_id = str(
                resume_existing_session.get("claude_session_id") or ""
            ).strip()
            projects_root = get_projects_root(cwd or None)
            located_session_path = (
                await locate_session_file(projects_root, candidate_session_id)
                if (projects_root and candidate_session_id)
                else None
            )
            if not located_session_path:
                logger.warning(
                    "Claude session transcript missing locally; falling back "
                    "to a fresh SDK session. thread_id=%s stale_claude_session_id=%s "
                    "projects_root=%s",
                    request.thread_id,
                    candidate_session_id,
                    projects_root,
                )
                resume_existing_session = None

        existing_claude_session_id: Optional[str] = (
            resume_existing_session.get("claude_session_id") if resume_existing_session else None
        )
        should_resume = bool(request.resume and existing_claude_session_id)
        # None on first turn lets the SDK allocate a fresh session ID.
        thread_id_for_agent: Optional[str] = existing_claude_session_id if should_resume else None

        # Deck plugin pack (deck-integration-delta §Chat Assembly): pack the
        # thread-locked Deck's enabled plugin installations into the thread
        # workspace and write the server-controlled launch manifest.  Frozen
        # semantics — an already-packed workspace is re-validated and its
        # packed copies repaired, never silently reconfigured; disabling a
        # plugin on the Deck only affects workspaces created afterwards.
        # deck_id reuses the resume-check row above (no extra DB read); with
        # no locked Deck the pack is a full no-op (no DB, no filesystem).
        if workspace_enabled and cwd:
            thread_deck_id = (
                str((existing_session or {}).get("deck_id") or "").strip() or None
            )
            if thread_deck_id:
                if dream_context is not None:
                    if (
                        dream_context.thread_id != request.thread_id
                        or dream_context.thread_id != state.session_id
                        or dream_context.deck_id != thread_deck_id
                    ):
                        raise ValueError(
                            "Story Workspace Dream context does not match the trusted thread Deck"
                        )
                try:
                    await asyncio.to_thread(
                        _pack_thread_workspace_plugins,
                        cwd,
                        thread_deck_id,
                        dream_mode=(dream_context is not None),
                    )
                except Exception:
                    logger.exception(
                        "Deck plugin pack failed for thread_id=%s deck_id=%s",
                        request.thread_id,
                        thread_deck_id,
                    )
                    raise
            elif dream_context is not None:
                raise ValueError("Story Workspace Dream turn requires a thread-locked Deck")
        elif dream_context is not None:
            raise ValueError("Story Workspace Dream turn requires Workspace Mode")

        dream_workbench_instruction: str | None = None
        turn_voice_system_prompt = request.system_prompt or None
        if dream_context is not None:
            dream_workbench_turn = await asyncio.to_thread(
                self._dream_workbench_context.refresh_for_turn,
                context=dream_context,
                workspace_root=cwd,
            )
            dream_workbench_instruction = dream_workbench_turn.instruction
            turn_voice_system_prompt = (
                await _resolve_story_workspace_dream_deck_prompt(
                    context=dream_context,
                    actor_id=request.user_id,
                )
            )

        # editor_session_id is user_sessions.id from /api/sessions, carried in
        # editor_state["id"].  This is distinct from state.session_id (Claude thread ID)
        # and os.path.basename(cwd) (workspace directory name).
        #
        # Soft-cache semantics: update AgentRunState.editor_state when the request
        # provides a snapshot (frontend snapshot takes priority); fall back to the
        # previously cached state when the request omits editor_state (pure-chat turn).
        state.with_editor_state(request.editor_state, int(request.user_id))
        # Resolve the active editor_state: prefer the freshly provided snapshot; fall
        # back to the flyweight cache so a resumed turn without a snapshot still sees
        # document context.
        active_editor_state = request.editor_state if request.editor_state is not None else state.editor_state
        editor_session_id: str = (active_editor_state or {}).get("id") or ""

        user_message_content = self._context_builder.build_user_message(
            request.message_parts,
            attachments=request.attachments,
            model=request.model,
            max_turns=request.max_turns,
            thread_id=state.session_id,
            resume=should_resume,
            cwd=cwd,
            editor_session_id=editor_session_id,
            voice_system_prompt=turn_voice_system_prompt,
            story_workspace_dream_context=dream_context,
            story_workspace_dream_workbench_instruction=(
                dream_workbench_instruction
            ),
        )

        server_runtime_env = {
            **request.model_runtime_env,
            **dict(self._claude_code_runtime_env_provider()),
        }
        run_options = AgentRunOptions(
            thread_id=thread_id_for_agent,
            user_message=user_message_content,
            canonical_user_id=str(request.user_id),
            gateway_idempotency_key=(
                "dream-turn-"
                + hashlib.sha256(
                    (
                        f"{request.user_id}\n{request.thread_id}\n"
                        f"{request.message_id}"
                    ).encode("utf-8")
                ).hexdigest()
                if request.message_id
                else None
            ),
            resume=should_resume,
            model=request.model,
            cwd=cwd or None,
            claude_tmp_workspace=claude_tmp_workspace,
            claude_config_home=claude_config_home,
            claude_secure_storage_home=claude_secure_storage_home,
            claude_mcp_servers=claude_mcp_servers,
            notion_credential_home=notion_credential_home,
            max_turns=request.max_turns,
            tool_choice=request.tool_choice,  # type: ignore[arg-type]
            im_full_access_enabled=im_full_access_enabled,
            sandbox_network_mode=sandbox_network_mode,  # type: ignore[arg-type]
            system_prompt=state.system_prompt,
            mcp_env={
                **user_env_vars,
                "INK_AGENT_USER_ID": str(request.user_id),
                "INK_AGENT_THREAD_ID": state.session_id,
                **(
                    {
                        "INK_AGENT_WORKFLOW_RUN_ID": (
                            dream_context.workflow_run_id
                        ),
                        **(
                            {
                                "INK_AGENT_STORY_WORKSPACE_MESSAGE_ID": (
                                    request.message_id
                                )
                            }
                            if isinstance(request.message_id, str)
                            and request.message_id.startswith("dream_agent_")
                            else {}
                        ),
                    }
                    if dream_context is not None
                    else {}
                ),
            },
            user_sdk_env=user_env_vars,
            server_runtime_env=server_runtime_env,
            editor_state=active_editor_state,
            # Live getter: agent_runner._pre_tool_use_hook calls this instead of
            # reading opts.editor_state so it always sees the AgentRunState
            # flyweight's latest value (updated after each write-tool DB refresh).
            editor_state_getter=(lambda s=state: s.editor_state) if active_editor_state is not None else None,
            # Live setter: agent_runner._post_tool_use_hook calls this after a
            # successful switch_editor tool call to update the flyweight with the
            # new session's editor_state loaded from the database.
            editor_state_setter=(lambda v, s=state: s.with_editor_state(v, s.editor_user_id)) if active_editor_state is not None else None,
        )

        dream_artifact_turn_ticket: DreamArtifactTurnTicket | None = None
        if dream_context is not None:
            if not cwd:
                raise RuntimeError("Dream runtime assembly has no server-owned workspace")
            await self._dream_runtime_init_activator(
                context=dream_context,
                actor_id=request.user_id,
                cwd=cwd,
                # Runtime receipts bind to the canonical Thread assembled for
                # this turn. The Claude SDK transcript/session remains owned by
                # the unchanged Phase 3 runner and normal Chat persistence.
                remote_session_ref=request.thread_id,
            )
            dream_artifact_turn_ticket = (
                self._dream_artifact_turn_hook.before_main_turn(
                    context=dream_context,
                    actor_id=request.user_id,
                    cwd=cwd,
                )
            )
            if dream_auto_repair_metadata_is_valid(request.message_metadata):
                metadata = dict(request.message_metadata or {})
                if (
                    metadata.get("dispatch_status")
                    != DREAM_AUTO_REPAIR_DISPATCHED
                    or metadata.get("workflowRunId")
                    != dream_context.workflow_run_id
                    or request.thread_id != dream_context.thread_id
                    or not isinstance(request.message_id, str)
                    or not request.message_id
                ):
                    raise DreamAutoRepairError(
                        "DREAM_AUTO_REPAIR_IDENTITY_INVALID",
                        "Dream 自动修正执行身份不可验证，已安全停止。",
                    )
                cleanup = (
                    self._dream_artifact_turn_hook
                    .resolve_auto_repair_project_cleanup_scope(
                        dream_artifact_turn_ticket,
                        validation_code=str(metadata["validationCode"]),
                    )
                )
                try:
                    persisted_cleanup = (
                        dream_auto_repair_project_cleanup_from_metadata(
                            metadata
                        )
                    )
                except ValueError as exc:
                    raise DreamAutoRepairError(
                        "DREAM_AUTO_REPAIR_IDENTITY_INVALID",
                        "Dream 自动修正项目根身份不可验证，已安全停止。",
                        cause=exc,
                    ) from exc
                if cleanup != persisted_cleanup:
                    raise DreamAutoRepairError(
                        "DREAM_AUTO_REPAIR_IDENTITY_INVALID",
                        "Dream 自动修正项目根事实已变化，已安全停止。",
                    )
                if cleanup is not None:
                    trusted_project_slug, stale_project_slugs = cleanup
                    run_options.dream_auto_repair_scope = (
                        DreamAutoRepairExecutionScope(
                            schema_version=(
                                DREAM_AUTO_REPAIR_EXECUTION_SCHEMA_VERSION
                            ),
                            message_id=request.message_id,
                            originating_turn_id=str(
                                metadata["originatingTurnId"]
                            ),
                            workflow_run_id=dream_context.workflow_run_id,
                            thread_id=dream_context.thread_id,
                            actor_id=str(request.user_id),
                            repair_attempt=int(metadata["repairAttempt"]),
                            validation_code=str(metadata["validationCode"]),
                            trusted_project_slug=trusted_project_slug,
                            stale_project_slugs=stale_project_slugs,
                        )
                    )
                    # The visible message is a durable conversation fact;
                    # WORKBENCH.md is the matching server-owned filesystem fact
                    # that a fresh Claude Session must read before acting.
                    await asyncio.to_thread(
                        self._dream_workbench_context.refresh_for_turn,
                        context=dream_context,
                        workspace_root=cwd,
                        auto_repair_project_cleanup=cleanup,
                        auto_repair_validation_code=str(
                            metadata["validationCode"]
                        ),
                        auto_repair_attempt=int(metadata["repairAttempt"]),
                    )

        from claude_agent.event_bus import BusProxyQueue

        confirmation_store = ToolConfirmationStore(
            thread_id=state.session_id,
            turn_id=state.current_turn_id,
        )
        turn_ctx = _TurnContext(
            queue=BusProxyQueue(bus),
            confirmation_store=confirmation_store,
        )
        state.turn_context = turn_ctx

        return _TurnExecution(
            request=request,
            state=state,
            runner=runner,
            run_options=run_options,
            turn_context=turn_ctx,
            dream_context=dream_context,
            dream_artifact_turn_ticket=dream_artifact_turn_ticket,
            resume_existing_session=resume_existing_session,
        )

    # ------------------------------------------------------------------
    # Phase 3: Session Execution
    # ------------------------------------------------------------------

    async def execute_session(
        self,
        execution: "_TurnExecution",
    ) -> ClaudeAgentTurnContinuation | None:
        """Execute a turn and unconditionally release confirmation resources."""

        try:
            return await self._execute_session_inner(execution)
        finally:
            # Timeout/reject leaves only a bounded tombstone while the turn is
            # active.  Every terminal/error/cancellation path clears both live
            # policy/Futures and those tombstones before the factory drops the
            # turn context.
            execution.turn_context.confirmation_store.cancel_all()

    async def _execute_session_inner(
        self,
        execution: "_TurnExecution",
    ) -> ClaudeAgentTurnContinuation | None:
        """Stream the agent turn and emit SSE events via the queue.

        User message is persisted immediately before inference starts so that
        thread-switching in the frontend (which disconnects the SSE stream) does
        not lose the user's turn.  Partial assistant content is flushed on
        CancelledError so resumed views can show in-progress tool invocations.
        """
        queue = execution.turn_context.queue
        store = execution.turn_context.confirmation_store

        # --- P2 fix: save user message immediately before inference ---
        await self._persist_user_message(execution)

        # Emit session metadata header
        await queue.put(
            _event(
                "message-metadata",
                {
                    "sessionId": execution.state.session_id,
                    "turnIndex": execution.state.turn_count,
                    "turnId": execution.state.current_turn_id,
                },
            )
        )

        error_event_emitted = False
        emit_error = self._make_error_cb(queue)

        async def on_error(exc: Exception) -> None:
            nonlocal error_event_emitted
            if error_event_emitted:
                return
            error_event_emitted = True
            await emit_error(exc)

        callbacks = AgentStreamingCallbacks(
            on_text_delta=self._make_text_delta_cb(queue, execution.turn_context),
            on_text_done=self._make_text_done_cb(queue, execution.turn_context),
            on_tool_event=self._make_tool_event_cb(
                queue, execution.turn_context, execution.state
            ),
            on_tool_confirmation_request=self._make_tool_confirm_cb(queue, store, execution.turn_context),
            on_error=on_error,
            on_message=partial(self._persist_sdk_session_from_message, execution),
            on_plan_file_changed=self._make_plan_file_changed_cb(queue, execution.state),
            on_tasks_changed=self._make_tasks_changed_cb(queue, execution.state),
        )

        try:
            result = await execution.runner.run_streaming(execution.run_options, callbacks)
        except asyncio.CancelledError:
            # Explicit stop / shutdown cancellation — flush partial assistant
            # content so the next load of this thread shows completed pieces.
            await self._persist_partial_assistant(execution, turn_status="cancelled")
            try:
                await self.mark_auto_repair_failed(execution.request)
            except Exception:
                logger.exception(
                    "Dream auto-repair cancellation status could not be persisted "
                    "thread_id=%s message_id=%s",
                    execution.request.thread_id,
                    execution.request.message_id,
                )
            await _put_terminal(
                queue,
                _event(
                    "finish",
                    {"finishReason": "stop", "cancelled": True},
                ),
            )
            raise

        if result.success and getattr(result, "protocol_completed", None) is not False:
            full_text = result.full_text
            # A completed Claude Turn is an immutable conversation fact even
            # when the Dream workspace postcondition requests one repair Turn
            # or ultimately fails.  Commit the exact collected SSE parts first;
            # the Hook may mutate projection state, never Chat history truth.
            await self._persist_assistant_turn(execution, result)
            dream_artifact_turn_ticket = getattr(
                execution,
                "dream_artifact_turn_ticket",
                None,
            )
            if dream_artifact_turn_ticket is not None:
                try:
                    sync_result = await asyncio.to_thread(
                        self._dream_artifact_turn_hook.after_main_turn,
                        dream_artifact_turn_ticket,
                    )
                    logger.info(
                        "Dream workbench synchronized run_id=%s changed_stages=%s "
                        "private_artifact_changed=%s private_files=%s "
                        "story_index_status=%s",
                        execution.dream_context.workflow_run_id
                        if execution.dream_context is not None
                        else "",
                        list(sync_result.changed_stages),
                        sync_result.private_artifact_changed,
                        len(sync_result.private_files),
                        sync_result.story_index_status,
                    )
                except DreamArtifactTurnHookError as exc:
                    logger.exception(
                        "Dream workbench synchronization failed for thread_id=%s",
                        execution.request.thread_id,
                    )
                    if dream_auto_repair_metadata_is_valid(
                        execution.request.message_metadata
                    ):
                        await self.mark_auto_repair_failed(execution.request)
                        raise DreamAutoRepairExhaustedError(exc.issue.code) from exc
                    if (
                        exc.issue.repairability
                        is DreamArtifactRepairability.AGENT_REPAIRABLE
                    ):
                        return await self._build_dream_auto_repair_continuation(
                            execution,
                            result=result,
                            error=exc,
                        )
                    # Artifact publication is a root-turn postcondition, not an
                    # optional Observer projection. Propagate through the same
                    # Chat turn terminal path; never emit a second lifecycle.
                    raise
                except Exception:
                    logger.exception(
                        "Dream workbench synchronization failed for thread_id=%s",
                        execution.request.thread_id,
                    )
                    if dream_auto_repair_metadata_is_valid(
                        execution.request.message_metadata
                    ):
                        await self.mark_auto_repair_failed(execution.request)
                    raise
            await queue.put(
                _event("message-final", {
                    "text": full_text,
                    "usage": result.usage,
                    "sessionId": result.session_id,
                })
            )
            # A structured story proposal is persisted before the terminal frame
            # so Dream can open the canonical review panel without polling or
            # trusting client-derived provenance.
            story_output = await self._store_story_workspace_output(execution, full_text)
            if story_output is not None:
                await queue.put(_event("story-workspace-output", story_output))
            terminal = _event("finish", {"finishReason": "stop"})
        else:
            result_error = result.error or RuntimeError(
                "Claude turn ended without a trustworthy terminal ResultMessage."
            )
            error_msg = _format_exception_for_sse(result_error)
            if not error_event_emitted:
                error_event_emitted = True
                await queue.put(_event("error", {"errorText": error_msg}))
            # Even on error, flush whatever partial assistant content was collected.
            await self._persist_partial_assistant(execution, turn_status="error")
            await self.mark_auto_repair_failed(execution.request)
            terminal = _event("finish", {"finishReason": "error"})

        await _put_terminal(queue, terminal)
        return None

    async def _build_dream_auto_repair_continuation(
        self,
        execution: "_TurnExecution",
        *,
        result: Any,
        error: DreamArtifactTurnHookError,
    ) -> ClaudeAgentTurnContinuation:
        """Persist and announce one allowlisted user fact before continuing."""

        dream_context = execution.dream_context
        originating_message_id = execution.request.message_id
        originating_turn_id = execution.state.current_turn_id
        if dream_context is None:
            raise DreamAutoRepairError(
                "DREAM_AUTO_REPAIR_IDENTITY_INVALID",
                "Dream 自动修正缺少可信 Run 上下文，已安全停止。",
            )
        if (
            isinstance(execution.request.message_metadata, Mapping)
            and execution.request.message_metadata.get("kind")
            == DREAM_AUTO_REPAIR_METADATA_KIND
        ):
            raise DreamAutoRepairExhaustedError(error.issue.code)
        dream_artifact_turn_ticket = getattr(
            execution,
            "dream_artifact_turn_ticket",
            None,
        )
        if dream_artifact_turn_ticket is None:
            raise DreamAutoRepairError(
                "DREAM_AUTO_REPAIR_IDENTITY_INVALID",
                "Dream 自动修正缺少可信工作区校验身份，已安全停止。",
            )
        project_cleanup = await asyncio.to_thread(
            self._dream_artifact_turn_hook.resolve_auto_repair_project_cleanup_scope,
            dream_artifact_turn_ticket,
            validation_code=error.issue.code,
        )
        message = build_dream_auto_repair_message(
            issue=error.issue,
            workflow_run_id=dream_context.workflow_run_id,
            thread_id=execution.request.thread_id,
            originating_message_id=str(originating_message_id or ""),
            originating_turn_id=str(originating_turn_id or ""),
            project_cleanup=project_cleanup,
        )
        await asyncio.to_thread(persist_dream_auto_repair_message, message)
        dispatch_claimed = False
        try:
            # ``dispatched`` is committed before publication so SSE, history,
            # and the next Turn share one exact message representation.
            await self._settle_auto_repair_message(
                message,
                DREAM_AUTO_REPAIR_DISPATCHED,
            )
            dispatch_claimed = True
            await self._persist_auto_repair_resume_session(execution, result)
            await execution.turn_context.queue.put(
                _event("chat-message", {"message": message.sse_message()})
            )
        except BaseException:
            # The message remains a durable conversation fact when resume or
            # EventBus publication fails. Do not mask cancellation or the
            # original fail-closed exception with a status-write failure.
            if dispatch_claimed:
                try:
                    await self._settle_auto_repair_message(
                        message,
                        DREAM_AUTO_REPAIR_FAILED,
                    )
                except Exception:
                    logger.exception(
                        "Dream auto-repair dispatch failure status could not be persisted "
                        "thread_id=%s message_id=%s",
                        message.thread_id,
                        message.id,
                    )
            raise
        continuation_request = replace(
            execution.request,
            reconnect=False,
            resume=True,
            message_id=message.id,
            message_parts=message.persistence_parts(),
            message_metadata=dict(message.metadata),
            attachments=None,
        )
        return ClaudeAgentTurnContinuation(request=continuation_request)

    @staticmethod
    async def _settle_auto_repair_message(
        message: Any,
        status: str,
    ) -> None:
        transitioned = await asyncio.to_thread(
            settle_dream_auto_repair_message,
            message.id,
            thread_id=message.thread_id,
            expected_metadata=dict(message.metadata),
            status=status,
        )
        if status == DREAM_AUTO_REPAIR_DISPATCHED and not transitioned:
            raise DreamAutoRepairError(
                "DREAM_AUTO_REPAIR_ALREADY_DISPATCHED",
                "Dream 自动修正已由同一条持久化消息启动，未重复执行。",
            )
        message.metadata["dispatch_status"] = status

    @staticmethod
    async def _persist_auto_repair_resume_session(
        execution: "_TurnExecution",
        result: Any,
    ) -> None:
        """Make the first Claude transcript resumable before the repair Turn."""

        captured_session_id = str(getattr(result, "session_id", None) or "").strip()
        if captured_session_id:
            try:
                await asyncio.to_thread(
                    _db.update_chat_thread_claude_session,
                    execution.request.thread_id,
                    captured_session_id,
                    _AGENT_RUNTIME_CONTRACT_VERSION,
                )
                return
            except Exception as exc:
                raise DreamAutoRepairError(
                    "DREAM_AUTO_REPAIR_RESUME_UNAVAILABLE",
                    "Dream 自动修正无法安全续接 Claude 会话，已停止自动修正。",
                    cause=exc,
                ) from exc
        try:
            existing = await asyncio.to_thread(
                _db.get_chat_thread,
                execution.request.thread_id,
                int(execution.request.user_id),
            )
        except Exception as exc:
            raise DreamAutoRepairError(
                "DREAM_AUTO_REPAIR_RESUME_UNAVAILABLE",
                "Dream 自动修正无法安全续接 Claude 会话，已停止自动修正。",
                cause=exc,
            ) from exc
        if not _has_usable_claude_resume(existing):
            raise DreamAutoRepairError(
                "DREAM_AUTO_REPAIR_RESUME_UNAVAILABLE",
                "Dream 自动修正无法安全续接 Claude 会话，已停止自动修正。",
            )

    @staticmethod
    async def _settle_auto_repair(
        request: ClaudeAgentRunRequest,
        status: str,
    ) -> None:
        metadata = request.message_metadata
        if not dream_auto_repair_metadata_is_valid(metadata):
            return
        await asyncio.to_thread(
            settle_dream_auto_repair_message,
            str(request.message_id or ""),
            thread_id=request.thread_id,
            expected_metadata=dict(metadata),
            status=status,
        )

    async def mark_auto_repair_failed(
        self,
        request: ClaudeAgentRunRequest,
    ) -> None:
        """Durably settle an internal repair request as failed."""

        if not dream_auto_repair_metadata_is_valid(request.message_metadata):
            return
        await self._settle_auto_repair(request, DREAM_AUTO_REPAIR_FAILED)

    async def _store_story_workspace_output(
        self,
        execution: "_TurnExecution",
        full_text: str,
    ) -> Optional[dict[str, Any]]:
        """Persist an explicit JSON story bundle without changing Chat outcome."""

        if execution.dream_context is not None:
            return None

        thread_id = execution.request.thread_id
        candidate = (full_text or "").strip()
        is_structured_candidate = candidate.startswith("{") or (
            candidate.startswith("```json") and candidate.endswith("```")
        )
        payload = parse_agent_story_output(full_text)
        if payload is None:
            if is_structured_candidate:
                logger.warning(
                    "Agent story integration skipped thread_id=%s stage=parse_or_validate",
                    thread_id,
                )
            return None

        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(
                None,
                _store_story_workspace_output_sync,
                int(execution.request.user_id),
                thread_id,
                payload,
            )
        except Exception:
            logger.exception(
                "Agent story integration failed thread_id=%s stage=store",
                thread_id,
            )
            return None

    async def _persist_user_message(self, execution: "_TurnExecution") -> None:
        """Persist the user message immediately before inference starts (P2 fix).

        Saving the user turn before calling runner.run_streaming ensures the
        message is visible in the thread history even when the SSE stream is
        cancelled mid-flight (e.g. the user switches threads).
        """
        import database

        thread_id = execution.request.thread_id
        user_message_id = execution.request.message_id
        user_parts = execution.request.message_parts
        message_metadata = execution.request.message_metadata
        try:
            from services.story_workspace.dream_confirmation_service import (
                StoryWorkspaceDreamConfirmationError,
                story_workspace_guard_persisted_dream_confirmation_turn,
            )
        except ModuleNotFoundError:
            from backend.services.story_workspace.dream_confirmation_service import (
                StoryWorkspaceDreamConfirmationError,
                story_workspace_guard_persisted_dream_confirmation_turn,
            )

        def _save_user() -> None:
            resolved_user_parts: list = list(user_parts) if user_parts else [{"type": "text", "text": ""}]
            db = database.get_db()
            try:
                is_persisted_dream_confirmation = (
                    story_workspace_guard_persisted_dream_confirmation_turn(
                        db,
                        thread_id=thread_id,
                        actor_id=str(execution.request.user_id),
                        message_id=user_message_id,
                        parts=resolved_user_parts,
                        metadata=message_metadata,
                    )
                )
            finally:
                db.close()
            if is_persisted_dream_confirmation:
                # The confirmation service owns this pre-persisted hidden row.
                # In particular, never replace its newer durable claim lease
                # with the older request snapshot carried through a thread lock.
                return
            database.save_chat_message(
                thread_id, "user",
                parts=resolved_user_parts,
                message_id=user_message_id,
                metadata=message_metadata,
            )
            # Auto-fill thread title from first user message if still NULL.
            thread = database.get_chat_thread(thread_id, int(execution.request.user_id))
            if thread and not thread.get("title"):
                title = _extract_text_from_parts(user_parts).strip()[:MAX_THREAD_TITLE_LENGTH]
                database.update_chat_thread_title(thread_id, title)

        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, _save_user)
        except StoryWorkspaceDreamConfirmationError:
            logger.exception(
                "Rejected non-authoritative Dream control persistence "
                "for thread_id=%s",
                thread_id,
            )
            raise
        except (
            database.ChatMessageIdentityConflict,
            database.PostgresError,
        ):
            logger.exception(
                "Canonical user message persistence rejected for thread_id=%s",
                thread_id,
            )
            raise
        except Exception:
            logger.exception(
                "Failed to persist user message for thread_id=%s", thread_id
            )

    async def _persist_partial_assistant(
        self,
        execution: "_TurnExecution",
        *,
        turn_status: str = "error",
    ) -> None:
        """Flush partial assistant content collected so far (called on cancel/error).

        Converts whatever SSE events were collected before cancellation into
        UIMessage parts and upserts an assistant row.  The row is marked with
        ``is_partial=True`` in metadata so the frontend can show an appropriate
        indicator.  If no collectible events exist the call is a no-op.
        """
        import database

        turn_ctx = execution.turn_context
        if not turn_ctx or not turn_ctx.collected_parts:
            return

        asst_parts = _sse_events_to_ui_parts(turn_ctx.collected_parts)
        if not asst_parts:
            return

        thread_id = execution.request.thread_id
        asst_metadata: dict = {
            "is_partial": True,
            "turnId": execution.state.current_turn_id,
            "turnStatus": turn_status,
        }
        _attach_story_workspace_dream_assistant_source(
            asst_metadata,
            execution.request,
            execution.dream_context,
        )
        if execution.request.model:
            asst_metadata["chatModel"] = {"provider": "gateway", "model": execution.request.model}
        tool_count = sum(1 for p in asst_parts if p.get("type") == "tool-invocation")
        if tool_count:
            asst_metadata["toolCount"] = tool_count

        def _save_partial() -> None:
            database.save_chat_message(
                thread_id, "assistant",
                parts=asst_parts,
                metadata=asst_metadata,
            )

        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, _save_partial)
        except Exception:
            logger.exception(
                "Failed to persist partial assistant for thread_id=%s", thread_id
            )

    async def _persist_sdk_session_from_message(
        self,
        execution: "_TurnExecution",
        message: Any,
    ) -> None:
        """Persist the SDK-native Session ID as soon as the stream exposes it."""

        data = getattr(message, "data", None)
        if not isinstance(data, Mapping):
            return
        session_id = str(data.get("session_id") or "").strip()
        if not session_id:
            return
        resumed_session_id = str(
            (execution.resume_existing_session or {}).get("claude_session_id") or ""
        ).strip()
        if session_id == resumed_session_id:
            return
        try:
            await asyncio.to_thread(
                _db.update_chat_thread_claude_session,
                execution.request.thread_id,
                session_id,
                _AGENT_RUNTIME_CONTRACT_VERSION,
            )
        except Exception:
            logger.exception(
                "Failed to persist observed Claude Session: thread_id=%s",
                execution.request.thread_id,
            )

    async def _persist_assistant_turn(
        self, execution: "_TurnExecution", result: Any
    ) -> None:
        """Save the completed assistant message after a successful turn.

        User message was already saved by _persist_user_message.  This method
        saves the assistant message + updates claude_session_id on chat_thread.
        Aligned with better-chatbot onFinish / chatRepository.upsertMessage.
        """
        import database

        thread_id = execution.request.thread_id
        assistant_text: str = result.full_text if result else ""
        turn_ctx = execution.turn_context

        def _save_assistant() -> None:
            asst_parts: list = _sse_events_to_ui_parts(turn_ctx.collected_parts)
            if not asst_parts:
                asst_parts = [{"type": "text", "text": assistant_text}] if assistant_text else []

            asst_metadata: dict = {}
            final_part_index = _completed_turn_final_part_index(asst_parts)
            asst_metadata["turnId"] = execution.state.current_turn_id
            if final_part_index is not None:
                asst_metadata["turnStatus"] = "completed"
                asst_metadata["finalPartIndex"] = final_part_index
            duration_ms = getattr(result, "duration_ms", None)
            if (
                isinstance(duration_ms, int)
                and not isinstance(duration_ms, bool)
                and duration_ms >= 0
            ):
                asst_metadata["durationMs"] = duration_ms
            _attach_story_workspace_dream_assistant_source(
                asst_metadata,
                execution.request,
                execution.dream_context,
            )
            if result and result.usage:
                input_t = result.usage.get("input_tokens")
                output_t = result.usage.get("output_tokens")
                asst_metadata["usage"] = {
                    "inputTokens": input_t,
                    "outputTokens": output_t,
                    "totalTokens": result.usage.get("total_tokens") or (
                        (input_t or 0) + (output_t or 0)
                    ),
                }
            if execution.request.model:
                asst_metadata["chatModel"] = {
                    "provider": "gateway",
                    "model": execution.request.model,
                }
            tool_count = sum(1 for p in asst_parts if p.get("type") == "tool-invocation")
            if tool_count:
                asst_metadata["toolCount"] = tool_count

            database.save_chat_message(
                thread_id, "assistant",
                parts=asst_parts,
                metadata=asst_metadata or None,
                history_final_text=(
                    asst_parts[final_part_index]["text"]
                    if final_part_index is not None
                    else None
                ),
                history_process_available=(
                    final_part_index is not None and final_part_index > 0
                ),
                history_projection_version=(
                    1 if final_part_index is not None else None
                ),
            )

        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, _save_assistant)
        except Exception as exc:
            logger.exception(
                "Failed to persist assistant message for thread_id=%s", thread_id
            )
            raise ClaudeAgentAssistantPersistenceError() from exc

        captured_session_id = result.session_id if result else None
        if captured_session_id:
            try:
                await loop.run_in_executor(
                    None,
                    _db.update_chat_thread_claude_session,
                    thread_id,
                    captured_session_id,
                    _AGENT_RUNTIME_CONTRACT_VERSION,
                )
            except Exception:
                # The SDK on_message callback already owns eager Session
                # persistence.  Its successful assistant row must not be
                # reclassified as missing if this idempotent safeguard fails.
                logger.exception(
                    "Failed to persist completed Claude Session for thread_id=%s",
                    thread_id,
                )

    # Keep _persist_turn as a legacy alias used by test stubs / older callers.
    async def _persist_turn(
        self, execution: "_TurnExecution", result: Any
    ) -> None:
        """Deprecated: use _persist_user_message + _persist_assistant_turn instead.

        Kept for backward compatibility with any test stubs that call this directly.
        """
        await self._persist_user_message(execution)
        await self._persist_assistant_turn(execution, result)

    # ------------------------------------------------------------------
    # Tool confirmation (called from HTTP endpoint via factory)
    # ------------------------------------------------------------------

    async def confirm_tool(
        self,
        state: AgentRunState,
        tool_call_id: str,
        approved: bool,
        reason: Optional[str] = None,
        answers: Optional[dict[str, Any]] = None,
        *,
        thread_id: str,
        turn_id: str,
    ) -> ToolConfirmationResolution | None:
        """Validate and resolve one exact active-turn confirmation."""

        if state.session_id != thread_id or state.current_turn_id != turn_id:
            logger.warning(
                "confirm_tool: active turn changed for session_id=%s",
                state.session_id,
            )
            return None
        turn_ctx = state.turn_context
        if turn_ctx is None:
            logger.warning(
                "confirm_tool: no active turn_context for session_id=%s", state.session_id
            )
            return None
        result = ToolConfirmationResult(approved=approved, reason=reason, answers=answers)
        try:
            return await turn_ctx.confirmation_store.resolve_exact(
                thread_id=thread_id,
                turn_id=turn_id,
                tool_call_id=tool_call_id,
                result=result,
            )
        except ToolConfirmationNotPending:
            return None

    # ------------------------------------------------------------------
    # SSE callback factories (aligned with Pawkeyland SSE protocol)
    # ------------------------------------------------------------------

    @staticmethod
    def _make_text_delta_cb(
        queue: asyncio.Queue, turn_ctx: _TurnContext
    ):
        async def on_text_delta(delta: str) -> None:
            # Emit text-start when this is the first delta of a new text block.
            last_type = turn_ctx.collected_parts[-1].get("type") if turn_ctx.collected_parts else None
            if last_type not in ("text-start", "text-delta"):
                await queue.put(_event("text-start", {"id": _TEXT_PART_ID}))
                turn_ctx.collected_parts.append({"type": "text-start", "id": _TEXT_PART_ID})
            await queue.put(_event("text-delta", {"id": _TEXT_PART_ID, "delta": delta}))
            turn_ctx.collected_parts.append({"type": "text-delta", "id": _TEXT_PART_ID, "delta": delta})

        return on_text_delta

    @staticmethod
    def _make_text_done_cb(queue: asyncio.Queue, turn_ctx: _TurnContext):
        async def on_text_done(full_text: str) -> None:
            if full_text:
                await queue.put(_event("text-end", {"id": _TEXT_PART_ID}))
                turn_ctx.collected_parts.append({"type": "text-end", "id": _TEXT_PART_ID})

        return on_text_done

    @staticmethod
    def _make_tool_event_cb(
        queue: asyncio.Queue,
        turn_ctx: _TurnContext,
        state: Optional[Any] = None,
    ):
        """Emit SSE tool / reasoning events and collect them into collected_parts.

        Each SSE event is both emitted to ``queue`` (frontend) and appended to
        ``collected_parts`` (persistence).  The conversion to UIMessage parts
        happens later in ``_sse_events_to_ui_parts()``.

        Collected → SSE event type stored in collected_parts:
          ``thinking_delta``               → reasoning-start (first), reasoning-delta
          ``content_block_stop``           → reasoning-end
          ``thinking`` (atomic)            → reasoning-start, reasoning-delta, reasoning-end
          ``tool_use`` / ``tool_use_start``→ tool-input-available (when input present)
          ``tool_input_delta``             → tool-input-delta (live preview only)
          ``tool_input_available``         → tool-input-available
          ``tool_result``                  → tool-output-available

        Not collected: tool-input-start (no data payload), tool-input-delta
        (live preview only), tool-approval-request.
        Ignored entirely: result, message_*, tool_progress, tool_use_summary, etc.

        After a successful ``tool_result`` for any tool in ``_EDITOR_WRITE_TOOL_NAMES``,
        the method reloads ``editor_state`` from the database and updates
        ``state.editor_state`` (the AgentRunState flyweight).  The PreToolUse hook in
        agent_runner reads editor_state via ``opts.editor_state_getter`` which is bound
        to ``state.editor_state``, so subsequent same-turn virtual-index reads
        automatically see the refreshed data without any additional opts patching.
        """
        async def on_tool_event(payload: ToolEventPayload) -> None:
            tool_call_id = payload.tool_call_id
            tool_name = payload.tool_name
            event_type = payload.type

            # --- thinking_delta: incremental reasoning stream ---
            if event_type == "thinking_delta" and payload.output:
                if not turn_ctx.current_reasoning_id:
                    turn_ctx.current_reasoning_id = str(uuid4())
                    await queue.put(_event("reasoning-start", {"id": turn_ctx.current_reasoning_id}))
                    turn_ctx.collected_parts.append({"type": "reasoning-start", "id": turn_ctx.current_reasoning_id})
                turn_ctx.has_thinking_delta = True
                delta_text = str(payload.output)
                turn_ctx.current_reasoning_text.append(delta_text)
                await queue.put(_event("reasoning-delta", {"id": turn_ctx.current_reasoning_id, "delta": delta_text}))
                turn_ctx.collected_parts.append({"type": "reasoning-delta", "id": turn_ctx.current_reasoning_id, "delta": delta_text})
                return

            # --- content_block_stop for streamed thinking ---
            if event_type == "content_block_stop" and isinstance(payload.output, dict):
                content_block = payload.output.get("content_block")
                if (
                    isinstance(content_block, dict)
                    and content_block.get("type") == "thinking"
                    and turn_ctx.has_thinking_delta
                    and turn_ctx.current_reasoning_id
                ):
                    await queue.put(_event("reasoning-end", {"id": turn_ctx.current_reasoning_id}))
                    turn_ctx.collected_parts.append({"type": "reasoning-end", "id": turn_ctx.current_reasoning_id})
                    turn_ctx.completed_streamed_reasoning_texts.append(
                        str(content_block.get("thinking") or "".join(turn_ctx.current_reasoning_text))
                    )
                    turn_ctx.current_reasoning_id = None
                    turn_ctx.has_thinking_delta = False
                    turn_ctx.current_reasoning_text.clear()
                    return

            # --- thinking: complete reasoning block (non-streamed or dedup guard) ---
            if event_type == "thinking" and payload.output:
                thinking_output = str(payload.output)
                if (
                    turn_ctx.completed_streamed_reasoning_texts
                    and thinking_output == turn_ctx.completed_streamed_reasoning_texts[0]
                ):
                    turn_ctx.completed_streamed_reasoning_texts.pop(0)
                    return
                if turn_ctx.has_thinking_delta and turn_ctx.current_reasoning_id:
                    await queue.put(_event("reasoning-end", {"id": turn_ctx.current_reasoning_id}))
                    turn_ctx.collected_parts.append({"type": "reasoning-end", "id": turn_ctx.current_reasoning_id})
                    turn_ctx.current_reasoning_id = None
                    turn_ctx.has_thinking_delta = False
                    turn_ctx.current_reasoning_text.clear()
                    return
                reasoning_id = str(uuid4())
                await queue.put(_event("reasoning-start", {"id": reasoning_id}))
                turn_ctx.collected_parts.append({"type": "reasoning-start", "id": reasoning_id})
                await queue.put(_event("reasoning-delta", {"id": reasoning_id, "delta": thinking_output}))
                turn_ctx.collected_parts.append({"type": "reasoning-delta", "id": reasoning_id, "delta": thinking_output})
                await queue.put(_event("reasoning-end", {"id": reasoning_id}))
                turn_ctx.collected_parts.append({"type": "reasoning-end", "id": reasoning_id})
                return

            # --- tool_use / tool_use_start: new tool call beginning ---
            if event_type in ("tool_use", "tool_use_start") and tool_call_id and tool_name:
                # Track name so tool_result can identify editor write tools.
                turn_ctx.tool_name_by_id[tool_call_id] = tool_name
                if isinstance(payload.input, dict):
                    turn_ctx.tool_input_by_id[tool_call_id] = dict(payload.input)
                if tool_call_id not in turn_ctx.registered_tool_call_ids:
                    turn_ctx.registered_tool_call_ids.add(tool_call_id)
                    await queue.put(_event("tool-input-start", {"toolCallId": tool_call_id, "toolName": tool_name}))
                if payload.input is not None and tool_call_id not in turn_ctx.emitted_tool_input_ids:
                    turn_ctx.emitted_tool_input_ids.add(tool_call_id)
                    evt = {"type": "tool-input-available", "toolCallId": tool_call_id, "toolName": tool_name, "input": payload.input}
                    await queue.put(_event("tool-input-available", {"toolCallId": tool_call_id, "toolName": tool_name, "input": payload.input}))
                    turn_ctx.collected_parts.append(evt)
                    await _observe_plan_mode_transition(queue, state, tool_call_id, tool_name)
                    await _observe_todo_write(queue, state, tool_name, payload.input)
                return

            # --- tool_input_delta: streamed tool JSON input for live previews ---
            if event_type == "tool_input_delta" and tool_call_id and tool_name:
                turn_ctx.tool_name_by_id[tool_call_id] = tool_name
                if tool_call_id not in turn_ctx.registered_tool_call_ids:
                    turn_ctx.registered_tool_call_ids.add(tool_call_id)
                    await queue.put(_event("tool-input-start", {"toolCallId": tool_call_id, "toolName": tool_name}))
                delta_text = "" if payload.output is None else str(payload.output)
                if delta_text:
                    await queue.put(_event("tool-input-delta", {"toolCallId": tool_call_id, "toolName": tool_name, "delta": delta_text}))
                return

            # --- tool_input_available: complete streamed JSON input ready ---
            if event_type == "tool_input_available" and tool_call_id and tool_name:
                # Track name so tool_result can identify editor write tools.
                turn_ctx.tool_name_by_id[tool_call_id] = tool_name
                if isinstance(payload.input, dict):
                    turn_ctx.tool_input_by_id[tool_call_id] = dict(payload.input)
                if tool_call_id not in turn_ctx.registered_tool_call_ids:
                    turn_ctx.registered_tool_call_ids.add(tool_call_id)
                    await queue.put(_event("tool-input-start", {"toolCallId": tool_call_id, "toolName": tool_name}))
                if tool_call_id not in turn_ctx.emitted_tool_input_ids:
                    turn_ctx.emitted_tool_input_ids.add(tool_call_id)
                    evt = {"type": "tool-input-available", "toolCallId": tool_call_id, "toolName": tool_name, "input": payload.input or {}}
                    await queue.put(_event("tool-input-available", {"toolCallId": tool_call_id, "toolName": tool_name, "input": payload.input or {}}))
                    turn_ctx.collected_parts.append(evt)
                    await _observe_plan_mode_transition(queue, state, tool_call_id, tool_name)
                    await _observe_todo_write(queue, state, tool_name, payload.input or {})
                return

            # --- tool_result: tool execution result ---
            if event_type == "tool_result" and tool_call_id:
                if tool_call_id not in turn_ctx.registered_tool_call_ids:
                    fallback_name = tool_name or "unknown"
                    logger.warning(
                        "tool_result for unregistered toolCallId=%s (toolName=%s). Auto-registering.",
                        tool_call_id, fallback_name,
                    )
                    turn_ctx.registered_tool_call_ids.add(tool_call_id)
                    await queue.put(_event("tool-input-start", {"toolCallId": tool_call_id, "toolName": fallback_name}))
                    turn_ctx.emitted_tool_input_ids.add(tool_call_id)
                    fallback_evt = {"type": "tool-input-available", "toolCallId": tool_call_id, "toolName": fallback_name, "input": {}}
                    await queue.put(_event("tool-input-available", {"toolCallId": tool_call_id, "toolName": fallback_name, "input": {}}))
                    turn_ctx.collected_parts.append(fallback_evt)
                resolved_tool_name = tool_name or turn_ctx.tool_name_by_id.get(tool_call_id, "")
                editor_result = (
                    _extract_editor_tool_result(payload.output)
                    if resolved_tool_name in _EDITOR_WRITE_TOOL_NAMES
                    else None
                )
                is_error = bool(payload.is_error) or _is_editor_tool_result_error(
                    resolved_tool_name, payload.output
                )
                evt = {"type": "tool-output-available", "toolCallId": tool_call_id, "output": payload.output, "isError": is_error}
                await queue.put(_event("tool-output-available", {"toolCallId": tool_call_id, "output": payload.output, "isError": is_error}))
                turn_ctx.collected_parts.append(evt)

                # Every actor/session-matched Editor result refreshes the single
                # AgentRunState cache from the DB. Success then publishes the existing
                # session event; business failures only replace stale read context so
                # same-turn retries cannot keep targeting a removed cell.
                if (
                    resolved_tool_name in _EDITOR_WRITE_TOOL_NAMES
                    and state is not None
                    and state.editor_state is not None
                ):
                    tool_input = turn_ctx.tool_input_by_id.get(tool_call_id) or {}
                    editor_session_id = str(
                        tool_input.get("editor_session_id") or ""
                    ).strip()
                    live_editor_session_id = str(
                        (state.editor_state or {}).get("id") or ""
                    ).strip()
                    user_id: int = state.editor_user_id
                    cache_refreshed = False
                    if (
                        editor_session_id
                        and editor_session_id == live_editor_session_id
                        and user_id
                    ):
                        try:
                            import database as _db_mod
                            fresh_row = await asyncio.to_thread(
                                _db_mod.get_session, user_id, editor_session_id
                            )
                            if fresh_row and fresh_row.get("editor_state"):
                                fresh_editor_state = fresh_row["editor_state"]
                                state.editor_state = fresh_editor_state
                                cache_refreshed = True
                                logger.debug(
                                    "editor_state refreshed from DB after %s "
                                    "(editor_session_id=%s user_id=%s)",
                                    resolved_tool_name, editor_session_id, user_id,
                                )
                        except Exception:
                            logger.warning(
                                "editor_state DB-reload failed after write tool=%s "
                                "editor_session_id=%s user_id=%s",
                                resolved_tool_name, editor_session_id, user_id,
                            )
                    write_succeeded = bool(
                        not is_error
                        and editor_result is not None
                        and editor_result.get("ok") is True
                    )
                    if write_succeeded and cache_refreshed:
                        await session_event_bus.publish(
                            EditSessionEvent(
                                type="session_updated",
                                session_id=editor_session_id,
                                user_id=str(user_id),
                                source="agent",
                                tool_call_id=tool_call_id,
                                tool_name=resolved_tool_name,
                            )
                        )
                return

        return on_tool_event

    @staticmethod
    def _make_tool_confirm_cb(
        queue: asyncio.Queue,
        store: ToolConfirmationStore,
        turn_ctx: _TurnContext,
    ):
        async def on_tool_confirmation_request(payload: dict[str, Any]) -> Optional[dict[str, Any]]:
            tool_call_id: str = payload.get("tool_call_id", "") or payload.get("toolCallId", "")
            tool_name: str = payload.get("tool_name", "") or payload.get("toolName", "")
            tool_input: dict[str, Any] = payload.get("input") or {}

            # Step 0: derive immutable server policy and atomically register it
            # together with the Future before any client-visible frame.  An SDK
            # duplicate may join only when the policy fingerprint is identical.
            policy = store.policy_from_payload(payload)
            policy_fingerprint = policy.fingerprint
            registered_fingerprint = (
                turn_ctx.confirmation_policy_fingerprints.get(tool_call_id)
            )
            if registered_fingerprint is not None:
                if registered_fingerprint != policy_fingerprint:
                    raise ToolConfirmationPolicyConflict(
                        "duplicate callback policy mismatch"
                    )
                registered = False
            else:
                registered = store.register_pending(policy)
                turn_ctx.confirmation_policy_fingerprints[
                    tool_call_id
                ] = policy_fingerprint
            if not registered:
                logger.debug(
                    "on_tool_confirmation_request: duplicate hook invocation for "
                    "tool_call_id=%s — joining existing Future",
                    tool_call_id,
                )
                try:
                    result = await store.await_pending(tool_call_id, tool_name=tool_name)
                    return {"approved": result.approved, "reason": result.reason, "answers": result.answers}
                except TimeoutError:
                    return {"approved": False, "reason": "timeout"}
                except asyncio.CancelledError:
                    store.cancel_pending(tool_call_id)
                    raise

            # Step 1: emit tool-input-start + tool-input-available with dedup so that
            # events already sent by _make_tool_event_cb are not repeated.
            if tool_call_id not in turn_ctx.registered_tool_call_ids:
                turn_ctx.registered_tool_call_ids.add(tool_call_id)
                await queue.put(_event("tool-input-start", {"toolCallId": tool_call_id, "toolName": tool_name}))
            if tool_call_id not in turn_ctx.emitted_tool_input_ids:
                turn_ctx.emitted_tool_input_ids.add(tool_call_id)
                evt = {"type": "tool-input-available", "toolCallId": tool_call_id, "toolName": tool_name, "input": tool_input}
                await queue.put(_event("tool-input-available", {"toolCallId": tool_call_id, "toolName": tool_name, "input": tool_input}))
                turn_ctx.collected_parts.append(evt)

            # Step 2: emit tool-approval-request (lifecycle frame — not collected).
            # SandboxPermissionRequest frames carry the sandbox_network
            # discriminator + networkRequest metadata so the frontend renders
            # the network-variant confirmation card; generic confirmations omit
            # both keys (backward compatible).
            approval_event: dict[str, Any] = {"toolCallId": tool_call_id, "toolName": tool_name, "input": tool_input}
            if policy.kind != "approval":
                approval_event["confirmationKind"] = policy.kind
            if policy.kind == "sandbox_network":
                approval_event["networkRequest"] = {
                    "host": policy.network_host,
                    "policyMode": policy.network_policy,
                    "matchedAllowedDomain": None,
                }
            await queue.put(_event("tool-approval-request", approval_event))

            # Step 3 & 4: block until user responds.
            try:
                result = await store.await_pending(tool_call_id, tool_name=tool_name)
                # Include answers so agent_runner can merge them into tool_input for
                # AskUserQuestion-style tools (§9.5 design contract).
                return {"approved": result.approved, "reason": result.reason, "answers": result.answers}
            except TimeoutError:
                logger.warning(
                    "Tool confirmation timed out: tool_call_id=%s tool_name=%s",
                    tool_call_id,
                    tool_name,
                )
                return {"approved": False, "reason": "timeout"}
            except asyncio.CancelledError:
                store.cancel_pending(tool_call_id)
                raise

        return on_tool_confirmation_request

    @staticmethod
    def _make_error_cb(queue: asyncio.Queue):
        async def on_error(exc: Exception) -> None:
            await queue.put(_event("error", {"errorText": _format_exception_for_sse(exc)}))

        return on_error

    @staticmethod
    def _make_plan_file_changed_cb(queue: asyncio.Queue, state: Optional[Any]):
        """Build the runner on_plan_file_changed callback (claude-plan §5.3).

        Fired by the runner PostToolUse hook (debounced per file per turn)
        after a built-in Write/Edit/MultiEdit lands in the thread workspace
        plans dir.  Reads the plan file and emits plan-updated; IO failures
        skip the emission and only log.
        """

        async def on_plan_file_changed(file_path: str) -> None:
            plan_state = _ensure_plan_state(state)
            await _emit_plan_updated(queue, plan_state, Path(file_path))

        return on_plan_file_changed

    @staticmethod
    def _make_tasks_changed_cb(queue: asyncio.Queue, state: Optional[Any]):
        """Build the runner on_tasks_changed callback (claude-todo §5.3).

        Fired by the runner PostToolUse hook (debounced per tasks dir per
        turn) after TaskCreate/TaskUpdate; the payload is the full TodoItem
        list already derived from the tasks dir.  Emits todo-updated with
        source "task_v2"; the frame is never collected into collected_parts.
        """

        async def on_tasks_changed(todos: list) -> None:
            if not isinstance(todos, list):
                logger.warning("on_tasks_changed: non-list payload; skipping emit.")
                return
            todo_state = _ensure_todo_state(state)
            todo_state.source = "task_v2"
            todo_state.todos = todos
            todo_state.updated_at = _utc_now_iso()
            await _emit_todo_updated(queue, todo_state)

        return on_tasks_changed



# ---------------------------------------------------------------------------
# Turn execution bundle
# ---------------------------------------------------------------------------


@dataclass
class _TurnExecution:
    request: ClaudeAgentRunRequest
    state: AgentRunState
    runner: ClaudeAgentRunner
    run_options: AgentRunOptions
    turn_context: _TurnContext
    # Internal server-derived Dream authority. It is assembled from actor +
    # canonical Thread and is never part of ClaudeAgentRunRequest or HTTP/SSE.
    dream_context: StoryWorkspaceDreamRunContext | None = None
    # Root-turn business projection ticket assembled from the same trusted
    # Dream context. It is internal and never enters the Chat/SSE payload.
    dream_artifact_turn_ticket: DreamArtifactTurnTicket | None = None
    # The DB row used to source claude_session_id for resume / persistence;
    # None on the first turn of a session.
    resume_existing_session: Optional[dict] = None


# ---------------------------------------------------------------------------
# SSE events → UIMessage parts conversion
# ---------------------------------------------------------------------------


def _sse_events_to_ui_parts(events: list) -> list:
    """Convert collected raw SSE events to UIMessage-compatible parts for persistence.

    Linear single-pass over the collected SSE event dicts.  Mirrors how the
    Vercel AI SDK assembles UIMessage['parts'] from UIMessageChunks in better-chatbot.

    Input event types (§4.5.2):
      text-start/delta/end    → {"type":"text", "text":"..."}
      reasoning-start/delta/end → {"type":"reasoning", "id":"...", "text":"..."}
      tool-input-available    → {"type":"tool-invocation", "state":"call", ...}
      tool-output-available   → patches matching invocation in-place

    Ignored: anything not listed above (tool-input-start, tool-approval-request, etc.)
    """
    parts: list[dict] = []
    current_text: Optional[dict] = None
    current_reasoning: Optional[dict] = None
    tool_by_id: dict[str, dict] = {}

    for event in events:
        etype = event.get("type")

        if etype == "text-start":
            current_text = {"type": "text", "text": ""}
            parts.append(current_text)

        elif etype == "text-delta":
            if current_text is not None:
                current_text["text"] += event.get("delta", "")

        elif etype == "text-end":
            current_text = None

        elif etype == "reasoning-start":
            current_reasoning = {"type": "reasoning", "id": event.get("id", ""), "text": ""}
            parts.append(current_reasoning)

        elif etype == "reasoning-delta":
            if current_reasoning is not None:
                current_reasoning["text"] += event.get("delta", "")

        elif etype == "reasoning-end":
            current_reasoning = None

        elif etype == "tool-input-available":
            tool_id = event.get("toolCallId")
            if tool_id:
                inv: dict = {
                    "type": "tool-invocation",
                    "toolCallId": tool_id,
                    "toolName": event.get("toolName"),
                    "state": "call",
                    "input": event.get("input", {}),
                    "dynamic": True,
                }
                parts.append(inv)
                tool_by_id[tool_id] = inv

        elif etype == "tool-output-available":
            tool_id = event.get("toolCallId")
            if tool_id and tool_id in tool_by_id:
                inv = tool_by_id[tool_id]
                inv["state"] = "output-error" if event.get("isError") else "output-available"
                inv["output"] = event.get("output")

    return parts


def _completed_turn_final_part_index(parts: list) -> int | None:
    """Return the unique protocol-safe final text suffix for a completed turn.

    Persistence emits only text, reasoning, and tool-invocation parts.  A final
    answer is trustworthy when the suffix after the last process part contains
    exactly one non-empty text part and no unknown/diagnostic part.  This keeps
    intermediate assistant text before later tools in the process region and
    deliberately refuses ambiguous or tool-ended turns.
    """

    last_process_index = -1
    for index, part in enumerate(parts):
        if not isinstance(part, dict):
            return None
        part_type = part.get("type")
        if part_type not in {"text", "reasoning", "tool-invocation"}:
            return None
        if part_type in {"reasoning", "tool-invocation"}:
            last_process_index = index

    suffix = list(enumerate(parts[last_process_index + 1 :], last_process_index + 1))
    if len(suffix) != 1:
        return None
    index, part = suffix[0]
    if part.get("type") != "text":
        return None
    text = part.get("text")
    return index if isinstance(text, str) and bool(text.strip()) else None


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------


def _event(event_type: str, data: dict[str, Any]) -> NormalizedAgentEvent:
    """Create one protocol-neutral event for the internal EventBus."""

    return NormalizedAgentEvent.create(event_type, data)


async def _put_terminal(queue: Any, event: NormalizedAgentEvent) -> None:
    """Use the EventBus atomic terminal seam, retaining plain-queue tests."""

    put_terminal = getattr(queue, "put_terminal", None)
    if callable(put_terminal):
        await put_terminal(event)
        return
    await queue.put(event)
    await queue.put(None)


def _sse(event_type: str, data: dict[str, Any]) -> str:
    """Legacy Chat-frame helper retained for external test/caller compatibility."""

    return ChatStreamAdapter.encode(_event(event_type, data))
