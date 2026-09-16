# [Input] Published Deck manifest facts supplied by the Admin DTO boundary.
# [Output] Pure Chat/Dream capability mapping without persistence access.
# [Pos] Pure Agent-type policy test; projection and CAS/UOW belong to Admin Registry122-129.
# [Sync] 2026-09-16: retire the legacy Dream SQL projection fixture.
"""Deck Agent-type capability derivation tests."""

from __future__ import annotations

from copy import deepcopy
import unittest

from models.deck_plugin import DeckAgentType
from services.deck.agent_type import agent_type_from_manifest
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

if __name__ == "__main__":
    unittest.main()
