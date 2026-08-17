# [Input] database.save_preferences with a recording PostgreSQL connection boundary.
# [Output] Fast regression for the atomic, field-preserving preference upsert.
# [Pos] database preference contract test in backend/tests
# [Sync] 2026-08-14: prevent first-login SELECT/INSERT races and preserve empty JSON.

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import database


class _RecordingConnection:
    def __init__(self) -> None:
        self.executions: list[tuple[str, tuple[object, ...]]] = []
        self.commits = 0
        self.closes = 0

    def execute(self, query: str, parameters: tuple[object, ...]):
        self.executions.append((query, parameters))

    def commit(self) -> None:
        self.commits += 1

    def close(self) -> None:
        self.closes += 1


def test_save_preferences_is_one_atomic_field_preserving_upsert() -> None:
    connection = _RecordingConnection()
    with mock.patch.object(database, "get_db", return_value=connection):
        database.save_preferences(
            7,
            voice_configs={},
            state_config={},
            timezone="Asia/Shanghai",
        )

    assert len(connection.executions) == 1
    query, parameters = connection.executions[0]
    assert query.lstrip().upper().startswith("INSERT INTO USER_PREFERENCES")
    assert "ON CONFLICT (user_id) DO UPDATE" in query
    assert "COALESCE(EXCLUDED.timezone, user_preferences.timezone)" in query
    assert parameters == (7, "{}", None, "{}", None, "Asia/Shanghai")
    assert connection.commits == 1
    assert connection.closes == 1
