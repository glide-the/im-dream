"""Contracts for server-only Dream episode/workflow command dispatch."""

from __future__ import annotations

import asyncio
import json
import sqlite3
import unittest
from unittest.mock import patch

from agent_stream_events import NormalizedAgentEvent
from services.story_workspace.dream_internal_command_service import (
    StoryWorkspaceDreamInternalCommandCoordinator,
    StoryWorkspaceDreamInternalCommandError,
    StoryWorkspaceDreamInternalCommandService,
    StoryWorkspaceDreamInternalPendingDispatch,
    story_workspace_guard_persisted_dream_internal_command_turn,
)
from story_workspace.contracts import (
    StoryWorkspaceDreamInternalCommand,
    StoryWorkspaceDreamRunContext,
)


RUN_ID = "run_0123456789abcdef0123456789abcdef"
THREAD_ID = "dream-thread"
ACTOR_ID = "7"


def _provenance(
    *,
    run_id: str = RUN_ID,
    thread_id: str = THREAD_ID,
    actor_id: str = ACTOR_ID,
) -> dict:
    return {
        "schema": "story-workspace-episode-action/v1",
        "workflow_run_id": run_id,
        "thread_id": thread_id,
        "actor_id": actor_id,
        "action": "write_script",
        "episode_uid": "a" * 32,
        "input_revision": None,
        "expected_facts_revision": None,
        "expected_manifest_revision": None,
        "expected_workflow_revision": None,
    }


def _context(
    *,
    run_id: str = RUN_ID,
    thread_id: str = THREAD_ID,
) -> StoryWorkspaceDreamRunContext:
    return StoryWorkspaceDreamRunContext(
        workflow_run_id=run_id,
        thread_id=thread_id,
        deck_id="deck-1",
        deck_plugin_id="drama-forge",
        deck_plugin_version="1.0.0",
        deck_plugin_binding_id="binding-1",
        binding_revision=1,
        deck_runtime_snapshot_id="snapshot-1",
        runtime_plugin_lock_id="lock-1",
    )


class _Factory:
    def __init__(
        self,
        *,
        running: bool = False,
        events: list[NormalizedAgentEvent] | None = None,
        block: bool = False,
    ) -> None:
        self.running = running
        self.events = events or [
            NormalizedAgentEvent.create("message-final", {"text": "done"}),
            NormalizedAgentEvent.create("finish", {"finishReason": "stop"}),
        ]
        self.block = block
        self.requests: list[object] = []
        self.started = asyncio.Event()
        self.cancelled = asyncio.Event()

    def session_snapshot(self, _thread_id: str):
        return {"lifecycle": "running"} if self.running else None

    async def run_events(self, request):
        self.requests.append(request)
        self.started.set()
        if self.block:
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.cancelled.set()
                raise
        for event in self.events:
            yield event


class DreamInternalCommandServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            CREATE TABLE chat_thread (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                updated_at TEXT
            );
            CREATE TABLE chat_message (
                id TEXT PRIMARY KEY,
                thread_id TEXT,
                role TEXT,
                parts TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE story_workspace_workspaces (
                id TEXT PRIMARY KEY,
                owner_id INTEGER
            );
            CREATE TABLE workflow_runs (
                id TEXT PRIMARY KEY,
                workspace_id TEXT,
                source_voice_thread_id TEXT,
                created_by TEXT
            );
            INSERT INTO chat_thread (id, user_id) VALUES ('dream-thread', 7);
            INSERT INTO story_workspace_workspaces (id, owner_id)
            VALUES ('workspace-1', 7);
            INSERT INTO workflow_runs
                (id, workspace_id, source_voice_thread_id, created_by)
            VALUES
                ('run_0123456789abcdef0123456789abcdef',
                 'workspace-1', 'dream-thread', '7');
            """
        )

    def tearDown(self) -> None:
        self.db.close()

    def _metadata(self) -> dict:
        row = self.db.execute("SELECT metadata FROM chat_message").fetchone()
        self.assertIsNotNone(row)
        return json.loads(row["metadata"])

    def _claim(
        self,
        *,
        service: StoryWorkspaceDreamInternalCommandService | None = None,
        key: str = "key-1",
        text: str = "继续",
        context: StoryWorkspaceDreamRunContext | None = None,
    ):
        selected = service or StoryWorkspaceDreamInternalCommandService(self.db)
        with patch(
            "services.story_workspace.dream_internal_command_service."
            "story_workspace_read_dream_confirmation_fact",
            return_value=(True, True),
        ):
            return selected.claim_message(
                run_id=RUN_ID,
                thread_id=THREAD_ID,
                actor_id=ACTOR_ID,
                context=context or _context(),
                command=StoryWorkspaceDreamInternalCommand(
                    text=text,
                    idempotencyKey=key,
                ),
                provenance=_provenance(),
            )

    def test_claim_is_run_thread_bound_and_requires_business_confirmation(self) -> None:
        command = StoryWorkspaceDreamInternalCommand(
            text="继续",
            idempotencyKey="key-permission",
        )
        service = StoryWorkspaceDreamInternalCommandService(self.db)
        with self.assertRaisesRegex(
            StoryWorkspaceDreamInternalCommandError,
            "WORKFLOW_PERMISSION_DENIED",
        ):
            service.claim_message(
                run_id=RUN_ID,
                thread_id=THREAD_ID,
                actor_id=ACTOR_ID,
                context=_context(thread_id="other-thread"),
                command=command,
                provenance=_provenance(),
            )
        with patch(
            "services.story_workspace.dream_internal_command_service."
            "story_workspace_read_dream_confirmation_fact",
            return_value=(False, False),
        ):
            with self.assertRaisesRegex(
                StoryWorkspaceDreamInternalCommandError,
                "DREAM_AGENT_MESSAGE_NOT_READY",
            ):
                service.claim_message(
                    run_id=RUN_ID,
                    thread_id=THREAD_ID,
                    actor_id=ACTOR_ID,
                    context=_context(),
                    command=command,
                    provenance=_provenance(),
                )

    def test_same_key_replays_text_conflict_and_second_live_key_is_busy(self) -> None:
        accepted, pending = self._claim()
        replay, replay_pending = self._claim()
        self.assertIsNotNone(pending)
        self.assertIsNone(replay_pending)
        self.assertEqual(accepted.message_id, replay.message_id)
        with self.assertRaisesRegex(
            StoryWorkspaceDreamInternalCommandError,
            "IDEMPOTENCY_CONFLICT",
        ):
            self._claim(text="改变后的命令")
        with self.assertRaisesRegex(
            StoryWorkspaceDreamInternalCommandError,
            "DREAM_AGENT_MESSAGE_BUSY",
        ):
            self._claim(key="key-2")
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM chat_message").fetchone()[0],
            1,
        )

    def test_live_thread_rejects_a_second_internal_command(self) -> None:
        service = StoryWorkspaceDreamInternalCommandService(
            self.db,
            thread_factory=_Factory(running=True),
        )
        with self.assertRaisesRegex(
            StoryWorkspaceDreamInternalCommandError,
            "DREAM_AGENT_MESSAGE_NOT_READY",
        ):
            self._claim(service=service)

    def test_persisted_turn_guard_allows_heartbeat_drift_but_rejects_stale_or_tampered_claims(
        self,
    ) -> None:
        _accepted, pending = self._claim(key="key-guard")
        self.assertIsNotNone(pending)
        authoritative = self._metadata()
        authoritative["dispatch_claim_lease_until"] = 200.0
        self.db.execute(
            "UPDATE chat_message SET metadata = ?",
            (json.dumps(authoritative),),
        )
        self.db.commit()
        request_metadata = dict(pending.metadata)
        request_metadata["dispatch_claim_lease_until"] = 130.0

        with patch(
            "services.story_workspace.dream_internal_command_service.time.time",
            return_value=150.0,
        ):
            self.assertTrue(
                story_workspace_guard_persisted_dream_internal_command_turn(
                    self.db,
                    thread_id=THREAD_ID,
                    actor_id=ACTOR_ID,
                    message_id=pending.message_id,
                    parts=pending.parts,
                    metadata=request_metadata,
                )
            )

            tampered_claim = dict(request_metadata)
            tampered_claim["dispatch_claim_id"] = "claim-forged"
            tampered_provenance = dict(request_metadata)
            tampered_provenance["story_workspace_episode_action"] = {
                **_provenance(),
                "actor_id": "8",
            }
            future_lease = dict(request_metadata)
            future_lease["dispatch_claim_lease_until"] = 201.0
            scenarios = (
                (pending.parts + [{"type": "text", "text": "extra"}], request_metadata),
                (pending.parts, tampered_claim),
                (pending.parts, tampered_provenance),
                (pending.parts, future_lease),
            )
            for parts, metadata in scenarios:
                with self.subTest(metadata=metadata), self.assertRaises(
                    StoryWorkspaceDreamInternalCommandError
                ):
                    story_workspace_guard_persisted_dream_internal_command_turn(
                        self.db,
                        thread_id=THREAD_ID,
                        actor_id=ACTOR_ID,
                        message_id=pending.message_id,
                        parts=parts,
                        metadata=metadata,
                    )

        with patch(
            "services.story_workspace.dream_internal_command_service.time.time",
            return_value=201.0,
        ), self.assertRaises(StoryWorkspaceDreamInternalCommandError):
            story_workspace_guard_persisted_dream_internal_command_turn(
                self.db,
                thread_id=THREAD_ID,
                actor_id=ACTOR_ID,
                message_id=pending.message_id,
                parts=pending.parts,
                metadata=request_metadata,
            )

    def test_persisted_turn_guard_rejects_missing_row_and_run_ownership_drift(
        self,
    ) -> None:
        with self.assertRaises(StoryWorkspaceDreamInternalCommandError):
            story_workspace_guard_persisted_dream_internal_command_turn(
                self.db,
                thread_id=THREAD_ID,
                actor_id=ACTOR_ID,
                message_id="dream_agent_" + "f" * 64,
                parts=[{"type": "text", "text": "forged"}],
                metadata={},
            )

        _accepted, pending = self._claim(key="key-owned")
        self.db.execute(
            "UPDATE workflow_runs SET source_voice_thread_id = 'other-thread'"
        )
        self.db.commit()
        with self.assertRaisesRegex(
            StoryWorkspaceDreamInternalCommandError,
            "WORKFLOW_PERMISSION_DENIED",
        ):
            story_workspace_guard_persisted_dream_internal_command_turn(
                self.db,
                thread_id=THREAD_ID,
                actor_id=ACTOR_ID,
                message_id=pending.message_id,
                parts=pending.parts,
                metadata=pending.metadata,
            )

    def test_expired_lease_handoff_rejects_old_owner_heartbeat_and_ack(self) -> None:
        service = StoryWorkspaceDreamInternalCommandService(self.db)
        _accepted, old_pending = self._claim(service=service, key="key-handoff")
        self.assertIsNotNone(old_pending)
        metadata = self._metadata()
        metadata["dispatch_claim_lease_until"] = 0
        self.db.execute(
            "UPDATE chat_message SET metadata = ?",
            (json.dumps(metadata),),
        )
        self.db.commit()
        _replayed, new_pending = self._claim(service=service, key="key-handoff")
        self.assertIsNotNone(new_pending)
        old_claim = old_pending.metadata["dispatch_claim_id"]
        new_claim = new_pending.metadata["dispatch_claim_id"]
        self.assertNotEqual(old_claim, new_claim)
        self.assertFalse(service._renew_claim(old_pending.message_id, old_claim))
        self.assertFalse(service._mark_dispatched(old_pending.message_id, old_claim))
        current = self._metadata()
        self.assertEqual(current["dispatch_claim_id"], new_claim)
        self.assertEqual(current["dispatch_status"], "dispatching")

    def test_lease_renews_and_failed_attempt_can_be_explicitly_recovered(self) -> None:
        service = StoryWorkspaceDreamInternalCommandService(self.db)
        _accepted, pending = self._claim(service=service, key="key-lease")
        self.assertIsNotNone(pending)
        before = self._metadata()["dispatch_claim_lease_until"]
        self.assertTrue(
            service._renew_claim(
                pending.message_id,
                pending.metadata["dispatch_claim_id"],
            )
        )
        self.assertGreater(self._metadata()["dispatch_claim_lease_until"], before)
        service._release_claim(
            pending.message_id,
            pending.metadata["dispatch_claim_id"],
        )
        expired = self._metadata()
        expired["dispatch_status"] = "dispatching"
        expired["dispatch_claim_lease_until"] = 0
        self.db.execute(
            "UPDATE chat_message SET metadata = ?",
            (json.dumps(expired),),
        )
        self.db.commit()
        _replayed, recovered = self._claim(service=service, key="key-lease")
        self.assertIsNotNone(recovered)

    def test_success_uses_authoritative_thread_context_and_marks_dispatched(self) -> None:
        factory = _Factory()
        service = StoryWorkspaceDreamInternalCommandService(
            self.db,
            thread_factory=factory,
        )
        _accepted, pending = self._claim(service=service)
        self.assertIsNotNone(pending)
        self.assertTrue(asyncio.run(service.dispatch(pending)))
        self.assertEqual(len(factory.requests), 1)
        request = factory.requests[0]
        self.assertEqual(request.thread_id, THREAD_ID)
        self.assertFalse(hasattr(request, "story_workspace_dream_context"))
        self.assertEqual(self._metadata()["dispatch_status"], "dispatched")

    def test_error_terminal_marks_failed_and_does_not_retry_implicitly(self) -> None:
        factory = _Factory(
            events=[
                NormalizedAgentEvent.create("error", {"errorText": "unavailable"}),
                NormalizedAgentEvent.create("finish", {"finishReason": "error"}),
            ]
        )
        service = StoryWorkspaceDreamInternalCommandService(
            self.db,
            thread_factory=factory,
        )
        _accepted, pending = self._claim(service=service, key="key-error")
        self.assertIsNotNone(pending)
        self.assertFalse(asyncio.run(service.dispatch(pending)))
        metadata = self._metadata()
        self.assertEqual(metadata["dispatch_status"], "failed")
        self.assertEqual(
            metadata["dispatch_error_code"],
            "DREAM_AGENT_DISPATCH_FAILED",
        )

    def test_shutdown_cancellation_keeps_lease_recoverable(self) -> None:
        async def exercise() -> None:
            factory = _Factory(block=True)
            service = StoryWorkspaceDreamInternalCommandService(
                self.db,
                thread_factory=factory,
            )
            _accepted, pending = self._claim(service=service, key="key-cancel")
            self.assertIsNotNone(pending)
            task = asyncio.create_task(service.dispatch(pending))
            await asyncio.wait_for(factory.started.wait(), timeout=0.2)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task

        asyncio.run(exercise())
        metadata = self._metadata()
        self.assertEqual(metadata["dispatch_status"], "dispatching")
        self.assertGreater(metadata["dispatch_claim_lease_until"], 0)

    def test_lost_heartbeat_cancels_inflight_turn_without_acknowledging_old_claim(
        self,
    ) -> None:
        async def exercise() -> None:
            factory = _Factory(block=True)
            service = StoryWorkspaceDreamInternalCommandService(
                self.db,
                thread_factory=factory,
            )
            _accepted, pending = self._claim(service=service, key="key-lost-lease")
            self.assertIsNotNone(pending)
            with patch(
                "services.story_workspace.dream_internal_command_service."
                "_LEASE_HEARTBEAT_SECONDS",
                0,
            ), patch.object(service, "_renew_claim", return_value=False):
                self.assertFalse(await service.dispatch(pending))
            await asyncio.wait_for(factory.cancelled.wait(), timeout=0.2)

        asyncio.run(exercise())
        self.assertEqual(self._metadata()["dispatch_status"], "dispatching")


class DreamInternalCommandCoordinatorTest(unittest.IsolatedAsyncioTestCase):
    def _pending(
        self,
        claim_id: str = "claim-1",
    ) -> StoryWorkspaceDreamInternalPendingDispatch:
        return StoryWorkspaceDreamInternalPendingDispatch(
            thread_id=THREAD_ID,
            actor_id=ACTOR_ID,
            context=_context(),
            message_id="pending-message",
            parts=[{"type": "text", "text": "继续"}],
            metadata={"dispatch_claim_id": claim_id},
        )

    async def test_coalesces_and_awaits_owned_tasks(self) -> None:
        release = asyncio.Event()
        calls: list[str] = []

        async def dispatch(item) -> None:
            calls.append(item.message_id)
            await release.wait()

        coordinator = StoryWorkspaceDreamInternalCommandCoordinator(dispatch)
        pending = self._pending()
        self.assertTrue(coordinator.schedule(pending))
        self.assertFalse(coordinator.schedule(pending))
        await asyncio.sleep(0)
        self.assertEqual(coordinator.diagnostics()["running_tasks"], 1)
        release.set()
        await coordinator.wait_for_idle()
        self.assertEqual(calls, ["pending-message"])
        self.assertEqual(coordinator.diagnostics()["owned_tasks"], 0)

    async def test_aclose_cancels_and_awaits_every_owned_task(self) -> None:
        entered = asyncio.Event()

        async def dispatch(_item) -> None:
            entered.set()
            await asyncio.Event().wait()

        coordinator = StoryWorkspaceDreamInternalCommandCoordinator(dispatch)
        self.assertTrue(coordinator.schedule(self._pending()))
        await asyncio.wait_for(entered.wait(), timeout=0.2)
        await asyncio.wait_for(coordinator.aclose(), timeout=0.2)
        self.assertEqual(coordinator.diagnostics()["owned_tasks"], 0)

    async def test_raising_dispatcher_is_retrieved_logged_and_released(self) -> None:
        async def dispatch(_item) -> None:
            raise RuntimeError("dispatch exploded")

        coordinator = StoryWorkspaceDreamInternalCommandCoordinator(dispatch)
        with patch(
            "services.story_workspace.dream_internal_command_service.logger.error"
        ) as log_error:
            self.assertTrue(coordinator.schedule(self._pending()))
            await coordinator.wait_for_idle()
            await asyncio.sleep(0)

        self.assertEqual(coordinator.diagnostics()["owned_tasks"], 0)
        log_error.assert_called_once()

    async def test_new_claim_cancels_and_awaits_old_owner_before_handoff(self) -> None:
        old_entered = asyncio.Event()
        old_exited = asyncio.Event()
        new_entered = asyncio.Event()

        async def dispatch(item) -> None:
            if item.metadata["dispatch_claim_id"] == "claim-old":
                old_entered.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    old_exited.set()
                return
            self.assertTrue(old_exited.is_set())
            new_entered.set()

        coordinator = StoryWorkspaceDreamInternalCommandCoordinator(dispatch)
        self.assertTrue(coordinator.schedule(self._pending("claim-old")))
        await asyncio.wait_for(old_entered.wait(), timeout=0.2)
        self.assertTrue(coordinator.schedule(self._pending("claim-new")))
        await asyncio.wait_for(new_entered.wait(), timeout=0.2)
        await coordinator.wait_for_idle()

    async def test_recovery_is_bounded_and_start_reopens_after_aclose(self) -> None:
        limits: list[int] = []

        async def recover(limit: int):
            limits.append(limit)
            return []

        async def dispatch(_item) -> None:
            return None

        coordinator = StoryWorkspaceDreamInternalCommandCoordinator(
            dispatch,
            recoverer=recover,
            reconcile_interval_s=3600,
            max_dispatch_tasks=3,
        )
        self.assertEqual(await coordinator.reconcile_once(), 0)
        self.assertEqual(limits, [3])
        await coordinator.aclose()
        self.assertFalse(coordinator.schedule(self._pending()))
        coordinator.start()
        self.assertTrue(coordinator.schedule(self._pending()))
        await coordinator.wait_for_idle()
        await coordinator.aclose()


if __name__ == "__main__":
    unittest.main()
