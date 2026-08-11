"""Project one authorized Episode surface into bounded Story index metadata."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

try:
    from story_workspace.contracts import (
        StoryWorkspaceEpisodeArtifactAvailability,
        StoryWorkspaceEpisodeArtifactSurface,
    )
    from services.story_workspace.episode_artifact_service import (
        StoryWorkspaceEpisodeAuthority,
    )
    from services.story_workspace.episode_binding_service import (
        StoryWorkspaceEpisodeBindingContext,
        StoryWorkspaceEpisodeBindingError,
        StoryWorkspaceEpisodeBindingService,
    )
except ModuleNotFoundError:  # pragma: no cover - repository-root imports.
    from backend.story_workspace.contracts import (
        StoryWorkspaceEpisodeArtifactAvailability,
        StoryWorkspaceEpisodeArtifactSurface,
    )
    from backend.services.story_workspace.episode_artifact_service import (
        StoryWorkspaceEpisodeAuthority,
    )
    from backend.services.story_workspace.episode_binding_service import (
        StoryWorkspaceEpisodeBindingContext,
        StoryWorkspaceEpisodeBindingError,
        StoryWorkspaceEpisodeBindingService,
    )


ARTIFACT_SOURCE_TYPE = "dream_episode"
_RUN_ID_PATTERN = re.compile(r"^run_[0-9a-f]{32}$")
_PROJECT_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_REVISION_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


class ArtifactStoryProjectionError(RuntimeError):
    """Safe projector failure; exception details stay on the server."""

    def __init__(self, code: str, *, retryable: bool) -> None:
        super().__init__(code)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True)
class ArtifactStoryProjection:
    """Internal-only metadata written to ``story_workspace_stories``."""

    story_id: str
    workspace_id: str
    author_id: int
    source_run_id: str
    source_thread_ref: str
    source_project_id: str
    title: str
    episode_count: int
    artifact_manifest_revision: str
    script_revision: str
    script_size_bytes: int
    artifact_status: str = "available"
    # Rolling-release compatibility projection only. PostgreSQL/API truth is
    # artifact_status; the legacy column is dual-written until contract phase.
    artifact_available: bool = True
    artifact_source_type: str = ARTIFACT_SOURCE_TYPE


class ArtifactStoryIndexProjector:
    """Extract metadata only from an already authorized, safely read surface."""

    @staticmethod
    def deterministic_story_id(workspace_id: str, project_id: str) -> str:
        value = (
            "urn:ink-memory:artifact-story:v1:"
            f"{workspace_id}:{project_id}"
        )
        return str(uuid5(NAMESPACE_URL, value))

    @staticmethod
    def _trusted_value(value: Any, attribute: str, mapping_key: str) -> object:
        if hasattr(value, attribute):
            return getattr(value, attribute)
        if isinstance(value, Mapping):
            try:
                return value[mapping_key]
            except KeyError:
                pass
        raise ArtifactStoryProjectionError(
            "story_index_invalid_artifact",
            retryable=False,
        )

    @classmethod
    def project(
        cls,
        *,
        workspace_root: str | Path,
        workflow_run: Any,
        actor_id: int | str,
        thread_id: str,
        episode_authority: object,
        refreshed_surface: StoryWorkspaceEpisodeArtifactSurface,
    ) -> ArtifactStoryProjection:
        """Build one Project Story projection without returning content or paths."""

        try:
            author_id = int(actor_id)
        except (TypeError, ValueError) as exc:
            raise ArtifactStoryProjectionError(
                "story_index_invalid_artifact",
                retryable=False,
            ) from exc
        workspace_id = str(
            cls._trusted_value(workflow_run, "workspace_id", "workspace_id")
        ).strip()
        run_id = str(
            cls._trusted_value(workflow_run, "workflow_run_id", "run_id")
        ).strip()
        if (
            author_id < 1
            or not workspace_id
            or len(workspace_id) > 255
            or _RUN_ID_PATTERN.fullmatch(run_id) is None
            or not isinstance(thread_id, str)
            or not thread_id
            or len(thread_id) > 255
            or Path(thread_id).parts != (thread_id,)
            or thread_id in {".", ".."}
        ):
            raise ArtifactStoryProjectionError(
                "story_index_invalid_artifact",
                retryable=False,
            )

        authority = StoryWorkspaceEpisodeAuthority.parse(
            episode_authority,
            expected_run_id=run_id,
        )
        if authority is None:
            raise ArtifactStoryProjectionError(
                "story_index_invalid_artifact",
                retryable=False,
            )

        try:
            binding_service = StoryWorkspaceEpisodeBindingService(workspace_root)
            project_id = binding_service.read_canonical_project_story_slug(
                authority.story_slug
            )
            if (
                _PROJECT_ID_PATTERN.fullmatch(project_id) is None
                or project_id != authority.story_slug
            ):
                raise ArtifactStoryProjectionError(
                    "story_index_invalid_artifact",
                    retryable=False,
                )
            registry = binding_service.read_episode_registry_read_only(
                StoryWorkspaceEpisodeBindingContext(
                    workflow_run_id=run_id,
                    trusted_project_story_slug=project_id,
                    locked_context_story_slug=authority.story_slug,
                    run_provenance_story_slug=authority.story_slug,
                    episode_uid=authority.episode_uid,
                )
            )
            project_name = binding_service.read_canonical_project_name(project_id)
        except ArtifactStoryProjectionError:
            raise
        except StoryWorkspaceEpisodeBindingError as exc:
            raise ArtifactStoryProjectionError(
                "story_index_invalid_artifact",
                retryable=False,
            ) from exc

        if (
            refreshed_surface.run_id != run_id
            or refreshed_surface.opaque_episode_id != authority.episode_uid
            or refreshed_surface.manifest_revision is None
            or _REVISION_PATTERN.fullmatch(refreshed_surface.manifest_revision) is None
            or registry.workflow_run_id != run_id
            or registry.story_slug != project_id
            or not any(
                entry.episode_uid == authority.episode_uid
                and entry.episode_code == authority.episode_code
                for entry in registry.episodes
            )
            or not 1 <= len(registry.episodes) <= 99
        ):
            raise ArtifactStoryProjectionError(
                "story_index_invalid_artifact",
                retryable=False,
            )

        scripts = [
            artifact
            for artifact in refreshed_surface.artifacts
            if artifact.relative_key == "script.md"
        ]
        if len(scripts) != 1:
            raise ArtifactStoryProjectionError(
                "story_index_invalid_artifact",
                retryable=False,
            )
        script = scripts[0]
        if script.availability is StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED:
            raise ArtifactStoryProjectionError("artifact_missing", retryable=True)
        if script.availability is StoryWorkspaceEpisodeArtifactAvailability.UNAVAILABLE:
            raise ArtifactStoryProjectionError(
                "story_index_write_failed",
                retryable=True,
            )
        if script.availability is not StoryWorkspaceEpisodeArtifactAvailability.AVAILABLE:
            raise ArtifactStoryProjectionError(
                "story_index_invalid_artifact",
                retryable=False,
            )
        if (
            script.content_revision is None
            or _REVISION_PATTERN.fullmatch(script.content_revision) is None
            or script.size is None
            or isinstance(script.size, bool)
            or script.size < 0
        ):
            raise ArtifactStoryProjectionError(
                "story_index_invalid_artifact",
                retryable=False,
            )

        return ArtifactStoryProjection(
            story_id=cls.deterministic_story_id(workspace_id, project_id),
            workspace_id=workspace_id,
            author_id=author_id,
            source_run_id=run_id,
            source_thread_ref=thread_id,
            source_project_id=project_id,
            title=project_name or project_id,
            episode_count=len(registry.episodes),
            artifact_manifest_revision=refreshed_surface.manifest_revision,
            script_revision=script.content_revision,
            script_size_bytes=script.size,
        )


__all__ = [
    "ARTIFACT_SOURCE_TYPE",
    "ArtifactStoryIndexProjector",
    "ArtifactStoryProjection",
    "ArtifactStoryProjectionError",
]
