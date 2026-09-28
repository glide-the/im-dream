# [Input] Public production Chat routes with the real Admin DTO transport and explicit fake auth/runtime providers.
# [Output] HTTP CRUD/history/process/cursor/permission/unknown-write regressions with Dream DB fenced off.
# [Pos] Provider-free route contracts; no duplicate API, state machine, SSE parser or database fixture.
# [Sync] 2026-09-28: exercise wait_threads completion/cursor/input wake and ordinary non-returning Thread creation.
# [Sync] 2026-09-29: require owner-scoped user-turn navigation to pair only public messages in their own range.
# [Sync] 2026-09-28: exercise create/list/read/send Thread Tool host behavior and stable running-Thread sends.
# [Sync] 2026-09-27: running or incomplete task messages cannot be projected as completed results.
# [Sync] 2026-09-27: verify owner-filtered task-session navigation links through the public Thread route.
# [Sync] 2026-09-27: verify side-task first-turn no-resume launch and retry-safe single claim.
# [Sync] 2026-09-26: expose an empty Admin queue snapshot and reject orphaned inputs before ordinary Chat dispatch.
# [Sync] 2026-09-17: carry user OAuth and confidential service OAuth as separate Bearers.
# [Sync] 2026-09-15: verify exact Editor grant creation and pre-SSE owner cleanup on failure.
# [Sync] 2026-09-15: verify Admin Workflow read precedes message/SSE and supplies immutable Service snapshot.
# [Sync] 2026-09-15: read one OAuth SystemConfig snapshot before model and attachment preparation.
# [Sync] 2026-09-16: verify OAuth model reads and distinct gateway/persistence purpose grants.
# [Sync] 2026-09-14: verify actual production HTTP adapters and existing response projections.
from __future__ import annotations

import json
import asyncio
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
        scopes = frozenset(
            {"dream:read"}
            if token == "read-only"
            else {
                "dream:read",
                "dream:write",
                "messages:create",
                "messages:count_tokens",
                "models:list",
            }
        )
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
    async def model_selection(user_id, client_model_alias, system_config, *, access_token):
        assert system_config == {"model": "explicit-fake-model", "workspace_enabled": True}
        assert access_token == "read-write"
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
        "chat-input.list": {"entries": []},
        "chat-input.transition": {"entry": {"message_id": "queued-message", "thread_id": "owned-thread", "queue_sequence": "1", "status": "cancelled", "revision": 2, "dispatch_turn_id": None, "created_at": "2026-09-26T00:00:00Z", "text": "new work"}},
        "workflow-context.resolve": {"context": None},
        "user-system-config.get": {"config_json": '{"model":"explicit-fake-model","workspace_enabled":true}'},
        "chat-user-message.persist": {"message_id": "public-message-1", "confirmation_preserved": False},
        "runtime-delegation.create": lambda input_dto, _request_id: {
            **input_dto,
            "token": "idg_" + ({"gateway-cli": "g", "server-persistence": "p", "editor-stdio": "e"}[input_dto["purpose"]] * 43),
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
            "maximum_expires_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        },
        "chat-message.page": {"messages": [message_value(final=True)], "has_more": True, "latest_message_id": "message-1"},
        "chat-message.latest": {"message_id": "message-1"}, "chat-message.process-detail": {"message": message_value()},
    }
    calls = []
    def handler(request):
        request_id = request.headers["x-request-id"]
        assert "x-ink-dream-service" not in request.headers
        assert "x-ink-dream-credential" not in request.headers
        if request.headers.get("authorization") != "Bearer fixture.service.access.token":
            assert request.headers["x-ink-dream-service-authorization"] == "Bearer fixture.service.access.token"
        else:
            assert "x-ink-dream-service-authorization" not in request.headers
        if request.url.path.endswith("/capabilities"):
            value = {"version": "1", "auth": {"issuer": config.issuer, "jwks_uri": config.jwks_uri, "resource": config.resource, "algorithm": "ES256", "clients": {"browser": "dream-browser", "device": "dream-device"}, "scopes": ["dream:read", "dream:write"], "delegations": [item.model_dump() for item in DELEGATION_CAPABILITIES]},
                "schema_capabilities": [item.model_dump() for item in RUNTIME_SCHEMA_REQUIREMENTS], "operations": [op.capability.model_dump() for op in (*CHAT_OPERATIONS, *SYSTEM_CONFIG_OPERATIONS, CURRENT_PROFILE, RESOLVE_WORKFLOW_CONTEXT, PERSIST_USER_MESSAGE)] + [op.model_dump() for op in EDITOR_RUNTIME_CAPABILITIES]}
        elif request.url.path.endswith("/principal"):
            value = {
                "subject": "opaque-subject",
                "canonical_user_id": "42",
                "client_id": "dream-browser",
                "scopes": ["dream:read"]
                if request.headers["authorization"] == "Bearer read-only"
                else [
                    "dream:read",
                    "dream:write",
                    "messages:create",
                    "messages:count_tokens",
                    "models:list",
                ],
                "status": "active",
            }
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


def test_queue_card_cancel_and_side_task_use_owned_admin_operations(boundary, monkeypatch):
    from routers import claude_agent as routes
    client, outputs, calls, _factory = boundary
    queued = {"message_id": "queued-message", "thread_id": "owned-thread", "queue_sequence": "1", "status": "queued", "revision": 1,
              "dispatch_turn_id": None, "created_at": "2026-09-26T00:00:00Z", "text": "new work"}
    outputs["chat-input.list"] = {"entries": [queued]}
    auth = {"Authorization": "Bearer read-write"}
    cancelled = client.post("/api/claude-agent/threads/owned-thread/inputs/queued-message/cancel",
                            headers=auth, json={"expected_revision": 1})
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert next(input_dto for operation, input_dto, _ in calls if operation == "chat-input.transition")["action"] == "cancel"
    async def launch(*, task, current_user, chat, owner):
        assert task.task_id == "task-one"
        assert str(current_user["user_id"]) == "42"
        return {"task_id": task.task_id, "thread_id": task.thread_id, "launch_status": "starting", "dispatch_started": True}
    monkeypatch.setattr(routes, "_task_session_launch_initial", launch)
    outputs["task-session.create"] = {"task": {"task_id": "task-one", "source_thread_id": "owned-thread", "thread_id": "child-thread",
        "title": "new work", "initial_message_id": "child-message", "initial_message": "new work", "launch_status": "pending",
        "launch_error_code": None, "created_at": "2026-09-26T00:00:00Z"}}
    moved = client.post("/api/claude-agent/threads/owned-thread/inputs/queued-message/side-task",
                        headers=auth, json={"expected_revision": 1})
    assert moved.status_code == 200
    assert moved.json()["thread_id"] == "child-thread"
    create = next(input_dto for operation, input_dto, _ in calls if operation == "task-session.create")
    assert create["source_message_id"] == "queued-message"
    assert create["request_key"] == "side:queued-message"


def test_task_session_links_use_current_thread_authorization_and_safe_projection(boundary):
    client, outputs, calls, _factory = boundary
    link = {"task_id": "task-one", "source_thread_id": "owned-thread", "thread_id": "child-thread",
            "title": "Review task", "launch_status": "starting", "launch_error_code": None,
            "created_at": "2026-09-27T00:00:00Z"}
    outputs["task-session.links"] = {
        "source": {**link, "source_title": "Saved conversation"},
        "created": [link],
    }
    response = client.get(
        "/api/claude-agent/threads/owned-thread/task-links",
        headers={"Authorization": "Bearer read-only"},
    )
    assert response.status_code == 200
    assert response.json() == outputs["task-session.links"]
    operation, input_dto, _ = next(call for call in calls if call[0] == "task-session.links")
    assert operation == "task-session.links"
    assert input_dto == {"thread_id": "owned-thread"}
    assert "user_id" not in json.dumps(response.json())

    links_before = len([call for call in calls if call[0] == "task-session.links"])
    original = outputs["chat-thread.get"]
    outputs["chat-thread.get"] = lambda input_dto, _request_id: (
        original if input_dto["thread_id"] == "owned-thread" else {"thread": None}
    )
    denied = client.get(
        "/api/claude-agent/threads/not-owned/task-links",
        headers={"Authorization": "Bearer read-only"},
    )
    assert denied.status_code == 404
    assert len([call for call in calls if call[0] == "task-session.links"]) == links_before


def test_side_task_first_launch_has_no_resume_and_replay_does_not_launch_twice(boundary, monkeypatch):
    from routers import claude_agent as routes
    client, outputs, calls, _factory = boundary
    queued = {"message_id": "queued-message", "thread_id": "owned-thread", "queue_sequence": "1", "status": "queued", "revision": 1,
              "dispatch_turn_id": None, "created_at": "2026-09-26T00:00:00Z", "text": "new work"}
    outputs["chat-input.list"] = {"entries": [queued]}
    task = {"task_id": "task-one", "source_thread_id": "owned-thread", "thread_id": "child-thread",
            "title": "new work", "initial_message_id": "child-message", "initial_message": "new work",
            "launch_status": "pending", "launch_error_code": None, "created_at": "2026-09-26T00:00:00Z"}
    outputs["task-session.create"] = {"task": task}
    claims = []
    def launch(input_dto, _request_id):
        claims.append(input_dto["action"])
        return {"task": {**task, "launch_status": "starting"}, "changed": len(claims) == 1}
    outputs["task-session.launch"] = launch
    launches = []
    async def stream(body, *, current_user, chat, owner):
        launches.append(body)
        assert str(current_user["user_id"]) == "42"
        async def frames():
            yield ": child started\n\n"
        return types.SimpleNamespace(body_iterator=frames())
    monkeypatch.setattr(routes, "claude_agent_stream", stream)
    auth = {"Authorization": "Bearer read-write"}
    path = "/api/claude-agent/threads/owned-thread/inputs/queued-message/side-task"
    first = client.post(path, headers=auth, json={"expected_revision": 1})
    assert first.status_code == 200 and first.json()["dispatch_started"] is True
    outputs["chat-input.list"] = {"entries": [{**queued, "status": "cancelled", "revision": 2}]}
    replay = client.post(path, headers=auth, json={"expected_revision": 1})
    assert replay.status_code == 200 and replay.json()["dispatch_started"] is False
    assert claims == ["claim", "claim"]
    assert len(launches) == 1
    assert launches[0].thread_id == "child-thread"
    assert launches[0].resume is False
    assert launches[0].message["id"] == "child-message"
    assert len([call for call in calls if call[0] == "task-session.create"]) == 2


def test_thread_tool_host_reuses_owned_running_thread_for_send_and_read(boundary, monkeypatch):
    from routers import claude_agent as routes
    from libs.claude_agent_kit.server.session_projection_protocol import ThreadToolCommandRequestDTO
    from services.admin_data import chat_models as dto
    _client, _outputs, _calls, factory = boundary
    async def owned(_user, _chat, thread_id):
        assert thread_id == "child-thread"
        return {"id": thread_id, "title": "Child", "claude_session_id": "real-child-session"}
    monkeypatch.setattr(routes, "_admin_thread", owned)
    factory.session_snapshot = lambda _thread_id: {"lifecycle": "running"}
    factory.accepting_input = lambda _thread_id: True
    submitted = []
    async def enqueue_input(**kwargs):
        submitted.append(kwargs)
        return types.SimpleNamespace(status="queued")
    factory.enqueue_input = enqueue_input
    class Actor:
        canonical_user_id = "42"

        def __init__(self, access_token="bound-user-token"):
            self.access_token = access_token
    monkeypatch.setattr(routes, "AdminRequestActor", Actor)
    class Chat:
        def list_messages(self): pass
        def list_inputs(self): pass
    chat = Chat()
    async def invoke(_user, operation, _input):
        if operation.__name__ == "list_messages":
            messages = []
            if submitted:
                messages.append(dto.ChatMessageDTO(
                    id=submitted[0]["message_id"], role="assistant",
                    parts=[{"type": "text", "text": "saved result"}], metadata=None,
                    metadata_decode_error=False, created_at="2026-09-28T00:00:00Z",
                    history_final_text="saved result", history_process_available=False,
                    history_projection_version=1,
                ))
            return types.SimpleNamespace(messages=messages)
        if operation.__name__ == "list_inputs":
            return types.SimpleNamespace(entries=[types.SimpleNamespace(message_id=submitted[0]["message_id"], status="queued")])
        raise AssertionError(operation.__name__)
    monkeypatch.setattr(routes, "_chat_invoke", invoke)
    def command(operation, **kwargs):
        return ThreadToolCommandRequestDTO(
            capability="c" * 43, request_id="request-one", operation=operation,
            tool_call_id="call-one", thread_id="child-thread", **kwargs
        )
    async def run():
        provider = routes._ThreadToolTurnProvider(loop=asyncio.get_running_loop(),
            current_user={"user_id": "42", "_admin_actor": Actor()}, chat=chat, owner=None,
            source_thread_id="owned-thread", source_message_id="source-message", timeout_seconds=2)
        provider.refresh_authorization({"user_id": "42", "_admin_actor": Actor("fresh-user-token")})
        first = await provider._perform(command("thread.send", prompt="continue"))
        replay = await provider._perform(command("thread.send", prompt="continue"))
        read = await provider._perform(command("thread.read"))
        assert first.status == replay.status == "queued"
        assert first.message_id == replay.message_id
        assert read.status == "running" and read.running is True
        assert read.messages and read.messages[0].text == "saved result"
    asyncio.run(run())
    assert len(submitted) == 1
    assert submitted[0]["thread_id"] == "child-thread"
    assert submitted[0]["access_token"] == "fresh-user-token"


def test_thread_tool_host_creates_related_thread_and_lists_owned_threads(boundary, monkeypatch):
    from routers import claude_agent as routes
    from libs.claude_agent_kit.server.session_projection_protocol import ThreadToolCommandRequestDTO
    from services.admin_data import chat_models as dto
    _client, _outputs, _calls, _factory = boundary
    task = dto.TaskSessionDTO(
        task_id="task-one", source_thread_id="owned-thread", thread_id="child-thread",
        title="Review", initial_message_id="child-message", initial_message="Inspect",
        launch_status="pending", launch_error_code=None, created_at="2026-09-28T00:00:00Z",
    )
    class Actor:
        canonical_user_id = "42"
        access_token = "bound-user-token"
    class Chat:
        def create_task_session(self): pass
        def list_threads(self): pass
    chat = Chat()
    async def invoke(_user, operation, input_dto):
        if operation.__name__ == "create_task_session":
            assert input_dto.source_thread_id == "owned-thread"
            assert input_dto.initial_message == "Inspect"
            return dto.TaskSessionResultDTO(task=task)
        if operation.__name__ == "list_threads":
            assert input_dto.limit == 3
            return dto.ThreadListResultDTO(threads=[dto.ChatThreadSummaryDTO(
                id="child-thread", title="Review", deck_id=None, voice_id=None,
                created_at="2026-09-28T00:00:00Z", updated_at=None,
            )])
        raise AssertionError(operation.__name__)
    async def launch(**_kwargs):
        return {"launch_status": "starting", "dispatch_started": True}
    monkeypatch.setattr(routes, "_chat_invoke", invoke)
    monkeypatch.setattr(routes, "_task_session_launch_initial", launch)
    def command(operation, **kwargs):
        return ThreadToolCommandRequestDTO(
            capability="c" * 43, request_id="request-one", operation=operation,
            tool_call_id="call-one", **kwargs,
        )
    async def run():
        provider = routes._ThreadToolTurnProvider(
            loop=asyncio.get_running_loop(),
            current_user={"user_id": "42", "_admin_actor": Actor()},
            chat=chat, owner=None, source_thread_id="owned-thread",
            source_message_id="source-message", timeout_seconds=2,
        )
        created = await provider._perform(
            command("thread.create", prompt="Inspect", title="Review")
        )
        listed = await provider._perform(command("thread.list", limit=3))
        assert created.thread_id == "child-thread"
        assert created.status == "starting"
        assert listed.status == "ok"
        assert listed.threads and listed.threads[0].thread_id == "child-thread"
    asyncio.run(run())


def test_wait_threads_returns_completion_suppresses_replayed_final_and_wakes_on_input(
    boundary,
    monkeypatch,
):
    from routers import claude_agent as routes
    from libs.claude_agent_kit.server.session_projection_protocol import (
        ThreadToolCommandRequestDTO,
        ThreadToolWaitTargetDTO,
    )

    _client, _outputs, _calls, _factory = boundary

    class Actor:
        canonical_user_id = "42"
        access_token = "bound-user-token"

    class Chat:
        def message_page(self):
            pass

        def list_task_session_links(self):
            pass

    chat = Chat()
    final = types.SimpleNamespace(
        id="final-message",
        role="assistant",
        metadata_decode_error=False,
        metadata={"turnStatus": "completed", "finalPartIndex": 0},
        history_projection_version=1,
        history_final_text="child result",
    )

    async def admin_thread(_user, _chat, thread_id):
        if thread_id == "missing-thread":
            return None
        return {
            "id": thread_id,
            "title": "Child task",
            "claude_session_id": "saved-session",
        }

    async def invoke(_user, operation, _input_dto):
        if operation.__name__ == "message_page":
            return types.SimpleNamespace(messages=[final])
        if operation.__name__ == "list_task_session_links":
            return types.SimpleNamespace(source=None)
        raise AssertionError(operation.__name__)

    class Factory:
        input_received = False
        running = False
        pending_tool_call_ids = []

        def session_snapshot(self, _thread_id):
            return (
                {"lifecycle": "running", "turn_count": 2}
                if self.running
                else None
            )

        def tool_confirmation_snapshot(self, _thread_id):
            return {
                "pending_tool_call_ids": self.pending_tool_call_ids,
                "tool_confirmation_observation": "known",
            }

        @staticmethod
        def input_generation(_thread_id):
            return 7

        async def wait_for_input_after(self, _thread_id, _generation, *, timeout_seconds):
            assert timeout_seconds > 0
            return self.input_received

    factory = Factory()
    monkeypatch.setattr(routes, "_admin_thread", admin_thread)
    monkeypatch.setattr(routes, "_chat_invoke", invoke)
    monkeypatch.setattr(routes, "claude_agent_thread_factory", factory)

    def command(*, after_cursor=None, timeout_ms=0):
        return ThreadToolCommandRequestDTO(
            capability="c" * 43,
            request_id="request-wait",
            operation="thread.wait",
            tool_call_id="call-wait",
            targets=[
                ThreadToolWaitTargetDTO(
                    thread_id="child-thread",
                    after_cursor=after_cursor,
                )
            ],
            timeout_ms=timeout_ms,
        )

    async def run():
        provider = routes._ThreadToolTurnProvider(
            loop=asyncio.get_running_loop(),
            current_user={"user_id": "42", "_admin_actor": Actor()},
            chat=chat,
            owner=None,
            source_thread_id="source-thread",
            source_message_id="source-message",
            timeout_seconds=2,
        )
        completed = await provider._perform(command())
        assert completed.wait_reason == "completed"
        assert completed.updates and completed.updates[0].final_text == "child result"
        cursor = completed.updates[0].cursor

        partially_available = await provider._perform(
            ThreadToolCommandRequestDTO(
                capability="c" * 43,
                request_id="request-wait-multiple",
                operation="thread.wait",
                tool_call_id="call-wait-multiple",
                targets=[
                    ThreadToolWaitTargetDTO(thread_id="missing-thread"),
                    ThreadToolWaitTargetDTO(thread_id="child-thread"),
                ],
                timeout_ms=0,
            )
        )
        assert partially_available.wait_reason == "completed"
        assert partially_available.errors
        assert partially_available.errors[0].thread_id == "missing-thread"
        assert partially_available.errors[0].error_code == "THREAD_NOT_FOUND"

        repeated = await provider._perform(command(after_cursor=cursor))
        assert repeated.wait_reason == "timeout"
        assert repeated.updates and repeated.updates[0].final_text is None

        factory.running = True
        factory.pending_tool_call_ids = ["tool-call-one"]
        attention = await provider._perform(command())
        assert attention.wait_reason == "needs_attention"
        assert attention.updates and attention.updates[0].pending_tool_call_ids == [
            "tool-call-one"
        ]

        factory.running = False
        factory.pending_tool_call_ids = []
        final.metadata = {"turnStatus": "failed"}
        failed = await provider._perform(command(timeout_ms=1_000))
        assert failed.wait_reason == "error"
        assert failed.updates and failed.updates[0].status == "failed"
        assert failed.errors and failed.errors[0].error_code == "THREAD_TARGET_FAILED"

        failed_repeated = await provider._perform(
            command(after_cursor=failed.updates[0].cursor)
        )
        assert failed_repeated.wait_reason == "timeout"
        assert failed_repeated.errors is None

        final.metadata = {"turnStatus": "pending"}
        factory.input_received = True
        interrupted = await provider._perform(command(timeout_ms=1_000))
        assert interrupted.wait_reason == "input_received"
        assert interrupted.updates and interrupted.updates[0].status == "idle"

    asyncio.run(run())


def test_task_session_get_rechecks_source_thread_and_reports_unknown_owner(boundary):
    client, outputs, _calls, factory = boundary
    outputs["task-session.get"] = {"task": {"task_id": "task-one", "source_thread_id": "owned-thread", "thread_id": "child-thread",
        "title": "new work", "initial_message_id": "child-message", "initial_message": "new work", "launch_status": "starting",
        "launch_error_code": None, "created_at": "2026-09-26T00:00:00Z"}}
    outputs["chat-message.page"] = {"messages": [{"id": "pending-user", "role": "user",
        "parts": [{"type": "text", "text": "still waiting"}], "metadata": None,
        "metadata_decode_error": False, "created_at": "2026-09-27T00:00:00Z",
        "history_final_text": None, "history_process_available": False,
        "history_projection_version": None}], "has_more": False,
        "latest_message_id": "pending-user"}
    factory.session_snapshot = lambda _thread_id: None
    auth = {"Authorization": "Bearer read-write"}
    response = client.get("/api/claude-agent/threads/owned-thread/tasks/task-one", headers=auth)
    assert response.status_code == 200
    assert response.json()["status"] == "state_unknown"
    assert "claude_session_id" not in response.json()
    outputs["chat-thread.get"] = {"thread": None}
    denied = client.get("/api/claude-agent/threads/foreign-thread/tasks/task-one", headers=auth)
    assert denied.status_code == 404


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


def test_turn_navigation_pairs_public_user_messages_without_crossing_turns(boundary):
    client, outputs, calls, _ = boundary

    def row(message_id, role, parts, metadata=None, final_text=None):
        return {
            **message_value(message_id=message_id),
            "role": role,
            "parts": parts,
            "metadata": metadata or {},
            "history_final_text": final_text,
        }

    outputs["chat-message.list"] = {"messages": [
        row("user-1", "user", [{"type": "text", "text": "First question"}]),
        row("answer-1", "assistant", [{"type": "text", "text": "First answer"}],
            {"turnStatus": "completed", "turnId": "turn-1", "finalPartIndex": 0}, "First answer"),
        row("user-2", "user", [{"type": "text", "text": "Second question"}]),
        row("auto", "user", [{"type": "text", "text": "Internal repair input"}],
            {"kind": "story-workspace-dream-auto-repair"}),
        row("auto-answer", "assistant", [{"type": "text", "text": "Repair result"}],
            {"turnStatus": "completed", "turnId": "turn-auto", "finalPartIndex": 0}, "Repair result"),
        row("user-3", "user", [{"type": "file", "filename": "notes.pdf", "mediaType": "application/pdf", "url": "https://example.test/file"}]),
        row("answer-3", "assistant", [{"type": "text", "text": "Could not finish"}],
            {"turnStatus": "error", "turnId": "turn-3", "is_partial": True}),
    ]}
    response = request(client, "GET", "/api/claude-agent/threads/owned-thread/turn-navigation")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.json()["items"] == [
        {"message_id": "user-1", "user_preview": "First question", "has_attachment": False,
         "assistant_preview": "First answer", "status": "answered"},
        {"message_id": "user-2", "user_preview": "Second question", "has_attachment": False,
         "assistant_preview": None, "status": "no_reply"},
        {"message_id": "user-3", "user_preview": "notes.pdf", "has_attachment": True,
         "assistant_preview": None, "status": "failed"},
    ]
    assert [call[0] for call in calls] == ["chat-thread.get", "chat-message.list"]
    outputs["chat-thread.get"] = {"thread": None}
    assert request(client, "GET", "/api/claude-agent/threads/another-thread/turn-navigation").status_code == 404
    assert calls[-1][0] == "chat-thread.get"


def test_turn_navigation_keeps_legacy_reply_and_reports_unresolved_or_failed_turns(boundary):
    client, outputs, _, _ = boundary

    def row(message_id, role, text, metadata=None):
        return {
            **message_value(message_id=message_id),
            "role": role,
            "parts": [{"type": "text", "text": text}],
            "metadata": metadata or {},
            "history_final_text": None,
            "history_projection_version": None,
            "history_process_available": False,
        }

    outputs["chat-message.list"] = {"messages": [
        row("legacy-user", "user", "Older question"),
        row("legacy-answer", "assistant", "Older reply"),
        row("unknown-user", "user", "Needs review"),
        row("unknown-answer", "assistant", "Diagnostic text", {"turnId": "turn-unknown", "turnStatus": "completed"}),
        row("failed-user", "user", "Could not dispatch", {"dispatch_status": "failed"}),
    ]}

    response = request(client, "GET", "/api/claude-agent/threads/owned-thread/turn-navigation")
    assert response.status_code == 200
    assert [(item["message_id"], item["assistant_preview"], item["status"])
            for item in response.json()["items"]] == [
        ("legacy-user", "Older reply", "answered"),
        ("unknown-user", None, "state_unknown"),
        ("failed-user", None, "failed"),
    ]


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
    assert [call[0] for call in calls] == ["chat-thread.get", "chat-input.list", "user-system-config.get", "workflow-context.resolve", "runtime-delegation.create", "runtime-delegation.create", "chat-user-message.persist"]
    assert calls[-3][1] == {"purpose": "gateway-cli", "thread_id": "owned-thread", "run_id": None, "editor_session_id": None, "scopes": ["messages:create", "messages:count_tokens", "models:list"]}
    assert calls[-2][1] == {"purpose": "server-persistence", "thread_id": "owned-thread", "run_id": None, "editor_session_id": None, "scopes": ["dream:read", "dream:write"]}
    assert calls[-1][1] == {"thread_id": "owned-thread", "message_id": "public-message-1", "parts_json": '[{"type":"text","text":"Original user message"}]', "metadata_json": None, "title_candidate": "Original user message"}
    assert len(factory.run_requests) == 1 and factory.run_requests[0].message_id == "public-message-1"
    resolution = factory.run_requests[0].admin_workflow_resolution
    assert resolution is not None and resolution.context_for(actor_id="42", thread_id="owned-thread") is None


def test_orphaned_queue_blocks_new_chat_turn_before_runtime(boundary):
    client, outputs, calls, factory = boundary
    outputs["chat-input.list"] = {"entries": [{
        "message_id": "queued-message", "thread_id": "owned-thread",
        "queue_sequence": "1", "status": "queued", "revision": 1,
        "dispatch_turn_id": None, "created_at": "2026-09-26T00:00:00Z",
        "text": "waiting",
    }]}
    response = request(client, "POST", "/api/claude-agent", json={
        "id": "owned-thread",
        "message": {"id": "new-message", "parts": [{"type": "text", "text": "new"}]},
    })
    assert response.status_code == 409
    assert response.json()["detail"]["error_code"] == "CHAT_INPUT_RECONCILIATION_REQUIRED"
    assert [call[0] for call in calls] == ["chat-thread.get", "chat-input.list"]
    assert not factory.run_requests


@pytest.mark.parametrize("method,path,json_body", [
    ("GET", "/api/claude-agent/threads/not-owned/inputs", None),
    ("POST", "/api/claude-agent/threads/not-owned/inputs", {
        "id": "not-owned", "message": {"id": "new-message", "parts": [{"type": "text", "text": "queued"}]},
    }),
    ("POST", "/api/claude-agent/threads/not-owned/inputs/new-message/select", {"expected_revision": 1}),
])
def test_queue_routes_reject_foreign_thread_before_runtime(boundary, method, path, json_body):
    client, outputs, calls, factory = boundary
    outputs["chat-thread.get"] = {"thread": None}
    response = request(client, method, path, json=json_body)
    assert response.status_code == 404
    assert [call[0] for call in calls] == ["chat-thread.get"]
    assert not factory.run_requests


@pytest.mark.parametrize("method,path,json_body", [
    ("GET", "/api/claude-agent/threads/owned-thread/inputs", None),
    ("POST", "/api/claude-agent/threads/owned-thread/inputs", {
        "id": "owned-thread", "message": {"id": "new-message", "parts": [{"type": "text", "text": "queued"}]},
    }),
    ("POST", "/api/claude-agent/threads/owned-thread/inputs/new-message/select", {"expected_revision": 1}),
])
def test_queue_routes_require_authenticated_user(boundary, method, path, json_body):
    client, _, calls, factory = boundary
    response = client.request(method, path, json=json_body)
    assert response.status_code == 401
    assert not calls and not factory.run_requests


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
    assert len(calls) == 7 and calls[-1][0] == "chat-user-message.persist"
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
        "chat-input.list",
        "user-system-config.get",
        "workflow-context.resolve",
        "runtime-delegation.create",
        "runtime-delegation.create",
        "runtime-delegation.create",
        "chat-user-message.persist",
    ]
    assert calls[6][1] == {
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
    assert [item[0] for item in calls] == ["chat-thread.get", "chat-input.list", "user-system-config.get", "workflow-context.resolve"]
    assert not factory.run_requests


def test_server_grant_failure_precedes_message_or_runtime(boundary):
    client, outputs, calls, factory = boundary
    def created(input_dto, _request_id):
        if input_dto["purpose"] == "server-persistence":
            return (403, "DELEGATION_SCOPE_NOT_CONSENTED")
        return {
            **input_dto,
            "token": "idg_" + "g" * 43,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
            "maximum_expires_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        }

    outputs["runtime-delegation.create"] = created
    response = request(client, "POST", "/api/claude-agent", json={"id": "owned-thread", "message": {"id": "public-message-1", "parts": [{"type": "text", "text": "Original user message"}]}})
    assert response.status_code == 403 and not factory.run_requests
    assert [item[0] for item in calls] == ["chat-thread.get", "chat-input.list", "user-system-config.get", "workflow-context.resolve", "runtime-delegation.create", "runtime-delegation.create"]


def test_atomic_reservation_unknown_is_not_retried_or_started(boundary):
    client, outputs, calls, factory = boundary
    outputs["chat-user-message.persist"] = httpx.ReadTimeout("synthetic private diagnostic")
    response = request(client, "POST", "/api/claude-agent", json={"id": "owned-thread", "message": {"id": "public-message-1", "parts": [{"type": "text", "text": "Original user message"}]}})
    assert response.status_code == 504 and response.json()["detail"]["error_code"] == "ADMIN_TIMEOUT"
    assert response.json()["detail"]["outcome_unknown"] is True
    assert not factory.run_requests and sum(item[0] == "chat-user-message.persist" for item in calls) == 1
    assert "private" not in response.text
