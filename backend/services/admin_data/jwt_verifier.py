# [Input] AdminDataConfig, Admin OAuth ES256 access tokens and the fixed issuer JWKS.
# [Output] Immutable verified OAuth claims; canonical users.id still requires Admin principal.
# [Pos] Dream Resource Server signature/scope boundary using PyJWT's JWK and JWT validation.
# [Sync] 2026-09-14: cached, rate-limited JWKS lookup with no token-selected network URLs.
"""Validate Admin OAuth access tokens; never issue or silently renew tokens."""

from __future__ import annotations

from dataclasses import dataclass
import json
from threading import RLock
import time
from typing import Any, Callable

import httpx
import jwt
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError

from .config import (
    ACCESS_TOKEN_ALGORITHM, ACCESS_TOKEN_MAX_LIFETIME_SECONDS,
    ACCESS_TOKEN_TYPE, AdminDataConfig,
)
from .errors import AdminDataError, invalid_access_token, unavailable


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not any(ord(c) < 32 or ord(c) == 127 for c in value)


@dataclass(frozen=True, slots=True)
class OAuthPrincipalClaims:
    subject: str
    client_id: str
    scopes: frozenset[str]
    token_id: str
    issued_at: int
    expires_at: int


class _HttpJWKClient(jwt.PyJWKClient):
    """Reuse PyJWT parsing/cache; constrain fetches to one configured HTTP origin."""

    def __init__(self, config: AdminDataConfig, client: httpx.Client, clock: Callable[[], float]) -> None:
        super().__init__(config.jwks_uri, cache_keys=False, cache_jwk_set=True, lifespan=config.jwks_cache_seconds)
        self._config = config
        self._http = client
        self._clock = clock
        self._last_fetch: float | None = None

    def fetch_data(self) -> Any:
        now = self._clock()
        if self._last_fetch is not None and now - self._last_fetch < self._config.jwks_refresh_min_interval_seconds:
            raise PyJWKClientConnectionError("JWKS refresh is temporarily unavailable")
        self._last_fetch = now
        try:
            with self._http.stream("GET", self.uri, headers={"accept": "application/json"}, timeout=self._config.timeout_seconds, follow_redirects=False) as response:
                if response.status_code != 200:
                    raise PyJWKClientConnectionError("JWKS is unavailable")
                chunks = bytearray()
                for chunk in response.iter_bytes():
                    chunks.extend(chunk)
                    if len(chunks) > self._config.max_response_bytes:
                        raise PyJWKClientConnectionError("JWKS response is invalid")
            data = json.loads(chunks)
            if not isinstance(data, dict) or not isinstance(data.get("keys"), list):
                raise PyJWKClientConnectionError("JWKS response is invalid")
            try:
                jwt.PyJWKSet.from_dict(data)
            except (jwt.PyJWTError, ValueError, TypeError, KeyError):
                raise PyJWKClientConnectionError("JWKS response is invalid") from None
        except (httpx.HTTPError, ValueError, UnicodeError):
            raise PyJWKClientConnectionError("JWKS is unavailable") from None
        if self.jwk_set_cache is not None:
            self.jwk_set_cache.put(data)
        return data

    def get_signing_key(self, kid: str) -> jwt.PyJWK:
        keys = self.get_signing_keys()
        matches = [key for key in keys if key.key_id == kid]
        if not matches:
            # Prevent attacker-selected unknown kids from forcing one fetch/request.
            now = self._clock()
            if self._last_fetch is not None and now - self._last_fetch < self._config.jwks_refresh_min_interval_seconds:
                raise PyJWKClientError("Unknown signing key")
            keys = self.get_signing_keys(refresh=True)
            matches = [key for key in keys if key.key_id == kid]
        if len(matches) != 1 or matches[0].algorithm_name != ACCESS_TOKEN_ALGORITHM:
            raise PyJWKClientError("Invalid signing key")
        return matches[0]


class AdminJWTVerifier:
    def __init__(self, config: AdminDataConfig, *, client: httpx.Client | None = None, monotonic: Callable[[], float] = time.monotonic) -> None:
        self._config = config
        self._owns_client = client is None
        self._http = client or httpx.Client(timeout=config.timeout_seconds, follow_redirects=False, trust_env=False)
        self._jwks = _HttpJWKClient(config, self._http, monotonic)
        self._lock = RLock()

    def close(self) -> None:
        if self._owns_client:
            self._http.close()

    def verify(self, token: str, *, required_scopes: frozenset[str] = frozenset()) -> OAuthPrincipalClaims:
        try:
            header = jwt.get_unverified_header(token)
            if header.get("alg") != ACCESS_TOKEN_ALGORITHM or header.get("typ") != ACCESS_TOKEN_TYPE or not _nonempty_text(header.get("kid")):
                raise invalid_access_token()
            if header.get("crit"):
                raise invalid_access_token()
            with self._lock:
                key = self._jwks.get_signing_key(header["kid"])
            claims = jwt.decode(token, key, algorithms=[ACCESS_TOKEN_ALGORITHM], issuer=self._config.issuer, audience=self._config.resource,
                options={"require": ["sub", "iss", "aud", "exp", "iat", "jti", "client_id", "scope"], "strict_aud": True})
            for name in ("exp", "iat"):
                if isinstance(claims[name], bool) or not isinstance(claims[name], int):
                    raise invalid_access_token()
            if "nbf" in claims and (isinstance(claims["nbf"], bool) or not isinstance(claims["nbf"], int)):
                raise invalid_access_token()
            lifetime = claims["exp"] - claims["iat"]
            if not 0 < lifetime <= ACCESS_TOKEN_MAX_LIFETIME_SECONDS:
                raise invalid_access_token()
            if not all(_nonempty_text(claims[name]) for name in ("sub", "client_id", "jti", "scope")):
                raise invalid_access_token()
            scopes = frozenset(claims["scope"].split())
            if not required_scopes <= scopes:
                raise AdminDataError("INSUFFICIENT_SCOPE", 403)
            return OAuthPrincipalClaims(claims["sub"], claims["client_id"], scopes, claims["jti"], claims["iat"], claims["exp"])
        except PyJWKClientConnectionError:
            raise unavailable() from None
        except jwt.InvalidAudienceError:
            raise AdminDataError("INVALID_TOKEN_RESOURCE", 403) from None
        except (jwt.PyJWTError, PyJWKClientError, ValueError, TypeError, KeyError):
            raise invalid_access_token() from None
