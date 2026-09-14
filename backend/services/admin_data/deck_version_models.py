# [Input] Actual Admin deckVoiceDto content-version and closed v1 snapshot schemas.
# [Output] Strict wire DTOs preserving canonical identity, ISO microseconds and raw snapshot JSON.
# [Pos] Read-only Deck content schema boundary; no snapshot/diff/hash or database implementation.
# [Sync] 2026-09-15: consume the five published Deck content-version operation shapes.
from __future__ import annotations

import json
from typing import Annotated, Literal

from pydantic import Field, JsonValue, field_validator

from .chat_models import ChatStrictDTO, EntityId, NonnegativeSafeInteger, PositiveSafeInteger, validate_timestamp_text
from .models import CanonicalUserId, PrincipalDTO

SafeInteger = Annotated[int, Field(ge=-9_007_199_254_740_991, le=9_007_199_254_740_991)]
Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


class DeckIdInputDTO(ChatStrictDTO):
    deck_id: EntityId


class DeckVersionMutationInputDTO(DeckIdInputDTO):
    expected_draft_revision: PositiveSafeInteger
    expected_base_version: PositiveSafeInteger | None


class DeckVersionCommitInputDTO(DeckVersionMutationInputDTO):
    description: Annotated[str, Field(max_length=200)] | None


class DeckVersionHistoryInputDTO(DeckIdInputDTO):
    limit: Annotated[int, Field(ge=1, le=100)]


class DeckVersionDetailInputDTO(DeckIdInputDTO):
    version: PositiveSafeInteger


class DeckVersionStateDTO(DeckIdInputDTO):
    draft_revision: PositiveSafeInteger
    latest_version: PositiveSafeInteger | None
    published_draft_revision: NonnegativeSafeInteger
    dirty: bool
    status: Literal["unpublished", "draft", "published"]
    next_version: PositiveSafeInteger


class DeckVersionChangeDTO(ChatStrictDTO):
    scope: Literal["deck", "agent_type", "agents", "claude_plugins", "runtime_binding"]
    change_type: Literal["added", "removed", "modified"]
    label: str
    fields: list[str]


class DeckVersionSummaryDTO(ChatStrictDTO):
    version: PositiveSafeInteger
    base_version: PositiveSafeInteger | None
    source_draft_revision: PositiveSafeInteger
    description: str | None
    content_hash: Digest
    created_by: CanonicalUserId
    created_at: str
    runtime_plugin_version: str | None
    _timestamp = field_validator("created_at")(validate_timestamp_text)

    @field_validator("created_by")
    @classmethod
    def validate_created_by(cls, value: str) -> str:
        return PrincipalDTO.validate_canonical_id(value)


class DeckVersionPreviewDTO(DeckVersionStateDTO):
    target_version: PositiveSafeInteger
    changes: list[DeckVersionChangeDTO]
    impact: list[str]


class DeckVersionCommitDTO(DeckIdInputDTO):
    version: DeckVersionSummaryDTO
    state: DeckVersionStateDTO


class DeckVersionHistoryDTO(DeckIdInputDTO):
    current: DeckVersionStateDTO
    versions: list[DeckVersionSummaryDTO]


class LocalizedContentDTO(ChatStrictDTO):
    name: str
    name_zh: str | None
    name_en: str | None
    description: str | None
    description_zh: str | None
    description_en: str | None
    icon: str | None
    color: str | None


class SnapshotDeckDTO(LocalizedContentDTO):
    id: EntityId
    enabled: bool | None
    order_index: SafeInteger | None


class SnapshotAgentDTO(ChatStrictDTO):
    id: EntityId
    name: str
    name_zh: str | None
    name_en: str | None
    system_prompt: str
    icon: str | None
    color: str | None
    enabled: bool
    order_index: SafeInteger | None
    memory_workspace_config: JsonValue


class SnapshotPluginDTO(ChatStrictDTO):
    plugin_installation_id: EntityId
    package_spec: EntityId
    resolved_version: EntityId
    artifact_digest: str
    enabled: bool
    order_index: SafeInteger


class SnapshotBindingDTO(ChatStrictDTO):
    deck_plugin_id: EntityId
    deck_plugin_version: EntityId
    binding_revision: PositiveSafeInteger


class DeckContentSnapshotDTO(ChatStrictDTO):
    schema_version: Literal["deck-content/v1"]
    deck: SnapshotDeckDTO
    agent_type: Literal["chat", "dream"]
    agents: list[SnapshotAgentDTO]
    claude_plugins: list[SnapshotPluginDTO]
    runtime_binding: SnapshotBindingDTO | None


def _reject_constant(_value):
    raise ValueError("Non-JSON number")


class DeckVersionDetailDTO(DeckVersionSummaryDTO, DeckIdInputDTO):
    snapshot_json: str

    @field_validator("snapshot_json")
    @classmethod
    def validate_snapshot(cls, value):
        try:
            DeckContentSnapshotDTO.model_validate(json.loads(value, parse_constant=_reject_constant))
        except (ValueError, TypeError):
            raise ValueError("Invalid Deck content snapshot") from None
        # Shape validation must not rewrite numeric lexemes or canonical bytes.
        return value

    def public_projection(self) -> dict:
        result = self.model_dump(exclude={"snapshot_json"})
        result["created_by"] = int(self.created_by)
        result["snapshot"] = json.loads(self.snapshot_json, parse_constant=_reject_constant)
        return result
