# [Input] Admin-backed Notion store, strict DTO transport, and provider-free Admin fixture.
# [Output] Verify identity binding, resource/snapshot roundtrip, background authority, and source closure.
# [Pos] Notion Admin DTO adapter contract tests.
# [Sync] 2026-09-17: verify background store calls carry service OAuth without a user token.
from __future__ import annotations

import sys
import unittest
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
TEST_ROOT = Path(__file__).resolve().parent
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

from libs.claude_agent_kit.server.notion_snapshot import snapshot_identity
from notion import store
from notion_admin_fake import build_notion_admin_boundary
from services.admin_data.errors import AdminDataError
from services.admin_data.notion_connector_data import NotionConnectorCreateInputDTO


class TestNotionStore(unittest.TestCase):
    def setUp(self) -> None:
        (
            self.owner,
            self.actor,
            self.state,
            self.user_store,
            self.background_store,
        ) = build_notion_admin_boundary()
        store.close_default_store()
        store.open_default_store(store=self.user_store)

    def tearDown(self) -> None:
        store.close_default_store()
        self.owner.close()

    @staticmethod
    def _sample_snapshot(connector_id: str) -> dict:
        return {
            "metadata": {
                "workspace_id": connector_id,
                "resource_connector_id": connector_id,
                "snapshot_version": "snap-001",
                "source_revision": "rev-001",
                "sync_cursor": "cursor-001",
                "fetched_at": "2026-09-16T00:00:00Z",
                "state": "snapshot_ready",
            },
            "connector": {"id": connector_id, "platform": "notion"},
            "index": [{"page_id": "page-1", "title": "Page"}],
            "databases": [{"database_id": "db-1", "title": "Tasks"}],
            "database_pages": {"db-1": [{"page_id": "page-1"}]},
            "pages": {},
            "identity": {
                "workspace_id": connector_id,
                "resource_connector_id": connector_id,
                "snapshot_version": "snap-001",
                "source_revision": "rev-001",
                "sync_cursor": "cursor-001",
            },
        }

    def test_user_roundtrip_uses_oauth_admin_operations(self) -> None:
        connector = store.create_connector(7, "Notion", config={"label": "primary"})
        connector_id = connector["id"]
        self.assertEqual(connector["user_id"], 7)
        authenticated = store.save_auth_state(
            connector_id,
            7,
            auth_status="authenticated",
            config_patch={"connection_label": "primary"},
        )
        self.assertEqual(authenticated["auth_status"], "authenticated")
        selected = store.replace_connector_resources(
            connector_id,
            7,
            databases=[{"database_id": "db-1", "title": "Tasks"}],
            pages=[{"page_id": "page-1", "title": "Page"}],
        )
        self.assertEqual(selected["connector"]["selected_databases"], ["db-1"])
        self.assertEqual(selected["connector"]["selected_pages"], ["page-1"])
        self.assertTrue(
            all(item["sync_status"] == "pending" for item in selected["resources"])
        )
        snapshot = self._sample_snapshot(connector_id)
        saved = store.save_snapshot(
            connector_id, 7, connector_id, snapshot, selected["resources"]
        )
        self.assertEqual(snapshot_identity(saved)["resource_connector_id"], connector_id)
        self.assertEqual(
            store.get_current_snapshot(connector_id, connector_id, 7), snapshot
        )
        self.assertEqual(store.get_snapshot(connector_id, "snap-001", 7), snapshot)
        self.assertEqual(len(store.list_snapshots(connector_id, 7)), 1)
        self.assertTrue(
            all(
                item["sync_status"] == "synced"
                for item in store.list_connector_resources(connector_id, 7)
            )
        )
        store.attach_thread_to_connector(connector_id, 7, "thread-1")
        self.assertEqual(
            store.get_connector_for_thread("thread-1", 7)["id"], connector_id
        )
        self.assertTrue(store.delete_connector(connector_id, 7))
        self.assertEqual(store.list_connectors(7), [])
        user_calls = [
            call
            for call in self.state.calls
            if call[0] != "notion.sync-candidates.list"
        ]
        self.assertTrue(user_calls)
        self.assertTrue(
            all(call[2] == "Bearer notion-oauth-token" for call in user_calls)
        )
        self.assertTrue(
            all(
                not {
                    "user_id",
                    "actor_id",
                    "canonical_user_id",
                    "sql",
                    "table",
                }
                & call[1].keys()
                for call in user_calls
            )
        )

    def test_background_store_uses_service_scope_without_user_token(self) -> None:
        connector = self.user_store.create_connector(7, "Notion")
        self.user_store.save_auth_state(
            connector["id"], 7, auth_status="authenticated", config_patch={}
        )
        candidates = self.background_store.list_sync_candidates()
        self.assertEqual([item["id"] for item in candidates], [connector["id"]])
        fetched = self.background_store.get_connector(connector["id"], 7)
        self.assertEqual(fetched["user_id"], 7)
        background_calls = [
            call for call in self.state.calls if call[0].startswith("notion.sync")
        ]
        self.assertTrue(background_calls)
        self.assertTrue(
            all(call[2] == "Bearer fixture.service.access.token" for call in background_calls)
        )
        with self.assertRaises(AdminDataError):
            self.background_store.create_connector(7, "Forbidden")

    def test_actor_binding_and_dto_extra_fields_fail_closed(self) -> None:
        with self.assertRaises(AdminDataError):
            self.user_store.list_connectors(8)
        with self.assertRaises(ValidationError):
            NotionConnectorCreateInputDTO.model_validate(
                {
                    "authority": None,
                    "name": "Notion",
                    "platform": "notion",
                    "config": {},
                    "user_id": "7",
                }
            )

    def test_default_runtime_requires_explicit_typed_store(self) -> None:
        self.assertIs(store.default_store(), self.user_store)
        store.close_default_store()
        with self.assertRaises(AdminDataError):
            store.default_store()
        with self.assertRaises(TypeError):
            store.open_default_store(store=object())  # type: ignore[arg-type]

    def test_production_store_source_contains_no_database_path(self) -> None:
        source = Path(store.__file__).read_text(encoding="utf-8").casefold()
        for forbidden in (
            "import database",
            "psycopg",
            "postgrespool",
            "postgresunitofwork",
            "select ",
            "insert ",
            "update ",
            "delete from",
            "create table",
            "sqlite",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn("adminnotionconnectordata", source)


if __name__ == "__main__":
    unittest.main()
