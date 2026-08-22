# [Input] Consume claude_agent/thread_pool.py, claude_agent/service.py,
#         claude_agent/event_bus.py, claude_agent/admission.py,
#         libs/claude_agent_kit/runner.py, claude_agent/observer.py.
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
# [Sync] 2026-08-22: acquire one process-local concurrency/memory admission
#                    lease before context/SDK startup and release it in every terminal path.

"""Claude Agent Thread Factory — 四阶段会话编排入口."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
import os
from typing import Any, AsyncGenerator, AsyncIterator, Optional
from uuid import uuid4

from claude_agent.admission import (
    AgentAdmissionLease,
    ClaudeAgentAdmissionController,
)
from claude_agent.event_bus import IEventBus, create_event_bus
from claude_agent.chat_stream_adapter import ChatStreamAdapter
from claude_agent.observer import LoggingObserver, SessionObserverRegistry
from claude_agent.stream_events import NormalizedAgentEvent
from claude_agent.tool_confirmation_store import ToolConfirmationResolution
from libs.claude_agent_kit.server.agent_runner import ClaudeAgentRunner
from claude_agent.service import (
    ClaudeAgentRunRequest,
    ClaudeAgentService,
    _format_exception_for_sse,
)
from claude_agent.thread_pool import (
    AgentRunLifecycle,
    AgentRunState,
    AgentRunStatePool,
    AgentRunStateSweeper,
    _validate_session_id,
)
try:
    from services.story_workspace.dream_lifecycle_observer import (
        DreamObserver,
    )
except ModuleNotFoundError:
    from backend.services.story_workspace.dream_lifecycle_observer import (
        DreamObserver,
    )

logger = logging.getLogger(__name__)

_MAX_TOOL_CONFIRMATION_SNAPSHOT_IDS = 256
_MAX_TOOL_CALL_ID_LENGTH = 255


async def _publish_failure_terminal(
    bus: IEventBus,
    error_text: str,
    *,
    error_code: str | None = None,
    retryable: bool | None = None,
    retry_after_seconds: int | None = None,
) -> None:
    """Close one still-open turn with the existing Chat failure contract.

    Normal execution remains owned by ``ClaudeAgentService.execute_session``.
    This helper is only for factory failures that occur outside that method's
    normal runner-result path.  ``IEventBus.is_done`` keeps the fallback from
    adding a second terminal after a service already closed the stream.
    """

    if bus.is_done:
        return
    error_data: dict[str, Any] = {"errorText": error_text}
    if error_code:
        error_data["errorCode"] = error_code
    if retryable is not None:
        error_data["retryable"] = retryable
    if retry_after_seconds is not None:
        error_data["retryAfterSeconds"] = retry_after_seconds
    await bus.publish(NormalizedAgentEvent.create("error", error_data))
    await bus.publish_terminal(
        NormalizedAgentEvent.create("finish", {"finishReason": "error"})
    )


async def _publish_cancelled_terminal(bus: IEventBus) -> None:
    """Close a cancelled turn when cancellation lands outside Service's runner wait."""

    if bus.is_done:
        return
    await bus.publish_terminal(
        NormalizedAgentEvent.create(
            "finish",
            {"finishReason": "stop", "cancelled": True},
        )
    )


async def _publish_terminal_resilient(
    publisher: Any,
    *,
    task_name: str,
) -> None:
    """Finish one atomic terminal write despite repeated outer cancellation.

    The producer task may receive a second ``cancel()`` while it is already in
    its cancellation/error handler.  Publishing in a separately owned task
    and repeatedly shielding it prevents that second signal from reopening the
    stream without a sentinel.  The EventBus itself enforces first-terminal
    wins, so a racing service terminal remains single-valued.
    """

    terminal_task = asyncio.create_task(publisher, name=task_name)
    while not terminal_task.done():
        try:
            await asyncio.shield(terminal_task)
        except asyncio.CancelledError:
            # Preserve the caller's explicit ``raise`` after the terminal task
            # settles, but consume repeated cancellation at this await seam.
            continue
    await terminal_task


def _stop_wait_seconds() -> float:
    """Return the bounded wait for frontend stop requests."""

    try:
        raw = os.getenv("INK_AGENT_STOP_WAIT_S", "3") or "3"
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return 3.0


_STOP_WAIT_SECONDS: float = _stop_wait_seconds()


@dataclass(frozen=True, slots=True)
class _ChatTurnCompletion:
    saw_message_final: bool
    saw_finish: bool
    finish_reason: str | None
    cancelled: bool


class _ChatTurnCompletionTracker:
    def __init__(self) -> None:
        self.saw_message_final = False
        self.saw_finish = False
        self.finish_reason: str | None = None
        self.cancelled = False

    def observe(self, event: NormalizedAgentEvent) -> None:
        if event.is_keepalive or self.saw_finish:
            return
        if event.type == "message-final":
            self.saw_message_final = True
            return
        if event.type != "finish":
            return
        self.saw_finish = True
        self.finish_reason = str(event.data.get("finishReason") or "") or None
        self.cancelled = event.data.get("cancelled") is True

    def result(self) -> _ChatTurnCompletion:
        return _ChatTurnCompletion(
            saw_message_final=self.saw_message_final,
            saw_finish=self.saw_finish,
            finish_reason=self.finish_reason,
            cancelled=self.cancelled,
        )


class _ChatTurnStream(AsyncIterator[str]):
    """One Chat SSE iterator plus the completion of that exact same turn."""

    def __init__(
        self,
        source: AsyncGenerator[str, None],
        completion: asyncio.Future[_ChatTurnCompletion],
    ) -> None:
        self._source = source
        self.completion = completion

    def __aiter__(self) -> _ChatTurnStream:
        return self

    async def __anext__(self) -> str:
        return await anext(self._source)

    async def aclose(self) -> None:
        await self._source.aclose()


def build_session_id(request: ClaudeAgentRunRequest) -> str:
    """Return a stable session_id for *request*."""
    sid = request.thread_id
    _validate_session_id(sid)
    return sid


class ClaudeAgentThreadFactory:
    """Entry point for all Claude Agent streaming requests."""

    def __init__(
        self,
        *,
        dream_observer: DreamObserver | None = None,
        admission_controller: ClaudeAgentAdmissionController | None = None,
    ) -> None:
        self._pool = AgentRunStatePool()
        self._observers = SessionObserverRegistry()
        self._service = ClaudeAgentService()
        self._sweeper = AgentRunStateSweeper(
            self._pool,
            on_evicted=self._on_sessions_evicted,
        )
        self._observers.register(LoggingObserver())
        self._dream_observer = dream_observer or DreamObserver()
        self._observers.register(self._dream_observer)
        self._admission = admission_controller or ClaudeAgentAdmissionController()
        self._closing_turn_tasks: set[asyncio.Task[Any]] = set()
        self._phase4_tasks: set[asyncio.Task[Any]] = set()
        self._closing = False
        self._closed = False
        self._close_task: asyncio.Task[None] | None = None

    def start(self) -> None:
        self._require_accepting_runs()
        self._sweeper.start()
        logger.info(
            "ClaudeAgentThreadFactory started; admission=%s",
            self._admission.stats(),
        )

    async def aclose(self) -> None:
        """Drain the factory once and reject new work before the first await."""

        if self._closed:
            return
        close_task = self._close_task
        if close_task is None:
            # This assignment intentionally precedes task creation/any await.
            # A turn queued behind a per-thread lock will observe the gate when
            # it eventually acquires that lock and cannot resurrect the pool.
            self._closing = True
            close_task = asyncio.create_task(
                self._aclose_impl(),
                name="claude-agent-factory-close",
            )
            self._close_task = close_task
        await asyncio.shield(close_task)

    async def _aclose_impl(self) -> None:
        await self._sweeper.stop()
        running_tasks = [
            state.bg_task
            for session_id in self._pool.list_session_ids()
            if (state := self._pool.get(session_id)) is not None
            and state.bg_task is not None
            and not state.bg_task.done()
        ]
        running_tasks.extend(
            task for task in self._closing_turn_tasks if not task.done()
        )
        # The same turn can still be present in the pool and close tracker.
        running_tasks = list(dict.fromkeys(running_tasks))
        destroyed = self._pool.destroy_all()
        if running_tasks:
            for task in running_tasks:
                task.cancel()
            await asyncio.gather(*running_tasks, return_exceptions=True)
        while self._phase4_tasks:
            phase4 = list(self._phase4_tasks)
            await asyncio.gather(*phase4, return_exceptions=True)
            for task in phase4:
                self._owned_task_done(self._phase4_tasks, task)
        await self._observers.aclose()
        if destroyed:
            for sid in destroyed:
                await self._fire_session_ended(
                    sid, reason="factory_aclose", turn_count=None
                )
        self._closed = True
        logger.info("ClaudeAgentThreadFactory closed; destroyed %d session(s)", len(destroyed))

    def _require_accepting_runs(self) -> None:
        if self._closing or self._closed:
            raise RuntimeError("ClaudeAgentThreadFactory is closing")

    # ------------------------------------------------------------------
    # Primary API: streaming turn / reconnect
    # ------------------------------------------------------------------

    def run_streaming(
        self,
        request: ClaudeAgentRunRequest,
    ) -> _ChatTurnStream:
        """Return the sole public Agent turn stream and its completion handle."""

        completion: asyncio.Future[_ChatTurnCompletion] = (
            asyncio.get_running_loop().create_future()
        )
        return _ChatTurnStream(
            self._run_streaming_frames(request, completion),
            completion,
        )

    async def _run_streaming_frames(
        self,
        request: ClaudeAgentRunRequest,
        completion: asyncio.Future[_ChatTurnCompletion],
    ) -> AsyncGenerator[str, None]:
        """Private implementation for the canonical Chat turn stream."""

        self._require_accepting_runs()
        tracker = _ChatTurnCompletionTracker()
        session_id = build_session_id(request)
        if request.reconnect:
            adapter = ChatStreamAdapter()
            try:
                async for event in self._subscribe_events(session_id):
                    tracker.observe(event)
                    yield adapter.encode(event)
            finally:
                if not completion.done():
                    completion.set_result(tracker.result())
            return

        adapter = ChatStreamAdapter()
        lock = self._pool.get_lock(session_id)
        await lock.acquire()
        release_lock_on_exit = True
        state: AgentRunState | None = None
        try:
            # ``aclose`` can start while this request is queued behind another
            # turn. Recheck after acquisition before creating/reviving state.
            self._require_accepting_runs()
            state = self._pool.get_or_create(session_id)
            if state.lifecycle == AgentRunLifecycle.RUNNING:
                raise RuntimeError(
                    f"Session {session_id!r} is already running; use reconnect instead"
                )

            state.current_turn_id = str(uuid4())
            state.current_dream_context = None
            state.current_message_metadata = (
                dict(request.message_metadata)
                if isinstance(request.message_metadata, dict)
                else None
            )
            state.current_message_id = request.message_id
            state.current_user_id = str(request.user_id)
            bus = create_event_bus(session_id, state.current_turn_id)
            state.event_bus = bus

            # No await is permitted between RUNNING and bg_task ownership:
            # every externally observable running turn is therefore stoppable.
            state.mark_running()
            bg_task = asyncio.create_task(
                self._run_turn_task(request, state, bus, lock),
                name=f"claude-agent-session-{session_id}",
            )
            state.bg_task = bg_task
            # _run_turn_task releases the lock when the turn ends (or on early
            # disconnect the task keeps running and still owns lock release).
            release_lock_on_exit = False

            token = await bus.subscribe()
            try:
                async for event in bus.read(token):
                    tracker.observe(event)
                    yield adapter.encode(event)
            finally:
                await bus.unsubscribe(token)
        finally:
            if release_lock_on_exit:
                if state is not None and state.bg_task is None:
                    state.current_dream_context = None
                    state.current_message_metadata = None
                    state.current_message_id = None
                    state.current_user_id = None
                    state.event_bus = None
                    if state.lifecycle == AgentRunLifecycle.RUNNING:
                        state.mark_idle()
                lock.release()
            if not completion.done():
                completion.set_result(tracker.result())

    async def subscribe_stream(self, session_id: str) -> AsyncGenerator[str, None]:
        """Subscribe to an in-flight turn using the public Chat SSE adapter."""

        adapter = ChatStreamAdapter()
        async for event in self._subscribe_events(session_id):
            yield adapter.encode(event)

    async def _subscribe_events(
        self,
        session_id: str,
    ) -> AsyncGenerator[NormalizedAgentEvent, None]:
        """Subscribe to protocol-neutral replay and live events."""

        self._require_accepting_runs()
        _validate_session_id(session_id)
        state = self._pool.get(session_id)
        if state is None or state.lifecycle != AgentRunLifecycle.RUNNING:
            raise RuntimeError(f"No running session for {session_id!r}")
        bus = state.event_bus
        if bus is None:
            raise RuntimeError(f"Session {session_id!r} has no active EventBus")

        token = await bus.subscribe()
        try:
            # A Redis/in-memory subscription may itself yield control while
            # shutdown starts.  Do not open a reconnect reader after the gate.
            self._require_accepting_runs()
            async for event in bus.read(token):
                yield event
        finally:
            await bus.unsubscribe(token)

    async def _run_turn_task(
        self,
        request: ClaudeAgentRunRequest,
        state: AgentRunState,
        bus: IEventBus,
        lock: asyncio.Lock,
    ) -> None:
        """Own context assembly plus execution so every RUNNING turn is cancellable."""
        session_id = state.session_id
        turn_id = state.current_turn_id
        session_started = False
        admission_lease: AgentAdmissionLease | None = None
        try:
            admission_lease = self._admission.try_acquire(session_id)
            await self._observers.emit_before_context_assembly(
                session_id,
                {"resume": request.resume},
            )
            if state.runner is None:
                await self._observers.emit_before_runner_created(session_id)
                runner = ClaudeAgentRunner()
                state.with_runner(runner)
                await self._observers.emit_after_runner_created(session_id, runner)
            else:
                runner = state.runner
            execution = await self._service.assemble_context(
                request,
                state=state,
                bus=bus,
                runner=runner,
            )
            state.current_dream_context = execution.dream_context
            await self._observers.emit_after_context_assembly(
                session_id,
                {
                    "system_prompt_len": len(state.system_prompt),
                    "turn_id": turn_id,
                    "actor_id": str(request.user_id),
                    "event_bus": bus,
                    "dream_context": execution.dream_context,
                },
            )
            await self._observers.emit_before_session_started(
                session_id,
                {"resume": request.resume},
            )
            session_started = True
            await self._service.execute_session(execution)
        except asyncio.CancelledError:
            logger.info("Turn cancelled for session_id=%s", session_id)
            if bus is not None and not bus.is_done:
                try:
                    await _publish_terminal_resilient(
                        _publish_cancelled_terminal(bus),
                        task_name=f"claude-agent-cancel-terminal-{session_id}",
                    )
                except Exception:
                    logger.exception(
                        "Failed to publish cancellation terminal for session_id=%s",
                        session_id,
                    )
            raise
        except Exception as exc:
            logger.exception("Turn setup/execution failed for session_id=%s", session_id)
            if not bus.is_done:
                try:
                    error_text = _format_exception_for_sse(exc)
                    raw_error_code = getattr(exc, "code", None)
                    error_code = (
                        raw_error_code
                        if isinstance(raw_error_code, str) and raw_error_code
                        else None
                    )
                    if error_code:
                        error_text = f"[{error_code}] {error_text}"
                    retryable = getattr(exc, "retryable", None)
                    if not isinstance(retryable, bool):
                        retryable = None
                    retry_after_seconds = getattr(
                        exc, "retry_after_seconds", None
                    )
                    if not isinstance(retry_after_seconds, int):
                        retry_after_seconds = None
                    await _publish_terminal_resilient(
                        _publish_failure_terminal(
                            bus,
                            error_text,
                            error_code=error_code,
                            retryable=retryable,
                            retry_after_seconds=retry_after_seconds,
                        ),
                        task_name=f"claude-agent-failure-terminal-{session_id}",
                    )
                except Exception:
                    # A broken external EventBus must not prevent lifecycle and
                    # per-session lock cleanup below.
                    logger.exception(
                        "Failed to publish fallback terminal for session_id=%s",
                        session_id,
                    )
        finally:
            if admission_lease is not None:
                admission_lease.release()
            state.turn_context = None
            state.current_dream_context = None
            state.current_message_metadata = None
            state.current_message_id = None
            state.current_user_id = None
            state.event_bus = None
            state.bg_task = None
            if state.lifecycle == AgentRunLifecycle.RUNNING:
                state.mark_idle()
            try:
                if session_started:
                    await self._observers.emit_after_session_started(session_id)
            finally:
                try:
                    lock.release()
                except RuntimeError:
                    logger.debug(
                        "Lock already released for session_id=%s", session_id
                    )

    # ------------------------------------------------------------------
    # Tool confirmation
    # ------------------------------------------------------------------

    async def confirm_tool(
        self,
        session_id: str,
        tool_call_id: str,
        approved: bool,
        reason: Optional[str] = None,
        answers: Optional[dict[str, Any]] = None,
        *,
        actor_id: str,
    ) -> ToolConfirmationResolution | None:
        _validate_session_id(session_id)
        state = self._pool.get(session_id)
        if (
            state is None
            or state.lifecycle != AgentRunLifecycle.RUNNING
            or str(state.current_user_id or "") != str(actor_id)
        ):
            logger.warning(
                "confirm_tool: session %s is not an actor-owned running turn",
                session_id,
            )
            return None
        turn_id = state.current_turn_id
        if not turn_id:
            return None
        return await self._service.confirm_tool(
            state,
            tool_call_id,
            approved,
            reason,
            answers,
            thread_id=session_id,
            turn_id=turn_id,
        )

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
                self._track_owned_task(self._closing_turn_tasks, bg_task)
        self._pool.destroy(session_id)
        phase4_task = asyncio.create_task(
            self._fire_session_ended(
                session_id,
                reason="explicit_close",
                turn_count=turn_count,
            ),
            name=f"claude-agent-phase4-{session_id}",
        )
        self._track_owned_task(self._phase4_tasks, phase4_task)

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

    def tool_confirmation_snapshot(self, session_id: str) -> dict[str, Any]:
        """Return the Generic Chat runtime's pending confirmation identities.

        A non-running thread has no runtime-owned confirmations, so its empty
        observation is authoritative. A running turn is authoritative only
        when its confirmation store can be read successfully; missing or
        failing runtime state must remain unknown so a browser never treats a
        transport failure as proof that a historical confirmation was settled.
        """

        _validate_session_id(session_id)
        state = self._pool.get(session_id)
        if state is None or state.lifecycle != AgentRunLifecycle.RUNNING:
            return {
                "pending_tool_call_ids": [],
                "tool_confirmation_observation": "known",
            }

        turn_context = getattr(state, "turn_context", None)
        store = getattr(turn_context, "confirmation_store", None)
        pending_ids = getattr(store, "pending_ids", None)
        if not callable(pending_ids):
            return {
                "pending_tool_call_ids": [],
                "tool_confirmation_observation": "unknown",
            }

        try:
            observed = pending_ids()
            unique_ids: list[str] = []
            seen: set[str] = set()
            overflow = False
            for item in observed:
                if (
                    not isinstance(item, str)
                    or not item
                    or len(item) > _MAX_TOOL_CALL_ID_LENGTH
                    or item in seen
                ):
                    continue
                if len(unique_ids) >= _MAX_TOOL_CONFIRMATION_SNAPSHOT_IDS:
                    overflow = True
                    break
                seen.add(item)
                unique_ids.append(item)
        except Exception:
            logger.exception(
                "Failed to read Chat runtime confirmations for session_id=%s",
                session_id,
            )
            return {
                "pending_tool_call_ids": [],
                "tool_confirmation_observation": "unknown",
            }

        if overflow:
            return {
                "pending_tool_call_ids": [],
                "tool_confirmation_observation": "unknown",
            }

        return {
            "pending_tool_call_ids": unique_ids,
            "tool_confirmation_observation": "known",
        }

    def list_session_snapshots(self) -> list[dict[str, Any]]:
        return self._pool.snapshot_all()

    def sweep_stats(self) -> dict[str, Any]:
        stats = self._sweeper.sweep_stats()
        stats["admission"] = self._admission.stats()
        return stats

    def dream_lifecycle_diagnostics(self) -> dict[str, int]:
        """Return bounded process diagnostics, never workflow or Chat state."""

        return self._dream_observer.diagnostics()

    def dream_workflow_activity_projection(self) -> list[Any]:
        """Return the bounded, non-authoritative latest Dream activity hints."""

        return self._dream_observer.projection_snapshot()

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

    def _track_owned_task(
        self,
        registry: set[asyncio.Task[Any]],
        task: asyncio.Task[Any],
    ) -> None:
        registry.add(task)
        task.add_done_callback(
            lambda completed: self._owned_task_done(registry, completed)
        )

    @staticmethod
    def _owned_task_done(
        registry: set[asyncio.Task[Any]],
        task: asyncio.Task[Any],
    ) -> None:
        if task not in registry:
            return
        registry.discard(task)
        if task.cancelled():
            return
        try:
            failure = task.exception()
        except asyncio.CancelledError:
            return
        if failure is not None:
            logger.error(
                "Claude Agent owned cleanup task failed",
                exc_info=(type(failure), failure, failure.__traceback__),
            )

    async def _on_sessions_evicted(
        self, session_ids: list[str], reason: str
    ) -> None:
        for sid in session_ids:
            await self._fire_session_ended(
                sid,
                reason=reason,
                turn_count=None,
            )
