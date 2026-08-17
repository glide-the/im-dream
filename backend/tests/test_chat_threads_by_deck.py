"""Deck-scoped Chat history list regressions.

[Input] Actor-owned chat_thread rows and the public Claude-thread listing route.
[Output] Verify deck_id filtering stays ownership-scoped and preserves pagination.
[Pos] Related-conversation API contract tests in backend/tests.
[Sync] 2026-08-17: cover Settings / Work related Chat history queries.
"""

from __future__ import annotations

import asyncio

import database
from routers import claude_agent as claude_agent_router


class _Rows:
    def fetchall(self) -> list[dict]:
        return [{
            "id": "thread-a",
            "title": "Related conversation",
            "deck_id": "deck-a",
            "voice_id": "voice-a",
            "created_at": "2026-08-16T00:00:00Z",
            "updated_at": "2026-08-17T00:00:00Z",
        }]


class _Connection:
    def __init__(self) -> None:
        self.execution: tuple[str, tuple[object, ...]] | None = None
        self.closed = False

    def execute(self, statement: str, parameters=()) -> _Rows:
        self.execution = (" ".join(statement.split()), tuple(parameters))
        return _Rows()

    def close(self) -> None:
        self.closed = True


def test_list_chat_threads_filters_owned_rows_by_deck(monkeypatch) -> None:
    connection = _Connection()
    monkeypatch.setattr(database, "get_db", lambda: connection)

    rows = database.list_chat_threads(28, limit=20, offset=0, deck_id="deck-a")

    assert [row["id"] for row in rows] == ["thread-a"]
    assert connection.execution is not None
    statement, parameters = connection.execution
    assert "WHERE user_id = %s AND deck_id = %s" in statement
    assert parameters == (28, "deck-a", 20, 0)
    assert connection.closed is True


def test_thread_route_forwards_deck_filter_without_search(monkeypatch) -> None:
    calls: list[dict] = []

    def list_threads(user_id, *, limit, offset, deck_id):
        calls.append({
            "user_id": user_id,
            "limit": limit,
            "offset": offset,
            "deck_id": deck_id,
        })
        return [{"id": "thread-a", "deck_id": deck_id}]

    monkeypatch.setattr(claude_agent_router.database, "list_chat_threads", list_threads)

    payload = asyncio.run(claude_agent_router.claude_agent_list_threads(
        deck_id="deck-a",
        query=None,
        search_scope="all",
        retrieval_mode=None,
        vector_query=None,
        min_score=None,
        limit=20,
        offset=0,
        current_user={"user_id": 28},
    ))

    assert calls == [{"user_id": 28, "limit": 20, "offset": 0, "deck_id": "deck-a"}]
    assert payload == {"threads": [{"id": "thread-a", "deck_id": "deck-a"}]}
