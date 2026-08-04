"""Focused tests for the one-shot Dream confirmation continuation."""

from __future__ import annotations

import asyncio
from dataclasses import replace
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
for candidate in (str(BACKEND_ROOT), str(REPOSITORY_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

import tests._sdk_stubs  # noqa: F401 - stub optional SDK before service import

import database
import story_workspace.contracts as contracts_module
import claude_agent.service as claude_service_module
from claude_agent.service import (
    ClaudeAgentRunRequest,
    ClaudeAgentService,
    _TurnContext,
)
from claude_agent.thread_pool import AgentRunState
from claude_agent.tool_confirmation_store import ToolConfirmationStore
from models.workflow_run import RunStatus, WorkflowRun
from routers import story_workspace
from services.deck import story_workflow_gateway as gateway_module
import services.story_workspace.dream_confirmation_service as confirmation_module
from services.story_workspace.dream_confirmation_service import (
    STORY_WORKSPACE_DREAM_CONFIRMATION_METADATA_KIND,
    StoryWorkspaceDreamConfirmationDispatch,
    StoryWorkspacePersistedDreamConfirmation,
    StoryWorkspaceDreamConfirmationError,
    StoryWorkspaceDreamConfirmationService,
    StoryWorkspaceDreamConfirmationCoordinator,
    story_workspace_build_dream_confirmation_turn_dispatcher,
    story_workspace_dream_confirmation_message_id,
    story_workspace_mark_dream_confirmation_dispatched,
    story_workspace_read_dream_confirmation_fact,
    story_workspace_read_pending_dream_confirmations,
)
from story_workspace.contracts import (
    StoryWorkspaceDreamConfirmationAccepted,
    StoryWorkspaceDreamConfirmationCommand,
    StoryWorkspaceDreamFilesResponse,
    StoryWorkspaceDreamSourceResponse,
    StoryWorkspaceDreamStage,
    StoryWorkspaceDreamStageResponse,
    StoryWorkspaceDreamRunContext,
)


RUN_ID = "run_" + "a" * 32
OTHER_RUN_ID = "run_" + "b" * 32
THREAD_ID = "thread-dream-confirmation"
OTHER_THREAD_ID = "thread-dream-confirmation-other"
WORKSPACE_ID = "workspace-dream-confirmation"
ACTOR_ID = "41"
OTHER_ACTOR_ID = "42"
NOW = datetime(2026, 8, 4, 12, 0, tzinfo=UTC)


def make_run(
    *,
    run_id: str = RUN_ID,
    thread_id: str | None = THREAD_ID,
    actor_id: str = ACTOR_ID,
) -> WorkflowRun:
    return WorkflowRun(
        workflow_run_id=run_id,
        deck_plugin_id="ink.dream.story-workflow",
        deck_plugin_version="1.0.0",
        workflow_definition_ref="deck://ink.dream/workflow.json",
        deck_runtime_snapshot_id="drs_" + "5" * 32,
        status=RunStatus.RUNNING,
        deck_plugin_manifest_hash="sha256:" + "c" * 64,
        deck_plugin_binding_id="dpb_" + "2" * 32,
        binding_revision=1,
        runtime_plugin_lock_id="rpl_" + "1" * 32,
        runtime_load_receipt_id="rlr_" + "4" * 32,
        workflow_preflight_id="pf_" + "3" * 32,
        agent_session_id="as_" + "6" * 32,
        workspace_id=WORKSPACE_ID,
        idempotency_key="run-key",
        input_hash="sha256:" + "d" * 64,
        semantic_fingerprint="sha256:" + "e" * 64,
        status_version=1,
        created_by=actor_id,
        created_at=NOW,
        started_at=NOW,
        source_voice_thread_id=thread_id,
    )


def complete_projection(
    *,
    run_id: str = RUN_ID,
    thread_id: str = THREAD_ID,
    revisions: tuple[int, int, int] = (2, 3, 4),
) -> StoryWorkspaceDreamFilesResponse:
    source_files = {
        StoryWorkspaceDreamStage.CHARACTERS: "assets/characters/lead.md",
        StoryWorkspaceDreamStage.SCENES: "assets/scenes/opening.md",
        StoryWorkspaceDreamStage.STORYBOARDS: (
            "stories/demo/episodes/EP01/storyboard.yaml"
        ),
    }
    titles = {
        StoryWorkspaceDreamStage.CHARACTERS: "人物",
        StoryWorkspaceDreamStage.SCENES: "场景",
        StoryWorkspaceDreamStage.STORYBOARDS: "分镜",
    }
    routes = {
        StoryWorkspaceDreamStage.CHARACTERS: (
            f"/story-workspace/characters?run={run_id}"
        ),
        StoryWorkspaceDreamStage.SCENES: f"/story-workspace/scenes?run={run_id}",
        StoryWorkspaceDreamStage.STORYBOARDS: (
            f"/story-workspace/runs/{run_id}/execution"
        ),
    }
    stages = {}
    for stage, revision in zip(StoryWorkspaceDreamStage, revisions):
        stages[stage] = StoryWorkspaceDreamStageResponse(
            stage=stage,
            revision=revision,
            source_files=[source_files[stage]],
            page={"title": titles[stage], "entry_route": routes[stage]},
            items=[{
                "entity_id": f"{stage.value}-entity",
                "display_name": stage.value,
                "summary": "summary",
                "source_file": source_files[stage],
                "relations": [],
            }],
        )
    return StoryWorkspaceDreamFilesResponse(
        story_workspace_run_id=run_id,
        thread_id=thread_id,
        source=StoryWorkspaceDreamSourceResponse(
            deck_plugin_binding_id="dpb_" + "2" * 32,
            binding_revision=1,
            deck_plugin_version="1.0.0",
            deck_runtime_snapshot_id="drs_" + "5" * 32,
            runtime_plugin_lock_id="rpl_" + "1" * 32,
        ),
        required_stages=list(StoryWorkspaceDreamStage),
        run_revision=1,
        stages=stages,
        can_confirm=True,
    )


def command(**overrides: object) -> StoryWorkspaceDreamConfirmationCommand:
    body: dict[str, object] = {
        "storyWorkspaceRunId": RUN_ID,
        "threadId": THREAD_ID,
        "baseRevisions": {"characters": 2, "scenes": 3, "storyboards": 4},
        "edits": [{
            "stage": "characters",
            "entityId": "characters-entity",
            "fields": {
                "displayName": "新主角",
                "summary": None,
                "relations": ["scenes-entity"],
            },
        }],
        "idempotencyKey": "swc_test-key",
    }
    body.update(overrides)
    return StoryWorkspaceDreamConfirmationCommand.model_validate(body)


class RecordingProjectionReader:
    def __init__(self, projection: StoryWorkspaceDreamFilesResponse) -> None:
        self.projection = projection
        self.calls = 0

    def __call__(self, run: WorkflowRun, thread_id: str):
        self.calls += 1
        return self.projection


class ManualClock:
    def __init__(self, now: float = 0.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class ConfirmationFixture:
    def __init__(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.old_database_path = database.DB_PATH
        database.DB_PATH = Path(self.temporary_directory.name) / "confirmation.db"
        db = database.get_db()
        database.create_tables(db)
        db.executemany(
            "INSERT INTO users (id, email, password_hash) VALUES (?, ?, 'hash')",
            [
                (int(ACTOR_ID), "dream-confirmation@example.com"),
                (int(OTHER_ACTOR_ID), "other-dream-confirmation@example.com"),
            ],
        )
        db.executemany(
            "INSERT INTO chat_thread (id, user_id, title) VALUES (?, ?, ?)",
            [
                (THREAD_ID, int(ACTOR_ID), "Dream confirmation"),
                (OTHER_THREAD_ID, int(OTHER_ACTOR_ID), "Other Dream"),
            ],
        )
        db.execute(
            "INSERT INTO story_workspace_workspaces (id, name, owner_id) "
            "VALUES (?, 'Dream', ?)",
            (WORKSPACE_ID, int(ACTOR_ID)),
        )
        db.commit()
        db.execute("PRAGMA foreign_keys=OFF")
        database.create_workflow_run_tables(db)
        db.execute(
            "INSERT INTO workflow_runs ("
            "id, workspace_id, deck_plugin_id, deck_plugin_version, "
            "workflow_definition_ref, deck_runtime_snapshot_id, status, "
            "deck_plugin_manifest_hash, deck_plugin_binding_id, "
            "binding_revision, runtime_plugin_lock_id, workflow_preflight_id, "
            "source_voice_thread_id, source_message_id, source_message_time, "
            "idempotency_key, input_hash, "
            "semantic_fingerprint, created_by"
            ") VALUES (?, ?, ?, ?, ?, ?, 'running', ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                RUN_ID,
                WORKSPACE_ID,
                "ink.dream.story-workflow",
                "1.0.0",
                "deck://ink.dream/workflow.json",
                "drs_" + "5" * 32,
                "sha256:" + "c" * 64,
                "dpb_" + "2" * 32,
                "rpl_" + "1" * 32,
                "pf_" + "3" * 32,
                THREAD_ID,
                "message-source-1",
                NOW.isoformat(),
                "run-key",
                "sha256:" + "d" * 64,
                "sha256:" + "e" * 64,
                ACTOR_ID,
            ),
        )
        db.commit()
        db.execute("PRAGMA foreign_keys=ON")
        db.close()
        self.runs = {RUN_ID: make_run()}
        self.projection_reader = RecordingProjectionReader(complete_projection())

    def service(self, *, db: sqlite3.Connection | None = None):
        return StoryWorkspaceDreamConfirmationService(
            db or database.get_db(),
            run_reader=lambda run_id: self.runs[run_id],
            projection_reader=self.projection_reader,
            request_id_factory=lambda: "request-confirmation-1",
        )

    def rows(self) -> list[dict]:
        db = database.get_db()
        try:
            rows = db.execute(
                "SELECT id, thread_id, role, parts, metadata FROM chat_message"
            ).fetchall()
        finally:
            db.close()
        return [
            {
                "id": row["id"],
                "thread_id": row["thread_id"],
                "role": row["role"],
                "parts": json.loads(row["parts"]),
                "metadata": json.loads(row["metadata"]),
            }
            for row in rows
        ]

    def claim(
        self,
        dispatch: StoryWorkspaceDreamConfirmationDispatch,
        *,
        claim_id: str = "claim-test-owner",
        now_s: float = 100.0,
        lease_duration_s: float = 30.0,
    ) -> StoryWorkspaceDreamConfirmationDispatch:
        with database.get_db() as db:
            claimed = (
                confirmation_module.story_workspace_claim_dream_confirmation(
                    db,
                    dispatch,
                    claim_id=claim_id,
                    now_s=now_s,
                    lease_duration_s=lease_duration_s,
                )
            )
        assert claimed is not None
        return claimed

    def close(self) -> None:
        database.DB_PATH = self.old_database_path
        self.temporary_directory.cleanup()


class StoryWorkspaceDreamConfirmationContractTests(unittest.TestCase):
    def test_accepted_contract_uses_rest_camel_aliases(self) -> None:
        accepted = StoryWorkspaceDreamConfirmationAccepted(
            message_id="dream-confirm-1",
            story_workspace_run_id=RUN_ID,
            thread_id=THREAD_ID,
            status="accepted",
            replayed=False,
            dispatched=True,
            request_id="request-1",
        )
        self.assertEqual(
            set(accepted.model_dump(mode="json", by_alias=True)),
            {
                "messageId",
                "storyWorkspaceRunId",
                "threadId",
                "status",
                "replayed",
                "dispatched",
                "requestId",
            },
        )

    def test_nan_never_enters_command(self) -> None:
        with self.assertRaises(ValidationError):
            command(edits=[{
                "stage": "characters",
                "entityId": "characters-entity",
                "fields": {"summary": float("nan")},
            }])

    def test_accepted_contract_is_publicly_exported(self) -> None:
        self.assertIn(
            "StoryWorkspaceDreamConfirmationAccepted",
            contracts_module.__all__,
        )

    def test_files_response_confirmation_fact_controls_can_confirm(self) -> None:
        confirmed = complete_projection().model_copy(update={
            "confirmation_accepted": True,
            "confirmation_dispatched": True,
            "can_confirm": False,
        })
        confirmed = StoryWorkspaceDreamFilesResponse.model_validate(
            confirmed.model_dump()
        )
        wire = confirmed.model_dump(mode="json", by_alias=True)
        self.assertTrue(wire["confirmationAccepted"])
        self.assertTrue(wire["confirmationDispatched"])
        self.assertFalse(wire["canConfirm"])

        with self.assertRaises(ValidationError):
            StoryWorkspaceDreamFilesResponse.model_validate({
                **complete_projection().model_dump(),
                "confirmation_accepted": False,
                "confirmation_dispatched": True,
                "can_confirm": False,
            })


class StoryWorkspaceDreamConfirmationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = ConfirmationFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def submit(self, **overrides: object):
        service = self.fixture.service()
        try:
            return service.submit_confirmation(
                RUN_ID,
                command(**overrides),
                actor_id=ACTOR_ID,
            )
        finally:
            service.close()

    def assert_error(self, expected_status: int, **overrides: object) -> None:
        with self.assertRaises(StoryWorkspaceDreamConfirmationError) as raised:
            self.submit(**overrides)
        self.assertEqual(raised.exception.status_code, expected_status)

    def test_success_persists_one_hidden_command_with_exact_audit_shape(self) -> None:
        persisted = self.submit()
        self.assertFalse(persisted.accepted.replayed)
        self.assertFalse(persisted.accepted.dispatched)
        self.assertIsNotNone(persisted.dispatch)
        rows = self.fixture.rows()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["thread_id"], THREAD_ID)
        self.assertEqual(row["role"], "user")
        metadata = row["metadata"]
        self.assertEqual(
            set(metadata),
            {
                "kind",
                "actor",
                "story_workspace_run_id",
                "thread_id",
                "base_revisions",
                "edit_count",
                "command_fingerprint",
                "idempotency_key",
                "request_id",
                "dispatch_status",
            },
        )
        self.assertEqual(
            metadata["kind"],
            STORY_WORKSPACE_DREAM_CONFIRMATION_METADATA_KIND,
        )
        self.assertEqual(metadata["actor"], ACTOR_ID)
        self.assertEqual(metadata["story_workspace_run_id"], RUN_ID)
        self.assertEqual(metadata["thread_id"], THREAD_ID)
        self.assertEqual(metadata["base_revisions"], {
            "characters": 2,
            "scenes": 3,
            "storyboards": 4,
        })
        self.assertEqual(metadata["edit_count"], 1)
        self.assertEqual(metadata["idempotency_key"], "swc_test-key")
        self.assertTrue(metadata["command_fingerprint"].startswith("sha256:"))
        self.assertEqual(metadata["request_id"], "request-confirmation-1")
        self.assertEqual(metadata["dispatch_status"], "pending")
        self.assertEqual(row["id"], persisted.accepted.message_id)
        self.assertEqual(
            row["id"],
            story_workspace_dream_confirmation_message_id(
                ACTOR_ID, RUN_ID, "swc_test-key"
            ),
        )

        self.assertEqual(len(row["parts"]), 1)
        part = row["parts"][0]
        self.assertEqual(part["type"], "text")
        text = part["text"]
        self.assertIn('"storyWorkspaceRunId"', text)
        self.assertIn('"threadId"', text)
        self.assertIn('"baseRevisions"', text)
        self.assertIn('"entityId"', text)
        self.assertIn('"displayName"', text)
        self.assertIn("canonical workspace files", text)
        self.assertIn("stage revision", text)
        self.assertIn("same plugin", text)
        self.assertIn("Do not ask for another confirmation", text)
        forbidden = ("reject", "failure", "retry", "archive")
        serialized = json.dumps(row, ensure_ascii=False).lower()
        self.assertFalse(any(word in serialized for word in forbidden))

    def test_agent_service_resave_preserves_hidden_command_and_metadata(self) -> None:
        persisted = self.submit()
        original = self.fixture.rows()[0]

        async def _resave() -> None:
            request = ClaudeAgentRunRequest(
                user_id=ACTOR_ID,
                thread_id=THREAD_ID,
                resume=True,
                message_id=persisted.accepted.message_id,
                message_parts=original["parts"],
                message_metadata=original["metadata"],
            )
            execution = claude_service_module._TurnExecution(
                request=request,
                state=AgentRunState(session_id=THREAD_ID),
                runner=unittest.mock.Mock(),
                run_options=unittest.mock.Mock(),
                turn_context=_TurnContext(
                    queue=asyncio.Queue(),
                    confirmation_store=ToolConfirmationStore(),
                ),
            )
            await ClaudeAgentService()._persist_user_message(execution)

        asyncio.run(_resave())
        rewritten = self.fixture.rows()[0]
        self.assertEqual(rewritten["id"], original["id"])
        self.assertEqual(rewritten["parts"], original["parts"])
        self.assertEqual(rewritten["metadata"], original["metadata"])
        self.assertEqual(
            rewritten["metadata"]["kind"],
            STORY_WORKSPACE_DREAM_CONFIRMATION_METADATA_KIND,
        )
        structured = json.loads(rewritten["parts"][0]["text"])
        self.assertEqual(
            structured["command"],
            command().model_dump(mode="json", by_alias=True),
        )

    def test_url_body_and_authoritative_thread_mismatches_are_rejected(self) -> None:
        self.assert_error(409, storyWorkspaceRunId=OTHER_RUN_ID)
        self.assert_error(409, threadId=OTHER_THREAD_ID)
        self.fixture.runs[RUN_ID] = make_run(thread_id=OTHER_THREAD_ID)
        self.assert_error(403, threadId=OTHER_THREAD_ID)
        self.assertEqual(self.fixture.rows(), [])

    def test_required_stages_and_exact_revisions_are_required(self) -> None:
        incomplete = complete_projection()
        del incomplete.stages[StoryWorkspaceDreamStage.STORYBOARDS]
        object.__setattr__(incomplete, "can_confirm", False)
        self.fixture.projection_reader.projection = incomplete
        self.assert_error(409)

        self.fixture.projection_reader.projection = complete_projection(
            revisions=(9, 3, 4)
        )
        self.assert_error(409)
        self.assertEqual(self.fixture.rows(), [])

    def test_edits_require_known_entities_and_exact_field_whitelist_and_types(self) -> None:
        invalid_edits = [
            {"stage": "characters", "entityId": "unknown", "fields": {"summary": "x"}},
            {"stage": "characters", "entityId": "characters-entity", "fields": {"sourceFile": "x"}},
            {"stage": "characters", "entityId": "characters-entity", "fields": {"display_name": "x"}},
            {"stage": "characters", "entityId": "characters-entity", "fields": {"displayName": " "}},
            {"stage": "characters", "entityId": "characters-entity", "fields": {"displayName": "x" * 201}},
            {"stage": "characters", "entityId": "characters-entity", "fields": {"summary": 3}},
            {"stage": "characters", "entityId": "characters-entity", "fields": {"summary": "x" * 4001}},
            {"stage": "characters", "entityId": "characters-entity", "fields": {"relations": "x"}},
            {"stage": "characters", "entityId": "characters-entity", "fields": {"relations": [""]}},
            {"stage": "characters", "entityId": "characters-entity", "fields": {"relations": ["x" * 129]}},
            {"stage": "characters", "entityId": "characters-entity", "fields": {"relations": [str(i) for i in range(101)]}},
        ]
        for edits in invalid_edits:
            with self.subTest(edits=edits):
                self.assert_error(422, edits=[edits])
        self.assertEqual(self.fixture.rows(), [])

    def test_pending_exact_replay_recovers_dispatch_then_success_stays_one_shot(
        self,
    ) -> None:
        first = self.submit()
        replay = self.submit()
        self.assertFalse(first.accepted.replayed)
        self.assertTrue(replay.accepted.replayed)
        self.assertEqual(first.accepted.request_id, replay.accepted.request_id)
        self.assertIsNotNone(replay.dispatch)
        self.assertFalse(replay.accepted.dispatched)
        self.assertEqual(replay.dispatch.parts, first.dispatch.parts)
        self.assertEqual(
            replay.dispatch.metadata["dispatch_status"],
            "pending",
        )
        self.assertEqual(len(self.fixture.rows()), 1)

        db = database.get_db()
        try:
            claimed = self.fixture.claim(replay.dispatch)
            self.assertTrue(
                story_workspace_mark_dream_confirmation_dispatched(
                    db,
                    claimed,
                )
            )
        finally:
            db.close()

        completed_replay = self.submit()
        self.assertTrue(completed_replay.accepted.replayed)
        self.assertTrue(completed_replay.accepted.dispatched)
        self.assertIsNone(completed_replay.dispatch)
        self.assertEqual(
            self.fixture.rows()[0]["metadata"]["dispatch_status"],
            "dispatched",
        )

        with self.assertRaises(StoryWorkspaceDreamConfirmationError) as raised:
            self.submit(edits=[], idempotencyKey="swc_test-key")
        self.assertEqual(
            (raised.exception.code, raised.exception.status_code),
            ("IDEMPOTENCY_CONFLICT", 409),
        )
        self.assertEqual(len(self.fixture.rows()), 1)

    def test_actor_run_allows_only_one_confirmation_across_idempotency_keys(
        self,
    ) -> None:
        first = self.submit()
        with self.assertRaises(StoryWorkspaceDreamConfirmationError) as raised:
            self.submit(idempotencyKey="swc_second-key")

        self.assertEqual(
            (raised.exception.code, raised.exception.status_code),
            ("IDEMPOTENCY_CONFLICT", 409),
        )
        self.assertEqual(len(self.fixture.rows()), 1)
        self.assertEqual(self.fixture.rows()[0]["id"], first.accepted.message_id)

    def test_actor_run_uniqueness_does_not_depend_on_current_thread(self) -> None:
        first = self.submit()
        replacement_thread_id = "thread-dream-confirmation-rebound"
        db = database.get_db()
        try:
            db.execute(
                "INSERT INTO chat_thread (id, user_id, title) VALUES (?, ?, ?)",
                (replacement_thread_id, int(ACTOR_ID), "Rebound Dream"),
            )
            db.commit()
        finally:
            db.close()
        self.fixture.runs[RUN_ID] = make_run(thread_id=replacement_thread_id)

        with self.assertRaises(StoryWorkspaceDreamConfirmationError) as raised:
            self.submit(
                threadId=replacement_thread_id,
                idempotencyKey="swc_rebound-key",
            )

        self.assertEqual(
            (raised.exception.code, raised.exception.status_code),
            ("IDEMPOTENCY_CONFLICT", 409),
        )
        self.assertEqual(len(self.fixture.rows()), 1)
        self.assertEqual(self.fixture.rows()[0]["id"], first.accepted.message_id)

    def test_confirmation_fact_is_scoped_to_actor_thread_and_run(self) -> None:
        persisted = self.submit()
        claimed = self.fixture.claim(persisted.dispatch)
        db = database.get_db()
        try:
            self.assertEqual(
                story_workspace_read_dream_confirmation_fact(
                    db,
                    actor_id=ACTOR_ID,
                    thread_id=THREAD_ID,
                    run_id=RUN_ID,
                ),
                (True, False),
            )
            self.assertEqual(
                story_workspace_read_dream_confirmation_fact(
                    db,
                    actor_id=OTHER_ACTOR_ID,
                    thread_id=THREAD_ID,
                    run_id=RUN_ID,
                ),
                (False, False),
            )
            self.assertTrue(
                story_workspace_mark_dream_confirmation_dispatched(
                    db,
                    claimed,
                )
            )
            self.assertEqual(
                story_workspace_read_dream_confirmation_fact(
                    db,
                    actor_id=ACTOR_ID,
                    thread_id=THREAD_ID,
                    run_id=RUN_ID,
                ),
                (True, True),
            )
        finally:
            db.close()

    def test_actor_run_and_key_are_isolated_in_message_id(self) -> None:
        first = story_workspace_dream_confirmation_message_id(
            ACTOR_ID,
            RUN_ID,
            "swc_same",
        )
        self.assertNotEqual(
            first,
            story_workspace_dream_confirmation_message_id(
                ACTOR_ID, RUN_ID, "swc_different"
            ),
        )
        self.assertNotEqual(
            first,
            story_workspace_dream_confirmation_message_id(
                OTHER_ACTOR_ID, RUN_ID, "swc_same"
            ),
        )
        self.assertNotEqual(
            first,
            story_workspace_dream_confirmation_message_id(
                ACTOR_ID, OTHER_RUN_ID, "swc_same"
            ),
        )

    def test_second_projection_read_fails_closed_before_insert(self) -> None:
        first = complete_projection()
        stale = complete_projection(revisions=(3, 3, 4))

        class ChangingReader:
            calls = 0

            def __call__(self, _run, _thread):
                self.calls += 1
                return first if self.calls == 1 else stale

        service = StoryWorkspaceDreamConfirmationService(
            database.get_db(),
            run_reader=lambda _run_id: self.fixture.runs[RUN_ID],
            projection_reader=ChangingReader(),
        )
        try:
            with self.assertRaises(StoryWorkspaceDreamConfirmationError) as raised:
                service.submit_confirmation(RUN_ID, command(), actor_id=ACTOR_ID)
        finally:
            service.close()
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(self.fixture.rows(), [])

    def test_database_failure_rolls_back_message_and_thread_touch(self) -> None:
        db = database.get_db()
        original_updated_at = db.execute(
            "SELECT updated_at FROM chat_thread WHERE id = ?", (THREAD_ID,)
        ).fetchone()[0]
        db.execute(
            "CREATE TRIGGER fail_confirmation_touch BEFORE UPDATE ON chat_thread "
            "BEGIN SELECT RAISE(ABORT, 'touch failed'); END"
        )
        db.commit()
        service = self.fixture.service(db=db)
        try:
            with self.assertRaises(StoryWorkspaceDreamConfirmationError) as raised:
                service.submit_confirmation(RUN_ID, command(), actor_id=ACTOR_ID)
            row_count = db.execute("SELECT COUNT(*) FROM chat_message").fetchone()[0]
            updated_at = db.execute(
                "SELECT updated_at FROM chat_thread WHERE id = ?", (THREAD_ID,)
            ).fetchone()[0]
        finally:
            service.close()
        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(row_count, 0)
        self.assertEqual(updated_at, original_updated_at)

    def test_concurrent_same_submission_inserts_once(self) -> None:
        barrier = threading.Barrier(2)
        results = []
        errors = []

        def worker() -> None:
            service = self.fixture.service()
            try:
                barrier.wait(timeout=5)
                results.append(service.submit_confirmation(
                    RUN_ID, command(), actor_id=ACTOR_ID
                ))
            except BaseException as exc:
                errors.append(exc)
            finally:
                service.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        self.assertEqual(errors, [])
        self.assertEqual(len(results), 2)
        self.assertEqual(sorted(r.accepted.replayed for r in results), [False, True])
        self.assertEqual(sum(r.dispatch is not None for r in results), 2)
        self.assertEqual(len(self.fixture.rows()), 1)


class StoryWorkspaceDreamConfirmationCoordinatorTests(
    unittest.IsolatedAsyncioTestCase
):
    async def asyncSetUp(self) -> None:
        self.fixture = ConfirmationFixture()

    async def asyncTearDown(self) -> None:
        self.fixture.close()

    async def _wait_until(self, predicate, *, timeout: float = 1.0) -> None:
        async def wait() -> None:
            while not predicate():
                await asyncio.sleep(0.005)

        await asyncio.wait_for(wait(), timeout=timeout)

    async def test_two_coordinators_atomically_claim_one_pending_message(
        self,
    ) -> None:
        self.fixture.service().submit_confirmation(
            RUN_ID,
            command(),
            actor_id=ACTOR_ID,
        )
        claim_barrier = threading.Barrier(2)
        result_lock = threading.Lock()
        scheduled: list[int] = []
        consumptions = 0

        async def consume(*_args):
            nonlocal consumptions
            with result_lock:
                consumptions += 1
            return True

        def worker(index: int) -> None:
            db_opens = 0

            def competing_db_factory():
                nonlocal db_opens
                db_opens += 1
                # First connection scans. Align the second connection so both
                # independent event loops contend on the claim transaction.
                if db_opens == 2:
                    claim_barrier.wait(timeout=5)
                return database.get_db()

            async def run() -> None:
                coordinator = StoryWorkspaceDreamConfirmationCoordinator(
                    competing_db_factory,
                    dispatcher_factory=lambda: consume,
                    reconcile_interval_s=3600,
                    lease_clock=ManualClock(1_000.0),
                    claim_id_factory=lambda: f"claim-{index}",
                )
                claimed_count = await coordinator.reconcile_once()
                await coordinator.wait_for_idle()
                with result_lock:
                    scheduled.append(claimed_count)

            asyncio.run(run())

        await asyncio.gather(
            asyncio.to_thread(worker, 0),
            asyncio.to_thread(worker, 1),
        )

        self.assertEqual(sorted(scheduled), [0, 1])
        self.assertEqual(consumptions, 1)

    async def test_fresh_claim_blocks_other_coordinator_scan_and_agent(
        self,
    ) -> None:
        persisted = self.fixture.service().submit_confirmation(
            RUN_ID,
            command(),
            actor_id=ACTOR_ID,
        )
        entered = asyncio.Event()
        release = asyncio.Event()
        consumptions = 0

        async def consume(*_args):
            nonlocal consumptions
            consumptions += 1
            entered.set()
            await release.wait()
            return True

        clock = ManualClock(2_000.0)
        first = StoryWorkspaceDreamConfirmationCoordinator(
            database.get_db,
            dispatcher_factory=lambda: consume,
            reconcile_interval_s=3600,
            lease_clock=clock,
            claim_id_factory=lambda: "claim-first",
        )
        second = StoryWorkspaceDreamConfirmationCoordinator(
            database.get_db,
            dispatcher_factory=lambda: consume,
            reconcile_interval_s=3600,
            lease_clock=clock,
            claim_id_factory=lambda: "claim-second",
        )
        try:
            self.assertTrue(first.schedule(persisted.dispatch))
            await entered.wait()
            self.assertEqual(await second.reconcile_once(), 0)
            self.assertFalse(second.schedule(persisted.dispatch))
            self.assertEqual(consumptions, 1)
            release.set()
            await first.wait_for_idle()
        finally:
            release.set()
            await first.stop()
            await second.stop()

    async def test_claimed_metadata_survives_agent_user_message_resave(
        self,
    ) -> None:
        persisted = self.fixture.service().submit_confirmation(
            RUN_ID,
            command(),
            actor_id=ACTOR_ID,
        )
        observed: list[dict] = []

        async def consume(thread_id, actor_id, message_id, parts, metadata):
            request = ClaudeAgentRunRequest(
                user_id=actor_id,
                thread_id=thread_id,
                resume=True,
                message_id=message_id,
                message_parts=parts,
                message_metadata=metadata,
            )
            execution = claude_service_module._TurnExecution(
                request=request,
                state=AgentRunState(session_id=thread_id),
                runner=unittest.mock.Mock(),
                run_options=unittest.mock.Mock(),
                turn_context=_TurnContext(
                    queue=asyncio.Queue(),
                    confirmation_store=ToolConfirmationStore(),
                ),
            )
            await ClaudeAgentService()._persist_user_message(execution)
            observed.append(self.fixture.rows()[0]["metadata"])
            return True

        coordinator = StoryWorkspaceDreamConfirmationCoordinator(
            database.get_db,
            dispatcher_factory=lambda: consume,
            reconcile_interval_s=3600,
            lease_clock=ManualClock(3_000.0),
            claim_id_factory=lambda: "claim-agent-resave",
        )
        self.assertTrue(coordinator.schedule(persisted.dispatch))
        await coordinator.wait_for_idle()

        self.assertEqual(observed[0]["dispatch_status"], "dispatching")
        self.assertEqual(
            observed[0]["dispatch_claim_id"],
            "claim-agent-resave",
        )
        completed = self.fixture.rows()[0]["metadata"]
        self.assertEqual(completed["dispatch_status"], "dispatched")
        self.assertNotIn("dispatch_claim_id", completed)

    async def test_exact_replay_during_fresh_claim_cannot_schedule_dispatch(
        self,
    ) -> None:
        persisted = self.fixture.service().submit_confirmation(
            RUN_ID,
            command(),
            actor_id=ACTOR_ID,
        )
        entered = asyncio.Event()
        release = asyncio.Event()

        async def consume(*_args):
            entered.set()
            await release.wait()
            return True

        coordinator = StoryWorkspaceDreamConfirmationCoordinator(
            database.get_db,
            dispatcher_factory=lambda: consume,
            reconcile_interval_s=3600,
            lease_clock=ManualClock(4_000.0),
            claim_id_factory=lambda: "claim-replay",
        )
        try:
            self.assertTrue(coordinator.schedule(persisted.dispatch))
            await entered.wait()
            replay = self.fixture.service().submit_confirmation(
                RUN_ID,
                command(),
                actor_id=ACTOR_ID,
            )
            self.assertTrue(replay.accepted.replayed)
            self.assertFalse(replay.accepted.dispatched)
            self.assertIsNone(replay.dispatch)
            self.assertFalse(coordinator.schedule(replay.dispatch))
        finally:
            release.set()
            await coordinator.wait_for_idle()

    async def test_ack_rejects_non_owner_claim(self) -> None:
        persisted = self.fixture.service().submit_confirmation(
            RUN_ID,
            command(),
            actor_id=ACTOR_ID,
        )
        with database.get_db() as db:
            claimed = confirmation_module.story_workspace_claim_dream_confirmation(
                db,
                persisted.dispatch,
                claim_id="claim-owner",
                now_s=5_000.0,
                lease_duration_s=30.0,
            )
        self.assertIsNotNone(claimed)
        wrong_claim = replace(
            claimed,
            metadata={
                **claimed.metadata,
                "dispatch_claim_id": "claim-not-owner",
            },
        )
        with database.get_db() as db:
            with self.assertRaises(StoryWorkspaceDreamConfirmationError) as raised:
                story_workspace_mark_dream_confirmation_dispatched(
                    db,
                    wrong_claim,
                )
            self.assertEqual(raised.exception.status_code, 409)
            self.assertTrue(
                story_workspace_mark_dream_confirmation_dispatched(db, claimed)
            )
            self.assertTrue(
                story_workspace_mark_dream_confirmation_dispatched(db, claimed)
            )

    async def test_stale_lease_is_recovered_once_across_two_coordinators(
        self,
    ) -> None:
        persisted = self.fixture.service().submit_confirmation(
            RUN_ID,
            command(),
            actor_id=ACTOR_ID,
        )
        with database.get_db() as db:
            original_claim = (
                confirmation_module.story_workspace_claim_dream_confirmation(
                    db,
                    persisted.dispatch,
                    claim_id="claim-stale",
                    now_s=6_000.0,
                    lease_duration_s=10.0,
                )
            )
        self.assertIsNotNone(original_claim)

        entered = 0
        first_entered = asyncio.Event()
        release = asyncio.Event()

        async def consume(*_args):
            nonlocal entered
            entered += 1
            first_entered.set()
            await release.wait()
            return True

        clock = ManualClock(6_011.0)
        coordinators = [
            StoryWorkspaceDreamConfirmationCoordinator(
                database.get_db,
                dispatcher_factory=lambda: consume,
                reconcile_interval_s=3600,
                lease_clock=clock,
                claim_id_factory=lambda index=index: f"claim-recovered-{index}",
            )
            for index in range(2)
        ]
        try:
            scheduled = await asyncio.gather(
                *(coordinator.reconcile_once() for coordinator in coordinators)
            )
            await first_entered.wait()
            self.assertEqual(sum(scheduled), 1)
            self.assertEqual(entered, 1)
            release.set()
            await asyncio.gather(
                *(coordinator.wait_for_idle() for coordinator in coordinators)
            )
        finally:
            release.set()
            await asyncio.gather(
                *(coordinator.stop() for coordinator in coordinators)
            )

    async def test_failed_consumption_remains_pending_then_reconciles(self) -> None:
        persisted = self.fixture.service().submit_confirmation(
            RUN_ID,
            command(),
            actor_id=ACTOR_ID,
        )
        attempts: list[str] = []

        async def consume(thread_id, actor_id, message_id, parts, metadata):
            attempts.append(message_id)
            if len(attempts) == 1:
                raise RuntimeError("stream failed before completion")
            return True

        clock = ManualClock()
        coordinator = StoryWorkspaceDreamConfirmationCoordinator(
            database.get_db,
            dispatcher_factory=lambda: consume,
            reconcile_interval_s=3600,
            clock=clock,
            lease_clock=clock,
            retry_base_s=2,
            retry_max_s=8,
        )
        try:
            coordinator.start()
            await self._wait_until(lambda: len(attempts) == 1)
            await coordinator.wait_for_idle()
            with database.get_db() as db:
                self.assertEqual(
                    story_workspace_read_dream_confirmation_fact(
                        db,
                        actor_id=ACTOR_ID,
                        thread_id=THREAD_ID,
                        run_id=RUN_ID,
                    ),
                    (True, False),
                )

            self.assertEqual(await coordinator.reconcile_once(), 0)
            clock.advance(2)
            self.assertEqual(await coordinator.reconcile_once(), 1)
            await self._wait_until(lambda: len(attempts) == 2)
            await coordinator.wait_for_idle()
            with database.get_db() as db:
                self.assertEqual(
                    story_workspace_read_dream_confirmation_fact(
                        db,
                        actor_id=ACTOR_ID,
                        thread_id=THREAD_ID,
                        run_id=RUN_ID,
                    ),
                    (True, True),
                )
        finally:
            await coordinator.stop()

        self.assertEqual(attempts, [persisted.accepted.message_id] * 2)

    async def test_completion_before_ack_can_replay_but_cannot_lose_work(self) -> None:
        persisted = self.fixture.service().submit_confirmation(
            RUN_ID,
            command(),
            actor_id=ACTOR_ID,
        )
        consumptions = 0

        async def consume(*_args):
            nonlocal consumptions
            consumptions += 1
            return True

        clock = ManualClock()
        coordinator = StoryWorkspaceDreamConfirmationCoordinator(
            database.get_db,
            dispatcher_factory=lambda: consume,
            reconcile_interval_s=3600,
            clock=clock,
            lease_clock=clock,
            lease_duration_s=2,
            retry_base_s=2,
            retry_max_s=8,
        )
        real_mark = coordinator._mark_dispatched_sync
        acknowledgements = 0

        def flaky_mark(dispatch):
            nonlocal acknowledgements
            acknowledgements += 1
            if acknowledgements == 1:
                raise RuntimeError("process stopped before durable ack")
            return real_mark(dispatch)

        with patch.object(coordinator, "_mark_dispatched_sync", flaky_mark):
            coordinator.schedule(persisted.dispatch)
            await coordinator.wait_for_idle()
            with database.get_db() as db:
                self.assertEqual(
                    story_workspace_read_dream_confirmation_fact(
                        db,
                        actor_id=ACTOR_ID,
                        thread_id=THREAD_ID,
                        run_id=RUN_ID,
                    ),
                    (True, False),
                )
            self.assertEqual(await coordinator.reconcile_once(), 0)
            clock.advance(2)
            self.assertEqual(await coordinator.reconcile_once(), 1)
            await coordinator.wait_for_idle()

        with database.get_db() as db:
            self.assertEqual(
                story_workspace_read_dream_confirmation_fact(
                    db,
                    actor_id=ACTOR_ID,
                    thread_id=THREAD_ID,
                    run_id=RUN_ID,
                ),
                (True, True),
            )
        self.assertEqual(consumptions, 2)
        self.assertEqual(acknowledgements, 2)

    async def test_false_consumption_uses_exponential_per_message_backoff(self) -> None:
        persisted = self.fixture.service().submit_confirmation(
            RUN_ID,
            command(),
            actor_id=ACTOR_ID,
        )
        attempts = 0

        async def consume(*_args):
            nonlocal attempts
            attempts += 1
            return attempts >= 3

        clock = ManualClock()
        coordinator = StoryWorkspaceDreamConfirmationCoordinator(
            database.get_db,
            dispatcher_factory=lambda: consume,
            reconcile_interval_s=0.01,
            clock=clock,
            lease_clock=clock,
            retry_base_s=2,
            retry_max_s=8,
        )

        coordinator.schedule(persisted.dispatch)
        await coordinator.wait_for_idle()
        self.assertEqual(attempts, 1)
        self.assertEqual(await coordinator.reconcile_once(), 0)
        clock.advance(1.99)
        self.assertEqual(await coordinator.reconcile_once(), 0)
        clock.advance(0.01)
        self.assertEqual(await coordinator.reconcile_once(), 1)
        await coordinator.wait_for_idle()
        self.assertEqual(attempts, 2)

        clock.advance(3.99)
        self.assertEqual(await coordinator.reconcile_once(), 0)
        clock.advance(0.01)
        self.assertEqual(await coordinator.reconcile_once(), 1)
        await coordinator.wait_for_idle()
        self.assertEqual(attempts, 3)
        self.assertNotIn(
            persisted.accepted.message_id,
            coordinator._retry_state,
        )
        with database.get_db() as db:
            self.assertEqual(
                story_workspace_read_dream_confirmation_fact(
                    db,
                    actor_id=ACTOR_ID,
                    thread_id=THREAD_ID,
                    run_id=RUN_ID,
                ),
                (True, True),
            )

    async def test_scan_and_submit_deduplicate_one_in_flight_message(self) -> None:
        persisted = self.fixture.service().submit_confirmation(
            RUN_ID,
            command(),
            actor_id=ACTOR_ID,
        )
        entered = asyncio.Event()
        release = asyncio.Event()
        attempts = 0

        async def consume(*_args):
            nonlocal attempts
            attempts += 1
            entered.set()
            await release.wait()
            return True

        coordinator = StoryWorkspaceDreamConfirmationCoordinator(
            database.get_db,
            dispatcher_factory=lambda: consume,
            reconcile_interval_s=3600,
        )
        try:
            self.assertTrue(coordinator.schedule(persisted.dispatch))
            await entered.wait()
            await coordinator.reconcile_once()
            self.assertFalse(coordinator.schedule(persisted.dispatch))
            self.assertEqual(attempts, 1)
            release.set()
            await coordinator.wait_for_idle()
        finally:
            await coordinator.stop()

    async def test_shutdown_cancels_consumption_and_leaves_pending(self) -> None:
        persisted = self.fixture.service().submit_confirmation(
            RUN_ID,
            command(),
            actor_id=ACTOR_ID,
        )
        entered = asyncio.Event()

        async def consume(*_args):
            entered.set()
            await asyncio.Event().wait()

        coordinator = StoryWorkspaceDreamConfirmationCoordinator(
            database.get_db,
            dispatcher_factory=lambda: consume,
            reconcile_interval_s=3600,
        )
        coordinator.schedule(persisted.dispatch)
        await entered.wait()
        await coordinator.stop()

        with database.get_db() as db:
            self.assertEqual(
                story_workspace_read_dream_confirmation_fact(
                    db,
                    actor_id=ACTOR_ID,
                    thread_id=THREAD_ID,
                    run_id=RUN_ID,
                ),
                (True, False),
            )

    async def test_scan_fails_closed_when_run_authority_binding_drifts(self) -> None:
        self.fixture.service().submit_confirmation(
            RUN_ID,
            command(),
            actor_id=ACTOR_ID,
        )
        cases = (
            (
                "UPDATE story_workspace_workspaces SET owner_id = ? WHERE id = ?",
                (int(OTHER_ACTOR_ID), WORKSPACE_ID),
                "UPDATE story_workspace_workspaces SET owner_id = ? WHERE id = ?",
                (int(ACTOR_ID), WORKSPACE_ID),
            ),
        )
        for mutate, values, restore, restore_values in cases:
            with self.subTest(mutate=mutate):
                with database.get_db() as db:
                    db.execute(mutate, values)
                    db.commit()
                    self.assertEqual(
                        story_workspace_read_pending_dream_confirmations(db),
                        [],
                    )
                    db.execute(restore, restore_values)
                    db.commit()

    async def test_scan_recovers_legacy_pending_row_without_dispatch_status(self) -> None:
        persisted = self.fixture.service().submit_confirmation(
            RUN_ID,
            command(),
            actor_id=ACTOR_ID,
        )
        with database.get_db() as db:
            row = db.execute(
                "SELECT metadata FROM chat_message WHERE id = ?",
                (persisted.accepted.message_id,),
            ).fetchone()
            metadata = json.loads(row["metadata"])
            metadata.pop("dispatch_status")
            db.execute(
                "UPDATE chat_message SET metadata = ? WHERE id = ?",
                (json.dumps(metadata), persisted.accepted.message_id),
            )
            db.commit()
            pending = story_workspace_read_pending_dream_confirmations(db)

        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].message_id, persisted.accepted.message_id)

    async def test_scan_skips_malformed_pending_envelope(self) -> None:
        persisted = self.fixture.service().submit_confirmation(
            RUN_ID,
            command(),
            actor_id=ACTOR_ID,
        )
        with database.get_db() as db:
            db.execute(
                "UPDATE chat_message SET parts = ? WHERE id = ?",
                (
                    json.dumps([{"type": "text", "text": "[]"}]),
                    persisted.accepted.message_id,
                ),
            )
            db.commit()
            self.assertEqual(
                story_workspace_read_pending_dream_confirmations(db),
                [],
            )


class StoryWorkspaceDreamConfirmationDispatcherTests(unittest.IsolatedAsyncioTestCase):
    async def test_resume_rebuilds_dream_context_from_persisted_run(self) -> None:
        requests = []

        class FakeFactory:
            async def run_streaming(self, request):
                requests.append(request)
                yield 'data: {"type":"message-final","text":"done"}\n\n'
                yield 'data: {"type":"finish","finishReason":"stop"}\n\n'

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "resume-context.db"
            db = sqlite3.connect(db_path)
            db.executescript(
                """
                CREATE TABLE story_workspace_workspaces (
                    id TEXT PRIMARY KEY, owner_id INTEGER NOT NULL
                );
                CREATE TABLE deck_plugin_bindings (
                    deck_plugin_binding_id TEXT PRIMARY KEY,
                    deck_id TEXT NOT NULL,
                    deck_plugin_id TEXT NOT NULL,
                    deck_plugin_version TEXT NOT NULL,
                    binding_revision INTEGER NOT NULL
                );
                CREATE TABLE workflow_runs (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    source_voice_thread_id TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    deck_plugin_id TEXT NOT NULL,
                    deck_plugin_version TEXT NOT NULL,
                    deck_plugin_binding_id TEXT NOT NULL,
                    binding_revision INTEGER NOT NULL,
                    deck_runtime_snapshot_id TEXT NOT NULL,
                    runtime_plugin_lock_id TEXT NOT NULL
                );
                """
            )
            db.execute(
                "INSERT INTO story_workspace_workspaces VALUES (?, ?)",
                (WORKSPACE_ID, int(ACTOR_ID)),
            )
            db.execute(
                "INSERT INTO deck_plugin_bindings VALUES (?, ?, ?, ?, ?)",
                (
                    "dpb_" + "2" * 32,
                    "deck-dream",
                    "ink.dream.story-workflow",
                    "1.0.0",
                    1,
                ),
            )
            db.execute(
                "INSERT INTO workflow_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    RUN_ID,
                    WORKSPACE_ID,
                    THREAD_ID,
                    ACTOR_ID,
                    "ink.dream.story-workflow",
                    "1.0.0",
                    "dpb_" + "2" * 32,
                    1,
                    "drs_" + "5" * 32,
                    "rpl_" + "1" * 32,
                ),
            )
            db.commit()
            db.close()

            def open_db() -> sqlite3.Connection:
                return sqlite3.connect(db_path)

            dispatcher = story_workspace_build_dream_confirmation_turn_dispatcher(
                FakeFactory(),
                request_factory=lambda **values: SimpleNamespace(**values),
            )
            metadata = {
                "kind": STORY_WORKSPACE_DREAM_CONFIRMATION_METADATA_KIND,
                "story_workspace_run_id": RUN_ID,
                "thread_id": THREAD_ID,
                "actor": ACTOR_ID,
            }
            with patch.object(database, "get_db", side_effect=open_db):
                self.assertTrue(
                    await dispatcher(
                        THREAD_ID,
                        ACTOR_ID,
                        "message-resume",
                        [{"type": "text", "text": "continue"}],
                        metadata,
                    )
                )

        context = requests[0].story_workspace_dream_context
        self.assertEqual(context.workflow_run_id, RUN_ID)
        self.assertEqual(context.thread_id, THREAD_ID)
        self.assertEqual(context.deck_id, "deck-dream")
        self.assertEqual(context.binding_revision, 1)

    async def test_running_thread_is_queued_on_factory_lock_and_uses_same_turn_data(self) -> None:
        release = asyncio.Event()
        entered = asyncio.Event()
        requests = []

        class FakeFactory:
            async def run_streaming(self, request):
                requests.append(request)
                entered.set()
                await release.wait()
                yield 'data: {"type":"message-final","text":"done"}\n\n'
                yield 'data: {"type":"finish","finishReason":"stop"}\n\n'

        dispatcher = story_workspace_build_dream_confirmation_turn_dispatcher(
            FakeFactory(),
            request_factory=lambda **values: SimpleNamespace(**values),
            context_loader=lambda thread_id, actor_id, metadata: StoryWorkspaceDreamRunContext(
                workflow_run_id=RUN_ID,
                thread_id=thread_id,
                deck_id="deck-dream",
                deck_plugin_id="ink.dream.story-workflow",
                deck_plugin_version="1.0.0",
                deck_plugin_binding_id="dpb_" + "2" * 32,
                binding_revision=1,
                deck_runtime_snapshot_id="drs_" + "5" * 32,
                runtime_plugin_lock_id="rpl_" + "1" * 32,
            ),
        )
        parts = [{"type": "text", "text": "structured"}]
        metadata = {
            "kind": STORY_WORKSPACE_DREAM_CONFIRMATION_METADATA_KIND
        }
        dispatch_task = dispatcher(
            THREAD_ID, ACTOR_ID, "message-1", parts, metadata
        )
        await asyncio.wait_for(entered.wait(), timeout=2)
        release.set()
        self.assertTrue(await dispatch_task)
        self.assertEqual(len(requests), 1)
        request = requests[0]
        self.assertEqual(request.thread_id, THREAD_ID)
        self.assertEqual(request.message_id, "message-1")
        self.assertTrue(request.resume)
        self.assertIs(request.message_parts, parts)
        self.assertIs(request.message_metadata, metadata)
        self.assertEqual(
            request.story_workspace_dream_context.workflow_run_id,
            RUN_ID,
        )

    async def test_dispatcher_exception_does_not_raise_to_caller(self) -> None:
        class BrokenFactory:
            def run_streaming(self, _request):
                raise RuntimeError("dispatcher broke")

        dispatcher = story_workspace_build_dream_confirmation_turn_dispatcher(
            BrokenFactory(),
            request_factory=lambda **values: SimpleNamespace(**values),
        )
        self.assertFalse(
            await dispatcher(THREAD_ID, ACTOR_ID, "message-1", [], {})
        )

    async def test_error_frame_is_not_successful_consumption(self) -> None:
        class ErrorFactory:
            async def run_streaming(self, _request):
                yield 'data: {"type":"error","errorText":"agent failed"}\n\n'

        dispatcher = story_workspace_build_dream_confirmation_turn_dispatcher(
            ErrorFactory(),
            request_factory=lambda **values: SimpleNamespace(**values),
        )
        self.assertFalse(
            await dispatcher(THREAD_ID, ACTOR_ID, "message-1", [], {})
        )

    async def test_finish_stop_without_message_final_is_not_consumed(self) -> None:
        class CancelledFactory:
            async def run_streaming(self, _request):
                yield 'data: {"type":"finish","finishReason":"stop"}\n\n'

        dispatcher = story_workspace_build_dream_confirmation_turn_dispatcher(
            CancelledFactory(),
            request_factory=lambda **values: SimpleNamespace(**values),
        )
        self.assertFalse(
            await dispatcher(THREAD_ID, ACTOR_ID, "message-1", [], {})
        )

    async def test_message_final_without_terminal_finish_is_not_consumed(self) -> None:
        class TruncatedFactory:
            async def run_streaming(self, _request):
                yield 'data: {"type":"message-final","text":"done"}\n\n'

        dispatcher = story_workspace_build_dream_confirmation_turn_dispatcher(
            TruncatedFactory(),
            request_factory=lambda **values: SimpleNamespace(**values),
        )
        self.assertFalse(
            await dispatcher(THREAD_ID, ACTOR_ID, "message-1", [], {})
        )


class StoryWorkspaceDreamConfirmationRouteTests(unittest.TestCase):
    def test_post_returns_202_camel_and_passes_only_authenticated_actor(self) -> None:
        calls = []

        class Gateway:
            async def submit_dream_confirmation(self, run_id, request, *, actor):
                calls.append((run_id, request, actor))
                return StoryWorkspaceDreamConfirmationAccepted(
                    message_id="message-1",
                    story_workspace_run_id=run_id,
                    thread_id=request.thread_id,
                    status="accepted",
                    replayed=False,
                    dispatched=True,
                    request_id="request-1",
                )

        app = FastAPI()
        app.dependency_overrides[story_workspace.get_current_user] = lambda: {
            "user_id": int(ACTOR_ID),
            "email": "dream-confirmation@example.com",
        }
        app.dependency_overrides[story_workspace.get_story_workflow_gateway] = Gateway
        app.include_router(story_workspace.router)
        with (
            patch.object(
                story_workspace,
                "get_or_create_default_workspace",
                side_effect=AssertionError("must not create workspace"),
            ) as create_workspace,
            TestClient(app) as client,
        ):
            response = client.post(
                f"/api/story-workspace/workflow-runs/{RUN_ID}/dream-confirmation",
                json=command().model_dump(mode="json", by_alias=True),
            )

        self.assertEqual(response.status_code, 202, response.text)
        self.assertEqual(calls[0][0], RUN_ID)
        self.assertEqual(calls[0][2], {"actor_id": ACTOR_ID})
        self.assertEqual(
            set(response.json()),
            {
                "messageId",
                "storyWorkspaceRunId",
                "threadId",
                "status",
                "replayed",
                "dispatched",
                "requestId",
            },
        )
        create_workspace.assert_not_called()


class StoryWorkspaceDreamConfirmationGatewayTests(unittest.IsolatedAsyncioTestCase):
    async def test_sync_chain_schedules_durable_work_without_claiming_completion(self) -> None:
        coordinator = unittest.mock.Mock()
        coordinator.schedule.return_value = True
        gateway = gateway_module.StoryWorkflowApplicationGateway(
            dream_confirmation_coordinator=coordinator,
        )
        main_thread = threading.get_ident()
        worker_threads = []
        accepted = StoryWorkspaceDreamConfirmationAccepted(
            message_id="message-1",
            story_workspace_run_id=RUN_ID,
            thread_id=THREAD_ID,
            status="accepted",
            replayed=False,
            dispatched=False,
            request_id="request-1",
        )
        dispatch = StoryWorkspaceDreamConfirmationDispatch(
            thread_id=THREAD_ID,
            actor_id=ACTOR_ID,
            message_id="message-1",
            parts=[{"type": "text", "text": "structured"}],
            metadata={
                "kind": STORY_WORKSPACE_DREAM_CONFIRMATION_METADATA_KIND
            },
        )

        def sync_chain(*_args):
            worker_threads.append(threading.get_ident())
            return StoryWorkspacePersistedDreamConfirmation(
                accepted=accepted,
                dispatch=dispatch,
            )

        with patch.object(gateway, "_submit_dream_confirmation_sync", sync_chain):
            result = await gateway.submit_dream_confirmation(
                RUN_ID,
                command(),
                actor={"actor_id": ACTOR_ID},
        )

        self.assertNotEqual(worker_threads, [main_thread])
        coordinator.schedule.assert_called_once_with(dispatch)
        self.assertFalse(result.dispatched)

        replay = accepted.model_copy(update={"replayed": True, "dispatched": True})
        with (
            patch.object(
                gateway,
                "_submit_dream_confirmation_sync",
                return_value=StoryWorkspacePersistedDreamConfirmation(
                    accepted=replay,
                    dispatch=None,
                ),
            ),
        ):
            replay_result = await gateway.submit_dream_confirmation(
                RUN_ID,
                command(),
                actor={"actor_id": ACTOR_ID},
            )
        self.assertTrue(replay_result.replayed)
        self.assertTrue(replay_result.dispatched)
        coordinator.schedule.assert_called_once()

    async def test_in_flight_replay_remains_pending_without_duplicate_schedule(self) -> None:
        coordinator = unittest.mock.Mock()
        coordinator.schedule.side_effect = [True, False]
        gateway = gateway_module.StoryWorkflowApplicationGateway(
            dream_confirmation_coordinator=coordinator,
        )
        pending = StoryWorkspaceDreamConfirmationAccepted(
            message_id="message-1",
            story_workspace_run_id=RUN_ID,
            thread_id=THREAD_ID,
            status="accepted",
            replayed=False,
            dispatched=False,
            request_id="request-1",
        )
        dispatch = StoryWorkspaceDreamConfirmationDispatch(
            thread_id=THREAD_ID,
            actor_id=ACTOR_ID,
            message_id="message-1",
            parts=[{"type": "text", "text": "structured"}],
            metadata={
                "kind": STORY_WORKSPACE_DREAM_CONFIRMATION_METADATA_KIND,
                "dispatch_status": "pending",
            },
        )
        persisted = iter([
            StoryWorkspacePersistedDreamConfirmation(
                accepted=pending,
                dispatch=dispatch,
            ),
            StoryWorkspacePersistedDreamConfirmation(
                accepted=pending.model_copy(update={"replayed": True}),
                dispatch=dispatch,
            ),
        ])
        with patch.object(
            gateway,
            "_submit_dream_confirmation_sync",
            side_effect=lambda *_args: next(persisted),
        ):
            first = await gateway.submit_dream_confirmation(
                RUN_ID,
                command(),
                actor={"actor_id": ACTOR_ID},
            )
            replay = await gateway.submit_dream_confirmation(
                RUN_ID,
                command(),
                actor={"actor_id": ACTOR_ID},
            )

        self.assertFalse(first.dispatched)
        self.assertTrue(replay.replayed)
        self.assertFalse(replay.dispatched)
        self.assertEqual(coordinator.schedule.call_count, 2)

    async def test_dispatch_exception_keeps_accepted_result(self) -> None:
        coordinator = unittest.mock.Mock()
        coordinator.schedule.side_effect = RuntimeError("scheduler unavailable")
        gateway = gateway_module.StoryWorkflowApplicationGateway(
            dream_confirmation_coordinator=coordinator,
        )
        accepted = StoryWorkspaceDreamConfirmationAccepted(
            message_id="message-1",
            story_workspace_run_id=RUN_ID,
            thread_id=THREAD_ID,
            status="accepted",
            replayed=False,
            dispatched=False,
            request_id="request-1",
        )
        persisted = StoryWorkspacePersistedDreamConfirmation(
            accepted=accepted,
            dispatch=StoryWorkspaceDreamConfirmationDispatch(
                THREAD_ID,
                ACTOR_ID,
                "message-1",
                [],
                {},
            ),
        )
        with patch.object(
            gateway,
            "_submit_dream_confirmation_sync",
            return_value=persisted,
        ):
            result = await gateway.submit_dream_confirmation(
                RUN_ID,
                command(),
                actor={"actor_id": ACTOR_ID},
            )
        self.assertEqual(result.status, "accepted")
        self.assertFalse(result.dispatched)


if __name__ == "__main__":
    unittest.main()
