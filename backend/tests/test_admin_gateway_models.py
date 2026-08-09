from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import jwt
import pytest

from backend.services.admin_gateway.config import AdminGatewayConfig
from backend.services.admin_gateway.inference import GatewayInferenceError
from backend.services.admin_gateway.models import GatewayModelCatalogClient


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

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return self.response


def configuration() -> AdminGatewayConfig:
    return AdminGatewayConfig(
        enabled=True,
        base_url="http://127.0.0.1:3000",
        service_key=SERVICE_KEY,
        issuer="dream-test",
        audience="admin-gateway-test",
        client_id="dream-model-catalog-test",
        token_lifetime_seconds=60,
    )


def test_catalog_uses_models_scope_and_strict_public_projection() -> None:
    transport = RecordingTransport(FakeResponse(200, {
        "object": "list",
        "data": [{
            "id": "dream-balanced",
            "display_name": "Dream Balanced",
            "protocol": "anthropic",
            "context_window": 200000,
            "max_output_tokens": 8192,
            "capabilities": {"tools": True},
            "gateway_scopes": ["messages:create", "models:list"],
            "owned_by": "internal-provider",
        }],
    }))
    models = GatewayModelCatalogClient(
        42,
        configuration=configuration(),
        transport=transport,
    ).list_models()

    assert models[0].public_dict() == {
        "modelAlias": "dream-balanced",
        "displayName": "Dream Balanced",
        "protocol": "anthropic",
        "capabilities": {"tools": True},
        "gatewayScopes": ["messages:create", "models:list"],
        "contextWindow": 200000,
        "maxOutputTokens": 8192,
    }
    call = transport.calls[0]
    assert call["url"] == "http://127.0.0.1:3000/v1/models"
    claims = jwt.decode(
        call["headers"]["authorization"].removeprefix("Bearer "),
        SERVICE_KEY,
        algorithms=["HS256"],
        audience="admin-gateway-test",
        issuer="dream-test",
    )
    assert claims["sub"] == "42"
    assert claims["scope"] == "models:list"


def test_catalog_rejects_malformed_or_duplicate_aliases() -> None:
    malformed = RecordingTransport(FakeResponse(200, {
        "object": "list",
        "data": [{"id": "unsafe alias"}],
    }))
    with pytest.raises(GatewayInferenceError, match="GATEWAY_MODEL_CATALOG_INVALID"):
        GatewayModelCatalogClient(
            7,
            configuration=configuration(),
            transport=malformed,
        ).list_models()

