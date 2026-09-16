# [Input] Registry175-182 catalog, current OAuth bearer and closed Claude Plugin lifecycle DTOs.
# [Output] Strict Pydantic projections plus original-request recovery for Admin-owned persistence.
# [Pos] Dream wire boundary; Admin owns Marketplace queries, locks, Drizzle writes and transactions.
# [Sync] 2026-09-16: consume shared Claude Plugin data operations without SQL or actor selectors.
"""Typed Admin consumer for shared Claude Plugin catalog and install lifecycle."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator, model_validator

from .chat_models import ChatStrictDTO, PresentFieldsDTO
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import CommittedReceiptDTO, OperationCapabilityDTO, SchemaCapabilityDTO
from .workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS


Identifier = Annotated[str, Field(min_length=1, max_length=255)]
PackageSpec = Annotated[str, Field(min_length=3, max_length=300)]
Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
CommitSha = Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
BoundedPath = Annotated[str, Field(min_length=1, max_length=4096)]
SourceType = Literal[
    "claude-official", "marketplace", "github", "platform-builtin"
]


class ClaudePluginEmptyInputDTO(ChatStrictDTO):
    pass


class ClaudePluginOperationsListInputDTO(ChatStrictDTO):
    limit: int = Field(ge=1, le=100)


class ClaudePluginOperationReadInputDTO(ChatStrictDTO):
    operation_id: Identifier


class ClaudePluginInstallationReadInputDTO(ChatStrictDTO):
    installation_id: Identifier


class ClaudePluginOperationDTO(ChatStrictDTO):
    id: Identifier
    operation_kind: Literal["install", "uninstall", "validate", "revalidate"]
    requested_package_spec: PackageSpec
    marketplace_entry_id: Identifier | None
    status: Literal["queued", "running", "ready", "error"]
    phase: Literal[
        "queued",
        "starting",
        "cli-install",
        "cli-validate",
        "verify",
        "import",
        "ready",
        "error",
    ]
    progress: int = Field(ge=0, le=100)
    message: str | None
    executable: str | None
    argv_json: str | None
    cwd: str | None
    cli_version: str | None
    exit_code: int | None
    evidence_path: str | None
    installation_id: Identifier | None
    error_code: Identifier | None
    error_summary: str | None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None

    @field_validator("created_at", "updated_at", "finished_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Operation timestamp requires timezone")
        return value


class ClaudePluginInstallationDTO(ChatStrictDTO):
    id: Identifier
    requested_package_spec: PackageSpec
    marketplace_entry_id: Identifier | None
    package_name: Identifier
    marketplace: Identifier
    requested_version: str | None
    resolved_version: str = Field(min_length=1, max_length=255)
    source_type: SourceType
    artifact_digest: Digest
    artifact_path: BoundedPath
    claude_cli_version: str = Field(min_length=1, max_length=255)
    cli_git_commit_sha: str | None
    manifest_json: str | None
    component_inventory_json: str
    compatibility_json: str
    status: Literal["installing", "ready", "error", "uninstalled"]
    operation_id: Identifier
    error_code: Identifier | None
    error_summary: str | None
    file_count: int = Field(ge=0)
    created_at: datetime
    updated_at: datetime
    installed_at: datetime | None

    @field_validator("created_at", "updated_at", "installed_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Installation timestamp requires timezone")
        return value


class ClaudePluginInstallationListItemDTO(ClaudePluginInstallationDTO):
    deck_ref_count: int = Field(ge=0)


class ClaudePluginDeckRefDTO(ChatStrictDTO):
    deck_id: Identifier
    enabled: bool
    order_index: int


class ClaudePluginInstallationDetailDTO(ClaudePluginInstallationDTO):
    deck_refs: list[ClaudePluginDeckRefDTO]


class ClaudePluginInstallationsListDTO(ChatStrictDTO):
    installations: list[ClaudePluginInstallationListItemDTO]
    permissions: dict[Literal["can_manage_shared_plugins"], Literal[True]]


class ClaudePluginOperationsListDTO(ChatStrictDTO):
    operations: list[ClaudePluginOperationDTO]


class ClaudePluginMarketplaceSourceDTO(ChatStrictDTO):
    entry_id: Identifier
    package_spec: PackageSpec
    package_name: Identifier
    marketplace_name: Identifier
    remote_url: str = Field(min_length=1, max_length=2048)
    requested_ref: str | None = Field(default=None, max_length=255)
    approved_commit_sha: CommitSha
    marketplace_manifest_sha256: Sha256
    plugin_manifest_sha256: Sha256 | None
    approved_plugin_digest: Digest
    compatibility: dict[str, Any]


class ClaudePluginMarketplaceRevisionDTO(ChatStrictDTO):
    id: Identifier
    commit_sha: CommitSha
    marketplace_manifest_sha256: Sha256
    plugin_manifest_sha256: Sha256 | None
    plugin_digest: Digest
    requested_ref: str | None = Field(default=None, max_length=255)


class ClaudePluginMarketplaceIdentityDTO(ChatStrictDTO):
    id: Identifier
    display_name: str = Field(min_length=1, max_length=500)
    remote_url: str = Field(min_length=1, max_length=2048)


class ClaudePluginMarketplaceInstallationDTO(ChatStrictDTO):
    id: Identifier
    status: Literal["ready"]
    resolved_version: str = Field(min_length=1, max_length=255)


class ClaudePluginMarketplaceEntryDTO(ChatStrictDTO):
    id: Identifier
    package_name: Identifier
    marketplace_name: Identifier
    package_spec: PackageSpec
    display_name: str = Field(min_length=1, max_length=500)
    description: str | None
    version: str | None
    homepage: str | None
    component_inventory: dict[str, Any]
    compatibility: dict[str, Any]
    revision: ClaudePluginMarketplaceRevisionDTO
    marketplace: ClaudePluginMarketplaceIdentityDTO
    installation: ClaudePluginMarketplaceInstallationDTO | None


class ClaudePluginMarketplaceListDTO(ChatStrictDTO):
    entries: list[ClaudePluginMarketplaceEntryDTO]
    scope: Literal["platform-global"]
    permissions: dict[Literal["can_install_shared_plugins"], Literal[True]]


class ClaudePluginInstallPrepareInputDTO(PresentFieldsDTO):
    source_kind: Literal["package", "marketplace_entry"]
    package_spec: PackageSpec | None = None
    source_type: Literal[
        "claude-official", "marketplace", "platform-builtin"
    ] | None = None
    marketplace_entry_id: Identifier | None = None

    @model_validator(mode="after")
    def require_exact_source_fields(self):
        required = (
            {"source_kind", "package_spec", "source_type"}
            if self.source_kind == "package"
            else {"source_kind", "marketplace_entry_id"}
        )
        if self.model_fields_set != required:
            raise ValueError("Install source fields do not match source_kind")
        return self


class ClaudePluginInstallPlanDTO(ChatStrictDTO):
    accepted: Literal[True]
    operation_id: Identifier
    package_spec: PackageSpec
    marketplace_entry_id: Identifier | None
    requested_source_type: Literal[
        "claude-official", "marketplace", "platform-builtin"
    ] | None
    marketplace_source: ClaudePluginMarketplaceSourceDTO | None


class ClaudePluginInstallationEvidenceDTO(ChatStrictDTO):
    package_name: Identifier
    marketplace: Identifier
    requested_version: str | None
    resolved_version: str = Field(min_length=1, max_length=255)
    source_type: Literal["claude-official", "marketplace", "platform-builtin"]
    artifact_digest: Digest
    artifact_path: BoundedPath
    claude_cli_version: str = Field(min_length=1, max_length=255)
    cli_git_commit_sha: str | None = Field(default=None, max_length=255)
    manifest_json: str | None = Field(default=None, max_length=1_000_000)
    component_inventory_json: str = Field(max_length=1_000_000)
    compatibility_json: str = Field(max_length=1_000_000)
    file_count: int = Field(ge=0, le=9_007_199_254_740_991)


class ClaudePluginExecutionEvidenceDTO(ChatStrictDTO):
    executable: str = Field(min_length=1, max_length=4096)
    argv: list[Annotated[str, Field(max_length=4096)]] = Field(max_length=128)
    cwd: BoundedPath
    cli_version: str = Field(min_length=1, max_length=255)
    exit_code: int


class ClaudePluginInstallReportInputDTO(PresentFieldsDTO):
    event: Literal["begin", "progress", "fail", "complete"]
    operation_id: Identifier
    phase: Literal["cli-install", "cli-validate", "verify", "import"] | None = None
    progress: Literal[20, 55, 80] | None = None
    message: Annotated[str, Field(min_length=1, max_length=1000)] | None = None
    error_code: Identifier | None = None
    error_summary: Annotated[str, Field(min_length=1, max_length=2000)] | None = None
    evidence_path: BoundedPath | None = None
    installation: ClaudePluginInstallationEvidenceDTO | None = None
    execution: ClaudePluginExecutionEvidenceDTO | None = None

    @model_validator(mode="after")
    def require_exact_event_fields(self):
        common = {"event", "operation_id"}
        required = {
            "begin": set(),
            "progress": {"phase", "progress", "message"},
            "fail": {"error_code", "error_summary", "evidence_path"},
            "complete": {"installation", "execution", "evidence_path"},
        }[self.event]
        if self.model_fields_set != common | required:
            raise ValueError("Install report fields do not match event")
        if self.event == "progress" and (
            (self.phase in {"cli-install", "cli-validate"} and self.progress != 20)
            or (self.phase == "verify" and self.progress != 55)
            or (self.phase == "import" and self.progress != 80)
        ):
            raise ValueError("Install progress does not match phase")
        return self


def _operation(name, kind, input_dto, output_dto, hash_value):
    return DomainOperation(
        OperationCapabilityDTO(
            name=name,
            kind=kind,
            user_scope="dream:read" if kind == "read" else "dream:write",
            background_scope=None,
            input_schema_version=1,
            output_schema_version=1,
            contract_sha256=hash_value,
        ),
        input_dto,
        output_dto,
    )


LIST_CLAUDE_PLUGIN_INSTALLATIONS = _operation(
    "claude-plugin.installations.list", "read", ClaudePluginEmptyInputDTO,
    ClaudePluginInstallationsListDTO,
    "9795d0b9465050b0d9032be3b227a32a70a6a4fca50742e5921006d5b408deeb",
)
LIST_CLAUDE_PLUGIN_MARKETPLACE = _operation(
    "claude-plugin.marketplace.list", "read", ClaudePluginEmptyInputDTO,
    ClaudePluginMarketplaceListDTO,
    "b7c05e5e460f36b5f8d8d03d3c595f405d58bf7f862f10e316b6e4b152cdd8bf",
)
PREPARE_CLAUDE_PLUGIN_INSTALL = _operation(
    "claude-plugin.install.prepare", "write", ClaudePluginInstallPrepareInputDTO,
    ClaudePluginInstallPlanDTO,
    "02e01bdd5681e2f62eda62ea65e879f693fc72ebbf0f299fca47998e88601fad",
)
LIST_CLAUDE_PLUGIN_OPERATIONS = _operation(
    "claude-plugin.operations.list", "read", ClaudePluginOperationsListInputDTO,
    ClaudePluginOperationsListDTO,
    "3a27f57269a9fb4da02526aaed41655850c53c264bcca49e669c76e6c37663ae",
)
READ_CLAUDE_PLUGIN_OPERATION = _operation(
    "claude-plugin.operation.read", "read", ClaudePluginOperationReadInputDTO,
    ClaudePluginOperationDTO,
    "edf3e075cb100ebe56ccd86703f80d08e9c7be952bca48e585484a29516b14b5",
)
READ_CLAUDE_PLUGIN_INSTALLATION = _operation(
    "claude-plugin.installation.read", "read", ClaudePluginInstallationReadInputDTO,
    ClaudePluginInstallationDetailDTO,
    "690ae2a07b92258c11e36843cac1024f248aa8204410e39a4a2895bc07a8d620",
)
REPORT_CLAUDE_PLUGIN_INSTALL = _operation(
    "claude-plugin.install.report", "write", ClaudePluginInstallReportInputDTO,
    ClaudePluginOperationDTO,
    "661e28352ec56257282f914091a6b33bc435d1dcdd4c1c7cf44482f2c16b7504",
)
UNINSTALL_CLAUDE_PLUGIN_INSTALLATION = _operation(
    "claude-plugin.installation.uninstall", "write",
    ClaudePluginInstallationReadInputDTO, ClaudePluginInstallationDTO,
    "904b5e2796ac17378facb4b3e8d2afb9e4e9cd72dc79a57dbd0cd74b3947d2a3",
)
CLAUDE_PLUGIN_OPERATIONS = (
    LIST_CLAUDE_PLUGIN_INSTALLATIONS,
    LIST_CLAUDE_PLUGIN_MARKETPLACE,
    PREPARE_CLAUDE_PLUGIN_INSTALL,
    LIST_CLAUDE_PLUGIN_OPERATIONS,
    READ_CLAUDE_PLUGIN_OPERATION,
    READ_CLAUDE_PLUGIN_INSTALLATION,
    REPORT_CLAUDE_PLUGIN_INSTALL,
    UNINSTALL_CLAUDE_PLUGIN_INSTALLATION,
)
CLAUDE_PLUGIN_SCHEMA_REQUIREMENTS = (
    *WORKFLOW_SCHEMA_REQUIREMENTS,
    SchemaCapabilityDTO(
        capability="dream.claude-plugin.remote-marketplace.v1",
        version=1,
        contract_sha256=(
            "d215cb2764f656ab32e364a4900b3aac"
            "73fca60c77ef4c9f3a914fd192a8c314"
        ),
    ),
)


def require_claude_plugin_capabilities(client: AdminDataClient, request_id: str) -> None:
    capabilities = client.capabilities(request_id)
    schemas = {item.capability: item for item in capabilities.schema_capabilities}
    if len(schemas) != len(capabilities.schema_capabilities) or any(
        schemas.get(item.capability) != item
        for item in CLAUDE_PLUGIN_SCHEMA_REQUIREMENTS
    ):
        raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)


class AdminClaudePluginData:
    def __init__(self, client: AdminDataClient) -> None:
        self._client = client

    def _execute(self, operation, input_dto, request_id: str, access_token: str):
        require_claude_plugin_capabilities(self._client, request_id)
        result = self._client.execute(
            operation, input_dto, request_id, access_token=access_token
        )
        if operation is PREPARE_CLAUDE_PLUGIN_INSTALL:
            if input_dto.source_kind == "marketplace_entry" and (
                result.marketplace_entry_id != input_dto.marketplace_entry_id
            ):
                raise invalid_response(request_id, write=True)
        elif operation is REPORT_CLAUDE_PLUGIN_INSTALL and (
            result.id != input_dto.operation_id
        ):
            raise invalid_response(request_id, write=True)
        elif operation is UNINSTALL_CLAUDE_PLUGIN_INSTALLATION and (
            result.id != input_dto.installation_id
        ):
            raise invalid_response(request_id, write=True)
        return result

    def _write(self, operation, input_dto, request_id: str, access_token: str):
        try:
            return self._execute(operation, input_dto, request_id, access_token)
        except AdminDataError as error:
            if not error.outcome_unknown:
                raise
        try:
            receipt = self._client.receipt(
                operation, request_id, access_token=access_token
            )
        except AdminDataError as error:
            raise AdminDataError(
                error.code,
                error.status_code,
                request_id,
                True,
                error.details,
            ) from None
        if not isinstance(receipt, CommittedReceiptDTO) or not isinstance(
            receipt.result, operation.output_dto
        ):
            raise AdminDataError("ADMIN_WRITE_RESULT_UNKNOWN", 503, request_id, True)
        result = receipt.result
        if operation is PREPARE_CLAUDE_PLUGIN_INSTALL:
            if input_dto.source_kind == "marketplace_entry" and (
                result.marketplace_entry_id != input_dto.marketplace_entry_id
            ):
                raise invalid_response(request_id, write=True)
        elif operation is REPORT_CLAUDE_PLUGIN_INSTALL and result.id != input_dto.operation_id:
            raise invalid_response(request_id, write=True)
        elif operation is UNINSTALL_CLAUDE_PLUGIN_INSTALLATION and result.id != input_dto.installation_id:
            raise invalid_response(request_id, write=True)
        return result

    def list_installations(self, input_dto, request_id: str, *, access_token: str):
        return self._execute(
            LIST_CLAUDE_PLUGIN_INSTALLATIONS, input_dto, request_id, access_token
        )

    def list_marketplace(self, input_dto, request_id: str, *, access_token: str):
        return self._execute(
            LIST_CLAUDE_PLUGIN_MARKETPLACE, input_dto, request_id, access_token
        )

    def prepare(self, input_dto, request_id: str, *, access_token: str):
        return self._write(
            PREPARE_CLAUDE_PLUGIN_INSTALL, input_dto, request_id, access_token
        )

    def list_operations(self, input_dto, request_id: str, *, access_token: str):
        return self._execute(
            LIST_CLAUDE_PLUGIN_OPERATIONS, input_dto, request_id, access_token
        )

    def read_operation(self, input_dto, request_id: str, *, access_token: str):
        return self._execute(
            READ_CLAUDE_PLUGIN_OPERATION, input_dto, request_id, access_token
        )

    def read_installation(self, input_dto, request_id: str, *, access_token: str):
        return self._execute(
            READ_CLAUDE_PLUGIN_INSTALLATION, input_dto, request_id, access_token
        )

    def report(self, input_dto, request_id: str, *, access_token: str):
        return self._write(
            REPORT_CLAUDE_PLUGIN_INSTALL, input_dto, request_id, access_token
        )

    def uninstall(self, input_dto, request_id: str, *, access_token: str):
        return self._write(
            UNINSTALL_CLAUDE_PLUGIN_INSTALLATION,
            input_dto,
            request_id,
            access_token,
        )
