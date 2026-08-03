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
from pathlib import Path
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


@dataclass(frozen=True)
class InitProfile:
    runtime_dirs: tuple[str, ...] = field(default_factory=tuple)
    workspace_files: tuple[WorkspaceFileSpec, ...] = field(default_factory=tuple)
    python: PythonRuntimeSpec | None = None


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

    return InitProfile(
        runtime_dirs=runtime_dirs,
        workspace_files=tuple(workspace_files),
        python=python_spec,
    )


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
