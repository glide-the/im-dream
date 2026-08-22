# [Input] Consume claude_agent/admission.py and the existing thread factory/EventBus path.
# [Output] Verify bounded concurrency, host/cgroup memory preflight, retryable
#          SSE errors, missing-metric fallback, and idempotent lease release.
# [Pos] resource-admission test node in backend/tests.
# [Sync] 2026-08-22: add provider-free admission and factory integration coverage.

"""Tests for Claude Agent process-local resource admission."""
from __future__ import annotations

import asyncio
import sys
import unittest
import unittest.mock
from pathlib import Path
from types import SimpleNamespace

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
from claude_agent.service import ClaudeAgentRunRequest
from claude_agent.stream_events import NormalizedAgentEvent
from claude_agent.thread_factory import ClaudeAgentThreadFactory

_MIB = 1024 * 1024


def _config(*, max_runs: int = 1) -> AgentAdmissionConfig:
    return AgentAdmissionConfig(
        max_concurrent_runs=max_runs,
        run_memory_budget_mib=512,
        memory_reserve_mib=128,
        retry_after_seconds=60,
    )


def _request(thread_id: str) -> ClaudeAgentRunRequest:
    return ClaudeAgentRunRequest(
        user_id=f"user-{thread_id}",
        thread_id=thread_id,
        message_parts=[{"type": "text", "text": "hello"}],
    )


class TestClaudeAgentAdmissionController(unittest.TestCase):
    def test_admits_and_releases_idempotently(self):
        controller = ClaudeAgentAdmissionController(
            _config(),
            snapshot_provider=lambda: AgentResourceSnapshot(
                host_available_bytes=900 * _MIB,
                cgroup_current_bytes=100 * _MIB,
                cgroup_max_bytes=1024 * _MIB,
            ),
        )

        lease = controller.try_acquire("thread-one")
        self.assertEqual(controller.stats()["active_runs"], 1)
        lease.release()
        lease.release()
        self.assertEqual(controller.stats()["active_runs"], 0)

    def test_rejects_second_concurrent_run_before_resampling(self):
        samples = 0

        def snapshot():
            nonlocal samples
            samples += 1
            return AgentResourceSnapshot(host_available_bytes=900 * _MIB)

        controller = ClaudeAgentAdmissionController(
            _config(), snapshot_provider=snapshot
        )
        lease = controller.try_acquire("thread-one")

        with self.assertRaises(ClaudeAgentAdmissionError) as caught:
            controller.try_acquire("thread-two")

        self.assertEqual(caught.exception.code, "CLAUDE_AGENT_CAPACITY_EXHAUSTED")
        self.assertTrue(caught.exception.retryable)
        self.assertEqual(caught.exception.retry_after_seconds, 60)
        self.assertEqual(samples, 1)
        self.assertEqual(controller.stats()["capacity_denials"], 1)
        lease.release()

    def test_rejects_low_host_available_memory(self):
        controller = ClaudeAgentAdmissionController(
            _config(),
            snapshot_provider=lambda: AgentResourceSnapshot(
                host_available_bytes=639 * _MIB,
            ),
        )

        with self.assertRaises(ClaudeAgentAdmissionError) as caught:
            controller.try_acquire("thread-low-host")

        self.assertEqual(caught.exception.code, "CLAUDE_AGENT_MEMORY_PRESSURE")
        self.assertEqual(controller.stats()["active_runs"], 0)
        self.assertEqual(controller.stats()["memory_denials"], 1)

    def test_rejects_low_cgroup_headroom_even_when_host_has_memory(self):
        controller = ClaudeAgentAdmissionController(
            _config(),
            snapshot_provider=lambda: AgentResourceSnapshot(
                host_available_bytes=2 * 1024 * _MIB,
                cgroup_current_bytes=500 * _MIB,
                cgroup_max_bytes=1024 * _MIB,
            ),
        )

        with self.assertRaises(ClaudeAgentAdmissionError) as caught:
            controller.try_acquire("thread-low-cgroup")

        self.assertEqual(caught.exception.code, "CLAUDE_AGENT_MEMORY_PRESSURE")
        self.assertEqual(controller.stats()["cgroup_headroom_mib"], 524)

    def test_observed_remote_idle_headroom_admits_one_turn(self):
        controller = ClaudeAgentAdmissionController(
            _config(),
            snapshot_provider=lambda: AgentResourceSnapshot(
                host_available_bytes=673 * _MIB,
                cgroup_current_bytes=282 * _MIB,
                cgroup_max_bytes=1024 * _MIB,
            ),
        )

        lease = controller.try_acquire("thread-remote-baseline")

        stats = controller.stats()
        self.assertEqual(stats["host_available_mib"], 673)
        self.assertEqual(stats["cgroup_headroom_mib"], 742)
        lease.release()

    def test_missing_memory_metrics_keeps_concurrency_guard(self):
        controller = ClaudeAgentAdmissionController(
            _config(),
            snapshot_provider=AgentResourceSnapshot,
        )
        lease = controller.try_acquire("thread-no-metrics")

        stats = controller.stats()
        self.assertFalse(stats["metrics_available"])
        self.assertEqual(stats["active_runs"], 1)
        lease.release()

    def test_invalid_budget_config_fails_closed(self):
        with unittest.mock.patch.dict(
            "os.environ",
            {"INK_AGENT_RUN_MEMORY_BUDGET_MIB": "0"},
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "must be >= 1"):
                AgentAdmissionConfig.from_env()


class TestClaudeAgentAdmissionFactoryIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_capacity_error_uses_existing_sse_terminal_and_releases(self):
        controller = ClaudeAgentAdmissionController(
            _config(),
            snapshot_provider=lambda: AgentResourceSnapshot(
                host_available_bytes=900 * _MIB,
            ),
        )
        factory = ClaudeAgentThreadFactory(admission_controller=controller)
        entered = asyncio.Event()
        release = asyncio.Event()

        async def assemble(_request, *, state, bus, runner):
            del state, runner
            return SimpleNamespace(dream_context=None, bus=bus)

        async def execute(execution):
            entered.set()
            await release.wait()
            await execution.bus.publish_terminal(
                NormalizedAgentEvent.create(
                    "finish", {"finishReason": "completed"}
                )
            )

        factory._service.assemble_context = assemble
        factory._service.execute_session = execute

        async def collect(request):
            return [frame async for frame in factory.run_streaming(request)]

        with unittest.mock.patch("claude_agent.thread_factory.ClaudeAgentRunner"):
            first = asyncio.create_task(collect(_request("thread-one")))
            await asyncio.wait_for(entered.wait(), timeout=0.5)
            second_frames = await asyncio.wait_for(
                collect(_request("thread-two")), timeout=0.5
            )
            self.assertEqual(controller.stats()["active_runs"], 1)
            release.set()
            await asyncio.wait_for(first, timeout=0.5)

        compact = "".join(second_frames).replace(" ", "")
        self.assertIn('"type":"error"', compact)
        self.assertIn(
            '"errorCode":"CLAUDE_AGENT_CAPACITY_EXHAUSTED"', compact
        )
        self.assertIn('"retryable":true', compact)
        self.assertIn('"retryAfterSeconds":60', compact)
        self.assertIn('"type":"finish"', compact)
        self.assertEqual(controller.stats()["active_runs"], 0)

    async def test_setup_failure_releases_lease_for_retry(self):
        controller = ClaudeAgentAdmissionController(
            _config(),
            snapshot_provider=lambda: AgentResourceSnapshot(
                host_available_bytes=900 * _MIB,
            ),
        )
        factory = ClaudeAgentThreadFactory(admission_controller=controller)

        async def assemble(*_args, **_kwargs):
            raise RuntimeError("setup failed")

        factory._service.assemble_context = assemble

        async def collect(request):
            return [frame async for frame in factory.run_streaming(request)]

        with unittest.mock.patch("claude_agent.thread_factory.ClaudeAgentRunner"):
            first = await collect(_request("thread-retry"))
            second = await collect(_request("thread-retry"))

        self.assertIn('"type":"error"', "".join(first).replace(" ", ""))
        self.assertIn('"type":"error"', "".join(second).replace(" ", ""))
        lock = factory._pool.get_lock("thread-retry")
        await asyncio.wait_for(lock.acquire(), timeout=0.5)
        lock.release()
        self.assertEqual(controller.stats()["active_runs"], 0)

    async def test_stop_cancellation_releases_active_lease(self):
        controller = ClaudeAgentAdmissionController(
            _config(),
            snapshot_provider=lambda: AgentResourceSnapshot(
                host_available_bytes=900 * _MIB,
            ),
        )
        factory = ClaudeAgentThreadFactory(admission_controller=controller)
        entered = asyncio.Event()

        async def assemble(_request, *, state, bus, runner):
            del state, bus, runner
            return SimpleNamespace(dream_context=None)

        async def execute(_execution):
            entered.set()
            await asyncio.Event().wait()

        factory._service.assemble_context = assemble
        factory._service.execute_session = execute

        async def collect():
            return [
                frame
                async for frame in factory.run_streaming(
                    _request("thread-cancel")
                )
            ]

        with unittest.mock.patch("claude_agent.thread_factory.ClaudeAgentRunner"):
            consumer = asyncio.create_task(collect())
            await asyncio.wait_for(entered.wait(), timeout=0.5)
            self.assertEqual(controller.stats()["active_runs"], 1)
            stopped = await factory.stop_thread("thread-cancel")
            frames = await asyncio.wait_for(consumer, timeout=0.5)

        self.assertTrue(stopped["stop_requested"])
        self.assertFalse(stopped["running"])
        self.assertIn('"finishReason":"stop"', "".join(frames).replace(" ", ""))
        self.assertEqual(controller.stats()["active_runs"], 0)
