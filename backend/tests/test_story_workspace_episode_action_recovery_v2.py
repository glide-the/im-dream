"""Server projection recovery and per-Episode workflow fact isolation tests."""

from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from services.story_workspace.episode_action_service import (
    StoryWorkspaceEpisodeWorkflowFactService,
)
from services.story_workspace.episode_binding_service import (
    StoryWorkspaceEpisodeBindingContext,
    StoryWorkspaceEpisodeBindingService,
)
from services.story_workspace.multi_episode_action_service import (
    StoryWorkspaceEpisodeActionProjectionService,
)
from story_workspace.contracts import (
    StoryWorkspaceEpisodeAction,
    StoryWorkspaceEpisodeArtifactAvailability,
    StoryWorkspaceEpisodeWorkflowFile,
)


RUN_ID = "run_0123456789abcdef0123456789abcdef"
EP01_ID = "1" * 32
MANIFEST = "sha256:" + "a" * 64
NOW = datetime(2026, 8, 6, tzinfo=UTC)


def _surface(episode_uid: str, manifest_revision: str = MANIFEST) -> object:
    keys = (
        "episode-outline.md",
        "script.md",
        "storyboard.yaml",
        "prompts/",
        "renders/",
        "review-report.md",
    )
    artifacts = [
        SimpleNamespace(
            relative_key=key,
            availability=StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED,
            content_revision=None,
        )
        for key in keys
    ]
    return SimpleNamespace(
        run_id=RUN_ID,
        opaque_episode_id=episode_uid,
        manifest_revision=manifest_revision,
        artifacts=artifacts,
        auxiliary=SimpleNamespace(review=None),
    )


def _facts(episode_uid: str) -> StoryWorkspaceEpisodeWorkflowFile:
    return StoryWorkspaceEpisodeWorkflowFile(
        workflow_run_id=RUN_ID,
        episode_uid=episode_uid,
        revision=0,
        completions=[],
        updated_at=NOW,
    )


class StoryWorkspaceEpisodeActionRecoveryV2Test(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary_directory.name)
        (self.workspace / ".dream").mkdir()
        (self.workspace / "stories" / "demo" / "episodes" / "EP01").mkdir(
            parents=True
        )
        (self.workspace / "stories" / "demo" / "project.yaml").write_text(
            "project_id: demo\nformat:\n  total_episodes: 3\n",
            encoding="utf-8",
        )
        self.binding_service = StoryWorkspaceEpisodeBindingService(self.workspace)
        self.context = StoryWorkspaceEpisodeBindingContext(
            workflow_run_id=RUN_ID,
            trusted_project_story_slug="demo",
            locked_context_story_slug="demo",
            run_provenance_story_slug="demo",
            episode_uid=EP01_ID,
        )
        self.binding_service.bind_first_episode(self.context)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_projection_is_identical_after_refresh_and_reentry(self) -> None:
        registry = self.binding_service.read_episode_registry(self.context)
        first = StoryWorkspaceEpisodeActionProjectionService.project(
            surface=_surface(EP01_ID),
            facts=_facts(EP01_ID),
            registry=registry,
            total_episodes=3,
        )
        reentered = StoryWorkspaceEpisodeActionProjectionService().project(
            surface=_surface(EP01_ID),
            facts=_facts(EP01_ID),
            registry=registry,
            total_episodes=3,
        )

        self.assertEqual(first, reentered)
        self.assertEqual(first.action_options[0].label, "开始 EP01 分集规划")
        self.assertEqual(
            StoryWorkspaceEpisodeActionProjectionService.surface_etag(
                MANIFEST,
                first,
            ),
            StoryWorkspaceEpisodeActionProjectionService.surface_etag(
                MANIFEST,
                reentered,
            ),
        )

    def test_new_manifest_revision_replaces_old_action_identity_and_etag(self) -> None:
        registry = self.binding_service.read_episode_registry(self.context)
        first = StoryWorkspaceEpisodeActionProjectionService.project(
            surface=_surface(EP01_ID),
            facts=_facts(EP01_ID),
            registry=registry,
            total_episodes=3,
        )
        revised_manifest = "sha256:" + "b" * 64
        revised = StoryWorkspaceEpisodeActionProjectionService.project(
            surface=_surface(EP01_ID, revised_manifest),
            facts=_facts(EP01_ID),
            registry=registry,
            total_episodes=3,
        )

        self.assertNotEqual(
            StoryWorkspaceEpisodeActionProjectionService.surface_etag(MANIFEST, first),
            StoryWorkspaceEpisodeActionProjectionService.surface_etag(
                revised_manifest,
                revised,
            ),
        )

    def test_ep01_and_ep02_workflow_facts_are_isolated_and_recoverable(self) -> None:
        registry = self.binding_service.ensure_next_episode(
            self.context,
            expected_revision=1,
            total_episodes=3,
        )
        ep02_id = registry.episodes[1].episode_uid
        facts_service = StoryWorkspaceEpisodeWorkflowFactService(self.workspace)
        ep01 = facts_service.record_completion(
            workflow_run_id=RUN_ID,
            episode_uid=EP01_ID,
            action=StoryWorkspaceEpisodeAction.PLAN_EPISODE,
            input_revision=MANIFEST,
            manifest_revision=MANIFEST,
            message_id="dream_agent_" + "1" * 64,
            expected_revision=0,
        )
        ep02 = facts_service.record_completion(
            workflow_run_id=RUN_ID,
            episode_uid=ep02_id,
            action=StoryWorkspaceEpisodeAction.PLAN_EPISODE,
            input_revision=MANIFEST,
            manifest_revision=MANIFEST,
            message_id="dream_agent_" + "2" * 64,
            expected_revision=0,
        )

        self.assertEqual(ep01.episode_uid, EP01_ID)
        self.assertEqual(ep02.episode_uid, ep02_id)
        self.assertEqual(facts_service.read(RUN_ID, EP01_ID), ep01)
        self.assertEqual(facts_service.read(RUN_ID, ep02_id), ep02)
        run_directory = self.binding_service.workspace_root / ".dream" / "runtime" / "runs" / RUN_ID
        self.assertTrue((run_directory / "episode-workflow.json").is_file())
        self.assertTrue((run_directory / f"episode-workflow.{ep02_id}.json").is_file())


if __name__ == "__main__":
    unittest.main()
