# [Input] Public task-session detail route, current router inventory, owner-bound Admin DTOs and saved target Chat messages.
# [Output] Completed detail only from a final assistant projection and absence of the retired public task-results route.
# [Pos] Provider-free task-session detail regression; wait_threads owns active parent completion delivery.
# [Sync] 2026-09-28: require removal of the task-results polling route after adopting wait_threads.
# [Sync] 2026-09-27: cover the saved Notion child-result gap without inventing a notification dispatch.
from __future__ import annotations

import pytest
from fastapi import HTTPException

from routers import claude_agent as route
from services.admin_data.chat_models import (
    ChatMessageDTO,
    ChatThreadDTO,
    MessagePageResultDTO,
    TaskSessionDTO,
    TaskSessionResultDTO,
    ThreadResultDTO,
)
from services.admin_data.request_auth import AdminRequestActor


SOURCE = "source-thread"
TARGET = "target-thread"
TASK = "task-id"


def actor(user_id: str = "42") -> dict:
    return AdminRequestActor(
        subject=f"account:{user_id}", canonical_user_id=user_id,
        client_id="dream", scopes=frozenset({"dream:read", "dream:write"}),
        issued_at=1, expires_at=9999999999, access_token="test-token",
    ).current_user_projection()


def thread(thread_id: str, user_id: str = "42") -> ChatThreadDTO:
    return ChatThreadDTO(
        id=thread_id, user_id=user_id, title="Task", deck_id=None, voice_id=None,
        claude_session_id="opaque-session", agent_contract_version="v1",
        created_at="2026-09-27T00:00:00Z", updated_at="2026-09-27T00:01:00Z",
    )


def task() -> TaskSessionDTO:
    return TaskSessionDTO(
        task_id=TASK, source_thread_id=SOURCE, thread_id=TARGET,
        title="Read today's note", initial_message_id="first-message",
        initial_message="Read today's note", launch_status="starting",
        launch_error_code=None, created_at="2026-09-27T00:00:00Z",
    )


def message(role: str = "assistant", *, completed: bool = True) -> ChatMessageDTO:
    final = role == "assistant" and completed
    return ChatMessageDTO(
        id="saved-result", role=role, parts=[{"type": "text", "text": "Result"}],
        metadata={"turnStatus": "completed"} if final else {"turnStatus": "cancelled"},
        metadata_decode_error=False, created_at="2026-09-27T00:01:00Z",
        history_final_text="Result" if final else None,
        history_process_available=False, history_projection_version=1 if final else None,
    )


class Chat:
    def __init__(self, latest: ChatMessageDTO, *, owned: bool = True) -> None:
        self.latest = latest
        self.owned = owned

    def get_thread(self, input_dto, request_id, *, access_token):
        assert access_token == "test-token"
        return ThreadResultDTO(thread=thread(input_dto.thread_id) if self.owned else None)

    def get_task_session(self, input_dto, request_id, *, access_token):
        assert input_dto.source_thread_id == SOURCE and input_dto.task_id == TASK
        return TaskSessionResultDTO(task=task())

    def message_page(self, input_dto, request_id, *, access_token):
        assert input_dto.thread_id == TARGET and input_dto.limit == 1
        return MessagePageResultDTO(messages=[self.latest], has_more=False, latest_message_id=self.latest.id)


@pytest.mark.asyncio
async def test_completed_child_result_is_read_from_authorized_saved_assistant(monkeypatch):
    monkeypatch.setattr(route.claude_agent_thread_factory, "session_snapshot", lambda _id: None)
    result = await route.claude_agent_task_session_get(SOURCE, TASK, current_user=actor(), chat=Chat(message()))
    assert result["status"] == "completed"
    assert result["result_message_id"] == "saved-result"
    assert result["result_text"] == "Result"
    assert result["running"] is False


def test_public_task_results_polling_route_is_retired():
    paths = {item.path for item in route.router.routes}
    assert "/api/claude-agent/threads/{thread_id}/task-results" not in paths


@pytest.mark.asyncio
async def test_latest_user_or_partial_assistant_is_never_a_completed_result(monkeypatch):
    monkeypatch.setattr(route.claude_agent_thread_factory, "session_snapshot", lambda _id: None)
    for latest in (message("user"), message(completed=False)):
        result = await route.claude_agent_task_session_get(SOURCE, TASK, current_user=actor(), chat=Chat(latest))
        assert result["status"] == "state_unknown"
        assert result["result_message_id"] is None
        assert result["result_text"] is None


@pytest.mark.asyncio
async def test_running_child_is_not_reported_complete_from_previous_final(monkeypatch):
    monkeypatch.setattr(route.claude_agent_thread_factory, "session_snapshot", lambda _id: {"lifecycle": "running"})
    result = await route.claude_agent_task_session_get(SOURCE, TASK, current_user=actor(), chat=Chat(message()))
    assert result["status"] == "running"
    assert result["result_message_id"] is None


@pytest.mark.asyncio
async def test_source_thread_ownership_precedes_target_message_read(monkeypatch):
    monkeypatch.setattr(route.claude_agent_thread_factory, "session_snapshot", lambda _id: None)
    chat = Chat(message(), owned=False)
    with pytest.raises(HTTPException) as exc:
        await route.claude_agent_task_session_get(SOURCE, TASK, current_user=actor("999"), chat=chat)
    assert exc.value.status_code == 404
