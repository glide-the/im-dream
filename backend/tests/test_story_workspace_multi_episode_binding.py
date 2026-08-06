"""Trusted multi-Episode registry, numbering, and CAS tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pydantic import ValidationError

from services.story_workspace.episode_binding_service import (
    StoryWorkspaceEpisodeBindingContext,
    StoryWorkspaceEpisodeBindingContractError,
    StoryWorkspaceEpisodeBindingIdentityConflict,
    StoryWorkspaceEpisodeBindingService,
)
from story_workspace.contracts import StoryWorkspaceEpisodeRegistryFile


RUN_ID = "run_0123456789abcdef0123456789abcdef"


class StoryWorkspaceMultiEpisodeBindingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary_directory.name)
        (self.workspace / ".dream").mkdir()
        (self.workspace / "stories" / "demo" / "episodes" / "EP01").mkdir(
            parents=True
        )
        self.service = StoryWorkspaceEpisodeBindingService(self.workspace)
        self.context = StoryWorkspaceEpisodeBindingContext(
            workflow_run_id=RUN_ID,
            trusted_project_story_slug="demo",
            locked_context_story_slug="demo",
            run_provenance_story_slug="demo",
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

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

    def test_legacy_ep01_projects_as_registry_without_rewriting(self) -> None:
        legacy = self.service.bind_first_episode(self.context)
        legacy_bytes = self.binding_path.read_bytes()

        registry = self.service.read_episode_registry(self.context)

        self.assertEqual(registry.schema_version, "dream-episode/v2")
        self.assertEqual(registry.revision, 1)
        self.assertEqual(registry.active_episode_uid, legacy.episode_uid)
        self.assertEqual(len(registry.episodes), 1)
        self.assertEqual(registry.episodes[0].episode_number, 1)
        self.assertEqual(registry.episodes[0].episode_code, "EP01")
        self.assertEqual(self.binding_path.read_bytes(), legacy_bytes)

    def test_next_episode_upgrades_same_binding_file_with_server_numbering(
        self,
    ) -> None:
        first = self.service.bind_first_episode(self.context)

        registry = self.service.ensure_next_episode(
            self.context,
            expected_revision=1,
            total_episodes=3,
        )

        self.assertEqual(registry.revision, 2)
        self.assertEqual(registry.active_episode_uid, first.episode_uid)
        self.assertEqual(
            [(item.episode_number, item.episode_code) for item in registry.episodes],
            [(1, "EP01"), (2, "EP02")],
        )
        self.assertEqual(
            registry.episodes[1].episode_root,
            "stories/demo/episodes/EP02",
        )
        self.assertRegex(registry.episodes[1].episode_uid, r"^[0-9a-f]{32}$")
        persisted = json.loads(self.binding_path.read_text(encoding="utf-8"))
        self.assertEqual(persisted, registry.model_dump(mode="json"))

    def test_replayed_next_candidate_is_idempotent_under_stale_revision(self) -> None:
        self.service.bind_first_episode(self.context)
        first_result = self.service.ensure_next_episode(
            self.context,
            expected_revision=1,
            total_episodes=3,
        )
        committed_bytes = self.binding_path.read_bytes()

        replay = self.service.ensure_next_episode(
            self.context,
            expected_revision=1,
            total_episodes=3,
        )

        self.assertEqual(replay, first_result)
        self.assertEqual(len(replay.episodes), 2)
        self.assertEqual(self.binding_path.read_bytes(), committed_bytes)

    def test_competing_next_requests_converge_on_one_opaque_identity(self) -> None:
        self.service.bind_first_episode(self.context)
        competing_service = StoryWorkspaceEpisodeBindingService(self.workspace)

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(
                    lambda service: service.ensure_next_episode(
                        self.context,
                        expected_revision=1,
                        total_episodes=3,
                    ),
                    (self.service, competing_service),
                )
            )

        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0].revision, 2)
        self.assertEqual(len(results[0].episodes), 2)
        self.assertEqual(
            results[0].episodes[1].episode_uid,
            results[1].episodes[1].episode_uid,
        )

    def test_active_ep02_can_create_ep03_without_array_owned_identity(self) -> None:
        self.service.bind_first_episode(self.context)
        with_ep02 = self.service.ensure_next_episode(
            self.context,
            expected_revision=1,
            total_episodes=3,
        )
        ep02 = with_ep02.episodes[1]
        active_ep02 = self.service.activate_episode(
            self.context,
            episode_uid=ep02.episode_uid,
            expected_revision=2,
        )

        with_ep03 = self.service.ensure_next_episode(
            self.context,
            expected_revision=active_ep02.revision,
            total_episodes=3,
        )

        self.assertEqual(with_ep03.active_episode_uid, ep02.episode_uid)
        self.assertEqual(with_ep03.revision, 4)
        self.assertEqual(
            [(item.episode_number, item.episode_code) for item in with_ep03.episodes],
            [(1, "EP01"), (2, "EP02"), (3, "EP03")],
        )

    def test_wrong_story_revision_or_total_fails_before_write(self) -> None:
        self.service.bind_first_episode(self.context)
        original = self.binding_path.read_bytes()
        other_story_context = StoryWorkspaceEpisodeBindingContext(
            workflow_run_id=RUN_ID,
            trusted_project_story_slug="other",
            locked_context_story_slug="other",
            run_provenance_story_slug="other",
        )
        (self.workspace / "stories" / "other" / "episodes").mkdir(parents=True)

        cases = (
            (StoryWorkspaceEpisodeBindingIdentityConflict, other_story_context, 1, 3),
            (StoryWorkspaceEpisodeBindingContractError, self.context, 9, 3),
            (StoryWorkspaceEpisodeBindingContractError, self.context, 1, 1),
        )
        for error, context, revision, total in cases:
            with self.subTest(error=error.__name__, revision=revision, total=total):
                with self.assertRaises(error):
                    self.service.ensure_next_episode(
                        context,
                        expected_revision=revision,
                        total_episodes=total,
                    )
                self.assertEqual(self.binding_path.read_bytes(), original)

    def test_registry_contract_rejects_client_supplied_numbering_and_paths(
        self,
    ) -> None:
        self.service.bind_first_episode(self.context)
        registry = self.service.read_episode_registry(self.context)
        payload = registry.model_dump(mode="json")
        first = payload["episodes"][0]

        for mutation in (
            {"episode_number": 2},
            {"episode_code": "EP02"},
            {"episode_root": "stories/demo/episodes/EP02"},
            {"episode_root": "../../outside"},
        ):
            with self.subTest(mutation=mutation):
                tampered = {**payload, "episodes": [{**first, **mutation}]}
                with self.assertRaises(ValidationError):
                    StoryWorkspaceEpisodeRegistryFile.model_validate(tampered)


if __name__ == "__main__":
    unittest.main()
