# [Input] Notion operation normalization and discovery helpers.
# [Output] Verify discovery filtering plus data source query, search sort, and lazy page Markdown contracts.
# [Pos] test node in backend/tests
# [Sync] 2026-07-08: cover filtering of Notion People system data sources from database discovery.
# [Sync] 2026-08-28: construct operations with an explicit server-owned credential home.
# [Sync] 2026-08-28: lock ntn 0.15.1 data source query paths, search sort payloads,
#                    and Markdown page reads so upstream endpoint drift cannot recur.
# [Sync] 2026-08-28: cover the Markdown-only endpoint used by the Runtime Read hook.
# [Sync] 2026-08-29: prove discovery consumes every search page, rejects cursor
#                    loops, and never returns opaque upstream response blobs.
# [Sync] 2026-10-13: use official 2026-03-11 page_markdown DTOs, valid UUID identities,
#                    explicit fake API/provider boundaries, incomplete-body rejection, and safe remote errors.
# [Sync] 2026-10-13: cover recursive unknown-block Markdown expansion, deduplication,
#                    cycle/placeholder rejection, and safe child remote errors.
# [Sync] 2026-10-13: cover self-unknown link_preview leaf DTOs, URL preservation,
#                    strict leaf validation, and safe detail-read failures.
# [Sync] 2026-10-13: cover self-unknown link_to_page union leaves for page,
#                    database, and comment targets without following target IDs.

from __future__ import annotations

import asyncio
import sys
import tempfile
import unittest
import json
from pathlib import Path
from types import MethodType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from notion import operations
from notion.today import NotionTodayError


PAGE_ID = "00000000-0000-4000-8000-000000000001"
BLOCK_ID = "00000000-0000-4000-8000-000000000002"
CHILD_ID = "00000000-0000-4000-8000-000000000003"
GRANDCHILD_ID = "00000000-0000-4000-8000-000000000004"
OTHER_CHILD_ID = "00000000-0000-4000-8000-000000000005"
API_VERSION = "2026-03-11"


def page_markdown(markdown="# Roadmap\n\nShip the connector.", *, page_id=PAGE_ID, **overrides):
    return {
        "object": "page_markdown",
        "id": page_id,
        "markdown": markdown,
        "truncated": False,
        "unknown_block_ids": [],
        **overrides,
    }


def link_preview_block(*, block_id=PAGE_ID, url="https://example.com/reference", **overrides):
    return {
        "object": "block",
        "id": block_id,
        "type": "link_preview",
        "has_children": False,
        "archived": False,
        "in_trash": False,
        "link_preview": {"url": url},
        **overrides,
    }


def link_to_page_block(*, target_type="page_id", target_id=CHILD_ID, block_id=PAGE_ID, **overrides):
    return {
        "object": "block",
        "id": block_id,
        "type": "link_to_page",
        "has_children": False,
        "archived": False,
        "in_trash": False,
        "link_to_page": {"type": target_type, target_type: target_id},
        **overrides,
    }


class TestNotionOperations(unittest.IsolatedAsyncioTestCase):
    async def test_discover_databases_filters_people_system_database(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        client = operations.NotionOperationClient(Path(temporary.name), api_version=API_VERSION)

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
        self.assertNotIn("raw", databases[0])

    async def test_discovery_paginates_all_results(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        client = operations.NotionOperationClient(Path(temporary.name), api_version=API_VERSION)
        client.search = AsyncMock(
            side_effect=[
                operations.SearchResult(
                    results=[{"id": "page-1", "title": "First"}],
                    has_more=True,
                    next_cursor="cursor-2",
                ),
                operations.SearchResult(
                    results=[{"id": "page-2", "title": "Second"}],
                    has_more=False,
                    next_cursor=None,
                ),
            ]
        )

        pages = await client.discover_pages(page_size=25)

        self.assertEqual([item["page_id"] for item in pages], ["page-1", "page-2"])
        self.assertIsNone(client.search.await_args_list[0].args[0].start_cursor)
        self.assertEqual(client.search.await_args_list[1].args[0].start_cursor, "cursor-2")
        self.assertNotIn("raw", pages[0])

    async def test_discovery_rejects_non_advancing_cursor(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        client = operations.NotionOperationClient(Path(temporary.name), api_version=API_VERSION)
        client.search = AsyncMock(
            side_effect=[
                operations.SearchResult([], True, "same-cursor"),
                operations.SearchResult([], True, "same-cursor"),
            ]
        )

        with self.assertRaisesRegex(
            operations.NotionOperationError,
            "pagination did not advance",
        ):
            await client.discover_databases()

    async def test_query_database_uses_selected_data_source_endpoint(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        client = operations.NotionOperationClient(Path(temporary.name), api_version=API_VERSION)
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
        client = operations.NotionOperationClient(Path(temporary.name), api_version=API_VERSION)
        client._run_endpoint = AsyncMock(
            side_effect=[
                {"results": [], "has_more": False},
                {"object": "page", "id": PAGE_ID, "properties": {}},
                page_markdown(),
                {"results": [{"object": "block", "id": BLOCK_ID, "type": "heading_1"}]},
            ]
        )

        await client.search(
            operations.SearchFilter(
                object_type="database",
                sort={"direction": "descending", "timestamp": "last_edited_time"},
                page_size=10,
            )
        )
        page = await client.get_page(PAGE_ID)

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
        self.assertEqual(page.data["blocks"][0]["id"], BLOCK_ID)
        self.assertEqual(
            [call.args[0] for call in client._run_endpoint.await_args_list[1:]],
            [
                f"v1/pages/{PAGE_ID}",
                f"v1/pages/{PAGE_ID}/markdown",
                f"v1/blocks/{PAGE_ID}/children",
            ],
        )

    async def test_lazy_page_read_calls_only_markdown_endpoint(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        client = operations.NotionOperationClient(Path(temporary.name), api_version=API_VERSION)
        client._run_endpoint = AsyncMock(return_value=page_markdown("# On demand"))

        page = await client.get_page_markdown(PAGE_ID)

        self.assertEqual(page.data, {"markdown": "# On demand"})
        client._run_endpoint.assert_awaited_once_with(f"v1/pages/{PAGE_ID}/markdown")

    async def test_markdown_rejects_wrong_identity_shape_and_incomplete_body(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        client = operations.NotionOperationClient(Path(temporary.name), api_version=API_VERSION)
        cases = [
            ({**page_markdown(), "id": "00000000-0000-4000-8000-000000000099"}, "NOTION_UPSTREAM_UNAVAILABLE", 502),
            ({**page_markdown(), "object": "page"}, "NOTION_UPSTREAM_UNAVAILABLE", 502),
            ({**page_markdown(), "markdown": []}, "NOTION_UPSTREAM_UNAVAILABLE", 502),
            ({**page_markdown(), "truncated": True}, "NOTION_MARKDOWN_INCOMPLETE", 422),
        ]
        for payload, code, status in cases:
            with self.subTest(code=code):
                client._run_endpoint = AsyncMock(return_value=payload)
                with self.assertRaises(NotionTodayError) as failure:
                    await client.get_page_markdown(PAGE_ID)
                self.assertEqual((failure.exception.code, failure.exception.status), (code, status))

        client._run_endpoint = AsyncMock(
            side_effect=[
                page_markdown(
                    '<unknown url="https://www.notion.so/00000000-0000-4000-8000-000000000099" />',
                    unknown_block_ids=[BLOCK_ID],
                ),
                page_markdown("child", page_id=BLOCK_ID),
            ]
        )
        with self.assertRaises(NotionTodayError) as missing_placeholder:
            await client.get_page_markdown(PAGE_ID)
        self.assertEqual(
            (missing_placeholder.exception.code, missing_placeholder.exception.status),
            ("NOTION_MARKDOWN_INCOMPLETE", 422),
        )

    async def test_markdown_expands_one_level_and_recursive_subtrees_preserving_surrounding_text(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        client = operations.NotionOperationClient(Path(temporary.name), api_version=API_VERSION)
        client._run_endpoint = AsyncMock(
            side_effect=[
                page_markdown(
                    f'before\n<unknown url="https://www.notion.so/{CHILD_ID}" />\nafter',
                    truncated=True,
                    unknown_block_ids=[CHILD_ID],
                ),
                page_markdown(
                    f'child-before\n<unknown url="https://www.notion.so/{GRANDCHILD_ID}" />\nchild-after',
                    page_id=CHILD_ID,
                    truncated=True,
                    unknown_block_ids=[GRANDCHILD_ID],
                ),
                page_markdown("", page_id=GRANDCHILD_ID),
            ]
        )

        result = await client.get_page_markdown(PAGE_ID)

        self.assertEqual(
            result.data["markdown"],
            "before\nchild-before\n\nchild-after\nafter",
        )
        self.assertEqual(
            [call.args[0] for call in client._run_endpoint.await_args_list],
            [
                f"v1/pages/{PAGE_ID}/markdown",
                f"v1/pages/{CHILD_ID}/markdown",
                f"v1/pages/{GRANDCHILD_ID}/markdown",
            ],
        )

    async def test_markdown_reads_a_repeated_block_once_and_replaces_each_reference(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        client = operations.NotionOperationClient(Path(temporary.name), api_version=API_VERSION)
        client._run_endpoint = AsyncMock(
            side_effect=[
                page_markdown(
                    f'A<unknown url="https://www.notion.so/{CHILD_ID}" />B'
                    f'<unknown url="https://www.notion.so/{CHILD_ID}" />C',
                    unknown_block_ids=[CHILD_ID],
                ),
                page_markdown("child", page_id=CHILD_ID),
            ]
        )

        result = await client.get_page_markdown(PAGE_ID)

        self.assertEqual(result.data["markdown"], "AchildBchildC")
        self.assertEqual(client._run_endpoint.await_count, 2)

    async def test_markdown_expands_self_unknown_link_preview_leaf_without_fetching_url(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        url = "https://external.example/reference?source=notion&part=1"
        client = operations.NotionOperationClient(Path(temporary.name), api_version=API_VERSION)
        client._run_endpoint = AsyncMock(
            side_effect=[
                page_markdown(
                    f"before\n<unknown url=\"https://www.notion.so/{PAGE_ID}\" />\n"
                    f"middle\n<unknown url=\"https://www.notion.so/{PAGE_ID}\" />\nafter",
                    truncated=True,
                    unknown_block_ids=[PAGE_ID],
                ),
                link_preview_block(url=url),
            ]
        )

        result = await client.get_page_markdown(PAGE_ID)

        expected_leaf = "```json\n" + json.dumps(
            {"type": "link_preview", "url": url}, ensure_ascii=False
        ) + "\n```"
        self.assertEqual(
            result.data["markdown"],
            f"before\n{expected_leaf}\nmiddle\n{expected_leaf}\nafter",
        )
        self.assertEqual(
            [call.args[0] for call in client._run_endpoint.await_args_list],
            [f"v1/pages/{PAGE_ID}/markdown", f"v1/blocks/{PAGE_ID}"],
        )
        self.assertNotIn("external.example", [call.args[0] for call in client._run_endpoint.await_args_list])

    async def test_markdown_expands_all_link_to_page_union_targets_without_following_ids(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        targets = [
            ("page_id", CHILD_ID),
            ("database_id", GRANDCHILD_ID),
            ("comment_id", OTHER_CHILD_ID),
        ]
        for target_type, target_id in targets:
            with self.subTest(target_type=target_type):
                client = operations.NotionOperationClient(Path(temporary.name), api_version=API_VERSION)
                client._run_endpoint = AsyncMock(
                    side_effect=[
                        page_markdown(
                            f'before\n<unknown url="https://www.notion.so/{PAGE_ID}" />\nafter',
                            truncated=True,
                            unknown_block_ids=[PAGE_ID],
                        ),
                        link_to_page_block(target_type=target_type, target_id=target_id),
                    ]
                )

                result = await client.get_page_markdown(PAGE_ID)

                expected = "```json\n" + json.dumps(
                    {
                        "type": "link_to_page",
                        "link_to_page": {"type": target_type, target_type: target_id},
                    },
                    ensure_ascii=False,
                ) + "\n```"
                self.assertEqual(result.data["markdown"], f"before\n{expected}\nafter")
                self.assertEqual(
                    [call.args[0] for call in client._run_endpoint.await_args_list],
                    [f"v1/pages/{PAGE_ID}/markdown", f"v1/blocks/{PAGE_ID}"],
                )
                self.assertNotIn(target_id, [call.args[0] for call in client._run_endpoint.await_args_list])

    async def test_markdown_rejects_invalid_link_to_page_union_shapes(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        cases = [
            {"type": "workspace", "workspace": CHILD_ID},
            {"type": "page_id", "page_id": "invalid id!"},
            {"type": "page_id"},
            {"type": "page_id", "page_id": CHILD_ID, "title": "extra"},
            {"type": "page_id", "database_id": CHILD_ID},
        ]
        for link_value in cases:
            with self.subTest(link_value=link_value):
                client = operations.NotionOperationClient(Path(temporary.name), api_version=API_VERSION)
                client._run_endpoint = AsyncMock(
                    side_effect=[
                        page_markdown(
                            f'<unknown url="https://www.notion.so/{PAGE_ID}" />',
                            truncated=True,
                            unknown_block_ids=[PAGE_ID],
                        ),
                        link_to_page_block(link_to_page=link_value),
                    ]
                )
                with self.assertRaises(NotionTodayError) as failure:
                    await client.get_page_markdown(PAGE_ID)
                self.assertEqual((failure.exception.code, failure.exception.status), ("NOTION_MARKDOWN_INCOMPLETE", 422))

    async def test_markdown_rejects_invalid_self_leaf_id_and_shape(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)

        invalid_id_client = operations.NotionOperationClient(Path(temporary.name), api_version=API_VERSION)
        invalid_id_client._run_endpoint = AsyncMock(
            return_value=page_markdown(
                '<unknown url="https://www.notion.so/not-a-valid-id" />',
                truncated=True,
                unknown_block_ids=["invalid id!"],
            )
        )
        with self.assertRaises(NotionTodayError) as invalid_id:
            await invalid_id_client.get_page_markdown(PAGE_ID)
        self.assertEqual((invalid_id.exception.code, invalid_id.exception.status), ("NOTION_UPSTREAM_UNAVAILABLE", 502))

        mismatch_client = operations.NotionOperationClient(Path(temporary.name), api_version=API_VERSION)
        mismatch_client._run_endpoint = AsyncMock(
            side_effect=[
                page_markdown(
                    f'<unknown url="https://www.notion.so/{PAGE_ID}" />',
                    truncated=True,
                    unknown_block_ids=[PAGE_ID],
                ),
                link_preview_block(block_id=BLOCK_ID),
            ]
        )
        with self.assertRaises(NotionTodayError) as mismatch:
            await mismatch_client.get_page_markdown(PAGE_ID)
        self.assertEqual((mismatch.exception.code, mismatch.exception.status), ("NOTION_UPSTREAM_UNAVAILABLE", 502))

    async def test_markdown_rejects_unsupported_self_leaf_shapes(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        cases = [
            {"type": "paragraph"},
            {"has_children": True},
            {"archived": True},
            {"in_trash": True},
            {"link_preview": {}},
            {"link_preview": {"url": "https://example.com", "title": "extra"}},
            {"link_preview": {"url": "   "}},
        ]
        for overrides in cases:
            with self.subTest(overrides=overrides):
                client = operations.NotionOperationClient(Path(temporary.name), api_version=API_VERSION)
                client._run_endpoint = AsyncMock(
                    side_effect=[
                        page_markdown(
                            f'<unknown url="https://www.notion.so/{PAGE_ID}" />',
                            truncated=True,
                            unknown_block_ids=[PAGE_ID],
                        ),
                        link_preview_block(**overrides),
                    ]
                )
                with self.assertRaises(NotionTodayError) as failure:
                    await client.get_page_markdown(PAGE_ID)
                self.assertEqual((failure.exception.code, failure.exception.status), ("NOTION_MARKDOWN_INCOMPLETE", 422))

    async def test_markdown_propagates_self_leaf_detail_404_and_429_safely(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        for error in [
            NotionTodayError("NOTION_RESOURCE_UNAVAILABLE", 404),
            NotionTodayError("NOTION_RATE_LIMITED", 429, retry_after=7),
        ]:
            with self.subTest(code=error.code):
                client = operations.NotionOperationClient(Path(temporary.name), api_version=API_VERSION)
                client._run_endpoint = AsyncMock(
                    side_effect=[
                        page_markdown(
                            f'<unknown url="https://www.notion.so/{PAGE_ID}" />',
                            truncated=True,
                            unknown_block_ids=[PAGE_ID],
                        ),
                        error,
                    ]
                )
                with self.assertRaises(NotionTodayError) as failure:
                    await client.get_page_markdown(PAGE_ID)
                self.assertEqual((failure.exception.code, failure.exception.status), (error.code, error.status))
                self.assertNotIn("secret", str(failure.exception))

    async def test_markdown_rejects_cycles_and_unmatched_or_ambiguous_placeholders(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)

        cycle_client = operations.NotionOperationClient(Path(temporary.name), api_version=API_VERSION)
        cycle_client._run_endpoint = AsyncMock(
            side_effect=[
                page_markdown(
                    f'<unknown url="https://www.notion.so/{CHILD_ID}" />',
                    unknown_block_ids=[CHILD_ID],
                ),
                page_markdown(
                    f'<unknown url="https://www.notion.so/{PAGE_ID}" />',
                    page_id=CHILD_ID,
                    unknown_block_ids=[PAGE_ID],
                ),
            ]
        )
        with self.assertRaises(NotionTodayError) as cycle_failure:
            await cycle_client.get_page_markdown(PAGE_ID)
        self.assertEqual((cycle_failure.exception.code, cycle_failure.exception.status), ("NOTION_MARKDOWN_INCOMPLETE", 422))

        self_leaf_client = operations.NotionOperationClient(Path(temporary.name), api_version=API_VERSION)
        self_leaf_client._run_endpoint = AsyncMock(
            side_effect=[
                page_markdown(
                    f'<unknown url="https://www.notion.so/{PAGE_ID}" />',
                    truncated=True,
                    unknown_block_ids=[PAGE_ID],
                ),
                {
                    "object": "block",
                    "id": PAGE_ID,
                    "type": "paragraph",
                    "has_children": False,
                    "archived": False,
                    "in_trash": False,
                    "paragraph": {"rich_text": []},
                },
            ]
        )
        with self.assertRaises(NotionTodayError) as self_leaf_failure:
            await self_leaf_client.get_page_markdown(PAGE_ID)
        self.assertEqual((self_leaf_failure.exception.code, self_leaf_failure.exception.status), ("NOTION_MARKDOWN_INCOMPLETE", 422))

        for markdown, ids in [
            (
                f'<unknown url="https://www.notion.so/{OTHER_CHILD_ID}" />',
                [CHILD_ID],
            ),
            (
                f'<unknown url="https://www.notion.so/{CHILD_ID}-{OTHER_CHILD_ID}" />',
                [CHILD_ID, OTHER_CHILD_ID],
            ),
        ]:
            with self.subTest(markdown=markdown):
                client = operations.NotionOperationClient(Path(temporary.name), api_version=API_VERSION)
                child_payloads = [page_markdown("child", page_id=identifier) for identifier in ids]
                client._run_endpoint = AsyncMock(
                    side_effect=[page_markdown(markdown, unknown_block_ids=ids), *child_payloads]
                )
                with self.assertRaises(NotionTodayError) as failure:
                    await client.get_page_markdown(PAGE_ID)
                self.assertEqual((failure.exception.code, failure.exception.status), ("NOTION_MARKDOWN_INCOMPLETE", 422))

        invalid_client = operations.NotionOperationClient(Path(temporary.name), api_version=API_VERSION)
        invalid_client._run_endpoint = AsyncMock(
            return_value=page_markdown("body", unknown_block_ids=["invalid id!"])
        )
        with self.assertRaises(NotionTodayError) as invalid_failure:
            await invalid_client.get_page_markdown(PAGE_ID)
        self.assertEqual((invalid_failure.exception.code, invalid_failure.exception.status), ("NOTION_UPSTREAM_UNAVAILABLE", 502))

    async def test_markdown_propagates_safe_child_404_and_429_without_body_or_secret(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        for error in [
            NotionTodayError("NOTION_RESOURCE_UNAVAILABLE", 404),
            NotionTodayError("NOTION_RATE_LIMITED", 429, retry_after=7),
        ]:
            with self.subTest(code=error.code):
                client = operations.NotionOperationClient(Path(temporary.name), api_version=API_VERSION)
                client._run_endpoint = AsyncMock(
                    side_effect=[
                        page_markdown(
                            f'<unknown url="https://www.notion.so/{CHILD_ID}" />',
                            unknown_block_ids=[CHILD_ID],
                        ),
                        error,
                    ]
                )
                with self.assertRaises(NotionTodayError) as failure:
                    await client.get_page_markdown(PAGE_ID)
                self.assertEqual((failure.exception.code, failure.exception.status), (error.code, error.status))
                self.assertNotIn("secret", str(failure.exception))

    async def test_explicit_provider_maps_remote_errors_without_leaking_messages(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        client = operations.NotionOperationClient(Path(temporary.name), api_version=API_VERSION)
        for status, code, retry_after in [(404, "NOTION_RESOURCE_UNAVAILABLE", None), (429, "NOTION_RATE_LIMITED", 7), (502, "NOTION_UPSTREAM_UNAVAILABLE", None)]:
            with self.subTest(status=status):
                error = {"status": status, "message": "secret page details"}
                if status == 429:
                    error["headers"] = {"Retry-After": "7"}
                process = SimpleNamespace(
                    returncode=1,
                    communicate=AsyncMock(return_value=(json.dumps({"error": error}).encode(), b"")),
                )
                with patch.object(operations.asyncio, "create_subprocess_exec", AsyncMock(return_value=process)) as provider:
                    with self.assertRaises(NotionTodayError) as failure:
                        await client.get_page_markdown(PAGE_ID)
                self.assertEqual(failure.exception.code, code)
                self.assertEqual(failure.exception.status, status)
                self.assertEqual(failure.exception.retry_after, retry_after)
                self.assertNotIn("secret page details", str(failure.exception))
                args = provider.await_args.args
                self.assertIn("--notion-version", args)
                self.assertIn(API_VERSION, args)

    async def test_timeout_kills_and_reaps_provider_and_returns_safe_504(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        client = operations.NotionOperationClient(Path(temporary.name), api_version=API_VERSION)
        process = SimpleNamespace(
            returncode=None,
            communicate=AsyncMock(),
            kill=MagicMock(),
            wait=AsyncMock(),
        )
        async def timed_out(awaitable, timeout):
            del timeout
            awaitable.close()
            raise asyncio.TimeoutError
        with patch.object(operations.asyncio, "create_subprocess_exec", AsyncMock(return_value=process)), \
                patch.object(operations.asyncio, "wait_for", timed_out):
            with self.assertRaises(NotionTodayError) as failure:
                await client.get_page_markdown(PAGE_ID)
        self.assertEqual((failure.exception.code, failure.exception.status), ("NOTION_UPSTREAM_TIMEOUT", 504))
        self.assertNotIn("secret", str(failure.exception))
        process.kill.assert_called_once_with()
        process.wait.assert_awaited_once_with()


if __name__ == "__main__":
    unittest.main()
