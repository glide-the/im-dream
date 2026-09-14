# [Sync] 2026-09-15: retain isolated Run default DI; complete default ingress is verified separately.
# [Input] Public Run read/create/retry handlers, shared OAuth and published full Run DTOs.
# [Output] Full-state/time/source/key/error and explicit original receipt technical evidence.
# [Pos] Provider-free production harness; default Workspace loader is test-only dependency injection.
# [Sync] 2026-09-15: fence old domain SQL/services and retain unknown writes without retries.
from __future__ import annotations

import copy
import json
from uuid import UUID

import httpx
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from models.workflow_run import WorkflowRun
from routers.deps import get_current_user
from routers.story_workspace import _story_workflow_current_user, router
from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.request_auth import AdminRequestAuth
from services.admin_data.run_data import AdminRunData, CREATE_RUN, RETRY_RUN, RUN_OPERATIONS, RunCreateInputDTO, RunDTO
from services.admin_data.workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS
from services.errors.error_registry import WORKFLOW_RUN_ROUTE_ERRORS, build_error_payload, workflow_run_route_error
from tests.test_admin_request_auth import Verifier

RUN_ID = "run_" + "1" * 32
RETRY_ID = "run_" + "2" * 32
PREFLIGHT_ID = "pf_" + "3" * 32
URL = "/api/story-workspace/workflow-runs"
WRITE = {"authorization": "Bearer write-token"}
READ = {"authorization": "Bearer read-token"}


def run(status="queued"):
    value = {
        "workflow_run_id": RUN_ID, "deck_plugin_id": "plugin-1", "deck_plugin_version": "1.0.0",
        "workflow_definition_ref": "deck://plugin-1/workflow.json", "deck_runtime_snapshot_id": "snapshot-1",
        "status": status, "failed_step": None, "error_code": None, "retry_of_run_id": None,
        "deck_plugin_manifest_hash": "sha256:" + "a" * 64, "deck_plugin_binding_id": "binding-1",
        "binding_revision": 1, "runtime_plugin_lock_id": "lock-1", "runtime_load_receipt_id": None,
        "workflow_preflight_id": PREFLIGHT_ID, "agent_session_id": None, "source_voice_thread_id": None,
        "source_message_id": None, "source_message_time": None, "workspace_id": "existing-workspace-1",
        "idempotency_key": "business-key", "input_hash": "sha256:" + "b" * 64, "semantic_fingerprint": "sha256:" + "c" * 64,
        "status_version": 1, "created_by": "42", "created_at": "2026-09-14T00:00:00.123456+00:00",
        "started_at": None, "completed_at": None,
    }
    if status in {"running", "output_validating", "pending_review", "confirmed", "rejected", "completed"}:
        value.update(runtime_load_receipt_id="receipt-1", agent_session_id="as_" + "4" * 32, started_at="2026-09-14T00:00:00.123457+00:00")
    if status in {"failed", "cancelled", "rejected", "completed"}:
        value["completed_at"] = "2026-09-14T00:00:00.123458+00:00"
    if status == "failed":
        value.update(failed_step="original_step", error_code="original_failure")
    return value


def body():
    return {"workflow_preflight_id": PREFLIGHT_ID, "preflight_token": "synthetic-private-token", "idempotency_key": "business-key"}


@pytest.fixture
def boundary(monkeypatch):
    import database
    import routers.story_workspace as module
    def no_sql(*_a, **_kw):
        pytest.fail("Run domain must not open Dream SQL or old application service")
    monkeypatch.setattr(database, "get_db", no_sql)
    monkeypatch.setattr(module, "get_story_workflow_run_application_service", no_sql)
    config = AdminDataConfig(base_url="https://admin.example", issuer="https://admin.example/api/auth", resource="https://dream.example/api", service_client_id="dream-service", service_secret="s" * 32)
    state = {"result": {"run": run()}, "receipt": None}
    calls = []
    schemas = [item.model_dump() for item in WORKFLOW_SCHEMA_REQUIREMENTS]
    operations = [item.capability.model_dump() for item in RUN_OPERATIONS]
    class ScopeVerifier(Verifier):
        def verify(self, token, *, required_scopes):
            if token.startswith("idg_"):
                raise AdminDataError("INVALID_ACCESS_TOKEN", 401)
            return super().verify(token, required_scopes=required_scopes)
    def handler(request):
        rid = request.headers["x-request-id"]
        UUID(rid)
        assert request.headers["x-ink-dream-service"] == config.service_client_id
        assert request.headers["x-ink-dream-credential"] == config.service_secret
        assert "cookie" not in request.headers
        if request.url.path.endswith("/capabilities"):
            value = {"version": "1", "auth": {"issuer": config.issuer, "jwks_uri": config.jwks_uri, "resource": config.resource, "algorithm": "ES256", "clients": {"browser": "dream-browser", "device": "dream-device"}, "scopes": ["dream:read", "dream:write"], "delegations": []}, "schema_capabilities": schemas, "operations": operations}
        else:
            token = request.headers["authorization"].removeprefix("Bearer ")
            assert token in {"read-token", "write-token"}
            if request.url.path.endswith("/principal"):
                value = {"subject": "opaque-ba-subject", "canonical_user_id": "42", "client_id": "dream-browser", "scopes": ["dream:read", "dream:write"] if token == "write-token" else ["dream:read"], "status": "active"}
            else:
                if "/receipts/" in request.url.path:
                    assert request.method == "GET" and request.url.path.endswith("/" + rid)
                    operation = request.url.params["operation"]
                    calls.append(("receipt", rid, operation, None))
                    value = state["receipt"]
                else:
                    assert request.method == "POST"
                    operation = request.url.path.rsplit("/", 1)[-1]
                    envelope = json.loads(request.content)
                    assert set(envelope) == {"request_id", "input"} and envelope["request_id"] == rid
                    assert envelope["input"]["workspace_id"] == "existing-workspace-1"
                    calls.append(("execute", rid, operation, envelope["input"]))
                    value = state["result"]
                if isinstance(value, Exception):
                    raise value
                if isinstance(value, tuple):
                    status, code = value
                    return httpx.Response(status, json={"request_id": rid, "error": {"code": code, "message": "private upstream source/token"}})
        return httpx.Response(200, json={"request_id": rid, "data": value})
    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = AdminDataClient(config, client=http, operations=RUN_OPERATIONS)
    owner = AdminRequestAuth(config, client=client, verifier=ScopeVerifier())
    app = FastAPI()
    app.state.admin_request_auth = owner
    async def current_workspace(current_user=Depends(get_current_user)):
        return {**current_user, "workspace_id": "existing-workspace-1"}
    app.dependency_overrides[_story_workflow_current_user] = current_workspace
    app.include_router(router)
    with TestClient(app) as browser:
        yield browser, state, calls, schemas, operations, AdminRunData(client, canonical_user_id="42")
    owner.close()
    http.close()


@pytest.mark.parametrize("status", ["preflight", "queued", "running", "output_validating", "pending_review", "confirmed", "rejected", "completed", "failed", "cancelled"])
def test_read_all_original_states_full_fields(boundary, status):
    browser, state, calls, *_ = boundary
    value = state["result"]["run"] = run(status)
    value["deck_plugin_version"] = " 1.0.0\u0085"
    response = browser.get(URL + "/" + RUN_ID, headers=READ)
    assert response.status_code == 200 and response.json() == WorkflowRun.model_validate(value).model_dump(mode="json")
    assert len(response.json()) == 28 and response.json()["created_at"] == "2026-09-14T00:00:00.123456Z"
    assert len(calls) == 1 and calls[0][2] == "workflow-run.read"


def test_create_required_null_sources_and_old_semantic_pf_replay(boundary):
    browser, state, calls, *_ = boundary
    state["result"]["run"]["workflow_preflight_id"] = "pf_" + "9" * 32
    response = browser.post(URL, headers=WRITE, json=body())
    assert response.status_code == 201 and response.json()["workflow_preflight_id"] != PREFLIGHT_ID
    assert calls[0][3] == {"workspace_id": "existing-workspace-1", **body(), "source_voice_thread_id": None, "source_message_id": None, "source_message_time": None}


def test_create_source_time_keeps_original_python_precision_and_codepoints(boundary):
    browser, state, calls, *_ = boundary
    key = "😀" * 255
    source = {"source_voice_thread_id": "voice-thread", "source_message_id": "source-message", "source_message_time": "2026-09-14T08:00:00.123456999+08:00"}
    state["result"]["run"].update(idempotency_key=key, **{**source, "source_message_time": "2026-09-14T00:00:00.123456+00:00"})
    response = browser.post(URL, headers=WRITE, json={**body(), "idempotency_key": key, **source})
    assert response.status_code == 201 and response.json()["source_message_time"] == "2026-09-14T00:00:00.123456Z"
    assert calls[0][3]["source_message_time"] == "2026-09-14T08:00:00.123456+08:00" and calls[0][3]["idempotency_key"] == key
    assert "synthetic-private-token" not in repr(RunCreateInputDTO(**calls[0][3]))


def test_retry_has_no_source_preread_and_keeps_full_result(boundary):
    browser, state, calls, *_ = boundary
    state["result"]["run"].update(workflow_run_id=RETRY_ID, retry_of_run_id=RUN_ID)
    response = browser.post(URL + "/" + RUN_ID + "/retry", headers=WRITE, json=body())
    assert response.status_code == 201 and len(response.json()) == 28
    assert len(calls) == 1 and calls[0][2:] == ("workflow-run.retry", {"workspace_id": "existing-workspace-1", "workflow_run_id": RUN_ID, **body()})


@pytest.mark.parametrize("patch", [{"created_by": "43"}, {"workspace_id": "other-workspace"}, {"idempotency_key": "other-key"}, {"retry_of_run_id": RUN_ID}, {"source_voice_thread_id": "other-source"}, {"binding_revision": False}, {"status_version": 9_007_199_254_740_992}, {"extra": "private"}])
def test_invalid_write_reply_keeps_uuid_unknown_and_no_retry(boundary, patch):
    browser, state, calls, *_ = boundary
    state["result"]["run"].update(patch)
    response = browser.post(URL, headers=WRITE, json=body())
    assert response.status_code == 503 and response.json()["detail"] == {"error_code": "ADMIN_RESPONSE_INVALID", "request_id": calls[0][1], "outcome_unknown": True}
    assert len(calls) == 1 and "private" not in response.text


@pytest.mark.parametrize("patch", [{"workflow_run_id": RETRY_ID}, {"created_by": "43"}, {"workspace_id": "other"}, {"created_at": "2026-09-14T00:00:00.1234567Z"}, {"started_at": "2026-09-14T00:00:00.123455Z"}, {"status": "completed"}, {"source_message_time": "2026-09-14T00:00:00Z"}])
def test_invalid_read_reply_is_safe_without_unknown(boundary, patch):
    browser, state, calls, *_ = boundary
    state["result"]["run"].update(patch)
    response = browser.get(URL + "/" + RUN_ID, headers=READ)
    assert response.status_code == 503 and response.json()["detail"]["outcome_unknown"] is False and len(calls) == 1


@pytest.mark.parametrize("field", ["failed_step", "error_code", "retry_of_run_id", "runtime_load_receipt_id", "agent_session_id", "source_voice_thread_id", "source_message_id", "source_message_time", "started_at", "completed_at"])
def test_nullable_wire_fields_are_required(boundary, field):
    browser, state, calls, *_ = boundary
    state["result"]["run"].pop(field)
    assert browser.get(URL + "/" + RUN_ID, headers=READ).status_code == 503 and len(calls) == 1


@pytest.mark.parametrize("raw", ["wrong", " " + RUN_ID, RUN_ID + " ", RUN_ID.upper()])
@pytest.mark.parametrize("suffix,method", [("", "get"), ("/retry", "post")])
def test_bad_path_is_original_404_before_domain_io(boundary, raw, suffix, method):
    browser, _, calls, *_ = boundary
    response = getattr(browser, method)(URL + "/" + raw + suffix, headers=WRITE, **({"json": body()} if method == "post" else {}))
    assert response.status_code == 404 and response.json() == build_error_payload("AGENT_EXECUTION_FAILED") and not calls


@pytest.mark.parametrize("mutation", ["schema-missing", "schema-hash", "schema-duplicate", "operation-hash", "operation-missing"])
def test_exact_capabilities_before_domain_write(boundary, mutation):
    browser, _, calls, schemas, operations, *_ = boundary
    if mutation == "schema-missing": schemas.pop()
    elif mutation == "schema-hash": schemas[-1]["contract_sha256"] = "0" * 64
    elif mutation == "schema-duplicate": schemas.append(copy.copy(schemas[0]))
    elif mutation == "operation-hash": operations[1]["contract_sha256"] = "0" * 64
    else: operations.pop(1)
    assert browser.post(URL, headers=WRITE, json=body()).status_code == 503 and not calls


@pytest.mark.parametrize("token,status", [(None, 401), ("expired-token", 401), ("idg_server", 401), ("read-token", 403)])
def test_public_write_scope_and_current_oauth(boundary, token, status):
    browser, _, calls, *_ = boundary
    response = browser.post(URL, headers={} if token is None else {"authorization": "Bearer " + token}, json=body())
    assert response.status_code == status and not calls


@pytest.mark.parametrize("patch", [{"source_voice_thread_id": "thread-only"}, {"source_message_id": "message-only"}, {"source_voice_thread_id": "thread", "source_message_id": "message", "source_message_time": "2026-09-14T00:00:00"}, {"source_message_time": "private-invalid-time"}, {"idempotency_key": "\x1c"}])
def test_invalid_source_or_python_blank_key_is_original_422(boundary, patch):
    browser, _, calls, *_ = boundary
    response = browser.post(URL, headers=WRITE, json={**body(), **patch})
    assert response.status_code == 422 and response.json() == build_error_payload("AGENT_EXECUTION_FAILED") and not calls
    assert "private" not in response.text and "synthetic" not in response.text


@pytest.mark.parametrize("patch", [{"preflight_token": False}, {"idempotency_key": "😀" * 256}, {"workflow_preflight_id": "private-invalid"}, {"extra": "private source"}])
@pytest.mark.parametrize("suffix", ["", "/" + RUN_ID + "/retry"])
def test_scoped_framework_validation_does_not_echo_token_source(boundary, patch, suffix):
    browser, _, calls, *_ = boundary
    response = browser.post(URL + suffix, headers=WRITE, json={**body(), **patch})
    assert response.status_code == 422 and response.json() == {"detail": "Invalid Workflow Run request"} and not calls


@pytest.mark.parametrize("code,pair", list(WORKFLOW_RUN_ROUTE_ERRORS.items()) + [("INVALID_RUN_REQUEST", ("AGENT_EXECUTION_FAILED", 400))])
def test_original_business_error_mapping(boundary, code, pair):
    browser, state, calls, *_ = boundary
    state["result"] = (pair[1], code)
    expected = workflow_run_route_error(code)
    response = browser.post(URL, headers=WRITE, json=body())
    assert response.status_code == expected.status_code and response.json() == build_error_payload(expected.code)
    assert len(calls) == 1 and "private upstream" not in response.text


@pytest.mark.parametrize("status,code", [(503, "PREFLIGHT_TOKEN_INVALID"), (403, "WORKFLOW_SOURCE_NOT_AUTHORIZED"), (400, "INPUT_INVALID")])
def test_other_admin_errors_keep_safe_uuid_without_aliases(boundary, status, code):
    browser, state, calls, *_ = boundary
    state["result"] = (status, code)
    response = browser.post(URL, headers=WRITE, json=body())
    assert response.status_code == status and response.json()["detail"] == {"error_code": code, "request_id": calls[0][1], "outcome_unknown": status >= 500}


@pytest.mark.parametrize("operation,suffix", [(CREATE_RUN, ""), (RETRY_RUN, "/" + RUN_ID + "/retry")])
@pytest.mark.parametrize("status", ["absent", "committed"])
def test_unknown_write_explicit_same_uuid_generic_receipt(boundary, operation, suffix, status):
    browser, state, calls, *_, data = boundary
    value = copy.deepcopy(state["result"])
    if operation is RETRY_RUN:
        value["run"].update(workflow_run_id=RETRY_ID, retry_of_run_id=RUN_ID)
    state["result"] = httpx.ReadTimeout("private body/token")
    response = browser.post(URL + suffix, headers=WRITE, json=body())
    rid = calls[0][1]
    assert response.status_code == 504 and response.json()["detail"] == {"error_code": "ADMIN_TIMEOUT", "request_id": rid, "outcome_unknown": True}
    state["receipt"] = {"status": status, "operation": operation.capability.name, "request_id": rid, **({"result": value} if status == "committed" else {})}
    dto = operation.input_dto(**calls[0][3])
    result = data.receipt(operation, dto, rid, access_token="write-token")
    assert result.status == status and len(calls) == 2 and calls[-1][:3] == ("receipt", rid, operation.capability.name)


@pytest.mark.parametrize("patch", [{"created_by": "43"}, {"workspace_id": "other"}, {"idempotency_key": "other"}, {"retry_of_run_id": RUN_ID}])
def test_bounded_receipt_mismatch_rejected_without_execute(boundary, patch):
    _, state, calls, *_, data = boundary
    from uuid import uuid4
    rid = str(uuid4())
    value = run()
    value.update(patch)
    state["receipt"] = {"status": "committed", "operation": "workflow-run.create", "request_id": rid, "result": {"run": value}}
    dto = RunCreateInputDTO(workspace_id="existing-workspace-1", **body(), source_voice_thread_id=None, source_message_id=None, source_message_time=None)
    with pytest.raises(AdminDataError) as captured:
        data.receipt(CREATE_RUN, dto, rid, access_token="write-token")
    assert captured.value.code == "ADMIN_RESPONSE_INVALID" and not captured.value.outcome_unknown
    assert len(calls) == 1 and calls[0][0] == "receipt"


def test_dto_original_source_projection_and_strict_integer():
    value = run()
    value.update(source_voice_thread_id="legacy-thread-only")
    assert RunDTO.model_validate(value).model_dump()["source_message_id"] is None
    value["status_version"] = 1.0
    with pytest.raises(ValidationError): RunDTO.model_validate(value)


def test_receipt_wrong_operation_or_input_rejected_before_http(boundary):
    _, _, calls, *_, data = boundary
    from services.admin_data.run_data import READ_RUN
    from uuid import uuid4
    for operation, value in [(READ_RUN, {}), (CREATE_RUN, {})]:
        with pytest.raises(AdminDataError):
            data.receipt(operation, value, str(uuid4()), access_token="write-token")
    assert not calls
