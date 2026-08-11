from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
import re
import shlex
import sys
from typing import Any

from .config import AdminGatewayConfig, AdminGatewayConfigurationError
from .token import validate_gateway_subject


def _gateway_helper_command() -> str:
    return shlex.join(
        [sys.executable, "-m", "services.admin_gateway.subject_token_helper"]
    )


def _install_gateway_helper_settings(options: Any) -> None:
    existing = getattr(options, "settings", None)
    if existing:
        try:
            payload = json.loads(existing)
        except (TypeError, ValueError) as exc:
            raise AdminGatewayConfigurationError(
                "Admin Gateway integration is enabled but not safely configured"
            ) from exc
        if not isinstance(payload, dict):
            raise AdminGatewayConfigurationError(
                "Admin Gateway integration is enabled but not safely configured"
            )
    else:
        payload = {}
    # Flag settings have higher precedence than workspace/project settings, so
    # a packed plugin cannot replace the server-owned token issuer.
    payload["apiKeyHelper"] = _gateway_helper_command()
    options.settings = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def gateway_sdk_helper_is_configured(options: Any) -> bool:
    """Verify the exact server-owned helper contract without logging secrets."""

    env = getattr(options, "env", None)
    if not isinstance(env, dict):
        return False
    try:
        configuration = AdminGatewayConfig.from_environment(env)
        subject = validate_gateway_subject(
            str(env.get("INK_GATEWAY_CANONICAL_SUBJECT", ""))
        )
        settings = json.loads(getattr(options, "settings", None) or "")
    except (AdminGatewayConfigurationError, TypeError, ValueError):
        return False
    if not isinstance(settings, dict):
        return False
    return bool(
        configuration.enabled
        and subject
        and settings.get("apiKeyHelper") == _gateway_helper_command()
        and env.get("ANTHROPIC_BASE_URL") == configuration.base_url
        and env.get("CLAUDE_CODE_API_KEY_HELPER_TTL_MS")
        and env.get("PYTHONPATH") == str(Path(__file__).resolve().parents[2])
        and str(env.get("ANTHROPIC_CUSTOM_HEADERS", "")).startswith(
            f"x-api-key: {configuration.service_key}"
        )
    )


def gateway_enabled(environment: Mapping[str, str] | None = None) -> bool:
    return AdminGatewayConfig.from_environment(environment).enabled


def apply_gateway_sdk_env_to_options(
    options: Any,
    canonical_user_id: str | None,
    *,
    gateway_idempotency_key: str | None = None,
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
    subject = validate_gateway_subject(canonical_user_id or "")
    existing = getattr(options, "env", None) or {}
    env = dict(existing)
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("ANTHROPIC_AUTH_TOKEN", None)
    env["ANTHROPIC_BASE_URL"] = configured.base_url
    custom_headers = f"x-api-key: {configured.service_key}"
    if gateway_idempotency_key is not None:
        if re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._:-]{0,254}",
            gateway_idempotency_key,
        ) is None:
            raise AdminGatewayConfigurationError(
                "Gateway turn idempotency key is invalid"
            )
        # One Claude Agent turn may contain several provider requests as the
        # model consumes tool results.  The Admin Gateway owns derivation of a
        # stable request-level key from this turn root plus the exact body;
        # sending the root as Idempotency-Key would incorrectly collapse the
        # second tool-loop request into the first reservation.
        custom_headers += (
            f"\nx-ink-turn-idempotency-key: {gateway_idempotency_key}"
        )
    env["ANTHROPIC_CUSTOM_HEADERS"] = custom_headers
    # Claude Code caches apiKeyHelper results. Refresh well inside the short
    # subject-token lifetime; if a request still reaches 401 after a long tool
    # wait, Claude Code clears this cache and retries with a freshly issued JWT.
    env["CLAUDE_CODE_API_KEY_HELPER_TTL_MS"] = str(
        max(1, configured.token_lifetime_seconds // 2) * 1000
    )
    env["INK_GATEWAY_ENABLED"] = "1"
    env["INK_GATEWAY_BASE_URL"] = configured.base_url
    env["INK_GATEWAY_SERVICE_KEY"] = configured.service_key
    env["INK_GATEWAY_SUBJECT_JWT_ISSUER"] = configured.issuer
    env["INK_GATEWAY_SUBJECT_JWT_AUDIENCE"] = configured.audience
    env["INK_GATEWAY_SERVICE_CLIENT_ID"] = configured.client_id
    env["INK_GATEWAY_SUBJECT_TOKEN_LIFETIME_SECONDS"] = str(
        configured.token_lifetime_seconds
    )
    env["INK_GATEWAY_CANONICAL_SUBJECT"] = subject
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
    options.env = env
    _install_gateway_helper_settings(options)
    return options
