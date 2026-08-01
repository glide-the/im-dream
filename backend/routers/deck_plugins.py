"""Logical Deck control-plane routes; domain services retain authoritative state."""

from __future__ import annotations

from typing import Any, Literal, Protocol

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .deps import get_current_user

try:
    from services.errors.error_registry import ApiRouteError, build_error_payload
except ModuleNotFoundError:
    from backend.services.errors.error_registry import ApiRouteError, build_error_payload


router = APIRouter(prefix="/api/deck-plugins", tags=["deck-plugins"])


class _StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class InstallRequest(_StrictRequest):
    deck_plugin_id: str = Field(min_length=3)
    version: str = Field(min_length=5)
    source: str = Field(min_length=1)
    scope_type: Literal["instance", "workspace"]
    scope_id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1, max_length=255)


class EnableRequest(_StrictRequest):
    scope_type: Literal["instance", "workspace"]
    scope_id: str = Field(min_length=1)


class DisableRequest(EnableRequest):
    reason: str = Field(min_length=1, max_length=500)
    revocation_level: Literal["normal", "security"] = "normal"


class VersionActionRequest(EnableRequest):
    target_version: str = Field(min_length=5)


class ReconcileRequest(EnableRequest):
    environment: str = Field(min_length=1, max_length=128)


class DeckPluginAdminGateway(Protocol):
    async def list_installations(self, *, scope_id: str | None) -> Any: ...
    async def install(self, request: InstallRequest, *, actor_id: str) -> Any: ...
    async def get_version(self, deck_plugin_id: str, version: str) -> Any: ...
    async def enable(self, deck_plugin_id: str, request: EnableRequest, *, actor_id: str) -> Any: ...
    async def disable(self, deck_plugin_id: str, request: DisableRequest, *, actor_id: str) -> Any: ...
    async def upgrade(self, deck_plugin_id: str, request: VersionActionRequest, *, actor_id: str) -> Any: ...
    async def rollback(self, deck_plugin_id: str, request: VersionActionRequest, *, actor_id: str) -> Any: ...
    async def runtime_readiness(self, deck_plugin_id: str, *, environment: str) -> Any: ...
    async def reconcile(self, deck_plugin_id: str, request: ReconcileRequest, *, actor_id: str) -> Any: ...


class _UnavailableDeckPluginGateway:
    def __getattr__(self, _name: str):
        async def unavailable(*_args: Any, **_kwargs: Any) -> Any:
            raise ApiRouteError("DECK_RUNTIME_CONFIG_UNAVAILABLE", status_code=503)

        return unavailable


def get_deck_plugin_gateway() -> DeckPluginAdminGateway:
    """Deployment adapters override this dependency with the Deck control plane."""

    return _UnavailableDeckPluginGateway()  # type: ignore[return-value]


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
    current_user: dict[str, Any] = Depends(get_current_user),
    gateway: DeckPluginAdminGateway = Depends(get_deck_plugin_gateway),
):
    denied = _require_permission(current_user, "plugin:read", "plugin:admin")
    if denied is not None:
        return denied
    return await _call(gateway.list_installations(scope_id=scope_id))


@router.post("/install", status_code=202)
async def install_plugin(
    request: InstallRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: dict[str, Any] = Depends(get_current_user),
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
    return await _call(gateway.install(request, actor_id=_actor_id(current_user)))


@router.get("/{deck_plugin_id}/versions/{version}")
async def get_plugin_version(
    deck_plugin_id: str,
    version: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    gateway: DeckPluginAdminGateway = Depends(get_deck_plugin_gateway),
):
    del current_user
    return await _call(gateway.get_version(deck_plugin_id, version))


@router.post("/{deck_plugin_id}/enable")
async def enable_plugin(
    deck_plugin_id: str,
    request: EnableRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    gateway: DeckPluginAdminGateway = Depends(get_deck_plugin_gateway),
):
    denied = _require_permission(current_user, "plugin:admin")
    if denied is not None:
        return denied
    return await _call(gateway.enable(deck_plugin_id, request, actor_id=_actor_id(current_user)))


@router.post("/{deck_plugin_id}/disable")
async def disable_plugin(
    deck_plugin_id: str,
    request: DisableRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    gateway: DeckPluginAdminGateway = Depends(get_deck_plugin_gateway),
):
    denied = _require_permission(current_user, "plugin:admin")
    if denied is not None:
        return denied
    return await _call(gateway.disable(deck_plugin_id, request, actor_id=_actor_id(current_user)))


@router.post("/{deck_plugin_id}/upgrade")
async def upgrade_plugin(
    deck_plugin_id: str,
    request: VersionActionRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    gateway: DeckPluginAdminGateway = Depends(get_deck_plugin_gateway),
):
    denied = _require_permission(current_user, "plugin:admin")
    if denied is not None:
        return denied
    return await _call(gateway.upgrade(deck_plugin_id, request, actor_id=_actor_id(current_user)))


@router.post("/{deck_plugin_id}/rollback")
async def rollback_plugin(
    deck_plugin_id: str,
    request: VersionActionRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    gateway: DeckPluginAdminGateway = Depends(get_deck_plugin_gateway),
):
    denied = _require_permission(current_user, "plugin:admin")
    if denied is not None:
        return denied
    return await _call(gateway.rollback(deck_plugin_id, request, actor_id=_actor_id(current_user)))


@router.get("/{deck_plugin_id}/runtime-readiness")
async def get_runtime_readiness(
    deck_plugin_id: str,
    environment: str = Query(min_length=1, max_length=128),
    current_user: dict[str, Any] = Depends(get_current_user),
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
    current_user: dict[str, Any] = Depends(get_current_user),
    gateway: DeckPluginAdminGateway = Depends(get_deck_plugin_gateway),
):
    denied = _require_permission(current_user, "plugin:admin", "plugin:service")
    if denied is not None:
        return denied
    return await _call(gateway.reconcile(deck_plugin_id, request, actor_id=_actor_id(current_user)))
