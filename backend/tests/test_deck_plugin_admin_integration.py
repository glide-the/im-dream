from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

import database
from routers import deck_plugins, story_workspace
from services.deck.builtin_plugin import (
    BUILTIN_DECK_PLUGIN_ID,
    BUILTIN_DECK_PLUGIN_VERSION,
    BUILTIN_SOURCE_REF,
    builtin_plugin_path,
)
from services.deck.chat_context import DeckChatContextService


class DeckPluginAdminIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._old_path = database.DB_PATH
        self._old_dir = database.DB_DIR
        database.DB_PATH = Path(self._tmp.name) / "deck-admin.db"
        database.DB_DIR = database.DB_PATH.parent
        with patch.dict(os.environ, {"INK_ENVIRONMENT": "test"}, clear=False):
            database.init_db()
        db = database.get_db()
        try:
            with db:
                db.execute(
                    """
                    INSERT INTO users (id, email, password_hash, display_name, role)
                    VALUES (101, 'deck-admin@example.test', 'unused', 'Deck Admin', 'admin')
                    """
                )
        finally:
            db.close()

        self.app = FastAPI()
        self.app.dependency_overrides[deck_plugins.get_current_user] = lambda: {
            "user_id": 101,
            "email": "deck-admin@example.test",
            "role": "admin",
        }
        self.app.dependency_overrides[story_workspace.get_current_user] = lambda: {
            "user_id": 101,
            "email": "deck-admin@example.test",
            "role": "admin",
        }
        self.app.include_router(deck_plugins.router)
        self.app.include_router(story_workspace.router)
        self._environment = patch.dict(os.environ, {"INK_ENVIRONMENT": "test"}, clear=False)
        self._environment.start()

    def tearDown(self) -> None:
        self._environment.stop()
        database.DB_PATH = self._old_path
        database.DB_DIR = self._old_dir
        self._tmp.cleanup()

    def test_install_list_and_readiness_use_real_materialized_plugin(self) -> None:
        with TestClient(self.app) as client:
            preview = client.get(
                f"/api/deck-plugins/{BUILTIN_DECK_PLUGIN_ID}/versions/"
                f"{BUILTIN_DECK_PLUGIN_VERSION}"
            )
            self.assertEqual(preview.status_code, 200, preview.text)
            self.assertEqual(preview.json()["status"], "uninstalled")

            installed = client.post(
                "/api/deck-plugins/install",
                json={
                    "deck_plugin_id": BUILTIN_DECK_PLUGIN_ID,
                    "deck_plugin_version": BUILTIN_DECK_PLUGIN_VERSION,
                    "source_type": "controlled",
                    "source": BUILTIN_SOURCE_REF,
                },
            )
            self.assertEqual(installed.status_code, 202, installed.text)
            self.assertEqual(installed.json()["status"], "completed")

            catalog = client.get("/api/deck-plugins/installations")
            self.assertEqual(catalog.status_code, 200, catalog.text)
            self.assertTrue(catalog.json()["permissions"]["can_manage"])
            self.assertEqual(catalog.json()["installations"][0]["status"], "ready")

            readiness = client.get(
                f"/api/deck-plugins/{BUILTIN_DECK_PLUGIN_ID}/runtime-readiness"
            )
            self.assertEqual(readiness.status_code, 200, readiness.text)
            self.assertEqual(readiness.json()["materialization_status"], "materialized")
            self.assertEqual(readiness.json()["activation_status"], "loadable")

        db = database.get_db()
        try:
            materialization = db.execute(
                """
                SELECT cache_ref, verification_status, materialization_status,
                       activation_status
                FROM runtime_plugin_materializations
                """
            ).fetchone()
        finally:
            db.close()
        self.assertEqual(Path(materialization["cache_ref"]), builtin_plugin_path().resolve())
        self.assertEqual(materialization["verification_status"], "verified")
        self.assertEqual(materialization["materialization_status"], "materialized")
        self.assertEqual(materialization["activation_status"], "loadable")

        deck_id = database.create_deck(101, "Dream Story Deck")
        db = database.get_db()
        try:
            workspace_id = db.execute(
                "SELECT id FROM story_workspace_workspaces WHERE owner_id = '101'"
            ).fetchone()["id"]
            with db:
                db.execute(
                    """
                    INSERT INTO deck_plugin_bindings (
                        deck_plugin_binding_id, deck_id, workspace_id, creator_id,
                        deck_plugin_id, deck_plugin_version, binding_revision,
                        status, applied_to
                    ) VALUES ('dpb_11111111111111111111111111111111', ?, ?, '101', ?, ?, 1,
                              'active', 'next_run')
                    """,
                    (deck_id, workspace_id, BUILTIN_DECK_PLUGIN_ID, BUILTIN_DECK_PLUGIN_VERSION),
                )
            context = asyncio.run(
                DeckChatContextService(db).resolve(deck_id=deck_id, actor_id="101")
            )
        finally:
            db.close()
        self.assertEqual(context.claude_plugin_paths, (str(builtin_plugin_path().resolve()),))
        self.assertIsNone(context.claude_settings_json)

        with TestClient(self.app) as client:
            preflight_response = client.post(
                "/api/story-workspace/workflow-preflights",
                json={
                    "deck_id": deck_id,
                    "binding_revision": 1,
                    "input": {"intent": "create_story", "message": "A quiet moonlit archive"},
                },
            )
            self.assertEqual(preflight_response.status_code, 202, preflight_response.text)
            preflight = preflight_response.json()
            self.assertEqual(preflight["status"], "passed", preflight)
            self.assertTrue(preflight["preflight_token"].startswith("pft_"))

            run_response = client.post(
                "/api/story-workspace/workflow-runs",
                json={
                    "workflow_preflight_id": preflight["workflow_preflight_id"],
                    "preflight_token": preflight["preflight_token"],
                    "idempotency_key": "dream-story-run-1",
                },
            )
            self.assertEqual(run_response.status_code, 201, run_response.text)
            run = run_response.json()
            self.assertEqual(run["status"], "queued")

            fetched = client.get(
                f"/api/story-workspace/workflow-runs/{run['workflow_run_id']}"
            )
            self.assertEqual(fetched.status_code, 200, fetched.text)
            self.assertEqual(fetched.json()["deck_runtime_snapshot_id"], preflight["deck_runtime_snapshot_id"])

            cancelled = client.post(
                f"/api/story-workspace/workflow-runs/{run['workflow_run_id']}/cancel",
                json={},
            )
            self.assertEqual(cancelled.status_code, 200, cancelled.text)
            self.assertEqual(cancelled.json()["status"], "cancelled")

    def test_install_rejects_a_browser_supplied_local_path(self) -> None:
        with TestClient(self.app) as client:
            response = client.post(
                "/api/deck-plugins/install",
                json={
                    "deck_plugin_id": BUILTIN_DECK_PLUGIN_ID,
                    "deck_plugin_version": BUILTIN_DECK_PLUGIN_VERSION,
                    "source_type": "local",
                    "source": "/tmp/untrusted-plugin",
                },
            )
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(response.json()["error"]["code"], "DECK_PLUGIN_SOURCE_DENIED")


if __name__ == "__main__":
    unittest.main()
import asyncio
