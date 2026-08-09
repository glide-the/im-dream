"""Five same-origin Dream BFF routes for the Token-only Product API."""

from __future__ import annotations

import json
import os
import re
import uuid
from typing import Any, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, ValidationError

from .deps import get_current_user, http_bearer
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
    PlansQuery,
    PreviewSubscriptionCommand,
    UsageQuery,
    subscription_command_adapter,
)
from services.admin_product.runtime import (
    close_default_product_bff_service,
    get_default_product_bff_service,
)
from services.admin_product.service import ProductBff


router = APIRouter(tags=["product-subscription-bff"])

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$")
_IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._~-]{8,128}$")
_MAX_BODY_BYTES = 16_384
_POSTGRES_BIGINT_MAXIMUM = 9_223_372_036_854_775_807
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


def _session_subject(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None,
) -> str:
    try:
        user = get_current_user(request, response, credentials)
    except HTTPException:
        raise ProductBffError(
            code="PRODUCT_AUTH_REQUIRED",
            message="A valid Dream session is required.",
            status_code=401,
        ) from None
    user_id = user.get("user_id") if isinstance(user, dict) else None
    if isinstance(user_id, bool) or not isinstance(user_id, (int, str)):
        raise ProductBffError(
            code="PRODUCT_AUTH_REQUIRED",
            message="A valid Dream session is required.",
            status_code=401,
        )
    subject = str(user_id)
    if (
        not re.fullmatch(r"[1-9]\d{0,18}", subject)
        or int(subject) > _POSTGRES_BIGINT_MAXIMUM
    ):
        raise ProductBffError(
            code="PRODUCT_AUTH_REQUIRED",
            message="A valid Dream session is required.",
            status_code=401,
        )
    return subject


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


async def _parse_command(
    request: Request,
) -> PreviewSubscriptionCommand | ExecuteSubscriptionCommand:
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
    try:
        return subscription_command_adapter.validate_python(payload)
    except ValidationError as exc:
        errors = exc.errors()
        location = errors[0].get("loc", ["body"]) if errors else ["body"]
        field = str(location[-1]) if location else "body"
        raise invalid_input(field=field) from None


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
    if not supplied:
        raise ProductBffError(
            code="PRODUCT_IDEMPOTENCY_KEY_REQUIRED",
            message="Idempotency-Key is required for command execution.",
            status_code=400,
        )
    if not _IDEMPOTENCY_KEY_PATTERN.fullmatch(supplied):
        raise invalid_input(field="Idempotency-Key")
    return supplied


def _copy_session_renewal(source: Response, target: Response) -> None:
    for key, value in source.raw_headers:
        lowered = key.lower()
        if lowered in {b"x-new-access-token", b"set-cookie"}:
            target.raw_headers.append((key, value))


def _success(
    payload: dict[str, Any], session_response: Response, request_id: str
) -> JSONResponse:
    assert_safe_product_payload(payload)
    if payload.get("meta", {}).get("requestId") != request_id:
        raise ProductBffError(
            code="PRODUCT_DEPENDENCY_UNAVAILABLE",
            message="The subscription service returned an invalid response.",
            status_code=503,
        )
    response = JSONResponse(
        content=payload,
        status_code=200,
        headers={"cache-control": "no-store", "x-request-id": request_id},
    )
    _copy_session_renewal(session_response, response)
    return response


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
    session_response: Response,
    credentials: HTTPAuthorizationCredentials | None,
    operation: Any,
) -> JSONResponse:
    request_id = _request_id(request)
    try:
        _assert_no_identity_override(request)
        subject = _session_subject(request, session_response, credentials)
        _parse_query(request, EmptyQuery)
        payload = await operation(subject, request_id)
        return _success(payload, session_response, request_id)
    except ProductBffError as exc:
        return _error(exc, request_id)
    except Exception:
        return _error(dependency_unavailable(), request_id)


@router.get("/api/story-workspace/subscription/context")
async def subscription_context(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    service: ProductBff = Depends(get_product_bff_service),
) -> JSONResponse:
    return await _read_route(
        request=request,
        session_response=response,
        credentials=credentials,
        operation=service.subscription_context,
    )


@router.get("/api/story-workspace/subscription/plans")
async def plans(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    service: ProductBff = Depends(get_product_bff_service),
) -> JSONResponse:
    request_id = _request_id(request)
    try:
        _assert_no_identity_override(request)
        subject = _session_subject(request, response, credentials)
        query = _parse_query(request, PlansQuery)
        return _success(
            await service.plans(subject, query, request_id), response, request_id
        )
    except ProductBffError as exc:
        return _error(exc, request_id)
    except Exception:
        return _error(dependency_unavailable(), request_id)


@router.get("/api/story-workspace/usage")
async def usage(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    service: ProductBff = Depends(get_product_bff_service),
) -> JSONResponse:
    request_id = _request_id(request)
    try:
        _assert_no_identity_override(request)
        subject = _session_subject(request, response, credentials)
        query = _parse_query(request, UsageQuery)
        return _success(
            await service.usage(subject, query, request_id), response, request_id
        )
    except ProductBffError as exc:
        return _error(exc, request_id)
    except Exception:
        return _error(dependency_unavailable(), request_id)


@router.get("/api/story-workspace/models")
async def models(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    service: ProductBff = Depends(get_product_bff_service),
) -> JSONResponse:
    return await _read_route(
        request=request,
        session_response=response,
        credentials=credentials,
        operation=service.model_catalog,
    )


@router.post("/api/story-workspace/subscription/commands")
async def subscription_commands(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    service: ProductBff = Depends(get_product_bff_service),
) -> JSONResponse:
    request_id = _request_id(request)
    try:
        _assert_write_origin(request)
        _assert_no_identity_override(request)
        subject = _session_subject(request, response, credentials)
        command = await _parse_command(request)
        idempotency_key = _idempotency_key(request, command)
        payload = await service.subscription_command(
            subject, command, request_id, idempotency_key
        )
        return _success(payload, response, request_id)
    except ProductBffError as exc:
        return _error(exc, request_id)
    except Exception:
        return _error(dependency_unavailable(), request_id)


@router.on_event("shutdown")
async def close_product_bff_runtime() -> None:
    await close_default_product_bff_service()
