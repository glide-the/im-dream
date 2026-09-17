"""Deck-scoped Chat history list regressions.

[Input] Strict Admin Chat DTOs and the public Claude-thread listing route.
[Output] Verify deck_id remains a typed server-side ownership filter.
[Pos] Admin DTO consumer contract tests in backend/tests; no Dream SQL fixture.
[Sync] 2026-09-16: replace the retired Dream database mock with Admin DTO injection.
"""

from __future__ import annotations

import asyncio

import pytest
from pydantic import ValidationError

from routers import claude_agent as claude_agent_router
from services.admin_data import chat_models as chat_dto


def test_thread_list_dto_rejects_caller_supplied_user_identity() -> None:
    with pytest.raises(ValidationError):
        chat_dto.ThreadListInputDTO(
            deck_id="deck-a",
            limit=20,
            offset=0,
            user_id="28",
        )


def test_thread_route_forwards_deck_filter_without_search(monkeypatch) -> None:
    calls: list[tuple[object, object]] = []

    def list_threads(*_args, **_kwargs):
        raise AssertionError("the route must call this through invoke_admin_operation")

    chat = type("Chat", (), {"list_threads": staticmethod(list_threads)})()

    async def invoke(current_user, operation, input_dto):
        calls.append((current_user, input_dto))
        assert operation is chat.list_threads
        return chat_dto.ThreadListResultDTO(
            threads=[
                chat_dto.ChatThreadSummaryDTO(
                    id="thread-a",
                    title="Related conversation",
                    deck_id=input_dto.deck_id,
                    voice_id="voice-a",
                    created_at="2026-08-16T00:00:00Z",
                    updated_at="2026-08-17T00:00:00Z",
                )
            ]
        )

    monkeypatch.setattr(claude_agent_router, "_chat_invoke", invoke)

    payload = asyncio.run(
        claude_agent_router.claude_agent_list_threads(
            deck_id="deck-a",
            query=None,
            search_scope="all",
            retrieval_mode=None,
            vector_query=None,
            min_score=None,
            limit=20,
            offset=0,
            current_user={"user_id": 28},
            chat=chat,
        )
    )

    assert len(calls) == 1
    assert calls[0][0] == {"user_id": 28}
    assert calls[0][1] == chat_dto.ThreadListInputDTO(
        deck_id="deck-a", limit=20, offset=0
    )
    assert payload == {
        "threads": [
            {
                "id": "thread-a",
                "title": "Related conversation",
                "deck_id": "deck-a",
                "voice_id": "voice-a",
                "created_at": "2026-08-16T00:00:00Z",
                "updated_at": "2026-08-17T00:00:00Z",
            }
        ]
    }
