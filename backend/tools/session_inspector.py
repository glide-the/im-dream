#!/usr/bin/env python3
# [Input] Explicit account selector, Admin OAuth, public Dream URL, local day and timezone.
# [Output] Inspect and rebuild matching Sessions through Admin-backed public DTO routes.
# [Pos] Manual Session contract tool; no database credentials or SQL.
# [Sync] 2026-09-16: replace Dream PostgreSQL reads/writes with public Session API calls.

"""Inspect and rebuild Sessions through the same public routes used by the product."""

from __future__ import annotations

import argparse
import os
from zoneinfo import ZoneInfo

import httpx

from tools.session_inserter import _profile, _require_expected_account, _token


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect and rebuild sessions for a given day.")
    parser.add_argument("--email", help="Expected authenticated user email")
    parser.add_argument("--user-id", type=int, help="Expected authenticated user ID")
    parser.add_argument("--backend-url", default=os.environ.get("INK_MEMORY_BACKEND_URL", "http://localhost:8000"))
    parser.add_argument("--api-token", default=os.environ.get("INK_MEMORY_IMPORT_API_TOKEN"))
    parser.add_argument("--date", required=True, help="Local date in YYYY-MM-DD")
    parser.add_argument("--timezone", default="UTC", help="IANA timezone name")
    return parser.parse_args()


def _first_line(state: dict) -> str:
    for cell in state.get("cells", []):
        if cell.get("type") == "text" and isinstance(cell.get("content"), str):
            return cell["content"].splitlines()[0] if cell["content"] else ""
    return ""


def main() -> None:
    args = parse_args()
    ZoneInfo(args.timezone)
    token = _token(args.api_token)
    base = args.backend_url.rstrip("/")
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(timeout=60, trust_env=False, follow_redirects=False) as client:
        profile = _profile(client, base, token)
        _require_expected_account(profile, args.email, args.user_id)
        listed = client.get(
            f"{base}/api/sessions/range",
            headers=headers,
            params={
                "start_date": args.date,
                "end_date": args.date,
                "timezone": args.timezone,
            },
        )
        listed.raise_for_status()
        ids = [item["id"] for item in listed.json().get("sessions", [])]
        if not ids:
            print("⚠️  No sessions found for the requested day.")
            return
        batched = client.post(f"{base}/api/sessions/batch", headers=headers, json={"ids": ids})
        batched.raise_for_status()
        sessions = batched.json().get("sessions", [])
        print(f"Found {len(sessions)} session(s) for user {profile['id']} on {args.date}.")
        for session in sessions:
            state = session["editor_state"]
            print("------------------------------------------------------------")
            print(f"🗂  Session ID:   {session['id']}")
            print(f"📅  Created At:   {session.get('created_at')}")
            print(f"🕒  Updated At:   {session.get('updated_at')}")
            print(f"🏷️   Name:         {session.get('name') or '(none)'}")
            print(f"📝  First Line:   {_first_line(state) or '(empty)'}")
            deleted = client.delete(f"{base}/api/sessions/{session['id']}", headers=headers)
            deleted.raise_for_status()
            recreated = client.post(
                f"{base}/api/sessions",
                headers=headers,
                json={
                    "session_id": session["id"],
                    "editor_state": state,
                    "name": session.get("name"),
                    "labels": session.get("labels", []),
                    "created_at": session.get("created_at"),
                },
            )
            recreated.raise_for_status()
            print("✅ Recreated successfully through the public Session API.")


if __name__ == "__main__":
    main()
