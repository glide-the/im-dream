"""Database-managed Claude MCP service contracts.

[Input] Actor-scoped in-memory repositories plus fake discovery and OAuth coordinators.
[Output] CRUD/CAS/ownership, DB-only list/get, compatibility, logout, partial discovery, and zero-CLI evidence.
[Pos] Provider-free managed MCP service coverage; no database, subprocess, network, or credential access.
[Sync] 2026-08-25: replace online CLI lifecycle tests with managed PostgreSQL service contracts.
[Sync] 2026-08-25: prove bulk discovery delegates identifiers once without serial duplicate repository reads.
[Sync] 2026-08-25: prove 401/403 discovery, not public input, promotes a remote Server to OAuth-required.
[Sync] 2026-08-27: distinguish retryable capability verification failure from a missing Admin contract.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from claude_mcp.contracts import (
    ClaudeMcpError,
    ClaudeMcpErrorCode,
    ClaudeMcpOperation,
    ClaudeMcpState,
    McpAuthKind,
    McpScope,
    McpServerCreate,
    McpServerPatch,
    McpTransport,
)
from claude_mcp.inventory import McpDiscoveryError, McpDiscoveryResult, McpDiscoveryStatus
from claude_mcp.repository import McpServerRecord
from claude_mcp.service import ClaudeMcpService, _UnavailableOAuthCoordinator


def _server(
    *,
    server_id: str = "server-1",
    user_id: str = "7",
    key: str = "alpha",
    revision: int = 1,
    workspace_id: str | None = None,
    scope: str = "user",
    credential_revision: int = 0,
):
    return McpServerRecord(
        id=server_id,
        user_id=user_id,
        workspace_id=workspace_id,
        scope=scope,
        server_key=key,
        display_name=key.title(),
        transport=McpTransport.STREAMABLE_HTTP,
        remote_url="https://mcp.example.test/mcp",
        stdio_profile_key=None,
        auth_kind=McpAuthKind.NONE,
        enabled=True,
        config_revision=revision,
        credential_revision=credential_revision,
        credential_id=None,
        credential_configured=False,
        created_at="2026-08-25T00:00:00+00:00",
        updated_at="2026-08-25T00:00:00+00:00",
    )


class _Repository:
    def __init__(self, servers=(), *, capability=True):
        self.servers = {item.id: item for item in servers}
        self.capability = capability
        self.calls = []

    async def capability_available(self):
        self.calls.append(("capability",))
        if isinstance(self.capability, Exception):
            raise self.capability
        return self.capability

    async def list_servers(self, actor_id, workspace_id=None):
        self.calls.append(("list", actor_id, workspace_id))
        return [
            item for item in self.servers.values()
            if item.user_id == actor_id
            and (item.scope == "user" or item.workspace_id == workspace_id)
        ]

    async def get_server(self, actor_id, identifier, workspace_id=None):
        self.calls.append(("get", actor_id, identifier, workspace_id))
        for item in self.servers.values():
            if item.user_id == actor_id and identifier in {item.id, item.server_key}:
                if item.scope == "workspace" and item.workspace_id != workspace_id:
                    return None
                return item
        return None

    async def create_server(self, actor_id, create):
        self.calls.append(("create", actor_id, create))
        if any(item.user_id == actor_id and item.server_key == create.server_key for item in self.servers.values()):
            raise ClaudeMcpError(ClaudeMcpErrorCode.SERVER_ALREADY_EXISTS, "Server already exists.")
        item = _server(
            server_id=f"server-{len(self.servers) + 1}",
            user_id=actor_id,
            key=create.server_key,
            workspace_id=create.workspace_id,
            scope=create.scope.value,
        )
        item = replace(
            item,
            display_name=create.display_name,
            transport=create.transport,
            remote_url=create.remote_url,
            stdio_profile_key=create.stdio_profile_key,
            auth_kind=create.auth_kind,
            enabled=create.enabled,
        )
        self.servers[item.id] = item
        return item

    async def update_server(self, actor_id, server_id, patch):
        item = await self.get_server(actor_id, server_id, patch.workspace_id)
        if item is None:
            raise ClaudeMcpError(ClaudeMcpErrorCode.SERVER_NOT_FOUND, "Server not found.")
        if item.config_revision != patch.expected_revision:
            raise ClaudeMcpError(ClaudeMcpErrorCode.SERVER_REVISION_CONFLICT, "Revision conflict.")
        changes = {name: value for name, value in patch.changes().items() if value is not None}
        updated = replace(item, **changes, config_revision=item.config_revision + 1)
        self.servers[item.id] = updated
        self.calls.append(("update", actor_id, server_id, patch.expected_revision))
        return updated

    async def delete_server(self, actor_id, server_id, expected_revision, workspace_id=None):
        item = await self.get_server(actor_id, server_id, workspace_id)
        if item is None:
            raise ClaudeMcpError(ClaudeMcpErrorCode.SERVER_NOT_FOUND, "Server not found.")
        if expected_revision is not None and item.config_revision != expected_revision:
            raise ClaudeMcpError(ClaudeMcpErrorCode.SERVER_REVISION_CONFLICT, "Revision conflict.")
        del self.servers[item.id]
        self.calls.append(("delete", actor_id, item.id, expected_revision))
        return item

    async def delete_credential(self, actor_id, server_id):
        item = await self.get_server(actor_id, server_id)
        if item is None:
            raise ClaudeMcpError(ClaudeMcpErrorCode.SERVER_NOT_FOUND, "Server not found.")
        updated = replace(item, credential_id=None, credential_configured=False, credential_revision=item.credential_revision + 1)
        self.servers[item.id] = updated
        self.calls.append(("logout", actor_id, item.id))
        return updated


class _Discovery:
    def __init__(self):
        self.calls = []

    async def discover_one(self, actor_id, server_id, *, workspace_id=None, force=False, auth=None):
        self.calls.append(("one", actor_id, server_id, force, auth))
        return McpDiscoveryResult(
            server_id=server_id,
            status=McpDiscoveryStatus.COMPLETE,
            config_revision=1,
            credential_revision=0,
            tools=(),
            resources=(),
            prompts=(),
            server_info=None,
            error=None,
            discovered_at="2026-08-25T00:00:00+00:00",
        )

    async def discover_many(self, actor_id, server_ids, *, workspace_id=None, force=False):
        self.calls.append(("many", actor_id, tuple(server_ids), force))
        return [
            McpDiscoveryResult(
                server_id=server_id,
                status=(McpDiscoveryStatus.COMPLETE if index == 0 else McpDiscoveryStatus.FAILED),
                config_revision=1,
                credential_revision=0,
                tools=(), resources=(), prompts=(), server_info=None,
                error=(None if index == 0 else McpDiscoveryError("CLAUDE_MCP_PROTOCOL_ERROR", True)),
                discovered_at="2026-08-25T00:00:00+00:00",
            )
            for index, server_id in enumerate(server_ids)
        ]

    async def cancel(self, actor_id, server_id):
        self.calls.append(("cancel", actor_id, server_id))
        return True


class _OAuth:
    def __init__(self):
        self.operation = ClaudeMcpOperation(
            id="operation-1",
            actor_id="7",
            identity_fingerprint="managed-db",
            server_name="server-1",
            state=ClaudeMcpState.WAITING_FOR_USER,
            created_at="2026-08-25T00:00:00+00:00",
            updated_at="2026-08-25T00:00:00+00:00",
            authorization_url="https://auth.example.test/authorize?state=opaque",
        )

    async def start(self, actor_id, server):
        assert actor_id == server.user_id
        return self.operation

    async def get(self, actor_id, operation_id):
        if actor_id != self.operation.actor_id or operation_id != self.operation.id:
            raise ClaudeMcpError(ClaudeMcpErrorCode.OPERATION_NOT_FOUND, "Operation not found.")
        return self.operation

    async def submit_redirect(self, actor_id, operation_id, redirect_url):
        assert "private" in redirect_url
        operation = await self.get(actor_id, operation_id)
        operation.authorization_url = None
        operation.redirect_submitted = True
        operation.state = ClaudeMcpState.EXCHANGING_CODE
        return operation

    async def cancel(self, actor_id, operation_id):
        operation = await self.get(actor_id, operation_id)
        operation.authorization_url = None
        operation.state = ClaudeMcpState.FAILED
        operation.error_code = ClaudeMcpErrorCode.AUTH_CANCELLED.value
        return operation

    async def shutdown(self):
        return None


def _service(servers=(), *, capability=True):
    repository = _Repository(servers, capability=capability)
    discovery = _Discovery()
    oauth = _OAuth()
    return ClaudeMcpService(repository=repository, discovery=discovery, oauth=oauth), repository, discovery


def test_capability_missing_fails_closed_and_legacy_cli_fields_are_null() -> None:
    async def scenario():
        service, _, _ = _service(capability=False)
        capability = await service.capability("7")
        assert capability.enabled is False
        assert capability.reason_code == "CLAUDE_MCP_SCHEMA_CAPABILITY_MISSING"
        assert capability.to_dict()["cli_version"] is None
        with pytest.raises(ClaudeMcpError) as raised:
            await service.list_servers("7")
        assert raised.value.code is ClaudeMcpErrorCode.SCHEMA_CAPABILITY_MISSING

    asyncio.run(scenario())


def test_transient_capability_verification_has_distinct_safe_reason() -> None:
    async def scenario():
        unavailable = ClaudeMcpError(
            ClaudeMcpErrorCode.SCHEMA_CAPABILITY_UNAVAILABLE,
            "Managed MCP database capability could not be verified.",
        )
        service, _, _ = _service(capability=unavailable)
        capability = await service.capability("7")
        assert capability.enabled is False
        assert capability.reason_code == "CLAUDE_MCP_SCHEMA_CAPABILITY_UNAVAILABLE"
        with pytest.raises(ClaudeMcpError) as raised:
            await service.list_servers("7")
        assert raised.value.code is ClaudeMcpErrorCode.SCHEMA_CAPABILITY_UNAVAILABLE

    asyncio.run(scenario())


def test_list_and_get_are_db_only_and_owner_scoped(monkeypatch) -> None:
    async def forbidden_subprocess(*_args, **_kwargs):
        raise AssertionError("CLI/subprocess must not run")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", forbidden_subprocess)

    async def scenario():
        own, foreign = _server(), _server(server_id="server-2", user_id="8", key="foreign")
        service, repository, discovery = _service([own, foreign])
        listed = await service.list_servers("7")
        assert [item.name for item in listed] == ["alpha"]
        assert listed[0].state is ClaudeMcpState.CONFIGURED
        assert (await service.get_server("7", "server-1")).name == "alpha"
        with pytest.raises(ClaudeMcpError) as raised:
            await service.get_server("7", "server-2")
        assert raised.value.code is ClaudeMcpErrorCode.SERVER_NOT_FOUND
        assert discovery.calls == []
        assert [call[0] for call in repository.calls].count("list") == 1

    asyncio.run(scenario())


def test_crud_legacy_create_and_workspace_scope_preserve_cas() -> None:
    async def scenario():
        service, _, discovery = _service()
        created = await service.configure_http_server("7", "alpha", "https://mcp.example.test/mcp")
        assert created.name == "alpha" and created.transport == "streamable_http"
        assert discovery.calls == []

        updated = await service.update_server(
            "7", created.id, McpServerPatch(expected_revision=1, enabled=False)
        )
        assert updated.enabled is False and updated.revision == 2
        with pytest.raises(ClaudeMcpError) as stale:
            await service.update_server(
                "7", created.id, McpServerPatch(expected_revision=1, enabled=True)
            )
        assert stale.value.code is ClaudeMcpErrorCode.SERVER_REVISION_CONFLICT

        removed = await service.remove_server("7", created.id, expected_revision=2)
        assert removed.state is ClaudeMcpState.NOT_CONFIGURED

        workspace = await service.create_server(
            "7",
            McpServerCreate(
                server_key="workspace",
                display_name="Workspace",
                transport=McpTransport.STDIO,
                auth_kind=McpAuthKind.NONE,
                scope=McpScope.WORKSPACE,
                workspace_id="workspace-1",
                stdio_profile_key="safe-profile",
            ),
        )
        with pytest.raises(ClaudeMcpError):
            await service.get_server("7", workspace.id)
        assert (await service.get_server("7", workspace.id, workspace_id="workspace-1")).name == "workspace"

    asyncio.run(scenario())


def test_single_and_bulk_discovery_keep_partial_results() -> None:
    async def scenario():
        service, repository, discovery = _service([_server(), _server(server_id="server-2", key="beta")])
        one = await service.discover_server("7", "server-1", force=True)
        assert one.status is McpDiscoveryStatus.COMPLETE
        assert not any(call[0] == "get" for call in repository.calls)
        gets_before_bulk = sum(call[0] == "get" for call in repository.calls)
        bulk = await service.discover_servers("7", ["server-1", "server-2"], force=True)
        assert bulk[0].status is McpDiscoveryStatus.COMPLETE
        assert bulk[1].status is McpDiscoveryStatus.FAILED
        assert sum(call[0] == "get" for call in repository.calls) == gets_before_bulk
        assert discovery.calls[-1] == (
            "many", "7", ("server-1", "server-2"), True
        )
        assert await service.cancel_discovery("7", "server-1") is True

    asyncio.run(scenario())


def test_discovery_persists_backend_owned_oauth_classification() -> None:
    async def scenario():
        service, repository, discovery = _service([_server()])

        async def credential_required(
            actor_id, server_id, *, workspace_id=None, force=False, auth=None
        ):
            discovery.calls.append(("credential-required", actor_id, server_id, force))
            return McpDiscoveryResult(
                server_id="server-1",
                status=McpDiscoveryStatus.FAILED,
                config_revision=1,
                credential_revision=0,
                tools=(), resources=(), prompts=(), server_info=None,
                error=McpDiscoveryError(
                    "CLAUDE_MCP_CREDENTIAL_REQUIRED", False
                ),
                discovered_at="2026-08-25T00:00:00+00:00",
            )

        discovery.discover_one = credential_required
        result = await service.discover_server("7", "alpha", force=True)
        assert result.config_revision == 2
        detected = await service.get_server("7", "alpha")
        assert detected.auth_kind == "oauth"
        assert detected.auth_state.value == "required"
        assert detected.state is ClaudeMcpState.NEEDS_AUTH
        assert await service.start_auth("7", "alpha")

        reset = await service.update_server(
            "7",
            "alpha",
            McpServerPatch(
                expected_revision=2,
                remote_url="https://other.example.test/mcp",
            ),
        )
        assert reset.auth_kind == "none"
        assert reset.auth_state.value == "unknown"
        assert reset.state is ClaudeMcpState.CONFIGURED
        assert repository.servers["server-1"].auth_kind is McpAuthKind.NONE

    asyncio.run(scenario())


def test_oauth_redirect_logout_and_errors_never_project_secret() -> None:
    async def scenario():
        oauth_server = replace(_server(), auth_kind=McpAuthKind.OAUTH)
        service, _, _ = _service([oauth_server])
        assert (await service.get_server("7", oauth_server.id)).state is ClaudeMcpState.NEEDS_AUTH
        operation = await service.start_auth("7", oauth_server.id)
        assert operation.authorization_url
        submitted = await service.submit_redirect(
            "7", operation.id, "https://callback.example.test/?code=private&state=private"
        )
        assert "private" not in repr(submitted.to_dict())
        logged_out = await service.logout("7", oauth_server.id)
        assert logged_out.state is ClaudeMcpState.LOGGED_OUT

        anonymous = replace(oauth_server, id="server-2", server_key="anonymous", auth_kind=McpAuthKind.NONE)
        service.repository.servers[anonymous.id] = anonymous
        with pytest.raises(ClaudeMcpError) as not_required:
            await service.start_auth("7", anonymous.id)
        assert not_required.value.code is ClaudeMcpErrorCode.AUTH_NOT_REQUIRED

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("code", "message"),
    [
        (
            ClaudeMcpErrorCode.CREDENTIAL_ENCRYPTION_NOT_CONFIGURED,
            "Managed MCP credential encryption is not configured.",
        ),
        (
            ClaudeMcpErrorCode.OAUTH_CONFIGURATION_MISSING,
            "Managed MCP OAuth callback configuration is unavailable.",
        ),
    ],
)
def test_unavailable_oauth_reports_the_exact_configuration_gate(code, message) -> None:
    async def scenario():
        coordinator = _UnavailableOAuthCoordinator(code, message)
        with pytest.raises(ClaudeMcpError) as raised:
            await coordinator.start("7", object())
        assert raised.value.code is code
        assert str(raised.value) == message

    asyncio.run(scenario())
