# [Input] Production OAuthClientCredentialsTokenSource with a deterministic fake Admin transport.
# [Output] Basic client auth, exact grant/resource body, cache reuse and redacted failure evidence.
# [Pos] Provider-free OAuth machine-token protocol tests; no database or external HTTP.
# [Sync] 2026-09-17: validate the new Dream confidential-client token source.

from __future__ import annotations

from base64 import b64decode
import json

import httpx
import pytest

from services.admin_data.config import AdminDataConfig
from services.admin_data.errors import AdminDataError
from services.admin_data.service_token import OAuthClientCredentialsTokenSource


def _config() -> AdminDataConfig:
    return AdminDataConfig(
        base_url="https://admin.example",
        issuer="https://admin.example/api/auth",
        resource="https://dream.example/api",
        service_client_id="dream:service",
        service_secret="secret:value/" + "s" * 32,
    )


def test_client_credentials_uses_basic_auth_exact_resource_and_cache() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        scheme, encoded = request.headers["authorization"].split(" ", 1)
        assert scheme == "Basic"
        assert b64decode(encoded).decode("utf-8") == "dream%3Aservice:secret%3Avalue%2F" + "s" * 32
        assert request.content.decode("ascii") == "grant_type=client_credentials&resource=https%3A%2F%2Fdream.example%2Fapi"
        return httpx.Response(200, json={
            "access_token": "issued.service.token",
            "token_type": "Bearer",
            "expires_in": 300,
            "expires_at": 1_900_000_000,
            "scope": "capabilities:read",
        })

    clock = [10.0]
    client = httpx.Client(transport=httpx.MockTransport(handler))
    source = OAuthClientCredentialsTokenSource(_config(), client, monotonic=lambda: clock[0])
    assert source.access_token() == "issued.service.token"
    clock[0] = 100.0
    assert source.access_token() == "issued.service.token"
    assert len(calls) == 1


@pytest.mark.parametrize("response", [
    httpx.Response(401, json={"error": "invalid_client"}),
    httpx.Response(200, json={"access_token": "bad token", "token_type": "Bearer", "expires_in": 300, "scope": "capabilities:read"}),
])
def test_client_credentials_failures_are_redacted(response: httpx.Response) -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda _request: response))
    with pytest.raises(AdminDataError) as captured:
        OAuthClientCredentialsTokenSource(_config(), client).access_token()
    assert captured.value.code == "ADMIN_SERVICE_AUTH_UNAVAILABLE"
    assert "secret:value" not in repr(captured.value)
