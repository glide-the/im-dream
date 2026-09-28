# [Input] Admin result claim DTOs, production TaskResultCoordinator and canonical turn-drain helper.
# [Output] One source dispatch, terminal settlement after owner exit, and recovery after uncertain cancellation.
# [Pos] Provider-free task-result worker contract test; no model or business database access.
# [Sync] 2026-09-27: verify source continuation uses the existing Chat turn stream and exact Admin states.
# [Sync] 2026-09-28: source result requests suppress cached browser Editor context without requesting an Editor grant.
# [Sync] 2026-09-28: verify the production request preparer preserves the saved source session and Admin claim identity.
# [Sync] 2026-09-28: repeat an uncertain global claim with its original request ID before polling another result.
# [Sync] 2026-09-28: keep the claim grant live until the Factory owner finishes queued follow-up turns.
# [Sync] 2026-09-28: stop new claims during shutdown, then settle only after the Factory owner exits.
from __future__ import annotations

import asyncio
import threading
from types import SimpleNamespace

import pytest

from claude_agent.service import ClaudeAgentRunRequest
from claude_agent.task_result_coordinator import TaskResultCoordinator
from services.admin_data.delegation import DelegationCreatedDTO, RuntimeHttpConfig
from services.admin_data.errors import AdminDataError
from services.admin_data.session_projection_broker import SessionProjectionBrokerSettings
from services.admin_data.task_session_result_data import (
    AdminTaskResultClaim, AdminTaskResultWorkerData, TaskResultClaimNextOutputDTO,
    TaskResultClaimOutputDTO, TaskResultDTO, TaskResultSettleInputDTO,
)


def claim() -> AdminTaskResultClaim:
    return AdminTaskResultClaim(
        result=TaskResultDTO(
            notification_id="notice-1", task_id="task-1", source_thread_id="source-1",
            target_thread_id="child-1", target_turn_id="child-turn",
            target_final_message_id="child-final", title="Read today's notes",
            final_text="Summary", status="dispatching", revision=2,
            claim_id="claim-1", source_turn_id="source-turn",
            source_input_message_id="source-input", source_final_message_id=None,
            error_code=None, created_at="2026-09-27T00:00:00Z",
            updated_at="2026-09-27T00:01:00Z",
        ),
        actor_id="42", source_session_id="claude-session",
        source_input_message_id="source-input", source_input_text="Summary",
        persistence_grant=None, gateway_grant=None,
    )


class Worker:
    def __init__(self) -> None:
        self.settled: list[TaskResultSettleInputDTO] = []
        self.claims = [claim()]

    def claim_next(self, request_id):
        return self.claims.pop(0) if self.claims else None

    def settle(self, input_dto, request_id):
        self.settled.append(input_dto)


class OwnerPart:
    def __init__(self) -> None:
        self.started = 0
        self.closed = 0

    def start(self):
        self.started += 1

    def close(self):
        self.closed += 1


class Factory:
    def __init__(self, *, final: bool = True, blocked: bool = False,
                 hold_owner: bool = False, stream_error: bool = False) -> None:
        self.requests = []
        self.final = final
        self.blocked = blocked
        self.hold_owner = hold_owner
        self.stream_error = stream_error
        self.entered = asyncio.Event()
        self.first_turn_done = asyncio.Event()
        self.owner_completion = None

    def run_streaming(self, request):
        self.requests.append(request)
        completion = asyncio.get_running_loop().create_future()
        owner_completion = asyncio.get_running_loop().create_future()
        self.owner_completion = owner_completion

        async def frames():
            try:
                self.entered.set()
                if self.blocked:
                    await asyncio.Event().wait()
                if self.stream_error:
                    raise RuntimeError("source stream reader failed")
                completion.set_result(SimpleNamespace(
                    cancelled=False, finish_reason="stop" if not self.final else "end_turn",
                    saw_finish=True, saw_message_final=self.final,
                ))
                yield "ignored by canonical completion handle"
            finally:
                self.first_turn_done.set()
                if not self.hold_owner and not owner_completion.done():
                    owner_completion.set_result(None)

        return Stream(frames(), completion, owner_completion)


class Stream:
    def __init__(self, frames, completion, owner_completion) -> None:
        self._frames = frames
        self.completion = completion
        self.owner_completion = owner_completion

    def __aiter__(self):
        return self._frames


def preparer(owner):
    async def prepare(result_claim):
        assert result_claim.result.notification_id == "notice-1"
        return owner, ClaudeAgentRunRequest(
            user_id="42", thread_id="source-1", resume=True,
            message_id="source-input", message_parts=[{"type": "text", "text": "Summary"}],
            message_metadata={"kind": "task-session-result",
                              "taskResultNotificationId": "notice-1",
                              "claimId": "claim-1", "sourceTurnId": "source-turn"},
            user_message_pre_persisted=True, task_result_turn_id="source-turn",
        )
    return prepare


@pytest.mark.asyncio
async def test_committed_source_turn_settles_delivered_once():
    worker, factory = Worker(), Factory()
    owner = SimpleNamespace(persistence=OwnerPart(), gateway_runtime=OwnerPart())
    coordinator = TaskResultCoordinator(worker, factory, request_preparer=preparer(owner))
    await coordinator._dispatch(claim())
    assert len(factory.requests) == 1
    assert factory.requests[0].thread_id == "source-1"
    assert factory.requests[0].resume is True
    assert factory.requests[0].task_result_turn_id == "source-turn"
    assert owner.persistence.started == owner.gateway_runtime.started == 1
    assert len(worker.settled) == 1
    assert worker.settled[0].action == "delivered"
    assert worker.settled[0].model_dump(mode="json") == {
        "notification_id": "notice-1", "expected_revision": 2,
        "claim_id": "claim-1", "action": "delivered",
    }


@pytest.mark.asyncio
async def test_result_settlement_waits_for_factory_owner_after_first_final():
    worker, factory = Worker(), Factory(hold_owner=True)
    owner = SimpleNamespace(persistence=OwnerPart(), gateway_runtime=OwnerPart())
    coordinator = TaskResultCoordinator(worker, factory, request_preparer=preparer(owner))
    dispatch = asyncio.create_task(coordinator._dispatch(claim()))
    await asyncio.wait_for(factory.first_turn_done.wait(), timeout=1)
    assert factory.owner_completion is not None
    assert not dispatch.done()
    assert worker.settled == []
    factory.owner_completion.set_result(None)
    await asyncio.wait_for(dispatch, timeout=1)
    assert [item.action for item in worker.settled] == ["delivered"]


@pytest.mark.asyncio
async def test_stream_error_waits_for_factory_owner_before_unknown_settlement():
    worker, factory = Worker(), Factory(hold_owner=True, stream_error=True)
    owner = SimpleNamespace(persistence=OwnerPart(), gateway_runtime=OwnerPart())
    coordinator = TaskResultCoordinator(worker, factory, request_preparer=preparer(owner))
    dispatch = asyncio.create_task(coordinator._dispatch(claim()))
    await asyncio.wait_for(factory.first_turn_done.wait(), timeout=1)
    assert factory.owner_completion is not None
    assert worker.settled == []
    assert not dispatch.done()
    factory.owner_completion.set_result(None)
    await asyncio.wait_for(dispatch, timeout=1)
    assert [item.action for item in worker.settled] == ["mark_unknown"]
    assert owner.persistence.closed == owner.gateway_runtime.closed == 1


@pytest.mark.asyncio
async def test_shutdown_keeps_active_claim_until_factory_owner_exits():
    worker, factory = Worker(), Factory(hold_owner=True)
    owner = SimpleNamespace(persistence=OwnerPart(), gateway_runtime=OwnerPart())
    coordinator = TaskResultCoordinator(
        worker, factory, poll_interval_s=0.01, request_preparer=preparer(owner),
    )
    coordinator.start()
    await asyncio.wait_for(factory.first_turn_done.wait(), timeout=1)
    await coordinator.stop_claiming()
    assert worker.settled == []
    assert factory.owner_completion is not None
    assert not factory.owner_completion.done()
    factory.owner_completion.set_result(None)
    await asyncio.wait_for(coordinator.stop(), timeout=1)
    assert [item.action for item in worker.settled] == ["delivered"]


@pytest.mark.asyncio
async def test_missing_final_is_unknown_and_never_redispatched():
    worker, factory = Worker(), Factory(final=False)
    owner = SimpleNamespace(persistence=OwnerPart(), gateway_runtime=OwnerPart())
    coordinator = TaskResultCoordinator(worker, factory, request_preparer=preparer(owner))
    await coordinator._dispatch(claim())
    assert len(factory.requests) == 1
    assert worker.settled[0].action == "mark_unknown"
    assert worker.settled[0].error_code == "TASK_SESSION_RETURN_STATE_UNKNOWN"


@pytest.mark.asyncio
async def test_preparation_failure_is_proven_not_submitted():
    worker, factory = Worker(), Factory()

    async def fail(_claim):
        raise RuntimeError("model catalog unavailable")

    coordinator = TaskResultCoordinator(worker, factory, request_preparer=fail)
    await coordinator._dispatch(claim())
    assert factory.requests == []
    assert worker.settled[0].action == "failed"
    assert worker.settled[0].error_code == "TASK_SESSION_RETURN_NOT_SUBMITTED"


@pytest.mark.asyncio
async def test_grant_start_failure_closes_both_owners_without_sdk_submission():
    worker, factory = Worker(), Factory()
    owner = SimpleNamespace(persistence=OwnerPart(), gateway_runtime=OwnerPart())

    def fail_start():
        raise RuntimeError("grant rejected")

    owner.gateway_runtime.start = fail_start
    coordinator = TaskResultCoordinator(worker, factory, request_preparer=preparer(owner))
    await coordinator._dispatch(claim())
    assert factory.requests == []
    assert owner.persistence.closed == owner.gateway_runtime.closed == 1
    assert worker.settled[0].action == "failed"


@pytest.mark.asyncio
async def test_source_claude_session_change_blocks_resume_before_factory():
    worker, factory = Worker(), Factory()
    persistence, gateway = OwnerPart(), OwnerPart()
    persistence.thread = lambda **_kwargs: SimpleNamespace(claude_session_id="different-session")
    worker.turn_owner = lambda _claim, _request_id: SimpleNamespace(
        persistence=persistence, gateway_runtime=gateway,
    )
    coordinator = TaskResultCoordinator(worker, factory)
    await coordinator._dispatch(claim())
    assert factory.requests == []
    assert persistence.closed == gateway.closed == 1
    assert worker.settled[0].action == "failed"


@pytest.mark.asyncio
async def test_production_request_preparer_uses_saved_source_session_and_claim(monkeypatch):
    from claude_agent import task_result_coordinator as module

    worker, factory = Worker(), Factory()
    persistence = OwnerPart()
    persistence.thread = lambda **_kwargs: SimpleNamespace(
        claude_session_id="claude-session", deck_id=None, voice_id=None,
    )
    persistence.system_config = lambda **_kwargs: None
    gateway = OwnerPart()
    workflow = SimpleNamespace(context_for=lambda **_kwargs: None)
    owner = SimpleNamespace(
        workflow=workflow, persistence=persistence, gateway_runtime=gateway,
    )
    worker.turn_owner = lambda _claim, _request_id: owner
    monkeypatch.setattr(module, "resolve_platform_model", lambda *_args, **_kwargs: SimpleNamespace(
        model_alias="claude-test-model", claude_code_runtime_env=lambda: {},
    ))
    coordinator = TaskResultCoordinator(worker, factory)

    prepared_owner, request = await coordinator._prepare_request(claim())

    assert prepared_owner is owner
    assert request.user_id == "42"
    assert request.thread_id == "source-1"
    assert request.resume is True
    assert request.message_id == "source-input"
    assert request.user_message_pre_persisted is True
    assert request.task_result_turn_id == "source-turn"
    assert request.message_metadata == {
        "kind": "task-session-result",
        "taskResultNotificationId": "notice-1",
        "taskId": "task-1",
        "targetTurnId": "child-turn",
        "claimId": "claim-1",
        "sourceTurnId": "source-turn",
    }
    assert request.model == "claude-test-model"
    assert request.admin_turn_persistence is persistence
    assert request.admin_workflow_resolution is workflow
    assert request.admin_gateway_runtime is gateway
    assert request.inherit_cached_editor_state is False


@pytest.mark.asyncio
async def test_cancelled_dispatch_leaves_claim_for_admin_recovery():
    worker, factory = Worker(), Factory(blocked=True)
    owner = SimpleNamespace(persistence=OwnerPart(), gateway_runtime=OwnerPart())
    coordinator = TaskResultCoordinator(worker, factory, request_preparer=preparer(owner))
    task = asyncio.create_task(coordinator._dispatch(claim()))
    await factory.entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert len(factory.requests) == 1
    assert worker.settled == []


@pytest.mark.asyncio
async def test_shutdown_waits_for_pending_claim_response_before_draining():
    started = threading.Event()
    release = threading.Event()

    class SlowWorker(Worker):
        def __init__(self):
            super().__init__()
            self.calls = 0

        def claim_next(self, request_id):
            self.calls += 1
            started.set()
            release.wait(timeout=1)
            return super().claim_next(request_id)

    worker, factory = SlowWorker(), Factory()
    owner = SimpleNamespace(persistence=OwnerPart(), gateway_runtime=OwnerPart())
    coordinator = TaskResultCoordinator(
        worker, factory, poll_interval_s=0.01, request_preparer=preparer(owner),
    )
    coordinator.start()
    assert await asyncio.to_thread(started.wait, 1)
    stopping = asyncio.create_task(coordinator.stop_claiming())
    await asyncio.sleep(0)
    assert not stopping.done()
    release.set()
    await asyncio.wait_for(stopping, timeout=1)
    await asyncio.wait_for(coordinator.stop(), timeout=1)
    assert worker.calls == 1
    assert len(factory.requests) == 1
    assert [item.action for item in worker.settled] == ["delivered"]


@pytest.mark.asyncio
async def test_background_poll_claims_one_result_and_stops():
    worker, factory = Worker(), Factory()
    owner = SimpleNamespace(persistence=OwnerPart(), gateway_runtime=OwnerPart())
    coordinator = TaskResultCoordinator(
        worker, factory, poll_interval_s=0.01, request_preparer=preparer(owner),
    )
    coordinator.start()
    for _ in range(100):
        if worker.settled:
            break
        await asyncio.sleep(0.01)
    await coordinator.stop()
    assert len(factory.requests) == 1
    assert [item.action for item in worker.settled] == ["delivered"]


@pytest.mark.asyncio
async def test_background_poll_recovers_unknown_claim_with_same_request_id():
    class UncertainWorker(Worker):
        def __init__(self):
            super().__init__()
            self.request_ids = []

        def claim_next(self, request_id):
            self.request_ids.append(request_id)
            if len(self.request_ids) == 1:
                raise AdminDataError("ADMIN_WRITE_RESULT_UNKNOWN", 503, request_id, True)
            if len(self.request_ids) == 2:
                # Capability refresh can fail before Admin sees the replay.
                raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)
            return super().claim_next(request_id)

    worker, factory = UncertainWorker(), Factory()
    owner = SimpleNamespace(persistence=OwnerPart(), gateway_runtime=OwnerPart())
    sequence = iter(range(1, 1000))
    coordinator = TaskResultCoordinator(
        worker, factory, poll_interval_s=0.01,
        request_id_factory=lambda: f"claim-{next(sequence)}",
        request_preparer=preparer(owner),
    )
    coordinator.start()
    try:
        for _ in range(100):
            if worker.settled:
                break
            await asyncio.sleep(0.01)
    finally:
        await coordinator.stop()
    assert worker.request_ids[:3] == ["claim-1", "claim-1", "claim-1"]
    assert len(factory.requests) == 1
    assert [item.action for item in worker.settled] == ["delivered"]


@pytest.mark.asyncio
async def test_terminal_replay_rotates_to_a_new_claim_request():
    class TerminalWorker(Worker):
        def __init__(self):
            super().__init__()
            self.request_ids = []

        def claim_next(self, request_id):
            self.request_ids.append(request_id)
            if len(self.request_ids) == 1:
                raise AdminDataError("ADMIN_WRITE_RESULT_UNKNOWN", 503, request_id, True)
            if len(self.request_ids) == 2:
                raise AdminDataError("TASK_SESSION_RETURN_STATE_UNKNOWN", 409, request_id)
            return super().claim_next(request_id)

    worker, factory = TerminalWorker(), Factory()
    owner = SimpleNamespace(persistence=OwnerPart(), gateway_runtime=OwnerPart())
    sequence = iter(range(1, 1000))
    coordinator = TaskResultCoordinator(
        worker, factory, poll_interval_s=0.01,
        request_id_factory=lambda: f"claim-{next(sequence)}",
        request_preparer=preparer(owner),
    )
    coordinator.start()
    try:
        for _ in range(100):
            if worker.settled:
                break
            await asyncio.sleep(0.01)
    finally:
        await coordinator.stop()
    assert worker.request_ids[:3] == ["claim-1", "claim-1", "claim-2"]
    assert len(factory.requests) == 1


def test_unknown_claim_recovers_only_with_original_request_and_same_input(monkeypatch):
    from services.admin_data import task_session_result_data as data

    monkeypatch.setattr(data, "require_task_result_capability", lambda _client, _id: None)

    def grant(purpose, scopes, token):
        return DelegationCreatedDTO(
            token=token, purpose=purpose, thread_id="source-1",
            run_id=None, editor_session_id=None, scopes=scopes,
            expires_at="2099-01-01T00:00:00Z",
            maximum_expires_at="2099-01-02T00:00:00Z",
        )

    output = TaskResultClaimNextOutputDTO(claim=TaskResultClaimOutputDTO(
        result=claim().result, actor_id="42", source_session_id="claude-session",
        source_input_message_id="source-input", source_input_text="Summary",
        source_persistence_authorization=grant(
            "server-persistence", ["dream:read", "dream:write"], "idg_" + "A" * 43,
        ),
        source_gateway_authorization=grant(
            "gateway-cli", ["messages:create", "messages:count_tokens", "models:list"],
            "idg_" + "B" * 43,
        ),
    ))

    class Client:
        def __init__(self):
            self.calls = []

        def execute(self, operation, input_dto, request_id):
            self.calls.append((operation.capability.name, input_dto.model_dump(mode="json"), request_id))
            if len(self.calls) == 1:
                raise AdminDataError("ADMIN_WRITE_RESULT_UNKNOWN", 503, request_id, True)
            return output

        def receipt(self, *_args, **_kwargs):
            raise AssertionError("Bearer-bearing claim cannot use a plain receipt")

    client = Client()
    worker = AdminTaskResultWorkerData(
        client, runtime_http_config=RuntimeHttpConfig("http://127.0.0.1:39000"),
        session_broker_settings=SessionProjectionBrokerSettings(timeout_seconds=1, max_bytes=1024),
    )
    recovered = worker.claim_next("original-request")
    assert recovered is not None
    assert recovered.result.notification_id == "notice-1"
    assert recovered.persistence_grant.token == "idg_" + "A" * 43
    assert recovered.gateway_grant.token == "idg_" + "B" * 43
    assert client.calls == [
        ("task-session.result-claim-next", {}, "original-request"),
        ("task-session.result-claim-next", {}, "original-request"),
    ]
