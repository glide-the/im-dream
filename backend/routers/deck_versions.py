"""Authenticated Deck content-version state, preview, commit, and history routes.

[Input] Original public version DTOs, explicit Admin request actor and typed domain consumer.
[Output] Existing `/api/decks/{id}/versions*` responses with safe CAS and unknown-result errors.
[Pos] Public Deck version boundary; Admin owns snapshots, hashes, CAS and durable transactions.
[Sync] 2026-09-15: replace public Dream PG service creation with five capability-gated Admin operations.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .deps import get_current_user, invoke_admin_operation
from models.deck_version import (
    DeckVersionCommitRequest, DeckVersionCommitResponse, DeckVersionDetailResponse,
    DeckVersionHistoryResponse, DeckVersionMutationRequest, DeckVersionPreviewResponse,
    DeckVersionState,
)
from services.admin_data.deck_version_data import AdminDeckVersionData
from services.admin_data import deck_version_models as dto
from services.admin_data.errors import AdminDataError
from services.admin_data.request_auth import AdminRequestAuth

router = APIRouter(prefix="/api/decks", tags=["deck-content-versions"])


def _data(request: Request) -> AdminDeckVersionData:
    owner = getattr(request.app.state, "admin_request_auth", None)
    if not isinstance(owner, AdminRequestAuth):
        raise HTTPException(status_code=503, detail="ADMIN_CONFIGURATION_INVALID")
    return AdminDeckVersionData(owner.client)


def _error(exc: AdminDataError, request_id: str) -> JSONResponse:
    messages = {
        "DECK_VERSION_CONFLICT": "Deck draft changed. Refresh the preview before committing.",
        "DECK_VERSION_NO_CHANGES": "Deck content has no changes to commit.",
        "DECK_VERSION_ACCESS_DENIED": "Deck not found or permission denied.",
        "DECK_VERSION_NOT_FOUND": "Deck version not found or permission denied.",
        "ADMIN_CAPABILITY_UNAVAILABLE": "Deck content version capability is not available.",
    }
    content = {"error_code": exc.code, "message": messages.get(exc.code, "Deck operation could not be completed."),
        "request_id": exc.request_id or request_id, "outcome_unknown": exc.outcome_unknown}
    if exc.details is not None:
        content.update(exc.details.model_dump())
    return JSONResponse(status_code=exc.status_code, content=content)


async def _invoke(current_user: dict[str, Any], method, input_dto):
    return await invoke_admin_operation(current_user, method, input_dto, error_handler=_error)


def _input(model, **values):
    try:
        return model(**values)
    except ValidationError:
        raise HTTPException(status_code=422, detail="Invalid Deck version input") from None


@router.get("/{deck_id}/version-state", response_model=DeckVersionState)
async def get_version_state(deck_id: str, current_user: dict[str, Any] = Depends(get_current_user), data: AdminDeckVersionData = Depends(_data)):
    result = await _invoke(current_user, data.state, _input(dto.DeckIdInputDTO, deck_id=deck_id))
    return result if isinstance(result, JSONResponse) else result.model_dump()


@router.post("/{deck_id}/versions/preview", response_model=DeckVersionPreviewResponse)
async def preview_version(deck_id: str, request: DeckVersionMutationRequest,
    current_user: dict[str, Any] = Depends(get_current_user), data: AdminDeckVersionData = Depends(_data)):
    result = await _invoke(current_user, data.preview, _input(dto.DeckVersionMutationInputDTO, deck_id=deck_id, **request.model_dump()))
    return result if isinstance(result, JSONResponse) else result.model_dump()


@router.post("/{deck_id}/versions", response_model=DeckVersionCommitResponse)
async def commit_version(deck_id: str, request: DeckVersionCommitRequest,
    current_user: dict[str, Any] = Depends(get_current_user), data: AdminDeckVersionData = Depends(_data)):
    result = await _invoke(current_user, data.commit, _input(dto.DeckVersionCommitInputDTO, deck_id=deck_id, **request.model_dump()))
    if isinstance(result, JSONResponse):
        return result
    projection = result.model_dump()
    projection["version"]["created_by"] = int(result.version.created_by)
    return projection


@router.get("/{deck_id}/versions", response_model=DeckVersionHistoryResponse)
async def list_versions(deck_id: str, limit: int = Query(default=50, ge=1, le=100),
    current_user: dict[str, Any] = Depends(get_current_user), data: AdminDeckVersionData = Depends(_data)):
    result = await _invoke(current_user, data.history, _input(dto.DeckVersionHistoryInputDTO, deck_id=deck_id, limit=limit))
    if isinstance(result, JSONResponse):
        return result
    projection = result.model_dump()
    for version in projection["versions"]:
        version["created_by"] = int(version["created_by"])
    return projection


@router.get("/{deck_id}/versions/{version}", response_model=DeckVersionDetailResponse)
async def get_version(deck_id: str, version: int = Path(ge=1, le=9_007_199_254_740_991),
    current_user: dict[str, Any] = Depends(get_current_user), data: AdminDeckVersionData = Depends(_data)):
    result = await _invoke(current_user, data.detail, _input(dto.DeckVersionDetailInputDTO, deck_id=deck_id, version=version))
    return result if isinstance(result, JSONResponse) else result.public_projection()
