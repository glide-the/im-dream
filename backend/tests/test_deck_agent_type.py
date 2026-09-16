# [Input] Published Deck manifest facts and a provider-free binding projection fixture.
# [Output] Chat/Dream mapping and exact active runtime-version decoration.
# [Pos] Pure Agent-type policy test; binding CAS/UOW belongs to Admin Registry122-129.
# [Sync] 2026-09-16: remove dependency on the retired Dream SQLite binding fixture.
"""Deck Agent-type capability derivation and projection tests."""

from __future__ import annotations

from copy import deepcopy
import unittest

from models.deck_plugin import DeckAgentType, DeckPluginManifestV1
from services.deck.agent_type import (
    agent_type_from_manifest,
    decorate_decks_with_agent_type,
)
from tests.test_deck_plugin_manifest import valid_manifest_data


DECK_ID = "deck-binding-test"
PLUGIN_ID = "voice-decks.story-dramatize"
VERSION = "3.1.0"


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _ProjectionDb:
    """Supplies already-authorized projection rows; never parses or executes SQL."""

    def __init__(self, manifest_json: str) -> None:
        self.manifest_json = manifest_json
        self.calls = 0

    def execute(self, _sql, parameters):
        self.calls += 1
        assert parameters == (DECK_ID,)
        if self.calls == 1:
            return _Rows([{"deck_id": DECK_ID, "binding_revision": 1}])
        if self.calls == 2:
            return _Rows(
                [
                    {
                        "deck_id": DECK_ID,
                        "deck_plugin_id": PLUGIN_ID,
                        "deck_plugin_version": VERSION,
                        "manifest_json": self.manifest_json,
                    }
                ]
            )
        raise AssertionError("unexpected projection read")


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

    def test_deck_list_decoration_exposes_exact_active_runtime_version(self) -> None:
        data = valid_manifest_data()
        data["capabilities"] = [*data["capabilities"], "story.workspace.propose"]
        manifest = DeckPluginManifestV1.model_validate(data)
        db = _ProjectionDb(manifest.model_dump_json())
        deck = {"id": DECK_ID, "name": "Binding Deck"}

        decorate_decks_with_agent_type(db, [deck])

        self.assertEqual(db.calls, 2)
        self.assertEqual(deck["agent_type"], "dream")
        self.assertEqual(deck["agent_type_revision"], 1)
        self.assertEqual(deck["deck_plugin_id"], PLUGIN_ID)
        self.assertEqual(deck["deck_plugin_version"], VERSION)


if __name__ == "__main__":
    unittest.main()
