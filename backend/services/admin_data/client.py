# [Input] AdminDataConfig and exact Admin Pydantic DTO/registered domain contracts.
# [Output] No-retry HTTP consumer with separate service/user authentication and receipt recovery.
# [Pos] Sole Admin authentication/data transport; domain adapters register explicit DTO operations.
# [Sync] 2026-09-14: implement v1 principal/capability/handle/receipt contracts without SQL/UOW emulation.
"""Admin DTO client. HTTP failures never imply rollback of a dispatched write."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Generic, Literal, TypeVar

import httpx
from pydantic import BaseModel, TypeAdapter, ValidationError, create_model

from .config import ADMIN_INTERNAL_PREFIX, AdminDataConfig
from .errors import AdminDataError, invalid_response, unavailable
from .models import (
    AbsentReceiptDTO, BrowserExchangeDTO, BrowserHandleDTO, BrowserHandleRequestDTO,
    BrowserResolutionDTO, BrowserRevokedDTO, CapabilitiesDTO, CommittedReceiptDTO,
    ErrorEnvelopeDTO, Identifier, OperationCapabilityDTO, PrincipalDTO,
    RequestDTO, ResponseEnvelopeDTO, StrictDTO,
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
        adapter = TypeAdapter(ResponseEnvelopeDTO[output_type])
        try:
            with self._http.stream(method, self._config.base_url + ADMIN_INTERNAL_PREFIX + path,
                headers=headers, params=params, json=input_dto.model_dump(mode="json") if input_dto is not None else None,
                timeout=self._config.timeout_seconds, follow_redirects=False) as response:
                status = response.status_code
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > self._config.max_response_bytes:
                        raise invalid_response(request_id, write=write)
        except httpx.TimeoutException:
            raise AdminDataError("ADMIN_TIMEOUT", 504, request_id, write) from None
        except httpx.HTTPError:
            raise unavailable(request_id, write=write) from None
        if not 200 <= status < 300:
            if status not in {400, 401, 403, 404, 409, 422, 429, 503, 504}:
                raise unavailable(request_id, write=write)
            try:
                error = ErrorEnvelopeDTO.model_validate_json(raw)
                if error.request_id != request_id:
                    raise invalid_response(request_id, write=write)
            except ValidationError:
                raise invalid_response(request_id, write=write) from None
            # Never retain/render the upstream message, which can contain SQL/secrets.
            raise AdminDataError(error.error.code, status, request_id, write and status >= 500)
        try:
            result = adapter.validate_json(raw)
        except ValidationError:
            raise invalid_response(request_id, write=write) from None
        if result.request_id != request_id:
            raise invalid_response(request_id, write=write)
        return result.data

    def capabilities(self, request_id: str) -> CapabilitiesDTO:
        self._advertised = {}
        result = self._request("GET", "/capabilities", request_id, CapabilitiesDTO)
        auth = result.auth
        if auth.issuer != self._config.issuer or auth.jwks_uri != self._config.jwks_uri or auth.resource != self._config.resource:
            self._advertised = {}
            raise invalid_response(request_id)
        advertised = {item.name: item for item in result.operations}
        if len(advertised) != len(result.operations):
            self._advertised = {}
            raise invalid_response(request_id)
        self._advertised = advertised
        return result

    def principal(self, access_token: str, request_id: str) -> PrincipalDTO:
        return self._request("GET", "/principal", request_id, PrincipalDTO, access_token=access_token)

    def exchange_browser_session(self, request: BrowserExchangeDTO) -> BrowserHandleDTO:
        return self._request("POST", "/browser-sessions/exchange", request.request_id, BrowserHandleDTO, input_dto=request, write=True)

    def resolve_browser_session(self, request: BrowserHandleRequestDTO) -> BrowserResolutionDTO:
        # Resolve can rotate refresh tokens; a timeout requires same-handle recovery.
        return self._request("POST", "/browser-sessions/resolve", request.request_id, BrowserResolutionDTO, input_dto=request, write=True)

    def revoke_browser_session(self, request: BrowserHandleRequestDTO) -> BrowserRevokedDTO:
        return self._request("POST", "/browser-sessions/revoke", request.request_id, BrowserRevokedDTO, input_dto=request, write=True)

    def execute(self, operation: DomainOperation[InputT, OutputT], input_dto: InputT, request_id: str, *, access_token: str | None = None) -> OutputT:
        name = operation.capability.name
        if self._operations.get(name) is not operation or self._advertised.get(name) != operation.capability:
            raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)
        if type(input_dto) is not operation.input_dto:
            raise AdminDataError("ADMIN_OPERATION_INPUT_INVALID", 400, request_id)
        if operation.capability.user_scope is not None and access_token is None:
            raise AdminDataError("INVALID_ACCESS_TOKEN", 401, request_id)
        OperationRequest = create_model("OperationRequest", __base__=RequestDTO, input=(operation.input_dto, ...))
        body = OperationRequest(request_id=request_id, input=input_dto)
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
