# [Sync] 2026-09-15: share current profile/explicit write-only secret scopes with the real Deck resolver harness.
# [Input] Registered76 DTO/client and actual default-dependent FastAPI Workflow ingress.
# [Output] Default-before-domain, original text ID, scope/unknown-write and receipt technical evidence.
# [Pos] Provider-free harness; Admin transport is injected, production default loader is retained.
# [Sync] 2026-09-15: fence Dream SQL and exercise shared OAuth, complete PF/Run and no-resend recovery.
# [Sync] 2026-09-15: share the real default ingress fixture with public Run cancel, without a copied loader.
from __future__ import annotations

import json
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from routers.story_workspace import router
from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError, OAuthPrincipalClaims
from services.admin_data.preflight_data import EXECUTE_PREFLIGHT, READ_PREFLIGHT, PREFLIGHT_EXECUTION_SCHEMA_REQUIREMENTS
from services.admin_data.deck_plugin_binding_data import READ_BINDING
from services.admin_data.request_auth import AdminRequestAuth
from services.admin_data.profile_data import CURRENT_PROFILE
from services.admin_data.run_data import RUN_OPERATIONS
from services.admin_data.workspace_data import AdminWorkspaceData, ENSURE_DEFAULT_WORKSPACE, WorkspaceDefaultInputDTO, WorkspaceDefaultOutputDTO
from tests.test_admin_preflight_execution import request_body
from tests.test_admin_preflight_routes import PREFLIGHT_ID, preflight
from tests.test_admin_request_auth import Verifier, profile_value
from tests.test_admin_run_routes import RUN_ID, body, run

PREFIX = "/api/story-workspace"
WRITE = {"authorization": "Bearer write-token"}
READ = {"authorization": "Bearer read-token"}


@pytest.fixture
def boundary(monkeypatch):
    import database
    import routers.story_workspace as module

    def no_sql(*_a, **_kw):
        pytest.fail("Default-dependent Workflow ingress must not open Dream SQL or old domain service")

    monkeypatch.setattr(database, "get_db", no_sql)
    config = AdminDataConfig(base_url="https://admin.example", issuer="https://admin.example/api/auth", resource="https://dream.example/api", service_client_id="dream-service", service_secret="s" * 32)
    registered_operations = (ENSURE_DEFAULT_WORKSPACE, READ_PREFLIGHT, EXECUTE_PREFLIGHT, *RUN_OPERATIONS, CURRENT_PROFILE, READ_BINDING)
    operations = [item.capability.model_dump() for item in registered_operations]
    schemas = [item.model_dump() for item in PREFLIGHT_EXECUTION_SCHEMA_REQUIREMENTS]
    state = {"default": {"workspace_id": "existing-workspace-1"}, "receipt": None, "receipt_operation": "workspace-default.ensure", "cancel": {"run": run("cancelled")}, "profile": {"user": profile_value()}}
    calls = []

    class ScopeVerifier(Verifier):
        def verify(self, token, *, required_scopes):
            if token.startswith("idg_"):
                raise AdminDataError("INVALID_ACCESS_TOKEN", 401)
            if token == "write-only-token":
                scopes = frozenset({"dream:write"})
                if not required_scopes <= scopes:
                    raise AdminDataError("INSUFFICIENT_SCOPE", 403)
                return OAuthPrincipalClaims("opaque-ba-subject", "dream-browser", scopes, "token-id", 100, 400)
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
            assert token in {"read-token", "write-token", "write-only-token"}
            if request.url.path.endswith("/principal"):
                scopes = ["dream:read", "dream:write"] if token == "write-token" else ["dream:write"] if token == "write-only-token" else ["dream:read"]
                value = {"subject": "opaque-ba-subject", "canonical_user_id": "42", "client_id": "dream-browser", "scopes": scopes, "status": "active"}
            elif "/receipts/" in request.url.path:
                assert request.method == "GET" and dict(request.url.params) == {"operation": state["receipt_operation"]}
                assert request.url.path.endswith("/" + rid)
                calls.append(("receipt", rid, None))
                value = state["receipt"]
            else:
                assert request.method == "POST"
                operation = request.url.path.rsplit("/", 1)[-1]
                envelope = json.loads(request.content)
                assert set(envelope) == {"request_id", "input"} and envelope["request_id"] == rid
                calls.append((operation, rid, envelope["input"]))
                if operation == "workspace-default.ensure":
                    assert token in {"write-token", "write-only-token"} and envelope["input"] == {}
                    value = state["default"]
                elif operation == "workflow-preflight.execute":
                    assert envelope["input"]["workspace_id"] == "existing-workspace-1"
                    pf = preflight()
                    pf["binding_revision"] = envelope["input"]["binding_revision"]
                    value = {"request_state": "committed", "preflight": pf}
                elif operation == "workflow-preflight.read":
                    value = {"preflight": preflight()}
                elif operation == "user-profile.current":
                    assert envelope["input"] == {}
                    value = state["profile"]
                elif operation == "deck-plugin-binding.current":
                    value = {
                        "deck_id": envelope["input"]["deck_id"],
                        "binding_revision": 0,
                        "applied_to": "next_run",
                        "binding": None,
                    }
                else:
                    assert envelope["input"]["workspace_id"] == "existing-workspace-1"
                    row = run()
                    if operation == "workflow-run.retry":
                        row["retry_of_run_id"] = RUN_ID
                    value = state["cancel"] if operation == "workflow-run.cancel" else {"run": row}
            if isinstance(value, Exception):
                raise value
            if isinstance(value, tuple):
                status, code = value
                return httpx.Response(status, json={"request_id": rid, "error": {"code": code, "message": "synthetic private upstream content"}})
        return httpx.Response(200, json={"request_id": rid, "data": value})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = AdminDataClient(config, client=http, operations=registered_operations)
    owner = AdminRequestAuth(config, client=client, verifier=ScopeVerifier())
    app = FastAPI()
    app.state.admin_request_auth = owner
    app.include_router(router)
    assert not app.dependency_overrides
    with TestClient(app) as browser:
        yield browser, state, calls, schemas, operations, AdminWorkspaceData(client, canonical_user_id="42")
    owner.close()
    http.close()


@pytest.mark.parametrize("path,method,payload,status,operation,fields", [
    ("/workflow-preflights", "POST", request_body(), 202, "workflow-preflight.execute", 17),
    ("/workflow-runs", "POST", body(), 201, "workflow-run.create", 28),
    ("/workflow-runs/" + RUN_ID + "/retry", "POST", body(), 201, "workflow-run.retry", 28),
    ("/workflow-runs/" + RUN_ID, "GET", None, 200, "workflow-run.read", 28),
])
def test_original_default_loader_then_actual_public_domain(boundary, path, method, payload, status, operation, fields):
    browser, _state, calls, *_ = boundary
    response = browser.request(method, PREFIX + path, headers=WRITE, **({"json": payload} if payload is not None else {}))
    assert response.status_code == status and len(response.json()) == fields
    assert [item[0] for item in calls] == ["workspace-default.ensure", operation]
    assert calls[0][2] == {} and calls[0][1] != calls[1][1]


@pytest.mark.parametrize("headers,status", [({}, 401), (READ, 403), ({"authorization": "Bearer idg_" + "a" * 43}, 401), ({"authorization": "Bearer expired-token"}, 401)])
def test_default_write_scope_does_not_expand_read_or_editor_access(boundary, headers, status):
    browser, _state, calls, *_ = boundary
    response = browser.get(PREFIX + "/workflow-runs/" + RUN_ID, headers=headers)
    assert response.status_code == status and calls == []


def test_readonly_preflight_get_keeps_independent_no_default_path(boundary):
    browser, _state, calls, *_ = boundary
    response = browser.get(PREFIX + "/workflow-preflights/" + PREFLIGHT_ID, headers=READ)
    assert response.status_code == 200 and len(response.json()) == 17
    assert [item[0] for item in calls] == ["workflow-preflight.read"]


@pytest.mark.parametrize("result", [{}, {"workspace_id": ""}, {"workspace_id": None}, {"workspace_id": 12}, {"workspace_id": "legacy", "owner_id": "42"}, httpx.ReadTimeout("synthetic private upstream content")])
def test_unknown_initialization_stops_before_domain_and_does_not_resend(boundary, result):
    browser, state, calls, *_ = boundary
    state["default"] = result
    response = browser.post(PREFIX + "/workflow-runs", headers=WRITE, json=body())
    assert response.status_code == (504 if isinstance(result, httpx.TimeoutException) else 503)
    detail = response.json()["detail"]
    assert detail["outcome_unknown"] is True and detail["request_id"] == calls[0][1]
    assert [item[0] for item in calls] == ["workspace-default.ensure"]
    assert "private upstream" not in response.text


@pytest.mark.parametrize("status,code", [(401, "INVALID_ACCESS_TOKEN"), (403, "WORKSPACE_DEFAULT_PERMISSION_DENIED"), (503, "ADMIN_UNAVAILABLE")])
def test_initialization_rejection_stops_before_domain(boundary, status, code):
    browser, state, calls, *_ = boundary
    state["default"] = (status, code)
    response = browser.post(PREFIX + "/workflow-preflights", headers=WRITE, json=request_body())
    assert response.status_code == status
    assert [item[0] for item in calls] == ["workspace-default.ensure"]
    assert "private upstream" not in response.text


@pytest.mark.parametrize("fault", ["identity", "unified", "schema_hash", "operation_hash", "operation_missing"])
def test_missing_exact_capability_blocks_default_before_http(boundary, fault):
    browser, _state, calls, schemas, operations, _data = boundary
    if fault in {"identity", "unified"}:
        schemas[:] = [item for item in schemas if item["capability"] != ("identity.better-auth.v1" if fault == "identity" else "dream.schema.unified.v1")]
    elif fault == "schema_hash":
        schemas[0]["contract_sha256"] = "0" * 64
    elif fault == "operation_hash":
        operations[0]["contract_sha256"] = "0" * 64
    else:
        operations.pop(0)
    response = browser.post(PREFIX + "/workflow-runs", headers=WRITE, json=body())
    assert response.status_code == 503 and calls == []


@pytest.mark.parametrize("workspace_id", ["legacy-text-id", "  legacy\n", "\u0085", "x" * 300, "非UUID工作区"])
def test_original_workspace_text_is_not_repaired_or_restricted(boundary, workspace_id):
    _browser, state, calls, _schemas, _operations, data = boundary
    state["default"] = {"workspace_id": workspace_id}
    result = data.ensure_default(WorkspaceDefaultInputDTO(), "a7e9e6ec-9900-4e07-b37b-113ba1d6b2ea", access_token="write-token")
    assert result.workspace_id == workspace_id and calls[0][2] == {}


@pytest.mark.parametrize("status", ["absent", "committed"])
def test_original_uuid_two_state_receipt_never_initializes_again(boundary, status):
    browser, state, calls, _schemas, _operations, data = boundary
    state["default"] = httpx.ReadTimeout("synthetic private upstream content")
    response = browser.post(PREFIX + "/workflow-runs", headers=WRITE, json=body())
    rid = response.json()["detail"]["request_id"]
    state["receipt"] = {"status": status, "operation": "workspace-default.ensure", "request_id": rid, **({"result": {"workspace_id": "legacy-text-id"}} if status == "committed" else {})}
    receipt = data.default_receipt(rid, access_token="write-token")
    assert receipt.status == status
    if status == "committed":
        assert receipt.result.workspace_id == "legacy-text-id"
    assert [item[0] for item in calls] == ["workspace-default.ensure", "receipt"] and calls[1][1] == rid


def test_default_dto_rejects_caller_identity_and_empty_output():
    with pytest.raises(ValidationError):
        WorkspaceDefaultInputDTO(owner_id="42")
    with pytest.raises(ValidationError):
        WorkspaceDefaultOutputDTO(workspace_id="")


def test_existing_server_workspace_keeps_original_read_scope_branch(boundary, monkeypatch):
    from services.admin_data.request_auth import AdminRequestActor

    project = AdminRequestActor.current_user_projection
    monkeypatch.setattr(AdminRequestActor, "current_user_projection", lambda self: {**project(self), "workspace_id": "existing-workspace-1"})
    browser, _state, calls, *_ = boundary
    response = browser.get(PREFIX + "/workflow-runs/" + RUN_ID, headers=READ)
    assert response.status_code == 200 and len(response.json()) == 28
    assert [item[0] for item in calls] == ["workflow-run.read"]


@pytest.mark.parametrize("patch", [{"operation": "workflow-run.create"}, {"request_id": "other-original-id"}, {"status": "in_progress"}, {"result": {"workspace_id": ""}}])
def test_receipt_identity_and_closed_shape_are_not_repaired(boundary, patch):
    _browser, state, calls, _schemas, _operations, data = boundary
    rid = "a7e9e6ec-9900-4e07-b37b-113ba1d6b2ea"
    state["receipt"] = {"status": "committed", "operation": "workspace-default.ensure", "request_id": rid, "result": {"workspace_id": "legacy-text-id"}, **patch}
    with pytest.raises(AdminDataError, match="ADMIN_RESPONSE_INVALID"):
        data.default_receipt(rid, access_token="write-token")
    assert calls == [("receipt", rid, None)]
