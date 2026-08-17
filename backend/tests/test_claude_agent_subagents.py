# [Input] Consume claude_agent.subagent_projection filesystem projection.
# [Output] Verify completed/running/cancelled/failed classification, recovery,
#          safe readonly messages, stable ordering, redaction, and empty state.
# [Pos] Focused unit test node for the Chat subagent sidebar API projection.
# [Sync] 2026-08-04: initial subagent transcript projection coverage.

from __future__ import annotations

import json
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

projection_path = ROOT / "claude_agent" / "subagent_projection.py"
projection_spec = importlib.util.spec_from_file_location(
    "claude_agent_subagent_projection_for_test", projection_path
)
if projection_spec is None or projection_spec.loader is None:
    raise RuntimeError(f"Unable to load {projection_path}")
projection_module = importlib.util.module_from_spec(projection_spec)
projection_spec.loader.exec_module(projection_module)
build_thread_subagents_payload = projection_module.build_thread_subagents_payload


def _record(timestamp: str, role: str, content: list[dict]) -> dict:
    return {
        "timestamp": timestamp,
        "message": {"role": role, "content": content},
    }


class TestSubagentProjection(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        self.thread_id = "thread-subagents"
        self.subagents_dir = (
            self.root
            / self.thread_id
            / ".claude-home"
            / "projects"
            / "session-a"
            / "subagents"
        )
        self.subagents_dir.mkdir(parents=True)

    def _write_agent(
        self,
        agent_id: str,
        records: list[dict],
        *,
        description: str | None = None,
    ) -> None:
        stem = f"agent-{agent_id}"
        meta = {
            "agentType": "quality-reviewer",
            "description": description or f"Task {agent_id}",
            "toolUseId": f"tool-{agent_id}",
            "spawnDepth": 1,
            "prompt": "must never reach the browser",
        }
        (self.subagents_dir / f"{stem}.meta.json").write_text(
            json.dumps(meta), encoding="utf-8"
        )
        (self.subagents_dir / f"{stem}.jsonl").write_text(
            "\n".join(json.dumps(item) for item in records) + "\n",
            encoding="utf-8",
        )

    def test_projects_status_counts_and_safe_shape(self) -> None:
        self._write_agent(
            "completed",
            [
                _record("2026-08-04T09:00:00Z", "user", [{"type": "text", "text": "review"}]),
                _record(
                    "2026-08-04T09:00:10Z",
                    "assistant",
                    [{"type": "text", "text": "PASS. No new regressions."}],
                ),
            ],
            description="Task3 quality review",
        )
        self._write_agent(
            "running",
            [
                _record("2026-08-04T10:00:00Z", "user", [{"type": "text", "text": "work"}]),
                _record(
                    "2026-08-04T10:00:04Z",
                    "assistant",
                    [{"type": "tool_use", "id": "read-secret", "name": "Read", "input": {"path": "/secret"}}],
                ),
            ],
        )
        self._write_agent(
            "cancelled",
            [
                _record("2026-08-04T11:00:00Z", "assistant", [{"type": "text", "text": "Drafting"}]),
                _record(
                    "2026-08-04T11:00:03Z",
                    "user",
                    [{"type": "text", "text": "[Request interrupted by user]"}],
                ),
            ],
        )
        self._write_agent(
            "failed",
            [
                _record("2026-08-04T12:00:00Z", "user", [{"type": "text", "text": "run"}]),
                _record(
                    "2026-08-04T12:00:01Z",
                    "user",
                    [{"type": "tool_result", "is_error": True, "content": "permission denied"}],
                ),
            ],
        )

        payload = build_thread_subagents_payload(self.thread_id, self.root)

        self.assertTrue(payload["exists"])
        self.assertEqual(
            payload["counts"],
            {"running": 1, "completed": 1, "ended": 2, "total": 4},
        )
        by_id = {task["agent_id"]: task for task in payload["tasks"]}
        self.assertEqual(by_id["completed"]["status"], "completed")
        self.assertEqual(by_id["completed"]["summary"], "PASS. No new regressions.")
        self.assertEqual(by_id["completed"]["duration_ms"], 10_000)
        self.assertEqual(by_id["running"]["status"], "running")
        self.assertIsNone(by_id["running"]["finished_at"])
        self.assertEqual(by_id["running"]["activity"][0]["tool_name"], "Read")
        self.assertNotIn("input", by_id["running"]["activity"][0])
        self.assertEqual(by_id["cancelled"]["status"], "cancelled")
        self.assertEqual(by_id["failed"]["status"], "failed")
        self.assertEqual(by_id["failed"]["error"], "permission denied")
        self.assertNotIn("prompt", by_id["completed"])
        self.assertNotIn("path", by_id["running"])

    def test_activity_excludes_prompts_thinking_and_tool_payloads(self) -> None:
        self._write_agent(
            "details",
            [
                _record("2026-08-04T13:00:00Z", "user", [{"type": "text", "text": "private prompt"}]),
                _record(
                    "2026-08-04T13:00:01Z",
                    "assistant",
                    [
                        {"type": "thinking", "thinking": "private reasoning"},
                        {"type": "tool_use", "id": "tool-1", "name": "Grep", "input": {"pattern": "secret"}},
                    ],
                ),
                _record(
                    "2026-08-04T13:00:02Z",
                    "user",
                    [{"type": "tool_result", "tool_use_id": "tool-1", "content": "/private/path"}],
                ),
                _record(
                    "2026-08-04T13:00:03Z",
                    "assistant",
                    [{"type": "text", "text": "Review complete."}],
                ),
            ],
        )

        activity = build_thread_subagents_payload(self.thread_id, self.root)["tasks"][0]["activity"]
        serialized = json.dumps(activity)
        self.assertEqual([item["status"] for item in activity], ["started", "completed", "completed"])
        self.assertNotIn("private prompt", serialized)
        self.assertNotIn("private reasoning", serialized)
        self.assertNotIn("secret", serialized)
        self.assertNotIn("/private/path", serialized)
        self.assertIn("Review complete.", serialized)

    def test_inactive_thread_settles_unclosed_transcript_without_rewriting_it(self) -> None:
        self._write_agent(
            "orphaned",
            [
                _record("2026-08-04T10:00:00Z", "user", [{"type": "text", "text": "work"}]),
                _record(
                    "2026-08-04T10:00:04Z",
                    "assistant",
                    [{"type": "tool_use", "id": "read-1", "name": "Read", "input": {"path": "/private"}}],
                ),
            ],
        )

        inactive = build_thread_subagents_payload(
            self.thread_id,
            self.root,
            runtime_running=False,
        )
        task = inactive["tasks"][0]
        self.assertEqual(task["status"], "cancelled")
        self.assertIsNone(task["finished_at"])
        self.assertEqual(task["messages"][-1]["status"], "cancelled")
        self.assertEqual(
            inactive["counts"],
            {"running": 0, "completed": 0, "ended": 1, "total": 1},
        )

        live = build_thread_subagents_payload(
            self.thread_id,
            self.root,
            runtime_running=True,
        )
        self.assertEqual(live["tasks"][0]["status"], "running")
        self.assertEqual(live["counts"]["running"], 1)

    def test_messages_project_dispatch_tools_final_and_terminal_status(self) -> None:
        self._write_agent(
            "conversation",
            [
                _record("2026-08-04T13:00:00Z", "user", [{"type": "text", "text": "private prompt"}]),
                _record(
                    "2026-08-04T13:00:01Z",
                    "assistant",
                    [
                        {"type": "text", "text": "I will inspect the code."},
                        {
                            "type": "tool_use",
                            "id": "tool-1",
                            "name": "Read",
                            "input": {"file_path": "frontend/src/App.tsx", "api_key": "must-hide"},
                        },
                    ],
                ),
                _record(
                    "2026-08-04T13:00:02Z",
                    "user",
                    [{"type": "tool_result", "tool_use_id": "tool-1", "content": "source excerpt"}],
                ),
                _record(
                    "2026-08-04T13:00:03Z",
                    "assistant",
                    [{"type": "text", "text": "## Done\n\n- Tests passed"}],
                ),
            ],
        )

        task = build_thread_subagents_payload(self.thread_id, self.root)["tasks"][0]
        messages = task["messages"]

        self.assertEqual(messages[0]["kind"], "task")
        self.assertEqual(messages[0]["text"], "must never reach the browser")
        self.assertEqual([item["sequence"] for item in messages], list(range(1, len(messages) + 1)))
        tool_call = next(item for item in messages if item["kind"] == "tool_call")
        tool_result = next(item for item in messages if item["kind"] == "tool_result")
        self.assertEqual(tool_call["tool_call_id"], tool_result["tool_call_id"])
        self.assertIn("[redacted]", tool_call["input"])
        self.assertNotIn("must-hide", tool_call["input"])
        self.assertEqual(sum(item["kind"] == "final" for item in messages), 1)
        self.assertEqual(messages[-1]["kind"], "status")
        self.assertEqual(messages[-1]["status"], "completed")
        self.assertEqual(task["message_count"], len(messages))
        self.assertEqual(task["projection_version"], 2)

    def test_cancelled_message_timeline_keeps_prior_output_and_terminal_state(self) -> None:
        self._write_agent(
            "cancelled-timeline",
            [
                _record("2026-08-04T14:00:00Z", "assistant", [{"type": "text", "text": "Partial output"}]),
                _record(
                    "2026-08-04T14:00:01Z",
                    "user",
                    [{"type": "text", "text": "[Request interrupted by user]"}],
                ),
            ],
        )

        task = build_thread_subagents_payload(self.thread_id, self.root)["tasks"][0]
        self.assertEqual(task["status"], "cancelled")
        self.assertTrue(any(item["text"] == "Partial output" for item in task["messages"]))
        self.assertEqual(task["messages"][-1]["status"], "cancelled")

    def test_intermediate_error_does_not_override_successful_final_answer(self) -> None:
        self._write_agent(
            "recovered",
            [
                _record(
                    "2026-08-04T12:00:00Z",
                    "user",
                    [{"type": "tool_result", "is_error": True, "content": "first attempt failed"}],
                ),
                _record(
                    "2026-08-04T12:00:05Z",
                    "assistant",
                    [{"type": "text", "text": "Recovered and completed."}],
                ),
            ],
        )

        task = build_thread_subagents_payload(self.thread_id, self.root)["tasks"][0]
        self.assertEqual(task["status"], "completed")
        self.assertIsNone(task["error"])

    def test_final_summary_preserves_markdown_block_structure(self) -> None:
        self._write_agent(
            "markdown",
            [
                _record(
                    "2026-08-04T12:00:00Z",
                    "assistant",
                    [
                        {
                            "type": "text",
                            "text": "## Review\n\n- PASS\n- No regressions\n\n```ts\nconst ok = true;\n```",
                        }
                    ],
                ),
            ],
        )

        summary = build_thread_subagents_payload(self.thread_id, self.root)["tasks"][0]["summary"]
        self.assertEqual(
            summary,
            "## Review\n\n- PASS\n- No regressions\n\n```ts\nconst ok = true;\n```",
        )

    def test_missing_workspace_returns_empty_payload(self) -> None:
        payload = build_thread_subagents_payload("missing-thread", self.root)
        self.assertFalse(payload["exists"])
        self.assertEqual(payload["tasks"], [])
        self.assertEqual(payload["counts"]["total"], 0)


if __name__ == "__main__":
    unittest.main()
