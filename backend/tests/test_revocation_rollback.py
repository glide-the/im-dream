"""Development/test evidence for DECK-015 revocation, degradation and rollback."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
import hashlib
import json
import sqlite3
import unittest
import uuid

from backend import database
from backend.models.deck_plugin import (
    DeckPluginManifestV1,
    DeckRuntimePluginLock,
    InstallationStatus,
    RuntimePluginLockEntry,
)
from backend.services.deck_plugin.degradation_service import (
    DEGRADATION_NOT_DECLARED,
    DEGRADATION_OUTPUT_SCHEMA_MISMATCH,
    DEGRADATION_PERMISSION_DENIED,
    DEGRADATION_REQUIRED_PLUGIN_MISSING,
    DEGRADATION_SECURITY_REVOCATION,
    DegradationService,
    DegradedModeDefinition,
)
from backend.services.deck_plugin.installation_service import (
    InstallationService,
    InstallationServiceError,
    RuntimePreparation,
)
from backend.services.deck_plugin.revocation_service import (
    EVIDENCE_CASE_NAMES,
    REVOCATION_AUTHORIZATION_DENIED,
    REVOCATION_GRACE_OUT_OF_RANGE,
    REVOCATION_SCOPE_APPROVAL_REQUIRED,
    RUN_TERMINAL_CONFLICT,
    SECURITY_REVOCATION,
    SECURITY_TERMINATION_UNCONFIRMED,
    EvidenceCase,
    ImpactResolution,
    InMemoryRevocationRepository,
    InMemoryRun,
    InMemoryRunCoordinator,
    NotificationDeliveryResult,
    RevocationAuthorization,
    RevocationLevel,
    RevocationService,
    RevocationServiceError,
    SQLiteRevocationRepository,
)
from backend.services.deck_plugin.rollback_manager import (
    ROLLBACK_DIGEST_INVALID,
    ROLLBACK_INCOMPATIBLE,
    RollbackManager,
    RollbackManagerError,
)
from backend.tests.test_deck_plugin_manifest import valid_manifest_data


NOW = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
RELEASE_KEY = "release-fixture-1"
DIGEST = "sha256:" + "d" * 64
PLUGIN_ID = "voice-decks.story-dramatize"


def mode_manifest(*, declared: bool = True, optional: bool = True) -> DeckPluginManifestV1:
    data = valid_manifest_data()
    data["runtime"]["degraded_modes"] = ["without-voice-tools"] if declared else []
    data["runtime"]["claude_code_plugins"][0]["required"] = not optional
    return DeckPluginManifestV1.model_validate(data)


def ready_preparer(_plugin_id, _version, _runtime_lock):
    return RuntimePreparation(
        runtime_readiness="ready_non_production",
        lock_materialized=True,
        load_smoke_passed=True,
    )


class RevocationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.repository = InMemoryRevocationRepository()
        self.runs = InMemoryRunCoordinator(
            [
                InMemoryRun("run-queued", "queued"),
                InMemoryRun("run-running", "running"),
                InMemoryRun("run-history", "completed"),
            ]
        )
        self.now = NOW
        self.current_target = ("deck_plugin_release", RELEASE_KEY)
        self.resolution = ImpactResolution(
            release_ids=(RELEASE_KEY,),
            installation_ids=("installation-b", "installation-a"),
            binding_ids=("binding-b", "binding-a"),
            runtime_lock_ids=("lock-a",),
            snapshot_ids=("snapshot-a",),
            workflow_run_ids=("run-queued", "run-running", "run-history"),
            session_ids=("session-a",),
            runtime_node_ids=("node-a",),
            resolved_environment_ids=("env-1",),
            resolved_tenant_or_project_ids=("tenant-1",),
            resolver_revision="resolver-test/v1",
        )
        self.service = self.make_service()

    def authorization(self, request):
        common = dict(
            allowed=True,
            allowed_environment_ids=frozenset({"env-1"}),
            allowed_tenant_or_project_ids=frozenset({"tenant-1"}),
            allowed_targets=frozenset({(request.target_type, request.target_key)}),
            executor_id="machine-revocation-coordinator",
            executor_is_machine=True,
            reviewer_id="security-reviewer",
        )
        if request.level is RevocationLevel.DISABLE:
            return RevocationAuthorization(
                actor_role="DeckOperator",
                actor_permissions=frozenset({"deck.disable"}),
                **common,
            )
        if request.level is RevocationLevel.REVOKE:
            return RevocationAuthorization(
                actor_role="SecurityResponder",
                actor_permissions=frozenset({"security.revocation.propose"}),
                approver_role="SecurityApprover",
                approver_permissions=frozenset({"security.revocation.approve"}),
                **common,
            )
        return RevocationAuthorization(
            actor_role="SecurityResponder",
            actor_permissions=frozenset({"security.revocation.break_glass"}),
            approver_role="SecurityApprover" if request.approved_by else None,
            approver_permissions=(
                frozenset({"security.revocation.approve"})
                if request.approved_by
                else frozenset()
            ),
            break_glass_expires_at=self.now + timedelta(minutes=10),
            **common,
        )

    def make_service(self, *, notification_sender=None):
        return RevocationService(
            self.repository,
            self.runs,
            authorizer=self.authorization,
            impact_resolver=lambda _request: self.resolution,
            notification_sender=notification_sender,
            clock=lambda: self.now,
        )

    async def revoke(self, level, *, key="idem-1", grace=None, approved_by="approver"):
        return await self.service.revoke(
            key,
            level,
            "deck_plugin_release",
            RELEASE_KEY,
            ["env-1"],
            ["tenant-1"],
            "known-compromise",
            None if level is RevocationLevel.DISABLE else "incident-1",
            "requester",
            None if level is RevocationLevel.DISABLE else approved_by,
            grace,
        )

    async def test_disable_blocks_new_operations_without_touching_active_or_history(self):
        result = await self.revoke(RevocationLevel.DISABLE)

        self.assertIsNone(result.effective_grace_seconds)
        self.assertIsNone(result.grace_deadline_at)
        self.assertEqual(self.runs.get("run-queued").status, "queued")
        self.assertEqual(self.runs.get("run-running").status, "running")
        self.assertEqual(self.runs.get("run-history").status, "completed")
        self.assertEqual(self.repository.commands, {})
        self.assertTrue(
            self.service.is_new_operation_blocked(
                target_type="release",
                target_key=RELEASE_KEY,
                environment_id="env-1",
                tenant_or_project_id="tenant-1",
            )
        )
        self.assertFalse(self.repository.quarantined_targets)
        self.assertTrue(self.repository.notifications)

    async def test_revoke_default_grace_hard_stop_and_idempotent_replay(self):
        self.runs.termination_outcomes.update(
            {
                ("run-queued", "hard"): "ack",
                ("run-running", "hard"): "ack",
            }
        )
        result = await self.revoke(RevocationLevel.REVOKE)

        self.assertEqual(result.effective_grace_seconds, 60)
        self.assertEqual(result.grace_deadline_at, NOW + timedelta(seconds=60))
        self.assertEqual(self.runs.get("run-queued").status, "cancelling")
        self.assertEqual(self.runs.get("run-running").status, "cancelling")
        self.assertEqual(self.runs.get("run-history").status, "completed")
        self.assertEqual(await self.service.process_due_hard_stops(NOW + timedelta(seconds=59)), ())

        command_ids = await self.service.process_due_hard_stops(
            NOW + timedelta(seconds=60)
        )
        self.assertEqual(len(command_ids), 2)
        self.assertEqual(self.runs.get("run-queued").status, "cancelled")
        self.assertEqual(self.runs.get("run-running").termination_mode, "hard")
        replay = await self.revoke(RevocationLevel.REVOKE)
        self.assertTrue(replay.replayed)
        self.assertEqual(replay.revocation_id, result.revocation_id)
        self.assertEqual(replay.impact_manifest_id, result.impact_manifest_id)
        self.assertEqual(len(self.repository.records), 1)
        self.assertIn(self.current_target, self.repository.quarantined_targets)

    async def test_grace_boundaries_role_separation_and_scope_fail_closed(self):
        zero = await self.revoke(RevocationLevel.REVOKE, grace=0)
        self.assertEqual(zero.grace_deadline_at, NOW)

        with self.assertRaises(RevocationServiceError) as too_large:
            await self.service.revoke(
                "idem-too-large",
                RevocationLevel.REVOKE,
                "release",
                RELEASE_KEY,
                ["env-1"],
                ["tenant-1"],
                "test",
                "incident-2",
                "requester",
                "approver",
                301,
            )
        self.assertEqual(too_large.exception.code, REVOCATION_GRACE_OUT_OF_RANGE)

        with self.assertRaises(RevocationServiceError) as same_actor:
            await self.service.revoke(
                "idem-same-actor",
                RevocationLevel.REVOKE,
                "release",
                RELEASE_KEY,
                ["env-1"],
                ["tenant-1"],
                "test",
                "incident-3",
                "requester",
                "requester",
                300,
            )
        self.assertEqual(same_actor.exception.code, REVOCATION_AUTHORIZATION_DENIED)

        with self.assertRaises(RevocationServiceError) as out_of_scope:
            await self.service.revoke(
                "idem-scope",
                RevocationLevel.DISABLE,
                "release",
                RELEASE_KEY,
                ["env-2"],
                ["tenant-1"],
                "test",
                None,
                "requester",
                None,
                None,
            )
        self.assertEqual(out_of_scope.exception.code, REVOCATION_SCOPE_APPROVAL_REQUIRED)

    async def test_scope_expansion_creates_new_record_linked_to_original(self):
        repository = InMemoryRevocationRepository()
        runs = InMemoryRunCoordinator([])

        def expanded_auth(request):
            return RevocationAuthorization(
                allowed=True,
                actor_role="SecurityResponder",
                actor_permissions=frozenset({"security.revocation.propose"}),
                approver_role="SecurityApprover",
                approver_permissions=frozenset({"security.revocation.approve"}),
                allowed_environment_ids=frozenset({"env-1", "env-2"}),
                allowed_tenant_or_project_ids=frozenset({"tenant-1"}),
                allowed_targets=frozenset(
                    {("deck_plugin_release", RELEASE_KEY)}
                ),
                executor_id="machine-revocation-coordinator",
                executor_is_machine=True,
                reviewer_id="security-reviewer",
            )

        def expanded_impact(request):
            return ImpactResolution(
                release_ids=(RELEASE_KEY,),
                resolved_environment_ids=request.environment_ids,
                resolved_tenant_or_project_ids=request.tenant_or_project_ids,
            )

        service = RevocationService(
            repository,
            runs,
            authorizer=expanded_auth,
            impact_resolver=expanded_impact,
            clock=lambda: NOW,
        )
        first = await service.revoke(
            "scope-original",
            RevocationLevel.REVOKE,
            "release",
            RELEASE_KEY,
            ["env-1"],
            ["tenant-1"],
            "fixture",
            "incident-original",
            "requester",
            "approver",
            60,
        )
        expanded = await service.revoke(
            "scope-expanded",
            RevocationLevel.REVOKE,
            "release",
            RELEASE_KEY,
            ["env-1", "env-2"],
            ["tenant-1"],
            "fixture",
            "incident-expanded",
            "requester",
            "approver",
            60,
        )
        self.assertNotEqual(expanded.revocation_id, first.revocation_id)
        self.assertEqual(
            repository.get_record(expanded.revocation_id).extends_revocation_id,
            first.revocation_id,
        )

    async def test_emergency_is_immediate_and_unconfirmed_waits_ten_seconds(self):
        result = await self.revoke(
            RevocationLevel.EMERGENCY, approved_by=None, grace=0
        )
        record = self.repository.get_record(result.revocation_id)
        self.assertEqual(result.grace_deadline_at, NOW)
        self.assertEqual(
            record.ratification_deadline_at, NOW + timedelta(minutes=30)
        )
        self.assertTrue(
            all(run.termination_mode == "hard" for run in self.runs.runs.values() if run.status == "cancelling")
        )
        self.assertFalse(
            any(
                item.incident_type == SECURITY_TERMINATION_UNCONFIRMED
                for item in self.repository.incidents
            )
        )
        self.assertEqual(
            self.service.process_unconfirmed_terminations(NOW + timedelta(seconds=9)),
            (),
        )
        incidents = self.service.process_unconfirmed_terminations(
            NOW + timedelta(seconds=10)
        )
        self.assertEqual(len(incidents), 2)
        self.assertTrue(
            all(
                self.runs.get(run_id).status == "cancelling"
                for run_id in ("run-queued", "run-running")
            )
        )
        overdue = self.service.process_overdue_emergency_ratifications(
            NOW + timedelta(minutes=31)
        )
        self.assertEqual(len(overdue), 1)

    async def test_terminal_mapping_conflict_guard_and_concurrent_suppression(self):
        self.runs.termination_outcomes[("run-queued", "graceful")] = "ack"
        self.runs.termination_outcomes[("run-running", "hard")] = "isolated_failure"
        result = await self.revoke(RevocationLevel.REVOKE, grace=300)
        self.assertEqual(self.runs.get("run-queued").status, "cancelled")
        self.assertEqual(
            self.runs.get("run-queued").terminal_reason_code, SECURITY_REVOCATION
        )
        self.assertFalse(
            self.service.guard_terminal_transition("run-running", "completed")
        )
        self.assertTrue(
            any(item.event_type == RUN_TERMINAL_CONFLICT for item in self.repository.audit_events)
        )

        # A stronger emergency may shorten/escalate, but a later weak request
        # cannot duplicate the terminal command or downgrade the mode.
        emergency = await self.service.revoke(
            "idem-emergency",
            RevocationLevel.EMERGENCY,
            "release",
            RELEASE_KEY,
            ["env-1"],
            ["tenant-1"],
            "escalate",
            "incident-2",
            "requester",
            None,
            0,
        )
        self.assertNotEqual(emergency.revocation_id, result.revocation_id)
        self.assertEqual(self.runs.get("run-running").status, "failed")
        self.assertIsNotNone(self.runs.get("run-running").isolation_receipt_id)
        self.assertTrue(
            any(
                item.event_type == "workflow.run.security_cancellation_suppressed"
                for item in self.repository.audit_events
            )
        )

    async def test_notification_six_attempts_fail_without_delaying_hard_stop(self):
        attempts = []

        async def fail_sender(entry):
            attempts.append((entry.notification_id, entry.attempt_count + 1))
            return NotificationDeliveryResult(False, error_code="provider-down")

        self.service = self.make_service(notification_sender=fail_sender)
        self.runs.termination_outcomes[("run-queued", "hard")] = "ack"
        self.runs.termination_outcomes[("run-running", "hard")] = "ack"
        await self.revoke(RevocationLevel.EMERGENCY, approved_by=None, grace=0)
        self.assertEqual(self.runs.get("run-running").status, "cancelled")

        for offset in (30, 120, 600, 1800, 7200):
            await self.service.deliver_due_notifications(
                NOW + timedelta(seconds=offset)
            )
        self.assertTrue(self.repository.notifications)
        self.assertTrue(
            all(item.attempt_count == 6 for item in self.repository.notifications.values())
        )
        self.assertTrue(
            all(item.next_attempt_at is None for item in self.repository.notifications.values())
        )
        self.assertEqual(
            len(
                [
                    item
                    for item in self.repository.incidents
                    if item.incident_type == "security.notification.delivery_failed"
                ]
            ),
            len(self.repository.notifications),
        )

    async def test_sqlite_repository_persists_barrier_outboxes_and_append_only_audit(self):
        db = sqlite3.connect(":memory:")
        db.execute("PRAGMA foreign_keys=ON")
        repository = SQLiteRevocationRepository(db)
        self.repository = repository
        self.runs.termination_outcomes[("run-queued", "hard")] = "ack"
        self.runs.termination_outcomes[("run-running", "hard")] = "ack"

        async def fail_once(_entry):
            return NotificationDeliveryResult(False, error_code="provider-down")

        self.service = self.make_service(notification_sender=fail_once)
        result = await self.revoke(
            RevocationLevel.EMERGENCY,
            key="sqlite-persisted",
            approved_by=None,
            grace=0,
        )
        reopened = SQLiteRevocationRepository(db)
        self.assertEqual(
            reopened.find_idempotency("sqlite-persisted").revocation_id,
            result.revocation_id,
        )
        self.assertEqual(len(reopened.commands), 3)
        self.assertTrue(reopened.audit_events)
        self.assertEqual(len(reopened.runtime_receipts), 2)
        self.assertTrue(
            all(item.inbox_receipt_id.startswith("inr_") for item in reopened.runtime_receipts.values())
        )
        self.assertTrue(reopened.notifications)
        self.assertTrue(
            all(item.attempt_count == 1 for item in reopened.notifications.values())
        )
        self.assertIn(self.current_target, reopened.quarantined_targets)

        with self.assertRaises(sqlite3.IntegrityError):
            db.execute(
                "UPDATE security_revocations SET record_json = '{}' WHERE revocation_id = ?",
                (result.revocation_id,),
            )
        db.rollback()
        notification_id = next(iter(reopened.notifications.values())).notification_id
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute(
                "DELETE FROM revocation_notification_outbox WHERE notification_id = ?",
                (notification_id,),
            )
        db.rollback()
        db.close()

    async def test_four_target_manifest_is_sorted_hashed_and_scope_not_truncated(self):
        targets = (
            ("deck_plugin_release", RELEASE_KEY),
            ("runtime_plugin_digest", DIGEST),
            ("signing_identity", "trust|issuer|subject|fingerprint"),
            ("capability_policy", "policy-a@revision-1"),
        )
        manifests = []
        for index, (target_type, target_key) in enumerate(targets):
            repository = InMemoryRevocationRepository()
            runs = InMemoryRunCoordinator([])

            def auth(request):
                return replace(
                    self.authorization(request),
                    allowed_targets=frozenset({(request.target_type, request.target_key)}),
                )

            resolution = replace(
                self.resolution,
                workflow_run_ids=(),
                installation_ids=("z", "a", "z"),
            )
            service = RevocationService(
                repository,
                runs,
                authorizer=auth,
                impact_resolver=lambda _request, value=resolution: value,
                clock=lambda: NOW,
            )
            result = await service.revoke(
                f"target-{index}",
                RevocationLevel.REVOKE,
                target_type,
                target_key,
                ["env-1"],
                ["tenant-1"],
                "fixture",
                f"incident-{index}",
                "requester",
                "approver",
                60,
            )
            manifest = repository.manifests[result.impact_manifest_id]
            self.assertEqual(manifest.resolution.installation_ids, ("a", "z"))
            self.assertRegex(manifest.manifest_sha256, r"^sha256:[0-9a-f]{64}$")
            manifests.append(manifest.impact_manifest_id)
        self.assertEqual(len(set(manifests)), 4)

        bad_resolution = replace(
            self.resolution,
            resolved_environment_ids=("env-outside",),
        )
        bad_service = RevocationService(
            InMemoryRevocationRepository(),
            self.runs,
            authorizer=self.authorization,
            impact_resolver=lambda _request: bad_resolution,
            clock=lambda: NOW,
        )
        with self.assertRaises(RevocationServiceError) as caught:
            await bad_service.revoke(
                "bad-impact",
                RevocationLevel.REVOKE,
                "release",
                RELEASE_KEY,
                ["env-1"],
                ["tenant-1"],
                "fixture",
                "incident-bad",
                "requester",
                "approver",
                60,
            )
        self.assertEqual(caught.exception.code, REVOCATION_SCOPE_APPROVAL_REQUIRED)

    async def test_stage4_evidence_pack_requires_all_cases_reviewer_and_rollout(self):
        self.runs.termination_outcomes.update(
            {
                ("run-queued", "hard"): "ack",
                ("run-running", "hard"): "ack",
            }
        )
        execution = await self.revoke(
            RevocationLevel.EMERGENCY,
            key="evidence-emergency",
            approved_by=None,
            grace=0,
        )
        command_ids = [item.command_id for item in self.repository.commands.values()]
        event_ids = [item.event_id for item in self.repository.audit_events]
        receipt_ids = [
            item.termination_receipt_id
            for item in self.runs.runs.values()
            if item.termination_receipt_id
        ]
        notification_ids = [
            item.notification_id for item in self.repository.notifications.values()
        ]
        raw_ids = [
            execution.revocation_id,
            execution.impact_manifest_id,
            execution.manifest_sha256,
            *command_ids,
            *event_ids,
            *receipt_ids,
            *notification_ids,
        ]
        self.assertGreaterEqual(len(raw_ids), 11)
        evidence_by_case = {
            "three_level_authorization_and_behavior": (
                execution.revocation_id,
                execution.impact_manifest_id,
                event_ids[0],
            ),
            "four_target_impact_resolution": (
                execution.impact_manifest_id,
                execution.manifest_sha256,
            ),
            "scope_expansion_replay_and_concurrency": (
                execution.revocation_id,
                command_ids[0],
                event_ids[-1],
            ),
            "disable_does_not_terminate": (
                execution.impact_manifest_id,
                command_ids[-1],
            ),
            "revoke_grace_to_hard_stop": (
                command_ids[0],
                event_ids[1],
                receipt_ids[0],
            ),
            "emergency_immediate_hard_stop": (
                execution.revocation_id,
                event_ids[1],
                receipt_ids[0],
            ),
            "at_least_once_cancellation": (
                command_ids[0],
                receipt_ids[0],
                event_ids[2],
            ),
            "terminal_mapping_and_conflict_guard": (
                receipt_ids[0],
                receipt_ids[1],
                event_ids[2],
            ),
            "append_only_audit": tuple(event_ids),
            "notification_timing_and_failure": tuple(notification_ids),
            "quarantine_and_superseding_recovery": (
                execution.revocation_id,
                execution.impact_manifest_id,
                "quarantine:deck_plugin_release:" + RELEASE_KEY,
            ),
        }
        cases = tuple(
            EvidenceCase(
                case_name=name,
                test_case_id=(
                    "backend.tests.test_revocation_rollback:"
                    f"evidence-case-{index:02d}"
                ),
                evidence_ids=evidence_by_case[name],
                observed_at=NOW + timedelta(seconds=index),
            )
            for index, name in enumerate(EVIDENCE_CASE_NAMES, start=1)
        )
        pack = RevocationService.build_evidence_pack(
            cases,
            tested_release_or_commit="working-tree-SUO-332",
            test_environment="development-test",
            test_run_id="unittest-revocation-rollback",
            generated_at=NOW,
        )
        self.assertEqual(len(pack.cases), 11)
        self.assertRegex(pack.evidence_manifest_sha256, r"^sha256:[0-9a-f]{64}$")
        self.assertFalse(pack.production_gate_satisfied)
        print(
            "DEVELOPMENT_EVIDENCE_PACK",
            pack.evidence_pack_id,
            pack.evidence_manifest_sha256,
            ",".join(raw_ids),
        )
        reviewed_not_approved = RevocationService.build_evidence_pack(
            cases,
            tested_release_or_commit="working-tree-SUO-332",
            test_environment="development-test",
            test_run_id="unittest-revocation-rollback",
            generated_at=NOW,
            independent_reviewer_id="reviewer-independent",
        )
        self.assertFalse(reviewed_not_approved.production_gate_satisfied)
        with self.assertRaises(RevocationServiceError):
            RevocationService.build_evidence_pack(
                cases[:-1],
                tested_release_or_commit="working-tree-SUO-332",
                test_environment="development-test",
                test_run_id="unittest-revocation-rollback",
                generated_at=NOW,
            )


class DegradationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        manifest = mode_manifest()
        plugin = manifest.runtime.claude_code_plugins[0]
        self.plugin_id = plugin.claude_code_plugin_id
        self.capability = plugin.capability_bindings[0]
        self.definition = DegradedModeDefinition(
            degraded_mode_id="without-voice-tools",
            optional_plugin_ids=frozenset({self.plugin_id}),
            omittable_capabilities=frozenset({self.capability}),
            replacement_steps=("skip_optional_voice_enrichment",),
            output_schema_ref=manifest.workflow.output_schema_ref,
        )
        self.service = DegradationService([self.definition])

    async def test_degradation_requires_manifest_declaration_and_same_schema(self):
        undeclared = await self.service.evaluate_degradation(
            mode_manifest(declared=False), [self.plugin_id], [self.capability]
        )
        self.assertFalse(undeclared.allowed)
        self.assertEqual(undeclared.error_code, DEGRADATION_NOT_DECLARED)

        allowed = await self.service.evaluate_degradation(
            mode_manifest(), [self.plugin_id], [self.capability]
        )
        self.assertTrue(allowed.allowed)
        self.assertEqual(allowed.degraded_mode_id, "without-voice-tools")
        self.assertTrue(allowed.user_confirmation_required)
        self.assertTrue(allowed.runtime_load_receipt_required)
        self.assertEqual(
            allowed.output_schema_ref, mode_manifest().workflow.output_schema_ref
        )

        wrong_schema = DegradationService(
            [replace(self.definition, output_schema_ref="schema://different")]
        )
        denied = await wrong_schema.evaluate_degradation(
            mode_manifest(), [self.plugin_id], [self.capability]
        )
        self.assertEqual(denied.error_code, DEGRADATION_OUTPUT_SCHEMA_MISMATCH)

    async def test_required_permission_and_revocation_never_auto_degrade(self):
        required = await self.service.evaluate_degradation(
            mode_manifest(optional=False), [self.plugin_id], [self.capability]
        )
        self.assertEqual(required.error_code, DEGRADATION_REQUIRED_PLUGIN_MISSING)

        unauthorized = await self.service.evaluate_degradation(
            mode_manifest(),
            [self.plugin_id],
            [self.capability],
            capability_authorization_satisfied=False,
        )
        self.assertEqual(unauthorized.error_code, DEGRADATION_PERMISSION_DENIED)

        revoked = await self.service.evaluate_degradation(
            mode_manifest(),
            [self.plugin_id],
            [self.capability],
            security_revoked=True,
        )
        self.assertEqual(revoked.error_code, DEGRADATION_SECURITY_REVOCATION)


class RollbackManagerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        database.create_tables(self.db)
        database.create_workflow_run_tables(self.db)
        self.add_release("3.1.0")
        self.add_release("3.2.0")
        self.installation_id = f"dpi_{uuid.uuid4().hex}"
        with self.db:
            self.db.execute(
                """
                INSERT INTO deck_plugin_installations (
                    id, scope_type, scope_id, deck_plugin_id,
                    installed_versions_json, default_version, status,
                    approved_capabilities_json, source_policy_id
                ) VALUES (?, 'workspace', 'workspace-rollback', ?, ?, '3.2.0',
                          'ready', ?, 'policy-default')
                """,
                (
                    self.installation_id,
                    PLUGIN_ID,
                    json.dumps(["3.1.0", "3.2.0"]),
                    json.dumps(valid_manifest_data()["capabilities"]),
                ),
            )
        self.installation_service = InstallationService(
            self.db,
            runtime_preparer=ready_preparer,
            compatibility_checker=lambda _plugin, _version: True,
        )
        self.audit_events = []

    def tearDown(self):
        self.db.close()

    def add_release(self, version, *, status="published"):
        data = valid_manifest_data()
        data["deck_plugin_version"] = version
        data["status"] = status
        data["workflow"]["workflow_definition_ref"] = (
            f"deck://{PLUGIN_ID}/{version}/workflow.json"
        )
        manifest = DeckPluginManifestV1.model_validate(data)
        manifest_hash = "sha256:" + hashlib.sha256(
            manifest.model_dump_json().encode()
        ).hexdigest()
        runtime_lock = DeckRuntimePluginLock(
            runtime_plugin_lock_id=f"rpl_{uuid.uuid4().hex}",
            deck_plugin_id=PLUGIN_ID,
            deck_plugin_version=version,
            deck_plugin_manifest_hash=manifest_hash,
            claude_code_plugins=[
                RuntimePluginLockEntry(
                    claude_code_plugin_id=(
                        manifest.runtime.claude_code_plugins[0].claude_code_plugin_id
                    ),
                    resolved_version="1.4.2",
                    source_ref="marketplace://voice-decks@2026-08-01",
                    artifact_digest=DIGEST,
                    required=True,
                    capability_bindings=(
                        manifest.runtime.claude_code_plugins[0].capability_bindings
                    ),
                )
            ],
            created_at=NOW,
            production_ready=False,
            production_readiness_reasons=["Stage 4 production gate is closed"],
        )
        with self.db:
            self.db.execute(
                """
                INSERT INTO deck_plugin_releases (
                    id, deck_plugin_id, deck_plugin_version, display_name,
                    status, manifest_json, manifest_hash, workflow_definition_ref,
                    capabilities_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"dr_{uuid.uuid4().hex}",
                    PLUGIN_ID,
                    version,
                    manifest.display_name,
                    status,
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

    def manager(self, *, compatible=True, digest_valid=True):
        return RollbackManager(
            self.db,
            self.installation_service,
            compatibility_checker=lambda _manifest, _lock: compatible,
            digest_verifier=lambda _digest: digest_valid,
            audit_appender=self.audit_events.append,
            clock=lambda: NOW,
        )

    async def test_explicit_rollback_changes_only_default_and_appends_audit(self):
        workflow_projection = tuple(
            self.db.execute("SELECT * FROM workflow_runs ORDER BY id").fetchall()
        )
        binding_projection = tuple(
            self.db.execute("SELECT * FROM deck_plugin_bindings ORDER BY deck_plugin_binding_id").fetchall()
        )
        result = await self.manager().rollback_installation(
            self.installation_id, "3.1.0", "plugin-admin"
        )
        installation = self.installation_service.get(self.installation_id)
        self.assertEqual(result.previous_default_version, "3.2.0")
        self.assertEqual(result.target_version, "3.1.0")
        self.assertEqual(installation.default_version, "3.1.0")
        self.assertEqual(installation.installed_versions, ["3.1.0", "3.2.0"])
        self.assertTrue(result.affects_future_resolution_only)
        self.assertEqual(len(self.audit_events), 1)
        self.assertFalse(self.audit_events[0].historical_runs_modified)
        self.assertEqual(
            tuple(self.db.execute("SELECT * FROM workflow_runs ORDER BY id").fetchall()),
            workflow_projection,
        )
        self.assertEqual(
            tuple(self.db.execute("SELECT * FROM deck_plugin_bindings ORDER BY deck_plugin_binding_id").fetchall()),
            binding_projection,
        )

    async def test_rollback_fails_closed_on_digest_or_compatibility(self):
        with self.assertRaises(RollbackManagerError) as bad_digest:
            await self.manager(digest_valid=False).rollback_installation(
                self.installation_id, "3.1.0", "plugin-admin"
            )
        self.assertEqual(bad_digest.exception.code, ROLLBACK_DIGEST_INVALID)
        self.assertEqual(
            self.installation_service.get(self.installation_id).default_version,
            "3.2.0",
        )

        with self.assertRaises(RollbackManagerError) as incompatible:
            await self.manager(compatible=False).rollback_installation(
                self.installation_id, "3.1.0", "plugin-admin"
            )
        self.assertEqual(incompatible.exception.code, ROLLBACK_INCOMPATIBLE)
        self.assertEqual(self.audit_events, [])

    async def test_failed_upgrade_preserves_old_ready_default(self):
        self.add_release("3.3.0")

        async def fail_new_version(_plugin_id, version, _runtime_lock):
            if version == "3.3.0":
                return RuntimePreparation(
                    runtime_readiness="load_failed",
                    lock_materialized=True,
                    load_smoke_passed=False,
                    error_code="DECK_PLUGIN_RUNTIME_NOT_READY",
                    error_summary="target load-smoke failed",
                )
            return ready_preparer(_plugin_id, version, _runtime_lock)

        self.installation_service._runtime_preparer = fail_new_version
        with self.assertRaises(InstallationServiceError):
            await self.installation_service.upgrade(self.installation_id, "3.3.0")
        preserved = self.installation_service.get(self.installation_id)
        self.assertEqual(preserved.status, InstallationStatus.READY)
        self.assertEqual(preserved.default_version, "3.2.0")
        self.assertNotIn("3.3.0", preserved.installed_versions)


if __name__ == "__main__":
    unittest.main()
