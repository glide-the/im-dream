# [Input] Production ClaudeAgentRunner, manifest-qualified Dream Runtime, local fake Provider, and a test-owned native ntn executable outside the workspace.
# [Output] Process-isolated provider-free proof that an approved actor-bound notion-cli Bash call executes inside the real Runtime and sandbox.
# [Pos] Integration contract test node in backend/tests; no real Notion credential or content is accessed.
# [Sync] 2026-09-04: add the Dream notion-cli PreToolUse regression acceptance.
# [Sync] 2026-09-13: compile the fixture to match Runtime 0.1.9 native ntn policy without allowing shell-script shadows.
# [Sync] 2026-09-13: assert final Bash binding and real config file readability.

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

_NTN_COMMAND = 'ntn api v1/search --data \'{"query":"fixture-only","page_size":1}\''


def _run_contract(tmp_path: Path, *, installed_cli: bool = False, relative_shadow: bool = False) -> None:
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

    command = _NTN_COMMAND
    requests_seen: list[dict[str, Any]] = []
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        build_handler(
            command=command,
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

        fake_bin = tmp_path / "native-notion-bin"
        fake_bin.mkdir()
        fake_ntn = fake_bin / "ntn"
        subprocess.run(
            ["cc", str(Path(__file__).with_name("fixtures") / "notion_cli_native.c"),
             "-o", str(fake_ntn)],
            check=True,
            capture_output=True,
            text=True,
        )
        fake_ntn.chmod(0o755)
        if installed_cli:
            if not shutil.which("ntn"):
                raise SystemExit("Installed ntn unavailable")
        else:
            os.environ["PATH"] = f"{fake_bin}{os.pathsep}{os.environ['PATH']}"
        if relative_shadow:
            (workspace / "relative-bin").mkdir()
            os.environ["PATH"] = "relative-bin" + os.pathsep + os.environ["PATH"]

        notion_home = workspace / ".notion-home"
        notion_home.mkdir(mode=0o700)
        notion_auth = notion_home / "auth.json"
        notion_auth.write_text(
            '{}' if installed_cli else '{"access_token":"fixture-notion-token"}',
            encoding="utf-8",
        )
        notion_auth.chmod(0o600)
        notion_config = notion_home / "config.json"
        notion_config.write_text('{"version":"0.15.1","defaultWorkspaceIds":{}}')
        notion_config.chmod(0o600)

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
    assert [item["input"]["command"] for item in confirmations if "command" in item.get("input", {})] == [command], confirmations
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
    expected = "No workspace selected" if installed_cli else '{"fake_ntn":"ok"}'
    if relative_shadow:
        expected = "fixture binding unavailable"
    assert any(
        isinstance(content, str) and expected in content
        for content in tool_results
    ), tool_results


@pytest.mark.parametrize("installed_cli,relative_shadow", [(False, False), (True, False), (False, True)], ids=["native-fixture", "installed-ntn-config", "relative-shadow-denied"])
def test_real_runtime_executes_approved_fake_ntn_without_notion_access(
    tmp_path: Path, installed_cli: bool, relative_shadow: bool,
) -> None:
    """Use a clean process so SDK stubs from unit-test collection cannot leak."""

    completed = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), str(tmp_path), str(int(installed_cli)), str(int(relative_shadow))],
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
        _run_contract(Path(sys.argv[1]), installed_cli=len(sys.argv) > 2 and sys.argv[2] == "1", relative_shadow=len(sys.argv) > 3 and sys.argv[3] == "1")
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(77) from exc
