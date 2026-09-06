"""Actor-scoped orchestration for database-managed MCP resources.

[Input] Injected PostgreSQL repository, standard-MCP discovery, OAuth coordinator, and policy.
[Output] Safe CRUD, capability, discovery, OAuth, logout, and legacy-compatible DTO projections.
[Pos] Managed MCP application service; no CLI, subprocess, filesystem config, or runtime DDL.
[Sync] 2026-08-25: replace online CLI management with exact-capability managed PostgreSQL flow.
[Sync] 2026-08-25: report OAuth callback and credential-cipher configuration gates separately.
[Sync] 2026-08-25: derive anonymous/OAuth requirements from standard-MCP discovery instead of public CRUD inputs.
[Sync] 2026-08-27: report transient capability verification separately while allowing repository retries.
[Sync] 2026-09-06: enforce versioned server-owned Apps policy before credential projection.
[Sync] 2026-09-06: emit the authoritative post-refresh credential revision with each Node connection profile.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Any

from .contracts import (
    ClaudeMcpCapability,
    ClaudeMcpError,
    ClaudeMcpErrorCode,
    ClaudeMcpServer,
    ClaudeMcpState,
    McpAppsConnectionView,
    McpAppsRuntimePolicy,
    McpAppsStaticView,
    McpAuthKind,
    McpScope,
    McpServerCreate,
    McpServerPatch,
    McpTransport,
)
from .repository import McpServerRecord

_default_service: "ClaudeMcpService | None" = None


class ClaudeMcpService:
    """Expose managed MCP behavior while keeping repository/network roles separate."""

    def __init__(
        self,
        *,
        repository: Any,
        discovery: Any,
        oauth: Any,
        runtime_snapshot_loader: Any = None,
        mcp_apps_policy_provider: Any = None,
        pool: Any = None,
    ) -> None:
        self.repository = repository
        self.discovery = discovery
        self.oauth = oauth
        self.runtime_snapshot_loader = runtime_snapshot_loader
        self.mcp_apps_policy_provider = mcp_apps_policy_provider
        self._pool = pool

    async def _require_capability(self) -> None:
        if not await self.repository.capability_available():
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.SCHEMA_CAPABILITY_MISSING,
                "Managed MCP database capability is unavailable.",
            )

    @staticmethod
    def _project(record: McpServerRecord, *, state: ClaudeMcpState | None = None) -> ClaudeMcpServer:
        return ClaudeMcpServer.managed(
            id=record.id,
            name=record.server_key,
            display_name=record.display_name,
            transport=record.transport.value,
            config_scope=record.scope,
            auth_kind=record.auth_kind.value,
            enabled=record.enabled,
            revision=record.config_revision,
            credential_revision=record.credential_revision,
            credential_ref=record.credential_id,
            credential_configured=record.credential_configured,
            workspace_id=record.workspace_id,
            remote_url=record.remote_url,
            stdio_profile_key=record.stdio_profile_key,
            state=state,
        )

    async def capability(self, actor_id: str) -> ClaudeMcpCapability:
        del actor_id
        try:
            available = await self.repository.capability_available()
        except ClaudeMcpError as exc:
            if exc.code is not ClaudeMcpErrorCode.SCHEMA_CAPABILITY_UNAVAILABLE:
                raise
            return ClaudeMcpCapability.managed(
                enabled=False,
                reason_code=exc.code.value,
            )
        return ClaudeMcpCapability.managed(
            enabled=available,
            reason_code=(
                None
                if available
                else ClaudeMcpErrorCode.SCHEMA_CAPABILITY_MISSING.value
            ),
        )

    async def list_servers(
        self, actor_id: str, workspace_id: str | None = None
    ) -> list[ClaudeMcpServer]:
        await self._require_capability()
        return [
            self._project(record)
            for record in await self.repository.list_servers(actor_id, workspace_id)
        ]

    async def _record(
        self, actor_id: str, identifier: str, workspace_id: str | None = None
    ) -> McpServerRecord:
        await self._require_capability()
        record = await self.repository.get_server(actor_id, identifier, workspace_id)
        if record is None:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.SERVER_NOT_FOUND,
                "Claude MCP server was not found.",
            )
        return record

    async def get_server(
        self, actor_id: str, identifier: str, workspace_id: str | None = None
    ) -> ClaudeMcpServer:
        return self._project(await self._record(actor_id, identifier, workspace_id))

    def _mcp_apps_policy(self) -> McpAppsRuntimePolicy:
        try:
            value = (
                self.mcp_apps_policy_provider()
                if callable(self.mcp_apps_policy_provider)
                else self.mcp_apps_policy_provider
            )
            if value is None:
                return McpAppsRuntimePolicy.deny_all()
            if isinstance(value, McpAppsRuntimePolicy):
                return value
            return McpAppsRuntimePolicy.from_mapping(value)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.APP_RUNTIME_POLICY_INVALID,
                "MCP Apps server policy is unavailable.",
            ) from exc

    def mcp_apps_static_view(self) -> McpAppsStaticView:
        return McpAppsStaticView(
            protocol_version="2026-01-26",
            policy=self._mcp_apps_policy(),
        )

    async def mcp_apps_connection_view(
        self,
        actor_id: str,
        identifier: str,
        workspace_scope: str | None,
        *,
        expected_config_revision: int | None,
        expected_credential_revision: int | None,
        ttl_seconds: float,
        expected_policy_revision: int | None = None,
        now: datetime | None = None,
    ) -> McpAppsConnectionView:
        """Return one short-lived Node-only view after pre-decryption validation."""
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        record = await self._record(actor_id, identifier, workspace_scope)
        if str(record.user_id) != str(actor_id) or not record.enabled:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.APP_RUNTIME_DENIED,
                "MCP Apps connection view is unavailable.",
            )
        if (
            expected_config_revision is not None
            and expected_config_revision != record.config_revision
        ) or (
            expected_credential_revision is not None
            and expected_credential_revision != record.credential_revision
        ):
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.APP_RUNTIME_REVISION_CONFLICT,
                "MCP Apps session revision is no longer current.",
            )
        policy = self._mcp_apps_policy()
        if (
            expected_policy_revision is not None
            and expected_policy_revision != policy.revision
        ):
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.APP_RUNTIME_REVISION_CONFLICT,
                "MCP Apps session policy revision is no longer current.",
            )
        server_policy = policy.servers.get(record.server_key)
        if (
            server_policy is None
            or not policy.effective.resource_reads
        ):
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.APP_RUNTIME_DENIED,
                "MCP Apps connection view is unavailable.",
            )
        snapshot = await self.repository.get_discovery_snapshot(actor_id, record)
        inventory = snapshot.get("inventory") if isinstance(snapshot, dict) else None
        if not isinstance(inventory, dict) or snapshot.get("status") != "complete":
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.INVENTORY_UNAVAILABLE,
                "MCP Apps catalog is unavailable.",
            )
        raw_tools = inventory.get("tools")
        raw_resources = inventory.get("resources")
        if not isinstance(raw_tools, list) or not isinstance(raw_resources, list):
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.INVENTORY_MALFORMED,
                "MCP Apps catalog is invalid.",
            )
        def inventory_tool_is_low_risk(tool: Any) -> bool:
            if not isinstance(tool, dict) or not isinstance(tool.get("name"), str):
                return False
            annotations = tool.get("annotations")
            metadata = tool.get("_meta")
            return (
                isinstance(annotations, dict)
                and annotations.get("readOnlyHint") is True
                and annotations.get("destructiveHint") is not True
                and annotations.get("confirmationRequired") is not True
                and annotations.get("requiresConfirmation") is not True
                and (
                    not isinstance(metadata, dict)
                    or (
                        metadata.get("confirmationRequired") is not True
                        and metadata.get("requiresConfirmation") is not True
                    )
                )
            )

        inventory_tools = {
            str(tool["name"])
            for tool in raw_tools
            if isinstance(tool, dict) and isinstance(tool.get("name"), str)
        }
        inventory_safe_tools = {
            str(tool["name"])
            for tool in raw_tools
            if inventory_tool_is_low_risk(tool)
        }
        allowed_tools = tuple(
            name
            for name in server_policy.allowed_tools
            if name in inventory_tools
        )
        allowed_resources = tuple(
            uri
            for uri in server_policy.allowed_resources
            if any(
                isinstance(resource, dict) and resource.get("uri") == uri
                for resource in raw_resources
            )
        )
        app_callable_low_risk_tools = tuple(
            name
            for name in server_policy.app_callable_low_risk_tools
            if (
                policy.effective.low_risk_tool_calls
                and name in allowed_tools
                and name in inventory_safe_tools
            )
        )
        if not allowed_tools or not allowed_resources or self.runtime_snapshot_loader is None:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.INVENTORY_UNAVAILABLE,
                "MCP Apps read-only catalog is unavailable.",
            )
        projected = await self.runtime_snapshot_loader.load_server_config(
            actor_id,
            record,
            expected_config_revision=record.config_revision,
            expected_credential_revision=record.credential_revision,
        )
        config = projected.config
        if config.get("type") != "http" or not isinstance(config.get("url"), str):
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.TRANSPORT_UNSUPPORTED,
                "MCP Apps Phase 1 requires Streamable HTTP.",
            )
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        profile: dict[str, Any] = {
            "type": McpTransport.STREAMABLE_HTTP.value,
            "url": config["url"],
        }
        if isinstance(config.get("headers"), dict):
            profile["headers"] = dict(config["headers"])
        return McpAppsConnectionView(
            actor_scope=str(actor_id),
            workspace_scope=workspace_scope,
            server_id=str(record.id),
            server_ref=record.server_key,
            config_revision=projected.config_revision,
            credential_revision=projected.credential_revision,
            expires_at=(current + timedelta(seconds=ttl_seconds)).isoformat(),
            allowed_tools=allowed_tools,
            allowed_resources=allowed_resources,
            app_callable_low_risk_tools=app_callable_low_risk_tools,
            policy=policy,
            connection_profile=profile,
        )

    async def create_server(
        self, actor_id: str, create: McpServerCreate
    ) -> ClaudeMcpServer:
        await self._require_capability()
        return self._project(await self.repository.create_server(actor_id, create))

    async def configure_http_server(
        self, actor_id: str, server_name: str, server_url: str
    ) -> ClaudeMcpServer:
        """Retain the safe legacy HTTP create shape without invoking a CLI."""
        try:
            create = McpServerCreate(
                server_key=server_name,
                display_name=server_name,
                transport=McpTransport.STREAMABLE_HTTP,
                auth_kind=McpAuthKind.NONE,
                scope=McpScope.USER,
                remote_url=server_url,
            )
        except ValueError as exc:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.SERVER_CONFIGURATION_INVALID,
                "Claude MCP server configuration is invalid.",
            ) from exc
        return await self.create_server(actor_id, create)

    async def update_server(
        self, actor_id: str, identifier: str, patch: McpServerPatch
    ) -> ClaudeMcpServer:
        record = await self._record(actor_id, identifier, patch.workspace_id)
        next_transport = patch.transport or record.transport
        next_url = (
            patch.remote_url if patch.remote_url is not None else record.remote_url
        )
        next_stdio_profile = (
            patch.stdio_profile_key
            if patch.stdio_profile_key is not None
            else record.stdio_profile_key
        )
        endpoint_changed = (
            next_transport is not record.transport
            or next_url != record.remote_url
            or next_stdio_profile != record.stdio_profile_key
        )
        if endpoint_changed and patch.auth_kind is None:
            # auth_kind is an internal, detected projection. A changed
            # transport/endpoint must be probed again instead of inheriting a
            # user's old anonymous/OAuth choice.
            patch = replace(patch, auth_kind=McpAuthKind.NONE)
        return self._project(
            await self.repository.update_server(actor_id, record.id, patch)
        )

    async def _persist_detected_auth_kind(
        self,
        actor_id: str,
        identifier: str,
        workspace_id: str | None,
        result: Any,
    ) -> Any:
        """Persist only protocol-evidenced auth classification in the DB row."""

        if (
            result.error is None
            or result.error.code != "CLAUDE_MCP_CREDENTIAL_REQUIRED"
        ):
            # Successful anonymous discovery keeps the default NONE value.
            # Other failures carry no authentication evidence and must not
            # rewrite configuration or add list/discovery N+1 reads.
            return result
        record = await self._record(actor_id, identifier, workspace_id)
        if record.transport is McpTransport.STDIO:
            return result
        desired = McpAuthKind.OAUTH
        if record.auth_kind is desired:
            return result

        try:
            updated = await self.repository.update_server(
                actor_id,
                record.id,
                McpServerPatch(
                    expected_revision=record.config_revision,
                    auth_kind=desired,
                    workspace_id=workspace_id,
                ),
            )
        except ClaudeMcpError as exc:
            if exc.code is not ClaudeMcpErrorCode.SERVER_REVISION_CONFLICT:
                raise
            # A concurrent request may already have persisted the same
            # protocol evidence. Re-read once and accept that converged state.
            current = await self._record(actor_id, record.id, workspace_id)
            if current.auth_kind is not desired:
                raise
            updated = current

        adjusted = replace(result, config_revision=updated.config_revision)
        save_snapshot = getattr(self.repository, "save_discovery_snapshot", None)
        if save_snapshot is not None:
            try:
                await save_snapshot(
                    actor_id,
                    updated,
                    adjusted,
                    ttl_seconds=self.discovery.policy.cache_ttl_seconds,
                )
            except (AttributeError, TypeError):
                await save_snapshot(actor_id, updated, adjusted)
        return adjusted

    async def remove_server(
        self,
        actor_id: str,
        identifier: str,
        expected_revision: int | None = None,
        workspace_id: str | None = None,
    ) -> ClaudeMcpServer:
        record = await self._record(actor_id, identifier, workspace_id)
        removed = await self.repository.delete_server(
            actor_id, record.id, expected_revision, workspace_id
        )
        return self._project(removed, state=ClaudeMcpState.NOT_CONFIGURED)

    async def discover_server(
        self,
        actor_id: str,
        identifier: str,
        workspace_id: str | None = None,
        force: bool = False,
    ):
        await self._require_capability()
        result = await self.discovery.discover_one(
            actor_id, identifier, workspace_id=workspace_id, force=force
        )
        return await self._persist_detected_auth_kind(
            actor_id, identifier, workspace_id, result
        )

    async def get_server_inventory(
        self, actor_id: str, identifier: str, workspace_id: str | None = None
    ):
        return await self.discover_server(actor_id, identifier, workspace_id)

    async def discover_servers(
        self,
        actor_id: str,
        identifiers: list[str],
        workspace_id: str | None = None,
        force: bool = False,
    ):
        await self._require_capability()
        # The coordinator resolves each identifier under actor/workspace scope
        # inside its TaskGroup, then applies the bounded remote semaphore.  Do
        # not pre-read every row serially here: that duplicated repository
        # lookups and reintroduced an avoidable 2N management N+1.
        results = await self.discovery.discover_many(
            actor_id,
            identifiers,
            workspace_id=workspace_id,
            force=force,
        )
        return await asyncio.gather(
            *(
                self._persist_detected_auth_kind(
                    actor_id, identifier, workspace_id, result
                )
                for identifier, result in zip(identifiers, results)
            )
        )

    async def cancel_discovery(
        self,
        actor_id: str,
        identifier: str,
        workspace_id: str | None = None,
    ) -> bool:
        record = await self._record(actor_id, identifier, workspace_id)
        return await self.discovery.cancel(actor_id, record.id)

    async def start_auth(
        self, actor_id: str, identifier: str, workspace_id: str | None = None
    ):
        record = await self._record(actor_id, identifier, workspace_id)
        if record.auth_kind is not McpAuthKind.OAUTH:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.AUTH_NOT_REQUIRED,
                "Claude MCP authentication is not required for this server.",
            )
        return await self.oauth.start(actor_id, record)

    async def get_operation(self, actor_id: str, operation_id: str):
        await self._require_capability()
        return await self.oauth.get(actor_id, operation_id)

    async def submit_redirect(
        self, actor_id: str, operation_id: str, redirect_url: str
    ):
        await self._require_capability()
        return await self.oauth.submit_redirect(actor_id, operation_id, redirect_url)

    async def cancel_auth(self, actor_id: str, operation_id: str):
        await self._require_capability()
        return await self.oauth.cancel(actor_id, operation_id)

    async def logout(
        self, actor_id: str, identifier: str, workspace_id: str | None = None
    ) -> ClaudeMcpServer:
        record = await self._record(actor_id, identifier, workspace_id)
        updated = await self.repository.delete_credential(actor_id, record.id)
        return self._project(updated, state=ClaudeMcpState.LOGGED_OUT)

    async def shutdown(self) -> None:
        await self.oauth.shutdown()
        if self._pool is not None:
            self._pool.close()


class _UnavailableOAuthCoordinator:
    def __init__(self, code: ClaudeMcpErrorCode, message: str) -> None:
        self.code = code
        self.message = message

    async def _unavailable(self, *_args: Any, **_kwargs: Any):
        raise ClaudeMcpError(self.code, self.message)

    start = get = submit_redirect = cancel = _unavailable

    async def shutdown(self) -> None:
        return None


class _CredentialUnavailableAuthResolver:
    async def resolve(self, actor_id: str, server: McpServerRecord):
        del actor_id
        if server.credential_configured:
            from .crypto import McpCredentialConfigurationError

            raise McpCredentialConfigurationError()
        return None


def _mcp_apps_policy_from_env() -> McpAppsRuntimePolicy:
    """Read the current server-owned policy on demand so revisions invalidate sessions."""
    raw = os.environ.get("INK_MCP_APPS_POLICY_JSON")
    if raw is None:
        return McpAppsRuntimePolicy.deny_all()
    try:
        return McpAppsRuntimePolicy.from_mapping(json.loads(raw))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ClaudeMcpError(
            ClaudeMcpErrorCode.APP_RUNTIME_POLICY_INVALID,
            "MCP Apps server policy is unavailable.",
        ) from exc


def build_default_claude_mcp_service() -> ClaudeMcpService:
    """Open and inject the production PostgreSQL/MCP dependencies explicitly."""
    from .crypto import McpCredentialCipher, McpCredentialConfigurationError
    from .inventory import (
        McpDiscoveryCoordinator,
        McpDiscoveryPolicy,
        McpSdkSessionFactory,
        StdioProfileResolver,
    )
    from .oauth import ManagedMcpAuthResolver, ManagedMcpOAuthCoordinator
    from .repository import PostgresMcpRepository
    from .runtime_snapshot import ManagedMcpRuntimeSnapshotLoader
    from .settings import ClaudeMcpSettings
    try:
        from backend.persistence.postgres import PostgresPool
    except ModuleNotFoundError:  # pragma: no cover
        from persistence.postgres import PostgresPool

    settings = ClaudeMcpSettings.from_env()
    pool = PostgresPool.from_env(application_name="ink-dream-managed-mcp")
    pool.open()
    repository = PostgresMcpRepository(pool)
    try:
        cipher = McpCredentialCipher.from_env()
    except McpCredentialConfigurationError:
        cipher = None
    stdio_profiles = StdioProfileResolver.from_json(settings.stdio_profiles_json)
    session_factory = McpSdkSessionFactory(
        stdio_profiles=stdio_profiles,
        connect_timeout_seconds=settings.discovery_item_timeout_seconds,
        read_timeout_seconds=settings.discovery_server_timeout_seconds,
    )
    policy = McpDiscoveryPolicy(
        max_parallel_servers=settings.discovery_max_parallel_servers,
        server_timeout_seconds=settings.discovery_server_timeout_seconds,
        item_timeout_seconds=settings.discovery_item_timeout_seconds,
        max_inventory_items=settings.max_inventory_items,
        max_inventory_pages=settings.max_inventory_pages,
        max_text_length=settings.max_inventory_text_length,
        cache_ttl_seconds=settings.discovery_cache_ttl_seconds,
    )
    auth_resolver: Any = (
        None if cipher is not None else _CredentialUnavailableAuthResolver()
    )
    oauth: Any = _UnavailableOAuthCoordinator(
        ClaudeMcpErrorCode.CREDENTIAL_ENCRYPTION_NOT_CONFIGURED,
        "Managed MCP credential encryption is not configured.",
    )
    metadata = None
    if settings.oauth_redirect_uri and cipher is not None:
        from mcp.shared.auth import OAuthClientMetadata

        metadata = OAuthClientMetadata(
            redirect_uris=[settings.oauth_redirect_uri],
            client_name=settings.oauth_client_name,
        )
        auth_resolver = ManagedMcpAuthResolver(
            repository,
            cipher,
            client_metadata=metadata,
            timeout_seconds=settings.discovery_server_timeout_seconds,
        )
    discovery = McpDiscoveryCoordinator(
        repository, session_factory, policy=policy, auth_resolver=auth_resolver
    )
    runtime_snapshot_loader = ManagedMcpRuntimeSnapshotLoader(
        repository,
        cipher,
        stdio_profiles=stdio_profiles,
        max_servers=settings.max_servers_per_actor,
        oauth_refresher=discovery,
    )
    if metadata is not None:
        oauth = ManagedMcpOAuthCoordinator(
            repository,
            cipher,
            discovery,
            client_metadata=metadata,
            auth_timeout_seconds=settings.auth_timeout_seconds,
            readiness_timeout_seconds=settings.readiness_timeout_seconds,
            max_redirect_url_length=settings.max_redirect_url_length,
        )
    elif cipher is not None:
        oauth = _UnavailableOAuthCoordinator(
            ClaudeMcpErrorCode.OAUTH_CONFIGURATION_MISSING,
            "Managed MCP OAuth callback configuration is unavailable.",
        )
    return ClaudeMcpService(
        repository=repository,
        discovery=discovery,
        oauth=oauth,
        runtime_snapshot_loader=runtime_snapshot_loader,
        mcp_apps_policy_provider=_mcp_apps_policy_from_env,
        pool=pool,
    )


def get_default_claude_mcp_service() -> ClaudeMcpService:
    """Return the process singleton shared by Router and Chat integration."""
    global _default_service
    if _default_service is None:
        _default_service = build_default_claude_mcp_service()
    return _default_service


def get_default_managed_mcp_runtime_snapshot_loader():
    """Return the singleton service's injectable Runtime snapshot loader."""
    return get_default_claude_mcp_service().runtime_snapshot_loader


async def shutdown_default_claude_mcp_service() -> None:
    global _default_service
    service, _default_service = _default_service, None
    if service is not None:
        await service.shutdown()


__all__ = [
    "ClaudeMcpService",
    "build_default_claude_mcp_service",
    "get_default_claude_mcp_service",
    "get_default_managed_mcp_runtime_snapshot_loader",
    "shutdown_default_claude_mcp_service",
]
