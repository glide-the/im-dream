# [Input] Consume backend/routers/workspace.py and workspace file manager APIs.
# [Output] Validate workspace file/content/download contracts, including Thread ownership and safe directory ZIPs.
# [Pos] test node in backend/tests
# [Sync] 2026-09-15: use actual Admin OAuth/strict Thread transport and fence retired DB ownership.
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
# [Sync] 2026-09-11: give the download endpoint the same ownership, Workspace
#                    Mode, public-path, no-create, and symlink contract as the
#                    content endpoint for Chat explicit downloads.
# [Sync] 2026-09-15: use typed Admin SystemConfig reads before every workspace filesystem operation.

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
from uuid import UUID

import httpx

ROOT = Path(__file__).resolve().parents[1]  # backend/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.testclient import TestClient

import tests._sdk_stubs  # noqa: F401
from libs.claude_agent_kit.server.workspace import get_or_create_workspace
from routers import workspace as workspace_router
from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.chat_data import GET_THREAD
from services.admin_data.request_auth import AdminRequestAuth
from services.admin_data.workspace_data import WORKSPACE_SCHEMA_REQUIREMENTS
from services.admin_data.system_config_data import GET_USER_SYSTEM_CONFIG
from tests.test_admin_request_auth import Verifier


class TestWorkspaceDownloadHeaders(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["AGENT_CWD"] = self._tmp.name

        self._system_config = {"workspace_enabled": True}

        config = AdminDataConfig(base_url="https://admin.example", issuer="https://admin.example/api/auth", resource="https://dream.example/api", service_client_id="dream-service", service_secret="s" * 32)
        self._admin_schemas = [x.model_dump() for x in WORKSPACE_SCHEMA_REQUIREMENTS]
        self._admin_operations = [GET_THREAD.capability.model_dump(), GET_USER_SYSTEM_CONFIG.capability.model_dump()]
        self._admin_calls = []
        class WorkspaceVerifier(Verifier):
            def verify(self, token, *, required_scopes):
                if token.startswith("idg_"):
                    raise AdminDataError("INVALID_ACCESS_TOKEN", 401)
                return super().verify(token, required_scopes=required_scopes)
        def handler(request):
            rid = request.headers["x-request-id"]
            UUID(rid)
            self.assertEqual(request.headers["x-ink-dream-service"], config.service_client_id)
            self.assertEqual(request.headers["x-ink-dream-credential"], config.service_secret)
            if request.url.path.endswith("/capabilities"):
                value = {"version": "1", "auth": {"issuer": config.issuer, "jwks_uri": config.jwks_uri, "resource": config.resource, "algorithm": "ES256", "clients": {"browser": "dream-browser", "device": "dream-device"}, "scopes": ["dream:read", "dream:write"], "delegations": []}, "schema_capabilities": self._admin_schemas, "operations": self._admin_operations}
            else:
                self.assertEqual(request.headers["authorization"], "Bearer test-token")
                self.assertNotIn("cookie", request.headers)
                if request.url.path.endswith("/principal"):
                    value = {"subject": "opaque-ba-subject", "canonical_user_id": "1", "client_id": "dream-browser", "scopes": ["dream:read", "dream:write"], "status": "active"}
                else:
                    operation = request.url.path.rsplit("/", 1)[1]
                    body = json.loads(request.content)
                    self.assertEqual(set(body), {"request_id", "input"})
                    self.assertEqual(body["request_id"], rid)
                    self._admin_calls.append(rid)
                    if operation == "chat-thread.get":
                        self.assertEqual(set(body["input"]), {"thread_id"})
                        value = {"thread": self._thread_lookup(body["input"]["thread_id"])}
                    else:
                        self.assertEqual(operation, "user-system-config.get")
                        self.assertEqual(body["input"], {})
                        value = {"config_json": json.dumps(self._system_config, ensure_ascii=False, allow_nan=False)}
            return httpx.Response(200, json={"request_id": rid, "data": value})
        self._admin_http = httpx.Client(transport=httpx.MockTransport(handler))
        admin = AdminDataClient(config, client=self._admin_http, operations=(GET_THREAD, GET_USER_SYSTEM_CONFIG))
        self._admin_owner = AdminRequestAuth(config, client=admin, verifier=WorkspaceVerifier())
        app = FastAPI()
        app.state.admin_request_auth = self._admin_owner
        app.include_router(workspace_router.router)
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self._admin_owner.close()
        self._admin_http.close()
        os.environ.pop("AGENT_CWD", None)
        self._tmp.cleanup()

    def _thread_lookup(self, thread_id):
        return {"id": thread_id, "user_id": "1", "title": None, "deck_id": None, "voice_id": None, "created_at": None, "updated_at": None, "claude_session_id": None, "agent_contract_version": None}

    def test_admin_thread_reply_identity_and_dto_fail_before_mode_or_files(self):
        for endpoint in ["content", "download"]:
            for patch in [{"id": "other-thread"}, {"user_id": "2"}, {"title": False}, {"created_at": "private malformed time"}]:
                with self.subTest(endpoint=endpoint, patch=patch):
                    value = {**self._thread_lookup("owned-thread"), **patch}
                    with (
                        unittest.mock.patch.object(self, "_thread_lookup", return_value=value),
                        unittest.mock.patch.object(workspace_router, "get_existing_workspace") as files,
                    ):
                        response = self.client.get("/api/workspace/files/" + endpoint, params={"sessionId": "owned-thread", "path": "files/result.txt"}, headers={"Authorization": "Bearer test-token"})
                    self.assertEqual(response.status_code, 503, response.text)
                    self.assertEqual(response.json()["detail"]["code"], "WORKSPACE_AUTH_UNAVAILABLE")
                    self.assertNotIn("private", response.text)
                    files.assert_not_called()

    def test_admin_thread_timeout_does_not_retry_or_access_mode_files(self):
        for endpoint in ["content", "download"]:
            with self.subTest(endpoint=endpoint):
                before = len(self._admin_calls)
                with (
                    unittest.mock.patch.object(self, "_thread_lookup", side_effect=httpx.ReadTimeout("private token")),
                    unittest.mock.patch.object(workspace_router, "get_existing_workspace") as files,
                ):
                    response = self.client.get("/api/workspace/files/" + endpoint, params={"sessionId": "owned-thread", "path": "files/result.txt"}, headers={"Authorization": "Bearer test-token"})
                self.assertEqual(response.status_code, 503, response.text)
                self.assertEqual(response.json()["detail"]["code"], "WORKSPACE_AUTH_UNAVAILABLE")
                self.assertEqual(len(self._admin_calls), before + 1)
                files.assert_not_called()

    def test_admin_schema_and_thread_hash_are_required_before_file_access(self):
        original_schemas = [dict(x) for x in self._admin_schemas]
        for endpoint in ["content", "download"]:
            for mutation in ["missing-schema", "missing-keyset", "bad-schema", "bad-final", "duplicate-schema", "bad-operation"]:
                with self.subTest(endpoint=endpoint, mutation=mutation):
                    self._admin_schemas = [dict(x) for x in original_schemas]
                    self._admin_operations = [GET_THREAD.capability.model_dump(), GET_USER_SYSTEM_CONFIG.capability.model_dump()]
                    if mutation == "missing-schema":
                        self._admin_schemas.pop()
                    elif mutation == "missing-keyset":
                        self._admin_schemas.pop(2)
                    elif mutation == "bad-schema":
                        self._admin_schemas[0]["contract_sha256"] = "0" * 64
                    elif mutation == "bad-final":
                        self._admin_schemas[-1]["contract_sha256"] = "0" * 64
                    elif mutation == "duplicate-schema":
                        self._admin_schemas.append(dict(self._admin_schemas[0]))
                    else:
                        self._admin_operations[0]["contract_sha256"] = "0" * 64
                    before = len(self._admin_calls)
                    with (
                        unittest.mock.patch.object(workspace_router, "get_existing_workspace") as files,
                    ):
                        response = self.client.get("/api/workspace/files/" + endpoint, params={"sessionId": "owned-thread", "path": "files/result.txt"}, headers={"Authorization": "Bearer test-token"})
                    self.assertEqual(response.status_code, 503, response.text)
                    self.assertEqual(len(self._admin_calls), before)
                    files.assert_not_called()

    def test_shared_oauth_rejects_missing_expired_and_runtime_grants(self):
        for endpoint in ["content", "download"]:
            for token in [None, "expired-token", "idg_synthetic"]:
                with self.subTest(endpoint=endpoint, token=token):
                    response = self.client.get("/api/workspace/files/" + endpoint, params={"sessionId": "owned-thread", "path": "files/result.txt"}, headers={} if token is None else {"Authorization": "Bearer " + token})
                    self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(self._admin_calls, [])

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

    def test_download_public_subdir_root_returns_zip_for_file_sidebar(self):
        session_id = "download-subdir-root"
        workspace = get_or_create_workspace(session_id)
        (workspace / "files" / "root-file.txt").write_text("root export", encoding="utf-8")

        response = self.client.get(
            "/api/workspace/files/download",
            params={"sessionId": session_id, "path": "files"},
            headers={"Authorization": "Bearer test-token"},
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["content-type"], "application/zip")
        self.assertIn('filename="files.zip"', response.headers["content-disposition"])
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            self.assertEqual(
                archive.read("files/root-file.txt"),
                b"root export",
            )

    def test_download_exports_ordinary_workspace_content_outside_managed_subdirs(self):
        session_id = "download-ordinary-content"
        workspace = get_or_create_workspace(session_id)
        (workspace / "exports").mkdir()
        (workspace / "exports" / "chapter-1.md").write_text("exported chapter", encoding="utf-8")
        (workspace / "bundle-notes.txt").write_text("root-level note", encoding="utf-8")

        directory_response = self.client.get(
            "/api/workspace/files/download",
            params={"sessionId": session_id, "path": "exports"},
            headers={"Authorization": "Bearer test-token"},
        )
        root_file_response = self.client.get(
            "/api/workspace/files/download",
            params={"sessionId": session_id, "path": "bundle-notes.txt"},
            headers={"Authorization": "Bearer test-token"},
        )

        self.assertEqual(directory_response.status_code, 200, directory_response.text)
        self.assertEqual(directory_response.headers["content-type"], "application/zip")
        self.assertIn(
            'filename="exports.zip"',
            directory_response.headers["content-disposition"],
        )
        with zipfile.ZipFile(io.BytesIO(directory_response.content)) as archive:
            self.assertEqual(archive.read("exports/chapter-1.md"), b"exported chapter")
        self.assertEqual(root_file_response.status_code, 200, root_file_response.text)
        self.assertEqual(root_file_response.content, b"root-level note")

    def test_download_regular_file_rejects_in_workspace_symlink(self):
        session_id = "download-file-symlink"
        workspace = get_or_create_workspace(session_id)
        (workspace / "files" / "target.txt").write_text("target", encoding="utf-8")
        (workspace / "files" / "alias.txt").symlink_to(workspace / "files" / "target.txt")

        response = self.client.get(
            "/api/workspace/files/download",
            params={"sessionId": session_id, "path": "files/alias.txt"},
            headers={"Authorization": "Bearer test-token"},
        )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(response.json()["detail"]["code"], "SYMLINK_NOT_ALLOWED")

    def test_download_foreign_thread_is_hidden_before_workspace_probe(self):
        with (
            unittest.mock.patch.object(
                self,
                "_thread_lookup",
                return_value=None,
            ),
            unittest.mock.patch.object(
                workspace_router,
                "get_existing_workspace",
            ) as existing_workspace,
        ):
            response = self.client.get(
                "/api/workspace/files/download",
                params={"sessionId": "foreign-thread", "path": "files/export.zip"},
                headers={"Authorization": "Bearer test-token"},
            )

        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(response.json()["detail"]["code"], "WORKSPACE_NOT_FOUND")
        existing_workspace.assert_not_called()
        self.assertFalse((Path(self._tmp.name) / "foreign-thread").exists())

    def test_download_workspace_disabled_is_rejected_before_workspace_probe(self):
        with (
            unittest.mock.patch.object(
                self,
                "_system_config",
                {"workspace_enabled": False},
            ),
            unittest.mock.patch.object(
                workspace_router,
                "get_existing_workspace",
            ) as existing_workspace,
        ):
            response = self.client.get(
                "/api/workspace/files/download",
                params={"sessionId": "disabled-thread", "path": "files/export.zip"},
                headers={"Authorization": "Bearer test-token"},
            )

        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["detail"]["code"], "WORKSPACE_DISABLED")
        existing_workspace.assert_not_called()

    def test_download_missing_workspace_does_not_create_one(self):
        session_id = "download-missing-workspace"
        response = self.client.get(
            "/api/workspace/files/download",
            params={"sessionId": session_id, "path": "files/report.pdf"},
            headers={"Authorization": "Bearer test-token"},
        )

        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(response.json()["detail"]["code"], "WORKSPACE_NOT_FOUND")
        self.assertFalse((Path(self._tmp.name) / session_id).exists())

    def test_download_rejects_ambiguous_and_dot_runtime_paths_without_workspace_probe(self):
        invalid_paths = (
            "../secret.zip",
            "files/../secret.zip",
            "files/../.dream/state.json",
            "/files/secret.zip",
            "files\\secret.zip",
            "files//secret.zip",
            "files/./secret.zip",
            "files/",
            "files/%2e%2e/secret.zip",
            "files/export.zip?download=1",
            "files/export.zip#fragment",
            ".dream/state.json",
            ".dream",
            ".claude/settings.json",
            ".claude",
            ".editor/index.json",
            ".notion-home/credentials.json",
            "C:/secret.zip",
        )
        with unittest.mock.patch.object(
            workspace_router,
            "get_existing_workspace",
        ) as existing_workspace:
            for path in invalid_paths:
                with self.subTest(path=path):
                    response = self.client.get(
                        "/api/workspace/files/download",
                        params={"sessionId": "download-paths", "path": path},
                        headers={"Authorization": "Bearer test-token"},
                    )
                    self.assertEqual(response.status_code, 400, response.text)
                    self.assertEqual(
                        response.json()["detail"]["code"],
                        "INVALID_WORKSPACE_URI",
                    )
        existing_workspace.assert_not_called()

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
                self,
                "_thread_lookup",
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
                self,
                "_system_config",
                {"workspace_enabled": False},
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
            self,
            "_system_config",
            {
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
            self,
            "_system_config",
            {
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
