# [Sync] 2026-09-17: verify confidential service OAuth and separate delegated-user Bearer transport.
# [Input] Actual preferences/default-voice routes, typed Admin DTO/auth transport and synthetic raw config text.
# [Output] Partial/null/object/numeric/time/permission and original-ID unknown-write contract evidence.
# [Pos] Provider-free public preferences harness; no PG, model or copied merge transaction.
# [Sync] 2026-09-15: fence Dream DB and verify two current-OAuth preference operations.
from __future__ import annotations

import json
import math
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.preferences import router
from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.preferences_data import PREFERENCES_OPERATIONS
from services.admin_data.request_auth import AdminRequestAuth
from services.admin_data.workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS
from tests.test_admin_request_auth import Verifier

FIELDS = {"voice_configs_json": None, "meta_prompt": None, "state_config_json": None, "selected_state": None, "timezone": None}
HEADERS = {"authorization": "Bearer write-token"}


def preference():
    return {**FIELDS, "first_login_completed": 1, "updated_at": "2026-09-15T03:02:01.123456+08:00"}


def boundary(monkeypatch):
    import database
    monkeypatch.setattr(database, "get_db", lambda: pytest.fail("Public preferences must not use Dream PG"))
    monkeypatch.setattr(database, "get_preferences", lambda *_: pytest.fail("Public preferences must use Admin"))
    monkeypatch.setattr(database, "save_preferences", lambda *_args, **_kwargs: pytest.fail("Public preferences must use Admin"))
    config = AdminDataConfig(base_url="https://admin.example", issuer="https://admin.example/api/auth",
        resource="https://dream.example/api", service_client_id="dream-service", service_secret="s" * 32)
    outputs = {"user-preferences.get": {"preferences": preference()}, "user-preferences.save": {"success": True}}
    schemas = [item.model_dump() for item in WORKFLOW_SCHEMA_REQUIREMENTS]
    operations = [item.capability.model_dump() for item in PREFERENCES_OPERATIONS]
    calls = []
    class PreferenceVerifier(Verifier):
        def verify(self, token, *, required_scopes):
            if token.startswith("idg_"):
                raise AdminDataError("INVALID_ACCESS_TOKEN", 401)
            return super().verify(token, required_scopes=required_scopes)
    def handler(request):
        request_id = request.headers["x-request-id"]
        UUID(request_id)
        if request.url.path.endswith("/capabilities"):
            value = {"version": "1", "auth": {"issuer": config.issuer, "jwks_uri": config.jwks_uri, "resource": config.resource,
                "algorithm": "ES256", "clients": {"browser": "dream-browser", "device": "dream-device"},
                "scopes": ["dream:read", "dream:write"], "delegations": []}, "schema_capabilities": schemas, "operations": operations}
        elif request.url.path.endswith("/principal"):
            value = {"subject": "opaque-ba-subject", "canonical_user_id": "42", "client_id": "dream-browser",
                "scopes": ["dream:read"] if request.headers["authorization"] == "Bearer read-token" else ["dream:read", "dream:write"], "status": "active"}
        else:
            name = request.url.path.rsplit("/", 1)[-1]
            body = json.loads(request.content)
            assert set(body) == {"request_id", "input"} and body["request_id"] == request_id
            assert not {"user_id", "actor_id", "first_login_completed", "system_config"} & body["input"].keys()
            assert request.headers["authorization"] in {"Bearer write-token", "Bearer read-token"}
            assert request.headers["x-ink-dream-service-authorization"] == "Bearer fixture.service.access.token"
            assert "x-ink-dream-credential" not in request.headers and "cookie" not in request.headers
            calls.append((name, body["input"], request_id))
            value = outputs[name]
            if isinstance(value, Exception):
                raise value
        return httpx.Response(200, json={"request_id": request_id, "data": value})
    client = AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(handler)), operations=PREFERENCES_OPERATIONS)
    app = FastAPI()
    app.state.admin_request_auth = AdminRequestAuth(config, client=client, verifier=PreferenceVerifier())
    app.include_router(router)
    return TestClient(app), calls, outputs, schemas, operations


def test_unsaved_get_is_empty_object_and_nullable_projection_keeps_original_fields(monkeypatch):
    client, calls, outputs, *_ = boundary(monkeypatch)
    with client:
        outputs["user-preferences.get"]["preferences"] = None
        assert client.get("/api/preferences", headers=HEADERS).json() == {}
        outputs["user-preferences.get"]["preferences"] = preference()
        response = client.get("/api/preferences", headers=HEADERS)
        assert response.status_code == 200 and response.json() == {"voice_configs": None, "meta_prompt": None,
            "state_config": None, "selected_state": None, "timezone": None, "first_login_completed": 1,
            "updated_at": "2026-09-15T03:02:01.123456+08:00"}
    assert [item[1] for item in calls] == [{}, {}]


def test_partial_null_and_empty_object_save_keep_original_merge_inputs(monkeypatch):
    client, calls, *_ = boundary(monkeypatch)
    with client:
        assert client.post("/api/preferences", headers=HEADERS, json={"meta_prompt": "写清楚", "timezone": "Asia/Shanghai"}).json() == {"success": True}
        assert client.post("/api/preferences", headers=HEADERS, json={"voice_configs": {}, "state_config": {}, "selected_state": None}).json() == {"success": True}
        assert client.post("/api/preferences", headers=HEADERS, json={}).json() == {"success": True}
    assert calls[0][1] == {**FIELDS, "meta_prompt": "写清楚", "timezone": "Asia/Shanghai"}
    assert calls[1][1] == {**FIELDS, "voice_configs_json": "{}", "state_config_json": "{}"}
    assert calls[2][1] == FIELDS
    assert len({item[2] for item in calls}) == 3


def test_config_raw_json_roundtrip_preserves_float_negative_zero_and_bigint(monkeypatch):
    client, calls, outputs, *_ = boundary(monkeypatch)
    numbers = {"float": 1.0, "negative": -0.0, "bigint": 9_007_199_254_740_993}
    with client:
        assert client.post("/api/preferences", headers=HEADERS, json={"voice_configs": numbers}).status_code == 200
        raw = calls[0][1]["voice_configs_json"]
        assert '"float": 1.0' in raw and '"negative": -0.0' in raw and '9007199254740993' in raw
        outputs["user-preferences.get"]["preferences"]["voice_configs_json"] = raw
        result = client.get("/api/preferences", headers=HEADERS).json()["voice_configs"]
    assert type(result["float"]) is float and type(result["negative"]) is float
    assert math.copysign(1, result["negative"]) == -1
    assert type(result["bigint"]) is int and result["bigint"] == numbers["bigint"]


def test_empty_text_is_written_and_public_nonfinite_json_is_rejected(monkeypatch):
    client, calls, *_ = boundary(monkeypatch)
    with client:
        assert client.post("/api/preferences", headers=HEADERS, json={"meta_prompt": "", "selected_state": "", "timezone": ""}).status_code == 200
        assert client.post("/api/preferences", headers={**HEADERS, "content-type": "application/json"}, content='{"state_config":{"nan":NaN}}').status_code == 422
    assert len(calls) == 1 and calls[0][1] == {**FIELDS, "meta_prompt": "", "selected_state": "", "timezone": ""}


@pytest.mark.parametrize("content", ['{"state_config":{"private":NaN}}',
    '{"voice_configs":{"private":Infinity}}', '{"state_config":{"private":1e400}}',
    '[{"private":NaN}]', '{"meta_prompt":"private",'])
def test_invalid_raw_public_json_has_safe_422_without_body_echo(monkeypatch, content):
    client, calls, *_ = boundary(monkeypatch)
    with client:
        response = client.post("/api/preferences", headers={**HEADERS, "content-type": "application/json"}, content=content)
    assert response.status_code == 422 and response.json() == {"detail": "Invalid preferences request"}
    assert not calls and "private" not in response.text


@pytest.mark.parametrize("field,value", [("user_id", "43"), ("actor_id", "43"), ("first_login_completed", 1),
    ("system_config", {}), ("voice_configs", []), ("state_config", "raw"), ("meta_prompt", False), ("timezone", 8)])
def test_invalid_public_fields_fail_without_domain_write(monkeypatch, field, value):
    client, calls, *_ = boundary(monkeypatch)
    with client:
        response = client.post("/api/preferences", headers=HEADERS, json={field: value})
    assert response.status_code == 422 and not calls


@pytest.mark.parametrize("field,value", [("voice_configs_json", "[]"), ("state_config_json", "malformed private"),
    ("voice_configs_json", '{"nan":NaN}'), ("state_config_json", '{"overflow":1e400}'),
    ("first_login_completed", True), ("updated_at", "2026-02-29T01:00:00Z"), ("system_config", {})])
def test_invalid_stored_projection_fails_safely_without_heal(monkeypatch, field, value):
    client, calls, outputs, *_ = boundary(monkeypatch)
    outputs["user-preferences.get"]["preferences"][field] = value
    with client:
        response = client.get("/api/preferences", headers=HEADERS)
    assert response.status_code == 503 and len(calls) == 1 and "malformed private" not in response.text
    assert all(name == "user-preferences.get" for name, *_ in calls)


@pytest.mark.parametrize("value", [False, 1, "true"])
def test_unconfirmed_save_reply_is_unknown(monkeypatch, value):
    client, calls, outputs, *_ = boundary(monkeypatch)
    outputs["user-preferences.save"]["success"] = value
    with client:
        response = client.post("/api/preferences", headers=HEADERS, json={})
    assert response.status_code == 503 and response.json()["detail"]["outcome_unknown"] is True
    assert response.json()["detail"]["request_id"] == calls[0][2]


def test_unknown_save_retains_original_request_id_without_post_retry(monkeypatch):
    client, calls, outputs, *_ = boundary(monkeypatch)
    outputs["user-preferences.save"] = httpx.ReadTimeout("synthetic private credential")
    with client:
        response = client.post("/api/preferences", headers=HEADERS, json={})
    assert response.status_code == 504 and response.json()["detail"]["outcome_unknown"] is True
    assert len(calls) == 1 and response.json()["detail"]["request_id"] == calls[0][2]
    assert "synthetic private" not in response.text


@pytest.mark.parametrize("index", range(2))
@pytest.mark.parametrize("damage", ["missing", "hash", "duplicate"])
def test_exact_physical_capabilities_required_before_domain_call(monkeypatch, index, damage):
    client, calls, _, schemas, _ = boundary(monkeypatch)
    if damage == "missing":
        schemas.pop(index)
    elif damage == "hash":
        schemas[index]["contract_sha256"] = "b" * 64
    else:
        schemas.append(dict(schemas[index]))
    with client:
        assert client.get("/api/preferences", headers=HEADERS).status_code == 503
    assert not calls


def test_operation_hash_drift_fails_before_domain_call(monkeypatch):
    client, calls, _, _, operations = boundary(monkeypatch)
    operations[0]["contract_sha256"] = "b" * 64
    with client:
        assert client.get("/api/preferences", headers=HEADERS).status_code == 503
    assert not calls


def test_default_voices_and_current_oauth_scope_rules_remain(monkeypatch):
    import config
    client, calls, *_ = boundary(monkeypatch)
    with client:
        assert client.get("/api/default-voices").json() == config.VOICE_ARCHETYPES
        assert not calls
        assert client.get("/api/preferences", headers={"authorization": "Bearer read-token"}).status_code == 200
        assert client.post("/api/preferences", headers={"authorization": "Bearer read-token"}, json={}).status_code == 403
        assert client.get("/api/preferences", headers={"authorization": "Bearer idg_" + "a" * 43}).status_code == 401
        client.cookies.set("access_token", "read-token")
        assert client.get("/api/preferences?token=read-token").status_code == 401
    assert len(calls) == 1
