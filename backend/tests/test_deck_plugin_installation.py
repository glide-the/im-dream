"""Tests for the Deck Plugin Installation lifecycle foundation."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import hashlib
import json
import sqlite3
import unittest
import uuid

from backend import database
from backend.schema import legacy_main_sqlite
from backend.models.deck_plugin import (
    DeckPluginInstallation,
    DeckPluginManifestV1,
    DeckRuntimePluginLock,
    InstallationStatus,
    RuntimePluginLockEntry,
)
from backend.services.deck_plugin.installation_service import (
    DECK_PLUGIN_CONCURRENT_MODIFICATION,
    DECK_PLUGIN_INSTALLATION_CONFLICT,
    DECK_PLUGIN_INVALID_TRANSITION,
    DECK_PLUGIN_PURGE_RETENTION_BLOCKED,
    DECK_PLUGIN_ROLLBACK_BLOCKED,
    DECK_PLUGIN_RUNTIME_NOT_READY,
    InstallResult,
    InstallationService,
    InstallationServiceError,
    RuntimePreparation,
    Scope,
    assert_installation_transition,
)
from backend.tests.test_deck_plugin_manifest import valid_manifest_data


PLUGIN_ID = "voice-decks.story-dramatize"
DIGEST = "sha256:" + "d" * 64


def ready_preparer(_plugin_id, _version, _runtime_lock):
    return RuntimePreparation(
        runtime_readiness="ready_non_production",
        lock_materialized=True,
        load_smoke_passed=True,
    )


class InstallationLifecycleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        legacy_main_sqlite.create_tables(self.db)
        self.add_release("3.1.0")
        self.service = InstallationService(self.db, runtime_preparer=ready_preparer)

    def tearDown(self):
        self.db.close()

    def add_release(
        self,
        version: str,
        *,
        capabilities: list[str] | None = None,
        artifact_digest: str = DIGEST,
    ) -> None:
        data = valid_manifest_data()
        data["deck_plugin_version"] = version
        data["status"] = "published"
        data["workflow"]["workflow_definition_ref"] = (
            f"deck://{PLUGIN_ID}/{version}/workflow.json"
        )
        if capabilities is not None:
            data["capabilities"] = capabilities
            data["workflow"]["steps"] = [
                {"step_id": "run", "required_capabilities": capabilities[:1]}
            ]
            data["runtime"]["claude_code_plugins"][0]["capability_bindings"] = (
                capabilities[:1]
            )
        manifest = DeckPluginManifestV1.model_validate(data)
        manifest_hash = "sha256:" + hashlib.sha256(
            manifest.model_dump_json().encode("utf-8")
        ).hexdigest()
        runtime_lock = DeckRuntimePluginLock(
            runtime_plugin_lock_id=f"rpl_{uuid.uuid4().hex}",
            deck_plugin_id=PLUGIN_ID,
            deck_plugin_version=version,
            deck_plugin_manifest_hash=manifest_hash,
            claude_code_plugins=[
                RuntimePluginLockEntry(
                    claude_code_plugin_id="ink-dream-tools@voice-decks",
                    resolved_version="1.4.2",
                    source_ref="marketplace://voice-decks@2026-08-01",
                    artifact_digest=artifact_digest,
                    required=True,
                    capability_bindings=data["runtime"]["claude_code_plugins"][0][
                        "capability_bindings"
                    ],
                )
            ],
            created_at=datetime.now(UTC),
            production_ready=False,
            production_readiness_reasons=[
                "production supply-chain gate has not passed"
            ],
        )
        with self.db:
            self.db.execute(
                """
                INSERT INTO deck_plugin_releases (
                    id, deck_plugin_id, deck_plugin_version, display_name,
                    status, manifest_json, manifest_hash, workflow_definition_ref,
                    capabilities_json
                ) VALUES (?, ?, ?, ?, 'published', ?, ?, ?, ?)
                """,
                (
                    f"dr_{uuid.uuid4().hex}",
                    PLUGIN_ID,
                    version,
                    manifest.display_name,
                    manifest.model_dump_json(),
                    manifest_hash,
                    manifest.workflow.workflow_definition_ref,
                    json.dumps(manifest.capabilities),
                ),
            )
            self.db.execute(
                """
                INSERT INTO deck_runtime_plugin_locks (
                    id, deck_plugin_id, deck_plugin_version,
                    deck_plugin_manifest_hash, lock_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    runtime_lock.runtime_plugin_lock_id,
                    PLUGIN_ID,
                    version,
                    manifest_hash,
                    runtime_lock.model_dump_json(),
                ),
            )

    async def install_ready(
        self,
        *,
        scope_id: str = "workspace-1",
        version: str = "3.1.0",
        service: InstallationService | None = None,
    ) -> DeckPluginInstallation:
        lifecycle = service or self.service
        started = await lifecycle.install(
            PLUGIN_ID,
            version,
            Scope(scope_type="workspace", scope_id=scope_id),
            source_policy_id="policy-default",
        )
        self.assertIsInstance(started, InstallResult)
        self.assertEqual(started.status, InstallationStatus.INSTALLING)
        self.assertTrue(started.operation_id.startswith("op_"))
        self.assertEqual(started.runtime_readiness, "materializing")
        self.assertIn("story.context.read", started.capability_diff.added)
        completed = await lifecycle.complete_installation(
            started.deck_plugin_installation_id
        )
        self.assertEqual(completed.status, InstallationStatus.READY)
        return lifecycle.get(started.deck_plugin_installation_id)

    async def test_install_model_response_and_persisted_fields(self):
        installation = await self.install_ready()
        self.assertTrue(installation.deck_plugin_installation_id.startswith("dpi_"))
        self.assertEqual(installation.scope_type, "workspace")
        self.assertEqual(installation.scope_id, "workspace-1")
        self.assertEqual(installation.installed_versions, ["3.1.0"])
        self.assertEqual(installation.default_version, "3.1.0")
        self.assertEqual(installation.status, InstallationStatus.READY)
        self.assertEqual(installation.source_policy_id, "policy-default")
        self.assertIsNone(installation.last_error_code)
        self.assertIsNotNone(installation.created_at)
        self.assertIsNotNone(installation.updated_at)

    async def test_legal_transitions_invalid_transition_and_terminal_state(self):
        installation = await self.install_ready()
        disabled = await self.service.disable(
            installation.deck_plugin_installation_id, "maintenance"
        )
        self.assertEqual(disabled.status, InstallationStatus.DISABLED)
        ready = await self.service.enable(installation.deck_plugin_installation_id)
        self.assertEqual(ready.status, InstallationStatus.READY)
        with self.assertRaises(InstallationServiceError) as caught:
            await self.service.enable(installation.deck_plugin_installation_id)
        self.assertEqual(caught.exception.code, DECK_PLUGIN_INVALID_TRANSITION)

        removed = await self.service.uninstall(installation.deck_plugin_installation_id)
        self.assertEqual(removed.status, InstallationStatus.UNINSTALLED)
        with self.assertRaises(InstallationServiceError):
            await self.service.enable(installation.deck_plugin_installation_id)
        with self.assertRaises(InstallationServiceError):
            assert_installation_transition(
                InstallationStatus.UNINSTALLED, InstallationStatus.READY
            )

    async def test_install_error_and_retry_recovery(self):
        attempts = 0

        async def prepare(_plugin_id, _version, _runtime_lock):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                return RuntimePreparation(
                    runtime_readiness="load_failed",
                    lock_materialized=True,
                    load_smoke_passed=False,
                    error_code=DECK_PLUGIN_RUNTIME_NOT_READY,
                    error_summary="load smoke failed",
                )
            return RuntimePreparation(
                runtime_readiness="ready_non_production",
                lock_materialized=True,
                load_smoke_passed=True,
            )

        service = InstallationService(self.db, runtime_preparer=prepare)
        started = await service.install(
            PLUGIN_ID,
            "3.1.0",
            Scope(scope_type="instance", scope_id="instance-retry"),
        )
        with self.assertRaises(InstallationServiceError) as caught:
            await service.complete_installation(started.deck_plugin_installation_id)
        self.assertEqual(caught.exception.code, DECK_PLUGIN_RUNTIME_NOT_READY)
        self.assertEqual(
            caught.exception.to_dict()["error"]["code"],
            DECK_PLUGIN_RUNTIME_NOT_READY,
        )
        self.assertEqual(
            service.get(started.deck_plugin_installation_id).status,
            InstallationStatus.ERROR,
        )
        retried = await service.retry(started.deck_plugin_installation_id)
        self.assertEqual(retried.status, InstallationStatus.INSTALLING)
        recovered = await service.complete_installation(
            started.deck_plugin_installation_id
        )
        self.assertEqual(recovered.status, InstallationStatus.READY)

    async def test_capability_expansion_requires_approval_before_switch(self):
        installation = await self.install_ready()
        expanded = [*installation.approved_capabilities, "network.external.call"]
        self.add_release("3.2.0", capabilities=expanded)

        pending = await self.service.upgrade(
            installation.deck_plugin_installation_id, "3.2.0"
        )
        self.assertEqual(pending.status, InstallationStatus.UPGRADE_PENDING)
        self.assertEqual(pending.capability_diff.added, ["network.external.call"])
        before_approval = self.service.get(installation.deck_plugin_installation_id)
        self.assertEqual(before_approval.default_version, "3.1.0")
        self.assertEqual(before_approval.installed_versions, ["3.1.0"])

        upgraded = await self.service.approve_upgrade(
            installation.deck_plugin_installation_id
        )
        self.assertEqual(upgraded.status, InstallationStatus.READY)
        after_approval = self.service.get(installation.deck_plugin_installation_id)
        self.assertEqual(after_approval.default_version, "3.2.0")
        self.assertEqual(after_approval.installed_versions, ["3.1.0", "3.2.0"])

    async def test_failed_upgrade_preserves_old_ready_version(self):
        installation = await self.install_ready()
        self.add_release("3.2.0", capabilities=installation.approved_capabilities)

        async def fail_target(_plugin_id, version, _runtime_lock):
            if version == "3.2.0":
                return RuntimePreparation(
                    runtime_readiness="load_failed",
                    lock_materialized=True,
                    load_smoke_passed=False,
                    error_code=DECK_PLUGIN_RUNTIME_NOT_READY,
                    error_summary="target load smoke failed",
                )
            return RuntimePreparation(
                runtime_readiness="ready_non_production",
                lock_materialized=True,
                load_smoke_passed=True,
            )

        self.service._runtime_preparer = fail_target
        with self.assertRaises(InstallationServiceError):
            await self.service.upgrade(
                installation.deck_plugin_installation_id, "3.2.0"
            )
        preserved = self.service.get(installation.deck_plugin_installation_id)
        self.assertEqual(preserved.status, InstallationStatus.READY)
        self.assertEqual(preserved.default_version, "3.1.0")
        self.assertEqual(preserved.installed_versions, ["3.1.0"])
        self.assertEqual(preserved.last_error_code, DECK_PLUGIN_RUNTIME_NOT_READY)

    async def test_rollback_is_explicit_and_does_not_rewrite_historical_runs(self):
        installation = await self.install_ready()
        self.add_release("3.2.0", capabilities=installation.approved_capabilities)
        await self.service.upgrade(
            installation.deck_plugin_installation_id, "3.2.0"
        )
        historical_runs = {"run-1": "3.1.0", "run-2": "3.2.0"}

        rolled_back = await self.service.rollback(
            installation.deck_plugin_installation_id, "3.1.0"
        )
        self.assertEqual(rolled_back.default_version, "3.1.0")
        self.assertEqual(rolled_back.installed_versions, ["3.1.0", "3.2.0"])
        self.assertEqual(historical_runs, {"run-1": "3.1.0", "run-2": "3.2.0"})

        with self.assertRaises(InstallationServiceError) as caught:
            await self.service.rollback(
                installation.deck_plugin_installation_id, "3.0.0"
            )
        self.assertEqual(caught.exception.code, DECK_PLUGIN_ROLLBACK_BLOCKED)
        self.assertEqual(
            self.service.get(installation.deck_plugin_installation_id).default_version,
            "3.1.0",
        )

    async def test_rollback_requires_verified_digest(self):
        self.add_release(
            "3.0.0",
            capabilities=valid_manifest_data()["capabilities"],
            artifact_digest="",
        )
        installation = await self.install_ready(
            scope_id="digest-rollback", version="3.0.0"
        )
        await self.service.upgrade(
            installation.deck_plugin_installation_id, "3.1.0"
        )
        with self.assertRaises(InstallationServiceError) as caught:
            await self.service.rollback(
                installation.deck_plugin_installation_id, "3.0.0"
            )
        self.assertEqual(caught.exception.code, DECK_PLUGIN_ROLLBACK_BLOCKED)

    async def test_soft_uninstall_retains_history_and_force_purge_requires_proof(self):
        soft = await self.install_ready(scope_id="soft")
        removed = await self.service.uninstall(soft.deck_plugin_installation_id)
        self.assertEqual(removed.status, InstallationStatus.UNINSTALLED)
        self.assertEqual(
            self.service.get(soft.deck_plugin_installation_id).installed_versions,
            ["3.1.0"],
        )

        force_candidate = await self.install_ready(scope_id="force-blocked")
        with self.assertRaises(InstallationServiceError) as caught:
            await self.service.uninstall(force_candidate.deck_plugin_installation_id, True)
        self.assertEqual(caught.exception.code, DECK_PLUGIN_PURGE_RETENTION_BLOCKED)

        purge_service = InstallationService(
            self.db,
            runtime_preparer=ready_preparer,
            retention_checker=lambda _installation: True,
        )
        purged = await purge_service.uninstall(
            force_candidate.deck_plugin_installation_id, True
        )
        self.assertEqual(purged.status, InstallationStatus.UNINSTALLED)
        with self.assertRaises(InstallationServiceError):
            purge_service.get(force_candidate.deck_plugin_installation_id)

    async def test_concurrent_install_has_one_winner_and_structured_conflict(self):
        scope = Scope(scope_type="workspace", scope_id="concurrent")
        outcomes = await asyncio.gather(
            self.service.install(PLUGIN_ID, "3.1.0", scope),
            self.service.install(PLUGIN_ID, "3.1.0", scope),
            return_exceptions=True,
        )
        successes = [item for item in outcomes if isinstance(item, InstallResult)]
        failures = [item for item in outcomes if isinstance(item, InstallationServiceError)]
        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0].code, DECK_PLUGIN_INSTALLATION_CONFLICT)
        self.assertIn("operation_id", failures[0].to_dict()["error"])

    async def test_overlapping_upgrades_return_deterministic_conflict(self):
        installation = await self.install_ready()
        self.add_release("3.2.0", capabilities=installation.approved_capabilities)
        self.add_release("3.3.0", capabilities=installation.approved_capabilities)
        started = asyncio.Event()
        release = asyncio.Event()

        async def slow_prepare(_plugin_id, version, _runtime_lock):
            if version == "3.2.0":
                started.set()
                await release.wait()
            return RuntimePreparation(
                runtime_readiness="ready_non_production",
                lock_materialized=True,
                load_smoke_passed=True,
            )

        self.service._runtime_preparer = slow_prepare
        first = asyncio.create_task(
            self.service.upgrade(installation.deck_plugin_installation_id, "3.2.0")
        )
        await started.wait()
        with self.assertRaises(InstallationServiceError) as caught:
            await self.service.upgrade(
                installation.deck_plugin_installation_id, "3.3.0"
            )
        self.assertEqual(caught.exception.code, DECK_PLUGIN_CONCURRENT_MODIFICATION)
        self.assertTrue(caught.exception.retryable)
        release.set()
        await first
        self.assertEqual(
            self.service.get(installation.deck_plugin_installation_id).default_version,
            "3.2.0",
        )

    async def test_database_constraints_indexes_and_idempotent_initialization(self):
        legacy_main_sqlite.create_tables(self.db)
        indexes = {
            row["name"]
            for row in self.db.execute(
                "PRAGMA index_list('deck_plugin_installations')"
            )
        }
        self.assertIn("idx_installations_deck_plugin", indexes)
        self.assertIn("idx_installations_scope", indexes)
        self.assertIn("idx_installations_status", indexes)
        self.assertTrue(
            any(
                row["unique"]
                for row in self.db.execute(
                    "PRAGMA index_list('deck_plugin_installations')"
                )
            )
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                """
                INSERT INTO deck_plugin_installations (
                    id, scope_type, scope_id, deck_plugin_id, source_policy_id
                ) VALUES ('dpi_bad', 'global', 'scope', 'plugin.id', 'policy')
                """
            )


if __name__ == "__main__":
    unittest.main()
