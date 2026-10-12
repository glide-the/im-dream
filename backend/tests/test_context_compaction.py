# [Sync] 2026-10-12: cover latest root usage, exact model windows, cache counts, invalidation and persistence.
# [Input] Public SDK messages, production Service callback/persistence and isolated storage mock.
# [Output] Completion truth, immutable snapshots, replay deduplication and status-only cancellation contracts.
# [Pos] Provider-free technical regression; no normal database or real model.
# [Sync] 2026-10-12: test the production projection and original message persistence.
import asyncio
import importlib
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import Mock

import tests._sdk_stubs  # noqa: F401
from claude_agent_sdk.types import TextBlock
from claude_agent.context_compaction import ContextCompactionTracker, ContextUsageTracker, public_context_usage
from claude_agent.service import ClaudeAgentRunRequest, ClaudeAgentService, _TurnContext
from claude_agent.tool_confirmation_store import ToolConfirmationStore


def status(event_id, value):
    return {"uuid": event_id, "status": value}


def boundary(event_id, trigger):
    return {"uuid": event_id, "compact_metadata": {"trigger": trigger, "pre_tokens": 120}}


class UsageContracts(TestCase):
    def test_final_stream_usage_replaces_early_assistant_zero_and_never_accumulates_requests(self):
        tracker = ContextUsageTracker()
        for tokens in (999, 420):
            tracker.observe_stream({"type": "message_start", "message": {"model": "model", "usage": {"input_tokens": 0}}})
            tracker.observe_assistant("model", {"input_tokens": 0})
            tracker.observe_stream({"type": "message_delta", "usage": {"input_tokens": tokens, "output_tokens": 500}})
            tracker.observe_stream({"type": "message_stop"})
        tracker.observe_assistant("model", {"input_tokens": 0})
        tracker.observe_result({"model": {"contextWindow": 1000}}, "alias", is_error=False)
        self.assertEqual(tracker.metadata()["contextUsage"]["inputTokens"], 420)

    def test_latest_root_input_includes_cache_but_never_output_or_aggregates(self):
        tracker = ContextUsageTracker()
        tracker.observe_assistant("model", {"input_tokens": 400, "cache_read_input_tokens": 10, "cache_creation_input_tokens": 10, "output_tokens": 500})
        tracker.observe_assistant("subagent", {"input_tokens": 9999}, parent="tool")
        self.assertTrue(tracker.observe_result({"model": {"contextWindow": 1000, "inputTokens": 999999}}, "alias", is_error=False))
        self.assertEqual(tracker.metadata()["contextUsage"], {"status": "available", "model": "alias", "inputTokens": 420, "contextWindow": 1000})

    def test_invalid_or_mismatched_window_never_falls_back_to_another_model(self):
        for usage in ({"other": {"contextWindow": 1000}}, {"model": {"contextWindow": 0}}, {"model": {"contextWindow": True}}):
            tracker = ContextUsageTracker()
            tracker.observe_assistant("model", {"input_tokens": 40})
            tracker.observe_result(usage, "alias", is_error=False)
            self.assertEqual(tracker.metadata(), {"contextUsage": {"status": "unavailable"}})
        for count in (True, -1, 1.2, 2**53):
            tracker = ContextUsageTracker()
            tracker.observe_assistant("model", {"input_tokens": count})
            self.assertIsNone(tracker.candidate)

    def test_boundary_invalidation_requires_new_actual_usage_and_terminal_snapshot_is_sealed(self):
        tracker = ContextUsageTracker()
        tracker.observe_assistant("model", {"input_tokens": 40})
        tracker.invalidate()
        tracker.observe_assistant("<synthetic>", {"input_tokens": 0})
        tracker.observe_result({"model": {"contextWindow": 1000}}, "alias", is_error=False)
        self.assertEqual(tracker.metadata(), {"contextUsage": {"status": "unavailable"}})
        tracker.observe_assistant("model", {"input_tokens": 20})
        tracker.observe_result({"model": {"contextWindow": 1000}}, "alias", is_error=False)
        tracker.finish(invalidate=False)
        saved = tracker.metadata()
        tracker.observe_assistant("model", {"input_tokens": 999})
        tracker.observe_result({}, "alias", is_error=True)
        self.assertEqual(tracker.metadata(), saved)

    def test_history_projection_is_closed_and_works_without_compaction_rows(self):
        from routers.claude_agent import PublicChatMetadataDto
        metadata, _ = PublicChatMetadataDto.from_storage({"contextUsage": {"status": "available", "model": "alias", "inputTokens": 0, "contextWindow": 1000, "private": "drop"}})
        self.assertEqual(metadata.contextUsage, {"status": "available", "model": "alias", "inputTokens": 0, "contextWindow": 1000})
        self.assertIsNone(public_context_usage({"status": "available", "model": "alias", "inputTokens": True, "contextWindow": 1000}))


class TrackerContracts(TestCase):
    def test_public_history_retains_only_closed_compaction_fields(self):
        from routers.claude_agent import PublicChatMetadataDto
        metadata, malformed = PublicChatMetadataDto.from_storage({
            "contextCompactions": [
                {"id": "bad", "state": "completed", "trigger": None},
                {"id": "actual", "state": "completed", "trigger": "manual", "private": "drop"},
            ],
            "compactCompletionText": "Compacted",
        })
        self.assertFalse(malformed)
        self.assertEqual(metadata.contextCompactions, [{"id": "actual", "state": "completed", "trigger": "manual"}])
        self.assertEqual(metadata.compactCompletionText, "Compacted")

    def test_null_and_success_are_not_a_completion_boundary(self):
        tracker = ContextCompactionTracker()
        tracker.consume("status", status("start", "compacting"))
        earlier = tracker.metadata()
        tracker.consume("status", status("end-status", None))
        self.assertEqual(tracker.rows[0]["state"], "unconfirmed")
        tracker.finish("unconfirmed")
        self.assertEqual(tracker.rows[0]["trigger"], None)
        self.assertEqual(earlier["contextCompactions"][0]["state"], "running")

    def test_actual_boundary_recovers_missing_start_and_has_real_source(self):
        tracker = ContextCompactionTracker()
        self.assertTrue(tracker.consume("compact_boundary", boundary("boundary", "auto")))
        self.assertEqual(tracker.rows, [{"id": "boundary", "state": "completed", "trigger": "auto"}])
        self.assertFalse(tracker.finish("failed"))

    def test_retry_and_repeated_events_update_one_cycle(self):
        tracker = ContextCompactionTracker()
        tracker.consume("status", status("start", "compacting"))
        self.assertFalse(tracker.consume("status", status("repeat-running", "compacting")))
        tracker.consume("status", status("idle", None))
        tracker.consume("status", status("retry-start", "compacting"))
        tracker.consume("compact_boundary", boundary("completed", "manual"))
        self.assertFalse(tracker.consume("compact_boundary", boundary("completed", "manual")))
        self.assertFalse(tracker.consume("status", status("start", "compacting")))
        self.assertFalse(tracker.consume("status", status("late-idle", None)))
        self.assertEqual(len(tracker.rows), 1)
        self.assertEqual(tracker.rows[0]["state"], "completed")

    def test_later_cycle_does_not_rewrite_completed_facts(self):
        tracker = ContextCompactionTracker()
        tracker.consume("compact_boundary", boundary("first", "manual"))
        tracker.consume("status", status("second", "compacting"))
        tracker.finish("cancelled")
        self.assertEqual([row["state"] for row in tracker.rows], ["completed", "cancelled"])

    def test_terminal_turn_cannot_accept_late_callbacks_as_a_new_cycle(self):
        tracker = ContextCompactionTracker()
        tracker.consume("status", status("start", "compacting"))
        tracker.finish("cancelled")
        saved = tracker.metadata()
        self.assertFalse(tracker.consume("compact_boundary", boundary("late", "manual")))
        self.assertFalse(tracker.consume("status", status("late-start", "compacting")))
        self.assertFalse(tracker.record_completion_text("Compacted"))
        self.assertFalse(tracker.finish("failed"))
        self.assertEqual(tracker.metadata(), saved)

    def test_malformed_messages_do_not_create_or_complete_a_row(self):
        tracker = ContextCompactionTracker()
        for subtype, data in [("status", {"uuid": "missing-status"}), ("status", {"status": "compacting"}),
                              ("status", status("other", "working")),
                              ("compact_boundary", boundary("bad-trigger", "other")),
                              ("compact_boundary", {"uuid": "missing-metadata"})]:
            self.assertFalse(tracker.consume(subtype, data))
        self.assertEqual(tracker.metadata(), {})

    def test_synthetic_text_before_boundary_is_not_itself_success(self):
        tracker = ContextCompactionTracker()
        self.assertFalse(tracker.record_completion_text("Compacted"))
        self.assertEqual(tracker.metadata(), {})
        tracker.consume("compact_boundary", boundary("real", "manual"))
        self.assertEqual(tracker.metadata()["compactCompletionText"], "Compacted")


class ServiceContracts(IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = ClaudeAgentService()
        self.queue = asyncio.Queue()
        self.ctx = _TurnContext(queue=self.queue, confirmation_store=ToolConfirmationStore())
        self.execution = SimpleNamespace(
            turn_context=self.ctx,
            state=SimpleNamespace(session_id="owned-thread", turn_count=1, current_turn_id="owned-turn"),
            request=ClaudeAgentRunRequest(user_id="7", thread_id="owned-thread"),
            resume_existing_session=None,
            dream_context=None,
        )

    async def observe(self, subtype, data):
        # Older Runner suites replace the SDK module at collection time. Build
        # the public DTO from the same currently injected module as Service.
        message_type = importlib.import_module("claude_agent_sdk.types").SystemMessage
        await self.service._observe_sdk_message(self.execution, message_type(subtype=subtype, data=data))

    async def test_actual_assistant_and_result_usage_share_existing_frame_and_persistence(self):
        types = importlib.import_module("claude_agent_sdk.types")
        self.execution.request.model = "alias"
        message = types.AssistantMessage(content=[])
        message.model = "model"; message.usage = {"input_tokens": 400, "cache_read_input_tokens": 20}
        await self.service._observe_sdk_message(self.execution, message)
        result = types.ResultMessage()
        result.is_error = False; result.model_usage = {"model": {"contextWindow": 1000}}
        await self.service._observe_sdk_message(self.execution, result)
        event = await asyncio.wait_for(self.queue.get(), timeout=2)
        self.assertEqual(event.type, "message-metadata")
        self.assertEqual(event.data["contextUsage"]["inputTokens"], 420)
        save = Mock(); self.service._save_assistant_message = save
        await self.service._finish_context_compaction(self.execution, "unconfirmed")
        await self.service._persist_assistant_turn(self.execution, SimpleNamespace(full_text="OK", session_id=None, usage=None, duration_ms=1))
        self.assertEqual(save.call_args.kwargs["metadata"]["contextUsage"], event.data["contextUsage"])

    async def test_final_root_stream_input_reaches_metadata_without_early_zero(self):
        types = importlib.import_module("claude_agent_sdk.types")
        self.execution.request.model = "alias"
        for event in ({"type": "message_start", "message": {"model": "model", "usage": {"input_tokens": 0}}},
                      {"type": "message_delta", "usage": {"input_tokens": 420}}, {"type": "message_stop"}):
            await self.service._observe_sdk_message(self.execution, types.StreamEvent(event=event))
        result = types.ResultMessage(); result.is_error = False
        result.model_usage = {"model": {"contextWindow": 1000}}
        await self.service._observe_sdk_message(self.execution, result)
        metadata = await asyncio.wait_for(self.queue.get(), timeout=2)
        self.assertEqual(metadata.data["contextUsage"]["inputTokens"], 420)

    async def test_callback_uses_existing_metadata_frame_and_copies_snapshots(self):
        await self.observe("status", status("start", "compacting"))
        first = await asyncio.wait_for(self.queue.get(), timeout=2)
        await self.observe("compact_boundary", boundary("actual", "auto"))
        second = await asyncio.wait_for(self.queue.get(), timeout=2)
        self.assertEqual(first.type, "message-metadata")
        self.assertEqual(first.data["contextCompactions"][0]["state"], "running")
        self.assertEqual(second.data["contextCompactions"][0]["state"], "completed")
        self.assertEqual(second.data["turnId"], "owned-turn")
        await self.observe("compact_boundary", boundary("actual", "auto"))
        self.assertTrue(self.queue.empty())

    async def test_only_sdk_synthetic_completion_can_replace_legacy_text(self):
        await self.observe("compact_boundary", boundary("actual", "manual"))
        message_type = importlib.import_module("claude_agent_sdk.types").AssistantMessage
        ordinary = message_type(content=[TextBlock(text="Compacted")]); ordinary.model = "real-model"
        await self.service._observe_sdk_message(self.execution, ordinary)
        self.assertNotIn("compactCompletionText", self.ctx.compaction.metadata())
        synthetic = message_type(content=[TextBlock(text="Compacted")]); synthetic.model = "<synthetic>"
        await self.service._observe_sdk_message(self.execution, synthetic)
        self.assertEqual(self.ctx.compaction.metadata()["compactCompletionText"], "Compacted")

    async def test_status_only_cancel_persists_without_fabricating_text(self):
        await self.observe("status", status("start", "compacting"))
        save = Mock()
        self.service._save_assistant_message = save
        await self.service._persist_partial_assistant(self.execution, turn_status="cancelled")
        values = save.call_args.kwargs
        self.assertEqual(values["parts"], [])
        self.assertEqual(values["metadata"]["turnStatus"], "cancelled")
        self.assertEqual(values["metadata"]["contextCompactions"][0]["state"], "cancelled")

    async def test_completion_metadata_preserves_original_final_text_protocol(self):
        await self.observe("compact_boundary", boundary("actual", "auto"))
        await self.service._make_text_delta_cb(self.queue, self.ctx)("Continue normally")
        await self.service._make_text_done_cb(self.queue, self.ctx)("Continue normally")
        save = Mock(); self.service._save_assistant_message = save
        result = SimpleNamespace(full_text="Continue normally", session_id=None, usage=None, duration_ms=100)
        await self.service._persist_assistant_turn(self.execution, result)
        values = save.call_args.kwargs
        self.assertEqual(values["parts"], [{"type": "text", "text": "Continue normally"}])
        self.assertEqual(values["history_final_text"], "Continue normally")
        self.assertEqual(values["metadata"]["finalPartIndex"], 0)
        self.assertEqual(values["metadata"]["contextCompactions"][0]["trigger"], "auto")
