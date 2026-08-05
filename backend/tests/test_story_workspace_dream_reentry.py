"""Durable, actor-scoped Dream re-entry projection tests."""

from __future__ import annotations

import json
import sqlite3
import sys
import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from routers import story_workspace
from services.errors.error_registry import ApiRouteError
from story_workspace.contracts import StoryWorkspaceDreamStage


ACTOR_ID = "7"
WORKSPACE_ID = "workspace-1"


def run_id(number: int) -> str:
    return "run_" + f"{number:032x}"


@dataclass(frozen=True)
class _Stage:
    revision: int


@dataclass(frozen=True)
class _Projection:
    stages: dict[StoryWorkspaceDreamStage, _Stage]
    stage_activity_at: datetime | None = None


def _create_schema(db: sqlite3.Connection) -> None:
    db.executescript(
        """
        CREATE TABLE story_workspace_workspaces (id TEXT PRIMARY KEY, owner_id INTEGER);
        CREATE TABLE decks (id TEXT PRIMARY KEY, name TEXT, owner_id INTEGER, enabled INTEGER);
        CREATE TABLE workflow_preflights (
          workflow_preflight_id TEXT PRIMARY KEY,
          deck_id TEXT,
          workspace_id TEXT,
          creator_id TEXT,
          created_by TEXT,
          deck_plugin_id TEXT,
          deck_plugin_version TEXT,
          runtime_plugin_lock_id TEXT
          ,binding_revision INTEGER
          ,deck_runtime_snapshot_id TEXT
        );
        CREATE TABLE deck_plugin_bindings (
          deck_plugin_binding_id TEXT PRIMARY KEY,
          deck_id TEXT,
          workspace_id TEXT,
          creator_id TEXT,
          deck_plugin_id TEXT,
          deck_plugin_version TEXT,
          binding_revision INTEGER
        );
        CREATE TABLE workflow_runs (
          id TEXT PRIMARY KEY,
          workspace_id TEXT,
          deck_plugin_id TEXT,
          deck_plugin_version TEXT,
          workflow_definition_ref TEXT,
          deck_runtime_snapshot_id TEXT,
          deck_plugin_manifest_hash TEXT,
          deck_plugin_binding_id TEXT,
          binding_revision INTEGER,
          runtime_plugin_lock_id TEXT,
          workflow_preflight_id TEXT,
          source_voice_thread_id TEXT,
          source_message_id TEXT,
          created_by TEXT,
          created_at TEXT
        );
        CREATE TABLE deck_plugin_releases (
          deck_plugin_id TEXT,
          deck_plugin_version TEXT,
          workflow_definition_ref TEXT,
          manifest_hash TEXT,
          manifest_json TEXT
        );
        CREATE TABLE deck_runtime_plugin_locks (
          id TEXT PRIMARY KEY,
          deck_plugin_id TEXT,
          deck_plugin_version TEXT,
          deck_plugin_manifest_hash TEXT
        );
        CREATE TABLE deck_runtime_snapshots (
          deck_runtime_snapshot_id TEXT PRIMARY KEY,
          deck_id TEXT,
          deck_plugin_binding_id TEXT,
          binding_revision INTEGER
        );
        CREATE TABLE chat_thread (
          id TEXT PRIMARY KEY,
          user_id INTEGER,
          deck_id TEXT,
          voice_id TEXT,
          updated_at TEXT
        );
        CREATE TABLE chat_message (
          id TEXT PRIMARY KEY,
          thread_id TEXT,
          role TEXT,
          parts TEXT,
          metadata TEXT,
          created_at TEXT
        );
        """
    )


def _launch_metadata(
    *,
    run: str,
    thread: str,
    deck: str,
    goal: str,
    actor: str = ACTOR_ID,
) -> str:
    return json.dumps({
        "kind": "story-workspace-dream-launch",
        "actorId": actor,
        "workspaceId": WORKSPACE_ID,
        "deckId": deck,
        "workflowRunId": run,
        "threadId": thread,
        "goal": goal,
        "dreamContext": {
            "workflow_run_id": run,
            "thread_id": thread,
            "deck_id": deck,
            "deck_plugin_id": "plugin-1",
            "deck_plugin_version": "1.0.0",
            "deck_plugin_binding_id": "binding-PLACEHOLDER",
            "binding_revision": 1,
            "deck_runtime_snapshot_id": "snapshot-1",
            "runtime_plugin_lock_id": "lock-1",
        },
    })


def _confirmation_metadata(*, run: str, thread: str, dispatched: bool) -> str:
    return json.dumps({
        "kind": "story-workspace-dream-confirmation",
        "actor": ACTOR_ID,
        "thread_id": thread,
        "story_workspace_run_id": run,
        "dispatch_status": "dispatched" if dispatched else "pending",
    })


class StoryWorkspaceDreamReentryServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        _create_schema(self.db)
        self.db.executemany(
            "INSERT INTO story_workspace_workspaces (id, owner_id) VALUES (?, ?)",
            [(WORKSPACE_ID, int(ACTOR_ID)), ("workspace-other", 8)],
        )
        self.db.executemany(
            "INSERT INTO decks (id, name, owner_id, enabled) VALUES (?, ?, ?, 1)",
            [("deck-1", "甲板一", int(ACTOR_ID)), ("deck-other", "他人甲板", 8)],
        )
        self.projections: dict[str, _Projection] = {}
        self.live_threads: set[str] = set()

    def tearDown(self) -> None:
        self.db.close()

    def _add_run(
        self,
        number: int,
        *,
        complete: bool,
        confirmation: str | None = None,
        created_at: str = "2026-08-05T10:00:00+00:00",
        updated_at: str = "2026-08-05T10:00:00+00:00",
        actor: str = ACTOR_ID,
        workspace: str = WORKSPACE_ID,
        deck: str = "deck-1",
        goal: str | None = None,
        include_goal: bool = True,
        thread_deck: str | None = None,
        metadata_kind: str = "story-workspace-dream-launch",
        workflow_definition_ref: str = "deck://ink.dream/story/1.0.0/workflow.json",
        preflight_binding_revision: int = 1,
        preflight_snapshot_id: str | None = None,
        preflight_lock_id: str | None = None,
        stage_activity_at: datetime | None = None,
        dream_release: bool = True,
        real_launch_metadata: bool = False,
        agent_id: str | None = None,
    ) -> str:
        value = run_id(number)
        thread = f"thread-{number}"
        preflight = f"pf-{number}"
        binding = f"binding-{number}"
        source = f"source-{number}"
        plugin = f"plugin-{number}"
        snapshot = f"snapshot-{number}"
        lock = f"lock-{number}"
        manifest = f"manifest-{number}"
        preflight_snapshot_id = preflight_snapshot_id or snapshot
        preflight_lock_id = preflight_lock_id or lock
        self.db.execute(
            "INSERT INTO workflow_preflights VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                preflight, deck, workspace, actor, actor, plugin, "1.0.0",
                preflight_lock_id, preflight_binding_revision, preflight_snapshot_id,
            ),
        )
        self.db.execute(
            "INSERT INTO deck_plugin_bindings VALUES (?, ?, ?, ?, ?, ?, ?)",
            (binding, deck, workspace, actor, plugin, "1.0.0", 1),
        )
        self.db.execute(
            "INSERT INTO workflow_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                value, workspace, plugin, "1.0.0", workflow_definition_ref,
                snapshot, manifest, binding, 1, lock, preflight,
                thread, source, actor, created_at,
            ),
        )
        self.db.execute(
            "INSERT INTO deck_plugin_releases VALUES (?, ?, ?, ?, ?)",
            (
                plugin,
                "1.0.0",
                workflow_definition_ref,
                manifest,
                json.dumps({
                    "capabilities": ["story.workspace.propose"] if dream_release else ["chat.general"],
                    "runtime": {"claude_code_plugins": [{
                        "capability_bindings": ["story.workspace.propose"] if dream_release else ["chat.general"],
                    }]},
                }),
            ),
        )
        self.db.execute(
            "INSERT INTO deck_runtime_plugin_locks VALUES (?, ?, ?, ?)",
            (lock, plugin, "1.0.0", manifest),
        )
        self.db.execute(
            "INSERT INTO deck_runtime_snapshots VALUES (?, ?, ?, ?)",
            (snapshot, deck, binding, 1),
        )
        self.db.execute(
            "INSERT INTO chat_thread VALUES (?, ?, ?, ?, ?)",
            (thread, int(actor), thread_deck or deck, agent_id, updated_at),
        )
        metadata = json.loads(_launch_metadata(
            run=value,
            thread=thread,
            deck=deck,
            goal=goal or f"创作目标 {number}",
            actor=actor,
        ))
        if not include_goal:
            metadata.pop("goal")
        metadata["kind"] = metadata_kind
        metadata["dreamContext"]["deck_plugin_binding_id"] = binding
        metadata["dreamContext"]["deck_plugin_id"] = plugin
        metadata["dreamContext"]["deck_runtime_snapshot_id"] = snapshot
        metadata["dreamContext"]["runtime_plugin_lock_id"] = lock
        if real_launch_metadata:
            metadata.update({
                "schemaVersion": "story-workspace-dream-launch/v1",
                "visibility": "system-hidden",
                "agentId": agent_id,
                "idempotencyKey": f"dream-reentry-{number}",
                "requestFingerprint": "sha256:" + "a" * 64,
                "dispatchStatus": "dispatched",
            })
            metadata["dreamContext"]["agent_id"] = agent_id
        self.db.execute(
            "INSERT INTO chat_message VALUES (?, ?, 'user', '[]', ?, ?)",
            (source, thread, json.dumps(metadata), created_at),
        )
        if confirmation is not None:
            self.db.execute(
                "INSERT INTO chat_message VALUES (?, ?, 'user', '[]', ?, ?)",
                (
                    f"confirmation-{number}", thread,
                    _confirmation_metadata(
                        run=value,
                        thread=thread,
                        dispatched=confirmation == "dispatched",
                    ),
                    updated_at,
                ),
            )
        stages = {}
        if complete:
            stages = {
                stage: _Stage(index)
                for index, stage in enumerate(StoryWorkspaceDreamStage, start=1)
            }
        self.projections[value] = _Projection(
            stages=stages,
            stage_activity_at=stage_activity_at,
        )
        self.db.commit()
        return value

    def _source_metadata(self, number: int) -> dict[str, object]:
        row = self.db.execute(
            "SELECT metadata FROM chat_message WHERE id = ?",
            (f"source-{number}",),
        ).fetchone()
        self.assertIsNotNone(row)
        return json.loads(row["metadata"])

    def _replace_source_metadata(
        self,
        number: int,
        metadata: dict[str, object],
    ) -> None:
        self.db.execute(
            "UPDATE chat_message SET metadata = ? WHERE id = ?",
            (json.dumps(metadata), f"source-{number}"),
        )
        self.db.commit()

    def _service(self, loader=None):
        from services.story_workspace.dream_reentry_service import (
            StoryWorkspaceDreamReentryService,
        )

        return StoryWorkspaceDreamReentryService(
            db_factory=lambda: self.db,
            dream_files_loader=loader or (
                lambda row, *_args: self.projections[str(row["run_id"])]
            ),
            live_turn_lookup=lambda thread: thread in self.live_threads,
            close_connections=False,
        )

    def test_projects_exact_lifecycle_groups_and_stable_order(self) -> None:
        generating_new = self._add_run(1, complete=False, updated_at="2026-08-05T14:00:00+00:00")
        generating_old = self._add_run(2, complete=True, updated_at="2026-08-05T13:00:00+00:00")
        self.live_threads.add("thread-2")
        waiting = self._add_run(3, complete=True, updated_at="2026-08-05T12:00:00+00:00")
        continuing = self._add_run(4, complete=True, confirmation="accepted", updated_at="2026-08-05T11:00:00+00:00")
        recent = self._add_run(5, complete=True, confirmation="dispatched", updated_at="2026-08-05T15:00:00+00:00")

        response = self._service().list_dream_runs(actor={"actor_id": ACTOR_ID})

        self.assertEqual(
            [item.story_workspace_run_id for item in response.runs],
            [generating_new, generating_old, waiting, continuing, recent],
        )
        self.assertEqual(
            [item.lifecycle.value for item in response.runs],
            ["generating", "generating", "waiting_confirmation", "continuing", "recent"],
        )
        self.assertEqual(
            [item.group for item in response.runs],
            ["in_progress", "in_progress", "in_progress", "in_progress", "recent"],
        )
        self.assertTrue(all(item.sort_key for item in response.runs))

    def test_projects_the_creation_goal_prefix_as_the_run_title(self) -> None:
        goal = "创作一个雨夜车站重逢的短篇故事，人物关系克制，结尾保留悬念。" * 3
        value = self._add_run(6, complete=False, goal=goal)

        response = self._service().list_dream_runs(actor={"actor_id": ACTOR_ID})

        self.assertEqual(response.runs[0].story_workspace_run_id, value)
        self.assertEqual(response.runs[0].goal_prefix, goal[:80])

    def test_legacy_launch_without_goal_remains_visible_with_deck_fallback(self) -> None:
        value = self._add_run(7, complete=False, include_goal=False)

        response = self._service().list_dream_runs(actor={"actor_id": ACTOR_ID})

        self.assertEqual(response.runs[0].story_workspace_run_id, value)
        self.assertEqual(response.runs[0].goal_prefix, "甲板一")

    def test_real_launch_agent_provenance_and_legacy_missing_fields_are_visible(self) -> None:
        legacy = self._add_run(8, complete=False)
        real = self._add_run(
            9,
            complete=False,
            real_launch_metadata=True,
            agent_id="voice-dream-1",
        )
        real_without_agent = self._add_run(
            10,
            complete=False,
            real_launch_metadata=True,
        )
        statements: list[str] = []
        self.db.set_trace_callback(statements.append)

        response = self._service().list_dream_runs(actor={"actor_id": ACTOR_ID})

        self.assertEqual(
            {item.story_workspace_run_id for item in response.runs},
            {legacy, real, real_without_agent},
        )
        authorized = next(
            statement for statement in statements
            if "FROM workflow_runs AS run" in statement
        )
        self.assertIn("thread.voice_id AS thread_voice_id", authorized)

    def test_agent_provenance_is_paired_and_matches_the_authorized_thread(self) -> None:
        valid = self._add_run(
            170,
            complete=False,
            real_launch_metadata=True,
            agent_id="voice-valid",
        )
        mutations = {
            171: lambda value: value["dreamContext"].__setitem__("agent_id", "voice-other"),
            172: lambda value: value.__setitem__("agentId", "voice-other"),
            173: lambda value: value.pop("agentId"),
            174: lambda value: value["dreamContext"].pop("agent_id"),
        }
        for number, mutate in mutations.items():
            self._add_run(
                number,
                complete=False,
                real_launch_metadata=True,
                agent_id="voice-bound",
            )
            metadata = self._source_metadata(number)
            mutate(metadata)
            self._replace_source_metadata(number, metadata)

        response = self._service().list_dream_runs(actor={"actor_id": ACTOR_ID})

        self.assertEqual(
            [item.story_workspace_run_id for item in response.runs],
            [valid],
        )

    def test_dream_context_keeps_nine_required_fields_and_rejects_unknown_extras(self) -> None:
        required = (
            "workflow_run_id",
            "thread_id",
            "deck_id",
            "deck_plugin_id",
            "deck_plugin_version",
            "deck_plugin_binding_id",
            "binding_revision",
            "deck_runtime_snapshot_id",
            "runtime_plugin_lock_id",
        )
        visible = self._add_run(
            180,
            complete=False,
            real_launch_metadata=True,
            agent_id="voice-visible",
        )
        for offset, field in enumerate(required, start=181):
            self._add_run(
                offset,
                complete=False,
                real_launch_metadata=True,
                agent_id=f"voice-{offset}",
            )
            metadata = self._source_metadata(offset)
            metadata["dreamContext"].pop(field)
            self._replace_source_metadata(offset, metadata)
        self._add_run(190, complete=False, real_launch_metadata=True)
        context_extra = self._source_metadata(190)
        context_extra["dreamContext"]["unexpected"] = "forged"
        self._replace_source_metadata(190, context_extra)
        self._add_run(191, complete=False, real_launch_metadata=True)
        top_level_extra = self._source_metadata(191)
        top_level_extra["unexpected"] = "forged"
        self._replace_source_metadata(191, top_level_extra)

        response = self._service().list_dream_runs(actor={"actor_id": ACTOR_ID})

        self.assertEqual(
            [item.story_workspace_run_id for item in response.runs],
            [visible],
        )

    def test_fails_closed_for_foreign_or_forged_binding_rows(self) -> None:
        visible = self._add_run(10, complete=False)
        self._add_run(11, complete=False, actor="8", workspace="workspace-other", deck="deck-other")
        self._add_run(12, complete=False, thread_deck="deck-other")
        self._add_run(13, complete=False, metadata_kind="ordinary-chat")

        response = self._service().list_dream_runs(actor={"actor_id": ACTOR_ID})

        self.assertEqual([item.story_workspace_run_id for item in response.runs], [visible])

    def test_sql_rejects_non_dream_or_inconsistent_provenance_edges(self) -> None:
        visible = self._add_run(30, complete=False)
        wrong_workflow = self._add_run(31, complete=False)
        wrong_revision = self._add_run(32, complete=False)
        wrong_snapshot = self._add_run(33, complete=False)
        wrong_lock = self._add_run(34, complete=False)
        wrong_context = self._add_run(35, complete=False)
        self.db.execute(
            "UPDATE workflow_runs SET workflow_definition_ref = 'deck://other/workflow.json' WHERE id = ?",
            (wrong_workflow,),
        )
        self.db.execute(
            "UPDATE workflow_preflights SET binding_revision = 2 WHERE workflow_preflight_id = 'pf-32'"
        )
        self.db.execute(
            "UPDATE workflow_preflights SET deck_runtime_snapshot_id = 'snapshot-other' WHERE workflow_preflight_id = 'pf-33'"
        )
        self.db.execute(
            "UPDATE workflow_preflights SET runtime_plugin_lock_id = 'lock-other' WHERE workflow_preflight_id = 'pf-34'"
        )
        metadata = json.loads(self.db.execute(
            "SELECT metadata FROM chat_message WHERE id = 'source-35'"
        ).fetchone()[0])
        metadata["dreamContext"]["runtime_plugin_lock_id"] = "lock-other"
        self.db.execute(
            "UPDATE chat_message SET metadata = ? WHERE id = 'source-35'",
            (json.dumps(metadata),),
        )
        self.db.commit()

        response = self._service().list_dream_runs(actor={"actor_id": ACTOR_ID})

        self.assertEqual([item.story_workspace_run_id for item in response.runs], [visible])

    def test_release_without_dream_surface_or_capability_is_never_projected(self) -> None:
        visible = self._add_run(36, complete=False)
        self._add_run(37, complete=False, dream_release=False)

        response = self._service().list_dream_runs(actor={"actor_id": ACTOR_ID})

        self.assertEqual([item.story_workspace_run_id for item in response.runs], [visible])

    def test_collection_keeps_all_in_progress_and_only_twenty_most_recent_runs(self) -> None:
        oldest_in_progress = self._add_run(
            60,
            complete=False,
            created_at="2026-08-01T00:00:00+00:00",
            updated_at="2026-08-01T00:00:00+00:00",
        )
        for number in range(61, 162):
            self._add_run(
                number,
                complete=True,
                confirmation="dispatched",
                created_at=f"2026-08-05T{number % 24:02d}:00:00+00:00",
                updated_at=f"2026-08-05T{number % 24:02d}:00:00+00:00",
            )

        loader_calls: list[tuple[str, int]] = []

        def loader(row, _actor, db):
            value = str(row["run_id"])
            loader_calls.append((value, id(db)))
            return self.projections[value]

        statements: list[str] = []
        self.db.set_trace_callback(statements.append)
        response = self._service(loader=loader).list_dream_runs(actor={"actor_id": ACTOR_ID})

        self.assertEqual(response.runs[0].story_workspace_run_id, oldest_in_progress)
        self.assertEqual(len(response.runs), 21)
        self.assertEqual(len(loader_calls), 102)
        self.assertEqual(len({connection_id for _, connection_id in loader_calls}), 1)
        selects = [statement for statement in statements if statement.lstrip().upper().startswith("SELECT")]
        self.assertEqual(len(selects), 2)

    def test_only_missing_stage_file_is_empty_and_permission_or_contract_errors_propagate(self) -> None:
        value = self._add_run(40, complete=False)

        missing = self._service(loader=lambda *_args: (_ for _ in ()).throw(FileNotFoundError()))
        self.assertEqual(
            missing.list_dream_runs(actor={"actor_id": ACTOR_ID}).runs[0].lifecycle.value,
            "generating",
        )
        for error in (
            ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403),
            RuntimeError("Dream contract is broken"),
        ):
            with self.subTest(error=type(error).__name__), self.assertRaises(type(error)):
                self._service(loader=lambda *_args, error=error: (_ for _ in ()).throw(error)).list_dream_runs(
                    actor={"actor_id": ACTOR_ID}
                )
        self.assertIn(value, self.projections)

    def test_stage_activity_time_participates_in_stable_recent_sort(self) -> None:
        older_thread_newer_stage = self._add_run(
            41,
            complete=True,
            confirmation="dispatched",
            updated_at="2026-08-05T10:00:00+00:00",
            stage_activity_at=datetime(2026, 8, 5, 14, tzinfo=timezone.utc),
        )
        newer_thread = self._add_run(
            42,
            complete=True,
            confirmation="dispatched",
            updated_at="2026-08-05T13:00:00+00:00",
        )

        response = self._service().list_dream_runs(actor={"actor_id": ACTOR_ID})

        self.assertEqual(
            [item.story_workspace_run_id for item in response.runs],
            [older_thread_newer_stage, newer_thread],
        )
        self.assertEqual(response.runs[0].last_activity_at.hour, 14)

    def test_confirmation_lookup_is_a_bounded_batch_query_not_per_run_scan(self) -> None:
        for number in range(50, 56):
            self._add_run(number, complete=False)
        statements: list[str] = []
        self.db.set_trace_callback(statements.append)

        self._service().list_dream_runs(actor={"actor_id": ACTOR_ID})

        selects = [statement for statement in statements if statement.lstrip().upper().startswith("SELECT")]
        self.assertEqual(len(selects), 2)
        self.assertIn("LIMIT", selects[1].upper())

    def test_rejects_malformed_actor_and_does_not_fall_back_to_another_workspace(self) -> None:
        self._add_run(20, complete=False)

        with self.assertRaises(ApiRouteError) as raised:
            self._service().list_dream_runs(actor={"actor_id": "not-a-number"})

        self.assertEqual(raised.exception.status_code, 403)


class StoryWorkspaceDreamReentryRouteTest(unittest.TestCase):
    def test_route_uses_authenticated_actor_and_camel_case_contract(self) -> None:
        class Gateway:
            async def list_dream_runs(self, *, actor):
                self.actor = actor
                from story_workspace.contracts import (
                    StoryWorkspaceDreamReentryCollection,
                    StoryWorkspaceDreamReentryItem,
                    StoryWorkspaceDreamRunLifecycle,
                )

                return StoryWorkspaceDreamReentryCollection(runs=[
                    StoryWorkspaceDreamReentryItem(
                        story_workspace_run_id=run_id(99),
                        goal_prefix="创作一个雨夜车站重逢的短篇故事",
                        deck_id="deck-1",
                        deck_display_name="甲板一",
                        workflow_display_name="Dream",
                        deck_plugin_version="1.0.0",
                        lifecycle=StoryWorkspaceDreamRunLifecycle.GENERATING,
                        group="in_progress",
                        stage_revisions={},
                        confirmation_accepted=False,
                        confirmation_dispatched=False,
                        last_activity_at=datetime(2026, 8, 5, tzinfo=timezone.utc),
                        created_at=datetime(2026, 8, 5, tzinfo=timezone.utc),
                        sort_key="x",
                        href=f"/story-workspace/dream?run={run_id(99)}",
                    ),
                ])

        app = FastAPI()
        gateway = Gateway()
        app.dependency_overrides[story_workspace.get_current_user] = lambda: {"user_id": 7}
        app.dependency_overrides[story_workspace.get_story_workflow_gateway] = lambda: gateway
        app.include_router(story_workspace.router)
        with TestClient(app) as client:
            response = client.get("/api/story-workspace/dream-runs")

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(gateway.actor, {"actor_id": ACTOR_ID})
        self.assertEqual(response.json()["runs"][0]["storyWorkspaceRunId"], run_id(99))
        self.assertEqual(response.json()["runs"][0]["goalPrefix"], "创作一个雨夜车站重逢的短篇故事")
        self.assertNotIn("threadId", response.text)
