"""Stable contracts for the Claude MCP resource connector.

[Input] Claude CLI capability/status evidence and user-owned OAuth operation transitions.
[Output] Domain enums, safe DTO projections, runtime identity, and structured errors.
[Pos] Dependency-light contract layer shared by the router, driver, service, and tests.
[Sync] 2026-08-19: define the reviewed v1 state and error vocabulary.
[Sync] 2026-08-19: add fail-closed credential projection errors for user-to-thread synchronization.
[Sync] 2026-08-19: add restricted user-scope server configuration and ownership errors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Mapping


class ClaudeMcpState(str, Enum):
    NOT_CONFIGURED = "not_configured"
    CONFIGURED = "configured"
    NEEDS_AUTH = "needs_auth"
    AUTH_STARTING = "auth_starting"
    WAITING_FOR_USER = "waiting_for_user"
    EXCHANGING_CODE = "exchanging_code"
    CONNECTED = "connected"
    FAILED = "failed"
    CANCELLING = "cancelling"
    LOGGED_OUT = "logged_out"
    DISABLED = "disabled"


class ClaudeMcpErrorCode(str, Enum):
    IDENTITY_UNAVAILABLE = "CLAUDE_MCP_IDENTITY_UNAVAILABLE"
    CLI_UNAVAILABLE = "CLAUDE_MCP_CLI_UNAVAILABLE"
    CLI_VERSION_UNSUPPORTED = "CLAUDE_MCP_CLI_VERSION_UNSUPPORTED"
    SERVER_NOT_FOUND = "CLAUDE_MCP_SERVER_NOT_FOUND"
    SERVER_CONFIGURATION_INVALID = "CLAUDE_MCP_SERVER_CONFIGURATION_INVALID"
    SERVER_OWNERSHIP_CONFLICT = "CLAUDE_MCP_SERVER_OWNERSHIP_CONFLICT"
    OPERATION_NOT_FOUND = "CLAUDE_MCP_OPERATION_NOT_FOUND"
    OPERATION_CONFLICT = "CLAUDE_MCP_OPERATION_CONFLICT"
    INVALID_REDIRECT_URL = "CLAUDE_MCP_INVALID_REDIRECT_URL"
    MALFORMED_CLI_OUTPUT = "CLAUDE_MCP_MALFORMED_CLI_OUTPUT"
    CLI_FAILED = "CLAUDE_MCP_CLI_FAILED"
    AUTH_TIMEOUT = "CLAUDE_MCP_AUTH_TIMEOUT"
    AUTH_CANCELLED = "CLAUDE_MCP_AUTH_CANCELLED"
    CREDENTIAL_SYNC_FAILED = "CLAUDE_MCP_CREDENTIAL_SYNC_FAILED"


class ClaudeMcpError(RuntimeError):
    """Client-safe domain error; details must never contain OAuth material."""

    def __init__(self, code: ClaudeMcpErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ClaudeMcpRuntimeIdentity:
    """One exact CLI/config/cwd/credential identity shared with an Agent runtime."""

    command: tuple[str, ...]
    config_dir: Path
    cwd: Path
    env: Mapping[str, str]
    fingerprint: str

    def __post_init__(self) -> None:
        if not self.command or not all(self.command):
            raise ValueError("command must contain a non-empty executable argv")
        if not Path(self.command[0]).is_absolute():
            raise ValueError("command executable must be an absolute path")
        if not self.config_dir.is_absolute() or not self.cwd.is_absolute():
            raise ValueError("config_dir and cwd must be absolute")


@dataclass(frozen=True)
class ClaudeMcpCapability:
    enabled: bool
    reason_code: str | None
    cli_version: str | None
    minimum_cli_version: str
    headless_minimum_cli_version: str
    credential_identity: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "reason_code": self.reason_code,
            "cli_version": self.cli_version,
            "minimum_cli_version": self.minimum_cli_version,
            "headless_minimum_cli_version": self.headless_minimum_cli_version,
            "credential_identity": self.credential_identity,
        }


@dataclass(frozen=True)
class ClaudeMcpServer:
    name: str
    state: ClaudeMcpState
    transport: str | None = None
    detail: str | None = None
    active_operation_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "state": self.state.value,
            "transport": self.transport,
            "detail": self.detail,
            "active_operation_id": self.active_operation_id,
        }


@dataclass
class ClaudeMcpOperation:
    id: str
    actor_id: str
    identity_fingerprint: str
    server_name: str
    state: ClaudeMcpState
    created_at: str
    updated_at: str
    authorization_url: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    redirect_submitted: bool = False
    task: object | None = field(default=None, repr=False)
    handle: object | None = field(default=None, repr=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "server_name": self.server_name,
            "state": self.state.value,
            "authorization_url": self.authorization_url,
            "error": (
                {"code": self.error_code, "message": self.error_message}
                if self.error_code
                else None
            ),
            "redirect_submitted": self.redirect_submitted,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
