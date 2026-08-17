#!/usr/bin/env python3
"""Report Story Artifact index drift without changing PostgreSQL or files.

This command has one mode: dry-run.  It starts a read-only PostgreSQL
transaction through the reconcile service and always rolls the connection back.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.story_workspace.artifact_story_index_reconcile import (  # noqa: E402
    ArtifactStoryIndexReconcileReport,
    ArtifactStoryIndexReconcileService,
    decode_reconcile_cursor,
)


_EXIT_DATABASE_UNAVAILABLE = 2
_WORKSPACE_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,255}$")
_RUN_ID = re.compile(r"^run_[0-9a-f]{32}$")


def _workspace_id(value: str) -> str:
    if _WORKSPACE_ID.fullmatch(value) is None:
        raise argparse.ArgumentTypeError("workspace id is invalid")
    return value


def _run_id(value: str) -> str:
    if _RUN_ID.fullmatch(value) is None:
        raise argparse.ArgumentTypeError("run id is invalid")
    return value


def _bounded_limit(value: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError("limit must be an integer") from None
    if not 1 <= parsed <= 500:
        raise argparse.ArgumentTypeError("limit must be between 1 and 500")
    return parsed


def _bounded_deadline(value: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError("deadline must be a number") from None
    if not 0 < parsed <= 60.0:
        raise argparse.ArgumentTypeError(
            "deadline must be greater than 0 and at most 60 seconds"
        )
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="report drift only (the only supported mode)",
    )
    parser.add_argument(
        "--workspace-id",
        type=_workspace_id,
        help="restrict candidates to one workspace",
    )
    parser.add_argument(
        "--run-id",
        type=_run_id,
        help="restrict candidates to one workflow run",
    )
    parser.add_argument(
        "--limit",
        type=_bounded_limit,
        default=100,
        help="maximum DB candidates to inspect across both phases (default: 100)",
    )
    parser.add_argument(
        "--cursor",
        help="opaque next_cursor from a prior invocation with the same scope",
    )
    parser.add_argument(
        "--deadline-seconds",
        type=_bounded_deadline,
        default=10.0,
        help="soft wall-clock deadline between candidates (default: 10)",
    )
    return parser


def _open_database() -> Any:
    # Match the runtime DATABASE_URL without starting the process-wide pool.
    # A one-shot read-only command owns exactly one direct connection, which
    # keeps ``--help`` side-effect free and guarantees prompt interpreter exit.
    from dotenv import load_dotenv
    import psycopg
    from psycopg.rows import dict_row
    from persistence.config import DATABASE_URL_ENV, parse_postgres_target

    load_dotenv(BACKEND_ROOT / ".env", override=False)
    target = parse_postgres_target(os.environ.get(DATABASE_URL_ENV, ""))
    return psycopg.connect(
        target.dsn,
        autocommit=False,
        row_factory=dict_row,
        application_name="ink-dream-memory-story-index-reconcile",
    )


def _close_database(db: Any) -> None:
    try:
        db.rollback()
    except Exception:
        pass
    try:
        db.close()
    except Exception:
        pass


def execute_dry_run(
    arguments: argparse.Namespace,
    *,
    db_factory: Callable[[], Any] | None = None,
    service_factory: Callable[[], ArtifactStoryIndexReconcileService] | None = None,
) -> ArtifactStoryIndexReconcileReport:
    # Validate the scope-bound cursor before a network connection is attempted.
    decode_reconcile_cursor(
        arguments.cursor,
        workspace_id=arguments.workspace_id,
        run_id=arguments.run_id,
    )
    try:
        db = (db_factory or _open_database)()
    except Exception:
        return ArtifactStoryIndexReconcileReport.database_failure("unavailable")
    try:
        service = (service_factory or ArtifactStoryIndexReconcileService)()
        return service.dry_run(
            db=db,
            workspace_id=arguments.workspace_id,
            run_id=arguments.run_id,
            limit=arguments.limit,
            cursor=arguments.cursor,
            deadline_seconds=arguments.deadline_seconds,
        )
    except ValueError:
        raise
    except Exception:
        return ArtifactStoryIndexReconcileReport.database_failure("unavailable")
    finally:
        _close_database(db)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        report = execute_dry_run(arguments)
    except ValueError as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            report.public_dict(),
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0 if report.database_status == "available" else _EXIT_DATABASE_UNAVAILABLE


if __name__ == "__main__":
    raise SystemExit(main())
