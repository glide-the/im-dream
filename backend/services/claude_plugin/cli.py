"""Real Claude CLI subprocess execution with evidence capture.

Hard rules (deck-integration-delta §Install Flow):

- argv arrays only.  ``shell=True``, ``os.system`` and string command lines
  are forbidden everywhere in this package.
- The executable is resolved once via ``shutil.which("claude")`` (or the
  explicit ``INK_CLAUDE_CLI_PATH`` override) and must be a real file.
- Every execution records: executable, argv, cwd, CLI version, timeout,
  exit code, sanitized stdout/stderr and the file-tree snapshot delta around
  the managed config dir.
- A non-zero exit or a timeout never produces a ``ready`` record; the
  operation evidence is still persisted for audit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from . import runtime

_ENV_CLI_PATH = "INK_CLAUDE_CLI_PATH"
_DEFAULT_TIMEOUT_SECONDS = 300
_MAX_CAPTURE_BYTES = 64 * 1024

# Redact common credential shapes before persisting output.
_REDACT_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_-]{8,}"),
    re.compile(r"(?i)(authorization:\s*bearer\s+)[A-Za-z0-9._-]+"),
    re.compile(r"(?i)(x-api-key:\s*)[A-Za-z0-9._-]+"),
]


class ClaudeCliError(RuntimeError):
    """Raised when the Claude CLI cannot be located or executed."""


@dataclass(frozen=True)
class CliExecution:
    """Evidence for one real CLI subprocess execution."""

    executable: str
    argv: list[str]
    cwd: str
    cli_version: str
    exit_code: int
    timed_out: bool
    stdout: str
    stderr: str
    started_at: str
    finished_at: str
    duration_ms: int

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    def to_json(self) -> dict[str, object]:
        return {
            "executable": self.executable,
            "argv": list(self.argv),
            "cwd": self.cwd,
            "cli_version": self.cli_version,
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
        }


def resolve_claude_binary() -> Path:
    """Return the verified path of the real ``claude`` executable."""
    override = os.environ.get(_ENV_CLI_PATH, "").strip()
    candidate: str | None = None
    if override:
        expanded = Path(override).expanduser()
        if expanded.is_file() and os.access(expanded, os.X_OK):
            candidate = str(expanded.resolve())
    else:
        found = shutil.which("claude")
        if found:
            candidate = str(Path(found).resolve())
    if candidate is None:
        raise ClaudeCliError(
            "Claude CLI executable not found. Install Claude Code or set "
            f"{_ENV_CLI_PATH} to an executable path."
        )
    return Path(candidate)


def _sanitize(text: str) -> str:
    for pattern in _REDACT_PATTERNS:
        text = pattern.sub(lambda m: (m.group(1) if m.lastindex else "") + "<redacted>", text)
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) > _MAX_CAPTURE_BYTES:
        half = _MAX_CAPTURE_BYTES // 2
        text = (
            encoded[:half].decode("utf-8", errors="replace")
            + "\n…<truncated>…\n"
            + encoded[-half:].decode("utf-8", errors="replace")
        )
    return text


def snapshot_file_tree(root: Path) -> dict[str, str]:
    """Map ``relative/path -> sha256:<hex>`` for regular files under *root*."""
    root = Path(root)
    snapshot: dict[str, str] = {}
    if not root.is_dir():
        return snapshot
    for item in sorted(root.rglob("*")):
        if not item.is_file():
            continue
        try:
            relative = item.relative_to(root).as_posix()
        except ValueError:  # pragma: no cover - defensive
            continue
        digest = hashlib.sha256()
        try:
            with item.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError:
            continue
        snapshot[relative] = "sha256:" + digest.hexdigest()
    return snapshot


def snapshot_delta(before: dict[str, str], after: dict[str, str]) -> dict[str, list[str]]:
    """Compute created/changed/deleted between two file-tree snapshots."""
    created = sorted(path for path in after if path not in before)
    deleted = sorted(path for path in before if path not in after)
    changed = sorted(
        path for path in after if path in before and after[path] != before[path]
    )
    return {"created": created, "changed": changed, "deleted": deleted}


def get_cli_version(executable: Path | None = None) -> str:
    """Return the real ``claude --version`` output (single line)."""
    binary = executable or resolve_claude_binary()
    result = subprocess.run(
        [str(binary), "--version"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise ClaudeCliError(
            f"claude --version failed with exit code {result.returncode}: "
            f"{result.stderr.strip()[:200]}"
        )
    return result.stdout.strip().splitlines()[0] if result.stdout.strip() else "unknown"


def run_claude(
    argv: list[str],
    *,
    cwd: Path,
    timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS,
) -> CliExecution:
    """Execute the real Claude CLI with an argv array; never a shell.

    *argv* excludes the executable itself (e.g. ``["plugin", "install", X]``).
    The managed ``CLAUDE_CONFIG_DIR`` is injected by :func:`runtime.managed_cli_env`.
    """
    if not argv or not all(isinstance(part, str) and part for part in argv):
        raise ClaudeCliError(f"argv must be a non-empty list of strings: {argv!r}")
    binary = resolve_claude_binary()
    cli_version = get_cli_version(binary)
    full_argv = [str(binary), *argv]
    started = datetime.now(UTC)
    timed_out = False
    try:
        result = subprocess.run(
            full_argv,
            cwd=str(cwd),
            env=runtime.managed_cli_env(),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        exit_code = result.returncode
        stdout = result.stdout or ""
        stderr = result.stderr or ""
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = -1
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = ((exc.stderr or "") if isinstance(exc.stderr, str) else "") + (
            f"\n<timeout after {timeout_seconds}s>"
        )
    finished = datetime.now(UTC)
    return CliExecution(
        executable=str(binary),
        argv=full_argv,
        cwd=str(cwd),
        cli_version=cli_version,
        exit_code=exit_code,
        timed_out=timed_out,
        stdout=_sanitize(stdout),
        stderr=_sanitize(stderr),
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
        duration_ms=int((finished - started).total_seconds() * 1000),
    )


def write_operation_evidence(operation_id: str, payload: dict[str, object]) -> Path:
    """Persist an operation evidence document under the managed root."""
    operations_dir = runtime.get_operations_root() / operation_id
    operations_dir.mkdir(parents=True, exist_ok=True)
    path = operations_dir / "operation.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path
