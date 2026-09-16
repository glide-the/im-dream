# [Input] Dream runtime Python module graph after Admin data-service migration.
# [Output] Reject database driver imports, PostgreSQL bootstrap, SQL/table access and retired local repositories.
# [Pos] Static production database-closure regression suite.
# [Sync] 2026-09-16: replace PostgreSQL-semantic tests with a zero-runtime-database gate.

"""Prove Dream production modules can reach persistence only through Admin DTO clients."""

from __future__ import annotations

import ast
from pathlib import Path


_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_RUNTIME_FILES = (
    _REPOSITORY_ROOT / "backend/server.py",
    _REPOSITORY_ROOT / "backend/agent_factory.py",
)
_RUNTIME_TREES = tuple(
    _REPOSITORY_ROOT / relative
    for relative in (
        "backend/routers",
        "backend/services",
        "backend/claude_agent",
        "backend/claude_mcp",
        "backend/libs/claude_agent_kit/server",
    )
)
_FORBIDDEN_IMPORT_ROOTS = {
    "asyncpg",
    "database",
    "psycopg",
    "psycopg2",
    "sqlalchemy",
}
_RETIRED_DATABASE_PATHS = (
    "backend/services/workflow/run_service.py",
    "backend/services/story_workspace/dream_workflow_lifecycle_service.py",
    "backend/services/story_workspace/artifact_story_index_repository.py",
    "backend/services/story_workspace/artifact_story_index_service.py",
    "backend/services/story_workspace/artifact_story_index_reconcile.py",
    "backend/script/reconcile_story_artifact_index.py",
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
    files = list(_RUNTIME_FILES)
    for root in _RUNTIME_TREES:
        files.extend(root.rglob("*.py"))
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


def test_runtime_module_graph_has_no_database_driver_or_database_import() -> None:
    failures = [
        failure
        for path in _runtime_python_files()
        for failure in _forbidden_imports(path)
    ]
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
