# [Input] Consume the project-root .env and ClaudeCodeOptions-like objects.
# [Output] Provide helpers that merge project env vars into ClaudeCodeOptions.env
#          and force Claude Code to read project settings only.
# [Pos] SDK environment helper node in libs/claude_agent_kit/server
# [Sync] 2026-05-08: centralize project .env injection for ClaudeSDKClient subprocess options.
# [Sync] 2026-05-08: map TypeScript settingSources=["project"] to Python SDK extra_args.
# [Sync] 2026-05-11: map PAWKEYLAND_AGENT_THINKING to Claude Code interleaved-thinking env.
# [Sync] 2026-05-11: map formal PAWKEYLAND_AGENT_* runtime provider config into Claude Code Anthropic-compatible env names and --model.
# [Sync] 2026-05-11: route DeepSeek Agent disabled-thinking traffic through Pawkeyland's explicit Anthropic thinking-toggle proxy.

"""Runtime option helpers for Claude Code SDK subprocesses."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional

from dotenv import dotenv_values

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_PROJECT_ENV_FILE = _PROJECT_ROOT / ".env"
_CLAUDE_SETTING_SOURCES_ARG = "setting-sources"
_CLAUDE_PROJECT_SETTING_SOURCE = "project"
_CLAUDE_DISABLE_INTERLEAVED_THINKING_ENV = "DISABLE_INTERLEAVED_THINKING"
_AGENT_UPSTREAM_BASE_URL_ENV = "PAWKEYLAND_AGENT_UPSTREAM_BASE_URL"
_CLAUDE_MODEL_ENV_NAMES = (
    "ANTHROPIC_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
)
_AGENT_THINKING_ENABLED_VALUES = {"1", "true", "yes", "on", "enable", "enabled", "thinking"}


def _agent_thinking_disabled(env: Mapping[str, str]) -> bool:
    """Return whether Pawkeyland's formal Agent thinking selector disables thinking."""

    try:
        from libs.volcresource.cfg import resolve_agent_runtime_config

        thinking = str(resolve_agent_runtime_config(env=env).get("thinking") or "").strip().lower()
        return thinking != "enabled"
    except Exception:  # noqa: BLE001
        raw = str(env.get("PAWKEYLAND_AGENT_THINKING") or "").strip().lower()
        return raw not in _AGENT_THINKING_ENABLED_VALUES


def project_dotenv_env(env_file: Optional[Path | str] = None) -> dict[str, str]:
    """Return project ``.env`` values suitable for ``ClaudeCodeOptions.env``."""
    path = Path(env_file) if env_file is not None else _PROJECT_ENV_FILE
    if not path.exists():
        return {}

    values = dotenv_values(path)
    return {
        str(key): str(value)
        for key, value in values.items()
        if key and value is not None
    }


def merge_project_dotenv_env(
    existing_env: Optional[Mapping[str, str]] = None,
    env_file: Optional[Path | str] = None,
) -> dict[str, str]:
    """Merge project ``.env`` with caller-provided SDK env overrides."""
    merged = project_dotenv_env(env_file)
    if existing_env:
        merged.update(
            {
                str(key): str(value)
                for key, value in existing_env.items()
                if value is not None
            }
        )
    return merged


def apply_project_dotenv_to_options(
    options: Any,
    env_file: Optional[Path | str] = None,
) -> Any:
    """Ensure a ClaudeCodeOptions-like object carries project ``.env`` vars."""
    existing_env = getattr(options, "env", None) or {}
    options.env = merge_project_dotenv_env(existing_env, env_file)
    return options


def apply_agent_runtime_env_to_options(options: Any) -> Any:
    """Map formal Pawkeyland Agent runtime config to Claude Code SDK env names."""

    env = getattr(options, "env", None) or {}
    if not isinstance(env, dict):
        env = dict(env)
        options.env = env

    from libs.volcresource.cfg import agent_transport_base_url, resolve_agent_runtime_config

    resolved = resolve_agent_runtime_config(env=env)
    base_url = str(resolved.get("base_url") or "").strip()
    transport_base_url = agent_transport_base_url(resolved)
    api_key = str(resolved.get("api_key") or "").strip()
    model = str(resolved.get("model") or "").strip()

    if transport_base_url:
        env["ANTHROPIC_BASE_URL"] = transport_base_url
    if transport_base_url and base_url and transport_base_url != base_url:
        env[_AGENT_UPSTREAM_BASE_URL_ENV] = base_url
    else:
        env.pop(_AGENT_UPSTREAM_BASE_URL_ENV, None)
    if api_key:
        env["ANTHROPIC_API_KEY"] = api_key
        env["ANTHROPIC_AUTH_TOKEN"] = api_key
    if model:
        for key in _CLAUDE_MODEL_ENV_NAMES:
            env[key] = model
        if not str(getattr(options, "model", "") or "").strip():
            options.model = model
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


def apply_agent_thinking_env_to_options(options: Any) -> Any:
    """Translate Pawkeyland Agent thinking config into Claude Code subprocess env."""

    env = getattr(options, "env", None) or {}
    if not isinstance(env, dict):
        env = dict(env)
        options.env = env

    if _agent_thinking_disabled(env):
        env[_CLAUDE_DISABLE_INTERLEAVED_THINKING_ENV] = "1"
    else:
        # Override stale shell/project aliases because PAWKEYLAND_AGENT_THINKING
        # is the formal source of truth for this app's Agent bridge.
        env[_CLAUDE_DISABLE_INTERLEAVED_THINKING_ENV] = ""
    return options


def apply_project_sdk_runtime_options(
    options: Any,
    env_file: Optional[Path | str] = None,
) -> Any:
    """Apply all Pawkeyland project-level Claude SDK runtime defaults."""
    apply_project_dotenv_to_options(options, env_file)
    apply_agent_runtime_env_to_options(options)
    apply_agent_thinking_env_to_options(options)
    apply_project_setting_sources_to_options(options)
    return options
