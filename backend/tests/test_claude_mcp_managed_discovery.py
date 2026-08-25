"""Provider-free standard MCP discovery orchestration contracts.

[Input] In-memory Server records and fake MCP ClientSession-compatible factories.
[Output] Three-transport inventory, bounded concurrency, single-flight, cache, timeout, cancel, and partial-result evidence.
[Pos] Managed MCP discovery tests; no Agent SDK, CLI, subprocess, network, OAuth, or database.
[Sync] 2026-08-25: define the standard Python MCP SDK discovery contract.
[Sync] 2026-08-25: prove bounded pagination exhausts all three inventory capabilities on one connection.
[Sync] 2026-08-25: prove interactive OAuth bypasses ordinary single-flight timeout and remains directly cancellable.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
from types import SimpleNamespace

import pytest

from claude_mcp.contracts import McpAuthKind, McpTransport
from claude_mcp.inventory import (
    McpDiscoveryCoordinator,
    McpDiscoveryPolicy,
    McpTransportHttpError,
)
from claude_mcp.repository import McpServerRecord


def _server(index: int, transport: McpTransport = McpTransport.STREAMABLE_HTTP):
    return McpServerRecord(
        id=f"server-{index}",
        user_id="7",
        workspace_id=None,
        scope="user",
        server_key=f"server-{index}",
        display_name=f"Server {index}",
        transport=transport,
        remote_url=(None if transport is McpTransport.STDIO else f"https://mcp{index}.example.test/mcp"),
        stdio_profile_key=("profile" if transport is McpTransport.STDIO else None),
        auth_kind=McpAuthKind.NONE,
        enabled=True,
        config_revision=1,
        credential_revision=0,
        credential_id=None,
        credential_configured=False,
        created_at="2026-08-25T00:00:00+00:00",
        updated_at="2026-08-25T00:00:00+00:00",
    )


class _Repository:
    def __init__(self, servers):
        self.servers = {item.id: item for item in servers}
        self.snapshots = {}
        self.saved = []

    async def get_server(self, actor_id, server_id, workspace_id=None):
        item = self.servers.get(server_id)
        return item if item and item.user_id == actor_id else None

    async def get_discovery_snapshot(self, actor_id, server):
        return self.snapshots.get((actor_id, server.id, server.config_revision, server.credential_revision))

    async def save_discovery_snapshot(self, actor_id, server, result):
        self.saved.append((actor_id, server.id, result.status.value))
        self.snapshots[(actor_id, server.id, server.config_revision, server.credential_revision)] = result


class _Session:
    def __init__(self, factory, server, *, delay=0, error=None, capabilities=None):
        self.factory = factory
        self.server = server
        self.delay = delay
        self.error = error
        self.capabilities = capabilities or {"tools", "resources", "prompts"}
        self.called = []
        self.cursors = []

    async def initialize(self):
        self.factory.active += 1
        self.factory.max_active = max(self.factory.max_active, self.factory.active)
        try:
            if self.delay:
                await asyncio.sleep(self.delay)
            if self.error:
                raise self.error
            capabilities = SimpleNamespace(
                tools=(SimpleNamespace() if "tools" in self.capabilities else None),
                resources=(SimpleNamespace() if "resources" in self.capabilities else None),
                prompts=(SimpleNamespace() if "prompts" in self.capabilities else None),
            )
            return SimpleNamespace(
                serverInfo=SimpleNamespace(name="fake", version="1"),
                capabilities=capabilities,
            )
        finally:
            self.factory.active -= 1

    async def _list(self, kind, cursor):
        self.called.append(kind)
        self.cursors.append((kind, cursor))
        pages = self.factory.pages.get(self.server.id, {}).get(kind)
        if pages is not None:
            page_items, next_cursor = pages[cursor]
            return SimpleNamespace(**{kind: page_items, "nextCursor": next_cursor})
        defaults = {
            "tools": [SimpleNamespace(name="tool", description="safe", annotations=None)],
            "resources": [SimpleNamespace(uri="memory://resource", name="resource", description=None, mimeType="text/plain")],
            "prompts": [SimpleNamespace(name="prompt", description="safe", arguments=[])],
        }
        return SimpleNamespace(**{kind: defaults[kind], "nextCursor": None})

    async def list_tools(self, cursor=None):
        return await self._list("tools", cursor)

    async def list_resources(self, cursor=None):
        return await self._list("resources", cursor)

    async def list_prompts(self, cursor=None):
        return await self._list("prompts", cursor)


class _SessionFactory:
    def __init__(self, *, delay=0, errors=None, capabilities=None, pages=None):
        self.delay = delay
        self.errors = errors or {}
        self.capabilities = capabilities or {}
        self.pages = pages or {}
        self.calls = []
        self.request_read_timeouts = []
        self.active = 0
        self.max_active = 0
        self.sessions = []

    @asynccontextmanager
    async def open(
        self,
        server,
        *,
        auth=None,
        request_read_timeout_seconds=None,
    ):
        self.calls.append((server.id, server.transport, auth))
        self.request_read_timeouts.append(request_read_timeout_seconds)
        session = _Session(
            self,
            server,
            delay=self.delay,
            error=self.errors.get(server.id),
            capabilities=self.capabilities.get(server.id),
        )
        self.sessions.append(session)
        yield session


def _policy(**overrides):
    values = dict(
        max_parallel_servers=2,
        server_timeout_seconds=1.0,
        item_timeout_seconds=0.5,
        max_inventory_items=20,
        max_inventory_pages=8,
        max_text_length=200,
    )
    values.update(overrides)
    return McpDiscoveryPolicy(**values)


def test_zero_and_five_server_discovery_are_bounded_and_complete() -> None:
    async def scenario():
        empty = McpDiscoveryCoordinator(_Repository([]), _SessionFactory(), policy=_policy())
        assert await empty.discover_many("7", []) == []

        servers = [_server(index) for index in range(5)]
        factory = _SessionFactory(delay=0.03)
        coordinator = McpDiscoveryCoordinator(_Repository(servers), factory, policy=_policy())
        results = await coordinator.discover_many("7", [item.id for item in servers])
        assert len(results) == 5
        assert all(result.status.value == "complete" for result in results)
        assert factory.max_active == 2
        assert all(len(result.tools) == len(result.resources) == len(result.prompts) == 1 for result in results)

    asyncio.run(scenario())


def test_all_three_transports_use_the_same_safe_inventory_contract() -> None:
    async def scenario():
        servers = [
            _server(1, McpTransport.STREAMABLE_HTTP),
            _server(2, McpTransport.SSE),
            _server(3, McpTransport.STDIO),
        ]
        factory = _SessionFactory()
        coordinator = McpDiscoveryCoordinator(_Repository(servers), factory, policy=_policy())
        results = await coordinator.discover_many("7", [item.id for item in servers])
        assert [call[1] for call in factory.calls] == [item.transport for item in servers]
        assert all(result.to_dict()["tools"][0]["name"] == "tool" for result in results)

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("declared", "counts"),
    [({"tools"}, (1, 0, 0)), ({"resources"}, (0, 1, 0))],
)
def test_only_declared_capabilities_are_requested_on_one_connection(declared, counts) -> None:
    async def scenario():
        server = _server(1)
        factory = _SessionFactory(capabilities={server.id: declared})
        coordinator = McpDiscoveryCoordinator(
            _Repository([server]), factory, policy=_policy()
        )
        result = await coordinator.discover_one("7", server.id, force=True)
        assert (len(result.tools), len(result.resources), len(result.prompts)) == counts
        assert len(factory.calls) == len(factory.sessions) == 1
        assert set(factory.sessions[0].called) == declared

    asyncio.run(scenario())


def test_paginated_inventory_exhausts_all_capabilities_on_one_connection() -> None:
    async def scenario():
        server = _server(1)
        pages = {
            server.id: {
                "tools": {
                    None: ([SimpleNamespace(name="tool-1", description=None, annotations=None)], "tools-2"),
                    "tools-2": ([SimpleNamespace(name="tool-2", description=None, annotations=None)], None),
                },
                "resources": {
                    None: ([SimpleNamespace(uri="qa://resource-1", name="resource-1", description=None, mimeType="text/plain")], "resources-2"),
                    "resources-2": ([SimpleNamespace(uri="qa://resource-2", name="resource-2", description=None, mimeType="text/plain")], None),
                },
                "prompts": {
                    None: ([SimpleNamespace(name="prompt-1", description=None, arguments=[])], "prompts-2"),
                    "prompts-2": ([SimpleNamespace(name="prompt-2", description=None, arguments=[])], None),
                },
            }
        }
        factory = _SessionFactory(pages=pages)
        result = await McpDiscoveryCoordinator(
            _Repository([server]), factory, policy=_policy()
        ).discover_one("7", server.id, force=True)
        assert [item["name"] for item in result.tools] == ["tool-1", "tool-2"]
        assert [item["name"] for item in result.resources] == ["resource-1", "resource-2"]
        assert [item["name"] for item in result.prompts] == ["prompt-1", "prompt-2"]
        assert result.truncated is False
        assert len(factory.calls) == len(factory.sessions) == 1
        assert len(factory.sessions[0].cursors) == 6
        assert set(factory.sessions[0].cursors) == {
            ("tools", None), ("resources", None), ("prompts", None),
            ("tools", "tools-2"), ("resources", "resources-2"), ("prompts", "prompts-2"),
        }

    asyncio.run(scenario())


def test_pagination_page_bound_truncates_and_cursor_cycle_fails_safe() -> None:
    async def scenario():
        bounded = _server(1)
        bounded_pages = {
            bounded.id: {
                "tools": {
                    None: ([SimpleNamespace(name="tool-1", description=None, annotations=None)], "tools-2"),
                }
            }
        }
        bounded_result = await McpDiscoveryCoordinator(
            _Repository([bounded]),
            _SessionFactory(pages=bounded_pages, capabilities={bounded.id: {"tools"}}),
            policy=_policy(max_inventory_pages=1),
        ).discover_one("7", bounded.id, force=True)
        assert bounded_result.status.value == "complete"
        assert bounded_result.truncated is True
        assert [item["name"] for item in bounded_result.tools] == ["tool-1"]

        cyclic = _server(2)
        cyclic_pages = {
            cyclic.id: {
                "tools": {
                    None: ([], "loop"),
                    "loop": ([], "loop"),
                }
            }
        }
        cyclic_result = await McpDiscoveryCoordinator(
            _Repository([cyclic]),
            _SessionFactory(pages=cyclic_pages, capabilities={cyclic.id: {"tools"}}),
            policy=_policy(),
        ).discover_one("7", cyclic.id, force=True)
        assert cyclic_result.status.value == "failed"
        assert cyclic_result.error
        assert cyclic_result.error.code == "CLAUDE_MCP_PROTOCOL_ERROR"

    asyncio.run(scenario())


def test_cached_safe_error_restores_non_retryable_semantics() -> None:
    async def scenario():
        server = _server(1)
        repository = _Repository([server])
        repository.snapshots[("7", server.id, 1, 0)] = {
            "status": "failed",
            "inventory": {"tools": [], "resources": [], "prompts": []},
            "safe_error_code": "CLAUDE_MCP_CREDENTIAL_REQUIRED",
            "discovered_at": "2026-08-25T00:00:00+00:00",
        }
        result = await McpDiscoveryCoordinator(
            repository, _SessionFactory(), policy=_policy()
        ).discover_one("7", server.id)
        assert result.cached is True
        assert result.error and result.error.retryable is False

    asyncio.run(scenario())


def test_single_flight_and_exact_revision_cache_invalidation() -> None:
    async def scenario():
        server = _server(1)
        repository = _Repository([server])
        factory = _SessionFactory(delay=0.04)
        coordinator = McpDiscoveryCoordinator(repository, factory, policy=_policy())

        first, second = await asyncio.gather(
            coordinator.discover_one("7", server.id),
            coordinator.discover_one("7", server.id),
        )
        assert first.to_dict() == second.to_dict()
        assert len(factory.calls) == 1

        cached = await coordinator.discover_one("7", server.id)
        assert cached.cached is True
        assert len(factory.calls) == 1

        repository.servers[server.id] = replace(server, config_revision=2)
        refreshed = await coordinator.discover_one("7", server.id)
        assert refreshed.config_revision == 2 and refreshed.cached is False
        assert len(factory.calls) == 2

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("status", "code"),
    [(401, "CLAUDE_MCP_CREDENTIAL_REQUIRED"), (403, "CLAUDE_MCP_CREDENTIAL_REQUIRED"), (404, "CLAUDE_MCP_SERVER_REJECTED")],
)
def test_http_errors_are_mapped_without_response_body(status: int, code: str) -> None:
    async def scenario():
        server = _server(1)
        error = McpTransportHttpError(status, private_body="token=must-not-leak")
        coordinator = McpDiscoveryCoordinator(
            _Repository([server]), _SessionFactory(errors={server.id: error}), policy=_policy()
        )
        result = await coordinator.discover_one("7", server.id, force=True)
        assert result.error and result.error.code == code
        assert "must-not-leak" not in repr(result.to_dict())

    asyncio.run(scenario())


def test_timeout_cancel_and_partial_success_do_not_cancel_siblings() -> None:
    async def scenario():
        fast, slow = _server(1), _server(2)
        factory = _SessionFactory(delay=0.05)
        coordinator = McpDiscoveryCoordinator(
            _Repository([fast, slow]), factory, policy=_policy(server_timeout_seconds=0.02)
        )
        results = await coordinator.discover_many("7", [fast.id, slow.id])
        assert all(result.error and result.error.code == "CLAUDE_MCP_INVENTORY_TIMEOUT" for result in results)

        mixed_factory = _SessionFactory(errors={slow.id: RuntimeError("private")})
        mixed = McpDiscoveryCoordinator(_Repository([fast, slow]), mixed_factory, policy=_policy())
        partial = await mixed.discover_many("7", [fast.id, slow.id])
        assert [result.status.value for result in partial] == ["complete", "failed"]

        task = asyncio.create_task(
            (cancel_coordinator := McpDiscoveryCoordinator(
                _Repository([fast]), _SessionFactory(delay=2), policy=_policy()
            )).discover_one("7", fast.id, force=True)
        )
        await asyncio.sleep(0.01)
        assert await cancel_coordinator.cancel("7", fast.id) is True
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())


def test_interactive_auth_uses_its_own_timeout_and_direct_cancel_ownership() -> None:
    async def scenario():
        server = _server(1)
        auth = object()
        completing_factory = _SessionFactory(delay=0.04)
        completing = McpDiscoveryCoordinator(
            _Repository([server]),
            completing_factory,
            policy=_policy(
                server_timeout_seconds=0.01,
                item_timeout_seconds=0.01,
            ),
        )
        result = await completing.discover_one(
            "7",
            server.id,
            force=True,
            auth=auth,
            operation_timeout_seconds=0.2,
        )
        assert result.status.value == "complete"
        assert completing_factory.calls == [
            (server.id, server.transport, auth)
        ]
        assert completing_factory.request_read_timeouts == [0.2]
        assert completing._inflight == {}

        cancelling_factory = _SessionFactory(delay=2)
        cancelling = McpDiscoveryCoordinator(
            _Repository([server]), cancelling_factory, policy=_policy()
        )
        task = asyncio.create_task(
            cancelling.discover_one(
                "7",
                server.id,
                force=True,
                auth=auth,
                operation_timeout_seconds=1,
            )
        )
        await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert cancelling_factory.active == 0
        assert cancelling._inflight == {}

    asyncio.run(scenario())
