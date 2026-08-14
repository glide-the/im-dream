# [Input] Screenplay Deck policy, Deck-default service, persistence helpers, and
#         Deck routes.
# [Output] Verify one screenplay-role default, retirement visibility, zero-ref
#          repair, community query validity, verified drama-forge selection,
#          and atomic rollback behavior.
# [Pos] Deck default policy and creation contract test in backend/tests
# [Sync] 2026-08-14: cover new provisioning and non-destructive legacy repair.

from __future__ import annotations

from typing import Any

import pytest
from fastapi import HTTPException

import config
import database
from routers import voices as voices_router
from services.deck import defaults as deck_defaults


class _Cursor:
    def __init__(self, row: dict[str, Any] | None = None) -> None:
        self._row = row

    def fetchone(self):
        return self._row


class _CreateDeckDb:
    def __init__(self, installation: dict[str, Any] | None) -> None:
        self.installation = installation
        self.statements: list[tuple[str, tuple[Any, ...]]] = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> _Cursor:
        normalized = " ".join(sql.split())
        self.statements.append((normalized, tuple(params)))
        if "SELECT MAX(order_index)" in normalized:
            return _Cursor({"max_order": 0})
        if "FROM claude_plugin_installations" in normalized:
            return _Cursor(self.installation)
        return _Cursor()

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


class _SystemDeckLookupDb:
    def __init__(self, row: dict[str, Any] | None) -> None:
        self.row = row
        self.params: tuple[Any, ...] | None = None
        self.closed = False

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> _Cursor:
        assert "is_system IS TRUE" in " ".join(sql.split())
        self.params = tuple(params)
        return _Cursor(self.row)

    def close(self) -> None:
        self.closed = True


class _PublishedDeckDb:
    def __init__(self) -> None:
        self.sql = ""
        self.closed = False

    def execute(self, sql: str, params: tuple[Any, ...] = ()):
        self.sql = " ".join(sql.split())

        class _Rows:
            @staticmethod
            def fetchall() -> list[dict[str, Any]]:
                return []

        return _Rows()

    def close(self) -> None:
        self.closed = True


class _ReconcileDb(_CreateDeckDb):
    def __init__(self, existing_ref: dict[str, Any] | None) -> None:
        super().__init__(_verified_installation())
        self.existing_ref = existing_ref

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> _Cursor:
        normalized = " ".join(sql.split())
        self.statements.append((normalized, tuple(params)))
        if "SELECT d.id FROM decks d" in normalized:
            return _Cursor({"id": "screenplay-user-deck"})
        if "SELECT 1 FROM deck_claude_plugin_refs" in normalized:
            return _Cursor(self.existing_ref)
        if "FROM claude_plugin_installations" in normalized:
            return _Cursor(self.installation)
        return _Cursor()


def _verified_installation() -> dict[str, Any]:
    return {
        "id": "installation-drama-forge",
        "requested_package_spec": "drama-forge@drama-studio",
        "package_name": "drama-forge",
        "marketplace": "drama-studio",
        "resolved_version": "1.0.1",
        "artifact_digest": "sha256:verified",
        "status": "ready",
    }


def _default_ref() -> dict[str, str]:
    installation = _verified_installation()
    return {
        "plugin_installation_id": installation["id"],
        "package_name": installation["package_name"],
        "resolved_version": installation["resolved_version"],
        "artifact_digest": installation["artifact_digest"],
    }


def test_screenplay_template_is_the_only_active_default_policy() -> None:
    template = config.SCREENPLAY_DECK_TEMPLATE
    assert template["id"] == config.DEFAULT_SYSTEM_DECK_ID
    assert template["name"] == "剧本创作团队"
    assert [voice["name"] for voice in template["voices"]] == [
        "编剧",
        "戏剧结构师",
        "人物塑造师",
        "对白编辑",
        "连续性审校",
    ]
    assert config.RETIRED_SYSTEM_DECK_IDS == (
        "introspection_deck",
        "scholar_deck",
        "philosophy_deck",
    )


def test_retired_visibility_preserves_user_modified_decks() -> None:
    sql, params = database._retired_system_deck_visibility()
    assert params == list(config.RETIRED_SYSTEM_DECK_IDS)
    assert "d.has_local_changes IS TRUE" in sql
    assert "changed_voice.has_local_changes IS TRUE" in sql
    assert sql.count("%s") == len(params)


def test_published_decks_group_author_for_postgresql(monkeypatch) -> None:
    fake_db = _PublishedDeckDb()
    monkeypatch.setattr(database, "get_db", lambda: fake_db)

    assert database.get_published_decks() == []
    assert "GROUP BY d.id, u.display_name" in fake_db.sql
    assert fake_db.closed is True


def test_new_user_provisions_only_the_active_screenplay_system_deck(monkeypatch) -> None:
    fake_db = _SystemDeckLookupDb({"id": config.DEFAULT_SYSTEM_DECK_ID})
    forks: list[tuple[int, str, bool, dict]] = []
    fallbacks: list[int] = []
    monkeypatch.setattr(database, "get_db", lambda: fake_db)
    monkeypatch.setattr(
        database,
        "fork_deck",
        lambda user_id, deck_id, enabled=True, default_plugin_ref=None: forks.append(
            (user_id, deck_id, enabled, default_plugin_ref)
        ) or "forked",
    )
    monkeypatch.setattr(
        database,
        "create_default_screenplay_deck",
        lambda user_id, default_plugin_ref: fallbacks.append(user_id) or "fallback",
    )

    database.auto_fork_system_decks(7, _default_ref())

    assert fake_db.params == (config.DEFAULT_SYSTEM_DECK_ID,)
    assert forks == [(7, config.DEFAULT_SYSTEM_DECK_ID, True, _default_ref())]
    assert fallbacks == []
    assert fake_db.closed is True


def test_new_user_falls_back_to_user_owned_screenplay_template(monkeypatch) -> None:
    fake_db = _SystemDeckLookupDb(None)
    forks: list[tuple[Any, ...]] = []
    fallbacks: list[int] = []
    monkeypatch.setattr(database, "get_db", lambda: fake_db)
    monkeypatch.setattr(
        database,
        "fork_deck",
        lambda *args, **kwargs: forks.append((*args, kwargs)) or "forked",
    )
    monkeypatch.setattr(
        database,
        "create_default_screenplay_deck",
        lambda user_id, default_plugin_ref: fallbacks.append(user_id) or "fallback",
    )

    database.auto_fork_system_decks(7, _default_ref())

    assert forks == []
    assert fallbacks == [7]
    assert fake_db.closed is True


def test_reconcile_empty_default_deck_refs_adds_only_drama_forge(monkeypatch) -> None:
    fake_db = _ReconcileDb(existing_ref=None)
    monkeypatch.setattr(database, "get_db", lambda: fake_db)

    result = database.reconcile_default_screenplay_deck_plugin_ref(7, _default_ref())

    assert result == {
        "deck_id": "screenplay-user-deck",
        "reconciled": True,
        "reason": "missing_ref",
    }
    inserts = [
        sql for sql, _ in fake_db.statements if "INSERT INTO deck_claude_plugin_refs" in sql
    ]
    assert len(inserts) == 1
    assert fake_db.commits == 1
    assert fake_db.rollbacks == 0
    assert fake_db.closed is True


def test_reconcile_preserves_any_existing_user_plugin_selection(monkeypatch) -> None:
    fake_db = _ReconcileDb(existing_ref={"exists": 1})
    monkeypatch.setattr(database, "get_db", lambda: fake_db)

    result = database.reconcile_default_screenplay_deck_plugin_ref(7, _default_ref())

    assert result == {
        "deck_id": "screenplay-user-deck",
        "reconciled": False,
        "reason": "refs_preserved",
    }
    assert not any(
        "INSERT INTO deck_claude_plugin_refs" in sql for sql, _ in fake_db.statements
    )
    assert fake_db.commits == 0
    assert fake_db.rollbacks == 1
    assert fake_db.closed is True


def test_create_deck_commits_deck_and_default_plugin_ref_together(monkeypatch) -> None:
    fake_db = _CreateDeckDb(_verified_installation())
    monkeypatch.setattr(database, "get_db", lambda: fake_db)

    deck_id = database.create_deck(
        7,
        "新剧本卡组",
        default_plugin_ref=_default_ref(),
    )

    assert deck_id
    assert fake_db.commits == 1
    assert fake_db.rollbacks == 0
    assert any("INSERT INTO decks" in sql for sql, _ in fake_db.statements)
    plugin_ref_inserts = [
        sql for sql, _ in fake_db.statements if "INSERT INTO deck_claude_plugin_refs" in sql
    ]
    assert len(plugin_ref_inserts) == 1
    assert "VALUES (%s, %s, %s, %s, %s, 1, 0" in plugin_ref_inserts[0]
    assert fake_db.closed is True


def test_create_deck_rolls_back_when_default_plugin_changes(monkeypatch) -> None:
    installation = _verified_installation()
    installation["status"] = "uninstalled"
    fake_db = _CreateDeckDb(installation)
    monkeypatch.setattr(database, "get_db", lambda: fake_db)

    with pytest.raises(ValueError, match="DEFAULT_DECK_PLUGIN_UNAVAILABLE"):
        database.create_deck(7, "不会留下的卡组", default_plugin_ref=_default_ref())

    assert fake_db.commits == 0
    assert fake_db.rollbacks == 1
    assert not any("INSERT INTO deck_claude_plugin_refs" in sql for sql, _ in fake_db.statements)


def test_default_service_resolves_exact_verified_installation(monkeypatch) -> None:
    installation = _verified_installation()
    fake_db = _CreateDeckDb(installation)

    class _InstallService:
        def __init__(self, db) -> None:
            assert db is fake_db

        def list_installations(self):
            return [installation]

        def verify_installation_artifact(self, record) -> bool:
            return record is installation

        def check_cli_compatibility(self, record) -> bool:
            return record is installation

    monkeypatch.setattr(deck_defaults.database, "get_db", lambda: fake_db)
    monkeypatch.setattr(deck_defaults, "PluginInstallService", _InstallService)

    assert deck_defaults.resolve_default_deck_plugin_ref() == _default_ref()
    assert fake_db.closed is True


def test_reconcile_route_delegates_to_default_service(monkeypatch) -> None:
    expected = {
        "deck_id": "screenplay-user-deck",
        "reconciled": True,
        "reason": "missing_ref",
    }
    actors: list[int] = []
    monkeypatch.setattr(
        voices_router,
        "reconcile_default_screenplay_deck_plugin",
        lambda user_id: actors.append(user_id) or expected,
    )

    assert voices_router.reconcile_deck_defaults(
        current_user={"user_id": 7},
    ) == expected
    assert actors == [7]


def test_router_fails_closed_without_default_plugin(monkeypatch) -> None:
    monkeypatch.setattr(
        voices_router,
        "resolve_default_deck_plugin_ref",
        lambda: (_ for _ in ()).throw(voices_router.DefaultDeckPluginUnavailable()),
    )
    created: list[dict[str, Any]] = []
    monkeypatch.setattr(
        voices_router.database,
        "create_deck",
        lambda *args, **kwargs: created.append(kwargs),
    )

    with pytest.raises(HTTPException) as raised:
        voices_router.create_deck(
            voices_router.DeckCreateRequest(name="New Deck"),
            current_user={"user_id": 7},
        )

    assert raised.value.status_code == 409
    assert "drama-forge v1.0.1" in str(raised.value.detail)
    assert created == []
