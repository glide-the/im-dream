"""Verify the Admin-selected screenplay Deck Claude plugin on shared storage.

[Input] Admin's closed six-field candidate plus the existing shared-artifact and CLI verifiers.
[Output] Return the four-field immutable evidence accepted by Admin Deck writes, or fail closed.
[Pos] Deck-default application service in backend/services/deck.
[Sync] 2026-08-14: centralize drama-forge resolution and default-Deck repair.
[Sync] 2026-08-15: default reconciliation now provisions a missing default for
                   legacy actors while preserving existing Decks and refs.
[Sync] 2026-09-15: remove Dream SQL/config selection; Admin selects and rechecks policy while Dream verifies local bytes/CLI.
"""

from __future__ import annotations

try:
    from services.claude_plugin.install_service import PluginInstallService
    from services.admin_data.deck_default_data import (
        DefaultPluginEvidenceDTO,
        DefaultPluginInstallationDTO,
    )
except ModuleNotFoundError:  # pragma: no cover - package import compatibility
    from backend.services.claude_plugin.install_service import PluginInstallService
    from backend.services.admin_data.deck_default_data import (
        DefaultPluginEvidenceDTO,
        DefaultPluginInstallationDTO,
    )


class DefaultDeckPluginUnavailable(RuntimeError):
    """The configured Deck plugin has no verified ready installation."""


def resolve_default_deck_plugin_ref(
    installation: DefaultPluginInstallationDTO | None,
) -> DefaultPluginEvidenceDTO:
    """Verify Admin's candidate against shared bytes and the current Claude CLI."""

    if installation is None:
        raise DefaultDeckPluginUnavailable()
    record = installation.model_dump()
    if not PluginInstallService.verify_installation_artifact(record):
        raise DefaultDeckPluginUnavailable()
    if not PluginInstallService.check_cli_compatibility(record):
        raise DefaultDeckPluginUnavailable()
    return DefaultPluginEvidenceDTO(
        plugin_installation_id=installation.plugin_installation_id,
        package_name=installation.package_name,
        resolved_version=installation.resolved_version,
        artifact_digest=installation.artifact_digest,
    )
