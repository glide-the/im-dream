"""Injectable, no-retry client for the five Admin Product API routes."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, Protocol, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from .config import AdminProductConfig
from .errors import (
    ProductBffError,
    dependency_unavailable,
    invalid_product_response,
)
from .models import (
    CommandResultEnvelope,
    ContextEnvelope,
    ExecuteSubscriptionCommand,
    ModelCatalogEnvelope,
    PlansEnvelope,
    PlansQuery,
    PreviewEnvelope,
    PreviewSubscriptionCommand,
    ProductErrorEnvelope,
    UsageEnvelope,
    UsageQuery,
)
from .token import ProductScope, issue_product_token


_MAX_RESPONSE_BYTES = 1_048_576
_PASSTHROUGH_ERROR_STATUSES = {400, 401, 402, 403, 404, 409, 429, 502, 503}
# Canonical Token-only Product API field-name firewall. Keep this tuple
# entry-for-entry aligned with app/lib/product/safety.ts in ink-admin-memory.
# Token-domain names such as ``tokenBalance`` are intentionally permitted.
_FORBIDDEN_RESPONSE_KEY_FRAGMENTS = (
    "price",
    "amount",
    "currency",
    "microusd",
    "cash",
    "monetary",
    "financial",
    "payment",
    "topup",
    "checkout",
    "refund",
    "reversal",
    "ledger",
    "effectivefrom",
    "effectiveto",
    "provider",
    "secret",
    "credential",
    "platformuserid",
    "authorization",
    "apikey",
    "keyhash",
    "ciphertext",
)
_PUBLIC_ERROR_MESSAGES = {
    400: "The Product API request is invalid.",
    401: "A valid Dream session is required.",
    402: "The current subscription-period Token allowance is insufficient.",
    403: "The requested subscription action or entitlement is not allowed.",
    404: "The requested subscription resource is not available.",
    409: "The subscription changed or conflicts with the requested action.",
    429: "The Product API rate limit was reached; retry later.",
    502: "The inference provider could not safely complete the request.",
    503: "The subscription service is temporarily unavailable.",
}
_PUBLIC_ERROR_DETAIL_FIELDS = {
    "expectedVersion",
    "actualVersion",
    "periodEnd",
    "status",
    "reasonCode",
    "metric",
    "unit",
    "availableTokens",
    "requiredTokens",
    "modelAlias",
    "gatewayScope",
    "requiredScope",
    "retryable",
    "window",
    "current",
    "limit",
    "remaining",
}


def _normalized_key(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def assert_safe_product_payload(
    value: Any,
    *,
    _seen: set[int] | None = None,
) -> None:
    """Reject forbidden product fields before any object is returned upstream."""

    if not isinstance(value, (dict, list)):
        return
    seen = _seen if _seen is not None else set()
    marker = id(value)
    if marker in seen:
        raise invalid_product_response()
    seen.add(marker)
    if isinstance(value, list):
        for item in value:
            assert_safe_product_payload(item, _seen=seen)
    else:
        for key, item in value.items():
            if not isinstance(key, str):
                raise invalid_product_response()
            normalized = _normalized_key(key)
            if any(fragment in normalized for fragment in _FORBIDDEN_RESPONSE_KEY_FRAGMENTS):
                raise invalid_product_response()
            assert_safe_product_payload(item, _seen=seen)
    seen.remove(marker)


class AdminProductGateway(Protocol):
    async def plans(
        self, canonical_user_id: str, query: PlansQuery, request_id: str
    ) -> dict[str, Any]: ...

    async def subscription_context(
        self, canonical_user_id: str, request_id: str
    ) -> dict[str, Any]: ...

    async def usage(
        self, canonical_user_id: str, query: UsageQuery, request_id: str
    ) -> dict[str, Any]: ...

    async def model_catalog(
        self, canonical_user_id: str, request_id: str
    ) -> dict[str, Any]: ...

    async def subscription_command(
        self,
        canonical_user_id: str,
        command: PreviewSubscriptionCommand | ExecuteSubscriptionCommand,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]: ...


ModelT = TypeVar("ModelT", bound=BaseModel)


class AdminProductClient:
    """Call exactly one Admin route per BFF request, without automatic retry."""

    def __init__(
        self,
        configuration: AdminProductConfig,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._configuration = configuration
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(configuration.timeout_seconds),
            follow_redirects=False,
            trust_env=False,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def _headers(
        self,
        canonical_user_id: str,
        scope: ProductScope,
        request_id: str,
        *,
        write: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, str]:
        headers = {
            "accept": "application/json",
            "authorization": "Bearer "
            + issue_product_token(
                self._configuration,
                canonical_user_id=canonical_user_id,
                scope=scope,
            ),
            "x-request-id": request_id,
        }
        if write:
            headers["content-type"] = "application/json"
            headers["origin"] = self._configuration.request_origin
        if idempotency_key is not None:
            headers["idempotency-key"] = idempotency_key
        return headers

    async def _request(
        self,
        *,
        method: Literal["GET", "POST"],
        path: str,
        canonical_user_id: str,
        scope: ProductScope,
        request_id: str,
        response_model: type[ModelT],
        query: Mapping[str, Any] | None = None,
        body: Mapping[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        try:
            response = await self._client.request(
                method,
                f"{self._configuration.base_url}{path}",
                params=query,
                json=body,
                follow_redirects=False,
                headers=self._headers(
                    canonical_user_id,
                    scope,
                    request_id,
                    write=method == "POST",
                    idempotency_key=idempotency_key,
                ),
            )
        except httpx.HTTPError:
            raise dependency_unavailable() from None

        declared_length = response.headers.get("content-length")
        if declared_length:
            if not declared_length.isdigit():
                raise invalid_product_response() from None
            if int(declared_length) > _MAX_RESPONSE_BYTES:
                raise invalid_product_response()
        if len(response.content) > _MAX_RESPONSE_BYTES:
            raise invalid_product_response()
        try:
            payload = response.json()
        except (ValueError, UnicodeError):
            raise invalid_product_response() from None
        assert_safe_product_payload(payload)

        if response.status_code != 200:
            self._raise_upstream_error(response.status_code, payload, request_id)
        try:
            parsed = response_model.model_validate(payload)
        except ValidationError:
            raise invalid_product_response() from None
        result = parsed.model_dump(mode="json")
        if result.get("meta", {}).get("requestId") != request_id:
            raise invalid_product_response()
        assert_safe_product_payload(result)
        return result

    @staticmethod
    def _raise_upstream_error(
        status_code: int, payload: Any, expected_request_id: str
    ) -> None:
        if status_code not in _PASSTHROUGH_ERROR_STATUSES:
            raise dependency_unavailable()
        try:
            parsed = ProductErrorEnvelope.model_validate(payload)
        except ValidationError:
            raise invalid_product_response() from None
        if parsed.meta.requestId != expected_request_id:
            raise invalid_product_response()
        raw_details = (
            parsed.error.details.model_dump(mode="json", exclude_none=True)
            if parsed.error.details is not None
            else {}
        )
        details = {
            key: value
            for key, value in raw_details.items()
            if key in _PUBLIC_ERROR_DETAIL_FIELDS
        } or None
        raise ProductBffError(
            code=parsed.error.code,
            message=_PUBLIC_ERROR_MESSAGES[status_code],
            status_code=status_code,
            details=details,
            retry_after_seconds=parsed.meta.retryAfterSeconds,
        )

    async def plans(
        self, canonical_user_id: str, query: PlansQuery, request_id: str
    ) -> dict[str, Any]:
        return await self._request(
            method="GET",
            path="/api/product/v1/plans",
            canonical_user_id=canonical_user_id,
            scope="product:read",
            request_id=request_id,
            response_model=PlansEnvelope,
            query=query.model_dump(mode="json", exclude_none=True),
        )

    async def subscription_context(
        self, canonical_user_id: str, request_id: str
    ) -> dict[str, Any]:
        return await self._request(
            method="GET",
            path="/api/product/v1/me/subscription-context",
            canonical_user_id=canonical_user_id,
            scope="product:read",
            request_id=request_id,
            response_model=ContextEnvelope,
        )

    async def usage(
        self, canonical_user_id: str, query: UsageQuery, request_id: str
    ) -> dict[str, Any]:
        return await self._request(
            method="GET",
            path="/api/product/v1/me/usage",
            canonical_user_id=canonical_user_id,
            scope="product:read",
            request_id=request_id,
            response_model=UsageEnvelope,
            query=query.model_dump(mode="json", exclude_none=True),
        )

    async def model_catalog(
        self, canonical_user_id: str, request_id: str
    ) -> dict[str, Any]:
        return await self._request(
            method="GET",
            path="/api/product/v1/me/model-catalog",
            canonical_user_id=canonical_user_id,
            scope="product:read",
            request_id=request_id,
            response_model=ModelCatalogEnvelope,
        )

    async def subscription_command(
        self,
        canonical_user_id: str,
        command: PreviewSubscriptionCommand | ExecuteSubscriptionCommand,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        execute = isinstance(command, ExecuteSubscriptionCommand)
        if execute != (idempotency_key is not None):
            raise ProductBffError(
                code=(
                    "PRODUCT_IDEMPOTENCY_KEY_REQUIRED"
                    if execute
                    else "PRODUCT_IDEMPOTENCY_KEY_NOT_ALLOWED"
                ),
                message=(
                    "Idempotency-Key is required for command execution."
                    if execute
                    else "Idempotency-Key is allowed only for command execution."
                ),
                status_code=400,
            )
        return await self._request(
            method="POST",
            path="/api/product/v1/me/subscription-commands",
            canonical_user_id=canonical_user_id,
            scope="product:write",
            request_id=request_id,
            response_model=CommandResultEnvelope if execute else PreviewEnvelope,
            body=command.model_dump(mode="json", exclude_none=True),
            idempotency_key=idempotency_key,
        )
