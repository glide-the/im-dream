# [Input] Authenticated connector router, isolated Admin DTO boundary and fake remote Notion provider.
# [Output] Public article reads exercise page identity, selected scope, revocation and safe errors.
# [Pos] Provider-free regression; the fixture owns temporary credentials and in-memory Admin data.
from dataclasses import replace
from unittest import TestCase
from unittest.mock import AsyncMock, patch

import test_notion_connector_router_flow as connector_flow
from notion.operations import NotionOperationClient
from notion.today import NotionTodayError
from routers import notion as notion_router


class NoteArticleJourney(TestCase):
    page = "40b30b75-47c3-80cd-9930-c384ab35023c"
    other = "42130b75-47c3-800a-ad38-daaa6f003a8a"

    def setUp(self):
        self.fixture = connector_flow.TestNotionConnectorRouterFlow()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.client = self.fixture.client
        self.endpoint = "/api/connectors/notion/articles/" + self.page.replace("-", "")
        self.remote = AsyncMock(return_value={
            "object": "page_markdown", "id": self.page, "markdown": "## Meeting\nAgenda",
            "truncated": False, "unknown_block_ids": [],
        })
        self.enterContext(patch.object(NotionOperationClient, "_run_endpoint", self.remote))
        self.enterContext(patch("config.NOTION_TODAY_API_VERSION", "2026-03-11"))

    def connect(self):
        connector = self.client.post("/api/connectors", json={"name": "Writing fixture"}).json()["connector"]["id"]
        self.base = f"/api/connectors/{connector}"
        for path in ["/auth/login", "/auth/poll"]:
            self.assertEqual(self.client.post(self.base + path).status_code, 200)
        self.select([self.page.replace("-", "")])

    def select(self, pages):
        response = self.client.post(self.base + "/resources/select", json={"selected_pages": pages})
        self.assertEqual(response.status_code, 200, response.text)

    def test_reads_only_selected_page_and_validates_upstream_identity(self):
        self.connect()
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"pageId": self.page, "title": "Team Notes", "markdown": "## Meeting\nAgenda"})
        self.assertIn("no-store", response.headers["cache-control"])
        self.remote.assert_awaited_once_with(f"v1/pages/{self.page}/markdown")
        self.remote.return_value["id"] = self.other
        self.assertEqual(self.client.get(self.endpoint).status_code, 502)

    def test_unavailable_connector_scope_and_invalid_id_do_not_read(self):
        self.assertEqual(self.client.get(self.endpoint).status_code, 404)
        self.connect()
        denied = self.client.get("/api/connectors/notion/articles/" + self.other)
        self.assertEqual(denied.json()["detail"]["error_code"], "NOTION_RESOURCE_NOT_SELECTED")
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(self.client.get("/api/connectors/notion/articles/not-a-page-id").status_code, 422)
        self.remote.assert_not_awaited()

    def test_non_notion_platform_cannot_supply_article_scope(self):
        self.connect()
        self.assertEqual(self.client.patch(self.base, json={"platform": "other"}).status_code, 200)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 404)
        self.remote.assert_not_awaited()

    def test_another_actor_cannot_read_the_selected_article(self):
        self.connect()
        actor = replace(self.fixture._actor, canonical_user_id="8", access_token="other-notion-oauth-token")
        self.client.app.dependency_overrides[notion_router.get_current_user] = actor.current_user_projection
        response = self.client.get(self.endpoint)
        self.assertIn(response.status_code, (403, 404))
        self.assertNotIn("Agenda", response.text)
        self.remote.assert_not_awaited()

    def test_drops_body_if_user_removes_selection_while_reading(self):
        self.connect()
        def revoke(*_):
            self.select([])
            return self.remote.return_value
        self.remote.side_effect = revoke
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 409, response.text)
        self.assertNotIn("Agenda", response.text)

    def test_expired_upstream_authorization_is_scoped_to_notion(self):
        self.connect()
        self.remote.side_effect = NotionTodayError("NOTION_AUTH_EXPIRED", 401)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"]["error_code"], "NOTION_AUTH_EXPIRED")
