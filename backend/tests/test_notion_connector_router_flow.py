# [Input] Notion connector router and facade wiring for the business flow.
# [Output] Exercise create → auth → resources → sync through the real router,
#          PostgreSQL repository, pure transactional fake, and mocked CLI.
# [Pos] test node in backend/tests
# [Sync] 2026-07-04: route-level business flow coverage for Notion connector
#                    create/auth/discovery/selection/sync.
# [Sync] 2026-07-08: assert selected sources hydrate through connector responses so
#                    Settings refresh and Chat linked-resource summaries stay in sync.
# [Sync] 2026-08-28: drive auth through actor-owned agentdata homes and prove
#                    browser notion_home input is ignored rather than persisted.
# [Sync] 2026-08-28: assert successful selection advances last_synced_at instead
#                    of leaving the connector in an authenticated empty-snapshot state.
# [Sync] 2026-08-28: assert selection publishes an actor agentdata snapshot, ignores
#                    thread workspace identity, and exposes a versioned scheduled-sync policy.
# [Sync] 2026-08-28: model index-only snapshots and exact pending-to-synced resource publication.
# [Sync] 2026-08-29: cover fail-closed source clearing and failed reauthorization
#                    that preserves only a previously effective actor credential.

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
TEST_ROOT = Path(__file__).resolve().parent
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from notion import auth as notion_auth
from notion import operations as notion_operations
from notion import store as notion_store
from notion import sync as notion_sync
from notion.errors import NotionPermissionError
from notion.credentials import NotionCredentialStore
from notion_postgres_fake import build_fake_notion_store
from routers import notion as notion_router


class TestNotionConnectorRouterFlow(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._store, self._database, self._pool = build_fake_notion_store(users={7})
        notion_store.close_default_store()
        notion_store.open_default_store(store=self._store)
        self._credential_runtime_root = Path(self._tmp.name) / "agentdata" / "notion-runtime"
        self._env_patcher = patch.dict(
            os.environ,
            {"INK_NOTION_RUNTIME_ROOT": str(self._credential_runtime_root)},
            clear=False,
        )
        self._env_patcher.start()
        self._notion_home = str(Path(self._tmp.name) / "browser-controlled-home")
        self._workspace_id = "workspace-business"
        self._snapshot_version = "snap-business-001"
        self._source_revision = "rev-business-001"
        self._sync_cursor = "cursor-business-001"
        self._patches = [
            patch.object(
                notion_auth,
                "start_login",
                new=AsyncMock(side_effect=self._mock_start_login),
            ),
            patch.object(
                notion_auth,
                "poll_login",
                new=AsyncMock(side_effect=self._mock_poll_login),
            ),
            patch.object(
                notion_operations,
                "discover_databases",
                new=AsyncMock(side_effect=self._mock_discover_databases),
            ),
            patch.object(
                notion_operations,
                "discover_pages",
                new=AsyncMock(side_effect=self._mock_discover_pages),
            ),
            patch.object(
                notion_sync,
                "build_canonical_snapshot",
                new=AsyncMock(side_effect=self._mock_build_snapshot),
            ),
        ]
        for patcher in self._patches:
            patcher.start()

        app = FastAPI()
        app.dependency_overrides[notion_router.get_current_user] = (
            lambda: {"user_id": 7, "email": "board@example.com"}
        )
        app.include_router(notion_router.router)
        self.client = TestClient(app)
        self.snapshot_calls: list[dict[str, object]] = []

    def tearDown(self):
        self.client.close()
        for patcher in reversed(self._patches):
            patcher.stop()
        notion_store.close_default_store()
        self._env_patcher.stop()
        self._tmp.cleanup()

    def _mock_start_login(self, notion_home):
        notion_home = Path(notion_home)
        self.assertTrue(
            notion_home.is_relative_to(self._credential_runtime_root.resolve(strict=False))
        )
        (notion_home / "auth.json").write_text(
            '{"access_token":"router-flow-secret"}\n',
            encoding="utf-8",
        )
        return notion_auth.LoginInitResult(
            verification_url="https://www.notion.so/workers/cli-login?verificationCode=VAF-HWY",
            verification_code="VAF-HWY",
            poll_interval_seconds=5,
        )

    def _mock_poll_login(self, notion_home):
        self.assertTrue(
            Path(notion_home).is_relative_to(
                self._credential_runtime_root.resolve(strict=False)
            )
        )
        return notion_auth.AuthStatusResult(
            status="authenticated",
            detail="Notion is connected.",
        )

    def _mock_discover_databases(self, notion_home, query=None, page_size=100):
        self.assertTrue(
            Path(notion_home).is_relative_to(
                self._credential_runtime_root.resolve(strict=False)
            )
        )
        del query, page_size
        return [
            {
                "database_id": "db-team",
                "title": "Team Knowledge",
                "url": "https://www.notion.so/db-team",
                "page_count": 2,
                "properties_schema": {"Name": {"type": "title"}},
                "last_edited": "2026-07-04T13:30:00Z",
            }
        ]

    def _mock_discover_pages(self, notion_home, query=None, page_size=100):
        self.assertTrue(
            Path(notion_home).is_relative_to(
                self._credential_runtime_root.resolve(strict=False)
            )
        )
        del query, page_size
        return [
            {
                "page_id": "page-team",
                "title": "Team Notes",
                "url": "https://www.notion.so/page-team",
                "last_edited": "2026-07-04T13:30:00Z",
            }
        ]

    def _mock_build_snapshot(self, connector, selected_resources, workspace_id, operations):
        del operations
        selected_database_ids = [
            str(resource.get("external_id") or "")
            for resource in selected_resources
            if resource.get("resource_type") == "notion_database"
        ]
        selected_page_ids = [
            str(resource.get("external_id") or "")
            for resource in selected_resources
            if resource.get("resource_type") == "notion_page"
        ]
        self.snapshot_calls.append(
            {
                "connector_id": connector["id"],
                "workspace_id": workspace_id,
                "database_ids": selected_database_ids,
                "page_ids": selected_page_ids,
            }
        )
        return {
            "metadata": {
                "workspace_id": workspace_id,
                "resource_connector_id": str(connector["id"]),
                "snapshot_version": self._snapshot_version,
                "source_revision": self._source_revision,
                "sync_cursor": self._sync_cursor,
                "fetched_at": "2026-07-04T13:30:00Z",
                "state": "snapshot_ready",
            },
            "connector": {
                "id": connector["id"],
                "platform": "notion",
                "auth_status": "authenticated",
                "selected_databases": selected_database_ids,
                "selected_pages": selected_page_ids,
            },
            "index": [
                {
                    "page_id": "page-team",
                    "title": "Team Notes",
                    "url": "https://www.notion.so/page-team",
                    "last_edited": "2026-07-04T13:30:00Z",
                }
            ],
            "databases": [
                {
                    "database_id": "db-team",
                    "title": "Team Knowledge",
                    "page_count": 2,
                    "properties_schema": {"Name": {"type": "title"}},
                    "last_edited": "2026-07-04T13:30:00Z",
                    "url": "https://www.notion.so/db-team",
                }
            ],
            "database_pages": {
                "db-team": [
                    {
                        "page_id": "page-team",
                        "title": "Team Notes",
                        "last_edited": "2026-07-04T13:30:00Z",
                    }
                ]
            },
            "pages": {},
            "identity": {
                "workspace_id": workspace_id,
                "resource_connector_id": str(connector["id"]),
                "snapshot_version": self._snapshot_version,
                "source_revision": self._source_revision,
                "sync_cursor": self._sync_cursor,
            },
        }

    def test_connector_router_happy_path(self):
        create_response = self.client.post(
            "/api/connectors",
            json={
                "name": "Notion Resource Connector",
                "platform": "notion",
                "notion_home": self._notion_home,
            },
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(create_response.status_code, 200, create_response.text)
        connector = create_response.json()["connector"]
        connector_id = connector["id"]
        self.assertEqual(connector["auth_status"], "pending")
        self.assertNotIn("notion_home", connector["config"])

        login_response = self.client.post(
            f"/api/connectors/{connector_id}/auth/login",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(login_response.status_code, 200, login_response.text)
        login_payload = login_response.json()
        self.assertEqual(login_payload["verificationCode"], "VAF-HWY")
        self.assertEqual(login_payload["connector"]["auth_status"], "pending")

        poll_response = self.client.post(
            f"/api/connectors/{connector_id}/auth/poll",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(poll_response.status_code, 200, poll_response.text)
        poll_payload = poll_response.json()
        self.assertEqual(poll_payload["status"], "authenticated")
        self.assertEqual(poll_payload["connector"]["auth_status"], "authenticated")

        databases_response = self.client.get(
            f"/api/connectors/{connector_id}/databases",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(databases_response.status_code, 200, databases_response.text)
        databases = databases_response.json()["databases"]
        self.assertEqual(databases[0]["database_id"], "db-team")
        self.assertFalse(databases[0]["selected"])

        pages_response = self.client.get(
            f"/api/connectors/{connector_id}/pages",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(pages_response.status_code, 200, pages_response.text)
        pages = pages_response.json()["pages"]
        self.assertEqual(pages[0]["page_id"], "page-team")
        self.assertFalse(pages[0]["selected"])

        select_response = self.client.post(
            f"/api/connectors/{connector_id}/resources/select",
            json={
                "selected_databases": [databases[0]],
                "selected_pages": [pages[0]],
                "workspace_id": self._workspace_id,
            },
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(select_response.status_code, 200, select_response.text)
        select_payload = select_response.json()
        self.assertTrue(select_payload["synced"])
        self.assertEqual(select_payload["databaseCount"], 1)
        self.assertEqual(select_payload["pageCount"], 1)
        self.assertEqual(select_payload["snapshotIdentity"]["workspace_id"], connector_id)
        self.assertEqual(select_payload["snapshotIdentity"]["snapshot_version"], self._snapshot_version)
        actor_snapshot = (
            NotionCredentialStore().user_paths(7).snapshot_root
            / connector_id
            / "current.json"
        )
        self.assertTrue(actor_snapshot.is_file())
        self.assertNotIn(self._workspace_id, str(actor_snapshot))

        selected_resources_response = self.client.get(
            f"/api/connectors/{connector_id}/resources",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(selected_resources_response.status_code, 200, selected_resources_response.text)
        selected_resources = selected_resources_response.json()["resources"]
        self.assertEqual(len(selected_resources), 2)
        self.assertEqual(
            {resource["resource_type"] for resource in selected_resources},
            {"notion_database", "notion_page"},
        )
        self.assertTrue(
            all(resource["sync_status"] == "synced" for resource in selected_resources)
        )

        databases_again_response = self.client.get(
            f"/api/connectors/{connector_id}/databases",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(databases_again_response.status_code, 200, databases_again_response.text)
        self.assertTrue(databases_again_response.json()["databases"][0]["selected"])

        pages_again_response = self.client.get(
            f"/api/connectors/{connector_id}/pages",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(pages_again_response.status_code, 200, pages_again_response.text)
        self.assertTrue(pages_again_response.json()["pages"][0]["selected"])

        sync_response = self.client.post(
            f"/api/connectors/{connector_id}/sync",
            json={"workspace_id": self._workspace_id},
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(sync_response.status_code, 200, sync_response.text)
        sync_payload = sync_response.json()
        self.assertTrue(sync_payload["synced"])
        self.assertEqual(sync_payload["databaseCount"], 1)
        self.assertEqual(sync_payload["pageCount"], 1)

        final_connector_response = self.client.get(
            f"/api/connectors/{connector_id}",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(final_connector_response.status_code, 200, final_connector_response.text)
        final_connector = final_connector_response.json()["connector"]
        self.assertEqual(final_connector["current_snapshot_version"], self._snapshot_version)
        self.assertEqual(final_connector["current_source_revision"], self._source_revision)
        self.assertIsNotNone(final_connector["last_synced_at"])
        self.assertEqual(final_connector["selected_databases"], ["db-team"])
        self.assertEqual(final_connector["selected_pages"], ["page-team"])
        self.assertEqual(
            {source["external_id"] for source in final_connector["sources"]},
            {"db-team", "page-team"},
        )
        self.assertEqual(final_connector["sync_policy"]["status"], "applied")
        self.assertTrue(final_connector["sync_policy"]["effective"]["enabled"])
        policy_response = self.client.put(
            f"/api/connectors/{connector_id}/sync-policy",
            json={"enabled": False, "interval_minutes": 60},
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(policy_response.status_code, 200, policy_response.text)
        updated_policy = policy_response.json()["connector"]["sync_policy"]
        self.assertFalse(updated_policy["effective"]["enabled"])
        self.assertEqual(updated_policy["desired"], updated_policy["effective"])
        self.assertEqual(updated_policy["status"], "disabled")
        self.assertEqual(len(self.snapshot_calls), 2)

    def test_connector_auth_poll_no_pending_session_does_not_regress_auth(self):
        create_response = self.client.post(
            "/api/connectors",
            json={
                "name": "Notion Resource Connector",
                "platform": "notion",
                "notion_home": self._notion_home,
            },
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(create_response.status_code, 200, create_response.text)
        connector_id = create_response.json()["connector"]["id"]

        login_response = self.client.post(
            f"/api/connectors/{connector_id}/auth/login",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(login_response.status_code, 200, login_response.text)

        polling_sequence = [
            notion_auth.AuthStatusResult(
                status="authenticated",
                detail="Notion is connected.",
            ),
            notion_auth.AuthStatusResult(
                status="consumed",
                detail="Notion authorization is no longer active. Start authorization again.",
            ),
        ]
        with patch.object(
            notion_auth,
            "poll_login",
            new=AsyncMock(side_effect=polling_sequence),
        ):
            first_poll = self.client.post(
                f"/api/connectors/{connector_id}/auth/poll",
                headers={"Authorization": "Bearer test-token"},
            )
            self.assertEqual(first_poll.status_code, 200, first_poll.text)
            first_payload = first_poll.json()
            self.assertEqual(first_payload["status"], "authenticated")
            self.assertEqual(first_payload["auth_status"], "authenticated")

            second_poll = self.client.post(
                f"/api/connectors/{connector_id}/auth/poll",
                headers={"Authorization": "Bearer test-token"},
            )
            self.assertEqual(second_poll.status_code, 200, second_poll.text)
            second_payload = second_poll.json()
            self.assertEqual(second_payload["status"], "authenticated")
            self.assertEqual(second_payload["auth_status"], "authenticated")

        final_connector = self.client.get(
            f"/api/connectors/{connector_id}",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(final_connector.status_code, 200, final_connector.text)
        final_payload = final_connector.json()["connector"]
        self.assertEqual(final_payload["auth_status"], "authenticated")
        self.assertEqual(final_payload["config"].get("auth_session", {}).get("auth_session_status"), "authenticated")

    def test_connector_auth_poll_no_pending_session_without_auth_marks_error(self):
        create_response = self.client.post(
            "/api/connectors",
            json={
                "name": "Notion Resource Connector",
                "platform": "notion",
                "notion_home": self._notion_home,
            },
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(create_response.status_code, 200, create_response.text)
        connector_id = create_response.json()["connector"]["id"]

        login_response = self.client.post(
            f"/api/connectors/{connector_id}/auth/login",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(login_response.status_code, 200, login_response.text)

        with patch.object(
            notion_auth,
            "poll_login",
            new=AsyncMock(
                return_value=notion_auth.AuthStatusResult(
                    status="consumed",
                    detail="Notion authorization is no longer active. Start authorization again.",
                )
            ),
        ):
            poll_response = self.client.post(
                f"/api/connectors/{connector_id}/auth/poll",
                headers={"Authorization": "Bearer test-token"},
            )
            self.assertEqual(poll_response.status_code, 200, poll_response.text)
            poll_payload = poll_response.json()
            self.assertEqual(poll_payload["status"], "error")
            self.assertEqual(poll_payload["auth_status"], "error")

        final_connector = self.client.get(
            f"/api/connectors/{connector_id}",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(final_connector.status_code, 200, final_connector.text)
        final_payload = final_connector.json()["connector"]
        self.assertEqual(final_payload["auth_status"], "error")
        self.assertEqual(
            final_payload.get("config", {})
            .get("auth_session", {})
            .get("auth_session_status"),
            "consumed",
        )

    def test_failed_reauthorization_preserves_effective_credentials(self):
        create_response = self.client.post(
            "/api/connectors",
            json={"name": "Notion", "platform": "notion"},
            headers={"Authorization": "Bearer test-token"},
        )
        connector_id = create_response.json()["connector"]["id"]
        self.client.post(
            f"/api/connectors/{connector_id}/auth/login",
            headers={"Authorization": "Bearer test-token"},
        )
        first_poll = self.client.post(
            f"/api/connectors/{connector_id}/auth/poll",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(first_poll.json()["auth_status"], "authenticated")

        self.client.post(
            f"/api/connectors/{connector_id}/auth/login",
            headers={"Authorization": "Bearer test-token"},
        )
        with patch.object(
            notion_auth,
            "poll_login",
            new=AsyncMock(
                return_value=notion_auth.AuthStatusResult(
                    status="expired",
                    detail="The new authorization attempt expired.",
                )
            ),
        ):
            failed_poll = self.client.post(
                f"/api/connectors/{connector_id}/auth/poll",
                headers={"Authorization": "Bearer test-token"},
            )

        self.assertEqual(failed_poll.status_code, 200, failed_poll.text)
        self.assertEqual(failed_poll.json()["status"], "expired")
        self.assertEqual(failed_poll.json()["auth_status"], "authenticated")
        final_connector = self.client.get(
            f"/api/connectors/{connector_id}",
            headers={"Authorization": "Bearer test-token"},
        ).json()["connector"]
        self.assertEqual(final_connector["auth_status"], "authenticated")
        self.assertEqual(
            final_connector["config"]["auth_session"]["auth_session_status"],
            "expired",
        )
        self.assertTrue(NotionCredentialStore().has_credentials(7))

    def test_failed_reauthorization_does_not_revive_expired_credentials(self):
        create_response = self.client.post(
            "/api/connectors",
            json={"name": "Notion", "platform": "notion"},
            headers={"Authorization": "Bearer test-token"},
        )
        connector_id = create_response.json()["connector"]["id"]
        self.client.post(
            f"/api/connectors/{connector_id}/auth/login",
            headers={"Authorization": "Bearer test-token"},
        )
        first_poll = self.client.post(
            f"/api/connectors/{connector_id}/auth/poll",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(first_poll.json()["auth_status"], "authenticated")

        notion_store.update_connector(
            connector_id,
            7,
            {"auth_status": "expired"},
        )
        self.client.post(
            f"/api/connectors/{connector_id}/auth/login",
            headers={"Authorization": "Bearer test-token"},
        )
        with patch.object(
            notion_auth,
            "poll_login",
            new=AsyncMock(
                return_value=notion_auth.AuthStatusResult(
                    status="expired",
                    detail="The replacement authorization attempt expired.",
                )
            ),
        ):
            failed_poll = self.client.post(
                f"/api/connectors/{connector_id}/auth/poll",
                headers={"Authorization": "Bearer test-token"},
            )

        self.assertEqual(failed_poll.status_code, 200, failed_poll.text)
        self.assertEqual(failed_poll.json()["status"], "expired")
        self.assertEqual(failed_poll.json()["auth_status"], "expired")
        self.assertTrue(NotionCredentialStore().has_credentials(7))

    def test_empty_selection_clears_current_index_without_disconnect(self):
        create_response = self.client.post(
            "/api/connectors",
            json={"name": "Notion", "platform": "notion"},
            headers={"Authorization": "Bearer test-token"},
        )
        connector_id = create_response.json()["connector"]["id"]
        self.client.post(
            f"/api/connectors/{connector_id}/auth/login",
            headers={"Authorization": "Bearer test-token"},
        )
        self.client.post(
            f"/api/connectors/{connector_id}/auth/poll",
            headers={"Authorization": "Bearer test-token"},
        )
        selected = self.client.post(
            f"/api/connectors/{connector_id}/resources/select",
            json={
                "selected_databases": [
                    {"database_id": "db-team", "title": "Team Knowledge"}
                ],
                "selected_pages": [],
            },
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(selected.status_code, 200, selected.text)
        self.assertTrue(selected.json()["synced"])

        cleared = self.client.post(
            f"/api/connectors/{connector_id}/resources/select",
            json={"selected_databases": [], "selected_pages": []},
            headers={"Authorization": "Bearer test-token"},
        )

        self.assertEqual(cleared.status_code, 200, cleared.text)
        payload = cleared.json()
        self.assertFalse(payload["synced"])
        self.assertIsNone(payload["snapshotIdentity"])
        self.assertEqual(payload["connector"]["auth_status"], "authenticated")
        self.assertEqual(payload["connector"]["sources"], [])
        self.assertIsNone(payload["connector"]["current_snapshot_version"])
        self.assertIsNone(payload["connector"]["last_synced_at"])
        self.assertFalse(
            (
                NotionCredentialStore().user_paths(7).snapshot_root
                / connector_id
                / "current.json"
            ).exists()
        )

    def test_unauthorized_connector_cannot_discover_notion(self):
        create_response = self.client.post(
            "/api/connectors",
            json={"name": "Notion", "platform": "notion"},
            headers={"Authorization": "Bearer test-token"},
        )
        connector_id = create_response.json()["connector"]["id"]

        response = self.client.get(
            f"/api/connectors/{connector_id}/databases",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(response.status_code, 401, response.text)
        self.assertIn("Reconnect Notion", response.json()["detail"])
        self.assertNotIn(str(self._credential_runtime_root), response.text)

    def test_other_user_cannot_read_connector(self):
        create_response = self.client.post(
            "/api/connectors",
            json={"name": "Private Notion", "platform": "notion"},
            headers={"Authorization": "Bearer test-token"},
        )
        connector_id = create_response.json()["connector"]["id"]
        self.client.app.dependency_overrides[notion_router.get_current_user] = (
            lambda: {"user_id": 8, "email": "other@example.com"}
        )

        response = self.client.get(
            f"/api/connectors/{connector_id}",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(response.json()["detail"], "Notion connector not found.")
        self.assertNotIn(connector_id, response.text)

    def test_permission_error_response_redacts_raw_cli_text(self):
        create_response = self.client.post(
            "/api/connectors",
            json={"name": "Notion", "platform": "notion"},
            headers={"Authorization": "Bearer test-token"},
        )
        connector_id = create_response.json()["connector"]["id"]
        self.client.post(
            f"/api/connectors/{connector_id}/auth/login",
            headers={"Authorization": "Bearer test-token"},
        )
        self.client.post(
            f"/api/connectors/{connector_id}/auth/poll",
            headers={"Authorization": "Bearer test-token"},
        )
        secret = "raw-notion-token-in-cli-output"

        with patch.object(
            notion_operations,
            "discover_databases",
            new=AsyncMock(side_effect=NotionPermissionError(secret)),
        ):
            response = self.client.get(
                f"/api/connectors/{connector_id}/databases",
                headers={"Authorization": "Bearer test-token"},
            )
        self.assertEqual(response.status_code, 403, response.text)
        self.assertNotIn(secret, response.text)
        self.assertIn("permissions", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
