# [Input] Consume claude_agent/thread_pool.py, claude_agent/service.py,
#         claude_agent/event_bus.py, libs/claude_agent_kit/runner.py, claude_agent/observer.py.
# [Output] Provide ClaudeAgentThreadFactory, build_session_id
#          to HTTP route handlers in server.py.
# [Pos] factory-entry node in backend/claude_agent
# [Sync] 2026-05-22: adapted from Pawkeyland application/claude_agent/thread_factory.py.
#                    session_id = user_id (no persona).
#                    Removed pet/persona/mem0/IdentityService/volcresource dependencies.
# [Sync] 2026-06-09: EventBus reconnect — SSE disconnect no longer cancels bg_task;
#                    subscribe_stream / run_streaming(reconnect) replay live frames;
#                    per-session lock held until bg_task completes.
# [Sync] 2026-06-25: add stop_thread() for frontend-initiated current-turn
#                    cancellation without destroying the chat thread.
# [Sync] 2026-08-03: assemble_context failure (e.g. WorkspacePackError from
#                    workspace plugin pack) now emits an SSE error frame +
#                    sentinel via the EventBus and resets lifecycle to IDLE,
#                    instead of a bare SSE disconnect + stuck RUNNING session.

"""Claude Agent Thread Factory — 四阶段会话编排入口."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, AsyncGenerator, Optional
from uuid import uuid4

from claude_agent.event_bus import IEventBus, create_event_bus
from claude_agent.observer import LoggingObserver, SessionObserverRegistry
from libs.claude_agent_kit.server.agent_runner import ClaudeAgentRunner
from claude_agent.service import (
    ClaudeAgentRunRequest,
    ClaudeAgentService,
    _format_exception_for_sse,
    _sse,
)
from claude_agent.thread_pool import (
    AgentRunLifecycle,
    AgentRunState,
    AgentRunStatePool,
    AgentRunStateSweeper,
    _validate_session_id,
)

logger = logging.getLogger(__name__)

_DREAM_PUBLIC_TOOL_CONFIRMATIONS_ATTR = (
    "_story_workspace_dream_public_tool_confirmations"
)
_DREAM_PUBLIC_TOOL_CONFIRMATION_SUBSCRIBERS_ATTR = (
    "_story_workspace_dream_public_tool_confirmation_subscribers"
)


def _stop_wait_seconds() -> float:
    """Return the bounded wait for frontend stop requests."""

    try:
        raw = os.getenv("INK_AGENT_STOP_WAIT_S", "3") or "3"
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return 3.0


_STOP_WAIT_SECONDS: float = _stop_wait_seconds()


def build_session_id(request: ClaudeAgentRunRequest) -> str:
    """Return a stable session_id for *request*."""
    sid = request.thread_id
    _validate_session_id(sid)
    return sid


class ClaudeAgentThreadFactory:
    """Entry point for all Claude Agent streaming requests."""

    def __init__(self) -> None:
        self._pool = AgentRunStatePool()
        self._observers = SessionObserverRegistry()
        self._service = ClaudeAgentService()
        self._sweeper = AgentRunStateSweeper(
            self._pool,
            on_evicted=self._on_sessions_evicted,
        )
        self._observers.register(LoggingObserver())
        # The factory owns cleanup because these projections are scoped to an
        # in-memory turn, not to any browser's SSE subscription.
        self._story_workspace_dream_public_tool_confirmations: dict[
            tuple[str, str, str, str, str], dict[str, Any]
        ] = {}
        self._story_workspace_dream_public_tool_confirmation_subscribers: dict[
            tuple[str, str, str, str], int
        ] = {}

    def start(self) -> None:
        self._sweeper.start()
        logger.info("ClaudeAgentThreadFactory started")

    async def aclose(self) -> None:
        await self._sweeper.stop()
        destroyed = self._pool.destroy_all()
        if destroyed:
            for sid in destroyed:
                await self._fire_session_ended(
                    sid, reason="factory_aclose", turn_count=None
                )
        logger.info("ClaudeAgentThreadFactory closed; destroyed %d session(s)", len(destroyed))

    # ------------------------------------------------------------------
    # Primary API: streaming turn / reconnect
    # ------------------------------------------------------------------

    async def run_streaming(
        self,
        request: ClaudeAgentRunRequest,
    ) -> AsyncGenerator[str, None]:
        """Execute a streaming agent turn or reconnect to an in-flight turn."""
        session_id = build_session_id(request)
        if request.reconnect:
            async for frame in self.subscribe_stream(session_id):
                yield frame
            return

        lock = self._pool.get_lock(session_id)
        await lock.acquire()
        release_lock_on_exit = True
        try:
            state = self._pool.get_or_create(session_id)
            if state.lifecycle == AgentRunLifecycle.RUNNING:
                raise RuntimeError(
                    f"Session {session_id!r} is already running; use reconnect instead"
                )

            self._clear_story_workspace_dream_public_turn(
                session_id,
                state.current_turn_id,
            )
            state.current_turn_id = str(uuid4())
            state.current_dream_context = request.story_workspace_dream_context
            state.current_message_metadata = (
                dict(request.message_metadata)
                if isinstance(request.message_metadata, dict)
                else None
            )
            state.current_message_id = request.message_id
            state.current_user_id = str(request.user_id)
            bus = create_event_bus(session_id, state.current_turn_id)
            state.event_bus = bus
            state.mark_running()

            await self._observers.emit_before_context_assembly(
                session_id, {"resume": request.resume}
            )

            if state.runner is None:
                await self._observers.emit_before_runner_created(session_id)
                runner = ClaudeAgentRunner()
                state.with_runner(runner)
                await self._observers.emit_after_runner_created(session_id, runner)
            else:
                runner = state.runner

            try:
                execution = await self._service.assemble_context(
                    request, state=state, bus=bus, runner=runner
                )
            except Exception as exc:
                # Context assembly failed before bg_task was created (e.g.
                # workspace plugin pack raising WorkspacePackError). Surface
                # the failure as an SSE error frame + sentinel through the
                # EventBus so the frontend sees a proper error event instead
                # of a bare disconnect, and reset the lifecycle so the same
                # session can be retried instead of being stuck in RUNNING.
                logger.exception(
                    "Context assembly failed for session_id=%s", session_id
                )
                if state.lifecycle == AgentRunLifecycle.RUNNING:
                    state.mark_idle()
                self._clear_story_workspace_dream_public_turn(
                    session_id,
                    state.current_turn_id,
                )
                state.event_bus = None
                error_text = _format_exception_for_sse(exc)
                error_code = getattr(exc, "code", None)
                if isinstance(error_code, str) and error_code:
                    error_text = f"[{error_code}] {error_text}"
                await bus.publish(_sse("error", {"errorText": error_text}))
                await bus.publish(None)  # sentinel — closes the stream
                token = await bus.subscribe()
                try:
                    async for frame in bus.read(token):
                        yield frame
                finally:
                    await bus.unsubscribe(token)
                return

            await self._observers.emit_after_context_assembly(
                session_id, {"system_prompt_len": len(state.system_prompt)}
            )

            await self._observers.emit_before_session_started(
                session_id, {"resume": request.resume}
            )

            bg_task = asyncio.create_task(
                self._run_turn_task(execution, state, lock),
                name=f"claude-agent-session-{session_id}",
            )
            state.bg_task = bg_task
            # _run_turn_task releases the lock when the turn ends (or on early
            # disconnect the task keeps running and still owns lock release).
            release_lock_on_exit = False

            token = await bus.subscribe()
            try:
                async for frame in bus.read(token):
                    yield frame
            finally:
                await bus.unsubscribe(token)
        finally:
            if release_lock_on_exit:
                lock.release()

    async def subscribe_stream(self, session_id: str) -> AsyncGenerator[str, None]:
        """Subscribe to an in-flight turn's EventBus (replay + live frames)."""
        _validate_session_id(session_id)
        state = self._pool.get(session_id)
        if state is None or state.lifecycle != AgentRunLifecycle.RUNNING:
            raise RuntimeError(f"No running session for {session_id!r}")
        bus = state.event_bus
        if bus is None:
            raise RuntimeError(f"Session {session_id!r} has no active EventBus")

        token = await bus.subscribe()
        try:
            async for frame in bus.read(token):
                yield frame
        finally:
            await bus.unsubscribe(token)

    async def subscribe_expected_stream(
        self,
        session_id: str,
        expected_turn_id: str,
    ) -> AsyncGenerator[str, None]:
        """Replay one expected live turn without surfacing turn-race errors.

        Dream's adapter snapshots a turn ID before subscribing. A completed or
        replaced turn is an ordinary idle transition, not an exception exposed
        to a user-facing EventSource. Capturing the bus before subscribing keeps
        its replay buffer available even when the producer finishes immediately
        afterwards.
        """

        _validate_session_id(session_id)
        state = self._pool.get(session_id)
        if (
            state is None
            or state.lifecycle != AgentRunLifecycle.RUNNING
            or state.current_turn_id != expected_turn_id
        ):
            return
        bus = state.event_bus
        if bus is None:
            return
        try:
            token = await bus.subscribe()
        except Exception:
            return
        try:
            async for frame in bus.read(token):
                yield frame
        finally:
            await bus.unsubscribe(token)

    def is_expected_story_workspace_dream_turn(
        self,
        session_id: str,
        expected_turn_id: str,
        run_id: str,
        actor_id: str,
    ) -> bool:
        """Return whether the active turn is a trusted source of Dream output."""

        return self._trusted_story_workspace_dream_state(
            session_id,
            run_id,
            actor_id,
            expected_turn_id=expected_turn_id,
        ) is not None

    def story_workspace_dream_turn_snapshot(
        self,
        session_id: str,
        run_id: str,
        actor_id: str,
    ) -> Optional[dict[str, Any]]:
        """Return the trusted Dream turn and runtime-pending tool identities.

        This is deliberately separate from ``session_snapshot``. Generic Chat
        diagnostics must not expose, or become evidence for, a Dream turn.
        """

        state = self._trusted_story_workspace_dream_state(
            session_id,
            run_id,
            actor_id,
        )
        if state is None or not state.current_turn_id:
            return None
        turn_context = state.turn_context
        store = getattr(turn_context, "confirmation_store", None)
        pending_ids = getattr(store, "pending_ids", None)
        observation = "unknown"
        if not callable(pending_ids):
            runtime_pending: list[str] = []
        else:
            try:
                runtime_pending = [
                    item
                    for item in pending_ids()
                    if isinstance(item, str) and 0 < len(item) <= 255
                ]
                observation = "known"
            except Exception:
                logger.exception(
                    "Failed to read Dream runtime confirmations for session_id=%s",
                    session_id,
                )
                runtime_pending = []
        return {
            "turn_id": state.current_turn_id,
            "pending_tool_call_ids": runtime_pending,
            "pending_tool_call_ids_observation": observation,
        }

    def _trusted_story_workspace_dream_state(
        self,
        session_id: str,
        run_id: str,
        actor_id: str,
        *,
        expected_turn_id: Optional[str] = None,
    ) -> Optional[AgentRunState]:
        """Resolve one active state only when its Dream provenance is exact."""

        state = self._pool.get(session_id)
        if (
            state is None
            or state.lifecycle != AgentRunLifecycle.RUNNING
            or not state.current_turn_id
            or (
                expected_turn_id is not None
                and state.current_turn_id != expected_turn_id
            )
            or str(state.current_user_id or "") != actor_id
        ):
            return None
        context = state.current_dream_context
        metadata = state.current_message_metadata or {}
        kind = metadata.get("kind") if isinstance(metadata, dict) else None
        if (
            context is None
            or context.workflow_run_id != run_id
            or context.thread_id != session_id
            or kind not in {
                "story-workspace-dream-launch",
                "story-workspace-dream-confirmation",
                "story-workspace-dream-agent-user",
            }
        ):
            return None
        if kind == "story-workspace-dream-launch":
            trusted = (
                metadata.get("workflowRunId") == run_id
                and metadata.get("threadId") == session_id
                and str(metadata.get("actorId") or "") == actor_id
            )
        else:
            trusted = (
                metadata.get("story_workspace_run_id") == run_id
                and str(metadata.get("thread_id") or "") == session_id
                and str(metadata.get("actor_id") or metadata.get("actor") or "")
                == actor_id
            )
        return state if trusted else None

    def _clear_story_workspace_dream_public_turn(
        self,
        session_id: str,
        turn_id: Optional[str],
    ) -> None:
        """Drop public projections and observer leases owned by one old turn."""

        if not turn_id:
            return
        for attribute in (
            _DREAM_PUBLIC_TOOL_CONFIRMATIONS_ATTR,
            _DREAM_PUBLIC_TOOL_CONFIRMATION_SUBSCRIBERS_ATTR,
        ):
            registry = getattr(self, attribute, None)
            if not isinstance(registry, dict):
                continue
            for key in tuple(registry):
                if (
                    isinstance(key, tuple)
                    and len(key) >= 2
                    and key[0] == session_id
                    and key[1] == turn_id
                ):
                    registry.pop(key, None)

    async def _run_turn_task(
        self,
        execution: Any,
        state: AgentRunState,
        lock: asyncio.Lock,
    ) -> None:
        """Run execute_session and release per-session lock when the turn ends."""
        session_id = state.session_id
        turn_id = state.current_turn_id
        try:
            await self._service.execute_session(execution)
        except asyncio.CancelledError:
            logger.info("Turn cancelled for session_id=%s", session_id)
            raise
        except Exception:
            logger.exception("Turn failed for session_id=%s", session_id)
        finally:
            self._clear_story_workspace_dream_public_turn(session_id, turn_id)
            state.turn_context = None
            state.current_dream_context = None
            state.current_message_metadata = None
            state.current_message_id = None
            state.current_user_id = None
            state.event_bus = None
            state.bg_task = None
            if state.lifecycle == AgentRunLifecycle.RUNNING:
                state.mark_idle()
            await self._observers.emit_after_session_started(session_id)
            try:
                lock.release()
            except RuntimeError:
                logger.debug(
                    "Lock already released for session_id=%s", session_id
                )

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
        state = self._pool.get(session_id)
        turn_count = state.turn_count if state else None
        if state is not None:
            bg_task = state.bg_task
            if bg_task is not None and not bg_task.done():
                bg_task.cancel()
        self._pool.destroy(session_id)
        asyncio.create_task(
            self._fire_session_ended(session_id, reason="explicit_close", turn_count=turn_count),
            name=f"claude-agent-phase4-{session_id}",
        )

    async def stop_thread(self, session_id: str) -> dict[str, Any]:
        """Cancel the currently running turn without destroying the thread.

        This is intentionally narrower than ``close_thread``: it stops the
        in-flight ``bg_task`` while preserving the chat thread and reusable
        flyweight session for future turns.
        """

        _validate_session_id(session_id)
        state = self._pool.get(session_id)
        if state is None:
            return {
                "stop_requested": False,
                "running": False,
                "lifecycle": "not_found",
            }

        bg_task = state.bg_task
        if (
            state.lifecycle != AgentRunLifecycle.RUNNING
            or bg_task is None
            or bg_task.done()
        ):
            snapshot = state.snapshot()
            return {
                "stop_requested": False,
                "running": False,
                "lifecycle": snapshot.get("lifecycle", "idle"),
            }

        bg_task.cancel()
        if _STOP_WAIT_SECONDS > 0:
            try:
                await asyncio.wait_for(bg_task, timeout=_STOP_WAIT_SECONDS)
            except asyncio.CancelledError:
                pass
            except asyncio.TimeoutError:
                logger.warning(
                    "stop_thread timed out waiting for cancellation: session_id=%s",
                    session_id,
                )
            except Exception:
                logger.exception(
                    "stop_thread observed task failure while stopping: session_id=%s",
                    session_id,
                )

        snapshot = self.session_snapshot(session_id)
        lifecycle = snapshot.get("lifecycle", "not_found") if snapshot else "not_found"
        return {
            "stop_requested": True,
            "running": lifecycle == AgentRunLifecycle.RUNNING.value,
            "lifecycle": lifecycle,
        }

    def session_snapshot(self, session_id: str) -> Optional[dict[str, Any]]:
        return self._pool.snapshot_session(session_id)

    def list_session_snapshots(self) -> list[dict[str, Any]]:
        return self._pool.snapshot_all()

    def sweep_stats(self) -> dict[str, Any]:
        return self._sweeper.sweep_stats()

    def register_observer(self, observer: Any) -> None:
        self._observers.register(observer)

    def unregister_observer(self, observer: Any) -> None:
        self._observers.unregister(observer)

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
