# [Input] Production special-route consumers/keeper and injected HTTP, clock and request identities.
# [Output] Purpose isolation, published readiness and unknown-renewal recovery without PG/models.
# [Pos] Provider-free Runtime authorization contracts; no alternate Agent or authentication path.
# [Sync] 2026-09-16: verify the Gateway turn owner projects and closes one opaque grant.
# [Sync] 2026-09-14: verify all four actual special-route DTOs and pre-expiry server renewal.

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json

import httpx
import pytest
from pydantic import ValidationError

from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.delegation import (
    AdminDelegationCreator, AdminRuntimeClient, DELEGATION_CAPABILITIES,
    DelegationCreateInputDTO, RUNTIME_SCHEMA_REQUIREMENTS, RuntimeGrant, RuntimeHttpConfig,
)
from services.admin_data.delegation_keeper import RuntimeGrantKeeper
from services.admin_data.gateway_runtime import AdminGatewayRuntime

NOW = datetime(2026, 9, 14, 4, tzinfo=timezone.utc)
TOKEN = "idg_" + "a" * 43


def grant():
    return RuntimeGrant(TOKEN, "gateway-cli", "thread-1", "run-1", None,
        ("messages:create", "models:list"), NOW + timedelta(seconds=100), NOW + timedelta(hours=2))


def wire(value, *, expires=None):
    return {"purpose": value.purpose, "thread_id": value.thread_id, "run_id": value.run_id,
        "editor_session_id": value.editor_session_id, "scopes": list(value.scopes),
        "expires_at": (expires or value.expires_at).isoformat(),
        "maximum_expires_at": value.maximum_expires_at.isoformat()}


def reply(request, data):
    return httpx.Response(200, json={"data": data, "request_id": request.headers["x-request-id"]})


def capabilities(config):
    return {"version": "1", "auth": {"issuer": config.issuer, "jwks_uri": config.jwks_uri,
        "algorithm": "ES256", "resource": config.resource, "clients": {"browser": "browser", "device": "device"},
        "scopes": ["dream:read", "dream:write"], "delegations": [x.model_dump() for x in DELEGATION_CAPABILITIES]},
        "schema_capabilities": [x.model_dump() for x in RUNTIME_SCHEMA_REQUIREMENTS], "operations": []}


@pytest.fixture
def config():
    return AdminDataConfig(base_url="https://admin.example", issuer="https://admin.example/api/auth",
        resource="https://dream.example/api", service_secret="s" * 32, service_client_id="dream-server")


@pytest.mark.parametrize("purpose,scopes,session", [
    ("server-persistence", ["dream:read", "dream:write"], None),
    ("gateway-cli", ["messages:create", "models:list"], None),
    ("editor-stdio", ["editor:read", "editor:write"], "real-session-1"),
])
def test_create_uses_actual_special_route_and_exact_purpose(config, purpose, scopes, session):
    requested = DelegationCreateInputDTO(purpose=purpose, thread_id="thread-1", run_id=None,
        editor_session_id=session, scopes=scopes)
    calls = []
    def handler(request):
        calls.append(request)
        assert request.headers["x-ink-dream-credential"] == config.service_secret
        if request.url.path.endswith("/capabilities"):
            return reply(request, capabilities(config))
        assert request.url.path == "/api/internal/dream/v1/runtime-delegations"
        assert request.headers["authorization"] == "Bearer user-oauth"
        assert json.loads(request.content) == {"request_id": "create-1", "input": requested.model_dump()}
        return reply(request, {**requested.model_dump(), "token": TOKEN,
            "expires_at": (NOW + timedelta(minutes=5)).isoformat(),
            "maximum_expires_at": (NOW + timedelta(hours=2)).isoformat()})
    client = AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(handler)))
    result = AdminDelegationCreator(client, clock=lambda: NOW).create(requested, access_token="user-oauth", request_id="create-1")
    assert len(calls) == 2 and result.scopes == tuple(scopes) and result.editor_session_id == session
    assert TOKEN not in repr(result)


@pytest.mark.parametrize("mutation", [
    lambda d: d["auth"].update(delegations=[]),
    lambda d: d["auth"]["delegations"][0].update(path="https://other.example/steal"),
    lambda d: d["auth"]["delegations"][1].update(contract_sha256="b" * 64),
    lambda d: d["auth"]["delegations"].append(d["auth"]["delegations"][0]),
    lambda d: d.update(schema_capabilities=d["schema_capabilities"][:-1]),
    lambda d: d["schema_capabilities"][1].update(contract_sha256="b" * 64),
])
def test_unpublished_or_changed_runtime_contract_refuses_before_create(config, mutation):
    data = capabilities(config); mutation(data); calls = []
    def handler(request):
        calls.append(request); return reply(request, data)
    client = AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(handler)))
    requested = DelegationCreateInputDTO(purpose="gateway-cli", thread_id="thread-1", run_id=None,
        editor_session_id=None, scopes=["messages:create"])
    with pytest.raises(AdminDataError) as error:
        AdminDelegationCreator(client, clock=lambda: NOW).create(requested, access_token="oauth", request_id="create-1")
    assert error.value.code == "ADMIN_CAPABILITY_UNAVAILABLE" and len(calls) == 1


@pytest.mark.parametrize("purpose,scopes,session", [
    ("server-persistence", ["messages:create"], None),
    ("gateway-cli", ["dream:write"], None),
    ("editor-stdio", ["editor:write"], None),
    ("gateway-cli", ["messages:create"], "other-session"),
    ("gateway-cli", ["messages:create", "messages:create"], None),
])
def test_purpose_scope_or_editor_binding_cannot_expand(purpose, scopes, session):
    with pytest.raises(ValidationError):
        DelegationCreateInputDTO(purpose=purpose, thread_id="thread-1", run_id=None,
            editor_session_id=session, scopes=scopes)


def test_public_renew_has_only_opaque_grant_even_with_client_defaults():
    current = grant(); calls = []
    def handler(request):
        calls.append(request)
        assert request.url.path == "/api/runtime-delegations/renew"
        assert request.headers["authorization"] == "Bearer " + TOKEN
        assert not any(key in request.headers for key in ("cookie", "x-api-key", "x-ink-dream-service", "x-ink-dream-credential"))
        assert json.loads(request.content) == {"request_id": "renew-1"}
        return reply(request, wire(current, expires=NOW + timedelta(seconds=200)))
    http = httpx.Client(transport=httpx.MockTransport(handler), headers={"x-api-key": "global-key"},
        cookies={"admin-session": "ambient-cookie"}, auth=("ambient", "password"))
    client = AdminRuntimeClient(RuntimeHttpConfig("https://admin.example"), client=http)
    renewed = client.renew(current, "renew-1")
    assert renewed.token == TOKEN and renewed.maximum_expires_at == current.maximum_expires_at and len(calls) == 1


@pytest.mark.parametrize("field,value", [
    ("purpose", "server-persistence"), ("thread_id", "another-thread"),
    ("run_id", None), ("editor_session_id", "other-session"), ("scopes", ["messages:create", "messages:count_tokens"]),
    ("maximum_expires_at", (NOW + timedelta(hours=3)).isoformat()),
    ("expires_at", (NOW + timedelta(seconds=99)).isoformat()),
])
def test_renewed_authority_and_maximum_are_immutable(field, value):
    current = grant(); data = wire(current, expires=NOW + timedelta(seconds=200)); data[field] = value
    client = AdminRuntimeClient(RuntimeHttpConfig("https://admin.example"),
        client=httpx.Client(transport=httpx.MockTransport(lambda request: reply(request, data))))
    with pytest.raises(AdminDataError) as error:
        client.renew(current, "renew-1")
    assert error.value.code == "ADMIN_RESPONSE_INVALID" and error.value.outcome_unknown


def test_unknown_renewal_recovers_original_receipt_after_expiry_without_second_post():
    current = grant(); now = [NOW]; paths = []; receipt_ids = []
    def handler(request):
        paths.append(request.url.path)
        if request.method == "POST":
            raise httpx.ReadTimeout("lost response after commit", request=request)
        assert dict(request.url.params) == {"operation": "runtime-delegation.renew"}
        receipt_ids.append(request.headers["x-request-id"])
        if len(receipt_ids) == 1:
            return reply(request, {"status": "absent", "operation": "runtime-delegation.renew", "request_id": "renew-original"})
        return reply(request, {"status": "committed", "operation": "runtime-delegation.renew", "request_id": "renew-original",
            "result": wire(current, expires=NOW + timedelta(seconds=300))})
    client = AdminRuntimeClient(RuntimeHttpConfig("https://admin.example"), client=httpx.Client(transport=httpx.MockTransport(handler)))
    keeper = RuntimeGrantKeeper(current, client, clock=lambda: now[0], request_id_factory=lambda: "renew-original")
    keeper.tick(); assert paths == []
    now[0] += timedelta(seconds=60); keeper.tick()
    assert keeper.diagnostics().pending_request_id == "renew-original"
    keeper.tick(); assert keeper.diagnostics().pending_request_id == "renew-original"
    now[0] = NOW + timedelta(seconds=120)
    with pytest.raises(AdminDataError): keeper.current("gateway-cli")
    keeper.tick()
    assert keeper.current("gateway-cli").expires_at == NOW + timedelta(seconds=300)
    assert keeper.diagnostics().pending_request_id is None
    assert sum(path.endswith("/renew") for path in paths) == 1 and receipt_ids == ["renew-original", "renew-original"]


def test_revoke_and_receipt_use_original_action_and_no_other_authority():
    calls = []
    def handler(request):
        calls.append(request)
        assert request.headers["authorization"] == "Bearer " + TOKEN
        if request.method == "POST": return reply(request, {"revoked": True})
        return reply(request, {"status": "committed", "operation": "runtime-delegation.revoke", "request_id": "revoke-1", "result": {"revoked": True}})
    client = AdminRuntimeClient(RuntimeHttpConfig("https://admin.example"), client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert client.revoke(grant(), "revoke-1").revoked
    assert client.receipt(grant(), "runtime-delegation.revoke", "revoke-1").result.revoked
    assert [x.url.path for x in calls] == ["/api/runtime-delegations/revoke", "/api/runtime-delegations/receipts/revoke-1"]
    assert all("x-ink-dream-credential" not in x.headers and "cookie" not in x.headers for x in calls)


def test_receipt_mismatch_cannot_be_adopted():
    data = {"status": "committed", "operation": "runtime-delegation.revoke", "request_id": "renew-1", "result": {"revoked": True}}
    client = AdminRuntimeClient(RuntimeHttpConfig("https://admin.example"),
        client=httpx.Client(transport=httpx.MockTransport(lambda request: reply(request, data))))
    with pytest.raises(AdminDataError): client.receipt(grant(), "runtime-delegation.renew", "renew-1")


def test_maximum_expiry_or_closed_keeper_cannot_renew_or_project_other_purpose():
    current = replace(grant(), maximum_expires_at=grant().expires_at)
    calls = []
    client = AdminRuntimeClient(RuntimeHttpConfig("https://admin.example"),
        client=httpx.Client(transport=httpx.MockTransport(lambda request: calls.append(request))))
    now = [NOW]; keeper = RuntimeGrantKeeper(current, client, clock=lambda: now[0])
    now[0] += timedelta(seconds=60); keeper.tick(); assert calls == []
    with pytest.raises(AdminDataError) as error: keeper.current("server-persistence")
    assert error.value.status_code == 403
    now[0] += timedelta(seconds=41); keeper.tick()
    with pytest.raises(AdminDataError): keeper.current("gateway-cli")
    keeper.close(); keeper.tick(); assert calls == [] and keeper.diagnostics().stopped


def test_gateway_runtime_owns_one_opaque_grant_and_closes_its_http_client():
    class Client:
        def __init__(self):
            self.closed = 0

        def close(self):
            self.closed += 1

    now = datetime.now(timezone.utc)
    current = RuntimeGrant(
        TOKEN,
        "gateway-cli",
        "thread-1",
        "run-1",
        None,
        ("messages:create", "messages:count_tokens", "models:list"),
        now + timedelta(minutes=5),
        now + timedelta(hours=2),
    )
    client = Client()
    runtime = AdminGatewayRuntime(current, client)  # type: ignore[arg-type]
    assert runtime.access_token() == TOKEN
    assert TOKEN not in repr(runtime)
    runtime.start()
    runtime.close()
    runtime.close()
    assert client.closed == 1
    with pytest.raises(AdminDataError, match="DELEGATION_EXPIRED"):
        runtime.access_token()
