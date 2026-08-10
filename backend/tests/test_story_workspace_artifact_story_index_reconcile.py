"""Focused safety and pagination tests for Story Artifact index dry-runs."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

try:
    from script import reconcile_story_artifact_index as reconcile_cli
except ModuleNotFoundError:  # pragma: no cover - repository-root invocation.
    from backend.script import reconcile_story_artifact_index as reconcile_cli
from services.story_workspace import artifact_story_index_repository as repository_module
from services.story_workspace.artifact_story_index_projector import (
    ARTIFACT_SOURCE_TYPE,
    ArtifactStoryProjection,
    ArtifactStoryProjectionError,
)
from services.story_workspace.artifact_story_index_reconcile import (
    ArtifactStoryIndexReconcileCursor,
    ArtifactStoryIndexReconcileReport,
    ArtifactStoryIndexReconcileService,
    ArtifactStoryIndexRunCandidate,
    decode_reconcile_cursor,
    encode_reconcile_cursor,
)
from services.story_workspace.artifact_story_index_repository import (
    PUBLIC_STORY_COLUMNS,
    ArtifactStoryIndexRecord,
    ArtifactStoryIndexRepository,
    ArtifactStoryIndexRepositoryError,
    STORY_INDEX_DATABASE_UNAVAILABLE,
    STORY_INDEX_SCHEMA_UNAVAILABLE,
)


WORKSPACE_ID = "workspace-reconcile"
RUN_A = "run_" + "1" * 32
RUN_B = "run_" + "2" * 32
THREAD_A = "thread-authorized-a"
THREAD_B = "thread-authorized-b"
PROJECT_A = "project-a"
PROJECT_B = "project-b"
STORY_A = "story-a"
STORY_B = "story-b"
MANIFEST_REVISION = "sha256:" + "a" * 64
SCRIPT_REVISION = "sha256:" + "b" * 64


class _Rows:
    def __init__(self, rows: list[Any] | None = None) -> None:
        self.rows = rows or []

    def fetchall(self) -> list[Any]:
        return self.rows

    def fetchone(self) -> Any | None:
        return self.rows[0] if self.rows else None


class _TransactionDB:
    def __init__(self, *, fail_execute: bool = False) -> None:
        self.fail_execute = fail_execute
        self.statements: list[tuple[str, tuple[object, ...]]] = []
        self.rollback_count = 0
        self.close_count = 0

    def execute(
        self,
        statement: str,
        parameters: tuple[object, ...] = (),
    ) -> _Rows:
        self.statements.append((statement, parameters))
        if self.fail_execute:
            raise RuntimeError("database unavailable")
        return _Rows()

    def rollback(self) -> None:
        self.rollback_count += 1

    def commit(self) -> None:  # pragma: no cover - a call is always a failure.
        raise AssertionError("dry-run must never commit")

    def close(self) -> None:
        self.close_count += 1


def _authority_metadata(run_id: str, project_id: str) -> str:
    return json.dumps(
        {
            "story_workspace_episode_identity": {
                "schema": "story-workspace-episode-authority/v1",
                "workflow_run_id": run_id,
                "episode_uid": "c" * 32,
                "story_slug": project_id,
                "episode_code": "EP01",
            }
        }
    )


def _authorized_row(
    run_id: str,
    *,
    thread_id: str = THREAD_A,
    project_id: str = PROJECT_A,
) -> dict[str, object]:
    return {
        "run_id": run_id,
        "workspace_id": WORKSPACE_ID,
        "thread_id": thread_id,
        "source_metadata": _authority_metadata(run_id, project_id),
    }


def _candidate(
    run_id: str,
    *,
    thread_id: str = THREAD_A,
) -> ArtifactStoryIndexRunCandidate:
    return ArtifactStoryIndexRunCandidate(
        run_id=run_id,
        workspace_id=WORKSPACE_ID,
        created_by="7",
        actor_id=7,
        related_workspace_id=WORKSPACE_ID,
        actor_user_id=7,
        thread_id=thread_id,
        source_message_id="message-source",
        source_role="user",
    )


def _projection(
    run_id: str = RUN_A,
    *,
    thread_id: str = THREAD_A,
    project_id: str = PROJECT_A,
    story_id: str = STORY_A,
) -> ArtifactStoryProjection:
    return ArtifactStoryProjection(
        story_id=story_id,
        workspace_id=WORKSPACE_ID,
        author_id=7,
        source_run_id=run_id,
        source_thread_ref=thread_id,
        source_project_id=project_id,
        title="Project",
        episode_count=2,
        artifact_manifest_revision=MANIFEST_REVISION,
        script_revision=SCRIPT_REVISION,
        script_size_bytes=321,
    )


def _record(
    *,
    run_id: str | None = RUN_A,
    thread_id: str | None = THREAD_A,
    project_id: str = PROJECT_A,
    story_id: str = STORY_A,
) -> ArtifactStoryIndexRecord:
    return ArtifactStoryIndexRecord(
        story_id=story_id,
        identifier=project_id,
        title="Project",
        workspace_id=WORKSPACE_ID,
        source_run_id=run_id,
        source_thread_ref=thread_id,
        source_project_id=project_id,
        artifact_manifest_revision=MANIFEST_REVISION,
        script_revision=SCRIPT_REVISION,
        artifact_sync_status="indexed",
        artifact_indexed_at=object(),
        artifact_sync_error_code=None,
        episode_count=2,
        script_size_bytes=321,
        artifact_available=True,
        reconcile_version=1,
    )


class _ProjectionMap:
    def __init__(
        self,
        projections: dict[str, ArtifactStoryProjection],
        events: list[str],
        *,
        error: ArtifactStoryProjectionError | None = None,
    ) -> None:
        self.projections = projections
        self.events = events
        self.error = error

    def project(self, **kwargs: Any) -> ArtifactStoryProjection:
        run_id = str(kwargs["workflow_run"]["run_id"])
        self.events.append(f"project:{run_id}")
        if self.error is not None:
            raise self.error
        return self.projections[run_id]


class _Repository:
    def __init__(
        self,
        *,
        candidates: list[ArtifactStoryIndexRunCandidate] | None = None,
        authorized_rows: dict[str, dict[str, object]] | None = None,
        indexes: dict[tuple[str, str], ArtifactStoryIndexRecord] | None = None,
        stories: list[ArtifactStoryIndexRecord] | None = None,
        events: list[str] | None = None,
        schema_error: str | None = None,
    ) -> None:
        self.candidates = sorted(candidates or [], key=lambda item: item.run_id)
        self.authorized_rows = authorized_rows or {}
        self.indexes = indexes or {}
        self.stories = sorted(stories or [], key=lambda item: item.story_id)
        self.events = events if events is not None else []
        self.schema_error = schema_error
        self.run_calls: list[dict[str, object]] = []
        self.story_calls: list[dict[str, object]] = []

    def require_schema(self) -> None:
        if self.schema_error is not None:
            raise ArtifactStoryIndexRepositoryError(
                self.schema_error,
                retryable=True,
            )

    def list_run_candidates(
        self,
        *,
        workspace_id: str | None,
        run_id: str | None,
        after: str | None,
        limit: int,
    ) -> list[ArtifactStoryIndexRunCandidate]:
        self.run_calls.append(
            {
                "workspace_id": workspace_id,
                "run_id": run_id,
                "after": after,
                "limit": limit,
            }
        )
        rows = [
            item
            for item in self.candidates
            if (workspace_id is None or item.workspace_id == workspace_id)
            and (run_id is None or item.run_id == run_id)
            and (after is None or item.run_id > after)
        ]
        return rows[:limit]

    def authorize_run(
        self,
        candidate: ArtifactStoryIndexRunCandidate,
    ) -> dict[str, object] | None:
        self.events.append(f"authorize:{candidate.run_id}")
        return self.authorized_rows.get(candidate.run_id)

    def find_index(
        self,
        *,
        workspace_id: str,
        project_id: str,
    ) -> ArtifactStoryIndexRecord | None:
        return self.indexes.get((workspace_id, project_id))

    def list_story_records(
        self,
        *,
        workspace_id: str | None,
        run_id: str | None,
        after: str | None,
        limit: int,
    ) -> list[ArtifactStoryIndexRecord]:
        self.story_calls.append(
            {
                "workspace_id": workspace_id,
                "run_id": run_id,
                "after": after,
                "limit": limit,
            }
        )
        rows = [
            item
            for item in self.stories
            if (workspace_id is None or item.workspace_id == workspace_id)
            and (run_id is None or item.source_run_id == run_id)
            and (after is None or item.story_id > after)
        ]
        return rows[:limit]


def _service(
    repository: _Repository,
    projections: dict[str, ArtifactStoryProjection],
    events: list[str],
    *,
    projector_error: ArtifactStoryProjectionError | None = None,
    monotonic: Any = None,
) -> ArtifactStoryIndexReconcileService:
    def resolve(thread_id: str) -> Path:
        events.append(f"resolve:{thread_id}")
        return Path("/private/tmp") / thread_id

    def read_surface(workspace: Path, run_id: str, authority: Any) -> object:
        events.append(f"surface:{run_id}")
        return object()

    return ArtifactStoryIndexReconcileService(
        repository_factory=lambda _db: repository,
        projector=_ProjectionMap(projections, events, error=projector_error),
        workspace_resolver=resolve,
        surface_reader=read_surface,
        monotonic=monotonic or (lambda: 0.0),
    )


def test_dry_run_authorizes_before_resolving_and_reports_create() -> None:
    events: list[str] = []
    candidate = _candidate(RUN_A)
    repository = _Repository(
        candidates=[candidate],
        authorized_rows={RUN_A: _authorized_row(RUN_A)},
        events=events,
    )
    db = _TransactionDB()

    report = _service(repository, {RUN_A: _projection()}, events).dry_run(
        db=db,
        limit=5,
    )

    assert events[:2] == [f"authorize:{RUN_A}", f"resolve:{THREAD_A}"]
    assert report.public_dict() == {
        "projects_discovered": 1,
        "episodes_discovered": 2,
        "stories_indexable": 1,
        "indexes_existing": 0,
        "indexes_to_create": 1,
        "indexes_to_update": 0,
        "indexes_unchanged": 0,
        "conflicts": 0,
        "invalid_artifacts": 0,
        "missing_relations": 0,
        "database_status": "available",
        "applied": False,
        "next_cursor": None,
    }
    assert db.statements == [("SET TRANSACTION READ ONLY", ())]
    assert db.rollback_count == 1


def test_unauthorized_run_never_resolves_a_thread_workspace() -> None:
    events: list[str] = []
    repository = _Repository(candidates=[_candidate(RUN_A)], events=events)
    db = _TransactionDB()

    report = _service(repository, {}, events).dry_run(db=db, limit=5)

    assert events == [f"authorize:{RUN_A}"]
    assert report.missing_relations == 1
    assert report.projects_discovered == 0
    assert report.applied is False


def test_empty_db_first_scan_never_touches_the_shared_artifact_root() -> None:
    repository = _Repository()

    def forbidden_resolver(_thread_id: str) -> Path:
        raise AssertionError("shared Artifact root must not be scanned")

    service = ArtifactStoryIndexReconcileService(
        repository_factory=lambda _db: repository,
        workspace_resolver=forbidden_resolver,
    )

    report = service.dry_run(db=_TransactionDB(), limit=5)

    assert report.projects_discovered == 0
    assert report.next_cursor is None


def test_story_source_thread_ref_is_not_resolved_before_db_reauthorization() -> None:
    events: list[str] = []
    untrusted_record = _record(thread_id="..")
    repository = _Repository(
        candidates=[_candidate(RUN_A)],
        authorized_rows={RUN_A: _authorized_row(RUN_A)},
        stories=[untrusted_record],
        events=events,
    )
    cursor = encode_reconcile_cursor(
        ArtifactStoryIndexReconcileCursor(phase="stories")
    )

    report = _service(repository, {RUN_A: _projection()}, events).dry_run(
        db=_TransactionDB(),
        cursor=cursor,
        limit=5,
    )

    assert events == [f"authorize:{RUN_A}"]
    assert report.conflicts == 1
    assert report.indexes_existing == 1


def test_cursor_continues_run_phase_then_advances_to_story_phase() -> None:
    events: list[str] = []
    repository = _Repository(
        candidates=[_candidate(RUN_A), _candidate(RUN_B, thread_id=THREAD_B)],
        authorized_rows={
            RUN_A: _authorized_row(RUN_A),
            RUN_B: _authorized_row(
                RUN_B,
                thread_id=THREAD_B,
                project_id=PROJECT_B,
            ),
        },
        events=events,
    )
    service = _service(
        repository,
        {
            RUN_A: _projection(),
            RUN_B: _projection(
                RUN_B,
                thread_id=THREAD_B,
                project_id=PROJECT_B,
                story_id=STORY_B,
            ),
        },
        events,
    )

    first = service.dry_run(db=_TransactionDB(), limit=1)
    first_position = decode_reconcile_cursor(
        first.next_cursor,
        workspace_id=None,
        run_id=None,
    )
    assert first_position == ArtifactStoryIndexReconcileCursor(
        phase="runs",
        after=RUN_A,
    )

    second = service.dry_run(
        db=_TransactionDB(),
        limit=1,
        cursor=first.next_cursor,
    )
    second_position = decode_reconcile_cursor(
        second.next_cursor,
        workspace_id=None,
        run_id=None,
    )
    assert second_position == ArtifactStoryIndexReconcileCursor(phase="stories")
    assert repository.run_calls[1]["after"] == RUN_A


def test_cursor_is_bound_to_workspace_and_run_scope_before_db_access() -> None:
    cursor = encode_reconcile_cursor(
        ArtifactStoryIndexReconcileCursor(workspace_id=WORKSPACE_ID, run_id=RUN_A)
    )
    db = _TransactionDB()

    with pytest.raises(ValueError, match="cursor is invalid"):
        ArtifactStoryIndexReconcileService().dry_run(
            db=db,
            workspace_id="different-workspace",
            run_id=RUN_A,
            cursor=cursor,
        )

    assert db.statements == []
    assert db.rollback_count == 0


def test_deadline_returns_a_resumable_cursor_without_resolving() -> None:
    events: list[str] = []
    repository = _Repository(
        candidates=[_candidate(RUN_A)],
        authorized_rows={RUN_A: _authorized_row(RUN_A)},
        events=events,
    )
    clock = iter((0.0, 11.0))
    service = _service(
        repository,
        {RUN_A: _projection()},
        events,
        monotonic=lambda: next(clock),
    )

    report = service.dry_run(
        db=_TransactionDB(),
        limit=5,
        deadline_seconds=10.0,
    )

    assert events == []
    assert decode_reconcile_cursor(
        report.next_cursor,
        workspace_id=None,
        run_id=None,
    ) == ArtifactStoryIndexReconcileCursor(phase="runs")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_run_id", RUN_B),
        ("script_size_bytes", 999),
        ("artifact_sync_status", "stale"),
        ("artifact_indexed_at", None),
        ("artifact_sync_error_code", "artifact_missing"),
        ("artifact_available", False),
        ("reconcile_version", 0),
    ],
)
def test_record_drift_fields_require_an_update(field: str, value: object) -> None:
    projection = _projection()
    record = _record()
    assert not ArtifactStoryIndexReconcileService._record_needs_update(
        record,
        projection,
    )
    assert ArtifactStoryIndexReconcileService._record_needs_update(
        replace(record, **{field: value}),
        projection,
    )


def test_invalid_artifact_is_not_counted_as_an_actionable_update() -> None:
    events: list[str] = []
    repository = _Repository(
        candidates=[_candidate(RUN_A)],
        authorized_rows={RUN_A: _authorized_row(RUN_A)},
        stories=[_record()],
        events=events,
    )
    cursor = encode_reconcile_cursor(
        ArtifactStoryIndexReconcileCursor(phase="stories")
    )
    service = _service(
        repository,
        {RUN_A: _projection()},
        events,
        projector_error=ArtifactStoryProjectionError(
            "story_index_invalid_artifact",
            retryable=False,
        ),
    )

    report = service.dry_run(db=_TransactionDB(), cursor=cursor, limit=5)

    assert report.invalid_artifacts == 1
    assert report.indexes_existing == 1
    assert report.indexes_to_update == 0


@pytest.mark.parametrize(
    ("error_code", "expected_status"),
    [
        (STORY_INDEX_SCHEMA_UNAVAILABLE, "schema_unavailable"),
        (STORY_INDEX_DATABASE_UNAVAILABLE, "unavailable"),
    ],
)
def test_repository_failures_are_structured_and_rolled_back(
    error_code: str,
    expected_status: str,
) -> None:
    repository = _Repository(schema_error=error_code)
    db = _TransactionDB()

    report = _service(repository, {}, []).dry_run(db=db)

    assert report.database_status == expected_status
    assert report.applied is False
    assert db.rollback_count >= 1


def test_database_failure_starting_read_only_transaction_is_structured() -> None:
    db = _TransactionDB(fail_execute=True)

    report = ArtifactStoryIndexReconcileService().dry_run(db=db)

    assert report.database_status == "unavailable"
    assert report.applied is False
    assert db.rollback_count == 1


class _ReadOnlyRepositoryDB(_TransactionDB):
    def execute(
        self,
        statement: str,
        parameters: tuple[object, ...] = (),
    ) -> _Rows:
        self.statements.append((statement, parameters))
        if "information_schema.columns" in statement:
            return _Rows(
                [
                    {"column_name": column}
                    for column in repository_module._INDEX_COLUMNS
                ]
            )
        if "pg_catalog.pg_index" in statement:
            return _Rows(
                [
                    {
                        "column_names": [
                            "workspace_id",
                            "artifact_source_type",
                            "source_project_id",
                        ],
                        "key_count": 3,
                        "all_direct_columns": True,
                        "is_full_index": True,
                    }
                ]
            )
        return _Rows()


def test_real_repository_dry_run_issues_only_read_sql_and_rolls_back() -> None:
    db = _ReadOnlyRepositoryDB()

    report = ArtifactStoryIndexReconcileService().dry_run(db=db, limit=3)

    assert report.database_status == "available"
    assert db.rollback_count == 1
    assert db.statements[0][0] == "SET TRANSACTION READ ONLY"
    assert all(
        statement.lstrip().upper().startswith(("SELECT", "SET TRANSACTION READ ONLY"))
        for statement, _ in db.statements
    )


def test_list_records_compatibly_filters_by_source_run_id() -> None:
    db = _ReadOnlyRepositoryDB()
    repository = ArtifactStoryIndexRepository(db)

    assert repository.list_records(
        workspace_id=WORKSPACE_ID,
        source_run_id=RUN_A,
        cursor=STORY_A,
        limit=7,
    ) == []

    statement, parameters = db.statements[-1]
    assert "AND source_run_id = %s" in statement
    assert "AND id > %s" in statement
    assert parameters == (
        ARTIFACT_SOURCE_TYPE,
        WORKSPACE_ID,
        RUN_A,
        STORY_A,
        7,
    )


def test_reviewed_revision_remains_a_schema_gate_but_not_a_browser_dto() -> None:
    assert "reviewed_script_revision" in repository_module._INDEX_COLUMNS
    assert "reviewed_script_revision" not in PUBLIC_STORY_COLUMNS


def test_cli_has_only_dry_run_mode(capsys: pytest.CaptureFixture[str]) -> None:
    arguments = reconcile_cli.build_parser().parse_args([])
    assert arguments.dry_run is True
    assert not hasattr(arguments, "apply")

    with pytest.raises(SystemExit) as raised:
        reconcile_cli.build_parser().parse_args(["--apply"])
    assert raised.value.code == 2
    assert "--apply" not in reconcile_cli.build_parser().format_help()
    capsys.readouterr()


def test_cli_reports_connection_failure_without_an_exception() -> None:
    arguments = reconcile_cli.build_parser().parse_args([])

    report = reconcile_cli.execute_dry_run(
        arguments,
        db_factory=lambda: (_ for _ in ()).throw(RuntimeError("offline")),
    )

    assert report.database_status == "unavailable"
    assert report.applied is False


def test_cli_closes_with_rollback_and_emits_structured_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db = _TransactionDB()
    arguments = reconcile_cli.build_parser().parse_args(
        [
            "--workspace-id",
            WORKSPACE_ID,
            "--run-id",
            RUN_A,
            "--limit",
            "4",
            "--deadline-seconds",
            "3",
        ]
    )

    class _Service:
        def dry_run(self, **kwargs: object) -> ArtifactStoryIndexReconcileReport:
            assert kwargs["workspace_id"] == WORKSPACE_ID
            assert kwargs["run_id"] == RUN_A
            assert kwargs["limit"] == 4
            assert kwargs["deadline_seconds"] == 3.0
            return ArtifactStoryIndexReconcileReport(projects_discovered=1)

    report = reconcile_cli.execute_dry_run(
        arguments,
        db_factory=lambda: db,
        service_factory=_Service,
    )
    assert report.projects_discovered == 1
    assert db.rollback_count == 1
    assert db.close_count == 1

    monkeypatch.setattr(reconcile_cli, "execute_dry_run", lambda _arguments: report)
    assert reconcile_cli.main([]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["projects_discovered"] == 1
    assert payload["database_status"] == "available"
    assert payload["applied"] is False
    assert set(payload) == set(ArtifactStoryIndexReconcileReport().public_dict())
