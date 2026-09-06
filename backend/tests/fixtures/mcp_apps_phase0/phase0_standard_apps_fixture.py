# [Input] A test-only CLI request plus the Node runtime available on PATH.
# [Output] Canonical Python entrypoint for the phase0-standard-apps-fixture Node implementation.
# [Pos] Task_301 compatibility wrapper; it launches only the colocated provider-free fixture.
# [Sync] 2026-09-04: expose the task-specified fixture entry without adding a production runtime path.

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


IMPLEMENTATION = Path(__file__).with_suffix(".mjs")


def fixture_command(arguments: list[str]) -> list[str]:
    """Resolve the colocated Node fixture without embedding a machine-specific path."""

    node = shutil.which("node")
    if node is None:
        raise RuntimeError("phase0-standard-apps-fixture requires Node on PATH")
    return [node, str(IMPLEMENTATION), *arguments]


def main() -> int:
    completed = subprocess.run(fixture_command(sys.argv[1:]), check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
