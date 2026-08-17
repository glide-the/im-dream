# [Input] Consume Agent bundle models/service, Story Workspace endpoint, and Claude success flow.
# [Output] Verify contract, atomic persistence, idempotency, REST errors, and Chat isolation.
# [Pos] focused task_204 integration tests in backend/tests.
# [Sync] 2026-08-01: add AC-204-01 through AC-204-05 executable coverage.

from __future__ import annotations

import asyncio
import sqlite3
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database
from agent_stream_events import NormalizedAgentEvent
from routers import story_workspace
from story_workspace.contracts import (
    StoryWorkspaceAgentCharacterPayload,
    StoryWorkspaceAgentScenePayload,
    StoryWorkspaceAgentStoryPayload,
)
from services.story_workspace.agent_integration import (
    AgentIntegrationError,
    parse_agent_story_output,
    store_agent_story_output,
)
from tests.legacy_database_fixture import LegacyDatabaseModuleFixture


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
  published_at DATETIME
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
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
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
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
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


class _StoryWorkspaceDatabaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(_SCHEMA)
        self.connection.execute("INSERT INTO users (id) VALUES (1)")
        self.connection.execute(
            "INSERT INTO story_workspace_workspaces (id, name, owner_id, settings) "
            "VALUES ('workspace-1', 'Writer', 1, '{}')"
        )
        self.connection.commit()

    def tearDown(self) -> None:
        self.connection.close()

    @staticmethod
    def _payload(*, description: str = "雨夜故事") -> StoryWorkspaceAgentStoryPayload:
        return StoryWorkspaceAgentStoryPayload(
            title="午夜咖啡馆",
            description=description,
            type="script",
            content="# 第一幕",
            characters=[
                StoryWorkspaceAgentCharacterPayload(
                    name="林小雨",
                    identity="咖啡师",
                    personality="温柔",
                    tags=["温柔"],
                ),
                StoryWorkspaceAgentCharacterPayload(name="周晴", identity="店主"),
            ],
            scenes=[
                StoryWorkspaceAgentScenePayload(
                    name="雨夜", description="开场", order_index=0
                ),
                StoryWorkspaceAgentScenePayload(
                    name="清晨", description="结尾", order_index=1
                ),
            ],
        )

    def test_agent_story_payload_contract_and_import(self) -> None:
        payload = StoryWorkspaceAgentStoryPayload(
            title="  标题  ", future_field="ignored"
        )
        self.assertEqual(payload.title, "标题")
        self.assertNotIn("future_field", payload.model_dump())
        self.assertIsNone(parse_agent_story_output("ordinary Chat prose"))
        self.assertEqual(
            parse_agent_story_output('```json\n{"title":"JSON 剧本"}\n```').title,
            "JSON 剧本",
        )

        with self.assertRaises(ValidationError):
            StoryWorkspaceAgentStoryPayload(description="没有标题")
        with self.assertRaises(ValidationError):
            StoryWorkspaceAgentStoryPayload(title="有效", characters=[{"name": "  "}])
        with self.assertRaises(ValidationError):
            StoryWorkspaceAgentStoryPayload(
                title="有效", scenes=[{"description": "无名称"}]
            )

    def test_store_agent_story_output_persists_complete_bundle(self) -> None:
        result = store_agent_story_output(
            self.connection,
            1,
            "workspace-1",
            "thread-001",
            self._payload(),
        )

        story = self.connection.execute(
            "SELECT * FROM story_workspace_stories WHERE id = ?",
            (result["story_id"],),
        ).fetchone()
        self.assertEqual(story["review_status"], "pending")
        self.assertEqual(story["agent_generated"], 1)
        self.assertEqual(story["agent_session_id"], "thread-001")
        self.assertEqual((story["character_count"], story["scene_count"]), (2, 2))

        characters = self.connection.execute(
            "SELECT * FROM story_workspace_characters ORDER BY name"
        ).fetchall()
        scenes = self.connection.execute(
            "SELECT * FROM story_workspace_scenes ORDER BY order_index"
        ).fetchall()
        self.assertEqual(len(characters), 2)
        self.assertEqual(len(scenes), 2)
        self.assertTrue(all(row["review_status"] == "pending" for row in characters + scenes))
        self.assertTrue(all(row["agent_generated"] == 1 for row in characters + scenes))
        self.assertTrue(all(row["story_count"] == 1 for row in characters))
        self.assertTrue(all(row["character_count"] == 2 for row in scenes))
        self.assertEqual(
            self.connection.execute(
                "SELECT COUNT(*) FROM story_workspace_story_characters"
            ).fetchone()[0],
            2,
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT COUNT(*) FROM story_workspace_scene_characters"
            ).fetchone()[0],
            4,
        )

    def test_store_agent_story_output_is_idempotent(self) -> None:
        first = store_agent_story_output(
            self.connection, 1, "workspace-1", "thread-001", self._payload()
        )
        self.connection.execute(
            "UPDATE story_workspace_stories SET created_at = '2025-01-01 00:00:00' "
            "WHERE id = ?",
            (first["story_id"],),
        )
        self.connection.commit()

        updated_payload = self._payload(description="第二次生成")
        updated_payload.characters[0].personality = "冷静"
        updated_payload.scenes[0].description = "更新后的开场"
        second = store_agent_story_output(
            self.connection, 1, "workspace-1", "thread-001", updated_payload
        )

        self.assertEqual(first["story_id"], second["story_id"])
        expected_counts = {
            "story_workspace_stories": 1,
            "story_workspace_characters": 2,
            "story_workspace_scenes": 2,
            "story_workspace_story_characters": 2,
            "story_workspace_scene_characters": 4,
        }
        for table, expected in expected_counts.items():
            with self.subTest(table=table):
                count = self.connection.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]
                self.assertEqual(count, expected)

        story = self.connection.execute(
            "SELECT description, created_at FROM story_workspace_stories WHERE id = ?",
            (first["story_id"],),
        ).fetchone()
        self.assertEqual(story["description"], "第二次生成")
        self.assertEqual(story["created_at"], "2025-01-01 00:00:00")
        self.assertEqual(
            self.connection.execute(
                "SELECT personality FROM story_workspace_characters WHERE name = '林小雨'"
            ).fetchone()[0],
            "冷静",
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT description FROM story_workspace_scenes WHERE order_index = 0"
            ).fetchone()[0],
            "更新后的开场",
        )

    def test_store_agent_story_output_rolls_back_complete_bundle(self) -> None:
        self.connection.executescript(
            """CREATE TRIGGER fail_agent_scene BEFORE INSERT ON story_workspace_scenes
               WHEN NEW.name = '雨夜'
               BEGIN SELECT RAISE(ABORT, 'injected scene failure'); END;"""
        )
        with self.assertRaises(AgentIntegrationError):
            store_agent_story_output(
                self.connection, 1, "workspace-1", "thread-001", self._payload()
            )
        for table in (
            "story_workspace_stories",
            "story_workspace_characters",
            "story_workspace_scenes",
            "story_workspace_story_characters",
            "story_workspace_scene_characters",
        ):
            with self.subTest(table=table):
                self.assertEqual(
                    self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0],
                    0,
                )


class StoryWorkspaceAgentEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_fixture = LegacyDatabaseModuleFixture(
            database,
            Path(self.temp_dir.name) / "agent-output.db",
        )
        self.database_fixture.start()
        db = database.get_db()
        db.executescript(_SCHEMA)
        db.execute("INSERT INTO users (id) VALUES (1)")
        db.commit()
        db.close()

        self.app = FastAPI()
        self.app.dependency_overrides[story_workspace.get_current_user] = lambda: {
            "user_id": 1
        }
        self.app.include_router(story_workspace.router)
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.client.close()
        self.database_fixture.stop()
        self.temp_dir.cleanup()

    def test_internal_agent_output_endpoint_contract(self) -> None:
        anonymous_app = FastAPI()
        anonymous_app.include_router(story_workspace.router)
        with TestClient(anonymous_app) as anonymous_client:
            response = anonymous_client.post(
                "/api/story-workspace/internal/agent-output",
                json={"title": "未认证"},
                headers={"X-Agent-Session-Id": "thread-001"},
            )
        self.assertEqual(response.status_code, 401)

        missing_header = self.client.post(
            "/api/story-workspace/internal/agent-output", json={"title": "缺 Header"}
        )
        self.assertEqual(missing_header.status_code, 400)

        invalid_payload = self.client.post(
            "/api/story-workspace/internal/agent-output",
            json={"description": "缺标题"},
            headers={"X-Agent-Session-Id": "thread-001"},
        )
        self.assertEqual(invalid_payload.status_code, 422)

        success = self.client.post(
            "/api/story-workspace/internal/agent-output",
            json={
                "title": "端点剧本",
                "characters": [{"name": "端点角色"}],
                "scenes": [{"name": "端点场景", "order_index": 0}],
            },
            headers={"X-Agent-Session-Id": "thread-001"},
        )
        self.assertEqual(success.status_code, 200, success.text)
        self.assertEqual(success.json()["review_status"], "pending")
        self.assertEqual(len(success.json()["character_ids"]), 1)
        self.assertEqual(len(success.json()["scene_ids"]), 1)

        with unittest.mock.patch.object(
            story_workspace,
            "store_agent_story_output",
            side_effect=AgentIntegrationError("injected"),
        ):
            failure = self.client.post(
                "/api/story-workspace/internal/agent-output",
                json={"title": "存储失败"},
                headers={"X-Agent-Session-Id": "thread-failure"},
            )
        self.assertEqual(failure.status_code, 422)


import tests._sdk_stubs  # noqa: E402,F401 - install SDK stub before service import
import claude_agent.service as claude_service_module  # noqa: E402
from claude_agent.service import ClaudeAgentService  # noqa: E402


class ClaudeAgentStoryOutputIsolationTest(unittest.IsolatedAsyncioTestCase):
    async def test_agent_store_failure_isolated_from_successful_chat_stream(self) -> None:
        queue: asyncio.Queue = asyncio.Queue()
        result = SimpleNamespace(
            success=True,
            full_text='{"title":"隔离测试"}',
            usage={"input_tokens": 1, "output_tokens": 1},
            session_id="sdk-session",
            error=None,
        )

        class _Runner:
            async def run_streaming(self, run_options, callbacks):
                return result

        execution = SimpleNamespace(
            request=SimpleNamespace(
                user_id="1",
                thread_id="thread-isolation",
            ),
            state=SimpleNamespace(session_id="thread-isolation", turn_count=1),
            runner=_Runner(),
            run_options=SimpleNamespace(),
            turn_context=SimpleNamespace(
                queue=queue,
                confirmation_store=unittest.mock.Mock(),
                collected_parts=[],
            ),
            dream_context=None,
        )
        service = ClaudeAgentService()

        with (
            unittest.mock.patch.object(
                service,
                "_persist_user_message",
                new=unittest.mock.AsyncMock(),
            ),
            unittest.mock.patch.object(
                service,
                "_persist_assistant_turn",
                new=unittest.mock.AsyncMock(),
            ),
            unittest.mock.patch.object(
                claude_service_module,
                "_store_story_workspace_output_sync",
                side_effect=RuntimeError("injected store failure"),
            ),
            self.assertLogs(claude_service_module.logger, level="ERROR") as logs,
        ):
            await service.execute_session(execution)

        frames = []
        while not queue.empty():
            frames.append(queue.get_nowait())
        events = [frame for frame in frames if isinstance(frame, NormalizedAgentEvent)]
        self.assertIn("message-final", [event.type for event in events])
        self.assertIn("finish", [event.type for event in events])
        terminal = next(event for event in events if event.type == "finish")
        self.assertEqual(terminal.data.get("finishReason"), "stop")
        self.assertNotIn("error", [event.type for event in events])
        self.assertIsNone(frames[-1])
        self.assertIn("thread_id=thread-isolation stage=store", "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()
