"""Workspace init profiles and managed per-plugin Python runtimes.

Design: docs/design/deck/drama-forge-workspace-init-design.md §4/§5.

A plugin artifact may carry ``.ink/workspace-init.json`` (digest-pinned with
the artifact).  When the workspace packer copies such an artifact into an
agent workspace it:

1. creates the declared runtime directory skeleton (``stories/`` …),
2. injects workspace files (e.g. the workspace CLAUDE.md, create-if-missing),
3. ensures a managed virtualenv for the plugin's Python toolchain under
   ``<runtime-root>/plugin-runtimes/<artifact_digest>/venv`` and records it
   in the launch manifest so the CLI launcher can prepend it to ``PATH``.

Init runs only on first pack; frozen workspaces never re-run init steps
(the venv is a derived cache and may be rebuilt — plugin versions and init
results stay frozen).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

INIT_PROFILE_RELATIVE_PATH = Path(".ink") / "workspace-init.json"
INIT_PROFILE_SCHEMA_VERSION = "workspace-init/v1"
RUNTIME_RECEIPT_NAME = "runtime-receipt.json"
VENV_DIR_NAME = "venv"


class WorkspaceInitError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class WorkspaceFileSpec:
    path: str
    source: str
    mode: str = "create-if-missing"


@dataclass(frozen=True)
class PythonRuntimeSpec:
    requirements: str
    min_version: str | None = None


# --- surfaces[] extension (design_004 §3.1; schema stays workspace-init/v1) ---

ALLOWED_SURFACE_NAMES = frozenset({"dream"})
RESERVED_PROTOCOL_DIRS = frozenset({".ink", ".editor", ".notion"})
PROTOCOL_DIR_RE = re.compile(r"^\.[a-z][a-z0-9-]*$")
ENTRY_ROUTE_PREFIX = "/story-workspace/"


@dataclass(frozen=True)
class SurfaceSpec:
    name: str
    protocol_dir: str
    entry_route: str


def validate_surfaces(raw: list) -> list[SurfaceSpec]:
    """Validate a profile's ``surfaces[]``; fail-closed on anything illegal.

    Rules (design_004 §3.1): name whitelist, single-level dot-prefixed
    protocol dir outside the reserved set, entry route confined to the
    story-workspace domain, and per-profile uniqueness of both name and
    protocol_dir.  Raises ``WorkspaceInitError`` with code
    ``CLAUDE_PLUGIN_INIT_PROFILE_INVALID`` (surfaced as
    ``WorkspacePackError`` with the same code at the pack boundary).
    """
    specs: list[SurfaceSpec] = []
    seen_names: set[str] = set()
    seen_dirs: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise WorkspaceInitError(
                "CLAUDE_PLUGIN_INIT_PROFILE_INVALID",
                "surfaces entries must be objects",
            )
        name = item.get("name", "")
        pdir = item.get("protocol_dir", "")
        route = item.get("entry_route", "")
        ok = (
            isinstance(name, str)
            and name in ALLOWED_SURFACE_NAMES
            and isinstance(pdir, str)
            and PROTOCOL_DIR_RE.match(pdir) is not None
            and pdir not in RESERVED_PROTOCOL_DIRS
            and isinstance(route, str)
            and route.startswith(ENTRY_ROUTE_PREFIX)
            and name not in seen_names
            and pdir not in seen_dirs
        )
        if not ok:
            raise WorkspaceInitError(
                "CLAUDE_PLUGIN_INIT_PROFILE_INVALID",
                f"invalid surface declaration: {item!r}",
            )
        seen_names.add(name)
        seen_dirs.add(pdir)
        specs.append(SurfaceSpec(name=name, protocol_dir=pdir, entry_route=route))
    return specs


@dataclass(frozen=True)
class InitProfile:
    runtime_dirs: tuple[str, ...] = field(default_factory=tuple)
    workspace_files: tuple[WorkspaceFileSpec, ...] = field(default_factory=tuple)
    python: PythonRuntimeSpec | None = None
    surfaces: tuple[SurfaceSpec, ...] = field(default_factory=tuple)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _validate_relative(value: object, *, what: str, allow_ink: bool = False) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkspaceInitError(
            "CLAUDE_PLUGIN_INIT_PROFILE_INVALID", f"{what} must be a non-empty string"
        )
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise WorkspaceInitError(
            "CLAUDE_PLUGIN_INIT_PROFILE_INVALID",
            f"{what} must be a workspace-relative path without '..': {value!r}",
        )
    if not allow_ink and candidate.parts and candidate.parts[0] == ".ink":
        raise WorkspaceInitError(
            "CLAUDE_PLUGIN_INIT_PROFILE_INVALID",
            f"{what} must not target the server-controlled .ink/ tree: {value!r}",
        )
    return value


def load_init_profile(packed_dir: Path) -> InitProfile | None:
    """Parse and validate ``<packed_dir>/.ink/workspace-init.json``.

    Returns None when the plugin ships no profile (fully backwards
    compatible).  Any malformed profile raises — fail-closed.
    """
    packed_dir = Path(packed_dir)
    profile_path = packed_dir / INIT_PROFILE_RELATIVE_PATH
    if not profile_path.is_file():
        return None
    try:
        payload = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceInitError(
            "CLAUDE_PLUGIN_INIT_PROFILE_INVALID",
            f"init profile is not valid JSON: {profile_path}",
        ) from exc
    if not isinstance(payload, dict):
        raise WorkspaceInitError(
            "CLAUDE_PLUGIN_INIT_PROFILE_INVALID", "init profile must be a JSON object"
        )
    if payload.get("schema_version") != INIT_PROFILE_SCHEMA_VERSION:
        raise WorkspaceInitError(
            "CLAUDE_PLUGIN_INIT_PROFILE_INVALID",
            f"unsupported init profile schema: {payload.get('schema_version')!r}",
        )

    raw_dirs = payload.get("runtime_dirs") or []
    if not isinstance(raw_dirs, list):
        raise WorkspaceInitError(
            "CLAUDE_PLUGIN_INIT_PROFILE_INVALID", "'runtime_dirs' must be a list"
        )
    runtime_dirs = tuple(
        _validate_relative(item, what="runtime_dirs entry") for item in raw_dirs
    )

    raw_files = payload.get("workspace_files") or []
    if not isinstance(raw_files, list):
        raise WorkspaceInitError(
            "CLAUDE_PLUGIN_INIT_PROFILE_INVALID", "'workspace_files' must be a list"
        )
    workspace_files: list[WorkspaceFileSpec] = []
    for item in raw_files:
        if not isinstance(item, dict):
            raise WorkspaceInitError(
                "CLAUDE_PLUGIN_INIT_PROFILE_INVALID",
                "workspace_files entries must be objects",
            )
        mode = item.get("mode", "create-if-missing")
        if mode != "create-if-missing":
            raise WorkspaceInitError(
                "CLAUDE_PLUGIN_INIT_PROFILE_INVALID",
                f"unsupported workspace_files mode: {mode!r}",
            )
        spec = WorkspaceFileSpec(
            path=_validate_relative(item.get("path"), what="workspace_files.path"),
            # source is artifact-relative and legitimately lives under .ink/
            source=_validate_relative(
                item.get("source"), what="workspace_files.source", allow_ink=True
            ),
            mode=mode,
        )
        if not (packed_dir / spec.source).is_file():
            raise WorkspaceInitError(
                "CLAUDE_PLUGIN_INIT_PROFILE_INVALID",
                f"workspace_files source missing from artifact: {spec.source}",
            )
        workspace_files.append(spec)

    python_spec: PythonRuntimeSpec | None = None
    raw_python = payload.get("python")
    if raw_python is not None:
        if not isinstance(raw_python, dict):
            raise WorkspaceInitError(
                "CLAUDE_PLUGIN_INIT_PROFILE_INVALID", "'python' must be an object"
            )
        requirements = _validate_relative(
            raw_python.get("requirements"), what="python.requirements"
        )
        if not (packed_dir / requirements).is_file():
            raise WorkspaceInitError(
                "CLAUDE_PLUGIN_INIT_PROFILE_INVALID",
                f"python.requirements missing from artifact: {requirements}",
            )
        min_version = raw_python.get("min_version")
        if min_version is not None and not isinstance(min_version, str):
            raise WorkspaceInitError(
                "CLAUDE_PLUGIN_INIT_PROFILE_INVALID",
                "python.min_version must be a string",
            )
        python_spec = PythonRuntimeSpec(requirements=requirements, min_version=min_version)

    raw_surfaces = payload.get("surfaces") or []
    if not isinstance(raw_surfaces, list):
        raise WorkspaceInitError(
            "CLAUDE_PLUGIN_INIT_PROFILE_INVALID", "'surfaces' must be a list"
        )
    surfaces = tuple(validate_surfaces(raw_surfaces))

    return InitProfile(
        runtime_dirs=runtime_dirs,
        workspace_files=tuple(workspace_files),
        python=python_spec,
        surfaces=surfaces,
    )


# --- .dream/ protocol directory materialization (design_004 §3.2-§3.4) ---

DREAM_SURFACE_README = """# .dream/ — Dream Surface 协议目录

本目录由 packer 在会话首个 agent turn 的 pack 时物理映射到会话工作区，标识本工作区由 Dream 驱动插件加载。

## 静态启动层只读

- README.md 与 workspace.json 由 packer 写入，Agent 不得修改或删除。
- workspace.json 只记录 deck_id、插件制品清单和入口路由；pack 后保持冻结，
  不含 workflow_run_id、来源五字段或时间戳。

## Agent 运行内容层

- 页面描述位于 runtime/runs/<workflow_run_id>/run.json 与 stages/*.json。
- Agent 只能调用 mcp__story_workspace__write_dream_run 和
  mcp__story_workspace__write_dream_stage 更新运行内容层。
- 第一集只允许通过 mcp__story_workspace__bind_first_episode 建立服务端
  绑定，通过 mcp__story_workspace__record_episode_workflow_completion 记录受控的
  技术完成修订；两者均校验 host 注入的 run/thread/message 上下文，
  不持有剧情、剧本、分镜、Prompt 或渲染内容。
- 禁止使用 Write、Edit 或 Bash 直接修改 .dream；受控工具会从 host 读取
  actor、thread 与冻结的 WorkflowRun 来源字段，并校验 revision 和 source files。
- 先写人物、场景或分镜的 canonical 工作区文件，再调用 stage 工具同步页面元信息。
- Agent 对话的真相源是标准 Thread history/status/SSE；Dream 与 Chat
  使用同一 thread_id 恢复消息、确认、Stop 和终态。
- story-workspace REST API 只读取 Workflow 与 Artifact 业务投影；投影由
  DreamObserver 基于内部 EventBus 事实幂等更新，不产生第二套前端 SSE。

入口路由：/story-workspace/dream
"""


def materialize_dream_surface(
    workspace: Path, deck_id: str, plugins: list[dict], entry_route: str
) -> dict:
    """Materialize the static ``.dream/`` protocol directory; returns an
    audit step for the pack receipt.

    Atomic (audit A4): both files are written into a temporary directory and
    moved into place with ``os.rename``; any write failure fails the whole
    pack and never leaves a half-written ``.dream/``.  An already complete
    ``.dream/`` is kept (create-if-missing) so a re-pack of the same digest
    is byte-identical.  The payload holds launch facts only — no
    workflow_run_id, no timestamps (DEC-029).
    """
    workspace = Path(workspace)
    dream_dir = workspace / ".dream"
    if (dream_dir / "workspace.json").is_file() and (dream_dir / "README.md").is_file():
        return {"step": "materialize-surface", "surface": "dream", "path": ".dream/"}
    payload = {
        "schema_version": "dream-surface/v1",
        "deck_id": deck_id,
        "plugins": plugins,
        "entry_route": entry_route,
    }
    tmp_dir = workspace / f".dream.tmp-{os.getpid()}"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir()
    try:
        (tmp_dir / "workspace.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (tmp_dir / "README.md").write_text(DREAM_SURFACE_README, encoding="utf-8")
        if dream_dir.exists():
            shutil.rmtree(dream_dir)  # clear a half-written dir before rebuild
        os.rename(tmp_dir, dream_dir)
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
    return {"step": "materialize-surface", "surface": "dream", "path": ".dream/"}


def execute_init_profile(
    workspace: Path, packed_dir: Path, profile: InitProfile
) -> list[dict]:
    """Apply the profile to a fresh workspace; returns audit steps.

    Idempotent by construction: existing directories are kept, existing
    files are never overwritten (create-if-missing).
    """
    workspace = Path(workspace)
    packed_dir = Path(packed_dir)
    steps: list[dict] = []
    for rel_dir in profile.runtime_dirs:
        target = workspace / rel_dir
        if target.is_dir():
            steps.append({"action": "mkdir", "path": rel_dir, "result": "exists"})
            continue
        target.mkdir(parents=True, exist_ok=True)
        steps.append({"action": "mkdir", "path": rel_dir, "result": "created"})
    for spec in profile.workspace_files:
        target = workspace / spec.path
        if target.exists():
            steps.append(
                {"action": "write-file", "path": spec.path, "result": "exists-kept"}
            )
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(packed_dir / spec.source, target)
        steps.append({"action": "write-file", "path": spec.path, "result": "created"})
    return steps


def _requirements_digest(packed_dir: Path, spec: PythonRuntimeSpec) -> str:
    content = (packed_dir / spec.requirements).read_bytes()
    return hashlib.sha256(content).hexdigest()


def _check_min_version(min_version: str | None) -> None:
    if not min_version:
        return
    try:
        want = tuple(int(part) for part in min_version.split(".")[:2])
    except ValueError as exc:
        raise WorkspaceInitError(
            "CLAUDE_PLUGIN_INIT_PROFILE_INVALID",
            f"python.min_version is not a version string: {min_version!r}",
        ) from exc
    if sys.version_info[: len(want)] < want:
        raise WorkspaceInitError(
            "CLAUDE_PLUGIN_RUNTIME_FAILED",
            f"managed Python {sys.version.split()[0]} does not satisfy "
            f"min_version {min_version}",
        )


def ensure_plugin_venv(
    runtime_root: Path, artifact_digest: str, packed_dir: Path, spec: PythonRuntimeSpec
) -> Path:
    """Ensure the managed venv for one artifact digest; returns the venv dir.

    Layout: ``<runtime_root>/plugin-runtimes/<digest>/venv`` plus a receipt
    recording the requirements hash and interpreter version.  A matching
    existing venv is reused; anything else is rebuilt under a flock.
    """
    _check_min_version(spec.min_version)
    runtime_root = Path(runtime_root)
    # Digest carries a ':' (sha256:<hex>) which is the PATH separator and is
    # refused by `python -m venv`; reuse the artifact-store naming convention.
    slot_name = artifact_digest.replace(":", "-")
    slot = runtime_root / "plugin-runtimes" / slot_name
    slot.mkdir(parents=True, exist_ok=True)
    venv_dir = slot / VENV_DIR_NAME
    receipt_path = slot / RUNTIME_RECEIPT_NAME
    requirements_hash = _requirements_digest(Path(packed_dir), spec)

    lock_path = slot / ".lock"
    with open(lock_path, "w", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            interpreter = venv_dir / "bin" / "python3"
            if interpreter.is_file() and receipt_path.is_file():
                try:
                    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    receipt = {}
                if receipt.get("requirements_sha256") == requirements_hash:
                    return venv_dir

            if venv_dir.exists():
                shutil.rmtree(venv_dir)
            create = subprocess.run(
                [sys.executable, "-m", "venv", str(venv_dir)],
                capture_output=True,
                text=True,
                timeout=180,
            )
            if create.returncode != 0:
                raise WorkspaceInitError(
                    "CLAUDE_PLUGIN_RUNTIME_FAILED",
                    f"venv creation failed: {(create.stderr or '')[-500:]}",
                )
            install = subprocess.run(
                [
                    str(interpreter), "-m", "pip", "install",
                    "--disable-pip-version-check", "--no-input",
                    "-r", str(Path(packed_dir) / spec.requirements),
                ],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if install.returncode != 0:
                shutil.rmtree(venv_dir, ignore_errors=True)
                tail = (install.stderr or install.stdout or "")[-800:]
                raise WorkspaceInitError(
                    "CLAUDE_PLUGIN_RUNTIME_FAILED",
                    f"pip install failed for {spec.requirements}: {tail}",
                )
            receipt_path.write_text(
                json.dumps(
                    {
                        "artifact_digest": artifact_digest,
                        "requirements": spec.requirements,
                        "requirements_sha256": requirements_hash,
                        "python_version": sys.version.split()[0],
                        "created_at": _now(),
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            return venv_dir
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
