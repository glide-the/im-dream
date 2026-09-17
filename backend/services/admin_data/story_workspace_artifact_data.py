# [Sync] 2026-09-17: reuse the validated immutable Admin capability snapshot instead of repeating discovery per domain call.
# [Input] Admin Registry185-191 descriptors, OAuth or exact server-persistence grant, and normalized file facts.
# [Output] Strict authority/lifecycle/Story-index DTOs with original-request receipt recovery.
# [Pos] Dream consumer boundary; Admin owns ORM/transactions while Dream owns Runtime, SSE and shared files.
# [Sync] 2026-09-16: replace final Story Workspace production SQL with named Admin operations.
"""Typed Story Workspace Artifact Admin data client."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, field_validator

from models.workflow_run import WorkflowRun

from .chat_models import ChatStrictDTO, EntityId, PositiveSafeInteger, validate_timestamp_text
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import CommittedReceiptDTO, OperationCapabilityDTO
from .run_data import RunDTO, RunId
from .workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS


Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
ProjectSlug = Annotated[
    str,
    Field(min_length=1, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"),
]
EpisodeCode = Annotated[str, Field(pattern=r"^EP(?:0[1-9]|[1-9][0-9])$")]


class StoryWorkspaceEpisodeAuthorityDTO(ChatStrictDTO):
    schema_: Literal["story-workspace-episode-authority/v1"] = Field(alias="schema")
    workflow_run_id: RunId
    episode_uid: Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]
    story_slug: ProjectSlug
    episode_code: EpisodeCode


class StoryWorkspaceArtifactAuthorityDTO(ChatStrictDTO):
    run: RunDTO
    thread_id: Annotated[EntityId, Field(max_length=255)]
    thread_updated_at: str
    deck_id: EntityId
    deck_display_name: Annotated[str, Field(min_length=1, max_length=255)]
    launch_agent_id: Annotated[str, Field(min_length=1, max_length=255)] | None
    goal: Annotated[str, Field(min_length=1, max_length=12_000)]
    project_story_slug: ProjectSlug
    episode_authority: StoryWorkspaceEpisodeAuthorityDTO | None
    project_title: Annotated[str, Field(min_length=1, max_length=255)] | None
    confirmation_accepted: bool
    confirmation_dispatched: bool

    _thread_time = field_validator("thread_updated_at", mode="before")(
        validate_timestamp_text
    )

    def workflow_run(self) -> WorkflowRun:
        return WorkflowRun.model_validate(self.run.model_dump())


class StoryWorkspaceArtifactCursorDTO(ChatStrictDTO):
    created_at: str
    workflow_run_id: RunId

    _created_time = field_validator("created_at", mode="before")(
        validate_timestamp_text
    )


class StoryWorkspaceArtifactRunsInputDTO(ChatStrictDTO):
    limit: Annotated[int, Field(ge=1, le=100)]
    cursor: StoryWorkspaceArtifactCursorDTO | None


class StoryWorkspaceArtifactRunsOutputDTO(ChatStrictDTO):
    runs: list[StoryWorkspaceArtifactAuthorityDTO]
    next_cursor: StoryWorkspaceArtifactCursorDTO | None


class StoryWorkspaceArtifactAuthorityInputDTO(ChatStrictDTO):
    workflow_run_id: RunId


class StoryWorkspaceArtifactAuthorityOutputDTO(ChatStrictDTO):
    authority: StoryWorkspaceArtifactAuthorityDTO


class StoryWorkspaceEpisodeAuthorityEnsureInputDTO(ChatStrictDTO):
    workflow_run_id: RunId
    story_slug: ProjectSlug
    episode_code: EpisodeCode


class StoryWorkspaceEpisodeAuthorityEnsureOutputDTO(ChatStrictDTO):
    authority: StoryWorkspaceEpisodeAuthorityDTO
    replayed: bool


class StoryWorkspaceArtifactOutputReadyInputDTO(ChatStrictDTO):
    workflow_run_id: RunId
    normalized_result_ready: Literal[True]


class StoryWorkspaceArtifactOutputReadyOutputDTO(ChatStrictDTO):
    workflow_run_id: RunId
    status: Literal["pending_review", "confirmed", "rejected", "completed"]
    status_version: PositiveSafeInteger
    replayed: bool


class StoryWorkspaceArtifactProjectionDTO(ChatStrictDTO):
    source_project_id: ProjectSlug
    title: Annotated[str, Field(min_length=1, max_length=255)]
    episode_count: Annotated[int, Field(ge=1, le=99)]
    artifact_manifest_revision: Digest
    script_revision: Digest
    script_size_bytes: Annotated[int, Field(ge=0, le=9_007_199_254_740_991)]
    artifact_status: Literal["available"]

    @field_validator("title")
    @classmethod
    def require_trimmed_title(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("Story title must be trimmed")
        return value


class StoryWorkspaceArtifactIndexInputDTO(ChatStrictDTO):
    workflow_run_id: RunId
    projection: StoryWorkspaceArtifactProjectionDTO


class StoryWorkspaceArtifactIndexReconcileInputDTO(
    StoryWorkspaceArtifactIndexInputDTO
):
    expected_etag: Digest


class StoryWorkspaceArtifactIndexObservationDTO(ChatStrictDTO):
    run_id: RunId
    project_id: ProjectSlug
    project_title: Annotated[str, Field(min_length=1, max_length=255)]
    story_id: EntityId | None
    status: Literal["missing", "stale", "indexed", "failed"]
    observed_manifest_revision: Digest
    observed_script_revision: Digest
    indexed_manifest_revision: Digest | None
    indexed_script_revision: Digest | None
    episode_count: Annotated[int, Field(ge=1, le=99)]
    last_indexed_at: str | None
    error_code: Literal[
        "story_index_row_missing",
        "story_index_write_failed",
        "story_index_conflict",
        "story_index_revision_conflict",
    ] | None
    retryable: bool
    etag: Digest

    _indexed_time = field_validator("last_indexed_at", mode="before")(
        validate_timestamp_text
    )


class StoryWorkspaceArtifactIndexOutputDTO(ChatStrictDTO):
    observation: StoryWorkspaceArtifactIndexObservationDTO
    write_status: Literal["created", "updated", "same_revision"] | None


def _operation(name: str, kind: Literal["read", "write"], scope: str, digest: str,
               input_dto, output_dto):
    return DomainOperation(
        OperationCapabilityDTO(
            name=name,
            kind=kind,
            user_scope=scope,
            background_scope=None,
            input_schema_version=1,
            output_schema_version=1,
            contract_sha256=digest,
        ),
        input_dto,
        output_dto,
    )


LIST_STORY_WORKSPACE_ARTIFACT_RUNS = _operation(
    "story-workspace-artifact.runs", "read", "dream:read",
    "4a6d51e9768000a843c8a2fce68f4c98556368c05f504f5160786bfd3cff22dd",
    StoryWorkspaceArtifactRunsInputDTO, StoryWorkspaceArtifactRunsOutputDTO,
)
READ_STORY_WORKSPACE_ARTIFACT_AUTHORITY = _operation(
    "story-workspace-artifact.authority", "read", "dream:read",
    "2c7aa9af8fe8ea40c04a4065370ac77233911889a3d8658d4d7f7009e36732be",
    StoryWorkspaceArtifactAuthorityInputDTO,
    StoryWorkspaceArtifactAuthorityOutputDTO,
)
ENSURE_STORY_WORKSPACE_EPISODE_AUTHORITY = _operation(
    "story-workspace-artifact.episode-authority.ensure", "write", "dream:write",
    "344f0c181d785370f3b98a6755d20fff3005db4bc46008640a5ddcad149dd792",
    StoryWorkspaceEpisodeAuthorityEnsureInputDTO,
    StoryWorkspaceEpisodeAuthorityEnsureOutputDTO,
)
MARK_STORY_WORKSPACE_ARTIFACT_OUTPUT_READY = _operation(
    "story-workspace-artifact.output-ready", "write", "dream:write",
    "dc56799f1c487f5a1e37b59d9369803558baedc3c015829abb7661133876d6fa",
    StoryWorkspaceArtifactOutputReadyInputDTO,
    StoryWorkspaceArtifactOutputReadyOutputDTO,
)
INSPECT_STORY_WORKSPACE_ARTIFACT_INDEX = _operation(
    "story-workspace-artifact.index.inspect", "read", "dream:read",
    "514c48c5790736a94893712d5ed0c44795ee46cce8061ad3f531a842bf9b46e1",
    StoryWorkspaceArtifactIndexInputDTO, StoryWorkspaceArtifactIndexOutputDTO,
)
MATERIALIZE_STORY_WORKSPACE_ARTIFACT_INDEX = _operation(
    "story-workspace-artifact.index.materialize", "write", "dream:write",
    "555f6c9fad6dd659b5da6ae855325ef2af81edf6a21224bd3a1b2cd8c1b18a8a",
    StoryWorkspaceArtifactIndexInputDTO, StoryWorkspaceArtifactIndexOutputDTO,
)
RECONCILE_STORY_WORKSPACE_ARTIFACT_INDEX = _operation(
    "story-workspace-artifact.index.reconcile", "write", "dream:write",
    "18dda46efa34060fbaf01b665cfd0f43a4ea6805295847b5d5f48acde79f08dc",
    StoryWorkspaceArtifactIndexReconcileInputDTO,
    StoryWorkspaceArtifactIndexOutputDTO,
)
STORY_WORKSPACE_ARTIFACT_OPERATIONS = (
    LIST_STORY_WORKSPACE_ARTIFACT_RUNS,
    READ_STORY_WORKSPACE_ARTIFACT_AUTHORITY,
    ENSURE_STORY_WORKSPACE_EPISODE_AUTHORITY,
    MARK_STORY_WORKSPACE_ARTIFACT_OUTPUT_READY,
    INSPECT_STORY_WORKSPACE_ARTIFACT_INDEX,
    MATERIALIZE_STORY_WORKSPACE_ARTIFACT_INDEX,
    RECONCILE_STORY_WORKSPACE_ARTIFACT_INDEX,
)


def require_story_workspace_artifact_capabilities(
    client: AdminDataClient, request_id: str
) -> None:
    capabilities = client.capabilities_snapshot(request_id)
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


class AdminStoryWorkspaceArtifactProvider:
    """Turn-owned provider for exact Run authority and Artifact writes."""

    def story_workspace_artifact_authority(self, *, actor_id: str,
                                           thread_id: str,
                                           workflow_run_id: str):
        raise NotImplementedError

    def ensure_story_workspace_episode_authority(self, *, actor_id: str,
                                                 thread_id: str,
                                                 workflow_run_id: str,
                                                 story_slug: str,
                                                 episode_code: str):
        raise NotImplementedError

    def mark_story_workspace_artifact_output_ready(self, *, actor_id: str,
                                                   thread_id: str,
                                                   workflow_run_id: str):
        raise NotImplementedError

    def materialize_story_workspace_artifact_index(self, *, actor_id: str,
                                                   thread_id: str,
                                                   workflow_run_id: str,
                                                   projection: StoryWorkspaceArtifactProjectionDTO):
        raise NotImplementedError


class AdminStoryWorkspaceArtifactData:
    def __init__(self, client: AdminDataClient, *, canonical_user_id: str):
        self._client = client
        self._canonical_user_id = canonical_user_id

    def _validate(self, operation, input_dto, result, request_id: str,
                  *, write: bool = False):
        invalid = False
        if operation is LIST_STORY_WORKSPACE_ARTIFACT_RUNS:
            invalid = any(
                item.run.created_by != self._canonical_user_id
                or item.thread_id != item.run.source_voice_thread_id
                or (
                    item.episode_authority is not None
                    and item.run.workflow_run_id
                    != item.episode_authority.workflow_run_id
                )
                for item in result.runs
            )
        elif operation is READ_STORY_WORKSPACE_ARTIFACT_AUTHORITY:
            item = result.authority
            invalid = (
                item.run.created_by != self._canonical_user_id
                or item.run.workflow_run_id != input_dto.workflow_run_id
                or item.thread_id != item.run.source_voice_thread_id
            )
        elif operation is ENSURE_STORY_WORKSPACE_EPISODE_AUTHORITY:
            invalid = (
                result.authority.workflow_run_id != input_dto.workflow_run_id
                or result.authority.story_slug != input_dto.story_slug
                or result.authority.episode_code != input_dto.episode_code
            )
        elif operation is MARK_STORY_WORKSPACE_ARTIFACT_OUTPUT_READY:
            invalid = result.workflow_run_id != input_dto.workflow_run_id
        else:
            observation = result.observation
            invalid = (
                observation.run_id != input_dto.workflow_run_id
                or observation.project_id != input_dto.projection.source_project_id
                or observation.project_title != input_dto.projection.title
                or observation.observed_manifest_revision
                != input_dto.projection.artifact_manifest_revision
                or observation.observed_script_revision
                != input_dto.projection.script_revision
                or observation.episode_count != input_dto.projection.episode_count
                or (
                    operation is INSPECT_STORY_WORKSPACE_ARTIFACT_INDEX
                    and result.write_status is not None
                )
                or (
                    operation is not INSPECT_STORY_WORKSPACE_ARTIFACT_INDEX
                    and result.write_status is None
                )
            )
        if invalid:
            raise invalid_response(request_id, write=write)
        return result

    def execute(self, operation, input_dto, request_id: str, *, access_token: str):
        if not any(operation is item for item in STORY_WORKSPACE_ARTIFACT_OPERATIONS):
            raise AdminDataError("ADMIN_OPERATION_CONTRACT_INVALID", 503, request_id)
        if type(input_dto) is not operation.input_dto:
            raise AdminDataError("ADMIN_OPERATION_INPUT_INVALID", 400, request_id)
        require_story_workspace_artifact_capabilities(self._client, request_id)
        result = self._client.execute(
            operation, input_dto, request_id, access_token=access_token
        )
        return self._validate(
            operation, input_dto, result, request_id,
            write=operation.capability.kind == "write",
        )

    def receipt(self, operation, input_dto, request_id: str, *, access_token: str):
        if operation.capability.kind != "write" or not any(
            operation is item for item in STORY_WORKSPACE_ARTIFACT_OPERATIONS
        ):
            raise AdminDataError("ADMIN_OPERATION_CONTRACT_INVALID", 503, request_id)
        if type(input_dto) is not operation.input_dto:
            raise AdminDataError("ADMIN_OPERATION_INPUT_INVALID", 400, request_id)
        require_story_workspace_artifact_capabilities(self._client, request_id)
        result = self._client.receipt(
            operation, request_id, access_token=access_token
        )
        if isinstance(result, CommittedReceiptDTO):
            self._validate(
                operation, input_dto, result.result, request_id, write=True
            )
        return result

    def write_recovering(self, operation, input_dto, request_id: str,
                         *, access_token: str):
        try:
            return self.execute(
                operation, input_dto, request_id, access_token=access_token
            )
        except AdminDataError as error:
            if not error.outcome_unknown:
                raise
            original_request_id = request_id
        try:
            receipt = self.receipt(
                operation, input_dto, original_request_id,
                access_token=access_token,
            )
        except AdminDataError as error:
            raise AdminDataError(
                error.code, error.status_code, original_request_id, True,
                error.details,
            ) from None
        if not isinstance(receipt, CommittedReceiptDTO):
            raise AdminDataError(
                "ADMIN_WRITE_RESULT_UNKNOWN", 503, original_request_id, True
            )
        return receipt.result

    def list_runs(self, input_dto: StoryWorkspaceArtifactRunsInputDTO,
                  request_id: str, *, access_token: str):
        return self.execute(
            LIST_STORY_WORKSPACE_ARTIFACT_RUNS,
            input_dto,
            request_id,
            access_token=access_token,
        )

    def authority(self, input_dto: StoryWorkspaceArtifactAuthorityInputDTO,
                  request_id: str, *, access_token: str):
        return self.execute(
            READ_STORY_WORKSPACE_ARTIFACT_AUTHORITY,
            input_dto,
            request_id,
            access_token=access_token,
        )

    def inspect_index(self, input_dto: StoryWorkspaceArtifactIndexInputDTO,
                      request_id: str, *, access_token: str):
        return self.execute(
            INSPECT_STORY_WORKSPACE_ARTIFACT_INDEX,
            input_dto,
            request_id,
            access_token=access_token,
        )

    def reconcile_index(
        self,
        input_dto: StoryWorkspaceArtifactIndexReconcileInputDTO,
        request_id: str,
        *,
        access_token: str,
    ):
        return self.write_recovering(
            RECONCILE_STORY_WORKSPACE_ARTIFACT_INDEX,
            input_dto,
            request_id,
            access_token=access_token,
        )


__all__ = [
    "AdminStoryWorkspaceArtifactData",
    "AdminStoryWorkspaceArtifactProvider",
    "ENSURE_STORY_WORKSPACE_EPISODE_AUTHORITY",
    "INSPECT_STORY_WORKSPACE_ARTIFACT_INDEX",
    "LIST_STORY_WORKSPACE_ARTIFACT_RUNS",
    "MARK_STORY_WORKSPACE_ARTIFACT_OUTPUT_READY",
    "MATERIALIZE_STORY_WORKSPACE_ARTIFACT_INDEX",
    "READ_STORY_WORKSPACE_ARTIFACT_AUTHORITY",
    "RECONCILE_STORY_WORKSPACE_ARTIFACT_INDEX",
    "STORY_WORKSPACE_ARTIFACT_OPERATIONS",
    "StoryWorkspaceArtifactAuthorityDTO",
    "StoryWorkspaceArtifactAuthorityInputDTO",
    "StoryWorkspaceArtifactIndexInputDTO",
    "StoryWorkspaceArtifactIndexObservationDTO",
    "StoryWorkspaceArtifactIndexOutputDTO",
    "StoryWorkspaceArtifactIndexReconcileInputDTO",
    "StoryWorkspaceArtifactOutputReadyInputDTO",
    "StoryWorkspaceArtifactProjectionDTO",
    "StoryWorkspaceArtifactRunsInputDTO",
    "StoryWorkspaceArtifactRunsOutputDTO",
    "StoryWorkspaceEpisodeAuthorityDTO",
    "StoryWorkspaceEpisodeAuthorityEnsureInputDTO",
]
