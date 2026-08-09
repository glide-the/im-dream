"""Opt-in real PostgreSQL checks for migrated Dream runtime SQL.

These tests never consult ``DATABASE_URL``.  They run only when the caller
provides the exact, explicitly owned empty database through
``TEST_DATABASE_URL``.  Service-level commits are represented by savepoints
inside one rollback-only outer transaction, so no test data is published.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
import os
import re
from typing import Any

import psycopg
from psycopg import sql
from psycopg.pq import TransactionStatus
from psycopg.rows import dict_row
import pytest

from backend.models.deck_plugin import InstallationStatus
from backend.models.events import CanonicalEventType, EventEnvelope
from backend.services.deck_plugin.installation_service import InstallationService
from backend.services.events.event_emitter import EventEmitter
from backend.services.story_workspace.dream_reentry_service import (
    StoryWorkspaceDreamReentryService,
)


_EXPECTED_TEST_DATABASE_URL = (
    "postgresql://postgres@127.0.0.1:55439/"
    "ink_memory_dream_empty_codex_test"
)
_EXPECTED_DATABASE_NAME = "ink_memory_dream_empty_codex_test"
_INSTALLATION_ID = "dpi_11111111111111111111111111111111"
_CORE_EMPTY_TABLES = (
    "users",
    "story_workspace_workspaces",
    "deck_plugin_installations",
    "workflow_preflights",
    "workflow_runs",
    "chat_thread",
    "chat_message",
    "events",
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
    test_database_url = os.environ.get("TEST_DATABASE_URL")
    if test_database_url is None:
        pytest.skip("set the explicit TEST_DATABASE_URL to run real PostgreSQL checks")
    assert test_database_url == _EXPECTED_TEST_DATABASE_URL

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
        assert identity["database_name"] == _EXPECTED_DATABASE_NAME
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


def test_event_emitter_is_append_only_and_retry_idempotent_on_postgres(
    postgres_case: _PostgresCase,
) -> None:
    postgres_case.expect_rows(events=1)
    queued: list[EventEnvelope] = []
    projections: list[dict[str, Any]] = []
    emitter = EventEmitter(
        postgres_case.db,
        workspace_id="workspace-pg-runtime-test",
        queue_publisher=queued.append,
        projection_publisher=projections.append,
        clock=lambda: datetime(2026, 8, 9, 8, 0, tzinfo=UTC),
    )
    envelope = emitter.build_envelope(
        CanonicalEventType.WORKFLOW_RUN_STEP_PROGRESSED,
        "run-pg-runtime-test",
        {
            "workflow_run_id": "run-pg-runtime-test",
            "step_id": "draft",
            "progress": 0.5,
            "safe_summary": "PostgreSQL boundary verified",
        },
        "correlation-pg-runtime-test",
    )

    asyncio.run(emitter.emit(envelope))

    postgres_case.db.begin_service_scope()
    try:
        with pytest.raises(psycopg.Error) as append_only_error:
            postgres_case.db.execute(
                "UPDATE events SET correlation_id = %s WHERE event_id = %s",
                ("forbidden-rewrite", envelope.event_id),
            )
        assert append_only_error.value.sqlstate == "55000"
    finally:
        if postgres_case.db.in_transaction:
            postgres_case.db.rollback()

    asyncio.run(emitter.emit(envelope))

    row = postgres_case.db.execute(
        "SELECT event_id, aggregate_version, occurred_at "
        "FROM events WHERE event_id = %s",
        (envelope.event_id,),
    ).fetchone()
    assert row is not None
    assert row["event_id"] == envelope.event_id
    assert row["aggregate_version"] == 1
    assert isinstance(row["occurred_at"], datetime)
    assert queued == [envelope, envelope]
    assert [item["event_id"] for item in projections] == [
        envelope.event_id,
        envelope.event_id,
    ]


def test_plugin_installation_service_commits_inside_outer_rollback(
    postgres_case: _PostgresCase,
) -> None:
    postgres_case.expect_rows(deck_plugin_installations=1)
    postgres_case.db.execute(
        """
        INSERT INTO deck_plugin_installations (
            id, scope_type, scope_id, deck_plugin_id,
            installed_versions_json, default_version, status,
            approved_capabilities_json, source_policy_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            _INSTALLATION_ID,
            "workspace",
            "workspace-pg-runtime-test",
            "plugin.pg-runtime-test",
            '["1.0.0"]',
            "1.0.0",
            InstallationStatus.DISABLED.value,
            "[]",
            "test-policy",
        ),
    )

    service = InstallationService(postgres_case.db)
    postgres_case.db.begin_service_scope()
    result = asyncio.run(service.enable(_INSTALLATION_ID))

    row = postgres_case.db.execute(
        "SELECT status, revision FROM deck_plugin_installations WHERE id = %s",
        (_INSTALLATION_ID,),
    ).fetchone()
    assert result.status is InstallationStatus.READY
    assert row == {"status": InstallationStatus.READY.value, "revision": 1}
    assert _row_counts(postgres_case.observer)["deck_plugin_installations"] == 0


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
