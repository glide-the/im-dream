# [Sync] 2026-09-15: reuse the unchanged shared Deck four-schema readiness check.
# [Input] Actual four Admin Voice contracts, public request fields and current OAuth.
# [Output] Closed raw Memory JSON commands and original Voice mutation results.
# [Pos] Public Voice consumer; Admin owns default/order/row locks/draft revision/receipts.
# [Sync] 2026-09-15: consume create/update/delete/collect without Dream SQL or identity overrides.
from __future__ import annotations

import json

from pydantic import JsonValue, field_validator

from .chat_models import ChatStrictDTO, EntityId, PresentFieldsDTO
from .client import AdminDataClient, DomainOperation
from .deck_version_data import require_deck_capabilities
from .deck_version_models import SafeInteger
from .errors import AdminDataError
from .models import OperationCapabilityDTO
from .preferences_data import config_object


def validate_memory_input(raw: str | None) -> str | None:
    # Reuse the object parser; new commands require finite JSON while legacy
    # preference response strings retain their separate projection behavior.
    value = config_object(raw)
    if value is not None:
        json.dumps(value, allow_nan=False)
    return raw


class VoiceIdInputDTO(ChatStrictDTO):
    voice_id: EntityId


class VoiceCreateInputDTO(ChatStrictDTO):
    deck_id: EntityId
    name: str
    system_prompt: str
    name_zh: str | None
    name_en: str | None
    icon: str | None
    color: str | None
    memory_workspace_config_json: str | None
    order_index: SafeInteger | None
    _memory = field_validator('memory_workspace_config_json')(validate_memory_input)


class VoiceUpdateFieldsDTO(PresentFieldsDTO):
    name: str = None
    system_prompt: str = None
    name_zh: str | None = None
    name_en: str | None = None
    icon: str | None = None
    color: str | None = None
    enabled: bool = None
    order_index: SafeInteger | None = None
    thread_id: str | None = None
    memory_workspace_config_json: str | None = None
    _memory = field_validator('memory_workspace_config_json')(validate_memory_input)


class VoiceUpdateInputDTO(VoiceIdInputDTO):
    updates: VoiceUpdateFieldsDTO


class VoiceCollectInputDTO(VoiceIdInputDTO):
    target_deck_id: EntityId


class VoiceForkRequestDTO(ChatStrictDTO):
    target_deck_id: EntityId


class VoiceCreatedDTO(ChatStrictDTO):
    voice_id: EntityId


class VoiceChangedDTO(ChatStrictDTO):
    changed: bool


class VoiceCreateRequestDTO(ChatStrictDTO):
    deck_id: EntityId
    name: str
    system_prompt: str
    name_zh: str | None = None
    name_en: str | None = None
    icon: str | None = None
    color: str | None = None
    memory_workspace_config: dict[str, JsonValue] | None = None

    def domain_input(self):
        fields = self.model_dump(exclude={'memory_workspace_config'})
        return VoiceCreateInputDTO(**fields, order_index=None,
            memory_workspace_config_json=json.dumps(self.memory_workspace_config, ensure_ascii=False, allow_nan=False)
            if self.memory_workspace_config is not None else None)


class VoiceUpdateRequestDTO(ChatStrictDTO):
    name: str | None = None
    system_prompt: str | None = None
    name_zh: str | None = None
    name_en: str | None = None
    icon: str | None = None
    color: str | None = None
    enabled: bool | None = None
    order_index: SafeInteger | None = None
    thread_id: str | None = None
    memory_workspace_config: dict[str, JsonValue] | None = None

    def domain_input(self, voice_id: str):
        updates = self.model_dump(exclude_none=True, exclude={'memory_workspace_config'})
        if self.memory_workspace_config is not None:
            updates['memory_workspace_config_json'] = json.dumps(self.memory_workspace_config,
                ensure_ascii=False, sort_keys=True, allow_nan=False)
        return VoiceUpdateInputDTO(voice_id=voice_id, updates=VoiceUpdateFieldsDTO(**updates))


CREATE_VOICE = DomainOperation(OperationCapabilityDTO(name='voice.create', kind='write', user_scope='dream:write', background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256='ca8ff5b93598318becdb45cacbfa639f9e433dc953449c2c42120f8fabaafa87'), VoiceCreateInputDTO, VoiceCreatedDTO)
UPDATE_VOICE = DomainOperation(OperationCapabilityDTO(name='voice.update', kind='write', user_scope='dream:write', background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256='bd56b36c252bba82ef187dc4d4047eae8332c8f0537e5ac73dd7b5c70f41b7f6'), VoiceUpdateInputDTO, VoiceChangedDTO)
DELETE_VOICE = DomainOperation(OperationCapabilityDTO(name='voice.delete', kind='write', user_scope='dream:write', background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256='d5fd0f0fa962fe96206c2dd848260c9ca863c075e2997e907cf470c1ec531dda'), VoiceIdInputDTO, VoiceChangedDTO)
COLLECT_VOICE = DomainOperation(OperationCapabilityDTO(name='voice.collect', kind='write', user_scope='dream:write', background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256='1840c19c1c63532252469646b88116b8b93d24c8e6f27405844c251b96273020'), VoiceCollectInputDTO, VoiceCreatedDTO)
VOICE_OPERATIONS = (CREATE_VOICE, UPDATE_VOICE, DELETE_VOICE, COLLECT_VOICE)


class AdminVoiceData:
    def __init__(self, client: AdminDataClient):
        self._client = client

    def _execute(self, operation, input_dto, request_id, access_token):
        require_deck_capabilities(self._client, request_id)
        return self._client.execute(operation, input_dto, request_id, access_token=access_token)

    def create(self, input_dto, request_id, *, access_token):
        return self._execute(CREATE_VOICE, input_dto, request_id, access_token)

    def update(self, input_dto, request_id, *, access_token):
        return self._execute(UPDATE_VOICE, input_dto, request_id, access_token)

    def delete(self, input_dto, request_id, *, access_token):
        return self._execute(DELETE_VOICE, input_dto, request_id, access_token)

    def collect(self, input_dto, request_id, *, access_token):
        return self._execute(COLLECT_VOICE, input_dto, request_id, access_token)

    def receipt(self, operation, request_id, *, access_token):
        if not any(operation is spec for spec in VOICE_OPERATIONS):
            raise AdminDataError('ADMIN_OPERATION_CONTRACT_INVALID', 503, request_id)
        return self._client.receipt(operation, request_id, access_token=access_token)
