"""Execution helpers shared by the six Dream Alembic revisions."""

from __future__ import annotations

import os
from typing import Any

from .baseline import (
    BASELINE_TABLE_NAMES,
    decide_baseline_action,
    validate_baseline_for_adoption,
)
from .catalog import load_manifest
from .postgres import wave_statements


class IrreversibleDreamSchemaError(RuntimeError):
    """Dream canonical facts cannot be safely deleted by an Alembic downgrade."""


def _execute(bind: Any, statement: str) -> None:
    bind.exec_driver_sql(statement)


def upgrade_wave(bind: Any, wave: int) -> str:
    """Create one dependency wave; wave 1 may exactly adopt three tables."""

    manifest = load_manifest()
    if str(wave) not in manifest["waves"]:
        raise ValueError(f"unknown Dream migration wave: {wave}")

    if wave != 1:
        for statement in wave_statements(wave, manifest=manifest):
            _execute(bind, statement)
        return "created"

    from sqlalchemy import inspect

    inspector = inspect(bind)
    action = decide_baseline_action(
        inspector.get_table_names(),
        inspector.get_view_names(),
    )
    if action == "adopt":
        validate_baseline_for_adoption(
            bind,
            expected_owner=os.getenv("DREAM_EXPECTED_BASELINE_OWNER"),
            expected_acl_sha256=os.getenv("DREAM_EXPECTED_BASELINE_ACL_SHA256"),
            inspector=inspector,
        )
        statements = wave_statements(1, manifest=manifest, include_baseline=False)
    else:
        statements = wave_statements(1, manifest=manifest, include_baseline=True)
    for statement in statements:
        _execute(bind, statement)
    return action


def irreversible_downgrade(wave: int) -> None:
    tables = load_manifest()["waves"][str(wave)]
    baseline_note = " including adopted baseline" if BASELINE_TABLE_NAMES.intersection(tables) else ""
    raise IrreversibleDreamSchemaError(
        f"Dream migration wave {wave}{baseline_note} is irreversible; use a reviewed forward repair"
    )
