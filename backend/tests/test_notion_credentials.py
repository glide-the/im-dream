# [Input] Isolated agentdata/workspace roots and synthetic ntn credential files.
# [Output] Verify actor isolation, private permissions, atomic per-thread projection, rotation, revocation, and path safety.
# [Pos] Notion credential provider contract test node in backend/tests.
# [Sync] 2026-08-28: add coverage for the agentdata user source → thread projection architecture.

from __future__ import annotations

import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from notion.credentials import (
    NOTION_AUTH_FILENAME,
    NotionCredentialSettings,
    NotionCredentialStore,
)
from notion.errors import NotionCredentialError


class TestNotionCredentialStore(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.agentdata = self.root / "agentdata"
        self.workspace_root = self.agentdata / "agent-workspaces"
        self.workspace_root.mkdir(parents=True)
        self.thread_a = self.workspace_root / "thread-a"
        self.thread_b = self.workspace_root / "thread-b"
        self.thread_a.mkdir()
        self.thread_b.mkdir()
        self.store = NotionCredentialStore(
            NotionCredentialSettings(runtime_root=self.agentdata / "notion-runtime"),
            workspace_root_provider=lambda: self.workspace_root,
            thread_ids_provider=lambda actor: (
                [{"id": "thread-a"}] if actor == 7 else [{"id": "thread-b"}]
            ),
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _authorize(self, actor: int, session: str, token: str) -> Path:
        pending = self.store.begin_auth(actor, session)
        (pending / NOTION_AUTH_FILENAME).write_text(
            '{"access_token":"' + token + '"}\n',
            encoding="utf-8",
        )
        (pending / "config.json").write_text('{"active":"workspace"}\n', encoding="utf-8")
        return self.store.promote_auth(actor, session)

    def test_default_runtime_root_is_beside_agent_workspace_not_process_home(self):
        from notion.credentials import NotionCredentialSettings

        with unittest.mock.patch.dict(
            os.environ,
            {
                "AGENT_CWD": str(self.workspace_root),
                "HOME": str(self.root / "process-home"),
                "NOTION_HOME": str(self.root / "attacker-home"),
                "INK_NOTION_RUNTIME_ROOT": "",
            },
            clear=False,
        ):
            settings = NotionCredentialSettings.from_env()
        self.assertEqual(
            settings.runtime_root,
            (self.agentdata / "notion-runtime").resolve(strict=False),
        )
        self.assertNotIn("process-home", str(settings.runtime_root))

    def test_users_have_distinct_opaque_private_roots(self):
        paths_a = self.store.user_paths(7)
        paths_b = self.store.user_paths(8)
        self.assertNotEqual(paths_a.root, paths_b.root)
        self.assertNotIn("/7/", str(paths_a.root))
        self.assertNotIn("/8/", str(paths_b.root))
        self.assertEqual(paths_a.root.stat().st_mode & 0o777, 0o700)
        self.assertEqual(paths_b.root.stat().st_mode & 0o777, 0o700)

    def test_actor_a_and_b_receive_only_their_own_credentials(self):
        self._authorize(7, "a" * 32, "actor-a-secret")
        self._authorize(8, "b" * 32, "actor-b-secret")

        projection_a = self.store.project_thread(7, self.thread_a)
        projection_b = self.store.project_thread(8, self.thread_b)

        content_a = (projection_a.thread_home / NOTION_AUTH_FILENAME).read_text()
        content_b = (projection_b.thread_home / NOTION_AUTH_FILENAME).read_text()
        self.assertIn("actor-a-secret", content_a)
        self.assertNotIn("actor-b-secret", content_a)
        self.assertIn("actor-b-secret", content_b)
        self.assertNotEqual(projection_a.revision, projection_b.revision)
        self.assertEqual(projection_a.thread_home.stat().st_mode & 0o777, 0o700)
        self.assertEqual(
            (projection_a.thread_home / NOTION_AUTH_FILENAME).stat().st_mode & 0o777,
            0o600,
        )

    def test_reauthorization_updates_only_next_projection(self):
        self._authorize(7, "c" * 32, "old-secret")
        first = self.store.project_thread(7, self.thread_a)
        self.assertIn("old-secret", (first.thread_home / NOTION_AUTH_FILENAME).read_text())

        self._authorize(7, "d" * 32, "new-secret")
        # Effective source rotated, but the already projected turn remains old
        # until the next explicit per-turn synchronization.
        self.assertIn("old-secret", (first.thread_home / NOTION_AUTH_FILENAME).read_text())
        second = self.store.project_thread(7, self.thread_a)
        self.assertIn("new-secret", (second.thread_home / NOTION_AUTH_FILENAME).read_text())
        self.assertNotEqual(first.revision, second.revision)

    def test_missing_credentials_fail_closed_and_clear_stale_projection(self):
        self._authorize(7, "e" * 32, "stale-secret")
        projection = self.store.project_thread(7, self.thread_a)
        self.assertTrue(projection.thread_home.exists())
        self.store.clear_user(7)
        self.assertFalse((self.thread_a / ".notion-home").exists())
        self.assertFalse(self.store.has_credentials(7))
        with self.assertRaises(NotionCredentialError):
            self.store.project_thread(7, self.thread_a)
        self.assertFalse((self.thread_a / ".notion-home").exists())

    def test_projection_rejects_workspace_symlink_escape(self):
        self._authorize(7, "f" * 32, "secret")
        outside = self.root / "outside"
        outside.mkdir()
        link = self.workspace_root / "thread-link"
        link.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(NotionCredentialError):
            self.store.project_thread(7, link)


if __name__ == "__main__":
    unittest.main()
