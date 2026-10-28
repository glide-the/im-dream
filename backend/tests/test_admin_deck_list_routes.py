# [Sync] 2026-10-28: prove catalog single dispatch, ownership relations, empty output and capability failures.
# [Input] Actual public Deck list/Auth/DTO and controlled owned/community aggregates.
# [Output] Original mode-dependent fields, counts, authority and malformed/capability failure evidence.
# [Pos] Provider-free Deck list harness; no SQL, default initialization or policy copy.
# [Sync] 2026-09-15: fence both old list helpers and preserve one Admin read per mode.
from __future__ import annotations

import copy
import json
from uuid import UUID
import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers.voices import router
from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.deck_list_data import LIST_DECKS, READ_DECK_CATALOG
from services.admin_data.deck_version_data import DECK_VERSION_SCHEMA_REQUIREMENTS
from services.admin_data.request_auth import AdminRequestAuth
from tests.test_admin_deck_detail_routes import aggregate
from tests.test_admin_request_auth import Verifier

HEADERS = {"authorization":"Bearer read-token"}


def list_item():
    result = aggregate(); result.pop("voices")
    return {**result,"voice_count":2,"total_voice_count":3,"author_display_name":None}


@pytest.fixture
def boundary(monkeypatch):
    import database
    monkeypatch.setattr(database,"get_db",lambda *_a,**_kw:pytest.fail("Deck lists must not query Dream PG"))
    assert not hasattr(database,"get_user_decks") and not hasattr(database,"get_published_decks")
    config = AdminDataConfig(base_url="https://admin.example",issuer="https://admin.example/api/auth",resource="https://dream.example/api",service_client_id="dream-service",service_secret="s"*32)
    outputs = {"decks":[list_item()], "catalog":[{**list_item(), "voices":aggregate()["voices"]}]}; calls = []
    schemas = [x.model_dump() for x in DECK_VERSION_SCHEMA_REQUIREMENTS]; operations = [LIST_DECKS.capability.model_dump(), READ_DECK_CATALOG.capability.model_dump()]
    class ListVerifier(Verifier):
        def verify(self,token,*,required_scopes):
            if token.startswith("idg_"):raise AdminDataError("INVALID_ACCESS_TOKEN",401)
            return super().verify(token,required_scopes=required_scopes)
    def handler(request):
        rid = request.headers["x-request-id"]; UUID(rid)
        if request.url.path.endswith("/capabilities"):
            value = {"version":"1","auth":{"issuer":config.issuer,"jwks_uri":config.jwks_uri,"resource":config.resource,"algorithm":"ES256","clients":{"browser":"dream-browser","device":"dream-device"},"scopes":["dream:read","dream:write"],"delegations":[]},"schema_capabilities":schemas,"operations":operations}
        elif request.url.path.endswith("/principal"):
            value = {"subject":"opaque-ba-subject","canonical_user_id":"42","client_id":"dream-browser","scopes":["dream:read"],"status":"active"}
        else:
            catalog = request.url.path.endswith("/operations/deck.catalog")
            assert (catalog or request.url.path.endswith("/operations/deck.list")) and request.headers["authorization"]=="Bearer read-token" and "cookie" not in request.headers
            body = json.loads(request.content); assert set(body)=={"request_id","input"} and body["request_id"]==rid and set(body["input"])==(set() if catalog else {"community"})
            calls.append((body["input"],rid)); outputs.setdefault("timeouts", []).append(request.extensions["timeout"]); value = outputs["catalog" if catalog else "decks"]
            if isinstance(value,Exception):raise value
            value = {"decks":value}
        return httpx.Response(200,json={"request_id":rid,"data":value})
    http = httpx.Client(transport=httpx.MockTransport(handler)); client = AdminDataClient(config,client=http,operations=(LIST_DECKS,READ_DECK_CATALOG))
    app = FastAPI(); app.state.admin_request_auth = AdminRequestAuth(config,client=client,verifier=ListVerifier()); app.include_router(router)
    with TestClient(app) as browser:yield browser,outputs,calls,schemas,operations
    http.close()


@pytest.mark.parametrize("community",[False,True])
def test_both_modes_restore_original_fields_and_one_read(boundary,community):
    browser,outputs,calls,*_ = boundary
    if community:outputs["decks"][0].update(owner_id=None,total_voice_count=None,author_display_name="作者")
    expected = copy.deepcopy(outputs["decks"][0]); expected["owner_id"] = None if community else 42
    expected.pop("total_voice_count" if community else "author_display_name")
    response = browser.get("/api/decks?published="+str(community).lower(),headers=HEADERS)
    assert response.status_code==200 and response.json()=={"decks":[expected]} and len(calls)==1 and calls[0][0]=={"community":community}


@pytest.mark.parametrize("query,expected",[("",False),("?published=1",True),("?published=0",False),("?published=yes",True)])
def test_existing_public_query_bool_semantics(boundary,query,expected):
    browser,_,calls,*_ = boundary
    assert browser.get("/api/decks"+query,headers=HEADERS).status_code==200 and calls[0][0]=={"community":expected}


def test_empty_community_only_selects_mode_without_external_actor_id(boundary):
    browser,outputs,calls,*_ = boundary;outputs["decks"]=[]
    assert browser.get("/api/decks?published=true",headers=HEADERS).json()=={"decks":[]}
    assert calls[0][0]=={"community":True} and len(calls)==1


def test_order_and_large_owner_are_returned_without_local_policy_or_sort(boundary):
    browser,outputs,*_ = boundary; second=copy.deepcopy(list_item());second.update(id="deck-2",owner_id="9223372036854775807",order_index=-1)
    outputs["decks"].append(second);response=browser.get("/api/decks",headers=HEADERS)
    assert response.status_code==200 and [x["id"] for x in response.json()["decks"]]==["deck-1","deck-2"]
    assert response.json()["decks"][1]["owner_id"]==9223372036854775807


@pytest.mark.parametrize("field,value",[("voice_count",True),("voice_count",-1),("total_voice_count",9007199254740992),("deck_version_capability",1),("owner_id","0"),("created_at","bad private timestamp"),("extra","private")])
def test_malformed_list_response_is_closed_and_safe(boundary,field,value):
    browser,outputs,calls,*_ = boundary;outputs["decks"][0][field]=value;response=browser.get("/api/decks",headers=HEADERS)
    assert response.status_code==503 and response.json()["detail"]=={"error_code":"ADMIN_RESPONSE_INVALID","request_id":calls[0][1],"outcome_unknown":False}
    assert "private" not in response.text and len(calls)==1


@pytest.mark.parametrize("field",["total_voice_count","author_display_name"])
def test_nullable_helper_fields_are_wire_required(boundary,field):
    browser,outputs,*_ = boundary;outputs["decks"][0].pop(field)
    assert browser.get("/api/decks",headers=HEADERS).status_code==503


@pytest.mark.parametrize("mutation",["schema-missing","schema-hash","schema-duplicate","op-missing","op-hash"])
def test_four_exact_schemas_and_operation_gate_before_domain_io(boundary,mutation):
    browser,_,calls,schemas,operations=boundary
    if mutation=="schema-missing":schemas.pop()
    elif mutation=="schema-hash":schemas[0]["contract_sha256"]="0"*64
    elif mutation=="schema-duplicate":schemas.append(copy.copy(schemas[0]))
    elif mutation=="op-missing":operations.clear()
    else:operations[0]["contract_sha256"]="0"*64
    assert browser.get("/api/decks",headers=HEADERS).status_code==503 and not calls


def test_runtime_delegate_cannot_manage_deck_lists(boundary):
    browser,_,calls,*_=boundary
    assert browser.get("/api/decks",headers={"authorization":"Bearer idg_synthetic"}).status_code==401 and not calls


def test_read_timeout_preserves_original_request_with_bounded_transport_recovery(boundary):
    browser,outputs,calls,*_=boundary;outputs["decks"]=httpx.ReadTimeout("private token")
    response=browser.get("/api/decks",headers=HEADERS)
    assert response.status_code==504 and response.json()["detail"]=={"error_code":"ADMIN_TIMEOUT","request_id":calls[0][1],"outcome_unknown":False} and len(calls)==2
    assert calls[0] == calls[1] and outputs["timeouts"][1]["read"] == min(2.0, outputs["timeouts"][0]["read"])


def test_catalog_is_one_read_with_existing_voice_projection(boundary):
    browser, _, calls, *_ = boundary
    response = browser.get("/api/decks/catalog", headers=HEADERS)
    assert response.status_code == 200 and len(calls) == 1 and calls[0][0] == {}
    deck = response.json()["decks"][0]
    assert deck["id"] == "deck-1" and deck["owner_id"] == 42
    assert "author_display_name" not in deck and deck["total_voice_count"] == 3
    voice = deck["voices"][0]
    assert voice["deck_id"] == deck["id"] and voice["enabled"] is False
    assert voice["memory_workspace_config"]["big"] == 9007199254740993
    assert "memory_workspace_config_json" not in voice


def test_empty_catalog_is_a_successful_single_read(boundary):
    browser, outputs, calls, *_ = boundary
    outputs["catalog"] = []
    response = browser.get("/api/decks/catalog", headers=HEADERS)
    assert response.status_code == 200 and response.json() == {"decks": []} and len(calls) == 1


@pytest.mark.parametrize("mutation", ["missing-voices", "cross-deck", "duplicate-deck", "duplicate-voice", "extra-voice-field"])
def test_invalid_catalog_is_closed_without_detail_fallback(boundary, mutation):
    browser, outputs, calls, *_ = boundary
    deck = outputs["catalog"][0]
    if mutation == "missing-voices": deck.pop("voices")
    elif mutation == "cross-deck": deck["voices"][0]["deck_id"] = "private-other-deck"
    elif mutation == "duplicate-deck": outputs["catalog"].append(copy.deepcopy(deck))
    elif mutation == "duplicate-voice": deck["voices"].append(copy.deepcopy(deck["voices"][0]))
    else: deck["voices"][0]["private"] = "private detail"
    response = browser.get("/api/decks/catalog", headers=HEADERS)
    assert response.status_code == 503 and len(calls) == 1
    assert response.json()["detail"]["error_code"] == "ADMIN_RESPONSE_INVALID"
    assert "private" not in response.text


@pytest.mark.parametrize("mutation", ["missing", "hash", "schema"])
def test_catalog_requires_its_exact_published_capability(boundary, mutation):
    browser, _, calls, schemas, operations = boundary
    if mutation == "missing": operations.pop()
    elif mutation == "hash": operations[-1]["contract_sha256"] = "0" * 64
    else: schemas.pop()
    assert browser.get("/api/decks/catalog", headers=HEADERS).status_code == 503 and not calls


def test_catalog_timeout_keeps_bounded_same_request_transport_recovery(boundary):
    browser, outputs, calls, *_ = boundary
    outputs["catalog"] = httpx.ReadTimeout("private token")
    response = browser.get("/api/decks/catalog", headers=HEADERS)
    assert response.status_code == 504 and len(calls) == 2 and calls[0] == calls[1] and "private" not in response.text
    assert outputs["timeouts"][1]["read"] == min(2.0, outputs["timeouts"][0]["read"])


def test_catalog_rejects_runtime_delegation_before_domain_read(boundary):
    browser, _, calls, *_ = boundary
    assert browser.get("/api/decks/catalog", headers={"authorization":"Bearer idg_synthetic"}).status_code == 401
    assert not calls
