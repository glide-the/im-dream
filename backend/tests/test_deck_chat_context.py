# [Input] Legacy DB seam and strict Admin Registry105 Deck/Voice/plugin-ref snapshots.
# [Output] Prompt parity plus Dream-owned enabled/ready failure and filtering evidence.
# [Pos] Deck context domain tests; Admin owns data access while Dream owns business policy.
# [Sync] 2026-09-15: apply status facts before prompt/Runtime without a Dream database fallback.
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

from services.deck.chat_context import (
    MAX_DECK_CONTEXT_CHARS,
    DeckChatContextAssembler,
    DeckChatContextError,
    DeckChatContextService,
)
from services.admin_data.deck_chat_context_data import DeckChatContextOutputDTO
from services.deck.runtime_context import _compatibility_flag
import database
from backend.schema import legacy_main_sqlite
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
            {
                "INK_DECK_HOST_COMPATIBLE": "1",
                "INK_CLAUDE_AGENT_CONTRACT_COMPATIBLE": "1",
                "INK_STORY_SCHEMA_COMPATIBLE": "1",
                "INK_DECK_RUNTIME_CONFIG_COMPATIBLE": "1",
            },
        )
        self.environment.start()
        self.fixture = BindingFixture()
        legacy_main_sqlite.create_runtime_plugin_tables(self.fixture.db)
        legacy_main_sqlite.create_claude_plugin_tables(self.fixture.db)
        self.fixture.db.execute(
            """
            INSERT INTO voices (
                id, deck_id, name, system_prompt, enabled, order_index
            ) VALUES ('voice-dream', ?, 'Dream Guide', 'Keep a cinematic story voice.', 1, 0)
            """,
            (DECK_ID,),
        )
        self.fixture.db.execute(
            """
            INSERT INTO voices (
                id, deck_id, name, system_prompt, enabled, order_index
            ) VALUES ('voice-editor', ?, 'Story Editor', 'Challenge every plot hole.', 1, 1)
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

    async def test_selected_agent_excludes_sibling_agent_prompts(self) -> None:
        context = await DeckChatContextService(self.fixture.db).resolve(
            deck_id=DECK_ID,
            actor_id="1",
            voice_id="voice-dream",
        )

        self.assertIn("Dream Guide", context.system_prompt)
        self.assertIn("Keep a cinematic story voice.", context.system_prompt)
        self.assertNotIn("Story Editor", context.system_prompt)
        self.assertNotIn("Challenge every plot hole.", context.system_prompt)

        with self.assertRaises(DeckChatContextError) as caught:
            await DeckChatContextService(self.fixture.db).resolve(
                deck_id=DECK_ID,
                actor_id="1",
                voice_id="agent-outside-deck",
            )
        self.assertEqual(caught.exception.code, "AGENT_ACCESS_DENIED")

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

    async def test_admin_snapshot_preserves_prompt_and_provenance_without_db(self) -> None:
        snapshot = DeckChatContextOutputDTO.model_validate(
            {
                "deck": {
                    "id": DECK_ID,
                    "name": "Dream Deck",
                    "name_zh": None,
                    "name_en": None,
                    "description": None,
                    "description_zh": None,
                    "description_en": None,
                    "enabled": True,
                },
                "voices": [
                    {
                        "id": "voice-dream",
                        "name": "Dream Guide",
                        "name_zh": None,
                        "name_en": None,
                        "system_prompt": "Keep a cinematic story voice.",
                        "enabled": True,
                    }
                ],
                "plugin_refs": [
                    {
                        "plugin_installation_id": INSTALLATION_ID,
                        "package_spec": PACKAGE_SPEC,
                        "resolved_version": "6.2.0",
                        "artifact_digest": DIGEST,
                        "order_index": 0,
                        "enabled": True,
                        "installation_status": "ready",
                    }
                ],
            }
        )
        context = await DeckChatContextAssembler(snapshot).resolve()
        self.assertEqual(context.deck_id, DECK_ID)
        self.assertIn("Dream Guide", context.system_prompt)
        self.assertIn("Keep a cinematic story voice.", context.system_prompt)
        self.assertIn(PACKAGE_SPEC, context.system_prompt)
        self.assertNotIn("installation_status", context.plugin_refs[0])

    async def test_admin_snapshot_keeps_non_ready_failure_before_runtime(self) -> None:
        raw = {
            "deck": {
                "id": DECK_ID,
                "name": "Dream Deck",
                "name_zh": None,
                "name_en": None,
                "description": None,
                "description_zh": None,
                "description_en": None,
                "enabled": True,
            },
            "voices": [],
            "plugin_refs": [
                {
                    "plugin_installation_id": INSTALLATION_ID,
                    "package_spec": PACKAGE_SPEC,
                    "resolved_version": "6.2.0",
                    "artifact_digest": DIGEST,
                    "order_index": 0,
                    "enabled": True,
                    "installation_status": "error",
                }
            ],
        }
        with self.assertRaises(DeckChatContextError) as caught:
            await DeckChatContextAssembler(
                DeckChatContextOutputDTO.model_validate(raw)
            ).resolve()
        self.assertEqual(caught.exception.code, "DECK_PLUGIN_UNAVAILABLE")

    async def test_admin_snapshot_keeps_enabled_policy_in_dream(self) -> None:
        snapshot = DeckChatContextOutputDTO.model_validate(
            {
                "deck": {
                    "id": DECK_ID,
                    "name": "Dream Deck",
                    "name_zh": None,
                    "name_en": None,
                    "description": None,
                    "description_zh": None,
                    "description_en": None,
                    "enabled": True,
                },
                "voices": [
                    {
                        "id": "voice-disabled",
                        "name": "Disabled Voice",
                        "name_zh": None,
                        "name_en": None,
                        "system_prompt": "must not enter prompt",
                        "enabled": False,
                    }
                ],
                "plugin_refs": [
                    {
                        "plugin_installation_id": INSTALLATION_ID,
                        "package_spec": PACKAGE_SPEC,
                        "resolved_version": "6.2.0",
                        "artifact_digest": DIGEST,
                        "order_index": 0,
                        "enabled": False,
                        "installation_status": "error",
                    }
                ],
            }
        )

        context = await DeckChatContextAssembler(snapshot).resolve()
        self.assertNotIn("Disabled Voice", context.system_prompt)
        self.assertNotIn("must not enter prompt", context.system_prompt)
        self.assertEqual(context.plugin_refs, ())

        with self.assertRaises(DeckChatContextError) as disabled_voice:
            await DeckChatContextAssembler(
                snapshot,
                selected_voice_id="voice-disabled",
            ).resolve()
        self.assertEqual(disabled_voice.exception.code, "AGENT_ACCESS_DENIED")

        disabled_deck = snapshot.model_copy(
            update={"deck": snapshot.deck.model_copy(update={"enabled": False})}
        )
        with self.assertRaises(DeckChatContextError) as disabled:
            await DeckChatContextAssembler(disabled_deck).resolve()
        self.assertEqual(disabled.exception.code, "DECK_DISABLED")

        with self.assertRaises(DeckChatContextError) as missing_voice:
            await DeckChatContextAssembler(
                snapshot.model_copy(update={"voices": []}),
                selected_voice_id="voice-missing",
            ).resolve()
        self.assertEqual(missing_voice.exception.code, "AGENT_ACCESS_DENIED")

    async def test_admin_snapshot_preserves_the_existing_character_truncation(self) -> None:
        snapshot = DeckChatContextOutputDTO.model_validate(
            {
                "deck": {
                    "id": DECK_ID,
                    "name": "Dream Deck",
                    "name_zh": None,
                    "name_en": None,
                    "description": "界" * (MAX_DECK_CONTEXT_CHARS + 200),
                    "description_zh": None,
                    "description_en": None,
                    "enabled": True,
                },
                "voices": [],
                "plugin_refs": [],
            }
        )
        context = await DeckChatContextAssembler(snapshot).resolve()
        encoded = context.system_prompt.split("<deck_context>\n", 1)[1].split(
            "\n</deck_context>", 1
        )[0]
        self.assertEqual(len(encoded), MAX_DECK_CONTEXT_CHARS)

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
