# [Input] Consume notion_snapshot.py contract helpers.
# [Output] Unit tests for lightweight Notion index build, virtual path resolution, and proposal staleness.
# [Pos] test node in backend/tests
# [Sync] 2026-06-28: initial contract tests for resource-connector-owned canonical snapshots.
# [Sync] 2026-08-28: prove selected data sources build a paginated ID index
#                    without fetching or persisting page bodies.
# [Sync] 2026-08-28: prove failed-turn cleanup unlinks a malicious `.notion`
#                    symlink without deleting its external target.
# [Sync] 2026-08-28: prove legacy embedded page bodies are never projected into
#                    a thread; virtual page Reads remain hook-only during migration.

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from libs.claude_agent_kit.server.notion_snapshot import (
    CanonicalWorkspaceSnapshot,
    SnapshotMetadata,
    SnapshotWriteProposal,
    get_notion_snapshot_resource_data,
    is_notion_snapshot_path,
    resolve_notion_snapshot_resource,
    snapshot_identity,
    write_proposal_is_stale,
)
from notion import sync as notion_sync
from notion.operations import SearchResult


class NotionSnapshotContractTest(unittest.TestCase):
    def _snapshot(self) -> CanonicalWorkspaceSnapshot:
        return CanonicalWorkspaceSnapshot(
            metadata=SnapshotMetadata(
                workspace_id="workspace-1",
                resource_connector_id="connector-1",
                snapshot_version="snap-001",
                source_revision="rev-001",
                sync_cursor="cursor-001",
                fetched_at="2026-06-28T00:00:00Z",
            ),
            connector={"platform": "notion", "auth_status": "authenticated"},
            index=[{"page_id": "page-1", "title": "Roadmap"}],
            databases=[{"database_id": "db-1", "title": "Tasks"}],
            database_pages={"db-1": [{"page_id": "page-1", "title": "Roadmap"}]},
            pages={},
        )

    def test_resolves_supported_notion_virtual_paths(self):
        self.assertTrue(is_notion_snapshot_path(".notion/connector.json"))
        self.assertTrue(is_notion_snapshot_path("/tmp/ws/.notion/pages/page-1.json"))
        self.assertEqual(resolve_notion_snapshot_resource(".notion/databases/db-1.json"), "databases/db-1")
        self.assertEqual(resolve_notion_snapshot_resource(".notion/pages/page-1.json"), "pages/page-1")
        self.assertIsNone(resolve_notion_snapshot_resource(".notion/pages/.json"))
        self.assertIsNone(resolve_notion_snapshot_resource(".notion/unknown.json"))

    def test_extracts_snapshot_resources_with_metadata(self):
        snapshot = self._snapshot()

        connector = get_notion_snapshot_resource_data(".notion/connector.json", snapshot)
        self.assertEqual(connector["platform"], "notion")
        self.assertEqual(connector["snapshot"]["snapshot_version"], "snap-001")

        index = get_notion_snapshot_resource_data(".notion/index.json", snapshot)
        self.assertEqual(index["pages"][0]["page_id"], "page-1")
        self.assertEqual(index["snapshot"]["source_revision"], "rev-001")

        page = get_notion_snapshot_resource_data(".notion/pages/page-1.json", snapshot)
        self.assertTrue(page["missing"])
        self.assertEqual(page["reason"], "not_materialized_in_snapshot")
        self.assertEqual(page["snapshot"]["sync_cursor"], "cursor-001")

    def test_missing_page_reports_snapshot_scoped_miss(self):
        missing = get_notion_snapshot_resource_data(".notion/pages/page-missing.json", self._snapshot())

        self.assertTrue(missing["missing"])
        self.assertEqual(missing["reason"], "not_materialized_in_snapshot")
        self.assertEqual(missing["snapshot"]["snapshot_version"], "snap-001")

    def test_snapshot_identity_and_write_staleness(self):
        snapshot = self._snapshot()
        self.assertEqual(
            snapshot_identity(snapshot),
            {
                "workspace_id": "workspace-1",
                "resource_connector_id": "connector-1",
                "snapshot_version": "snap-001",
                "source_revision": "rev-001",
                "sync_cursor": "cursor-001",
            },
        )

        fresh = SnapshotWriteProposal(
            proposal_id="proposal-1",
            workspace_id="workspace-1",
            resource_connector_id="connector-1",
            base_snapshot_version="snap-001",
            base_source_revision="rev-001",
            base_sync_cursor="cursor-001",
        )
        stale = SnapshotWriteProposal(
            proposal_id="proposal-2",
            workspace_id="workspace-1",
            resource_connector_id="connector-1",
            base_snapshot_version="snap-old",
            base_source_revision="rev-001",
            base_sync_cursor="cursor-001",
        )

        self.assertFalse(write_proposal_is_stale(fresh, snapshot))
        self.assertTrue(write_proposal_is_stale(stale, snapshot))


class NotionSnapshotBuildTest(unittest.IsolatedAsyncioTestCase):
    async def test_selected_data_source_builds_paginated_index_without_page_reads(self):
        class FakeOperations:
            def __init__(self):
                self.queries = []

            async def query_database(self, query):
                self.queries.append(query)
                if query.start_cursor is None:
                    return SearchResult(
                        results=[
                            {
                                "id": "page-1",
                                "properties": {
                                    "Name": {"title": [{"plain_text": "Roadmap"}]},
                                },
                                "last_edited_time": "2026-08-28T10:00:00Z",
                            }
                        ],
                        has_more=True,
                        next_cursor="page-2-cursor",
                    )
                return SearchResult(
                    results=[
                        {
                            "id": "page-2",
                            "properties": {
                                "Name": {"title": [{"plain_text": "Launch"}]},
                            },
                            "last_edited_time": "2026-08-28T11:00:00Z",
                        }
                    ],
                    has_more=False,
                    next_cursor=None,
                )

            async def get_page(self, page_id):
                raise AssertionError(f"background snapshot fetched page body {page_id}")

        fake = FakeOperations()
        snapshot = await notion_sync.build_canonical_snapshot(
            connector={"id": "connector-1", "auth_status": "authenticated"},
            selected_resources=[
                {
                    "resource_type": "notion_database",
                    "external_id": "selected-source",
                    "title": "Team Knowledge",
                    "metadata": {},
                }
            ],
            workspace_id="workspace-1",
            operations=fake,
        )

        self.assertEqual([query.database_id for query in fake.queries], ["selected-source"] * 2)
        self.assertEqual(fake.queries[1].start_cursor, "page-2-cursor")
        self.assertEqual(snapshot["databases"][0]["page_count"], 2)
        self.assertEqual(snapshot["index"][0]["page_id"], "page-1")
        self.assertEqual(snapshot["index"][1]["page_id"], "page-2")
        self.assertEqual(snapshot["pages"], {})
        self.assertEqual(snapshot["metadata"]["state"], "snapshot_ready")

    async def test_selected_standalone_page_uses_saved_metadata_only(self):
        class NoRemoteOperations:
            async def query_database(self, query):
                raise AssertionError(query)

            async def get_page(self, page_id):
                raise AssertionError(page_id)

        snapshot = await notion_sync.build_canonical_snapshot(
            connector={"id": "connector-1", "auth_status": "authenticated"},
            selected_resources=[
                {
                    "resource_type": "notion_page",
                    "external_id": "page-direct",
                    "title": "Direct Page",
                    "metadata": {
                        "url": "https://www.notion.so/page-direct",
                        "last_edited": "2026-08-28T12:00:00Z",
                    },
                }
            ],
            workspace_id="workspace-1",
            operations=NoRemoteOperations(),
        )

        self.assertEqual(snapshot["index"], [{
            "page_id": "page-direct",
            "title": "Direct Page",
            "url": "https://www.notion.so/page-direct",
            "last_edited": "2026-08-28T12:00:00Z",
        }])
        self.assertEqual(snapshot["pages"], {})


class NotionSnapshotCleanupTest(unittest.TestCase):
    def test_materialization_discards_legacy_embedded_page_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir) / "thread"
            workspace.mkdir()
            snapshot = {
                "metadata": {
                    "workspace_id": "connector-1",
                    "resource_connector_id": "connector-1",
                    "snapshot_version": "legacy-v1",
                    "source_revision": "legacy-r1",
                    "sync_cursor": "legacy-c1",
                    "fetched_at": "2026-08-28T12:00:00Z",
                    "state": "snapshot_ready",
                },
                "connector": {"id": "connector-1", "platform": "notion"},
                "index": [{"page_id": "page-1", "title": "Legacy"}],
                "databases": [],
                "database_pages": {},
                "pages": {
                    "page-1": {
                        "page_id": "page-1",
                        "markdown": "must not enter the thread",
                    }
                },
            }

            notion_sync.materialize_workspace_snapshot(
                workspace,
                connector=snapshot["connector"],
                snapshot=snapshot,
            )

            self.assertEqual(
                json.loads((workspace / ".notion" / "index.json").read_text())[
                    "pages"
                ][0]["page_id"],
                "page-1",
            )
            self.assertEqual(list((workspace / ".notion" / "pages").iterdir()), [])

    def test_clear_workspace_snapshot_does_not_follow_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            workspace = root / "thread"
            external = root / "external"
            workspace.mkdir()
            external.mkdir()
            marker = external / "keep.txt"
            marker.write_text("keep", encoding="utf-8")
            (workspace / ".notion").symlink_to(external, target_is_directory=True)

            notion_sync.clear_workspace_snapshot(workspace)

            self.assertFalse((workspace / ".notion").exists())
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
