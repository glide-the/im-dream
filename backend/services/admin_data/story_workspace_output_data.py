# [Input] Admin Registry109 output contract and one exact server-persistence Thread grant.
# [Output] Strict Story proposal DTOs with original-request receipt recovery.
# [Pos] Dream consumer boundary; Admin owns ORM/transaction while Dream owns parsing, Runtime, SSE and files.
# [Sync] 2026-09-15: pin story-workspace-output.store without actor, Workspace, SQL or path selectors.
"""Typed Registry109 consumer for atomic standalone Story proposal persistence."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from .chat_models import ChatStrictDTO, EntityId
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import CommittedReceiptDTO, OperationCapabilityDTO
from .workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS


class StoryWorkspaceOutputCharacterDTO(ChatStrictDTO):
    name: Annotated[str, Field(min_length=1)]
    identity: str | None
    personality: str | None
    background: str | None
    catchphrase: str | None
    tags: list[str]

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Character name must not be blank")
        return value


class StoryWorkspaceOutputSceneDTO(ChatStrictDTO):
    name: Annotated[str, Field(min_length=1)]
    description: str | None
    order_index: Annotated[int, Field(ge=-2_147_483_648, le=2_147_483_647)]

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Scene name must not be blank")
        return value


class StoryWorkspaceOutputStoryDTO(ChatStrictDTO):
    title: Annotated[str, Field(min_length=1)]
    description: str | None
    type: Literal["short", "long", "script", "outline"]
    content: str | None
    characters: list[StoryWorkspaceOutputCharacterDTO]
    scenes: list[StoryWorkspaceOutputSceneDTO]

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Story title must not be blank")
        return value

    @model_validator(mode="after")
    def require_unique_bundle_identities(self):
        if len({item.name for item in self.characters}) != len(self.characters):
            raise ValueError("Character names must be unique")
        if len({item.order_index for item in self.scenes}) != len(self.scenes):
            raise ValueError("Scene order_index values must be unique")
        return self


class StoryWorkspaceOutputInputDTO(ChatStrictDTO):
    thread_id: Annotated[EntityId, Field(max_length=255)]
    story: StoryWorkspaceOutputStoryDTO


class StoryWorkspaceOutputResultDTO(ChatStrictDTO):
    story_id: EntityId
    review_status: Literal["pending"]
    character_ids: list[EntityId]
    scene_ids: list[EntityId]
    chat_thread_id: Annotated[EntityId, Field(max_length=255)]
    deck_id: EntityId | None
    deck_name: str | None
    deck_name_zh: str | None
    deck_name_en: str | None


STORE_STORY_WORKSPACE_OUTPUT = DomainOperation(
    OperationCapabilityDTO(
        name="story-workspace-output.store",
        kind="write",
        user_scope="dream:write",
        background_scope=None,
        input_schema_version=1,
        output_schema_version=1,
        contract_sha256=(
            "2b7d9180c78829df86289d717037ddbf"
            "d20ecee517d8213e0e71b9388cee65ed"
        ),
    ),
    StoryWorkspaceOutputInputDTO,
    StoryWorkspaceOutputResultDTO,
)
STORY_WORKSPACE_OUTPUT_OPERATIONS = (STORE_STORY_WORKSPACE_OUTPUT,)


def require_story_workspace_output_capabilities(
    client: AdminDataClient,
    request_id: str,
) -> None:
    capabilities = client.capabilities(request_id)
    schemas = {
        item.capability: item for item in capabilities.schema_capabilities
    }
    if (
        len(schemas) != len(capabilities.schema_capabilities)
        or any(
            schemas.get(item.capability) != item
            for item in WORKFLOW_SCHEMA_REQUIREMENTS
        )
    ):
        raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)


class AdminStoryWorkspaceOutputProvider:
    """Marker for a server owner that persists one parsed Story proposal."""

    def store_story_workspace_output(
        self,
        *,
        actor_id: str,
        thread_id: str,
        story: dict,
    ) -> StoryWorkspaceOutputResultDTO:
        raise NotImplementedError


class AdminStoryWorkspaceOutputData:
    def __init__(self, client: AdminDataClient) -> None:
        self._client = client

    @staticmethod
    def validate_reply(
        input_dto: StoryWorkspaceOutputInputDTO,
        result: StoryWorkspaceOutputResultDTO,
        request_id: str,
        *,
        write: bool,
    ) -> StoryWorkspaceOutputResultDTO:
        if result.chat_thread_id != input_dto.thread_id:
            raise invalid_response(request_id, write=write)
        return result

    def store(
        self,
        input_dto: StoryWorkspaceOutputInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> StoryWorkspaceOutputResultDTO:
        if type(input_dto) is not StoryWorkspaceOutputInputDTO:
            raise AdminDataError("ADMIN_OPERATION_INPUT_INVALID", 400, request_id)
        require_story_workspace_output_capabilities(self._client, request_id)
        result = self._client.execute(
            STORE_STORY_WORKSPACE_OUTPUT,
            input_dto,
            request_id,
            access_token=access_token,
        )
        return self.validate_reply(input_dto, result, request_id, write=True)

    def store_recovering(
        self,
        input_dto: StoryWorkspaceOutputInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> StoryWorkspaceOutputResultDTO:
        """Execute once and recover only the same original committed result."""

        try:
            return self.store(
                input_dto,
                request_id,
                access_token=access_token,
            )
        except AdminDataError as error:
            if not error.outcome_unknown:
                raise
            original_request_id = request_id
        try:
            receipt = self.receipt(
                input_dto,
                original_request_id,
                access_token=access_token,
            )
        except AdminDataError as error:
            raise AdminDataError(
                error.code,
                error.status_code,
                original_request_id,
                True,
                error.details,
            ) from None
        if not isinstance(receipt, CommittedReceiptDTO):
            raise AdminDataError(
                "ADMIN_WRITE_RESULT_UNKNOWN",
                503,
                original_request_id,
                True,
            )
        return receipt.result

    def receipt(
        self,
        input_dto: StoryWorkspaceOutputInputDTO,
        request_id: str,
        *,
        access_token: str,
    ):
        if type(input_dto) is not StoryWorkspaceOutputInputDTO:
            raise AdminDataError("ADMIN_OPERATION_INPUT_INVALID", 400, request_id)
        require_story_workspace_output_capabilities(self._client, request_id)
        result = self._client.receipt(
            STORE_STORY_WORKSPACE_OUTPUT,
            request_id,
            access_token=access_token,
        )
        if result.status == "committed":
            self.validate_reply(input_dto, result.result, request_id, write=True)
        return result
