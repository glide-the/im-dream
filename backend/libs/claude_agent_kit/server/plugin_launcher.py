"""Claude CLI launch boundary for workspace-packed plugins.

This module is the ONLY place where ``--plugin-dir`` reaches the Claude CLI.
It reads the server-controlled launch manifest
(``<workspace>/.ink/launch-manifest.json``) written by
``services.claude_plugin.workspace_packer``, re-verifies every packed
plugin directory against its pinned SHA-256 digest, and attaches the
corresponding plugin entries to the SDK options at the CLI process
launcher/adapter boundary.

How the flag is emitted: ``ClaudeAgentOptions.plugins`` entries of
``{"type": "local", "path": ...}`` are translated by the SDK's
``SubprocessCLITransport`` into literal repeated ``--plugin-dir <path>``
argv elements for the real ``claude`` executable
(``claude_agent_sdk/_internal/transport/subprocess_cli.py`` — verified with
claude-agent-sdk 0.2.128 / Claude Code 2.1.220).  Paths come exclusively
from the workspace manifest — never from ``AgentRunOptions``, never from a
client request, and clients can neither submit ``--plugin-dir`` nor control
the manifest.

Fail-closed: any manifest/integrity problem raises
:class:`PluginLaunchError` and the run aborts; plugins are never silently
skipped or silently loaded from another location.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from .plugin_digest import compute_plugin_digest, digest_is_valid

logger = logging.getLogger(__name__)

LAUNCH_MANIFEST_RELATIVE_PATH = Path(".ink") / "launch-manifest.json"
LAUNCH_MANIFEST_SCHEMA_VERSION = "claude-launch/v1"


class PluginLaunchError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def read_workspace_launch_manifest(cwd: str | Path | None) -> list[dict[str, Any]]:
    """Return verified plugin entries for the workspace at *cwd*.

    An empty list means "no manifest" (a workspace without packed plugins is
    legitimate).  Any *invalid* state raises — fail-closed.
    """
    if not cwd:
        return []
    workspace = Path(cwd).resolve()
    manifest_path = workspace / LAUNCH_MANIFEST_RELATIVE_PATH
    if not manifest_path.is_file():
        return []
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PluginLaunchError(
            "CLAUDE_PLUGIN_MANIFEST_INVALID",
            f"launch manifest is not valid JSON: {manifest_path}",
        ) from exc
    if not isinstance(payload, dict):
        raise PluginLaunchError(
            "CLAUDE_PLUGIN_MANIFEST_INVALID",
            "launch manifest must be a JSON object",
        )
    if payload.get("schema_version") != LAUNCH_MANIFEST_SCHEMA_VERSION:
        raise PluginLaunchError(
            "CLAUDE_PLUGIN_MANIFEST_INVALID",
            f"unsupported launch manifest schema: {payload.get('schema_version')!r}",
        )
    raw_plugins = payload.get("plugins")
    if not isinstance(raw_plugins, list):
        raise PluginLaunchError(
            "CLAUDE_PLUGIN_MANIFEST_INVALID",
            "launch manifest 'plugins' must be a list",
        )
    verified: list[dict[str, Any]] = []
    for entry in raw_plugins:
        verified.append(_verify_entry(workspace, entry))
    return verified


def _verify_entry(workspace: Path, entry: Any) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise PluginLaunchError(
            "CLAUDE_PLUGIN_MANIFEST_INVALID", "manifest entry must be an object"
        )
    package_spec = entry.get("package_spec")
    relative_path = entry.get("relative_path")
    digest = entry.get("artifact_digest")
    if not isinstance(package_spec, str) or "@" not in package_spec:
        raise PluginLaunchError(
            "CLAUDE_PLUGIN_MANIFEST_INVALID",
            f"manifest entry has an invalid package_spec: {package_spec!r}",
        )
    if not isinstance(relative_path, str) or not relative_path.startswith(".ink/plugins/"):
        raise PluginLaunchError(
            "CLAUDE_PLUGIN_MANIFEST_INVALID",
            f"manifest entry has an invalid relative_path: {relative_path!r}",
        )
    if not isinstance(digest, str) or not digest_is_valid(digest):
        raise PluginLaunchError(
            "CLAUDE_PLUGIN_MANIFEST_INVALID",
            f"manifest entry has an invalid artifact_digest: {digest!r}",
        )
    packed_dir = (workspace / relative_path).resolve()
    try:
        packed_dir.relative_to(workspace)
    except ValueError as exc:
        raise PluginLaunchError(
            "CLAUDE_PLUGIN_MANIFEST_INVALID",
            f"manifest entry path escapes the workspace: {relative_path!r}",
        ) from exc
    if not packed_dir.is_dir():
        raise PluginLaunchError(
            "CLAUDE_PLUGIN_PACK_MISSING",
            f"packed plugin directory is missing: {relative_path}",
        )
    actual = compute_plugin_digest(packed_dir)
    if actual != digest:
        raise PluginLaunchError(
            "CLAUDE_PLUGIN_INTEGRITY_FAILED",
            f"packed plugin digest mismatch for {package_spec}: "
            f"expected {digest}, found {actual}",
        )
    plugin_root = packed_dir / ".claude-plugin" / "plugin.json"
    return {
        "package_spec": package_spec,
        "resolved_version": entry.get("resolved_version"),
        "artifact_digest": digest,
        "relative_path": relative_path,
        "absolute_path": str(packed_dir),
        "has_manifest": plugin_root.is_file(),
    }


def read_workspace_runtime_venv_dirs(cwd: str | Path | None) -> list[str]:
    """Return validated managed-venv dirs declared by the workspace manifest.

    Empty list means "no manifest" or "manifest without a runtime section".
    A declared but missing venv dir raises — fail-closed, because hook
    subprocesses would otherwise silently fall back to a system python3
    without the plugin's dependencies (drama-forge-workspace-init-design §5).
    """
    if not cwd:
        return []
    workspace = Path(cwd).resolve()
    manifest_path = workspace / LAUNCH_MANIFEST_RELATIVE_PATH
    if not manifest_path.is_file():
        return []
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PluginLaunchError(
            "CLAUDE_PLUGIN_MANIFEST_INVALID",
            f"launch manifest is not valid JSON: {manifest_path}",
        ) from exc
    runtime = payload.get("runtime") if isinstance(payload, dict) else None
    if runtime is None:
        return []
    if not isinstance(runtime, dict) or not isinstance(runtime.get("venv_dirs"), list):
        raise PluginLaunchError(
            "CLAUDE_PLUGIN_MANIFEST_INVALID",
            "manifest 'runtime.venv_dirs' must be a list",
        )
    venv_dirs: list[str] = []
    for item in runtime["venv_dirs"]:
        if not isinstance(item, str) or not Path(item).is_absolute():
            raise PluginLaunchError(
                "CLAUDE_PLUGIN_MANIFEST_INVALID",
                f"runtime.venv_dirs entry must be an absolute path: {item!r}",
            )
        if not (Path(item) / "bin" / "python3").is_file():
            raise PluginLaunchError(
                "CLAUDE_PLUGIN_RUNTIME_MISSING",
                f"managed plugin venv is missing its interpreter: {item}",
            )
        venv_dirs.append(item)
    return venv_dirs


def apply_plugin_launch_options(sdk_options: Any, cwd: str | Path | None) -> list[dict[str, Any]]:
    """Attach verified workspace plugins to *sdk_options* (CLI argv boundary).

    Sets ``sdk_options.plugins`` to ``[{"type": "local", "path": ...}]`` so
    the SDK's subprocess transport emits literal ``--plugin-dir <path>`` argv
    for each entry.  Returns the verified entries (for receipts/logging).
    """
    entries = read_workspace_launch_manifest(cwd)
    if not entries:
        return []
    sdk_options.plugins = [
        {"type": "local", "path": entry["absolute_path"]} for entry in entries
    ]
    # Managed plugin runtimes (workspace-init design §5): prepend each
    # manifest-declared venv's bin/ to PATH so hook subprocesses (children of
    # the claude CLI) resolve python3 with the plugin's dependencies.
    venv_dirs = read_workspace_runtime_venv_dirs(cwd)
    if venv_dirs:
        existing_env = getattr(sdk_options, "env", None) or {}
        if not isinstance(existing_env, dict):
            existing_env = dict(existing_env)
        base_path = existing_env.get("PATH") or os.environ.get("PATH", "")
        sdk_options.env = {
            **existing_env,
            "PATH": os.pathsep.join(
                [*(str(Path(d) / "bin") for d in venv_dirs), base_path]
            ),
            "VIRTUAL_ENV": venv_dirs[0],
        }
    logger.info(
        "Claude CLI launch: --plugin-dir × %d from workspace manifest (%s)",
        len(entries),
        ", ".join(entry["package_spec"] for entry in entries),
    )
    return entries
