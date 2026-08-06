"""Actor-scoped Episode artifact aggregation and REST boundary tests."""

from __future__ import annotations

import json
import errno
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from routers import story_workspace
from services.deck import story_workflow_gateway as gateway_module
from services.errors.error_registry import ApiRouteError
from services.story_workspace.episode_artifact_service import (
    StoryWorkspaceEpisodeArtifactPathError,
    StoryWorkspaceEpisodeArtifactService,
)
from services.story_workspace.episode_auxiliary_artifact_adapter import (
    StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
)
from services.story_workspace.episode_binding_service import (
    StoryWorkspaceEpisodeBindingContext,
    StoryWorkspaceEpisodeBindingService,
)
from story_workspace.contracts import (
    StoryWorkspaceEpisodeArtifactAvailability,
    StoryWorkspaceEpisodeArtifactSurface,
    StoryWorkspaceEpisodeBindingAvailability,
    StoryWorkspaceEpisodeBindingRecovery,
)


RUN_ID = "run_0123456789abcdef0123456789abcdef"
OTHER_RUN_ID = "run_fedcba9876543210fedcba9876543210"
ACTOR_ID = "7"
WORKSPACE_ID = "workspace-1"
THREAD_ID = "thread-1"
VENDOR_EPISODE = (
    Path(__file__).resolve().parents[2]
    / "vendor"
    / "drama-forge"
    / "drama-forge"
    / "stories"
    / "didi-zhengzhou"
    / "episodes"
    / "EP01"
)


def _binding_context(run_id: str = RUN_ID, story_slug: str = "didi-zhengzhou"):
    return StoryWorkspaceEpisodeBindingContext(
        workflow_run_id=run_id,
        trusted_project_story_slug=story_slug,
        locked_context_story_slug=story_slug,
        run_provenance_story_slug=story_slug,
    )


def _episode_authority(
    episode_uid: str,
    *,
    run_id: str = RUN_ID,
    story_slug: str = "didi-zhengzhou",
) -> dict[str, str]:
    return {
        "schema": "story-workspace-episode-authority/v1",
        "workflow_run_id": run_id,
        "episode_uid": episode_uid,
        "story_slug": story_slug,
        "episode_code": "EP01",
    }


def _unbound_surface() -> StoryWorkspaceEpisodeArtifactSurface:
    return StoryWorkspaceEpisodeArtifactSurface(
        runId=RUN_ID,
        bindingAvailability=StoryWorkspaceEpisodeBindingAvailability.UNBOUND,
        bindingRecovery=StoryWorkspaceEpisodeBindingRecovery(
            autoRepairAttempted=True,
            canDispatch=True,
            publicReason="episode_binding_unproven",
        ),
    )


class _RecordingGateway:
    def __init__(self, response: StoryWorkspaceEpisodeArtifactSurface) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, str]]] = []

    async def get_episode_artifacts(
        self,
        workflow_run_id: str,
        *,
        actor: dict[str, str],
    ) -> StoryWorkspaceEpisodeArtifactSurface:
        self.calls.append((workflow_run_id, actor))
        return self.response


def test_route_passes_only_run_and_actor_and_honors_etag() -> None:
    surface = _unbound_surface()
    app = FastAPI()
    gateway = _RecordingGateway(surface)
    app.dependency_overrides[story_workspace.get_current_user] = lambda: {
        "user_id": int(ACTOR_ID),
    }
    app.dependency_overrides[story_workspace.get_story_workflow_gateway] = (
        lambda: gateway
    )
    app.include_router(story_workspace.router)

    with TestClient(app) as client:
        response = client.get(
            f"/api/story-workspace/workflow-runs/{RUN_ID}/episode-artifacts"
        )

    assert response.status_code == 200
    assert response.json()["bindingAvailability"] == "unbound"
    assert gateway.calls == [(RUN_ID, {"actor_id": ACTOR_ID})]


def test_route_returns_304_only_for_the_exact_quoted_manifest_etag() -> None:
    manifest_revision = "sha256:" + "a" * 64
    class EtagGateway(_RecordingGateway):
        async def get_episode_artifacts(self, workflow_run_id: str, *, actor: dict[str, str]):
            self.calls.append((workflow_run_id, actor))
            return type("Surface", (), {
                "model_dump": lambda self, **_: {
                    "runId": workflow_run_id,
                    "etag": manifest_revision,
                }
            })()

    app = FastAPI()
    gateway = EtagGateway(_unbound_surface())
    app.dependency_overrides[story_workspace.get_current_user] = lambda: {
        "user_id": int(ACTOR_ID),
    }
    app.dependency_overrides[story_workspace.get_story_workflow_gateway] = lambda: gateway
    app.include_router(story_workspace.router)
    with TestClient(app) as client:
        response = client.get(
            f"/api/story-workspace/workflow-runs/{RUN_ID}/episode-artifacts",
            headers={"If-None-Match": f'"{manifest_revision}"'},
        )
        unquoted = client.get(
            f"/api/story-workspace/workflow-runs/{RUN_ID}/episode-artifacts",
            headers={"If-None-Match": manifest_revision},
        )

    assert response.status_code == 304
    assert response.headers["etag"] == f'"{manifest_revision}"'
    assert response.content == b""
    assert unquoted.status_code == 200


class TestStoryWorkspaceEpisodeArtifactService:
    def setup_method(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary_directory.name)
        (self.workspace / ".dream").mkdir()
        self.story = self.workspace / "stories" / "didi-zhengzhou"
        self.episode = self.story / "episodes" / "EP01"
        self.episode.mkdir(parents=True)
        (self.story / "project.yaml").write_text(
            "project_id: didi-zhengzhou\nproject_name: Demo\n",
            encoding="utf-8",
        )
        self.binding = StoryWorkspaceEpisodeBindingService(
            self.workspace
        ).resolve_or_repair_binding(_binding_context()).binding
        assert self.binding is not None
        self.authority = _episode_authority(self.binding.episode_uid)
        self.service = StoryWorkspaceEpisodeArtifactService(self.workspace)

    def teardown_method(self) -> None:
        self.temporary_directory.cleanup()

    def read_surface(self):
        return self.service.read_surface(
            RUN_ID,
            episode_authority=self.authority,
        )

    def test_missing_artifacts_are_six_recoverable_not_generated_facts(self) -> None:
        surface = self.read_surface()

        assert surface.binding_availability is StoryWorkspaceEpisodeBindingAvailability.BOUND
        assert surface.opaque_episode_id == self.binding.episode_uid
        assert len(surface.artifacts) == 6
        assert {
            item.relative_key: item.availability for item in surface.artifacts
        } == {
            "episode-outline.md": StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED,
            "script.md": StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED,
            "storyboard.yaml": StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED,
            "prompts/": StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED,
            "renders/": StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED,
            "review-report.md": StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED,
        }
        assert surface.narrative is not None
        assert surface.narrative.narrative_beats == []
        assert surface.narrative.scenes == []
        assert surface.narrative.shots == []
        assert surface.auxiliary is not None
        assert surface.auxiliary.prompts.total == 0
        assert "stories/didi-zhengzhou" not in surface.model_dump_json()
        assert str(self.workspace) not in surface.model_dump_json()

    def test_real_didi_episode_projects_45_prompts_45_queue_and_no_orphans(self) -> None:
        for name in (
            "episode-outline.md",
            "script.md",
            "storyboard.yaml",
            "review-report.md",
        ):
            shutil.copy2(VENDOR_EPISODE / name, self.episode / name)
        shutil.copytree(VENDOR_EPISODE / "prompts", self.episode / "prompts")
        shutil.copytree(VENDOR_EPISODE / "renders", self.episode / "renders")

        surface = self.read_surface()

        assert surface.narrative is not None
        assert len(surface.narrative.shots) == 45
        assert surface.auxiliary is not None
        assert surface.auxiliary.prompts.total == 45
        assert surface.auxiliary.render_guide is not None
        assert surface.auxiliary.render_guide.queue.total == 45
        assert surface.auxiliary.associations.orphan_prompts == []
        assert surface.auxiliary.associations.orphan_queue_entries == []
        assert all(
            item.availability is StoryWorkspaceEpisodeArtifactAvailability.AVAILABLE
            for item in surface.artifacts
        )

    def test_manifest_revision_and_etag_change_with_content_fact(self) -> None:
        first = self.read_surface()
        (self.episode / "episode-outline.md").write_text(
            "---\ntitle: Demo\n---\n# Story Goals\n- Begin\n",
            encoding="utf-8",
        )
        second = self.read_surface()

        assert first.manifest_revision != second.manifest_revision
        assert second.etag == second.manifest_revision

    @pytest.mark.parametrize(
        "relative_target",
        [
            "episode-outline.md",
            "prompts",
            "renders",
        ],
    )
    def test_symlink_at_any_artifact_layer_is_rejected(
        self,
        relative_target: str,
    ) -> None:
        outside = self.workspace / "outside"
        outside.write_text("private", encoding="utf-8")
        target = self.episode / relative_target
        target.symlink_to(outside)

        with pytest.raises(StoryWorkspaceEpisodeArtifactPathError):
            self.read_surface()

    def test_invalid_artifact_is_200_surface_fact_without_untrusted_text(self) -> None:
        (self.episode / "storyboard.yaml").write_bytes(b"shots: [\xff]\n")

        surface = self.read_surface()

        storyboard = next(
            item for item in surface.artifacts if item.relative_key == "storyboard.yaml"
        )
        assert storyboard.availability is StoryWorkspaceEpisodeArtifactAvailability.INVALID
        assert "\\xff" not in surface.model_dump_json()

    def test_review_case_variant_links_to_storyboard_canonical_view_id(self) -> None:
        (self.episode / "storyboard.yaml").write_text(
            "shots:\n  - shot_id: S04-E01-020a\n    visual: Canonical shot.\n",
            encoding="utf-8",
        )
        (self.episode / "review-report.md").write_text(
            "# Review\n\n## Shot finding\nS04-E01-020A needs work.\n",
            encoding="utf-8",
        )

        surface = self.read_surface()

        assert surface.narrative is not None
        assert surface.auxiliary is not None
        assert surface.auxiliary.review is not None
        shot = surface.narrative.shots[0]
        target = surface.auxiliary.review.targets[0]
        assert target.source_key == shot.shot_id
        assert target.target_view_id == shot.id
        assert target.association_status.value == "linked"

    def test_duplicate_case_variant_review_target_isolated_from_narrative(self) -> None:
        (self.episode / "storyboard.yaml").write_text(
            "shots:\n  - shot_id: S04-E01-020a\n    visual: Canonical shot.\n",
            encoding="utf-8",
        )
        (self.episode / "review-report.md").write_text(
            (
                "# Review\n\n## First\nS04-E01-020a needs work.\n\n"
                "## Second\nS04-E01-020A repeats the target.\n"
            ),
            encoding="utf-8",
        )

        surface = self.read_surface()

        availability = {item.relative_key: item.availability for item in surface.artifacts}
        assert availability["storyboard.yaml"] is StoryWorkspaceEpisodeArtifactAvailability.AVAILABLE
        assert availability["review-report.md"] is StoryWorkspaceEpisodeArtifactAvailability.INVALID
        assert surface.narrative is not None
        assert len(surface.narrative.shots) == 1
        assert surface.auxiliary is not None
        assert surface.auxiliary.review is None

    def test_verified_file_read_eio_is_local_unavailable(self) -> None:
        storyboard_path = self.episode / "storyboard.yaml"
        storyboard_path.write_text(
            "shots:\n  - shot_id: S04-E01-020a\n    visual: Canonical shot.\n",
            encoding="utf-8",
        )
        real_read = os.read
        storyboard_identity = (storyboard_path.stat().st_dev, storyboard_path.stat().st_ino)

        def fail_storyboard_read(descriptor: int, size: int) -> bytes:
            try:
                metadata = os.fstat(descriptor)
                descriptor_identity = (metadata.st_dev, metadata.st_ino)
            except OSError:
                descriptor_identity = None
            if descriptor_identity == storyboard_identity:
                raise OSError(errno.EIO, "simulated transient read failure")
            return real_read(descriptor, size)

        with patch("services.story_workspace.episode_artifact_service.os.read", fail_storyboard_read):
            surface = self.read_surface()

        availability = {item.relative_key: item.availability for item in surface.artifacts}
        assert availability["storyboard.yaml"] is StoryWorkspaceEpisodeArtifactAvailability.UNAVAILABLE
        assert availability["episode-outline.md"] is StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED
        assert surface.narrative is not None
        assert surface.narrative.shots == []

    def test_verified_directory_list_eio_is_local_unavailable(self) -> None:
        prompts_path = self.episode / "prompts"
        prompts_path.mkdir()
        (prompts_path / "shot.yaml").write_text("shots: []\n", encoding="utf-8")
        prompt_identity = (prompts_path.stat().st_dev, prompts_path.stat().st_ino)
        real_listdir = os.listdir

        def fail_prompt_list(directory: int | str | os.PathLike[str]):
            if isinstance(directory, int):
                metadata = os.fstat(directory)
                if (metadata.st_dev, metadata.st_ino) == prompt_identity:
                    raise OSError(errno.EIO, "simulated transient list failure")
            return real_listdir(directory)

        with patch(
            "services.story_workspace.episode_artifact_service.os.listdir",
            fail_prompt_list,
        ):
            surface = self.read_surface()

        availability = {item.relative_key: item.availability for item in surface.artifacts}
        assert availability["prompts/"] is StoryWorkspaceEpisodeArtifactAvailability.UNAVAILABLE
        assert surface.auxiliary is not None
        assert surface.auxiliary.prompts.items == []

    def test_backend_same_entry_closure_rejects_crosswire_to_real_shot(self) -> None:
        (self.episode / "storyboard.yaml").write_text(
            (
                "shots:\n"
                "  - shot_id: S04-E01-020a\n    visual: First shot.\n"
                "  - shot_id: S04-E01-020b\n    visual: Second shot.\n"
            ),
            encoding="utf-8",
        )
        (self.episode / "review-report.md").write_text(
            "# Review\n\n## Shot finding\nS04-E01-020a needs work.\n",
            encoding="utf-8",
        )
        surface = self.read_surface()
        assert surface.narrative is not None
        assert surface.auxiliary is not None
        assert surface.auxiliary.review is not None
        target = surface.auxiliary.review.targets[0]
        wrong_target = target.model_copy(
            update={"target_view_id": surface.narrative.shots[1].id}
        )
        review = surface.auxiliary.review.model_copy(
            update={"targets": [wrong_target]}
        )
        auxiliary = surface.auxiliary.model_copy(update={"review": review})

        with pytest.raises(
            StoryWorkspaceEpisodeAuxiliaryArtifactParseError,
            match="canonical_link_mismatch",
        ):
            self.service._assert_auxiliary_same_entry(
                auxiliary,
                surface.narrative,
                root="review",
            )

    def test_binding_story_or_canonical_project_identity_cannot_be_swapped(self) -> None:
        (self.story / "project.yaml").write_text(
            "project_id: other\n",
            encoding="utf-8",
        )

        with pytest.raises(StoryWorkspaceEpisodeArtifactPathError):
            self.read_surface()

    @pytest.mark.parametrize(
        "binding_updates",
        [
            {"workflow_run_id": OTHER_RUN_ID},
            {"story_slug": "other", "episode_root": "stories/other/episodes/EP01"},
            {"episode_root": "stories/didi-zhengzhou/episodes/../other"},
        ],
    )
    def test_persisted_binding_cannot_change_run_story_or_root(
        self,
        binding_updates: dict[str, str],
    ) -> None:
        binding_path = (
            self.workspace / ".dream" / "runtime" / "runs" / RUN_ID / "episode.json"
        )
        payload = json.loads(binding_path.read_text(encoding="utf-8"))
        payload.update(binding_updates)
        binding_path.write_text(json.dumps(payload), encoding="utf-8")

        surface = self.read_surface()
        assert surface.binding_availability is StoryWorkspaceEpisodeBindingAvailability.UNBOUND
        assert surface.artifacts == []

    @pytest.mark.parametrize(
        ("component", "replacement_kind"),
        [
            ("stories", "dir"),
            ("stories/didi-zhengzhou", "dir"),
            ("stories/didi-zhengzhou/episodes", "dir"),
            ("stories/didi-zhengzhou/episodes/EP01", "dir"),
            (".dream/runtime/runs/" + RUN_ID + "/episode.json", "file"),
        ],
    )
    def test_symlink_in_binding_or_episode_ancestor_is_rejected(
        self,
        component: str,
        replacement_kind: str,
    ) -> None:
        target = self.workspace / component
        outside = self.workspace / ("outside-" + replacement_kind)
        if replacement_kind == "dir":
            outside.mkdir()
            shutil.rmtree(target)
        else:
            outside.write_text("private", encoding="utf-8")
            target.unlink()
        target.symlink_to(outside)

        with pytest.raises(StoryWorkspaceEpisodeArtifactPathError):
            self.read_surface()

    def test_symlink_inside_approved_directory_is_rejected(self) -> None:
        prompts = self.episode / "prompts"
        prompts.mkdir()
        outside = self.workspace / "outside.yaml"
        outside.write_text("shots: []\n", encoding="utf-8")
        (prompts / "episode.yaml").symlink_to(outside)

        with pytest.raises(StoryWorkspaceEpisodeArtifactPathError):
            self.read_surface()

    def test_unbound_does_not_probe_episode_tree(self) -> None:
        service = StoryWorkspaceEpisodeArtifactService(self.workspace)

        with patch.object(
            service,
            "_read_bound_episode",
            side_effect=AssertionError("artifact probe before binding"),
        ) as probe:
            surface = service.read_surface(
                OTHER_RUN_ID,
                episode_authority=_episode_authority(
                    "f" * 32,
                    run_id=OTHER_RUN_ID,
                ),
            )

        assert surface.binding_availability is StoryWorkspaceEpisodeBindingAvailability.UNBOUND
        assert surface.artifacts == []
        assert surface.opaque_episode_id is None
        probe.assert_not_called()

    @pytest.mark.parametrize(
        "authority",
        [
            None,
            {},
            {"schema": "wrong"},
            _episode_authority("e" * 32),
            _episode_authority("a" * 32, run_id=OTHER_RUN_ID),
            _episode_authority("a" * 32, story_slug="other"),
        ],
    )
    def test_missing_invalid_or_mismatched_authority_is_unbound_without_probe(
        self,
        authority: dict[str, str] | None,
    ) -> None:
        with patch.object(
            self.service,
            "_read_bound_episode",
            side_effect=AssertionError("Episode probe without matched authority"),
        ) as probe:
            surface = self.service.read_surface(
                RUN_ID,
                episode_authority=authority,
            )

        assert surface.binding_availability is StoryWorkspaceEpisodeBindingAvailability.UNBOUND
        assert surface.artifacts == []
        probe.assert_not_called()

    def test_self_consistent_binding_and_project_swap_cannot_override_authority(self) -> None:
        binding_path = (
            self.workspace / ".dream" / "runtime" / "runs" / RUN_ID / "episode.json"
        )
        payload = json.loads(binding_path.read_text(encoding="utf-8"))
        payload.update(
            {
                "episode_uid": "e" * 32,
                "story_slug": "other",
                "episode_root": "stories/other/episodes/EP01",
            }
        )
        binding_path.write_text(json.dumps(payload), encoding="utf-8")
        swapped_episode = self.workspace / "stories" / "other" / "episodes" / "EP01"
        swapped_episode.mkdir(parents=True)
        (swapped_episode.parent.parent / "project.yaml").write_text(
            "project_id: other\n",
            encoding="utf-8",
        )
        (swapped_episode / "episode-outline.md").write_text(
            "# Story Goals\n- SWAPPED SOURCE\n",
            encoding="utf-8",
        )

        with patch.object(
            self.service,
            "_read_bound_episode",
            side_effect=AssertionError("swapped Episode must not be probed"),
        ) as probe:
            surface = self.service.read_surface(
                RUN_ID,
                episode_authority=self.authority,
            )

        assert surface.binding_availability is StoryWorkspaceEpisodeBindingAvailability.UNBOUND
        assert "SWAPPED SOURCE" not in surface.model_dump_json()
        probe.assert_not_called()

    def test_oversize_root_is_invalid_while_other_artifacts_remain_available(self) -> None:
        (self.episode / "episode-outline.md").write_bytes(b"x" * (1024 * 1024 + 1))
        (self.episode / "script.md").write_text(
            "---\ntitle: Demo\n---\n# Script\n",
            encoding="utf-8",
        )

        first = self.read_surface()
        (self.episode / "episode-outline.md").write_bytes(b"y" * (1024 * 1024 + 2))
        second = self.read_surface()

        availability = {item.relative_key: item.availability for item in second.artifacts}
        assert availability["episode-outline.md"] is StoryWorkspaceEpisodeArtifactAvailability.INVALID
        assert availability["script.md"] is StoryWorkspaceEpisodeArtifactAvailability.AVAILABLE
        assert first.manifest_revision != second.manifest_revision

    def test_oversize_root_revision_changes_after_same_size_preserved_mtime_rewrite(
        self,
    ) -> None:
        outline = self.episode / "episode-outline.md"
        outline.write_bytes(b"x" * (1024 * 1024 + 1))
        original = outline.stat()
        first = self.read_surface()

        outline.write_bytes(b"y" * original.st_size)
        os.utime(outline, ns=(original.st_atime_ns, original.st_mtime_ns))
        second = self.read_surface()

        outline_fact = next(
            item
            for item in second.artifacts
            if item.relative_key == "episode-outline.md"
        )
        assert (
            outline_fact.availability
            is StoryWorkspaceEpisodeArtifactAvailability.INVALID
        )
        assert first.manifest_revision != second.manifest_revision

    def test_unapproved_directory_entry_revision_changes_after_same_size_preserved_mtime_rewrite(
        self,
    ) -> None:
        renders = self.episode / "renders"
        renders.mkdir()
        unapproved = renders / "private.bin"
        unapproved.write_bytes(b"AAAA")
        original = unapproved.stat()
        first = self.read_surface()

        unapproved.write_bytes(b"BBBB")
        os.utime(unapproved, ns=(original.st_atime_ns, original.st_mtime_ns))
        second = self.read_surface()

        renders_fact = next(
            item for item in second.artifacts if item.relative_key == "renders/"
        )
        assert (
            renders_fact.availability
            is StoryWorkspaceEpisodeArtifactAvailability.INVALID
        )
        assert first.manifest_revision != second.manifest_revision

    def test_prompt_count_and_unapproved_render_entry_are_isolated_invalid_roots(self) -> None:
        prompts = self.episode / "prompts"
        prompts.mkdir()
        for index in range(129):
            (prompts / f"p-{index:03d}.yaml").write_text(
                "shots: []\n",
                encoding="utf-8",
            )
        renders = self.episode / "renders"
        renders.mkdir()
        (renders / "private.bin").write_bytes(b"not approved")

        surface = self.read_surface()

        availability = {item.relative_key: item.availability for item in surface.artifacts}
        assert availability["prompts/"] is StoryWorkspaceEpisodeArtifactAvailability.INVALID
        assert availability["renders/"] is StoryWorkspaceEpisodeArtifactAvailability.INVALID
        assert surface.auxiliary is not None
        assert surface.auxiliary.prompts.total == 0
        assert surface.auxiliary.render_guide is None

    @pytest.mark.parametrize(
        "secret",
        [
            "/Users/private/story.txt",
            r"C:\\Users\\private\\story.txt",
            "api_key=sk-proj-abcdefghijklmnopqrstuv",
            "Bearer abcdefghijklmnop",
            "hidden reasoning: private chain",
            "/drama-forge:drama-init --token secret",
            "token: abcdefghijklmnopqrstuvwxyz123456",
        ],
    )
    def test_narrative_sensitive_text_never_crosses_u2_u4_surface(
        self,
        secret: str,
    ) -> None:
        (self.episode / "episode-outline.md").write_text(
            f"# Story Goals\n- {secret}\n",
            encoding="utf-8",
        )

        surface = self.read_surface()
        payload = surface.model_dump_json()

        assert secret not in payload
        outline = next(
            item for item in surface.artifacts if item.relative_key == "episode-outline.md"
        )
        assert outline.availability is StoryWorkspaceEpisodeArtifactAvailability.INVALID


def _create_gateway_schema(db: sqlite3.Connection) -> None:
    db.executescript(
        """
        CREATE TABLE story_workspace_workspaces (id TEXT PRIMARY KEY, owner_id INTEGER);
        CREATE TABLE decks (id TEXT PRIMARY KEY, name TEXT, owner_id INTEGER, enabled INTEGER);
        CREATE TABLE workflow_preflights (
          workflow_preflight_id TEXT PRIMARY KEY, deck_id TEXT, workspace_id TEXT,
          creator_id TEXT, created_by TEXT, deck_plugin_id TEXT,
          deck_plugin_version TEXT, runtime_plugin_lock_id TEXT,
          binding_revision INTEGER, deck_runtime_snapshot_id TEXT
        );
        CREATE TABLE deck_plugin_bindings (
          deck_plugin_binding_id TEXT PRIMARY KEY, deck_id TEXT, workspace_id TEXT,
          creator_id TEXT, deck_plugin_id TEXT, deck_plugin_version TEXT,
          binding_revision INTEGER
        );
        CREATE TABLE workflow_runs (
          id TEXT PRIMARY KEY, workspace_id TEXT, deck_plugin_id TEXT,
          deck_plugin_version TEXT, workflow_definition_ref TEXT,
          deck_runtime_snapshot_id TEXT, deck_plugin_manifest_hash TEXT,
          deck_plugin_binding_id TEXT, binding_revision INTEGER,
          runtime_plugin_lock_id TEXT, workflow_preflight_id TEXT,
          source_voice_thread_id TEXT, source_message_id TEXT,
          created_by TEXT, created_at TEXT
        );
        CREATE TABLE deck_plugin_releases (
          deck_plugin_id TEXT, deck_plugin_version TEXT,
          workflow_definition_ref TEXT, manifest_hash TEXT, manifest_json TEXT
        );
        CREATE TABLE deck_runtime_plugin_locks (
          id TEXT PRIMARY KEY, deck_plugin_id TEXT, deck_plugin_version TEXT,
          deck_plugin_manifest_hash TEXT
        );
        CREATE TABLE deck_runtime_snapshots (
          deck_runtime_snapshot_id TEXT PRIMARY KEY, deck_id TEXT,
          deck_plugin_binding_id TEXT, binding_revision INTEGER
        );
        CREATE TABLE chat_thread (
          id TEXT PRIMARY KEY, user_id INTEGER, deck_id TEXT,
          voice_id TEXT, updated_at TEXT
        );
        CREATE TABLE chat_message (
          id TEXT PRIMARY KEY, thread_id TEXT, role TEXT, parts TEXT,
          metadata TEXT, created_at TEXT
        );
        """
    )


def _seed_authorized_gateway_run(db: sqlite3.Connection) -> None:
    deck = "deck-1"
    plugin = "plugin-1"
    binding = "binding-1"
    snapshot = "snapshot-1"
    lock = "lock-1"
    preflight = "pf-1"
    source = "source-1"
    workflow = "deck://ink.dream/story/1.0.0/workflow.json"
    manifest_hash = "sha256:" + "1" * 64
    db.execute(
        "INSERT INTO story_workspace_workspaces VALUES (?, ?)",
        (WORKSPACE_ID, int(ACTOR_ID)),
    )
    db.execute("INSERT INTO decks VALUES (?, ?, ?, 1)", (deck, "Dream", int(ACTOR_ID)))
    db.execute(
        "INSERT INTO workflow_preflights VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (preflight, deck, WORKSPACE_ID, ACTOR_ID, ACTOR_ID, plugin, "1.0.0", lock, 1, snapshot),
    )
    db.execute(
        "INSERT INTO deck_plugin_bindings VALUES (?, ?, ?, ?, ?, ?, ?)",
        (binding, deck, WORKSPACE_ID, ACTOR_ID, plugin, "1.0.0", 1),
    )
    db.execute(
        "INSERT INTO workflow_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (RUN_ID, WORKSPACE_ID, plugin, "1.0.0", workflow, snapshot, manifest_hash,
         binding, 1, lock, preflight, THREAD_ID, source, ACTOR_ID, "2026-08-05T00:00:00Z"),
    )
    db.execute(
        "INSERT INTO deck_plugin_releases VALUES (?, ?, ?, ?, ?)",
        (plugin, "1.0.0", workflow, manifest_hash, json.dumps({"surfaces": [{"name": "dream"}]})),
    )
    db.execute(
        "INSERT INTO deck_runtime_plugin_locks VALUES (?, ?, ?, ?)",
        (lock, plugin, "1.0.0", manifest_hash),
    )
    db.execute(
        "INSERT INTO deck_runtime_snapshots VALUES (?, ?, ?, ?)",
        (snapshot, deck, binding, 1),
    )
    db.execute(
        "INSERT INTO chat_thread VALUES (?, ?, ?, ?, ?)",
        (THREAD_ID, int(ACTOR_ID), deck, None, "2026-08-05T00:00:00Z"),
    )
    metadata = {
        "kind": "story-workspace-dream-launch",
        "actorId": ACTOR_ID,
        "workspaceId": WORKSPACE_ID,
        "deckId": deck,
        "workflowRunId": RUN_ID,
        "threadId": THREAD_ID,
        "dreamContext": {
            "workflow_run_id": RUN_ID,
            "thread_id": THREAD_ID,
            "deck_id": deck,
            "deck_plugin_id": plugin,
            "deck_plugin_version": "1.0.0",
            "deck_plugin_binding_id": binding,
            "binding_revision": 1,
            "deck_runtime_snapshot_id": snapshot,
            "runtime_plugin_lock_id": lock,
        },
    }
    db.execute(
        "INSERT INTO chat_message VALUES (?, ?, 'user', '[]', ?, ?)",
        (source, THREAD_ID, json.dumps(metadata), "2026-08-05T00:00:00Z"),
    )
    db.commit()


def _set_gateway_episode_authority(
    db: sqlite3.Connection,
    episode_uid: str,
    *,
    authority: dict[str, str] | None = None,
) -> None:
    row = db.execute(
        "SELECT metadata FROM chat_message WHERE id = 'source-1'"
    ).fetchone()
    metadata = json.loads(row[0])
    metadata["story_workspace_episode_identity"] = authority or _episode_authority(
        episode_uid
    )
    db.execute(
        "UPDATE chat_message SET metadata = ? WHERE id = 'source-1'",
        (json.dumps(metadata),),
    )
    db.commit()


def test_gateway_authorizes_full_provenance_before_any_workspace_probe() -> None:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    _create_gateway_schema(db)
    _seed_authorized_gateway_run(db)
    gateway = gateway_module.StoryWorkflowApplicationGateway()

    with patch.object(
        gateway,
        "_thread_workspace",
        side_effect=AssertionError("unauthorized path probe"),
    ) as workspace_probe:
        with pytest.raises(ApiRouteError) as captured:
            gateway._get_episode_artifacts_from_db(
                db,
                RUN_ID,
                {"actor_id": "8"},
            )

    assert captured.value.status_code == 404
    workspace_probe.assert_not_called()
    db.close()


def test_gateway_missing_authority_is_unbound_before_thread_workspace_probe() -> None:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    _create_gateway_schema(db)
    _seed_authorized_gateway_run(db)
    gateway = gateway_module.StoryWorkflowApplicationGateway()

    with patch.object(
        gateway,
        "_thread_workspace",
        side_effect=AssertionError("missing authority must not probe workspace"),
    ) as workspace_probe:
        surface = gateway._get_episode_artifacts_from_db(
            db,
            RUN_ID,
            {"actor_id": ACTOR_ID},
        )

    assert surface.binding_availability is StoryWorkspaceEpisodeBindingAvailability.UNBOUND
    assert surface.artifacts == []
    workspace_probe.assert_not_called()
    db.close()


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE story_workspace_workspaces SET owner_id = 8",
        "UPDATE workflow_runs SET created_by = '8'",
        "UPDATE deck_plugin_bindings SET workspace_id = 'workspace-other'",
        "UPDATE decks SET owner_id = 8",
        "UPDATE chat_thread SET user_id = 8",
        "UPDATE chat_thread SET deck_id = 'deck-other'",
        "UPDATE workflow_preflights SET runtime_plugin_lock_id = 'lock-other'",
        "UPDATE deck_runtime_snapshots SET binding_revision = 9",
        "UPDATE deck_runtime_plugin_locks SET deck_plugin_manifest_hash = 'other'",
        "UPDATE chat_message SET metadata = '{}'",
    ],
)
def test_gateway_hides_every_broken_run_deck_thread_provenance_before_probe(
    mutation: str,
) -> None:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    _create_gateway_schema(db)
    _seed_authorized_gateway_run(db)
    db.execute(mutation)
    db.commit()
    gateway = gateway_module.StoryWorkflowApplicationGateway()

    with patch.object(
        gateway,
        "_thread_workspace",
        side_effect=AssertionError("unauthorized path probe"),
    ) as workspace_probe:
        with pytest.raises(ApiRouteError) as captured:
            gateway._get_episode_artifacts_from_db(
                db,
                RUN_ID,
                {"actor_id": ACTOR_ID},
            )

    assert captured.value.status_code == 404
    workspace_probe.assert_not_called()
    db.close()


def test_gateway_owner_get_reads_bound_episode_after_full_authorization() -> None:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    _create_gateway_schema(db)
    _seed_authorized_gateway_run(db)
    gateway = gateway_module.StoryWorkflowApplicationGateway()
    with tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        workspace = root / THREAD_ID
        (workspace / ".dream").mkdir(parents=True)
        story = workspace / "stories" / "didi-zhengzhou"
        (story / "episodes" / "EP01").mkdir(parents=True)
        (story / "project.yaml").write_text(
            "project_id: didi-zhengzhou\n",
            encoding="utf-8",
        )
        binding = StoryWorkspaceEpisodeBindingService(
            workspace
        ).resolve_or_repair_binding(_binding_context()).binding
        assert binding is not None
        _set_gateway_episode_authority(db, binding.episode_uid)

        with patch.object(gateway, "_thread_workspace", return_value=workspace):
            surface = gateway._get_episode_artifacts_from_db(
                db,
                RUN_ID,
                {"actor_id": ACTOR_ID},
            )

    assert surface.binding_availability is StoryWorkspaceEpisodeBindingAvailability.BOUND
    assert surface.opaque_episode_id == binding.episode_uid
    assert len(surface.artifacts) == 6
    db.close()


def test_real_route_owner_etag_refresh_and_other_actor_invisibility() -> None:
    with tempfile.TemporaryDirectory() as temporary_directory:
        base = Path(temporary_directory)
        db_path = base / "episode-api.db"
        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
        _create_gateway_schema(db)
        _seed_authorized_gateway_run(db)
        db.close()

        root = base / "workspaces"
        workspace = root / THREAD_ID
        (workspace / ".dream").mkdir(parents=True)
        story = workspace / "stories" / "didi-zhengzhou"
        episode = story / "episodes" / "EP01"
        episode.mkdir(parents=True)
        (story / "project.yaml").write_text(
            "project_id: didi-zhengzhou\n",
            encoding="utf-8",
        )
        StoryWorkspaceEpisodeBindingService(workspace).resolve_or_repair_binding(
            _binding_context()
        )
        binding_path = workspace / ".dream" / "runtime" / "runs" / RUN_ID / "episode.json"
        binding_uid = json.loads(binding_path.read_text(encoding="utf-8"))["episode_uid"]
        db = sqlite3.connect(db_path)
        _set_gateway_episode_authority(db, binding_uid)
        db.close()

        app = FastAPI()
        current_actor = {"value": int(ACTOR_ID)}
        app.dependency_overrides[story_workspace.get_current_user] = lambda: {
            "user_id": current_actor["value"],
        }
        app.dependency_overrides[
            story_workspace.get_story_workflow_gateway
        ] = gateway_module.StoryWorkflowApplicationGateway
        app.include_router(story_workspace.router)
        with (
            patch.object(gateway_module.database, "DB_PATH", db_path),
            patch.object(
                gateway_module,
                "story_workspace_get_workspace_root",
                return_value=root,
            ),
            TestClient(app) as client,
        ):
            first = client.get(
                f"/api/story-workspace/workflow-runs/{RUN_ID}/episode-artifacts"
            )
            first_etag = first.headers["etag"]
            unchanged = client.get(
                f"/api/story-workspace/workflow-runs/{RUN_ID}/episode-artifacts",
                headers={"If-None-Match": first_etag},
            )
            (episode / "episode-outline.md").write_text(
                "---\ntitle: Demo\n---\n# Story Goals\n- Begin\n",
                encoding="utf-8",
            )
            changed = client.get(
                f"/api/story-workspace/workflow-runs/{RUN_ID}/episode-artifacts",
                headers={"If-None-Match": first_etag},
            )
            current_actor["value"] = 8
            forbidden = client.get(
                f"/api/story-workspace/workflow-runs/{RUN_ID}/episode-artifacts"
            )

    assert first.status_code == 200
    assert first.json()["bindingAvailability"] == "bound"
    assert unchanged.status_code == 304
    assert unchanged.content == b""
    assert changed.status_code == 200
    assert changed.headers["etag"] != first_etag
    assert forbidden.status_code == 404
    assert forbidden.json()["error"]["code"] == "WORKFLOW_PERMISSION_DENIED"


@pytest.mark.parametrize(
    ("workspace_error", "expected_status"),
    [
        (ApiRouteError("AGENT_EXECUTION_FAILED", status_code=404), 404),
        (ApiRouteError("WORKFLOW_PERMISSION_DENIED", status_code=403), 404),
        (ApiRouteError("DECK_RUNTIME_CONFIG_UNAVAILABLE", status_code=503), 404),
    ],
)
def test_episode_workspace_invisibility_has_one_public_404_boundary(
    workspace_error: ApiRouteError,
    expected_status: int,
) -> None:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    _create_gateway_schema(db)
    _seed_authorized_gateway_run(db)
    _set_gateway_episode_authority(db, "a" * 32)
    gateway = gateway_module.StoryWorkflowApplicationGateway()

    with patch.object(gateway, "_thread_workspace", side_effect=workspace_error):
        with pytest.raises(ApiRouteError) as captured:
            gateway._get_episode_artifacts_from_db(
                db,
                RUN_ID,
                {"actor_id": ACTOR_ID},
            )

    assert captured.value.status_code == expected_status
    assert captured.value.code == "WORKFLOW_PERMISSION_DENIED"
    db.close()
