"""Focused, filesystem-safe tests for the Artifact Story index projector."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid5

import pytest

from services.story_workspace.artifact_story_index_projector import (
    ArtifactStoryIndexProjector,
    ArtifactStoryProjectionError,
)
from services.story_workspace.episode_artifact_adapter import (
    STORY_WORKSPACE_EPISODE_MARKDOWN_MAX_BYTES,
)
from services.story_workspace.episode_artifact_service import (
    StoryWorkspaceEpisodeArtifactPathError,
    StoryWorkspaceEpisodeArtifactService,
)
from services.story_workspace.episode_binding_service import (
    StoryWorkspaceEpisodeBindingContext,
    StoryWorkspaceEpisodeBindingService,
)
from story_workspace.contracts import StoryWorkspaceEpisodeArtifactAvailability


RUN_ID = "run_0123456789abcdef0123456789abcdef"
WORKSPACE_ID = "workspace-projector-tests"
THREAD_ID = "thread-projector-tests"
PROJECT_ID = "safe-project"
ACTOR_ID = 17

VALID_SCRIPT = (
    b"---\n"
    b"title: Safe Episode\n"
    b"episode: 1\n"
    b"---\n"
    b"# Safe Episode\n\n"
    b"S01. Studio [scene-studio] - Day - Interior\n\n"
    b"[The author opens a notebook.]\n"
)


@dataclass
class _ProjectorCase:
    shared_root: Path
    workspace: Path
    story: Path
    episode: Path
    context: StoryWorkspaceEpisodeBindingContext
    binding_service: StoryWorkspaceEpisodeBindingService
    artifact_service: StoryWorkspaceEpisodeArtifactService
    authority: dict[str, str]
    workflow_run: SimpleNamespace

    @property
    def script(self) -> Path:
        return self.episode / "script.md"

    def write_script(self, payload: bytes = VALID_SCRIPT) -> bytes:
        self.script.write_bytes(payload)
        return payload

    def read_surface(self):
        return self.artifact_service.read_surface(
            RUN_ID,
            episode_authority=self.authority,
        )

    def project(self, *, surface=None):
        return ArtifactStoryIndexProjector().project(
            workspace_root=self.workspace,
            workflow_run=self.workflow_run,
            actor_id=ACTOR_ID,
            thread_id=THREAD_ID,
            episode_authority=self.authority,
            refreshed_surface=surface if surface is not None else self.read_surface(),
        )


@pytest.fixture
def projector_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> _ProjectorCase:
    """Every Artifact test uses a private shared root through ``AGENT_CWD``."""

    shared_root = tmp_path / "shared-artifact-root"
    workspace = shared_root / THREAD_ID
    episode = workspace / "stories" / PROJECT_ID / "episodes" / "EP01"
    episode.mkdir(parents=True)
    (workspace / ".dream").mkdir()
    story = episode.parents[1]
    (story / "project.yaml").write_text(
        "project_id: safe-project\nproject_name: Safe Project\n"
        "format:\n  total_episodes: 99\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENT_CWD", str(shared_root))

    context = StoryWorkspaceEpisodeBindingContext(
        workflow_run_id=RUN_ID,
        trusted_project_story_slug=PROJECT_ID,
        locked_context_story_slug=PROJECT_ID,
        run_provenance_story_slug=PROJECT_ID,
    )
    binding_service = StoryWorkspaceEpisodeBindingService(workspace)
    binding = binding_service.resolve_or_repair_binding(context).binding
    assert binding is not None
    authority = {
        "schema": "story-workspace-episode-authority/v1",
        "workflow_run_id": RUN_ID,
        "episode_uid": binding.episode_uid,
        "story_slug": PROJECT_ID,
        "episode_code": "EP01",
    }
    return _ProjectorCase(
        shared_root=shared_root,
        workspace=workspace,
        story=story,
        episode=episode,
        context=context,
        binding_service=binding_service,
        artifact_service=StoryWorkspaceEpisodeArtifactService(workspace),
        authority=authority,
        workflow_run=SimpleNamespace(
            workflow_run_id=RUN_ID,
            workspace_id=WORKSPACE_ID,
        ),
    )


def test_deterministic_story_id_uses_the_frozen_uuid5_seed() -> None:
    expected = str(
        uuid5(
            NAMESPACE_URL,
            "urn:ink-memory:artifact-story:v1:workspace-projector-tests:safe-project",
        )
    )

    assert (
        ArtifactStoryIndexProjector.deterministic_story_id(
            WORKSPACE_ID,
            PROJECT_ID,
        )
        == expected
    )
    assert (
        ArtifactStoryIndexProjector.deterministic_story_id(
            WORKSPACE_ID,
            PROJECT_ID,
        )
        == expected
    )


def test_projects_only_bounded_metadata_and_actual_registry_count(
    projector_case: _ProjectorCase,
) -> None:
    first = projector_case.binding_service.read_episode_registry(
        projector_case.context
    )
    registry = projector_case.binding_service.ensure_next_episode(
        projector_case.context,
        expected_revision=first.revision,
        total_episodes=3,
    )
    (projector_case.story / "episodes" / "EP02").mkdir()
    script = projector_case.write_script()

    projection = projector_case.project()

    assert projection.workspace_id == WORKSPACE_ID
    assert projection.author_id == ACTOR_ID
    assert projection.source_run_id == RUN_ID
    assert projection.source_thread_ref == THREAD_ID
    assert projection.source_project_id == PROJECT_ID
    assert projection.title == "Safe Project"
    assert projection.episode_count == len(registry.episodes) == 2
    assert projection.script_revision == "sha256:" + hashlib.sha256(script).hexdigest()
    assert projection.script_size_bytes == len(script)
    assert projection.artifact_status == "available"
    assert projection.artifact_available is True
    assert projection.artifact_manifest_revision.startswith("sha256:")
    assert projection.story_id == ArtifactStoryIndexProjector.deterministic_story_id(
        WORKSPACE_ID,
        PROJECT_ID,
    )
    assert set(asdict(projection)) == {
        "story_id",
        "workspace_id",
        "author_id",
        "source_run_id",
        "source_thread_ref",
        "source_project_id",
        "title",
        "episode_count",
        "artifact_manifest_revision",
        "script_revision",
        "script_size_bytes",
        "artifact_status",
        "artifact_available",
        "artifact_source_type",
    }


@pytest.mark.parametrize(
    "project_yaml",
    [
        "project_id: safe-project\n",
        "project_id: safe-project\nproject_name: /Users/private/internal-story\n",
        "project_id: safe-project\nproject_name: stories/private/internal-story\n",
        "project_id: safe-project\nproject_name: C:\\\\private\\\\internal-story\n",
        "project_id: safe-project\nproject_name: First\nproject_name: Second\n",
        "project_id: safe-project\nproject_name: Bearer abcdefghijklmnop\n",
    ],
)
def test_unsafe_or_ambiguous_project_name_falls_back_to_project_id(
    projector_case: _ProjectorCase,
    project_yaml: str,
) -> None:
    projector_case.story.joinpath("project.yaml").write_text(
        project_yaml,
        encoding="utf-8",
    )
    projector_case.write_script()

    assert projector_case.project().title == PROJECT_ID


def test_missing_script_is_retryable_artifact_missing(
    projector_case: _ProjectorCase,
) -> None:
    surface = projector_case.read_surface()
    script = next(item for item in surface.artifacts if item.relative_key == "script.md")
    assert script.availability is StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED

    with pytest.raises(ArtifactStoryProjectionError) as raised:
        projector_case.project(surface=surface)

    assert raised.value.code == "artifact_missing"
    assert raised.value.retryable is True


@pytest.mark.parametrize(
    "payload",
    [
        b"\xff\xfe\xfd",
        b"x" * (STORY_WORKSPACE_EPISODE_MARKDOWN_MAX_BYTES + 1),
    ],
    ids=["invalid-utf8", "oversize"],
)
def test_invalid_or_oversize_script_fails_closed(
    projector_case: _ProjectorCase,
    payload: bytes,
) -> None:
    projector_case.write_script(payload)
    surface = projector_case.read_surface()
    script = next(item for item in surface.artifacts if item.relative_key == "script.md")
    assert script.availability is StoryWorkspaceEpisodeArtifactAvailability.INVALID

    with pytest.raises(ArtifactStoryProjectionError) as raised:
        projector_case.project(surface=surface)

    assert raised.value.code == "story_index_invalid_artifact"
    assert raised.value.retryable is False


def test_traversal_authority_is_rejected_before_projection(
    projector_case: _ProjectorCase,
) -> None:
    projector_case.write_script()
    surface = projector_case.read_surface()
    traversal = dict(projector_case.authority, story_slug="../safe-project")

    with pytest.raises(ArtifactStoryProjectionError) as raised:
        ArtifactStoryIndexProjector().project(
            workspace_root=projector_case.workspace,
            workflow_run=projector_case.workflow_run,
            actor_id=ACTOR_ID,
            thread_id=THREAD_ID,
            episode_authority=traversal,
            refreshed_surface=surface,
        )

    assert raised.value.code == "story_index_invalid_artifact"


def test_script_symlink_escape_is_stopped_by_the_reused_artifact_service(
    projector_case: _ProjectorCase,
) -> None:
    outside = projector_case.shared_root / "outside-script.md"
    outside.write_bytes(VALID_SCRIPT + b"\nPRIVATE\n")
    projector_case.script.symlink_to(outside)

    with pytest.raises(StoryWorkspaceEpisodeArtifactPathError):
        projector_case.read_surface()


def test_workspace_inode_swap_between_safe_reads_fails_closed(
    projector_case: _ProjectorCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    projector_case.write_script()
    surface = projector_case.read_surface()
    original_read = StoryWorkspaceEpisodeBindingService.read_canonical_project_story_slug
    swapped = False

    def read_then_swap(service: StoryWorkspaceEpisodeBindingService, slug: str) -> str:
        nonlocal swapped
        result = original_read(service, slug)
        if not swapped:
            swapped = True
            moved = projector_case.shared_root / "original-thread-workspace"
            projector_case.workspace.rename(moved)
            projector_case.workspace.mkdir()
        return result

    monkeypatch.setattr(
        StoryWorkspaceEpisodeBindingService,
        "read_canonical_project_story_slug",
        read_then_swap,
    )

    with pytest.raises(ArtifactStoryProjectionError) as raised:
        projector_case.project(surface=surface)

    assert raised.value.code == "story_index_invalid_artifact"
    assert raised.value.retryable is False


def test_projector_uses_the_no_create_registry_reader(
    projector_case: _ProjectorCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    projector_case.write_script()
    surface = projector_case.read_surface()

    def forbidden_locking_read(*_args, **_kwargs):
        raise AssertionError("projector must not create or lock registry paths")

    monkeypatch.setattr(
        StoryWorkspaceEpisodeBindingService,
        "read_episode_registry",
        forbidden_locking_read,
    )

    projection = projector_case.project(surface=surface)

    assert projection.episode_count == 1
