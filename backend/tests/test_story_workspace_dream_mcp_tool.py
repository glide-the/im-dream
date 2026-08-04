"""Controlled Story Workspace MCP seam for Dream runtime file writes."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
from libs.claude_agent_kit.server.story_workspace_mcp_server import (
    create_story_workspace_mcp_server,
)
from libs.claude_agent_kit.server.story_workspace_tool import (
    STORY_WORKSPACE_DREAM_TOOL_SPECS,
    allowed_story_workspace_tool_names,
    handle_story_workspace_dream_tool,
)


RUN_ID = "run_0123456789abcdef0123456789abcdef"
THREAD_ID = "thread-dream-mcp"


class StoryWorkspaceDreamMcpToolTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.workspace_root = self.root / "workspaces"
        self.workspace = self.workspace_root / THREAD_ID
        self.workspace.mkdir(parents=True)
        (self.workspace / ".dream").mkdir()
        (self.workspace / "assets" / "characters").mkdir(parents=True)
        (self.workspace / "assets" / "characters" / "lead.md").write_text(
            "# Lead\n", encoding="utf-8"
        )
        self.database_path = self.root / "test.db"
        self.statements: list[str] = []
        db = sqlite3.connect(self.database_path)
        try:
            db.executescript(
                """
                CREATE TABLE story_workspace_workspaces (
                    id TEXT PRIMARY KEY,
                    owner_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE chat_thread (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL
                );
                CREATE TABLE workflow_runs (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    deck_plugin_id TEXT NOT NULL,
                    deck_plugin_version TEXT NOT NULL,
                    workflow_definition_ref TEXT NOT NULL,
                    deck_runtime_snapshot_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    failed_step TEXT,
                    error_code TEXT,
                    retry_of_run_id TEXT,
                    deck_plugin_manifest_hash TEXT NOT NULL,
                    deck_plugin_binding_id TEXT NOT NULL,
                    binding_revision INTEGER NOT NULL,
                    runtime_plugin_lock_id TEXT NOT NULL,
                    runtime_load_receipt_id TEXT,
                    workflow_preflight_id TEXT NOT NULL,
                    agent_session_id TEXT,
                    source_voice_thread_id TEXT,
                    source_message_id TEXT,
                    source_message_time TEXT,
                    idempotency_key TEXT NOT NULL,
                    input_hash TEXT NOT NULL,
                    semantic_fingerprint TEXT NOT NULL,
                    status_version INTEGER NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT
                );
                """
            )
            db.execute(
                "INSERT INTO story_workspace_workspaces (id, owner_id, created_at) "
                "VALUES (?, ?, ?)",
                ("workspace-1", 7, "2026-08-04T00:00:00+00:00"),
            )
            db.execute(
                "INSERT INTO chat_thread (id, user_id) VALUES (?, ?)",
                (THREAD_ID, 7),
            )
            db.execute(
                """
                INSERT INTO workflow_runs (
                    id, workspace_id, deck_plugin_id, deck_plugin_version,
                    workflow_definition_ref, deck_runtime_snapshot_id, status,
                    failed_step, error_code, retry_of_run_id,
                    deck_plugin_manifest_hash, deck_plugin_binding_id,
                    binding_revision, runtime_plugin_lock_id,
                    runtime_load_receipt_id, workflow_preflight_id,
                    agent_session_id, source_voice_thread_id, source_message_id,
                    source_message_time, idempotency_key, input_hash,
                    semantic_fingerprint, status_version, created_by, created_at,
                    started_at, completed_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?, ?, ?, NULL,
                    ?, NULL, ?, NULL, NULL, ?, ?, ?, ?, ?, ?, NULL, NULL
                )
                """,
                (
                    RUN_ID,
                    "workspace-1",
                    "plugin-1",
                    "1.2.3",
                    "workflow-1",
                    "snapshot-1",
                    "preflight",
                    "sha256:" + "1" * 64,
                    "binding-1",
                    3,
                    "lock-1",
                    "pf_" + "2" * 32,
                    THREAD_ID,
                    "idempotency-1",
                    "sha256:" + "3" * 64,
                    "sha256:" + "4" * 64,
                    1,
                    "7",
                    "2026-08-04T00:00:00+00:00",
                ),
            )
            db.commit()
        finally:
            db.close()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _open_db(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.database_path)
        db.row_factory = sqlite3.Row
        db.set_trace_callback(self.statements.append)
        return db

    def _call(
        self,
        tool_name: str,
        arguments: dict[str, object],
        *,
        actor_id: str = "7",
        thread_id: str = THREAD_ID,
    ) -> dict[str, object]:
        with (
            patch.object(database, "get_db", side_effect=self._open_db),
            patch(
                "libs.claude_agent_kit.server.story_workspace_tool.get_workspace_root",
                return_value=self.workspace_root,
            ),
            patch.dict(
                os.environ,
                {
                    "INK_AGENT_USER_ID": actor_id,
                    "INK_AGENT_THREAD_ID": thread_id,
                },
            ),
        ):
            return json.loads(
                handle_story_workspace_dream_tool(tool_name, arguments)
            )

    def test_tool_contract_exposes_only_non_forgeable_arguments(self) -> None:
        self.assertEqual(
            set(STORY_WORKSPACE_DREAM_TOOL_SPECS),
            {"write_dream_run", "write_dream_stage"},
        )
        self.assertEqual(
            set(allowed_story_workspace_tool_names()),
            {
                "mcp__story_workspace__write_dream_run",
                "mcp__story_workspace__write_dream_stage",
            },
        )
        forbidden = {
            "actorId",
            "threadId",
            "deckPluginBindingId",
            "bindingRevision",
            "deckPluginVersion",
            "deckRuntimeSnapshotId",
            "runtimePluginLockId",
        }
        for spec in STORY_WORKSPACE_DREAM_TOOL_SPECS.values():
            schema = spec.input_schema
            self.assertFalse(forbidden & set(schema["properties"]))
            self.assertFalse(schema["additionalProperties"])

        server = create_story_workspace_mcp_server()
        self.assertEqual(server.name, "story_workspace")

    def test_real_run_and_stage_writes_return_minimal_json(self) -> None:
        run_result = self._call(
            "write_dream_run",
            {"workflowRunId": RUN_ID, "expectedRevision": 0},
        )
        self.assertEqual(
            run_result,
            {"changedStages": [], "revision": 1, "run": RUN_ID},
        )
        stage_result = self._call(
            "write_dream_stage",
            {
                "workflowRunId": RUN_ID,
                "stage": "characters",
                "sourceFiles": ["assets/characters/lead.md"],
                "items": [
                    {
                        "entityId": "character-1",
                        "displayName": "Lead",
                        "summary": "Protagonist",
                        "sourceFile": "assets/characters/lead.md",
                        "relations": [],
                    }
                ],
                "expectedRevision": 0,
            },
        )
        self.assertEqual(
            stage_result,
            {
                "changedStages": ["characters"],
                "revision": 1,
                "run": RUN_ID,
                "stage": "characters",
            },
        )
        persisted = json.loads(
            (
                self.workspace
                / ".dream"
                / "runtime"
                / "runs"
                / RUN_ID
                / "stages"
                / "characters.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            persisted["items"][0]["source_file"],
            "assets/characters/lead.md",
        )
        self.assertFalse(
            any(statement.lstrip().upper().startswith("CREATE ") for statement in self.statements)
        )

    def test_cross_thread_cross_actor_and_forgeable_inputs_fail_closed(self) -> None:
        runtime = self.workspace / ".dream" / "runtime"
        for actor_id, thread_id, extra in (
            ("7", "different-thread", {}),
            ("8", THREAD_ID, {}),
            ("7", THREAD_ID, {"threadId": THREAD_ID}),
            ("7", THREAD_ID, {"deckPluginVersion": "forged"}),
        ):
            with self.subTest(actor_id=actor_id, thread_id=thread_id, extra=extra):
                result = self._call(
                    "write_dream_run",
                    {
                        "workflowRunId": RUN_ID,
                        "expectedRevision": 0,
                        **extra,
                    },
                    actor_id=actor_id,
                    thread_id=thread_id,
                )
                self.assertEqual(result, {"error": "DREAM_WRITE_REJECTED"})
                self.assertNotIn(str(self.workspace), json.dumps(result))
                self.assertFalse(runtime.exists())

    def test_cas_conflict_is_sanitized_and_does_not_advance_revision(self) -> None:
        first = self._call(
            "write_dream_run",
            {"workflowRunId": RUN_ID, "expectedRevision": 0},
        )
        second = self._call(
            "write_dream_run",
            {"workflowRunId": RUN_ID, "expectedRevision": 0},
        )
        self.assertEqual(first["revision"], 1)
        self.assertEqual(second, {"error": "DREAM_WRITE_REJECTED"})
        run_payload = json.loads(
            (
                self.workspace
                / ".dream"
                / "runtime"
                / "runs"
                / RUN_ID
                / "run.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(run_payload["revision"], 1)

    def test_missing_workspace_or_run_never_creates_or_guesses(self) -> None:
        missing_thread = "thread-does-not-exist"
        result = self._call(
            "write_dream_run",
            {"workflowRunId": "run_" + "f" * 32, "expectedRevision": 0},
            thread_id=missing_thread,
        )
        self.assertEqual(result, {"error": "DREAM_WRITE_REJECTED"})
        self.assertFalse((self.workspace_root / missing_thread).exists())
        self.assertFalse((self.workspace / ".dream" / "runtime").exists())
        self.assertFalse(
            any(
                statement.lstrip().upper().startswith(("CREATE ", "INSERT ", "UPDATE "))
                for statement in self.statements
            )
        )


if __name__ == "__main__":
    unittest.main()
