# [Input] Consume libs/claude_agent_kit/types.py, libs/claude_agent_kit/runner.py,
#         claude_agent/context_builder.py, claude_agent/tool_confirmation_store.py.
#         Reads database module for session persistence.
# [Output] Provide ClaudeAgentRunRequest, ClaudeAgentService to thread_factory.py.
# [Pos] core-business node in backend/claude_agent
# [Sync] 2026-05-22: adapted from Pawkeyland application/claude_agent/service.py.
#                    Removed: pet/persona/mem0/sticker_filter/IdentityService.
#                    Session context provided by ClaudeAgentContextBuilder.

"""Claude Agent Service — core business logic for Ink & Memory.

Responsibilities:
- ``assemble_context``: Phase 1 — build system prompt + run options for the turn.
- ``execute_session``: Phase 3 — stream the agent turn, emit SSE events, persist (optional).

SSE event schema::

    data: {"type": "text-delta",     "text": "..."}
    data: {"type": "text-done",      "text": "..."}
    data: {"type": "tool-event",     "tool_name": "...", "tool_call_id": "...", "state": "..."}
    data: {"type": "tool-approval-request", "toolCallId": "...", "toolName": "...", "input": {...}}
    data: {"type": "message-metadata", "sessionId": "...", "turnIndex": 0}
    data: {"type": "message-final",  "text": "...", "usage": {...}}
    data: {"type": "finish",         "reason": "success"}
    data: {"type": "error",          "message": "..."}
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Optional

from claude_agent.context_builder import ClaudeAgentContextBuilder
from libs.claude_agent_kit.server.agent_runner import ClaudeAgentRunner
from claude_agent.thread_pool import AgentRunState
from claude_agent.tool_confirmation_store import ToolConfirmationResult, ToolConfirmationStore
from libs.claude_agent_kit.types import AgentRunOptions, AgentStreamingCallbacks, ToolEventPayload

logger = logging.getLogger(__name__)

# Keepalive interval for SSE comments (seconds).
_SSE_KEEPALIVE_S: float = float(os.getenv("INK_AGENT_SSE_KEEPALIVE_S", "15") or "15")


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------


@dataclass
class ClaudeAgentRunRequest:
    """Validated request for a single Claude Agent turn.

    All string IDs are validated by the factory before this dataclass is built.
    """

    user_id: str
    thread_id: str
    message: str
    resume: bool = False
    tool_choice: str = "auto"
    model: Optional[str] = None
    max_turns: int = int(os.getenv("INK_AGENT_MAX_TURNS", "100") or "100")
    cwd: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Turn context (extrinsic state bundle)
# ---------------------------------------------------------------------------


@dataclass
class _TurnContext:
    """Mutable state bundle for a single agent turn."""

    queue: asyncio.Queue
    confirmation_store: ToolConfirmationStore
    pending_tool_call_ids: set = field(default_factory=set)
    full_text_accumulator: list[str] = field(default_factory=list)
    turn_start_ts: float = field(default_factory=time.monotonic)


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

        user_message = self._context_builder.build_user_message(request.message)

        run_options = AgentRunOptions(
            thread_id=state.session_id,
            user_message=user_message,
            resume=request.resume,
            model=request.model,
            cwd=request.cwd or state.cwd or None,
            max_turns=request.max_turns,
            tool_choice=request.tool_choice,  # type: ignore[arg-type]
            system_prompt=state.system_prompt,
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
            on_tool_event=self._make_tool_event_cb(queue),
            on_tool_confirmation_request=self._make_tool_confirm_cb(queue, store),
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
            await queue.put(_sse("finish", {"reason": "success"}))
            # Persist user and assistant messages to the database
            await self._persist_turn(execution, full_text)
        else:
            error_msg = str(result.error) if result.error else "Unknown error"
            await queue.put(_sse("error", {"message": error_msg}))
            await queue.put(_sse("finish", {"reason": "error"}))

        await queue.put(None)  # Sentinel: end of stream

    async def _persist_turn(
        self, execution: "_TurnExecution", assistant_text: str
    ) -> None:
        """Save user and assistant messages to the database after a successful turn."""
        import asyncio
        import database

        thread_id = execution.request.thread_id
        user_text = execution.request.message

        loop = asyncio.get_running_loop()

        def _save() -> None:
            database.save_chat_message(thread_id, "user", user_text)
            database.save_chat_message(thread_id, "assistant", assistant_text)
            # Auto-fill thread title from first user message if still NULL
            thread = database.get_chat_thread(thread_id, int(execution.request.user_id))
            if thread and not thread.get("title"):
                title = user_text.strip()[:50]
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
    # SSE callback factories
    # ------------------------------------------------------------------

    @staticmethod
    def _make_text_delta_cb(
        queue: asyncio.Queue, turn_ctx: _TurnContext
    ):
        async def on_text_delta(delta: str) -> None:
            turn_ctx.full_text_accumulator.append(delta)
            await queue.put(_sse("text-delta", {"text": delta}))

        return on_text_delta

    @staticmethod
    def _make_text_done_cb(queue: asyncio.Queue, turn_ctx: _TurnContext):
        async def on_text_done(full_text: str) -> None:
            await queue.put(_sse("text-done", {"text": full_text}))

        return on_text_done

    @staticmethod
    def _make_tool_event_cb(queue: asyncio.Queue):
        async def on_tool_event(payload: ToolEventPayload) -> None:
            await queue.put(
                _sse("tool-event", {
                    "tool_name": payload.tool_name,
                    "tool_call_id": payload.tool_call_id,
                    "state": payload.state,
                    "input": payload.input,
                    "output": payload.output,
                    "is_error": payload.is_error,
                })
            )

        return on_tool_event

    @staticmethod
    def _make_tool_confirm_cb(queue: asyncio.Queue, store: ToolConfirmationStore):
        async def on_tool_confirmation_request(payload: dict[str, Any]) -> Optional[dict[str, Any]]:
            tool_call_id = payload.get("toolCallId", "")
            tool_name = payload.get("toolName", "")
            tool_input = payload.get("input", {})

            store.begin_pending(tool_call_id)
            await queue.put(
                _sse("tool-approval-request", {
                    "toolCallId": tool_call_id,
                    "toolName": tool_name,
                    "input": tool_input,
                })
            )
            try:
                result = await store.await_pending(tool_call_id, tool_name=tool_name)
                return {"approved": result.approved, "reason": result.reason}
            except TimeoutError:
                logger.warning(
                    "Tool confirmation timed out for tool_call_id=%s", tool_call_id
                )
                return {"approved": False, "reason": "timeout"}

        return on_tool_confirmation_request

    @staticmethod
    def _make_error_cb(queue: asyncio.Queue):
        async def on_error(exc: Exception) -> None:
            await queue.put(_sse("error", {"message": str(exc)}))

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
# SSE helpers
# ---------------------------------------------------------------------------


def _sse(event_type: str, data: dict[str, Any]) -> str:
    """Format a single SSE data frame."""
    return f"data: {json.dumps({'type': event_type, **data})}\n\n"
