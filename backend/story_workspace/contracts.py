"""Canonical contracts for the Story Workspace domain.

This module owns the data shapes shared by Story Workspace API, review, and
Agent-integration layers. Persistence and business workflows remain in their
respective router and service modules.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import math
import re
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
STORY_WORKSPACE_DREAM_AGENT_QUESTION_TEXT_MAX = 300
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
    agent_id: str | None = Field(default=None, min_length=1, max_length=255)
    goal: str = Field(min_length=1, max_length=12000)
    idempotency_key: str = Field(
        min_length=1,
        max_length=255,
        pattern=r"^[A-Za-z0-9._:-]+$",
    )

    @field_validator("deck_id", "agent_id", "goal", "idempotency_key")
    @classmethod
    def launch_values_have_no_boundary_whitespace(cls, value: str | None) -> str | None:
        if value is None:
            return value
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
    agent_id: str | None = Field(default=None, min_length=1, max_length=255)
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
    agent_id: str | None = Field(default=None, min_length=1, max_length=255)
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


_STORY_WORKSPACE_DREAM_AGENT_ACTIVITY_LABELS = {
    "workspace_read": "读取工作区资料",
    "dream_write": "更新 Dream 内容",
    "reference_lookup": "查找参考资料",
    "delegation": "协同处理创作任务",
    "other": "处理 Dream 创作任务",
}


class StoryWorkspaceDreamAgentTextContent(_StoryWorkspaceDreamWireModel):
    """One bounded public text part in its persisted message order."""

    kind: Literal["text"] = "text"
    text: str = Field(min_length=1, max_length=STORY_WORKSPACE_DREAM_AGENT_MESSAGE_TEXT_MAX)
    truncated: bool = False


class StoryWorkspaceDreamAgentActivityContent(_StoryWorkspaceDreamWireModel):
    """Server-authored activity summary; raw generic tool data is never carried."""

    kind: Literal["activity"] = "activity"
    id: str = Field(pattern=r"^dream_activity_[0-9a-f]{32,64}$")
    category: Literal[
        "workspace_read", "dream_write", "reference_lookup", "delegation", "other"
    ]
    label: Literal[
        "读取工作区资料",
        "更新 Dream 内容",
        "查找参考资料",
        "协同处理创作任务",
        "处理 Dream 创作任务",
    ]
    status: Literal["running", "completed", "stopped"]

    @model_validator(mode="after")
    def label_matches_category(self) -> "StoryWorkspaceDreamAgentActivityContent":
        if self.label != _STORY_WORKSPACE_DREAM_AGENT_ACTIVITY_LABELS[self.category]:
            raise ValueError("Dream Agent activity label must match its fixed category")
        return self


StoryWorkspaceDreamAgentContent = (
    StoryWorkspaceDreamAgentTextContent | StoryWorkspaceDreamAgentActivityContent
)


class StoryWorkspaceDreamAgentMessage(_StoryWorkspaceDreamWireModel):
    """Safe message plus ordered Dream-only public content projection."""

    id: str = Field(min_length=1, max_length=255)
    role: Literal["user", "assistant"]
    text: str = Field(min_length=1, max_length=STORY_WORKSPACE_DREAM_AGENT_MESSAGE_TEXT_MAX)
    truncated: bool = False
    content: list[StoryWorkspaceDreamAgentContent]
    created_at: datetime


class StoryWorkspaceDreamAgentToolConfirmationOption(_StoryWorkspaceDreamWireModel):
    """One bounded public option; runner IDs and raw values never cross the wire."""

    label: str = Field(min_length=1, max_length=STORY_WORKSPACE_DREAM_AGENT_QUESTION_OPTION_MAX)
    value: str = Field(min_length=1, max_length=STORY_WORKSPACE_DREAM_AGENT_QUESTION_OPTION_MAX)


class StoryWorkspaceDreamAgentToolConfirmationQuestion(_StoryWorkspaceDreamWireModel):
    """Server-authored AskUser question with an opaque public identity."""

    id: str = Field(
        min_length=1,
        max_length=STORY_WORKSPACE_DREAM_AGENT_QUESTION_ID_MAX,
        pattern=r"^q[0-9]+$",
    )
    question: str = Field(
        min_length=1,
        max_length=STORY_WORKSPACE_DREAM_AGENT_QUESTION_TEXT_MAX,
    )
    type: Literal["text", "textarea", "select", "checkbox", "radio", "number"]
    required: StrictBool
    multi_select: Optional[StrictBool] = None
    options: Optional[
        list[StoryWorkspaceDreamAgentToolConfirmationOption]
    ] = Field(default=None, max_length=12)
    placeholder: Optional[str] = Field(
        default=None,
        max_length=STORY_WORKSPACE_DREAM_AGENT_QUESTION_PLACEHOLDER_MAX,
    )


class StoryWorkspaceDreamAgentToolConfirmationNetwork(_StoryWorkspaceDreamWireModel):
    """Allowlisted network summary without raw request parameters."""

    host: Optional[str] = Field(
        default=None,
        max_length=253,
        pattern=(
            r"^(?:[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?"
            r"|[A-Fa-f0-9:]+)(?::[0-9]{1,5})?$"
        ),
    )
    policy: Literal["allowlist", "open", "deny", "unknown"]


class StoryWorkspaceDreamAgentToolConfirmation(_StoryWorkspaceDreamWireModel):
    """Safe display projection for one runtime-pending Dream tool decision."""

    tool_call_id: str = Field(
        min_length=1,
        max_length=STORY_WORKSPACE_DREAM_AGENT_TOOL_CALL_ID_MAX,
        pattern=r"^[A-Za-z0-9._:/-]+$",
    )
    kind: Literal["approval", "ask_user", "sandbox_network"]
    tool_name: str = Field(
        min_length=1,
        max_length=80,
        pattern=r"^[A-Za-z0-9 .:-]+$",
    )
    questions: Optional[
        list[StoryWorkspaceDreamAgentToolConfirmationQuestion]
    ] = Field(default=None, max_length=8)
    network: Optional[StoryWorkspaceDreamAgentToolConfirmationNetwork] = None

    @model_validator(mode="after")
    def fields_match_confirmation_kind(self) -> "StoryWorkspaceDreamAgentToolConfirmation":
        if self.kind == "ask_user":
            if not self.questions or self.network is not None:
                raise ValueError("AskUser confirmation requires questions only")
        elif self.kind == "sandbox_network":
            if self.network is None or self.questions is not None:
                raise ValueError("Sandbox confirmation requires network only")
        elif self.questions is not None or self.network is not None:
            raise ValueError("Approval confirmation cannot carry typed details")
        return self


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
    pending_tool_confirmations: list[StoryWorkspaceDreamAgentToolConfirmation] = Field(
        default_factory=list,
        max_length=256,
    )
    tool_confirmation_observation: Literal["known", "unknown"]
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
                    max_length=STORY_WORKSPACE_DREAM_AGENT_QUESTION_ID_MAX,
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


class StoryWorkspaceEpisodeBindingToolInput(StoryWorkspaceDreamToolInput):
    """Path-free request for the server-owned EP01 binding CAS."""

    workflow_run_id: str = Field(
        alias="workflowRunId",
        pattern=r"^run_[0-9a-f]{32}$",
    )
    expected_binding_revision: int = Field(
        alias="expectedBindingRevision",
        ge=0,
        le=1,
        strict=True,
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


class StoryWorkspaceEpisodeBindingAvailability(str, Enum):
    """Whether a run has a server-proven first-episode binding."""

    BOUND = "bound"
    UNBOUND = "unbound"


class StoryWorkspaceEpisodeBindingPublicReason(str, Enum):
    """Allowlisted public recovery reasons without internal diagnostics."""

    EPISODE_BINDING_UNPROVEN = "episode_binding_unproven"


class StoryWorkspaceEpisodeArtifactAvailability(str, Enum):
    """Filesystem/parse availability, not an Episode business lifecycle."""

    NOT_GENERATED = "not_generated"
    AVAILABLE = "available"
    INVALID = "invalid"
    UNAVAILABLE = "unavailable"


class StoryWorkspaceEpisodeProducerAction(str, Enum):
    """Safe action vocabulary for artifact provenance and UI translation."""

    PLAN_EPISODE = "plan_episode"
    WRITE_SCRIPT = "write_script"
    REVIEW_SCRIPT = "review_script"
    BUILD_ASSETS = "build_assets"
    REGENERATE_STORYBOARD = "regenerate_storyboard"
    GENERATE_PROMPTS = "generate_prompts"
    REVIEW_FULL_CHAIN = "review_full_chain"
    COMMIT_EPISODE = "commit_episode"
    PREPARE_RENDER_GUIDE = "prepare_render_guide"


class StoryWorkspaceEpisodeAction(str, Enum):
    """Server-derived Episode capabilities, never persisted lifecycle states."""

    PLAN_EPISODE = "plan_episode"
    WRITE_SCRIPT = "write_script"
    REVIEW_SCRIPT = "review_script"
    REFRESH_ASSETS = "refresh_assets"
    REGENERATE_STORYBOARD = "regenerate_storyboard"
    GENERATE_PROMPTS = "generate_prompts"
    REVIEW_FULL_CHAIN = "review_full_chain"
    VALIDATE_EPISODE = "validate_episode"
    PREPARE_RENDER_GUIDE = "prepare_render_guide"
    NONE_IN_SCOPE = "none_in_scope"


class StoryWorkspaceEpisodeActionDiagnostic(str, Enum):
    """Evidence quality for a derived action, not an Episode business status."""

    READY = "ready"
    NEEDS_CONFIRMATION = "needs_confirmation"


class StoryWorkspaceEpisodeWorkflowCompletion(_StoryWorkspaceDreamStorageModel):
    """One technical completion fact tied to a canonical input snapshot."""

    action: StoryWorkspaceEpisodeAction
    input_revision: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    manifest_revision: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    message_id: str = Field(pattern=r"^dream_agent_[0-9a-f]{64}$")
    recorded_at: datetime

    @model_validator(mode="after")
    def action_is_completable(self) -> "StoryWorkspaceEpisodeWorkflowCompletion":
        if self.action is StoryWorkspaceEpisodeAction.NONE_IN_SCOPE:
            raise ValueError("none_in_scope cannot be recorded as completion")
        return self


class StoryWorkspaceEpisodeWorkflowFile(_StoryWorkspaceDreamStorageModel):
    """Revisioned workflow evidence; never an owner of creative content."""

    schema_version: Literal["dream-episode-workflow/v1"] = (
        "dream-episode-workflow/v1"
    )
    workflow_run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    episode_uid: str = Field(pattern=r"^[0-9a-f]{32}$")
    revision: _StoryWorkspaceDreamNonNegativeInt = 0
    completions: list[StoryWorkspaceEpisodeWorkflowCompletion] = Field(
        default_factory=list,
        max_length=9,
    )
    updated_at: datetime

    @model_validator(mode="after")
    def actions_are_unique(self) -> "StoryWorkspaceEpisodeWorkflowFile":
        actions = [item.action for item in self.completions]
        if len(actions) != len(set(actions)):
            raise ValueError("workflow completion actions must be unique")
        return self


class StoryWorkspaceEpisodeWorkflowCompletionToolInput(
    StoryWorkspaceDreamToolInput
):
    """Path-free request; the host message owns all completion evidence."""

    workflow_run_id: str = Field(
        alias="workflowRunId",
        pattern=r"^run_[0-9a-f]{32}$",
    )


class StoryWorkspaceEpisodeActionResolution(_StoryWorkspaceDreamWireModel):
    """One evidence-derived next capability and its diagnostic confidence."""

    action: StoryWorkspaceEpisodeAction
    diagnostic: StoryWorkspaceEpisodeActionDiagnostic
    can_dispatch: StrictBool

    @model_validator(mode="after")
    def dispatch_matches_action(self) -> "StoryWorkspaceEpisodeActionResolution":
        if (
            self.action is StoryWorkspaceEpisodeAction.NONE_IN_SCOPE
            and self.can_dispatch
        ):
            raise ValueError("none_in_scope cannot be dispatched")
        return self


class StoryWorkspaceEpisodeActionAvailability(str, Enum):
    """Public option eligibility derived from current server facts."""

    EXECUTABLE = "executable"
    PREVIEW = "preview"
    BLOCKED = "blocked"


class StoryWorkspaceEpisodeActionDispatchState(str, Enum):
    """Technical dispatch coordination, never an Episode lifecycle."""

    IDLE = "idle"
    ACCEPTED = "accepted"
    DISPATCHING = "dispatching"
    DISPATCHED = "dispatched"


class StoryWorkspaceEpisodeRelation(str, Enum):
    """The bounded current/next Episode window exposed by the resolver."""

    CURRENT = "current"
    NEXT = "next"


class StoryWorkspaceEpisodeActionTarget(_StoryWorkspaceDreamWireModel):
    """Path-free Episode display identity issued by the server."""

    opaque_episode_id: Optional[str] = Field(
        default=None,
        pattern=r"^[0-9a-f]{32}$",
    )
    candidate_id: Optional[str] = Field(
        default=None,
        pattern=r"^episode_candidate_[0-9a-f]{64}$",
    )
    display_label: StrictStr = Field(pattern=r"^EP[0-9]{2,}$")
    relation: StoryWorkspaceEpisodeRelation

    @model_validator(mode="after")
    def identity_matches_relation(self) -> "StoryWorkspaceEpisodeActionTarget":
        if (self.opaque_episode_id is None) == (self.candidate_id is None):
            raise ValueError("an Episode target requires exactly one opaque identity")
        if (
            self.relation is StoryWorkspaceEpisodeRelation.CURRENT
            and self.opaque_episode_id is None
        ):
            raise ValueError("the current Episode target must already be bound")
        return self


class StoryWorkspaceEpisodeArtifactCanonicalInput(_StoryWorkspaceDreamWireModel):
    """One Episode-manifest-owned public canonical input."""

    source_type: Literal["episode_artifact"] = "episode_artifact"
    artifact: Literal[
        "episode_outline",
        "script",
        "review_report",
        "storyboard",
        "prompts",
        "renders",
    ]
    owner: Literal["episode_artifact_manifest"] = "episode_artifact_manifest"
    label: StrictStr = Field(min_length=1, max_length=120)
    availability: Literal["available", "not_generated", "invalid", "unavailable"]
    public_revision: Optional[str] = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    revision_kind: Literal["content"] = "content"
    requirement: Literal["required", "context"]


class StoryWorkspaceProjectArtifactCanonicalInput(_StoryWorkspaceDreamWireModel):
    """One allowlisted canonical project-file input without its path."""

    source_type: Literal["project_artifact"] = "project_artifact"
    artifact: Literal[
        "project_definition",
        "master_outline",
        "worldbuilding",
        "character_arc_ledger",
    ]
    owner: Literal["canonical_project_files"] = "canonical_project_files"
    label: StrictStr = Field(min_length=1, max_length=120)
    availability: Literal["available", "not_generated", "invalid", "unavailable"]
    public_revision: Optional[str] = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    revision_kind: Literal["content"] = "content"
    requirement: Literal["required", "context"]


class StoryWorkspaceAssetContextCanonicalInput(_StoryWorkspaceDreamWireModel):
    """Public aggregate status for canonical project asset inventory."""

    source_type: Literal["asset_context"] = "asset_context"
    context: Literal["character_scene_prop_inventory"] = (
        "character_scene_prop_inventory"
    )
    owner: Literal["canonical_project_asset_inventory"] = (
        "canonical_project_asset_inventory"
    )
    label: StrictStr = Field(min_length=1, max_length=120)
    availability: Literal["current", "stale", "unavailable"]
    public_revision: Optional[str] = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    revision_kind: Literal["aggregate"] = "aggregate"
    requirement: Literal["context"] = "context"


class StoryWorkspaceWorkflowFactCanonicalInput(_StoryWorkspaceDreamWireModel):
    """One workflow-fact-owned prerequisite exposed without internal metadata."""

    source_type: Literal["workflow_fact"] = "workflow_fact"
    fact: Literal[
        "refresh_assets_completion",
        "full_chain_review",
        "validation",
        "prior_episode_validation",
    ]
    owner: Literal["episode_workflow_facts"] = "episode_workflow_facts"
    label: StrictStr = Field(min_length=1, max_length=120)
    availability: Literal["current", "stale", "missing"]
    public_revision: Optional[str] = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    revision_kind: Literal["input", "facts"]
    requirement: Literal["required"] = "required"


StoryWorkspaceEpisodeActionCanonicalInput = Annotated[
    StoryWorkspaceEpisodeArtifactCanonicalInput
    | StoryWorkspaceProjectArtifactCanonicalInput
    | StoryWorkspaceAssetContextCanonicalInput
    | StoryWorkspaceWorkflowFactCanonicalInput,
    Field(discriminator="source_type"),
]


class StoryWorkspaceEpisodeActionOptionV2(_StoryWorkspaceDreamWireModel):
    """One opaque, target-aware server-owned workflow action option."""

    action_id: str = Field(pattern=r"^episode_action_[0-9a-f]{64}$")
    action: StoryWorkspaceEpisodeAction
    target_episode: StoryWorkspaceEpisodeActionTarget
    label: StrictStr = Field(min_length=1, max_length=160)
    description: StrictStr = Field(min_length=1, max_length=500)
    display_command: StrictStr = Field(min_length=1, max_length=160)
    availability: StoryWorkspaceEpisodeActionAvailability
    is_recommended: StrictBool
    can_dispatch: StrictBool
    disabled_reason: Optional[StrictStr] = Field(default=None, max_length=300)
    canonical_inputs: list[StoryWorkspaceEpisodeActionCanonicalInput] = Field(
        default_factory=list,
        max_length=16,
    )
    consequences: list[StrictStr] = Field(default_factory=list, max_length=8)
    dispatch_state: StoryWorkspaceEpisodeActionDispatchState = (
        StoryWorkspaceEpisodeActionDispatchState.IDLE
    )

    @model_validator(mode="after")
    def option_state_is_consistent(self) -> "StoryWorkspaceEpisodeActionOptionV2":
        if self.action is StoryWorkspaceEpisodeAction.NONE_IN_SCOPE:
            raise ValueError("none_in_scope cannot be rendered as an option")
        if any(
            marker in self.display_command
            for marker in ("mcp__", "workflowRunId", "expectedBindingRevision")
        ):
            raise ValueError("display_command must not expose internal tool details")
        if self.availability in {
            StoryWorkspaceEpisodeActionAvailability.PREVIEW,
            StoryWorkspaceEpisodeActionAvailability.BLOCKED,
        }:
            if self.dispatch_state is not StoryWorkspaceEpisodeActionDispatchState.IDLE:
                raise ValueError("preview and blocked options must remain idle")
            if self.can_dispatch:
                raise ValueError("preview and blocked options cannot be dispatched")
        if self.dispatch_state in {
            StoryWorkspaceEpisodeActionDispatchState.ACCEPTED,
            StoryWorkspaceEpisodeActionDispatchState.DISPATCHING,
            StoryWorkspaceEpisodeActionDispatchState.DISPATCHED,
        } and self.can_dispatch:
            raise ValueError("non-idle options cannot be dispatched")
        if self.can_dispatch and (
            self.availability is not StoryWorkspaceEpisodeActionAvailability.EXECUTABLE
            or self.disabled_reason is not None
        ):
            raise ValueError("dispatchable options must be executable without a reason")
        if not self.can_dispatch and self.disabled_reason is None:
            raise ValueError("non-dispatchable options require a public reason")
        return self


class StoryWorkspaceEpisodeActionProjectionV2(_StoryWorkspaceDreamWireModel):
    """A bounded server-ordered current/next Episode action projection."""

    recommended_action_id: Optional[str] = Field(
        default=None,
        pattern=r"^episode_action_[0-9a-f]{64}$",
    )
    action_options: list[StoryWorkspaceEpisodeActionOptionV2] = Field(
        default_factory=list,
        max_length=9,
    )

    @model_validator(mode="after")
    def options_match_recommendation(self) -> "StoryWorkspaceEpisodeActionProjectionV2":
        if not self.action_options:
            if self.recommended_action_id is not None:
                raise ValueError("an empty projection cannot recommend an action")
            return self
        if self.recommended_action_id != self.action_options[0].action_id:
            raise ValueError("the first option must match recommended_action_id")
        recommended = [item for item in self.action_options if item.is_recommended]
        if len(recommended) != 1 or recommended[0].action_id != self.recommended_action_id:
            raise ValueError("a non-empty projection requires one recommendation")
        identities = [item.action_id for item in self.action_options]
        if len(identities) != len(set(identities)):
            raise ValueError("action option identities must be unique")
        return self


class StoryWorkspaceEpisodeActionOption(_StoryWorkspaceDreamWireModel):
    """One server-ordered workflow option exposed for navigation only."""

    action: StoryWorkspaceEpisodeAction
    label: StrictStr = Field(min_length=1, max_length=120)
    display_command: StrictStr = Field(min_length=1, max_length=120)
    is_current: StrictBool
    can_dispatch: StrictBool

    @model_validator(mode="after")
    def dispatch_requires_current_option(self) -> "StoryWorkspaceEpisodeActionOption":
        if self.can_dispatch and not self.is_current:
            raise ValueError("only the current workflow option can be dispatched")
        if any(
            marker in self.display_command
            for marker in ("mcp__", "workflowRunId", "expectedBindingRevision")
        ):
            raise ValueError("display_command must not expose internal tool details")
        return self


class StoryWorkspaceEpisodeWorkflowProjection(_StoryWorkspaceDreamWireModel):
    """Derived workflow navigation plus the revision of technical facts."""

    facts_revision: _StoryWorkspaceDreamNonNegativeInt
    next_action: StoryWorkspaceEpisodeActionResolution
    prerequisites: list[StoryWorkspaceEpisodeAction] = Field(
        default_factory=list,
        max_length=9,
    )
    action_options: list[StoryWorkspaceEpisodeActionOption] = Field(
        default_factory=list,
        max_length=9,
    )
    legacy_partial: StrictBool

    @field_validator("prerequisites")
    @classmethod
    def prerequisites_are_unique_and_completed(
        cls,
        values: list[StoryWorkspaceEpisodeAction],
    ) -> list[StoryWorkspaceEpisodeAction]:
        if len(values) != len(set(values)):
            raise ValueError("workflow prerequisites must be unique")
        if StoryWorkspaceEpisodeAction.NONE_IN_SCOPE in values:
            raise ValueError("none_in_scope is not a prerequisite")
        return values

    @model_validator(mode="after")
    def action_options_match_next_action(
        self,
    ) -> "StoryWorkspaceEpisodeWorkflowProjection":
        if self.next_action.action is StoryWorkspaceEpisodeAction.NONE_IN_SCOPE:
            if self.action_options:
                raise ValueError("none_in_scope cannot expose workflow options")
            return self
        if not self.action_options:
            raise ValueError("an active workflow requires ordered action options")
        current = self.action_options[0]
        if (
            current.action is not self.next_action.action
            or not current.is_current
            or current.can_dispatch != self.next_action.can_dispatch
        ):
            raise ValueError("the first workflow option must match next_action")
        if any(option.is_current or option.can_dispatch for option in self.action_options[1:]):
            raise ValueError("upcoming workflow options are display-only")
        actions = [option.action for option in self.action_options]
        if len(actions) != len(set(actions)):
            raise ValueError("workflow action options must be unique")
        return self


class StoryWorkspaceEpisodeBindingRecoveryCommand(_StoryWorkspaceDreamWireModel):
    """Path-free request for the server-owned first-Episode recovery intent."""

    idempotency_key: str = Field(
        min_length=1,
        max_length=255,
        pattern=r"^[A-Za-z0-9._:-]+$",
    )


_STORY_WORKSPACE_EPISODE_GUIDANCE_DENYLIST = (
    re.compile(r"(?:^|\s)/drama-[a-z-]+\b", re.IGNORECASE),
    re.compile(
        r"\b(?:hidden|internal)\s+(?:reasoning|thoughts?)\b|"
        r"\bchain\s+of\s+thought\b|\bsystem\s+prompt\b|"
        r"隐藏推理|内部推理|思维链|系统提示词",
        re.IGNORECASE,
    ),
    re.compile(r"\bBearer\s+\S+", re.IGNORECASE),
    re.compile(
        r"(?<![A-Za-z0-9_-])(?:sk-(?:ant-|proj-)?|gh[pousr]_|xox[baprs]-)"
        r"[A-Za-z0-9_-]{16,}",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?<![A-Za-z0-9])/(?:Users|home)/[^\s]+|"
        r"(?<![A-Za-z0-9])[A-Za-z]:\\Users\\[^\s]+",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:\$\{?HOME\}?|~)/(?:\.[^/\s]+|[^/\s]+)/(?:[^\s]+)|"
        r"(?<![A-Za-z0-9])/(?:etc)/(?:passwd|shadow)(?![A-Za-z0-9])",
        re.IGNORECASE,
    ),
    re.compile(r"(?<![A-Za-z0-9_])\.\.?/[^\s]+"),
    re.compile(
        r"(?:^|[\r\n;&|])\s*(?:[$>#]\s*)?"
        r"(?:git|python(?:3(?:\.\d+)*)?|npx|rm|sudo|node|bash|sh)\b"
        r"\s+(?:--?[A-Za-z0-9]|[A-Za-z0-9_./@])",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:process\.)?env(?:\s*\||\s*\[|\.)|\bprintenv\b|"
        r"\b[A-Z][A-Z0-9_]*(?:KEY|TOKEN|SECRET|CREDENTIALS?)\s*=",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:curl|wget)\b.{0,500}\|\s*(?:ba|z|fi)?sh\b",
        re.IGNORECASE,
    ),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.IGNORECASE),
    re.compile(
        r"\bmcp__[a-z0-9_]+\b|\brecord_episode_workflow_completion\b|"
        r"story_workspace_(?:dream_context|episode_action|run_id)|"
        r"dispatch_(?:claim_id|claim_lease_until|status)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:workflowRunId|expectedFactsRevision|expectedManifestRevision|"
        r"expectedWorkflowRevision|inputRevision|factsRevision|manifestRevision|"
        r"workflow_run_id|expected_facts_revision|expected_manifest_revision|"
        r"expected_workflow_revision|input_revision)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bsha256:[0-9a-f]{64}\b", re.IGNORECASE),
    re.compile(
        r"(?<![A-Za-z0-9_])CAS(?![A-Za-z0-9_])|"
        r"\bcompare[- ]and[- ](?:swap|set)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:忽略|无视|覆盖).{0,24}(?:上文|以上|之前|前述|限制|约束)"
        r".{0,48}(?:继续|执行|运行|下一步|后续)|"
        r"\b(?:ignore|override|disregard)\b.{0,64}"
        r"\b(?:previous|prior|above|instructions?|constraints?)\b.{0,64}"
        r"\b(?:continue|execute|run|next|remaining|subsequent)\b",
        re.IGNORECASE,
    ),
)


class StoryWorkspaceEpisodeActionContinueCommand(_StoryWorkspaceDreamWireModel):
    """Untrusted request to dispatch one server-revalidated Episode capability."""

    episode_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    action: StoryWorkspaceEpisodeAction
    idempotency_key: str = Field(
        min_length=1,
        max_length=255,
        pattern=r"^[A-Za-z0-9._:-]+$",
    )
    user_guidance: Optional[StrictStr] = Field(default=None, max_length=2000)

    @field_validator("user_guidance")
    @classmethod
    def guidance_is_bounded_plain_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if any(
            ord(character) < 32 and character not in "\n\t"
            for character in normalized
        ):
            raise ValueError("user guidance must be bounded plain text")
        if any(
            pattern.search(normalized)
            for pattern in _STORY_WORKSPACE_EPISODE_GUIDANCE_DENYLIST
        ):
            raise ValueError("user guidance contains disallowed sensitive content")
        return normalized


class StoryWorkspaceEpisodeActionAccepted(_StoryWorkspaceDreamWireModel):
    """Durable dispatch acknowledgement; canonical files remain authoritative."""

    run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    episode_id: Optional[str] = Field(default=None, pattern=r"^[0-9a-f]{32}$")
    capability: StoryWorkspaceEpisodeAction | Literal[
        "recover_first_episode_binding"
    ]
    message_id: str = Field(min_length=1, max_length=255)
    accepted: Literal[True] = True
    replayed: StrictBool


class StoryWorkspaceEpisodeArtifactConsumer(str, Enum):
    """Allowlisted UI consumers; never accepts arbitrary component names."""

    EPISODE_OVERVIEW = "episode_overview"
    STORYLINE_NAVIGATOR = "storyline_navigator"
    NARRATIVE_WORKBENCH = "narrative_workbench"
    SHOT_INSPECTOR = "shot_inspector"
    PROMPT_VIEW = "prompt_view"
    RENDER_VIEW = "render_view"
    REVIEW_VIEW = "review_view"


class StoryWorkspaceEpisodeBindingFile(_StoryWorkspaceDreamStorageModel):
    """Immutable run-scoped identity persisted as ``episode.json``."""

    schema_version: Literal["dream-episode/v1"] = "dream-episode/v1"
    workflow_run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    episode_uid: str = Field(pattern=r"^[0-9a-f]{32}$")
    story_slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    episode_code: Literal["EP01"] = "EP01"
    episode_root: str = Field(min_length=1, max_length=512)
    revision: Literal[1] = 1
    updated_at: datetime

    @model_validator(mode="after")
    def episode_root_matches_server_identity(
        self,
    ) -> "StoryWorkspaceEpisodeBindingFile":
        expected_root = f"stories/{self.story_slug}/episodes/EP01"
        if self.episode_root != expected_root:
            raise ValueError("episode_root does not match the canonical EP01 identity")
        return self


class StoryWorkspaceEpisodeBindingEntry(_StoryWorkspaceDreamStorageModel):
    """One server-numbered Episode identity in the run-scoped registry."""

    episode_uid: str = Field(pattern=r"^[0-9a-f]{32}$")
    episode_number: _StoryWorkspaceDreamPositiveInt = Field(le=99)
    episode_code: str = Field(pattern=r"^EP[0-9]{2}$")
    episode_root: str = Field(min_length=1, max_length=512)
    created_at: datetime


class StoryWorkspaceEpisodeRegistryFile(_StoryWorkspaceDreamStorageModel):
    """Revisioned multi-Episode identity owner persisted as ``episode.json``."""

    schema_version: Literal["dream-episode/v2"] = "dream-episode/v2"
    workflow_run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    story_slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    active_episode_uid: str = Field(pattern=r"^[0-9a-f]{32}$")
    episodes: list[StoryWorkspaceEpisodeBindingEntry] = Field(
        min_length=1,
        max_length=99,
    )
    revision: _StoryWorkspaceDreamPositiveInt
    updated_at: datetime

    @model_validator(mode="after")
    def registry_owns_contiguous_canonical_numbering(
        self,
    ) -> "StoryWorkspaceEpisodeRegistryFile":
        seen_uids: set[str] = set()
        for expected_number, episode in enumerate(self.episodes, start=1):
            if episode.episode_number != expected_number:
                raise ValueError("Episode registry numbering must be contiguous")
            expected_code = f"EP{expected_number:02d}"
            if episode.episode_code != expected_code:
                raise ValueError("Episode code does not match the server-owned number")
            expected_root = (
                f"stories/{self.story_slug}/episodes/{expected_code}"
            )
            if episode.episode_root != expected_root:
                raise ValueError("Episode root does not match the registry identity")
            if episode.episode_uid in seen_uids:
                raise ValueError("Episode registry identities must be unique")
            seen_uids.add(episode.episode_uid)
        if self.active_episode_uid not in seen_uids:
            raise ValueError("active Episode must exist in the registry")
        return self


class StoryWorkspaceEpisodeBindingRecovery(_StoryWorkspaceDreamWireModel):
    """Public recovery facts without story paths or internal failure details."""

    auto_repair_attempted: StrictBool
    can_dispatch: StrictBool
    public_reason: Optional[StoryWorkspaceEpisodeBindingPublicReason] = None

    @model_validator(mode="after")
    def reason_matches_dispatch_capability(
        self,
    ) -> "StoryWorkspaceEpisodeBindingRecovery":
        if self.can_dispatch != (self.public_reason is not None):
            raise ValueError(
                "only an unbound recoverable surface exposes a recovery reason"
            )
        return self


class StoryWorkspaceEpisodeArtifactManifestEntry(_StoryWorkspaceDreamWireModel):
    """One allowlisted artifact fact in the Episode surface manifest."""

    relative_key: str = Field(
        min_length=1,
        max_length=512,
    )
    availability: StoryWorkspaceEpisodeArtifactAvailability
    content_revision: Optional[str] = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    mtime: Optional[datetime] = None
    size: Optional[_StoryWorkspaceDreamNonNegativeInt] = None
    producer_action: StoryWorkspaceEpisodeProducerAction
    consumers: list[StoryWorkspaceEpisodeArtifactConsumer] = Field(
        min_length=1,
        max_length=8,
    )

    @field_validator("relative_key")
    @classmethod
    def relative_key_is_allowlisted(cls, value: str) -> str:
        top_level = {
            "episode-outline.md",
            "script.md",
            "storyboard.yaml",
            "review-report.md",
        }
        if value in top_level or value in {"prompts/", "renders/"}:
            return value
        prefixes = ("prompts/", "renders/")
        matching_prefix = next(
            (prefix for prefix in prefixes if value.startswith(prefix)),
            None,
        )
        if matching_prefix is None:
            raise ValueError("relative_key is not an allowlisted Episode artifact")
        segments = value[len(matching_prefix) :].split("/")
        if any(
            segment in {"", ".", ".."}
            or any(
                not character.isascii()
                or not (character.isalnum() or character in "._-")
                for character in segment
            )
            for segment in segments
        ):
            raise ValueError("relative_key must be safely relative")
        approved_extensions = (
            {".md", ".yaml", ".yml"}
            if matching_prefix == "prompts/"
            else {".json", ".md"}
        )
        filename = segments[-1]
        extension = (
            "." + filename.rsplit(".", maxsplit=1)[-1].lower()
            if "." in filename
            else ""
        )
        if extension not in approved_extensions:
            raise ValueError("relative_key extension is not approved")
        return value

    @field_validator("consumers")
    @classmethod
    def consumers_are_unique(
        cls,
        values: list[StoryWorkspaceEpisodeArtifactConsumer],
    ) -> list[StoryWorkspaceEpisodeArtifactConsumer]:
        if len(values) != len(set(values)):
            raise ValueError("consumers must not contain duplicates")
        return values

    @model_validator(mode="after")
    def metadata_matches_availability(
        self,
    ) -> "StoryWorkspaceEpisodeArtifactManifestEntry":
        metadata = (self.content_revision, self.mtime, self.size)
        if self.availability is StoryWorkspaceEpisodeArtifactAvailability.AVAILABLE:
            if any(value is None for value in metadata):
                raise ValueError("available artifacts require revision, mtime, and size")
        elif any(value is not None for value in metadata):
            raise ValueError("unavailable artifacts must not expose file metadata")
        if self.relative_key == "episode-outline.md":
            allowed_producers = {StoryWorkspaceEpisodeProducerAction.PLAN_EPISODE}
            expected_consumers = [
                StoryWorkspaceEpisodeArtifactConsumer.EPISODE_OVERVIEW,
                StoryWorkspaceEpisodeArtifactConsumer.STORYLINE_NAVIGATOR,
                StoryWorkspaceEpisodeArtifactConsumer.NARRATIVE_WORKBENCH,
            ]
        elif self.relative_key == "script.md":
            allowed_producers = {StoryWorkspaceEpisodeProducerAction.WRITE_SCRIPT}
            expected_consumers = [
                StoryWorkspaceEpisodeArtifactConsumer.NARRATIVE_WORKBENCH,
                StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
            ]
        elif self.relative_key == "storyboard.yaml":
            allowed_producers = {
                StoryWorkspaceEpisodeProducerAction.REGENERATE_STORYBOARD
            }
            expected_consumers = [
                StoryWorkspaceEpisodeArtifactConsumer.NARRATIVE_WORKBENCH,
                StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
            ]
        elif self.relative_key.startswith("prompts/"):
            allowed_producers = {
                StoryWorkspaceEpisodeProducerAction.GENERATE_PROMPTS
            }
            expected_consumers = [
                StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
                StoryWorkspaceEpisodeArtifactConsumer.PROMPT_VIEW,
            ]
        elif self.relative_key.startswith("renders/"):
            allowed_producers = {
                StoryWorkspaceEpisodeProducerAction.PREPARE_RENDER_GUIDE
            }
            expected_consumers = [
                StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
                StoryWorkspaceEpisodeArtifactConsumer.RENDER_VIEW,
            ]
        else:
            allowed_producers = {
                StoryWorkspaceEpisodeProducerAction.REVIEW_SCRIPT,
                StoryWorkspaceEpisodeProducerAction.REVIEW_FULL_CHAIN,
            }
            expected_consumers = [
                StoryWorkspaceEpisodeArtifactConsumer.REVIEW_VIEW,
                StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
            ]
        if self.producer_action not in allowed_producers:
            raise ValueError("producer_action does not match relative_key")
        if self.consumers != expected_consumers:
            raise ValueError("consumers do not match relative_key")
        return self


class StoryWorkspaceEpisodeAssociationStatus(str, Enum):
    """Evidence-backed relationship state for one projected entity."""

    LINKED = "linked"
    UNLINKED = "unlinked"
    ORPHAN = "orphan"


class StoryWorkspaceEpisodeSourceArtifact(str, Enum):
    """Allowlisted canonical artifact names used by Episode provenance."""

    EPISODE_OUTLINE = "episode-outline.md"
    SCRIPT = "script.md"
    STORYBOARD = "storyboard.yaml"


class StoryWorkspaceEpisodeDialogueType(str, Enum):
    """Canonical DramaForge storyboard dialogue types."""

    SPOKEN = "spoken"
    VOICEOVER = "voiceover"
    OS = "os"
    INNER = "inner"


class StoryWorkspaceEpisodeDepthPlane(str, Enum):
    """Canonical compositional depth for multi-character shots."""

    FRONT = "front"
    MID = "mid"
    BACK = "back"


class StoryWorkspaceEpisodeMetricAvailability(str, Enum):
    """Whether a coverage denominator exists; not a workflow status."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class StoryWorkspaceEpisodeAssociationCoverage(_StoryWorkspaceDreamWireModel):
    """Bounded association metric with honest zero-denominator semantics."""

    availability: StoryWorkspaceEpisodeMetricAvailability
    linked: _StoryWorkspaceDreamNonNegativeInt
    total: _StoryWorkspaceDreamNonNegativeInt
    ratio: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def availability_matches_denominator(
        self,
    ) -> "StoryWorkspaceEpisodeAssociationCoverage":
        if self.linked > self.total:
            raise ValueError("linked coverage cannot exceed total")
        if self.total == 0:
            if (
                self.availability is not StoryWorkspaceEpisodeMetricAvailability.UNAVAILABLE
                or self.linked != 0
                or self.ratio is not None
            ):
                raise ValueError("zero-denominator coverage must be unavailable")
            return self
        expected_ratio = self.linked / self.total
        if (
            self.availability is not StoryWorkspaceEpisodeMetricAvailability.AVAILABLE
            or self.ratio is None
            or not math.isclose(self.ratio, expected_ratio, rel_tol=1e-12)
        ):
            raise ValueError("available coverage must match linked / total")
        return self


class StoryWorkspaceEpisodeCharacterBeat(_StoryWorkspaceDreamWireModel):
    """Auxiliary character-arc evidence; never a narrative hierarchy node."""

    id: str = Field(pattern=r"^[0-9a-f]{32}$")
    source_key: str = Field(min_length=1, max_length=128)
    character_id: Optional[str] = Field(default=None, max_length=128)
    action: Optional[str] = Field(default=None, max_length=128)
    start_state: Optional[str] = Field(default=None, max_length=2000)
    trigger: Optional[str] = Field(default=None, max_length=2000)
    choice: Optional[str] = Field(default=None, max_length=2000)
    end_state: Optional[str] = Field(default=None, max_length=2000)
    visible_evidence: Optional[str] = Field(default=None, max_length=2000)


class StoryWorkspaceEpisodeOverview(_StoryWorkspaceDreamWireModel):
    """Episode story facts owned by ``episode-outline.md``."""

    title: Optional[str] = Field(default=None, max_length=500)
    series: Optional[str] = Field(default=None, max_length=500)
    story_goals: list[str] = Field(default_factory=list, max_length=32)
    core_conflict: Optional[str] = Field(default=None, max_length=4000)
    hook: Optional[str] = Field(default=None, max_length=4000)
    source_artifact: Optional[
        Literal[StoryWorkspaceEpisodeSourceArtifact.EPISODE_OUTLINE]
    ] = None
    source_revision: Optional[str] = Field(
        default=None,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,127}$",
    )
    generated_from: Optional[str] = Field(
        default=None,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9@._:-]{0,254}$",
    )
    character_beats: list[StoryWorkspaceEpisodeCharacterBeat] = Field(
        default_factory=list,
        max_length=256,
    )


class StoryWorkspaceEpisodeNarrativeBeat(_StoryWorkspaceDreamWireModel):
    """One explicit ``SC-NN`` section from the Episode outline."""

    id: str = Field(pattern=r"^[0-9a-f]{32}$")
    source_key: str = Field(pattern=r"^SC-[0-9]{2,}$")
    title: str = Field(min_length=1, max_length=500)
    asset_scene_ref: Optional[str] = Field(default=None, max_length=255)
    narrative_function: Optional[str] = Field(default=None, max_length=500)
    emotion_tone: Optional[str] = Field(default=None, max_length=500)
    summary: Optional[str] = Field(default=None, max_length=4000)
    scene_goals: list[str] = Field(default_factory=list, max_length=32)
    key_dialogue_beats: list[str] = Field(default_factory=list, max_length=32)
    source_artifact: Literal[
        StoryWorkspaceEpisodeSourceArtifact.EPISODE_OUTLINE
    ] = StoryWorkspaceEpisodeSourceArtifact.EPISODE_OUTLINE
    source_revision: Optional[str] = Field(
        default=None,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,127}$",
    )
    generated_from: Optional[str] = Field(
        default=None,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9@._:-]{0,254}$",
    )


class StoryWorkspaceEpisodeDialogueLine(_StoryWorkspaceDreamWireModel):
    """Plain-text script dialogue safe for a scene context preview."""

    speaker: str = Field(min_length=1, max_length=128)
    qualifier: Optional[str] = Field(default=None, max_length=255)
    text: str = Field(min_length=1, max_length=2000)


class StoryWorkspaceEpisodeScriptScene(_StoryWorkspaceDreamWireModel):
    """One explicit ``SNN.`` scene heading from ``script.md``."""

    id: str = Field(pattern=r"^[0-9a-f]{32}$")
    source_key: str = Field(pattern=r"^S[0-9]{2,}$")
    title: str = Field(min_length=1, max_length=500)
    heading: str = Field(min_length=1, max_length=1000)
    asset_scene_ref: Optional[str] = Field(default=None, max_length=255)
    narrative_beat_id: Optional[str] = Field(
        default=None,
        pattern=r"^[0-9a-f]{32}$",
    )
    declared_narrative_beat_ref: Optional[str] = Field(
        default=None,
        pattern=r"^SC-[0-9]{2,}$",
    )
    association_status: StoryWorkspaceEpisodeAssociationStatus
    actions: list[str] = Field(default_factory=list, max_length=256)
    dialogue: list[StoryWorkspaceEpisodeDialogueLine] = Field(
        default_factory=list,
        max_length=256,
    )
    camera_cues: list[str] = Field(default_factory=list, max_length=256)
    source_artifact: Literal[
        StoryWorkspaceEpisodeSourceArtifact.SCRIPT
    ] = StoryWorkspaceEpisodeSourceArtifact.SCRIPT
    source_revision: Optional[str] = Field(
        default=None,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,127}$",
    )
    generated_from: Optional[str] = Field(
        default=None,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9@._:-]{0,254}$",
    )

    @model_validator(mode="after")
    def linked_scene_has_a_beat(self) -> "StoryWorkspaceEpisodeScriptScene":
        if (
            self.association_status is StoryWorkspaceEpisodeAssociationStatus.LINKED
        ) != (self.narrative_beat_id is not None):
            raise ValueError("only linked scenes may expose narrative_beat_id")
        return self


class StoryWorkspaceEpisodeShotCharacter(_StoryWorkspaceDreamWireModel):
    """Allowlisted storyboard character reference and visible action."""

    ref: str = Field(min_length=1, max_length=128)
    display_name: Optional[str] = Field(default=None, max_length=255)
    depth_plane: Optional[StoryWorkspaceEpisodeDepthPlane] = None
    action: Optional[str] = Field(default=None, max_length=2000)
    emotion: Optional[str] = Field(default=None, max_length=1000)


class StoryWorkspaceEpisodeStoryboardDialogue(_StoryWorkspaceDreamWireModel):
    """Canonical structured storyboard dialogue; never stringified from mappings."""

    speaker: str = Field(min_length=1, max_length=128)
    line: str = Field(min_length=1, max_length=2000)
    type: StoryWorkspaceEpisodeDialogueType


class StoryWorkspaceEpisodeShotCamera(_StoryWorkspaceDreamWireModel):
    """Allowlisted camera fields from the canonical eight-layer shot schema."""

    angle: Optional[str] = Field(default=None, max_length=255)
    height: Optional[str] = Field(default=None, max_length=255)
    movement: Optional[str] = Field(default=None, max_length=255)
    lens: Optional[str] = Field(default=None, max_length=255)


class StoryWorkspaceEpisodeShotTiming(_StoryWorkspaceDreamWireModel):
    """Allowlisted timing fields from the canonical shot schema."""

    duration_sec: Optional[float] = Field(default=None, ge=0.0, le=3600.0)
    transition_in: Optional[str] = Field(default=None, max_length=255)
    transition_out: Optional[str] = Field(default=None, max_length=255)


class StoryWorkspaceEpisodeStoryboardShot(_StoryWorkspaceDreamWireModel):
    """One canonical shot and its evidence-backed hierarchy links."""

    id: str = Field(pattern=r"^[0-9a-f]{32}$")
    shot_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    asset_scene_ref: Optional[str] = Field(default=None, max_length=255)
    declared_script_scene_ref: Optional[str] = Field(
        default=None,
        pattern=r"^S[0-9]{2,}$",
    )
    declared_narrative_beat_ref: Optional[str] = Field(
        default=None,
        pattern=r"^SC-[0-9]{2,}$",
    )
    script_scene_id: Optional[str] = Field(default=None, pattern=r"^[0-9a-f]{32}$")
    narrative_beat_id: Optional[str] = Field(default=None, pattern=r"^[0-9a-f]{32}$")
    association_status: StoryWorkspaceEpisodeAssociationStatus
    shot_type: Optional[str] = Field(default=None, max_length=255)
    characters: list[StoryWorkspaceEpisodeShotCharacter] = Field(
        default_factory=list,
        max_length=128,
    )
    camera: StoryWorkspaceEpisodeShotCamera = Field(
        default_factory=StoryWorkspaceEpisodeShotCamera,
    )
    visual: Optional[str] = Field(default=None, max_length=4000)
    dialogue: list[StoryWorkspaceEpisodeStoryboardDialogue] = Field(
        default_factory=list,
        max_length=128,
    )
    timing: StoryWorkspaceEpisodeShotTiming = Field(
        default_factory=StoryWorkspaceEpisodeShotTiming,
    )
    source_artifact: Literal[
        StoryWorkspaceEpisodeSourceArtifact.STORYBOARD
    ] = StoryWorkspaceEpisodeSourceArtifact.STORYBOARD
    source_revision: Optional[str] = Field(
        default=None,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,127}$",
    )
    generated_from: Optional[str] = Field(
        default=None,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9@._:-]{0,254}$",
    )

    @model_validator(mode="after")
    def linked_shot_has_a_script_scene(self) -> "StoryWorkspaceEpisodeStoryboardShot":
        if (
            self.association_status is StoryWorkspaceEpisodeAssociationStatus.LINKED
        ) != (self.script_scene_id is not None):
            raise ValueError("only linked shots may expose script_scene_id")
        return self


class StoryWorkspaceEpisodeAssociationDiagnostics(_StoryWorkspaceDreamWireModel):
    """Machine-readable hierarchy quality without positional inference."""

    beat_scene_coverage: StoryWorkspaceEpisodeAssociationCoverage
    scene_shot_coverage: StoryWorkspaceEpisodeAssociationCoverage
    missing_links: list[str] = Field(default_factory=list, max_length=2048)
    orphan_artifacts: list[str] = Field(default_factory=list, max_length=2048)

    @field_validator("missing_links", "orphan_artifacts")
    @classmethod
    def diagnostics_are_unique_and_safe(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("association diagnostics must be unique")
        if any(
            not value
            or len(value) > 512
            or any(ord(char) < 32 for char in value)
            for value in values
        ):
            raise ValueError("association diagnostics must be bounded plain text")
        return values


class StoryWorkspaceEpisodeNarrativeProjection(_StoryWorkspaceDreamWireModel):
    """Read-only Episode → Beat → Scene → Shot view-model projection."""

    episode_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    story_arc_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    overview: StoryWorkspaceEpisodeOverview
    narrative_beats: list[StoryWorkspaceEpisodeNarrativeBeat] = Field(
        default_factory=list,
        max_length=256,
    )
    scenes: list[StoryWorkspaceEpisodeScriptScene] = Field(
        default_factory=list,
        max_length=1000,
    )
    shots: list[StoryWorkspaceEpisodeStoryboardShot] = Field(
        default_factory=list,
        max_length=1000,
    )
    associations: StoryWorkspaceEpisodeAssociationDiagnostics

    @model_validator(mode="after")
    def projected_ids_are_unique(self) -> "StoryWorkspaceEpisodeNarrativeProjection":
        for values in (self.narrative_beats, self.scenes, self.shots):
            ids = [value.id for value in values]
            if len(ids) != len(set(ids)):
                raise ValueError("projected entity IDs must be unique within their kind")
        return self


class StoryWorkspaceEpisodePromptParameters(_StoryWorkspaceDreamWireModel):
    """Allowlisted creative settings; never raw renderer/tool arguments."""

    model: Optional[str] = Field(default=None, max_length=128)
    mode: Optional[str] = Field(default=None, max_length=128)
    duration_sec: Optional[float] = Field(default=None, ge=0.0, le=3600.0)
    motion_strength: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    camera_motion: Optional[str] = Field(default=None, max_length=255)
    aspect_ratio: Optional[str] = Field(
        default=None,
        max_length=32,
        pattern=r"^[0-9]{1,3}:[0-9]{1,3}$",
    )


class StoryWorkspaceEpisodePromptGenerability(_StoryWorkspaceDreamWireModel):
    """Allowlisted, user-facing prompt feasibility facts."""

    character_anchor: Optional[str] = Field(default=None, max_length=128)
    motion_feasibility: Optional[str] = Field(default=None, max_length=128)
    duration_budget: Optional[str] = Field(default=None, max_length=128)
    notes: Optional[str] = Field(default=None, max_length=2000)


class StoryWorkspaceEpisodePrompt(_StoryWorkspaceDreamWireModel):
    """One explicit shot prompt without any inferred render relationship."""

    id: str = Field(pattern=r"^[0-9a-f]{32}$")
    shot_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    kind: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")
    shot_view_id: Optional[str] = Field(default=None, pattern=r"^[0-9a-f]{32}$")
    association_status: StoryWorkspaceEpisodeAssociationStatus
    positive: str = Field(min_length=1, max_length=8000)
    negative: Optional[str] = Field(default=None, max_length=4000)
    parameters: StoryWorkspaceEpisodePromptParameters = Field(
        default_factory=StoryWorkspaceEpisodePromptParameters,
    )
    generability: StoryWorkspaceEpisodePromptGenerability = Field(
        default_factory=StoryWorkspaceEpisodePromptGenerability,
    )
    source_artifact: str = Field(
        pattern=r"^prompts/[A-Za-z0-9][A-Za-z0-9._-]{0,254}\.ya?ml$",
    )
    source_revision: str = Field(
        pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,127}$",
    )

    @model_validator(mode="after")
    def linked_prompt_has_a_shot(self) -> "StoryWorkspaceEpisodePrompt":
        if (
            self.association_status is StoryWorkspaceEpisodeAssociationStatus.LINKED
        ) != (self.shot_view_id is not None):
            raise ValueError("only linked prompts may expose shot_view_id")
        return self


class StoryWorkspaceEpisodePromptPage(_StoryWorkspaceDreamWireModel):
    """Bounded prompt page with a revision-bound opaque cursor."""

    items: list[StoryWorkspaceEpisodePrompt] = Field(
        default_factory=list,
        max_length=100,
    )
    total: _StoryWorkspaceDreamNonNegativeInt
    next_cursor: Optional[str] = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def page_items_are_unique(self) -> "StoryWorkspaceEpisodePromptPage":
        ids = [item.id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("prompt page IDs must be unique")
        if len(self.items) > self.total:
            raise ValueError("prompt page cannot exceed its total")
        return self


class StoryWorkspaceEpisodeArtifactSection(_StoryWorkspaceDreamWireModel):
    """A safe section whose ID is local to one source revision."""

    id: str = Field(pattern=r"^[0-9a-f]{32}$")
    level: StrictInt = Field(ge=1, le=6)
    title: str = Field(min_length=1, max_length=500)
    text: str = Field(default="", max_length=8000)
    source_artifact: Literal["renders/render-guide.md", "review-report.md"]
    source_revision: str = Field(
        pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,127}$",
    )


class StoryWorkspaceEpisodeRenderQueueEntry(_StoryWorkspaceDreamWireModel):
    """One explicit render queue row linked only to its shot."""

    id: str = Field(pattern=r"^[0-9a-f]{32}$")
    shot_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    shot_view_id: Optional[str] = Field(default=None, pattern=r"^[0-9a-f]{32}$")
    association_status: StoryWorkspaceEpisodeAssociationStatus
    duration_sec: Optional[float] = Field(default=None, ge=0.0, le=3600.0)
    risk: Optional[str] = Field(default=None, max_length=128)
    priority: Optional[str] = Field(default=None, max_length=64)
    renderer: Optional[str] = Field(
        default=None,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$",
    )
    status: Optional[str] = Field(
        default=None,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$",
    )
    source_artifact: Literal["renders/render-guide.md"] = "renders/render-guide.md"
    source_revision: str = Field(
        pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,127}$",
    )

    @model_validator(mode="after")
    def linked_queue_entry_has_a_shot(
        self,
    ) -> "StoryWorkspaceEpisodeRenderQueueEntry":
        if (
            self.association_status is StoryWorkspaceEpisodeAssociationStatus.LINKED
        ) != (self.shot_view_id is not None):
            raise ValueError("only linked queue entries may expose shot_view_id")
        return self


class StoryWorkspaceEpisodeRenderQueuePage(_StoryWorkspaceDreamWireModel):
    """Bounded explicit queue page; it intentionally has no prompt reference."""

    items: list[StoryWorkspaceEpisodeRenderQueueEntry] = Field(
        default_factory=list,
        max_length=100,
    )
    total: _StoryWorkspaceDreamNonNegativeInt
    next_cursor: Optional[str] = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def queue_page_items_are_unique(self) -> "StoryWorkspaceEpisodeRenderQueuePage":
        ids = [item.id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("render queue page IDs must be unique")
        if len(self.items) > self.total:
            raise ValueError("render queue page cannot exceed its total")
        return self


class StoryWorkspaceEpisodeRenderGuide(_StoryWorkspaceDreamWireModel):
    """Safe guide sections and an explicit queue; no registered media in v1."""

    sections: list[StoryWorkspaceEpisodeArtifactSection] = Field(
        default_factory=list,
        max_length=128,
    )
    queue: StoryWorkspaceEpisodeRenderQueuePage
    source_artifact: Literal["renders/render-guide.md"] = "renders/render-guide.md"
    source_revision: str = Field(
        pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,127}$",
    )


class StoryWorkspaceEpisodeReviewScope(str, Enum):
    """Declared or evidence-derived report scope, not a workflow status."""

    SCRIPT = "script"
    FULL_CHAIN = "full-chain"
    UNKNOWN = "unknown"


class StoryWorkspaceEpisodeReviewTargetKind(str, Enum):
    NARRATIVE_BEAT = "narrative-beat"
    SCRIPT_SCENE = "script-scene"
    SHOT = "shot"


class StoryWorkspaceEpisodeReviewTarget(_StoryWorkspaceDreamWireModel):
    """A stable location created only from an explicit source locator."""

    id: str = Field(pattern=r"^[0-9a-f]{32}$")
    kind: StoryWorkspaceEpisodeReviewTargetKind
    source_key: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    target_view_id: Optional[str] = Field(default=None, pattern=r"^[0-9a-f]{32}$")
    association_status: StoryWorkspaceEpisodeAssociationStatus
    section_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    source_artifact: Literal["review-report.md"] = "review-report.md"
    source_revision: str = Field(
        pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,127}$",
    )

    @model_validator(mode="after")
    def linked_review_target_has_a_view_id(
        self,
    ) -> "StoryWorkspaceEpisodeReviewTarget":
        if (
            self.association_status is StoryWorkspaceEpisodeAssociationStatus.LINKED
        ) != (self.target_view_id is not None):
            raise ValueError("only linked review targets may expose target_view_id")
        return self


class StoryWorkspaceEpisodeReviewedSourceRevision(_StoryWorkspaceDreamWireModel):
    """An explicit reviewed artifact revision declared by the report."""

    source_artifact: str = Field(
        pattern=(
            r"^(episode-outline\.md|script\.md|storyboard\.yaml|"
            r"prompts/[A-Za-z0-9][A-Za-z0-9._-]{0,254}\.ya?ml|"
            r"renders/render-guide\.md)$"
        ),
    )
    source_revision: str = Field(
        pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,127}$",
    )


class StoryWorkspaceEpisodeReviewReport(_StoryWorkspaceDreamWireModel):
    """Read-only review facts that never own Episode creative content."""

    scope: StoryWorkspaceEpisodeReviewScope
    overall_verdict: Optional[str] = Field(
        default=None,
        pattern=r"^[A-Z][A-Z0-9_ -]{0,63}$",
    )
    reviewed_artifacts: list[str] = Field(default_factory=list, max_length=256)
    source_revisions: list[StoryWorkspaceEpisodeReviewedSourceRevision] = Field(
        default_factory=list,
        max_length=256,
    )
    sections: list[StoryWorkspaceEpisodeArtifactSection] = Field(
        default_factory=list,
        max_length=128,
    )
    targets: list[StoryWorkspaceEpisodeReviewTarget] = Field(
        default_factory=list,
        max_length=2048,
    )
    source_artifact: Literal["review-report.md"] = "review-report.md"
    source_revision: str = Field(
        pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,127}$",
    )

    @field_validator("reviewed_artifacts")
    @classmethod
    def reviewed_artifacts_are_safe_and_unique(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("reviewed_artifacts must be unique")
        if any(
            not value
            or value.startswith("/")
            or ".." in value.split("/")
            or "\\" in value
            for value in values
        ):
            raise ValueError("reviewed_artifacts must be safe relative keys")
        return values


class StoryWorkspaceEpisodeAuxiliaryAssociationDiagnostics(
    _StoryWorkspaceDreamWireModel
):
    """Prompt/queue coverage without inventing a Prompt → Render edge."""

    shot_prompt_coverage: StoryWorkspaceEpisodeAssociationCoverage
    shot_render_queue_coverage: StoryWorkspaceEpisodeAssociationCoverage
    total_prompts: _StoryWorkspaceDreamNonNegativeInt
    total_queue_entries: _StoryWorkspaceDreamNonNegativeInt
    orphan_prompts: list[str] = Field(default_factory=list, max_length=2048)
    orphan_queue_entries: list[str] = Field(default_factory=list, max_length=2048)
    duplicate_queue_shot_ids: list[str] = Field(default_factory=list, max_length=2048)

    @field_validator(
        "orphan_prompts",
        "orphan_queue_entries",
        "duplicate_queue_shot_ids",
    )
    @classmethod
    def auxiliary_diagnostics_are_safe_and_unique(
        cls,
        values: list[str],
    ) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("auxiliary diagnostics must be unique")
        if any(
            not value
            or len(value) > 512
            or any(ord(char) < 32 for char in value)
            for value in values
        ):
            raise ValueError("auxiliary diagnostics must be bounded plain text")
        return values


class StoryWorkspaceEpisodeAuxiliaryProjection(_StoryWorkspaceDreamWireModel):
    """Read-only Prompt, Render Queue, and Review auxiliary view models."""

    manifest_revision: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    prompts: StoryWorkspaceEpisodePromptPage
    render_guide: Optional[StoryWorkspaceEpisodeRenderGuide] = None
    review: Optional[StoryWorkspaceEpisodeReviewReport] = None
    associations: StoryWorkspaceEpisodeAuxiliaryAssociationDiagnostics


class StoryWorkspaceEpisodeArtifactDocument(_StoryWorkspaceDreamWireModel):
    """Safe Markdown body from one canonical Episode document artifact."""

    relative_key: Literal[
        "episode-outline.md",
        "script.md",
        "review-report.md",
    ]
    markdown: str = Field(max_length=1024 * 1024)
    source_revision: str = Field(
        pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,127}$",
    )

    @field_validator("markdown")
    @classmethod
    def markdown_is_bounded_non_html_text(cls, value: str) -> str:
        if re.search(r"<!--[\s\S]*?-->|</?[A-Za-z][^>]*>", value):
            raise ValueError("artifact Markdown cannot contain raw HTML")
        if any(
            ord(character) == 127
            or (ord(character) < 32 and character not in "\t\n\r")
            for character in value
        ):
            raise ValueError("artifact Markdown cannot contain control characters")
        return value


class StoryWorkspaceEpisodeArtifactSurface(_StoryWorkspaceDreamWireModel):
    """Actor-scoped Episode manifest plus normalized read-only projections."""

    run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    opaque_episode_id: Optional[str] = Field(
        default=None,
        pattern=r"^[0-9a-f]{32}$",
    )
    manifest_revision: Optional[str] = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    etag: Optional[str] = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    binding_availability: StoryWorkspaceEpisodeBindingAvailability
    binding_recovery: StoryWorkspaceEpisodeBindingRecovery
    artifacts: list[StoryWorkspaceEpisodeArtifactManifestEntry] = Field(
        default_factory=list,
        max_length=256,
    )
    documents: list[StoryWorkspaceEpisodeArtifactDocument] = Field(
        default_factory=list,
        max_length=3,
    )
    narrative: Optional[StoryWorkspaceEpisodeNarrativeProjection] = None
    auxiliary: Optional[StoryWorkspaceEpisodeAuxiliaryProjection] = None
    workflow: Optional[StoryWorkspaceEpisodeWorkflowProjection] = None

    @model_validator(mode="after")
    def binding_controls_episode_surface(
        self,
    ) -> "StoryWorkspaceEpisodeArtifactSurface":
        if self.binding_availability is StoryWorkspaceEpisodeBindingAvailability.BOUND:
            if (
                self.opaque_episode_id is None
                or self.manifest_revision is None
                or self.etag is None
            ):
                raise ValueError("bound surfaces require opaque identity and revisions")
            expected_roots = {
                "episode-outline.md",
                "script.md",
                "storyboard.yaml",
                "prompts/",
                "renders/",
                "review-report.md",
            }
            actual_roots = {artifact.relative_key for artifact in self.artifacts}
            if len(self.artifacts) != len(expected_roots) or actual_roots != expected_roots:
                raise ValueError("bound surfaces require all six root artifacts")
        elif (
            self.opaque_episode_id is not None
            or self.manifest_revision is not None
            or self.etag is not None
            or self.artifacts
            or self.documents
            or self.narrative is not None
            or self.auxiliary is not None
            or self.workflow is not None
        ):
            raise ValueError("unbound surfaces cannot expose Episode artifacts")
        relative_keys = [artifact.relative_key for artifact in self.artifacts]
        if len(relative_keys) != len(set(relative_keys)):
            raise ValueError("artifacts must have unique relative_key values")
        document_keys = [document.relative_key for document in self.documents]
        if len(document_keys) != len(set(document_keys)):
            raise ValueError("documents must have unique relative_key values")
        manifest_by_key = {artifact.relative_key: artifact for artifact in self.artifacts}
        for document in self.documents:
            manifest = manifest_by_key.get(document.relative_key)
            if (
                manifest is None
                or manifest.availability
                is not StoryWorkspaceEpisodeArtifactAvailability.AVAILABLE
                or manifest.content_revision != document.source_revision
            ):
                raise ValueError("documents require matching available artifact revisions")
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
    "StoryWorkspaceDreamAgentActivityContent",
    "StoryWorkspaceDreamAgentContent",
    "StoryWorkspaceDreamAgentMessageAccepted",
    "StoryWorkspaceDreamAgentMessageCommand",
    "StoryWorkspaceDreamAgentMessageSnapshot",
    "StoryWorkspaceDreamAgentTextContent",
    "StoryWorkspaceDreamAgentToolConfirmation",
    "StoryWorkspaceDreamAgentToolConfirmationAccepted",
    "StoryWorkspaceDreamAgentToolConfirmationCommand",
    "StoryWorkspaceDreamAgentToolConfirmationNetwork",
    "StoryWorkspaceDreamAgentToolConfirmationOption",
    "StoryWorkspaceDreamAgentToolConfirmationQuestion",
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
    "StoryWorkspaceEpisodeAction",
    "StoryWorkspaceEpisodeActionAvailability",
    "StoryWorkspaceEpisodeActionAccepted",
    "StoryWorkspaceEpisodeActionCanonicalInput",
    "StoryWorkspaceEpisodeActionContinueCommand",
    "StoryWorkspaceEpisodeActionDiagnostic",
    "StoryWorkspaceEpisodeActionDispatchState",
    "StoryWorkspaceEpisodeActionOption",
    "StoryWorkspaceEpisodeActionOptionV2",
    "StoryWorkspaceEpisodeActionProjectionV2",
    "StoryWorkspaceEpisodeActionResolution",
    "StoryWorkspaceEpisodeActionTarget",
    "StoryWorkspaceEpisodeArtifactCanonicalInput",
    "StoryWorkspaceAssetContextCanonicalInput",
    "StoryWorkspaceEpisodeBindingToolInput",
    "StoryWorkspaceEpisodeArtifactSection",
    "StoryWorkspaceEpisodeAuxiliaryAssociationDiagnostics",
    "StoryWorkspaceEpisodeAuxiliaryProjection",
    "StoryWorkspaceEpisodePrompt",
    "StoryWorkspaceEpisodePromptGenerability",
    "StoryWorkspaceEpisodePromptPage",
    "StoryWorkspaceEpisodePromptParameters",
    "StoryWorkspaceEpisodeRenderGuide",
    "StoryWorkspaceEpisodeRenderQueueEntry",
    "StoryWorkspaceEpisodeRenderQueuePage",
    "StoryWorkspaceEpisodeReviewReport",
    "StoryWorkspaceEpisodeReviewScope",
    "StoryWorkspaceEpisodeReviewTarget",
    "StoryWorkspaceEpisodeReviewTargetKind",
    "StoryWorkspaceEpisodeReviewedSourceRevision",
    "StoryWorkspaceEpisodeRelation",
    "StoryWorkspaceEpisodeWorkflowCompletion",
    "StoryWorkspaceEpisodeWorkflowCompletionToolInput",
    "StoryWorkspaceEpisodeWorkflowFile",
    "StoryWorkspaceEpisodeWorkflowProjection",
    "StoryWorkspaceProjectArtifactCanonicalInput",
    "StoryWorkspaceWorkflowFactCanonicalInput",
    "StoryWorkspaceEpisodeBindingRecoveryCommand",
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
