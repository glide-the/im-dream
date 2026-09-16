# [Sync] 2026-09-16: remove the integration-only EventEmitter path after production retirement.

"""Opt-in real PostgreSQL checks for migrated Dream runtime SQL.

These tests never consult ``DATABASE_URL``.  They run only when the caller
provides the exact, explicitly owned empty database through
``TEST_DATABASE_URL``.  Service-level commits are represented by savepoints
inside one rollback-only outer transaction, so no test data is published.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any

import psycopg
import pytest
from psycopg import sql
from psycopg.pq import TransactionStatus
from psycopg.rows import dict_row

from backend.persistence.config import require_test_database_target
from backend.services.story_workspace.dream_reentry_service import (
    StoryWorkspaceDreamReentryService,
)

_CORE_EMPTY_TABLES = (
    "users",
    "story_workspace_workspaces",
    "deck_plugin_installations",
    "workflow_preflights",
    "workflow_runs",
    "chat_thread",
    "chat_message",
    "events",
    "decks",
    "voices",
)
_FORBIDDEN_MUTATION = re.compile(
    r"^\s*(?:DROP|TRUNCATE|DELETE)\b",
    re.IGNORECASE,
)


def _row_counts(connection: psycopg.Connection[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in _CORE_EMPTY_TABLES:
        relation = connection.execute(
            "SELECT to_regclass(%s) AS relation",
            (f"public.{table}",),
        ).fetchone()
        assert relation is not None and relation["relation"] is not None, table
        row = connection.execute(
            sql.SQL("SELECT COUNT(*) AS count FROM {}").format(
                sql.Identifier(table)
            )
        ).fetchone()
        assert row is not None
        counts[table] = int(row["count"])
    return counts


class _RollbackOnlyServiceConnection:
    """Run service transactions as savepoints under an outer test rollback."""

    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection
        self._savepoint: str | None = None
        self._sequence = 0

    @property
    def in_transaction(self) -> bool:
        # Services care about their own clean boundary, not the test's outer
        # rollback-only transaction.
        return self._savepoint is not None

    def begin_service_scope(self) -> None:
        if self._savepoint is not None:
            raise RuntimeError("nested service transaction is not supported")
        self._sequence += 1
        self._savepoint = f"runtime_service_{self._sequence}"
        self._connection.execute(
            sql.SQL("SAVEPOINT {}").format(sql.Identifier(self._savepoint))
        )

    def execute(self, query: Any, parameters: Any = None) -> Any:
        rendered = str(query).strip()
        if _FORBIDDEN_MUTATION.match(rendered):
            raise AssertionError("destructive SQL is forbidden in this integration test")
        if rendered.upper() == "BEGIN":
            self.begin_service_scope()
            return None
        if parameters is None:
            return self._connection.execute(query)
        return self._connection.execute(query, parameters)

    def commit(self) -> None:
        savepoint = self._required_savepoint()
        self._connection.execute(
            sql.SQL("RELEASE SAVEPOINT {}").format(sql.Identifier(savepoint))
        )
        self._savepoint = None

    def rollback(self) -> None:
        savepoint = self._required_savepoint()
        self._connection.execute(
            sql.SQL("ROLLBACK TO SAVEPOINT {}").format(sql.Identifier(savepoint))
        )
        self._connection.execute(
            sql.SQL("RELEASE SAVEPOINT {}").format(sql.Identifier(savepoint))
        )
        self._savepoint = None

    def close(self) -> None:
        # Legacy database helpers own/close their connection.  The integration
        # fixture owns the real PostgreSQL connection and rolls it back after
        # every test, so expose the same interface without closing it early.
        return None

    def _required_savepoint(self) -> str:
        if self._savepoint is None:
            raise RuntimeError("service transaction has not started")
        return self._savepoint


@dataclass
class _PostgresCase:
    connection: psycopg.Connection[Any]
    observer: psycopg.Connection[Any]
    db: _RollbackOnlyServiceConnection
    expected_rows_before_rollback: dict[str, int] = field(
        default_factory=lambda: dict.fromkeys(_CORE_EMPTY_TABLES, 0)
    )

    def expect_rows(self, **counts: int) -> None:
        unknown = set(counts) - set(_CORE_EMPTY_TABLES)
        assert not unknown
        self.expected_rows_before_rollback.update(counts)


@pytest.fixture
def postgres_case() -> Any:
    if os.environ.get("TEST_DATABASE_URL") is None:
        pytest.skip("set the explicit TEST_DATABASE_URL to run real PostgreSQL checks")
    target = require_test_database_target()
    test_database_url = target.dsn

    observer = psycopg.connect(
        test_database_url,
        autocommit=True,
        row_factory=dict_row,
    )
    connection = psycopg.connect(
        test_database_url,
        autocommit=False,
        row_factory=dict_row,
    )
    wrapper = _RollbackOnlyServiceConnection(connection)
    expected_empty = dict.fromkeys(_CORE_EMPTY_TABLES, 0)
    try:
        identity = observer.execute(
            "SELECT current_database() AS database_name"
        ).fetchone()
        assert identity is not None
        assert identity["database_name"] == target.database_name
        assert _row_counts(observer) == expected_empty

        connection.execute("BEGIN")
        case = _PostgresCase(connection, observer, wrapper)
        yield case

        if wrapper.in_transaction:
            wrapper.rollback()
        if connection.info.transaction_status is not TransactionStatus.INERROR:
            assert _row_counts(connection) == case.expected_rows_before_rollback
        connection.rollback()
        assert _row_counts(observer) == expected_empty
    finally:
        if wrapper.in_transaction:
            wrapper.rollback()
        connection.rollback()
        connection.close()
        observer.close()


def test_dream_reentry_jsonb_queries_execute_on_real_postgres(
    postgres_case: _PostgresCase,
) -> None:
    rows = StoryWorkspaceDreamReentryService._query_authorized_rows(
        postgres_case.db,
        7,
    )
    assert rows == []

    facts = StoryWorkspaceDreamReentryService._confirmation_facts(
        postgres_case.db,
        [{"thread_id": "missing-thread", "run_id": "missing-run"}],
        7,
    )
    assert facts == {"missing-run": (False, False)}
    assert _row_counts(postgres_case.connection) == dict.fromkeys(
        _CORE_EMPTY_TABLES,
        0,
    )
