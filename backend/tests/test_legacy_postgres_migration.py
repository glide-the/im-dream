from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
from uuid import UUID

import pytest

import schema.importer as legacy_importer
from persistence.config import require_test_database_url
from schema.catalog import load_manifest
from schema.importer import (
    CONTRACT,
    LegacyMigrationError,
    readonly_snapshot_bundle,
    run_legacy_migration,
    scan_sources,
    transform_value,
    wave_topological_order,
)
from script.migrate_legacy_to_postgres import main as migration_cli_main


def _create_legacy_file(path: Path, source: str) -> None:
    manifest = load_manifest()
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        tables = [
            table
            for table in manifest["tables"]
            if table["source_database"] == source
        ]
        for table in tables:
            connection.execute(str(table["source_create_sql"]))
        for table in tables:
            for index in table["explicit_indexes"]:
                connection.execute(str(index["source_sql"]))
        table_names = {str(table["name"]) for table in tables}
        for trigger in manifest["triggers"]:
            if str(trigger["table"]) in table_names:
                connection.execute(str(trigger["source_sql"]))
        connection.commit()
    finally:
        connection.close()


def _legacy_pair(tmp_path: Path, *, populated: bool = True) -> tuple[Path, Path]:
    main = tmp_path / "main-fixture.db"
    notion = tmp_path / "notion-fixture.db"
    _create_legacy_file(main, "main")
    _create_legacy_file(notion, "notion")
    if populated:
        connection = sqlite3.connect(main)
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute(
                "INSERT INTO users "
                "(id,email,password_hash,display_name,avatar_url,role,created_at,updated_at) "
                "VALUES (1,?,?,?,?,?,?,?)",
                (
                    "migration-user@example.invalid",
                    "not-a-real-secret",
                    "Migration Fixture",
                    None,
                    "user",
                    "2026-08-09 00:00:00",
                    "2026-08-09T00:00:00Z",
                ),
            )
            connection.execute(
                "INSERT INTO story_workspace_workspaces "
                "(id,name,owner_id,settings,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                (
                    "workspace-fixture",
                    "Fixture",
                    1,
                    '{"theme":"ink"}',
                    "2026-08-09 00:00:00",
                    "2026-08-09T00:00:00+00:00",
                ),
            )
            connection.execute(
                "INSERT INTO story_workspace_stories "
                "(id,identifier,title,description,status,review_status,type,content,"
                "author_id,workspace_id,character_count,scene_count,agent_generated,"
                "agent_session_id,review_notes,created_at,updated_at,confirmed_at,published_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    "story-fixture",
                    "fixture-001",
                    "Fixture",
                    None,
                    "draft",
                    "pending",
                    "short",
                    None,
                    1,
                    "workspace-fixture",
                    0,
                    0,
                    1,
                    None,
                    None,
                    "2026-08-09 00:00:00",
                    "2026-08-09T00:00:00Z",
                    None,
                    None,
                ),
            )
            connection.commit()
        finally:
            connection.close()

        connection = sqlite3.connect(notion)
        try:
            connection.execute(
                "INSERT INTO resource_connectors "
                "(id,user_id,name,platform,auth_status,config_json,"
                "current_snapshot_version,current_source_revision,current_sync_cursor,"
                "last_synced_at,created_at,updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    "connector-fixture",
                    1,
                    "Fixture",
                    "notion",
                    "connected",
                    '{"selected":[]}',
                    None,
                    None,
                    None,
                    "2026-08-09T00:00:00Z",
                    "2026-08-09T00:00:00Z",
                    "2026-08-09T00:00:00Z",
                ),
            )
            connection.commit()
        finally:
            connection.close()
    return main, notion


def _snapshot_kwargs(main: Path, notion: Path) -> dict[str, object]:
    return {
        "main_path": main,
        "notion_path": notion,
        "expected_main_filename": main.name,
        "expected_notion_filename": notion.name,
    }


def test_manifest_order_covers_all_43_plus_5_tables_and_respects_foreign_keys() -> None:
    manifest = load_manifest()
    order = wave_topological_order(manifest)
    assert len(order) == 48
    assert len(set(order)) == 48
    positions = {name: index for index, name in enumerate(order)}
    table_by_name = {str(table["name"]): table for table in manifest["tables"]}
    assert [table_by_name[name]["migration_wave"] for name in order] == sorted(
        table_by_name[name]["migration_wave"] for name in order
    )
    for name, table in table_by_name.items():
        for foreign_key in table["foreign_keys"]:
            target = str(foreign_key["target_table"])
            if target != name:
                assert positions[target] < positions[name]


def test_readonly_online_backup_and_source_validation_cover_all_tables(
    tmp_path: Path,
) -> None:
    main, notion = _legacy_pair(tmp_path)
    manifest = load_manifest()
    with readonly_snapshot_bundle(
        main,
        notion,
        expected_main_filename=main.name,
        expected_notion_filename=notion.name,
    ) as snapshots:
        reports, schema_digests, foreign_key_checks = scan_sources(
            snapshots, manifest, batch_size=2
        )
        assert snapshots.main.path != main
        assert snapshots.notion.path != notion
        assert snapshots.main.sha256
        assert snapshots.notion.sha256
    assert len(reports) == 48
    assert sum(report["sourceCount"] for report in reports) == 4
    assert {report["source"] for report in reports} == {"main", "notion"}
    assert set(schema_digests) == {"main", "notion"}
    assert foreign_key_checks == sum(
        len(table["foreign_keys"]) for table in manifest["tables"]
    )
    assert all(len(report["pkSha256"]) == 64 for report in reports)
    assert all(len(report["rowSha256"]) == 64 for report in reports)


@pytest.mark.parametrize(
    ("relative", "code"),
    [
        (True, "SOURCE_PATH_NOT_ABSOLUTE"),
        (False, "SOURCE_FILENAME_UNEXPECTED"),
    ],
)
def test_source_path_and_filename_guards(
    tmp_path: Path, relative: bool, code: str
) -> None:
    main, notion = _legacy_pair(tmp_path, populated=False)
    selected_main = Path(main.name) if relative else main
    with pytest.raises(LegacyMigrationError) as captured:
        with readonly_snapshot_bundle(
            selected_main,
            notion,
            expected_main_filename="approved.db" if not relative else main.name,
            expected_notion_filename=notion.name,
        ):
            pass
    assert captured.value.code == code


def test_source_symlink_is_rejected(tmp_path: Path) -> None:
    main, notion = _legacy_pair(tmp_path, populated=False)
    linked = tmp_path / "linked-main.db"
    linked.symlink_to(main)
    with pytest.raises(LegacyMigrationError) as captured:
        with readonly_snapshot_bundle(
            linked,
            notion,
            expected_main_filename=linked.name,
            expected_notion_filename=notion.name,
        ):
            pass
    assert captured.value.code == "SOURCE_SYMLINK_REJECTED"


def test_cross_database_notion_user_orphan_blocks_migration(tmp_path: Path) -> None:
    main, notion = _legacy_pair(tmp_path)
    connection = sqlite3.connect(notion)
    try:
        connection.execute("UPDATE resource_connectors SET user_id=999")
        connection.commit()
    finally:
        connection.close()
    with readonly_snapshot_bundle(
        main,
        notion,
        expected_main_filename=main.name,
        expected_notion_filename=notion.name,
    ) as snapshots:
        with pytest.raises(LegacyMigrationError) as captured:
            scan_sources(snapshots, load_manifest(), batch_size=10)
    assert captured.value.code == "SOURCE_FOREIGN_KEY_ORPHAN"


@pytest.mark.parametrize(
    ("statement", "code"),
    [
        (
            "UPDATE story_workspace_workspaces SET settings='not-json'",
            "SOURCE_JSON_INVALID",
        ),
        (
            "UPDATE story_workspace_workspaces SET created_at='not-time'",
            "SOURCE_TIME_INVALID",
        ),
    ],
)
def test_invalid_json_and_time_block_before_staging(
    tmp_path: Path, statement: str, code: str
) -> None:
    main, notion = _legacy_pair(tmp_path)
    connection = sqlite3.connect(main)
    try:
        connection.execute(statement)
        connection.commit()
    finally:
        connection.close()
    with readonly_snapshot_bundle(
        main,
        notion,
        expected_main_filename=main.name,
        expected_notion_filename=notion.name,
    ) as snapshots:
        with pytest.raises(LegacyMigrationError) as captured:
            scan_sources(snapshots, load_manifest(), batch_size=10)
    assert captured.value.code == code


def test_strict_value_transforms_cover_boolean_integer_json_and_time() -> None:
    manifest = load_manifest()
    decks = next(table for table in manifest["tables"] if table["name"] == "decks")
    enabled = next(column for column in decks["columns"] if column["name"] == "enabled")
    assert transform_value("decks", enabled, 1) is True
    with pytest.raises(LegacyMigrationError, match="SOURCE_BOOLEAN_INVALID"):
        transform_value("decks", enabled, 2)

    workspaces = next(
        table
        for table in manifest["tables"]
        if table["name"] == "story_workspace_workspaces"
    )
    settings = next(
        column for column in workspaces["columns"] if column["name"] == "settings"
    )
    assert transform_value(workspaces["name"], settings, '{"b":1}') == {"b": 1}
    created = next(
        column for column in workspaces["columns"] if column["name"] == "created_at"
    )
    assert transform_value(workspaces["name"], created, "2026-08-09 00:00:00").tzinfo


def test_default_source_dry_run_receipt_is_redacted_and_does_not_claim_target(
    tmp_path: Path,
) -> None:
    main, notion = _legacy_pair(tmp_path)
    receipt = run_legacy_migration(
        **_snapshot_kwargs(main, notion),
        mode="source-dry-run",
        batch_size=3,
        run_id=UUID("00000000-0000-4000-8000-000000000001"),
    )
    rendered = json.dumps(receipt, sort_keys=True)
    assert receipt["contract"] == CONTRACT
    assert receipt["status"] == "validated"
    assert receipt["validation"]["tables"] == 48
    assert receipt["validation"]["targetComplete"] is False
    assert receipt["phases"]["staging"] == "not_run"
    assert receipt["target"]["validated"] is False
    assert str(main) not in rendered
    assert str(notion) not in rendered
    assert "migration-user@example.invalid" not in rendered
    assert "not-a-real-secret" not in rendered
    assert receipt["security"] == {
        "containsBusinessValues": False,
        "containsSourcePaths": False,
        "containsDsn": False,
        "implicitOverwrite": False,
        "destructiveTargetCleanup": False,
    }


def test_cli_defaults_to_source_dry_run_and_prints_only_json_receipt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main, notion = _legacy_pair(tmp_path)
    exit_code = migration_cli_main(
        [
            "--main-sqlite",
            str(main),
            "--notion-sqlite",
            str(notion),
            "--expected-main-filename",
            main.name,
            "--expected-notion-filename",
            notion.name,
            "--batch-size",
            "2",
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    receipt = json.loads(captured.out)
    assert receipt["mode"] == "source-dry-run"
    assert receipt["validation"]["tables"] == 48
    assert str(main) not in captured.out
    assert "migration-user@example.invalid" not in captured.out


def test_cli_failure_receipt_is_stable_redacted_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main, notion = _legacy_pair(tmp_path, populated=False)
    run_id = "00000000-0000-4000-8000-000000000003"
    exit_code = migration_cli_main(
        [
            "--main-sqlite",
            str(main),
            "--notion-sqlite",
            str(notion),
            "--expected-main-filename",
            "wrong.db",
            "--expected-notion-filename",
            notion.name,
            "--migration-run-id",
            run_id,
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    receipt = json.loads(captured.err)
    assert receipt == {
        "contract": CONTRACT,
        "status": "failed",
        "runId": run_id,
        "phase": "snapshot",
        "errorCode": "SOURCE_FILENAME_UNEXPECTED",
        "details": {},
        "containsBusinessValues": False,
        "containsSourcePaths": False,
        "containsDsn": False,
    }
    assert str(main) not in captured.err


def test_target_modes_require_exact_database_and_isolation_safety(
    tmp_path: Path,
) -> None:
    main, notion = _legacy_pair(tmp_path, populated=False)
    with pytest.raises(LegacyMigrationError) as captured:
        run_legacy_migration(
            **_snapshot_kwargs(main, notion),
            mode="target-dry-run",
        )
    assert captured.value.code == "EXPECTED_TARGET_DATABASE_REQUIRED"

    with pytest.raises(LegacyMigrationError) as captured:
        run_legacy_migration(
            **_snapshot_kwargs(main, notion),
            mode="execute",
            expected_target_database="ink_memory_codex_test",
            environ={},
        )
    assert captured.value.code == "TARGET_SAFETY_CHECK_FAILED"


def test_migration_sql_has_no_implicit_overwrite_or_destructive_target_statement() -> None:
    source = (
        Path(__file__).resolve().parents[1] / "schema" / "importer.py"
    ).read_text(encoding="utf-8")
    normalized = source.upper()
    assert "ON CONFLICT DO UPDATE" not in normalized
    assert "DELETE FROM" not in normalized
    assert "TRUNCATE" not in normalized
    assert "DROP TABLE" not in normalized


@pytest.mark.skipif(
    os.getenv("INK_RUN_LEGACY_PG_MIGRATION_TEST") != "1",
    reason="requires an explicitly owned, Alembic-head, empty TEST_DATABASE_URL",
)
def test_isolated_postgres_full_48_table_rehearsal_rolls_back(tmp_path: Path) -> None:
    expected_database = os.environ.get("INK_EXPECTED_TEST_DATABASE", "")
    assert expected_database
    main, notion = _legacy_pair(tmp_path)
    receipt = run_legacy_migration(
        **_snapshot_kwargs(main, notion),
        mode="target-dry-run",
        expected_target_database=expected_database,
        batch_size=2,
    )
    assert receipt["target"]["validated"] is True
    assert receipt["target"]["stagingTables"] == 48
    assert receipt["target"]["transaction"] == "rolled_back_rehearsal"
    assert receipt["validation"]["targetComplete"] is True
    assert sum(table["inserted"] for table in receipt["tables"]) == 4


@pytest.mark.skipif(
    os.getenv("INK_RUN_LEGACY_PG_MIGRATION_TEST") != "1",
    reason="requires an explicitly owned, Alembic-head, empty TEST_DATABASE_URL",
)
def test_isolated_postgres_baseline_exact_match_and_drift_are_distinguished(
    tmp_path: Path,
) -> None:
    expected_database = os.environ.get("INK_EXPECTED_TEST_DATABASE", "")
    assert expected_database
    dsn = require_test_database_url(expected_database)
    main, notion = _legacy_pair(tmp_path)
    manifest = load_manifest()
    tables = {str(table["name"]): table for table in manifest["tables"]}
    run_id = UUID("00000000-0000-4000-8000-000000000002")

    import psycopg

    with readonly_snapshot_bundle(
        main,
        notion,
        expected_main_filename=main.name,
        expected_notion_filename=notion.name,
    ) as snapshots:
        connection = psycopg.connect(dsn, autocommit=False)
        try:
            connection.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
            stages: dict[str, str] = {}
            for name in (
                "users",
                "story_workspace_workspaces",
                "story_workspace_stories",
            ):
                stages[name], _ = legacy_importer._stage_table(
                    connection,
                    snapshots,
                    tables[name],
                    run_id=run_id,
                    batch_size=2,
                )
                assert legacy_importer._insert_from_stage(
                    connection,
                    tables[name],
                    stages[name],
                    baseline=True,
                ) == 1
                assert legacy_importer._baseline_conflicts(
                    connection, tables[name], stages[name]
                ) == (0, 0, 1)
            baseline_names = (
                "users",
                "story_workspace_workspaces",
                "story_workspace_stories",
            )
            baseline_tables = {name: tables[name] for name in baseline_names}
            exact_reports = {name: {} for name in baseline_names}
            legacy_importer._validate_target_conflicts(
                connection,
                baseline_tables,
                stages,
                exact_reports,
                commit=False,
                approve_baseline_inserts=False,
            )

            connection.execute(
                "UPDATE users SET display_name='different' WHERE id=1"
            )
            connection.execute(
                "UPDATE story_workspace_workspaces SET name='different' "
                "WHERE id='workspace-fixture'"
            )
            connection.execute(
                "UPDATE story_workspace_stories SET title='different' "
                "WHERE id='story-fixture'"
            )
            for name in (
                "users",
                "story_workspace_workspaces",
                "story_workspace_stories",
            ):
                missing, mismatched, matched = legacy_importer._baseline_conflicts(
                    connection, tables[name], stages[name]
                )
                assert missing == 0
                assert mismatched == 1
                assert matched == 1
            with pytest.raises(LegacyMigrationError) as captured:
                legacy_importer._validate_target_conflicts(
                    connection,
                    baseline_tables,
                    stages,
                    {name: {} for name in baseline_names},
                    commit=False,
                    approve_baseline_inserts=False,
                )
            assert captured.value.code == "TARGET_CONFLICTS_DETECTED"
            assert captured.value.details == {
                "conflicts": [
                    {
                        "table": "story_workspace_stories",
                        "kind": "baseline_row_or_unique_drift",
                        "count": 1,
                    },
                    {
                        "table": "story_workspace_workspaces",
                        "kind": "baseline_row_or_unique_drift",
                        "count": 1,
                    },
                    {
                        "table": "users",
                        "kind": "baseline_row_or_unique_drift",
                        "count": 1,
                    },
                ]
            }
        finally:
            connection.rollback()
            connection.close()
