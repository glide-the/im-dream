"""Unit tests for PluginInstallService reinstall/revive and remote digest semantics.

[Input] Production install service with explicit SQLite fixture, fake CLI registry, and canonical plugin trees.
[Output] Replay/revive/error terminal evidence plus rejection of content outside an Admin-approved digest.
[Pos] Provider-free install contract test; SQLite is a named fixture, never a runtime fallback.
[Sync] 2026-08-19: add Remote Marketplace ref transport, full-content drift rejection, and lineage fixture columns.

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
from backend.schema import legacy_main_sqlite
from services.claude_plugin import cli as plugin_cli
from services.claude_plugin import install_service
from services.claude_plugin.install_service import (
    MARKETPLACE_REMOTE_DRIFT,
    PLUGIN_INSTALL_FAILED,
    PluginInstallError,
    PluginInstallService,
)
from services.claude_plugin.digest import compute_plugin_digest
from services.claude_plugin.marketplace_service import MarketplaceInstallSource
from services.claude_plugin.package_spec import parse_package_spec

PACKAGE_SPEC = "drama-forge@drama-studio"


def _approved_remote_source() -> MarketplaceInstallSource:
    return MarketplaceInstallSource(
        entry_id="cpme_drama_forge",
        package_spec=PACKAGE_SPEC,
        package_name="drama-forge",
        marketplace_name="drama-studio",
        remote_url="https://github.com/example/drama-studio",
        requested_ref="release/v1",
        approved_commit_sha="a" * 40,
        marketplace_manifest_sha256="b" * 64,
        plugin_manifest_sha256=None,
        approved_plugin_digest="sha256:" + "0" * 64,
        compatibility={},
    )


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
        self.db.row_factory = sqlite3.Row
        legacy_main_sqlite.create_claude_plugin_tables(self.db)
        self.db.execute(
            "ALTER TABLE claude_plugin_operations ADD COLUMN marketplace_entry_id TEXT"
        )
        self.db.execute(
            "ALTER TABLE claude_plugin_installations ADD COLUMN marketplace_entry_id TEXT"
        )
        self.db.commit()
        # Stub the CLI boundary: marketplace ensure, registry lookup, run.
        self._patches = [
            mock.patch.object(
                install_service,
                "_ensure_marketplace",
                lambda spec, evidence, **_kwargs: evidence.setdefault(
                    "marketplace_revision", {}
                ),
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

    def test_remote_entry_rejects_installed_content_outside_approved_digest(self) -> None:
        approved = _approved_remote_source()

        with self.assertRaises(PluginInstallError) as caught:
            PluginInstallService(self.db).install(
                PACKAGE_SPEC,
                source_type="marketplace",
                marketplace_entry=approved,
            )

        self.assertEqual(
            caught.exception.code,
            MARKETPLACE_REMOTE_DRIFT,
            str(caught.exception),
        )
        self.assertNotEqual(
            compute_plugin_digest(self.plugin_root),
            approved.approved_plugin_digest,
        )
        row = self.db.execute(
            "SELECT status, error_code FROM claude_plugin_operations "
            "WHERE marketplace_entry_id = ?",
            (approved.entry_id,),
        ).fetchone()
        self.assertEqual(tuple(row), ("error", MARKETPLACE_REMOTE_DRIFT))


def test_remote_marketplace_registration_transports_the_approved_ref() -> None:
    approved = _approved_remote_source()
    observed: list[list[str]] = []

    def run_claude(argv: list[str], *, cwd: Path):
        observed.append(list(argv))
        return _fake_execution(argv)

    with (
        mock.patch.object(install_service, "_known_marketplaces", return_value={}),
        mock.patch.object(
            install_service,
            "resolve_local_marketplace",
            side_effect=AssertionError("remote entry must not resolve a local marketplace"),
        ),
        mock.patch.object(plugin_cli, "run_claude", side_effect=run_claude),
        mock.patch.object(
            install_service.runtime,
            "get_install_workspace",
            return_value=Path("/managed/install-workspace"),
        ),
        mock.patch.object(
            install_service,
            "_verified_remote_marketplace_checkout",
        ) as verify_checkout,
    ):
        install_service._ensure_marketplace(
            parse_package_spec(PACKAGE_SPEC),
            {},
            marketplace_entry=approved,
        )

    assert observed == [[
        "plugin",
        "marketplace",
        "add",
        "https://github.com/example/drama-studio#release/v1",
    ]]
    verify_checkout.assert_called_once()


if __name__ == "__main__":
    unittest.main()
