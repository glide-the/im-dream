"""Authenticated Deck content-version state, preview, commit, and history routes.

[Input] Strict version DTOs, current user, and the Deck content-version service.
[Output] Production `/api/decks/{id}/versions*` endpoints with fail-closed capability/CAS errors.
[Pos] Deck content-version HTTP boundary in backend/routers.
[Sync] 2026-08-16: add explicit draft preview and immutable vN commit routes.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

import database

from .deps import get_current_user

try:
    from backend.models.deck_version import (
        DeckVersionCommitRequest,
        DeckVersionCommitResponse,
        DeckVersionDetailResponse,
        DeckVersionHistoryResponse,
        DeckVersionMutationRequest,
        DeckVersionPreviewResponse,
        DeckVersionState,
    )
    from backend.services.deck.content_versioning import (
        DeckContentVersionService,
        DeckVersionAccessError,
        DeckVersionCapabilityError,
        DeckVersionConflict,
        DeckVersionNoChanges,
    )
except ModuleNotFoundError:  # pragma: no cover - backend PYTHONPATH compatibility
    from models.deck_version import (
        DeckVersionCommitRequest,
        DeckVersionCommitResponse,
        DeckVersionDetailResponse,
        DeckVersionHistoryResponse,
        DeckVersionMutationRequest,
        DeckVersionPreviewResponse,
        DeckVersionState,
    )
    from services.deck.content_versioning import (
        DeckContentVersionService,
        DeckVersionAccessError,
        DeckVersionCapabilityError,
        DeckVersionConflict,
        DeckVersionNoChanges,
    )


router = APIRouter(prefix="/api/decks", tags=["deck-content-versions"])


def _service() -> Iterator[DeckContentVersionService]:
    db = database.get_db()
    try:
        yield DeckContentVersionService(db)
    finally:
        db.close()


def _error(exc: Exception) -> JSONResponse:
    if isinstance(exc, DeckVersionCapabilityError):
        return JSONResponse(
            status_code=503,
            content={
                "error_code": exc.code,
                "message": "Deck content version capability is not available.",
            },
        )
    if isinstance(exc, DeckVersionAccessError):
        return JSONResponse(
            status_code=404,
            content={"error_code": exc.code, "message": "Deck not found or permission denied."},
        )
    if isinstance(exc, DeckVersionConflict):
        return JSONResponse(
            status_code=409,
            content={
                "error_code": exc.code,
                "message": str(exc),
                "current_draft_revision": exc.draft_revision,
                "current_version": exc.latest_version,
            },
        )
    if isinstance(exc, DeckVersionNoChanges):
        return JSONResponse(
            status_code=409,
            content={"error_code": exc.code, "message": str(exc)},
        )
    raise exc


@router.get("/{deck_id}/version-state", response_model=DeckVersionState)
def get_version_state(
    deck_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    service: DeckContentVersionService = Depends(_service),
):
    try:
        return service.get_state(deck_id, int(current_user["user_id"]))
    except (DeckVersionCapabilityError, DeckVersionAccessError) as exc:
        return _error(exc)


@router.post("/{deck_id}/versions/preview", response_model=DeckVersionPreviewResponse)
def preview_version(
    deck_id: str,
    request: DeckVersionMutationRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    service: DeckContentVersionService = Depends(_service),
):
    try:
        return service.preview(deck_id, int(current_user["user_id"]), request)
    except (
        DeckVersionCapabilityError,
        DeckVersionAccessError,
        DeckVersionConflict,
        DeckVersionNoChanges,
    ) as exc:
        return _error(exc)


@router.post("/{deck_id}/versions", response_model=DeckVersionCommitResponse)
def commit_version(
    deck_id: str,
    request: DeckVersionCommitRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    service: DeckContentVersionService = Depends(_service),
):
    try:
        return service.commit(deck_id, int(current_user["user_id"]), request)
    except (
        DeckVersionCapabilityError,
        DeckVersionAccessError,
        DeckVersionConflict,
        DeckVersionNoChanges,
    ) as exc:
        return _error(exc)


@router.get("/{deck_id}/versions", response_model=DeckVersionHistoryResponse)
def list_versions(
    deck_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: dict[str, Any] = Depends(get_current_user),
    service: DeckContentVersionService = Depends(_service),
):
    try:
        return service.list_versions(deck_id, int(current_user["user_id"]), limit=limit)
    except (DeckVersionCapabilityError, DeckVersionAccessError) as exc:
        return _error(exc)


@router.get("/{deck_id}/versions/{version}", response_model=DeckVersionDetailResponse)
def get_version(
    deck_id: str,
    version: int,
    current_user: dict[str, Any] = Depends(get_current_user),
    service: DeckContentVersionService = Depends(_service),
):
    try:
        return service.get_version(deck_id, int(current_user["user_id"]), version)
    except (DeckVersionCapabilityError, DeckVersionAccessError) as exc:
        return _error(exc)

