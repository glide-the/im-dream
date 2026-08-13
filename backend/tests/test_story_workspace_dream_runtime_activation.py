"""Dream SDK-init to Workflow Run activation contract tests."""

from __future__ import annotations

import unittest

from backend.models.runtime_plugin import compute_artifact_set_hash
from backend.models.workflow_run import RunStatus
from backend.services.story_workspace.dream_runtime_activation_service import (
    DREAM_RUNTIME_INIT_INVALID,
    StoryWorkspaceDreamRuntimeActivationError,
    StoryWorkspaceDreamRuntimeActivationService,
)
from backend.services.story_workspace.dream_workflow_lifecycle_service import (
    StoryWorkspaceDreamWorkflowLifecycleService,
)
from backend.tests.test_workflow_run import WorkflowRunFixture


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


class StoryWorkspaceDreamRuntimeActivationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.fixture = WorkflowRunFixture()
        self.runtime_lock = self._runtime_lock()
        self.artifact_set_hash = compute_artifact_set_hash(self.runtime_lock)
        self._seed_materialization()

    def tearDown(self) -> None:
        self.fixture.close()

    def _runtime_lock(self):
        from backend.models.deck_plugin import (
            DeckRuntimePluginLock,
            RuntimePluginLockEntry,
        )

        raw = self.fixture.db.execute(
            "SELECT lock_json FROM deck_runtime_plugin_locks WHERE id = ?",
            ("rpl_" + "1" * 32,),
        ).fetchone()["lock_json"]
        payload = __import__("json").loads(raw)
        runtime_lock = DeckRuntimePluginLock(
            **payload,
            created_at=self.fixture.now,
            production_ready=False,
            production_readiness_reasons=["legacy_unverified"],
        )
        self.fixture.lock_json = runtime_lock.model_dump_json()
        self.fixture.db.execute(
            "UPDATE deck_runtime_plugin_locks SET lock_json = ? WHERE id = ?",
            (self.fixture.lock_json, runtime_lock.runtime_plugin_lock_id),
        )
        self.fixture.db.commit()
        return runtime_lock

    def _seed_materialization(self) -> None:
        entry = self.runtime_lock.claude_code_plugins[0]
        self.fixture.db.execute(
            """
            INSERT INTO runtime_plugin_materializations (
                runtime_materialization_id, runtime_environment_id,
                runtime_pool_id, runtime_node_id, claude_code_plugin_id,
                resolved_version, artifact_digest, materialized_digest,
                artifact_set_hash, policy_revision, declaration_status,
                materialization_status, activation_status,
                materialization_key, attempt_id, attempt_count,
                verification_status, retention_state, cache_ref,
                created_at, updated_at
            ) VALUES (?, 'ink-local', 'ink-local', 'local', ?, ?, ?, ?, ?,
                      'dream-launch/v1', 'declared', 'materialized', 'loadable',
                      ?, ?, 1, 'verified', 'shared_artifact', 'cache:test', ?, ?)
            """,
            (
                "rm_" + "7" * 32,
                entry.claude_code_plugin_id,
                entry.resolved_version,
                entry.artifact_digest,
                entry.artifact_digest,
                self.artifact_set_hash,
                "sha256:" + "8" * 64,
                "rpa_" + "9" * 32,
                self.fixture.now.isoformat(),
                self.fixture.now.isoformat(),
            ),
        )
        self.fixture.db.commit()

    def _service(self) -> StoryWorkspaceDreamRuntimeActivationService:
        return StoryWorkspaceDreamRuntimeActivationService(
            self.fixture.db,
            token_secret=self.fixture.service._token_secret,
            clock=lambda: self.fixture.now,
        )

    def _verified_plugins(self) -> list[dict[str, object]]:
        entry = self.runtime_lock.claude_code_plugins[0]
        return [
            {
                "package_spec": entry.claude_code_plugin_id,
                "resolved_version": entry.resolved_version,
                "artifact_digest": entry.artifact_digest,
                "relative_path": ".ink/plugins/verified",
                "absolute_path": "/redacted/verified",
                "has_manifest": True,
            }
        ]

    async def test_verified_assembled_context_activates_same_run_before_session_execution(self) -> None:
        run = await self.fixture.create("dream-runtime-init")

        activated = await self._service().activate_from_assembled_context(
            workflow_run_id=run.workflow_run_id,
            actor_context=self.fixture.actor,
            remote_session_ref="thread-dream-runtime-1",
            verified_plugins=self._verified_plugins(),
        )

        self.assertEqual(activated.status, RunStatus.RUNNING)
        self.assertIsNotNone(activated.runtime_load_receipt_id)
        self.assertIsNotNone(activated.agent_session_id)
        receipt = self.fixture.db.execute(
            "SELECT * FROM runtime_load_receipts WHERE receipt_id = ?",
            (activated.runtime_load_receipt_id,),
        ).fetchone()
        session = self.fixture.db.execute(
            "SELECT * FROM agent_sessions WHERE agent_session_id = ?",
            (activated.agent_session_id,),
        ).fetchone()
        self.assertEqual(receipt["workflow_run_id"], run.workflow_run_id)
        self.assertEqual(receipt["required_entries_ready"], 1)
        self.assertEqual(receipt["runtime_environment_id"], "ink-local")
        self.assertEqual(receipt["deployment_tier"], "local")
        self.assertEqual(session["status"], "active")
        self.assertEqual(session["deployment_tier"], "local")
        self.assertEqual(session["remote_session_ref"], "thread-dream-runtime-1")
        self.assertEqual(
            self.fixture.db.execute(
                "SELECT activation_status FROM runtime_plugin_materializations"
            ).fetchone()["activation_status"],
            "loaded",
        )

        replay = await self._service().activate_from_assembled_context(
            workflow_run_id=run.workflow_run_id,
            actor_context=self.fixture.actor,
            remote_session_ref="thread-dream-runtime-1",
            verified_plugins=self._verified_plugins(),
        )
        self.assertEqual(replay.agent_session_id, activated.agent_session_id)
        self.assertEqual(
            self.fixture.db.execute(
                "SELECT COUNT(*) AS count FROM runtime_load_receipts"
            ).fetchone()["count"],
            1,
        )

    async def test_verified_deck_plugin_can_coexist_with_exact_runtime_adapter(self) -> None:
        """Deck plugins share the frozen manifest but are not runtime-lock entries."""

        run = await self.fixture.create("dream-runtime-deck-plugin-coexistence")
        verified_plugins = [
            {
                "package_spec": "drama-forge@drama-studio",
                "resolved_version": "1.0.1",
                "artifact_digest": "sha256:" + "d" * 64,
                "relative_path": ".ink/plugins/drama-forge",
                "absolute_path": "/redacted/drama-forge",
                "has_manifest": True,
            },
            *self._verified_plugins(),
        ]

        activated = await self._service().activate_from_assembled_context(
            workflow_run_id=run.workflow_run_id,
            actor_context=self.fixture.actor,
            remote_session_ref="thread-with-deck-plugin",
            verified_plugins=verified_plugins,
        )

        self.assertEqual(activated.status, RunStatus.RUNNING)
        self.assertIsNotNone(activated.runtime_load_receipt_id)

    async def test_wrong_runtime_adapter_still_fails_with_verified_deck_plugin(self) -> None:
        run = await self.fixture.create("dream-runtime-adapter-mismatch")
        verified_plugins = self._verified_plugins()
        verified_plugins[0]["artifact_digest"] = "sha256:" + "0" * 64
        verified_plugins.append(
            {
                "package_spec": "drama-forge@drama-studio",
                "resolved_version": "1.0.1",
                "artifact_digest": "sha256:" + "d" * 64,
                "has_manifest": True,
            }
        )

        with self.assertRaises(StoryWorkspaceDreamRuntimeActivationError) as captured:
            await self._service().activate_from_assembled_context(
                workflow_run_id=run.workflow_run_id,
                actor_context=self.fixture.actor,
                remote_session_ref="thread-wrong-adapter",
                verified_plugins=verified_plugins,
            )

        self.assertEqual(captured.exception.code, DREAM_RUNTIME_INIT_INVALID)

    async def test_admin_materialization_with_same_hash_does_not_poison_dream_activation(self) -> None:
        entry = self.runtime_lock.claude_code_plugins[0]
        self.fixture.db.execute(
            """
            INSERT INTO runtime_plugin_materializations (
                runtime_materialization_id, runtime_environment_id,
                runtime_pool_id, runtime_node_id, claude_code_plugin_id,
                resolved_version, artifact_digest, materialized_digest,
                artifact_set_hash, policy_revision, declaration_status,
                materialization_status, activation_status,
                materialization_key, attempt_id, attempt_count,
                verification_status, retention_state, cache_ref,
                created_at, updated_at
            ) VALUES (?, 'runtime-test', 'runtime-test', 'local', ?, ?, ?, ?, ?,
                      'deck-admin/v1', 'declared', 'materialized', 'loadable',
                      ?, ?, 1, 'verified', 'local_cache', 'cache:admin', ?, ?)
            """,
            (
                "rm_" + "a" * 32,
                entry.claude_code_plugin_id,
                entry.resolved_version,
                entry.artifact_digest,
                entry.artifact_digest,
                self.artifact_set_hash,
                "sha256:" + "b" * 64,
                "rpa_" + "c" * 32,
                self.fixture.now.isoformat(),
                self.fixture.now.isoformat(),
            ),
        )
        self.fixture.db.commit()
        run = await self.fixture.create("dream-runtime-policy-isolation")

        activated = await self._service().activate_from_assembled_context(
            workflow_run_id=run.workflow_run_id,
            actor_context=self.fixture.actor,
            remote_session_ref="thread-policy-isolation",
            verified_plugins=self._verified_plugins(),
        )

        self.assertEqual(activated.status, RunStatus.RUNNING)
        receipt = self.fixture.db.execute(
            "SELECT policy_revision FROM runtime_load_receipts "
            "WHERE receipt_id = ?",
            (activated.runtime_load_receipt_id,),
        ).fetchone()
        self.assertEqual(receipt["policy_revision"], "dream-launch/v1")

    async def test_active_runtime_accepts_fresh_chat_sessions_without_rebinding(self) -> None:
        run = await self.fixture.create("dream-runtime-resume-states")
        service = self._service()
        activation_init = {
            "session_id": "claude-session-runtime-activation",
            "tools": ["mcp__story_workspace__write_dream_run"],
        }
        running = await service.activate_from_assembled_context(
            workflow_run_id=run.workflow_run_id,
            actor_context=self.fixture.actor,
            remote_session_ref=activation_init["session_id"],
            verified_plugins=self._verified_plugins(),
        )
        replayed_running = await service.activate_from_assembled_context(
            workflow_run_id=run.workflow_run_id,
            actor_context=self.fixture.actor,
            remote_session_ref="thread-runtime-fresh-running",
            verified_plugins=self._verified_plugins(),
        )
        self.assertEqual(replayed_running.status, RunStatus.RUNNING)

        output_validating = await self.fixture.service.transition_run(
            running.workflow_run_id,
            RunStatus.OUTPUT_VALIDATING,
            self.fixture.actor,
            reason_code="test_output_validation_started",
        )
        replayed_validating = await service.activate_from_assembled_context(
            workflow_run_id=run.workflow_run_id,
            actor_context=self.fixture.actor,
            remote_session_ref="thread-runtime-fresh-validating",
            verified_plugins=self._verified_plugins(),
        )
        self.assertEqual(replayed_validating.status, RunStatus.OUTPUT_VALIDATING)
        lifecycle = StoryWorkspaceDreamWorkflowLifecycleService(
            self.fixture.db,
            token_secret=self.fixture.service._token_secret,
            clock=lambda: self.fixture.now,
        )

        pending = await lifecycle.record_output_ready(
            output_validating.workflow_run_id,
            self.fixture.actor,
            normalized_result_ready=True,
        )
        replayed_pending = await service.activate_from_assembled_context(
            workflow_run_id=run.workflow_run_id,
            actor_context=self.fixture.actor,
            remote_session_ref="thread-runtime-fresh-pending",
            verified_plugins=self._verified_plugins(),
        )
        self.assertEqual(replayed_pending.status, RunStatus.PENDING_REVIEW)

        confirmed = await lifecycle.record_confirmation_accepted(
            pending.workflow_run_id,
            self.fixture.actor,
            review_items_approved=True,
        )
        replayed_confirmed = await service.activate_from_assembled_context(
            workflow_run_id=run.workflow_run_id,
            actor_context=self.fixture.actor,
            remote_session_ref="thread-runtime-fresh-confirmed",
            verified_plugins=self._verified_plugins(),
        )
        self.assertEqual(replayed_confirmed.status, RunStatus.CONFIRMED)

        confirmed = await lifecycle.record_post_confirmation_dispatched(
            confirmed.workflow_run_id,
            self.fixture.actor,
        )
        replayed_confirmed = await service.activate_from_assembled_context(
            workflow_run_id=run.workflow_run_id,
            actor_context=self.fixture.actor,
            remote_session_ref="thread-runtime-fresh-confirmed",
            verified_plugins=self._verified_plugins(),
        )
        self.assertEqual(replayed_confirmed.status, RunStatus.CONFIRMED)
        session = self.fixture.db.execute(
            "SELECT remote_session_ref FROM agent_sessions "
            "WHERE agent_session_id = ?",
            (running.agent_session_id,),
        ).fetchone()
        self.assertEqual(
            session["remote_session_ref"],
            "claude-session-runtime-activation",
        )
        self.assertEqual(
            self.fixture.db.execute(
                "SELECT COUNT(*) AS count FROM agent_sessions "
                "WHERE workflow_run_id = ?",
                (run.workflow_run_id,),
            ).fetchone()["count"],
            1,
        )
        self.assertEqual(
            self.fixture.db.execute(
                "SELECT COUNT(*) AS count FROM runtime_load_receipts "
                "WHERE workflow_run_id = ?",
                (run.workflow_run_id,),
            ).fetchone()["count"],
            1,
        )

    async def test_active_runtime_revalidates_tool_manifest_and_session_binding(self) -> None:
        run = await self.fixture.create("dream-runtime-active-revalidation")
        service = self._service()
        init = {
            "session_id": "claude-session-runtime-original",
            "tools": ["mcp__story_workspace__write_dream_run"],
        }
        activated = await service.activate_from_assembled_context(
            workflow_run_id=run.workflow_run_id,
            actor_context=self.fixture.actor,
            remote_session_ref=init["session_id"],
            verified_plugins=self._verified_plugins(),
        )

        tampered = self._verified_plugins()
        tampered[0]["artifact_digest"] = "sha256:" + "0" * 64
        invalid_cases = [
            ({**init, "session_id": "fresh-tampered-plugin"}, tampered)
        ]
        for sdk_init, plugins in invalid_cases:
            with self.subTest(session=sdk_init["session_id"]), self.assertRaises(
                StoryWorkspaceDreamRuntimeActivationError
            ) as captured:
                await service.activate_from_assembled_context(
                    workflow_run_id=run.workflow_run_id,
                    actor_context=self.fixture.actor,
                    remote_session_ref=sdk_init["session_id"],
                    verified_plugins=plugins,
                )
            self.assertEqual(captured.exception.code, DREAM_RUNTIME_INIT_INVALID)

        self.fixture.db.execute(
            "UPDATE agent_sessions SET status = 'terminated', "
            "terminated_at = ?, termination_reason_code = 'test_terminated' "
            "WHERE agent_session_id = ?",
            (self.fixture.now.isoformat(), activated.agent_session_id),
        )
        self.fixture.db.commit()
        with self.assertRaises(StoryWorkspaceDreamRuntimeActivationError) as captured:
            await service.activate_from_assembled_context(
                workflow_run_id=run.workflow_run_id,
                actor_context=self.fixture.actor,
                remote_session_ref="fresh-inactive-binding",
                verified_plugins=self._verified_plugins(),
            )
        self.assertEqual(captured.exception.code, DREAM_RUNTIME_INIT_INVALID)

    async def test_invalid_thread_or_missing_plugin_fails_closed_without_receipt(self) -> None:
        run = await self.fixture.create("dream-runtime-init-invalid")

        for init, plugins in (
            ({"session_id": "", "tools": []}, self._verified_plugins()),
            (
                {
                    "session_id": "claude-session-runtime-2",
                    "tools": ["mcp__story_workspace__write_dream_run"],
                },
                [],
            ),
        ):
            with self.subTest(init=init, plugins=plugins):
                with self.assertRaises(StoryWorkspaceDreamRuntimeActivationError) as captured:
                    await self._service().activate_from_assembled_context(
                        workflow_run_id=run.workflow_run_id,
                        actor_context=self.fixture.actor,
                        remote_session_ref=init["session_id"],
                        verified_plugins=plugins,
                    )
                self.assertEqual(captured.exception.code, DREAM_RUNTIME_INIT_INVALID)

        persisted = self.fixture.service.read_run(run.workflow_run_id, self.fixture.actor)
        self.assertEqual(persisted.status, RunStatus.QUEUED)
        self.assertEqual(
            self.fixture.db.execute(
                "SELECT COUNT(*) AS count FROM runtime_load_receipts"
            ).fetchone()["count"],
            0,
        )

    async def test_initial_output_and_confirmation_advance_only_launch_lifecycle(self) -> None:
        run = await self.fixture.create("dream-runtime-lifecycle")
        running = await self._service().activate_from_assembled_context(
            workflow_run_id=run.workflow_run_id,
            actor_context=self.fixture.actor,
            remote_session_ref="thread-lifecycle",
            verified_plugins=self._verified_plugins(),
        )
        lifecycle = StoryWorkspaceDreamWorkflowLifecycleService(
            PsycopgReadTransactionConnection(self.fixture.db),
            token_secret=self.fixture.service._token_secret,
            clock=lambda: self.fixture.now,
        )

        pending = await lifecycle.record_output_ready(
            running.workflow_run_id,
            self.fixture.actor,
            normalized_result_ready=True,
        )
        self.assertEqual(pending.status, RunStatus.PENDING_REVIEW)

        confirmed = await lifecycle.record_confirmation_accepted(
            running.workflow_run_id,
            self.fixture.actor,
            review_items_approved=True,
        )
        self.assertEqual(confirmed.status, RunStatus.CONFIRMED)

        confirmed = await lifecycle.record_post_confirmation_dispatched(
            running.workflow_run_id,
            self.fixture.actor,
        )
        self.assertEqual(confirmed.status, RunStatus.CONFIRMED)

        transitions = self.fixture.db.execute(
            "SELECT to_status FROM workflow_run_transitions "
            "WHERE workflow_run_id = ? ORDER BY transition_seq",
            (running.workflow_run_id,),
        ).fetchall()
        self.assertEqual(
            [row["to_status"] for row in transitions],
            [
                "preflight",
                "queued",
                "running",
                "output_validating",
                "pending_review",
                "confirmed",
            ],
        )

    async def test_lifecycle_rejects_unproven_initial_output(self) -> None:
        run = await self.fixture.create("dream-runtime-lifecycle-guard")
        lifecycle = StoryWorkspaceDreamWorkflowLifecycleService(
            self.fixture.db,
            token_secret=self.fixture.service._token_secret,
            clock=lambda: self.fixture.now,
        )

        with self.assertRaises(ValueError):
            await lifecycle.record_output_ready(
                run.workflow_run_id,
                self.fixture.actor,
                normalized_result_ready=False,
            )
if __name__ == "__main__":
    unittest.main()
