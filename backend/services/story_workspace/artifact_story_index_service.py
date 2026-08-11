"""Application orchestration for Artifact → PostgreSQL Story indexing."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

try:
    from services.story_workspace.artifact_story_index_projector import (
        ArtifactStoryIndexProjector,
        ArtifactStoryProjection,
        ArtifactStoryProjectionError,
    )
    from services.story_workspace.artifact_story_index_repository import (
        ArtifactStoryIndexRecord,
        ArtifactStoryIndexRepository,
        ArtifactStoryIndexRepositoryError,
        STORY_INDEX_CONFLICT,
        STORY_INDEX_REVISION_CONFLICT,
    )
except ModuleNotFoundError:  # pragma: no cover - repository-root imports.
    from backend.services.story_workspace.artifact_story_index_projector import (
        ArtifactStoryIndexProjector,
        ArtifactStoryProjection,
        ArtifactStoryProjectionError,
    )
    from backend.services.story_workspace.artifact_story_index_repository import (
        ArtifactStoryIndexRecord,
        ArtifactStoryIndexRepository,
        ArtifactStoryIndexRepositoryError,
        STORY_INDEX_CONFLICT,
        STORY_INDEX_REVISION_CONFLICT,
    )


_SAFE_ERROR_CODES = frozenset(
    {
        "story_index_row_missing",
        "story_index_schema_unavailable",
        "story_index_database_unavailable",
        "story_index_write_failed",
        "story_index_conflict",
        "story_index_invalid_artifact",
        "story_index_revision_conflict",
        "artifact_missing",
    }
)


def _canonical_timestamp(value: object | None) -> str | None:
    """Serialize timestamps once, in UTC, for both wire data and ETags."""

    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return str(value) if value is not None else None


@dataclass(frozen=True)
class ArtifactStoryIndexObservation:
    run_id: str
    project_id: str
    story_id: str | None
    status: str
    observed_manifest_revision: str | None
    observed_script_revision: str | None
    indexed_manifest_revision: str | None
    indexed_script_revision: str | None
    episode_count: int
    last_indexed_at: object | None
    error_code: str | None
    retryable: bool
    etag: str

    def public_dict(self) -> dict[str, object]:
        return {
            "runId": self.run_id,
            "projectId": self.project_id,
            "storyId": self.story_id,
            "status": self.status,
            "observedManifestRevision": self.observed_manifest_revision,
            "observedScriptRevision": self.observed_script_revision,
            "indexedManifestRevision": self.indexed_manifest_revision,
            "indexedScriptRevision": self.indexed_script_revision,
            "episodeCount": self.episode_count,
            "lastIndexedAt": _canonical_timestamp(self.last_indexed_at),
            "errorCode": self.error_code,
            "retryable": self.retryable,
            "etag": self.etag,
        }


@dataclass(frozen=True)
class ArtifactStoryIndexSnapshot:
    """One file projection and the exact DB row behind its public ETag."""

    projection: ArtifactStoryProjection
    record: ArtifactStoryIndexRecord | None
    observation: ArtifactStoryIndexObservation


class ArtifactStoryIndexService:
    """Compose safe filesystem projection and transactional repository writes."""

    def __init__(
        self,
        *,
        projector: ArtifactStoryIndexProjector | None = None,
        repository_factory: Callable[[Any], ArtifactStoryIndexRepository]
        | None = None,
    ) -> None:
        self._projector = projector or ArtifactStoryIndexProjector()
        self._repository_factory = repository_factory or ArtifactStoryIndexRepository

    def project(
        self,
        *,
        workspace_root: str | Path,
        workflow_run: Any,
        actor_id: int | str,
        thread_id: str,
        episode_authority: object,
        refreshed_surface: Any,
    ) -> ArtifactStoryProjection:
        return self._projector.project(
            workspace_root=workspace_root,
            workflow_run=workflow_run,
            actor_id=actor_id,
            thread_id=thread_id,
            episode_authority=episode_authority,
            refreshed_surface=refreshed_surface,
        )

    def materialize(
        self,
        *,
        db: Any,
        workspace_root: str | Path,
        workflow_run: Any,
        actor_id: int | str,
        thread_id: str,
        episode_authority: object,
        refreshed_surface: Any,
    ) -> dict[str, object]:
        """Attempt one idempotent DB write without changing file success."""

        try:
            projection = self.project(
                workspace_root=workspace_root,
                workflow_run=workflow_run,
                actor_id=actor_id,
                thread_id=thread_id,
                episode_authority=episode_authority,
                refreshed_surface=refreshed_surface,
            )
        except ArtifactStoryProjectionError as exc:
            return {
                "status": "failed",
                "errorCode": exc.code,
                "retryable": exc.retryable,
            }
        return self.materialize_projection(db=db, projection=projection)

    def materialize_projection(
        self,
        *,
        db: Any,
        projection: ArtifactStoryProjection,
        expected_record: ArtifactStoryIndexRecord | None = None,
        require_expected_record: bool = False,
    ) -> dict[str, object]:
        """Write an already frozen projection, optionally with a locked DB CAS."""

        try:
            repository = self._repository_factory(db)
            if require_expected_record:
                result = repository.upsert(
                    projection,
                    expected_record=expected_record,
                    require_expected_record=True,
                )
            else:
                result = repository.upsert(projection)
        except ArtifactStoryIndexRepositoryError as exc:
            return {
                "status": "failed",
                "errorCode": exc.code,
                "retryable": exc.retryable,
            }
        if result.status in {"conflict", "revision_conflict"}:
            return {
                "status": "conflict",
                "storyId": result.story_id,
                "errorCode": result.error_code
                or (
                    STORY_INDEX_REVISION_CONFLICT
                    if result.status == "revision_conflict"
                    else STORY_INDEX_CONFLICT
                ),
                "retryable": result.retryable,
            }
        return {
            "status": result.status,
            "storyId": result.story_id,
            "errorCode": None,
            "retryable": False,
        }

    @staticmethod
    def _safe_stored_error(value: str | None) -> str | None:
        return value if value in _SAFE_ERROR_CODES else None

    @staticmethod
    def _observation_etag(payload: dict[str, object]) -> str:
        encoded = json.dumps(
            payload,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
            default=str,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(encoded).hexdigest()

    def inspect(
        self,
        *,
        db: Any,
        workspace_root: str | Path,
        workflow_run: Any,
        actor_id: int | str,
        thread_id: str,
        episode_authority: object,
        refreshed_surface: Any,
    ) -> ArtifactStoryIndexObservation:
        """Compare current file revisions with the canonical PostgreSQL row."""

        return self.inspect_snapshot(
            db=db,
            workspace_root=workspace_root,
            workflow_run=workflow_run,
            actor_id=actor_id,
            thread_id=thread_id,
            episode_authority=episode_authority,
            refreshed_surface=refreshed_surface,
        ).observation

    def inspect_snapshot(
        self,
        *,
        db: Any,
        workspace_root: str | Path,
        workflow_run: Any,
        actor_id: int | str,
        thread_id: str,
        episode_authority: object,
        refreshed_surface: Any,
    ) -> ArtifactStoryIndexSnapshot:
        """Project files once and bind that immutable view to its DB observation."""

        projection = self.project(
            workspace_root=workspace_root,
            workflow_run=workflow_run,
            actor_id=actor_id,
            thread_id=thread_id,
            episode_authority=episode_authority,
            refreshed_surface=refreshed_surface,
        )
        return self.inspect_projection(db=db, projection=projection)

    def inspect_projection(
        self,
        *,
        db: Any,
        projection: ArtifactStoryProjection,
    ) -> ArtifactStoryIndexSnapshot:
        """Read DB state for a frozen projection without another filesystem read."""

        record = self._repository_factory(db).find(
            workspace_id=projection.workspace_id,
            source_project_id=projection.source_project_id,
        )
        observation = self._build_observation(projection, record)
        return ArtifactStoryIndexSnapshot(
            projection=projection,
            record=record,
            observation=observation,
        )

    def _build_observation(
        self,
        projection: ArtifactStoryProjection,
        record: ArtifactStoryIndexRecord | None,
    ) -> ArtifactStoryIndexObservation:
        status: str
        error_code: str | None = None
        retryable = False
        identity_conflict = (
            record is not None and record.story_id != projection.story_id
        )
        public_story_id = (
            record.story_id
            if record is not None and not identity_conflict
            else None
        )
        if record is None:
            status = "missing"
            error_code = "story_index_row_missing"
            retryable = True
        elif (
            identity_conflict
            or record.source_thread_ref != projection.source_thread_ref
        ):
            status = "failed"
            error_code = "story_index_conflict"
        elif (
            record.identifier != projection.source_project_id
            or record.title != projection.title
            or record.source_run_id != projection.source_run_id
            or record.episode_count != projection.episode_count
            or record.artifact_manifest_revision
            != projection.artifact_manifest_revision
            or record.script_revision != projection.script_revision
            or record.script_size_bytes != projection.script_size_bytes
        ):
            status = "stale"
            retryable = True
        elif record.artifact_sync_status == "indexed":
            if (
                record.artifact_indexed_at is None
                or record.artifact_sync_error_code is not None
                or record.artifact_status != "available"
                or record.reconcile_version != 1
            ):
                status = "stale"
                retryable = True
            else:
                status = "indexed"
        elif record.artifact_sync_status == "stale":
            status = "stale"
            retryable = True
        elif record.artifact_sync_status == "missing":
            status = "missing"
            error_code = self._safe_stored_error(record.artifact_sync_error_code)
            retryable = True
        else:
            status = "failed"
            error_code = self._safe_stored_error(record.artifact_sync_error_code)
            if error_code is None:
                error_code = "story_index_write_failed"
            retryable = error_code != "story_index_conflict"

        projected_state: dict[str, object] = {
            "storyId": projection.story_id,
            "workspaceId": projection.workspace_id,
            "authorId": projection.author_id,
            "sourceRunId": projection.source_run_id,
            "sourceThreadRef": projection.source_thread_ref,
            "sourceProjectId": projection.source_project_id,
            "title": projection.title,
            "episodeCount": projection.episode_count,
            "artifactManifestRevision": projection.artifact_manifest_revision,
            "scriptRevision": projection.script_revision,
            "scriptSizeBytes": projection.script_size_bytes,
            "artifactStatus": projection.artifact_status,
            "artifactSourceType": projection.artifact_source_type,
        }
        indexed_state: dict[str, object] | None = None
        if record is not None:
            # This exact internal snapshot is hashed, never serialized.  It
            # keeps If-Match sensitive to every field reconcile may replace.
            indexed_state = {
                "storyId": record.story_id,
                "identifier": record.identifier,
                "title": record.title,
                "workspaceId": record.workspace_id,
                "sourceRunId": record.source_run_id,
                "sourceThreadRef": record.source_thread_ref,
                "sourceProjectId": record.source_project_id,
                "artifactManifestRevision": record.artifact_manifest_revision,
                "scriptRevision": record.script_revision,
                "artifactSyncStatus": record.artifact_sync_status,
                "artifactIndexedAt": _canonical_timestamp(
                    record.artifact_indexed_at
                ),
                "artifactSyncErrorCode": record.artifact_sync_error_code,
                "episodeCount": record.episode_count,
                "scriptSizeBytes": record.script_size_bytes,
                "artifactStatus": record.artifact_status,
                "reconcileVersion": record.reconcile_version,
            }
        etag_payload: dict[str, object] = {
            "projected": projected_state,
            "indexed": indexed_state,
            "status": status,
            "errorCode": error_code,
            "retryable": retryable,
        }
        return ArtifactStoryIndexObservation(
            run_id=projection.source_run_id,
            project_id=projection.source_project_id,
            story_id=public_story_id,
            status=status,
            observed_manifest_revision=projection.artifact_manifest_revision,
            observed_script_revision=projection.script_revision,
            indexed_manifest_revision=(
                record.artifact_manifest_revision if record is not None else None
            ),
            indexed_script_revision=(
                record.script_revision if record is not None else None
            ),
            episode_count=projection.episode_count,
            last_indexed_at=(record.artifact_indexed_at if record is not None else None),
            error_code=error_code,
            retryable=retryable,
            etag=self._observation_etag(etag_payload),
        )


__all__ = [
    "ArtifactStoryIndexObservation",
    "ArtifactStoryIndexService",
    "ArtifactStoryIndexSnapshot",
]
