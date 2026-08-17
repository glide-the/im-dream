"""Logical Voice Decks plugin-binding routes backed by the Deck domain owner."""

from __future__ import annotations

from typing import Any, Protocol

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from .deps import get_current_user

try:
    from models.deck_plugin import DeckPluginBindingUpdateRequest, DeckPluginSelectionRequest
    from services.errors.error_registry import ApiRouteError, build_error_payload
except ModuleNotFoundError:
    from backend.models.deck_plugin import (
        DeckPluginBindingUpdateRequest,
        DeckPluginSelectionRequest,
    )
    from backend.services.errors.error_registry import ApiRouteError, build_error_payload


router = APIRouter(prefix="/api/voice-decks", tags=["voice-decks-plugin-binding"])


class VoiceDeckPluginGateway(Protocol):
    async def list_options(self, deck_id: str, *, actor: dict[str, Any]) -> Any: ...
    async def get_binding(self, deck_id: str, *, actor: dict[str, Any]) -> Any: ...
    async def save_binding(self, deck_id: str, request: DeckPluginBindingUpdateRequest, *, actor: dict[str, Any]) -> Any: ...
    async def validate_binding(self, deck_id: str, request: DeckPluginSelectionRequest, *, actor: dict[str, Any]) -> Any: ...


class _UnavailableVoiceDeckGateway:
    def __getattr__(self, _name: str):
        async def unavailable(*_args: Any, **_kwargs: Any) -> Any:
            raise ApiRouteError("DECK_RUNTIME_CONFIG_UNAVAILABLE", status_code=503)

        return unavailable


def get_voice_deck_gateway() -> VoiceDeckPluginGateway:
    """Deployment adapters override this with the existing Deck binding service."""

    return _UnavailableVoiceDeckGateway()  # type: ignore[return-value]


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


@router.get("/{deck_id}/plugin-options")
async def get_plugin_options(
    deck_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    gateway: VoiceDeckPluginGateway = Depends(get_voice_deck_gateway),
):
    return await _call(gateway.list_options(deck_id, actor=current_user))


@router.get("/{deck_id}/plugin-binding")
async def get_plugin_binding(
    deck_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    gateway: VoiceDeckPluginGateway = Depends(get_voice_deck_gateway),
):
    return await _call(gateway.get_binding(deck_id, actor=current_user))


@router.put("/{deck_id}/plugin-binding")
async def put_plugin_binding(
    deck_id: str,
    request: DeckPluginBindingUpdateRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    gateway: VoiceDeckPluginGateway = Depends(get_voice_deck_gateway),
):
    return await _call(gateway.save_binding(deck_id, request, actor=current_user))


@router.post("/{deck_id}/plugin-binding/validate")
async def validate_plugin_binding(
    deck_id: str,
    request: DeckPluginSelectionRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    gateway: VoiceDeckPluginGateway = Depends(get_voice_deck_gateway),
):
    return await _call(gateway.validate_binding(deck_id, request, actor=current_user))
