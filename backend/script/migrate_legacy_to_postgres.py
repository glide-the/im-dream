#!/usr/bin/env python3
"""Rehearse or execute the Dream 43 + 5 SQLite to PostgreSQL import.

The default mode validates read-only SQLite Online Backup snapshots and does
not connect to PostgreSQL. ``--target-dry-run`` rehearses staging/import in an
isolated PostgreSQL transaction and rolls it back. ``--execute`` commits only
to a safety-validated ``TEST_DATABASE_URL``. ``--production-execute`` is a
separate explicit cutover path that verifies DATABASE_URL name/host/port/owner.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from uuid import UUID, uuid4


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from schema.importer import (  # noqa: E402
    CONTRACT,
    DEFAULT_MAIN_FILENAME,
    DEFAULT_NOTION_FILENAME,
    LegacyMigrationError,
    run_legacy_migration,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--main-sqlite",
        type=Path,
        required=True,
        help="absolute path to the legacy 43-table main SQLite file",
    )
    parser.add_argument(
        "--notion-sqlite",
        type=Path,
        required=True,
        help="absolute path to the legacy 5-table Notion SQLite file",
    )
    parser.add_argument(
        "--expected-main-filename",
        default=DEFAULT_MAIN_FILENAME,
        help="exact expected main source basename",
    )
    parser.add_argument(
        "--expected-notion-filename",
        default=DEFAULT_NOTION_FILENAME,
        help="exact expected Notion source basename",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--target-dry-run",
        action="store_true",
        help="stage/import/verify against TEST_DATABASE_URL, then roll back",
    )
    mode.add_argument(
        "--execute",
        action="store_true",
        help="commit to an isolated TEST_DATABASE_URL after all validations pass",
    )
    mode.add_argument(
        "--production-execute",
        action="store_true",
        help="commit to DATABASE_URL only with complete explicit target identity",
    )
    parser.add_argument(
        "--expected-target-database",
        help="required exact database name for either PostgreSQL mode",
    )
    parser.add_argument(
        "--approve-baseline-inserts",
        action="store_true",
        help="with --execute, approve insertion of missing canonical baseline rows",
    )
    parser.add_argument("--expected-target-host")
    parser.add_argument("--expected-target-port", type=int)
    parser.add_argument("--expected-target-owner")
    parser.add_argument(
        "--production-approval",
        help="must equal MIGRATE-43+5-TO:<expected database>",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1_000,
        help="bounded staging batch size (1..100000)",
    )
    parser.add_argument(
        "--migration-run-id",
        type=UUID,
        help="optional caller-assigned UUID for an auditable rehearsal",
    )
    return parser


def _mode(arguments: argparse.Namespace) -> str:
    if arguments.production_execute:
        return "production-execute"
    if arguments.execute:
        return "execute"
    if arguments.target_dry_run:
        return "target-dry-run"
    return "source-dry-run"


def _safe_filename(value: str) -> bool:
    return bool(value) and Path(value).name == value and value not in {".", ".."}


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    selected_mode = _mode(arguments)
    migration_run_id = arguments.migration_run_id or uuid4()
    try:
        if not _safe_filename(arguments.expected_main_filename) or not _safe_filename(
            arguments.expected_notion_filename
        ):
            raise LegacyMigrationError(
                "EXPECTED_SOURCE_FILENAME_INVALID", phase="configuration"
            )
        receipt = run_legacy_migration(
            main_path=arguments.main_sqlite,
            notion_path=arguments.notion_sqlite,
            mode=selected_mode,
            expected_main_filename=arguments.expected_main_filename,
            expected_notion_filename=arguments.expected_notion_filename,
            expected_target_database=arguments.expected_target_database,
            approve_baseline_inserts=arguments.approve_baseline_inserts,
            expected_target_host=arguments.expected_target_host,
            expected_target_port=arguments.expected_target_port,
            expected_target_owner=arguments.expected_target_owner,
            production_approval=arguments.production_approval,
            batch_size=arguments.batch_size,
            run_id=migration_run_id,
        )
    except LegacyMigrationError as error:
        print(
            json.dumps(
                {
                    "contract": CONTRACT,
                    "status": "failed",
                    "runId": str(migration_run_id),
                    "phase": error.phase,
                    "errorCode": error.code,
                    "details": error.details,
                    "containsBusinessValues": False,
                    "containsSourcePaths": False,
                    "containsDsn": False,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 2
    except BaseException as error:
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            raise
        print(
            json.dumps(
                {
                    "contract": CONTRACT,
                    "status": "failed",
                    "runId": str(migration_run_id),
                    "phase": "internal",
                    "errorCode": "MIGRATION_INTERNAL_ERROR",
                    "containsBusinessValues": False,
                    "containsSourcePaths": False,
                    "containsDsn": False,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
