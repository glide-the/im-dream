#!/usr/bin/env python3
# [Input] Consume database system-config APIs and shared auth dependency.
# [Output] Register GET/PUT /api/system-config endpoints.
# [Pos] system-config route node in backend/routers
# [Sync] 2026-05-27: initial implementation — system config (model, theme, env_vars, etc.).
# [Sync] 2026-06-09: accept im_full_access_enabled for Settings-controlled
#                    Claude-agent full-access tool approval.
# [Sync] 2026-06-13: workspace_enabled also controls per-thread Claude Code
#                    Bash sandbox settings written into .claude/settings.json.
# [Sync] 2026-06-21: accept sandbox network policy and allowed domains.
# [Sync] 2026-06-25: return merged config from PUT so Settings can hydrate
#                    sanitized sandbox-network values after save.
# [Sync] 2026-07-26: accept sandbox_fs_allowed_write_paths — extra absolute
#                    writable paths for the per-thread Bash sandbox
#                    (absolute-only, trailing-slash stripped, deduped, capped).
# [Sync] 2026-08-30: reserve INK_AGENT_SANDBOX_ENABLED for deployment-owned
#                    process configuration; user env_vars cannot override it.

"""System configuration API.

Endpoints
---------
GET  /api/system-config  — retrieve the caller's system config
PUT  /api/system-config  — merge a partial update into the caller's system config

The system config is a freeform dict stored per user.  Known fields:

  provider         : str  — LLM provider ("anthropic" | "openai")
  model            : str  — model name
  system_prompt    : str  — custom system prompt for the AI agent
  workspace_enabled: bool — whether the workspace file sidebar and per-thread
                            cwd/context are active; sandbox enablement is a
                            separate deployment-owned environment capability
  sandbox_network_mode: str — per-thread Bash sandbox network policy
                            ("disabled" | "allowlist" | "open")
  sandbox_network_allowed_domains: list[str] — domains pre-allowed when the
                            sandbox network policy is "allowlist"
  sandbox_fs_allowed_write_paths: list[str] — additional absolute paths the
                            per-thread Bash sandbox may write (appended to
                            filesystem.allowWrite after the thread workspace
                            and Claude Code's own sandbox TMPDIR)
  im_full_access_enabled: bool — whether Claude-agent PreToolUse approvals
                            should allow exposed tools automatically except
                            AskUserQuestion-style answer forms
  theme            : str  — UI theme ("light" | "dark" | "system")
  env_vars         : dict — user-supplied env vars forwarded to skills/MCP servers
                            as key→value string pairs
"""

from __future__ import annotations

import asyncio
import re
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException

import database
from services.admin_gateway import GatewayInferenceError, GatewayModelCatalogClient
from .deps import get_current_user

router = APIRouter()

# Keys that must be string→string when present in env_vars to prevent injection
_ENV_VAR_KEY_MAX_LEN = 256
_ENV_VAR_VALUE_MAX_LEN = 4096
_ENV_VARS_MAX_ENTRIES = 64
_SECRET_ENV_KEY_PATTERN = re.compile(
    r"(?:^|_)(?:API_KEY|AUTH_TOKEN|ACCESS_TOKEN|REFRESH_TOKEN|TOKEN|SECRET|"
    r"PASSWORD|PASSPHRASE|PRIVATE_KEY|CREDENTIAL|AUTHORIZATION)(?:$|_)",
    re.IGNORECASE,
)
_SERVER_CONTROLLED_ENV_KEYS = frozenset(
    {
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_MODEL",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL",
        "ANTHROPIC_DEFAULT_SONNET_MODEL",
        "ANTHROPIC_DEFAULT_OPUS_MODEL",
        "OPENAI_BASE_URL",
        "INK_ADMIN_PRODUCT_API_BASE_URL",
        "INK_ADMIN_PRODUCT_JWT_ISSUER",
        "INK_ADMIN_PRODUCT_JWT_AUDIENCE",
        "INK_ADMIN_PRODUCT_CLIENT_ID",
        "INK_ADMIN_PRODUCT_ORIGIN",
        "INK_GATEWAY_BASE_URL",
        "INK_GATEWAY_SERVICE_CLIENT_ID",
        "INK_AGENT_SANDBOX_ENABLED",
    }
)
_SANDBOX_NETWORK_MODES = {"disabled", "allowlist", "open"}
_SANDBOX_NETWORK_ALLOWED_DOMAIN_MAX_ENTRIES = 64
_SANDBOX_NETWORK_ALLOWED_DOMAIN_MAX_LEN = 253
_SANDBOX_FS_ALLOWED_WRITE_PATH_MAX_ENTRIES = 32
_SANDBOX_FS_ALLOWED_WRITE_PATH_MAX_LEN = 512
_SANDBOX_DOMAIN_PATTERN = re.compile(
    r"^(?:\*\.)?(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"
)
_MODEL_ALIAS_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$")


def _gateway_error(exc: GatewayInferenceError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": "The platform model catalog is unavailable."},
    )


def _sanitize_env_vars(raw: object) -> dict[str, str]:
    """Validate and normalise env_vars from the request body.

    Accepts only a flat dict[str, str].  Keys and values are trimmed and
    truncated; keys must be non-empty after trimming.  At most
    ``_ENV_VARS_MAX_ENTRIES`` entries are accepted (excess entries are
    silently dropped).
    """
    if not isinstance(raw, dict):
        return {}
    result: dict[str, str] = {}
    for key, value in raw.items():
        k = str(key).strip()[: _ENV_VAR_KEY_MAX_LEN]
        v = str(value).strip()[: _ENV_VAR_VALUE_MAX_LEN]
        if _is_sensitive_or_server_controlled_env_key(k):
            raise HTTPException(
                status_code=400,
                detail="Secret-like and provider-routing environment variables cannot be stored in user settings",
            )
        if k:
            result[k] = v
        if len(result) >= _ENV_VARS_MAX_ENTRIES:
            break
    return result


def _is_sensitive_or_server_controlled_env_key(key: str) -> bool:
    normalized = key.strip().upper()
    return bool(
        normalized in _SERVER_CONTROLLED_ENV_KEYS
        or _SECRET_ENV_KEY_PATTERN.search(normalized)
    )


def _public_system_config(raw: object) -> dict:
    """Drop legacy secret-like values before a system config reaches a client."""

    if not isinstance(raw, dict):
        return {}
    public = dict(raw)
    env_vars = public.get("env_vars")
    if isinstance(env_vars, dict):
        public["env_vars"] = {
            str(key): str(value)
            for key, value in env_vars.items()
            if not _is_sensitive_or_server_controlled_env_key(str(key))
        }
    return public


def _domain_candidate(raw: object) -> str:
    """Extract a hostname-like sandbox domain pattern from user input."""

    value = str(raw).strip().lower()
    if not value:
        return ""
    parsed = urlparse(value if "://" in value else f"//{value}")
    host = parsed.hostname or value.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    host = host.strip().rstrip(".")[:_SANDBOX_NETWORK_ALLOWED_DOMAIN_MAX_LEN]
    if value.startswith("*.") and not host.startswith("*."):
        host = f"*.{host}"
    return host


def _sanitize_sandbox_network_allowed_domains(raw: object) -> list[str]:
    """Validate and normalize sandbox network allowed-domain patterns."""

    if isinstance(raw, str):
        items: list[object] = re.split(r"[\s,;]+", raw)
    elif isinstance(raw, list):
        items = raw
    else:
        return []

    result: list[str] = []
    for item in items:
        domain = _domain_candidate(item)
        if (
            domain
            and domain != "*"
            and _SANDBOX_DOMAIN_PATTERN.match(domain)
            and domain not in result
        ):
            result.append(domain)
        if len(result) >= _SANDBOX_NETWORK_ALLOWED_DOMAIN_MAX_ENTRIES:
            break
    return result


def _sanitize_sandbox_fs_allowed_write_paths(raw: object) -> list[str]:
    """Validate and normalize sandbox filesystem extra writable paths.

    Mirrors the domains sanitizer's reject-silently policy: accepts a list
    (or a whitespace/comma/semicolon separated string), keeps only absolute
    paths, strips trailing slashes (except the root ``/``), dedupes
    preserving order, and caps entry count / path length.
    """

    if isinstance(raw, str):
        items: list[object] = re.split(r"[\n,;]+", raw)
    elif isinstance(raw, list):
        items = raw
    else:
        return []

    result: list[str] = []
    for item in items:
        path = str(item).strip()
        if not path or not path.startswith("/"):
            continue
        path = (path.rstrip("/") or "/")[: _SANDBOX_FS_ALLOWED_WRITE_PATH_MAX_LEN]
        if path not in result:
            result.append(path)
        if len(result) >= _SANDBOX_FS_ALLOWED_WRITE_PATH_MAX_ENTRIES:
            break
    return result


@router.get("/api/system-config")
def get_system_config(current_user: dict = Depends(get_current_user)):
    """Return the caller's system configuration."""
    user_id = current_user["user_id"]
    return _public_system_config(database.get_system_config(user_id))


@router.put("/api/system-config")
async def put_system_config(
    request: dict,
    current_user: dict = Depends(get_current_user),
):
    """Merge *request* into the caller's system configuration.

    Accepted keys: ``provider``, ``model``, ``system_prompt``,
    ``workspace_enabled``, ``sandbox_network_mode``,
    ``sandbox_network_allowed_domains``, ``sandbox_fs_allowed_write_paths``,
    ``im_full_access_enabled``, ``theme``, ``env_vars``.
    Unknown keys are ignored.
    """
    user_id = current_user["user_id"]

    patch: dict = {}

    if "provider" in request and str(request["provider"]).strip() != "gateway":
        raise HTTPException(
            status_code=400,
            detail="AI provider routing is controlled by the Admin Gateway",
        )
    if "model" in request:
        model_alias = str(request["model"]).strip()
        if not _MODEL_ALIAS_PATTERN.fullmatch(model_alias):
            raise HTTPException(status_code=422, detail="Invalid platform model alias")
        try:
            catalog = await asyncio.to_thread(
                GatewayModelCatalogClient(user_id).fetch_catalog
            )
        except GatewayInferenceError as exc:
            raise _gateway_error(exc) from exc
        selected = next(
            (model for model in catalog.models if model.model_alias == model_alias),
            None,
        )
        if selected is None:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "GATEWAY_MODEL_SELECTION_STALE",
                    "message": "The selected model is no longer enabled. Refresh and choose another model.",
                },
            )
        if not selected.callable:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "GATEWAY_MODEL_NOT_AVAILABLE",
                    "message": "The selected model is visible but not callable for the current subscription.",
                    "availability": selected.availability,
                    "requiredPlanCode": selected.required_plan_code,
                    "upgradeHint": selected.upgrade_hint,
                },
            )
        patch["model"] = model_alias
        patch["provider"] = "gateway"
    if "system_prompt" in request:
        patch["system_prompt"] = str(request["system_prompt"])[:16_384]
    if "workspace_enabled" in request:
        patch["workspace_enabled"] = bool(request["workspace_enabled"])
    if "sandbox_network_mode" in request:
        mode = str(request["sandbox_network_mode"]).strip().lower()
        if mode in _SANDBOX_NETWORK_MODES:
            patch["sandbox_network_mode"] = mode
    if "sandbox_network_allowed_domains" in request:
        patch["sandbox_network_allowed_domains"] = (
            _sanitize_sandbox_network_allowed_domains(
                request["sandbox_network_allowed_domains"]
            )
        )
    if "sandbox_fs_allowed_write_paths" in request:
        patch["sandbox_fs_allowed_write_paths"] = (
            _sanitize_sandbox_fs_allowed_write_paths(
                request["sandbox_fs_allowed_write_paths"]
            )
        )
    if "im_full_access_enabled" in request:
        patch["im_full_access_enabled"] = bool(request["im_full_access_enabled"])
    if "theme" in request:
        theme = str(request["theme"])
        if theme in ("light", "dark", "system"):
            patch["theme"] = theme
    if "env_vars" in request:
        patch["env_vars"] = _sanitize_env_vars(request["env_vars"])

    if patch:
        database.save_system_config(user_id, patch)

    return {
        "success": True,
        "data": _public_system_config(database.get_system_config(user_id)),
    }
