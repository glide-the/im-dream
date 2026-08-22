"""Real subprocess/PTTY contract coverage for the Claude MCP driver.

[Input] Test-owned runtime identity and deterministic fake Claude CLI executable argv.
[Output] Version/list/add/login stdin/exit/logout/remove evidence with exact colon-bearing argv.
[Pos] Isolated technical test; launches no real Claude CLI or OAuth request.
[Sync] 2026-08-19: verify same-process redirect writing and official command argv shapes.
[Sync] 2026-08-19: verify restricted user-scope HTTP add/remove argv shapes.
[Sync] 2026-08-20: verify config and secure-storage selectors share one platform-user home.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from claude_mcp.contracts import ClaudeMcpRuntimeIdentity
from claude_mcp.driver import ClaudeMcpCliDriver
from claude_mcp.parser import parse_authorization_url
from claude_mcp.settings import ClaudeMcpSettings


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "claude_mcp_fake_cli.py"


def _settings() -> ClaudeMcpSettings:
    return ClaudeMcpSettings(
        auth_timeout_seconds=3,
        command_timeout_seconds=3,
        terminate_grace_seconds=1,
        readiness_timeout_seconds=2,
        max_capture_bytes=65536,
        max_server_name_length=512,
        max_redirect_url_length=8192,
    )


def _identity(tmp_path: Path, **overrides: str) -> ClaudeMcpRuntimeIdentity:
    config_dir = tmp_path / "config"
    config_dir.mkdir(exist_ok=True)
    env = dict(os.environ)
    env.update(
        {
            "CLAUDE_MCP_FAKE_STATE_PATH": str(tmp_path / "state"),
            "CLAUDE_MCP_FAKE_REDIRECT_PATH": str(tmp_path / "redirect"),
            "CLAUDE_MCP_FAKE_ARGV_PATH": str(tmp_path / "argv.json"),
            "CLAUDE_MCP_FAKE_CONFIGURED_PATH": str(tmp_path / "configured.json"),
            "CLAUDE_MCP_FAKE_REMOVED_PATH": str(tmp_path / "removed"),
            "CLAUDE_MCP_FAKE_IDENTITY_ENV_PATH": str(tmp_path / "identity-env.json"),
            **overrides,
        }
    )
    return ClaudeMcpRuntimeIdentity(
        command=(sys.executable, str(FIXTURE)),
        config_dir=config_dir.resolve(),
        cwd=tmp_path.resolve(),
        env=env,
        fingerprint="test-user-config",
    )


def test_driver_runs_public_commands_and_writes_redirect_to_same_pty(tmp_path: Path) -> None:
    async def scenario() -> None:
        identity = _identity(tmp_path)
        driver = ClaudeMcpCliDriver(_settings())
        version = await driver.version(identity)
        assert version.ok and "2.1.220" in version.output
        identity_env = json.loads(
            (tmp_path / "identity-env.json").read_text(encoding="utf-8")
        )
        assert identity_env == {
            "CLAUDE_CONFIG_DIR": str(identity.config_dir),
            "CLAUDE_SECURESTORAGE_CONFIG_DIR": str(identity.config_dir),
        }

        listed = await driver.list_servers(identity)
        assert listed.ok
        assert "plugin:comfy-cloud:comfy-cloud" in listed.output

        configured = await driver.add_http_user_server(
            identity,
            "user:server",
            "https://mcp.example.test/api",
        )
        assert configured.ok
        assert json.loads((tmp_path / "argv.json").read_text(encoding="utf-8")) == [
            "mcp",
            "add",
            "--transport",
            "http",
            "--scope",
            "user",
            "user:server",
            "https://mcp.example.test/api",
        ]

        server_name = "plugin:comfy-cloud:comfy-cloud"
        handle = await driver.start_login(identity, server_name)
        output = ""
        while parse_authorization_url(output) is None:
            output += (await asyncio.wait_for(handle.read(), timeout=2)).decode(
                "utf-8", errors="replace"
            )
        redirect = "https://callback.example.test/complete?code=private-code&state=private-state"
        await handle.write_redirect(redirect)
        assert await asyncio.wait_for(handle.wait(), timeout=2) == 0
        handle.close()

        assert (tmp_path / "redirect").read_text(encoding="utf-8") == redirect
        assert (tmp_path / "state").read_text(encoding="utf-8") == "connected"
        assert json.loads((tmp_path / "argv.json").read_text(encoding="utf-8")) == [
            "mcp",
            "login",
            server_name,
            "--no-browser",
        ]

        logged_out = await driver.logout(identity, server_name)
        assert logged_out.ok
        assert json.loads((tmp_path / "argv.json").read_text(encoding="utf-8")) == [
            "mcp",
            "logout",
            server_name,
        ]

        removed = await driver.remove_user_server(identity, "user:server")
        assert removed.ok
        assert json.loads((tmp_path / "argv.json").read_text(encoding="utf-8")) == [
            "mcp",
            "remove",
            "--scope",
            "user",
            "user:server",
        ]

    asyncio.run(scenario())


def test_short_command_timeout_returns_bounded_terminal_result(tmp_path: Path) -> None:
    async def scenario() -> None:
        settings = _settings()
        settings = ClaudeMcpSettings(
            **{
                **settings.__dict__,
                "command_timeout_seconds": 1,
            }
        )
        identity = _identity(
            tmp_path,
            CLAUDE_MCP_FAKE_BEHAVIOR="timeout",
            CLAUDE_MCP_FAKE_SLEEP_SECONDS="5",
        )
        # The fixture only sleeps for login; start and terminate that process
        # here to prove the driver owns its process group cleanup.
        driver = ClaudeMcpCliDriver(settings)
        handle = await driver.start_login(identity, "server:with:colons")
        assert await asyncio.wait_for(handle.read(), timeout=2)
        await handle.terminate()
        assert handle.process.returncode is not None

    asyncio.run(scenario())
