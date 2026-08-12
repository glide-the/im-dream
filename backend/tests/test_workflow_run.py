"""Focused Workflow Run transaction, state, retry, and receipt tests."""

from __future__ import annotations

import asyncio
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta, timezone
import hashlib
import hmac
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from pydantic import ValidationError

from backend.schema.legacy_main_sqlite import (
    create_agent_session_tables,
    create_tables,
)
from backend.models.workflow_run import (
    AuthenticatedActorContext,
    RunStatus,
    WorkflowRun,
)
from backend.services.workflow.run_service import (
    IDEMPOTENCY_CONFLICT,
    IllegalRunTransition,
    IdempotencyConflict,
    RetrySourceMismatch,
    RuntimeLoadReceiptNotReady,
    WorkflowRunError,
    WorkflowRunService,
)


TOKEN_SECRET = b"workflow-preflight-test-secret-32-bytes-minimum"
PLUGIN_ID = "voice-decks.story-dramatize"
PLUGIN_VERSION = "3.1.0"
MANIFEST_HASH = "sha256:" + "c" * 64
INPUT_HASH = "sha256:" + "a" * 64
SNAPSHOT_ID = "drs_" + "3" * 32
LOCK_ID = "rpl_" + "1" * 32
WORKSPACE_ID = "workspace-run-test"
ACTOR_ID = "1"
DECK_ID = "deck-run-test"
BINDING_ID = "dpb_" + "2" * 32
WORKFLOW_REF = "deck://voice-decks.story-dramatize/3.1.0/workflow.json"


class InjectedFailure(RuntimeError):
    pass


class RecordingConnection:
    def __init__(self, connection):
        self.connection = connection
        self.transition_parameters = None

    @property
    def in_transaction(self):
        return self.connection.in_transaction

    def execute(self, query, parameters=()):
        if "completed_at = CASE WHEN" in query:
            self.transition_parameters = parameters
        return self.connection.execute(query, parameters)

    def commit(self):
        return self.connection.commit()

    def rollback(self):
        return self.connection.rollback()


class WorkflowRunFixture:
    def __init__(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "workflow-run.db"
        self.now = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)
        self.voice_message_time = self.now
        self.receipts: dict[str, dict] = {}
        self.fail_at: str | None = None
        self.db = self.connect()
        create_tables(self.db)
        create_agent_session_tables(self.db)
        self.lock_json = self._seed_dependencies()
        self.actor = AuthenticatedActorContext(
            workspace_id=WORKSPACE_ID,
            actor_id=ACTOR_ID,
        )
        self.service = self.make_service(self.db)

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10, check_same_thread=False)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("PRAGMA journal_mode=WAL")
        return db

    def close(self) -> None:
        self.db.close()
        self.temp_dir.cleanup()

    def make_service(self, db: sqlite3.Connection) -> WorkflowRunService:
        return WorkflowRunService(
            db,
            token_secret=TOKEN_SECRET,
            receipt_reader=lambda receipt_id: self.receipts[receipt_id],
            clock=lambda: self.now,
            failure_injector=self._inject_failure,
        )

    def _inject_failure(self, checkpoint: str) -> None:
        if checkpoint == self.fail_at:
            raise InjectedFailure(checkpoint)

    def _seed_dependencies(self) -> str:
        self.db.execute(
            "INSERT INTO users (id, email, password_hash) VALUES (1, ?, 'hash')",
            ("workflow-run@example.com",),
        )
        self.db.execute(
            "INSERT INTO decks (id, name, owner_id) VALUES (?, 'Run Deck', 1)",
            (DECK_ID,),
        )
        self.db.execute(
            """
            INSERT INTO story_workspace_workspaces (id, name, owner_id)
            VALUES (?, 'Run Workspace', 1)
            """,
            (WORKSPACE_ID,),
        )
        self.db.execute(
            """
            INSERT INTO deck_plugin_releases (
                id, deck_plugin_id, deck_plugin_version, display_name,
                status, manifest_json, manifest_hash, workflow_definition_ref
            ) VALUES (?, ?, ?, 'Voice Deck', 'published', '{}', ?, ?)
            """,
            (
                "dpr_" + "4" * 32,
                PLUGIN_ID,
                PLUGIN_VERSION,
                MANIFEST_HASH,
                WORKFLOW_REF,
            ),
        )
        lock_json = json.dumps(
            {
                "runtime_plugin_lock_id": LOCK_ID,
                "deck_plugin_id": PLUGIN_ID,
                "deck_plugin_version": PLUGIN_VERSION,
                "deck_plugin_manifest_hash": MANIFEST_HASH,
                "claude_code_plugins": [
                    {
                        "claude_code_plugin_id": "ink-dream-tools@voice-decks",
                        "resolved_version": "1.4.2",
                        "source_ref": "trusted:voice-decks",
                        "artifact_digest": "sha256:" + "d" * 64,
                        "required": True,
                        "capability_bindings": ["story.context.read"],
                    }
                ],
            },
            sort_keys=True,
        )
        self.db.execute(
            """
            INSERT INTO deck_runtime_plugin_locks (
                id, deck_plugin_id, deck_plugin_version,
                deck_plugin_manifest_hash, lock_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (LOCK_ID, PLUGIN_ID, PLUGIN_VERSION, MANIFEST_HASH, lock_json),
        )
        self.db.execute(
            """
            INSERT INTO deck_plugin_bindings (
                deck_plugin_binding_id, deck_id, workspace_id, creator_id,
                deck_plugin_id, deck_plugin_version, binding_revision,
                status, applied_to
            ) VALUES (?, ?, ?, ?, ?, ?, 1, 'active', 'next_run')
            """,
            (
                BINDING_ID,
                DECK_ID,
                WORKSPACE_ID,
                ACTOR_ID,
                PLUGIN_ID,
                PLUGIN_VERSION,
            ),
        )
        self.db.commit()
        return lock_json

    def issue_preflight(
        self,
        *,
        input_hash: str = INPUT_HASH,
        snapshot_id: str = SNAPSHOT_ID,
        actor_id: str = ACTOR_ID,
        expires_at: datetime | None = None,
    ) -> tuple[str, str]:
        preflight_id = "pf_" + hashlib.md5(
            f"{self.now.isoformat()}:{self.db.total_changes}".encode("utf-8")
        ).hexdigest()
        expires = expires_at or (self.now + timedelta(minutes=5))
        payload = self._canonical_json(
            {
                "preflight_id": preflight_id,
                "binding_revision": 1,
                "input_hash": input_hash,
                "deck_runtime_snapshot_id": snapshot_id,
                "runtime_plugin_lock_id": LOCK_ID,
                "expires_at": self._iso(expires),
            }
        )
        signature = hmac.new(TOKEN_SECRET, payload, hashlib.sha256).digest()
        token = "pft_" + base64.urlsafe_b64encode(signature).rstrip(b"=").decode(
            "ascii"
        )
        token_hash = "sha256:" + hashlib.sha256(token.encode("utf-8")).hexdigest()
        self.db.execute(
            """
            INSERT INTO workflow_preflights (
                workflow_preflight_id, request_fingerprint, deck_id,
                binding_revision, deck_plugin_id, deck_plugin_version,
                runtime_plugin_lock_id, deck_runtime_profile_id,
                deck_runtime_snapshot_id, deck_runtime_snapshot_summary_hash,
                input_hash, status, expires_at, preflight_token_hash,
                created_by, created_at, updated_at
            ) VALUES (?, ?, ?, 1, ?, ?, ?, 'drp_test', ?, ?, ?, 'passed',
                      ?, ?, ?, ?, ?)
            """,
            (
                preflight_id,
                "sha256:" + hashlib.sha256(preflight_id.encode()).hexdigest(),
                DECK_ID,
                PLUGIN_ID,
                PLUGIN_VERSION,
                LOCK_ID,
                snapshot_id,
                "sha256:" + "e" * 64,
                input_hash,
                self._iso(expires),
                token_hash,
                actor_id,
                self._iso(self.now),
                self._iso(self.now),
            ),
        )
        self.db.commit()
        return preflight_id, token

    async def create(
        self,
        key: str = "start-1",
        *,
        preflight: tuple[str, str] | None = None,
        source_voice_thread_id: str | None = "voice-thread-1",
        actor: AuthenticatedActorContext | None = None,
    ) -> WorkflowRun:
        preflight_id, token = preflight or self.issue_preflight()
        return await self.service.create_run(
            preflight_id,
            token,
            key,
            source_voice_thread_id,
            actor or self.actor,
            source_message_id="voice-message-1"
            if source_voice_thread_id is not None
            else None,
            source_message_time=self.voice_message_time
            if source_voice_thread_id is not None
            else None,
        )

    def ready_receipt(self, run: WorkflowRun, receipt_id: str = "receipt-1") -> str:
        if not receipt_id.startswith("rlr_"):
            receipt_id = "rlr_" + hashlib.md5(receipt_id.encode()).hexdigest()
        digest = self.service._lock_digest(self.lock_json)
        self.receipts[receipt_id] = {
            "receipt_id": receipt_id,
            "workflow_run_id": run.workflow_run_id,
            "runtime_plugin_lock_id": run.runtime_plugin_lock_id,
            "runtime_plugin_lock_digest": digest,
            "required_entries_ready": True,
        }
        self.db.execute(
            """
            INSERT INTO runtime_load_receipts (
                receipt_id, workflow_run_id, runtime_plugin_lock_id,
                runtime_plugin_lock_digest, runtime_environment_id,
                runtime_pool_id, distribution_mode, runtime_node_id,
                artifact_set_hash, policy_revision, deployment_tier,
                scope, readiness_state, required_entries_ready, created_at
            ) VALUES (?, ?, ?, ?, 'env-test', 'env-test', 'local_persistent',
                      'node-test', ?, 'policy-test', 'test', 'session',
                      'session_loaded', 1, ?)
            """,
            (
                receipt_id,
                run.workflow_run_id,
                run.runtime_plugin_lock_id,
                digest,
                "sha256:" + "f" * 64,
                self._iso(self.now),
            ),
        )
        self.db.commit()
        return receipt_id

    def ready_session(self, run: WorkflowRun, receipt_id: str) -> str:
        session_id = "as_" + hashlib.md5(
            f"{run.workflow_run_id}:{receipt_id}".encode()
        ).hexdigest()
        receipt = self.db.execute(
            "SELECT * FROM runtime_load_receipts WHERE receipt_id = ?",
            (receipt_id,),
        ).fetchone()
        request_hash = "sha256:" + hashlib.sha256(
            f"{run.workflow_run_id}:{receipt_id}".encode()
        ).hexdigest()
        self.db.execute(
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
                      'creating', ?, ?, 'test-owner')
            """,
            (
                session_id,
                run.workflow_run_id,
                receipt_id,
                receipt["runtime_environment_id"],
                receipt["runtime_pool_id"],
                receipt["distribution_mode"],
                receipt["runtime_node_id"],
                receipt["artifact_set_hash"],
                receipt["policy_revision"],
                receipt["deployment_tier"],
                run.runtime_plugin_lock_id,
                receipt["runtime_plugin_lock_digest"],
                "sha256:" + "a" * 64,
                "sha256:" + "b" * 64,
                request_hash,
                self._iso(self.now),
                self._iso(self.now + timedelta(seconds=30)),
            ),
        )
        self.db.commit()
        return session_id

    @staticmethod
    def _canonical_json(value: object) -> bytes:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

    @staticmethod
    def _iso(value: datetime) -> str:
        return value.astimezone(UTC).isoformat(timespec="microseconds")


class WorkflowRunTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.fixture = WorkflowRunFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    async def test_create_freezes_server_sources_and_writes_atomic_initial_history(self):
        preflight_id, token = self.fixture.issue_preflight()
        run = await self.fixture.create(preflight=(preflight_id, token))

        self.assertEqual(run.status, RunStatus.QUEUED)
        self.assertEqual(run.status_version, 2)
        self.assertEqual(run.workspace_id, WORKSPACE_ID)
        self.assertEqual(run.created_by, ACTOR_ID)
        self.assertEqual(run.workflow_preflight_id, preflight_id)
        self.assertEqual(run.deck_plugin_manifest_hash, MANIFEST_HASH)
        self.assertEqual(run.deck_plugin_binding_id, BINDING_ID)
        self.assertEqual(run.source_voice_thread_id, "voice-thread-1")
        self.assertEqual(run.source_message_id, "voice-message-1")
        self.assertEqual(run.source_message_time, self.fixture.now)
        transitions = self.fixture.service.list_transitions(
            run.workflow_run_id,
            self.fixture.actor,
        )
        self.assertEqual(
            [(item.from_status, item.to_status) for item in transitions],
            [
                (None, RunStatus.PREFLIGHT),
                (RunStatus.PREFLIGHT, RunStatus.QUEUED),
            ],
        )
        consumption = self.fixture.db.execute(
            "SELECT * FROM workflow_run_token_consumptions"
        ).fetchone()
        self.assertIsNotNone(consumption)
        self.assertNotIn(token, " ".join(str(value) for value in consumption))
        self.assertTrue(consumption["token_digest"].startswith("hmac-sha256:"))

    async def test_postgres_datetime_rows_are_normalized_to_utc(self):
        run = await self.fixture.create()
        row = dict(
            self.fixture.db.execute(
                "SELECT * FROM workflow_runs WHERE id = ?",
                (run.workflow_run_id,),
            ).fetchone()
        )
        east_eight = timezone(timedelta(hours=8))
        row.update(
            {
                "status": "completed",
                "runtime_load_receipt_id": "receipt-postgres-native-time",
                "agent_session_id": "as_" + "8" * 32,
                "source_message_time": datetime(2026, 8, 1, 18, 0, tzinfo=east_eight),
                "created_at": datetime(2026, 8, 1, 17, 0, tzinfo=east_eight),
                "started_at": datetime(2026, 8, 1, 18, 30, tzinfo=east_eight),
                "completed_at": datetime(2026, 8, 1, 19, 0, tzinfo=east_eight),
            }
        )

        parsed = self.fixture.service._row_to_run(row)

        self.assertEqual(parsed.created_at, datetime(2026, 8, 1, 9, 0, tzinfo=UTC))
        self.assertEqual(
            parsed.source_message_time,
            datetime(2026, 8, 1, 10, 0, tzinfo=UTC),
        )
        self.assertEqual(parsed.started_at, datetime(2026, 8, 1, 10, 30, tzinfo=UTC))
        self.assertEqual(parsed.completed_at, datetime(2026, 8, 1, 11, 0, tzinfo=UTC))

    async def test_read_run_can_join_an_existing_read_transaction(self):
        created = await self.fixture.create()
        self.fixture.db.execute("BEGIN")
        service = self.fixture.make_service(self.fixture.db)

        observed = service.read_run(created.workflow_run_id, self.fixture.actor)

        self.assertEqual(observed.workflow_run_id, created.workflow_run_id)
        self.assertTrue(self.fixture.db.in_transaction)
        self.fixture.db.rollback()

    async def test_mutation_still_rejects_a_caller_owned_transaction(self):
        preflight = self.fixture.issue_preflight()
        self.fixture.db.execute("BEGIN")
        service = self.fixture.make_service(self.fixture.db)

        with self.assertRaisesRegex(RuntimeError, "clean transaction boundary"):
            await service.create_run(
                preflight[0],
                preflight[1],
                "caller-owned-transaction",
                "voice-thread-1",
                self.fixture.actor,
                source_message_id="voice-message-1",
                source_message_time=self.fixture.voice_message_time,
            )
        self.fixture.db.rollback()

    async def test_terminal_transition_uses_a_postgres_boolean_parameter(self):
        created = await self.fixture.create()
        connection = RecordingConnection(self.fixture.db)
        service = self.fixture.make_service(connection)

        cancelled = await service.transition_run(
            created.workflow_run_id,
            RunStatus.CANCELLED,
            self.fixture.actor,
            reason_code="boolean-contract",
        )

        self.assertEqual(cancelled.status, RunStatus.CANCELLED)
        self.assertIsNotNone(connection.transition_parameters)
        self.assertIs(type(connection.transition_parameters[8]), bool)

    def test_datetime_parser_keeps_iso_text_compatibility_and_rejects_invalid_values(self):
        self.assertEqual(
            self.fixture.service._parse_datetime("2026-08-01T10:00:00Z"),
            datetime(2026, 8, 1, 10, 0, tzinfo=UTC),
        )
        with self.assertRaises(ValueError):
            self.fixture.service._parse_datetime("not-a-timestamp")
        with self.assertRaises(TypeError):
            self.fixture.service._parse_datetime(1)  # type: ignore[arg-type]

    async def test_exact_replay_survives_token_expiry_without_new_transition(self):
        preflight = self.fixture.issue_preflight()
        first = await self.fixture.create(preflight=preflight)
        self.fixture.now += timedelta(hours=1)
        replayed = await self.fixture.create(preflight=preflight)
        self.assertEqual(replayed.workflow_run_id, first.workflow_run_id)
        self.assertEqual(
            self.fixture.db.execute(
                "SELECT COUNT(*) FROM workflow_run_transitions"
            ).fetchone()[0],
            2,
        )

    async def test_equivalent_fresh_token_maps_to_original_run(self):
        first = await self.fixture.create()
        second_preflight = self.fixture.issue_preflight()
        replayed = await self.fixture.create(preflight=second_preflight)
        self.assertEqual(replayed.workflow_run_id, first.workflow_run_id)
        self.assertEqual(replayed.semantic_fingerprint, first.semantic_fingerprint)
        self.assertEqual(
            self.fixture.db.execute(
                "SELECT COUNT(*) FROM workflow_run_token_consumptions"
            ).fetchone()[0],
            2,
        )
        self.assertEqual(
            self.fixture.db.execute("SELECT COUNT(*) FROM workflow_runs").fetchone()[0],
            1,
        )

    async def test_token_and_key_conflicts_fail_closed_without_run_disclosure(self):
        preflight = self.fixture.issue_preflight()
        original = await self.fixture.create(preflight=preflight)
        cases = (
            (
                preflight,
                "different-key",
                "voice-thread-1",
                self.fixture.actor,
            ),
            (
                preflight,
                "start-1",
                "changed-voice-thread",
                self.fixture.actor,
            ),
            (
                preflight,
                "start-1",
                "voice-thread-1",
                AuthenticatedActorContext(
                    workspace_id="other-workspace",
                    actor_id=ACTOR_ID,
                ),
            ),
            (
                preflight,
                "start-1",
                "voice-thread-1",
                AuthenticatedActorContext(
                    workspace_id=WORKSPACE_ID,
                    actor_id="other-actor",
                ),
            ),
        )
        for token_pair, key, voice, actor in cases:
            with self.subTest(key=key, actor=actor), self.assertRaises(
                IdempotencyConflict
            ) as captured:
                await self.fixture.create(
                    key,
                    preflight=token_pair,
                    source_voice_thread_id=voice,
                    actor=actor,
                )
            self.assertEqual(captured.exception.code, IDEMPOTENCY_CONFLICT)
            self.assertNotIn(original.workflow_run_id, str(captured.exception))

        fresh = self.fixture.issue_preflight()
        with self.assertRaises(IdempotencyConflict):
            await self.fixture.create(
                preflight=fresh,
                source_voice_thread_id="changed-voice-thread",
            )
        self.assertIsNone(
            self.fixture.db.execute(
                "SELECT consumed_at FROM workflow_preflights WHERE workflow_preflight_id = ?",
                (fresh[0],),
            ).fetchone()[0]
        )
        self.assertEqual(
            self.fixture.db.execute("SELECT COUNT(*) FROM workflow_runs").fetchone()[0],
            1,
        )

    async def test_voice_source_tuple_is_complete_and_part_of_idempotency(self):
        preflight = self.fixture.issue_preflight()
        with self.assertRaises(WorkflowRunError) as incomplete:
            await self.fixture.service.create_run(
                preflight[0],
                preflight[1],
                "voice-incomplete",
                "voice-thread-1",
                self.fixture.actor,
            )
        self.assertEqual(incomplete.exception.code, "INVALID_RUN_REQUEST")

        run = await self.fixture.create(preflight=preflight)
        fresh = self.fixture.issue_preflight()
        with self.assertRaises(IdempotencyConflict):
            await self.fixture.service.create_run(
                fresh[0],
                fresh[1],
                run.idempotency_key,
                run.source_voice_thread_id,
                self.fixture.actor,
                source_message_id="voice-message-changed",
                source_message_time=run.source_message_time,
            )

    async def test_invalid_expired_and_unauthorized_preflights_create_nothing(self):
        preflight_id, token = self.fixture.issue_preflight()
        with self.assertRaises(WorkflowRunError) as invalid:
            await self.fixture.create(preflight=(preflight_id, token + "x"))
        self.assertEqual(invalid.exception.code, "PREFLIGHT_TOKEN_INVALID")

        expired = self.fixture.issue_preflight(expires_at=self.fixture.now - timedelta(seconds=1))
        with self.assertRaises(WorkflowRunError) as expired_error:
            await self.fixture.create(key="expired", preflight=expired)
        self.assertEqual(expired_error.exception.code, "PREFLIGHT_TOKEN_EXPIRED")

        unauthorized = self.fixture.issue_preflight(actor_id="other-actor")
        with self.assertRaises(WorkflowRunError) as denied:
            await self.fixture.create(key="denied", preflight=unauthorized)
        self.assertEqual(denied.exception.code, "PREFLIGHT_NOT_FOUND_OR_NOT_AUTHORIZED")
        self.assertEqual(
            self.fixture.db.execute("SELECT COUNT(*) FROM workflow_runs").fetchone()[0],
            0,
        )
        self.assertEqual(
            self.fixture.db.execute(
                "SELECT COUNT(*) FROM workflow_run_token_consumptions"
            ).fetchone()[0],
            0,
        )

    async def test_create_failure_injection_rolls_back_run_token_and_transitions(self):
        preflight = self.fixture.issue_preflight()
        for checkpoint in (
            "run_written",
            "token_mapped",
            "initial_transition_written",
            "queued_transition_written",
        ):
            with self.subTest(checkpoint=checkpoint):
                self.fixture.fail_at = checkpoint
                with self.assertRaises(InjectedFailure):
                    await self.fixture.create(preflight=preflight)
                for table in (
                    "workflow_runs",
                    "workflow_run_token_consumptions",
                    "workflow_run_transitions",
                ):
                    self.assertEqual(
                        self.fixture.db.execute(
                            f"SELECT COUNT(*) FROM {table}"
                        ).fetchone()[0],
                        0,
                    )
                self.assertIsNone(
                    self.fixture.db.execute(
                        """
                        SELECT consumed_at FROM workflow_preflights
                        WHERE workflow_preflight_id = ?
                        """,
                        (preflight[0],),
                    ).fetchone()[0]
                )
        self.fixture.fail_at = None
        created = await self.fixture.create(preflight=preflight)
        self.assertEqual(created.status, RunStatus.QUEUED)

    async def test_full_legal_path_keeps_status_and_transition_versions_in_sync(self):
        run = await self.fixture.create()
        receipt_id = self.fixture.ready_receipt(run)
        session_id = self.fixture.ready_session(run, receipt_id)
        run = await self.fixture.service.transition_run(
            run.workflow_run_id,
            RunStatus.RUNNING,
            self.fixture.actor,
            runtime_load_receipt_id=receipt_id,
            agent_session_id=session_id,
        )
        self.assertEqual(run.runtime_load_receipt_id, receipt_id)
        self.assertEqual(run.agent_session_id, session_id)
        self.assertIsNotNone(run.started_at)
        run = await self.fixture.service.transition_run(
            run.workflow_run_id,
            RunStatus.OUTPUT_VALIDATING,
            self.fixture.actor,
        )
        run = await self.fixture.service.transition_run(
            run.workflow_run_id,
            RunStatus.PENDING_REVIEW,
            self.fixture.actor,
            normalized_result_ready=True,
        )
        run = await self.fixture.service.transition_run(
            run.workflow_run_id,
            RunStatus.CONFIRMED,
            self.fixture.actor,
            review_items_approved=True,
        )
        run = await self.fixture.service.transition_run(
            run.workflow_run_id,
            RunStatus.COMPLETED,
            self.fixture.actor,
        )
        self.assertEqual(run.status, RunStatus.COMPLETED)
        self.assertEqual(run.status_version, 7)
        self.assertIsNotNone(run.completed_at)
        transitions = self.fixture.service.list_transitions(
            run.workflow_run_id,
            self.fixture.actor,
        )
        self.assertEqual([item.transition_seq for item in transitions], list(range(1, 8)))
        self.assertEqual(transitions[-1].to_status, RunStatus.COMPLETED)

    async def test_running_transition_closes_psycopg_receipt_read_before_write(self):
        run = await self.fixture.create("postgres-receipt-boundary")
        receipt_id = self.fixture.ready_receipt(run, "postgres-receipt-boundary")
        session_id = self.fixture.ready_session(run, receipt_id)

        class PsycopgReadTransactionConnection:
            def __init__(self, target):
                self.target = target
                self.read_transaction = False

            @property
            def in_transaction(self):
                return self.read_transaction or self.target.in_transaction

            def execute(self, statement, params=()):
                normalized = statement.lstrip().upper()
                if normalized == "BEGIN" and self.read_transaction:
                    raise RuntimeError("cannot begin inside psycopg read transaction")
                cursor = self.target.execute(statement, params)
                if normalized.startswith("SELECT"):
                    self.read_transaction = True
                return cursor

            def rollback(self):
                self.target.rollback()
                self.read_transaction = False

            def commit(self):
                self.target.commit()
                self.read_transaction = False

        connection = PsycopgReadTransactionConnection(self.fixture.db)

        def read_receipt(selected_receipt_id):
            connection.execute(
                "SELECT receipt_id FROM runtime_load_receipts WHERE receipt_id = ?",
                (selected_receipt_id,),
            ).fetchone()
            return self.fixture.receipts[selected_receipt_id]

        service = WorkflowRunService(
            connection,
            token_secret=TOKEN_SECRET,
            receipt_reader=read_receipt,
            clock=lambda: self.fixture.now,
        )

        running = await service.transition_run(
            run.workflow_run_id,
            RunStatus.RUNNING,
            self.fixture.actor,
            runtime_load_receipt_id=receipt_id,
            agent_session_id=session_id,
        )

        self.assertEqual(running.status, RunStatus.RUNNING)

    async def test_confirmed_rejected_and_cancelled_legal_terminal_paths(self):
        async def advance_to_pending(key: str) -> WorkflowRun:
            candidate = await self.fixture.create(key)
            receipt_id = self.fixture.ready_receipt(candidate, f"receipt-{key}")
            session_id = self.fixture.ready_session(candidate, receipt_id)
            candidate = await self.fixture.service.transition_run(
                candidate.workflow_run_id,
                RunStatus.RUNNING,
                self.fixture.actor,
                runtime_load_receipt_id=receipt_id,
                agent_session_id=session_id,
            )
            candidate = await self.fixture.service.transition_run(
                candidate.workflow_run_id,
                RunStatus.OUTPUT_VALIDATING,
                self.fixture.actor,
            )
            return await self.fixture.service.transition_run(
                candidate.workflow_run_id,
                RunStatus.PENDING_REVIEW,
                self.fixture.actor,
                normalized_result_ready=True,
            )

        rejected = await advance_to_pending("reject-path")
        rejected = await self.fixture.service.transition_run(
            rejected.workflow_run_id,
            RunStatus.REJECTED,
            self.fixture.actor,
            reason_code="review_rejected",
        )
        self.assertEqual(rejected.status, RunStatus.REJECTED)
        self.assertIsNotNone(rejected.completed_at)

        confirmed = await advance_to_pending("confirm-path")
        confirmed = await self.fixture.service.transition_run(
            confirmed.workflow_run_id,
            RunStatus.CONFIRMED,
            self.fixture.actor,
            review_items_approved=True,
        )
        confirmed = await self.fixture.service.transition_run(
            confirmed.workflow_run_id,
            RunStatus.COMPLETED,
            self.fixture.actor,
        )
        self.assertEqual(confirmed.status, RunStatus.COMPLETED)

        cancelled = await self.fixture.create("cancel-path")
        cancelled = await self.fixture.service.transition_run(
            cancelled.workflow_run_id,
            RunStatus.CANCELLED,
            self.fixture.actor,
            reason_code="user_cancelled",
        )
        self.assertEqual(cancelled.status, RunStatus.CANCELLED)
        with self.assertRaises(IllegalRunTransition):
            await self.fixture.service.transition_run(
                cancelled.workflow_run_id,
                RunStatus.QUEUED,
                self.fixture.actor,
            )

    async def test_illegal_guards_and_terminal_non_resurrection(self):
        run = await self.fixture.create()
        with self.assertRaises(IllegalRunTransition):
            await self.fixture.service.transition_run(
                run.workflow_run_id,
                RunStatus.PENDING_REVIEW,
                self.fixture.actor,
            )
        with self.assertRaises(IllegalRunTransition):
            await self.fixture.service.transition_run(
                run.workflow_run_id,
                RunStatus.FAILED,
                self.fixture.actor,
            )
        failed = await self.fixture.service.transition_run(
            run.workflow_run_id,
            RunStatus.FAILED,
            self.fixture.actor,
            failed_step="agent_start",
            error_code="AGENT_START_FAILED",
        )
        with self.assertRaises(IllegalRunTransition):
            await self.fixture.service.transition_run(
                failed.workflow_run_id,
                RunStatus.QUEUED,
                self.fixture.actor,
            )
        self.assertEqual(
            self.fixture.db.execute(
                "SELECT COUNT(*) FROM workflow_run_transitions"
            ).fetchone()[0],
            3,
        )

    async def test_receipt_guard_rejects_every_mismatch_then_binds_once(self):
        run = await self.fixture.create()
        receipt_id = self.fixture.ready_receipt(run)
        session_id = self.fixture.ready_session(run, receipt_id)
        base = dict(self.fixture.receipts[receipt_id])
        cases = (
            {"workflow_run_id": "run_" + "9" * 32},
            {"runtime_plugin_lock_id": "rpl_" + "8" * 32},
            {"runtime_plugin_lock_digest": "sha256:" + "9" * 64},
            {"required_entries_ready": False},
        )
        for updates in cases:
            with self.subTest(updates=updates):
                self.fixture.receipts[receipt_id] = {**base, **updates}
                with self.assertRaises(RuntimeLoadReceiptNotReady):
                    await self.fixture.service.transition_run(
                        run.workflow_run_id,
                        RunStatus.RUNNING,
                        self.fixture.actor,
                        runtime_load_receipt_id=receipt_id,
                        agent_session_id=session_id,
                    )
        self.fixture.receipts[receipt_id] = base
        running = await self.fixture.service.transition_run(
            run.workflow_run_id,
            RunStatus.RUNNING,
            self.fixture.actor,
            runtime_load_receipt_id=receipt_id,
            agent_session_id=session_id,
        )
        self.assertEqual(running.runtime_load_receipt_id, receipt_id)
        self.assertEqual(running.agent_session_id, session_id)
        with self.assertRaises(sqlite3.IntegrityError):
            self.fixture.db.execute(
                "UPDATE workflow_runs SET runtime_load_receipt_id = 'receipt-other' WHERE id = ?",
                (run.workflow_run_id,),
            )
        self.fixture.db.rollback()

    async def test_transition_failure_rolls_back_current_state_and_history(self):
        run = await self.fixture.create()
        receipt_id = self.fixture.ready_receipt(run)
        session_id = self.fixture.ready_session(run, receipt_id)
        self.fixture.fail_at = "status_transition_written"
        with self.assertRaises(InjectedFailure):
            await self.fixture.service.transition_run(
                run.workflow_run_id,
                RunStatus.RUNNING,
                self.fixture.actor,
                runtime_load_receipt_id=receipt_id,
                agent_session_id=session_id,
            )
        row = self.fixture.db.execute(
            "SELECT status, status_version, runtime_load_receipt_id FROM workflow_runs"
        ).fetchone()
        self.assertEqual(tuple(row), ("queued", 2, None))
        self.assertEqual(
            self.fixture.db.execute(
                "SELECT status FROM agent_sessions WHERE agent_session_id = ?",
                (session_id,),
            ).fetchone()[0],
            "creating",
        )
        self.assertEqual(
            self.fixture.db.execute(
                "SELECT COUNT(*) FROM workflow_run_transitions"
            ).fetchone()[0],
            2,
        )

    async def test_database_guards_make_history_and_provenance_immutable(self):
        run = await self.fixture.create()
        statements = (
            "UPDATE workflow_run_token_consumptions SET actor_id = 'other'",
            "DELETE FROM workflow_run_token_consumptions",
            "UPDATE workflow_run_transitions SET reason_code = 'changed'",
            "DELETE FROM workflow_run_transitions",
            "UPDATE workflow_runs SET workspace_id = 'other'",
            "UPDATE workflow_runs SET semantic_fingerprint = 'sha256:' || printf('%064d', 0)",
            "UPDATE workflow_runs SET source_message_id = 'changed'",
        )
        for statement in statements:
            with self.subTest(statement=statement), self.assertRaises(
                sqlite3.IntegrityError
            ):
                self.fixture.db.execute(statement)
            self.fixture.db.rollback()
        stored = self.fixture.db.execute(
            "SELECT workspace_id, semantic_fingerprint FROM workflow_runs WHERE id = ?",
            (run.workflow_run_id,),
        ).fetchone()
        self.assertEqual(stored["workspace_id"], WORKSPACE_ID)
        self.assertEqual(stored["semantic_fingerprint"], run.semantic_fingerprint)

    async def test_retry_uses_fresh_preflight_and_preserves_frozen_source(self):
        original = await self.fixture.create()
        original = await self.fixture.service.transition_run(
            original.workflow_run_id,
            RunStatus.FAILED,
            self.fixture.actor,
            failed_step="agent_start",
            error_code="AGENT_START_FAILED",
        )
        fresh = self.fixture.issue_preflight()
        retry = await self.fixture.service.retry_run(
            original.workflow_run_id,
            self.fixture.actor,
            preflight_id=fresh[0],
            preflight_token=fresh[1],
            idempotency_key="retry-1",
        )
        self.assertNotEqual(retry.workflow_run_id, original.workflow_run_id)
        self.assertEqual(retry.retry_of_run_id, original.workflow_run_id)
        for field in (
            "deck_plugin_id",
            "deck_plugin_version",
            "workflow_definition_ref",
            "deck_runtime_snapshot_id",
            "deck_plugin_manifest_hash",
            "deck_plugin_binding_id",
            "binding_revision",
            "runtime_plugin_lock_id",
            "input_hash",
            "source_voice_thread_id",
            "source_message_id",
            "source_message_time",
        ):
            self.assertEqual(getattr(retry, field), getattr(original, field))
        self.assertIsNone(retry.runtime_load_receipt_id)
        self.assertIsNone(retry.agent_session_id)

        changed_input = self.fixture.issue_preflight(
            input_hash="sha256:" + "b" * 64
        )
        with self.assertRaises(RetrySourceMismatch):
            await self.fixture.service.retry_run(
                original.workflow_run_id,
                self.fixture.actor,
                preflight_id=changed_input[0],
                preflight_token=changed_input[1],
                idempotency_key="retry-changed-input",
            )
        self.assertIsNone(
            self.fixture.db.execute(
                "SELECT consumed_at FROM workflow_preflights WHERE workflow_preflight_id = ?",
                (changed_input[0],),
            ).fetchone()[0]
        )

    async def test_schema_is_idempotent_strict_and_has_exact_scope_constraint(self):
        create_tables(self.fixture.db)
        sql = self.fixture.db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='workflow_runs'"
        ).fetchone()[0]
        normalized = " ".join(sql.split())
        self.assertIn("UNIQUE(workspace_id, created_by, idempotency_key)", normalized)
        tables = {
            row[0]
            for row in self.fixture.db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        self.assertTrue(
            {
                "workflow_runs",
                "workflow_run_token_consumptions",
                "workflow_run_transitions",
            }.issubset(tables)
        )
        # The application schema includes the shared audit event store; the
        # workflow service still does not own a separate transactional outbox.
        self.assertIn("events", tables)
        self.assertNotIn("outbox", tables)

        run = await self.fixture.create()
        with self.assertRaises(ValidationError):
            WorkflowRun(**run.model_dump(), client_workspace="spoofed")

    async def test_workspace_and_actor_partition_the_idempotency_scope(self):
        first = await self.fixture.create()
        self.assertEqual(first.workspace_id, WORKSPACE_ID)
        # A second authorized binding/preflight in another workspace may reuse
        # the same key without colliding. Its actor remains server-authenticated.
        other_workspace = "workspace-run-other"
        other_deck = "deck-run-other"
        other_binding = "dpb_" + "7" * 32
        self.fixture.db.execute(
            """
            INSERT INTO story_workspace_workspaces (id, name, owner_id)
            VALUES (?, 'Other Workspace', 1)
            """,
            (other_workspace,),
        )
        self.fixture.db.execute(
            "INSERT INTO decks (id, name, owner_id) VALUES (?, 'Other Deck', 1)",
            (other_deck,),
        )
        self.fixture.db.execute(
            """
            INSERT INTO deck_plugin_bindings (
                deck_plugin_binding_id, deck_id, workspace_id, creator_id,
                deck_plugin_id, deck_plugin_version, binding_revision,
                status, applied_to
            ) VALUES (?, ?, ?, ?, ?, ?, 1, 'active', 'next_run')
            """,
            (
                other_binding,
                other_deck,
                other_workspace,
                ACTOR_ID,
                PLUGIN_ID,
                PLUGIN_VERSION,
            ),
        )
        self.fixture.db.commit()

        original_deck = globals()["DECK_ID"]
        # Insert the second preflight explicitly so no client workspace value is
        # involved in the run request.
        preflight_id = "pf_" + "8" * 32
        expires = self.fixture.now + timedelta(minutes=5)
        payload = self.fixture._canonical_json(
            {
                "preflight_id": preflight_id,
                "binding_revision": 1,
                "input_hash": INPUT_HASH,
                "deck_runtime_snapshot_id": SNAPSHOT_ID,
                "runtime_plugin_lock_id": LOCK_ID,
                "expires_at": self.fixture._iso(expires),
            }
        )
        token = "pft_" + base64.urlsafe_b64encode(
            hmac.new(TOKEN_SECRET, payload, hashlib.sha256).digest()
        ).rstrip(b"=").decode("ascii")
        self.fixture.db.execute(
            """
            INSERT INTO workflow_preflights (
                workflow_preflight_id, request_fingerprint, deck_id,
                binding_revision, deck_plugin_id, deck_plugin_version,
                runtime_plugin_lock_id, deck_runtime_profile_id,
                deck_runtime_snapshot_id, deck_runtime_snapshot_summary_hash,
                input_hash, status, expires_at, preflight_token_hash,
                created_by, created_at, updated_at
            ) VALUES (?, ?, ?, 1, ?, ?, ?, 'drp_test', ?, ?, ?, 'passed',
                      ?, ?, ?, ?, ?)
            """,
            (
                preflight_id,
                "sha256:" + "f" * 64,
                other_deck,
                PLUGIN_ID,
                PLUGIN_VERSION,
                LOCK_ID,
                SNAPSHOT_ID,
                "sha256:" + "e" * 64,
                INPUT_HASH,
                self.fixture._iso(expires),
                "sha256:" + hashlib.sha256(token.encode()).hexdigest(),
                ACTOR_ID,
                self.fixture._iso(self.fixture.now),
                self.fixture._iso(self.fixture.now),
            ),
        )
        self.fixture.db.commit()
        second = await self.fixture.service.create_run(
            preflight_id,
            token,
            "start-1",
            "voice-thread-1",
            AuthenticatedActorContext(
                workspace_id=other_workspace,
                actor_id=ACTOR_ID,
            ),
            source_message_id="voice-message-1",
            source_message_time=self.fixture.voice_message_time,
        )
        self.assertNotEqual(second.workflow_run_id, first.workflow_run_id)
        self.assertEqual(second.workspace_id, other_workspace)
        self.assertEqual(original_deck, DECK_ID)


class WorkflowRunConcurrencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = WorkflowRunFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    @unittest.skip(
        "legacy SQLite cannot model PostgreSQL row-lock concurrency; superseded by owned-PG contract"
    )
    def test_concurrent_same_scope_token_and_key_create_exactly_one_run(self):
        preflight = self.fixture.issue_preflight()

        def create_from_connection() -> str:
            db = self.fixture.connect()
            try:
                service = self.fixture.make_service(db)
                run = asyncio.run(
                    service.create_run(
                        preflight[0],
                        preflight[1],
                        "concurrent-key",
                        "voice-thread-1",
                        self.fixture.actor,
                        source_message_id="voice-message-1",
                        source_message_time=self.fixture.voice_message_time,
                    )
                )
                return run.workflow_run_id
            finally:
                db.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            run_ids = list(executor.map(lambda _: create_from_connection(), range(2)))
        self.assertEqual(len(set(run_ids)), 1)
        self.assertEqual(
            self.fixture.db.execute("SELECT COUNT(*) FROM workflow_runs").fetchone()[0],
            1,
        )
        self.assertEqual(
            self.fixture.db.execute(
                "SELECT COUNT(*) FROM workflow_run_token_consumptions"
            ).fetchone()[0],
            1,
        )
        self.assertEqual(
            self.fixture.db.execute(
                """
                SELECT COUNT(*) FROM workflow_run_transitions
                WHERE from_status IS NULL AND to_status = 'preflight'
                """
            ).fetchone()[0],
            1,
        )


if __name__ == "__main__":
    unittest.main()
