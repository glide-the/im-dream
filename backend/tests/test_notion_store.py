# [Input] Notion Connector PostgreSQL repository with a pure transactional fake.
# [Output] Verify five-table behavior, SQL contract, rollback, and snapshot identity.
# [Pos] test node in backend/tests
# [Sync] 2026-07-04: initial store coverage for Notion connector persistence.
# [Sync] 2026-07-08: cover connector list/detail sources hydration for refresh-safe
#                    resource selections.

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
TEST_ROOT = Path(__file__).resolve().parent
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

from libs.claude_agent_kit.server.notion_snapshot import (
    CanonicalWorkspaceSnapshot,
    SnapshotMetadata,
    snapshot_identity,
)
from notion import store
from notion_postgres_fake import TABLE_NAMES, build_fake_notion_store


class TestNotionStore(unittest.TestCase):
    def setUp(self):
        self._store, self._database, self._pool = build_fake_notion_store(users={7, 8})
        store.close_default_store()
        store.open_default_store(store=self._store)

    def tearDown(self):
        store.close_default_store()

    def _sample_snapshot(self, connector_id: str, workspace_id: str = "workspace-1") -> CanonicalWorkspaceSnapshot:
        metadata = SnapshotMetadata(
            workspace_id=workspace_id,
            resource_connector_id=connector_id,
            snapshot_version="snap-001",
            source_revision="rev-001",
            sync_cursor="cursor-001",
            fetched_at="2026-07-04T00:00:00Z",
        )
        return CanonicalWorkspaceSnapshot(
            metadata=metadata,
            connector={
                "id": connector_id,
                "platform": "notion",
                "auth_status": "authenticated",
                "selected_databases": ["db-1"],
                "selected_pages": ["page-standalone"],
            },
            index=[
                {"page_id": "page-db-1", "title": "Database Page", "url": "https://www.notion.so/page-db-1", "last_edited": "2026-07-03T10:00:00Z"},
                {"page_id": "page-standalone", "title": "Standalone Page", "url": "https://www.notion.so/page-standalone", "last_edited": "2026-07-02T10:00:00Z"},
            ],
            databases=[
                {
                    "database_id": "db-1",
                    "title": "Tasks",
                    "page_count": 1,
                    "properties_schema": {"Name": {"type": "title"}},
                    "last_edited": "2026-07-03T10:00:00Z",
                    "url": "https://www.notion.so/db-1",
                }
            ],
            database_pages={
                "db-1": [
                    {
                        "page_id": "page-db-1",
                        "title": "Database Page",
                        "last_edited": "2026-07-03T10:00:00Z",
                        "status": "In Progress",
                    }
                ]
            },
            pages={
                "page-db-1": {
                    "page_id": "page-db-1",
                    "title": "Database Page",
                    "url": "https://www.notion.so/page-db-1",
                    "last_edited": "2026-07-03T10:00:00Z",
                    "properties": {"Name": {"title": [{"plain_text": "Database Page"}]}},
                    "blocks": [{"type": "paragraph", "text": "Ship it"}],
                },
                "page-standalone": {
                    "page_id": "page-standalone",
                    "title": "Standalone Page",
                    "url": "https://www.notion.so/page-standalone",
                    "last_edited": "2026-07-02T10:00:00Z",
                    "properties": {"Name": {"title": [{"plain_text": "Standalone Page"}]}},
                    "blocks": [{"type": "paragraph", "text": "Read me"}],
                },
            },
        )

    def test_connector_resource_selection_and_snapshot_roundtrip(self):
        connector = store.create_connector(7, name="Notion", config={"notion_home": "/tmp/notion-home"})
        self.assertEqual(connector["auth_status"], "pending")
        self.assertEqual(store.list_connectors(7)[0]["id"], connector["id"])

        updated = store.save_auth_state(
            connector["id"],
            7,
            auth_status="authenticated",
            config_patch={"notion_home": "/tmp/notion-home"},
            verification_url="https://www.notion.so/workers/cli-login",
            verification_code="VAF-HWY",
            poll_interval_seconds=5,
        )
        self.assertEqual(updated["auth_status"], "authenticated")

        selected = store.replace_connector_resources(
            connector["id"],
            7,
            databases=[
                {
                    "database_id": "db-1",
                    "title": "Tasks",
                    "page_count": 1,
                    "properties_schema": {"Name": {"type": "title"}},
                    "last_edited": "2026-07-03T10:00:00Z",
                    "url": "https://www.notion.so/db-1",
                }
            ],
            pages=[
                {
                    "page_id": "page-standalone",
                    "title": "Standalone Page",
                    "last_edited": "2026-07-02T10:00:00Z",
                    "url": "https://www.notion.so/page-standalone",
                }
            ],
        )
        self.assertEqual(len(selected["resources"]), 2)
        self.assertEqual(selected["connector"]["selected_databases"], ["db-1"])
        self.assertEqual(selected["connector"]["selected_pages"], ["page-standalone"])
        self.assertEqual(len(selected["connector"]["sources"]), 2)
        self.assertEqual(selected["connector"]["sources"][0]["external_id"], "db-1")
        self.assertEqual(store.list_connectors(7)[0]["sources"][0]["external_id"], "db-1")
        self.assertEqual(store.get_connector(connector["id"], 7)["sources"][1]["external_id"], "page-standalone")

        snapshot = self._sample_snapshot(connector["id"])
        saved = store.save_snapshot(connector["id"], 7, "workspace-1", snapshot)
        self.assertEqual(saved["metadata"]["snapshot_version"], "snap-001")
        self.assertEqual(snapshot_identity(saved)["resource_connector_id"], connector["id"])

        current = store.get_current_snapshot("workspace-1", connector["id"], 7)
        self.assertIsNotNone(current)
        self.assertEqual(current["metadata"]["snapshot_version"], "snap-001")
        self.assertEqual(current["pages"]["page-standalone"]["title"], "Standalone Page")
        self.assertEqual(store.list_snapshots(connector["id"], 7)[0]["snapshot"]["metadata"]["snapshot_version"], "snap-001")
        self.assertEqual(len(store.list_connector_resources(connector["id"], 7)), 2)
        self.assertEqual(len(self._database.tables["resource_connectors"]), 1)
        self.assertEqual(len(self._database.tables["connector_resources"]), 2)
        self.assertEqual(len(self._database.tables["connector_resource_pages"]), 1)
        self.assertEqual(len(self._database.tables["connector_snapshots"]), 1)

    def test_attach_thread_finds_connector(self):
        connector = store.create_connector(7, name="Notion")
        store.attach_thread_to_connector(connector["id"], 7, "thread-1")

        found = store.get_connector_for_thread("thread-1", 7)
        self.assertIsNotNone(found)
        self.assertEqual(found["id"], connector["id"])
        self.assertEqual(len(self._database.tables["connector_chat_threads"]), 1)

    def test_connector_delete_cascades_all_five_tables(self):
        connector = store.create_connector(7, name="Notion")
        store.replace_connector_resources(
            connector["id"],
            7,
            databases=[{"database_id": "db-1", "title": "Tasks"}],
            pages=[],
        )
        store.save_snapshot(connector["id"], 7, "workspace-1", self._sample_snapshot(connector["id"]))
        store.attach_thread_to_connector(connector["id"], 7, "thread-1")

        self.assertTrue(store.delete_connector(connector["id"], 7))
        self.assertEqual(
            {table: len(self._database.tables[table]) for table in TABLE_NAMES},
            {table: 0 for table in TABLE_NAMES},
        )

    def test_failed_resource_replacement_rolls_back_without_partial_delete(self):
        connector = store.create_connector(7, name="Notion")
        store.replace_connector_resources(
            connector["id"],
            7,
            databases=[{"database_id": "db-original", "title": "Original"}],
            pages=[],
        )
        before = {
            table: [dict(row) for row in rows]
            for table, rows in self._database.tables.items()
        }
        self._database.fail_marker = "notion.resource.insert"
        with self.assertRaisesRegex(RuntimeError, "injected failure"):
            store.replace_connector_resources(
                connector["id"],
                7,
                databases=[{"database_id": "db-replacement", "title": "Replacement"}],
                pages=[],
            )
        self._database.fail_marker = None

        self.assertEqual(self._database.tables, before)
        self.assertEqual(self._pool.connections[-1].commits, 0)
        self.assertEqual(self._pool.connections[-1].rollbacks, 1)

    def test_failed_page_materialization_rolls_back_snapshot_and_pointer(self):
        connector = store.create_connector(7, name="Notion")
        store.replace_connector_resources(
            connector["id"],
            7,
            databases=[{"database_id": "db-1", "title": "Tasks"}],
            pages=[],
        )
        before = {
            table: [dict(row) for row in rows]
            for table, rows in self._database.tables.items()
        }
        self._database.fail_marker = "notion.resource_page.insert"
        with self.assertRaisesRegex(RuntimeError, "injected failure"):
            store.save_snapshot(
                connector["id"], 7, "workspace-1", self._sample_snapshot(connector["id"])
            )
        self._database.fail_marker = None

        self.assertEqual(self._database.tables, before)
        self.assertEqual(self._pool.connections[-1].commits, 0)
        self.assertEqual(self._pool.connections[-1].rollbacks, 1)

    def test_runtime_source_is_postgres_only_and_all_queries_are_bound(self):
        connector = store.create_connector(7, name="Notion")
        store.get_connector(connector["id"], 7)
        source = Path(store.__file__).read_text(encoding="utf-8")
        lowered = source.casefold()
        for forbidden in (
            "sqlite3",
            "begin immediate",
            "create table",
            "ink_agent_notion_db_path",
            "db_path",
        ):
            self.assertNotIn(forbidden, lowered)
        self.assertNotIn("PRAGMA", source)
        self.assertNotIn("?", source)
        self.assertNotIn("import database", source)
        self.assertIn("PostgresUnitOfWork", source)
        self.assertIn("PostgresPool.from_env", source)
        queries = [
            query
            for connection in self._pool.connections
            for query, _params in connection.executions
            if "notion." in query
        ]
        self.assertTrue(queries)
        self.assertTrue(all("%s" in query for query in queries))
        self.assertTrue(all("?" not in query for query in queries))

    def test_default_runtime_opens_and_closes_only_its_lifecycle_pool(self):
        class LifecyclePool:
            def __init__(self):
                self.open_calls = 0
                self.close_calls = 0

            def open(self):
                self.open_calls += 1

            def close(self):
                self.close_calls += 1

            def connection(self, timeout=None):  # pragma: no cover - not used here
                raise AssertionError(timeout)

        lifecycle_pool = LifecyclePool()
        store.close_default_store()
        with patch.object(
            store.PostgresPool,
            "from_env",
            return_value=lifecycle_pool,
        ) as factory:
            configured = store.open_default_store()
            self.assertIsInstance(configured, store.NotionConnectorStore)
            self.assertEqual(lifecycle_pool.open_calls, 1)
            factory.assert_called_once_with(
                application_name="ink-dream-notion-connectors"
            )
            store.close_default_store()
        self.assertEqual(lifecycle_pool.close_calls, 1)


if __name__ == "__main__":
    unittest.main()
