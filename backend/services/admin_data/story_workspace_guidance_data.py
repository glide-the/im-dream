# [Input] Admin Registry115 guidance contract, current OAuth bearer, canonical actor and original request identity.
# [Output] Strict command/result/dispatch DTOs with identity checks and original-receipt-only recovery.
# [Pos] Dream guidance data consumer; all SQL, ORM, permissions, idempotency and transactions stay in Admin.
# [Sync] 2026-09-15: replace Dream guidance persistence with one named DTO/ORM operation.
"""Typed Registry115 consumer for Story Workspace guidance persistence."""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from .chat_models import ChatStrictDTO
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import CanonicalUserId, CommittedReceiptDTO, Identifier, OperationCapabilityDTO
from .workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS

RunId = Annotated[str, Field(pattern=r"^run_[0-9a-f]{32}$")]
MessageId = Annotated[str, Field(min_length=1, max_length=512)]


class StoryWorkspaceGuidanceInputDTO(ChatStrictDTO):
    workflow_run_id: RunId
    kind: Literal["retry-step", "free-text"]
    text: Annotated[str, Field(max_length=4_000)] | None
    step_id: Annotated[str, Field(min_length=1, max_length=128)] | None
    idempotency_key: Annotated[str, Field(min_length=1, max_length=255)]

    @field_validator("text", "step_id", "idempotency_key")
    @classmethod
    def strip_command_text(cls, value: str | None) -> str | None:
        return None if value is None else value.strip()

    @model_validator(mode="after")
    def require_kind_fields(self):
        if self.kind == "free-text" and not self.text:
            raise ValueError("free-text guidance requires non-blank text")
        if self.kind == "retry-step" and self.step_id is None:
            raise ValueError("retry-step guidance requires step_id")
        return self


class StoryWorkspaceGuidanceMetadataDTO(ChatStrictDTO):
    kind: Literal["story-workspace-guidance"]
    story_workspace_run_id: RunId
    actor: CanonicalUserId
    request_id: Identifier
    idempotency_key: Annotated[str, Field(min_length=1, max_length=255)]
    command_kind: Literal["retry-step", "free-text"]
    step_id: Annotated[str, Field(min_length=1, max_length=128)] | None
    text_summary: Annotated[str, Field(max_length=200)]
    review_action: Literal["guide"]
    command_fingerprint: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


class StoryWorkspaceGuidanceTextPartDTO(ChatStrictDTO):
    type: Literal["text"]
    text: str


class StoryWorkspaceGuidanceDispatchDTO(ChatStrictDTO):
    thread_id: Annotated[str, Field(min_length=1, max_length=255)]
    message_id: MessageId
    parts: Annotated[list[StoryWorkspaceGuidanceTextPartDTO], Field(min_length=1, max_length=1)]
    metadata: StoryWorkspaceGuidanceMetadataDTO


class StoryWorkspaceGuidanceResultDTO(ChatStrictDTO):
    message_id: MessageId
    story_workspace_run_id: RunId
    review_action: Literal["guide"]
    status: Literal["accepted"]
    replayed: bool
    request_id: Identifier
    dispatch: StoryWorkspaceGuidanceDispatchDTO | None

    @model_validator(mode="after")
    def bind_dispatch_to_new_result(self):
        if self.replayed != (self.dispatch is None):
            raise ValueError("Only a newly committed guidance result carries dispatch")
        if self.dispatch is not None and (
            self.dispatch.message_id != self.message_id
            or self.dispatch.metadata.story_workspace_run_id
            != self.story_workspace_run_id
            or self.dispatch.metadata.request_id != self.request_id
        ):
            raise ValueError("Guidance dispatch identity does not match the result")
        return self


SUBMIT_STORY_WORKSPACE_GUIDANCE = DomainOperation(
    OperationCapabilityDTO(
        name="story-workspace-guidance.submit",
        kind="write",
        user_scope="dream:write",
        background_scope=None,
        input_schema_version=1,
        output_schema_version=1,
        contract_sha256=(
            "a061ed38d2ca10073bbb7fd078e679f07"
            "2f0cbd4ff1ce900792fbf8725223727"
        ),
    ),
    StoryWorkspaceGuidanceInputDTO,
    StoryWorkspaceGuidanceResultDTO,
)
STORY_WORKSPACE_GUIDANCE_OPERATIONS = (SUBMIT_STORY_WORKSPACE_GUIDANCE,)


def _canonical(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _expected_fingerprint(
    actor_id: str,
    input_dto: StoryWorkspaceGuidanceInputDTO,
) -> str:
    return "sha256:" + hashlib.sha256(
        _canonical({
            "story_workspace_run_id": input_dto.workflow_run_id,
            "actor": actor_id,
            "command_kind": input_dto.kind,
            "text": input_dto.text,
            "step_id": input_dto.step_id,
        }).encode("utf-8")
    ).hexdigest()


def _expected_turn_text(input_dto: StoryWorkspaceGuidanceInputDTO) -> str:
    prefix = f"[story-workspace guidance · run {input_dto.workflow_run_id}]"
    if input_dto.kind == "retry-step":
        suffix = f": {input_dto.text}" if input_dto.text else ""
        return f"{prefix} retry step {input_dto.step_id}{suffix}"
    return f"{prefix} {input_dto.text or ''}"


def _expected_summary(input_dto: StoryWorkspaceGuidanceInputDTO) -> str:
    if input_dto.kind == "retry-step":
        suffix = f": {input_dto.text}" if input_dto.text else ""
        value = f"retry-step {input_dto.step_id}{suffix}"
    else:
        value = input_dto.text or ""
    return value[:200]


def require_story_workspace_guidance_capabilities(
    client: AdminDataClient,
    request_id: str,
) -> None:
    capabilities = client.capabilities(request_id)
    schemas = {item.capability: item for item in capabilities.schema_capabilities}
    if len(schemas) != len(capabilities.schema_capabilities) or any(
        schemas.get(item.capability) != item for item in WORKFLOW_SCHEMA_REQUIREMENTS
    ):
        raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)


class AdminStoryWorkspaceGuidanceData:
    def __init__(self, client: AdminDataClient, *, canonical_user_id: str) -> None:
        self._client = client
        self._canonical_user_id = canonical_user_id

    def _validate(
        self,
        input_dto: StoryWorkspaceGuidanceInputDTO,
        result: StoryWorkspaceGuidanceResultDTO,
        request_id: str,
        *,
        recovered: bool,
    ) -> StoryWorkspaceGuidanceResultDTO:
        expected_message_id = f"guide_{input_dto.idempotency_key}"
        if (
            result.message_id != expected_message_id
            or result.story_workspace_run_id != input_dto.workflow_run_id
        ):
            raise invalid_response(request_id, write=True)
        dispatch = result.dispatch
        if dispatch is not None and (
            dispatch.message_id != expected_message_id
            or dispatch.metadata.actor != self._canonical_user_id
            or dispatch.metadata.idempotency_key != input_dto.idempotency_key
            or dispatch.metadata.command_kind != input_dto.kind
            or dispatch.metadata.step_id != input_dto.step_id
            or dispatch.metadata.text_summary != _expected_summary(input_dto)
            or dispatch.metadata.command_fingerprint
            != _expected_fingerprint(self._canonical_user_id, input_dto)
            or len(dispatch.parts) != 1
            or dispatch.parts[0].text != _expected_turn_text(input_dto)
        ):
            raise invalid_response(request_id, write=True)
        return result

    def submit(
        self,
        input_dto: StoryWorkspaceGuidanceInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> StoryWorkspaceGuidanceResultDTO:
        if type(input_dto) is not StoryWorkspaceGuidanceInputDTO:
            raise AdminDataError("ADMIN_OPERATION_INPUT_INVALID", 400, request_id)
        require_story_workspace_guidance_capabilities(self._client, request_id)
        result = self._client.execute(
            SUBMIT_STORY_WORKSPACE_GUIDANCE,
            input_dto,
            request_id,
            access_token=access_token,
        )
        return self._validate(input_dto, result, request_id, recovered=False)

    def submit_recovering(
        self,
        input_dto: StoryWorkspaceGuidanceInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> StoryWorkspaceGuidanceResultDTO:
        try:
            return self.submit(input_dto, request_id, access_token=access_token)
        except AdminDataError as error:
            if not error.outcome_unknown:
                raise
        try:
            receipt = self._client.receipt(
                SUBMIT_STORY_WORKSPACE_GUIDANCE,
                request_id,
                access_token=access_token,
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
                "ADMIN_WRITE_RESULT_UNKNOWN",
                503,
                request_id,
                True,
            )
        try:
            return self._validate(
                input_dto,
                receipt.result,
                request_id,
                recovered=True,
            )
        except AdminDataError as error:
            raise AdminDataError(
                error.code,
                error.status_code,
                request_id,
                True,
                error.details,
            ) from None
