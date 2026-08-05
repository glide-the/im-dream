"""Controlled Story Workspace MCP seam for Dream runtime file writes."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import database
from libs.claude_agent_kit.server import story_workspace_tool
from libs.claude_agent_kit.server.story_workspace_mcp_server import (
    story_workspace_create_mcp_server,
)
from libs.claude_agent_kit.server.story_workspace_tool import (
    STORY_WORKSPACE_DREAM_TOOL_SPECS,
    story_workspace_allowed_tool_names,
    story_workspace_handle_dream_tool,
)
from story_workspace import contracts as story_workspace_contracts
from story_workspace.contracts import (
    StoryWorkspaceDreamRunToolInput,
    StoryWorkspaceDreamStageItemToolInput,
    StoryWorkspaceDreamStageToolInput,
    StoryWorkspaceEpisodeAction,
    StoryWorkspaceEpisodeBindingToolInput,
    StoryWorkspaceEpisodeWorkflowCompletionToolInput,
)
from services.story_workspace.episode_action_service import (
    StoryWorkspaceEpisodeNextActionResolver,
    StoryWorkspaceEpisodeWorkflowFactService,
)
from services.story_workspace.episode_artifact_service import (
    StoryWorkspaceEpisodeArtifactService,
    StoryWorkspaceEpisodeAuthority,
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
                    user_id INTEGER NOT NULL,
                    deck_id TEXT NOT NULL
                );
                CREATE TABLE deck_plugin_bindings (
                    deck_plugin_binding_id TEXT PRIMARY KEY,
                    binding_revision INTEGER NOT NULL,
                    deck_plugin_id TEXT NOT NULL,
                    deck_plugin_version TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    deck_id TEXT NOT NULL
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
                CREATE TABLE chat_message (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    parts TEXT,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            db.execute(
                "INSERT INTO story_workspace_workspaces (id, owner_id, created_at) "
                "VALUES (?, ?, ?)",
                ("workspace-1", 7, "2026-08-04T00:00:00+00:00"),
            )
            db.execute(
                "INSERT INTO chat_thread (id, user_id, deck_id) VALUES (?, ?, ?)",
                (THREAD_ID, 7, "deck-1"),
            )
            db.execute(
                "INSERT INTO deck_plugin_bindings VALUES (?, ?, ?, ?, ?, ?)",
                ("binding-1", 3, "plugin-1", "1.2.3", "workspace-1", "deck-1"),
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

    def _seed_episode_action(
        self,
        *,
        action: str,
        episode_uid: str | None = None,
        manifest_revision: str | None = None,
        input_revision: str | None = None,
        message_id: str = "dream_agent_" + "a" * 64,
    ) -> None:
        launch_metadata = {
            "kind": "story-workspace-dream-launch",
            "actorId": "7",
            "workspaceId": "workspace-1",
            "deckId": "deck-1",
            "workflowRunId": RUN_ID,
            "threadId": THREAD_ID,
            "dreamContext": {
                "workflow_run_id": RUN_ID,
                "thread_id": THREAD_ID,
                "deck_id": "deck-1",
                "deck_plugin_id": "plugin-1",
                "deck_plugin_version": "1.2.3",
                "deck_plugin_binding_id": "binding-1",
                "binding_revision": 3,
                "deck_runtime_snapshot_id": "snapshot-1",
                "runtime_plugin_lock_id": "lock-1",
            },
        }
        action_metadata = {
            "kind": "story-workspace-dream-agent-user",
            "story_workspace_run_id": RUN_ID,
            "actor_id": "7",
            "thread_id": THREAD_ID,
            "dispatch_status": "dispatching",
            "dispatch_claim_id": "claim-1",
            "dispatch_claim_lease_until": time.time() + 60,
            "story_workspace_episode_action": {
                "schema": "story-workspace-episode-action/v1",
                "action": action,
                "episode_uid": episode_uid,
                "surface_revision": manifest_revision,
                "manifest_revision": manifest_revision,
                "input_revision": input_revision,
            },
        }
        db = sqlite3.connect(self.database_path)
        try:
            db.execute(
                "INSERT OR IGNORE INTO chat_message "
                "(id, thread_id, role, parts, metadata) VALUES (?, ?, 'user', '[]', ?)",
                ("launch-source", THREAD_ID, json.dumps(launch_metadata)),
            )
            db.execute(
                "INSERT OR REPLACE INTO chat_message "
                "(id, thread_id, role, parts, metadata) VALUES (?, ?, 'user', '[]', ?)",
                (message_id, THREAD_ID, json.dumps(action_metadata)),
            )
            db.commit()
        finally:
            db.close()

    def _call(
        self,
        tool_name: str,
        arguments: dict[str, object],
        *,
        actor_id: str = "7",
        thread_id: str = THREAD_ID,
        trusted_run_id: str = RUN_ID,
        message_id: str = "dream_agent_" + "a" * 64,
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
                    "INK_AGENT_WORKFLOW_RUN_ID": trusted_run_id,
                    "INK_AGENT_STORY_WORKSPACE_MESSAGE_ID": message_id,
                },
            ),
        ):
            return json.loads(
                story_workspace_handle_dream_tool(tool_name, arguments)
            )

    def test_tool_contract_exposes_only_non_forgeable_arguments(self) -> None:
        self.assertEqual(
            set(STORY_WORKSPACE_DREAM_TOOL_SPECS),
            {
                "write_dream_run",
                "write_dream_stage",
                "bind_first_episode",
                "record_episode_workflow_completion",
            },
        )
        self.assertEqual(
            set(story_workspace_allowed_tool_names()),
            {
                "mcp__story_workspace__write_dream_run",
                "mcp__story_workspace__write_dream_stage",
                "mcp__story_workspace__bind_first_episode",
                "mcp__story_workspace__record_episode_workflow_completion",
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

        server = story_workspace_create_mcp_server()
        self.assertEqual(server.name, "story_workspace")

    def test_agent_visible_input_contracts_have_one_canonical_owner(self) -> None:
        contract_types = (
            StoryWorkspaceDreamRunToolInput,
            StoryWorkspaceDreamStageItemToolInput,
            StoryWorkspaceDreamStageToolInput,
            StoryWorkspaceEpisodeBindingToolInput,
            StoryWorkspaceEpisodeWorkflowCompletionToolInput,
        )
        for contract_type in contract_types:
            self.assertEqual(contract_type.__module__, "story_workspace.contracts")
            self.assertIn(contract_type.__name__, story_workspace_contracts.__all__)

        for legacy_name in (
            "_DreamToolInput",
            "_WriteDreamRunInput",
            "_DreamStageItemInput",
            "_WriteDreamStageInput",
        ):
            self.assertFalse(hasattr(story_workspace_tool, legacy_name))

        run_schema = StoryWorkspaceDreamRunToolInput.model_json_schema(
            by_alias=True
        )
        self.assertEqual(
            set(run_schema["properties"]),
            {"workflowRunId", "expectedRevision"},
        )
        self.assertFalse(run_schema["additionalProperties"])

        stage_schema = StoryWorkspaceDreamStageToolInput.model_json_schema(
            by_alias=True
        )
        self.assertEqual(
            set(stage_schema["properties"]),
            {
                "workflowRunId",
                "stage",
                "sourceFiles",
                "items",
                "expectedRevision",
            },
        )
        item_schema = stage_schema["$defs"][
            "StoryWorkspaceDreamStageItemToolInput"
        ]
        self.assertEqual(
            set(item_schema["properties"]),
            {
                "entityId",
                "displayName",
                "summary",
                "sourceFile",
                "relations",
            },
        )
        self.assertFalse(item_schema["additionalProperties"])

        binding_schema = StoryWorkspaceEpisodeBindingToolInput.model_json_schema(
            by_alias=True
        )
        self.assertEqual(
            set(binding_schema["properties"]),
            {"workflowRunId", "storySlug", "expectedBindingRevision"},
        )
        completion_schema = (
            StoryWorkspaceEpisodeWorkflowCompletionToolInput.model_json_schema(
                by_alias=True
            )
        )
        self.assertEqual(
            set(completion_schema["properties"]),
            {
                "workflowRunId",
                "episodeId",
                "action",
                "inputRevision",
                "expectedWorkflowRevision",
                "expectedManifestRevision",
            },
        )
        for schema in (binding_schema, completion_schema):
            self.assertFalse(schema["additionalProperties"])
            self.assertFalse(
                {"actorId", "threadId", "messageId", "path", "root"}
                & set(schema["properties"])
            )

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

    def test_run_in_actors_second_workspace_uses_its_exact_workspace(self) -> None:
        db = sqlite3.connect(self.database_path)
        try:
            db.execute(
                "INSERT INTO story_workspace_workspaces (id, owner_id, created_at) "
                "VALUES (?, ?, ?)",
                ("workspace-2", 7, "2026-08-04T01:00:00+00:00"),
            )
            db.execute(
                "INSERT INTO story_workspace_workspaces (id, owner_id, created_at) "
                "VALUES (?, ?, ?)",
                ("workspace-other-actor", 8, "2026-08-04T02:00:00+00:00"),
            )
            db.execute(
                "UPDATE workflow_runs SET workspace_id = ? WHERE id = ?",
                ("workspace-2", RUN_ID),
            )
            db.commit()
        finally:
            db.close()

        cross_actor_result = self._call(
            "write_dream_run",
            {"workflowRunId": RUN_ID, "expectedRevision": 0},
            actor_id="8",
        )
        self.assertEqual(cross_actor_result, {"error": "DREAM_WRITE_REJECTED"})
        self.assertFalse((self.workspace / ".dream" / "runtime").exists())

        result = self._call(
            "write_dream_run",
            {"workflowRunId": RUN_ID, "expectedRevision": 0},
        )

        self.assertEqual(
            result,
            {"changedStages": [], "revision": 1, "run": RUN_ID},
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

    def test_missing_or_cross_run_trusted_context_fails_closed(self) -> None:
        other_run_id = "run_" + "9" * 32
        for trusted_run_id in ("", other_run_id):
            with self.subTest(trusted_run_id=trusted_run_id):
                result = self._call(
                    "write_dream_run",
                    {"workflowRunId": RUN_ID, "expectedRevision": 0},
                    trusted_run_id=trusted_run_id,
                )
                self.assertEqual(result, {"error": "DREAM_WRITE_REJECTED"})
                self.assertFalse((self.workspace / ".dream" / "runtime").exists())

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

    def test_agent_only_binding_validates_project_and_persisted_action(self) -> None:
        story = self.workspace / "stories" / "demo"
        (story / "episodes" / "EP01").mkdir(parents=True)
        (story / "project.yaml").write_text("project_id: demo\n", encoding="utf-8")
        self._seed_episode_action(action="recover_first_episode_binding")

        result = self._call(
            "bind_first_episode",
            {
                "workflowRunId": RUN_ID,
                "storySlug": "demo",
                "expectedBindingRevision": 0,
            },
        )

        self.assertEqual(result["run"], RUN_ID)
        self.assertEqual(result["bindingRevision"], 1)
        self.assertRegex(str(result["episodeId"]), r"^[0-9a-f]{32}$")
        db = sqlite3.connect(self.database_path)
        source = json.loads(
            db.execute(
                "SELECT metadata FROM chat_message WHERE id = 'launch-source'"
            ).fetchone()[0]
        )
        db.close()
        self.assertEqual(
            source["story_workspace_episode_identity"]["episode_uid"],
            result["episodeId"],
        )
        self.assertNotIn("episodeRoot", json.dumps(result))

        forged = self._call(
            "bind_first_episode",
            {
                "workflowRunId": RUN_ID,
                "storySlug": "other",
                "expectedBindingRevision": 0,
            },
        )
        self.assertEqual(forged, {"error": "DREAM_WRITE_REJECTED"})

    def test_episode_tools_reject_missing_forged_or_inactive_message_identity(self) -> None:
        story = self.workspace / "stories" / "demo"
        (story / "episodes" / "EP01").mkdir(parents=True)
        (story / "project.yaml").write_text("project_id: demo\n", encoding="utf-8")
        self._seed_episode_action(action="recover_first_episode_binding")
        arguments = {
            "workflowRunId": RUN_ID,
            "storySlug": "demo",
            "expectedBindingRevision": 0,
        }
        for message_id in ("", "dream_agent_" + "b" * 64):
            with self.subTest(message_id=message_id):
                self.assertEqual(
                    self._call(
                        "bind_first_episode",
                        arguments,
                        message_id=message_id,
                    ),
                    {"error": "DREAM_WRITE_REJECTED"},
                )

        db = sqlite3.connect(self.database_path)
        metadata = json.loads(
            db.execute(
                "SELECT metadata FROM chat_message WHERE id = ?",
                ("dream_agent_" + "a" * 64,),
            ).fetchone()[0]
        )
        metadata["dispatch_status"] = "dispatched"
        db.execute(
            "UPDATE chat_message SET metadata = ? WHERE id = ?",
            (json.dumps(metadata), "dream_agent_" + "a" * 64),
        )
        db.commit()
        db.close()
        self.assertEqual(
            self._call("bind_first_episode", arguments),
            {"error": "DREAM_WRITE_REJECTED"},
        )

    def test_completion_tool_checks_action_input_and_replays_same_cas(self) -> None:
        story = self.workspace / "stories" / "demo"
        (story / "episodes" / "EP01").mkdir(parents=True)
        (story / "project.yaml").write_text("project_id: demo\n", encoding="utf-8")
        self._seed_episode_action(action="recover_first_episode_binding")
        bound = self._call(
            "bind_first_episode",
            {
                "workflowRunId": RUN_ID,
                "storySlug": "demo",
                "expectedBindingRevision": 0,
            },
        )
        episode_uid = str(bound["episodeId"])
        authority = StoryWorkspaceEpisodeAuthority(
            workflow_run_id=RUN_ID,
            episode_uid=episode_uid,
            story_slug="demo",
            episode_code="EP01",
        )
        surface = StoryWorkspaceEpisodeArtifactService(self.workspace).read_surface(
            RUN_ID,
            episode_authority=authority,
        )
        facts = StoryWorkspaceEpisodeWorkflowFactService(self.workspace).read(
            RUN_ID,
            episode_uid,
        )
        input_revision = StoryWorkspaceEpisodeNextActionResolver.action_input_revision(
            StoryWorkspaceEpisodeAction.PLAN_EPISODE,
            surface,
            facts,
        )
        self._seed_episode_action(
            action="plan_episode",
            episode_uid=episode_uid,
            manifest_revision=surface.manifest_revision,
            input_revision=input_revision,
        )
        arguments = {
            "workflowRunId": RUN_ID,
            "episodeId": episode_uid,
            "action": "plan_episode",
            "inputRevision": input_revision,
            "expectedWorkflowRevision": 0,
            "expectedManifestRevision": surface.manifest_revision,
        }
        first = self._call("record_episode_workflow_completion", arguments)
        replay = self._call("record_episode_workflow_completion", arguments)

        self.assertEqual(first["workflowRevision"], 1)
        self.assertEqual(replay, first)
        persisted = StoryWorkspaceEpisodeWorkflowFactService(self.workspace).read(
            RUN_ID,
            episode_uid,
        )
        self.assertEqual(persisted.revision, 1)
        self.assertEqual(len(persisted.completions), 1)

        poisoned = dict(arguments)
        poisoned["inputRevision"] = "sha256:" + "f" * 64
        self.assertEqual(
            self._call("record_episode_workflow_completion", poisoned),
            {"error": "DREAM_WRITE_REJECTED"},
        )


if __name__ == "__main__":
    unittest.main()
