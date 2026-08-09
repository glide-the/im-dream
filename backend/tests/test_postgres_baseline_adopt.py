from __future__ import annotations

from dataclasses import replace

import pytest

from schema.baseline import (
    BASELINE_CONTRACTS,
    BASELINE_TABLE_NAMES,
    BaselineAdoptionError,
    decide_baseline_action,
    validate_baseline_for_adoption,
    validate_table_contract,
)
from schema.migration import IrreversibleDreamSchemaError, irreversible_downgrade


class _Type:
    def __init__(self, value: str, *, timezone: bool = False) -> None:
        self.value = value
        self.timezone = timezone

    def __str__(self) -> str:
        return self.value


def _type(value: str) -> _Type:
    if value == "timestamptz":
        return _Type("TIMESTAMP WITH TIME ZONE", timezone=True)
    return _Type(value.upper())


class _Inspector:
    def __init__(self, table_name: str) -> None:
        self.table_name = table_name
        self.contract = BASELINE_CONTRACTS[table_name]
        self.column_override = None

    def get_columns(self, _table_name: str):
        columns = [
            {
                "name": column.name,
                "type": _type(column.pg_type),
                "nullable": column.nullable,
                "default": column.default,
                "identity": {"generation": "BY DEFAULT"} if column.identity else None,
            }
            for column in self.contract.columns
        ]
        return self.column_override or columns

    def get_pk_constraint(self, _table_name: str):
        return {"constrained_columns": list(self.contract.primary_key)}

    def get_indexes(self, _table_name: str):
        return [
            {"name": name, "unique": unique, "column_names": list(columns)}
            for name, (unique, columns) in self.contract.indexes.items()
        ]

    def get_unique_constraints(self, _table_name: str):
        return []

    def get_foreign_keys(self, _table_name: str):
        return [
            {
                "name": name,
                "constrained_columns": list(columns),
                "referred_table": target_table,
                "referred_columns": list(target_columns),
                "options": {"ondelete": on_delete},
            }
            for name, (columns, target_table, target_columns, on_delete) in self.contract.foreign_keys.items()
        ]

    def get_check_constraints(self, _table_name: str):
        return [
            {"name": name, "sqltext": " ".join(tokens)}
            for name, tokens in self.contract.checks.items()
        ]


def test_baseline_action_is_all_create_or_all_exact_adopt() -> None:
    assert decide_baseline_action([]) == "create"
    assert decide_baseline_action(BASELINE_TABLE_NAMES) == "adopt"

    with pytest.raises(BaselineAdoptionError, match="partially present"):
        decide_baseline_action(["users"])
    with pytest.raises(BaselineAdoptionError, match="name collision"):
        decide_baseline_action([], ["users"])


@pytest.mark.parametrize("table_name", sorted(BASELINE_TABLE_NAMES))
def test_admin_head_baseline_contract_accepts_exact_profile(table_name: str) -> None:
    validate_table_contract(_Inspector(table_name), table_name)


def test_admin_head_baseline_contract_rejects_column_drift() -> None:
    inspector = _Inspector("users")
    columns = inspector.get_columns("users")
    columns[1] = {**columns[1], "nullable": True}
    inspector.column_override = columns

    with pytest.raises(BaselineAdoptionError, match="column contract drift"):
        validate_table_contract(inspector, "users")


def test_adoption_requires_explicit_expected_physical_owner() -> None:
    with pytest.raises(BaselineAdoptionError, match="EXPECTED_BASELINE_OWNER"):
        validate_baseline_for_adoption(
            object(),
            expected_owner=None,
            expected_acl_sha256=None,
            inspector=object(),
        )

    with pytest.raises(BaselineAdoptionError, match="EXPECTED_BASELINE_ACL_SHA256"):
        validate_baseline_for_adoption(
            object(),
            expected_owner="approved_owner",
            expected_acl_sha256=None,
            inspector=object(),
        )


@pytest.mark.parametrize("wave", range(1, 7))
def test_all_schema_downgrades_are_non_destructive_and_irreversible(wave: int) -> None:
    with pytest.raises(IrreversibleDreamSchemaError, match="forward repair"):
        irreversible_downgrade(wave)
