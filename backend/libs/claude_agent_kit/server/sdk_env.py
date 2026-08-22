# [Input] Consume backend/.env, process env, and ClaudeAgentOptions-like objects.
# [Output] Provide helpers that merge project/runtime env vars into ClaudeAgentOptions.env
#          and force Claude Code to read project settings only.
# [Pos] SDK environment helper node in libs/claude_agent_kit/server
# [Sync] 2026-05-08: centralize .env injection for ClaudeSDKClient subprocess options.
# [Sync] 2026-05-08: map TypeScript settingSources=["project"] to Python SDK extra_args.
# [Sync] 2026-05-24: load SDK subprocess env from backend/.env by default.
# [Sync] 2026-05-24: keep SDK env injection direct; no app runtime alias mapping.
# [Sync] 2026-05-24: add INK_AGENT_ALLOW_REQUEST_MODEL_OVERRIDE to allowlist (renamed from
#                    PAWKEYLAND_CLAUDE_AGENT_ALLOW_REQUEST_MODEL_OVERRIDE); legacy key kept
#                    for zero-downtime migration.
# [Sync] 2026-06-12: merge Cloud Run/process SDK env after backend/.env so Secret
#                    Manager-injected ANTHROPIC_AUTH_TOKEN reaches the subprocess.
# [Sync] 2026-07-20: add apply_plan_mode_env_to_options() — inject per-thread
#                    CLAUDE_CONFIG_DIR={cwd}/.claude-home at the lowest env
#                    priority so Plan Mode files land in the thread workspace
#                    (claude-plan §5.1); key stays out of the dotenv allowlist.
# [Sync] 2026-07-20: add apply_task_v2_env_to_options() — gated by
#                    INK_AGENT_TASK_V2_ENABLED (default off), injects
#                    CLAUDE_CODE_ENABLE_TASKS=1 / CLAUDE_CODE_TASK_LIST_ID=main
#                    at the lowest env priority so v2 task files land in
#                    {workspace}/.claude-home/tasks/main/ (claude-todo §5.1).
# [Sync] 2026-07-26: SDK migration claude-code-sdk → claude-agent-sdk 0.2.128 —
#                    docstring/type-name updates only (ClaudeAgentOptions);
#                    extra_args["setting-sources"]="project" passthrough is
#                    still correct because the new transport only emits its own
#                    --setting-sources flag when options.setting_sources is set
#                    (we never set it).
# [Sync] 2026-07-26: HOTFIX task-list divergence — the 0.2.128 bundled CLI
#                    enables task tools by default (CLAUDE_CODE_ENABLE_TASKS
#                    !== "0") and falls back to sessionId/teamName taskListId
#                    when CLAUDE_CODE_TASK_LIST_ID is unset, so runs with the
#                    legacy INK_AGENT_TASK_V2_ENABLED gate off wrote tasks to
#                    per-session dirs that get_tasks_dir("main") never found
#                    (empty 计划与待办 panel despite working task tools).
#                    apply_task_v2_env_to_options now ALWAYS pins
#                    CLAUDE_CODE_TASK_LIST_ID=main (lowest priority); the gate
#                    only forces an explicit CLAUDE_CODE_ENABLE_TASKS=1.
# [Sync] 2026-07-26: add apply_cli_path_to_options() — pin options.cli_path to
#                    the system/npm CLI (CLAUDE_CODE_CLI_PATH override →
#                    shutil.which("claude") → leave unset for SDK bundled
#                    fallback) so Docker's apply-seccomp-patched npm CLI is not
#                    shadowed by the SDK bundled CLI; explicit cli_path wins.
# [Sync] 2026-08-03: scope correction — CLAUDE_CONFIG_DIR={cwd}/.claude-home
#                    relocates the CLI's ENTIRE config home (plans/, tasks/,
#                    projects/ transcripts, plugins/, agents/, caches), not
#                    just Plan Mode.  Add resolve_claude_config_home() as the
#                    single path-resolution source and
#                    apply_claude_config_home_to_options() applied FIRST in the
#                    env chain (renamed from apply_plan_mode_env_to_options,
#                    kept as a wrapper; constant renamed
#                    _PLAN_MODE_CONFIG_HOME_DIRNAME → _CLAUDE_CONFIG_HOME_DIRNAME
#                    with alias).
# [Sync] 2026-08-12: set Claude Code's native transient-request retry default
#                    to three through CLAUDE_CODE_MAX_RETRIES. This is a
#                    server-owned CLI default, not an Agent turn retry loop.
# [Sync] 2026-08-14: pin Claude Code's native temp root through a canonicalized
#                    CLAUDE_CODE_TMPDIR (configured default /tmp/claude) so its
#                    per-uid cwd-* files stay under the exact allowWrite root.
# [Sync] 2026-08-22: relocate CLAUDE_CODE_TMPDIR into each canonical thread
#                    workspace at .claude-tmp; reject missing/relative/root cwd
#                    and prepare the 0700 directory at the CLI spawn boundary.
# [Sync] 2026-08-22: restore strict system-CLI discovery for MCP management and
#                    the server-owned secure-storage selector without changing
#                    the thread-scoped TMPDIR contract.

"""Runtime option helpers for Claude Code SDK subprocesses."""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any, Mapping, Optional

from dotenv import dotenv_values

_BACKEND_ROOT = Path(__file__).resolve().parents[3]
_PROJECT_ENV_FILE = _BACKEND_ROOT / ".env"
_CLAUDE_SETTING_SOURCES_ARG = "setting-sources"
_CLAUDE_PROJECT_SETTING_SOURCE = "project"
_CLAUDE_CODE_MAX_RETRIES_ENV_NAME = "CLAUDE_CODE_MAX_RETRIES"
CLAUDE_CODE_MAX_RETRIES_DEFAULT = "3"
_CLAUDE_CODE_TMPDIR_ENV_NAME = "CLAUDE_CODE_TMPDIR"
CLAUDE_CODE_TMPDIR_DIRNAME = ".claude-tmp"
_CLAUDE_TMP_WORKSPACE_OPTION_ATTR = "_ink_claude_tmp_workspace"
CLAUDE_AGENT_MAX_BUFFER_SIZE_ENV_NAME = "INK_CLAUDE_AGENT_MAX_BUFFER_SIZE_BYTES"
CLAUDE_AGENT_MAX_BUFFER_SIZE_DEFAULT = 8 * 1024 * 1024
CLAUDE_AGENT_MAX_BUFFER_SIZE_MINIMUM = 1024 * 1024
CLAUDE_AGENT_MAX_BUFFER_SIZE_MAXIMUM = 64 * 1024 * 1024

logger = logging.getLogger(__name__)
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
_GATEWAY_COMPETING_CREDENTIAL_ENV_NAMES = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN",
)
_USER_SDK_ENV_NAMES = frozenset(
    {
        "API_TIMEOUT_MS",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC",
        "DISABLE_INTERLEAVED_THINKING",
    }
)

# Plan Mode / config-home injection (claude-plan §5.1).  CLAUDE_CONFIG_DIR is
# deliberately NOT in ``_PROJECT_DOTENV_SDK_ENV_NAMES`` so backend/.env cannot
# relocate the global Claude config home.
#
# 2026-08-03 scope correction: ``.claude-home`` is NOT Plan-Mode-only.  Once
# ``CLAUDE_CONFIG_DIR={cwd}/.claude-home`` is injected, the CLI moves its
# entire config home into the per-thread workspace — plans/, tasks/,
# projects/ (session transcripts), plugins/, agents/, skills/settings caches
# and every other built-in feature stop reading the user's real ``~/.claude``.
# Backend code that resolves config-home-relative paths must go through
# :func:`resolve_claude_config_home` (single source of truth), never ``~``.
_CLAUDE_CONFIG_DIR_ENV_NAME = "CLAUDE_CONFIG_DIR"
_CLAUDE_CONFIG_HOME_DIRNAME = ".claude-home"
CLAUDE_SECURE_STORAGE_CONFIG_DIR_ENV_NAME = (
    "CLAUDE_SECURESTORAGE_CONFIG_DIR"
)
# Backward-compatible alias (2026-08-03 rename — the redirect covers far more
# than Plan Mode); prefer _CLAUDE_CONFIG_HOME_DIRNAME in new code.
_PLAN_MODE_CONFIG_HOME_DIRNAME = _CLAUDE_CONFIG_HOME_DIRNAME

# Task v2 (file tasks) injection (claude-todo §5.1).  Both keys stay out of
# ``_PROJECT_DOTENV_SDK_ENV_NAMES`` so neither backend/.env nor user_sdk_env
# can flip the v1/v2 tool family or relocate the task list.
_TASK_V2_ENABLED_ENV_NAME = "INK_AGENT_TASK_V2_ENABLED"
_CLAUDE_CODE_ENABLE_TASKS_ENV_NAME = "CLAUDE_CODE_ENABLE_TASKS"
_CLAUDE_CODE_TASK_LIST_ID_ENV_NAME = "CLAUDE_CODE_TASK_LIST_ID"
# Fixed taskListId (claude-todo §5.1): without it the CLI falls back to its
# own sessionId, scattering one thread's tasks across per-session subdirs.
# workspace.get_tasks_dir() resolves the same constant — single source.
CLAUDE_CODE_TASK_LIST_ID_VALUE = "main"
_TRUE_ENV_VALUES = frozenset({"1", "true", "yes", "on"})


def resolve_claude_agent_max_buffer_size(
    process_env: Optional[Mapping[str, str]] = None,
) -> int:
    """Return the bounded SDK stdout limit for one CLI NDJSON message."""

    source = os.environ if process_env is None else process_env
    raw = str(source.get(CLAUDE_AGENT_MAX_BUFFER_SIZE_ENV_NAME) or "").strip()
    if not raw:
        return CLAUDE_AGENT_MAX_BUFFER_SIZE_DEFAULT
    try:
        value = int(raw)
    except ValueError:
        value = 0
    if not (
        CLAUDE_AGENT_MAX_BUFFER_SIZE_MINIMUM
        <= value
        <= CLAUDE_AGENT_MAX_BUFFER_SIZE_MAXIMUM
    ):
        logger.warning(
            "%s=%r must be between %d and %d bytes; using %d.",
            CLAUDE_AGENT_MAX_BUFFER_SIZE_ENV_NAME,
            raw,
            CLAUDE_AGENT_MAX_BUFFER_SIZE_MINIMUM,
            CLAUDE_AGENT_MAX_BUFFER_SIZE_MAXIMUM,
            CLAUDE_AGENT_MAX_BUFFER_SIZE_DEFAULT,
        )
        return CLAUDE_AGENT_MAX_BUFFER_SIZE_DEFAULT
    return value


def resolve_claude_code_tmpdir(
    workspace: Optional[Path | str],
) -> str:
    """Return the canonical per-thread Claude Code temporary root.

    Claude Code derives its per-uid ``claude-UID/cwd-*`` shell files
    beneath ``CLAUDE_CODE_TMPDIR``.  The root is always the hidden
    ``.claude-tmp`` directory inside the canonical thread workspace so a
    container restart cannot remove a global parent directory and sibling
    threads never share CLI settings or shell scratch files.

    Browser/user/process env settings cannot relocate this security boundary.
    """

    raw_value = str(workspace or "").strip()
    raw = Path(raw_value)
    if not raw_value or not raw.is_absolute():
        raise ValueError("Claude Code requires an absolute thread workspace")
    try:
        workspace_abs = raw.resolve(strict=False)
    except (OSError, RuntimeError):
        raise ValueError("Claude Code thread workspace cannot be resolved") from None
    if workspace_abs == Path("/"):
        raise ValueError("Claude Code thread workspace cannot be the filesystem root")
    return str(workspace_abs / CLAUDE_CODE_TMPDIR_DIRNAME)


def ensure_claude_code_tmpdir(workspace: Optional[Path | str]) -> str:
    """Create and validate the canonical per-thread CLI temp directory."""

    candidate = Path(resolve_claude_code_tmpdir(workspace))
    workspace_abs = candidate.parent.resolve(strict=True)
    if not workspace_abs.is_dir():
        raise ValueError("Claude Code thread workspace must be a directory")
    if candidate.is_symlink():
        raise ValueError("Claude Code thread temp directory cannot be a symlink")
    candidate.mkdir(mode=0o700, parents=False, exist_ok=True)
    resolved = candidate.resolve(strict=True)
    if not resolved.is_dir() or resolved.parent != workspace_abs:
        raise ValueError("Claude Code thread temp directory escaped its workspace")
    resolved.chmod(0o700)
    return str(resolved)


def apply_gateway_credential_tombstones(environment: dict[str, str]) -> None:
    """Override credentials inherited by the SDK subprocess when Gateway is on.

    ``claude-agent-sdk`` overlays ``options.env`` onto the full parent process
    environment. Removing a key from ``options.env`` therefore cannot remove a
    credential already present in uvicorn's ``os.environ``. Empty values are
    the subprocess transport's only deletion-equivalent and make Claude Code
    select the server-owned ``apiKeyHelper`` instead.
    """

    for name in _GATEWAY_COMPETING_CREDENTIAL_ENV_NAMES:
        environment[name] = ""


def task_v2_enabled() -> bool:
    """Return whether the legacy v2 opt-in gate is set (claude-todo §5.1).

    Historical note: enabling v2 used to make the CLI expose
    ``TaskCreate``/``TaskUpdate``/``TaskList``/``TaskGet`` and disable v1
    ``TodoWrite`` (official mutual exclusion), so it was an explicit opt-in
    via ``INK_AGENT_TASK_V2_ENABLED``.  The claude-agent-sdk 0.2.128 bundled
    CLI enables task tools **by default** (``CLAUDE_CODE_ENABLE_TASKS !==
    "0"``), so the gate no longer controls tool availability — it only
    forces an explicit ``CLAUDE_CODE_ENABLE_TASKS=1`` injection.  The fixed
    taskListId pinning no longer depends on this gate (see
    :func:`apply_task_v2_env_to_options`).
    """

    raw = os.getenv(_TASK_V2_ENABLED_ENV_NAME, "").strip().lower()
    return raw in _TRUE_ENV_VALUES


def _is_project_dotenv_sdk_env_key(key: str) -> bool:
    """Return whether a backend .env key should be passed to Claude Code."""

    return key in _PROJECT_DOTENV_SDK_ENV_NAMES


def project_dotenv_env(env_file: Optional[Path | str] = None) -> dict[str, str]:
    """Return backend ``.env`` values suitable for ``ClaudeAgentOptions.env``."""
    path = Path(env_file) if env_file is not None else _PROJECT_ENV_FILE
    if not path.exists():
        return {}

    values = dotenv_values(path)
    return {
        str(key): str(value)
        for key, value in values.items()
        if key and value is not None and _is_project_dotenv_sdk_env_key(str(key))
    }


def process_sdk_env(process_env: Optional[Mapping[str, str]] = None) -> dict[str, str]:
    """Return process env values suitable for ``ClaudeAgentOptions.env``.

    Cloud Run injects Secret Manager values as regular environment variables,
    not as a ``backend/.env`` file.  These values still need to be copied into
    ``ClaudeAgentOptions.env`` because setting that field makes the SDK
    subprocess use the explicit map instead of inheriting the whole parent env.
    """

    source = os.environ if process_env is None else process_env
    return {
        str(key): str(value)
        for key, value in source.items()
        if key and value is not None and _is_project_dotenv_sdk_env_key(str(key))
    }


def merge_project_dotenv_env(
    existing_env: Optional[Mapping[str, str]] = None,
    env_file: Optional[Path | str] = None,
    process_env: Optional[Mapping[str, str]] = None,
) -> dict[str, str]:
    """Merge backend ``.env``, process env, and caller-provided SDK env overrides."""
    merged = project_dotenv_env(env_file)
    merged.update(process_sdk_env(process_env))
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
    # ``ClaudeAgentRunner`` applies the server-owned Gateway configuration
    # after the first project/runtime merge. ``SimpleClaudeAgentSDKClient``
    # deliberately reapplies these defaults for direct callers immediately
    # before spawning Claude Code. That second merge must not resurrect a
    # direct Provider bearer token from backend/.env or the parent process:
    # Claude Code gives ANTHROPIC_AUTH_TOKEN precedence over apiKeyHelper, so
    # the canonical Gateway subject JWT would otherwise be replaced and the
    # request would correctly fail authentication at the Admin boundary. Keep
    # empty tombstones instead of popping: the Python SDK inherits the entire
    # parent environment before overlaying this map.
    primary_gateway_flag = str(merged.get("INK_GATEWAY_ENABLED", "")).strip()
    legacy_gateway_flag = str(
        merged.get("INK_GATEWAY_CLAUDE_AGENT_ENABLED", "")
    ).strip()
    gateway_enabled = (
        primary_gateway_flag or legacy_gateway_flag
    ).lower() in _TRUE_ENV_VALUES
    if gateway_enabled:
        apply_gateway_credential_tombstones(merged)
    return merged


def apply_project_dotenv_to_options(
    options: Any,
    env_file: Optional[Path | str] = None,
) -> Any:
    """Ensure a ClaudeAgentOptions-like object carries project/runtime SDK vars."""
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
    *,
    thread_workspace: Optional[Path | str] = None,
) -> Any:
    """Apply all project-level Claude SDK runtime defaults.

    ``thread_workspace`` is a server-owned launch binding, distinct from the
    SDK ``cwd``.  The runner records it on the options object so the final
    client adapter can safely reapply project defaults without losing the
    binding.  Browser, dotenv, process, and user SDK env values cannot set or
    relocate it.
    """
    apply_project_dotenv_to_options(options, env_file)
    existing_env = getattr(options, "env", None) or {}
    if not isinstance(existing_env, dict):
        existing_env = dict(existing_env)
    existing_env.setdefault(
        _CLAUDE_CODE_MAX_RETRIES_ENV_NAME,
        CLAUDE_CODE_MAX_RETRIES_DEFAULT,
    )
    # Server-owned and intentionally assigned rather than setdefault: the
    # workspace sandbox is generated from the same resolver, so an arbitrary
    # caller/process value cannot move Claude's files outside this thread.
    if thread_workspace is not None:
        canonical_tmpdir = Path(resolve_claude_code_tmpdir(thread_workspace))
        setattr(
            options,
            _CLAUDE_TMP_WORKSPACE_OPTION_ATTR,
            str(canonical_tmpdir.parent),
        )
    authoritative_workspace = getattr(
        options,
        _CLAUDE_TMP_WORKSPACE_OPTION_ATTR,
        None,
    ) or getattr(options, "cwd", None)
    if authoritative_workspace:
        existing_env[_CLAUDE_CODE_TMPDIR_ENV_NAME] = resolve_claude_code_tmpdir(
            authoritative_workspace
        )
    else:
        # Helper-only callers may merge project env before a run has a cwd.
        # Never retain a caller/process relocation; the spawn boundary below
        # requires a canonical thread workspace before launching the CLI.
        existing_env.pop(_CLAUDE_CODE_TMPDIR_ENV_NAME, None)
    options.env = existing_env
    apply_project_setting_sources_to_options(options)
    return options


def get_options_claude_tmp_workspace(options: Any) -> Optional[str]:
    """Return the server-bound workspace used for Claude CLI temp storage."""

    value = getattr(options, _CLAUDE_TMP_WORKSPACE_OPTION_ATTR, None) or getattr(
        options,
        "cwd",
        None,
    )
    return str(value) if value else None


def resolve_claude_config_home(
    cwd: Optional[str | Path] = None,
) -> Optional[str]:
    """Resolve the effective Claude config home for a thread.

    Single source of truth for every backend module that needs
    config-home-relative paths (plans, tasks, session transcripts, plugins,
    agents, skills caches).  Resolution order mirrors the SDK env chain:

      1. ``CLAUDE_CONFIG_DIR`` process env (explicit override) — wins.
      2. *cwd* provided (Workspace Mode) → ``{cwd}/.claude-home``, matching
         the value injected into the SDK subprocess.
      3. ``None`` — caller falls back to the official default ``~/.claude``.

    Resolved in the service layer right after workspace/cwd resolution —
    BEFORE any claude module (resume probe, plugin pack, plan/tasks readers,
    agent run) touches the filesystem — and carried into the runner via
    ``AgentRunOptions.claude_config_home`` so the decision is not buried in
    the ``run_streaming`` lifecycle.
    """
    config_dir = os.environ.get(_CLAUDE_CONFIG_DIR_ENV_NAME)
    if config_dir:
        return config_dir
    if cwd:
        return str(Path(str(cwd)) / _CLAUDE_CONFIG_HOME_DIRNAME)
    return None


def apply_claude_config_home_to_options(
    options: Any,
    config_home: Optional[str | Path] = None,
    cwd: Optional[str | Path] = None,
) -> Any:
    """Point the Claude Code config home at the per-thread workspace.

    Sets ``CLAUDE_CONFIG_DIR=<config_home>`` (resolved via
    :func:`resolve_claude_config_home` when only *cwd* is given) so ALL CLI
    built-ins land under ``{workspace}/.claude-home/`` — plans/
    (claude-plan §5.1), tasks/, projects/ session transcripts, plugins,
    agents and caches — instead of the user's real ``~/.claude``.

    Priority: FIRST in the SDK env chain — call *before*
    ``apply_project_sdk_runtime_options`` so the value is treated as
    explicit ``options.env`` and no later merge (backend/.env, process env,
    ``user_sdk_env``) can relocate it.  An explicitly provided
    ``CLAUDE_CONFIG_DIR`` already present in ``options.env`` is preserved.
    No-op when neither *config_home* nor *cwd* resolves (Workspace Mode
    disabled).
    """
    home = str(config_home) if config_home else resolve_claude_config_home(cwd)
    if not home:
        return options
    existing_env = getattr(options, "env", None) or {}
    if not isinstance(existing_env, dict):
        existing_env = dict(existing_env)
    if existing_env.get(_CLAUDE_CONFIG_DIR_ENV_NAME):
        options.env = existing_env
        return options
    options.env = {
        **existing_env,
        _CLAUDE_CONFIG_DIR_ENV_NAME: home,
    }
    return options


def apply_claude_secure_storage_home_to_options(
    options: Any,
    secure_storage_home: Optional[str | Path] = None,
) -> Any:
    """Bind Claude Code secure storage to the authenticated platform user.

    The selector is server-owned and separate from the thread-local
    ``CLAUDE_CONFIG_DIR``. It is primarily used by macOS Keychain; Linux keeps
    it unset and consumes the file projection created by ``claude_mcp``.
    """

    if secure_storage_home is None:
        return options
    raw = Path(str(secure_storage_home)).expanduser()
    if not raw.is_absolute():
        raise ValueError("Claude secure-storage home must be absolute.")
    try:
        resolved = raw.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise ValueError("Claude secure-storage home is invalid.") from exc
    if resolved == Path("/"):
        raise ValueError("Claude secure-storage home is invalid.")
    existing_env = getattr(options, "env", None) or {}
    if not isinstance(existing_env, dict):
        existing_env = dict(existing_env)
    options.env = {
        **existing_env,
        CLAUDE_SECURE_STORAGE_CONFIG_DIR_ENV_NAME: str(resolved),
    }
    return options


def apply_plan_mode_env_to_options(
    options: Any,
    cwd: Optional[str | Path] = None,
) -> Any:
    """Backward-compatible wrapper (2026-08-03 rename).

    The redirect covers far more than Plan Mode; prefer
    :func:`apply_claude_config_home_to_options` in new code.
    """
    return apply_claude_config_home_to_options(options, cwd=cwd)


def apply_task_v2_env_to_options(options: Any) -> Any:
    """Pin the v2 file-task list location for every run (claude-todo §5.1).

    Always injects ``CLAUDE_CODE_TASK_LIST_ID=main`` (lowest priority) so v2
    task JSON lands under ``{CLAUDE_CONFIG_DIR}/tasks/main/`` — i.e.
    ``{workspace}/.claude-home/tasks/main/`` once
    ``apply_claude_config_home_to_options`` has redirected the config home.
    Fixing taskListId prevents the CLI's sessionId/teamName fallback from
    scattering one thread's tasks across per-session subdirectories that
    ``workspace.get_tasks_dir()`` never finds.

    Why unconditional: the claude-agent-sdk 0.2.128 bundled CLI enables task
    tools **by default** (``CLAUDE_CODE_ENABLE_TASKS !== "0"``), so without
    this injection a run with the legacy ``INK_AGENT_TASK_V2_ENABLED`` gate
    off would still execute TaskCreate/TaskUpdate but write them to a
    per-session list dir — the panel then shows nothing (2026-07-26
    production bug).  ``CLAUDE_CODE_ENABLE_TASKS=1`` is additionally injected
    when the legacy gate is truthy (belt-and-braces with the CLI default;
    preserves an explicit opt-out path via the CLI's own
    ``CLAUDE_CODE_ENABLE_TASKS=0``).

    Priority: lowest in the SDK env chain — call *after*
    ``apply_claude_config_home_to_options`` and *before*
    ``apply_user_sdk_env_to_options``.  Explicit values already present in
    ``options.env`` are preserved.
    """

    existing_env = getattr(options, "env", None) or {}
    if not isinstance(existing_env, dict):
        existing_env = dict(existing_env)
    merged = dict(existing_env)
    merged.setdefault(
        _CLAUDE_CODE_TASK_LIST_ID_ENV_NAME, CLAUDE_CODE_TASK_LIST_ID_VALUE
    )
    if task_v2_enabled():
        merged.setdefault(_CLAUDE_CODE_ENABLE_TASKS_ENV_NAME, "1")
    options.env = merged
    return options


# CLI binary resolution (2026-07-26, Docker apply-seccomp fix).  The
# claude-agent-sdk transport prefers its bundled CLI over any system install
# (``_find_cli``: bundled first).  Production Docker patches the npm CLI's
# vendor apply-seccomp into a passthrough to survive nested userns, so the
# patched binary must win over the bundled one.
_CLAUDE_CODE_CLI_PATH_ENV_NAME = "CLAUDE_CODE_CLI_PATH"


def resolve_claude_cli_path(
    process_env: Optional[Mapping[str, str]] = None,
) -> Optional[str]:
    """Resolve an executable system CLI for Agent and MCP management calls."""

    source = os.environ if process_env is None else process_env
    override = str(source.get(_CLAUDE_CODE_CLI_PATH_ENV_NAME) or "").strip()
    if override:
        candidate = Path(override).expanduser()
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate.resolve())
        logger.warning(
            "%s is set but is not executable; falling back to PATH.",
            _CLAUDE_CODE_CLI_PATH_ENV_NAME,
        )
    search_path = source.get("PATH") if process_env is not None else None
    system_cli = shutil.which("claude", path=search_path)
    if not system_cli:
        return None
    candidate = Path(system_cli)
    if not candidate.is_file() or not os.access(candidate, os.X_OK):
        return None
    return str(candidate.resolve())


def apply_cli_path_to_options(options: Any) -> Any:
    """Pin ``options.cli_path`` to the system/npm CLI when available.

    Resolution order (first hit wins):

    1. ``CLAUDE_CODE_CLI_PATH`` env var, when set and the path exists.
       A set-but-missing path logs a warning and falls through — a stale
       override must never shadow a working CLI.
    2. ``shutil.which("claude")`` — the system/npm install.  Production
       Docker ships the npm CLI with the vendor apply-seccomp passthrough
       patch (nested-userns ``/proc/self/setgroups`` workaround); pinning it
       prevents the SDK's bundled CLI from silently shadowing the patched
       binary (2026-07-26 recurrence).  Local dev likewise stays on the
       developer's own npm claude.
    3. Leave ``cli_path`` unset — documented escape hatch: the SDK then
       falls back to its bundled CLI (usable when no system claude exists).

    An explicitly pre-set ``options.cli_path`` always wins over this helper.
    """

    if getattr(options, "cli_path", None):
        return options
    system_cli = resolve_claude_cli_path()
    if system_cli:
        options.cli_path = system_cli
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
        if k and v is not None and str(k) in _USER_SDK_ENV_NAMES
    }
    # Merge: filtered user env overlays existing (which already has backend/.env).
    merged = {**existing_env, **filtered}
    # Remove any deprecated keys.
    for key in _REMOVED_PROJECT_DOTENV_SDK_ENV_NAMES:
        merged.pop(key, None)
    options.env = merged
    return options
