#!/usr/bin/env python3
# [Input] Typed Admin current-user identity and legacy localStorage import requests.
# [Output] Current profile, Registry101 import/first-login routes and retired local-auth responses.
# [Pos] Auth product adapter; Admin/BFF alone execute login, account creation and session revocation.
# [Sync] 2026-09-15: normalize localStorage categories into Registry101 DTOs and remove Dream database writes.
# [Sync] 2026-09-14: stop local JWT/refresh issuance; preserve typed profile and independent imports.

from datetime import datetime, timedelta, timezone
import json
import logging
from typing import Callable, Optional, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, ValidationError
from starlette.concurrency import run_in_threadpool

from services.admin_data.errors import AdminDataError
from services.admin_data.local_data_import import (
    AdminLocalDataImportData,
    FirstLoginCompleteInputDTO,
    LocalDataImportInputDTO,
    LocalDataPictureDTO,
    LocalDataPreferencesDTO,
    LocalDataReportDTO,
    LocalDataSessionDTO,
    require_json_object_text,
)
from services.admin_data.retired_auth import retired_authentication
from services.admin_data.request_auth import AdminRequestActor, AdminRequestAuth
from .deps import (
    SafeRequestValidationRoute,
    get_admin_request_auth,
    get_current_user,
    invoke_admin_operation,
)


class _AuthRoute(SafeRequestValidationRoute):
    validation_error_detail = "Invalid authentication request"


router = APIRouter(route_class=_AuthRoute)
logger = logging.getLogger(__name__)
_MAX_SAFE_INTEGER = 9_007_199_254_740_991
ParsedT = TypeVar("ParsedT")


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
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        hide_input_in_errors=True,
    )

    currentSession: Optional[str] = None
    calendarEntries: Optional[str] = None
    dailyPictures: Optional[str] = None
    voiceCustomizations: Optional[str] = None
    metaPrompt: Optional[str] = None
    stateConfig: Optional[str] = None
    selectedState: Optional[str] = None
    analysisReports: Optional[str] = None
    oldDocument: Optional[str] = None


class CalendarRecoveryRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        hide_input_in_errors=True,
    )

    calendarEntries: Optional[str] = None


def _local_data(request: Request) -> AdminLocalDataImportData:
    owner = getattr(request.app.state, "admin_request_auth", None)
    if not isinstance(owner, AdminRequestAuth):
        raise HTTPException(status_code=503, detail="ADMIN_CONFIGURATION_INVALID")
    return AdminLocalDataImportData(owner.client)


def _json_object_text(value: object) -> str:
    if not isinstance(value, dict):
        raise ValueError("Legacy value must be an object")
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )


def _parse_category(
    category: str,
    raw: str | None,
    parser: Callable[[str], ParsedT],
    empty: ParsedT,
) -> ParsedT:
    if not raw:
        return empty
    try:
        return parser(raw)
    except (
        KeyError,
        TypeError,
        ValueError,
        OverflowError,
        RecursionError,
        ValidationError,
    ):
        logger.warning("Ignoring malformed local-data category: %s", category)
        return empty


def _current_session(raw: str) -> list[LocalDataSessionDTO]:
    require_json_object_text(raw)
    return [
        LocalDataSessionDTO(
            id="current-session",
            name="Current Session",
            editor_state=raw,
        )
    ]


def _calendar_sessions(raw: str) -> list[LocalDataSessionDTO]:
    calendar = json.loads(raw)
    if not isinstance(calendar, dict):
        raise ValueError("Calendar must be an object")
    sessions: list[LocalDataSessionDTO] = []
    seen: set[str] = set()
    for date_text, entries in calendar.items():
        if not isinstance(date_text, str) or not isinstance(entries, list):
            raise ValueError("Calendar entries are invalid")
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("Calendar entry is invalid")
            session_id = entry["id"]
            if not isinstance(session_id, str) or session_id in seen:
                raise ValueError("Calendar Session identifier is invalid")
            seen.add(session_id)
            sessions.append(
                LocalDataSessionDTO(
                    id=session_id,
                    name=f"{date_text} - {entry.get('firstLine', 'Untitled')}",
                    editor_state=_json_object_text(entry["state"]),
                )
            )
    return sessions


def _old_document_session(raw: str) -> list[LocalDataSessionDTO]:
    old_document = json.loads(raw)
    if not isinstance(old_document, dict) or not old_document.get("document"):
        return []
    return [
        LocalDataSessionDTO(
            id="old-document",
            name="Old Document (migrated)",
            editor_state=_json_object_text(
                {"cells": [{"type": "text", "content": str(old_document)}]}
            ),
        )
    ]


def _pictures(raw: str) -> list[LocalDataPictureDTO]:
    value = json.loads(raw)
    if not isinstance(value, list):
        raise ValueError("Pictures must be a list")
    pictures: list[LocalDataPictureDTO] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("Picture is invalid")
        pictures.append(
            LocalDataPictureDTO(
                date=item["date"],
                image_base64=item["base64"],
                prompt=item.get("prompt", ""),
            )
        )
    return pictures


def _report_timestamp(value: object) -> str:
    if type(value) is not int or abs(value) > _MAX_SAFE_INTEGER:
        raise ValueError("Report timestamp must be safe integer milliseconds")
    try:
        timestamp = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(
            milliseconds=value
        )
    except OverflowError:
        raise ValueError("Report timestamp is outside the supported date range") from None
    return timestamp.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Report clock must include a timezone")
    return value.astimezone(timezone.utc).isoformat(
        timespec="milliseconds"
    ).replace("+00:00", "Z")


def _reports(raw: str, *, missing_timestamp: str) -> list[LocalDataReportDTO]:
    value = json.loads(raw)
    if not isinstance(value, list):
        raise ValueError("Reports must be a list")
    reports: list[LocalDataReportDTO] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("Report is invalid")
        reports.append(
            LocalDataReportDTO(
                type=item.get("type", "unknown"),
                data=_json_object_text(item.get("data", {})),
                all_notes=item.get("allNotes", ""),
                timestamp=(
                    _report_timestamp(item["timestamp"])
                    if "timestamp" in item
                    else missing_timestamp
                ),
            )
        )
    return reports


def _preferences(request: ImportDataRequest) -> LocalDataPreferencesDTO | None:
    voice_configs = _parse_category(
        "voiceCustomizations",
        request.voiceCustomizations,
        require_json_object_text,
        None,
    )
    state_config = _parse_category(
        "stateConfig",
        request.stateConfig,
        require_json_object_text,
        None,
    )
    meta_prompt = request.metaPrompt if request.metaPrompt else None
    selected_state = request.selectedState if request.selectedState else None
    if all(
        value is None
        for value in (voice_configs, meta_prompt, state_config, selected_state)
    ):
        return None
    return LocalDataPreferencesDTO(
        voice_configs=voice_configs,
        meta_prompt=meta_prompt,
        state_config=state_config,
        selected_state=selected_state,
    )


def _normalized_import(
    request: ImportDataRequest,
    *,
    now: datetime | None = None,
) -> LocalDataImportInputDTO:
    session_groups = (
        ("currentSession", request.currentSession, _current_session),
        ("calendarEntries", request.calendarEntries, _calendar_sessions),
        ("oldDocument", request.oldDocument, _old_document_session),
    )
    sessions: list[LocalDataSessionDTO] = []
    seen: set[str] = set()
    for category, raw, parser in session_groups:
        parsed = _parse_category(category, raw, parser, [])
        if any(item.id in seen for item in parsed):
            logger.warning("Ignoring duplicate local-data Session category: %s", category)
            continue
        sessions.extend(parsed)
        seen.update(item.id for item in parsed)
    normalized = LocalDataImportInputDTO(
        sessions=sessions,
        pictures=_parse_category(
            "dailyPictures", request.dailyPictures, _pictures, []
        ),
        preferences=_preferences(request),
        reports=_parse_category(
            "analysisReports",
            request.analysisReports,
            lambda raw: _reports(
                raw,
                missing_timestamp=_iso_timestamp(now or _utc_now()),
            ),
            [],
        ),
    )
    logger.info(
        "Normalized local-data import: sessions=%d pictures=%d preferences=%d reports=%d",
        len(normalized.sessions),
        len(normalized.pictures),
        0 if normalized.preferences is None else 1,
        len(normalized.reports),
    )
    return normalized


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
async def import_local_data(
    request: ImportDataRequest,
    current_user: dict = Depends(get_current_user),
    data: AdminLocalDataImportData = Depends(_local_data),
):
    """
    Import localStorage data through the Admin aggregate on first login.

    Extracts sessions, pictures, preferences, and reports from localStorage export.
    """
    result = await invoke_admin_operation(
        current_user,
        data.import_data,
        _normalized_import(request),
    )
    return result.model_dump()


@router.post("/api/import-calendar-recovery")
async def import_calendar_recovery(
    request: CalendarRecoveryRequest,
    current_user: dict = Depends(get_current_user),
    data: AdminLocalDataImportData = Depends(_local_data),
):
    """
    Recovery endpoint to import calendar entries that were missed in initial migration.

    Request body:
    {
        "calendarEntries": "{\"2025-11-01\": [...]}"  # JSON string
    }
    """
    calendar_json = request.calendarEntries

    if not isinstance(calendar_json, str) or not calendar_json:
        raise HTTPException(status_code=400, detail="calendarEntries required")

    try:
        sessions = _calendar_sessions(calendar_json)
    except (
        KeyError,
        TypeError,
        ValueError,
        OverflowError,
        RecursionError,
        ValidationError,
    ):
        logger.warning("Rejecting malformed calendar recovery data")
        raise HTTPException(status_code=400, detail="Failed to parse calendar") from None
    result = await invoke_admin_operation(
        current_user,
        data.import_data,
        LocalDataImportInputDTO(
            sessions=sessions,
            pictures=[],
            preferences=None,
            reports=[],
        ),
    )
    return {
        "success": result.success,
        "imported": {"sessions": result.imported.sessions},
    }


@router.post("/api/mark-first-login-completed")
async def mark_first_login_completed(
    current_user: dict = Depends(get_current_user),
    data: AdminLocalDataImportData = Depends(_local_data),
):
    """
    Mark user's first login as completed.
    Called after migration dialog is shown (migrate or skip).
    """
    result = await invoke_admin_operation(
        current_user,
        data.complete_first_login,
        FirstLoginCompleteInputDTO(),
    )
    return {"success": result.success}
