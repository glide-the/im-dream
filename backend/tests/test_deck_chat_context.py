"""Deck → Chat → ClaudeAgent context and plugin-loading contract tests.

2026-08-02 (deck-integration-delta): rewritten for the shared-installation
architecture.  DeckChatContext no longer produces settings JSON or plugin
paths; it validates ``deck_claude_plugin_refs`` → ``claude_plugin_installations``
references and returns them as informational provenance.  Plugin bytes flow
through the workspace pack, never through per-run agent options.
"""

from __future__ import annotations

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
from tests.test_deck_plugin_binding import BindingFixture, DECK_ID


DIGEST = "sha256:" + "b" * 64
INSTALLATION_ID = "cpi_test_ready"
PACKAGE_SPEC = "superpowers@claude-plugins-official"


def _insert_installation(db, *, status: str = "ready", installation_id: str = INSTALLATION_ID) -> None:
    db.execute(
        """
        INSERT INTO claude_plugin_installations (
            id, requested_package_spec, package_name, marketplace,
            resolved_version, source_type, artifact_digest, artifact_path,
            claude_cli_version, component_inventory_json, status,
            operation_id, file_count, installed_at
        ) VALUES (?, ?, 'superpowers', 'claude-plugins-official',
                  '6.2.0', 'claude-official', ?, '/managed/artifacts/x',
                  '2.1.220 (Claude Code)', '{}', ?, 'cop_test', 180,
                  '2026-08-02T00:00:00')
        """,
        (installation_id, PACKAGE_SPEC, DIGEST, status),
    )


def _insert_ref(
    db,
    *,
    deck_id: str = DECK_ID,
    installation_id: str = INSTALLATION_ID,
    enabled: int = 1,
) -> None:
    db.execute(
        """
        INSERT INTO deck_claude_plugin_refs (
            deck_id, plugin_installation_id, package_spec, resolved_version,
            artifact_digest, enabled, order_index
        ) VALUES (?, ?, ?, '6.2.0', ?, ?, 0)
        """,
        (deck_id, installation_id, PACKAGE_SPEC, DIGEST, enabled),
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
        database.create_claude_plugin_tables(self.fixture.db)
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
        self.assertEqual(context.plugin_refs, ())
        self.assertIsNone(context.plugin_provenance)
        self.assertIn("exactly one JSON object", context.system_prompt)

    async def test_dream_mode_uses_workspace_file_lifecycle_not_legacy_json(self) -> None:
        context = await DeckChatContextService(self.fixture.db).resolve(
            deck_id=DECK_ID,
            actor_id="1",
            dream_mode=True,
        )

        self.assertNotIn("exactly one JSON object", context.system_prompt)
        self.assertNotIn("pending Dream proposal", context.system_prompt)
        self.assertIn("canonical workspace files", context.system_prompt)
        self.assertIn("Dream run context", context.system_prompt)

    async def test_ready_refs_surface_as_digest_pinned_provenance(self) -> None:
        _insert_installation(self.fixture.db)
        _insert_ref(self.fixture.db)
        self.fixture.db.commit()

        context = await DeckChatContextService(self.fixture.db).resolve(
            deck_id=DECK_ID,
            actor_id="1",
        )
        self.assertEqual(len(context.plugin_refs), 1)
        ref = context.plugin_refs[0]
        self.assertEqual(ref["package_spec"], PACKAGE_SPEC)
        self.assertEqual(ref["resolved_version"], "6.2.0")
        self.assertEqual(ref["artifact_digest"], DIGEST)
        self.assertEqual(
            context.plugin_provenance["source"],  # type: ignore[index]
            "deck_claude_plugin_refs",
        )
        # Provenance is embedded in the system prompt for transparency.
        self.assertIn(PACKAGE_SPEC, context.system_prompt)
        # The context must never carry settings JSON or plugin paths.
        self.assertFalse(hasattr(context, "claude_settings_json"))
        self.assertFalse(hasattr(context, "claude_plugin_paths"))

    async def test_non_ready_installation_fails_closed(self) -> None:
        _insert_installation(self.fixture.db, status="installing")
        _insert_ref(self.fixture.db)
        self.fixture.db.commit()

        with self.assertRaises(DeckChatContextError) as caught:
            await DeckChatContextService(self.fixture.db).resolve(
                deck_id=DECK_ID,
                actor_id="1",
            )
        self.assertEqual(caught.exception.code, "DECK_PLUGIN_UNAVAILABLE")

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
