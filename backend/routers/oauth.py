#!/usr/bin/env python3
# [Input] Legacy Google login/callback paths; configured public Admin authority only.
# [Output] Explicit 410 standard-endpoint migration DTO; never consumes OAuth codes or cookies.
# [Pos] Retired Google issuer adapter; Admin owns actual Google account authentication.
# [Sync] 2026-09-14: remove Authlib/local-token execution while preserving both public paths.

from fastapi import APIRouter
from services.admin_data.retired_auth import retired_authentication

router = APIRouter()


@router.get("/oauth/google/login")
def google_login():
    return retired_authentication()


@router.get("/oauth/google/callback")
def google_callback():
    return retired_authentication()
