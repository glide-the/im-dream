# [Input] Actual public Deck version routes, Admin authentication/DTO transport and static synthetic outputs.
# [Output] Five-operation, four-capability, CAS/error and exact raw-snapshot projection evidence.
# [Pos] Provider-free public contract harness; no copied version algorithm, PG, model or user service.
# [Sync] 2026-09-15: fence Dream PG while validating content version reads/commit through Admin.
from __future__ import annotations

from copy import deepcopy
import json
import math
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from routers.deck_versions import router
from services.admin_data import AdminDataClient, AdminDataConfig
from services.admin_data.deck_version_data import DECK_VERSION_OPERATIONS, DECK_VERSION_SCHEMA_REQUIREMENTS
from services.admin_data.deck_version_models import DeckVersionDetailDTO
from services.admin_data.request_auth import AdminRequestAuth
from tests.test_admin_request_auth import Verifier


def state():
    return {"deck_id": "deck-1", "draft_revision": 2, "latest_version": None,
        "published_draft_revision": 0, "dirty": True, "status": "unpublished", "next_version": 1}


def summary():
    return {"version": 1, "base_version": None, "source_draft_revision": 2, "description": None,
        "content_hash": "sha256:" + "a" * 64, "created_by": "42", "created_at": "2026-09-15T01:02:03.123456Z",
        "runtime_plugin_version": None}


def snapshot():
    return {"schema_version": "deck-content/v1", "deck": {"id": "deck-1", "name": "写作", "name_zh": None,
        "name_en": None, "description": None, "description_zh": None, "description_en": None,
        "icon": None, "color": None, "enabled": None, "order_index": None}, "agent_type": "chat",
        "agents": [{"id": "voice-1", "name": "Writer", "name_zh": None, "name_en": None, "system_prompt": "Write",
            "icon": None, "color": None, "enabled": True, "order_index": None,
            "memory_workspace_config": {"float": 1.0, "negative_zero": -0.0, "large": 9_007_199_254_740_993}}],
        "claude_plugins": [], "runtime_binding": None}


def boundary(monkeypatch):
    import database
    monkeypatch.setattr(database, "get_db", lambda: pytest.fail("Public Deck version routes must not use Dream PG"))
    config = AdminDataConfig(base_url="https://admin.example", issuer="https://admin.example/api/auth",
        resource="https://dream.example/api", service_client_id="dream-service", service_secret="s" * 32)
    calls = []
    outputs = {
        "deck-content.state": state(),
        "deck-content.preview": {**state(), "target_version": 1, "changes": [{"scope": "deck", "change_type": "modified", "label": "写作", "fields": ["name"]}], "impact": ["新建Thread可选择"]},
        "deck-content.commit": {"deck_id": "deck-1", "version": summary(), "state": {**state(), "latest_version": 1, "published_draft_revision": 2, "dirty": False, "status": "published", "next_version": 2}},
        "deck-content.history": {"deck_id": "deck-1", "current": state(), "versions": [summary()]},
        "deck-content.detail": {**summary(), "deck_id": "deck-1", "snapshot_json": json.dumps(snapshot(), ensure_ascii=False)},
    }
    schemas = [item.model_dump() for item in DECK_VERSION_SCHEMA_REQUIREMENTS]
    advertised = [item.capability.model_dump() for item in DECK_VERSION_OPERATIONS]
    refresh = {"fail_next": False}
    def handler(request):
        request_id = request.headers["x-request-id"]
        UUID(request_id)
        if request.url.path.endswith("/capabilities"):
            if refresh["fail_next"]:
                refresh["fail_next"] = False
                raise httpx.ConnectError("synthetic private connect error")
            value = {"version": "1", "auth": {"issuer": config.issuer, "jwks_uri": config.jwks_uri, "resource": config.resource,
                "algorithm": "ES256", "clients": {"browser": "dream-browser", "device": "dream-device"},
                "scopes": ["dream:read", "dream:write"], "delegations": []}, "schema_capabilities": schemas, "operations": advertised}
        elif request.url.path.endswith("/principal"):
            value = {"subject": "opaque-ba-subject", "canonical_user_id": "42", "client_id": "dream-browser",
                "scopes": ["dream:read"] if request.headers["authorization"] == "Bearer read-token" else ["dream:read", "dream:write"], "status": "active"}
        else:
            name = request.url.path.rsplit("/", 1)[-1]
            body = json.loads(request.content)
            assert set(body) == {"request_id", "input"} and body["request_id"] == request_id
            assert body["input"]["deck_id"] == "deck-1" and not {"user_id", "actor_id"} & body["input"].keys()
            assert request.headers["authorization"] in {"Bearer read-token", "Bearer write-token"}
            assert request.headers["x-ink-dream-credential"] == "s" * 32 and "cookie" not in request.headers
            calls.append((name, body["input"], request_id))
            value = outputs[name]
            if isinstance(value, Exception):
                raise value
            if isinstance(value, tuple):
                code, details = value[1:]
                error = {"code": code, "message": "synthetic private failure"}
                if details is not None:
                    error["details"] = details
                return httpx.Response(value[0], json={"request_id": request_id, "error": error})
        return httpx.Response(200, json={"request_id": request_id, "data": value})
    client = AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(handler)), operations=DECK_VERSION_OPERATIONS)
    app = FastAPI()
    app.state.admin_request_auth = AdminRequestAuth(config, client=client, verifier=Verifier())
    app.include_router(router)
    return TestClient(app), calls, outputs, schemas, advertised, refresh


HEADERS = {"authorization": "Bearer write-token"}
CAS = {"expected_draft_revision": 2, "expected_base_version": None}


def test_five_public_operations_keep_original_response_and_exact_cas(monkeypatch):
    client, calls, _, _, _, _ = boundary(monkeypatch)
    with client:
        assert client.get("/api/decks/deck-1/version-state", headers=HEADERS).json() == state()
        preview = client.post("/api/decks/deck-1/versions/preview", headers=HEADERS, json=CAS)
        assert preview.status_code == 200 and preview.json()["changes"][0]["fields"] == ["name"]
        committed = client.post("/api/decks/deck-1/versions", headers=HEADERS, json={**CAS, "description": "版本😀"})
        assert committed.status_code == 200 and committed.json()["version"]["created_by"] == 42
        assert committed.json()["version"]["created_at"] == "2026-09-15T01:02:03.123456Z"
        history = client.get("/api/decks/deck-1/versions?limit=100", headers=HEADERS)
        assert history.status_code == 200 and history.json()["versions"][0]["created_by"] == 42
        detail = client.get("/api/decks/deck-1/versions/1", headers=HEADERS)
        assert detail.status_code == 200 and "snapshot_json" not in detail.json()
        assert "version" in detail.json() and detail.json()["snapshot"]["deck"]["name"] == "写作"
    assert [name for name, *_ in calls] == [item.capability.name for item in DECK_VERSION_OPERATIONS]
    assert calls[1][1] == {"deck_id": "deck-1", **CAS}
    assert calls[2][1] == {"deck_id": "deck-1", **CAS, "description": "版本😀"}
    assert calls[3][1] == {"deck_id": "deck-1", "limit": 100}


def test_detail_raw_snapshot_keeps_python_numeric_types_and_negative_zero(monkeypatch):
    client, _, outputs, *_ = boundary(monkeypatch)
    raw = outputs["deck-content.detail"]["snapshot_json"]
    parsed = DeckVersionDetailDTO.model_validate(outputs["deck-content.detail"])
    assert parsed.snapshot_json == raw
    with client:
        response = client.get("/api/decks/deck-1/versions/1", headers=HEADERS)
    numbers = response.json()["snapshot"]["agents"][0]["memory_workspace_config"]
    assert type(numbers["float"]) is float and numbers["float"] == 1.0
    assert type(numbers["negative_zero"]) is float and math.copysign(1, numbers["negative_zero"]) == -1
    assert type(numbers["large"]) is int and numbers["large"] == 9_007_199_254_740_993


@pytest.mark.parametrize("index", range(4))
@pytest.mark.parametrize("damage", ["missing", "hash", "version", "duplicate"])
def test_each_required_physical_capability_fails_before_domain_io(monkeypatch, index, damage):
    client, calls, _, schemas, *_ = boundary(monkeypatch)
    if damage == "missing":
        schemas.pop(index)
    elif damage == "duplicate":
        schemas.append(deepcopy(schemas[index]))
    else:
        schemas[index]["contract_sha256" if damage == "hash" else "version"] = "b" * 64 if damage == "hash" else 2
    with client:
        response = client.get("/api/decks/deck-1/version-state", headers=HEADERS)
    assert response.status_code == 503 and not calls


def test_operation_hash_mismatch_fails_before_domain_io(monkeypatch):
    client, calls, _, _, advertised, _ = boundary(monkeypatch)
    advertised[0]["contract_sha256"] = "b" * 64
    with client:
        assert client.get("/api/decks/deck-1/version-state", headers=HEADERS).status_code == 503
    assert not calls


@pytest.mark.parametrize("body", [{"expected_draft_revision": True}, {"expected_draft_revision": "2"}, {"expected_draft_revision": 0},
    {"expected_draft_revision": 9_007_199_254_740_992}, {"expected_base_version": False}, {"description": "😀" * 201}, {"actor_id": "43"}])
def test_invalid_public_commit_is_rejected_without_domain_write(monkeypatch, body):
    client, calls, *_ = boundary(monkeypatch)
    with client:
        response = client.post("/api/decks/deck-1/versions", headers=HEADERS, json={**CAS, **body})
    assert response.status_code == 422 and not calls


def test_conflict_preserves_closed_revisions_without_upstream_message(monkeypatch):
    client, calls, outputs, *_ = boundary(monkeypatch)
    outputs["deck-content.commit"] = (409, "DECK_VERSION_CONFLICT", {"current_draft_revision": 3, "current_version": None})
    with client:
        response = client.post("/api/decks/deck-1/versions", headers=HEADERS, json=CAS)
    assert response.status_code == 409
    assert response.json()["current_draft_revision"] == 3 and response.json()["current_version"] is None
    assert response.json()["request_id"] == calls[0][2] and not response.json()["outcome_unknown"]
    assert "synthetic private" not in response.text


def test_unknown_commit_retains_original_uuid_and_never_retries(monkeypatch):
    client, calls, outputs, *_ = boundary(monkeypatch)
    outputs["deck-content.commit"] = httpx.ReadTimeout("synthetic private credential")
    with client:
        response = client.post("/api/decks/deck-1/versions", headers=HEADERS, json=CAS)
    assert response.status_code == 504 and response.json()["outcome_unknown"] is True
    assert len(calls) == 1 and response.json()["request_id"] == calls[0][2]
    assert "synthetic private" not in response.text


@pytest.mark.parametrize("operation,damage", [("deck-content.state", "deck_id"), ("deck-content.commit", "state"),
    ("deck-content.history", "current"), ("deck-content.detail", "version"), ("deck-content.detail", "snapshot")])
def test_response_entity_mismatch_fails_closed(monkeypatch, operation, damage):
    client, _, outputs, *_ = boundary(monkeypatch)
    if damage in {"state", "current"}:
        outputs[operation][damage]["deck_id"] = "other"
    elif damage == "snapshot":
        content = snapshot(); content["deck"]["id"] = "other"
        outputs[operation]["snapshot_json"] = json.dumps(content)
    else:
        outputs[operation][damage] = 2 if damage == "version" else "other"
    with client:
        if operation == "deck-content.commit":
            response = client.post("/api/decks/deck-1/versions", headers=HEADERS, json=CAS)
        else:
            suffix = {"deck-content.state": "version-state", "deck-content.history": "versions", "deck-content.detail": "versions/1"}[operation]
            response = client.get("/api/decks/deck-1/" + suffix, headers=HEADERS)
    assert response.status_code == 503 and response.json()["outcome_unknown"] is (operation == "deck-content.commit")


@pytest.mark.parametrize("damage", ["extra", "missing", "invalid_json", "nonfinite", "overflow", "bool_integer"])
def test_raw_snapshot_closed_shape_validation_does_not_rewrite(damage):
    content = snapshot()
    if damage == "extra":
        content["agents"][0]["unknown"] = "private"
    elif damage == "missing":
        del content["deck"]["enabled"]
    elif damage == "nonfinite":
        content["agents"][0]["memory_workspace_config"] = {"overflow": float("inf")}
    elif damage == "bool_integer":
        content["deck"]["order_index"] = True
    raw = "[] trailing" if damage == "invalid_json" else json.dumps(content)
    if damage == "overflow":
        raw = raw.replace('"float": 1.0', '"float": 1e400')
    with pytest.raises(ValidationError):
        DeckVersionDetailDTO.model_validate({**summary(), "deck_id": "deck-1", "snapshot_json": raw})


def test_capability_refresh_failure_can_recover_on_next_authenticated_request(monkeypatch):
    client, calls, _, _, _, refresh = boundary(monkeypatch)
    with client:
        assert client.get("/api/decks/deck-1/version-state", headers=HEADERS).status_code == 200
        refresh["fail_next"] = True
        assert client.get("/api/decks/deck-1/version-state", headers=HEADERS).status_code == 503
        assert client.get("/api/decks/deck-1/version-state", headers=HEADERS).status_code == 200
    assert len(calls) == 2


def test_public_scope_and_cookie_query_rules_remain_shared(monkeypatch):
    client, calls, *_ = boundary(monkeypatch)
    with client:
        assert client.get("/api/decks/deck-1/version-state", headers={"authorization": "Bearer read-token"}).status_code == 200
        assert client.post("/api/decks/deck-1/versions", headers={"authorization": "Bearer read-token"}, json=CAS).status_code == 403
        client.cookies.set("access_token", "read-token")
        assert client.get("/api/decks/deck-1/version-state?token=read-token").status_code == 401
    assert len(calls) == 1
