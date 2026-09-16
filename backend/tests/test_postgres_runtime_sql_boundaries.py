# [Input] Dream backend and Next server source graphs after Admin data-service migration.
# [Output] Reject database clients, bootstrap, SQL/table access and retired repositories.
# [Pos] Static production database-closure regression suite.
# [Sync] 2026-09-16: scan all backend production Python for database imports and SQL.

"""Prove Dream production modules can reach persistence only through Admin DTO clients."""

from __future__ import annotations

import ast
import re
from pathlib import Path


_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_BACKEND_ROOT = _REPOSITORY_ROOT / "backend"
_NON_PRODUCTION_PARTS = {
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "tests",
}
_FORBIDDEN_IMPORT_ROOTS = {
    "aiosqlite",
    "asyncpg",
    "database",
    "psycopg",
    "psycopg2",
    "sqlite3",
    "sqlalchemy",
}
_RETIRED_DATABASE_PATHS = (
    "backend/database.py",
    "backend/persistence",
    "backend/schema",
    "backend/services/workflow/run_service.py",
    "backend/services/story_workspace/dream_workflow_lifecycle_service.py",
    "backend/services/story_workspace/artifact_story_index_repository.py",
    "backend/services/story_workspace/artifact_story_index_service.py",
    "backend/services/story_workspace/artifact_story_index_reconcile.py",
    "backend/script/reconcile_story_artifact_index.py",
)
_SQL_STATEMENT = re.compile(
    r"^\s*(?:"
    r"SELECT\b[\s\S]*\bFROM\b|"
    r"WITH\b[\s\S]*\b(?:SELECT|INSERT|UPDATE|DELETE)\b|"
    r"INSERT\s+INTO\b|"
    r"UPDATE\b[\s\S]*\bSET\b|"
    r"DELETE\s+FROM\b|"
    r"(?:CREATE|ALTER|DROP)\s+(?:TABLE|INDEX|SCHEMA|TRIGGER|FUNCTION)\b"
    r")",
    re.IGNORECASE,
)
_FRONTEND_ROOTS = (
    _REPOSITORY_ROOT / "frontend/app",
    _REPOSITORY_ROOT / "frontend/packages",
)
_FRONTEND_SUFFIXES = {".cjs", ".js", ".mjs", ".ts", ".tsx"}
_FRONTEND_NON_PRODUCTION_PARTS = {
    ".next",
    "__tests__",
    "coverage",
    "e2e",
    "node_modules",
}
_FRONTEND_DATABASE_IMPORT = re.compile(
    r"(?:\bfrom\s+|\brequire\s*\(|\bimport\s*\()\s*[\"']"
    r"(?:@prisma/client|better-sqlite3|drizzle-orm|mysql2?|pg|postgres|sqlite3?)"
    r"(?:[/\"'])"
)
_FRONTEND_DATABASE_MARKERS = (
    "DATABASE_URL",
    "INK_DATABASE_ENV_FILE",
    "TEST_DATABASE_URL",
    "postgresql://",
)
_STORY_RUNTIME_PATHS = (
    "backend/services/deck/story_workflow_application.py",
    "backend/services/story_workspace/dream_reentry_service.py",
    "backend/services/story_workspace/dream_artifact_turn_hook.py",
    "backend/routers/story_workspace.py",
)
_FORBIDDEN_STORY_STORAGE_MARKERS = (
    "workflow_runs",
    "story_workspace_stories",
    "story_workspace_workspaces",
    "chat_threads",
    "database.get_db",
    "DATABASE_URL",
)


def _runtime_python_files() -> tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for path in _BACKEND_ROOT.rglob("*.py")
            if not _NON_PRODUCTION_PARTS.intersection(path.relative_to(_BACKEND_ROOT).parts)
        )
    )


def _frontend_runtime_files() -> tuple[Path, ...]:
    files: list[Path] = []
    for root in _FRONTEND_ROOTS:
        files.extend(
            path
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix in _FRONTEND_SUFFIXES
            and not _FRONTEND_NON_PRODUCTION_PARTS.intersection(path.relative_to(root).parts)
            and ".test." not in path.name
            and ".spec." not in path.name
        )
    return tuple(sorted(set(files)))


def _forbidden_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    failures: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        else:
            continue
        for name in names:
            root = name.split(".", 1)[0]
            if root in _FORBIDDEN_IMPORT_ROOTS:
                failures.append(f"{path.relative_to(_REPOSITORY_ROOT)}:{node.lineno}:{name}")
    return failures


def _joined_string_text(node: ast.JoinedStr) -> str:
    return "".join(
        part.value if isinstance(part, ast.Constant) and isinstance(part.value, str) else "{}"
        for part in node.values
    )


def _sql_literals(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    failures: list[str] = []
    for node in ast.walk(tree):
        value: str | None = None
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value
        elif isinstance(node, ast.JoinedStr):
            value = _joined_string_text(node)
        if value is not None and _SQL_STATEMENT.match(value):
            failures.append(f"{path.relative_to(_REPOSITORY_ROOT)}:{node.lineno}")
    return failures


def test_runtime_module_graph_has_no_database_driver_or_database_import() -> None:
    failures = [
        failure
        for path in _runtime_python_files()
        for failure in _forbidden_imports(path)
    ]
    assert failures == []


def test_runtime_module_graph_has_no_sql_statements() -> None:
    failures = [
        failure
        for path in _runtime_python_files()
        for failure in _sql_literals(path)
    ]
    assert failures == []


def test_frontend_runtime_has_no_database_client_or_database_url() -> None:
    failures: list[str] = []
    for path in _frontend_runtime_files():
        source = path.read_text(encoding="utf-8")
        relative = path.relative_to(_REPOSITORY_ROOT)
        if _FRONTEND_DATABASE_IMPORT.search(source):
            failures.append(f"{relative}: database client import")
        for marker in _FRONTEND_DATABASE_MARKERS:
            if marker in source:
                failures.append(f"{relative}: {marker}")
    assert failures == []


def test_server_has_no_database_credential_or_pool_lifecycle() -> None:
    source = (_REPOSITORY_ROOT / "backend/server.py").read_text(encoding="utf-8")
    for marker in (
        "DATABASE_URL",
        "INK_LOAD_DATABASE_URL_FROM_ENV_FILE",
        "startup_database",
        "shutdown_database",
        "database.init_db",
        "database.close_db",
    ):
        assert marker not in source


def test_story_workspace_runtime_has_no_sql_or_table_access() -> None:
    failures: list[str] = []
    for relative in _STORY_RUNTIME_PATHS:
        source = (_REPOSITORY_ROOT / relative).read_text(encoding="utf-8")
        for marker in _FORBIDDEN_STORY_STORAGE_MARKERS:
            if marker in source:
                failures.append(f"{relative}: {marker}")
    assert failures == []


def test_replaced_local_database_services_are_retired() -> None:
    assert [
        relative
        for relative in _RETIRED_DATABASE_PATHS
        if (_REPOSITORY_ROOT / relative).exists()
    ] == []
