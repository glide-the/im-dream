from __future__ import annotations

import re

from schema.catalog import load_manifest
from schema.postgres import all_trigger_ddls


APPEND_ONLY_TRIGGER_PREFIXES = {
    "deck_runtime_snapshots": "deck_runtime_snapshots",
    "events": "events",
    "runtime_load_receipt_entries": "runtime_load_receipt_entries",
    "runtime_load_receipts": "runtime_load_receipts",
    "runtime_plugin_reconcile_attempts": "runtime_reconcile_attempts",
    "workflow_run_token_consumptions": "workflow_run_token_consumptions",
    "workflow_run_transitions": "workflow_run_transitions",
}


def test_all_25_sqlite_guards_have_postgres_function_and_trigger() -> None:
    manifest = load_manifest()
    pairs = list(all_trigger_ddls(manifest))

    assert len(manifest["triggers"]) == len(pairs) == 25
    rendered = "\n".join(part for pair in pairs for part in pair)
    assert rendered.count("CREATE FUNCTION") == 25
    assert rendered.count("CREATE TRIGGER") == 25
    assert "RAISE(ABORT" not in rendered
    assert "IF NOT EXISTS" not in rendered
    assert "IS DISTINCT FROM" in rendered
    assert "IS NOT DISTINCT FROM" in rendered


def test_append_only_tables_have_update_and_delete_guards() -> None:
    manifest = load_manifest()
    trigger_names = {trigger["name"] for trigger in manifest["triggers"]}
    for table_name, prefix in APPEND_ONLY_TRIGGER_PREFIXES.items():
        assert table_name in {trigger["table"] for trigger in manifest["triggers"]}
        assert f"{prefix}_no_update" in trigger_names
        assert f"{prefix}_no_delete" in trigger_names


def test_voice_source_guard_uses_postgres_num_nonnulls() -> None:
    manifest = load_manifest()
    source = next(
        trigger
        for trigger in manifest["triggers"]
        if trigger["name"] == "workflow_runs_voice_source_insert_guard"
    )
    function, trigger = next(
        pair
        for item, pair in zip(manifest["triggers"], all_trigger_ddls(manifest))
        if item["name"] == source["name"]
    )

    assert "num_nonnulls(" in function
    assert "num_nonnull(" not in function
    assert "+ (NEW." not in function
    assert "BEFORE INSERT" in trigger


def test_trigger_identifiers_are_unique_and_postgres_safe() -> None:
    manifest = load_manifest()
    names = [trigger["name"] for trigger in manifest["triggers"]]
    assert len(names) == len(set(names)) == 25
    assert all(re.fullmatch(r"[a-z0-9_]+", name) for name in names)
