#!/usr/bin/env python3
# [Input] Registry103 picture-history reads and shared OAuth/date helpers.
# [Output] Preserve the three read-only /api/pictures* public projections.
# [Pos] Picture route adapter; Admin owns current-user history persistence and selection.
# [Sync] 2026-09-15: replace three Dream database reads with strict Registry103 consumers.
# [Sync] 2026-05-25: extracted picture routes from backend/server.py.
# [Sync] 2026-08-31: remove generation/save endpoints; historical picture reads remain.

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from services.admin_data.picture_history_data import (
    AdminPictureHistoryData,
    PictureHistoryFullInputDTO,
    PictureHistoryListInputDTO,
    PictureHistoryListOutputDTO,
    require_iso_date,
)
from services.admin_data.request_auth import AdminRequestAuth

from .deps import _validate_date_str, get_current_user, invoke_admin_operation

router = APIRouter()
PictureLimit = Annotated[int, Query(ge=0, le=9_007_199_254_740_991)]


def _picture_history(request: Request) -> AdminPictureHistoryData:
    owner = getattr(request.app.state, "admin_request_auth", None)
    if not isinstance(owner, AdminRequestAuth):
        raise HTTPException(status_code=503, detail="ADMIN_CONFIGURATION_INVALID")
    return AdminPictureHistoryData(owner.client)


def _picture_rows(
    result: PictureHistoryListOutputDTO,
    *,
    empty_prompt: bool,
) -> list[dict]:
    pictures = [item.model_dump() for item in result.pictures]
    if empty_prompt:
        for picture in pictures:
            picture["prompt"] = picture["prompt"] or ""
    return pictures


def _picture_date(value: str | None) -> str | None:
    normalized = _validate_date_str(value)
    if normalized is None:
        return None
    try:
        return require_iso_date(normalized)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format, expected YYYY-MM-DD",
        ) from None


@router.get("/api/pictures")
async def get_pictures(
    limit: PictureLimit = 30,
    current_user: dict = Depends(get_current_user),
    data: AdminPictureHistoryData = Depends(_picture_history),
):
    """
    Get recent daily pictures for current user (thumbnails only for fast loading).

    Query params:
    - limit: Max number of pictures to return (default 30)
    """
    result = await invoke_admin_operation(
        current_user,
        data.list,
        PictureHistoryListInputDTO(
            start_date=None,
            end_date=None,
            limit=limit,
        ),
    )
    return {"pictures": _picture_rows(result, empty_prompt=True)}


@router.get("/api/pictures/range")
async def get_pictures_range(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: PictureLimit = 30,
    current_user: dict = Depends(get_current_user),
    data: AdminPictureHistoryData = Depends(_picture_history),
):
    """
    Get daily pictures within an optional date range.
    """
    start_date = _picture_date(start_date)
    end_date = _picture_date(end_date)
    result = await invoke_admin_operation(
        current_user,
        data.list,
        PictureHistoryListInputDTO(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        ),
    )
    return {"pictures": _picture_rows(result, empty_prompt=False)}


@router.get("/api/pictures/{date}/full")
async def get_picture_full(
    date: str,
    current_user: dict = Depends(get_current_user),
    data: AdminPictureHistoryData = Depends(_picture_history),
):
    """
    Get full resolution image for a specific date (on-demand loading).

    Path params:
    - date: Date in YYYY-MM-DD format
    """
    normalized_date = _picture_date(date)
    if normalized_date is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format, expected YYYY-MM-DD",
        )
    result = await invoke_admin_operation(
        current_user,
        data.full,
        PictureHistoryFullInputDTO(date=normalized_date),
    )

    if not result.image_base64:
        raise HTTPException(status_code=404, detail="Picture not found for this date")

    return {"image_base64": result.image_base64}
