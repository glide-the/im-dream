# [Input] Consume Linux resource sampler, public admission snapshots, Observer counters, and DTO projector.
# [Output] Verify cgroup/proc absence, Claude RSS aggregation, staleness, errors, and DTO privacy/shape.
# [Pos] Focused resource diagnostics tests in backend/tests.
# [Sync] 2026-08-27: add provider-free Linux sampler and closed diagnostics DTO coverage.

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tests._sdk_stubs  # noqa: F401

from claude_agent.admission import (
    AgentAdmissionConfig,
    AgentResourceSnapshot,
    ClaudeAgentAdmissionController,
    read_agent_resource_snapshot,
)
from claude_agent.resource_diagnostics import (
    ClaudeAgentResourceDiagnostics,
    ClaudeAgentResourceSampler,
    ClaudeProcessSnapshot,
    ResourceSample,
    read_claude_process_snapshot,
)
from claude_agent.resource_observer import (
    ClaudeAgentResourceObserver,
    ObservedClaudeAgentAdmissionController,
)


_MIB = 1024 * 1024


def _write_proc_process(
    root: Path,
    pid: int,
    *,
    parent_pid: int,
    rss_kib: int,
    executable: str,
) -> None:
    process = root / str(pid)
    process.mkdir()
    (process / "status").write_text(
        f"Name:\ttest\nPid:\t{pid}\nPPid:\t{parent_pid}\nVmRSS:\t{rss_kib} kB\n",
        encoding="utf-8",
    )
    os.symlink(f"/runtime/{executable}", process / "exe")


class TestLinuxResourceReads(unittest.TestCase):
    def test_missing_host_and_cgroup_metrics_are_unavailable(self) -> None:
        with mock.patch(
            "claude_agent.admission._cgroup_v2_directory", return_value=None
        ), mock.patch(
            "claude_agent.admission._read_host_available_bytes", return_value=None
        ):
            snapshot = read_agent_resource_snapshot()
        self.assertFalse(snapshot.metrics_available)
        self.assertIsNone(snapshot.cgroup_current_bytes)
        self.assertIsNone(snapshot.cgroup_event_oom_kill)

    def test_cgroup_fields_and_memory_events_are_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cgroup = Path(directory)
            (cgroup / "memory.current").write_text(str(900 * _MIB))
            (cgroup / "memory.max").write_text(str(1024 * _MIB))
            (cgroup / "memory.stat").write_text(
                "inactive_file 209715200\nslab_reclaimable 52428800\n"
            )
            (cgroup / "memory.events").write_text(
                "low 1\nhigh 2\nmax 3\noom 4\noom_kill 5\n"
            )
            with mock.patch(
                "claude_agent.admission._cgroup_v2_directory", return_value=cgroup
            ), mock.patch(
                "claude_agent.admission._read_host_available_bytes",
                return_value=2048 * _MIB,
            ):
                snapshot = read_agent_resource_snapshot()

        self.assertEqual(snapshot.cgroup_raw_headroom_bytes, 124 * _MIB)
        self.assertEqual(snapshot.cgroup_inactive_file_bytes, 200 * _MIB)
        self.assertEqual(snapshot.cgroup_slab_reclaimable_bytes, 50 * _MIB)
        self.assertEqual(snapshot.cgroup_reclaimable_bytes, 250 * _MIB)
        self.assertEqual(snapshot.cgroup_headroom_bytes, 374 * _MIB)
        self.assertEqual(
            (
                snapshot.cgroup_event_low,
                snapshot.cgroup_event_high,
                snapshot.cgroup_event_max,
                snapshot.cgroup_event_oom,
                snapshot.cgroup_event_oom_kill,
            ),
            (1, 2, 3, 4, 5),
        )

    def test_proc_absent_is_unavailable(self) -> None:
        snapshot = read_claude_process_snapshot(
            proc_root=Path("/definitely/missing/proc"),
            backend_pid=100,
            executable_names={"ink-claude-code-dream"},
        )
        self.assertFalse(snapshot.available)
        self.assertIsNone(snapshot.count)
        self.assertIsNone(snapshot.total_rss_bytes)

    def test_only_backend_descendant_claude_executables_are_aggregated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory)
            _write_proc_process(proc, 100, parent_pid=1, rss_kib=50, executable="python")
            _write_proc_process(
                proc, 200, parent_pid=100, rss_kib=10, executable="ink-claude-code-dream"
            )
            _write_proc_process(proc, 201, parent_pid=200, rss_kib=20, executable="claude")
            _write_proc_process(proc, 202, parent_pid=100, rss_kib=30, executable="python")
            _write_proc_process(proc, 300, parent_pid=1, rss_kib=40, executable="claude")
            snapshot = read_claude_process_snapshot(
                proc_root=proc,
                backend_pid=100,
                executable_names={"ink-claude-code-dream", "claude"},
            )
        self.assertTrue(snapshot.available)
        self.assertEqual(snapshot.count, 2)
        self.assertEqual(snapshot.total_rss_bytes, 30 * 1024)


class TestResourceSampler(unittest.IsolatedAsyncioTestCase):
    async def test_sampler_error_is_isolated(self) -> None:
        sampler = ClaudeAgentResourceSampler()
        with mock.patch.object(
            sampler, "_sample_sync", side_effect=OSError("unavailable")
        ):
            await sampler.sample_once()
        snapshot = sampler.snapshot()
        self.assertEqual(snapshot.status, "error")
        self.assertEqual(snapshot.error_code, "sample_error")
        self.assertTrue(snapshot.stale)

    async def test_timeout_and_staleness_are_isolated(self) -> None:
        sampler = ClaudeAgentResourceSampler(
            timeout_seconds=0.01,
            stale_after_seconds=0.02,
            interval_seconds=0.01,
        )

        def blocked():
            time.sleep(0.1)
            return ResourceSample(
                memory=AgentResourceSnapshot(),
                claude_processes=ClaudeProcessSnapshot(available=False),
            )

        with mock.patch.object(sampler, "_sample_sync", side_effect=blocked):
            await sampler.sample_once()
        snapshot = sampler.snapshot()
        self.assertEqual(snapshot.status, "timeout")
        self.assertEqual(snapshot.error_code, "sample_timeout")
        self.assertTrue(snapshot.stale)

    async def test_successful_sample_becomes_stale(self) -> None:
        sampler = ClaudeAgentResourceSampler(
            stale_after_seconds=0.01,
            interval_seconds=0.01,
        )
        sample = ResourceSample(
            memory=AgentResourceSnapshot(host_available_bytes=1024 * _MIB),
            claude_processes=ClaudeProcessSnapshot(
                available=True, count=0, total_rss_bytes=0
            ),
        )
        with mock.patch.object(sampler, "_sample_sync", return_value=sample):
            await sampler.sample_once()
        self.assertFalse(sampler.snapshot().stale)
        await asyncio.sleep(0.02)
        self.assertTrue(sampler.snapshot().stale)


class TestDiagnosticsDTO(unittest.TestCase):
    def test_closed_dto_contains_no_business_or_credential_fields(self) -> None:
        config = AgentAdmissionConfig(
            max_concurrent_runs=1,
            run_memory_budget_mib=512,
            memory_reserve_mib=128,
            retry_after_seconds=60,
        )
        observer = ClaudeAgentResourceObserver()
        admission = ObservedClaudeAgentAdmissionController(
            ClaudeAgentAdmissionController(
                config,
                snapshot_provider=lambda: AgentResourceSnapshot(
                    host_available_bytes=2048 * _MIB
                ),
            ),
            observer,
        )
        sampler = ClaudeAgentResourceSampler()
        sampler._status = "ok"
        sampler._sampled_at = "2026-08-27T00:00:00Z"
        sampler._sampled_monotonic = time.monotonic()
        sampler._sample = ResourceSample(
            memory=AgentResourceSnapshot(
                host_available_bytes=2048 * _MIB,
                cgroup_current_bytes=100 * _MIB,
                cgroup_max_bytes=2048 * _MIB,
                cgroup_reclaimable_bytes=50 * _MIB,
            ),
            claude_processes=ClaudeProcessSnapshot(
                available=True, count=1, total_rss_bytes=200 * _MIB
            ),
        )
        diagnostics = ClaudeAgentResourceDiagnostics(
            admission=admission,
            observer=observer,
            sampler=sampler,
        )
        with mock.patch.dict(os.environ, {}, clear=True):
            payload = diagnostics.snapshot().model_dump()

        self.assertEqual(
            set(payload),
            {
                "schema_version",
                "backend_status",
                "scope",
                "config",
                "turns",
                "admission",
                "claude_processes",
                "memory",
                "sample",
            },
        )
        serialized = repr(payload).lower()
        for forbidden in (
            "session_id",
            "thread_id",
            "prompt",
            "transcript",
            "authorization",
            "cookie",
            "token",
            "cmdline",
        ):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(payload["scope"]["active_runs"], "process")
        self.assertTrue(payload["scope"]["reset_on_restart"])
        self.assertTrue(payload["admission"]["can_start_new_agent"])

    def test_invalid_post_start_env_is_redacted_and_requires_restart(self) -> None:
        config = AgentAdmissionConfig.defaults()
        observer = ClaudeAgentResourceObserver()
        admission = ObservedClaudeAgentAdmissionController(
            ClaudeAgentAdmissionController(
                config,
                snapshot_provider=AgentResourceSnapshot,
            ),
            observer,
        )
        sampler = ClaudeAgentResourceSampler()
        diagnostics = ClaudeAgentResourceDiagnostics(
            admission=admission,
            observer=observer,
            sampler=sampler,
        )
        with mock.patch.dict(
            os.environ,
            {"INK_AGENT_MAX_CONCURRENT_RUNS": "not-an-integer"},
            clear=True,
        ):
            payload = diagnostics.snapshot().model_dump()
        self.assertIsNone(payload["config"]["environment"]["max_concurrent_runs"])
        self.assertTrue(payload["config"]["restart_required"])
