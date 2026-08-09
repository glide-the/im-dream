from __future__ import annotations

import re
import secrets
import time
from collections.abc import Callable

import jwt

from .config import AdminGatewayConfig, AdminGatewayConfigurationError

_CANONICAL_USER_PATTERN = re.compile(r"^[1-9][0-9]{0,18}$")
_POSTGRES_BIGINT_MAXIMUM = 9_223_372_036_854_775_807


def issue_gateway_subject_token(
    configuration: AdminGatewayConfig,
    canonical_user_id: str,
    *,
    scope: str = "messages:create",
    clock: Callable[[], float] = time.time,
    token_id: str | None = None,
) -> str:
    if not configuration.enabled:
        raise AdminGatewayConfigurationError(
            "Admin Gateway integration is not enabled"
        )
    subject = str(canonical_user_id).strip()
    if (
        not _CANONICAL_USER_PATTERN.fullmatch(subject)
        or int(subject) > _POSTGRES_BIGINT_MAXIMUM
    ):
        raise AdminGatewayConfigurationError(
            "The canonical Gateway subject is invalid"
        )
    issued_at = int(clock())
    payload = {
        "sub": subject,
        "iss": configuration.issuer,
        "aud": configuration.audience,
        "client_id": configuration.client_id,
        "azp": configuration.client_id,
        "scope": scope,
        "iat": issued_at,
        "exp": issued_at + configuration.token_lifetime_seconds,
        "jti": token_id or secrets.token_urlsafe(24),
    }
    return jwt.encode(payload, configuration.service_key, algorithm="HS256")
