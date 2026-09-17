# [Input] Consume backend/session_events.py and backend/routers/sessions.py.
# [Output] Verify Edit Session event bus user isolation, browser SSE payloads, and route event publication.
# [Pos] test node in backend/tests
# [Sync] 2026-09-15: verify API update publication through production auth/DTO transport after confirmed Admin persistence.
# [Sync] 2026-06-14: add tests for Edit Session event-driven sync bus.

from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from session_events import EditSessionEvent, SessionEventBus
from routers import sessions as sessions_router
from tests._admin_session_fixture import build_session_boundary, editor_state


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


class TestSessionEventBus(unittest.TestCase):
    def test_publish_is_user_scoped(self):
        async def scenario():
            bus = SessionEventBus()
            user_one = await bus.subscribe("1")
            user_two = await bus.subscribe("2")

            await bus.publish(
                EditSessionEvent(
                    type="session_updated",
                    session_id="session-1",
                    user_id="1",
                    source="agent",
                    tool_call_id="tool-1",
                )
            )

            event = await asyncio.wait_for(user_one.get(), timeout=1.0)
            self.assertEqual(event.session_id, "session-1")
            self.assertTrue(user_two.empty())

            await bus.unsubscribe("1", user_one)
            await bus.unsubscribe("2", user_two)

        _run(scenario())

    def test_sse_frame_uses_browser_field_names(self):
        event = EditSessionEvent(
            type="session_updated",
            session_id="session-1",
            user_id="1",
            source="agent",
            tool_call_id="tool-1",
            tool_name="mcp__editor__write_segment",
            timestamp="2026-06-14T00:00:00Z",
        )

        frame = event.to_sse_frame()

        self.assertTrue(frame.startswith("event: session_updated\n"))
        data_line = next(line for line in frame.splitlines() if line.startswith("data: "))
        payload = json.loads(data_line[len("data: "):])
        self.assertEqual(payload["type"], "session_updated")
        self.assertEqual(payload["sessionId"], "session-1")
        self.assertEqual(payload["toolCallId"], "tool-1")
        self.assertEqual(payload["toolName"], "mcp__editor__write_segment")
        self.assertNotIn("user_id", payload)
        self.assertNotIn("session_id", payload)


class TestSessionRouteEvents(unittest.TestCase):
    def test_save_session_publishes_api_update_event(self):
        async def scenario():
            bus = SessionEventBus()
            app, calls, _ = build_session_boundary(user_id="9")
            subscription = await bus.subscribe("9")
            try:
                with mock.patch.object(sessions_router, "session_event_bus", bus):
                    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://dream.example") as client:
                        response = await client.post("/api/sessions", headers={"authorization": "Bearer write-token"}, json={
                            "session_id": "session-1", "name": "Session API", "editor_state": editor_state(),
                        })
                    self.assertEqual(response.status_code, 200)
                    result = response.json()

                event = await asyncio.wait_for(subscription.get(), timeout=1.0)
            finally:
                await bus.unsubscribe("9", subscription)

            self.assertEqual(result, {"success": True})
            self.assertEqual(
                calls[0][0:2],
                ("session.save", {"session_id": "session-1", "editor_state": editor_state(), "name": "Session API", "labels": None, "created_at": None}),
            )
            self.assertEqual(event.type, "session_updated")
            self.assertEqual(event.session_id, "session-1")
            self.assertEqual(event.source, "api")

        _run(scenario())


if __name__ == "__main__":
    unittest.main()
