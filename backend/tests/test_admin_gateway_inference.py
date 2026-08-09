from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jwt
import pytest

from backend.services.admin_gateway.config import (
    AdminGatewayConfig,
    AdminGatewayConfigurationError,
)
from backend.services.admin_gateway.inference import (
    GatewayInferenceClient,
    GatewayInferenceError,
    GatewayInferenceModels,
    GatewayPolyAgent,
)


SERVICE_KEY = "gw_test_service_key_with_more_than_32_bytes"


@dataclass
class FakeResponse:
    status_code: int
    payload: Any

    def json(self) -> Any:
        return self.payload


class RecordingTransport:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return self.response


def configuration(enabled: bool = True) -> AdminGatewayConfig:
    return AdminGatewayConfig(
        enabled=enabled,
        base_url="http://127.0.0.1:3000",
        service_key=SERVICE_KEY,
        issuer="dream-test",
        audience="admin-gateway-test",
        client_id="dream-inference-test",
        token_lifetime_seconds=60,
    )


def models() -> GatewayInferenceModels:
    return GatewayInferenceModels(
        text="dream-text",
        image_description="dream-image-description",
        image_generation="dream-image",
    )


def test_openai_gateway_client_binds_canonical_subject_and_never_uses_provider_secret() -> None:
    transport = RecordingTransport(
        FakeResponse(
            200,
            {"choices": [{"message": {"content": "gateway result"}}]},
        )
    )
    client = GatewayInferenceClient(
        42,
        configuration=configuration(),
        models=models(),
        transport=transport,
    )

    payload = client.chat(
        messages=[{"role": "user", "content": "hello"}],
        model_alias="dream-text",
        max_tokens=200,
        timeout=12,
        idempotency_key="dream-inference-request-42",
    )

    assert client.text_content(payload) == "gateway result"
    call = transport.calls[0]
    assert call["url"] == "http://127.0.0.1:3000/v1/chat/completions"
    assert call["headers"]["x-api-key"] == SERVICE_KEY
    assert "provider" not in " ".join(call["headers"]).lower()
    token = call["headers"]["authorization"].removeprefix("Bearer ")
    claims = jwt.decode(
        token,
        SERVICE_KEY,
        algorithms=["HS256"],
        audience="admin-gateway-test",
        issuer="dream-test",
    )
    assert claims["sub"] == "42"
    assert claims["scope"] == "chat:create"
    assert call["json"]["model"] == "dream-text"
    assert call["json"]["stream"] is False


def test_gateway_polyagent_is_no_tools_and_has_no_direct_fallback() -> None:
    transport = RecordingTransport(
        FakeResponse(200, {"choices": [{"message": {"content": "ok"}}]})
    )
    client = GatewayInferenceClient(
        9,
        configuration=configuration(),
        models=models(),
        transport=transport,
    )
    agent = GatewayPolyAgent(9, agent_id="voice", client=client)
    result = agent.run("prompt", system_prompt="system", cli="no-tools")
    assert result.is_success is True
    assert result.content == "ok"
    assert transport.calls[0]["json"]["messages"] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "prompt"},
    ]
    with pytest.raises(GatewayInferenceError, match="GATEWAY_TOOLS_NOT_ALLOWED"):
        agent.run("prompt", cli="tools")


def test_disabled_or_failed_gateway_fails_closed_without_response_payload() -> None:
    with pytest.raises(AdminGatewayConfigurationError):
        GatewayInferenceClient(7, configuration=configuration(False), models=models())

    sensitive = "provider-secret-that-must-not-leak"
    transport = RecordingTransport(FakeResponse(502, {"detail": sensitive}))
    client = GatewayInferenceClient(
        7,
        configuration=configuration(),
        models=models(),
        transport=transport,
    )
    with pytest.raises(GatewayInferenceError) as captured:
        client.chat(
            messages=[{"role": "user", "content": "hello"}],
            model_alias="dream-text",
            max_tokens=32,
            timeout=1,
        )
    assert captured.value.code == "GATEWAY_PROVIDER_FAILED"
    assert sensitive not in str(captured.value)


def test_runtime_inference_entrypoints_have_no_direct_provider_transport() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    server_source = (backend_root / "server.py").read_text(encoding="utf-8")
    picture_source = (backend_root / "picture_service.py").read_text(encoding="utf-8")
    assert "PolyAgent(id=" not in server_source
    assert "GatewayPolyAgent(user_id" in server_source
    assert "requests.post" not in picture_source
    assert "IMAGE_API_ENDPOINT" not in picture_source
    assert "IMAGE_API_KEY" not in picture_source
