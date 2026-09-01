# [Input] Structured Dream Hook issues, ClaudeAgentService continuation builder, and chat persistence helpers.
# [Output] Verify allowlisted/redacted message construction, stable identity, and persistence-before-SSE ordering.
# [Pos] Dream workbench auto-repair application contract test in backend/tests.
# [Sync] 2026-09-01: initial bounded auto-repair message and dispatch coverage.
# [Sync] 2026-09-01: cover duplicate-root/stage templates, move-not-copy
#                    cleanup guidance, and safe exhausted-error detail.
# [Sync] 2026-09-01: require root-cleanup prompts to reject marker-only
#                    project.yaml deletion observed in the production replay.
# [Sync] 2026-09-01: require ambiguous repair messages and .dream projection
#                    inputs to name the protected root and the only stale roots.
# [Sync] 2026-09-01: keep legacy v1 history readable while requiring every new
#                    project-root repair message to carry server cleanup facts.
# [Sync] 2026-09-01: a completed repair attempt is persisted before its second
#                    Hook failure is classified, so the SSE transcript survives.

"""Dream workbench auto-repair message and continuation tests."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tests._sdk_stubs  # noqa: F401

from claude_agent.service import (
    ClaudeAgentRunRequest,
    ClaudeAgentService,
    _TurnContext,
    _TurnExecution,
)
from claude_agent.thread_pool import AgentRunState
from claude_agent.tool_confirmation_store import ToolConfirmationStore
from libs.claude_agent_kit.types import AgentRunResult
from services.story_workspace.dream_artifact_turn_hook import (
    DreamArtifactRepairability,
    DreamArtifactTurnHookError,
    DreamArtifactValidationIssue,
)
from services.story_workspace.dream_auto_repair_service import (
    DREAM_AUTO_REPAIR_DISPATCHED,
    DREAM_AUTO_REPAIR_METADATA_KIND,
    DreamAutoRepairError,
    DreamAutoRepairExhaustedError,
    build_dream_auto_repair_message,
    dream_auto_repair_metadata_is_valid,
    persist_dream_auto_repair_message,
)
from story_workspace.contracts import StoryWorkspaceDreamRunContext


RUN_ID = "run_0123456789abcdef0123456789abcdef"
PROJECT_CLEANUP = ("server-project", ("workspace-project",))
AMBIGUOUS_PROJECT_CLEANUP = ("server-project", ("stale-project",))


def mismatch_issue(
    *,
    expected: str = "server-project",
    actual: str = "workspace-project",
) -> DreamArtifactValidationIssue:
    return DreamArtifactValidationIssue(
        code="PROJECT_STORY_SLUG_MISMATCH",
        repairability=DreamArtifactRepairability.AGENT_REPAIRABLE,
        public_message="safe",
        expected=expected,
        actual=actual,
    )


def ambiguous_project_issue() -> DreamArtifactValidationIssue:
    return DreamArtifactValidationIssue(
        code="DREAM_CANONICAL_PROJECT_AMBIGUOUS",
        repairability=DreamArtifactRepairability.AGENT_REPAIRABLE,
        public_message="safe",
    )


def duplicate_stage_issue(
    *,
    stage: str = "storyboards",
) -> DreamArtifactValidationIssue:
    return DreamArtifactValidationIssue(
        code="DREAM_STAGE_ENTITY_ID_DUPLICATE",
        repairability=DreamArtifactRepairability.AGENT_REPAIRABLE,
        public_message="safe",
        expected=stage,
        actual="duplicate_entity_id",
    )


def invalid_stage_issue() -> DreamArtifactValidationIssue:
    return DreamArtifactValidationIssue(
        code="DREAM_STAGE_SCHEMA_INVALID",
        repairability=DreamArtifactRepairability.AGENT_REPAIRABLE,
        public_message="safe",
        expected="characters",
        actual="schema_invalid",
    )


def dream_context() -> StoryWorkspaceDreamRunContext:
    return StoryWorkspaceDreamRunContext(
        workflow_run_id=RUN_ID,
        thread_id="thread-auto-repair",
        deck_id="deck-1",
        deck_plugin_id="plugin-1",
        deck_plugin_version="1.0.0",
        deck_plugin_binding_id="binding-1",
        binding_revision=1,
        deck_runtime_snapshot_id="snapshot-1",
        runtime_plugin_lock_id="lock-1",
    )


class RecordingQueue:
    def __init__(self, order: list[str]) -> None:
        self.order = order
        self.events: list[object] = []

    async def put(self, event: object) -> None:
        self.order.append("sse")
        self.events.append(event)


class DreamAutoRepairContractTest(unittest.TestCase):
    def test_message_identity_is_stable_and_body_contains_only_allowlisted_facts(self) -> None:
        first = build_dream_auto_repair_message(
            issue=mismatch_issue(),
            workflow_run_id=RUN_ID,
            thread_id="thread-auto-repair",
            originating_message_id="message-origin",
            originating_turn_id="turn-origin",
            project_cleanup=PROJECT_CLEANUP,
        )
        second = build_dream_auto_repair_message(
            issue=mismatch_issue(),
            workflow_run_id=RUN_ID,
            thread_id="thread-auto-repair",
            originating_message_id="message-origin",
            originating_turn_id="turn-origin",
            project_cleanup=PROJECT_CLEANUP,
        )
        recovered_turn = build_dream_auto_repair_message(
            issue=mismatch_issue(),
            workflow_run_id=RUN_ID,
            thread_id="thread-auto-repair",
            originating_message_id="message-origin",
            originating_turn_id="turn-after-process-recovery",
            project_cleanup=PROJECT_CLEANUP,
        )

        self.assertEqual(first.id, second.id)
        self.assertEqual(first.id, recovered_turn.id)
        self.assertEqual(
            first.metadata["idempotencyKey"],
            recovered_turn.metadata["idempotencyKey"],
        )
        self.assertNotEqual(
            first.metadata["originatingTurnId"],
            recovered_turn.metadata["originatingTurnId"],
        )
        self.assertTrue(first.id.startswith("dream_repair_"))
        self.assertEqual(first.metadata["repairAttempt"], 1)
        self.assertEqual(first.metadata["validationCode"], "PROJECT_STORY_SLUG_MISMATCH")
        text = first.parts[0]["text"]
        self.assertIn("server-project", text)
        self.assertIn("workspace-project", text)
        self.assertIn("移动或合并", text)
        self.assertIn("不得只复制目录", text)
        self.assertIn("唯一 canonical 项目", text)
        self.assertIn("服务器可信项目根（必须保留）：stories/server-project", text)
        self.assertIn("rm -rf -- stories/workspace-project", text)
        self.assertEqual(
            first.metadata["projectCleanup"],
            {
                "trustedProjectSlug": "server-project",
                "staleProjectSlugs": ["workspace-project"],
            },
        )
        self.assertNotIn("postgresql://", text)

    def test_duplicate_project_and_stage_issues_use_bounded_cleanup_templates(self) -> None:
        ambiguous = build_dream_auto_repair_message(
            issue=ambiguous_project_issue(),
            workflow_run_id=RUN_ID,
            thread_id="thread-auto-repair",
            originating_message_id="message-project-ambiguous",
            originating_turn_id="turn-origin",
            project_cleanup=AMBIGUOUS_PROJECT_CLEANUP,
        )
        duplicate = build_dream_auto_repair_message(
            issue=duplicate_stage_issue(),
            workflow_run_id=RUN_ID,
            thread_id="thread-auto-repair",
            originating_message_id="message-stage-duplicate",
            originating_turn_id="turn-origin",
        )
        invalid = build_dream_auto_repair_message(
            issue=invalid_stage_issue(),
            workflow_run_id=RUN_ID,
            thread_id="thread-auto-repair",
            originating_message_id="message-stage-invalid",
            originating_turn_id="turn-origin",
        )

        self.assertEqual(
            ambiguous.metadata["validationCode"],
            "DREAM_CANONICAL_PROJECT_AMBIGUOUS",
        )
        self.assertIn("移除其余重复项目根", ambiguous.parts[0]["text"])
        self.assertIn("不得只删除旧根的 project.yaml", ambiguous.parts[0]["text"])
        self.assertIn(
            "服务器可信项目根（必须保留）：stories/server-project",
            ambiguous.parts[0]["text"],
        )
        self.assertIn(
            "本轮旧项目根（仅允许清理这些路径）：stories/stale-project",
            ambiguous.parts[0]["text"],
        )
        self.assertIn(
            "rm -rf -- stories/stale-project",
            ambiguous.parts[0]["text"],
        )
        self.assertEqual(
            duplicate.metadata["validationCode"],
            "DREAM_STAGE_ENTITY_ID_DUPLICATE",
        )
        self.assertIn("storyboards stage", duplicate.parts[0]["text"])
        self.assertIn("不得仅篡改 entity_id", duplicate.parts[0]["text"])
        self.assertEqual(
            invalid.metadata["validationCode"],
            "DREAM_STAGE_SCHEMA_INVALID",
        )
        self.assertIn("characters stage", invalid.parts[0]["text"])

    def test_new_project_root_repair_has_fact_while_legacy_v1_stays_visible(self) -> None:
        message = build_dream_auto_repair_message(
            issue=mismatch_issue(),
            workflow_run_id=RUN_ID,
            thread_id="thread-auto-repair",
            originating_message_id="message-origin",
            originating_turn_id="turn-origin",
            project_cleanup=PROJECT_CLEANUP,
        )

        self.assertTrue(dream_auto_repair_metadata_is_valid(message.metadata))
        without_cleanup = dict(message.metadata)
        without_cleanup.pop("projectCleanup")
        self.assertTrue(dream_auto_repair_metadata_is_valid(without_cleanup))

    def test_stage_schema_repair_may_carry_observed_cleanup_fact(self) -> None:
        message = build_dream_auto_repair_message(
            issue=invalid_stage_issue(),
            workflow_run_id=RUN_ID,
            thread_id="thread-auto-repair",
            originating_message_id="message-stage-invalid",
            originating_turn_id="turn-origin",
            project_cleanup=PROJECT_CLEANUP,
        )

        self.assertTrue(dream_auto_repair_metadata_is_valid(message.metadata))
        self.assertEqual(
            message.metadata["projectCleanup"],
            {
                "trustedProjectSlug": "server-project",
                "staleProjectSlugs": ["workspace-project"],
            },
        )

    def test_exhausted_error_exposes_only_allowlisted_final_reason(self) -> None:
        error = DreamAutoRepairExhaustedError(
            "DREAM_STAGE_ENTITY_ID_DUPLICATE"
        )
        unsafe = DreamAutoRepairExhaustedError("postgresql://secret")

        self.assertEqual(error.code, "DREAM_WORKBENCH_AUTO_REPAIR_FAILED")
        self.assertIn("DREAM_STAGE_ENTITY_ID_DUPLICATE", error.public_message)
        self.assertIn("不会发起第三轮", error.public_message)
        self.assertNotIn("postgresql://", unsafe.public_message)
        self.assertNotIn("secret", unsafe.public_message)

    def test_unallowlisted_or_unsafe_issue_never_reaches_visible_message(self) -> None:
        with self.assertRaises(DreamAutoRepairError) as raised:
            build_dream_auto_repair_message(
                issue=mismatch_issue(actual="postgresql://user:secret@internal/db"),
                workflow_run_id=RUN_ID,
                thread_id="thread-auto-repair",
                originating_message_id="message-origin",
                originating_turn_id="turn-origin",
            )

        self.assertIn(
            raised.exception.code,
            {
                "DREAM_AUTO_REPAIR_NOT_ALLOWLISTED",
                "DREAM_AUTO_REPAIR_IDENTITY_INVALID",
            },
        )
        self.assertNotIn("secret", raised.exception.public_message)

    def test_ambiguous_project_without_server_cleanup_fact_fails_closed(self) -> None:
        with self.assertRaises(DreamAutoRepairError) as raised:
            build_dream_auto_repair_message(
                issue=ambiguous_project_issue(),
                workflow_run_id=RUN_ID,
                thread_id="thread-auto-repair",
                originating_message_id="message-origin",
                originating_turn_id="turn-origin",
            )

        self.assertEqual(
            raised.exception.code,
            "DREAM_AUTO_REPAIR_IDENTITY_INVALID",
        )

    def test_persistence_uses_exact_sse_message_identity(self) -> None:
        message = build_dream_auto_repair_message(
            issue=mismatch_issue(),
            workflow_run_id=RUN_ID,
            thread_id="thread-auto-repair",
            originating_message_id="message-origin",
            originating_turn_id="turn-origin",
            project_cleanup=PROJECT_CLEANUP,
        )
        with patch(
            "services.story_workspace.dream_auto_repair_service.database.save_chat_message"
        ) as save:
            persist_dream_auto_repair_message(message)

        save.assert_called_once_with(
            message.thread_id,
            "user",
            message.persistence_parts(),
            message.id,
            dict(message.metadata),
        )
        self.assertEqual(message.sse_message()["id"], message.id)
        self.assertEqual(message.sse_message()["parts"], message.persistence_parts())
        self.assertEqual(message.sse_message()["metadata"], message.metadata)

    def test_continuation_commits_message_and_resume_before_sse(self) -> None:
        async def scenario():
            artifact_hook = unittest.mock.Mock()
            artifact_hook.resolve_auto_repair_project_cleanup_scope.return_value = (
                PROJECT_CLEANUP
            )
            service = ClaudeAgentService(
                dream_artifact_turn_hook=artifact_hook
            )
            order: list[str] = []
            queue = RecordingQueue(order)
            state = AgentRunState(session_id="thread-auto-repair")
            state.current_turn_id = "turn-origin"
            request = ClaudeAgentRunRequest(
                user_id="7",
                thread_id="thread-auto-repair",
                message_id="message-origin",
                message_parts=[{"type": "text", "text": "original"}],
            )
            execution = SimpleNamespace(
                request=request,
                state=state,
                dream_context=dream_context(),
                turn_context=SimpleNamespace(queue=queue),
                dream_artifact_turn_ticket=unittest.mock.sentinel.ticket,
            )
            error = DreamArtifactTurnHookError(
                "slug mismatch",
                issue=mismatch_issue(),
            )

            def persist(_message):
                order.append("persist")

            def settle(_message_id, *, thread_id, expected_metadata, status):
                del thread_id, expected_metadata
                order.append(f"settle:{status}")
                return True

            async def persist_resume(_execution, _result):
                order.append("resume")

            with (
                patch(
                    "claude_agent.service.persist_dream_auto_repair_message",
                    side_effect=persist,
                ),
                patch(
                    "claude_agent.service.settle_dream_auto_repair_message",
                    side_effect=settle,
                ),
                patch.object(
                    service,
                    "_persist_auto_repair_resume_session",
                    new=AsyncMock(side_effect=persist_resume),
                ),
            ):
                continuation = await service._build_dream_auto_repair_continuation(
                    execution,
                    result=SimpleNamespace(session_id="claude-session"),
                    error=error,
                )
            return continuation, order, queue.events, artifact_hook

        continuation, order, events, artifact_hook = asyncio.run(scenario())

        self.assertEqual(
            order,
            ["persist", f"settle:{DREAM_AUTO_REPAIR_DISPATCHED}", "resume", "sse"],
        )
        self.assertTrue(continuation.request.resume)
        self.assertEqual(
            continuation.request.message_metadata["kind"],
            DREAM_AUTO_REPAIR_METADATA_KIND,
        )
        self.assertEqual(
            continuation.request.message_metadata["dispatch_status"],
            DREAM_AUTO_REPAIR_DISPATCHED,
        )
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.type, "chat-message")
        self.assertEqual(event.data["message"]["id"], continuation.request.message_id)
        self.assertEqual(
            event.data["message"]["metadata"],
            continuation.request.message_metadata,
        )
        artifact_hook.resolve_auto_repair_project_cleanup_scope.assert_called_once_with(
            unittest.mock.sentinel.ticket,
            validation_code="PROJECT_STORY_SLUG_MISMATCH",
        )
        self.assertIn(
            "服务器可信项目根（必须保留）：stories/server-project",
            continuation.request.message_parts[0]["text"],
        )

    def test_second_hook_failure_stops_without_a_third_turn(self) -> None:
        async def scenario():
            error = DreamArtifactTurnHookError(
                "slug mismatch",
                issue=mismatch_issue(),
            )
            artifact_hook = unittest.mock.Mock()
            artifact_hook.after_main_turn.side_effect = error
            service = ClaudeAgentService(dream_artifact_turn_hook=artifact_hook)
            message = build_dream_auto_repair_message(
                issue=mismatch_issue(),
                workflow_run_id=RUN_ID,
                thread_id="thread-auto-repair",
                originating_message_id="message-origin",
                originating_turn_id="turn-origin",
                project_cleanup=PROJECT_CLEANUP,
            )
            message.metadata["dispatch_status"] = DREAM_AUTO_REPAIR_DISPATCHED
            request = ClaudeAgentRunRequest(
                user_id="7",
                thread_id="thread-auto-repair",
                resume=True,
                message_id=message.id,
                message_parts=message.persistence_parts(),
                message_metadata=dict(message.metadata),
            )
            state = AgentRunState(session_id="thread-auto-repair")
            queue: asyncio.Queue = asyncio.Queue()
            turn_context = _TurnContext(
                queue=queue,
                confirmation_store=ToolConfirmationStore(),
            )

            class SuccessfulRepairRunner:
                async def run_streaming(self, opts, callbacks):
                    del opts, callbacks
                    return AgentRunResult(
                        full_text="attempted repair",
                        session_id="claude-session",
                        success=True,
                    )

            execution = _TurnExecution(
                request=request,
                state=state,
                runner=SuccessfulRepairRunner(),
                run_options=unittest.mock.Mock(),
                turn_context=turn_context,
                dream_context=dream_context(),
                dream_artifact_turn_ticket=unittest.mock.sentinel.ticket,
            )
            with (
                patch.object(
                    service,
                    "_persist_user_message",
                    new=AsyncMock(),
                ),
                patch.object(
                    service,
                    "_persist_assistant_turn",
                    new=AsyncMock(),
                ) as persist_assistant,
                patch.object(
                    service,
                    "mark_auto_repair_failed",
                    new=AsyncMock(),
                ) as mark_failed,
            ):
                with self.assertRaises(DreamAutoRepairExhaustedError):
                    await service.execute_session(execution)
            return artifact_hook, persist_assistant, mark_failed, list(queue._queue)

        artifact_hook, persist_assistant, mark_failed, events = asyncio.run(scenario())

        persist_assistant.assert_awaited_once()
        artifact_hook.after_main_turn.assert_called_once_with(
            unittest.mock.sentinel.ticket
        )
        mark_failed.assert_awaited_once()
        self.assertFalse(any(getattr(event, "type", None) == "chat-message" for event in events))

    def test_first_repairable_hook_runs_after_assistant_persistence(self) -> None:
        async def scenario():
            order: list[str] = []
            error = DreamArtifactTurnHookError(
                "slug mismatch",
                issue=mismatch_issue(),
            )
            artifact_hook = unittest.mock.Mock()

            def fail_hook(_ticket):
                order.append("hook")
                raise error

            artifact_hook.after_main_turn.side_effect = fail_hook
            service = ClaudeAgentService(dream_artifact_turn_hook=artifact_hook)
            request = ClaudeAgentRunRequest(
                user_id="7",
                thread_id="thread-auto-repair",
                message_id="message-origin",
                message_parts=[{"type": "text", "text": "original"}],
            )
            execution = _TurnExecution(
                request=request,
                state=AgentRunState(session_id="thread-auto-repair"),
                runner=unittest.mock.Mock(
                    run_streaming=AsyncMock(
                        return_value=AgentRunResult(
                            full_text="first attempt",
                            session_id="claude-session",
                            success=True,
                        )
                    )
                ),
                run_options=unittest.mock.Mock(),
                turn_context=_TurnContext(
                    queue=asyncio.Queue(),
                    confirmation_store=ToolConfirmationStore(),
                ),
                dream_context=dream_context(),
                dream_artifact_turn_ticket=unittest.mock.sentinel.ticket,
            )
            expected = unittest.mock.sentinel.continuation
            with (
                patch.object(service, "_persist_user_message", new=AsyncMock()),
                patch.object(
                    service,
                    "_persist_assistant_turn",
                    new=AsyncMock(
                        side_effect=lambda *_args: order.append("assistant")
                    ),
                ),
                patch.object(
                    service,
                    "_build_dream_auto_repair_continuation",
                    new=AsyncMock(
                        side_effect=lambda *_args, **_kwargs: (
                            order.append("continuation") or expected
                        )
                    ),
                ),
            ):
                actual = await service.execute_session(execution)
            return actual, expected, order

        actual, expected, order = asyncio.run(scenario())

        self.assertIs(actual, expected)
        self.assertEqual(order, ["assistant", "hook", "continuation"])

    def test_successful_repair_hook_persists_assistant_and_finishes_normally(self) -> None:
        async def scenario():
            artifact_hook = unittest.mock.Mock()
            artifact_hook.after_main_turn.return_value = SimpleNamespace(
                changed_stages=(),
                private_artifact_changed=True,
                private_files=("stories/server-project/project.yaml",),
                story_index_status="updated",
            )
            service = ClaudeAgentService(dream_artifact_turn_hook=artifact_hook)
            message = build_dream_auto_repair_message(
                issue=mismatch_issue(),
                workflow_run_id=RUN_ID,
                thread_id="thread-auto-repair",
                originating_message_id="message-origin",
                originating_turn_id="turn-origin",
                project_cleanup=PROJECT_CLEANUP,
            )
            message.metadata["dispatch_status"] = DREAM_AUTO_REPAIR_DISPATCHED
            request = ClaudeAgentRunRequest(
                user_id="7",
                thread_id="thread-auto-repair",
                resume=True,
                message_id=message.id,
                message_parts=message.persistence_parts(),
                message_metadata=dict(message.metadata),
            )
            state = AgentRunState(session_id="thread-auto-repair")
            queue: asyncio.Queue = asyncio.Queue()
            turn_context = _TurnContext(
                queue=queue,
                confirmation_store=ToolConfirmationStore(),
            )

            class SuccessfulRepairRunner:
                async def run_streaming(self, opts, callbacks):
                    del opts, callbacks
                    return AgentRunResult(
                        full_text="workspace 已修正",
                        session_id="claude-session",
                        success=True,
                    )

            execution = _TurnExecution(
                request=request,
                state=state,
                runner=SuccessfulRepairRunner(),
                run_options=unittest.mock.Mock(),
                turn_context=turn_context,
                dream_context=dream_context(),
                dream_artifact_turn_ticket=unittest.mock.sentinel.ticket,
            )
            with (
                patch.object(
                    service,
                    "_persist_user_message",
                    new=AsyncMock(),
                ),
                patch.object(
                    service,
                    "_persist_assistant_turn",
                    new=AsyncMock(),
                ) as persist_assistant,
                patch.object(
                    service,
                    "_store_story_workspace_output",
                    new=AsyncMock(return_value=None),
                ),
            ):
                continuation = await service.execute_session(execution)
            return continuation, persist_assistant, list(queue._queue), artifact_hook

        continuation, persist_assistant, events, artifact_hook = asyncio.run(scenario())

        self.assertIsNone(continuation)
        persist_assistant.assert_awaited_once()
        artifact_hook.after_main_turn.assert_called_once_with(
            unittest.mock.sentinel.ticket
        )
        self.assertEqual(getattr(events[-2], "type", None), "finish")
        self.assertIsNone(events[-1])

    def test_existing_dispatch_claim_does_not_publish_or_start_duplicate(self) -> None:
        async def scenario():
            artifact_hook = unittest.mock.Mock()
            artifact_hook.resolve_auto_repair_project_cleanup_scope.return_value = (
                PROJECT_CLEANUP
            )
            service = ClaudeAgentService(
                dream_artifact_turn_hook=artifact_hook
            )
            order: list[str] = []
            queue = RecordingQueue(order)
            state = AgentRunState(session_id="thread-auto-repair")
            state.current_turn_id = "turn-origin"
            execution = SimpleNamespace(
                request=ClaudeAgentRunRequest(
                    user_id="7",
                    thread_id="thread-auto-repair",
                    message_id="message-origin",
                    message_parts=[{"type": "text", "text": "original"}],
                ),
                state=state,
                dream_context=dream_context(),
                turn_context=SimpleNamespace(queue=queue),
                dream_artifact_turn_ticket=unittest.mock.sentinel.ticket,
            )
            error = DreamArtifactTurnHookError(
                "slug mismatch",
                issue=mismatch_issue(),
            )

            with (
                patch(
                    "claude_agent.service.persist_dream_auto_repair_message",
                    side_effect=lambda _message: order.append("persist"),
                ),
                patch(
                    "claude_agent.service.settle_dream_auto_repair_message",
                    return_value=False,
                ) as settle,
                patch.object(
                    service,
                    "_persist_auto_repair_resume_session",
                    new=AsyncMock(side_effect=lambda *_args: order.append("resume")),
                ),
            ):
                with self.assertRaises(DreamAutoRepairError) as raised:
                    await service._build_dream_auto_repair_continuation(
                        execution,
                        result=SimpleNamespace(session_id="claude-session"),
                        error=error,
                    )
            return raised.exception, order, queue.events, settle

        error, order, events, settle = asyncio.run(scenario())

        self.assertEqual(error.code, "DREAM_AUTO_REPAIR_ALREADY_DISPATCHED")
        self.assertEqual(order, ["persist"])
        self.assertEqual(events, [])
        self.assertEqual(settle.call_count, 1)


if __name__ == "__main__":
    unittest.main()
