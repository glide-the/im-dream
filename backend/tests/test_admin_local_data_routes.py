# [Input] Registry101 contracts, legacy localStorage payloads and the three public Auth routes.
# [Output] Strict DTO, safe parsing, accepted-count, receipt recovery and Dream-DB fence evidence.
# [Pos] Provider-free local-data consumer/route harness; no PostgreSQL, browser or real account.
# [Sync] 2026-09-15: bind Dream imports and first-login completion to Admin c051a58e.
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from routers import auth as auth_routes
from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.local_data_import import (
    COMPLETE_FIRST_LOGIN,
    IMPORT_LOCAL_DATA,
    LOCAL_DATA_IMPORT_OPERATIONS,
    LocalDataImportInputDTO,
    LocalDataImportOutputDTO,
    LocalDataPictureDTO,
    LocalDataPreferencesDTO,
    LocalDataReportDTO,
    LocalDataSessionDTO,
)
from services.admin_data.request_auth import AdminRequestAuth
from services.admin_data.workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS
from tests.test_admin_request_auth import Verifier


HEADERS = {"authorization": "Bearer write-token"}


def _forbidden(*_args, **_kwargs):
    pytest.fail("Public local-data routes must not use Dream PostgreSQL")


def _accepted_counts(value: dict) -> dict:
    preferences = value["preferences"]
    preference_count = 0
    if preferences is not None:
        preference_count += int(
            preferences["voice_configs"] is not None
            and bool(json.loads(preferences["voice_configs"]))
        )
        preference_count += int(bool(preferences["meta_prompt"]))
        preference_count += int(
            preferences["state_config"] is not None
            and bool(json.loads(preferences["state_config"]))
        )
        preference_count += int(bool(preferences["selected_state"]))
    return {
        "sessions": len(value["sessions"]),
        "pictures": len(value["pictures"]),
        "preferences": preference_count,
        "reports": len(value["reports"]),
    }


def boundary(monkeypatch):
    import database

    for name in ("get_db", "import_user_data", "set_first_login_completed"):
        monkeypatch.setattr(database, name, _forbidden)
    config = AdminDataConfig(
        base_url="https://admin.example",
        issuer="https://admin.example/api/auth",
        resource="https://dream.example/api",
        service_client_id="dream-service",
        service_secret="s" * 32,
    )
    state = {
        "calls": [],
        "unknown": set(),
        "receipt_ids": [],
        "missing_capability": False,
    }
    schemas = [item.model_dump() for item in WORKFLOW_SCHEMA_REQUIREMENTS]
    operations = [item.capability.model_dump() for item in LOCAL_DATA_IMPORT_OPERATIONS]

    def handler(request: httpx.Request) -> httpx.Response:
        request_id = request.headers["x-request-id"]
        UUID(request_id)
        if request.url.path.endswith("/capabilities"):
            advertised = [] if state["missing_capability"] else operations
            value = {
                "version": "1",
                "auth": {
                    "issuer": config.issuer,
                    "jwks_uri": config.jwks_uri,
                    "resource": config.resource,
                    "algorithm": "ES256",
                    "clients": {
                        "browser": "dream-browser",
                        "device": "dream-device",
                    },
                    "scopes": ["dream:read", "dream:write"],
                    "delegations": [],
                },
                "schema_capabilities": schemas,
                "operations": advertised,
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
            state["receipt_ids"].append((operation, request_id))
            result = (
                {
                    "success": True,
                    "imported": {
                        "sessions": 1,
                        "pictures": 0,
                        "preferences": 0,
                        "reports": 0,
                    },
                }
                if operation == IMPORT_LOCAL_DATA.capability.name
                else {"success": True, "first_login_completed": 1}
            )
            value = {
                "request_id": request_id,
                "status": "committed",
                "operation": operation,
                "result": result,
            }
        else:
            operation = request.url.path.rsplit("/", 1)[-1]
            body = json.loads(request.content)
            assert set(body) == {"request_id", "input"}
            assert body["request_id"] == request_id
            assert not {
                "user_id",
                "subject",
                "actor",
                "sql",
                "table",
                "column",
            } & body["input"].keys()
            assert request.headers["authorization"] == "Bearer write-token"
            assert request.headers["x-ink-dream-credential"] == "s" * 32
            assert "cookie" not in request.headers
            state["calls"].append((operation, body["input"], request_id))
            if operation in state["unknown"]:
                raise httpx.ReadTimeout("synthetic response loss", request=request)
            value = (
                {"success": True, "imported": _accepted_counts(body["input"])}
                if operation == IMPORT_LOCAL_DATA.capability.name
                else {"success": True, "first_login_completed": 1}
            )
        return httpx.Response(
            200,
            json={"request_id": request_id, "data": value},
        )

    admin_client = AdminDataClient(
        config,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        operations=LOCAL_DATA_IMPORT_OPERATIONS,
    )
    app = FastAPI()
    app.state.admin_request_auth = AdminRequestAuth(
        config,
        client=admin_client,
        verifier=Verifier(),
    )
    app.include_router(auth_routes.router)
    return TestClient(app), state


def test_import_normalizes_all_categories_and_uses_admin_accepted_counts(monkeypatch):
    client, state = boundary(monkeypatch)
    payload = {
        "currentSession": '{"counter":9007199254740993,"float":1.0}',
        "calendarEntries": json.dumps({
            "2026-09-15": [{
                "id": "calendar-1",
                "firstLine": "Entry",
                "state": {"counter": 9_007_199_254_740_993, "float": 1.0},
            }],
        }),
        "dailyPictures": json.dumps([{
            "date": "2026-09-15",
            "base64": "data:image/png;base64,AA==",
            "prompt": "prompt",
        }]),
        "voiceCustomizations": '{"counter":9007199254740993,"float":1.0}',
        "metaPrompt": "meta",
        "stateConfig": '{"state":1.0}',
        "selectedState": "focused",
        "analysisReports": '[{"type":"patterns","data":{"counter":9007199254740993,"float":1.0},"allNotes":"notes","timestamp":1757913600123}]',
        "oldDocument": '{"document":"legacy"}',
    }
    with client:
        response = client.post("/api/import-local-data", headers=HEADERS, json=payload)
    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "imported": {
            "sessions": 3,
            "pictures": 1,
            "preferences": 4,
            "reports": 1,
        },
    }
    operation, value, request_id = state["calls"][-1]
    assert operation == IMPORT_LOCAL_DATA.capability.name
    UUID(request_id)
    assert value["sessions"][0]["editor_state"] == payload["currentSession"]
    assert value["sessions"][1]["editor_state"] == '{"counter":9007199254740993,"float":1.0}'
    assert value["preferences"]["voice_configs"] == payload["voiceCustomizations"]
    assert value["reports"] == [{
        "type": "patterns",
        "data": '{"counter":9007199254740993,"float":1.0}',
        "all_notes": "notes",
        "timestamp": "2025-09-15T05:20:00.123Z",
    }]


def test_malformed_categories_are_independent_and_never_echoed(monkeypatch, caplog):
    client, state = boundary(monkeypatch)
    payload = {
        "currentSession": '{"valid":true}',
        "calendarEntries": '{"SECRET_CALENDAR"',
        "dailyPictures": '[{"date":"invalid","base64":"SECRET_IMAGE"}]',
        "voiceCustomizations": '["SECRET_VOICE"]',
        "stateConfig": '{"valid":1.0}',
        "analysisReports": '[{"data":{"SECRET_REPORT":1},"timestamp":"bad"}]',
    }
    with client:
        response = client.post("/api/import-local-data", headers=HEADERS, json=payload)
    assert response.status_code == 200
    assert response.json()["imported"] == {
        "sessions": 1,
        "pictures": 0,
        "preferences": 1,
        "reports": 0,
    }
    value = state["calls"][-1][1]
    assert [item["id"] for item in value["sessions"]] == ["current-session"]
    assert value["preferences"] == {
        "voice_configs": None,
        "meta_prompt": None,
        "state_config": '{"valid":1.0}',
        "selected_state": None,
    }
    assert "SECRET_" not in caplog.text


def test_report_without_legacy_timestamp_uses_one_request_clock(monkeypatch):
    client, state = boundary(monkeypatch)
    monkeypatch.setattr(
        auth_routes,
        "_utc_now",
        lambda: datetime(2026, 9, 15, 8, 9, 10, 123456, tzinfo=timezone.utc),
    )
    with client:
        response = client.post(
            "/api/import-local-data",
            headers=HEADERS,
            json={
                "analysisReports": json.dumps([
                    {"type": "echoes", "data": {}, "allNotes": "one"},
                    {"type": "traits", "data": {}, "allNotes": "two"},
                ]),
            },
        )
    assert response.status_code == 200
    assert response.json()["imported"]["reports"] == 2
    assert [item["timestamp"] for item in state["calls"][-1][1]["reports"]] == [
        "2026-09-15T08:09:10.123Z",
        "2026-09-15T08:09:10.123Z",
    ]


def test_calendar_recovery_reuses_aggregate_and_preserves_public_shape(monkeypatch):
    client, state = boundary(monkeypatch)
    calendar = json.dumps({
        "2026-09-15": [{"id": "calendar-1", "state": {"id": "calendar-1"}}]
    })
    with client:
        response = client.post(
            "/api/import-calendar-recovery",
            headers=HEADERS,
            json={"calendarEntries": calendar},
        )
        invalid = client.post(
            "/api/import-calendar-recovery",
            headers=HEADERS,
            json={"calendarEntries": "SECRET_INVALID"},
        )
    assert response.status_code == 200
    assert response.json() == {"success": True, "imported": {"sessions": 1}}
    assert state["calls"][-1][1] == {
        "sessions": [{
            "id": "calendar-1",
            "name": "2026-09-15 - Untitled",
            "editor_state": '{"id":"calendar-1"}',
        }],
        "pictures": [],
        "preferences": None,
        "reports": [],
    }
    assert invalid.status_code == 400
    assert invalid.json() == {"detail": "Failed to parse calendar"}
    assert "SECRET_INVALID" not in invalid.text


def test_first_login_completion_keeps_public_response(monkeypatch):
    client, state = boundary(monkeypatch)
    with client:
        first = client.post("/api/mark-first-login-completed", headers=HEADERS)
        repeated = client.post("/api/mark-first-login-completed", headers=HEADERS)
    assert first.json() == repeated.json() == {"success": True}
    assert [item[0] for item in state["calls"]] == [
        COMPLETE_FIRST_LOGIN.capability.name,
        COMPLETE_FIRST_LOGIN.capability.name,
    ]
    assert all(item[1] == {} for item in state["calls"])


def test_unknown_import_result_uses_original_receipt_without_resend(monkeypatch):
    client, state = boundary(monkeypatch)
    state["unknown"].add(IMPORT_LOCAL_DATA.capability.name)
    with client:
        response = client.post(
            "/api/import-local-data",
            headers=HEADERS,
            json={"currentSession": '{"id":"current-session"}'},
        )
    assert response.status_code == 200
    assert response.json()["imported"]["sessions"] == 1
    writes = [item for item in state["calls"] if item[0] == "local-data.import"]
    assert len(writes) == 1
    assert state["receipt_ids"] == [("local-data.import", writes[0][2])]


def test_unknown_first_login_result_uses_original_receipt_without_resend(monkeypatch):
    client, state = boundary(monkeypatch)
    state["unknown"].add(COMPLETE_FIRST_LOGIN.capability.name)
    with client:
        response = client.post("/api/mark-first-login-completed", headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == {"success": True}
    writes = [
        item
        for item in state["calls"]
        if item[0] == COMPLETE_FIRST_LOGIN.capability.name
    ]
    assert len(writes) == 1
    assert state["receipt_ids"] == [
        (COMPLETE_FIRST_LOGIN.capability.name, writes[0][2])
    ]


def test_missing_registry101_operation_fails_before_business_write(monkeypatch):
    client, state = boundary(monkeypatch)
    state["missing_capability"] = True
    with client:
        response = client.post(
            "/api/import-local-data",
            headers=HEADERS,
            json={"currentSession": '{"valid":true}'},
        )
    assert response.status_code == 503
    assert state["calls"] == []


@pytest.mark.parametrize(
    "path,payload",
    [
        ("/api/import-local-data", {"user_id": "42"}),
        ("/api/import-local-data", {"sql": "SECRET SQL"}),
        (
            "/api/import-calendar-recovery",
            {"calendarEntries": "{}", "actor": "SECRET ACTOR"},
        ),
    ],
)
def test_public_import_requests_reject_unknown_selectors_without_echo(
    monkeypatch,
    path,
    payload,
):
    client, state = boundary(monkeypatch)
    with client:
        response = client.post(path, headers=HEADERS, json=payload)
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid authentication request"}
    assert "SECRET" not in response.text
    assert state["calls"] == []


def test_registry101_dtos_are_closed_and_preserve_raw_json_text():
    value = LocalDataImportInputDTO(
        sessions=[LocalDataSessionDTO(
            id="session-1",
            name=None,
            editor_state='{"counter":9007199254740993,"float":1.0}',
        )],
        pictures=[LocalDataPictureDTO(
            date="2026-09-15",
            image_base64="image",
            prompt=None,
        )],
        preferences=LocalDataPreferencesDTO(
            voice_configs='{"negativeZero":-0.0}',
            meta_prompt=None,
            state_config=None,
            selected_state=None,
        ),
        reports=[LocalDataReportDTO(
            type="patterns",
            data='{"counter":9007199254740993,"float":1.0}',
            all_notes="",
            timestamp="2025-09-15T05:20:00.123Z",
        )],
    )
    assert value.sessions[0].editor_state.endswith('"float":1.0}')
    assert value.preferences.voice_configs == '{"negativeZero":-0.0}'
    with pytest.raises(ValidationError):
        LocalDataImportInputDTO.model_validate({
            **value.model_dump(),
            "user_id": "42",
        })
    with pytest.raises(ValidationError):
        LocalDataImportInputDTO.model_validate({
            **value.model_dump(),
            "sessions": [value.sessions[0].model_dump()] * 2,
        })
    with pytest.raises(ValidationError):
        LocalDataReportDTO(
            type="patterns",
            data="[]",
            all_notes="",
            timestamp="1757913600123",
        )
    with pytest.raises(ValidationError):
        LocalDataImportOutputDTO.model_validate({
            "success": True,
            "imported": {
                "sessions": True,
                "pictures": 0,
                "preferences": 0,
                "reports": 0,
            },
        })


def test_production_request_owner_registers_both_registry101_operations():
    config = AdminDataConfig(
        base_url="https://admin.example",
        issuer="https://admin.example/api/auth",
        resource="https://dream.example/api",
        service_client_id="dream-service",
        service_secret="s" * 32,
    )
    owner = AdminRequestAuth(config)
    try:
        registered = owner.client._operations
        assert registered[IMPORT_LOCAL_DATA.capability.name] is IMPORT_LOCAL_DATA
        assert registered[COMPLETE_FIRST_LOGIN.capability.name] is COMPLETE_FIRST_LOGIN
    finally:
        owner.close()
