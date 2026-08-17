# [Input] Consume Story Workspace guidance service, router, and temporary SQLite data.
# [Output] Verify guidance command contract, idempotent endpoint, and guide audit metadata.
# [Pos] focused test node for Dream Surface Task 3 (guidance command + ReviewEvent guide audit).
# [Sync] 2026-08-04: add Task 3 coverage (chat_message.metadata carriage, zero DDL).

"""Focused tests for the Story Workspace guidance command and idempotent endpoint.

Contract source: design_004 §5.3 / DEC-032 — guidance is persisted as a
``chat_message`` user row marked ``metadata.kind == "story-workspace-guidance"``;
the idempotency key derives the message id (``guide_<key>``); the service layer
SELECTs first: same key + same content → 202 replay, same key + different
content → 409. ``awaiting-guidance`` stays a projection state; no new RunStatus.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
import unittest.mock
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
for candidate in (str(ROOT), str(REPO_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

import database
from backend.schema import legacy_main_sqlite
from backend.tests.legacy_database_fixture import LegacyDatabaseModuleFixture
from models.workflow_run import RunStatus, WorkflowRun
from services.workflow.run_service import RunNotFound, WorkflowRunError
from routers import story_workspace
from story_workspace.contracts import (
    StoryWorkspaceExecutionProjection,
    StoryWorkspaceGuidanceCommandPayload,
    StoryWorkspaceGuidanceKind,
    StoryWorkspaceReviewEventAction,
    StoryWorkspaceSurface,
)
from services.story_workspace.guidance_service import (
    GUIDANCE_METADATA_KIND,
    StoryWorkspaceGuidanceError,
    StoryWorkspaceGuidanceService,
)


RUN_ID = "run_" + "a" * 32
THREAD_ID = "thread-guidance-1"
USER_ID = 11
ACTOR = str(USER_ID)
WORKSPACE_ID = "ws-guidance"
NOW = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)


def make_run(
    status: RunStatus,
    *,
    run_id: str = RUN_ID,
    thread_id: str | None = THREAD_ID,
) -> WorkflowRun:
    """Build a contract-valid WorkflowRun for the requested status."""

    kwargs: dict = {
        "workflow_run_id": run_id,
        "deck_plugin_id": "ink.dream.story-workflow",
        "deck_plugin_version": "1.0.0",
        "workflow_definition_ref": "deck://ink.dream.story-workflow/1.0.0/workflow.json",
        "deck_runtime_snapshot_id": "drs_" + "5" * 32,
        "status": status,
        "deck_plugin_manifest_hash": "sha256:" + "c" * 64,
        "deck_plugin_binding_id": "dpb_" + "2" * 32,
        "binding_revision": 1,
        "runtime_plugin_lock_id": "rpl_" + "1" * 32,
        "workflow_preflight_id": "pf_" + "3" * 32,
        "workspace_id": WORKSPACE_ID,
        "idempotency_key": "run-key-1",
        "input_hash": "sha256:" + "a" * 64,
        "semantic_fingerprint": "sha256:" + "b" * 64,
        "status_version": 1,
        "created_by": ACTOR,
        "created_at": NOW,
        "source_voice_thread_id": thread_id,
    }
    if status not in (RunStatus.PREFLIGHT, RunStatus.QUEUED):
        kwargs.update(
            runtime_load_receipt_id="rlr_" + "4" * 32,
            agent_session_id="as_" + "6" * 32,
            started_at=NOW,
        )
    if status is RunStatus.FAILED:
        kwargs.update(failed_step="s3", error_code="STEP_RENDER_FAILED")
    if status in (RunStatus.FAILED, RunStatus.COMPLETED, RunStatus.REJECTED):
        kwargs.update(completed_at=NOW)
    return WorkflowRun(**kwargs)


class RecordingDispatcher:
    """Test double for the same-thread new-turn injection seam."""

    def __init__(self, delivered: bool = True) -> None:
        self.delivered = delivered
        self.calls: list[dict] = []

    def __call__(
        self,
        thread_id: str,
        actor_id: str,
        message_id: str,
        parts: list,
        metadata: dict,
    ) -> bool:
        self.calls.append(
            {
                "thread_id": thread_id,
                "actor_id": actor_id,
                "message_id": message_id,
                "parts": parts,
                "metadata": metadata,
            }
        )
        return self.delivered


class GuidanceFixture:
    """Temporary database plus a guidance service wired with test doubles."""

    def __init__(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_fixture = LegacyDatabaseModuleFixture(
            database,
            Path(self.temp_dir.name) / "guidance-test.db",
        )
        self.database_fixture.start()
        db = database.get_db()
        legacy_main_sqlite.create_tables(db)
        db.execute(
            "INSERT INTO users (id, email, password_hash) VALUES (?, ?, 'hash')",
            (USER_ID, "guidance@example.com"),
        )
        db.execute(
            "INSERT INTO users (id, email, password_hash) VALUES (?, ?, 'hash')",
            (USER_ID + 1, "other@example.com"),
        )
        db.execute(
            "INSERT INTO chat_thread (id, user_id, title) VALUES (?, ?, ?)",
            (THREAD_ID, USER_ID, "Dream thread"),
        )
        db.execute(
            "INSERT INTO chat_thread (id, user_id, title) VALUES (?, ?, ?)",
            ("thread-other", USER_ID + 1, "Other thread"),
        )
        db.commit()
        db.close()
        self.runs: dict[str, WorkflowRun] = {}
        self.dispatcher = RecordingDispatcher()
        self.service = self.make_service()

    def make_service(self) -> StoryWorkspaceGuidanceService:
        return StoryWorkspaceGuidanceService(
            database.get_db(),
            run_reader=self._read_run,
            dispatcher=self.dispatcher,
        )

    def _read_run(self, run_id: str) -> WorkflowRun:
        run = self.runs.get(run_id)
        if run is None:
            raise RunNotFound()
        return run

    def add_run(self, status: RunStatus, **kwargs) -> WorkflowRun:
        run = make_run(status, **kwargs)
        self.runs[run.workflow_run_id] = run
        return run

    def guidance_messages_for(self, run_id: str) -> list[dict]:
        db = database.get_db()
        try:
            rows = db.execute(
                "SELECT id, thread_id, role, parts, metadata, created_at "
                "FROM chat_message ORDER BY created_at ASC, id ASC"
            ).fetchall()
        finally:
            db.close()
        messages = []
        for row in rows:
            metadata = json.loads(row["metadata"]) if row["metadata"] else None
            if not metadata or metadata.get("kind") != GUIDANCE_METADATA_KIND:
                continue
            if metadata.get("story_workspace_run_id") != run_id:
                continue
            messages.append(
                {
                    "id": row["id"],
                    "thread_id": row["thread_id"],
                    "role": row["role"],
                    "parts": json.loads(row["parts"]),
                    "metadata": metadata,
                }
            )
        return messages

    def close(self) -> None:
        self.database_fixture.stop()
        self.temp_dir.cleanup()


class StoryWorkspaceGuidanceServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = GuidanceFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def submit(self, run_id: str = RUN_ID, **overrides):
        body = {
            "kind": "free-text",
            "text": "第二集节奏放慢",
            "idempotency_key": "k-1",
            "actor": ACTOR,
        }
        body.update(overrides)
        command = StoryWorkspaceGuidanceCommandPayload(**body)
        return self.fixture.service.submit_guidance(run_id, command, actor_id=ACTOR)

    def test_guidance_accepted_when_run_confirmed(self):
        self.fixture.add_run(RunStatus.CONFIRMED)
        result = self.submit()
        self.assertEqual(result["status"], "accepted")
        self.assertFalse(result["replayed"])
        self.assertEqual(result["message_id"], "guide_k-1")

        messages = self.fixture.guidance_messages_for(RUN_ID)
        self.assertEqual(len(messages), 1)
        message = messages[0]
        self.assertEqual(message["role"], "user")
        self.assertEqual(message["thread_id"], THREAD_ID)
        metadata = message["metadata"]
        self.assertEqual(metadata["kind"], "story-workspace-guidance")
        self.assertEqual(metadata["story_workspace_run_id"], RUN_ID)
        self.assertEqual(metadata["actor"], ACTOR)
        self.assertTrue(metadata["request_id"])
        self.assertEqual(metadata["idempotency_key"], "k-1")
        self.assertEqual(metadata["command_kind"], "free-text")
        self.assertIn("第二集节奏放慢", metadata["text_summary"])
        # ReviewEvent action=guide audit semantics carried on the same metadata.
        self.assertEqual(metadata["review_action"], "guide")

        # Injection: handed to the same thread's runner as a new user turn.
        self.assertEqual(len(self.fixture.dispatcher.calls), 1)
        dispatch = self.fixture.dispatcher.calls[0]
        self.assertEqual(dispatch["thread_id"], THREAD_ID)
        self.assertEqual(dispatch["message_id"], "guide_k-1")
        self.assertIn("第二集节奏放慢", json.dumps(dispatch["parts"], ensure_ascii=False))

    def test_guidance_idempotent_replay(self):
        self.fixture.add_run(RunStatus.CONFIRMED)
        body = {"kind": "retry-step", "step_id": "s3",
                "idempotency_key": "k-2", "actor": ACTOR}
        r1 = self.submit(**body)
        r2 = self.submit(**body)
        self.assertEqual(r1["status"], r2["status"])
        self.assertEqual(r1["status"], "accepted")
        self.assertFalse(r1["replayed"])
        self.assertTrue(r2["replayed"])
        self.assertEqual(r1["request_id"], r2["request_id"])
        # Same key + same content → single record, no duplicate injection.
        self.assertEqual(len(self.fixture.guidance_messages_for(RUN_ID)), 1)
        self.assertEqual(len(self.fixture.dispatcher.calls), 1)

    def test_guidance_conflicting_replay_returns_409(self):
        self.fixture.add_run(RunStatus.CONFIRMED)
        self.submit(text="A", idempotency_key="k-3")
        with self.assertRaises(StoryWorkspaceGuidanceError) as ctx:
            self.submit(text="B", idempotency_key="k-3")
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(ctx.exception.code, "IDEMPOTENCY_CONFLICT")
        # The original record is preserved; the conflict is observable.
        messages = self.fixture.guidance_messages_for(RUN_ID)
        self.assertEqual(len(messages), 1)
        self.assertIn("A", messages[0]["metadata"]["text_summary"])
        self.assertEqual(len(self.fixture.dispatcher.calls), 1)

    def test_concurrent_database_identity_conflict_maps_to_guidance_409(self):
        self.fixture.add_run(RunStatus.CONFIRMED)
        with unittest.mock.patch.object(
            database,
            "save_chat_message",
            side_effect=database.ChatMessageIdentityConflict("guide_k-race"),
        ):
            with self.assertRaises(StoryWorkspaceGuidanceError) as raised:
                self.submit(idempotency_key="k-race")
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.code, "IDEMPOTENCY_CONFLICT")
        self.assertEqual(self.fixture.dispatcher.calls, [])

    def test_guidance_rejected_when_not_confirmed(self):
        self.fixture.add_run(RunStatus.PENDING_REVIEW)
        with self.assertRaises(StoryWorkspaceGuidanceError) as ctx:
            self.submit(idempotency_key="k-4")
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(ctx.exception.code, "WORKFLOW_RUN_NOT_GUIDABLE")
        self.assertEqual(self.fixture.guidance_messages_for(RUN_ID), [])
        self.assertEqual(self.fixture.dispatcher.calls, [])

    def test_guidance_rejected_when_run_completed(self):
        self.fixture.add_run(RunStatus.COMPLETED)
        with self.assertRaises(StoryWorkspaceGuidanceError) as ctx:
            self.submit(idempotency_key="k-5")
        self.assertEqual(ctx.exception.code, "WORKFLOW_RUN_NOT_GUIDABLE")

    def test_guidance_rejected_without_source_thread(self):
        self.fixture.add_run(RunStatus.CONFIRMED, thread_id=None)
        with self.assertRaises(StoryWorkspaceGuidanceError) as ctx:
            self.submit(idempotency_key="k-6")
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(ctx.exception.code, "WORKFLOW_RUN_NOT_GUIDABLE")

    def test_guidance_rejected_when_thread_not_owned(self):
        self.fixture.add_run(RunStatus.CONFIRMED, thread_id="thread-other")
        with self.assertRaises(StoryWorkspaceGuidanceError) as ctx:
            self.submit(idempotency_key="k-7")
        self.assertEqual(ctx.exception.status_code, 409)

    def test_guidance_rejected_when_actor_mismatch(self):
        self.fixture.add_run(RunStatus.CONFIRMED)
        with self.assertRaises(StoryWorkspaceGuidanceError) as ctx:
            self.fixture.service.submit_guidance(
                RUN_ID,
                StoryWorkspaceGuidanceCommandPayload(
                    kind="free-text",
                    text="x",
                    idempotency_key="k-8",
                    actor="someone-else",
                ),
                actor_id=ACTOR,
            )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.code, "WORKFLOW_PERMISSION_DENIED")

    def test_guidance_retry_step_accepted(self):
        self.fixture.add_run(RunStatus.CONFIRMED)
        result = self.submit(
            kind="retry-step", step_id="s3", text=None, idempotency_key="k-9"
        )
        self.assertEqual(result["status"], "accepted")
        message = self.fixture.guidance_messages_for(RUN_ID)[0]
        self.assertEqual(message["metadata"]["command_kind"], "retry-step")
        self.assertEqual(message["metadata"]["step_id"], "s3")
        self.assertIn("s3", message["parts"][0]["text"])

    def test_guidance_dispatch_failure_still_accepted(self):
        self.fixture.dispatcher.delivered = False
        self.fixture.add_run(RunStatus.CONFIRMED)
        result = self.submit(idempotency_key="k-10")
        # 202 semantics: persisted and queued even when no live runner turn
        # could be started (mid-turn injection channel does not exist, R5).
        self.assertEqual(result["status"], "accepted")
        self.assertFalse(result["dispatched"])
        self.assertEqual(len(self.fixture.guidance_messages_for(RUN_ID)), 1)


class StoryWorkspaceGuidanceContractTests(unittest.TestCase):
    def test_free_text_requires_text(self):
        with self.assertRaises(ValidationError):
            StoryWorkspaceGuidanceCommandPayload(
                kind="free-text", idempotency_key="k", actor=ACTOR
            )

    def test_retry_step_requires_step_id(self):
        with self.assertRaises(ValidationError):
            StoryWorkspaceGuidanceCommandPayload(
                kind="retry-step", idempotency_key="k", actor=ACTOR
            )

    def test_kind_enum_values(self):
        self.assertEqual(StoryWorkspaceGuidanceKind.RETRY_STEP.value, "retry-step")
        self.assertEqual(StoryWorkspaceGuidanceKind.FREE_TEXT.value, "free-text")

    def test_review_event_action_includes_guide(self):
        # ReviewEvent action enum extension (contract layer only, no DDL).
        self.assertEqual(StoryWorkspaceReviewEventAction.GUIDE.value, "guide")

    def test_surface_value_object(self):
        surface = StoryWorkspaceSurface(
            name="dream",
            protocol_dir=".dream",
            entry_route="/story-workspace/dream",
        )
        self.assertEqual(surface.protocol_dir, ".dream")

    def test_execution_projection_shape(self):
        projection = StoryWorkspaceExecutionProjection(
            run_id=RUN_ID,
            phase="confirmed",
            steps=[{"step_id": "s3", "status": "blocked"}],
            assets_ref=None,
            events=[{"type": "story-workspace.execution.guidance-submitted"}],
        )
        self.assertEqual(projection.run_id, RUN_ID)
        self.assertEqual(projection.phase, "confirmed")
        self.assertEqual(len(projection.steps), 1)


class _RealServiceGateway:
    """Gateway test double backed by the real guidance service."""

    def __init__(self, fixture: GuidanceFixture) -> None:
        self.fixture = fixture

    async def submit_guidance(self, workflow_run_id, request, *, actor):
        from services.errors.error_registry import ApiRouteError

        db = database.get_db()
        try:
            service = StoryWorkspaceGuidanceService(
                db,
                run_reader=self.fixture._read_run,
                dispatcher=self.fixture.dispatcher,
            )
            return service.submit_guidance(
                workflow_run_id, request, actor_id=actor["actor_id"]
            )
        except StoryWorkspaceGuidanceError as exc:
            raise ApiRouteError(exc.code, status_code=exc.status_code) from exc
        except WorkflowRunError as exc:
            status = 404 if exc.code == "WORKFLOW_RUN_NOT_FOUND" else 409
            raise ApiRouteError("AGENT_EXECUTION_FAILED", status_code=status) from exc
        finally:
            db.close()


class StoryWorkspaceGuidanceRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = GuidanceFixture()
        app = FastAPI()
        app.dependency_overrides[story_workspace.get_current_user] = lambda: {
            "user_id": USER_ID,
            "workspace_id": WORKSPACE_ID,
            "role": "user",
        }
        app.dependency_overrides[story_workspace.get_story_workflow_run_service] = (
            lambda: _RealServiceGateway(self.fixture)
        )
        app.include_router(story_workspace.router)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        self.fixture.close()

    def post_guidance(self, run_id: str = RUN_ID, **overrides):
        body = {
            "kind": "free-text",
            "text": "第二集节奏放慢",
            "idempotency_key": "k-1",
            "actor": ACTOR,
        }
        body.update(overrides)
        return self.client.post(
            f"/api/story-workspace/runs/{run_id}/guidance", json=body
        )

    def test_post_guidance_accepted_returns_202(self):
        self.fixture.add_run(RunStatus.CONFIRMED)
        resp = self.post_guidance()
        self.assertEqual(resp.status_code, 202)
        payload = resp.json()
        self.assertEqual(payload["status"], "accepted")
        self.assertEqual(payload["message_id"], "guide_k-1")
        self.assertTrue(payload["request_id"])
        self.assertFalse(payload["replayed"])
        self.assertEqual(len(self.fixture.guidance_messages_for(RUN_ID)), 1)

    def test_post_guidance_idempotent_replay_returns_202(self):
        self.fixture.add_run(RunStatus.CONFIRMED)
        body = {"kind": "retry-step", "step_id": "s3",
                "idempotency_key": "k-2", "actor": ACTOR}
        r1 = self.post_guidance(**body)
        r2 = self.post_guidance(**body)
        self.assertEqual(r1.status_code, 202)
        self.assertEqual(r2.status_code, 202)
        self.assertTrue(r2.json()["replayed"])
        self.assertEqual(len(self.fixture.guidance_messages_for(RUN_ID)), 1)

    def test_post_guidance_conflicting_replay_returns_409(self):
        self.fixture.add_run(RunStatus.CONFIRMED)
        self.post_guidance(text="A", idempotency_key="k-3")
        resp = self.post_guidance(text="B", idempotency_key="k-3")
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["error"]["code"], "IDEMPOTENCY_CONFLICT")

    def test_post_guidance_not_confirmed_returns_409(self):
        self.fixture.add_run(RunStatus.PENDING_REVIEW)
        resp = self.post_guidance(idempotency_key="k-4")
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["error"]["code"], "WORKFLOW_RUN_NOT_GUIDABLE")

    def test_post_guidance_unknown_run_returns_404(self):
        resp = self.post_guidance(run_id="run_" + "f" * 32)
        self.assertEqual(resp.status_code, 404)

    def test_post_guidance_validation_error_returns_422(self):
        self.fixture.add_run(RunStatus.CONFIRMED)
        resp = self.client.post(
            f"/api/story-workspace/runs/{RUN_ID}/guidance",
            json={"kind": "free-text", "idempotency_key": "k-x", "actor": ACTOR},
        )
        self.assertEqual(resp.status_code, 422)

    def test_post_guidance_actor_mismatch_returns_403(self):
        self.fixture.add_run(RunStatus.CONFIRMED)
        resp = self.post_guidance(actor="someone-else", idempotency_key="k-8")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["error"]["code"], "WORKFLOW_PERMISSION_DENIED")


if __name__ == "__main__":
    unittest.main()
