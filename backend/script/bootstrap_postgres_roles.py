#!/usr/bin/env python3
"""Bootstrap and verify Dream/Admin PostgreSQL roles in an isolated database.

The command refuses DATABASE_URL and accepts only a validated TEST_DATABASE_URL.
It never creates LOGIN roles and never changes the target database owner.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import psycopg
from psycopg import sql

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from persistence.config import require_test_database_target  # noqa: E402
from schema.catalog import load_manifest  # noqa: E402


_ROLE_PREFIX = re.compile(r"^[a-z][a-z0-9_]{2,30}$")


@dataclass(frozen=True)
class RoleNames:
    admin_migration: str
    admin_runtime: str
    dream_migration: str
    dream_runtime: str

    @classmethod
    def from_prefix(cls, prefix: str) -> "RoleNames":
        if not _ROLE_PREFIX.fullmatch(prefix):
            raise ValueError("role prefix must match ^[a-z][a-z0-9_]{2,30}$")
        return cls(
            admin_migration=f"{prefix}_admin_migration",
            admin_runtime=f"{prefix}_admin_runtime",
            dream_migration=f"{prefix}_dream_migration",
            dream_runtime=f"{prefix}_dream_runtime",
        )

    def all(self) -> tuple[str, ...]:
        return (
            self.admin_migration,
            self.admin_runtime,
            self.dream_migration,
            self.dream_runtime,
        )


def _dream_tables() -> frozenset[str]:
    manifest = load_manifest()
    tables = frozenset(str(table["name"]) for table in manifest["tables"])
    if len(tables) != 48:
        raise RuntimeError("Dream role bootstrap requires the exact 43+5 manifest")
    return tables | {"dream_alembic_version"}


def _create_roles(connection: psycopg.Connection, roles: RoleNames) -> None:
    for role in roles.all():
        exists = connection.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)
        ).fetchone()
        if exists is None:
            connection.execute(
                sql.SQL(
                    "CREATE ROLE {} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                    "NOINHERIT NOREPLICATION NOBYPASSRLS"
                ).format(sql.Identifier(role))
            )


def _public_tables(connection: psycopg.Connection) -> list[str]:
    return [
        row[0]
        for row in connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        ).fetchall()
    ]


def _alter_table_owner(
    connection: psycopg.Connection,
    table: str,
    owner: str,
) -> None:
    connection.execute(
        sql.SQL("ALTER TABLE public.{} OWNER TO {}").format(
            sql.Identifier(table), sql.Identifier(owner)
        )
    )


def _grant_table(
    connection: psycopg.Connection,
    table: str,
    privileges: str,
    role: str,
) -> None:
    connection.execute(
        sql.SQL("GRANT " + privileges + " ON TABLE public.{} TO {}").format(
            sql.Identifier(table), sql.Identifier(role)
        )
    )


def _configure_tables(
    connection: psycopg.Connection,
    roles: RoleNames,
    dream_tables: frozenset[str],
) -> tuple[int, int]:
    dream_count = 0
    admin_count = 0
    for table in _public_tables(connection):
        is_dream = table in dream_tables
        owner = roles.dream_migration if is_dream else roles.admin_migration
        _alter_table_owner(connection, table, owner)
        connection.execute(
            sql.SQL("REVOKE ALL ON TABLE public.{} FROM PUBLIC").format(
                sql.Identifier(table)
            )
        )
        if is_dream:
            dream_count += 1
            _grant_table(connection, table, "SELECT, INSERT, UPDATE, DELETE", roles.dream_runtime)
            _grant_table(connection, table, "SELECT", roles.admin_runtime)
        else:
            admin_count += 1
            _grant_table(connection, table, "SELECT, INSERT, UPDATE, DELETE", roles.admin_runtime)
    return dream_count, admin_count


def _sequence_rows(connection: psycopg.Connection) -> list[tuple[str, str | None]]:
    return connection.execute(
        """
        SELECT sequence.relname,
               owned_table.relname
        FROM pg_class AS sequence
        JOIN pg_namespace AS namespace ON namespace.oid = sequence.relnamespace
        LEFT JOIN pg_depend AS dependency
          ON dependency.classid = 'pg_class'::regclass
         AND dependency.objid = sequence.oid
         AND dependency.deptype IN ('a', 'i')
        LEFT JOIN pg_class AS owned_table ON owned_table.oid = dependency.refobjid
        WHERE namespace.nspname = 'public' AND sequence.relkind = 'S'
        ORDER BY sequence.relname
        """
    ).fetchall()


def _configure_sequences(
    connection: psycopg.Connection,
    roles: RoleNames,
    dream_tables: frozenset[str],
) -> None:
    for sequence, owned_table in _sequence_rows(connection):
        is_dream = owned_table in dream_tables if owned_table else False
        owner = roles.dream_migration if is_dream else roles.admin_migration
        runtime = roles.dream_runtime if is_dream else roles.admin_runtime
        # ALTER TABLE ... OWNER transfers an OWNED BY sequence as part of the
        # same ownership boundary. PostgreSQL rejects a second direct owner
        # change for such sequences, so only standalone sequences need it.
        if owned_table is None:
            connection.execute(
                sql.SQL("ALTER SEQUENCE public.{} OWNER TO {}").format(
                    sql.Identifier(sequence), sql.Identifier(owner)
                )
            )
        connection.execute(
            sql.SQL("REVOKE ALL ON SEQUENCE public.{} FROM PUBLIC").format(
                sql.Identifier(sequence)
            )
        )
        connection.execute(
            sql.SQL("GRANT USAGE, SELECT ON SEQUENCE public.{} TO {}").format(
                sql.Identifier(sequence), sql.Identifier(runtime)
            )
        )


def _function_rows(connection: psycopg.Connection) -> list[tuple[str, str, list[str]]]:
    rows = connection.execute(
        """
        SELECT function.proname,
               pg_get_function_identity_arguments(function.oid),
               COALESCE(array_agg(DISTINCT trigger_table.relname)
                 FILTER (WHERE trigger_table.relname IS NOT NULL), ARRAY[]::name[])
        FROM pg_proc AS function
        JOIN pg_namespace AS namespace ON namespace.oid = function.pronamespace
        LEFT JOIN pg_trigger AS trigger
          ON trigger.tgfoid = function.oid AND NOT trigger.tgisinternal
        LEFT JOIN pg_class AS trigger_table ON trigger_table.oid = trigger.tgrelid
        WHERE namespace.nspname = 'public'
        GROUP BY function.oid, function.proname
        ORDER BY function.proname
        """
    ).fetchall()
    return [(row[0], row[1], list(row[2])) for row in rows]


def _configure_functions(
    connection: psycopg.Connection,
    roles: RoleNames,
    dream_tables: frozenset[str],
) -> None:
    for name, identity_arguments, trigger_tables in _function_rows(connection):
        is_dream = bool(trigger_tables) and all(
            table in dream_tables for table in trigger_tables
        )
        if name == "sync_canonical_user_billing_identity":
            is_dream = False
        owner = roles.dream_migration if is_dream else roles.admin_migration
        runtime = roles.dream_runtime if is_dream else roles.admin_runtime
        signature = sql.SQL("public.{}({})").format(
            sql.Identifier(name), sql.SQL(identity_arguments)
        )
        connection.execute(
            sql.SQL("ALTER FUNCTION {} OWNER TO {}").format(
                signature, sql.Identifier(owner)
            )
        )
        connection.execute(sql.SQL("REVOKE ALL ON FUNCTION {} FROM PUBLIC").format(signature))
        connection.execute(
            sql.SQL("GRANT EXECUTE ON FUNCTION {} TO {}").format(
                signature, sql.Identifier(runtime)
            )
        )
        if name == "sync_canonical_user_billing_identity":
            connection.execute(
                sql.SQL("ALTER FUNCTION {} SECURITY DEFINER").format(signature)
            )
            connection.execute(
                sql.SQL("ALTER FUNCTION {} SET search_path = pg_catalog, public").format(
                    signature
                )
            )


def _configure_schemas(connection: psycopg.Connection, roles: RoleNames) -> None:
    connection.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
    for role in roles.all():
        connection.execute(
            sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(role))
        )
    for owner in (roles.admin_migration, roles.dream_migration):
        connection.execute(
            sql.SQL("GRANT CREATE ON SCHEMA public TO {}").format(sql.Identifier(owner))
        )

    drizzle = connection.execute(
        "SELECT 1 FROM pg_namespace WHERE nspname = 'drizzle'"
    ).fetchone()
    if drizzle:
        connection.execute(
            sql.SQL("ALTER SCHEMA drizzle OWNER TO {}").format(
                sql.Identifier(roles.admin_migration)
            )
        )
        connection.execute("REVOKE ALL ON SCHEMA drizzle FROM PUBLIC")
        connection.execute(
            sql.SQL("GRANT USAGE ON SCHEMA drizzle TO {}").format(
                sql.Identifier(roles.admin_runtime)
            )
        )
        connection.execute(
            sql.SQL("ALTER TABLE drizzle.__drizzle_migrations OWNER TO {}").format(
                sql.Identifier(roles.admin_migration)
            )
        )
        connection.execute("REVOKE ALL ON drizzle.__drizzle_migrations FROM PUBLIC")
        connection.execute(
            sql.SQL("GRANT SELECT ON drizzle.__drizzle_migrations TO {}").format(
                sql.Identifier(roles.admin_runtime)
            )
        )


def _configure_types(connection: psycopg.Connection, roles: RoleNames) -> None:
    types = connection.execute(
        """
        SELECT type.typname
        FROM pg_type AS type
        JOIN pg_namespace AS namespace ON namespace.oid = type.typnamespace
        WHERE namespace.nspname = 'public'
          AND type.typtype IN ('e', 'd')
        ORDER BY type.typname
        """
    ).fetchall()
    for (type_name,) in types:
        for role in roles.all():
            connection.execute(
                sql.SQL("GRANT USAGE ON TYPE public.{} TO {}").format(
                    sql.Identifier(type_name), sql.Identifier(role)
                )
            )


def _configure_default_privileges(
    connection: psycopg.Connection,
    roles: RoleNames,
) -> None:
    statements = (
        (roles.dream_migration, "TABLES", "SELECT, INSERT, UPDATE, DELETE", roles.dream_runtime),
        (roles.dream_migration, "TABLES", "SELECT", roles.admin_runtime),
        (roles.dream_migration, "SEQUENCES", "USAGE, SELECT", roles.dream_runtime),
        (roles.dream_migration, "FUNCTIONS", "EXECUTE", roles.dream_runtime),
        (roles.admin_migration, "TABLES", "SELECT, INSERT, UPDATE, DELETE", roles.admin_runtime),
        (roles.admin_migration, "SEQUENCES", "USAGE, SELECT", roles.admin_runtime),
        (roles.admin_migration, "FUNCTIONS", "EXECUTE", roles.admin_runtime),
    )
    for owner, object_type, privileges, grantee in statements:
        connection.execute(
            sql.SQL(
                "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public "
                "GRANT " + privileges + " ON " + object_type + " TO {}"
            ).format(sql.Identifier(owner), sql.Identifier(grantee))
        )


def bootstrap(connection: psycopg.Connection, roles: RoleNames) -> dict[str, int]:
    dream_tables = _dream_tables()
    _create_roles(connection, roles)
    _configure_schemas(connection, roles)
    dream_count, admin_count = _configure_tables(connection, roles, dream_tables)
    _configure_sequences(connection, roles, dream_tables)
    _configure_functions(connection, roles, dream_tables)
    _configure_types(connection, roles)
    _configure_default_privileges(connection, roles)
    return {"dreamTables": dream_count, "adminTables": admin_count}


def _has_table_privilege(
    connection: psycopg.Connection,
    role: str,
    table: str,
    privilege: str,
) -> bool:
    row = connection.execute(
        "SELECT has_table_privilege(%s, %s, %s)",
        (role, f"public.{table}", privilege),
    ).fetchone()
    return bool(row[0])


def verify(connection: psycopg.Connection, roles: RoleNames) -> dict[str, object]:
    checks = {
        "dream_reads_users": _has_table_privilege(
            connection, roles.dream_runtime, "users", "SELECT"
        ),
        "dream_writes_users": _has_table_privilege(
            connection, roles.dream_runtime, "users", "INSERT"
        ),
        "dream_cannot_read_subscriptions": not _has_table_privilege(
            connection, roles.dream_runtime, "subscriptions", "SELECT"
        ),
        "dream_cannot_write_subscriptions": not _has_table_privilege(
            connection, roles.dream_runtime, "subscriptions", "INSERT"
        ),
        "admin_reads_users": _has_table_privilege(
            connection, roles.admin_runtime, "users", "SELECT"
        ),
        "admin_cannot_update_users": not _has_table_privilege(
            connection, roles.admin_runtime, "users", "UPDATE"
        ),
        "admin_cannot_delete_users": not _has_table_privilege(
            connection, roles.admin_runtime, "users", "DELETE"
        ),
        "admin_writes_subscriptions": _has_table_privilege(
            connection, roles.admin_runtime, "subscriptions", "INSERT"
        ),
    }
    owner_rows = connection.execute(
        """
        SELECT tablename, tableowner
        FROM pg_tables
        WHERE schemaname = 'public'
          AND tablename IN ('users', 'connector_resources', 'subscriptions', 'gateway_requests')
        ORDER BY tablename
        """
    ).fetchall()
    owners = {row[0]: row[1] for row in owner_rows}
    checks["dream_owners"] = (
        owners.get("users") == roles.dream_migration
        and owners.get("connector_resources") == roles.dream_migration
    )
    checks["admin_owners"] = (
        owners.get("subscriptions") == roles.admin_migration
        and owners.get("gateway_requests") == roles.admin_migration
    )

    projection_verified = False
    try:
        connection.execute("SAVEPOINT role_projection_check")
        connection.execute(sql.SQL("SET LOCAL ROLE {}").format(sql.Identifier(roles.dream_runtime)))
        user_id = 9_100_000_000_000_001
        connection.execute(
            "INSERT INTO users (id, email, password_hash, display_name) VALUES (%s,%s,%s,%s)",
            (user_id, "role-matrix@ink-memory.test", "not-a-real-secret", "Role Matrix"),
        )
        connection.execute("RESET ROLE")
        projected = connection.execute(
            """
            SELECT count(*)
            FROM platform_users AS platform_user
            JOIN billing_accounts AS account ON account.platform_user_id = platform_user.id
            WHERE platform_user.source = 'ink-dream'
              AND platform_user.external_user_id = %s
            """,
            (str(user_id),),
        ).fetchone()
        projection_verified = projected[0] == 1
    finally:
        connection.execute("RESET ROLE")
        connection.execute("ROLLBACK TO SAVEPOINT role_projection_check")
        connection.execute("RELEASE SAVEPOINT role_projection_check")
    checks["dream_insert_provisions_billing_identity"] = projection_verified

    failed = sorted(name for name, passed in checks.items() if not passed)
    if failed:
        raise RuntimeError("role verification failed: " + ", ".join(failed))
    return {"checks": checks, "owners": owners}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role-prefix", required=True)
    parser.add_argument("--verify-only", action="store_true")
    arguments = parser.parse_args()
    roles = RoleNames.from_prefix(arguments.role_prefix)
    target = require_test_database_target()
    with psycopg.connect(target.dsn, autocommit=False) as connection:
        counts = None if arguments.verify_only else bootstrap(connection, roles)
        receipt = verify(connection, roles)
        connection.commit()
    print(
        json.dumps(
            {
                "database": target.database_name,
                "roles": {name: "NOLOGIN" for name in roles.all()},
                "counts": counts,
                **receipt,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
