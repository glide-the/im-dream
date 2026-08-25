"""Thin FastAPI boundary for database-managed MCP resources.

[Input] Authenticated actor, strict CRUD/discovery/OAuth DTOs, and optional workspace scope.
[Output] Redacted managed-MCP capability, Server, discovery, operation, and error DTOs.
[Pos] HTTP adapter only; no CLI, subprocess, credentials, MCP sessions, or persistence logic.
[Sync] 2026-08-25: expose managed CRUD, bulk discovery, OAuth callback/cancel, and logout.
[Sync] 2026-08-25: map the explicit missing OAuth callback configuration gate to HTTP 503.
[Sync] 2026-08-25: remove public auth_kind inputs; standard MCP discovery owns authentication classification.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .deps import get_current_user

try:
    from claude_mcp.contracts import (
        ClaudeMcpError,
        ClaudeMcpErrorCode,
        McpAuthKind,
        McpScope,
        McpServerCreate,
        McpServerPatch,
        McpTransport,
    )
    from claude_mcp.service import (
        ClaudeMcpService,
        get_default_claude_mcp_service,
        shutdown_default_claude_mcp_service,
    )
except ModuleNotFoundError:  # pragma: no cover
    from backend.claude_mcp.contracts import (
        ClaudeMcpError,
        ClaudeMcpErrorCode,
        McpAuthKind,
        McpScope,
        McpServerCreate,
        McpServerPatch,
        McpTransport,
    )
    from backend.claude_mcp.service import (
        ClaudeMcpService,
        get_default_claude_mcp_service,
        shutdown_default_claude_mcp_service,
    )


_service: ClaudeMcpService | None = None


@asynccontextmanager
async def _lifespan(_app):
    global _service
    if _service is None:
        _service = get_default_claude_mcp_service()
    try:
        yield
    finally:
        if _service is not None:
            await shutdown_default_claude_mcp_service()
            _service = None


router = APIRouter(
    prefix="/api/claude-mcp", tags=["claude-mcp"], lifespan=_lifespan
)


_ERROR_STATUS = {
    ClaudeMcpErrorCode.SCHEMA_CAPABILITY_MISSING: 503,
    ClaudeMcpErrorCode.SERVER_NOT_FOUND: 404,
    ClaudeMcpErrorCode.OPERATION_NOT_FOUND: 404,
    ClaudeMcpErrorCode.AUTH_OPERATION_EXPIRED: 404,
    ClaudeMcpErrorCode.SERVER_ALREADY_EXISTS: 409,
    ClaudeMcpErrorCode.SERVER_OWNERSHIP_CONFLICT: 409,
    ClaudeMcpErrorCode.SERVER_REVISION_CONFLICT: 409,
    ClaudeMcpErrorCode.OPERATION_CONFLICT: 409,
    ClaudeMcpErrorCode.AUTH_CANCELLED: 409,
    ClaudeMcpErrorCode.SERVER_CONFIGURATION_INVALID: 422,
    ClaudeMcpErrorCode.INVALID_REDIRECT_URL: 422,
    ClaudeMcpErrorCode.TRANSPORT_UNSUPPORTED: 422,
    ClaudeMcpErrorCode.STDIO_PROFILE_DENIED: 422,
    ClaudeMcpErrorCode.ENDPOINT_DENIED: 422,
    ClaudeMcpErrorCode.AUTH_TIMEOUT: 504,
    ClaudeMcpErrorCode.INVENTORY_TIMEOUT: 504,
    ClaudeMcpErrorCode.INVENTORY_TOO_LARGE: 502,
    ClaudeMcpErrorCode.CREDENTIAL_ENCRYPTION_NOT_CONFIGURED: 503,
    ClaudeMcpErrorCode.OAUTH_CONFIGURATION_MISSING: 503,
    ClaudeMcpErrorCode.PROTOCOL_ERROR: 502,
}


class RedirectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    redirect_url: str = Field(min_length=1)


class CreateServerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1)
    display_name: str | None = None
    transport: Literal["streamable_http", "sse", "stdio"] = "streamable_http"
    url: str | None = None
    stdio_profile_key: str | None = None
    scope: Literal["user", "workspace"] = "user"
    workspace_id: str | None = None
    enabled: bool = True
    idempotency_key: str | None = None

    @model_validator(mode="after")
    def validate_shape(self):
        if self.transport == "stdio" and (self.url or not self.stdio_profile_key):
            raise ValueError("stdio requires only stdio_profile_key")
        if self.transport != "stdio" and (not self.url or self.stdio_profile_key):
            raise ValueError("remote transport requires only url")
        if self.scope == "workspace" and not self.workspace_id:
            raise ValueError("workspace scope requires workspace_id")
        if self.scope == "user" and self.workspace_id:
            raise ValueError("user scope forbids workspace_id")
        return self

    def domain(self) -> McpServerCreate:
        return McpServerCreate(
            server_key=self.name,
            display_name=self.display_name or self.name,
            transport=McpTransport(self.transport),
            auth_kind=McpAuthKind.NONE,
            scope=McpScope(self.scope),
            workspace_id=self.workspace_id,
            remote_url=self.url,
            stdio_profile_key=self.stdio_profile_key,
            enabled=self.enabled,
            idempotency_key=self.idempotency_key,
        )


class UpdateServerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    expected_revision: int = Field(ge=1)
    display_name: str | None = None
    transport: Literal["streamable_http", "sse", "stdio"] | None = None
    workspace_id: str | None = None
    url: str | None = None
    stdio_profile_key: str | None = None
    enabled: bool | None = None

    def domain(self) -> McpServerPatch:
        return McpServerPatch(
            expected_revision=self.expected_revision,
            display_name=self.display_name,
            transport=McpTransport(self.transport) if self.transport else None,
            workspace_id=self.workspace_id,
            remote_url=self.url,
            stdio_profile_key=self.stdio_profile_key,
            enabled=self.enabled,
        )


class DiscoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    force: bool = False
    workspace_id: str | None = None


class BulkDiscoveryRequest(DiscoveryRequest):
    server_ids: list[str] = Field(min_length=1, max_length=64)


def get_claude_mcp_service() -> ClaudeMcpService:
    if _service is None:
        raise RuntimeError("Managed MCP service has not started.")
    return _service


def _actor_id(current_user: dict[str, Any]) -> str:
    value = current_user.get("user_id")
    if value is None:
        raise ClaudeMcpError(
            ClaudeMcpErrorCode.OPERATION_NOT_FOUND,
            "Authenticated actor identity is unavailable.",
        )
    return str(value)


def _error(exc: ClaudeMcpError) -> JSONResponse:
    return JSONResponse(
        status_code=_ERROR_STATUS.get(exc.code, 500),
        content={"error": {"code": exc.code.value, "message": str(exc)}},
    )


@router.get("/capability")
async def capability(current_user=Depends(get_current_user), service=Depends(get_claude_mcp_service)):
    return (await service.capability(_actor_id(current_user))).to_dict()


@router.get("/servers")
async def list_servers(workspace_id: str | None = None, current_user=Depends(get_current_user), service=Depends(get_claude_mcp_service)):
    try:
        values = await service.list_servers(_actor_id(current_user), workspace_id)
        return {"servers": [value.to_dict() for value in values]}
    except ClaudeMcpError as exc:
        return _error(exc)


@router.post("/servers", status_code=201)
async def create_server(request: CreateServerRequest, current_user=Depends(get_current_user), service=Depends(get_claude_mcp_service)):
    try:
        value = await service.create_server(_actor_id(current_user), request.domain())
        return {"server": value.to_dict()}
    except (ClaudeMcpError, ValueError) as exc:
        if isinstance(exc, ValueError):
            exc = ClaudeMcpError(ClaudeMcpErrorCode.SERVER_CONFIGURATION_INVALID, "Claude MCP server configuration is invalid.")
        return _error(exc)


@router.get("/servers/{identifier}")
async def get_server(identifier: str, workspace_id: str | None = None, current_user=Depends(get_current_user), service=Depends(get_claude_mcp_service)):
    try:
        return {"server": (await service.get_server(_actor_id(current_user), identifier, workspace_id)).to_dict()}
    except ClaudeMcpError as exc:
        return _error(exc)


@router.patch("/servers/{identifier}")
async def update_server(identifier: str, request: UpdateServerRequest, current_user=Depends(get_current_user), service=Depends(get_claude_mcp_service)):
    try:
        return {"server": (await service.update_server(_actor_id(current_user), identifier, request.domain())).to_dict()}
    except (ClaudeMcpError, ValueError) as exc:
        if isinstance(exc, ValueError):
            exc = ClaudeMcpError(ClaudeMcpErrorCode.SERVER_CONFIGURATION_INVALID, "Claude MCP server configuration is invalid.")
        return _error(exc)


@router.delete("/servers/{identifier}")
async def delete_server(identifier: str, expected_revision: int | None = Query(default=None, ge=1), workspace_id: str | None = None, current_user=Depends(get_current_user), service=Depends(get_claude_mcp_service)):
    try:
        value = await service.remove_server(_actor_id(current_user), identifier, expected_revision, workspace_id)
        return {"server": value.to_dict()}
    except ClaudeMcpError as exc:
        return _error(exc)


@router.post("/servers/{identifier}/discoveries")
async def discover_server(identifier: str, request: DiscoveryRequest, current_user=Depends(get_current_user), service=Depends(get_claude_mcp_service)):
    try:
        result = await service.discover_server(_actor_id(current_user), identifier, request.workspace_id, request.force)
        return {"discovery": result.to_dict()}
    except ClaudeMcpError as exc:
        return _error(exc)


@router.delete("/servers/{identifier}/discoveries")
async def cancel_discovery(identifier: str, workspace_id: str | None = None, current_user=Depends(get_current_user), service=Depends(get_claude_mcp_service)):
    try:
        cancelled = await service.cancel_discovery(
            _actor_id(current_user), identifier, workspace_id
        )
        return {"status": "cancelled" if cancelled else "idle"}
    except ClaudeMcpError as exc:
        return _error(exc)


@router.get("/server-inventories/{identifier}")
async def legacy_inventory(identifier: str, workspace_id: str | None = None, current_user=Depends(get_current_user), service=Depends(get_claude_mcp_service)):
    try:
        result = await service.get_server_inventory(_actor_id(current_user), identifier, workspace_id)
        return {"inventory": result.to_dict()}
    except ClaudeMcpError as exc:
        return _error(exc)


@router.post("/discoveries")
async def discover_many(request: BulkDiscoveryRequest, current_user=Depends(get_current_user), service=Depends(get_claude_mcp_service)):
    try:
        results = await service.discover_servers(_actor_id(current_user), request.server_ids, request.workspace_id, request.force)
        complete = sum(result.status.value == "complete" for result in results)
        status = "complete" if complete == len(results) else "failed" if complete == 0 else "partial"
        return {"status": status, "results": [result.to_dict() for result in results]}
    except ClaudeMcpError as exc:
        return _error(exc)


@router.post("/servers/{identifier}/auth-operations", status_code=202)
async def start_auth(identifier: str, workspace_id: str | None = None, current_user=Depends(get_current_user), service=Depends(get_claude_mcp_service)):
    try:
        return {"operation": (await service.start_auth(_actor_id(current_user), identifier, workspace_id)).to_dict()}
    except ClaudeMcpError as exc:
        return _error(exc)


@router.get("/auth-operations/{operation_id}")
async def get_auth(operation_id: str, current_user=Depends(get_current_user), service=Depends(get_claude_mcp_service)):
    try:
        return {"operation": (await service.get_operation(_actor_id(current_user), operation_id)).to_dict()}
    except ClaudeMcpError as exc:
        return _error(exc)


@router.post("/auth-operations/{operation_id}/redirect")
async def redirect_auth(operation_id: str, request: RedirectRequest, current_user=Depends(get_current_user), service=Depends(get_claude_mcp_service)):
    try:
        return {"operation": (await service.submit_redirect(_actor_id(current_user), operation_id, request.redirect_url)).to_dict()}
    except ClaudeMcpError as exc:
        return _error(exc)


@router.post("/auth-operations/{operation_id}/cancel")
@router.delete("/auth-operations/{operation_id}")
async def cancel_auth(operation_id: str, current_user=Depends(get_current_user), service=Depends(get_claude_mcp_service)):
    try:
        return {"operation": (await service.cancel_auth(_actor_id(current_user), operation_id)).to_dict()}
    except ClaudeMcpError as exc:
        return _error(exc)


@router.delete("/servers/{identifier}/credential")
@router.post("/servers/{identifier}/logout")
async def logout(identifier: str, workspace_id: str | None = None, current_user=Depends(get_current_user), service=Depends(get_claude_mcp_service)):
    try:
        return {"server": (await service.logout(_actor_id(current_user), identifier, workspace_id)).to_dict()}
    except ClaudeMcpError as exc:
        return _error(exc)
