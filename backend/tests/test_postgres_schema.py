from __future__ import annotations

from schema.catalog import (
    EXPECTED_COUNTS,
    EXPECTED_POSTGRES_COUNTS,
    MANIFEST_PATH,
    REVOCATION_TEST_ONLY_TABLES,
    build_legacy_manifest,
    load_manifest,
    render_manifest,
)
from schema.importer import APPROVED_TARGET_INDEXES


REQUIRED_TABLE_FIELDS = {
    "ddl_owner",
    "repository_owner",
    "migration_wave",
    "source_query",
    "type_transform",
    "pk_digest",
    "row_digest",
    "unique_checks",
    "fk_checks",
    "enum_json_time_checks",
    "sequence_check",
    "trigger_checks",
    "rollback_boundary",
}


def test_effective_43_plus_5_manifest_is_reproducible() -> None:
    checked_in = load_manifest()
    recomputed = build_legacy_manifest()

    assert checked_in == recomputed
    assert MANIFEST_PATH.read_text(encoding="ascii") == render_manifest(recomputed)
    assert checked_in["counts"] == EXPECTED_COUNTS
    assert checked_in["counts"]["main"] == {
        "tables": 43,
        "columns": 522,
        "explicit_indexes": 73,
        "triggers": 25,
    }
    assert checked_in["counts"]["notion"] == {
        "tables": 5,
        "columns": 45,
        "explicit_indexes": 5,
        "triggers": 0,
    }
    assert checked_in["counts"]["combined"] == {
        "tables": 48,
        "columns": 567,
        "explicit_indexes": 78,
        "triggers": 25,
    }


def test_every_table_has_the_migration_delivery_contract() -> None:
    manifest = load_manifest()
    names = {table["name"] for table in manifest["tables"]}

    assert len(names) == 48
    assert not names.intersection(REVOCATION_TEST_ONLY_TABLES)
    assert set(manifest["excluded"]["revocation_test_only_tables"]) == set(
        REVOCATION_TEST_ONLY_TABLES
    )
    for table in manifest["tables"]:
        assert REQUIRED_TABLE_FIELDS <= set(table)
        assert table["ddl_owner"] == "ink-dream-memory"
        assert table["repository_owner"] == "ink-dream-memory"
        assert table["primary_key"]
        assert table["source_query"].startswith("SELECT ")
        assert table["rollback_boundary"]
        assert set(table["type_transform"]) == {
            column["name"] for column in table["columns"]
        }


def test_postgres_target_separates_approved_baseline_delta_from_source() -> None:
    manifest = load_manifest()

    assert manifest["postgres_target_counts"] == EXPECTED_POSTGRES_COUNTS == {
        "tables": 48,
        "columns": 569,
        "explicit_indexes": 82,
        "triggers": 25,
    }
    exceptions = manifest["baseline_adopt"]["source_to_target_exceptions"]
    assert "users.status" in exceptions
    assert "story_workspace_workspaces.status" in exceptions
    assert "jsonb" in exceptions["story_workspace_workspaces.settings"]
    assert APPROVED_TARGET_INDEXES["users_email_uidx"] == ("users", True)
    assert APPROVED_TARGET_INDEXES["idx_workflow_runs_source_voice_thread"] == (
        "workflow_runs",
        False,
    )


def test_legacy_json_is_text_except_approved_workspace_baseline() -> None:
    manifest = load_manifest()
    for table in manifest["tables"]:
        for column in table["columns"]:
            if column["transform"]["json_text"]:
                assert column["transform"]["target_type"] == "text"

def test_wave_inventory_is_total_and_dependency_ordered() -> None:
    manifest = load_manifest()
    ordered = [
        table
        for wave in sorted(manifest["waves"], key=int)
        for table in manifest["waves"][wave]
    ]
    assert len(ordered) == len(set(ordered)) == 48
    assert set(ordered) == {table["name"] for table in manifest["tables"]}
    positions = {name: index for index, name in enumerate(ordered)}
    tables = {table["name"]: table for table in manifest["tables"]}
    for source_name, table in tables.items():
        for foreign_key in table["foreign_keys"]:
            target_name = foreign_key["target_table"]
            if target_name in positions and target_name != source_name:
                assert positions[target_name] < positions[source_name], (
                    f"{source_name} is ordered before FK target {target_name}"
                )
    assert positions["users"] < positions["story_workspace_workspaces"]
    assert positions["story_workspace_workspaces"] < positions["story_workspace_stories"]
    assert positions["workflow_runs"] < positions["runtime_load_receipts"]
    assert positions["runtime_load_receipts"] < positions["agent_sessions"]
    assert positions["resource_connectors"] < positions["connector_resources"]


def test_dream_keeps_only_the_legacy_data_manifest() -> None:
    assert MANIFEST_PATH.name == "legacy_schema_manifest.json.gz.b64"
