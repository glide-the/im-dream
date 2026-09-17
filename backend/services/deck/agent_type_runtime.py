"""Verify Admin-selected Agent-type Runtime artifacts on Dream shared storage.

[Input] Registry128 closed installation candidate and existing artifact/CLI verifiers.
[Output] Registry129 immutable evidence, or a closed Runtime-unavailable error.
[Pos] Local filesystem application service; it has no database client or persistence behavior.
[Sync] 2026-09-16: split local byte/manifest/CLI verification from Admin-owned Runtime metadata.
"""

from __future__ import annotations

try:
    from services.admin_data.deck_plugin_binding_data import (
        AgentTypeRuntimeCandidateDTO,
        AgentTypeVerifiedPluginDTO,
    )
    from services.claude_plugin import artifact_store
    from services.claude_plugin.install_service import (
        PluginInstallError,
        PluginInstallService,
        read_manifest,
    )
except ModuleNotFoundError:  # pragma: no cover - package import compatibility
    from backend.services.admin_data.deck_plugin_binding_data import (
        AgentTypeRuntimeCandidateDTO,
        AgentTypeVerifiedPluginDTO,
    )
    from backend.services.claude_plugin import artifact_store
    from backend.services.claude_plugin.install_service import (
        PluginInstallError,
        PluginInstallService,
        read_manifest,
    )


class AgentTypeRuntimeUnavailable(RuntimeError):
    """The selected immutable artifact cannot run on this Dream host."""


def verify_agent_type_runtime(
    candidate: AgentTypeRuntimeCandidateDTO,
) -> AgentTypeVerifiedPluginDTO:
    """Derive evidence from the configured shared artifact store and local CLI."""

    record = candidate.model_dump()
    if not PluginInstallService.verify_installation_artifact(record):
        raise AgentTypeRuntimeUnavailable()
    if not PluginInstallService.check_cli_compatibility(record):
        raise AgentTypeRuntimeUnavailable()
    try:
        artifact = artifact_store.get_artifact(
            candidate.package_name,
            candidate.marketplace,
            candidate.artifact_digest,
        )
        has_manifest = read_manifest(artifact.path) is not None
    except (artifact_store.ArtifactStoreError, PluginInstallError, OSError):
        raise AgentTypeRuntimeUnavailable() from None
    if not has_manifest:
        raise AgentTypeRuntimeUnavailable()
    return AgentTypeVerifiedPluginDTO(
        plugin_installation_id=candidate.plugin_installation_id,
        package_spec=candidate.package_spec,
        resolved_version=candidate.resolved_version,
        artifact_digest=candidate.artifact_digest,
        has_manifest=True,
    )
