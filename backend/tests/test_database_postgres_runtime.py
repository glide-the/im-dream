"""Opt-in, rollback-only contract for Dream's PostgreSQL runtime helpers."""

from __future__ import annotations

import os
from types import SimpleNamespace
from uuid import uuid4

import pytest
from psycopg.pq import TransactionStatus

import database
from persistence.config import require_test_database_url


class _RollbackOnlyLease:
    """Share one real transaction while suppressing helper-level commit/close."""

    def __init__(self, lease) -> None:
        self._lease = lease

    def __getattr__(self, name: str):
        return getattr(self._lease, name)

    def commit(self) -> None:
        return None

    def close(self) -> None:
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        if exc_type is not None:
            self._lease.rollback()
        return False


def _owned_database_url() -> str:
    if os.environ.get("INK_RUN_DATABASE_RUNTIME_PG_TEST") != "1":
        pytest.skip("set INK_RUN_DATABASE_RUNTIME_PG_TEST=1 for the owned PostgreSQL contract")
    expected = os.environ.get("INK_EXPECTED_TEST_DATABASE")
    if not expected:
        pytest.skip("INK_EXPECTED_TEST_DATABASE must name the disposable database exactly")
    return require_test_database_url(expected)


def test_runtime_helpers_execute_on_postgres_and_rollback(monkeypatch) -> None:
    test_url = _owned_database_url()
    monkeypatch.setenv("DATABASE_URL", test_url)
    database.close_db()

    real_lease = database.get_db()
    rollback_lease = _RollbackOnlyLease(real_lease)
    original_get_db = database.get_db
    database.get_db = lambda: rollback_lease
    suffix = uuid4().hex

    try:
        user_id = database.create_user(
            f"pg-runtime-{suffix}@ink-memory.test",
            "non-secret-test-hash",
            "PostgreSQL Runtime",
        )
        assert database.get_user_by_id(user_id)["email"].startswith("pg-runtime-")

        database.save_preferences(
            user_id,
            voice_configs={"runtime": "postgresql"},
            timezone="Asia/Shanghai",
        )
        assert database.get_preferences(user_id)["timezone"] == "Asia/Shanghai"

        session_id = f"pg-session-{suffix}"
        database.save_session(
            user_id,
            session_id,
            {"cells": [{"type": "text", "content": "PostgreSQL runtime"}]},
            name="PG runtime",
            labels=["postgresql"],
        )
        assert database.get_session(user_id, session_id)["labels"] == ["postgresql"]
        assert database.get_sessions_batch(user_id, [session_id])[0]["editor_state"]
        assert database.list_sessions_in_range(user_id, None, None, include_text=True)[0][
            "text"
        ] == "PostgreSQL runtime"
        database.save_daily_picture(
            user_id,
            "2026-08-09",
            "data:image/png;base64,postgresql-runtime",
            prompt="PostgreSQL range",
        )
        assert database.get_daily_pictures_range(
            user_id,
            "2026-08-09",
            "2026-08-09",
        )[0]["prompt"] == "PostgreSQL range"

        thread_id = database.create_chat_thread(user_id, title="PostgreSQL chat")
        message_id = f"pg-message-{suffix}"
        database.save_chat_message(
            thread_id,
            "user",
            [{"type": "text", "text": "hello"}],
            message_id=message_id,
            metadata={"b": 2, "a": 1},
        )
        database.save_chat_message(
            thread_id,
            "user",
            [{"text": "hello", "type": "text"}],
            message_id=message_id,
            metadata={"a": 1, "b": 2},
        )
        with pytest.raises(database.ChatMessageIdentityConflict):
            database.save_chat_message(
                thread_id,
                "assistant",
                [{"type": "text", "text": "reparent attempt"}],
                message_id=message_id,
                metadata={"a": 1, "b": 2},
            )
        assert database.get_chat_thread(thread_id, user_id)["title"] == "PostgreSQL chat"
        messages = database.list_chat_messages(thread_id)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["parts"][0]["text"] == "hello"

        task_id = database.create_reflection_task(
            user_id,
            ["growth"],
            {"source": "postgresql-contract"},
        )
        database.append_reflection_task_event(
            task_id,
            "created",
            {"safe": True},
            sequence=1,
        )
        assert database.get_reflection_task(task_id, user_id)["sections"] == ["growth"]
        assert database.list_reflection_task_events(task_id, user_id)[0]["event_type"] == "created"

        deck_id = database.create_deck(
            user_id,
            "PostgreSQL deck",
            description="Boolean columns use native PostgreSQL values",
        )
        voice_id = database.create_voice(
            user_id,
            deck_id,
            "PostgreSQL voice",
            "Use the PostgreSQL runtime contract.",
        )
        assert database.update_deck(user_id, deck_id, {"enabled": False}) is True
        assert database.update_voice(user_id, voice_id, {"enabled": False}) is True
        deck = database.get_deck_with_voices(user_id, deck_id)
        assert deck is not None
        assert deck["enabled"] is False
        assert deck["has_local_changes"] is False
        assert deck["voices"][0]["enabled"] is False
        assert deck["voices"][0]["has_local_changes"] is False
    finally:
        database.get_db = original_get_db
        real_lease.rollback()
        real_lease.close()
        database.close_db()

    verification = database.get_db()
    try:
        counts = verification.execute(
            """
            SELECT
              (SELECT count(*) FROM users) AS users,
              (SELECT count(*) FROM user_sessions) AS sessions,
              (SELECT count(*) FROM daily_pictures) AS daily_pictures,
              (SELECT count(*) FROM chat_thread) AS threads,
              (SELECT count(*) FROM reflection_task) AS reflection_tasks,
              (SELECT count(*) FROM decks) AS decks,
              (SELECT count(*) FROM voices) AS voices
            """
        ).fetchone()
        assert dict(counts) == {
            "users": 0,
            "sessions": 0,
            "daily_pictures": 0,
            "threads": 0,
            "reflection_tasks": 0,
            "decks": 0,
            "voices": 0,
        }
    finally:
        verification.close()
        database.close_db()


class _FakeConnection:
    def __init__(self, status: TransactionStatus) -> None:
        self.info = SimpleNamespace(transaction_status=status)
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1
        self.info.transaction_status = TransactionStatus.IDLE

    def rollback(self) -> None:
        self.rollbacks += 1
        self.info.transaction_status = TransactionStatus.IDLE


class _FakeRawPool:
    def __init__(self) -> None:
        self.returned: list[_FakeConnection] = []

    def putconn(self, connection: _FakeConnection) -> None:
        self.returned.append(connection)


def test_connection_context_finishes_transaction_without_returning_lease() -> None:
    raw_pool = _FakeRawPool()
    pool = SimpleNamespace(raw_pool=raw_pool)
    connection = _FakeConnection(TransactionStatus.INTRANS)
    lease = database._PooledConnectionLease(pool, connection)

    with lease as entered:
        assert entered is lease

    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert raw_pool.returned == []

    lease.close()
    assert raw_pool.returned == [connection]

    failing_connection = _FakeConnection(TransactionStatus.INTRANS)
    failing_lease = database._PooledConnectionLease(pool, failing_connection)
    with pytest.raises(RuntimeError, match="rollback"):
        with failing_lease:
            raise RuntimeError("rollback")

    assert failing_connection.commits == 0
    assert failing_connection.rollbacks == 1
    assert raw_pool.returned == [connection]
    failing_lease.close()
    assert raw_pool.returned == [connection, failing_connection]
