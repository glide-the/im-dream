"""Controlled Story Workspace MCP seam for Dream runtime file writes."""

from __future__ import annotations

import json
import os
import shutil
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
                    deck_id TEXT NOT NULL,
                    voice_id TEXT
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
            db.execute(
                "UPDATE workflow_runs "
                "SET source_message_id = ?, source_message_time = ? WHERE id = ?",
                (
                    "launch-source",
                    "2026-08-04T00:00:01+00:00",
                    RUN_ID,
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

    def _launch_metadata(self) -> dict[str, object]:
        db = sqlite3.connect(self.database_path)
        try:
            row = db.execute(
                "SELECT metadata FROM chat_message WHERE id = 'launch-source'"
            ).fetchone()
            self.assertIsNotNone(row)
            return json.loads(row[0])
        finally:
            db.close()

    def _replace_launch_metadata(
        self,
        metadata: dict[str, object],
        *,
        thread_agent_id: str | None,
    ) -> str:
        encoded = json.dumps(metadata, sort_keys=True)
        db = sqlite3.connect(self.database_path)
        try:
            db.execute(
                "UPDATE chat_thread SET voice_id = ? WHERE id = ?",
                (thread_agent_id, THREAD_ID),
            )
            db.execute(
                "UPDATE chat_message SET metadata = ? WHERE id = 'launch-source'",
                (encoded,),
            )
            db.commit()
        finally:
            db.close()
        return encoded

    def _insert_launch_decoy(
        self,
        message_id: str,
        metadata: dict[str, object],
    ) -> str:
        encoded = json.dumps(metadata, sort_keys=True)
        db = sqlite3.connect(self.database_path)
        try:
            db.execute(
                "INSERT INTO chat_message "
                "(id, thread_id, role, parts, metadata) "
                "VALUES (?, ?, 'user', '[]', ?)",
                (message_id, THREAD_ID, encoded),
            )
            db.commit()
        finally:
            db.close()
        return encoded

    def _message_metadata(self, message_id: str) -> dict[str, object]:
        db = sqlite3.connect(self.database_path)
        try:
            row = db.execute(
                "SELECT metadata FROM chat_message WHERE id = ?",
                (message_id,),
            ).fetchone()
            self.assertIsNotNone(row)
            return json.loads(row[0])
        finally:
            db.close()

    @staticmethod
    def _current_launch_metadata(
        legacy: dict[str, object],
        agent_id: str | None,
    ) -> dict[str, object]:
        current = json.loads(json.dumps(legacy))
        current["schemaVersion"] = "story-workspace-dream-launch/v1"
        current["agentId"] = agent_id
        current["dreamContext"]["agent_id"] = agent_id
        return current

    def _seed_episode_action(
        self,
        *,
        action: str,
        episode_uid: str | None = None,
        manifest_revision: str | None = None,
        input_revision: str | None = None,
        facts_revision: int | None = None,
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
                "workflow_run_id": RUN_ID,
                "thread_id": THREAD_ID,
                "actor_id": "7",
                "action": action,
                "episode_uid": episode_uid,
                "input_revision": input_revision,
                "expected_facts_revision": facts_revision,
                "expected_manifest_revision": manifest_revision,
                "expected_workflow_revision": manifest_revision,
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

    def _prepare_full_chain_action(
        self,
        *,
        review_report: str | None,
        alias_report: str | None = None,
    ) -> tuple[str, StoryWorkspaceEpisodeAuthority, object, object]:
        vendor_story = (
            Path(__file__).resolve().parents[2]
            / "vendor"
            / "drama-forge"
            / "drama-forge"
            / "stories"
            / "didi-zhengzhou"
        )
        story = self.workspace / "stories" / "didi-zhengzhou"
        shutil.copytree(vendor_story, story)
        self._seed_episode_action(action="recover_first_episode_binding")
        bound = self._call(
            "bind_first_episode",
            {"workflowRunId": RUN_ID, "expectedBindingRevision": 0},
        )
        episode_uid = str(bound["episodeId"])
        authority = StoryWorkspaceEpisodeAuthority(
            workflow_run_id=RUN_ID,
            episode_uid=episode_uid,
            story_slug="didi-zhengzhou",
            episode_code="EP01",
        )
        episode = story / "episodes" / "EP01"
        if review_report is not None:
            (episode / "review-report.md").write_text(
                review_report,
                encoding="utf-8",
            )
        if alias_report is not None:
            (episode / "full-chain-review-report.md").write_text(
                alias_report,
                encoding="utf-8",
            )
        artifact_service = StoryWorkspaceEpisodeArtifactService(self.workspace)
        surface = artifact_service.read_surface(
            RUN_ID,
            episode_authority=authority,
        )
        facts_service = StoryWorkspaceEpisodeWorkflowFactService(self.workspace)
        facts = facts_service.read(RUN_ID, episode_uid)
        for index, action in enumerate(
            (
                StoryWorkspaceEpisodeAction.REFRESH_ASSETS,
                StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD,
                StoryWorkspaceEpisodeAction.GENERATE_PROMPTS,
            ),
            start=1,
        ):
            facts = facts_service.record_completion(
                workflow_run_id=RUN_ID,
                episode_uid=episode_uid,
                action=action,
                input_revision=(
                    StoryWorkspaceEpisodeNextActionResolver.action_input_revision(
                        action,
                        surface,
                        facts,
                    )
                ),
                manifest_revision=surface.manifest_revision,
                message_id="dream_agent_" + str(index) * 64,
                expected_revision=facts.revision,
            )
        input_revision = (
            StoryWorkspaceEpisodeNextActionResolver.action_input_revision(
                StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN,
                surface,
                facts,
            )
        )
        self._seed_episode_action(
            action=StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN.value,
            episode_uid=episode_uid,
            manifest_revision=surface.manifest_revision,
            input_revision=input_revision,
            facts_revision=facts.revision,
        )
        return episode_uid, authority, surface, facts

    def _prepare_script_review_action(
        self,
        *,
        review_report: str,
    ) -> tuple[str, StoryWorkspaceEpisodeAuthority, object, object]:
        vendor_story = (
            Path(__file__).resolve().parents[2]
            / "vendor"
            / "drama-forge"
            / "drama-forge"
            / "stories"
            / "didi-zhengzhou"
        )
        story = self.workspace / "stories" / "didi-zhengzhou"
        shutil.copytree(vendor_story, story)
        episode = story / "episodes" / "EP01"
        shutil.rmtree(episode / "prompts")
        shutil.rmtree(episode / "renders")
        (episode / "review-report.md").write_text(
            review_report,
            encoding="utf-8",
        )
        self._seed_episode_action(action="recover_first_episode_binding")
        bound = self._call(
            "bind_first_episode",
            {"workflowRunId": RUN_ID, "expectedBindingRevision": 0},
        )
        episode_uid = str(bound["episodeId"])
        authority = StoryWorkspaceEpisodeAuthority(
            workflow_run_id=RUN_ID,
            episode_uid=episode_uid,
            story_slug="didi-zhengzhou",
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
        self._seed_episode_action(
            action=StoryWorkspaceEpisodeAction.REVIEW_SCRIPT.value,
            episode_uid=episode_uid,
            manifest_revision=surface.manifest_revision,
            input_revision=(
                StoryWorkspaceEpisodeNextActionResolver.action_input_revision(
                    StoryWorkspaceEpisodeAction.REVIEW_SCRIPT,
                    surface,
                    facts,
                )
            ),
            facts_revision=facts.revision,
        )
        return episode_uid, authority, surface, facts

    @staticmethod
    def _valid_full_chain_report(surface: object) -> str:
        artifacts = {
            item.relative_key: item.content_revision
            for item in surface.artifacts
        }
        prompt_revisions = {
            item.source_artifact: item.source_revision
            for item in surface.auxiliary.prompts.items
        }
        reviewed_files = [
            "episode-outline.md",
            "script.md",
            "storyboard.yaml",
            *sorted(prompt_revisions),
        ]
        source_revisions = {
            "episode-outline.md": artifacts["episode-outline.md"],
            "script.md": artifacts["script.md"],
            "storyboard.yaml": artifacts["storyboard.yaml"],
            **prompt_revisions,
        }
        reviewed_yaml = "\n".join(f"  - {path}" for path in reviewed_files)
        revisions_yaml = "\n".join(
            f"  {path}: {revision}"
            for path, revision in source_revisions.items()
        )
        return (
            "---\n"
            "scope: full-chain\n"
            "overall_verdict: APPROVED\n"
            "reviewed_files:\n"
            f"{reviewed_yaml}\n"
            "source_revisions:\n"
            f"{revisions_yaml}\n"
            "---\n"
            "# 完整链路审阅\n\n"
            "当前规范产物关联完整。\n"
        )

    @staticmethod
    def _valid_script_review_report(surface: object) -> str:
        script_revision = next(
            item.content_revision
            for item in surface.artifacts
            if item.relative_key == "script.md"
        )
        return (
            "---\n"
            "scope: script\n"
            "overall_verdict: APPROVED\n"
            "reviewed_files:\n"
            "  - script.md\n"
            "source_revisions:\n"
            f"  script.md: {script_revision}\n"
            "---\n"
            "# 剧本审阅\n\n"
            "当前剧本审阅通过。\n"
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
            {"workflowRunId", "expectedBindingRevision"},
        )
        completion_schema = (
            StoryWorkspaceEpisodeWorkflowCompletionToolInput.model_json_schema(
                by_alias=True
            )
        )
        self.assertEqual(
            set(completion_schema["properties"]),
            {"workflowRunId"},
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
        (story / "project.yaml").write_text(
            'project_id: "demo"\n',
            encoding="utf-8",
        )
        self._seed_episode_action(action="recover_first_episode_binding")

        result = self._call(
            "bind_first_episode",
            {
                "workflowRunId": RUN_ID,
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

    def test_agent_only_binding_accepts_legacy_project_mapping_identity(
        self,
    ) -> None:
        story = self.workspace / "stories" / "demo"
        (story / "episodes" / "EP01").mkdir(parents=True)
        (story / "project.yaml").write_text(
            "project:\n"
            "  project_id: demo\n"
            "  project_name: Legacy Dream project\n",
            encoding="utf-8",
        )
        self._seed_episode_action(action="recover_first_episode_binding")

        result = self._call(
            "bind_first_episode",
            {
                "workflowRunId": RUN_ID,
                "expectedBindingRevision": 0,
            },
        )

        self.assertEqual(result["run"], RUN_ID)
        self.assertEqual(result["bindingRevision"], 1)
        self.assertRegex(str(result["episodeId"]), r"^[0-9a-f]{32}$")

    def test_source_launch_generation_and_agent_provenance_matrix(self) -> None:
        self._seed_episode_action(action="recover_first_episode_binding")
        legacy = self._launch_metadata()
        current = self._current_launch_metadata(legacy, "voice-authorized")
        current_null = self._current_launch_metadata(legacy, None)
        modern_without_agents = json.loads(json.dumps(current))
        modern_without_agents.pop("agentId")
        modern_without_agents["dreamContext"].pop("agent_id")
        partial_top = json.loads(json.dumps(current))
        partial_top["dreamContext"].pop("agent_id")
        partial_context = json.loads(json.dumps(current))
        partial_context.pop("agentId")
        unknown_schema = json.loads(json.dumps(current))
        unknown_schema["schemaVersion"] = "story-workspace-dream-launch/v2"
        cases = (
            ("legacy", legacy, "voice-authorized", True),
            ("current", current, "voice-authorized", True),
            ("current-null", current_null, None, True),
            ("modern-dual-delete", modern_without_agents, "voice-authorized", False),
            ("partial-top", partial_top, "voice-authorized", False),
            ("partial-context", partial_context, "voice-authorized", False),
            ("unknown-schema", unknown_schema, "voice-authorized", False),
        )
        for label, metadata, thread_agent_id, accepted in cases:
            with self.subTest(label=label):
                self._replace_launch_metadata(
                    metadata,
                    thread_agent_id=thread_agent_id,
                )
                db = self._open_db()
                try:
                    if accepted:
                        source = story_workspace_tool._source_launch_row(  # noqa: SLF001
                            db,
                            actor_id=7,
                            thread_id=THREAD_ID,
                            workflow_run_id=RUN_ID,
                        )
                        self.assertEqual(source[0], "launch-source")
                    else:
                        with self.assertRaises(PermissionError):
                            story_workspace_tool._source_launch_row(  # noqa: SLF001
                                db,
                                actor_id=7,
                                thread_id=THREAD_ID,
                                workflow_run_id=RUN_ID,
                            )
                finally:
                    db.close()
        self.assertTrue(
            any(
                "thread.voice_id AS thread_voice_id" in statement
                for statement in self.statements
            )
        )

    def test_source_launch_never_accepts_a_same_thread_decoy(self) -> None:
        self._seed_episode_action(action="recover_first_episode_binding")
        legacy = self._launch_metadata()
        forged_authority = self._current_launch_metadata(legacy, "voice-forged")
        decoys = (
            ("current", self._current_launch_metadata(legacy, "voice-authorized")),
            ("legacy", legacy),
        )
        for label, decoy in decoys:
            with self.subTest(label=label):
                self._replace_launch_metadata(
                    forged_authority,
                    thread_agent_id="voice-authorized",
                )
                decoy_id = f"launch-decoy-{label}"
                self._insert_launch_decoy(decoy_id, decoy)
                db = self._open_db()
                try:
                    with self.assertRaises(PermissionError):
                        story_workspace_tool._source_launch_row(  # noqa: SLF001
                            db,
                            actor_id=7,
                            thread_id=THREAD_ID,
                            workflow_run_id=RUN_ID,
                        )
                finally:
                    db.close()
                cleanup = sqlite3.connect(self.database_path)
                try:
                    cleanup.execute(
                        "DELETE FROM chat_message WHERE id = ?",
                        (decoy_id,),
                    )
                    cleanup.commit()
                finally:
                    cleanup.close()
        self.assertTrue(
            any(
                "source.id = run.source_message_id" in statement
                for statement in self.statements
            )
        )

    def test_binding_rejects_forged_agent_before_any_episode_write(self) -> None:
        story = self.workspace / "stories" / "demo"
        (story / "episodes" / "EP01").mkdir(parents=True)
        (story / "project.yaml").write_text("project_id: demo\n", encoding="utf-8")
        self._seed_episode_action(action="recover_first_episode_binding")
        legacy = self._launch_metadata()
        forged = self._current_launch_metadata(legacy, "voice-forged")
        raw_before = self._replace_launch_metadata(
            forged,
            thread_agent_id="voice-authorized",
        )
        decoy_before = self._insert_launch_decoy("launch-decoy", legacy)

        result = self._call(
            "bind_first_episode",
            {"workflowRunId": RUN_ID, "expectedBindingRevision": 0},
        )

        self.assertEqual(result, {"error": "DREAM_WRITE_REJECTED"})
        self.assertEqual(
            self._launch_metadata(),
            json.loads(raw_before),
        )
        self.assertEqual(
            self._message_metadata("launch-decoy"),
            json.loads(decoy_before),
        )
        self.assertNotIn(
            "story_workspace_episode_identity",
            self._message_metadata("launch-decoy"),
        )
        self.assertFalse(
            (
                self.workspace
                / ".dream"
                / "runtime"
                / "runs"
                / RUN_ID
                / "episode.json"
            ).exists()
        )
        self.assertFalse(
            (
                self.workspace
                / ".dream"
                / "runtime"
                / "runs"
                / RUN_ID
                / "episodes"
            ).exists()
        )

    def test_episode_tools_reject_missing_forged_or_inactive_message_identity(self) -> None:
        story = self.workspace / "stories" / "demo"
        (story / "episodes" / "EP01").mkdir(parents=True)
        (story / "project.yaml").write_text("project_id: demo\n", encoding="utf-8")
        self._seed_episode_action(action="recover_first_episode_binding")
        arguments = {
            "workflowRunId": RUN_ID,
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
            facts_revision=facts.revision,
        )
        (story / "episodes" / "EP01" / "episode-outline.md").write_text(
            "---\ntitle: Demo\n---\n# Story Goals\n- Begin\n",
            encoding="utf-8",
        )
        output_surface = StoryWorkspaceEpisodeArtifactService(
            self.workspace
        ).read_surface(
            RUN_ID,
            episode_authority=authority,
        )
        self.assertNotEqual(
            output_surface.manifest_revision,
            surface.manifest_revision,
        )
        arguments = {"workflowRunId": RUN_ID}
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
        self.assertEqual(
            persisted.completions[0].manifest_revision,
            output_surface.manifest_revision,
        )

        poisoned = {**arguments, "inputRevision": "sha256:" + "f" * 64}
        self.assertEqual(
            self._call("record_episode_workflow_completion", poisoned),
            {"error": "DREAM_WRITE_REJECTED"},
        )

    def test_completion_rechecks_agent_provenance_before_workflow_write(self) -> None:
        story = self.workspace / "stories" / "demo"
        episode = story / "episodes" / "EP01"
        episode.mkdir(parents=True)
        (story / "project.yaml").write_text("project_id: demo\n", encoding="utf-8")
        self._seed_episode_action(action="recover_first_episode_binding")
        bound = self._call(
            "bind_first_episode",
            {"workflowRunId": RUN_ID, "expectedBindingRevision": 0},
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
        facts_service = StoryWorkspaceEpisodeWorkflowFactService(self.workspace)
        facts = facts_service.read(RUN_ID, episode_uid)
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
            facts_revision=facts.revision,
        )
        (episode / "episode-outline.md").write_text(
            "---\ntitle: Demo\n---\n# Story Goals\n- Begin\n",
            encoding="utf-8",
        )
        forged = self._current_launch_metadata(
            self._launch_metadata(),
            "voice-forged",
        )
        valid_decoy = self._current_launch_metadata(
            self._launch_metadata(),
            "voice-authorized",
        )
        raw_before = self._replace_launch_metadata(
            forged,
            thread_agent_id="voice-authorized",
        )
        decoy_before = self._insert_launch_decoy(
            "launch-decoy",
            valid_decoy,
        )

        result = self._call(
            "record_episode_workflow_completion",
            {"workflowRunId": RUN_ID},
        )

        self.assertEqual(result, {"error": "DREAM_WRITE_REJECTED"})
        self.assertEqual(self._launch_metadata(), json.loads(raw_before))
        self.assertEqual(
            self._message_metadata("launch-decoy"),
            json.loads(decoy_before),
        )
        persisted = facts_service.read(RUN_ID, episode_uid)
        self.assertEqual(persisted.revision, 0)
        self.assertEqual(persisted.completions, [])

    def test_full_chain_completion_rejects_alias_report_without_writing_fact(
        self,
    ) -> None:
        script_review = (
            "---\n"
            "scope: script\n"
            "overall_verdict: APPROVED\n"
            "reviewed_files:\n"
            "  - script.md\n"
            "---\n"
            "# 剧本审阅\n"
        )
        alias_review = (
            "---\n"
            "scope: full-chain\n"
            "overall_verdict: APPROVED\n"
            "---\n"
            "# 完整链路审阅\n"
        )
        episode_uid, _authority, _surface, facts = self._prepare_full_chain_action(
            review_report=script_review,
            alias_report=alias_review,
        )

        result = self._call(
            "record_episode_workflow_completion",
            {"workflowRunId": RUN_ID},
        )

        self.assertEqual(result["error"], "DREAM_WRITE_REJECTED")
        self.assertEqual(result["reason"], "canonical_review_report_required")
        self.assertIn("review-report.md", str(result["message"]))
        self.assertNotIn(str(self.workspace), str(result))
        persisted = StoryWorkspaceEpisodeWorkflowFactService(self.workspace).read(
            RUN_ID,
            episode_uid,
        )
        self.assertEqual(persisted.revision, facts.revision)
        self.assertFalse(
            any(
                item.action is StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN
                for item in persisted.completions
            )
        )

    def test_script_review_completion_rejects_noncanonical_report_without_fact(
        self,
    ) -> None:
        episode_uid, _authority, _surface, facts = self._prepare_script_review_action(
            review_report=(
                "# EP01 剧本审阅\n\n"
                "审阅结果：APPROVED\n"
            ),
        )

        result = self._call(
            "record_episode_workflow_completion",
            {"workflowRunId": RUN_ID},
        )

        self.assertEqual(result["error"], "DREAM_WRITE_REJECTED")
        self.assertEqual(result["reason"], "canonical_review_report_required")
        persisted = StoryWorkspaceEpisodeWorkflowFactService(self.workspace).read(
            RUN_ID,
            episode_uid,
        )
        self.assertEqual(persisted.revision, facts.revision)
        self.assertFalse(
            any(
                item.action is StoryWorkspaceEpisodeAction.REVIEW_SCRIPT
                for item in persisted.completions
            )
        )

    def test_script_review_completion_accepts_current_report_and_recommends_prompts(
        self,
    ) -> None:
        episode_uid, authority, initial, facts = self._prepare_script_review_action(
            review_report="# 待修复剧本审阅\n",
        )
        episode = (
            self.workspace
            / "stories"
            / "didi-zhengzhou"
            / "episodes"
            / "EP01"
        )
        (episode / "review-report.md").write_text(
            self._valid_script_review_report(initial),
            encoding="utf-8",
        )
        surface = StoryWorkspaceEpisodeArtifactService(self.workspace).read_surface(
            RUN_ID,
            episode_authority=authority,
        )
        self._seed_episode_action(
            action=StoryWorkspaceEpisodeAction.REVIEW_SCRIPT.value,
            episode_uid=episode_uid,
            manifest_revision=surface.manifest_revision,
            input_revision=(
                StoryWorkspaceEpisodeNextActionResolver.action_input_revision(
                    StoryWorkspaceEpisodeAction.REVIEW_SCRIPT,
                    surface,
                    facts,
                )
            ),
            facts_revision=facts.revision,
        )

        result = self._call(
            "record_episode_workflow_completion",
            {"workflowRunId": RUN_ID},
        )
        replay = self._call(
            "record_episode_workflow_completion",
            {"workflowRunId": RUN_ID},
        )

        self.assertEqual(result["action"], "review_script")
        self.assertEqual(replay, result)
        persisted = StoryWorkspaceEpisodeWorkflowFactService(self.workspace).read(
            RUN_ID,
            episode_uid,
        )
        projection = StoryWorkspaceEpisodeNextActionResolver().project(
            surface,
            persisted,
        )
        self.assertEqual(
            projection.next_action.action,
            StoryWorkspaceEpisodeAction.GENERATE_PROMPTS,
        )
        self.assertTrue(projection.next_action.can_dispatch)

    def test_full_chain_completion_rejects_missing_source_revisions(self) -> None:
        incomplete_review = (
            "---\n"
            "scope: full-chain\n"
            "overall_verdict: APPROVED\n"
            "reviewed_files:\n"
            "  - episode-outline.md\n"
            "  - script.md\n"
            "  - storyboard.yaml\n"
            "  - prompts/ep001-prompts.yml\n"
            "---\n"
            "# 完整链路审阅\n"
        )
        episode_uid, _authority, _surface, facts = self._prepare_full_chain_action(
            review_report=incomplete_review,
        )

        result = self._call(
            "record_episode_workflow_completion",
            {"workflowRunId": RUN_ID},
        )

        self.assertEqual(result["error"], "DREAM_WRITE_REJECTED")
        self.assertEqual(result["reason"], "current_source_revisions_required")
        persisted = StoryWorkspaceEpisodeWorkflowFactService(self.workspace).read(
            RUN_ID,
            episode_uid,
        )
        self.assertEqual(persisted.revision, facts.revision)

    def test_full_chain_completion_rejects_orphan_prompt_coverage(self) -> None:
        episode_uid, authority, _initial, facts = self._prepare_full_chain_action(
            review_report=(
                "---\n"
                "scope: full-chain\n"
                "overall_verdict: APPROVED\n"
                "---\n"
                "# 待更新审阅\n"
            ),
        )
        episode = (
            self.workspace
            / "stories"
            / "didi-zhengzhou"
            / "episodes"
            / "EP01"
        )
        prompt_path = episode / "prompts" / "ep001-prompts.yml"
        prompt_path.write_text(
            prompt_path.read_text(encoding="utf-8")
            + "\n- shot_id: ORPHAN-E01-999\n"
            + "  positive: orphan prompt\n",
            encoding="utf-8",
        )
        artifact_service = StoryWorkspaceEpisodeArtifactService(self.workspace)
        prompt_surface = artifact_service.read_surface(
            RUN_ID,
            episode_authority=authority,
        )
        (episode / "review-report.md").write_text(
            self._valid_full_chain_report(prompt_surface),
            encoding="utf-8",
        )
        surface = artifact_service.read_surface(
            RUN_ID,
            episode_authority=authority,
        )
        self._seed_episode_action(
            action=StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN.value,
            episode_uid=episode_uid,
            manifest_revision=surface.manifest_revision,
            input_revision=(
                StoryWorkspaceEpisodeNextActionResolver.action_input_revision(
                    StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN,
                    surface,
                    facts,
                )
            ),
            facts_revision=facts.revision,
        )

        result = self._call(
            "record_episode_workflow_completion",
            {"workflowRunId": RUN_ID},
        )

        self.assertEqual(result["error"], "DREAM_WRITE_REJECTED")
        self.assertEqual(result["reason"], "complete_prompt_coverage_required")
        persisted = StoryWorkspaceEpisodeWorkflowFactService(self.workspace).read(
            RUN_ID,
            episode_uid,
        )
        self.assertEqual(persisted.revision, facts.revision)

    def test_full_chain_completion_accepts_current_report_and_advances_to_validation(
        self,
    ) -> None:
        episode_uid, authority, initial, facts = self._prepare_full_chain_action(
            review_report=(
                "---\n"
                "scope: full-chain\n"
                "overall_verdict: APPROVED\n"
                "---\n"
                "# 待更新审阅\n"
            ),
        )
        episode = (
            self.workspace
            / "stories"
            / "didi-zhengzhou"
            / "episodes"
            / "EP01"
        )
        (episode / "review-report.md").write_text(
            self._valid_full_chain_report(initial),
            encoding="utf-8",
        )
        surface = StoryWorkspaceEpisodeArtifactService(self.workspace).read_surface(
            RUN_ID,
            episode_authority=authority,
        )
        input_revision = (
            StoryWorkspaceEpisodeNextActionResolver.action_input_revision(
                StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN,
                surface,
                facts,
            )
        )
        self._seed_episode_action(
            action=StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN.value,
            episode_uid=episode_uid,
            manifest_revision=surface.manifest_revision,
            input_revision=input_revision,
            facts_revision=facts.revision,
        )

        result = self._call(
            "record_episode_workflow_completion",
            {"workflowRunId": RUN_ID},
        )
        replay = self._call(
            "record_episode_workflow_completion",
            {"workflowRunId": RUN_ID},
        )

        self.assertEqual(result["action"], "review_full_chain")
        self.assertEqual(replay, result)
        persisted = StoryWorkspaceEpisodeWorkflowFactService(self.workspace).read(
            RUN_ID,
            episode_uid,
        )
        projection = StoryWorkspaceEpisodeNextActionResolver().project(
            surface,
            persisted,
        )
        self.assertEqual(
            projection.next_action.action,
            StoryWorkspaceEpisodeAction.VALIDATE_EPISODE,
        )

    def test_binding_rejects_multiple_canonical_projects_without_agent_choice(self) -> None:
        for slug in ("demo-a", "demo-b"):
            story = self.workspace / "stories" / slug
            (story / "episodes" / "EP01").mkdir(parents=True)
            (story / "project.yaml").write_text(
                f"project_id: {slug}\n",
                encoding="utf-8",
            )
        self._seed_episode_action(action="recover_first_episode_binding")

        result = self._call(
            "bind_first_episode",
            {
                "workflowRunId": RUN_ID,
                "expectedBindingRevision": 0,
            },
        )

        self.assertEqual(result, {"error": "DREAM_WRITE_REJECTED"})
        self.assertFalse(
            (
                self.workspace
                / ".dream"
                / "runtime"
                / "runs"
                / RUN_ID
                / "episode.json"
            ).exists()
        )

    def test_binding_rejects_project_id_that_does_not_match_directory(self) -> None:
        story = self.workspace / "stories" / "demo"
        (story / "episodes" / "EP01").mkdir(parents=True)
        (story / "project.yaml").write_text(
            "project_id: other\n",
            encoding="utf-8",
        )
        self._seed_episode_action(action="recover_first_episode_binding")

        result = self._call(
            "bind_first_episode",
            {
                "workflowRunId": RUN_ID,
                "expectedBindingRevision": 0,
            },
        )

        self.assertEqual(result, {"error": "DREAM_WRITE_REJECTED"})
        db = sqlite3.connect(self.database_path)
        source = json.loads(
            db.execute(
                "SELECT metadata FROM chat_message WHERE id = 'launch-source'"
            ).fetchone()[0]
        )
        db.close()
        self.assertNotIn("story_workspace_episode_identity", source)

    def test_binding_rejects_project_id_values_smuggled_across_yaml_lines(self) -> None:
        payloads = (
            "project_id:\ndemo\n",
            "project_id:\r\n\tdemo\r\n",
            "project_id:\vdemo\n",
            "project_id:\fdemo\n",
        )
        story = self.workspace / "stories" / "demo"
        (story / "episodes" / "EP01").mkdir(parents=True)
        self._seed_episode_action(action="recover_first_episode_binding")

        for payload in payloads:
            with self.subTest(payload=repr(payload)):
                (story / "project.yaml").write_text(
                    payload,
                    encoding="utf-8",
                    newline="",
                )
                result = self._call(
                    "bind_first_episode",
                    {
                        "workflowRunId": RUN_ID,
                        "expectedBindingRevision": 0,
                    },
                )
                self.assertEqual(result, {"error": "DREAM_WRITE_REJECTED"})


if __name__ == "__main__":
    unittest.main()
