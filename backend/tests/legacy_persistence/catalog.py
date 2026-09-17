"""Deterministic PostgreSQL application-catalog fingerprinting.

Admin migration bookkeeping lives outside the application schema. The snapshot
captures the structural facts needed by the Dream 43-core + 5-Notion data gate,
then hashes canonical JSON rather than PostgreSQL display text.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from typing import Any, Final

from .errors import CatalogMismatchError, map_postgres_error


CATALOG_FORMAT_VERSION: Final = "ink-dream-postgres-catalog-v1"
EXPECTED_CORE_TABLE_COUNT: Final = 43
EXPECTED_NOTION_TABLE_COUNT: Final = 5
EXPECTED_APPLICATION_TABLE_COUNT: Final = 48
# The immutable SQLite inventory and the Admin current-head exact-adopt target
# intentionally differ.  Admin head retains two deprecated status columns and
# replaces/adds the complete canonical baseline index set.  Its
# ``workspace.settings`` JSONB conversion changes type, not column count.
SOURCE_COLUMN_COUNT: Final = 567
TARGET_COLUMN_COUNT: Final = 569
SOURCE_EXPLICIT_INDEX_COUNT: Final = 78
TARGET_EXPLICIT_INDEX_COUNT: Final = 82

# ``EXPECTED_*`` names are the public readiness API.  Unqualified compatibility
# names always describe the PostgreSQL target, never the legacy source.
EXPECTED_SOURCE_APPLICATION_COLUMN_COUNT: Final = SOURCE_COLUMN_COUNT
EXPECTED_TARGET_APPLICATION_COLUMN_COUNT: Final = TARGET_COLUMN_COUNT
EXPECTED_APPLICATION_COLUMN_COUNT: Final = EXPECTED_TARGET_APPLICATION_COLUMN_COUNT
EXPECTED_SOURCE_EXPLICIT_INDEX_COUNT: Final = SOURCE_EXPLICIT_INDEX_COUNT
EXPECTED_TARGET_EXPLICIT_INDEX_COUNT: Final = TARGET_EXPLICIT_INDEX_COUNT
EXPECTED_EXPLICIT_INDEX_COUNT: Final = EXPECTED_TARGET_EXPLICIT_INDEX_COUNT
EXPECTED_CORE_TRIGGER_COUNT: Final = 25


CATALOG_TABLES_SQL: Final = """
/* ink_catalog:tables */
SELECT
  n.nspname AS schema_name,
  c.relname AS table_name
FROM pg_catalog.pg_class AS c
JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = %s
  AND c.relkind IN ('r', 'p')
ORDER BY n.nspname, c.relname
"""

CATALOG_COLUMNS_SQL: Final = """
/* ink_catalog:columns */
SELECT
  n.nspname AS schema_name,
  c.relname AS table_name,
  a.attnum AS ordinal_position,
  a.attname AS column_name,
  pg_catalog.format_type(a.atttypid, a.atttypmod) AS pg_type,
  NOT a.attnotnull AS is_nullable,
  CASE a.attidentity
    WHEN 'a' THEN 'always'
    WHEN 'd' THEN 'by_default'
    ELSE NULL
  END AS identity_kind,
  pg_catalog.pg_get_expr(ad.adbin, ad.adrelid, true) AS default_expression,
  CASE
    WHEN a.attcollation = 0 THEN NULL
    ELSE quote_ident(cn.nspname) || '.' || quote_ident(co.collname)
  END AS collation_name
FROM pg_catalog.pg_attribute AS a
JOIN pg_catalog.pg_class AS c ON c.oid = a.attrelid
JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
LEFT JOIN pg_catalog.pg_attrdef AS ad
  ON ad.adrelid = a.attrelid AND ad.adnum = a.attnum
LEFT JOIN pg_catalog.pg_collation AS co ON co.oid = a.attcollation
LEFT JOIN pg_catalog.pg_namespace AS cn ON cn.oid = co.collnamespace
WHERE n.nspname = %s
  AND c.relkind IN ('r', 'p')
  AND a.attnum > 0
  AND NOT a.attisdropped
ORDER BY n.nspname, c.relname, a.attnum
"""

CATALOG_CONSTRAINTS_SQL: Final = """
/* ink_catalog:constraints */
SELECT
  n.nspname AS schema_name,
  c.relname AS table_name,
  con.conname AS constraint_name,
  con.contype AS constraint_type,
  ARRAY(
    SELECT att.attname
    FROM unnest(con.conkey) WITH ORDINALITY AS key(attnum, position)
    JOIN pg_catalog.pg_attribute AS att
      ON att.attrelid = con.conrelid AND att.attnum = key.attnum
    ORDER BY key.position
  ) AS columns,
  rn.nspname AS referenced_schema,
  rc.relname AS referenced_table,
  ARRAY(
    SELECT att.attname
    FROM unnest(con.confkey) WITH ORDINALITY AS key(attnum, position)
    JOIN pg_catalog.pg_attribute AS att
      ON att.attrelid = con.confrelid AND att.attnum = key.attnum
    ORDER BY key.position
  ) AS referenced_columns,
  pg_catalog.pg_get_constraintdef(con.oid, true) AS definition
FROM pg_catalog.pg_constraint AS con
JOIN pg_catalog.pg_class AS c ON c.oid = con.conrelid
JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
LEFT JOIN pg_catalog.pg_class AS rc ON rc.oid = con.confrelid
LEFT JOIN pg_catalog.pg_namespace AS rn ON rn.oid = rc.relnamespace
WHERE n.nspname = %s
  AND c.relkind IN ('r', 'p')
  AND con.contype IN ('p', 'u', 'c', 'f')
ORDER BY n.nspname, c.relname, con.contype, con.conname
"""

CATALOG_INDEXES_SQL: Final = """
/* ink_catalog:indexes */
SELECT
  n.nspname AS schema_name,
  c.relname AS table_name,
  ic.relname AS index_name,
  am.amname AS access_method,
  i.indisunique AS is_unique,
  i.indisvalid AS is_valid,
  key.position AS key_position,
  key.position > i.indnkeyatts AS is_included,
  pg_catalog.pg_get_indexdef(i.indexrelid, key.position, true) AS key_expression,
  CASE
    WHEN key.position > i.indnkeyatts THEN NULL
    WHEN (i.indoption[key.position - 1] & 1) = 1 THEN 'desc'
    ELSE 'asc'
  END AS sort_order,
  CASE
    WHEN key.position > i.indnkeyatts THEN NULL
    WHEN (i.indoption[key.position - 1] & 2) = 2 THEN 'first'
    ELSE 'last'
  END AS nulls_order,
  pg_catalog.pg_get_expr(i.indpred, i.indrelid, true) AS predicate
FROM pg_catalog.pg_index AS i
JOIN pg_catalog.pg_class AS c ON c.oid = i.indrelid
JOIN pg_catalog.pg_class AS ic ON ic.oid = i.indexrelid
JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
JOIN pg_catalog.pg_am AS am ON am.oid = ic.relam
CROSS JOIN LATERAL generate_series(1, i.indnatts) AS key(position)
LEFT JOIN pg_catalog.pg_constraint AS con ON con.conindid = i.indexrelid
WHERE n.nspname = %s
  AND c.relkind IN ('r', 'p')
  AND con.oid IS NULL
ORDER BY n.nspname, c.relname, ic.relname, key.position
"""

CATALOG_TRIGGERS_SQL: Final = """
/* ink_catalog:triggers */
SELECT
  n.nspname AS schema_name,
  c.relname AS table_name,
  t.tgname AS trigger_name,
  CASE
    WHEN (t.tgtype & 2) = 2 THEN 'before'
    WHEN (t.tgtype & 64) = 64 THEN 'instead_of'
    ELSE 'after'
  END AS timing,
  CASE WHEN (t.tgtype & 1) = 1 THEN 'row' ELSE 'statement' END AS trigger_level,
  ARRAY_REMOVE(ARRAY[
    CASE WHEN (t.tgtype & 4) = 4 THEN 'insert' END,
    CASE WHEN (t.tgtype & 8) = 8 THEN 'delete' END,
    CASE WHEN (t.tgtype & 16) = 16 THEN 'update' END,
    CASE WHEN (t.tgtype & 32) = 32 THEN 'truncate' END
  ], NULL) AS events,
  pg_catalog.pg_get_functiondef(p.oid) AS function_definition
FROM pg_catalog.pg_trigger AS t
JOIN pg_catalog.pg_class AS c ON c.oid = t.tgrelid
JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
JOIN pg_catalog.pg_proc AS p ON p.oid = t.tgfoid
WHERE n.nspname = %s
  AND c.relkind IN ('r', 'p')
  AND NOT t.tgisinternal
ORDER BY n.nspname, c.relname, t.tgname
"""


@dataclass(frozen=True)
class CatalogCounts:
    tables: int
    columns: int
    explicit_indexes: int
    triggers: int


@dataclass(frozen=True)
class CatalogExpectations:
    tables: int | None = None
    columns: int | None = None
    explicit_indexes: int | None = None
    triggers: int | None = None

    @classmethod
    def dream_43_plus_5(cls) -> "CatalogExpectations":
        """Return the Admin current-head PostgreSQL target profile."""

        return cls(
            tables=EXPECTED_APPLICATION_TABLE_COUNT,
            columns=EXPECTED_APPLICATION_COLUMN_COUNT,
            explicit_indexes=EXPECTED_EXPLICIT_INDEX_COUNT,
            triggers=EXPECTED_CORE_TRIGGER_COUNT,
        )

    def matches(self, actual: CatalogCounts) -> bool:
        return all(
            expected is None or expected == value
            for expected, value in (
                (self.tables, actual.tables),
                (self.columns, actual.columns),
                (self.explicit_indexes, actual.explicit_indexes),
                (self.triggers, actual.triggers),
            )
        )


@dataclass(frozen=True)
class CatalogSnapshot:
    schema: str
    fingerprint: str
    counts: CatalogCounts
    payload: Mapping[str, Any]

    @property
    def sha256(self) -> str:
        return self.fingerprint

    def canonical_json(self) -> str:
        return canonical_catalog_json(self.payload)


def _fetchall(connection: Any, sql: str, parameters: tuple[Any, ...]) -> list[Any]:
    result = connection.execute(sql, parameters)
    if hasattr(result, "fetchall"):
        return list(result.fetchall())
    if isinstance(result, Iterable) and not isinstance(result, (str, bytes, Mapping)):
        return list(result)
    raise CatalogMismatchError()


def _record(row: Any, fields: Sequence[str]) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return {field: row.get(field) for field in fields}
    if isinstance(row, Sequence) and not isinstance(row, (str, bytes)):
        if len(row) != len(fields):
            raise CatalogMismatchError()
        return dict(zip(fields, row))
    raise CatalogMismatchError()


def _string_array(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    # Psycopg decodes PostgreSQL arrays.  This modest fallback keeps pure fakes
    # convenient without trying to implement PostgreSQL's full array grammar.
    if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
        body = value[1:-1]
        return [] if not body else [item.strip('"') for item in body.split(",")]
    raise CatalogMismatchError()


def _expected_table_names(
    expected_names: Iterable[str] | None,
    *,
    schema: str,
) -> frozenset[str] | None:
    if expected_names is None:
        return None
    normalized: set[str] = set()
    for value in expected_names:
        if not isinstance(value, str) or not value:
            raise CatalogMismatchError()
        if "." in value:
            qualified_schema, table_name = value.split(".", 1)
            if qualified_schema != schema or not table_name:
                raise CatalogMismatchError()
        else:
            table_name = value
        if table_name in normalized:
            raise CatalogMismatchError()
        normalized.add(table_name)
    return frozenset(normalized)


def canonical_catalog_json(payload: Mapping[str, Any]) -> str:
    """Serialize a catalog payload with stable keys, ordering, and whitespace."""

    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def catalog_fingerprint_from_payload(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_catalog_json(payload).encode("utf-8")).hexdigest()


def catalog_snapshot(
    connection: Any,
    schema: str = "public",
    expected_names: Iterable[str] | None = None,
) -> CatalogSnapshot:
    """Read, canonicalize, and fingerprint one PostgreSQL application schema."""

    if not isinstance(schema, str) or not schema or "\x00" in schema:
        raise CatalogMismatchError()
    expected = _expected_table_names(expected_names, schema=schema)

    try:
        table_rows = _fetchall(connection, CATALOG_TABLES_SQL, (schema,))
        column_rows = _fetchall(connection, CATALOG_COLUMNS_SQL, (schema,))
        constraint_rows = _fetchall(connection, CATALOG_CONSTRAINTS_SQL, (schema,))
        index_rows = _fetchall(connection, CATALOG_INDEXES_SQL, (schema,))
        trigger_rows = _fetchall(connection, CATALOG_TRIGGERS_SQL, (schema,))
    except CatalogMismatchError:
        raise
    except BaseException as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        raise map_postgres_error(exc) from None

    tables: dict[tuple[str, str], dict[str, Any]] = {}
    table_fields = ("schema_name", "table_name")
    for raw_row in table_rows:
        row = _record(raw_row, table_fields)
        key = (str(row["schema_name"]), str(row["table_name"]))
        if key[0] != schema or key in tables:
            raise CatalogMismatchError()
        tables[key] = {
            "schema": key[0],
            "table": key[1],
            "columns": [],
            "constraints": {
                "primary_key": [],
                "unique": [],
                "check": [],
                "foreign_key": [],
            },
            "indexes": [],
            "triggers": [],
        }

    discovered_names = frozenset(table_name for _, table_name in tables)
    if expected is not None and discovered_names != expected:
        raise CatalogMismatchError()

    column_fields = (
        "schema_name",
        "table_name",
        "ordinal_position",
        "column_name",
        "pg_type",
        "is_nullable",
        "identity_kind",
        "default_expression",
        "collation_name",
    )
    for raw_row in column_rows:
        row = _record(raw_row, column_fields)
        key = (str(row["schema_name"]), str(row["table_name"]))
        if key not in tables:
            raise CatalogMismatchError()
        tables[key]["columns"].append(
            {
                "ordinal": int(row["ordinal_position"]),
                "name": str(row["column_name"]),
                "pg_type": str(row["pg_type"]),
                "nullable": bool(row["is_nullable"]),
                "identity": row["identity_kind"] or None,
                "default": row["default_expression"],
                "collation": row["collation_name"],
            }
        )

    constraint_fields = (
        "schema_name",
        "table_name",
        "constraint_name",
        "constraint_type",
        "columns",
        "referenced_schema",
        "referenced_table",
        "referenced_columns",
        "definition",
    )
    constraint_kinds = {"p": "primary_key", "u": "unique", "c": "check", "f": "foreign_key"}
    for raw_row in constraint_rows:
        row = _record(raw_row, constraint_fields)
        key = (str(row["schema_name"]), str(row["table_name"]))
        kind = constraint_kinds.get(str(row["constraint_type"]))
        if key not in tables or kind is None:
            raise CatalogMismatchError()
        item: dict[str, Any] = {
            "name": str(row["constraint_name"]),
            "columns": _string_array(row["columns"]),
            "definition": str(row["definition"]),
        }
        if kind == "foreign_key":
            item["references"] = {
                "schema": str(row["referenced_schema"]),
                "table": str(row["referenced_table"]),
                "columns": _string_array(row["referenced_columns"]),
            }
        tables[key]["constraints"][kind].append(item)

    index_fields = (
        "schema_name",
        "table_name",
        "index_name",
        "access_method",
        "is_unique",
        "is_valid",
        "key_position",
        "is_included",
        "key_expression",
        "sort_order",
        "nulls_order",
        "predicate",
    )
    indexes: dict[tuple[str, str, str], dict[str, Any]] = {}
    for raw_row in index_rows:
        row = _record(raw_row, index_fields)
        table_key = (str(row["schema_name"]), str(row["table_name"]))
        if table_key not in tables:
            raise CatalogMismatchError()
        index_key = (*table_key, str(row["index_name"]))
        item = indexes.setdefault(
            index_key,
            {
                "name": index_key[2],
                "method": str(row["access_method"]),
                "unique": bool(row["is_unique"]),
                "valid": bool(row["is_valid"]),
                "predicate": row["predicate"],
                "keys": [],
            },
        )
        if (
            item["method"] != str(row["access_method"])
            or item["unique"] != bool(row["is_unique"])
            or item["valid"] != bool(row["is_valid"])
            or item["predicate"] != row["predicate"]
        ):
            raise CatalogMismatchError()
        item["keys"].append(
            {
                "position": int(row["key_position"]),
                "expression": str(row["key_expression"]),
                "included": bool(row["is_included"]),
                "order": row["sort_order"],
                "nulls": row["nulls_order"],
            }
        )
    for (schema_name, table_name, _), item in indexes.items():
        item["keys"].sort(key=lambda key: key["position"])
        tables[(schema_name, table_name)]["indexes"].append(item)

    trigger_fields = (
        "schema_name",
        "table_name",
        "trigger_name",
        "timing",
        "trigger_level",
        "events",
        "function_definition",
    )
    for raw_row in trigger_rows:
        row = _record(raw_row, trigger_fields)
        key = (str(row["schema_name"]), str(row["table_name"]))
        if key not in tables:
            raise CatalogMismatchError()
        function_definition = str(row["function_definition"])
        tables[key]["triggers"].append(
            {
                "name": str(row["trigger_name"]),
                "timing": str(row["timing"]),
                "level": str(row["trigger_level"]),
                "events": sorted(_string_array(row["events"])),
                "function_def_hash": hashlib.sha256(
                    function_definition.encode("utf-8")
                ).hexdigest(),
            }
        )

    canonical_tables = []
    for table in tables.values():
        table["columns"].sort(key=lambda column: (column["ordinal"], column["name"]))
        for constraints in table["constraints"].values():
            constraints.sort(key=lambda constraint: constraint["name"])
        table["indexes"].sort(key=lambda index: index["name"])
        table["triggers"].sort(key=lambda trigger: trigger["name"])
        canonical_tables.append(table)
    canonical_tables.sort(key=lambda table: (table["schema"], table["table"]))

    payload: dict[str, Any] = {
        "format": CATALOG_FORMAT_VERSION,
        "schema": schema,
        "tables": canonical_tables,
    }
    counts = CatalogCounts(
        tables=len(canonical_tables),
        columns=sum(len(table["columns"]) for table in canonical_tables),
        explicit_indexes=sum(len(table["indexes"]) for table in canonical_tables),
        triggers=sum(len(table["triggers"]) for table in canonical_tables),
    )
    return CatalogSnapshot(
        schema=schema,
        fingerprint=catalog_fingerprint_from_payload(payload),
        counts=counts,
        payload=payload,
    )


def catalog_fingerprint(
    connection: Any,
    schema: str = "public",
    expected_names: Iterable[str] | None = None,
) -> str:
    """Compatibility helper returning only the SHA-256 hex digest."""

    return catalog_snapshot(connection, schema, expected_names).fingerprint


__all__ = [
    "CATALOG_COLUMNS_SQL",
    "CATALOG_CONSTRAINTS_SQL",
    "CATALOG_FORMAT_VERSION",
    "CATALOG_INDEXES_SQL",
    "CATALOG_TABLES_SQL",
    "CATALOG_TRIGGERS_SQL",
    "CatalogCounts",
    "CatalogExpectations",
    "CatalogSnapshot",
    "EXPECTED_APPLICATION_COLUMN_COUNT",
    "EXPECTED_APPLICATION_TABLE_COUNT",
    "EXPECTED_CORE_TABLE_COUNT",
    "EXPECTED_CORE_TRIGGER_COUNT",
    "EXPECTED_EXPLICIT_INDEX_COUNT",
    "EXPECTED_NOTION_TABLE_COUNT",
    "EXPECTED_SOURCE_APPLICATION_COLUMN_COUNT",
    "EXPECTED_SOURCE_EXPLICIT_INDEX_COUNT",
    "EXPECTED_TARGET_APPLICATION_COLUMN_COUNT",
    "EXPECTED_TARGET_EXPLICIT_INDEX_COUNT",
    "SOURCE_COLUMN_COUNT",
    "SOURCE_EXPLICIT_INDEX_COUNT",
    "TARGET_COLUMN_COUNT",
    "TARGET_EXPLICIT_INDEX_COUNT",
    "canonical_catalog_json",
    "catalog_fingerprint",
    "catalog_fingerprint_from_payload",
    "catalog_snapshot",
]
