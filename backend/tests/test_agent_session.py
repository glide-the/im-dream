"""Focused task_009 AgentSession, atomic start, and reload guard tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import sqlite3
import unittest

from pydantic import ValidationError

from backend.models.agent_session import (
    AgentSession,
    AgentSessionStatus,
    SessionStartResult,
    validate_session_transition,
)
from backend.models.deck_plugin import DeckRuntimePluginLock, RuntimePluginLockEntry
from backend.models.runtime_plugin import (
    LoadReceiptEntry,
    RuntimeLoadReceipt,
    compute_artifact_set_hash,
)
from backend.models.workflow_run import RunStatus
from backend.services.claude_agent.remote_interaction_guard import (
    ManagementSmokeContext,
    PluginRef,
    RemoteInteractionGuard,
    RUNTIME_PLUGIN_RELOAD_UNSUPPORTED,
)
from backend.services.claude_agent.session_manager import (
    AGENT_SESSION_COMMIT_FAILED,
    AGENT_SESSION_CREATE_CONFLICT,
    AGENT_SESSION_RECEIPT_INVALID,
    AGENT_SESSION_START_FAILED,
    AGENT_SESSION_TERMINATE_UNCONFIRMED,
    AgentSessionError,
    SessionManager,
)
from backend.services.workflow.run_service import WorkflowRunService
from backend.tests.test_workflow_run import (
    LOCK_ID,
    MANIFEST_HASH,
    PLUGIN_ID,
    PLUGIN_VERSION,
    TOKEN_SECRET,
    WorkflowRunFixture,
)


CAPABILITY = "story.context.read"
RUNTIME_PLUGIN_ID = "ink-dream-tools@voice-decks"
RUNTIME_PLUGIN_VERSION = "1.4.2"
ARTIFACT_DIGEST = "sha256:" + "d" * 64


class StaticReceiptReader:
    def __init__(self, receipt: RuntimeLoadReceipt) -> None:
        self.receipt = receipt

    def read_receipt(self, receipt_id: str) -> RuntimeLoadReceipt:
        if receipt_id != self.receipt.receipt_id:
            raise KeyError(receipt_id)
        return self.receipt

    def read_workflow_readiness(self, receipt_id: str) -> dict[str, object]:
        receipt = self.read_receipt(receipt_id)
        return {
            "receipt_id": receipt.receipt_id,
            "workflow_run_id": receipt.workflow_run_id,
            "runtime_plugin_lock_id": receipt.runtime_plugin_lock_id,
            "runtime_plugin_lock_digest": receipt.runtime_plugin_lock_digest,
            "required_entries_ready": receipt.required_entries_ready,
        }


class FakeRunSessionAdapter:
    def __init__(self) -> None:
        self.starts = 0
        self.terminations = 0
        self.allow_query_values: list[bool] = []
        self.fail_start = False
        self.fail_terminate = False
        self.started_event: asyncio.Event | None = None
        self.release_event: asyncio.Event | None = None

    async def start_session(
        self,
        *,
        agent_session_id: str,
        session_request_key: str,
        settings_json: str,
        runtime_node_id: str,
        allow_query: bool,
    ) -> SessionStartResult:
        self.starts += 1
        self.allow_query_values.append(allow_query)
        if self.started_event is not None:
            self.started_event.set()
        if self.release_event is not None:
            await self.release_event.wait()
        if self.fail_start:
            raise RuntimeError("fake adapter start failure")
        return SessionStartResult(
            agent_session_id=agent_session_id,
            session_request_key=session_request_key,
            active=True,
            remote_session_ref="remote:test-session",
        )

    async def terminate_session(
        self,
        *,
        agent_session_id: str,
        reason_code: str,
    ) -> None:
        self.terminations += 1
        if self.fail_terminate:
            raise RuntimeError("fake adapter terminate failure")


class AgentSessionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.fixture = WorkflowRunFixture()
        self.runtime_lock = DeckRuntimePluginLock(
            runtime_plugin_lock_id=LOCK_ID,
            deck_plugin_id=PLUGIN_ID,
            deck_plugin_version=PLUGIN_VERSION,
            deck_plugin_manifest_hash=MANIFEST_HASH,
            claude_code_plugins=[
                RuntimePluginLockEntry(
                    claude_code_plugin_id=RUNTIME_PLUGIN_ID,
                    resolved_version=RUNTIME_PLUGIN_VERSION,
                    source_ref="trusted:voice-decks",
                    artifact_digest=ARTIFACT_DIGEST,
                    required=True,
                    capability_bindings=[CAPABILITY],
                )
            ],
            created_at=self.fixture.now,
            production_ready=False,
            production_readiness_reasons=["legacy_unverified"],
        )

    def tearDown(self) -> None:
        self.fixture.close()

    async def prepare(
        self,
        key: str = "session-start",
        *,
        adapter: FakeRunSessionAdapter | None = None,
    ) -> tuple[SessionManager, FakeRunSessionAdapter, StaticReceiptReader, object]:
        run = await self.fixture.create(key)
        receipt = self._persist_receipt(run.workflow_run_id)
        reader = StaticReceiptReader(receipt)
        self.fixture.service._receipt_reader = reader.read_workflow_readiness
        selected_adapter = adapter or FakeRunSessionAdapter()
        manager = SessionManager(
            self.fixture.db,
            receipt_reader=reader,
            adapter=selected_adapter,
            workflow_run_service=self.fixture.service,
            clock=lambda: self.fixture.now,
            creating_lease_seconds=30,
        )
        return manager, selected_adapter, reader, run

    def _persist_receipt(self, workflow_run_id: str) -> RuntimeLoadReceipt:
        receipt_id = "rlr_" + workflow_run_id.removeprefix("run_")
        lock_digest = self.fixture.service._lock_digest(self.fixture.lock_json)
        artifact_set_hash = compute_artifact_set_hash(self.runtime_lock)
        entry = LoadReceiptEntry(
            claude_code_plugin_id=RUNTIME_PLUGIN_ID,
            resolved_version=RUNTIME_PLUGIN_VERSION,
            artifact_digest=ARTIFACT_DIGEST,
            materialized_digest=ARTIFACT_DIGEST,
            verification_status="legacy_unverified",
            retention_state="pinned",
            required=True,
            loaded_capabilities=[CAPABILITY],
            load_status="loaded",
            loaded_at=self.fixture.now,
        )
        receipt = RuntimeLoadReceipt(
            receipt_id=receipt_id,
            workflow_run_id=workflow_run_id,
            runtime_plugin_lock_id=LOCK_ID,
            runtime_plugin_lock_digest=lock_digest,
            runtime_environment_id="runtime-test",
            runtime_pool_id="runtime-test",
            distribution_mode="local_persistent",
            runtime_node_id="node-test",
            artifact_set_hash=artifact_set_hash,
            policy_revision="policy-test-v1",
            deployment_tier="test",
            scope="session",
            readiness_state="session_loaded",
            required_entries_ready=True,
            entries=[entry],
            created_at=self.fixture.now,
        )
        self.fixture.db.execute(
            """
            INSERT INTO runtime_load_receipts (
                receipt_id, workflow_run_id, runtime_plugin_lock_id,
                runtime_plugin_lock_digest, runtime_environment_id,
                runtime_pool_id, distribution_mode, runtime_node_id,
                artifact_set_hash, policy_revision, deployment_tier,
                scope, readiness_state, required_entries_ready, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                receipt.receipt_id,
                receipt.workflow_run_id,
                receipt.runtime_plugin_lock_id,
                receipt.runtime_plugin_lock_digest,
                receipt.runtime_environment_id,
                receipt.runtime_pool_id,
                receipt.distribution_mode,
                receipt.runtime_node_id,
                receipt.artifact_set_hash,
                receipt.policy_revision,
                receipt.deployment_tier,
                receipt.scope,
                receipt.readiness_state,
                receipt.created_at.isoformat(),
            ),
        )
        self.fixture.db.execute(
            """
            INSERT INTO runtime_load_receipt_entries (
                receipt_id, claude_code_plugin_id, resolved_version,
                artifact_digest, materialized_digest, verification_status,
                retention_state, required, loaded_capabilities_json,
                load_status, loaded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
            """,
            (
                receipt.receipt_id,
                entry.claude_code_plugin_id,
                entry.resolved_version,
                entry.artifact_digest,
                entry.materialized_digest,
                entry.verification_status,
                entry.retention_state,
                '["story.context.read"]',
                entry.load_status,
                entry.loaded_at.isoformat(),
            ),
        )
        self.fixture.db.commit()
        return receipt

    async def _start(
        self,
        manager: SessionManager,
        run: object,
        reader: StaticReceiptReader,
        *,
        marketplace_source: str = "trusted:voice-decks",
    ) -> AgentSession:
        return await manager.create_or_resume_session(
            workflow_run_id=run.workflow_run_id,
            runtime_load_receipt_id=reader.receipt.receipt_id,
            runtime_lock=self.runtime_lock,
            approved_capabilities=[CAPABILITY],
            trusted_marketplaces={"voice-decks": marketplace_source},
            actor_context=self.fixture.actor,
        )

    async def test_success_is_atomic_idempotent_and_never_allows_query(self) -> None:
        manager, adapter, reader, run = await self.prepare()
        session = await self._start(manager, run, reader)

        self.assertEqual(session.status, AgentSessionStatus.ACTIVE)
        self.assertEqual(adapter.starts, 1)
        self.assertEqual(adapter.allow_query_values, [False])
        stored_run = self.fixture.db.execute(
            "SELECT * FROM workflow_runs WHERE id = ?",
            (run.workflow_run_id,),
        ).fetchone()
        self.assertEqual(stored_run["status"], "running")
        self.assertEqual(stored_run["runtime_load_receipt_id"], reader.receipt.receipt_id)
        self.assertEqual(stored_run["agent_session_id"], session.agent_session_id)
        self.assertEqual(
            self.fixture.db.execute(
                "SELECT COUNT(*) FROM workflow_run_transitions WHERE to_status = 'running'"
            ).fetchone()[0],
            1,
        )

        replay = await self._start(manager, run, reader)
        self.assertEqual(replay.agent_session_id, session.agent_session_id)
        self.assertEqual(adapter.starts, 1)

    async def test_concurrent_same_key_has_one_owner_and_competing_settings_fail(self) -> None:
        adapter = FakeRunSessionAdapter()
        adapter.started_event = asyncio.Event()
        adapter.release_event = asyncio.Event()
        manager, _, reader, run = await self.prepare(adapter=adapter)

        owner = asyncio.create_task(self._start(manager, run, reader))
        await adapter.started_event.wait()
        replay = await self._start(manager, run, reader)
        self.assertEqual(replay.status, AgentSessionStatus.CREATING)
        self.assertEqual(adapter.starts, 1)
        with self.assertRaises(AgentSessionError) as conflict:
            await self._start(
                manager,
                run,
                reader,
                marketplace_source="trusted:other-policy",
            )
        self.assertEqual(conflict.exception.code, AGENT_SESSION_CREATE_CONFLICT)
        adapter.release_event.set()
        active = await owner
        self.assertEqual(active.status, AgentSessionStatus.ACTIVE)
        self.assertEqual(adapter.starts, 1)

    async def test_receipt_drift_fails_before_adapter_and_creates_no_session(self) -> None:
        manager, adapter, reader, run = await self.prepare()
        original = reader.receipt
        for update in (
            {"runtime_node_id": "node-drift"},
            {"runtime_pool_id": "other-pool"},
            {"deployment_tier": "production"},
        ):
            with self.subTest(update=update):
                reader.receipt = original.model_copy(update=update)
                with self.assertRaises(AgentSessionError) as captured:
                    await self._start(manager, run, reader)
                self.assertEqual(
                    captured.exception.code,
                    AGENT_SESSION_RECEIPT_INVALID,
                )
        self.assertEqual(adapter.starts, 0)
        self.assertEqual(
            self.fixture.db.execute("SELECT COUNT(*) FROM agent_sessions").fetchone()[0],
            0,
        )

    async def test_adapter_failure_maps_session_and_run_without_bindings(self) -> None:
        adapter = FakeRunSessionAdapter()
        adapter.fail_start = True
        manager, _, reader, run = await self.prepare(adapter=adapter)
        with self.assertRaises(AgentSessionError) as captured:
            await self._start(manager, run, reader)
        self.assertEqual(captured.exception.code, AGENT_SESSION_START_FAILED)
        session = self.fixture.db.execute("SELECT * FROM agent_sessions").fetchone()
        self.assertEqual(session["status"], "failed")
        stored_run = self.fixture.db.execute(
            "SELECT * FROM workflow_runs WHERE id = ?",
            (run.workflow_run_id,),
        ).fetchone()
        self.assertEqual(stored_run["status"], "failed")
        self.assertIsNone(stored_run["runtime_load_receipt_id"])
        self.assertIsNone(stored_run["agent_session_id"])

    async def test_database_failure_rolls_back_and_terminates_remote(self) -> None:
        for checkpoint in (
            "session_updated",
            "status_updated",
            "status_transition_written",
        ):
            with self.subTest(checkpoint=checkpoint):
                manager, adapter, reader, run = await self.prepare(
                    key=f"failure-{checkpoint}"
                )
                self.fixture.fail_at = checkpoint
                with self.assertRaises(AgentSessionError) as captured:
                    await self._start(manager, run, reader)
                self.assertEqual(captured.exception.code, AGENT_SESSION_COMMIT_FAILED)
                self.assertEqual(adapter.terminations, 1)
                session = self.fixture.db.execute(
                    "SELECT * FROM agent_sessions WHERE workflow_run_id = ?",
                    (run.workflow_run_id,),
                ).fetchone()
                self.assertEqual(session["status"], "failed")
                stored_run = self.fixture.db.execute(
                    """
                    SELECT status, runtime_load_receipt_id, agent_session_id
                    FROM workflow_runs WHERE id = ?
                    """,
                    (run.workflow_run_id,),
                ).fetchone()
                self.assertEqual(tuple(stored_run), ("queued", None, None))
                self.assertEqual(
                    self.fixture.db.execute(
                        """
                        SELECT COUNT(*) FROM workflow_run_transitions
                        WHERE workflow_run_id = ? AND to_status = 'running'
                        """,
                        (run.workflow_run_id,),
                    ).fetchone()[0],
                    0,
                )
                self.fixture.fail_at = None

    async def test_unconfirmed_compensation_blocks_a_second_live_attempt(self) -> None:
        adapter = FakeRunSessionAdapter()
        adapter.fail_terminate = True
        manager, _, reader, run = await self.prepare(adapter=adapter)
        self.fixture.fail_at = "status_updated"
        with self.assertRaises(AgentSessionError) as captured:
            await self._start(manager, run, reader)
        self.assertEqual(captured.exception.code, AGENT_SESSION_TERMINATE_UNCONFIRMED)
        session = self.fixture.db.execute("SELECT * FROM agent_sessions").fetchone()
        self.assertEqual(session["status"], "creating")
        self.assertEqual(session["owner_token"], "compensation_pending")
        with self.assertRaises(AgentSessionError) as conflict:
            await self._start(
                manager,
                run,
                reader,
                marketplace_source="trusted:other-policy",
            )
        self.assertEqual(conflict.exception.code, AGENT_SESSION_CREATE_CONFLICT)

    async def test_terminal_session_and_database_bindings_are_immutable(self) -> None:
        manager, _, reader, run = await self.prepare()
        session = await self._start(manager, run, reader)
        terminated = await manager.terminate_session(
            session.agent_session_id,
            reason_code="USER_CANCELLED",
            actor_context=self.fixture.actor,
        )
        self.assertEqual(terminated.status, AgentSessionStatus.TERMINATED)
        stored_run = self.fixture.db.execute(
            "SELECT status FROM workflow_runs WHERE id = ?",
            (run.workflow_run_id,),
        ).fetchone()
        self.assertEqual(stored_run["status"], "cancelled")
        with self.assertRaises(sqlite3.IntegrityError):
            self.fixture.db.execute(
                "UPDATE agent_sessions SET settings_hash = ? WHERE agent_session_id = ?",
                ("sha256:" + "9" * 64, session.agent_session_id),
            )
        self.fixture.db.rollback()
        with self.assertRaises(sqlite3.IntegrityError):
            self.fixture.db.execute(
                "UPDATE agent_sessions SET status = 'active' WHERE agent_session_id = ?",
                (session.agent_session_id,),
            )
        self.fixture.db.rollback()

    async def test_models_reject_secret_settings_and_terminal_resurrection(self) -> None:
        manager, _, reader, run = await self.prepare()
        session = await self._start(manager, run, reader)
        payload = session.model_dump()
        payload["settings_json"] = (
            '{"enabledPlugins":{"ink-dream-tools@voice-decks":true},'
            '"extraKnownMarketplaces":{"voice-decks":{"source":"trusted"}},'
            '"pluginPolicy":{"allowedCapabilities":["story.context.read"]},'
            '"secret":"forbidden"}'
        )
        with self.assertRaises(ValidationError):
            AgentSession.model_validate(payload)
        run_row = self.fixture.db.execute(
            "SELECT * FROM workflow_runs WHERE id = ?",
            (run.workflow_run_id,),
        ).fetchone()
        run_model = self.fixture.service._row_to_run(run_row)
        run_payload = run_model.model_dump()
        run_payload["source_voice_thread_id"] = session.agent_session_id
        with self.assertRaises(ValidationError):
            type(run_model).model_validate(run_payload)
        with self.assertRaises(ValueError):
            validate_session_transition(
                AgentSessionStatus.TERMINATED,
                AgentSessionStatus.ACTIVE,
            )

    async def test_reload_guard_rejects_run_sessions_and_limits_management_smoke(self) -> None:
        manager, _, reader, run = await self.prepare()
        session = await self._start(manager, run, reader)
        plugin = PluginRef(
            claude_code_plugin_id=RUNTIME_PLUGIN_ID,
            resolved_version=RUNTIME_PLUGIN_VERSION,
            artifact_digest=ARTIFACT_DIGEST,
            capabilities=[CAPABILITY],
            materialized=True,
            marketplace_cached=True,
        )
        guard = RemoteInteractionGuard(self.fixture.db)
        denied = await guard.guard_reload(
            workflow_run_id=run.workflow_run_id,
            agent_session_id=session.agent_session_id,
            proposed_plugins=[plugin],
            proposed_capabilities=[CAPABILITY],
        )
        self.assertFalse(denied.allowed)
        self.assertEqual(denied.reason_code, RUNTIME_PLUGIN_RELOAD_UNSUPPORTED)

        management = ManagementSmokeContext(
            management_session_id="mgmt_idle-test",
            deployment_tier="test",
            plugins=[plugin],
        )
        smoke_guard = RemoteInteractionGuard(
            self.fixture.db,
            management_context_reader=lambda session_id: management
            if session_id == management.management_session_id
            else None,
        )
        allowed = await smoke_guard.guard_reload(
            workflow_run_id=None,
            agent_session_id=management.management_session_id,
            proposed_plugins=[plugin],
            proposed_capabilities=[CAPABILITY],
        )
        self.assertTrue(allowed.allowed)
        self.assertTrue(allowed.diagnostic_only)
        self.assertFalse(allowed.writes_readiness)
        self.assertFalse(allowed.creates_receipt)
        self.assertFalse(allowed.production_authorized)

        production = management.model_copy(update={"deployment_tier": "production"})
        production_guard = RemoteInteractionGuard(
            self.fixture.db,
            management_context_reader=lambda _session_id: production,
        )
        denied_production = await production_guard.guard_reload(
            workflow_run_id=None,
            agent_session_id=production.management_session_id,
            proposed_plugins=[plugin],
            proposed_capabilities=[CAPABILITY],
        )
        self.assertFalse(denied_production.allowed)


if __name__ == "__main__":
    unittest.main()
