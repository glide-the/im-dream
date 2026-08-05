"""Episode binding contract, CAS, and containment tests."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from services.story_workspace.episode_binding_service import (
    StoryWorkspaceEpisodeBindingContext,
    StoryWorkspaceEpisodeBindingContractError,
    StoryWorkspaceEpisodeBindingIdentityConflict,
    StoryWorkspaceEpisodeBindingPathError,
    StoryWorkspaceEpisodeBindingService,
)
from story_workspace.contracts import (
    StoryWorkspaceEpisodeArtifactAvailability,
    StoryWorkspaceEpisodeArtifactConsumer,
    StoryWorkspaceEpisodeArtifactManifestEntry,
    StoryWorkspaceEpisodeArtifactSurface,
    StoryWorkspaceEpisodeBindingAvailability,
    StoryWorkspaceEpisodeBindingRecovery,
    StoryWorkspaceEpisodeProducerAction,
)


RUN_ID = "run_0123456789abcdef0123456789abcdef"


class StoryWorkspaceEpisodeBindingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary_directory.name)
        (self.workspace / ".dream").mkdir()
        (self.workspace / "stories" / "demo" / "episodes").mkdir(parents=True)
        self.service = StoryWorkspaceEpisodeBindingService(self.workspace)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @staticmethod
    def context(
        *,
        story_slug: str | None = "demo",
        locked_story_slug: str | None = "demo",
        run_story_slug: str | None = "demo",
        run_id: str = RUN_ID,
    ) -> StoryWorkspaceEpisodeBindingContext:
        return StoryWorkspaceEpisodeBindingContext(
            workflow_run_id=run_id,
            trusted_project_story_slug=story_slug,
            locked_context_story_slug=locked_story_slug,
            run_provenance_story_slug=run_story_slug,
        )

    @property
    def binding_path(self) -> Path:
        return (
            self.workspace
            / ".dream"
            / "runtime"
            / "runs"
            / RUN_ID
            / "episode.json"
        )

    def test_first_binding_uses_server_owned_ep01_identity(self) -> None:
        binding = self.service.bind_first_episode(self.context())

        self.assertEqual(binding.schema_version, "dream-episode/v1")
        self.assertEqual(binding.workflow_run_id, RUN_ID)
        self.assertRegex(binding.episode_uid, r"^[0-9a-f]{32}$")
        self.assertEqual(binding.story_slug, "demo")
        self.assertEqual(binding.episode_code, "EP01")
        self.assertEqual(binding.episode_root, "stories/demo/episodes/EP01")
        self.assertEqual(binding.revision, 1)
        self.assertEqual(
            json.loads(self.binding_path.read_text(encoding="utf-8")),
            binding.model_dump(mode="json"),
        )

    def test_same_binding_request_is_idempotent(self) -> None:
        first = self.service.bind_first_episode(self.context())
        first_bytes = self.binding_path.read_bytes()

        second = self.service.bind_first_episode(self.context())

        self.assertEqual(second, first)
        self.assertEqual(second.episode_uid, first.episode_uid)
        self.assertEqual(second.revision, 1)
        self.assertEqual(self.binding_path.read_bytes(), first_bytes)

    def test_existing_binding_cannot_switch_story(self) -> None:
        first = self.service.bind_first_episode(self.context())
        first_bytes = self.binding_path.read_bytes()
        (self.workspace / "stories" / "other" / "episodes").mkdir(parents=True)

        with self.assertRaises(StoryWorkspaceEpisodeBindingIdentityConflict):
            self.service.bind_first_episode(
                self.context(
                    story_slug="other",
                    locked_story_slug="other",
                    run_story_slug="other",
                )
            )

        self.assertEqual(self.binding_path.read_bytes(), first_bytes)
        self.assertEqual(first.story_slug, "demo")

    def test_existing_binding_rejects_episode_root_and_run_tampering(self) -> None:
        self.service.bind_first_episode(self.context())
        canonical = json.loads(self.binding_path.read_text(encoding="utf-8"))

        mutations = (
            {"episode_code": "EP02"},
            {"episode_root": "stories/demo/episodes/EP02"},
            {"episode_root": "../../outside"},
            {"workflow_run_id": "run_fedcba9876543210fedcba9876543210"},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.binding_path.write_text(
                    json.dumps({**canonical, **mutation}),
                    encoding="utf-8",
                )
                with self.assertRaises(StoryWorkspaceEpisodeBindingContractError):
                    self.service.bind_first_episode(self.context())

    def test_proven_legacy_context_is_auto_repaired(self) -> None:
        result = self.service.resolve_or_repair_binding(self.context())

        self.assertEqual(
            result.binding_availability,
            StoryWorkspaceEpisodeBindingAvailability.BOUND,
        )
        self.assertIsNotNone(result.binding)
        self.assertTrue(result.recovery.auto_repair_attempted)
        self.assertTrue(result.recovery.can_dispatch)
        self.assertTrue(self.binding_path.is_file())

    def test_unproven_legacy_context_is_unbound_without_episode_probe(self) -> None:
        with patch.object(
            self.service,
            "_validate_episode_root",
            side_effect=AssertionError("episode root must not be probed"),
        ) as probe:
            result = self.service.resolve_or_repair_binding(
                self.context(locked_story_slug=None)
            )

        self.assertEqual(
            result.binding_availability,
            StoryWorkspaceEpisodeBindingAvailability.UNBOUND,
        )
        self.assertIsNone(result.binding)
        self.assertTrue(result.recovery.auto_repair_attempted)
        self.assertFalse(result.recovery.can_dispatch)
        self.assertEqual(result.recovery.public_reason, "episode_binding_unproven")
        probe.assert_not_called()
        self.assertFalse((self.workspace / ".dream" / "runtime").exists())

    def test_mismatched_legacy_evidence_is_unbound_without_episode_probe(self) -> None:
        with patch.object(
            self.service,
            "_validate_episode_root",
            side_effect=AssertionError("episode root must not be probed"),
        ) as probe:
            result = self.service.resolve_or_repair_binding(
                self.context(run_story_slug="other")
            )

        self.assertEqual(
            result.binding_availability,
            StoryWorkspaceEpisodeBindingAvailability.UNBOUND,
        )
        self.assertIsNone(result.binding)
        probe.assert_not_called()

    def test_invalid_story_segments_are_rejected_before_writing(self) -> None:
        for invalid in ("../demo", "demo/../../outside", "/absolute", "Demo"):
            with self.subTest(story_slug=invalid):
                with self.assertRaises(StoryWorkspaceEpisodeBindingContractError):
                    self.service.bind_first_episode(
                        self.context(
                            story_slug=invalid,
                            locked_story_slug=invalid,
                            run_story_slug=invalid,
                        )
                    )
        self.assertFalse((self.workspace / ".dream" / "runtime").exists())

    def test_symlinked_story_root_is_rejected_without_binding_write(self) -> None:
        story_root = self.workspace / "stories" / "demo"
        shutil.rmtree(story_root)
        outside = self.workspace / "outside"
        (outside / "episodes").mkdir(parents=True)
        story_root.symlink_to(outside, target_is_directory=True)

        with self.assertRaises(StoryWorkspaceEpisodeBindingPathError):
            self.service.bind_first_episode(self.context())

        self.assertFalse(self.binding_path.exists())

    def test_manifest_wire_contract_never_exposes_episode_root(self) -> None:
        timestamp = datetime(2026, 8, 5, tzinfo=timezone.utc)
        entry = StoryWorkspaceEpisodeArtifactManifestEntry(
            relativeKey="episode-outline.md",
            availability=StoryWorkspaceEpisodeArtifactAvailability.AVAILABLE,
            contentRevision="sha256:" + "1" * 64,
            mtime=timestamp,
            size=128,
            producerAction=StoryWorkspaceEpisodeProducerAction.PLAN_EPISODE,
            consumers=[
                StoryWorkspaceEpisodeArtifactConsumer.EPISODE_OVERVIEW,
                StoryWorkspaceEpisodeArtifactConsumer.STORYLINE_NAVIGATOR,
            ],
        )
        surface = StoryWorkspaceEpisodeArtifactSurface(
            runId=RUN_ID,
            opaqueEpisodeId="a" * 32,
            manifestRevision="sha256:" + "2" * 64,
            etag='"sha256:' + "2" * 64 + '"',
            bindingAvailability=StoryWorkspaceEpisodeBindingAvailability.BOUND,
            bindingRecovery=StoryWorkspaceEpisodeBindingRecovery(
                autoRepairAttempted=False,
                canDispatch=True,
            ),
            artifacts=[entry],
        )

        payload = surface.model_dump(mode="json", by_alias=True)
        self.assertNotIn("episodeRoot", payload)
        self.assertEqual(payload["artifacts"][0]["relativeKey"], "episode-outline.md")
        self.assertEqual(payload["artifacts"][0]["size"], 128)

    def test_manifest_contract_rejects_path_traversal(self) -> None:
        with self.assertRaises(ValidationError):
            StoryWorkspaceEpisodeArtifactManifestEntry(
                relativeKey="prompts/../../secret.txt",
                availability=StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED,
                producerAction=StoryWorkspaceEpisodeProducerAction.GENERATE_PROMPTS,
                consumers=[StoryWorkspaceEpisodeArtifactConsumer.PROMPT_VIEW],
            )


if __name__ == "__main__":
    unittest.main()
