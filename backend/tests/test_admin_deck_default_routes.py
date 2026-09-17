# [Input] Registry104 contracts, current OAuth, local plugin verifiers and public Deck create/reconcile routes.
# [Output] Exact two-step evidence flow, closed DTOs, original receipt recovery and Dream-PostgreSQL fences.
# [Pos] Provider-free Deck-default consumer/route harness; no real PostgreSQL, Google account or model call.
# [Sync] 2026-09-15: bind public create/reconcile to Admin policy selection and transaction-owned writes.
from __future__ import annotations

import json
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from routers import voices as deck_routes
from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.deck_default_data import (
    AdminDeckDefaultData,
    CREATE_DECK,
    DECK_DEFAULT_OPERATIONS,
    PROVISION_DEFAULT_DECK,
    DeckDefaultInputDTO,
    DefaultPluginEvidenceDTO,
)
from services.admin_data.deck_version_data import DECK_VERSION_SCHEMA_REQUIREMENTS
from services.admin_data.models import CommittedReceiptDTO
from services.admin_data.request_auth import AdminRequestAuth
from services.deck import defaults as deck_defaults
from tests.test_admin_request_auth import Verifier


HEADERS = {"authorization": "Bearer write-token"}
DIGEST = f"sha256:{'a' * 64}"
CANDIDATE = {
    "plugin_installation_id": "installation-drama-forge",
    "package_name": "drama-forge",
    "marketplace": "drama-studio",
    "resolved_version": "1.0.1",
    "artifact_digest": DIGEST,
    "compatibility_json": '{"claude_code":">=1.0.0"}',
}


def _forbidden(*_args, **_kwargs):
    pytest.fail("Public Deck-default routes must not use Dream PostgreSQL")


@pytest.fixture
def boundary(monkeypatch):
    import database

    monkeypatch.setattr(database, "get_db", _forbidden)
    for retired in (
        "create_deck",
        "auto_fork_system_decks",
        "reconcile_default_screenplay_deck_plugin_ref",
    ):
        assert not hasattr(database, retired)
    verifier_calls: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        deck_defaults.PluginInstallService,
        "verify_installation_artifact",
        staticmethod(lambda record: verifier_calls.append(("artifact", record)) or True),
    )
    monkeypatch.setattr(
        deck_defaults.PluginInstallService,
        "check_cli_compatibility",
        staticmethod(lambda record: verifier_calls.append(("cli", record)) or True),
    )

    config = AdminDataConfig(
        base_url="https://admin.example",
        issuer="https://admin.example/api/auth",
        resource="https://dream.example/api",
        service_client_id="dream-service",
        service_secret="s" * 32,
    )
    state = {
        "calls": [],
        "receipt_calls": [],
        "schemas": [item.model_dump() for item in DECK_VERSION_SCHEMA_REQUIREMENTS],
        "operations": [item.capability.model_dump() for item in DECK_DEFAULT_OPERATIONS],
        "outputs": {
            "deck.default-plugin.resolve": {"installation": dict(CANDIDATE)},
            "deck.create": {"deck_id": "deck-created"},
            "deck.reconcile-default": {
                "deck_id": "screenplay-user-deck",
                "reconciled": True,
                "reason": "missing_ref",
            },
            "deck.provision-default": {"deck_id": "screenplay-user-deck"},
        },
        "receipts": {},
    }

    class DeckVerifier(Verifier):
        def verify(self, token, *, required_scopes):
            if token.startswith("idg_"):
                raise AdminDataError("INVALID_ACCESS_TOKEN", 401)
            return super().verify(token, required_scopes=required_scopes)

    def handler(request: httpx.Request) -> httpx.Response:
        request_id = request.headers["x-request-id"]
        UUID(request_id)
        if request.url.path.endswith("/capabilities"):
            value = {
                "version": "1",
                "auth": {
                    "issuer": config.issuer,
                    "jwks_uri": config.jwks_uri,
                    "resource": config.resource,
                    "algorithm": "ES256",
                    "clients": {"browser": "dream-browser", "device": "dream-device"},
                    "scopes": ["dream:read", "dream:write"],
                    "delegations": [],
                },
                "schema_capabilities": state["schemas"],
                "operations": state["operations"],
            }
        elif request.url.path.endswith("/principal"):
            value = {
                "subject": "opaque-ba-subject",
                "canonical_user_id": "42",
                "client_id": "dream-browser",
                "scopes": ["dream:read", "dream:write"],
                "status": "active",
            }
        elif "/receipts/" in request.url.path:
            operation = request.url.params["operation"]
            state["receipt_calls"].append((operation, request_id))
            value = state["receipts"].get(
                request_id,
                {"status": "absent", "operation": operation, "request_id": request_id},
            )
        else:
            operation = request.url.path.rsplit("/", 1)[-1]
            body = json.loads(request.content)
            assert set(body) == {"request_id", "input"}
            assert body["request_id"] == request_id
            assert not {
                "user_id", "actor_id", "subject", "sql", "table", "column",
            } & body["input"].keys()
            assert request.headers["authorization"] == "Bearer write-token"
            assert "cookie" not in request.headers
            state["calls"].append((operation, body["input"], request_id))
            value = state["outputs"][operation]
            if isinstance(value, Exception):
                if operation != "deck.default-plugin.resolve":
                    state["receipts"].setdefault(
                        request_id,
                        {
                            "status": "absent",
                            "operation": operation,
                            "request_id": request_id,
                        },
                    )
                raise value
            if isinstance(value, tuple):
                status, code = value
                return httpx.Response(
                    status,
                    json={
                        "request_id": request_id,
                        "error": {"code": code, "message": "private upstream detail"},
                    },
                )
        return httpx.Response(200, json={"request_id": request_id, "data": value})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = AdminDataClient(config, client=http, operations=DECK_DEFAULT_OPERATIONS)
    app = FastAPI()
    app.state.admin_request_auth = AdminRequestAuth(
        config,
        client=client,
        verifier=DeckVerifier(),
    )
    app.include_router(deck_routes.router)
    with TestClient(app) as browser:
        yield browser, state, verifier_calls, AdminDeckDefaultData(client)
    http.close()


def test_create_uses_admin_candidate_local_verification_and_one_admin_write(boundary):
    browser, state, verifier_calls, _data = boundary
    response = browser.post(
        "/api/decks",
        headers=HEADERS,
        json={
            "name": "New Deck",
            "description": "",
            "name_zh": None,
            "color": None,
        },
    )
    assert response.status_code == 200
    assert response.json() == {"deck_id": "deck-created"}
    assert [call[0] for call in state["calls"]] == [
        "deck.default-plugin.resolve",
        "deck.create",
    ]
    assert state["calls"][0][1] == {}
    create_input = state["calls"][1][1]
    assert create_input == {
        "name": "New Deck",
        "name_zh": None,
        "name_en": None,
        "description": "",
        "description_zh": None,
        "description_en": None,
        "icon": None,
        "color": None,
        "order_index": None,
        "default_plugin_evidence": {
            key: CANDIDATE[key]
            for key in (
                "plugin_installation_id",
                "package_name",
                "resolved_version",
                "artifact_digest",
            )
        },
    }
    assert [kind for kind, _record in verifier_calls] == ["artifact", "cli"]
    assert verifier_calls[0][1] == CANDIDATE


def test_reconcile_uses_same_verified_evidence_and_preserves_result(boundary):
    browser, state, _verifier_calls, _data = boundary
    response = browser.post("/api/decks/defaults/reconcile", headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == {
        "deck_id": "screenplay-user-deck",
        "reconciled": True,
        "reason": "missing_ref",
    }
    assert [call[0] for call in state["calls"]] == [
        "deck.default-plugin.resolve",
        "deck.reconcile-default",
    ]


@pytest.mark.parametrize("failure", ["missing", "artifact", "cli"])
def test_missing_or_unverified_candidate_fails_closed_before_write(boundary, monkeypatch, failure):
    browser, state, _verifier_calls, _data = boundary
    if failure == "missing":
        state["outputs"]["deck.default-plugin.resolve"] = {"installation": None}
    elif failure == "artifact":
        monkeypatch.setattr(
            deck_defaults.PluginInstallService,
            "verify_installation_artifact",
            staticmethod(lambda _record: False),
        )
    else:
        monkeypatch.setattr(
            deck_defaults.PluginInstallService,
            "check_cli_compatibility",
            staticmethod(lambda _record: False),
        )
    response = browser.post("/api/decks", headers=HEADERS, json={"name": "New Deck"})
    assert response.status_code == 409
    assert "drama-forge v1.0.1" in response.json()["detail"]
    assert [call[0] for call in state["calls"]] == ["deck.default-plugin.resolve"]


def test_admin_transaction_rechecks_evidence_and_keeps_original_409(boundary):
    browser, state, _verifier_calls, _data = boundary
    state["outputs"]["deck.create"] = (409, "DEFAULT_DECK_PLUGIN_UNAVAILABLE")
    response = browser.post("/api/decks", headers=HEADERS, json={"name": "New Deck"})
    assert response.status_code == 409
    assert "private upstream detail" not in response.text
    assert len(state["calls"]) == 2


def test_unknown_create_recovers_committed_original_receipt_without_retry(boundary):
    browser, state, _verifier_calls, _data = boundary
    state["outputs"]["deck.create"] = httpx.ReadTimeout("private request body")

    class CommittingReceipts(dict):
        def setdefault(self, request_id, _default=None):
            return super().setdefault(
                request_id,
                {
                    "status": "committed",
                    "operation": "deck.create",
                    "request_id": request_id,
                    "result": {"deck_id": "deck-committed"},
                },
            )

    state["receipts"] = CommittingReceipts(state["receipts"])
    response = browser.post("/api/decks", headers=HEADERS, json={"name": "New Deck"})
    assert response.status_code == 200
    assert response.json() == {"deck_id": "deck-committed"}
    writes = [call for call in state["calls"] if call[0] == "deck.create"]
    assert len(writes) == 1
    assert state["receipt_calls"] == [("deck.create", writes[0][2])]


def test_unknown_create_with_absent_receipt_stays_unknown_without_retry(boundary):
    browser, state, _verifier_calls, _data = boundary
    state["outputs"]["deck.create"] = httpx.ReadTimeout("private request body")
    response = browser.post("/api/decks", headers=HEADERS, json={"name": "New Deck"})
    assert response.status_code == 503
    assert response.json()["detail"]["error_code"] == "ADMIN_WRITE_RESULT_UNKNOWN"
    assert response.json()["detail"]["outcome_unknown"] is True
    writes = [call for call in state["calls"] if call[0] == "deck.create"]
    assert len(writes) == 1
    assert state["receipt_calls"] == [("deck.create", writes[0][2])]


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "New Deck", "default_plugin_evidence": dict(CANDIDATE)},
        {"name": "New Deck", "user_id": 42},
        {"name": "New Deck", "order_index": 0},
        {"name": 3},
    ],
)
def test_browser_cannot_author_evidence_actor_or_server_order(boundary, payload):
    browser, state, _verifier_calls, _data = boundary
    response = browser.post("/api/decks", headers=HEADERS, json=payload)
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid Deck request"}
    assert state["calls"] == []


@pytest.mark.parametrize(
    "bad_candidate",
    [
        {**CANDIDATE, "status": "ready"},
        {**CANDIDATE, "artifact_digest": f"sha256:{'z' * 64}"},
        {**CANDIDATE, "compatibility_json": 3},
    ],
)
def test_malformed_candidate_fails_closed_without_local_verification_or_write(boundary, bad_candidate):
    browser, state, verifier_calls, _data = boundary
    state["outputs"]["deck.default-plugin.resolve"] = {"installation": bad_candidate}
    response = browser.post("/api/decks", headers=HEADERS, json={"name": "New Deck"})
    assert response.status_code == 503
    assert response.json()["detail"]["error_code"] == "ADMIN_RESPONSE_INVALID"
    assert [call[0] for call in state["calls"]] == ["deck.default-plugin.resolve"]
    assert verifier_calls == []


@pytest.mark.parametrize("mutation", ["schema", "schema-duplicate", "operation", "operation-hash"])
def test_exact_registry104_capability_gate_precedes_domain_io(boundary, mutation):
    browser, state, _verifier_calls, _data = boundary
    if mutation == "schema":
        state["schemas"].pop()
    elif mutation == "schema-duplicate":
        state["schemas"].append(state["schemas"][0].copy())
    elif mutation == "operation":
        state["operations"].pop(0)
    else:
        state["operations"][0]["contract_sha256"] = "0" * 64
    response = browser.post("/api/decks", headers=HEADERS, json={"name": "New Deck"})
    assert response.status_code == 503
    assert state["calls"] == []


def test_provision_contract_is_registered_strict_and_receipt_typed(boundary):
    _browser, _state, _verifier_calls, data = boundary
    evidence = DefaultPluginEvidenceDTO(
        plugin_installation_id=CANDIDATE["plugin_installation_id"],
        package_name=CANDIDATE["package_name"],
        resolved_version=CANDIDATE["resolved_version"],
        artifact_digest=CANDIDATE["artifact_digest"],
    )
    with pytest.raises(ValidationError):
        DeckDefaultInputDTO.model_validate(
            {"default_plugin_evidence": evidence.model_dump(), "user_id": "42"}
        )
    assert PROVISION_DEFAULT_DECK in DECK_DEFAULT_OPERATIONS
    assert CREATE_DECK.capability.kind == "write"


def test_committed_receipt_model_keeps_exact_typed_result():
    receipt = CommittedReceiptDTO[CREATE_DECK.output_dto](
        request_id="original-id",
        status="committed",
        operation="deck.create",
        result={"deck_id": "deck-created"},
    )
    assert type(receipt.result) is CREATE_DECK.output_dto
