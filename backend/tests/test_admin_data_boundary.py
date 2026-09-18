# [Input] Exact Admin DTOs and production consumer classes with injected HTTP/JWKS providers.
# [Output] Deterministic authentication, bounded read recovery and unknown-commit receipts without PG/model calls.
# [Pos] Provider-free tests for the unified Admin consumer boundary.
# [Sync] 2026-09-14: cover auth/receipt security and exact closed Deck conflict feedback without upstream messages.
# [Sync] 2026-09-15: controlled catalog refresh/execute concurrency retains exact contracts and per-request actor headers.
# [Sync] 2026-09-16: cover Better Auth scalar and closed resource/userinfo audience-array access tokens.
# [Sync] 2026-09-17: assert separate user and client_credentials bearer transport.
# [Sync] 2026-09-18: verify public issuer claims with internal DTO, token and JWKS transport URLs.
# [Sync] 2026-09-17: recover one read-only transport failure while writes remain single-dispatch.
"""Invoke the real client/verifier through injected HTTP; no alternate production path."""

from __future__ import annotations

import json
import time
from threading import Event, Lock, Thread

from cryptography.hazmat.primitives.asymmetric import ec
import httpx
import jwt
import pytest
from pydantic import ValidationError

from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError, AdminJWTVerifier, DomainOperation
from services.admin_data.models import (
    AbsentReceiptDTO, BrowserExchangeDTO, BrowserHandleRequestDTO, CommittedReceiptDTO,
    OperationCapabilityDTO, StrictDTO,
)


@pytest.fixture
def config():
    return AdminDataConfig(base_url="https://admin.example", issuer="https://admin.example/api/auth", resource="https://dream.example/api", service_secret="test-service-credential-" + "x" * 32, service_client_id="dream-web")


def principal():
    return {"subject": "ba-opaque-user", "canonical_user_id": "42", "client_id": "dream-browser", "scopes": ["dream:read"], "status": "active"}


def response(data, request_id="request-1"):
    return httpx.Response(200, json={"data": data, "request_id": request_id})


def auth_capabilities(config, operations=()):
    return {"version": "1", "auth": {"issuer": config.issuer, "jwks_uri": config.jwks_uri, "algorithm": "ES256", "resource": config.resource, "clients": {"browser": "dream-browser", "device": "dream-cli"}, "scopes": ["dream:read", "dream:write"], "delegations": []}, "schema_capabilities": [], "operations": [item.capability.model_dump() for item in operations]}


def test_separate_service_identity_user_delegation_and_canonical_mapping(config):
    requests = []
    def handler(request):
        requests.append(request)
        return response(principal())
    client = AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(handler)))
    result = client.principal("admin-user-token", "request-1")
    assert result.subject == "ba-opaque-user" and result.canonical_user_id == "42"
    request = requests[0]
    assert str(request.url) == config.base_url + "/api/internal/dream/v1/principal"
    assert request.headers["authorization"] == "Bearer admin-user-token"
    assert request.headers["x-ink-dream-service-authorization"] == "Bearer fixture.service.access.token"
    assert "x-ink-dream-service" not in request.headers and "x-ink-dream-credential" not in request.headers
    assert request.headers["authorization"] == "Bearer admin-user-token"
    assert "user_id" not in request.url.query.decode()


def test_internal_transport_preserves_public_authority_for_token_data_and_jwks(config, signing_key):
    split = AdminDataConfig(**{
        **config.__dict__, "transport_base_url": "http://127.0.0.1:3000",
    })
    calls = []
    def handler(request):
        calls.append(request)
        if request.url.path == "/api/auth/jwks":
            return httpx.Response(200, json={"keys": [jwk(signing_key)]})
        return response(principal())
    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = AdminDataClient(split, client=http)
    assert client.principal("user.access.token", "request-1").canonical_user_id == "42"
    verifier = AdminJWTVerifier(split, client=http)
    assert verifier.verify(token(split, signing_key)).subject == "ba-opaque-user"
    assert [str(call.url) for call in calls] == [
        "http://127.0.0.1:3000/api/internal/dream/v1/principal",
        "http://127.0.0.1:3000/api/auth/jwks",
    ]
    assert split.issuer == "https://admin.example/api/auth"
    assert split.jwks_uri == "https://admin.example/api/auth/jwks"


@pytest.mark.parametrize("mutation", [lambda d: d.update(canonical_user_id=42), lambda d: d.update(user_id="42"), lambda d: d.update(status="disabled"), lambda d: d.update(canonical_user_id="9223372036854775808")])
def test_reject_orm_extra_fields_and_invalid_principal_dto(config, mutation):
    payload = principal(); mutation(payload)
    client = AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(lambda _: response(payload))))
    with pytest.raises(AdminDataError) as exc:
        client.principal("token", "request-1")
    assert exc.value.code == "ADMIN_RESPONSE_INVALID"


@pytest.mark.parametrize("status", [401, 403, 404, 409, 422, 503, 504])
def test_redacted_error_preserves_status_and_request_id(config, status):
    def handler(_):
        return httpx.Response(status, json={"error": {"code": "DOMAIN_FAILURE", "message": "secret SQL credential body"}, "request_id": "request-1"})
    client = AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(AdminDataError) as exc:
        client.principal("token", "request-1")
    assert exc.value.status_code == status and exc.value.request_id == "request-1"
    assert "credential" not in str(exc.value) and "secret SQL" not in repr(exc.value)


@pytest.mark.parametrize("current_version", [None, 0, 9_007_199_254_740_991])
def test_deck_version_conflict_retains_only_typed_revision_details(config, current_version):
    details = {"current_draft_revision": 9_007_199_254_740_991, "current_version": current_version}
    client = AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(409, json={"error": {"code": "DECK_VERSION_CONFLICT", "message": "private SQL", "details": details}, "request_id": "request-1"}))))
    with pytest.raises(AdminDataError) as exc:
        client.principal("token", "request-1")
    assert exc.value.code == "DECK_VERSION_CONFLICT" and exc.value.status_code == 409
    assert exc.value.details.model_dump() == details
    assert "private SQL" not in repr(exc.value)


@pytest.mark.parametrize("code,details", [
    ("OTHER_FAILURE", {"current_draft_revision": 1, "current_version": None}),
    ("DECK_VERSION_CONFLICT", None),
    ("DECK_VERSION_CONFLICT", {"current_draft_revision": True, "current_version": None}),
    ("DECK_VERSION_CONFLICT", {"current_draft_revision": -1, "current_version": None}),
    ("DECK_VERSION_CONFLICT", {"current_draft_revision": 9_007_199_254_740_992, "current_version": None}),
    ("DECK_VERSION_CONFLICT", {"current_draft_revision": 1, "current_version": None, "sql": "private"}),
])
def test_unknown_or_invalid_error_details_fail_closed(config, code, details):
    client = AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(409, json={"error": {"code": code, "message": "private SQL", "details": details}, "request_id": "request-1"}))))
    with pytest.raises(AdminDataError) as exc:
        client.principal("token", "request-1")
    assert exc.value.code == "ADMIN_RESPONSE_INVALID" and exc.value.details is None


@pytest.mark.parametrize("payload", [{"data": principal(), "request_id": "other"}, {"data": principal(), "request_id": "request-1", "extra": "bad"}])
def test_response_envelope_identity_and_shape(config, payload):
    client = AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))))
    with pytest.raises(AdminDataError) as exc:
        client.principal("token", "request-1")
    assert exc.value.code == "ADMIN_RESPONSE_INVALID"


@pytest.mark.parametrize("failure", ["timeout", "connection", "bad-success"])
def test_browser_exchange_unknown_outcome_never_retries(config, failure):
    calls = []
    def handler(request):
        calls.append(request)
        if failure == "timeout": raise httpx.ReadTimeout("secret transport URL", request=request)
        if failure == "connection": raise httpx.ConnectError("secret credential", request=request)
        return response({"handle": "dbr_" + "a" * 43, "expires_at": "missing timezone"})
    client = AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(handler)))
    body = BrowserExchangeDTO(request_id="request-1", transaction_id="transaction-1", code="private-code", code_verifier="a" * 43, redirect_uri="https://dream.example/auth/callback")
    with pytest.raises(AdminDataError) as exc:
        client.exchange_browser_session(body)
    assert len(calls) == 1 and exc.value.outcome_unknown and exc.value.request_id == "request-1"
    assert "private-code" not in repr(body) and "secret" not in str(exc.value)


def test_read_only_request_recovers_one_stale_transport_with_short_timeout(config):
    calls = []
    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ReadTimeout("stale pooled connection", request=request)
        assert request.extensions["timeout"] == {
            key: 2.0 for key in ("connect", "read", "write", "pool")
        }
        return response(principal())
    client = AdminDataClient(
        config,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert client.principal("admin-user-token", "request-1").canonical_user_id == "42"
    assert len(calls) == 2


def test_read_only_http_rejection_is_not_retried(config):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(503, json={
            "error": {"code": "ADMIN_UNAVAILABLE", "message": "closed"},
            "request_id": "request-1",
        })
    client = AdminDataClient(
        config,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(AdminDataError):
        client.principal("admin-user-token", "request-1")
    assert len(calls) == 1


def test_browser_handle_expiry_and_credentials_stay_server_owned(config):
    client = AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(lambda _: response({"access_token": "private-token", "expires_at": "2026-09-14T20:00:00Z", "principal": principal()}))))
    result = client.resolve_browser_session(BrowserHandleRequestDTO(request_id="request-1", handle="dbr_" + "a" * 43))
    assert result.expires_at.utcoffset().total_seconds() == 0
    assert "private-token" not in repr(result)


class PersistNoteInput(StrictDTO):
    session_id: str
    text: str


class PersistNoteOutput(StrictDTO):
    revision: int


def operation():
    # Technical fixture DTO registered via the real composition API, never deployed.
    return DomainOperation(OperationCapabilityDTO(name="notes.persist", kind="write", user_scope="dream:write", background_scope=None, input_schema_version=1, output_schema_version=1, contract_sha256="a" * 64), PersistNoteInput, PersistNoteOutput)


def test_capability_snapshot_reuses_validated_catalog_and_forced_failure_invalidates(config):
    spec = operation()
    capability_requests = []

    def handler(request):
        request_id = request.headers["x-request-id"]
        capability_requests.append(request_id)
        if request_id == "forced-failure":
            raise httpx.ReadTimeout("private catalog detail", request=request)
        return response(auth_capabilities(config, (spec,)), request_id)

    client = AdminDataClient(
        config,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        operations=(spec,),
    )
    first = client.capabilities_snapshot("first")
    second = client.capabilities_snapshot("second")
    assert first is second
    assert capability_requests == ["first"]

    with pytest.raises(AdminDataError):
        client.capabilities("forced-failure")
    assert not client.capabilities_ready

    recovered = client.capabilities_snapshot("recovered")
    assert recovered is not first
    assert capability_requests == ["first", "forced-failure", "forced-failure", "recovered"]


@pytest.mark.parametrize("refresh_result", ["valid", "missing", "hash", "failure"])
def test_catalog_refresh_does_not_expose_intermediate_empty_advertisement(config, refresh_result):
    spec = operation(); entered, release, started, done = Event(), Event(), Event(), Event()
    refresh_errors, write_errors, results, calls = [], [], [], []

    def handler(request):
        request_id = request.headers["x-request-id"]
        if request.url.path.endswith("/capabilities"):
            value = auth_capabilities(config, (spec,))
            if request_id == "refresh":
                entered.set(); assert release.wait(2), "harness did not release catalog refresh"
                if refresh_result == "failure": raise httpx.ReadTimeout("private catalog detail")
                if refresh_result == "missing": value["operations"] = []
                if refresh_result == "hash": value["operations"][0]["contract_sha256"] = "b" * 64
            return response(value, request_id)
        calls.append(request_id)
        return response({"revision": 3}, request_id)

    http = httpx.Client(transport=httpx.MockTransport(handler)); client = AdminDataClient(config, client=http, operations=(spec,))
    client.capabilities("bootstrap")

    def refresh():
        try: client.capabilities("refresh")
        except BaseException as exc: refresh_errors.append(exc)

    def write():
        started.set()
        try: results.append(client.execute(spec, PersistNoteInput(session_id="note-1", text="text"), "concurrent-write", access_token="actor-token"))
        except BaseException as exc: write_errors.append(exc)
        finally: done.set()

    reader = Thread(target=refresh, name="stage22-catalog-refresh")
    writer = Thread(target=write, name="stage22-catalog-write")
    reader.start()
    try:
        assert entered.wait(2); writer.start(); assert started.wait(2)
        assert not done.wait(0.05), "execute observed the intermediate catalog state"
    finally:
        release.set(); reader.join(2)
        if writer.ident is not None: writer.join(2)
        http.close()
    assert not reader.is_alive() and not writer.is_alive()
    if refresh_result == "valid":
        assert not refresh_errors and not write_errors and results[0].revision == 3 and calls == ["concurrent-write"]
    else:
        assert not calls and not results and len(write_errors) == 1 and isinstance(write_errors[0], AdminDataError)
        assert write_errors[0].request_id == "concurrent-write" and not write_errors[0].outcome_unknown
        assert bool(refresh_errors) is (refresh_result == "failure")


def test_catalog_sync_does_not_serialize_domain_http_or_mix_actor_headers(config):
    spec = operation(); both_entered, release = Event(), Event(); guard = Lock(); calls, failures = [], []

    def handler(request):
        request_id = request.headers["x-request-id"]
        if request.url.path.endswith("/capabilities"): return response(auth_capabilities(config, (spec,)), request_id)
        with guard:
            calls.append((request_id, request.headers["authorization"], json.loads(request.content)))
            if len(calls) == 2: both_entered.set()
        assert release.wait(2), "harness did not release domain HTTP"
        return response({"revision": 3}, request_id)

    http = httpx.Client(transport=httpx.MockTransport(handler)); client = AdminDataClient(config, client=http, operations=(spec,))
    client.capabilities("bootstrap")

    def write(id):
        try: client.execute(spec, PersistNoteInput(session_id=f"note-{id}", text=f"text-{id}"), f"write-{id}", access_token=f"actor-{id}")
        except BaseException as exc: failures.append(exc)

    workers = [Thread(target=write, args=(id,), name=f"stage22-domain-write-{id}") for id in (1, 2)]
    for worker in workers: worker.start()
    try:
        assert both_entered.wait(2), "domain HTTP became globally serialized"
    finally:
        release.set()
        for worker in workers: worker.join(2)
        http.close()
    assert not failures and all(not worker.is_alive() for worker in workers)
    assert sorted(calls) == [(f"write-{id}", f"Bearer actor-{id}", {"request_id": f"write-{id}", "input": {"session_id": f"note-{id}", "text": f"text-{id}"}}) for id in (1, 2)]


def test_multiple_catalog_refreshes_cannot_interleave_advertisement_updates(config):
    spec = operation(); first_entered, second_started, second_entered, release = Event(), Event(), Event(), Event()
    failures, calls = [], []

    def handler(request):
        request_id = request.headers["x-request-id"]; calls.append(request_id)
        value = auth_capabilities(config, (spec,))
        if request_id == "first":
            first_entered.set(); assert release.wait(2), "harness did not release first refresh"
        if request_id == "second":
            second_entered.set(); value["operations"] = []
        return response(value, request_id)

    http = httpx.Client(transport=httpx.MockTransport(handler)); client = AdminDataClient(config, client=http, operations=(spec,))
    client.capabilities("bootstrap")

    def refresh(id):
        if id == "second": second_started.set()
        try: client.capabilities(id)
        except BaseException as exc: failures.append(exc)

    first = Thread(target=refresh, args=("first",), name="stage22-first-refresh")
    second = Thread(target=refresh, args=("second",), name="stage22-second-refresh")
    first.start()
    try:
        assert first_entered.wait(2); second.start(); assert second_started.wait(2)
        assert not second_entered.wait(0.05), "refreshes modified the shared advertisement concurrently"
    finally:
        release.set(); first.join(2)
        if second.ident is not None: second.join(2)
        http.close()
    assert not failures and not first.is_alive() and not second.is_alive()
    assert calls == ["bootstrap", "first", "second"]
    with pytest.raises(AdminDataError) as exc:
        client.execute(spec, PersistNoteInput(session_id="note-1", text="text"), "later-write", access_token="actor-token")
    assert exc.value.code == "ADMIN_CAPABILITY_UNAVAILABLE" and calls == ["bootstrap", "first", "second"]


def test_unadvertised_operation_cannot_dispatch(config):
    calls = []
    spec = operation()
    client = AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(lambda r: calls.append(r))), operations=(spec,))
    with pytest.raises(AdminDataError) as exc:
        client.execute(spec, PersistNoteInput(session_id="note-1", text="text"), "request-1", access_token="token")
    assert not calls and exc.value.code == "ADMIN_CAPABILITY_UNAVAILABLE"


@pytest.mark.parametrize("mutation", [
    lambda item: item.update(contract_sha256="b" * 64),
    lambda item: item.update(output_schema_version=2),
    lambda item: item.update(input_schema_version=True),
])
def test_operation_input_output_contract_drift_blocks_dispatch(config, mutation):
    spec = operation(); calls = []
    advertised = auth_capabilities(config, (spec,))
    mutation(advertised["operations"][0])
    def handler(request):
        calls.append(request)
        return response(advertised, "bootstrap")
    client = AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(handler)), operations=(spec,))
    try:
        client.capabilities("bootstrap")
    except AdminDataError:
        pass
    with pytest.raises(AdminDataError):
        client.execute(spec, PersistNoteInput(session_id="note-1", text="text"), "request-1", access_token="token")
    assert len(calls) == 1


@pytest.mark.parametrize("committed", [True, False])
def test_write_timeout_recovers_only_original_receipt(config, committed):
    calls = []; spec = operation()
    def handler(request):
        calls.append(request)
        if request.url.path.endswith("/capabilities"): return response(auth_capabilities(config, (spec,)), "bootstrap")
        if "/operations/" in request.url.path:
            assert json.loads(request.content) == {"request_id": "request-1", "input": {"session_id": "note-1", "text": "text"}}
            raise httpx.ReadTimeout("unknown commit", request=request)
        data = {"status": "committed" if committed else "absent", "operation": spec.capability.name, "request_id": "request-1"}
        if committed: data["result"] = {"revision": 2}
        return response(data)
    client = AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(handler)), operations=(spec,))
    client.capabilities("bootstrap")
    with pytest.raises(AdminDataError) as exc:
        client.execute(spec, PersistNoteInput(session_id="note-1", text="text"), "request-1", access_token="token")
    assert exc.value.outcome_unknown
    result = client.receipt(spec, "request-1", access_token="token")
    assert isinstance(result, CommittedReceiptDTO if committed else AbsentReceiptDTO)
    assert len(calls) == 3  # bootstrap, one write, explicit receipt; no hidden repeat write


@pytest.mark.parametrize("field,value", [("base_url", "http://remote.example"), ("transport_base_url", "http://remote.example"), ("issuer", "https://other.example/api/auth"), ("service_secret", "short"), ("service_client_id", "client\r\nheader"), ("timeout_seconds", float("nan"))])
def test_server_configuration_fail_closed_and_redacted(config, field, value):
    from dataclasses import asdict
    values = asdict(config); values[field] = value
    with pytest.raises(AdminDataError) as exc:
        AdminDataConfig(**values)
    assert str(exc.value) == "ADMIN_CONFIGURATION_INVALID (503)"
    if isinstance(value, str): assert value not in str(exc.value)
    assert config.service_secret not in repr(config)


@pytest.fixture
def signing_key():
    return ec.generate_private_key(ec.SECP256R1())


def token(config, key, *, kid="key-1", claims=None, headers=None):
    now = int(time.time())
    payload = {"sub": "ba-opaque-user", "iss": config.issuer, "aud": config.resource, "exp": now + 240, "iat": now, "jti": "jti-1", "client_id": "dream-browser", "scope": "dream:read dream:write"}
    if claims is not None: payload.update(claims)
    return jwt.encode(payload, key, algorithm="ES256", headers={"kid": kid, "typ": "at+jwt", **(headers or {})})


def jwk(key, kid="key-1"):
    value = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(key.public_key()))
    return {**value, "kid": kid, "use": "sig", "alg": "ES256"}


def verifier(config, keys):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"keys": keys})
    return AdminJWTVerifier(config, client=httpx.Client(transport=httpx.MockTransport(handler))), calls


def test_signed_token_subject_remains_opaque_and_jwks_cached(config, signing_key):
    check, calls = verifier(config, [jwk(signing_key)])
    signed = token(config, signing_key)
    for _ in range(3):
        result = check.verify(signed, required_scopes=frozenset({"dream:read"}))
        assert result.subject == "ba-opaque-user" and not hasattr(result, "user_id")
    assert len(calls) == 1 and str(calls[0].url) == config.jwks_uri


@pytest.mark.parametrize("audience", [
    pytest.param("scalar", id="scalar-dream-resource"),
    pytest.param("better-auth-array", id="better-auth-resource-and-userinfo"),
])
def test_accepts_admin_resource_audience_contract(config, signing_key, audience):
    value = config.resource if audience == "scalar" else [config.resource, config.issuer + "/oauth2/userinfo"]
    check, _ = verifier(config, [jwk(signing_key)])
    assert check.verify(token(config, signing_key, claims={"aud": value})).subject == "ba-opaque-user"


@pytest.mark.parametrize("audience", [
    pytest.param(["https://unrelated.example/api", "https://dream.example/api"], id="arbitrary-extra"),
    pytest.param(["https://admin.example/api/auth/oauth2/userinfo"], id="userinfo-only"),
    pytest.param(["https://dream.example/api", "https://dream.example/api"], id="duplicate"),
    pytest.param(["https://dream.example/api", ""], id="empty-member"),
    pytest.param(["https://dream.example/api", 7], id="non-string-member"),
    pytest.param([], id="empty-array"),
])
def test_rejects_non_resource_or_malformed_audience_array(config, signing_key, audience):
    check, _ = verifier(config, [jwk(signing_key)])
    with pytest.raises(AdminDataError) as exc:
        check.verify(token(config, signing_key, claims={"aud": audience}))
    assert exc.value.code == "INVALID_TOKEN_RESOURCE" and exc.value.status_code == 403


@pytest.mark.parametrize("claims,status", [({"iss": "https://google.example"}, 401), ({"aud": "other-resource"}, 403), ({"scope": "product:read"}, 403), ({"exp": 1}, 401), ({"iat": int(time.time()) + 600}, 401), ({"sub": ""}, 401), ({"jti": ""}, 401), ({"client_id": ""}, 401), ({"exp": int(time.time()) + 1000}, 401), ({"iat": True}, 401), ({"scope": ["dream:read"]}, 401)])
def test_jwt_field_scope_time_and_resource_checks(config, signing_key, claims, status):
    check, _ = verifier(config, [jwk(signing_key)])
    with pytest.raises(AdminDataError) as exc:
        check.verify(token(config, signing_key, claims=claims), required_scopes=frozenset({"dream:read"}))
    assert exc.value.status_code == status


@pytest.mark.parametrize("headers", [{"typ": "JWT"}, {"typ": "id+jwt"}, {"crit": ["unknown"]}])
def test_reject_wrong_token_type_before_network(config, signing_key, headers):
    check, calls = verifier(config, [jwk(signing_key)])
    with pytest.raises(AdminDataError): check.verify(token(config, signing_key, headers=headers))
    assert not calls


def test_reject_old_hs256_authority_before_jwks(config):
    check, calls = verifier(config, [])
    old = jwt.encode({"sub": "42", "exp": int(time.time()) + 3600}, "old-authority", algorithm="HS256")
    with pytest.raises(AdminDataError) as exc: check.verify(old)
    assert exc.value.status_code == 401 and not calls


def test_unknown_kid_refresh_is_bounded_and_rotation_recovers(config, signing_key):
    second = ec.generate_private_key(ec.SECP256R1()); now = [0.0]; calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"keys": [jwk(signing_key)] + ([jwk(second, "key-2")] if len(calls) > 1 else [])})
    check = AdminJWTVerifier(config, client=httpx.Client(transport=httpx.MockTransport(handler)), monotonic=lambda: now[0])
    check.verify(token(config, signing_key))
    for n in range(5):
        with pytest.raises(AdminDataError): check.verify(token(config, second, kid=f"attacker-{n}"))
    assert len(calls) == 1
    now[0] += config.jwks_refresh_min_interval_seconds
    assert check.verify(token(config, second, kid="key-2")).subject == "ba-opaque-user"
    assert len(calls) == 2


def test_jwks_unavailable_is_dependency_failure_without_token_fallback(config, signing_key):
    calls = []
    def handler(request):
        calls.append(request); raise httpx.ReadTimeout("secret URL", request=request)
    check = AdminJWTVerifier(config, client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(AdminDataError) as exc: check.verify(token(config, signing_key))
    assert exc.value.status_code == 503 and len(calls) == 1


def test_wrong_signature_rejected_with_cached_key(config, signing_key):
    check, calls = verifier(config, [jwk(signing_key)])
    other = ec.generate_private_key(ec.SECP256R1())
    with pytest.raises(AdminDataError) as exc: check.verify(token(config, other))
    assert exc.value.status_code == 401 and len(calls) == 1


@pytest.mark.parametrize("missing", ["sub", "iss", "aud", "exp", "iat", "jti", "client_id", "scope"])
def test_missing_required_claim_rejected(config, signing_key, missing):
    check, _ = verifier(config, [jwk(signing_key)])
    payload = jwt.decode(token(config, signing_key), options={"verify_signature": False})
    del payload[missing]
    signed = jwt.encode(payload, signing_key, algorithm="ES256", headers={"kid": "key-1", "typ": "at+jwt"})
    with pytest.raises(AdminDataError) as exc: check.verify(signed)
    assert exc.value.status_code == 401


def test_service_request_header_injection_rejected_before_http(config):
    calls = []
    client = AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(lambda r: calls.append(r))))
    with pytest.raises(ValidationError): client.principal("token", "request\r\nheader")
    with pytest.raises(AdminDataError): client.principal("token\r\nheader", "request-1")
    assert not calls


def test_response_size_bound_marks_write_unknown(config):
    from dataclasses import replace
    client = AdminDataClient(replace(config, max_response_bytes=32), client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=b"x" * 100))))
    with pytest.raises(AdminDataError) as exc:
        client.revoke_browser_session(BrowserHandleRequestDTO(request_id="request-1", handle="dbr_" + "a" * 43))
    assert exc.value.outcome_unknown
