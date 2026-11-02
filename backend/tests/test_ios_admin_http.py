# [Input] AdminDataConfig, the existing request_admin_dto DTO boundary, and a fake native callback.
# [Output] Provider-free proof of iOS Admin routing, response bounds, write semantics, and restoration.
# [Pos] Backend transport contract test; native/Xcode and real Admin acceptance remain separate.
# [Sync] 2026-10-31: cover iOS Admin JSON transport through the original HTTPX public entry.
# [Sync] 2026-10-31: use the published BrowserRevokedDTO and BrowserHandleRequestDTO at the typed boundary.

from __future__ import annotations

import base64
import json

import httpx
import pytest

import mobile_runtime.ios_admin_http as ios_admin_http
from services.admin_data.config import AdminDataConfig
from services.admin_data.errors import AdminDataError
from services.admin_data.http_transport import request_admin_dto
from services.admin_data.models import BrowserHandleRequestDTO, BrowserRevokedDTO


_HANDLE = "dbr_" + "a" * 43


def _config(*, max_response_bytes: int = 1024) -> AdminDataConfig:
    return AdminDataConfig(
        base_url="https://admin.example",
        issuer="https://admin.example/api/auth",
        resource="https://dream.example/api",
        service_secret="s" * 32,
        service_client_id="ios-service",
        transport_base_url="https://admin.example",
        timeout_seconds=1.5,
        max_response_bytes=max_response_bytes,
    )


def _wire(value: dict) -> str:
    return base64.b64encode(json.dumps(value, separators=(",", ":")).encode()).decode()


@pytest.fixture(autouse=True)
def _restore_httpx_transport():
    original = httpx.HTTPTransport.handle_request
    ios_admin_http._owner = None
    yield
    httpx.HTTPTransport.handle_request = original
    ios_admin_http._owner = None


def test_normal_dto_uses_native_once_and_preserves_request_body():
    calls: list[dict] = []

    def native(packet: str) -> str:
        calls.append(json.loads(packet))
        return json.dumps({
            "ok": True, "status": 200, "headers": {"content-type": "application/json"},
            "bodyBase64": _wire({"request_id": "req_normal", "data": {"value": "ok"}}),
        })

    config = _config()
    ios_admin_http.install_admin_http(config, native)
    with httpx.Client(transport=httpx.HTTPTransport(), trust_env=False) as client:
        request = httpx.Request("POST", config.transport_origin + "/api/internal/dream/v1/fixture",
                                headers={"accept": "application/json", "x-request-id": "req_normal"},
                                json={"value": "sent-once"})
        response = client.send(request, stream=True)
        try:
            body = json.loads(response.read())
        finally:
            response.close()
    assert len(calls) == 1
    assert calls[0]["method"] == "POST"
    assert calls[0]["url"].endswith("/api/internal/dream/v1/fixture")
    assert json.loads(base64.b64decode(calls[0]["bodyBase64"])) == {"value": "sent-once"}
    assert body == {"request_id": "req_normal", "data": {"value": "ok"}}


def test_request_admin_dto_returns_original_typed_dto():
    def native(packet: str) -> str:
        assert json.loads(packet)["url"].endswith("/api/internal/dream/v1/fixture")
        return json.dumps({
            "ok": True, "status": 200, "headers": {},
            "bodyBase64": _wire({"request_id": "req_dto", "data": {"revoked": True}}),
        })

    config = _config()
    ios_admin_http.install_admin_http(config, native)
    with httpx.Client(transport=httpx.HTTPTransport(), trust_env=False) as client:
        result = request_admin_dto(
            client, method="GET", url=config.transport_origin + "/api/internal/dream/v1/fixture",
            request_id="req_dto", output_type=BrowserRevokedDTO,
            headers={"accept": "application/json", "x-request-id": "req_dto"},
            timeout_seconds=1.5, max_response_bytes=1024,
        )
    assert isinstance(result, BrowserRevokedDTO)
    assert result.revoked is True


def test_error_envelope_preserves_code_status_and_request_id():
    def native(_: str) -> str:
        return json.dumps({
            "ok": True, "status": 403, "headers": {"content-type": "application/json"},
            "bodyBase64": _wire({"request_id": "req_denied", "error": {"code": "ADMIN_DENIED", "message": "denied"}}),
        })

    config = _config()
    ios_admin_http.install_admin_http(config, native)
    with httpx.Client(transport=httpx.HTTPTransport(), trust_env=False) as client:
        with pytest.raises(AdminDataError) as caught:
            request_admin_dto(
                client, method="GET", url=config.transport_origin + "/api/internal/dream/v1/fixture",
                request_id="req_denied", output_type=BrowserRevokedDTO,
                headers={"accept": "application/json", "x-request-id": "req_denied"},
                timeout_seconds=1.5, max_response_bytes=1024,
            )
    assert (caught.value.code, caught.value.status_code, caught.value.request_id) == ("ADMIN_DENIED", 403, "req_denied")


def test_max_response_bytes_rejects_max_plus_one():
    config = _config(max_response_bytes=4)

    def native(_: str) -> str:
        return json.dumps({"ok": True, "status": 200, "headers": {}, "bodyBase64": _wire({"x": "12345"})})

    ios_admin_http.install_admin_http(config, native)
    with httpx.Client(transport=httpx.HTTPTransport(), trust_env=False) as client:
        with pytest.raises(AdminDataError) as caught:
            request_admin_dto(
                client, method="GET", url=config.transport_origin + "/api/internal/dream/v1/fixture",
                request_id="req_large", output_type=BrowserRevokedDTO,
                headers={"accept": "application/json", "x-request-id": "req_large"},
                timeout_seconds=1.5, max_response_bytes=4,
            )
    assert caught.value.code == "ADMIN_RESPONSE_INVALID"
    assert caught.value.request_id == "req_large"


def test_write_transport_failure_is_single_dispatch_and_unknown():
    calls = 0

    def native(_: str) -> str:
        nonlocal calls
        calls += 1
        return json.dumps({"ok": False, "error": "transport"})

    config = _config()
    ios_admin_http.install_admin_http(config, native)
    with httpx.Client(transport=httpx.HTTPTransport(), trust_env=False) as client:
        with pytest.raises(AdminDataError) as caught:
            request_admin_dto(
                client, method="POST", url=config.transport_origin + "/api/internal/dream/v1/write",
                request_id="req_write", output_type=BrowserRevokedDTO,
                headers={"accept": "application/json", "x-request-id": "req_write"},
                timeout_seconds=1.5, max_response_bytes=1024,
                input_dto=BrowserHandleRequestDTO(request_id="req_write", handle=_HANDLE), write=True,
            )
    assert calls == 1
    assert (caught.value.code, caught.value.status_code, caught.value.outcome_unknown) == ("ADMIN_UNAVAILABLE", 503, True)


def test_non_manual_or_other_origin_uses_original_transport():
    fallback_calls = []

    def fallback(transport, request):
        fallback_calls.append((request.url, request.headers.get("x-request-id")))
        return httpx.Response(200, headers={"content-type": "application/json"},
                             content=json.dumps({"request_id": "req_other", "data": {"revoked": True}}),
                             request=request)

    original = httpx.HTTPTransport.handle_request
    httpx.HTTPTransport.handle_request = fallback
    config = _config()
    ios_admin_http.install_admin_http(config, lambda _: (_ for _ in ()).throw(AssertionError("native should not run")))
    with httpx.Client(transport=httpx.HTTPTransport(), trust_env=False) as client:
        result = request_admin_dto(
            client, method="GET", url="https://other.example/api/internal/dream/v1/fixture",
            request_id="req_other", output_type=BrowserRevokedDTO,
            headers={"accept": "application/json", "x-request-id": "req_other"},
            timeout_seconds=1.5, max_response_bytes=1024,
        )
    httpx.HTTPTransport.handle_request = original
    assert result.revoked is True
    assert fallback_calls == [("https://other.example/api/internal/dream/v1/fixture", "req_other")]


def test_malformed_native_response_fails_closed_without_body_leak():
    def native(_: str) -> str:
        return json.dumps({"ok": True, "status": 200, "headers": {"x": 3}, "bodyBase64": "%%%"})

    config = _config()
    ios_admin_http.install_admin_http(config, native)
    with httpx.Client(transport=httpx.HTTPTransport(), trust_env=False) as client:
        with pytest.raises(AdminDataError) as caught:
            request_admin_dto(
                client, method="GET", url=config.transport_origin + "/api/internal/dream/v1/fixture",
                request_id="req_bad", output_type=BrowserRevokedDTO,
                headers={"accept": "application/json", "x-request-id": "req_bad"},
                timeout_seconds=1.5, max_response_bytes=1024,
            )
    assert (caught.value.code, caught.value.status_code) == ("ADMIN_UNAVAILABLE", 503)
