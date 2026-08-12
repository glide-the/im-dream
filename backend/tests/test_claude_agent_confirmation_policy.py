from __future__ import annotations

import asyncio
import sys
import threading
import unittest
import unittest.mock
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tests._sdk_stubs  # noqa: F401

from claude_agent.event_bus import BusProxyQueue, InMemoryEventBus
from claude_agent.service import ClaudeAgentService, _TurnContext
from claude_agent.stream_events import NormalizedAgentEvent
from claude_agent.thread_factory import ClaudeAgentThreadFactory
from claude_agent.thread_pool import AgentRunState
from claude_agent.tool_confirmation_store import (
    MAX_PENDING_CONFIRMATIONS,
    SETTLED_CONFIRMATION_TTL_S,
    ToolConfirmationCapacityExceeded,
    ToolConfirmationInvalidDecision,
    ToolConfirmationNotPending,
    ToolConfirmationPolicyConflict,
    ToolConfirmationResult,
    ToolConfirmationStore,
)


class TestToolConfirmationPolicy(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.store = ToolConfirmationStore(thread_id="thread-1", turn_id="turn-1")

    async def asyncTearDown(self) -> None:
        self.store.cancel_all()

    def _policy(self, **overrides):
        payload = {
            "tool_call_id": "call-1",
            "tool_name": "Bash",
            "input": {"command": "pwd"},
            **overrides,
        }
        return self.store.policy_from_payload(payload)

    async def _wait_for_bus_event(self, token, event_type: str):
        while True:
            event = await asyncio.wait_for(token.get(), timeout=1.0)
            if event is not None and event.type == event_type:
                return event

    async def _replay_completed_bus(self, bus: InMemoryEventBus):
        await bus.publish_terminal(
            NormalizedAgentEvent.create(
                "finish",
                {"finishReason": "stop"},
            )
        )
        token = await bus.subscribe()
        return [event async for event in bus.read(token)]

    async def test_invalid_decision_never_touches_the_future(self) -> None:
        policy = self.store.policy_from_payload(
            {
                "tool_call_id": "call-1",
                "tool_name": "AskUserQuestion",
                "input": {
                    "questions": [
                        {
                            "question": "Continue?",
                            "type": "radio",
                            "required": True,
                            "options": ["yes", "no"],
                        }
                    ]
                },
            }
        )
        self.store.register_pending(policy)
        waiter = asyncio.create_task(self.store.await_pending("call-1"))

        with self.assertRaises(ToolConfirmationInvalidDecision):
            await self.store.resolve_exact(
                thread_id="thread-1",
                turn_id="turn-1",
                tool_call_id="call-1",
                result=ToolConfirmationResult(True, answers={"unknown": "yes"}),
            )

        self.assertTrue(self.store.has_pending("call-1"))
        resolution = await self.store.resolve_exact(
            thread_id="thread-1",
            turn_id="turn-1",
            tool_call_id="call-1",
            result=ToolConfirmationResult(True, answers={"q0": "yes"}),
        )
        self.assertFalse(resolution.replayed)
        self.assertEqual(resolution.result.answers, {"Continue?": "yes"})
        self.assertEqual((await waiter).answers, {"Continue?": "yes"})

    async def test_callback_registers_policy_before_approval_becomes_visible(self) -> None:
        queue = asyncio.Queue()
        turn_context = _TurnContext(queue=queue, confirmation_store=self.store)
        callback = ClaudeAgentService._make_tool_confirm_cb(
            queue,
            self.store,
            turn_context,
        )
        task = asyncio.create_task(
            callback(
                {
                    "tool_call_id": "call-1",
                    "tool_name": "Bash",
                    "input": {"command": "pwd"},
                }
            )
        )
        approval = None
        while approval is None:
            event = await asyncio.wait_for(queue.get(), timeout=1.0)
            if event.type == "tool-approval-request":
                approval = event
        self.assertTrue(self.store.has_pending("call-1"))
        self.assertEqual(self.store.policy_for("call-1").kind, "approval")
        self.assertEqual(approval.data["toolCallId"], "call-1")
        await self.store.resolve_exact(
            thread_id="thread-1",
            turn_id="turn-1",
            tool_call_id="call-1",
            result=ToolConfirmationResult(True),
        )
        self.assertEqual(await task, {"approved": True, "reason": None, "answers": None})

    async def test_duplicate_callbacks_share_one_pending_decision(self) -> None:
        bus = InMemoryEventBus()
        queue = BusProxyQueue(bus)
        turn_context = _TurnContext(queue=queue, confirmation_store=self.store)
        callback = ClaudeAgentService._make_tool_confirm_cb(
            queue,
            self.store,
            turn_context,
        )
        payload = {
            "tool_call_id": "call-1",
            "tool_name": "Bash",
            "input": {"command": "pwd"},
        }
        live = await bus.subscribe()
        first = asyncio.create_task(callback(payload))
        await self._wait_for_bus_event(live, "tool-approval-request")
        duplicate = asyncio.create_task(callback(payload))
        await self.store.resolve_exact(
            thread_id="thread-1",
            turn_id="turn-1",
            tool_call_id="call-1",
            result=ToolConfirmationResult(False, reason="declined"),
        )
        first_result, duplicate_result = await asyncio.gather(first, duplicate)
        replayed_result = await callback(payload)
        self.assertFalse(first_result["approved"])
        self.assertEqual(duplicate_result, first_result)
        self.assertEqual(replayed_result, first_result)

        replay = await self._replay_completed_bus(bus)
        self.assertEqual(
            sum(event.type == "tool-approval-request" for event in replay),
            1,
        )

    async def test_cancelled_http_resolver_does_not_lose_pending_decision(self) -> None:
        bus = InMemoryEventBus()
        queue = BusProxyQueue(bus)
        turn_context = _TurnContext(queue=queue, confirmation_store=self.store)
        callback = ClaudeAgentService._make_tool_confirm_cb(
            queue,
            self.store,
            turn_context,
        )
        live = await bus.subscribe()
        callback_task = asyncio.create_task(
            callback(
                {
                    "tool_call_id": "call-1",
                    "tool_name": "Bash",
                    "input": {"command": "pwd"},
                }
            )
        )
        await self._wait_for_bus_event(live, "tool-approval-request")

        original_schedule = self.store._schedule_result
        scheduled = asyncio.Event()
        captured: dict[str, object] = {}

        def hold_schedule(record, identity, result) -> None:
            captured.update(record=record, identity=identity, result=result)
            scheduled.set()

        self.store._schedule_result = hold_schedule
        resolver = asyncio.create_task(
            self.store.resolve_exact(
                thread_id="thread-1",
                turn_id="turn-1",
                tool_call_id="call-1",
                result=ToolConfirmationResult(True),
            )
        )
        await asyncio.wait_for(scheduled.wait(), timeout=1.0)
        resolver.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await resolver

        original_schedule(
            captured["record"],
            captured["identity"],
            captured["result"],
        )
        result = await asyncio.wait_for(callback_task, timeout=1.0)
        self.assertTrue(result["approved"])

    async def test_timeout_denies_and_turn_cancel_cleans_pending_decision(self) -> None:
        timeout_queue = asyncio.Queue()
        timeout_context = _TurnContext(
            queue=timeout_queue,
            confirmation_store=self.store,
        )
        timeout_callback = ClaudeAgentService._make_tool_confirm_cb(
            timeout_queue,
            self.store,
            timeout_context,
        )
        with unittest.mock.patch.object(
            self.store,
            "await_pending",
            new=unittest.mock.AsyncMock(side_effect=TimeoutError("timeout")),
        ):
            timeout_result = await timeout_callback(
                {
                    "tool_call_id": "call-1",
                    "tool_name": "Bash",
                    "input": {"command": "pwd"},
                }
            )
        self.assertEqual(timeout_result, {"approved": False, "reason": "timeout"})

        cancel_store = ToolConfirmationStore(
            thread_id="thread-2",
            turn_id="turn-2",
        )
        self.addAsyncCleanup(asyncio.to_thread, cancel_store.cancel_all)
        cancel_queue = asyncio.Queue()
        cancel_context = _TurnContext(
            queue=cancel_queue,
            confirmation_store=cancel_store,
        )
        cancel_callback = ClaudeAgentService._make_tool_confirm_cb(
            cancel_queue,
            cancel_store,
            cancel_context,
        )
        cancelled = asyncio.create_task(
            cancel_callback(
                {
                    "tool_call_id": "call-cancel",
                    "tool_name": "Bash",
                    "input": {"command": "pwd"},
                }
            )
        )
        while True:
            event = await asyncio.wait_for(cancel_queue.get(), timeout=1.0)
            if event.type == "tool-approval-request":
                break
        cancelled.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await cancelled
        self.assertFalse(cancel_store.has_pending("call-cancel"))

    async def test_malformed_ask_user_is_published_as_reject_only(self) -> None:
        queue = asyncio.Queue()
        turn_context = _TurnContext(queue=queue, confirmation_store=self.store)
        callback = ClaudeAgentService._make_tool_confirm_cb(
            queue,
            self.store,
            turn_context,
        )
        task = asyncio.create_task(
            callback(
                {
                    "tool_call_id": "call-1",
                    "tool_name": "AskUserQuestion",
                    "input": {"questions": []},
                }
            )
        )
        approval = None
        while approval is None:
            event = await asyncio.wait_for(queue.get(), timeout=1.0)
            if event.type == "tool-approval-request":
                approval = event
        self.assertEqual(approval.data["confirmationKind"], "reject_only")
        await self.store.resolve_exact(
            thread_id="thread-1",
            turn_id="turn-1",
            tool_call_id="call-1",
            result=ToolConfirmationResult(False),
        )
        self.assertFalse((await task)["approved"])

    async def test_touch_animation_remains_generic_approval(self) -> None:
        policy = self.store.policy_from_payload(
            {
                "tool_call_id": "call-1",
                "tool_name": "mcp__story_workspace__touch_animation",
                "input": {
                    "act": "pulse",
                    "duration": 300,
                    "interaction": "preview",
                },
            }
        )
        self.assertEqual(policy.kind, "approval")
        self.store.register_pending(policy)
        waiter = asyncio.create_task(self.store.await_pending("call-1"))
        resolution = await self.store.resolve_exact(
            thread_id="thread-1",
            turn_id="turn-1",
            tool_call_id="call-1",
            result=ToolConfirmationResult(True),
        )
        self.assertTrue(resolution.result.approved)
        self.assertIsNone((await waiter).answers)

    async def test_question_text_keys_preserve_existing_chat_contract(self) -> None:
        policy = self.store.policy_from_payload(
            {
                "tool_call_id": "call-1",
                "tool_name": "mcp__user__ask_user",
                "input": {"questions": [{"question": "Name?", "required": True}]},
            }
        )
        self.store.register_pending(policy)
        waiter = asyncio.create_task(self.store.await_pending("call-1"))
        resolution = await self.store.resolve_exact(
            thread_id="thread-1",
            turn_id="turn-1",
            tool_call_id="call-1",
            result=ToolConfirmationResult(True, answers={"Name?": "Lin"}),
        )
        self.assertEqual(resolution.result.answers, {"Name?": "Lin"})
        self.assertEqual((await waiter).answers, {"Name?": "Lin"})

    async def test_reject_only_cannot_be_approved_but_can_be_rejected(self) -> None:
        policy = self.store.policy_from_payload(
            {
                "tool_call_id": "call-1",
                "tool_name": "AskUserQuestion",
                "input": {"questions": []},
            }
        )
        self.assertEqual(policy.kind, "reject_only")
        self.store.register_pending(policy)
        with self.assertRaises(ToolConfirmationInvalidDecision):
            await self.store.resolve_exact(
                thread_id="thread-1",
                turn_id="turn-1",
                tool_call_id="call-1",
                result=ToolConfirmationResult(True),
            )
        resolution = await self.store.resolve_exact(
            thread_id="thread-1",
            turn_id="turn-1",
            tool_call_id="call-1",
            result=ToolConfirmationResult(False, reason="cannot render safely"),
        )
        self.assertFalse(resolution.result.approved)

    async def test_network_policy_is_server_derived_and_deny_is_reject_only_in_effect(self) -> None:
        policy = self.store.policy_from_payload(
            {
                "tool_call_id": "call-1",
                "tool_name": "SandboxNetworkAccess",
                "input": {"host": "cdn.example.com"},
                "confirmationKind": "sandbox_network",
                "networkRequest": {
                    "host": "cdn.example.com",
                    "policyMode": "deny",
                    "matchedAllowedDomain": None,
                },
            }
        )
        self.assertEqual(policy.network_host, "cdn.example.com")
        self.assertEqual(policy.network_policy, "deny")
        self.store.register_pending(policy)
        with self.assertRaises(ToolConfirmationInvalidDecision):
            await self.store.resolve_exact(
                thread_id="thread-1",
                turn_id="turn-1",
                tool_call_id="call-1",
                result=ToolConfirmationResult(True),
            )
        self.assertTrue(self.store.has_pending("call-1"))

    async def test_duplicate_callback_policy_mismatch_and_capacity_fail_closed(self) -> None:
        store = ToolConfirmationStore(
            thread_id="thread-1",
            turn_id="turn-1",
            max_pending=1,
        )
        try:
            first = store.policy_from_payload(
                {"tool_call_id": "call-1", "tool_name": "Bash", "input": {"a": 1}}
            )
            store.register_pending(first)
            conflicting = store.policy_from_payload(
                {"tool_call_id": "call-1", "tool_name": "Bash", "input": {"a": 2}}
            )
            with self.assertRaises(ToolConfirmationPolicyConflict):
                store.register_pending(conflicting)
            second = store.policy_from_payload(
                {"tool_call_id": "call-2", "tool_name": "Bash", "input": {}}
            )
            with self.assertRaises(ToolConfirmationCapacityExceeded):
                store.register_pending(second)
        finally:
            store.cancel_all()

    async def test_process_wide_pending_capacity_is_bounded(self) -> None:
        stores: list[ToolConfirmationStore] = []
        overflow: ToolConfirmationStore | None = None
        try:
            for index in range(MAX_PENDING_CONFIRMATIONS):
                store = ToolConfirmationStore(
                    thread_id=f"thread-{index}",
                    turn_id=f"turn-{index}",
                )
                store.register_pending(
                    store.policy_from_payload(
                        {
                            "tool_call_id": f"call-{index}",
                            "tool_name": "Bash",
                            "input": {},
                        }
                    )
                )
                stores.append(store)
            overflow = ToolConfirmationStore(
                thread_id="thread-overflow",
                turn_id="turn-overflow",
            )
            with self.assertRaises(ToolConfirmationCapacityExceeded):
                overflow.register_pending(
                    overflow.policy_from_payload(
                        {
                            "tool_call_id": "call-overflow",
                            "tool_name": "Bash",
                            "input": {},
                        }
                    )
                )
        finally:
            if overflow is not None:
                overflow.cancel_all()
            for store in stores:
                store.cancel_all()

    async def test_oversized_reason_and_wrong_tool_leave_original_future_pending(self) -> None:
        self.store.register_pending(self._policy())
        with self.assertRaises(Exception) as wrong_tool:
            await self.store.resolve_exact(
                thread_id="thread-1",
                turn_id="turn-1",
                tool_call_id="call-other",
                result=ToolConfirmationResult(True),
            )
        self.assertEqual(getattr(wrong_tool.exception, "code", None), "TOOL_CONFIRMATION_NOT_PENDING")
        with self.assertRaises(ToolConfirmationInvalidDecision):
            await self.store.resolve_exact(
                thread_id="thread-1",
                turn_id="turn-1",
                tool_call_id="call-1",
                result=ToolConfirmationResult(False, reason="x" * 501),
            )
        self.assertTrue(self.store.has_pending("call-1"))

    async def test_concurrent_duplicate_resolution_has_one_winner_and_stable_replay(self) -> None:
        self.store.register_pending(self._policy())

        async def resolve():
            return await self.store.resolve_exact(
                thread_id="thread-1",
                turn_id="turn-1",
                tool_call_id="call-1",
                result=ToolConfirmationResult(True),
            )

        first, second = await asyncio.gather(resolve(), resolve())
        self.assertEqual(sorted([first.replayed, second.replayed]), [False, True])
        self.assertTrue(first.result.approved)
        self.assertTrue(second.result.approved)
        replay = await resolve()
        self.assertTrue(replay.replayed)
        self.assertTrue(replay.result.approved)

    async def test_cancelled_resolver_does_not_cancel_shared_settlement_ack(self) -> None:
        self.store.register_pending(self._policy())
        original_schedule = self.store._schedule_result
        scheduled = asyncio.Event()
        captured: dict[str, object] = {}

        def hold_schedule(record, identity, result) -> None:
            captured.update(record=record, identity=identity, result=result)
            scheduled.set()

        self.store._schedule_result = hold_schedule

        async def resolve():
            return await self.store.resolve_exact(
                thread_id="thread-1",
                turn_id="turn-1",
                tool_call_id="call-1",
                result=ToolConfirmationResult(True),
            )

        first = asyncio.create_task(resolve())
        await asyncio.wait_for(scheduled.wait(), timeout=1.0)
        first.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first

        second = asyncio.create_task(resolve())
        await asyncio.sleep(0)
        original_schedule(
            captured["record"],
            captured["identity"],
            captured["result"],
        )
        resolution = await asyncio.wait_for(second, timeout=1.0)
        self.assertTrue(resolution.replayed)
        self.assertTrue(resolution.result.approved)

    async def test_settled_replay_tombstone_expires(self) -> None:
        self.store.register_pending(self._policy())
        with unittest.mock.patch(
            "claude_agent.tool_confirmation_store.time.monotonic",
            return_value=100.0,
        ):
            await self.store.resolve_exact(
                thread_id="thread-1",
                turn_id="turn-1",
                tool_call_id="call-1",
                result=ToolConfirmationResult(True),
            )
        with unittest.mock.patch(
            "claude_agent.tool_confirmation_store.time.monotonic",
            return_value=100.0 + SETTLED_CONFIRMATION_TTL_S + 1.0,
        ):
            with self.assertRaises(ToolConfirmationNotPending):
                await self.store.resolve_exact(
                    thread_id="thread-1",
                    turn_id="turn-1",
                    tool_call_id="call-1",
                    result=ToolConfirmationResult(True),
                )

    async def test_turn_drift_fails_without_settling(self) -> None:
        self.store.register_pending(self._policy())
        with self.assertRaises(Exception) as raised:
            await self.store.resolve_exact(
                thread_id="thread-1",
                turn_id="turn-old",
                tool_call_id="call-1",
                result=ToolConfirmationResult(True),
            )
        self.assertEqual(getattr(raised.exception, "code", None), "TOOL_CONFIRMATION_NOT_PENDING")
        self.assertTrue(self.store.has_pending("call-1"))

    async def test_timeout_and_turn_cleanup_remove_all_runtime_state(self) -> None:
        self.store.register_pending(self._policy())
        with self.assertRaises(TimeoutError):
            await self.store.await_pending("call-1", timeout_s=0.001)
        self.assertEqual(self.store.pending_ids(), [])
        self.store.cancel_all()
        self.assertEqual(self.store.pending_ids(), [])

    async def test_service_requires_exact_state_turn(self) -> None:
        self.store.register_pending(self._policy())
        state = AgentRunState(session_id="thread-1")
        state.current_turn_id = "turn-1"
        state.turn_context = _TurnContext(
            queue=asyncio.Queue(),
            confirmation_store=self.store,
        )
        service = ClaudeAgentService()
        stale = await service.confirm_tool(
            state,
            "call-1",
            True,
            thread_id="thread-1",
            turn_id="turn-old",
        )
        self.assertIsNone(stale)
        self.assertTrue(self.store.has_pending("call-1"))
        settled = await service.confirm_tool(
            state,
            "call-1",
            True,
            thread_id="thread-1",
            turn_id="turn-1",
        )
        self.assertIsNotNone(settled)
        self.assertTrue(settled.result.approved)

    async def test_service_error_path_cleans_pending_policy_and_future(self) -> None:
        self.store.register_pending(self._policy())
        service = ClaudeAgentService()
        service._execute_session_inner = unittest.mock.AsyncMock(
            side_effect=RuntimeError("runner failed")
        )
        execution = SimpleNamespace(
            turn_context=SimpleNamespace(confirmation_store=self.store)
        )
        with self.assertRaisesRegex(RuntimeError, "runner failed"):
            await service.execute_session(execution)
        self.assertEqual(self.store.pending_ids(), [])

    async def test_factory_requires_exact_active_actor_and_snapshots_turn(self) -> None:
        factory = ClaudeAgentThreadFactory()
        state = factory._pool.get_or_create("thread-1")
        state.current_user_id = "7"
        state.current_turn_id = "turn-1"
        state.turn_context = _TurnContext(
            queue=asyncio.Queue(),
            confirmation_store=self.store,
        )
        state.mark_running()
        expected = type("Resolution", (), {})()
        factory._service.confirm_tool = unittest.mock.AsyncMock(return_value=expected)

        denied = await factory.confirm_tool(
            "thread-1",
            "call-1",
            True,
            actor_id="8",
        )
        self.assertIsNone(denied)
        factory._service.confirm_tool.assert_not_awaited()

        resolved = await factory.confirm_tool(
            "thread-1",
            "call-1",
            True,
            actor_id="7",
        )
        self.assertIs(resolved, expected)
        factory._service.confirm_tool.assert_awaited_once_with(
            state,
            "call-1",
            True,
            None,
            None,
            thread_id="thread-1",
            turn_id="turn-1",
        )


class TestCrossLoopResolution(unittest.TestCase):
    def test_resolve_exact_waits_until_owner_future_is_settled(self) -> None:
        ready = threading.Event()
        owner_observed = threading.Event()
        holder: dict[str, object] = {}

        def owner_thread() -> None:
            async def owner() -> None:
                store = ToolConfirmationStore(thread_id="thread-x", turn_id="turn-x")
                holder["store"] = store
                store.register_pending(
                    store.policy_from_payload(
                        {"tool_call_id": "call-x", "tool_name": "Bash", "input": {}}
                    )
                )
                ready.set()
                holder["result"] = await store.await_pending("call-x")
                owner_observed.set()

            asyncio.run(owner())

        thread = threading.Thread(target=owner_thread, daemon=True)
        thread.start()
        self.assertTrue(ready.wait(timeout=2.0))
        store = holder["store"]

        async def resolve() -> None:
            resolution = await store.resolve_exact(
                thread_id="thread-x",
                turn_id="turn-x",
                tool_call_id="call-x",
                result=ToolConfirmationResult(True),
            )
            self.assertTrue(resolution.result.approved)
            self.assertTrue(owner_observed.wait(timeout=1.0))

        asyncio.run(resolve())
        thread.join(timeout=2.0)
        self.assertFalse(thread.is_alive())
        self.assertTrue(holder["result"].approved)


if __name__ == "__main__":
    unittest.main()
