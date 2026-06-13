# [Input] Consume backend/routers/workspace.py and workspace file manager APIs.
# [Output] Validate workspace router download headers and Unicode filename handling.
# [Pos] test node in backend/tests
# [Sync] 2026-06-13: initial coverage for RFC 8187 download Content-Disposition.

"""Regression tests for the workspace file router."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]  # backend/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.testclient import TestClient

import tests._sdk_stubs  # noqa: F401
from libs.claude_agent_kit.server.workspace import get_or_create_workspace
from routers import workspace as workspace_router


class TestWorkspaceDownloadHeaders(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["AGENT_CWD"] = self._tmp.name

        self._auth_patch = unittest.mock.patch.object(
            workspace_router.auth,
            "verify_access_token",
            return_value={"user_id": 1, "email": "test@example.com"},
        )
        self._auth_patch.start()

        app = FastAPI()
        app.include_router(workspace_router.router)
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self._auth_patch.stop()
        os.environ.pop("AGENT_CWD", None)
        self._tmp.cleanup()

    def test_download_unicode_filename_uses_latin1_safe_header(self):
        session_id = "download-unicode"
        filename = "AGI_Builder_二轮问卷.md"
        workspace = get_or_create_workspace(session_id)
        target = workspace / "files" / filename
        target.write_text("hello", encoding="utf-8")

        response = self.client.get(
            "/api/workspace/files/download",
            params={"sessionId": session_id, "path": f"files/{filename}"},
            headers={"Authorization": "Bearer test-token"},
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.content, b"hello")

        disposition = response.headers["content-disposition"]
        disposition.encode("latin-1")
        self.assertIn('filename="', disposition)
        self.assertIn(f"filename*=UTF-8''{quote(filename, safe='')}", disposition)
        self.assertNotIn("二轮问卷", disposition)


if __name__ == "__main__":
    unittest.main()
