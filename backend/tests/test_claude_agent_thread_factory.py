# [Input] Consume ClaudeAgentThreadFactory, AgentRunStatePool, AgentRunLifecycle,
#         ClaudeAgentRunRequest from backend/claude_agent/.
# [Output] Verify Phase 2 runner flyweight cache, TTL eviction, close_thread,
#          observer hooks, Phase 1/4 extrinsic/intrinsic state contracts,
#          per-session lock serialisation.
# [Pos] test node in backend/tests
# [Sync] 2026-05-22: migrated from Pawkeyland scripts/test_claude_agent_thread_factory.py.
#                    Removed: pet/persona/mem0/IdentityService stubs.
#                    ENV: PAWKEYLAND_RUNNER_TTL_S → INK_AGENT_TTL_S.
# [Sync] 2026-06-06: align session_id expectations with current thread_id
#                    strategy and ClaudeAgentRunRequest.message_parts.
# [Sync] 2026-06-25: cover frontend stop flow cancelling a running background turn.
# [Sync] 2026-08-31: cover safe structured Dream binding failure SSE without code duplication in errorText.

"""Unit tests for ClaudeAgentThreadFactory.

Stubs out ClaudeAgentService and ClaudeAgentRunner so the SDK runtime is
never invoked during unit testing.
"""
from __future__ import annotations

import asyncio
import sys
import time
import types
import unittest
import unittest.mock
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]  # backend/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tests._sdk_stubs  # noqa: F401 — stub claude_agent_sdk before libs.claude_agent_kit

# Additional stubs already handled by _sdk_stubs; this comment left for clarity.
if "claude_agent_sdk" not in sys.modules:
    _sdk_stub = types.ModuleType("claude_agent_sdk")
    sys.modules["claude_agent_sdk"] = _sdk_stub
    sys.modules["claude_agent_sdk.types"] = types.ModuleType("claude_agent_sdk.types")

import claude_agent.thread_factory as thread_factory_module
from claude_agent.thread_factory import ClaudeAgentThreadFactory, build_session_id
from claude_agent.event_bus import create_event_bus
from claude_agent.stream_events import NormalizedAgentEvent
from claude_agent.thread_pool import (
    AgentRunLifecycle,
    AgentRunState,
    AgentRunStatePool,
    AgentRunStateSweeper,
)
from claude_agent.service import ClaudeAgentRunRequest, ClaudeAgentService
from claude_agent.observer import LoggingObserver, SessionObserverRegistry
from services.story_workspace.dream_lifecycle_observer import DreamObserver
from story_workspace.contracts import StoryWorkspaceDreamRunContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def _make_request(user_id: str = "user_1", message: str = "hello", thread_id: Optional[str] = None) -> ClaudeAgentRunRequest:
    return ClaudeAgentRunRequest(
        user_id=user_id,
        thread_id=thread_id or f"thread_{user_id}",
        message_parts=[{"type": "text", "text": message}],
    )


def _make_factory() -> ClaudeAgentThreadFactory:
    """Return a factory with Service and Runner stubbed out."""
    factory = ClaudeAgentThreadFactory()
    return factory


def _make_dream_context(
    *,
    run_id: str = "run_" + "1" * 32,
    thread_id: str = "thread_dream_trusted",
) -> StoryWorkspaceDreamRunContext:
    return StoryWorkspaceDreamRunContext(
        workflow_run_id=run_id,
        thread_id=thread_id,
        deck_id="deck-dream",
        deck_plugin_id="ink.dream.story-workflow",
        deck_plugin_version="1.0.0",
        deck_plugin_binding_id="dpb_" + "2" * 32,
        binding_revision=1,
        deck_runtime_snapshot_id="drs_" + "3" * 32,
        runtime_plugin_lock_id="rpl_" + "4" * 32,
    )


# ---------------------------------------------------------------------------
# build_session_id
# ---------------------------------------------------------------------------

class TestBuildSessionId(unittest.TestCase):
    def test_returns_thread_id(self):
        req = _make_request(user_id="alice", thread_id="thread_alice")
        self.assertEqual(build_session_id(req), "thread_alice")

    def test_rejects_slash_in_thread_id(self):
        req = _make_request(thread_id="a/b")
        with self.assertRaises(ValueError):
            build_session_id(req)

    def test_rejects_double_dot_in_thread_id(self):
        req = _make_request(thread_id="..evil")
        with self.assertRaises(ValueError):
            build_session_id(req)

    def test_different_threads_get_different_ids(self):
        r1 = _make_request(user_id="alice", thread_id="thread_alice")
        r2 = _make_request(user_id="alice", thread_id="thread_bob")
        self.assertNotEqual(build_session_id(r1), build_session_id(r2))


# ---------------------------------------------------------------------------
# AgentRunStatePool — basic
# ---------------------------------------------------------------------------

class TestAgentRunStatePool(unittest.TestCase):
    def setUp(self):
        self.pool = AgentRunStatePool()

    def test_get_or_create_returns_new_state(self):
        state = self.pool.get_or_create("u1")
        self.assertIsInstance(state, AgentRunState)
        self.assertEqual(state.session_id, "u1")

    def test_get_or_create_returns_same_state_on_repeat(self):
        s1 = self.pool.get_or_create("u1")
        s2 = self.pool.get_or_create("u1")
        self.assertIs(s1, s2)

    def test_different_sessions_are_isolated(self):
        s1 = self.pool.get_or_create("u1")
        s2 = self.pool.get_or_create("u2")
        self.assertIsNot(s1, s2)

    def test_destroy_marks_state_destroyed(self):
        self.pool.get_or_create("u1")
        self.pool.destroy("u1")
        state = self.pool._states["u1"]
        self.assertEqual(state.lifecycle, AgentRunLifecycle.DESTROYED)

    def test_get_returns_none_for_destroyed(self):
        self.pool.get_or_create("u1")
        self.pool.destroy("u1")
        self.assertIsNone(self.pool.get("u1"))

    def test_get_or_create_rebuilds_after_destroy(self):
        self.pool.get_or_create("u1").mark_running()
        original_lock = self.pool.get_lock("u1")
        self.pool.destroy("u1")
        new_state = self.pool.get_or_create("u1")
        self.assertEqual(new_state.lifecycle, AgentRunLifecycle.IDLE)
        self.assertIs(original_lock, self.pool.get_lock("u1"))

    def test_each_session_gets_own_lock(self):
        lock1 = self.pool.get_lock("u1")
        lock2 = self.pool.get_lock("u2")
        self.assertIsNot(lock1, lock2)

    def test_same_session_always_gets_same_lock(self):
        lock1 = self.pool.get_lock("u1")
        lock2 = self.pool.get_lock("u1")
        self.assertIs(lock1, lock2)

    def test_get_or_create_preserves_lock_obtained_before_first_state(self):
        """Factory acquires the lock before it creates the first state."""

        acquired_first = self.pool.get_lock("u1")
        self.pool.get_or_create("u1")
        self.assertIs(acquired_first, self.pool.get_lock("u1"))

    def test_destroy_all_destroys_all(self):
        self.pool.get_or_create("u1")
        self.pool.get_or_create("u2")
        destroyed = self.pool.destroy_all()
        self.assertCountEqual(destroyed, ["u1", "u2"])

    def test_snapshot_session_returns_dict(self):
        state = self.pool.get_or_create("u1")
        state.is_context_initialized = True
        snap = self.pool.snapshot_session("u1")
        self.assertIsInstance(snap, dict)
        self.assertEqual(snap["session_id"], "u1")
        self.assertTrue(snap["context_initialized"])

    def test_snapshot_session_returns_none_for_unknown(self):
        self.assertIsNone(self.pool.snapshot_session("unknown"))


# ---------------------------------------------------------------------------
# AgentRunState — lifecycle transitions
# ---------------------------------------------------------------------------

class TestAgentRunState(unittest.TestCase):
    def _state(self, sid="s1"):
        return AgentRunState(session_id=sid)

    def test_initial_lifecycle_is_idle(self):
        self.assertEqual(self._state().lifecycle, AgentRunLifecycle.IDLE)

    def test_mark_running_transitions_to_running(self):
        s = self._state()
        s.mark_running()
        self.assertEqual(s.lifecycle, AgentRunLifecycle.RUNNING)

    def test_mark_idle_from_running_increments_turn_count(self):
        s = self._state()
        s.mark_running()
        s.mark_idle()
        self.assertEqual(s.turn_count, 1)
        self.assertEqual(s.lifecycle, AgentRunLifecycle.IDLE)

    def test_mark_destroyed_clears_runner(self):
        s = self._state()
        s.runner = object()
        s.mark_destroyed()
        self.assertIsNone(s.runner)
        self.assertEqual(s.lifecycle, AgentRunLifecycle.DESTROYED)

    def test_cannot_mark_destroyed_state_running(self):
        s = self._state()
        s.mark_destroyed()
        with self.assertRaises(RuntimeError):
            s.mark_running()

    def test_is_expired_false_for_fresh_state(self):
        s = self._state()
        self.assertFalse(s.is_expired)

    def test_is_expired_true_when_idle_beyond_ttl(self):
        s = self._state()
        s._last_active_ts = time.monotonic() - 700  # > default 600s TTL
        self.assertTrue(s.is_expired)

    def test_is_expired_false_while_running(self):
        s = self._state()
        s.mark_running()
        s._last_active_ts = time.monotonic() - 700
        self.assertFalse(s.is_expired)  # only IDLE states expire

    def test_snapshot_contains_required_keys(self):
        s = self._state()
        snap = s.snapshot()
        for key in ("session_id", "lifecycle", "turn_count", "idle_seconds",
                    "remaining_seconds", "ttl_seconds", "runner_present",
                    "context_initialized"):
            self.assertIn(key, snap)

    def test_with_system_prompt_sets_field(self):
        s = self._state()
        s.with_system_prompt("You are a writer's assistant.")
        self.assertEqual(s.system_prompt, "You are a writer's assistant.")

    def test_with_runner_sets_field(self):
        s = self._state()
        sentinel = object()
        s.with_runner(sentinel)
        self.assertIs(s.runner, sentinel)


# ---------------------------------------------------------------------------
# AgentRunStateSweeper — TTL eviction
# ---------------------------------------------------------------------------

class TestAgentRunStateSweeper(unittest.TestCase):
    def setUp(self):
        self.pool = AgentRunStatePool()
        self.evicted_calls: list = []
        async def _on_evicted(sids, reason):
            self.evicted_calls.append((sids, reason))
        self.sweeper = AgentRunStateSweeper(self.pool, interval_s=9999, on_evicted=_on_evicted)

    def _expire(self, sid: str):
        state = self.pool.get_or_create(sid)
        state._last_active_ts = time.monotonic() - 700

    def test_sweep_once_evicts_expired_sessions(self):
        self._expire("u1")
        self.pool.get_or_create("u2")  # fresh — not expired
        evicted = _run(self.sweeper.sweep_once())
        self.assertIn("u1", evicted)
        self.assertNotIn("u2", evicted)

    def test_sweep_once_fires_callback(self):
        self._expire("u1")
        _run(self.sweeper.sweep_once())
        self.assertEqual(len(self.evicted_calls), 1)
        self.assertEqual(self.evicted_calls[0][1], "ttl_expired")

    def test_sweep_skips_locked_sessions(self):
        self._expire("u1")
        lock = self.pool.get_lock("u1")

        async def _hold_and_sweep():
            async with lock:
                return await self.sweeper.sweep_once()

        evicted = _run(_hold_and_sweep())
        self.assertNotIn("u1", evicted)

    def test_sweep_stats_contains_expected_keys(self):
        stats = self.sweeper.sweep_stats()
        self.assertIn("ttl_seconds", stats)
        self.assertIn("sweep_interval_seconds", stats)
        self.assertIn("active_sessions", stats)

    def test_stop_does_not_raise_when_not_started(self):
        _run(self.sweeper.stop())  # should not raise


# ---------------------------------------------------------------------------
# ClaudeAgentThreadFactory — runner flyweight (Phase 2)
# ---------------------------------------------------------------------------

class TestFactoryRunnerFlyweight(unittest.TestCase):
    """Runner is created once per session_id and reused across turns."""

    def setUp(self):
        self.factory = ClaudeAgentThreadFactory()
        # Stub service to avoid real SDK calls
        self._patch_service()

    def _patch_service(self):
        """Replace service methods with stubs that emit a minimal SSE stream."""
        async def _assemble(req, *, state, bus, runner):
            from claude_agent.event_bus import BusProxyQueue
            from claude_agent.service import _TurnExecution, _TurnContext
            from libs.claude_agent_kit.types import AgentRunOptions
            state.is_context_initialized = True
            state.system_prompt = "stub"
            text_parts = [
                part.get("text", "")
                for part in (req.message_parts or [])
                if isinstance(part, dict) and part.get("type") == "text"
            ]
            opts = AgentRunOptions(thread_id=state.session_id, user_message="".join(text_parts))
            turn_ctx = _TurnContext(
                queue=BusProxyQueue(bus),
                confirmation_store=unittest.mock.MagicMock(),
            )
            state.turn_context = turn_ctx
            return _TurnExecution(
                request=req, state=state, runner=runner,
                run_options=opts, turn_context=turn_ctx,
            )

        async def _execute(execution):
            await execution.turn_context.queue.put('data: {"type":"finish","reason":"success"}\n\n')
            await execution.turn_context.queue.put(None)

        self.factory._service.assemble_context = _assemble
        self.factory._service.execute_session = _execute

        # Stub ClaudeAgentRunner to avoid real SDK
        self._runner_instances: list = []
        factory = self.factory

        class _FakeRunner:
            # Original ClaudeAgentRunner.__init__ takes optional sdk_client only
            def __init__(self, sdk_client=None):
                self.session_id = None  # set after creation in factory
                factory._test_runner_instances = getattr(factory, "_test_runner_instances", [])
                factory._test_runner_instances.append(self)

        with unittest.mock.patch("claude_agent.thread_factory.ClaudeAgentRunner", _FakeRunner):
            self._FakeRunner = _FakeRunner

    def _drain(self, req: ClaudeAgentRunRequest) -> list[str]:
        async def _collect():
            frames = []
            async for frame in self.factory.run_streaming(req):
                frames.append(frame)
            return frames
        with unittest.mock.patch("claude_agent.thread_factory.ClaudeAgentRunner", self._FakeRunner):
            return _run(_collect())

    def test_runner_created_on_first_turn(self):
        req = _make_request("user_runner_1")
        with unittest.mock.patch("claude_agent.thread_factory.ClaudeAgentRunner", self._FakeRunner):
            _run(self._collect_gen(req))
        self.assertEqual(len(getattr(self.factory, "_test_runner_instances", [])), 1)

    def test_run_streaming_exposes_same_turn_completion_handle(self):
        async def collect():
            stream = self.factory.run_streaming(_make_request("completion-handle"))
            frames = [frame async for frame in stream]
            return frames, await stream.completion

        with unittest.mock.patch(
            "claude_agent.thread_factory.ClaudeAgentRunner",
            self._FakeRunner,
        ):
            frames, completion = _run(collect())

        self.assertTrue(frames)
        self.assertTrue(completion.saw_finish)

    def test_runner_reused_on_second_turn(self):
        req = _make_request("user_runner_2")
        with unittest.mock.patch("claude_agent.thread_factory.ClaudeAgentRunner", self._FakeRunner):
            _run(self._collect_gen(req))
            _run(self._collect_gen(req))
        instances = getattr(self.factory, "_test_runner_instances", [])
        self.assertEqual(len(instances), 1, "Runner should be created only once within TTL")

    def _install_dream_observer(self, coordinator) -> None:
        self.factory.unregister_observer(self.factory._dream_observer)
        self.factory._dream_observer = DreamObserver(coordinator)
        self.factory.register_observer(self.factory._dream_observer)

    def _assemble_with_dream_context(self, context, calls=None) -> None:
        original_assemble = self.factory._service.assemble_context

        async def assemble(*args, **kwargs):
            execution = await original_assemble(*args, **kwargs)
            execution.dream_context = context
            if calls is not None:
                calls.append(("assemble", kwargs["state"].current_turn_id))
            return execution

        self.factory._service.assemble_context = assemble

    def test_dream_observer_attaches_after_context_and_closes_after_turn(self):
        calls: list[tuple[str, str | None]] = []

        class RecordingCoordinator:
            async def attach_before_session_execution(
                self,
                *,
                context,
                actor_id,
                turn_id,
                bus,
            ):
                self.assertions = (context, actor_id, turn_id, bus)
                calls.append(("attach", turn_id))

            async def close_turn(self, _thread_id, turn_id, *, reason):
                calls.append((reason, turn_id))

        coordinator = RecordingCoordinator()
        self._install_dream_observer(coordinator)
        context = _make_dream_context(thread_id="thread_dream_observed")
        self._assemble_with_dream_context(context, calls)
        request = ClaudeAgentRunRequest(
            user_id="7",
            thread_id=context.thread_id,
            message_parts=[{"type": "text", "text": "dream"}],
        )

        async def scenario():
            await self._collect_gen(request)
            state = self.factory._pool.get(context.thread_id)
            task = state.bg_task if state is not None else None
            if task is not None:
                await task

        with unittest.mock.patch(
            "claude_agent.thread_factory.ClaudeAgentRunner",
            self._FakeRunner,
        ):
            _run(scenario())

        self.assertEqual(calls[0][0], "assemble")
        self.assertEqual(calls[1][0], "attach")
        self.assertIn(("session_execution_finished", calls[0][1]), calls)

    def test_public_run_request_has_no_dream_context_field(self):
        request = ClaudeAgentRunRequest(
            user_id="7",
            thread_id="thread-requested",
            message_parts=[{"type": "text", "text": "dream"}],
        )
        self.assertFalse(hasattr(request, "story_workspace_dream_context"))

    def test_dream_observer_attach_failure_is_off_path_and_still_cleaned(self):
        closed: list[tuple[str, str]] = []

        class FailingCoordinator:
            async def attach_before_session_execution(self, **_kwargs):
                raise RuntimeError("observer unavailable")

            async def close_turn(self, thread_id, _turn_id, *, reason):
                closed.append((thread_id, reason))

        self._install_dream_observer(FailingCoordinator())
        context = _make_dream_context(thread_id="thread-dream-off-path")
        self._assemble_with_dream_context(context)
        request = ClaudeAgentRunRequest(
            user_id="7",
            thread_id=context.thread_id,
            message_parts=[{"type": "text", "text": "dream"}],
        )

        async def scenario():
            await self._collect_gen(request)
            state = self.factory._pool.get(context.thread_id)
            task = state.bg_task if state is not None else None
            if task is not None:
                await task

        with (
            unittest.mock.patch(
                "claude_agent.thread_factory.ClaudeAgentRunner",
                self._FakeRunner,
            ),
            unittest.mock.patch("claude_agent.thread_factory.logger.exception"),
        ):
            _run(scenario())

        self.assertIn((context.thread_id, "session_execution_finished"), closed)

    def test_dream_close_failure_after_run_cannot_strand_state_or_lock(self):
        class FailingCloseCoordinator:
            def __init__(self):
                self.close_calls = 0

            async def attach_before_session_execution(self, **_kwargs):
                return None

            async def close_turn(self, *_args, **_kwargs):
                self.close_calls += 1
                raise RuntimeError("dream close unavailable")

        coordinator = FailingCloseCoordinator()
        self._install_dream_observer(coordinator)
        context = _make_dream_context(thread_id="thread-dream-close-fails")
        self._assemble_with_dream_context(context)
        request = ClaudeAgentRunRequest(
            user_id="7",
            thread_id=context.thread_id,
            message_parts=[{"type": "text", "text": "dream"}],
        )

        async def scenario():
            await self._collect_gen(request)
            state = self.factory._pool.get(context.thread_id)
            for _ in range(100):
                if state is not None and state.bg_task is None:
                    break
                await asyncio.sleep(0.01)
            return state, self.factory._pool.get_lock(context.thread_id).locked()

        with (
            unittest.mock.patch(
                "claude_agent.thread_factory.ClaudeAgentRunner",
                self._FakeRunner,
            ),
            unittest.mock.patch("claude_agent.thread_factory.logger.exception"),
        ):
            state, lock_is_held = _run(scenario())

        self.assertEqual(coordinator.close_calls, 1)
        self.assertIsNotNone(state)
        self.assertEqual(state.lifecycle, AgentRunLifecycle.IDLE)
        self.assertIsNone(state.event_bus)
        self.assertFalse(lock_is_held)

    def test_pre_assembly_setup_failure_does_not_attach_dream_observer(self):
        class RecordingCoordinator:
            def __init__(self):
                self.attach_calls = 0
                self.close_calls = 0

            async def attach_before_session_execution(self, **_kwargs):
                self.attach_calls += 1

            async def close_turn(self, *_args, **_kwargs):
                self.close_calls += 1

        coordinator = RecordingCoordinator()
        self._install_dream_observer(coordinator)
        context = _make_dream_context(thread_id="thread-dream-setup-fails")
        request = ClaudeAgentRunRequest(
            user_id="7",
            thread_id=context.thread_id,
            message_parts=[{"type": "text", "text": "dream"}],
        )
        state = self.factory._pool.get_or_create(context.thread_id)
        state.mark_running = unittest.mock.Mock(
            side_effect=RuntimeError("primary setup failed")
        )

        with (
            self.assertRaisesRegex(RuntimeError, "primary setup failed"),
            unittest.mock.patch("claude_agent.thread_factory.logger.exception"),
        ):
            _run(self._collect_gen(request))

        self.assertEqual(coordinator.attach_calls, 0)
        self.assertEqual(coordinator.close_calls, 0)
        self.assertEqual(state.lifecycle, AgentRunLifecycle.IDLE)
        self.assertIsNone(state.event_bus)
        self.assertFalse(self.factory._pool.get_lock(context.thread_id).locked())

    def test_dream_confirmation_followup_queues_behind_in_flight_turn(self):
        """The real factory lock serializes a confirmed business follow-up."""

        from services.story_workspace.dream_confirmation_service import (
            story_workspace_build_dream_confirmation_turn_dispatcher,
        )

        first_request = _make_request(
            "user_dream_queue",
            message="first",
            thread_id="thread_dream_queue",
        )
        second_parts = [{"type": "text", "text": "structured confirmation"}]
        second_metadata = {"kind": "story-workspace-dream-confirmation"}
        first_release: asyncio.Event
        first_started: asyncio.Event
        second_started: asyncio.Event
        executed_messages: list[str]

        async def _scenario():
            nonlocal first_release, first_started, second_started, executed_messages
            first_release = asyncio.Event()
            first_started = asyncio.Event()
            second_started = asyncio.Event()
            executed_messages = []

            async def _execute(execution):
                text = "".join(
                    part.get("text", "")
                    for part in (execution.request.message_parts or [])
                    if isinstance(part, dict) and part.get("type") == "text"
                )
                executed_messages.append(text)
                if text == "first":
                    first_started.set()
                    await first_release.wait()
                else:
                    second_started.set()
                await execution.turn_context.queue.put(
                    'data: {"type":"finish","reason":"success"}\n\n'
                )
                await execution.turn_context.queue.put(None)

            self.factory._service.execute_session = _execute
            dispatcher = story_workspace_build_dream_confirmation_turn_dispatcher(
                self.factory,
                request_factory=ClaudeAgentRunRequest,
            )

            with unittest.mock.patch(
                "claude_agent.thread_factory.ClaudeAgentRunner",
                self._FakeRunner,
            ):
                first_consumer = asyncio.create_task(
                    self._collect_gen(first_request)
                )
                await asyncio.wait_for(first_started.wait(), timeout=1.0)

                dispatched = dispatcher(
                    "thread_dream_queue",
                    "user_dream_queue",
                    "dream-confirmation-message",
                    second_parts,
                    second_metadata,
                )
                self.assertTrue(dispatched)
                await asyncio.sleep(0)
                self.assertEqual(executed_messages, ["first"])

                first_release.set()
                await asyncio.wait_for(first_consumer, timeout=1.0)
                await asyncio.wait_for(second_started.wait(), timeout=1.0)

                for _ in range(100):
                    snapshot = self.factory.session_snapshot("thread_dream_queue")
                    if snapshot and snapshot["lifecycle"] == "idle":
                        break
                    await asyncio.sleep(0.01)
                return dispatched, snapshot

        dispatched, snapshot = _run(_scenario())
        self.assertTrue(dispatched)
        self.assertEqual(
            executed_messages,
            ["first", "structured confirmation"],
        )
        self.assertEqual(snapshot["lifecycle"], "idle")

    async def _collect_gen(self, req):
        async for _ in self.factory.run_streaming(req):
            pass

    def test_different_sessions_get_different_runners(self):
        req1 = _make_request("user_a")
        req2 = _make_request("user_b")
        with unittest.mock.patch("claude_agent.thread_factory.ClaudeAgentRunner", self._FakeRunner):
            _run(self._collect_gen(req1))
            _run(self._collect_gen(req2))
        instances = getattr(self.factory, "_test_runner_instances", [])
        self.assertEqual(len(instances), 2)
        # Different runner instances (by identity) for different sessions
        self.assertIsNot(instances[0], instances[1])

    def test_close_thread_destroys_session(self):
        req = _make_request("user_close", thread_id="thread_close")

        async def _run_and_close():
            with unittest.mock.patch("claude_agent.thread_factory.ClaudeAgentRunner", self._FakeRunner):
                await self._collect_gen(req)
            self.factory.close_thread("thread_close")

        _run(_run_and_close())
        state = self.factory._pool._states.get("thread_close")
        self.assertEqual(state.lifecycle, AgentRunLifecycle.DESTROYED)

    def test_session_snapshot_returns_dict(self):
        req = _make_request("user_snap", thread_id="thread_snap")
        with unittest.mock.patch("claude_agent.thread_factory.ClaudeAgentRunner", self._FakeRunner):
            _run(self._collect_gen(req))
        snap = self.factory.session_snapshot("thread_snap")
        self.assertIsNotNone(snap)
        self.assertEqual(snap["session_id"], "thread_snap")

    def test_session_snapshot_none_for_unknown(self):
        self.assertIsNone(self.factory.session_snapshot("nonexistent"))

    def test_tool_confirmation_snapshot_is_known_empty_without_a_running_turn(self):
        self.factory._pool.get_or_create("thread-idle")

        self.assertEqual(
            self.factory.tool_confirmation_snapshot("thread-idle"),
            {
                "pending_tool_call_ids": [],
                "tool_confirmation_observation": "known",
            },
        )
        self.assertEqual(
            self.factory.tool_confirmation_snapshot("thread-not-found"),
            {
                "pending_tool_call_ids": [],
                "tool_confirmation_observation": "known",
            },
        )

    def test_tool_confirmation_snapshot_reads_deduplicated_bounded_runtime_ids(self):
        state = self.factory._pool.get_or_create("thread-running-confirmation")
        state.turn_context = SimpleNamespace(
            confirmation_store=SimpleNamespace(
                pending_ids=lambda: [
                    "call-pending",
                    "call-pending",
                    "",
                    "x" * 256,
                    42,
                    "call-second",
                ],
            ),
        )
        state.mark_running()

        self.assertEqual(
            self.factory.tool_confirmation_snapshot("thread-running-confirmation"),
            {
                "pending_tool_call_ids": ["call-pending", "call-second"],
                "tool_confirmation_observation": "known",
            },
        )

    def test_tool_confirmation_snapshot_is_unknown_when_running_store_is_unreadable(self):
        state = self.factory._pool.get_or_create("thread-running-unknown")
        state.turn_context = SimpleNamespace(confirmation_store=None)
        state.mark_running()

        self.assertEqual(
            self.factory.tool_confirmation_snapshot("thread-running-unknown"),
            {
                "pending_tool_call_ids": [],
                "tool_confirmation_observation": "unknown",
            },
        )

    def test_tool_confirmation_snapshot_is_unknown_when_pending_ids_exceed_limit(self):
        state = self.factory._pool.get_or_create("thread-running-overflow")
        state.turn_context = SimpleNamespace(
            confirmation_store=SimpleNamespace(
                pending_ids=lambda: [f"call-{index}" for index in range(257)],
            ),
        )
        state.mark_running()

        self.assertEqual(
            self.factory.tool_confirmation_snapshot("thread-running-overflow"),
            {
                "pending_tool_call_ids": [],
                "tool_confirmation_observation": "unknown",
            },
        )

    def test_stop_thread_cancels_running_turn(self):
        req = _make_request("user_stop", thread_id="thread_stop")

        async def _execute_until_cancel(execution):
            await execution.turn_context.queue.put(
                'data: {"type":"text-start","id":"text-0"}\n\n'
            )
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                await execution.turn_context.queue.put(
                    'data: {"type":"finish","finishReason":"stop"}\n\n'
                )
                await execution.turn_context.queue.put(None)
                raise

        async def _scenario():
            self.factory._service.execute_session = _execute_until_cancel
            frames: list[str] = []

            with unittest.mock.patch("claude_agent.thread_factory.ClaudeAgentRunner", self._FakeRunner):
                consumer = asyncio.create_task(self._collect_frames(req, frames))
                for _ in range(100):
                    snapshot = self.factory.session_snapshot("thread_stop")
                    if snapshot and snapshot.get("lifecycle") == "running":
                        break
                    await asyncio.sleep(0.01)

                result = await self.factory.stop_thread("thread_stop")
                await asyncio.wait_for(consumer, timeout=1.0)
                return result, frames, self.factory.session_snapshot("thread_stop")

        result, frames, snapshot = _run(_scenario())

        self.assertTrue(result["stop_requested"])
        self.assertFalse(result["running"])
        self.assertEqual(result["lifecycle"], "idle")
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["lifecycle"], "idle")
        self.assertTrue(any('"finishReason":"stop"' in frame for frame in frames))

    def test_stop_during_context_assembly_has_one_cancel_terminal(self):
        request = _make_request("assemble_stop", thread_id="thread_assemble_stop")

        async def scenario():
            entered = asyncio.Event()

            async def assemble(_request, *, state, bus, runner):
                del state, bus, runner
                entered.set()
                await asyncio.Event().wait()

            self.factory._service.assemble_context = assemble
            frames: list[str] = []
            with unittest.mock.patch(
                "claude_agent.thread_factory.ClaudeAgentRunner",
                self._FakeRunner,
            ):
                consumer = asyncio.create_task(self._collect_frames(request, frames))
                await asyncio.wait_for(entered.wait(), timeout=0.2)
                state = self.factory._pool.get(request.thread_id)
                self.assertIsNotNone(state)
                self.assertEqual(state.lifecycle, AgentRunLifecycle.RUNNING)
                self.assertIsNotNone(state.bg_task)
                self.assertFalse(state.bg_task.done())
                stopped = await self.factory.stop_thread(request.thread_id)
                await asyncio.wait_for(consumer, timeout=0.5)
            return stopped, frames

        stopped, frames = _run(scenario())
        self.assertEqual(stopped["lifecycle"], "idle")
        self.assertEqual(
            sum('"type":"finish"' in frame.replace(" ", "") for frame in frames),
            1,
        )
        self.assertIn('"finishReason":"stop"', "".join(frames).replace(" ", ""))

    def test_stop_after_service_terminal_does_not_add_second_finish(self):
        request = _make_request("terminal_stop", thread_id="thread_terminal_stop")

        async def scenario():
            terminal_published = asyncio.Event()

            async def execute(execution):
                await execution.turn_context.queue.put(
                    NormalizedAgentEvent.create("message-final", {"text": "done"})
                )
                await execution.turn_context.queue.put(
                    NormalizedAgentEvent.create(
                        "finish", {"finishReason": "stop"}
                    )
                )
                terminal_published.set()
                await asyncio.Event().wait()

            self.factory._service.execute_session = execute
            frames: list[str] = []
            with unittest.mock.patch(
                "claude_agent.thread_factory.ClaudeAgentRunner",
                self._FakeRunner,
            ):
                consumer = asyncio.create_task(self._collect_frames(request, frames))
                await asyncio.wait_for(terminal_published.wait(), timeout=0.2)
                await asyncio.wait_for(consumer, timeout=0.2)
                stopped = await self.factory.stop_thread(request.thread_id)
            return stopped, frames

        stopped, frames = _run(scenario())
        self.assertEqual(stopped["lifecycle"], "idle")
        self.assertEqual(
            sum('"type":"finish"' in frame.replace(" ", "") for frame in frames),
            1,
        )

    def test_repeated_cancel_during_terminal_write_still_closes_once(self):
        async def scenario():
            factory = ClaudeAgentThreadFactory()
            state = factory._pool.get_or_create("thread_double_cancel")
            state.mark_running()
            state.current_turn_id = "turn-double-cancel"
            state.runner = unittest.mock.Mock()
            bus = create_event_bus(state.session_id, state.current_turn_id)
            state.event_bus = bus
            lock = factory._pool.get_lock(state.session_id)
            await lock.acquire()
            execute_entered = asyncio.Event()
            terminal_entered = asyncio.Event()
            release_terminal = asyncio.Event()

            async def assemble(_request, *, state, bus, runner):
                del state, bus, runner
                return SimpleNamespace(dream_context=None)

            async def execute(_execution):
                execute_entered.set()
                await asyncio.Event().wait()

            original = thread_factory_module._publish_cancelled_terminal

            async def blocked_terminal(selected_bus):
                terminal_entered.set()
                await release_terminal.wait()
                await original(selected_bus)

            factory._service.assemble_context = assemble
            factory._service.execute_session = execute
            token = await bus.subscribe()
            with unittest.mock.patch.object(
                thread_factory_module,
                "_publish_cancelled_terminal",
                blocked_terminal,
            ):
                task = asyncio.create_task(
                    factory._run_turn_task(
                        _make_request(
                            "double_cancel",
                            thread_id=state.session_id,
                        ),
                        state,
                        bus,
                        lock,
                    )
                )
                await asyncio.wait_for(execute_entered.wait(), timeout=0.2)
                task.cancel()
                await asyncio.wait_for(terminal_entered.wait(), timeout=0.2)
                task.cancel()
                release_terminal.set()
                with self.assertRaises(asyncio.CancelledError):
                    await task
            events = [event async for event in bus.read(token)]
            await bus.unsubscribe(token)
            return events

        events = _run(scenario())
        self.assertEqual([event.type for event in events], ["finish"])
        self.assertEqual(events[0].data["finishReason"], "stop")
        self.assertIs(events[0].data["cancelled"], True)

    async def _collect_frames(self, req, frames):
        async for frame in self.factory.run_streaming(req):
            frames.append(frame)


# ---------------------------------------------------------------------------
# Observer registration
# ---------------------------------------------------------------------------

class TestObserverRegistration(unittest.TestCase):
    def test_register_and_unregister(self):
        factory = ClaudeAgentThreadFactory()
        obs = LoggingObserver()
        factory.register_observer(obs)
        factory.unregister_observer(obs)
        # No error = pass

    def test_logging_observer_registered_by_default(self):
        factory = ClaudeAgentThreadFactory()
        observers = factory._observers._observers
        self.assertTrue(
            any(isinstance(o, LoggingObserver) for o in observers),
            "LoggingObserver should be registered at factory creation",
        )


# ---------------------------------------------------------------------------
# Factory aclose
# ---------------------------------------------------------------------------

class TestFactoryAclose(unittest.TestCase):
    def test_aclose_destroys_all_sessions(self):
        factory = ClaudeAgentThreadFactory()
        factory._pool.get_or_create("u1")
        factory._pool.get_or_create("u2")
        _run(factory.aclose())
        for sid in ("u1", "u2"):
            state = factory._pool._states.get(sid)
            self.assertEqual(state.lifecycle, AgentRunLifecycle.DESTROYED)

    def test_close_thread_cleanup_remains_factory_owned_until_aclose(self):
        async def scenario():
            class Coordinator:
                def __init__(self):
                    self.entered = asyncio.Event()
                    self.release = asyncio.Event()
                    self.closed = False

                async def close_session(self, _session_id, *, reason):
                    self.assert_reason = reason
                    self.entered.set()
                    await self.release.wait()

                async def aclose(self):
                    self.closed = True

            coordinator = Coordinator()
            factory = ClaudeAgentThreadFactory(
                dream_observer=DreamObserver(coordinator),
            )
            state = factory._pool.get_or_create("thread-close-owned")
            state.mark_running()
            turn_entered = asyncio.Event()

            async def turn():
                turn_entered.set()
                await asyncio.Event().wait()

            state.bg_task = asyncio.create_task(turn())
            await turn_entered.wait()
            factory.close_thread(state.session_id)
            await asyncio.wait_for(coordinator.entered.wait(), timeout=0.2)
            self.assertEqual(len(factory._phase4_tasks), 1)

            closing = asyncio.create_task(factory.aclose())
            await asyncio.sleep(0)
            self.assertFalse(closing.done())
            coordinator.release.set()
            await asyncio.wait_for(closing, timeout=0.2)
            self.assertEqual(factory._closing_turn_tasks, set())
            self.assertEqual(factory._phase4_tasks, set())
            self.assertTrue(coordinator.closed)

        _run(scenario())

    def test_aclose_is_idempotent_and_sets_gate_before_drain_await(self):
        async def scenario():
            class Coordinator:
                def __init__(self):
                    self.calls = 0
                    self.entered = asyncio.Event()
                    self.release = asyncio.Event()

                async def aclose(self):
                    self.calls += 1
                    self.entered.set()
                    await self.release.wait()

            coordinator = Coordinator()
            factory = ClaudeAgentThreadFactory(
                dream_observer=DreamObserver(coordinator),
            )
            first = asyncio.create_task(factory.aclose())
            await asyncio.wait_for(coordinator.entered.wait(), timeout=0.2)
            self.assertTrue(factory._closing)
            second = asyncio.create_task(factory.aclose())

            request = _make_request(
                "closing-rejected",
                thread_id="thread-closing-rejected",
            )
            stream = factory.run_streaming(request)
            with self.assertRaisesRegex(RuntimeError, "closing"):
                await anext(stream)
            await stream.aclose()

            reconnect = factory.run_streaming(
                ClaudeAgentRunRequest(
                    user_id="closing-rejected",
                    thread_id="thread-closing-rejected",
                    reconnect=True,
                )
            )
            with self.assertRaisesRegex(RuntimeError, "closing"):
                await anext(reconnect)
            await reconnect.aclose()

            coordinator.release.set()
            await asyncio.wait_for(asyncio.gather(first, second), timeout=0.2)
            await factory.aclose()
            return coordinator.calls, factory._closed

        calls, closed = _run(scenario())
        self.assertEqual(calls, 1)
        self.assertTrue(closed)

    def test_turn_queued_on_lock_rechecks_close_gate_after_acquire(self):
        async def scenario():
            class Coordinator:
                async def aclose(self):
                    return None

            factory = ClaudeAgentThreadFactory(
                dream_observer=DreamObserver(Coordinator()),
            )
            request = _make_request(
                "close-race",
                thread_id="thread-close-race",
            )
            lock = factory._pool.get_lock(request.thread_id)
            await lock.acquire()
            stream = factory.run_streaming(request)
            queued = asyncio.create_task(anext(stream))
            await asyncio.sleep(0)
            self.assertFalse(queued.done())

            await factory.aclose()
            self.assertFalse(queued.done())
            lock.release()
            with self.assertRaisesRegex(RuntimeError, "closing"):
                await asyncio.wait_for(queued, timeout=0.2)
            await stream.aclose()
            return factory._pool.get(request.thread_id), lock.locked()

        state, lock_is_held = _run(scenario())
        self.assertIsNone(state)
        self.assertFalse(lock_is_held)


# ---------------------------------------------------------------------------
# assemble_context failure (workspace pack) → SSE error frame
# ---------------------------------------------------------------------------

class TestAssembleContextFailure(unittest.TestCase):
    """assemble_context raising (e.g. WorkspacePackError from plugin pack)
    must surface an SSE error frame + sentinel instead of a bare disconnect,
    and must reset the session lifecycle so the session can be retried."""

    def setUp(self):
        self.factory = ClaudeAgentThreadFactory()

    def _fail_assemble(self, exc: Exception):
        async def _assemble(req, *, state, bus, runner):
            raise exc
        self.factory._service.assemble_context = _assemble

    def _drain(self, req: ClaudeAgentRunRequest) -> list[str]:
        async def _collect():
            frames = []
            async for frame in self.factory.run_streaming(req):
                frames.append(frame)
            return frames
        with unittest.mock.patch("claude_agent.thread_factory.ClaudeAgentRunner"):
            return _run(_collect())

    def test_pack_failure_emits_sse_error_frame(self):
        from services.claude_plugin.workspace_packer import WorkspacePackError
        self._fail_assemble(
            WorkspacePackError("WORKSPACE_PACK_DIGEST_MISMATCH", "digest mismatch")
        )
        req = _make_request("user_pack_fail_1")
        frames = self._drain(req)
        error_frames = [f for f in frames if '"type":"error"' in f.replace(" ", "")]
        self.assertTrue(error_frames, f"expected an SSE error frame, got: {frames!r}")
        self.assertIn("WORKSPACE_PACK_DIGEST_MISMATCH", error_frames[0])
        self.assertIn("digest mismatch", error_frames[0])
        self.assertEqual(
            sum('"type":"finish"' in frame.replace(" ", "") for frame in frames),
            1,
        )
        self.assertIn('"finishReason":"error"', "".join(frames))

    def test_generic_failure_emits_sse_error_frame(self):
        self._fail_assemble(RuntimeError("kaboom"))
        req = _make_request("user_pack_fail_generic")
        frames = self._drain(req)
        error_frames = [f for f in frames if '"type":"error"' in f.replace(" ", "")]
        self.assertTrue(error_frames, f"expected an SSE error frame, got: {frames!r}")
        self.assertIn("kaboom", error_frames[0])

    def test_dream_binding_failure_emits_safe_structured_error(self):
        from services.story_workspace.dream_thread_binding import (
            DreamThreadBindingConflict,
        )

        self._fail_assemble(DreamThreadBindingConflict("branched_retry_graph"))
        frames = self._drain(_make_request("user_dream_binding_fail"))
        error_frame = next(
            frame for frame in frames if '"type":"error"' in frame.replace(" ", "")
        )

        self.assertIn('"errorCode":"DREAM_THREAD_BINDING_CONFLICT"', error_frame)
        self.assertIn('"retryable":false', error_frame)
        self.assertIn("This conversation's Dream binding is unavailable.", error_frame)
        self.assertNotIn("branched_retry_graph", error_frame)
        self.assertNotIn("[DREAM_THREAD_BINDING_CONFLICT]", error_frame)

    def test_failure_resets_lifecycle_and_allows_retry(self):
        from services.claude_plugin.workspace_packer import WorkspacePackError
        self._fail_assemble(WorkspacePackError("WORKSPACE_PACK_ERROR", "boom"))
        req = _make_request("user_pack_fail_2")
        self._drain(req)

        state = self.factory._pool.get("thread_user_pack_fail_2")
        self.assertEqual(state.lifecycle, AgentRunLifecycle.IDLE)
        self.assertIsNone(state.event_bus)

        # Retry on the same session must NOT raise "already running";
        # it should run the turn again and emit another error frame.
        frames = self._drain(req)
        error_frames = [f for f in frames if '"type":"error"' in f.replace(" ", "")]
        self.assertTrue(
            error_frames,
            "retry after pack failure should emit a fresh error frame, "
            f"got: {frames!r}",
        )

    def test_unexpected_execution_failure_closes_the_stream_once(self):
        async def exercise():
            factory = ClaudeAgentThreadFactory()
            state = factory._pool.get_or_create("thread_unexpected_failure")
            state.mark_running()
            state.current_turn_id = "turn-unexpected"
            bus = create_event_bus(state.session_id, state.current_turn_id)
            state.event_bus = bus
            lock = factory._pool.get_lock(state.session_id)
            await lock.acquire()

            async def _execute(_execution):
                raise RuntimeError("unexpected persistence failure")

            async def _assemble(_request, *, state, bus, runner):
                del state, bus, runner
                return object()

            state.runner = unittest.mock.Mock()
            factory._service.assemble_context = _assemble
            factory._service.execute_session = _execute
            token = await bus.subscribe()
            task = asyncio.create_task(
                factory._run_turn_task(
                    _make_request(
                        "unexpected_failure",
                        thread_id="thread_unexpected_failure",
                    ),
                    state,
                    bus,
                    lock,
                )
            )
            events = [event async for event in bus.read(token)]
            await task
            await bus.unsubscribe(token)
            return events, state

        events, state = _run(exercise())
        self.assertEqual(
            [event.type for event in events],
            ["error", "finish"],
        )
        self.assertEqual(events[1].data["finishReason"], "error")
        self.assertEqual(state.lifecycle, AgentRunLifecycle.IDLE)
        self.assertIsNone(state.event_bus)


if __name__ == "__main__":
    unittest.main()
