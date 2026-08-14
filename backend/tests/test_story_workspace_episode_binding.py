"""Episode binding contract, CAS, and containment tests."""

from __future__ import annotations

import json
import os
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
    StoryWorkspaceEpisodeBindingFile,
    StoryWorkspaceEpisodeProducerAction,
)


RUN_ID = "run_0123456789abcdef0123456789abcdef"
MANIFEST_REVISION = "sha256:" + "2" * 64
ARTIFACT_SPECS = (
    (
        "episode-outline.md",
        StoryWorkspaceEpisodeProducerAction.PLAN_EPISODE,
        (
            StoryWorkspaceEpisodeArtifactConsumer.EPISODE_OVERVIEW,
            StoryWorkspaceEpisodeArtifactConsumer.STORYLINE_NAVIGATOR,
            StoryWorkspaceEpisodeArtifactConsumer.NARRATIVE_WORKBENCH,
        ),
    ),
    (
        "script.md",
        StoryWorkspaceEpisodeProducerAction.WRITE_SCRIPT,
        (
            StoryWorkspaceEpisodeArtifactConsumer.NARRATIVE_WORKBENCH,
            StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
        ),
    ),
    (
        "storyboard.yaml",
        StoryWorkspaceEpisodeProducerAction.REGENERATE_STORYBOARD,
        (
            StoryWorkspaceEpisodeArtifactConsumer.NARRATIVE_WORKBENCH,
            StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
        ),
    ),
    (
        "prompts/",
        StoryWorkspaceEpisodeProducerAction.GENERATE_PROMPTS,
        (
            StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
            StoryWorkspaceEpisodeArtifactConsumer.PROMPT_VIEW,
        ),
    ),
    (
        "renders/",
        StoryWorkspaceEpisodeProducerAction.PREPARE_RENDER_GUIDE,
        (
            StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
            StoryWorkspaceEpisodeArtifactConsumer.RENDER_VIEW,
        ),
    ),
    (
        "review-report.md",
        StoryWorkspaceEpisodeProducerAction.REVIEW_FULL_CHAIN,
        (
            StoryWorkspaceEpisodeArtifactConsumer.REVIEW_VIEW,
            StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
        ),
    ),
)


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

    @staticmethod
    def manifest_entries() -> list[StoryWorkspaceEpisodeArtifactManifestEntry]:
        return [
            StoryWorkspaceEpisodeArtifactManifestEntry(
                relativeKey=relative_key,
                availability=StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED,
                producerAction=producer_action,
                consumers=list(consumers),
            )
            for relative_key, producer_action, consumers in ARTIFACT_SPECS
        ]

    @classmethod
    def bound_surface(
        cls,
        *,
        artifacts: list[StoryWorkspaceEpisodeArtifactManifestEntry] | None = None,
        manifest_revision: str = MANIFEST_REVISION,
        etag: str | None = None,
    ) -> StoryWorkspaceEpisodeArtifactSurface:
        return StoryWorkspaceEpisodeArtifactSurface(
            runId=RUN_ID,
            opaqueEpisodeId="a" * 32,
            episodeCode="EP01",
            manifestRevision=manifest_revision,
            etag=etag or manifest_revision,
            bindingAvailability=StoryWorkspaceEpisodeBindingAvailability.BOUND,
            artifacts=artifacts if artifacts is not None else cls.manifest_entries(),
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

    def test_same_identity_cas_does_not_replace_existing_inode(self) -> None:
        first = self.service.bind_first_episode(self.context())
        original_inode = self.binding_path.stat().st_ino
        original_bytes = self.binding_path.read_bytes()

        with self.service._locked_run_directory(RUN_ID) as run_descriptor:
            result = self.service._write_first_binding(run_descriptor, first)

        self.assertEqual(result, first)
        self.assertEqual(self.binding_path.stat().st_ino, original_inode)
        self.assertEqual(self.binding_path.read_bytes(), original_bytes)

    def test_competing_first_binding_is_never_overwritten(self) -> None:
        competitor = StoryWorkspaceEpisodeBindingFile(
            workflow_run_id=RUN_ID,
            episode_uid="b" * 32,
            story_slug="demo",
            episode_code="EP01",
            episode_root="stories/demo/episodes/EP01",
            revision=1,
            updated_at=datetime(2026, 8, 5, tzinfo=timezone.utc),
        )
        competitor_bytes = (competitor.model_dump_json() + "\n").encode("utf-8")
        original_read = self.service._read_binding
        injected = False

        def read_with_competing_commit(
            run_descriptor: int,
        ) -> StoryWorkspaceEpisodeBindingFile | None:
            nonlocal injected
            current = original_read(run_descriptor)
            if current is None and not injected:
                injected = True
                descriptor = os.open(
                    "episode.json",
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    0o600,
                    dir_fd=run_descriptor,
                )
                try:
                    os.write(descriptor, competitor_bytes)
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
                os.fsync(run_descriptor)
            return current

        with patch.object(
            self.service,
            "_read_binding",
            side_effect=read_with_competing_commit,
        ):
            with self.assertRaises(StoryWorkspaceEpisodeBindingIdentityConflict):
                self.service.bind_first_episode(self.context())

        self.assertEqual(self.binding_path.read_bytes(), competitor_bytes)
        self.assertEqual(
            self.service.bind_first_episode(self.context()).episode_uid,
            competitor.episode_uid,
        )

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

    def test_canonical_project_identity_accepts_one_quoted_or_unquoted_ascii_id(
        self,
    ) -> None:
        project_path = self.workspace / "stories" / "demo" / "project.yaml"

        for payload in (
            "project_id: demo\n",
            'project_id: "demo"\n',
            "project_id: 'demo'\n",
            "project_id: demo\r\n",
            'project_id:\t"demo"\t\r\n',
        ):
            with self.subTest(payload=repr(payload)):
                project_path.write_text(
                    payload,
                    encoding="utf-8",
                    newline="",
                )
                self.assertEqual(
                    self.service.read_canonical_project_story_slug("demo"),
                    "demo",
                )
                self.assertEqual(
                    self.service.discover_unique_canonical_project_story_slug(),
                    "demo",
                )

    def test_canonical_project_identity_accepts_legacy_project_mapping_id(
        self,
    ) -> None:
        project_path = self.workspace / "stories" / "demo" / "project.yaml"
        project_path.write_text(
            "project:\n"
            "  project_id: demo\n"
            "  project_name: Legacy Dream project\n"
            "concept:\n"
            "  logline: Keep the existing project readable.\n",
            encoding="utf-8",
        )

        self.assertEqual(
            self.service.read_canonical_project_story_slug("demo"),
            "demo",
        )
        self.assertEqual(
            self.service.discover_unique_canonical_project_story_slug(),
            "demo",
        )

    def test_canonical_project_identity_rejects_ambiguous_or_unsafe_values(
        self,
    ) -> None:
        project_path = self.workspace / "stories" / "demo" / "project.yaml"
        payloads = (
            "project_id: demo\nproject_id: demo\n",
            'project_id: "demo"\nproject_id: demo\n',
            "project_id: 项目\nproject_id: demo\n",
            "project_id: []\nproject_id: demo\n",
            " project_id: demo\n",
            " project_id: other\nproject_id: demo\n",
            "project_id: other\n",
            "project_id: 项目\n",
            "project_id: 'demo\"\n",
            "project_id: demo # ambiguous trailing syntax\n",
            "project_id:\ndemo\n",
            "project_id:\r\n\tdemo\r\n",
            "project_id:\vdemo\n",
            "project_id:\fdemo\n",
            "project_id: demo\v\n",
            "project_id: demo\f\n",
            "other:\n  project_id: demo\n",
            "project:\n    project_id: demo\n",
            "project:\n  project_id: other\n",
            "project:\n  project_id: demo\nproject_id: demo\n",
            "project:\n  project_id: demo\nproject:\n  project_name: duplicate\n",
        )

        for payload in payloads:
            with self.subTest(payload=payload):
                project_path.write_text(payload, encoding="utf-8")
                with self.assertRaises(StoryWorkspaceEpisodeBindingContractError):
                    self.service.read_canonical_project_story_slug("demo")

    def test_canonical_project_identity_rejects_symlink_and_oversize_file(
        self,
    ) -> None:
        project_path = self.workspace / "stories" / "demo" / "project.yaml"
        outside = self.workspace / "outside-project.yaml"
        outside.write_text("project_id: demo\n", encoding="utf-8")
        project_path.symlink_to(outside)
        with self.assertRaises(StoryWorkspaceEpisodeBindingPathError):
            self.service.read_canonical_project_story_slug("demo")

        project_path.unlink()
        project_path.write_text(
            "project_id: demo\n" + "#" * (256 * 1024),
            encoding="utf-8",
        )
        with self.assertRaises(StoryWorkspaceEpisodeBindingPathError):
            self.service.read_canonical_project_story_slug("demo")

    def test_symlinked_story_root_is_rejected_without_binding_write(self) -> None:
        story_root = self.workspace / "stories" / "demo"
        shutil.rmtree(story_root)
        outside = self.workspace / "outside"
        (outside / "episodes").mkdir(parents=True)
        story_root.symlink_to(outside, target_is_directory=True)

        with self.assertRaises(StoryWorkspaceEpisodeBindingPathError):
            self.service.bind_first_episode(self.context())

        self.assertFalse(self.binding_path.exists())

    def test_every_binding_and_episode_path_layer_rejects_symlinks(self) -> None:
        layers = (".dream", "runtime", "runs", "run", "episode.json", "EP01")
        for layer in layers:
            with self.subTest(layer=layer), tempfile.TemporaryDirectory() as directory:
                workspace = Path(directory)
                dream = workspace / ".dream"
                episode_parent = workspace / "stories" / "demo" / "episodes"
                dream.mkdir()
                episode_parent.mkdir(parents=True)
                outside = workspace / "outside"
                outside.mkdir()
                if layer == ".dream":
                    dream.rmdir()
                    dream.symlink_to(outside, target_is_directory=True)
                elif layer == "runtime":
                    (dream / "runtime").symlink_to(outside, target_is_directory=True)
                elif layer == "runs":
                    (dream / "runtime").mkdir()
                    (dream / "runtime" / "runs").symlink_to(
                        outside,
                        target_is_directory=True,
                    )
                elif layer == "run":
                    (dream / "runtime" / "runs").mkdir(parents=True)
                    (dream / "runtime" / "runs" / RUN_ID).symlink_to(
                        outside,
                        target_is_directory=True,
                    )
                elif layer == "episode.json":
                    run_directory = dream / "runtime" / "runs" / RUN_ID
                    run_directory.mkdir(parents=True)
                    target = outside / "episode.json"
                    target.write_text("{}", encoding="utf-8")
                    (run_directory / "episode.json").symlink_to(target)
                else:
                    (episode_parent / "EP01").symlink_to(
                        outside,
                        target_is_directory=True,
                    )
                service = StoryWorkspaceEpisodeBindingService(workspace)
                with self.assertRaises(StoryWorkspaceEpisodeBindingPathError):
                    service.bind_first_episode(self.context())

    def test_manifest_wire_contract_never_exposes_episode_root(self) -> None:
        surface = self.bound_surface()

        payload = surface.model_dump(mode="json", by_alias=True)
        self.assertNotIn("episodeRoot", payload)
        self.assertEqual(payload["artifacts"][0]["relativeKey"], "episode-outline.md")
        self.assertEqual(len(payload["artifacts"]), 6)
        self.assertTrue(
            all(
                item["availability"] == "not_generated"
                for item in payload["artifacts"]
            )
        )

    def test_artifact_mapping_is_fixed_by_key_or_prefix(self) -> None:
        for relative_key, producer_action, consumers in ARTIFACT_SPECS:
            with self.subTest(relative_key=relative_key, field="producerAction"):
                with self.assertRaises(ValidationError):
                    StoryWorkspaceEpisodeArtifactManifestEntry(
                        relativeKey=relative_key,
                        availability=(
                            StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED
                        ),
                        producerAction=StoryWorkspaceEpisodeProducerAction.COMMIT_EPISODE,
                        consumers=list(consumers),
                    )
            with self.subTest(relative_key=relative_key, field="consumers"):
                with self.assertRaises(ValidationError):
                    StoryWorkspaceEpisodeArtifactManifestEntry(
                        relativeKey=relative_key,
                        availability=(
                            StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED
                        ),
                        producerAction=producer_action,
                        consumers=[StoryWorkspaceEpisodeArtifactConsumer.REVIEW_VIEW],
                    )

    def test_review_report_accepts_only_review_producers(self) -> None:
        consumers = [
            StoryWorkspaceEpisodeArtifactConsumer.REVIEW_VIEW,
            StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
        ]
        for producer in (
            StoryWorkspaceEpisodeProducerAction.REVIEW_SCRIPT,
            StoryWorkspaceEpisodeProducerAction.REVIEW_FULL_CHAIN,
        ):
            StoryWorkspaceEpisodeArtifactManifestEntry(
                relativeKey="review-report.md",
                availability=StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED,
                producerAction=producer,
                consumers=consumers,
            )
        with self.assertRaises(ValidationError):
            StoryWorkspaceEpisodeArtifactManifestEntry(
                relativeKey="review-report.md",
                availability=StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED,
                producerAction=StoryWorkspaceEpisodeProducerAction.WRITE_SCRIPT,
                consumers=consumers,
            )

    def test_directory_artifacts_allow_only_approved_text_extensions(self) -> None:
        cases = (
            (
                "prompts/shot.yml",
                StoryWorkspaceEpisodeProducerAction.GENERATE_PROMPTS,
                [
                    StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
                    StoryWorkspaceEpisodeArtifactConsumer.PROMPT_VIEW,
                ],
            ),
            (
                "prompts/shot.yaml",
                StoryWorkspaceEpisodeProducerAction.GENERATE_PROMPTS,
                [
                    StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
                    StoryWorkspaceEpisodeArtifactConsumer.PROMPT_VIEW,
                ],
            ),
            (
                "renders/render-guide.md",
                StoryWorkspaceEpisodeProducerAction.PREPARE_RENDER_GUIDE,
                [
                    StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
                    StoryWorkspaceEpisodeArtifactConsumer.RENDER_VIEW,
                ],
            ),
            (
                "renders/queue.json",
                StoryWorkspaceEpisodeProducerAction.PREPARE_RENDER_GUIDE,
                [
                    StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
                    StoryWorkspaceEpisodeArtifactConsumer.RENDER_VIEW,
                ],
            ),
        )
        for relative_key, producer, consumers in cases:
            with self.subTest(relative_key=relative_key):
                StoryWorkspaceEpisodeArtifactManifestEntry(
                    relativeKey=relative_key,
                    availability=StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED,
                    producerAction=producer,
                    consumers=consumers,
                )

    def test_raw_paths_and_unapproved_extensions_are_rejected(self) -> None:
        invalid_keys = (
            "/absolute/script.md",
            "prompts/../../secret.txt",
            "prompts/C:\\secret.yml",
            "prompts/shot.html",
            "renders/frame.png",
            "episode-outline.md/child",
        )
        for relative_key in invalid_keys:
            with self.subTest(relative_key=relative_key):
                with self.assertRaises(ValidationError):
                    StoryWorkspaceEpisodeArtifactManifestEntry(
                        relativeKey=relative_key,
                        availability=(
                            StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED
                        ),
                        producerAction=(
                            StoryWorkspaceEpisodeProducerAction.GENERATE_PROMPTS
                        ),
                        consumers=[
                            StoryWorkspaceEpisodeArtifactConsumer.SHOT_INSPECTOR,
                            StoryWorkspaceEpisodeArtifactConsumer.PROMPT_VIEW,
                        ],
                    )

    def test_bound_surface_requires_complete_roots_and_allows_aggregate_etag(self) -> None:
        for artifacts in ([], self.manifest_entries()[:-1]):
            with self.subTest(count=len(artifacts)):
                with self.assertRaises(ValidationError):
                    self.bound_surface(artifacts=artifacts)
        surface = self.bound_surface(etag="sha256:" + "3" * 64)
        self.assertNotEqual(surface.etag, surface.manifest_revision)

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
