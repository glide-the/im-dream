"""Deck publication and collection policy regressions.

[Input] Persisted Deck ownership/template/publication facts.
[Output] Verify default Decks cannot publish, actors cannot collect themselves,
         and private Decks cannot be collected by ID.
[Pos] Focused Deck sharing policy tests in backend/tests.
[Sync] 2026-08-14: add My Published Decks permission coverage.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

import config
from routers import voices as voices_router
from services.deck.sharing import (
    COLLECTION_SOURCE_UNAVAILABLE,
    DEFAULT_INITIALIZED_DECK,
    SELF_COLLECTION_FORBIDDEN,
    DeckSharingPolicyError,
    decorate_decks_with_sharing_policy,
    is_default_initialized_deck,
    require_collectable,
    require_publishable,
)


def _screenplay_fallback() -> dict:
    template = config.SCREENPLAY_DECK_TEMPLATE
    return {
        "id": "legacy-default",
        "name": template["name"],
        "name_zh": template["name_zh"],
        "name_en": template["name_en"],
        "is_system": False,
        "parent_id": None,
        "has_local_changes": False,
        "voice_count": len(template["voices"]),
        "voices": [
            {"name": voice["name"], "has_local_changes": False}
            for voice in template["voices"]
        ],
    }


@pytest.mark.parametrize(
    "deck",
    [
        {"is_system": True},
        {"is_system": False, "parent_id": config.DEFAULT_SYSTEM_DECK_ID},
        {"is_system": False, "parent_id": config.RETIRED_SYSTEM_DECK_IDS[0]},
        _screenplay_fallback(),
    ],
)
def test_system_initialized_decks_are_not_publishable(deck: dict) -> None:
    assert is_default_initialized_deck(deck) is True
    with pytest.raises(DeckSharingPolicyError) as caught:
        require_publishable(deck)
    assert caught.value.reason == DEFAULT_INITIALIZED_DECK


def test_user_authored_deck_is_publishable_and_decorated() -> None:
    deck = {
        "id": "user-deck",
        "name": "My Story Helper",
        "is_system": False,
        "parent_id": None,
        "has_local_changes": False,
        "voice_count": 0,
    }
    decorate_decks_with_sharing_policy([deck])
    assert deck["can_publish"] is True
    assert deck["publish_block_reason"] is None


def test_actor_cannot_collect_own_published_deck() -> None:
    with pytest.raises(DeckSharingPolicyError) as caught:
        require_collectable(
            {"owner_id": 28, "published": True, "is_system": False},
            actor_id=28,
        )
    assert caught.value.reason == SELF_COLLECTION_FORBIDDEN


def test_actor_cannot_collect_another_users_private_deck() -> None:
    with pytest.raises(DeckSharingPolicyError) as caught:
        require_collectable(
            {"owner_id": 29, "published": False, "is_system": False},
            actor_id=28,
        )
    assert caught.value.reason == COLLECTION_SOURCE_UNAVAILABLE


def test_other_users_published_deck_remains_collectable() -> None:
    require_collectable(
        {"owner_id": 29, "published": True, "is_system": False},
        actor_id=28,
    )


def test_community_list_excludes_the_current_actor(monkeypatch) -> None:
    calls: list[int | None] = []
    monkeypatch.setattr(
        voices_router.database,
        "get_published_decks",
        lambda exclude_owner_id=None: calls.append(exclude_owner_id) or [],
    )
    assert voices_router.list_decks(
        published=True,
        current_user={"user_id": 28},
    ) == {"decks": []}
    assert calls == [28]


def test_publish_route_returns_conflict_for_default_deck(monkeypatch) -> None:
    monkeypatch.setattr(
        voices_router.database,
        "get_deck_with_voices",
        lambda _user_id, _deck_id: {"id": "default", "published": False},
    )
    monkeypatch.setattr(
        voices_router.database,
        "publish_deck",
        lambda _deck_id, _user_id: (_ for _ in ()).throw(
            DeckSharingPolicyError(
                DEFAULT_INITIALIZED_DECK,
                "System-initialized Decks cannot be published",
            )
        ),
    )
    with pytest.raises(HTTPException) as caught:
        voices_router.publish_deck("default", {"user_id": 28})
    assert caught.value.status_code == 409


def test_fork_route_returns_conflict_for_self_collection(monkeypatch) -> None:
    monkeypatch.setattr(
        voices_router.database,
        "fork_deck",
        lambda _user_id, _deck_id: (_ for _ in ()).throw(
            DeckSharingPolicyError(
                SELF_COLLECTION_FORBIDDEN,
                "You cannot collect your own published Deck",
            )
        ),
    )
    with pytest.raises(HTTPException) as caught:
        voices_router.fork_deck("mine", {"user_id": 28})
    assert caught.value.status_code == 409
