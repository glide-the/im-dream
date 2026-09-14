# [Input] Actual Admin userPreferences DTOs, raw Python config JSON and current request OAuth.
# [Output] Two exact capability-gated operations and the original public preference projection.
# [Pos] User preferences consumer; system/Runtime policy and first-login writes are separate domains.
# [Sync] 2026-09-15: migrate public get/save without JSON numeric re-encoding or Dream PG.
from __future__ import annotations

import json
from typing import Literal

from pydantic import JsonValue, field_validator

from .chat_models import ChatStrictDTO, validate_timestamp_text
from .client import AdminDataClient, DomainOperation
from .deck_version_models import SafeInteger
from .errors import AdminDataError, invalid_response
from .models import OperationCapabilityDTO
from .workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS


def config_object(raw: str | None) -> dict | None:
    if raw is None:
        return None
    try:
        value = json.loads(raw)
    except (ValueError, TypeError):
        raise ValueError("Invalid preference configuration") from None
    if not isinstance(value, dict):
        raise ValueError("Preference configuration must be an object")
    return value


class PreferencesGetInputDTO(ChatStrictDTO):
    pass


class PreferencesSaveInputDTO(ChatStrictDTO):
    voice_configs_json: str | None
    meta_prompt: str | None
    state_config_json: str | None
    selected_state: str | None
    timezone: str | None

    @field_validator("voice_configs_json", "state_config_json")
    @classmethod
    def validate_config(cls, value):
        config_object(value)
        return value


class PreferencesDTO(PreferencesSaveInputDTO):
    first_login_completed: SafeInteger | None
    updated_at: str | None
    _timestamp = field_validator("updated_at")(validate_timestamp_text)

    def public_projection(self) -> dict:
        result = self.model_dump(exclude={"voice_configs_json", "state_config_json"})
        result["voice_configs"] = config_object(self.voice_configs_json)
        result["state_config"] = config_object(self.state_config_json)
        # Legacy raw object text remains unchanged at the wire boundary. The
        # public JSON response cannot represent NaN/Infinity; fail safely.
        json.dumps(result, allow_nan=False)
        return result


class PreferencesGetOutputDTO(ChatStrictDTO):
    preferences: PreferencesDTO | None


class PreferencesSavedDTO(ChatStrictDTO):
    success: Literal[True]

    @field_validator("success", mode="before")
    @classmethod
    def require_true_bool(cls, value):
        if value is not True:
            raise ValueError("Preference save was not confirmed")
        return value


class PreferencesSaveRequestDTO(ChatStrictDTO):
    voice_configs: dict[str, JsonValue] | None = None
    meta_prompt: str | None = None
    state_config: dict[str, JsonValue] | None = None
    selected_state: str | None = None
    timezone: str | None = None

    def domain_input(self) -> PreferencesSaveInputDTO:
        return PreferencesSaveInputDTO(
            voice_configs_json=json.dumps(self.voice_configs, ensure_ascii=False, allow_nan=False) if self.voice_configs is not None else None,
            meta_prompt=self.meta_prompt,
            state_config_json=json.dumps(self.state_config, ensure_ascii=False, allow_nan=False) if self.state_config is not None else None,
            selected_state=self.selected_state, timezone=self.timezone,
        )


GET_PREFERENCES = DomainOperation(OperationCapabilityDTO(name="user-preferences.get", kind="read", user_scope="dream:read", background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256="757b12445ab664d26be82ade16e791d4331de348a4854403ff3c5a77f5b98d70"), PreferencesGetInputDTO, PreferencesGetOutputDTO)
SAVE_PREFERENCES = DomainOperation(OperationCapabilityDTO(name="user-preferences.save", kind="write", user_scope="dream:write", background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256="0e0dbd5bdd90404b44fe10fe65e1b67ebdea2a55496751e45140e5166c0bca56"), PreferencesSaveInputDTO, PreferencesSavedDTO)
PREFERENCES_OPERATIONS = (GET_PREFERENCES, SAVE_PREFERENCES)


class AdminPreferencesData:
    def __init__(self, client: AdminDataClient):
        self._client = client

    def _execute(self, operation, input_dto, request_id, access_token):
        capabilities = self._client.capabilities(request_id)
        schemas = {item.capability: item for item in capabilities.schema_capabilities}
        if len(schemas) != len(capabilities.schema_capabilities) or any(schemas.get(item.capability) != item for item in WORKFLOW_SCHEMA_REQUIREMENTS):
            raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)
        return self._client.execute(operation, input_dto, request_id, access_token=access_token)

    def get(self, input_dto: PreferencesGetInputDTO, request_id: str, *, access_token: str) -> dict:
        result = self._execute(GET_PREFERENCES, input_dto, request_id, access_token)
        try:
            return result.preferences.public_projection() if result.preferences is not None else {}
        except (ValueError, TypeError):
            raise invalid_response(request_id) from None

    def save(self, input_dto: PreferencesSaveInputDTO, request_id: str, *, access_token: str) -> PreferencesSavedDTO:
        return self._execute(SAVE_PREFERENCES, input_dto, request_id, access_token)
