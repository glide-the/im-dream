# [Input] Immutable chat message writes, including optional derived final projection fields.
# [Output] Verify message-id CAS and strict projection validation without PostgreSQL.
# [Pos] Provider-free chat_message persistence contract tests.
# [Sync] 2026-09-02: extend the insert fake and tests for assistant final projection columns.

from __future__ import annotations

import json
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database


class _Cursor:
    def __init__(self, row=None) -> None:
        self._row = row

    def fetchone(self):
        return self._row


class _SharedDatabase:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.rows: dict[str, dict[str, object]] = {}
        self.statements: list[str] = []
        self.touches = 0
        self.commits = 0


class _Connection:
    def __init__(self, shared: _SharedDatabase) -> None:
        self.shared = shared

    def execute(self, statement, params=()):
        normalized = " ".join(str(statement).split())
        with self.shared.lock:
            self.shared.statements.append(normalized)
            if normalized.startswith("INSERT INTO chat_message"):
                (
                    message_id,
                    thread_id,
                    role,
                    parts,
                    metadata,
                    history_final_text,
                    history_process_available,
                    history_projection_version,
                ) = params
                if message_id in self.shared.rows:
                    return _Cursor()
                self.shared.rows[message_id] = {
                    "thread_id": thread_id,
                    "role": role,
                    "parts": parts,
                    "metadata": metadata,
                    "history_final_text": history_final_text,
                    "history_process_available": history_process_available,
                    "history_projection_version": history_projection_version,
                }
                return _Cursor({"id": message_id})
            if normalized.startswith(
                "SELECT thread_id, role, parts, metadata FROM chat_message"
            ):
                return _Cursor(self.shared.rows.get(params[0]))
            if normalized.startswith("UPDATE chat_thread SET updated_at"):
                self.shared.touches += 1
                return _Cursor()
        raise AssertionError(normalized)

    def commit(self) -> None:
        with self.shared.lock:
            self.shared.commits += 1

    def close(self) -> None:
        return None


class ChatMessageIdentityCASTest(unittest.TestCase):
    def setUp(self) -> None:
        self.shared = _SharedDatabase()
        self.get_db = patch.object(
            database,
            "get_db",
            side_effect=lambda: _Connection(self.shared),
        )
        self.get_db.start()
        self.addCleanup(self.get_db.stop)

    def save(
        self,
        *,
        thread_id: str = "thread-1",
        role: str = "user",
        parts=None,
        metadata=None,
        message_id: str = "message-1",
        **kwargs,
    ) -> str:
        return database.save_chat_message(
            thread_id,
            role,
            parts if parts is not None else [{"type": "text", "text": "hello"}],
            message_id=message_id,
            metadata=metadata,
            **kwargs,
        )

    def test_insert_then_json_semantic_exact_replay_is_read_only(self) -> None:
        self.save(
            parts=[{"text": "你好", "type": "text"}],
            metadata={"nested": {"b": 2, "a": 1}},
        )
        replayed = database.save_chat_message(
            "thread-1",
            "user",
            [],
            message_id="message-1",
            parts_json='[{"type":"text", "text":"你好"}]',
            metadata_json='{"nested": {"a": 1, "b": 2}}',
        )

        self.assertEqual(replayed, "message-1")
        self.assertEqual(len(self.shared.rows), 1)
        self.assertEqual(self.shared.touches, 1)
        self.assertEqual(self.shared.commits, 2)
        insert_sql = next(
            sql for sql in self.shared.statements if sql.startswith("INSERT")
        )
        self.assertIn("ON CONFLICT (id) DO NOTHING RETURNING id", insert_sql)
        self.assertNotIn("DO UPDATE", insert_sql)

    def test_same_id_cannot_change_any_immutable_identity_field(self) -> None:
        baseline_parts = [{"type": "text", "text": "hello"}]
        baseline_metadata = {"source": "public"}
        mutations = (
            {"thread_id": "thread-2"},
            {"role": "assistant"},
            {"parts": [{"type": "text", "text": "changed"}]},
            {"metadata": {"source": "server"}},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.shared.rows.clear()
                self.shared.touches = 0
                self.save(parts=baseline_parts, metadata=baseline_metadata)
                values = {
                    "thread_id": "thread-1",
                    "role": "user",
                    "parts": baseline_parts,
                    "metadata": baseline_metadata,
                    **mutation,
                }
                with self.assertRaises(
                    database.ChatMessageIdentityConflict
                ) as raised:
                    self.save(**values)
                self.assertEqual(raised.exception.code, "CHAT_MESSAGE_IDENTITY_CONFLICT")
                row = self.shared.rows["message-1"]
                self.assertEqual(row["thread_id"], "thread-1")
                self.assertEqual(row["role"], "user")
                self.assertEqual(json.loads(str(row["parts"])), baseline_parts)
                self.assertEqual(json.loads(str(row["metadata"])), baseline_metadata)
                self.assertEqual(self.shared.touches, 1)

    def test_completed_assistant_projection_must_match_canonical_final(self) -> None:
        parts = [
            {"type": "reasoning", "text": "work"},
            {"type": "text", "text": "answer"},
        ]
        metadata = {
            "turnId": "turn-1",
            "turnStatus": "completed",
            "finalPartIndex": 1,
        }
        self.save(
            role="assistant",
            parts=parts,
            metadata=metadata,
            history_final_text="answer",
            history_process_available=True,
            history_projection_version=1,
        )
        row = self.shared.rows["message-1"]
        self.assertEqual(row["history_final_text"], "answer")
        self.assertTrue(row["history_process_available"])
        self.assertEqual(row["history_projection_version"], 1)

        with self.assertRaisesRegex(ValueError, "does not match"):
            self.save(
                message_id="message-2",
                role="assistant",
                parts=parts,
                metadata=metadata,
                history_final_text="different",
                history_process_available=True,
                history_projection_version=1,
            )

    def test_partial_projection_fields_fail_before_database_write(self) -> None:
        with self.assertRaisesRegex(ValueError, "incomplete"):
            self.save(history_final_text="answer")
        self.assertEqual(self.shared.statements, [])

    def test_concurrent_different_payloads_have_one_winner_without_reparent(self) -> None:
        barrier = threading.Barrier(2)
        outcomes: list[tuple[str, str]] = []
        outcome_lock = threading.Lock()

        def write(thread_id: str, text: str) -> None:
            barrier.wait(timeout=2)
            try:
                self.save(
                    thread_id=thread_id,
                    parts=[{"type": "text", "text": text}],
                )
                outcome = ("ok", thread_id)
            except database.ChatMessageIdentityConflict:
                outcome = ("conflict", thread_id)
            with outcome_lock:
                outcomes.append(outcome)

        threads = (
            threading.Thread(target=write, args=("thread-1", "one")),
            threading.Thread(target=write, args=("thread-2", "two")),
        )
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=2)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(sorted(status for status, _ in outcomes), ["conflict", "ok"])
        winner = next(thread_id for status, thread_id in outcomes if status == "ok")
        self.assertEqual(self.shared.rows["message-1"]["thread_id"], winner)
        self.assertEqual(self.shared.touches, 1)


if __name__ == "__main__":
    unittest.main()
