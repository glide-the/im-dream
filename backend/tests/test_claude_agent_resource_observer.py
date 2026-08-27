# [Input] Consume the resource Observer, admission decorator, existing admission controller,
#         normalized EventBus, and existing turn classifier semantics.
# [Output] Verify registration, terminal counts, denial observation, exception isolation, and lease safety.
# [Pos] Focused resource Observer contract tests in backend/tests.
# [Sync] 2026-08-27: add provider-free coverage for process-local Claude resource observations.

from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tests._sdk_stubs  # noqa: F401

from claude_agent.admission import (
    AgentAdmissionConfig,
    AgentResourceSnapshot,
    ClaudeAgentAdmissionController,
    ClaudeAgentAdmissionError,
)
from claude_agent.event_bus import InMemoryEventBus
from claude_agent.observer import SessionObserverRegistry
from claude_agent.resource_observer import (
    ClaudeAgentResourceObserver,
    ObservedClaudeAgentAdmissionController,
)
from claude_agent.service import ClaudeAgentRunRequest
from claude_agent.stream_events import NormalizedAgentEvent
from claude_agent.thread_factory import ClaudeAgentThreadFactory


_MIB = 1024 * 1024


def _config() -> AgentAdmissionConfig:
    return AgentAdmissionConfig(
        max_concurrent_runs=1,
        run_memory_budget_mib=512,
        memory_reserve_mib=128,
        retry_after_seconds=60,
    )


async def _settle(observer: ClaudeAgentResourceObserver) -> None:
    for _ in range(100):
        if not observer._reader_tasks:
            return
        await asyncio.sleep(0)
    raise AssertionError("resource Observer reader did not settle")


class TestClaudeAgentResourceObserver(unittest.IsolatedAsyncioTestCase):
    async def test_factory_integration_counts_completion_and_preserves_release(self) -> None:
        observer = ClaudeAgentResourceObserver()
        admission = ObservedClaudeAgentAdmissionController(
            ClaudeAgentAdmissionController(
                _config(),
                snapshot_provider=lambda: AgentResourceSnapshot(
                    host_available_bytes=2 * 1024 * _MIB
                ),
            ),
            observer,
        )
        factory = ClaudeAgentThreadFactory(admission_controller=admission)
        factory.register_observer(observer)

        async def assemble(_request, *, state, bus, runner):
            del state, runner
            return SimpleNamespace(dream_context=None, bus=bus)

        async def execute(execution):
            await execution.bus.publish(
                NormalizedAgentEvent.create("message-final", {"text": "discarded"})
            )
            await execution.bus.publish_terminal(
                NormalizedAgentEvent.create("finish", {"finishReason": "stop"})
            )

        factory._service.assemble_context = assemble
        factory._service.execute_session = execute
        request = ClaudeAgentRunRequest(
            user_id="private-user",
            thread_id="private-thread",
            message_parts=[{"type": "text", "text": "discarded"}],
        )
        with mock.patch("claude_agent.thread_factory.ClaudeAgentRunner"):
            frames = [frame async for frame in factory.run_streaming(request)]
        await _settle(observer)

        self.assertTrue(frames)
        counters = observer.snapshot()
        self.assertEqual(counters.admission_granted_total, 1)
        self.assertEqual(counters.turn_started_total, 1)
        self.assertEqual(counters.turn_completed_total, 1)
        self.assertEqual(admission.stats()["active_runs"], 0)
        self.assertNotIn("private", repr(counters))
        await factory.aclose()

    async def test_register_unregister_and_three_terminal_outcomes(self) -> None:
        registry = SessionObserverRegistry()
        observer = ClaudeAgentResourceObserver()
        registry.register(observer)

        completed = InMemoryEventBus()
        await registry.emit_after_context_assembly("private-session", {"event_bus": completed})
        await completed.publish(
            NormalizedAgentEvent.create("message-final", {"text": "never retained"})
        )
        await completed.publish_terminal(
            NormalizedAgentEvent.create("finish", {"finishReason": "stop"})
        )

        failed = InMemoryEventBus()
        await registry.emit_after_context_assembly("private-session", {"event_bus": failed})
        await failed.publish_terminal(
            NormalizedAgentEvent.create("finish", {"finishReason": "error"})
        )

        cancelled = InMemoryEventBus()
        await registry.emit_after_context_assembly("private-session", {"event_bus": cancelled})
        await cancelled.publish_terminal(
            NormalizedAgentEvent.create(
                "finish", {"finishReason": "stop", "cancelled": True}
            )
        )
        await _settle(observer)

        registry.unregister(observer)
        ignored = InMemoryEventBus()
        await registry.emit_after_context_assembly("private-session", {"event_bus": ignored})
        snapshot = observer.snapshot()
        self.assertEqual(snapshot.turn_started_total, 3)
        self.assertEqual(snapshot.turn_completed_total, 1)
        self.assertEqual(snapshot.turn_failed_total, 1)
        self.assertEqual(snapshot.turn_cancelled_total, 1)
        self.assertNotIn("private-session", repr(snapshot))
        await observer.aclose()

    async def test_reader_failure_is_off_path(self) -> None:
        class BrokenBus:
            async def subscribe(self):
                raise RuntimeError("unavailable")

        observer = ClaudeAgentResourceObserver()
        observer.on_after_context_assembly("discarded", {"event_bus": BrokenBus()})
        await _settle(observer)
        self.assertEqual(observer.snapshot().turn_started_total, 1)
        await observer.aclose()


class TestObservedAdmissionController(unittest.TestCase):
    def test_grant_capacity_denial_and_original_lease_release(self) -> None:
        observer = ClaudeAgentResourceObserver()
        delegate = ClaudeAgentAdmissionController(
            _config(),
            snapshot_provider=lambda: AgentResourceSnapshot(
                host_available_bytes=2 * 1024 * _MIB
            ),
        )
        admission = ObservedClaudeAgentAdmissionController(delegate, observer)

        lease = admission.try_acquire("one")
        with self.assertRaises(ClaudeAgentAdmissionError) as caught:
            admission.try_acquire("two")
        self.assertEqual(caught.exception.code, "CLAUDE_AGENT_CAPACITY_EXHAUSTED")
        lease.release()

        counters = observer.snapshot()
        self.assertEqual(counters.admission_granted_total, 1)
        self.assertEqual(counters.capacity_denials_total, 1)
        self.assertEqual(counters.last_denial_type, "capacity")
        self.assertEqual(admission.stats()["active_runs"], 0)

    def test_memory_denial_is_observed_without_acquiring(self) -> None:
        observer = ClaudeAgentResourceObserver()
        admission = ObservedClaudeAgentAdmissionController(
            ClaudeAgentAdmissionController(
                _config(),
                snapshot_provider=lambda: AgentResourceSnapshot(
                    host_available_bytes=100 * _MIB
                ),
            ),
            observer,
        )
        with self.assertRaises(ClaudeAgentAdmissionError):
            admission.try_acquire("memory")
        counters = observer.snapshot()
        self.assertEqual(counters.memory_pressure_denials_total, 1)
        self.assertEqual(counters.last_denial_type, "memory_pressure")
        self.assertEqual(admission.stats()["active_runs"], 0)

    def test_observer_exception_cannot_change_grant_denial_or_lease(self) -> None:
        observer = ClaudeAgentResourceObserver()
        delegate = ClaudeAgentAdmissionController(
            _config(),
            snapshot_provider=lambda: AgentResourceSnapshot(
                host_available_bytes=2 * 1024 * _MIB
            ),
        )
        admission = ObservedClaudeAgentAdmissionController(delegate, observer)
        with mock.patch.object(
            observer,
            "record_admission_granted",
            side_effect=RuntimeError("observer failed"),
        ):
            lease = admission.try_acquire("one")
        self.assertEqual(admission.stats()["active_runs"], 1)
        with mock.patch.object(
            observer,
            "record_admission_denied",
            side_effect=RuntimeError("observer failed"),
        ):
            with self.assertRaises(ClaudeAgentAdmissionError) as caught:
                admission.try_acquire("two")
        self.assertEqual(caught.exception.code, "CLAUDE_AGENT_CAPACITY_EXHAUSTED")
        lease.release()
        self.assertEqual(admission.stats()["active_runs"], 0)
