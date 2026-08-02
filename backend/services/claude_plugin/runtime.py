"""Server-managed Claude plugin runtime root and its directory layout.

The runtime root is fully isolated from the developer's real ``~/.claude``:

- ``config/``            — injected as ``CLAUDE_CONFIG_DIR`` for every managed
                           CLI invocation; holds the CLI's own settings.json,
                           plugins/installed_plugins.json registry,
                           plugins/known_marketplaces.json and plugins/cache.
- ``install-workspace/`` — the ``cwd`` for ``claude plugin install``.
- ``artifacts/``         — immutable plugin directories named
                           ``<package>@<marketplace>@sha256-<digest>``.
- ``operations/``        — per-operation evidence (argv, cwd, env policy,
                           exit code, sanitized stdout/stderr, file snapshots).

The layout mirrors what the real CLI (verified with Claude Code 2.1.220)
writes, never an invented structure.
"""

from __future__ import annotations

import os
from pathlib import Path

_ENV_ROOT = "INK_CLAUDE_PLUGIN_RUNTIME_ROOT"

_DEFAULT_ROOT = (
    Path(__file__).resolve().parents[2] / "data" / "claude-plugin-runtime"
)


def get_runtime_root() -> Path:
    """Return the managed plugin runtime root, creating it on first use.

    Resolution order:
    1. ``INK_CLAUDE_PLUGIN_RUNTIME_ROOT`` (absolute path only).
    2. ``<backend>/data/claude-plugin-runtime``.
    """
    raw = os.environ.get(_ENV_ROOT, "").strip()
    if raw:
        candidate = Path(raw).expanduser()
        if candidate.is_absolute():
            root = candidate
        else:  # pragma: no cover - defensive; logged and ignored
            root = _DEFAULT_ROOT
    else:
        root = _DEFAULT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    for child in ("config", "install-workspace", "artifacts", "operations"):
        (root / child).mkdir(parents=True, exist_ok=True)
    return root


def get_config_dir() -> Path:
    """Isolated ``CLAUDE_CONFIG_DIR`` for all managed CLI invocations."""
    return get_runtime_root() / "config"


def get_install_workspace() -> Path:
    """The ``cwd`` used for ``claude plugin install`` executions."""
    return get_runtime_root() / "install-workspace"


def get_artifacts_root() -> Path:
    """Root of the immutable artifact store."""
    return get_runtime_root() / "artifacts"


def get_operations_root() -> Path:
    """Root where per-operation evidence is persisted."""
    return get_runtime_root() / "operations"


def get_cli_registry_path() -> Path:
    """The CLI's own install registry inside the managed config dir."""
    return get_config_dir() / "plugins" / "installed_plugins.json"


def get_cli_cache_root() -> Path:
    """The CLI's plugin cache root inside the managed config dir."""
    return get_config_dir() / "plugins" / "cache"


def managed_cli_env(base: dict[str, str] | None = None) -> dict[str, str]:
    """Environment for managed CLI subprocesses.

    Starts from a minimal pass-through of the current environment (PATH and
    auth-related keys must survive so the real CLI can run) and pins
    ``CLAUDE_CONFIG_DIR`` at the isolated config dir.  ``HOME`` is preserved:
    the CLI locates credentials through it, while every piece of plugin state
    is redirected by ``CLAUDE_CONFIG_DIR`` (verified behavior of Claude Code
    2.1.220: settings, registry, marketplace clones and plugin cache all land
    under ``CLAUDE_CONFIG_DIR``).
    """
    env = dict(base if base is not None else os.environ)
    env["CLAUDE_CONFIG_DIR"] = str(get_config_dir())
    return env
