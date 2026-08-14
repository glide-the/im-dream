"""Derive the product-facing Deck Agent type from published binding facts.

This module is the sole mapping between Deck Plugin capabilities and the
Chat/Dream product enum. It never trusts a browser mode flag and does not own
schema creation or runtime provisioning.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

try:
    from backend.models.deck_plugin import DeckAgentType, DeckPluginManifestV1
except ModuleNotFoundError:  # Support the backend directory on PYTHONPATH.
    from models.deck_plugin import DeckAgentType, DeckPluginManifestV1


DREAM_AGENT_CAPABILITY = "story.workspace.propose"


def agent_type_from_manifest(raw_manifest: Any) -> DeckAgentType:
    """Fail closed to ordinary Chat when release evidence is absent or invalid."""

    try:
        manifest = (
            DeckPluginManifestV1.model_validate(raw_manifest)
            if isinstance(raw_manifest, dict)
            else DeckPluginManifestV1.model_validate_json(str(raw_manifest))
        )
    except (TypeError, ValueError):
        return DeckAgentType.CHAT
    return (
        DeckAgentType.DREAM
        if DREAM_AGENT_CAPABILITY in manifest.capabilities
        else DeckAgentType.CHAT
    )


def agent_type_records_for_decks(
    db: Any,
    deck_ids: Iterable[str],
) -> dict[str, tuple[DeckAgentType, int]]:
    """Return server-derived type and monotonic binding revision per Deck."""

    identifiers = list(dict.fromkeys(str(deck_id) for deck_id in deck_ids))
    if not identifiers:
        return {}
    placeholders = ",".join("%s" for _ in identifiers)
    revisions = {
        str(row["deck_id"]): int(row["binding_revision"])
        for row in db.execute(
            f"""
            SELECT deck_id, MAX(binding_revision) AS binding_revision
            FROM deck_plugin_bindings
            WHERE deck_id IN ({placeholders})
            GROUP BY deck_id
            """,
            tuple(identifiers),
        ).fetchall()
    }
    records = {
        deck_id: (DeckAgentType.CHAT, revisions.get(deck_id, 0))
        for deck_id in identifiers
    }
    rows = db.execute(
        f"""
        SELECT binding.deck_id, release.manifest_json
        FROM deck_plugin_bindings AS binding
        JOIN deck_plugin_releases AS release
          ON release.deck_plugin_id = binding.deck_plugin_id
         AND release.deck_plugin_version = binding.deck_plugin_version
        WHERE binding.status = 'active'
          AND release.status IN ('published', 'deprecated')
          AND binding.deck_id IN ({placeholders})
        """,
        tuple(identifiers),
    ).fetchall()
    for row in rows:
        deck_id = str(row["deck_id"])
        records[deck_id] = (
            agent_type_from_manifest(row["manifest_json"]),
            revisions.get(deck_id, 0),
        )
    return records


def decorate_decks_with_agent_type(db: Any, decks: list[dict[str, Any]]) -> None:
    records = agent_type_records_for_decks(db, (deck["id"] for deck in decks))
    for deck in decks:
        agent_type, revision = records.get(
            str(deck["id"]),
            (DeckAgentType.CHAT, 0),
        )
        deck["agent_type"] = agent_type.value
        deck["agent_type_revision"] = revision
