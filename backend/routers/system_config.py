#!/usr/bin/env python3
# [Input] Consume database system-config APIs and shared auth dependency.
# [Output] Register GET/PUT /api/system-config endpoints.
# [Pos] system-config route node in backend/routers
# [Sync] 2026-05-27: initial implementation — system config (model, theme, env_vars, etc.).

"""System configuration API.

Endpoints
---------
GET  /api/system-config  — retrieve the caller's system config
PUT  /api/system-config  — merge a partial update into the caller's system config

The system config is a freeform dict stored per user.  Known fields:

  provider         : str  — LLM provider ("anthropic" | "openai")
  model            : str  — model name
  system_prompt    : str  — custom system prompt for the AI agent
  workspace_enabled: bool — whether the workspace file sidebar is active
  theme            : str  — UI theme ("light" | "dark" | "system")
  env_vars         : dict — user-supplied env vars forwarded to skills/MCP servers
                            as key→value string pairs
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

import database
from .deps import get_current_user

router = APIRouter()

# Keys that must be string→string when present in env_vars to prevent injection
_ENV_VAR_KEY_MAX_LEN = 256
_ENV_VAR_VALUE_MAX_LEN = 4096
_ENV_VARS_MAX_ENTRIES = 64


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
        if k:
            result[k] = v
        if len(result) >= _ENV_VARS_MAX_ENTRIES:
            break
    return result


@router.get("/api/system-config")
def get_system_config(current_user: dict = Depends(get_current_user)):
    """Return the caller's system configuration."""
    user_id = current_user["user_id"]
    return database.get_system_config(user_id)


@router.put("/api/system-config")
def put_system_config(
    request: dict,
    current_user: dict = Depends(get_current_user),
):
    """Merge *request* into the caller's system configuration.

    Accepted keys: ``provider``, ``model``, ``system_prompt``,
    ``workspace_enabled``, ``theme``, ``env_vars``.
    Unknown keys are stored but not used by the server.
    """
    user_id = current_user["user_id"]

    patch: dict = {}

    if "provider" in request:
        patch["provider"] = str(request["provider"])[:64]
    if "model" in request:
        patch["model"] = str(request["model"])[:256]
    if "system_prompt" in request:
        patch["system_prompt"] = str(request["system_prompt"])[:16_384]
    if "workspace_enabled" in request:
        patch["workspace_enabled"] = bool(request["workspace_enabled"])
    if "theme" in request:
        theme = str(request["theme"])
        if theme in ("light", "dark", "system"):
            patch["theme"] = theme
    if "env_vars" in request:
        patch["env_vars"] = _sanitize_env_vars(request["env_vars"])

    if patch:
        database.save_system_config(user_id, patch)

    return {"success": True}
