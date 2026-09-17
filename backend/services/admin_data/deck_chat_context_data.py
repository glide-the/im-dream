# [Input] Admin Registry105 Deck chat-context storage contract and current request OAuth.
# [Output] Strict actor-owned Deck/Voice/plugin-ref status snapshot for Dream policy and prompt assembly.
# [Pos] Public Chat data consumer; Admin owns ORM/access while Dream owns enabled/ready rules and Runtime.
# [Sync] 2026-09-15: consume the status-projection contract without Dream PostgreSQL fallback.
"""Typed Registry105 consumer for one immutable Deck chat-context read."""

from __future__ import annotations

from dataclasses import dataclass
from pydantic import TypeAdapter

from .chat_models import ChatStrictDTO, EntityId
from .client import AdminDataClient, DomainOperation
from .deck_refs_data import ArtifactDigest, InstallationStatus, PgOrder
from .errors import AdminDataError, invalid_response
from .models import CanonicalUserId, OperationCapabilityDTO, PrincipalDTO
from .workflow_data import require_workflow_capabilities


class DeckChatContextInputDTO(ChatStrictDTO):
    deck_id: EntityId
    voice_id: EntityId | None


class DeckChatContextDeckDTO(ChatStrictDTO):
    id: EntityId
    name: str
    name_zh: str | None
    name_en: str | None
    description: str | None
    description_zh: str | None
    description_en: str | None
    enabled: bool | None


class DeckChatContextVoiceDTO(ChatStrictDTO):
    id: EntityId
    name: str
    name_zh: str | None
    name_en: str | None
    system_prompt: str
    enabled: bool | None


class DeckChatContextPluginRefDTO(ChatStrictDTO):
    plugin_installation_id: EntityId
    package_spec: str
    resolved_version: EntityId
    artifact_digest: ArtifactDigest
    order_index: PgOrder
    enabled: bool
    installation_status: InstallationStatus


class DeckChatContextOutputDTO(ChatStrictDTO):
    deck: DeckChatContextDeckDTO
    voices: list[DeckChatContextVoiceDTO]
    plugin_refs: list[DeckChatContextPluginRefDTO]


RESOLVE_DECK_CHAT_CONTEXT = DomainOperation(
    OperationCapabilityDTO(
        name="deck-chat-context.resolve",
        kind="read",
        user_scope="dream:read",
        background_scope=None,
        input_schema_version=1,
        output_schema_version=1,
        contract_sha256="c956db969d76208bd99d2d8ad2c9e7eb2f6154d835388424e7db5ca09ca74b97",
    ),
    DeckChatContextInputDTO,
    DeckChatContextOutputDTO,
)
DECK_CHAT_CONTEXT_OPERATIONS = (RESOLVE_DECK_CHAT_CONTEXT,)


@dataclass(frozen=True, slots=True)
class AdminDeckChatContextResolution:
    canonical_user_id: str
    deck_id: str
    voice_id: str | None
    snapshot: DeckChatContextOutputDTO

    def __post_init__(self) -> None:
        PrincipalDTO.validate_canonical_id(
            TypeAdapter(CanonicalUserId).validate_python(
                self.canonical_user_id,
                strict=True,
            )
        )
        if self.snapshot.deck.id != self.deck_id:
            raise ValueError("Deck chat-context snapshot does not match selection")

    def context_for(
        self,
        *,
        actor_id: str,
        deck_id: str,
        voice_id: str | None,
    ) -> DeckChatContextOutputDTO:
        if (
            self.canonical_user_id != str(actor_id)
            or self.deck_id != deck_id
            or self.voice_id != voice_id
        ):
            raise AdminDataError("DREAM_DELEGATION_ENTITY_DENIED", 403)
        return self.snapshot


class AdminDeckChatContextData:
    def __init__(
        self,
        client: AdminDataClient,
        *,
        canonical_user_id: str,
    ) -> None:
        self._client = client
        self._canonical_user_id = PrincipalDTO.validate_canonical_id(
            TypeAdapter(CanonicalUserId).validate_python(
                canonical_user_id,
                strict=True,
            )
        )

    def resolve(
        self,
        input_dto: DeckChatContextInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> AdminDeckChatContextResolution:
        require_workflow_capabilities(self._client, request_id)
        result = self._client.execute(
            RESOLVE_DECK_CHAT_CONTEXT,
            input_dto,
            request_id,
            access_token=access_token,
        )
        voice_ids = [voice.id for voice in result.voices]
        ref_ids = [ref.plugin_installation_id for ref in result.plugin_refs]
        if (
            result.deck.id != input_dto.deck_id
            or len(voice_ids) != len(set(voice_ids))
            or len(ref_ids) != len(set(ref_ids))
            or [ref.order_index for ref in result.plugin_refs]
            != sorted(ref.order_index for ref in result.plugin_refs)
            or (
                input_dto.voice_id is not None
                and any(voice_id != input_dto.voice_id for voice_id in voice_ids)
            )
        ):
            raise invalid_response(request_id)
        return AdminDeckChatContextResolution(
            canonical_user_id=self._canonical_user_id,
            deck_id=input_dto.deck_id,
            voice_id=input_dto.voice_id,
            snapshot=result,
        )
