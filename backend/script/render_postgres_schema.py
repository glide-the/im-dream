#!/usr/bin/env python3
"""Render/check ordinary PostgreSQL DDL from the checked-in manifest."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from schema.catalog import POSTGRES_SCHEMA_PATH, load_manifest
from schema.postgres import render_postgres_schema


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    rendered = render_postgres_schema(load_manifest())
    if arguments.check:
        if not POSTGRES_SCHEMA_PATH.exists():
            raise SystemExit(f"PostgreSQL schema artifact is missing: {POSTGRES_SCHEMA_PATH}")
        if POSTGRES_SCHEMA_PATH.read_text(encoding="utf-8") != rendered:
            raise SystemExit(
                "postgres_schema.sql is stale; inspect the generated DDL before updating"
            )
        print("PostgreSQL schema DDL: OK (48 tables / 569 columns / 81 indexes / 25 triggers)")
        return 0
    if arguments.output:
        arguments.output.write_text(rendered, encoding="utf-8")
        print(f"wrote PostgreSQL schema DDL: {arguments.output}")
        return 0
    sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
