"""Managed MCP Resources thin-router contracts.

[Input] Authenticated FastAPI calls with an injected provider-free fake service.
[Output] Strict CRUD/discovery/bulk/OAuth/logout DTO forwarding and safe error status evidence.
[Pos] Public route boundary tests; no database, CLI, subprocess, MCP server, or OAuth provider.
[Sync] 2026-08-25: replace CLI-shaped routes with managed database API coverage.
[Sync] 2026-08-25: prove public CRUD rejects user-selected auth_kind and defaults detection state internally.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from claude_mcp.contracts import (
    ClaudeMcpCapability,
    ClaudeMcpError,
    ClaudeMcpErrorCode,
    ClaudeMcpOperation,
    ClaudeMcpServer,
    ClaudeMcpState,
    McpAuthKind,
)
from claude_mcp.inventory import McpDiscoveryError, McpDiscoveryResult, McpDiscoveryStatus
from routers import claude_mcp
from routers.deps import get_current_user


class _Service:
    def __init__(self):
        self.calls = []
        self.server = ClaudeMcpServer.managed(
            id="server-1", name="alpha", display_name="Alpha",
            transport="streamable_http", config_scope="user",
            auth_kind="none", enabled=True, revision=1,
            remote_url="https://mcp.example.test/mcp",
        )
        self.operation = ClaudeMcpOperation(
            id="operation-1", actor_id="7", identity_fingerprint="managed-db",
            server_name="server-1", state=ClaudeMcpState.WAITING_FOR_USER,
            created_at="2026-08-25T00:00:00+00:00", updated_at="2026-08-25T00:00:00+00:00",
            authorization_url="https://auth.example.test/authorize?state=opaque",
        )

    async def shutdown(self): pass
    async def capability(self, actor):
        return ClaudeMcpCapability.managed(enabled=True)
    async def list_servers(self, actor, workspace_id=None):
        self.calls.append(("list", actor, workspace_id))
        if workspace_id:
            return [ClaudeMcpServer.managed(
                id="server-workspace", name="workspace", display_name="Workspace",
                transport="stdio", config_scope="workspace", auth_kind="none",
                enabled=True, revision=1, workspace_id=workspace_id,
            )]
        return [self.server]
    async def get_server(self, actor, identifier, workspace_id=None):
        self.calls.append(("get", actor, identifier, workspace_id)); return self.server
    async def create_server(self, actor, create):
        self.calls.append(("create", actor, create)); return self.server
    async def update_server(self, actor, identifier, patch):
        self.calls.append(("update", actor, identifier, patch)); return self.server
    async def remove_server(self, actor, identifier, expected_revision=None, workspace_id=None):
        self.calls.append(("delete", actor, identifier, expected_revision));
        return ClaudeMcpServer.managed(id="server-1", name="alpha", display_name="Alpha", transport="streamable_http", config_scope="user", auth_kind="none", enabled=False, revision=1, state=ClaudeMcpState.NOT_CONFIGURED)
    async def discover_server(self, actor, identifier, workspace_id=None, force=False):
        self.calls.append(("discover", actor, identifier, force)); return _discovery(identifier)
    async def discover_servers(self, actor, ids, workspace_id=None, force=False):
        self.calls.append(("bulk", actor, tuple(ids), force));
        return [_discovery(ids[0]), _discovery(ids[1], failed=True)]
    async def cancel_discovery(self, actor, identifier, workspace_id=None):
        self.calls.append(("cancel-discovery", actor, identifier)); return True
    async def start_auth(self, actor, identifier, workspace_id=None): self.calls.append(("auth", actor, identifier, workspace_id)); return self.operation
    async def get_operation(self, actor, operation_id):
        if actor != "7": raise ClaudeMcpError(ClaudeMcpErrorCode.OPERATION_NOT_FOUND, "Operation not found.")
        return self.operation
    async def submit_redirect(self, actor, operation_id, redirect):
        self.calls.append(("redirect", actor, operation_id)); self.operation.authorization_url = None; return self.operation
    async def cancel_auth(self, actor, operation_id): self.calls.append(("cancel", actor, operation_id)); return self.operation
    async def logout(self, actor, identifier, workspace_id=None): self.calls.append(("logout", actor, identifier, workspace_id)); return self.server


def _discovery(server_id: str, failed: bool = False):
    return McpDiscoveryResult(
        server_id=server_id,
        status=McpDiscoveryStatus.FAILED if failed else McpDiscoveryStatus.COMPLETE,
        config_revision=1, credential_revision=0,
        tools=(), resources=(), prompts=(), server_info=None,
        error=McpDiscoveryError("CLAUDE_MCP_PROTOCOL_ERROR", True) if failed else None,
        discovered_at=datetime.now(timezone.utc).isoformat(),
    )


def _client(service=None, actor_id=7):
    service = service or _Service()
    app = FastAPI()
    app.include_router(claude_mcp.router)
    app.dependency_overrides[get_current_user] = lambda: {"user_id": actor_id}
    app.dependency_overrides[claude_mcp.get_claude_mcp_service] = lambda: service
    return TestClient(app), service


def test_crud_discovery_bulk_and_logout_are_thin_forwarders():
    client, service = _client()
    assert client.get("/api/claude-mcp/capability").json()["management_mode"] == "managed_db"
    assert client.get("/api/claude-mcp/servers").json()["servers"][0]["id"] == "server-1"
    scoped = client.get("/api/claude-mcp/servers?workspace_id=workspace-1").json()
    assert scoped["servers"][0]["config_scope"] == "workspace"
    assert scoped["servers"][0]["state"] == "configured"
    created = client.post("/api/claude-mcp/servers", json={
        "name": "alpha", "display_name": "Alpha", "transport": "streamable_http",
        "url": "https://mcp.example.test/mcp", "scope": "user",
    })
    assert created.status_code == 201
    assert service.calls[-1][2].auth_kind is McpAuthKind.NONE
    patched = client.patch("/api/claude-mcp/servers/server-1", json={"expected_revision": 1, "enabled": False})
    assert patched.status_code == 200
    discovered = client.post("/api/claude-mcp/servers/server-1/discoveries", json={"force": True})
    assert discovered.status_code == 200
    assert client.delete("/api/claude-mcp/servers/server-1/discoveries").json()["status"] == "cancelled"
    bulk = client.post("/api/claude-mcp/discoveries", json={"server_ids": ["server-1", "server-2"], "force": True})
    assert bulk.json()["status"] == "partial"
    assert client.delete("/api/claude-mcp/servers/server-1/credential").status_code == 200
    assert client.delete("/api/claude-mcp/servers/server-1?expected_revision=1").status_code == 200
    assert {call[0] for call in service.calls} >= {"create", "update", "discover", "cancel-discovery", "bulk", "logout", "delete"}


def test_legacy_create_shape_is_safe_and_stdio_command_is_forbidden():
    client, service = _client()
    legacy = client.post("/api/claude-mcp/servers", json={"name": "legacy", "url": "https://mcp.example.test/mcp"})
    assert legacy.status_code == 201
    assert service.calls[-1][2].transport.value == "streamable_http"
    user_selected_auth = client.post("/api/claude-mcp/servers", json={
        "name": "auth-policy", "url": "https://mcp.example.test/mcp",
        "auth_kind": "oauth",
    })
    assert user_selected_auth.status_code == 422
    denied = client.post("/api/claude-mcp/servers", json={
        "name": "unsafe", "transport": "stdio", "stdio_profile_key": "safe", "command": "sh",
    })
    assert denied.status_code == 422


def test_oauth_redirect_and_owner_error_never_echo_secret():
    client, _ = _client()
    assert client.post("/api/claude-mcp/servers/server-1/auth-operations").status_code == 202
    secret = "https://callback.example.test/?code=private-code&state=private-state"
    redirected = client.post("/api/claude-mcp/auth-operations/operation-1/redirect", json={"redirect_url": secret})
    assert redirected.status_code == 200 and secret not in redirected.text and "private-code" not in redirected.text
    foreign, _ = _client(actor_id=8)
    missing = foreign.get("/api/claude-mcp/auth-operations/operation-1")
    assert missing.status_code == 404 and "Operation not found" in missing.text
