"""Deck aggregate draft, explicit commit, immutable history, and CAS tests.

[Input] Isolated SQLite compatibility fixture plus production service/DTOs.
[Output] Prove v1/vN iteration, preview-without-write, and conflict preservation.
[Pos] Provider-free Deck content-version application contract tests.
[Sync] 2026-08-16: add CozeLoop-inspired draft -> preview -> commit coverage.
"""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from backend.schema import legacy_main_sqlite
from models.deck_version import DeckVersionCommitRequest, DeckVersionMutationRequest
from services.deck.content_versioning import (
    DeckContentVersionService,
    DeckVersionConflict,
    DeckVersionNoChanges,
    advance_deck_draft_revision,
)


DECK_ID = "deck-content-version-test"


class DeckContentVersionFixture:
    def __init__(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = sqlite3.connect(Path(self.temp_dir.name) / "versions.db")
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        legacy_main_sqlite.create_tables(self.db)
        self.db.execute("ALTER TABLE decks ADD COLUMN draft_revision INTEGER NOT NULL DEFAULT 1")
        self.db.execute("ALTER TABLE decks ADD COLUMN latest_version INTEGER NOT NULL DEFAULT 0")
        self.db.execute("ALTER TABLE decks ADD COLUMN published_draft_revision INTEGER NOT NULL DEFAULT 0")
        self.db.execute(
            """
            CREATE TABLE deck_versions (
              id TEXT PRIMARY KEY,
              deck_id TEXT NOT NULL,
              version INTEGER NOT NULL,
              base_version INTEGER,
              source_draft_revision INTEGER NOT NULL,
              description TEXT,
              snapshot_json TEXT NOT NULL,
              content_hash TEXT NOT NULL,
              created_by INTEGER NOT NULL,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              UNIQUE(deck_id, version)
            )
            """
        )
        self.db.execute(
            """
            CREATE TABLE deck_claude_plugin_refs (
              deck_id TEXT NOT NULL,
              plugin_installation_id TEXT NOT NULL,
              package_spec TEXT NOT NULL,
              resolved_version TEXT NOT NULL,
              artifact_digest TEXT NOT NULL,
              enabled INTEGER NOT NULL DEFAULT 1,
              order_index INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY(deck_id, plugin_installation_id)
            )
            """
        )
        self.db.execute(
            "INSERT INTO users (id, email, password_hash) VALUES (1, 'owner@example.com', 'hash')"
        )
        self.db.execute(
            """
            INSERT INTO decks (id, name, description, icon, color, owner_id, enabled, order_index)
            VALUES (?, 'Draft Deck', 'Initial draft', 'brain', 'blue', 1, 1, 1)
            """,
            (DECK_ID,),
        )
        self.db.execute(
            """
            INSERT INTO voices (id, deck_id, name, system_prompt, icon, color, owner_id, enabled, order_index)
            VALUES ('voice-1', ?, 'Writer', 'Write clearly.', 'brain', 'blue', 1, 1, 1)
            """,
            (DECK_ID,),
        )
        self.db.commit()
        self.service = DeckContentVersionService(self.db)

    def close(self) -> None:
        self.db.close()
        self.temp_dir.cleanup()

    def state_request(self) -> DeckVersionMutationRequest:
        state = self.service.get_state(DECK_ID, 1)
        return DeckVersionMutationRequest(
            expected_draft_revision=state.draft_revision,
            expected_base_version=state.latest_version,
        )

    def change_name(self, value: str) -> None:
        self.db.execute("BEGIN")
        self.db.execute("UPDATE decks SET name = ? WHERE id = ?", (value, DECK_ID))
        advance_deck_draft_revision(self.db, DECK_ID)
        self.db.commit()


@patch("services.deck.content_versioning.content_version_capability_available", return_value=True)
class DeckContentVersionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = DeckContentVersionFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_preview_does_not_write_and_first_commit_creates_v1(self, _capability) -> None:
        request = self.fixture.state_request()
        preview = self.fixture.service.preview(DECK_ID, 1, request)
        self.assertEqual(preview.target_version, 1)
        self.assertTrue({change.scope for change in preview.changes} >= {"deck", "agent_type", "agents"})
        count = self.fixture.db.execute("SELECT COUNT(*) FROM deck_versions").fetchone()[0]
        self.assertEqual(count, 0)

        committed = self.fixture.service.commit(
            DECK_ID,
            1,
            DeckVersionCommitRequest(**request.model_dump(), description="Initial Deck"),
        )
        self.assertEqual(committed.version.version, 1)
        self.assertFalse(committed.state.dirty)
        snapshot = json.loads(
            self.fixture.db.execute("SELECT snapshot_json FROM deck_versions").fetchone()[0]
        )
        self.assertEqual(snapshot["deck"]["name"], "Draft Deck")

    def test_effective_form_change_creates_v2_and_history_is_descending(self, _capability) -> None:
        first = self.fixture.state_request()
        self.fixture.service.commit(DECK_ID, 1, DeckVersionCommitRequest(**first.model_dump()))
        self.fixture.change_name("Draft Deck updated")
        next_request = self.fixture.state_request()
        preview = self.fixture.service.preview(DECK_ID, 1, next_request)
        self.assertEqual(preview.target_version, 2)
        self.assertEqual(preview.changes[0].scope, "deck")
        committed = self.fixture.service.commit(
            DECK_ID,
            1,
            DeckVersionCommitRequest(**next_request.model_dump(), description="Rename"),
        )
        self.assertEqual(committed.version.base_version, 1)
        history = self.fixture.service.list_versions(DECK_ID, 1)
        self.assertEqual([item.version for item in history.versions], [2, 1])

    def test_stale_confirmation_conflicts_without_overwriting_draft_or_v1(self, _capability) -> None:
        stale = self.fixture.state_request()
        self.fixture.change_name("Concurrent form update")
        with self.assertRaises(DeckVersionConflict):
            self.fixture.service.commit(
                DECK_ID,
                1,
                DeckVersionCommitRequest(**stale.model_dump()),
            )
        deck = self.fixture.db.execute(
            "SELECT name, draft_revision, latest_version FROM decks WHERE id = ?", (DECK_ID,)
        ).fetchone()
        self.assertEqual((deck["name"], deck["draft_revision"], deck["latest_version"]), ("Concurrent form update", 2, 0))
        self.assertEqual(self.fixture.db.execute("SELECT COUNT(*) FROM deck_versions").fetchone()[0], 0)

    def test_clean_committed_draft_cannot_generate_duplicate_version(self, _capability) -> None:
        request = self.fixture.state_request()
        self.fixture.service.commit(DECK_ID, 1, DeckVersionCommitRequest(**request.model_dump()))
        clean = self.fixture.state_request()
        with self.assertRaises(DeckVersionNoChanges):
            self.fixture.service.preview(DECK_ID, 1, clean)


if __name__ == "__main__":
    unittest.main()
