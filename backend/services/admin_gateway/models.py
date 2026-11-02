# [Sync] 2026-10-10: separate saved AI/Image ownership; Responses images stay disabled pending a complete bridge.
# [Sync] 2026-10-10: validate endpoint-specific image catalog; Images-only models cannot become text defaults.
# [Input] Consume an Admin-issued OAuth or entity-delegation bearer and the server-only Gateway key.
# [Output] Provide strict server-only model capabilities and Claude Code Runtime settings.
# [Pos] Admin Gateway model contract boundary; runtime-only fields never enter public Dream DTOs.
# [Sync] 2026-09-19: log safe upstream Gateway error codes without credentials or response bodies.
# [Sync] 2026-09-16: replace Dream-signed subject JWTs with Admin-issued bearers.
# [Sync] 2026-10-25: log transport exception class and elapsed time without request, response or credential content.

"""Strict server-only client for the Admin public Gateway model catalog."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re
import time
from typing import Any, Mapping, Protocol

import requests

from .config import AdminGatewayConfig, AdminGatewayConfigurationError
from .errors import GatewayInferenceError
_MODEL_ALIAS = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$")
_ACCESS_TOKEN = re.compile(r"^[A-Za-z0-9._~-]{16,8192}$")
_PROTOCOLS = frozenset({"anthropic", "openai"})
_PUBLIC_CAPABILITIES = frozenset({"chat", "json", "tools", "vision", "streaming", "image_generation", "image_edit", "responses_image_generation", "responses_image_edit"})
_AVAILABILITY = frozenset({
    "included",
    "upgrade_required",
    "subscription_inactive",
    "allowance_exhausted",
    "permission_denied",
    "maintenance",
})
_CLAUDE_CODE_RUNTIME_INTEGER_MAX = 2_147_483_647
_SAFE_GATEWAY_ERROR_CODE = re.compile(r"^GATEWAY_[A-Z0-9_]{1,79}$")
logger = logging.getLogger(__name__)


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
    claude_code_auto_compact_window: int | None = None
    claude_code_max_context_tokens: int | None = None

    image_callable: bool = False
    image_generation: bool = False
    image_edit: bool = False
    image_configured: bool = False
    image_entitled: bool = False
    responses_image: dict[str, bool] | None = None

    @property
    def is_conversation_model(self) -> bool:
        # Old text catalogs omit chat; Images-only records must opt into chat.
        return self.capabilities.get("chat") is not False and (
            not (self.image_generation or self.image_edit)
            or self.capabilities.get("chat") is True
        )

    def claude_code_runtime_env(self) -> dict[str, str]:
        """Project configured model fields to the exact server-owned env keys."""

        env: dict[str, str] = {}
        if self.max_output_tokens is not None:
            env["INK_CLAUDE_CODE_MODEL_MAX_OUTPUT_TOKENS"] = str(
                self.max_output_tokens
            )
        if self.claude_code_auto_compact_window is not None:
            env["CLAUDE_CODE_AUTO_COMPACT_WINDOW"] = str(
                self.claude_code_auto_compact_window
            )
        if self.claude_code_max_context_tokens is not None:
            env["CLAUDE_CODE_MAX_CONTEXT_TOKENS"] = str(
                self.claude_code_max_context_tokens
            )
        return env

    def public_dict(self) -> dict[str, Any]:
        return {
            "modelAlias": self.model_alias,
            "displayName": self.display_name,
            "protocol": self.protocol,
            "capabilities": {
                **{key: value for key, value in self.capabilities.items() if key not in {"image_generation", "image_edit"}},
                **({"chat": False} if not self.is_conversation_model else {}),
            },
            "contextWindow": self.context_window,
            "maxOutputTokens": self.max_output_tokens,
            "enabled": self.enabled,
            "callable": self.callable and self.is_conversation_model,
            "availability": self.availability,
            "requiredPlanCode": self.required_plan_code,
            "upgradeHint": self.upgrade_hint,
            "images": {
                "generation": self.image_generation, "edit": self.image_edit,
                "configured": self.image_configured, "entitled": self.image_entitled,
                "callable": self.image_callable,
            },
            "responsesImage": self.responses_image or {
                "generation": False, "edit": False, "configured": False,
                "entitled": False, "callable": False,
            },
        }


@dataclass(frozen=True)
class GatewayModelCatalog:
    models: tuple[GatewayModel, ...]
    default_model_alias: str | None
    default_image_model_alias: str | None = None


def _optional_non_negative_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise GatewayInferenceError("GATEWAY_MODEL_CATALOG_INVALID", 502)
    return value


def _optional_positive_runtime_int(value: Any) -> int | None:
    if value is None:
        return None
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 1
        or value > _CLAUDE_CODE_RUNTIME_INTEGER_MAX
    ):
        raise GatewayInferenceError("GATEWAY_MODEL_CATALOG_INVALID", 502)
    return value


def _parse_model(raw: Any) -> GatewayModel:
    if not isinstance(raw, dict):
        raise GatewayInferenceError("GATEWAY_MODEL_CATALOG_INVALID", 502)
    legacy_keys = {
        "id", "display_name", "protocol", "capabilities",
        "context_window", "max_output_tokens", "enabled", "callable",
        "claude_code_auto_compact_window", "claude_code_max_context_tokens",
        "availability", "required_plan_code", "upgrade_hint",
    }
    image_keys = {"endpoint_availability", "image_input_token_reserve_per_image", "image_output_token_reserve_per_image"}
    if set(raw) not in (legacy_keys, legacy_keys | image_keys):
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
        or not set(capabilities).issubset(_PUBLIC_CAPABILITIES)
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
    endpoints = raw.get("endpoint_availability")
    image_callable = image_generation = image_edit = False
    messages_callable = callable_value
    if "endpoint_availability" in raw:
        if not isinstance(endpoints, dict) or set(endpoints) not in ({"messages", "chat", "images"}, {"messages", "chat", "images", "responses_image"}):
            raise GatewayInferenceError("GATEWAY_MODEL_CATALOG_INVALID", 502)
        for name, keys in (("messages", {"callable", "entitled"}), ("chat", {"callable", "entitled"}), ("images", {"callable", "entitled", "configured", "generation", "edit"})):
            endpoint = endpoints[name]
            if not isinstance(endpoint, dict) or set(endpoint) != keys or any(type(value) is not bool for value in endpoint.values()):
                raise GatewayInferenceError("GATEWAY_MODEL_CATALOG_INVALID", 502)
            if endpoint["callable"] and (not callable_value or not endpoint["entitled"]):
                raise GatewayInferenceError("GATEWAY_MODEL_CATALOG_INVALID", 502)
        images = endpoints["images"]
        if images["callable"] and (not images["configured"] or not (images["generation"] or images["edit"])):
            raise GatewayInferenceError("GATEWAY_MODEL_CATALOG_INVALID", 502)
        if images["generation"] != capabilities.get("image_generation", False) or images["edit"] != capabilities.get("image_edit", False):
            raise GatewayInferenceError("GATEWAY_MODEL_CATALOG_INVALID", 502)
        for key in image_keys - {"endpoint_availability"}:
            reserve = raw[key]
            if reserve is not None and (type(reserve) is not int or not 1 <= reserve <= 9_007_199_254_740_991):
                raise GatewayInferenceError("GATEWAY_MODEL_CATALOG_INVALID", 502)
        messages_callable = endpoints["messages"]["callable"]
        image_callable, image_generation, image_edit = images["callable"], images["generation"], images["edit"]
        native = endpoints.get("responses_image")
        if "responses_image" in endpoints:
            if (not isinstance(native, dict) or set(native) != {"callable", "entitled", "configured", "generation", "edit"}
                    or any(type(value) is not bool for value in native.values())
                    or native["callable"] and (not messages_callable or capabilities.get("chat") is False
                        or (image_generation or image_edit) and capabilities.get("chat") is not True
                        or not native["entitled"] or not native["configured"] or not (native["generation"] or native["edit"]))):
                raise GatewayInferenceError("GATEWAY_MODEL_CATALOG_INVALID", 502)
    elif set(capabilities) & {"image_generation", "image_edit"}:
        raise GatewayInferenceError("GATEWAY_MODEL_CATALOG_INVALID", 502)
    return GatewayModel(
        model_alias=alias,
        display_name=display_name.strip(),
        protocol=protocol,
        capabilities=dict(capabilities),
        context_window=_optional_non_negative_int(raw.get("context_window")),
        max_output_tokens=_optional_positive_runtime_int(raw.get("max_output_tokens")),
        claude_code_auto_compact_window=_optional_positive_runtime_int(
            raw.get("claude_code_auto_compact_window")
        ),
        claude_code_max_context_tokens=_optional_positive_runtime_int(
            raw.get("claude_code_max_context_tokens")
        ),
        enabled=True,
        callable=messages_callable,
        image_callable=image_callable,
        image_generation=image_generation,
        image_edit=image_edit,
        image_configured=endpoints["images"]["configured"] if endpoints else False,
        image_entitled=endpoints["images"]["entitled"] if endpoints else False,
        responses_image=endpoints.get("responses_image") if endpoints else None,
        availability=availability,
        required_plan_code=required_plan_code,
        upgrade_hint=upgrade_hint.strip() if upgrade_hint else None,
    )


class GatewayModelCatalogClient:
    def __init__(
        self,
        *,
        access_token: str,
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
        token = str(access_token).strip()
        if not _ACCESS_TOKEN.fullmatch(token):
            raise GatewayInferenceError("GATEWAY_UNAUTHORIZED", 401)
        self._access_token = token
        self.transport = transport

    def fetch_catalog(self, *, timeout: float = 10) -> GatewayModelCatalog:
        started = time.monotonic()
        try:
            response = self.transport.get(
                f"{self.configuration.base_url}/v1/models",
                headers={
                    "authorization": f"Bearer {self._access_token}",
                    "x-api-key": self.configuration.service_key,
                    "accept": "application/json",
                },
                timeout=timeout,
            )
        except Exception as exc:
            logger.warning("claude_agent_failure stage=model_catalog transport_error=%s elapsed_ms=%s",
                           type(exc).__name__, round((time.monotonic() - started) * 1000))
            raise GatewayInferenceError("GATEWAY_UNAVAILABLE", 503) from exc
        if response.status_code != 200:
            status = int(response.status_code)
            upstream_code = None
            try:
                payload = response.json()
                candidate = payload.get("error", {}).get("code")
                if isinstance(candidate, str) and _SAFE_GATEWAY_ERROR_CODE.fullmatch(candidate):
                    upstream_code = candidate
            except Exception:
                pass
            code = {
                401: "GATEWAY_UNAUTHORIZED",
                402: "GATEWAY_TOKEN_ALLOWANCE_EXHAUSTED",
                403: "GATEWAY_FORBIDDEN",
                409: "GATEWAY_CONFLICT",
                429: "GATEWAY_RATE_LIMITED",
                502: "GATEWAY_PROVIDER_FAILED",
                503: "GATEWAY_UNAVAILABLE",
            }.get(status, "GATEWAY_REQUEST_FAILED")
            logger.warning(
                "claude_agent_failure stage=model_catalog "
                "status=%s mapped_code=%s upstream_code=%s",
                status,
                code,
                upstream_code or "unavailable",
            )
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
            or default_alias not in {item["id"] for item in payload["data"] if item["callable"]}
        ):
            raise GatewayInferenceError("GATEWAY_MODEL_CATALOG_INVALID", 502)
        text_default = default_alias if any(m.model_alias == default_alias and m.callable and m.is_conversation_model for m in models) else None
        image_default = default_alias if any(m.model_alias == default_alias and m.image_callable for m in models) else None
        return GatewayModelCatalog(tuple(models), text_default, image_default)

    def list_models(self, *, timeout: float = 10) -> list[GatewayModel]:
        return [model for model in self.fetch_catalog(timeout=timeout).models if model.is_conversation_model]
