#!/usr/bin/env python3
"""Deterministic fake Claude MCP CLI for isolated argv/PTTY contract tests.

[Input] Claude-compatible argv plus test-only environment paths and behavior flags.
[Output] Bounded status/auth/failure and management/login terminal behavior without a real OAuth provider.
[Pos] Explicit test fixture; never imported or selected by production code.
[Sync] 2026-08-19: cover official headless OAuth stdin and lifecycle branches.
[Sync] 2026-08-19: cover restricted user-scope HTTP add/remove argv.
[Sync] 2026-08-20: emulate direct browser-callback completion before stdin submission.
[Sync] 2026-08-20: capture non-secret config/secure-storage selectors for identity tests.
[Sync] 2026-08-21: emit formal config scope for removal-authorization coverage.
[Sync] 2026-08-25: emulate stable Authentication/Failure-Code output and authless post-logout truth.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time


def _state_path() -> Path:
    return Path(os.environ["CLAUDE_MCP_FAKE_STATE_PATH"])


def _read_state() -> str:
    path = _state_path()
    return (
        path.read_text(encoding="utf-8").strip()
        if path.exists()
        else os.environ.get("CLAUDE_MCP_FAKE_DEFAULT_STATE", "needs_auth")
    )


def _write_state(value: str) -> None:
    _state_path().write_text(value, encoding="utf-8")


def _record_argv() -> None:
    target = os.environ.get("CLAUDE_MCP_FAKE_ARGV_PATH")
    if target:
        Path(target).write_text(json.dumps(sys.argv[1:]), encoding="utf-8")


def _record_identity_env() -> None:
    target = os.environ.get("CLAUDE_MCP_FAKE_IDENTITY_ENV_PATH")
    if target:
        Path(target).write_text(
            json.dumps(
                {
                    "CLAUDE_CONFIG_DIR": os.environ.get("CLAUDE_CONFIG_DIR"),
                    "CLAUDE_SECURESTORAGE_CONFIG_DIR": os.environ.get(
                        "CLAUDE_SECURESTORAGE_CONFIG_DIR"
                    ),
                }
            ),
            encoding="utf-8",
        )


def _named_path(env_name: str) -> Path | None:
    value = os.environ.get(env_name)
    return Path(value) if value else None


def _authentication_for_state(state: str) -> str:
    explicit = os.environ.get("CLAUDE_MCP_FAKE_AUTH_STATE")
    if explicit:
        return explicit
    return {
        "connected": "authenticated",
        "needs_auth": "required",
        "logged_out": "required",
    }.get(state, "unknown")


def _status_label(state: str) -> str:
    return {
        "connected": "✓ Connected",
        "needs_auth": "Needs authentication",
        "failed": "Failed",
        "unavailable": "Unavailable",
        "forbidden": "Forbidden",
        "configured": "Configured",
        "logged_out": "Logged out",
        "disabled": "Disabled",
    }.get(state, "Unknown future state")


def _emit_server_status(server_name: str) -> None:
    state = _read_state()
    print(f"{server_name}\nStatus: {_status_label(state)}", flush=True)
    if os.environ.get("CLAUDE_MCP_FAKE_LEGACY_OUTPUT") != "1":
        print(f"Authentication: {_authentication_for_state(state)}", flush=True)
        failure_code = os.environ.get("CLAUDE_MCP_FAKE_FAILURE_CODE")
        if failure_code:
            print(f"Failure-Code: {failure_code}", flush=True)
    transport_label = (
        "Type" if os.environ.get("CLAUDE_MCP_FAKE_LEGACY_OUTPUT") == "1" else "Transport"
    )
    print(
        f"{transport_label}: {os.environ.get('CLAUDE_MCP_FAKE_TRANSPORT', 'http')}",
        flush=True,
    )


def main() -> int:
    _record_argv()
    _record_identity_env()
    args = sys.argv[1:]
    version = os.environ.get("CLAUDE_MCP_FAKE_VERSION", "2.1.220")
    if args == ["--version"]:
        print(f"{version} (Claude Code)", flush=True)
        return 0
    if len(args) < 2 or args[0] != "mcp":
        print("unsupported fixture command", flush=True)
        return 64

    command = args[1]
    server_name = args[2] if len(args) > 2 else ""
    if command == "login" and args[2:] == ["--help"]:
        if os.environ.get("CLAUDE_MCP_FAKE_HIDE_NO_BROWSER") == "1":
            print("Usage: claude mcp login <name>", flush=True)
        else:
            print("Usage: claude mcp login <name> --no-browser", flush=True)
        return 0
    if command == "logout" and args[2:] == ["--help"]:
        print("Usage: claude mcp logout <name>", flush=True)
        return 0
    if command == "add" and args[2:] == ["--help"]:
        print("Usage: claude mcp add --transport http --scope user <name> <url>", flush=True)
        return 0
    if command == "remove" and args[2:] == ["--help"]:
        print("Usage: claude mcp remove --scope user <name>", flush=True)
        return 0
    if command == "list":
        status = _status_label(_read_state())
        print(f"plugin:comfy-cloud:comfy-cloud: https://mcp.example.test - {status}", flush=True)
        configured = _named_path("CLAUDE_MCP_FAKE_CONFIGURED_PATH")
        if configured and configured.exists():
            payload = json.loads(configured.read_text(encoding="utf-8"))
            print(f"{payload['name']}: {payload['url']} - {status}", flush=True)
        return 0
    if command == "get":
        removed = _named_path("CLAUDE_MCP_FAKE_REMOVED_PATH")
        if (
            os.environ.get("CLAUDE_MCP_FAKE_SERVER_MISSING") == "1"
            or (removed and removed.exists() and removed.read_text(encoding="utf-8") == server_name)
        ):
            print(f"No server found: {server_name}", flush=True)
            return 1
        _emit_server_status(server_name)
        scope = os.environ.get(
            "CLAUDE_MCP_FAKE_SCOPE",
            "plugin" if server_name.startswith("plugin:") else "user",
        )
        labels = {
            "user": "User config (available in all your projects)",
            "local": "Local config (private to this project)",
            "project": "Project config (shared via .mcp.json)",
            "plugin": "Plugin server",
        }
        print(f"Scope: {labels.get(scope, scope)}", flush=True)
        return 0
    if command == "logout":
        failure_code = os.environ.get("CLAUDE_MCP_FAKE_LOGOUT_FAILURE_CODE")
        if failure_code:
            print(f"Failure-Code: {failure_code}", flush=True)
            print("provider detail access_token=fixture-secret", flush=True)
            return 9
        _write_state(os.environ.get("CLAUDE_MCP_FAKE_LOGOUT_STATE", "needs_auth"))
        print(f"Logged out of {server_name}", flush=True)
        return 0
    if command == "add":
        expected_prefix = ["--transport", "http", "--scope", "user"]
        if args[2:6] != expected_prefix or len(args) != 8:
            print("invalid add argv", flush=True)
            return 64
        configured = _named_path("CLAUDE_MCP_FAKE_CONFIGURED_PATH")
        if configured:
            configured.write_text(
                json.dumps({"name": args[6], "url": args[7]}),
                encoding="utf-8",
            )
        removed = _named_path("CLAUDE_MCP_FAKE_REMOVED_PATH")
        if removed and removed.exists():
            removed.unlink()
        print(f"Added HTTP MCP server {args[6]} to user config", flush=True)
        return 0
    if command == "remove":
        if args[2:4] != ["--scope", "user"] or len(args) != 5:
            print("invalid remove argv", flush=True)
            return 64
        removed = _named_path("CLAUDE_MCP_FAKE_REMOVED_PATH")
        if removed:
            removed.write_text(args[4], encoding="utf-8")
        print(f"Removed MCP server {args[4]}", flush=True)
        return 0
    if command != "login" or args[-1] != "--no-browser":
        print("unsupported fixture mcp command", flush=True)
        return 64

    behavior = os.environ.get("CLAUDE_MCP_FAKE_BEHAVIOR", "success")
    semantic_failures = {
        "auth_not_required": "auth_not_required",
        "auth_not_advertised": "auth_not_advertised",
        "metadata_invalid": "metadata_invalid",
        "network_unreachable": "network_unreachable",
        "server_rejected": "server_rejected",
        "semantic_timeout": "timeout",
        "process_exited": "process_exited",
    }
    if behavior in semantic_failures:
        print(f"Failure-Code: {semantic_failures[behavior]}", flush=True)
        print("provider detail refresh_token=fixture-secret", flush=True)
        return 9
    if behavior == "nonzero":
        print("provider failed with token=<redacted>", flush=True)
        return 9
    if behavior == "malformed":
        print("Waiting for browser authorization", flush=True)
        return 0
    if behavior == "exit0_authenticated":
        _write_state("connected")
        print("Already authenticated", flush=True)
        return 0

    print(
        "Open https://oauth.example.test/authorize?client_id=fake&state=session-secret",
        flush=True,
    )
    if behavior == "timeout":
        time.sleep(float(os.environ.get("CLAUDE_MCP_FAKE_SLEEP_SECONDS", "10")))
        return 0
    if behavior == "browser_callback":
        time.sleep(float(os.environ.get("CLAUDE_MCP_FAKE_CALLBACK_SECONDS", "0.05")))
        _write_state("connected")
        print("Browser callback complete", flush=True)
        return 0

    redirect_url = sys.stdin.readline().strip()
    capture_path = os.environ.get("CLAUDE_MCP_FAKE_REDIRECT_PATH")
    if capture_path:
        Path(capture_path).write_text(redirect_url, encoding="utf-8")
    if not redirect_url.startswith(("http://", "https://")):
        print("invalid redirect", flush=True)
        return 8
    _write_state("connected")
    print("Token exchange complete", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
