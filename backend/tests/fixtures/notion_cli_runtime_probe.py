#!/usr/bin/env python3
"""Run one provider-free ntn command through the real Dream SDK/Runtime path.

[Input] Installed production-qualified Dream SDK/Runtime plus local fake provider and ntn fixtures.
[Output] A content-free JSON receipt proving the PreToolUse decision and Bash result.
[Pos] Opt-in compiled Runtime contract probe; it never contacts Notion or a real model.
[Sync] 2026-09-04: add the regression probe for actor-bound read-only ntn auto execution.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from threading import Thread
from uuid import uuid4

from http.server import ThreadingHTTPServer

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from claude_agent_sandbox_fake_provider import _Handler  # noqa: E402
from libs.claude_agent_kit.server.agent_runner import ClaudeAgentRunner  # noqa: E402
from libs.claude_agent_kit.server.workspace import get_or_create_workspace  # noqa: E402
from libs.claude_agent_kit.types import (  # noqa: E402
    AgentRunOptions,
    AgentStreamingCallbacks,
)


_COMMAND = 'ntn api v1/search --data \'{"query":"policy-probe","page_size":1}\''


async def _probe(
    provider_url: str,
    workspace: Path,
    *,
    thread_id: str,
) -> dict[str, object]:
    notion_home = workspace / ".notion-home"
    notion_home.mkdir(mode=0o700)
    auth_path = notion_home / "auth.json"
    auth_path.write_text(
        json.dumps({"workspace-probe": "synthetic-probe-token"}),
        encoding="utf-8",
    )
    auth_path.chmod(0o600)
    config_path = notion_home / "config.json"
    config_path.write_text(
        json.dumps({"defaultWorkspaceIds": {"prod": "workspace-probe"}}),
        encoding="utf-8",
    )
    config_path.chmod(0o600)
    fixture_bin = workspace / "fixture-bin"
    fixture_bin.mkdir()
    fake_ntn = fixture_bin / "ntn"
    shutil.copy2(Path(__file__).with_name("ntn"), fake_ntn)
    fake_ntn.chmod(0o700)

    tool_receipts: list[dict[str, object]] = []
    errors: list[str] = []

    def on_tool_event(payload: object) -> None:
        if getattr(payload, "type", None) != "tool_result":
            return
        tool_receipts.append(
            {
                "tool_name": getattr(payload, "tool_name", None),
                "state": getattr(payload, "state", None),
                "is_error": getattr(payload, "is_error", None),
                "output": getattr(payload, "output", None),
            }
        )

    def on_error(error: Exception) -> None:
        errors.append(type(error).__name__)

    process_overrides = {
        "PATH": f"{fixture_bin}{os.pathsep}{os.environ.get('PATH', '')}",
        "INK_GATEWAY_ENABLED": "0",
        "ANTHROPIC_BASE_URL": provider_url,
        "ANTHROPIC_AUTH_TOKEN": "synthetic-provider-token",
        "ANTHROPIC_MODEL": "claude-notion-policy-probe",
    }
    previous_values = {name: os.environ.get(name) for name in process_overrides}
    os.environ.update(process_overrides)
    try:
        result = await ClaudeAgentRunner().run_streaming(
            AgentRunOptions(
                thread_id=thread_id,
                user_message="provider-free permission probe",
                cwd=str(workspace),
                claude_tmp_workspace=str(workspace),
                notion_credential_home=str(notion_home),
                tool_choice="auto",
            ),
            AgentStreamingCallbacks(
                on_text_delta=lambda _delta: None,
                on_tool_event=on_tool_event,
                on_error=on_error,
            ),
        )
    finally:
        for name, previous_value in previous_values.items():
            if previous_value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = previous_value

    bash_receipts = [item for item in tool_receipts if item["tool_name"] == "Bash"]
    passed = bool(
        result.success
        and result.protocol_completed
        and result.full_text == "sandbox probe complete"
        and len(bash_receipts) == 1
        and bash_receipts[0]["state"] == "output-available"
        and bash_receipts[0]["is_error"] is False
        and "fake-ntn-read-ok" in str(bash_receipts[0]["output"])
        and not errors
    )
    return {
        "passed": passed,
        "runtime_result": {
            "success": result.success,
            "protocol_completed": result.protocol_completed,
            "terminal_stop_reason": result.terminal_stop_reason,
        },
        "bash": [
            {
                "state": item["state"],
                "is_error": item["is_error"],
                "content_free_marker": "fake-ntn-read-ok" in str(item["output"]),
            }
            for item in bash_receipts
        ],
        "error_types": errors,
    }


def main() -> int:
    _Handler.request_number = 0
    _Handler.command = _COMMAND
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        provider_url = f"http://127.0.0.1:{server.server_address[1]}"
        with tempfile.TemporaryDirectory(prefix="ink-notion-runtime-probe-") as root:
            previous_agent_cwd = os.environ.get("AGENT_CWD")
            os.environ["AGENT_CWD"] = root
            try:
                thread_id = str(uuid4())
                workspace = get_or_create_workspace(
                    thread_id,
                    sandbox_enabled=False,
                )
                receipt = asyncio.run(
                    _probe(provider_url, workspace, thread_id=thread_id)
                )
            finally:
                if previous_agent_cwd is None:
                    os.environ.pop("AGENT_CWD", None)
                else:
                    os.environ["AGENT_CWD"] = previous_agent_cwd
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
