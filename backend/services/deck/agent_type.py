"""Derive the product-facing Deck Agent type from published binding facts.

This module maps an Admin-supplied published manifest to the Chat/Dream
product enum. It never opens a database or trusts a browser mode flag.

[Sync 2026-09-16] Remove the legacy Dream SQL projection after list/detail adopted Admin DTOs.
"""

from __future__ import annotations

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
