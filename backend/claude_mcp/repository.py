"""Actor-scoped Admin DTO repository for managed MCP persistence.

[Input] Shared AdminDataClient plus one explicit OAuth or Runtime authorization context.
[Output] Existing managed-MCP records through Registry134-147 business operations.
[Pos] Sole Dream persistence adapter for managed MCP; contains no SQL, ORM, pool, DDL, or fallback.
[Sync] 2026-09-16: replace Dream PostgreSQL access with strict Admin DTO operations and receipt recovery.
"""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterator, Protocol
from uuid import uuid4

from services.admin_data.client import AdminDataClient, DomainOperation
from services.admin_data.errors import AdminDataError
from services.admin_data.managed_mcp_data import (
    CREATE_MANAGED_MCP_SERVER,
    DELETE_MANAGED_MCP_CREDENTIAL,
    DELETE_MANAGED_MCP_SERVER,
    GET_MANAGED_MCP_APP_SETTINGS,
    GET_MANAGED_MCP_CREDENTIAL,
    GET_MANAGED_MCP_DISCOVERY,
    GET_MANAGED_MCP_IMPORT_RECEIPT,
    GET_MANAGED_MCP_SERVER,
    IMPORT_MANAGED_MCP_SERVER,
    LIST_MANAGED_MCP_SERVERS,
    MANAGED_MCP_OPERATIONS,
    MANAGED_MCP_SCHEMA_REQUIREMENTS,
    SAVE_MANAGED_MCP_DISCOVERY,
    UPDATE_MANAGED_MCP_APP_SETTINGS,
    UPDATE_MANAGED_MCP_SERVER,
    UPSERT_MANAGED_MCP_CREDENTIAL,
    ManagedMcpAppPreferenceDTO,
    ManagedMcpAppSettingsGetInputDTO,
    ManagedMcpAppSettingsUpdateInputDTO,
    ManagedMcpAuthorityDTO,
    ManagedMcpCredentialEnvelopeDTO,
    ManagedMcpCredentialGetInputDTO,
    ManagedMcpCredentialUpsertInputDTO,
    ManagedMcpDiscoveryGetInputDTO,
    ManagedMcpDiscoverySaveInputDTO,
    ManagedMcpImportInputDTO,
    ManagedMcpImportReceiptGetInputDTO,
    ManagedMcpScopedInputDTO,
    ManagedMcpServerCreateDTO,
    ManagedMcpServerDeleteInputDTO,
    ManagedMcpServerDTO,
    ManagedMcpServerGetInputDTO,
    ManagedMcpServerPatchInputDTO,
)
from services.admin_data.models import CommittedReceiptDTO

from .contracts import (
    ClaudeMcpError,
    ClaudeMcpErrorCode,
    McpAppPreferenceState,
    McpAppSettingsPatch,
    McpAuthKind,
    McpServerCreate,
    McpServerPatch,
    McpTransport,
)


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
    ciphertext: str = field(repr=False)
    iv: str = field(repr=False)
    tag: str = field(repr=False)
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


@dataclass(frozen=True)
class McpAppSettingsRecord:
    desired: McpAppPreferenceState
    revision: int


@dataclass(frozen=True, repr=False)
class McpDataAuthorization:
    """One server-derived actor credential; never serialized as actor input."""

    actor_id: str
    access_token: str = field(repr=False)
    thread_id: str | None = None
    workflow_run_id: str | None = None

    def __post_init__(self) -> None:
        if (
            not self.actor_id.isdecimal()
            or int(self.actor_id) < 1
            or not self.access_token
            or any(
                character.isspace()
                or ord(character) < 32
                or ord(character) == 127
                for character in self.access_token
            )
            or (self.thread_id is None and self.workflow_run_id is not None)
        ):
            raise ValueError("Invalid managed MCP authorization")
        if self.thread_id is not None:
            ManagedMcpAuthorityDTO(
                thread_id=self.thread_id,
                workflow_run_id=self.workflow_run_id,
            )

    @property
    def authority(self) -> ManagedMcpAuthorityDTO | None:
        if self.thread_id is None:
            return None
        return ManagedMcpAuthorityDTO(
            thread_id=self.thread_id,
            workflow_run_id=self.workflow_run_id,
        )


class ManagedMcpRepository(Protocol):
    async def capability_available(self) -> bool: ...
    async def app_settings_capability_available(self) -> bool: ...
    async def list_servers(self, actor_id: str, workspace_id: str | None = None) -> list[McpServerRecord]: ...
    async def get_server(self, actor_id: str, identifier: str, workspace_id: str | None = None) -> McpServerRecord | None: ...
    async def create_server(self, actor_id: str, create: McpServerCreate) -> McpServerRecord: ...
    async def update_server(self, actor_id: str, server_id: str, patch: McpServerPatch) -> McpServerRecord: ...
    async def delete_server(self, actor_id: str, server_id: str, expected_revision: int | None, workspace_id: str | None = None) -> McpServerRecord: ...
    async def get_app_settings(self, actor_id: str, server_id: str, workspace_id: str | None = None) -> McpAppSettingsRecord | None: ...
    async def update_app_settings(self, actor_id: str, server_id: str, patch: McpAppSettingsPatch) -> McpAppSettingsRecord: ...
    async def get_credential(self, actor_id: str, server_id: str) -> McpCredentialRecord | None: ...
    async def upsert_credential(self, actor_id: str, server_id: str, *, kind: str, envelope: Any, expires_at: datetime | None = None) -> McpCredentialRecord: ...
    async def delete_credential(self, actor_id: str, server_id: str) -> McpServerRecord: ...
    async def get_discovery_snapshot(self, actor_id: str, server: McpServerRecord) -> dict[str, Any] | None: ...
    async def save_discovery_snapshot(self, actor_id: str, server: McpServerRecord, result: Any, *, ttl_seconds: float = 300.0) -> None: ...
    async def find_import_receipt(self, actor_id: str, source_hash: str) -> McpImportReceipt | None: ...
    async def import_server(self, actor_id: str, create: McpServerCreate, source_hash: str, config_hash: str, *, run_id: str | None = None) -> McpImportReceipt: ...


_ADMIN_ERROR_CODES = {
    "ADMIN_CAPABILITY_UNAVAILABLE": ClaudeMcpErrorCode.SCHEMA_CAPABILITY_MISSING,
    "ADMIN_CONFIGURATION_INVALID": ClaudeMcpErrorCode.SCHEMA_CAPABILITY_UNAVAILABLE,
    "ADMIN_OPERATION_CONTRACT_INVALID": ClaudeMcpErrorCode.SCHEMA_CAPABILITY_UNAVAILABLE,
    "ADMIN_RESPONSE_INVALID": ClaudeMcpErrorCode.SCHEMA_CAPABILITY_UNAVAILABLE,
    "ADMIN_TIMEOUT": ClaudeMcpErrorCode.SCHEMA_CAPABILITY_UNAVAILABLE,
    "ADMIN_UNAVAILABLE": ClaudeMcpErrorCode.SCHEMA_CAPABILITY_UNAVAILABLE,
    "ADMIN_WRITE_RESULT_UNKNOWN": ClaudeMcpErrorCode.SCHEMA_CAPABILITY_UNAVAILABLE,
    "DREAM_DELEGATION_ENTITY_DENIED": ClaudeMcpErrorCode.IDENTITY_UNAVAILABLE,
    "DREAM_SCOPE_REQUIRED": ClaudeMcpErrorCode.IDENTITY_UNAVAILABLE,
    "INSUFFICIENT_SCOPE": ClaudeMcpErrorCode.IDENTITY_UNAVAILABLE,
    "INVALID_ACCESS_TOKEN": ClaudeMcpErrorCode.IDENTITY_UNAVAILABLE,
    "OPERATION_REQUEST_CONFLICT": ClaudeMcpErrorCode.OPERATION_CONFLICT,
}


def _domain_error(error: AdminDataError) -> ClaudeMcpError:
    try:
        code = ClaudeMcpErrorCode(error.code)
    except ValueError:
        code = _ADMIN_ERROR_CODES.get(
            error.code,
            ClaudeMcpErrorCode.SCHEMA_CAPABILITY_UNAVAILABLE,
        )
    return ClaudeMcpError(code, "Managed MCP Admin data operation failed safely.")


def _server_record(value: ManagedMcpServerDTO) -> McpServerRecord:
    return McpServerRecord(
        id=value.id,
        user_id=value.user_id,
        workspace_id=value.workspace_id,
        scope=value.scope,
        server_key=value.server_key,
        display_name=value.display_name,
        transport=McpTransport(value.transport),
        remote_url=value.remote_url,
        stdio_profile_key=value.stdio_profile_key,
        auth_kind=McpAuthKind(value.auth_kind),
        enabled=value.enabled,
        config_revision=value.config_revision,
        credential_revision=value.credential_revision,
        credential_id=value.credential_id,
        credential_configured=value.credential_configured,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )


class AdminManagedMcpRepository:
    """Adapt Registry134-147 into the existing managed-MCP domain protocol."""

    def __init__(self, client: AdminDataClient) -> None:
        self._client = client
        self._authorization: ContextVar[McpDataAuthorization | None] = ContextVar(
            f"managed_mcp_authorization_{id(self)}",
            default=None,
        )

    @property
    def admin_client(self) -> AdminDataClient:
        """Expose identity only for process-singleton composition checks."""

        return self._client

    @contextmanager
    def authorize(
        self, authorization: McpDataAuthorization
    ) -> Iterator["AdminManagedMcpRepository"]:
        if type(authorization) is not McpDataAuthorization:
            raise TypeError("Managed MCP authorization must be exact")
        token = self._authorization.set(authorization)
        try:
            yield self
        finally:
            self._authorization.reset(token)

    def _current(self, actor_id: str | None = None) -> McpDataAuthorization:
        authorization = self._authorization.get()
        if authorization is None or (
            actor_id is not None and authorization.actor_id != str(actor_id)
        ):
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.IDENTITY_UNAVAILABLE,
                "Managed MCP authorization is unavailable.",
            )
        return authorization

    def _execute_sync(self, operation: DomainOperation, input_dto: Any) -> Any:
        authorization = self._current()
        request_id = str(uuid4())
        try:
            return self._client.execute(
                operation,
                input_dto,
                request_id,
                access_token=authorization.access_token,
            )
        except AdminDataError as error:
            if not error.outcome_unknown or operation.capability.kind != "write":
                raise _domain_error(error) from None
        try:
            receipt = self._client.receipt(
                operation,
                request_id,
                access_token=authorization.access_token,
            )
        except AdminDataError as receipt_error:
            raise _domain_error(receipt_error) from None
        if not isinstance(receipt, CommittedReceiptDTO):
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.SCHEMA_CAPABILITY_UNAVAILABLE,
                "Managed MCP write result is unknown.",
            )
        return receipt.result

    async def _execute(self, operation: DomainOperation, input_dto: Any) -> Any:
        return await asyncio.to_thread(self._execute_sync, operation, input_dto)

    async def capability_available(self) -> bool:
        self._current()
        return self._client.supports(
            MANAGED_MCP_OPERATIONS,
            MANAGED_MCP_SCHEMA_REQUIREMENTS,
        )

    async def app_settings_capability_available(self) -> bool:
        return await self.capability_available()

    async def list_servers(
        self, actor_id: str, workspace_id: str | None = None
    ) -> list[McpServerRecord]:
        authorization = self._current(actor_id)
        result = await self._execute(
            LIST_MANAGED_MCP_SERVERS,
            ManagedMcpScopedInputDTO(
                authority=authorization.authority,
                workspace_id=workspace_id,
            ),
        )
        return [_server_record(value) for value in result.servers]

    async def get_server(
        self,
        actor_id: str,
        identifier: str,
        workspace_id: str | None = None,
    ) -> McpServerRecord | None:
        authorization = self._current(actor_id)
        result = await self._execute(
            GET_MANAGED_MCP_SERVER,
            ManagedMcpServerGetInputDTO(
                authority=authorization.authority,
                workspace_id=workspace_id,
                identifier=identifier,
            ),
        )
        return None if result.server is None else _server_record(result.server)

    async def create_server(
        self, actor_id: str, create: McpServerCreate
    ) -> McpServerRecord:
        authorization = self._current(actor_id)
        result = await self._execute(
            CREATE_MANAGED_MCP_SERVER,
            ManagedMcpServerCreateDTO(
                authority=authorization.authority,
                workspace_id=create.workspace_id,
                server_key=create.server_key,
                display_name=create.display_name,
                transport=create.transport.value,
                auth_kind=create.auth_kind.value,
                scope=create.scope.value,
                remote_url=create.remote_url,
                stdio_profile_key=create.stdio_profile_key,
                enabled=create.enabled,
            ),
        )
        return _server_record(result.server)

    async def update_server(
        self, actor_id: str, server_id: str, patch: McpServerPatch
    ) -> McpServerRecord:
        authorization = self._current(actor_id)
        result = await self._execute(
            UPDATE_MANAGED_MCP_SERVER,
            ManagedMcpServerPatchInputDTO(
                authority=authorization.authority,
                server_id=server_id,
                expected_revision=patch.expected_revision,
                display_name=patch.display_name,
                transport=patch.transport.value if patch.transport else None,
                auth_kind=patch.auth_kind.value if patch.auth_kind else None,
                remote_url=patch.remote_url,
                stdio_profile_key=patch.stdio_profile_key,
                enabled=patch.enabled,
            ),
        )
        return _server_record(result.server)

    async def delete_server(
        self,
        actor_id: str,
        server_id: str,
        expected_revision: int | None,
        workspace_id: str | None = None,
    ) -> McpServerRecord:
        del workspace_id
        authorization = self._current(actor_id)
        result = await self._execute(
            DELETE_MANAGED_MCP_SERVER,
            ManagedMcpServerDeleteInputDTO(
                authority=authorization.authority,
                server_id=server_id,
                expected_revision=expected_revision,
            ),
        )
        return _server_record(result.server)

    async def get_app_settings(
        self,
        actor_id: str,
        server_id: str,
        workspace_id: str | None = None,
    ) -> McpAppSettingsRecord | None:
        authorization = self._current(actor_id)
        result = await self._execute(
            GET_MANAGED_MCP_APP_SETTINGS,
            ManagedMcpAppSettingsGetInputDTO(
                authority=authorization.authority,
                workspace_id=workspace_id,
                server_id=server_id,
            ),
        )
        if result.settings is None:
            return None
        return McpAppSettingsRecord(
            desired=McpAppPreferenceState(**result.settings.desired.model_dump()),
            revision=result.settings.revision,
        )

    async def update_app_settings(
        self, actor_id: str, server_id: str, patch: McpAppSettingsPatch
    ) -> McpAppSettingsRecord:
        authorization = self._current(actor_id)
        result = await self._execute(
            UPDATE_MANAGED_MCP_APP_SETTINGS,
            ManagedMcpAppSettingsUpdateInputDTO(
                authority=authorization.authority,
                workspace_id=patch.workspace_id,
                server_id=server_id,
                expected_revision=patch.expected_revision,
                desired=ManagedMcpAppPreferenceDTO(**patch.desired.__dict__),
            ),
        )
        return McpAppSettingsRecord(
            desired=McpAppPreferenceState(**result.settings.desired.model_dump()),
            revision=result.settings.revision,
        )

    async def get_credential(
        self, actor_id: str, server_id: str
    ) -> McpCredentialRecord | None:
        authorization = self._current(actor_id)
        result = await self._execute(
            GET_MANAGED_MCP_CREDENTIAL,
            ManagedMcpCredentialGetInputDTO(
                authority=authorization.authority,
                server_id=server_id,
            ),
        )
        if result.credential is None:
            return None
        return McpCredentialRecord(**result.credential.model_dump())

    async def upsert_credential(
        self,
        actor_id: str,
        server_id: str,
        *,
        kind: str,
        envelope: Any,
        expires_at: datetime | None = None,
    ) -> McpCredentialRecord:
        authorization = self._current(actor_id)
        expiry = None
        if expires_at is not None:
            if expires_at.tzinfo is None or expires_at.utcoffset() is None:
                raise ValueError("Managed MCP credential expiry must have a timezone")
            expiry = expires_at.astimezone(timezone.utc).isoformat()
        result = await self._execute(
            UPSERT_MANAGED_MCP_CREDENTIAL,
            ManagedMcpCredentialUpsertInputDTO(
                authority=authorization.authority,
                server_id=server_id,
                kind=kind,
                envelope=ManagedMcpCredentialEnvelopeDTO(
                    ciphertext=envelope.ciphertext,
                    iv=envelope.iv,
                    tag=envelope.tag,
                    fingerprint=envelope.fingerprint,
                    key_version=envelope.key_version,
                ),
                expires_at=expiry,
            ),
        )
        return McpCredentialRecord(**result.credential.model_dump())

    async def delete_credential(
        self, actor_id: str, server_id: str
    ) -> McpServerRecord:
        authorization = self._current(actor_id)
        result = await self._execute(
            DELETE_MANAGED_MCP_CREDENTIAL,
            ManagedMcpCredentialGetInputDTO(
                authority=authorization.authority,
                server_id=server_id,
            ),
        )
        return _server_record(result.server)

    async def get_discovery_snapshot(
        self, actor_id: str, server: McpServerRecord
    ) -> dict[str, Any] | None:
        authorization = self._current(actor_id)
        result = await self._execute(
            GET_MANAGED_MCP_DISCOVERY,
            ManagedMcpDiscoveryGetInputDTO(
                authority=authorization.authority,
                server_id=server.id,
                config_revision=server.config_revision,
                credential_revision=server.credential_revision,
            ),
        )
        return (
            None
            if result.snapshot is None
            else result.snapshot.model_dump(mode="json")
        )

    async def save_discovery_snapshot(
        self,
        actor_id: str,
        server: McpServerRecord,
        result: Any,
        *,
        ttl_seconds: float = 300.0,
    ) -> None:
        authorization = self._current(actor_id)
        await self._execute(
            SAVE_MANAGED_MCP_DISCOVERY,
            ManagedMcpDiscoverySaveInputDTO(
                authority=authorization.authority,
                server_id=server.id,
                config_revision=server.config_revision,
                credential_revision=server.credential_revision,
                status=result.status.value,
                inventory=result.inventory_dict(),
                safe_error_code=result.error.code if result.error else None,
                ttl_seconds=ttl_seconds,
            ),
        )

    async def find_import_receipt(
        self, actor_id: str, source_hash: str
    ) -> McpImportReceipt | None:
        authorization = self._current(actor_id)
        result = await self._execute(
            GET_MANAGED_MCP_IMPORT_RECEIPT,
            ManagedMcpImportReceiptGetInputDTO(
                authority=authorization.authority,
                source_hash=source_hash,
            ),
        )
        return (
            None
            if result.receipt is None
            else McpImportReceipt(**result.receipt.model_dump())
        )

    async def import_server(
        self,
        actor_id: str,
        create: McpServerCreate,
        source_hash: str,
        config_hash: str,
        *,
        run_id: str | None = None,
    ) -> McpImportReceipt:
        authorization = self._current(actor_id)
        result = await self._execute(
            IMPORT_MANAGED_MCP_SERVER,
            ManagedMcpImportInputDTO(
                authority=authorization.authority,
                workspace_id=create.workspace_id,
                server_key=create.server_key,
                display_name=create.display_name,
                transport=create.transport.value,
                auth_kind=create.auth_kind.value,
                scope=create.scope.value,
                remote_url=create.remote_url,
                stdio_profile_key=create.stdio_profile_key,
                enabled=create.enabled,
                source_hash=source_hash,
                config_hash=config_hash,
                run_id=run_id,
            ),
        )
        return McpImportReceipt(**result.receipt.model_dump())


__all__ = [
    "AdminManagedMcpRepository",
    "ManagedMcpRepository",
    "McpAppSettingsRecord",
    "McpCredentialRecord",
    "McpDataAuthorization",
    "McpImportReceipt",
    "McpServerRecord",
]
