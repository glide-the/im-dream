"""Actor-scoped REST projection tests for Dream runtime files."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import database
from tests.legacy_database_fixture import LegacyDatabaseModuleFixture
from models.workflow_run import AuthenticatedActorContext, RunStatus, WorkflowRun
from routers import story_workspace
from services.deck import story_workflow_gateway as gateway_module
from services.errors.error_registry import ApiRouteError, build_error_payload
import services.story_workspace.dream_file_service as dream_files
from services.story_workspace.dream_file_service import (
    StoryWorkspaceDreamContractError,
    StoryWorkspaceDreamDurabilityIndeterminate,
    StoryWorkspaceDreamFileError,
    StoryWorkspaceDreamFileWriter,
    StoryWorkspaceDreamIOError,
    StoryWorkspaceDreamPathError,
    StoryWorkspaceDreamPlatformUnsupported,
)
from services.workflow.run_service import WorkflowRunError
from story_workspace.contracts import (
    StoryWorkspaceDreamFilesResponse,
    StoryWorkspaceDreamSourceResponse,
    StoryWorkspaceDreamStage,
    StoryWorkspaceDreamStageResponse,
)


RUN_ID = "run_0123456789abcdef0123456789abcdef"
OTHER_RUN_ID = "run_fedcba9876543210fedcba9876543210"
THREAD_ID = "thread-1"
WORKSPACE_ID = "workspace-1"
ACTOR_ID = "7"


def authoritative_run(**overrides: object) -> WorkflowRun:
    values: dict[str, object] = {
        "workflow_run_id": RUN_ID,
        "deck_plugin_id": "plugin-1",
        "workflow_definition_ref": "workflow-1",
        "deck_plugin_binding_id": "binding-1",
        "binding_revision": 3,
        "deck_plugin_version": "1.2.3",
        "deck_runtime_snapshot_id": "snapshot-1",
        "runtime_plugin_lock_id": "lock-1",
        "deck_plugin_manifest_hash": "sha256:" + "1" * 64,
        "workflow_preflight_id": "pf_" + "2" * 32,
        "status": RunStatus.PREFLIGHT,
        "workspace_id": WORKSPACE_ID,
        "idempotency_key": "run-request-1",
        "input_hash": "sha256:" + "3" * 64,
        "semantic_fingerprint": "sha256:" + "4" * 64,
        "status_version": 1,
        "created_by": ACTOR_ID,
        "created_at": datetime(2026, 8, 4, tzinfo=timezone.utc),
        "source_voice_thread_id": THREAD_ID,
    }
    values.update(overrides)
    return WorkflowRun(**values)


def waiting_response() -> StoryWorkspaceDreamFilesResponse:
    return StoryWorkspaceDreamFilesResponse(
        story_workspace_run_id=RUN_ID,
        thread_id=THREAD_ID,
        source=StoryWorkspaceDreamSourceResponse(
            deck_plugin_binding_id="binding-1",
            binding_revision=3,
            deck_plugin_version="1.2.3",
            deck_runtime_snapshot_id="snapshot-1",
            runtime_plugin_lock_id="lock-1",
        ),
        required_stages=list(StoryWorkspaceDreamStage),
        run_revision=0,
        stages={},
        can_confirm=False,
    )


def complete_response() -> StoryWorkspaceDreamFilesResponse:
    source_files = {
        StoryWorkspaceDreamStage.CHARACTERS: "assets/characters/lead.md",
        StoryWorkspaceDreamStage.SCENES: "assets/scenes/opening.md",
        StoryWorkspaceDreamStage.STORYBOARDS: (
            "stories/demo/episodes/EP01/storyboard.yaml"
        ),
    }
    titles = {
        StoryWorkspaceDreamStage.CHARACTERS: "人物",
        StoryWorkspaceDreamStage.SCENES: "场景",
        StoryWorkspaceDreamStage.STORYBOARDS: "分镜",
    }
    routes = {
        StoryWorkspaceDreamStage.CHARACTERS: (
            f"/story-workspace/characters?run={RUN_ID}"
        ),
        StoryWorkspaceDreamStage.SCENES: (
            f"/story-workspace/scenes?run={RUN_ID}"
        ),
        StoryWorkspaceDreamStage.STORYBOARDS: (
            f"/story-workspace/runs/{RUN_ID}/execution"
        ),
    }
    stages = {
        stage: StoryWorkspaceDreamStageResponse(
            stage=stage,
            revision=index,
            source_files=[source_files[stage]],
            page={"title": titles[stage], "entry_route": routes[stage]},
            items=[{
                "entity_id": f"entity-{index}",
                "display_name": f"Entity {index}",
                "summary": "summary",
                "source_file": source_files[stage],
                "relations": [],
            }],
        )
        for index, stage in enumerate(StoryWorkspaceDreamStage, start=1)
    }
    return StoryWorkspaceDreamFilesResponse(
        story_workspace_run_id=RUN_ID,
        thread_id=THREAD_ID,
        source=StoryWorkspaceDreamSourceResponse(
            deck_plugin_binding_id="binding-1",
            binding_revision=3,
            deck_plugin_version="1.2.3",
            deck_runtime_snapshot_id="snapshot-1",
            runtime_plugin_lock_id="lock-1",
        ),
        required_stages=list(StoryWorkspaceDreamStage),
        run_revision=1,
        stages=stages,
        can_confirm=True,
    )


class _RecordingGateway:
    def __init__(self, response: StoryWorkspaceDreamFilesResponse) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, str]]] = []

    async def get_dream_files(self, workflow_run_id: str, *, actor: dict[str, str]):
        self.calls.append((workflow_run_id, actor))
        return self.response


class StoryWorkspaceDreamFilesRouteTest(unittest.TestCase):
    def make_client(
        self,
        response: StoryWorkspaceDreamFilesResponse,
    ) -> tuple[TestClient, _RecordingGateway]:
        app = FastAPI()
        gateway = _RecordingGateway(response)
        app.dependency_overrides[story_workspace.get_current_user] = lambda: {
            "user_id": int(ACTOR_ID),
            "workspace_id": WORKSPACE_ID,
        }
        app.dependency_overrides[story_workspace.get_story_workflow_gateway] = (
            lambda: gateway
        )
        app.include_router(story_workspace.router)
        return TestClient(app), gateway

    def test_route_passes_url_run_and_actor_and_uses_camel_aliases(self) -> None:
        client, gateway = self.make_client(complete_response())
        try:
            response = client.get(
                f"/api/story-workspace/workflow-runs/{RUN_ID}/dream-files"
            )
        finally:
            client.close()

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            gateway.calls,
            [(RUN_ID, {"actor_id": ACTOR_ID})],
        )
        payload = response.json()
        self.assertEqual(
            set(payload),
            {
                "storyWorkspaceRunId",
                "threadId",
                "source",
                "requiredStages",
                "runRevision",
                "stages",
                "canConfirm",
                "confirmationAccepted",
                "confirmationDispatched",
                "confirmationLabel",
            },
        )
        self.assertFalse(payload["confirmationAccepted"])
        self.assertFalse(payload["confirmationDispatched"])
        self.assertEqual(
            set(payload["source"]),
            {
                "deckPluginBindingId",
                "bindingRevision",
                "deckPluginVersion",
                "deckRuntimeSnapshotId",
                "runtimePluginLockId",
            },
        )
        character = payload["stages"]["characters"]
        self.assertIn("sourceFiles", character)
        self.assertIn("entryRoute", character["page"])
        self.assertIn("entityId", character["items"][0])
        self.assertFalse(any("_" in key for key in payload))

    def test_existing_run_endpoint_remains_snake_case(self) -> None:
        class RunGateway(_RecordingGateway):
            async def get_run(self, workflow_run_id: str, *, actor: dict[str, str]):
                return {
                    "workflow_run_id": workflow_run_id,
                    "source_voice_thread_id": THREAD_ID,
                }

        app = FastAPI()
        gateway = RunGateway(waiting_response())
        app.dependency_overrides[story_workspace.get_current_user] = lambda: {
            "user_id": int(ACTOR_ID),
            "workspace_id": WORKSPACE_ID,
        }
        app.dependency_overrides[story_workspace.get_story_workflow_gateway] = (
            lambda: gateway
        )
        app.include_router(story_workspace.router)
        with TestClient(app) as client:
            response = client.get(f"/api/story-workspace/workflow-runs/{RUN_ID}")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("workflow_run_id", response.json())
        self.assertNotIn("workflowRunId", response.json())

    def test_unexpected_gateway_failure_is_safe_and_never_returns_success(self) -> None:
        class BrokenGateway(_RecordingGateway):
            async def get_dream_files(
                self,
                workflow_run_id: str,
                *,
                actor: dict[str, str],
            ):
                raise RuntimeError("internal /private/workspace")

        app = FastAPI()
        gateway = BrokenGateway(waiting_response())
        app.dependency_overrides[story_workspace.get_current_user] = lambda: {
            "user_id": int(ACTOR_ID),
            "workspace_id": WORKSPACE_ID,
        }
        app.dependency_overrides[story_workspace.get_story_workflow_gateway] = (
            lambda: gateway
        )
        app.include_router(story_workspace.router)
        with TestClient(app) as client:
            response = client.get(
                f"/api/story-workspace/workflow-runs/{RUN_ID}/dream-files"
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["error"]["code"],
            "DECK_RUNTIME_CONFIG_UNAVAILABLE",
        )
        self.assertNotIn("/private/workspace", response.text)

    def test_jwt_without_workspace_never_creates_one_for_dream_get(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_fixture = LegacyDatabaseModuleFixture(
                database,
                Path(temporary_directory) / "read-only-route.db",
            )
            database_fixture.start()
            try:
                db = database.get_db()
                db.execute(
                    """
                    CREATE TABLE story_workspace_workspaces (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        owner_id INTEGER NOT NULL,
                        settings TEXT NOT NULL DEFAULT '{}',
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                db.commit()
                db.close()

                app = FastAPI()
                app.dependency_overrides[story_workspace.get_current_user] = lambda: {
                    "user_id": int(ACTOR_ID),
                    "email": "writer@example.com",
                }
                app.dependency_overrides[
                    story_workspace.get_story_workflow_gateway
                ] = gateway_module.StoryWorkflowApplicationGateway
                app.include_router(story_workspace.router)

                creator = story_workspace.get_or_create_default_workspace
                with (
                    patch.object(
                        story_workspace,
                        "get_or_create_default_workspace",
                        wraps=creator,
                    ) as create_workspace,
                    TestClient(app) as client,
                ):
                    response = client.get(
                        f"/api/story-workspace/workflow-runs/{RUN_ID}/dream-files"
                    )

                db = database.get_db()
                count = db.execute(
                    "SELECT COUNT(*) FROM story_workspace_workspaces"
                ).fetchone()[0]
                db.close()
            finally:
                database_fixture.stop()

        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(response.json()["error"]["code"], "WORKFLOW_PERMISSION_DENIED")
        create_workspace.assert_not_called()
        self.assertEqual(count, 0)

    def test_route_passes_only_actor_and_does_not_resolve_workspace(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_fixture = LegacyDatabaseModuleFixture(
                database,
                Path(temporary_directory) / "read-only-route.db",
            )
            database_fixture.start()
            try:
                db = database.get_db()
                db.execute(
                    """
                    CREATE TABLE story_workspace_workspaces (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        owner_id INTEGER NOT NULL,
                        settings TEXT NOT NULL DEFAULT '{}',
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                db.executemany(
                    "INSERT INTO story_workspace_workspaces "
                    "(id, name, owner_id, created_at) VALUES (?, ?, ?, ?)",
                    [
                        ("workspace-new", "New", int(ACTOR_ID), "2026-08-04"),
                        ("workspace-old", "Old", int(ACTOR_ID), "2026-08-01"),
                    ],
                )
                db.commit()
                db.close()

                app = FastAPI()
                gateway = _RecordingGateway(waiting_response())
                app.dependency_overrides[story_workspace.get_current_user] = lambda: {
                    "user_id": int(ACTOR_ID),
                    "email": "writer@example.com",
                }
                app.dependency_overrides[
                    story_workspace.get_story_workflow_gateway
                ] = lambda: gateway
                app.include_router(story_workspace.router)

                creator = story_workspace.get_or_create_default_workspace
                with (
                    patch.object(
                        story_workspace,
                        "get_or_create_default_workspace",
                        wraps=creator,
                    ) as create_workspace,
                    patch.object(
                        story_workspace.database,
                        "get_db",
                        side_effect=AssertionError(
                            "route dependency must not access the database"
                        ),
                    ) as route_get_db,
                    TestClient(app) as client,
                ):
                    response = client.get(
                        f"/api/story-workspace/workflow-runs/{RUN_ID}/dream-files"
                    )

                db = database.get_db()
                count = db.execute(
                    "SELECT COUNT(*) FROM story_workspace_workspaces"
                ).fetchone()[0]
                db.close()
            finally:
                database_fixture.stop()

        self.assertEqual(response.status_code, 200, response.text)
        create_workspace.assert_not_called()
        route_get_db.assert_not_called()
        self.assertEqual(count, 2)
        self.assertEqual(
            gateway.calls,
            [(RUN_ID, {"actor_id": ACTOR_ID})],
        )

    def test_dream_get_database_failures_are_registered_503_responses(self) -> None:
        cases: list[tuple[str, object]] = []
        cases.append(("get_db", RuntimeError("get_db /private/database")))

        select_db = Mock()
        select_db.execute.side_effect = sqlite3.OperationalError(
            "select /private/database"
        )
        cases.append(("select", select_db))

        close_db = Mock()
        close_db.execute.return_value.fetchone.return_value = None
        close_db.close.side_effect = RuntimeError("close /private/database")
        cases.append(("close", close_db))

        for name, failure in cases:
            with self.subTest(case=name):
                app = FastAPI()
                app.dependency_overrides[story_workspace.get_current_user] = lambda: {
                    "user_id": int(ACTOR_ID),
                    "email": "writer@example.com",
                }
                app.dependency_overrides[
                    story_workspace.get_story_workflow_gateway
                ] = gateway_module.StoryWorkflowApplicationGateway
                app.include_router(story_workspace.router)

                get_db = (
                    patch.object(
                        gateway_module.database,
                        "get_db",
                        side_effect=failure,
                    )
                    if name == "get_db"
                    else patch.object(
                        gateway_module.database,
                        "get_db",
                        return_value=failure,
                    )
                )
                with get_db, TestClient(
                    app,
                    raise_server_exceptions=False,
                ) as client:
                    response = client.get(
                        f"/api/story-workspace/workflow-runs/{RUN_ID}/dream-files"
                    )

                self.assertEqual(response.status_code, 503, response.text)
                self.assertEqual(
                    response.json()["error"]["code"],
                    "DECK_RUNTIME_CONFIG_UNAVAILABLE",
                )
                self.assertNotIn("/private/database", response.text)


class StoryWorkspaceDreamFilesGatewayTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name) / "workspaces"
        self.root.mkdir()
        self.workspace = self.root / THREAD_ID
        self.workspace.mkdir()
        self.dream = self.workspace / ".dream"
        self.dream.mkdir()
        (self.dream / "README.md").write_text("static\n", encoding="utf-8")
        (self.dream / "workspace.json").write_text(
            '{"schema_version":"dream-surface/v1"}\n', encoding="utf-8"
        )
        self.run = authoritative_run()
        self.gateway = gateway_module.StoryWorkflowApplicationGateway()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @staticmethod
    def tree_snapshot(root: Path) -> list[tuple[str, str, bytes | None]]:
        snapshot: list[tuple[str, str, bytes | None]] = []
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                snapshot.append((relative, "symlink", os.readlink(path).encode()))
            elif path.is_dir():
                snapshot.append((relative, "dir", None))
            else:
                snapshot.append((relative, "file", path.read_bytes()))
        return snapshot

    @contextmanager
    def wired(
        self,
        *,
        run: WorkflowRun | None = None,
        run_error: WorkflowRunError | None = None,
        thread: dict[str, object] | None = None,
        root: Path | None = None,
    ):
        db = Mock()
        selected_run = run or self.run
        owner_cursor = Mock()
        owner_cursor.fetchone.return_value = {"id": "discarded-owner-workspace"}
        run_cursor = Mock()
        run_cursor.fetchone.return_value = {
            "workspace_id": selected_run.workspace_id,
        }
        confirmation_cursor = Mock()
        confirmation_cursor.fetchall.return_value = []

        def execute(query, _params=()):
            if "FROM workflow_runs" in query:
                return run_cursor
            if "FROM chat_message" in query:
                return confirmation_cursor
            return owner_cursor

        db.execute.side_effect = execute
        selected_thread = {"id": THREAD_ID, "user_id": int(ACTOR_ID)}
        if thread is not None:
            selected_thread = thread
        with (
            patch.dict(os.environ, {"INK_ENVIRONMENT": "test"}),
            patch.object(gateway_module.database, "get_db", return_value=db),
            patch.object(gateway_module, "WorkflowRunService") as service_class,
            patch.object(
                gateway_module.database,
                "get_chat_thread",
                return_value=selected_thread,
            ) as get_thread,
            patch.object(
                gateway_module,
                "story_workspace_get_workspace_root",
                return_value=root or self.root,
            ),
        ):
            read_run = service_class.return_value.read_run
            if run_error is not None:
                read_run.side_effect = run_error
            else:
                read_run.return_value = selected_run
            yield read_run, get_thread, db

    async def call(self):
        return await self.gateway.get_dream_files(
            RUN_ID,
            actor={"actor_id": ACTOR_ID},
        )

    async def test_uses_canonical_workspace_root_without_optional_agent_sdk(
        self,
    ) -> None:
        with patch.dict(os.environ, {"AGENT_CWD": str(self.root)}):
            self.assertEqual(
                gateway_module.story_workspace_get_workspace_root(),
                self.root,
            )

    async def test_owner_read_uses_scoped_run_and_owned_original_thread(self) -> None:
        with self.wired() as (read_run, get_thread, db):
            result = await self.call()

        read_run.assert_called_once_with(
            RUN_ID,
            AuthenticatedActorContext(
                workspace_id=WORKSPACE_ID,
                actor_id=ACTOR_ID,
            ),
        )
        get_thread.assert_called_once_with(THREAD_ID, int(ACTOR_ID))
        run_scope_queries = [
            call.args
            for call in db.execute.call_args_list
            if "FROM workflow_runs" in call.args[0]
        ]
        self.assertEqual(len(run_scope_queries), 1)
        self.assertEqual(
            run_scope_queries[0][1],
            (RUN_ID, ACTOR_ID, int(ACTOR_ID)),
        )
        db.close.assert_called_once_with()
        self.assertEqual(result.story_workspace_run_id, RUN_ID)

    async def test_actor_with_multiple_workspaces_uses_run_owned_workspace(self) -> None:
        selected_workspace = "workspace-newer-owned-by-run"
        selected_run = authoritative_run(workspace_id=selected_workspace)
        with self.wired(run=selected_run) as (read_run, _, _):
            result = await self.call()

        read_run.assert_called_once_with(
            RUN_ID,
            AuthenticatedActorContext(
                workspace_id=selected_workspace,
                actor_id=ACTOR_ID,
            ),
        )
        self.assertEqual(result.story_workspace_run_id, RUN_ID)

    async def test_static_workspace_is_waiting_and_get_writes_nothing(self) -> None:
        before = self.tree_snapshot(self.root)
        with self.wired():
            result = await self.call()
        self.assertEqual(result.run_revision, 0)
        self.assertEqual(result.stages, {})
        self.assertFalse(result.can_confirm)
        self.assertEqual(self.tree_snapshot(self.root), before)
        self.assertFalse((self.dream / "runtime").exists())

        run_directory = self.dream / "runtime" / "runs" / RUN_ID
        run_directory.mkdir(parents=True)
        before = self.tree_snapshot(self.root)
        with self.wired():
            result = await self.call()
        self.assertEqual(result.run_revision, 0)
        self.assertEqual(result.stages, {})
        self.assertFalse(result.can_confirm)
        self.assertEqual(self.tree_snapshot(self.root), before)

    async def test_complete_three_stage_projection_has_source_and_is_confirmable(
        self,
    ) -> None:
        sources = {
            StoryWorkspaceDreamStage.CHARACTERS: "assets/characters/lead.md",
            StoryWorkspaceDreamStage.SCENES: "assets/scenes/opening.md",
            StoryWorkspaceDreamStage.STORYBOARDS: (
                "stories/demo/episodes/EP01/storyboard.yaml"
            ),
        }
        for relative in sources.values():
            path = self.workspace / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("canonical\n", encoding="utf-8")
        writer = StoryWorkspaceDreamFileWriter(self.workspace)
        writer.write_run(self.run, thread_id=THREAD_ID, expected_revision=0)
        for index, (stage, source_file) in enumerate(sources.items(), start=1):
            writer.write_stage(
                self.run,
                stage=stage,
                source_files=[source_file],
                items=[{
                    "entity_id": f"entity-{index}",
                    "display_name": f"Entity {index}",
                    "summary": "summary",
                    "source_file": source_file,
                    "relations": [],
                }],
                expected_revision=0,
            )

        before = self.tree_snapshot(self.root)
        with self.wired():
            result = await self.call()
        wire = result.model_dump(mode="json", by_alias=True)
        self.assertEqual(set(wire["stages"]), {"characters", "scenes", "storyboards"})
        self.assertEqual(wire["runRevision"], 1)
        self.assertTrue(wire["canConfirm"])
        self.assertEqual(len(wire["source"]), 5)
        self.assertEqual(self.tree_snapshot(self.root), before)

    async def test_persisted_confirmation_fact_disables_confirmation(self) -> None:
        reader = Mock()
        reader.workspace_root = self.workspace.resolve()
        reader.read.return_value = complete_response()
        with (
            self.wired(),
            patch.object(
                gateway_module,
                "StoryWorkspaceDreamFileReader",
                return_value=reader,
            ),
            patch.object(
                gateway_module,
                "story_workspace_read_dream_confirmation_fact",
                return_value=(True, True),
            ) as read_confirmation,
        ):
            result = await self.call()

        read_confirmation.assert_called_once()
        _, fact_kwargs = read_confirmation.call_args
        self.assertEqual(
            fact_kwargs,
            {
                "actor_id": ACTOR_ID,
                "thread_id": THREAD_ID,
                "run_id": RUN_ID,
            },
        )
        self.assertTrue(result.confirmation_accepted)
        self.assertTrue(result.confirmation_dispatched)
        self.assertFalse(result.can_confirm)

    async def test_other_actor_run_and_other_actor_thread_are_not_disclosed(self) -> None:
        with self.wired(
            run_error=WorkflowRunError("WORKFLOW_RUN_NOT_FOUND", "private run path")
        ):
            with self.assertRaises(ApiRouteError) as hidden_run:
                await self.call()
        self.assertEqual(hidden_run.exception.status_code, 404)
        self.assertNotIn("private run path", json.dumps(
            build_error_payload(hidden_run.exception.code)
        ))

        with self.wired() as (_, get_thread, _):
            get_thread.return_value = None
            with self.assertRaises(ApiRouteError) as hidden_thread:
                await self.call()
        self.assertEqual(hidden_thread.exception.status_code, 404)
        self.assertEqual(hidden_thread.exception.code, "WORKFLOW_PERMISSION_DENIED")

    async def test_run_without_source_thread_is_rejected(self) -> None:
        with self.wired(run=authoritative_run(source_voice_thread_id=None)):
            with self.assertRaises(ApiRouteError) as raised:
                await self.call()
        self.assertEqual(
            (raised.exception.code, raised.exception.status_code),
            ("OUTPUT_CONTRACT_INVALID", 422),
        )

    async def test_missing_workspace_is_not_created(self) -> None:
        shutil.rmtree(self.workspace)
        with self.wired():
            with self.assertRaises(ApiRouteError) as raised:
                await self.call()
        self.assertEqual(raised.exception.status_code, 404)
        self.assertFalse(self.workspace.exists())

    async def test_missing_static_dream_directory_is_not_a_waiting_success(self) -> None:
        shutil.rmtree(self.dream)
        with self.wired():
            with self.assertRaises(ApiRouteError) as raised:
                await self.call()
        self.assertEqual(
            (raised.exception.code, raised.exception.status_code),
            ("OUTPUT_CONTRACT_INVALID", 422),
        )
        self.assertFalse(self.dream.exists())

    async def test_workspace_symlink_and_escape_are_rejected(self) -> None:
        external = Path(self.temporary_directory.name) / "external"
        external.mkdir()
        shutil.rmtree(self.workspace)
        self.workspace.symlink_to(external, target_is_directory=True)
        with self.wired():
            with self.assertRaises(ApiRouteError) as symlinked:
                await self.call()
        self.assertEqual(
            (symlinked.exception.code, symlinked.exception.status_code),
            ("WORKFLOW_PERMISSION_DENIED", 403),
        )

        escaping_run = authoritative_run(source_voice_thread_id="../external")
        with self.wired(
            run=escaping_run,
            thread={"id": "../external", "user_id": int(ACTOR_ID)},
        ):
            with self.assertRaises(ApiRouteError) as escaped:
                await self.call()
        self.assertEqual(
            (escaped.exception.code, escaped.exception.status_code),
            ("WORKFLOW_PERMISSION_DENIED", 403),
        )

    async def test_workspace_swap_to_external_symlink_before_reader_is_rejected(
        self,
    ) -> None:
        external = Path(self.temporary_directory.name) / "external"
        external.mkdir()
        external_dream = external / ".dream"
        external_dream.mkdir()
        (external_dream / "README.md").write_text("external\n", encoding="utf-8")
        (external_dream / "workspace.json").write_text(
            '{"schema_version":"dream-surface/v1"}\n', encoding="utf-8"
        )
        original_workspace = self.root / "thread-original"
        canonical_workspace = self.workspace.resolve()
        real_reader = gateway_module.StoryWorkspaceDreamFileReader

        def swap_then_construct(workspace: Path):
            self.workspace.rename(original_workspace)
            self.workspace.symlink_to(external, target_is_directory=True)
            return real_reader(workspace)

        with (
            self.wired(),
            patch.object(
                gateway_module,
                "StoryWorkspaceDreamFileReader",
                side_effect=swap_then_construct,
            ) as construct_reader,
        ):
            with self.assertRaises(ApiRouteError) as raised:
                await self.call()

        construct_reader.assert_called_once_with(canonical_workspace)
        self.assertEqual(
            (raised.exception.code, raised.exception.status_code),
            ("WORKFLOW_PERMISSION_DENIED", 403),
        )
        self.assertNotEqual(external.resolve(), original_workspace.resolve())

    async def test_workspace_root_swap_after_reader_validation_is_rejected(
        self,
    ) -> None:
        writer = StoryWorkspaceDreamFileWriter(self.workspace)
        writer.write_run(self.run, thread_id=THREAD_ID, expected_revision=0)

        external_root = Path(self.temporary_directory.name) / "external-root"
        external_workspace = external_root / THREAD_ID
        external_dream = external_workspace / ".dream"
        external_dream.mkdir(parents=True)
        (external_dream / "README.md").write_text("external\n", encoding="utf-8")
        (external_dream / "workspace.json").write_text(
            '{"schema_version":"dream-surface/v1"}\n', encoding="utf-8"
        )
        StoryWorkspaceDreamFileWriter(external_workspace).write_run(
            self.run,
            thread_id=THREAD_ID,
            expected_revision=0,
        )

        displaced_root = Path(self.temporary_directory.name) / "original-root"
        real_reader = gateway_module.StoryWorkspaceDreamFileReader

        def construct_reader(workspace: Path):
            reader = real_reader(workspace)
            original_read = reader.read

            def swap_root_then_read(*args, **kwargs):
                self.root.rename(displaced_root)
                self.root.symlink_to(external_root, target_is_directory=True)
                return original_read(*args, **kwargs)

            reader.read = Mock(side_effect=swap_root_then_read)
            return reader

        with (
            self.wired(),
            patch.object(
                gateway_module,
                "StoryWorkspaceDreamFileReader",
                side_effect=construct_reader,
            ),
        ):
            with self.assertRaises(ApiRouteError) as raised:
                await self.call()

        self.assertEqual(
            (raised.exception.code, raised.exception.status_code),
            ("WORKFLOW_PERMISSION_DENIED", 403),
        )

    async def test_writer_lock_does_not_block_asyncio_timer(self) -> None:
        writer = StoryWorkspaceDreamFileWriter(self.workspace)
        writer.write_run(self.run, thread_id=THREAD_ID, expected_revision=0)
        run_directory = self.dream / "runtime" / "runs" / RUN_ID
        lock_ready = threading.Event()

        def hold_writer_lock() -> None:
            descriptor = os.open(run_directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                dream_files.fcntl.flock(descriptor, dream_files.fcntl.LOCK_EX)
                lock_ready.set()
                time.sleep(0.3)
                dream_files.fcntl.flock(descriptor, dream_files.fcntl.LOCK_UN)
            finally:
                os.close(descriptor)

        lock_thread = threading.Thread(target=hold_writer_lock)
        lock_thread.start()
        self.assertTrue(lock_ready.wait(1))

        async def timer_elapsed() -> float:
            started = asyncio.get_running_loop().time()
            await asyncio.sleep(0.05)
            return asyncio.get_running_loop().time() - started

        try:
            with self.wired():
                elapsed, result = await asyncio.gather(timer_elapsed(), self.call())
        finally:
            lock_thread.join(timeout=1)

        self.assertLess(elapsed, 0.15)
        self.assertEqual(result.run_revision, 1)

    async def test_malformed_storage_maps_to_safe_contract_error(self) -> None:
        run_directory = self.dream / "runtime" / "runs" / RUN_ID
        run_directory.mkdir(parents=True)
        (run_directory / "run.json").write_text(
            '{"schema_version":"dream-run/v1","private_path":"/secret/home"}',
            encoding="utf-8",
        )
        with self.wired():
            with self.assertRaises(ApiRouteError) as raised:
                await self.call()
        self.assertEqual(
            (raised.exception.code, raised.exception.status_code),
            ("OUTPUT_CONTRACT_INVALID", 422),
        )
        public = json.dumps(build_error_payload(raised.exception.code))
        self.assertNotIn("/secret/home", public)
        self.assertNotIn("run.json", public)

    async def test_reader_errors_have_stable_allowlisted_mappings(self) -> None:
        cases = (
            (
                StoryWorkspaceDreamContractError("schema /private/path"),
                "OUTPUT_CONTRACT_INVALID",
                422,
            ),
            (
                StoryWorkspaceDreamPathError("symlink /private/path"),
                "WORKFLOW_PERMISSION_DENIED",
                403,
            ),
            (
                StoryWorkspaceDreamDurabilityIndeterminate(1, "private-state"),
                "RESULT_COMMIT_FAILED",
                409,
            ),
            (
                StoryWorkspaceDreamIOError("disk /private/path"),
                "DECK_RUNTIME_CONFIG_UNAVAILABLE",
                503,
            ),
            (
                StoryWorkspaceDreamPlatformUnsupported("kernel /private/path"),
                "AGENT_EXECUTION_FAILED",
                501,
            ),
            (
                StoryWorkspaceDreamFileError("unknown /private/path"),
                "AGENT_EXECUTION_FAILED",
                422,
            ),
        )
        for error, code, status in cases:
            with self.subTest(error=type(error).__name__):
                reader = Mock()
                reader.workspace_root = self.workspace.resolve()
                reader.read.side_effect = error
                with (
                    self.wired(),
                    patch.object(
                        gateway_module,
                        "StoryWorkspaceDreamFileReader",
                        return_value=reader,
                    ),
                ):
                    with self.assertRaises(ApiRouteError) as raised:
                        await self.call()
                self.assertEqual(
                    (raised.exception.code, raised.exception.status_code),
                    (code, status),
                )
                payload = json.dumps(build_error_payload(code))
                self.assertNotIn("/private/path", payload)
                self.assertNotIn("private-state", payload)

    async def test_get_never_calls_workspace_creator_or_packer(self) -> None:
        with (
            self.wired(),
            patch.object(
                story_workspace,
                "get_or_create_default_workspace",
                side_effect=AssertionError("GET must not create a workspace"),
            ) as create_workspace,
            patch.object(
                gateway_module,
                "pack_workspace_plugins",
                create=True,
                side_effect=AssertionError("GET must not pack plugins"),
            ) as pack_plugins,
        ):
            result = await self.call()
        self.assertEqual(result.run_revision, 0)
        create_workspace.assert_not_called()
        pack_plugins.assert_not_called()


if __name__ == "__main__":
    unittest.main()
