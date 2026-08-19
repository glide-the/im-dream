"""Global, Admin-owned ClaudePlugin Remote Marketplace catalog.

[Input] Admin Drizzle capability plus approved immutable marketplace revisions.
[Output] One shared Dream catalog and install-safe ref/commit/manifest/full-digest source receipts.
[Pos] Read-only application boundary between Admin marketplace governance and the real install pipeline.
[Sync] 2026-08-19: require the exact capability hash and resolve full remote installation lineage.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Final

try:
    from backend.schema.capabilities import (
        CLAUDE_PLUGIN_REMOTE_MARKETPLACE_CAPABILITY,
        CLAUDE_PLUGIN_REMOTE_MARKETPLACE_CONTRACT_SHA256,
    )
except ModuleNotFoundError:  # pragma: no cover - backend PYTHONPATH compatibility
    from schema.capabilities import (
        CLAUDE_PLUGIN_REMOTE_MARKETPLACE_CAPABILITY,
        CLAUDE_PLUGIN_REMOTE_MARKETPLACE_CONTRACT_SHA256,
    )


MARKETPLACE_CAPABILITY_MISSING: Final = (
    "CLAUDE_PLUGIN_MARKETPLACE_CAPABILITY_MISSING"
)
MARKETPLACE_ENTRY_NOT_FOUND: Final = "CLAUDE_PLUGIN_MARKETPLACE_ENTRY_NOT_FOUND"
MARKETPLACE_ENTRY_UNAVAILABLE: Final = (
    "CLAUDE_PLUGIN_MARKETPLACE_ENTRY_UNAVAILABLE"
)
MARKETPLACE_REMOTE_DRIFT: Final = "CLAUDE_PLUGIN_MARKETPLACE_REMOTE_DRIFT"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_PLUGIN_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_REMOTE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,254}$")


class MarketplaceCatalogError(RuntimeError):
    """Stable fail-closed error from the shared remote catalog."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class MarketplaceInstallSource:
    """Immutable facts rechecked immediately before a real CLI install."""

    entry_id: str
    package_spec: str
    package_name: str
    marketplace_name: str
    remote_url: str
    requested_ref: str | None
    approved_commit_sha: str
    marketplace_manifest_sha256: str
    plugin_manifest_sha256: str | None
    approved_plugin_digest: str
    compatibility: dict[str, Any]


def remote_marketplace_capability_available(db: Any) -> bool:
    """Check the exact Admin-owned capability without issuing any DDL."""

    try:
        row = db.execute(
            "SELECT version, contract_sha256 "
            "FROM drizzle.schema_capabilities WHERE capability = %s",
            (CLAUDE_PLUGIN_REMOTE_MARKETPLACE_CAPABILITY,),
        ).fetchone()
    except Exception:
        return False
    if row is None:
        return False
    contract_hash = str(row["contract_sha256"])
    return (
        int(row["version"]) >= 1
        and contract_hash == CLAUDE_PLUGIN_REMOTE_MARKETPLACE_CONTRACT_SHA256
    )


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


class MarketplaceCatalogService:
    """Read the one platform-global catalog visible to every Dream user."""

    def __init__(self, db: Any) -> None:
        self.db = db

    def _require_capability(self) -> None:
        if not remote_marketplace_capability_available(self.db):
            raise MarketplaceCatalogError(
                MARKETPLACE_CAPABILITY_MISSING,
                "Remote Marketplace capability is not available",
            )

    def list_entries(self) -> list[dict[str, Any]]:
        self._require_capability()
        rows = self.db.execute(
            """
            SELECT entry.id, entry.package_name, entry.marketplace_name,
                   entry.package_spec, entry.display_name, entry.description,
                   entry.version, entry.homepage, entry.component_inventory_json,
                   entry.compatibility_json, entry.plugin_manifest_sha256,
                   entry.plugin_digest,
                   revision.id AS revision_id,
                   revision.resolved_commit_sha,
                   revision.requested_ref,
                   revision.manifest_sha256 AS marketplace_manifest_sha256,
                   marketplace.id AS marketplace_id,
                   marketplace.display_name AS marketplace_display_name,
                   marketplace.remote_url,
                   installation.id AS installation_id,
                   installation.status AS installation_status,
                   installation.resolved_version AS installed_version
            FROM claude_plugin_marketplace_entry_policies AS policy
            JOIN claude_plugin_marketplace_entries AS entry
              ON entry.id = policy.approved_entry_id
             AND entry.marketplace_id = policy.marketplace_id
             AND entry.package_name = policy.package_name
            JOIN claude_plugin_marketplace_revisions AS revision
              ON revision.id = entry.revision_id
            JOIN claude_plugin_marketplaces AS marketplace
              ON marketplace.id = entry.marketplace_id
            LEFT JOIN LATERAL (
              SELECT current_installation.id, current_installation.status,
                     current_installation.resolved_version
              FROM claude_plugin_installations AS current_installation
              WHERE current_installation.package_name = entry.package_name
                AND current_installation.marketplace = entry.marketplace_name
                AND current_installation.status = 'ready'
                AND (
                  current_installation.marketplace_entry_id = entry.id
                  OR current_installation.artifact_digest = entry.plugin_digest
                )
              ORDER BY current_installation.installed_at DESC NULLS LAST,
                       current_installation.created_at DESC,
                       current_installation.id DESC
              LIMIT 1
            ) AS installation ON TRUE
            WHERE policy.decision = 'approved'
              AND entry.validation_status = 'valid'
              AND revision.validation_status = 'valid'
              AND marketplace.status = 'active'
            ORDER BY marketplace.display_name, entry.display_name, entry.package_name
            """
        ).fetchall()
        return [
            {
                "id": str(row["id"]),
                "package_name": str(row["package_name"]),
                "marketplace_name": str(row["marketplace_name"]),
                "package_spec": str(row["package_spec"]),
                "display_name": str(row["display_name"]),
                "description": row["description"],
                "version": row["version"],
                "homepage": row["homepage"],
                "component_inventory": _json_object(
                    row["component_inventory_json"]
                ),
                "compatibility": _json_object(row["compatibility_json"]),
                "revision": {
                    "id": str(row["revision_id"]),
                    "commit_sha": str(row["resolved_commit_sha"]),
                    "marketplace_manifest_sha256": str(
                        row["marketplace_manifest_sha256"]
                    ),
                    "plugin_manifest_sha256": row["plugin_manifest_sha256"],
                    "plugin_digest": str(row["plugin_digest"]),
                    "requested_ref": row["requested_ref"],
                },
                "marketplace": {
                    "id": str(row["marketplace_id"]),
                    "display_name": str(row["marketplace_display_name"]),
                    "remote_url": str(row["remote_url"]),
                },
                "installation": (
                    {
                        "id": str(row["installation_id"]),
                        "status": str(row["installation_status"]),
                        "resolved_version": str(row["installed_version"]),
                    }
                    if row["installation_id"] is not None
                    else None
                ),
            }
            for row in rows
        ]

    def resolve_install_source(self, entry_id: str) -> MarketplaceInstallSource:
        self._require_capability()
        row = self.db.execute(
            """
            SELECT entry.id, entry.package_spec, entry.package_name,
                   entry.marketplace_name, entry.plugin_manifest_sha256,
                   entry.plugin_digest, entry.compatibility_json,
                   revision.resolved_commit_sha,
                   revision.requested_ref,
                   revision.manifest_sha256 AS marketplace_manifest_sha256,
                   marketplace.remote_url
            FROM claude_plugin_marketplace_entry_policies AS policy
            JOIN claude_plugin_marketplace_entries AS entry
              ON entry.id = policy.approved_entry_id
             AND entry.marketplace_id = policy.marketplace_id
             AND entry.package_name = policy.package_name
            JOIN claude_plugin_marketplace_revisions AS revision
              ON revision.id = entry.revision_id
            JOIN claude_plugin_marketplaces AS marketplace
              ON marketplace.id = entry.marketplace_id
            WHERE entry.id = %s
              AND policy.decision = 'approved'
              AND entry.validation_status = 'valid'
              AND revision.validation_status = 'valid'
              AND marketplace.status = 'active'
            """,
            (entry_id,),
        ).fetchone()
        if row is None:
            exists = self.db.execute(
                "SELECT 1 FROM claude_plugin_marketplace_entries WHERE id = %s",
                (entry_id,),
            ).fetchone()
            raise MarketplaceCatalogError(
                (
                    MARKETPLACE_ENTRY_UNAVAILABLE
                    if exists is not None
                    else MARKETPLACE_ENTRY_NOT_FOUND
                ),
                "Marketplace entry is not approved and active",
            )
        commit_sha = str(row["resolved_commit_sha"])
        marketplace_manifest_sha = str(row["marketplace_manifest_sha256"])
        plugin_manifest_sha = row["plugin_manifest_sha256"]
        plugin_digest = str(row["plugin_digest"])
        requested_ref = row["requested_ref"]
        if (
            not _COMMIT_SHA.fullmatch(commit_sha)
            or not _SHA256.fullmatch(marketplace_manifest_sha)
            or not _PLUGIN_DIGEST.fullmatch(plugin_digest)
            or (
                plugin_manifest_sha is not None
                and not _SHA256.fullmatch(str(plugin_manifest_sha))
            )
            or (
                requested_ref is not None
                and (
                    not _REMOTE_REF.fullmatch(str(requested_ref))
                    or ".." in str(requested_ref)
                    or "//" in str(requested_ref)
                    or "@{" in str(requested_ref)
                    or str(requested_ref).endswith(("/", "."))
                    or any(
                        segment.endswith(".lock")
                        for segment in str(requested_ref).split("/")
                    )
                )
            )
        ):
            raise MarketplaceCatalogError(
                MARKETPLACE_ENTRY_UNAVAILABLE,
                "Marketplace entry provenance is invalid",
            )
        return MarketplaceInstallSource(
            entry_id=str(row["id"]),
            package_spec=str(row["package_spec"]),
            package_name=str(row["package_name"]),
            marketplace_name=str(row["marketplace_name"]),
            remote_url=str(row["remote_url"]),
            requested_ref=(
                str(requested_ref) if requested_ref is not None else None
            ),
            approved_commit_sha=commit_sha,
            marketplace_manifest_sha256=marketplace_manifest_sha,
            plugin_manifest_sha256=(
                str(plugin_manifest_sha) if plugin_manifest_sha is not None else None
            ),
            approved_plugin_digest=plugin_digest,
            compatibility=_json_object(row["compatibility_json"]),
        )


__all__ = [
    "MARKETPLACE_CAPABILITY_MISSING",
    "MARKETPLACE_ENTRY_NOT_FOUND",
    "MARKETPLACE_ENTRY_UNAVAILABLE",
    "MARKETPLACE_REMOTE_DRIFT",
    "MarketplaceCatalogError",
    "MarketplaceCatalogService",
    "MarketplaceInstallSource",
    "remote_marketplace_capability_available",
]
