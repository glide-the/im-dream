"""Explicit test-only bridge for legacy file-backed unit suites.

The production ``database`` module is PostgreSQL-only.  A few historical API
tests still need their handwritten SQLite fixture schema while they are being
replaced by PostgreSQL contracts.  This helper injects fresh connections only
into the test process; it never changes runtime configuration or exports a
fallback from production code.
"""

from __future__ import annotations

from pathlib import Path
import sqlite3
import sys
from types import ModuleType
from unittest.mock import patch

from backend.schema import legacy_main_sqlite


class LegacyDatabaseModuleFixture:
    def __init__(self, database_module: ModuleType, path: Path) -> None:
        self.database_module = database_module
        self.path = path
        self._patchers: list[object] = []

    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    def start(self, *, initialize_legacy_schema: bool = False) -> None:
        modules: list[ModuleType] = [self.database_module]
        source_file = getattr(self.database_module, "__file__", None)
        for name in ("database", "backend.database"):
            candidate = sys.modules.get(name)
            if (
                isinstance(candidate, ModuleType)
                and candidate not in modules
                and getattr(candidate, "__file__", None) == source_file
            ):
                modules.append(candidate)
        for module in modules:
            patcher = patch.object(module, "get_db", side_effect=self.connect)
            patcher.start()
            self._patchers.append(patcher)

        if initialize_legacy_schema:
            connection = self.connect()
            try:
                legacy_main_sqlite.create_tables(connection)
                legacy_main_sqlite.create_agent_session_tables(connection)
                legacy_main_sqlite.create_claude_plugin_tables(connection)
            finally:
                connection.close()

    def stop(self) -> None:
        while self._patchers:
            self._patchers.pop().stop()

