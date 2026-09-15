# [Input] Public Preflight GET/Auth/HTTP and controlled original lifecycle projections.
# [Output] Full-field, owner, token, microsecond, capability and no-Dream-SQL evidence.
# [Pos] Provider-free production-entry harness; no real database, model or signing authority.
# [Sync] 2026-09-15: fence legacy Workspace/service dependencies and reuse the original public model.
# [Sync] 2026-09-15: stop patching the retired router Workspace symbol after its production removal.
from __future__ import annotations

import copy
import json
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from models.workflow_preflight import WorkflowPreflight
from routers.story_workspace import router
from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.preflight_data import PreflightDTO, READ_PREFLIGHT
from services.admin_data.request_auth import AdminRequestAuth
from services.admin_data.workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS
from services.errors.error_registry import build_error_payload
from tests.test_admin_request_auth import Verifier

PREFLIGHT_ID = "pf_" + "1" * 32
URL = "/api/story-workspace/workflow-preflights/" + PREFLIGHT_ID
HEADERS = {"authorization": "Bearer read-token"}


def preflight():
    return {
        "workflow_preflight_id": PREFLIGHT_ID, "deck_id": "deck-1", "binding_revision": 0,
        "deck_plugin_id": "plugin-1", "deck_plugin_version": "1.0.0", "runtime_plugin_lock_id": "lock-1",
        "deck_runtime_profile_id": "profile-1", "deck_runtime_snapshot_id": "snapshot-1",
        "deck_runtime_snapshot_summary_hash": "original-summary", "input_hash": "sha256:" + "a" * 64,
        "status": "passed", "error_code": None, "failed_check": None,
        "expires_at": "2026-09-14T00:00:00.123457+00:00", "preflight_token": "synthetic-pft",
        "created_by": "42", "created_at": "2026-09-14T00:00:00.123456+00:00",
    }


@pytest.fixture
def boundary(monkeypatch):
    import database
    import routers.story_workspace as module
    def no_legacy(*_a, **_kw):
        pytest.fail("Preflight GET must not use Dream SQL/default Workspace/old service")
    monkeypatch.setattr(database, "get_db", no_legacy)
    monkeypatch.setattr(module, "get_story_workflow_run_application_service", no_legacy)
    config = AdminDataConfig(base_url="https://admin.example", issuer="https://admin.example/api/auth", resource="https://dream.example/api", service_client_id="dream-service", service_secret="s" * 32)
    state = {"result": {"preflight": preflight()}}
    calls = []
    schemas = [item.model_dump() for item in WORKFLOW_SCHEMA_REQUIREMENTS]
    operations = [READ_PREFLIGHT.capability.model_dump()]
    class ReadVerifier(Verifier):
        def verify(self, token, *, required_scopes):
            if token.startswith("idg_"):
                raise AdminDataError("INVALID_ACCESS_TOKEN", 401)
            return super().verify(token, required_scopes=required_scopes)
    def handler(request):
        rid = request.headers["x-request-id"]
        UUID(rid)
        assert request.headers["x-ink-dream-service"] == config.service_client_id
        assert request.headers["x-ink-dream-credential"] == config.service_secret
        if request.url.path.endswith("/capabilities"):
            value = {"version": "1", "auth": {"issuer": config.issuer, "jwks_uri": config.jwks_uri, "resource": config.resource, "algorithm": "ES256", "clients": {"browser": "dream-browser", "device": "dream-device"}, "scopes": ["dream:read", "dream:write"], "delegations": []}, "schema_capabilities": schemas, "operations": operations}
        elif request.url.path.endswith("/principal"):
            value = {"subject": "opaque-ba-subject", "canonical_user_id": "42", "client_id": "dream-browser", "scopes": ["dream:read"], "status": "active"}
        else:
            assert request.url.path.endswith("/operations/workflow-preflight.read")
            assert request.headers["authorization"] == "Bearer read-token" and "cookie" not in request.headers
            body = json.loads(request.content)
            assert set(body) == {"request_id", "input"} and body["request_id"] == rid
            assert body["input"] == {"workflow_preflight_id": PREFLIGHT_ID}
            calls.append(rid)
            value = state["result"]
            if isinstance(value, Exception):
                raise value
            if isinstance(value, tuple):
                status, code = value
                return httpx.Response(status, json={"request_id": rid, "error": {"code": code, "message": "private upstream body"}})
        return httpx.Response(200, json={"request_id": rid, "data": value})
    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = AdminDataClient(config, client=http, operations=(READ_PREFLIGHT,))
    app = FastAPI()
    owner = AdminRequestAuth(config, client=client, verifier=ReadVerifier())
    app.state.admin_request_auth = owner
    app.include_router(router)
    with TestClient(app) as browser:
        yield browser, state, calls, schemas, operations
    owner.close()
    http.close()


@pytest.mark.parametrize("status,token", [("passed", "synthetic-pft"), ("passed", None), ("checking", None), ("failed", None), ("expired", None)])
def test_all_states_preserve_original_full_public_projection(boundary, status, token):
    browser, state, calls, *_ = boundary
    value = state["result"]["preflight"]
    value.update(status=status, preflight_token=token)
    if status != "passed":
        value.update(deck_runtime_snapshot_id=None, deck_runtime_snapshot_summary_hash=None)
    if status == "failed":
        value.update(error_code="ORIGINAL_FAILURE", failed_check="binding_release")
    expected = WorkflowPreflight.model_validate(value).model_dump(mode="json")
    response = browser.get(URL, headers=HEADERS)
    assert response.status_code == 200 and response.json() == expected
    assert len(response.json()) == 17 and len(calls) == 1
    assert response.json()["created_at"] == "2026-09-14T00:00:00.123456Z"
    assert "synthetic-pft" not in repr(PreflightDTO.model_validate(value))


def test_original_string_strip_and_offset_datetime_json(boundary):
    browser, state, *_ = boundary
    value = state["result"]["preflight"]
    value.update(deck_id=" deck-1\u0085", deck_runtime_snapshot_id="", deck_runtime_snapshot_summary_hash="", preflight_token="", created_at="2026-09-14T08:00:00.123456+08:00")
    expected = WorkflowPreflight.model_validate(value).model_dump(mode="json")
    response = browser.get(URL, headers=HEADERS)
    assert response.status_code == 200 and response.json() == expected


@pytest.mark.parametrize("field", ["deck_runtime_snapshot_id", "deck_runtime_snapshot_summary_hash", "error_code", "failed_check", "preflight_token"])
def test_nullable_fields_are_required_on_wire(boundary, field):
    browser, state, *_ = boundary
    state["result"]["preflight"].pop(field)
    assert browser.get(URL, headers=HEADERS).status_code == 503


@pytest.mark.parametrize("patch", [
    {"binding_revision": -1}, {"binding_revision": True}, {"binding_revision": 1.0}, {"binding_revision": 9_007_199_254_740_992},
    {"created_by": "43"}, {"workflow_preflight_id": "pf_" + "2" * 32}, {"input_hash": "sha256:invalid"},
    {"unexpected": "private"}, {"preflight_token": 0}, {"status": "invalid"}, {"error_code": "private"},
    {"status": "failed", "error_code": "private", "failed_check": "binding_release", "preflight_token": "private"},
    {"status": "failed", "preflight_token": None}, {"status": "checking"}, {"deck_runtime_snapshot_id": None},
    {"expires_at": "2026-09-14T00:00:00.123456Z"}, {"expires_at": "2026-09-14T00:00:00.123455Z"},
    {"expires_at": "2026-09-14T00:00:00.1234571Z"}, {"created_at": "2026-09-14T00:00:00"},
    {"created_at": " 2026-09-14T00:00:00.123456Z "}, {"created_at": "2026-02-30T00:00:00Z"},
])
def test_invalid_projection_fails_safely_without_second_read(boundary, patch):
    browser, state, calls, *_ = boundary
    state["result"]["preflight"].update(patch)
    response = browser.get(URL, headers=HEADERS)
    assert response.status_code == 503 and response.json()["detail"] == {"error_code": "ADMIN_RESPONSE_INVALID", "request_id": calls[0], "outcome_unknown": False}
    assert len(calls) == 1 and "private" not in response.text and "synthetic-pft" not in response.text


@pytest.mark.parametrize("value", [None, {}, {"preflight": None}, {"preflight": []}])
def test_missing_and_wrong_outer_projection_fails_closed(boundary, value):
    browser, state, *_ = boundary
    state["result"] = value
    assert browser.get(URL, headers=HEADERS).status_code == 503


@pytest.mark.parametrize("mutation", ["schema-missing", "schema-hash", "schema-duplicate", "op-missing", "op-hash"])
def test_exact_two_schemas_and_registered_operation_before_domain_io(boundary, mutation):
    browser, _, calls, schemas, operations = boundary
    if mutation == "schema-missing":
        schemas.pop()
    elif mutation == "schema-hash":
        schemas[0]["contract_sha256"] = "0" * 64
    elif mutation == "schema-duplicate":
        schemas.append(copy.copy(schemas[0]))
    elif mutation == "op-missing":
        operations.clear()
    else:
        operations[0]["contract_sha256"] = "0" * 64
    assert browser.get(URL, headers=HEADERS).status_code == 503 and not calls


@pytest.mark.parametrize("bad_id", ["not-a-preflight", "PF_" + "1" * 32, "pf_" + "g" * 32, PREFLIGHT_ID + "%20", "%20" + PREFLIGHT_ID])
def test_bad_public_path_keeps_old_404_without_admin_read(boundary, bad_id):
    browser, _, calls, *_ = boundary
    response = browser.get("/api/story-workspace/workflow-preflights/" + bad_id, headers=HEADERS)
    assert response.status_code == 404 and response.json() == build_error_payload("WORKFLOW_PERMISSION_DENIED") and not calls


@pytest.mark.parametrize("status", [403, 404])
def test_owner_or_missing_reply_keeps_original_404(boundary, status):
    browser, state, calls, *_ = boundary
    state["result"] = (status, "WORKFLOW_PERMISSION_DENIED")
    response = browser.get(URL, headers=HEADERS)
    assert response.status_code == 404 and response.json() == build_error_payload("WORKFLOW_PERMISSION_DENIED") and len(calls) == 1


@pytest.mark.parametrize("token", [None, "expired-token", "idg_synthetic"])
def test_shared_oauth_rejects_absent_expired_and_runtime_grant(boundary, token):
    browser, _, calls, *_ = boundary
    response = browser.get(URL, headers={} if token is None else {"authorization": "Bearer " + token})
    assert response.status_code == 401 and not calls


def test_timeout_keeps_same_request_id_without_retry(boundary):
    browser, state, calls, *_ = boundary
    state["result"] = httpx.ReadTimeout("private token")
    response = browser.get(URL, headers=HEADERS)
    assert response.status_code == 504 and response.json()["detail"] == {"error_code": "ADMIN_TIMEOUT", "request_id": calls[0], "outcome_unknown": False}
    assert len(calls) == 1 and "private" not in response.text
