"""Red/green contract tests for the run-bound Dream Agent adapter."""

from __future__ import annotations

import asyncio
import json
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
    STORY_WORKSPACE_DREAM_AGENT_QUESTION_KEY_MAX,
    STORY_WORKSPACE_DREAM_AGENT_QUESTION_OPTION_MAX,
    STORY_WORKSPACE_DREAM_AGENT_QUESTION_PLACEHOLDER_MAX,
    StoryWorkspaceDreamAgentMessageCommand,
    StoryWorkspaceDreamAgentToolConfirmationCommand,
    StoryWorkspaceDreamRunContext,
)
from services.story_workspace.dream_agent_message_service import (  # noqa: E402
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

    def session_snapshot(self, _thread_id: str):
        return {"lifecycle": "running", "current_turn_id": "turn-1"} if self.running else None

    async def subscribe_stream(self, _thread_id: str):
        for frame in self.frames:
            yield frame

    def is_expected_story_workspace_dream_turn(self, *_args) -> bool:
        return True

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
        self.assertIn("id: turn-1:2", output)
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
                    "question": "Run command: rm -rf workspace",
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
            '"id":"style","question":"选择叙事风格","placeholder":"请选择",'
            '"options":[{"label":"温暖","value":"warm"}]}]}}\n\n',
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
        self.assertIn("event: tool_confirmation_requested", safe_output)
        self.assertIn("选择叙事风格", safe_output)

    def test_ask_user_public_question_lengths_and_keys_are_one_contract(self) -> None:
        question_key = "问" * STORY_WORKSPACE_DREAM_AGENT_QUESTION_KEY_MAX
        command = StoryWorkspaceDreamAgentToolConfirmationCommand(
            toolCallId="tool-length",
            approved=True,
            answers={question_key: "普通回答"},
        )
        self.assertIn(question_key, command.answers or {})

        safe_factory = _ToolConfirmationFactory()
        safe_factory.frames = [
            "data: " + json.dumps({
                "type": "tool-approval-request",
                "toolCallId": "tool-max-lengths",
                "toolName": "AskUserQuestion",
                "input": {"questions": [{
                    "id": "i" * STORY_WORKSPACE_DREAM_AGENT_QUESTION_ID_MAX,
                    "question": question_key,
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
                "input": {"questions": [{"question": question_key + "超"}]},
            }, ensure_ascii=False) + "\n\n",
            "data: " + json.dumps({
                "type": "tool-approval-request",
                "toolCallId": "tool-id-too-long",
                "toolName": "AskUserQuestion",
                "input": {"questions": [{
                    "id": "i" * (STORY_WORKSPACE_DREAM_AGENT_QUESTION_ID_MAX + 1),
                    "question": "普通问题",
                }]},
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
            "data: " + json.dumps({
                "type": "tool-approval-request",
                "toolCallId": "tool-duplicate",
                "toolName": "AskUserQuestion",
                "input": {"questions": [
                    {"id": "one", "question": "同一个问题"},
                    {"id": "two", "question": "同一个问题"},
                ]},
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

    def test_confirm_tool_requires_same_active_trusted_dream_turn(self) -> None:
        factory = _ToolConfirmationFactory()
        factory.frames = [
            'data: {"type":"tool-approval-request","toolCallId":"tool-ask",'
            '"toolName":"AskUserQuestion","input":{"questions":[{'
            '"id":"q1","question":"继续吗？","options":["继续","停止"]}]}}\n\n',
        ]
        service = StoryWorkspaceDreamAgentMessageService(
            self.db,
            thread_factory=factory,
        )
        asyncio.run(_collect(service.events(
            thread_id=THREAD_ID,
            run_id=RUN_ID,
            actor_id=ACTOR_ID,
        )))
        command = StoryWorkspaceDreamAgentToolConfirmationCommand(
            toolCallId="tool-ask",
            approved=True,
            reason="用户已选择",
            answers={"继续吗？": "继续"},
        )
        accepted = service.confirm_tool(
            run_id=RUN_ID,
            thread_id=THREAD_ID,
            actor_id=ACTOR_ID,
            command=command,
        )
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
            asyncio.run(_collect(service.events(
                thread_id=THREAD_ID,
                run_id=RUN_ID,
                actor_id=ACTOR_ID,
            )))
            return service, factory

        valid_service, valid_factory = pending_service()
        accepted = valid_service.confirm_tool(
            run_id=RUN_ID,
            thread_id=THREAD_ID,
            actor_id=ACTOR_ID,
            command=StoryWorkspaceDreamAgentToolConfirmationCommand(
                toolCallId="tool-current",
                approved=True,
                answers={
                    "补充说明": "继续完善人物动机",
                    "选择风格": "温暖",
                    "确认继续": True,
                    "选择元素": ["雨", "灯"],
                },
            ),
        )
        self.assertTrue(accepted.resolved)
        self.assertEqual(valid_factory.confirmations[-1][0], "confirm")

        invalid_answers = (
            {"未知问题": "继续"},
            {"补充说明": "公开说明", "选择风格": "秘密风格", "确认继续": True, "选择元素": ["雨"]},
            {"补充说明": "公开说明", "选择风格": "温暖", "确认继续": True, "选择元素": ["雨", "不存在"]},
            {"补充说明": "公开说明", "选择风格": "温暖", "确认继续": "true", "选择元素": ["雨"]},
            {"补充说明": "", "选择风格": "温暖", "确认继续": True, "选择元素": ["雨"]},
        )
        for answers in invalid_answers:
            with self.subTest(answers=answers):
                service, factory = pending_service()
                with self.assertRaisesRegex(
                    StoryWorkspaceDreamAgentMessageError,
                    "DREAM_AGENT_TOOL_CONFIRMATION_INVALID",
                ):
                    service.confirm_tool(
                        run_id=RUN_ID,
                        thread_id=THREAD_ID,
                        actor_id=ACTOR_ID,
                        command=StoryWorkspaceDreamAgentToolConfirmationCommand(
                            toolCallId="tool-current",
                            approved=True,
                            answers=answers,
                        ),
                    )
                self.assertFalse(any(item[0] == "confirm" for item in factory.confirmations))

        wrong_tool_service, wrong_tool_factory = pending_service()
        with self.assertRaisesRegex(
            StoryWorkspaceDreamAgentMessageError,
            "DREAM_AGENT_TOOL_CONFIRMATION_NOT_READY",
        ):
            wrong_tool_service.confirm_tool(
                run_id=RUN_ID,
                thread_id=THREAD_ID,
                actor_id=ACTOR_ID,
                command=StoryWorkspaceDreamAgentToolConfirmationCommand(
                    toolCallId="tool-other",
                    approved=True,
                ),
            )
        self.assertFalse(
            any(item[0] == "confirm" for item in wrong_tool_factory.confirmations)
        )

        reject_service, reject_factory = pending_service()
        with self.assertRaisesRegex(
            StoryWorkspaceDreamAgentMessageError,
            "DREAM_AGENT_TOOL_CONFIRMATION_INVALID",
        ):
            reject_service.confirm_tool(
                run_id=RUN_ID,
                thread_id=THREAD_ID,
                actor_id=ACTOR_ID,
                command=StoryWorkspaceDreamAgentToolConfirmationCommand(
                    toolCallId="tool-current",
                    approved=False,
                    answers={"选择风格": "温暖"},
                ),
            )
        self.assertFalse(any(item[0] == "confirm" for item in reject_factory.confirmations))

    def test_tool_confirmation_contract_rejects_untrusted_context_and_oversized_answers(self) -> None:
        from pydantic import ValidationError

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
        try:
            asyncio.run(_collect(StoryWorkspaceDreamAgentMessageService(
                event_db,
                thread_factory=factory,
            ).events(
                thread_id=THREAD_ID,
                run_id=RUN_ID,
                actor_id=ACTOR_ID,
            )))
        finally:
            event_db.close()

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
            accepted = asyncio.run(gateway.confirm_dream_agent_tool(
                RUN_ID,
                command,
                actor={"actor_id": ACTOR_ID},
            ))

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
