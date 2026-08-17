"""Opt-in disposable PostgreSQL Deck content-version contract.

[Input] Explicit loopback TEST_DATABASE_URL already migrated by Admin Drizzle.
[Output] Prove real JSONB/FOR UPDATE/RETURNING/CAS behavior without touching normal data.
[Pos] Isolated PostgreSQL integration test for Deck content commits.
[Sync] 2026-08-16: add real schema/service v1→v2 verification.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
from urllib.parse import urlparse

import psycopg
from psycopg.pq import TransactionStatus
from psycopg.rows import dict_row
import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from models.deck_version import DeckVersionCommitRequest, DeckVersionMutationRequest
import database
from services.deck.content_versioning import DeckContentVersionService, DeckVersionConflict


class Lease:
    def __init__(self, connection):
        self.connection = connection

    def __getattr__(self, name):
        return getattr(self.connection, name)

    @property
    def in_transaction(self) -> bool:
        return self.connection.info.transaction_status is not TransactionStatus.IDLE

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        if exc_type is None:
            self.connection.commit()
        else:
            self.connection.rollback()
        return False


def disposable_url() -> str:
    if os.environ.get("INK_RUN_DECK_VERSION_PG_TEST") != "1":
        pytest.skip("set INK_RUN_DECK_VERSION_PG_TEST=1 for the disposable PostgreSQL contract")
    url = os.environ.get("TEST_DATABASE_URL", "")
    parsed = urlparse(url)
    assert parsed.hostname in {"127.0.0.1", "localhost"}
    assert parsed.path.endswith("_test")
    assert os.environ.get("INK_DECK_VERSION_PG_DISPOSABLE") == "1"
    return url


def test_real_postgres_draft_preview_commit_and_conflict() -> None:
    url = disposable_url()

    raw = psycopg.connect(url, row_factory=dict_row)
    db = Lease(raw)
    try:
        raw.execute(
            "INSERT INTO users (id,email,password_hash) VALUES (%s,%s,%s)",
            (900010, "deck-content-service@example.invalid", "hash"),
        )
        raw.execute(
            "INSERT INTO decks (id,name,description,icon,color,owner_id,enabled,order_index) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            ("deck-content-service", "PG Deck", "draft", "brain", "blue", 900010, True, 1),
        )
        raw.execute(
            "INSERT INTO voices (id,deck_id,name,system_prompt,icon,color,owner_id,enabled,order_index) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            ("voice-content-service", "deck-content-service", "Writer", "Write.", "brain", "blue", 900010, True, 1),
        )
        raw.commit()

        service = DeckContentVersionService(db)
        state = service.get_state("deck-content-service", 900010)
        first = DeckVersionMutationRequest(
            expected_draft_revision=state.draft_revision,
            expected_base_version=state.latest_version,
        )
        assert service.preview("deck-content-service", 900010, first).target_version == 1
        committed = service.commit(
            "deck-content-service",
            900010,
            DeckVersionCommitRequest(**first.model_dump(), description="Initial"),
        )
        assert committed.version.version == 1
        assert committed.state.dirty is False

        raw.execute("BEGIN")
        raw.execute(
            "UPDATE decks SET name=%s, draft_revision=draft_revision+1 WHERE id=%s",
            ("PG Deck v2", "deck-content-service"),
        )
        raw.commit()
        next_state = service.get_state("deck-content-service", 900010)
        second = DeckVersionMutationRequest(
            expected_draft_revision=next_state.draft_revision,
            expected_base_version=next_state.latest_version,
        )
        assert service.commit(
            "deck-content-service",
            900010,
            DeckVersionCommitRequest(**second.model_dump(), description="Rename"),
        ).version.version == 2
        assert [entry.version for entry in service.list_versions("deck-content-service", 900010).versions] == [2, 1]

        with pytest.raises(DeckVersionConflict):
            service.commit(
                "deck-content-service",
                900010,
                DeckVersionCommitRequest(**first.model_dump()),
            )
        row = raw.execute(
            "SELECT name,latest_version FROM decks WHERE id=%s", ("deck-content-service",)
        ).fetchone()
        assert row == {"name": "PG Deck v2", "latest_version": 2}
    finally:
        raw.close()


def test_every_effective_form_write_advances_one_aggregate_revision(monkeypatch) -> None:
    url = disposable_url()
    raw = psycopg.connect(url, row_factory=dict_row)
    try:
        raw.execute(
            "INSERT INTO users (id,email,password_hash) VALUES (%s,%s,%s)",
            (900011, "deck-form-service@example.invalid", "hash"),
        )
        raw.execute(
            "INSERT INTO decks (id,name,owner_id) VALUES (%s,%s,%s)",
            ("deck-form-service", "Form Deck", 900011),
        )
        raw.execute(
            """
            INSERT INTO claude_plugin_installations (
              id,requested_package_spec,package_name,marketplace,resolved_version,
              source_type,artifact_digest,artifact_path,claude_cli_version,status,operation_id
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                "plugin-form-service", "form-plugin@official", "form-plugin", "official",
                "1.0.0", "marketplace", "sha256:" + "f" * 64, "/isolated/test",
                "2.1.0", "ready", "operation-form-service",
            ),
        )
        raw.commit()
    finally:
        raw.close()

    def lease_factory():
        return Lease(psycopg.connect(url, row_factory=dict_row))

    monkeypatch.setattr(database, "get_db", lease_factory)
    assert database.update_deck(900011, "deck-form-service", {"name": "Form Deck updated"})
    assert database.update_deck(900011, "deck-form-service", {"name": "Form Deck updated"})
    voice_id = database.create_voice(
        900011, "deck-form-service", "Form Agent", "Draft prompt", icon="brain", color="blue"
    )
    assert database.update_voice(900011, voice_id, {"system_prompt": "Updated prompt"})
    assert database.update_voice(900011, voice_id, {"system_prompt": "Updated prompt"})
    ref = {
        "plugin_installation_id": "plugin-form-service",
        "package_spec": "form-plugin@official",
        "resolved_version": "1.0.0",
        "artifact_digest": "sha256:" + "f" * 64,
        "enabled": True,
        "order_index": 0,
    }
    ref_db = lease_factory()
    database.replace_deck_claude_plugin_refs(ref_db, "deck-form-service", [ref])
    ref_db.close()
    ref_db = lease_factory()
    database.replace_deck_claude_plugin_refs(ref_db, "deck-form-service", [ref])
    ref_db.close()
    ref_db = lease_factory()
    database.replace_deck_claude_plugin_refs(ref_db, "deck-form-service", [])
    ref_db.close()
    assert database.delete_voice(900011, voice_id)

    verify = lease_factory()
    try:
        row = verify.execute(
            "SELECT draft_revision FROM decks WHERE id=%s", ("deck-form-service",)
        ).fetchone()
        assert row["draft_revision"] == 7
    finally:
        verify.close()
