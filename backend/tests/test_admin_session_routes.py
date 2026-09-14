# [Input] Actual Session public HTTP routes, strict Editor/Session DTOs and named fake-provider fixture.
# [Output] Ownership/shape/timezone/metrics/unknown-write contracts with all Dream DB session access fenced.
# [Pos] Provider-free public Session validation; real business acceptance remains separate.
# [Sync] 2026-09-15: cover all six domain operations, unchanged public projections and no side effects on failed writes.
from __future__ import annotations

import asyncio
import json
from copy import deepcopy

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from tests._admin_session_fixture import build_session_boundary, editor_state, full_session, preview_session
from services.admin_data.editor_models import EditorStateDTO
from services.admin_data.session_models import SessionSaveInputDTO
from routers import sessions as routes
from session_events import SessionEventBus


@pytest.fixture
def boundary(monkeypatch):
    import database
    def forbidden(*args, **kwargs):
        pytest.fail("Session HTTP must not query Dream PG")
    for name in ("get_db", "save_session", "get_session", "get_sessions_batch", "list_sessions", "list_sessions_in_range", "get_all_sessions_with_text", "delete_session"):
        monkeypatch.setattr(database, name, forbidden)
    monkeypatch.setattr(routes, "session_event_bus", SessionEventBus())
    app, calls, outputs = build_session_boundary()
    return TestClient(app), calls, outputs


def request(client, method, path, **kwargs):
    return client.request(method, path, headers={"authorization": "Bearer write-token"}, **kwargs)


def test_list_and_range_keep_original_metadata_day_and_precise_time(boundary):
    client, calls, _ = boundary
    response = request(client, "GET", "/api/sessions?timezone=Asia/Shanghai")
    expected = preview_session()
    expected.pop("text")
    assert response.json() == {"sessions": [{**expected, "date_key": "2026-08-31"}]}
    response = request(client, "GET", "/api/sessions/range?start_date=2026-08-30&end_date=2026-08-31&timezone=America/Los_Angeles")
    assert response.json()["sessions"][0]["date_key"] == "2026-08-30"
    assert calls[-1][1] == {"start_date": "2026-08-30", "end_date": "2026-08-31", "include_text": False}


def test_full_get_batch_and_missing_keep_public_shape(boundary):
    client, calls, outputs = boundary
    assert request(client, "GET", "/api/sessions/session-1").json() == full_session()
    assert request(client, "POST", "/api/sessions/batch", json={"ids": ["session-1", "session-1"]}).json() == {"sessions": [full_session()]}
    before = len(calls)
    assert request(client, "POST", "/api/sessions/batch", json={"ids": []}).json() == {"sessions": []}
    assert len(calls) == before
    outputs["session.get"] = {"session": None}
    missing = request(client, "GET", "/api/sessions/missing")
    assert missing.status_code == 404 and missing.json() == {"detail": "Session not found"}


def test_aggregate_retains_text_metrics_without_exposing_prose(boundary):
    client, calls, outputs = boundary
    original = outputs["session.text-list"]["sessions"][0]
    outputs["session.text-list"]["sessions"] = [original,
        {**original, "id": "empty", "text": "", "updated_at": "2026-09-01T00:00:00Z"}]
    response = request(client, "GET", "/api/sessions/aggregate?timezone=Asia/Shanghai")
    assert response.status_code == 200
    assert response.json()["stats"] == {"total_days": 2, "total_entries": 1, "total_words": 3}
    assert response.json()["sessions"][0]["word_count"] == 2 and "text" not in response.json()["sessions"][0]
    assert calls[-1][0:2] == ("session.text-list", {})


@pytest.mark.parametrize("path", ["/api/sessions?timezone=Missing/Zone", "/api/sessions/aggregate?timezone=Missing/Zone", "/api/sessions/range?start_date=2026-02-30"])
def test_invalid_calendar_input_fails_before_data_request(boundary, path):
    client, calls, _ = boundary
    assert request(client, "GET", path).status_code == 400 and not calls


def test_save_omits_optional_state_fields_and_keeps_null_name_labels(boundary):
    client, calls, _ = boundary
    state = {**editor_state(), "selectedState": None}
    response = request(client, "POST", "/api/sessions", json={"session_id": "session-1", "editor_state": state})
    assert response.status_code == 200 and response.json() == {"success": True}
    assert calls[-1][1] == {"session_id": "session-1", "editor_state": state, "name": None, "labels": None, "created_at": None}
    assert request(client, "DELETE", "/api/sessions/session-1").json() == {"success": True}


@pytest.mark.parametrize("method,path,event_type", [("POST", "/api/sessions", "session_updated"), ("DELETE", "/api/sessions/session-1", "session_deleted")])
def test_confirmed_writes_publish_only_the_current_users_edit_event(boundary, method, path, event_type):
    client, calls, _ = boundary
    async def scenario():
        bus = routes.session_event_bus
        current, other = await bus.subscribe("42"), await bus.subscribe("43")
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=client.app), base_url="https://dream.example") as api:
                kwargs = {"json": {"session_id": "session-1", "editor_state": editor_state()}} if method == "POST" else {}
                response = await api.request(method, path, headers={"authorization": "Bearer write-token"}, **kwargs)
            assert response.status_code == 200
            event = await asyncio.wait_for(current.get(), 1)
            assert (event.type, event.session_id, event.user_id, event.source) == (event_type, "session-1", "42", "api")
            assert other.empty() and len(calls) == 1
        finally:
            await bus.unsubscribe("42", current)
            await bus.unsubscribe("43", other)
    asyncio.run(scenario())


@pytest.mark.parametrize("state_patch", [{"id": "other"}, {"unexpected": "private prose"}, {"writingThreadId": None}, {"createdAt": None}, {"cells": [{"id": "text-1", "type": "text", "content": 123}]}])
def test_invalid_editor_input_is_closed_and_does_not_send_private_values(boundary, state_patch):
    client, calls, _ = boundary
    response = request(client, "POST", "/api/sessions", json={"session_id": "session-1", "editor_state": {**editor_state(), **state_patch}})
    assert response.status_code == 400 and not calls and "private prose" not in response.text


@pytest.mark.parametrize("method,path,operation", [("POST", "/api/sessions", "session.save"), ("DELETE", "/api/sessions/session-1", "session.delete")])
def test_unknown_writes_keep_original_id_no_retry_and_no_edit_event(boundary, monkeypatch, method, path, operation):
    client, calls, outputs = boundary
    published = []
    async def publish(event):
        published.append(event)
    monkeypatch.setattr(routes.session_event_bus, "publish", publish)
    outputs[operation] = httpx.ReadTimeout("synthetic private diagnostic")
    kwargs = {"json": {"session_id": "session-1", "editor_state": editor_state()}} if method == "POST" else {}
    response = request(client, method, path, **kwargs)
    assert response.status_code == 504 and response.json()["detail"] == {"error_code": "ADMIN_TIMEOUT", "request_id": calls[0][2], "outcome_unknown": True}
    assert len(calls) == 1 and not published and "private" not in response.text


@pytest.mark.parametrize("code,status", [("ENTITY_NOT_FOUND", 404), ("DELEGATION_ENTITY_DENIED", 403), ("EDITOR_STATE_INVALID", 503)])
def test_admin_domain_errors_keep_safe_status_and_no_fallback(boundary, code, status):
    client, calls, outputs = boundary
    outputs["session.get"] = (status, code)
    response = request(client, "GET", "/api/sessions/session-1")
    assert response.status_code == status and response.json()["detail"]["error_code"] == code
    assert "private" not in response.text and len(calls) == 1


def test_get_and_batch_reject_response_identity_mismatch(boundary):
    client, _, outputs = boundary
    outputs["session.get"] = {"session": full_session("other")}
    assert request(client, "GET", "/api/sessions/session-1").status_code == 503
    outputs["session.batch"] = {"sessions": [full_session("other")]}
    assert request(client, "POST", "/api/sessions/batch", json={"ids": ["session-1"]}).status_code == 503


def test_no_cookie_token_or_read_only_mutation_bypasses_current_dependency(boundary):
    client, calls, _ = boundary
    client.cookies.set("access_token", "write-token")
    assert client.get("/api/sessions?token=write-token").status_code == 401 and not calls
    response = client.delete("/api/sessions/session-1", headers={"authorization": "Bearer read-only"})
    assert response.status_code == 403 and not calls


def test_all_editor_cell_variants_and_optional_values_round_trip():
    state = editor_state()
    state["cells"].extend([
        {"id": "widget-1", "type": "widget", "widgetType": "chat", "data": {"enabled": True, "empty": None}},
        {"id": "suggestion-1", "type": "writing-suggestion", "content": "建议", "status": "failed", "anchor": {"textCellId": "text-1", "textSnapshot": "正文"},
            "createdAt": "2026-09-15T00:00:00.123456Z", "updatedAt": "2026-09-15T00:00:01Z", "error": {"code": "ERROR", "message": "说明", "retryable": True}, "requestId": "request-1", "previousContent": "旧建议"},
    ])
    state["commentors"] = [{"id": "comment-1", "phrase": "正文", "comment": "评论", "voice": "声音", "icon": "ink", "color": "blue", "computedAt": 1,
        "textSnapshot": "正文", "chatHistory": [{"role": "user", "content": "回复", "timestamp": 2}], "feedback": "star"}]
    state["tasks"] = [{"id": "task-1", "type": "thinking", "message": "处理中", "startedAt": 1}]
    state["weightPath"] = [{"timestamp": 1, "text": "正文", "weight": 2, "delta": 2, "energy": 2}]
    assert json.loads(EditorStateDTO.model_validate(state).model_dump_json()) == state
    invalid = deepcopy(state)
    invalid["commentors"][0]["computedAt"] = True
    with pytest.raises(ValidationError):
        EditorStateDTO.model_validate(invalid)
    invalid["commentors"][0]["computedAt"] = float("inf")
    with pytest.raises(ValidationError):
        EditorStateDTO.model_validate(invalid)


def test_session_save_nullable_fields_are_required():
    with pytest.raises(ValidationError):
        SessionSaveInputDTO.model_validate({"session_id": "session-1", "editor_state": editor_state()})
