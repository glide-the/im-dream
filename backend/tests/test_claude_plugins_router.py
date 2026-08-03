"""Route-level authorization contracts for shared Claude Code plugins."""

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


class _Cursor:
    def __init__(self, rows: list[tuple], columns: list[str] | None = None) -> None:
        self._rows = rows
        self.description = [(column,) for column in columns] if columns else None

    def fetchall(self) -> list[tuple]:
        return self._rows


class _Db:
    def execute(self, sql: str, _params: object = ()) -> _Cursor:
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


class _InstallService:
    def __init__(self, _db: _Db) -> None:
        pass

    def list_installations(self) -> list[dict[str, object]]:
        return [{"id": "plugin-1", "package_name": "demo"}]


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
