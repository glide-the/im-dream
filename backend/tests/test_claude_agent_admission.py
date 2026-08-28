# [Input] Consume claude_agent/admission.py and the existing thread factory/EventBus path.
# [Output] Verify safe resource config, concurrency, host/cgroup memory preflight, retryable
#          SSE errors, missing-metric fallback, and idempotent lease release.
# [Pos] resource-admission test node in backend/tests.
# [Sync] 2026-08-28: cover shared safe-integer/combined-memory replacement boundaries
#                    without changing admission ordering, live leases, cancellation, or SSE.

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
    AGENT_RESOURCE_JSON_SAFE_INTEGER_MAX,
    AGENT_RESOURCE_MAX_COMBINED_MEMORY_MIB,
    AgentAdmissionConfig,
    AgentResourceSnapshot,
    ClaudeAgentAdmissionController,
    ClaudeAgentAdmissionError,
    read_agent_resource_snapshot,
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

    def test_reclaimable_cgroup_cache_admits_one_turn(self):
        controller = ClaudeAgentAdmissionController(
            _config(),
            snapshot_provider=lambda: AgentResourceSnapshot(
                host_available_bytes=2 * 1024 * _MIB,
                cgroup_current_bytes=1940 * _MIB,
                cgroup_max_bytes=2048 * _MIB,
                cgroup_reclaimable_bytes=700 * _MIB,
            ),
        )

        lease = controller.try_acquire("thread-cache-pressure")

        stats = controller.stats()
        self.assertEqual(stats["cgroup_raw_headroom_mib"], 108)
        self.assertEqual(stats["cgroup_reclaimable_mib"], 700)
        self.assertEqual(stats["cgroup_headroom_mib"], 808)
        lease.release()

    def test_resource_snapshot_reads_only_reclaimable_cgroup_classes(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            cgroup = Path(directory)
            (cgroup / "memory.current").write_text(str(1900 * _MIB))
            (cgroup / "memory.max").write_text(str(2048 * _MIB))
            (cgroup / "memory.stat").write_text(
                "inactive_file 314572800\n"
                "active_file 734003200\n"
                "slab_reclaimable 209715200\n"
                "slab_unreclaimable 104857600\n"
            )
            with unittest.mock.patch(
                "claude_agent.admission._cgroup_v2_directory",
                return_value=cgroup,
            ), unittest.mock.patch(
                "claude_agent.admission._read_host_available_bytes",
                return_value=3 * 1024 * _MIB,
            ):
                snapshot = read_agent_resource_snapshot()

        self.assertEqual(snapshot.cgroup_raw_headroom_bytes, 148 * _MIB)
        self.assertEqual(snapshot.cgroup_reclaimable_bytes, 500 * _MIB)
        self.assertEqual(snapshot.cgroup_headroom_bytes, 648 * _MIB)

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

    def test_env_accepts_values_above_historical_product_caps(self):
        with unittest.mock.patch.dict(
            "os.environ",
            {
                "INK_AGENT_MAX_CONCURRENT_RUNS": "17",
                "INK_AGENT_RUN_MEMORY_BUDGET_MIB": "8193",
                "INK_AGENT_MEMORY_RESERVE_MIB": "4097",
                "INK_AGENT_SWEEP_INTERVAL_S": "3601",
            },
            clear=True,
        ):
            config = AgentAdmissionConfig.from_env()

        self.assertEqual(config, AgentAdmissionConfig(17, 8_193, 4_097, 3_601))

    def test_env_accepts_safe_and_combined_memory_exact_boundaries(self):
        with unittest.mock.patch.dict(
            "os.environ",
            {
                "INK_AGENT_MAX_CONCURRENT_RUNS": str(
                    AGENT_RESOURCE_JSON_SAFE_INTEGER_MAX
                ),
                "INK_AGENT_RUN_MEMORY_BUDGET_MIB": str(
                    AGENT_RESOURCE_MAX_COMBINED_MEMORY_MIB - 1
                ),
                "INK_AGENT_MEMORY_RESERVE_MIB": "1",
                "INK_AGENT_SWEEP_INTERVAL_S": str(
                    AGENT_RESOURCE_JSON_SAFE_INTEGER_MAX
                ),
            },
            clear=True,
        ):
            config = AgentAdmissionConfig.from_env()

        self.assertEqual(
            config.required_headroom_bytes,
            AGENT_RESOURCE_MAX_COMBINED_MEMORY_MIB * _MIB,
        )

    def test_env_rejects_safe_integer_and_combined_memory_overflow(self):
        invalid_environments = (
            {
                "INK_AGENT_MAX_CONCURRENT_RUNS": str(
                    AGENT_RESOURCE_JSON_SAFE_INTEGER_MAX + 1
                )
            },
            {"INK_AGENT_MEMORY_RESERVE_MIB": "0"},
            {
                "INK_AGENT_RUN_MEMORY_BUDGET_MIB": str(
                    AGENT_RESOURCE_MAX_COMBINED_MEMORY_MIB
                ),
                "INK_AGENT_MEMORY_RESERVE_MIB": "1",
            },
        )
        for environment in invalid_environments:
            with self.subTest(environment=environment), unittest.mock.patch.dict(
                "os.environ",
                environment,
                clear=True,
            ):
                with self.assertRaises(ValueError):
                    AgentAdmissionConfig.from_env()

    def test_invalid_concurrency_env_fails_closed(self):
        invalid_values = (
            "0",
            "-1",
            "1.5",
            "not-an-integer",
        )
        for raw in invalid_values:
            with self.subTest(raw=raw), unittest.mock.patch.dict(
                "os.environ",
                {"INK_AGENT_MAX_CONCURRENT_RUNS": raw},
                clear=True,
            ):
                with self.assertRaises(ValueError):
                    AgentAdmissionConfig.from_env()

    def test_lower_live_concurrency_only_changes_future_acquisitions(self):
        controller = ClaudeAgentAdmissionController(
            _config(max_runs=2),
            snapshot_provider=AgentResourceSnapshot,
        )
        existing = controller.try_acquire("thread-existing")
        replacement = AgentAdmissionConfig(
            max_concurrent_runs=1,
            run_memory_budget_mib=640,
            memory_reserve_mib=192,
            retry_after_seconds=90,
        )

        previous = controller.replace_config(replacement)

        self.assertEqual(previous, _config(max_runs=2))
        self.assertEqual(controller.stats()["active_runs"], 1)
        with self.assertRaises(ClaudeAgentAdmissionError) as caught:
            controller.try_acquire("thread-future")
        self.assertEqual(caught.exception.retry_after_seconds, 90)
        existing.release()
        future = controller.try_acquire("thread-future")
        future.release()

    def test_invalid_live_config_replacement_preserves_current_config(self):
        controller = ClaudeAgentAdmissionController(_config())

        with self.assertRaises(TypeError):
            controller.replace_config(object())  # type: ignore[arg-type]

        self.assertEqual(controller.config, _config())

    def test_public_config_boundary_rejects_invalid_values_for_every_field(self):
        fields = (
            "max_concurrent_runs",
            "run_memory_budget_mib",
            "memory_reserve_mib",
            "retry_after_seconds",
        )
        invalid_values = (
            0,
            -1,
            1.5,
            True,
            None,
            "1",
            AGENT_RESOURCE_JSON_SAFE_INTEGER_MAX + 1,
        )
        valid = {
            "max_concurrent_runs": 1,
            "run_memory_budget_mib": 512,
            "memory_reserve_mib": 128,
            "retry_after_seconds": 60,
        }
        for field in fields:
            for value in invalid_values:
                values = {**valid, field: value}
                invalid = AgentAdmissionConfig(**values)  # type: ignore[arg-type]
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        ClaudeAgentAdmissionController(invalid)
                    controller = ClaudeAgentAdmissionController(_config())
                    with self.assertRaises(ValueError):
                        controller.replace_config(invalid)
                    self.assertEqual(controller.config, _config())

    def test_public_config_boundary_accepts_technical_maxima(self):
        maximum = AgentAdmissionConfig(
            max_concurrent_runs=AGENT_RESOURCE_JSON_SAFE_INTEGER_MAX,
            run_memory_budget_mib=AGENT_RESOURCE_MAX_COMBINED_MEMORY_MIB - 1,
            memory_reserve_mib=1,
            retry_after_seconds=AGENT_RESOURCE_JSON_SAFE_INTEGER_MAX,
        )
        controller = ClaudeAgentAdmissionController(maximum)

        self.assertEqual(controller.config, maximum)
        self.assertLessEqual(
            controller.config.required_headroom_bytes,
            AGENT_RESOURCE_JSON_SAFE_INTEGER_MAX,
        )

    def test_public_config_boundary_rejects_combined_memory_plus_one(self):
        invalid = AgentAdmissionConfig(
            max_concurrent_runs=1,
            run_memory_budget_mib=AGENT_RESOURCE_MAX_COMBINED_MEMORY_MIB,
            memory_reserve_mib=1,
            retry_after_seconds=1,
        )
        with self.assertRaises(ValueError):
            ClaudeAgentAdmissionController(invalid)
        controller = ClaudeAgentAdmissionController(_config())
        with self.assertRaises(ValueError):
            controller.replace_config(invalid)
        self.assertEqual(controller.config, _config())


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
