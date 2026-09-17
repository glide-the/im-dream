#!/usr/bin/env python3
# [Input] Consume the public Session API with Admin ISO DTOs and the retained timestamp helper.
# [Output] Verify timezone-correct date_key and native-datetime helper compatibility.
# [Pos] session router contract test in backend/tests
# [Sync] 2026-09-15: move the route regression to the public typed Admin boundary; keep native timestamp helper coverage.
# [Sync] 2026-08-31: cover native PostgreSQL datetime calendar grouping regression.

from datetime import datetime, timezone
import unittest
from fastapi.testclient import TestClient

from routers import sessions as sessions_router
from tests._admin_session_fixture import build_session_boundary, preview_session


class SessionRouterCalendarTest(unittest.TestCase):
    def test_list_sessions_projects_admin_timestamps_to_local_days(self) -> None:
        rows = [
            {
                "id": "aware-datetime",
                "created_at": "2026-08-30T16:30:00Z",
                "updated_at": "2026-08-31T02:00:00Z",
            },
            {
                "id": "naive-datetime",
                "created_at": "2026-08-29T16:30:00Z",
                "updated_at": "2026-08-30T02:00:00Z",
            },
            {
                "id": "iso-string",
                "created_at": "2026-08-28T16:30:00Z",
                "updated_at": "2026-08-29T02:00:00Z",
            },
            {
                "id": "undated",
                "created_at": None,
                "updated_at": None,
            },
        ]

        app, _, outputs = build_session_boundary(user_id="7")
        outputs["session.list"] = {"sessions": [{**preview_session(), **row} for row in rows]}
        response = TestClient(app).get("/api/sessions?timezone=Asia/Shanghai", headers={"authorization": "Bearer read-only"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(
            [session["date_key"] for session in payload["sessions"]],
            ["2026-08-31", "2026-08-30", "2026-08-29", None],
        )

    def test_timestamp_helper_keeps_native_postgres_datetime_support(self) -> None:
        aware = datetime(2026, 8, 30, 16, 30, tzinfo=timezone.utc)
        naive = datetime(2026, 8, 30, 16, 30)
        self.assertEqual(sessions_router._clean_timestamp(aware), aware)
        self.assertEqual(sessions_router._clean_timestamp(naive), aware)


if __name__ == "__main__":
    unittest.main()
