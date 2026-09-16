# [Input] Production SQL-bearing modules and PostgreSQL-only Story Workspace query contracts.
# [Output] Reject runtime DDL/SQLite fallbacks and lock the Dream re-entry authorization predicates.
# [Pos] Static PostgreSQL boundary regression suite.
# [Sync] 2026-08-31: allow mutable current-Agent selection while keeping launch metadata internally consistent.
# [Sync] 2026-09-16: remove SQL-free manifest and workspace validators from the active SQL inventory.

"""Regression gates for the PostgreSQL-only Dream runtime SQL boundary."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from backend.services.story_workspace.dream_reentry_service import (
    StoryWorkspaceDreamReentryService,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_PRODUCTION_SQL_FILES = (
    "backend/services/deck/story_workflow_application.py",
    "backend/services/story_workspace/dream_confirmation_service.py",
    "backend/services/story_workspace/agent_integration.py",
    "backend/services/story_workspace/dream_launch_infrastructure.py",
    "backend/services/story_workspace/dream_reentry_service.py",
    "backend/libs/claude_agent_kit/server/story_workspace_tool.py",
    "backend/routers/story_workspace.py",
    "backend/script/import_diaries.py",
)
_SQL_MARKER = re.compile(
    r"^\s*(?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|PRAGMA|BEGIN|"
    r"WHERE|AND|OR|SET|VALUES|JOIN|ORDER\s+BY|LIMIT)\b",
    re.IGNORECASE,
)
_FORBIDDEN_PRODUCTION_SQL = {
    "qmark placeholder": re.compile(r"\?"),
    "SQLite INSERT OR": re.compile(r"\bINSERT\s+OR\b", re.IGNORECASE),
    "SQLite rowid": re.compile(r"\browid\b", re.IGNORECASE),
    "SQLite JSON function": re.compile(
        r"\bjson_(?:valid|extract|each)\s*\(", re.IGNORECASE
    ),
    "SQLite immediate transaction": re.compile(
        r"\bBEGIN\s+IMMEDIATE\b", re.IGNORECASE
    ),
    "SQLite PRAGMA": re.compile(r"\bPRAGMA\b", re.IGNORECASE),
    "runtime DDL": re.compile(r"\bCREATE\s+(?:TABLE|TRIGGER)\b", re.IGNORECASE),
}


def _sql_literals(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    literals: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        line = getattr(node, "lineno", 0)
        if _SQL_MARKER.search(node.value):
            literals.append((line, node.value))
    return literals


def test_production_sql_uses_postgresql_semantics_only() -> None:
    failures: list[str] = []
    for relative_path in _PRODUCTION_SQL_FILES:
        path = _REPOSITORY_ROOT / relative_path
        for line, sql in _sql_literals(path):
            for label, pattern in _FORBIDDEN_PRODUCTION_SQL.items():
                if pattern.search(sql):
                    failures.append(f"{relative_path}:{line}: {label}")
    assert failures == []


def test_unreachable_sql_boundaries_are_retired() -> None:
    assert not (
        _REPOSITORY_ROOT
        / "backend/services/claude_agent/remote_interaction_guard.py"
    ).exists()
    manifest_source = (
        _REPOSITORY_ROOT / "backend/services/deck_plugin/manifest_validator.py"
    ).read_text(encoding="utf-8")
    assert "db.execute" not in manifest_source
    assert "deck_plugin_releases" not in manifest_source
    application_source = (
        _REPOSITORY_ROOT / "backend/services/deck/story_workflow_application.py"
    ).read_text(encoding="utf-8")
    assert "StoryWorkflowRunApplicationService" not in application_source
    assert "get_story_workflow_run_application_service" not in application_source


class _RecordingCursor:
    rowcount = 1

    def fetchall(self) -> list[object]:
        return []


class _RecordingDb:
    def __init__(self) -> None:
        self.executions: list[tuple[str, tuple[object, ...]]] = []
        self.commit_count = 0
        self.rollback_count = 0

    def execute(
        self,
        sql: str,
        parameters: tuple[object, ...] | list[object] = (),
    ) -> _RecordingCursor:
        self.executions.append((sql, tuple(parameters)))
        return _RecordingCursor()

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1


def test_dream_reentry_queries_have_postgresql_jsonb_and_bound_parameters() -> None:
    db = _RecordingDb()
    assert StoryWorkspaceDreamReentryService._query_authorized_rows(db, 7) == []
    authorized_sql, authorized_parameters = db.executions[-1]
    assert "jsonb_array_elements" in authorized_sql
    assert "::jsonb" in authorized_sql
    assert "IS NOT DISTINCT FROM thread.voice_id" not in authorized_sql
    assert authorized_sql.count("IS NOT DISTINCT FROM") == 1
    assert authorized_sql.count("%s") == len(authorized_parameters) == 5

    facts = StoryWorkspaceDreamReentryService._confirmation_facts(
        db,
        [{"thread_id": "thread-1", "run_id": "run-1"}],
        7,
    )
    assert facts == {"run-1": (False, False)}
    confirmation_sql, confirmation_parameters = db.executions[-1]
    assert "::jsonb ->> 'kind'" in confirmation_sql
    assert confirmation_sql.count("%s") == len(confirmation_parameters) == 3
