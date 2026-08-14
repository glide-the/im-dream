"""Compatibility chain and least-privilege capability tests."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import sqlite3
import unittest

from pydantic import ValidationError

from backend import database
from backend.schema import legacy_main_sqlite
from backend.models.deck_plugin import (
    CapabilityDiff,
    CompatibilityCheck,
    CompatibilityResult,
    DeckPluginManifestV1,
    DeckRuntimePluginLock,
    InstallationStatus,
    RuntimePluginLockEntry,
)
from backend.services.deck_plugin.capability_evaluator import (
    compute_effective_capabilities,
)
from backend.services.deck_plugin.compatibility_service import (
    CAPABILITY_APPROVAL_DENIED,
    CLAUDE_AGENT_INCOMPATIBLE,
    DECK_HOST_INCOMPATIBLE,
    DECK_PLUGIN_UNAVAILABLE,
    DECK_RUNTIME_CONFIG_INCOMPATIBLE,
    RUNTIME_PLUGIN_NOT_READY,
    RUNTIME_PLUGIN_UNRESOLVED,
    STORY_SCHEMA_INCOMPATIBLE,
    WORKFLOW_PERMISSION_DENIED,
    CompatibilityService,
    CompatibilityServiceError,
    RuntimeContext,
)
from backend.services.deck_plugin.installation_service import Scope
from backend.tests.test_deck_plugin_manifest import valid_manifest_data


PLUGIN_ID = "voice-decks.story-dramatize"
VERSION = "3.1.0"
INSTALLATION_ID = "dpi_" + "1" * 32
RUNTIME_PLUGIN_ID = "ink-dream-tools@voice-decks"
DIGEST = "sha256:" + "d" * 64


class CapabilityEvaluatorTests(unittest.TestCase):
    def test_effective_capabilities_are_the_strict_five_domain_intersection(self):
        result = compute_effective_capabilities(
            {"story.context.read", "story.result.produce", "unknown.capability"},
            {"story.context.read", "story.result.produce", "unknown.capability"},
            {"story.context.read", "story.result.produce", "unknown.capability"},
            {"story.context.read", "story.result.produce", "unknown.capability"},
            {"story.context.read", "story.result.produce"},
        )
        self.assertEqual(
            result,
            {"story.context.read", "story.result.produce"},
        )

    def test_server_registry_can_only_narrow_runtime_supported_capabilities(self):
        common = {"story.context.read", "story.result.produce"}
        result = compute_effective_capabilities(
            common,
            common,
            common,
            common,
            common,
            known_capabilities={"story.context.read", "unknown.capability"},
        )
        self.assertEqual(result, {"story.context.read"})

    def test_result_and_diff_models_enforce_canonical_structured_output(self):
        failure = CompatibilityResult(
            passed=False,
            failed_check=CompatibilityCheck.DECK_HOST_COMPATIBLE,
            error_code=DECK_HOST_INCOMPATIBLE,
            recovery_action="upgrade_deck_host",
        )
        self.assertEqual(failure.model_dump()["effective_capabilities"], [])
        with self.assertRaises(ValidationError):
            CompatibilityResult(passed=False)
        with self.assertRaises(ValidationError):
            CompatibilityResult(
                passed=False,
                failed_check=CompatibilityCheck.DECK_HOST_COMPATIBLE,
                error_code=DECK_HOST_INCOMPATIBLE,
                recovery_action="upgrade_deck_host",
                effective_capabilities=["story.context.read"],
            )
        with self.assertRaises(ValidationError):
            CapabilityDiff(
                added=["b", "a"],
                removed=[],
                requires_approval=True,
            )


class CompatibilityServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        legacy_main_sqlite.create_tables(self.db)
        self.manifest, self.runtime_lock = self._seed_release_and_installation()
        self.service = CompatibilityService(
            self.db,
            administrator_authorizer=lambda actor: actor == "admin-1",
        )

    def tearDown(self):
        self.db.close()

    def _seed_release_and_installation(self):
        data = valid_manifest_data()
        data["status"] = "published"
        manifest = DeckPluginManifestV1.model_validate(data)
        manifest_hash = "sha256:" + hashlib.sha256(
            manifest.model_dump_json().encode("utf-8")
        ).hexdigest()
        runtime_lock = DeckRuntimePluginLock(
            runtime_plugin_lock_id="rpl_" + "2" * 32,
            deck_plugin_id=PLUGIN_ID,
            deck_plugin_version=VERSION,
            deck_plugin_manifest_hash=manifest_hash,
            claude_code_plugins=[
                RuntimePluginLockEntry(
                    claude_code_plugin_id=RUNTIME_PLUGIN_ID,
                    resolved_version="1.4.2",
                    source_ref="marketplace://voice-decks@2026-08-01",
                    artifact_digest=DIGEST,
                    required=True,
                    capability_bindings=[
                        "workspace.files.read",
                        "story.result.produce",
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
                    "dr_" + "3" * 32,
                    PLUGIN_ID,
                    VERSION,
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
                    VERSION,
                    manifest_hash,
                    runtime_lock.model_dump_json(),
                ),
            )
            self.db.execute(
                """
                INSERT INTO deck_plugin_installations (
                    id, scope_type, scope_id, deck_plugin_id,
                    installed_versions_json, default_version, status,
                    approved_capabilities_json, source_policy_id
                ) VALUES (?, 'workspace', 'workspace-1', ?, ?, ?, 'ready', ?, ?)
                """,
                (
                    INSTALLATION_ID,
                    PLUGIN_ID,
                    json.dumps([VERSION]),
                    VERSION,
                    json.dumps(manifest.capabilities),
                    "policy-default",
                ),
            )
        return manifest, runtime_lock

    def _context(self, **updates) -> RuntimeContext:
        capabilities = set(self.manifest.capabilities)
        data = {
            "deck_host_compatible": True,
            "claude_agent_compatible": True,
            "story_schema_compatible": True,
            "deck_runtime_config_compatible": True,
            "deck_runtime_snapshot_policy": capabilities,
            "user_and_workspace_grants": capabilities,
            "claude_agent_runtime_supported": capabilities,
            "materialized_runtime_plugin_ids": {RUNTIME_PLUGIN_ID},
            "loadable_runtime_plugin_ids": {RUNTIME_PLUGIN_ID},
        }
        data.update(updates)
        return RuntimeContext(**data)

    async def _check(self, context: RuntimeContext | None = None):
        return await self.service.check_compatibility(
            PLUGIN_ID,
            VERSION,
            Scope(scope_type="workspace", scope_id="workspace-1"),
            context or self._context(),
        )

    async def test_all_eight_checks_pass_and_return_only_effective_capabilities(self):
        result = await self._check()
        self.assertTrue(result.passed)
        self.assertIsNone(result.failed_check)
        self.assertEqual(result.effective_capabilities, sorted(self.manifest.capabilities))

    async def test_fixed_order_short_circuits_at_first_failure(self):
        with self.db:
            self.db.execute(
                "UPDATE deck_plugin_installations SET status = 'disabled' WHERE id = ?",
                (INSTALLATION_ID,),
            )
        result = await self._check(
            self._context(
                deck_host_compatible=False,
                claude_agent_compatible=False,
                story_schema_compatible=False,
                deck_runtime_config_compatible=False,
                user_and_workspace_grants=set(),
                materialized_runtime_plugin_ids=set(),
            )
        )
        self.assertEqual(result.failed_check, CompatibilityCheck.RELEASE_AVAILABLE)
        self.assertEqual(result.error_code, DECK_PLUGIN_UNAVAILABLE)

    async def test_server_verdict_dimensions_return_normative_safe_failures(self):
        cases = (
            (
                {"deck_host_compatible": False},
                CompatibilityCheck.DECK_HOST_COMPATIBLE,
                DECK_HOST_INCOMPATIBLE,
            ),
            (
                {"claude_agent_compatible": False},
                CompatibilityCheck.CLAUDE_AGENT_COMPATIBLE,
                CLAUDE_AGENT_INCOMPATIBLE,
            ),
            (
                {"story_schema_compatible": False},
                CompatibilityCheck.STORY_SCHEMA_COMPATIBLE,
                STORY_SCHEMA_INCOMPATIBLE,
            ),
            (
                {"deck_runtime_config_compatible": False},
                CompatibilityCheck.DECK_RUNTIME_CONFIG_COMPATIBLE,
                DECK_RUNTIME_CONFIG_INCOMPATIBLE,
            ),
            (
                {"user_and_workspace_grants": {"story.context.read"}},
                CompatibilityCheck.WORKFLOW_PERMISSION,
                WORKFLOW_PERMISSION_DENIED,
            ),
            (
                {"loadable_runtime_plugin_ids": set()},
                CompatibilityCheck.RUNTIME_PLUGIN_READY,
                RUNTIME_PLUGIN_NOT_READY,
            ),
        )
        for updates, expected_check, expected_code in cases:
            with self.subTest(expected_check=expected_check):
                result = await self._check(self._context(**updates))
                self.assertFalse(result.passed)
                self.assertEqual(result.failed_check, expected_check)
                self.assertEqual(result.error_code, expected_code)
                self.assertTrue(result.recovery_action)
                payload = result.model_dump()
                self.assertNotIn("manifest", payload)
                self.assertNotIn("secret", json.dumps(payload).lower())

    async def test_unresolved_lock_fails_before_permission_and_readiness(self):
        broken_lock = self.runtime_lock.model_copy(deep=True)
        broken_lock.claude_code_plugins[0].artifact_digest = ""
        with self.db:
            self.db.execute(
                "UPDATE deck_runtime_plugin_locks SET lock_json = ? WHERE id = ?",
                (broken_lock.model_dump_json(), broken_lock.runtime_plugin_lock_id),
            )
        result = await self._check(
            self._context(
                user_and_workspace_grants=set(),
                materialized_runtime_plugin_ids=set(),
            )
        )
        self.assertEqual(
            result.failed_check,
            CompatibilityCheck.RUNTIME_PLUGIN_RESOLVED,
        )
        self.assertEqual(result.error_code, RUNTIME_PLUGIN_UNRESOLVED)

    async def test_unknown_or_ungranted_required_capability_is_denied(self):
        result = await self._check(
            self._context(known_capabilities={"story.context.read"})
        )
        self.assertEqual(result.failed_check, CompatibilityCheck.WORKFLOW_PERMISSION)
        self.assertEqual(result.effective_capabilities, [])

    async def test_runtime_context_rejects_client_version_substitution(self):
        data = self._context().model_dump()
        data["client_deck_host_version"] = "999.0.0"
        with self.assertRaises(ValidationError):
            RuntimeContext.model_validate(data)

    async def test_deprecated_release_requires_explicit_server_policy(self):
        with self.db:
            self.db.execute(
                "UPDATE deck_plugin_releases SET status = 'deprecated'"
            )
        denied = await self._check()
        allowed = await self._check(
            self._context(deprecated_release_allowed_by_policy=True)
        )
        self.assertEqual(denied.error_code, DECK_PLUGIN_UNAVAILABLE)
        self.assertTrue(allowed.passed)

    async def test_capability_expansion_stages_pending_and_requires_admin(self):
        target_data = valid_manifest_data()
        target_data["deck_plugin_version"] = "3.2.0"
        target_data["workflow"]["workflow_definition_ref"] = (
            f"deck://{PLUGIN_ID}/3.2.0/workflow.json"
        )
        target_data["capabilities"].append("network.external.call")
        target_manifest = DeckPluginManifestV1.model_validate(target_data)

        diff = await self.service.check_capability_expansion(
            INSTALLATION_ID,
            target_manifest,
        )
        self.assertEqual(diff.added, ["network.external.call"])
        self.assertTrue(diff.requires_approval)
        row = self.db.execute(
            "SELECT * FROM deck_plugin_installations WHERE id = ?",
            (INSTALLATION_ID,),
        ).fetchone()
        self.assertEqual(row["status"], InstallationStatus.UPGRADE_PENDING.value)
        self.assertNotIn(
            "network.external.call",
            json.loads(row["approved_capabilities_json"]),
        )

        with self.assertRaises(CompatibilityServiceError) as caught:
            await self.service.approve_capability_expansion(
                INSTALLATION_ID,
                target_manifest.capabilities,
                "editor-1",
            )
        self.assertEqual(caught.exception.code, CAPABILITY_APPROVAL_DENIED)

        approved = await self.service.approve_capability_expansion(
            INSTALLATION_ID,
            target_manifest.capabilities,
            "admin-1",
        )
        self.assertEqual(approved.status, InstallationStatus.READY)
        self.assertIn("network.external.call", approved.approved_capabilities)


if __name__ == "__main__":
    unittest.main()
