"""Short-lived HS256 service token issuance for the Admin Product API."""

from __future__ import annotations

from datetime import UTC, datetime
import re
import secrets
from typing import Literal

import jwt

from .config import AdminProductConfig
from .errors import configuration_unavailable


_SUBJECT_PATTERN = re.compile(r"^[1-9]\d{0,18}$")
_POSTGRES_BIGINT_MAXIMUM = 9_223_372_036_854_775_807
ProductScope = Literal["product:read", "product:write"]


def issue_product_token(
    configuration: AdminProductConfig,
    *,
    canonical_user_id: str,
    scope: ProductScope,
    now: datetime | None = None,
    token_id: str | None = None,
) -> str:
    """Issue a single-purpose token whose lifetime can never exceed 300s."""

    if (
        not _SUBJECT_PATTERN.fullmatch(canonical_user_id)
        or int(canonical_user_id) > _POSTGRES_BIGINT_MAXIMUM
    ):
        raise configuration_unavailable()
    issued_at = now or datetime.now(UTC)
    if issued_at.tzinfo is None:
        issued_at = issued_at.replace(tzinfo=UTC)
    issued_epoch = int(issued_at.timestamp())
    expires_epoch = issued_epoch + configuration.token_lifetime_seconds
    jti = token_id or secrets.token_urlsafe(24)
    if not jti or len(jti) > 200:
        raise configuration_unavailable()
    payload = {
        "sub": canonical_user_id,
        "iss": configuration.jwt_issuer,
        "aud": configuration.jwt_audience,
        "client_id": configuration.client_id,
        "scope": scope,
        "iat": issued_epoch,
        "exp": expires_epoch,
        "jti": jti,
    }
    return jwt.encode(payload, configuration.jwt_secret, algorithm="HS256")
