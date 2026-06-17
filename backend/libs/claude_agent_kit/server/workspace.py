# [Input] None — reads AGENT_CWD env var and project root for template assets.
# [Output] Provide get_workspace_root, init_workspace, get_or_create_workspace,
#          extract_archive_in_skills, list_workspace_files, list_workspace_file_tree,
#          read_workspace_file_content, write_workspace_file, delete_workspace_file,
#          move_workspace_file to application and API layers.
# [Pos] workspace manager node in libs/claude_agent_kit/server
# [Sync] 2026-05-06: initial implementation — WSK-01 workspace init + WSK-04 archive extraction
# [Sync] 2026-05-08: refresh project .claude template files on every init while preserving runtime skills.
# [Sync] 2026-05-08: call sync_skills_symlinks() at the end of init_workspace so skills are linked on first init.
# [Sync] 2026-05-09: seed workspace/skills/ from project .claude/skills/ on init so bundled skills are available.
# [Sync] 2026-05-28: add _init_editor_index() — create .editor/ virtual index placeholder directory.
# [Sync] 2026-06-06: memory/ remains outside init_workspace and is initialised
#                    only by the workspace file interface endpoint using the
#                    partition (voice) config.
# [Sync] 2026-06-13: sync per-thread Claude Code sandbox settings into
#                    {workspace}/.claude/settings.json so Bash is OS-confined
#                    to the current thread workspace when workspace mode is on.
# [Sync] 2026-06-14: add read-only runtime dependency allowlist so sandboxed
#                    Bash can execute Python/Node/system tools without exposing
#                    project source directories outside the thread workspace.
# [Sync] 2026-06-14: auto-enable Claude Code Docker nested Bash sandbox mode
#                    when the backend runs inside a Linux container.
# [Sync] 2026-06-16: keep .claude/skills fully writable by narrowing sandbox
#                    denyWrite to config/runtime internals instead of .claude/.
# [Sync] 2026-06-16: workspace_file_sync imports direct .claude/skills writes
#                    into workspace/skills before rebuilding discovery symlinks.
# [Sync] 2026-06-17: include standard Linux sbin directories in sandbox runtime
#                    read allowlist so bubblewrap can build its rootfs in Docker.

"""Workspace manager for Claude Agent session directories.

Each conversation gets an isolated working directory under the workspace root:

    {workspace_root}/{session_id}/
        files/          – user-uploaded or agent-produced files
        logs/           – agent execution logs
        skills/         – installable skill packages / files
        .editor/        – EditorState virtual index (placeholder files; see workspace-adapter.md)
        .claude/        – Claude project config (synced from repo template)
        .claude/skills/ – symlinks → ../skills/*; direct writes are imported back
                           into skills/ (managed by workspace_file_sync)

The ``memory/`` procedural memory subdirectory is **not** created by
``init_workspace``.  It is initialised explicitly through the workspace
file-interface endpoint (``POST /api/workspace/memory-init``), which reads the
per-voice partition config from the ``voices`` DB table.

Archive extraction (WSK-04)
---------------------------
When a file with a recognised archive extension is uploaded to ``skills/``,
``extract_archive_in_skills`` validates every entry for path-traversal / link
attacks before atomically moving the extracted directory into place.  On any
failure the original ``skills/`` content is preserved unchanged.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import sys
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Literal, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WORKSPACE_SUBDIRS: tuple[str, ...] = ("files", "logs", "skills")
ARCHIVE_EXTENSIONS: frozenset[str] = frozenset(
    {".zip", ".skill", ".tar.gz", ".tgz", ".tar"}
)
SANDBOX_EXTRA_ALLOW_READ_ENV = "INK_AGENT_SANDBOX_EXTRA_ALLOW_READ"
SANDBOX_PRESERVE_ALIAS_READ_PATHS: frozenset[str] = frozenset(
    {"/bin", "/sbin", "/lib", "/lib64"}
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_PROJECT_ROOT: Path = Path(__file__).resolve().parents[4]


def _project_root() -> Path:
    """Return the repository root used for workspace template assets."""
    return _PROJECT_ROOT


def _append_existing_sandbox_read_path(
    paths: list[Path],
    raw_path: str | os.PathLike[str],
    *,
    preserve_alias: bool = False,
) -> None:
    """Append *raw_path* when it exists and is not already present."""

    if not raw_path:
        return
    try:
        raw = Path(raw_path).expanduser()
        if preserve_alias:
            alias = raw if raw.is_absolute() else raw.resolve(strict=False)
            if alias.exists() and alias not in paths:
                paths.append(alias)
        path = raw.resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        return
    if not path.exists() or path in paths:
        return
    paths.append(path)


def _running_in_linux_container() -> bool:
    """Return True when this backend process appears to run inside a container."""

    if not sys.platform.startswith("linux"):
        return False
    for marker in ("/.dockerenv", "/run/.containerenv"):
        try:
            if Path(marker).exists():
                return True
        except OSError:
            pass
    try:
        cgroup = Path("/proc/1/cgroup").read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return any(token in cgroup for token in ("docker", "containerd", "kubepods"))


def _runtime_root_for_executable(raw_path: Optional[str]) -> Optional[Path]:
    """Return the narrow read root needed to execute *raw_path* inside sandbox."""

    if not raw_path:
        return None
    try:
        executable = Path(raw_path).expanduser().resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        return None
    if not executable.exists():
        return None

    parent = executable.parent
    if parent.name == "bin":
        grandparent = parent.parent
        # Version-managed runtimes keep libraries beside bin/.
        if any(part in {".pyenv", ".nvm", ".bun", ".asdf", "node", "versions"} for part in grandparent.parts):
            return grandparent
        # Homebrew and language installs usually need lib/ or Cellar/ beside bin/.
        if str(grandparent).startswith(("/opt/homebrew", "/usr/local", "/home/linuxbrew")):
            return grandparent

    return parent


def _sandbox_runtime_read_allow_paths() -> list[str]:
    """Return read-only runtime dependency paths for Bash sandbox execution.

    The thread workspace remains the only product data root. These paths are
    deliberately limited to interpreters, system libraries, package-manager
    runtime roots, and temp directories needed to start common developer tools.
    Additional deployment-specific runtime paths can be supplied through
    ``INK_AGENT_SANDBOX_EXTRA_ALLOW_READ`` using ``os.pathsep`` separators.
    """

    paths: list[Path] = []
    home = Path.home()

    for raw_path in (
        tempfile.gettempdir(),
        os.getenv("TMPDIR", ""),
        "/tmp",
        "/private/tmp",
        home / ".pyenv",
        home / ".nvm" / "versions" / "node",
        home / ".bun",
        home / ".local" / "bin",
        home / "miniconda3",
        "/opt/miniconda3",
        "/opt/conda",
        "/opt/homebrew/bin",
        "/opt/homebrew/opt",
        "/opt/homebrew/lib",
        "/opt/homebrew/Cellar",
        "/home/linuxbrew/.linuxbrew/bin",
        "/home/linuxbrew/.linuxbrew/opt",
        "/home/linuxbrew/.linuxbrew/lib",
        "/home/linuxbrew/.linuxbrew/Cellar",
        "/bin",
        "/usr/bin",
        "/sbin",
        "/usr/sbin",
        "/usr/local/bin",
        "/usr/local/sbin",
        "/usr/lib",
        "/usr/lib64",
        "/lib",
        "/lib64",
        "/usr/lib/x86_64-linux-gnu",
        "/etc/ssl",
        "/System/Library/OpenSSL",
        "/System/Library/Frameworks",
        "/Library/Apple",
        "/usr/local/go",
        "/usr/lib/go",
        "/usr/share/go",
        "/usr/lib/jvm",
        "/opt/homebrew/opt/openjdk@17",
    ):
        preserve_alias = (
            isinstance(raw_path, str)
            and raw_path in SANDBOX_PRESERVE_ALIAS_READ_PATHS
        )
        _append_existing_sandbox_read_path(
            paths,
            raw_path,
            preserve_alias=preserve_alias,
        )

    for executable in (
        sys.executable,
        *(shutil.which(name) for name in (
            "python3",
            "python",
            "node",
            "npm",
            "npx",
            "bash",
            "sh",
            "rg",
            "grep",
            "git",
            "go",
            "java",
            "make",
            "gcc",
            "g++",
        )),
    ):
        runtime_root = _runtime_root_for_executable(executable)
        if runtime_root is not None:
            _append_existing_sandbox_read_path(paths, runtime_root)

    for raw_path in os.getenv(SANDBOX_EXTRA_ALLOW_READ_ENV, "").split(os.pathsep):
        _append_existing_sandbox_read_path(paths, raw_path.strip())

    return [str(path) for path in paths]


# ---------------------------------------------------------------------------
# Public API — workspace root resolution
# ---------------------------------------------------------------------------


def get_workspace_root() -> Path:
    """Return the base directory that holds all session workspaces.

    Resolution order:
    1. ``AGENT_CWD`` environment variable (must be an absolute path).
    2. ``{tempdir}/claude-agent-workspaces`` (stable cross-platform default).
    """
    env_val = os.environ.get("AGENT_CWD", "").strip()
    if env_val:
        root = Path(env_val)
        if root.is_absolute():
            return root
        logger.warning(
            "AGENT_CWD=%r is not absolute; falling back to temp directory.", env_val
        )
    return Path(tempfile.gettempdir()) / "ink-agent-workspaces"


# ---------------------------------------------------------------------------
# Public API — workspace lifecycle
# ---------------------------------------------------------------------------


def _workspace_sandbox_config(workspace: Path, enabled: bool) -> dict:
    """Return Claude Code sandbox settings for a single thread workspace.

    ``AGENT_CWD`` points to the parent workspace root.  The actual isolation
    target for a conversation is the resolved ``workspace`` path
    (``{AGENT_CWD}/{thread_id}``).
    """

    workspace_abs = workspace.resolve(strict=False)
    
    enabled = bool(enabled)

    # allow_read = [str(workspace_abs), *_sandbox_runtime_read_allow_paths()]
    allow_read = [str(workspace_abs)]

    sandbox_config = {
        "enabled": enabled,
        "failIfUnavailable": enabled,
        "autoAllowBashIfSandboxed": enabled,
        "allowUnsandboxedCommands": not enabled,
        "filesystem": {
            # sandbox-runtime read policy is deny-then-allow.  The product
            # goal is stricter than Claude Code's default (which can read most
            # of the host): deny the filesystem root and re-allow only this
            # thread cwd.  This prevents sibling workspaces and unrelated host
            # paths from being readable by Bash subprocesses.
            "denyRead": ["/app", str(workspace_abs.parent)],
            "allowRead": allow_read,
            # Write policy is allow-only for the thread workspace.  Keep
            # .claude/skills writable so skill symlinks and runtime-installed
            # skills can be fully managed, but deny config/hook internals that
            # should not be mutated by Bash.
            "allowWrite": [str(workspace_abs)],
            "denyWrite": [
                str(workspace_abs / ".claude" / "settings.json"),
                str(workspace_abs / ".claude" / "settings.local.json"),
                str(workspace_abs / ".claude" / "hooks"),
                str(workspace_abs / ".claude" / ".clawhub"),
                str(workspace_abs / ".claude" / "worktrees"),
                str(workspace_abs / ".editor"),
                str(workspace_abs / ".mcp.json"),
            ],
        },
    }
    # if enabled and _running_in_linux_container():
    #     # Claude Code's Linux sandbox uses bubblewrap.  Inside Docker, a fresh
    #     # /proc mount may be unavailable, so Claude Code supports this weaker
    #     # nested mode when the outer container is the primary isolation layer.
    #     sandbox_config["enableWeakerNestedSandbox"] = True
    return sandbox_config


def sync_workspace_sandbox_settings(workspace: Path, *, enabled: bool = True) -> None:
    """Merge per-thread sandbox settings into ``{workspace}/.claude/settings.json``.

    Existing non-sandbox settings copied from the project template are preserved.
    The ``sandbox`` block is owned by workspace initialisation because it is
    derived from the resolved per-thread workspace path.
    """

    try:
        workspace_root_abs = get_workspace_root().resolve(strict=False)
        workspace_abs = workspace.resolve(strict=False)
        if not workspace_abs.is_relative_to(workspace_root_abs):
            logger.warning(
                "sync_workspace_sandbox_settings: workspace %r is outside "
                "workspace root %r; aborting.",
                workspace_abs,
                workspace_root_abs,
            )
            return
    except Exception:  # noqa: BLE001
        logger.warning(
            "sync_workspace_sandbox_settings: could not resolve workspace path; aborting.",
            exc_info=True,
        )
        return

    claude_dir = workspace_abs / ".claude"
    settings_path = claude_dir / "settings.json"
    claude_dir.mkdir(parents=True, exist_ok=True)

    settings: dict = {}
    if settings_path.is_file():
        try:
            parsed = json.loads(settings_path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                settings = parsed
        except Exception:  # noqa: BLE001
            logger.warning(
                "Could not parse %s; rewriting with template-compatible sandbox settings.",
                settings_path,
                exc_info=True,
            )

    settings["sandbox"] = _workspace_sandbox_config(workspace_abs, enabled)
    try:
        settings_path.write_text(
            json.dumps(settings, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except Exception:  # noqa: BLE001
        logger.warning(
            "Failed to write sandbox settings to %s",
            settings_path,
            exc_info=True,
        )


def init_workspace(session_id: str, *, sandbox_enabled: bool = True) -> Path:
    """Create (or repair) the workspace skeleton for *session_id*.

    This function is **idempotent**:
    - First call: creates all directories and copies template assets.
    - Subsequent calls: repairs missing subdirectories and refreshes project
      ``.claude`` template files while preserving runtime-managed skills.

    Returns the fully-qualified workspace path.
    """
    workspace = get_workspace_root() / session_id
    workspace.mkdir(parents=True, exist_ok=True)

    # Ensure standard subdirectories exist (idempotent).
    for subdir in WORKSPACE_SUBDIRS:
        (workspace / subdir).mkdir(exist_ok=True)

    # Copy template assets from project root (only on first init).
    _copy_template_assets(workspace)

    # Keep per-thread Bash sandbox settings current. The sandbox block depends
    # on this workspace's resolved path, so it cannot live in the project
    # template unchanged.
    sync_workspace_sandbox_settings(workspace, enabled=sandbox_enabled)

    # Ensure .claude/skills/ exists so symlink sync has a target directory.
    (workspace / ".claude" / "skills").mkdir(parents=True, exist_ok=True)

    # Sync skills symlinks on every init (create on first call, refresh on subsequent calls).
    from .workspace_file_sync import sync_skills_symlinks  # local import avoids circular
    sync_skills_symlinks(workspace)

    # Initialise the .editor/ virtual index placeholder directory.
    _init_editor_index(workspace)

    logger.debug("Workspace initialised: %s", workspace)
    return workspace


def get_or_create_workspace(session_id: str, *, sandbox_enabled: bool = True) -> Path:
    """Return the workspace path for *session_id*, creating it if needed.

    This is the primary entry point for the service layer.  It calls
    ``init_workspace`` on every access so that any accidentally-deleted
    subdirectories are transparently restored.

    Raises ``ValueError`` when *session_id* contains path-traversal characters
    (``/``, ``\\``, ``..``) to prevent workspace root escape.
    """
    if not session_id or "/" in session_id or "\\" in session_id or ".." in session_id:
        raise ValueError(f"Invalid session_id: {session_id!r}")
    return init_workspace(session_id, sandbox_enabled=sandbox_enabled)


# ---------------------------------------------------------------------------
# Internal — template asset copying
# ---------------------------------------------------------------------------


def _sync_claude_project_template(src_claude: Path, dst_claude: Path) -> None:
    """Sync project ``.claude`` template files into a workspace.

    Runtime-managed ``.claude/skills`` is intentionally excluded because it is
    maintained by ``workspace_file_sync`` as symlinks to ``workspace/skills``;
    any direct real files/directories there are imported back into
    ``workspace/skills`` before symlink rebuild.
    Other existing workspace-local files are preserved unless they conflict
    with a project template file or directory.
    """
    if not src_claude.is_dir():
        dst_claude.mkdir(parents=True, exist_ok=True)
        return

    dst_claude.mkdir(parents=True, exist_ok=True)

    for src_child in sorted(src_claude.iterdir()):
        if src_child.name == "skills":
            continue

        dst_child = dst_claude / src_child.name
        try:
            if src_child.is_dir():
                if dst_child.exists() and not dst_child.is_dir():
                    dst_child.unlink()
                shutil.copytree(
                    str(src_child),
                    str(dst_child),
                    dirs_exist_ok=True,
                )
                continue

            if src_child.is_file():
                if dst_child.exists() and dst_child.is_dir():
                    logger.warning(
                        "Cannot sync .claude template file %s over directory %s.",
                        src_child,
                        dst_child,
                    )
                    continue
                shutil.copy2(str(src_child), str(dst_child))
        except Exception:  # noqa: BLE001
            logger.warning(
                "Failed to sync .claude template path %s to %s; skipping.",
                src_child,
                dst_child,
                exc_info=True,
            )


def _seed_workspace_skills(project_root: Path, workspace: Path) -> None:
    """Seed ``{workspace}/skills/`` from ``{project_root}/.claude/skills/``.

    Called once per init so that project-bundled skills are available to the
    agent from the first run.  Existing entries in ``workspace/skills/`` are
    never overwritten — this preserves user/agent-installed skills across
    subsequent ``init_workspace`` calls.
    """
    src_skills = project_root / ".claude" / "skills"
    dst_skills = workspace / "skills"

    if not src_skills.is_dir():
        return

    dst_skills.mkdir(parents=True, exist_ok=True)

    for src_entry in src_skills.iterdir():
        if src_entry.name.startswith("."):
            continue
        dst_entry = dst_skills / src_entry.name
        if dst_entry.exists():
            continue  # preserve existing workspace skill
        try:
            if src_entry.is_dir():
                shutil.copytree(str(src_entry), str(dst_entry))
            else:
                shutil.copy2(str(src_entry), str(dst_entry))
            logger.debug("Seeded skill %s → %s", src_entry.name, dst_entry)
        except Exception:  # noqa: BLE001
            logger.warning(
                "Failed to seed skill %s to %s; skipping.",
                src_entry,
                dst_entry,
                exc_info=True,
            )


_EDITOR_INDEX_README = """\
# .editor/ — EditorState 虚拟索引目录

此目录下的 JSON 文件是**占位符**，磁盘内容始终为空 `{}`。

当 Agent 调用 `read_file(".editor/<resource>.json")` 时，Python SDK 的 PreToolUse
钩子会将读取路径重定向到一个临时文件，该临时文件在运行时由当前 `editor_state` 动态填充。

等价的 MCP 工具读取方式：
  - `list_segments` / `read_segment`   → cells.json 等效
  - `list_comments` / `read_comment`   → commentors.json 等效
  - `read_session_meta`                → session.json 等效

⚠️ 禁止向此目录写入文件。写入操作被 Claude Code settings.json `permissions.deny` 拒绝，
   即使绕过限制写入也不会影响 EditorState（占位符不是真实数据源）。
"""

# Placeholder content for every .editor/<resource>.json file.
_EDITOR_PLACEHOLDER = "{}\n"

# Ordered list of virtual resource filenames (stems used in EDITOR_RESOURCES).
_EDITOR_PLACEHOLDER_STEMS: tuple[str, ...] = (
    "cells",
    "commentors",
    "tasks",
    "session",
    "full_state",
)


def _init_editor_index(workspace: Path) -> None:
    """Create (or repair) the ``.editor/`` virtual index directory.

    - Creates ``.editor/`` (idempotent — ``exist_ok=True``).
    - Writes (or refreshes) ``.editor/README.md`` so the Agent always sees
      current instructions.
    - Writes placeholder ``{}\n`` for each resource JSON on **first init
      only** — existing placeholder files are preserved so accidental early
      writes are not silently restored.

    This function is called by :func:`init_workspace` after the standard
    ``files/``, ``logs/``, ``skills/`` subdirectories are created.
    """
    # Resolve the workspace to an absolute path and construct the .editor/
    # subdirectory.  Verify the resolved path stays inside the workspace root
    # to guard against unexpected traversal in the input.  If resolution
    # fails (e.g. workspace does not exist yet on this call), fall back to
    # the unresolved path — `mkdir(exist_ok=True)` will create both.
    try:
        workspace_root_abs = get_workspace_root().resolve()
        workspace_abs = workspace.resolve()
        # Confirm the workspace itself is inside the configured root.
        if not workspace_abs.is_relative_to(workspace_root_abs):
            logger.warning(
                "_init_editor_index: workspace %r is outside workspace root %r; aborting.",
                workspace_abs,
                workspace_root_abs,
            )
            return
        # .editor/ is a fixed subdirectory name — no further user input involved.
        editor_dir_abs = workspace_abs / ".editor"
    except Exception:  # noqa: BLE001
        logger.warning(
            "_init_editor_index: could not resolve workspace path; aborting to avoid writing to unverified path.",
            exc_info=True,
        )
        return
    editor_dir = editor_dir_abs
    editor_dir.mkdir(exist_ok=True)

    # Always refresh README so instructions stay in sync with the template.
    try:
        (editor_dir / "README.md").write_text(_EDITOR_INDEX_README, encoding="utf-8")
    except Exception:  # noqa: BLE001
        logger.warning("Failed to write .editor/README.md; skipping.", exc_info=True)

    # Write placeholder JSON files (skip if already present).
    for stem in _EDITOR_PLACEHOLDER_STEMS:
        placeholder = editor_dir / f"{stem}.json"
        if placeholder.exists():
            continue
        try:
            placeholder.write_text(_EDITOR_PLACEHOLDER, encoding="utf-8")
            logger.debug("Created .editor/%s.json placeholder", stem)
        except Exception:  # noqa: BLE001
            logger.warning(
                "Failed to create .editor/%s.json placeholder; skipping.",
                stem,
                exc_info=True,
            )


def _copy_template_assets(workspace: Path) -> None:
    """Copy/sync project-root template assets into *workspace*.

    Assets copied:
    - ``.claude/`` template paths (excluding runtime-managed ``skills/``)
    - Project ``.claude/skills/`` entries seeded into ``workspace/skills/``
      (first-init only; existing entries are preserved)
    - ``.mcp.json`` (skipped silently when absent from project root)

    ``.claude`` template files are refreshed on every call so existing
    workspaces follow project settings. ``.mcp.json`` remains first-init only.
    """
    project_root = _project_root()

    # Sync .claude/ template (if present in project root).
    src_claude = project_root / ".claude"
    dst_claude = workspace / ".claude"
    _sync_claude_project_template(src_claude, dst_claude)

    # Seed workspace/skills/ from project .claude/skills/ (skip existing entries).
    _seed_workspace_skills(project_root, workspace)

    # Copy .mcp.json (optional — silently skipped when absent).
    src_mcp = project_root / ".mcp.json"
    dst_mcp = workspace / ".mcp.json"
    if src_mcp.is_file() and not dst_mcp.exists():
        try:
            shutil.copy2(str(src_mcp), str(dst_mcp))
            logger.debug("Copied .mcp.json to %s", dst_mcp)
        except Exception:  # noqa: BLE001
            logger.warning(
                "Failed to copy .mcp.json to %s; skipping.", dst_mcp, exc_info=True
            )


# ---------------------------------------------------------------------------
# Public API — path security helper (used by API layer)
# ---------------------------------------------------------------------------


def resolve_safe_path(workspace: Path, rel_path: str) -> Path:
    """Resolve *rel_path* relative to *workspace* and verify it stays inside.

    Raises ``ValueError`` for any path that would escape the workspace root,
    including ``../`` traversal, absolute paths, and symlink-based escapes.
    """
    if not rel_path or rel_path.strip() in ("", "."):
        return workspace

    # Reject absolute paths immediately (before any Path resolution).
    if os.path.isabs(rel_path):
        raise ValueError(f"Absolute path not allowed: {rel_path!r}")

    candidate = (workspace / rel_path).resolve()
    try:
        candidate.relative_to(workspace.resolve())
    except ValueError:
        raise ValueError(
            f"Path traversal detected: {rel_path!r} escapes workspace."
        ) from None

    return candidate


# ---------------------------------------------------------------------------
# Public API — archive extraction (WSK-04)
# ---------------------------------------------------------------------------

ExtractionStatus = Literal["extracted", "failed", "unsupported"]


def is_archive(filename: str) -> bool:
    """Return True when *filename* matches a supported archive extension."""
    name = filename.lower()
    for ext in ARCHIVE_EXTENSIONS:
        if name.endswith(ext):
            return True
    return False


def extract_archive_in_skills(
    workspace_path: Path,
    archive_rel_path: str,
) -> tuple[ExtractionStatus, Optional[str]]:
    """Extract an archive from ``skills/`` into a sibling skill directory.

    Safety guarantees:
    - Every archive entry is validated against path-traversal, absolute paths,
      and (for TAR) symbolic-link and hard-link entries.
    - Extraction is first performed into a temporary directory inside
      ``skills/``; only on full success is the directory atomically renamed to
      its final location.
    - On any validation or extraction failure the original ``skills/`` content
      is left untouched.
    - The archive file is deleted on success.

    Returns a ``(status, message)`` tuple where *status* is one of:
    - ``"extracted"``: extraction completed; symlink sync should follow.
    - ``"failed"``:    validation or extraction error; *message* has detail.
    - ``"unsupported"``: archive format not recognised.
    """
    from .workspace_file_sync import sync_skills_symlinks  # local import avoids circular

    skills_dir = workspace_path / "skills"
    archive_path = skills_dir / archive_rel_path

    if not archive_path.is_file():
        return "failed", f"Archive not found: {archive_rel_path}"

    archive_name = archive_path.name
    if not is_archive(archive_name):
        return "unsupported", f"Unsupported archive format: {archive_name}"

    # Determine the target directory name (strip archive extension(s)).
    target_name = _strip_archive_extension(archive_name)
    if not target_name:
        return "failed", f"Cannot derive target name from: {archive_name}"

    final_dir = skills_dir / target_name

    # Extract to a temporary directory first (atomic rollback guarantee).
    tmp_dir: Optional[Path] = None
    try:
        tmp_dir = Path(
            tempfile.mkdtemp(prefix=".extract_tmp_", dir=skills_dir)
        )

        if archive_name.endswith(".zip") or archive_name.endswith(".skill"):
            _extract_zip_safe(archive_path, tmp_dir)
        elif (
            archive_name.endswith(".tar.gz")
            or archive_name.endswith(".tgz")
            or archive_name.endswith(".tar")
        ):
            _extract_tar_safe(archive_path, tmp_dir)
        else:
            return "unsupported", f"Unsupported archive format: {archive_name}"

        # Atomic move: remove existing target if present, then rename.
        if final_dir.exists() or final_dir.is_symlink():
            if final_dir.is_dir() and not final_dir.is_symlink():
                shutil.rmtree(final_dir)
            else:
                final_dir.unlink()
        tmp_dir.rename(final_dir)
        tmp_dir = None  # renamed — do not clean up in finally

        # Remove the archive file on success.
        archive_path.unlink(missing_ok=True)

        # Re-sync symlinks after extraction.
        sync_skills_symlinks(workspace_path)

        logger.info(
            "Archive extracted: %s → %s", archive_rel_path, final_dir.name
        )
        return "extracted", None

    except _ArchiveSecurityError as exc:
        logger.warning(
            "Archive security validation failed (%s): %s", archive_rel_path, exc
        )
        return "failed", f"Security validation failed: {exc}"
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Archive extraction error (%s): %s", archive_rel_path, exc
        )
        return "failed", f"Extraction error: {exc}"
    finally:
        if tmp_dir is not None and tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Internal — archive helpers
# ---------------------------------------------------------------------------


class _ArchiveSecurityError(ValueError):
    """Raised when an archive entry fails security validation."""


def _strip_archive_extension(name: str) -> str:
    """Return *name* with its archive extension(s) removed."""
    lower = name.lower()
    for ext in (".tar.gz", ".tgz", ".tar", ".skill", ".zip"):
        if lower.endswith(ext):
            return name[: len(name) - len(ext)]
    return name


def _validate_zip_entry(member_name: str, extract_root: Path) -> None:
    """Raise ``_ArchiveSecurityError`` if *member_name* is unsafe."""
    if os.path.isabs(member_name):
        raise _ArchiveSecurityError(f"Absolute path in archive: {member_name!r}")
    if ".." in Path(member_name).parts:
        raise _ArchiveSecurityError(f"Path traversal in archive: {member_name!r}")
    # Verify resolved target stays inside extract root.
    candidate = (extract_root / member_name).resolve()
    try:
        candidate.relative_to(extract_root.resolve())
    except ValueError:
        raise _ArchiveSecurityError(
            f"Archive entry escapes extraction directory: {member_name!r}"
        ) from None


def _extract_zip_safe(archive_path: Path, extract_root: Path) -> None:
    """Extract a ZIP archive with path-traversal validation."""
    with zipfile.ZipFile(archive_path, "r") as zf:
        for info in zf.infolist():
            _validate_zip_entry(info.filename, extract_root)
        zf.extractall(extract_root)


def _validate_tar_entry(member: tarfile.TarInfo, extract_root: Path) -> None:
    """Raise ``_ArchiveSecurityError`` if *member* is unsafe (TAR-specific)."""
    name = member.name

    if member.issym() or member.islnk():
        raise _ArchiveSecurityError(
            f"Symlink/hardlink entry rejected: {name!r}"
        )
    if os.path.isabs(name):
        raise _ArchiveSecurityError(f"Absolute path in archive: {name!r}")
    if ".." in Path(name).parts:
        raise _ArchiveSecurityError(f"Path traversal in archive: {name!r}")
    candidate = (extract_root / name).resolve()
    try:
        candidate.relative_to(extract_root.resolve())
    except ValueError:
        raise _ArchiveSecurityError(
            f"Archive entry escapes extraction directory: {name!r}"
        ) from None


def _extract_tar_safe(archive_path: Path, extract_root: Path) -> None:
    """Extract a TAR archive with path-traversal and link validation."""
    with tarfile.open(archive_path, "r:*") as tf:
        members = tf.getmembers()
        for member in members:
            _validate_tar_entry(member, extract_root)
        # Use a filter that only extracts regular files and directories.
        # Pass filter="data" when available (Python ≥ 3.12) to suppress
        # deprecation warnings; fall back to extractall without filter.
        try:
            tf.extractall(extract_root, members=members, filter="data")
        except TypeError:
            tf.extractall(extract_root, members=members)

# ---------------------------------------------------------------------------
# Public API — file management (ported from claude-agent-next-kit workspace.ts)
# ---------------------------------------------------------------------------

# Error codes mirroring the TypeScript WorkspaceFileAccessErrorCode union type.
WorkspaceFileAccessErrorCode = Literal["PATH_TRAVERSAL", "NOT_FOUND", "IS_DIRECTORY"]


class WorkspaceFileAccessError(Exception):
    """Raised when a workspace file access operation fails.

    Attributes:
        code: Machine-readable error category.
        status: Suggested HTTP status code.
    """

    def __init__(
        self,
        code: WorkspaceFileAccessErrorCode,
        message: str,
        status: int,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


@dataclass
class WorkspaceFileInfo:
    """Metadata for a single entry inside a workspace directory."""

    name: str
    path: str
    is_directory: bool
    size: int
    modified_at: str  # ISO 8601


@dataclass
class WorkspaceFileTreeNode:
    """Recursive tree node — extends WorkspaceFileInfo with optional children."""

    name: str
    path: str
    is_directory: bool
    size: int
    modified_at: str  # ISO 8601
    children: Optional[List["WorkspaceFileTreeNode"]] = field(default=None)


@dataclass
class WorkspaceFileContent:
    """File content together with its metadata."""

    content: bytes
    file_name: str
    size: int
    modified_at: str  # ISO 8601


def _normalize_sub_path(sub_path: str) -> str:
    """Strip leading/trailing slashes and normalise backslashes."""
    return sub_path.replace("\\", "/").strip("/")


def _resolve_workspace_safe_path(
    workspace_path: Path,
    rel_path: str,
) -> Path:
    """Resolve *rel_path* inside *workspace_path* with path-traversal protection.

    Returns a path reconstructed from the workspace root and the validated
    relative portion (with symlinks resolved), so the return value contains
    no user-controlled string components.

    Raises :class:`WorkspaceFileAccessError` (code ``"PATH_TRAVERSAL"``) when the
    resolved path would escape the workspace root.
    """
    workspace_root = workspace_path.resolve()
    resolved = (workspace_path / rel_path).resolve()
    try:
        relative_part = resolved.relative_to(workspace_root)
    except ValueError:
        raise WorkspaceFileAccessError(
            "PATH_TRAVERSAL",
            "Path traversal not allowed",
            400,
        ) from None
    # Build the return path from trusted components only (no user string).
    return workspace_root / relative_part


def _mtime_iso(stat: os.stat_result) -> str:
    """Convert a ``stat_result`` mtime to an ISO 8601 UTC string."""
    return datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()


def _is_skills_path(file_path: str) -> bool:
    """Return True when *file_path* (relative) is inside the ``skills/`` directory."""
    normalized = file_path.replace("\\", "/")
    return normalized == "skills" or normalized.startswith("skills/")


def list_workspace_files(
    workspace_path: Path,
    sub_path: str = "",
) -> List[WorkspaceFileInfo]:
    """List the immediate children of a workspace directory.

    Returns entries sorted with directories first, then by name.
    Dot-prefixed entries are excluded.  Returns an empty list when *sub_path*
    does not exist inside *workspace_path*.
    """
    normalized_sub = _normalize_sub_path(sub_path)
    if normalized_sub:
        target_dir = _resolve_workspace_safe_path(workspace_path, normalized_sub)
    else:
        target_dir = workspace_path

    if not target_dir.exists():
        return []

    try:
        entries = list(target_dir.iterdir())
    except OSError:
        return []

    result: List[WorkspaceFileInfo] = []
    for entry in entries:
        if entry.name.startswith("."):
            continue
        try:
            stat = entry.stat()
        except OSError:
            continue
        relative_path = f"{normalized_sub}/{entry.name}" if normalized_sub else entry.name
        result.append(
            WorkspaceFileInfo(
                name=entry.name,
                path=relative_path,
                is_directory=entry.is_dir(),
                size=stat.st_size,
                modified_at=_mtime_iso(stat),
            )
        )

    result.sort(key=lambda f: (0 if f.is_directory else 1, f.name.lower()))
    return result


def list_workspace_file_tree(
    workspace_path: Path,
    sub_path: str = "",
) -> List[WorkspaceFileTreeNode]:
    """Recursively build a file-tree rooted at *sub_path* in *workspace_path*."""
    current_level = list_workspace_files(workspace_path, sub_path)
    nodes: List[WorkspaceFileTreeNode] = []
    for info in current_level:
        node = WorkspaceFileTreeNode(
            name=info.name,
            path=info.path,
            is_directory=info.is_directory,
            size=info.size,
            modified_at=info.modified_at,
        )
        if info.is_directory:
            node.children = list_workspace_file_tree(workspace_path, info.path)
        nodes.append(node)
    return nodes


def read_workspace_file_content(
    workspace_path: Path,
    file_path: str,
) -> WorkspaceFileContent:
    """Read a file from the workspace and return its content and metadata.

    Raises :class:`WorkspaceFileAccessError` when the file is not found, the
    path traverses outside the workspace, or the path points to a directory.
    """
    full_path = _resolve_workspace_safe_path(workspace_path, file_path)

    if not full_path.exists():
        raise WorkspaceFileAccessError("NOT_FOUND", "File not found", 404)

    if full_path.is_dir():
        raise WorkspaceFileAccessError(
            "IS_DIRECTORY",
            "Directory download is not supported",
            400,
        )

    stat = full_path.stat()
    return WorkspaceFileContent(
        content=full_path.read_bytes(),
        file_name=full_path.name,
        size=stat.st_size,
        modified_at=_mtime_iso(stat),
    )


def write_workspace_file(
    workspace_path: Path,
    file_path: str,
    content: bytes,
) -> str:
    """Write *content* to *file_path* inside *workspace_path*.

    Creates parent directories as needed.  When *file_path* is inside
    ``skills/``, symlinks are automatically re-synced and any recognised
    archive is extracted asynchronously.

    Returns the relative path of the written file.
    """
    full_path = _resolve_workspace_safe_path(workspace_path, file_path)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(content)

    if _is_skills_path(file_path):
        from .workspace_file_sync import sync_skills_symlinks  # local import
        sync_skills_symlinks(workspace_path)
        if is_archive(full_path.name):
            import threading
            threading.Thread(
                target=lambda: extract_archive_in_skills(workspace_path, full_path.name),
                daemon=True,
            ).start()

    return file_path


def delete_workspace_file(
    workspace_path: Path,
    file_path: str,
) -> bool:
    """Delete a file or directory from the workspace.

    Returns ``True`` on success, ``False`` when the path does not exist.
    Automatically re-syncs skills symlinks when the deleted path is inside
    ``skills/``.
    """
    full_path = _resolve_workspace_safe_path(workspace_path, file_path)

    if not full_path.exists() and not full_path.is_symlink():
        return False

    try:
        if full_path.is_dir() and not full_path.is_symlink():
            shutil.rmtree(full_path)
        else:
            full_path.unlink()
    except OSError:
        return False

    if _is_skills_path(file_path):
        from .workspace_file_sync import sync_skills_symlinks  # local import
        sync_skills_symlinks(workspace_path)

    return True


def move_workspace_file(
    workspace_path: Path,
    from_path: str,
    to_path: str,
) -> bool:
    """Move or rename a file within the workspace.

    Returns ``True`` on success, ``False`` when the source does not exist.
    Creates the destination parent directory if needed.  Re-syncs skills
    symlinks when either path is inside ``skills/``.
    """
    full_from = _resolve_workspace_safe_path(workspace_path, from_path)
    full_to = _resolve_workspace_safe_path(workspace_path, to_path)

    if not full_from.exists():
        return False

    try:
        full_to.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(full_from), str(full_to))
    except OSError:
        return False

    if _is_skills_path(from_path) or _is_skills_path(to_path):
        from .workspace_file_sync import sync_skills_symlinks  # local import
        sync_skills_symlinks(workspace_path)

    return True
