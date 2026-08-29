# [Input] Notion operation normalization and discovery helpers.
# [Output] Verify discovery filtering plus data source query, search sort, and lazy page Markdown contracts.
# [Pos] test node in backend/tests
# [Sync] 2026-07-08: cover filtering of Notion People system data sources from database discovery.
# [Sync] 2026-08-28: construct operations with an explicit server-owned credential home.
# [Sync] 2026-08-28: lock ntn 0.15.1 data source query paths, search sort payloads,
#                    and Markdown page reads so upstream endpoint drift cannot recur.
# [Sync] 2026-08-28: cover the Markdown-only endpoint used by the Runtime Read hook.

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import MethodType
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from notion import operations


class TestNotionOperations(unittest.IsolatedAsyncioTestCase):
    async def test_discover_databases_filters_people_system_database(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        client = operations.NotionOperationClient(Path(temporary.name))

        async def fake_search(self, search_filter):
            del self, search_filter
            return operations.SearchResult(
                results=[
                    {
                        "id": "people-db",
                        "object": "data_source",
                        "title": [{"plain_text": "People"}],
                        "properties": {
                            "Name": {"id": "title", "name": "Name", "type": "title"},
                            "Person": {"id": "people%3Aperson", "name": "Person", "type": "people"},
                            "Membership Type": {
                                "id": "people%3Amembership_type",
                                "name": "Membership Type",
                                "type": "select",
                                "select": {
                                    "options": [
                                        {"id": "owner", "name": "Workspace owner"},
                                        {"id": "membership_admin", "name": "Membership admin"},
                                        {"id": "member", "name": "Member"},
                                    ]
                                },
                            },
                        },
                    },
                    {
                        "id": "project-db",
                        "object": "data_source",
                        "title": [{"plain_text": "Projects"}],
                        "properties": {
                            "Name": {"id": "title", "name": "Name", "type": "title"},
                            "Status": {"id": "status", "name": "Status", "type": "select"},
                        },
                    },
                ],
                has_more=False,
                next_cursor=None,
            )

        client.search = MethodType(fake_search, client)

        databases = await client.discover_databases()

        self.assertEqual([item["database_id"] for item in databases], ["project-db"])
        self.assertEqual(databases[0]["title"], "Projects")

    async def test_query_database_uses_selected_data_source_endpoint(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        client = operations.NotionOperationClient(Path(temporary.name))
        client._run_endpoint = AsyncMock(
            return_value={"results": [{"id": "page-1"}], "has_more": False}
        )

        result = await client.query_database(
            operations.DatabaseQuery(
                database_id="selected-source",
                filter={"property": "Status", "status": {"equals": "Done"}},
                sorts=[{"timestamp": "last_edited_time", "direction": "descending"}],
                page_size=25,
                start_cursor="cursor-1",
            )
        )

        self.assertEqual(result.results, [{"id": "page-1"}])
        client._run_endpoint.assert_awaited_once_with(
            "v1/data_sources/selected-source/query",
            {
                "page_size": 25,
                "filter": {"property": "Status", "status": {"equals": "Done"}},
                "sorts": [
                    {"timestamp": "last_edited_time", "direction": "descending"}
                ],
                "start_cursor": "cursor-1",
            },
        )

    async def test_search_forwards_sort_and_page_read_returns_markdown(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        client = operations.NotionOperationClient(Path(temporary.name))
        client._run_endpoint = AsyncMock(
            side_effect=[
                {"results": [], "has_more": False},
                {"id": "page-1", "properties": {}},
                {"markdown": "# Roadmap\n\nShip the connector."},
                {"results": [{"id": "block-1", "type": "heading_1"}]},
            ]
        )

        await client.search(
            operations.SearchFilter(
                object_type="database",
                sort={"direction": "descending", "timestamp": "last_edited_time"},
                page_size=10,
            )
        )
        page = await client.get_page("page-1")

        first_call = client._run_endpoint.await_args_list[0]
        self.assertEqual(first_call.args[0], "v1/search")
        self.assertEqual(
            first_call.args[1],
            {
                "page_size": 10,
                "filter": {"property": "object", "value": "data_source"},
                "sort": {
                    "direction": "descending",
                    "timestamp": "last_edited_time",
                },
            },
        )
        self.assertEqual(page.data["markdown"], "# Roadmap\n\nShip the connector.")
        self.assertEqual(page.data["blocks"][0]["id"], "block-1")
        self.assertEqual(
            [call.args[0] for call in client._run_endpoint.await_args_list[1:]],
            [
                "v1/pages/page-1",
                "v1/pages/page-1/markdown",
                "v1/blocks/page-1/children",
            ],
        )

    async def test_lazy_page_read_calls_only_markdown_endpoint(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        client = operations.NotionOperationClient(Path(temporary.name))
        client._run_endpoint = AsyncMock(return_value={"markdown": "# On demand"})

        page = await client.get_page_markdown("page-1")

        self.assertEqual(page.data, {"markdown": "# On demand"})
        client._run_endpoint.assert_awaited_once_with("v1/pages/page-1/markdown")


if __name__ == "__main__":
    unittest.main()
