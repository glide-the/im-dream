# [Input] PostgreSQL database adapter mocked at the chat_thread Agent-selection boundary.
# [Output] Verify same-Deck current-Agent selection uses actor/deck/expected-voice CAS and closes resources.
# [Pos] Chat thread Agent-selection persistence contract in backend/tests.
# [Sync] 2026-08-17: initial same-Deck Agent CAS coverage.

from __future__ import annotations

import unittest
import unittest.mock
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database


class ChatThreadAgentSelectionTests(unittest.TestCase):
    def test_select_current_agent_is_scoped_by_actor_deck_and_expected_voice(self):
        db = unittest.mock.Mock()
        cursor = unittest.mock.Mock(rowcount=1)
        db.execute.return_value = cursor

        with unittest.mock.patch.object(database, "get_db", return_value=db):
            selected = database.select_chat_thread_voice(
                "thread-1",
                7,
                "deck-1",
                "voice-2",
                "voice-1",
            )

        self.assertTrue(selected)
        sql, params = db.execute.call_args.args
        self.assertIn("user_id = %s", sql)
        self.assertIn("deck_id = %s", sql)
        self.assertIn("voice_id IS NOT DISTINCT FROM %s", sql)
        self.assertEqual(
            params,
            ("voice-2", "thread-1", 7, "deck-1", "voice-1"),
        )
        db.commit.assert_called_once_with()
        db.close.assert_called_once_with()

    def test_stale_expected_agent_loses_without_fallback_write(self):
        db = unittest.mock.Mock()
        db.execute.return_value = unittest.mock.Mock(rowcount=0)

        with unittest.mock.patch.object(database, "get_db", return_value=db):
            selected = database.select_chat_thread_voice(
                "thread-1",
                7,
                "deck-1",
                "voice-3",
                "voice-1",
            )

        self.assertFalse(selected)
        db.execute.assert_called_once()
        db.commit.assert_called_once_with()
        db.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
