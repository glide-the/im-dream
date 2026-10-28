# [Sync] 2026-10-28: consume the exact actor Deck/Agent catalog capability in a single Admin operation.
# [Input] Published Deck list contract, current OAuth and original per-mode public fields.
# [Output] Original owned/community Deck lists with counts, author fields and canonical ID projection.
# [Pos] Read-only list consumer; Admin owns visibility, ordering and all policy decoration.
# [Sync] 2026-09-15: consume both list modes without default/installation/file side effects.
from __future__ import annotations

from .chat_models import ChatStrictDTO, NonnegativeSafeInteger
from .client import AdminDataClient, DomainOperation
from .deck_detail_data import DeckPolicyDTO, DeckVoiceDTO
from .deck_version_data import require_deck_capabilities
from .models import OperationCapabilityDTO
from .errors import invalid_response


class DeckListInputDTO(ChatStrictDTO):
    community: bool


class DeckListItemDTO(DeckPolicyDTO):
    voice_count: NonnegativeSafeInteger
    total_voice_count: NonnegativeSafeInteger | None
    author_display_name: str | None

    def public_projection(self, *, community: bool):
        result = super().public_projection()
        result.pop("total_voice_count" if community else "author_display_name")
        return result


class DeckListOutputDTO(ChatStrictDTO):
    decks: list[DeckListItemDTO]


LIST_DECKS = DomainOperation(OperationCapabilityDTO(name="deck.list", kind="read", user_scope="dream:read", background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256="4c8b3d396a30c9c3bb534aca04f50e4d90dad37dd9ecb96ad8c217894e6eb8eb"),
    DeckListInputDTO, DeckListOutputDTO)


class DeckCatalogInputDTO(ChatStrictDTO):
    pass


class DeckCatalogItemDTO(DeckListItemDTO):
    voices: list[DeckVoiceDTO]

    def public_projection(self, *, community: bool = False):
        result = super().public_projection(community=community)
        result["voices"] = [voice.public_projection() for voice in self.voices]
        return result


class DeckCatalogOutputDTO(ChatStrictDTO):
    decks: list[DeckCatalogItemDTO]


READ_DECK_CATALOG = DomainOperation(OperationCapabilityDTO(name="deck.catalog", kind="read", user_scope="dream:read", background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256="0c53861e1a635742e37f7b26ab954a57af1f550261d3ddc1ea5dbfb17f574a5e"),
    DeckCatalogInputDTO, DeckCatalogOutputDTO)


class AdminDeckListData:
    def __init__(self, client: AdminDataClient):
        self._client = client

    def list(self, input_dto: DeckListInputDTO, request_id: str, *, access_token: str):
        require_deck_capabilities(self._client, request_id)
        result = self._client.execute(LIST_DECKS, input_dto, request_id, access_token=access_token)
        return {"decks": [item.public_projection(community=input_dto.community) for item in result.decks]}

    def catalog(self, input_dto: DeckCatalogInputDTO, request_id: str, *, access_token: str):
        require_deck_capabilities(self._client, request_id)
        result = self._client.execute(READ_DECK_CATALOG, input_dto, request_id, access_token=access_token)
        deck_ids: set[str] = set()
        voice_ids: set[str] = set()
        for deck in result.decks:
            if deck.id in deck_ids:
                raise invalid_response(request_id)
            deck_ids.add(deck.id)
            for voice in deck.voices:
                if voice.deck_id != deck.id or voice.id in voice_ids:
                    raise invalid_response(request_id)
                voice_ids.add(voice.id)
        try:
            return {"decks": [deck.public_projection() for deck in result.decks]}
        except (ValueError, TypeError):
            raise invalid_response(request_id) from None
