"""Deck publishing and collection policy.

[Input] Persisted Deck ownership, publication, parent-template, and local-change facts.
[Output] Derive publish eligibility and reject default-Deck publishing, self-collection,
         and collection of non-public Decks.
[Pos] Shared Deck sharing policy used by list DTO decoration and mutation boundaries.
[Sync] 2026-08-14: add the server-owned sharing policy for My Published Decks.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

try:
    import config
except ModuleNotFoundError:  # pragma: no cover - package import compatibility
    from backend import config


DEFAULT_INITIALIZED_DECK = "default_initialized"
SELF_COLLECTION_FORBIDDEN = "self_collection_forbidden"
COLLECTION_SOURCE_UNAVAILABLE = "collection_source_unavailable"


class DeckSharingPolicyError(ValueError):
    """A Deck sharing mutation conflicts with the server-owned policy."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


def _enabled(value: Any) -> bool:
    return value is True or value == 1


def is_default_initialized_deck(deck: Mapping[str, Any]) -> bool:
    """Recognize shared templates and user copies provisioned from them.

    Modern copies retain their configured template ID in ``parent_id``. The
    exact screenplay fingerprint covers legacy fallback copies and copies whose
    parent link was broken by the former publishing behavior.
    """

    if _enabled(deck.get("is_system")):
        return True

    system_template_ids = {
        config.DEFAULT_SYSTEM_DECK_ID,
        *config.RETIRED_SYSTEM_DECK_IDS,
    }
    if deck.get("parent_id") in system_template_ids:
        return True

    template = config.SCREENPLAY_DECK_TEMPLATE
    voice_count = deck.get("total_voice_count", deck.get("voice_count"))
    voices = deck.get("voices")
    if isinstance(voices, list):
        voice_count = len(voices)

    return (
        deck.get("parent_id") is None
        and not _enabled(deck.get("has_local_changes"))
        and deck.get("name") == template["name"]
        and deck.get("name_zh") == template["name_zh"]
        and deck.get("name_en") == template["name_en"]
        and voice_count == len(template["voices"])
    )


def decorate_decks_with_sharing_policy(decks: Iterable[dict[str, Any]]) -> None:
    """Attach list-safe publication policy facts without changing persistence."""

    for deck in decks:
        blocked = is_default_initialized_deck(deck)
        deck["can_publish"] = not blocked
        deck["publish_block_reason"] = DEFAULT_INITIALIZED_DECK if blocked else None


def require_publishable(deck: Mapping[str, Any]) -> None:
    if is_default_initialized_deck(deck):
        raise DeckSharingPolicyError(
            DEFAULT_INITIALIZED_DECK,
            "System-initialized Decks cannot be published",
        )


def require_collectable(deck: Mapping[str, Any], actor_id: int) -> None:
    owner_id = deck.get("owner_id")
    if owner_id is not None and int(owner_id) == int(actor_id):
        raise DeckSharingPolicyError(
            SELF_COLLECTION_FORBIDDEN,
            "You cannot collect your own published Deck",
        )
    if not _enabled(deck.get("is_system")) and not _enabled(deck.get("published")):
        raise DeckSharingPolicyError(
            COLLECTION_SOURCE_UNAVAILABLE,
            "Only system or published Decks can be collected",
        )
