"""Automatic root-turn workbench synchronization contract."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.workflow_run import RunStatus, WorkflowRun
from services.story_workspace.dream_artifact_turn_hook import DreamArtifactTurnHook
from services.story_workspace.dream_file_service import StoryWorkspaceDreamFileReader
from story_workspace.contracts import StoryWorkspaceDreamRunContext


RUN_ID = "run_0123456789abcdef0123456789abcdef"
THREAD_ID = "thread-dream-artifact-hook"


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


class DreamArtifactTurnHookTest(unittest.TestCase):
    def setUp(self) -> None:
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

    def test_successful_root_turn_projects_page_stages_and_private_artifacts(self) -> None:
        hook = DreamArtifactTurnHook()
        ticket = hook.before_main_turn(
            context=context(),
            actor_id="actor-1",
            cwd=str(self.workspace),
        )
        with patch.object(hook, "_load_authoritative_run", return_value=authoritative_run()):
            result = hook.after_main_turn(ticket)

        self.assertEqual(
            result.changed_stages,
            ("characters", "scenes", "storyboards"),
        )
        self.assertTrue(result.private_artifact_changed)
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
        with patch.object(hook, "_load_authoritative_run", return_value=authoritative_run()):
            first = hook.after_main_turn(ticket)
            second = hook.after_main_turn(ticket)

        self.assertTrue(first.private_artifact_changed)
        self.assertEqual(second.changed_stages, ())
        self.assertFalse(second.private_artifact_changed)
        reader = StoryWorkspaceDreamFileReader(self.workspace)
        self.assertEqual(reader.read_stage(authoritative_run(), stage="characters").revision, 1)

        script = self.workspace / "stories" / "demo-project" / "episodes" / "EP01" / "script.md"
        script.write_text("# EP01 剧本\n\n林夏：继续。\n", encoding="utf-8")
        with patch.object(hook, "_load_authoritative_run", return_value=authoritative_run()):
            third = hook.after_main_turn(ticket)
        self.assertEqual(third.changed_stages, ())
        self.assertTrue(third.private_artifact_changed)
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


if __name__ == "__main__":
    unittest.main()
