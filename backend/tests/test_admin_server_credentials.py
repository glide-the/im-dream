# [Input] Production SDK merge/user-overlay and MCP config/env projection with synthetic server secrets.
# [Output] Evidence that Admin/Auth secrets stay on the server across parent and explicit child overlays.
# [Pos] Provider-free credential boundary contracts; no real values, SDK query, DB or model calls.
# [Sync] 2026-09-14: cover repeated merge, parent preservation and internal/external stdio config.

from __future__ import annotations

import json
import os
from types import SimpleNamespace
from unittest import mock

import tests._sdk_stubs  # noqa: F401
from libs.claude_agent_kit.server.sdk_env import (
    ADMIN_AUTH_SERVER_ONLY_ENV_NAMES,
    apply_user_sdk_env_to_options, merge_project_dotenv_env,
)
from libs.claude_agent_kit.server.agent_runner import (
    _mcp_server_config_json_value, _stdio_env, _write_mcp_config_projection,
)


def secrets():
    return {key: "synthetic-private-value" for key in ADMIN_AUTH_SERVER_ONLY_ENV_NAMES}


def test_final_sdk_merge_tombstones_parent_and_existing_server_secrets(tmp_path):
    environment = {**secrets(), "PATH": "/usr/bin", "INK_ADMIN_DREAM_SERVICE_CLIENT_ID": "dream-web"}
    dotenv = tmp_path / "runtime.env"
    dotenv.write_text("INK_ADMIN_DREAM_SERVICE_SECRET=synthetic-dotenv-private\nAPI_TIMEOUT_MS=900\n")
    with mock.patch.dict(os.environ, environment, clear=True):
        overlay = merge_project_dotenv_env({**secrets(), "API_TIMEOUT_MS": "1200"}, dotenv)
        overlay = merge_project_dotenv_env(overlay, dotenv)
        assert all(overlay[key] == "" for key in ADMIN_AUTH_SERVER_ONLY_ENV_NAMES)
        assert overlay["API_TIMEOUT_MS"] == "1200"
        assert os.environ["INK_ADMIN_DREAM_SERVICE_SECRET"] == environment["INK_ADMIN_DREAM_SERVICE_SECRET"]
        child_environment = {**os.environ, **overlay}
        assert all(not child_environment[key] for key in ADMIN_AUTH_SERVER_ONLY_ENV_NAMES)
        assert child_environment["PATH"] == "/usr/bin"
        assert child_environment["INK_ADMIN_DREAM_SERVICE_CLIENT_ID"] == "dream-web"


def test_user_overlay_cannot_restore_admin_auth_secrets():
    options = SimpleNamespace(env={**secrets(), "API_TIMEOUT_MS": "900"})
    apply_user_sdk_env_to_options(options, {**secrets(), "API_TIMEOUT_MS": "1200"})
    assert all(options.env[key] == "" for key in ADMIN_AUTH_SERVER_ONLY_ENV_NAMES)
    assert options.env["API_TIMEOUT_MS"] == "1200"


def test_stdio_explicit_env_does_not_restore_server_secrets():
    result = _stdio_env(extra_env={**secrets(), "INK_AGENT_THREAD_ID": "owned-thread"})
    assert not set(result).intersection(ADMIN_AUTH_SERVER_ONLY_ENV_NAMES)
    assert result["INK_AGENT_THREAD_ID"] == "owned-thread"


def test_external_mcp_projection_removes_secrets_without_mutating_source(tmp_path):
    original = {"type": "stdio", "command": "synthetic-tool", "args": [], "env": {**secrets(), "INK_AGENT_THREAD_ID": "owned-thread"}}
    projected = _mcp_server_config_json_value(original)
    assert set(projected["env"]) == {"INK_AGENT_THREAD_ID"}
    assert original["env"] == {**secrets(), "INK_AGENT_THREAD_ID": "owned-thread"}
    workspace = tmp_path / "owned-thread"
    workspace.mkdir()
    path = _write_mcp_config_projection({"external": original}, thread_workspace=str(workspace))
    written = json.loads(path.read_text())
    assert written["mcpServers"]["external"]["env"] == {"INK_AGENT_THREAD_ID": "owned-thread"}
    assert "synthetic-private-value" not in path.read_text()
    assert path.parent.parent == workspace / ".claude-tmp"
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.parent.stat().st_mode & 0o777 == 0o700
