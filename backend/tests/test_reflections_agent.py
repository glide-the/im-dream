# [Input] Reflections router, Reflections-agent engine, and database helpers.
# [Output] Functional tests for Reflections-agent task persistence, execution,
#          results, events, and API endpoints.
# [Pos] test node in backend/tests
# [Sync] 2026-06-25: add first-release Reflections-agent functional coverage.

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import auth
import database
from reflections_agent import ReflectionsTaskEngine, create_reflections_task, get_or_create_reflection_event_bus
from routers import deps as router_deps
from routers.reflections import router as reflections_router


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


class ReflectionsAgentFunctionalTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db_path = database.DB_PATH
        self.old_agent_cwd = os.environ.get("AGENT_CWD")
        database.DB_PATH = Path(self.tmp.name) / "ink-test.db"
        os.environ["AGENT_CWD"] = str(Path(self.tmp.name) / "agent-workspace")
        database.init_db()
        self.user_id = database.create_user(
            "reflections-agent@example.com",
            auth.hash_password("secret123"),
            "Reflections Agent",
        )
        database.save_session(
            self.user_id,
            "session-a",
            {"cells": [{"type": "text", "content": "I keep returning to the same worry about creative work and courage."}]},
            name="Entry A",
            created_at="2026-06-01 10:00:00",
        )
        database.save_session(
            self.user_id,
            "session-b",
            {"cells": [{"type": "text", "content": "Today I noticed another pattern: I reflect before acting and then write it down."}]},
            name="Entry B",
            created_at="2026-06-02 10:00:00",
        )

    def tearDown(self) -> None:
        database.DB_PATH = self.old_db_path
        if self.old_agent_cwd is None:
            os.environ.pop("AGENT_CWD", None)
        else:
            os.environ["AGENT_CWD"] = self.old_agent_cwd
        self.tmp.cleanup()

    def test_task_engine_persists_results_and_events(self):
        task_id = create_reflections_task(self.user_id, ["echoes", "traits"], {})
        _run(ReflectionsTaskEngine().run(task_id))

        task = database.get_reflection_task(task_id, self.user_id)
        self.assertIsNotNone(task)
        self.assertEqual(task["status"], "COMPLETED")
        self.assertTrue(task["workspace_path"])

        results = database.list_reflection_results(task_id, self.user_id)
        self.assertEqual({r["section"] for r in results}, {"echoes", "traits"})
        self.assertTrue(all(r["related_session_ids"] for r in results))

        events = database.list_reflection_task_events(task_id, self.user_id)
        event_types = [event["event_type"] for event in events]
        self.assertIn("reflection.context.ready", event_types)
        self.assertIn("reflection.task.completed", event_types)

    def test_event_bus_replays_events_after_subscribe(self):
        async def _case():
            task_id = database.create_reflection_task(self.user_id, ["echoes"], {})
            bus = await get_or_create_reflection_event_bus(task_id)
            first = await bus.publish("reflection.task.started", {"started_at": "now"})
            await bus.publish("reflection.section.completed", {"section": "echoes", "result_count": 1})
            token = await bus.subscribe(first.id)
            replayed = []
            reader = bus.read(token)
            try:
                event = await anext(reader)
                replayed.append(event.type)
            finally:
                await reader.aclose()
                await bus.unsubscribe(token)
            self.assertEqual(replayed, ["reflection.section.completed"])

        _run(_case())

    def test_router_creates_task_and_exposes_results(self):
        app = FastAPI()
        app.include_router(reflections_router)
        app.dependency_overrides[router_deps.get_current_user] = lambda: {"user_id": self.user_id}

        with TestClient(app) as client:
            response = client.post("/api/reflections/tasks", json={"sections": ["echoes"]})
            self.assertEqual(response.status_code, 202, response.text)
            task_id = response.json()["task_id"]

            task_payload = None
            for _ in range(50):
                task_response = client.get(f"/api/reflections/tasks/{task_id}")
                self.assertEqual(task_response.status_code, 200, task_response.text)
                task_payload = task_response.json()
                if task_payload["status"] in {"COMPLETED", "PARTIAL_FAILED", "FAILED"}:
                    break
                time.sleep(0.05)

            self.assertIsNotNone(task_payload)
            self.assertEqual(task_payload["status"], "COMPLETED")

            results_response = client.get(f"/api/reflections/tasks/{task_id}/results")
            self.assertEqual(results_response.status_code, 200, results_response.text)
            results = results_response.json()["results"]
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["section"], "echoes")

            latest_response = client.get("/api/reflections/latest")
            self.assertEqual(latest_response.status_code, 200, latest_response.text)
            self.assertEqual(latest_response.json()["task"]["task_id"], task_id)


    def test_all_sections_use_frontend_language(self):
        app = FastAPI()
        app.include_router(reflections_router)
        app.dependency_overrides[router_deps.get_current_user] = lambda: {"user_id": self.user_id}

        with TestClient(app) as client:
            response = client.post(
                "/api/reflections/tasks",
                json={"sections": ["echoes", "traits", "patterns"], "language": "zh-CN"},
            )
            self.assertEqual(response.status_code, 202, response.text)
            task_id = response.json()["task_id"]

            task_payload = None
            for _ in range(50):
                task_response = client.get(f"/api/reflections/tasks/{task_id}")
                self.assertEqual(task_response.status_code, 200, task_response.text)
                task_payload = task_response.json()
                if task_payload["status"] in {"COMPLETED", "PARTIAL_FAILED", "FAILED"}:
                    break
                time.sleep(0.05)

            self.assertIsNotNone(task_payload)
            self.assertEqual(task_payload["input_snapshot"]["language"], "zh")

            results_response = client.get(f"/api/reflections/tasks/{task_id}/results")
            self.assertEqual(results_response.status_code, 200, results_response.text)
            results = results_response.json()["results"]
            by_section = {result["section"]: result for result in results}
            self.assertEqual(set(by_section), {"echoes", "traits", "patterns"})
            self.assertIn("情绪", by_section["echoes"]["title"])
            self.assertIn("自我", by_section["traits"]["title"])
            self.assertIn("写作", by_section["patterns"]["title"])

            task = database.get_reflection_task(task_id, self.user_id)
            for section in ("echoes", "traits", "patterns"):
                prompt_path = Path(task["workspace_path"]) / section / "MEMORY_ANSWER_PROMPT.md"
                prompt = prompt_path.read_text(encoding="utf-8")
                self.assertIn("Runtime Language Requirement", prompt)
                self.assertIn("Simplified Chinese", prompt)

    def test_router_can_create_without_autostart_then_start(self):
        app = FastAPI()
        app.include_router(reflections_router)
        app.dependency_overrides[router_deps.get_current_user] = lambda: {"user_id": self.user_id}

        with TestClient(app) as client:
            response = client.post(
                "/api/reflections/tasks",
                json={"sections": ["echoes"], "auto_start": False},
            )
            self.assertEqual(response.status_code, 202, response.text)
            task_id = response.json()["task_id"]
            created = database.get_reflection_task(task_id, self.user_id)
            self.assertEqual(created["status"], "CREATED")

            start_response = client.post(f"/api/reflections/tasks/{task_id}/start")
            self.assertEqual(start_response.status_code, 202, start_response.text)

            for _ in range(50):
                task = database.get_reflection_task(task_id, self.user_id)
                if task["status"] in {"COMPLETED", "PARTIAL_FAILED", "FAILED"}:
                    break
                time.sleep(0.05)

            self.assertEqual(database.get_reflection_task(task_id, self.user_id)["status"], "COMPLETED")
            events = database.list_reflection_task_events(task_id, self.user_id)
            self.assertIn("reflection.task.started", [event["event_type"] for event in events])


if __name__ == "__main__":
    unittest.main()
