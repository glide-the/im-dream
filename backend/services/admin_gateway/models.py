"""Strict server-only client for the Admin public Gateway model catalog."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Protocol

import requests

from .config import AdminGatewayConfig, AdminGatewayConfigurationError
from .inference import GatewayInferenceError
from .token import issue_gateway_subject_token


_MODEL_ALIAS = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$")
_PROTOCOLS = frozenset({"anthropic", "openai"})


class CatalogTransport(Protocol):
    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout: float,
    ) -> Any: ...


@dataclass(frozen=True)
class GatewayModel:
    model_alias: str
    display_name: str
    protocol: str
    capabilities: dict[str, bool]
    gateway_scopes: tuple[str, ...]
    context_window: int | None
    max_output_tokens: int | None

    def public_dict(self) -> dict[str, Any]:
        return {
            "modelAlias": self.model_alias,
            "displayName": self.display_name,
            "protocol": self.protocol,
            "capabilities": self.capabilities,
            "gatewayScopes": list(self.gateway_scopes),
            "contextWindow": self.context_window,
            "maxOutputTokens": self.max_output_tokens,
        }


def _optional_non_negative_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise GatewayInferenceError("GATEWAY_MODEL_CATALOG_INVALID", 502)
    return value


def _parse_model(raw: Any) -> GatewayModel:
    if not isinstance(raw, dict):
        raise GatewayInferenceError("GATEWAY_MODEL_CATALOG_INVALID", 502)
    alias = raw.get("id")
    display_name = raw.get("display_name")
    protocol = raw.get("protocol")
    capabilities = raw.get("capabilities")
    scopes = raw.get("gateway_scopes")
    if (
        not isinstance(alias, str)
        or not _MODEL_ALIAS.fullmatch(alias)
        or not isinstance(display_name, str)
        or not display_name.strip()
        or len(display_name) > 160
        or protocol not in _PROTOCOLS
        or not isinstance(capabilities, dict)
        or any(not isinstance(key, str) or not isinstance(value, bool) for key, value in capabilities.items())
        or not isinstance(scopes, list)
        or any(not isinstance(scope, str) or not _MODEL_ALIAS.fullmatch(scope) for scope in scopes)
    ):
        raise GatewayInferenceError("GATEWAY_MODEL_CATALOG_INVALID", 502)
    return GatewayModel(
        model_alias=alias,
        display_name=display_name.strip(),
        protocol=protocol,
        capabilities=dict(capabilities),
        gateway_scopes=tuple(dict.fromkeys(scopes)),
        context_window=_optional_non_negative_int(raw.get("context_window")),
        max_output_tokens=_optional_non_negative_int(raw.get("max_output_tokens")),
    )


class GatewayModelCatalogClient:
    def __init__(
        self,
        canonical_user_id: int | str,
        *,
        configuration: AdminGatewayConfig | None = None,
        environment: Mapping[str, str] | None = None,
        transport: CatalogTransport = requests,
    ) -> None:
        try:
            self.configuration = configuration or AdminGatewayConfig.from_environment(environment)
        except AdminGatewayConfigurationError as exc:
            raise GatewayInferenceError("GATEWAY_UNAVAILABLE", 503) from exc
        if not self.configuration.enabled:
            raise GatewayInferenceError("GATEWAY_UNAVAILABLE", 503)
        self.canonical_user_id = str(canonical_user_id)
        self.transport = transport

    def list_models(self, *, timeout: float = 10) -> list[GatewayModel]:
        try:
            token = issue_gateway_subject_token(
                self.configuration,
                self.canonical_user_id,
                scope="models:list",
            )
        except AdminGatewayConfigurationError as exc:
            raise GatewayInferenceError("GATEWAY_UNAUTHORIZED", 401) from exc
        try:
            response = self.transport.get(
                f"{self.configuration.base_url}/v1/models",
                headers={
                    "authorization": f"Bearer {token}",
                    "x-api-key": self.configuration.service_key,
                    "accept": "application/json",
                },
                timeout=timeout,
            )
        except Exception as exc:
            raise GatewayInferenceError("GATEWAY_UNAVAILABLE", 503) from exc
        if response.status_code != 200:
            status = int(response.status_code)
            code = {
                401: "GATEWAY_UNAUTHORIZED",
                402: "GATEWAY_TOKEN_ALLOWANCE_EXHAUSTED",
                403: "GATEWAY_FORBIDDEN",
                409: "GATEWAY_CONFLICT",
                429: "GATEWAY_RATE_LIMITED",
                502: "GATEWAY_PROVIDER_FAILED",
                503: "GATEWAY_UNAVAILABLE",
            }.get(status, "GATEWAY_REQUEST_FAILED")
            raise GatewayInferenceError(code, status)
        try:
            payload = response.json()
        except Exception as exc:
            raise GatewayInferenceError("GATEWAY_MODEL_CATALOG_INVALID", 502) from exc
        if not isinstance(payload, dict) or payload.get("object") != "list" or not isinstance(payload.get("data"), list):
            raise GatewayInferenceError("GATEWAY_MODEL_CATALOG_INVALID", 502)
        models = [_parse_model(item) for item in payload["data"]]
        aliases = [model.model_alias for model in models]
        if len(aliases) != len(set(aliases)):
            raise GatewayInferenceError("GATEWAY_MODEL_CATALOG_INVALID", 502)
        return models
