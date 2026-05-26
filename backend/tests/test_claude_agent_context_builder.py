# [Input] Consume ClaudeAgentContextBuilder from backend/claude_agent/context_builder.py.
#         Mock database.list_sessions to provide writing session fixtures.
# [Output] Verify system_prompt assembly: header, recent sessions block, runtime context,
#          session count cap, empty-sessions fallback, and DB error graceful degradation.
# [Pos] test node in backend/tests
# [Sync] 2026-05-22: fresh implementation for Ink & Memory writing-session context.
#                    (Pawkeyland's context_builder tested pet persona / sticker / necklace —
#                     all removed; replaced with writing-session-based context.)

"""Unit tests for ClaudeAgentContextBuilder (Ink & Memory writing context)."""
from __future__ import annotations

import asyncio
import sys
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # backend/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tests._sdk_stubs  # noqa: F401 — stub claude_code_sdk before libs.claude_agent_kit

from claude_agent.context_builder import (
    ClaudeAgentContextBuilder,
    _NO_SESSIONS_TEXT,
    _SESSIONS_HEADER,
    _render_session_entry,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _fake_sessions(n: int = 3) -> list[dict]:
    return [
        {
            "id": f"s{i}",
            "name": f"Session {i}",
            "updated_at": f"2026-05-{10 + i:02d}T10:00:00",
            "first_line": f"Today I thought about {'loneliness' if i % 2 == 0 else 'joy'}.",
        }
        for i in range(1, n + 1)
    ]


# ---------------------------------------------------------------------------
# render_session_entry
# ---------------------------------------------------------------------------

class TestRenderSessionEntry(unittest.TestCase):
    def test_includes_date_from_updated_at(self):
        row = {"name": "Test", "updated_at": "2026-05-20T09:00:00", "first_line": "hello"}
        rendered = _render_session_entry(row)
        self.assertIn("2026-05-20", rendered)

    def test_includes_name_as_title(self):
        row = {"name": "My Journal", "updated_at": "2026-05-20", "first_line": "text"}
        rendered = _render_session_entry(row)
        self.assertIn("My Journal", rendered)

    def test_includes_first_line_as_excerpt(self):
        row = {"name": "X", "updated_at": "2026-05-20", "first_line": "I felt calm today."}
        rendered = _render_session_entry(row)
        self.assertIn("I felt calm today.", rendered)

    def test_empty_first_line_uses_placeholder(self):
        row = {"name": "X", "updated_at": "2026-05-20", "first_line": ""}
        rendered = _render_session_entry(row)
        self.assertIn("Empty entry", rendered)

    def test_missing_name_uses_untitled(self):
        row = {"name": None, "updated_at": "2026-05-20", "first_line": "text"}
        rendered = _render_session_entry(row)
        self.assertIn("Untitled", rendered)

    def test_falls_back_to_created_at_when_no_updated_at(self):
        row = {"name": "X", "created_at": "2026-04-01", "first_line": "text"}
        rendered = _render_session_entry(row)
        self.assertIn("2026-04-01", rendered)


# ---------------------------------------------------------------------------
# build_system_prompt
# ---------------------------------------------------------------------------

class TestBuildSystemPrompt(unittest.TestCase):
    def _builder(self, n: int = 5) -> ClaudeAgentContextBuilder:
        return ClaudeAgentContextBuilder(context_session_count=n)

    def _mock_db(self, sessions):
        """Return a patcher that makes database.list_sessions return sessions."""
        import database as _db  # noqa: PLC0415 — local import, backend path
        return unittest.mock.patch.object(_db, "list_sessions", return_value=sessions)

    def test_prompt_contains_sessions_header(self):
        with self._mock_db(_fake_sessions(2)):
            prompt = _run(self._builder().build_system_prompt("user_1"))
        self.assertIn(_SESSIONS_HEADER.strip(), prompt)

    def test_prompt_contains_session_names(self):
        sessions = _fake_sessions(2)
        with self._mock_db(sessions):
            prompt = _run(self._builder().build_system_prompt("user_1"))
        for s in sessions:
            self.assertIn(s["name"], prompt)

    def test_prompt_contains_writing_assistant_role(self):
        with self._mock_db([]):
            prompt = _run(self._builder().build_system_prompt("user_1"))
        self.assertIn("writing assistant", prompt.lower())

    def test_empty_sessions_uses_fallback(self):
        with self._mock_db([]):
            prompt = _run(self._builder().build_system_prompt("user_1"))
        self.assertIn(_NO_SESSIONS_TEXT.strip(), prompt)

    def test_respects_context_session_count_cap(self):
        sessions = _fake_sessions(10)
        with self._mock_db(sessions):
            prompt = _run(ClaudeAgentContextBuilder(context_session_count=3).build_system_prompt("u"))
        # Only first 3 session names should appear
        for s in sessions[:3]:
            self.assertIn(s["name"], prompt)
        for s in sessions[3:]:
            self.assertNotIn(s["name"], prompt)

    def test_db_error_gracefully_degrades_to_no_sessions(self):
        import database as _db
        with unittest.mock.patch.object(_db, "list_sessions", side_effect=RuntimeError("db down")):
            prompt = _run(self._builder().build_system_prompt("user_1"))
        self.assertIn(_NO_SESSIONS_TEXT.strip(), prompt)
        # Prompt should still be a valid string (not raise)
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 50)


# ---------------------------------------------------------------------------
# build_user_message
# ---------------------------------------------------------------------------

class TestBuildUserMessage(unittest.TestCase):
    def setUp(self):
        self.builder = ClaudeAgentContextBuilder()

    def _text_blocks(self, blocks):
        """Return the concatenated text of all text-type blocks."""
        return "\n".join(b["text"] for b in blocks if b.get("type") == "text")

    def _parts(self, text: str) -> list:
        """Wrap plain text as a minimal AI-SDK UIMessage parts list."""
        return [{"type": "text", "text": text}]

    def test_returns_list_of_content_blocks(self):
        blocks = self.builder.build_user_message(self._parts("Hello there"))
        self.assertIsInstance(blocks, list)
        self.assertTrue(all(isinstance(b, dict) for b in blocks))

    def test_includes_runtime_context_block(self):
        blocks = self.builder.build_user_message(self._parts("Hello there"))
        combined = self._text_blocks(blocks)
        self.assertIn("<runtime_context>", combined)
        self.assertIn("Date:", combined)

    def test_user_text_is_last_block(self):
        blocks = self.builder.build_user_message(self._parts("My message"))
        last = blocks[-1]
        self.assertEqual(last["type"], "text")
        self.assertEqual(last["text"], "My message")

    def test_runtime_context_block_before_user_text(self):
        blocks = self.builder.build_user_message(self._parts("My message"))
        # At least two text blocks: runtime_context and user text
        self.assertGreaterEqual(len(blocks), 2)
        # runtime_context block appears before the final user text block
        runtime_idx = next(
            i for i, b in enumerate(blocks) if "<runtime_context>" in b.get("text", "")
        )
        user_idx = len(blocks) - 1
        self.assertLess(runtime_idx, user_idx)

    def test_includes_local_timezone(self):
        blocks = self.builder.build_user_message(self._parts("x"), local_timezone="Asia/Shanghai")
        combined = self._text_blocks(blocks)
        self.assertIn("Asia/Shanghai", combined)

    def test_no_timezone_by_default(self):
        blocks = self.builder.build_user_message(self._parts("x"))
        combined = self._text_blocks(blocks)
        # No Timezone line when local_timezone is not provided
        self.assertNotIn("Timezone:", combined)

    def test_empty_message_still_has_runtime_block(self):
        blocks = self.builder.build_user_message(self._parts(""))
        combined = self._text_blocks(blocks)
        self.assertIn("<runtime_context>", combined)

    def test_none_message_parts_still_has_runtime_block(self):
        blocks = self.builder.build_user_message(None)
        combined = self._text_blocks(blocks)
        self.assertIn("<runtime_context>", combined)

    def test_include_runtime_context_false_skips_block(self):
        blocks = self.builder.build_user_message(
            self._parts("hello"), include_runtime_context=False
        )
        combined = self._text_blocks(blocks)
        self.assertNotIn("<runtime_context>", combined)
        self.assertIn("hello", combined)

    def test_image_attachment_becomes_image_block(self):
        from dataclasses import dataclass

        @dataclass
        class _Att:
            name: str
            media_type: str
            data: str

        att = _Att(name="photo.jpg", media_type="image/jpeg", data="abc123")
        blocks = self.builder.build_user_message(self._parts("see image"), attachments=[att])
        image_blocks = [b for b in blocks if b.get("type") == "image"]
        self.assertEqual(len(image_blocks), 1)
        self.assertEqual(image_blocks[0]["source"]["data"], "abc123")

    def test_unsupported_attachment_is_skipped(self):
        from dataclasses import dataclass

        @dataclass
        class _Att:
            name: str
            media_type: str
            data: str

        att = _Att(name="doc.pdf", media_type="application/pdf", data="abc")
        blocks = self.builder.build_user_message(self._parts("see doc"), attachments=[att])
        image_blocks = [b for b in blocks if b.get("type") == "image"]
        self.assertEqual(len(image_blocks), 0)

    def test_model_and_thread_id_in_runtime_context(self):
        blocks = self.builder.build_user_message(
            self._parts("hi"), model="claude-3-5-sonnet", thread_id="sess-abc", max_turns=50
        )
        combined = self._text_blocks(blocks)
        self.assertIn("claude-3-5-sonnet", combined)
        self.assertIn("sess-abc", combined)
        self.assertIn("50", combined)

    def test_resume_flag_in_runtime_context(self):
        blocks = self.builder.build_user_message(self._parts("hi"), resume=True)
        combined = self._text_blocks(blocks)
        self.assertIn("Resumed conversation: yes", combined)

    def test_multiple_text_parts_concatenated(self):
        parts = [{"type": "text", "text": "Hello"}, {"type": "text", "text": "world"}]
        blocks = self.builder.build_user_message(parts, include_runtime_context=False)
        last = blocks[-1]
        self.assertEqual(last["type"], "text")
        self.assertIn("Hello", last["text"])
        self.assertIn("world", last["text"])


if __name__ == "__main__":
    unittest.main()
