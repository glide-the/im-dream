# [Sync] 2026-09-17: verify confidential service OAuth and separate delegated-user Bearer transport.
# [Input] Actual refs public router/Auth/client/DTO, synthetic metadata and explicitly owned artifact fixture.
# [Output] OAuth/schema/evidence/default/read projection/unknown-write and safe validation contract evidence.
# [Pos] Provider-free refs harness; actual local digest checks with injected CLI version, no shared FS/model/PG acceptance.
# [Sync] 2026-09-15: fence Dream DB and call production refs operations through the public FastAPI routes.
from __future__ import annotations

import json
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.claude_plugins import router
from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.deck_refs_data import DECK_REFS_OPERATIONS
from services.admin_data.request_auth import AdminRequestAuth
from services.admin_data.workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS
from services.claude_plugin import install_service
from tests.test_admin_request_auth import Verifier

HEADERS = {"authorization": "Bearer write-token"}
DECK = "deck-7"


def installation(id="plugin-1"):
    return {"id": id, "requested_package_spec": "demo@market", "package_name": "demo", "marketplace": "market",
        "resolved_version": "1.0.0", "artifact_digest": "sha256:" + "a" * 64, "claude_cli_version": "2.1.241",
        "source_type": "marketplace", "status": "ready", "manifest_json": None, "component_inventory_json": "{}",
        "compatibility_json": '{"claude_code":">=2.0.0"}'}


def ref(id="plugin-1"):
    record = installation(id)
    return {"deck_id": DECK, "plugin_installation_id": id, "package_spec": "demo@market",
        "resolved_version": record["resolved_version"], "artifact_digest": record["artifact_digest"], "enabled": True,
        "order_index": -2, "created_at": "2026-09-15T03:02:01.123456+08:00", "updated_at": "2026-09-15T03:02:02.654321+08:00",
        "installation_status": record["status"], "source_type": record["source_type"], "claude_cli_version": record["claude_cli_version"],
        "manifest_json": None, "component_inventory_json": "{}"}


def boundary(monkeypatch, *, local_checks=True, canonical_user_id="42"):
    import database
    monkeypatch.setattr(database, "get_db", lambda: pytest.fail("Public refs must not use Dream PG"))
    if local_checks:
        monkeypatch.setattr(install_service.PluginInstallService, "verify_installation_artifact", staticmethod(lambda _: True))
        monkeypatch.setattr(install_service.PluginInstallService, "check_cli_compatibility", staticmethod(lambda _: True))
    config = AdminDataConfig(base_url="https://admin.example", issuer="https://admin.example/api/auth", resource="https://dream.example/api",
        service_client_id="dream-service", service_secret="s" * 32)
    outputs = {"deck-plugin-refs.list": {"deck_id": DECK, "refs": [ref()]}, "deck-plugin-refs.prepare": {"installations": [installation()]},
        "deck-plugin-refs.replace": {"deck_id": DECK, "refs": [ref()], "changed": False}}
    schemas = [item.model_dump() for item in WORKFLOW_SCHEMA_REQUIREMENTS]
    operations = [item.capability.model_dump() for item in DECK_REFS_OPERATIONS]
    calls = []

    class RefsVerifier(Verifier):
        def verify(self, token, *, required_scopes):
            if token.startswith("idg_"):
                raise AdminDataError("INVALID_ACCESS_TOKEN", 401)
            return super().verify(token, required_scopes=required_scopes)

    def handler(request):
        request_id = request.headers["x-request-id"]; UUID(request_id)
        if request.url.path.endswith("/capabilities"):
            value = {"version": "1", "auth": {"issuer": config.issuer, "jwks_uri": config.jwks_uri, "resource": config.resource,
                "algorithm": "ES256", "clients": {"browser": "dream-browser", "device": "dream-device"},
                "scopes": ["dream:read", "dream:write"], "delegations": []}, "schema_capabilities": schemas, "operations": operations}
        elif request.url.path.endswith("/principal"):
            value = {"subject": "opaque-ba-subject", "canonical_user_id": canonical_user_id, "client_id": "dream-browser",
                "scopes": ["dream:read"] if request.headers["authorization"] == "Bearer read-token" else ["dream:read", "dream:write"], "status": "active"}
        else:
            name = request.url.path.rsplit("/", 1)[-1]; body = json.loads(request.content)
            assert set(body) == {"request_id", "input"} and body["request_id"] == request_id
            assert not {"actor_id", "user_id", "path", "artifact_path"} & body["input"].keys()
            assert request.headers["authorization"] in {"Bearer write-token", "Bearer read-token"}
            assert request.headers["x-ink-dream-service-authorization"] == "Bearer fixture.service.access.token"
            assert "x-ink-dream-credential" not in request.headers and "cookie" not in request.headers
            calls.append((name, body["input"], request_id)); value = outputs[name]
            if isinstance(value, Exception):
                raise value
            if isinstance(value, httpx.Response):
                return httpx.Response(value.status_code, json={"request_id": request_id, "error": {"code": "ENTITY_NOT_FOUND", "message": "private owner"}})
        return httpx.Response(200, json={"request_id": request_id, "data": value})

    client = AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(handler)), operations=DECK_REFS_OPERATIONS)
    app = FastAPI(); app.state.admin_request_auth = AdminRequestAuth(config, client=client, verifier=RefsVerifier()); app.include_router(router)
    return TestClient(app), calls, outputs, schemas, operations


def test_list_preserves_original_refs_enabled_integer_and_precise_time(monkeypatch):
    client, calls, *_ = boundary(monkeypatch)
    with client:
        response = client.get(f"/api/decks/{DECK}/claude-plugins", headers=HEADERS)
    assert response.status_code == 200 and response.json() == {"deck_id": DECK, "refs": [{**ref(), "enabled": 1}]}
    assert type(response.json()["refs"][0]["enabled"]) is int
    assert calls[0][1] == {"deck_id": DECK}


def test_replace_builds_source_evidence_only_from_prepare_and_keeps_public_shape(monkeypatch):
    client, calls, outputs, *_ = boundary(monkeypatch)
    outputs["deck-plugin-refs.prepare"]["installations"][0]["compatibility_json"] = '{"claude_code": ">=2.0.0", "float":1.0, "zero":-0.0, "big":9007199254740993}'
    with client:
        response = client.put(f"/api/decks/{DECK}/claude-plugins", headers=HEADERS, json={"refs": [{"plugin_installation_id": "\u3000plugin-1\u3000"}]})
    assert response.status_code == 200 and set(response.json()) == {"deck_id", "refs"}
    assert [name for name, *_ in calls] == ["deck-plugin-refs.prepare", "deck-plugin-refs.replace"]
    assert calls[0][1] == {"deck_id": DECK, "installation_ids": ["plugin-1"]}
    evidence = calls[1][1]["refs"][0]
    assert evidence == {"plugin_installation_id": "plugin-1", "package_name": "demo", "marketplace": "market", "resolved_version": "1.0.0",
        "artifact_digest": "sha256:" + "a" * 64, "compatibility_json": outputs["deck-plugin-refs.prepare"]["installations"][0]["compatibility_json"],
        "enabled": True, "order_index": 0}
    assert calls[0][2] != calls[1][2]


def test_empty_refs_and_explicit_disabled_negative_order_are_preserved(monkeypatch):
    client, calls, outputs, *_ = boundary(monkeypatch)
    with client:
        response = client.put(f"/api/decks/{DECK}/claude-plugins", headers=HEADERS,
            json={"refs": [{"plugin_installation_id": "plugin-1", "enabled": False, "order_index": -9}]})
        assert response.status_code == 200
        outputs["deck-plugin-refs.prepare"]["installations"] = []; outputs["deck-plugin-refs.replace"]["refs"] = []
        assert client.put(f"/api/decks/{DECK}/claude-plugins", headers=HEADERS, json={}).json() == {"deck_id": DECK, "refs": []}
    assert calls[1][1]["refs"][0]["enabled"] is False and calls[1][1]["refs"][0]["order_index"] == -9
    assert calls[2][1]["installation_ids"] == [] and calls[3][1]["refs"] == []


def test_actual_contract_has_no_legacy_arbitrary_32_ref_limit(monkeypatch):
    client, calls, outputs, *_ = boundary(monkeypatch)
    ids = [f"plugin-{index}" for index in range(33)]
    outputs["deck-plugin-refs.prepare"]["installations"] = [installation(id) for id in ids]
    outputs["deck-plugin-refs.replace"]["refs"] = [ref(id) for id in ids]
    with client:
        assert client.put(f"/api/decks/{DECK}/claude-plugins", headers=HEADERS, json={"refs": [{"plugin_installation_id": id} for id in ids]}).status_code == 200
    assert [item["order_index"] for item in calls[1][1]["refs"]] == list(range(33))


@pytest.mark.parametrize("field,value", [("user_id", "43"), ("artifact_path", "/private"), ("package_name", "override"),
    ("artifact_digest", "sha256:" + "b" * 64), ("compatibility_json", "{}"), ("enabled", 1), ("order_index", True),
    ("order_index", 2_147_483_648), ("plugin_installation_id", " ")])
def test_invalid_public_ref_fields_fail_before_domain_io_without_body_echo(monkeypatch, field, value):
    client, calls, *_ = boundary(monkeypatch)
    with client:
        response = client.put(f"/api/decks/{DECK}/claude-plugins", headers=HEADERS, json={"refs": [{"plugin_installation_id": "plugin-1", field: value}]})
    assert response.status_code == 422 and response.json() == {"detail": "Invalid plugin request"} and not calls


@pytest.mark.parametrize("body", [{"actor_id": "43"}, {"refs": [{"plugin_installation_id": "plugin-1"}, {"plugin_installation_id": " plugin-1 "}]}])
def test_actor_or_duplicate_stripped_ids_rejected_before_domain_io(monkeypatch, body):
    client, calls, *_ = boundary(monkeypatch)
    with client:
        assert client.put(f"/api/decks/{DECK}/claude-plugins", headers=HEADERS, json=body).status_code == 422
    assert not calls


def test_nonfinite_public_input_returns_safe_422(monkeypatch):
    client, calls, *_ = boundary(monkeypatch)
    with client:
        response = client.put(f"/api/decks/{DECK}/claude-plugins", headers={**HEADERS, "content-type": "application/json"},
            content='{"refs":[{"plugin_installation_id":"plugin-1","order_index":NaN}]}')
    assert response.status_code == 422 and not calls and response.json() == {"detail": "Invalid plugin request"}


@pytest.mark.parametrize("damage", ["missing", "extra", "duplicate", "not-ready", "path", "digest", "manifest-required-null"])
def test_invalid_prepared_metadata_fails_before_artifact_or_replace(monkeypatch, damage):
    client, calls, outputs, *_ = boundary(monkeypatch)
    records = outputs["deck-plugin-refs.prepare"]["installations"]
    if damage == "missing": records.clear()
    elif damage == "extra": records.append(installation("other"))
    elif damage == "duplicate": records.append(installation())
    elif damage == "not-ready": records[0]["status"] = "error"
    elif damage == "path": records[0]["artifact_path"] = "/private"
    elif damage == "digest": records[0]["artifact_digest"] = "private"
    else: records[0].pop("manifest_json")
    monkeypatch.setattr(install_service.PluginInstallService, "verify_installation_artifact", staticmethod(lambda _: pytest.fail("Invalid preparation reached FS")))
    with client:
        response = client.put(f"/api/decks/{DECK}/claude-plugins", headers=HEADERS, json={"refs": [{"plugin_installation_id": "plugin-1"}]})
    assert response.status_code == 503 and len(calls) == 1 and response.json()["error"]["outcome_unknown"] is False


@pytest.mark.parametrize("operation", ["deck-plugin-refs.list", "deck-plugin-refs.replace"])
def test_reply_entity_mismatch_is_safe_and_write_unknown(monkeypatch, operation):
    client, calls, outputs, *_ = boundary(monkeypatch)
    outputs[operation]["refs"][0]["deck_id"] = "other"
    with client:
        response = client.get(f"/api/decks/{DECK}/claude-plugins", headers=HEADERS) if operation.endswith("list") else client.put(
            f"/api/decks/{DECK}/claude-plugins", headers=HEADERS, json={"refs": [{"plugin_installation_id": "plugin-1"}]})
    assert response.status_code == 503 and response.json()["error"]["outcome_unknown"] is operation.endswith("replace")
    assert response.json()["error"]["request_id"] == calls[-1][2]


def test_lost_replace_response_retains_original_uuid_and_never_retries(monkeypatch):
    client, calls, outputs, *_ = boundary(monkeypatch)
    outputs["deck-plugin-refs.replace"] = httpx.ReadTimeout("private source content")
    with client:
        response = client.put(f"/api/decks/{DECK}/claude-plugins", headers=HEADERS, json={"refs": [{"plugin_installation_id": "plugin-1"}]})
    assert response.status_code == 504 and len(calls) == 2 and response.json()["error"]["outcome_unknown"] is True
    assert response.json()["error"]["request_id"] == calls[-1][2] and "private" not in response.text


def test_missing_owned_deck_preserves_404_without_upstream_text(monkeypatch):
    client, calls, outputs, *_ = boundary(monkeypatch)
    outputs["deck-plugin-refs.list"] = httpx.Response(404)
    with client:
        response = client.get(f"/api/decks/{DECK}/claude-plugins", headers=HEADERS)
    assert response.status_code == 404 and "private" not in response.text and len(calls) == 1
    assert response.json()["error"]["outcome_unknown"] is False


@pytest.mark.parametrize("index", range(2))
@pytest.mark.parametrize("damage", ["missing", "hash", "duplicate"])
def test_two_exact_physical_capabilities_required_before_domain_io(monkeypatch, index, damage):
    client, calls, _, schemas, _ = boundary(monkeypatch)
    if damage == "missing": schemas.pop(index)
    elif damage == "hash": schemas[index]["contract_sha256"] = "b" * 64
    else: schemas.append(dict(schemas[index]))
    with client:
        assert client.get(f"/api/decks/{DECK}/claude-plugins", headers=HEADERS).status_code == 503
    assert not calls


@pytest.mark.parametrize("index", range(3))
def test_each_operation_hash_must_match_before_dispatch(monkeypatch, index):
    client, calls, _, _, operations = boundary(monkeypatch)
    operations[index]["contract_sha256"] = "b" * 64
    with client:
        response = client.get(f"/api/decks/{DECK}/claude-plugins", headers=HEADERS) if index == 0 else client.put(
            f"/api/decks/{DECK}/claude-plugins", headers=HEADERS, json={"refs": [{"plugin_installation_id": "plugin-1"}]})
    assert response.status_code == 503 and len(calls) == (1 if index == 2 else 0)


@pytest.mark.parametrize("failure", [None, "tampered", "incompatible"])
def test_actual_owned_artifact_digest_and_cli_semver_check_before_replace(monkeypatch, tmp_path, failure):
    store = install_service.artifact_store
    source = tmp_path / "stage21-plugin-source"; (source / ".claude-plugin").mkdir(parents=True)
    (source / ".claude-plugin" / "plugin.json").write_text('{"name":"demo","version":"1.0.0"}')
    monkeypatch.setattr(store.runtime, "get_artifacts_root", lambda: tmp_path / "stage21-owned-artifacts")
    monkeypatch.setattr(install_service.cli, "get_cli_version", lambda: "2.1.241")
    artifact = store.import_tree(source, package_name="demo", marketplace="market")
    client, calls, outputs, *_ = boundary(monkeypatch, local_checks=False)
    outputs["deck-plugin-refs.prepare"]["installations"][0]["artifact_digest"] = artifact.digest
    outputs["deck-plugin-refs.replace"]["refs"][0]["artifact_digest"] = artifact.digest
    try:
        if failure == "tampered":
            store._make_writable(artifact.path); (artifact.path / ".claude-plugin" / "plugin.json").write_text('{"name":"tampered"}')
        elif failure == "incompatible":
            outputs["deck-plugin-refs.prepare"]["installations"][0]["compatibility_json"] = '{"claude_code":">=9.0.0"}'
        with client:
            response = client.put(f"/api/decks/{DECK}/claude-plugins", headers=HEADERS, json={"refs": [{"plugin_installation_id": "plugin-1"}]})
        assert response.status_code == (200 if failure is None else 409)
        assert len(calls) == (2 if failure is None else 1)
        if failure is not None:
            assert response.json()["error"]["code"] == ("CLAUDE_PLUGIN_INTEGRITY_FAILED" if failure == "tampered" else "CLAUDE_PLUGIN_INCOMPATIBLE")
    finally:
        store._make_writable(artifact.path)


def test_current_user_oauth_scope_and_entity_grant_rules_remain(monkeypatch):
    client, calls, *_ = boundary(monkeypatch)
    with client:
        assert client.get(f"/api/decks/{DECK}/claude-plugins", headers={"authorization": "Bearer read-token"}).status_code == 200
        assert client.put(f"/api/decks/{DECK}/claude-plugins", headers={"authorization": "Bearer read-token"}, json={}).status_code == 403
        assert client.get(f"/api/decks/{DECK}/claude-plugins", headers={"authorization": "Bearer idg_" + "a" * 43}).status_code == 401
        client.cookies.set("access_token", "read-token")
        assert client.get(f"/api/decks/{DECK}/claude-plugins?token=read-token").status_code == 401
    assert len(calls) == 1
