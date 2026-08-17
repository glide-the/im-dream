"""Deck Agent type capability derivation and binding-history tests.

[Sync 2026-08-16] Assert list DTO decoration includes exact active version facts.
"""

from __future__ import annotations

import asyncio
from copy import deepcopy
from pathlib import Path
import sys
import unittest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from models.deck_plugin import DeckAgentType
from services.deck.agent_type import agent_type_from_manifest, decorate_decks_with_agent_type
from tests.test_deck_plugin_binding import BindingFixture
from tests.test_deck_plugin_manifest import valid_manifest_data


class DeckAgentTypeTests(unittest.TestCase):
    def test_manifest_capability_is_the_only_dream_mapping(self) -> None:
        chat_manifest = valid_manifest_data()
        dream_manifest = deepcopy(chat_manifest)
        dream_manifest["capabilities"] = [
            *dream_manifest["capabilities"],
            "story.workspace.propose",
        ]
        self.assertEqual(agent_type_from_manifest(chat_manifest), DeckAgentType.CHAT)
        self.assertEqual(agent_type_from_manifest(dream_manifest), DeckAgentType.DREAM)
        self.assertEqual(agent_type_from_manifest({"invalid": True}), DeckAgentType.CHAT)

    def test_chat_selection_stales_binding_and_keeps_revision_monotonic(self) -> None:
        async def scenario() -> None:
            fixture = BindingFixture()
            try:
                first = await fixture.binding.save(
                    deck_id="deck-binding-test",
                    actor_id="1",
                    requested_workspace_id="workspace-binding-test",
                    request=fixture.request(0),
                )
                cleared = fixture.binding.clear(
                    deck_id="deck-binding-test",
                    actor_id="1",
                    requested_workspace_id="workspace-binding-test",
                    expected_binding_revision=first.binding_revision,
                )
                self.assertIsNone(cleared.binding)
                self.assertEqual(cleared.binding_revision, 1)
                second = await fixture.binding.save(
                    deck_id="deck-binding-test",
                    actor_id="1",
                    requested_workspace_id="workspace-binding-test",
                    request=fixture.request(1),
                )
                self.assertEqual(second.binding_revision, 2)
            finally:
                fixture.close()

        asyncio.run(scenario())

    def test_deck_list_decoration_exposes_exact_active_runtime_version(self) -> None:
        async def scenario() -> None:
            fixture = BindingFixture()
            try:
                await fixture.binding.save(
                    deck_id="deck-binding-test",
                    actor_id="1",
                    requested_workspace_id="workspace-binding-test",
                    request=fixture.request(0),
                )
                deck = {"id": "deck-binding-test", "name": "Binding Deck"}
                decorate_decks_with_agent_type(fixture.db, [deck])
                self.assertEqual(deck["agent_type_revision"], 1)
                self.assertEqual(deck["deck_plugin_id"], "voice-decks.story-dramatize")
                self.assertEqual(deck["deck_plugin_version"], "3.1.0")
            finally:
                fixture.close()

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
