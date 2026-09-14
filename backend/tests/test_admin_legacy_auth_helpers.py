# [Input] Retired authentication helpers and named script contracts with synthetic credentials.
# [Output] Provider-free refusal/account-binding evidence; no local credentials or persistent actions.
# [Pos] Legacy authority retirement regression tests.
# [Sync] 2026-09-15: verify helpers refuse local authority and import labels fail before I/O.
from __future__ import annotations

from types import SimpleNamespace

import httpx
import jwt
import pytest

import auth
from backend.script import import_diaries as importer


@pytest.mark.parametrize("call", [
    lambda: auth.create_access_token(1, "synthetic@example.com"),
    lambda: auth.create_refresh_token_value(),
    lambda: auth.hash_password("synthetic-password"),
    lambda: auth.verify_password("synthetic-password", "synthetic-hash"),
])
def test_retired_helpers_cannot_issue_or_authenticate(call, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "synthetic-legacy-secret")
    with pytest.raises(auth.LegacyAuthenticationRetired) as failure:
        call()
    assert "synthetic" not in str(failure.value)


def test_legacy_hmac_token_is_rejected_even_with_matching_environment(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "synthetic-legacy-secret")
    token = jwt.encode({"user_id": 1, "email": "synthetic@example.com"}, "synthetic-legacy-secret", algorithm="HS256")
    assert auth.verify_access_token(token) is None
    assert auth.maybe_renew_access_token({"user_id": 1, "exp": 0}) is None


def test_import_agent_missing_credential_stops_before_files_or_database(monkeypatch):
    monkeypatch.setattr(importer, "parse_args", lambda: SimpleNamespace(label_mode="agent", api_token=None))
    def forbidden(*args, **kwargs):
        pytest.fail("Missing OAuth must stop before files/database/network")
    monkeypatch.setattr(importer, "resolve_source_dir", forbidden)
    monkeypatch.setattr(importer.database, "get_db", forbidden)
    with pytest.raises(SystemExit, match="explicit --api-token"):
        importer.main()
    with pytest.raises(SystemExit, match="explicit --api-token"):
        importer._build_agent_token(1)


@pytest.mark.parametrize("raw", [None, "", " ", "synthetic token", "synthetic\x00token", "synthetic\x7ftoken"])
def test_import_agent_rejects_invalid_credential_without_reflection(raw):
    with pytest.raises(SystemExit) as failure:
        importer._require_agent_token(raw)
    assert "synthetic" not in str(failure.value)


@pytest.mark.parametrize("status,profile,accepted", [
    (200, {"id": 7}, True), (200, {"id": 8}, False),
    (200, {"id": True}, False), (200, {"id": "7"}, False),
    (401, {"id": 7}, False), (302, {"id": 7}, False),
])
def test_import_agent_uses_public_profile_to_bind_existing_account(monkeypatch, status, profile, accepted):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(status, json=profile)
    real_client = httpx.Client
    monkeypatch.setattr(importer._httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))
    if accepted:
        importer._require_agent_account("https://dream.example", "synthetic-oauth", 7)
    else:
        with pytest.raises(SystemExit, match="must match"):
            importer._require_agent_account("https://dream.example", "synthetic-oauth", 7)
    assert len(requests) == 1
    assert str(requests[0].url) == "https://dream.example/api/me"
    assert requests[0].headers["authorization"] == "Bearer synthetic-oauth"
