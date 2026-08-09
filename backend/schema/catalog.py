"""Reproducible, data-free catalog of Dream's 43 + 5 legacy tables.

Only schema metadata is inspected.  No legacy row, credential, token, story,
or chat payload is read or emitted by this module.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import base64
from contextlib import redirect_stdout
import gzip
import hashlib
import importlib
import io
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any, Callable, Iterable


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
MANIFEST_PATH = Path(__file__).with_name("legacy_schema_manifest.json.gz.b64")
POSTGRES_SCHEMA_PATH = Path(__file__).with_name("postgres_schema.sql")

EXPECTED_COUNTS = {
    "main": {"tables": 43, "columns": 522, "explicit_indexes": 73, "triggers": 25},
    "notion": {"tables": 5, "columns": 45, "explicit_indexes": 5, "triggers": 0},
    "combined": {"tables": 48, "columns": 567, "explicit_indexes": 78, "triggers": 25},
}

EXPECTED_POSTGRES_COUNTS = {
    "tables": 48,
    "columns": 569,
    "explicit_indexes": 81,
    "triggers": 25,
}

BASELINE_TABLES = (
    "users",
    "story_workspace_workspaces",
    "story_workspace_stories",
)

REVOCATION_TEST_ONLY_TABLES = (
    "revocation_audit_events",
    "revocation_cancel_commands",
    "revocation_impact_manifests",
    "revocation_incidents",
    "revocation_notification_outbox",
    "revocation_quarantined_targets",
    "revocation_runtime_receipts",
    "security_revocations",
)

WAVE_TABLES: dict[int, tuple[str, ...]] = {
    1: (
        "users",
        "story_workspace_workspaces",
        "story_workspace_stories",
        "auth_sessions",
        "oauth_accounts",
        "refresh_tokens",
        "device_authorizations",
    ),
    2: (
        "story_workspace_characters",
        "story_workspace_scenes",
        "story_workspace_story_characters",
        "story_workspace_scene_characters",
    ),
    3: (
        "user_preferences",
        "user_sessions",
        "analysis_reports",
        "daily_pictures",
        "friend_invites",
        "friendships",
    ),
    4: (
        "reflections_section_configs",
        "reflection_task",
        "reflection_result",
        "reflection_task_event",
        "events",
    ),
    5: (
        "decks",
        "voices",
        "chat_thread",
        "chat_message",
        "workflow_preflights",
        "deck_plugin_releases",
        "deck_runtime_plugin_locks",
        "deck_plugin_installations",
        "deck_plugin_bindings",
        "deck_runtime_snapshots",
        "workflow_runs",
        "workflow_run_token_consumptions",
        "workflow_run_transitions",
        "runtime_plugin_materializations",
        "runtime_plugin_reconcile_attempts",
        "runtime_load_receipts",
        "runtime_load_receipt_entries",
        "agent_sessions",
        "claude_plugin_installations",
        "claude_plugin_operations",
        "deck_claude_plugin_refs",
    ),
    6: (
        "resource_connectors",
        "connector_resources",
        "connector_resource_pages",
        "connector_snapshots",
        "connector_chat_threads",
    ),
}

TABLE_TO_WAVE = {
    table_name: wave
    for wave, table_names in WAVE_TABLES.items()
    for table_name in table_names
}

# Notion stores timestamps in TEXT today.  They still have explicit temporal
# semantics and are converted to timestamptz at the PostgreSQL boundary.
NOTION_TIME_COLUMNS = {
    "resource_connectors": {"last_synced_at", "created_at", "updated_at"},
    "connector_resources": {"created_at", "updated_at"},
    "connector_resource_pages": {"last_edited", "created_at", "updated_at"},
    "connector_snapshots": {"fetched_at", "created_at", "updated_at"},
    "connector_chat_threads": {"created_at", "updated_at"},
}

# INTEGER columns that identify canonical users must remain type-compatible
# with users.id (bigint identity).  Other SQLite INTEGER values remain integer.
CANONICAL_USER_ID_COLUMNS = {
    ("analysis_reports", "user_id"),
    ("auth_sessions", "user_id"),
    ("chat_thread", "user_id"),
    ("daily_pictures", "user_id"),
    ("decks", "owner_id"),
    ("device_authorizations", "user_id"),
    ("friend_invites", "user_id"),
    ("friend_invites", "used_by"),
    ("friendships", "user_id"),
    ("friendships", "friend_id"),
    ("oauth_accounts", "user_id"),
    ("reflection_result", "user_id"),
    ("reflection_task", "user_id"),
    ("reflections_section_configs", "user_id"),
    ("refresh_tokens", "user_id"),
    ("resource_connectors", "user_id"),
    ("story_workspace_characters", "author_id"),
    ("story_workspace_scenes", "author_id"),
    ("story_workspace_stories", "author_id"),
    ("story_workspace_workspaces", "owner_id"),
    ("user_preferences", "user_id"),
    ("user_sessions", "user_id"),
    ("users", "id"),
    ("voices", "owner_id"),
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def manifest_digest(payload: dict[str, Any]) -> str:
    unsigned = deepcopy(payload)
    unsigned.pop("catalog_sha256", None)
    return hashlib.sha256(_canonical_json(unsigned).encode("utf-8")).hexdigest()


def _source_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _extract_checks(create_sql: str) -> list[str]:
    """Extract balanced CHECK bodies without pretending to parse row data."""

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
            raise ValueError("unbalanced CHECK expression in effective SQLite schema")
        checks.append(create_sql[cursor + 1 : end - 1].strip())
        position = end


def _quoted_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _column_transform(
    source: str,
    table_name: str,
    column: dict[str, Any],
    create_sql: str,
) -> dict[str, Any]:
    source_type = str(column["sqlite_type"] or "").upper()
    name = str(column["name"])
    identity_pattern = f"{name} INTEGER PRIMARY KEY AUTOINCREMENT".upper()
    identity = identity_pattern in " ".join(create_sql.split()).upper()

    if identity:
        target_type = "bigint"
        rule = "integer-primary-key-autoincrement-to-bigint-identity"
    elif (table_name, name) in CANONICAL_USER_ID_COLUMNS:
        target_type = "bigint"
        rule = "canonical-user-id-to-bigint"
    elif source == "notion" and name in NOTION_TIME_COLUMNS.get(table_name, set()):
        target_type = "timestamptz"
        rule = "validated-legacy-text-time-to-timestamptz"
    elif source_type == "DATETIME":
        target_type = "timestamptz"
        rule = "validated-legacy-datetime-to-timestamptz"
    elif source_type == "BOOLEAN":
        target_type = "boolean"
        rule = "strict-zero-one-to-boolean"
    elif source_type == "INTEGER":
        target_type = "integer"
        rule = "range-checked-integer"
    elif source_type in {"REAL", "FLOAT", "DOUBLE"}:
        target_type = "double precision"
        rule = "finite-real"
    elif source_type in {"BLOB"}:
        target_type = "bytea"
        rule = "byte-preserving-blob"
    else:
        target_type = "text"
        rule = "byte-preserving-text"

    lowered_name = name.lower()
    is_json_text = target_type == "text" and (
        "json" in lowered_name
        or lowered_name in {
            "settings",
            "tags",
            "sections",
            "input_snapshot",
            "payload",
            "related_session_ids",
        }
    )
    if is_json_text:
        rule = "validated-json-preserved-as-text"

    return {
        "target_type": target_type,
        "rule": rule,
        "identity": identity,
        "json_text": is_json_text,
        "time": target_type == "timestamptz",
    }


def _group_foreign_keys(rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    grouped: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        grouped[int(row["id"])].append(row)
    foreign_keys: list[dict[str, Any]] = []
    for foreign_key_id in sorted(grouped):
        parts = sorted(grouped[foreign_key_id], key=lambda row: int(row["seq"]))
        foreign_keys.append(
            {
                "columns": [str(row["from"]) for row in parts],
                "target_table": str(parts[0]["table"]),
                "target_columns": [str(row["to"]) for row in parts],
                "on_update": str(parts[0]["on_update"]).upper(),
                "on_delete": str(parts[0]["on_delete"]).upper(),
                "match": str(parts[0]["match"]).upper(),
                "target_only": False,
            }
        )
    return foreign_keys


def _index_columns(db: sqlite3.Connection, index_name: str) -> list[dict[str, Any]]:
    rows = db.execute(f"PRAGMA index_xinfo({_quoted_identifier(index_name)})").fetchall()
    return [
        {
            "sequence": int(row[0]),
            "column": None if int(row[1]) < 0 else str(row[2]),
            "descending": bool(row[3]),
            "collation": None if row[4] is None else str(row[4]),
            "key": bool(row[5]),
        }
        for row in rows
        if bool(row[5])
    ]


def _table_indexes(db: sqlite3.Connection, table_name: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    explicit_rows = db.execute(
        "SELECT name, sql FROM sqlite_master "
        "WHERE type = 'index' AND tbl_name = ? AND sql IS NOT NULL ORDER BY name",
        (table_name,),
    ).fetchall()
    explicit = [
        {
            "name": str(row[0]),
            "source_sql": str(row[1]),
            "columns": _index_columns(db, str(row[0])),
        }
        for row in explicit_rows
    ]

    unique_checks: list[dict[str, Any]] = []
    db.row_factory = sqlite3.Row
    for row in db.execute(f"PRAGMA index_list({_quoted_identifier(table_name)})").fetchall():
        if not bool(row["unique"]):
            continue
        name = str(row["name"])
        unique_checks.append(
            {
                "name": name,
                "columns": [
                    column["column"]
                    for column in _index_columns(db, name)
                    if column["column"] is not None
                ],
                "origin": str(row["origin"]),
                "partial": bool(row["partial"]),
            }
        )
    return explicit, sorted(unique_checks, key=lambda item: item["name"])


def _extract_database(
    source: str,
    builder: Callable[[sqlite3.Connection], Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    # Legacy builders print progress for application startup.  The offline
    # manifest stream must contain only deterministic artifact bytes.
    with redirect_stdout(io.StringIO()):
        builder(db)

    tables: list[dict[str, Any]] = []
    trigger_rows = db.execute(
        "SELECT name, tbl_name, sql FROM sqlite_master "
        "WHERE type = 'trigger' ORDER BY name"
    ).fetchall()
    triggers = [
        {
            "name": str(row["name"]),
            "table": str(row["tbl_name"]),
            "source_sql": str(row["sql"]),
        }
        for row in trigger_rows
    ]
    triggers_by_table: dict[str, list[str]] = defaultdict(list)
    for trigger in triggers:
        triggers_by_table[trigger["table"]].append(trigger["name"])

    table_rows = db.execute(
        "SELECT name, sql FROM sqlite_master "
        "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    for table_row in table_rows:
        table_name = str(table_row["name"])
        create_sql = str(table_row["sql"])
        column_rows = db.execute(
            f"PRAGMA table_xinfo({_quoted_identifier(table_name)})"
        ).fetchall()
        columns: list[dict[str, Any]] = []
        for row in column_rows:
            column = {
                "ordinal": int(row["cid"]),
                "name": str(row["name"]),
                "sqlite_type": str(row["type"] or ""),
                "not_null": bool(row["notnull"]),
                "default": row["dflt_value"],
                "pk_ordinal": int(row["pk"]),
                "hidden": int(row["hidden"]),
            }
            column["transform"] = _column_transform(source, table_name, column, create_sql)
            columns.append(column)

        primary_key = [
            column["name"]
            for column in sorted(columns, key=lambda item: item["pk_ordinal"] or 10_000)
            if column["pk_ordinal"]
        ]
        foreign_keys = _group_foreign_keys(
            db.execute(f"PRAGMA foreign_key_list({_quoted_identifier(table_name)})").fetchall()
        )
        if table_name == "chat_thread":
            # The live legacy database gained deck_id/voice_id through ALTER
            # TABLE. SQLite cannot add FK constraints with that operation, so
            # those relations exist only in freshly built fixtures. Preserve
            # the intended PostgreSQL constraints while validating the real
            # 43-table source against the one FK it physically contains.
            for foreign_key in foreign_keys:
                if foreign_key["columns"] in (["deck_id"], ["voice_id"]):
                    foreign_key["target_only"] = True
                    foreign_key["precondition"] = (
                        "source orphan count must be zero before target FK creation"
                    )
        if table_name == "resource_connectors":
            foreign_keys.append(
                {
                    "columns": ["user_id"],
                    "target_table": "users",
                    "target_columns": ["id"],
                    "on_update": "NO ACTION",
                    "on_delete": "RESTRICT",
                    "match": "NONE",
                    "target_only": True,
                    "precondition": "source orphan count must be zero before canonical FK creation",
                }
            )
        explicit_indexes, unique_checks = _table_indexes(db, table_name)
        check_expressions = _extract_checks(create_sql)
        json_columns = [
            column["name"] for column in columns if column["transform"]["json_text"]
        ]
        time_columns = [
            column["name"] for column in columns if column["transform"]["time"]
        ]
        identity_columns = [
            column["name"] for column in columns if column["transform"]["identity"]
        ]
        order_columns = primary_key or [column["name"] for column in columns]
        select_columns = ", ".join(_quoted_identifier(column["name"]) for column in columns)
        order_by = ", ".join(_quoted_identifier(column) for column in order_columns)
        tables.append(
            {
                "name": table_name,
                "source_database": source,
                "source_create_sql": create_sql,
                "columns": columns,
                "primary_key": primary_key,
                "foreign_keys": foreign_keys,
                "checks": check_expressions,
                "explicit_indexes": explicit_indexes,
                "ddl_owner": "ink-dream-memory",
                "repository_owner": "ink-dream-memory",
                "migration_wave": TABLE_TO_WAVE[table_name],
                "source_query": f"SELECT {select_columns} FROM {_quoted_identifier(table_name)} ORDER BY {order_by}",
                "type_transform": {
                    column["name"]: column["transform"] for column in columns
                },
                "pk_digest": "sha256(canonical-json(sorted(primary-key-tuples)))",
                "row_digest": "sha256(canonical-json(rows-in-primary-key-order; all columns; values never logged))",
                "unique_checks": unique_checks,
                "fk_checks": foreign_keys,
                "enum_json_time_checks": {
                    "check_expressions": check_expressions,
                    "json_text_columns": json_columns,
                    "timestamptz_columns": time_columns,
                },
                "sequence_check": (
                    {
                        "identity_columns": identity_columns,
                        "rule": "set identity sequence to max(imported id) after verified import",
                    }
                    if identity_columns
                    else None
                ),
                "trigger_checks": sorted(triggers_by_table.get(table_name, [])),
                "rollback_boundary": (
                    "baseline adoption and imported business facts are irreversible; forward repair after PostgreSQL writes"
                    if table_name in BASELINE_TABLES
                    else "no implicit destructive downgrade; forward repair after PostgreSQL business writes"
                ),
            }
        )

    counts = {
        "tables": len(tables),
        "columns": sum(len(table["columns"]) for table in tables),
        "explicit_indexes": sum(len(table["explicit_indexes"]) for table in tables),
        "triggers": len(triggers),
    }
    db.close()
    return tables, triggers, counts


def _import_legacy_builders() -> tuple[Callable[[sqlite3.Connection], Any], Callable[[sqlite3.Connection], Any]]:
    backend = str(BACKEND_ROOT)
    if backend not in sys.path:
        sys.path.insert(0, backend)
    legacy_main = importlib.import_module("schema.legacy_main_sqlite")
    legacy_notion = importlib.import_module("schema.legacy_notion_sqlite")

    def build_main(db: sqlite3.Connection) -> None:
        legacy_main.create_tables(db)
        legacy_main.create_agent_session_tables(db)
        legacy_main.create_claude_plugin_tables(db)

    return build_main, legacy_notion.create_legacy_notion_tables


def build_legacy_manifest() -> dict[str, Any]:
    """Recompute the complete metadata manifest from in-memory SQLite only."""

    build_main, build_notion = _import_legacy_builders()
    main_tables, main_triggers, main_counts = _extract_database("main", build_main)
    notion_tables, notion_triggers, notion_counts = _extract_database("notion", build_notion)
    combined_counts = {
        key: main_counts[key] + notion_counts[key]
        for key in ("tables", "columns", "explicit_indexes", "triggers")
    }
    actual_counts = {
        "main": main_counts,
        "notion": notion_counts,
        "combined": combined_counts,
    }
    if actual_counts != EXPECTED_COUNTS:
        raise RuntimeError(
            "effective SQLite schema drifted; expected "
            f"{EXPECTED_COUNTS!r}, observed {actual_counts!r}"
        )

    table_names = {table["name"] for table in main_tables + notion_tables}
    wave_names = set(TABLE_TO_WAVE)
    if table_names != wave_names:
        raise RuntimeError(
            "migration wave inventory differs from effective schema: "
            f"missing={sorted(table_names - wave_names)!r}, "
            f"unexpected={sorted(wave_names - table_names)!r}"
        )
    if table_names.intersection(REVOCATION_TEST_ONLY_TABLES):
        raise RuntimeError("test-only revocation tables entered the canonical schema")

    payload: dict[str, Any] = {
        "manifest_version": 1,
        "contract": "ink-dream-memory-postgresql-43-plus-5",
        "source": {
            "method": "in-memory effective SQLite builders; schema metadata only; no business rows",
            "main_builder": "schema.legacy_main_sqlite.create_tables + create_agent_session_tables + create_claude_plugin_tables",
            "notion_builder": "schema.legacy_notion_sqlite.create_legacy_notion_tables",
            "files": {
                "backend/schema/legacy_main_sqlite.py": _source_sha256(
                    BACKEND_ROOT / "schema" / "legacy_main_sqlite.py"
                ),
                "backend/schema/legacy_notion_sqlite.py": _source_sha256(
                    BACKEND_ROOT / "schema" / "legacy_notion_sqlite.py"
                ),
            },
        },
        "counts": actual_counts,
        "postgres_target_counts": EXPECTED_POSTGRES_COUNTS,
        "baseline_adopt": {
            "tables": list(BASELINE_TABLES),
            "policy": "all absent=create; all present+exact contract+explicit expected owner+ACL fingerprint=adopt; partial/name collision/drift=fail closed",
            "downgrade": "irreversible",
            "approved_profile": "Admin Drizzle current head after 0011_nappy_prodigy.sql",
            "source_to_target_exceptions": {
                "users.status": "approved deprecated Admin compatibility column retained; text not null default active",
                "story_workspace_workspaces.status": "approved deprecated Admin compatibility column retained; text not null default active",
                "story_workspace_workspaces.settings": "approved canonical baseline jsonb exception; all other legacy JSON remains text",
                "indexes": "Admin head replaces seven source baseline indexes with ten approved canonical indexes",
                "checks": "Admin head adds users/workspace status and story non-negative count checks",
            },
        },
        "excluded": {
            "revocation_test_only_tables": list(REVOCATION_TEST_ONLY_TABLES),
            "reason": "created only by dormant SQLiteRevocationRepository test fixture; not part of production init_db or the real 43+5 inventory",
        },
        "waves": {str(wave): list(tables) for wave, tables in WAVE_TABLES.items()},
        "tables": main_tables + notion_tables,
        "triggers": main_triggers + notion_triggers,
    }
    payload["catalog_sha256"] = manifest_digest(payload)
    return payload


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    encoded = "".join(path.read_text(encoding="ascii").splitlines())
    payload = json.loads(gzip.decompress(base64.b64decode(encoded)).decode("utf-8"))
    expected_digest = payload.get("catalog_sha256")
    actual_digest = manifest_digest(payload)
    if expected_digest != actual_digest:
        raise RuntimeError(
            f"schema manifest digest mismatch: expected {expected_digest!r}, got {actual_digest!r}"
        )
    if payload.get("counts") != EXPECTED_COUNTS:
        raise RuntimeError("checked-in schema manifest count contract is invalid")
    if payload.get("postgres_target_counts") != EXPECTED_POSTGRES_COUNTS:
        raise RuntimeError("checked-in PostgreSQL target count contract is invalid")
    return payload


def render_manifest(payload: dict[str, Any]) -> str:
    # The complete catalog repeats 567 column contracts.  Store it as
    # deterministic gzip + base64 so the checked-in artifact remains compact;
    # export/verify commands expose a human-readable aggregate receipt.
    raw = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
    encoded = base64.b64encode(gzip.compress(raw, compresslevel=9, mtime=0)).decode("ascii")
    return "\n".join(encoded[offset : offset + 76] for offset in range(0, len(encoded), 76)) + "\n"
