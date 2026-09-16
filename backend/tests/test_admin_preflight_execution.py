# [Sync] 2026-09-15: keep isolated PF default DI; complete default ingress has a separate production-path suite.
# [Input] Public PF POST/Auth/HTTP plus original request-state and receipt contracts.
# [Output] Domain execution, raw Python JSON, three-state recovery and safe rejection evidence.
# [Pos] Provider-free harness; default Workspace is explicitly injected, not a whole no-PG proof.
# [Sync] 2026-09-15: exercise the production handler/DTO/client; never resume or resend an unknown write.
from __future__ import annotations

import copy
import json
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from models.workflow_preflight import WorkflowPreflight
from routers.deps import get_current_user
from routers.story_workspace import _story_workflow_current_user, router
from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.preflight_data import AdminPreflightData, EXECUTE_PREFLIGHT, PREFLIGHT_EXECUTION_SCHEMA_REQUIREMENTS, PreflightExecutionInputDTO, READ_PREFLIGHT
from services.admin_data.request_auth import AdminRequestAuth
from tests.test_admin_preflight_routes import preflight
from tests.test_admin_request_auth import Verifier

URL = "/api/story-workspace/workflow-preflights"
HEADERS = {"authorization": "Bearer write-token"}


def request_body():
    return {"deck_id": "deck-1", "binding_revision": 0, "input": {"goal": "private prose", "float": 1.0, "negative_zero": -0.0, "large": 9_007_199_254_740_993, "中文": "原文"}}


@pytest.fixture
def boundary(monkeypatch):
    import database
    import routers.story_workspace as module
    def no_sql(*_a, **_kw):
        pytest.fail("PF domain execution must not open Dream PG or old service")
    monkeypatch.setattr(database, "get_db", no_sql)
    config = AdminDataConfig(base_url="https://admin.example", issuer="https://admin.example/api/auth", resource="https://dream.example/api", service_client_id="dream-service", service_secret="s" * 32)
    state = {"execute": {"request_state": "committed", "preflight": preflight()}, "receipt": None}
    calls = []
    schemas = [item.model_dump() for item in PREFLIGHT_EXECUTION_SCHEMA_REQUIREMENTS]
    operations = [spec.capability.model_dump() for spec in (READ_PREFLIGHT, EXECUTE_PREFLIGHT)]
    class ScopeVerifier(Verifier):
        def verify(self, token, *, required_scopes):
            if token.startswith("idg_"):
                raise AdminDataError("INVALID_ACCESS_TOKEN", 401)
            return super().verify(token, required_scopes=required_scopes)
    def handler(request):
        rid = request.headers["x-request-id"]
        UUID(rid)
        if request.url.path.endswith("/capabilities"):
            value = {"version": "1", "auth": {"issuer": config.issuer, "jwks_uri": config.jwks_uri, "resource": config.resource, "algorithm": "ES256", "clients": {"browser": "dream-browser", "device": "dream-device"}, "scopes": ["dream:read", "dream:write"], "delegations": []}, "schema_capabilities": schemas, "operations": operations}
        else:
            assert request.headers["authorization"] == "Bearer write-token" and "cookie" not in request.headers
            if request.url.path.endswith("/principal"):
                value = {"subject": "opaque-ba-subject", "canonical_user_id": "42", "client_id": "dream-browser", "scopes": ["dream:read", "dream:write"], "status": "active"}
            elif "/receipts/" in request.url.path:
                assert request.method == "GET" and request.url.path.endswith("/" + rid)
                assert dict(request.url.params) == {"operation": "workflow-preflight.execute"}
                calls.append(("receipt", rid, None))
                value = state["receipt"]
                if isinstance(value, Exception):
                    raise value
            else:
                assert request.url.path.endswith("/operations/workflow-preflight.execute")
                body = json.loads(request.content)
                assert set(body) == {"request_id", "input"} and body["request_id"] == rid
                assert set(body["input"]) == {"workspace_id", "deck_id", "binding_revision", "input_json"}
                assert body["input"]["workspace_id"] == "existing-workspace-1"
                calls.append(("execute", rid, body["input"]))
                value = state["execute"]
                if isinstance(value, Exception):
                    raise value
        return httpx.Response(200, json={"request_id": rid, "data": value})
    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = AdminDataClient(config, client=http, operations=(READ_PREFLIGHT, EXECUTE_PREFLIGHT))
    owner = AdminRequestAuth(config, client=client, verifier=ScopeVerifier())
    app = FastAPI()
    app.state.admin_request_auth = owner
    # Isolate this PF contract with a harness-only default loader. The separate
    # default Workspace suite retains the production Admin loader end-to-end.
    async def current_workspace(current_user=Depends(get_current_user)):
        return {**current_user, "workspace_id": "existing-workspace-1"}
    app.dependency_overrides[_story_workflow_current_user] = current_workspace
    app.include_router(router)
    with TestClient(app) as browser:
        yield browser, state, calls, schemas, operations, AdminPreflightData(client, canonical_user_id="42"), client
    owner.close()
    http.close()


@pytest.mark.parametrize("request_state,status", [("in_progress", "checking"), ("committed", "checking"), ("committed", "passed"), ("committed", "failed"), ("committed", "expired")])
def test_original_202_full_fields_without_resuming_checks(boundary, request_state, status):
    browser, state, calls, *_ = boundary
    value = state["execute"]["preflight"]
    state["execute"]["request_state"] = request_state
    value.update(status=status, preflight_token=None)
    if status == "failed":
        value.update(error_code="ORIGINAL_FAILURE", failed_check="binding_release")
    response = browser.post(URL, headers=HEADERS, json=request_body())
    assert response.status_code == 202 and response.json() == WorkflowPreflight.model_validate(value).model_dump(mode="json")
    assert len(response.json()) == 17 and len(calls) == 1 and calls[0][0] == "execute"
    raw = calls[0][2]["input_json"]
    expected = json.dumps(request_body()["input"], ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True)
    assert raw == expected and '"float":1.0' in raw and '"negative_zero":-0.0' in raw and '9007199254740993' in raw
    assert "private prose" not in repr(PreflightExecutionInputDTO(**calls[0][2]))


@pytest.mark.parametrize("patch", [{"created_by": "43"}, {"deck_id": "other-deck"}, {"binding_revision": 1}, {"preflight_token": False}, {"unexpected": "private"}])
def test_bad_write_reply_is_unknown_and_never_retried(boundary, patch):
    browser, state, calls, *_ = boundary
    state["execute"]["preflight"].update(patch)
    response = browser.post(URL, headers=HEADERS, json=request_body())
    assert response.status_code == 503 and response.json()["detail"] == {"error_code": "ADMIN_RESPONSE_INVALID", "request_id": calls[0][1], "outcome_unknown": True}
    assert len(calls) == 1 and "private" not in response.text and "synthetic-pft" not in response.text


def test_in_progress_cannot_report_passed_or_a_token(boundary):
    browser, state, calls, *_ = boundary
    state["execute"]["request_state"] = "in_progress"
    assert browser.post(URL, headers=HEADERS, json=request_body()).status_code == 503 and len(calls) == 1


@pytest.mark.parametrize("mutation", ["request-schema-missing", "request-schema-hash", "duplicate-schema", "execute-hash", "execute-missing"])
def test_three_exact_schemas_and_execute_contract_before_write(boundary, mutation):
    browser, _, calls, schemas, operations, *_ = boundary
    if mutation == "request-schema-missing":
        schemas.pop()
    elif mutation == "request-schema-hash":
        schemas[-1]["contract_sha256"] = "0" * 64
    elif mutation == "duplicate-schema":
        schemas.append(copy.copy(schemas[0]))
    elif mutation == "execute-hash":
        operations[-1]["contract_sha256"] = "0" * 64
    else:
        operations.pop()
    assert browser.post(URL, headers=HEADERS, json=request_body()).status_code == 503 and not calls


@pytest.mark.parametrize("token,status", [(None, 401), ("expired-token", 401), ("idg_synthetic", 401), ("read-token", 403)])
def test_oauth_write_required_before_domain_operation(boundary, token, status):
    browser, _, calls, *_ = boundary
    response = browser.post(URL, headers={} if token is None else {"authorization": "Bearer " + token}, json=request_body())
    assert response.status_code == status and not calls


@pytest.mark.parametrize("patch", [{"binding_revision": 9_007_199_254_740_992}, {"binding_revision": -1}, {"input": []}, {"input": {"private": float("inf")}}, {"deck_id": ""}, {"private": "not-a-field"}])
def test_safe_public_validation_never_echoes_input(boundary, patch):
    browser, _, calls, *_ = boundary
    body = {**request_body(), **patch}
    # json.dumps permits a synthetic nonfinite input here; httpx json= forbids it.
    response = browser.post(URL, headers={**HEADERS, "content-type": "application/json"}, content=json.dumps(body))
    assert response.status_code == 422 and response.json() == {"detail": "Invalid Preflight request"} and not calls


@pytest.mark.parametrize("status", ["absent", "in_progress", "committed"])
def test_unknown_write_recovers_same_uuid_by_explicit_read_only_receipt(boundary, status):
    browser, state, calls, _, _, data, _ = boundary
    state["execute"] = httpx.ReadTimeout("private body")
    response = browser.post(URL, headers=HEADERS, json=request_body())
    rid = calls[0][1]
    assert response.status_code == 504 and response.json()["detail"] == {"error_code": "ADMIN_TIMEOUT", "request_id": rid, "outcome_unknown": True} and len(calls) == 1
    receipt = {"status": status, "operation": "workflow-preflight.execute", "request_id": rid}
    if status != "absent":
        value = preflight()
        if status == "in_progress":
            value.update(status="checking", preflight_token=None)
        receipt["result"] = {"request_state": status, "preflight": value}
    state["receipt"] = receipt
    result = data.receipt(rid, access_token="write-token")
    assert result.model_dump() == receipt and calls == [calls[0], ("receipt", rid, None)]
    assert "synthetic-pft" not in repr(result)


@pytest.mark.parametrize("mutation", ["operation", "request-id", "actor", "state", "checking", "absent-result", "extra"])
def test_receipt_mismatch_is_safe_and_does_not_execute(boundary, mutation):
    _, state, calls, _, _, data, _ = boundary
    rid = str(uuid4())
    receipt = {"status": "committed", "operation": "workflow-preflight.execute", "request_id": rid, "result": {"request_state": "committed", "preflight": preflight()}}
    if mutation == "operation":
        receipt["operation"] = "other-operation"
    elif mutation == "request-id":
        receipt["request_id"] = str(uuid4())
    elif mutation == "actor":
        receipt["result"]["preflight"]["created_by"] = "43"
    elif mutation == "state":
        receipt["result"]["request_state"] = "in_progress"
    elif mutation == "checking":
        receipt["status"] = receipt["result"]["request_state"] = "in_progress"
    elif mutation == "absent-result":
        receipt["status"] = "absent"
    else:
        receipt["private"] = "body"
    state["receipt"] = receipt
    with pytest.raises(AdminDataError) as error:
        data.receipt(rid, access_token="write-token")
    assert error.value.code == "ADMIN_RESPONSE_INVALID" and not error.value.outcome_unknown
    assert len(calls) == 1 and calls[0] == ("receipt", rid, None) and "private" not in str(error.value)


@pytest.mark.parametrize("raw", ["[]", "null", "true", "1", '{"n":NaN}', "not-json"])
def test_wire_input_requires_actual_object_json(raw):
    with pytest.raises(ValidationError):
        PreflightExecutionInputDTO(workspace_id="workspace", deck_id="deck", binding_revision=0, input_json=raw)


def test_pydantic_identifier_strip_does_not_rewrite_extra_python_controls():
    dto = PreflightExecutionInputDTO(workspace_id=" workspace\u0085", deck_id="\u001Cdeck\u001F", binding_revision=0, input_json=" {\"a\":1} ")
    assert dto.workspace_id == "workspace" and dto.deck_id == "\u001Cdeck\u001F" and dto.input_json == " {\"a\":1} "
