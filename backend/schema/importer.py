"""Fail-closed legacy SQLite to PostgreSQL migration rehearsal/import.

This module is migration tooling only.  ``sqlite3`` is deliberately confined
to read-only legacy snapshots; Dream's production persistence path must not
import it.  The checked-in 43 + 5 manifest is the sole table/column allowlist.

No row value, source path, DSN, or driver exception is included in receipts or
public failures.  Target work happens in one serializable transaction and uses
session-local temporary staging tables.  Conflicts abort; there is no implicit
upsert, overwrite, destructive cleanup, or partial commit.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import stat
from tempfile import TemporaryDirectory
from typing import Any, Final
from uuid import UUID, uuid4

from .catalog import BASELINE_TABLES, load_manifest
from .postgres import BASELINE_INDEX_DDL


CONTRACT: Final = "ink-dream-legacy-postgres-import-v1"
EXPECTED_ALEMBIC_HEAD: Final = "20260809_06"
DEFAULT_MAIN_FILENAME: Final = "ink-and-memory.db"
DEFAULT_NOTION_FILENAME: Final = "notion-connectors.db"
TARGET_SCHEMA: Final = "public"
APPROVED_EXTERNAL_TRIGGERS: Final = {
    ("users", "users_sync_billing_identity"),
    ("users", "zz_users_default_free_subscription"),
}
APPROVED_TARGET_COLUMN_EXTENSIONS: Final = {
    "story_workspace_stories": (
        ("artifact_source_type", "text"),
        ("source_run_id", "text"),
        ("source_thread_ref", "text"),
        ("source_project_id", "text"),
        ("episode_count", "integer"),
        ("artifact_status", "text"),
        ("artifact_manifest_revision", "text"),
        ("script_revision", "text"),
        ("artifact_sync_status", "text"),
        ("artifact_indexed_at", "timestamptz"),
        ("artifact_sync_error_code", "text"),
        ("script_size_bytes", "bigint"),
        ("artifact_available", "boolean"),
        ("reconcile_version", "integer"),
        ("reviewed_script_revision", "text"),
    ),
}
APPROVED_TARGET_INDEX_EXTENSIONS: Final = {
    "story_workspace_stories_artifact_identity_uidx": (
        "story_workspace_stories",
        True,
    ),
    "story_workspace_stories_artifact_status_idx": (
        "story_workspace_stories",
        False,
    ),
    "story_workspace_stories_workspace_project_idx": (
        "story_workspace_stories",
        False,
    ),
}
APPROVED_TARGET_CHECK_COUNT_EXTENSIONS: Final = {
    "story_workspace_stories": 13,
}
# The long-lived SQLite source evolved through ALTER TABLE. Physical column
# order is therefore not a semantic contract: every migration query names its
# columns explicitly. One historical column also predates its builder default;
# the snapshot is read-only, so either observed default is safe for migration.
_APPROVED_SOURCE_DEFAULT_VARIANTS: Final = {
    ("main", "users", "updated_at"): frozenset({None, "CURRENT_TIMESTAMP"}),
}
_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]*$")
_INTEGER_MIN = -(2**31)
_INTEGER_MAX = 2**31 - 1
_BIGINT_MIN = -(2**63)
_BIGINT_MAX = 2**63 - 1


class LegacyMigrationError(RuntimeError):
    """Redacted, stable failure suitable for CLI output and automation."""

    def __init__(
        self,
        code: str,
        *,
        phase: str,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.phase = phase
        self.details = dict(details or {})
        super().__init__(code)


@dataclass(frozen=True)
class SnapshotFile:
    source: str
    path: Path
    sha256: str
    size_bytes: int
    source_size_bytes: int
    source_mtime_ns: int


@dataclass(frozen=True)
class SnapshotBundle:
    main: SnapshotFile
    notion: SnapshotFile

    def for_source(self, source: str) -> SnapshotFile:
        if source == "main":
            return self.main
        if source == "notion":
            return self.notion
        raise LegacyMigrationError("MANIFEST_SOURCE_INVALID", phase="manifest")


class _CanonicalDigest:
    """Incrementally hash a canonical JSON array without retaining rows."""

    def __init__(self) -> None:
        self._hash = hashlib.sha256()
        self._hash.update(b"[")
        self._first = True
        self.count = 0

    def add(self, value: Any) -> None:
        if not self._first:
            self._hash.update(b",")
        self._first = False
        self._hash.update(_canonical_json(value).encode("utf-8"))
        self.count += 1

    def hexdigest(self) -> str:
        digest = self._hash.copy()
        digest.update(b"]")
        return digest.hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _quote(identifier: str) -> str:
    if not _IDENTIFIER.fullmatch(identifier):
        raise LegacyMigrationError("MANIFEST_IDENTIFIER_INVALID", phase="manifest")
    return '"' + identifier + '"'


def _qualified(schema: str, table: str) -> str:
    return f"{_quote(schema)}.{_quote(table)}"


def _normalize_sql(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _normalize_default(value: object) -> str | None:
    if value is None:
        return None
    return _normalize_sql(value)


def _source_columns_compatible(
    *,
    source: str,
    table_name: str,
    actual_columns: Sequence[tuple[int, str, str, bool, object, int, int]],
    expected_columns: Sequence[tuple[int, str, str, bool, object, int, int]],
) -> bool:
    """Compare source columns by name while retaining every semantic guard."""

    actual_by_name = {column[1]: column for column in actual_columns}
    expected_by_name = {column[1]: column for column in expected_columns}
    if len(actual_by_name) != len(actual_columns) or len(expected_by_name) != len(
        expected_columns
    ):
        return False
    if set(actual_by_name) != set(expected_by_name):
        return False

    for name in sorted(expected_by_name):
        actual = actual_by_name[name]
        expected = expected_by_name[name]
        # cid/ordinal is intentionally excluded. Named SELECTs make SQLite's
        # append order irrelevant, while type/nullability/PK/hidden remain
        # strict migration contracts.
        if (
            str(actual[2]).upper(),
            bool(actual[3]),
            int(actual[5]),
            int(actual[6]),
        ) != (
            str(expected[2]).upper(),
            bool(expected[3]),
            int(expected[5]),
            int(expected[6]),
        ):
            return False
        actual_default = _normalize_default(actual[4])
        expected_default = _normalize_default(expected[4])
        if actual_default == expected_default:
            continue
        approved = _APPROVED_SOURCE_DEFAULT_VARIANTS.get((source, table_name, name))
        if approved is None or {actual_default, expected_default} - approved:
            return False
    return True


def _foreign_key_signature(foreign_key: Mapping[str, Any]) -> tuple[object, ...]:
    return (
        tuple(str(column) for column in foreign_key["columns"]),
        str(foreign_key["target_table"]),
        tuple(str(column) for column in foreign_key["target_columns"]),
        str(foreign_key["on_update"]).upper(),
        str(foreign_key["on_delete"]).upper(),
        str(foreign_key["match"]).upper(),
    )


def _source_foreign_keys_compatible(
    actual_foreign_keys: Sequence[Mapping[str, Any]],
    expected_foreign_keys: Sequence[Mapping[str, Any]],
) -> bool:
    """Allow target-only FKs to be present or absent in legacy SQLite."""

    actual = {_foreign_key_signature(item) for item in actual_foreign_keys}
    required = {
        _foreign_key_signature(item)
        for item in expected_foreign_keys
        if not bool(item.get("target_only"))
    }
    allowed = {_foreign_key_signature(item) for item in expected_foreign_keys}
    return len(actual) == len(actual_foreign_keys) and required <= actual <= allowed


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _validate_source_file(path: Path, *, expected_filename: str) -> os.stat_result:
    if not path.is_absolute():
        raise LegacyMigrationError("SOURCE_PATH_NOT_ABSOLUTE", phase="snapshot")
    try:
        metadata = path.lstat()
    except OSError:
        raise LegacyMigrationError("SOURCE_FILE_UNAVAILABLE", phase="snapshot") from None
    if stat.S_ISLNK(metadata.st_mode):
        raise LegacyMigrationError("SOURCE_SYMLINK_REJECTED", phase="snapshot")
    if not stat.S_ISREG(metadata.st_mode):
        raise LegacyMigrationError("SOURCE_NOT_REGULAR_FILE", phase="snapshot")
    if metadata.st_size <= 0:
        raise LegacyMigrationError("SOURCE_FILE_EMPTY", phase="snapshot")
    if path.name != expected_filename:
        raise LegacyMigrationError("SOURCE_FILENAME_UNEXPECTED", phase="snapshot")
    return metadata


def _open_read_only_sqlite(path: Path) -> sqlite3.Connection:
    try:
        connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection
    except sqlite3.Error:
        raise LegacyMigrationError("SOURCE_OPEN_FAILED", phase="snapshot") from None


def _assert_sqlite_integrity(connection: sqlite3.Connection) -> None:
    try:
        quick = connection.execute("PRAGMA quick_check").fetchall()
        integrity = connection.execute("PRAGMA integrity_check").fetchall()
        foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchone()
    except sqlite3.Error:
        raise LegacyMigrationError("SOURCE_INTEGRITY_CHECK_FAILED", phase="snapshot") from None
    quick_values = [str(row[0]) for row in quick]
    integrity_values = [str(row[0]) for row in integrity]
    if quick_values != ["ok"] or integrity_values != ["ok"] or foreign_keys is not None:
        raise LegacyMigrationError("SOURCE_INTEGRITY_INVALID", phase="snapshot")


@contextmanager
def readonly_snapshot_bundle(
    main_path: Path,
    notion_path: Path,
    *,
    expected_main_filename: str = DEFAULT_MAIN_FILENAME,
    expected_notion_filename: str = DEFAULT_NOTION_FILENAME,
) -> Iterator[SnapshotBundle]:
    """Take coordinated, per-file consistent SQLite Online Backup snapshots.

    Two SQLite files cannot provide a distributed atomic snapshot.  Both
    read-only transactions are established before either backup begins, which
    provides a stable snapshot for each file and a bounded coordinated capture.
    The receipt states this boundary explicitly.
    """

    main_metadata = _validate_source_file(
        main_path, expected_filename=expected_main_filename
    )
    notion_metadata = _validate_source_file(
        notion_path, expected_filename=expected_notion_filename
    )
    if main_path.resolve() == notion_path.resolve():
        raise LegacyMigrationError("SOURCE_FILES_MUST_DIFFER", phase="snapshot")

    with TemporaryDirectory(prefix="ink-dream-pg-import-") as temporary:
        temporary_path = Path(temporary)
        os.chmod(temporary_path, 0o700)
        destinations = {
            "main": temporary_path / "main.snapshot.sqlite3",
            "notion": temporary_path / "notion.snapshot.sqlite3",
        }
        sources: dict[str, sqlite3.Connection] = {}
        with ExitStack() as stack:
            try:
                for source, source_path in (("main", main_path), ("notion", notion_path)):
                    connection = _open_read_only_sqlite(source_path)
                    sources[source] = connection
                    stack.callback(connection.close)
                    connection.execute("BEGIN")
                    # Establish both read snapshots before either backup starts.
                    connection.execute(
                        "SELECT count(*) FROM sqlite_master"
                    ).fetchone()
                for source in ("main", "notion"):
                    destination = sqlite3.connect(destinations[source])
                    try:
                        sources[source].backup(destination)
                    finally:
                        destination.close()
                    os.chmod(destinations[source], 0o600)
            except LegacyMigrationError:
                raise
            except (OSError, sqlite3.Error):
                raise LegacyMigrationError("SOURCE_SNAPSHOT_FAILED", phase="snapshot") from None

        snapshot_metadata: dict[str, SnapshotFile] = {}
        source_metadata = {"main": main_metadata, "notion": notion_metadata}
        for source in ("main", "notion"):
            snapshot = destinations[source]
            connection = _open_read_only_sqlite(snapshot)
            try:
                _assert_sqlite_integrity(connection)
            finally:
                connection.close()
            metadata = snapshot.stat()
            snapshot_metadata[source] = SnapshotFile(
                source=source,
                path=snapshot,
                sha256=_sha256_file(snapshot),
                size_bytes=metadata.st_size,
                source_size_bytes=source_metadata[source].st_size,
                source_mtime_ns=source_metadata[source].st_mtime_ns,
            )
        yield SnapshotBundle(
            main=snapshot_metadata["main"], notion=snapshot_metadata["notion"]
        )


def _sqlite_foreign_keys(
    connection: sqlite3.Connection, table_name: str
) -> list[dict[str, Any]]:
    grouped: dict[int, list[sqlite3.Row]] = {}
    rows = connection.execute(
        f"PRAGMA foreign_key_list({_quote(table_name)})"
    ).fetchall()
    for row in rows:
        grouped.setdefault(int(row["id"]), []).append(row)
    result: list[dict[str, Any]] = []
    for foreign_key_id in sorted(grouped):
        parts = sorted(grouped[foreign_key_id], key=lambda item: int(item["seq"]))
        result.append(
            {
                "columns": [str(item["from"]) for item in parts],
                "target_table": str(parts[0]["table"]),
                "target_columns": [str(item["to"]) for item in parts],
                "on_update": str(parts[0]["on_update"]).upper(),
                "on_delete": str(parts[0]["on_delete"]).upper(),
                "match": str(parts[0]["match"]).upper(),
                "target_only": False,
            }
        )
    return result


def _extract_checks(create_sql: str) -> list[str]:
    upper = create_sql.upper()
    checks: list[str] = []
    position = 0
    while True:
        start = upper.find("CHECK", position)
        if start < 0:
            return checks
        cursor = start + len("CHECK")
        while cursor < len(create_sql) and create_sql[cursor].isspace():
            cursor += 1
        if cursor >= len(create_sql) or create_sql[cursor] != "(":
            position = cursor
            continue
        depth = 1
        end = cursor + 1
        quote: str | None = None
        while end < len(create_sql) and depth:
            character = create_sql[end]
            if quote:
                if character == quote:
                    if end + 1 < len(create_sql) and create_sql[end + 1] == quote:
                        end += 2
                        continue
                    quote = None
            elif character in {"'", '"'}:
                quote = character
            elif character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
            end += 1
        if depth:
            raise LegacyMigrationError("SOURCE_CHECK_SCHEMA_INVALID", phase="manifest")
        checks.append(create_sql[cursor + 1 : end - 1].strip())
        position = end


def _validate_source_schema(
    connection: sqlite3.Connection,
    *,
    source: str,
    tables: Sequence[Mapping[str, Any]],
    expected_triggers: Sequence[Mapping[str, Any]],
) -> str:
    try:
        actual_table_rows = connection.execute(
            "SELECT name, sql FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    except sqlite3.Error:
        raise LegacyMigrationError("SOURCE_SCHEMA_READ_FAILED", phase="manifest") from None
    expected_names = {str(table["name"]) for table in tables}
    actual_names = {str(row["name"]) for row in actual_table_rows}
    if actual_names != expected_names:
        raise LegacyMigrationError("SOURCE_TABLE_INVENTORY_MISMATCH", phase="manifest")
    actual_sql = {str(row["name"]): str(row["sql"] or "") for row in actual_table_rows}

    schema_digest = hashlib.sha256()
    for table in sorted(tables, key=lambda item: str(item["name"])):
        name = str(table["name"])
        try:
            rows = connection.execute(
                f"PRAGMA table_xinfo({_quote(name)})"
            ).fetchall()
        except sqlite3.Error:
            raise LegacyMigrationError("SOURCE_COLUMN_SCHEMA_READ_FAILED", phase="manifest") from None
        actual_columns = [
            (
                int(row["cid"]),
                str(row["name"]),
                str(row["type"] or ""),
                bool(row["notnull"]),
                row["dflt_value"],
                int(row["pk"]),
                int(row["hidden"]),
            )
            for row in rows
        ]
        expected_columns = [
            (
                int(column["ordinal"]),
                str(column["name"]),
                str(column["sqlite_type"] or ""),
                bool(column["not_null"]),
                column["default"],
                int(column["pk_ordinal"]),
                int(column["hidden"]),
            )
            for column in table["columns"]
        ]
        if not _source_columns_compatible(
            source=source,
            table_name=name,
            actual_columns=actual_columns,
            expected_columns=expected_columns,
        ):
            raise LegacyMigrationError("SOURCE_COLUMN_SCHEMA_MISMATCH", phase="manifest")

        actual_foreign_keys = _sqlite_foreign_keys(connection, name)
        expected_foreign_keys = [dict(foreign_key) for foreign_key in table["foreign_keys"]]
        if not _source_foreign_keys_compatible(
            actual_foreign_keys,
            expected_foreign_keys,
        ):
            raise LegacyMigrationError("SOURCE_FOREIGN_KEY_SCHEMA_MISMATCH", phase="manifest")

        expected_checks = [_normalize_sql(check) for check in table["checks"]]
        observed_checks = [_normalize_sql(check) for check in _extract_checks(actual_sql[name])]
        if observed_checks != expected_checks:
            raise LegacyMigrationError("SOURCE_CHECK_SCHEMA_MISMATCH", phase="manifest")

        index_rows = connection.execute(
            "SELECT name, sql FROM sqlite_master "
            "WHERE type='index' AND tbl_name=? AND sql IS NOT NULL ORDER BY name",
            (name,),
        ).fetchall()
        actual_indexes = [
            (str(row["name"]), _normalize_sql(row["sql"])) for row in index_rows
        ]
        expected_indexes = [
            (str(index["name"]), _normalize_sql(index["source_sql"]))
            for index in table["explicit_indexes"]
        ]
        if actual_indexes != expected_indexes:
            raise LegacyMigrationError("SOURCE_INDEX_SCHEMA_MISMATCH", phase="manifest")
        schema_digest.update(name.encode("utf-8"))
        schema_digest.update(_normalize_sql(actual_sql[name]).encode("utf-8"))

    trigger_rows = connection.execute(
        "SELECT name, tbl_name, sql FROM sqlite_master "
        "WHERE type='trigger' ORDER BY name"
    ).fetchall()
    actual_trigger_contract = [
        (
            str(row["name"]),
            str(row["tbl_name"]),
            _normalize_sql(row["sql"]),
        )
        for row in trigger_rows
    ]
    expected_trigger_contract = [
        (
            str(trigger["name"]),
            str(trigger["table"]),
            _normalize_sql(trigger["source_sql"]),
        )
        for trigger in expected_triggers
        if any(str(table["name"]) == str(trigger["table"]) for table in tables)
    ]
    if actual_trigger_contract != expected_trigger_contract:
        raise LegacyMigrationError("SOURCE_TRIGGER_SCHEMA_MISMATCH", phase="manifest")
    return schema_digest.hexdigest()


def _parse_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        candidate = value.strip()
        if candidate.endswith("Z"):
            candidate = candidate[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            raise LegacyMigrationError("SOURCE_TIME_INVALID", phase="transform") from None
    else:
        raise LegacyMigrationError("SOURCE_TIME_INVALID", phase="transform")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    try:
        return parsed.astimezone(timezone.utc)
    except (OverflowError, ValueError):
        raise LegacyMigrationError("SOURCE_TIME_INVALID", phase="transform") from None


def _parse_json(value: Any) -> Any:
    if not isinstance(value, str):
        raise LegacyMigrationError("SOURCE_JSON_INVALID", phase="transform")
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        raise LegacyMigrationError("SOURCE_JSON_INVALID", phase="transform") from None


def transform_value(table_name: str, column: Mapping[str, Any], value: Any) -> Any:
    """Validate and convert one SQLite value to its PostgreSQL boundary type."""

    if value is None:
        return None
    transform = column["transform"]
    target_type = str(transform["target_type"])
    if bool(transform.get("time")):
        return _parse_time(value)
    if bool(transform.get("json_text")):
        parsed = _parse_json(value)
        if table_name == "story_workspace_workspaces" and column["name"] == "settings":
            # Approved canonical baseline exception: source TEXT becomes JSONB.
            return parsed
        return value
    if target_type in {"integer", "bigint"}:
        if isinstance(value, bool) or not isinstance(value, int):
            raise LegacyMigrationError("SOURCE_INTEGER_INVALID", phase="transform")
        minimum, maximum = (
            (_INTEGER_MIN, _INTEGER_MAX)
            if target_type == "integer"
            else (_BIGINT_MIN, _BIGINT_MAX)
        )
        if value < minimum or value > maximum:
            raise LegacyMigrationError("SOURCE_INTEGER_OUT_OF_RANGE", phase="transform")
        return value
    if target_type == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, int) and value in {0, 1}:
            return bool(value)
        raise LegacyMigrationError("SOURCE_BOOLEAN_INVALID", phase="transform")
    if target_type == "double precision":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise LegacyMigrationError("SOURCE_REAL_INVALID", phase="transform")
        converted = float(value)
        if not math.isfinite(converted):
            raise LegacyMigrationError("SOURCE_REAL_NON_FINITE", phase="transform")
        return converted
    if target_type == "bytea":
        if not isinstance(value, (bytes, bytearray, memoryview)):
            raise LegacyMigrationError("SOURCE_BLOB_INVALID", phase="transform")
        return bytes(value)
    if target_type == "text":
        if not isinstance(value, str):
            raise LegacyMigrationError("SOURCE_TEXT_INVALID", phase="transform")
        return value
    raise LegacyMigrationError("MANIFEST_TRANSFORM_UNSUPPORTED", phase="manifest")


def _digest_value(value: Any) -> Any:
    if isinstance(value, datetime):
        normalized = value.astimezone(timezone.utc).isoformat(timespec="microseconds")
        return normalized.replace("+00:00", "Z")
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"$bytes": base64.b64encode(bytes(value)).decode("ascii")}
    return value


def transform_row(table: Mapping[str, Any], row: Sequence[Any]) -> tuple[Any, ...]:
    columns = list(table["columns"])
    if len(row) != len(columns):
        raise LegacyMigrationError("SOURCE_ROW_WIDTH_MISMATCH", phase="transform")
    return tuple(
        transform_value(str(table["name"]), column, value)
        for column, value in zip(columns, row, strict=True)
    )


def _unique_predicate(table: Mapping[str, Any], unique: Mapping[str, Any]) -> str:
    if not bool(unique.get("partial")):
        return ""
    for index in table["explicit_indexes"]:
        if str(index["name"]) != str(unique["name"]):
            continue
        match = re.search(r"\bWHERE\b(?P<predicate>.*)$", str(index["source_sql"]), re.I | re.S)
        if match:
            return match.group("predicate").strip()
    raise LegacyMigrationError("MANIFEST_PARTIAL_INDEX_INVALID", phase="manifest")


def _validate_source_constraints(
    connection: sqlite3.Connection, table: Mapping[str, Any]
) -> None:
    name = str(table["name"])
    try:
        primary_key = [str(column) for column in table["primary_key"]]
        if not primary_key:
            raise LegacyMigrationError("MANIFEST_PRIMARY_KEY_MISSING", phase="manifest")
        pk_columns = ", ".join(_quote(column) for column in primary_key)
        pk_null = " OR ".join(f"{_quote(column)} IS NULL" for column in primary_key)
        null_count = connection.execute(
            f"SELECT count(*) FROM {_quote(name)} WHERE {pk_null}"
        ).fetchone()[0]
        duplicate_count = connection.execute(
            f"SELECT count(*) FROM (SELECT {pk_columns} FROM {_quote(name)} "
            f"GROUP BY {pk_columns} HAVING count(*) > 1) AS duplicate_keys"
        ).fetchone()[0]
        if null_count or duplicate_count:
            raise LegacyMigrationError("SOURCE_PRIMARY_KEY_INVALID", phase="validate")

        for unique in table["unique_checks"]:
            if str(unique.get("origin")) == "pk":
                continue
            columns = [str(column) for column in unique["columns"]]
            if not columns:
                raise LegacyMigrationError("MANIFEST_UNIQUE_UNSUPPORTED", phase="manifest")
            rendered = ", ".join(_quote(column) for column in columns)
            filters = [f"{_quote(column)} IS NOT NULL" for column in columns]
            predicate = _unique_predicate(table, unique)
            if predicate:
                filters.append(f"({predicate})")
            where = " AND ".join(filters)
            duplicates = connection.execute(
                f"SELECT count(*) FROM (SELECT {rendered} FROM {_quote(name)} "
                f"WHERE {where} GROUP BY {rendered} HAVING count(*) > 1) AS duplicate_keys"
            ).fetchone()[0]
            if duplicates:
                raise LegacyMigrationError("SOURCE_UNIQUE_INVALID", phase="validate")

        for check in table["checks"]:
            failures = connection.execute(
                f"SELECT count(*) FROM {_quote(name)} WHERE NOT ({check})"
            ).fetchone()[0]
            if failures:
                raise LegacyMigrationError("SOURCE_CHECK_INVALID", phase="validate")

        sequence = table.get("sequence_check")
        if sequence:
            for column in sequence["identity_columns"]:
                maximum = connection.execute(
                    f"SELECT max({_quote(str(column))}) FROM {_quote(name)}"
                ).fetchone()[0]
                row = connection.execute(
                    "SELECT seq FROM sqlite_sequence WHERE name=?", (name,)
                ).fetchone()
                if maximum is not None and (row is None or int(row[0]) < int(maximum)):
                    raise LegacyMigrationError("SOURCE_SEQUENCE_INVALID", phase="validate")
    except LegacyMigrationError:
        raise
    except sqlite3.Error:
        raise LegacyMigrationError("SOURCE_CONSTRAINT_VALIDATION_FAILED", phase="validate") from None


def _scan_table(
    connection: sqlite3.Connection,
    table: Mapping[str, Any],
    *,
    batch_size: int,
) -> dict[str, Any]:
    _validate_source_constraints(connection, table)
    primary_key = [str(column) for column in table["primary_key"]]
    column_names = [str(column["name"]) for column in table["columns"]]
    pk_positions = [column_names.index(column) for column in primary_key]
    pk_digest = _CanonicalDigest()
    row_digest = _CanonicalDigest()
    count = 0
    try:
        cursor = connection.execute(str(table["source_query"]))
        while rows := cursor.fetchmany(batch_size):
            for source_row in rows:
                transformed = transform_row(table, tuple(source_row))
                pk_digest.add([_digest_value(transformed[index]) for index in pk_positions])
                row_digest.add([_digest_value(value) for value in transformed])
                count += 1
    except LegacyMigrationError:
        raise
    except sqlite3.Error:
        raise LegacyMigrationError("SOURCE_ROW_READ_FAILED", phase="transform") from None
    return {
        "table": str(table["name"]),
        "source": str(table["source_database"]),
        "wave": int(table["migration_wave"]),
        "sourceCount": count,
        "pkSha256": pk_digest.hexdigest(),
        "rowSha256": row_digest.hexdigest(),
        "uniqueChecks": len(table["unique_checks"]),
        "foreignKeyChecks": len(table["foreign_keys"]),
        "checkExpressions": len(table["checks"]),
        "jsonColumns": len(table["enum_json_time_checks"]["json_text_columns"]),
        "timeColumns": len(table["enum_json_time_checks"]["timestamptz_columns"]),
        "sequenceColumns": len(
            (table.get("sequence_check") or {}).get("identity_columns", [])
        ),
        "triggerChecks": len(table["trigger_checks"]),
    }


def _validate_cross_database_foreign_keys(
    snapshots: SnapshotBundle, tables: Sequence[Mapping[str, Any]]
) -> int:
    connection = sqlite3.connect(":memory:", uri=True)
    try:
        connection.execute("PRAGMA query_only=ON")
        connection.execute(
            "ATTACH DATABASE ? AS main_source",
            (f"{snapshots.main.path.as_uri()}?mode=ro",),
        )
        connection.execute(
            "ATTACH DATABASE ? AS notion_source",
            (f"{snapshots.notion.path.as_uri()}?mode=ro",),
        )
        checks = 0
        source_by_table = {
            str(table["name"]): str(table["source_database"]) for table in tables
        }
        for table in tables:
            source_alias = f"{source_by_table[str(table['name'])]}_source"
            for foreign_key in table["foreign_keys"]:
                target_alias = f"{source_by_table[str(foreign_key['target_table'])]}_source"
                local_columns = [str(column) for column in foreign_key["columns"]]
                target_columns = [str(column) for column in foreign_key["target_columns"]]
                joins = " AND ".join(
                    f"child.{_quote(local)} = parent.{_quote(target)}"
                    for local, target in zip(local_columns, target_columns, strict=True)
                )
                present = " AND ".join(
                    f"child.{_quote(column)} IS NOT NULL" for column in local_columns
                )
                missing = f"parent.{_quote(target_columns[0])} IS NULL"
                query = (
                    f"SELECT count(*) FROM {_quote(source_alias)}.{_quote(str(table['name']))} AS child "
                    f"LEFT JOIN {_quote(target_alias)}.{_quote(str(foreign_key['target_table']))} AS parent "
                    f"ON {joins} WHERE {present} AND {missing}"
                )
                if connection.execute(query).fetchone()[0]:
                    raise LegacyMigrationError("SOURCE_FOREIGN_KEY_ORPHAN", phase="validate")
                checks += 1
        return checks
    except LegacyMigrationError:
        raise
    except sqlite3.Error:
        raise LegacyMigrationError("SOURCE_FOREIGN_KEY_VALIDATION_FAILED", phase="validate") from None
    finally:
        connection.close()


def scan_sources(
    snapshots: SnapshotBundle,
    manifest: Mapping[str, Any],
    *,
    batch_size: int,
) -> tuple[list[dict[str, Any]], dict[str, str], int]:
    if batch_size < 1 or batch_size > 100_000:
        raise LegacyMigrationError("BATCH_SIZE_INVALID", phase="configuration")
    tables = list(manifest["tables"])
    reports: list[dict[str, Any]] = []
    schema_digests: dict[str, str] = {}
    expected_triggers = list(manifest["triggers"])
    for source in ("main", "notion"):
        connection = _open_read_only_sqlite(snapshots.for_source(source).path)
        try:
            source_tables = [
                table for table in tables if str(table["source_database"]) == source
            ]
            schema_digests[source] = _validate_source_schema(
                connection,
                source=source,
                tables=source_tables,
                expected_triggers=expected_triggers,
            )
            reports.extend(
                _scan_table(connection, table, batch_size=batch_size)
                for table in source_tables
            )
        finally:
            connection.close()
    foreign_key_checks = _validate_cross_database_foreign_keys(snapshots, tables)
    if len(reports) != 48:
        raise LegacyMigrationError("SOURCE_REPORT_INVENTORY_MISMATCH", phase="verify")
    return reports, schema_digests, foreign_key_checks


def wave_topological_order(manifest: Mapping[str, Any]) -> list[str]:
    """Return a deterministic FK-safe order while preserving waves 1 through 6."""

    tables = {str(table["name"]): table for table in manifest["tables"]}
    ordered: list[str] = []
    completed: set[str] = set()
    for wave in range(1, 7):
        remaining = {
            name
            for name, table in tables.items()
            if int(table["migration_wave"]) == wave
        }
        while remaining:
            ready: list[str] = []
            for name in remaining:
                dependencies = {
                    str(foreign_key["target_table"])
                    for foreign_key in tables[name]["foreign_keys"]
                    if str(foreign_key["target_table"]) != name
                }
                if dependencies.issubset(completed | (set(tables) - remaining)):
                    ready.append(name)
            if not ready:
                raise LegacyMigrationError("MANIFEST_FOREIGN_KEY_CYCLE", phase="manifest")
            for name in sorted(ready):
                ordered.append(name)
                completed.add(name)
                remaining.remove(name)
    if set(ordered) != set(tables):
        raise LegacyMigrationError("MANIFEST_WAVE_INVENTORY_INVALID", phase="manifest")
    # Final independent proof prevents a future wave edit from hiding a reverse FK.
    positions = {name: index for index, name in enumerate(ordered)}
    for name, table in tables.items():
        for foreign_key in table["foreign_keys"]:
            target = str(foreign_key["target_table"])
            if target != name and positions[target] > positions[name]:
                raise LegacyMigrationError("MANIFEST_FOREIGN_KEY_ORDER_INVALID", phase="manifest")
    return ordered


def _expected_target_columns(
    table: Mapping[str, Any],
    *,
    include_extensions: bool = False,
) -> list[tuple[str, str]]:
    columns = [
        (str(column["name"]), str(column["transform"]["target_type"]))
        for column in table["columns"]
    ]
    name = str(table["name"])
    if name == "users":
        # Admin current-head canonical baseline deliberately orders the
        # compatibility/profile columns differently from legacy SQLite.
        source = dict(columns)
        columns = [
            ("id", source["id"]),
            ("email", source["email"]),
            ("password_hash", source["password_hash"]),
            ("display_name", source["display_name"]),
            ("created_at", source["created_at"]),
            ("avatar_url", source["avatar_url"]),
            ("role", source["role"]),
            ("updated_at", source["updated_at"]),
            ("status", "text"),
        ]
    elif name == "story_workspace_workspaces":
        columns = [
            (column_name, "jsonb" if column_name == "settings" else column_type)
            for column_name, column_type in columns
        ]
        columns.append(("status", "text"))
    if include_extensions:
        columns.extend(APPROVED_TARGET_COLUMN_EXTENSIONS.get(name, ()))
    return columns


def _target_type(data_type: str) -> str:
    aliases = {
        "timestamp with time zone": "timestamptz",
        "character varying": "text",
    }
    return aliases.get(data_type, data_type)


def _expected_target_indexes(
    manifest: Mapping[str, Any],
    *,
    enabled_extensions: frozenset[str] = frozenset(),
) -> dict[str, tuple[str, bool]]:
    baseline_tables = set(BASELINE_TABLES)
    expected: dict[str, tuple[str, bool]] = {}
    for table in manifest["tables"]:
        name = str(table["name"])
        if name in baseline_tables:
            continue
        for index in table["explicit_indexes"]:
            source_sql = str(index["source_sql"])
            expected[str(index["name"])] = (
                name,
                bool(re.match(r"^\s*CREATE\s+UNIQUE\s+INDEX\b", source_sql, re.I)),
            )
    for statement in BASELINE_INDEX_DDL:
        match = re.match(
            r"^CREATE\s+(?P<unique>UNIQUE\s+)?INDEX\s+(?P<name>[a-z0-9_]+)\s+ON\s+"
            r"(?P<table>[a-z0-9_]+)",
            statement,
            re.I,
        )
        if not match:
            raise LegacyMigrationError("MANIFEST_BASELINE_INDEX_INVALID", phase="manifest")
        expected[match.group("name")] = (
            match.group("table"),
            bool(match.group("unique")),
        )
    expected.update(
        {
            name: contract
            for name, contract in APPROVED_TARGET_INDEX_EXTENSIONS.items()
            if contract[0] in enabled_extensions
        }
    )
    return expected


def _expected_target_constraints(
    manifest: Mapping[str, Any],
    *,
    enabled_extensions: frozenset[str] = frozenset(),
) -> tuple[
    dict[str, tuple[str, ...]],
    set[tuple[str, tuple[str, ...], str, tuple[str, ...], str, str]],
    set[tuple[str, tuple[str, ...]]],
    dict[str, int],
]:
    primary_keys: dict[str, tuple[str, ...]] = {}
    foreign_keys: set[
        tuple[str, tuple[str, ...], str, tuple[str, ...], str, str]
    ] = set()
    unique_constraints: set[tuple[str, tuple[str, ...]]] = set()
    check_counts: dict[str, int] = {}
    for table in manifest["tables"]:
        name = str(table["name"])
        primary_keys[name] = tuple(str(column) for column in table["primary_key"])
        for foreign_key in table["foreign_keys"]:
            on_update = str(foreign_key["on_update"])
            on_delete = str(foreign_key["on_delete"])
            if name in BASELINE_TABLES:
                # Approved Admin current-head baseline tightens these deletes.
                on_delete = "RESTRICT"
            foreign_keys.add(
                (
                    name,
                    tuple(str(column) for column in foreign_key["columns"]),
                    str(foreign_key["target_table"]),
                    tuple(str(column) for column in foreign_key["target_columns"]),
                    on_update,
                    on_delete,
                )
            )
        if name not in BASELINE_TABLES:
            for unique in table["unique_checks"]:
                if str(unique["origin"]) == "u":
                    unique_constraints.add(
                        (name, tuple(str(column) for column in unique["columns"]))
                    )
        check_counts[name] = len(table["checks"])
    check_counts["users"] += 1
    check_counts["story_workspace_workspaces"] += 1
    check_counts["story_workspace_stories"] += 2
    for name, count in APPROVED_TARGET_CHECK_COUNT_EXTENSIONS.items():
        if name in enabled_extensions:
            check_counts[name] += count
    return primary_keys, foreign_keys, unique_constraints, check_counts


def _validate_target_constraints_and_indexes(
    connection: Any,
    manifest: Mapping[str, Any],
    *,
    enabled_extensions: frozenset[str] = frozenset(),
) -> dict[str, int]:
    expected_names = {str(table["name"]) for table in manifest["tables"]}
    expected_pk, expected_fk, expected_unique, expected_checks = (
        _expected_target_constraints(
            manifest,
            enabled_extensions=enabled_extensions,
        )
    )
    action_names = {
        "a": "NO ACTION",
        "r": "RESTRICT",
        "c": "CASCADE",
        "n": "SET NULL",
        "d": "SET DEFAULT",
    }
    constraint_rows = connection.execute(
        "SELECT c.relname, con.contype, "
        "ARRAY(SELECT a.attname FROM unnest(con.conkey) WITH ORDINALITY AS k(attnum,pos) "
        "JOIN pg_catalog.pg_attribute AS a ON a.attrelid=con.conrelid "
        "AND a.attnum=k.attnum ORDER BY k.pos), "
        "rc.relname, "
        "ARRAY(SELECT a.attname FROM unnest(con.confkey) WITH ORDINALITY AS k(attnum,pos) "
        "JOIN pg_catalog.pg_attribute AS a ON a.attrelid=con.confrelid "
        "AND a.attnum=k.attnum ORDER BY k.pos), "
        "con.confupdtype, con.confdeltype, con.convalidated "
        "FROM pg_catalog.pg_constraint AS con "
        "JOIN pg_catalog.pg_class AS c ON c.oid=con.conrelid "
        "JOIN pg_catalog.pg_namespace AS n ON n.oid=c.relnamespace "
        "LEFT JOIN pg_catalog.pg_class AS rc ON rc.oid=con.confrelid "
        "WHERE n.nspname=%s AND con.contype IN ('p','u','c','f')",
        (TARGET_SCHEMA,),
    ).fetchall()
    actual_pk: dict[str, tuple[str, ...]] = {}
    actual_fk: set[
        tuple[str, tuple[str, ...], str, tuple[str, ...], str, str]
    ] = set()
    actual_unique: set[tuple[str, tuple[str, ...]]] = set()
    actual_checks = {name: 0 for name in expected_names}
    for row in constraint_rows:
        values = tuple(row.values()) if isinstance(row, Mapping) else tuple(row)
        name = str(values[0])
        if name not in expected_names:
            continue
        constraint_type = str(values[1])
        columns = tuple(str(column) for column in (values[2] or ()))
        if not bool(values[7]):
            raise LegacyMigrationError("TARGET_CONSTRAINT_NOT_VALIDATED", phase="target")
        if constraint_type == "p":
            actual_pk[name] = columns
        elif constraint_type == "u":
            actual_unique.add((name, columns))
        elif constraint_type == "c":
            actual_checks[name] += 1
        elif constraint_type == "f":
            actual_fk.add(
                (
                    name,
                    columns,
                    str(values[3]),
                    tuple(str(column) for column in (values[4] or ())),
                    action_names.get(str(values[5]), "INVALID"),
                    action_names.get(str(values[6]), "INVALID"),
                )
            )
    if actual_pk != expected_pk:
        raise LegacyMigrationError("TARGET_PRIMARY_KEY_CONTRACT_MISMATCH", phase="target")
    if actual_fk != expected_fk:
        raise LegacyMigrationError("TARGET_FOREIGN_KEY_CONTRACT_MISMATCH", phase="target")
    if actual_unique != expected_unique:
        raise LegacyMigrationError("TARGET_UNIQUE_CONTRACT_MISMATCH", phase="target")
    if actual_checks != expected_checks:
        raise LegacyMigrationError("TARGET_CHECK_CONTRACT_MISMATCH", phase="target")

    expected_indexes = _expected_target_indexes(
        manifest,
        enabled_extensions=enabled_extensions,
    )
    index_rows = connection.execute(
        "SELECT c.relname, irel.relname, i.indisunique, i.indisvalid "
        "FROM pg_catalog.pg_index AS i "
        "JOIN pg_catalog.pg_class AS c ON c.oid=i.indrelid "
        "JOIN pg_catalog.pg_class AS irel ON irel.oid=i.indexrelid "
        "JOIN pg_catalog.pg_namespace AS n ON n.oid=c.relnamespace "
        "LEFT JOIN pg_catalog.pg_constraint AS con ON con.conindid=i.indexrelid "
        "WHERE n.nspname=%s AND con.oid IS NULL",
        (TARGET_SCHEMA,),
    ).fetchall()
    actual_indexes: dict[str, tuple[str, bool]] = {}
    for row in index_rows:
        values = tuple(row.values()) if isinstance(row, Mapping) else tuple(row)
        table_name = str(values[0])
        if table_name not in expected_names:
            continue
        if not bool(values[3]):
            raise LegacyMigrationError("TARGET_INDEX_NOT_VALID", phase="target")
        actual_indexes[str(values[1])] = (table_name, bool(values[2]))
    if actual_indexes != expected_indexes:
        raise LegacyMigrationError("TARGET_INDEX_CONTRACT_MISMATCH", phase="target")
    return {
        "primaryKeys": len(actual_pk),
        "foreignKeys": len(actual_fk),
        "uniqueConstraints": len(actual_unique),
        "checks": sum(actual_checks.values()),
        "explicitIndexes": len(actual_indexes),
    }


def _fetch_scalar(connection: Any, query: str, parameters: Sequence[Any] = ()) -> Any:
    cursor = connection.execute(query, tuple(parameters))
    row = cursor.fetchone()
    if row is None:
        raise LegacyMigrationError("TARGET_QUERY_EMPTY", phase="target")
    if isinstance(row, Mapping):
        return next(iter(row.values()))
    return row[0]


def _validate_target_catalog(
    connection: Any, manifest: Mapping[str, Any]
) -> dict[str, Any]:
    try:
        version = _fetch_scalar(
            connection, "SELECT version_num FROM dream_alembic_version"
        )
        if str(version) != EXPECTED_ALEMBIC_HEAD:
            raise LegacyMigrationError("TARGET_ALEMBIC_HEAD_MISMATCH", phase="target")
        database_name = str(_fetch_scalar(connection, "SELECT current_database()"))
        rows = connection.execute(
            "SELECT table_name, column_name, data_type "
            "FROM information_schema.columns WHERE table_schema=%s "
            "ORDER BY table_name, ordinal_position",
            (TARGET_SCHEMA,),
        ).fetchall()
        columns_by_table: dict[str, list[tuple[str, str]]] = {}
        for row in rows:
            if isinstance(row, Mapping):
                table_name = str(row["table_name"])
                column_name = str(row["column_name"])
                data_type = str(row["data_type"])
            else:
                table_name, column_name, data_type = map(str, row)
            columns_by_table.setdefault(table_name, []).append(
                (column_name, _target_type(data_type))
            )
        enabled_extensions: set[str] = set()
        for table in manifest["tables"]:
            name = str(table["name"])
            actual_columns = columns_by_table.get(name)
            base_columns = _expected_target_columns(table)
            extended_columns = _expected_target_columns(
                table,
                include_extensions=True,
            )
            if actual_columns == extended_columns and extended_columns != base_columns:
                enabled_extensions.add(name)
            elif actual_columns != base_columns:
                raise LegacyMigrationError("TARGET_TABLE_CONTRACT_MISMATCH", phase="target")

        trigger_rows = connection.execute(
            "SELECT c.relname, t.tgname, t.tgenabled "
            "FROM pg_catalog.pg_trigger AS t "
            "JOIN pg_catalog.pg_class AS c ON c.oid=t.tgrelid "
            "JOIN pg_catalog.pg_namespace AS n ON n.oid=c.relnamespace "
            "WHERE n.nspname=%s AND NOT t.tgisinternal",
            (TARGET_SCHEMA,),
        ).fetchall()
        actual_triggers: dict[tuple[str, str], str] = {}
        for row in trigger_rows:
            if isinstance(row, Mapping):
                key = (str(row["relname"]), str(row["tgname"]))
                enabled = str(row["tgenabled"])
            else:
                key = (str(row[0]), str(row[1]))
                enabled = str(row[2])
            actual_triggers[key] = enabled
        for trigger in manifest["triggers"]:
            key = (str(trigger["table"]), str(trigger["name"]))
            if key not in actual_triggers or actual_triggers[key] == "D":
                raise LegacyMigrationError("TARGET_TRIGGER_CONTRACT_MISMATCH", phase="target")
        expected_trigger_keys = {
            (str(trigger["table"]), str(trigger["name"]))
            for trigger in manifest["triggers"]
        }
        dream_table_names = {str(table["name"]) for table in manifest["tables"]}
        external = {
            key
            for key in actual_triggers
            if key[0] in dream_table_names and key not in expected_trigger_keys
        }
        if not external.issubset(APPROVED_EXTERNAL_TRIGGERS):
            raise LegacyMigrationError("TARGET_TRIGGER_EXTENSION_UNAPPROVED", phase="target")
        ownership_rows = connection.execute(
            "SELECT c.relname, pg_catalog.pg_get_userbyid(c.relowner), "
            "COALESCE(c.relacl::text,'') "
            "FROM pg_catalog.pg_class AS c "
            "JOIN pg_catalog.pg_namespace AS n ON n.oid=c.relnamespace "
            "WHERE n.nspname=%s AND c.relkind IN ('r','p') ORDER BY c.relname",
            (TARGET_SCHEMA,),
        ).fetchall()
        ownership_contract: list[list[str]] = []
        for row in ownership_rows:
            values = tuple(row.values()) if isinstance(row, Mapping) else tuple(row)
            if str(values[0]) in dream_table_names:
                ownership_contract.append([str(value) for value in values])
        if len(ownership_contract) != len(dream_table_names):
            raise LegacyMigrationError("TARGET_OWNER_ACL_INVENTORY_MISMATCH", phase="target")
        constraint_receipt = _validate_target_constraints_and_indexes(
            connection,
            manifest,
            enabled_extensions=frozenset(enabled_extensions),
        )
        return {
            "databaseSha256": hashlib.sha256(database_name.encode("utf-8")).hexdigest(),
            "alembicHead": EXPECTED_ALEMBIC_HEAD,
            "tables": len(manifest["tables"]),
            "columns": sum(
                len(columns_by_table[str(table["name"])])
                for table in manifest["tables"]
            ),
            "approvedExtensionTables": sorted(enabled_extensions),
            "triggers": len(manifest["triggers"]),
            "ownerAclSha256": hashlib.sha256(
                _canonical_json(ownership_contract).encode("utf-8")
            ).hexdigest(),
            **constraint_receipt,
        }
    except LegacyMigrationError:
        raise
    except Exception:
        raise LegacyMigrationError("TARGET_CATALOG_VALIDATION_FAILED", phase="target") from None


def _stage_name(run_id: UUID, table_name: str) -> str:
    digest = hashlib.sha256(f"{run_id}:{table_name}".encode("utf-8")).hexdigest()[:12]
    return f"dream_stage_{digest}"


def _stage_table(
    connection: Any,
    snapshots: SnapshotBundle,
    table: Mapping[str, Any],
    *,
    run_id: UUID,
    batch_size: int,
) -> tuple[str, int]:
    name = str(table["name"])
    stage = _stage_name(run_id, name)
    target = _qualified(TARGET_SCHEMA, name)
    try:
        connection.execute(
            f"CREATE TEMP TABLE {_quote(stage)} ("
            f"LIKE {target} INCLUDING DEFAULTS INCLUDING GENERATED INCLUDING IDENTITY, "
            '"migration_run_id" UUID NOT NULL)'
        )
        column_names = [str(column["name"]) for column in table["columns"]]
        placeholders = ["%s"] * len(column_names)
        if name == "story_workspace_workspaces":
            settings_position = column_names.index("settings")
            placeholders[settings_position] = "CAST(%s AS jsonb)"
        insert = (
            f"INSERT INTO {_quote(stage)} (\"migration_run_id\", "
            + ", ".join(_quote(column) for column in column_names)
            + ") VALUES (%s, "
            + ", ".join(placeholders)
            + ")"
        )
        source_connection = _open_read_only_sqlite(
            snapshots.for_source(str(table["source_database"])).path
        )
        count = 0
        try:
            source_cursor = source_connection.execute(str(table["source_query"]))
            target_cursor = connection.cursor()
            while rows := source_cursor.fetchmany(batch_size):
                parameters: list[tuple[Any, ...]] = []
                for source_row in rows:
                    transformed = list(transform_row(table, tuple(source_row)))
                    if name == "story_workspace_workspaces":
                        settings_position = column_names.index("settings")
                        transformed[settings_position] = _canonical_json(
                            transformed[settings_position]
                        )
                    parameters.append((run_id, *transformed))
                target_cursor.executemany(insert, parameters)
                count += len(parameters)
        finally:
            source_connection.close()
        staged = int(_fetch_scalar(connection, f"SELECT count(*) FROM {_quote(stage)}"))
        if staged != count:
            raise LegacyMigrationError("STAGING_COUNT_MISMATCH", phase="staging")
        return stage, staged
    except LegacyMigrationError:
        raise
    except Exception:
        raise LegacyMigrationError("STAGING_WRITE_FAILED", phase="staging") from None


def _normalize_database_row(
    table: Mapping[str, Any], values: Sequence[Any]
) -> tuple[Any, ...]:
    columns = list(table["columns"])
    if len(values) != len(columns):
        raise LegacyMigrationError("TARGET_ROW_WIDTH_MISMATCH", phase="verify")
    normalized: list[Any] = []
    for column, value in zip(columns, values, strict=True):
        if (
            str(table["name"]) == "story_workspace_workspaces"
            and str(column["name"]) == "settings"
            and isinstance(value, (dict, list, int, float, bool))
        ):
            normalized.append(value)
        else:
            normalized.append(transform_value(str(table["name"]), column, value))
    return tuple(normalized)


def _digest_database_query(
    connection: Any,
    table: Mapping[str, Any],
    *,
    from_clause: str,
    alias: str,
    batch_size: int,
) -> tuple[int, str, str]:
    columns = [str(column["name"]) for column in table["columns"]]
    primary_key = [str(column) for column in table["primary_key"]]
    pk_positions = [columns.index(column) for column in primary_key]
    selected = ", ".join(f"{alias}.{_quote(column)}" for column in columns)
    ordered = ", ".join(f"{alias}.{_quote(column)}" for column in primary_key)
    pk_digest = _CanonicalDigest()
    row_digest = _CanonicalDigest()
    try:
        cursor = connection.execute(
            f"SELECT {selected} FROM {from_clause} ORDER BY {ordered}"
        )
        while rows := cursor.fetchmany(batch_size):
            for row in rows:
                values = tuple(row.values()) if isinstance(row, Mapping) else tuple(row)
                normalized = _normalize_database_row(table, values)
                pk_digest.add(
                    [_digest_value(normalized[position]) for position in pk_positions]
                )
                row_digest.add([_digest_value(value) for value in normalized])
    except LegacyMigrationError:
        raise
    except Exception:
        raise LegacyMigrationError("TARGET_DIGEST_QUERY_FAILED", phase="verify") from None
    return pk_digest.count, pk_digest.hexdigest(), row_digest.hexdigest()


def _row_comparison(table: Mapping[str, Any], left: str, right: str) -> str:
    columns = [str(column["name"]) for column in table["columns"]]
    return "ROW(" + ", ".join(
        f"{left}.{_quote(column)}" for column in columns
    ) + ") IS DISTINCT FROM ROW(" + ", ".join(
        f"{right}.{_quote(column)}" for column in columns
    ) + ")"


def _pk_join(table: Mapping[str, Any], left: str, right: str) -> str:
    return " AND ".join(
        f"{left}.{_quote(str(column))} = {right}.{_quote(str(column))}"
        for column in table["primary_key"]
    )


def _staged_drift_summary(
    connection: Any,
    table: Mapping[str, Any],
    stage: str,
) -> dict[str, Any]:
    """Return schema/count-only evidence for rows changed after import."""

    name = str(table["name"])
    target = _qualified(TARGET_SCHEMA, name)
    columns = [str(column["name"]) for column in table["columns"]]
    comparison = _row_comparison(table, "target", "stage")
    joined = (
        f"{_quote(stage)} AS stage JOIN {target} AS target "
        f"ON {_pk_join(table, 'stage', 'target')}"
    )
    changed_columns: dict[str, int] = {}
    for column in columns:
        count = int(
            _fetch_scalar(
                connection,
                f"SELECT count(*) FROM {joined} WHERE {comparison} AND "
                f"target.{_quote(column)} IS DISTINCT FROM stage.{_quote(column)}",
            )
        )
        if count:
            changed_columns[column] = count
    newer_count = 0
    if "updated_at" in columns:
        newer_count = int(
            _fetch_scalar(
                connection,
                f"SELECT count(*) FROM {joined} WHERE {comparison} AND "
                "target.updated_at > stage.updated_at",
            )
        )
    return {
        "changedColumns": changed_columns,
        "postCutoverNewer": newer_count,
    }


def _baseline_conflicts(
    connection: Any, table: Mapping[str, Any], stage: str
) -> tuple[int, int, int]:
    name = str(table["name"])
    target = _qualified(TARGET_SCHEMA, name)
    first_pk = _quote(str(table["primary_key"][0]))
    query = (
        "SELECT "
        f"count(*) FILTER (WHERE target.{first_pk} IS NULL), "
        f"count(*) FILTER (WHERE target.{first_pk} IS NOT NULL AND "
        f"{_row_comparison(table, 'target', 'stage')}), "
        f"count(*) FILTER (WHERE target.{first_pk} IS NOT NULL) "
        f"FROM {_quote(stage)} AS stage LEFT JOIN {target} AS target "
        f"ON {_pk_join(table, 'stage', 'target')}"
    )
    row = connection.execute(query).fetchone()
    values = tuple(row.values()) if isinstance(row, Mapping) else tuple(row)
    missing, mismatched, matched = map(int, values)
    if name == "users":
        unique_conflicts = int(
            _fetch_scalar(
                connection,
                f"SELECT count(*) FROM {_quote(stage)} AS stage "
                f"JOIN {target} AS target ON target.email=stage.email "
                "WHERE target.id IS DISTINCT FROM stage.id",
            )
        )
        if unique_conflicts:
            mismatched += unique_conflicts
    return missing, mismatched, matched


def _insert_from_stage(
    connection: Any,
    table: Mapping[str, Any],
    stage: str,
    *,
    baseline: bool,
) -> int:
    name = str(table["name"])
    target = _qualified(TARGET_SCHEMA, name)
    columns = [str(column["name"]) for column in table["columns"]]
    rendered_columns = ", ".join(_quote(column) for column in columns)
    order = ", ".join(f"stage.{_quote(str(column))}" for column in table["primary_key"])
    where = ""
    if baseline:
        where = (
            f" WHERE NOT EXISTS (SELECT 1 FROM {target} AS target "
            f"WHERE {_pk_join(table, 'stage', 'target')})"
        )
    statement = (
        f"INSERT INTO {target} ({rendered_columns}) "
        f"SELECT "
        + ", ".join(f"stage.{_quote(column)}" for column in columns)
        + f" FROM {_quote(stage)} AS stage{where} ORDER BY {order}"
    )
    try:
        cursor = connection.execute(statement)
        return int(cursor.rowcount)
    except Exception as error:
        # Schema identifiers and SQLSTATE are safe operational evidence. Never
        # expose the driver message/detail because either can contain row data.
        details: dict[str, Any] = {"table": name}
        sqlstate = getattr(error, "sqlstate", None)
        if isinstance(sqlstate, str) and re.fullmatch(r"[0-9A-Z]{5}", sqlstate):
            details["sqlstate"] = sqlstate
        diagnostic = getattr(error, "diag", None)
        if diagnostic is not None:
            for attribute, key in (
                ("constraint_name", "constraint"),
                ("column_name", "column"),
                ("table_name", "reportedTable"),
            ):
                value = getattr(diagnostic, attribute, None)
                if isinstance(value, str) and _IDENTIFIER.fullmatch(value):
                    details[key] = value
        raise LegacyMigrationError(
            "TARGET_IMPORT_FAILED",
            phase="import",
            details=details,
        ) from None


def _validate_target_conflicts(
    connection: Any,
    tables: Mapping[str, Mapping[str, Any]],
    stage_names: Mapping[str, str],
    reports: Mapping[str, dict[str, Any]],
    *,
    commit: bool,
    approve_baseline_inserts: bool,
) -> None:
    conflicts: list[dict[str, Any]] = []
    approval_requirements: list[dict[str, Any]] = []
    for name, table in tables.items():
        if name in BASELINE_TABLES:
            missing, mismatched, matched = _baseline_conflicts(
                connection, table, stage_names[name]
            )
            reports[name]["baselineMatched"] = matched
            reports[name]["baselineMissing"] = missing
            reports[name]["conflicts"] = mismatched
            if mismatched:
                conflicts.append(
                    {
                        "table": name,
                        "kind": "baseline_row_or_unique_drift",
                        "count": mismatched,
                    }
                )
            if missing and commit and not approve_baseline_inserts:
                approval_requirements.append(
                    {
                        "table": name,
                        "kind": "missing_baseline_rows",
                        "count": missing,
                    }
                )
        else:
            target_count = int(
                _fetch_scalar(
                    connection,
                    f"SELECT count(*) FROM {_qualified(TARGET_SCHEMA, name)}",
                )
            )
            reports[name]["preexistingTargetCount"] = target_count
            reports[name]["conflicts"] = target_count
            if target_count:
                conflicts.append(
                    {
                        "table": name,
                        "kind": "nonbaseline_target_not_empty",
                        "count": target_count,
                    }
                )
    if conflicts:
        raise LegacyMigrationError(
            "TARGET_CONFLICTS_DETECTED",
            phase="conflict",
            details={"conflicts": sorted(conflicts, key=lambda item: item["table"])},
        )
    if approval_requirements:
        raise LegacyMigrationError(
            "BASELINE_INSERT_APPROVAL_REQUIRED",
            phase="conflict",
            details={
                "approvalRequirements": sorted(
                    approval_requirements, key=lambda item: item["table"]
                )
            },
        )


def _validate_target_foreign_keys(
    connection: Any, manifest: Mapping[str, Any]
) -> int:
    checks = 0
    try:
        for table in manifest["tables"]:
            table_name = str(table["name"])
            for foreign_key in table["foreign_keys"]:
                local_columns = [str(column) for column in foreign_key["columns"]]
                target_columns = [str(column) for column in foreign_key["target_columns"]]
                joins = " AND ".join(
                    f"child.{_quote(local)} = parent.{_quote(target)}"
                    for local, target in zip(local_columns, target_columns, strict=True)
                )
                present = " AND ".join(
                    f"child.{_quote(column)} IS NOT NULL" for column in local_columns
                )
                missing = f"parent.{_quote(target_columns[0])} IS NULL"
                query = (
                    f"SELECT count(*) FROM {_qualified(TARGET_SCHEMA, table_name)} AS child "
                    f"LEFT JOIN {_qualified(TARGET_SCHEMA, str(foreign_key['target_table']))} AS parent "
                    f"ON {joins} WHERE {present} AND {missing}"
                )
                if int(_fetch_scalar(connection, query)):
                    raise LegacyMigrationError("TARGET_FOREIGN_KEY_ORPHAN", phase="verify")
                checks += 1
        return checks
    except LegacyMigrationError:
        raise
    except Exception:
        raise LegacyMigrationError("TARGET_FOREIGN_KEY_VALIDATION_FAILED", phase="verify") from None


def _calibrate_sequences(
    connection: Any, manifest: Mapping[str, Any]
) -> int:
    calibrated = 0
    try:
        for table in manifest["tables"]:
            name = str(table["name"])
            sequence_check = table.get("sequence_check")
            if not sequence_check:
                continue
            for column in sequence_check["identity_columns"]:
                sequence_name = _fetch_scalar(
                    connection,
                    "SELECT pg_get_serial_sequence(%s, %s)",
                    (f"{TARGET_SCHEMA}.{name}", str(column)),
                )
                if not sequence_name:
                    raise LegacyMigrationError("TARGET_SEQUENCE_MISSING", phase="verify")
                maximum = _fetch_scalar(
                    connection,
                    f"SELECT max({_quote(str(column))}) FROM {_qualified(TARGET_SCHEMA, name)}",
                )
                connection.execute(
                    "SELECT setval(CAST(%s AS regclass), %s, %s)",
                    (
                        str(sequence_name),
                        1 if maximum is None else int(maximum),
                        maximum is not None,
                    ),
                )
                parts = str(sequence_name).replace('"', "").split(".")
                if len(parts) != 2 or not all(_IDENTIFIER.fullmatch(part) for part in parts):
                    raise LegacyMigrationError("TARGET_SEQUENCE_NAME_INVALID", phase="verify")
                state = connection.execute(
                    f"SELECT last_value, is_called FROM {_qualified(parts[0], parts[1])}"
                ).fetchone()
                values = tuple(state.values()) if isinstance(state, Mapping) else tuple(state)
                last_value, is_called = int(values[0]), bool(values[1])
                expected_value = 1 if maximum is None else int(maximum)
                expected_called = maximum is not None
                if last_value != expected_value or is_called != expected_called:
                    raise LegacyMigrationError("TARGET_SEQUENCE_CALIBRATION_FAILED", phase="verify")
                calibrated += 1
        return calibrated
    except LegacyMigrationError:
        raise
    except Exception:
        raise LegacyMigrationError("TARGET_SEQUENCE_VALIDATION_FAILED", phase="verify") from None


def _verify_staged_subset(
    connection: Any,
    table: Mapping[str, Any],
    stage: str,
    *,
    source_report: Mapping[str, Any],
    batch_size: int,
    allow_target_extras: bool = False,
) -> dict[str, Any]:
    target = _qualified(TARGET_SCHEMA, str(table["name"]))
    first_pk = _quote(str(table["primary_key"][0]))
    query = (
        "SELECT "
        f"count(*) FILTER (WHERE target.{first_pk} IS NULL), "
        f"count(*) FILTER (WHERE target.{first_pk} IS NOT NULL AND "
        f"{_row_comparison(table, 'target', 'stage')}) "
        f"FROM {_quote(stage)} AS stage LEFT JOIN {target} AS target "
        f"ON {_pk_join(table, 'stage', 'target')}"
    )
    row = connection.execute(query).fetchone()
    values = tuple(row.values()) if isinstance(row, Mapping) else tuple(row)
    missing, mismatched = map(int, values)
    if missing or mismatched:
        raise LegacyMigrationError(
            "TARGET_ROW_VERIFICATION_FAILED",
            phase="verify",
            details={
                "table": str(table["name"]),
                "missing": missing,
                "mismatched": mismatched,
            },
        )
    target_count = int(_fetch_scalar(connection, f"SELECT count(*) FROM {target}"))
    source_count = int(source_report["sourceCount"])
    if (
        not allow_target_extras
        and str(table["name"]) not in BASELINE_TABLES
        and target_count != source_count
    ):
        raise LegacyMigrationError("TARGET_COUNT_VERIFICATION_FAILED", phase="verify")
    digest_count, pk_digest, row_digest = _digest_database_query(
        connection,
        table,
        from_clause=(
            f"{_quote(stage)} AS stage JOIN {target} AS target "
            f"ON {_pk_join(table, 'stage', 'target')}"
        ),
        alias="target",
        batch_size=batch_size,
    )
    if (
        digest_count != int(source_report["sourceCount"])
        or pk_digest != str(source_report["pkSha256"])
        or row_digest != str(source_report["rowSha256"])
    ):
        raise LegacyMigrationError("TARGET_DIGEST_VERIFICATION_FAILED", phase="verify")
    return {
        "targetCount": target_count,
        "verifiedSubsetCount": source_count,
        "targetExtraCount": target_count - source_count,
        "targetPkSha256": pk_digest,
        "targetRowSha256": row_digest,
    }


def verify_existing_postgres(
    connection: Any,
    snapshots: SnapshotBundle,
    manifest: Mapping[str, Any],
    source_reports: list[dict[str, Any]],
    *,
    run_id: UUID,
    batch_size: int,
    accept_post_cutover_changes: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Prove every legacy row exists while allowing post-cutover target rows.

    All source rows are transformed into transaction-local temporary staging.
    The target subset must match by primary key and canonical row digest.  No
    business table, sequence, or durable migration state is changed here.
    """

    reports = {str(report["table"]): dict(report) for report in source_reports}
    tables = {str(table["name"]): table for table in manifest["tables"]}
    stage_names: dict[str, str] = {}
    try:
        # PostgreSQL READ ONLY transactions reject INSERTs into temporary
        # staging tables.  This path contains no durable DML and always rolls
        # the SERIALIZABLE transaction back after subset verification.
        connection.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
        connection.execute("SET LOCAL lock_timeout='5s'")
        connection.execute("SET LOCAL statement_timeout='30min'")
        target_receipt = _validate_target_catalog(connection, manifest)

        for name in sorted(tables):
            stage, staged = _stage_table(
                connection,
                snapshots,
                tables[name],
                run_id=run_id,
                batch_size=batch_size,
            )
            stage_names[name] = stage
            if staged != int(reports[name]["sourceCount"]):
                raise LegacyMigrationError(
                    "STAGING_SOURCE_COUNT_MISMATCH", phase="staging"
                )
            reports[name]["stageCount"] = staged
            stage_count, stage_pk_digest, stage_row_digest = _digest_database_query(
                connection,
                tables[name],
                from_clause=f"{_quote(stage)} AS stage",
                alias="stage",
                batch_size=batch_size,
            )
            if (
                stage_count != int(reports[name]["sourceCount"])
                or stage_pk_digest != str(reports[name]["pkSha256"])
                or stage_row_digest != str(reports[name]["rowSha256"])
            ):
                raise LegacyMigrationError("STAGING_DIGEST_MISMATCH", phase="staging")
            reports[name]["stagePkSha256"] = stage_pk_digest
            reports[name]["stageRowSha256"] = stage_row_digest

        target_fk_checks = _validate_target_foreign_keys(connection, manifest)
        verified_primary_keys = 0
        exact_matched_rows = 0
        post_cutover_changed_rows = 0
        target_rows = 0
        blocking_drifts: list[dict[str, Any]] = []
        for name, table in tables.items():
            try:
                verification = _verify_staged_subset(
                    connection,
                    table,
                    stage_names[name],
                    source_report=reports[name],
                    batch_size=batch_size,
                    allow_target_extras=True,
                )
            except LegacyMigrationError as error:
                if error.code != "TARGET_ROW_VERIFICATION_FAILED":
                    raise
                drift = {
                    "table": name,
                    "missing": int(error.details.get("missing", 0)),
                    "mismatched": int(error.details.get("mismatched", 0)),
                }
                if drift["mismatched"]:
                    drift.update(
                        _staged_drift_summary(
                            connection,
                            table,
                            stage_names[name],
                        )
                    )
                target = _qualified(TARGET_SCHEMA, name)
                target_count = int(
                    _fetch_scalar(connection, f"SELECT count(*) FROM {target}")
                )
                source_count = int(reports[name]["sourceCount"])
                is_proven_post_cutover = (
                    drift["missing"] == 0
                    and drift["mismatched"] > 0
                    and drift.get("postCutoverNewer") == drift["mismatched"]
                )
                reports[name].update(
                    {
                        **drift,
                        "targetCount": target_count,
                        "targetExtraCount": target_count - source_count,
                        "verifiedPrimaryKeyCount": source_count - drift["missing"],
                        "exactMatchedCount": (
                            source_count - drift["missing"] - drift["mismatched"]
                        ),
                        "postCutoverChangedCount": (
                            drift["mismatched"] if is_proven_post_cutover else 0
                        ),
                        "inserted": 0,
                    }
                )
                target_rows += target_count
                if accept_post_cutover_changes and is_proven_post_cutover:
                    verified_primary_keys += source_count
                    exact_matched_rows += source_count - drift["mismatched"]
                    post_cutover_changed_rows += drift["mismatched"]
                    continue
                blocking_drifts.append(drift)
                continue
            reports[name].update(verification)
            reports[name]["inserted"] = 0
            source_count = int(verification["verifiedSubsetCount"])
            reports[name]["verifiedPrimaryKeyCount"] = source_count
            reports[name]["exactMatchedCount"] = source_count
            reports[name]["postCutoverChangedCount"] = 0
            verified_primary_keys += source_count
            exact_matched_rows += source_count
            target_rows += int(verification["targetCount"])

        if blocking_drifts:
            raise LegacyMigrationError(
                "TARGET_ROW_VERIFICATION_FAILED",
                phase="verify",
                details={
                    "drifts": blocking_drifts,
                    "missing": sum(item["missing"] for item in blocking_drifts),
                    "mismatched": sum(
                        item["mismatched"] for item in blocking_drifts
                    ),
                },
            )

        target_receipt.update(
            {
                "stagingTables": len(stage_names),
                "insertedRows": 0,
                "verifiedSourcePrimaryKeys": verified_primary_keys,
                "exactMatchedRows": exact_matched_rows,
                "postCutoverChangedRows": post_cutover_changed_rows,
                "targetExtraRows": target_rows - verified_primary_keys,
                "targetRows": target_rows,
                "foreignKeyChecks": target_fk_checks,
                "sequenceColumns": 0,
                "transaction": "rolled_back_temporary_staging_verification",
            }
        )
        connection.rollback()
        return target_receipt, [reports[name] for name in sorted(reports)]
    except LegacyMigrationError:
        try:
            connection.rollback()
        except Exception:
            pass
        raise
    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass
        raise LegacyMigrationError("TARGET_TRANSACTION_FAILED", phase="target") from None


def migrate_to_postgres(
    connection: Any,
    snapshots: SnapshotBundle,
    manifest: Mapping[str, Any],
    source_reports: list[dict[str, Any]],
    *,
    run_id: UUID,
    batch_size: int,
    commit: bool,
    approve_baseline_inserts: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Rehearse or commit all 48 tables in one serializable transaction."""

    reports = {str(report["table"]): dict(report) for report in source_reports}
    tables = {str(table["name"]): table for table in manifest["tables"]}
    stage_names: dict[str, str] = {}
    try:
        connection.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
        connection.execute("SET LOCAL lock_timeout='5s'")
        connection.execute("SET LOCAL statement_timeout='30min'")
        target_receipt = _validate_target_catalog(connection, manifest)

        for name in sorted(tables):
            stage, staged = _stage_table(
                connection,
                snapshots,
                tables[name],
                run_id=run_id,
                batch_size=batch_size,
            )
            stage_names[name] = stage
            if staged != int(reports[name]["sourceCount"]):
                raise LegacyMigrationError("STAGING_SOURCE_COUNT_MISMATCH", phase="staging")
            reports[name]["stageCount"] = staged
            stage_count, stage_pk_digest, stage_row_digest = _digest_database_query(
                connection,
                tables[name],
                from_clause=f"{_quote(stage)} AS stage",
                alias="stage",
                batch_size=batch_size,
            )
            if (
                stage_count != int(reports[name]["sourceCount"])
                or stage_pk_digest != str(reports[name]["pkSha256"])
                or stage_row_digest != str(reports[name]["rowSha256"])
            ):
                raise LegacyMigrationError("STAGING_DIGEST_MISMATCH", phase="staging")
            reports[name]["stagePkSha256"] = stage_pk_digest
            reports[name]["stageRowSha256"] = stage_row_digest

        _validate_target_conflicts(
            connection,
            tables,
            stage_names,
            reports,
            commit=commit,
            approve_baseline_inserts=approve_baseline_inserts,
        )

        inserted_total = 0
        for name in wave_topological_order(manifest):
            table = tables[name]
            inserted = _insert_from_stage(
                connection,
                table,
                stage_names[name],
                baseline=name in BASELINE_TABLES,
            )
            reports[name]["inserted"] = inserted
            inserted_total += inserted

        target_fk_checks = _validate_target_foreign_keys(connection, manifest)
        sequence_columns = _calibrate_sequences(connection, manifest)
        for name, table in tables.items():
            reports[name].update(
                _verify_staged_subset(
                    connection,
                    table,
                    stage_names[name],
                    source_report=reports[name],
                    batch_size=batch_size,
                )
            )

        target_receipt.update(
            {
                "stagingTables": len(stage_names),
                "insertedRows": inserted_total,
                "foreignKeyChecks": target_fk_checks,
                "sequenceColumns": sequence_columns,
                "transaction": "committed" if commit else "rolled_back_rehearsal",
            }
        )
        if commit:
            connection.commit()
        else:
            connection.rollback()
        return target_receipt, [reports[name] for name in sorted(reports)]
    except LegacyMigrationError:
        try:
            connection.rollback()
        except Exception:
            pass
        raise
    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass
        raise LegacyMigrationError("TARGET_TRANSACTION_FAILED", phase="target") from None


def _source_receipt(
    snapshots: SnapshotBundle,
    schema_digests: Mapping[str, str],
    reports: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    grouped: dict[str, list[Mapping[str, Any]]] = {"main": [], "notion": []}
    for report in reports:
        grouped[str(report["source"])].append(report)
    result: dict[str, Any] = {
        "snapshotMethod": "sqlite-online-backup-read-only",
        "coordination": "simultaneous-read-transactions-per-file-consistent-no-cross-file-atomicity",
    }
    for source in ("main", "notion"):
        snapshot = snapshots.for_source(source)
        result[source] = {
            "tables": len(grouped[source]),
            "rows": sum(int(report["sourceCount"]) for report in grouped[source]),
            "snapshotSha256": snapshot.sha256,
            "schemaSha256": schema_digests[source],
            "snapshotBytes": snapshot.size_bytes,
            "sourceBytes": snapshot.source_size_bytes,
            "sourceMtimeNs": snapshot.source_mtime_ns,
        }
    return result


def run_legacy_migration(
    *,
    main_path: Path,
    notion_path: Path,
    mode: str = "source-dry-run",
    expected_main_filename: str = DEFAULT_MAIN_FILENAME,
    expected_notion_filename: str = DEFAULT_NOTION_FILENAME,
    expected_target_database: str | None = None,
    approve_baseline_inserts: bool = False,
    expected_target_host: str | None = None,
    expected_target_port: int | None = None,
    expected_target_owner: str | None = None,
    production_approval: str | None = None,
    accept_post_cutover_changes: bool = False,
    batch_size: int = 1_000,
    run_id: UUID | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Run source validation, target rehearsal, or explicit isolated import."""

    supported_modes = {
        "source-dry-run",
        "target-dry-run",
        "execute",
        "verify-existing",
        "production-execute",
    }
    commit_modes = {"execute", "production-execute"}
    target_modes = {"target-dry-run", "verify-existing", *commit_modes}
    direct_database_modes = {"verify-existing", "production-execute"}
    if mode not in supported_modes:
        raise LegacyMigrationError("MODE_INVALID", phase="configuration")
    if mode not in commit_modes and approve_baseline_inserts:
        raise LegacyMigrationError("BASELINE_APPROVAL_MODE_INVALID", phase="configuration")
    if accept_post_cutover_changes and mode != "verify-existing":
        raise LegacyMigrationError(
            "POST_CUTOVER_APPROVAL_MODE_INVALID", phase="configuration"
        )
    if mode in target_modes and not expected_target_database:
        raise LegacyMigrationError("EXPECTED_TARGET_DATABASE_REQUIRED", phase="configuration")
    if mode in direct_database_modes:
        approval_action = (
            "MIGRATE-43+5-TO"
            if mode == "production-execute"
            else "VERIFY-43+5-IN"
        )
        expected_approval = f"{approval_action}:{expected_target_database}"
        if production_approval != expected_approval:
            raise LegacyMigrationError(
                (
                    "PRODUCTION_TARGET_APPROVAL_REQUIRED"
                    if mode == "production-execute"
                    else "TARGET_VERIFY_APPROVAL_REQUIRED"
                ),
                phase="configuration",
            )
        if (
            not expected_target_host
            or expected_target_port is None
            or expected_target_port < 1
            or expected_target_port > 65535
            or not expected_target_owner
        ):
            raise LegacyMigrationError(
                (
                    "PRODUCTION_TARGET_IDENTITY_REQUIRED"
                    if mode == "production-execute"
                    else "TARGET_VERIFY_IDENTITY_REQUIRED"
                ),
                phase="configuration",
            )
    migration_run_id = run_id or uuid4()
    if not isinstance(migration_run_id, UUID):
        raise LegacyMigrationError("RUN_ID_INVALID", phase="configuration")
    manifest = load_manifest()
    wave_topological_order(manifest)

    with readonly_snapshot_bundle(
        main_path,
        notion_path,
        expected_main_filename=expected_main_filename,
        expected_notion_filename=expected_notion_filename,
    ) as snapshots:
        reports, schema_digests, source_fk_checks = scan_sources(
            snapshots, manifest, batch_size=batch_size
        )
        target_receipt: dict[str, Any] = {
            "validated": False,
            "transaction": "not_started",
        }
        if mode in target_modes:
            from persistence.config import (
                DATABASE_URL_ENV,
                parse_postgres_target,
                require_test_database_url,
            )

            values = os.environ if environ is None else environ
            if mode in direct_database_modes:
                try:
                    target = parse_postgres_target(values.get(DATABASE_URL_ENV, ""))
                except Exception:
                    raise LegacyMigrationError(
                        (
                            "PRODUCTION_TARGET_SAFETY_CHECK_FAILED"
                            if mode == "production-execute"
                            else "TARGET_VERIFY_SAFETY_CHECK_FAILED"
                        ),
                        phase="configuration",
                    ) from None
                if (
                    target.database_name != expected_target_database
                    or (target.host or "").casefold()
                    != str(expected_target_host).casefold()
                    or target.port != expected_target_port
                ):
                    raise LegacyMigrationError(
                        (
                            "PRODUCTION_TARGET_SAFETY_CHECK_FAILED"
                            if mode == "production-execute"
                            else "TARGET_VERIFY_SAFETY_CHECK_FAILED"
                        ),
                        phase="configuration",
                    )
                dsn = target.dsn
            else:
                try:
                    dsn = require_test_database_url(
                        expected_target_database,
                        environ=values,
                    )
                except Exception:
                    raise LegacyMigrationError(
                        "TARGET_SAFETY_CHECK_FAILED", phase="configuration"
                    ) from None
            try:
                import psycopg

                connection = psycopg.connect(
                    dsn,
                    autocommit=False,
                    application_name="ink-dream-legacy-pg-import",
                )
            except Exception:
                raise LegacyMigrationError("TARGET_CONNECTION_FAILED", phase="target") from None
            try:
                if mode in direct_database_modes:
                    identity = connection.execute(
                        "SELECT current_database(), current_user, "
                        "pg_catalog.pg_get_userbyid(datdba) "
                        "FROM pg_catalog.pg_database WHERE datname=current_database()"
                    ).fetchone()
                    identity_values = (
                        tuple(identity.values())
                        if isinstance(identity, Mapping)
                        else tuple(identity or ())
                    )
                    if identity_values != (
                        expected_target_database,
                        expected_target_owner,
                        expected_target_owner,
                    ):
                        raise LegacyMigrationError(
                            (
                                "PRODUCTION_TARGET_IDENTITY_MISMATCH"
                                if mode == "production-execute"
                                else "TARGET_VERIFY_IDENTITY_MISMATCH"
                            ),
                            phase="configuration",
                        )
                    # The read-only identity query starts psycopg's implicit
                    # transaction. End it before migrate_to_postgres opens its
                    # required SERIALIZABLE transaction.
                    connection.rollback()
                if mode == "verify-existing":
                    target_receipt, reports = verify_existing_postgres(
                        connection,
                        snapshots,
                        manifest,
                        reports,
                        run_id=migration_run_id,
                        batch_size=batch_size,
                        accept_post_cutover_changes=accept_post_cutover_changes,
                    )
                else:
                    target_receipt, reports = migrate_to_postgres(
                        connection,
                        snapshots,
                        manifest,
                        reports,
                        run_id=migration_run_id,
                        batch_size=batch_size,
                        commit=mode in commit_modes,
                        approve_baseline_inserts=approve_baseline_inserts,
                    )
                target_receipt["validated"] = True
            finally:
                connection.close()

        return {
            "contract": CONTRACT,
            "receiptVersion": 1,
            "runId": str(migration_run_id),
            "mode": mode,
            "status": (
                "committed"
                if mode in commit_modes
                else "adopted_with_post_cutover_changes"
                if mode == "verify-existing"
                and accept_post_cutover_changes
                and int(target_receipt.get("postCutoverChangedRows", 0)) > 0
                else "adopted_exact"
                if mode == "verify-existing" and accept_post_cutover_changes
                else "verified_existing"
                if mode == "verify-existing"
                else "validated"
            ),
            "manifestSha256": str(manifest["catalog_sha256"]),
            "source": _source_receipt(
                snapshots, schema_digests, reports
            ),
            "phases": {
                "snapshot": "passed",
                "manifest": "passed",
                "transform": "passed",
                "conflict": (
                    "not_applicable"
                    if mode == "verify-existing"
                    else "passed"
                    if mode != "source-dry-run"
                    else "not_run"
                ),
                "staging": "passed" if mode != "source-dry-run" else "not_run",
                "import": (
                    "committed"
                    if mode in commit_modes
                    else "rolled_back"
                    if mode == "target-dry-run"
                    else "not_run"
                ),
                "verify": "passed" if mode != "source-dry-run" else "source_only",
            },
            "validation": {
                "tables": len(reports),
                "sourceRows": sum(int(report["sourceCount"]) for report in reports),
                "sourceForeignKeyChecks": source_fk_checks,
                "targetComplete": mode != "source-dry-run",
            },
            "target": target_receipt,
            "tables": reports,
            "security": {
                "containsBusinessValues": False,
                "containsSourcePaths": False,
                "containsDsn": False,
                "implicitOverwrite": False,
                "destructiveTargetCleanup": False,
            },
        }


__all__ = [
    "CONTRACT",
    "DEFAULT_MAIN_FILENAME",
    "DEFAULT_NOTION_FILENAME",
    "EXPECTED_ALEMBIC_HEAD",
    "LegacyMigrationError",
    "SnapshotBundle",
    "SnapshotFile",
    "migrate_to_postgres",
    "readonly_snapshot_bundle",
    "run_legacy_migration",
    "scan_sources",
    "transform_row",
    "transform_value",
    "verify_existing_postgres",
    "wave_topological_order",
]
