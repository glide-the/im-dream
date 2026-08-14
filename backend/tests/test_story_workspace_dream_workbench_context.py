# [Input] DreamWorkbenchContext and a server-owned Thread workspace fixture.
# [Output] Verify durable context refresh, actual-path instruction, and current project/Episode facts.
# [Pos] Story Workspace workbench-context contract test.

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from story_workspace.contracts import StoryWorkspaceDreamRunContext
from story_workspace.dream_workbench_context import (
    DREAM_ASSET_COLLABORATION_SOURCE_PATH,
    DREAM_WORKBENCH_CONTEXT_SOURCE_PATH,
    DreamWorkbenchContext,
    DreamWorkbenchContextError,
    load_dream_asset_collaboration_contract,
)


RUN_ID = "run_0123456789abcdef0123456789abcdef"
THREAD_ID = "thread-dream-workbench-context"


def context() -> StoryWorkspaceDreamRunContext:
    return StoryWorkspaceDreamRunContext(
        workflow_run_id=RUN_ID,
        thread_id=THREAD_ID,
        deck_id="deck-dream",
        deck_plugin_id="plugin-dream",
        deck_plugin_version="1.0.0",
        deck_plugin_binding_id="binding-dream",
        binding_revision=1,
        deck_runtime_snapshot_id="snapshot-dream",
        runtime_plugin_lock_id="lock-dream",
    )


class DreamWorkbenchContextTest(unittest.TestCase):
    def test_materializes_host_owned_contract_and_current_project_facts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / THREAD_ID
            (workspace / ".dream").mkdir(parents=True)
            episode = workspace / "stories" / "demo-story" / "episodes" / "EP02"
            episode.mkdir(parents=True)
            (episode.parents[1] / "project.yaml").write_text(
                "project_id: demo-story\nproject_name: 旧标题\n",
                encoding="utf-8",
            )

            result = DreamWorkbenchContext().refresh_for_turn(
                context=context(),
                workspace_root=workspace,
            )

            deployed = (workspace / ".dream" / "WORKBENCH.md").read_text(
                encoding="utf-8"
            )
            asset_contract = (
                workspace / ".dream" / "ASSET-COLLABORATION.md"
            ).read_text(encoding="utf-8")
            self.assertIn("Skill 负责创作", deployed)
            self.assertIn("project_name", deployed)
            self.assertIn('"project_slug": "demo-story"', deployed)
            self.assertIn('"EP02"', deployed)
            self.assertIn(RUN_ID, deployed)
            self.assertIn(str(workspace), deployed)
            self.assertEqual(
                asset_contract,
                load_dream_asset_collaboration_contract(),
            )
            self.assertIn("必须使用 Read、Write、Edit", asset_contract)
            self.assertIn("character_refs", asset_contract)
            self.assertIn("total_duration_sec", asset_contract)
            self.assertEqual(result.project_slug, "demo-story")
            self.assertEqual(result.episode_codes, ("EP02",))
            self.assertIn("stories/demo-story/project.yaml", result.instruction)
            self.assertIn("直接编辑 canonical `project.yaml`", result.instruction)
            self.assertEqual(
                result.workspace_file,
                str(workspace.resolve() / ".dream" / "WORKBENCH.md"),
            )
            self.assertIn(f"`{result.workspace_file}`", result.instruction)
            self.assertEqual(
                result.asset_collaboration_file,
                str(workspace.resolve() / ".dream" / "ASSET-COLLABORATION.md"),
            )
            self.assertIn(
                f"`{result.asset_collaboration_file}`",
                result.instruction,
            )
            self.assertIn("必须使用 Read 工具读取", result.instruction)
            self.assertIn("proposal JSON 规则不适用于本轮", result.instruction)

    def test_missing_deployed_context_is_restored_on_next_turn(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / THREAD_ID
            (workspace / ".dream").mkdir(parents=True)
            service = DreamWorkbenchContext()

            first = service.refresh_for_turn(
                context=context(),
                workspace_root=workspace,
            )
            Path(first.workspace_file).unlink()
            second = service.refresh_for_turn(
                context=context(),
                workspace_root=workspace,
            )

            self.assertEqual(second.workspace_file, first.workspace_file)
            self.assertTrue(Path(second.workspace_file).is_file())
            self.assertTrue(Path(second.asset_collaboration_file).is_file())
            self.assertIn(RUN_ID, Path(second.workspace_file).read_text("utf-8"))

    def test_missing_asset_contract_is_restored_on_next_turn(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / THREAD_ID
            (workspace / ".dream").mkdir(parents=True)
            service = DreamWorkbenchContext()

            first = service.refresh_for_turn(
                context=context(),
                workspace_root=workspace,
            )
            Path(first.asset_collaboration_file).unlink()
            second = service.refresh_for_turn(
                context=context(),
                workspace_root=workspace,
            )

            self.assertEqual(
                second.asset_collaboration_file,
                first.asset_collaboration_file,
            )
            self.assertEqual(
                Path(second.asset_collaboration_file).read_text("utf-8"),
                load_dream_asset_collaboration_contract(),
            )

    def test_unsafe_deployed_context_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / THREAD_ID
            dream = workspace / ".dream"
            dream.mkdir(parents=True)
            target = dream / "WORKBENCH.md"
            target.symlink_to(DREAM_WORKBENCH_CONTEXT_SOURCE_PATH)

            with self.assertRaisesRegex(
                DreamWorkbenchContextError,
                "context file is unsafe",
            ):
                DreamWorkbenchContext().refresh_for_turn(
                    context=context(),
                    workspace_root=workspace,
                )

    def test_unsafe_asset_contract_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / THREAD_ID
            dream = workspace / ".dream"
            dream.mkdir(parents=True)
            target = dream / "ASSET-COLLABORATION.md"
            target.symlink_to(DREAM_ASSET_COLLABORATION_SOURCE_PATH)

            with self.assertRaisesRegex(
                DreamWorkbenchContextError,
                "asset collaboration context file is unsafe",
            ):
                DreamWorkbenchContext().refresh_for_turn(
                    context=context(),
                    workspace_root=workspace,
                )


if __name__ == "__main__":
    unittest.main()
