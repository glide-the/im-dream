"""Active Deck Plugin install/list/readiness integration coverage.

[Sync] 2026-09-16: remove the retired local Deck refs/Chat/Workflow SQL fragment.
"""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

import database
from models.deck_plugin import DeckRuntimePluginLock
from models.runtime_plugin import compute_artifact_set_hash
from routers import deck_plugins, story_workspace
from tests.legacy_database_fixture import LegacyDatabaseModuleFixture
from services.deck.builtin_plugin import (
    BUILTIN_DECK_PLUGIN_ID,
    BUILTIN_DECK_PLUGIN_VERSION,
    BUILTIN_SOURCE_REF,
    builtin_plugin_path,
    seed_builtin_deck_plugin,
)


class DeckPluginAdminIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._database_fixture = LegacyDatabaseModuleFixture(
            database,
            Path(self._tmp.name) / "deck-admin.db",
        )
        self._database_fixture.start(initialize_legacy_schema=True)
        db = database.get_db()
        try:
            with db:
                db.execute(
                    """
                    INSERT INTO users (id, email, password_hash, display_name, role)
                    VALUES (101, 'deck-admin@example.test', 'unused', 'Deck Admin', 'admin')
                    """
                )
                db.execute(
                    "INSERT INTO story_workspace_workspaces (id, name, owner_id) "
                    "VALUES ('workspace-deck-admin', 'Deck Admin', 101)"
                )
            seed_builtin_deck_plugin(db)
        finally:
            db.close()

        self.app = FastAPI()
        self.app.dependency_overrides[deck_plugins.get_current_user] = lambda: {
            "user_id": 101,
            "email": "deck-admin@example.test",
            "role": "admin",
            "workspace_id": "workspace-deck-admin",
        }
        self.app.dependency_overrides[deck_plugins._deck_plugin_current_user] = lambda: {
            "user_id": 101,
            "email": "deck-admin@example.test",
            "role": "admin",
            "workspace_id": "workspace-deck-admin",
        }
        self.app.dependency_overrides[story_workspace.get_current_user] = lambda: {
            "user_id": 101,
            "email": "deck-admin@example.test",
            "role": "admin",
            "workspace_id": "workspace-deck-admin",
        }
        self.app.include_router(deck_plugins.router)
        self.app.include_router(story_workspace.router)
        self._capabilities = patch.dict(
            os.environ,
            {
                "INK_DECK_HOST_COMPATIBLE": "1",
                "INK_CLAUDE_AGENT_CONTRACT_COMPATIBLE": "1",
                "INK_STORY_SCHEMA_COMPATIBLE": "1",
                "INK_DECK_RUNTIME_CONFIG_COMPATIBLE": "1",
            },
            clear=False,
        )
        self._capabilities.start()

    def tearDown(self) -> None:
        self._capabilities.stop()
        self._database_fixture.stop()
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
                       activation_status, artifact_set_hash
                FROM runtime_plugin_materializations
                """
            ).fetchone()
            lock_row = db.execute(
                "SELECT lock_json FROM deck_runtime_plugin_locks "
                "WHERE deck_plugin_id = ? AND deck_plugin_version = ?",
                (BUILTIN_DECK_PLUGIN_ID, BUILTIN_DECK_PLUGIN_VERSION),
            ).fetchone()
        finally:
            db.close()
        self.assertEqual(Path(materialization["cache_ref"]), builtin_plugin_path().resolve())
        self.assertEqual(materialization["verification_status"], "verified")
        self.assertEqual(materialization["materialization_status"], "materialized")
        self.assertEqual(materialization["activation_status"], "loadable")
        self.assertEqual(
            materialization["artifact_set_hash"],
            compute_artifact_set_hash(
                DeckRuntimePluginLock.model_validate_json(lock_row["lock_json"])
            ),
        )


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
