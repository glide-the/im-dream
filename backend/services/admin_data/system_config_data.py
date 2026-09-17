# [Input] Published User/Thread SystemConfig DTOs, exact schema capabilities and explicit OAuth or persistence grant.
# [Output] Closed typed get/patch commands, raw Python JSON decoding and original PATCH receipt recovery.
# [Pos] Sole SystemConfig data consumer; it owns no database, model catalog, filesystem or Runtime policy.
# [Sync] 2026-09-15: consume registered80 SystemConfig contracts without numeric re-encoding or database fallback.
"""Typed Admin SystemConfig operations and fail-closed raw JSON projection."""

from __future__ import annotations

import json
import math
import re
from typing import Any, Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from .chat_models import PresentFieldsDTO, ThreadIdInputDTO
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import OperationCapabilityDTO, StrictDTO
from .workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS, require_workflow_capabilities


_MODEL_ALIAS_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$")
_DOMAIN_PATTERN = re.compile(
    r"^(?:\*\.)?(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"
)
_SECRET_ENV_KEY_PATTERN = re.compile(
    r"(?:^|_)(?:API_KEY|AUTH_TOKEN|ACCESS_TOKEN|REFRESH_TOKEN|TOKEN|SECRET|"
    r"PASSWORD|PASSPHRASE|PRIVATE_KEY|CREDENTIAL|AUTHORIZATION)(?:$|_)",
    re.IGNORECASE,
)
_SERVER_CONTROLLED_ENV_KEYS = frozenset({
    "ANTHROPIC_BASE_URL", "ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL", "OPENAI_BASE_URL",
    "INK_ADMIN_PRODUCT_API_BASE_URL", "INK_ADMIN_PRODUCT_ORIGIN", "INK_GATEWAY_BASE_URL",
    "INK_GATEWAY_SERVICE_CLIENT_ID", "INK_AGENT_SANDBOX_ENABLED", "CLAUDE_CODE_EFFORT_LEVEL",
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW", "CLAUDE_CODE_MAX_CONTEXT_TOKENS",
    "INK_CLAUDE_CODE_MODEL_MAX_OUTPUT_TOKENS", "CLAUDE_CODE_MAX_OUTPUT_TOKENS", "CLAUDE_CODE_TMPDIR",
    "INK_AGENT_USER_ID", "INK_AGENT_THREAD_ID", "INK_AGENT_WORKFLOW_RUN_ID", "INK_STORY_WORKSPACE_MESSAGE_ID",
})


def _reject_json_constant(_value: str):
    raise ValueError("Non-finite JSON number")


def _require_finite_json(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Non-finite JSON number")
    if isinstance(value, list):
        for item in value:
            _require_finite_json(item)
    elif isinstance(value, dict):
        for item in value.values():
            _require_finite_json(item)


def decode_system_config(raw: str, request_id: str | None = None) -> dict[str, Any]:
    """Decode Admin's raw Python JSON without narrowing integers or float categories."""

    try:
        value = json.loads(raw, parse_constant=_reject_json_constant)
        if not isinstance(value, dict):
            raise ValueError("SystemConfig must be an object")
        _require_finite_json(value)
    except (TypeError, ValueError, RecursionError):
        raise invalid_response(request_id) from None
    return value


class SystemConfigGetInputDTO(StrictDTO):
    pass


class SystemConfigReadOutputDTO(StrictDTO):
    config_json: str = Field(min_length=1)

    def configuration(self, request_id: str) -> dict[str, Any]:
        return decode_system_config(self.config_json, request_id)


class SystemConfigPatchInputDTO(PresentFieldsDTO):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, hide_input_in_errors=True, allow_inf_nan=False)

    model: str | None = None
    provider: Literal["gateway"] | None = None
    system_prompt: str | None = None
    workspace_enabled: bool | None = None
    sandbox_network_mode: Literal["disabled", "allowlist", "open"] | None = None
    sandbox_network_allowed_domains: list[str] | None = None
    sandbox_fs_allowed_write_paths: list[str] | None = None
    im_full_access_enabled: bool | None = None
    theme: Literal["light", "dark", "system"] | None = None
    env_vars: dict[str, str] | None = None

    @model_validator(mode="after")
    def validate_present_fields(self):
        for name in self.model_fields_set:
            if getattr(self, name) is None:
                raise ValueError("SystemConfig patch fields cannot be null")
        if ("model" in self.model_fields_set) != ("provider" in self.model_fields_set):
            raise ValueError("Model and provider must be supplied together")
        return self

    @field_validator("model")
    @classmethod
    def validate_model(cls, value):
        if value is not None and _MODEL_ALIAS_PATTERN.fullmatch(value) is None:
            raise ValueError("Invalid model alias")
        return value

    @field_validator("system_prompt")
    @classmethod
    def validate_prompt(cls, value):
        if value is not None and len(value) > 16_384:
            raise ValueError("System prompt is too long")
        return value

    @field_validator("sandbox_network_allowed_domains")
    @classmethod
    def validate_domains(cls, value):
        if value is None:
            return value
        if len(value) > 64 or len(set(value)) != len(value):
            raise ValueError("Invalid sandbox domain list")
        if any(len(item) > 253 or _DOMAIN_PATTERN.fullmatch(item) is None for item in value):
            raise ValueError("Invalid sandbox domain")
        return value

    @field_validator("sandbox_fs_allowed_write_paths")
    @classmethod
    def validate_paths(cls, value):
        if value is None:
            return value
        if len(value) > 32 or len(set(value)) != len(value):
            raise ValueError("Invalid sandbox path list")
        if any(len(item) > 512 or not item.startswith("/") or (item != "/" and item.endswith("/")) for item in value):
            raise ValueError("Invalid sandbox path")
        return value

    @field_validator("env_vars")
    @classmethod
    def validate_env_vars(cls, value):
        if value is None:
            return value
        if len(value) > 64:
            raise ValueError("Too many environment variables")
        for key, item in value.items():
            if (
                not key or key.strip() != key or len(key) > 256
                or key.upper() in _SERVER_CONTROLLED_ENV_KEYS
                or _SECRET_ENV_KEY_PATTERN.search(key)
                or item.strip() != item or len(item) > 4096
            ):
                raise ValueError("Invalid environment variable")
        return value


class SystemConfigPatchedDTO(StrictDTO):
    success: Literal[True]

    @field_validator("success", mode="before")
    @classmethod
    def require_true_bool(cls, value):
        if value is not True:
            raise ValueError("SystemConfig patch was not confirmed")
        return value


GET_USER_SYSTEM_CONFIG = DomainOperation(
    OperationCapabilityDTO(name="user-system-config.get", kind="read", user_scope="dream:read", background_scope=None,
        input_schema_version=1, output_schema_version=1,
        contract_sha256="6e9b75cccbc6e843a9c25a0cbec041fef4c6dff3919af8449eff03c23e779dd5"),
    SystemConfigGetInputDTO, SystemConfigReadOutputDTO,
)
PATCH_USER_SYSTEM_CONFIG = DomainOperation(
    OperationCapabilityDTO(name="user-system-config.patch", kind="write", user_scope="dream:write", background_scope=None,
        input_schema_version=1, output_schema_version=1,
        contract_sha256="4f596ea05fe6adc5d881f5484b41ce40ae3a08358a7332f1b3b964112bd38b72"),
    SystemConfigPatchInputDTO, SystemConfigPatchedDTO,
)
GET_THREAD_SYSTEM_CONFIG = DomainOperation(
    OperationCapabilityDTO(name="thread-system-config.get", kind="read", user_scope="dream:read", background_scope=None,
        input_schema_version=1, output_schema_version=1,
        contract_sha256="50ca46f131005c0e9831797fc9f2590984da8c8878fec92db61656ec9eefec8b"),
    ThreadIdInputDTO, SystemConfigReadOutputDTO,
)
SYSTEM_CONFIG_OPERATIONS = (GET_USER_SYSTEM_CONFIG, PATCH_USER_SYSTEM_CONFIG, GET_THREAD_SYSTEM_CONFIG)


class AdminSystemConfigData:
    def __init__(self, client: AdminDataClient):
        self._client = client

    def _execute(self, operation, input_dto, request_id: str, access_token: str):
        require_workflow_capabilities(self._client, request_id)
        return self._client.execute(operation, input_dto, request_id, access_token=access_token)

    def get_user(self, input_dto: SystemConfigGetInputDTO, request_id: str, *, access_token: str) -> dict[str, Any]:
        result = self._execute(GET_USER_SYSTEM_CONFIG, input_dto, request_id, access_token)
        return result.configuration(request_id)

    def patch_user(self, input_dto: SystemConfigPatchInputDTO, request_id: str, *, access_token: str) -> SystemConfigPatchedDTO:
        return self._execute(PATCH_USER_SYSTEM_CONFIG, input_dto, request_id, access_token)

    def patch_receipt(self, request_id: str, *, access_token: str):
        require_workflow_capabilities(self._client, request_id)
        return self._client.receipt(PATCH_USER_SYSTEM_CONFIG, request_id, access_token=access_token)

    def get_thread(self, input_dto: ThreadIdInputDTO, request_id: str, *, access_token: str) -> dict[str, Any]:
        result = self._execute(GET_THREAD_SYSTEM_CONFIG, input_dto, request_id, access_token)
        return result.configuration(request_id)
