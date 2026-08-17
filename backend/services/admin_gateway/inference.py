"""Canonical-subject OpenAI-compatible client for non-Claude Dream inference."""

from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Any, Mapping, Protocol
import uuid

import requests

from .config import AdminGatewayConfig, AdminGatewayConfigurationError
from .token import issue_gateway_subject_token


_MODEL_ALIAS = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$")


class GatewayInferenceError(RuntimeError):
    """Value-free inference failure safe for logs and API mapping."""

    def __init__(self, code: str, status_code: int = 503) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


class JsonTransport(Protocol):
    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        json: Mapping[str, Any],
        timeout: float,
    ) -> Any: ...


def _required_alias(values: Mapping[str, str], name: str, fallback: str = "") -> str:
    value = values.get(name, "").strip() or fallback
    if not _MODEL_ALIAS.fullmatch(value):
        raise AdminGatewayConfigurationError(
            "Dream inference Gateway model aliases are not safely configured"
        )
    return value


@dataclass(frozen=True)
class GatewayInferenceModels:
    text: str
    image_description: str
    image_generation: str

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> "GatewayInferenceModels":
        values = os.environ if environment is None else environment
        text = _required_alias(values, "INK_GATEWAY_TEXT_MODEL_ALIAS")
        return cls(
            text=text,
            image_description=_required_alias(
                values, "INK_GATEWAY_IMAGE_DESCRIPTION_MODEL_ALIAS", text
            ),
            image_generation=_required_alias(
                values, "INK_GATEWAY_IMAGE_GENERATION_MODEL_ALIAS"
            ),
        )


class GatewayInferenceClient:
    def __init__(
        self,
        canonical_user_id: int | str,
        *,
        configuration: AdminGatewayConfig | None = None,
        models: GatewayInferenceModels | None = None,
        environment: Mapping[str, str] | None = None,
        transport: JsonTransport = requests,
    ) -> None:
        self.configuration = configuration or AdminGatewayConfig.from_environment(
            environment
        )
        if not self.configuration.enabled:
            raise AdminGatewayConfigurationError(
                "Dream inference requires the Admin Gateway"
            )
        self.models = models or GatewayInferenceModels.from_environment(environment)
        self.canonical_user_id = str(canonical_user_id)
        self.transport = transport

    def chat(
        self,
        *,
        messages: list[dict[str, Any]],
        model_alias: str,
        max_tokens: int,
        timeout: float,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if not _MODEL_ALIAS.fullmatch(model_alias):
            raise GatewayInferenceError("GATEWAY_MODEL_ALIAS_INVALID")
        token = issue_gateway_subject_token(
            self.configuration,
            self.canonical_user_id,
            scope="chat:create",
        )
        headers = {
            "authorization": f"Bearer {token}",
            "x-api-key": self.configuration.service_key,
            "content-type": "application/json",
            "idempotency-key": idempotency_key or f"dream-{uuid.uuid4().hex}",
        }
        try:
            response = self.transport.post(
                f"{self.configuration.base_url}/v1/chat/completions",
                headers=headers,
                json={
                    "model": model_alias,
                    "messages": messages,
                    "max_completion_tokens": max_tokens,
                    "stream": False,
                },
                timeout=timeout,
            )
        except Exception as exc:
            raise GatewayInferenceError("GATEWAY_UNAVAILABLE") from exc
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
            raise GatewayInferenceError("GATEWAY_RESPONSE_INVALID", 502) from exc
        if not isinstance(payload, dict):
            raise GatewayInferenceError("GATEWAY_RESPONSE_INVALID", 502)
        return payload

    @staticmethod
    def text_content(payload: Mapping[str, Any]) -> str:
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise GatewayInferenceError("GATEWAY_RESPONSE_INVALID", 502) from exc
        if not isinstance(content, str) or not content.strip():
            raise GatewayInferenceError("GATEWAY_RESPONSE_INVALID", 502)
        return content.strip()


@dataclass(frozen=True)
class GatewayAgentResult:
    is_success: bool
    content: str | None


class GatewayPolyAgent:
    """PolyAgent-compatible no-tools adapter with no direct-provider fallback."""

    def __init__(
        self,
        canonical_user_id: int | str,
        *,
        agent_id: str,
        client: GatewayInferenceClient | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.client = client or GatewayInferenceClient(canonical_user_id)

    def run(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        model: str | None = None,
        cli: str = "no-tools",
        tracked: bool = True,
        **_: Any,
    ) -> GatewayAgentResult:
        del model, tracked
        if cli != "no-tools":
            raise GatewayInferenceError("GATEWAY_TOOLS_NOT_ALLOWED")
        messages: list[dict[str, str]] = []
        if system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = self.client.chat(
            messages=messages,
            model_alias=self.client.models.text,
            max_tokens=8_192,
            timeout=120,
        )
        return GatewayAgentResult(
            is_success=True,
            content=self.client.text_content(payload),
        )
