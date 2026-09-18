# [Input] Server-owned OAuth client ID/secret, Admin issuer/resource and bounded HTTP transport.
# [Output] Cached short-lived client_credentials bearer with one bounded transport recovery or a redacted AdminDataError.
# [Pos] Confidential service-token source shared by the sole Admin DTO client.
# [Sync] 2026-09-18: obtain public-issuer tokens through the configured internal Admin transport origin.
# [Sync] 2026-09-17: recover one stale/closed token transport without retrying HTTP responses or business DTO calls.
"""Fetch and cache an Admin-issued machine token without exposing credentials."""

from __future__ import annotations

from base64 import b64encode
from threading import Lock
import time
from typing import Callable
from urllib.parse import quote_plus, urlencode

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .config import AdminDataConfig
from .errors import AdminDataError


class _ServiceTokenDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    access_token: str = Field(pattern=r"^[A-Za-z0-9._~-]+$", max_length=16_384)
    token_type: str
    expires_in: int = Field(gt=0, le=300)
    expires_at: int | None = Field(default=None, gt=0)
    scope: str = Field(min_length=1, max_length=1_000)


class OAuthClientCredentialsTokenSource:
    """RFC 6749 client_credentials source with bounded cache and transport recovery."""

    def __init__(self, config: AdminDataConfig, client: httpx.Client,
                 *, monotonic: Callable[[], float] = time.monotonic) -> None:
        self._config = config
        self._client = client
        self._monotonic = monotonic
        self._lock = Lock()
        self._token: str | None = None
        self._reuse_until = 0.0

    def access_token(self) -> str:
        with self._lock:
            now = self._monotonic()
            if self._token is not None and now < self._reuse_until:
                return self._token
            client_id = quote_plus(self._config.service_client_id, safe="")
            client_secret = quote_plus(self._config.service_secret, safe="")
            basic = b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
            raw: bytearray | None = None
            for attempt in range(2):
                # The second attempt only recovers a stale/closed pooled connection.
                # It cannot extend an unavailable Admin by another full request timeout.
                timeout = self._config.timeout_seconds if attempt == 0 else min(2.0, self._config.timeout_seconds)
                request = httpx.Request(
                    "POST",
                    self._config.transport_issuer + "/oauth2/token",
                    headers={
                        "accept": "application/json",
                        "content-type": "application/x-www-form-urlencoded",
                        "authorization": "Basic " + basic,
                    },
                    content=urlencode({
                        "grant_type": "client_credentials",
                        "resource": self._config.resource,
                    }).encode("ascii"),
                    extensions={"timeout": {key: timeout for key in ("connect", "read", "write", "pool")}},
                )
                try:
                    response = self._client.send(request, stream=True, follow_redirects=False, auth=None)
                    try:
                        raw = bytearray()
                        for chunk in response.iter_bytes():
                            raw.extend(chunk)
                            if len(raw) > self._config.max_response_bytes:
                                raise AdminDataError("ADMIN_SERVICE_AUTH_UNAVAILABLE", 503)
                        if not 200 <= response.status_code < 300:
                            raise AdminDataError("ADMIN_SERVICE_AUTH_UNAVAILABLE", 503)
                    finally:
                        response.close()
                    break
                except AdminDataError:
                    raise
                except httpx.HTTPError:
                    if attempt == 1:
                        raise AdminDataError("ADMIN_SERVICE_AUTH_UNAVAILABLE", 503) from None
            if raw is None:
                raise AdminDataError("ADMIN_SERVICE_AUTH_UNAVAILABLE", 503)
            try:
                token = _ServiceTokenDTO.model_validate_json(raw)
            except ValidationError:
                raise AdminDataError("ADMIN_SERVICE_AUTH_UNAVAILABLE", 503) from None
            if token.token_type != "Bearer" or any(scope == "" for scope in token.scope.split(" ")):
                raise AdminDataError("ADMIN_SERVICE_AUTH_UNAVAILABLE", 503)
            skew = min(30, max(1, token.expires_in // 5))
            self._token = token.access_token
            self._reuse_until = now + max(1, token.expires_in - skew)
            return token.access_token
