# [Input] Admin Registry148-168 descriptors and actor-free Notion connector domain values.
# [Output] Strict Pydantic DTOs, exact operation capabilities and bounded unknown-write recovery.
# [Pos] Dream wire boundary; Admin owns Drizzle ORM, permissions, row locks and transactions.
# [Sync] 2026-09-16: pin the complete Notion connector data API without SQL or database credentials.
"""Typed Admin consumer contracts for Notion connector persistence."""

from __future__ import annotations

from threading import RLock
from typing import Annotated, Literal

from pydantic import Field, JsonValue, field_validator, model_serializer

from .chat_models import ChatStrictDTO, validate_timestamp_text
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import (
    CommittedReceiptDTO,
    OperationCapabilityDTO,
    SchemaCapabilityDTO,
)


EntityId = Annotated[str, Field(min_length=1, max_length=255)]
ConnectorId = Annotated[
    str,
    Field(
        pattern=(
            r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-"
            r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
        )
    ),
]
CanonicalUserId = Annotated[str, Field(pattern=r"^[1-9][0-9]*$")]
RunId = Annotated[str, Field(pattern=r"^run_[0-9a-f]{32}$")]
JsonObject = dict[str, JsonValue]
ResourceType = Literal["notion_database", "notion_page"]


class NotionAuthorityDTO(ChatStrictDTO):
    thread_id: EntityId
    workflow_run_id: RunId | None


class NotionUserInputDTO(ChatStrictDTO):
    authority: NotionAuthorityDTO | None


class NotionResourceDTO(ChatStrictDTO):
    id: ConnectorId
    connector_id: ConnectorId
    resource_type: ResourceType
    external_id: EntityId
    title: Annotated[str, Field(max_length=2000)]
    metadata: JsonObject
    sync_status: Annotated[str, Field(min_length=1, max_length=64)]
    created_at: str
    updated_at: str

    _timestamps = field_validator("created_at", "updated_at")(
        validate_timestamp_text
    )


class NotionConnectorDTO(ChatStrictDTO):
    id: ConnectorId
    user_id: CanonicalUserId
    name: Annotated[str, Field(min_length=1, max_length=200)]
    platform: Annotated[str, Field(min_length=1, max_length=64)]
    auth_status: Annotated[str, Field(min_length=1, max_length=64)]
    config: JsonObject
    current_snapshot_version: EntityId | None
    current_source_revision: EntityId | None
    current_sync_cursor: EntityId | None
    last_synced_at: str | None
    created_at: str
    updated_at: str
    sources: list[NotionResourceDTO]

    _timestamps = field_validator("created_at", "updated_at")(
        validate_timestamp_text
    )

    @field_validator("last_synced_at")
    @classmethod
    def validate_last_synced_at(cls, value: str | None) -> str | None:
        return None if value is None else validate_timestamp_text(value)


class NotionConnectorOutputDTO(ChatStrictDTO):
    connector: NotionConnectorDTO


class NotionConnectorNullableOutputDTO(ChatStrictDTO):
    connector: NotionConnectorDTO | None


class NotionConnectorListOutputDTO(ChatStrictDTO):
    connectors: list[NotionConnectorDTO]


class NotionConnectorCreateInputDTO(NotionUserInputDTO):
    name: Annotated[str, Field(min_length=1, max_length=200)]
    platform: Annotated[str, Field(min_length=1, max_length=64)]
    config: JsonObject


class NotionConnectorListInputDTO(NotionUserInputDTO):
    pass


class NotionConnectorGetInputDTO(NotionUserInputDTO):
    connector_id: ConnectorId


class NotionConnectorActiveInputDTO(NotionUserInputDTO):
    pass


class NotionConnectorPatchDTO(ChatStrictDTO):
    name: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    platform: Annotated[str, Field(min_length=1, max_length=64)] | None = None
    auth_status: Annotated[str, Field(min_length=1, max_length=64)] | None = None
    config_patch: JsonObject | None = None
    current_snapshot_version: EntityId | None = None
    current_source_revision: EntityId | None = None
    current_sync_cursor: EntityId | None = None
    last_synced_at: str | None = None

    @field_validator("last_synced_at")
    @classmethod
    def validate_last_synced_at(cls, value: str | None) -> str | None:
        return None if value is None else validate_timestamp_text(value)

    @model_serializer
    def serialize_present_fields(self) -> dict[str, JsonValue]:
        if not self.model_fields_set:
            raise ValueError("At least one connector field is required")
        return {
            field: getattr(self, field)
            for field in self.model_fields_set
        }


class NotionConnectorPatchInputDTO(NotionUserInputDTO):
    connector_id: ConnectorId
    patch: NotionConnectorPatchDTO


class NotionConnectorDeleteInputDTO(NotionUserInputDTO):
    connector_id: ConnectorId


class NotionConnectorDeleteOutputDTO(ChatStrictDTO):
    deleted: bool


class NotionAuthStateSaveInputDTO(NotionUserInputDTO):
    connector_id: ConnectorId
    auth_status: Annotated[str, Field(min_length=1, max_length=64)]
    config_patch: JsonObject


class NotionResourceSelectionDTO(ChatStrictDTO):
    external_id: EntityId
    title: Annotated[str, Field(max_length=2000)]
    metadata: JsonObject


class NotionResourcesReplaceInputDTO(NotionUserInputDTO):
    connector_id: ConnectorId
    databases: Annotated[list[NotionResourceSelectionDTO], Field(max_length=10_000)]
    pages: Annotated[list[NotionResourceSelectionDTO], Field(max_length=10_000)]


class NotionResourcesListInputDTO(NotionUserInputDTO):
    connector_id: ConnectorId


class NotionResourcesListOutputDTO(ChatStrictDTO):
    resources: list[NotionResourceDTO]


class NotionResourceDeleteInputDTO(NotionUserInputDTO):
    connector_id: ConnectorId
    resource_id: ConnectorId


class NotionResourceDeleteOutputDTO(ChatStrictDTO):
    deleted: bool


class NotionSnapshotMetadataDTO(ChatStrictDTO):
    workspace_id: EntityId
    resource_connector_id: ConnectorId
    snapshot_version: EntityId
    source_revision: EntityId
    sync_cursor: EntityId
    fetched_at: str
    state: Literal["snapshot_ready"]

    _timestamp = field_validator("fetched_at")(validate_timestamp_text)


class NotionSnapshotSaveInputDTO(NotionUserInputDTO):
    connector_id: ConnectorId
    workspace_id: EntityId
    snapshot: JsonObject
    synced_resources: Annotated[list["NotionSyncedResourceDTO"], Field(max_length=20_000)]


class NotionSyncedResourceDTO(ChatStrictDTO):
    resource_type: ResourceType
    external_id: EntityId


class NotionSnapshotOutputDTO(ChatStrictDTO):
    snapshot: JsonObject


class NotionSnapshotNullableOutputDTO(ChatStrictDTO):
    snapshot: JsonObject | None


class NotionSnapshotCurrentInputDTO(NotionUserInputDTO):
    connector_id: ConnectorId
    workspace_id: EntityId


class NotionSnapshotGetInputDTO(NotionUserInputDTO):
    connector_id: ConnectorId
    snapshot_version: EntityId


class NotionSnapshotListInputDTO(NotionUserInputDTO):
    connector_id: ConnectorId


class NotionSnapshotRecordDTO(ChatStrictDTO):
    id: ConnectorId
    connector_id: ConnectorId
    snapshot_version: EntityId
    source_revision: EntityId
    sync_cursor: EntityId
    fetched_at: str
    state: Literal["snapshot_ready"]
    created_at: str
    updated_at: str
    snapshot: JsonObject

    _timestamps = field_validator("fetched_at", "created_at", "updated_at")(
        validate_timestamp_text
    )


class NotionSnapshotListOutputDTO(ChatStrictDTO):
    snapshots: list[NotionSnapshotRecordDTO]


class NotionThreadAttachInputDTO(NotionUserInputDTO):
    connector_id: ConnectorId
    thread_id: EntityId


class NotionThreadResolveInputDTO(NotionUserInputDTO):
    thread_id: EntityId


class NotionSyncCandidatesInputDTO(ChatStrictDTO):
    pass


class NotionSyncCandidatesOutputDTO(ChatStrictDTO):
    connectors: list[NotionConnectorDTO]


class NotionSyncConnectorInputDTO(ChatStrictDTO):
    connector_id: ConnectorId


class NotionSyncConnectorPatchInputDTO(ChatStrictDTO):
    connector_id: ConnectorId
    patch: NotionConnectorPatchDTO


class NotionSyncResourcesInputDTO(ChatStrictDTO):
    connector_id: ConnectorId


class NotionSyncSnapshotSaveInputDTO(ChatStrictDTO):
    connector_id: ConnectorId
    workspace_id: EntityId
    snapshot: JsonObject
    synced_resources: Annotated[list[NotionSyncedResourceDTO], Field(max_length=20_000)]


def _operation(
    name: str,
    kind: Literal["read", "write"],
    digest: str,
    input_dto,
    output_dto,
    *,
    background: bool = False,
) -> DomainOperation:
    return DomainOperation(
        OperationCapabilityDTO(
            name=name,
            kind=kind,
            user_scope=None if background else (
                "dream:read" if kind == "read" else "dream:write"
            ),
            background_scope="connectors:sync" if background else None,
            input_schema_version=1,
            output_schema_version=1,
            contract_sha256=digest,
        ),
        input_dto,
        output_dto,
    )


CREATE_NOTION_CONNECTOR = _operation("notion.connector.create", "write", "402473bfc7ae9406cd0cae4da568864cedb4586c873f31a34cf34189bc290e1a", NotionConnectorCreateInputDTO, NotionConnectorOutputDTO)
LIST_NOTION_CONNECTORS = _operation("notion.connector.list", "read", "d761ef4d8d80047d1d7118bf9f7659a325232ffc7dc6aa87b7c12e36c65bbe06", NotionConnectorListInputDTO, NotionConnectorListOutputDTO)
GET_NOTION_CONNECTOR = _operation("notion.connector.get", "read", "64815d1eac39d954d10925e1409ed7d796370ba9ea0434e5b6a110743061b0c5", NotionConnectorGetInputDTO, NotionConnectorNullableOutputDTO)
GET_ACTIVE_NOTION_CONNECTOR = _operation("notion.connector.active", "read", "07f1cbb77d8c762db86a922742d5d911151eef82647d56e19fb2aadd40e373f7", NotionConnectorActiveInputDTO, NotionConnectorNullableOutputDTO)
PATCH_NOTION_CONNECTOR = _operation("notion.connector.patch", "write", "18795e612570625fa1bbf05f68c263effbfe9a8d91db261e0798d386b08ddae3", NotionConnectorPatchInputDTO, NotionConnectorOutputDTO)
DELETE_NOTION_CONNECTOR = _operation("notion.connector.delete", "write", "61f0d6dc1900e0d44fde9439b3629fba941a0c90f3a590494f454da84780cfa5", NotionConnectorDeleteInputDTO, NotionConnectorDeleteOutputDTO)
SAVE_NOTION_AUTH_STATE = _operation("notion.auth-state.save", "write", "db1783d4dc34872b90796605950c214031230cced460c79d6a59c414e2deb9e6", NotionAuthStateSaveInputDTO, NotionConnectorOutputDTO)
REPLACE_NOTION_RESOURCES = _operation("notion.resources.replace", "write", "af6f06a4dc1042034e8922f0e47847d7128da988c7d66ca42f762c1d4cbd76d1", NotionResourcesReplaceInputDTO, NotionConnectorOutputDTO)
LIST_NOTION_RESOURCES = _operation("notion.resources.list", "read", "71286f9fb456dbd348a49f33b01530eb89c401d29bdb3c7c241d567a0fca08e2", NotionResourcesListInputDTO, NotionResourcesListOutputDTO)
DELETE_NOTION_RESOURCE = _operation("notion.resource.delete", "write", "d5bf4e45f95c1bc2c811552f74dcf4c129cc8573e92edc088c2d657908c2a173", NotionResourceDeleteInputDTO, NotionResourceDeleteOutputDTO)
SAVE_NOTION_SNAPSHOT = _operation("notion.snapshot.save", "write", "9a6e948d64b83f0eed68fb280ee08c9697040cd733bb53d7b25c46e72e6000ad", NotionSnapshotSaveInputDTO, NotionSnapshotOutputDTO)
GET_CURRENT_NOTION_SNAPSHOT = _operation("notion.snapshot.current", "read", "38b158eba983348e8223af83d2f5d8a239452610d2745447add6f3c7c1e82e53", NotionSnapshotCurrentInputDTO, NotionSnapshotNullableOutputDTO)
GET_NOTION_SNAPSHOT = _operation("notion.snapshot.get", "read", "1cba6aa7fb46a911a8381117111b86253c2c446617c04e9d8f3ccad5831c3a05", NotionSnapshotGetInputDTO, NotionSnapshotNullableOutputDTO)
LIST_NOTION_SNAPSHOTS = _operation("notion.snapshot.list", "read", "c2835b854ff6c1146046716d7ea4b613d0b1fff31fee5c74a30dd78c8dae2503", NotionSnapshotListInputDTO, NotionSnapshotListOutputDTO)
ATTACH_NOTION_THREAD = _operation("notion.thread.attach", "write", "a21822b1020ae2b56e7995d0f38a8129acef0c28c60bc892a4a326929b13c213", NotionThreadAttachInputDTO, NotionConnectorOutputDTO)
RESOLVE_NOTION_THREAD = _operation("notion.thread.resolve", "read", "ccd487f299d6c82e6bc30c6f09e2b3c36a5b7a04f108d64d28ff2ace6a8eb648", NotionThreadResolveInputDTO, NotionConnectorNullableOutputDTO)
LIST_NOTION_SYNC_CANDIDATES = _operation("notion.sync-candidates.list", "read", "bd2eaf88d782805a5c5b0c636a95b9ce11639dad660531577a7baf650ee92c00", NotionSyncCandidatesInputDTO, NotionSyncCandidatesOutputDTO, background=True)
GET_NOTION_SYNC_CONNECTOR = _operation("notion.sync-connector.get", "read", "8a110449b15beba461abd1ad53e9ef530a4e05a65e05f6f74a47811d54935e8e", NotionSyncConnectorInputDTO, NotionConnectorNullableOutputDTO, background=True)
PATCH_NOTION_SYNC_CONNECTOR = _operation("notion.sync-connector.patch", "write", "1f079c7698f6f4f0c46311fb98f41977f1ac784c1dfee3c76e98046e4d946c79", NotionSyncConnectorPatchInputDTO, NotionConnectorOutputDTO, background=True)
LIST_NOTION_SYNC_RESOURCES = _operation("notion.sync-resources.list", "read", "58eecf561bfbae8035a7e6e53fc988c605e90c48526d0c301c367135a704e2e2", NotionSyncResourcesInputDTO, NotionResourcesListOutputDTO, background=True)
SAVE_NOTION_SYNC_SNAPSHOT = _operation("notion.sync-snapshot.save", "write", "4922cbb523ce184eb8176f1cb9ed1a68c279cde83421d15d685d7ce46ad67383", NotionSyncSnapshotSaveInputDTO, NotionSnapshotOutputDTO, background=True)

NOTION_CONNECTOR_OPERATIONS = (
    CREATE_NOTION_CONNECTOR, LIST_NOTION_CONNECTORS, GET_NOTION_CONNECTOR,
    GET_ACTIVE_NOTION_CONNECTOR, PATCH_NOTION_CONNECTOR,
    DELETE_NOTION_CONNECTOR, SAVE_NOTION_AUTH_STATE,
    REPLACE_NOTION_RESOURCES, LIST_NOTION_RESOURCES,
    DELETE_NOTION_RESOURCE, SAVE_NOTION_SNAPSHOT,
    GET_CURRENT_NOTION_SNAPSHOT, GET_NOTION_SNAPSHOT,
    LIST_NOTION_SNAPSHOTS, ATTACH_NOTION_THREAD, RESOLVE_NOTION_THREAD,
    LIST_NOTION_SYNC_CANDIDATES, GET_NOTION_SYNC_CONNECTOR,
    PATCH_NOTION_SYNC_CONNECTOR, LIST_NOTION_SYNC_RESOURCES,
    SAVE_NOTION_SYNC_SNAPSHOT,
)
NOTION_CONNECTOR_SCHEMA_REQUIREMENTS = (
    SchemaCapabilityDTO(capability="identity.better-auth.v1", version=1, contract_sha256="1dc05e229d3f4147923fcdfe117c4c4930a43bf9f31439d7b4bc83d2a0d04cd3"),
    SchemaCapabilityDTO(capability="dream.schema.unified.v1", version=1, contract_sha256="8b71cf5687f61dee884c3e6f2fb109c7a951b0789066a0f13583a7b67757fa71"),
)


class AdminNotionConnectorData:
    """Execute Registry148-168 with no retry and exact receipt recovery."""

    def __init__(self, client: AdminDataClient) -> None:
        self._client = client
        self._catalog_lock = RLock()

    def ensure_capabilities(self, request_id: str) -> None:
        with self._catalog_lock:
            if not self._client.supports(
                NOTION_CONNECTOR_OPERATIONS,
                NOTION_CONNECTOR_SCHEMA_REQUIREMENTS,
            ):
                self._client.capabilities(request_id)
            if not self._client.supports(
                NOTION_CONNECTOR_OPERATIONS,
                NOTION_CONNECTOR_SCHEMA_REQUIREMENTS,
            ):
                raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)

    def execute(
        self,
        operation: DomainOperation,
        input_dto: ChatStrictDTO,
        request_id: str,
        *,
        access_token: str | None,
        background_connector_id: str | None = None,
    ):
        self.ensure_capabilities(request_id)
        try:
            return self._client.execute(
                operation,
                input_dto,
                request_id,
                access_token=access_token,
            )
        except AdminDataError as error:
            if not error.outcome_unknown or operation.capability.kind != "write":
                raise
        try:
            if operation.capability.background_scope is not None:
                if background_connector_id is None:
                    raise invalid_response(request_id, write=True)
                receipt = self._client.background_receipt(
                    operation,
                    request_id,
                    connector_id=background_connector_id,
                )
            else:
                receipt = self._client.receipt(
                    operation,
                    request_id,
                    access_token=access_token,
                )
        except AdminDataError as error:
            raise AdminDataError(
                error.code, error.status_code, request_id, True
            ) from None
        if not isinstance(receipt, CommittedReceiptDTO):
            raise AdminDataError(
                "ADMIN_WRITE_RESULT_UNKNOWN", 503, request_id, True
            )
        return receipt.result


__all__ = [
    "AdminNotionConnectorData",
    "NOTION_CONNECTOR_OPERATIONS",
    "NOTION_CONNECTOR_SCHEMA_REQUIREMENTS",
    "NotionAuthorityDTO",
]
