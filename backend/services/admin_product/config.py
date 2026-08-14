"""Fail-closed, redacted configuration for the Admin Product API client."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import os
import re
from urllib.parse import urlsplit

from .errors import configuration_unavailable


_CLIENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$")


def _required(values: Mapping[str, str], name: str) -> str:
    value = values.get(name)
    if not isinstance(value, str) or not value.strip():
        raise configuration_unavailable()
    if value != value.strip() or any(character in value for character in "\r\n\x00"):
        raise configuration_unavailable()
    return value


def _exact_origin(value: str, *, allow_loopback_http: bool) -> str:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except (TypeError, ValueError):
        raise configuration_unavailable() from None
    host = (parsed.hostname or "").casefold()
    loopback = host in {"localhost", "127.0.0.1", "::1"}
    if (
        parsed.scheme not in {"http", "https"}
        or (parsed.scheme == "http" and not (allow_loopback_http and loopback))
        or not host
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise configuration_unavailable()
    default_port = 443 if parsed.scheme == "https" else 80
    authority = parsed.hostname or ""
    if ":" in authority and not authority.startswith("["):
        authority = f"[{authority}]"
    if port is not None and port != default_port:
        authority = f"{authority}:{port}"
    return f"{parsed.scheme}://{authority}"


def parse_origin_allowlist(
    value: str | None,
    *,
    allow_loopback_http: bool = True,
) -> frozenset[str]:
    if not isinstance(value, str) or not value.strip():
        raise configuration_unavailable()
    origins = [entry.strip() for entry in value.split(",")]
    if not origins or any(not origin for origin in origins):
        raise configuration_unavailable()
    return frozenset(
        _exact_origin(origin, allow_loopback_http=allow_loopback_http)
        for origin in origins
    )


@dataclass(frozen=True, repr=False)
class AdminProductConfig:
    base_url: str = field(repr=False)
    jwt_secret: str = field(repr=False)
    jwt_issuer: str
    jwt_audience: str
    client_id: str
    request_origin: str
    token_lifetime_seconds: int = 240
    timeout_seconds: float = 8.0

    def __post_init__(self) -> None:
        normalized_url = _exact_origin(self.base_url, allow_loopback_http=True)
        normalized_origin = _exact_origin(
            self.request_origin, allow_loopback_http=True
        )
        if normalized_url != self.base_url or normalized_origin != self.request_origin:
            raise configuration_unavailable()
        if len(self.jwt_secret.encode("utf-8")) < 32:
            raise configuration_unavailable()
        if any(character in self.jwt_secret for character in "\r\n\x00"):
            raise configuration_unavailable()
        if (
            not self.jwt_issuer
            or len(self.jwt_issuer) > 200
            or any(character in self.jwt_issuer for character in "\r\n\x00")
        ):
            raise configuration_unavailable()
        if (
            not self.jwt_audience
            or len(self.jwt_audience) > 200
            or any(character in self.jwt_audience for character in "\r\n\x00")
        ):
            raise configuration_unavailable()
        if not _CLIENT_ID_PATTERN.fullmatch(self.client_id):
            raise configuration_unavailable()
        if not 30 <= self.token_lifetime_seconds <= 300:
            raise configuration_unavailable()
        if not 0 < self.timeout_seconds <= 30:
            raise configuration_unavailable()

    def __repr__(self) -> str:
        return (
            "AdminProductConfig(base_url=<redacted>, jwt_secret=<redacted>, "
            f"client_id={self.client_id!r})"
        )

    @classmethod
    def from_env(
        cls, *, environ: Mapping[str, str] | None = None
    ) -> "AdminProductConfig":
        values = os.environ if environ is None else environ
        lifetime_raw = values.get("INK_ADMIN_PRODUCT_JWT_TTL_SECONDS", "240")
        timeout_raw = values.get("INK_ADMIN_PRODUCT_TIMEOUT_SECONDS", "8")
        try:
            lifetime = int(lifetime_raw)
            timeout = float(timeout_raw)
        except (TypeError, ValueError):
            raise configuration_unavailable() from None
        base_url = _exact_origin(
            _required(values, "INK_ADMIN_PRODUCT_API_BASE_URL"),
            allow_loopback_http=True,
        )
        request_origin = _exact_origin(
            _required(values, "INK_ADMIN_PRODUCT_ORIGIN"),
            allow_loopback_http=True,
        )
        return cls(
            base_url=base_url,
            jwt_secret=_required(values, "INK_ADMIN_PRODUCT_JWT_SECRET"),
            jwt_issuer=_required(values, "INK_ADMIN_PRODUCT_JWT_ISSUER"),
            jwt_audience=_required(values, "INK_ADMIN_PRODUCT_JWT_AUDIENCE"),
            client_id=_required(values, "INK_ADMIN_PRODUCT_CLIENT_ID"),
            request_origin=request_origin,
            token_lifetime_seconds=lifetime,
            timeout_seconds=timeout,
        )
