"""Resolve and reconcile the configured screenplay Deck Claude plugin.

[Input] Product Deck defaults, verified Claude plugin installations, and Deck
        persistence helpers.
[Output] Provide one reusable policy boundary for new Deck provisioning and
         idempotent repair of untouched default screenplay Decks with no refs.
[Pos] Deck-default application service in backend/services/deck.
[Sync] 2026-08-14: centralize drama-forge resolution and default-Deck repair.
"""

from __future__ import annotations

from typing import Any

try:
    import config
    import database
    from services.claude_plugin.install_service import PluginInstallService
except ModuleNotFoundError:  # pragma: no cover - package import compatibility
    from backend import config, database
    from backend.services.claude_plugin.install_service import PluginInstallService


class DefaultDeckPluginUnavailable(RuntimeError):
    """The configured Deck plugin has no verified ready installation."""


def resolve_default_deck_plugin_ref() -> dict[str, Any]:
    """Resolve the configured package/version after integrity checks."""

    package_name = config.DEFAULT_DECK_CLAUDE_PLUGIN_PACKAGE_NAME
    resolved_version = config.DEFAULT_DECK_CLAUDE_PLUGIN_VERSION
    if not package_name or not resolved_version:
        raise DefaultDeckPluginUnavailable()

    db = database.get_db()
    try:
        service = PluginInstallService(db)
        installation = next(
            (
                item
                for item in service.list_installations()
                if item.get("package_name") == package_name
                and item.get("resolved_version") == resolved_version
                and item.get("status") == "ready"
            ),
            None,
        )
        if installation is None:
            raise DefaultDeckPluginUnavailable()
        if not service.verify_installation_artifact(installation):
            raise DefaultDeckPluginUnavailable()
        if not service.check_cli_compatibility(installation):
            raise DefaultDeckPluginUnavailable()
        return {
            "plugin_installation_id": installation["id"],
            "package_name": installation["package_name"],
            "resolved_version": installation["resolved_version"],
            "artifact_digest": installation["artifact_digest"],
        }
    finally:
        db.close()


def provision_default_screenplay_deck(user_id: int) -> str:
    """Create the user's default screenplay Deck with its default plugin."""

    return database.auto_fork_system_decks(
        user_id,
        default_plugin_ref=resolve_default_deck_plugin_ref(),
    )


def reconcile_default_screenplay_deck_plugin(user_id: int) -> dict[str, Any]:
    """Repair only an untouched default Deck whose plugin refs are empty."""

    return database.reconcile_default_screenplay_deck_plugin_ref(
        user_id,
        default_plugin_ref=resolve_default_deck_plugin_ref(),
    )
