# [Input] Production scheduled-task DTO port, current-turn Tool bridge and explicit fake Admin capability snapshots.
# [Output] Prove fail-closed capability checks and stable source/Tool-call authorization for schedule creation.
# [Pos] Provider-free scheduled Chat consumer contract tests; no database, browser account or model call.
# [Sync] 2026-10-07: prove a scheduled manual-tool request fails even when the stream later emits a successful final event.
# [Sync] 2026-10-07: guard the v3 source/new Thread contract, captured model alias and uncertain start receipts.
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from libs.claude_agent_kit.server.session_projection_protocol import ThreadToolCommandRequestDTO
from routers.claude_agent import _ThreadToolTurnProvider
from services.admin_data.errors import AdminDataError
from services.admin_data.scheduled_task_data import (
    AdminScheduledTaskData, CREATE_TASK_V3, CreateScheduledTaskV3InputDTO,
    DailyRuleDTO, DAY_TASK_V3, DayScheduledTaskInputDTO,
    PREPARE_TRIGGER_V3, RENEW_TRIGGER_V3, START_TRIGGER_V3, FINISH_TRIGGER_V3,
)
from claude_agent.scheduled_task_coordinator import ScheduledTaskCoordinator
from claude_agent.chat_stream_adapter import ChatStreamAdapter
from claude_agent.stream_events import NormalizedAgentEvent


class CapabilityClient:
    def __init__(self, *, supported: bool, supported_after_refresh: bool | None = None,
                 refresh_error: bool = False):
        self.supported = supported
        self.supported_after_refresh = supported_after_refresh
        self.refresh_error = refresh_error
        self.executed = []
        self.refreshes = []

    def capabilities_snapshot(self, request_id):
        return object()

    def supports(self, operations, requirements):
        assert operations == (DAY_TASK_V3,)
        assert len(requirements) == 3
        return self.supported

    def capabilities(self, request_id):
        self.refreshes.append(request_id)
        if self.refresh_error:
            raise AdminDataError("ADMIN_DATA_UNAVAILABLE", 503, request_id)
        if self.supported_after_refresh is not None:
            self.supported = self.supported_after_refresh
        return object()

    def execute(self, operation, input_dto, request_id, *, access_token=None):
        self.executed.append((operation, input_dto, request_id, access_token))
        return SimpleNamespace(tasks=[], triggers=[])


def test_scheduled_date_requires_all_three_published_admin_capabilities():
    client = CapabilityClient(supported=False)
    with pytest.raises(AdminDataError, match="ADMIN_CAPABILITY_UNAVAILABLE"):
        AdminScheduledTaskData(client).execute(
            DAY_TASK_V3, DayScheduledTaskInputDTO(local_date="2026-09-29",
                                               display_time_zone="Asia/Shanghai"),
            "734e880b-7313-4103-bf25-b77ac96df08e", access_token="user-grant",
        )
    assert client.refreshes == ["734e880b-7313-4103-bf25-b77ac96df08e"]
    assert client.executed == []


def test_scheduled_date_refreshes_one_stale_process_catalog_before_dispatch():
    client = CapabilityClient(supported=False, supported_after_refresh=True)
    result = AdminScheduledTaskData(client).execute(
        DAY_TASK_V3, DayScheduledTaskInputDTO(local_date="2026-09-29",
                                           display_time_zone="Asia/Shanghai"),
        "734e880b-7313-4103-bf25-b77ac96df08e", access_token="user-grant",
    )
    assert result.tasks == []
    assert client.refreshes == ["734e880b-7313-4103-bf25-b77ac96df08e"]
    assert len(client.executed) == 1


def test_scheduled_date_stays_fail_closed_when_catalog_refresh_fails():
    client = CapabilityClient(supported=False, refresh_error=True)
    with pytest.raises(AdminDataError, match="ADMIN_DATA_UNAVAILABLE"):
        AdminScheduledTaskData(client).execute(
            DAY_TASK_V3, DayScheduledTaskInputDTO(local_date="2026-09-29",
                                               display_time_zone="Asia/Shanghai"),
            "734e880b-7313-4103-bf25-b77ac96df08e", access_token="user-grant",
        )
    assert client.refreshes == ["734e880b-7313-4103-bf25-b77ac96df08e"]
    assert client.executed == []


def test_scheduled_tool_uses_current_turn_grant_and_stable_call_key():
    calls = []

    class Persistence:
        def current_grant(self, *, actor_id, thread_id):
            assert (actor_id, thread_id) == ("42", "source-thread")
            return SimpleNamespace(token="idg_current_turn")

    def create(_self, operation, input_dto, request_id, *, access_token):
        assert operation is CREATE_TASK_V3
        assert isinstance(input_dto, CreateScheduledTaskV3InputDTO)
        assert isinstance(input_dto.rule, DailyRuleDTO)
        assert input_dto.target_editor_session_id is None
        assert input_dto.run_thread_mode == "source_thread"
        assert input_dto.model_alias == "dream-balanced"
        calls.append((input_dto, request_id, access_token))
        return SimpleNamespace(task=SimpleNamespace(
            id="734e880b-7313-4103-bf25-b77ac96df08e", title=input_dto.title,
            rule=input_dto.rule, next_run_at="2026-09-29T01:00:00Z", status="active", revision=1,
            run_thread_mode=input_dto.run_thread_mode, model_alias=input_dto.model_alias,
        ))

    async def run():
        provider = _ThreadToolTurnProvider(
            loop=asyncio.get_running_loop(), current_user={"user_id": "42"},
            chat=None, owner=SimpleNamespace(client=object()),
            source_thread_id="source-thread", source_message_id="source-message",
            timeout_seconds=2, model_alias="dream-balanced", turn_persistence=Persistence(),
        )
        command = ThreadToolCommandRequestDTO(
            capability="c" * 43, request_id="734e880b-7313-4103-bf25-b77ac96df08e",
            operation="schedule.create", tool_call_id="model-call",
            title="Morning note", prompt="Summarize my notes",
            schedule_rule={"kind": "daily", "local_time": "09:00", "time_zone": "Asia/Shanghai"},
        )
        first = await provider._perform(command)
        second = await provider._perform(command)
        assert first.scheduled_task == second.scheduled_task
        assert first.scheduled_task["revision"] == 1

    with patch("routers.claude_agent.AdminScheduledTaskData.execute", create):
        asyncio.run(run())
    assert calls[0][0].create_request_key == calls[1][0].create_request_key
    assert calls[0][1] == calls[0][0].create_request_key
    assert calls[0][2] == "idg_current_turn"


def test_schedule_broker_rejects_model_authored_actor_fields():
    with pytest.raises(ValueError):
        ThreadToolCommandRequestDTO(
            capability="c" * 43, request_id="734e880b-7313-4103-bf25-b77ac96df08e",
            operation="schedule.create", tool_call_id="model-call",
            title="Task", prompt="Do work", user_id="42",
            schedule_rule={"kind": "once", "local_date": "2026-09-29", "local_time": "09:00",
                           "time_zone": "Asia/Shanghai", "selected_offset_minutes": None},
        )


@pytest.mark.parametrize(
    ("approval_violation", "expected_status", "expected_error"),
    [
        (None, "succeeded", None),
        ("SCHEDULE_TOOL_APPROVAL_REQUIRED", "failed", "SCHEDULE_TOOL_APPROVAL_REQUIRED"),
    ],
)
def test_worker_binds_admin_turn_before_canonical_chat_stream(
    monkeypatch, approval_violation, expected_status, expected_error,
):
    from claude_agent import scheduled_task_coordinator as worker_module
    from routers import claude_agent as routes

    steps = []
    trigger = SimpleNamespace(
        id="734e880b-7313-4103-bf25-b77ac96df08e",
        target_thread_id="target-thread", input_message_id="target-input",
    )
    claim_id = "832624ec-6cb6-484b-8ca9-a93d39811af0"
    owner = SimpleNamespace(client=object(), runtime_http_config=object(),
                            session_broker_settings=object())
    coordinator = ScheduledTaskCoordinator(owner, poll_interval_seconds=2)
    prepared = SimpleNamespace(prepared=True, task_session=None, trigger=trigger,
                               authority_token="sta_authority", authority_expires_at="2099-01-01T00:00:00Z",
                               target_editor_session_id=None, target_thread_id="target-thread",
                               input_message_id="target-input", resume_existing_thread=True,
                               model_alias="dream-balanced")
    authority = SimpleNamespace(trigger_id=trigger.id, claim_id=claim_id,
                                target_thread_id="target-thread", canonical_user_id="42",
                                subject="user-subject", client_id="scheduled-client",
                                    scopes=["dream:read", "dream:write"],
                                    target_editor_session_id=None,
                                issued_at="2026-09-28T00:00:00Z",
                                expires_at="2099-01-01T00:00:00Z")

    async def execute(operation, input_dto, request_id):
        if operation is PREPARE_TRIGGER_V3:
            steps.append("prepare")
            return prepared
        if operation is START_TRIGGER_V3:
            steps.append("start")
            return SimpleNamespace(trigger=SimpleNamespace(target_turn_id=input_dto.target_turn_id))
        if operation is FINISH_TRIGGER_V3:
            steps.append(("finish", input_dto.status, input_dto.final_message_id, input_dto.error_code))
            return SimpleNamespace(trigger=trigger)
        raise AssertionError(operation)

    coordinator._execute = execute
    coordinator._data.execute = lambda *args, **kwargs: authority
    monkeypatch.setattr(worker_module, "AdminDelegationCreator", lambda client: SimpleNamespace(
        create=lambda *args, **kwargs: SimpleNamespace(token="idg_grant")))
    monkeypatch.setattr(worker_module, "AdminWorkflowData", lambda client: SimpleNamespace(
        resolve=lambda *args, **kwargs: SimpleNamespace()))
    monkeypatch.setattr(worker_module, "AdminTurnPersistence", lambda *args, **kwargs: SimpleNamespace(close=lambda: None))
    monkeypatch.setattr(worker_module, "AdminRuntimeClient", lambda *args, **kwargs: object())
    monkeypatch.setattr(worker_module, "AdminGatewayRuntime", lambda *args, **kwargs: SimpleNamespace(close=lambda: None))
    monkeypatch.setattr(worker_module, "AdminChatData", lambda client: SimpleNamespace(
        process_detail=lambda *args, **kwargs: SimpleNamespace(message=SimpleNamespace(
            role="user", parts=[{"type": "text", "text": "Summarize my notes"}],
        )),
    ))

    async def chat_stream(body, user, chat, owner, *, scheduled_dispatch):
        steps.append("preflight")
        if approval_violation is not None:
            scheduled_dispatch.tool_approval_violation.record(approval_violation)
        completion = asyncio.get_running_loop().create_future()
        completion.set_result(None)

        async def frames():
            assert steps == ["prepare", "preflight", "start"]
            adapter = ChatStreamAdapter()
            yield adapter.encode(NormalizedAgentEvent.create("message-final", {"text": "done"}))
            yield adapter.encode(NormalizedAgentEvent.create("finish", {"finishReason": "stop"}))

        return SimpleNamespace(body_iterator=frames(), scheduled_owner_completion=completion)

    monkeypatch.setattr(routes, "_claude_agent_stream_impl", chat_stream)
    asyncio.run(coordinator._dispatch(trigger, claim_id))
    assert steps[-1][0] == "finish"
    assert steps[-1][1] == expected_status
    assert (steps[-1][2] is not None) is (expected_status == "succeeded")
    assert steps[-1][3] == expected_error


def test_worker_replays_only_original_uncertain_start_receipt():
    coordinator = ScheduledTaskCoordinator(SimpleNamespace(client=object()), poll_interval_seconds=2)
    seen = []

    async def execute(operation, input_dto, request_id):
        assert operation is START_TRIGGER_V3
        seen.append((input_dto.target_turn_id, request_id))
        if len(seen) == 1:
            raise AdminDataError("ADMIN_OUTCOME_UNKNOWN", 503, request_id, outcome_unknown=True)
        return SimpleNamespace(trigger=SimpleNamespace(target_turn_id=input_dto.target_turn_id))

    coordinator._execute = execute
    result = asyncio.run(coordinator._start(
        "734e880b-7313-4103-bf25-b77ac96df08e",
        "832624ec-6cb6-484b-8ca9-a93d39811af0", "turn-1",
    ))
    assert result.trigger.target_turn_id == "turn-1"
    assert len(seen) == 2 and seen[0] == seen[1]


def test_worker_renew_failure_is_reported_and_requires_reconciliation(monkeypatch, caplog):
    from claude_agent import scheduled_task_coordinator as worker_module

    coordinator = ScheduledTaskCoordinator(SimpleNamespace(client=object()), poll_interval_seconds=2)

    async def expired_wait(_awaitable, *, timeout):
        _awaitable.close()
        raise asyncio.TimeoutError

    async def execute(operation, input_dto, request_id):
        assert operation is RENEW_TRIGGER_V3
        raise AdminDataError("SCHEDULE_LEASE_EXPIRED", 409, request_id)

    monkeypatch.setattr(worker_module.asyncio, "wait_for", expired_wait)
    coordinator._execute = execute
    outcome = asyncio.run(coordinator._renew_until_done(
        "734e880b-7313-4103-bf25-b77ac96df08e",
        "832624ec-6cb6-484b-8ca9-a93d39811af0",
        "2026-09-28T00:00:00Z", asyncio.Event(),
    ))
    assert outcome is False
    assert "SCHEDULE_LEASE_EXPIRED" in caplog.text
