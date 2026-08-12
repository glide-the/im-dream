"""Bounded, read-only reconciliation for Dream Artifact Story indexes.

The first version deliberately has no apply path.  PostgreSQL is the starting
point for both directions: Run candidates are relation-checked and fully
authorized before a thread workspace is resolved, while existing Story rows
are re-authorized through their source Run before their internal locator is
used.  The shared Artifact root is never scanned.
"""

from __future__ import annotations

import base64
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal, Mapping

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
        STORY_INDEX_DATABASE_UNAVAILABLE,
        STORY_INDEX_SCHEMA_UNAVAILABLE,
    )
    from services.story_workspace.dream_reentry_service import (
        StoryWorkspaceDreamReentryService,
    )
    from services.story_workspace.episode_artifact_service import (
        StoryWorkspaceEpisodeArtifactService,
        StoryWorkspaceEpisodeAuthority,
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
        STORY_INDEX_DATABASE_UNAVAILABLE,
        STORY_INDEX_SCHEMA_UNAVAILABLE,
    )
    from backend.services.story_workspace.dream_reentry_service import (
        StoryWorkspaceDreamReentryService,
    )
    from backend.services.story_workspace.episode_artifact_service import (
        StoryWorkspaceEpisodeArtifactService,
        StoryWorkspaceEpisodeAuthority,
    )


_RUN_ID_PATTERN = re.compile(r"^run_[0-9a-f]{32}$")
_SAFE_SCOPE_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,255}$")
_CURSOR_VERSION = 1
_MAX_CURSOR_BYTES = 2048
_DEFAULT_LIMIT = 100
_MAX_LIMIT = 500
_DEFAULT_DEADLINE_SECONDS = 10.0
ReconcilePhase = Literal["runs", "stories"]
DatabaseStatus = Literal["available", "schema_unavailable", "unavailable"]


@dataclass(frozen=True)
class ArtifactStoryIndexRunCandidate:
    """One bounded DB-first candidate; it is not yet fully authorized."""

    run_id: str
    workspace_id: str
    created_by: str | None
    actor_id: int | None
    related_workspace_id: str | None
    actor_user_id: int | None
    thread_id: str | None
    source_message_id: str | None
    source_role: str | None

    @property
    def base_relations_complete(self) -> bool:
        return (
            self.actor_id is not None
            and self.actor_id > 0
            and self.related_workspace_id == self.workspace_id
            and self.actor_user_id == self.actor_id
            and self.created_by == str(self.actor_id)
            and isinstance(self.thread_id, str)
            and bool(self.thread_id)
            and isinstance(self.source_message_id, str)
            and bool(self.source_message_id)
            and self.source_role == "user"
        )


@dataclass(frozen=True)
class ArtifactStoryIndexReconcileCursor:
    phase: ReconcilePhase = "runs"
    after: str | None = None
    workspace_id: str | None = None
    run_id: str | None = None


def _urlsafe_encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _urlsafe_decode(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode(value + padding)


def encode_reconcile_cursor(cursor: ArtifactStoryIndexReconcileCursor) -> str:
    payload = {
        "after": cursor.after,
        "phase": cursor.phase,
        "runId": cursor.run_id,
        "v": _CURSOR_VERSION,
        "workspaceId": cursor.workspace_id,
    }
    return _urlsafe_encode(
        json.dumps(
            payload,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )


def decode_reconcile_cursor(
    value: str | None,
    *,
    workspace_id: str | None,
    run_id: str | None,
) -> ArtifactStoryIndexReconcileCursor:
    if value is None:
        return ArtifactStoryIndexReconcileCursor(
            workspace_id=workspace_id,
            run_id=run_id,
        )
    if not isinstance(value, str) or not value or len(value) > _MAX_CURSOR_BYTES:
        raise ValueError("story index reconcile cursor is invalid")
    try:
        payload = json.loads(_urlsafe_decode(value))
    except (ValueError, TypeError, json.JSONDecodeError):
        raise ValueError("story index reconcile cursor is invalid") from None
    if not isinstance(payload, dict) or set(payload) != {
        "after",
        "phase",
        "runId",
        "v",
        "workspaceId",
    }:
        raise ValueError("story index reconcile cursor is invalid")
    phase = payload.get("phase")
    after = payload.get("after")
    if (
        payload.get("v") != _CURSOR_VERSION
        or phase not in {"runs", "stories"}
        or (after is not None and (
            not isinstance(after, str)
            or _SAFE_SCOPE_PATTERN.fullmatch(after) is None
        ))
        or payload.get("workspaceId") != workspace_id
        or payload.get("runId") != run_id
    ):
        raise ValueError("story index reconcile cursor is invalid")
    return ArtifactStoryIndexReconcileCursor(
        phase=phase,
        after=after,
        workspace_id=workspace_id,
        run_id=run_id,
    )


@dataclass(frozen=True)
class ArtifactStoryIndexReconcileReport:
    projects_discovered: int = 0
    episodes_discovered: int = 0
    stories_indexable: int = 0
    indexes_existing: int = 0
    indexes_to_create: int = 0
    indexes_to_update: int = 0
    indexes_unchanged: int = 0
    conflicts: int = 0
    invalid_artifacts: int = 0
    missing_relations: int = 0
    database_status: DatabaseStatus = "available"
    applied: Literal[False] = False
    next_cursor: str | None = None

    def public_dict(self) -> dict[str, object]:
        return {
            "projects_discovered": self.projects_discovered,
            "episodes_discovered": self.episodes_discovered,
            "stories_indexable": self.stories_indexable,
            "indexes_existing": self.indexes_existing,
            "indexes_to_create": self.indexes_to_create,
            "indexes_to_update": self.indexes_to_update,
            "indexes_unchanged": self.indexes_unchanged,
            "conflicts": self.conflicts,
            "invalid_artifacts": self.invalid_artifacts,
            "missing_relations": self.missing_relations,
            "database_status": self.database_status,
            "applied": False,
            "next_cursor": self.next_cursor,
        }

    @classmethod
    def database_failure(
        cls,
        status: Literal["schema_unavailable", "unavailable"],
    ) -> "ArtifactStoryIndexReconcileReport":
        return cls(database_status=status)


class ArtifactStoryIndexReconcileRepository:
    """Read-only PostgreSQL access for the two reconcile directions."""

    def __init__(self, db: Any) -> None:
        self.db = db
        self.index_repository = ArtifactStoryIndexRepository(db)

    def require_schema(self) -> None:
        self.index_repository.require_schema()

    @staticmethod
    def _candidate(row: Mapping[str, object]) -> ArtifactStoryIndexRunCandidate:
        actor = row["actor_id"]
        actor_user = row["actor_user_id"]
        return ArtifactStoryIndexRunCandidate(
            run_id=str(row["run_id"]),
            workspace_id=str(row["workspace_id"]),
            created_by=(
                str(row["created_by"])
                if row["created_by"] is not None
                else None
            ),
            actor_id=int(actor) if actor is not None else None,
            related_workspace_id=(
                str(row["related_workspace_id"])
                if row["related_workspace_id"] is not None
                else None
            ),
            actor_user_id=(int(actor_user) if actor_user is not None else None),
            thread_id=(
                str(row["relation_thread_id"])
                if row["relation_thread_id"] is not None
                else None
            ),
            source_message_id=(
                str(row["relation_source_id"])
                if row["relation_source_id"] is not None
                else None
            ),
            source_role=(
                str(row["source_role"])
                if row["source_role"] is not None
                else None
            ),
        )

    def list_run_candidates(
        self,
        *,
        workspace_id: str | None,
        run_id: str | None,
        after: str | None,
        limit: int,
    ) -> list[ArtifactStoryIndexRunCandidate]:
        conditions = ["TRUE"]
        parameters: list[object] = []
        if workspace_id is not None:
            conditions.append("run.workspace_id = %s")
            parameters.append(workspace_id)
        if run_id is not None:
            conditions.append("run.id = %s")
            parameters.append(run_id)
        if after is not None:
            conditions.append("run.id > %s")
            parameters.append(after)
        parameters.append(limit)
        try:
            rows = self.db.execute(
                "SELECT run.id AS run_id, run.workspace_id AS workspace_id, "
                "run.created_by AS created_by, workspace.id AS related_workspace_id, "
                "workspace.owner_id AS actor_id, actor.id AS actor_user_id, "
                "thread.id AS relation_thread_id, source.id AS relation_source_id, "
                "source.role AS source_role "
                "FROM workflow_runs AS run "
                "LEFT JOIN story_workspace_workspaces AS workspace "
                "ON workspace.id = run.workspace_id "
                "LEFT JOIN users AS actor ON actor.id = workspace.owner_id "
                "LEFT JOIN chat_thread AS thread "
                "ON thread.id = run.source_voice_thread_id "
                "AND thread.user_id = workspace.owner_id "
                "LEFT JOIN chat_message AS source "
                "ON source.id = run.source_message_id "
                "AND source.thread_id = thread.id "
                f"WHERE {' AND '.join(conditions)} "
                "ORDER BY run.id ASC LIMIT %s",
                tuple(parameters),
            ).fetchall()
        except Exception as exc:
            raise ArtifactStoryIndexRepositoryError(
                STORY_INDEX_DATABASE_UNAVAILABLE,
                retryable=True,
            ) from exc
        return [self._candidate(row) for row in rows]

    def authorize_run(
        self,
        candidate: ArtifactStoryIndexRunCandidate,
    ) -> Mapping[str, object] | None:
        if not candidate.base_relations_complete or candidate.actor_id is None:
            return None
        try:
            rows = StoryWorkspaceDreamReentryService._query_authorized_rows(
                self.db,
                candidate.actor_id,
                workflow_run_id=candidate.run_id,
                limit=2,
            )
        except Exception as exc:
            raise ArtifactStoryIndexRepositoryError(
                STORY_INDEX_DATABASE_UNAVAILABLE,
                retryable=True,
            ) from exc
        if len(rows) != 1:
            return None
        row = rows[0]
        if (
            str(row["run_id"]) != candidate.run_id
            or str(row["workspace_id"]) != candidate.workspace_id
            or not StoryWorkspaceDreamReentryService._source_metadata_matches(
                row["source_metadata"],
                actor_id=candidate.actor_id,
                workspace_id=str(row["workspace_id"]),
                run_id=str(row["run_id"]),
                thread_id=str(row["thread_id"]),
                thread_agent_id=row["thread_voice_id"],
                deck_id=str(row["deck_id"]),
                deck_plugin_id=str(row["deck_plugin_id"]),
                deck_plugin_version=str(row["deck_plugin_version"]),
                binding_id=str(row["binding_id"]),
                binding_revision=int(row["binding_revision"]),
                runtime_snapshot_id=str(row["deck_runtime_snapshot_id"]),
                runtime_lock_id=str(row["runtime_plugin_lock_id"]),
            )
        ):
            return None
        return row

    def find_index(
        self,
        *,
        workspace_id: str,
        project_id: str,
    ) -> ArtifactStoryIndexRecord | None:
        return self.index_repository.find(
            workspace_id=workspace_id,
            source_project_id=project_id,
        )

    def list_story_records(
        self,
        *,
        workspace_id: str | None,
        run_id: str | None,
        after: str | None,
        limit: int,
    ) -> list[ArtifactStoryIndexRecord]:
        records = self.index_repository.list_records(
            workspace_id=workspace_id,
            limit=limit,
            cursor=after,
            source_run_id=run_id,
        )
        return records


@dataclass
class _ReconcileAccumulator:
    projects: set[tuple[str, str]] = field(default_factory=set)
    episode_counts: dict[tuple[str, str], int] = field(default_factory=dict)
    indexable: set[tuple[str, str]] = field(default_factory=set)
    existing: set[str] = field(default_factory=set)
    to_create: set[tuple[str, str]] = field(default_factory=set)
    to_update: set[tuple[str, str]] = field(default_factory=set)
    unchanged: set[tuple[str, str]] = field(default_factory=set)
    conflicts: set[tuple[str, str]] = field(default_factory=set)
    invalid: set[str] = field(default_factory=set)
    missing: set[str] = field(default_factory=set)
    thread_by_project: dict[tuple[str, str], str] = field(default_factory=dict)

    @staticmethod
    def key(projection: ArtifactStoryProjection) -> tuple[str, str]:
        return (projection.workspace_id, projection.source_project_id)

    def observe_projection(self, projection: ArtifactStoryProjection) -> bool:
        key = self.key(projection)
        self.projects.add(key)
        self.indexable.add(key)
        self.episode_counts[key] = max(
            projection.episode_count,
            self.episode_counts.get(key, 0),
        )
        previous_thread = self.thread_by_project.setdefault(
            key,
            projection.source_thread_ref,
        )
        if previous_thread != projection.source_thread_ref:
            self.mark_conflict(key)
            return False
        return key not in self.conflicts

    def mark_conflict(self, key: tuple[str, str]) -> None:
        self.conflicts.add(key)
        self.to_create.discard(key)
        self.to_update.discard(key)
        self.unchanged.discard(key)

    def mark_create(self, key: tuple[str, str]) -> None:
        if key not in self.conflicts and key not in self.to_update:
            self.unchanged.discard(key)
            self.to_create.add(key)

    def mark_update(self, key: tuple[str, str]) -> None:
        if key not in self.conflicts:
            self.to_create.discard(key)
            self.unchanged.discard(key)
            self.to_update.add(key)

    def mark_unchanged(self, key: tuple[str, str]) -> None:
        if (
            key not in self.conflicts
            and key not in self.to_create
            and key not in self.to_update
        ):
            self.unchanged.add(key)

    def report(
        self,
        *,
        next_cursor: str | None,
    ) -> ArtifactStoryIndexReconcileReport:
        return ArtifactStoryIndexReconcileReport(
            projects_discovered=len(self.projects),
            episodes_discovered=sum(self.episode_counts.values()),
            stories_indexable=len(self.indexable),
            indexes_existing=len(self.existing),
            indexes_to_create=len(self.to_create),
            indexes_to_update=len(self.to_update),
            indexes_unchanged=len(self.unchanged),
            conflicts=len(self.conflicts),
            invalid_artifacts=len(self.invalid),
            missing_relations=len(self.missing),
            next_cursor=next_cursor,
        )


class ArtifactStoryIndexReconcileService:
    """Dry-run both directions with a global per-call limit and deadline."""

    def __init__(
        self,
        *,
        repository_factory: Callable[[Any], ArtifactStoryIndexReconcileRepository]
        | None = None,
        projector: ArtifactStoryIndexProjector | None = None,
        workspace_resolver: Callable[[str], Path] | None = None,
        surface_reader: Callable[[Path, str, StoryWorkspaceEpisodeAuthority], Any]
        | None = None,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._repository_factory = (
            repository_factory or ArtifactStoryIndexReconcileRepository
        )
        self._projector = projector or ArtifactStoryIndexProjector()
        self._workspace_resolver = workspace_resolver or self._resolve_thread_workspace
        self._surface_reader = surface_reader or self._read_surface
        self._monotonic = monotonic

    @staticmethod
    def _resolve_thread_workspace(thread_id: str) -> Path:
        try:
            from services.deck.story_workflow_application import (
                DreamArtifactApplicationService,
            )
        except ModuleNotFoundError:  # pragma: no cover - repository-root imports.
            from backend.services.deck.story_workflow_application import (
                DreamArtifactApplicationService,
            )
        return DreamArtifactApplicationService._thread_workspace(thread_id)

    @staticmethod
    def _read_surface(
        workspace: Path,
        run_id: str,
        authority: StoryWorkspaceEpisodeAuthority,
    ) -> Any:
        return StoryWorkspaceEpisodeArtifactService(workspace).read_surface(
            run_id,
            episode_authority=authority,
        )

    @staticmethod
    def _authority(row: Mapping[str, object]) -> StoryWorkspaceEpisodeAuthority | None:
        raw = row["source_metadata"]
        try:
            metadata = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, ValueError):
            return None
        if not isinstance(metadata, Mapping):
            return None
        return StoryWorkspaceEpisodeAuthority.parse(
            metadata.get("story_workspace_episode_identity"),
            expected_run_id=str(row["run_id"]),
        )

    def _project(
        self,
        row: Mapping[str, object],
        actor_id: int,
    ) -> ArtifactStoryProjection | None:
        authority = self._authority(row)
        if authority is None:
            return None
        thread_id = str(row["thread_id"])
        workspace = self._workspace_resolver(thread_id)
        surface = self._surface_reader(workspace, str(row["run_id"]), authority)
        return self._projector.project(
            workspace_root=workspace,
            workflow_run=row,
            actor_id=actor_id,
            thread_id=thread_id,
            episode_authority=authority,
            refreshed_surface=surface,
        )

    @staticmethod
    def _record_needs_update(
        record: ArtifactStoryIndexRecord,
        projection: ArtifactStoryProjection,
    ) -> bool:
        return (
            record.identifier != projection.source_project_id
            or record.title != projection.title
            or record.source_run_id != projection.source_run_id
            or record.artifact_manifest_revision != projection.artifact_manifest_revision
            or record.script_revision != projection.script_revision
            or record.episode_count != projection.episode_count
            or record.script_size_bytes != projection.script_size_bytes
            or record.artifact_sync_status != "indexed"
            or record.artifact_indexed_at is None
            or record.artifact_sync_error_code is not None
            or record.artifact_available is not True
            or record.reconcile_version != 1
        )

    def _process_run_candidate(
        self,
        repository: ArtifactStoryIndexReconcileRepository,
        candidate: ArtifactStoryIndexRunCandidate,
        accumulator: _ReconcileAccumulator,
    ) -> None:
        row = repository.authorize_run(candidate)
        if row is None or candidate.actor_id is None:
            accumulator.missing.add(candidate.run_id)
            return
        if self._authority(row) is None:
            accumulator.missing.add(candidate.run_id)
            return
        try:
            projection = self._project(row, candidate.actor_id)
        except ArtifactStoryProjectionError:
            accumulator.invalid.add(candidate.run_id)
            return
        except Exception:
            accumulator.invalid.add(candidate.run_id)
            return
        if projection is None:
            accumulator.missing.add(candidate.run_id)
            return
        key = accumulator.key(projection)
        if not accumulator.observe_projection(projection):
            return
        record = repository.find_index(
            workspace_id=projection.workspace_id,
            project_id=projection.source_project_id,
        )
        if record is None:
            accumulator.mark_create(key)
            return
        accumulator.existing.add(record.story_id)
        if (
            record.story_id != projection.story_id
            or record.source_thread_ref != projection.source_thread_ref
        ):
            accumulator.mark_conflict(key)
        elif self._record_needs_update(record, projection):
            accumulator.mark_update(key)
        else:
            accumulator.mark_unchanged(key)

    def _process_story_record(
        self,
        repository: ArtifactStoryIndexReconcileRepository,
        record: ArtifactStoryIndexRecord,
        accumulator: _ReconcileAccumulator,
    ) -> None:
        accumulator.existing.add(record.story_id)
        key = (record.workspace_id, record.source_project_id)
        source_run_id = record.source_run_id
        if source_run_id is None or _RUN_ID_PATTERN.fullmatch(source_run_id) is None:
            accumulator.missing.add(record.story_id)
            return
        candidates = repository.list_run_candidates(
            workspace_id=record.workspace_id,
            run_id=source_run_id,
            after=None,
            limit=2,
        )
        if len(candidates) != 1:
            accumulator.missing.add(record.story_id)
            return
        candidate = candidates[0]
        row = repository.authorize_run(candidate)
        authority = self._authority(row) if row is not None else None
        if row is None or authority is None or candidate.actor_id is None:
            accumulator.missing.add(record.story_id)
            return
        trusted_thread = str(row["thread_id"])
        if (
            trusted_thread != record.source_thread_ref
            or authority.story_slug != record.source_project_id
        ):
            accumulator.mark_conflict(key)
            return
        previous_thread = accumulator.thread_by_project.setdefault(
            key,
            trusted_thread,
        )
        if previous_thread != trusted_thread:
            accumulator.mark_conflict(key)
            return
        try:
            projection = self._project(row, candidate.actor_id)
        except ArtifactStoryProjectionError:
            accumulator.invalid.add(record.story_id)
            return
        except Exception:
            accumulator.invalid.add(record.story_id)
            return
        if projection is None:
            accumulator.missing.add(record.story_id)
            return
        if (
            projection.story_id != record.story_id
            or accumulator.key(projection) != key
        ):
            accumulator.mark_conflict(key)
            return
        accumulator.observe_projection(projection)
        if self._record_needs_update(record, projection):
            accumulator.mark_update(key)
        else:
            accumulator.mark_unchanged(key)

    @staticmethod
    def _validate_scope(
        *,
        workspace_id: str | None,
        run_id: str | None,
        limit: int,
        deadline_seconds: float,
    ) -> None:
        if workspace_id is not None and (
            not isinstance(workspace_id, str)
            or _SAFE_SCOPE_PATTERN.fullmatch(workspace_id) is None
        ):
            raise ValueError("workspace scope is invalid")
        if run_id is not None and (
            not isinstance(run_id, str) or _RUN_ID_PATTERN.fullmatch(run_id) is None
        ):
            raise ValueError("run scope is invalid")
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= _MAX_LIMIT
        ):
            raise ValueError("reconcile limit is invalid")
        if (
            isinstance(deadline_seconds, bool)
            or not isinstance(deadline_seconds, (int, float))
            or not 0 < float(deadline_seconds) <= 60.0
        ):
            raise ValueError("reconcile deadline is invalid")

    def dry_run(
        self,
        *,
        db: Any,
        workspace_id: str | None = None,
        run_id: str | None = None,
        limit: int = _DEFAULT_LIMIT,
        cursor: str | None = None,
        deadline_seconds: float = _DEFAULT_DEADLINE_SECONDS,
    ) -> ArtifactStoryIndexReconcileReport:
        """Compare at most ``limit`` rows and always roll back the DB session."""

        self._validate_scope(
            workspace_id=workspace_id,
            run_id=run_id,
            limit=limit,
            deadline_seconds=deadline_seconds,
        )
        position = decode_reconcile_cursor(
            cursor,
            workspace_id=workspace_id,
            run_id=run_id,
        )
        try:
            db.execute("SET TRANSACTION READ ONLY")
            repository = self._repository_factory(db)
            repository.require_schema()
        except ArtifactStoryIndexRepositoryError as exc:
            try:
                db.rollback()
            except Exception:
                pass
            if exc.code == STORY_INDEX_SCHEMA_UNAVAILABLE:
                return ArtifactStoryIndexReconcileReport.database_failure(
                    "schema_unavailable"
                )
            return ArtifactStoryIndexReconcileReport.database_failure("unavailable")
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            return ArtifactStoryIndexReconcileReport.database_failure("unavailable")

        accumulator = _ReconcileAccumulator()
        deadline = self._monotonic() + float(deadline_seconds)
        budget = limit
        next_position: ArtifactStoryIndexReconcileCursor | None = None
        try:
            if position.phase == "runs":
                candidates = repository.list_run_candidates(
                    workspace_id=workspace_id,
                    run_id=run_id,
                    after=position.after,
                    limit=budget + 1,
                )
                processed = 0
                last_after = position.after
                for candidate in candidates[:budget]:
                    if self._monotonic() >= deadline:
                        break
                    self._process_run_candidate(repository, candidate, accumulator)
                    processed += 1
                    last_after = candidate.run_id
                budget -= processed
                if len(candidates) > processed:
                    next_position = ArtifactStoryIndexReconcileCursor(
                        phase="runs",
                        after=last_after,
                        workspace_id=workspace_id,
                        run_id=run_id,
                    )
                elif budget == 0:
                    next_position = ArtifactStoryIndexReconcileCursor(
                        phase="stories",
                        workspace_id=workspace_id,
                        run_id=run_id,
                    )
                else:
                    position = ArtifactStoryIndexReconcileCursor(
                        phase="stories",
                        workspace_id=workspace_id,
                        run_id=run_id,
                    )

            if next_position is None and position.phase == "stories" and budget > 0:
                if self._monotonic() >= deadline:
                    next_position = ArtifactStoryIndexReconcileCursor(
                        phase="stories",
                        after=position.after,
                        workspace_id=workspace_id,
                        run_id=run_id,
                    )
                else:
                    records = repository.list_story_records(
                        workspace_id=workspace_id,
                        run_id=run_id,
                        after=position.after,
                        limit=budget + 1,
                    )
                    processed = 0
                    last_after = position.after
                    for record in records[:budget]:
                        if self._monotonic() >= deadline:
                            break
                        self._process_story_record(repository, record, accumulator)
                        processed += 1
                        last_after = record.story_id
                    if len(records) > processed:
                        next_position = ArtifactStoryIndexReconcileCursor(
                            phase="stories",
                            after=last_after,
                            workspace_id=workspace_id,
                            run_id=run_id,
                        )
        except ArtifactStoryIndexRepositoryError as exc:
            status: Literal["schema_unavailable", "unavailable"] = (
                "schema_unavailable"
                if exc.code == STORY_INDEX_SCHEMA_UNAVAILABLE
                else "unavailable"
            )
            return ArtifactStoryIndexReconcileReport.database_failure(status)
        finally:
            try:
                db.rollback()
            except Exception:
                pass

        encoded_cursor = (
            encode_reconcile_cursor(next_position)
            if next_position is not None
            else None
        )
        return accumulator.report(next_cursor=encoded_cursor)


__all__ = [
    "ArtifactStoryIndexReconcileCursor",
    "ArtifactStoryIndexReconcileReport",
    "ArtifactStoryIndexReconcileRepository",
    "ArtifactStoryIndexReconcileService",
    "ArtifactStoryIndexRunCandidate",
    "decode_reconcile_cursor",
    "encode_reconcile_cursor",
]
