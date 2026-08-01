# [Input] Consume Story Workspace router, temporary SQLite data, and FastAPI TestClient.
# [Output] Verify task_202 authentication, ownership, query, detail, and PATCH contracts.
# [Pos] focused API test node for backend/routers/story_workspace.py.
# [Sync] 2026-08-01: add Story Workspace REST API baseline coverage.

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database
from routers import story_workspace


_SCHEMA = """
CREATE TABLE users (id INTEGER PRIMARY KEY);
CREATE TABLE story_workspace_workspaces (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  owner_id INTEGER NOT NULL,
  settings TEXT DEFAULT '{}',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (owner_id) REFERENCES users (id)
);
CREATE TABLE story_workspace_stories (
  id TEXT PRIMARY KEY,
  identifier TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'draft',
  review_status TEXT NOT NULL DEFAULT 'pending',
  type TEXT NOT NULL DEFAULT 'short',
  content TEXT,
  author_id INTEGER NOT NULL,
  workspace_id TEXT NOT NULL,
  character_count INTEGER NOT NULL DEFAULT 0,
  scene_count INTEGER NOT NULL DEFAULT 0,
  agent_generated INTEGER NOT NULL DEFAULT 1,
  agent_session_id TEXT,
  review_notes TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  confirmed_at DATETIME,
  published_at DATETIME,
  FOREIGN KEY (author_id) REFERENCES users (id),
  FOREIGN KEY (workspace_id) REFERENCES story_workspace_workspaces (id)
);
CREATE TABLE story_workspace_characters (
  id TEXT PRIMARY KEY,
  identifier TEXT NOT NULL,
  name TEXT NOT NULL,
  avatar_url TEXT,
  identity TEXT,
  personality TEXT,
  background TEXT,
  catchphrase TEXT,
  tags TEXT DEFAULT '[]',
  notes TEXT,
  author_id INTEGER NOT NULL,
  workspace_id TEXT NOT NULL,
  story_count INTEGER NOT NULL DEFAULT 0,
  review_status TEXT NOT NULL DEFAULT 'pending',
  agent_generated INTEGER NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (author_id) REFERENCES users (id),
  FOREIGN KEY (workspace_id) REFERENCES story_workspace_workspaces (id)
);
CREATE TABLE story_workspace_scenes (
  id TEXT PRIMARY KEY,
  identifier TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  story_id TEXT,
  author_id INTEGER NOT NULL,
  workspace_id TEXT NOT NULL,
  character_count INTEGER NOT NULL DEFAULT 0,
  order_index INTEGER NOT NULL DEFAULT 0,
  review_status TEXT NOT NULL DEFAULT 'pending',
  agent_generated INTEGER NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (story_id) REFERENCES story_workspace_stories (id),
  FOREIGN KEY (author_id) REFERENCES users (id),
  FOREIGN KEY (workspace_id) REFERENCES story_workspace_workspaces (id)
);
CREATE TABLE story_workspace_story_characters (
  story_id TEXT NOT NULL,
  character_id TEXT NOT NULL,
  role_type TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (story_id, character_id)
);
CREATE TABLE story_workspace_scene_characters (
  scene_id TEXT NOT NULL,
  character_id TEXT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (scene_id, character_id)
);
"""


class StoryWorkspaceAPITest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = database.DB_PATH
        database.DB_PATH = Path(self.temp_dir.name) / "story-workspace-test.db"
        db = database.get_db()
        db.executescript(_SCHEMA)
        db.executemany("INSERT INTO users (id) VALUES (?)", [(1,), (2,), (3,)])
        db.executemany(
            "INSERT INTO story_workspace_workspaces (id, name, owner_id, settings) "
            "VALUES (?, ?, ?, ?)",
            [
                ("ws-1", "Writer One", 1, '{"theme":"ink"}'),
                ("ws-2", "Writer Two", 2, "{}"),
            ],
        )
        db.executemany(
            """INSERT INTO story_workspace_stories
               (id, identifier, title, description, status, review_status, type,
                content, author_id, workspace_id, character_count, scene_count,
                agent_generated, agent_session_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    "story-1", "story-001", "午夜咖啡馆", "雨夜故事", "draft",
                    "pending", "short", "chapter one", 1, "ws-1", 1, 1, 1,
                    "thread-1", "2026-07-01 00:00:00", "2026-07-03 00:00:00",
                ),
                (
                    "story-2", "story-002", "白昼书店", "日光故事", "published",
                    "confirmed", "long", "chapter two", 1, "ws-1", 0, 0, 1,
                    "thread-2", "2026-07-02 00:00:00", "2026-07-02 00:00:00",
                ),
                (
                    "story-3", "story-003", "咖啡与月亮", "月光故事", "draft",
                    "rejected", "outline", "chapter three", 1, "ws-1", 0, 0, 1,
                    "thread-3", "2026-07-03 00:00:00", "2026-07-01 00:00:00",
                ),
                (
                    "story-other", "story-900", "他人的故事", "private", "draft",
                    "pending", "script", "secret", 2, "ws-2", 1, 1, 1,
                    "thread-other", "2026-07-01 00:00:00", "2026-07-04 00:00:00",
                ),
            ],
        )
        db.executemany(
            """INSERT INTO story_workspace_characters
               (id, identifier, name, identity, personality, tags, author_id,
                workspace_id, story_count, review_status, agent_generated,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    "char-1", "char-001", "林小雨", "咖啡师", "温柔", '["温柔"]',
                    1, "ws-1", 1, "pending", 1, "2026-07-01", "2026-07-03",
                ),
                (
                    "char-2", "char-002", "周晴", "店主", "果断", '["果断"]',
                    1, "ws-1", 0, "confirmed", 1, "2026-07-02", "2026-07-02",
                ),
                (
                    "char-other", "char-900", "他人角色", "未知", "private", "[]",
                    2, "ws-2", 1, "pending", 1, "2026-07-01", "2026-07-04",
                ),
            ],
        )
        db.executemany(
            """INSERT INTO story_workspace_scenes
               (id, identifier, name, description, story_id, author_id, workspace_id,
                character_count, order_index, review_status, agent_generated,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    "scene-1", "scene-001", "开场·雨夜", "雨中的咖啡馆", "story-1",
                    1, "ws-1", 1, 1, "pending", 1, "2026-07-01", "2026-07-03",
                ),
                (
                    "scene-2", "scene-002", "书店午后", "晴天", "story-2",
                    1, "ws-1", 0, 2, "confirmed", 1, "2026-07-02", "2026-07-02",
                ),
                (
                    "scene-other", "scene-900", "秘密场景", "private", "story-other",
                    2, "ws-2", 1, 1, "pending", 1, "2026-07-01", "2026-07-04",
                ),
            ],
        )
        db.execute(
            "INSERT INTO story_workspace_story_characters "
            "(story_id, character_id, role_type) VALUES (?, ?, ?)",
            ("story-1", "char-1", "主角"),
        )
        db.execute(
            "INSERT INTO story_workspace_scene_characters (scene_id, character_id) "
            "VALUES (?, ?)",
            ("scene-1", "char-1"),
        )
        db.commit()
        db.close()

        app = FastAPI()
        app.dependency_overrides[story_workspace.get_current_user] = (
            lambda: {"user_id": 1, "email": "writer@example.com"}
        )
        app.include_router(story_workspace.router)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        database.DB_PATH = self.old_db_path
        self.temp_dir.cleanup()

    def test_unauthenticated_request_is_rejected(self) -> None:
        app = FastAPI()
        app.include_router(story_workspace.router)
        with TestClient(app) as anonymous_client:
            response = anonymous_client.get("/api/story-workspace/stories")
        self.assertEqual(response.status_code, 401)

    def test_workspace_get_patch_and_owner_isolation(self) -> None:
        response = self.client.get("/api/story-workspace/workspace")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["id"], "ws-1")
        self.assertEqual(response.json()["settings"], {"theme": "ink"})

        response = self.client.patch(
            "/api/story-workspace/workspace/ws-1",
            json={"name": "Ink Room", "settings": {"theme": "paper"}},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["name"], "Ink Room")
        self.assertEqual(response.json()["settings"], {"theme": "paper"})

        response = self.client.patch(
            "/api/story-workspace/workspace/ws-2", json={"name": "stolen"}
        )
        self.assertEqual(response.status_code, 404)

    def test_workspace_is_created_for_user_without_one(self) -> None:
        app = FastAPI()
        app.dependency_overrides[story_workspace.get_current_user] = lambda: {"user_id": 3}
        app.include_router(story_workspace.router)
        with TestClient(app) as user_three_client:
            first = user_three_client.get("/api/story-workspace/workspace")
            second = user_three_client.get("/api/story-workspace/workspace")
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["id"], second.json()["id"])
        self.assertEqual(first.json()["owner_id"], 3)

    def test_story_search_filters_sort_and_pagination(self) -> None:
        response = self.client.get(
            "/api/story-workspace/stories",
            params={
                "q": "咖啡",
                "status": "draft",
                "type": "short,outline",
                "review_status": "pending,rejected",
                "sort": "title",
                "order": "asc",
                "page": 1,
                "per_page": 1,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(len(payload["data"]), 1)
        self.assertEqual(payload["data"][0]["title"], "午夜咖啡馆")
        self.assertEqual(
            payload["pagination"],
            {"page": 1, "per_page": 1, "total": 2, "total_pages": 2},
        )
        self.assertNotIn("story-other", [item["id"] for item in payload["data"]])

    def test_list_query_rejects_sort_injection_and_large_pages(self) -> None:
        response = self.client.get(
            "/api/story-workspace/stories", params={"sort": "title; DROP TABLE users"}
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.get(
            "/api/story-workspace/stories", params={"order": "sideways"}
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.get(
            "/api/story-workspace/stories", params={"per_page": 101}
        )
        self.assertEqual(response.status_code, 422)

    def test_story_detail_contains_owned_characters_and_scenes(self) -> None:
        response = self.client.get("/api/story-workspace/stories/story-1")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual([item["id"] for item in payload["characters"]], ["char-1"])
        self.assertEqual([item["id"] for item in payload["scenes"]], ["scene-1"])
        self.assertEqual(payload["characters"][0]["tags"], ["温柔"])

    def test_character_and_scene_lists_and_details(self) -> None:
        response = self.client.get(
            "/api/story-workspace/characters",
            params={"q": "林", "review_status": "pending", "sort": "name"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([item["id"] for item in response.json()["data"]], ["char-1"])
        self.assertEqual(response.json()["pagination"]["total"], 1)

        response = self.client.get("/api/story-workspace/characters/char-1")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([item["id"] for item in response.json()["stories"]], ["story-1"])

        response = self.client.get(
            "/api/story-workspace/scenes",
            params={"q": "雨夜", "story_id": "story-1", "review_status": "pending"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([item["id"] for item in response.json()["data"]], ["scene-1"])

        response = self.client.get("/api/story-workspace/scenes/scene-1")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["story"]["id"], "story-1")
        self.assertEqual([item["id"] for item in response.json()["characters"]], ["char-1"])

    def test_controlled_patches_update_only_allowed_fields(self) -> None:
        response = self.client.patch(
            "/api/story-workspace/stories/story-1",
            json={"title": "新标题", "content": "edited", "type": "script"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["title"], "新标题")
        self.assertEqual(response.json()["review_status"], "pending")

        response = self.client.patch(
            "/api/story-workspace/characters/char-1",
            json={"identity": "夜班咖啡师", "tags": ["温柔", "敏锐"]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["tags"], ["温柔", "敏锐"])

        response = self.client.patch(
            "/api/story-workspace/scenes/scene-1",
            json={"description": "雨更大了", "order_index": 3},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["order_index"], 3)

    def test_patch_rejects_authoritative_and_unknown_fields(self) -> None:
        forbidden_payloads = [
            {"review_status": "confirmed"},
            {"agent_generated": False},
            {"agent_session_id": "forged-thread"},
            {"author_id": 2},
            {"unknown": "value"},
        ]
        for payload in forbidden_payloads:
            with self.subTest(payload=payload):
                response = self.client.patch(
                    "/api/story-workspace/stories/story-1", json=payload
                )
                self.assertEqual(response.status_code, 422, response.text)

        db = database.get_db()
        row = db.execute(
            "SELECT review_status, agent_generated, agent_session_id, author_id "
            "FROM story_workspace_stories WHERE id = ?",
            ("story-1",),
        ).fetchone()
        db.close()
        self.assertEqual(dict(row), {
            "review_status": "pending",
            "agent_generated": 1,
            "agent_session_id": "thread-1",
            "author_id": 1,
        })

        for payload in ({"title": None}, {"type": "novel"}):
            with self.subTest(payload=payload):
                response = self.client.patch(
                    "/api/story-workspace/stories/story-1", json=payload
                )
                self.assertEqual(response.status_code, 422, response.text)

    def test_cross_user_and_missing_resources_return_404(self) -> None:
        cases = [
            ("get", "/api/story-workspace/stories/story-other", None),
            ("patch", "/api/story-workspace/stories/story-other", {"title": "stolen"}),
            ("get", "/api/story-workspace/characters/char-other", None),
            ("patch", "/api/story-workspace/characters/char-other", {"name": "stolen"}),
            ("get", "/api/story-workspace/scenes/scene-other", None),
            ("patch", "/api/story-workspace/scenes/scene-other", {"name": "stolen"}),
            ("get", "/api/story-workspace/stories/missing", None),
            ("get", "/api/story-workspace/characters/missing", None),
            ("get", "/api/story-workspace/scenes/missing", None),
        ]
        for method, path, body in cases:
            with self.subTest(method=method, path=path):
                response = getattr(self.client, method)(path, json=body) if body else getattr(self.client, method)(path)
                self.assertEqual(response.status_code, 404, response.text)

    def test_scene_cannot_be_reassigned_to_another_users_story(self) -> None:
        response = self.client.patch(
            "/api/story-workspace/scenes/scene-1",
            json={"story_id": "story-other"},
        )
        self.assertEqual(response.status_code, 404, response.text)

    def test_router_exposes_only_the_requested_baseline_methods(self) -> None:
        methods_by_path: dict[str, set[str]] = {}
        for route in story_workspace.router.routes:
            methods_by_path.setdefault(route.path, set()).update(route.methods)
        expected = {
            "/api/story-workspace/workspace": {"GET"},
            "/api/story-workspace/workspace/{workspace_id}": {"PATCH"},
            "/api/story-workspace/stories": {"GET"},
            "/api/story-workspace/stories/{story_id}": {"GET", "PATCH"},
            "/api/story-workspace/characters": {"GET"},
            "/api/story-workspace/characters/{character_id}": {"GET", "PATCH"},
            "/api/story-workspace/scenes": {"GET"},
            "/api/story-workspace/scenes/{scene_id}": {"GET", "PATCH"},
        }
        for path, methods in expected.items():
            self.assertIn(path, methods_by_path)
            self.assertEqual(methods_by_path[path], methods)
        self.assertFalse(any("workflow-runs" in path for path in methods_by_path))


if __name__ == "__main__":
    unittest.main()
