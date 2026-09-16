# [Input] SDK options, an Admin-issued entity delegation and server-owned Gateway routing.
# [Output] Force Claude Code through Admin Gateway with an entity-bound opaque bearer.
# [Pos] Runtime credential boundary; service keys and Dream signing authority never enter the child.
# [Sync] 2026-09-16: consume Admin gateway-cli delegations and retire the local apiKeyHelper signer.
from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from libs.claude_agent_kit.server.sdk_env import (
    apply_gateway_credential_tombstones,
)

from .config import AdminGatewayConfig, AdminGatewayConfigurationError


_DELEGATION_TOKEN = re.compile(r"^idg_[A-Za-z0-9_-]{43}$")


def gateway_sdk_helper_is_configured(options: Any) -> bool:
    """Verify the exact Admin delegation projection without logging it."""

    env = getattr(options, "env", None)
    if not isinstance(env, dict):
        return False
    enabled = str(env.get("INK_GATEWAY_ENABLED", "")).strip().lower()
    base_url = str(env.get("INK_GATEWAY_BASE_URL", "")).strip()
    return bool(
        enabled in {"1", "true", "yes", "on"}
        and base_url
        and env.get("ANTHROPIC_BASE_URL") == base_url
        and _DELEGATION_TOKEN.fullmatch(
            str(env.get("ANTHROPIC_AUTH_TOKEN", ""))
        )
        and not env.get("INK_GATEWAY_SERVICE_KEY")
    )


def gateway_enabled(environment: Mapping[str, str] | None = None) -> bool:
    return AdminGatewayConfig.from_environment(environment).enabled


def apply_gateway_sdk_env_to_options(
    options: Any,
    delegation_token: str | None,
    *,
    gateway_idempotency_key: str | None = None,
    environment: Mapping[str, str] | None = None,
    configuration: AdminGatewayConfig | None = None,
) -> Any:
    """Install an Admin-owned entity credential after every user/project overlay."""

    configured = configuration or AdminGatewayConfig.from_environment(environment)
    if not configured.enabled:
        return options
    token = str(delegation_token or "").strip()
    if not _DELEGATION_TOKEN.fullmatch(token):
        raise AdminGatewayConfigurationError(
            "Admin Gateway integration requires an Admin-issued delegation"
        )
    existing = getattr(options, "env", None) or {}
    env = dict(existing)
    apply_gateway_credential_tombstones(env)
    env["ANTHROPIC_BASE_URL"] = configured.base_url
    env["ANTHROPIC_AUTH_TOKEN"] = token
    if gateway_idempotency_key is not None:
        if re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._:-]{0,254}",
            gateway_idempotency_key,
        ) is None:
            raise AdminGatewayConfigurationError(
                "Gateway turn idempotency key is invalid"
            )
        # The Gateway derives request-level keys from the stable turn root and
        # exact body, so a multi-step tool loop remains distinct and retryable.
        env["ANTHROPIC_CUSTOM_HEADERS"] = (
            f"x-ink-turn-idempotency-key: {gateway_idempotency_key}"
        )
    env["INK_GATEWAY_ENABLED"] = "1"
    env["INK_GATEWAY_BASE_URL"] = configured.base_url
    options.env = env
    return options
