# [Input] Consume claude_agent/thread_pool.py, claude_agent/service.py,
#         libs/claude_agent_kit/runner.py, claude_agent/observer.py.
# [Output] Provide ClaudeAgentThreadFactory, build_session_id
#          to HTTP route handlers in server.py.
# [Pos] factory-entry node in backend/claude_agent
# [Sync] 2026-05-22: adapted from Pawkeyland application/claude_agent/thread_factory.py.
#                    session_id = user_id (no persona).
#                    Removed pet/persona/mem0/IdentityService/volcresource dependencies.

"""Claude Agent Thread Factory — 四阶段会话编排入口.

``build_session_id``
    Maps a ``ClaudeAgentRunRequest`` to a stable ``session_id`` string.
    Current strategy: ``user_id``.  Extend to ``f"{user_id}__{tag}"`` if
    per-topic sessions are needed in the future.

``ClaudeAgentThreadFactory``
    Singleton-per-process.  Creates and manages ``AgentRunState`` flyweights,
    serialises concurrent requests via per-session ``asyncio.Lock``, and drives
    the four lifecycle phases for each turn.

Public API::

    await factory.run_streaming(request)        → AsyncGenerator[str]
    factory.confirm_tool(session_id, ...)
    factory.close_thread(session_id)            → None
    factory.session_snapshot(session_id)        → dict | None
    factory.list_session_snapshots()            → list[dict]
    factory.sweep_stats()                       → dict
    factory.register_observer(obs)
    factory.unregister_observer(obs)
    await factory.aclose()
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncGenerator, Optional

from claude_agent.observer import LoggingObserver, SessionObserverRegistry
from libs.claude_agent_kit.server.agent_runner import ClaudeAgentRunner
from claude_agent.service import ClaudeAgentRunRequest, ClaudeAgentService
from claude_agent.thread_pool import (
    AgentRunLifecycle,
    AgentRunStatePool,
    AgentRunStateSweeper,
    _validate_session_id,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Session ID construction
# ---------------------------------------------------------------------------


def build_session_id(request: ClaudeAgentRunRequest) -> str:
    """Return a stable session_id for *request*.

    Current convention: the authenticated ``user_id``.  Session IDs must not
    contain ``/``, ``\\``, or ``..`` (enforced by :func:`_validate_session_id`).
    """
    sid = request.user_id
    _validate_session_id(sid)
    return sid


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class ClaudeAgentThreadFactory:
    """Entry point for all Claude Agent streaming requests.

    Lifecycle (per turn)::

        Phase 1 — context_builder: assemble system_prompt (first turn only)
        Phase 2 — runner.py: create ClaudeAgentRunner (first turn only)
        Phase 3 — service.py: execute streaming turn, emit SSE events
        Phase 4 — observer: fire session_ended on DESTROYED state

    Create one shared instance at server startup and pass it to the
    ``@app.on_event("startup")`` handler::

        claude_agent_thread_factory = ClaudeAgentThreadFactory()
        claude_agent_thread_factory.start()

    Shutdown::

        await claude_agent_thread_factory.aclose()
    """

    def __init__(self) -> None:
        self._pool = AgentRunStatePool()
        self._observers = SessionObserverRegistry()
        self._service = ClaudeAgentService()
        self._sweeper = AgentRunStateSweeper(
            self._pool,
            on_evicted=self._on_sessions_evicted,
        )
        self._observers.register(LoggingObserver())

    def start(self) -> None:
        """Start the background TTL sweeper task."""
        self._sweeper.start()
        logger.info("ClaudeAgentThreadFactory started")

    async def aclose(self) -> None:
        """Shut down the factory: stop sweeper and destroy all sessions."""
        await self._sweeper.stop()
        destroyed = self._pool.destroy_all()
        if destroyed:
            for sid in destroyed:
                await self._fire_session_ended(
                    sid, reason="factory_aclose", turn_count=None
                )
        logger.info("ClaudeAgentThreadFactory closed; destroyed %d session(s)", len(destroyed))

    # ------------------------------------------------------------------
    # Primary API: streaming turn
    # ------------------------------------------------------------------

    async def run_streaming(
        self,
        request: ClaudeAgentRunRequest,
    ) -> AsyncGenerator[str, None]:
        """Execute a streaming agent turn and yield SSE frames.

        One ``asyncio.Lock`` per session_id serialises concurrent callers.
        Yields are SSE-formatted strings (``"data: {...}\\n\\n"``).
        """
        session_id = build_session_id(request)
        lock = self._pool.get_lock(session_id)

        async with lock:
            queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
            state = self._pool.get_or_create(session_id)
            state.mark_running()

            # Phase 1: context assembly
            await self._observers.emit_before_context_assembly(
                session_id, {"resume": request.resume}
            )

            # Phase 2: runner creation (cached)
            if state.runner is None:
                await self._observers.emit_before_runner_created(session_id)
                runner = ClaudeAgentRunner()
                state.with_runner(runner)
                await self._observers.emit_after_runner_created(session_id, runner)
            else:
                runner = state.runner

            execution = await self._service.assemble_context(
                request, state=state, queue=queue, runner=runner
            )

            await self._observers.emit_after_context_assembly(
                session_id, {"system_prompt_len": len(state.system_prompt)}
            )

            # Phase 3: execute session in background task
            await self._observers.emit_before_session_started(
                session_id, {"resume": request.resume}
            )
            bg_task = asyncio.create_task(
                self._service.execute_session(execution),
                name=f"claude-agent-session-{session_id}",
            )

            try:
                # Yield SSE frames from the queue
                async for frame in self._drain_queue(queue, bg_task):
                    yield frame
            finally:
                # Cancel any pending tool confirmations on disconnect
                turn_ctx = state.turn_context
                if turn_ctx is not None:
                    for tcid in list(turn_ctx.confirmation_store.pending_ids()):
                        turn_ctx.confirmation_store.cancel_pending(tcid)
                    state.turn_context = None

                if not bg_task.done():
                    bg_task.cancel()
                    try:
                        await bg_task
                    except (asyncio.CancelledError, Exception):
                        pass

                state.mark_idle()
                await self._observers.emit_after_session_started(session_id)

    @staticmethod
    async def _drain_queue(
        queue: asyncio.Queue,
        bg_task: "asyncio.Task[None]",
    ) -> AsyncGenerator[str, None]:
        """Drain SSE frames from queue until sentinel (None) or bg_task failure."""
        while True:
            try:
                frame = await asyncio.wait_for(queue.get(), timeout=15.0)
                if frame is None:
                    break
                yield frame
            except asyncio.TimeoutError:
                # Emit SSE keepalive comment to prevent proxy timeout
                yield ": keepalive\n\n"
            except asyncio.CancelledError:
                break

    # ------------------------------------------------------------------
    # Tool confirmation
    # ------------------------------------------------------------------

    def confirm_tool(
        self,
        session_id: str,
        tool_call_id: str,
        approved: bool,
        reason: Optional[str] = None,
        answers: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Resolve a pending tool confirmation for an active session."""
        state = self._pool.get(session_id)
        if state is None or state.lifecycle != AgentRunLifecycle.RUNNING:
            logger.warning(
                "confirm_tool: session %s not in RUNNING state", session_id
            )
            return False
        return self._service.confirm_tool(state, tool_call_id, approved, reason, answers)

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def close_thread(self, session_id: str) -> None:
        """Explicitly destroy a session and trigger Phase 4 observer."""
        state = self._pool.get(session_id)
        turn_count = state.turn_count if state else None
        self._pool.destroy(session_id)
        asyncio.create_task(
            self._fire_session_ended(session_id, reason="explicit_close", turn_count=turn_count),
            name=f"claude-agent-phase4-{session_id}",
        )

    def session_snapshot(self, session_id: str) -> Optional[dict[str, Any]]:
        return self._pool.snapshot_session(session_id)

    def list_session_snapshots(self) -> list[dict[str, Any]]:
        return self._pool.snapshot_all()

    def sweep_stats(self) -> dict[str, Any]:
        return self._sweeper.sweep_stats()

    # ------------------------------------------------------------------
    # Observer management
    # ------------------------------------------------------------------

    def register_observer(self, observer: Any) -> None:
        self._observers.register(observer)

    def unregister_observer(self, observer: Any) -> None:
        self._observers.unregister(observer)

    # ------------------------------------------------------------------
    # Internal: Phase 4 firing
    # ------------------------------------------------------------------

    async def _fire_session_ended(
        self,
        session_id: str,
        *,
        reason: str,
        turn_count: Optional[int],
    ) -> None:
        await self._observers.emit_before_session_ended(session_id)
        result: dict[str, Any] = {
            "session_id": session_id,
            "reason": reason,
            "destroyed": True,
        }
        if turn_count is not None:
            result["turn_count"] = turn_count
        await self._observers.emit_after_session_ended(session_id, result)

    async def _on_sessions_evicted(
        self, session_ids: list[str], reason: str
    ) -> None:
        for sid in session_ids:
            await self._fire_session_ended(sid, reason=reason, turn_count=None)
