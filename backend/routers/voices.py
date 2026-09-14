#!/usr/bin/env python3
# [Sync] 2026-09-15: four public Voice operations use Admin; Deck/default/plugin/internal data remains pending.
# [Input] Consume typed Admin public Voice operations, database Deck APIs and the shared Deck-default service,
#         and shared auth dependency.
# [Output] Register /api/decks* and /api/voices* endpoints; new Deck creation
#          fails closed unless its configured default plugin ref is verified;
#          default-team repair is explicit and idempotent.
# [Pos] deck-and-voice route node in backend/routers
# [Sync] 2026-05-25: extracted deck and voice management routes from backend/server.py.
# [Sync] 2026-08-14: atomically bind the configured drama-forge version to every
#                    newly created Deck after ready/digest/CLI verification.
# [Sync] 2026-08-14: expose transactional default-team plugin reconciliation for existing accounts.
# [Sync] 2026-08-14: enforce system-default publication and self-collection policy at the API boundary.
# [Sync] 2026-08-14: expose the active system default alongside other actors'
#                    published Decks in the collectable community projection.
# [Sync] 2026-08-15: reconcile missing legacy default teams as well as empty plugin refs.
# [Sync] 2026-08-16: map preserved child/runtime Deck deletion dependencies to HTTP 409.

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

import database
import config

try:
    from services.deck.defaults import (
        DefaultDeckPluginUnavailable,
        reconcile_default_screenplay_deck_plugin,
        resolve_default_deck_plugin_ref,
    )
except ModuleNotFoundError:  # pragma: no cover - package import compatibility
    from backend.services.deck.defaults import (
        DefaultDeckPluginUnavailable,
        reconcile_default_screenplay_deck_plugin,
        resolve_default_deck_plugin_ref,
    )

try:
    from services.deck.sharing import DeckSharingPolicyError
except ModuleNotFoundError:  # pragma: no cover - package import compatibility
    from backend.services.deck.sharing import DeckSharingPolicyError

from services.admin_data.voice_data import (
    AdminVoiceData, VoiceCollectInputDTO, VoiceCreateRequestDTO, VoiceForkRequestDTO,
    VoiceIdInputDTO, VoiceUpdateRequestDTO,
)
from services.admin_data.request_auth import AdminRequestAuth
from .deps import SafeRequestValidationRoute, get_current_user, invoke_admin_operation

router = APIRouter()


class DeckCreateRequest(BaseModel):
    name: str
    description: str = None
    name_zh: str = None
    name_en: str = None
    description_zh: str = None
    description_en: str = None
    icon: str = None
    color: str = None


class DeckUpdateRequest(BaseModel):
    name: str = None
    description: str = None
    name_zh: str = None
    name_en: str = None
    description_zh: str = None
    description_en: str = None
    icon: str = None
    color: str = None
    enabled: bool = None
    order_index: int = None


VoiceCreateRequest = VoiceCreateRequestDTO
VoiceUpdateRequest = VoiceUpdateRequestDTO
VoiceForkRequest = VoiceForkRequestDTO


@router.get("/api/decks")
def list_decks(published: bool = False, current_user: dict = Depends(get_current_user)):
    """Get actor Decks or collectable system/public community Decks."""
    if published:
        decks = database.get_published_decks(
            exclude_owner_id=current_user["user_id"],
        )
    else:
        user_id = current_user["user_id"]
        decks = database.get_user_decks(user_id)
    return {"decks": decks}


@router.post("/api/decks/defaults/reconcile")
def reconcile_deck_defaults(current_user: dict = Depends(get_current_user)):
    """Create a missing actor default or repair its empty verified plugin ref."""

    try:
        return reconcile_default_screenplay_deck_plugin(current_user["user_id"])
    except (DefaultDeckPluginUnavailable, ValueError) as exc:
        if isinstance(exc, ValueError) and str(exc) != "DEFAULT_DECK_PLUGIN_UNAVAILABLE":
            raise
        raise HTTPException(
            status_code=409,
            detail=(
                "Default Deck plugin "
                f"{config.DEFAULT_DECK_CLAUDE_PLUGIN_PACKAGE_NAME} "
                f"v{config.DEFAULT_DECK_CLAUDE_PLUGIN_VERSION} is unavailable"
            ),
        ) from None


@router.get("/api/decks/{deck_id}")
def get_deck(deck_id: str, current_user: dict = Depends(get_current_user)):
    """Get deck with all voices"""
    user_id = current_user["user_id"]
    deck = database.get_deck_with_voices(user_id, deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    return deck


@router.post("/api/decks")
def create_deck(
    request: DeckCreateRequest, current_user: dict = Depends(get_current_user)
):
    """Create a user Deck with its verified product-default Claude plugin."""
    user_id = current_user["user_id"]
    try:
        default_plugin_ref = resolve_default_deck_plugin_ref()
        deck_id = database.create_deck(
            user_id,
            name=request.name,
            description=request.description,
            name_zh=request.name_zh,
            name_en=request.name_en,
            description_zh=request.description_zh,
            description_en=request.description_en,
            icon=request.icon,
            color=request.color,
            default_plugin_ref=default_plugin_ref,
        )
    except (DefaultDeckPluginUnavailable, ValueError) as exc:
        if isinstance(exc, ValueError) and str(exc) != "DEFAULT_DECK_PLUGIN_UNAVAILABLE":
            raise
        raise HTTPException(
            status_code=409,
            detail=(
                "Default Deck plugin "
                f"{config.DEFAULT_DECK_CLAUDE_PLUGIN_PACKAGE_NAME} "
                f"v{config.DEFAULT_DECK_CLAUDE_PLUGIN_VERSION} is unavailable"
            ),
        ) from None
    return {"deck_id": deck_id}


@router.put("/api/decks/{deck_id}")
def update_deck(
    deck_id: str,
    request: DeckUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update a user deck"""
    user_id = current_user["user_id"]
    updates = {k: v for k, v in request.dict().items() if v is not None}

    success = database.update_deck(user_id, deck_id, updates)
    if not success:
        raise HTTPException(
            status_code=404, detail="Deck not found or permission denied"
        )
    return {"success": True}


@router.delete("/api/decks/{deck_id}")
def delete_deck(deck_id: str, current_user: dict = Depends(get_current_user)):
    """Delete an unreferenced user Deck and its mutable refs/voices."""
    user_id = current_user["user_id"]
    try:
        success = database.delete_deck(user_id, deck_id)
    except database.DeckDeletionConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    if not success:
        raise HTTPException(
            status_code=404, detail="Deck not found or permission denied"
        )
    return {"success": True}


@router.post("/api/decks/{deck_id}/fork")
def fork_deck(deck_id: str, current_user: dict = Depends(get_current_user)):
    """Fork a deck (system or published community deck) to create user's own copy"""
    user_id = current_user["user_id"]
    try:
        new_deck_id = database.fork_deck(user_id, deck_id)
        database.increment_deck_install_count(deck_id)
        return {"deck_id": new_deck_id}
    except DeckSharingPolicyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/decks/{deck_id}/publish")
def publish_deck(deck_id: str, current_user: dict = Depends(get_current_user)):
    """
    Publish/unpublish a deck to community store.
    @@@ Warning: Publishing breaks parent_id chain (deck becomes standalone)
    """
    user_id = current_user["user_id"]
    try:
        deck = database.get_deck_with_voices(user_id, deck_id)
        if not deck:
            raise HTTPException(
                status_code=404, detail="Deck not found or not owned by user"
            )

        if deck.get("published"):
            database.unpublish_deck(deck_id, user_id)
            return {"success": True, "published": False}
        database.publish_deck(deck_id, user_id)
        return {"success": True, "published": True}
    except HTTPException:
        raise
    except DeckSharingPolicyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@router.post("/api/decks/{deck_id}/sync")
def sync_deck(deck_id: str, current_user: dict = Depends(get_current_user)):
    """Sync user's forked deck with parent template (force overwrites local changes)"""
    user_id = current_user["user_id"]
    try:
        result = database.sync_deck_with_parent(user_id, deck_id, force=True)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class _VoiceRoute(SafeRequestValidationRoute):
    validation_error_detail = "Invalid Voice request"


_voice_router = APIRouter(route_class=_VoiceRoute)


def _voice_data(request: Request) -> AdminVoiceData:
    owner = getattr(request.app.state, "admin_request_auth", None)
    if not isinstance(owner, AdminRequestAuth):
        raise HTTPException(status_code=503, detail="ADMIN_CONFIGURATION_INVALID")
    return AdminVoiceData(owner.client)


def _voice_error(kind: str, voice_id: str | None = None):
    def error(exc, request_id):
        if not exc.outcome_unknown and exc.status_code == 404:
            if exc.code == "DECK_ACCESS_DENIED" and kind in {"create", "collect"}:
                raise HTTPException(status_code=400, detail="Deck not found or permission denied" if kind == "create" else "Target deck not found or permission denied")
            if exc.code == "VOICE_ACCESS_DENIED" and kind == "collect":
                raise HTTPException(status_code=400, detail=f"Voice {voice_id} not found")
        raise HTTPException(status_code=exc.status_code, detail={"error_code": exc.code,
            "request_id": exc.request_id or request_id, "outcome_unknown": exc.outcome_unknown})
    return error


@_voice_router.post("/api/voices")
async def create_voice(
    request: VoiceCreateRequest, current_user: dict = Depends(get_current_user), data: AdminVoiceData = Depends(_voice_data),
):
    result = await invoke_admin_operation(current_user, data.create, request.domain_input(), error_handler=_voice_error("create"))
    return result.model_dump()


@_voice_router.put("/api/voices/{voice_id}")
async def update_voice(
    voice_id: str, request: VoiceUpdateRequest, current_user: dict = Depends(get_current_user), data: AdminVoiceData = Depends(_voice_data),
):
    result = await invoke_admin_operation(current_user, data.update, request.domain_input(voice_id), error_handler=_voice_error("update"))
    if not result.changed:
        raise HTTPException(status_code=404, detail="Voice not found or permission denied")
    return {"success": True}


@_voice_router.delete("/api/voices/{voice_id}")
async def delete_voice(voice_id: str, current_user: dict = Depends(get_current_user), data: AdminVoiceData = Depends(_voice_data)):
    result = await invoke_admin_operation(current_user, data.delete, VoiceIdInputDTO(voice_id=voice_id), error_handler=_voice_error("delete"))
    if not result.changed:
        raise HTTPException(status_code=404, detail="Voice not found or permission denied")
    return {"success": True}


@_voice_router.post("/api/voices/{voice_id}/fork")
async def fork_voice(
    voice_id: str, request: VoiceForkRequest, current_user: dict = Depends(get_current_user), data: AdminVoiceData = Depends(_voice_data),
):
    result = await invoke_admin_operation(current_user, data.collect, VoiceCollectInputDTO(voice_id=voice_id, target_deck_id=request.target_deck_id), error_handler=_voice_error("collect", voice_id))
    return result.model_dump()


router.include_router(_voice_router)
