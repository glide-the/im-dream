#!/usr/bin/env python3
"""Verify static schema artifacts and optionally a read-only isolated PG catalog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from persistence.catalog import catalog_snapshot
from persistence.config import require_test_database_url
from schema.catalog import (
    EXPECTED_POSTGRES_COUNTS,
    MANIFEST_PATH,
    POSTGRES_SCHEMA_PATH,
    REVOCATION_TEST_ONLY_TABLES,
    build_legacy_manifest,
    load_manifest,
    render_manifest,
)
from schema.postgres import BASELINE_INDEX_DDL, render_postgres_schema


# The Admin-owned canonical-user projection trigger is intentionally retained
# when Dream adopts the three shared baseline tables.  It is not one of the 25
# Dream legacy triggers, so count it as an approved shared-schema extension
# while still rejecting every unrecognised trigger on the 48 Dream tables.
APPROVED_BASELINE_EXTERNAL_TRIGGERS = {
    ("users", "users_sync_billing_identity"),
}


def verify_static_artifacts() -> dict[str, Any]:
    manifest = load_manifest()
    recomputed = render_manifest(build_legacy_manifest())
    if MANIFEST_PATH.read_text(encoding="utf-8") != recomputed:
        raise RuntimeError("checked-in legacy schema manifest is stale")
    ddl = POSTGRES_SCHEMA_PATH.read_text(encoding="utf-8")
    if ddl != render_postgres_schema(manifest):
        raise RuntimeError("checked-in PostgreSQL DDL is stale")
    if re.search(r"\bIF\s+NOT\s+EXISTS\b", ddl, flags=re.IGNORECASE):
        raise RuntimeError("PostgreSQL DDL masks a name collision")
    if re.search(r"\b(?:DROP\s+TABLE|TRUNCATE|DELETE\s+FROM)\b", ddl, flags=re.IGNORECASE):
        raise RuntimeError("PostgreSQL DDL contains a destructive data operation")
    counts = {
        "tables": len(re.findall(r"^CREATE TABLE ", ddl, flags=re.MULTILINE)),
        "explicit_indexes": len(
            re.findall(r"^CREATE (?:UNIQUE )?INDEX ", ddl, flags=re.MULTILINE)
        ),
        "triggers": len(re.findall(r"^CREATE TRIGGER ", ddl, flags=re.MULTILINE)),
    }
    if counts != {
        "tables": EXPECTED_POSTGRES_COUNTS["tables"],
        "explicit_indexes": EXPECTED_POSTGRES_COUNTS["explicit_indexes"],
        "triggers": EXPECTED_POSTGRES_COUNTS["triggers"],
    }:
        raise RuntimeError(f"rendered PostgreSQL object count drift: {counts!r}")
    if any(name in ddl for name in REVOCATION_TEST_ONLY_TABLES):
        raise RuntimeError("test-only revocation table leaked into PostgreSQL DDL")
    if len(BASELINE_INDEX_DDL) != 10:
        raise RuntimeError("approved Admin-head baseline index profile drift")
    return {
        "source": manifest["counts"],
        "target": manifest["postgres_target_counts"],
        "manifestSha256": manifest["catalog_sha256"],
    }


def _expected_index_names(manifest: dict[str, Any]) -> set[str]:
    baseline_tables = set(manifest["baseline_adopt"]["tables"])
    names = {
        str(index["name"])
        for table in manifest["tables"]
        if table["name"] not in baseline_tables
        for index in table["explicit_indexes"]
    }
    for statement in BASELINE_INDEX_DDL:
        match = re.match(r"CREATE (?:UNIQUE )?INDEX ([A-Za-z0-9_]+)", statement)
        if not match:
            raise RuntimeError("invalid static baseline index DDL")
        names.add(match.group(1))
    return names


def verify_isolated_catalog() -> dict[str, Any]:
    """Connect only to an explicitly isolated TEST_DATABASE_URL, read-only."""

    dsn = require_test_database_url()
    import psycopg

    manifest = load_manifest()
    expected_names = {str(table["name"]) for table in manifest["tables"]}
    with psycopg.connect(dsn) as connection:
        connection.execute("SET TRANSACTION READ ONLY")
        snapshot = catalog_snapshot(connection)
    dream_tables = {
        str(table["table"]): table
        for table in snapshot.payload["tables"]
        if str(table["table"]) in expected_names
    }
    if set(dream_tables) != expected_names:
        raise RuntimeError("isolated PostgreSQL catalog is missing Dream tables")
    expected_triggers = {
        (str(trigger["table"]), str(trigger["name"]))
        for trigger in manifest["triggers"]
    }
    actual_triggers = {
        (table_name, str(trigger["name"]))
        for table_name, table in dream_tables.items()
        for trigger in table["triggers"]
    }
    if expected_triggers - actual_triggers:
        raise RuntimeError("isolated PostgreSQL trigger inventory is incomplete")
    unrecognised_triggers = actual_triggers - expected_triggers
    if not unrecognised_triggers.issubset(APPROVED_BASELINE_EXTERNAL_TRIGGERS):
        raise RuntimeError("isolated PostgreSQL trigger inventory has unknown extensions")
    counts = {
        "tables": len(dream_tables),
        "columns": sum(len(table["columns"]) for table in dream_tables.values()),
        "explicit_indexes": sum(len(table["indexes"]) for table in dream_tables.values()),
        "triggers": len(expected_triggers),
    }
    if counts != EXPECTED_POSTGRES_COUNTS:
        raise RuntimeError(f"isolated PostgreSQL target count mismatch: {counts!r}")
    actual_indexes = {
        str(index["name"])
        for table in dream_tables.values()
        for index in table["indexes"]
    }
    if actual_indexes != _expected_index_names(manifest):
        raise RuntimeError("isolated PostgreSQL explicit index inventory mismatch")
    return {"target": counts, "catalogSha256": snapshot.sha256}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        action="store_true",
        help="also inspect an explicitly isolated TEST_DATABASE_URL in read-only mode",
    )
    arguments = parser.parse_args(argv)
    receipt: dict[str, Any] = {"static": verify_static_artifacts()}
    if arguments.database:
        receipt["database"] = verify_isolated_catalog()
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
