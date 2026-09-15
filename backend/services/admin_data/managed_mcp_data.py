# [Input] Admin Registry134-147 descriptors and actor-free managed-MCP domain values.
# [Output] Strict Pydantic DTOs and exact operation/schema capability contracts.
# [Pos] Dream wire boundary; Admin owns Drizzle ORM, permissions, locks and transactions.
# [Sync] 2026-09-16: pin the complete managed-MCP data API without SQL or database credentials.
"""Typed Admin consumer contracts for managed MCP persistence."""

from __future__ import annotations

from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import Field, JsonValue, field_validator, model_validator

from .chat_models import ChatStrictDTO, validate_timestamp_text
from .client import DomainOperation
from .models import OperationCapabilityDTO, SchemaCapabilityDTO


SAFE_INTEGER_MAX = 9_007_199_254_740_991
EntityId = Annotated[str, Field(min_length=1, max_length=255)]
ServerId = Annotated[
    str,
    Field(
        pattern=(
            r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-"
            r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
        )
    ),
]
RunId = Annotated[str, Field(pattern=r"^run_[0-9a-f]{32}$")]
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
ServerKey = Annotated[
    str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
]
StdioProfileKey = Annotated[
    str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
]
Transport = Literal["streamable_http", "sse", "stdio"]
AuthKind = Literal["none", "oauth"]
Scope = Literal["user", "workspace"]
CredentialKind = Literal["oauth", "headers", "stdio_env"]
InventoryStatus = Literal["complete", "failed", "cancelled"]


def validate_remote_url_text(value: str | None) -> str | None:
    """Accept only the closed remote endpoint shape published by Admin."""

    if value is None:
        return None
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Managed MCP remote URL is invalid")
    return value


class ManagedMcpAuthorityDTO(ChatStrictDTO):
    thread_id: EntityId
    workflow_run_id: RunId | None


class ManagedMcpInputDTO(ChatStrictDTO):
    authority: ManagedMcpAuthorityDTO | None


class ManagedMcpScopedInputDTO(ManagedMcpInputDTO):
    workspace_id: EntityId | None


class ManagedMcpServerDTO(ChatStrictDTO):
    id: ServerId
    user_id: Annotated[str, Field(pattern=r"^[1-9][0-9]*$")]
    workspace_id: EntityId | None
    scope: Scope
    server_key: ServerKey
    display_name: Annotated[str, Field(min_length=1, max_length=200)]
    transport: Transport
    remote_url: str | None
    stdio_profile_key: StdioProfileKey | None
    auth_kind: AuthKind
    enabled: bool
    config_revision: Annotated[int, Field(ge=1, le=SAFE_INTEGER_MAX)]
    credential_revision: Annotated[int, Field(ge=0, le=SAFE_INTEGER_MAX)]
    credential_id: ServerId | None
    credential_configured: bool
    created_at: str
    updated_at: str

    _timestamps = field_validator("created_at", "updated_at")(
        validate_timestamp_text
    )
    _remote_url = field_validator("remote_url")(validate_remote_url_text)

    @model_validator(mode="after")
    def validate_stored_shape(self):
        if (self.scope == "user") != (self.workspace_id is None):
            raise ValueError("Managed MCP Server scope is inconsistent")
        if ((self.transport == "stdio") != (self.stdio_profile_key is not None)
            or (self.transport == "stdio") == (self.remote_url is not None)):
            raise ValueError("Managed MCP Server endpoint is inconsistent")
        if self.credential_configured:
            if self.credential_id is None or self.credential_revision < 1:
                raise ValueError("Managed MCP credential state is inconsistent")
        elif self.credential_id is not None:
            raise ValueError("Managed MCP credential state is inconsistent")
        return self


class ManagedMcpServerCreateDTO(ManagedMcpScopedInputDTO):
    server_key: ServerKey
    display_name: Annotated[str, Field(min_length=1, max_length=200)]
    transport: Transport
    auth_kind: AuthKind
    scope: Scope
    remote_url: str | None
    stdio_profile_key: StdioProfileKey | None
    enabled: bool

    @field_validator("display_name")
    @classmethod
    def strip_display_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Managed MCP display name must not be blank")
        return value

    _remote_url = field_validator("remote_url")(validate_remote_url_text)

    @model_validator(mode="after")
    def validate_shape(self):
        if (self.scope == "user") != (self.workspace_id is None):
            raise ValueError("Managed MCP scope is inconsistent")
        if ((self.transport == "stdio") != (self.stdio_profile_key is not None)
            or (self.transport == "stdio") == (self.remote_url is not None)):
            raise ValueError("Managed MCP endpoint is inconsistent")
        return self


class ManagedMcpServerListOutputDTO(ChatStrictDTO):
    servers: list[ManagedMcpServerDTO]


class ManagedMcpServerGetInputDTO(ManagedMcpScopedInputDTO):
    identifier: EntityId


class ManagedMcpServerGetOutputDTO(ChatStrictDTO):
    server: ManagedMcpServerDTO | None


class ManagedMcpServerOutputDTO(ChatStrictDTO):
    server: ManagedMcpServerDTO


class ManagedMcpServerPatchInputDTO(ManagedMcpInputDTO):
    server_id: ServerId
    expected_revision: Annotated[int, Field(ge=1, le=SAFE_INTEGER_MAX)]
    display_name: Annotated[str, Field(min_length=1, max_length=200)] | None
    transport: Transport | None
    auth_kind: AuthKind | None
    remote_url: str | None
    stdio_profile_key: StdioProfileKey | None
    enabled: bool | None

    _remote_url = field_validator("remote_url")(validate_remote_url_text)


class ManagedMcpServerDeleteInputDTO(ManagedMcpInputDTO):
    server_id: ServerId
    expected_revision: Annotated[int, Field(ge=1, le=SAFE_INTEGER_MAX)] | None


class ManagedMcpAppPreferenceDTO(ChatStrictDTO):
    enabled: bool
    low_risk_tool_calls: bool
    ui_messages: bool


class ManagedMcpAppSettingsDTO(ChatStrictDTO):
    desired: ManagedMcpAppPreferenceDTO
    revision: Annotated[int, Field(ge=1, le=SAFE_INTEGER_MAX)]


class ManagedMcpAppSettingsGetInputDTO(ManagedMcpScopedInputDTO):
    server_id: ServerId


class ManagedMcpAppSettingsGetOutputDTO(ChatStrictDTO):
    settings: ManagedMcpAppSettingsDTO | None


class ManagedMcpAppSettingsUpdateInputDTO(ManagedMcpScopedInputDTO):
    server_id: ServerId
    expected_revision: Annotated[int, Field(ge=1, le=SAFE_INTEGER_MAX)]
    desired: ManagedMcpAppPreferenceDTO


class ManagedMcpAppSettingsOutputDTO(ChatStrictDTO):
    settings: ManagedMcpAppSettingsDTO


class ManagedMcpCredentialDTO(ChatStrictDTO):
    id: ServerId
    server_id: ServerId
    user_id: Annotated[str, Field(pattern=r"^[1-9][0-9]*$")]
    kind: CredentialKind
    ciphertext: Annotated[str, Field(min_length=1, repr=False)]
    iv: Annotated[str, Field(min_length=1, repr=False)]
    tag: Annotated[str, Field(min_length=1, repr=False)]
    fingerprint: Annotated[str, Field(pattern=r"^[0-9a-f]{16}$")]
    key_version: Annotated[int, Field(ge=1, le=SAFE_INTEGER_MAX)]
    credential_revision: Annotated[int, Field(ge=1, le=SAFE_INTEGER_MAX)]
    expires_at: str | None

    @field_validator("expires_at")
    @classmethod
    def validate_expiry(cls, value: str | None) -> str | None:
        return None if value is None else validate_timestamp_text(value)


class ManagedMcpCredentialGetInputDTO(ManagedMcpInputDTO):
    server_id: ServerId


class ManagedMcpCredentialGetOutputDTO(ChatStrictDTO):
    credential: ManagedMcpCredentialDTO | None


class ManagedMcpCredentialEnvelopeDTO(ChatStrictDTO):
    ciphertext: Annotated[str, Field(min_length=1, repr=False)]
    iv: Annotated[str, Field(min_length=1, repr=False)]
    tag: Annotated[str, Field(min_length=1, repr=False)]
    fingerprint: Annotated[str, Field(pattern=r"^[0-9a-f]{16}$")]
    key_version: Annotated[int, Field(ge=1, le=SAFE_INTEGER_MAX)]


class ManagedMcpCredentialUpsertInputDTO(ManagedMcpInputDTO):
    server_id: ServerId
    kind: CredentialKind
    envelope: ManagedMcpCredentialEnvelopeDTO
    expires_at: str | None

    _expiry = field_validator("expires_at")(
        ManagedMcpCredentialDTO.validate_expiry.__func__
    )


class ManagedMcpCredentialOutputDTO(ChatStrictDTO):
    credential: ManagedMcpCredentialDTO


class ManagedMcpDiscoveryGetInputDTO(ManagedMcpInputDTO):
    server_id: ServerId
    config_revision: Annotated[int, Field(ge=1, le=SAFE_INTEGER_MAX)]
    credential_revision: Annotated[int, Field(ge=0, le=SAFE_INTEGER_MAX)]


class ManagedMcpDiscoverySnapshotDTO(ChatStrictDTO):
    status: InventoryStatus
    inventory: dict[str, JsonValue]
    safe_error_code: Annotated[str, Field(min_length=1, max_length=255)] | None
    discovered_at: str

    _timestamp = field_validator("discovered_at")(validate_timestamp_text)


class ManagedMcpDiscoveryGetOutputDTO(ChatStrictDTO):
    snapshot: ManagedMcpDiscoverySnapshotDTO | None


class ManagedMcpDiscoverySaveInputDTO(ManagedMcpInputDTO):
    server_id: ServerId
    config_revision: Annotated[int, Field(ge=1, le=SAFE_INTEGER_MAX)]
    credential_revision: Annotated[int, Field(ge=0, le=SAFE_INTEGER_MAX)]
    status: InventoryStatus
    inventory: dict[str, JsonValue]
    safe_error_code: Annotated[str, Field(min_length=1, max_length=255)] | None
    ttl_seconds: Annotated[float, Field(gt=0)]


class ManagedMcpDiscoverySaveOutputDTO(ChatStrictDTO):
    saved: Literal[True]


class ManagedMcpImportReceiptDTO(ChatStrictDTO):
    state: Literal["imported", "noop", "conflict", "credential_reauth_required"]
    target_server_id: ServerId | None
    canonical_config_sha256: Sha256


class ManagedMcpImportReceiptGetInputDTO(ManagedMcpInputDTO):
    source_hash: Sha256


class ManagedMcpImportReceiptGetOutputDTO(ChatStrictDTO):
    receipt: ManagedMcpImportReceiptDTO | None


class ManagedMcpImportInputDTO(ManagedMcpServerCreateDTO):
    source_hash: Sha256
    config_hash: Sha256
    run_id: EntityId | None


class ManagedMcpImportOutputDTO(ChatStrictDTO):
    receipt: ManagedMcpImportReceiptDTO


def _operation(name: str, kind: Literal["read", "write"], digest: str, input_dto, output_dto):
    return DomainOperation(
        OperationCapabilityDTO(
            name=name,
            kind=kind,
            user_scope="dream:read" if kind == "read" else "dream:write",
            background_scope=None,
            input_schema_version=1,
            output_schema_version=1,
            contract_sha256=digest,
        ),
        input_dto,
        output_dto,
    )


LIST_MANAGED_MCP_SERVERS = _operation("managed-mcp.servers.list", "read", "4107ec96394ddf15594f97686e9909c7bb73d8375752d17cf2fe1d646d7c1c7d", ManagedMcpScopedInputDTO, ManagedMcpServerListOutputDTO)
GET_MANAGED_MCP_SERVER = _operation("managed-mcp.server.get", "read", "90b2442c617365a96d32ab6f620b791be02ce5e5f9cf89b1bc44cf34ef549c8b", ManagedMcpServerGetInputDTO, ManagedMcpServerGetOutputDTO)
CREATE_MANAGED_MCP_SERVER = _operation("managed-mcp.server.create", "write", "675a2e2328d8962538dae02dcf3a8825e534093963872471ccbda3cb25f7933e", ManagedMcpServerCreateDTO, ManagedMcpServerOutputDTO)
UPDATE_MANAGED_MCP_SERVER = _operation("managed-mcp.server.update", "write", "6e8bcb85845d5855b9b53bc85af530dfeb020bc11b3c8149dbf740daba2ec4fe", ManagedMcpServerPatchInputDTO, ManagedMcpServerOutputDTO)
DELETE_MANAGED_MCP_SERVER = _operation("managed-mcp.server.delete", "write", "d1a908a4a3105e4bac0c0f3dfbaf24cfefb26cf0047f604f0dddef6dab9dfccc", ManagedMcpServerDeleteInputDTO, ManagedMcpServerOutputDTO)
GET_MANAGED_MCP_APP_SETTINGS = _operation("managed-mcp.app-settings.get", "read", "9b5776c2876968dc5099ace2f7d023de70732055e06b8a1a28b9e2f2401eaa15", ManagedMcpAppSettingsGetInputDTO, ManagedMcpAppSettingsGetOutputDTO)
UPDATE_MANAGED_MCP_APP_SETTINGS = _operation("managed-mcp.app-settings.update", "write", "c6e9dc6babb3293a6cfa61550ad3cca11ec2fc67ac4a4db341332b9b8de90b76", ManagedMcpAppSettingsUpdateInputDTO, ManagedMcpAppSettingsOutputDTO)
GET_MANAGED_MCP_CREDENTIAL = _operation("managed-mcp.credential.get", "read", "779377d499e39b5bf2f962198a1872c69fc624593a3a339de031c6c0f7299813", ManagedMcpCredentialGetInputDTO, ManagedMcpCredentialGetOutputDTO)
UPSERT_MANAGED_MCP_CREDENTIAL = _operation("managed-mcp.credential.upsert", "write", "168bf580c075e2510af530ef7d27f2c0800340029d94859ad4bc39e1480e5845", ManagedMcpCredentialUpsertInputDTO, ManagedMcpCredentialOutputDTO)
DELETE_MANAGED_MCP_CREDENTIAL = _operation("managed-mcp.credential.delete", "write", "4da8b362dd86cc76da2199e51135fadb2009ef2c24453c42588f7dc6a450d61c", ManagedMcpCredentialGetInputDTO, ManagedMcpServerOutputDTO)
GET_MANAGED_MCP_DISCOVERY = _operation("managed-mcp.discovery.get", "read", "e809a7e272996115ee0fd7c96d4b929024a094b81a570b226ce960a135dbcdcc", ManagedMcpDiscoveryGetInputDTO, ManagedMcpDiscoveryGetOutputDTO)
SAVE_MANAGED_MCP_DISCOVERY = _operation("managed-mcp.discovery.save", "write", "a00378206f45390f121c6dacda23e7f552df82b84a95c9fef94b4be5487d7688", ManagedMcpDiscoverySaveInputDTO, ManagedMcpDiscoverySaveOutputDTO)
GET_MANAGED_MCP_IMPORT_RECEIPT = _operation("managed-mcp.import-receipt.get", "read", "27dcc16169f770c185a0e12e093e57dd10174e5bb87c009d1c9585210d1b3819", ManagedMcpImportReceiptGetInputDTO, ManagedMcpImportReceiptGetOutputDTO)
IMPORT_MANAGED_MCP_SERVER = _operation("managed-mcp.import", "write", "261f10ff87d3da4fb99feb2d8f9792cac3441380ff8966cfd2b6dac7d7578e9a", ManagedMcpImportInputDTO, ManagedMcpImportOutputDTO)

MANAGED_MCP_OPERATIONS = (
    LIST_MANAGED_MCP_SERVERS,
    GET_MANAGED_MCP_SERVER,
    CREATE_MANAGED_MCP_SERVER,
    UPDATE_MANAGED_MCP_SERVER,
    DELETE_MANAGED_MCP_SERVER,
    GET_MANAGED_MCP_APP_SETTINGS,
    UPDATE_MANAGED_MCP_APP_SETTINGS,
    GET_MANAGED_MCP_CREDENTIAL,
    UPSERT_MANAGED_MCP_CREDENTIAL,
    DELETE_MANAGED_MCP_CREDENTIAL,
    GET_MANAGED_MCP_DISCOVERY,
    SAVE_MANAGED_MCP_DISCOVERY,
    GET_MANAGED_MCP_IMPORT_RECEIPT,
    IMPORT_MANAGED_MCP_SERVER,
)

MANAGED_MCP_SCHEMA_REQUIREMENTS = (
    SchemaCapabilityDTO(
        capability="dream.managed-mcp-resources.v1",
        version=1,
        contract_sha256="746dfcb1343c485bee9fb7cc3fa363424db4a66ad31cd6824ed2024be049614a",
    ),
    SchemaCapabilityDTO(
        capability="dream.mcp-app-connection-settings.v1",
        version=1,
        contract_sha256="c8a1daebd20db54890ca31bf154faad4bd6f2714c609dba413acca88e2139202",
    ),
)


__all__ = [
    "MANAGED_MCP_OPERATIONS",
    "MANAGED_MCP_SCHEMA_REQUIREMENTS",
    "ManagedMcpAuthorityDTO",
    "ManagedMcpAppPreferenceDTO",
    "ManagedMcpAppSettingsGetInputDTO",
    "ManagedMcpAppSettingsUpdateInputDTO",
    "ManagedMcpCredentialEnvelopeDTO",
    "ManagedMcpCredentialGetInputDTO",
    "ManagedMcpCredentialUpsertInputDTO",
    "ManagedMcpDiscoveryGetInputDTO",
    "ManagedMcpDiscoverySaveInputDTO",
    "ManagedMcpImportInputDTO",
    "ManagedMcpImportReceiptGetInputDTO",
    "ManagedMcpScopedInputDTO",
    "ManagedMcpServerCreateDTO",
    "ManagedMcpServerDeleteInputDTO",
    "ManagedMcpServerGetInputDTO",
    "ManagedMcpServerPatchInputDTO",
]
