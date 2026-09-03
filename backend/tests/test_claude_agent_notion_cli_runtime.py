# [Input] Production ClaudeAgentRunner, manifest-qualified Dream Runtime, local fake Provider, and a workspace-local fake ntn executable.
# [Output] Process-isolated provider-free proof that an approved actor-bound notion-cli Bash call executes inside the real Runtime and sandbox.
# [Pos] Integration contract test node in backend/tests; no real Notion credential or content is accessed.
# [Sync] 2026-09-04: add the Dream notion-cli PreToolUse regression acceptance.

from __future__ import annotations

import asyncio
import json
import os
import stat
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

_NTN_COMMAND = 'ntn api v1/search --data \'{"query":"fixture-only","page_size":1}\''


def _run_contract(tmp_path: Path) -> None:
    from libs.claude_agent_kit import (
        AgentRunOptions,
        AgentRunResult,
        AgentStreamingCallbacks,
    )
    from libs.claude_agent_kit.server.agent_runner import ClaudeAgentRunner
    from libs.claude_agent_kit.server.sdk_env import resolve_claude_cli_path
    from libs.claude_agent_kit.server.workspace import (
        init_workspace,
        sync_builtin_workspace_skills,
    )
    from tests.fixtures.claude_agent_sandbox_fake_provider import build_handler

    try:
        runtime_path = resolve_claude_cli_path()
    except (OSError, RuntimeError) as exc:  # pragma: no cover - installation state
        raise SystemExit(f"Dream Runtime unavailable: {exc}") from exc
    if runtime_path is None:  # pragma: no cover - external installation state
        raise SystemExit("Dream Runtime unavailable")

    requests_seen: list[dict[str, Any]] = []
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        build_handler(
            command=_NTN_COMMAND,
            final_text="fake ntn contract complete",
            requests_seen=requests_seen,
            announce_requests=False,
        ),
    )
    server.daemon_threads = True
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        os.environ["AGENT_CWD"] = str(tmp_path / "workspaces")
        os.environ["INK_GATEWAY_ENABLED"] = "0"
        os.environ["INK_GATEWAY_CLAUDE_AGENT_ENABLED"] = "0"
        os.environ["ANTHROPIC_API_KEY"] = ""
        os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = ""
        os.environ["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
        provider_url = f"http://127.0.0.1:{server.server_port}"
        os.environ["ANTHROPIC_BASE_URL"] = provider_url
        os.environ["ANTHROPIC_AUTH_TOKEN"] = "fixture-provider-token"

        workspace = init_workspace(
            "thread-ntn-contract",
            sandbox_enabled=True,
            sandbox_network_mode="allowlist",
        )
        (workspace / ".dream").mkdir(exist_ok=True)
        sync_builtin_workspace_skills(workspace, enabled_platforms={"notion"})

        fake_bin = workspace / "fake-bin"
        fake_bin.mkdir()
        fake_ntn = fake_bin / "ntn"
        fake_ntn.write_text(
            "#!/bin/sh\nprintf '%s\\n' '{\"fake_ntn\":\"ok\"}'\n",
            encoding="utf-8",
        )
        fake_ntn.chmod(fake_ntn.stat().st_mode | stat.S_IXUSR)
        os.environ["PATH"] = f"{fake_bin}{os.pathsep}{os.environ['PATH']}"

        notion_home = workspace / ".notion-home"
        notion_home.mkdir(mode=0o700)
        notion_auth = notion_home / "auth.json"
        notion_auth.write_text(
            '{"access_token":"fixture-notion-token"}',
            encoding="utf-8",
        )
        notion_auth.chmod(0o600)

        confirmations: list[dict[str, Any]] = []
        errors: list[str] = []

        async def confirm(payload: dict[str, Any]) -> dict[str, bool]:
            confirmations.append(payload)
            return {"approved": True}

        async def run() -> AgentRunResult:
            return await ClaudeAgentRunner().run_streaming(
                AgentRunOptions(
                    thread_id="thread-ntn-contract",
                    user_message="run the provider-forced fixture",
                    cwd=str(workspace),
                    claude_tmp_workspace=str(workspace),
                    notion_credential_home=str(notion_home),
                    tool_choice="auto",
                    max_turns=3,
                    user_sdk_env={
                        "ANTHROPIC_BASE_URL": provider_url,
                        "ANTHROPIC_AUTH_TOKEN": "fixture-provider-token",
                    },
                ),
                AgentStreamingCallbacks(
                    on_text_delta=lambda _delta: None,
                    on_tool_confirmation_request=confirm,
                    on_error=lambda exc: errors.append(str(exc)),
                ),
            )

        result = asyncio.run(run())
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)

    assert result.success is True
    assert result.full_text == "fake ntn contract complete"
    assert errors == []
    assert [item["input"]["command"] for item in confirmations] == [_NTN_COMMAND]
    assert (workspace / ".claude" / "skills" / "notion-cli").exists()
    settings = json.loads((workspace / ".claude" / "settings.json").read_text())
    assert settings["sandbox"]["enabled"] is True
    tool_results = [
        item.get("content")
        for request in requests_seen
        for message in request.get("messages", [])
        if isinstance(message, dict)
        for item in (
            message.get("content") if isinstance(message.get("content"), list) else []
        )
        if isinstance(item, dict) and item.get("type") == "tool_result"
    ]
    assert any(
        isinstance(content, str) and '{"fake_ntn":"ok"}' in content
        for content in tool_results
    )


def test_real_runtime_executes_approved_fake_ntn_without_notion_access(
    tmp_path: Path,
) -> None:
    """Use a clean process so SDK stubs from unit-test collection cannot leak."""

    completed = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), str(tmp_path)],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if completed.returncode == 77:
        pytest.skip(completed.stderr.strip() or "Dream Runtime unavailable")
    assert completed.returncode == 0, completed.stdout + completed.stderr


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    try:
        _run_contract(Path(sys.argv[1]))
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(77) from exc
