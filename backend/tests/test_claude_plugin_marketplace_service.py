"""Remote Marketplace catalog and approved-entry resolution contracts.

[Input] Production MarketplaceCatalogService with PostgreSQL-shaped fake rows.
[Output] Evidence for one global projection, ref/commit/manifest/full-digest receipts, and fail-closed capability behavior.
[Pos] Focused backend unit tests for Admin-owned ClaudePlugin Marketplace consumption.
[Sync] 2026-08-19: add global catalog success plus missing/wrong-contract capability failure coverage.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.claude_plugin.marketplace_service import (
    MARKETPLACE_CAPABILITY_MISSING,
    MarketplaceCatalogError,
    MarketplaceCatalogService,
)
from schema.capabilities import CLAUDE_PLUGIN_REMOTE_MARKETPLACE_CONTRACT_SHA256


class _Cursor:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)


class _Db:
    def __init__(
        self,
        *,
        capability: bool = True,
        contract_hash: str = CLAUDE_PLUGIN_REMOTE_MARKETPLACE_CONTRACT_SHA256,
    ) -> None:
        self.capability = capability
        self.contract_hash = contract_hash

    def execute(self, sql: str, params=()):
        if "drizzle.schema_capabilities" in sql:
            return _Cursor(
                [
                    {
                        "version": 1,
                        "contract_sha256": self.contract_hash,
                    }
                ]
                if self.capability
                else []
            )
        if "WHERE entry.id = %s" in sql:
            return _Cursor(
                [
                    {
                        "id": params[0],
                        "package_spec": "comfy-cloud@comfy-skills",
                        "package_name": "comfy-cloud",
                        "marketplace_name": "comfy-skills",
                        "plugin_manifest_sha256": "b" * 64,
                        "plugin_digest": "sha256:" + "e" * 64,
                        "compatibility_json": {},
                        "resolved_commit_sha": "c" * 40,
                        "requested_ref": "main",
                        "marketplace_manifest_sha256": "d" * 64,
                        "remote_url": "https://github.com/Comfy-Org/comfy-skills",
                    }
                ]
            )
        if "ORDER BY marketplace.display_name" in sql:
            return _Cursor(
                [
                    {
                        "id": "cpme_comfy",
                        "package_name": "comfy-cloud",
                        "marketplace_name": "comfy-skills",
                        "package_spec": "comfy-cloud@comfy-skills",
                        "display_name": "comfy-cloud",
                        "description": "Comfy Cloud",
                        "version": "0.1.0",
                        "homepage": "https://docs.comfy.org/cloud/mcp",
                        "component_inventory_json": {"commands": 12, "mcpServers": 1},
                        "compatibility_json": {},
                        "plugin_manifest_sha256": "b" * 64,
                        "plugin_digest": "sha256:" + "e" * 64,
                        "revision_id": "cpmr_comfy",
                        "resolved_commit_sha": "c" * 40,
                        "requested_ref": "main",
                        "marketplace_manifest_sha256": "d" * 64,
                        "marketplace_id": "cpm_comfy",
                        "marketplace_display_name": "Comfy Skills",
                        "remote_url": "https://github.com/Comfy-Org/comfy-skills",
                        "installation_id": None,
                        "installation_status": None,
                        "installed_version": None,
                    }
                ]
            )
        raise AssertionError(f"unexpected SQL: {sql}")


def test_every_authenticated_user_reads_the_same_global_catalog_projection() -> None:
    service = MarketplaceCatalogService(_Db())

    first_read = service.list_entries()
    second_read = service.list_entries()

    assert first_read == second_read
    assert first_read[0]["package_spec"] == "comfy-cloud@comfy-skills"
    assert first_read[0]["component_inventory"] == {"commands": 12, "mcpServers": 1}
    assert first_read[0]["installation"] is None


def test_approved_entry_resolves_remote_revision_and_manifest_lineage() -> None:
    source = MarketplaceCatalogService(_Db()).resolve_install_source("cpme_comfy")

    assert source.entry_id == "cpme_comfy"
    assert source.package_spec == "comfy-cloud@comfy-skills"
    assert source.approved_commit_sha == "c" * 40
    assert source.requested_ref == "main"
    assert source.marketplace_manifest_sha256 == "d" * 64
    assert source.plugin_manifest_sha256 == "b" * 64
    assert source.approved_plugin_digest == "sha256:" + "e" * 64


def test_catalog_fails_closed_without_admin_capability() -> None:
    with pytest.raises(MarketplaceCatalogError) as caught:
        MarketplaceCatalogService(_Db(capability=False)).list_entries()

    assert caught.value.code == MARKETPLACE_CAPABILITY_MISSING


def test_catalog_fails_closed_when_admin_contract_hash_does_not_match() -> None:
    with pytest.raises(MarketplaceCatalogError) as caught:
        MarketplaceCatalogService(_Db(contract_hash="0" * 64)).list_entries()

    assert caught.value.code == MARKETPLACE_CAPABILITY_MISSING
