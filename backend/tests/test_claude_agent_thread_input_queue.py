# [Input] Production ThreadFactory queue methods and strict Admin queue DTOs with isolated fake provider responses.
# [Output] Verify stable enqueue, input-arrival wake, ordered single claim, selection interrupt and fail-closed interrupt failure.
# [Pos] Provider-free queue contract tests; no model, HTTP service or database.
# [Sync] 2026-09-26: exercise the real per-Thread owner and queue transitions.
# [Sync] 2026-09-28: verify a result-owned Factory turn drains a queued user input before owner completion.
# [Sync] 2026-09-28: verify wait_threads can wake on a newly accepted source input without claiming consumption.
# [Sync] 2026-09-28: verify selection records only an acknowledged, turn-scoped interrupt.
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from claude_agent.service import ClaudeAgentRunRequest
from claude_agent.thread_factory import ClaudeAgentThreadFactory
from claude_agent.stream_events import NormalizedAgentEvent
from services.admin_data.chat_models import QueueEntryDTO


class QueueProvider:
    def __init__(self) -> None:
        self.entries: dict[str, QueueEntryDTO] = {}
        self.sequence = 0
        self.interrupted = 0
        self.interrupt_failure = False
        self.closed = 0

    def start(self):
        return None

    def close(self):
        self.closed += 1

    def list_inputs(self, input_dto, request_id, *, access_token):
        return SimpleNamespace(entries=[row for row in self.entries.values()
                                        if row.thread_id == input_dto.thread_id])

    def enqueue_input(self, input_dto, request_id, *, access_token):
        self.sequence += 1
        import json
        text = "\n".join(part["text"] for part in json.loads(input_dto.parts_json))
        row = QueueEntryDTO(message_id=input_dto.message_id, thread_id=input_dto.thread_id,
                            queue_sequence=str(self.sequence), status="queued", revision=1,
                            dispatch_turn_id=None, created_at="2026-09-26T00:00:00Z", text=text)
        self.entries[row.message_id] = row
        return SimpleNamespace(entry=row)

    def list_queued_inputs(self, *, actor_id, thread_id):
        return [row for row in self.entries.values() if row.thread_id == thread_id]

    def transition_queued_input(self, *, actor_id, thread_id, message_id, expected_revision,
                                action, dispatch_turn_id):
        row = self.entries[message_id]
        assert row.thread_id == thread_id and row.revision == expected_revision
        next_status = {"select": "selected", "claim": "dispatching", "consume": "consumed",
                       "fail": "failed", "mark_unknown": "state_unknown"}[action]
        row = row.model_copy(update={"status": next_status, "revision": row.revision + 1,
                                     "dispatch_turn_id": dispatch_turn_id if action == "claim"
                                     else row.dispatch_turn_id})
        self.entries[message_id] = row
        return row

    async def interrupt(self):
        self.interrupted += 1
        if self.interrupt_failure:
            raise RuntimeError("interrupt failed")


def owner(factory: ClaudeAgentThreadFactory, provider: QueueProvider, thread_id: str):
    state = factory._pool.get_or_create(thread_id)
    state.mark_running()
    state.with_runner(provider)
    request = ClaudeAgentRunRequest(user_id="42", thread_id=thread_id,
                                    message_parts=[{"type": "text", "text": "first"}],
                                    admin_turn_persistence=provider)
    factory._input_templates[thread_id] = request
    factory._input_accepting.add(thread_id)
    return request, state


@pytest.mark.asyncio
async def test_queue_claims_one_message_in_sequence_and_replays_same_id():
    factory = ClaudeAgentThreadFactory()
    provider = QueueProvider()
    request, state = owner(factory, provider, "thread-queue")
    async def add(message_id, text):
        return await factory.enqueue_input(thread_id=request.thread_id, user_id="42",
                                           message_id=message_id, parts=[{"type": "text", "text": text}],
                                           title_candidate=text, tool_choice="auto", chat=provider,
                                           access_token="owned-token")
    first = await add("message-a", "one")
    assert (await add("message-a", "one")).message_id == first.message_id
    with pytest.raises(RuntimeError, match="CHAT_MESSAGE_IDENTITY_CONFLICT"):
        await add("message-a", "different")
    second = await add("message-b", "two")
    assert (first.queue_sequence, second.queue_sequence, provider.sequence) == ("1", "2", 2)
    item, claim = await factory._claim_next_input(request, state)
    assert (item.message_id, claim.status) == ("message-a", "dispatching")
    assert len(factory._input_queues[request.thread_id]) == 1
    provider.transition_queued_input(actor_id="42", thread_id=request.thread_id,
                                     message_id="message-a", expected_revision=claim.revision,
                                     action="consume", dispatch_turn_id=claim.dispatch_turn_id)
    item, claim = await factory._claim_next_input(request, state)
    assert (item.message_id, claim.status) == ("message-b", "dispatching")


@pytest.mark.asyncio
async def test_new_input_advances_generation_and_wakes_waiter_once():
    factory = ClaudeAgentThreadFactory()
    provider = QueueProvider()
    request, _state = owner(factory, provider, "thread-wait-input")
    generation = factory.input_generation(request.thread_id)
    waiter = asyncio.create_task(
        factory.wait_for_input_after(
            request.thread_id,
            generation,
            timeout_seconds=1,
        )
    )
    await asyncio.sleep(0)
    await factory.enqueue_input(
        thread_id=request.thread_id,
        user_id="42",
        message_id="message-wake",
        parts=[{"type": "text", "text": "new input"}],
        title_candidate="new input",
        tool_choice="auto",
        chat=provider,
        access_token="owned-token",
    )
    assert await waiter is True
    assert factory.input_generation(request.thread_id) == generation + 1
    assert provider.entries["message-wake"].status == "queued"
    assert await factory.wait_for_input_after(
        request.thread_id,
        generation + 1,
        timeout_seconds=0,
    ) is False


@pytest.mark.asyncio
async def test_selection_signals_current_owner_and_failed_interrupt_does_not_claim():
    factory = ClaudeAgentThreadFactory()
    provider = QueueProvider()
    request, state = owner(factory, provider, "thread-guide")
    await factory.enqueue_input(thread_id=request.thread_id, user_id="42", message_id="message-a",
                                parts=[{"type": "text", "text": "guide"}], title_candidate="guide",
                                tool_choice="auto", chat=provider, access_token="owned-token")
    selected, signalled = await factory.select_input(thread_id=request.thread_id, user_id="42",
                                                      message_id="message-a", expected_revision=1)
    assert (selected.status, signalled, provider.interrupted) == ("selected", True, 1)
    assert state.guide_interrupt_turn_id == state.current_turn_id
    item, claim = await factory._claim_next_input(request, state)
    assert (item.message_id, claim.status) == ("message-a", "dispatching")

    failing_factory = ClaudeAgentThreadFactory()
    failing_provider = QueueProvider()
    failing_provider.interrupt_failure = True
    failed_request, failed_state = owner(failing_factory, failing_provider, "thread-fail")
    await failing_factory.enqueue_input(thread_id=failed_request.thread_id, user_id="42",
                                        message_id="message-b", parts=[{"type": "text", "text": "guide"}],
                                        title_candidate="guide", tool_choice="auto", chat=failing_provider,
                                        access_token="owned-token")
    failed, signalled = await failing_factory.select_input(thread_id=failed_request.thread_id,
                                                            user_id="42", message_id="message-b",
                                                            expected_revision=1)
    assert (failed.status, signalled) == ("failed", False)
    assert failed_state.guide_interrupt_turn_id is None
    assert await failing_factory._claim_next_input(failed_request, failed_state) is None


@pytest.mark.asyncio
async def test_task_result_owner_finishes_queued_user_input_before_releasing_grant(monkeypatch):
    factory = ClaudeAgentThreadFactory()
    provider = QueueProvider()
    first_started, release_first = asyncio.Event(), asyncio.Event()
    second_started, release_second = asyncio.Event(), asyncio.Event()
    executed: list[str] = []

    async def assemble(request, *, state, bus, runner):
        state.system_prompt = "isolated source context"
        return SimpleNamespace(
            request=request, state=state, bus=bus, dream_context=None,
            sdk_terminal_received=False, user_response_committed=False,
            queue_result_failed=False,
        )

    async def execute(execution):
        message_id = execution.request.message_id
        executed.append(message_id)
        if len(executed) == 1:
            first_started.set()
            await release_first.wait()
        else:
            second_started.set()
            await release_second.wait()
        await execution.bus.publish(NormalizedAgentEvent.create(
            "message-final", {"text": "completed"},
        ))
        await execution.bus.publish_terminal(NormalizedAgentEvent.create(
            "finish", {"finishReason": "end_turn"},
        ))
        execution.sdk_terminal_received = True
        execution.user_response_committed = True
        return None

    monkeypatch.setattr(factory._service, "assemble_context", assemble)
    monkeypatch.setattr(factory._service, "execute_session", execute)
    monkeypatch.setattr("claude_agent.thread_factory.ClaudeAgentRunner", lambda: object())
    request = ClaudeAgentRunRequest(
        user_id="42", thread_id="source-result-queue", resume=True,
        message_id="source-result-input", message_parts=[{"type": "text", "text": "result"}],
        message_metadata={"kind": "task-session-result", "sourceTurnId": "source-result-turn",
                          "taskResultNotificationId": "notice-1", "claimId": "claim-1"},
        user_message_pre_persisted=True, task_result_turn_id="source-result-turn",
        admin_turn_persistence=provider,
    )
    stream = factory.run_streaming(request)
    collector = asyncio.create_task(_collect_stream(stream))
    try:
        await asyncio.wait_for(first_started.wait(), timeout=1)
        queued = await factory.enqueue_input(
            thread_id=request.thread_id, user_id="42", message_id="queued-user-input",
            parts=[{"type": "text", "text": "follow-up"}], title_candidate="follow-up",
            tool_choice="auto", chat=provider, access_token="owned-token",
        )
        assert queued.status == "queued"
        release_first.set()
        await asyncio.wait_for(collector, timeout=1)
        await asyncio.wait_for(second_started.wait(), timeout=1)
        assert (await stream.completion).saw_message_final is True
        assert stream.owner_completion is not None and not stream.owner_completion.done()
        assert provider.entries["queued-user-input"].status == "dispatching"
        release_second.set()
        await asyncio.wait_for(stream.owner_completion, timeout=1)
        assert executed == ["source-result-input", "queued-user-input"]
        assert provider.entries["queued-user-input"].status == "consumed"
    finally:
        release_first.set()
        release_second.set()
        await factory.aclose()


async def _collect_stream(stream):
    return [frame async for frame in stream]
