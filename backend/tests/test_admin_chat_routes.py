# [Input] Public production Chat routes with the real Admin DTO transport and explicit fake auth/runtime providers.
# [Output] HTTP CRUD/history/process/cursor/permission/unknown-write regressions with Dream DB fenced off.
# [Pos] Provider-free route contracts; no duplicate API, state machine, SSE parser or database fixture.
# [Sync] 2026-09-15: gate public streaming on the bound server grant and atomic user reservation before runtime.
# [Sync] 2026-09-15: verify exact Editor grant creation and pre-SSE owner cleanup on failure.
# [Sync] 2026-09-15: verify Admin Workflow read precedes message/SSE and supplies immutable Service snapshot.
# [Sync] 2026-09-15: read one OAuth SystemConfig snapshot before model and attachment preparation.
# [Sync] 2026-09-14: verify actual production HTTP adapters and existing response projections.
from __future__ import annotations

import json
import sys
import types
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError, OAuthPrincipalClaims
from services.admin_data.chat_data import CHAT_OPERATIONS
from services.admin_data.profile_data import CURRENT_PROFILE
from services.admin_data.request_auth import AdminRequestAuth
from services.admin_data.workflow_data import RESOLVE_WORKFLOW_CONTEXT, WORKFLOW_SCHEMA_REQUIREMENTS
from services.admin_data.delegation import DELEGATION_CAPABILITIES, RUNTIME_SCHEMA_REQUIREMENTS
from services.admin_data.editor_runtime import EDITOR_RUNTIME_CAPABILITIES
from services.admin_data.user_message_data import PERSIST_USER_MESSAGE
from services.admin_data.system_config_data import SYSTEM_CONFIG_OPERATIONS


class StaticVerifier:
    def verify(self, token, *, required_scopes):
        scopes = frozenset({"dream:read"} if token == "read-only" else {"dream:read", "dream:write"})
        if not required_scopes <= scopes:
            raise AdminDataError("INSUFFICIENT_SCOPE", 403)
        return OAuthPrincipalClaims("opaque-subject", "dream-browser", scopes, "test-jti", 100, 400)


def thread_value():
    return {"id": "owned-thread", "user_id": "42", "title": "Saved conversation", "deck_id": None, "voice_id": None,
        "created_at": "2026-09-14T00:00:00.123456Z", "updated_at": None, "claude_session_id": None, "agent_contract_version": None}


def message_value(*, final=False, message_id="message-1", created_at="2026-09-14T00:00:00.123456Z"):
    return {"id": message_id, "role": "assistant", "parts": [{"type": "text", "text": "final"}] if final else [{"type": "reasoning", "text": "process"}, {"type": "text", "text": "final"}],
        "metadata": {"turnId": "turn-1", "turnStatus": "completed", "finalPartIndex": 1}, "metadata_decode_error": False,
        "created_at": created_at, "history_final_text": "final", "history_process_available": True, "history_projection_version": 1}


@pytest.fixture
def boundary(monkeypatch):
    # Import the real router with explicit runtime/resource providers. No configured
    # composition-root policy reader or runtime is invoked by this route harness.
    factory = types.SimpleNamespace(closed=[])
    factory.close_thread = lambda thread_id: factory.closed.append(thread_id)
    monkeypatch.setitem(sys.modules, "agent_factory", types.SimpleNamespace(claude_agent_thread_factory=factory))
    import routers.claude_agent as routes
    import database
    monkeypatch.setattr(routes, "claude_agent_thread_factory", factory)
    def forbidden(*args, **kwargs):
        raise AssertionError("Migrated Chat HTTP route must not query Dream PG")
    assert not hasattr(database, "get_deck_with_voices")
    for name in ("get_db", "get_chat_thread", "create_chat_thread", "list_chat_threads", "list_chat_threads_for_search", "delete_chat_thread", "list_chat_messages", "list_chat_message_page", "get_latest_chat_message_id", "get_chat_message_process_detail", "save_chat_message", "get_system_config"):
        monkeypatch.setattr(database, name, forbidden)
    async def bindings(user_id):
        return {}
    monkeypatch.setattr(routes, "_load_current_user_mcp_app_resource_bindings", bindings)
    async def model_selection(user_id, client_model_alias, system_config):
        assert system_config == {"model": "explicit-fake-model", "workspace_enabled": True}
        return "explicit-fake-model"
    monkeypatch.setattr(routes, "_resolve_platform_model_selection", model_selection)
    factory.run_requests = []
    async def frames(run_request):
        factory.run_requests.append(run_request)
        yield ": explicit-fake-runtime\n\n"
    factory.run_streaming = frames
    config = AdminDataConfig(base_url="https://admin.example", issuer="https://admin.example/api/auth", resource="https://dream.example/api", service_secret="s" * 32, service_client_id="dream-service")
    summary = {key: value for key, value in thread_value().items() if key in {"id", "title", "deck_id", "voice_id", "created_at", "updated_at"}}
    outputs = {
        "chat-thread.get": {"thread": thread_value()}, "chat-thread.create": {"thread_id": "created-thread", "deck_id": None, "voice_id": None},
        "chat-thread.list": {"threads": [summary]}, "chat-thread.search": {"threads": [{**summary, "messages_text": "Saved conversation"}]},
        "chat-thread.delete": {"changed": True}, "chat-message.list": {"messages": [message_value()]},
        "chat-message.persist": {"message_id": "public-message-1"},
        "workflow-context.resolve": {"context": None},
        "user-system-config.get": {"config_json": '{"model":"explicit-fake-model","workspace_enabled":true}'},
        "chat-user-message.persist": {"message_id": "public-message-1", "confirmation_preserved": False},
        "runtime-delegation.create": {"token": "idg_" + "a" * 43, "purpose": "server-persistence", "thread_id": "owned-thread", "run_id": None,
            "editor_session_id": None, "scopes": ["dream:read", "dream:write"], "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
            "maximum_expires_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()},
        "chat-message.page": {"messages": [message_value(final=True)], "has_more": True, "latest_message_id": "message-1"},
        "chat-message.latest": {"message_id": "message-1"}, "chat-message.process-detail": {"message": message_value()},
    }
    calls = []
    def handler(request):
        request_id = request.headers["x-request-id"]
        assert request.headers["X-Ink-Dream-Service"] == config.service_client_id
        assert request.headers["X-Ink-Dream-Credential"] == config.service_secret
        if request.url.path.endswith("/capabilities"):
            value = {"version": "1", "auth": {"issuer": config.issuer, "jwks_uri": config.jwks_uri, "resource": config.resource, "algorithm": "ES256", "clients": {"browser": "dream-browser", "device": "dream-device"}, "scopes": ["dream:read", "dream:write"], "delegations": [item.model_dump() for item in DELEGATION_CAPABILITIES]},
                "schema_capabilities": [item.model_dump() for item in RUNTIME_SCHEMA_REQUIREMENTS], "operations": [op.capability.model_dump() for op in (*CHAT_OPERATIONS, *SYSTEM_CONFIG_OPERATIONS, CURRENT_PROFILE, RESOLVE_WORKFLOW_CONTEXT, PERSIST_USER_MESSAGE)] + [op.model_dump() for op in EDITOR_RUNTIME_CAPABILITIES]}
        elif request.url.path.endswith("/principal"):
            value = {"subject": "opaque-subject", "canonical_user_id": "42", "client_id": "dream-browser", "scopes": ["dream:read"] if request.headers["authorization"] == "Bearer read-only" else ["dream:read", "dream:write"], "status": "active"}
        else:
            operation = "runtime-delegation.create" if request.url.path.endswith("/runtime-delegations") else request.url.path.rsplit("/", 1)[1]
            payload = json.loads(request.content)
            assert set(payload) == {"request_id", "input"} and payload["request_id"] == request_id
            assert "user_id" not in payload["input"]
            calls.append((operation, payload["input"], request_id))
            value = outputs[operation]
            if callable(value):
                value = value(payload["input"], request_id)
            if isinstance(value, Exception): raise value
            if isinstance(value, tuple):
                status, code = value
                return httpx.Response(status, json={"request_id": request_id, "error": {"code": code, "message": "safe"}})
        return httpx.Response(200, json={"request_id": request_id, "data": value})
    client = AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(handler)), operations=(*CHAT_OPERATIONS, *SYSTEM_CONFIG_OPERATIONS, CURRENT_PROFILE, RESOLVE_WORKFLOW_CONTEXT, PERSIST_USER_MESSAGE))
    app = FastAPI()
    app.state.admin_request_auth = AdminRequestAuth(config, client=client, verifier=StaticVerifier())
    app.include_router(routes.router)
    return TestClient(app), outputs, calls, factory


def request(client, method, path, **kwargs):
    return client.request(method, path, headers={"authorization": "Bearer read-write"}, **kwargs)


def test_create_thread_uses_admin_owned_deck_voice_transaction(boundary):
    client, outputs, calls, _ = boundary
    outputs["chat-thread.create"] = {"thread_id": "created-thread", "deck_id": "owned-deck", "voice_id": "owned-voice"}
    response = request(client, "POST", "/api/claude-agent/threads", json={"deckId": "owned-deck", "voiceId": "owned-voice", "title": "Title"})
    assert response.status_code == 200 and response.json() == outputs["chat-thread.create"]
    assert calls[0][:2] == ("chat-thread.create", {"deck_id": "owned-deck", "voice_id": "owned-voice", "title": "Title"})


def test_voice_without_deck_preserves_422_before_domain_write(boundary):
    client, _, calls, _ = boundary
    response = request(client, "POST", "/api/claude-agent/threads", json={"voiceId": "owned-voice"})
    assert response.status_code == 422 and not calls


@pytest.mark.parametrize("path", ["/api/claude-agent/chat-history", "/api/claude-agent/threads?limit=5&offset=2"])
def test_thread_lists_preserve_public_summary_and_scope(boundary, path):
    client, _, calls, _ = boundary
    response = request(client, "GET", path)
    assert response.status_code == 200 and response.json()["threads"][0]["title"] == "Saved conversation"
    assert "user_id" not in response.json()["threads"][0]
    assert calls[0][0] == "chat-thread.list"


def test_thread_search_keeps_existing_retriever(boundary):
    client, _, calls, _ = boundary
    response = request(client, "GET", "/api/claude-agent/threads?query=Saved&search_scope=all")
    assert response.status_code == 200 and response.json()["threads"]
    assert calls[0][0] == "chat-thread.search" and "retrieval" in response.json()


def test_delete_closes_runtime_only_after_admin_commit(boundary):
    client, outputs, calls, factory = boundary
    response = request(client, "DELETE", "/api/claude-agent/threads/owned-thread")
    assert response.status_code == 200 and response.json() == {"ok": True}
    assert calls[0][0] == "chat-thread.delete" and factory.closed == ["owned-thread"]
    outputs["chat-thread.delete"] = {"changed": False}
    response = request(client, "DELETE", "/api/claude-agent/threads/not-owned")
    assert response.status_code == 404 and factory.closed == ["owned-thread"]


def test_history_preserves_canonical_parts_without_dream_pg(boundary):
    client, _, calls, _ = boundary
    response = request(client, "GET", "/api/claude-agent/threads/owned-thread/messages")
    assert response.status_code == 200
    assert len(response.json()["messages"][0]["parts"]) == 2
    assert [call[0] for call in calls] == ["chat-thread.get", "chat-message.list"]


def test_page_cursor_preserves_microseconds_and_thread_binding(boundary):
    client, _, calls, _ = boundary
    response = request(client, "GET", "/api/claude-agent/threads/owned-thread/messages?limit=20")
    assert response.status_code == 200
    payload = response.json()
    assert payload["has_more"] and len(payload["messages"][0]["parts"]) == 1
    assert payload["messages"][0]["projection_version"] == 1
    cursor = payload["next_cursor"]
    response = request(client, "GET", "/api/claude-agent/threads/owned-thread/messages", params={"limit": 20, "cursor": cursor})
    assert response.status_code == 200
    assert calls[-1][1]["before"] == {"id": "message-1", "created_at": "2026-09-14T00:00:00.123456+00:00"}
    before_pages = sum(call[0] == "chat-message.page" for call in calls)
    response = request(client, "GET", "/api/claude-agent/threads/different-thread/messages", params={"limit": 20, "cursor": cursor})
    assert response.status_code == 400 and sum(call[0] == "chat-message.page" for call in calls) == before_pages


def test_known_latest_avoids_page_read(boundary):
    client, _, calls, _ = boundary
    response = request(client, "GET", "/api/claude-agent/threads/owned-thread/messages?limit=20&known_latest_message_id=message-1")
    assert response.status_code == 200 and response.json()["unchanged"]
    assert [call[0] for call in calls] == ["chat-thread.get", "chat-message.latest"]


def test_null_cursor_time_and_large_final_are_preserved(boundary):
    client, outputs, calls, _ = boundary
    text = "完整正文" * 40_000
    value = message_value(final=True, created_at=None)
    value["parts"][0]["text"] = text; value["history_final_text"] = text
    outputs["chat-message.page"]["messages"] = [value]
    response = request(client, "GET", "/api/claude-agent/threads/owned-thread/messages?limit=20")
    assert response.status_code == 200 and response.json()["messages"][0]["parts"][0]["text"] == text
    response = request(client, "GET", "/api/claude-agent/threads/owned-thread/messages", params={"limit": 20, "cursor": response.json()["next_cursor"]})
    assert response.status_code == 200 and calls[-1][1]["before"] == {"id": "message-1", "created_at": None}


def test_process_detail_uses_admin_canonical_projection(boundary):
    client, outputs, calls, _ = boundary
    response = request(client, "GET", "/api/claude-agent/threads/owned-thread/messages/message-1/process")
    assert response.status_code == 200 and len(response.json()["parts"]) == 2
    assert calls[-1][:2] == ("chat-message.process-detail", {"thread_id": "owned-thread", "message_id": "message-1"})
    outputs["chat-message.process-detail"] = {"message": None}
    assert request(client, "GET", "/api/claude-agent/threads/owned-thread/messages/message-1/process").status_code == 404


def test_owner_absence_and_readonly_scope_fail_closed(boundary):
    client, outputs, calls, _ = boundary
    outputs["chat-thread.get"] = {"thread": None}
    assert request(client, "GET", "/api/claude-agent/threads/not-owned/messages").status_code == 404
    assert [call[0] for call in calls] == ["chat-thread.get"]
    response = client.post("/api/claude-agent/threads", headers={"authorization": "Bearer read-only"}, json={})
    assert response.status_code == 403 and len(calls) == 1


@pytest.mark.parametrize("failure,status", [((409, "CHAT_MESSAGE_IDENTITY_CONFLICT"), 409), (httpx.ReadTimeout("safe timeout"), 504)])
def test_writes_do_not_retry_and_report_original_unknown_request(boundary, failure, status):
    client, outputs, calls, _ = boundary
    outputs["chat-thread.create"] = failure
    response = request(client, "POST", "/api/claude-agent/threads", json={})
    assert response.status_code == status and len(calls) == 1
    assert response.json()["detail"]["request_id"] == calls[0][2]
    assert response.json()["detail"]["outcome_unknown"] is (status == 504)


def test_stream_reserves_original_user_identity_through_admin_before_runtime(boundary):
    client, _, calls, factory = boundary
    response = request(client, "POST", "/api/claude-agent", json={"id": "owned-thread", "message": {"id": "public-message-1", "parts": [{"type": "text", "text": "Original user message"}]}})
    assert response.status_code == 200 and response.headers["content-type"].startswith("text/event-stream")
    assert response.text == ": explicit-fake-runtime\n\n"
    assert [call[0] for call in calls] == ["chat-thread.get", "user-system-config.get", "workflow-context.resolve", "runtime-delegation.create", "chat-user-message.persist"]
    assert calls[-2][1] == {"purpose": "server-persistence", "thread_id": "owned-thread", "run_id": None, "editor_session_id": None, "scopes": ["dream:read", "dream:write"]}
    assert calls[-1][1] == {"thread_id": "owned-thread", "message_id": "public-message-1", "parts_json": '[{"type":"text","text":"Original user message"}]', "metadata_json": None, "title_candidate": "Original user message"}
    assert len(factory.run_requests) == 1 and factory.run_requests[0].message_id == "public-message-1"
    resolution = factory.run_requests[0].admin_workflow_resolution
    assert resolution is not None and resolution.context_for(actor_id="42", thread_id="owned-thread") is None


def test_stream_identity_conflict_preserves_public_409_without_starting_runtime(
    boundary, monkeypatch
):
    from services.admin_data.editor_runtime import AdminEditorRuntime
    from services.admin_data.turn_persistence import AdminTurnPersistence

    client, outputs, calls, factory = boundary
    closed = []
    monkeypatch.setattr(AdminTurnPersistence, "close", lambda self: closed.append("turn"))
    monkeypatch.setattr(AdminEditorRuntime, "close", lambda self: closed.append("editor"))
    outputs["chat-user-message.persist"] = (409, "CHAT_MESSAGE_IDENTITY_CONFLICT")
    response = request(client, "POST", "/api/claude-agent", json={"id": "owned-thread", "message": {"id": "public-message-1", "parts": [{"type": "text", "text": "conflicting value"}]}})
    assert response.status_code == 409 and not factory.run_requests
    assert response.json()["detail"]["error_code"] == "CHAT_MESSAGE_IDENTITY_CONFLICT"
    assert response.json()["detail"]["message"] == "The message identifier is already bound."
    assert len(calls) == 5 and calls[-1][0] == "chat-user-message.persist"
    assert closed == ["turn", "editor"]


def test_editor_grant_is_exact_and_precedes_user_reservation(boundary):
    client, outputs, calls, factory = boundary

    def created(input_dto, _request_id):
        token_letter = "a" if input_dto["purpose"] == "server-persistence" else "b"
        return {
            **input_dto,
            "token": "idg_" + token_letter * 43,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
            "maximum_expires_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        }

    outputs["runtime-delegation.create"] = created
    response = request(client, "POST", "/api/claude-agent", json={
        "id": "owned-thread",
        "message": {"id": "public-message-1", "parts": [{"type": "text", "text": "edit"}]},
        "editor_state": {"id": "session-1"},
    })
    assert response.status_code == 200 and len(factory.run_requests) == 1
    assert [item[0] for item in calls] == [
        "chat-thread.get",
        "user-system-config.get",
        "workflow-context.resolve",
        "runtime-delegation.create",
        "runtime-delegation.create",
        "chat-user-message.persist",
    ]
    assert calls[4][1] == {
        "purpose": "editor-stdio",
        "thread_id": "owned-thread",
        "run_id": None,
        "editor_session_id": "session-1",
        "scopes": ["editor:read", "editor:write"],
    }
    run_request = factory.run_requests[0]
    run_request.admin_editor_runtime.close()
    run_request.admin_turn_persistence.close()


def test_editor_grant_failure_closes_existing_turn_owner(boundary, monkeypatch):
    from services.admin_data.turn_persistence import AdminTurnPersistence

    client, outputs, calls, factory = boundary
    closed = []
    monkeypatch.setattr(AdminTurnPersistence, "close", lambda self: closed.append(self))

    def created(input_dto, _request_id):
        if input_dto["purpose"] == "editor-stdio":
            return (404, "ENTITY_NOT_FOUND")
        return {
            **input_dto,
            "token": "idg_" + "a" * 43,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
            "maximum_expires_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        }

    outputs["runtime-delegation.create"] = created
    response = request(client, "POST", "/api/claude-agent", json={
        "id": "owned-thread",
        "message": {"id": "public-message-1", "parts": [{"type": "text", "text": "edit"}]},
        "editor_state": {"id": "missing-session"},
    })
    assert response.status_code == 404 and response.json()["detail"]["error_code"] == "ENTITY_NOT_FOUND"
    assert len(closed) == 1 and not factory.run_requests
    assert [item[0] for item in calls][-2:] == [
        "runtime-delegation.create",
        "runtime-delegation.create",
    ]


@pytest.mark.parametrize("code,status", [("DREAM_THREAD_BINDING_CONFLICT", 409), ("DREAM_SCOPE_REQUIRED", 403), ("ADMIN_UNAVAILABLE", 503)])
def test_workflow_read_failure_precedes_message_reservation_and_sse(boundary, code, status):
    client, outputs, calls, factory = boundary
    outputs["workflow-context.resolve"] = (status, code)
    response = request(client, "POST", "/api/claude-agent", json={"id": "owned-thread", "message": {"id": "public-message-1", "parts": [{"type": "text", "text": "Original user message"}]}})
    assert response.status_code == status and response.json()["detail"]["error_code"] == code
    assert [item[0] for item in calls] == ["chat-thread.get", "user-system-config.get", "workflow-context.resolve"]
    assert not factory.run_requests


def test_server_grant_failure_precedes_message_or_runtime(boundary):
    client, outputs, calls, factory = boundary
    outputs["runtime-delegation.create"] = (403, "DELEGATION_SCOPE_NOT_CONSENTED")
    response = request(client, "POST", "/api/claude-agent", json={"id": "owned-thread", "message": {"id": "public-message-1", "parts": [{"type": "text", "text": "Original user message"}]}})
    assert response.status_code == 403 and not factory.run_requests
    assert [item[0] for item in calls] == ["chat-thread.get", "user-system-config.get", "workflow-context.resolve", "runtime-delegation.create"]


def test_atomic_reservation_unknown_is_not_retried_or_started(boundary):
    client, outputs, calls, factory = boundary
    outputs["chat-user-message.persist"] = httpx.ReadTimeout("synthetic private diagnostic")
    response = request(client, "POST", "/api/claude-agent", json={"id": "owned-thread", "message": {"id": "public-message-1", "parts": [{"type": "text", "text": "Original user message"}]}})
    assert response.status_code == 504 and response.json()["detail"]["error_code"] == "ADMIN_TIMEOUT"
    assert response.json()["detail"]["outcome_unknown"] is True
    assert not factory.run_requests and sum(item[0] == "chat-user-message.persist" for item in calls) == 1
    assert "private" not in response.text
