# [Input] Actual server persistence holder, synthetic DTO transport and explicitly controlled clock/threads.
# [Output] Entity scope, known reservation reuse, original-ID recovery and shutdown drain evidence.
# [Pos] Provider-free turn lifecycle tests; no PG/model/real service or alternate SSE implementation.
# [Sync] 2026-09-15: validate Thread/SDK Session scope, native init callbacks and one cross-operation unknown barrier.
# [Sync] 2026-09-15: validate server-only persistence authority and short-lock current snapshots.
# [Sync] 2026-09-15: validate assistant full/partial DTOs, four schemas and shared pending barrier.
# [Sync] 2026-09-15: validate Editor broker ownership beside the existing grant lifecycle.
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from threading import Event, Thread
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.chat_data import GET_THREAD, PERSIST_MESSAGE, UPDATE_SESSION
from services.admin_data.delegation import RuntimeGrant
from services.admin_data.delegation_keeper import RuntimeGrantKeeper
from services.admin_data.turn_persistence import AdminTurnPersistence
from services.admin_data.user_message_data import PERSIST_USER_MESSAGE
from services.admin_data.workflow_data import AdminWorkflowResolution
from services.admin_data.workspace_data import WORKSPACE_SCHEMA_REQUIREMENTS

NOW = datetime(2026, 9, 15, tzinfo=timezone.utc)
TOKEN = "idg_" + "a" * 43


def grant():
    return RuntimeGrant(TOKEN, "server-persistence", "thread-1", None, None,
        ("dream:read", "dream:write"), NOW + timedelta(seconds=100), NOW + timedelta(hours=2))


def holder(*, lose_response=False, lose_operation=None, block=None, thread_patch=None, schema_fault=None, assistant_patch=None):
    config = AdminDataConfig(base_url="https://admin.example", issuer="https://admin.example/api/auth", resource="https://dream.example/api", service_secret="s" * 32, service_client_id="dream-service")
    calls, receipt_states = [], ["absent", "committed"]
    thread_row = {"id": "thread-1", "user_id": "42", "title": None, "deck_id": None, "voice_id": None,
        "created_at": None, "updated_at": None, "claude_session_id": None, "agent_contract_version": None, **(thread_patch or {})}
    operations = (PERSIST_USER_MESSAGE, GET_THREAD, UPDATE_SESSION, PERSIST_MESSAGE)
    schemas = [item.model_dump() for item in WORKSPACE_SCHEMA_REQUIREMENTS]
    if schema_fault == "missing": schemas.pop()
    elif schema_fault == "duplicate": schemas.append(dict(schemas[0]))
    elif isinstance(schema_fault, int): schemas[schema_fault]["contract_sha256"] = "0" * 64
    def transport(request):
        request_id = request.headers["x-request-id"]
        calls.append(request)
        if request.url.path.endswith("/capabilities"):
            value = {"version": "1", "auth": {"issuer": config.issuer, "jwks_uri": config.jwks_uri, "resource": config.resource, "algorithm": "ES256", "clients": {"browser": "dream-browser", "device": "dream-device"}, "scopes": ["dream:read", "dream:write"], "delegations": []}, "schema_capabilities": schemas, "operations": [item.capability.model_dump() for item in operations]}
        elif "/receipts/" in request.url.path:
            assert request_id == "write-original"
            state = receipt_states.pop(0)
            operation = request.url.params["operation"]
            value = {"status": state, "request_id": request_id, "operation": operation}
            if state == "committed":
                value["result"] = {"changed": True} if operation == UPDATE_SESSION.capability.name else ({"message_id": "message-1"} if operation == PERSIST_MESSAGE.capability.name else {"message_id": "message-1", "confirmation_preserved": False})
        else:
            assert request.headers["authorization"] == "Bearer " + TOKEN
            assert request_id == "write-original"
            if block is not None:
                entered, release = block
                entered.set()
                assert release.wait(2), "Owned HTTP fixture did not release"
            name = request.url.path.rsplit("/", 1)[-1]
            input_dto = json.loads(request.content)["input"]
            if name == GET_THREAD.capability.name:
                value = {"thread": thread_row}
            elif name == UPDATE_SESSION.capability.name:
                thread_row.update(claude_session_id=input_dto["claude_session_id"], agent_contract_version=input_dto["agent_contract_version"])
                value = {"changed": True}
            elif name == PERSIST_MESSAGE.capability.name:
                value = {"message_id": input_dto["message_id"], **(assistant_patch or {})}
            else:
                value = {"message_id": input_dto["message_id"], "confirmation_preserved": False}
            if lose_response or name == lose_operation:
                raise httpx.ReadTimeout("synthetic private body")
        return httpx.Response(200, json={"request_id": request_id, "data": value})
    client = AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(transport)), operations=operations)
    client.capabilities("capabilities-1")
    runtime = SimpleNamespace(closed=[], renew=lambda value, request_id: value, receipt=lambda *args: None)
    runtime.close = lambda: runtime.closed.append(True)
    value = AdminTurnPersistence(AdminWorkflowResolution("42", "thread-1", None), grant(), client,
        runtime_client_factory=lambda: runtime, clock=lambda: NOW, request_id_factory=lambda: "write-original")
    return value, calls, runtime


def persist(value, *, message_id="message-1", text="original"):
    return value.persist_user(actor_id="42", thread_id="thread-1", message_id=message_id,
        parts=[{"type": "text", "text": text}], metadata=None)


def test_known_public_reservation_is_reused_without_another_write():
    value, calls, _ = holder()
    first = persist(value)
    assert persist(value) is first
    assert len(calls) == 2
    with pytest.raises(AdminDataError, match="CHAT_MESSAGE_IDENTITY_CONFLICT"):
        persist(value, text="changed")
    assert len(calls) == 2


@pytest.mark.parametrize("actor,thread", [("43", "thread-1"), ("42", "other")])
def test_holder_rejects_other_actor_or_thread_before_data_access(actor, thread):
    value, calls, _ = holder()
    with pytest.raises(AdminDataError, match="DREAM_DELEGATION_ENTITY_DENIED"):
        value.current_grant(actor_id=actor, thread_id=thread)
    assert len(calls) == 1


@pytest.mark.parametrize("change", [{"purpose": "gateway-cli", "scopes": ("models:list",)}, {"run_id": "run_" + "a" * 32}, {"thread_id": "other"}, {"scopes": ("dream:write",)}])
def test_server_holder_cannot_accept_wrong_purpose_or_frozen_entities(change):
    value, _, _ = holder()
    with pytest.raises(AdminDataError, match="ADMIN_CONFIGURATION_INVALID"):
        AdminTurnPersistence(AdminWorkflowResolution("42", "thread-1", None), replace(grant(), **change), value._client,
            runtime_client_factory=lambda: None, clock=lambda: NOW)


def test_unknown_write_keeps_original_id_and_recovers_receipt_without_post_retry():
    value, calls, _ = holder(lose_response=True)
    with pytest.raises(AdminDataError) as lost:
        persist(value)
    assert lost.value.outcome_unknown and lost.value.request_id == "write-original"
    with pytest.raises(AdminDataError, match="ADMIN_WRITE_RESULT_UNKNOWN"):
        persist(value, message_id="other")
    assert len(calls) == 2
    with pytest.raises(AdminDataError, match="ADMIN_WRITE_RESULT_UNKNOWN"):
        persist(value)
    result = persist(value)
    assert result.message_id == "message-1" and persist(value) is result
    assert sum(request.method == "POST" for request in calls) == 1
    assert [request.url.path.rsplit("/", 1)[1] for request in calls[-2:]] == ["write-original", "write-original"]


def test_factory_owned_start_and_close_stop_the_only_renewal_client():
    value, calls, runtime = holder()
    value.start()
    value.start()
    value.close()
    assert value._keeper.diagnostics().stopped and not value._keeper._thread.is_alive()
    assert runtime.closed == [True] and len(calls) == 1
    with pytest.raises(AdminDataError, match="DELEGATION_EXPIRED"):
        persist(value)


def test_close_drains_already_dispatched_writer_without_new_commands():
    entered, release, closed = Event(), Event(), Event()
    value, calls, _ = holder(block=(entered, release))
    errors = []
    def write():
        try:
            persist(value)
        except Exception as error:
            errors.append(error)
    worker = Thread(target=write)
    closer = Thread(target=lambda: (value.close(), closed.set()))
    worker.start()
    try:
        assert entered.wait(1)
        closer.start()
        assert not closed.wait(0.05)
    finally:
        release.set()
        worker.join(2)
        if closer.ident is not None:
            closer.join(2)
    assert closed.is_set() and not errors and len(calls) == 2


def test_current_snapshot_does_not_wait_for_renewal_http():
    entered, release, projected = Event(), Event(), Event()
    now = [NOW + timedelta(seconds=60)]
    def renew(value, request_id):
        entered.set()
        assert release.wait(2)
        return replace(value, expires_at=NOW + timedelta(seconds=200))
    keeper = RuntimeGrantKeeper(grant(), SimpleNamespace(renew=renew), clock=lambda: now[0])
    # Constructed at +60, so the renewal deadline is +80.
    now[0] = NOW + timedelta(seconds=85)
    worker = Thread(target=keeper.tick)
    probe = Thread(target=lambda: (keeper.current("server-persistence"), projected.set()))
    worker.start()
    try:
        assert entered.wait(1)
        probe.start()
        assert projected.wait(1), "Current must read the prior valid snapshot while HTTP is blocked"
    finally:
        release.set()
        worker.join(2)
        if probe.ident is not None:
            probe.join(2)
        keeper.close()
    assert projected.is_set() and keeper.diagnostics().pending_request_id is None


def test_service_reuses_atomic_public_reservation_with_pg_fenced(monkeypatch):
    from claude_agent.service import ClaudeAgentRunRequest, ClaudeAgentService
    import database
    value, calls, _ = holder()
    persist(value)
    monkeypatch.setattr(database, "get_db", lambda: pytest.fail("Public user turn must not use Dream PG"))
    request = ClaudeAgentRunRequest(user_id="42", thread_id="thread-1", message_id="message-1",
        message_parts=[{"type": "text", "text": "original"}], admin_turn_persistence=value)
    service = ClaudeAgentService()
    asyncio.run(service._persist_user_message(SimpleNamespace(request=request)))
    assert len(calls) == 2 and request.message_id == "message-1"


def session(value, session_id="44444444-4444-4444-8444-444444444444"):
    return value.update_session(actor_id="42", thread_id="thread-1", session_id=session_id, contract_version="current")


def test_thread_read_and_session_update_use_exact_server_authority():
    value, calls, _ = holder()
    row = value.thread(actor_id="42", thread_id="thread-1")
    assert row.id == "thread-1" and row.user_id == "42" and row.claude_session_id is None
    first = session(value)
    assert session(value) is first
    row = value.thread(actor_id="42", thread_id="thread-1")
    assert row.claude_session_id == "44444444-4444-4444-8444-444444444444"
    assert row.agent_contract_version == "current"
    posts = [json.loads(request.content)["input"] for request in calls if request.method == "POST"]
    assert posts == [{"thread_id": "thread-1"}, {"thread_id": "thread-1", "claude_session_id": row.claude_session_id, "agent_contract_version": "current"}, {"thread_id": "thread-1"}]
    assert all(request.headers["authorization"] == "Bearer " + TOKEN for request in calls[1:])


def test_mutable_session_identity_only_reuses_the_most_recent_confirmation():
    value, calls, _ = holder()
    session(value, "A")
    session(value, "B")
    session(value, "A")
    session(value, "A")
    assert [json.loads(request.content)["input"]["claude_session_id"] for request in calls[1:]] == ["A", "B", "A"]
    assert value.thread(actor_id="42", thread_id="thread-1").claude_session_id == "A"


@pytest.mark.parametrize("patch", [{"id": "other"}, {"user_id": "43"}])
def test_thread_read_rejects_reply_entity_mismatch(patch):
    value, calls, _ = holder(thread_patch=patch)
    with pytest.raises(AdminDataError) as error:
        value.thread(actor_id="42", thread_id="thread-1")
    assert error.value.code == "ADMIN_RESPONSE_INVALID" and not error.value.outcome_unknown
    assert len(calls) == 2


@pytest.mark.parametrize("operation", ["thread", "session"])
@pytest.mark.parametrize("actor,thread", [("43", "thread-1"), ("42", "other")])
def test_thread_and_session_reject_other_entities_before_io(operation, actor, thread):
    value, calls, _ = holder()
    with pytest.raises(AdminDataError, match="DREAM_DELEGATION_ENTITY_DENIED"):
        if operation == "thread":
            value.thread(actor_id=actor, thread_id=thread)
        else:
            value.update_session(actor_id=actor, thread_id=thread, session_id="A", contract_version="current")
    assert len(calls) == 1


def test_unknown_session_blocks_other_writes_including_known_user_and_recovers_original_receipt():
    value, calls, _ = holder(lose_operation=UPDATE_SESSION.capability.name)
    persist(value)
    with pytest.raises(AdminDataError) as lost:
        session(value)
    assert lost.value.outcome_unknown and lost.value.request_id == "write-original"
    for write in (lambda: persist(value), lambda: persist(value, message_id="other"), lambda: session(value, "B")):
        with pytest.raises(AdminDataError, match="ADMIN_WRITE_RESULT_UNKNOWN") as blocked:
            write()
        assert blocked.value.request_id == "write-original" and blocked.value.outcome_unknown
    assert len(calls) == 3
    with pytest.raises(AdminDataError, match="ADMIN_WRITE_RESULT_UNKNOWN"):
        session(value)
    recovered = session(value)
    assert recovered.changed is True and session(value) is recovered
    assert persist(value).message_id == "message-1"
    assert sum(request.method == "POST" and request.url.path.endswith(UPDATE_SESSION.capability.name) for request in calls) == 1
    assert [request.url.params["operation"] for request in calls[-2:]] == [UPDATE_SESSION.capability.name] * 2


def test_unknown_user_blocks_session_write_without_dispatch():
    value, calls, _ = holder(lose_operation=PERSIST_USER_MESSAGE.capability.name)
    with pytest.raises(AdminDataError):
        persist(value)
    with pytest.raises(AdminDataError, match="ADMIN_WRITE_RESULT_UNKNOWN"):
        session(value)
    assert len(calls) == 2


def test_close_drains_an_already_dispatched_thread_read():
    entered, release, closed = Event(), Event(), Event()
    value, calls, _ = holder(block=(entered, release))
    rows, errors = [], []
    def read():
        try:
            rows.append(value.thread(actor_id="42", thread_id="thread-1"))
        except Exception as error:
            errors.append(error)
    worker = Thread(target=read)
    closer = Thread(target=lambda: (value.close(), closed.set()))
    worker.start()
    try:
        assert entered.wait(1)
        closer.start()
        assert not closed.wait(0.05)
    finally:
        release.set()
        worker.join(2)
        if closer.ident is not None:
            closer.join(2)
    assert closed.is_set() and not errors and rows[0].id == "thread-1" and len(calls) == 2


def test_public_native_init_is_the_next_turn_resume_identity_with_thread_pg_fenced(monkeypatch, tmp_path):
    import re
    import claude_agent.service as service_module
    from claude_agent.service import ClaudeAgentRunRequest, ClaudeAgentService
    from claude_agent.thread_pool import AgentRunState
    from claude_agent_sdk.types import SystemMessage
    from tests.test_claude_agent_service import _FakeBus, _FakeContextBuilder
    value, calls, _ = holder()
    service = ClaudeAgentService(context_builder=_FakeContextBuilder(), platform_model_resolver=lambda *_: "dream-balanced",
        managed_mcp_runtime_snapshot_loader=SimpleNamespace(load=AsyncMock(return_value={})))
    request = ClaudeAgentRunRequest(user_id="42", thread_id="thread-1", resume=True,
        admin_workflow_resolution=AdminWorkflowResolution("42", "thread-1", None), admin_turn_persistence=value)
    monkeypatch.setattr(service_module._db, "get_chat_thread", lambda *_: pytest.fail("Public Thread read must use Admin"))
    monkeypatch.setattr(service_module._db, "update_chat_thread_claude_session", lambda *_: pytest.fail("Public SDK Session must use Admin"))
    # Settings is an explicitly retained domain dependency, unrelated to the
    # Thread authority verified here; use existing production DI and own FS.
    monkeypatch.setattr(service_module._db, "get_system_config", lambda *_: {"workspace_enabled": True})
    monkeypatch.setattr(service_module, "get_or_create_workspace", lambda *_args, **_kwargs: tmp_path.resolve())
    new_id = "44444444-4444-4444-8444-444444444444"
    async def scenario():
        state = AgentRunState(session_id=request.thread_id)
        fresh = await service.assemble_context(request, state=state, bus=_FakeBus(), runner=Mock())
        assert fresh.run_options.thread_id is None
        await service._persist_sdk_session_from_message(fresh, SimpleNamespace(data={"session_id": new_id}))
        await service._persist_sdk_session_from_message(fresh, SystemMessage(subtype="error", data={"session_id": new_id}))
        assert not any(item.url.path.endswith(UPDATE_SESSION.capability.name) for item in calls)
        await service._persist_sdk_session_from_message(fresh, SystemMessage(subtype="init", data={"session_id": new_id}))
        project = tmp_path / ".claude-home" / "projects" / re.sub(r"[^a-zA-Z0-9]", "-", str(tmp_path.resolve()))
        project.mkdir(parents=True)
        (project / f"{new_id}.jsonl").write_text(json.dumps({"type": "user", "uuid": "fixture", "sessionId": new_id,
            "message": {"role": "user", "content": "fixture"}}) + "\n")
        resumed = await service.assemble_context(request, state=state, bus=_FakeBus(), runner=Mock())
        assert resumed.run_options.resume and resumed.run_options.thread_id == new_id
        assert resumed.request.thread_id == "thread-1" and resumed.request.admin_turn_persistence is value
        await service._persist_sdk_session_from_message(resumed, SystemMessage(subtype="init", data={"session_id": new_id}))
    asyncio.run(scenario())
    assert sum(item.url.path.endswith(UPDATE_SESSION.capability.name) for item in calls) == 1


@pytest.mark.parametrize("lose_session", [False, True])
def test_public_native_init_persists_before_original_cancel_terminal_with_pg_fenced(monkeypatch, lose_session):
    import claude_agent.service as service_module
    from claude_agent.service import ClaudeAgentRunRequest, ClaudeAgentService
    from claude_agent.thread_pool import AgentRunState
    from claude_agent.tool_confirmation_store import ToolConfirmationStore
    from claude_agent_sdk.types import SystemMessage
    value, calls, _ = holder(lose_operation=UPDATE_SESSION.capability.name if lose_session else None)
    service = ClaudeAgentService(dream_artifact_turn_hook=Mock())
    monkeypatch.setattr(service_module._db, "update_chat_thread_claude_session", lambda *_: pytest.fail("Public callback must use Admin"))
    monkeypatch.setattr(service_module._db, "get_db", lambda: pytest.fail("Public user reservation must use Admin"))
    # Raw assistant persistence has not migrated; inject only that retained
    # boundary while executing the real service callbacks/cancel/SSE path.
    partial = AsyncMock()
    monkeypatch.setattr(service, "_persist_partial_assistant", partial)
    async def scenario():
        queue = asyncio.Queue()
        request = ClaudeAgentRunRequest(user_id="42", thread_id="thread-1", message_id="message-1",
            message_parts=[{"type": "text", "text": "original"}], admin_turn_persistence=value)
        class CancelRunner:
            async def run_streaming(self, opts, callbacks):
                await callbacks.on_message(SystemMessage(subtype="init", data={"session_id": "A"}))
                await callbacks.on_text_delta("partial")
                raise asyncio.CancelledError()
        execution = service_module._TurnExecution(request=request, state=AgentRunState(session_id="thread-1"),
            runner=CancelRunner(), run_options=Mock(), turn_context=service_module._TurnContext(queue=queue, confirmation_store=ToolConfirmationStore()),
            dream_artifact_turn_ticket=Mock())
        with pytest.raises(asyncio.CancelledError):
            await service.execute_session(execution)
        frames = []
        while not queue.empty():
            frames.append(queue.get_nowait())
        assert frames[-1] is None
        assert frames[-2].payload() == {"type": "finish", "finishReason": "stop", "cancelled": True}
        metadata = next(frame for frame in frames if frame is not None and frame.type == "message-metadata")
        assert metadata.data["turnId"]
    asyncio.run(scenario())
    partial.assert_awaited_once()
    assert partial.await_args.kwargs["turn_status"] == "cancelled"
    assert [item.url.path.rsplit("/", 1)[-1] for item in calls[1:]] == [PERSIST_USER_MESSAGE.capability.name, UPDATE_SESSION.capability.name]
    if lose_session:
        with pytest.raises(AdminDataError, match="ADMIN_WRITE_RESULT_UNKNOWN"):
            session(value, "B")
        assert len(calls) == 3


@pytest.mark.parametrize("cancel", [False, True])
@pytest.mark.parametrize("active_editor", [False, True])
def test_original_factory_keeps_grant_on_disconnect_and_drains_it_on_terminal(
    monkeypatch, cancel, active_editor
):
    import claude_agent.thread_factory as factory_module
    from claude_agent.service import ClaudeAgentRunRequest
    from claude_agent.stream_events import NormalizedAgentEvent
    from claude_agent.thread_factory import ClaudeAgentThreadFactory
    value, _, runtime = holder()
    editor_runtime = SimpleNamespace(start_calls=0, close_calls=0)
    editor_runtime.start = lambda: setattr(
        editor_runtime, "start_calls", editor_runtime.start_calls + 1
    )
    editor_runtime.close = lambda: setattr(
        editor_runtime, "close_calls", editor_runtime.close_calls + 1
    )
    monkeypatch.setattr(factory_module, "ClaudeAgentRunner", lambda: SimpleNamespace())

    async def scenario():
        finish = asyncio.Event()
        released = []
        admission = SimpleNamespace(try_acquire=lambda session_id: SimpleNamespace(release=lambda: released.append(session_id)))
        factory = ClaudeAgentThreadFactory(dream_observer=SimpleNamespace(), admission_controller=admission)
        class Service:
            async def assemble_context(self, request, *, state, bus, runner):
                assert value._keeper is not None
                assert editor_runtime.start_calls == int(active_editor)
                state.system_prompt = "explicit-fake-context"
                return SimpleNamespace(dream_context=None, bus=bus)
            async def execute_session(self, execution):
                await execution.bus.publish(NormalizedAgentEvent.create("message-metadata", {"sessionId": "thread-1"}))
                await finish.wait()
                await execution.bus.publish_terminal(NormalizedAgentEvent.create("finish", {"finishReason": "stop"}))
            async def mark_auto_repair_failed(self, request):
                pass
        factory._service = Service()
        request = ClaudeAgentRunRequest(
            user_id="42",
            thread_id="thread-1",
            admin_turn_persistence=value,
            admin_editor_runtime=editor_runtime,
            editor_state={"id": "editor-1"} if active_editor else None,
        )
        stream = factory.run_streaming(request)
        try:
            first = await asyncio.wait_for(anext(stream), 1)
            assert "message-metadata" in first
            state = factory._pool.get("thread-1")
            task = state.bg_task
            await stream.aclose()
            assert factory.session_snapshot("thread-1")["lifecycle"] == "running"
            assert value.current_grant(actor_id="42", thread_id="thread-1").token == TOKEN
            assert editor_runtime.close_calls == 0
            assert not released
            if cancel:
                result = await factory.stop_thread("thread-1")
                assert result["running"] is False
            else:
                finish.set()
                await asyncio.wait_for(task, 1)
            assert released == ["thread-1"]
        finally:
            finish.set()
            await stream.aclose()
            await factory.aclose()
        assert runtime.closed == [True] and not value._keeper._thread.is_alive()
        assert editor_runtime.start_calls == int(active_editor)
        assert editor_runtime.close_calls == 1
    asyncio.run(scenario())
def assistant_write(value, **changes):
    args = {"actor_id": "42", "thread_id": "thread-1", "message_id": "message-1",
        "parts": [{"type": "text", "text": "  原结果\n"}],
        "metadata": {"turnId": "turn-original", "turnStatus": "completed", "finalPartIndex": 0,
            "durationMs": 1250, "usage": {"inputTokens": 3, "outputTokens": 2, "totalTokens": 5}},
        "history_final_text": "  原结果\n", "history_process_available": False, "history_projection_version": 1}
    return value.persist_assistant(**{**args, **changes})


def test_assistant_uses_original_complete_history_DTO_and_current_grant():
    value, calls, _ = holder()
    result = assistant_write(value)
    request = next(item for item in calls if item.url.path.endswith(PERSIST_MESSAGE.capability.name))
    body = json.loads(request.content)
    assert result.message_id == "message-1"
    assert request.headers["authorization"] == "Bearer " + TOKEN
    assert set(body["input"]) == {"thread_id", "message_id", "role", "parts", "metadata", "history_final_text", "history_process_available", "history_projection_version"}
    assert body["input"]["role"] == "assistant" and body["input"]["history_final_text"] == "  原结果\n"
    assert body["input"]["metadata"]["usage"]["totalTokens"] == 5
    assert TOKEN not in request.content.decode() and value._pending is None


@pytest.mark.parametrize("actor,thread", [("43", "thread-1"), ("42", "another-thread")])
def test_assistant_rejects_wrong_actor_or_thread_before_io(actor, thread):
    value, calls, _ = holder()
    before = len(calls)
    with pytest.raises(AdminDataError): assistant_write(value, actor_id=actor, thread_id=thread)
    assert len(calls) == before


@pytest.mark.parametrize("fault", ["missing", "duplicate", 0, 1, 2, 3])
def test_assistant_requires_four_exact_schemas_before_command(fault):
    value, calls, _ = holder(schema_fault=fault)
    before = len(calls)
    with pytest.raises(AdminDataError) as error: assistant_write(value)
    assert error.value.code == "ADMIN_CAPABILITY_UNAVAILABLE"
    assert value._pending is None
    assert all(item.method == "GET" and item.url.path.endswith("/capabilities") for item in calls[before:])


@pytest.mark.parametrize("patch", [{"message_id": "another-message"}, {"message_id": None}, {"extra": "private"}])
def test_assistant_bad_reply_retains_original_pending_identity(patch):
    value, calls, _ = holder(assistant_patch=patch)
    with pytest.raises(AdminDataError) as error: assistant_write(value)
    assert error.value.code == "ADMIN_RESPONSE_INVALID" and error.value.outcome_unknown
    assert value._pending.operation is PERSIST_MESSAGE and value._pending.request_id == "write-original"
    assert sum(item.url.path.endswith(PERSIST_MESSAGE.capability.name) for item in calls) == 1


def test_unknown_assistant_blocks_user_session_and_new_assistant_then_only_recovers_original():
    value, calls, _ = holder(lose_operation=PERSIST_MESSAGE.capability.name)
    with pytest.raises(AdminDataError) as error: assistant_write(value)
    assert error.value.request_id == "write-original" and error.value.outcome_unknown
    before = len(calls)
    for method in [lambda: value.persist_user(actor_id="42", thread_id="thread-1", message_id="user-other", parts=[{"type":"text","text":"user"}], metadata=None),
        lambda: value.update_session(actor_id="42", thread_id="thread-1", session_id="native", contract_version="v1"),
        lambda: assistant_write(value, message_id="another-message")]:
        with pytest.raises(AdminDataError) as result: method()
        assert result.value.request_id == "write-original" and result.value.outcome_unknown
    assert len(calls) == before
    with pytest.raises(AdminDataError): assistant_write(value)  # Original absent does not resend.
    result = assistant_write(value)
    assert result.message_id == "message-1" and value._pending is None
    assert sum(item.url.path.endswith(PERSIST_MESSAGE.capability.name) for item in calls) == 1
    reads = [item for item in calls if "/receipts/" in item.url.path]
    assert len(reads) == 2 and all(item.method == "GET" and item.url.path.endswith("write-original") and item.url.params["operation"] == PERSIST_MESSAGE.capability.name for item in reads)


@pytest.mark.parametrize("operation", [PERSIST_USER_MESSAGE, UPDATE_SESSION], ids=lambda item:item.capability.name)
def test_unknown_existing_writer_blocks_assistant_before_io(operation):
    value, calls, _ = holder(lose_operation=operation.capability.name)
    with pytest.raises(AdminDataError):
        if operation is PERSIST_USER_MESSAGE:
            value.persist_user(actor_id="42", thread_id="thread-1", message_id="user-1", parts=[{"type":"text","text":"user"}], metadata=None)
        else:
            value.update_session(actor_id="42", thread_id="thread-1", session_id="native", contract_version="v1")
    before = len(calls)
    with pytest.raises(AdminDataError) as error: assistant_write(value)
    assert error.value.outcome_unknown and len(calls) == before


@pytest.mark.parametrize("outcome", ["completed", "cancelled", "error"])
def test_public_execute_session_persists_original_assistant_parts_with_SQL_fenced(monkeypatch, outcome):
    import database
    import claude_agent.service as service_module
    from claude_agent.service import ClaudeAgentRunRequest, ClaudeAgentService
    from claude_agent.thread_pool import AgentRunState
    from claude_agent.tool_confirmation_store import ToolConfirmationStore
    from libs.claude_agent_kit.types import AgentRunResult
    from tests.test_claude_agent_service import _FakeContextBuilder
    value, calls, _ = holder()
    monkeypatch.setattr(database, "save_chat_message", lambda *_a, **_kw: pytest.fail("Public assistant must not write SQL"))
    monkeypatch.setattr(database, "get_db", lambda *_a, **_kw: pytest.fail("Public turn persistence must not open SQL"))
    class Runner:
        async def run_streaming(self, opts, callbacks):
            await callbacks.on_text_delta("原文结果")
            if outcome == "cancelled": raise asyncio.CancelledError
            await callbacks.on_text_done("原文结果")
            return AgentRunResult(full_text="原文结果", session_id=None, success=outcome=="completed",
                error="synthetic failure" if outcome=="error" else None,
                usage={"input_tokens":3,"output_tokens":2}, duration_ms=1250)
    service = ClaudeAgentService(context_builder=_FakeContextBuilder(), platform_model_resolver=lambda *_:"dream-balanced",
        managed_mcp_runtime_snapshot_loader=SimpleNamespace(load=AsyncMock(return_value={})))
    async def scenario():
        request = ClaudeAgentRunRequest(user_id="42",thread_id="thread-1",message_id="user-1",
            message_parts=[{"type":"text","text":"用户文本"}],model="dream-balanced",admin_turn_persistence=value,
            admin_workflow_resolution=AdminWorkflowResolution("42","thread-1",None))
        execution = service_module._TurnExecution(request=request,state=AgentRunState(session_id="thread-1"),runner=Runner(),run_options=Mock(),
            turn_context=service_module._TurnContext(queue=asyncio.Queue(),confirmation_store=ToolConfirmationStore()))
        if outcome == "cancelled":
            with pytest.raises(asyncio.CancelledError): await service.execute_session(execution)
        else: await service.execute_session(execution)
        return execution
    execution = asyncio.run(scenario())
    assistant = [item for item in calls if item.url.path.endswith(PERSIST_MESSAGE.capability.name)]
    assert len(assistant)==1
    dto = json.loads(assistant[0].content)["input"]
    assert dto["parts"]==[{"type":"text","text":"原文结果"}] and dto["metadata"]["turnStatus"]==outcome
    assert dto["metadata"]["chatModel"]=={"provider":"gateway","model":"dream-balanced"}
    assert dto["metadata"]["turnId"]==execution.state.current_turn_id
    assert dto["message_id"] not in {execution.request.message_id, execution.state.current_turn_id}
    if outcome=="completed":
        assert (dto["history_final_text"],dto["history_process_available"],dto["history_projection_version"])==("原文结果",False,1)
        assert dto["metadata"]["durationMs"]==1250 and dto["metadata"]["usage"]["totalTokens"]==5
    else:
        assert dto["metadata"]["is_partial"] is True
        assert (dto["history_final_text"],dto["history_process_available"],dto["history_projection_version"])==(None,False,None)
