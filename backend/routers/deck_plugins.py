"""Logical Deck control-plane routes; domain services retain authoritative state."""

from __future__ import annotations

from typing import Any, Literal, Protocol
import uuid

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

import database
from services.story_workspace.agent_integration import get_or_create_default_workspace

from .deps import get_current_user

try:
    from services.errors.error_registry import ApiRouteError, build_error_payload
    from services.deck.admin_gateway import get_deck_plugin_admin_service
except ModuleNotFoundError:
    from backend.services.errors.error_registry import ApiRouteError, build_error_payload
    from backend.services.deck.admin_gateway import get_deck_plugin_admin_service


router = APIRouter(prefix="/api/deck-plugins", tags=["deck-plugins"])


class _StrictRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        populate_by_name=True,
    )


class InstallRequest(_StrictRequest):
    deck_plugin_id: str = Field(min_length=3)
    version: str = Field(alias="deck_plugin_version", min_length=5)
    source_type: Literal["marketplace", "local", "controlled"] = "controlled"
    source: str = Field(min_length=1)
    scope_type: Literal["instance", "workspace"] | None = None
    scope_id: str | None = None
    idempotency_key: str = Field(
        default_factory=lambda: f"install-{uuid.uuid4().hex}",
        min_length=1,
        max_length=255,
    )


class EnableRequest(_StrictRequest):
    scope_type: Literal["instance", "workspace"] | None = None
    scope_id: str | None = None


class DisableRequest(EnableRequest):
    reason: str = Field(default="Disabled from Plugin Admin", min_length=1, max_length=500)
    revocation_level: Literal["normal", "security"] = "normal"


class VersionActionRequest(EnableRequest):
    target_version: str = Field(min_length=5)


class ReconcileRequest(EnableRequest):
    environment: str = Field(default="current", min_length=1, max_length=128)


class UninstallRequest(EnableRequest):
    purge: bool = False


class DeckPluginAdminGateway(Protocol):
    async def list_installations(self, *, scope_id: str | None) -> Any: ...
    async def install(self, request: InstallRequest, *, actor_id: str) -> Any: ...
    async def get_version(self, deck_plugin_id: str, version: str) -> Any: ...
    async def enable(self, deck_plugin_id: str, request: EnableRequest, *, actor_id: str) -> Any: ...
    async def disable(self, deck_plugin_id: str, request: DisableRequest, *, actor_id: str) -> Any: ...
    async def upgrade(self, deck_plugin_id: str, request: VersionActionRequest, *, actor_id: str) -> Any: ...
    async def rollback(self, deck_plugin_id: str, request: VersionActionRequest, *, actor_id: str) -> Any: ...
    async def uninstall(self, deck_plugin_id: str, request: UninstallRequest, *, actor_id: str) -> Any: ...
    async def approve_upgrade(self, deck_plugin_id: str, request: EnableRequest, *, actor_id: str) -> Any: ...
    async def reject_upgrade(self, deck_plugin_id: str, request: EnableRequest, *, actor_id: str) -> Any: ...
    async def runtime_readiness(self, deck_plugin_id: str, *, environment: str) -> Any: ...
    async def reconcile(self, deck_plugin_id: str, request: ReconcileRequest, *, actor_id: str) -> Any: ...


class _UnavailableDeckPluginGateway:
    def __getattr__(self, _name: str):
        async def unavailable(*_args: Any, **_kwargs: Any) -> Any:
            raise ApiRouteError("DECK_RUNTIME_CONFIG_UNAVAILABLE", status_code=503)

        return unavailable


def get_deck_plugin_gateway() -> DeckPluginAdminGateway:
    """Return the application Deck control-plane adapter."""

    return get_deck_plugin_admin_service()


def _actor_id(current_user: dict[str, Any]) -> str:
    return str(current_user["user_id"])


def _permissions(current_user: dict[str, Any]) -> set[str]:
    raw = current_user.get("permissions", current_user.get("scopes", []))
    if isinstance(raw, str):
        return set(raw.split())
    return {str(item) for item in raw}


def _require_permission(
    current_user: dict[str, Any],
    *accepted: str,
) -> JSONResponse | None:
    if current_user.get("role") == "admin":
        return None
    if _permissions(current_user).intersection(accepted):
        return None
    return JSONResponse(
        status_code=403,
        content=build_error_payload("WORKFLOW_PERMISSION_DENIED"),
    )


async def _deck_plugin_current_user(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Resolve the authenticated user's owned Deck workspace for scoped admin."""
    db = database.get_db()
    try:
        user_id = int(current_user["user_id"])
        workspace_id = current_user.get("workspace_id") or get_or_create_default_workspace(db, user_id)
        user_row = db.execute("SELECT role FROM users WHERE id = %s", (user_id,)).fetchone()
    finally:
        db.close()
    return {
        **current_user,
        "workspace_id": workspace_id,
        "role": current_user.get("role") or (user_row["role"] if user_row else "user"),
    }


def _workspace_request(
    request: _StrictRequest,
    current_user: dict[str, Any],
) -> _StrictRequest | JSONResponse:
    scope_type = getattr(request, "scope_type", None)
    scope_id = getattr(request, "scope_id", None)
    if scope_type == "instance" and current_user.get("role") != "admin":
        return JSONResponse(
            status_code=403,
            content=build_error_payload("WORKFLOW_PERMISSION_DENIED"),
        )
    expected_workspace = str(current_user["workspace_id"])
    if scope_type == "workspace" and scope_id and str(scope_id) != expected_workspace:
        return JSONResponse(
            status_code=403,
            content=build_error_payload("WORKFLOW_PERMISSION_DENIED"),
        )
    if scope_type is None:
        scope_type = "workspace"
    if scope_id is None:
        scope_id = expected_workspace if scope_type == "workspace" else "instance"
    return request.model_copy(update={"scope_type": scope_type, "scope_id": str(scope_id)})


def _json(value: Any) -> Any:
    return value.model_dump(mode="json") if hasattr(value, "model_dump") else value


async def _call(awaitable: Any) -> Any:
    try:
        return _json(await awaitable)
    except ApiRouteError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(
                exc.code,
                operation_id=exc.operation_id,
                run_id=exc.run_id,
                failed_check=exc.failed_check,
            ),
        )
    except Exception:
        return JSONResponse(
            status_code=503,
            content=build_error_payload("DECK_RUNTIME_CONFIG_UNAVAILABLE"),
        )


@router.get("/installations")
async def list_installations(
    scope_id: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(_deck_plugin_current_user),
    gateway: DeckPluginAdminGateway = Depends(get_deck_plugin_gateway),
):
    denied = _require_permission(current_user, "plugin:read", "plugin:admin")
    if denied is not None:
        return denied
    effective_scope = scope_id or str(current_user["workspace_id"])
    payload = await _call(gateway.list_installations(scope_id=effective_scope))
    if isinstance(payload, JSONResponse):
        return payload
    return {
        **payload,
        "permissions": {
            "can_manage": True,
            "can_install_local": current_user.get("role") == "admin",
            "can_force_purge": current_user.get("role") == "admin",
        },
    }


@router.post("/install", status_code=202)
async def install_plugin(
    request: InstallRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: dict[str, Any] = Depends(_deck_plugin_current_user),
    gateway: DeckPluginAdminGateway = Depends(get_deck_plugin_gateway),
):
    denied = _require_permission(current_user, "plugin:admin")
    if denied is not None:
        return denied
    if idempotency_key is not None and idempotency_key != request.idempotency_key:
        return JSONResponse(
            status_code=409,
            content=build_error_payload("IDEMPOTENCY_CONFLICT"),
        )
    scoped = _workspace_request(request, current_user)
    if isinstance(scoped, JSONResponse):
        return scoped
    return await _call(gateway.install(scoped, actor_id=_actor_id(current_user)))


@router.get("/{deck_plugin_id}/versions/{version}")
async def get_plugin_version(
    deck_plugin_id: str,
    version: str,
    current_user: dict[str, Any] = Depends(_deck_plugin_current_user),
    gateway: DeckPluginAdminGateway = Depends(get_deck_plugin_gateway),
):
    del current_user
    return await _call(gateway.get_version(deck_plugin_id, version))


@router.post("/{deck_plugin_id}/enable")
async def enable_plugin(
    deck_plugin_id: str,
    request: EnableRequest,
    current_user: dict[str, Any] = Depends(_deck_plugin_current_user),
    gateway: DeckPluginAdminGateway = Depends(get_deck_plugin_gateway),
):
    denied = _require_permission(current_user, "plugin:admin")
    if denied is not None:
        return denied
    scoped = _workspace_request(request, current_user)
    if isinstance(scoped, JSONResponse):
        return scoped
    return await _call(gateway.enable(deck_plugin_id, scoped, actor_id=_actor_id(current_user)))


@router.post("/{deck_plugin_id}/disable")
async def disable_plugin(
    deck_plugin_id: str,
    request: DisableRequest,
    current_user: dict[str, Any] = Depends(_deck_plugin_current_user),
    gateway: DeckPluginAdminGateway = Depends(get_deck_plugin_gateway),
):
    denied = _require_permission(current_user, "plugin:admin")
    if denied is not None:
        return denied
    scoped = _workspace_request(request, current_user)
    if isinstance(scoped, JSONResponse):
        return scoped
    return await _call(gateway.disable(deck_plugin_id, scoped, actor_id=_actor_id(current_user)))


@router.post("/{deck_plugin_id}/upgrade")
async def upgrade_plugin(
    deck_plugin_id: str,
    request: VersionActionRequest,
    current_user: dict[str, Any] = Depends(_deck_plugin_current_user),
    gateway: DeckPluginAdminGateway = Depends(get_deck_plugin_gateway),
):
    denied = _require_permission(current_user, "plugin:admin")
    if denied is not None:
        return denied
    scoped = _workspace_request(request, current_user)
    if isinstance(scoped, JSONResponse):
        return scoped
    return await _call(gateway.upgrade(deck_plugin_id, scoped, actor_id=_actor_id(current_user)))


@router.post("/{deck_plugin_id}/rollback")
async def rollback_plugin(
    deck_plugin_id: str,
    request: VersionActionRequest,
    current_user: dict[str, Any] = Depends(_deck_plugin_current_user),
    gateway: DeckPluginAdminGateway = Depends(get_deck_plugin_gateway),
):
    denied = _require_permission(current_user, "plugin:admin")
    if denied is not None:
        return denied
    scoped = _workspace_request(request, current_user)
    if isinstance(scoped, JSONResponse):
        return scoped
    return await _call(gateway.rollback(deck_plugin_id, scoped, actor_id=_actor_id(current_user)))


@router.get("/{deck_plugin_id}/runtime-readiness")
async def get_runtime_readiness(
    deck_plugin_id: str,
    environment: str = Query(default="current", min_length=1, max_length=128),
    current_user: dict[str, Any] = Depends(_deck_plugin_current_user),
    gateway: DeckPluginAdminGateway = Depends(get_deck_plugin_gateway),
):
    denied = _require_permission(current_user, "plugin:admin")
    if denied is not None:
        return denied
    return await _call(gateway.runtime_readiness(deck_plugin_id, environment=environment))


@router.post("/{deck_plugin_id}/reconcile", status_code=202)
async def reconcile_plugin(
    deck_plugin_id: str,
    request: ReconcileRequest,
    current_user: dict[str, Any] = Depends(_deck_plugin_current_user),
    gateway: DeckPluginAdminGateway = Depends(get_deck_plugin_gateway),
):
    denied = _require_permission(current_user, "plugin:admin", "plugin:service")
    if denied is not None:
        return denied
    scoped = _workspace_request(request, current_user)
    if isinstance(scoped, JSONResponse):
        return scoped
    return await _call(gateway.reconcile(deck_plugin_id, scoped, actor_id=_actor_id(current_user)))


@router.post("/{deck_plugin_id}/uninstall")
async def uninstall_plugin(
    deck_plugin_id: str,
    request: UninstallRequest,
    current_user: dict[str, Any] = Depends(_deck_plugin_current_user),
    gateway: DeckPluginAdminGateway = Depends(get_deck_plugin_gateway),
):
    denied = _require_permission(current_user, "plugin:admin")
    if denied is not None:
        return denied
    if request.purge and current_user.get("role") != "admin":
        return JSONResponse(status_code=403, content=build_error_payload("WORKFLOW_PERMISSION_DENIED"))
    scoped = _workspace_request(request, current_user)
    if isinstance(scoped, JSONResponse):
        return scoped
    return await _call(gateway.uninstall(deck_plugin_id, scoped, actor_id=_actor_id(current_user)))


@router.post("/{deck_plugin_id}/upgrade/approve")
async def approve_plugin_upgrade(
    deck_plugin_id: str,
    request: EnableRequest,
    current_user: dict[str, Any] = Depends(_deck_plugin_current_user),
    gateway: DeckPluginAdminGateway = Depends(get_deck_plugin_gateway),
):
    denied = _require_permission(current_user, "plugin:admin")
    if denied is not None:
        return denied
    scoped = _workspace_request(request, current_user)
    if isinstance(scoped, JSONResponse):
        return scoped
    return await _call(gateway.approve_upgrade(deck_plugin_id, scoped, actor_id=_actor_id(current_user)))


@router.post("/{deck_plugin_id}/upgrade/reject")
async def reject_plugin_upgrade(
    deck_plugin_id: str,
    request: EnableRequest,
    current_user: dict[str, Any] = Depends(_deck_plugin_current_user),
    gateway: DeckPluginAdminGateway = Depends(get_deck_plugin_gateway),
):
    denied = _require_permission(current_user, "plugin:admin")
    if denied is not None:
        return denied
    scoped = _workspace_request(request, current_user)
    if isinstance(scoped, JSONResponse):
        return scoped
    return await _call(gateway.reject_upgrade(deck_plugin_id, scoped, actor_id=_actor_id(current_user)))
