#!/usr/bin/env python3
# [Input] Legacy Device/code/verification/token paths and configured public Admin authority.
# [Output] Explicit 410 migration DTO; no local Device state, refresh mutation or token issuance.
# [Pos] Retired Device issuer adapter; Admin owns RFC8628 and OAuth token actions.
# [Sync] 2026-09-14: retain paths/error import while removing Authlib/DB/local signing authority.

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.admin_data.retired_auth import retired_authentication

router = APIRouter()

# Historical DTO imports remain available; retired routes never parse them.
class DeviceCodeRequest(BaseModel):
    client_id: str
    scope: Optional[str] = None

class DeviceCodeResponse(BaseModel):
    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str
    expires_in: int
    interval: int

class DeviceVerifyRequest(BaseModel):
    user_code: str
    approve: bool = True


class OAuthProtocolError(HTTPException):
    """Retained error import for the existing FastAPI protocol error handler."""
    def __init__(self, error: str, description: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail={"error": error, "error_description": description})
        self.error = error
        self.description = description


@router.post("/oauth/device/code")
def create_device_code():
    return retired_authentication()


@router.get("/oauth/device/verify")
def get_device_verification():
    return retired_authentication()


@router.post("/oauth/device/verify")
def verify_device_code():
    return retired_authentication()


@router.post("/oauth/token")
def oauth_token():
    return retired_authentication()
