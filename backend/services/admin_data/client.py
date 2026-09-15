# [Input] AdminDataConfig and exact Admin Pydantic DTO/registered domain contracts.
# [Output] No-retry HTTP consumer with separate service/user authentication and receipt recovery.
# [Pos] Sole Admin authentication/data transport; domain adapters register explicit DTO operations.
# [Sync] 2026-09-14: implement v1 contracts and shared bounded HTTP parsing and closed Deck conflict revisions without SQL/UOW emulation.
# [Sync] 2026-09-15: expose catalog readiness so failed domain refreshes can recover through request authentication.
# [Sync] 2026-09-15: synchronize catalog refresh/readiness/operation checks while keeping domain HTTP concurrent.
# [Sync] 2026-09-15: read the dedicated original Preflight receipt without changing generic two-state receipts.
# [Sync] 2026-09-15: read task-scoped background Reflections receipts with the original task and request IDs.
# [Sync] 2026-09-16: expose a lock-safe local contract/capability readiness check for managed MCP composition.
"""Admin DTO client. HTTP failures never imply rollback of a dispatched write."""

from __future__ import annotations

from dataclasses import dataclass
import re
from threading import RLock
from typing import Generic, Literal, TypeVar

import httpx
from pydantic import BaseModel, TypeAdapter, create_model

from .config import ADMIN_INTERNAL_PREFIX, AdminDataConfig
from .errors import AdminDataError, invalid_response
from .http_transport import request_admin_dto
from .models import (
    AbsentReceiptDTO, BrowserExchangeDTO, BrowserHandleDTO, BrowserHandleRequestDTO,
    BrowserResolutionDTO, BrowserRevokedDTO, CapabilitiesDTO, CommittedReceiptDTO,
    Identifier, OperationCapabilityDTO, PrincipalDTO, SchemaCapabilityDTO,
    RequestDTO, StrictDTO,
)

InputT = TypeVar("InputT", bound=StrictDTO)
OutputT = TypeVar("OutputT", bound=BaseModel)


@dataclass(frozen=True)
class DomainOperation(Generic[InputT, OutputT]):
    """Composition-owned exact DTO contract, never supplied by a browser request."""

    capability: OperationCapabilityDTO
    input_dto: type[InputT]
    output_dto: type[OutputT]


class AdminDataClient:
    def __init__(self, config: AdminDataConfig, *, client: httpx.Client | None = None, operations: tuple[DomainOperation, ...] = ()) -> None:
        self._config = config
        self._owns_client = client is None
        self._http = client or httpx.Client(timeout=config.timeout_seconds, follow_redirects=False, trust_env=False)
        self._operations = {operation.capability.name: operation for operation in operations}
        if len(self._operations) != len(operations) or any(
            re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name) is None
            for name in self._operations
        ):
            raise AdminDataError("ADMIN_OPERATION_CONTRACT_INVALID", 503)
        self._advertised: dict[str, OperationCapabilityDTO] = {}
        self._schema_capabilities: dict[str, SchemaCapabilityDTO] = {}
        self._schema_capabilities_unique = False
        self._capabilities_ready = False
        self._catalog_lock = RLock()

    @property
    def capabilities_ready(self) -> bool:
        with self._catalog_lock:
            return self._capabilities_ready

    def close(self) -> None:
        if self._owns_client:
            self._http.close()

    def _request(self, method: Literal["GET", "POST"], path: str, request_id: str, output_type, *, input_dto: BaseModel | None = None, access_token: str | None = None, params: dict[str, str] | None = None, write: bool = False):
        # Validate before sending; never concatenate unvalidated IDs into paths/headers.
        RequestDTO(request_id=request_id)
        if access_token is not None and (not access_token or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in access_token)):
            raise AdminDataError("INVALID_ACCESS_TOKEN", 401, request_id)
        headers = {
            "accept": "application/json", "x-request-id": request_id,
            "X-Ink-Dream-Service": self._config.service_client_id,
            "X-Ink-Dream-Credential": self._config.service_secret,
        }
        if access_token is not None:
            headers["authorization"] = "Bearer " + access_token
        return request_admin_dto(self._http, method=method,
            url=self._config.base_url + ADMIN_INTERNAL_PREFIX + path,
            request_id=request_id, output_type=output_type, headers=headers,
            timeout_seconds=self._config.timeout_seconds,
            max_response_bytes=self._config.max_response_bytes,
            input_dto=input_dto, params=params, write=write)

    def capabilities(self, request_id: str) -> CapabilitiesDTO:
        with self._catalog_lock:
            self._advertised = {}
            self._schema_capabilities = {}
            self._schema_capabilities_unique = False
            self._capabilities_ready = False
            result = self._request("GET", "/capabilities", request_id, CapabilitiesDTO)
            auth = result.auth
            if auth.issuer != self._config.issuer or auth.jwks_uri != self._config.jwks_uri or auth.resource != self._config.resource:
                raise invalid_response(request_id)
            advertised = {item.name: item for item in result.operations}
            schemas = {
                item.capability: item for item in result.schema_capabilities
            }
            if len(advertised) != len(result.operations):
                raise invalid_response(request_id)
            self._advertised = advertised
            self._schema_capabilities = schemas
            self._schema_capabilities_unique = (
                len(schemas) == len(result.schema_capabilities)
            )
            self._capabilities_ready = True
            return result

    def supports(
        self,
        operations: tuple[DomainOperation, ...],
        schema_requirements: tuple[SchemaCapabilityDTO, ...] = (),
    ) -> bool:
        """Check the last authenticated catalog without issuing another request."""

        with self._catalog_lock:
            return (
                self._capabilities_ready
                and self._schema_capabilities_unique
                and all(
                    self._operations.get(operation.capability.name) is operation
                    and self._advertised.get(operation.capability.name)
                    == operation.capability
                    for operation in operations
                )
                and all(
                    self._schema_capabilities.get(requirement.capability)
                    == requirement
                    for requirement in schema_requirements
                )
            )

    def principal(self, access_token: str, request_id: str) -> PrincipalDTO:
        return self._request("GET", "/principal", request_id, PrincipalDTO, access_token=access_token)

    def _create_runtime_delegation(self, request, *, access_token: str):
        # Special Admin ingress has its own strict DTO and published-schema gate.
        from .delegation import DelegationCreatedDTO, DelegationCreateRequestDTO
        if type(request) is not DelegationCreateRequestDTO:
            raise AdminDataError("ADMIN_OPERATION_INPUT_INVALID", 400)
        return self._request("POST", "/runtime-delegations", request.request_id,
            DelegationCreatedDTO, input_dto=request, access_token=access_token, write=True)

    def exchange_browser_session(self, request: BrowserExchangeDTO) -> BrowserHandleDTO:
        return self._request("POST", "/browser-sessions/exchange", request.request_id, BrowserHandleDTO, input_dto=request, write=True)

    def resolve_browser_session(self, request: BrowserHandleRequestDTO) -> BrowserResolutionDTO:
        # Resolve can rotate refresh tokens; a timeout requires same-handle recovery.
        return self._request("POST", "/browser-sessions/resolve", request.request_id, BrowserResolutionDTO, input_dto=request, write=True)

    def revoke_browser_session(self, request: BrowserHandleRequestDTO) -> BrowserRevokedDTO:
        return self._request("POST", "/browser-sessions/revoke", request.request_id, BrowserRevokedDTO, input_dto=request, write=True)

    def execute(self, operation: DomainOperation[InputT, OutputT], input_dto: InputT, request_id: str, *, access_token: str | None = None) -> OutputT:
        with self._catalog_lock:
            name = operation.capability.name
            if self._operations.get(name) is not operation or self._advertised.get(name) != operation.capability:
                raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)
            if type(input_dto) is not operation.input_dto:
                raise AdminDataError("ADMIN_OPERATION_INPUT_INVALID", 400, request_id)
            if operation.capability.user_scope is not None and access_token is None:
                raise AdminDataError("INVALID_ACCESS_TOKEN", 401, request_id)
            OperationRequest = create_model("OperationRequest", __base__=RequestDTO, input=(operation.input_dto, ...))
            body = OperationRequest(request_id=request_id, input=input_dto)
        # Each domain HTTP uses its own immutable DTO/actor/UUID outside the
        # catalog boundary. Refresh locking must not serialize these requests.
        return self._request("POST", "/operations/" + name, request_id, operation.output_dto, input_dto=body, access_token=access_token, write=operation.capability.kind == "write")

    def receipt(self, operation: DomainOperation[InputT, OutputT], request_id: str, *, access_token: str | None = None) -> CommittedReceiptDTO[OutputT] | AbsentReceiptDTO:
        name = operation.capability.name
        if self._operations.get(name) is not operation:
            raise AdminDataError("ADMIN_OPERATION_CONTRACT_INVALID", 503, request_id)
        if operation.capability.user_scope is not None and access_token is None:
            raise AdminDataError("INVALID_ACCESS_TOKEN", 401, request_id)
        TypeAdapter(Identifier).validate_python(request_id)
        output = CommittedReceiptDTO[operation.output_dto] | AbsentReceiptDTO
        result = self._request("GET", "/receipts/" + request_id, request_id, output, params={"operation": name}, access_token=access_token)
        if result.operation != name or result.request_id != request_id:
            raise invalid_response(request_id)
        # An absent receipt remains an explicit absent DTO; it never triggers a retry.
        return result

    def reflection_task_receipt(
        self,
        operation: DomainOperation[InputT, OutputT],
        request_id: str,
        *,
        task_id: str,
    ) -> CommittedReceiptDTO[OutputT] | AbsentReceiptDTO:
        """Read one original background write result under its task receipt actor."""

        from .reflection_task_models import ReflectionTaskId

        name = operation.capability.name
        if (
            self._operations.get(name) is not operation
            or operation.capability.kind != "write"
            or operation.capability.user_scope is not None
            or operation.capability.background_scope != "reflections:execute"
        ):
            raise AdminDataError(
                "ADMIN_OPERATION_CONTRACT_INVALID", 503, request_id
            )
        TypeAdapter(Identifier).validate_python(request_id)
        TypeAdapter(ReflectionTaskId).validate_python(task_id, strict=True)
        output = CommittedReceiptDTO[operation.output_dto] | AbsentReceiptDTO
        result = self._request(
            "GET",
            "/receipts/" + request_id,
            request_id,
            output,
            params={"operation": name, "task_id": task_id},
        )
        if result.operation != name or result.request_id != request_id:
            raise invalid_response(request_id)
        return result

    def preflight_original_receipt(self, request_id: str, *, access_token: str):
        # The domain composition checks its three exact schema requirements.
        # This explicit reader keeps every generic receipt on its original DTO.
        from .preflight_data import EXECUTE_PREFLIGHT, PreflightOriginalReceiptDTO
        operation = EXECUTE_PREFLIGHT
        name = operation.capability.name
        with self._catalog_lock:
            if self._operations.get(name) is not operation or self._advertised.get(name) != operation.capability:
                raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)
        if not access_token:
            raise AdminDataError("INVALID_ACCESS_TOKEN", 401, request_id)
        TypeAdapter(Identifier).validate_python(request_id)
        result = self._request("GET", "/receipts/" + request_id, request_id, PreflightOriginalReceiptDTO,
            params={"operation": name}, access_token=access_token)
        if result.operation != name or result.request_id != request_id:
            raise invalid_response(request_id)
        return result
