"""Canonical contracts for the Story Workspace domain.

This module owns the data shapes shared by Story Workspace API, review, and
Agent-integration layers. Persistence and business workflows remain in their
respective router and service modules.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator


STORY_WORKSPACE_CONTRACT_VERSION = "1.1.0"
STORY_WORKSPACE_REVIEW_NOTES_MAX_LENGTH = 2000


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


class StoryWorkspaceResourceType(str, Enum):
    STORY = "story"
    CHARACTER = "character"
    SCENE = "scene"


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
    "StoryWorkspacePaginatedResponse",
    "StoryWorkspacePaginationInfo",
    "StoryWorkspaceResourceType",
    "StoryWorkspaceReviewActionRequest",
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
    "StoryWorkspaceWorkspace",
    "StoryWorkspaceWorkspacePatch",
]
