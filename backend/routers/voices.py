#!/usr/bin/env python3
# [Sync] 2026-09-15: both public Deck list modes use Admin without default or filesystem side effects.
# [Sync] 2026-09-15: public Deck detail uses Admin; legacy Memory projection remains pure and shared.
# [Sync] 2026-09-15: four public Voice operations use Admin; Deck chat-context/internal data remains pending.
# [Sync] 2026-09-15: five public Deck mutations use Admin; deletion keeps code-owned closed dependency messages.
# [Sync] 2026-09-15: Deck create/default reconcile use Registry104 plus Dream's shared-artifact verifier.
# [Input] Consume typed Admin public Deck/Voice operations, the local Deck-default verifier and shared auth dependency.
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

import database
import config

try:
    from services.deck.defaults import (
        DefaultDeckPluginUnavailable,
        resolve_default_deck_plugin_ref,
    )
except ModuleNotFoundError:  # pragma: no cover - package import compatibility
    from backend.services.deck.defaults import (
        DefaultDeckPluginUnavailable,
        resolve_default_deck_plugin_ref,
    )

from services.admin_data.chat_models import ChatStrictDTO
from services.admin_data.deck_default_data import (
    AdminDeckDefaultData,
    DeckCreateInputDTO,
    DeckDefaultInputDTO,
    DefaultPluginEvidenceDTO,
    DefaultPluginResolveInputDTO,
)
from services.admin_data.deck_mutation_data import AdminDeckMutationData, DeckUpdateRequestDTO
from services.admin_data.deck_detail_data import AdminDeckDetailData
from services.admin_data.deck_list_data import AdminDeckListData, DeckListInputDTO
from services.admin_data.deck_version_models import DeckIdInputDTO
from services.admin_data.models import DeckDeleteBlockedDetailsDTO
from services.admin_data.voice_data import (
    AdminVoiceData, VoiceCollectInputDTO, VoiceCreateRequestDTO, VoiceForkRequestDTO,
    VoiceIdInputDTO, VoiceUpdateRequestDTO,
)
from services.admin_data.request_auth import AdminRequestAuth
from .deps import SafeRequestValidationRoute, get_current_user, invoke_admin_operation


class _DeckRoute(SafeRequestValidationRoute):
    validation_error_detail = "Invalid Deck request"


router = APIRouter(route_class=_DeckRoute)


class DeckCreateRequest(ChatStrictDTO):
    name: str
    description: str | None = None
    name_zh: str | None = None
    name_en: str | None = None
    description_zh: str | None = None
    description_en: str | None = None
    icon: str | None = None
    color: str | None = None

    def domain_input(self, evidence: DefaultPluginEvidenceDTO) -> DeckCreateInputDTO:
        return DeckCreateInputDTO(
            **self.model_dump(),
            order_index=None,
            default_plugin_evidence=evidence,
        )


DeckUpdateRequest = DeckUpdateRequestDTO


VoiceCreateRequest = VoiceCreateRequestDTO
VoiceUpdateRequest = VoiceUpdateRequestDTO
VoiceForkRequest = VoiceForkRequestDTO


def _deck_list_data(request: Request) -> AdminDeckListData:
    owner = getattr(request.app.state, "admin_request_auth", None)
    if not isinstance(owner, AdminRequestAuth):
        raise HTTPException(status_code=503, detail="ADMIN_CONFIGURATION_INVALID")
    return AdminDeckListData(owner.client)


@router.get("/api/decks")
async def list_decks(published: bool = False, current_user: dict = Depends(get_current_user), data: AdminDeckListData = Depends(_deck_list_data)):
    """Read actor Decks or the collectable community aggregate through Admin."""
    return await invoke_admin_operation(current_user, data.list, DeckListInputDTO(community=published))


def _deck_default_data(request: Request) -> AdminDeckDefaultData:
    owner = getattr(request.app.state, "admin_request_auth", None)
    if not isinstance(owner, AdminRequestAuth):
        raise HTTPException(status_code=503, detail="ADMIN_CONFIGURATION_INVALID")
    return AdminDeckDefaultData(owner.client)


def _default_deck_plugin_unavailable() -> HTTPException:
    return HTTPException(
        status_code=409,
        detail=(
            "Default Deck plugin "
            f"{config.DEFAULT_DECK_CLAUDE_PLUGIN_PACKAGE_NAME} "
            f"v{config.DEFAULT_DECK_CLAUDE_PLUGIN_VERSION} is unavailable"
        ),
    )


def _deck_default_error(exc, request_id):
    if (
        not exc.outcome_unknown
        and exc.status_code == 409
        and exc.code == "DEFAULT_DECK_PLUGIN_UNAVAILABLE"
    ):
        raise _default_deck_plugin_unavailable()
    raise HTTPException(
        status_code=exc.status_code,
        detail={
            "error_code": exc.code,
            "request_id": exc.request_id or request_id,
            "outcome_unknown": exc.outcome_unknown,
        },
    )


async def _verified_default_plugin(
    current_user: dict,
    data: AdminDeckDefaultData,
) -> DefaultPluginEvidenceDTO:
    resolved = await invoke_admin_operation(
        current_user,
        data.resolve,
        DefaultPluginResolveInputDTO(),
    )
    try:
        return resolve_default_deck_plugin_ref(resolved.installation)
    except DefaultDeckPluginUnavailable:
        raise _default_deck_plugin_unavailable() from None


@router.post("/api/decks/defaults/reconcile")
async def reconcile_deck_defaults(
    current_user: dict = Depends(get_current_user),
    data: AdminDeckDefaultData = Depends(_deck_default_data),
):
    """Create a missing actor default or repair its empty verified plugin ref."""

    evidence = await _verified_default_plugin(current_user, data)
    return await invoke_admin_operation(
        current_user,
        data.reconcile,
        DeckDefaultInputDTO(default_plugin_evidence=evidence),
        error_handler=_deck_default_error,
    )


def _deck_detail_data(request: Request) -> AdminDeckDetailData:
    owner = getattr(request.app.state, "admin_request_auth", None)
    if not isinstance(owner, AdminRequestAuth):
        raise HTTPException(status_code=503, detail="ADMIN_CONFIGURATION_INVALID")
    return AdminDeckDetailData(owner.client)


@router.get("/api/decks/{deck_id}")
async def get_deck(deck_id: str, current_user: dict = Depends(get_current_user), data: AdminDeckDetailData = Depends(_deck_detail_data)):
    """Read the owned Deck aggregate through Admin and restore its public fields."""
    deck = await invoke_admin_operation(current_user, data.detail, DeckIdInputDTO(deck_id=deck_id))
    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found")
    return deck


@router.post("/api/decks")
async def create_deck(
    request: DeckCreateRequest,
    current_user: dict = Depends(get_current_user),
    data: AdminDeckDefaultData = Depends(_deck_default_data),
):
    """Create a user Deck with its verified product-default Claude plugin."""
    evidence = await _verified_default_plugin(current_user, data)
    return await invoke_admin_operation(
        current_user,
        data.create,
        request.domain_input(evidence),
        error_handler=_deck_default_error,
    )


_deck_mutation_router = APIRouter(route_class=_DeckRoute)


def _deck_mutation_data(request: Request) -> AdminDeckMutationData:
    owner = getattr(request.app.state, "admin_request_auth", None)
    if not isinstance(owner, AdminRequestAuth):
        raise HTTPException(status_code=503, detail="ADMIN_CONFIGURATION_INVALID")
    return AdminDeckMutationData(owner.client)


def _deck_mutation_error(kind: str, deck_id: str):
    def error(exc, request_id):
        if not exc.outcome_unknown:
            if exc.code == "DECK_DELETE_BLOCKED" and exc.status_code == 409 and kind == "delete":
                reason = exc.details.reason if isinstance(exc.details, DeckDeleteBlockedDetailsDTO) else "referenced_records"
                raise HTTPException(status_code=409, detail=str(database.DeckDeletionConflict(reason)))
            messages = {
                "DEFAULT_DECK_PUBLISH_FORBIDDEN": (409, "System-initialized Decks cannot be published"),
                "SELF_COLLECTION_FORBIDDEN": (409, "You cannot collect your own published Deck"),
                "COLLECTION_SOURCE_UNAVAILABLE": (409, "Only system or published Decks can be collected"),
            }
            expected_kind = "publish" if exc.code == "DEFAULT_DECK_PUBLISH_FORBIDDEN" else "collect"
            if exc.code in messages and kind == expected_kind and exc.status_code in {404, 409}:
                status, message = messages[exc.code]
                raise HTTPException(status_code=status, detail=message)
            if exc.code == "DECK_ACCESS_DENIED" and exc.status_code == 404:
                responses = {"sync": (400, "Deck not found or permission denied"),
                    "publish": (404, "Deck not found or not owned by user"),
                    "collect": (404, f"Deck {deck_id} not found")}
                status, message = responses.get(kind, (404, "Deck not found or permission denied"))
                raise HTTPException(status_code=status, detail=message)
            if exc.code == "DECK_PARENT_MISSING" and kind == "sync" and exc.status_code in {404, 409}:
                raise HTTPException(status_code=400, detail="Deck is not a fork (no parent)" if exc.status_code == 409 else "Parent deck not found")
        raise HTTPException(status_code=exc.status_code, detail={"error_code": exc.code,
            "request_id": exc.request_id or request_id, "outcome_unknown": exc.outcome_unknown})
    return error


@_deck_mutation_router.put("/api/decks/{deck_id}")
async def update_deck(deck_id: str, request: DeckUpdateRequest, current_user: dict = Depends(get_current_user), data: AdminDeckMutationData = Depends(_deck_mutation_data)):
    result = await invoke_admin_operation(current_user, data.update, request.domain_input(deck_id), error_handler=_deck_mutation_error("update", deck_id))
    if not result.changed:
        raise HTTPException(status_code=404, detail="Deck not found or permission denied")
    return {"success": True}


@_deck_mutation_router.delete("/api/decks/{deck_id}")
async def delete_deck(deck_id: str, current_user: dict = Depends(get_current_user), data: AdminDeckMutationData = Depends(_deck_mutation_data)):
    result = await invoke_admin_operation(current_user, data.delete, DeckIdInputDTO(deck_id=deck_id), error_handler=_deck_mutation_error("delete", deck_id))
    if not result.changed:
        raise HTTPException(status_code=404, detail="Deck not found or permission denied")
    return {"success": True}


@_deck_mutation_router.post("/api/decks/{deck_id}/fork")
async def fork_deck(deck_id: str, current_user: dict = Depends(get_current_user), data: AdminDeckMutationData = Depends(_deck_mutation_data)):
    result = await invoke_admin_operation(current_user, data.collect, DeckIdInputDTO(deck_id=deck_id), error_handler=_deck_mutation_error("collect", deck_id))
    return result.model_dump()


@_deck_mutation_router.post("/api/decks/{deck_id}/publish")
async def publish_deck(deck_id: str, current_user: dict = Depends(get_current_user), data: AdminDeckMutationData = Depends(_deck_mutation_data)):
    result = await invoke_admin_operation(current_user, data.publish, DeckIdInputDTO(deck_id=deck_id), error_handler=_deck_mutation_error("publish", deck_id))
    return {"success": True, "published": result.published}


@_deck_mutation_router.post("/api/decks/{deck_id}/sync")
async def sync_deck(deck_id: str, current_user: dict = Depends(get_current_user), data: AdminDeckMutationData = Depends(_deck_mutation_data)):
    result = await invoke_admin_operation(current_user, data.sync, DeckIdInputDTO(deck_id=deck_id), error_handler=_deck_mutation_error("sync", deck_id))
    return result.model_dump()


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


router.include_router(_deck_mutation_router)
router.include_router(_voice_router)
