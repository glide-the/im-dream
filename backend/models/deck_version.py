"""Deck aggregate draft and immutable content-version API contracts.

[Input] Authenticated Deck identities, aggregate draft revisions, and explicit commit metadata.
[Output] Strict version state, preview, commit, history, and conflict DTOs.
[Pos] Deck content-version model node in backend/models.
[Sync] 2026-08-16: introduce CozeLoop-inspired draft/explicit-commit contracts without Workflow.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DeckVersionMutationRequest(_StrictModel):
    expected_draft_revision: int = Field(ge=1)
    expected_base_version: int | None = Field(default=None, ge=1)


class DeckVersionCommitRequest(DeckVersionMutationRequest):
    description: str | None = Field(default=None, max_length=200)


class DeckVersionChange(_StrictModel):
    scope: Literal["deck", "agent_type", "agents", "claude_plugins", "runtime_binding"]
    change_type: Literal["added", "removed", "modified"]
    label: str
    fields: list[str] = Field(default_factory=list)


class DeckVersionSummary(_StrictModel):
    version: int = Field(ge=1)
    base_version: int | None = Field(default=None, ge=1)
    source_draft_revision: int = Field(ge=1)
    description: str | None = None
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    created_by: int
    created_at: datetime
    runtime_plugin_version: str | None = None


class DeckVersionState(_StrictModel):
    deck_id: str = Field(min_length=1)
    draft_revision: int = Field(ge=1)
    latest_version: int | None = Field(default=None, ge=1)
    published_draft_revision: int = Field(ge=0)
    dirty: bool
    status: Literal["unpublished", "draft", "published"]
    next_version: int = Field(ge=1)


class DeckVersionPreviewResponse(DeckVersionState):
    target_version: int = Field(ge=1)
    changes: list[DeckVersionChange]
    impact: list[str]


class DeckVersionCommitResponse(_StrictModel):
    deck_id: str = Field(min_length=1)
    version: DeckVersionSummary
    state: DeckVersionState


class DeckVersionHistoryResponse(_StrictModel):
    deck_id: str = Field(min_length=1)
    current: DeckVersionState
    versions: list[DeckVersionSummary]


class DeckVersionDetailResponse(DeckVersionSummary):
    deck_id: str = Field(min_length=1)
    snapshot: dict[str, object]


__all__ = [
    "DeckVersionChange",
    "DeckVersionCommitRequest",
    "DeckVersionCommitResponse",
    "DeckVersionDetailResponse",
    "DeckVersionHistoryResponse",
    "DeckVersionMutationRequest",
    "DeckVersionPreviewResponse",
    "DeckVersionState",
    "DeckVersionSummary",
]
