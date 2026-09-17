# [Input] Explicit configured URL, per-request headers, strict DTO and bounded httpx client.
# [Output] Correlated closed response with one bounded read-only transport recovery, preserving unknown write outcomes.
# [Pos] Shared HTTP parser; holds no service, user, DB or Gateway authentication configuration.
# [Sync] 2026-09-17: recover one stale read-only transport while never replaying a dispatched write.
"""Send exactly the supplied headers, without ambient client cookies or credentials."""

from __future__ import annotations

from typing import Literal

import httpx
from pydantic import BaseModel, TypeAdapter, ValidationError

from .errors import AdminDataError, invalid_response, unavailable
from .models import ErrorEnvelopeDTO, RequestDTO, ResponseEnvelopeDTO


def request_admin_dto(http: httpx.Client, *, method: Literal["GET", "POST"], url: str,
    request_id: str, output_type, headers: dict[str, str], timeout_seconds: float,
    max_response_bytes: int, input_dto: BaseModel | None = None,
    params: dict[str, str] | None = None, write: bool = False):
    RequestDTO(request_id=request_id)
    # Client.build_request/stream merge default headers and cookies. A prepared
    # Request keeps server authentication confined to this explicit projection.
    raw: bytearray | None = None
    status: int | None = None
    for attempt in range(2 if not write else 1):
        # Read operations and receipt lookups are side-effect free even when the
        # operation ingress uses POST. A short second transport attempt repairs
        # a stale pooled connection without extending an unavailable Admin by a
        # second full timeout. Writes remain single-dispatch.
        timeout = timeout_seconds if attempt == 0 else min(2.0, timeout_seconds)
        request = httpx.Request(method, url, headers=headers, params=params,
            json=input_dto.model_dump(mode="json") if input_dto is not None else None,
            extensions={"timeout": {key: timeout for key in ("connect", "read", "write", "pool")}})
        try:
            response = http.send(request, stream=True, follow_redirects=False, auth=None)
            try:
                status = response.status_code
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > max_response_bytes:
                        raise invalid_response(request_id, write=write)
            finally:
                response.close()
            break
        except httpx.TimeoutException:
            if write or attempt == 1:
                raise AdminDataError("ADMIN_TIMEOUT", 504, request_id, write) from None
        except httpx.HTTPError:
            if write or attempt == 1:
                raise unavailable(request_id, write=write) from None
    if raw is None or status is None:
        raise unavailable(request_id, write=write)
    if not 200 <= status < 300:
        if status not in {400, 401, 403, 404, 409, 422, 429, 503, 504}:
            raise unavailable(request_id, write=write)
        try:
            error = ErrorEnvelopeDTO.model_validate_json(raw)
            if error.request_id != request_id:
                raise invalid_response(request_id, write=write)
        except ValidationError:
            raise invalid_response(request_id, write=write) from None
        raise AdminDataError(error.error.code, status, request_id,
            write and status >= 500, error.error.details)
    try:
        result = TypeAdapter(ResponseEnvelopeDTO[output_type]).validate_json(raw)
    except ValidationError:
        raise invalid_response(request_id, write=write) from None
    if result.request_id != request_id:
        raise invalid_response(request_id, write=write)
    return result.data
