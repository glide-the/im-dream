# [Input] Actual five Admin Deck mutation contracts and current request OAuth.
# [Output] Original Deck mutation results with optional fields and original-ID receipt recovery.
# [Pos] Deck mutation consumer; Admin owns locks/policy/publication/collection/draft transactions.
# [Sync] 2026-09-15: consume five writes; list/detail/default/plugin evidence remain separate.
from __future__ import annotations

from .chat_models import ChatStrictDTO, EntityId, NonnegativeSafeInteger, PresentFieldsDTO
from .client import AdminDataClient, DomainOperation
from .deck_version_data import require_deck_capabilities
from .deck_version_models import DeckIdInputDTO, SafeInteger
from .errors import AdminDataError
from .models import OperationCapabilityDTO
from .social_data import SocialSuccessDTO
from .voice_data import VoiceChangedDTO


class DeckUpdateFieldsDTO(PresentFieldsDTO):
    name: str = None
    name_zh: str | None = None
    name_en: str | None = None
    description: str | None = None
    description_zh: str | None = None
    description_en: str | None = None
    icon: str | None = None
    color: str | None = None
    enabled: bool = None
    order_index: SafeInteger | None = None


class DeckUpdateInputDTO(DeckIdInputDTO):
    updates: DeckUpdateFieldsDTO


class DeckUpdateRequestDTO(ChatStrictDTO):
    name: str | None = None
    name_zh: str | None = None
    name_en: str | None = None
    description: str | None = None
    description_zh: str | None = None
    description_en: str | None = None
    icon: str | None = None
    color: str | None = None
    enabled: bool | None = None
    order_index: SafeInteger | None = None

    def domain_input(self, deck_id):
        return DeckUpdateInputDTO(deck_id=deck_id, updates=DeckUpdateFieldsDTO(**self.model_dump(exclude_none=True)))


class DeckCreatedDTO(ChatStrictDTO):
    deck_id: EntityId


class DeckPublicationDTO(ChatStrictDTO):
    published: bool


class DeckSyncedDTO(SocialSuccessDTO):
    synced_voices: NonnegativeSafeInteger


def _operation(name, input_dto, output_dto, digest):
    return DomainOperation(OperationCapabilityDTO(name=name, kind='write', user_scope='dream:write', background_scope=None,
        input_schema_version=1, output_schema_version=1, contract_sha256=digest), input_dto, output_dto)


UPDATE_DECK = _operation('deck.update', DeckUpdateInputDTO, VoiceChangedDTO, '4111833406be119dacffda8b06a89aef2c5cacf16038c6c45234953fb458455d')
DELETE_DECK = _operation('deck.delete', DeckIdInputDTO, VoiceChangedDTO, '3f190fabd6e61c1f226e19d468da58690dcfc9086466aa90ef78fca2abc3eb26')
PUBLISH_DECK = _operation('deck.toggle-publication', DeckIdInputDTO, DeckPublicationDTO, '80b452d28f596fe32e5b85c0bd945e4605aa84d138a8a5502334009aebc8a3f3')
COLLECT_DECK = _operation('deck.collect', DeckIdInputDTO, DeckCreatedDTO, '759d3339f70596e1bcf40b81e830baf4fc9409cdd3167bf9ecd5387ee7fc0565')
SYNC_DECK = _operation('deck.sync-parent', DeckIdInputDTO, DeckSyncedDTO, 'd9e8a56ccad9c0d82157ce064e913e06aa0489265a3a6a34257462a4756f96df')
DECK_MUTATION_OPERATIONS = (UPDATE_DECK, DELETE_DECK, PUBLISH_DECK, COLLECT_DECK, SYNC_DECK)


class AdminDeckMutationData:
    def __init__(self, client: AdminDataClient):
        self._client = client

    def _execute(self, operation, input_dto, request_id, access_token):
        require_deck_capabilities(self._client, request_id)
        return self._client.execute(operation, input_dto, request_id, access_token=access_token)

    def update(self, input_dto, request_id, *, access_token):
        return self._execute(UPDATE_DECK, input_dto, request_id, access_token)

    def delete(self, input_dto, request_id, *, access_token):
        return self._execute(DELETE_DECK, input_dto, request_id, access_token)

    def publish(self, input_dto, request_id, *, access_token):
        return self._execute(PUBLISH_DECK, input_dto, request_id, access_token)

    def collect(self, input_dto, request_id, *, access_token):
        return self._execute(COLLECT_DECK, input_dto, request_id, access_token)

    def sync(self, input_dto, request_id, *, access_token):
        return self._execute(SYNC_DECK, input_dto, request_id, access_token)

    def receipt(self, operation, request_id, *, access_token):
        if not any(operation is spec for spec in DECK_MUTATION_OPERATIONS):
            raise AdminDataError('ADMIN_OPERATION_CONTRACT_INVALID', 503, request_id)
        return self._client.receipt(operation, request_id, access_token=access_token)
