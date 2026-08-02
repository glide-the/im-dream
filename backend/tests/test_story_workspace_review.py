# [Input] Consume Story Workspace review routes and a temporary SQLite database.
# [Output] Verify task_203 transitions, batch accounting, auth, and audit logs.
# [Pos] Focused unittest node for the Story Workspace review workflow.
# [Sync] 2026-08-01: cover AC-203-01 through AC-203-07.

from __future__ import annotations

import logging
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
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE story_workspace_stories (
  id TEXT PRIMARY KEY,
  identifier TEXT NOT NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft',
  review_status TEXT NOT NULL DEFAULT 'pending',
  type TEXT NOT NULL DEFAULT 'short',
  author_id INTEGER NOT NULL,
  workspace_id TEXT NOT NULL,
  character_count INTEGER NOT NULL DEFAULT 0,
  scene_count INTEGER NOT NULL DEFAULT 0,
  agent_generated INTEGER NOT NULL DEFAULT 1,
  review_notes TEXT CHECK(review_notes IS NULL OR length(review_notes) <= 2000),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  confirmed_at DATETIME,
  published_at DATETIME
);
CREATE TABLE story_workspace_characters (
  id TEXT PRIMARY KEY,
  identifier TEXT NOT NULL,
  name TEXT NOT NULL,
  author_id INTEGER NOT NULL,
  workspace_id TEXT NOT NULL,
  story_count INTEGER NOT NULL DEFAULT 0,
  review_status TEXT NOT NULL DEFAULT 'pending',
  agent_generated INTEGER NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  status TEXT NOT NULL DEFAULT 'active',
  review_notes TEXT CHECK(review_notes IS NULL OR length(review_notes) <= 2000),
  confirmed_at DATETIME,
  archived_at DATETIME
);
CREATE TABLE story_workspace_scenes (
  id TEXT PRIMARY KEY,
  identifier TEXT NOT NULL,
  name TEXT NOT NULL,
  story_id TEXT,
  author_id INTEGER NOT NULL,
  workspace_id TEXT NOT NULL,
  character_count INTEGER NOT NULL DEFAULT 0,
  order_index INTEGER NOT NULL DEFAULT 0,
  review_status TEXT NOT NULL DEFAULT 'pending',
  agent_generated INTEGER NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  status TEXT NOT NULL DEFAULT 'active',
  review_notes TEXT CHECK(review_notes IS NULL OR length(review_notes) <= 2000),
  confirmed_at DATETIME,
  archived_at DATETIME
);
CREATE TABLE story_workspace_story_characters (
  story_id TEXT NOT NULL,
  character_id TEXT NOT NULL,
  role_type TEXT,
  PRIMARY KEY (story_id, character_id)
);
CREATE TABLE story_workspace_scene_characters (
  scene_id TEXT NOT NULL,
  character_id TEXT NOT NULL,
  PRIMARY KEY (scene_id, character_id)
);
"""


class _CaptureHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


class StoryWorkspaceReviewTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = database.DB_PATH
        database.DB_PATH = Path(self.temp_dir.name) / "story-review-test.db"
        db = database.get_db()
        db.executescript(_SCHEMA)
        db.executemany("INSERT INTO users (id) VALUES (?)", [(1,), (2,)])
        db.executemany(
            "INSERT INTO story_workspace_workspaces (id, name, owner_id) "
            "VALUES (?, ?, ?)",
            [("ws-1", "Writer One", 1), ("ws-2", "Writer Two", 2)],
        )
        self._seed_resources(db)
        db.commit()
        db.close()

        self.app = FastAPI()
        self.app.dependency_overrides[story_workspace.get_current_user] = (
            lambda: {"user_id": 1, "email": "writer@example.com"}
        )
        self.app.include_router(story_workspace.router)
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.client.close()
        database.DB_PATH = self.old_db_path
        self.temp_dir.cleanup()

    @staticmethod
    def _seed_resources(db) -> None:
        states = [
            ("pending-confirm", "pending", "active", 1, 1),
            ("pending-reject", "pending", "active", 1, 1),
            ("confirmed", "confirmed", "active", 1, 1),
            ("rejected", "rejected", "active", 1, 1),
            ("archived", "pending", "archived", 1, 1),
            ("other", "pending", "active", 2, 1),
            ("manual", "pending", "active", 1, 0),
        ]
        for suffix, review_status, asset_status, author_id, generated in states:
            workspace_id = "ws-1" if author_id == 1 else "ws-2"
            story_status = "archived" if asset_status == "archived" else "draft"
            db.execute(
                "INSERT INTO story_workspace_stories "
                "(id, identifier, title, status, review_status, author_id, "
                "workspace_id, agent_generated) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"story-{suffix}",
                    f"story-{suffix}",
                    suffix,
                    story_status,
                    review_status,
                    author_id,
                    workspace_id,
                    generated,
                ),
            )
            db.execute(
                "INSERT INTO story_workspace_characters "
                "(id, identifier, name, author_id, workspace_id, review_status, "
                "agent_generated, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"character-{suffix}",
                    f"character-{suffix}",
                    suffix,
                    author_id,
                    workspace_id,
                    review_status,
                    generated,
                    asset_status,
                ),
            )
            db.execute(
                "INSERT INTO story_workspace_scenes "
                "(id, identifier, name, author_id, workspace_id, review_status, "
                "agent_generated, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"scene-{suffix}",
                    f"scene-{suffix}",
                    suffix,
                    author_id,
                    workspace_id,
                    review_status,
                    generated,
                    asset_status,
                ),
            )

    def _db_value(self, table: str, resource_id: str, column: str):
        db = database.get_db()
        try:
            return db.execute(
                f"SELECT {column} FROM {table} WHERE id = ?", (resource_id,)
            ).fetchone()[0]
        finally:
            db.close()

    def test_pending_confirm_and_reject_for_all_resource_types(self) -> None:
        notes = "改" * 2000
        for plural, prefix in (
            ("stories", "story"),
            ("characters", "character"),
            ("scenes", "scene"),
        ):
            with self.subTest(resource=prefix, action="confirm"):
                response = self.client.post(
                    f"/api/story-workspace/{plural}/{prefix}-pending-confirm/confirm"
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["review_status"], "confirmed")
                self.assertIsNotNone(response.json()["confirmed_at"])

            with self.subTest(resource=prefix, action="reject"):
                response = self.client.post(
                    f"/api/story-workspace/{plural}/{prefix}-pending-reject/reject",
                    json={"review_notes": notes},
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["review_status"], "rejected")
                self.assertEqual(response.json()["review_notes"], notes)

    def test_story_confirmation_commits_the_reviewed_bundle_and_publishes(self) -> None:
        db = database.get_db()
        try:
            with db:
                db.execute(
                    "INSERT INTO story_workspace_stories "
                    "(id, identifier, title, status, review_status, author_id, workspace_id, agent_generated) "
                    "VALUES ('story-bundle', 'story-bundle', 'Bundle', 'draft', 'pending', 1, 'ws-1', 1)"
                )
                db.execute(
                    "INSERT INTO story_workspace_characters "
                    "(id, identifier, name, author_id, workspace_id, review_status, agent_generated, status) "
                    "VALUES ('character-bundle', 'character-bundle', 'Bundle role', 1, 'ws-1', 'pending', 1, 'active')"
                )
                db.execute(
                    "INSERT INTO story_workspace_scenes "
                    "(id, identifier, name, story_id, author_id, workspace_id, review_status, agent_generated, status) "
                    "VALUES ('scene-bundle', 'scene-bundle', 'Bundle scene', 'story-bundle', 1, 'ws-1', 'pending', 1, 'active')"
                )
                db.execute(
                    "INSERT INTO story_workspace_story_characters (story_id, character_id) "
                    "VALUES ('story-bundle', 'character-bundle')"
                )
        finally:
            db.close()

        response = self.client.post("/api/story-workspace/stories/story-bundle/confirm")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["review_status"], "confirmed")
        self.assertEqual(response.json()["status"], "published")
        self.assertEqual(response.json()["execution"]["status"], "completed")
        self.assertEqual(
            self._db_value("story_workspace_characters", "character-bundle", "review_status"),
            "confirmed",
        )
        self.assertEqual(
            self._db_value("story_workspace_scenes", "scene-bundle", "review_status"),
            "confirmed",
        )

    def test_non_pending_review_transition_matrix(self) -> None:
        for plural, prefix in (
            ("stories", "story"),
            ("characters", "character"),
            ("scenes", "scene"),
        ):
            for current_status in ("confirmed", "rejected", "archived"):
                for action in ("confirm", "reject"):
                    with self.subTest(
                        resource=prefix,
                        current_status=current_status,
                        action=action,
                    ):
                        response = self.client.post(
                            f"/api/story-workspace/{plural}/"
                            f"{prefix}-{current_status}/{action}",
                            json={"review_notes": "should not persist"}
                            if action == "reject"
                            else None,
                        )
                        self.assertEqual(response.status_code, 400, response.text)

    def test_story_archive_matrix_preserves_review_status(self) -> None:
        cases = [
            ("story-pending-confirm", "pending"),
            ("story-confirmed", "confirmed"),
            ("story-rejected", "rejected"),
        ]
        for story_id, expected_review_status in cases:
            with self.subTest(story_id=story_id):
                response = self.client.post(
                    f"/api/story-workspace/stories/{story_id}/archive"
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["status"], "archived")
                self.assertEqual(
                    response.json()["review_status"], expected_review_status
                )
                repeated = self.client.post(
                    f"/api/story-workspace/stories/{story_id}/archive"
                )
                self.assertEqual(repeated.status_code, 400, repeated.text)

    def test_batch_pending_only_and_result_accounting(self) -> None:
        response = self.client.post(
            "/api/story-workspace/batch",
            json={
                "action": "confirm",
                "resource_type": "story",
                "ids": [
                    "story-pending-confirm",
                    "story-confirmed",
                    "story-other",
                    "story-missing",
                ],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["total_requested"], 4)
        self.assertEqual(response.json()["total_updated"], 1)
        self.assertEqual(
            response.json()["skipped_ids"],
            ["story-confirmed", "story-other", "story-missing"],
        )
        self.assertEqual(
            [item["id"] for item in response.json()["updated_items"]],
            ["story-pending-confirm"],
        )

        response = self.client.post(
            "/api/story-workspace/batch",
            json={
                "action": "reject",
                "resource_type": "character",
                "ids": ["character-pending-reject", "character-rejected"],
                "review_notes": "批量修改",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["total_updated"], 1)
        self.assertEqual(response.json()["skipped_ids"], ["character-rejected"])
        self.assertEqual(
            response.json()["updated_items"][0]["review_notes"], "批量修改"
        )

        response = self.client.post(
            "/api/story-workspace/batch",
            json={
                "action": "archive",
                "resource_type": "scene",
                "ids": ["scene-pending-confirm", "scene-confirmed"],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["total_updated"], 1)
        self.assertEqual(response.json()["skipped_ids"], ["scene-confirmed"])
        self.assertEqual(response.json()["updated_items"][0]["status"], "archived")
        self.assertIsNotNone(response.json()["updated_items"][0]["archived_at"])

    def test_review_authentication_and_owner_isolation(self) -> None:
        anonymous_app = FastAPI()
        anonymous_app.include_router(story_workspace.router)
        with TestClient(anonymous_app) as anonymous_client:
            response = anonymous_client.post(
                "/api/story-workspace/stories/story-pending-confirm/confirm"
            )
        self.assertEqual(response.status_code, 401, response.text)

        for resource, prefix in (
            ("stories", "story"),
            ("characters", "character"),
            ("scenes", "scene"),
        ):
            with self.subTest(resource=resource, owner="other"):
                response = self.client.post(
                    f"/api/story-workspace/{resource}/{prefix}-other/confirm"
                )
                self.assertEqual(response.status_code, 404, response.text)
            with self.subTest(resource=resource, generated=False):
                response = self.client.post(
                    f"/api/story-workspace/{resource}/{prefix}-manual/confirm"
                )
                self.assertEqual(response.status_code, 404, response.text)

    def test_review_request_validation_is_atomic(self) -> None:
        invalid_payloads = [
            {"action": "publish", "resource_type": "story", "ids": ["story-pending-confirm"]},
            {"action": "confirm", "resource_type": "episode", "ids": ["story-pending-confirm"]},
            {"action": "confirm", "resource_type": "story", "ids": []},
            {"action": "confirm", "resource_type": "story", "ids": [f"id-{index}" for index in range(101)]},
            {"action": "reject", "resource_type": "story", "ids": ["story-pending-confirm"], "review_notes": "x" * 2001},
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.client.post(
                    "/api/story-workspace/batch", json=payload
                )
                self.assertEqual(response.status_code, 422, response.text)
                self.assertEqual(
                    self._db_value(
                        "story_workspace_stories",
                        "story-pending-confirm",
                        "review_status",
                    ),
                    "pending",
                )

        response = self.client.post(
            "/api/story-workspace/stories/story-pending-reject/reject",
            json={"review_notes": "字" * 2001},
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            self._db_value(
                "story_workspace_stories",
                "story-pending-reject",
                "review_status",
            ),
            "pending",
        )

    def test_review_action_emits_structured_audit_log(self) -> None:
        handler = _CaptureHandler()
        old_level = story_workspace.logger.level
        story_workspace.logger.addHandler(handler)
        story_workspace.logger.setLevel(logging.INFO)
        try:
            response = self.client.post(
                "/api/story-workspace/characters/character-pending-reject/reject",
                json={"review_notes": "补充人物动机"},
            )
        finally:
            story_workspace.logger.removeHandler(handler)
            story_workspace.logger.setLevel(old_level)

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(handler.records), 1)
        record = handler.records[0]
        self.assertEqual(record.getMessage(), "story_workspace_review")
        self.assertTrue(record.id)
        self.assertEqual(record.user_id, 1)
        self.assertEqual(record.resource_type, "character")
        self.assertEqual(record.resource_id, "character-pending-reject")
        self.assertEqual(record.action, "reject")
        self.assertEqual(record.previous_status, "pending")
        self.assertEqual(record.new_status, "rejected")
        self.assertEqual(record.review_notes, "补充人物动机")
        self.assertTrue(record.created_at.endswith("+00:00"))


if __name__ == "__main__":
    unittest.main()
