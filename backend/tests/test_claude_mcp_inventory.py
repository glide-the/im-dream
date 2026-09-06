"""Standard-SDK transport policy tests for managed MCP discovery.

[Input] Provider-free stdio profile JSON, local standard MCP fixtures, and endpoint/profile policy values.
[Output] Loopback/non-global URL classification, no-redirect HTTP, real cursor pagination, and no legacy Agent/CLI path.
[Pos] Small transport-factory contract complementing managed discovery orchestration tests.
[Sync] 2026-08-25: retire Agent-runtime polling coverage after direct MCP SDK migration.
[Sync] 2026-08-25: verify real standard-MCP nextCursor pagination over one managed stdio connection.
[Sync] 2026-09-06: cover explicit loopback HTTP discovery while preserving other non-global and redirect denials.
[Sync] 2026-09-06: preserve only normalized descriptor-owned MCP App resource metadata.
"""

from __future__ import annotations

import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import inspect
import json
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from claude_mcp.inventory import (
    McpDiscoveryCoordinator,
    McpDiscoveryPolicy,
    McpSdkSessionFactory,
    StdioProfileResolver,
    _mcp_app_tool_metadata,
    _validate_remote_url,
)
from claude_mcp.contracts import McpAuthKind, McpTransport
from claude_mcp.repository import McpServerRecord


class _Repository:
    def __init__(self, server: McpServerRecord) -> None:
        self.server = server

    async def get_server(self, actor_id, server_id, workspace_id=None):
        del workspace_id
        if actor_id == self.server.user_id and server_id == self.server.id:
            return self.server
        return None

    async def get_discovery_snapshot(self, actor_id, server):
        del actor_id, server
        return None

    async def save_discovery_snapshot(
        self, actor_id, server, result, ttl_seconds=None
    ):
        del actor_id, server, result, ttl_seconds


def _remote_server(url: str) -> McpServerRecord:
    return McpServerRecord(
        id="server-loopback",
        user_id="7",
        workspace_id=None,
        scope="user",
        server_key="loopback",
        display_name="Loopback",
        transport=McpTransport.STREAMABLE_HTTP,
        remote_url=url,
        stdio_profile_key=None,
        auth_kind=McpAuthKind.NONE,
        enabled=True,
        config_revision=1,
        credential_revision=0,
        credential_id=None,
        credential_configured=False,
        created_at="2026-09-06T00:00:00+00:00",
        updated_at="2026-09-06T00:00:00+00:00",
    )


def _policy() -> McpDiscoveryPolicy:
    return McpDiscoveryPolicy(
        max_parallel_servers=1,
        server_timeout_seconds=10,
        item_timeout_seconds=5,
        max_inventory_items=20,
        max_inventory_pages=4,
        max_text_length=200,
    )


def _session_factory() -> McpSdkSessionFactory:
    return McpSdkSessionFactory(
        stdio_profiles=StdioProfileResolver.from_json("{}"),
        connect_timeout_seconds=5,
        read_timeout_seconds=5,
    )


def _reserve_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _wait_for_listener(process: subprocess.Popen[str], port: int) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stderr = process.stderr.read() if process.stderr else ""
            raise AssertionError(f"Streamable HTTP fixture exited early: {stderr[-1000:]}")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.1)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.02)
    raise AssertionError("Streamable HTTP fixture did not become ready")


def _stop_fixture(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def test_stdio_profiles_require_server_owned_absolute_executable() -> None:
    resolver = StdioProfileResolver.from_json(
        '{"safe":{"command":"/usr/bin/true","args":["--safe"],"env":{"A":"1"}}}'
    )
    assert resolver.resolve("safe").command == "/usr/bin/true"
    with pytest.raises(ValueError):
        StdioProfileResolver.from_json(
            '{"unsafe":{"command":"sh","args":[],"env":{}}}'
        )
    with pytest.raises(ValueError):
        resolver.resolve("browser-supplied")


def test_direct_sdk_factory_contains_no_agent_runtime_or_cli_inventory_path() -> None:
    source = inspect.getsource(McpSdkSessionFactory)
    assert "ClientSession" in source
    assert "ClaudeSDKClient" not in source
    assert "ClaudeMcpCliDriver" not in source
    assert "create_subprocess_exec" not in source


def test_mcp_app_tool_metadata_normalizes_descriptor_resource_uri_only() -> None:
    descriptor = SimpleNamespace(meta={
        "ui": {"resourceUri": "ui://get-time/mcp-app.html"},
        "ui/resourceUri": "ui://get-time/mcp-app.html",
        "private": {"token": "must-not-survive"},
    })

    assert _mcp_app_tool_metadata(descriptor, 200) == {
        "ui": {"resourceUri": "ui://get-time/mcp-app.html"}
    }
    descriptor.meta["ui/resourceUri"] = "ui://other/app.html"
    assert _mcp_app_tool_metadata(descriptor, 200) is None


@pytest.mark.parametrize(
    "url",
    (
        "http://127.0.0.1:3001/mcp",
        "http://127.255.255.254:3001/mcp",
        "http://[::1]:3001/mcp",
        "https://8.8.8.8/mcp",
    ),
)
def test_remote_url_policy_allows_explicit_global_and_loopback_ips(url: str) -> None:
    assert _validate_remote_url(url) == url


@pytest.mark.parametrize(
    "url",
    (
        "http://10.0.0.1:3001/mcp",
        "http://172.16.0.1:3001/mcp",
        "http://192.168.0.1:3001/mcp",
        "http://169.254.169.254/mcp",
        "http://0.0.0.0:3001/mcp",
        "http://224.0.0.1:3001/mcp",
        "http://240.0.0.1:3001/mcp",
        "http://[::]:3001/mcp",
        "http://[fc00::1]:3001/mcp",
        "http://[fe80::1]:3001/mcp",
        "http://[ff02::1]:3001/mcp",
        "http://user@127.0.0.1:3001/mcp",
        "http://127.0.0.1:3001/mcp?target=other",
        "http://127.0.0.1:3001/mcp#other",
    ),
)
def test_remote_url_policy_keeps_other_non_global_and_shape_denials(url: str) -> None:
    with pytest.raises(ValueError, match="denied"):
        _validate_remote_url(url)


def test_explicit_loopback_streamable_http_discovers_real_inventory() -> None:
    fixture = Path(__file__).parent / "fixtures" / "claude_mcp_inventory_server.py"
    port = _reserve_loopback_port()
    process = subprocess.Popen(
        [
            sys.executable,
            str(fixture),
            "--transport",
            "streamable-http",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=fixture.parent,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for_listener(process, port)

        async def scenario() -> None:
            server = _remote_server(f"http://127.0.0.1:{port}/mcp")
            result = await McpDiscoveryCoordinator(
                _Repository(server),
                _session_factory(),
                policy=_policy(),
            ).discover_one("7", server.id, force=True)
            assert result.status.value == "complete"
            assert [item["name"] for item in result.tools] == [
                "read_transport_status"
            ]
            assert [item["name"] for item in result.resources] == [
                "transport_status"
            ]
            assert [item["name"] for item in result.prompts] == [
                "summarize_transport_status"
            ]

        asyncio.run(scenario())
    finally:
        _stop_fixture(process)


def test_loopback_streamable_http_does_not_follow_redirects() -> None:
    redirected_requests = 0

    class RedirectTarget(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
            nonlocal redirected_requests
            redirected_requests += 1
            self.send_response(204)
            self.end_headers()

        do_POST = do_GET

        def log_message(self, _format: str, *_args: object) -> None:
            return None

    target = ThreadingHTTPServer(("127.0.0.1", 0), RedirectTarget)
    target_port = int(target.server_address[1])

    class RedirectSource(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
            self.send_response(307)
            self.send_header("Location", f"http://127.0.0.1:{target_port}/denied")
            self.end_headers()

        do_POST = do_GET

        def log_message(self, _format: str, *_args: object) -> None:
            return None

    source = ThreadingHTTPServer(("127.0.0.1", 0), RedirectSource)
    source_port = int(source.server_address[1])
    target_thread = threading.Thread(target=target.serve_forever, daemon=True)
    source_thread = threading.Thread(target=source.serve_forever, daemon=True)
    target_thread.start()
    source_thread.start()
    try:
        async def scenario() -> None:
            server = _remote_server(f"http://127.0.0.1:{source_port}/mcp")
            result = await McpDiscoveryCoordinator(
                _Repository(server),
                _session_factory(),
                policy=_policy(),
            ).discover_one("7", server.id, force=True)
            assert result.status.value == "failed"
            assert result.error is not None
            assert result.error.code == "CLAUDE_MCP_PROTOCOL_ERROR"

        asyncio.run(scenario())
        assert redirected_requests == 0
    finally:
        source.shutdown()
        target.shutdown()
        source.server_close()
        target.server_close()
        source_thread.join(timeout=5)
        target_thread.join(timeout=5)
        assert not source_thread.is_alive()
        assert not target_thread.is_alive()


def test_standard_stdio_server_exhausts_real_inventory_cursors() -> None:
    async def scenario() -> None:
        fixture = Path(__file__).parent / "fixtures" / "claude_mcp_inventory_server.py"
        resolver = StdioProfileResolver.from_json(json.dumps({
            "paginated": {
                "command": sys.executable,
                "args": [str(fixture), "--transport", "stdio", "--paginated"],
                "env": {},
                "cwd": str(fixture.parent),
            }
        }))
        server = McpServerRecord(
            id="server-paginated",
            user_id="7",
            workspace_id=None,
            scope="user",
            server_key="paginated",
            display_name="Paginated",
            transport=McpTransport.STDIO,
            remote_url=None,
            stdio_profile_key="paginated",
            auth_kind=McpAuthKind.NONE,
            enabled=True,
            config_revision=1,
            credential_revision=0,
            credential_id=None,
            credential_configured=False,
            created_at="2026-08-25T00:00:00+00:00",
            updated_at="2026-08-25T00:00:00+00:00",
        )
        result = await McpDiscoveryCoordinator(
            _Repository(server),
            McpSdkSessionFactory(
                stdio_profiles=resolver,
                connect_timeout_seconds=5,
                read_timeout_seconds=5,
            ),
            policy=McpDiscoveryPolicy(
                max_parallel_servers=1,
                server_timeout_seconds=10,
                item_timeout_seconds=5,
                max_inventory_items=20,
                max_inventory_pages=4,
                max_text_length=200,
            ),
        ).discover_one("7", server.id, force=True)
        assert result.status.value == "complete"
        assert [item["name"] for item in result.tools] == [
            "read_transport_status", "read_transport_version"
        ]
        assert [item["name"] for item in result.resources] == [
            "transport_status", "transport_version"
        ]
        assert [item["name"] for item in result.prompts] == [
            "summarize_transport_status", "summarize_transport_version"
        ]
        assert result.truncated is False

    asyncio.run(scenario())
