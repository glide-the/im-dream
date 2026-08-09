from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import jwt
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.admin_gateway.config import (
    AdminGatewayConfig,
    AdminGatewayConfigurationError,
)
from services.admin_gateway.sdk import apply_gateway_sdk_env_to_options
from services.admin_gateway.token import issue_gateway_subject_token


@dataclass
class Options:
    env: dict[str, str] = field(default_factory=dict)


def configured_environment() -> dict[str, str]:
    return {
        "INK_GATEWAY_CLAUDE_AGENT_ENABLED": "true",
        "INK_GATEWAY_BASE_URL": "https://admin.example.test",
        "INK_GATEWAY_SERVICE_KEY": "gw_" + "k" * 43,
        "INK_GATEWAY_SUBJECT_JWT_ISSUER": "https://dream.example.test",
        "INK_GATEWAY_SUBJECT_JWT_AUDIENCE": "ink-memory-gateway",
        "INK_GATEWAY_SERVICE_CLIENT_ID": "dream-bff",
        "INK_GATEWAY_SUBJECT_TOKEN_LIFETIME_SECONDS": "240",
    }


def test_disabled_gateway_preserves_existing_provider_environment():
    options = Options(env={"ANTHROPIC_AUTH_TOKEN": "legacy"})
    apply_gateway_sdk_env_to_options(options, "7", environment={})
    assert options.env == {"ANTHROPIC_AUTH_TOKEN": "legacy"}


def test_enabled_gateway_overrides_user_routing_and_binds_canonical_subject():
    values = configured_environment()
    options = Options(
        env={
            "ANTHROPIC_AUTH_TOKEN": "user-override",
            "ANTHROPIC_BASE_URL": "https://bypass.example",
            "ANTHROPIC_API_KEY": "legacy-secret",
        }
    )

    apply_gateway_sdk_env_to_options(options, "205", environment=values)

    assert options.env["ANTHROPIC_BASE_URL"] == "https://admin.example.test"
    assert options.env["ANTHROPIC_CUSTOM_HEADERS"] == (
        "x-api-key: " + values["INK_GATEWAY_SERVICE_KEY"]
    )
    assert "ANTHROPIC_API_KEY" not in options.env
    payload = jwt.decode(
        options.env["ANTHROPIC_AUTH_TOKEN"],
        values["INK_GATEWAY_SERVICE_KEY"],
        algorithms=["HS256"],
        audience=values["INK_GATEWAY_SUBJECT_JWT_AUDIENCE"],
        issuer=values["INK_GATEWAY_SUBJECT_JWT_ISSUER"],
    )
    assert payload["sub"] == "205"
    assert payload["client_id"] == "dream-bff"
    assert payload["azp"] == "dream-bff"
    assert payload["scope"] == "messages:create"
    assert payload["exp"] - payload["iat"] == 240
    assert payload["jti"]


def test_enabled_gateway_fails_closed_for_missing_subject_or_configuration():
    with pytest.raises(AdminGatewayConfigurationError):
        apply_gateway_sdk_env_to_options(
            Options(),
            None,
            environment=configured_environment(),
        )
    incomplete = configured_environment()
    incomplete.pop("INK_GATEWAY_SERVICE_KEY")
    with pytest.raises(AdminGatewayConfigurationError):
        apply_gateway_sdk_env_to_options(Options(), "7", environment=incomplete)


def test_gateway_config_repr_and_errors_do_not_expose_secret_values():
    values = configured_environment()
    config = AdminGatewayConfig.from_environment(values)
    assert values["INK_GATEWAY_SERVICE_KEY"] not in repr(config)
    with pytest.raises(AdminGatewayConfigurationError) as error:
        issue_gateway_subject_token(config, "not-a-user")
    assert values["INK_GATEWAY_SERVICE_KEY"] not in str(error.value)


def test_gateway_rejects_header_injection_and_non_https_remote_urls():
    values = configured_environment()
    values["INK_GATEWAY_SERVICE_KEY"] += "\nAuthorization: bad"
    with pytest.raises(AdminGatewayConfigurationError):
        AdminGatewayConfig.from_environment(values)
    values = configured_environment()
    values["INK_GATEWAY_BASE_URL"] = "http://admin.example.test"
    with pytest.raises(AdminGatewayConfigurationError):
        AdminGatewayConfig.from_environment(values)
