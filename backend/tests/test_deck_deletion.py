"""Deck deletion transaction and route regressions.

[Input] Owned Deck rows, related Chat threads, mutable plugin refs/bindings, and immutable runtime snapshots.
[Output] Verify ordered transactional cleanup, rollback, ownership, and HTTP 409 mapping.
[Pos] Focused Deck deletion tests in backend/tests.
[Sync] 2026-08-16: cover plugin-ref cleanup and fail-closed dependency conflicts.
[Sync] 2026-08-17: separate related-thread conflicts from unused bindings and immutable snapshots.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from psycopg.errors import ForeignKeyViolation

import database
from routers import voices as voices_router


class _Result:
    def __init__(self, row=None) -> None:
        self.row = row

    def fetchone(self):
        return self.row


class _Connection:
    def __init__(
        self,
        *,
        owner_id: int = 28,
        child_deck: bool = False,
        related_threads: bool = False,
        runtime_history: bool = False,
        foreign_key_failure: bool = False,
    ) -> None:
        self.owner_id = owner_id
        self.child_deck = child_deck
        self.related_threads = related_threads
        self.runtime_history = runtime_history
        self.foreign_key_failure = foreign_key_failure
        self.executions: list[tuple[str, tuple[object, ...]]] = []
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def execute(self, statement: str, parameters=()) -> _Result:
        normalized = " ".join(statement.split())
        params = tuple(parameters)
        self.executions.append((normalized, params))
        if normalized.startswith("SELECT owner_id FROM decks"):
            return _Result({"owner_id": self.owner_id})
        if normalized.startswith("SELECT 1 FROM decks WHERE parent_id"):
            return _Result({"?column?": 1} if self.child_deck else None)
        if normalized.startswith("SELECT 1 FROM chat_thread"):
            return _Result({"?column?": 1} if self.related_threads else None)
        if normalized.startswith("SELECT 1 FROM deck_runtime_snapshots"):
            return _Result({"?column?": 1} if self.runtime_history else None)
        if normalized == "DELETE FROM decks WHERE id = %s" and self.foreign_key_failure:
            raise ForeignKeyViolation("unexpected Deck reference")
        return _Result()

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def test_delete_deck_removes_mutable_refs_before_owned_deck(monkeypatch) -> None:
    connection = _Connection()
    monkeypatch.setattr(database, "get_db", lambda: connection)

    assert database.delete_deck(28, "deck-a") is True

    statements = [statement for statement, _ in connection.executions]
    assert statements[0] == "SELECT owner_id FROM decks WHERE id = %s FOR UPDATE"
    assert statements.index(
        "DELETE FROM deck_claude_plugin_refs WHERE deck_id = %s"
    ) < statements.index("DELETE FROM decks WHERE id = %s")
    assert statements.index(
        "DELETE FROM deck_plugin_bindings WHERE deck_id = %s"
    ) < statements.index("DELETE FROM decks WHERE id = %s")
    assert connection.committed is True
    assert connection.rolled_back is False
    assert connection.closed is True


@pytest.mark.parametrize(
    ("connection", "reason"),
    [
        (_Connection(child_deck=True), "child_decks"),
        (_Connection(related_threads=True), "related_threads"),
        (_Connection(runtime_history=True), "runtime_history"),
    ],
)
def test_delete_deck_preserves_business_dependencies(
    monkeypatch,
    connection: _Connection,
    reason: str,
) -> None:
    monkeypatch.setattr(database, "get_db", lambda: connection)

    with pytest.raises(database.DeckDeletionConflict) as caught:
        database.delete_deck(28, "deck-a")

    assert caught.value.reason == reason
    assert not any(statement.startswith("DELETE FROM") for statement, _ in connection.executions)
    assert connection.committed is False
    assert connection.rolled_back is True
    assert connection.closed is True


def test_delete_deck_rejects_non_owner_without_mutation(monkeypatch) -> None:
    connection = _Connection(owner_id=29)
    monkeypatch.setattr(database, "get_db", lambda: connection)

    assert database.delete_deck(28, "deck-a") is False
    assert not any(statement.startswith("DELETE FROM") for statement, _ in connection.executions)
    assert connection.committed is False
    assert connection.closed is True


def test_delete_deck_classifies_unexpected_foreign_key_as_conflict(monkeypatch) -> None:
    connection = _Connection(foreign_key_failure=True)
    monkeypatch.setattr(database, "get_db", lambda: connection)

    with pytest.raises(database.DeckDeletionConflict) as caught:
        database.delete_deck(28, "deck-a")

    assert caught.value.reason == "referenced_records"
    assert connection.committed is False
    assert connection.rolled_back is True
    assert connection.closed is True


def test_delete_route_maps_related_thread_conflict_to_409(monkeypatch) -> None:
    monkeypatch.setattr(
        voices_router.database,
        "delete_deck",
        lambda _user_id, _deck_id: (_ for _ in ()).throw(
            database.DeckDeletionConflict("related_threads")
        ),
    )

    with pytest.raises(HTTPException) as caught:
        voices_router.delete_deck("deck-a", {"user_id": 28})

    assert caught.value.status_code == 409
    assert caught.value.detail == "Deck cannot be deleted while related Chat conversations still exist."
