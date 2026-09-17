#!/usr/bin/env python3
# [Input] Explicit account selector, Admin OAuth, public Dream URL and Session fields.
# [Output] Create one synthetic Session through the Admin-backed public DTO route.
# [Pos] Manual timezone validation tool; no database credentials or SQL.
# [Sync] 2026-09-16: replace Dream PostgreSQL access with profile-bound public Session API calls.

"""Create one synthetic Session through the normal Dream production entrance."""

from __future__ import annotations

import argparse
import os
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Insert a session for a specific user/day.")
    parser.add_argument("--email", help="Expected authenticated user email")
    parser.add_argument("--user-id", type=int, help="Expected authenticated user ID")
    parser.add_argument("--backend-url", default=os.environ.get("INK_MEMORY_BACKEND_URL", "http://localhost:8000"))
    parser.add_argument("--api-token", default=os.environ.get("INK_MEMORY_IMPORT_API_TOKEN"))
    parser.add_argument("--date", required=True, help="Local date in YYYY-MM-DD")
    parser.add_argument("--time", default="09:00", help="Local time in HH:MM")
    parser.add_argument("--timezone", default="UTC", help="IANA timezone name")
    parser.add_argument("--title", help="Optional session title")
    parser.add_argument("--text", default="", help="Optional first text-cell content")
    parser.add_argument("--session-id", help="Optional explicit session ID")
    return parser.parse_args()


def _token(raw: str | None) -> str:
    value = str(raw or "").strip()
    if not value or any(character.isspace() or ord(character) < 32 for character in value):
        raise SystemExit("Explicit Admin OAuth --api-token is required.")
    return value


def _profile(client: httpx.Client, base: str, token: str) -> dict:
    response = client.get(f"{base}/api/me", headers={"Authorization": f"Bearer {token}"})
    if response.status_code != 200:
        raise SystemExit("Admin OAuth profile is unavailable.")
    value = response.json()
    if not isinstance(value, dict) or type(value.get("id")) is not int:
        raise SystemExit("Admin OAuth profile is invalid.")
    return value


def _require_expected_account(profile: dict, email: str | None, user_id: int | None) -> None:
    if email is None and user_id is None:
        raise SystemExit("Either --email or --user-id is required.")
    if email is not None and profile.get("email") != email:
        raise SystemExit("Admin OAuth account does not match --email.")
    if user_id is not None and profile["id"] != user_id:
        raise SystemExit("Admin OAuth account does not match --user-id.")


def local_timestamp(date: str, time_str: str, tz_name: str) -> str:
    tz = ZoneInfo(tz_name)
    local_dt = datetime.strptime(f"{date} {time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
    return local_dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_editor_state(session_id: str, text: str, created_at_iso: str) -> dict:
    return {
        "cells": [{"id": uuid.uuid4().hex[:12], "type": "text", "content": text}],
        "commentors": [],
        "tasks": [],
        "weightPath": [],
        "overlappedPhrases": [],
        "notFoundPhrases": [],
        "id": session_id,
        "selectedState": None,
        "createdAt": created_at_iso,
    }


def main() -> None:
    args = parse_args()
    token = _token(args.api_token)
    base = args.backend_url.rstrip("/")
    created_at = local_timestamp(args.date, args.time, args.timezone)
    session_id = args.session_id or str(uuid.uuid4())
    text = args.text.strip()
    title = args.title or (text.splitlines()[0][:60] if text else f"Session {args.date}")
    with httpx.Client(timeout=30, trust_env=False, follow_redirects=False) as client:
        profile = _profile(client, base, token)
        _require_expected_account(profile, args.email, args.user_id)
        response = client.post(
            f"{base}/api/sessions",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "session_id": session_id,
                "editor_state": build_editor_state(session_id, text, created_at),
                "name": title,
                "labels": [],
                "created_at": created_at,
            },
        )
        response.raise_for_status()
        if response.json() != {"success": True}:
            raise SystemExit("Session API did not confirm the write.")
    print(f"✅ Inserted session {session_id} for user {profile['id']} at {created_at}.")


if __name__ == "__main__":
    main()
