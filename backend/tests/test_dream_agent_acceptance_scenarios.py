"""Backend-owned DreamAgent release-acceptance scenarios.

These tests deliberately exercise the canonical Chat confirmation route,
ClaudeAgentService, shared EventBus, and Dream lifecycle Observer production
objects.  They never call a real model and they keep every scenario ID in the
test name so the S01-S14 release matrix is machine-auditable.
"""

from __future__ import annotations

import asyncio
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tests._sdk_stubs  # noqa: F401 - prevent any real SDK/provider import

import claude_agent.service as service_module
from claude_agent.event_bus import BusProxyQueue, InMemoryEventBus
from claude_agent.service import ClaudeAgentRunRequest, ClaudeAgentService, _TurnContext
from claude_agent.stream_events import NormalizedAgentEvent
from claude_agent.thread_factory import ClaudeAgentThreadFactory
from claude_agent.thread_pool import AgentRunState
from claude_agent.tool_confirmation_store import (
    ToolConfirmationInvalidDecision,
    ToolConfirmationResult,
    ToolConfirmationStore,
)
from fastapi import HTTPException
from libs.claude_agent_kit.types import AgentRunResult
from services.story_workspace.dream_lifecycle_observer import (
    DreamLifecycleCoordinator,
    DreamLifecycleObserver,
    DreamTurnIdentity,
    DreamTurnLease,
    DreamWorkflowActivityProjectionSink,
    NormalizedAgentTurnClassifier,
    NormalizedTurnOutcome,
)


RUN_ID = "run_" + "a" * 32
THREAD_ID = "thread-dream-acceptance"
TURN_ID = "turn-dream-acceptance"
ACTOR_ID = "7"


def _event(event_type: str, **data: object) -> NormalizedAgentEvent:
    return NormalizedAgentEvent.create(event_type, data)


async def _read_all(
    bus: InMemoryEventBus,
) -> list[NormalizedAgentEvent]:
    token = await bus.subscribe()
    return [event async for event in bus.read(token)]


class _FailingBusinessSink:
    """A hostile business adapter used to prove Observer failure isolation."""

    def __init__(self) -> None:
        self.entered = asyncio.Event()

    async def project(self, observation, lease) -> None:
        del observation, lease
        self.entered.set()
        raise RuntimeError("business projection unavailable")

    async def reconcile(self, run_id, actor_id, lease) -> None:
        del run_id, actor_id, lease
        self.entered.set()
        raise RuntimeError("business reconciliation unavailable")


class _TraceBus(InMemoryEventBus):
    """Real in-memory EventBus with a test-only ordering trace."""

    def __init__(self, trace: list[str]) -> None:
        super().__init__()
        self._trace = trace

    async def publish(self, event: NormalizedAgentEvent | None) -> None:
        if event is not None and event.type != "finish":
            self._trace.append(f"event:{event.type}")
        await super().publish(event)

    async def publish_terminal(self, event: NormalizedAgentEvent) -> None:
        self._trace.append(
            "event:finish:"
            f"{event.data.get('finishReason')}:"
            f"{event.data.get('cancelled') is True}"
        )
        await super().publish_terminal(event)


class _ResultRunner:
    def __init__(self, result: AgentRunResult | BaseException) -> None:
        self._result = result

    async def run_streaming(self, _options, _callbacks) -> AgentRunResult:
        if isinstance(self._result, BaseException):
            raise self._result
        return self._result


class DreamAgentS04ConfirmationAcceptance(unittest.IsolatedAsyncioTestCase):
    async def test_s04_canonical_route_enforces_owner_active_actor_and_qn_answers(
        self,
    ) -> None:
        """One owned Chat route resolves AskUser and replays one settlement."""

        import routers.claude_agent as route_module

        store = ToolConfirmationStore(thread_id=THREAD_ID, turn_id=TURN_ID)
        factory = ClaudeAgentThreadFactory()
        try:
            policy = store.policy_from_payload(
                {
                    "tool_call_id": "call-ask-user",
                    "tool_name": "AskUserQuestion",
                    "input": {
                        "questions": [
                            {
                                "question": "Choose a draft",
                                "type": "radio",
                                "required": True,
                                "options": ["A", "B"],
                            },
                            {
                                "question": "Improve which areas",
                                "type": "select",
                                "multiSelect": True,
                                "required": True,
                                "options": ["tone", "pace", "dialogue"],
                            },
                        ]
                    },
                }
            )
            self.assertEqual(policy.kind, "ask_user")
            store.register_pending(policy)
            runner_waiter = asyncio.create_task(store.await_pending("call-ask-user"))

            state = factory._pool.get_or_create(THREAD_ID)
            state.current_turn_id = TURN_ID
            state.current_user_id = ACTOR_ID
            state.turn_context = _TurnContext(
                queue=asyncio.Queue(),
                confirmation_store=store,
            )
            state.mark_running()
            body = route_module.ToolConfirmRequestBody(
                thread_id=THREAD_ID,
                tool_call_id="call-ask-user",
                approved=True,
                answers={"q0": "B", "q1": ["tone", "dialogue"]},
            )

            with (
                mock.patch.object(
                    route_module,
                    "claude_agent_thread_factory",
                    factory,
                ),
                mock.patch.object(
                    route_module.database,
                    "get_chat_thread",
                    return_value=None,
                ),
            ):
                with self.assertRaises(HTTPException) as foreign:
                    await route_module.claude_agent_tool_confirm(
                        body,
                        current_user={"user_id": int(ACTOR_ID)},
                    )
            self.assertEqual(foreign.exception.status_code, 404)
            self.assertTrue(store.has_pending("call-ask-user"))

            # Even if the durable owner lookup succeeds, an actor drift in the
            # active runtime must fail closed before touching the Future.
            state.current_user_id = "8"
            with (
                mock.patch.object(
                    route_module,
                    "claude_agent_thread_factory",
                    factory,
                ),
                mock.patch.object(
                    route_module.database,
                    "get_chat_thread",
                    return_value={"id": THREAD_ID, "user_id": int(ACTOR_ID)},
                ),
            ):
                with self.assertRaises(HTTPException) as stale_actor:
                    await route_module.claude_agent_tool_confirm(
                        body,
                        current_user={"user_id": int(ACTOR_ID)},
                    )
            self.assertEqual(stale_actor.exception.status_code, 409)
            self.assertTrue(store.has_pending("call-ask-user"))

            state.current_user_id = ACTOR_ID
            with (
                mock.patch.object(
                    route_module,
                    "claude_agent_thread_factory",
                    factory,
                ),
                mock.patch.object(
                    route_module.database,
                    "get_chat_thread",
                    return_value={"id": THREAD_ID, "user_id": int(ACTOR_ID)},
                ),
            ):
                first = await route_module.claude_agent_tool_confirm(
                    body,
                    current_user={"user_id": int(ACTOR_ID)},
                )
                replay = await route_module.claude_agent_tool_confirm(
                    body,
                    current_user={"user_id": int(ACTOR_ID)},
                )

            self.assertEqual(first, {"ok": True, "approved": True})
            self.assertEqual(replay, first)
            self.assertEqual(
                (await runner_waiter).answers,
                {
                    "Choose a draft": "B",
                    "Improve which areas": ["tone", "dialogue"],
                },
            )
            settled = await store.resolve_exact(
                thread_id=THREAD_ID,
                turn_id=TURN_ID,
                tool_call_id="call-ask-user",
                result=ToolConfirmationResult(
                    True,
                    answers={"q0": "B", "q1": ["tone", "dialogue"]},
                ),
            )
            self.assertTrue(settled.replayed)
        finally:
            store.cancel_all()
            await factory.aclose()

    async def test_s04_approval_reject_network_and_reject_only_are_server_derived(
        self,
    ) -> None:
        """SDK callback policy, not the browser decision, controls approval."""

        stores: list[ToolConfirmationStore] = []

        def make_store(suffix: str) -> ToolConfirmationStore:
            store = ToolConfirmationStore(
                thread_id=f"{THREAD_ID}-{suffix}",
                turn_id=f"{TURN_ID}-{suffix}",
            )
            stores.append(store)
            return store

        try:
            approval = make_store("approval")
            approval_policy = approval.policy_from_payload(
                {
                    "tool_call_id": "call-bash",
                    "tool_name": "Bash",
                    "input": {"command": "pwd"},
                }
            )
            approval.register_pending(approval_policy)
            rejected = await approval.resolve_exact(
                thread_id=approval.thread_id,
                turn_id=approval.turn_id,
                tool_call_id="call-bash",
                result=ToolConfirmationResult(False, reason="user declined"),
            )
            self.assertFalse(rejected.result.approved)

            network = make_store("network")
            network_policy = network.policy_from_payload(
                {
                    "tool_call_id": "call-network",
                    "tool_name": "SandboxNetworkAccess",
                    "input": {"host": "api.example.com"},
                    "confirmationKind": "sandbox_network",
                    "networkRequest": {
                        "host": "API.EXAMPLE.COM",
                        "policyMode": "allowlist",
                        "matchedAllowedDomain": "*.example.com",
                    },
                }
            )
            self.assertEqual(network_policy.kind, "sandbox_network")
            self.assertEqual(network_policy.network_host, "api.example.com")
            network.register_pending(network_policy)
            allowed = await network.resolve_exact(
                thread_id=network.thread_id,
                turn_id=network.turn_id,
                tool_call_id="call-network",
                result=ToolConfirmationResult(True),
            )
            self.assertTrue(allowed.result.approved)

            denied_network = make_store("network-deny")
            denied_policy = denied_network.policy_from_payload(
                {
                    "tool_call_id": "call-network-deny",
                    "tool_name": "SandboxNetworkAccess",
                    "input": {"host": "blocked.example.com"},
                    "confirmationKind": "sandbox_network",
                    "networkRequest": {
                        "host": "blocked.example.com",
                        "policyMode": "deny",
                    },
                }
            )
            denied_network.register_pending(denied_policy)
            with self.assertRaises(ToolConfirmationInvalidDecision):
                await denied_network.resolve_exact(
                    thread_id=denied_network.thread_id,
                    turn_id=denied_network.turn_id,
                    tool_call_id="call-network-deny",
                    result=ToolConfirmationResult(True),
                )
            self.assertTrue(denied_network.has_pending("call-network-deny"))
            await denied_network.resolve_exact(
                thread_id=denied_network.thread_id,
                turn_id=denied_network.turn_id,
                tool_call_id="call-network-deny",
                result=ToolConfirmationResult(False, reason="policy denied"),
            )

            reject_only = make_store("reject-only")
            reject_policy = reject_only.policy_from_payload(
                {
                    "tool_call_id": "call-malformed-ask",
                    "tool_name": "AskUserQuestion",
                    "input": {"questions": []},
                }
            )
            self.assertEqual(reject_policy.kind, "reject_only")
            reject_only.register_pending(reject_policy)
            with self.assertRaises(ToolConfirmationInvalidDecision):
                await reject_only.resolve_exact(
                    thread_id=reject_only.thread_id,
                    turn_id=reject_only.turn_id,
                    tool_call_id="call-malformed-ask",
                    result=ToolConfirmationResult(True),
                )
            final_rejection = await reject_only.resolve_exact(
                thread_id=reject_only.thread_id,
                turn_id=reject_only.turn_id,
                tool_call_id="call-malformed-ask",
                result=ToolConfirmationResult(False, reason="unrenderable"),
            )
            self.assertFalse(final_rejection.result.approved)
        finally:
            for store in stores:
                store.cancel_all()


class DreamAgentS11ObserverOffPathAcceptance(unittest.IsolatedAsyncioTestCase):
    async def test_s11_observer_projects_safe_business_scopes_to_dream_files(
        self,
    ) -> None:
        """Tool/subagent/content/workflow progress is correlated, not copied."""

        from services.deck.story_workflow_gateway import (
            StoryWorkflowApplicationGateway,
        )
        from story_workspace.contracts import (
            StoryWorkspaceDreamFilesResponse,
            StoryWorkspaceDreamSourceResponse,
            StoryWorkspaceDreamStage,
        )

        identity = DreamTurnIdentity(
            run_id=RUN_ID,
            thread_id=THREAD_ID,
            turn_id=TURN_ID,
            actor_id=ACTOR_ID,
            generation=1,
        )
        observer = DreamLifecycleObserver(identity)
        inputs = (
            _event(
                "tool-input-available",
                toolCallId="raw-tool-id",
                toolName="Bash",
                input={"token": "must-not-project"},
            ),
            _event(
                "tool-output-available",
                toolCallId="raw-tool-id",
                output={"secret": "must-not-project"},
                isError=False,
            ),
            _event(
                "tool-input-available",
                toolCallId="raw-subagent-id",
                toolName="Agent",
                input={"prompt": "private child prompt"},
            ),
            _event(
                "tool-input-available",
                toolCallId="raw-content-id",
                toolName="mcp__story_workspace__write_dream_run",
                input={"content": "private draft"},
            ),
            _event(
                "tool-approval-request",
                toolCallId="raw-workflow-id",
                toolName="mcp__story_workspace__continue_episode_action",
                input={"path": "/private/workspace"},
            ),
        )
        observations = [
            observer.observe(event, sequence=sequence)
            for sequence, event in enumerate(inputs)
        ]
        self.assertTrue(all(item is not None for item in observations))
        typed = [item for item in observations if item is not None]
        self.assertEqual(
            [(item.operation_scope, item.operation_state) for item in typed],
            [
                ("tool", "started"),
                ("tool", "succeeded"),
                ("subagent", "started"),
                ("content_generation", "started"),
                ("workflow_operation", "waiting_confirmation"),
            ],
        )
        self.assertEqual(typed[0].operation_id, typed[1].operation_id)
        for item in typed:
            if item.operation_id is not None:
                self.assertRegex(item.operation_id, r"^[0-9a-f]{64}$")
            rendered = repr(item)
            for private_value in (
                "raw-tool-id",
                "raw-subagent-id",
                "raw-content-id",
                "raw-workflow-id",
                "must-not-project",
                "private child prompt",
                "private draft",
                "/private/workspace",
            ):
                self.assertNotIn(private_value, rendered)

        response = StoryWorkspaceDreamFilesResponse(
            story_workspace_run_id=RUN_ID,
            thread_id=THREAD_ID,
            source=StoryWorkspaceDreamSourceResponse(
                deck_plugin_binding_id="binding-1",
                binding_revision=1,
                deck_plugin_version="1.0.0",
                deck_runtime_snapshot_id="snapshot-1",
                runtime_plugin_lock_id="lock-1",
            ),
            required_stages=list(StoryWorkspaceDreamStage),
            run_revision=0,
            stages={},
            can_confirm=False,
        )
        sink = DreamWorkflowActivityProjectionSink(max_entries=4)
        await sink.project(typed[-1], DreamTurnLease(identity))
        gateway = StoryWorkflowApplicationGateway()
        factory = SimpleNamespace(
            dream_workflow_activity_projection=lambda: sink.snapshot()
        )
        with mock.patch.object(
            gateway,
            "_dream_agent_thread_factory",
            return_value=factory,
        ):
            projected = gateway._attach_dream_agent_activity(
                response,
                workflow_run_id=RUN_ID,
                actor_id=ACTOR_ID,
            )
        self.assertIsNotNone(projected.agent_activity)
        assert projected.agent_activity is not None
        self.assertEqual(
            projected.agent_activity.operation_scope,
            "workflow_operation",
        )
        self.assertEqual(
            projected.agent_activity.operation_state,
            "waiting_confirmation",
        )
        self.assertEqual(
            projected.agent_activity.operation_id,
            typed[-1].operation_id,
        )

    async def test_s11_sink_failure_cannot_interrupt_or_replace_the_chat_stream(
        self,
    ) -> None:
        sink = _FailingBusinessSink()
        coordinator = DreamLifecycleCoordinator(
            sink,
            queue_size=8,
            graceful_sink_timeout_s=0.05,
        )
        bus = InMemoryEventBus()
        chat_token = await bus.subscribe()
        try:
            await coordinator.attach_before_session_execution(
                context=SimpleNamespace(
                    workflow_run_id=RUN_ID,
                    thread_id=THREAD_ID,
                ),
                actor_id=ACTOR_ID,
                turn_id=TURN_ID,
                bus=bus,
            )
            await bus.publish(_event("tool-input-start"))
            await asyncio.wait_for(sink.entered.wait(), timeout=1.0)
            await bus.publish(_event("message-final", text="canonical answer"))
            await bus.publish_terminal(_event("finish", finishReason="stop"))

            chat_events = [event async for event in bus.read(chat_token)]
            self.assertEqual(
                [event.type for event in chat_events],
                ["tool-input-start", "message-final", "finish"],
            )
            self.assertEqual(chat_events[-1].data["finishReason"], "stop")
            await coordinator.close_turn(
                THREAD_ID,
                TURN_ID,
                reason="s11_acceptance",
            )
            diagnostics = coordinator.diagnostics()
            self.assertGreaterEqual(diagnostics["sink_errors"], 1)
            self.assertEqual(diagnostics["active_handles"], 0)
            self.assertEqual(diagnostics["active_tasks"], 0)
            self.assertEqual(diagnostics["live_detached_tasks"], 0)
        finally:
            await coordinator.aclose()

    async def test_s11_projection_is_bounded_process_local_and_trusted_identity_only(
        self,
    ) -> None:
        sink = DreamWorkflowActivityProjectionSink(max_entries=1)

        first_identity = DreamTurnIdentity(
            run_id=RUN_ID,
            thread_id=f"{THREAD_ID}-one",
            turn_id=f"{TURN_ID}-one",
            actor_id=ACTOR_ID,
            generation=1,
        )
        first = DreamLifecycleObserver(first_identity).observe(
            _event("tool-input-start"),
            sequence=0,
        )
        self.assertIsNotNone(first)
        assert first is not None

        wrong_identity = DreamTurnIdentity(
            run_id=RUN_ID,
            thread_id=first_identity.thread_id,
            turn_id=first_identity.turn_id,
            actor_id="8",
            generation=2,
        )
        await sink.project(first, DreamTurnLease(wrong_identity))
        self.assertEqual(sink.snapshot(), [])

        await sink.project(first, DreamTurnLease(first_identity))
        self.assertEqual(len(sink.snapshot()), 1)

        second_identity = DreamTurnIdentity(
            run_id="run_" + "b" * 32,
            thread_id=f"{THREAD_ID}-two",
            turn_id=f"{TURN_ID}-two",
            actor_id=ACTOR_ID,
            generation=3,
        )
        second = DreamLifecycleObserver(second_identity).observe(
            _event("tool-input-start"),
            sequence=0,
        )
        assert second is not None
        await sink.project(second, DreamTurnLease(second_identity))
        snapshot = sink.snapshot()
        self.assertEqual(len(snapshot), 1)
        self.assertEqual(snapshot[0].run_id, second_identity.run_id)
        self.assertEqual(DreamWorkflowActivityProjectionSink().snapshot(), [])

        with self.assertRaises(FrozenInstanceError):
            first.sequence = 99  # type: ignore[misc]


class DreamAgentS12ObserverReplayAcceptance(unittest.IsolatedAsyncioTestCase):
    async def test_s12_duplicate_replay_gap_order_and_late_terminal_are_idempotent(
        self,
    ) -> None:
        identity = DreamTurnIdentity(
            run_id=RUN_ID,
            thread_id=THREAD_ID,
            turn_id=TURN_ID,
            actor_id=ACTOR_ID,
            generation=1,
        )
        observer = DreamLifecycleObserver(identity)
        sink = DreamWorkflowActivityProjectionSink(max_entries=4)
        lease = DreamTurnLease(identity)

        first = observer.observe(_event("tool-input-start"), sequence=0)
        duplicate = observer.observe(_event("tool-input-start"), sequence=0)
        self.assertIsNotNone(first)
        self.assertIsNone(duplicate)
        assert first is not None
        await sink.project(first, lease)
        first_projection = sink.snapshot()[0]

        # Replaying the same trusted turn in a fresh Observer derives the same
        # event ID.  The production latest-value sink rejects the equal
        # sequence rather than applying it twice.
        replay_observer = DreamLifecycleObserver(identity)
        replay = replay_observer.observe(_event("tool-input-start"), sequence=0)
        assert replay is not None
        self.assertEqual(replay.event_id, first.event_id)
        await sink.project(replay, lease)
        self.assertIs(sink.snapshot()[0], first_projection)

        gap = observer.observe(_event("text-delta", delta="private"), sequence=2)
        self.assertIsNotNone(gap)
        assert gap is not None
        self.assertEqual(gap.kind, "reconcile_requested")
        await sink.reconcile(gap.run_id, gap.actor_id, lease)
        self.assertTrue(sink.snapshot()[0].needs_reconcile)

        self.assertIsNone(
            observer.observe(_event("tool-output-available"), sequence=1)
        )
        terminal = observer.observe(
            _event("finish", finishReason="error"),
            sequence=3,
        )
        self.assertIsNotNone(terminal)
        assert terminal is not None
        await sink.project(terminal, lease)
        self.assertEqual(sink.snapshot()[0].terminal_outcome, "failed")
        self.assertIsNone(
            observer.observe(_event("finish", finishReason="stop"), sequence=4)
        )

        diagnostics = observer.diagnostics
        self.assertEqual(diagnostics.duplicates, 1)
        self.assertEqual(diagnostics.sequence_gaps, 1)
        self.assertEqual(diagnostics.out_of_order, 1)
        self.assertEqual(diagnostics.late_events, 1)


class DreamAgentS13SingleTerminalAcceptance(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _execution(
        *,
        bus: InMemoryEventBus,
        runner: _ResultRunner,
    ) -> tuple[ClaudeAgentService, service_module._TurnExecution]:
        service = ClaudeAgentService()
        context = _TurnContext(
            queue=BusProxyQueue(bus),
            confirmation_store=ToolConfirmationStore(
                thread_id=THREAD_ID,
                turn_id=TURN_ID,
            ),
        )
        execution = service_module._TurnExecution(
            request=ClaudeAgentRunRequest(
                user_id=ACTOR_ID,
                thread_id=THREAD_ID,
                message_id="acceptance-user-message",
                message_parts=[{"type": "text", "text": "continue"}],
            ),
            state=AgentRunState(session_id=THREAD_ID),
            runner=runner,
            run_options=SimpleNamespace(),
            turn_context=context,
        )
        return service, execution

    @staticmethod
    def _persistence_patches(
        service: ClaudeAgentService,
        trace: list[str],
    ) -> tuple[mock._patch, ...]:
        return (
            mock.patch.object(
                service,
                "_persist_user_message",
                new=mock.AsyncMock(
                    side_effect=lambda *_args: trace.append("persist:user")
                ),
            ),
            mock.patch.object(
                service,
                "_persist_assistant_turn",
                new=mock.AsyncMock(
                    side_effect=lambda *_args: trace.append("persist:assistant")
                ),
            ),
            mock.patch.object(
                service,
                "_persist_partial_assistant",
                new=mock.AsyncMock(
                    side_effect=lambda *_args: trace.append("persist:partial")
                ),
            ),
            mock.patch.object(
                service,
                "_store_story_workspace_output",
                new=mock.AsyncMock(
                    side_effect=lambda *_args: trace.append("persist:story")
                ),
            ),
        )

    async def test_s13_success_persists_after_message_final_before_one_finish(
        self,
    ) -> None:
        trace: list[str] = []
        bus = _TraceBus(trace)
        service, execution = self._execution(
            bus=bus,
            runner=_ResultRunner(
                AgentRunResult(
                    full_text="done",
                    session_id="claude-session",
                    success=True,
                    usage={"input_tokens": 1, "output_tokens": 1},
                )
            ),
        )
        patches = self._persistence_patches(service, trace)
        with patches[0], patches[1], patches[2], patches[3]:
            await service.execute_session(execution)

        self.assertLess(trace.index("persist:user"), trace.index("event:message-final"))
        self.assertLess(
            trace.index("event:message-final"),
            trace.index("persist:assistant"),
        )
        self.assertLess(
            trace.index("persist:assistant"),
            trace.index("persist:story"),
        )
        self.assertLess(
            trace.index("persist:story"),
            trace.index("event:finish:stop:False"),
        )

        events = await _read_all(bus)
        self.assertEqual(sum(event.type == "message-final" for event in events), 1)
        self.assertEqual(sum(event.type == "finish" for event in events), 1)
        classifier = NormalizedAgentTurnClassifier()
        outcomes = [classifier.observe(event) for event in events]
        self.assertEqual(
            [outcome for outcome in outcomes if outcome is not None],
            [NormalizedTurnOutcome.COMPLETED],
        )

        await bus.publish_terminal(_event("finish", finishReason="error"))
        self.assertEqual(
            sum(event.type == "finish" for event in await _read_all(bus)),
            1,
        )

    async def test_s13_failure_flushes_partial_then_emits_one_failed_finish(
        self,
    ) -> None:
        trace: list[str] = []
        bus = _TraceBus(trace)
        service, execution = self._execution(
            bus=bus,
            runner=_ResultRunner(
                AgentRunResult(
                    full_text="partial",
                    session_id="claude-session",
                    success=False,
                    error=RuntimeError("provider failed"),
                )
            ),
        )
        patches = self._persistence_patches(service, trace)
        with patches[0], patches[1], patches[2], patches[3]:
            await service.execute_session(execution)

        self.assertLess(trace.index("event:error"), trace.index("persist:partial"))
        self.assertLess(
            trace.index("persist:partial"),
            trace.index("event:finish:error:False"),
        )
        events = await _read_all(bus)
        self.assertNotIn("message-final", [event.type for event in events])
        finishes = [event for event in events if event.type == "finish"]
        self.assertEqual(len(finishes), 1)
        self.assertEqual(finishes[0].data["finishReason"], "error")

    async def test_s13_cancel_flushes_partial_then_emits_one_cancelled_finish(
        self,
    ) -> None:
        trace: list[str] = []
        bus = _TraceBus(trace)
        service, execution = self._execution(
            bus=bus,
            runner=_ResultRunner(asyncio.CancelledError()),
        )
        patches = self._persistence_patches(service, trace)
        with patches[0], patches[1], patches[2], patches[3]:
            with self.assertRaises(asyncio.CancelledError):
                await service.execute_session(execution)

        self.assertLess(
            trace.index("persist:partial"),
            trace.index("event:finish:stop:True"),
        )
        events = await _read_all(bus)
        finishes = [event for event in events if event.type == "finish"]
        self.assertEqual(len(finishes), 1)
        self.assertEqual(
            finishes[0].data,
            {"finishReason": "stop", "cancelled": True},
        )


class DreamAgentS14MigrationAcceptance(unittest.IsolatedAsyncioTestCase):
    async def test_s14_openapi_has_chat_contract_and_no_legacy_dream_conversation_routes(
        self,
    ) -> None:
        import server

        paths = server.app.openapi()["paths"]
        legacy_paths = [path for path in paths if "/dream-agent" in path]
        self.assertEqual(legacy_paths, [])
        self.assertIn("post", paths["/api/claude-agent/tool-confirm"])
        self.assertIn(
            "get",
            paths[
                "/api/story-workspace/workflow-runs/{workflow_run_id}/dream-files"
            ],
        )
        self.assertIn(
            "post",
            paths[
                "/api/story-workspace/workflow-runs/{workflow_run_id}/dream-confirmation"
            ],
        )
        self.assertFalse(
            (ROOT / "services/story_workspace/dream_agent_message_service.py").exists()
        )
        self.assertFalse(
            (ROOT / "services/story_workspace/dream_stream_adapter.py").exists()
        )

    async def test_s14_dream_gets_are_actor_scoped_reads_and_recovery_is_startup_only(
        self,
    ) -> None:
        import routers.story_workspace as route_module
        import server

        gateway = mock.Mock()
        gateway.list_dream_runs = mock.AsyncMock(return_value=[])
        gateway.get_dream_files = mock.AsyncMock(
            return_value={"threadId": THREAD_ID, "files": []}
        )
        gateway.start_internal_dream_dispatches = mock.Mock()

        listed = await route_module.story_workspace_list_dream_runs(
            current_user={"user_id": int(ACTOR_ID)},
            gateway=gateway,
        )
        files = await route_module.story_workspace_get_workflow_run_dream_files(
            RUN_ID,
            current_user={"user_id": int(ACTOR_ID)},
            gateway=gateway,
        )
        self.assertEqual(listed, [])
        self.assertEqual(files["threadId"], THREAD_ID)
        gateway.list_dream_runs.assert_awaited_once_with(
            actor={"actor_id": ACTOR_ID}
        )
        gateway.get_dream_files.assert_awaited_once_with(
            RUN_ID,
            actor={"actor_id": ACTOR_ID},
        )
        gateway.start_internal_dream_dispatches.assert_not_called()

        denied_gateway = mock.Mock()
        denied_gateway.list_dream_runs = mock.AsyncMock()
        denied = await route_module.story_workspace_list_dream_runs(
            current_user={},
            gateway=denied_gateway,
        )
        self.assertEqual(denied.status_code, 403)
        denied_gateway.list_dream_runs.assert_not_awaited()

        startup_names = [handler.__name__ for handler in server.app.router.on_startup]
        self.assertIn(
            "story_workspace_startup_dream_internal_dispatches",
            startup_names,
        )
        with mock.patch.object(
            server,
            "get_story_workflow_application_gateway",
            return_value=gateway,
        ):
            await server.story_workspace_startup_dream_internal_dispatches()
        gateway.start_internal_dream_dispatches.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
