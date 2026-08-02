"""Deck → Chat → ClaudeAgent context and plugin-loading contract tests."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys
import unittest
from unittest import mock


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.deck.chat_context import DeckChatContextError, DeckChatContextService
from services.deck.runtime_context import _compatibility_flag
import database
from tests.test_deck_plugin_binding import (
    BindingFixture,
    DECK_ID,
    DIGEST,
    RUNTIME_PLUGIN_ID,
)


class DeckChatContextTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.environment = mock.patch.dict(
            os.environ,
            {"INK_ENVIRONMENT": "test"},
        )
        self.environment.start()
        self.fixture = BindingFixture()
        database.create_runtime_plugin_tables(self.fixture.db)
        self.fixture.db.execute(
            """
            INSERT INTO voices (
                id, deck_id, name, system_prompt, enabled, order_index
            ) VALUES ('voice-dream', ?, 'Dream Guide', 'Keep a cinematic story voice.', 1, 0)
            """,
            (DECK_ID,),
        )
        self.fixture.db.commit()

    def tearDown(self) -> None:
        self.fixture.close()
        self.environment.stop()

    async def test_unbound_deck_loads_owned_voice_context_without_plugins(self) -> None:
        context = await DeckChatContextService(self.fixture.db).resolve(
            deck_id=DECK_ID,
            actor_id="1",
        )
        self.assertEqual(context.deck_id, DECK_ID)
        self.assertIn("Dream Guide", context.system_prompt)
        self.assertIn("Keep a cinematic story voice.", context.system_prompt)
        self.assertIsNone(context.claude_settings_json)
        self.assertIsNone(context.plugin_provenance)

    async def test_bound_ready_deck_generates_server_owned_claude_settings(self) -> None:
        await self.fixture.binding.save(
            deck_id=DECK_ID,
            actor_id="1",
            request=BindingFixture.request(0),
        )
        now = datetime.now(UTC).isoformat()
        self.fixture.db.execute(
            """
            INSERT INTO runtime_plugin_materializations (
                runtime_materialization_id, runtime_environment_id,
                runtime_pool_id, runtime_node_id, claude_code_plugin_id,
                resolved_version, artifact_digest, materialized_digest,
                artifact_set_hash, policy_revision, declaration_status,
                materialization_status, activation_status, materialization_key,
                attempt_id, attempt_count, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "rpm-deck-chat",
                "development",
                "development",
                "node-local",
                RUNTIME_PLUGIN_ID,
                "1.4.2",
                DIGEST,
                DIGEST,
                "sha256:" + "a" * 64,
                "policy-development",
                "declared",
                "materialized",
                "loadable",
                "deck-chat-ready",
                "attempt-deck-chat",
                1,
                now,
                now,
            ),
        )
        self.fixture.db.commit()

        context = await DeckChatContextService(self.fixture.db).resolve(
            deck_id=DECK_ID,
            actor_id="1",
        )
        self.assertEqual(
            json.loads(context.claude_settings_json or "{}"),
            {"enabledPlugins": {RUNTIME_PLUGIN_ID: True}},
        )
        self.assertEqual(
            context.plugin_provenance["binding_revision"], 1  # type: ignore[index]
        )
        self.assertIn(RUNTIME_PLUGIN_ID, context.system_prompt)

    async def test_bound_deck_fails_closed_when_runtime_is_not_materialized(self) -> None:
        await self.fixture.binding.save(
            deck_id=DECK_ID,
            actor_id="1",
            request=BindingFixture.request(0),
        )
        with self.assertRaises(DeckChatContextError) as caught:
            await DeckChatContextService(self.fixture.db).resolve(
                deck_id=DECK_ID,
                actor_id="1",
            )
        self.assertEqual(caught.exception.code, "RUNTIME_PLUGIN_NOT_READY")

    async def test_deck_ownership_is_server_enforced(self) -> None:
        with self.assertRaises(DeckChatContextError) as caught:
            await DeckChatContextService(self.fixture.db).resolve(
                deck_id=DECK_ID,
                actor_id="2",
            )
        self.assertEqual(caught.exception.code, "DECK_ACCESS_DENIED")

    def test_undeclared_environment_is_fail_closed(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(_compatibility_flag("INK_DECK_HOST_COMPATIBLE"))


if __name__ == "__main__":
    unittest.main()
