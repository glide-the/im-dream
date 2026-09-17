# [Input] Admin Registry114 catalog contracts, current OAuth bearer, and original request identity.
# [Output] Strict workspace/read/patch DTOs with identity checks and receipt-only write recovery.
# [Pos] Dream Story Workspace catalog consumer; all SQL, ORM, permissions, and transactions stay in Admin.
# [Sync] 2026-09-15: replace Dream catalog SQL with three named DTO/ORM business operations.
"""Typed Registry114 consumer for Story Workspace catalog browse and edit."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import ConfigDict, Field, RootModel, field_validator, model_validator

from .chat_models import ChatStrictDTO, EntityId, PresentFieldsDTO, validate_timestamp_text
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import CommittedReceiptDTO, OperationCapabilityDTO
from .story_workspace_review_data import (
    ReviewStatus,
    SafeNonnegativeInteger,
    StoryWorkspaceReviewCharacterDTO,
    StoryWorkspaceReviewSceneDTO,
    StoryWorkspaceReviewStoryDTO,
)
from .workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS

CatalogView = Literal[
    "story_list", "story_detail", "character_list", "character_detail",
    "scene_list", "scene_detail",
]
SortOrder = Literal["asc", "desc"]


class StoryWorkspaceCatalogWorkspaceDTO(ChatStrictDTO):
    id: Annotated[EntityId, Field(max_length=255)]
    name: str
    settings: dict[str, object]
    created_at: str
    updated_at: str
    _timestamps = field_validator("created_at", "updated_at")(validate_timestamp_text)


class StoryWorkspaceCatalogRelatedCharacterDTO(StoryWorkspaceReviewCharacterDTO):
    role_type: str | None


class StoryWorkspaceCatalogStoryDetailDTO(StoryWorkspaceReviewStoryDTO):
    characters: list[StoryWorkspaceCatalogRelatedCharacterDTO]
    scenes: list[StoryWorkspaceReviewSceneDTO]


class StoryWorkspaceCatalogCharacterDetailDTO(StoryWorkspaceReviewCharacterDTO):
    stories: list[StoryWorkspaceReviewStoryDTO]


class StoryWorkspaceCatalogSceneDetailDTO(StoryWorkspaceReviewSceneDTO):
    story: StoryWorkspaceReviewStoryDTO | None
    characters: list[StoryWorkspaceReviewCharacterDTO]


class StoryListInputDTO(ChatStrictDTO):
    view: Literal["story_list"]
    q: Annotated[str, Field(max_length=1_000)] | None
    review_status: list[ReviewStatus]
    status: list[Literal["draft", "published", "archived"]]
    type: list[Literal["short", "long", "script", "outline"]]
    sort: Literal["updated_at", "created_at", "title"]
    order: SortOrder
    page: Annotated[int, Field(ge=1)]
    per_page: Annotated[int, Field(ge=1, le=100)]


class CharacterListInputDTO(ChatStrictDTO):
    view: Literal["character_list"]
    q: Annotated[str, Field(max_length=1_000)] | None
    review_status: list[ReviewStatus]
    sort: Literal["updated_at", "created_at", "name"]
    order: SortOrder
    page: Annotated[int, Field(ge=1)]
    per_page: Annotated[int, Field(ge=1, le=100)]


class SceneListInputDTO(ChatStrictDTO):
    view: Literal["scene_list"]
    q: Annotated[str, Field(max_length=1_000)] | None
    review_status: list[ReviewStatus]
    story_id: Annotated[EntityId, Field(max_length=255)] | None
    sort: Literal["updated_at", "created_at", "name", "order_index"]
    order: SortOrder
    page: Annotated[int, Field(ge=1)]
    per_page: Annotated[int, Field(ge=1, le=100)]


class ResourceReadInputDTO(ChatStrictDTO):
    view: Literal["story_detail", "character_detail", "scene_detail"]
    resource_id: Annotated[EntityId, Field(max_length=255)]

    @field_validator("resource_id")
    @classmethod
    def normalize_resource_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("resource_id must not be blank")
        return value


CatalogReadInput = Annotated[
    StoryListInputDTO | CharacterListInputDTO | SceneListInputDTO | ResourceReadInputDTO,
    Field(discriminator="view"),
]


class StoryWorkspaceCatalogReadInputDTO(RootModel[CatalogReadInput]):
    model_config = ConfigDict(frozen=True, hide_input_in_errors=True)


class PaginationDTO(ChatStrictDTO):
    page: Annotated[int, Field(ge=1)]
    per_page: Annotated[int, Field(ge=1, le=100)]
    total: SafeNonnegativeInteger
    total_pages: SafeNonnegativeInteger


class StoryListResultDTO(ChatStrictDTO):
    view: Literal["story_list"]
    data: list[StoryWorkspaceReviewStoryDTO]
    pagination: PaginationDTO


class CharacterListResultDTO(ChatStrictDTO):
    view: Literal["character_list"]
    data: list[StoryWorkspaceReviewCharacterDTO]
    pagination: PaginationDTO


class SceneListResultDTO(ChatStrictDTO):
    view: Literal["scene_list"]
    data: list[StoryWorkspaceReviewSceneDTO]
    pagination: PaginationDTO


class StoryDetailResultDTO(ChatStrictDTO):
    view: Literal["story_detail"]
    item: StoryWorkspaceCatalogStoryDetailDTO


class CharacterDetailResultDTO(ChatStrictDTO):
    view: Literal["character_detail"]
    item: StoryWorkspaceCatalogCharacterDetailDTO


class SceneDetailResultDTO(ChatStrictDTO):
    view: Literal["scene_detail"]
    item: StoryWorkspaceCatalogSceneDetailDTO


CatalogReadResult = Annotated[
    StoryListResultDTO | StoryDetailResultDTO | CharacterListResultDTO |
    CharacterDetailResultDTO | SceneListResultDTO | SceneDetailResultDTO,
    Field(discriminator="view"),
]


class StoryWorkspaceCatalogReadResultDTO(RootModel[CatalogReadResult]):
    model_config = ConfigDict(frozen=True, hide_input_in_errors=True)


class WorkspacePatchDTO(PresentFieldsDTO):
    name: str = None  # type: ignore[assignment]
    settings: dict[str, object] = None  # type: ignore[assignment]


class WorkspaceEnsureInputDTO(ChatStrictDTO):
    action: Literal["ensure"]


class WorkspacePatchInputDTO(ChatStrictDTO):
    action: Literal["patch"]
    workspace_id: Annotated[EntityId, Field(max_length=255)]
    patch: WorkspacePatchDTO


class StoryWorkspaceCatalogWorkspaceInputDTO(
    RootModel[Annotated[WorkspaceEnsureInputDTO | WorkspacePatchInputDTO, Field(discriminator="action")]]
):
    model_config = ConfigDict(frozen=True, hide_input_in_errors=True)


class StoryWorkspaceCatalogWorkspaceResultDTO(ChatStrictDTO):
    action: Literal["ensure", "patch"]
    item: StoryWorkspaceCatalogWorkspaceDTO


class StoryPatchDTO(PresentFieldsDTO):
    title: str = None  # type: ignore[assignment]
    description: str | None = None
    content: str | None = None
    type: Literal["short", "long", "script", "outline"] = None  # type: ignore[assignment]


class CharacterPatchDTO(PresentFieldsDTO):
    name: str = None  # type: ignore[assignment]
    identity: str | None = None
    personality: str | None = None
    background: str | None = None
    catchphrase: str | None = None
    tags: list[str] = None  # type: ignore[assignment]
    avatar_url: str | None = None


class ScenePatchDTO(PresentFieldsDTO):
    name: str = None  # type: ignore[assignment]
    description: str | None = None
    story_id: Annotated[EntityId, Field(max_length=255)] | None = None
    order_index: Annotated[int, Field(ge=-2_147_483_648, le=2_147_483_647)] = None  # type: ignore[assignment]


class StoryPatchInputDTO(ChatStrictDTO):
    resource_type: Literal["story"]
    resource_id: Annotated[EntityId, Field(max_length=255)]
    patch: StoryPatchDTO


class CharacterPatchInputDTO(ChatStrictDTO):
    resource_type: Literal["character"]
    resource_id: Annotated[EntityId, Field(max_length=255)]
    patch: CharacterPatchDTO


class ScenePatchInputDTO(ChatStrictDTO):
    resource_type: Literal["scene"]
    resource_id: Annotated[EntityId, Field(max_length=255)]
    patch: ScenePatchDTO


CatalogPatchInput = Annotated[
    StoryPatchInputDTO | CharacterPatchInputDTO | ScenePatchInputDTO,
    Field(discriminator="resource_type"),
]


class StoryWorkspaceCatalogPatchInputDTO(RootModel[CatalogPatchInput]):
    model_config = ConfigDict(frozen=True, hide_input_in_errors=True)


class StoryPatchResultDTO(ChatStrictDTO):
    resource_type: Literal["story"]
    item: StoryWorkspaceReviewStoryDTO


class CharacterPatchResultDTO(ChatStrictDTO):
    resource_type: Literal["character"]
    item: StoryWorkspaceReviewCharacterDTO


class ScenePatchResultDTO(ChatStrictDTO):
    resource_type: Literal["scene"]
    item: StoryWorkspaceReviewSceneDTO


class StoryWorkspaceCatalogPatchResultDTO(
    RootModel[Annotated[StoryPatchResultDTO | CharacterPatchResultDTO | ScenePatchResultDTO,
                        Field(discriminator="resource_type")]]
):
    model_config = ConfigDict(frozen=True, hide_input_in_errors=True)


WORKSPACE_STORY_WORKSPACE_CATALOG = DomainOperation(
    OperationCapabilityDTO(
        name="story-workspace-catalog.workspace", kind="write", user_scope="dream:write",
        background_scope=None, input_schema_version=1, output_schema_version=1,
        contract_sha256="3fbd32dd7343ae5008d7f71f2475db1b022a95060f2544b9dfbea606af894965",
    ), StoryWorkspaceCatalogWorkspaceInputDTO, StoryWorkspaceCatalogWorkspaceResultDTO,
)
READ_STORY_WORKSPACE_CATALOG = DomainOperation(
    OperationCapabilityDTO(
        name="story-workspace-catalog.read", kind="read", user_scope="dream:read",
        background_scope=None, input_schema_version=1, output_schema_version=1,
        contract_sha256="317ed15c2f827c44099e0641693d3dcf09bc01186e26586a9b2281226faa142b",
    ), StoryWorkspaceCatalogReadInputDTO, StoryWorkspaceCatalogReadResultDTO,
)
PATCH_STORY_WORKSPACE_CATALOG = DomainOperation(
    OperationCapabilityDTO(
        name="story-workspace-catalog.patch", kind="write", user_scope="dream:write",
        background_scope=None, input_schema_version=1, output_schema_version=1,
        contract_sha256="0ef2cc94d01d488c46a9872efb389b43890e9267460705ebee33ac5ab47180cd",
    ), StoryWorkspaceCatalogPatchInputDTO, StoryWorkspaceCatalogPatchResultDTO,
)
STORY_WORKSPACE_CATALOG_OPERATIONS = (
    WORKSPACE_STORY_WORKSPACE_CATALOG, READ_STORY_WORKSPACE_CATALOG, PATCH_STORY_WORKSPACE_CATALOG,
)


def require_story_workspace_catalog_capabilities(client: AdminDataClient, request_id: str) -> None:
    capabilities = client.capabilities(request_id)
    schemas = {item.capability: item for item in capabilities.schema_capabilities}
    if len(schemas) != len(capabilities.schema_capabilities) or any(
        schemas.get(item.capability) != item for item in WORKFLOW_SCHEMA_REQUIREMENTS
    ):
        raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)


class AdminStoryWorkspaceCatalogData:
    def __init__(self, client: AdminDataClient) -> None:
        self._client = client

    def read(self, input_dto: StoryWorkspaceCatalogReadInputDTO, request_id: str, *, access_token: str):
        if type(input_dto) is not StoryWorkspaceCatalogReadInputDTO:
            raise AdminDataError("ADMIN_OPERATION_INPUT_INVALID", 400, request_id)
        require_story_workspace_catalog_capabilities(self._client, request_id)
        result = self._client.execute(READ_STORY_WORKSPACE_CATALOG, input_dto, request_id, access_token=access_token)
        if result.root.view != input_dto.root.view:
            raise invalid_response(request_id)
        if hasattr(input_dto.root, "resource_id") and result.root.item.id != input_dto.root.resource_id:
            raise invalid_response(request_id)
        if hasattr(result.root, "pagination") and (
            result.root.pagination.page != input_dto.root.page or
            result.root.pagination.per_page != input_dto.root.per_page
        ):
            raise invalid_response(request_id)
        return result.root

    def workspace(self, input_dto: StoryWorkspaceCatalogWorkspaceInputDTO, request_id: str, *, access_token: str):
        if type(input_dto) is not StoryWorkspaceCatalogWorkspaceInputDTO:
            raise AdminDataError("ADMIN_OPERATION_INPUT_INVALID", 400, request_id)
        require_story_workspace_catalog_capabilities(self._client, request_id)
        result = self._client.execute(WORKSPACE_STORY_WORKSPACE_CATALOG, input_dto, request_id, access_token=access_token)
        if result.action != input_dto.root.action or (
            isinstance(input_dto.root, WorkspacePatchInputDTO) and result.item.id != input_dto.root.workspace_id
        ):
            raise invalid_response(request_id, write=True)
        return result

    def patch(self, input_dto: StoryWorkspaceCatalogPatchInputDTO, request_id: str, *, access_token: str):
        if type(input_dto) is not StoryWorkspaceCatalogPatchInputDTO:
            raise AdminDataError("ADMIN_OPERATION_INPUT_INVALID", 400, request_id)
        require_story_workspace_catalog_capabilities(self._client, request_id)
        result = self._client.execute(PATCH_STORY_WORKSPACE_CATALOG, input_dto, request_id, access_token=access_token)
        if result.root.resource_type != input_dto.root.resource_type or result.root.item.id != input_dto.root.resource_id:
            raise invalid_response(request_id, write=True)
        return result.root

    def workspace_recovering(self, input_dto, request_id: str, *, access_token: str):
        return self._recover(WORKSPACE_STORY_WORKSPACE_CATALOG, input_dto, request_id, access_token,
                             self.workspace, self._validate_workspace_receipt)

    def patch_recovering(self, input_dto, request_id: str, *, access_token: str):
        return self._recover(PATCH_STORY_WORKSPACE_CATALOG, input_dto, request_id, access_token,
                             self.patch, self._validate_patch_receipt)

    @staticmethod
    def _validate_workspace_receipt(input_dto, result, request_id: str):
        if result.action != input_dto.root.action or (
            isinstance(input_dto.root, WorkspacePatchInputDTO) and result.item.id != input_dto.root.workspace_id
        ):
            raise invalid_response(request_id, write=True)
        return result

    @staticmethod
    def _validate_patch_receipt(input_dto, result, request_id: str):
        if result.root.resource_type != input_dto.root.resource_type or result.root.item.id != input_dto.root.resource_id:
            raise invalid_response(request_id, write=True)
        return result.root

    def _recover(self, operation, input_dto, request_id, access_token, execute, validate):
        try:
            return execute(input_dto, request_id, access_token=access_token)
        except AdminDataError as error:
            if not error.outcome_unknown:
                raise
        try:
            receipt = self._client.receipt(operation, request_id, access_token=access_token)
        except AdminDataError as error:
            raise AdminDataError(error.code, error.status_code, request_id, True, error.details) from None
        if not isinstance(receipt, CommittedReceiptDTO):
            raise AdminDataError("ADMIN_WRITE_RESULT_UNKNOWN", 503, request_id, True)
        try:
            return validate(input_dto, receipt.result, request_id)
        except AdminDataError as error:
            raise AdminDataError(error.code, error.status_code, request_id, True, error.details) from None
