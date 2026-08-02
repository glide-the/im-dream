"""Authenticated Deck Plugin binding, options, and validation endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator
import sqlite3
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

import database
from services.story_workspace.agent_integration import get_or_create_default_workspace

from .deps import get_current_user

try:
    from backend.models.deck_plugin import (
        DeckPluginBindingResponse,
        DeckPluginBindingState,
        DeckPluginBindingUpdateRequest,
        DeckPluginOptionsResponse,
        DeckPluginSelectionRequest,
        DeckPluginSelectionValidationResponse,
    )
    from backend.services.deck_plugin.binding_service import (
        BindingAccessError,
        BindingRevisionConflict,
        BindingSelectionRejected,
        BindingService,
    )
    from backend.services.deck_plugin.selection_validation_service import (
        SelectionValidationService,
    )
    from backend.services.deck.runtime_context import make_runtime_context_resolver
except ModuleNotFoundError:  # Support the backend directory on PYTHONPATH.
    from models.deck_plugin import (
        DeckPluginBindingResponse,
        DeckPluginBindingState,
        DeckPluginBindingUpdateRequest,
        DeckPluginOptionsResponse,
        DeckPluginSelectionRequest,
        DeckPluginSelectionValidationResponse,
    )
    from services.deck_plugin.binding_service import (
        BindingAccessError,
        BindingRevisionConflict,
        BindingSelectionRejected,
        BindingService,
    )
    from services.deck_plugin.selection_validation_service import (
        SelectionValidationService,
    )
    from services.deck.runtime_context import make_runtime_context_resolver


router = APIRouter(prefix="/api/voice-decks", tags=["deck-plugin-binding"])


async def _binding_db() -> AsyncIterator[sqlite3.Connection]:
    db = database.get_db()
    try:
        yield db
    finally:
        db.close()


def _selection_service(
    db: sqlite3.Connection = Depends(_binding_db),
) -> SelectionValidationService:
    return SelectionValidationService(
        db,
        runtime_context_resolver=make_runtime_context_resolver(db),
    )


def _binding_service(
    db: sqlite3.Connection = Depends(_binding_db),
    validator: SelectionValidationService = Depends(_selection_service),
) -> BindingService:
    return BindingService(db, selection_validator=validator)


def _actor_id(current_user: dict[str, Any]) -> str:
    return str(current_user["user_id"])


def _requested_workspace(current_user: dict[str, Any]) -> str | None:
    workspace_id = current_user.get("workspace_id")
    return str(workspace_id) if workspace_id else None


async def _deck_current_user(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Ensure Deck binding always has the authenticated user's default workspace."""
    if current_user.get("workspace_id"):
        return current_user
    db = database.get_db()
    try:
        workspace_id = get_or_create_default_workspace(db, int(current_user["user_id"]))
    finally:
        db.close()
    return {**current_user, "workspace_id": workspace_id}


def _access_denied() -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "error_code": "DECK_ACCESS_DENIED",
            "message": "Deck not found or permission denied.",
        },
    )


@router.get(
    "/{deck_id}/plugin-options",
    response_model=DeckPluginOptionsResponse,
)
async def get_plugin_options(
    deck_id: str,
    current_user: dict[str, Any] = Depends(_deck_current_user),
    binding: BindingService = Depends(_binding_service),
    validator: SelectionValidationService = Depends(_selection_service),
):
    actor_id = _actor_id(current_user)
    try:
        workspace_id = binding.resolve_workspace_access(
            deck_id=deck_id,
            actor_id=actor_id,
            requested_workspace_id=_requested_workspace(current_user),
        )
    except BindingAccessError:
        return _access_denied()
    return await validator.list_options(
        deck_id=deck_id,
        workspace_id=workspace_id,
        actor_id=actor_id,
    )


@router.get(
    "/{deck_id}/plugin-binding",
    response_model=DeckPluginBindingState,
)
async def get_plugin_binding(
    deck_id: str,
    current_user: dict[str, Any] = Depends(_deck_current_user),
    binding: BindingService = Depends(_binding_service),
):
    try:
        return await binding.get_current_state(
            deck_id=deck_id,
            actor_id=_actor_id(current_user),
            requested_workspace_id=_requested_workspace(current_user),
        )
    except BindingAccessError:
        return _access_denied()


@router.put(
    "/{deck_id}/plugin-binding",
    response_model=DeckPluginBindingResponse,
)
async def put_plugin_binding(
    deck_id: str,
    request: DeckPluginBindingUpdateRequest,
    current_user: dict[str, Any] = Depends(_deck_current_user),
    binding: BindingService = Depends(_binding_service),
):
    try:
        return await binding.save(
            deck_id=deck_id,
            actor_id=_actor_id(current_user),
            request=request,
            requested_workspace_id=_requested_workspace(current_user),
        )
    except BindingAccessError:
        return _access_denied()
    except BindingRevisionConflict as exc:
        return JSONResponse(
            status_code=409,
            content={
                "error_code": exc.code,
                "current_revision": exc.current_revision,
                "message": str(exc),
            },
        )
    except BindingSelectionRejected as exc:
        return JSONResponse(
            status_code=422,
            content={
                "error_code": exc.validation.reason_code,
                "message": str(exc),
                "validation": exc.validation.model_dump(mode="json"),
            },
        )


@router.post(
    "/{deck_id}/plugin-binding/validate",
    response_model=DeckPluginSelectionValidationResponse,
)
async def validate_plugin_binding(
    deck_id: str,
    request: DeckPluginSelectionRequest,
    current_user: dict[str, Any] = Depends(_deck_current_user),
    binding: BindingService = Depends(_binding_service),
    validator: SelectionValidationService = Depends(_selection_service),
):
    actor_id = _actor_id(current_user)
    try:
        workspace_id = binding.resolve_workspace_access(
            deck_id=deck_id,
            actor_id=actor_id,
            requested_workspace_id=_requested_workspace(current_user),
        )
    except BindingAccessError:
        return _access_denied()
    validation = await validator.validate(
        deck_plugin_id=request.deck_plugin_id,
        deck_plugin_version=request.deck_plugin_version,
        workspace_id=workspace_id,
        actor_id=actor_id,
    )
    return DeckPluginSelectionValidationResponse(
        deck_id=deck_id,
        deck_plugin_id=request.deck_plugin_id,
        deck_plugin_version=request.deck_plugin_version,
        validation=validation,
    )
