# [Input] Actual server persistence holder, synthetic DTO transport and explicitly controlled clock/threads.
# [Output] Entity scope, known reservation reuse, original-ID recovery and shutdown drain evidence.
# [Pos] Provider-free turn lifecycle tests; no PG/model/real service or alternate SSE implementation.
# [Sync] 2026-09-15: validate server-only persistence authority and short-lock current snapshots.
from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from threading import Event, Thread
from types import SimpleNamespace

import httpx
import pytest

from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.delegation import RuntimeGrant
from services.admin_data.delegation_keeper import RuntimeGrantKeeper
from services.admin_data.turn_persistence import AdminTurnPersistence
from services.admin_data.user_message_data import PERSIST_USER_MESSAGE
from services.admin_data.workflow_data import AdminWorkflowResolution

NOW = datetime(2026, 9, 15, tzinfo=timezone.utc)
TOKEN = "idg_" + "a" * 43


def grant():
    return RuntimeGrant(TOKEN, "server-persistence", "thread-1", None, None,
        ("dream:read", "dream:write"), NOW + timedelta(seconds=100), NOW + timedelta(hours=2))


def holder(*, lose_response=False, block=None):
    config = AdminDataConfig(base_url="https://admin.example", issuer="https://admin.example/api/auth", resource="https://dream.example/api", service_secret="s" * 32, service_client_id="dream-service")
    calls, receipt_states = [], ["absent", "committed"]
    def transport(request):
        request_id = request.headers["x-request-id"]
        calls.append(request)
        if request.url.path.endswith("/capabilities"):
            value = {"version": "1", "auth": {"issuer": config.issuer, "jwks_uri": config.jwks_uri, "resource": config.resource, "algorithm": "ES256", "clients": {"browser": "dream-browser", "device": "dream-device"}, "scopes": ["dream:write"], "delegations": []}, "schema_capabilities": [], "operations": [PERSIST_USER_MESSAGE.capability.model_dump()]}
        elif "/receipts/" in request.url.path:
            assert request_id == "write-original"
            state = receipt_states.pop(0)
            value = {"status": state, "request_id": request_id, "operation": PERSIST_USER_MESSAGE.capability.name}
            if state == "committed":
                value["result"] = {"message_id": "message-1", "confirmation_preserved": False}
        else:
            assert request.headers["authorization"] == "Bearer " + TOKEN
            assert request_id == "write-original"
            if block is not None:
                entered, release = block
                entered.set()
                assert release.wait(2), "Owned HTTP fixture did not release"
            if lose_response:
                raise httpx.ReadTimeout("synthetic private body")
            message_id = json.loads(request.content)["input"]["message_id"]
            value = {"message_id": message_id, "confirmation_preserved": False}
        return httpx.Response(200, json={"request_id": request_id, "data": value})
    client = AdminDataClient(config, client=httpx.Client(transport=httpx.MockTransport(transport)), operations=(PERSIST_USER_MESSAGE,))
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


@pytest.mark.parametrize("cancel", [False, True])
def test_original_factory_keeps_grant_on_disconnect_and_drains_it_on_terminal(monkeypatch, cancel):
    import claude_agent.thread_factory as factory_module
    from claude_agent.service import ClaudeAgentRunRequest
    from claude_agent.stream_events import NormalizedAgentEvent
    from claude_agent.thread_factory import ClaudeAgentThreadFactory
    value, _, runtime = holder()
    monkeypatch.setattr(factory_module, "ClaudeAgentRunner", lambda: SimpleNamespace())

    async def scenario():
        finish = asyncio.Event()
        released = []
        admission = SimpleNamespace(try_acquire=lambda session_id: SimpleNamespace(release=lambda: released.append(session_id)))
        factory = ClaudeAgentThreadFactory(dream_observer=SimpleNamespace(), admission_controller=admission)
        class Service:
            async def assemble_context(self, request, *, state, bus, runner):
                assert value._keeper is not None
                state.system_prompt = "explicit-fake-context"
                return SimpleNamespace(dream_context=None, bus=bus)
            async def execute_session(self, execution):
                await execution.bus.publish(NormalizedAgentEvent.create("message-metadata", {"sessionId": "thread-1"}))
                await finish.wait()
                await execution.bus.publish_terminal(NormalizedAgentEvent.create("finish", {"finishReason": "stop"}))
            async def mark_auto_repair_failed(self, request):
                pass
        factory._service = Service()
        request = ClaudeAgentRunRequest(user_id="42", thread_id="thread-1", admin_turn_persistence=value)
        stream = factory.run_streaming(request)
        try:
            first = await asyncio.wait_for(anext(stream), 1)
            assert "message-metadata" in first
            state = factory._pool.get("thread-1")
            task = state.bg_task
            await stream.aclose()
            assert factory.session_snapshot("thread-1")["lifecycle"] == "running"
            assert value.current_grant(actor_id="42", thread_id="thread-1").token == TOKEN
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
    asyncio.run(scenario())
