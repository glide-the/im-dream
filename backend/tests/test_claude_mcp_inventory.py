"""Static standard-SDK transport policy tests for managed MCP discovery.

[Input] Provider-free stdio profile JSON, the standard MCP fixture, and invalid endpoint/profile values.
[Output] Server-owned profile validation, real cursor pagination, and absence of legacy Agent/CLI inventory paths.
[Pos] Small transport-factory contract complementing managed discovery orchestration tests.
[Sync] 2026-08-25: retire Agent-runtime polling coverage after direct MCP SDK migration.
[Sync] 2026-08-25: verify real standard-MCP nextCursor pagination over one managed stdio connection.
"""

from __future__ import annotations

import asyncio
import inspect
import json
from pathlib import Path
import sys

import pytest

from claude_mcp.inventory import (
    McpDiscoveryCoordinator,
    McpDiscoveryPolicy,
    McpSdkSessionFactory,
    StdioProfileResolver,
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
