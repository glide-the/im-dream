"""Unit tests for PostgreSQL infrastructure; no test opens a database socket."""

from __future__ import annotations

import os
import sys
import unittest
from unittest import mock


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from persistence import (  # noqa: E402
    CatalogExpectations,
    CatalogMismatchError,
    EXPECTED_APPLICATION_COLUMN_COUNT,
    EXPECTED_EXPLICIT_INDEX_COUNT,
    EXPECTED_SOURCE_APPLICATION_COLUMN_COUNT,
    EXPECTED_SOURCE_EXPLICIT_INDEX_COUNT,
    EXPECTED_TARGET_APPLICATION_COLUMN_COUNT,
    EXPECTED_TARGET_EXPLICIT_INDEX_COUNT,
    CheckConstraintError,
    DeadlockError,
    ForeignKeyConstraintError,
    NotNullConstraintError,
    PersistenceTimeoutError,
    PostgresPool,
    PostgresUnitOfWork,
    SerializationFailureError,
    TestDatabaseSafetyError,
    UniqueConstraintError,
    catalog_snapshot,
    check_postgres_health,
    map_postgres_error,
    probe_postgres_health,
    require_test_database_target,
    require_test_database_url,
    validate_test_database_url,
)


class _FakeCursor:
    def __init__(self, *, rows=None, row=None):
        self._rows = list(rows or [])
        self._row = row

    def fetchall(self):
        return list(self._rows)

    def fetchone(self):
        return self._row


class _FakeConnection:
    def __init__(self):
        self.executions = []
        self.commits = 0
        self.rollbacks = 0
        self.execute_error = None

    def execute(self, query, parameters=None):
        self.executions.append((query, parameters))
        if self.execute_error is not None:
            raise self.execute_error
        return _FakeCursor(rows=[])

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class _FakeConnectionManager:
    def __init__(self, connection):
        self.connection = connection
        self.exit_calls = []

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc, traceback):
        self.exit_calls.append((exc_type, exc))
        return False


class _FakePool:
    def __init__(self, connection=None):
        self.connection_value = connection or _FakeConnection()
        self.managers = []
        self.timeouts = []

    def connection(self, timeout=None):
        self.timeouts.append(timeout)
        manager = _FakeConnectionManager(self.connection_value)
        self.managers.append(manager)
        return manager


class TestDatabaseGuardTest(unittest.TestCase):
    def test_test_database_url_is_required_without_production_fallback(self):
        with self.assertRaises(TestDatabaseSafetyError) as raised:
            require_test_database_url(
                environ={"DATABASE_URL": "postgresql://prod:secret@db/ink-memory"}
            )
        self.assertEqual(raised.exception.reason, "test_database_url_missing")
        self.assertNotIn("secret", str(raised.exception))

    def test_only_isolated_postgres_database_names_are_accepted(self):
        rejected = (
            "sqlite:///tmp/ink-test.db",
            "postgresql://local/ink-memory",
            "postgresql://local/customer",
            "postgresql://local/postgres",
            "postgresql://local/template1",
            "postgresql://local/contest",
        )
        for url in rejected:
            with self.subTest(url=url):
                with self.assertRaises(TestDatabaseSafetyError):
                    validate_test_database_url(url)

        for database in ("ink_test_api", "codex-dream", "dream_tmp", "dream-ci"):
            with self.subTest(database=database):
                target = validate_test_database_url(
                    f"postgresql://tester:not-printed@localhost/{database}"
                )
                self.assertEqual(target.database_name, database)
                self.assertNotIn("not-printed", repr(target))
                self.assertNotIn("not-printed", str(target))

    def test_same_normalized_production_target_is_rejected(self):
        with self.assertRaises(TestDatabaseSafetyError) as raised:
            validate_test_database_url(
                "postgresql://test-user:test-password@localhost/ink_test",
                database_url="postgres://prod-user:prod-password@127.0.0.1:5432/ink_test",
            )
        self.assertEqual(raised.exception.reason, "matches_database_url")
        rendered = str(raised.exception)
        self.assertNotIn("test-password", rendered)
        self.assertNotIn("prod-password", rendered)

    def test_expected_database_name_must_match_exactly(self):
        environment = {
            "TEST_DATABASE_URL": "postgresql://localhost/ink_test_worker_7",
            "DATABASE_URL": "postgresql://localhost/ink-memory",
        }
        target = require_test_database_target(
            "ink_test_worker_7",
            environ=environment,
        )
        self.assertEqual(target.database, "ink_test_worker_7")
        with self.assertRaises(TestDatabaseSafetyError) as raised:
            require_test_database_target("ink_test_worker_8", environ=environment)
        self.assertEqual(raised.exception.reason, "unexpected_database_name")
        with self.assertRaises(TestDatabaseSafetyError):
            require_test_database_target("INK_TEST_WORKER_7", environ=environment)

    def test_ambiguous_database_override_in_query_is_rejected(self):
        for override in (
            "dbname=ink-memory",
            "host=production.example",
            "service=production",
        ):
            with self.subTest(override=override):
                with self.assertRaises(TestDatabaseSafetyError):
                    validate_test_database_url(
                        f"postgresql://localhost/ink_test?{override}"
                    )

    def test_unverifiable_postgres_production_target_fails_closed(self):
        with self.assertRaises(TestDatabaseSafetyError) as raised:
            validate_test_database_url(
                "postgresql://localhost/ink_test",
                database_url="postgresql://localhost/ink_test?service=production",
            )
        self.assertEqual(raised.exception.reason, "database_url_unverifiable")

        target = validate_test_database_url(
            "postgresql://localhost/ink_test",
            database_url="sqlite:///legacy.db",
        )
        self.assertEqual(target.database_name, "ink_test")


class _SqlstateError(Exception):
    def __init__(self, sqlstate, unsafe_text):
        self.sqlstate = sqlstate
        super().__init__(unsafe_text)


class PostgresErrorMappingTest(unittest.TestCase):
    def test_constraint_and_concurrency_sqlstates_have_stable_types(self):
        cases = {
            "23505": UniqueConstraintError,
            "23503": ForeignKeyConstraintError,
            "23514": CheckConstraintError,
            "23502": NotNullConstraintError,
            "40001": SerializationFailureError,
            "40P01": DeadlockError,
            "57014": PersistenceTimeoutError,
        }
        for sqlstate, expected_type in cases.items():
            with self.subTest(sqlstate=sqlstate):
                error = map_postgres_error(
                    _SqlstateError(
                        sqlstate,
                        "SELECT secret FROM private; password=hunter2",
                    )
                )
                self.assertIsInstance(error, expected_type)
                self.assertNotIn("SELECT", str(error))
                self.assertNotIn("hunter2", str(error))

    def test_python_timeout_is_retryable_and_redacted(self):
        error = map_postgres_error(TimeoutError("postgresql://u:pw@host/db"))
        self.assertIsInstance(error, PersistenceTimeoutError)
        self.assertTrue(error.retryable)
        self.assertNotIn("pw", str(error))


class _DriverPool:
    def __init__(self, **kwargs):
        self.constructor_kwargs = kwargs
        self.connection_value = _FakeConnection()
        self.open_calls = []
        self.close_calls = []
        self.check_calls = 0

    def open(self, *, wait, timeout):
        self.open_calls.append((wait, timeout))

    def close(self, **kwargs):
        self.close_calls.append(kwargs)

    def connection(self, timeout=None):
        return _FakeConnectionManager(self.connection_value)

    def check(self):
        self.check_calls += 1

    def get_stats(self):
        return {"pool_size": 2}


class PostgresPoolTest(unittest.TestCase):
    def test_pool_is_lazy_configured_and_has_redacted_repr(self):
        captured = {}

        def factory(**kwargs):
            captured.update(kwargs)
            return _DriverPool(**kwargs)

        password = "never-show-this"
        pool = PostgresPool(
            f"postgresql://user:{password}@localhost/ink_memory",
            min_size=0,
            max_size=4,
            pool_factory=factory,
        )
        self.assertFalse(pool.opened)
        self.assertFalse(captured["open"])
        self.assertFalse(captured["kwargs"]["autocommit"])
        self.assertEqual(captured["min_size"], 0)
        self.assertNotIn(password, repr(pool))
        self.assertNotIn(password, repr(pool.config))

        pool.open(timeout=3)
        self.assertTrue(pool.opened)
        self.assertEqual(pool.raw_pool.open_calls, [(True, 3)])
        self.assertEqual(pool.get_stats(), {"pool_size": 2})
        pool.check()
        self.assertEqual(pool.raw_pool.check_calls, 1)
        pool.close()
        self.assertTrue(pool.closed)

    def test_factory_exception_never_surfaces_dsn(self):
        password = "factory-secret"

        def failing_factory(**kwargs):
            raise RuntimeError(kwargs["conninfo"])

        with self.assertRaises(Exception) as raised:
            PostgresPool(
                f"postgresql://user:{password}@localhost/ink_memory",
                pool_factory=failing_factory,
            )
        self.assertNotIn(password, str(raised.exception))

    def test_driver_error_leaving_connection_scope_is_redacted(self):
        pool = PostgresPool(
            dsn="postgresql://user:connection-secret@localhost/ink_memory",
            pool_factory=_DriverPool,
        )
        pool.open()
        with self.assertRaises(UniqueConstraintError) as raised:
            with pool.connection():
                raise _SqlstateError("23505", "INSERT secret SQL")
        self.assertNotIn("secret", str(raised.exception))
        pool.close()


class PostgresUnitOfWorkTest(unittest.TestCase):
    def test_success_without_explicit_commit_rolls_back(self):
        connection = _FakeConnection()
        with PostgresUnitOfWork(_FakePool(connection)) as uow:
            uow.execute("SELECT 1")
        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)

    def test_explicit_commit_publishes_once(self):
        connection = _FakeConnection()
        with PostgresUnitOfWork(_FakePool(connection)) as uow:
            uow.execute("INSERT INTO dreams VALUES (%s)", ("one",))
            uow.commit()
            self.assertTrue(uow.committed)
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)

    def test_exception_rolls_back_and_maps_driver_error(self):
        connection = _FakeConnection()
        pool = _FakePool(connection)
        with self.assertRaises(UniqueConstraintError) as raised:
            with PostgresUnitOfWork(pool):
                raise _SqlstateError(
                    "23505",
                    "INSERT private SQL password=do-not-leak",
                )
        self.assertEqual(connection.rollbacks, 1)
        self.assertNotIn("private", str(raised.exception))

    def test_non_database_body_exception_is_preserved(self):
        connection = _FakeConnection()
        marker = ValueError("application validation failed")
        with self.assertRaises(ValueError) as raised:
            with PostgresUnitOfWork(_FakePool(connection)):
                raise marker
        self.assertIs(raised.exception, marker)
        self.assertEqual(connection.rollbacks, 1)

    def test_transaction_policy_and_repository_share_connection(self):
        connection = _FakeConnection()
        factory_calls = []

        def repository_factory(bound_connection):
            factory_calls.append(bound_connection)
            return {"connection": bound_connection}

        with PostgresUnitOfWork(
            _FakePool(connection),
            isolation_level="serializable",
            read_only=True,
            repository_factories={"dreams": repository_factory},
        ) as uow:
            first = uow.repository("dreams")
            second = uow.repository("dreams")
            self.assertIs(first, second)
        self.assertEqual(factory_calls, [connection])
        self.assertEqual(
            connection.executions[0],
            ("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE READ ONLY", None),
        )


class _CatalogConnection(_FakeConnection):
    def __init__(self, *, reverse=False, changed_default=False):
        super().__init__()
        tables = [
            {"schema_name": "public", "table_name": "dreams"},
            {"schema_name": "public", "table_name": "users"},
        ]
        columns = [
            {
                "schema_name": "public",
                "table_name": "dreams",
                "ordinal_position": 2,
                "column_name": "title",
                "pg_type": "text",
                "is_nullable": False,
                "identity_kind": None,
                "default_expression": "'changed'::text" if changed_default else None,
                "collation_name": None,
            },
            {
                "schema_name": "public",
                "table_name": "dreams",
                "ordinal_position": 1,
                "column_name": "id",
                "pg_type": "uuid",
                "is_nullable": False,
                "identity_kind": None,
                "default_expression": "gen_random_uuid()",
                "collation_name": None,
            },
            {
                "schema_name": "public",
                "table_name": "users",
                "ordinal_position": 1,
                "column_name": "id",
                "pg_type": "bigint",
                "is_nullable": False,
                "identity_kind": "by_default",
                "default_expression": None,
                "collation_name": None,
            },
        ]
        constraints = [
            {
                "schema_name": "public",
                "table_name": "dreams",
                "constraint_name": "dreams_pkey",
                "constraint_type": "p",
                "columns": ["id"],
                "referenced_schema": None,
                "referenced_table": None,
                "referenced_columns": [],
                "definition": "PRIMARY KEY (id)",
            }
        ]
        indexes = [
            {
                "schema_name": "public",
                "table_name": "dreams",
                "index_name": "idx_dreams_title",
                "access_method": "btree",
                "is_unique": False,
                "is_valid": True,
                "key_position": 1,
                "is_included": False,
                "key_expression": "title DESC",
                "sort_order": "desc",
                "nulls_order": "first",
                "predicate": "(title IS NOT NULL)",
            }
        ]
        triggers = [
            {
                "schema_name": "public",
                "table_name": "dreams",
                "trigger_name": "dreams_updated_at",
                "timing": "before",
                "trigger_level": "row",
                "events": ["update"],
                "function_definition": "CREATE FUNCTION touch() RETURNS trigger ...",
            }
        ]
        if reverse:
            for rows in (tables, columns, constraints, indexes, triggers):
                rows.reverse()
        self.responses = {
            "ink_catalog:tables": tables,
            "ink_catalog:columns": columns,
            "ink_catalog:constraints": constraints,
            "ink_catalog:indexes": indexes,
            "ink_catalog:triggers": triggers,
        }

    def execute(self, query, parameters=None):
        self.executions.append((query, parameters))
        for marker, rows in self.responses.items():
            if marker in query:
                return _FakeCursor(rows=rows)
        if "ink_health:identity" in query:
            return _FakeCursor(
                row={
                    "database_name": "ink_test",
                    "schema_name": "public",
                    "server_version_num": "170002",
                    "is_in_recovery": False,
                }
            )
        raise AssertionError("unexpected query")


class CatalogFingerprintTest(unittest.TestCase):
    def test_admin_head_target_counts_are_distinct_from_legacy_source(self):
        self.assertEqual(EXPECTED_SOURCE_APPLICATION_COLUMN_COUNT, 567)
        self.assertEqual(EXPECTED_TARGET_APPLICATION_COLUMN_COUNT, 569)
        self.assertEqual(EXPECTED_APPLICATION_COLUMN_COUNT, 569)
        self.assertEqual(EXPECTED_SOURCE_EXPLICIT_INDEX_COUNT, 78)
        self.assertEqual(EXPECTED_TARGET_EXPLICIT_INDEX_COUNT, 81)
        self.assertEqual(EXPECTED_EXPLICIT_INDEX_COUNT, 81)

        target = CatalogExpectations.dream_43_plus_5()
        self.assertEqual(target.tables, 48)
        self.assertEqual(target.columns, 569)
        self.assertEqual(target.explicit_indexes, 81)
        self.assertEqual(target.triggers, 25)

    def test_fingerprint_is_order_independent_and_structurally_sensitive(self):
        expected_names = {"users", "dreams"}
        first = catalog_snapshot(_CatalogConnection(), "public", expected_names)
        reordered = catalog_snapshot(
            _CatalogConnection(reverse=True),
            "public",
            expected_names,
        )
        changed = catalog_snapshot(
            _CatalogConnection(changed_default=True),
            "public",
            expected_names,
        )
        self.assertEqual(first.fingerprint, reordered.fingerprint)
        self.assertNotEqual(first.fingerprint, changed.fingerprint)
        self.assertEqual(len(first.fingerprint), 64)
        self.assertEqual(first.counts.tables, 2)
        self.assertEqual(first.counts.columns, 3)
        self.assertEqual(first.counts.explicit_indexes, 1)
        self.assertEqual(first.counts.triggers, 1)

    def test_expected_table_set_is_an_exact_gate(self):
        with self.assertRaises(CatalogMismatchError):
            catalog_snapshot(_CatalogConnection(), expected_names={"dreams"})

    def test_health_can_attest_database_catalog_without_real_pool(self):
        connection = _CatalogConnection()
        fingerprint = catalog_snapshot(
            _CatalogConnection(),
            expected_names={"users", "dreams"},
        ).fingerprint
        health = check_postgres_health(
            _FakePool(connection),
            expected_names={"users", "dreams"},
            expected_fingerprint=fingerprint,
            expected_database_name="ink_test",
            expected_counts=CatalogExpectations(
                tables=2,
                columns=3,
                explicit_indexes=1,
                triggers=1,
            ),
        )
        self.assertTrue(health.ok)
        self.assertEqual(health.status, "ok")
        self.assertEqual(health.catalog_fingerprint, fingerprint)

        failed = probe_postgres_health(
            _FakePool(_CatalogConnection()),
            expected_names={"users", "dreams"},
            expected_fingerprint="0" * 64,
        )
        self.assertFalse(failed.ok)
        self.assertEqual(failed.error_code, CatalogMismatchError.code)

    def test_environment_is_never_read_when_mapping_is_injected(self):
        with mock.patch.dict(
            os.environ,
            {"TEST_DATABASE_URL": "postgresql://localhost/wrong_test"},
            clear=True,
        ):
            target = require_test_database_target(
                environ={"TEST_DATABASE_URL": "postgresql://localhost/right_test"}
            )
        self.assertEqual(target.database_name, "right_test")


if __name__ == "__main__":
    unittest.main()
