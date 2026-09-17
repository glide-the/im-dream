# [Sync] 2026-09-17: reuse the validated immutable Admin capability snapshot instead of repeating discovery per domain call.
# [Input] Actual Admin refs DTOs, current request OAuth and source-bound installation metadata.
# [Output] Three exact operations and the original public refs projection after local artifact/CLI checks.
# [Pos] Deck Claude Plugin refs consumer; Admin owns locks/semantic revision/transactions, Dream owns bytes/CLI.
# [Sync] 2026-09-15: replace public refs SQL without paths, actor selectors or copied verification algorithms.
from __future__ import annotations

from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BeforeValidator, Field, field_validator, model_validator

from services.claude_plugin.install_service import PluginInstallService
from .chat_models import ChatStrictDTO, EntityId, validate_timestamp_text
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import OperationCapabilityDTO
from .workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS

InstallationId = Annotated[str, BeforeValidator(lambda value: value.strip() if isinstance(value, str) else value), Field(min_length=1)]
PgOrder = Annotated[int, Field(ge=-2_147_483_648, le=2_147_483_647)]
ArtifactDigest = Annotated[str, Field(pattern=r"^sha256:[a-f0-9]{64}$")]
InstallationStatus = Literal["installing", "ready", "error", "uninstalled"]
InstallationSource = Literal["claude-official", "marketplace", "github", "platform-builtin"]


class PluginInstallationDTO(ChatStrictDTO):
    id: EntityId
    requested_package_spec: str
    package_name: EntityId
    marketplace: EntityId
    resolved_version: EntityId
    artifact_digest: ArtifactDigest
    claude_cli_version: str
    source_type: InstallationSource
    status: InstallationStatus
    manifest_json: str | None
    component_inventory_json: str
    compatibility_json: str


class PluginRefDTO(ChatStrictDTO):
    deck_id: EntityId
    plugin_installation_id: EntityId
    package_spec: str
    resolved_version: EntityId
    artifact_digest: ArtifactDigest
    enabled: bool
    order_index: PgOrder
    created_at: str
    updated_at: str
    installation_status: InstallationStatus
    source_type: InstallationSource
    claude_cli_version: str
    manifest_json: str | None
    component_inventory_json: str
    _timestamps = field_validator("created_at", "updated_at")(validate_timestamp_text)

    def public_projection(self):
        return {**self.model_dump(), "enabled": int(self.enabled)}


class PluginRefEvidenceDTO(ChatStrictDTO):
    plugin_installation_id: InstallationId
    package_name: EntityId
    marketplace: EntityId
    resolved_version: EntityId
    artifact_digest: ArtifactDigest
    compatibility_json: str
    enabled: bool
    order_index: PgOrder


class RefsListInputDTO(ChatStrictDTO):
    deck_id: EntityId


class RefsPrepareInputDTO(RefsListInputDTO):
    installation_ids: list[InstallationId]

    @field_validator("installation_ids")
    @classmethod
    def require_unique_ids(cls, values):
        if len(set(values)) != len(values):
            raise ValueError("Duplicate plugin installation")
        return values


class RefsReplaceInputDTO(RefsListInputDTO):
    refs: list[PluginRefEvidenceDTO]

    @field_validator("refs")
    @classmethod
    def require_unique_refs(cls, values):
        if len({item.plugin_installation_id for item in values}) != len(values):
            raise ValueError("Duplicate plugin installation")
        return values


class RefsOutputDTO(RefsListInputDTO):
    refs: list[PluginRefDTO]

    def public_projection(self):
        return {"deck_id": self.deck_id, "refs": [item.public_projection() for item in self.refs]}


class RefsReplacedDTO(RefsOutputDTO):
    changed: bool


class RefsPreparedDTO(ChatStrictDTO):
    installations: list[PluginInstallationDTO]


class PublicPluginRefDTO(ChatStrictDTO):
    plugin_installation_id: InstallationId
    enabled: bool = True
    order_index: PgOrder | None = None


class PublicRefsRequestDTO(ChatStrictDTO):
    refs: list[PublicPluginRefDTO] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_unique_refs(self):
        if len({item.plugin_installation_id for item in self.refs}) != len(self.refs):
            raise ValueError("Duplicate plugin installation")
        return self


class RefsSelectionDTO(PublicRefsRequestDTO):
    deck_id: EntityId


LIST_REFS = DomainOperation(OperationCapabilityDTO(name="deck-plugin-refs.list", kind="read", user_scope="dream:read", background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256="99a280621dacd34eb5552d73516e17003b8d79a873d4e62a8bb795a5b779c6d1"), RefsListInputDTO, RefsOutputDTO)
PREPARE_REFS = DomainOperation(OperationCapabilityDTO(name="deck-plugin-refs.prepare", kind="read", user_scope="dream:read", background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256="6d5f10aa39de3b2d45129c6dd731269b4f0c394397d3b4723323e2d4be60a90f"), RefsPrepareInputDTO, RefsPreparedDTO)
REPLACE_REFS = DomainOperation(OperationCapabilityDTO(name="deck-plugin-refs.replace", kind="write", user_scope="dream:write", background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256="5556a6190c578521560c0eecabee005d4428fe4d69fe75ef8eed17fa37aa6bf3"), RefsReplaceInputDTO, RefsReplacedDTO)
DECK_REFS_OPERATIONS = (LIST_REFS, PREPARE_REFS, REPLACE_REFS)


class AdminDeckRefsData:
    def __init__(self, client: AdminDataClient):
        self._client = client

    def _execute(self, operation, input_dto, request_id, access_token):
        capabilities = self._client.capabilities_snapshot(request_id)
        schemas = {item.capability: item for item in capabilities.schema_capabilities}
        if len(schemas) != len(capabilities.schema_capabilities) or any(schemas.get(item.capability) != item for item in WORKFLOW_SCHEMA_REQUIREMENTS):
            raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)
        result = self._client.execute(operation, input_dto, request_id, access_token=access_token)
        if operation is PREPARE_REFS:
            ids = [item.id for item in result.installations]
            if len(set(ids)) != len(ids) or set(ids) != set(input_dto.installation_ids) or any(item.status != "ready" for item in result.installations):
                raise invalid_response(request_id)
        elif result.deck_id != input_dto.deck_id or any(item.deck_id != input_dto.deck_id for item in result.refs):
            raise invalid_response(request_id, write=operation is REPLACE_REFS)
        return result

    def list(self, input_dto: RefsListInputDTO, request_id: str, *, access_token: str):
        return self._execute(LIST_REFS, input_dto, request_id, access_token).public_projection()

    def replace(self, selection: RefsSelectionDTO, request_id: str, *, access_token: str):
        prepared = self._execute(PREPARE_REFS, RefsPrepareInputDTO(deck_id=selection.deck_id,
            installation_ids=[item.plugin_installation_id for item in selection.refs]), str(uuid4()), access_token)
        by_id = {item.id: item for item in prepared.installations}
        refs = []
        for position, selected in enumerate(selection.refs):
            record = by_id[selected.plugin_installation_id].model_dump()
            if not PluginInstallService.verify_installation_artifact(record):
                raise AdminDataError("CLAUDE_PLUGIN_INTEGRITY_FAILED", 409, request_id)
            if not PluginInstallService.check_cli_compatibility(record):
                raise AdminDataError("CLAUDE_PLUGIN_INCOMPATIBLE", 409, request_id)
            refs.append(PluginRefEvidenceDTO(plugin_installation_id=selected.plugin_installation_id,
                package_name=record["package_name"], marketplace=record["marketplace"], resolved_version=record["resolved_version"],
                artifact_digest=record["artifact_digest"], compatibility_json=record["compatibility_json"], enabled=selected.enabled,
                order_index=selected.order_index if selected.order_index is not None else position))
        result = self._execute(REPLACE_REFS, RefsReplaceInputDTO(deck_id=selection.deck_id, refs=refs), request_id, access_token)
        if {item.plugin_installation_id for item in result.refs} != {item.plugin_installation_id for item in refs} or len(result.refs) != len(refs):
            raise invalid_response(request_id, write=True)
        return result.public_projection()
