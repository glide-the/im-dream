# [Input] Actual Admin purpose DTOs, published identity capabilities and explicit actor credentials.
# [Output] Immutable entity grants and bearer-only public actions with original-ID receipt recovery.
# [Pos] Runtime authorization consumer; server creation and public runtime credentials stay separate.
# [Sync] 2026-09-15: require the published unified Workflow schema in creation/discovery readiness.
# [Sync] 2026-09-15: let purpose-grant creation require additional exact operation contracts.
# [Sync] 2026-09-14: consume four frozen special-route contracts without PG or generic-operation emulation.
"""A delegation authorizes one purpose, thread/run and optional exact Editor Session."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from typing import Annotated, Callable, Literal

import httpx
from pydantic import Field, TypeAdapter, field_validator, model_validator

from .chat_models import validate_timestamp_text
from .client import AdminDataClient
from .config import AdminDataConfig, _origin
from .errors import AdminDataError, configuration_invalid, invalid_response
from .http_transport import request_admin_dto
from .models import AbsentReceiptDTO, CommittedReceiptDTO, DelegationCapabilityDTO, OperationCapabilityDTO, RequestDTO, SchemaCapabilityDTO, StrictDTO

Purpose = Literal["server-persistence", "gateway-cli", "editor-stdio"]
RuntimeScope = Literal["dream:read", "dream:write", "messages:create", "messages:count_tokens", "models:list", "editor:read", "editor:write"]
DelegationToken = Annotated[str, Field(pattern=r"^idg_[A-Za-z0-9_-]{43}$")]
EntityReference = Annotated[str, Field(min_length=1)]
Action = Literal["runtime-delegation.renew", "runtime-delegation.revoke"]
PURPOSE_SCOPES = {
    "server-persistence": frozenset(("dream:read", "dream:write")),
    "gateway-cli": frozenset(("messages:create", "messages:count_tokens", "models:list")),
    "editor-stdio": frozenset(("editor:read", "editor:write")),
}
# Digests are generated from Admin's actual input and output JSON schemas.
DELEGATION_CONTRACT_HASHES = {
    "runtime-delegation.create": "61186cc930977683a9739b412de0b0837ac482230ba0cf8c493d57f20d918273",
    "runtime-delegation.renew": "1d611aeb0c70864d330042e2f3825191a0624f177b81a62ba83fae31587117db",
    "runtime-delegation.revoke": "0c4c315146fb80dff05db14eed0ac7b301db1d85827f6a651cc1e1d7b25152f9",
    "runtime-delegation.receipt": "19bfb6e3eaa0ee783d688035afc347b3f2ec4b6771161e0ba445ed9b890ffdfc",
}
DELEGATION_CAPABILITIES = tuple(DelegationCapabilityDTO(name=name, method=method, path=path,
    input_schema_version=1, output_schema_version=1, contract_sha256=DELEGATION_CONTRACT_HASHES[name])
    for name, method, path in (
        ("runtime-delegation.create", "POST", "/api/internal/dream/v1/runtime-delegations"),
        ("runtime-delegation.renew", "POST", "/api/runtime-delegations/renew"),
        ("runtime-delegation.revoke", "POST", "/api/runtime-delegations/revoke"),
        ("runtime-delegation.receipt", "GET", "/api/runtime-delegations/receipts/{request_id}")))
RUNTIME_SCHEMA_REQUIREMENTS = (
    SchemaCapabilityDTO(capability="identity.better-auth.v1", version=1, contract_sha256="1dc05e229d3f4147923fcdfe117c4c4930a43bf9f31439d7b4bc83d2a0d04cd3"),
    SchemaCapabilityDTO(capability="identity.runtime-delegation.v1", version=1, contract_sha256="1a682e29c2fcfa6d870a64c131773f0fa2ce49866fc56b30f334e07040e79a83"),
    SchemaCapabilityDTO(capability="identity.runtime-purpose.v1", version=1, contract_sha256="20f6c9bf727ac1ecc874c96880de12764a9406b5948c4764f0cfc0a107030447"),
    SchemaCapabilityDTO(capability="dream.schema.unified.v1", version=1, contract_sha256="8b71cf5687f61dee884c3e6f2fb109c7a951b0789066a0f13583a7b67757fa71"),
)


class DelegationCreateInputDTO(StrictDTO):
    purpose: Purpose
    thread_id: EntityReference
    run_id: EntityReference | None
    editor_session_id: EntityReference | None
    scopes: list[RuntimeScope] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_purpose(self):
        if (len(set(self.scopes)) != len(self.scopes)
            or not set(self.scopes) <= PURPOSE_SCOPES[self.purpose]
            or ((self.purpose == "editor-stdio") != (self.editor_session_id is not None))):
            raise ValueError("Invalid delegation purpose or scope binding")
        return self


class DelegationCreateRequestDTO(RequestDTO):
    input: DelegationCreateInputDTO


class DelegationRenewDTO(StrictDTO):
    expires_at: str
    maximum_expires_at: str
    purpose: Purpose
    thread_id: str
    run_id: str | None
    editor_session_id: str | None
    scopes: list[RuntimeScope]
    _timestamps = field_validator("expires_at", "maximum_expires_at")(validate_timestamp_text)


class DelegationCreatedDTO(DelegationRenewDTO):
    token: DelegationToken = Field(repr=False)


class DelegationRevokedDTO(StrictDTO):
    revoked: Literal[True]


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass(frozen=True)
class RuntimeGrant:
    token: str = field(repr=False)
    purpose: Purpose
    thread_id: str
    run_id: str | None
    editor_session_id: str | None
    scopes: tuple[str, ...]
    expires_at: datetime
    maximum_expires_at: datetime

    def __post_init__(self):
        TypeAdapter(DelegationToken).validate_python(self.token)
        DelegationCreateInputDTO(purpose=self.purpose, thread_id=self.thread_id,
            run_id=self.run_id, editor_session_id=self.editor_session_id, scopes=list(self.scopes))
        if (not isinstance(self.scopes, tuple)
            or self.expires_at.tzinfo is None or self.maximum_expires_at.tzinfo is None
            or self.expires_at > self.maximum_expires_at):
            raise configuration_invalid()

    @classmethod
    def from_created(cls, result: DelegationCreatedDTO, requested: DelegationCreateInputDTO,
        request_id: str, *, now: datetime) -> RuntimeGrant:
        if any(getattr(result, name) != getattr(requested, name)
            for name in ("purpose", "thread_id", "run_id", "editor_session_id", "scopes")):
            raise invalid_response(request_id, write=True)
        expires, maximum = _time(result.expires_at), _time(result.maximum_expires_at)
        if not now < expires <= maximum:
            raise invalid_response(request_id, write=True)
        return cls(result.token, result.purpose, result.thread_id, result.run_id,
            result.editor_session_id, tuple(result.scopes), expires, maximum)

    def with_renewal(self, result: DelegationRenewDTO, request_id: str) -> RuntimeGrant:
        if (any(getattr(result, name) != getattr(self, name)
                for name in ("purpose", "thread_id", "run_id", "editor_session_id"))
            or tuple(result.scopes) != self.scopes
            or _time(result.maximum_expires_at) != self.maximum_expires_at
            or not self.expires_at <= _time(result.expires_at) <= self.maximum_expires_at):
            raise invalid_response(request_id, write=True)
        return RuntimeGrant(self.token, self.purpose, self.thread_id, self.run_id,
            self.editor_session_id, self.scopes, _time(result.expires_at), self.maximum_expires_at)


@dataclass(frozen=True)
class RuntimeHttpConfig:
    base_url: str
    timeout_seconds: float = 10.0
    max_response_bytes: int = 1_048_576

    def __post_init__(self):
        if (_origin(self.base_url) != self.base_url
            or not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0
            or type(self.max_response_bytes) is not int or self.max_response_bytes < 1):
            raise configuration_invalid()

    @classmethod
    def from_server_config(cls, config: AdminDataConfig) -> RuntimeHttpConfig:
        return cls(config.base_url, config.timeout_seconds, config.max_response_bytes)


class AdminDelegationCreator:
    def __init__(self, client: AdminDataClient, *, clock: Callable[[], datetime] | None = None):
        self._client = client
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def create(self, requested: DelegationCreateInputDTO, *, access_token: str, request_id: str,
        required_operations: tuple[OperationCapabilityDTO, ...] = ()) -> RuntimeGrant:
        capabilities = self._client.capabilities(request_id)
        advertised = {item.capability: item for item in capabilities.schema_capabilities}
        delegation_capabilities = {item.name: item for item in capabilities.auth.delegations}
        operation_capabilities = {item.name: item for item in capabilities.operations}
        if (len(advertised) != len(capabilities.schema_capabilities)
            or any(advertised.get(item.capability) != item for item in RUNTIME_SCHEMA_REQUIREMENTS)
            or len(delegation_capabilities) != len(capabilities.auth.delegations)
            or any(delegation_capabilities.get(item.name) != item for item in DELEGATION_CAPABILITIES)
            or len(operation_capabilities) != len(capabilities.operations)
            or any(operation_capabilities.get(item.name) != item for item in required_operations)):
            raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)
        result = self._client._create_runtime_delegation(
            DelegationCreateRequestDTO(request_id=request_id, input=requested), access_token=access_token)
        return RuntimeGrant.from_created(result, requested, request_id, now=self._clock())


class AdminRuntimeClient:
    """Public runtime protocol; constructor and requests never receive service secrets."""
    def __init__(self, config: RuntimeHttpConfig, *, client: httpx.Client | None = None):
        self._config = config
        self._owns_client = client is None
        self._http = client or httpx.Client(timeout=config.timeout_seconds, follow_redirects=False, trust_env=False)

    def close(self):
        if self._owns_client:
            self._http.close()

    def _request(self, method, path: str, token: str, request_id: str, output_type,
        *, body: RequestDTO | None = None, params: dict[str, str] | None = None, write: bool = False):
        TypeAdapter(DelegationToken).validate_python(token)
        return request_admin_dto(self._http, method=method,
            url=self._config.base_url + path, request_id=request_id, output_type=output_type,
            headers={"accept": "application/json", "x-request-id": request_id, "authorization": "Bearer " + token},
            timeout_seconds=self._config.timeout_seconds, max_response_bytes=self._config.max_response_bytes,
            input_dto=body, params=params, write=write)

    def renew(self, grant: RuntimeGrant, request_id: str) -> RuntimeGrant:
        result = self._request("POST", "/api/runtime-delegations/renew", grant.token,
            request_id, DelegationRenewDTO, body=RequestDTO(request_id=request_id), write=True)
        return grant.with_renewal(result, request_id)

    def revoke(self, grant: RuntimeGrant, request_id: str) -> DelegationRevokedDTO:
        return self._request("POST", "/api/runtime-delegations/revoke", grant.token,
            request_id, DelegationRevokedDTO, body=RequestDTO(request_id=request_id), write=True)

    def receipt(self, grant: RuntimeGrant, operation: Action, request_id: str):
        if operation not in ("runtime-delegation.renew", "runtime-delegation.revoke"):
            raise AdminDataError("ADMIN_OPERATION_CONTRACT_INVALID", 503, request_id)
        RequestDTO(request_id=request_id)
        output = DelegationRenewDTO if operation == "runtime-delegation.renew" else DelegationRevokedDTO
        result = self._request("GET", "/api/runtime-delegations/receipts/" + request_id,
            grant.token, request_id, CommittedReceiptDTO[output] | AbsentReceiptDTO,
            params={"operation": operation})
        if result.operation != operation or result.request_id != request_id:
            raise invalid_response(request_id)
        if isinstance(result, CommittedReceiptDTO) and operation == "runtime-delegation.renew":
            grant.with_renewal(result.result, request_id)
        return result
