from __future__ import annotations

import asyncio
from types import SimpleNamespace
import unittest

from agent_stream_events import NormalizedAgentEvent
from claude_agent.chat_stream_adapter import ChatStreamAdapter
from claude_agent.event_bus import InMemoryEventBus
from services.story_workspace.dream_lifecycle_observer import (
    DreamLifecycleCoordinator,
    DreamLifecycleObserver,
    DreamTurnIdentity,
    DreamTurnLease,
    DreamWorkflowActivityProjectionSink,
    NormalizedAgentTurnClassifier,
    NormalizedTurnOutcome,
    drain_chat_agent_turn,
)


RUN_ID = "run_" + "a" * 32
THREAD_ID = "thread-observer"
TURN_ID = "turn-observer"
ACTOR_ID = "7"


def _event(event_type: str, **data: object) -> NormalizedAgentEvent:
    return NormalizedAgentEvent.create(event_type, data)


class _Factory:
    def __init__(self, events: list[NormalizedAgentEvent]) -> None:
        self.events = events

    async def run_streaming(self, _request: object):
        for event in self.events:
            yield ChatStreamAdapter.encode(event)


class _RecordingSink:
    def __init__(self, *, fail: bool = False, hang: bool = False) -> None:
        self.fail = fail
        self.hang = hang
        self.items = []
        self.entered = asyncio.Event()

    async def project(self, observation, lease) -> None:
        self.entered.set()
        if self.hang:
            await asyncio.Event().wait()
        if self.fail:
            raise RuntimeError("sink failed")
        if lease.active:
            self.items.append(observation)

    async def reconcile(self, run_id, actor_id, lease) -> None:
        self.entered.set()
        if self.hang:
            await asyncio.Event().wait()
        if self.fail:
            raise RuntimeError("sink failed")
        if lease.active:
            self.items.append((run_id, actor_id, "reconcile"))


class _CancellationSwallowingSink:
    def __init__(self) -> None:
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.lease_active_after_cancel: bool | None = None

    async def project(self, _observation, lease) -> None:
        self.entered.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.lease_active_after_cancel = lease.active
            await self.release.wait()

    async def reconcile(self, _run_id, _actor_id, lease) -> None:
        await self.project(None, lease)


class _FailOnceReplayBus(InMemoryEventBus):
    """Replay-capable production adapter seam with one transient read error."""

    def __init__(self) -> None:
        super().__init__()
        self.subscribe_count = 0
        self.read_count = 0
        self.restarted = asyncio.Event()

    async def subscribe(self):
        token = await super().subscribe()
        self.subscribe_count += 1
        if self.subscribe_count == 2:
            self.restarted.set()
        return token

    async def read(self, token):
        self.read_count += 1
        fail_this_read = self.read_count == 1
        async for event in super().read(token):
            yield event
            if fail_this_read:
                raise RuntimeError("transient reader failure")


class _FailEveryReplayBus(_FailOnceReplayBus):
    async def read(self, token):
        self.read_count += 1
        async for event in InMemoryEventBus.read(self, token):
            yield event
            raise RuntimeError("persistent reader failure")


class NormalizedAgentTurnClassifierTest(unittest.IsolatedAsyncioTestCase):
    async def test_finish_is_the_only_terminal(self) -> None:
        classifier = NormalizedAgentTurnClassifier()
        self.assertIsNone(classifier.observe(_event("message-final", text="done")))
        self.assertEqual(
            classifier.observe(_event("finish", finishReason="stop")),
            NormalizedTurnOutcome.COMPLETED,
        )
        self.assertIsNone(classifier.observe(_event("finish", finishReason="error")))
        self.assertEqual(classifier.result().outcome, NormalizedTurnOutcome.COMPLETED)

    async def test_cancel_after_message_final_is_not_misclassified_completed(self) -> None:
        classifier = NormalizedAgentTurnClassifier()
        self.assertIsNone(classifier.observe(_event("message-final", text="done")))
        self.assertEqual(
            classifier.observe(
                _event("finish", finishReason="stop", cancelled=True)
            ),
            NormalizedTurnOutcome.CANCELLED,
        )

        observer = DreamLifecycleObserver(
            DreamTurnIdentity(
                run_id=RUN_ID,
                thread_id=THREAD_ID,
                turn_id=TURN_ID,
                actor_id=ACTOR_ID,
                generation=1,
            )
        )
        self.assertIsNone(
            observer.observe(_event("message-final", text="done"), sequence=0)
        )
        terminal = observer.observe(
            _event("finish", finishReason="stop", cancelled=True),
            sequence=1,
        )
        self.assertIsNotNone(terminal)
        self.assertEqual(terminal.terminal_outcome, "cancelled")

    async def test_drain_classifies_failure_cancel_and_incomplete(self) -> None:
        failed = await drain_chat_agent_turn(
            _Factory([_event("error"), _event("finish", finishReason="error")]),
            object(),
        )
        cancelled = await drain_chat_agent_turn(
            _Factory([_event("text-delta", delta="x"), _event("finish", finishReason="stop")]),
            object(),
        )
        incomplete = await drain_chat_agent_turn(
            _Factory([_event("message-final", text="x")]),
            object(),
        )
        self.assertEqual(failed.outcome, NormalizedTurnOutcome.FAILED)
        self.assertEqual(cancelled.outcome, NormalizedTurnOutcome.CANCELLED)
        self.assertEqual(incomplete.outcome, NormalizedTurnOutcome.INCOMPLETE)

    async def test_drain_rejects_non_chat_frame_values(self) -> None:
        class BrokenFactory:
            async def run_streaming(self, _request):
                yield _event("finish", finishReason="stop")

        with self.assertRaisesRegex(TypeError, "Chat SSE frame"):
            await drain_chat_agent_turn(BrokenFactory(), object())


class DreamLifecycleObserverTest(unittest.TestCase):
    def setUp(self) -> None:
        self.identity = DreamTurnIdentity(
            run_id=RUN_ID,
            thread_id=THREAD_ID,
            turn_id=TURN_ID,
            actor_id=ACTOR_ID,
            generation=1,
        )

    def test_duplicate_gap_and_late_events_are_bounded(self) -> None:
        observer = DreamLifecycleObserver(self.identity)
        waiting = observer.observe(_event("tool-approval-request"), sequence=0)
        self.assertEqual(waiting.kind, "waiting_confirmation_hint")
        self.assertIsNone(observer.observe(_event("tool-approval-request"), sequence=0))
        reconcile = observer.observe(_event("text-delta", delta="private"), sequence=2)
        self.assertEqual(reconcile.kind, "reconcile_requested")
        terminal = observer.observe(_event("finish", finishReason="error"), sequence=3)
        self.assertEqual(terminal.terminal_outcome, "failed")
        self.assertIsNone(observer.observe(_event("finish", finishReason="stop"), sequence=4))
        self.assertEqual(observer.diagnostics.duplicates, 1)
        self.assertEqual(observer.diagnostics.sequence_gaps, 1)
        self.assertEqual(observer.diagnostics.late_events, 1)

    def test_raw_event_content_never_enters_projection(self) -> None:
        observer = DreamLifecycleObserver(self.identity)
        observation = observer.observe(
            _event(
                "tool-input-available",
                toolCallId="secret-id",
                toolName="dangerous-tool",
                input={"token": "secret"},
            ),
            sequence=0,
        )
        rendered = repr(observation)
        self.assertNotIn("secret-id", rendered)
        self.assertNotIn("dangerous-tool", rendered)
        self.assertNotIn("token", rendered)

    def test_content_tool_progress_is_correlated_without_raw_tool_identity(self) -> None:
        observer = DreamLifecycleObserver(self.identity)
        started = observer.observe(
            _event(
                "tool-input-available",
                toolCallId="content-secret-call",
                toolName="mcp__story_workspace__write_dream_run",
                input={"private": "must-not-project"},
            ),
            sequence=0,
        )
        settled = observer.observe(
            _event(
                "tool-output-available",
                toolCallId="content-secret-call",
                output={"private": "must-not-project"},
                isError=False,
            ),
            sequence=1,
        )

        self.assertEqual(started.operation_scope, "content_generation")
        self.assertEqual(started.operation_state, "started")
        self.assertEqual(settled.operation_scope, "content_generation")
        self.assertEqual(settled.operation_state, "succeeded")
        self.assertEqual(started.operation_id, settled.operation_id)
        self.assertEqual(len(started.operation_id), 64)
        self.assertNotIn("content-secret-call", repr((started, settled)))
        self.assertNotIn("must-not-project", repr((started, settled)))

    def test_subagent_and_tool_failure_progress_remain_content_free(self) -> None:
        observer = DreamLifecycleObserver(self.identity)
        started = observer.observe(
            _event(
                "tool-input-start",
                toolCallId="subagent-call",
                toolName="Agent",
            ),
            sequence=0,
        )
        failed = observer.observe(
            _event(
                "tool-output-available",
                toolCallId="subagent-call",
                output="private subagent transcript",
                isError=True,
            ),
            sequence=1,
        )

        self.assertEqual(started.operation_scope, "subagent")
        self.assertEqual(started.operation_state, "started")
        self.assertEqual(failed.operation_scope, "subagent")
        self.assertEqual(failed.operation_state, "failed")
        self.assertEqual(started.operation_id, failed.operation_id)
        self.assertNotIn("private subagent transcript", repr(failed))


class DreamLifecycleCoordinatorTest(unittest.IsolatedAsyncioTestCase):
    def _context(self):
        return SimpleNamespace(workflow_run_id=RUN_ID, thread_id=THREAD_ID)

    async def test_default_sink_projects_one_terminal_and_releases_every_task(self) -> None:
        coordinator = DreamLifecycleCoordinator(queue_size=4)
        bus = InMemoryEventBus()
        await coordinator.attach_before_session_execution(
            context=self._context(),
            actor_id=ACTOR_ID,
            turn_id=TURN_ID,
            bus=bus,
        )
        await bus.publish(_event("message-final", text="must-not-project"))
        await bus.publish(_event("finish", finishReason="stop"))
        await bus.publish(_event("finish", finishReason="error"))
        await bus.publish(None)

        await coordinator.close_turn(THREAD_ID, TURN_ID, reason="test_terminal")
        projection = coordinator.projection_snapshot()
        self.assertEqual(len(projection), 1)
        self.assertEqual(projection[0].terminal_outcome, "completed")
        self.assertNotIn("must-not-project", repr(projection[0]))
        diagnostics = coordinator.diagnostics()
        self.assertEqual(diagnostics["active_handles"], 0)
        self.assertEqual(diagnostics["active_tasks"], 0)
        self.assertEqual(diagnostics["detached_tasks"], 0)
        self.assertEqual(diagnostics["live_detached_tasks"], 0)
        # The shared EventBus now rejects every post-terminal frame atomically.
        self.assertEqual(diagnostics["late_events"], 0)

    async def test_projection_orders_generation_before_same_turn_sequence(self) -> None:
        sink = DreamWorkflowActivityProjectionSink(max_entries=4)
        old_identity = DreamTurnIdentity(
            run_id=RUN_ID,
            thread_id=THREAD_ID,
            turn_id="turn-old",
            actor_id=ACTOR_ID,
            generation=1,
        )
        new_identity = DreamTurnIdentity(
            run_id=RUN_ID,
            thread_id=THREAD_ID,
            turn_id="turn-new",
            actor_id=ACTOR_ID,
            generation=2,
        )
        old_started = DreamLifecycleObserver(old_identity).observe(
            _event("tool-input-start", toolName="old"),
            sequence=0,
        )
        new_observer = DreamLifecycleObserver(new_identity)
        new_started = new_observer.observe(
            _event("tool-input-start", toolCallId="new", toolName="new"),
            sequence=0,
        )
        new_settled = new_observer.observe(
            _event("tool-output-available", toolCallId="new", isError=False),
            sequence=1,
        )
        assert old_started is not None
        assert new_started is not None
        assert new_settled is not None

        await sink.project(new_started, DreamTurnLease(new_identity))
        await sink.project(old_started, DreamTurnLease(old_identity))
        self.assertEqual(sink.snapshot()[0].generation, 2)
        self.assertEqual(sink.snapshot()[0].turn_id, "turn-new")
        await sink.project(new_settled, DreamTurnLease(new_identity))
        await sink.project(new_started, DreamTurnLease(new_identity))
        await sink.reconcile(RUN_ID, ACTOR_ID, DreamTurnLease(old_identity))
        projection = sink.snapshot()[0]
        self.assertEqual(projection.sequence, 1)
        self.assertEqual(projection.operation_state, "succeeded")
        self.assertFalse(projection.needs_reconcile)
        self.assertEqual(projection.actor_id, ACTOR_ID)

        other_actor_identity = DreamTurnIdentity(
            run_id=RUN_ID,
            thread_id=THREAD_ID,
            turn_id="turn-other-actor",
            actor_id="8",
            generation=3,
        )
        other_actor_started = DreamLifecycleObserver(other_actor_identity).observe(
            _event("tool-input-start"),
            sequence=0,
        )
        assert other_actor_started is not None
        await sink.project(
            other_actor_started,
            DreamTurnLease(other_actor_identity),
        )
        self.assertEqual(
            {(item.actor_id, item.generation) for item in sink.snapshot()},
            {(ACTOR_ID, 2), ("8", 3)},
        )

    async def test_reader_failure_reconciles_then_replays_once_without_duplicates(
        self,
    ) -> None:
        sink = _RecordingSink()
        coordinator = DreamLifecycleCoordinator(
            sink,
            queue_size=8,
            graceful_sink_timeout_s=0.1,
        )
        bus = _FailOnceReplayBus()
        await coordinator.attach_before_session_execution(
            context=self._context(),
            actor_id=ACTOR_ID,
            turn_id=TURN_ID,
            bus=bus,
        )
        await bus.publish(
            _event(
                "tool-input-start",
                toolCallId="content-call",
                toolName="mcp__story_workspace__write_dream_run",
            )
        )
        await asyncio.wait_for(bus.restarted.wait(), timeout=0.2)
        await bus.publish(
            _event(
                "tool-output-available",
                toolCallId="content-call",
                isError=False,
            )
        )
        await bus.publish(_event("message-final", text="private"))
        await bus.publish_terminal(_event("finish", finishReason="stop"))

        await coordinator.close_turn(THREAD_ID, TURN_ID, reason="reader_replay")
        projected = [item for item in sink.items if not isinstance(item, tuple)]
        self.assertEqual(
            [item.kind for item in projected],
            [
                "activity_started_hint",
                "activity_settled_hint",
                "turn_settled_hint",
            ],
        )
        self.assertEqual(len({item.event_id for item in projected}), 3)
        self.assertIn((RUN_ID, ACTOR_ID, "reconcile"), sink.items)
        diagnostics = coordinator.diagnostics()
        self.assertEqual(diagnostics["reader_errors"], 1)
        self.assertEqual(diagnostics["reader_restarts"], 1)
        self.assertGreaterEqual(diagnostics["duplicates"], 1)
        self.assertEqual(diagnostics["active_tasks"], 0)

    async def test_reader_failure_clears_stale_default_projection(self) -> None:
        coordinator = DreamLifecycleCoordinator(
            queue_size=4,
            graceful_sink_timeout_s=0.1,
        )
        bus = _FailEveryReplayBus()
        handle = await coordinator.attach_before_session_execution(
            context=self._context(),
            actor_id=ACTOR_ID,
            turn_id=TURN_ID,
            bus=bus,
        )
        await bus.publish(
            _event(
                "tool-input-start",
                toolCallId="content-call",
                toolName="mcp__story_workspace__write_dream_run",
            )
        )
        assert handle.cleanup_done is not None
        await asyncio.wait_for(handle.cleanup_done.wait(), timeout=0.3)

        projection = coordinator.projection_snapshot()
        self.assertEqual(len(projection), 1)
        self.assertEqual(projection[0].activity, "reconcile_requested")
        self.assertTrue(projection[0].needs_reconcile)
        self.assertIsNone(projection[0].operation_scope)
        self.assertIsNone(projection[0].operation_state)
        diagnostics = coordinator.diagnostics()
        self.assertEqual(diagnostics["reader_errors"], 2)
        self.assertEqual(diagnostics["reader_restarts"], 1)
        self.assertGreaterEqual(diagnostics["duplicates"], 1)

    async def test_hung_sink_and_full_queue_have_bounded_cleanup(self) -> None:
        sink = _RecordingSink(hang=True)
        coordinator = DreamLifecycleCoordinator(
            sink,
            queue_size=1,
            graceful_sink_timeout_s=0.02,
        )
        bus = InMemoryEventBus()
        await coordinator.attach_before_session_execution(
            context=self._context(),
            actor_id=ACTOR_ID,
            turn_id=TURN_ID,
            bus=bus,
        )
        await bus.publish(_event("tool-input-start"))
        await asyncio.wait_for(sink.entered.wait(), timeout=0.2)
        await bus.publish(_event("tool-input-available"))
        await bus.publish(_event("message-final"))
        await bus.publish(_event("finish", finishReason="stop"))
        await bus.publish(None)

        await asyncio.wait_for(
            coordinator.close_turn(THREAD_ID, TURN_ID, reason="hung_sink"),
            timeout=0.3,
        )
        diagnostics = coordinator.diagnostics()
        self.assertEqual(diagnostics["active_handles"], 0)
        self.assertEqual(diagnostics["active_tasks"], 0)
        self.assertGreaterEqual(diagnostics["queue_overflow"], 1)

    async def test_sink_swallowing_cancel_is_detached_after_lease_revocation(
        self,
    ) -> None:
        sink = _CancellationSwallowingSink()
        coordinator = DreamLifecycleCoordinator(
            sink,
            graceful_sink_timeout_s=0.01,
        )
        bus = InMemoryEventBus()
        await coordinator.attach_before_session_execution(
            context=self._context(),
            actor_id=ACTOR_ID,
            turn_id=TURN_ID,
            bus=bus,
        )
        await bus.publish(_event("tool-input-start"))
        await asyncio.wait_for(sink.entered.wait(), timeout=0.2)

        await asyncio.wait_for(
            coordinator.close_turn(THREAD_ID, TURN_ID, reason="cancel_swallowed"),
            timeout=0.2,
        )
        diagnostics = coordinator.diagnostics()
        self.assertFalse(sink.lease_active_after_cancel)
        self.assertGreaterEqual(diagnostics["detached_tasks"], 1)
        self.assertGreaterEqual(diagnostics["live_detached_tasks"], 1)
        self.assertEqual(diagnostics["active_handles"], 0)

        sink.release.set()
        for _ in range(20):
            if coordinator.diagnostics()["live_detached_tasks"] == 0:
                break
            await asyncio.sleep(0)
        self.assertEqual(coordinator.diagnostics()["live_detached_tasks"], 0)

    async def test_raising_sink_does_not_change_chat_bus_events(self) -> None:
        sink = _RecordingSink(fail=True)
        coordinator = DreamLifecycleCoordinator(sink, graceful_sink_timeout_s=0.05)
        bus = InMemoryEventBus()
        await coordinator.attach_before_session_execution(
            context=self._context(),
            actor_id=ACTOR_ID,
            turn_id=TURN_ID,
            bus=bus,
        )
        chat_token = await bus.subscribe()
        expected = [
            _event("tool-input-start", toolName="x"),
            _event("message-final", text="visible-to-chat"),
            _event("finish", finishReason="stop"),
        ]
        for event in expected:
            await bus.publish(event)
        await bus.publish(None)
        observed = [event async for event in bus.read(chat_token)]
        await bus.unsubscribe(chat_token)
        await coordinator.close_turn(THREAD_ID, TURN_ID, reason="raising_sink")

        self.assertEqual(observed, expected)
        self.assertGreaterEqual(coordinator.diagnostics()["sink_errors"], 1)
        self.assertEqual(coordinator.diagnostics()["active_tasks"], 0)

    async def test_sentinel_without_finish_requests_reconcile_not_success(self) -> None:
        coordinator = DreamLifecycleCoordinator(queue_size=2)
        bus = InMemoryEventBus()
        await coordinator.attach_before_session_execution(
            context=self._context(),
            actor_id=ACTOR_ID,
            turn_id=TURN_ID,
            bus=bus,
        )
        await bus.publish(_event("message-final"))
        await bus.publish(None)
        await coordinator.close_turn(THREAD_ID, TURN_ID, reason="missing_finish")
        projection = coordinator.projection_snapshot()
        self.assertEqual(len(projection), 1)
        self.assertIsNone(projection[0].terminal_outcome)
        self.assertTrue(projection[0].needs_reconcile)
        self.assertEqual(coordinator.diagnostics()["missing_terminal"], 1)


if __name__ == "__main__":
    unittest.main()
