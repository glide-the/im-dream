# [Input] Consume libs/claude_agent_kit/types.py, libs/claude_agent_kit/runner.py,
#         claude_agent/context_builder.py, claude_agent/tool_confirmation_store.py.
#         Reads database module for session persistence.
# [Output] Provide ClaudeAgentRunRequest, ClaudeAgentService to thread_factory.py.
# [Pos] core-business node in backend/claude_agent
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
# [Sync] 2026-05-25: refactor parts collection — use AgentStreamingCallbacks as single source:
#                    text deltas written directly to collected_parts[-1]["text"] in on_text_delta;
#                    text-end emitted once from on_text_done(full_text); no state flags needed.

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
    data: {"type": "tool-input-available", "toolCallId": "...", "toolName": "...", "input": {...}}
    data: {"type": "tool-output-available","toolCallId": "...", "output": ..., "isError": false}
    data: {"type": "tool-approval-request","toolCallId": "...", "toolName": "...", "input": {...}}
    data: {"type": "message-final",  "text": "...", "usage": {...}, "sessionId": "..."}
    data: {"type": "finish",         "finishReason": "stop"|"error"}
    data: {"type": "error",          "errorText": "..."}
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Optional
from uuid import uuid4

from claude_agent.context_builder import ClaudeAgentContextBuilder
from libs.claude_agent_kit.server.agent_runner import ClaudeAgentRunner
from claude_agent.thread_pool import AgentRunState
from libs.claude_agent_kit.server.workspace import get_or_create_workspace
from claude_agent.tool_confirmation_store import ToolConfirmationResult, ToolConfirmationStore
from libs.claude_agent_kit.messages.build_user_message_content import AttachmentPayload
from libs.claude_agent_kit.messages.message_parts import extract_text_from_parts
from libs.claude_agent_kit.types import AgentRunOptions, AgentStreamingCallbacks, ToolEventPayload

logger = logging.getLogger(__name__)

# Keepalive interval for SSE comments (seconds).
_SSE_KEEPALIVE_S: float = float(os.getenv("INK_AGENT_SSE_KEEPALIVE_S", "15") or "15")

# Maximum characters to use when auto-titling a thread from the first user message.
MAX_THREAD_TITLE_LENGTH: int = 50


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


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------


@dataclass
class ClaudeAgentRunRequest:
    """Validated request for a single Claude Agent turn.

    All string IDs are validated by the factory before this dataclass is built.
    ``message_parts`` carries the AI-SDK UIMessage parts list (e.g.
    ``[{"type": "text", "text": "..."}]``); plain text is derived from it as
    needed — the raw ``message_text`` string is never stored here.
    """

    user_id: str
    thread_id: str
    resume: bool = False
    tool_choice: str = "auto"
    model: Optional[str] = None
    max_turns: int = int(os.getenv("INK_AGENT_MAX_TURNS", "100") or "100")
    cwd: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)
    # AI-SDK message fields (for context assembly and DB persistence)
    message_id: Optional[str] = None
    message_parts: Optional[list] = None
    # File attachments to be passed as content blocks to Claude.
    attachments: Optional[list[AttachmentPayload]] = None


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

    queue: asyncio.Queue
    confirmation_store: ToolConfirmationStore
    pending_tool_call_ids: set = field(default_factory=set)
    turn_start_ts: float = field(default_factory=time.monotonic)
    # Dedup sets for SSE emission.
    registered_tool_call_ids: set = field(default_factory=set)
    emitted_tool_input_ids: set = field(default_factory=set)
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
    ) -> None:
        self._context_builder = context_builder or ClaudeAgentContextBuilder()

    # ------------------------------------------------------------------
    # Phase 1: Context Assembly
    # ------------------------------------------------------------------

    async def assemble_context(
        self,
        request: ClaudeAgentRunRequest,
        *,
        state: AgentRunState,
        queue: asyncio.Queue,
        runner: ClaudeAgentRunner,
    ) -> "_TurnExecution":
        """Build context for the upcoming turn.

        On the first turn of a session: loads DB context and constructs the
        system prompt (expensive).  On subsequent turns within the keepalive
        window: reuses the cached ``state.system_prompt``.

        Returns a ``_TurnExecution`` ready to pass to ``execute_session``.
        """
        if not state.is_context_initialized:
            logger.debug(
                "Phase 1: building system_prompt for session_id=%s", state.session_id
            )
            system_prompt = await self._context_builder.build_system_prompt(
                request.user_id
            )
            state.with_system_prompt(system_prompt)
            state.is_context_initialized = True
        else:
            logger.debug(
                "Phase 1: reusing cached system_prompt for session_id=%s", state.session_id
            )

        cwd = request.cwd or state.cwd
        if not cwd:
            workspace_path = get_or_create_workspace(state.session_id)
            cwd = str(workspace_path)
            state.with_cwd(cwd)

        user_message_content = self._context_builder.build_user_message(
            request.message_parts,
            attachments=request.attachments,
            model=request.model,
            max_turns=request.max_turns,
            thread_id=state.session_id,
            resume=request.resume,
            cwd=cwd,
        )

        # Load user-configured env vars (skills / MCP environment) from system config.
        user_env_vars: dict[str, str] = {}
        try:
            import database as _db
            sys_cfg = _db.get_system_config(int(request.user_id))
            raw_env = sys_cfg.get("env_vars") or {}
            if isinstance(raw_env, dict):
                user_env_vars = {str(k).strip(): str(v) for k, v in raw_env.items() if str(k).strip() and v is not None}
        except Exception:
            logger.warning("Failed to load user env_vars from system_config; skipping.")

        run_options = AgentRunOptions(
            thread_id=state.session_id,
            user_message=user_message_content,
            resume=request.resume,
            model=request.model,
            cwd=cwd or None,
            max_turns=request.max_turns,
            tool_choice=request.tool_choice,  # type: ignore[arg-type]
            system_prompt=state.system_prompt,
            mcp_env=user_env_vars,
            user_sdk_env=user_env_vars,
        )

        confirmation_store = ToolConfirmationStore()
        turn_ctx = _TurnContext(
            queue=queue,
            confirmation_store=confirmation_store,
        )
        state.turn_context = turn_ctx

        return _TurnExecution(
            request=request,
            state=state,
            runner=runner,
            run_options=run_options,
            turn_context=turn_ctx,
        )

    # ------------------------------------------------------------------
    # Phase 3: Session Execution
    # ------------------------------------------------------------------

    async def execute_session(self, execution: "_TurnExecution") -> None:
        """Stream the agent turn and emit SSE events via the queue."""
        queue = execution.turn_context.queue
        store = execution.turn_context.confirmation_store

        # Emit session metadata header
        await queue.put(
            _sse("message-metadata", {"sessionId": execution.state.session_id, "turnIndex": execution.state.turn_count})
        )

        callbacks = AgentStreamingCallbacks(
            on_text_delta=self._make_text_delta_cb(queue, execution.turn_context),
            on_text_done=self._make_text_done_cb(queue, execution.turn_context),
            on_tool_event=self._make_tool_event_cb(queue, execution.turn_context),
            on_tool_confirmation_request=self._make_tool_confirm_cb(queue, store, execution.turn_context),
            on_error=self._make_error_cb(queue),
        )

        result = await execution.runner.run_streaming(execution.run_options, callbacks)

        if result.success:
            full_text = result.full_text
            await queue.put(
                _sse("message-final", {
                    "text": full_text,
                    "usage": result.usage,
                    "sessionId": result.session_id,
                })
            )
            await queue.put(_sse("finish", {"finishReason": "stop"}))
            # Persist user and assistant messages to the database
            await self._persist_turn(execution, result)
        else:
            error_msg = str(result.error) if result.error else "Unknown error"
            await queue.put(_sse("error", {"errorText": error_msg}))
            await queue.put(_sse("finish", {"finishReason": "error"}))

        await queue.put(None)  # Sentinel: end of stream

    async def _persist_turn(
        self, execution: "_TurnExecution", result: Any
    ) -> None:
        """Save user and assistant messages to the database after a successful turn.

        Aligned with better-chatbot onFinish / chatRepository.upsertMessage pattern:
        - user message: parts list (from frontend AI-SDK message.parts, or text fallback)
        - assistant message: parts list (reasoning + tool-invocations + text) + metadata dict
        Serialisation (JSON) is handled inside database.save_chat_message.
        """
        import asyncio
        import database

        thread_id = execution.request.thread_id
        user_message_id = execution.request.message_id  # original AI-SDK ID or None
        user_parts = execution.request.message_parts     # original parts list or None
        assistant_text: str = result.full_text if result else ""
        turn_ctx = execution.turn_context

        loop = asyncio.get_running_loop()

        def _save() -> None:
            # --- User message ---
            # Mirror better-chatbot: store message.parts from the frontend AI SDK.
            # Fall back to an empty parts list when message_parts is not provided.
            resolved_user_parts: list = list(user_parts) if user_parts else [{"type": "text", "text": ""}]
            database.save_chat_message(
                thread_id, "user",
                parts=resolved_user_parts,
                message_id=user_message_id,
            )

            # --- Assistant message ---
            # Convert the collected raw SSE events to UIMessage-compatible parts.
            # This is the server-side equivalent of the Vercel AI SDK assembling
            # responseMessage.parts from UIMessageChunks in better-chatbot.
            asst_parts: list = _sse_events_to_ui_parts(turn_ctx.collected_parts)
            if not asst_parts:
                # Fallback: no collectible SSE events (e.g. test stubs / empty run).
                asst_parts = [{"type": "text", "text": assistant_text}] if assistant_text else []

            # Build metadata (model + usage + toolCount) — same as better-chatbot metadata
            asst_metadata: dict = {}
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
                    "provider": "anthropic",
                    "model": execution.request.model,
                }
            tool_count = sum(1 for p in asst_parts if p.get("type") == "tool-invocation")
            if tool_count:
                asst_metadata["toolCount"] = tool_count

            database.save_chat_message(
                thread_id, "assistant",
                parts=asst_parts,
                metadata=asst_metadata or None,
            )
            # Auto-fill thread title from first user message if still NULL
            thread = database.get_chat_thread(thread_id, int(execution.request.user_id))
            if thread and not thread.get("title"):
                title = _extract_text_from_parts(user_parts).strip()[:MAX_THREAD_TITLE_LENGTH]
                database.update_chat_thread_title(thread_id, title)

        try:
            await loop.run_in_executor(None, _save)
        except Exception:
            logger.exception(
                "Failed to persist messages for thread_id=%s", thread_id
            )

    # ------------------------------------------------------------------
    # Tool confirmation (called from HTTP endpoint via factory)
    # ------------------------------------------------------------------

    def confirm_tool(
        self,
        state: AgentRunState,
        tool_call_id: str,
        approved: bool,
        reason: Optional[str] = None,
        answers: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Resolve a pending tool confirmation."""
        turn_ctx = state.turn_context
        if turn_ctx is None:
            logger.warning(
                "confirm_tool: no active turn_context for session_id=%s", state.session_id
            )
            return False
        result = ToolConfirmationResult(approved=approved, reason=reason, answers=answers)
        return turn_ctx.confirmation_store.resolve(tool_call_id, result)

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
                await queue.put(_sse("text-start", {"id": _TEXT_PART_ID}))
                turn_ctx.collected_parts.append({"type": "text-start", "id": _TEXT_PART_ID})
            await queue.put(_sse("text-delta", {"id": _TEXT_PART_ID, "delta": delta}))
            turn_ctx.collected_parts.append({"type": "text-delta", "id": _TEXT_PART_ID, "delta": delta})

        return on_text_delta

    @staticmethod
    def _make_text_done_cb(queue: asyncio.Queue, turn_ctx: _TurnContext):
        async def on_text_done(full_text: str) -> None:
            if full_text:
                await queue.put(_sse("text-end", {"id": _TEXT_PART_ID}))
                turn_ctx.collected_parts.append({"type": "text-end", "id": _TEXT_PART_ID})

        return on_text_done

    @staticmethod
    def _make_tool_event_cb(queue: asyncio.Queue, turn_ctx: _TurnContext):
        """Emit SSE tool / reasoning events and collect them into collected_parts.

        Each SSE event is both emitted to ``queue`` (frontend) and appended to
        ``collected_parts`` (persistence).  The conversion to UIMessage parts
        happens later in ``_sse_events_to_ui_parts()``.

        Collected → SSE event type stored in collected_parts:
          ``thinking_delta``               → reasoning-start (first), reasoning-delta
          ``content_block_stop``           → reasoning-end
          ``thinking`` (atomic)            → reasoning-start, reasoning-delta, reasoning-end
          ``tool_use`` / ``tool_use_start``→ tool-input-available (when input present)
          ``tool_input_available``         → tool-input-available
          ``tool_result``                  → tool-output-available

        Not collected: tool-input-start (no data payload), tool-approval-request.
        Ignored entirely: result, message_*, tool_progress, tool_use_summary, etc.
        """
        async def on_tool_event(payload: ToolEventPayload) -> None:
            tool_call_id = payload.tool_call_id
            tool_name = payload.tool_name
            event_type = payload.type

            # --- thinking_delta: incremental reasoning stream ---
            if event_type == "thinking_delta" and payload.output:
                if not turn_ctx.current_reasoning_id:
                    turn_ctx.current_reasoning_id = str(uuid4())
                    await queue.put(_sse("reasoning-start", {"id": turn_ctx.current_reasoning_id}))
                    turn_ctx.collected_parts.append({"type": "reasoning-start", "id": turn_ctx.current_reasoning_id})
                turn_ctx.has_thinking_delta = True
                delta_text = str(payload.output)
                turn_ctx.current_reasoning_text.append(delta_text)
                await queue.put(_sse("reasoning-delta", {"id": turn_ctx.current_reasoning_id, "delta": delta_text}))
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
                    await queue.put(_sse("reasoning-end", {"id": turn_ctx.current_reasoning_id}))
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
                    await queue.put(_sse("reasoning-end", {"id": turn_ctx.current_reasoning_id}))
                    turn_ctx.collected_parts.append({"type": "reasoning-end", "id": turn_ctx.current_reasoning_id})
                    turn_ctx.current_reasoning_id = None
                    turn_ctx.has_thinking_delta = False
                    turn_ctx.current_reasoning_text.clear()
                    return
                reasoning_id = str(uuid4())
                await queue.put(_sse("reasoning-start", {"id": reasoning_id}))
                turn_ctx.collected_parts.append({"type": "reasoning-start", "id": reasoning_id})
                await queue.put(_sse("reasoning-delta", {"id": reasoning_id, "delta": thinking_output}))
                turn_ctx.collected_parts.append({"type": "reasoning-delta", "id": reasoning_id, "delta": thinking_output})
                await queue.put(_sse("reasoning-end", {"id": reasoning_id}))
                turn_ctx.collected_parts.append({"type": "reasoning-end", "id": reasoning_id})
                return

            # --- tool_use / tool_use_start: new tool call beginning ---
            if event_type in ("tool_use", "tool_use_start") and tool_call_id and tool_name:
                if tool_call_id not in turn_ctx.registered_tool_call_ids:
                    turn_ctx.registered_tool_call_ids.add(tool_call_id)
                    await queue.put(_sse("tool-input-start", {"toolCallId": tool_call_id, "toolName": tool_name}))
                if payload.input is not None and tool_call_id not in turn_ctx.emitted_tool_input_ids:
                    turn_ctx.emitted_tool_input_ids.add(tool_call_id)
                    evt = {"type": "tool-input-available", "toolCallId": tool_call_id, "toolName": tool_name, "input": payload.input}
                    await queue.put(_sse("tool-input-available", {"toolCallId": tool_call_id, "toolName": tool_name, "input": payload.input}))
                    turn_ctx.collected_parts.append(evt)
                return

            # --- tool_input_available: complete streamed JSON input ready ---
            if event_type == "tool_input_available" and tool_call_id and tool_name:
                if tool_call_id not in turn_ctx.registered_tool_call_ids:
                    turn_ctx.registered_tool_call_ids.add(tool_call_id)
                    await queue.put(_sse("tool-input-start", {"toolCallId": tool_call_id, "toolName": tool_name}))
                if tool_call_id not in turn_ctx.emitted_tool_input_ids:
                    turn_ctx.emitted_tool_input_ids.add(tool_call_id)
                    evt = {"type": "tool-input-available", "toolCallId": tool_call_id, "toolName": tool_name, "input": payload.input or {}}
                    await queue.put(_sse("tool-input-available", {"toolCallId": tool_call_id, "toolName": tool_name, "input": payload.input or {}}))
                    turn_ctx.collected_parts.append(evt)
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
                    await queue.put(_sse("tool-input-start", {"toolCallId": tool_call_id, "toolName": fallback_name}))
                    turn_ctx.emitted_tool_input_ids.add(tool_call_id)
                    fallback_evt = {"type": "tool-input-available", "toolCallId": tool_call_id, "toolName": fallback_name, "input": {}}
                    await queue.put(_sse("tool-input-available", {"toolCallId": tool_call_id, "toolName": fallback_name, "input": {}}))
                    turn_ctx.collected_parts.append(fallback_evt)
                is_error = bool(payload.is_error)
                evt = {"type": "tool-output-available", "toolCallId": tool_call_id, "output": payload.output, "isError": is_error}
                await queue.put(_sse("tool-output-available", {"toolCallId": tool_call_id, "output": payload.output, "isError": is_error}))
                turn_ctx.collected_parts.append(evt)
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

            # Step 0: register Future before any SSE that can trigger an immediate
            # POST /tool-confirm (fast clients must not resolve ahead of registration).
            # Guard: if the hook fires twice for the same tool call (SDK quirk), skip
            # re-registration and join the existing waiter to avoid RuntimeError +
            # the immediate-deny path in agent_runner._pre_tool_use_hook.
            if store.has_pending(tool_call_id):
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

            store.begin_pending(tool_call_id)

            # Step 1: emit tool-input-start + tool-input-available with dedup so that
            # events already sent by _make_tool_event_cb are not repeated.
            if tool_call_id not in turn_ctx.registered_tool_call_ids:
                turn_ctx.registered_tool_call_ids.add(tool_call_id)
                await queue.put(_sse("tool-input-start", {"toolCallId": tool_call_id, "toolName": tool_name}))
            if tool_call_id not in turn_ctx.emitted_tool_input_ids:
                turn_ctx.emitted_tool_input_ids.add(tool_call_id)
                evt = {"type": "tool-input-available", "toolCallId": tool_call_id, "toolName": tool_name, "input": tool_input}
                await queue.put(_sse("tool-input-available", {"toolCallId": tool_call_id, "toolName": tool_name, "input": tool_input}))
                turn_ctx.collected_parts.append(evt)

            # Step 2: emit tool-approval-request (lifecycle frame — not collected).
            await queue.put(_sse("tool-approval-request", {"toolCallId": tool_call_id, "toolName": tool_name, "input": tool_input}))

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
            await queue.put(_sse("error", {"errorText": str(exc)}))

        return on_error



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


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------


def _sse(event_type: str, data: dict[str, Any]) -> str:
    """Format a single SSE data frame."""
    return f"data: {json.dumps({'type': event_type, **data})}\n\n"
