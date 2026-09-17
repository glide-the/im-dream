# [Input] Real private broker, synthetic current WorkflowRun provider and an owned thread workspace.
# [Output] Successful controlled file write, mismatch/no-write and database-path closure evidence.
# [Pos] Provider-free Story Workspace stdio projection tests; no Admin, PostgreSQL or model.
# [Sync] 2026-09-16: verify Story Workspace consumes the turn-owned Admin Run projection.
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from models.workflow_run import RunStatus, WorkflowRun
from services.admin_data.session_models import SessionListResultDTO
from services.admin_data.session_projection_broker import (
    SessionProjectionBroker,
    SessionProjectionBrokerSettings,
)
import libs.claude_agent_kit.server.story_workspace_tool as story_tool


RUN_ID = "run_" + "a" * 32


def _run(**overrides) -> WorkflowRun:
    values = {
        "workflow_run_id": RUN_ID,
        "deck_plugin_id": "plugin-1",
        "deck_plugin_version": "1.0.0",
        "workflow_definition_ref": "workflow-1",
        "deck_runtime_snapshot_id": "snapshot-1",
        "status": RunStatus.PREFLIGHT,
        "deck_plugin_manifest_hash": "sha256:" + "1" * 64,
        "deck_plugin_binding_id": "binding-1",
        "binding_revision": 1,
        "runtime_plugin_lock_id": "lock-1",
        "workflow_preflight_id": "pf_" + "2" * 32,
        "source_voice_thread_id": "thread-1",
        "source_message_id": "message-1",
        "source_message_time": datetime(2026, 9, 16, tzinfo=timezone.utc),
        "workspace_id": "workspace-1",
        "idempotency_key": "run-request-1",
        "input_hash": "sha256:" + "3" * 64,
        "semantic_fingerprint": "sha256:" + "4" * 64,
        "status_version": 1,
        "created_by": "42",
        "created_at": datetime(2026, 9, 16, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return WorkflowRun.model_validate(values)


class _SessionProvider:
    def list_sessions(self, input_dto, request_id):
        return SessionListResultDTO(sessions=[])


class _RunProvider:
    def __init__(self, run: WorkflowRun):
        self.run = run
        self.calls: list[str] = []

    def current_workflow_run(self, request_id: str) -> WorkflowRun:
        self.calls.append(request_id)
        return self.run


def _start(run: WorkflowRun):
    provider = _RunProvider(run)
    broker = SessionProjectionBroker(
        _SessionProvider(),
        workflow_run_provider=provider,
        settings=SessionProjectionBrokerSettings(
            timeout_seconds=0.5,
            max_bytes=8192,
        ),
    )
    broker.start()
    return broker, provider


def _bind(monkeypatch, tmp_path: Path, broker: SessionProjectionBroker) -> Path:
    root = tmp_path / "workspaces"
    workspace = root / "thread-1"
    (workspace / ".dream").mkdir(parents=True)
    monkeypatch.setattr(story_tool, "get_workspace_root", lambda: root)
    for name, value in {
        "INK_AGENT_USER_ID": "42",
        "INK_AGENT_THREAD_ID": "thread-1",
        "INK_AGENT_WORKFLOW_RUN_ID": RUN_ID,
        **broker.child_env(),
    }.items():
        monkeypatch.setenv(name, value)
    return workspace


def test_run_write_uses_current_projection_and_preserves_cas(monkeypatch, tmp_path):
    broker, provider = _start(_run())
    try:
        workspace = _bind(monkeypatch, tmp_path, broker)
        source = workspace / "assets" / "characters" / "lead.md"
        source.parent.mkdir(parents=True)
        source.write_text("# Lead\n", encoding="utf-8")
        request = {"workflowRunId": RUN_ID, "expectedRevision": 0}

        first = json.loads(
            story_tool.story_workspace_handle_dream_tool("write_dream_run", request)
        )
        stage = json.loads(
            story_tool.story_workspace_handle_dream_tool(
                "write_dream_stage",
                {
                    "workflowRunId": RUN_ID,
                    "stage": "characters",
                    "sourceFiles": ["assets/characters/lead.md"],
                    "items": [
                        {
                            "entityId": "lead",
                            "displayName": "Lead",
                            "summary": "main character",
                            "sourceFile": "assets/characters/lead.md",
                            "relations": [],
                        }
                    ],
                    "expectedRevision": 0,
                },
            )
        )
        before = (workspace / ".dream" / "runtime" / "runs" / RUN_ID / "run.json").read_bytes()
        conflict = json.loads(
            story_tool.story_workspace_handle_dream_tool("write_dream_run", request)
        )

        assert first == {"changedStages": [], "revision": 1, "run": RUN_ID}
        assert stage == {
            "changedStages": ["characters"],
            "revision": 1,
            "run": RUN_ID,
            "stage": "characters",
        }
        assert conflict == {"error": "DREAM_WRITE_REJECTED"}
        assert (workspace / ".dream" / "runtime" / "runs" / RUN_ID / "run.json").read_bytes() == before
        assert len(provider.calls) == 3
    finally:
        broker.close()


def test_mismatched_projection_fails_before_any_runtime_file_write(monkeypatch, tmp_path):
    broker, provider = _start(_run(created_by="43"))
    try:
        workspace = _bind(monkeypatch, tmp_path, broker)

        result = json.loads(
            story_tool.story_workspace_handle_dream_tool(
                "write_dream_run",
                {"workflowRunId": RUN_ID, "expectedRevision": 0},
            )
        )

        assert result == {"error": "DREAM_WRITE_REJECTED"}
        assert provider.calls
        assert not (workspace / ".dream" / "runtime").exists()
    finally:
        broker.close()


def test_closed_broker_fails_without_database_fallback_or_file_write(
    monkeypatch,
    tmp_path,
):
    broker, _provider = _start(_run())
    workspace = _bind(monkeypatch, tmp_path, broker)
    broker.close()

    result = json.loads(
        story_tool.story_workspace_handle_dream_tool(
            "write_dream_run",
            {"workflowRunId": RUN_ID, "expectedRevision": 0},
        )
    )

    assert result == {"error": "DREAM_WRITE_REJECTED"}
    assert not (workspace / ".dream" / "runtime").exists()


def test_story_workspace_tool_source_has_no_database_or_sql_read_path():
    source = Path(story_tool.__file__).read_text(encoding="utf-8")
    blocked = (
        "import database",
        "database.get_db",
        "WorkflowRunService",
        "psycopg",
        "SELECT ",
        ".execute(",
    )
    assert all(marker not in source for marker in blocked)
    assert "current_workflow_run" in source
