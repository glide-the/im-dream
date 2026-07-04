# [Input] Consume backend/routers/system_config.py FastAPI router.
# [Output] Verify Settings system-config save responses include sanitized data.
# [Pos] test node in backend/tests
# [Sync] 2026-06-25: cover PUT /api/system-config returning merged sandbox
#                    network config so frontend Settings can hydrate after save.

"""Regression tests for the system-config router."""
from __future__ import annotations

import sys
import unittest
import unittest.mock
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]  # backend/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from routers import system_config as system_config_router


class TestSystemConfigRouter(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.dependency_overrides[system_config_router.get_current_user] = (
            lambda: {"user_id": 7, "email": "settings@example.com"}
        )
        app.include_router(system_config_router.router)
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()

    def test_put_returns_merged_sanitized_sandbox_network_config(self):
        saved_patch: dict = {}

        def save_config(user_id: int, patch: dict) -> None:
            self.assertEqual(user_id, 7)
            saved_patch.update(patch)

        def get_config(user_id: int) -> dict:
            self.assertEqual(user_id, 7)
            return {"workspace_enabled": True, **saved_patch}

        with (
            unittest.mock.patch.object(
                system_config_router.database,
                "save_system_config",
                side_effect=save_config,
            ),
            unittest.mock.patch.object(
                system_config_router.database,
                "get_system_config",
                side_effect=get_config,
            ),
        ):
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


if __name__ == "__main__":
    unittest.main()
