"""Stable contracts for the Claude MCP resource connector.

[Input] Admin-managed MCP rows, standard MCP discovery results, plus legacy importer/CLI compatibility evidence.
[Output] Managed CRUD/discovery/auth DTOs, safe compatibility projections, and structured semantic errors.
[Pos] Dependency-light contract layer shared by repository, discovery, router, service, importer, and legacy adapters.
[Sync] 2026-08-19: define the reviewed v1 state and error vocabulary.
[Sync] 2026-08-19: add fail-closed credential projection errors for user-to-thread synchronization.
[Sync] 2026-08-19: add restricted user-scope server configuration and ownership errors.
[Sync] 2026-08-20: add safe public-SDK inventory contracts for MCP tools and annotations.
[Sync] 2026-08-21: expose fail-closed CLI config scope and removability on server DTOs.
[Sync] 2026-08-25: project stable Runtime authentication identity and semantic MCP failures without exposing raw output.
[Sync] 2026-08-25: add database-managed scope/transport/auth/CRUD contracts while retaining safe legacy fields.
[Sync] 2026-08-25: distinguish missing OAuth callback configuration from missing credential encryption.
[Sync] 2026-08-25: treat unprobed remote authentication as unknown until standard-MCP discovery supplies evidence.
[Sync] 2026-08-27: distinguish transient PostgreSQL capability verification failures from a missing schema contract.
[Sync] 2026-09-06: add versioned deny-by-default MCP Apps policy and Phase 2/3 Node projections.
[Sync] 2026-09-06: add revisioned per-connection App preference and availability contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Mapping
from urllib.parse import urlsplit


_SERVER_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_MCP_APPS_SERVER_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_STDIO_PROFILE_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


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


class ClaudeMcpConfigScope(str, Enum):
    USER = "user"
    WORKSPACE = "workspace"
    LOCAL = "local"
    PROJECT = "project"
    PLUGIN = "plugin"
    UNKNOWN = "unknown"


class ClaudeMcpAuthState(str, Enum):
    """Transport authentication identity reported by the exact Runtime."""

    ANONYMOUS = "anonymous"
    REQUIRED = "required"
    AUTHENTICATED = "authenticated"
    UNKNOWN = "unknown"


class McpTransport(str, Enum):
    STREAMABLE_HTTP = "streamable_http"
    SSE = "sse"
    STDIO = "stdio"


class McpAuthKind(str, Enum):
    NONE = "none"
    OAUTH = "oauth"


class McpScope(str, Enum):
    USER = "user"
    WORKSPACE = "workspace"


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
    AUTH_NOT_REQUIRED = "CLAUDE_MCP_AUTH_NOT_REQUIRED"
    AUTH_NOT_ADVERTISED = "CLAUDE_MCP_AUTH_NOT_ADVERTISED"
    AUTH_METADATA_INVALID = "CLAUDE_MCP_AUTH_METADATA_INVALID"
    NETWORK_UNREACHABLE = "CLAUDE_MCP_NETWORK_UNREACHABLE"
    SERVER_REJECTED = "CLAUDE_MCP_SERVER_REJECTED"
    PROCESS_EXITED = "CLAUDE_MCP_PROCESS_EXITED"
    AUTH_TIMEOUT = "CLAUDE_MCP_AUTH_TIMEOUT"
    AUTH_CANCELLED = "CLAUDE_MCP_AUTH_CANCELLED"
    CREDENTIAL_SYNC_FAILED = "CLAUDE_MCP_CREDENTIAL_SYNC_FAILED"
    INVENTORY_UNAVAILABLE = "CLAUDE_MCP_INVENTORY_UNAVAILABLE"
    INVENTORY_TIMEOUT = "CLAUDE_MCP_INVENTORY_TIMEOUT"
    INVENTORY_MALFORMED = "CLAUDE_MCP_INVENTORY_MALFORMED"
    SCHEMA_CAPABILITY_MISSING = "CLAUDE_MCP_SCHEMA_CAPABILITY_MISSING"
    SCHEMA_CAPABILITY_UNAVAILABLE = "CLAUDE_MCP_SCHEMA_CAPABILITY_UNAVAILABLE"
    SERVER_ALREADY_EXISTS = "CLAUDE_MCP_SERVER_ALREADY_EXISTS"
    SERVER_REVISION_CONFLICT = "CLAUDE_MCP_SERVER_REVISION_CONFLICT"
    TRANSPORT_UNSUPPORTED = "CLAUDE_MCP_TRANSPORT_UNSUPPORTED"
    ENDPOINT_DENIED = "CLAUDE_MCP_ENDPOINT_DENIED"
    CREDENTIAL_REQUIRED = "CLAUDE_MCP_CREDENTIAL_REQUIRED"
    CREDENTIAL_INVALID = "CLAUDE_MCP_CREDENTIAL_INVALID"
    CREDENTIAL_ENCRYPTION_NOT_CONFIGURED = "CLAUDE_MCP_CREDENTIAL_ENCRYPTION_NOT_CONFIGURED"
    OAUTH_CONFIGURATION_MISSING = "CLAUDE_MCP_OAUTH_CONFIGURATION_MISSING"
    AUTH_OPERATION_EXPIRED = "CLAUDE_MCP_AUTH_OPERATION_EXPIRED"
    DISCOVERY_CANCELLED = "CLAUDE_MCP_DISCOVERY_CANCELLED"
    PROTOCOL_ERROR = "CLAUDE_MCP_PROTOCOL_ERROR"
    STDIO_PROFILE_DENIED = "CLAUDE_MCP_STDIO_PROFILE_DENIED"
    INVENTORY_TOO_LARGE = "CLAUDE_MCP_INVENTORY_TOO_LARGE"
    APP_RUNTIME_DENIED = "CLAUDE_MCP_APP_RUNTIME_DENIED"
    APP_RUNTIME_REVISION_CONFLICT = "CLAUDE_MCP_APP_RUNTIME_REVISION_CONFLICT"
    APP_RUNTIME_POLICY_INVALID = "CLAUDE_MCP_APP_RUNTIME_POLICY_INVALID"
    APP_SETTINGS_CAPABILITY_MISSING = "CLAUDE_MCP_APP_SETTINGS_CAPABILITY_MISSING"
    APP_SETTINGS_REVISION_CONFLICT = "CLAUDE_MCP_APP_SETTINGS_REVISION_CONFLICT"


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
    cli_version: str | None = None
    minimum_cli_version: str | None = None
    headless_minimum_cli_version: str | None = None
    credential_identity: str | None = None
    management_mode: str = "managed_db"
    schema_capability: str = "dream.managed-mcp-resources.v1"
    schema_version: int = 1
    transports: tuple[str, ...] = (
        McpTransport.STREAMABLE_HTTP.value,
        McpTransport.SSE.value,
        McpTransport.STDIO.value,
    )

    @classmethod
    def managed(
        cls,
        *,
        enabled: bool,
        reason_code: str | None = None,
    ) -> "ClaudeMcpCapability":
        return cls(enabled=enabled, reason_code=reason_code)

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "reason_code": self.reason_code,
            "cli_version": self.cli_version,
            "minimum_cli_version": self.minimum_cli_version,
            "headless_minimum_cli_version": self.headless_minimum_cli_version,
            "credential_identity": self.credential_identity,
            "management_mode": self.management_mode,
            "schema_capability": self.schema_capability,
            "schema_version": self.schema_version,
            "transports": list(self.transports),
        }


@dataclass(frozen=True)
class McpAppsPolicyState:
    """One explicit policy state; defaults are always deny."""

    resource_reads: bool = False
    low_risk_tool_calls: bool = False

    @classmethod
    def from_mapping(cls, value: Any, *, field_name: str) -> "McpAppsPolicyState":
        if not isinstance(value, dict) or set(value) != {
            "resourceReads",
            "lowRiskToolCalls",
        }:
            raise ValueError(f"invalid {field_name} MCP Apps policy state")
        if not all(isinstance(item, bool) for item in value.values()):
            raise ValueError(f"invalid {field_name} MCP Apps policy state")
        return cls(
            resource_reads=value["resourceReads"],
            low_risk_tool_calls=value["lowRiskToolCalls"],
        )

    def to_dict(self) -> dict[str, bool]:
        return {
            "resourceReads": self.resource_reads,
            "lowRiskToolCalls": self.low_risk_tool_calls,
        }


def _mcp_apps_string_tuple(value: Any, *, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item and "\x00" not in item for item in value
    ):
        raise ValueError(f"invalid {field_name}")
    if len(value) != len(set(value)):
        raise ValueError(f"duplicate {field_name}")
    return tuple(value)


@dataclass(frozen=True)
class McpAppsServerPolicy:
    """Server-owned positive lists; absence means that Server is unavailable to Apps."""

    allowed_tools: tuple[str, ...] = ()
    allowed_resources: tuple[str, ...] = ()
    app_callable_low_risk_tools: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, value: Any) -> "McpAppsServerPolicy":
        if not isinstance(value, dict) or set(value) != {
            "allowedTools",
            "allowedResources",
            "appCallableLowRiskTools",
        }:
            raise ValueError("invalid MCP Apps Server policy")
        allowed_tools = _mcp_apps_string_tuple(
            value["allowedTools"], field_name="allowedTools"
        )
        allowed_resources = _mcp_apps_string_tuple(
            value["allowedResources"], field_name="allowedResources"
        )
        callable_tools = _mcp_apps_string_tuple(
            value["appCallableLowRiskTools"],
            field_name="appCallableLowRiskTools",
        )
        if not set(callable_tools).issubset(allowed_tools):
            raise ValueError("appCallableLowRiskTools must be a subset of allowedTools")
        if any(not item.startswith("ui://") for item in allowed_resources):
            raise ValueError("allowedResources must contain only ui:// URIs")
        return cls(allowed_tools, allowed_resources, callable_tools)


@dataclass(frozen=True)
class McpAppsRuntimePolicy:
    """Versioned server-owned policy loaded from configuration, never Browser input."""

    version: int
    revision: int
    default: McpAppsPolicyState
    desired: McpAppsPolicyState
    effective: McpAppsPolicyState
    servers: Mapping[str, McpAppsServerPolicy]

    @classmethod
    def deny_all(cls) -> "McpAppsRuntimePolicy":
        state = McpAppsPolicyState()
        return cls(
            version=1,
            revision=1,
            default=state,
            desired=state,
            effective=state,
            servers=MappingProxyType({}),
        )

    @classmethod
    def from_mapping(cls, value: Any) -> "McpAppsRuntimePolicy":
        if not isinstance(value, dict) or set(value) != {
            "version",
            "revision",
            "default",
            "desired",
            "effective",
            "servers",
        }:
            raise ValueError("invalid MCP Apps policy")
        version = value["version"]
        revision = value["revision"]
        if not isinstance(version, int) or isinstance(version, bool) or version != 1:
            raise ValueError("unsupported MCP Apps policy version")
        if (
            not isinstance(revision, int)
            or isinstance(revision, bool)
            or revision < 1
            or revision > 9_007_199_254_740_991
        ):
            raise ValueError("invalid MCP Apps policy revision")
        default = McpAppsPolicyState.from_mapping(value["default"], field_name="default")
        desired = McpAppsPolicyState.from_mapping(value["desired"], field_name="desired")
        effective = McpAppsPolicyState.from_mapping(
            value["effective"], field_name="effective"
        )
        if default != McpAppsPolicyState():
            raise ValueError("MCP Apps default policy must deny every capability")
        if effective.resource_reads and not desired.resource_reads:
            raise ValueError("effective resourceReads exceeds desired policy")
        if effective.low_risk_tool_calls and not desired.low_risk_tool_calls:
            raise ValueError("effective lowRiskToolCalls exceeds desired policy")
        raw_servers = value["servers"]
        if not isinstance(raw_servers, dict) or not all(
            isinstance(key, str) and _MCP_APPS_SERVER_REF.fullmatch(key)
            for key in raw_servers
        ):
            raise ValueError("invalid MCP Apps Server policies")
        servers = {
            key: McpAppsServerPolicy.from_mapping(item)
            for key, item in raw_servers.items()
        }
        return cls(
            version,
            revision,
            default,
            desired,
            effective,
            MappingProxyType(servers),
        )

    def state_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "revision": self.revision,
            "default": self.default.to_dict(),
            "desired": self.desired.to_dict(),
            "effective": self.effective.to_dict(),
        }


@dataclass(frozen=True)
class McpAppPreferenceState:
    """One actor-owned desired state; the immutable default denies every choice."""

    enabled: bool = False
    low_risk_tool_calls: bool = False
    ui_messages: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "interactions": {
                "lowRiskToolCalls": self.low_risk_tool_calls,
                "uiMessages": self.ui_messages,
            },
        }


class McpAppAvailabilityState(str, Enum):
    READY = "ready"
    CONNECTION_DISABLED = "connection_disabled"
    TRANSPORT_UNSUPPORTED = "transport_unsupported"
    SERVER_POLICY_UNAVAILABLE = "server_policy_unavailable"
    INVENTORY_UNAVAILABLE = "inventory_unavailable"
    APP_NOT_ADVERTISED = "app_not_advertised"


@dataclass(frozen=True)
class McpAppServerAvailability:
    """Safe backend facts used by the Next deployment-policy composition root."""

    state: McpAppAvailabilityState
    reason_code: str | None
    resource_reads: bool = False
    low_risk_tool_calls: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "reasonCode": self.reason_code,
            "resourceReads": self.resource_reads,
            "lowRiskToolCalls": self.low_risk_tool_calls,
        }


@dataclass(frozen=True)
class McpAppConnectionSettings:
    """Default, actor desired, revision, and safe server-availability projection."""

    revision: int
    desired: McpAppPreferenceState
    server: McpAppServerAvailability
    default: McpAppPreferenceState = field(default_factory=McpAppPreferenceState)
    version: int = 1

    def __post_init__(self) -> None:
        if self.version != 1 or self.revision < 1:
            raise ValueError("invalid MCP App connection settings revision")

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "revision": self.revision,
            "default": self.default.to_dict(),
            "desired": self.desired.to_dict(),
            "server": self.server.to_dict(),
        }


@dataclass(frozen=True)
class McpAppSettingsPatch:
    expected_revision: int
    desired: McpAppPreferenceState
    workspace_id: str | None = None

    def __post_init__(self) -> None:
        if self.expected_revision < 1:
            raise ValueError("expected_revision must be positive")


@dataclass(frozen=True)
class McpAppsStaticView:
    """Non-sensitive Node composition metadata; never authorizes production Apps."""

    protocol_version: str
    policy: McpAppsRuntimePolicy = field(default_factory=McpAppsRuntimePolicy.deny_all)
    production_apps_effective: bool = False
    transports: tuple[str, ...] = (McpTransport.STREAMABLE_HTTP.value,)

    def to_dict(self) -> dict[str, object]:
        return {
            "protocolVersion": self.protocol_version,
            "productionAppsEffective": self.production_apps_effective,
            "transports": list(self.transports),
            "policy": self.policy.state_dict(),
        }


@dataclass(frozen=True, repr=False)
class McpAppsConnectionView:
    """Short-lived single-Server projection whose connection profile stays Node-only."""

    actor_scope: str
    workspace_scope: str | None
    server_id: str
    server_ref: str
    config_revision: int
    credential_revision: int
    app_settings_revision: int
    expires_at: str
    allowed_tools: tuple[str, ...]
    allowed_resources: tuple[str, ...]
    app_callable_low_risk_tools: tuple[str, ...]
    policy: McpAppsRuntimePolicy
    connection_profile: Mapping[str, Any]

    def __repr__(self) -> str:
        return (
            "McpAppsConnectionView("
            f"server_ref={self.server_ref!r}, config_revision={self.config_revision}, "
            f"credential_revision={self.credential_revision}, app_settings_revision={self.app_settings_revision}, "
            f"policy_revision={self.policy.revision}, "
            "connection_profile=<redacted>)"
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "actorScope": self.actor_scope,
            "workspaceScope": self.workspace_scope,
            "serverId": self.server_id,
            "serverRef": self.server_ref,
            "transportKind": McpTransport.STREAMABLE_HTTP.value,
            "enabled": True,
            "configRevision": self.config_revision,
            "credentialRevision": self.credential_revision,
            "appSettingsRevision": self.app_settings_revision,
            "expiresAt": self.expires_at,
            "allowedTools": list(self.allowed_tools),
            "allowedResources": list(self.allowed_resources),
            "appCallableLowRiskTools": list(self.app_callable_low_risk_tools),
            "policy": self.policy.state_dict(),
            "connectionProfile": dict(self.connection_profile),
        }


@dataclass(frozen=True)
class ClaudeMcpServer:
    name: str
    state: ClaudeMcpState
    transport: str | None = None
    detail: str | None = None
    active_operation_id: str | None = None
    config_scope: ClaudeMcpConfigScope = ClaudeMcpConfigScope.UNKNOWN
    removable: bool = False
    auth_state: ClaudeMcpAuthState = ClaudeMcpAuthState.UNKNOWN
    id: str | None = None
    display_name: str | None = None
    auth_kind: str | None = None
    enabled: bool = True
    revision: int | None = None
    credential_revision: int = 0
    credential_ref: str | None = None
    credential_configured: bool = False
    workspace_id: str | None = None
    url: str | None = None
    stdio_profile_key: str | None = None

    @classmethod
    def managed(
        cls,
        *,
        id: str,
        name: str,
        display_name: str,
        transport: str,
        config_scope: str,
        auth_kind: str,
        enabled: bool,
        revision: int,
        credential_revision: int = 0,
        credential_ref: str | None = None,
        credential_configured: bool = False,
        workspace_id: str | None = None,
        remote_url: str | None = None,
        stdio_profile_key: str | None = None,
        state: ClaudeMcpState | None = None,
    ) -> "ClaudeMcpServer":
        scope = (
            ClaudeMcpConfigScope.USER
            if config_scope == McpScope.USER.value
            else ClaudeMcpConfigScope.WORKSPACE
        )
        auth_state = (
            ClaudeMcpAuthState.AUTHENTICATED
            if credential_configured
            else ClaudeMcpAuthState.REQUIRED
            if auth_kind == McpAuthKind.OAUTH.value
            else ClaudeMcpAuthState.UNKNOWN
        )
        effective_state = state
        if effective_state is None:
            if not enabled:
                effective_state = ClaudeMcpState.DISABLED
            elif auth_kind == McpAuthKind.OAUTH.value and not credential_configured:
                effective_state = ClaudeMcpState.NEEDS_AUTH
            else:
                effective_state = ClaudeMcpState.CONFIGURED
        return cls(
            name=name,
            state=effective_state,
            transport=transport,
            config_scope=scope,
            removable=True,
            auth_state=auth_state,
            id=id,
            display_name=display_name,
            auth_kind=auth_kind,
            enabled=enabled,
            revision=revision,
            credential_revision=credential_revision,
            credential_ref=credential_ref,
            credential_configured=credential_configured,
            workspace_id=workspace_id,
            url=remote_url,
            stdio_profile_key=stdio_profile_key,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "state": self.state.value,
            "auth_state": self.auth_state.value,
            "transport": self.transport,
            "detail": self.detail,
            "active_operation_id": self.active_operation_id,
            "config_scope": self.config_scope.value,
            "removable": self.removable,
            "id": self.id,
            "display_name": self.display_name or self.name,
            "auth_kind": self.auth_kind,
            "enabled": self.enabled,
            "revision": self.revision,
            "credential_revision": self.credential_revision,
            "credential_ref": self.credential_ref,
            "credential_configured": self.credential_configured,
            "workspace_id": self.workspace_id,
            "url": self.url,
            "stdio_profile_key": self.stdio_profile_key,
        }


@dataclass(frozen=True)
class McpServerCreate:
    server_key: str
    display_name: str
    transport: McpTransport
    auth_kind: McpAuthKind
    scope: McpScope = McpScope.USER
    workspace_id: str | None = None
    remote_url: str | None = None
    stdio_profile_key: str | None = None
    enabled: bool = True
    idempotency_key: str | None = None

    def __post_init__(self) -> None:
        key = self.server_key.strip()
        display_name = self.display_name.strip()
        if not _SERVER_KEY.fullmatch(key) or not display_name or len(display_name) > 200:
            raise ValueError("invalid MCP server identity")
        object.__setattr__(self, "server_key", key)
        object.__setattr__(self, "display_name", display_name)
        if self.scope is McpScope.USER and self.workspace_id is not None:
            raise ValueError("user scope cannot carry workspace_id")
        if self.scope is McpScope.WORKSPACE and not self.workspace_id:
            raise ValueError("workspace scope requires workspace_id")
        if self.transport is McpTransport.STDIO:
            if self.remote_url is not None or not self.stdio_profile_key:
                raise ValueError("stdio requires only a profile key")
            if not _STDIO_PROFILE_KEY.fullmatch(self.stdio_profile_key):
                raise ValueError("invalid stdio profile key")
        else:
            if self.stdio_profile_key is not None or not self.remote_url:
                raise ValueError("remote transport requires only a URL")
            parsed = urlsplit(self.remote_url)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("invalid MCP remote URL")


@dataclass(frozen=True)
class McpServerPatch:
    expected_revision: int
    display_name: str | None = None
    transport: McpTransport | None = None
    auth_kind: McpAuthKind | None = None
    workspace_id: str | None = None
    remote_url: str | None = None
    stdio_profile_key: str | None = None
    enabled: bool | None = None

    def __post_init__(self) -> None:
        if self.expected_revision < 1:
            raise ValueError("expected_revision must be positive")
        if self.display_name is not None:
            value = self.display_name.strip()
            if not value or len(value) > 200:
                raise ValueError("invalid display name")
            object.__setattr__(self, "display_name", value)

    def changes(self) -> dict[str, Any]:
        return {
            "display_name": self.display_name,
            "transport": self.transport,
            "auth_kind": self.auth_kind,
            "remote_url": self.remote_url,
            "stdio_profile_key": self.stdio_profile_key,
            "enabled": self.enabled,
        }


class ClaudeMcpInventoryStatus(str, Enum):
    CONNECTED = "connected"
    FAILED = "failed"
    NEEDS_AUTH = "needs_auth"
    DISABLED = "disabled"


class ClaudeMcpCapabilityInventoryStatus(str, Enum):
    AVAILABLE = "available"
    NOT_REPORTED = "not_reported"


@dataclass(frozen=True)
class ClaudeMcpToolAnnotations:
    read_only: bool | None = None
    destructive: bool | None = None
    open_world: bool | None = None

    def to_dict(self) -> dict[str, bool | None]:
        return {
            "read_only": self.read_only,
            "destructive": self.destructive,
            "open_world": self.open_world,
        }


@dataclass(frozen=True)
class ClaudeMcpTool:
    name: str
    description: str | None
    annotations: ClaudeMcpToolAnnotations

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "annotations": self.annotations.to_dict(),
        }


@dataclass(frozen=True)
class ClaudeMcpServerInfo:
    name: str
    version: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "version": self.version}


@dataclass(frozen=True)
class ClaudeMcpServerInventory:
    server_name: str
    status: ClaudeMcpInventoryStatus
    config_scope: str
    runtime_scope: str | None
    transport: str | None
    url: str | None
    server_info: ClaudeMcpServerInfo | None
    tools: tuple[ClaudeMcpTool, ...]
    tool_count: int
    tools_truncated: bool
    refreshed_at: str

    def to_dict(self) -> dict[str, object]:
        tools_status = (
            ClaudeMcpCapabilityInventoryStatus.AVAILABLE
            if self.status is ClaudeMcpInventoryStatus.CONNECTED
            else ClaudeMcpCapabilityInventoryStatus.NOT_REPORTED
        )
        return {
            "server_name": self.server_name,
            "status": self.status.value,
            "config_scope": self.config_scope,
            "runtime_scope": self.runtime_scope,
            "transport": self.transport,
            "url": self.url,
            "server_info": self.server_info.to_dict() if self.server_info else None,
            "tools": [tool.to_dict() for tool in self.tools],
            "tool_count": self.tool_count,
            "tools_truncated": self.tools_truncated,
            "capabilities": {
                "tools": {
                    "status": tools_status.value,
                    "count": self.tool_count if tools_status is ClaudeMcpCapabilityInventoryStatus.AVAILABLE else None,
                },
                "resources": {
                    "status": ClaudeMcpCapabilityInventoryStatus.NOT_REPORTED.value,
                    "count": None,
                },
                "prompts": {
                    "status": ClaudeMcpCapabilityInventoryStatus.NOT_REPORTED.value,
                    "count": None,
                },
            },
            "refreshed_at": self.refreshed_at,
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
