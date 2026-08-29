# [Input] Server-owned Notion credential home and centralized CLI policy.
# [Output] Safe ntn login/poll/doctor helpers with minimal environment and redacted failures.
# [Pos] auth driver node in backend/notion; paths are resolved only by credentials.py.
# [Sync] 2026-08-28: remove request/process-home resolution, ambient token inheritance,
#                    public path output, and obsolete `ntn auth status` usage.
# [Sync] 2026-08-28: normalize imports during the final agentdata credential audit.

"""Notion authentication helpers backed by the server-owned ``ntn`` CLI."""
from __future__ import annotations

import asyncio
import contextlib
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from .errors import (
    NotionAuthError,
    NotionAuthTimeoutError,
    NotionCLIUnavailableError,
    NotionConfigError,
)

_DEFAULT_LOGIN_TIMEOUT_S = 20.0
_DEFAULT_POLL_TIMEOUT_S = 15.0
_DEFAULT_STATUS_TIMEOUT_S = 10.0
_URL_RE = re.compile(r"https?://\S+")
_VERIFICATION_CODE_RE = re.compile(r"\b[A-Z0-9]{3,5}(?:-[A-Z0-9]{2,5})+\b")
_NO_PENDING_SESSION_TOKENS = (
    "no pending login session found",
    "authorization session already consumed",
)
_PARENT_ENV_ALLOWLIST = (
    "PATH",
    "LANG",
    "LC_ALL",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "HTTPS_PROXY",
    "HTTP_PROXY",
    "NO_PROXY",
    "https_proxy",
    "http_proxy",
    "no_proxy",
)


@dataclass(frozen=True)
class LoginInitResult:
    """Parsed response from ``ntn login --no-browser``."""

    verification_url: str
    verification_code: str
    poll_interval_seconds: int = 5


@dataclass(frozen=True)
class AuthStatusResult:
    """Safe authentication state; raw CLI output never crosses this boundary."""

    status: str
    detail: str = ""


def _positive_timeout(name: str, default: float, *, maximum: float = 300.0) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if 0 < value <= maximum else default


def resolve_ntn_executable() -> str:
    """Resolve one server-controlled executable; connector/user data cannot override it."""

    configured = os.environ.get("INK_NOTION_CLI_PATH", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute() or not candidate.is_file() or not os.access(candidate, os.X_OK):
            raise NotionCLIUnavailableError("Notion service is temporarily unavailable.")
        return str(candidate.resolve(strict=True))
    discovered = shutil.which("ntn")
    if not discovered:
        raise NotionCLIUnavailableError("Notion service is temporarily unavailable.")
    return str(Path(discovered).resolve(strict=True))


def ensure_notion_home(notion_home: str | Path) -> Path:
    """Create one explicit server-owned home without consulting HOME/config/env."""

    path = Path(notion_home)
    if not path.is_absolute():
        raise NotionConfigError("Notion credential home must be an absolute server path.")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink() or not path.is_dir():
        raise NotionConfigError("Notion credential home is not a safe directory.")
    os.chmod(path, 0o700, follow_symlinks=False)
    return path.resolve(strict=True)


def build_notion_env(notion_home: str | Path) -> dict[str, str]:
    """Build a minimal ntn environment with a non-overridable file store."""

    home = ensure_notion_home(notion_home)
    env = {
        key: os.environ[key]
        for key in _PARENT_ENV_ALLOWLIST
        if os.environ.get(key)
    }
    env["NOTION_HOME"] = str(home)
    env["NOTION_KEYRING"] = "0"
    # Deliberately omit NOTION_API_TOKEN and HOME. The user identity is the
    # server-owned file snapshot, never an ambient process or user env value.
    return env


def _parse_login_output(stdout: str) -> LoginInitResult:
    url_match = _URL_RE.search(stdout or "")
    code_match = _VERIFICATION_CODE_RE.search(stdout or "")
    if not url_match or not code_match:
        raise NotionAuthError("Notion authorization could not be started. Please retry.")
    return LoginInitResult(
        verification_url=url_match.group(0).rstrip(").,"),
        verification_code=code_match.group(0).strip(),
        poll_interval_seconds=5,
    )


async def _run_ntn_command(
    *args: str,
    notion_home: str | Path,
    timeout_seconds: float,
) -> tuple[int, str, str]:
    executable = resolve_ntn_executable()
    try:
        proc = await asyncio.create_subprocess_exec(
            executable,
            *args,
            env=build_notion_env(notion_home),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except (FileNotFoundError, PermissionError, OSError) as exc:
        raise NotionCLIUnavailableError("Notion service is temporarily unavailable.") from exc

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
    except TimeoutError as exc:
        proc.kill()
        with contextlib.suppress(Exception):
            await proc.wait()
        raise NotionAuthTimeoutError("Notion authorization timed out. Please retry.") from exc

    return proc.returncode or 0, stdout.decode("utf-8", "replace"), stderr.decode("utf-8", "replace")


async def start_login(notion_home: str | Path) -> LoginInitResult:
    """Start device authorization inside an isolated pending user home."""

    code, stdout, stderr = await _run_ntn_command(
        "login",
        "--no-browser",
        notion_home=notion_home,
        timeout_seconds=_positive_timeout(
            "INK_NOTION_AUTH_LOGIN_TIMEOUT_SECONDS", _DEFAULT_LOGIN_TIMEOUT_S
        ),
    )
    if code != 0:
        raise NotionAuthError("Notion authorization could not be started. Please retry.")
    return _parse_login_output(stdout or stderr)


async def poll_login(notion_home: str | Path) -> AuthStatusResult:
    """Poll device authorization and map CLI output to a safe product state."""

    code, stdout, stderr = await _run_ntn_command(
        "login",
        "poll",
        notion_home=notion_home,
        timeout_seconds=_positive_timeout(
            "INK_NOTION_AUTH_POLL_TIMEOUT_SECONDS", _DEFAULT_POLL_TIMEOUT_S
        ),
    )
    combined = f"{stdout}\n{stderr}".lower()
    if code == 0:
        return AuthStatusResult(status="authenticated", detail="Notion is connected.")
    if any(token in combined for token in _NO_PENDING_SESSION_TOKENS):
        return AuthStatusResult(
            status="consumed",
            detail="Notion authorization is no longer active. Start authorization again.",
        )
    if "slow_down" in combined or "authorization_pending" in combined or "pending" in combined:
        return AuthStatusResult(
            status="pending",
            detail="Waiting for confirmation in Notion.",
        )
    if "expired" in combined or "timeout" in combined:
        return AuthStatusResult(
            status="expired",
            detail="Notion authorization expired. Start authorization again.",
        )
    raise NotionAuthError("Notion authorization could not be completed. Please retry.")


async def verify_status(notion_home: str | Path) -> AuthStatusResult:
    """Use the supported ``ntn doctor`` command to check the effective session."""

    code, stdout, stderr = await _run_ntn_command(
        "doctor",
        notion_home=notion_home,
        timeout_seconds=_positive_timeout(
            "INK_NOTION_AUTH_STATUS_TIMEOUT_SECONDS", _DEFAULT_STATUS_TIMEOUT_S
        ),
    )
    if code == 0:
        return AuthStatusResult(status="authenticated", detail="Notion is connected.")
    combined = f"{stdout}\n{stderr}".lower()
    if any(token in combined for token in ("unauthorized", "expired", "invalid", "not logged")):
        return AuthStatusResult(
            status="expired",
            detail="Notion authorization expired. Reconnect Notion and retry.",
        )
    return AuthStatusResult(
        status="error",
        detail="Notion connection could not be verified. Reconnect Notion and retry.",
    )


def normalize_login_result(result: object) -> dict[str, object]:
    """Return a path-free public response."""

    if isinstance(result, LoginInitResult):
        return {
            "verificationUrl": result.verification_url,
            "verificationCode": result.verification_code,
            "pollIntervalSeconds": result.poll_interval_seconds,
        }
    if isinstance(result, AuthStatusResult):
        return {"status": result.status, "detail": result.detail}
    raise NotionConfigError("Unsupported Notion auth result.")


__all__ = [
    "AuthStatusResult",
    "LoginInitResult",
    "build_notion_env",
    "ensure_notion_home",
    "normalize_login_result",
    "poll_login",
    "resolve_ntn_executable",
    "start_login",
    "verify_status",
]
