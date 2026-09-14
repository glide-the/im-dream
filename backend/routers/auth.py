#!/usr/bin/env python3
# [Input] Typed Admin current-user identity and standalone legacy data-import requests.
# [Output] Current profile/import routes and explicit 410 for retired password/local-cookie authority.
# [Pos] Auth product adapter; Admin/BFF alone execute login, account creation and session revocation.
# [Sync] 2026-09-14: stop local JWT/refresh issuance; preserve typed profile and independent imports.

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

import database

from services.admin_data.errors import AdminDataError
from services.admin_data.retired_auth import retired_authentication
from services.admin_data.request_auth import AdminRequestActor, AdminRequestAuth
from .deps import get_admin_request_auth, get_current_user

router = APIRouter()


class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    token: str


class ImportDataRequest(BaseModel):
    currentSession: Optional[str] = None
    calendarEntries: Optional[str] = None
    dailyPictures: Optional[str] = None
    voiceCustomizations: Optional[str] = None
    metaPrompt: Optional[str] = None
    stateConfig: Optional[str] = None
    selectedState: Optional[str] = None
    analysisReports: Optional[str] = None
    oldDocument: Optional[str] = None


@router.post("/api/register")
def register():
    """Retired password registration; Admin alone owns account creation."""
    return retired_authentication()


@router.post("/api/login")
def login():
    """Retired password authentication; never parse or forward the body."""
    return retired_authentication()


def _serialize_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "display_name": user["display_name"],
        "avatar_url": user.get("avatar_url"),
        "role": user.get("role", "user"),
        "created_at": user["created_at"],
    }


def _get_current_user_info(current_user: dict, owner: AdminRequestAuth, request_id: str) -> dict:
    actor = current_user.get("_admin_actor")
    if not isinstance(actor, AdminRequestActor):
        raise HTTPException(status_code=503, detail="ADMIN_CONFIGURATION_INVALID")
    try:
        return owner.current_profile(actor, request_id).dream_public_profile()
    except AdminDataError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from None


@router.get("/api/me")
async def get_current_user_info(
    request: Request,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
):
    """
    Get current user info from token.

    Requires an Admin OAuth bearer; browser BFF injects it after handle resolution.
    """
    return await run_in_threadpool(_get_current_user_info, current_user, owner, request.state.admin_request_id)


@router.get("/auth/me")
async def get_auth_current_user_info(
    request: Request,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
):
    """Alias for OAuth-oriented clients."""
    return await run_in_threadpool(_get_current_user_info, current_user, owner, request.state.admin_request_id)


@router.post("/auth/logout")
def logout():
    """Retired local refresh-cookie logout; Next BFF revokes its Admin handle."""
    return retired_authentication()


@router.post("/api/import-local-data")
def import_local_data(
    request: ImportDataRequest, current_user: dict = Depends(get_current_user)
):
    """
    Import localStorage data to database on first login.

    Extracts sessions, pictures, preferences, and reports from localStorage export.
    """
    import json

    user_id = current_user["user_id"]

    print(f"\n🔍 Migration request for user {user_id}:")
    print(
        f"  - currentSession: {len(request.currentSession) if request.currentSession else 0} chars"
    )
    print(
        f"  - calendarEntries: {len(request.calendarEntries) if request.calendarEntries else 0} chars"
    )
    print(
        f"  - dailyPictures: {len(request.dailyPictures) if request.dailyPictures else 0} chars"
    )
    print(
        f"  - oldDocument: {len(request.oldDocument) if request.oldDocument else 0} chars"
    )

    sessions = []

    if request.currentSession:
        try:
            current = json.loads(request.currentSession)
            sessions.append(
                {
                    "id": "current-session",
                    "name": "Current Session",
                    "editor_state": current,
                }
            )
            print(f"✅ Imported current session ({len(str(current))} chars)")
        except Exception as e:
            print(f"❌ Failed to parse current session: {e}")

    if request.calendarEntries:
        try:
            calendar = json.loads(request.calendarEntries)
            print(f"📅 Parsed calendar with {len(calendar)} dates")
            for date, entries in calendar.items():
                print(f"  - {date}: {len(entries)} entries")
                for entry in entries:
                    sessions.append(
                        {
                            "id": entry["id"],
                            "name": f"{date} - {entry.get('firstLine', 'Untitled')}",
                            "editor_state": entry["state"],
                        }
                    )
        except Exception as e:
            print(f"❌ Failed to parse calendar entries: {e}")
            import traceback

            traceback.print_exc()

    if request.oldDocument:
        try:
            old_doc = json.loads(request.oldDocument)
            if old_doc and old_doc.get("document"):
                sessions.append(
                    {
                        "id": "old-document",
                        "name": "Old Document (migrated)",
                        "editor_state": {
                            "cells": [{"type": "text", "content": str(old_doc)}]
                        },
                    }
                )
        except Exception:
            pass

    pictures = []
    if request.dailyPictures:
        try:
            pics = json.loads(request.dailyPictures)
            for pic in pics:
                pictures.append(
                    {
                        "date": pic["date"],
                        "image_base64": pic["base64"],
                        "prompt": pic.get("prompt", ""),
                    }
                )
        except Exception:
            pass

    preferences = {}
    if request.voiceCustomizations:
        try:
            preferences["voice_configs"] = json.loads(request.voiceCustomizations)
        except Exception:
            pass

    if request.metaPrompt:
        preferences["meta_prompt"] = request.metaPrompt

    if request.stateConfig:
        try:
            preferences["state_config"] = json.loads(request.stateConfig)
        except Exception:
            pass

    if request.selectedState:
        preferences["selected_state"] = request.selectedState

    reports = []
    if request.analysisReports:
        try:
            report_list = json.loads(request.analysisReports)
            for report in report_list:
                reports.append(
                    {
                        "type": report.get("type", "unknown"),
                        "data": report.get("data", {}),
                        "allNotes": report.get("allNotes", ""),
                        "timestamp": report.get("timestamp", ""),
                    }
                )
        except Exception:
            pass

    database.import_user_data(user_id, sessions, pictures, preferences, reports)

    return {
        "success": True,
        "imported": {
            "sessions": len(sessions),
            "pictures": len(pictures),
            "preferences": len([k for k, v in preferences.items() if v]),
            "reports": len(reports),
        },
    }


@router.post("/api/import-calendar-recovery")
def import_calendar_recovery(
    request: dict, current_user: dict = Depends(get_current_user)
):
    """
    Recovery endpoint to import calendar entries that were missed in initial migration.

    Request body:
    {
        "calendarEntries": "{\"2025-11-01\": [...]}"  # JSON string
    }
    """
    import json

    user_id = current_user["user_id"]
    calendar_json = request.get("calendarEntries")

    if not calendar_json:
        raise HTTPException(status_code=400, detail="calendarEntries required")

    sessions = []
    try:
        calendar = json.loads(calendar_json)
        print(f"📅 Recovery import: {len(calendar)} dates")
        for date, entries in calendar.items():
            print(f"  - {date}: {len(entries)} entries")
            for entry in entries:
                sessions.append(
                    {
                        "id": entry["id"],
                        "name": f"{date} - {entry.get('firstLine', 'Untitled')}",
                        "editor_state": entry["state"],
                    }
                )
    except Exception as e:
        print(f"❌ Failed to parse calendar: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=400, detail=f"Failed to parse calendar: {str(e)}"
        )

    database.import_user_data(user_id, sessions, [], {}, [])

    return {"success": True, "imported": {"sessions": len(sessions)}}


@router.post("/api/mark-first-login-completed")
def mark_first_login_completed(current_user: dict = Depends(get_current_user)):
    """
    Mark user's first login as completed.
    Called after migration dialog is shown (migrate or skip).
    """
    user_id = current_user["user_id"]
    database.set_first_login_completed(user_id)
    return {"success": True}
