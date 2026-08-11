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
from services.deck.chat_context import DeckChatContextService


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
        self._environment = patch.dict(os.environ, {"INK_ENVIRONMENT": "test"}, clear=False)
        self._environment.start()

    def tearDown(self) -> None:
        self._environment.stop()
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

        # New architecture (deck-integration-delta): the chat plugin path is
        # shared-installation based.  The legacy binding above stays for the
        # workflow-run path below; chat context now resolves deck refs.
        try:
            from services.claude_plugin.cli import resolve_claude_binary

            resolve_claude_binary()
        except Exception:
            self.skipTest(
                "BLOCKED: claude CLI unavailable; real platform-builtin "
                "install cannot run"
            )

        runtime_root = Path(self._tmp.name) / "plugin-runtime"
        with patch.dict(
            os.environ,
            {"INK_CLAUDE_PLUGIN_RUNTIME_ROOT": str(runtime_root)},
            clear=False,
        ):
            from services.claude_plugin.deck_refs_service import DeckPluginRefService
            from services.claude_plugin.install_service import PluginInstallService

            deck_id = database.create_deck(101, "Dream Story Deck")
            db = database.get_db()
            try:
                workspace_id = db.execute(
                    "SELECT id FROM story_workspace_workspaces WHERE owner_id = '101'"
                ).fetchone()["id"]
                operation = PluginInstallService(db).install(
                    "ink-dream-story@platform-builtin",
                    source_type="platform-builtin",
                )
                self.assertEqual(operation["status"], "ready", operation)
                installation_id = operation["installation_id"]

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
                refs = DeckPluginRefService(db).replace_refs(
                    deck_id,
                    "101",
                    [
                        {
                            "plugin_installation_id": installation_id,
                            "enabled": True,
                            "order_index": 0,
                        }
                    ],
                )
                self.assertEqual(len(refs), 1)
                self.assertEqual(refs[0]["package_spec"], "ink-dream-story@platform-builtin")

                context = asyncio.run(
                    DeckChatContextService(db).resolve(deck_id=deck_id, actor_id="101")
                )
            finally:
                db.close()
        self.assertEqual(len(context.plugin_refs), 1)
        self.assertEqual(
            context.plugin_refs[0]["package_spec"], "ink-dream-story@platform-builtin"
        )
        self.assertEqual(context.plugin_refs[0]["resolved_version"], "1.0.0")
        # The chat context must never carry settings JSON or plugin paths.
        self.assertFalse(hasattr(context, "claude_plugin_paths"))
        self.assertFalse(hasattr(context, "claude_settings_json"))

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
