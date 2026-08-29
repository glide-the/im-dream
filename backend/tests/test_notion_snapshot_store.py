# [Input] Isolated actor agentdata/workspace roots and synthetic canonical Notion snapshots.
# [Output] Verify atomic lightweight-index publication, actor isolation, thread projection, rotation, and revocation.
# [Pos] Notion agentdata snapshot provider contract test in backend/tests
# [Sync] 2026-08-28: prove background-owned lightweight indexes are independent
#                    of Chat and copied only into the requesting thread.
# [Sync] 2026-08-29: prove every turn intersects LKG content with current actor
#                    selection and excludes private connector configuration.

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from notion.credentials import NotionCredentialSettings, NotionCredentialStore
from notion.errors import NotionSnapshotNotReadyError
from notion.snapshot_store import NotionSnapshotStore


def _snapshot(connector_id: str, version: str, text: str) -> dict:
    return {
        "metadata": {
            "workspace_id": connector_id,
            "resource_connector_id": connector_id,
            "snapshot_version": version,
            "source_revision": f"revision-{version}",
            "sync_cursor": f"cursor-{version}",
            "fetched_at": "2026-08-28T12:00:00Z",
            "state": "snapshot_ready",
        },
        "connector": {"id": connector_id, "platform": "notion"},
        "index": [{"page_id": "page-1", "title": text}],
        "databases": [{"database_id": "database-1", "title": "Database"}],
        "database_pages": {
            "database-1": [{"page_id": "page-1", "title": "Page"}]
        },
        "pages": {},
        "identity": {
            "workspace_id": connector_id,
            "resource_connector_id": connector_id,
            "snapshot_version": version,
            "source_revision": f"revision-{version}",
            "sync_cursor": f"cursor-{version}",
        },
    }


class TestNotionSnapshotStore(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.workspace_root = root / "agentdata" / "agent-workspaces"
        self.workspace_root.mkdir(parents=True)
        self.thread_a = self.workspace_root / "thread-a"
        self.thread_b = self.workspace_root / "thread-b"
        self.thread_a.mkdir()
        self.thread_b.mkdir()
        credentials = NotionCredentialStore(
            NotionCredentialSettings(
                runtime_root=root / "agentdata" / "notion-runtime"
            ),
            workspace_root_provider=lambda: self.workspace_root,
            thread_ids_provider=lambda _actor: [],
        )
        self.credentials = credentials
        self.store = NotionSnapshotStore(credentials, max_snapshot_bytes=1024 * 1024)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_actor_snapshots_are_distinct_and_connector_bound(self) -> None:
        self.store.publish_current(7, "connector-a", _snapshot("connector-a", "v1", "actor-a"))
        self.store.publish_current(8, "connector-a", _snapshot("connector-a", "v2", "actor-b"))

        self.assertEqual(
            self.store.load_current(7, "connector-a")["index"][0]["title"],
            "actor-a",
        )
        self.assertEqual(
            self.store.load_current(8, "connector-a")["index"][0]["title"],
            "actor-b",
        )
        with self.assertRaises(NotionSnapshotNotReadyError):
            self.store.publish_current(
                7,
                "connector-b",
                _snapshot("connector-a", "v3", "wrong connector"),
            )

    def test_new_snapshot_rejects_embedded_page_body(self) -> None:
        snapshot = _snapshot("connector-a", "v1", "Page")
        snapshot["pages"] = {
            "page-1": {"page_id": "page-1", "markdown": "must stay remote"}
        }
        with self.assertRaisesRegex(
            NotionSnapshotNotReadyError,
            "lightweight page index",
        ):
            self.store.publish_current(7, "connector-a", snapshot)

    def test_thread_projection_uses_lkg_and_refreshes_only_on_next_turn(self) -> None:
        connector = {
            "id": "connector-a",
            "platform": "notion",
            "sources": [
                {
                    "resource_type": "notion_database",
                    "external_id": "database-1",
                }
            ],
        }
        self.store.publish_current(7, "connector-a", _snapshot("connector-a", "v1", "first"))
        first = self.store.project_thread(7, connector, self.thread_a)
        index_path = self.thread_a / ".notion" / "index.json"
        self.assertTrue(first.available)
        self.assertEqual(first.snapshot_version, "v1")
        self.assertEqual(json.loads(index_path.read_text())["pages"][0]["title"], "first")
        self.assertFalse((self.thread_a / ".notion" / "pages" / "page-1.json").exists())

        self.store.publish_current(7, "connector-a", _snapshot("connector-a", "v2", "second"))
        self.assertEqual(json.loads(index_path.read_text())["pages"][0]["title"], "first")
        second = self.store.project_thread(7, connector, self.thread_a)
        self.assertEqual(second.snapshot_version, "v2")
        self.assertEqual(json.loads(index_path.read_text())["pages"][0]["title"], "second")
        self.assertFalse((self.thread_b / ".notion").exists())

    def test_projection_removes_deselected_pages_and_private_config(self) -> None:
        self.store.publish_current(
            7,
            "connector-a",
            _snapshot("connector-a", "v1", "private page"),
        )
        connector = {
            "id": "connector-a",
            "platform": "notion",
            "auth_status": "authenticated",
            "user_id": 7,
            "config": {"verification_code": "must-not-project"},
            "sources": [],
        }

        projection = self.store.project_thread(7, connector, self.thread_a)

        self.assertFalse(projection.available)
        index = json.loads((self.thread_a / ".notion" / "index.json").read_text())
        public_connector = json.loads(
            (self.thread_a / ".notion" / "connector.json").read_text()
        )
        self.assertEqual(index["pages"], [])
        self.assertNotIn("user_id", public_connector)
        self.assertNotIn("config", public_connector)
        self.assertNotIn("must-not-project", json.dumps(public_connector))

    def test_missing_snapshot_projects_truthful_empty_state(self) -> None:
        projection = self.store.project_thread(
            7,
            {"id": "connector-a", "platform": "notion"},
            self.thread_a,
        )
        self.assertFalse(projection.available)
        self.assertEqual(
            json.loads((self.thread_a / ".notion" / "index.json").read_text())["pages"],
            [],
        )

    def test_clear_user_removes_snapshot_source_and_thread_credentials(self) -> None:
        self.store.publish_current(7, "connector-a", _snapshot("connector-a", "v1", "secret"))
        self.credentials.clear_user(7)
        self.assertIsNone(self.store.load_current(7, "connector-a"))


if __name__ == "__main__":
    unittest.main()
