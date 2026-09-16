# [Input] Current Admin OAuth/profile role, shared default Workspace and Registry170-174 control adapter.
# [Output] Original permission-scoped Deck Plugin API projections with Admin-owned persistence.
# [Pos] Logical Deck control-plane ingress; Dream retains product policy and shared-artifact verification.
# [Sync] 2026-09-16: pass the OAuth actor to Admin DTO operations and remove local persistence authority.
# [Sync] 2026-09-15: consume shared default Workspace and verified current profile role instead of local queries.
"""Logical Deck control-plane routes; domain services retain authoritative state."""

from __future__ import annotations

import uuid
from typing import Any, Literal, Protocol

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from services.admin_data.errors import AdminDataError
from services.admin_data.request_auth import AdminRequestActor, AdminRequestAuth
from starlette.concurrency import run_in_threadpool

from .deps import (
    get_admin_request_auth,
    get_current_user,
    resolve_admin_default_workspace,
)

try:
    from services.deck.admin_gateway import get_deck_plugin_admin_service
    from services.errors.error_registry import ApiRouteError, build_error_payload
except ModuleNotFoundError:
    from backend.services.deck.admin_gateway import get_deck_plugin_admin_service
    from backend.services.errors.error_registry import (
        ApiRouteError,
        build_error_payload,
    )


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
    async def list_installations(self, *, scope_type: str, scope_id: str, actor: AdminRequestActor) -> Any: ...
    async def install(self, request: InstallRequest, *, actor: AdminRequestActor) -> Any: ...
    async def get_version(self, deck_plugin_id: str, version: str, *, scope_type: str, scope_id: str, actor: AdminRequestActor) -> Any: ...
    async def enable(self, deck_plugin_id: str, request: EnableRequest, *, actor: AdminRequestActor) -> Any: ...
    async def disable(self, deck_plugin_id: str, request: DisableRequest, *, actor: AdminRequestActor) -> Any: ...
    async def upgrade(self, deck_plugin_id: str, request: VersionActionRequest, *, actor: AdminRequestActor) -> Any: ...
    async def rollback(self, deck_plugin_id: str, request: VersionActionRequest, *, actor: AdminRequestActor) -> Any: ...
    async def uninstall(self, deck_plugin_id: str, request: UninstallRequest, *, actor: AdminRequestActor) -> Any: ...
    async def approve_upgrade(self, deck_plugin_id: str, request: EnableRequest, *, actor: AdminRequestActor) -> Any: ...
    async def reject_upgrade(self, deck_plugin_id: str, request: EnableRequest, *, actor: AdminRequestActor) -> Any: ...
    async def runtime_readiness(self, deck_plugin_id: str, *, scope_type: str, scope_id: str, environment: str, actor: AdminRequestActor) -> Any: ...
    async def reconcile(self, deck_plugin_id: str, request: ReconcileRequest, *, actor: AdminRequestActor) -> Any: ...


class _UnavailableDeckPluginGateway:
    def __getattr__(self, _name: str):
        async def unavailable(*_args: Any, **_kwargs: Any) -> Any:
            raise ApiRouteError("DECK_RUNTIME_CONFIG_UNAVAILABLE", status_code=503)

        return unavailable


def get_deck_plugin_gateway(
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
) -> DeckPluginAdminGateway:
    """Return the application Deck control-plane adapter."""

    return get_deck_plugin_admin_service(owner)


def _actor(current_user: dict[str, Any]) -> AdminRequestActor:
    actor = current_user.get("_admin_actor")
    if not isinstance(actor, AdminRequestActor):
        raise ApiRouteError("DECK_RUNTIME_CONFIG_UNAVAILABLE", status_code=503)
    return actor


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
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
) -> dict[str, Any]:
    """Resolve the authenticated user's owned Deck workspace for scoped admin."""
    resolved = await resolve_admin_default_workspace(current_user, owner)
    if resolved.get("role"):
        return resolved
    actor = resolved.get("_admin_actor")
    if not isinstance(owner, AdminRequestAuth) or not isinstance(actor, AdminRequestActor):
        raise HTTPException(status_code=503, detail="ADMIN_CONFIGURATION_INVALID")
    request_id = str(uuid.uuid4())
    try:
        profile = await run_in_threadpool(owner.current_profile, actor, request_id)
    except AdminDataError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"error_code": exc.code, "request_id": exc.request_id or request_id, "outcome_unknown": exc.outcome_unknown}) from None
    return {**resolved, "role": profile.role}


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
    payload = await _call(
        gateway.list_installations(
            scope_type="workspace",
            scope_id=effective_scope,
            actor=_actor(current_user),
        )
    )
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
    return await _call(gateway.install(scoped, actor=_actor(current_user)))


@router.get("/{deck_plugin_id}/versions/{version}")
async def get_plugin_version(
    deck_plugin_id: str,
    version: str,
    current_user: dict[str, Any] = Depends(_deck_plugin_current_user),
    gateway: DeckPluginAdminGateway = Depends(get_deck_plugin_gateway),
):
    return await _call(
        gateway.get_version(
            deck_plugin_id,
            version,
            scope_type="workspace",
            scope_id=str(current_user["workspace_id"]),
            actor=_actor(current_user),
        )
    )


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
    return await _call(gateway.enable(deck_plugin_id, scoped, actor=_actor(current_user)))


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
    return await _call(gateway.disable(deck_plugin_id, scoped, actor=_actor(current_user)))


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
    return await _call(gateway.upgrade(deck_plugin_id, scoped, actor=_actor(current_user)))


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
    return await _call(gateway.rollback(deck_plugin_id, scoped, actor=_actor(current_user)))


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
    return await _call(
        gateway.runtime_readiness(
            deck_plugin_id,
            scope_type="workspace",
            scope_id=str(current_user["workspace_id"]),
            environment=environment,
            actor=_actor(current_user),
        )
    )


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
    return await _call(gateway.reconcile(deck_plugin_id, scoped, actor=_actor(current_user)))


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
    return await _call(gateway.uninstall(deck_plugin_id, scoped, actor=_actor(current_user)))


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
    return await _call(gateway.approve_upgrade(deck_plugin_id, scoped, actor=_actor(current_user)))


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
    return await _call(gateway.reject_upgrade(deck_plugin_id, scoped, actor=_actor(current_user)))
