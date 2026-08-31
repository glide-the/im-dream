#!/usr/bin/env python3
# [Input] Consume database picture reads and shared auth/date helpers.
# [Output] Register read-only /api/pictures* endpoints for historical images.
# [Pos] picture route node in backend/routers
# [Sync] 2026-05-25: extracted picture routes from backend/server.py.
# [Sync] 2026-08-31: remove generation/save endpoints; historical picture reads remain.

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
import database

from .deps import _validate_date_str, get_current_user

router = APIRouter()


@router.get("/api/pictures")
def get_pictures(limit: int = 30, current_user: dict = Depends(get_current_user)):
    """
    Get recent daily pictures for current user (thumbnails only for fast loading).

    Query params:
    - limit: Max number of pictures to return (default 30)
    """
    user_id = current_user["user_id"]
    pictures = database.get_daily_pictures(user_id, limit)
    return {"pictures": pictures}


@router.get("/api/pictures/range")
def get_pictures_range(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 30,
    current_user: dict = Depends(get_current_user),
):
    """
    Get daily pictures within an optional date range.
    """
    user_id = current_user["user_id"]
    start_date = _validate_date_str(start_date)
    end_date = _validate_date_str(end_date)
    pictures = database.get_daily_pictures_range(user_id, start_date, end_date, limit)
    return {"pictures": pictures}


@router.get("/api/pictures/{date}/full")
def get_picture_full(date: str, current_user: dict = Depends(get_current_user)):
    """
    Get full resolution image for a specific date (on-demand loading).

    Path params:
    - date: Date in YYYY-MM-DD format
    """
    user_id = current_user["user_id"]
    full_image = database.get_daily_picture_full(user_id, date)

    if not full_image:
        raise HTTPException(status_code=404, detail="Picture not found for this date")

    return {"image_base64": full_image}
