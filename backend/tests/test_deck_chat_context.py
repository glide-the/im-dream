# [Input] Strict Admin Registry105 Deck/Voice/plugin-ref snapshots.
# [Output] Prompt parity plus Dream-owned enabled/ready failure and filtering evidence.
# [Pos] Provider-free Deck context policy tests; Admin owns data access.
# [Sync] 2026-09-16: remove the retired SQLite resolver tests and retain DTO snapshot policy.
"""Deck → Chat → ClaudeAgent context policy contract tests."""

from __future__ import annotations

import unittest

from services.deck.chat_context import (
    MAX_DECK_CONTEXT_CHARS,
    DeckChatContextAssembler,
    DeckChatContextError,
)
from services.admin_data.deck_chat_context_data import DeckChatContextOutputDTO


DECK_ID = "deck-dream"
DIGEST = "sha256:" + "b" * 64
INSTALLATION_ID = "cpi_test_ready"
PACKAGE_SPEC = "superpowers@claude-plugins-official"


class DeckChatContextTests(unittest.IsolatedAsyncioTestCase):
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

    async def test_admin_snapshot_dream_mode_uses_workspace_file_lifecycle(self) -> None:
        snapshot = DeckChatContextOutputDTO.model_validate(
            {
                "deck": {
                    "id": DECK_ID, "name": "Dream Deck", "name_zh": None,
                    "name_en": None, "description": None,
                    "description_zh": None, "description_en": None,
                    "enabled": True,
                },
                "voices": [],
                "plugin_refs": [],
            }
        )
        context = await DeckChatContextAssembler(snapshot).resolve(dream_mode=True)
        self.assertIn("canonical workspace files", context.system_prompt)
        self.assertIn("Dream run context", context.system_prompt)
        self.assertNotIn("exactly one JSON object", context.system_prompt)
        self.assertNotIn("pending Dream proposal", context.system_prompt)



if __name__ == "__main__":
    unittest.main()
