# [Input] Production scheduled Thread route, strict DTOs and explicit fake Admin operation capabilities.
# [Output] Provider-free read/authentication, exact contract and fail-closed relation coverage.
# [Pos] Scheduled activity HTTP and consumer contract tests; no database or model call.
# [Sync] 2026-10-07: cover Thread read registration, empty results, missing operation and source ID mismatch.
import asyncio
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from routers import claude_agent as routes
from services.admin_data.errors import AdminDataError
from services.admin_data.scheduled_task_data import (
    AdminScheduledTaskData, THREAD_TASKS_V2, ScheduledTaskThreadInputDTO,
    ScheduledTaskThreadResultDTO, ScheduledTaskThreadSourceDTO,
)


def test_scheduled_thread_route_requires_production_authentication():
    app = FastAPI()
    app.include_router(routes.router)
    with TestClient(app) as client:
        response = client.get("/api/claude-agent/threads/source/scheduled-tasks")
    assert response.status_code == 401


def test_scheduled_thread_route_passes_exact_thread_read_dto(monkeypatch):
    async def invoke(current_user, method, input_dto):
        assert current_user == {"user_id": "42"}
        assert method.args == (THREAD_TASKS_V2,)
        assert input_dto == ScheduledTaskThreadInputDTO(thread_id="source")
        return ScheduledTaskThreadResultDTO(created=[], source=None)

    monkeypatch.setattr(routes, "invoke_admin_operation", invoke)
    result = asyncio.run(routes.claude_agent_scheduled_thread(
        "source", current_user={"user_id": "42"}, owner=SimpleNamespace(client=object()),
    ))
    assert result == {"created": [], "source": None}


def test_scheduled_thread_operation_is_read_only_and_missing_contract_stays_closed():
    executed = []
    client = SimpleNamespace(
        capabilities_snapshot=lambda request_id: None,
        capabilities=lambda request_id: None,
        supports=lambda operations, requirements: False,
        execute=lambda *args, **kwargs: executed.append(args),
    )
    assert THREAD_TASKS_V2.capability.name == "scheduled-task.v2.thread"
    assert THREAD_TASKS_V2.capability.kind == "read"
    assert THREAD_TASKS_V2.capability.user_scope == "dream:read"
    assert THREAD_TASKS_V2.capability.background_scope is None
    with pytest.raises(AdminDataError, match="ADMIN_CAPABILITY_UNAVAILABLE"):
        AdminScheduledTaskData(client).execute(THREAD_TASKS_V2,
            ScheduledTaskThreadInputDTO(thread_id="source"), "activity-read", access_token="fixture-token")
    assert executed == []


def test_scheduled_source_rejects_a_different_task_id():
    task = {"id": "550e8400-e29b-41d4-a716-446655440000", "source_thread_id": "source", "title": "任务", "prompt": "检查",
        "rule": {"kind": "interval", "interval_minutes": 10, "time_zone": "Asia/Shanghai"},
        "next_run_at": None, "status": "paused", "revision": 2,
        "created_at": "2026-10-07T00:00:00Z", "updated_at": "2026-10-07T00:00:00Z"}
    trigger = {"id": "550e8400-e29b-41d4-a716-446655440001", "task_id": task["id"], "kind": "scheduled", "scheduled_at": None,
        "definition_revision": 1, "title": "任务", "source_thread_id": "source", "time_zone": "Asia/Shanghai",
        "status": "succeeded", "task_session_id": "task-session", "target_thread_id": "execution", "input_message_id": "input",
        "target_turn_id": "turn", "final_message_id": "final", "error_code": None,
        "skipped_from_at": None, "skipped_through_at": None, "created_at": task["created_at"], "updated_at": task["updated_at"]}
    assert ScheduledTaskThreadSourceDTO(task=task, trigger=trigger).task.status == "paused"
    with pytest.raises(ValidationError, match="does not match"):
        ScheduledTaskThreadSourceDTO(task=task, trigger={**trigger, "task_id": trigger["id"]})
