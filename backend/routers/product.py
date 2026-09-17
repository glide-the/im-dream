"""Same-origin Dream BFF routes for subscription, payment and usage.

[Input] Admin OAuth bearer identity, strict Product DTOs and server-owned Product configuration.
[Output] Product-scope actor DTO calls with stable Dream Product error envelopes.
[Pos] Dream Product orchestration boundary; it never reads Product identity or business data from PostgreSQL.
[Sync] 2026-09-16: require Product OAuth scopes and remove Dream Product token signing.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from typing import Any, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, ValidationError

from starlette.concurrency import run_in_threadpool

from .deps import get_admin_request_auth, http_bearer
from services.admin_data.errors import AdminDataError
from services.admin_data.request_auth import AdminRequestActor
from services.admin_product.client import assert_safe_product_payload
from services.admin_product.config import parse_origin_allowlist
from services.admin_product.errors import (
    ProductBffError,
    dependency_unavailable,
    invalid_input,
)
from services.admin_product.models import (
    EmptyQuery,
    ExecuteSubscriptionCommand,
    PaymentIntentCreate,
    PlansQuery,
    PreviewSubscriptionCommand,
    UsageQuery,
    subscription_command_adapter,
)
from services.admin_product.runtime import (
    close_default_product_bff_service,
    get_default_product_bff_service,
)
from services.admin_product.service import ProductBff, ProductSessionActor


router = APIRouter(tags=["product-subscription-bff"])

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$")
_IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._~-]{8,128}$")
_PAYMENT_INTENT_ID_PATTERN = re.compile(r"^pay_[a-f0-9]{32}$")
_MAX_BODY_BYTES = 16_384
_IDENTITY_OVERRIDE_HEADERS = (
    "x-user-id",
    "x-canonical-user-id",
    "x-platform-user-id",
    "x-external-user-id",
)
QueryT = TypeVar("QueryT", bound=BaseModel)


def get_product_bff_service() -> ProductBff:
    """FastAPI override seam; the default object is lazy and import-safe."""

    return get_default_product_bff_service()


def _request_id(request: Request) -> str:
    supplied = (request.headers.get("x-request-id") or "").strip()
    if supplied and _REQUEST_ID_PATTERN.fullmatch(supplied):
        return supplied
    return f"dream_product_{uuid.uuid4().hex}"


def _assert_no_identity_override(request: Request) -> None:
    if any(request.headers.get(header) is not None for header in _IDENTITY_OVERRIDE_HEADERS):
        raise ProductBffError(
            code="PRODUCT_USER_OVERRIDE_DENIED",
            message="Product user identity comes only from the Dream session.",
            status_code=400,
        )


def _assert_write_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if not origin:
        raise ProductBffError(
            code="PRODUCT_ORIGIN_REQUIRED",
            message="An allowed Origin is required for this request.",
            status_code=403,
        )
    allowed = parse_origin_allowlist(os.environ.get("INK_ADMIN_PRODUCT_ORIGIN"))
    if origin not in allowed:
        raise ProductBffError(
            code="PRODUCT_ORIGIN_DENIED",
            message="The request Origin is not allowed.",
            status_code=403,
        )


async def _session_actor(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
    required_scope: str,
) -> ProductSessionActor:
    try:
        owner = get_admin_request_auth(request, credentials)  # type: ignore[arg-type]
        if not credentials or credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=401)
        actor = await run_in_threadpool(
            owner.authenticate,
            credentials.credentials,
            _request_id(request),
            required_scopes=frozenset({required_scope}),
        )
    except (HTTPException, AdminDataError):
        raise ProductBffError(
            code="PRODUCT_AUTH_REQUIRED",
            message="A valid Dream session is required.",
            status_code=401,
        ) from None
    if not isinstance(actor, AdminRequestActor):
        raise ProductBffError(
            code="PRODUCT_AUTH_REQUIRED",
            message="A valid Dream session is required.",
            status_code=401,
        )
    return ProductSessionActor(
        canonical_user_id=actor.canonical_user_id,
        scopes=actor.scopes,
        access_token=actor.access_token,
    )


def _parse_query(request: Request, model: type[QueryT]) -> QueryT:
    entries: dict[str, str] = {}
    for key, value in request.query_params.multi_items():
        if key in entries:
            raise invalid_input(field=key)
        entries[key] = value
    try:
        return model.model_validate(entries)
    except ValidationError as exc:
        field = str(exc.errors()[0].get("loc", ["query"])[0]) if exc.errors() else None
        raise invalid_input(field=field) from None


async def _strict_json_payload(request: Request) -> dict[str, Any]:
    content_type = (request.headers.get("content-type") or "").split(";", 1)[0].strip()
    if content_type != "application/json":
        raise ProductBffError(
            code="PRODUCT_JSON_REQUIRED",
            message="The request body must use application/json.",
            status_code=415,
        )
    declared = request.headers.get("content-length")
    if declared:
        if not declared.isdigit():
            raise invalid_input(field="content-length") from None
        if int(declared) > _MAX_BODY_BYTES:
            raise ProductBffError(
                code="PRODUCT_BODY_TOO_LARGE",
                message="The request body is too large.",
                status_code=413,
            )
    body = await request.body()
    if len(body) > _MAX_BODY_BYTES:
        raise ProductBffError(
            code="PRODUCT_BODY_TOO_LARGE",
            message="The request body is too large.",
            status_code=413,
        )
    def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate JSON key")
            value[key] = item
        return value

    try:
        payload = json.loads(body, object_pairs_hook=strict_object)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        raise ProductBffError(
            code="PRODUCT_JSON_INVALID",
            message="The request body must contain valid JSON.",
            status_code=400,
        ) from None
    if not isinstance(payload, dict):
        raise invalid_input(field="body")
    return payload


async def _parse_command(
    request: Request,
) -> PreviewSubscriptionCommand | ExecuteSubscriptionCommand:
    try:
        return subscription_command_adapter.validate_python(
            await _strict_json_payload(request)
        )
    except ValidationError as exc:
        errors = exc.errors()
        location = errors[0].get("loc", ["body"]) if errors else ["body"]
        field = str(location[-1]) if location else "body"
        raise invalid_input(field=field) from None


async def _parse_payment_intent(request: Request) -> PaymentIntentCreate:
    try:
        return PaymentIntentCreate.model_validate(await _strict_json_payload(request))
    except ValidationError as exc:
        errors = exc.errors()
        location = errors[0].get("loc", ["body"]) if errors else ["body"]
        field = str(location[-1]) if location else "body"
        raise invalid_input(field=field) from None


def _required_idempotency_key(request: Request) -> str:
    supplied = request.headers.get("idempotency-key")
    if not supplied:
        raise ProductBffError(
            code="PRODUCT_IDEMPOTENCY_KEY_REQUIRED",
            message="Idempotency-Key is required for this request.",
            status_code=400,
        )
    if not _IDEMPOTENCY_KEY_PATTERN.fullmatch(supplied):
        raise invalid_input(field="Idempotency-Key")
    return supplied


def _idempotency_key(
    request: Request,
    command: PreviewSubscriptionCommand | ExecuteSubscriptionCommand,
) -> str | None:
    supplied = request.headers.get("idempotency-key")
    if isinstance(command, PreviewSubscriptionCommand):
        if supplied is not None:
            raise ProductBffError(
                code="PRODUCT_IDEMPOTENCY_KEY_NOT_ALLOWED",
                message="Idempotency-Key is allowed only for command execution.",
                status_code=400,
            )
        return None
    return _required_idempotency_key(request)


def _success(payload: dict[str, Any], request_id: str) -> JSONResponse:
    assert_safe_product_payload(payload)
    if payload.get("meta", {}).get("requestId") != request_id:
        raise ProductBffError(
            code="PRODUCT_DEPENDENCY_UNAVAILABLE",
            message="The subscription service returned an invalid response.",
            status_code=503,
        )
    return JSONResponse(
        content=payload,
        status_code=200,
        headers={"cache-control": "no-store", "x-request-id": request_id},
    )


def _error(error: ProductBffError, request_id: str) -> JSONResponse:
    details = error.details
    try:
        assert_safe_product_payload(details)
    except ProductBffError:
        error = dependency_unavailable()
        details = None
    body = {
        "error": {
            "code": error.code,
            "message": error.message,
            **({"details": details} if details is not None else {}),
        },
        "meta": {
            "requestId": request_id,
            **(
                {"retryAfterSeconds": error.retry_after_seconds}
                if error.retry_after_seconds is not None
                else {}
            ),
        },
    }
    headers = {"cache-control": "no-store", "x-request-id": request_id}
    if error.retry_after_seconds is not None:
        headers["retry-after"] = str(error.retry_after_seconds)
    return JSONResponse(content=body, status_code=error.status_code, headers=headers)


async def _read_route(
    *,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
    operation: Any,
) -> JSONResponse:
    request_id = _request_id(request)
    try:
        _assert_no_identity_override(request)
        actor = await _session_actor(request, credentials, "product:read")
        _parse_query(request, EmptyQuery)
        payload = await operation(actor, request_id)
        return _success(payload, request_id)
    except ProductBffError as exc:
        return _error(exc, request_id)
    except Exception:
        return _error(dependency_unavailable(), request_id)


@router.get("/api/story-workspace/subscription/context")
async def subscription_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    service: ProductBff = Depends(get_product_bff_service),
) -> JSONResponse:
    return await _read_route(
        request=request,
        credentials=credentials,
        operation=service.subscription_context,
    )


@router.get("/api/story-workspace/subscription/plans")
async def plans(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    service: ProductBff = Depends(get_product_bff_service),
) -> JSONResponse:
    request_id = _request_id(request)
    try:
        _assert_no_identity_override(request)
        actor = await _session_actor(request, credentials, "product:read")
        query = _parse_query(request, PlansQuery)
        return _success(await service.plans(actor, query, request_id), request_id)
    except ProductBffError as exc:
        return _error(exc, request_id)
    except Exception:
        return _error(dependency_unavailable(), request_id)


@router.get("/api/story-workspace/usage")
async def usage(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    service: ProductBff = Depends(get_product_bff_service),
) -> JSONResponse:
    request_id = _request_id(request)
    try:
        _assert_no_identity_override(request)
        actor = await _session_actor(request, credentials, "product:read")
        query = _parse_query(request, UsageQuery)
        return _success(await service.usage(actor, query, request_id), request_id)
    except ProductBffError as exc:
        return _error(exc, request_id)
    except Exception:
        return _error(dependency_unavailable(), request_id)


@router.get("/api/story-workspace/models")
async def models(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    service: ProductBff = Depends(get_product_bff_service),
) -> JSONResponse:
    return await _read_route(
        request=request,
        credentials=credentials,
        operation=service.model_catalog,
    )


@router.post("/api/story-workspace/subscription/commands")
async def subscription_commands(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    service: ProductBff = Depends(get_product_bff_service),
) -> JSONResponse:
    request_id = _request_id(request)
    try:
        _assert_write_origin(request)
        _assert_no_identity_override(request)
        actor = await _session_actor(request, credentials, "product:write")
        command = await _parse_command(request)
        idempotency_key = _idempotency_key(request, command)
        payload = await service.subscription_command(
            actor, command, request_id, idempotency_key
        )
        return _success(payload, request_id)
    except ProductBffError as exc:
        return _error(exc, request_id)
    except Exception:
        return _error(dependency_unavailable(), request_id)


@router.post("/api/story-workspace/subscription/payment-intents")
async def create_payment_intent(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    service: ProductBff = Depends(get_product_bff_service),
) -> JSONResponse:
    request_id = _request_id(request)
    try:
        _assert_write_origin(request)
        _assert_no_identity_override(request)
        actor = await _session_actor(request, credentials, "product:write")
        payment = await _parse_payment_intent(request)
        idempotency_key = _required_idempotency_key(request)
        payload = await service.create_payment_intent(
            actor, payment, request_id, idempotency_key
        )
        return _success(payload, request_id)
    except ProductBffError as exc:
        return _error(exc, request_id)
    except Exception:
        return _error(dependency_unavailable(), request_id)


@router.get("/api/story-workspace/subscription/payment-intents/{payment_intent_id}")
async def payment_intent(
    payment_intent_id: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    service: ProductBff = Depends(get_product_bff_service),
) -> JSONResponse:
    request_id = _request_id(request)
    try:
        _assert_no_identity_override(request)
        if not _PAYMENT_INTENT_ID_PATTERN.fullmatch(payment_intent_id):
            raise invalid_input(field="paymentIntentId")
        actor = await _session_actor(request, credentials, "product:read")
        _parse_query(request, EmptyQuery)
        payload = await service.payment_intent(
            actor, payment_intent_id, request_id
        )
        return _success(payload, request_id)
    except ProductBffError as exc:
        return _error(exc, request_id)
    except Exception:
        return _error(dependency_unavailable(), request_id)


@router.on_event("shutdown")
async def close_product_bff_runtime() -> None:
    await close_default_product_bff_service()
