# [Input] Server-owned Admin public authority, optional internal transport origin, resource, credential and transport settings.
# [Output] Immutable validated configuration, excluding PG and environment-name switches.
# [Pos] Configuration source of truth for the unified Admin data/authentication client.
# [Sync] 2026-09-18: separate public issuer identity from an exact server-only Admin transport origin.
# [Sync] 2026-09-14: consume the Admin v0.1 protocol without enabled/fallback modes.
"""Authentication/data-service settings; secret values never appear in errors."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import os
from typing import Mapping
from urllib.parse import urlsplit, urlunsplit

from .errors import configuration_invalid

# Protocol paths and token lifetime are defined by Admin contract v0.1.
ADMIN_INTERNAL_PREFIX = "/api/internal/dream/v1"
AUTH_PATH = "/api/auth"
ACCESS_TOKEN_ALGORITHM = "ES256"
ACCESS_TOKEN_TYPE = "at+jwt"
ACCESS_TOKEN_MAX_LIFETIME_SECONDS = 300


def _required(values: Mapping[str, str], name: str) -> str:
    raw = values.get(name, "").strip()
    if not raw or any(ord(c) < 32 or ord(c) == 127 for c in raw):
        raise configuration_invalid()
    return raw


def _origin(raw: str) -> str:
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError:
        raise configuration_invalid() from None
    loopback_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if (
        (parsed.scheme != "https" and not loopback_http)
        or not parsed.hostname or parsed.username is not None or parsed.password is not None
        or parsed.query or parsed.fragment or parsed.path not in {"", "/"}
        or (port is not None and port < 1)
        or any(c.isspace() or c == "\\" for c in raw)
    ):
        raise configuration_invalid()
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def _number(values: Mapping[str, str], name: str, default: float) -> float:
    try:
        result = float(values.get(name, str(default)))
    except (TypeError, ValueError):
        raise configuration_invalid() from None
    if not math.isfinite(result) or result <= 0:
        raise configuration_invalid()
    return result


def _integer(values: Mapping[str, str], name: str, default: int) -> int:
    raw = values.get(name, str(default))
    if not raw.isascii() or not raw.isdigit() or int(raw) < 1:
        raise configuration_invalid()
    return int(raw)


@dataclass(frozen=True, repr=False)
class AdminDataConfig:
    base_url: str
    issuer: str
    resource: str
    service_secret: str = field(repr=False)
    service_client_id: str
    transport_base_url: str | None = None
    timeout_seconds: float = 10.0
    max_response_bytes: int = 1_048_576
    jwks_cache_seconds: int = 300
    jwks_refresh_min_interval_seconds: float = 5.0

    def __post_init__(self) -> None:
        if (
            _origin(self.base_url) != self.base_url
            or self.issuer != self.base_url + AUTH_PATH
            or (self.transport_base_url is not None and _origin(self.transport_base_url) != self.transport_base_url)
            or not self.resource or any(c.isspace() or ord(c) < 32 for c in self.resource)
            or len(self.service_secret.encode("utf-8")) < 32
            or not self.service_client_id or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in self.service_client_id)
            or any(ord(c) < 32 or ord(c) == 127 for c in self.service_secret)
            or not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0
            or isinstance(self.max_response_bytes, bool) or not isinstance(self.max_response_bytes, int) or self.max_response_bytes < 1
            or isinstance(self.jwks_cache_seconds, bool) or not isinstance(self.jwks_cache_seconds, int) or self.jwks_cache_seconds < 1
            or not math.isfinite(self.jwks_refresh_min_interval_seconds) or self.jwks_refresh_min_interval_seconds <= 0
        ):
            raise configuration_invalid()

    @property
    def jwks_uri(self) -> str:
        return self.issuer + "/jwks"

    @property
    def transport_origin(self) -> str:
        return self.transport_base_url or self.base_url

    @property
    def transport_issuer(self) -> str:
        return self.transport_origin + AUTH_PATH

    @property
    def transport_jwks_uri(self) -> str:
        return self.transport_issuer + "/jwks"

    def __repr__(self) -> str:
        return "AdminDataConfig(<server-owned values redacted>)"

    @classmethod
    def from_env(cls, values: Mapping[str, str] | None = None) -> AdminDataConfig:
        env = os.environ if values is None else values
        return cls(
            base_url=_origin(_required(env, "INK_ADMIN_DREAM_BASE_URL")),
            issuer=_required(env, "INK_ADMIN_AUTH_ISSUER"),
            resource=_required(env, "INK_DREAM_API_RESOURCE"),
            service_secret=_required(env, "INK_ADMIN_DREAM_SERVICE_SECRET"),
            service_client_id=_required(env, "INK_ADMIN_DREAM_SERVICE_CLIENT_ID"),
            transport_base_url=_origin(env["INK_ADMIN_DREAM_TRANSPORT_BASE_URL"].strip())
                if env.get("INK_ADMIN_DREAM_TRANSPORT_BASE_URL", "").strip() else None,
            timeout_seconds=_number(env, "INK_ADMIN_DREAM_TIMEOUT_SECONDS", 10.0),
            max_response_bytes=_integer(env, "INK_ADMIN_DREAM_MAX_RESPONSE_BYTES", 1_048_576),
            jwks_cache_seconds=_integer(env, "INK_ADMIN_JWKS_CACHE_SECONDS", 300),
            jwks_refresh_min_interval_seconds=_number(env, "INK_ADMIN_JWKS_REFRESH_MIN_INTERVAL_SECONDS", 5.0),
        )
