"""Red/green contract tests for the run-bound Dream Agent adapter."""

from __future__ import annotations

import asyncio
import json
import re
import sqlite3
import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from story_workspace.contracts import (  # noqa: E402
    STORY_WORKSPACE_DREAM_AGENT_QUESTION_ID_MAX,
    STORY_WORKSPACE_DREAM_AGENT_QUESTION_TEXT_MAX,
    STORY_WORKSPACE_DREAM_AGENT_QUESTION_OPTION_MAX,
    STORY_WORKSPACE_DREAM_AGENT_QUESTION_PLACEHOLDER_MAX,
    StoryWorkspaceDreamAgentMessageCommand,
    StoryWorkspaceDreamAgentToolConfirmation,
    StoryWorkspaceDreamAgentToolConfirmationCommand,
    StoryWorkspaceDreamRunContext,
)
from services.story_workspace.dream_agent_message_service import (  # noqa: E402
    _DREAM_PUBLIC_TOOL_CONFIRMATIONS_MAX,
    _dream_public_confirmation_registry,
    _remember_dream_public_confirmation,
    STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
    StoryWorkspaceDreamAgentMessageError,
    StoryWorkspaceDreamAgentMessageCoordinator,
    StoryWorkspaceDreamAgentMessageService,
)
from services.deck.story_workflow_gateway import StoryWorkflowApplicationGateway  # noqa: E402
from services.errors.error_registry import ApiRouteError  # noqa: E402
from routers import story_workspace  # noqa: E402
from story_workspace.contracts import StoryWorkspaceDreamAgentMessageAccepted, StoryWorkspaceDreamAgentMessageSnapshot  # noqa: E402
from claude_agent.service import ClaudeAgentRunRequest, _attach_story_workspace_dream_assistant_source  # noqa: E402
from claude_agent.thread_factory import ClaudeAgentThreadFactory  # noqa: E402


RUN_ID = "run_0123456789abcdef0123456789abcdef"
THREAD_ID = "dream-thread"
ACTOR_ID = "7"


class _Factory:
    def __init__(self, *, running: bool = False, frames: list[str] | None = None) -> None:
        self.running = running
        self.frames = frames or []
        self.requests: list[object] = []
        self.current_turn_id = "turn-1"
        self.pending_tool_call_ids: set[str] | None = None

    def session_snapshot(self, _thread_id: str):
        return (
            {"lifecycle": "running", "current_turn_id": self.current_turn_id}
            if self.running
            else None
        )

    async def subscribe_stream(self, _thread_id: str):
        for frame in self.frames:
            yield frame

    def is_expected_story_workspace_dream_turn(self, *_args) -> bool:
        return True

    def story_workspace_dream_turn_snapshot(
        self,
        thread_id: str,
        run_id: str,
        actor_id: str,
    ):
        if not self.running or not self.is_expected_story_workspace_dream_turn(
            thread_id,
            self.current_turn_id,
            run_id,
            actor_id,
        ):
            return None
        pending = self.pending_tool_call_ids
        if pending is None:
            pending = {
                match.group(1)
                for frame in self.frames
                for match in re.finditer(r'"toolCallId"\s*:\s*"([A-Za-z0-9._:/-]+)"', frame)
                if '"type":"tool-approval-request"' in frame.replace(" ", "")
            }
        return {
            "turn_id": self.current_turn_id,
            "pending_tool_call_ids": sorted(pending),
        }

    async def run_streaming(self, request):
        self.requests.append(request)
        yield 'data: {"type":"message-final"}\n\n'
        yield 'data: {"type":"finish","finishReason":"stop"}\n\n'


class _ToolConfirmationFactory(_Factory):
    def __init__(self, *, trusted: bool = True, resolved: bool = True) -> None:
        super().__init__(running=True)
        self.trusted = trusted
        self.resolved = resolved
        self.confirmations: list[tuple[object, ...]] = []

    def is_expected_story_workspace_dream_turn(
        self,
        thread_id: str,
        turn_id: str,
        run_id: str,
        actor_id: str,
    ) -> bool:
        self.confirmations.append(("trusted", thread_id, turn_id, run_id, actor_id))
        return self.trusted

    def confirm_tool(self, **kwargs):
        if self.resolved:
            if self.pending_tool_call_ids is None:
                self.pending_tool_call_ids = {
                    match.group(1)
                    for frame in self.frames
                    for match in re.finditer(
                        r'"toolCallId"\s*:\s*"([A-Za-z0-9._:/-]+)"',
                        frame,
                    )
                    if '"type":"tool-approval-request"' in frame.replace(" ", "")
                }
            self.pending_tool_call_ids.discard(str(kwargs.get("tool_call_id") or ""))
        self.confirmations.append(("confirm", kwargs))
        return self.resolved


def _context() -> StoryWorkspaceDreamRunContext:
    return StoryWorkspaceDreamRunContext(
        workflow_run_id=RUN_ID,
        thread_id=THREAD_ID,
        deck_id="deck-1",
        deck_plugin_id="drama-forge",
        deck_plugin_version="1.0.0",
        deck_plugin_binding_id="binding-1",
        binding_revision=1,
        deck_runtime_snapshot_id="snapshot-1",
        runtime_plugin_lock_id="lock-1",
    )


class StoryWorkspaceDreamAgentMessageServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            CREATE TABLE chat_thread (id TEXT PRIMARY KEY, user_id INTEGER, updated_at TEXT);
            CREATE TABLE chat_message (
                id TEXT PRIMARY KEY, thread_id TEXT, role TEXT, parts TEXT,
                metadata TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO chat_thread (id, user_id) VALUES ('dream-thread', 7);
            """
        )

    def tearDown(self) -> None:
        self.db.close()

    def _insert(self, message_id: str, role: str, parts: object, metadata: object) -> None:
        self.db.execute(
            "INSERT INTO chat_message (id, thread_id, role, parts, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (message_id, THREAD_ID, role, json.dumps(parts), json.dumps(metadata), datetime.now(UTC).isoformat()),
        )
        self.db.commit()

    def test_snapshot_only_projects_public_widget_user_and_assistant_text(self) -> None:
        self._insert("widget", "user", [{"type": "text", "text": "继续"}], {
            "kind": STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
            "story_workspace_run_id": RUN_ID,
            "actor_id": ACTOR_ID,
            "thread_id": THREAD_ID,
        })
        self._insert("assistant", "assistant", [
            {"type": "text", "text": "可公开的结果"},
            {"type": "reasoning", "text": "hidden thought"},
            {"type": "tool-invocation", "toolInvocation": {"input": {"token": "secret"}}},
        ], {"story_workspace_dream_source": {
            "run_id": RUN_ID,
            "thread_id": THREAD_ID,
            "actor_id": ACTOR_ID,
            "message_id": "widget",
            "kind": STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
        }})
        self._insert("control-assistant", "assistant", [{"type": "text", "text": "must not leak"}], {
            "kind": "story-workspace-dream-confirmation",
        })
        self._insert("other", "user", [{"type": "text", "text": "must not leak"}], {
            "kind": STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
            "story_workspace_run_id": RUN_ID,
            "actor_id": "8",
        })
        with patch(
            "services.story_workspace.dream_agent_message_service.story_workspace_read_dream_confirmation_fact",
            return_value=(True, True),
        ):
            result = StoryWorkspaceDreamAgentMessageService(self.db).snapshot(
                run_id=RUN_ID, thread_id=THREAD_ID, actor_id=ACTOR_ID
            )
        self.assertEqual([(message.id, message.text) for message in result.messages], [
            ("widget", "继续"), ("assistant", "可公开的结果"),
        ])
        self.assertTrue(result.can_send)

    def test_snapshot_projects_safe_ordered_content_without_raw_tool_data(self) -> None:
        self._insert("widget-content", "user", [{"type": "text", "text": "继续"}], {
            "kind": STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
            "story_workspace_run_id": RUN_ID,
            "actor_id": ACTOR_ID,
            "thread_id": THREAD_ID,
        })
        self._insert("assistant-content", "assistant", [
            {"type": "text", "text": "先读取资料。"},
            {"type": "reasoning", "text": "hidden chain of thought"},
            {
                "type": "tool-invocation",
                "toolCallId": "call-read-secret",
                "toolName": "Read",
                "state": "output-available",
                "input": {"path": "/private/story.md", "token": "secret"},
                "output": {"content": "private output"},
            },
            {"type": "text", "text": "再更新内容。"},
            {
                "type": "tool-invocation",
                "toolCallId": "call-writer-secret",
                "toolName": "mcp__story_workspace__write_dream_stage",
                "state": "output-error",
                "input": {"stage": "characters", "credential": "secret"},
                "output": {"error": "stack trace"},
            },
            {
                "type": "tool-invocation",
                "toolCallId": "call-unknown-secret",
                "toolName": "sk-secret-looking-tool-name",
                "state": "call",
                "input": {"command": "rm -rf /"},
            },
        ], {"story_workspace_dream_source": {
            "run_id": RUN_ID,
            "thread_id": THREAD_ID,
            "actor_id": ACTOR_ID,
            "message_id": "widget-content",
            "kind": STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
        }})

        with patch(
            "services.story_workspace.dream_agent_message_service.story_workspace_read_dream_confirmation_fact",
            return_value=(True, True),
        ):
            result = StoryWorkspaceDreamAgentMessageService(self.db).snapshot(
                run_id=RUN_ID, thread_id=THREAD_ID, actor_id=ACTOR_ID
            )

        message = next(item for item in result.messages if item.id == "assistant-content")
        self.assertEqual(message.text, "先读取资料。再更新内容。")
        self.assertEqual(
            [item.model_dump(mode="json", by_alias=True) for item in message.content],
            [
                {"kind": "text", "text": "先读取资料。", "truncated": False},
                {
                    "kind": "activity",
                    "id": message.content[1].id,
                    "category": "workspace_read",
                    "label": "读取工作区资料",
                    "status": "completed",
                },
                {"kind": "text", "text": "再更新内容。", "truncated": False},
                {
                    "kind": "activity",
                    "id": message.content[3].id,
                    "category": "dream_write",
                    "label": "更新 Dream 内容",
                    "status": "stopped",
                },
                {
                    "kind": "activity",
                    "id": message.content[4].id,
                    "category": "other",
                    "label": "处理 Dream 创作任务",
                    "status": "running",
                },
            ],
        )
        serialized = message.model_dump_json(by_alias=True)
        for forbidden in (
            "reasoning", "hidden chain", "toolCallId", "call-read-secret",
            "toolName", "/private/story.md", "credential", "stack trace",
            "sk-secret-looking-tool-name", "rm -rf",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_snapshot_redacts_sensitive_text_across_persisted_part_boundaries(self) -> None:
        self._insert("widget-sensitive", "user", [{"type": "text", "text": "继续"}], {
            "kind": STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
            "story_workspace_run_id": RUN_ID,
            "actor_id": ACTOR_ID,
            "thread_id": THREAD_ID,
        })
        probes = (
            ("secret-key", ["密钥：sk-ant-", "api03-" + "A" * 48]),
            ("pem", ["-----BEGIN PRIVATE ", "KEY-----\nprivate material"]),
            ("hidden", ["hidden chain ", "of thought: internal"]),
            ("system", ["system pro", "mpt: internal instructions"]),
            ("path", ["读取 /Users/dmeck/", "project/private.txt"]),
            ("generic-api-key", ["api_key=", "abcdef0123456789abcdef"]),
        )
        for index, (name, chunks) in enumerate(probes):
            self._insert(f"assistant-sensitive-{index}", "assistant", [
                {"type": "text", "text": chunk} for chunk in chunks
            ], {"story_workspace_dream_source": {
                "run_id": RUN_ID,
                "thread_id": THREAD_ID,
                "actor_id": ACTOR_ID,
                "message_id": "widget-sensitive",
                "kind": STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
            }})

        self._insert("assistant-safe-chinese", "assistant", [
            {"type": "text", "text": "角色关系已经整理完成，可以继续创作。"},
        ], {"story_workspace_dream_source": {
            "run_id": RUN_ID,
            "thread_id": THREAD_ID,
            "actor_id": ACTOR_ID,
            "message_id": "widget-sensitive",
            "kind": STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
        }})

        with patch(
            "services.story_workspace.dream_agent_message_service.story_workspace_read_dream_confirmation_fact",
            return_value=(True, True),
        ):
            result = StoryWorkspaceDreamAgentMessageService(self.db).snapshot(
                run_id=RUN_ID, thread_id=THREAD_ID, actor_id=ACTOR_ID
            )

        by_id = {message.id: message for message in result.messages}
        for index, (_name, chunks) in enumerate(probes):
            message = by_id[f"assistant-sensitive-{index}"]
            self.assertEqual(message.text, "[已隐藏敏感内容]")
            self.assertEqual(
                [item.model_dump(mode="json", by_alias=True) for item in message.content],
                [{"kind": "text", "text": "[已隐藏敏感内容]", "truncated": False}],
            )
            serialized = message.model_dump_json(by_alias=True)
            for chunk in chunks:
                self.assertNotIn(chunk, serialized)
        self.assertEqual(
            by_id["assistant-safe-chinese"].text,
            "角色关系已经整理完成，可以继续创作。",
        )

    def test_events_buffer_and_redact_sensitive_text_split_across_frames(self) -> None:
        sensitive_factory = _Factory(running=True, frames=[
            'data: {"type":"text-start","id":"text-1"}\n\n',
            'data: {"type":"text-delta","id":"text-1","delta":"创作建议包含 sk-"}\n\n',
            'data: {"type":"text-delta","id":"text-1","delta":"ant-api03-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"}\n\n',
            'data: {"type":"message-final"}\n\n',
        ])
        sensitive_output = "".join(asyncio.run(_collect(
            StoryWorkspaceDreamAgentMessageService(
                self.db, thread_factory=sensitive_factory
            ).events(
                thread_id=THREAD_ID,
                run_id=RUN_ID,
                actor_id=ACTOR_ID,
            )
        )))
        self.assertIn("event: assistant_text_delta", sensitive_output)
        self.assertIn("[已隐藏敏感内容]", sensitive_output)
        self.assertNotIn("sk-ant", sensitive_output)
        self.assertNotIn("api03", sensitive_output)
        self.assertIn("id: turn-1:2", sensitive_output)
        self.assertIn("id: turn-1:3", sensitive_output)

        safe_first = "角色关系已经整理。" + "雨夜氛围持续推进，" * 20
        safe_second = "场景与人物动机保持一致，可以继续创作。"
        safe_factory = _Factory(running=True, frames=[
            "data: " + json.dumps(
                {"type": "text-delta", "delta": safe_first},
                ensure_ascii=False,
            ) + "\n\n",
            "data: " + json.dumps(
                {"type": "text-delta", "delta": safe_second},
                ensure_ascii=False,
            ) + "\n\n",
            'data: {"type":"message-final"}\n\n',
        ])
        safe_output = "".join(asyncio.run(_collect(
            StoryWorkspaceDreamAgentMessageService(
                self.db, thread_factory=safe_factory
            ).events(
                thread_id=THREAD_ID,
                run_id=RUN_ID,
                actor_id=ACTOR_ID,
            )
        )))
        self.assertIn("id: turn-1:0", safe_output)
        self.assertIn("角色关系已经整理。", safe_output)
        self.assertLess(
            safe_output.index("event: assistant_text_delta"),
            safe_output.index("event: assistant_message_committed"),
        )

    def test_snapshot_redacts_internal_dream_diagnostic_variants(self) -> None:
        self._insert("widget-internal-diagnostic", "user", [{"type": "text", "text": "继续"}], {
            "kind": STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
            "story_workspace_run_id": RUN_ID,
            "actor_id": ACTOR_ID,
            "thread_id": THREAD_ID,
        })
        diagnostics = (
            "agentId",
            "agent_id",
            "bindingRevision",
            "binding_revision",
            "expectedBindingRevision",
            "expected_binding_revision",
            "expectedRevision",
            "expected_revision",
            "workflowRunId",
            "workflow_run_id",
            "threadId",
            "thread_id",
            "toolCallId",
            "tool_call_id",
            "bind_first_episode",
            "write_dream_run",
            "write_dream_stage",
            "record_episode_workflow_completion",
            "DREAM_WRITE_REJECTED",
            "mcp__story_workspace__",
        )
        for index, diagnostic in enumerate(diagnostics):
            self._insert(f"assistant-internal-diagnostic-{index}", "assistant", [
                {"type": "text", "text": f"内部结果：{diagnostic}=private"},
            ], {"story_workspace_dream_source": {
                "run_id": RUN_ID,
                "thread_id": THREAD_ID,
                "actor_id": ACTOR_ID,
                "message_id": "widget-internal-diagnostic",
                "kind": STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
            }})

        with patch(
            "services.story_workspace.dream_agent_message_service.story_workspace_read_dream_confirmation_fact",
            return_value=(True, True),
        ):
            result = StoryWorkspaceDreamAgentMessageService(self.db).snapshot(
                run_id=RUN_ID,
                thread_id=THREAD_ID,
                actor_id=ACTOR_ID,
            )

        by_id = {message.id: message for message in result.messages}
        for index, diagnostic in enumerate(diagnostics):
            with self.subTest(diagnostic=diagnostic):
                message = by_id[f"assistant-internal-diagnostic-{index}"]
                self.assertEqual(message.text, "[已隐藏敏感内容]")
                self.assertEqual(
                    [
                        item.model_dump(mode="json", by_alias=True)
                        for item in message.content
                    ],
                    [{
                        "kind": "text",
                        "text": "[已隐藏敏感内容]",
                        "truncated": False,
                    }],
                )
                self.assertNotIn(
                    diagnostic,
                    message.model_dump_json(by_alias=True),
                )

    def test_events_redact_internal_dream_diagnostics_split_across_frames(self) -> None:
        probes = (
            ("agent", "Id"),
            ("agent_", "id"),
            ("binding", "Revision"),
            ("binding_", "revision"),
            ("expectedBinding", "Revision"),
            ("expected_binding_", "revision"),
            ("expected", "Revision"),
            ("expected_", "revision"),
            ("workflowRun", "Id"),
            ("workflow_run_", "id"),
            ("thread", "Id"),
            ("thread_", "id"),
            ("toolCall", "Id"),
            ("tool_call_", "id"),
            ("bind_first_", "episode"),
            ("write_dream_", "run"),
            ("write_dream_", "stage"),
            ("record_episode_workflow_", "completion"),
            ("DREAM_WRITE_", "REJECTED"),
            ("mcp__story_", "workspace__"),
        )
        for index, (first, second) in enumerate(probes):
            with self.subTest(index=index):
                factory = _Factory(running=True, frames=[
                    "data: " + json.dumps(
                        {"type": "text-delta", "delta": "处理结果：" + first},
                        ensure_ascii=False,
                    ) + "\n\n",
                    "data: " + json.dumps(
                        {"type": "text-delta", "delta": second},
                        ensure_ascii=False,
                    ) + "\n\n",
                    'data: {"type":"message-final"}\n\n',
                ])
                output = "".join(asyncio.run(_collect(
                    StoryWorkspaceDreamAgentMessageService(
                        self.db,
                        thread_factory=factory,
                    ).events(
                        thread_id=THREAD_ID,
                        run_id=RUN_ID,
                        actor_id=ACTOR_ID,
                    )
                )))

                self.assertIn("[已隐藏敏感内容]", output)
                self.assertNotIn(first + second, output)

    def test_public_creative_command_text_is_not_treated_as_ask_user_input(self) -> None:
        self._insert("widget-creative-command", "user", [{"type": "text", "text": "继续"}], {
            "kind": STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
            "story_workspace_run_id": RUN_ID,
            "actor_id": ACTOR_ID,
            "thread_id": THREAD_ID,
        })
        safe_texts = (
            "请执行命令 /drama-plan",
            "下一步命令是 /drama-script (EP01)",
            "将军下达命令，角色离开",
        )
        for index, safe_text in enumerate(safe_texts):
            self._insert(f"assistant-creative-command-{index}", "assistant", [
                {"type": "text", "text": safe_text},
            ], {"story_workspace_dream_source": {
                "run_id": RUN_ID,
                "thread_id": THREAD_ID,
                "actor_id": ACTOR_ID,
                "message_id": "widget-creative-command",
                "kind": STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
            }})

        with patch(
            "services.story_workspace.dream_agent_message_service.story_workspace_read_dream_confirmation_fact",
            return_value=(True, True),
        ):
            snapshot = StoryWorkspaceDreamAgentMessageService(self.db).snapshot(
                run_id=RUN_ID,
                thread_id=THREAD_ID,
                actor_id=ACTOR_ID,
            )

        by_id = {message.id: message.text for message in snapshot.messages}
        for index, safe_text in enumerate(safe_texts):
            self.assertEqual(by_id[f"assistant-creative-command-{index}"], safe_text)

        factory = _Factory(running=True, frames=[
            'data: {"type":"text-delta","delta":"请执行命令 /drama-"}\n\n',
            'data: {"type":"text-delta","delta":"plan；下一步命令是 /drama-script (EP01)；"}\n\n',
            'data: {"type":"text-delta","delta":"将军下达命令，角色离开"}\n\n',
            'data: {"type":"message-final"}\n\n',
        ])
        output = "".join(asyncio.run(_collect(
            StoryWorkspaceDreamAgentMessageService(
                self.db,
                thread_factory=factory,
            ).events(
                thread_id=THREAD_ID,
                run_id=RUN_ID,
                actor_id=ACTOR_ID,
            )
        )))
        for safe_text in safe_texts:
            self.assertIn(safe_text, output)
        self.assertNotIn("[已隐藏敏感内容]", output)

    def test_confirmation_output_combines_resolved_and_finished_with_replayable_subcursors(self) -> None:
        frames = [
            'data: {"type":"tool-input-available","toolCallId":"tool-write","toolName":"mcp__story_workspace__write_dream_stage","input":{"stage":"characters"}}\n\n',
            'data: {"type":"tool-approval-request","toolCallId":"tool-write","toolName":"mcp__story_workspace__write_dream_stage","input":{"stage":"characters"}}\n\n',
            'data: {"type":"tool-output-available","toolCallId":"tool-write","output":{"credential":"secret"},"isError":false}\n\n',
            'data: {"type":"message-final"}\n\n',
        ]

        def collect(after: str | None = None) -> str:
            factory = _ToolConfirmationFactory()
            factory.frames = frames
            return "".join(asyncio.run(_collect(
                StoryWorkspaceDreamAgentMessageService(
                    self.db, thread_factory=factory
                ).events(
                    thread_id=THREAD_ID,
                    run_id=RUN_ID,
                    actor_id=ACTOR_ID,
                    after=after,
                )
            )))

        full = collect()
        self.assertIn("event: tool_confirmation_resolved", full)
        self.assertIn("event: agent_activity_finished", full)
        self.assertIn("id: turn-1:2:0", full)
        self.assertIn("id: turn-1:2:1", full)
        self.assertNotIn("credential", full)

        after_resolved = collect("turn-1:2:0")
        self.assertNotIn("event: tool_confirmation_resolved", after_resolved)
        self.assertEqual(after_resolved.count("event: agent_activity_finished"), 1)
        after_finished = collect("turn-1:2:1")
        self.assertNotIn("event: tool_confirmation_resolved", after_finished)
        self.assertNotIn("event: agent_activity_finished", after_finished)

    def test_events_project_safe_activity_lifecycle_with_stable_opaque_ids(self) -> None:
        factory = _Factory(running=True, frames=[
            'data: {"type":"tool-input-available","toolCallId":"tool-read","toolName":"Read","input":{"path":"/private/a","token":"secret"}}\n\n',
            'data: {"type":"tool-output-available","toolCallId":"tool-read","output":{"content":"private"},"isError":false}\n\n',
            'data: {"type":"tool-input-available","toolCallId":"tool-unknown","toolName":"sk-secret-tool","input":{"command":"rm -rf /"}}\n\n',
            'data: {"type":"tool-output-error","toolCallId":"tool-unknown","output":{"error":"stack trace"}}\n\n',
            'data: {"type":"thinking-delta","delta":"hidden reasoning"}\n\n',
            'data: {"type":"message-final"}\n\n',
        ])
        output = "".join(asyncio.run(_collect(
            StoryWorkspaceDreamAgentMessageService(
                self.db, thread_factory=factory
            ).events(
                thread_id=THREAD_ID,
                run_id=RUN_ID,
                actor_id=ACTOR_ID,
            )
        )))

        self.assertEqual(output.count("event: agent_activity_started"), 2)
        self.assertEqual(output.count("event: agent_activity_finished"), 2)
        self.assertIn('"category":"workspace_read"', output)
        self.assertIn('"label":"读取工作区资料"', output)
        self.assertIn('"status":"completed"', output)
        self.assertIn('"category":"other"', output)
        self.assertIn('"label":"处理 Dream 创作任务"', output)
        self.assertIn('"status":"stopped"', output)
        for forbidden in (
            "tool-read", "tool-unknown", "toolCallId", "toolName", "sk-secret-tool",
            "/private/a", "token", "private", "rm -rf", "stack trace", "reasoning",
        ):
            self.assertNotIn(forbidden, output)

    def test_snapshot_excludes_assistant_without_proven_source_and_truncates_text(self) -> None:
        self._insert("source", "user", [{"type": "text", "text": "继续"}], {
            "kind": STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
            "story_workspace_run_id": RUN_ID,
            "actor_id": ACTOR_ID,
            "thread_id": THREAD_ID,
        })
        self._insert("normal-assistant", "assistant", [{"type": "text", "text": "ordinary chat"}], {})
        self._insert("forged-assistant", "assistant", [{"type": "text", "text": "forged"}], {
            "story_workspace_dream_source": {
                "run_id": RUN_ID, "thread_id": THREAD_ID, "actor_id": "8",
                "message_id": "source", "kind": STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
            },
        })
        self._insert("long-assistant", "assistant", [{"type": "text", "text": "x" * 5000}], {
            "story_workspace_dream_source": {
                "run_id": RUN_ID, "thread_id": THREAD_ID, "actor_id": ACTOR_ID,
                "message_id": "source", "kind": STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
            },
        })
        with patch(
            "services.story_workspace.dream_agent_message_service.story_workspace_read_dream_confirmation_fact",
            return_value=(True, True),
        ):
            result = StoryWorkspaceDreamAgentMessageService(self.db).snapshot(
                run_id=RUN_ID, thread_id=THREAD_ID, actor_id=ACTOR_ID
            )
        self.assertEqual([message.id for message in result.messages], ["source", "long-assistant"])
        self.assertEqual(len(result.messages[-1].text), 4000)
        self.assertTrue(result.messages[-1].truncated)

    def test_snapshot_allows_launch_and_confirmation_assistants_but_rejects_control_sources(self) -> None:
        self._insert("launch-source", "user", [{"type": "text", "text": "hidden launch"}], {
            "kind": "story-workspace-dream-launch",
            "workflowRunId": RUN_ID,
            "threadId": THREAD_ID,
            "actorId": ACTOR_ID,
        })
        self._insert("launch-assistant", "assistant", [{"type": "text", "text": "人物正在生成"}], {
            "story_workspace_dream_source": {
                "run_id": RUN_ID, "thread_id": THREAD_ID, "actor_id": ACTOR_ID,
                "message_id": "launch-source", "kind": "story-workspace-dream-launch",
            },
        })
        self._insert("confirmation-source", "user", [{"type": "text", "text": "hidden confirmation"}], {
            "kind": "story-workspace-dream-confirmation",
            "story_workspace_run_id": RUN_ID,
            "thread_id": THREAD_ID,
            "actor": ACTOR_ID,
        })
        self._insert("confirmation-assistant", "assistant", [{"type": "text", "text": "分镜继续生成"}], {
            "story_workspace_dream_source": {
                "run_id": RUN_ID, "thread_id": THREAD_ID, "actor_id": ACTOR_ID,
                "message_id": "confirmation-source", "kind": "story-workspace-dream-confirmation",
            },
        })
        self._insert("guidance-source", "user", [{"type": "text", "text": "hidden guidance"}], {
            "kind": "story-workspace-guidance",
            "story_workspace_run_id": RUN_ID,
            "thread_id": THREAD_ID,
            "actor_id": ACTOR_ID,
        })
        self._insert("guidance-assistant", "assistant", [{"type": "text", "text": "must not leak"}], {
            "story_workspace_dream_source": {
                "run_id": RUN_ID, "thread_id": THREAD_ID, "actor_id": ACTOR_ID,
                "message_id": "guidance-source", "kind": "story-workspace-guidance",
            },
        })
        self._insert("control-source", "user", [{"type": "text", "text": "hidden control"}], {
            "kind": "system-control",
            "story_workspace_run_id": RUN_ID,
            "thread_id": THREAD_ID,
            "actor_id": ACTOR_ID,
        })
        self._insert("control-assistant", "assistant", [{"type": "text", "text": "must not leak either"}], {
            "story_workspace_dream_source": {
                "run_id": RUN_ID, "thread_id": THREAD_ID, "actor_id": ACTOR_ID,
                "message_id": "control-source", "kind": "system-control",
            },
        })
        with patch(
            "services.story_workspace.dream_agent_message_service.story_workspace_read_dream_confirmation_fact",
            return_value=(True, True),
        ):
            result = StoryWorkspaceDreamAgentMessageService(self.db).snapshot(
                run_id=RUN_ID, thread_id=THREAD_ID, actor_id=ACTOR_ID
            )
        self.assertEqual([(message.id, message.text) for message in result.messages], [
            ("launch-assistant", "人物正在生成"),
            ("confirmation-assistant", "分镜继续生成"),
        ])

    def test_events_filter_raw_sensitive_frames_and_honor_cursor_with_keepalive(self) -> None:
        factory = _Factory(running=True, frames=[
            'data: {"type":"thinking-delta","delta":"hidden"}\n\n',
            "data: not-json\n\n",
            'data: {"type":"text-delta","delta":"公开"}\n\n',
            'data: {"type":"tool-input-available","input":{"credential":"no"}}\n\n',
            'data: {"type":"message-final","message":"no raw"}\n\n',
        ])
        service = StoryWorkspaceDreamAgentMessageService(self.db, thread_factory=factory)
        frames = asyncio.run(_collect(service.events(
            thread_id=THREAD_ID, run_id=RUN_ID, actor_id=ACTOR_ID, after="turn-1:0"
        )))
        output = "".join(frames)
        self.assertIn("event: assistant_text_delta", output)
        self.assertIn("event: assistant_message_committed", output)
        self.assertIn(": keepalive", output)
        self.assertNotIn("hidden", output)
        self.assertNotIn("credential", output)
        self.assertNotIn("no raw", output)
        self.assertNotIn("id: turn-1:0", output)
        self.assertIn("id: turn-1:4:0", output)
        self.assertIn("id: turn-1:4:1", output)
        self.assertEqual(output.count("event: assistant_message_committed"), 1)

    def test_events_project_only_allowlisted_tool_confirmation_fields(self) -> None:
        factory = _ToolConfirmationFactory()
        factory.frames = [
            'data: {"type":"tool-approval-request","toolCallId":"tool-generic","toolName":"Bash","input":{"command":"rm -rf secret","token":"credential"}}\n\n',
            'data: {"type":"tool-approval-request","toolCallId":"tool-ask","toolName":"AskUserQuestion","input":{"questions":[{"id":"q1","question":"继续吗？","description":"hidden","options":[{"label":"继续","value":"yes","description":"hidden option"}]}],"credential":"no"}}\n\n',
            'data: {"type":"tool-approval-request","toolCallId":"tool-network","toolName":"SandboxNetworkAccess","input":{"token":"no"},"confirmationKind":"sandbox_network","networkRequest":{"host":"cdn.example.com","policyMode":"allowlist","matchedAllowedDomain":"secret.internal"}}\n\n',
            'data: {"type":"tool-output-available","toolCallId":"tool-generic","output":{"credential":"must-not-leak"},"isError":false}\n\n',
        ]
        service = StoryWorkspaceDreamAgentMessageService(self.db, thread_factory=factory)
        output = "".join(asyncio.run(_collect(service.events(
            thread_id=THREAD_ID,
            run_id=RUN_ID,
            actor_id=ACTOR_ID,
        ))))

        self.assertEqual(output.count("event: tool_confirmation_requested"), 3)
        self.assertEqual(output.count("event: tool_confirmation_resolved"), 1)
        self.assertIn('"confirmation":{"kind":"approval"', output)
        self.assertIn('"toolName":"Bash"', output)
        self.assertIn('"kind":"ask_user"', output)
        self.assertIn('"id":"q0"', output)
        self.assertIn('"question":"继续吗？"', output)
        self.assertIn('"options":[{"label":"继续","value":"继续"}]', output)
        self.assertIn('"required":true', output)
        self.assertIn('"type":"radio"', output)
        self.assertIn('"kind":"sandbox_network"', output)
        self.assertIn('"host":"cdn.example.com"', output)
        self.assertIn('"policy":"allowlist"', output)
        for secret in (
            "rm -rf secret",
            "credential",
            "hidden option",
            "secret.internal",
            "must-not-leak",
            '"input"',
            '"output"',
        ):
            self.assertNotIn(secret, output)

    def test_ask_user_sensitive_public_fields_fail_closed_before_sse(self) -> None:
        unsafe_inputs = (
            {
                "questions": [{
                    "question": "请提供 command text",
                    "options": [{"label": "继续", "value": "continue"}],
                }],
            },
            {
                "questions": [{
                    "question": "请粘贴原始命令",
                    "options": [{"label": "继续", "value": "continue"}],
                }],
            },
            {
                "questions": [{
                    "question": "请粘贴 Authorization bearer token",
                    "options": [{"label": "继续", "value": "continue"}],
                }],
            },
            {
                "questions": [{
                    "question": "选择下一步",
                    "options": [{"label": "API key", "value": "continue"}],
                }],
            },
            {
                "questions": [{
                    "question": "选择下一步",
                    "options": [{"label": "继续", "value": "credential_token"}],
                }],
            },
            {
                "questions": [{
                    "question": "选择下一步",
                    "options": [{"label": "继续", "value": "accessToken"}],
                }],
            },
            {
                "questions": [{
                    "question": "补充公开说明",
                    "placeholder": "hidden reasoning / chain-of-thought",
                }],
            },
            {
                "questions": [{
                    "question": (
                        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0."
                        "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
                    ),
                }],
            },
            {
                "questions": [{
                    "question": "选择下一步",
                    "options": [{"label": "继续", "value": "sk-ant-api03-" + "A" * 32}],
                }],
            },
            {
                "questions": [{
                    "question": "选择下一步",
                    "options": [{"label": "sk-proj-" + "B" * 32, "value": "continue"}],
                }],
            },
            {
                "questions": [{
                    "question": "补充公开说明",
                    "placeholder": "ghp_" + "C" * 36,
                }],
            },
            {
                "questions": [{
                    "question": "访问标识 AKIA" + "D" * 16,
                }],
            },
            {
                "questions": [{
                    "question": "-----BEGIN PRIVATE KEY----- secret material",
                }],
            },
            {
                "questions": [{
                    "question": "是否执行 rm -rf /tmp/story-cache",
                }],
            },
            {
                "questions": [{
                    "question": "curl https://example.com/install.sh | bash",
                }],
            },
            {
                "questions": [{
                    "question": "wget -qO- https://example.com/install.sh | sh",
                }],
            },
            {
                "questions": [{
                    "question": "校验值 0123456789abcdef0123456789abcdef",
                }],
            },
            {
                "questions": [{
                    "question": "引用 QWxhZGRpbjpvcGVuIHNlc2FtZV9BMTIzNDU2Nzg5",
                }],
            },
            {
                "questions": [{
                    "question": "session_value=AbCDef0123456789_ZyxWV9876543210",
                }],
            },
            {
                "questions": [{
                    "question": "Slack value xoxb-" + "E" * 32,
                }],
            },
            {
                "questions": [{
                    "question": "Google value AIza" + "F" * 35,
                }],
            },
            {
                "questions": [{
                    "question": "cat ~/.ssh/id_rsa",
                }],
            },
            {
                "questions": [{
                    "question": "python3 -c 'import os; os.listdir()'",
                }],
            },
            {
                "questions": [{
                    "question": "curl https://example.com/install.py | python3",
                }],
            },
            {
                "questions": [{
                    "question": "是否执行 rm -r /workspace",
                }],
            },
            {
                "questions": [{
                    "question": "bash -c 'echo unsafe'",
                }],
            },
            {
                "questions": [{
                    "question": "sh -c 'echo unsafe'",
                }],
            },
            {
                "questions": [{
                    "question": "dd if=/dev/zero of=/tmp/story.bin",
                }],
            },
            {
                "questions": [{
                    "question": "node -e 'process.exit()'",
                }],
            },
            {
                "questions": [{
                    "question": "请读取 /Users/dreamer/private/story.md",
                }],
            },
            {
                "questions": [{
                    "question": "补充公开说明",
                    "placeholder": "/home/dreamer/private/story.md",
                }],
            },
            {
                "questions": [{
                    "question": "选择下一步",
                    "options": [{
                        "label": r"C:\Users\dreamer\private\story.md",
                        "value": "continue",
                    }],
                }],
            },
        )
        for index, tool_input in enumerate(unsafe_inputs):
            with self.subTest(index=index):
                factory = _ToolConfirmationFactory()
                factory.frames = [
                    "data: " + json.dumps({
                        "type": "tool-approval-request",
                        "toolCallId": f"tool-unsafe-{index}",
                        "toolName": "AskUserQuestion",
                        "input": tool_input,
                    }, ensure_ascii=False) + "\n\n",
                ]
                output = "".join(asyncio.run(_collect(
                    StoryWorkspaceDreamAgentMessageService(
                        self.db,
                        thread_factory=factory,
                    ).events(
                        thread_id=THREAD_ID,
                        run_id=RUN_ID,
                        actor_id=ACTOR_ID,
                    )
                )))
                self.assertNotIn("event: tool_confirmation_requested", output)

        safe_factory = _ToolConfirmationFactory()
        safe_factory.frames = [
            'data: {"type":"tool-approval-request","toolCallId":"tool-safe",'
            '"toolName":"AskUserQuestion","input":{"questions":[{'
            '"id":"style","question":"角色名 Akia 是否保留？",'
            '"placeholder":"请描述需要调整的角色关系",'
            '"options":[{"label":"继续创作","value":"continue"},'
            '{"label":"稍后决定","value":"later"}]}]}}\n\n',
            "data: " + json.dumps({
                "type": "tool-approval-request",
                "toolCallId": "tool-safe-low-entropy",
                "toolName": "AskUserQuestion",
                "input": {"question": "章节代号 " + "A" * 48 + " 是否保留？"},
            }, ensure_ascii=False) + "\n\n",
            "data: " + json.dumps({
                "type": "tool-approval-request",
                "toolCallId": "tool-safe-animal-names",
                "toolName": "AskUserQuestion",
                "input": {"question": "角色名为 Python 和 Cat，是否保留？"},
            }, ensure_ascii=False) + "\n\n",
            "data: " + json.dumps({
                "type": "tool-approval-request",
                "toolCallId": "tool-safe-run-id",
                "toolName": "AskUserQuestion",
                "input": {
                    "question": (
                        "是否继续 run_0123456789abcdef0123456789abcdef 的创作？"
                    ),
                },
            }, ensure_ascii=False) + "\n\n",
            "data: " + json.dumps({
                "type": "tool-approval-request",
                "toolCallId": "tool-safe-drama-plan",
                "toolName": "AskUserQuestion",
                "input": {"question": "是否继续推进 /drama-plan？"},
            }, ensure_ascii=False) + "\n\n",
            "data: " + json.dumps({
                "type": "tool-approval-request",
                "toolCallId": "tool-safe-drama-script",
                "toolName": "AskUserQuestion",
                "input": {"question": "是否继续 /drama-script (EP01) 的创作？"},
            }, ensure_ascii=False) + "\n\n",
            "data: " + json.dumps({
                "type": "tool-approval-request",
                "toolCallId": "tool-safe-story-text",
                "toolName": "AskUserQuestion",
                "input": {"question": "角色沿山路返回旧城，这段剧情是否保留？"},
            }, ensure_ascii=False) + "\n\n",
        ]
        safe_output = "".join(asyncio.run(_collect(
            StoryWorkspaceDreamAgentMessageService(
                self.db,
                thread_factory=safe_factory,
            ).events(
                thread_id=THREAD_ID,
                run_id=RUN_ID,
                actor_id=ACTOR_ID,
            )
        )))
        self.assertEqual(safe_output.count("event: tool_confirmation_requested"), 7)
        self.assertIn("角色名 Akia 是否保留？", safe_output)
        self.assertIn(
            "是否继续 run_0123456789abcdef0123456789abcdef 的创作？",
            safe_output,
        )
        self.assertIn("是否继续推进 /drama-plan？", safe_output)
        self.assertIn("是否继续 /drama-script (EP01) 的创作？", safe_output)
        self.assertIn("角色沿山路返回旧城，这段剧情是否保留？", safe_output)

    def test_ask_user_public_question_lengths_and_keys_are_one_contract(self) -> None:
        from pydantic import ValidationError

        question_id = "i" * STORY_WORKSPACE_DREAM_AGENT_QUESTION_ID_MAX
        question_text = "问" * STORY_WORKSPACE_DREAM_AGENT_QUESTION_TEXT_MAX
        command = StoryWorkspaceDreamAgentToolConfirmationCommand(
            toolCallId="tool-length",
            approved=True,
            answers={question_id: "普通回答"},
        )
        self.assertIn(question_id, command.answers or {})
        with self.assertRaises(ValidationError):
            StoryWorkspaceDreamAgentToolConfirmationCommand(
                toolCallId="tool-length",
                approved=True,
                answers={question_id + "x": "普通回答"},
            )

        safe_factory = _ToolConfirmationFactory()
        safe_factory.frames = [
            "data: " + json.dumps({
                "type": "tool-approval-request",
                "toolCallId": "tool-max-lengths",
                "toolName": "AskUserQuestion",
                "input": {"questions": [{
                    "id": question_id,
                    "question": question_text,
                    "placeholder": (
                        "提" * STORY_WORKSPACE_DREAM_AGENT_QUESTION_PLACEHOLDER_MAX
                    ),
                    "options": [{
                        "label": "选" * STORY_WORKSPACE_DREAM_AGENT_QUESTION_OPTION_MAX,
                        "value": "v" * STORY_WORKSPACE_DREAM_AGENT_QUESTION_OPTION_MAX,
                    }],
                }]},
            }, ensure_ascii=False) + "\n\n",
        ]
        safe_output = "".join(asyncio.run(_collect(
            StoryWorkspaceDreamAgentMessageService(
                self.db,
                thread_factory=safe_factory,
            ).events(
                thread_id=THREAD_ID,
                run_id=RUN_ID,
                actor_id=ACTOR_ID,
            )
        )))
        self.assertEqual(safe_output.count("event: tool_confirmation_requested"), 1)

        factory = _ToolConfirmationFactory()
        factory.frames = [
            "data: " + json.dumps({
                "type": "tool-approval-request",
                "toolCallId": "tool-too-long",
                "toolName": "AskUserQuestion",
                "input": {"questions": [{"question": question_text + "超"}]},
            }, ensure_ascii=False) + "\n\n",
            "data: " + json.dumps({
                "type": "tool-approval-request",
                "toolCallId": "tool-option-too-long",
                "toolName": "AskUserQuestion",
                "input": {"questions": [{
                    "question": "普通问题",
                    "options": [{
                        "label": "选",
                        "value": "v" * (
                            STORY_WORKSPACE_DREAM_AGENT_QUESTION_OPTION_MAX + 1
                        ),
                    }],
                }]},
            }, ensure_ascii=False) + "\n\n",
            "data: " + json.dumps({
                "type": "tool-approval-request",
                "toolCallId": "tool-placeholder-too-long",
                "toolName": "AskUserQuestion",
                "input": {"questions": [{
                    "question": "普通问题",
                    "placeholder": "提" * (
                        STORY_WORKSPACE_DREAM_AGENT_QUESTION_PLACEHOLDER_MAX + 1
                    ),
                }]},
            }, ensure_ascii=False) + "\n\n",
        ]
        output = "".join(asyncio.run(_collect(
            StoryWorkspaceDreamAgentMessageService(
                self.db,
                thread_factory=factory,
            ).events(
                thread_id=THREAD_ID,
                run_id=RUN_ID,
                actor_id=ACTOR_ID,
            )
        )))
        self.assertNotIn("event: tool_confirmation_requested", output)

        raw_id = "sk-ant-api03-" + "R" * 48
        raw_id_factory = _ToolConfirmationFactory()
        raw_id_factory.frames = [
            "data: " + json.dumps({
                "type": "tool-approval-request",
                "toolCallId": "tool-raw-id",
                "toolName": "AskUserQuestion",
                "input": {"questions": [{
                    "id": raw_id,
                    "question": "普通公开问题",
                }]},
            }, ensure_ascii=False) + "\n\n",
        ]
        raw_id_output = "".join(asyncio.run(_collect(
            StoryWorkspaceDreamAgentMessageService(
                self.db,
                thread_factory=raw_id_factory,
            ).events(
                thread_id=THREAD_ID,
                run_id=RUN_ID,
                actor_id=ACTOR_ID,
            )
        )))
        self.assertIn("event: tool_confirmation_requested", raw_id_output)
        self.assertIn('"id":"q0"', raw_id_output)
        self.assertNotIn(raw_id, raw_id_output)

        duplicate_text_factory = _ToolConfirmationFactory()
        duplicate_text_factory.frames = [
            "data: " + json.dumps({
                "type": "tool-approval-request",
                "toolCallId": "tool-duplicate-text",
                "toolName": "AskUserQuestion",
                "input": {"questions": [
                    {"id": "one", "question": "同一个展示问题"},
                    {"id": "two", "question": "同一个展示问题"},
                ]},
            }, ensure_ascii=False) + "\n\n",
        ]
        duplicate_text_service = StoryWorkspaceDreamAgentMessageService(
            self.db,
            thread_factory=duplicate_text_factory,
        )
        duplicate_text_output = "".join(asyncio.run(_collect(
            duplicate_text_service.events(
                thread_id=THREAD_ID,
                run_id=RUN_ID,
                actor_id=ACTOR_ID,
            )
        )))
        self.assertNotIn("event: tool_confirmation_requested", duplicate_text_output)
        with self.assertRaisesRegex(
            StoryWorkspaceDreamAgentMessageError,
            "DREAM_AGENT_TOOL_CONFIRMATION_NOT_READY",
        ):
            duplicate_text_service.confirm_tool(
                run_id=RUN_ID,
                thread_id=THREAD_ID,
                actor_id=ACTOR_ID,
                command=StoryWorkspaceDreamAgentToolConfirmationCommand(
                    toolCallId="tool-duplicate-text",
                    approved=True,
                    answers={"one": "甲", "two": "乙"},
                ),
            )
        self.assertFalse(
            any(item[0] == "confirm" for item in duplicate_text_factory.confirmations)
        )

    def test_confirm_tool_requires_same_active_trusted_dream_turn(self) -> None:
        factory = _ToolConfirmationFactory()
        factory.frames = [
            'data: {"type":"tool-approval-request","toolCallId":"tool-ask",'
            '"toolName":"AskUserQuestion","input":{"questions":[{'
            '"question":"继续吗？","options":["继续","停止"]}]}}\n\n',
        ]
        service = StoryWorkspaceDreamAgentMessageService(
            self.db,
            thread_factory=factory,
        )
        command = StoryWorkspaceDreamAgentToolConfirmationCommand(
            toolCallId="tool-ask",
            approved=True,
            reason="用户已选择",
            answers={"q0": "继续"},
        )
        accepted = asyncio.run(_act_while_tool_confirmation_pending(
            service,
            lambda: service.confirm_tool(
                run_id=RUN_ID,
                thread_id=THREAD_ID,
                actor_id=ACTOR_ID,
                command=command,
            ),
        ))
        self.assertTrue(accepted.resolved)
        self.assertEqual(accepted.story_workspace_run_id, RUN_ID)
        self.assertEqual(accepted.tool_call_id, "tool-ask")
        self.assertNotIn(THREAD_ID, accepted.model_dump_json())
        self.assertEqual(factory.confirmations[-1], (
            "confirm",
            {
                "session_id": THREAD_ID,
                "tool_call_id": "tool-ask",
                "approved": True,
                "reason": "用户已选择",
                "answers": {"继续吗？": "继续"},
            },
        ))

        with self.assertRaisesRegex(
            StoryWorkspaceDreamAgentMessageError,
            "DREAM_AGENT_TOOL_CONFIRMATION_NOT_READY",
        ):
            StoryWorkspaceDreamAgentMessageService(
                self.db,
                thread_factory=_ToolConfirmationFactory(trusted=False),
            ).confirm_tool(
                run_id=RUN_ID,
                thread_id=THREAD_ID,
                actor_id=ACTOR_ID,
                command=command,
            )

    def test_confirm_tool_accepts_only_current_public_ask_user_answers(self) -> None:
        questions = [
            {"id": "note", "question": "补充说明", "type": "text", "required": True},
            {
                "id": "style",
                "question": "选择风格",
                "type": "radio",
                "required": True,
                "options": ["温暖", "冷峻"],
            },
            {
                "id": "confirm",
                "question": "确认继续",
                "type": "checkbox",
                "required": True,
            },
            {
                "id": "elements",
                "question": "选择元素",
                "type": "checkbox",
                "multiSelect": True,
                "required": True,
                "options": ["雨", "灯"],
            },
        ]

        def pending_service() -> tuple[
            StoryWorkspaceDreamAgentMessageService,
            _ToolConfirmationFactory,
        ]:
            factory = _ToolConfirmationFactory()
            factory.frames = [
                "data: " + json.dumps({
                    "type": "tool-approval-request",
                    "toolCallId": "tool-current",
                    "toolName": "AskUserQuestion",
                    "input": {"questions": questions},
                }, ensure_ascii=False) + "\n\n",
            ]
            service = StoryWorkspaceDreamAgentMessageService(
                self.db,
                thread_factory=factory,
            )
            return service, factory

        valid_service, valid_factory = pending_service()
        accepted = asyncio.run(_act_while_tool_confirmation_pending(
            valid_service,
            lambda: valid_service.confirm_tool(
                run_id=RUN_ID,
                thread_id=THREAD_ID,
                actor_id=ACTOR_ID,
                command=StoryWorkspaceDreamAgentToolConfirmationCommand(
                    toolCallId="tool-current",
                    approved=True,
                    answers={
                        "q0": "继续完善人物动机",
                        "q1": "温暖",
                        "q2": True,
                        "q3": ["雨", "灯"],
                    },
                ),
            ),
        ))
        self.assertTrue(accepted.resolved)
        self.assertEqual(valid_factory.confirmations[-1][0], "confirm")
        self.assertEqual(valid_factory.confirmations[-1][1]["answers"], {
            "补充说明": "继续完善人物动机",
            "选择风格": "温暖",
            "确认继续": True,
            "选择元素": ["雨", "灯"],
        })

        invalid_answers = (
            {"unknown": "继续"},
            {"note": "公开说明", "q1": "温暖", "q2": True, "q3": ["雨"]},
            {"q0": "公开说明", "q1": "秘密风格", "q2": True, "q3": ["雨"]},
            {"q0": "公开说明", "q1": "温暖", "q2": True, "q3": ["雨", "不存在"]},
            {"q0": "公开说明", "q1": "温暖", "q2": "true", "q3": ["雨"]},
            {"q0": "", "q1": "温暖", "q2": True, "q3": ["雨"]},
        )
        for answers in invalid_answers:
            with self.subTest(answers=answers):
                service, factory = pending_service()
                with self.assertRaisesRegex(
                    StoryWorkspaceDreamAgentMessageError,
                    "DREAM_AGENT_TOOL_CONFIRMATION_INVALID",
                ):
                    asyncio.run(_act_while_tool_confirmation_pending(
                        service,
                        lambda: service.confirm_tool(
                            run_id=RUN_ID,
                            thread_id=THREAD_ID,
                            actor_id=ACTOR_ID,
                            command=StoryWorkspaceDreamAgentToolConfirmationCommand(
                                toolCallId="tool-current",
                                approved=True,
                                answers=answers,
                            ),
                        ),
                    ))
                self.assertFalse(any(item[0] == "confirm" for item in factory.confirmations))

        wrong_tool_service, wrong_tool_factory = pending_service()
        with self.assertRaisesRegex(
            StoryWorkspaceDreamAgentMessageError,
            "DREAM_AGENT_TOOL_CONFIRMATION_NOT_READY",
        ):
            asyncio.run(_act_while_tool_confirmation_pending(
                wrong_tool_service,
                lambda: wrong_tool_service.confirm_tool(
                    run_id=RUN_ID,
                    thread_id=THREAD_ID,
                    actor_id=ACTOR_ID,
                    command=StoryWorkspaceDreamAgentToolConfirmationCommand(
                        toolCallId="tool-other",
                        approved=True,
                    ),
                ),
            ))
        self.assertFalse(
            any(item[0] == "confirm" for item in wrong_tool_factory.confirmations)
        )

        reject_service, reject_factory = pending_service()
        with self.assertRaisesRegex(
            StoryWorkspaceDreamAgentMessageError,
            "DREAM_AGENT_TOOL_CONFIRMATION_INVALID",
        ):
            asyncio.run(_act_while_tool_confirmation_pending(
                reject_service,
                lambda: reject_service.confirm_tool(
                    run_id=RUN_ID,
                    thread_id=THREAD_ID,
                    actor_id=ACTOR_ID,
                    command=StoryWorkspaceDreamAgentToolConfirmationCommand(
                        toolCallId="tool-current",
                        approved=False,
                        answers={"q1": "温暖"},
                    ),
                ),
            ))
        self.assertFalse(any(item[0] == "confirm" for item in reject_factory.confirmations))

    def test_tool_confirmation_contract_rejects_untrusted_context_and_oversized_answers(self) -> None:
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            StoryWorkspaceDreamAgentToolConfirmation.model_validate({
                "toolCallId": "tool-secret",
                "kind": "approval",
                "toolName": "Write",
                "input": {"file_path": "/Users/private/script.md"},
            })
        with self.assertRaises(ValidationError):
            StoryWorkspaceDreamAgentToolConfirmation.model_validate({
                "toolCallId": "tool-secret",
                "kind": "approval",
                "toolName": "Write",
                "title": "/Users/private/script.md",
            })
        with self.assertRaises(ValidationError):
            StoryWorkspaceDreamAgentToolConfirmationCommand.model_validate({
                "toolCallId": "tool-1",
                "approved": True,
                "threadId": THREAD_ID,
            })
        with self.assertRaises(ValidationError):
            StoryWorkspaceDreamAgentToolConfirmationCommand(
                toolCallId="x" * 256,
                approved=True,
            )
        with self.assertRaises(ValidationError):
            StoryWorkspaceDreamAgentToolConfirmationCommand(
                toolCallId="tool-1",
                approved=True,
                reason="x" * 501,
            )
        with self.assertRaises(ValidationError):
            StoryWorkspaceDreamAgentToolConfirmationCommand(
                toolCallId="tool-1",
                approved=True,
                answers={"q1": {"nested": "forbidden"}},
            )

    def test_events_never_forward_a_live_turn_without_trusted_dream_source(self) -> None:
        class GenericTurnFactory(_Factory):
            def is_expected_story_workspace_dream_turn(self, *_args) -> bool:
                return False

        service = StoryWorkspaceDreamAgentMessageService(
            self.db,
            thread_factory=GenericTurnFactory(
                running=True,
                frames=['data: {"type":"text-delta","delta":"ordinary"}\n\n'],
            ),
        )
        output = "".join(asyncio.run(_collect(service.events(
            thread_id=THREAD_ID, run_id=RUN_ID, actor_id=ACTOR_ID,
        ))))
        self.assertIn('"lifecycle":"idle"', output)
        self.assertNotIn("ordinary", output)

    def test_public_confirmation_registry_never_evicts_a_live_entry_at_capacity(self) -> None:
        factory = _ToolConfirmationFactory()
        for index in range(_DREAM_PUBLIC_TOOL_CONFIRMATIONS_MAX):
            self.assertTrue(_remember_dream_public_confirmation(
                factory,
                thread_id=THREAD_ID,
                turn_id="turn-capacity",
                run_id=RUN_ID,
                actor_id=ACTOR_ID,
                confirmation={
                    "toolCallId": f"tool-{index}",
                    "kind": "approval",
                    "toolName": "Write",
                },
            ))
        self.assertFalse(_remember_dream_public_confirmation(
            factory,
            thread_id=THREAD_ID,
            turn_id="turn-capacity",
            run_id=RUN_ID,
            actor_id=ACTOR_ID,
            confirmation={
                "toolCallId": "tool-over-capacity",
                "kind": "approval",
                "toolName": "Write",
            },
        ))
        registry = _dream_public_confirmation_registry(factory, create=False)
        assert registry is not None
        self.assertEqual(len(registry), _DREAM_PUBLIC_TOOL_CONFIRMATIONS_MAX)
        self.assertTrue(any(key[-1] == "tool-0" for key in registry))
        self.assertFalse(any(key[-1] == "tool-over-capacity" for key in registry))

    def test_snapshot_recovers_only_runtime_pending_safe_projection_and_prunes_stale(self) -> None:
        factory = _ToolConfirmationFactory()
        factory.pending_tool_call_ids = {"tool-write"}
        self.assertTrue(_remember_dream_public_confirmation(
            factory,
            thread_id=THREAD_ID,
            turn_id="turn-1",
            run_id=RUN_ID,
            actor_id=ACTOR_ID,
            confirmation={
                "toolCallId": "tool-write",
                "kind": "approval",
                "toolName": "Write",
            },
        ))
        self.assertTrue(_remember_dream_public_confirmation(
            factory,
            thread_id=THREAD_ID,
            turn_id="turn-1",
            run_id=RUN_ID,
            actor_id=ACTOR_ID,
            confirmation={
                "toolCallId": "tool-timeout",
                "kind": "approval",
                "toolName": "Write",
            },
        ))
        self.assertTrue(_remember_dream_public_confirmation(
            factory,
            thread_id=THREAD_ID,
            turn_id="turn-1",
            run_id=RUN_ID,
            actor_id="other-actor",
            confirmation={
                "toolCallId": "tool-foreign",
                "kind": "approval",
                "toolName": "Write",
            },
        ))

        with patch(
            "services.story_workspace.dream_agent_message_service.story_workspace_read_dream_confirmation_fact",
            return_value=(True, True),
        ):
            snapshot = StoryWorkspaceDreamAgentMessageService(
                self.db,
                thread_factory=factory,
            ).snapshot(
                run_id=RUN_ID,
                thread_id=THREAD_ID,
                actor_id=ACTOR_ID,
            )

        self.assertEqual(
            [item.tool_call_id for item in snapshot.pending_tool_confirmations],
            ["tool-write"],
        )
        payload = snapshot.model_dump_json(by_alias=True)
        self.assertNotIn("/Users/", payload)
        self.assertNotIn("file_path", payload)
        self.assertNotIn("input", payload)
        registry = _dream_public_confirmation_registry(factory, create=False)
        assert registry is not None
        self.assertFalse(any(key[-1] == "tool-timeout" for key in registry))
        self.assertTrue(any(key[-1] == "tool-foreign" for key in registry))

    def test_disconnect_keeps_runtime_pending_projection_recoverable_from_snapshot(self) -> None:
        async def exercise():
            factory = _ToolConfirmationFactory()
            factory.frames = [
                'data: {"type":"tool-approval-request","toolCallId":"tool-pending",'
                '"toolName":"Write","input":{"file_path":"/Users/private/script.md"}}\n\n',
            ]
            service = StoryWorkspaceDreamAgentMessageService(
                self.db,
                thread_factory=factory,
            )
            stream = service.events(
                thread_id=THREAD_ID,
                run_id=RUN_ID,
                actor_id=ACTOR_ID,
            )
            await _next_tool_confirmation(stream)
            await stream.aclose()
            with patch(
                "services.story_workspace.dream_agent_message_service.story_workspace_read_dream_confirmation_fact",
                return_value=(True, True),
            ):
                return service.snapshot(
                    run_id=RUN_ID,
                    thread_id=THREAD_ID,
                    actor_id=ACTOR_ID,
                )

        snapshot = asyncio.run(exercise())
        self.assertEqual(
            [item.tool_call_id for item in snapshot.pending_tool_confirmations],
            ["tool-pending"],
        )

    def test_confirm_prunes_exact_projection_when_runtime_no_longer_pending(self) -> None:
        factory = _ToolConfirmationFactory()
        factory.pending_tool_call_ids = set()
        self.assertTrue(_remember_dream_public_confirmation(
            factory,
            thread_id=THREAD_ID,
            turn_id="turn-1",
            run_id=RUN_ID,
            actor_id=ACTOR_ID,
            confirmation={
                "toolCallId": "tool-timeout",
                "kind": "approval",
                "toolName": "Write",
            },
        ))
        service = StoryWorkspaceDreamAgentMessageService(
            self.db,
            thread_factory=factory,
        )

        with self.assertRaisesRegex(
            StoryWorkspaceDreamAgentMessageError,
            "DREAM_AGENT_TOOL_CONFIRMATION_NOT_READY",
        ):
            service.confirm_tool(
                run_id=RUN_ID,
                thread_id=THREAD_ID,
                actor_id=ACTOR_ID,
                command=StoryWorkspaceDreamAgentToolConfirmationCommand(
                    toolCallId="tool-timeout",
                    approved=True,
                ),
            )

        registry = _dream_public_confirmation_registry(factory, create=False)
        self.assertEqual(registry, {})
        self.assertFalse(any(item[0] == "confirm" for item in factory.confirmations))

    def test_events_disconnect_retains_runtime_pending_turn_and_actor_registry(self) -> None:
        async def exercise() -> None:
            factory = _ToolConfirmationFactory()
            factory.frames = [
                'data: {"type":"tool-approval-request","toolCallId":"tool-pending",'
                '"toolName":"AskUserQuestion","input":{"question":"继续吗？",'
                '"options":["继续","停止"]}}\n\n',
            ]
            service = StoryWorkspaceDreamAgentMessageService(
                self.db,
                thread_factory=factory,
            )
            first_stream = service.events(
                thread_id=THREAD_ID,
                run_id=RUN_ID,
                actor_id=ACTOR_ID,
            )
            await _next_tool_confirmation(first_stream)

            factory.current_turn_id = "turn-2"
            second_stream = service.events(
                thread_id=THREAD_ID,
                run_id=RUN_ID,
                actor_id="8",
            )
            await _next_tool_confirmation(second_stream)
            registry = _dream_public_confirmation_registry(factory, create=False)
            assert registry is not None
            self.assertTrue(any(key[1:4] == ("turn-1", RUN_ID, ACTOR_ID) for key in registry))
            self.assertTrue(any(key[1:4] == ("turn-2", RUN_ID, "8") for key in registry))

            await first_stream.aclose()
            self.assertTrue(any(key[1:4] == ("turn-1", RUN_ID, ACTOR_ID) for key in registry))
            self.assertTrue(any(key[1:4] == ("turn-2", RUN_ID, "8") for key in registry))

            accepted = service.confirm_tool(
                run_id=RUN_ID,
                thread_id=THREAD_ID,
                actor_id="8",
                command=StoryWorkspaceDreamAgentToolConfirmationCommand(
                    toolCallId="tool-pending",
                    approved=True,
                    answers={"q0": "继续"},
                ),
            )
            self.assertTrue(accepted.resolved)
            await second_stream.aclose()
            self.assertTrue(any(key[1:4] == ("turn-1", RUN_ID, ACTOR_ID) for key in registry))
            self.assertFalse(any(key[1:4] == ("turn-2", RUN_ID, "8") for key in registry))

        asyncio.run(exercise())

    def test_terminal_event_cleans_every_confirmation_for_the_same_turn(self) -> None:
        factory = _ToolConfirmationFactory()
        factory.frames = [
            'data: {"type":"tool-approval-request","toolCallId":"tool-one",'
            '"toolName":"Write","input":{}}\n\n',
            'data: {"type":"tool-approval-request","toolCallId":"tool-two",'
            '"toolName":"Write","input":{}}\n\n',
            'data: {"type":"message-final"}\n\n',
        ]
        output = "".join(asyncio.run(_collect(
            StoryWorkspaceDreamAgentMessageService(
                self.db,
                thread_factory=factory,
            ).events(
                thread_id=THREAD_ID,
                run_id=RUN_ID,
                actor_id=ACTOR_ID,
            )
        )))
        self.assertEqual(output.count("event: tool_confirmation_requested"), 2)
        self.assertIn("event: assistant_message_committed", output)
        registry = _dream_public_confirmation_registry(factory, create=False)
        self.assertEqual(registry, {})

    def test_same_turn_subscriptions_hold_registry_until_the_last_release(self) -> None:
        async def exercise() -> None:
            factory = _ToolConfirmationFactory()
            factory.frames = [
                'data: {"type":"tool-approval-request","toolCallId":"tool-one",'
                '"toolName":"Write","input":{}}\n\n',
                'data: {"type":"tool-approval-request","toolCallId":"tool-two",'
                '"toolName":"Write","input":{}}\n\n',
            ]
            service = StoryWorkspaceDreamAgentMessageService(
                self.db,
                thread_factory=factory,
            )
            first_stream = service.events(
                thread_id=THREAD_ID,
                run_id=RUN_ID,
                actor_id=ACTOR_ID,
            )
            second_stream = service.events(
                thread_id=THREAD_ID,
                run_id=RUN_ID,
                actor_id=ACTOR_ID,
            )
            await _next_tool_confirmation(first_stream)
            await _next_tool_confirmation(first_stream)
            await _next_tool_confirmation(second_stream)
            await _next_tool_confirmation(second_stream)
            registry = _dream_public_confirmation_registry(factory, create=False)
            assert registry is not None
            self.assertEqual(len(registry), 2)

            await first_stream.aclose()
            self.assertEqual(len(registry), 2)
            accepted = service.confirm_tool(
                run_id=RUN_ID,
                thread_id=THREAD_ID,
                actor_id=ACTOR_ID,
                command=StoryWorkspaceDreamAgentToolConfirmationCommand(
                    toolCallId="tool-one",
                    approved=False,
                ),
            )
            self.assertTrue(accepted.resolved)
            self.assertEqual(len(registry), 1)

            await second_stream.aclose()
            self.assertEqual(len(registry), 1)
            self.assertTrue(any(key[-1] == "tool-two" for key in registry))

        asyncio.run(exercise())

    def test_claim_same_key_replays_different_text_conflicts_and_second_key_is_busy(self) -> None:
        service = StoryWorkspaceDreamAgentMessageService(self.db)
        first = StoryWorkspaceDreamAgentMessageCommand(text="继续", idempotencyKey="key-1")
        second = StoryWorkspaceDreamAgentMessageCommand(text="另一条", idempotencyKey="key-2")
        with patch(
            "services.story_workspace.dream_agent_message_service.story_workspace_read_dream_confirmation_fact",
            return_value=(True, True),
        ):
            accepted, pending = service.claim_message(
                run_id=RUN_ID, thread_id=THREAD_ID, actor_id=ACTOR_ID, context=_context(), command=first
            )
            replay, replay_pending = service.claim_message(
                run_id=RUN_ID, thread_id=THREAD_ID, actor_id=ACTOR_ID, context=_context(), command=first
            )
            with self.assertRaisesRegex(StoryWorkspaceDreamAgentMessageError, "IDEMPOTENCY_CONFLICT"):
                service.claim_message(
                    run_id=RUN_ID, thread_id=THREAD_ID, actor_id=ACTOR_ID, context=_context(),
                    command=StoryWorkspaceDreamAgentMessageCommand(text="改了", idempotencyKey="key-1"),
                )
            with self.assertRaisesRegex(StoryWorkspaceDreamAgentMessageError, "DREAM_AGENT_MESSAGE_BUSY"):
                service.claim_message(
                    run_id=RUN_ID, thread_id=THREAD_ID, actor_id=ACTOR_ID, context=_context(), command=second
                )
        self.assertIsNotNone(pending)
        self.assertIsNone(replay_pending)
        self.assertEqual(accepted.message_id, replay.message_id)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM chat_message").fetchone()[0], 1)

    def test_claim_rejects_before_one_confirmation_dispatch_and_when_live(self) -> None:
        command = StoryWorkspaceDreamAgentMessageCommand(text="继续", idempotencyKey="key-1")
        with patch(
            "services.story_workspace.dream_agent_message_service.story_workspace_read_dream_confirmation_fact",
            return_value=(False, False),
        ):
            with self.assertRaisesRegex(StoryWorkspaceDreamAgentMessageError, "NOT_READY"):
                StoryWorkspaceDreamAgentMessageService(self.db).claim_message(
                    run_id=RUN_ID, thread_id=THREAD_ID, actor_id=ACTOR_ID, context=_context(), command=command
                )
        with patch(
            "services.story_workspace.dream_agent_message_service.story_workspace_read_dream_confirmation_fact",
            return_value=(True, True),
        ):
            with self.assertRaisesRegex(StoryWorkspaceDreamAgentMessageError, "NOT_READY"):
                StoryWorkspaceDreamAgentMessageService(self.db, thread_factory=_Factory(running=True)).claim_message(
                    run_id=RUN_ID, thread_id=THREAD_ID, actor_id=ACTOR_ID, context=_context(), command=command
                )

    def test_pending_claim_projects_busy_renews_lease_and_same_key_recovers(self) -> None:
        service = StoryWorkspaceDreamAgentMessageService(self.db)
        command = StoryWorkspaceDreamAgentMessageCommand(text="继续", idempotencyKey="key-lease")
        with patch(
            "services.story_workspace.dream_agent_message_service.story_workspace_read_dream_confirmation_fact",
            return_value=(True, True),
        ):
            _accepted, pending = service.claim_message(
                run_id=RUN_ID, thread_id=THREAD_ID, actor_id=ACTOR_ID, context=_context(), command=command
            )
            snapshot = service.snapshot(run_id=RUN_ID, thread_id=THREAD_ID, actor_id=ACTOR_ID)
            self.assertEqual(snapshot.send_block_reason, "busy")
            self.assertFalse(snapshot.can_send)
            assert pending is not None
            before = json.loads(self.db.execute("SELECT metadata FROM chat_message").fetchone()[0])
            self.assertTrue(service._renew_claim(pending.message_id, pending.metadata["dispatch_claim_id"]))  # noqa: SLF001
            after = json.loads(self.db.execute("SELECT metadata FROM chat_message").fetchone()[0])
            self.assertGreater(after["dispatch_claim_lease_until"], before["dispatch_claim_lease_until"])
            service._release_claim(pending.message_id, pending.metadata["dispatch_claim_id"])  # noqa: SLF001
            expired = json.loads(self.db.execute("SELECT metadata FROM chat_message").fetchone()[0])
            expired["dispatch_status"] = "dispatching"
            expired["dispatch_claim_lease_until"] = 0
            self.db.execute(
                "UPDATE chat_message SET metadata = ? WHERE id = ?",
                (json.dumps(expired), pending.message_id),
            )
            self.db.commit()
            _replay, recovered = service.claim_message(
                run_id=RUN_ID, thread_id=THREAD_ID, actor_id=ACTOR_ID, context=_context(), command=command
            )
        self.assertIsNotNone(recovered)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM chat_message").fetchone()[0], 1)

    def test_expired_claim_handoff_rejects_old_owner_heartbeat_and_ack(self) -> None:
        service = StoryWorkspaceDreamAgentMessageService(self.db)
        command = StoryWorkspaceDreamAgentMessageCommand(text="继续", idempotencyKey="key-handoff")
        with patch(
            "services.story_workspace.dream_agent_message_service.story_workspace_read_dream_confirmation_fact",
            return_value=(True, True),
        ):
            _accepted, old_pending = service.claim_message(
                run_id=RUN_ID, thread_id=THREAD_ID, actor_id=ACTOR_ID, context=_context(), command=command
            )
            assert old_pending is not None
            expired = json.loads(self.db.execute("SELECT metadata FROM chat_message").fetchone()[0])
            expired["dispatch_claim_lease_until"] = 0
            self.db.execute(
                "UPDATE chat_message SET metadata = ? WHERE id = ?",
                (json.dumps(expired), old_pending.message_id),
            )
            self.db.commit()
            _replayed, new_pending = service.claim_message(
                run_id=RUN_ID, thread_id=THREAD_ID, actor_id=ACTOR_ID, context=_context(), command=command
            )
        assert new_pending is not None
        old_claim_id = old_pending.metadata["dispatch_claim_id"]
        new_claim_id = new_pending.metadata["dispatch_claim_id"]
        self.assertNotEqual(old_claim_id, new_claim_id)
        self.assertFalse(service._renew_claim(old_pending.message_id, old_claim_id))  # noqa: SLF001
        self.assertIs(service._mark_dispatched(old_pending.message_id, old_claim_id), False)  # noqa: SLF001
        metadata = json.loads(self.db.execute("SELECT metadata FROM chat_message").fetchone()[0])
        self.assertEqual(metadata["dispatch_claim_id"], new_claim_id)
        self.assertEqual(metadata["dispatch_status"], "dispatching")
        self.assertGreater(metadata["dispatch_claim_lease_until"], 0)

    def test_snapshot_names_initial_live_turn_as_generating_not_continuing(self) -> None:
        with patch(
            "services.story_workspace.dream_agent_message_service.story_workspace_read_dream_confirmation_fact",
            return_value=(False, False),
        ):
            snapshot = StoryWorkspaceDreamAgentMessageService(
                self.db, thread_factory=_Factory(running=True)
            ).snapshot(run_id=RUN_ID, thread_id=THREAD_ID, actor_id=ACTOR_ID)
        self.assertEqual(snapshot.send_block_reason, "generating")
        self.assertFalse(snapshot.can_send)

    def test_dispatch_uses_same_authoritative_thread_and_dream_context_once(self) -> None:
        factory = _Factory()
        service = StoryWorkspaceDreamAgentMessageService(self.db, thread_factory=factory)
        command = StoryWorkspaceDreamAgentMessageCommand(text="继续", idempotencyKey="key-1")
        with patch(
            "services.story_workspace.dream_agent_message_service.story_workspace_read_dream_confirmation_fact",
            return_value=(True, True),
        ):
            _accepted, pending = service.claim_message(
                run_id=RUN_ID, thread_id=THREAD_ID, actor_id=ACTOR_ID, context=_context(), command=command
            )
        assert pending is not None
        asyncio.run(service.dispatch(pending))
        self.assertEqual(len(factory.requests), 1)
        request = factory.requests[0]
        self.assertEqual(request.thread_id, THREAD_ID)
        self.assertEqual(request.story_workspace_dream_context, _context())
        metadata = json.loads(self.db.execute("SELECT metadata FROM chat_message").fetchone()[0])
        self.assertEqual(metadata["dispatch_status"], "dispatched")


class StoryWorkspaceDreamAgentBindingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            CREATE TABLE story_workspace_workspaces (id TEXT PRIMARY KEY, owner_id INTEGER);
            CREATE TABLE workflow_runs (
                id TEXT PRIMARY KEY, workspace_id TEXT, created_by TEXT,
                source_voice_thread_id TEXT, deck_plugin_id TEXT, deck_plugin_version TEXT,
                deck_plugin_binding_id TEXT, binding_revision INTEGER,
                deck_runtime_snapshot_id TEXT, runtime_plugin_lock_id TEXT
            );
            CREATE TABLE deck_plugin_bindings (
                deck_plugin_binding_id TEXT, binding_revision INTEGER,
                deck_plugin_id TEXT, deck_plugin_version TEXT, deck_id TEXT,
                workspace_id TEXT
            );
            CREATE TABLE chat_thread (id TEXT PRIMARY KEY, user_id INTEGER, deck_id TEXT);
            INSERT INTO story_workspace_workspaces VALUES ('workspace-1', 7);
            INSERT INTO workflow_runs VALUES (
                'run_0123456789abcdef0123456789abcdef', 'workspace-1', '7', 'dream-thread',
                'drama-forge', '1.0.0', 'binding-1', 1, 'snapshot-1', 'lock-1'
            );
            INSERT INTO deck_plugin_bindings VALUES ('binding-1', 1, 'drama-forge', '1.0.0', 'deck-1', 'workspace-1');
            INSERT INTO chat_thread VALUES ('dream-thread', 7, 'deck-1');
            """
        )

    def tearDown(self) -> None:
        self.db.close()

    def test_context_requires_actor_run_thread_and_exact_deck_binding(self) -> None:
        gateway = StoryWorkflowApplicationGateway()
        context = gateway._load_dream_agent_context_from_db(  # noqa: SLF001 - contract seam
            self.db, RUN_ID, {"actor_id": ACTOR_ID}
        )
        self.assertEqual(context.deck_id, "deck-1")
        self.db.execute("UPDATE chat_thread SET deck_id = 'wrong-deck' WHERE id = ?", (THREAD_ID,))
        with self.assertRaises(ApiRouteError) as wrong_deck:
            gateway._load_dream_agent_context_from_db(self.db, RUN_ID, {"actor_id": ACTOR_ID})
        self.assertEqual(wrong_deck.exception.status_code, 404)
        with self.assertRaises(ApiRouteError) as foreign:
            gateway._load_dream_agent_context_from_db(self.db, RUN_ID, {"actor_id": "8"})
        self.assertEqual(foreign.exception.status_code, 403)
        self.db.execute("UPDATE chat_thread SET deck_id = 'deck-1' WHERE id = ?", (THREAD_ID,))
        self.db.execute("UPDATE deck_plugin_bindings SET workspace_id = 'other-workspace'")
        with self.assertRaises(ApiRouteError) as cross_workspace:
            gateway._load_dream_agent_context_from_db(self.db, RUN_ID, {"actor_id": ACTOR_ID})
        self.assertEqual(cross_workspace.exception.status_code, 404)

    def test_gateway_confirms_only_on_the_thread_resolved_from_authorized_run(self) -> None:
        gateway = StoryWorkflowApplicationGateway()
        factory = _ToolConfirmationFactory()
        command = StoryWorkspaceDreamAgentToolConfirmationCommand(
            toolCallId="tool-1",
            approved=False,
            reason="暂不执行",
        )

        def open_db():
            connection = sqlite3.connect(":memory:")
            connection.row_factory = sqlite3.Row
            return connection

        factory.frames = [
            'data: {"type":"tool-approval-request","toolCallId":"tool-1",'
            '"toolName":"Write","input":{"file_path":"not-public"}}\n\n',
        ]
        event_db = open_db()
        event_service = StoryWorkspaceDreamAgentMessageService(
            event_db,
            thread_factory=factory,
        )

        async def confirm_while_pending():
            stream = event_service.events(
                thread_id=THREAD_ID,
                run_id=RUN_ID,
                actor_id=ACTOR_ID,
            )
            await _next_tool_confirmation(stream)
            try:
                return await gateway.confirm_dream_agent_tool(
                    RUN_ID,
                    command,
                    actor={"actor_id": ACTOR_ID},
                )
            finally:
                await stream.aclose()

        with (
            patch.object(
                gateway,
                "_load_dream_agent_context_sync",
                return_value=_context(),
            ) as load_context,
            patch.object(
                gateway,
                "_dream_agent_thread_factory",
                return_value=factory,
            ),
            patch(
                "services.deck.story_workflow_gateway.database.get_db",
                side_effect=open_db,
            ),
        ):
            try:
                accepted = asyncio.run(confirm_while_pending())
            finally:
                event_db.close()

        load_context.assert_called_once_with(RUN_ID, {"actor_id": ACTOR_ID})
        self.assertFalse(accepted.approved)
        self.assertEqual(factory.confirmations[-1][1]["session_id"], THREAD_ID)


class StoryWorkspaceDreamAssistantPersistenceTest(unittest.TestCase):
    def test_only_permitted_dream_source_turn_marks_assistant_persistence(self) -> None:
        metadata: dict[str, object] = {}
        _attach_story_workspace_dream_assistant_source(
            metadata,
            ClaudeAgentRunRequest(
                user_id=ACTOR_ID,
                thread_id=THREAD_ID,
                message_id="source-message",
                message_metadata={"kind": STORY_WORKSPACE_DREAM_AGENT_USER_KIND},
                story_workspace_dream_context=_context(),
            ),
        )
        self.assertEqual(metadata["story_workspace_dream_source"], {
            "run_id": RUN_ID, "thread_id": THREAD_ID, "actor_id": ACTOR_ID,
            "message_id": "source-message", "kind": STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
        })
        normal: dict[str, object] = {}
        _attach_story_workspace_dream_assistant_source(
            normal,
            ClaudeAgentRunRequest(user_id=ACTOR_ID, thread_id=THREAD_ID, message_id="ordinary"),
        )
        self.assertEqual(normal, {})


class StoryWorkspaceDreamExpectedTurnSubscriptionTest(unittest.TestCase):
    def test_ended_or_replaced_turn_is_idle_not_a_transport_exception(self) -> None:
        factory = ClaudeAgentThreadFactory()
        state = factory._pool.get_or_create(THREAD_ID)  # noqa: SLF001 - race seam
        state.mark_running()
        state.current_turn_id = "turn-new"

        async def collect():
            return [frame async for frame in factory.subscribe_expected_stream(THREAD_ID, "turn-old")]

        self.assertEqual(asyncio.run(collect()), [])


class StoryWorkspaceDreamMessageCoordinatorTest(unittest.TestCase):
    def test_coordinator_coalesces_one_pending_message_dispatch(self) -> None:
        calls: list[str] = []

        # The service-level recovery test above locks the durable same-key path;
        # this small async seam verifies the coordinator cannot double-schedule.
        async def execute() -> None:
            release_event = asyncio.Event()

            async def dispatch(item):
                calls.append(item.message_id)
                await release_event.wait()

            coordinator = StoryWorkspaceDreamAgentMessageCoordinator(dispatch)
            item = _pending_dispatch()
            self.assertTrue(coordinator.schedule(item))
            self.assertFalse(coordinator.schedule(item))
            await asyncio.sleep(0)
            release_event.set()
            await asyncio.sleep(0)

        asyncio.run(execute())
        self.assertEqual(calls, ["pending-message"])


class _DreamAgentRouteGateway:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    async def get_dream_agent_messages(self, run_id: str, *, actor: dict[str, str]):
        self.calls.append(("snapshot", actor))
        return StoryWorkspaceDreamAgentMessageSnapshot(
            story_workspace_run_id=run_id,
            lifecycle="idle",
            active_turn_id=None,
            can_send=True,
            messages=[],
            snapshot_at=datetime.now(UTC),
        )

    async def stream_dream_agent_events(self, run_id: str, *, actor: dict[str, str], after: str | None):
        self.calls.append(("events", (actor, after)))

        async def frames():
            yield ": keepalive\n\n"
            yield "event: assistant_text_delta\ndata: {\\\"turnId\\\":\\\"turn-1\\\",\\\"delta\\\":\\\"公开\\\"}\n\n"

        return frames()

    async def submit_dream_agent_message(self, run_id: str, request, *, actor: dict[str, str]):
        self.calls.append(("send", (actor, request.text, request.idempotency_key)))
        return StoryWorkspaceDreamAgentMessageAccepted(
            story_workspace_run_id=run_id,
            message_id="dream_agent_test",
        )

    async def confirm_dream_agent_tool(self, run_id: str, request, *, actor: dict[str, str]):
        self.calls.append((
            "tool-confirm",
            (actor, request.tool_call_id, request.approved, request.reason, request.answers),
        ))
        from story_workspace.contracts import StoryWorkspaceDreamAgentToolConfirmationAccepted

        return StoryWorkspaceDreamAgentToolConfirmationAccepted(
            story_workspace_run_id=run_id,
            tool_call_id=request.tool_call_id,
            approved=request.approved,
        )


class StoryWorkspaceDreamAgentRouteTest(unittest.TestCase):
    def test_snapshot_events_send_and_tool_confirm_use_run_bound_gateway_contracts(self) -> None:
        app = FastAPI()
        gateway = _DreamAgentRouteGateway()
        app.dependency_overrides[story_workspace.get_current_user] = lambda: {"user_id": 7}
        app.dependency_overrides[story_workspace.get_story_workflow_gateway] = lambda: gateway
        app.include_router(story_workspace.router)
        client = TestClient(app)
        try:
            snapshot = client.get(f"/api/story-workspace/workflow-runs/{RUN_ID}/dream-agent/messages")
            events = client.get(
                f"/api/story-workspace/workflow-runs/{RUN_ID}/dream-agent/events?after=turn-1:2"
            )
            sent = client.post(
                f"/api/story-workspace/workflow-runs/{RUN_ID}/dream-agent/messages",
                json={"text": "继续", "idempotencyKey": "key-1"},
            )
            confirmed = client.post(
                f"/api/story-workspace/workflow-runs/{RUN_ID}/dream-agent/tool-confirm",
                json={
                    "toolCallId": "tool-ask",
                    "approved": True,
                    "reason": "继续",
                    "answers": {"q1": "继续"},
                },
            )
            rejected_context = client.post(
                f"/api/story-workspace/workflow-runs/{RUN_ID}/dream-agent/tool-confirm",
                json={
                    "toolCallId": "tool-ask",
                    "approved": True,
                    "threadId": THREAD_ID,
                },
            )
            rejected_deck_context = client.post(
                f"/api/story-workspace/workflow-runs/{RUN_ID}/dream-agent/tool-confirm",
                json={
                    "toolCallId": "tool-ask",
                    "approved": True,
                    "deckId": "deck-1",
                },
            )
        finally:
            client.close()
        self.assertEqual(snapshot.status_code, 200, snapshot.text)
        self.assertEqual(snapshot.json()["storyWorkspaceRunId"], RUN_ID)
        self.assertEqual(events.status_code, 200, events.text)
        self.assertIn("assistant_text_delta", events.text)
        self.assertNotIn("reasoning", events.text)
        self.assertEqual(sent.status_code, 202, sent.text)
        self.assertEqual(sent.json()["messageId"], "dream_agent_test")
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        self.assertEqual(confirmed.json(), {
            "storyWorkspaceRunId": RUN_ID,
            "toolCallId": "tool-ask",
            "approved": True,
            "resolved": True,
        })
        self.assertEqual(rejected_context.status_code, 422, rejected_context.text)
        self.assertEqual(
            rejected_deck_context.status_code,
            422,
            rejected_deck_context.text,
        )
        self.assertEqual(gateway.calls, [
            ("snapshot", {"actor_id": ACTOR_ID}),
            ("events", ({"actor_id": ACTOR_ID}, "turn-1:2")),
            ("send", ({"actor_id": ACTOR_ID}, "继续", "key-1")),
            (
                "tool-confirm",
                ({"actor_id": ACTOR_ID}, "tool-ask", True, "继续", {"q1": "继续"}),
            ),
        ])


async def _collect(generator):
    return [frame async for frame in generator]


async def _next_tool_confirmation(generator):
    while True:
        try:
            frame = await anext(generator)
        except StopAsyncIteration as exc:
            raise AssertionError("tool confirmation was not projected") from exc
        if "event: tool_confirmation_requested" in frame:
            return frame


async def _act_while_tool_confirmation_pending(
    service,
    action,
    *,
    run_id: str = RUN_ID,
    thread_id: str = THREAD_ID,
    actor_id: str = ACTOR_ID,
):
    stream = service.events(
        thread_id=thread_id,
        run_id=run_id,
        actor_id=actor_id,
    )
    await _next_tool_confirmation(stream)
    try:
        return action()
    finally:
        await stream.aclose()


def _pending_dispatch():
    from services.story_workspace.dream_agent_message_service import StoryWorkspaceDreamAgentPendingDispatch

    return StoryWorkspaceDreamAgentPendingDispatch(
        thread_id=THREAD_ID,
        actor_id=ACTOR_ID,
        context=_context(),
        message_id="pending-message",
        parts=[{"type": "text", "text": "继续"}],
        metadata={"dispatch_claim_id": "claim-1"},
    )
