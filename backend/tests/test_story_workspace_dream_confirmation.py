"""Focused tests for the one-shot Dream confirmation continuation."""

from __future__ import annotations

import asyncio
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
from services.story_workspace.dream_confirmation_service import (
    DREAM_CONFIRMATION_METADATA_KIND,
    DreamConfirmationDispatch,
    PersistedDreamConfirmation,
    StoryWorkspaceDreamConfirmationError,
    StoryWorkspaceDreamConfirmationService,
    build_thread_turn_dispatcher,
    dream_confirmation_message_id,
)
from story_workspace.contracts import (
    StoryWorkspaceDreamConfirmationAccepted,
    StoryWorkspaceDreamConfirmationCommand,
    StoryWorkspaceDreamFilesResponse,
    StoryWorkspaceDreamSourceResponse,
    StoryWorkspaceDreamStage,
    StoryWorkspaceDreamStageResponse,
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
        db.commit()
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
            },
        )
        self.assertEqual(metadata["kind"], DREAM_CONFIRMATION_METADATA_KIND)
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
        self.assertEqual(row["id"], persisted.accepted.message_id)
        self.assertEqual(
            row["id"],
            dream_confirmation_message_id(ACTOR_ID, RUN_ID, "swc_test-key"),
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
            DREAM_CONFIRMATION_METADATA_KIND,
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

    def test_same_key_replay_and_conflict(self) -> None:
        first = self.submit()
        replay = self.submit()
        self.assertFalse(first.accepted.replayed)
        self.assertTrue(replay.accepted.replayed)
        self.assertEqual(first.accepted.request_id, replay.accepted.request_id)
        self.assertIsNone(replay.dispatch)
        self.assertEqual(len(self.fixture.rows()), 1)

        with self.assertRaises(StoryWorkspaceDreamConfirmationError) as raised:
            self.submit(edits=[], idempotencyKey="swc_test-key")
        self.assertEqual(
            (raised.exception.code, raised.exception.status_code),
            ("IDEMPOTENCY_CONFLICT", 409),
        )
        self.assertEqual(len(self.fixture.rows()), 1)

    def test_actor_run_and_key_are_isolated_in_message_id(self) -> None:
        first = dream_confirmation_message_id(ACTOR_ID, RUN_ID, "swc_same")
        self.assertNotEqual(
            first,
            dream_confirmation_message_id(ACTOR_ID, RUN_ID, "swc_different"),
        )
        self.assertNotEqual(
            first,
            dream_confirmation_message_id(OTHER_ACTOR_ID, RUN_ID, "swc_same"),
        )
        self.assertNotEqual(
            first,
            dream_confirmation_message_id(ACTOR_ID, OTHER_RUN_ID, "swc_same"),
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
        self.assertEqual(sum(r.dispatch is not None for r in results), 1)
        self.assertEqual(len(self.fixture.rows()), 1)


class StoryWorkspaceDreamConfirmationDispatcherTests(unittest.IsolatedAsyncioTestCase):
    async def test_running_thread_is_queued_on_factory_lock_and_uses_same_turn_data(self) -> None:
        release = asyncio.Event()
        entered = asyncio.Event()
        requests = []

        class FakeFactory:
            async def run_streaming(self, request):
                requests.append(request)
                entered.set()
                await release.wait()
                yield "done"

        dispatcher = build_thread_turn_dispatcher(
            FakeFactory(),
            request_factory=lambda **values: SimpleNamespace(**values),
        )
        parts = [{"type": "text", "text": "structured"}]
        metadata = {"kind": DREAM_CONFIRMATION_METADATA_KIND}
        dispatched = dispatcher(THREAD_ID, ACTOR_ID, "message-1", parts, metadata)
        self.assertTrue(dispatched)
        await asyncio.wait_for(entered.wait(), timeout=2)
        release.set()
        await asyncio.sleep(0)
        self.assertEqual(len(requests), 1)
        request = requests[0]
        self.assertEqual(request.thread_id, THREAD_ID)
        self.assertEqual(request.message_id, "message-1")
        self.assertTrue(request.resume)
        self.assertIs(request.message_parts, parts)
        self.assertIs(request.message_metadata, metadata)

    async def test_dispatcher_exception_does_not_raise_to_caller(self) -> None:
        class BrokenFactory:
            def run_streaming(self, _request):
                raise RuntimeError("dispatcher broke")

        dispatcher = build_thread_turn_dispatcher(
            BrokenFactory(),
            request_factory=lambda **values: SimpleNamespace(**values),
        )
        self.assertFalse(dispatcher(THREAD_ID, ACTOR_ID, "message-1", [], {}))


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
    async def test_sync_chain_is_offloaded_and_only_new_insert_is_dispatched(self) -> None:
        gateway = gateway_module.StoryWorkflowApplicationGateway()
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
        dispatch = DreamConfirmationDispatch(
            thread_id=THREAD_ID,
            actor_id=ACTOR_ID,
            message_id="message-1",
            parts=[{"type": "text", "text": "structured"}],
            metadata={"kind": DREAM_CONFIRMATION_METADATA_KIND},
        )

        def sync_chain(*_args):
            worker_threads.append(threading.get_ident())
            return PersistedDreamConfirmation(accepted=accepted, dispatch=dispatch)

        dispatcher_calls = []

        def dispatcher(*args):
            dispatcher_calls.append((threading.get_ident(), args))
            return True

        with (
            patch.object(gateway, "_submit_dream_confirmation_sync", sync_chain),
            patch.object(
                gateway_module,
                "build_dream_confirmation_dispatcher",
                return_value=dispatcher,
            ),
        ):
            result = await gateway.submit_dream_confirmation(
                RUN_ID,
                command(),
                actor={"actor_id": ACTOR_ID},
            )

        self.assertNotEqual(worker_threads, [main_thread])
        self.assertEqual(dispatcher_calls[0][0], main_thread)
        self.assertTrue(result.dispatched)

        replay = accepted.model_copy(update={"replayed": True})
        with (
            patch.object(
                gateway,
                "_submit_dream_confirmation_sync",
                return_value=PersistedDreamConfirmation(
                    accepted=replay,
                    dispatch=None,
                ),
            ),
            patch.object(
                gateway_module,
                "build_dream_confirmation_dispatcher",
            ) as build_dispatcher,
        ):
            replay_result = await gateway.submit_dream_confirmation(
                RUN_ID,
                command(),
                actor={"actor_id": ACTOR_ID},
            )
        self.assertTrue(replay_result.replayed)
        self.assertFalse(replay_result.dispatched)
        build_dispatcher.assert_not_called()

    async def test_dispatch_exception_keeps_accepted_result(self) -> None:
        gateway = gateway_module.StoryWorkflowApplicationGateway()
        accepted = StoryWorkspaceDreamConfirmationAccepted(
            message_id="message-1",
            story_workspace_run_id=RUN_ID,
            thread_id=THREAD_ID,
            status="accepted",
            replayed=False,
            dispatched=False,
            request_id="request-1",
        )
        persisted = PersistedDreamConfirmation(
            accepted=accepted,
            dispatch=DreamConfirmationDispatch(
                THREAD_ID,
                ACTOR_ID,
                "message-1",
                [],
                {},
            ),
        )
        with (
            patch.object(
                gateway,
                "_submit_dream_confirmation_sync",
                return_value=persisted,
            ),
            patch.object(
                gateway_module,
                "build_dream_confirmation_dispatcher",
                side_effect=RuntimeError("dispatcher unavailable"),
            ),
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
