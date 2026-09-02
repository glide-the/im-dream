# [Input] PostgreSQL-style chat_message rows and stable keyset boundaries.
# [Output] Provider-free query/ordering contract for newest and older message pages.
# [Pos] Backend database pagination regression seam; performs no schema mutation.
# [Sync] 2026-09-02: align both stable sort keys with the exact Admin 0042 index order.

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database


class _Rows:
    def __init__(
        self,
        rows: list[dict],
        *,
        row_batches: list[list[dict]] | None = None,
    ) -> None:
        self.rows = rows
        self.row_batches = list(row_batches or [])
        self.query = ""
        self.params: tuple[object, ...] = ()
        self.queries: list[str] = []
        self.params_history: list[tuple[object, ...]] = []
        self.closed = False

    def execute(self, query: str, params: tuple[object, ...]):
        self.query = " ".join(query.split())
        self.params = params
        self.queries.append(self.query)
        self.params_history.append(params)
        return self

    def fetchall(self) -> list[dict]:
        if self.row_batches:
            return self.row_batches.pop(0)
        return self.rows

    def fetchone(self) -> dict | None:
        return self.rows[0] if self.rows else None

    def close(self) -> None:
        self.closed = True


def _row(message_id: str, created_at: datetime | None, text: str) -> dict:
    return {
        "id": message_id,
        "role": "assistant",
        "parts": json.dumps([{"type": "text", "text": text}]),
        "metadata": json.dumps({"turnId": f"turn-{message_id}"}),
        "created_at": created_at,
    }


def test_newest_page_reverses_database_order_and_reads_limit_plus_one() -> None:
    instant = datetime(2026, 9, 2, 7, 0, tzinfo=timezone.utc)
    cursor = _Rows([
        _row("c", instant, "newest"),
        _row("b", instant, "middle"),
        _row("a", instant, "older"),
    ])
    with patch.object(database, "get_db", return_value=cursor):
        page = database.list_chat_message_page("thread-1", 2)

    assert [message["id"] for message in page["messages"]] == ["b", "c"]
    assert page["messages"][0]["parts"][0]["text"] == "middle"
    assert page["has_more"] is True
    assert page["latest_message_id"] == "c"
    assert "ORDER BY created_at DESC NULLS LAST, id DESC NULLS LAST LIMIT %s" in cursor.query
    assert cursor.params == ("thread-1", 3)
    assert cursor.closed is True


def test_nonnull_boundary_uses_index_tuple_then_null_tail_without_offset() -> None:
    boundary = datetime(2026, 9, 2, 7, 0, tzinfo=timezone.utc)
    cursor = _Rows([], row_batches=[[], []])
    with patch.object(database, "get_db", return_value=cursor):
        page = database.list_chat_message_page(
            "thread-1",
            20,
            before_created_at=boundary,
            before_id="message-b",
        )

    assert page["messages"] == []
    assert "(created_at, id) < (%s, %s)" in cursor.queries[0]
    assert "created_at IS NULL" in cursor.queries[1]
    assert cursor.params_history == [
        ("thread-1", boundary, "message-b", 21),
        ("thread-1", 21),
    ]
    assert all("OFFSET" not in query.upper() for query in cursor.queries)


def test_nonnull_boundary_fills_remaining_page_from_legacy_null_tail() -> None:
    boundary = datetime(2026, 9, 2, 7, 0, tzinfo=timezone.utc)
    nonnull = _row("b", boundary.replace(hour=6), "older-nonnull")
    null_peer = _row("a", None, "legacy-null")
    cursor = _Rows([], row_batches=[[nonnull], [null_peer]])
    with patch.object(database, "get_db", return_value=cursor):
        page = database.list_chat_message_page(
            "thread-1",
            2,
            before_created_at=boundary,
            before_id="message-c",
        )

    assert [message["id"] for message in page["messages"]] == ["a", "b"]
    assert page["has_more"] is False
    assert cursor.params_history[-1] == ("thread-1", 2)


def test_null_boundary_continues_only_with_null_timestamp_and_stable_id() -> None:
    cursor = _Rows([_row("a", None, "legacy-null")])
    with patch.object(database, "get_db", return_value=cursor):
        page = database.list_chat_message_page(
            "thread-1",
            1,
            before_id="message-b",
            before_created_at_is_null=True,
        )

    assert [message["id"] for message in page["messages"]] == ["a"]
    assert "created_at IS NULL AND id < %s" in cursor.query
    assert cursor.params == ("thread-1", "message-b", 2)


def test_invalid_boundary_fails_before_opening_database() -> None:
    with patch.object(database, "get_db") as get_db:
        with pytest.raises(ValueError, match="timestamp kind"):
            database.list_chat_message_page("thread-1", 20, before_id="message-b")
    get_db.assert_not_called()


def test_latest_probe_selects_only_id_with_same_stable_order() -> None:
    cursor = _Rows([{"id": "message-latest"}])
    with patch.object(database, "get_db", return_value=cursor):
        latest = database.get_latest_chat_message_id("thread-1")

    assert latest == "message-latest"
    assert cursor.query.startswith("SELECT id FROM chat_message")
    assert "parts" not in cursor.query
    assert "ORDER BY created_at DESC NULLS LAST, id DESC NULLS LAST LIMIT 1" in cursor.query
