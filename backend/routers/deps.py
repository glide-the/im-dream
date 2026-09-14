#!/usr/bin/env python3
# [Input] Consume the Admin request-auth owner and common FastAPI dependency inputs.
# [Output] Provide bearer-only canonical identity and shared date/text helpers to backend routers.
# [Pos] shared dependency node in backend/routers
# [Sync] 2026-05-25: extracted common dependency helpers from backend/server.py.
# [Sync] 2026-06-23: allow auth dependencies to read system access tokens from
#                    Authorization headers or OAuth login cookies.
# [Sync] 2026-08-03: sliding token renewal - authenticated requests receive a
#                    fresh access token (header + cookie) once the current one
#                    is past half of its lifetime.
# [Sync] 2026-08-31: normalize PostgreSQL datetime and ISO-string timestamps as
#                    UTC-aware values for timezone-correct calendar grouping.
# [Sync] 2026-09-14: switch shared request authentication to Admin; remove local JWT/cookie/query renewal authority.

from datetime import datetime, timezone
import re
from typing import Optional
from uuid import uuid4

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from services.admin_data.errors import AdminDataError
from services.admin_data.request_auth import AdminRequestAuth

http_bearer = HTTPBearer(auto_error=False)


def get_admin_request_auth(request: Request, credentials: HTTPAuthorizationCredentials = Depends(http_bearer)) -> AdminRequestAuth:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing authorization token")
    owner = getattr(request.app.state, "admin_request_auth", None)
    if owner is None:
        raise HTTPException(status_code=503, detail="ADMIN_CONFIGURATION_INVALID")
    return owner


async def get_admin_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
) -> dict:
    """Production resource dependency: no cookie/query token or local JWT renewal."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing authorization token")
    request_id = str(uuid4())
    required_scopes = frozenset({"dream:read" if request.method in {"GET", "HEAD", "OPTIONS"} else "dream:write"})
    try:
        actor = await run_in_threadpool(owner.authenticate, credentials.credentials, request_id, required_scopes=required_scopes)
    except AdminDataError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code) from None
    request.state.admin_request_actor = actor
    request.state.admin_request_id = request_id
    return actor.current_user_projection()


get_current_user = get_admin_current_user


def _count_mixed_words(text: str) -> int:
    """
    Count words in mixed Chinese/English text.
    - CJK characters count as 1 each
    - English is counted by whitespace-separated tokens
    """
    word_count = 0
    for ch in text:
        code = ord(ch)
        if (
            0x4E00 <= code <= 0x9FFF
            or 0x3400 <= code <= 0x4DBF
            or 0x3040 <= code <= 0x309F
            or 0x30A0 <= code <= 0x30FF
        ):
            word_count += 1
    english_words = re.sub(
        r"[\u4E00-\u9FFF\u3400-\u4DBF\u3040-\u309F\u30A0-\u30FF]",
        " ",
        text,
    )
    word_count += len([w for w in english_words.split() if w])
    return word_count


def _clean_timestamp(ts_raw: Optional[str | datetime]) -> Optional[datetime]:
    """Normalize PostgreSQL datetimes or ISO strings to timezone-aware values."""
    if not ts_raw:
        return None
    try:
        if isinstance(ts_raw, datetime):
            return (
                ts_raw
                if ts_raw.tzinfo is not None
                else ts_raw.replace(tzinfo=timezone.utc)
            )
        cleaned = ts_raw.replace("Z", "+00:00")
        if "T" not in cleaned and " " in cleaned:
            cleaned = cleaned.replace(" ", "T")
        parsed = datetime.fromisoformat(cleaned)
        return (
            parsed
            if parsed.tzinfo is not None
            else parsed.replace(tzinfo=timezone.utc)
        )
    except Exception:
        return None


def _validate_date_str(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        datetime.fromisoformat(value)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format, expected YYYY-MM-DD")
    if len(value) != 10:
        raise HTTPException(status_code=400, detail="Invalid date format, expected YYYY-MM-DD")
    return value
