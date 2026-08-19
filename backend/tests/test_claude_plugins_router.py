"""Route-level authorization contracts for shared Claude Code plugins.

[Input] Production FastAPI router with PostgreSQL-shaped services and captured background tasks.
[Output] Auth, platform-global catalog, entry-ID queue, terminal crash, operation, and Deck-ref route evidence.
[Pos] Focused public ClaudePlugin API contract tests; no real business database writes.
[Sync] 2026-08-19: cover identical catalogs, Remote Marketplace queueing, and background error termination.
"""

from __future__ import annotations

from pathlib import Path
import sys
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from routers import claude_plugins
from routers.deps import get_current_user
from services.claude_plugin.marketplace_service import MarketplaceInstallSource


class _Cursor:
    def __init__(self, rows: list[tuple], columns: list[str] | None = None) -> None:
        self._rows = rows
        self.description = [(column,) for column in columns] if columns else None

    def fetchall(self) -> list[tuple]:
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class _Db:
    def execute(self, sql: str, _params: object = ()) -> _Cursor:
        if "INSERT INTO claude_plugin_operations" in sql:
            return _Cursor([])
        if "deck_claude_plugin_refs" in sql:
            return _Cursor([("plugin-1", 2)])
        if "claude_plugin_operations" in sql:
            return _Cursor(
                [("op-1", "install", "demo@market", "ready")],
                ["id", "operation_kind", "requested_package_spec", "status"],
            )
        raise AssertionError(f"Unexpected query: {sql}")

    def close(self) -> None:
        pass

    def commit(self) -> None:
        pass


class _InstallService:
    def __init__(self, _db: _Db) -> None:
        pass

    def list_installations(self) -> list[dict[str, object]]:
        return [{"id": "plugin-1", "package_name": "demo"}]


class _BackgroundDb(_Db):
    def __init__(self) -> None:
        self.error_update: tuple | None = None
        self.commits = 0

    def execute(self, sql: str, params: object = ()) -> _Cursor:
        if "UPDATE claude_plugin_operations" in sql:
            self.error_update = tuple(params)  # type: ignore[arg-type]
            return _Cursor([])
        return super().execute(sql, params)

    def commit(self) -> None:
        self.commits += 1


def _client(current_user: dict[str, object]) -> TestClient:
    app = FastAPI()
    app.include_router(claude_plugins.router)
    app.dependency_overrides[get_current_user] = lambda: current_user
    return TestClient(app)


def test_signed_in_user_can_read_shared_plugins_and_operations() -> None:
    """The Settings page's initial reads must not require an admin role."""
    with (
        mock.patch.object(claude_plugins.database, "get_db", return_value=_Db()),
        mock.patch.object(claude_plugins, "PluginInstallService", _InstallService),
    ):
        client = _client({"user_id": 7, "role": "user"})
        installations = client.get("/api/claude-plugins/installations")
        operations = client.get("/api/claude-plugins/operations?limit=8")

    assert installations.status_code == 200
    assert installations.json() == {
        "installations": [{"id": "plugin-1", "package_name": "demo", "deck_ref_count": 2}],
        "permissions": {"can_manage_shared_plugins": True},
    }
    assert operations.status_code == 200
    assert operations.json()["operations"] == [
        {
            "id": "op-1",
            "operation_kind": "install",
            "requested_package_spec": "demo@market",
            "status": "ready",
        }
    ]


def test_shared_plugin_manager_capability_is_reported() -> None:
    with (
        mock.patch.object(claude_plugins.database, "get_db", return_value=_Db()),
        mock.patch.object(claude_plugins, "PluginInstallService", _InstallService),
    ):
        response = _client({"user_id": 1, "permissions": ["plugin:admin"]}).get(
            "/api/claude-plugins/installations"
        )

    assert response.status_code == 200
    assert response.json()["permissions"] == {"can_manage_shared_plugins": True}


def test_all_signed_in_users_receive_the_same_platform_global_marketplace() -> None:
    marketplace = mock.Mock()
    marketplace.list_entries.return_value = [
        {"id": "cpme_comfy", "package_spec": "comfy-cloud@comfy-skills"}
    ]
    with (
        mock.patch.object(claude_plugins.database, "get_db", return_value=_Db()),
        mock.patch.object(
            claude_plugins, "MarketplaceCatalogService", return_value=marketplace
        ),
    ):
        first = _client({"user_id": 1, "role": "user"}).get(
            "/api/claude-plugins/marketplace"
        )
        second = _client({"user_id": 99, "role": "user"}).get(
            "/api/claude-plugins/marketplace"
        )

    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.json()["scope"] == "platform-global"


def test_marketplace_install_accepts_entry_id_and_queues_the_public_pipeline() -> None:
    source = MarketplaceInstallSource(
        entry_id="cpme_comfy",
        package_spec="comfy-cloud@comfy-skills",
        package_name="comfy-cloud",
        marketplace_name="comfy-skills",
        remote_url="https://github.com/Comfy-Org/comfy-skills",
        requested_ref=None,
        approved_commit_sha="a" * 40,
        marketplace_manifest_sha256="b" * 64,
        plugin_manifest_sha256="c" * 64,
        approved_plugin_digest="sha256:" + "d" * 64,
        compatibility={},
    )
    marketplace = mock.Mock()
    marketplace.resolve_install_source.return_value = source
    run_install = mock.Mock()
    with (
        mock.patch.object(claude_plugins.database, "get_db", return_value=_Db()),
        mock.patch.object(
            claude_plugins, "MarketplaceCatalogService", return_value=marketplace
        ),
        mock.patch.object(claude_plugins, "_run_install", run_install),
    ):
        response = _client({"user_id": 7, "role": "user"}).post(
            "/api/claude-plugins/install",
            json={"marketplace_entry_id": "cpme_comfy"},
        )

    assert response.status_code == 202
    assert response.json()["package_spec"] == "comfy-cloud@comfy-skills"
    assert response.json()["marketplace_entry_id"] == "cpme_comfy"
    run_install.assert_called_once_with(
        response.json()["operation_id"],
        "comfy-cloud@comfy-skills",
        "marketplace",
        "cpme_comfy",
    )


def test_background_crash_finishes_the_public_operation_as_error() -> None:
    db = _BackgroundDb()
    service = mock.Mock()
    service.install.side_effect = RuntimeError("provider exploded")
    with (
        mock.patch.object(claude_plugins.database, "get_db", return_value=db),
        mock.patch.object(claude_plugins, "PluginInstallService", return_value=service),
    ):
        claude_plugins._run_install(
            "cop_failed",
            "demo@market",
            "marketplace",
        )

    assert db.error_update is not None
    assert db.error_update[1] == "CLAUDE_PLUGIN_INSTALL_FAILED"
    assert "provider exploded" not in db.error_update[2]
    assert db.error_update[-1] == "cop_failed"
    assert db.commits == 1


def test_deck_owner_can_replace_only_own_deck_plugin_refs() -> None:
    """Shared installation is admin-owned, but a Deck owner owns its bindings."""
    service = mock.Mock()
    service.replace_refs.return_value = [{"deck_id": "deck-7", "plugin_installation_id": "plugin-1"}]
    with (
        mock.patch.object(claude_plugins.database, "get_db", return_value=_Db()),
        mock.patch.object(claude_plugins, "DeckPluginRefService", return_value=service),
    ):
        response = _client({"user_id": 7, "role": "user"}).put(
            "/api/decks/deck-7/claude-plugins",
            json={"refs": [{"plugin_installation_id": "plugin-1", "enabled": True, "order_index": 0}]},
        )

    assert response.status_code == 200
    service.replace_refs.assert_called_once_with(
        "deck-7",
        "7",
        [{"plugin_installation_id": "plugin-1", "enabled": True, "order_index": 0}],
    )
