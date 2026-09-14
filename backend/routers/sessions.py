#!/usr/bin/env python3
# [Input] Consume typed Admin Session APIs, edit-session events, and shared explicit actor/date helpers.
# [Output] Register /api/sessions* endpoints and session event stream.
# [Pos] session route node in backend/routers
# [Sync] 2026-09-15: route all public Session storage through Admin; publish edit events only after confirmed writes.
# [Sync] 2026-05-25: extracted session storage routes from backend/server.py.
# [Sync] 2026-06-14: publish Edit Session update/delete events and expose
#                    /api/sessions/events SSE for frontend Agent-write sync.
# [Sync] 2026-08-31: preserve timezone-correct date_key values when PostgreSQL
#                    returns native datetime objects for writing sessions.

import asyncio
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ValidationError

from session_events import EditSessionEvent, session_event_bus
from services.admin_data import session_models as dto
from services.admin_data.request_auth import AdminRequestAuth
from services.admin_data.session_data import AdminSessionData

from .deps import (
    _clean_timestamp,
    _count_mixed_words,
    _validate_date_str,
    get_admin_request_auth,
    get_current_user,
    invoke_admin_operation,
)

router = APIRouter()


def get_admin_session_data(owner: AdminRequestAuth = Depends(get_admin_request_auth)) -> AdminSessionData:
    return AdminSessionData(owner.client)


def _session_input(schema, **values):
    try:
        return schema.model_validate(values)
    except ValidationError:
        raise HTTPException(status_code=400, detail="Invalid session input") from None


class SessionBatchRequest(BaseModel):
    ids: List[str]


@router.post("/api/sessions")
async def save_session(request: dict, current_user: dict = Depends(get_current_user), sessions: AdminSessionData = Depends(get_admin_session_data)):
    """
    Save or update a session.

    Request body:
    {
        "session_id": "string",
        "name": "optional string",
        "editor_state": {...},
        "labels": ["optional", "list", "of", "tags"]
    }
    """
    user_id = current_user["user_id"]
    session_id = request.get("session_id")
    editor_state = request.get("editor_state")
    name = request.get("name")
    labels = request.get("labels")

    if not session_id or not editor_state:
        raise HTTPException(
            status_code=400, detail="session_id and editor_state required"
        )

    input_dto = _session_input(dto.SessionSaveInputDTO, session_id=session_id,
        editor_state=editor_state, name=name, labels=labels, created_at=None)
    await invoke_admin_operation(current_user, sessions.save, input_dto)
    asyncio.create_task(
        session_event_bus.publish(
            EditSessionEvent(
                type="session_updated",
                session_id=session_id,
                user_id=str(user_id),
                source="api",
            )
        )
    )

    return {"success": True}


@router.get("/api/sessions/events")
async def session_events(current_user: dict = Depends(get_current_user)):
    """Stream authenticated Edit Session persistence events for the current user."""

    user_id = str(current_user["user_id"])
    return StreamingResponse(
        session_event_bus.read(user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/sessions")
async def list_sessions(
    timezone: str = "Asia/Shanghai", current_user: dict = Depends(get_current_user),
    sessions: AdminSessionData = Depends(get_admin_session_data),
):
    """
    List all sessions for current user.
    Returns: Array of session metadata (without full editor state) plus local day key + first line.
    """
    return await list_sessions_with_range(None, None, timezone, current_user, sessions)


@router.get("/api/sessions/range")
async def list_sessions_with_range(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    timezone: str = "Asia/Shanghai",
    current_user: dict = Depends(get_current_user),
    sessions: AdminSessionData = Depends(get_admin_session_data),
):
    """
    List sessions within an optional date range.
    """
    start_date = _validate_date_str(start_date)
    end_date = _validate_date_str(end_date)
    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(timezone)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid timezone")

    result = await invoke_admin_operation(current_user, sessions.list,
        _session_input(dto.SessionListInputDTO, start_date=start_date, end_date=end_date, include_text=False))

    enriched = []
    for item in result.sessions:
        s = item.model_dump(exclude={"text"})
        dt = _clean_timestamp(s.get("created_at") or s.get("updated_at"))
        date_key = dt.astimezone(tz).strftime("%Y-%m-%d") if dt else None
        enriched.append({**s, "date_key": date_key})

    return {"sessions": enriched}


@router.post("/api/sessions/batch")
async def get_sessions_batch(
    payload: SessionBatchRequest, current_user: dict = Depends(get_current_user),
    sessions: AdminSessionData = Depends(get_admin_session_data),
):
    """
    Fetch multiple sessions (with editor_state) in a single request.
    """
    session_ids = payload.ids or []

    if not session_ids:
        return {"sessions": []}

    result = await invoke_admin_operation(current_user, sessions.batch,
        _session_input(dto.SessionBatchInputDTO, session_ids=session_ids))
    return result.model_dump()


@router.get("/api/sessions/aggregate")
async def get_sessions_aggregate(
    timezone: str = "Asia/Shanghai", current_user: dict = Depends(get_current_user),
    sessions: AdminSessionData = Depends(get_admin_session_data),
):
    """
    Aggregate stats across all sessions for the user.
    Returns stats only (no concatenated text) and per-session summaries.
    """

    total_entries = 0
    total_words = 0
    days = set()

    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(timezone)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid timezone")

    result = await invoke_admin_operation(current_user, sessions.text_list, dto.SessionTextListInputDTO())
    records = [item.model_dump() for item in result.sessions]

    for s in records:
        text = s.get("text", "") or ""
        if text.strip():
            total_entries += 1
            total_words += _count_mixed_words(text)
        ts_raw = s.get("updated_at") or s.get("created_at")
        if ts_raw:
            try:
                cleaned = ts_raw.replace("Z", "+00:00")
                if "T" not in cleaned and " " in cleaned:
                    cleaned = cleaned.replace(" ", "T")
                dt = datetime.fromisoformat(cleaned)
                local_dt = dt.astimezone(tz)
                days.add(local_dt.strftime("%Y-%m-%d"))
            except Exception:
                continue

    stats = {
        "total_days": len(days),
        "total_entries": total_entries,
        "total_words": total_words,
    }

    summaries = [
        {
            "id": s["id"],
            "name": s.get("name"),
            "created_at": s.get("created_at"),
            "updated_at": s.get("updated_at"),
            "has_text": bool((s.get("text") or "").strip()),
            "word_count": len((s.get("text") or "").split()) if s.get("text") else 0,
        }
        for s in records
    ]

    return {
        "stats": stats,
        "sessions": summaries,
        "timezone": timezone,
    }


@router.get("/api/sessions/{session_id}")
async def get_session(session_id: str, current_user: dict = Depends(get_current_user), sessions: AdminSessionData = Depends(get_admin_session_data)):
    """
    Get a specific session by ID.

    Returns: Full session including editor_state
    """
    result = await invoke_admin_operation(current_user, sessions.get,
        _session_input(dto.SessionIdInputDTO, session_id=session_id))
    session = result.session

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session.model_dump()


@router.delete("/api/sessions/{session_id}")
async def delete_session_endpoint(
    session_id: str, current_user: dict = Depends(get_current_user),
    sessions: AdminSessionData = Depends(get_admin_session_data),
):
    """Delete a session."""
    user_id = current_user["user_id"]
    await invoke_admin_operation(current_user, sessions.delete,
        _session_input(dto.SessionIdInputDTO, session_id=session_id))
    asyncio.create_task(
        session_event_bus.publish(
            EditSessionEvent(
                type="session_deleted",
                session_id=session_id,
                user_id=str(user_id),
                source="api",
            )
        )
    )
    return {"success": True}
