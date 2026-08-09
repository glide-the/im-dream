from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping
from urllib.parse import urlsplit, urlunsplit


class AdminGatewayConfigurationError(RuntimeError):
    """Safe, value-free configuration failure."""


_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def _required(values: Mapping[str, str], name: str) -> str:
    value = values.get(name, "").strip()
    if not value:
        raise AdminGatewayConfigurationError(
            "Admin Gateway integration is enabled but not safely configured"
        )
    return value


def _base_url(raw: str) -> str:
    parsed = urlsplit(raw)
    local_http = parsed.scheme == "http" and parsed.hostname in {
        "127.0.0.1",
        "localhost",
        "::1",
    }
    if (
        (parsed.scheme != "https" and not local_http)
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise AdminGatewayConfigurationError(
            "Admin Gateway integration is enabled but not safely configured"
        )
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


@dataclass(frozen=True)
class AdminGatewayConfig:
    enabled: bool
    base_url: str = ""
    service_key: str = field(default="", repr=False)
    issuer: str = ""
    audience: str = ""
    client_id: str = ""
    token_lifetime_seconds: int = 240

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> "AdminGatewayConfig":
        values = os.environ if environment is None else environment
        enabled = values.get("INK_GATEWAY_CLAUDE_AGENT_ENABLED", "").strip().lower()
        if enabled not in _TRUE_VALUES:
            return cls(enabled=False)
        raw_lifetime = values.get(
            "INK_GATEWAY_SUBJECT_TOKEN_LIFETIME_SECONDS",
            "240",
        ).strip()
        try:
            lifetime = int(raw_lifetime)
        except ValueError as exc:
            raise AdminGatewayConfigurationError(
                "Admin Gateway integration is enabled but not safely configured"
            ) from exc
        key = _required(values, "INK_GATEWAY_SERVICE_KEY")
        if (
            not key.startswith("gw_")
            or len(key.encode("utf-8")) < 32
            or any(character in key for character in "\r\n")
            or not 30 <= lifetime <= 300
        ):
            raise AdminGatewayConfigurationError(
                "Admin Gateway integration is enabled but not safely configured"
            )
        return cls(
            enabled=True,
            base_url=_base_url(_required(values, "INK_GATEWAY_BASE_URL")),
            service_key=key,
            issuer=_required(values, "INK_GATEWAY_SUBJECT_JWT_ISSUER"),
            audience=_required(values, "INK_GATEWAY_SUBJECT_JWT_AUDIENCE"),
            client_id=_required(values, "INK_GATEWAY_SERVICE_CLIENT_ID"),
            token_lifetime_seconds=lifetime,
        )

    def __repr__(self) -> str:
        return (
            "AdminGatewayConfig("
            f"enabled={self.enabled!r}, base_url=<redacted>, "
            "service_key=<redacted>, issuer=<redacted>, audience=<redacted>, "
            "client_id=<redacted>, "
            f"token_lifetime_seconds={self.token_lifetime_seconds!r})"
        )
