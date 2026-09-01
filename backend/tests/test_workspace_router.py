# [Input] Consume backend/routers/workspace.py and workspace file manager APIs.
# [Output] Validate workspace file/content/download contracts, including Thread ownership and safe directory ZIPs.
# [Pos] test node in backend/tests
# [Sync] 2026-06-13: initial coverage for RFC 8187 download Content-Disposition.
# [Sync] 2026-06-21: cover workspace file APIs preserving Settings-backed
#                    sandbox network policy during workspace refresh.
# [Sync] 2026-06-25: assert open sandbox network mode omits sandbox.network
#                    before disabled refresh writes an explicit deny policy.
# [Sync] 2026-07-26: cover refresh preserving sandbox_fs_allowed_write_paths
#                    from Settings during workspace file API init.
# [Sync] 2026-08-17: cover directory ZIP layout, Unicode names, and symlink escape denial.
# [Sync] 2026-08-22: cover the no-create workspace:// content boundary: owned Thread,
#                    Workspace Mode, strict public paths, regular files, and no symlinks.
# [Sync] 2026-09-01: keep recursive workspace trees available when managed
#                    builtin Skills are read-only links outside the thread.

"""Regression tests for the workspace file router."""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
import unittest.mock
import zipfile
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
        self._thread_patch = unittest.mock.patch.object(
            workspace_router.database,
            "get_chat_thread",
            return_value={"id": "owned-thread", "user_id": 1},
        )
        self._thread_patch.start()
        self._config_patch = unittest.mock.patch.object(
            workspace_router.database,
            "get_system_config",
            return_value={"workspace_enabled": True},
        )
        self._config_patch.start()

        app = FastAPI()
        app.include_router(workspace_router.router)
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self._config_patch.stop()
        self._thread_patch.stop()
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

    def test_download_directory_returns_zip_with_selected_folder_root(self):
        session_id = "download-directory"
        directory_name = "第一章"
        workspace = get_or_create_workspace(session_id)
        target = workspace / "files" / directory_name
        (target / "场景").mkdir(parents=True)
        (target / "空目录").mkdir()
        (target / "大纲.md").write_text("chapter outline", encoding="utf-8")
        (target / "场景" / "开场.txt").write_text("opening scene", encoding="utf-8")

        response = self.client.get(
            "/api/workspace/files/download",
            params={"sessionId": session_id, "path": f"files/{directory_name}"},
            headers={"Authorization": "Bearer test-token"},
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["content-type"], "application/zip")
        self.assertIn(
            f"filename*=UTF-8''{quote(f'{directory_name}.zip', safe='')}",
            response.headers["content-disposition"],
        )
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            self.assertEqual(
                archive.namelist(),
                [
                    f"{directory_name}/",
                    f"{directory_name}/大纲.md",
                    f"{directory_name}/场景/",
                    f"{directory_name}/场景/开场.txt",
                    f"{directory_name}/空目录/",
                ],
            )
            self.assertEqual(
                archive.read(f"{directory_name}/场景/开场.txt"),
                b"opening scene",
            )

    def test_download_directory_rejects_symlink_escape(self):
        session_id = "download-directory-symlink"
        workspace = get_or_create_workspace(session_id)
        target = workspace / "files" / "export"
        target.mkdir(parents=True)
        outside_file = Path(self._tmp.name) / "outside-secret.txt"
        outside_file.write_text("secret", encoding="utf-8")
        (target / "secret-link.txt").symlink_to(outside_file)

        response = self.client.get(
            "/api/workspace/files/download",
            params={"sessionId": session_id, "path": "files/export"},
            headers={"Authorization": "Bearer test-token"},
        )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(response.json()["detail"]["code"], "PATH_TRAVERSAL")

    def test_content_reads_owned_unicode_regular_file_without_exposing_disk_path(self):
        session_id = "content-owned"
        filename = "分镜 preview.png"
        workspace = get_or_create_workspace(session_id)
        payload = b"not-a-real-png-but-route-bytes"
        (workspace / "files" / filename).write_bytes(payload)

        response = self.client.get(
            "/api/workspace/files/content",
            params={"sessionId": session_id, "path": f"files/{filename}"},
            headers={"Authorization": "Bearer test-token"},
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.content, payload)
        self.assertEqual(response.headers["content-type"], "image/png")
        self.assertEqual(response.headers["cache-control"], "private, no-store")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertNotIn(str(workspace), response.text)

    def test_content_foreign_thread_is_hidden_before_workspace_probe(self):
        with (
            unittest.mock.patch.object(
                workspace_router.database,
                "get_chat_thread",
                return_value=None,
            ),
            unittest.mock.patch.object(
                workspace_router,
                "get_existing_workspace",
            ) as existing_workspace,
        ):
            response = self.client.get(
                "/api/workspace/files/content",
                params={"sessionId": "foreign-thread", "path": "files/image.png"},
                headers={"Authorization": "Bearer test-token"},
            )

        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(response.json()["detail"]["code"], "WORKSPACE_NOT_FOUND")
        existing_workspace.assert_not_called()

    def test_content_workspace_disabled_is_rejected_before_workspace_probe(self):
        with (
            unittest.mock.patch.object(
                workspace_router.database,
                "get_system_config",
                return_value={"workspace_enabled": False},
            ),
            unittest.mock.patch.object(
                workspace_router,
                "get_existing_workspace",
            ) as existing_workspace,
        ):
            response = self.client.get(
                "/api/workspace/files/content",
                params={"sessionId": "disabled-thread", "path": "files/image.png"},
                headers={"Authorization": "Bearer test-token"},
            )

        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["detail"]["code"], "WORKSPACE_DISABLED")
        existing_workspace.assert_not_called()

    def test_content_rejects_ambiguous_and_non_public_paths_without_workspace_probe(self):
        invalid_paths = (
            "../secret.png",
            "files/../secret.png",
            "/files/secret.png",
            "files\\secret.png",
            "files//secret.png",
            "files/./secret.png",
            "files/",
            "files/%2e%2e/secret.png",
            "files/image.png?download=1",
            "files/image.png#fragment",
            "logs/secret.png",
            "C:/secret.png",
        )
        with unittest.mock.patch.object(
            workspace_router,
            "get_existing_workspace",
        ) as existing_workspace:
            for path in invalid_paths:
                with self.subTest(path=path):
                    response = self.client.get(
                        "/api/workspace/files/content",
                        params={"sessionId": "content-paths", "path": path},
                        headers={"Authorization": "Bearer test-token"},
                    )
                    self.assertEqual(response.status_code, 400, response.text)
                    self.assertEqual(response.json()["detail"]["code"], "INVALID_WORKSPACE_URI")
        existing_workspace.assert_not_called()

    def test_content_rejects_in_workspace_symlink_and_directory(self):
        session_id = "content-symlink"
        workspace = get_or_create_workspace(session_id)
        target = workspace / "files" / "target.png"
        target.write_bytes(b"image")
        (workspace / "files" / "alias.png").symlink_to(target)
        (workspace / "files" / "folder").mkdir()
        outside = Path(self._tmp.name) / "outside"
        outside.mkdir()
        (outside / "secret.png").write_bytes(b"outside")
        (workspace / "files" / "linked-folder").symlink_to(outside, target_is_directory=True)

        symlink_response = self.client.get(
            "/api/workspace/files/content",
            params={"sessionId": session_id, "path": "files/alias.png"},
            headers={"Authorization": "Bearer test-token"},
        )
        directory_response = self.client.get(
            "/api/workspace/files/content",
            params={"sessionId": session_id, "path": "files/folder"},
            headers={"Authorization": "Bearer test-token"},
        )
        parent_symlink_response = self.client.get(
            "/api/workspace/files/content",
            params={"sessionId": session_id, "path": "files/linked-folder/secret.png"},
            headers={"Authorization": "Bearer test-token"},
        )

        self.assertEqual(symlink_response.status_code, 400, symlink_response.text)
        self.assertEqual(symlink_response.json()["detail"]["code"], "SYMLINK_NOT_ALLOWED")
        self.assertEqual(directory_response.status_code, 400, directory_response.text)
        self.assertEqual(directory_response.json()["detail"]["code"], "IS_DIRECTORY")
        self.assertEqual(parent_symlink_response.status_code, 400, parent_symlink_response.text)
        self.assertEqual(parent_symlink_response.json()["detail"]["code"], "SYMLINK_NOT_ALLOWED")

    def test_content_missing_workspace_does_not_create_one(self):
        session_id = "content-missing-workspace"
        response = self.client.get(
            "/api/workspace/files/content",
            params={"sessionId": session_id, "path": "files/image.png"},
            headers={"Authorization": "Bearer test-token"},
        )

        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(response.json()["detail"]["code"], "WORKSPACE_NOT_FOUND")
        self.assertFalse((Path(self._tmp.name) / session_id).exists())

    def test_list_refresh_preserves_disabled_sandbox_network_policy(self):
        session_id = "network-disabled"
        workspace = get_or_create_workspace(
            session_id,
            sandbox_network_mode="open",
            sandbox_network_allowed_domains=["github.com"],
        )
        settings_path = workspace / ".claude" / "settings.json"
        initial_settings = json.loads(settings_path.read_text(encoding="utf-8"))
        self.assertNotIn("network", initial_settings["sandbox"])

        with unittest.mock.patch.object(
            workspace_router.database,
            "get_system_config",
            return_value={
                "workspace_enabled": True,
                "sandbox_network_mode": "disabled",
                "sandbox_network_allowed_domains": ["github.com"],
            },
        ):
            response = self.client.get(
                "/api/workspace/files",
                params={"sessionId": session_id},
                headers={"Authorization": "Bearer test-token"},
            )

        self.assertEqual(response.status_code, 200, response.text)
        refreshed_settings = json.loads(settings_path.read_text(encoding="utf-8"))
        self.assertEqual(
            refreshed_settings["sandbox"]["network"],
            {"allowedDomains": [], "deniedDomains": ["*"]},
        )

    def test_list_refresh_preserves_sandbox_fs_allowed_write_paths(self):
        session_id = "fs-extra-paths"
        workspace = get_or_create_workspace(session_id)
        settings_path = workspace / ".claude" / "settings.json"
        initial_settings = json.loads(settings_path.read_text(encoding="utf-8"))
        self.assertNotIn(
            "/data/out",
            initial_settings["sandbox"]["filesystem"]["allowWrite"],
        )

        with unittest.mock.patch.object(
            workspace_router.database,
            "get_system_config",
            return_value={
                "workspace_enabled": True,
                "sandbox_fs_allowed_write_paths": ["/data/out", "/var/cache"],
            },
        ):
            response = self.client.get(
                "/api/workspace/files",
                params={"sessionId": session_id},
                headers={"Authorization": "Bearer test-token"},
            )

        self.assertEqual(response.status_code, 200, response.text)
        refreshed_settings = json.loads(settings_path.read_text(encoding="utf-8"))
        allow_write = refreshed_settings["sandbox"]["filesystem"]["allowWrite"]
        self.assertEqual(allow_write[-2:], ["/data/out", "/var/cache"])

    def test_recursive_list_keeps_external_skill_link_as_leaf(self):
        session_id = "recursive-managed-skill-link"
        workspace = get_or_create_workspace(session_id)
        managed_source = Path(self._tmp.name) / "managed-skill-source"
        managed_source.mkdir()
        (managed_source / "SKILL.md").write_text(
            "managed instructions",
            encoding="utf-8",
        )
        managed_link = workspace / "skills" / "managed-skill"
        managed_link.symlink_to(managed_source, target_is_directory=True)

        response = self.client.get(
            "/api/workspace/files",
            params={"sessionId": session_id, "recursive": "1"},
            headers={"Authorization": "Bearer test-token"},
        )

        self.assertEqual(response.status_code, 200, response.text)
        tree = response.json()["tree"]
        skills = next(node for node in tree if node["name"] == "skills")
        managed = next(
            node for node in skills["children"] if node["name"] == "managed-skill"
        )
        self.assertFalse(managed["isDirectory"])
        self.assertNotIn("children", managed)


if __name__ == "__main__":
    unittest.main()
