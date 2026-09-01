# [Input] Canonical Dream workbench fixtures, trusted launch metadata, and the post-turn Hook.
# [Output] Verify deterministic artifact sync plus repairable/non-repairable validation classification.
# [Pos] Story Workspace post-turn Hook contract test in backend/tests.
# [Sync] 2026-09-01: cover allowlisted project-slug repair and fail-closed launch authority.

"""Automatic root-turn workbench synchronization contract."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.workflow_run import RunStatus, WorkflowRun
from services.story_workspace.dream_artifact_turn_hook import (
    DreamArtifactRepairability,
    DreamArtifactTurnHook,
    DreamArtifactTurnHookError,
)
from services.story_workspace.dream_file_service import StoryWorkspaceDreamFileReader
from services.story_workspace.episode_artifact_service import (
    StoryWorkspaceEpisodeAuthority,
)
from story_workspace.contracts import (
    StoryWorkspaceDreamRunContext,
    StoryWorkspaceDreamStage,
)


RUN_ID = "run_0123456789abcdef0123456789abcdef"
THREAD_ID = "thread-dream-artifact-hook"
ORIGINAL_MATERIALIZE_STORY_INDEX = DreamArtifactTurnHook._materialize_story_index


def authoritative_run() -> WorkflowRun:
    return WorkflowRun(
        workflow_run_id=RUN_ID,
        deck_plugin_id="plugin-1",
        workflow_definition_ref="workflow-1",
        deck_plugin_binding_id="binding-1",
        binding_revision=3,
        deck_plugin_version="1.2.3",
        deck_runtime_snapshot_id="snapshot-1",
        runtime_plugin_lock_id="lock-1",
        deck_plugin_manifest_hash="sha256:" + "1" * 64,
        workflow_preflight_id="pf_" + "2" * 32,
        status=RunStatus.PREFLIGHT,
        workspace_id="workspace-1",
        idempotency_key="run-request-1",
        input_hash="sha256:" + "3" * 64,
        semantic_fingerprint="sha256:" + "4" * 64,
        status_version=1,
        created_by="actor-1",
        created_at=datetime(2026, 8, 13, tzinfo=timezone.utc),
        source_voice_thread_id=THREAD_ID,
    )


def context() -> StoryWorkspaceDreamRunContext:
    return StoryWorkspaceDreamRunContext(
        workflow_run_id=RUN_ID,
        thread_id=THREAD_ID,
        deck_id="deck-1",
        deck_plugin_id="plugin-1",
        deck_plugin_version="1.2.3",
        deck_plugin_binding_id="binding-1",
        binding_revision=3,
        deck_runtime_snapshot_id="snapshot-1",
        runtime_plugin_lock_id="lock-1",
    )


def episode_authority() -> StoryWorkspaceEpisodeAuthority:
    return StoryWorkspaceEpisodeAuthority(
        workflow_run_id=RUN_ID,
        episode_uid="5" * 32,
        story_slug="demo-project",
        episode_code="EP01",
    )


def launched_run() -> WorkflowRun:
    return authoritative_run().model_copy(update={
        "source_message_id": "dream-launch-message",
        "source_message_time": datetime(2026, 8, 13, tzinfo=timezone.utc),
    })


def launch_metadata(*, project_story_slug: str = "demo-project") -> dict:
    selected_context = context()
    return {
        "kind": "story-workspace-dream-launch",
        "schemaVersion": "story-workspace-dream-launch/v1",
        "actorId": "actor-1",
        "workspaceId": "workspace-1",
        "deckId": "deck-1",
        "agentId": None,
        "workflowRunId": RUN_ID,
        "threadId": THREAD_ID,
        "goal": "雨夜归途",
        "projectStorySlug": project_story_slug,
        "dreamContext": selected_context.model_dump(mode="json"),
    }


class DreamArtifactTurnHookTest(unittest.TestCase):
    def setUp(self) -> None:
        self.story_index_materialize = patch.object(
            DreamArtifactTurnHook,
            "_materialize_story_index",
            return_value="same_revision",
        )
        self.story_index_materialize_mock = self.story_index_materialize.start()
        self.addCleanup(self.story_index_materialize.stop)
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary_directory.name) / THREAD_ID
        self.workspace.mkdir()
        (self.workspace / ".dream").mkdir()
        (self.workspace / "assets" / "characters").mkdir(parents=True)
        (self.workspace / "assets" / "scenes").mkdir(parents=True)
        episode = self.workspace / "stories" / "demo-project" / "episodes" / "EP01"
        episode.mkdir(parents=True)

        (self.workspace / "assets" / "characters" / "lead.md").write_text(
            """---
char_id: lead
char_name: 林夏
occupation: 调查记者
relationships:
  - char_id: guide
    relation: 旧友
---
# 林夏

她在雨夜返回旧车站寻找真相。
""",
            encoding="utf-8",
        )
        (self.workspace / "assets" / "scenes" / "station.md").write_text(
            """---
scene_id: station
name: 雨夜车站
type: exterior
---
# 雨夜车站

废弃站台被冷雨和钠灯包围。
""",
            encoding="utf-8",
        )
        (episode.parents[1] / "project.yaml").write_text(
            "project_id: demo-project\nproject_name: 雨夜归途\n",
            encoding="utf-8",
        )
        (episode / "episode-outline.md").write_text(
            "# EP01 大纲\n\n林夏回到车站。\n",
            encoding="utf-8",
        )
        (episode / "script.md").write_text(
            "# EP01 剧本\n\n林夏：我回来了。\n",
            encoding="utf-8",
        )
        (episode / "storyboard.yaml").write_text(
            """---
episode: EP01
total_shots: 2
total_duration_sec: 12.5
---
shots:
  - shot_id: S01
    scene_ref: station
""",
            encoding="utf-8",
        )
        (episode / "review-report.md").write_text(
            "# 审阅\n\n草稿可继续编辑。\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _binding_error(self, metadata: dict) -> DreamArtifactTurnHookError:
        hook = DreamArtifactTurnHook()
        ticket = hook.before_main_turn(
            context=context(),
            actor_id="actor-1",
            cwd=str(self.workspace),
        )
        db = MagicMock()
        db.in_transaction = False
        db.execute.return_value.fetchone.return_value = {
            "metadata": json.dumps(metadata),
        }
        with (
            patch(
                "services.story_workspace.dream_artifact_turn_hook.database.get_db",
                return_value=db,
            ),
            self.assertRaises(DreamArtifactTurnHookError) as raised,
        ):
            hook._ensure_first_episode_binding(
                ticket,
                launched_run(),
                private_files={
                    "stories/demo-project/episodes/EP01/script.md": b"# EP01\n",
                },
            )
        db.close.assert_called_once_with()
        return raised.exception

    def test_project_story_slug_mismatch_is_agent_repairable(self) -> None:
        error = self._binding_error(
            launch_metadata(project_story_slug="server-project")
        )

        self.assertEqual(error.code, "PROJECT_STORY_SLUG_MISMATCH")
        self.assertIs(
            error.issue.repairability,
            DreamArtifactRepairability.AGENT_REPAIRABLE,
        )
        self.assertEqual(error.issue.expected, "server-project")
        self.assertEqual(error.issue.actual, "demo-project")

    def test_launch_actor_thread_run_deck_and_plugin_authority_are_not_repairable(self) -> None:
        mutations = {
            "actor": lambda value: value.update(actorId="actor-forged"),
            "run": lambda value: value.update(workflowRunId="run_" + "f" * 32),
            "thread": lambda value: value.update(threadId="thread-forged"),
            "deck": lambda value: value.update(deckId="deck-forged"),
            "plugin_lock": lambda value: value["dreamContext"].update(
                runtime_plugin_lock_id="lock-forged"
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(authority=label):
                metadata = launch_metadata()
                mutate(metadata)
                error = self._binding_error(metadata)
                self.assertEqual(error.code, "DREAM_LAUNCH_AUTHORITY_INVALID")
                self.assertIs(
                    error.issue.repairability,
                    DreamArtifactRepairability.NON_REPAIRABLE,
                )

    def test_successful_root_turn_projects_page_stages_and_private_artifacts(self) -> None:
        hook = DreamArtifactTurnHook()
        ticket = hook.before_main_turn(
            context=context(),
            actor_id="actor-1",
            cwd=str(self.workspace),
        )
        with (
            patch.object(hook, "_load_authoritative_run", return_value=authoritative_run()),
            patch.object(hook, "_record_output_ready"),
            patch.object(hook, "_ensure_first_episode_binding", return_value=True),
        ):
            result = hook.after_main_turn(ticket)

        self.assertEqual(
            result.changed_stages,
            ("characters", "scenes", "storyboards"),
        )
        self.assertTrue(result.private_artifact_changed)
        self.assertTrue(result.episode_bound)
        self.assertEqual(result.story_index_status, "same_revision")
        self.assertEqual(result.changed_source_files, ())
        projection = StoryWorkspaceDreamFileReader(self.workspace).read(
            authoritative_run(),
            thread_id=THREAD_ID,
        )
        self.assertTrue(projection.can_confirm)
        self.assertEqual(projection.stages["characters"].items[0].display_name, "林夏")
        self.assertEqual(projection.stages["scenes"].items[0].display_name, "雨夜车站")
        self.assertEqual(projection.stages["storyboards"].items[0].entity_id, "EP01")

        artifact = self.workspace / ".dream" / "runtime" / "runs" / RUN_ID / "artifact"
        private_episode = artifact / "stories" / "demo-project" / "episodes" / "EP01"
        self.assertEqual(
            (private_episode / "script.md").read_text(encoding="utf-8"),
            "# EP01 剧本\n\n林夏：我回来了。\n",
        )
        manifest = json.loads((artifact / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], "dream-artifact-manifest/v1")
        self.assertEqual(manifest["workflow_run_id"], RUN_ID)
        self.assertEqual(
            {entry["path"] for entry in manifest["files"]},
            set(result.private_files),
        )

    def test_repeated_root_turn_is_idempotent_and_changed_file_republishes(self) -> None:
        hook = DreamArtifactTurnHook()
        ticket = hook.before_main_turn(
            context=context(),
            actor_id="actor-1",
            cwd=str(self.workspace),
        )
        with (
            patch.object(hook, "_load_authoritative_run", return_value=authoritative_run()),
            patch.object(hook, "_record_output_ready"),
            patch.object(hook, "_ensure_first_episode_binding", return_value=True),
        ):
            first = hook.after_main_turn(ticket)
            second = hook.after_main_turn(ticket)

        self.assertTrue(first.private_artifact_changed)
        self.assertEqual(second.changed_stages, ())
        self.assertFalse(second.private_artifact_changed)
        reader = StoryWorkspaceDreamFileReader(self.workspace)
        self.assertEqual(reader.read_stage(authoritative_run(), stage="characters").revision, 1)

        script = self.workspace / "stories" / "demo-project" / "episodes" / "EP01" / "script.md"
        script.write_text("# EP01 剧本\n\n林夏：继续。\n", encoding="utf-8")
        with (
            patch.object(hook, "_load_authoritative_run", return_value=authoritative_run()),
            patch.object(hook, "_record_output_ready"),
            patch.object(hook, "_ensure_first_episode_binding", return_value=True),
        ):
            third = hook.after_main_turn(ticket)
        self.assertEqual(third.changed_stages, ())
        self.assertTrue(third.private_artifact_changed)
        self.assertEqual(
            third.changed_source_files,
            ("stories/demo-project/episodes/EP01/script.md",),
        )
        private_script = (
            self.workspace
            / ".dream"
            / "runtime"
            / "runs"
            / RUN_ID
            / "artifact"
            / "stories"
            / "demo-project"
            / "episodes"
            / "EP01"
            / "script.md"
        )
        self.assertIn("继续", private_script.read_text(encoding="utf-8"))

    def test_removed_skill_sources_delete_stale_stage_and_new_sources_rebuild_it(self) -> None:
        hook = DreamArtifactTurnHook()
        ticket = hook.before_main_turn(
            context=context(),
            actor_id="actor-1",
            cwd=str(self.workspace),
        )
        patches = (
            patch.object(hook, "_load_authoritative_run", return_value=authoritative_run()),
            patch.object(hook, "_record_output_ready"),
            patch.object(hook, "_ensure_first_episode_binding", return_value=True),
        )
        with patches[0], patches[1], patches[2]:
            hook.after_main_turn(ticket)

        character = self.workspace / "assets" / "characters" / "lead.md"
        character.unlink()
        with (
            patch.object(hook, "_load_authoritative_run", return_value=authoritative_run()),
            patch.object(hook, "_record_output_ready"),
            patch.object(hook, "_ensure_first_episode_binding", return_value=True),
        ):
            removed = hook.after_main_turn(ticket)

        self.assertIn("characters", removed.changed_stages)
        reader = StoryWorkspaceDreamFileReader(self.workspace)
        self.assertIsNone(reader.read_stage(authoritative_run(), stage="characters"))

        character.write_text(
            "---\nchar_id: patient\nchar_name: 隔壁的病友\n---\n\n新的角色事实。\n",
            encoding="utf-8",
        )
        with (
            patch.object(hook, "_load_authoritative_run", return_value=authoritative_run()),
            patch.object(hook, "_record_output_ready"),
            patch.object(hook, "_ensure_first_episode_binding", return_value=True),
        ):
            rebuilt = hook.after_main_turn(ticket)

        self.assertIn("characters", rebuilt.changed_stages)
        stage = reader.read_stage(authoritative_run(), stage="characters")
        assert stage is not None
        self.assertEqual(stage.items[0].entity_id, "patient")
        self.assertEqual(stage.items[0].display_name, "隔壁的病友")

    def test_asset_crud_reconciles_characters_scenes_and_storyboard(self) -> None:
        """One complete natural-language asset journey maps file facts only."""

        hook = DreamArtifactTurnHook()
        ticket = hook.before_main_turn(
            context=context(),
            actor_id="actor-1",
            cwd=str(self.workspace),
        )

        def synchronize():
            with (
                patch.object(
                    hook,
                    "_load_authoritative_run",
                    return_value=authoritative_run(),
                ),
                patch.object(hook, "_record_output_ready"),
                patch.object(
                    hook,
                    "_ensure_first_episode_binding",
                    return_value=True,
                ),
            ):
                return hook.after_main_turn(ticket)

        synchronize()
        reader = StoryWorkspaceDreamFileReader(self.workspace)
        character = self.workspace / "assets" / "characters" / "guide.md"
        scene = self.workspace / "assets" / "scenes" / "fireplace.md"
        storyboard = (
            self.workspace
            / "stories"
            / "demo-project"
            / "episodes"
            / "EP01"
            / "storyboard.yaml"
        )

        character.write_text(
            "---\nchar_id: guide\nchar_name: 阿酷\n---\n\n短发的安全员。\n",
            encoding="utf-8",
        )
        scene.write_text(
            "---\nscene_id: fireplace\nscene_name: 火塘\n---\n\n暖橙色火光。\n",
            encoding="utf-8",
        )
        storyboard_payload = {
            "episode": "EP01",
            "total_shots": 1,
            "total_duration_sec": 0,
            "shots": [
                {
                    "shot_id": "S01",
                    "scene_ref": "station",
                }
            ],
        }
        storyboard_payload["shots"].append(
            {
                "shot_id": "shot-qa-asset",
                "scene_ref": "fireplace",
                "characters": ["guide"],
                "shot_type": "medium",
                "visual": "阿酷站在火塘旁",
                "camera": {"movement": "static"},
                "timing": {"duration_sec": 4},
            }
        )
        storyboard_payload["total_shots"] = len(storyboard_payload["shots"])
        storyboard_payload["total_duration_sec"] = 4
        storyboard.write_text(
            yaml.safe_dump(storyboard_payload, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

        added = synchronize()
        self.assertEqual(
            set(added.changed_stages),
            {"characters", "scenes", "storyboards"},
        )
        character_stage = reader.read_stage(authoritative_run(), stage="characters")
        scene_stage = reader.read_stage(authoritative_run(), stage="scenes")
        storyboard_stage = reader.read_stage(authoritative_run(), stage="storyboards")
        assert character_stage is not None
        assert scene_stage is not None
        assert storyboard_stage is not None
        self.assertEqual(
            {item.entity_id for item in character_stage.items},
            {"lead", "guide"},
        )
        self.assertEqual(
            {item.entity_id for item in scene_stage.items},
            {"station", "fireplace"},
        )

        character.write_text(
            "---\nchar_id: guide\nchar_name: 阿酷（安全员）\n---\n\n短发，穿黑色冲锋衣。\n",
            encoding="utf-8",
        )
        scene.write_text(
            "---\nscene_id: fireplace\nscene_name: 村子火塘\n---\n\n暖橙色火光与木椅。\n",
            encoding="utf-8",
        )
        storyboard_payload["shots"][-1]["visual"] = "阿酷穿黑色冲锋衣站在火塘旁"
        storyboard.write_text(
            yaml.safe_dump(storyboard_payload, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

        updated = synchronize()
        self.assertEqual(
            set(updated.changed_stages),
            {"characters", "scenes", "storyboards"},
        )
        character_stage = reader.read_stage(authoritative_run(), stage="characters")
        scene_stage = reader.read_stage(authoritative_run(), stage="scenes")
        assert character_stage is not None
        assert scene_stage is not None
        self.assertEqual(character_stage.revision, 3)
        self.assertEqual(scene_stage.revision, 3)
        self.assertIn(
            "阿酷（安全员）",
            {item.display_name for item in character_stage.items},
        )
        self.assertIn(
            "村子火塘",
            {item.display_name for item in scene_stage.items},
        )

        # Remove the referencing shot first, then its temporary character and
        # scene. This mirrors the contract's no-dangling-reference cleanup.
        storyboard_payload["shots"] = [
            shot
            for shot in storyboard_payload["shots"]
            if shot.get("shot_id") != "shot-qa-asset"
        ]
        storyboard_payload["total_shots"] = len(storyboard_payload["shots"])
        storyboard_payload["total_duration_sec"] = 0
        storyboard.write_text(
            yaml.safe_dump(storyboard_payload, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        character.unlink()
        scene.unlink()

        deleted = synchronize()
        self.assertEqual(
            set(deleted.changed_stages),
            {"characters", "scenes", "storyboards"},
        )
        character_stage = reader.read_stage(authoritative_run(), stage="characters")
        scene_stage = reader.read_stage(authoritative_run(), stage="scenes")
        assert character_stage is not None
        assert scene_stage is not None
        self.assertEqual(
            {item.entity_id for item in character_stage.items},
            {"lead"},
        )
        self.assertEqual(
            {item.entity_id for item in scene_stage.items},
            {"station"},
        )
        final_storyboard = yaml.safe_load(storyboard.read_text("utf-8"))
        self.assertFalse(
            any(
                shot.get("shot_id") == "shot-qa-asset"
                for shot in final_storyboard["shots"]
            )
        )

    def test_project_title_edit_republishes_canonical_project_file(self) -> None:
        hook = DreamArtifactTurnHook()
        ticket = hook.before_main_turn(
            context=context(),
            actor_id="actor-1",
            cwd=str(self.workspace),
        )
        with (
            patch.object(hook, "_load_authoritative_run", return_value=authoritative_run()),
            patch.object(hook, "_record_output_ready"),
            patch.object(hook, "_ensure_first_episode_binding", return_value=True),
        ):
            hook.after_main_turn(ticket)

        project = self.workspace / "stories" / "demo-project" / "project.yaml"
        project.write_text(
            "project_id: demo-project\nproject_name: 隔壁的病友\n",
            encoding="utf-8",
        )
        with (
            patch.object(hook, "_load_authoritative_run", return_value=authoritative_run()),
            patch.object(hook, "_record_output_ready"),
            patch.object(hook, "_ensure_first_episode_binding", return_value=True),
        ):
            result = hook.after_main_turn(ticket)

        self.assertTrue(result.private_artifact_changed)
        self.assertIn(
            "stories/demo-project/project.yaml",
            result.changed_source_files,
        )
        private_project = (
            self.workspace
            / ".dream"
            / "runtime"
            / "runs"
            / RUN_ID
            / "artifact"
            / "stories"
            / "demo-project"
            / "project.yaml"
        )
        self.assertIn("隔壁的病友", private_project.read_text(encoding="utf-8"))

    def test_any_successful_dream_turn_attempts_idempotent_episode_binding(self) -> None:
        hook = DreamArtifactTurnHook()
        ticket = hook.before_main_turn(
            context=context(),
            actor_id="actor-1",
            cwd=str(self.workspace),
        )
        with (
            patch.object(hook, "_load_authoritative_run", return_value=authoritative_run()),
            patch.object(hook, "_record_output_ready"),
            patch.object(hook, "_ensure_first_episode_binding", return_value=True) as bind,
        ):
            result = hook.after_main_turn(ticket)
        bind.assert_called_once()
        self.assertTrue(result.episode_bound)
        self.story_index_materialize_mock.assert_called_once_with(
            ticket,
            authoritative_run(),
            episode_authority=True,
        )

    def test_story_index_materialization_uses_current_episode_surface(self) -> None:
        ticket = DreamArtifactTurnHook().before_main_turn(
            context=context(),
            actor_id="actor-1",
            cwd=str(self.workspace),
        )
        surface = object()
        db = unittest.mock.MagicMock()
        story_index = unittest.mock.MagicMock()
        story_index.materialize.return_value = {
            "status": "updated",
            "storyId": "story-1",
            "errorCode": None,
        }
        with (
            patch(
                "services.story_workspace.dream_artifact_turn_hook."
                "StoryWorkspaceEpisodeArtifactService"
            ) as artifact_service,
            patch(
                "services.story_workspace.dream_artifact_turn_hook."
                "ArtifactStoryIndexService",
                return_value=story_index,
            ),
            patch(
                "services.story_workspace.dream_artifact_turn_hook.database.get_db",
                return_value=db,
            ),
        ):
            artifact_service.return_value.read_surface.return_value = surface
            status = ORIGINAL_MATERIALIZE_STORY_INDEX(
                ticket,
                authoritative_run(),
                episode_authority=episode_authority(),
            )

        self.assertEqual(status, "updated")
        artifact_service.return_value.read_surface.assert_called_once_with(
            RUN_ID,
            episode_authority=episode_authority(),
        )
        story_index.materialize.assert_called_once_with(
            db=db,
            workspace_root=self.workspace.resolve(),
            workflow_run=authoritative_run(),
            actor_id="actor-1",
            thread_id=THREAD_ID,
            episode_authority=episode_authority(),
            refreshed_surface=surface,
        )
        db.close.assert_called_once_with()

    def test_story_index_waits_for_script_without_failing_partial_workspace(self) -> None:
        ticket = DreamArtifactTurnHook().before_main_turn(
            context=context(),
            actor_id="actor-1",
            cwd=str(self.workspace),
        )
        db = unittest.mock.MagicMock()
        story_index = unittest.mock.MagicMock()
        story_index.materialize.return_value = {
            "status": "failed",
            "errorCode": "artifact_missing",
            "retryable": True,
        }
        with (
            patch(
                "services.story_workspace.dream_artifact_turn_hook."
                "StoryWorkspaceEpisodeArtifactService"
            ) as artifact_service,
            patch(
                "services.story_workspace.dream_artifact_turn_hook."
                "ArtifactStoryIndexService",
                return_value=story_index,
            ),
            patch(
                "services.story_workspace.dream_artifact_turn_hook.database.get_db",
                return_value=db,
            ),
        ):
            artifact_service.return_value.read_surface.return_value = object()
            status = ORIGINAL_MATERIALIZE_STORY_INDEX(
                ticket,
                authoritative_run(),
                episode_authority=episode_authority(),
            )

        self.assertEqual(status, "not_ready")

    def test_historical_unicode_and_header_only_assets_form_page_projection(self) -> None:
        (self.workspace / "assets" / "characters" / "凌波.yaml").write_text(
            """# 角色：凌波
id: lingbo
name: 凌波

## 核心特质
谨慎且有策略。
""",
            encoding="utf-8",
        )
        (self.workspace / "assets" / "scenes" / "studio.md").write_text(
            """---
scene_id: studio
scene_name: 创作工作室
location: 城市中心
""",
            encoding="utf-8",
        )

        projections = DreamArtifactTurnHook._collect_stage_projections(
            self.workspace.resolve()
        )
        by_stage = {projection.stage.value: projection for projection in projections}
        characters = {
            item["entity_id"]: item for item in by_stage["characters"].items
        }
        scenes = {item["entity_id"]: item for item in by_stage["scenes"].items}

        self.assertEqual(characters["lingbo"]["display_name"], "凌波")
        self.assertEqual(
            characters["lingbo"]["source_file"],
            "assets/characters/凌波.yaml",
        )
        self.assertEqual(scenes["studio"]["display_name"], "创作工作室")

    def test_character_projection_keeps_compact_summary_and_complete_document(self) -> None:
        character = self.workspace / "assets" / "characters" / "lao-tou.md"
        source = """---
char_id: lao-tou
char_name: 老头（庖丁）
---
# 老头（庖丁）（lao-tou）

身份：夏都王宫掌厨，实为商地出身的故人。

外形：满头白发，围裙满是油渍，佝偻但有精气神。

人物关系：
- 对伊尹：识破其手法来历，暗中协助、传递商地情报。
- 对夏桀：隐忍多年，潜伏于御膳房。

动机：等待拨乱反正的一天。
"""
        character.write_text(source, encoding="utf-8")

        projections = DreamArtifactTurnHook._collect_stage_projections(
            self.workspace.resolve()
        )
        characters = next(
            projection
            for projection in projections
            if projection.stage is StoryWorkspaceDreamStage.CHARACTERS
        )
        lao_tou = next(
            item for item in characters.items if item["entity_id"] == "lao-tou"
        )

        self.assertEqual(
            lao_tou["summary"],
            "身份：夏都王宫掌厨，实为商地出身的故人。",
        )
        self.assertEqual(lao_tou["content"], source.strip())
        self.assertIn("外形：满头白发", str(lao_tou["content"]))
        self.assertIn("人物关系：", str(lao_tou["content"]))
        self.assertIn("动机：等待拨乱反正的一天。", str(lao_tou["content"]))


if __name__ == "__main__":
    unittest.main()
