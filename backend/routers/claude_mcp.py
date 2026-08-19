"""Resources API for the Claude MCP resource connector.

[Input] Authenticated server/status reads plus restricted configuration, OAuth, redirect, cancel, logout, and removal actions.
[Output] Safe `claude-mcp` capability/server/operation DTOs with structured error codes.
[Pos] Thin FastAPI boundary over the Claude MCP service; never handles tokens or CLI output.
[Sync] 2026-08-19: expose the reviewed schema-free v1 connector contract.
[Sync] 2026-08-19: expose safe user-to-thread credential projection failures.
[Sync] 2026-08-19: expose HTTPS user-scope MCP configuration and removal.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .deps import get_current_user

try:
    from claude_mcp.contracts import ClaudeMcpError, ClaudeMcpErrorCode
    from claude_mcp.service import ClaudeMcpService
except ModuleNotFoundError:
    from backend.claude_mcp.contracts import ClaudeMcpError, ClaudeMcpErrorCode
    from backend.claude_mcp.service import ClaudeMcpService


_service = ClaudeMcpService()


@asynccontextmanager
async def _lifespan(_app):
    try:
        yield
    finally:
        await _service.shutdown()


router = APIRouter(
    prefix="/api/claude-mcp",
    tags=["claude-mcp"],
    lifespan=_lifespan,
)

_ERROR_STATUS = {
    ClaudeMcpErrorCode.IDENTITY_UNAVAILABLE: 503,
    ClaudeMcpErrorCode.CLI_UNAVAILABLE: 503,
    ClaudeMcpErrorCode.CLI_VERSION_UNSUPPORTED: 503,
    ClaudeMcpErrorCode.SERVER_NOT_FOUND: 404,
    ClaudeMcpErrorCode.OPERATION_NOT_FOUND: 404,
    ClaudeMcpErrorCode.OPERATION_CONFLICT: 409,
    ClaudeMcpErrorCode.SERVER_CONFIGURATION_INVALID: 422,
    ClaudeMcpErrorCode.SERVER_OWNERSHIP_CONFLICT: 409,
    ClaudeMcpErrorCode.INVALID_REDIRECT_URL: 422,
    ClaudeMcpErrorCode.MALFORMED_CLI_OUTPUT: 502,
    ClaudeMcpErrorCode.CLI_FAILED: 502,
    ClaudeMcpErrorCode.AUTH_TIMEOUT: 504,
    ClaudeMcpErrorCode.AUTH_CANCELLED: 409,
    ClaudeMcpErrorCode.CREDENTIAL_SYNC_FAILED: 500,
}


class RedirectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    redirect_url: str = Field(min_length=1)


class ConfigureServerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1)
    url: str = Field(min_length=1)


def get_claude_mcp_service() -> ClaudeMcpService:
    """Dependency seam used by production and isolated route tests."""
    return _service


def _actor_id(current_user: dict[str, Any]) -> str:
    user_id = current_user.get("user_id")
    if user_id is None:
        raise ClaudeMcpError(
            ClaudeMcpErrorCode.OPERATION_NOT_FOUND,
            "Authenticated actor identity is unavailable.",
        )
    return str(user_id)


def _error(exc: ClaudeMcpError) -> JSONResponse:
    return JSONResponse(
        status_code=_ERROR_STATUS.get(exc.code, 500),
        content={
            "error": {
                "code": exc.code.value,
                "message": str(exc),
            }
        },
    )


@router.get("/capability")
async def capability(
    current_user: dict[str, Any] = Depends(get_current_user),
    service: ClaudeMcpService = Depends(get_claude_mcp_service),
):
    return (await service.capability(_actor_id(current_user))).to_dict()


@router.get("/servers")
async def list_servers(
    current_user: dict[str, Any] = Depends(get_current_user),
    service: ClaudeMcpService = Depends(get_claude_mcp_service),
):
    try:
        servers = await service.list_servers(_actor_id(current_user))
    except ClaudeMcpError as exc:
        return _error(exc)
    return {"servers": [server.to_dict() for server in servers]}


@router.post("/servers", status_code=201)
async def configure_server(
    request: ConfigureServerRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    service: ClaudeMcpService = Depends(get_claude_mcp_service),
):
    try:
        server = await service.configure_http_server(
            _actor_id(current_user), request.name, request.url
        )
    except ClaudeMcpError as exc:
        return _error(exc)
    return {"server": server.to_dict()}


@router.get("/servers/{server_name:path}")
async def get_server(
    server_name: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    service: ClaudeMcpService = Depends(get_claude_mcp_service),
):
    try:
        server = await service.get_server(_actor_id(current_user), server_name)
    except ClaudeMcpError as exc:
        return _error(exc)
    return {"server": server.to_dict()}


@router.delete("/servers/{server_name:path}")
async def remove_server(
    server_name: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    service: ClaudeMcpService = Depends(get_claude_mcp_service),
):
    try:
        server = await service.remove_server(_actor_id(current_user), server_name)
    except ClaudeMcpError as exc:
        return _error(exc)
    return {"server": server.to_dict()}


@router.post("/servers/{server_name:path}/auth-operations", status_code=202)
async def start_auth(
    server_name: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    service: ClaudeMcpService = Depends(get_claude_mcp_service),
):
    try:
        operation = await service.start_auth(_actor_id(current_user), server_name)
    except ClaudeMcpError as exc:
        return _error(exc)
    return {"operation": operation.to_dict()}


@router.get("/auth-operations/{operation_id}")
async def get_auth_operation(
    operation_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    service: ClaudeMcpService = Depends(get_claude_mcp_service),
):
    try:
        operation = await service.get_operation(_actor_id(current_user), operation_id)
    except ClaudeMcpError as exc:
        return _error(exc)
    return {"operation": operation.to_dict()}


@router.post("/auth-operations/{operation_id}/redirect")
async def submit_redirect(
    operation_id: str,
    request: RedirectRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    service: ClaudeMcpService = Depends(get_claude_mcp_service),
):
    try:
        operation = await service.submit_redirect(
            _actor_id(current_user), operation_id, request.redirect_url
        )
    except ClaudeMcpError as exc:
        return _error(exc)
    return {"operation": operation.to_dict()}


@router.post("/auth-operations/{operation_id}/cancel")
async def cancel_auth(
    operation_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    service: ClaudeMcpService = Depends(get_claude_mcp_service),
):
    try:
        operation = await service.cancel_auth(_actor_id(current_user), operation_id)
    except ClaudeMcpError as exc:
        return _error(exc)
    return {"operation": operation.to_dict()}


@router.post("/servers/{server_name:path}/logout")
async def logout(
    server_name: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    service: ClaudeMcpService = Depends(get_claude_mcp_service),
):
    try:
        server = await service.logout(_actor_id(current_user), server_name)
    except ClaudeMcpError as exc:
        return _error(exc)
    return {"server": server.to_dict()}
