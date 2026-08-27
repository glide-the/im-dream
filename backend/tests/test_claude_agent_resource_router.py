# [Input] Consume the internal resource router, dedicated diagnostics bearer env, and closed DTO.
# [Output] Verify missing/wrong/correct token behavior and exact response field privacy.
# [Pos] Internal Claude Agent diagnostics route tests in backend/tests.
# [Sync] 2026-08-27: add constant-time bearer authentication and safe response coverage.

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tests._sdk_stubs  # noqa: F401

from fastapi import FastAPI
from fastapi.testclient import TestClient

from claude_agent.resource_diagnostics import ClaudeAgentResourceDiagnosticsDTO
from routers import claude_agent_resources


def _payload() -> dict:
    return {
        "schema_version": 1,
        "backend_status": "ok",
        "scope": {
            "active_runs": "process",
            "counters": "process_lifetime",
            "reset_on_restart": True,
        },
        "config": {
            "defaults": {
                "max_concurrent_runs": 1,
                "run_memory_budget_mib": 512,
                "memory_reserve_mib": 128,
                "retry_after_seconds": 60,
                "required_headroom_bytes": 671088640,
            },
            "environment": {
                "max_concurrent_runs": None,
                "run_memory_budget_mib": None,
                "memory_reserve_mib": None,
                "retry_after_seconds": None,
            },
            "effective": {
                "max_concurrent_runs": 1,
                "run_memory_budget_mib": 512,
                "memory_reserve_mib": 128,
                "retry_after_seconds": 60,
                "required_headroom_bytes": 671088640,
            },
            "effective_version": "0" * 64,
            "loaded_at": "2026-08-27T00:00:00Z",
            "restart_required": False,
        },
        "turns": {
            "started_total": 0,
            "completed_total": 0,
            "failed_total": 0,
            "cancelled_total": 0,
        },
        "admission": {
            "active_runs": 0,
            "max_concurrent_runs": 1,
            "granted_total": 0,
            "capacity_denials_total": 0,
            "memory_pressure_denials_total": 0,
            "last_denial_type": None,
            "last_denial_at": None,
            "can_start_new_agent": True,
        },
        "claude_processes": {"available": True, "count": 0, "total_rss_bytes": 0},
        "memory": {
            "host_available_bytes": None,
            "cgroup_current_bytes": None,
            "cgroup_max_bytes": None,
            "cgroup_raw_headroom_bytes": None,
            "inactive_file_bytes": None,
            "slab_reclaimable_bytes": None,
            "cgroup_reclaimable_bytes": None,
            "cgroup_effective_headroom_bytes": None,
            "required_headroom_bytes": 671088640,
            "events": {"low": None, "high": None, "max": None, "oom": None, "oom_kill": None},
        },
        "sample": {
            "status": "ok",
            "sampled_at": "2026-08-27T00:00:00Z",
            "age_seconds": 0.0,
            "stale": False,
            "error_code": None,
        },
    }


class TestClaudeAgentResourceRouter(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.include_router(claude_agent_resources.router)
        self.client = TestClient(app)
        self.diagnostics = SimpleNamespace(
            snapshot=lambda: ClaudeAgentResourceDiagnosticsDTO.model_validate(_payload())
        )
        self.patch = mock.patch.object(
            claude_agent_resources,
            "claude_agent_resource_diagnostics",
            self.diagnostics,
        )
        self.patch.start()

    def tearDown(self) -> None:
        self.patch.stop()
        self.client.close()

    def test_missing_server_token_fails_closed(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            response = self.client.get("/api/internal/claude-agent/resources")
        self.assertEqual(response.status_code, 503)

        with mock.patch.dict(
            os.environ, {"INK_AGENT_DIAGNOSTICS_TOKEN": "x" * 31}, clear=True
        ):
            weak = self.client.get("/api/internal/claude-agent/resources")
        self.assertEqual(weak.status_code, 503)

    def test_missing_or_wrong_bearer_is_unauthorized(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"INK_AGENT_DIAGNOSTICS_TOKEN": "dedicated-diagnostics-secret-value"},
            clear=True,
        ):
            missing = self.client.get("/api/internal/claude-agent/resources")
            wrong = self.client.get(
                "/api/internal/claude-agent/resources",
                headers={"Authorization": "Bearer wrong"},
            )
        self.assertEqual(missing.status_code, 401)
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(wrong.headers["www-authenticate"], "Bearer")

    def test_correct_bearer_returns_only_closed_dto(self) -> None:
        token = "dedicated-diagnostics-secret-value"
        with mock.patch.dict(
            os.environ, {"INK_AGENT_DIAGNOSTICS_TOKEN": token}, clear=True
        ):
            response = self.client.get(
                "/api/internal/claude-agent/resources",
                headers={"Authorization": f"Bearer {token}"},
            )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(set(payload), set(_payload()))
        serialized = response.text.lower()
        for forbidden in ("thread_id", "session_id", "prompt", "authorization", token):
            self.assertNotIn(forbidden, serialized)
