"""Test-only compatibility for historical SQLite unit fixtures.

Production code speaks psycopg's ``%s`` parameter protocol.  A bounded set of
legacy domain tests still exercises transaction/state-machine behavior with
ephemeral SQLite databases.  Returning a SQLite subclass here lets those
fixtures consume PostgreSQL-style placeholders without putting SQL rewriting,
SQLite imports, or a fallback connection path into production modules.
"""

from __future__ import annotations

import os
import re
import sqlite3
from typing import Any

from psycopg import IntegrityError as PostgresIntegrityError


# Never let importing backend/server.py inherit the developer's runtime DSN.
# Tests that need PostgreSQL must opt in through validated TEST_DATABASE_URL.
os.environ["INK_LOAD_DATABASE_URL_FROM_ENV_FILE"] = "0"
os.environ.setdefault(
    "INK_WORKFLOW_TOKEN_SECRET",
    "ink-dream-test-workflow-token-secret-v1",
)


_ORIGINAL_CONNECT = sqlite3.connect


def _postgres_sql_to_sqlite(statement: str) -> str:
    # Exact compatibility for the frozen Dream re-entry authorization query.
    # This is intentionally not a general JSONB translator: production keeps
    # the PostgreSQL expression, while historical SQLite fixtures exercise the
    # same joins and predicates through SQLite JSON1.
    statement = statement.replace(
        "EXISTS (SELECT 1 FROM jsonb_array_elements("
        "COALESCE(release.manifest_json::jsonb -> 'surfaces', '[]'::jsonb)) AS surface(value) "
        "WHERE surface.value ->> 'name' = 'dream')",
        "EXISTS (SELECT 1 FROM json_each("
        "COALESCE(json_extract(release.manifest_json, '$.surfaces'), '[]')) AS surface "
        "WHERE json_extract(surface.value, '$.name') = 'dream')",
    )
    statement = statement.replace(
        "EXISTS (SELECT 1 FROM jsonb_array_elements_text("
        "COALESCE(release.manifest_json::jsonb -> 'capabilities', '[]'::jsonb)) AS capability(value) "
        "WHERE capability.value = 'story.workspace.propose')",
        "EXISTS (SELECT 1 FROM json_each("
        "COALESCE(json_extract(release.manifest_json, '$.capabilities'), '[]')) AS capability "
        "WHERE capability.value = 'story.workspace.propose')",
    )
    statement = statement.replace(
        "EXISTS (SELECT 1 FROM jsonb_array_elements("
        "COALESCE(release.manifest_json::jsonb #> '{runtime,claude_code_plugins}', "
        "'[]'::jsonb)) AS plugin(value) "
        "CROSS JOIN LATERAL jsonb_array_elements_text("
        "COALESCE(plugin.value -> 'capability_bindings', '[]'::jsonb)) "
        "AS binding_capability(value) "
        "WHERE binding_capability.value = 'story.workspace.propose')",
        "EXISTS (SELECT 1 FROM json_each("
        "COALESCE(json_extract(release.manifest_json, '$.runtime.claude_code_plugins'), '[]')) AS plugin "
        "CROSS JOIN json_each(COALESCE(json_extract(plugin.value, '$.capability_bindings'), '[]')) "
        "AS binding_capability WHERE binding_capability.value = 'story.workspace.propose')",
    )
    metadata_json = "COALESCE(NULLIF(TRIM(source.metadata), ''), '{}')"
    statement = statement.replace(
        "(COALESCE(NULLIF(BTRIM(source.metadata), ''), '{}')::jsonb ->> 'schemaVersion')",
        f"json_extract({metadata_json}, '$.schemaVersion')",
    )
    statement = statement.replace(
        "(COALESCE(NULLIF(BTRIM(source.metadata), ''), '{}')::jsonb ->> 'agentId')",
        f"json_extract({metadata_json}, '$.agentId')",
    )
    statement = statement.replace(
        "(COALESCE(NULLIF(BTRIM(source.metadata), ''), '{}')::jsonb "
        "#>> '{dreamContext,agent_id}')",
        f"json_extract({metadata_json}, '$.dreamContext.agent_id')",
    )
    statement = statement.replace(
        "(COALESCE(NULLIF(BTRIM(metadata), ''), '{}')::jsonb ->> 'kind')",
        "json_extract(COALESCE(NULLIF(TRIM(metadata), ''), '{}'), '$.kind')",
    )
    translated = statement.replace("%s", "?")
    translated = re.sub(r"\s+FOR\s+UPDATE(?:\s+SKIP\s+LOCKED)?\b", "", translated, flags=re.IGNORECASE)
    translated = re.sub(r"\bBTRIM\s*\(", "TRIM(", translated, flags=re.IGNORECASE)
    translated = re.sub(r"\bILIKE\b", "LIKE", translated, flags=re.IGNORECASE)
    return translated


class _PostgresPlaceholderCursor(sqlite3.Cursor):
    def execute(self, sql: str, parameters: Any = (), /):  # type: ignore[override]
        try:
            return super().execute(_postgres_sql_to_sqlite(sql), parameters)
        except sqlite3.IntegrityError as exc:
            if "%s" in sql:
                raise PostgresIntegrityError(str(exc)) from None
            raise

    def executemany(self, sql: str, seq_of_parameters: Any, /):  # type: ignore[override]
        return super().executemany(
            _postgres_sql_to_sqlite(sql),
            seq_of_parameters,
        )


class _PostgresPlaceholderConnection(sqlite3.Connection):
    def cursor(self, factory: Any = _PostgresPlaceholderCursor):  # type: ignore[override]
        return super().cursor(factory)

    def execute(self, sql: str, parameters: Any = (), /):  # type: ignore[override]
        try:
            return super().execute(_postgres_sql_to_sqlite(sql), parameters)
        except sqlite3.IntegrityError as exc:
            if "%s" in sql:
                raise PostgresIntegrityError(str(exc)) from None
            raise

    def executemany(self, sql: str, seq_of_parameters: Any, /):  # type: ignore[override]
        return super().executemany(
            _postgres_sql_to_sqlite(sql),
            seq_of_parameters,
        )


def _connect_with_postgres_placeholders(*args: Any, **kwargs: Any):
    kwargs.setdefault("factory", _PostgresPlaceholderConnection)
    return _ORIGINAL_CONNECT(*args, **kwargs)


# Pytest imports this file before test modules construct their in-memory/file
# fixtures.  The patch is process-local to the test runner.
sqlite3.connect = _connect_with_postgres_placeholders
