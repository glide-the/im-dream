# [Input] Server-owned public Admin origin, exact issuer and Dream OAuth resource.
# [Output] Explicit 410 migration response with standard endpoints, no credential or forwarding.
# [Pos] Sole retired Dream issuer response owner; BFF/Admin execute actual authentication.
# [Sync] 2026-09-14: preserve legacy paths while refusing local token issuance and refresh.
"""A retired endpoint never reads passwords, codes, cookies or service secrets."""

from __future__ import annotations

import os
from typing import Mapping

from fastapi.responses import JSONResponse

from .config import AUTH_PATH, _origin
from .errors import AdminDataError


def retired_authentication(values: Mapping[str, str] | None = None) -> JSONResponse:
    env = os.environ if values is None else values
    try:
        origin = _origin(env.get("INK_ADMIN_DREAM_BASE_URL", "").strip())
        issuer = env.get("INK_ADMIN_AUTH_ISSUER", "").strip()
        resource = env.get("INK_DREAM_API_RESOURCE", "").strip()
        if issuer != origin + AUTH_PATH or not resource or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in resource):
            raise AdminDataError("ADMIN_CONFIGURATION_INVALID", 503)
    except (AdminDataError, ValueError, TypeError):
        return JSONResponse({"error": {"code": "ADMIN_CONFIGURATION_INVALID",
            "message": "The Admin authentication authority is not configured."}},
            status_code=503, headers={"Cache-Control": "no-store"})
    return JSONResponse({"error": {"code": "DREAM_AUTHENTICATION_RETIRED",
        "message": "Use the Admin authentication authority."}, "authentication": {
            "issuer": issuer, "authorization_endpoint": issuer + "/oauth2/authorize",
            "token_endpoint": issuer + "/oauth2/token", "device_authorization_endpoint": issuer + "/device/code",
            "revocation_endpoint": issuer + "/oauth2/revoke", "jwks_uri": issuer + "/jwks",
            "verification_uri": origin + "/auth/device", "resource": resource,
        }}, status_code=410, headers={"Cache-Control": "no-store"})
