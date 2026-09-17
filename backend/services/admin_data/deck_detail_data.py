# [Input] Published Admin Deck detail contract, current OAuth and original Voice projection.
# [Output] Closed owned aggregate restored to the original public Deck/Voice response.
# [Pos] Deck detail read consumer; Admin owns visibility, ordering and policy/version decoration.
# [Sync] 2026-09-15: consume one read; default/create/list/install data remains pending.
# [Sync] 2026-09-15: share original Deck policy fields and exact-true validation with list DTOs.
from __future__ import annotations

import json
from typing import Literal
from pydantic import field_validator, model_validator
from voice_projection import _parse_voice_row
from .chat_models import ChatStrictDTO, EntityId, NonnegativeSafeInteger, PositiveSafeInteger, validate_timestamp_text
from .client import AdminDataClient, DomainOperation
from .deck_version_data import require_deck_capabilities
from .deck_version_models import DeckIdInputDTO, SafeInteger
from .errors import invalid_response
from .models import CanonicalUserId, OperationCapabilityDTO, PrincipalDTO


class OwnedRowDTO(ChatStrictDTO):
    id: EntityId
    owner_id: CanonicalUserId | None
    is_system: bool | None
    parent_id: str | None
    enabled: bool | None
    has_local_changes: bool | None
    order_index: SafeInteger | None
    created_at: str | None
    updated_at: str | None
    name: str
    name_zh: str | None
    name_en: str | None
    icon: str | None
    color: str | None
    _timestamps = field_validator("created_at", "updated_at")(validate_timestamp_text)

    @field_validator("owner_id")
    @classmethod
    def canonical_owner(cls, value):
        return PrincipalDTO.validate_canonical_id(value) if value is not None else None

    def public_projection(self):
        result = self.model_dump()
        result["owner_id"] = int(self.owner_id) if self.owner_id is not None else None
        return result


class DeckVoiceDTO(OwnedRowDTO):
    deck_id: EntityId
    system_prompt: str
    thread_id: str | None
    memory_workspace_config_json: str | None

    def public_projection(self):
        result = super().public_projection()
        result["memory_workspace_config"] = result.pop("memory_workspace_config_json")
        return _parse_voice_row(result)


class DeckRowDTO(OwnedRowDTO):
    description: str | None
    description_zh: str | None
    description_en: str | None
    published: bool | None
    author_name: str | None
    install_count: SafeInteger | None
    draft_revision: PositiveSafeInteger
    latest_version: NonnegativeSafeInteger
    published_draft_revision: NonnegativeSafeInteger


class DeckPolicyDTO(DeckRowDTO):
    agent_type: Literal["chat", "dream"]
    agent_type_revision: NonnegativeSafeInteger
    deck_plugin_id: str | None
    deck_plugin_version: str | None
    can_publish: bool
    publish_block_reason: Literal["default_initialized"] | None
    deck_version_capability: Literal[True]
    deck_version: PositiveSafeInteger | None
    deck_version_dirty: bool
    deck_version_status: Literal["unpublished", "draft", "published"]
    next_deck_version: PositiveSafeInteger

    @model_validator(mode="before")
    @classmethod
    def exact_capability_bool(cls, value):
        if isinstance(value, dict) and value.get("deck_version_capability") is not True:
            raise ValueError("Deck capability must be true")
        return value


class DeckDetailDTO(DeckPolicyDTO):
    voices: list[DeckVoiceDTO]

    def public_projection(self):
        result = super().public_projection()
        result["voices"] = [voice.public_projection() for voice in self.voices]
        json.dumps(result, allow_nan=False)
        return result


class DeckDetailOutputDTO(ChatStrictDTO):
    deck: DeckDetailDTO | None


READ_DECK_DETAIL = DomainOperation(OperationCapabilityDTO(name="deck.detail", kind="read", user_scope="dream:read", background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256="52f1448eaa4935c662bec1811633a80d4ffc4ed764503210edc541a99369e964"),
    DeckIdInputDTO, DeckDetailOutputDTO)


class AdminDeckDetailData:
    def __init__(self, client: AdminDataClient):
        self._client = client

    def detail(self, input_dto: DeckIdInputDTO, request_id: str, *, access_token: str) -> dict | None:
        require_deck_capabilities(self._client, request_id)
        result = self._client.execute(READ_DECK_DETAIL, input_dto, request_id, access_token=access_token)
        if result.deck is None:
            return None
        if result.deck.id != input_dto.deck_id or any(voice.deck_id != input_dto.deck_id for voice in result.deck.voices):
            raise invalid_response(request_id)
        try:
            return result.deck.public_projection()
        except (ValueError, TypeError):
            raise invalid_response(request_id) from None
