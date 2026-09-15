# [Input] Admin Registry111 review contracts, current OAuth bearer and original request identity.
# [Output] Strict Story/Character/Scene DTOs with ordered batch validation and receipt-only recovery.
# [Pos] Dream review consumer; Admin owns ORM/transactions while Dream owns routes, pages, Runtime, SSE and files.
# [Sync] 2026-09-15: replace Dream review SQL with two named DTO/ORM business operations.
"""Typed Registry111 consumer for Story Workspace product review."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from .chat_models import ChatStrictDTO, EntityId, validate_timestamp_text
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import CommittedReceiptDTO, OperationCapabilityDTO
from .workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS

ReviewStatus = Literal["pending", "confirmed", "rejected"]
ReviewAction = Literal["confirm", "reject", "archive"]
ReviewResourceType = Literal["story", "character", "scene"]
SafeNonnegativeInteger = Annotated[int, Field(ge=0, le=9_007_199_254_740_991)]


class StoryWorkspaceReviewStoryDTO(ChatStrictDTO):
    id: Annotated[EntityId, Field(max_length=255)]
    identifier: str
    title: str
    description: str | None
    status: Literal["draft", "published", "archived"]
    review_status: ReviewStatus
    review_notes: str | None
    type: Literal["short", "long", "script", "outline"]
    character_count: SafeNonnegativeInteger
    scene_count: SafeNonnegativeInteger
    created_at: str
    updated_at: str
    confirmed_at: str | None
    source_run_id: str | None
    source_project_id: str | None
    episode_count: SafeNonnegativeInteger | None
    artifact_status: Literal["generating", "available", "missing", "invalid"] | None
    artifact_manifest_revision: str | None
    script_revision: str | None
    artifact_sync_status: Literal["syncing", "indexed", "stale", "failed"] | None
    artifact_indexed_at: str | None
    artifact_sync_error_code: Literal[
        "story_index_row_missing",
        "story_index_schema_unavailable",
        "story_index_database_unavailable",
        "story_index_write_failed",
        "story_index_conflict",
        "story_index_invalid_artifact",
        "story_index_revision_conflict",
        "artifact_missing",
    ] | None
    script_size_bytes: SafeNonnegativeInteger | None
    artifact_available: bool | None
    reconcile_version: SafeNonnegativeInteger | None

    _timestamps = field_validator(
        "created_at", "updated_at", "confirmed_at", "artifact_indexed_at"
    )(validate_timestamp_text)


class StoryWorkspaceReviewCharacterDTO(ChatStrictDTO):
    id: Annotated[EntityId, Field(max_length=255)]
    identifier: str
    name: str
    avatar_url: str | None
    identity: str | None
    personality: str | None
    background: str | None
    catchphrase: str | None
    tags: list[str]
    story_count: SafeNonnegativeInteger
    review_status: ReviewStatus
    review_notes: str | None
    status: Literal["active", "archived"]
    created_at: str
    updated_at: str
    confirmed_at: str | None
    archived_at: str | None

    _timestamps = field_validator(
        "created_at", "updated_at", "confirmed_at", "archived_at"
    )(validate_timestamp_text)


class StoryWorkspaceReviewSceneDTO(ChatStrictDTO):
    id: Annotated[EntityId, Field(max_length=255)]
    identifier: str
    name: str
    description: str | None
    story_id: Annotated[EntityId, Field(max_length=255)] | None
    character_count: SafeNonnegativeInteger
    order_index: Annotated[int, Field(ge=-2_147_483_648, le=2_147_483_647)]
    review_status: ReviewStatus
    review_notes: str | None
    status: Literal["active", "archived"]
    created_at: str
    updated_at: str
    confirmed_at: str | None
    archived_at: str | None

    _timestamps = field_validator(
        "created_at", "updated_at", "confirmed_at", "archived_at"
    )(validate_timestamp_text)


ReviewItemDTO = (
    StoryWorkspaceReviewStoryDTO
    | StoryWorkspaceReviewCharacterDTO
    | StoryWorkspaceReviewSceneDTO
)


class StoryWorkspaceReviewTransitionInputDTO(ChatStrictDTO):
    resource_type: ReviewResourceType
    resource_id: Annotated[EntityId, Field(max_length=255)]
    action: ReviewAction
    review_notes: Annotated[str, Field(max_length=2_000)] | None

    @field_validator("resource_id")
    @classmethod
    def strip_resource_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Resource identifier must not be blank")
        return value

    @model_validator(mode="after")
    def restrict_single_archive(self):
        if self.action == "archive" and self.resource_type != "story":
            raise ValueError("Only a Story supports single-item archive")
        return self


class StoryWorkspaceReviewTransitionResultDTO(ChatStrictDTO):
    resource_type: ReviewResourceType
    item: ReviewItemDTO

    @model_validator(mode="after")
    def match_item_type(self):
        expected = {
            "story": StoryWorkspaceReviewStoryDTO,
            "character": StoryWorkspaceReviewCharacterDTO,
            "scene": StoryWorkspaceReviewSceneDTO,
        }[self.resource_type]
        if type(self.item) is not expected:
            raise ValueError("Review item type does not match resource_type")
        return self


class StoryWorkspaceReviewBatchInputDTO(ChatStrictDTO):
    resource_type: ReviewResourceType
    ids: Annotated[list[Annotated[EntityId, Field(max_length=255)]], Field(min_length=1, max_length=100)]
    action: ReviewAction
    review_notes: Annotated[str, Field(max_length=2_000)] | None

    @field_validator("ids")
    @classmethod
    def normalize_ids(cls, ids: list[str]) -> list[str]:
        normalized = [value.strip() for value in ids]
        if any(not value for value in normalized):
            raise ValueError("ids must not contain blank values")
        if len(set(normalized)) != len(normalized):
            raise ValueError("ids must contain unique values")
        return normalized


class StoryWorkspaceReviewBatchResultDTO(ChatStrictDTO):
    success: Literal[True]
    action: ReviewAction
    resource_type: ReviewResourceType
    total_requested: Annotated[int, Field(ge=1, le=100)]
    total_updated: Annotated[int, Field(ge=0, le=100)]
    skipped_ids: list[Annotated[EntityId, Field(max_length=255)]]
    updated_items: list[ReviewItemDTO]

    @model_validator(mode="after")
    def match_item_types(self):
        expected = {
            "story": StoryWorkspaceReviewStoryDTO,
            "character": StoryWorkspaceReviewCharacterDTO,
            "scene": StoryWorkspaceReviewSceneDTO,
        }[self.resource_type]
        if any(type(item) is not expected for item in self.updated_items):
            raise ValueError("Batch item type does not match resource_type")
        return self


TRANSITION_STORY_WORKSPACE_REVIEW = DomainOperation(
    OperationCapabilityDTO(
        name="story-workspace-review.transition",
        kind="write",
        user_scope="dream:write",
        background_scope=None,
        input_schema_version=1,
        output_schema_version=1,
        contract_sha256=(
            "9f741208c6096b38f414fc5fb7c53d04"
            "5d771233055dd68005571e7b47392392"
        ),
    ),
    StoryWorkspaceReviewTransitionInputDTO,
    StoryWorkspaceReviewTransitionResultDTO,
)
BATCH_STORY_WORKSPACE_REVIEW = DomainOperation(
    OperationCapabilityDTO(
        name="story-workspace-review.batch",
        kind="write",
        user_scope="dream:write",
        background_scope=None,
        input_schema_version=1,
        output_schema_version=1,
        contract_sha256=(
            "621206fde4e9322a042940e45234fadf"
            "a4bbe01ba5febea67faf7d2ad0050667"
        ),
    ),
    StoryWorkspaceReviewBatchInputDTO,
    StoryWorkspaceReviewBatchResultDTO,
)
STORY_WORKSPACE_REVIEW_OPERATIONS = (
    TRANSITION_STORY_WORKSPACE_REVIEW,
    BATCH_STORY_WORKSPACE_REVIEW,
)


def require_story_workspace_review_capabilities(
    client: AdminDataClient,
    request_id: str,
) -> None:
    capabilities = client.capabilities(request_id)
    schemas = {item.capability: item for item in capabilities.schema_capabilities}
    if len(schemas) != len(capabilities.schema_capabilities) or any(
        schemas.get(item.capability) != item for item in WORKFLOW_SCHEMA_REQUIREMENTS
    ):
        raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)


class AdminStoryWorkspaceReviewData:
    def __init__(self, client: AdminDataClient) -> None:
        self._client = client

    @staticmethod
    def _validate_transition_reply(
        input_dto: StoryWorkspaceReviewTransitionInputDTO,
        result: StoryWorkspaceReviewTransitionResultDTO,
        request_id: str,
        *,
        write: bool,
    ) -> StoryWorkspaceReviewTransitionResultDTO:
        if result.resource_type != input_dto.resource_type or result.item.id != input_dto.resource_id:
            raise invalid_response(request_id, write=write)
        return result

    @staticmethod
    def _validate_batch_reply(
        input_dto: StoryWorkspaceReviewBatchInputDTO,
        result: StoryWorkspaceReviewBatchResultDTO,
        request_id: str,
        *,
        write: bool,
    ) -> StoryWorkspaceReviewBatchResultDTO:
        updated_ids = [item.id for item in result.updated_items]
        updated = set(updated_ids)
        skipped = set(result.skipped_ids)
        if (
            result.resource_type != input_dto.resource_type
            or result.action != input_dto.action
            or result.total_requested != len(input_dto.ids)
            or result.total_updated != len(updated_ids)
            or len(updated) != len(updated_ids)
            or len(skipped) != len(result.skipped_ids)
            or updated & skipped
            or updated | skipped != set(input_dto.ids)
            or updated_ids != [value for value in input_dto.ids if value in updated]
            or result.skipped_ids != [value for value in input_dto.ids if value in skipped]
        ):
            raise invalid_response(request_id, write=write)
        return result

    def transition(
        self,
        input_dto: StoryWorkspaceReviewTransitionInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> StoryWorkspaceReviewTransitionResultDTO:
        if type(input_dto) is not StoryWorkspaceReviewTransitionInputDTO:
            raise AdminDataError("ADMIN_OPERATION_INPUT_INVALID", 400, request_id)
        require_story_workspace_review_capabilities(self._client, request_id)
        result = self._client.execute(
            TRANSITION_STORY_WORKSPACE_REVIEW,
            input_dto,
            request_id,
            access_token=access_token,
        )
        return self._validate_transition_reply(input_dto, result, request_id, write=True)

    def batch(
        self,
        input_dto: StoryWorkspaceReviewBatchInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> StoryWorkspaceReviewBatchResultDTO:
        if type(input_dto) is not StoryWorkspaceReviewBatchInputDTO:
            raise AdminDataError("ADMIN_OPERATION_INPUT_INVALID", 400, request_id)
        require_story_workspace_review_capabilities(self._client, request_id)
        result = self._client.execute(
            BATCH_STORY_WORKSPACE_REVIEW,
            input_dto,
            request_id,
            access_token=access_token,
        )
        return self._validate_batch_reply(input_dto, result, request_id, write=True)

    def transition_recovering(self, input_dto, request_id: str, *, access_token: str):
        return self._recover(
            TRANSITION_STORY_WORKSPACE_REVIEW,
            input_dto,
            request_id,
            access_token,
            self.transition,
            self._validate_transition_reply,
        )

    def batch_recovering(self, input_dto, request_id: str, *, access_token: str):
        return self._recover(
            BATCH_STORY_WORKSPACE_REVIEW,
            input_dto,
            request_id,
            access_token,
            self.batch,
            self._validate_batch_reply,
        )

    def _recover(
        self,
        operation,
        input_dto,
        request_id: str,
        access_token: str,
        execute,
        validate,
    ):
        try:
            return execute(input_dto, request_id, access_token=access_token)
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
        if not isinstance(receipt, CommittedReceiptDTO):
            raise AdminDataError(
                "ADMIN_WRITE_RESULT_UNKNOWN", 503, request_id, True
            )
        try:
            return validate(input_dto, receipt.result, request_id, write=True)
        except AdminDataError as error:
            raise AdminDataError(
                error.code,
                error.status_code,
                request_id,
                True,
                error.details,
            ) from None
