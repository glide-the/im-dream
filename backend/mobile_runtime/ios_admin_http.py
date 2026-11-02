# [Input] Server-owned Admin origin/limits, original HTTPX requests and the App native HTTP function.
# [Output] Original HTTPX responses and errors through iOS URLSession for Admin JSON backchannels.
# [Pos] iOS transport binding; DTO, JWT, scope, persistence and read/write recovery remain upstream.
from __future__ import annotations

import base64
import binascii
from collections.abc import Callable
import json
import math

import httpx

from services.admin_data.config import ADMIN_INTERNAL_PREFIX, AUTH_PATH, AdminDataConfig

_owner: tuple[str, float, int] | None = None


def install_admin_http(config: AdminDataConfig, native_request: Callable[[str], str]) -> None:
    global _owner
    identity = (config.transport_origin, config.timeout_seconds, config.max_response_bytes)
    if _owner is not None:
        if identity != _owner:
            raise RuntimeError("IOS_ADMIN_HTTP_OWNER_ALREADY_BOUND")
        return
    selected = httpx.URL(config.transport_origin)
    original = httpx.HTTPTransport.handle_request

    def handle(transport: httpx.HTTPTransport, request: httpx.Request) -> httpx.Response:
        url = request.url
        if ((url.scheme, url.host, url.port) != (selected.scheme, selected.host, selected.port)
            or not (url.path.startswith(ADMIN_INTERNAL_PREFIX + "/")
                    or url.path in {AUTH_PATH + "/oauth2/token", AUTH_PATH + "/jwks"})):
            return original(transport, request)
        timeout = request.extensions.get("timeout", {}).get("read", config.timeout_seconds)
        if timeout is None:
            timeout = config.timeout_seconds
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise httpx.TransportError("Invalid iOS Admin timeout", request=request)
        payload = {"url": str(url), "method": request.method, "headers": dict(request.headers),
                   "bodyBase64": base64.b64encode(request.read()).decode("ascii"),
                   "timeoutSeconds": timeout, "maxResponseBytes": config.max_response_bytes}
        try:
            response = json.loads(native_request(json.dumps(payload)))
        except Exception:
            raise httpx.ReadError("iOS Admin transport failed", request=request) from None
        if not isinstance(response, dict) or response.get("ok") is not True:
            error = response.get("error") if isinstance(response, dict) else None
            exception = httpx.ReadTimeout if error == "timeout" else httpx.ReadError
            raise exception("iOS Admin transport failed", request=request)
        try:
            status, headers = response["status"], response["headers"]
            if (type(status) is not int or not 100 <= status <= 599 or not isinstance(headers, dict)
                or any(not isinstance(key, str) or not isinstance(value, str) for key, value in headers.items())):
                raise ValueError
            body = base64.b64decode(response["bodyBase64"], validate=True)
            return httpx.Response(status, headers=headers, stream=httpx.ByteStream(body), request=request)
        except (KeyError, ValueError, TypeError, binascii.Error):
            raise httpx.ReadError("Invalid iOS Admin response", request=request) from None

    httpx.HTTPTransport.handle_request = handle
    _owner = identity
