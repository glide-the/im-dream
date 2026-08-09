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
_AVAILABILITY = frozenset({
    "included",
    "upgrade_required",
    "subscription_inactive",
    "allowance_exhausted",
    "permission_denied",
    "maintenance",
})


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
    context_window: int | None
    max_output_tokens: int | None
    enabled: bool
    callable: bool
    availability: str
    required_plan_code: str | None
    upgrade_hint: str | None

    def public_dict(self) -> dict[str, Any]:
        return {
            "modelAlias": self.model_alias,
            "displayName": self.display_name,
            "protocol": self.protocol,
            "capabilities": self.capabilities,
            "contextWindow": self.context_window,
            "maxOutputTokens": self.max_output_tokens,
            "enabled": self.enabled,
            "callable": self.callable,
            "availability": self.availability,
            "requiredPlanCode": self.required_plan_code,
            "upgradeHint": self.upgrade_hint,
        }


@dataclass(frozen=True)
class GatewayModelCatalog:
    models: tuple[GatewayModel, ...]
    default_model_alias: str | None


def _optional_non_negative_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise GatewayInferenceError("GATEWAY_MODEL_CATALOG_INVALID", 502)
    return value


def _parse_model(raw: Any) -> GatewayModel:
    if not isinstance(raw, dict):
        raise GatewayInferenceError("GATEWAY_MODEL_CATALOG_INVALID", 502)
    if set(raw) != {
        "id", "display_name", "protocol", "capabilities",
        "context_window", "max_output_tokens", "enabled", "callable",
        "availability", "required_plan_code", "upgrade_hint",
    }:
        raise GatewayInferenceError("GATEWAY_MODEL_CATALOG_INVALID", 502)
    alias = raw.get("id")
    display_name = raw.get("display_name")
    protocol = raw.get("protocol")
    capabilities = raw.get("capabilities")
    enabled = raw.get("enabled")
    callable_value = raw.get("callable")
    availability = raw.get("availability")
    required_plan_code = raw.get("required_plan_code")
    upgrade_hint = raw.get("upgrade_hint")
    if (
        not isinstance(alias, str)
        or not _MODEL_ALIAS.fullmatch(alias)
        or not isinstance(display_name, str)
        or not display_name.strip()
        or len(display_name) > 160
        or protocol not in _PROTOCOLS
        or not isinstance(capabilities, dict)
        or any(not isinstance(key, str) or not isinstance(value, bool) for key, value in capabilities.items())
        or enabled is not True
        or not isinstance(callable_value, bool)
        or availability not in _AVAILABILITY
        or callable_value != (availability == "included")
        or (required_plan_code is not None and (
            not isinstance(required_plan_code, str)
            or not _MODEL_ALIAS.fullmatch(required_plan_code)
        ))
        or (upgrade_hint is not None and (
            not isinstance(upgrade_hint, str)
            or not upgrade_hint.strip()
            or len(upgrade_hint) > 240
        ))
    ):
        raise GatewayInferenceError("GATEWAY_MODEL_CATALOG_INVALID", 502)
    return GatewayModel(
        model_alias=alias,
        display_name=display_name.strip(),
        protocol=protocol,
        capabilities=dict(capabilities),
        context_window=_optional_non_negative_int(raw.get("context_window")),
        max_output_tokens=_optional_non_negative_int(raw.get("max_output_tokens")),
        enabled=True,
        callable=callable_value,
        availability=availability,
        required_plan_code=required_plan_code,
        upgrade_hint=upgrade_hint.strip() if upgrade_hint else None,
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

    def fetch_catalog(self, *, timeout: float = 10) -> GatewayModelCatalog:
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
        if (
            not isinstance(payload, dict)
            or set(payload) != {"object", "data", "default_model_alias"}
            or payload.get("object") != "list"
            or not isinstance(payload.get("data"), list)
        ):
            raise GatewayInferenceError("GATEWAY_MODEL_CATALOG_INVALID", 502)
        models = [_parse_model(item) for item in payload["data"]]
        aliases = [model.model_alias for model in models]
        if len(aliases) != len(set(aliases)):
            raise GatewayInferenceError("GATEWAY_MODEL_CATALOG_INVALID", 502)
        default_alias = payload.get("default_model_alias")
        if default_alias is not None and (
            not isinstance(default_alias, str)
            or not _MODEL_ALIAS.fullmatch(default_alias)
            or default_alias not in {model.model_alias for model in models if model.callable}
        ):
            raise GatewayInferenceError("GATEWAY_MODEL_CATALOG_INVALID", 502)
        return GatewayModelCatalog(tuple(models), default_alias)

    def list_models(self, *, timeout: float = 10) -> list[GatewayModel]:
        return list(self.fetch_catalog(timeout=timeout).models)
