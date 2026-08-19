"""Central policy settings for Claude MCP subprocess and credential projection.

[Input] Optional process-level policy environment variables and backend data root.
[Output] Validated runtime root, timeouts, capture/file bounds, and CLI version gates.
[Pos] Sole configuration source for Claude MCP operational policy; route handlers contain no policy literals.
[Sync] 2026-08-19: add bounded, deployment-name-independent OAuth process settings.
[Sync] 2026-08-19: add the absolute server-owned user credential root and bounded JSON projection size.
[Sync] 2026-08-19: add the bounded restricted HTTP server URL policy.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


_DEFAULT_RUNTIME_ROOT = (
    Path(__file__).resolve().parents[1] / "data" / "claude-mcp-runtime"
)


def _absolute_path(name: str, default: Path) -> Path:
    raw = os.environ.get(name, "").strip()
    candidate = Path(raw).expanduser() if raw else default
    if not candidate.is_absolute():
        return default.resolve(strict=False)
    return candidate.resolve(strict=False)


def _positive_int(name: str, default: int, *, maximum: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if 0 < value <= maximum else default


@dataclass(frozen=True)
class ClaudeMcpSettings:
    auth_timeout_seconds: int
    command_timeout_seconds: int
    terminate_grace_seconds: int
    readiness_timeout_seconds: int
    max_capture_bytes: int
    max_server_name_length: int
    max_redirect_url_length: int
    max_server_url_length: int = 2048
    runtime_root: Path = _DEFAULT_RUNTIME_ROOT
    max_credential_file_bytes: int = 1048576
    minimum_cli_version: str = "2.1.186"
    headless_minimum_cli_version: str = "2.1.191"

    @classmethod
    def from_env(cls) -> "ClaudeMcpSettings":
        return cls(
            runtime_root=_absolute_path(
                "INK_CLAUDE_MCP_RUNTIME_ROOT", _DEFAULT_RUNTIME_ROOT
            ),
            auth_timeout_seconds=_positive_int(
                "INK_CLAUDE_MCP_AUTH_TIMEOUT_SECONDS", 600, maximum=3600
            ),
            command_timeout_seconds=_positive_int(
                "INK_CLAUDE_MCP_COMMAND_TIMEOUT_SECONDS", 30, maximum=300
            ),
            terminate_grace_seconds=_positive_int(
                "INK_CLAUDE_MCP_TERMINATE_GRACE_SECONDS", 3, maximum=30
            ),
            readiness_timeout_seconds=_positive_int(
                "INK_CLAUDE_MCP_READINESS_TIMEOUT_SECONDS", 15, maximum=120
            ),
            max_capture_bytes=_positive_int(
                "INK_CLAUDE_MCP_MAX_CAPTURE_BYTES", 65536, maximum=1048576
            ),
            max_server_name_length=_positive_int(
                "INK_CLAUDE_MCP_MAX_SERVER_NAME_LENGTH", 512, maximum=2048
            ),
            max_redirect_url_length=_positive_int(
                "INK_CLAUDE_MCP_MAX_REDIRECT_URL_LENGTH", 8192, maximum=32768
            ),
            max_server_url_length=_positive_int(
                "INK_CLAUDE_MCP_MAX_SERVER_URL_LENGTH", 2048, maximum=8192
            ),
            max_credential_file_bytes=_positive_int(
                "INK_CLAUDE_MCP_MAX_CREDENTIAL_FILE_BYTES",
                1048576,
                maximum=16777216,
            ),
        )
