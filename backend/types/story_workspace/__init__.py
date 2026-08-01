"""Canonical backend type contract for the Story Workspace feature.

The models in this module intentionally contain no persistence or validation
logic.  They describe the data exchanged by Story Workspace database, API,
review, and Agent-integration layers.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar


TYPE_CONTRACT_VERSION = "1.0.0"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class ContentStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class StoryType(str, Enum):
    SHORT = "short"
    LONG = "long"
    SCRIPT = "script"
    OUTLINE = "outline"


class RoleType(str, Enum):
    PROTAGONIST = "protagonist"
    SUPPORTING = "supporting"
    EXTRA = "extra"


class BatchAction(str, Enum):
    CONFIRM = "confirm"
    REJECT = "reject"
    ARCHIVE = "archive"


class ResourceType(str, Enum):
    STORY = "story"
    CHARACTER = "character"
    SCENE = "scene"


@dataclass
class StoryWorkspaceStory:
    id: str
    identifier: str
    title: str
    description: Optional[str] = None
    status: ContentStatus = ContentStatus.DRAFT
    review_status: ReviewStatus = ReviewStatus.PENDING
    type: StoryType = StoryType.SHORT
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
    review_status: ReviewStatus = ReviewStatus.PENDING
    agent_generated: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


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
    review_status: ReviewStatus = ReviewStatus.PENDING
    agent_generated: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


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
    role_type: RoleType = RoleType.SUPPORTING
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
class PaginationInfo:
    page: int
    per_page: int
    total: int
    total_pages: int


T = TypeVar("T")


@dataclass
class PaginatedResponse(Generic[T]):
    data: List[T]
    pagination: PaginationInfo


@dataclass
class StoryFilter:
    q: Optional[str] = None
    review_status: List[ReviewStatus] = field(default_factory=list)
    status: List[ContentStatus] = field(default_factory=list)
    type: List[StoryType] = field(default_factory=list)
    sort: str = "updated_at"
    order: str = "desc"
    page: int = 1
    per_page: int = 20


@dataclass
class CharacterFilter:
    q: Optional[str] = None
    review_status: List[ReviewStatus] = field(default_factory=list)
    sort: str = "updated_at"
    order: str = "desc"
    page: int = 1
    per_page: int = 20


@dataclass
class SceneFilter:
    q: Optional[str] = None
    review_status: List[ReviewStatus] = field(default_factory=list)
    story_id: Optional[str] = None
    sort: str = "updated_at"
    order: str = "desc"
    page: int = 1
    per_page: int = 20


@dataclass
class ReviewActionRequest:
    review_notes: Optional[str] = None


@dataclass
class BatchReviewRequest:
    action: BatchAction
    ids: List[str]
    resource_type: ResourceType
    review_notes: Optional[str] = None


@dataclass
class BatchReviewResponse:
    success: bool
    action: BatchAction
    resource_type: ResourceType
    total_requested: int
    total_updated: int
    skipped_ids: List[str] = field(default_factory=list)
    updated_items: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class WorkspaceStats:
    total_stories: int = 0
    total_characters: int = 0
    total_scenes: int = 0
    pending_review_count: int = 0
    confirmed_count: int = 0
    rejected_count: int = 0


@dataclass
class AgentCharacterOutput:
    name: str
    identity: Optional[str] = None
    personality: Optional[str] = None
    background: Optional[str] = None
    catchphrase: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class AgentSceneOutput:
    name: str
    description: Optional[str] = None
    order_index: int = 0


@dataclass
class AgentStoryOutput:
    title: str
    description: Optional[str] = None
    type: StoryType = StoryType.SHORT
    content: Optional[str] = None
    characters: List[AgentCharacterOutput] = field(default_factory=list)
    scenes: List[AgentSceneOutput] = field(default_factory=list)


@dataclass
class AgentOutputRequest(AgentStoryOutput):
    """Direct request body accepted by the Agent-output integration endpoint."""


__all__ = [
    "TYPE_CONTRACT_VERSION",
    "AgentCharacterOutput",
    "AgentOutputRequest",
    "AgentSceneOutput",
    "AgentStoryOutput",
    "BatchAction",
    "BatchReviewRequest",
    "BatchReviewResponse",
    "CharacterFilter",
    "ContentStatus",
    "PaginatedResponse",
    "PaginationInfo",
    "ResourceType",
    "ReviewActionRequest",
    "ReviewStatus",
    "RoleType",
    "SceneFilter",
    "StoryFilter",
    "StoryType",
    "StoryWorkspaceCharacter",
    "StoryWorkspaceCharacterDetail",
    "StoryWorkspaceScene",
    "StoryWorkspaceSceneCharacter",
    "StoryWorkspaceSceneDetail",
    "StoryWorkspaceStory",
    "StoryWorkspaceStoryCharacter",
    "StoryWorkspaceStoryDetail",
    "StoryWorkspaceWorkspace",
    "WorkspaceStats",
]
