# [Input] Consume backend/.env and ClaudeCodeOptions-like objects.
# [Output] Provide helpers that merge project env vars into ClaudeCodeOptions.env
#          and force Claude Code to read project settings only.
# [Pos] SDK environment helper node in libs/claude_agent_kit/server
# [Sync] 2026-05-08: centralize .env injection for ClaudeSDKClient subprocess options.
# [Sync] 2026-05-08: map TypeScript settingSources=["project"] to Python SDK extra_args.
# [Sync] 2026-05-24: load SDK subprocess env from backend/.env by default.
# [Sync] 2026-05-24: keep SDK env injection direct; no app runtime alias mapping.
# [Sync] 2026-05-24: add INK_AGENT_ALLOW_REQUEST_MODEL_OVERRIDE to allowlist (renamed from
#                    PAWKEYLAND_CLAUDE_AGENT_ALLOW_REQUEST_MODEL_OVERRIDE); legacy key kept
#                    for zero-downtime migration.

"""Runtime option helpers for Claude Code SDK subprocesses."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional

from dotenv import dotenv_values

_BACKEND_ROOT = Path(__file__).resolve().parents[3]
_PROJECT_ENV_FILE = _BACKEND_ROOT / ".env"
_CLAUDE_SETTING_SOURCES_ARG = "setting-sources"
_CLAUDE_PROJECT_SETTING_SOURCE = "project"
_PROJECT_DOTENV_SDK_ENV_NAMES = frozenset(
    {
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_MODEL",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL",
        "ANTHROPIC_DEFAULT_SONNET_MODEL",
        "ANTHROPIC_DEFAULT_OPUS_MODEL",
        "API_TIMEOUT_MS",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC",
        "DISABLE_INTERLEAVED_THINKING",
        # Request-level model override gate (renamed from Pawkeyland prefix)
        "INK_AGENT_ALLOW_REQUEST_MODEL_OVERRIDE",
        # Legacy key — accepted by agent_runner.py fallback; kept here so old
        # .env files continue to work without redeployment.
        "PAWKEYLAND_CLAUDE_AGENT_ALLOW_REQUEST_MODEL_OVERRIDE",
    }
)
_REMOVED_PROJECT_DOTENV_SDK_ENV_NAMES = frozenset({"ANTHROPIC_API_KEY"})


def _is_project_dotenv_sdk_env_key(key: str) -> bool:
    """Return whether a backend .env key should be passed to Claude Code."""

    return key in _PROJECT_DOTENV_SDK_ENV_NAMES


def project_dotenv_env(env_file: Optional[Path | str] = None) -> dict[str, str]:
    """Return backend ``.env`` values suitable for ``ClaudeCodeOptions.env``."""
    path = Path(env_file) if env_file is not None else _PROJECT_ENV_FILE
    if not path.exists():
        return {}

    values = dotenv_values(path)
    return {
        str(key): str(value)
        for key, value in values.items()
        if key and value is not None and _is_project_dotenv_sdk_env_key(str(key))
    }


def merge_project_dotenv_env(
    existing_env: Optional[Mapping[str, str]] = None,
    env_file: Optional[Path | str] = None,
) -> dict[str, str]:
    """Merge backend ``.env`` with caller-provided SDK env overrides."""
    merged = project_dotenv_env(env_file)
    if existing_env:
        merged.update(
            {
                str(key): str(value)
                for key, value in existing_env.items()
                if value is not None
            }
        )
    for key in _REMOVED_PROJECT_DOTENV_SDK_ENV_NAMES:
        merged.pop(key, None)
    return merged


def apply_project_dotenv_to_options(
    options: Any,
    env_file: Optional[Path | str] = None,
) -> Any:
    """Ensure a ClaudeCodeOptions-like object carries backend ``.env`` vars."""
    existing_env = getattr(options, "env", None) or {}
    options.env = merge_project_dotenv_env(existing_env, env_file)
    return options


def apply_project_setting_sources_to_options(options: Any) -> Any:
    """Force Claude Code to load settings from the project source only.

    The TypeScript SDK exposes this as ``settingSources: ["project"]``.
    The Python SDK version used by this repo has no typed field yet, but its
    ``extra_args`` map is passed through to the Claude CLI.  The equivalent CLI
    flag is ``--setting-sources project``.
    """
    existing_extra_args = getattr(options, "extra_args", None)
    if existing_extra_args is None:
        existing_extra_args = {}
    if isinstance(existing_extra_args, dict):
        options.extra_args = existing_extra_args
    else:
        options.extra_args = dict(existing_extra_args)
    options.extra_args[_CLAUDE_SETTING_SOURCES_ARG] = _CLAUDE_PROJECT_SETTING_SOURCE
    return options


def apply_project_sdk_runtime_options(
    options: Any,
    env_file: Optional[Path | str] = None,
) -> Any:
    """Apply all project-level Claude SDK runtime defaults."""
    apply_project_dotenv_to_options(options, env_file)
    apply_project_setting_sources_to_options(options)
    return options


def apply_user_sdk_env_to_options(
    options: Any,
    user_env: Optional[Mapping[str, str]] = None,
) -> Any:
    """Overlay user-stored SDK env vars onto options, filtered to the allowlist.

    Must be called *after* apply_project_sdk_runtime_options so that
    user values take precedence over backend/.env defaults.
    """
    if not user_env:
        return options
    existing_env = getattr(options, "env", None) or {}
    if not isinstance(existing_env, dict):
        existing_env = dict(existing_env)
    # Only forward keys on the SDK allowlist to the subprocess.
    filtered = {
        str(k): str(v)
        for k, v in user_env.items()
        if k and v is not None and _is_project_dotenv_sdk_env_key(str(k))
    }
    # Merge: filtered user env overlays existing (which already has backend/.env).
    merged = {**existing_env, **filtered}
    # Remove any deprecated keys.
    for key in _REMOVED_PROJECT_DOTENV_SDK_ENV_NAMES:
        merged.pop(key, None)
    options.env = merged
    return options
