# [Input] Thread-local lightweight Notion index, private credential projection, and Runtime Read hook.
# [Output] Verify authorized lazy Markdown redirects, selection enforcement, redacted failures, and path isolation.
# [Pos] Notion index-to-Read-hook Runtime integration contract test node.
# [Sync] 2026-08-28: replace Agent-visible Notion MCP calls with the single `.notion/pages/<id>.json` lazy Read path.

from __future__ import annotations

import json
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from libs.claude_agent_kit.server.notion_read_hook import (
    apply_notion_page_read_redirect,
)
from notion.errors import NotionOperationError, NotionPermissionError
from notion.operations import OperationResult


class TestNotionLazyReadHook(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self._tmp.name) / "thread-1"
        self.workspace.mkdir()
        self.tmp_root = self.workspace / ".claude-tmp"
        self.tmp_root.mkdir(mode=0o700)
        self.tmp_root.chmod(0o700)

        notion_dir = self.workspace / ".notion"
        (notion_dir / "pages").mkdir(parents=True)
        (notion_dir / "index.json").write_text(
            json.dumps(
                {
                    "pages": [
                        {
                            "page_id": "page-1",
                            "title": "Roadmap",
                            "url": "https://www.notion.so/page-1",
                            "last_edited": "2026-08-28T10:00:00Z",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        (notion_dir / "snapshot.json").write_text(
            json.dumps(
                {
                    "resource_connector_id": "connector-1",
                    "snapshot_version": "snap-index-1",
                    "source_revision": "rev-index-1",
                    "sync_cursor": "cursor-index-1",
                    "fetched_at": "2026-08-28T10:00:00Z",
                    "state": "snapshot_ready",
                }
            ),
            encoding="utf-8",
        )

        self.home = self.workspace / ".notion-home"
        self.home.mkdir(mode=0o700)
        self.home.chmod(0o700)
        auth = self.home / "auth.json"
        auth.write_text('{"access_token":"fixture-secret"}\n', encoding="utf-8")
        auth.chmod(0o600)
        self.tmp_paths: list[str] = []

    def tearDown(self) -> None:
        self._tmp.cleanup()

    async def _read(self, page_id: str = "page-1") -> dict:
        result = await apply_notion_page_read_redirect(
            "Read",
            {"file_path": f".notion/pages/{page_id}.json"},
            workspace_path=str(self.workspace),
            credential_home=str(self.home),
            tmp_workspace=str(self.workspace),
            tmp_paths=self.tmp_paths,
        )
        self.assertIsNotNone(result)
        return result or {}

    @staticmethod
    def _redirect_path(result: dict) -> Path:
        return Path(result["hookSpecificOutput"]["updatedInput"]["file_path"])

    async def test_authorized_read_fetches_markdown_only_at_read_time(self) -> None:
        with unittest.mock.patch(
            "libs.claude_agent_kit.server.notion_read_hook.NotionOperationClient.get_page_markdown",
            new=unittest.mock.AsyncMock(
                return_value=OperationResult(
                    success=True,
                    data={"markdown": "# Roadmap\n\nShip the connector."},
                )
            ),
        ) as read_markdown:
            result = await self._read()

        redirected = self._redirect_path(result)
        payload = json.loads(redirected.read_text(encoding="utf-8"))
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["page_id"], "page-1")
        self.assertEqual(payload["markdown"], "# Roadmap\n\nShip the connector.")
        self.assertEqual(payload["snapshot"]["snapshot_version"], "snap-index-1")
        self.assertEqual(redirected.parent.resolve(), self.tmp_root.resolve())
        self.assertEqual(redirected.stat().st_mode & 0o777, 0o600)
        read_markdown.assert_awaited_once_with("page-1")

    async def test_unselected_page_is_rejected_without_remote_call(self) -> None:
        with unittest.mock.patch(
            "libs.claude_agent_kit.server.notion_read_hook.NotionOperationClient.get_page_markdown",
            new=unittest.mock.AsyncMock(),
        ) as read_markdown:
            result = await self._read("page-2")

        payload = json.loads(self._redirect_path(result).read_text(encoding="utf-8"))
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["code"], "NOTION_RESOURCE_NOT_SELECTED")
        read_markdown.assert_not_awaited()

    async def test_remote_failures_are_actionable_and_redacted(self) -> None:
        secret = "notion-secret-must-not-escape"
        for failure, expected_code in (
            (
                NotionPermissionError(f"permission output contained {secret}"),
                "NOTION_PERMISSION_DENIED",
            ),
            (
                NotionOperationError(f"raw CLI output contained {secret}"),
                "NOTION_REQUEST_FAILED",
            ),
        ):
            with self.subTest(expected_code=expected_code), unittest.mock.patch(
                "libs.claude_agent_kit.server.notion_read_hook.NotionOperationClient.get_page_markdown",
                new=unittest.mock.AsyncMock(side_effect=failure),
            ):
                result = await self._read()
            raw = self._redirect_path(result).read_text(encoding="utf-8")
            self.assertEqual(json.loads(raw)["code"], expected_code)
            self.assertNotIn(secret, raw)

    async def test_missing_projection_fails_closed_without_turn_exception(self) -> None:
        result = await apply_notion_page_read_redirect(
            "Read",
            {"file_path": ".notion/pages/page-1.json"},
            workspace_path=str(self.workspace),
            credential_home=None,
            tmp_workspace=str(self.workspace),
            tmp_paths=self.tmp_paths,
        )
        self.assertIsNotNone(result)
        payload = json.loads(self._redirect_path(result or {}).read_text(encoding="utf-8"))
        self.assertEqual(payload["code"], "NOTION_AUTH_REQUIRED")

    async def test_non_notion_and_escaped_paths_fall_through(self) -> None:
        for path in (
            "files/page-1.json",
            ".notion/pages/../index.json",
            str(Path(self._tmp.name) / "outside" / "page-1.json"),
        ):
            with self.subTest(path=path):
                result = await apply_notion_page_read_redirect(
                    "Read",
                    {"file_path": path},
                    workspace_path=str(self.workspace),
                    credential_home=str(self.home),
                    tmp_workspace=str(self.workspace),
                    tmp_paths=self.tmp_paths,
                )
                self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
