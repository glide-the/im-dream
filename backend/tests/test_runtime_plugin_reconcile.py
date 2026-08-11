"""Focused task_008 reconcile, materialization, receipt, and guard tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from pydantic import ValidationError

from backend.schema.legacy_main_sqlite import (
    create_agent_session_tables,
    create_runtime_plugin_tables,
    create_tables,
)
from backend.models.deck_plugin import DeckRuntimePluginLock, RuntimePluginLockEntry
from backend.models.runtime_plugin import (
    ActivationStatus,
    DeclarationStatus,
    MaterializationStatus,
    RuntimePlacementContext,
    compute_artifact_set_hash,
    sha256_digest,
)
from backend.models.workflow_run import (
    AuthenticatedActorContext,
    RunStatus,
    RuntimeLoadReceiptReadiness,
)
from backend.services.runtime_plugin.materialization_manager import (
    FileSystemAtomicPublisher,
    MaterializationError,
    MaterializationManager,
    RetentionEvidence,
    StagedArtifact,
)
from backend.services.runtime_plugin.reconcile_service import (
    AllowlistCliSourcePolicy,
    AllowlistRuntimeSourcePolicy,
    CliAuditRecord,
    CompletedCliProcess,
    MarketplaceIntent,
    ReconcileError,
    ReconcileService,
)
from backend.services.workflow.run_service import (
    RuntimeLoadReceiptNotReady,
    WorkflowRunService,
)


PLUGIN_ID = "ink-dream-tools@voice-decks"
PLUGIN_VERSION = "1.4.2"
SOURCE_REF = "github:voice-decks/marketplace@commit-123"
RUN_ID = "run_" + "1" * 32
LOCK_ID = "rpl_" + "2" * 32
MANIFEST_HASH = "sha256:" + "3" * 64
WORKSPACE_ID = "workspace-runtime-plugin"
ACTOR_ID = "1"
NOW = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
ARTIFACT_BYTES = b"verified runtime plugin artifact"
ARTIFACT_DIGEST = sha256_digest(ARTIFACT_BYTES)
TOKEN_SECRET = b"runtime-plugin-workflow-secret-32-bytes"


class FakeSettingsWriter:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def write_settings(self, **kwargs) -> None:
        self.calls.append(kwargs)


class FakeHeadlessRunner:
    def __init__(self, payload: dict | Exception) -> None:
        self.payload = payload
        self.calls: list[dict] = []

    def reconcile(self, **kwargs) -> dict:
        self.calls.append(kwargs)
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class FakeCliRunner:
    def __init__(self, result: CompletedCliProcess | Exception) -> None:
        self.result = result
        self.calls: list[tuple[list[str], int, bool]] = []

    def run(self, argv, *, timeout_seconds: int, shell: bool):
        self.calls.append((list(argv), timeout_seconds, shell))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class CollectingAuditSink:
    def __init__(self) -> None:
        self.records: list[CliAuditRecord] = []

    def record(self, record: CliAuditRecord) -> None:
        self.records.append(record)


class FakeArtifactProvider:
    def __init__(self, artifact: StagedArtifact) -> None:
        self.artifact = artifact
        self.calls = 0

    async def load_staged(self, **_kwargs) -> StagedArtifact:
        self.calls += 1
        await asyncio.sleep(0)
        return self.artifact


class FakeRetentionReader:
    def __init__(self, evidence: RetentionEvidence | None) -> None:
        self.evidence = evidence
        self.calls = 0

    def read(self, **_kwargs) -> RetentionEvidence | None:
        self.calls += 1
        return self.evidence


class RuntimePluginFixture:
    def __init__(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "runtime-plugin.db"
        self.cache_root = Path(self.temp_dir.name) / "cache"
        self.db = sqlite3.connect(self.db_path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        create_tables(self.db)
        create_runtime_plugin_tables(self.db)
        self.lock = DeckRuntimePluginLock(
            runtime_plugin_lock_id=LOCK_ID,
            deck_plugin_id="voice-decks.story-dramatize",
            deck_plugin_version="3.1.0",
            deck_plugin_manifest_hash=MANIFEST_HASH,
            claude_code_plugins=[
                RuntimePluginLockEntry(
                    claude_code_plugin_id=PLUGIN_ID,
                    resolved_version=PLUGIN_VERSION,
                    source_ref=SOURCE_REF,
                    artifact_digest=ARTIFACT_DIGEST,
                    required=True,
                    capability_bindings=["deck.render", "voice.synthesize"],
                )
            ],
            created_at=NOW,
            production_ready=False,
            production_readiness_reasons=["development/test only"],
        )
        self.lock_json = json.dumps(
            self.lock.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
        )
        self._seed_run()
        self.placement = RuntimePlacementContext(
            workflow_run_id=RUN_ID,
            runtime_environment_id="runtime-dev-1",
            runtime_pool_id="runtime-dev-1",
            distribution_mode="local_persistent",
            runtime_node_id="node-dev-1",
            artifact_set_hash=compute_artifact_set_hash(self.lock),
            policy_revision="policy-7",
            deployment_tier="test",
        )
        self.settings_writer = FakeSettingsWriter()
        self.source_policy = AllowlistRuntimeSourcePolicy(
            policy_revision="policy-7",
            plugins={
                PLUGIN_ID: MarketplaceIntent(
                    alias="voice-decks",
                    source="github",
                    repo="voice-decks/marketplace",
                    allowed_source_refs=frozenset({SOURCE_REF}),
                )
            },
        )
        self.cli_policy = AllowlistCliSourcePolicy(
            policy_revision="policy-7",
            allowed_plugins={PLUGIN_ID: frozenset({PLUGIN_VERSION})},
            allowed_marketplace_sources={
                "voice-decks": frozenset({SOURCE_REF}),
            },
        )

    def close(self) -> None:
        self.db.close()
        self.temp_dir.cleanup()

    def _seed_run(self) -> None:
        self.db.execute(
            "INSERT INTO users (id, email, password_hash) VALUES (1, ?, 'hash')",
            ("runtime-plugin@example.com",),
        )
        self.db.execute(
            "INSERT INTO decks (id, name, owner_id) VALUES ('deck-runtime', 'Runtime', 1)"
        )
        self.db.execute(
            """
            INSERT INTO story_workspace_workspaces (id, name, owner_id)
            VALUES (?, 'Runtime Workspace', 1)
            """,
            (WORKSPACE_ID,),
        )
        self.db.execute(
            """
            INSERT INTO deck_plugin_releases (
                id, deck_plugin_id, deck_plugin_version, display_name,
                status, manifest_json, manifest_hash, workflow_definition_ref
            ) VALUES (?, ?, ?, 'Voice Deck', 'published', '{}', ?, 'workflow://voice')
            """,
            (
                "dpr_" + "4" * 32,
                self.lock.deck_plugin_id,
                self.lock.deck_plugin_version,
                MANIFEST_HASH,
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
                LOCK_ID,
                self.lock.deck_plugin_id,
                self.lock.deck_plugin_version,
                MANIFEST_HASH,
                self.lock_json,
            ),
        )
        self.db.execute(
            """
            INSERT INTO deck_plugin_bindings (
                deck_plugin_binding_id, deck_id, workspace_id, creator_id,
                deck_plugin_id, deck_plugin_version, binding_revision,
                status, applied_to
            ) VALUES (?, 'deck-runtime', ?, ?, ?, ?, 1, 'active', 'next_run')
            """,
            (
                "dpb_" + "5" * 32,
                WORKSPACE_ID,
                ACTOR_ID,
                self.lock.deck_plugin_id,
                self.lock.deck_plugin_version,
            ),
        )
        self.db.execute(
            """
            INSERT INTO workflow_preflights (
                workflow_preflight_id, request_fingerprint, deck_id,
                binding_revision, deck_plugin_id, deck_plugin_version,
                runtime_plugin_lock_id, deck_runtime_profile_id,
                deck_runtime_snapshot_id, input_hash, status, expires_at,
                created_by, created_at, updated_at
            ) VALUES (?, ?, 'deck-runtime', 1, ?, ?, ?, 'profile-1',
                      'snapshot-1', ?, 'passed', ?, ?, ?, ?)
            """,
            (
                "pf_" + "6" * 32,
                "sha256:" + "7" * 64,
                self.lock.deck_plugin_id,
                self.lock.deck_plugin_version,
                LOCK_ID,
                "sha256:" + "8" * 64,
                "2026-08-01T13:00:00Z",
                ACTOR_ID,
                "2026-08-01T12:00:00Z",
                "2026-08-01T12:00:00Z",
            ),
        )
        self.db.execute(
            """
            INSERT INTO workflow_runs (
                id, workspace_id, deck_plugin_id, deck_plugin_version,
                workflow_definition_ref, deck_runtime_snapshot_id, status,
                deck_plugin_manifest_hash, deck_plugin_binding_id,
                binding_revision, runtime_plugin_lock_id,
                workflow_preflight_id, idempotency_key, input_hash,
                semantic_fingerprint, status_version, created_by, created_at
            ) VALUES (?, ?, ?, ?, 'workflow://voice', 'snapshot-1', 'queued',
                      ?, ?, 1, ?, ?, 'runtime-start-1', ?, ?, 2, ?, ?)
            """,
            (
                RUN_ID,
                WORKSPACE_ID,
                self.lock.deck_plugin_id,
                self.lock.deck_plugin_version,
                MANIFEST_HASH,
                "dpb_" + "5" * 32,
                LOCK_ID,
                "pf_" + "6" * 32,
                "sha256:" + "8" * 64,
                "sha256:" + "9" * 64,
                ACTOR_ID,
                "2026-08-01T12:00:00Z",
            ),
        )
        self.db.commit()

    def headless_payload(
        self,
        *,
        status: str = "loaded",
        capabilities: list[str] | None = None,
    ) -> dict:
        return {
            "plugins": [
                {
                    "claude_code_plugin_id": PLUGIN_ID,
                    "resolved_version": PLUGIN_VERSION,
                    "artifact_digest": ARTIFACT_DIGEST,
                    "loaded_capabilities": capabilities
                    or ["deck.render", "voice.synthesize"],
                    "load_status": status,
                    "loaded_at": NOW.isoformat(),
                }
            ]
        }

    def reconcile_service(
        self,
        *,
        headless_payload: dict | Exception | None = None,
        cli_result: CompletedCliProcess | Exception | None = None,
        audit_sink=None,
        max_reconcile_attempts: int = 2,
    ) -> tuple[ReconcileService, FakeHeadlessRunner, FakeCliRunner]:
        headless = FakeHeadlessRunner(headless_payload or self.headless_payload())
        cli = FakeCliRunner(
            cli_result
            or CompletedCliProcess(
                exit_code=0,
                stdout=json.dumps(
                    {
                        "claude_code_plugin_id": PLUGIN_ID,
                        "resolved_version": PLUGIN_VERSION,
                        "status": "installed",
                    }
                ).encode(),
                stderr=b"",
            )
        )
        service = ReconcileService(
            self.db,
            source_policy=self.source_policy,
            settings_writer=self.settings_writer,
            headless_runner=headless,
            cli_source_policy=self.cli_policy,
            cli_runner=cli,
            cli_audit_sink=audit_sink,
            cli_timeout_seconds=17,
            max_cli_output_bytes=512,
            max_reconcile_attempts=max_reconcile_attempts,
            clock=lambda: NOW,
        )
        return service, headless, cli

    def materialization_manager(
        self,
        *,
        content: bytes = ARTIFACT_BYTES,
        retention: RetentionEvidence | None = RetentionEvidence(
            authoritative=True,
            pinned_or_recoverable=True,
            evidence_ref="retention://proof-1",
        ),
    ) -> tuple[MaterializationManager, FakeArtifactProvider, FakeRetentionReader]:
        provider = FakeArtifactProvider(
            StagedArtifact(
                content=content,
                artifact_digest=ARTIFACT_DIGEST,
                verification_status="legacy_unverified",
                signature_bundle_ref=None,
                retention_state="pinned",
                restore_source_ref="restore://staged-1",
            )
        )
        retention_reader = FakeRetentionReader(retention)
        manager = MaterializationManager(
            self.db,
            artifact_provider=provider,
            retention_evidence_reader=retention_reader,
            publisher=FileSystemAtomicPublisher(self.cache_root),
            clock=lambda: NOW,
        )
        return manager, provider, retention_reader


class RuntimePluginReconcileTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.fixture = RuntimePluginFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_datetime_parser_accepts_psycopg_native_datetime_and_iso_text(self) -> None:
        native = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)

        self.assertEqual(ReconcileService._parse_datetime(native), native)
        self.assertEqual(
            ReconcileService._parse_datetime("2026-08-01T12:00:00Z"),
            native,
        )
        with self.assertRaises(ValueError):
            ReconcileService._parse_datetime("not-a-timestamp")
        with self.assertRaises(TypeError):
            ReconcileService._parse_datetime(1)  # type: ignore[arg-type]

    def test_placement_fails_closed_for_pool_mismatch_and_production(self) -> None:
        base = self.fixture.placement.model_dump()
        with self.assertRaises(ValidationError):
            RuntimePlacementContext(**{**base, "runtime_pool_id": "another-pool"})
        with self.assertRaises(ValidationError):
            RuntimePlacementContext(**{**base, "deployment_tier": "production"})
        with self.assertRaises(ValidationError):
            RuntimePlacementContext(**{**base, "distribution_mode": "temporary"})

    async def test_settings_and_headless_reconcile_complete_before_query(self) -> None:
        service, headless, _ = self.fixture.reconcile_service()
        result = await service.declare_and_reconcile(
            self.fixture.lock,
            self.fixture.placement,
        )
        expected_settings = {
            "enabledPlugins": {PLUGIN_ID: True},
            "extraKnownMarketplaces": {
                "voice-decks": {
                    "source": "github",
                    "repo": "voice-decks/marketplace",
                }
            },
        }
        self.assertEqual(result.settings_intent, expected_settings)
        self.assertTrue(result.completed_before_first_query)
        self.assertEqual(self.fixture.settings_writer.calls[0]["settings"], expected_settings)
        self.assertEqual(
            headless.calls[0]["env"],
            {"CLAUDE_CODE_SYNC_PLUGIN_INSTALL": "true"},
        )
        self.assertEqual(headless.calls[0]["runtime_node_id"], "node-dev-1")
        attempt = self.fixture.db.execute(
            "SELECT * FROM runtime_plugin_reconcile_attempts"
        ).fetchone()
        self.assertEqual(attempt["reconcile_path"], "headless")
        self.assertEqual(attempt["result_status"], "succeeded")

    async def test_headless_output_is_strict_and_failures_are_audited(self) -> None:
        payload = self.fixture.headless_payload()
        payload["unexpected"] = True
        service, headless, _ = self.fixture.reconcile_service(
            headless_payload=payload,
            max_reconcile_attempts=2,
        )
        with self.assertRaises(ReconcileError) as caught:
            await service.declare_and_reconcile(
                self.fixture.lock,
                self.fixture.placement,
            )
        self.assertEqual(caught.exception.code, "RECONCILE_OUTPUT_INVALID")
        self.assertEqual(len(headless.calls), 2)
        attempts = self.fixture.db.execute(
            "SELECT result_status FROM runtime_plugin_reconcile_attempts"
        ).fetchall()
        self.assertEqual([row[0] for row in attempts], ["failed", "failed"])

    async def test_cli_uses_allowlisted_argv_shell_false_timeout_and_strict_json(self) -> None:
        audit = CollectingAuditSink()
        service, _, cli = self.fixture.reconcile_service(audit_sink=audit)
        result = await service.cli_install(PLUGIN_ID, PLUGIN_VERSION, "project")
        self.assertEqual(result.status, "installed")
        self.assertEqual(
            cli.calls,
            [
                (
                    [
                        "claude",
                        "plugin",
                        "install",
                        PLUGIN_ID,
                        "--scope",
                        "project",
                        "--json",
                    ],
                    17,
                    False,
                )
            ],
        )
        self.assertEqual(audit.records[0].result_status, "succeeded")
        self.assertEqual(audit.records[0].policy_revision, "policy-7")

    async def test_cli_denial_invalid_output_and_redacted_audit_fail_closed(self) -> None:
        audit = CollectingAuditSink()
        process = CompletedCliProcess(
            exit_code=1,
            stdout=b'{"unexpected":true}',
            stderr=b"authorization=super-secret-value",
        )
        service, _, cli = self.fixture.reconcile_service(
            cli_result=process,
            audit_sink=audit,
        )
        with self.assertRaises(ReconcileError) as caught:
            await service.cli_install(PLUGIN_ID, PLUGIN_VERSION)
        self.assertEqual(caught.exception.code, "CLI_EXECUTION_FAILED")
        self.assertNotIn("super-secret-value", audit.records[0].stderr_summary)
        self.assertIn("[REDACTED]", audit.records[0].stderr_summary)

        with self.assertRaises(ReconcileError) as denied:
            await service.cli_install("untrusted@unknown", "1.0.0")
        self.assertEqual(denied.exception.code, "CLI_POLICY_DENIED")
        self.assertEqual(len(cli.calls), 1)
        self.assertEqual(audit.records[-1].result_status, "failed")

        timeout_audit = CollectingAuditSink()
        timeout_service, _, timeout_cli = self.fixture.reconcile_service(
            cli_result=TimeoutError(),
            audit_sink=timeout_audit,
        )
        with self.assertRaises(ReconcileError) as timed_out:
            await timeout_service.cli_install(PLUGIN_ID, PLUGIN_VERSION)
        self.assertEqual(timed_out.exception.code, "CLI_EXECUTION_FAILED")
        self.assertEqual(timeout_cli.calls[0][1:], (17, False))
        self.assertEqual(timeout_audit.records[0].result_status, "failed")

    async def test_materialization_is_idempotent_and_keeps_three_dimensions(self) -> None:
        manager, provider, retention_reader = self.fixture.materialization_manager()
        first, second = await asyncio.gather(
            manager.materialize(
                self.fixture.placement,
                PLUGIN_ID,
                PLUGIN_VERSION,
                ARTIFACT_DIGEST,
            ),
            manager.materialize(
                self.fixture.placement,
                PLUGIN_ID,
                PLUGIN_VERSION,
                ARTIFACT_DIGEST,
            ),
        )
        self.assertEqual({first.reused, second.reused}, {False, True})
        self.assertEqual(
            first.materialization.runtime_materialization_id,
            second.materialization.runtime_materialization_id,
        )
        self.assertEqual(provider.calls, 1)
        self.assertEqual(retention_reader.calls, 1)
        self.assertEqual(
            first.materialization.declaration_status,
            DeclarationStatus.DECLARED,
        )
        self.assertEqual(
            first.materialization.materialization_status,
            MaterializationStatus.MATERIALIZED,
        )
        self.assertEqual(
            first.materialization.activation_status,
            ActivationStatus.LOADABLE,
        )
        self.assertEqual(first.materialization.materialized_digest, ARTIFACT_DIGEST)
        self.assertEqual(Path(first.materialization.cache_ref).read_bytes(), ARTIFACT_BYTES)

    async def test_digest_and_retention_evidence_fail_closed(self) -> None:
        bad_manager, _, _ = self.fixture.materialization_manager(content=b"tampered")
        with self.assertRaises(MaterializationError) as digest_error:
            await bad_manager.materialize(
                self.fixture.placement,
                PLUGIN_ID,
                PLUGIN_VERSION,
                ARTIFACT_DIGEST,
            )
        self.assertEqual(digest_error.exception.code, "MATERIALIZATION_DIGEST_MISMATCH")

        placement = RuntimePlacementContext(
            **{
                **self.fixture.placement.model_dump(),
                "policy_revision": "policy-8",
            }
        )
        no_retention, _, _ = self.fixture.materialization_manager(retention=None)
        with self.assertRaises(MaterializationError) as retention_error:
            await no_retention.materialize(
                placement,
                PLUGIN_ID,
                PLUGIN_VERSION,
                ARTIFACT_DIGEST,
            )
        self.assertEqual(
            retention_error.exception.code,
            "MATERIALIZATION_RETENTION_EVIDENCE_MISSING",
        )
        rows = self.fixture.db.execute(
            """
            SELECT declaration_status, materialization_status, activation_status,
                   attempt_count, last_error
            FROM runtime_plugin_materializations ORDER BY attempt_count
            """
        ).fetchall()
        self.assertTrue(all(row["declaration_status"] == "declared" for row in rows))
        self.assertTrue(all(row["materialization_status"] == "failed" for row in rows))
        self.assertTrue(all(row["activation_status"] == "inactive" for row in rows))

    async def test_receipt_is_immutable_and_projection_drives_existing_run_guard(self) -> None:
        manager, _, _ = self.fixture.materialization_manager()
        materialization = await manager.materialize(
            self.fixture.placement,
            PLUGIN_ID,
            PLUGIN_VERSION,
            ARTIFACT_DIGEST,
        )
        service, _, _ = self.fixture.reconcile_service()
        reconcile = await service.declare_and_reconcile(
            self.fixture.lock,
            self.fixture.placement,
        )
        receipt = service.create_load_receipt(
            runtime_lock=self.fixture.lock,
            placement_context=self.fixture.placement,
            reconcile_result=reconcile,
            materializations=[materialization],
        )
        self.assertTrue(receipt.required_entries_ready)
        self.assertEqual(receipt.scope, "session")
        self.assertEqual(receipt.readiness_state, "session_loaded")
        self.assertEqual(receipt.entries[0].verification_status, "legacy_unverified")
        projection = service.read_workflow_readiness(receipt.receipt_id)
        self.assertEqual(
            set(projection),
            {
                "receipt_id",
                "workflow_run_id",
                "runtime_plugin_lock_id",
                "runtime_plugin_lock_digest",
                "required_entries_ready",
            },
        )
        with self.assertRaises(ValidationError):
            RuntimeLoadReceiptReadiness.model_validate(receipt.model_dump())
        run_before = self.fixture.db.execute(
            "SELECT status, agent_session_id, runtime_load_receipt_id FROM workflow_runs"
        ).fetchone()
        self.assertEqual(dict(run_before), {
            "status": "queued",
            "agent_session_id": None,
            "runtime_load_receipt_id": None,
        })

        actor = AuthenticatedActorContext(
            workspace_id=WORKSPACE_ID,
            actor_id=ACTOR_ID,
        )
        create_agent_session_tables(self.fixture.db)
        session_id = "as_" + "9" * 32
        self.fixture.db.execute(
            """
            INSERT INTO agent_sessions (
                agent_session_id, workflow_run_id, runtime_load_receipt_id,
                runtime_environment_id, runtime_pool_id, distribution_mode,
                runtime_node_id, artifact_set_hash, policy_revision,
                deployment_tier, runtime_plugin_lock_id,
                runtime_plugin_lock_digest, settings_json, settings_hash,
                plugin_set_hash, session_request_key, attempt_number, status,
                created_at, lease_expires_at, owner_token
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '{}', ?, ?, ?, 1,
                      'creating', ?, ?, 'task-009-integration')
            """,
            (
                session_id,
                RUN_ID,
                receipt.receipt_id,
                receipt.runtime_environment_id,
                receipt.runtime_pool_id,
                receipt.distribution_mode,
                receipt.runtime_node_id,
                receipt.artifact_set_hash,
                receipt.policy_revision,
                receipt.deployment_tier,
                receipt.runtime_plugin_lock_id,
                receipt.runtime_plugin_lock_digest,
                "sha256:" + "a" * 64,
                "sha256:" + "b" * 64,
                "sha256:" + "c" * 64,
                NOW.isoformat(),
                (NOW + timedelta(seconds=30)).isoformat(),
            ),
        )
        self.fixture.db.commit()
        bad_projections = [
            {**projection, "workflow_run_id": "run_" + "a" * 32},
            {**projection, "runtime_plugin_lock_id": "rpl_" + "b" * 32},
            {**projection, "runtime_plugin_lock_digest": "sha256:" + "c" * 64},
            {**projection, "required_entries_ready": False},
        ]
        for bad_projection in bad_projections:
            run_service = WorkflowRunService(
                self.fixture.db,
                token_secret=TOKEN_SECRET,
                receipt_reader=lambda _receipt_id, value=bad_projection: value,
                clock=lambda: NOW,
            )
            with self.assertRaises(RuntimeLoadReceiptNotReady):
                await run_service.transition_run(
                    RUN_ID,
                    RunStatus.RUNNING,
                    actor,
                    runtime_load_receipt_id=receipt.receipt_id,
                    agent_session_id=session_id,
                )

        run_service = WorkflowRunService(
            self.fixture.db,
            token_secret=TOKEN_SECRET,
            receipt_reader=service.read_workflow_readiness,
            clock=lambda: NOW,
        )
        running = await run_service.transition_run(
            RUN_ID,
            RunStatus.RUNNING,
            actor,
            runtime_load_receipt_id=receipt.receipt_id,
            agent_session_id=session_id,
        )
        self.assertEqual(running.status, RunStatus.RUNNING)
        self.assertEqual(running.runtime_load_receipt_id, receipt.receipt_id)
        self.assertEqual(running.agent_session_id, session_id)

        with self.assertRaises(sqlite3.IntegrityError):
            self.fixture.db.execute(
                "UPDATE runtime_load_receipts SET required_entries_ready = 0 WHERE receipt_id = ?",
                (receipt.receipt_id,),
            )
        if self.fixture.db.in_transaction:
            self.fixture.db.rollback()
        with self.assertRaises(sqlite3.IntegrityError):
            self.fixture.db.execute(
                "DELETE FROM runtime_load_receipt_entries WHERE receipt_id = ?",
                (receipt.receipt_id,),
            )
        if self.fixture.db.in_transaction:
            self.fixture.db.rollback()

    async def test_receipt_closes_psycopg_validation_reads_before_persisting(self) -> None:
        manager, _, _ = self.fixture.materialization_manager()
        materialization = await manager.materialize(
            self.fixture.placement,
            PLUGIN_ID,
            PLUGIN_VERSION,
            ARTIFACT_DIGEST,
        )
        service, _, _ = self.fixture.reconcile_service()
        reconcile = await service.declare_and_reconcile(
            self.fixture.lock,
            self.fixture.placement,
        )

        class PsycopgReadTransactionConnection:
            def __init__(self, target):
                self.target = target
                self.read_transaction = False

            @property
            def in_transaction(self):
                return self.read_transaction or self.target.in_transaction

            def execute(self, statement, params=()):
                cursor = self.target.execute(statement, params)
                if statement.lstrip().upper().startswith("SELECT"):
                    self.read_transaction = True
                return cursor

            def rollback(self):
                self.target.rollback()
                self.read_transaction = False

            def commit(self):
                self.target.commit()
                self.read_transaction = False

        service.db = PsycopgReadTransactionConnection(self.fixture.db)

        receipt = service.create_load_receipt(
            runtime_lock=self.fixture.lock,
            placement_context=self.fixture.placement,
            reconcile_result=reconcile,
            materializations=[materialization],
        )

        self.assertTrue(receipt.required_entries_ready)

    async def test_missing_capability_creates_not_ready_receipt(self) -> None:
        manager, _, _ = self.fixture.materialization_manager()
        materialization = await manager.materialize(
            self.fixture.placement,
            PLUGIN_ID,
            PLUGIN_VERSION,
            ARTIFACT_DIGEST,
        )
        service, _, _ = self.fixture.reconcile_service(
            headless_payload=self.fixture.headless_payload(
                capabilities=["deck.render"],
            )
        )
        reconcile = await service.declare_and_reconcile(
            self.fixture.lock,
            self.fixture.placement,
        )
        receipt = service.create_load_receipt(
            runtime_lock=self.fixture.lock,
            placement_context=self.fixture.placement,
            reconcile_result=reconcile,
            materializations=[materialization],
        )
        self.assertFalse(receipt.required_entries_ready)
        self.assertEqual(receipt.entries[0].load_status, "load_failed")
        run = self.fixture.db.execute(
            "SELECT status, agent_session_id FROM workflow_runs WHERE id = ?",
            (RUN_ID,),
        ).fetchone()
        self.assertEqual(run["status"], "queued")
        self.assertIsNone(run["agent_session_id"])


if __name__ == "__main__":
    unittest.main()
