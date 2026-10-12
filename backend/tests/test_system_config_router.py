# [Sync] 2026-10-10: separate saved AI/Image ownership; Responses images stay disabled pending a complete bridge.
# [Input] Consume the Settings router with an explicit Admin actor and typed SystemConfig adapter.
# [Output] Verify sanitized Admin patches and fresh read response behavior without Dream database access.
# [Pos] test node in backend/tests
# [Sync] 2026-06-25: cover PUT /api/system-config returning merged sandbox
#                    network config so frontend Settings can hydrate after save.
# [Sync] 2026-07-26: cover sandbox_fs_allowed_write_paths sanitizer (absolute-
#                    only, trailing-slash strip, dedupe, caps) via PUT.
# [Sync] 2026-08-30: reject the deployment-owned sandbox enablement key from
#                    user env_vars and redact legacy stored copies.
# [Sync] 2026-09-15: replace database mocks with the production Admin DTO invocation boundary.

"""Regression tests for the system-config router."""
from __future__ import annotations

import sys
import unittest
import unittest.mock
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]  # backend/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from routers import system_config as system_config_router
from services.admin_data.request_auth import AdminRequestActor


class _SystemConfigData:
    def __init__(self, config: dict):
        self.config = config
        self.calls: list[tuple[str, dict]] = []

    def get_user(self, input_dto, _request_id, *, access_token):
        assert access_token == "settings-token"
        self.calls.append(("get", input_dto.model_dump(mode="json")))
        return dict(self.config)

    def patch_user(self, input_dto, _request_id, *, access_token):
        assert access_token == "settings-token"
        patch = input_dto.model_dump(mode="json")
        self.calls.append(("patch", patch))
        self.config.update(patch)
        return SimpleNamespace(success=True)

    def patch_image_model(self, input_dto, _request_id, *, access_token):
        assert access_token == 'settings-token'
        patch = input_dto.model_dump(mode='json')
        self.calls.append(('patch-image', patch))
        self.config.update(patch)
        return SimpleNamespace(success=True)


class _AdminRouterHarness:
    def _start_admin_harness(self):
        self.saved_config: dict = {}
        self.admin_data = _SystemConfigData(self.saved_config)
        self.admin_owner = SimpleNamespace(client=object())
        actor = AdminRequestActor("subject", "7", "browser", frozenset({"dream:read", "dream:write"}), 1, 2, "settings-token")
        app = FastAPI()
        app.dependency_overrides[system_config_router.get_current_user] = lambda: {
            "user_id": 7,
            "email": "settings@example.com",
            "_admin_actor": actor,
        }
        app.dependency_overrides[system_config_router.get_admin_request_auth] = lambda: self.admin_owner
        self._data_patch = unittest.mock.patch.object(
            system_config_router,
            "AdminSystemConfigData",
            return_value=self.admin_data,
        )
        self._data_patch.start()
        app.include_router(system_config_router.router)
        self.client = TestClient(app)

    def _stop_admin_harness(self):
        self.client.close()
        self._data_patch.stop()


class TestSystemConfigRouter(_AdminRouterHarness, unittest.TestCase):
    def setUp(self):
        self._start_admin_harness()

    def tearDown(self):
        self._stop_admin_harness()

    def test_put_returns_merged_sanitized_sandbox_network_config(self):
        self.saved_config["workspace_enabled"] = True
        response = self.client.put(
            "/api/system-config",
            json={
                "sandbox_network_mode": "allowlist",
                "sandbox_network_allowed_domains": [
                    "HTTPS://Raw.GitHubUserContent.com/path/file.txt",
                    "*.githubusercontent.com",
                    "githubusercontent.com",
                    "*",
                    "raw.githubusercontent.com",
                ],
            },
        )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(
            payload["data"],
            {
                "workspace_enabled": True,
                "sandbox_network_mode": "allowlist",
                "sandbox_network_allowed_domains": [
                    "raw.githubusercontent.com",
                    "*.githubusercontent.com",
                    "githubusercontent.com",
                ],
            },
        )

    def test_put_rejects_secret_and_provider_routing_env_vars(self):
        response = self.client.put(
            "/api/system-config",
            json={
                "env_vars": {
                    "ANTHROPIC_AUTH_TOKEN": "must-not-be-stored",
                    "ANTHROPIC_BASE_URL": "https://bypass.example",
                    "INK_AGENT_SANDBOX_ENABLED": "false",
                }
            },
        )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(self.admin_data.calls, [])

    def test_get_drops_legacy_secret_values(self):
        self.saved_config.update({
            "theme": "dark",
            "env_vars": {
                "ANTHROPIC_AUTH_TOKEN": "legacy-secret",
                "ANTHROPIC_BASE_URL": "https://legacy.example",
                "INK_AGENT_SANDBOX_ENABLED": "false",
                "CLAUDE_CODE_TMPDIR": "/private/tmp/private",
                "API_TIMEOUT_MS": "120000",
            },
        })
        response = self.client.get("/api/system-config")

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json(),
            {"theme": "dark", "env_vars": {"API_TIMEOUT_MS": "120000"}},
        )

    def test_put_model_accepts_only_admin_gateway_catalog_alias(self):
        from services.admin_gateway.models import GatewayModel, GatewayModelCatalog

        model = GatewayModel(
            model_alias="dream-balanced",
            display_name="Dream Balanced",
            protocol="anthropic",
            capabilities={"tools": True},
            context_window=200000,
            max_output_tokens=8192,
            enabled=True,
            callable=True,
            availability="included",
            required_plan_code="free",
            upgrade_hint=None,
        )
        catalog = unittest.mock.MagicMock()
        catalog.fetch_catalog.return_value = GatewayModelCatalog((model,), "dream-balanced")
        with (
            unittest.mock.patch.object(
                system_config_router,
                "GatewayModelCatalogClient",
                return_value=catalog,
            ),
        ):
            response = self.client.put(
                "/api/system-config",
                json={"model": "dream-balanced"},
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.saved_config, {"model": "dream-balanced", "provider": "gateway"})
        self.assertEqual([name for name, _ in self.admin_data.calls], ["patch", "get"])

    def test_put_model_rejects_alias_not_returned_by_gateway(self):
        from services.admin_gateway.models import GatewayModelCatalog

        catalog = unittest.mock.MagicMock()
        catalog.fetch_catalog.return_value = GatewayModelCatalog((), None)
        with (
            unittest.mock.patch.object(
                system_config_router,
                "GatewayModelCatalogClient",
                return_value=catalog,
            ),
        ):
            response = self.client.put(
                "/api/system-config",
                json={"model": "provider-upstream-name"},
            )

        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.admin_data.calls, [])

    def test_put_model_rejects_visible_but_uncallable_alias(self):
        from services.admin_gateway.models import GatewayModel, GatewayModelCatalog

        model = GatewayModel(
            model_alias="dream-premium",
            display_name="Dream Premium",
            protocol="anthropic",
            capabilities={"tools": True},
            context_window=200000,
            max_output_tokens=8192,
            enabled=True,
            callable=False,
            availability="upgrade_required",
            required_plan_code="dream",
            upgrade_hint="升级 Dream 后可用",
        )
        catalog = unittest.mock.MagicMock()
        catalog.fetch_catalog.return_value = GatewayModelCatalog((model,), None)
        with (
            unittest.mock.patch.object(system_config_router, "GatewayModelCatalogClient", return_value=catalog),
        ):
            response = self.client.put("/api/system-config", json={"model": "dream-premium"})

        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(response.json()["detail"]["requiredPlanCode"], "dream")
        self.assertEqual(self.admin_data.calls, [])


class TestIndependentImageConfig(_AdminRouterHarness, unittest.TestCase):
    def setUp(self):
        self._start_admin_harness()

    def tearDown(self):
        self._stop_admin_harness()

    def catalog(self, *, callable=True, images=True):
        from services.admin_gateway.models import GatewayModel, GatewayModelCatalog
        entry = GatewayModel(model_alias='image-a', display_name='Image A', protocol='openai',
            capabilities={'chat': False}, context_window=None, max_output_tokens=None,
            enabled=True, callable=False, availability='included', required_plan_code=None,
            upgrade_hint=None, image_generation=images, image_edit=images,
            image_callable=callable, image_configured=True, image_entitled=callable)
        return unittest.mock.MagicMock(fetch_catalog=unittest.mock.MagicMock(return_value=GatewayModelCatalog((entry,), None)))

    def test_save_and_refresh_keeps_ai_selection(self):
        self.saved_config.update(model='chat-a', provider='gateway', unknown={'kept': True})
        with unittest.mock.patch.object(system_config_router, 'GatewayModelCatalogClient', return_value=self.catalog()):
            response = self.client.put('/api/system-config', json={'image_model': 'image-a'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['data'], self.saved_config)
        self.assertEqual(self.saved_config['model'], 'chat-a')
        self.assertEqual(self.saved_config['image_model'], 'image-a')
        self.assertEqual([call[0] for call in self.admin_data.calls], ['patch-image', 'get'])
        self.assertEqual(self.client.get('/api/system-config').json()['image_model'], 'image-a')

    def test_unavailable_or_nonimage_selection_never_writes(self):
        for callable, images, status in [(False, True, 403), (True, False, 409)]:
            with unittest.mock.patch.object(system_config_router, 'GatewayModelCatalogClient', return_value=self.catalog(callable=callable, images=images)):
                response = self.client.put('/api/system-config', json={'image_model': 'image-a'})
            self.assertEqual(response.status_code, status, response.text)
            self.assertEqual(self.admin_data.calls, [])

    def test_image_form_without_chat_flag_cannot_be_saved_as_ai(self):
        catalog = self.catalog()
        from dataclasses import replace
        entry = catalog.fetch_catalog.return_value.models[0]
        from services.admin_gateway.models import GatewayModelCatalog
        catalog.fetch_catalog.return_value = GatewayModelCatalog((replace(entry, callable=True, capabilities={'image_generation': True, 'image_edit': True}),), None)
        with unittest.mock.patch.object(system_config_router, 'GatewayModelCatalogClient', return_value=catalog):
            response = self.client.put('/api/system-config', json={'model': 'image-a'})
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.admin_data.calls, [])

    def test_mixed_and_invalid_image_patches_never_fetch_catalog_or_write(self):
        with unittest.mock.patch.object(system_config_router, 'GatewayModelCatalogClient') as catalog:
            for patch in [{'image_model': 'image-a', 'model': 'chat-a'}, {'image_model': None}, {'image_model': ' image-a'}]:
                self.assertEqual(self.client.put('/api/system-config', json=patch).status_code, 422)
            catalog.assert_not_called()
        self.assertEqual(self.admin_data.calls, [])


class TestSandboxFsAllowedWritePathsSanitizer(unittest.TestCase):
    """_sanitize_sandbox_fs_allowed_write_paths contract."""

    def _sanitize(self, raw):
        return system_config_router._sanitize_sandbox_fs_allowed_write_paths(raw)

    def test_accepts_absolute_paths_only(self):
        self.assertEqual(
            self._sanitize(["/data/out", "relative/path", "", "  ", "~/x", "data"]),
            ["/data/out"],
        )

    def test_strips_trailing_slashes_except_root(self):
        self.assertEqual(
            self._sanitize(["/data/out/", "/", "//"]),
            ["/data/out", "/"],
        )

    def test_dedupes_preserving_order(self):
        self.assertEqual(
            self._sanitize(["/b", "/a", "/b/", "/a", "/c"]),
            ["/b", "/a", "/c"],
        )

    def test_accepts_separated_string_input(self):
        self.assertEqual(
            self._sanitize("/data/out\n/data/cache, relative/bad;/data/logs"),
            ["/data/out", "/data/cache", "/data/logs"],
        )

    def test_rejects_non_list_non_string_input(self):
        self.assertEqual(self._sanitize(None), [])
        self.assertEqual(self._sanitize(42), [])
        self.assertEqual(self._sanitize({"path": "/x"}), [])

    def test_rejects_non_string_entries_silently(self):
        self.assertEqual(
            self._sanitize(["/ok", None, 123, ["nested"], "/ok2"]),
            ["/ok", "/ok2"],
        )

    def test_caps_entry_count(self):
        limit = system_config_router._SANDBOX_FS_ALLOWED_WRITE_PATH_MAX_ENTRIES
        result = self._sanitize([f"/p{i}" for i in range(limit + 10)])
        self.assertEqual(len(result), limit)
        self.assertEqual(result[0], "/p0")

    def test_caps_path_length(self):
        limit = system_config_router._SANDBOX_FS_ALLOWED_WRITE_PATH_MAX_LEN
        result = self._sanitize(["/" + "a" * (limit + 50)])
        self.assertEqual(result, [("/" + "a" * (limit + 50))[:limit]])


class TestSandboxFsAllowedWritePathsPut(_AdminRouterHarness, unittest.TestCase):
    """PUT /api/system-config wires the fs write paths key like the domains key."""

    def setUp(self):
        self._start_admin_harness()

    def tearDown(self):
        self._stop_admin_harness()

    def test_put_returns_merged_sanitized_fs_write_paths(self):
        self.saved_config["workspace_enabled"] = True
        response = self.client.put(
            "/api/system-config",
            json={
                "sandbox_fs_allowed_write_paths": [
                    "/data/out/",
                    "relative/bad",
                    "/data/out",
                    "/var/cache",
                ],
            },
        )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(
            payload["data"],
            {
                "workspace_enabled": True,
                "sandbox_fs_allowed_write_paths": ["/data/out", "/var/cache"],
            },
        )


if __name__ == "__main__":
    unittest.main()
