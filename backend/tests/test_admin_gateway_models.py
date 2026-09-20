from __future__ import annotations

# [Sync] 2026-09-19: verify safe upstream Gateway error-code logging without body or credential disclosure.

from dataclasses import dataclass
from typing import Any

import pytest

from backend.services.admin_gateway.config import AdminGatewayConfig
from backend.services.admin_gateway.errors import GatewayInferenceError
from backend.services.admin_gateway.models import GatewayModelCatalogClient


SERVICE_KEY = "gw_test_service_key_with_more_than_32_bytes"
ACCESS_TOKEN = "idg_" + "a" * 43


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
            "claude_code_auto_compact_window": 262144,
            "claude_code_max_context_tokens": 262144,
            "capabilities": {"tools": True},
            "enabled": True,
            "callable": True,
            "availability": "included",
            "required_plan_code": "free",
            "upgrade_hint": None,
        }],
        "default_model_alias": "dream-balanced",
    }))
    catalog = GatewayModelCatalogClient(
        access_token=ACCESS_TOKEN,
        configuration=configuration(),
        transport=transport,
    ).fetch_catalog()

    assert catalog.default_model_alias == "dream-balanced"
    assert catalog.models[0].public_dict() == {
        "modelAlias": "dream-balanced",
        "displayName": "Dream Balanced",
        "protocol": "anthropic",
        "capabilities": {"tools": True},
        "contextWindow": 200000,
        "maxOutputTokens": 8192,
        "enabled": True,
        "callable": True,
        "availability": "included",
        "requiredPlanCode": "free",
        "upgradeHint": None,
    }
    assert catalog.models[0].claude_code_runtime_env() == {
        "INK_CLAUDE_CODE_MODEL_MAX_OUTPUT_TOKENS": "8192",
        "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "262144",
        "CLAUDE_CODE_MAX_CONTEXT_TOKENS": "262144",
    }
    call = transport.calls[0]
    assert call["url"] == "http://127.0.0.1:3000/v1/models"
    assert call["headers"]["authorization"] == f"Bearer {ACCESS_TOKEN}"
    assert call["headers"]["x-api-key"] == SERVICE_KEY


def test_catalog_rejects_malformed_or_duplicate_aliases() -> None:
    malformed = RecordingTransport(FakeResponse(200, {
        "object": "list",
        "data": [{"id": "unsafe alias"}],
        "default_model_alias": None,
    }))
    with pytest.raises(GatewayInferenceError, match="GATEWAY_MODEL_CATALOG_INVALID"):
        GatewayModelCatalogClient(
            access_token=ACCESS_TOKEN,
            configuration=configuration(),
            transport=malformed,
        ).list_models()


def test_catalog_logs_safe_upstream_authentication_code(caplog: pytest.LogCaptureFixture) -> None:
    transport = RecordingTransport(FakeResponse(401, {
        "error": {
            "type": "authentication_error",
            "code": "GATEWAY_API_KEY_INVALID",
            "message": "private upstream text must not be logged",
        },
    }))

    with pytest.raises(GatewayInferenceError, match="GATEWAY_UNAUTHORIZED"):
        GatewayModelCatalogClient(
            access_token=ACCESS_TOKEN,
            configuration=configuration(),
            transport=transport,
        ).fetch_catalog()

    assert "claude_agent_failure stage=model_catalog" in caplog.text
    assert "status=401" in caplog.text
    assert "mapped_code=GATEWAY_UNAUTHORIZED" in caplog.text
    assert "upstream_code=GATEWAY_API_KEY_INVALID" in caplog.text
    assert "private upstream text" not in caplog.text
    assert ACCESS_TOKEN not in caplog.text
    assert SERVICE_KEY not in caplog.text


def test_catalog_rejects_capabilities_outside_the_public_allowlist() -> None:
    transport = RecordingTransport(FakeResponse(200, {
        "object": "list",
        "data": [{
            "id": "dream-balanced",
            "display_name": "Dream Balanced",
            "protocol": "anthropic",
            "context_window": 200000,
            "max_output_tokens": 8192,
            "claude_code_auto_compact_window": None,
            "claude_code_max_context_tokens": None,
            "capabilities": {"tools": True, "provider_debug": True},
            "enabled": True,
            "callable": True,
            "availability": "included",
            "required_plan_code": None,
            "upgrade_hint": None,
        }],
        "default_model_alias": "dream-balanced",
    }))

    with pytest.raises(GatewayInferenceError, match="GATEWAY_MODEL_CATALOG_INVALID"):
        GatewayModelCatalogClient(
            access_token=ACCESS_TOKEN,
            configuration=configuration(),
            transport=transport,
        ).list_models()


def test_catalog_rejects_non_positive_model_max_output_capability() -> None:
    transport = RecordingTransport(FakeResponse(200, {
        "object": "list",
        "data": [{
            "id": "dream-balanced",
            "display_name": "Dream Balanced",
            "protocol": "anthropic",
            "context_window": 200000,
            "max_output_tokens": 0,
            "claude_code_auto_compact_window": None,
            "claude_code_max_context_tokens": None,
            "capabilities": {"tools": True},
            "enabled": True,
            "callable": True,
            "availability": "included",
            "required_plan_code": None,
            "upgrade_hint": None,
        }],
        "default_model_alias": "dream-balanced",
    }))
    with pytest.raises(GatewayInferenceError, match="GATEWAY_MODEL_CATALOG_INVALID"):
        GatewayModelCatalogClient(
            access_token=ACCESS_TOKEN,
            configuration=configuration(),
            transport=transport,
        ).list_models()


@pytest.mark.parametrize("runtime_value", [0, -1, 2_147_483_648, True, "262144"])
def test_catalog_rejects_invalid_claude_code_runtime_windows(runtime_value: Any) -> None:
    transport = RecordingTransport(FakeResponse(200, {
        "object": "list",
        "data": [{
            "id": "dream-balanced",
            "display_name": "Dream Balanced",
            "protocol": "anthropic",
            "context_window": 200000,
            "max_output_tokens": 8192,
            "claude_code_auto_compact_window": runtime_value,
            "claude_code_max_context_tokens": None,
            "capabilities": {"tools": True},
            "enabled": True,
            "callable": True,
            "availability": "included",
            "required_plan_code": None,
            "upgrade_hint": None,
        }],
        "default_model_alias": "dream-balanced",
    }))
    with pytest.raises(GatewayInferenceError, match="GATEWAY_MODEL_CATALOG_INVALID"):
        GatewayModelCatalogClient(
            access_token=ACCESS_TOKEN,
            configuration=configuration(),
            transport=transport,
        ).list_models()
