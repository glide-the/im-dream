#!/usr/bin/env python3
"""Export/check the data-free 43 + 5 effective SQLite schema manifest."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from schema.catalog import MANIFEST_PATH, build_legacy_manifest, render_manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Recompute Dream schema metadata in memory; no business rows are read.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="fail when the checked-in manifest differs from the effective builders",
    )
    mode.add_argument(
        "--output",
        type=Path,
        help="write the deterministic manifest to an explicit path",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    rendered = render_manifest(build_legacy_manifest())
    if arguments.check:
        if not MANIFEST_PATH.exists():
            raise SystemExit(f"schema manifest is missing: {MANIFEST_PATH}")
        if MANIFEST_PATH.read_text(encoding="utf-8") != rendered:
            raise SystemExit(
                "effective SQLite schema differs from legacy_schema_manifest.json.gz.b64; "
                "review the structural diff before regenerating"
            )
        print("legacy schema manifest: OK (43/522 + 5/45 = 48/567)")
        return 0
    if arguments.output:
        arguments.output.write_text(rendered, encoding="utf-8")
        print(f"wrote data-free schema manifest: {arguments.output}")
        return 0
    sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
