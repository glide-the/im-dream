from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .config import AdminGatewayConfig
from .token import issue_gateway_subject_token


def gateway_enabled(environment: Mapping[str, str] | None = None) -> bool:
    return AdminGatewayConfig.from_environment(environment).enabled


def apply_gateway_sdk_env_to_options(
    options: Any,
    canonical_user_id: str | None,
    *,
    environment: Mapping[str, str] | None = None,
    configuration: AdminGatewayConfig | None = None,
) -> Any:
    """Force the Claude SDK through Admin Gateway when the canary is enabled.

    This function must run after project and user environment overlays. It
    overwrites provider authentication/routing and never falls back when an
    enabled Gateway configuration or canonical subject is invalid.
    """

    configured = configuration or AdminGatewayConfig.from_environment(environment)
    if not configured.enabled:
        return options
    token = issue_gateway_subject_token(configured, canonical_user_id or "")
    existing = getattr(options, "env", None) or {}
    env = dict(existing)
    env.pop("ANTHROPIC_API_KEY", None)
    env["ANTHROPIC_BASE_URL"] = configured.base_url
    env["ANTHROPIC_AUTH_TOKEN"] = token
    env["ANTHROPIC_CUSTOM_HEADERS"] = f"x-api-key: {configured.service_key}"
    options.env = env
    return options
