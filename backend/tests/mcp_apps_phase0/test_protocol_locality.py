# [Input] The named Node phase0-standard-apps-fixture and exact frontend dependency tree.
# [Output] Verify stdio, proxied/local HTTP, Node-reachable SSE, and fresh upstream-session portability.
# [Pos] Provider-free Phase 0 protocol/locality contract test; no production service or data is used.
# [Sync] 2026-09-04: cover P0-02/P0-05/P0-06 through the task-specified fixture entry.

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = (
    ROOT
    / "backend"
    / "tests"
    / "fixtures"
    / "mcp_apps_phase0"
    / "phase0_standard_apps_fixture.py"
)


def test_standard_transports_and_fresh_session_portability() -> None:
    completed = subprocess.run(
        [sys.executable, str(FIXTURE), "--probe-all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    evidence = json.loads(completed.stdout)

    for transport in (
        "stdio",
        "localhostStreamableHttp",
        "freshSessionStreamableHttp",
        "freshNodeUpstreamSession",
        "nodeReachableLegacySse",
    ):
        assert evidence[transport] == {
            "toolNames": ["phase0_show_shared_state"],
            "resourceUri": "ui://phase0-standard-apps-fixture/view.html",
            "resourceMimeType": "text/html;profile=mcp-app",
            "resourceStateIncluded": True,
        }

    assert int(evidence["nodeVersion"].removeprefix("v").split(".", 1)[0]) >= 20
    assert evidence["sharedStateVisibleAcrossSessions"] is True
    assert evidence["userDeviceStdio"] == (
        "excluded-node-cannot-start-process-on-user-device"
    )
