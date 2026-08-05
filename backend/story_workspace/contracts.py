"""Canonical contracts for the Story Workspace domain.

This module owns the data shapes shared by Story Workspace API, review, and
Agent-integration layers. Persistence and business workflows remain in their
respective router and service modules.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
from typing import Annotated, Any, Dict, Generic, List, Literal, Optional, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)


STORY_WORKSPACE_CONTRACT_VERSION = "1.2.0"
STORY_WORKSPACE_REVIEW_NOTES_MAX_LENGTH = 2000
STORY_WORKSPACE_GUIDANCE_TEXT_MAX_LENGTH = 4000
STORY_WORKSPACE_GUIDANCE_IDEMPOTENCY_KEY_MAX_LENGTH = 255
# Implementation guardrails: design_006 requires bounded file/list sizes but
# intentionally does not assign numeric policy values. Keep these centralized
# so a later product/security decision can revise them without schema drift.
STORY_WORKSPACE_DREAM_FILE_MAX_BYTES = 1024 * 1024
STORY_WORKSPACE_DREAM_SOURCE_FILES_MAX = 256
STORY_WORKSPACE_DREAM_ITEMS_MAX = 1000
STORY_WORKSPACE_DREAM_RELATIONS_MAX = 100
STORY_WORKSPACE_DREAM_EDITS_MAX = 1000
STORY_WORKSPACE_DREAM_EDIT_FIELDS_MAX = 64
STORY_WORKSPACE_DREAM_AGENT_MESSAGE_TEXT_MAX = 4000
STORY_WORKSPACE_DREAM_AGENT_TOOL_CALL_ID_MAX = 255
STORY_WORKSPACE_DREAM_AGENT_TOOL_REASON_MAX = 500
STORY_WORKSPACE_DREAM_AGENT_TOOL_ANSWERS_MAX_BYTES = 8192
STORY_WORKSPACE_DREAM_AGENT_TOOL_ANSWERS_MAX = 20
STORY_WORKSPACE_DREAM_AGENT_QUESTION_ID_MAX = 128
STORY_WORKSPACE_DREAM_AGENT_QUESTION_KEY_MAX = 300
STORY_WORKSPACE_DREAM_AGENT_QUESTION_OPTION_MAX = 120
STORY_WORKSPACE_DREAM_AGENT_QUESTION_PLACEHOLDER_MAX = 160
STORY_WORKSPACE_DREAM_AGENT_ANSWER_TEXT_MAX = 1000
_StoryWorkspaceDreamPositiveInt = Annotated[StrictInt, Field(ge=1)]
_StoryWorkspaceDreamNonNegativeInt = Annotated[StrictInt, Field(ge=0)]


def _story_workspace_to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class StoryWorkspaceReviewStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class StoryWorkspaceContentStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class StoryWorkspaceAssetStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class StoryWorkspaceStoryType(str, Enum):
    SHORT = "short"
    LONG = "long"
    SCRIPT = "script"
    OUTLINE = "outline"


class StoryWorkspaceRoleType(str, Enum):
    PROTAGONIST = "protagonist"
    SUPPORTING = "supporting"
    EXTRA = "extra"


class StoryWorkspaceBatchAction(str, Enum):
    CONFIRM = "confirm"
    REJECT = "reject"
    ARCHIVE = "archive"


class StoryWorkspaceReviewEventAction(str, Enum):
    """ReviewEvent audit action vocabulary (contract layer only, no DDL).

    ``GUIDE`` is the Dream Surface extension: every submitted guidance command
    is one ReviewEvent with action ``guide``; persistence reuses
    ``chat_message.metadata`` (DEC-032) instead of a new table.
    """

    CONFIRM = "confirm"
    REJECT = "reject"
    ARCHIVE = "archive"
    GUIDE = "guide"


class StoryWorkspaceGuidanceKind(str, Enum):
    RETRY_STEP = "retry-step"
    FREE_TEXT = "free-text"


class StoryWorkspaceResourceType(str, Enum):
    STORY = "story"
    CHARACTER = "character"
    SCENE = "scene"


class StoryWorkspaceDreamStage(str, Enum):
    CHARACTERS = "characters"
    SCENES = "scenes"
    STORYBOARDS = "storyboards"


class StoryWorkspaceDreamRunLifecycle(str, Enum):
    """Durable, user-visible lifecycle projected for Dream re-entry only."""

    GENERATING = "generating"
    WAITING_CONFIRMATION = "waiting_confirmation"
    CONTINUING = "continuing"
    RECENT = "recent"


STORY_WORKSPACE_DREAM_REQUIRED_STAGES = (
    StoryWorkspaceDreamStage.CHARACTERS,
    StoryWorkspaceDreamStage.SCENES,
    StoryWorkspaceDreamStage.STORYBOARDS,
)

_STORY_WORKSPACE_DREAM_STAGE_TITLES = {
    StoryWorkspaceDreamStage.CHARACTERS: "人物",
    StoryWorkspaceDreamStage.SCENES: "场景",
    StoryWorkspaceDreamStage.STORYBOARDS: "分镜",
}


def _dream_stage_entry_route(
    stage: StoryWorkspaceDreamStage,
    run_id: str,
) -> str:
    routes = {
        StoryWorkspaceDreamStage.CHARACTERS: (
            f"/story-workspace/characters?run={run_id}"
        ),
        StoryWorkspaceDreamStage.SCENES: (
            f"/story-workspace/scenes?run={run_id}"
        ),
        StoryWorkspaceDreamStage.STORYBOARDS: (
            f"/story-workspace/runs/{run_id}/execution"
        ),
    }
    return routes[stage]


def _validate_dream_relations(values: list[str]) -> list[str]:
    if any(not value or len(value) > 128 for value in values):
        raise ValueError(
            "relations must contain non-blank identifiers <= 128 chars"
        )
    return values


def _validate_dream_source_files(values: list[str]) -> list[str]:
    if len(values) != len(set(values)):
        raise ValueError("source_files must not contain duplicates")
    return values


def _validate_dream_stage_items(
    source_files: list[str],
    items: list[Any],
) -> None:
    if any(item.source_file not in source_files for item in items):
        raise ValueError("every item source_file must be declared in source_files")
    entity_ids = [item.entity_id for item in items]
    if len(entity_ids) != len(set(entity_ids)):
        raise ValueError("items must have unique entity_id values within a stage")


class _StoryWorkspaceDreamStorageModel(BaseModel):
    """Strict snake_case-only model for canonical runtime JSON files."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )


class _StoryWorkspaceDreamWireModel(BaseModel):
    """Strict REST model with explicit snake_case ↔ camelCase boundary."""

    model_config = ConfigDict(
        alias_generator=_story_workspace_to_camel,
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class StoryWorkspaceDreamLaunchCommand(_StoryWorkspaceDreamWireModel):
    """The complete untrusted request surface for starting a Dream run."""

    model_config = ConfigDict(
        alias_generator=_story_workspace_to_camel,
        extra="forbid",
        frozen=True,
        populate_by_name=False,
        str_strip_whitespace=False,
        validate_by_alias=True,
        validate_by_name=False,
    )

    deck_id: str = Field(min_length=1, max_length=255)
    goal: str = Field(min_length=1, max_length=12000)
    idempotency_key: str = Field(
        min_length=1,
        max_length=255,
        pattern=r"^[A-Za-z0-9._:-]+$",
    )

    @field_validator("deck_id", "goal", "idempotency_key")
    @classmethod
    def launch_values_have_no_boundary_whitespace(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("Dream launch fields must not contain boundary whitespace")
        return value


class StoryWorkspaceDreamRunContext(BaseModel):
    """Server-derived provenance injected into one Dream Agent turn.

    This is an internal trust-boundary contract, not a client-authored request.
    Every field is frozen from the authoritative run and its Deck binding.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )

    workflow_run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    thread_id: str = Field(min_length=1, max_length=255)
    deck_id: str = Field(min_length=1, max_length=255)
    deck_plugin_id: str = Field(min_length=1, max_length=255)
    deck_plugin_version: str = Field(min_length=1, max_length=255)
    deck_plugin_binding_id: str = Field(min_length=1, max_length=255)
    binding_revision: _StoryWorkspaceDreamPositiveInt
    deck_runtime_snapshot_id: str = Field(min_length=1, max_length=255)
    runtime_plugin_lock_id: str = Field(min_length=1, max_length=255)


class StoryWorkspaceDreamLaunchAccepted(_StoryWorkspaceDreamWireModel):
    """Canonical 201 response for a host-started Dream Agent turn."""

    status: Literal["accepted"] = "accepted"
    workflow_run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    thread_id: str = Field(min_length=1, max_length=255)
    deck_id: str = Field(min_length=1, max_length=255)
    deck_plugin_id: str = Field(min_length=1, max_length=255)
    deck_plugin_version: str = Field(min_length=1, max_length=255)
    deck_plugin_binding_id: str = Field(min_length=1, max_length=255)
    binding_revision: _StoryWorkspaceDreamPositiveInt
    deck_runtime_snapshot_id: str = Field(min_length=1, max_length=255)
    runtime_plugin_lock_id: str = Field(min_length=1, max_length=255)

    @classmethod
    def from_context(
        cls,
        context: StoryWorkspaceDreamRunContext,
    ) -> "StoryWorkspaceDreamLaunchAccepted":
        return cls.model_validate(context.model_dump(mode="json"))


class StoryWorkspaceDreamAgentMessageCommand(_StoryWorkspaceDreamWireModel):
    """Untrusted text command for the run-bound Dream Agent widget."""

    text: str = Field(min_length=1, max_length=STORY_WORKSPACE_DREAM_AGENT_MESSAGE_TEXT_MAX)
    idempotency_key: str = Field(
        min_length=1,
        max_length=255,
        pattern=r"^[A-Za-z0-9._:-]+$",
    )

    @field_validator("text")
    @classmethod
    def message_text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Dream Agent message text must not be blank")
        return value


class StoryWorkspaceDreamAgentMessage(_StoryWorkspaceDreamWireModel):
    """Safe, text-only message projection for the Dream workbench."""

    id: str = Field(min_length=1, max_length=255)
    role: Literal["user", "assistant"]
    text: str = Field(min_length=1, max_length=STORY_WORKSPACE_DREAM_AGENT_MESSAGE_TEXT_MAX)
    truncated: bool = False
    created_at: datetime


class StoryWorkspaceDreamAgentMessageSnapshot(_StoryWorkspaceDreamWireModel):
    """Persisted safe history plus transient execution availability."""

    story_workspace_run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    lifecycle: Literal["idle", "streaming"]
    active_turn_id: Optional[str] = Field(default=None, max_length=255)
    can_send: bool
    send_block_reason: Optional[
        Literal["generating", "waiting_confirmation", "confirming", "continuing", "busy"]
    ] = None
    messages: list[StoryWorkspaceDreamAgentMessage]
    snapshot_at: datetime


class StoryWorkspaceDreamAgentMessageAccepted(_StoryWorkspaceDreamWireModel):
    """Acknowledge one durable, idempotently claimed widget command."""

    story_workspace_run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    message_id: str = Field(min_length=1, max_length=255)
    accepted: Literal[True] = True


_StoryWorkspaceDreamToolAnswerText = Annotated[
    StrictStr,
    Field(max_length=STORY_WORKSPACE_DREAM_AGENT_ANSWER_TEXT_MAX),
]
_StoryWorkspaceDreamToolAnswerInteger = Annotated[
    StrictInt,
    Field(ge=-1_000_000_000, le=1_000_000_000),
]
_StoryWorkspaceDreamToolAnswerValue = (
    _StoryWorkspaceDreamToolAnswerText
    | StrictBool
    | _StoryWorkspaceDreamToolAnswerInteger
    | Annotated[list[_StoryWorkspaceDreamToolAnswerText], Field(max_length=20)]
)


class StoryWorkspaceDreamAgentToolConfirmationCommand(_StoryWorkspaceDreamWireModel):
    """Untrusted decision for one pending tool on the run-bound Dream turn."""

    tool_call_id: str = Field(
        min_length=1,
        max_length=STORY_WORKSPACE_DREAM_AGENT_TOOL_CALL_ID_MAX,
        pattern=r"^[A-Za-z0-9._:/-]+$",
    )
    approved: StrictBool
    reason: Optional[str] = Field(
        default=None,
        max_length=STORY_WORKSPACE_DREAM_AGENT_TOOL_REASON_MAX,
    )
    answers: Optional[
        dict[
            Annotated[
                StrictStr,
                Field(
                    min_length=1,
                    max_length=STORY_WORKSPACE_DREAM_AGENT_QUESTION_KEY_MAX,
                ),
            ],
            _StoryWorkspaceDreamToolAnswerValue,
        ]
    ] = Field(default=None, max_length=STORY_WORKSPACE_DREAM_AGENT_TOOL_ANSWERS_MAX)

    @model_validator(mode="after")
    def validate_tool_confirmation_payload(
        self,
    ) -> "StoryWorkspaceDreamAgentToolConfirmationCommand":
        if self.reason is not None and not self.reason.strip():
            raise ValueError("reason must not be blank")
        if self.answers is not None:
            encoded = json.dumps(
                self.answers,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            if len(encoded) > STORY_WORKSPACE_DREAM_AGENT_TOOL_ANSWERS_MAX_BYTES:
                raise ValueError("answers payload is too large")
        return self


class StoryWorkspaceDreamAgentToolConfirmationAccepted(_StoryWorkspaceDreamWireModel):
    """Safe acknowledgement without exposing the hidden thread or tool input."""

    story_workspace_run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    tool_call_id: str = Field(
        min_length=1,
        max_length=STORY_WORKSPACE_DREAM_AGENT_TOOL_CALL_ID_MAX,
    )
    approved: StrictBool
    resolved: Literal[True] = True


class StoryWorkspaceDreamToolInput(BaseModel):
    """Canonical base for Agent-visible Dream MCP input contracts."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=False,
        str_strip_whitespace=True,
    )


class StoryWorkspaceDreamRunToolInput(StoryWorkspaceDreamToolInput):
    workflow_run_id: str = Field(
        alias="workflowRunId",
        pattern=r"^run_[0-9a-f]{32}$",
        description="Authoritative WorkflowRun ID supplied by the host-started flow.",
    )
    expected_revision: int = Field(
        alias="expectedRevision",
        ge=0,
        strict=True,
        description="Current run.json revision; use 0 when it does not exist.",
    )


class StoryWorkspaceDreamStageItemToolInput(StoryWorkspaceDreamToolInput):
    entity_id: str = Field(alias="entityId", min_length=1, max_length=128)
    display_name: str = Field(alias="displayName", min_length=1, max_length=200)
    summary: Optional[str] = Field(default=None, max_length=4000)
    source_file: str = Field(alias="sourceFile", min_length=1, max_length=1024)
    relations: list[str] = Field(
        default_factory=list,
        max_length=STORY_WORKSPACE_DREAM_RELATIONS_MAX,
    )


class StoryWorkspaceDreamStageToolInput(StoryWorkspaceDreamToolInput):
    workflow_run_id: str = Field(
        alias="workflowRunId",
        pattern=r"^run_[0-9a-f]{32}$",
        description="Authoritative WorkflowRun ID supplied by the host-started flow.",
    )
    stage: StoryWorkspaceDreamStage = Field(
        description="One canonical Dream stage: characters, scenes, or storyboards."
    )
    source_files: list[str] = Field(
        alias="sourceFiles",
        min_length=1,
        max_length=STORY_WORKSPACE_DREAM_SOURCE_FILES_MAX,
        description="Existing canonical workspace files represented by this stage.",
    )
    items: list[StoryWorkspaceDreamStageItemToolInput] = Field(
        default_factory=list,
        max_length=STORY_WORKSPACE_DREAM_ITEMS_MAX,
        description="Normalized entities rendered by the corresponding Dream page.",
    )
    expected_revision: int = Field(
        alias="expectedRevision",
        ge=0,
        strict=True,
        description="Current stage file revision; use 0 when it does not exist.",
    )


class StoryWorkspaceDreamSource(_StoryWorkspaceDreamStorageModel):
    deck_plugin_binding_id: str = Field(min_length=1, max_length=255)
    binding_revision: _StoryWorkspaceDreamPositiveInt
    deck_plugin_version: str = Field(min_length=1, max_length=255)
    deck_runtime_snapshot_id: str = Field(min_length=1, max_length=255)
    runtime_plugin_lock_id: str = Field(min_length=1, max_length=255)


class StoryWorkspaceDreamRunFile(_StoryWorkspaceDreamStorageModel):
    """Canonical snake_case payload persisted as ``run.json``."""

    schema_version: Literal["dream-run/v1"] = "dream-run/v1"
    workflow_run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    thread_id: str = Field(min_length=1, max_length=255)
    source: StoryWorkspaceDreamSource
    projection_entry: str = Field(min_length=1, max_length=512)
    required_stages: list[StoryWorkspaceDreamStage] = Field(
        default_factory=lambda: list(STORY_WORKSPACE_DREAM_REQUIRED_STAGES),
        min_length=3,
        max_length=3,
    )
    revision: _StoryWorkspaceDreamPositiveInt

    @model_validator(mode="after")
    def fixed_run_fields_are_canonical(self) -> "StoryWorkspaceDreamRunFile":
        if tuple(self.required_stages) != STORY_WORKSPACE_DREAM_REQUIRED_STAGES:
            raise ValueError("required_stages must contain the three canonical stages")
        expected_entry = (
            f"/api/story-workspace/workflow-runs/{self.workflow_run_id}/dream-files"
        )
        if self.projection_entry != expected_entry:
            raise ValueError("projection_entry does not match workflow_run_id")
        return self


class StoryWorkspaceDreamStagePage(_StoryWorkspaceDreamStorageModel):
    title: str = Field(min_length=1, max_length=200)
    entry_route: str = Field(min_length=1, max_length=512)


class StoryWorkspaceDreamStageItem(_StoryWorkspaceDreamStorageModel):
    entity_id: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=200)
    summary: Optional[str] = Field(default=None, max_length=4000)
    source_file: str = Field(min_length=1, max_length=1024)
    relations: list[str] = Field(
        default_factory=list,
        max_length=STORY_WORKSPACE_DREAM_RELATIONS_MAX,
    )

    @field_validator("relations")
    @classmethod
    def relations_are_bounded(cls, values: list[str]) -> list[str]:
        return _validate_dream_relations(values)


class StoryWorkspaceDreamStageFile(_StoryWorkspaceDreamStorageModel):
    """Canonical snake_case payload persisted in ``stages/<stage>.json``."""

    schema_version: Literal["dream-stage/v1"] = "dream-stage/v1"
    workflow_run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    stage: StoryWorkspaceDreamStage
    revision: _StoryWorkspaceDreamPositiveInt
    source_files: list[str] = Field(
        min_length=1,
        max_length=STORY_WORKSPACE_DREAM_SOURCE_FILES_MAX,
    )
    page: StoryWorkspaceDreamStagePage
    items: list[StoryWorkspaceDreamStageItem] = Field(
        default_factory=list,
        max_length=STORY_WORKSPACE_DREAM_ITEMS_MAX,
    )

    @field_validator("source_files")
    @classmethod
    def source_files_are_unique(cls, values: list[str]) -> list[str]:
        return _validate_dream_source_files(values)

    @model_validator(mode="after")
    def fixed_stage_fields_are_canonical(self) -> "StoryWorkspaceDreamStageFile":
        if self.page.title != _STORY_WORKSPACE_DREAM_STAGE_TITLES[self.stage]:
            raise ValueError("page.title does not match stage")
        if self.page.entry_route != _dream_stage_entry_route(
            self.stage,
            self.workflow_run_id,
        ):
            raise ValueError(
                "page.entry_route does not match stage and workflow_run_id"
            )
        _validate_dream_stage_items(self.source_files, self.items)
        return self


class StoryWorkspaceDreamSourceResponse(_StoryWorkspaceDreamWireModel):
    deck_plugin_binding_id: str = Field(min_length=1, max_length=255)
    binding_revision: _StoryWorkspaceDreamPositiveInt
    deck_plugin_version: str = Field(min_length=1, max_length=255)
    deck_runtime_snapshot_id: str = Field(min_length=1, max_length=255)
    runtime_plugin_lock_id: str = Field(min_length=1, max_length=255)


class StoryWorkspaceDreamStagePageResponse(_StoryWorkspaceDreamWireModel):
    title: str = Field(min_length=1, max_length=200)
    entry_route: str = Field(min_length=1, max_length=512)


class StoryWorkspaceDreamStageItemResponse(_StoryWorkspaceDreamWireModel):
    entity_id: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=200)
    summary: Optional[str] = Field(default=None, max_length=4000)
    source_file: str = Field(min_length=1, max_length=1024)
    relations: list[str] = Field(
        default_factory=list,
        max_length=STORY_WORKSPACE_DREAM_RELATIONS_MAX,
    )

    @field_validator("relations")
    @classmethod
    def response_relations_are_bounded(cls, values: list[str]) -> list[str]:
        return _validate_dream_relations(values)


class StoryWorkspaceDreamStageResponse(_StoryWorkspaceDreamWireModel):
    stage: StoryWorkspaceDreamStage
    revision: _StoryWorkspaceDreamPositiveInt
    source_files: list[str] = Field(
        min_length=1,
        max_length=STORY_WORKSPACE_DREAM_SOURCE_FILES_MAX,
    )
    page: StoryWorkspaceDreamStagePageResponse
    items: list[StoryWorkspaceDreamStageItemResponse] = Field(
        default_factory=list,
        max_length=STORY_WORKSPACE_DREAM_ITEMS_MAX,
    )

    @field_validator("source_files")
    @classmethod
    def response_source_files_are_unique(cls, values: list[str]) -> list[str]:
        return _validate_dream_source_files(values)

    @model_validator(mode="after")
    def response_stage_fields_are_canonical(
        self,
    ) -> "StoryWorkspaceDreamStageResponse":
        route_patterns = {
            StoryWorkspaceDreamStage.CHARACTERS: (
                r"^/story-workspace/characters\?run=run_[0-9a-f]{32}$"
            ),
            StoryWorkspaceDreamStage.SCENES: (
                r"^/story-workspace/scenes\?run=run_[0-9a-f]{32}$"
            ),
            StoryWorkspaceDreamStage.STORYBOARDS: (
                r"^/story-workspace/runs/run_[0-9a-f]{32}/execution$"
            ),
        }
        if self.page.title != _STORY_WORKSPACE_DREAM_STAGE_TITLES[self.stage]:
            raise ValueError("page.title does not match stage")
        import re

        if re.fullmatch(route_patterns[self.stage], self.page.entry_route) is None:
            raise ValueError("page.entry_route is not canonical for stage")
        _validate_dream_stage_items(self.source_files, self.items)
        return self


class StoryWorkspaceDreamFilesResponse(_StoryWorkspaceDreamWireModel):
    story_workspace_run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    thread_id: str = Field(min_length=1, max_length=255)
    source: StoryWorkspaceDreamSourceResponse
    required_stages: list[StoryWorkspaceDreamStage] = Field(
        min_length=3,
        max_length=3,
    )
    run_revision: _StoryWorkspaceDreamNonNegativeInt
    stages: dict[StoryWorkspaceDreamStage, StoryWorkspaceDreamStageResponse]
    can_confirm: bool
    confirmation_accepted: bool = False
    confirmation_dispatched: bool = False
    confirmation_label: Literal["确认并继续"] = "确认并继续"

    @model_validator(mode="after")
    def confirmation_matches_file_completeness(
        self,
    ) -> "StoryWorkspaceDreamFilesResponse":
        if tuple(self.required_stages) != STORY_WORKSPACE_DREAM_REQUIRED_STAGES:
            raise ValueError("required_stages must contain the three canonical stages")
        if any(key is not value.stage for key, value in self.stages.items()):
            raise ValueError("each stages key must match its nested stage value")
        if any(
            value.page.entry_route
            != _dream_stage_entry_route(stage, self.story_workspace_run_id)
            for stage, value in self.stages.items()
        ):
            raise ValueError(
                "each stage entry route must match story_workspace_run_id"
            )
        if self.run_revision == 0 and self.stages:
            raise ValueError(
                "waiting projections without run.json cannot contain stages"
            )
        if self.confirmation_dispatched and not self.confirmation_accepted:
            raise ValueError(
                "confirmation_dispatched requires confirmation_accepted"
            )
        expected = set(STORY_WORKSPACE_DREAM_REQUIRED_STAGES)
        expected_can_confirm = (
            set(self.stages) == expected and not self.confirmation_accepted
        )
        if self.can_confirm != expected_can_confirm:
            raise ValueError(
                "can_confirm must reflect completeness and persisted confirmation"
            )
        return self


class StoryWorkspaceDreamReentryItem(_StoryWorkspaceDreamWireModel):
    """One permission-checked Dream run rendered by the canonical workbench."""

    story_workspace_run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    goal_prefix: str = Field(min_length=1, max_length=80)
    deck_id: str = Field(min_length=1, max_length=255)
    deck_display_name: str = Field(min_length=1, max_length=255)
    workflow_display_name: Literal["Dream"] = "Dream"
    deck_plugin_version: str = Field(min_length=1, max_length=255)
    lifecycle: StoryWorkspaceDreamRunLifecycle
    group: Literal["in_progress", "recent"]
    stage_revisions: dict[StoryWorkspaceDreamStage, _StoryWorkspaceDreamNonNegativeInt]
    confirmation_accepted: bool
    confirmation_dispatched: bool
    last_activity_at: datetime
    created_at: datetime
    sort_key: str = Field(min_length=1, max_length=512)
    href: str = Field(pattern=r"^/story-workspace/dream\?run=run_[0-9a-f]{32}$")

    @model_validator(mode="after")
    def lifecycle_matches_confirmation_facts(
        self,
    ) -> "StoryWorkspaceDreamReentryItem":
        if self.confirmation_dispatched and not self.confirmation_accepted:
            raise ValueError("confirmation_dispatched requires confirmation_accepted")
        if self.lifecycle is StoryWorkspaceDreamRunLifecycle.RECENT:
            if self.group != "recent" or not self.confirmation_dispatched:
                raise ValueError("recent requires dispatched confirmation")
        elif self.group != "in_progress":
            raise ValueError("non-recent lifecycle must be in_progress")
        return self


class StoryWorkspaceDreamReentryCollection(_StoryWorkspaceDreamWireModel):
    """Canonical actor-scoped collection; ordering is server-owned."""

    runs: list[StoryWorkspaceDreamReentryItem] = Field(default_factory=list)


class StoryWorkspaceDreamEdit(_StoryWorkspaceDreamWireModel):
    stage: StoryWorkspaceDreamStage
    entity_id: str = Field(min_length=1, max_length=128)
    fields: dict[str, Any] = Field(
        min_length=1,
        max_length=STORY_WORKSPACE_DREAM_EDIT_FIELDS_MAX,
    )

    @field_validator("fields")
    @classmethod
    def edit_fields_are_safe_json(cls, values: dict[str, Any]) -> dict[str, Any]:
        for key in values:
            if not key or len(key) > 128:
                raise ValueError("edit field names must be 1..128 characters")
        try:
            import json

            encoded = json.dumps(values, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("edit fields must be finite JSON values") from exc
        if len(encoded.encode("utf-8")) > 64 * 1024:
            raise ValueError("one edit fields payload must be at most 64 KiB")
        return values


class StoryWorkspaceDreamConfirmationCommand(_StoryWorkspaceDreamWireModel):
    story_workspace_run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    thread_id: str = Field(min_length=1, max_length=255)
    base_revisions: dict[StoryWorkspaceDreamStage, _StoryWorkspaceDreamPositiveInt]
    edits: list[StoryWorkspaceDreamEdit] = Field(
        default_factory=list,
        max_length=STORY_WORKSPACE_DREAM_EDITS_MAX,
    )
    idempotency_key: str = Field(
        pattern=r"^swc_[A-Za-z0-9._:-]+$",
        min_length=5,
        max_length=255,
    )

    @field_validator("base_revisions")
    @classmethod
    def all_base_revisions_are_present(
        cls,
        values: dict[StoryWorkspaceDreamStage, int],
    ) -> dict[StoryWorkspaceDreamStage, int]:
        if set(values) != set(STORY_WORKSPACE_DREAM_REQUIRED_STAGES):
            raise ValueError("base_revisions must contain all three required stages")
        if any(isinstance(value, bool) or value < 1 for value in values.values()):
            raise ValueError("base revisions must be positive integers")
        return values


class StoryWorkspaceDreamConfirmationAccepted(_StoryWorkspaceDreamWireModel):
    """202 response for one persisted Dream confirmation command."""

    message_id: str = Field(min_length=1, max_length=255)
    story_workspace_run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    thread_id: str = Field(min_length=1, max_length=255)
    status: Literal["accepted"] = "accepted"
    replayed: bool
    dispatched: bool
    request_id: str = Field(min_length=1, max_length=255)


@dataclass
class StoryWorkspaceStory:
    id: str
    identifier: str
    title: str
    description: Optional[str] = None
    status: StoryWorkspaceContentStatus = StoryWorkspaceContentStatus.DRAFT
    review_status: StoryWorkspaceReviewStatus = StoryWorkspaceReviewStatus.PENDING
    type: StoryWorkspaceStoryType = StoryWorkspaceStoryType.SHORT
    content: Optional[str] = None
    author_id: int = 0
    workspace_id: str = ""
    character_count: int = 0
    scene_count: int = 0
    agent_generated: bool = True
    agent_session_id: Optional[str] = None
    review_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    published_at: Optional[datetime] = None


@dataclass
class StoryWorkspaceCharacter:
    id: str
    identifier: str
    name: str
    avatar_url: Optional[str] = None
    identity: Optional[str] = None
    personality: Optional[str] = None
    background: Optional[str] = None
    catchphrase: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    author_id: int = 0
    workspace_id: str = ""
    story_count: int = 0
    review_status: StoryWorkspaceReviewStatus = StoryWorkspaceReviewStatus.PENDING
    agent_generated: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    status: StoryWorkspaceAssetStatus = StoryWorkspaceAssetStatus.ACTIVE
    review_notes: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None


@dataclass
class StoryWorkspaceScene:
    id: str
    identifier: str
    name: str
    description: Optional[str] = None
    story_id: Optional[str] = None
    author_id: int = 0
    workspace_id: str = ""
    character_count: int = 0
    order_index: int = 0
    review_status: StoryWorkspaceReviewStatus = StoryWorkspaceReviewStatus.PENDING
    agent_generated: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    status: StoryWorkspaceAssetStatus = StoryWorkspaceAssetStatus.ACTIVE
    review_notes: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None


@dataclass
class StoryWorkspaceWorkspace:
    id: str
    name: str
    owner_id: int
    settings: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class StoryWorkspaceStoryCharacter:
    story_id: str
    character_id: str
    role_type: StoryWorkspaceRoleType = StoryWorkspaceRoleType.SUPPORTING
    created_at: Optional[datetime] = None


@dataclass
class StoryWorkspaceSceneCharacter:
    scene_id: str
    character_id: str
    created_at: Optional[datetime] = None


@dataclass
class StoryWorkspaceStoryDetail(StoryWorkspaceStory):
    characters: List[StoryWorkspaceCharacter] = field(default_factory=list)
    scenes: List[StoryWorkspaceScene] = field(default_factory=list)


@dataclass
class StoryWorkspaceCharacterDetail(StoryWorkspaceCharacter):
    stories: List[StoryWorkspaceStory] = field(default_factory=list)


@dataclass
class StoryWorkspaceSceneDetail(StoryWorkspaceScene):
    characters: List[StoryWorkspaceCharacter] = field(default_factory=list)
    story: Optional[StoryWorkspaceStory] = None


@dataclass
class StoryWorkspacePaginationInfo:
    page: int
    per_page: int
    total: int
    total_pages: int


T = TypeVar("T")


@dataclass
class StoryWorkspacePaginatedResponse(Generic[T]):
    data: List[T]
    pagination: StoryWorkspacePaginationInfo


@dataclass
class StoryWorkspaceStoryFilter:
    q: Optional[str] = None
    review_status: List[StoryWorkspaceReviewStatus] = field(default_factory=list)
    status: List[StoryWorkspaceContentStatus] = field(default_factory=list)
    type: List[StoryWorkspaceStoryType] = field(default_factory=list)
    sort: str = "updated_at"
    order: str = "desc"
    page: int = 1
    per_page: int = 20


@dataclass
class StoryWorkspaceCharacterFilter:
    q: Optional[str] = None
    review_status: List[StoryWorkspaceReviewStatus] = field(default_factory=list)
    sort: str = "updated_at"
    order: str = "desc"
    page: int = 1
    per_page: int = 20


@dataclass
class StoryWorkspaceSceneFilter:
    q: Optional[str] = None
    review_status: List[StoryWorkspaceReviewStatus] = field(default_factory=list)
    story_id: Optional[str] = None
    sort: str = "updated_at"
    order: str = "desc"
    page: int = 1
    per_page: int = 20


@dataclass
class StoryWorkspaceReviewActionRequest:
    review_notes: Optional[str] = None

    def __post_init__(self) -> None:
        _validate_review_notes(self.review_notes)


@dataclass
class StoryWorkspaceBatchReviewRequest:
    action: StoryWorkspaceBatchAction
    ids: List[str]
    resource_type: StoryWorkspaceResourceType
    review_notes: Optional[str] = None

    def __post_init__(self) -> None:
        _validate_review_notes(self.review_notes)


def _validate_review_notes(review_notes: Optional[str]) -> None:
    if (
        review_notes is not None
        and len(review_notes) > STORY_WORKSPACE_REVIEW_NOTES_MAX_LENGTH
    ):
        raise ValueError(
            "review_notes must be at most "
            f"{STORY_WORKSPACE_REVIEW_NOTES_MAX_LENGTH} characters"
        )


@dataclass
class StoryWorkspaceBatchReviewResponse:
    success: bool
    action: StoryWorkspaceBatchAction
    resource_type: StoryWorkspaceResourceType
    total_requested: int
    total_updated: int
    skipped_ids: List[str] = field(default_factory=list)
    updated_items: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class StoryWorkspaceStats:
    total_stories: int = 0
    total_characters: int = 0
    total_scenes: int = 0
    pending_review_count: int = 0
    confirmed_count: int = 0
    rejected_count: int = 0


@dataclass
class StoryWorkspaceAgentCharacterOutput:
    name: str
    identity: Optional[str] = None
    personality: Optional[str] = None
    background: Optional[str] = None
    catchphrase: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class StoryWorkspaceAgentSceneOutput:
    name: str
    description: Optional[str] = None
    order_index: int = 0


@dataclass
class StoryWorkspaceAgentStoryOutput:
    title: str
    description: Optional[str] = None
    type: StoryWorkspaceStoryType = StoryWorkspaceStoryType.SHORT
    content: Optional[str] = None
    characters: List[StoryWorkspaceAgentCharacterOutput] = field(default_factory=list)
    scenes: List[StoryWorkspaceAgentSceneOutput] = field(default_factory=list)


@dataclass
class StoryWorkspaceAgentOutputRequest(StoryWorkspaceAgentStoryOutput):
    """Direct request body accepted by the Agent-output integration endpoint."""


@dataclass(frozen=True)
class StoryWorkspaceSurface:
    """Business-level surface descriptor (design_004 §6 contract value object)."""

    name: str
    protocol_dir: str
    entry_route: str


@dataclass(frozen=True)
class StoryWorkspaceGuidanceCommand:
    """Domain-level guidance command handed to the guidance service."""

    run_id: str
    kind: StoryWorkspaceGuidanceKind
    idempotency_key: str
    actor: str
    text: Optional[str] = None
    step_id: Optional[str] = None


@dataclass
class StoryWorkspaceExecutionProjection:
    """Read-side execution facts projection consumed by the execution page.

    ``phase`` may carry projection states such as ``awaiting-guidance`` —
    inferred from ``continuing`` plus blocked-step markers — which are
    deliberately NOT ``RunStatus`` enum values (audit note D13).
    """

    run_id: str
    phase: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    assets_ref: Optional[str] = None
    events: List[Dict[str, Any]] = field(default_factory=list)


class StoryWorkspaceGuidanceCommandPayload(BaseModel):
    """Request body of ``POST /api/story-workspace/runs/{run_id}/guidance``.

    The client ``actor`` is a declared identity hint; the service rejects any
    mismatch with the authenticated actor (never trusted on its own).
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    kind: StoryWorkspaceGuidanceKind
    text: Optional[str] = Field(
        default=None, max_length=STORY_WORKSPACE_GUIDANCE_TEXT_MAX_LENGTH
    )
    step_id: Optional[str] = Field(default=None, min_length=1, max_length=128)
    idempotency_key: str = Field(
        min_length=1, max_length=STORY_WORKSPACE_GUIDANCE_IDEMPOTENCY_KEY_MAX_LENGTH
    )
    actor: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def kind_fields_are_consistent(self) -> "StoryWorkspaceGuidanceCommandPayload":
        if self.kind == StoryWorkspaceGuidanceKind.FREE_TEXT:
            if not self.text or not self.text.strip():
                raise ValueError("free-text guidance requires non-blank text")
        if self.kind == StoryWorkspaceGuidanceKind.RETRY_STEP and not self.step_id:
            raise ValueError("retry-step guidance requires step_id")
        return self

    def to_command(self, run_id: str) -> StoryWorkspaceGuidanceCommand:
        return StoryWorkspaceGuidanceCommand(
            run_id=run_id,
            kind=self.kind,
            idempotency_key=self.idempotency_key,
            actor=self.actor,
            text=self.text,
            step_id=self.step_id,
        )


class _StoryWorkspaceAgentPayload(BaseModel):
    """Ignore future Agent fields while keeping the canonical minimum."""

    model_config = ConfigDict(extra="ignore")


class StoryWorkspaceAgentCharacterPayload(_StoryWorkspaceAgentPayload):
    name: str
    identity: Optional[str] = None
    personality: Optional[str] = None
    background: Optional[str] = None
    catchphrase: Optional[str] = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def _non_empty_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value


class StoryWorkspaceAgentScenePayload(_StoryWorkspaceAgentPayload):
    name: str
    description: Optional[str] = None
    order_index: int = 0

    @field_validator("name")
    @classmethod
    def _non_empty_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value


class StoryWorkspaceAgentStoryPayload(_StoryWorkspaceAgentPayload):
    title: str
    description: Optional[str] = None
    type: Literal["short", "long", "script", "outline"] = "short"
    content: Optional[str] = None
    characters: list[StoryWorkspaceAgentCharacterPayload] = Field(default_factory=list)
    scenes: list[StoryWorkspaceAgentScenePayload] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def _non_empty_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value


class _StoryWorkspaceControlledPatch(BaseModel):
    """Reject unknown fields so authoritative values cannot be patched indirectly."""

    model_config = ConfigDict(extra="forbid")


class StoryWorkspaceWorkspacePatch(_StoryWorkspaceControlledPatch):
    name: str = None  # type: ignore[assignment]
    settings: dict[str, Any] = None  # type: ignore[assignment]


class StoryWorkspaceStoryPatch(_StoryWorkspaceControlledPatch):
    title: str = None  # type: ignore[assignment]
    description: Optional[str] = None
    content: Optional[str] = None
    type: Literal["short", "long", "script", "outline"] = None  # type: ignore[assignment]


class StoryWorkspaceCharacterPatch(_StoryWorkspaceControlledPatch):
    name: str = None  # type: ignore[assignment]
    identity: Optional[str] = None
    personality: Optional[str] = None
    background: Optional[str] = None
    catchphrase: Optional[str] = None
    tags: list[str] = None  # type: ignore[assignment]
    avatar_url: Optional[str] = None


class StoryWorkspaceScenePatch(_StoryWorkspaceControlledPatch):
    name: str = None  # type: ignore[assignment]
    description: Optional[str] = None
    story_id: Optional[str] = None
    order_index: int = None  # type: ignore[assignment]


__all__ = [
    "STORY_WORKSPACE_CONTRACT_VERSION",
    "STORY_WORKSPACE_DREAM_EDITS_MAX",
    "STORY_WORKSPACE_DREAM_EDIT_FIELDS_MAX",
    "STORY_WORKSPACE_DREAM_FILE_MAX_BYTES",
    "STORY_WORKSPACE_DREAM_ITEMS_MAX",
    "STORY_WORKSPACE_DREAM_RELATIONS_MAX",
    "STORY_WORKSPACE_DREAM_REQUIRED_STAGES",
    "STORY_WORKSPACE_DREAM_SOURCE_FILES_MAX",
    "STORY_WORKSPACE_GUIDANCE_IDEMPOTENCY_KEY_MAX_LENGTH",
    "STORY_WORKSPACE_GUIDANCE_TEXT_MAX_LENGTH",
    "STORY_WORKSPACE_REVIEW_NOTES_MAX_LENGTH",
    "StoryWorkspaceAgentCharacterOutput",
    "StoryWorkspaceAgentCharacterPayload",
    "StoryWorkspaceAgentOutputRequest",
    "StoryWorkspaceAgentSceneOutput",
    "StoryWorkspaceAgentScenePayload",
    "StoryWorkspaceAgentStoryOutput",
    "StoryWorkspaceAgentStoryPayload",
    "StoryWorkspaceBatchAction",
    "StoryWorkspaceBatchReviewRequest",
    "StoryWorkspaceBatchReviewResponse",
    "StoryWorkspaceAssetStatus",
    "StoryWorkspaceCharacter",
    "StoryWorkspaceCharacterDetail",
    "StoryWorkspaceCharacterFilter",
    "StoryWorkspaceCharacterPatch",
    "StoryWorkspaceContentStatus",
    "StoryWorkspaceDreamConfirmationAccepted",
    "StoryWorkspaceDreamConfirmationCommand",
    "StoryWorkspaceDreamAgentMessage",
    "StoryWorkspaceDreamAgentMessageAccepted",
    "StoryWorkspaceDreamAgentMessageCommand",
    "StoryWorkspaceDreamAgentMessageSnapshot",
    "StoryWorkspaceDreamAgentToolConfirmationAccepted",
    "StoryWorkspaceDreamAgentToolConfirmationCommand",
    "StoryWorkspaceDreamEdit",
    "StoryWorkspaceDreamFilesResponse",
    "StoryWorkspaceDreamReentryCollection",
    "StoryWorkspaceDreamReentryItem",
    "StoryWorkspaceDreamRunLifecycle",
    "StoryWorkspaceDreamRunToolInput",
    "StoryWorkspaceDreamRunFile",
    "StoryWorkspaceDreamSource",
    "StoryWorkspaceDreamSourceResponse",
    "StoryWorkspaceDreamStage",
    "StoryWorkspaceDreamStageFile",
    "StoryWorkspaceDreamStageItemToolInput",
    "StoryWorkspaceDreamStageItem",
    "StoryWorkspaceDreamStageItemResponse",
    "StoryWorkspaceDreamStagePage",
    "StoryWorkspaceDreamStagePageResponse",
    "StoryWorkspaceDreamStageResponse",
    "StoryWorkspaceDreamStageToolInput",
    "StoryWorkspaceDreamToolInput",
    "StoryWorkspaceExecutionProjection",
    "StoryWorkspaceGuidanceCommand",
    "StoryWorkspaceGuidanceCommandPayload",
    "StoryWorkspaceGuidanceKind",
    "StoryWorkspacePaginatedResponse",
    "StoryWorkspacePaginationInfo",
    "StoryWorkspaceResourceType",
    "StoryWorkspaceReviewActionRequest",
    "StoryWorkspaceReviewEventAction",
    "StoryWorkspaceReviewStatus",
    "StoryWorkspaceRoleType",
    "StoryWorkspaceScene",
    "StoryWorkspaceSceneCharacter",
    "StoryWorkspaceSceneDetail",
    "StoryWorkspaceSceneFilter",
    "StoryWorkspaceScenePatch",
    "StoryWorkspaceStats",
    "StoryWorkspaceStory",
    "StoryWorkspaceStoryCharacter",
    "StoryWorkspaceStoryDetail",
    "StoryWorkspaceStoryFilter",
    "StoryWorkspaceStoryPatch",
    "StoryWorkspaceStoryType",
    "StoryWorkspaceSurface",
    "StoryWorkspaceWorkspace",
    "StoryWorkspaceWorkspacePatch",
]
