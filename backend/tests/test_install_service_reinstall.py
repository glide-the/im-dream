"""Unit tests for PluginInstallService reinstall/revive semantics.

Covers the UNIQUE-constraint crash seen when reinstalling a plugin whose
previous installation row was soft-deleted (status='uninstalled'): the
service must revive the existing row in place instead of inserting a
duplicate, and unexpected exceptions must still move the operation row to
a terminal error state.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import database
from services.claude_plugin import cli as plugin_cli
from services.claude_plugin import install_service
from services.claude_plugin.install_service import (
    PLUGIN_INSTALL_FAILED,
    PluginInstallError,
    PluginInstallService,
)

PACKAGE_SPEC = "drama-forge@drama-studio"


def _fake_execution(argv: list[str]) -> plugin_cli.CliExecution:
    return plugin_cli.CliExecution(
        executable="/fake/claude",
        argv=list(argv),
        cwd="/fake/cwd",
        cli_version="2.1.220",
        exit_code=0,
        timed_out=False,
        stdout="",
        stderr="",
        started_at="2026-08-03T00:00:00+00:00",
        finished_at="2026-08-03T00:00:01+00:00",
        duration_ms=1000,
    )


class ReinstallReviveTests(unittest.TestCase):
    """install → uninstall → install must revive, never violate UNIQUE."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._env = mock.patch.dict(
            os.environ,
            {"INK_CLAUDE_PLUGIN_RUNTIME_ROOT": str(self.root / "runtime")},
        )
        self._env.start()
        # Plugin source tree the fake registry record points at.
        self.plugin_root = self.root / "src" / "drama-forge"
        (self.plugin_root / ".claude-plugin").mkdir(parents=True)
        (self.plugin_root / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": "drama-forge", "version": "1.0.1"})
        )
        (self.plugin_root / "skills").mkdir(parents=True)
        (self.plugin_root / "skills" / "SKILL.md").write_text("# skill")
        self.db = sqlite3.connect(":memory:")
        database.create_claude_plugin_tables(self.db)
        self.db.commit()
        # Stub the CLI boundary: marketplace ensure, registry lookup, run.
        self._patches = [
            mock.patch.object(
                install_service, "_ensure_marketplace", lambda spec, evidence: None
            ),
            mock.patch.object(
                install_service,
                "_registry_entry_for",
                lambda spec: {
                    "installPath": str(self.plugin_root),
                    "version": "1.0.1",
                    "gitCommitSha": "abc123",
                },
            ),
            mock.patch.object(
                plugin_cli,
                "run_claude",
                lambda argv, *, cwd, timeout_seconds: _fake_execution(argv),
            ),
        ]
        for patcher in self._patches:
            patcher.start()

    def tearDown(self) -> None:
        for patcher in self._patches:
            patcher.stop()
        self._env.stop()
        self.db.close()
        self._tmp.cleanup()

    def _install(self) -> dict:
        return PluginInstallService(self.db).install(PACKAGE_SPEC)

    def _installation_count(self) -> int:
        row = self.db.execute(
            "SELECT COUNT(*) FROM claude_plugin_installations "
            "WHERE package_name = 'drama-forge'"
        ).fetchone()
        return int(row[0])

    def test_reinstall_after_uninstall_revives_same_installation(self) -> None:
        op1 = self._install()
        inst_id = op1["installation_id"]
        service = PluginInstallService(self.db)
        service.uninstall(inst_id)
        self.assertEqual(service.get_installation(inst_id)["status"], "uninstalled")

        op2 = self._install()
        self.assertEqual(op2["status"], "ready", op2.get("error_summary"))
        self.assertEqual(
            op2["installation_id"], inst_id,
            "reinstall must revive the same installation row",
        )
        inst = service.get_installation(inst_id)
        self.assertEqual(inst["status"], "ready")
        self.assertEqual(inst["operation_id"], op2["id"])
        self.assertIsNone(inst["error_code"])
        self.assertIsNone(inst["error_summary"])
        self.assertEqual(
            self._installation_count(), 1,
            "reinstall must not insert a duplicate row",
        )

    def test_repeated_install_replays_ready_record(self) -> None:
        op1 = self._install()
        op2 = self._install()
        self.assertEqual(op2["status"], "ready", op2.get("error_summary"))
        self.assertEqual(op2["installation_id"], op1["installation_id"])
        self.assertEqual(self._installation_count(), 1)

    def test_unexpected_exception_marks_operation_error(self) -> None:
        with mock.patch.object(
            install_service.artifact_store,
            "import_tree",
            side_effect=sqlite3.IntegrityError(
                "UNIQUE constraint failed: "
                "claude_plugin_installations.package_name"
            ),
        ):
            service = PluginInstallService(self.db)
            with self.assertRaises(PluginInstallError) as caught:
                service.install(PACKAGE_SPEC)
        self.assertEqual(caught.exception.code, PLUGIN_INSTALL_FAILED)
        row = self.db.execute(
            "SELECT status, phase, error_code, finished_at "
            "FROM claude_plugin_operations"
        ).fetchone()
        self.assertEqual(row[0], "error", "operation must not stay 'running'")
        self.assertEqual(row[1], "error")
        self.assertEqual(row[2], PLUGIN_INSTALL_FAILED)
        self.assertIsNotNone(row[3], "operation must have finished_at set")


if __name__ == "__main__":
    unittest.main()
