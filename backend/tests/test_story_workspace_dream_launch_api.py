"""Dream launch REST and production gateway integration tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

import database
from routers import story_workspace
from services.deck.builtin_plugin import (
    BUILTIN_CLAUDE_PLUGIN_ID,
    BUILTIN_DECK_PLUGIN_ID,
    BUILTIN_DECK_PLUGIN_VERSION,
    builtin_plugin_path,
    plugin_artifact_digest,
)
from services.deck.story_workflow_gateway import StoryWorkflowApplicationGateway
from services.deck_plugin.binding_service import BindingRevisionConflict
from services.story_workspace.dream_launch_gateway import (
    StoryWorkspaceDreamLaunchGateway,
)
from services.story_workspace.dream_launch_service import (
    StoryWorkspaceDreamLaunchIdempotencyConflict,
)
from story_workspace.contracts import (
    StoryWorkspaceDreamLaunchCommand,
    StoryWorkspaceDreamRunContext,
)


ACTOR_ID = "71"
OTHER_ACTOR_ID = "72"
WORKSPACE_ID = "workspace-dream-launch-api"
OTHER_WORKSPACE_ID = "workspace-dream-launch-api-other"
DECK_ID = "deck-dream-launch-api"
ALTERNATE_DECK_ID = "deck-dream-launch-api-alternate"


def launch_command(**overrides: object) -> StoryWorkspaceDreamLaunchCommand:
    payload: dict[str, object] = {
        "deckId": DECK_ID,
        "goal": "创作一个雨夜车站重逢的短篇故事",
        "idempotencyKey": "dream-api-launch-1",
    }
    payload.update(overrides)
    return StoryWorkspaceDreamLaunchCommand.model_validate(payload)


class ApiGateway:
    def __init__(self) -> None:
        self.calls: list[tuple[StoryWorkspaceDreamLaunchCommand, dict[str, str]]] = []

    async def start_dream_run(
        self,
        request: StoryWorkspaceDreamLaunchCommand,
        *,
        actor: dict[str, str],
    ) -> StoryWorkspaceDreamRunContext:
        self.calls.append((request, actor))
        return StoryWorkspaceDreamRunContext(
            workflow_run_id="run_" + "1" * 32,
            thread_id="thread-dream-api",
            deck_id=request.deck_id,
            deck_plugin_id=BUILTIN_DECK_PLUGIN_ID,
            deck_plugin_version=BUILTIN_DECK_PLUGIN_VERSION,
            deck_plugin_binding_id="dpb_" + "2" * 32,
            binding_revision=1,
            deck_runtime_snapshot_id="drs_" + "3" * 32,
            runtime_plugin_lock_id="rpl_" + "4" * 32,
        )


class StoryWorkspaceDreamLaunchApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = ApiGateway()
        self.app = FastAPI()
        self.app.dependency_overrides[story_workspace.get_current_user] = lambda: {
            "user_id": int(ACTOR_ID),
            "workspace_id": WORKSPACE_ID,
        }
        self.app.dependency_overrides[
            story_workspace.get_story_workflow_gateway
        ] = lambda: self.gateway
        self.app.include_router(story_workspace.router)

    def test_start_uses_canonical_request_and_returns_camel_case_context(self) -> None:
        with TestClient(self.app) as client:
            response = client.post(
                "/api/story-workspace/dream-runs/start",
                json={
                    "deckId": DECK_ID,
                    "goal": "创作一个雨夜车站重逢的短篇故事",
                    "idempotencyKey": "dream-api-launch-1",
                },
            )

        self.assertEqual(response.status_code, 201, response.text)
        payload = response.json()
        self.assertEqual(payload["status"], "accepted")
        self.assertEqual(payload["workflowRunId"], "run_" + "1" * 32)
        self.assertEqual(payload["threadId"], "thread-dream-api")
        self.assertEqual(payload["deckPluginBindingId"], "dpb_" + "2" * 32)
        self.assertFalse(any("_" in key for key in payload))
        request, actor = self.gateway.calls[0]
        self.assertEqual(request.deck_id, DECK_ID)
        self.assertEqual(
            actor,
            {"actor_id": ACTOR_ID, "workspace_id": WORKSPACE_ID},
        )

    def test_start_rejects_client_provenance_fields(self) -> None:
        forbidden = (
            {"threadId": "client-thread"},
            {"workflowRunId": "run_" + "9" * 32},
            {"bindingRevision": 999},
            {"sourceMessageId": "client-message"},
        )
        with TestClient(self.app) as client:
            for extra in forbidden:
                with self.subTest(extra=extra):
                    response = client.post(
                        "/api/story-workspace/dream-runs/start",
                        json={
                            "deckId": DECK_ID,
                            "goal": "目标",
                            "idempotencyKey": "dream-api-strict",
                            **extra,
                        },
                    )
                    self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.gateway.calls, [])

    def test_start_rejects_snake_case_launch_fields(self) -> None:
        with TestClient(self.app) as client:
            response = client.post(
                "/api/story-workspace/dream-runs/start",
                json={
                    "deck_id": DECK_ID,
                    "goal": "目标",
                    "idempotency_key": "dream-api-snake-case",
                },
            )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.gateway.calls, [])

    def test_start_rejects_launch_field_surrounding_or_blank_whitespace(self) -> None:
        invalid_fields = (
            ("deckId", f" {DECK_ID}"),
            ("deckId", f"{DECK_ID} "),
            ("goal", " /drama-forge:drama-init"),
            ("goal", "/drama-forge:drama-init\n"),
            ("goal", "   "),
            ("idempotencyKey", " dream-api-whitespace"),
            ("idempotencyKey", "dream-api-whitespace "),
        )
        with TestClient(self.app) as client:
            for field, value in invalid_fields:
                with self.subTest(field=field, value=value):
                    payload = {
                        "deckId": DECK_ID,
                        "goal": "/drama-forge:drama-init",
                        "idempotencyKey": "dream-api-whitespace",
                    }
                    payload[field] = value
                    response = client.post(
                        "/api/story-workspace/dream-runs/start",
                        json=payload,
                    )
                    self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.gateway.calls, [])


class FakeClaudePluginInstaller:
    def __init__(self, db) -> None:
        self.db = db

    def install(self, package_spec: str, *, source_type: str) -> dict[str, object]:
        self.assert_contract(package_spec, source_type)
        installation_id = "cpi_" + "5" * 32
        digest = plugin_artifact_digest()
        with self.db:
            self.db.execute(
                """
                INSERT OR IGNORE INTO claude_plugin_installations (
                    id, requested_package_spec, package_name, marketplace,
                    requested_version, resolved_version, source_type,
                    artifact_digest, artifact_path, claude_cli_version,
                    status, operation_id, installed_at
                ) VALUES (?, ?, 'ink-dream-story', 'platform-builtin', NULL,
                          '1.0.0', 'platform-builtin', ?, ?, '2.1.220',
                          'ready', ?, CURRENT_TIMESTAMP)
                """,
                (
                    installation_id,
                    package_spec,
                    digest,
                    str(builtin_plugin_path()),
                    "cop_" + "6" * 32,
                ),
            )
        return {"status": "ready", "installation_id": installation_id}

    def get_installation(self, installation_id: str):
        row = self.db.execute(
            "SELECT * FROM claude_plugin_installations WHERE id = ?",
            (installation_id,),
        ).fetchone()
        return dict(row) if row is not None else None

    def verify_installation_artifact(self, record: dict[str, object]) -> bool:
        return (
            record["artifact_digest"] == plugin_artifact_digest()
            and Path(str(record["artifact_path"])).resolve()
            == builtin_plugin_path().resolve()
        )

    @staticmethod
    def assert_contract(package_spec: str, source_type: str) -> None:
        if package_spec != "ink-dream-story@platform-builtin":
            raise AssertionError(package_spec)
        if source_type != "platform-builtin":
            raise AssertionError(source_type)


class RecordingTurnDispatcher:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.failures_remaining = 0

    def __call__(self, **values: object) -> bool:
        self.calls.append(values)
        if self.failures_remaining:
            self.failures_remaining -= 1
            raise RuntimeError("turn dispatch unavailable")
        return True


class DeferredMetadataPersistenceTurnDispatcher:
    """Model the Agent service persisting its accepted request a tick later."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.tasks: list[asyncio.Task[None]] = []

    def __call__(self, **values: object) -> asyncio.Task[None]:
        self.calls.append(values)
        message_id = str(values["message_id"])
        metadata = json.loads(json.dumps(values["metadata"]))

        async def persist_later() -> None:
            await asyncio.sleep(0)
            db = database.get_db()
            try:
                with db:
                    db.execute(
                        "UPDATE chat_message SET metadata = ? WHERE id = ?",
                        (json.dumps(metadata, sort_keys=True), message_id),
                    )
            finally:
                db.close()

        task = asyncio.create_task(persist_later())
        self.tasks.append(task)
        return task


class StoryWorkspaceDreamLaunchProductionTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_path = database.DB_PATH
        self.old_dir = database.DB_DIR
        database.DB_PATH = Path(self.temp_dir.name) / "dream-launch.db"
        database.DB_DIR = database.DB_PATH.parent
        self.environment = patch.dict(
            os.environ,
            {
                "INK_ENVIRONMENT": "test",
                "INK_WORKFLOW_TOKEN_SECRET": (
                    "ink-dream-development-workflow-token-secret-v1"
                ),
            },
            clear=False,
        )
        self.environment.start()
        database.init_db()
        db = database.get_db()
        try:
            with db:
                db.execute(
                    "INSERT INTO users (id, email, password_hash) VALUES (?, ?, 'hash')",
                    (int(ACTOR_ID), "dream-launch@example.test"),
                )
                db.execute(
                    "INSERT INTO users (id, email, password_hash) VALUES (?, ?, 'hash')",
                    (int(OTHER_ACTOR_ID), "dream-launch-other@example.test"),
                )
                db.execute(
                    "INSERT INTO story_workspace_workspaces (id, name, owner_id) "
                    "VALUES (?, 'Dream', ?), (?, 'Other', ?)",
                    (
                        WORKSPACE_ID,
                        int(ACTOR_ID),
                        OTHER_WORKSPACE_ID,
                        int(OTHER_ACTOR_ID),
                    ),
                )
                db.execute(
                    "INSERT INTO decks (id, name, owner_id, enabled) "
                    "VALUES (?, 'Dream Deck', ?, 1)",
                    (DECK_ID, int(ACTOR_ID)),
                )
                db.execute(
                    "INSERT INTO decks (id, name, owner_id, enabled) "
                    "VALUES (?, 'Alternate Dream Deck', ?, 1)",
                    (ALTERNATE_DECK_ID, int(ACTOR_ID)),
                )
        finally:
            db.close()
        self.turn_dispatcher = RecordingTurnDispatcher()

    async def asyncTearDown(self) -> None:
        self.environment.stop()
        database.DB_PATH = self.old_path
        database.DB_DIR = self.old_dir
        self.temp_dir.cleanup()

    def make_gateway(
        self,
        db,
        actor: dict[str, str],
        *,
        dispatch_before_claim=None,
    ):
        application = StoryWorkflowApplicationGateway()
        options = {}
        if dispatch_before_claim is not None:
            options["dispatch_before_claim"] = dispatch_before_claim
        return StoryWorkspaceDreamLaunchGateway(
            db,
            preflight_service=application._preflight_service(db, actor),
            token_secret="ink-dream-development-workflow-token-secret-v1",
            claude_installer_factory=FakeClaudePluginInstaller,
            turn_dispatcher=self.turn_dispatcher,
            **options,
        )

    async def start(
        self,
        command: StoryWorkspaceDreamLaunchCommand,
        actor=None,
        *,
        dispatch_before_claim=None,
    ):
        selected_actor = actor or {
            "actor_id": ACTOR_ID,
            "workspace_id": WORKSPACE_ID,
        }
        db = database.get_db()
        try:
            return await self.make_gateway(
                db,
                selected_actor,
                dispatch_before_claim=dispatch_before_claim,
            ).start(
                command,
                actor=selected_actor,
            )
        finally:
            db.close()

    async def test_provisions_binding_creates_authoritative_run_and_dispatches(self) -> None:
        context = await self.start(launch_command())

        self.assertEqual(context.deck_id, DECK_ID)
        self.assertEqual(context.deck_plugin_id, BUILTIN_DECK_PLUGIN_ID)
        self.assertEqual(BUILTIN_CLAUDE_PLUGIN_ID, "ink-dream-story@platform-builtin")
        db = database.get_db()
        try:
            claude_installation = db.execute(
                "SELECT * FROM claude_plugin_installations"
            ).fetchone()
            materialization = db.execute(
                "SELECT * FROM runtime_plugin_materializations"
            ).fetchone()
            deck_installation = db.execute(
                "SELECT * FROM deck_plugin_installations WHERE scope_id = ?",
                (WORKSPACE_ID,),
            ).fetchone()
            binding = db.execute(
                "SELECT * FROM deck_plugin_bindings WHERE deck_id = ? AND status = 'active'",
                (DECK_ID,),
            ).fetchone()
            adapter_refs = db.execute(
                "SELECT COUNT(*) FROM deck_claude_plugin_refs WHERE deck_id = ?",
                (DECK_ID,),
            ).fetchone()[0]
            source = db.execute(
                "SELECT message.*, thread.deck_id, thread.user_id "
                "FROM chat_message AS message JOIN chat_thread AS thread "
                "ON thread.id = message.thread_id"
            ).fetchone()
            run = db.execute(
                "SELECT * FROM workflow_runs WHERE id = ?",
                (context.workflow_run_id,),
            ).fetchone()
        finally:
            db.close()

        self.assertEqual(claude_installation["status"], "ready")
        self.assertEqual(claude_installation["artifact_digest"], plugin_artifact_digest())
        self.assertEqual(materialization["claude_code_plugin_id"], BUILTIN_CLAUDE_PLUGIN_ID)
        self.assertEqual(materialization["materialized_digest"], plugin_artifact_digest())
        self.assertEqual(deck_installation["status"], "ready")
        self.assertEqual(binding["deck_plugin_id"], BUILTIN_DECK_PLUGIN_ID)
        self.assertEqual(adapter_refs, 0)
        self.assertEqual(source["deck_id"], DECK_ID)
        self.assertEqual(str(source["user_id"]), ACTOR_ID)
        self.assertEqual(run["source_voice_thread_id"], context.thread_id)
        self.assertEqual(run["source_message_id"], source["id"])
        self.assertIsNotNone(run["source_message_time"])

        self.assertEqual(len(self.turn_dispatcher.calls), 1)
        dispatch = self.turn_dispatcher.calls[0]
        self.assertFalse(dispatch["resume"])
        self.assertEqual(dispatch["context"], context)
        launch_text = dispatch["parts"][0]["text"]
        self.assertIn("write_dream_run", launch_text)
        self.assertIn("write_dream_stage", launch_text)
        self.assertIn("AskUserQuestion", launch_text)
        self.assertIn("可编辑草稿", launch_text)

    async def test_replay_and_conflict_preserve_single_source_run_and_dispatch(self) -> None:
        first = await self.start(launch_command())
        second = await self.start(launch_command())
        self.assertEqual(second, first)

        with self.assertRaises(StoryWorkspaceDreamLaunchIdempotencyConflict):
            await self.start(launch_command(goal="不同的故事目标"))

        db = database.get_db()
        try:
            counts = {
                table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in (
                    "chat_thread",
                    "chat_message",
                    "workflow_runs",
                    "deck_plugin_bindings",
                    "deck_plugin_installations",
                    "runtime_plugin_materializations",
                    "claude_plugin_installations",
                )
            }
            metadata = json.loads(
                db.execute("SELECT metadata FROM chat_message").fetchone()[0]
            )
        finally:
            db.close()
        self.assertTrue(all(value == 1 for value in counts.values()), counts)
        self.assertEqual(len(self.turn_dispatcher.calls), 1)
        self.assertEqual(metadata["dispatchStatus"], "dispatched")
        self.assertEqual(metadata["workflowRunId"], first.workflow_run_id)

    async def test_same_key_changed_deck_is_an_idempotency_conflict(self) -> None:
        await self.start(launch_command())

        with self.assertRaises(StoryWorkspaceDreamLaunchIdempotencyConflict):
            await self.start(launch_command(deckId=ALTERNATE_DECK_ID))

        db = database.get_db()
        try:
            alternate_bindings = db.execute(
                "SELECT COUNT(*) FROM deck_plugin_bindings WHERE deck_id = ?",
                (ALTERNATE_DECK_ID,),
            ).fetchone()[0]
        finally:
            db.close()
        self.assertEqual(alternate_bindings, 0)

    async def test_replay_uses_frozen_binding_after_active_revision_drifts(self) -> None:
        first = await self.start(launch_command())
        replacement_binding_id = "dpb_" + "8" * 32
        db = database.get_db()
        try:
            current = db.execute(
                "SELECT * FROM deck_plugin_bindings "
                "WHERE deck_id = ? AND status = 'active'",
                (DECK_ID,),
            ).fetchone()
            with db:
                db.execute(
                    "UPDATE deck_plugin_bindings SET status = 'stale' "
                    "WHERE deck_plugin_binding_id = ?",
                    (current["deck_plugin_binding_id"],),
                )
                db.execute(
                    "INSERT INTO deck_plugin_bindings ("
                    "deck_plugin_binding_id, deck_id, workspace_id, creator_id, "
                    "deck_plugin_id, deck_plugin_version, binding_revision, "
                    "status, applied_to) "
                    "VALUES (?, ?, ?, ?, ?, ?, 2, 'active', 'next_run')",
                    (
                        replacement_binding_id,
                        DECK_ID,
                        WORKSPACE_ID,
                        ACTOR_ID,
                        BUILTIN_DECK_PLUGIN_ID,
                        BUILTIN_DECK_PLUGIN_VERSION,
                    ),
                )
        finally:
            db.close()

        replayed = await self.start(launch_command())

        self.assertEqual(replayed, first)
        self.assertEqual(replayed.binding_revision, 1)
        db = database.get_db()
        try:
            active = db.execute(
                "SELECT deck_plugin_binding_id, binding_revision "
                "FROM deck_plugin_bindings WHERE deck_id = ? AND status = 'active'",
                (DECK_ID,),
            ).fetchone()
        finally:
            db.close()
        self.assertEqual(active["deck_plugin_binding_id"], replacement_binding_id)
        self.assertEqual(active["binding_revision"], 2)
        self.assertEqual(len(self.turn_dispatcher.calls), 1)

    async def test_concurrent_pending_replay_claims_one_agent_turn(self) -> None:
        self.turn_dispatcher.failures_remaining = 1
        with self.assertRaisesRegex(RuntimeError, "turn dispatch unavailable"):
            await self.start(launch_command())

        self.turn_dispatcher = RecordingTurnDispatcher()
        before_claim = threading.Barrier(2)

        def replay():
            return asyncio.run(
                self.start(
                    launch_command(),
                    dispatch_before_claim=lambda: before_claim.wait(timeout=5),
                )
            )

        first, second = await asyncio.gather(
            asyncio.to_thread(replay),
            asyncio.to_thread(replay),
        )

        self.assertEqual(first, second)
        self.assertEqual(len(self.turn_dispatcher.calls), 1)

    async def test_fresh_dispatch_claim_is_not_duplicated(self) -> None:
        self.turn_dispatcher.failures_remaining = 1
        with self.assertRaisesRegex(RuntimeError, "turn dispatch unavailable"):
            await self.start(launch_command())

        self.turn_dispatcher = RecordingTurnDispatcher()
        self._set_dispatch_claim(datetime.now(UTC))

        await self.start(launch_command())

        self.assertEqual(self.turn_dispatcher.calls, [])
        metadata = self._read_source_metadata()
        self.assertEqual(metadata["dispatchStatus"], "dispatching")
        self.assertEqual(metadata["dispatchClaimId"], "claim-from-another-worker")

    async def test_stale_dispatch_claim_is_recovered(self) -> None:
        self.turn_dispatcher.failures_remaining = 1
        with self.assertRaisesRegex(RuntimeError, "turn dispatch unavailable"):
            await self.start(launch_command())

        self.turn_dispatcher = RecordingTurnDispatcher()
        self._set_dispatch_claim(datetime.now(UTC) - timedelta(minutes=10))

        await self.start(launch_command())

        self.assertEqual(len(self.turn_dispatcher.calls), 1)
        metadata = self._read_source_metadata()
        self.assertEqual(metadata["dispatchStatus"], "dispatched")
        self.assertNotIn("dispatchClaimId", metadata)
        self.assertNotIn("dispatchClaimedAt", metadata)

    async def test_agent_metadata_persistence_cannot_restore_dispatch_claim(
        self,
    ) -> None:
        deferred_dispatcher = DeferredMetadataPersistenceTurnDispatcher()
        self.turn_dispatcher = deferred_dispatcher

        await self.start(launch_command())
        await asyncio.gather(*deferred_dispatcher.tasks)

        metadata = self._read_source_metadata()
        self.assertEqual(metadata["dispatchStatus"], "dispatched")
        self.assertNotIn("dispatchClaimId", metadata)
        self.assertNotIn("dispatchClaimedAt", metadata)

    async def test_binding_revision_conflict_adopts_concurrent_builtin_winner(
        self,
    ) -> None:
        binding_id = "dpb_" + "9" * 32

        class ConcurrentWinnerBindingService:
            def __init__(nested_self, db, *, selection_validator) -> None:
                nested_self.db = db

            async def save(nested_self, **_values):
                with nested_self.db:
                    nested_self.db.execute(
                        "INSERT INTO deck_plugin_bindings ("
                        "deck_plugin_binding_id, deck_id, workspace_id, creator_id, "
                        "deck_plugin_id, deck_plugin_version, binding_revision, "
                        "status, applied_to) "
                        "VALUES (?, ?, ?, ?, ?, ?, 1, 'active', 'next_run')",
                        (
                            binding_id,
                            DECK_ID,
                            WORKSPACE_ID,
                            ACTOR_ID,
                            BUILTIN_DECK_PLUGIN_ID,
                            BUILTIN_DECK_PLUGIN_VERSION,
                        ),
                    )
                raise BindingRevisionConflict(1)

        with patch(
            "services.story_workspace.dream_launch_gateway.BindingService",
            ConcurrentWinnerBindingService,
        ):
            context = await self.start(launch_command())

        self.assertEqual(context.deck_plugin_binding_id, binding_id)
        self.assertEqual(context.binding_revision, 1)

    async def test_slash_command_remains_the_unmodified_launch_text_prefix(self) -> None:
        goal = "/drama-forge:drama-init"

        await self.start(launch_command(goal=goal))

        launch_text = self.turn_dispatcher.calls[0]["parts"][0]["text"]
        self.assertTrue(launch_text.startswith(goal))
        self.assertIn("不调用 AskUserQuestion", launch_text)
        self.assertIn("可编辑草稿", launch_text)

    async def test_launch_requires_canonical_project_identity_before_storyboard(self) -> None:
        await self.start(launch_command())

        launch_text = self.turn_dispatcher.calls[0]["parts"][0]["text"]
        self.assertIn("先完成 drama-init 的项目初始化语义", launch_text)
        self.assertIn("stories/<project_slug>/project.yaml", launch_text)
        self.assertIn("project_slug 必须与 project_id 完全相同", launch_text)
        self.assertIn("^[a-z0-9]+(?:-[a-z0-9]+)*$", launch_text)
        self.assertIn("project_name 只用于显示", launch_text)
        self.assertIn("全中文 project_name 不得直接成为物理项目身份", launch_text)
        self.assertIn("稳定 proj-<8位小写十六进制摘要>", launch_text)
        self.assertIn("规范项目身份成立后，才能写入 storyboard", launch_text)
        self.assertNotIn("mcp__", launch_text)
        self.assertNotIn("expectedBindingRevision", launch_text)

    async def test_dispatch_exception_leaves_pending_envelope_replayable(self) -> None:
        self.turn_dispatcher.failures_remaining = 1

        with self.assertRaisesRegex(RuntimeError, "turn dispatch unavailable"):
            await self.start(launch_command())
        db = database.get_db()
        try:
            pending = json.loads(
                db.execute("SELECT metadata FROM chat_message").fetchone()[0]
            )
        finally:
            db.close()
        self.assertEqual(pending["dispatchStatus"], "pending")

        replayed = await self.start(launch_command())
        db = database.get_db()
        try:
            dispatched = json.loads(
                db.execute("SELECT metadata FROM chat_message").fetchone()[0]
            )
            run_count = db.execute("SELECT COUNT(*) FROM workflow_runs").fetchone()[0]
        finally:
            db.close()
        self.assertEqual(dispatched["dispatchStatus"], "dispatched")
        self.assertEqual(dispatched["workflowRunId"], replayed.workflow_run_id)
        self.assertEqual(run_count, 1)
        self.assertEqual(len(self.turn_dispatcher.calls), 2)

    def _set_dispatch_claim(self, claimed_at: datetime) -> None:
        db = database.get_db()
        try:
            row = db.execute("SELECT id, metadata FROM chat_message").fetchone()
            metadata = json.loads(row["metadata"])
            metadata.update({
                "dispatchStatus": "dispatching",
                "dispatchClaimId": "claim-from-another-worker",
                "dispatchClaimedAt": claimed_at.isoformat(),
            })
            with db:
                db.execute(
                    "UPDATE chat_message SET metadata = ? WHERE id = ?",
                    (json.dumps(metadata, sort_keys=True), row["id"]),
                )
        finally:
            db.close()

    @staticmethod
    def _read_source_metadata() -> dict[str, object]:
        db = database.get_db()
        try:
            return json.loads(
                db.execute("SELECT metadata FROM chat_message").fetchone()[0]
            )
        finally:
            db.close()

    async def test_cross_actor_deck_launch_is_denied_before_source_creation(self) -> None:
        with self.assertRaises(PermissionError):
            await self.start(
                launch_command(),
                actor={
                    "actor_id": OTHER_ACTOR_ID,
                    "workspace_id": OTHER_WORKSPACE_ID,
                },
            )

        db = database.get_db()
        try:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM chat_thread").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM chat_message").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM workflow_runs").fetchone()[0], 0)
        finally:
            db.close()

    async def test_legacy_local_builtin_lock_is_repaired_without_deck_refs(self) -> None:
        db = database.get_db()
        try:
            release = db.execute(
                "SELECT manifest_json FROM deck_plugin_releases "
                "WHERE deck_plugin_id = ? AND deck_plugin_version = ?",
                (BUILTIN_DECK_PLUGIN_ID, BUILTIN_DECK_PLUGIN_VERSION),
            ).fetchone()
            manifest = json.loads(release["manifest_json"])
            manifest["runtime"]["claude_code_plugins"][0][
                "claude_code_plugin_id"
            ] = "ink-dream-story@local"
            manifest_json = json.dumps(
                manifest,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            manifest_hash = "sha256:" + hashlib.sha256(
                manifest_json.encode("utf-8")
            ).hexdigest()
            lock_row = db.execute(
                "SELECT lock_json FROM deck_runtime_plugin_locks "
                "WHERE deck_plugin_id = ? AND deck_plugin_version = ?",
                (BUILTIN_DECK_PLUGIN_ID, BUILTIN_DECK_PLUGIN_VERSION),
            ).fetchone()
            runtime_lock = json.loads(lock_row["lock_json"])
            runtime_lock["deck_plugin_manifest_hash"] = manifest_hash
            runtime_lock["claude_code_plugins"][0][
                "claude_code_plugin_id"
            ] = "ink-dream-story@local"
            runtime_lock["production_ready"] = False
            runtime_lock["production_readiness_reasons"] = [
                "repository_local_plugin",
                "development_runtime_only",
            ]
            with db:
                db.execute(
                    "UPDATE deck_plugin_releases SET manifest_json = ?, "
                    "manifest_hash = ?, runtime_spec_json = ? "
                    "WHERE deck_plugin_id = ? AND deck_plugin_version = ?",
                    (
                        manifest_json,
                        manifest_hash,
                        json.dumps(manifest["runtime"], sort_keys=True),
                        BUILTIN_DECK_PLUGIN_ID,
                        BUILTIN_DECK_PLUGIN_VERSION,
                    ),
                )
                db.execute(
                    "UPDATE deck_runtime_plugin_locks SET "
                    "deck_plugin_manifest_hash = ?, lock_json = ? "
                    "WHERE deck_plugin_id = ? AND deck_plugin_version = ?",
                    (
                        manifest_hash,
                        json.dumps(runtime_lock, sort_keys=True),
                        BUILTIN_DECK_PLUGIN_ID,
                        BUILTIN_DECK_PLUGIN_VERSION,
                    ),
                )
        finally:
            db.close()

        context = await self.start(launch_command())

        self.assertEqual(context.deck_plugin_id, BUILTIN_DECK_PLUGIN_ID)
        db = database.get_db()
        try:
            repaired_manifest = json.loads(
                db.execute(
                    "SELECT manifest_json FROM deck_plugin_releases "
                    "WHERE deck_plugin_id = ? AND deck_plugin_version = ?",
                    (BUILTIN_DECK_PLUGIN_ID, BUILTIN_DECK_PLUGIN_VERSION),
                ).fetchone()[0]
            )
            repaired_lock = json.loads(
                db.execute(
                    "SELECT lock_json FROM deck_runtime_plugin_locks "
                    "WHERE deck_plugin_id = ? AND deck_plugin_version = ?",
                    (BUILTIN_DECK_PLUGIN_ID, BUILTIN_DECK_PLUGIN_VERSION),
                ).fetchone()[0]
            )
            deck_ref_count = db.execute(
                "SELECT COUNT(*) FROM deck_claude_plugin_refs WHERE deck_id = ?",
                (DECK_ID,),
            ).fetchone()[0]
        finally:
            db.close()
        self.assertEqual(
            repaired_manifest["runtime"]["claude_code_plugins"][0][
                "claude_code_plugin_id"
            ],
            BUILTIN_CLAUDE_PLUGIN_ID,
        )
        self.assertEqual(
            repaired_lock["claude_code_plugins"][0]["claude_code_plugin_id"],
            BUILTIN_CLAUDE_PLUGIN_ID,
        )
        self.assertTrue(repaired_lock["production_ready"])
        self.assertEqual(deck_ref_count, 0)


if __name__ == "__main__":
    unittest.main()
