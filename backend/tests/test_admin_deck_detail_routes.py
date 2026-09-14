# [Input] Actual Deck detail route/Auth/DTO with controlled Admin aggregates and original Memory values.
# [Output] Original fields/numbers/time and closed malformed/entity/permission failure evidence.
# [Pos] Provider-free public Deck read harness; no database or copied policy implementation.
# [Sync] 2026-09-15: fence Dream reads and preserve raw legacy Memory projection.
from __future__ import annotations

import copy
import json
import math
from uuid import UUID
import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers.voices import router
from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.deck_detail_data import READ_DECK_DETAIL
from services.admin_data.deck_version_data import DECK_VERSION_SCHEMA_REQUIREMENTS
from services.admin_data.request_auth import AdminRequestAuth
from tests.test_admin_request_auth import Verifier

HEADERS = {"authorization": "Bearer read-token"}


def aggregate():
    return {"id": "deck-1", "name": "中文", "name_zh": None, "name_en": "", "description": "",
        "description_zh": None, "description_en": None, "icon": None, "color": "",
        "owner_id": "42", "is_system": False, "parent_id": None, "enabled": True,
        "has_local_changes": False, "order_index": 0, "created_at": "2026-09-15T01:02:03.123456+08:00",
        "updated_at": None, "published": False, "author_name": None, "install_count": 0,
        "draft_revision": 1, "latest_version": 0, "published_draft_revision": 0,
        "agent_type": "chat", "agent_type_revision": 0, "deck_plugin_id": None,
        "deck_plugin_version": None, "can_publish": True, "publish_block_reason": None,
        "deck_version_capability": True, "deck_version": None, "deck_version_dirty": True,
        "deck_version_status": "unpublished", "next_deck_version": 1,
        "voices": [{"id": "voice-1", "deck_id": "deck-1", "name": "角色", "name_zh": None,
            "name_en": "", "system_prompt": "正文", "icon": None, "color": "",
            "owner_id": "9223372036854775807", "is_system": False, "parent_id": None,
            "enabled": False, "has_local_changes": None, "order_index": 0,
            "created_at": "2026-09-15T01:02:03.123456Z", "updated_at": None, "thread_id": None,
            "memory_workspace_config_json": '{"float":1.0,"zero":-0.0,"big":9007199254740993}'}]}


@pytest.fixture
def boundary(monkeypatch):
    import database
    monkeypatch.setattr(database, "get_db", lambda: pytest.fail("Public detail must not read Dream PG"))
    monkeypatch.setattr(database, "get_deck_with_voices", lambda *_a: pytest.fail("Public detail must use Admin"))
    config = AdminDataConfig(base_url="https://admin.example", issuer="https://admin.example/api/auth",
        resource="https://dream.example/api", service_client_id="dream-service", service_secret="s"*32)
    outputs = {"deck": aggregate()}; schemas = [x.model_dump() for x in DECK_VERSION_SCHEMA_REQUIREMENTS]
    operations = [READ_DECK_DETAIL.capability.model_dump()]; calls = []

    class ReadVerifier(Verifier):
        def verify(self, token, *, required_scopes):
            if token.startswith("idg_"): raise AdminDataError("INVALID_ACCESS_TOKEN", 401)
            return super().verify(token, required_scopes=required_scopes)

    def handler(request):
        rid = request.headers["x-request-id"]; UUID(rid)
        if request.url.path.endswith("/capabilities"):
            value = {"version":"1", "auth":{"issuer":config.issuer, "jwks_uri":config.jwks_uri,
                "resource":config.resource, "algorithm":"ES256", "clients":{"browser":"dream-browser","device":"dream-device"},
                "scopes":["dream:read","dream:write"], "delegations":[]}, "schema_capabilities":schemas, "operations":operations}
        elif request.url.path.endswith("/principal"):
            value = {"subject":"opaque-ba-subject", "canonical_user_id":"42", "client_id":"dream-browser",
                "scopes":["dream:read"], "status":"active"}
        else:
            assert request.url.path.endswith("/operations/deck.detail")
            assert request.headers["authorization"] == "Bearer read-token" and "cookie" not in request.headers
            assert json.loads(request.content) == {"request_id":rid,"input":{"deck_id":"deck-1"}}
            calls.append(rid)
            value = outputs["deck"]
            if isinstance(value, Exception): raise value
            value = {"deck":value}
        return httpx.Response(200, json={"request_id":rid,"data":value})

    http = httpx.Client(transport=httpx.MockTransport(handler)); client = AdminDataClient(config, client=http, operations=(READ_DECK_DETAIL,))
    app = FastAPI(); app.state.admin_request_auth = AdminRequestAuth(config, client=client, verifier=ReadVerifier()); app.include_router(router)
    with TestClient(app) as browser: yield browser, outputs, calls, schemas, operations
    http.close()


def test_complete_original_response_preserves_fields_and_numeric_types(boundary):
    browser, _, calls, *_ = boundary; response = browser.get("/api/decks/deck-1", headers=HEADERS)
    expected = aggregate(); expected["owner_id"] = 42
    expected["voices"][0]["owner_id"] = 9223372036854775807
    expected["voices"][0].pop("memory_workspace_config_json")
    expected["voices"][0]["memory_workspace_config"] = {"float":1.0,"zero":-0.0,"big":9007199254740993}
    assert response.status_code == 200 and response.json() == expected and len(calls) == 1
    memory = response.json()["voices"][0]["memory_workspace_config"]
    assert type(memory["float"]) is float and math.copysign(1, memory["zero"]) == -1 and type(memory["big"]) is int


@pytest.mark.parametrize("raw,expected", [(None,None),("",""),("bad json",None),("[]",[]),("null",None),("false",False),("0",0),('"text"',"text")])
def test_legacy_memory_values_keep_original_read_behavior(boundary, raw, expected):
    browser, outputs, *_ = boundary; outputs["deck"]["voices"][0]["memory_workspace_config_json"] = raw
    response = browser.get("/api/decks/deck-1", headers=HEADERS)
    assert response.status_code == 200 and response.json()["voices"][0]["memory_workspace_config"] == expected


@pytest.mark.parametrize("raw", ['{"n":NaN}', '[Infinity]', '1e999'])
def test_nonfinite_legacy_memory_safe_failure_without_heal(boundary, raw):
    browser, outputs, calls, *_ = boundary; outputs["deck"]["voices"][0]["memory_workspace_config_json"] = raw
    response = browser.get("/api/decks/deck-1", headers=HEADERS)
    assert response.status_code == 503 and response.json()["detail"] == {"error_code":"ADMIN_RESPONSE_INVALID","request_id":calls[0],"outcome_unknown":False}
    assert len(calls) == 1 and outputs["deck"]["voices"][0]["memory_workspace_config_json"] == raw


def test_null_owned_aggregate_keeps_original_404(boundary):
    browser, outputs, *_ = boundary; outputs["deck"] = None
    response = browser.get("/api/decks/deck-1", headers=HEADERS)
    assert response.status_code == 404 and response.json() == {"detail":"Deck not found"}


@pytest.mark.parametrize("where,field,value", [
    ("deck","id","foreign"),("voice","deck_id","foreign"),("deck","extra","private"),
    ("voice","extra","private"),("deck","deck_version_capability",1),("deck","enabled",0),
    ("deck","draft_revision",0),("deck","latest_version",9007199254740992),
    ("voice","owner_id","9223372036854775808"),("deck","created_at","2026-13-99T01:02:03Z"),
    ("voice","order_index",True),("voice","memory_workspace_config_json",{}),
    ("deck","agent_type","other"),("deck","publish_block_reason","other")])
def test_closed_malformed_and_entity_mismatch_fails_safely(boundary, where, field, value):
    browser, outputs, calls, *_ = boundary
    target = outputs["deck"] if where == "deck" else outputs["deck"]["voices"][0]; target[field] = value
    response = browser.get("/api/decks/deck-1", headers=HEADERS)
    assert response.status_code == 503 and response.json()["detail"] == {"error_code":"ADMIN_RESPONSE_INVALID","request_id":calls[0],"outcome_unknown":False}
    assert "private" not in response.text and len(calls) == 1


@pytest.mark.parametrize("where,field", [("deck","description"),("voice","thread_id"),("voice","owner_id")])
def test_required_nullable_fields_cannot_be_missing(boundary, where, field):
    browser, outputs, *_ = boundary; target = outputs["deck"] if where == "deck" else outputs["deck"]["voices"][0]; target.pop(field)
    assert browser.get("/api/decks/deck-1", headers=HEADERS).status_code == 503


@pytest.mark.parametrize("mutation", ["schema-missing","schema-hash","schema-duplicate","op-hash","op-missing"])
def test_exact_contract_gates_before_detail_io(boundary, mutation):
    browser, _, calls, schemas, operations = boundary
    if mutation == "schema-missing": schemas.pop()
    elif mutation == "schema-hash": schemas[0]["contract_sha256"] = "0"*64
    elif mutation == "schema-duplicate": schemas.append(copy.copy(schemas[0]))
    elif mutation == "op-hash": operations[0]["contract_sha256"] = "0"*64
    else: operations.clear()
    assert browser.get("/api/decks/deck-1", headers=HEADERS).status_code == 503 and not calls


def test_runtime_delegation_is_not_deck_management_authority(boundary):
    browser, _, calls, *_ = boundary
    assert browser.get("/api/decks/deck-1", headers={"authorization":"Bearer idg_synthetic"}).status_code == 401 and not calls


def test_read_timeout_has_one_original_request_and_no_retry(boundary):
    browser, outputs, calls, *_ = boundary; outputs["deck"] = httpx.ReadTimeout("private token/body")
    response = browser.get("/api/decks/deck-1", headers=HEADERS)
    assert response.status_code == 504 and response.json()["detail"] == {"error_code":"ADMIN_TIMEOUT","request_id":calls[0],"outcome_unknown":False}
    assert len(calls) == 1 and "private" not in response.text
