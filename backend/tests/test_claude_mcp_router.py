"""Public Claude MCP Resources API contract tests.

[Input] Authenticated FastAPI calls with an injected provider-free fake service.
[Output] Capability, configuration/removal, colon-bearing server, operation, redirect, cancel, logout, and safe-error DTO evidence.
[Pos] Route boundary tests; no database, real CLI, or real OAuth activity.
[Sync] 2026-08-19: cover the reviewed `/api/claude-mcp` v1 contract and ownership seam.
[Sync] 2026-08-19: cover restricted HTTPS user-scope configuration and removal DTOs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from claude_mcp.contracts import (
    ClaudeMcpCapability,
    ClaudeMcpError,
    ClaudeMcpErrorCode,
    ClaudeMcpOperation,
    ClaudeMcpServer,
    ClaudeMcpState,
)
from routers import claude_mcp
from routers.deps import get_current_user


class _Service:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.operation = ClaudeMcpOperation(
            id="operation-1",
            actor_id="7",
            identity_fingerprint="identity-1",
            server_name="plugin:comfy-cloud:comfy-cloud",
            state=ClaudeMcpState.WAITING_FOR_USER,
            authorization_url="https://oauth.example.test/authorize?state=opaque",
            created_at=now,
            updated_at=now,
        )
        self.redirect_received: str | None = None
        self.configured: tuple[str, str] | None = None

    async def capability(self, actor_id: str) -> ClaudeMcpCapability:
        assert actor_id == "7"
        return ClaudeMcpCapability(True, None, "2.1.220", "2.1.186", "2.1.191", "identity-1")

    async def list_servers(self, actor_id: str) -> list[ClaudeMcpServer]:
        assert actor_id == "7"
        return [ClaudeMcpServer(self.operation.server_name, ClaudeMcpState.NEEDS_AUTH)]

    async def get_server(self, actor_id: str, server_name: str) -> ClaudeMcpServer:
        assert actor_id == "7"
        return ClaudeMcpServer(server_name, ClaudeMcpState.NEEDS_AUTH)

    async def configure_http_server(
        self, actor_id: str, server_name: str, server_url: str
    ) -> ClaudeMcpServer:
        assert actor_id == "7"
        self.configured = (server_name, server_url)
        return ClaudeMcpServer(server_name, ClaudeMcpState.NEEDS_AUTH)

    async def remove_server(self, actor_id: str, server_name: str) -> ClaudeMcpServer:
        assert actor_id == "7"
        return ClaudeMcpServer(server_name, ClaudeMcpState.NOT_CONFIGURED)

    async def start_auth(self, actor_id: str, server_name: str) -> ClaudeMcpOperation:
        assert actor_id == "7"
        assert server_name == self.operation.server_name
        return self.operation

    async def get_operation(self, actor_id: str, operation_id: str) -> ClaudeMcpOperation:
        if actor_id != "7" or operation_id != self.operation.id:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.OPERATION_NOT_FOUND,
                "Claude MCP authentication operation was not found.",
            )
        return self.operation

    async def submit_redirect(self, actor_id: str, operation_id: str, redirect_url: str) -> ClaudeMcpOperation:
        assert actor_id == "7" and operation_id == self.operation.id
        self.redirect_received = redirect_url
        self.operation.authorization_url = None
        self.operation.redirect_submitted = True
        self.operation.state = ClaudeMcpState.EXCHANGING_CODE
        return self.operation

    async def cancel_auth(self, actor_id: str, operation_id: str) -> ClaudeMcpOperation:
        assert actor_id == "7" and operation_id == self.operation.id
        self.operation.state = ClaudeMcpState.FAILED
        self.operation.authorization_url = None
        self.operation.error_code = ClaudeMcpErrorCode.AUTH_CANCELLED.value
        self.operation.error_message = "Claude MCP authentication was cancelled."
        return self.operation

    async def logout(self, actor_id: str, server_name: str) -> ClaudeMcpServer:
        assert actor_id == "7"
        return ClaudeMcpServer(server_name, ClaudeMcpState.LOGGED_OUT)


def _client(service: _Service, *, actor_id: int = 7) -> TestClient:
    app = FastAPI()
    app.include_router(claude_mcp.router)
    app.dependency_overrides[get_current_user] = lambda: {"user_id": actor_id}
    app.dependency_overrides[claude_mcp.get_claude_mcp_service] = lambda: service
    return TestClient(app)


def test_full_api_contract_preserves_colon_name_and_never_returns_redirect_submission() -> None:
    service = _Service()
    client = _client(service)
    server_name = "plugin:comfy-cloud:comfy-cloud"
    capability = client.get("/api/claude-mcp/capability")
    assert capability.status_code == 200
    assert capability.json()["enabled"] is True
    assert client.get("/api/claude-mcp/servers").json()["servers"][0]["name"] == server_name

    configured = client.post(
        "/api/claude-mcp/servers",
        json={"name": "user-server", "url": "https://mcp.example.test/api"},
    )
    assert configured.status_code == 201
    assert service.configured == ("user-server", "https://mcp.example.test/api")
    assert configured.json()["server"]["state"] == "needs_auth"

    started = client.post(f"/api/claude-mcp/servers/{server_name}/auth-operations")
    assert started.status_code == 202
    assert started.json()["operation"]["authorization_url"].startswith("https://oauth.example.test/")

    redirect = "https://callback.example.test/done?code=private&state=private"
    submitted = client.post(
        "/api/claude-mcp/auth-operations/operation-1/redirect",
        json={"redirect_url": redirect},
    )
    assert submitted.status_code == 200
    assert service.redirect_received == redirect
    assert submitted.json()["operation"]["authorization_url"] is None
    assert redirect not in submitted.text

    cancelled = client.post("/api/claude-mcp/auth-operations/operation-1/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["operation"]["error"]["code"] == "CLAUDE_MCP_AUTH_CANCELLED"

    logged_out = client.post(f"/api/claude-mcp/servers/{server_name}/logout")
    assert logged_out.status_code == 200
    assert logged_out.json()["server"]["state"] == "logged_out"

    removed = client.delete("/api/claude-mcp/servers/user-server")
    assert removed.status_code == 200
    assert removed.json()["server"]["state"] == "not_configured"


def test_operation_not_found_is_client_safe_and_owner_scoped() -> None:
    response = _client(_Service(), actor_id=8).get(
        "/api/claude-mcp/auth-operations/operation-1"
    )
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "CLAUDE_MCP_OPERATION_NOT_FOUND",
            "message": "Claude MCP authentication operation was not found.",
        }
    }
