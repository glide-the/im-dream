"""PostgreSQL liveness/readiness checks with optional catalog attestation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import hmac
from typing import Any, Final

from .catalog import (
    CatalogCounts,
    CatalogExpectations,
    CatalogSnapshot,
    catalog_snapshot,
)
from .errors import CatalogMismatchError, PersistenceError, map_postgres_error


POSTGRES_IDENTITY_SQL: Final = """
/* ink_health:identity */
SELECT
  current_database() AS database_name,
  current_schema() AS schema_name,
  current_setting('server_version_num') AS server_version_num,
  pg_catalog.pg_is_in_recovery() AS is_in_recovery
"""


@dataclass(frozen=True)
class PostgresHealth:
    ok: bool
    database_name: str | None = None
    schema: str | None = None
    server_version_num: int | None = None
    is_in_recovery: bool | None = None
    catalog_fingerprint: str | None = None
    catalog_counts: CatalogCounts | None = None
    error_code: str | None = None

    @property
    def status(self) -> str:
        return "ok" if self.ok else "error"


PostgresHealthStatus = PostgresHealth


def _fetchone(connection: Any, sql: str) -> Any:
    result = connection.execute(sql)
    if hasattr(result, "fetchone"):
        return result.fetchone()
    return result


def _identity_record(row: Any) -> tuple[str, str | None, int, bool]:
    if isinstance(row, Mapping):
        values = (
            row.get("database_name"),
            row.get("schema_name"),
            row.get("server_version_num"),
            row.get("is_in_recovery"),
        )
    elif isinstance(row, (list, tuple)) and len(row) == 4:
        values = tuple(row)
    else:
        raise CatalogMismatchError()
    database_name, schema_name, version, recovery = values
    if not isinstance(database_name, str) or not database_name:
        raise CatalogMismatchError()
    if schema_name is not None and not isinstance(schema_name, str):
        raise CatalogMismatchError()
    try:
        normalized_version = int(version)
    except (TypeError, ValueError):
        raise CatalogMismatchError() from None
    return database_name, schema_name, normalized_version, bool(recovery)


def check_postgres_health(
    pool: Any,
    *,
    schema: str = "public",
    expected_names: Iterable[str] | None = None,
    expected_fingerprint: str | None = None,
    expected_counts: CatalogExpectations | None = None,
    expected_database_name: str | None = None,
    include_catalog: bool = True,
) -> PostgresHealth:
    """Run a readiness check, raising only redacted persistence errors."""

    try:
        with pool.connection() as connection:
            database_name, current_schema, version, recovery = _identity_record(
                _fetchone(connection, POSTGRES_IDENTITY_SQL)
            )
            if (
                expected_database_name is not None
                and database_name.casefold() != expected_database_name.casefold()
            ):
                raise CatalogMismatchError()

            snapshot: CatalogSnapshot | None = None
            if include_catalog:
                snapshot = catalog_snapshot(connection, schema, expected_names)
                if (
                    expected_fingerprint is not None
                    and not hmac.compare_digest(
                        snapshot.fingerprint,
                        expected_fingerprint.casefold(),
                    )
                ):
                    raise CatalogMismatchError()
                if expected_counts is not None and not expected_counts.matches(
                    snapshot.counts
                ):
                    raise CatalogMismatchError()

            return PostgresHealth(
                ok=True,
                database_name=database_name,
                schema=current_schema,
                server_version_num=version,
                is_in_recovery=recovery,
                catalog_fingerprint=(snapshot.fingerprint if snapshot else None),
                catalog_counts=(snapshot.counts if snapshot else None),
            )
    except PersistenceError:
        raise
    except BaseException as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        raise map_postgres_error(exc) from None


def probe_postgres_health(pool: Any, **kwargs: Any) -> PostgresHealth:
    """Non-raising health probe suitable for a readiness response."""

    try:
        return check_postgres_health(pool, **kwargs)
    except PersistenceError as exc:
        return PostgresHealth(ok=False, error_code=exc.code)


health_check = check_postgres_health


__all__ = [
    "POSTGRES_IDENTITY_SQL",
    "PostgresHealth",
    "PostgresHealthStatus",
    "check_postgres_health",
    "health_check",
    "probe_postgres_health",
]
