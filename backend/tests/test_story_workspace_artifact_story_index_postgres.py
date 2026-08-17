"""Transactional Story index repository tests without a SQLite write fallback."""

from __future__ import annotations

import os
import re
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.rows import dict_row

from persistence.config import require_test_database_url
from services.story_workspace.artifact_story_index_projector import (
    ARTIFACT_SOURCE_TYPE,
    ArtifactStoryIndexProjector,
    ArtifactStoryProjection,
    ArtifactStoryProjectionError,
)
from services.story_workspace.artifact_story_index_repository import (
    PUBLIC_STORY_COLUMNS,
    ArtifactStoryIndexRecord,
    ArtifactStoryIndexRepository,
    ArtifactStoryIndexRepositoryError,
    ArtifactStoryIndexWriteResult,
    STORY_INDEX_CONFLICT,
    STORY_INDEX_DATABASE_UNAVAILABLE,
    STORY_INDEX_REVISION_CONFLICT,
    STORY_INDEX_SCHEMA_UNAVAILABLE,
    StoryWorkspacePublicStoryRepository,
)
from services.story_workspace.artifact_story_index_service import (
    ArtifactStoryIndexService,
)


REQUIRED_INDEX_COLUMNS = frozenset(
    {
        "artifact_source_type",
        "source_run_id",
        "source_thread_ref",
        "source_project_id",
        "episode_count",
        "artifact_status",
        "artifact_manifest_revision",
        "script_revision",
        "artifact_sync_status",
        "artifact_indexed_at",
        "artifact_sync_error_code",
        "script_size_bytes",
        "artifact_available",
        "reconcile_version",
        "reviewed_script_revision",
    }
)

EXPECTED_PUBLIC_STORY_COLUMNS = (
    "id",
    "identifier",
    "title",
    "description",
    "status",
    "review_status",
    "review_notes",
    "type",
    "character_count",
    "scene_count",
    "created_at",
    "updated_at",
    "confirmed_at",
    "source_run_id",
    "source_project_id",
    "episode_count",
    "artifact_status",
    "artifact_manifest_revision",
    "script_revision",
    "artifact_sync_status",
    "artifact_indexed_at",
    "artifact_sync_error_code",
    "script_size_bytes",
    "artifact_available",
    "reconcile_version",
)

WORKSPACE_ID = "workspace-repository-tests"
PROJECT_ID = "safe-project"
RUN_ID = "run_0123456789abcdef0123456789abcdef"
NEXT_RUN_ID = "run_fedcba9876543210fedcba9876543210"
THREAD_ID = "thread-repository-tests"
MANIFEST_REVISION = "sha256:" + "1" * 64
SCRIPT_REVISION = "sha256:" + "2" * 64
NEXT_MANIFEST_REVISION = "sha256:" + "3" * 64
NEXT_SCRIPT_REVISION = "sha256:" + "4" * 64


class _Rows:
    def __init__(self, rows: list[dict[str, Any]], *, rowcount: int | None = None):
        self._rows = rows
        self.rowcount = len(rows) if rowcount is None else rowcount

    def fetchall(self) -> list[dict[str, Any]]:
        return list(self._rows)

    def fetchone(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None


class _FakeRepositoryDB:
    """Small SQL-observing fake; it is not a database or SQLite substitute."""

    def __init__(
        self,
        *,
        schema_columns: frozenset[str] = REQUIRED_INDEX_COLUMNS,
        fail_schema_query: bool = False,
        identity_key_available: bool = True,
        identity_key_count: int = 3,
        identity_key_all_direct: bool = True,
        identity_key_full: bool = True,
    ) -> None:
        self.schema_columns = schema_columns
        self.fail_schema_query = fail_schema_query
        self.identity_key_available = identity_key_available
        self.identity_key_count = identity_key_count
        self.identity_key_all_direct = identity_key_all_direct
        self.identity_key_full = identity_key_full
        self.stories: list[dict[str, Any]] = []
        self.queries: list[tuple[str, tuple[Any, ...]]] = []
        self.commit_count = 0
        self.rollback_count = 0
        self._clock = 0

    def _timestamp(self) -> str:
        self._clock += 1
        return f"timestamp-{self._clock}"

    @staticmethod
    def _normalized(query: Any) -> str:
        return " ".join(str(query).split())

    def execute(self, query: Any, parameters: Any = None) -> _Rows:
        rendered = self._normalized(query)
        params = tuple(parameters or ())
        self.queries.append((rendered, params))
        upper = rendered.upper()

        if "FROM INFORMATION_SCHEMA.COLUMNS" in upper:
            if self.fail_schema_query:
                raise OSError("simulated PostgreSQL outage")
            return _Rows(
                [{"column_name": column} for column in sorted(self.schema_columns)]
            )
        if "FROM PG_CATALOG.PG_INDEX" in upper:
            return _Rows(
                [
                    {
                        "column_names": [
                            "workspace_id",
                            "artifact_source_type",
                            "source_project_id",
                        ],
                        "key_count": self.identity_key_count,
                        "all_direct_columns": self.identity_key_all_direct,
                        "predicate": (
                            "(artifact_source_type IS NOT NULL) AND "
                            "(source_project_id IS NOT NULL)"
                            if self.identity_key_full
                            else None
                        ),
                    }
                ]
                if self.identity_key_available
                else []
            )
        if upper.startswith("SELECT PG_ADVISORY_XACT_LOCK"):
            return _Rows([{"pg_advisory_xact_lock": None}])
        if (
            "FROM STORY_WORKSPACE_STORIES" in upper
            and "ARTIFACT_SOURCE_TYPE = %S" in upper
        ):
            workspace_id, source_type, project_id = params
            matches = [
                story
                for story in self.stories
                if story["workspace_id"] == workspace_id
                and story["artifact_source_type"] == source_type
                and story["source_project_id"] == project_id
            ]
            return _Rows(matches)
        if upper.startswith("SELECT ID FROM STORY_WORKSPACE_STORIES WHERE ID = %S"):
            matches = [story for story in self.stories if story["id"] == params[0]]
            return _Rows([{"id": story["id"]} for story in matches])
        if upper.startswith("INSERT INTO STORY_WORKSPACE_STORIES"):
            timestamp = self._timestamp()
            story = {
                "id": params[0],
                "identifier": params[1],
                "title": params[2],
                "description": None,
                "status": "draft",
                "review_status": "pending",
                "type": "script",
                "content": None,
                "author_id": params[3],
                "workspace_id": params[4],
                "character_count": 0,
                "scene_count": 0,
                "agent_generated": 1,
                "artifact_source_type": params[5],
                "source_run_id": params[6],
                "source_thread_ref": params[7],
                "source_project_id": params[8],
                "episode_count": params[9],
                "artifact_manifest_revision": params[10],
                "script_revision": params[11],
                "artifact_sync_status": "indexed",
                "artifact_indexed_at": timestamp,
                "artifact_sync_error_code": None,
                "script_size_bytes": params[12],
                "artifact_status": params[13],
                "artifact_available": params[14],
                "reconcile_version": 1,
                "review_notes": None,
                "confirmed_at": None,
                "published_at": None,
                "reviewed_script_revision": None,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
            self.stories.append(story)
            return _Rows([story], rowcount=1)
        if upper.startswith("UPDATE STORY_WORKSPACE_STORIES SET"):
            story = next(item for item in self.stories if item["id"] == params[13])
            timestamp = self._timestamp()
            story.update(
                {
                    "identifier": params[0],
                    "title": params[1],
                    "source_run_id": params[2],
                    "episode_count": params[3],
                    "artifact_manifest_revision": params[4],
                    "script_revision": params[5],
                    "artifact_sync_status": "indexed",
                    "artifact_indexed_at": timestamp,
                    "artifact_sync_error_code": None,
                    "script_size_bytes": params[6],
                    "artifact_status": params[7],
                    "artifact_available": params[8],
                    "reconcile_version": 1,
                    "updated_at": timestamp,
                }
            )
            if (
                story.get("status") == "published"
                and (
                    story.get("reviewed_script_revision") != params[9]
                    or params[10] != "available"
                )
            ):
                story["status"] = "draft"
                story["published_at"] = None
            return _Rows([story], rowcount=1)
        raise AssertionError(f"Unexpected repository SQL: {rendered}")

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1


class _RollbackOnlyRepositoryConnection:
    """Map repository commits/rollbacks to savepoints under one outer rollback."""

    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection
        self._sequence = 0
        self._savepoint: str | None = None
        self._start_savepoint()

    def _start_savepoint(self) -> None:
        self._sequence += 1
        self._savepoint = f"artifact_story_index_{self._sequence}"
        self._connection.execute(
            sql.SQL("SAVEPOINT {}").format(sql.Identifier(self._savepoint))
        )

    def execute(self, query: Any, parameters: Any = None) -> Any:
        if parameters is None:
            return self._connection.execute(query)
        return self._connection.execute(query, parameters)

    def commit(self) -> None:
        assert self._savepoint is not None
        self._connection.execute(
            sql.SQL("RELEASE SAVEPOINT {}").format(sql.Identifier(self._savepoint))
        )
        self._savepoint = None
        self._start_savepoint()

    def rollback(self) -> None:
        assert self._savepoint is not None
        identifier = sql.Identifier(self._savepoint)
        self._connection.execute(sql.SQL("ROLLBACK TO SAVEPOINT {}").format(identifier))
        self._connection.execute(sql.SQL("RELEASE SAVEPOINT {}").format(identifier))
        self._savepoint = None
        self._start_savepoint()


class _StubProjector:
    def __init__(
        self,
        projection: ArtifactStoryProjection | None = None,
        error: ArtifactStoryProjectionError | None = None,
    ) -> None:
        self.projection = projection or _projection()
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def project(self, **kwargs: Any) -> ArtifactStoryProjection:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.projection


class _StubRepository:
    def __init__(
        self,
        *,
        write_result: ArtifactStoryIndexWriteResult | None = None,
        record: ArtifactStoryIndexRecord | None = None,
        error: ArtifactStoryIndexRepositoryError | None = None,
    ) -> None:
        self.write_result = write_result
        self.record = record
        self.error = error
        self.upserts: list[ArtifactStoryProjection] = []
        self.upsert_expectations: list[tuple[ArtifactStoryIndexRecord | None, bool]] = []
        self.finds: list[tuple[str, str]] = []

    def upsert(
        self,
        projection: ArtifactStoryProjection,
        *,
        expected_record: ArtifactStoryIndexRecord | None = None,
        require_expected_record: bool = False,
    ) -> ArtifactStoryIndexWriteResult:
        self.upserts.append(projection)
        self.upsert_expectations.append((expected_record, require_expected_record))
        if self.error is not None:
            raise self.error
        assert self.write_result is not None
        return self.write_result

    def find(
        self,
        *,
        workspace_id: str,
        source_project_id: str,
    ) -> ArtifactStoryIndexRecord | None:
        self.finds.append((workspace_id, source_project_id))
        if self.error is not None:
            raise self.error
        return self.record


def _projection(**changes: Any) -> ArtifactStoryProjection:
    projection = ArtifactStoryProjection(
        story_id=ArtifactStoryIndexProjector.deterministic_story_id(
            WORKSPACE_ID,
            PROJECT_ID,
        ),
        workspace_id=WORKSPACE_ID,
        author_id=23,
        source_run_id=RUN_ID,
        source_thread_ref=THREAD_ID,
        source_project_id=PROJECT_ID,
        title="Safe Project",
        episode_count=1,
        artifact_manifest_revision=MANIFEST_REVISION,
        script_revision=SCRIPT_REVISION,
        script_size_bytes=512,
    )
    return replace(projection, **changes)


def _record(**changes: Any) -> ArtifactStoryIndexRecord:
    values: dict[str, Any] = {
        "story_id": _projection().story_id,
        "identifier": PROJECT_ID,
        "title": "Safe Project",
        "workspace_id": WORKSPACE_ID,
        "source_run_id": RUN_ID,
        "source_thread_ref": THREAD_ID,
        "source_project_id": PROJECT_ID,
        "artifact_manifest_revision": MANIFEST_REVISION,
        "script_revision": SCRIPT_REVISION,
        "artifact_sync_status": "indexed",
        "artifact_indexed_at": datetime(2026, 8, 10, tzinfo=timezone.utc),
        "artifact_sync_error_code": None,
        "episode_count": 1,
        "script_size_bytes": 512,
        "artifact_status": "available",
        "artifact_available": True,
        "reconcile_version": 1,
    }
    values.update(changes)
    return ArtifactStoryIndexRecord(**values)


def _materialize(service: ArtifactStoryIndexService) -> dict[str, object]:
    return service.materialize(
        db=object(),
        workspace_root="unused-by-stub",
        workflow_run=object(),
        actor_id=23,
        thread_id=THREAD_ID,
        episode_authority=object(),
        refreshed_surface=object(),
    )


def _inspect(service: ArtifactStoryIndexService):
    return service.inspect(
        db=object(),
        workspace_root="unused-by-stub",
        workflow_run=object(),
        actor_id=23,
        thread_id=THREAD_ID,
        episode_authority=object(),
        refreshed_surface=object(),
    )


def test_schema_unavailable_fails_closed_without_attempting_a_write() -> None:
    db = _FakeRepositoryDB(
        schema_columns=REQUIRED_INDEX_COLUMNS - {"source_thread_ref"}
    )

    with pytest.raises(ArtifactStoryIndexRepositoryError) as raised:
        ArtifactStoryIndexRepository(db).upsert(_projection())

    assert raised.value.code == STORY_INDEX_SCHEMA_UNAVAILABLE
    assert raised.value.retryable is True
    assert db.rollback_count >= 1
    assert not any(
        re.match(r"^(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\b", query, re.I)
        for query, _params in db.queries
    )


def test_database_unavailable_is_safe_and_retryable() -> None:
    db = _FakeRepositoryDB(fail_schema_query=True)

    with pytest.raises(ArtifactStoryIndexRepositoryError) as raised:
        ArtifactStoryIndexRepository(db).upsert(_projection())

    assert raised.value.code == STORY_INDEX_DATABASE_UNAVAILABLE
    assert raised.value.retryable is True
    assert db.rollback_count >= 1


def test_missing_stable_identity_key_fails_closed_before_write() -> None:
    db = _FakeRepositoryDB(identity_key_available=False)

    with pytest.raises(ArtifactStoryIndexRepositoryError) as raised:
        ArtifactStoryIndexRepository(db).upsert(_projection())

    assert raised.value.code == STORY_INDEX_SCHEMA_UNAVAILABLE
    assert raised.value.retryable is True
    assert not any(
        re.match(r"^(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\b", query, re.I)
        for query, _params in db.queries
    )


@pytest.mark.parametrize(
    "db",
    [
        _FakeRepositoryDB(identity_key_count=4),
        _FakeRepositoryDB(identity_key_all_direct=False),
        _FakeRepositoryDB(identity_key_full=False),
    ],
    ids=["extra-expression-key", "expression-key", "partial-index"],
)
def test_stable_identity_key_must_be_exact_plain_and_non_partial(
    db: _FakeRepositoryDB,
) -> None:
    with pytest.raises(ArtifactStoryIndexRepositoryError) as raised:
        ArtifactStoryIndexRepository(db).require_schema()

    assert raised.value.code == STORY_INDEX_SCHEMA_UNAVAILABLE
    assert raised.value.retryable is True


def test_first_insert_has_null_content_and_frozen_base_values() -> None:
    db = _FakeRepositoryDB()

    result = ArtifactStoryIndexRepository(db).upsert(_projection())

    assert result.status == "created"
    assert result.story_id == _projection().story_id
    story = db.stories[0]
    assert story == {
        **story,
        "identifier": PROJECT_ID,
        "title": "Safe Project",
        "description": None,
        "status": "draft",
        "review_status": "pending",
        "type": "script",
        "content": None,
        "author_id": 23,
        "workspace_id": WORKSPACE_ID,
        "character_count": 0,
        "scene_count": 0,
        "agent_generated": 1,
        "artifact_source_type": ARTIFACT_SOURCE_TYPE,
        "source_run_id": RUN_ID,
        "source_thread_ref": THREAD_ID,
        "source_project_id": PROJECT_ID,
        "artifact_sync_status": "indexed",
        "artifact_sync_error_code": None,
        "artifact_available": True,
        "reconcile_version": 1,
    }
    insert_sql = next(
        query for query, _params in db.queries if query.startswith("INSERT INTO")
    )
    assert "description" in insert_sql
    assert "content" in insert_sql
    assert "NULL, 'draft', 'pending', 'script', NULL" in insert_sql


def test_same_revision_is_a_true_noop_including_updated_at() -> None:
    db = _FakeRepositoryDB()
    repository = ArtifactStoryIndexRepository(db)
    repository.upsert(_projection())
    story = db.stories[0]
    story["updated_at"] = "sentinel-updated-at"
    before = dict(story)
    update_count = sum(
        query.upper().startswith("UPDATE STORY_WORKSPACE_STORIES")
        for query, _params in db.queries
    )

    result = repository.upsert(_projection())

    assert result.status == "same_revision"
    assert db.stories[0] == before
    assert db.stories[0]["updated_at"] == "sentinel-updated-at"
    assert (
        sum(
            query.upper().startswith("UPDATE STORY_WORKSPACE_STORIES")
            for query, _params in db.queries
        )
        == update_count
    )


def test_same_revision_repairs_retryable_index_metadata_drift() -> None:
    db = _FakeRepositoryDB()
    repository = ArtifactStoryIndexRepository(db)
    repository.upsert(_projection())
    story = db.stories[0]
    story.update(
        {
            "title": "Stale title",
            "source_run_id": NEXT_RUN_ID,
            "episode_count": 7,
            "artifact_sync_status": "failed",
            "artifact_indexed_at": None,
            "artifact_sync_error_code": STORY_INDEX_DATABASE_UNAVAILABLE,
            "script_size_bytes": 999,
            "artifact_available": False,
            "reconcile_version": 0,
        }
    )

    result = repository.upsert(_projection())

    assert result.status == "updated"
    assert story["title"] == "Safe Project"
    assert story["source_run_id"] == RUN_ID
    assert story["episode_count"] == 1
    assert story["artifact_sync_status"] == "indexed"
    assert story["artifact_indexed_at"] is not None
    assert story["artifact_sync_error_code"] is None
    assert story["script_size_bytes"] == 512
    assert story["artifact_available"] is True
    assert story["reconcile_version"] == 1


def test_new_revision_updates_same_id_preserves_review_history_and_demotes_publish() -> None:
    db = _FakeRepositoryDB()
    repository = ArtifactStoryIndexRepository(db)
    created = repository.upsert(_projection())
    story = db.stories[0]
    story.update(
        {
            "status": "published",
            "review_status": "confirmed",
            "review_notes": "Admin-owned note",
            "confirmed_at": "confirmed",
            "published_at": "published",
            "reviewed_script_revision": SCRIPT_REVISION,
            "content": "legacy content that the projector must preserve",
        }
    )

    updated = repository.upsert(
        _projection(
            source_run_id=NEXT_RUN_ID,
            title="Updated Safe Project",
            episode_count=3,
            artifact_manifest_revision=NEXT_MANIFEST_REVISION,
            script_revision=NEXT_SCRIPT_REVISION,
            script_size_bytes=1024,
        )
    )

    assert updated.status == "updated"
    assert updated.story_id == created.story_id == _projection().story_id
    assert story["source_run_id"] == NEXT_RUN_ID
    assert story["episode_count"] == 3
    assert story["artifact_manifest_revision"] == NEXT_MANIFEST_REVISION
    assert story["script_revision"] == NEXT_SCRIPT_REVISION
    assert story["reconcile_version"] == 1
    assert story["status"] == "draft"
    assert story["review_status"] == "confirmed"
    assert story["review_notes"] == "Admin-owned note"
    assert story["confirmed_at"] == "confirmed"
    assert story["published_at"] is None
    assert story["reviewed_script_revision"] == SCRIPT_REVISION
    assert story["content"] == "legacy content that the projector must preserve"

    update_sql = next(
        query
        for query, _params in db.queries
        if query.upper().startswith("UPDATE STORY_WORKSPACE_STORIES")
    )
    for forbidden_assignment in (
        "content =",
        "review_status =",
            "review_notes =",
            "confirmed_at =",
            "reviewed_script_revision =",
    ):
        assert forbidden_assignment not in update_sql


def test_cross_thread_project_is_a_conflict_without_overwrite() -> None:
    db = _FakeRepositoryDB()
    repository = ArtifactStoryIndexRepository(db)
    repository.upsert(_projection())
    before = dict(db.stories[0])

    result = repository.upsert(
        _projection(
            source_thread_ref="different-thread",
            artifact_manifest_revision=NEXT_MANIFEST_REVISION,
            script_revision=NEXT_SCRIPT_REVISION,
        )
    )

    assert result.status == "conflict"
    assert result.error_code == STORY_INDEX_CONFLICT
    assert result.retryable is False
    assert db.rollback_count == 1
    assert db.stories[0] == before


def test_locked_expected_record_cas_rejects_a_concurrent_row_change() -> None:
    db = _FakeRepositoryDB()
    repository = ArtifactStoryIndexRepository(db)
    created = repository.upsert(_projection())
    assert created.record is not None
    db.stories[0]["artifact_sync_status"] = "stale"
    before = dict(db.stories[0])

    result = repository.upsert(
        _projection(
            artifact_manifest_revision=NEXT_MANIFEST_REVISION,
            script_revision=NEXT_SCRIPT_REVISION,
        ),
        expected_record=created.record,
        require_expected_record=True,
    )

    assert result.status == "revision_conflict"
    assert result.error_code == STORY_INDEX_REVISION_CONFLICT
    assert result.retryable is True
    assert db.stories[0] == before
    assert db.rollback_count == 1


def test_locked_expected_record_cas_rejects_a_concurrent_title_change() -> None:
    db = _FakeRepositoryDB()
    repository = ArtifactStoryIndexRepository(db)
    created = repository.upsert(_projection())
    assert created.record is not None
    db.stories[0]["title"] = "Admin changed this title"

    result = repository.upsert(
        _projection(title="Projected replacement"),
        expected_record=created.record,
        require_expected_record=True,
    )

    assert result.status == "revision_conflict"
    assert result.error_code == STORY_INDEX_REVISION_CONFLICT
    assert db.stories[0]["title"] == "Admin changed this title"


def test_existing_stable_key_with_non_deterministic_id_is_a_conflict() -> None:
    db = _FakeRepositoryDB()
    repository = ArtifactStoryIndexRepository(db)
    repository.upsert(_projection())
    db.stories[0]["id"] = str(uuid4())
    before = dict(db.stories[0])

    result = repository.upsert(_projection())

    assert result.status == "conflict"
    assert result.error_code == STORY_INDEX_CONFLICT
    assert db.stories[0] == before


def test_deterministic_id_collision_with_another_key_is_a_conflict() -> None:
    db = _FakeRepositoryDB()
    collision = _FakeRepositoryDB()
    collision_repository = ArtifactStoryIndexRepository(collision)
    collision_repository.upsert(
        _projection(
            workspace_id="another-workspace",
            source_project_id="another-project",
            story_id=_projection().story_id,
        )
    )
    db.stories.extend(collision.stories)

    result = ArtifactStoryIndexRepository(db).upsert(_projection())

    assert result.status == "conflict"
    assert result.story_id == _projection().story_id
    assert result.error_code == STORY_INDEX_CONFLICT
    assert len(db.stories) == 1


def test_public_story_allowlist_is_exact_and_has_no_internal_locator() -> None:
    assert PUBLIC_STORY_COLUMNS == EXPECTED_PUBLIC_STORY_COLUMNS
    assert {
        "source_thread_ref",
        "content",
        "agent_session_id",
        "workspace_id",
        "author_id",
        "artifact_relative_path",
        "reviewed_script_revision",
    }.isdisjoint(PUBLIC_STORY_COLUMNS)


def test_public_story_projection_redacts_non_allowlisted_stored_error_text() -> None:
    raw = StoryWorkspacePublicStoryRepository._public_row(
        {
            "artifact_available": 1,
            "artifact_sync_error_code": "/Users/private/thread/Traceback",
        }
    )
    safe = StoryWorkspacePublicStoryRepository._public_row(
        {
            "artifact_available": 1,
            "artifact_sync_error_code": STORY_INDEX_DATABASE_UNAVAILABLE,
        }
    )

    assert raw["artifact_available"] is True
    assert raw["artifact_sync_error_code"] is None
    assert safe["artifact_sync_error_code"] == STORY_INDEX_DATABASE_UNAVAILABLE


@pytest.mark.parametrize("status", ["created", "updated", "same_revision"])
def test_service_materialize_preserves_repository_success_status(status: str) -> None:
    projection = _projection()
    repository = _StubRepository(
        write_result=ArtifactStoryIndexWriteResult(
            status=status,
            story_id=projection.story_id,
            record=_record(),
        )
    )
    projector = _StubProjector(projection)
    service = ArtifactStoryIndexService(
        projector=projector,
        repository_factory=lambda _db: repository,
    )

    result = _materialize(service)

    assert result == {
        "status": status,
        "storyId": projection.story_id,
        "errorCode": None,
        "retryable": False,
    }
    assert repository.upserts == [projection]
    assert len(projector.calls) == 1


def test_service_materialize_returns_safe_conflict_without_throwing() -> None:
    projection = _projection()
    repository = _StubRepository(
        write_result=ArtifactStoryIndexWriteResult(
            status="conflict",
            story_id=projection.story_id,
            record=_record(),
            error_code=STORY_INDEX_CONFLICT,
            retryable=False,
        )
    )
    service = ArtifactStoryIndexService(
        projector=_StubProjector(projection),
        repository_factory=lambda _db: repository,
    )

    assert _materialize(service) == {
        "status": "conflict",
        "storyId": projection.story_id,
        "errorCode": STORY_INDEX_CONFLICT,
        "retryable": False,
    }


def test_service_materialize_projection_forwards_the_exact_cas_snapshot() -> None:
    projection = _projection()
    expected = _record()
    repository = _StubRepository(
        write_result=ArtifactStoryIndexWriteResult(
            status="revision_conflict",
            story_id=projection.story_id,
            record=expected,
            error_code=STORY_INDEX_REVISION_CONFLICT,
            retryable=True,
        )
    )
    service = ArtifactStoryIndexService(
        projector=_StubProjector(projection),
        repository_factory=lambda _db: repository,
    )

    result = service.materialize_projection(
        db=object(),
        projection=projection,
        expected_record=expected,
        require_expected_record=True,
    )

    assert result == {
        "status": "conflict",
        "storyId": projection.story_id,
        "errorCode": STORY_INDEX_REVISION_CONFLICT,
        "retryable": True,
    }
    assert repository.upsert_expectations == [(expected, True)]


@pytest.mark.parametrize(
    ("error", "expected_code", "retryable"),
    [
        (
            ArtifactStoryProjectionError(
                "story_index_invalid_artifact",
                retryable=False,
            ),
            "story_index_invalid_artifact",
            False,
        ),
        (
            ArtifactStoryIndexRepositoryError(
                STORY_INDEX_SCHEMA_UNAVAILABLE,
                retryable=True,
            ),
            STORY_INDEX_SCHEMA_UNAVAILABLE,
            True,
        ),
    ],
)
def test_service_materialize_collapses_known_failures_to_safe_results(
    error: Exception,
    expected_code: str,
    retryable: bool,
) -> None:
    if isinstance(error, ArtifactStoryProjectionError):
        projector = _StubProjector(error=error)
        repository = _StubRepository()
    else:
        projector = _StubProjector()
        repository = _StubRepository(error=error)
    service = ArtifactStoryIndexService(
        projector=projector,
        repository_factory=lambda _db: repository,
    )

    assert _materialize(service) == {
        "status": "failed",
        "errorCode": expected_code,
        "retryable": retryable,
    }


@pytest.mark.parametrize(
    ("record", "status", "error_code", "retryable"),
    [
        (None, "missing", "story_index_row_missing", True),
        (_record(), "indexed", None, False),
        (
            _record(artifact_manifest_revision=NEXT_MANIFEST_REVISION),
            "stale",
            None,
            True,
        ),
        (_record(title="Stale indexed title"), "stale", None, True),
        (
            _record(source_thread_ref="another-thread"),
            "failed",
            STORY_INDEX_CONFLICT,
            False,
        ),
        (
            _record(
                artifact_sync_status="failed",
                artifact_sync_error_code=STORY_INDEX_DATABASE_UNAVAILABLE,
            ),
            "failed",
            STORY_INDEX_DATABASE_UNAVAILABLE,
            True,
        ),
    ],
)
def test_service_inspect_is_read_only_and_projects_safe_status(
    record: ArtifactStoryIndexRecord | None,
    status: str,
    error_code: str | None,
    retryable: bool,
) -> None:
    repository = _StubRepository(record=record)
    service = ArtifactStoryIndexService(
        projector=_StubProjector(),
        repository_factory=lambda _db: repository,
    )

    observation = _inspect(service)

    assert observation.status == status
    assert observation.error_code == error_code
    assert observation.retryable is retryable
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", observation.etag)
    assert repository.finds == [(WORKSPACE_ID, PROJECT_ID)]
    assert repository.upserts == []
    public = observation.public_dict()
    assert "sourceThreadRef" not in public
    assert "source_thread_ref" not in public
    assert "workspaceRoot" not in public
    assert "path" not in public


def test_service_inspect_redacts_a_non_deterministic_conflicting_story_id() -> None:
    repository = _StubRepository(record=_record(story_id=str(uuid4())))
    service = ArtifactStoryIndexService(
        projector=_StubProjector(),
        repository_factory=lambda _db: repository,
    )

    observation = _inspect(service)

    assert observation.status == "failed"
    assert observation.error_code == STORY_INDEX_CONFLICT
    assert observation.retryable is False
    assert observation.story_id is None
    assert observation.public_dict()["storyId"] is None


def test_observation_etag_covers_projected_and_indexed_titles() -> None:
    base_repository = _StubRepository(record=_record())
    base = ArtifactStoryIndexService(
        projector=_StubProjector(),
        repository_factory=lambda _db: base_repository,
    )
    projected_title = ArtifactStoryIndexService(
        projector=_StubProjector(_projection(title="Renamed project")),
        repository_factory=lambda _db: _StubRepository(record=_record()),
    )
    indexed_title = ArtifactStoryIndexService(
        projector=_StubProjector(),
        repository_factory=lambda _db: _StubRepository(
            record=_record(title="Concurrent Admin title")
        ),
    )

    base_etag = _inspect(base).etag

    assert _inspect(projected_title).etag != base_etag
    assert _inspect(indexed_title).etag != base_etag


def test_observation_serializes_postgres_offsets_as_utc() -> None:
    repository = _StubRepository(
        record=_record(
            artifact_indexed_at=datetime(
                2026,
                8,
                10,
                9,
                0,
                tzinfo=timezone(timedelta(hours=8)),
            )
        )
    )
    service = ArtifactStoryIndexService(
        projector=_StubProjector(),
        repository_factory=lambda _db: repository,
    )

    assert _inspect(service).public_dict()["lastIndexedAt"] == "2026-08-10T01:00:00Z"


def test_observation_etag_is_timezone_representation_independent() -> None:
    utc_record = _record(
        artifact_indexed_at=datetime(2026, 8, 10, 1, 0, tzinfo=timezone.utc)
    )
    offset_record = _record(
        artifact_indexed_at=datetime(
            2026,
            8,
            10,
            9,
            0,
            tzinfo=timezone(timedelta(hours=8)),
        )
    )
    utc_service = ArtifactStoryIndexService(
        projector=_StubProjector(),
        repository_factory=lambda _db: _StubRepository(record=utc_record),
    )
    offset_service = ArtifactStoryIndexService(
        projector=_StubProjector(),
        repository_factory=lambda _db: _StubRepository(record=offset_record),
    )

    assert _inspect(utc_service).etag == _inspect(offset_service).etag


@pytest.mark.parametrize(
    "index_statement",
    [
        (
            "CREATE UNIQUE INDEX deceptive_partial_identity ON "
            "story_workspace_stories "
            "(workspace_id, artifact_source_type, source_project_id) "
            "WHERE artifact_source_type = 'dream_episode'"
        ),
        (
            "CREATE UNIQUE INDEX deceptive_expression_identity ON "
            "story_workspace_stories "
            "(workspace_id, artifact_source_type, source_project_id, "
            "(lower(source_run_id)))"
        ),
    ],
    ids=["partial-index", "extra-expression-key"],
)
def test_postgres_schema_gate_rejects_ambiguous_identity_indexes(
    index_statement: str,
) -> None:
    """Exercise pg_index semantics in an isolated session-local table."""

    if not os.environ.get("TEST_DATABASE_URL"):
        pytest.skip("set explicit TEST_DATABASE_URL for PostgreSQL catalog checks")
    connection = psycopg.connect(require_test_database_url(), row_factory=dict_row)
    try:
        connection.execute(
            "CREATE TEMP TABLE story_workspace_stories ("
            "workspace_id TEXT, artifact_source_type TEXT, source_run_id TEXT, "
            "source_thread_ref TEXT, source_project_id TEXT, episode_count INTEGER, "
            "artifact_manifest_revision TEXT, script_revision TEXT, "
            "artifact_sync_status TEXT, artifact_indexed_at TIMESTAMPTZ, "
            "artifact_sync_error_code TEXT, script_size_bytes BIGINT, "
            "artifact_available BOOLEAN, reconcile_version INTEGER, "
            "reviewed_script_revision TEXT) ON COMMIT DROP"
        )
        connection.execute(index_statement)
        connection.execute("SET LOCAL search_path TO pg_temp")

        with pytest.raises(ArtifactStoryIndexRepositoryError) as raised:
            ArtifactStoryIndexRepository(connection).require_schema()

        assert raised.value.code == STORY_INDEX_SCHEMA_UNAVAILABLE
    finally:
        connection.rollback()
        connection.close()


@pytest.fixture
def postgres_repository_case() -> Iterator[
    tuple[psycopg.Connection[Any], ArtifactStoryIndexRepository, ArtifactStoryProjection]
]:
    """Use only an explicitly named disposable PostgreSQL; never create schema."""

    if not os.environ.get("TEST_DATABASE_URL"):
        pytest.skip("set explicit TEST_DATABASE_URL for disposable PostgreSQL checks")
    dsn = require_test_database_url()
    connection = psycopg.connect(dsn, row_factory=dict_row)
    try:
        columns = {
            str(row["column_name"])
            for row in connection.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = current_schema() "
                "AND table_name = 'story_workspace_stories'"
            ).fetchall()
        }
        if not REQUIRED_INDEX_COLUMNS.issubset(columns):
            pytest.skip(
                "Admin Story index migration is a PostgreSQL schema prerequisite"
            )
        connection.rollback()

        token = uuid4().hex
        user = connection.execute(
            "INSERT INTO users (email, password_hash, display_name) "
            "VALUES (%s, %s, %s) RETURNING id",
            (f"artifact-index-{token}@example.invalid", "test-hash", "Index Test"),
        ).fetchone()
        assert user is not None
        workspace_id = f"workspace-artifact-index-{token}"
        connection.execute(
            "INSERT INTO story_workspace_workspaces (id, name, owner_id) "
            "VALUES (%s, %s, %s)",
            (workspace_id, "Artifact Index Test", int(user["id"])),
        )
        projection = _projection(
            story_id=ArtifactStoryIndexProjector.deterministic_story_id(
                workspace_id,
                PROJECT_ID,
            ),
            workspace_id=workspace_id,
            author_id=int(user["id"]),
        )
        repository = ArtifactStoryIndexRepository(
            _RollbackOnlyRepositoryConnection(connection)
        )
        yield connection, repository, projection
    finally:
        connection.rollback()
        connection.close()


def test_postgres_create_noop_update_and_conflict_are_rollback_only(
    postgres_repository_case: tuple[
        psycopg.Connection[Any],
        ArtifactStoryIndexRepository,
        ArtifactStoryProjection,
    ],
) -> None:
    connection, repository, projection = postgres_repository_case

    created = repository.upsert(projection)
    assert created.status == "created"
    row = connection.execute(
        "SELECT * FROM story_workspace_stories WHERE id = %s",
        (projection.story_id,),
    ).fetchone()
    assert row is not None
    assert row["description"] is None
    assert row["content"] is None
    assert row["status"] == "draft"
    assert row["review_status"] == "pending"
    assert row["type"] == "script"
    assert row["agent_generated"] == 1

    sentinel = datetime(2001, 1, 1, tzinfo=timezone.utc)
    connection.execute(
        "UPDATE story_workspace_stories SET updated_at = %s WHERE id = %s",
        (sentinel, projection.story_id),
    )
    same = repository.upsert(projection)
    assert same.status == "same_revision"
    unchanged_at = connection.execute(
        "SELECT updated_at FROM story_workspace_stories WHERE id = %s",
        (projection.story_id,),
    ).fetchone()
    assert unchanged_at is not None
    assert unchanged_at["updated_at"] == sentinel

    connection.execute(
        "UPDATE story_workspace_stories SET status = 'published', "
        "review_status = 'confirmed', review_notes = %s, content = %s, "
        "confirmed_at = CURRENT_TIMESTAMP, published_at = CURRENT_TIMESTAMP, "
        "reviewed_script_revision = %s WHERE id = %s",
        (
            "Admin-owned note",
            "legacy content",
            SCRIPT_REVISION,
            projection.story_id,
        ),
    )
    next_projection = replace(
        projection,
        source_run_id=NEXT_RUN_ID,
        title="Updated Safe Project",
        episode_count=2,
        artifact_manifest_revision=NEXT_MANIFEST_REVISION,
        script_revision=NEXT_SCRIPT_REVISION,
        script_size_bytes=1024,
    )
    updated = repository.upsert(next_projection)
    assert updated.status == "updated"
    assert updated.story_id == created.story_id == projection.story_id
    protected = connection.execute(
        "SELECT status, review_status, review_notes, content, confirmed_at, "
        "published_at, reviewed_script_revision, reconcile_version, "
        "source_run_id, episode_count, artifact_manifest_revision, script_revision "
        "FROM story_workspace_stories WHERE id = %s",
        (projection.story_id,),
    ).fetchone()
    assert protected is not None
    assert protected["status"] == "draft"
    assert protected["review_status"] == "confirmed"
    assert protected["review_notes"] == "Admin-owned note"
    assert protected["content"] == "legacy content"
    assert protected["confirmed_at"] is not None
    assert protected["published_at"] is None
    assert protected["reviewed_script_revision"] == SCRIPT_REVISION
    assert protected["reconcile_version"] == 1
    assert protected["source_run_id"] == NEXT_RUN_ID
    assert protected["episode_count"] == 2
    assert protected["artifact_manifest_revision"] == NEXT_MANIFEST_REVISION
    assert protected["script_revision"] == NEXT_SCRIPT_REVISION

    conflict = repository.upsert(
        replace(
            next_projection,
            source_thread_ref="another-thread",
            artifact_manifest_revision="sha256:" + "5" * 64,
            script_revision="sha256:" + "6" * 64,
        )
    )
    assert conflict.status == "conflict"
    assert conflict.error_code == STORY_INDEX_CONFLICT
    still_indexed = connection.execute(
        "SELECT source_thread_ref, artifact_manifest_revision, script_revision "
        "FROM story_workspace_stories WHERE id = %s",
        (projection.story_id,),
    ).fetchone()
    assert still_indexed is not None
    assert still_indexed["source_thread_ref"] == THREAD_ID
    assert still_indexed["artifact_manifest_revision"] == NEXT_MANIFEST_REVISION
    assert still_indexed["script_revision"] == NEXT_SCRIPT_REVISION
