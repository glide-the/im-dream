"""Actor-scoped PostgreSQL repository for Admin-owned managed MCP tables.

[Input] An already-open PostgreSQL pool/UoW factory and exact Admin capability hash.
[Output] Read-only list/get plus transactional CRUD, credential, discovery snapshot, and import receipt operations.
[Pos] Sole Dream persistence boundary for `dream_mcp_*`; contains no DDL, SQLite, CLI, network, or runtime fallback.
[Sync] 2026-08-25: implement dream.managed-mcp-resources.v1 consumption with actor scope and CAS.
[Sync] 2026-08-25: cache the immutable process-lifetime schema capability after one exact fail-closed check.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import threading
from typing import Any, Protocol
import uuid

try:
    from backend.persistence.errors import UniqueConstraintError
    from backend.persistence.postgres import ConnectionPool
    from backend.persistence.unit_of_work import PostgresUnitOfWork
    from backend.schema.capabilities import (
        MANAGED_MCP_RESOURCES_CAPABILITY,
        MANAGED_MCP_RESOURCES_CONTRACT_SHA256,
        MANAGED_MCP_RESOURCES_VERSION,
    )
except ModuleNotFoundError:  # pragma: no cover - backend PYTHONPATH compatibility
    from persistence.errors import UniqueConstraintError
    from persistence.postgres import ConnectionPool
    from persistence.unit_of_work import PostgresUnitOfWork
    from schema.capabilities import (
        MANAGED_MCP_RESOURCES_CAPABILITY,
        MANAGED_MCP_RESOURCES_CONTRACT_SHA256,
        MANAGED_MCP_RESOURCES_VERSION,
    )

from .contracts import (
    ClaudeMcpError,
    ClaudeMcpErrorCode,
    McpAuthKind,
    McpScope,
    McpServerCreate,
    McpServerPatch,
    McpTransport,
)


UnitOfWorkFactory = Callable[..., Any]


@dataclass(frozen=True)
class McpServerRecord:
    id: str
    user_id: str
    workspace_id: str | None
    scope: str
    server_key: str
    display_name: str
    transport: McpTransport
    remote_url: str | None
    stdio_profile_key: str | None
    auth_kind: McpAuthKind
    enabled: bool
    config_revision: int
    credential_revision: int
    credential_id: str | None
    credential_configured: bool
    created_at: str
    updated_at: str


@dataclass(frozen=True, repr=False)
class McpCredentialRecord:
    id: str
    server_id: str
    user_id: str
    kind: str
    ciphertext: str
    iv: str
    tag: str
    fingerprint: str
    key_version: int
    credential_revision: int
    expires_at: str | None

    def __repr__(self) -> str:
        return (
            "McpCredentialRecord(id=<redacted>, server_id=<redacted>, "
            f"kind={self.kind!r}, credential_revision={self.credential_revision})"
        )


@dataclass(frozen=True)
class McpImportReceipt:
    state: str
    target_server_id: str | None
    canonical_config_sha256: str


class ManagedMcpRepository(Protocol):
    async def capability_available(self) -> bool: ...
    async def list_servers(self, actor_id: str, workspace_id: str | None = None) -> list[McpServerRecord]: ...
    async def get_server(self, actor_id: str, identifier: str, workspace_id: str | None = None) -> McpServerRecord | None: ...
    async def create_server(self, actor_id: str, create: McpServerCreate) -> McpServerRecord: ...
    async def update_server(self, actor_id: str, server_id: str, patch: McpServerPatch) -> McpServerRecord: ...
    async def delete_server(self, actor_id: str, server_id: str, expected_revision: int | None, workspace_id: str | None = None) -> McpServerRecord: ...


_SERVER_SELECT = """
    SELECT server.id, server.user_id, server.server_key, server.display_name,
           server.scope_type, server.scope_id, server.transport,
           server.remote_url, server.stdio_profile_key, server.auth_kind,
           server.enabled, server.config_revision,
           credential.id AS credential_id,
           COALESCE(credential.credential_revision, 0) AS credential_revision,
           (credential.id IS NOT NULL) AS credential_configured,
           server.created_at, server.updated_at
    FROM dream_mcp_servers AS server
    LEFT JOIN dream_mcp_credentials AS credential
      ON credential.server_id = server.id
"""


def _iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


def _server_from_row(row: Mapping[str, Any]) -> McpServerRecord:
    scope = str(row.get("scope_type", row.get("scope", "user")))
    return McpServerRecord(
        id=str(row["id"]),
        user_id=str(row["user_id"]),
        workspace_id=(
            str(row.get("scope_id", row.get("workspace_id")))
            if row.get("scope_id", row.get("workspace_id")) is not None
            else None
        ),
        scope=scope,
        server_key=str(row["server_key"]),
        display_name=str(row["display_name"]),
        transport=McpTransport(str(row["transport"])),
        remote_url=(str(row["remote_url"]) if row.get("remote_url") is not None else None),
        stdio_profile_key=(
            str(row["stdio_profile_key"])
            if row.get("stdio_profile_key") is not None
            else None
        ),
        auth_kind=McpAuthKind(str(row["auth_kind"])),
        enabled=bool(row["enabled"]),
        config_revision=int(row["config_revision"]),
        credential_revision=int(row.get("credential_revision") or 0),
        credential_id=(str(row["credential_id"]) if row.get("credential_id") else None),
        credential_configured=bool(row.get("credential_configured", False)),
        created_at=_iso(row["created_at"]),
        updated_at=_iso(row["updated_at"]),
    )


def _not_found() -> ClaudeMcpError:
    return ClaudeMcpError(
        ClaudeMcpErrorCode.SERVER_NOT_FOUND,
        "Claude MCP server was not found.",
    )


def _revision_conflict() -> ClaudeMcpError:
    return ClaudeMcpError(
        ClaudeMcpErrorCode.SERVER_REVISION_CONFLICT,
        "Claude MCP server changed before this request completed.",
    )


class PostgresMcpRepository:
    """Consume the exact Admin schema through explicit PostgreSQL UoWs."""

    def __init__(
        self,
        pool: ConnectionPool | None = None,
        *,
        unit_of_work_factory: UnitOfWorkFactory | None = None,
        expected_contract_sha256: str = MANAGED_MCP_RESOURCES_CONTRACT_SHA256,
    ) -> None:
        if (pool is None) == (unit_of_work_factory is None):
            raise ValueError("exactly one PostgreSQL dependency is required")
        if expected_contract_sha256 != MANAGED_MCP_RESOURCES_CONTRACT_SHA256:
            # Tests may inject a synthetic exact contract; production callers
            # always use the published constant. Preserve an explicit seam for
            # fake capability rows without allowing an env/runtime override.
            if not isinstance(expected_contract_sha256, str) or len(expected_contract_sha256) != 64:
                raise ValueError("expected contract hash must be SHA-256")
        self._expected_contract_sha256 = expected_contract_sha256
        self._unit_of_work_factory = unit_of_work_factory or (
            lambda **kwargs: PostgresUnitOfWork(pool, **kwargs)  # type: ignore[arg-type]
        )
        self._capability_cache: bool | None = None
        self._capability_lock = threading.Lock()

    def _uow(self, *, read_only: bool = False):
        try:
            return self._unit_of_work_factory(read_only=read_only)
        except TypeError:
            return self._unit_of_work_factory()

    async def capability_available(self) -> bool:
        return await asyncio.to_thread(self.capability_available_sync)

    def capability_available_sync(self) -> bool:
        if self._capability_cache is not None:
            return self._capability_cache
        with self._capability_lock:
            if self._capability_cache is not None:
                return self._capability_cache
            try:
                with self._uow(read_only=True) as uow:
                    row = uow.execute(
                        """/* mcp:capability */
                        SELECT version, contract_sha256
                        FROM drizzle.schema_capabilities
                        WHERE capability = %s
                        """,
                        (MANAGED_MCP_RESOURCES_CAPABILITY,),
                    ).fetchone()
            except Exception:
                available = False
            else:
                available = bool(
                    row
                    and int(row["version"]) == MANAGED_MCP_RESOURCES_VERSION
                    and row["contract_sha256"] == self._expected_contract_sha256
                )
            # Schema capabilities are deployment contracts, not mutable
            # business data.  A process that starts before migration remains
            # fail-closed until restart; normal list/Chat paths then pay no
            # repeated capability query.
            self._capability_cache = available
            return available

    async def list_servers(self, actor_id: str, workspace_id: str | None = None) -> list[McpServerRecord]:
        return await asyncio.to_thread(self.list_servers_sync, actor_id, workspace_id)

    def list_servers_sync(self, actor_id: str, workspace_id: str | None = None) -> list[McpServerRecord]:
        with self._uow(read_only=True) as uow:
            rows = uow.execute(
                _SERVER_SELECT
                + """/* mcp:list */
                WHERE server.user_id = %s::bigint
                  AND (
                    (server.scope_type = 'user' AND server.scope_id IS NULL)
                    OR (server.scope_type = 'workspace' AND server.scope_id = %s)
                  )
                ORDER BY server.updated_at DESC, server.id
                """,
                (actor_id, workspace_id),
            ).fetchall()
        return [_server_from_row(row) for row in rows]

    async def get_server(self, actor_id: str, identifier: str, workspace_id: str | None = None) -> McpServerRecord | None:
        return await asyncio.to_thread(self.get_server_sync, actor_id, identifier, workspace_id)

    def get_server_sync(self, actor_id: str, identifier: str, workspace_id: str | None = None) -> McpServerRecord | None:
        with self._uow(read_only=True) as uow:
            row = uow.execute(
                _SERVER_SELECT
                + """/* mcp:get */
                WHERE (server.id = %s OR server.server_key = %s)
                  AND server.user_id = %s::bigint
                  AND (
                    (server.scope_type = 'user' AND server.scope_id IS NULL)
                    OR (server.scope_type = 'workspace' AND server.scope_id = %s)
                  )
                ORDER BY (server.id = %s) DESC
                LIMIT 1
                """,
                (identifier, identifier, actor_id, workspace_id, identifier),
            ).fetchone()
        return _server_from_row(row) if row else None

    async def create_server(self, actor_id: str, create: McpServerCreate) -> McpServerRecord:
        return await asyncio.to_thread(self.create_server_sync, actor_id, create)

    def create_server_sync(self, actor_id: str, create: McpServerCreate) -> McpServerRecord:
        server_id = str(uuid.uuid4())
        try:
            with self._uow() as uow:
                if create.scope is McpScope.WORKSPACE:
                    owned = uow.execute(
                        """/* mcp:workspace-owner */
                        SELECT 1 AS owned
                        FROM story_workspace_workspaces
                        WHERE id = %s AND owner_id = %s::bigint
                        """,
                        (create.workspace_id, actor_id),
                    ).fetchone()
                    if owned is None:
                        raise ClaudeMcpError(
                            ClaudeMcpErrorCode.SERVER_OWNERSHIP_CONFLICT,
                            "Claude MCP workspace scope is not owned by this actor.",
                        )
                row = uow.execute(
                    """/* mcp:create */
                    INSERT INTO dream_mcp_servers (
                        id, user_id, server_key, display_name, scope_type,
                        scope_id, transport, remote_url, stdio_profile_key,
                        auth_kind, enabled, config_revision
                    ) VALUES (
                        %s, %s::bigint, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1
                    )
                    RETURNING id, user_id, server_key, display_name,
                              scope_type, scope_id, transport, remote_url,
                              stdio_profile_key, auth_kind, enabled,
                              config_revision, NULL::text AS credential_id,
                              0 AS credential_revision,
                              false AS credential_configured,
                              created_at, updated_at
                    """,
                    (
                        server_id,
                        actor_id,
                        create.server_key,
                        create.display_name,
                        create.scope.value,
                        create.workspace_id,
                        create.transport.value,
                        create.remote_url,
                        create.stdio_profile_key,
                        create.auth_kind.value,
                        create.enabled,
                    ),
                ).fetchone()
                uow.commit()
        except UniqueConstraintError:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.SERVER_ALREADY_EXISTS,
                "A Claude MCP server with this scope and key already exists.",
            ) from None
        if row is None:
            raise _not_found()
        return _server_from_row(row)

    async def update_server(self, actor_id: str, server_id: str, patch: McpServerPatch) -> McpServerRecord:
        return await asyncio.to_thread(self.update_server_sync, actor_id, server_id, patch)

    def update_server_sync(self, actor_id: str, server_id: str, patch: McpServerPatch) -> McpServerRecord:
        with self._uow() as uow:
            current = uow.execute(
                _SERVER_SELECT
                + """/* mcp:update-lock */
                WHERE server.id = %s AND server.user_id = %s::bigint
                  AND (server.scope_type = 'user' OR server.scope_id = %s)
                FOR UPDATE OF server
                """,
                (server_id, actor_id, patch.workspace_id),
            ).fetchone()
            if current is None:
                raise _not_found()
            record = _server_from_row(current)
            if record.config_revision != patch.expected_revision:
                raise _revision_conflict()

            transport = patch.transport or record.transport
            remote_url = patch.remote_url if patch.remote_url is not None else record.remote_url
            stdio_profile_key = (
                patch.stdio_profile_key
                if patch.stdio_profile_key is not None
                else record.stdio_profile_key
            )
            if patch.transport is McpTransport.STDIO:
                remote_url = None
            elif patch.transport in {McpTransport.SSE, McpTransport.STREAMABLE_HTTP}:
                stdio_profile_key = None
            try:
                McpServerCreate(
                    server_key=record.server_key,
                    display_name=patch.display_name or record.display_name,
                    transport=transport,
                    auth_kind=patch.auth_kind or record.auth_kind,
                    scope=McpScope(record.scope),
                    workspace_id=record.workspace_id,
                    remote_url=remote_url,
                    stdio_profile_key=stdio_profile_key,
                    enabled=record.enabled if patch.enabled is None else patch.enabled,
                )
            except ValueError:
                raise ClaudeMcpError(
                    ClaudeMcpErrorCode.SERVER_CONFIGURATION_INVALID,
                    "Claude MCP server configuration is invalid.",
                ) from None
            auth_kind = patch.auth_kind or record.auth_kind
            credential_invalidated = record.credential_configured and (
                transport is not record.transport
                or remote_url != record.remote_url
                or stdio_profile_key != record.stdio_profile_key
                or auth_kind is not record.auth_kind
            )
            if credential_invalidated:
                uow.execute(
                    """/* mcp:update-credential-clear */
                    DELETE FROM dream_mcp_credentials
                    WHERE server_id = %s
                    """,
                    (server_id,),
                )
                uow.execute(
                    """/* mcp:update-snapshot-clear */
                    DELETE FROM dream_mcp_discovery_snapshots
                    WHERE server_id = %s
                    """,
                    (server_id,),
                )
            row = uow.execute(
                """/* mcp:update */
                UPDATE dream_mcp_servers
                SET display_name = %s, transport = %s, remote_url = %s,
                    stdio_profile_key = %s, auth_kind = %s, enabled = %s,
                    config_revision = config_revision + 1, updated_at = now()
                WHERE id = %s AND user_id = %s::bigint
                  AND config_revision = %s
                RETURNING id, user_id, server_key, display_name,
                          scope_type, scope_id, transport, remote_url,
                          stdio_profile_key, auth_kind, enabled,
                          config_revision, NULL::text AS credential_id,
                          %s AS credential_revision,
                          %s AS credential_configured,
                          created_at, updated_at
                """,
                (
                    patch.display_name or record.display_name,
                    transport.value,
                    remote_url,
                    stdio_profile_key,
                    auth_kind.value,
                    record.enabled if patch.enabled is None else patch.enabled,
                    server_id,
                    actor_id,
                    patch.expected_revision,
                    0 if credential_invalidated else record.credential_revision,
                    False if credential_invalidated else record.credential_configured,
                ),
            ).fetchone()
            if row is None:
                raise _revision_conflict()
            uow.commit()
        return _server_from_row(row)

    async def delete_server(self, actor_id: str, server_id: str, expected_revision: int | None, workspace_id: str | None = None) -> McpServerRecord:
        return await asyncio.to_thread(self.delete_server_sync, actor_id, server_id, expected_revision, workspace_id)

    def delete_server_sync(self, actor_id: str, server_id: str, expected_revision: int | None, workspace_id: str | None = None) -> McpServerRecord:
        with self._uow() as uow:
            row = uow.execute(
                _SERVER_SELECT
                + """/* mcp:delete-lock */
                WHERE server.id = %s AND server.user_id = %s::bigint
                  AND (server.scope_type = 'user' OR server.scope_id = %s)
                FOR UPDATE OF server
                """,
                (server_id, actor_id, workspace_id),
            ).fetchone()
            if row is None:
                raise _not_found()
            record = _server_from_row(row)
            if expected_revision is not None and record.config_revision != expected_revision:
                raise _revision_conflict()
            deleted = uow.execute(
                """/* mcp:delete */
                DELETE FROM dream_mcp_servers
                WHERE id = %s AND user_id = %s::bigint
                  AND config_revision = %s
                RETURNING id
                """,
                (server_id, actor_id, record.config_revision),
            ).fetchone()
            if deleted is None:
                raise _revision_conflict()
            uow.commit()
        return record

    async def get_credential(self, actor_id: str, server_id: str) -> McpCredentialRecord | None:
        return await asyncio.to_thread(self.get_credential_sync, actor_id, server_id)

    def get_credential_sync(self, actor_id: str, server_id: str) -> McpCredentialRecord | None:
        with self._uow(read_only=True) as uow:
            row = uow.execute(
                """/* mcp:credential-get */
                SELECT credential.id, credential.server_id, server.user_id,
                       credential.kind, credential.ciphertext, credential.iv,
                       credential.tag, credential.fingerprint,
                       credential.key_version, credential.credential_revision,
                       credential.expires_at
                FROM dream_mcp_credentials AS credential
                JOIN dream_mcp_servers AS server ON server.id = credential.server_id
                WHERE credential.server_id = %s AND server.user_id = %s::bigint
                """,
                (server_id, actor_id),
            ).fetchone()
        if row is None:
            return None
        return McpCredentialRecord(
            id=str(row["id"]), server_id=str(row["server_id"]), user_id=str(row["user_id"]),
            kind=str(row["kind"]), ciphertext=str(row["ciphertext"]), iv=str(row["iv"]),
            tag=str(row["tag"]), fingerprint=str(row["fingerprint"]),
            key_version=int(row["key_version"]), credential_revision=int(row["credential_revision"]),
            expires_at=_iso(row["expires_at"]) if row.get("expires_at") is not None else None,
        )

    async def upsert_credential(self, actor_id: str, server_id: str, *, kind: str, envelope: Any, expires_at: datetime | None = None) -> McpCredentialRecord:
        return await asyncio.to_thread(
            self.upsert_credential_sync, actor_id, server_id,
            kind=kind, envelope=envelope, expires_at=expires_at,
        )

    def upsert_credential_sync(self, actor_id: str, server_id: str, *, kind: str, envelope: Any, expires_at: datetime | None = None) -> McpCredentialRecord:
        credential_id = str(uuid.uuid4())
        with self._uow() as uow:
            row = uow.execute(
                """/* mcp:credential-upsert */
                INSERT INTO dream_mcp_credentials (
                    id, server_id, kind, ciphertext, iv, tag, fingerprint,
                    key_version, credential_revision, expires_at
                )
                SELECT %s, server.id, %s, %s, %s, %s, %s, %s, 1, %s
                FROM dream_mcp_servers AS server
                WHERE server.id = %s AND server.user_id = %s::bigint
                ON CONFLICT (server_id) DO UPDATE SET
                    kind = EXCLUDED.kind,
                    ciphertext = EXCLUDED.ciphertext,
                    iv = EXCLUDED.iv,
                    tag = EXCLUDED.tag,
                    fingerprint = EXCLUDED.fingerprint,
                    key_version = EXCLUDED.key_version,
                    credential_revision = dream_mcp_credentials.credential_revision + 1,
                    expires_at = EXCLUDED.expires_at,
                    updated_at = now()
                RETURNING id, server_id, kind, ciphertext, iv, tag,
                          fingerprint, key_version, credential_revision, expires_at
                """,
                (
                    credential_id, kind, envelope.ciphertext, envelope.iv,
                    envelope.tag, envelope.fingerprint, envelope.key_version,
                    expires_at, server_id, actor_id,
                ),
            ).fetchone()
            if row is None:
                raise _not_found()
            uow.execute(
                """/* mcp:credential-snapshot-invalidate */
                DELETE FROM dream_mcp_discovery_snapshots
                WHERE server_id = %s
                """,
                (server_id,),
            )
            uow.commit()
        return McpCredentialRecord(
            id=str(row["id"]), server_id=str(row["server_id"]), user_id=actor_id,
            kind=str(row["kind"]), ciphertext=str(row["ciphertext"]), iv=str(row["iv"]),
            tag=str(row["tag"]), fingerprint=str(row["fingerprint"]),
            key_version=int(row["key_version"]), credential_revision=int(row["credential_revision"]),
            expires_at=_iso(row["expires_at"]) if row.get("expires_at") is not None else None,
        )

    async def delete_credential(self, actor_id: str, server_id: str) -> McpServerRecord:
        return await asyncio.to_thread(self.delete_credential_sync, actor_id, server_id)

    def delete_credential_sync(self, actor_id: str, server_id: str) -> McpServerRecord:
        with self._uow() as uow:
            server_row = uow.execute(
                _SERVER_SELECT
                + """/* mcp:credential-delete-lock */
                WHERE server.id = %s AND server.user_id = %s::bigint
                FOR UPDATE OF server
                """,
                (server_id, actor_id),
            ).fetchone()
            if server_row is None:
                raise _not_found()
            record = _server_from_row(server_row)
            uow.execute(
                """/* mcp:credential-delete */
                DELETE FROM dream_mcp_credentials AS credential
                USING dream_mcp_servers AS server
                WHERE credential.server_id = server.id
                  AND server.id = %s AND server.user_id = %s::bigint
                """,
                (server_id, actor_id),
            )
            uow.execute(
                """/* mcp:credential-snapshot-invalidate */
                DELETE FROM dream_mcp_discovery_snapshots
                WHERE server_id = %s
                """,
                (server_id,),
            )
            uow.commit()
        return McpServerRecord(
            **{
                **record.__dict__,
                "credential_id": None,
                "credential_configured": False,
                "credential_revision": record.credential_revision + 1,
            }
        )

    async def get_discovery_snapshot(self, actor_id: str, server: McpServerRecord) -> Any | None:
        return await asyncio.to_thread(self.get_discovery_snapshot_sync, actor_id, server)

    def get_discovery_snapshot_sync(self, actor_id: str, server: McpServerRecord) -> dict[str, Any] | None:
        with self._uow(read_only=True) as uow:
            row = uow.execute(
                """/* mcp:discovery-get */
                SELECT snapshot.status, snapshot.inventory,
                       snapshot.safe_error_code, snapshot.discovered_at
                FROM dream_mcp_discovery_snapshots AS snapshot
                JOIN dream_mcp_servers AS server ON server.id = snapshot.server_id
                WHERE snapshot.server_id = %s
                  AND snapshot.config_revision = %s
                  AND snapshot.credential_revision IS NOT DISTINCT FROM %s
                  AND snapshot.expires_at > now()
                  AND server.user_id = %s::bigint
                ORDER BY snapshot.discovered_at DESC
                LIMIT 1
                """,
                (
                    server.id,
                    server.config_revision,
                    server.credential_revision or None,
                    actor_id,
                ),
            ).fetchone()
        return dict(row) if row else None

    async def save_discovery_snapshot(self, actor_id: str, server: McpServerRecord, result: Any, *, ttl_seconds: float = 300.0) -> None:
        await asyncio.to_thread(
            self.save_discovery_snapshot_sync,
            actor_id,
            server,
            result,
            ttl_seconds=ttl_seconds,
        )

    def save_discovery_snapshot_sync(self, actor_id: str, server: McpServerRecord, result: Any, *, ttl_seconds: float = 300.0) -> None:
        inventory = result.inventory_dict()
        canonical = json.dumps(inventory, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        import hashlib

        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        with self._uow() as uow:
            owner = uow.execute(
                """/* mcp:discovery-owner */
                SELECT 1 AS owned FROM dream_mcp_servers
                WHERE id = %s AND user_id = %s::bigint
                  AND config_revision = %s
                """,
                (server.id, actor_id, server.config_revision),
            ).fetchone()
            if owner is None:
                raise _not_found()
            uow.execute(
                """/* mcp:discovery-save */
                INSERT INTO dream_mcp_discovery_snapshots (
                    id, server_id, config_revision, credential_revision,
                    status, inventory, inventory_sha256, safe_error_code,
                    discovered_at, expires_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s::jsonb, %s, %s,
                    now(), now() + (%s * interval '1 second')
                )
                ON CONFLICT (server_id, config_revision, credential_revision)
                DO UPDATE SET status = EXCLUDED.status,
                              inventory = EXCLUDED.inventory,
                              inventory_sha256 = EXCLUDED.inventory_sha256,
                              safe_error_code = EXCLUDED.safe_error_code,
                              discovered_at = now(),
                              expires_at = EXCLUDED.expires_at
                """,
                (
                    str(uuid.uuid4()), server.id, server.config_revision,
                    server.credential_revision or None, result.status.value,
                    canonical, digest,
                    result.error.code if result.error else None, ttl_seconds,
                ),
            )
            uow.commit()

    async def find_import_receipt(self, actor_id: str, source_hash: str) -> McpImportReceipt | None:
        return await asyncio.to_thread(self.find_import_receipt_sync, actor_id, source_hash)

    def find_import_receipt_sync(self, actor_id: str, source_hash: str) -> McpImportReceipt | None:
        with self._uow(read_only=True) as uow:
            row = uow.execute(
                """/* mcp:import-receipt-get */
                SELECT state, target_server_id, canonical_config_sha256
                FROM dream_mcp_import_receipts
                WHERE user_id = %s::bigint AND source_item_sha256 = %s
                  AND state IN ('imported', 'noop', 'conflict', 'credential_reauth_required')
                ORDER BY created_at DESC LIMIT 1
                """,
                (actor_id, source_hash),
            ).fetchone()
        return (
            McpImportReceipt(
                state=str(row["state"]),
                target_server_id=(str(row["target_server_id"]) if row.get("target_server_id") else None),
                canonical_config_sha256=str(row["canonical_config_sha256"]),
            )
            if row else None
        )

    async def import_server(self, actor_id: str, create: McpServerCreate, source_hash: str, config_hash: str, *, run_id: str | None = None) -> McpImportReceipt:
        return await asyncio.to_thread(
            self.import_server_sync,
            actor_id,
            create,
            source_hash,
            config_hash,
            run_id=run_id,
        )

    def import_server_sync(self, actor_id: str, create: McpServerCreate, source_hash: str, config_hash: str, *, run_id: str | None = None) -> McpImportReceipt:
        server_id = str(uuid.uuid4())
        receipt_id = str(uuid.uuid4())
        effective_run_id = run_id or str(uuid.uuid4())
        try:
            with self._uow() as uow:
                existing_receipt = uow.execute(
                    """/* mcp:import-lock */
                    SELECT state, target_server_id, canonical_config_sha256
                    FROM dream_mcp_import_receipts
                    WHERE user_id = %s::bigint AND source_item_sha256 = %s
                      AND state IN ('imported', 'noop', 'conflict', 'credential_reauth_required')
                    FOR SHARE
                    """,
                    (actor_id, source_hash),
                ).fetchone()
                if existing_receipt:
                    return McpImportReceipt(
                        state="noop",
                        target_server_id=(
                            str(existing_receipt["target_server_id"])
                            if existing_receipt.get("target_server_id") is not None
                            else None
                        ),
                        canonical_config_sha256=str(existing_receipt["canonical_config_sha256"]),
                    )
                conflict = uow.execute(
                    """/* mcp:import-target-check */
                    SELECT id FROM dream_mcp_servers
                    WHERE user_id = %s::bigint AND scope_type = %s
                      AND scope_id IS NOT DISTINCT FROM %s AND server_key = %s
                    """,
                    (actor_id, create.scope.value, create.workspace_id, create.server_key),
                ).fetchone()
                if conflict:
                    state = "conflict"
                    target_server_id = None
                else:
                    uow.execute(
                        """/* mcp:import-server */
                        INSERT INTO dream_mcp_servers (
                            id, user_id, server_key, display_name, scope_type,
                            scope_id, transport, remote_url, stdio_profile_key,
                            auth_kind, enabled, config_revision
                        ) VALUES (%s, %s::bigint, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
                        """,
                        (
                            server_id, actor_id, create.server_key, create.display_name,
                            create.scope.value, create.workspace_id, create.transport.value,
                            create.remote_url, create.stdio_profile_key,
                            create.auth_kind.value, create.enabled,
                        ),
                    )
                    state = "imported"
                    target_server_id = server_id
                uow.execute(
                    """/* mcp:import-receipt-save */
                    INSERT INTO dream_mcp_import_receipts (
                        id, user_id, source_item_sha256,
                        canonical_config_sha256, target_server_id, state, run_id
                    ) VALUES (%s, %s::bigint, %s, %s, %s, %s, %s)
                    """,
                    (
                        receipt_id, actor_id, source_hash, config_hash,
                        target_server_id, state, effective_run_id,
                    ),
                )
                uow.commit()
        except UniqueConstraintError:
            receipt = self.find_import_receipt_sync(actor_id, source_hash)
            if receipt:
                return McpImportReceipt("noop", receipt.target_server_id, receipt.canonical_config_sha256)
            raise
        return McpImportReceipt(state, target_server_id, config_hash)


__all__ = [
    "ManagedMcpRepository",
    "McpCredentialRecord",
    "McpImportReceipt",
    "McpServerRecord",
    "PostgresMcpRepository",
]
