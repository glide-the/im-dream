#!/usr/bin/env python3
# [Input] Consume writing-session routes with mocked PostgreSQL timestamp rows.
# [Output] Verify timezone-correct date_key projection for datetime and ISO timestamps.
# [Pos] session router contract test in backend/tests
# [Sync] 2026-08-31: cover native PostgreSQL datetime calendar grouping regression.

from datetime import datetime, timezone
import unittest
from unittest import mock

from routers import sessions as sessions_router


class SessionRouterCalendarTest(unittest.TestCase):
    def test_list_sessions_projects_native_postgres_datetimes_to_local_days(self) -> None:
        rows = [
            {
                "id": "aware-datetime",
                "created_at": datetime(2026, 8, 30, 16, 30, tzinfo=timezone.utc),
                "updated_at": datetime(2026, 8, 31, 2, 0, tzinfo=timezone.utc),
            },
            {
                "id": "naive-datetime",
                "created_at": datetime(2026, 8, 29, 16, 30),
                "updated_at": datetime(2026, 8, 30, 2, 0),
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

        with mock.patch.object(
            sessions_router.database,
            "list_sessions",
            return_value=rows,
        ):
            payload = sessions_router.list_sessions(
                timezone="Asia/Shanghai",
                current_user={"user_id": 7},
            )

        self.assertEqual(
            [session["date_key"] for session in payload["sessions"]],
            ["2026-08-31", "2026-08-30", "2026-08-29", None],
        )


if __name__ == "__main__":
    unittest.main()
