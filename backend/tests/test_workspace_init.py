"""Unit tests for workspace init profiles + managed plugin venvs.

Design: docs/design/deck/drama-forge-workspace-init-design.md §4-§6.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest import mock

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.claude_plugin.artifact_store import import_tree
from services.claude_plugin.workspace_init import (
    InitProfile,
    PythonRuntimeSpec,
    WorkspaceInitError,
    ensure_plugin_venv,
    execute_init_profile,
    load_init_profile,
)
from services.claude_plugin.workspace_packer import (
    WorkspacePackError,
    pack_workspace_plugins,
)
from libs.claude_agent_kit.server.plugin_launcher import (
    PluginLaunchError,
    apply_plugin_launch_options,
    read_workspace_runtime_venv_dirs,
)


def _write_profile_plugin(root: Path, *, requirements: str = "") -> Path:
    """Create a plugin tree carrying a workspace-init profile."""
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text(
        '{"name":"dramalike","version":"1.0.0"}'
    )
    (root / ".ink").mkdir()
    (root / ".ink" / "workspace-claude.md").write_text("# workspace rules\n")
    (root / "scripts").mkdir()
    (root / "scripts" / "requirements.txt").write_text(requirements)
    (root / ".ink" / "workspace-init.json").write_text(
        json.dumps(
            {
                "schema_version": "workspace-init/v1",
                "runtime_dirs": ["stories", "assets"],
                "workspace_files": [
                    {
                        "path": "CLAUDE.md",
                        "source": ".ink/workspace-claude.md",
                        "mode": "create-if-missing",
                    }
                ],
                "python": {"requirements": "scripts/requirements.txt"},
            }
        )
    )
    return root


class InitProfileParseTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_missing_profile_returns_none(self) -> None:
        (self.root / "plugin").mkdir()
        self.assertIsNone(load_init_profile(self.root / "plugin"))

    def test_valid_profile_parses(self) -> None:
        plugin = _write_profile_plugin(self.root / "plugin")
        profile = load_init_profile(plugin)
        self.assertIsInstance(profile, InitProfile)
        self.assertEqual(profile.runtime_dirs, ("stories", "assets"))
        self.assertEqual(profile.workspace_files[0].path, "CLAUDE.md")
        self.assertEqual(profile.python.requirements, "scripts/requirements.txt")

    def test_invalid_json_fails_closed(self) -> None:
        plugin = self.root / "plugin"
        (plugin / ".ink").mkdir(parents=True)
        (plugin / ".ink" / "workspace-init.json").write_text("{not json")
        with self.assertRaises(WorkspaceInitError) as caught:
            load_init_profile(plugin)
        self.assertEqual(caught.exception.code, "CLAUDE_PLUGIN_INIT_PROFILE_INVALID")

    def test_traversal_and_absolute_paths_rejected(self) -> None:
        for idx, bad_dirs in enumerate((["../escape"], ["/abs"], [".ink/evil"])):
            plugin = self.root / f"plugin-{idx}"
            (plugin / ".ink").mkdir(parents=True)
            (plugin / ".ink" / "workspace-init.json").write_text(
                json.dumps(
                    {"schema_version": "workspace-init/v1", "runtime_dirs": bad_dirs}
                )
            )
            with self.subTest(bad=bad_dirs):
                with self.assertRaises(WorkspaceInitError):
                    load_init_profile(plugin)

    def test_missing_workspace_file_source_rejected(self) -> None:
        plugin = self.root / "plugin"
        (plugin / ".ink").mkdir(parents=True)
        (plugin / ".ink" / "workspace-init.json").write_text(
            json.dumps(
                {
                    "schema_version": "workspace-init/v1",
                    "workspace_files": [{"path": "CLAUDE.md", "source": ".ink/nope.md"}],
                }
            )
        )
        with self.assertRaises(WorkspaceInitError) as caught:
            load_init_profile(plugin)
        self.assertIn("missing from artifact", str(caught.exception))


class ExecuteInitProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.plugin = _write_profile_plugin(self.root / "plugin")
        self.profile = load_init_profile(self.plugin)
        self.workspace = self.root / "ws"
        self.workspace.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_creates_dirs_and_injects_files(self) -> None:
        steps = execute_init_profile(self.workspace, self.plugin, self.profile)
        self.assertTrue((self.workspace / "stories").is_dir())
        self.assertTrue((self.workspace / "assets").is_dir())
        self.assertEqual(
            (self.workspace / "CLAUDE.md").read_text(), "# workspace rules\n"
        )
        results = {(s["action"], s["path"], s["result"]) for s in steps}
        self.assertIn(("mkdir", "stories", "created"), results)
        self.assertIn(("write-file", "CLAUDE.md", "created"), results)

    def test_idempotent_never_overwrites(self) -> None:
        execute_init_profile(self.workspace, self.plugin, self.profile)
        (self.workspace / "CLAUDE.md").write_text("user edits\n")
        (self.workspace / "stories" / "keep.txt").write_text("keep")
        steps = execute_init_profile(self.workspace, self.plugin, self.profile)
        self.assertEqual((self.workspace / "CLAUDE.md").read_text(), "user edits\n")
        self.assertTrue((self.workspace / "stories" / "keep.txt").is_file())
        self.assertTrue(all(s["result"] != "created" for s in steps))


class ManagedVenvTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.plugin = _write_profile_plugin(self.root / "plugin")
        self.spec = PythonRuntimeSpec(requirements="scripts/requirements.txt")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_creates_and_reuses_venv(self) -> None:
        runtime_root = self.root / "runtime"
        venv = ensure_plugin_venv(runtime_root, "sha256:" + "a" * 64, self.plugin, self.spec)
        self.assertTrue((venv / "bin" / "python3").is_file())
        receipt = json.loads(
            (venv.parent / "runtime-receipt.json").read_text()
        )
        created_at = receipt["created_at"]
        # Second call with unchanged requirements reuses the venv.
        again = ensure_plugin_venv(runtime_root, "sha256:" + "a" * 64, self.plugin, self.spec)
        self.assertEqual(again, venv)
        receipt2 = json.loads((venv.parent / "runtime-receipt.json").read_text())
        self.assertEqual(receipt2["created_at"], created_at)

    def test_pip_failure_is_fail_closed(self) -> None:
        (self.plugin / "scripts" / "requirements.txt").write_text(
            "definitely-not-a-real-package-xyz==0.0.0\n"
        )
        with self.assertRaises(WorkspaceInitError) as caught:
            ensure_plugin_venv(
                self.root / "runtime", "sha256:" + "b" * 64, self.plugin, self.spec
            )
        self.assertEqual(caught.exception.code, "CLAUDE_PLUGIN_RUNTIME_FAILED")
        # Failed venv is cleaned up so a retry can succeed later.
        slot = self.root / "runtime" / "plugin-runtimes" / ("sha256-" + "b" * 64)
        self.assertFalse((slot / "venv").exists())


class PackerInitIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._env = mock.patch.dict(
            os.environ,
            {"INK_CLAUDE_PLUGIN_RUNTIME_ROOT": str(Path(self._tmp.name) / "runtime")},
        )
        self._env.start()
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            CREATE TABLE claude_plugin_installations (
              id TEXT PRIMARY KEY, requested_package_spec TEXT NOT NULL,
              package_name TEXT NOT NULL, marketplace TEXT NOT NULL,
              resolved_version TEXT NOT NULL, source_type TEXT NOT NULL,
              artifact_digest TEXT NOT NULL, artifact_path TEXT NOT NULL,
              claude_cli_version TEXT NOT NULL,
              compatibility_json TEXT NOT NULL DEFAULT '{}',
              status TEXT NOT NULL DEFAULT 'ready', operation_id TEXT NOT NULL,
              file_count INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE deck_claude_plugin_refs (
              deck_id TEXT NOT NULL, plugin_installation_id TEXT NOT NULL,
              package_spec TEXT NOT NULL, resolved_version TEXT NOT NULL,
              artifact_digest TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
              order_index INTEGER NOT NULL DEFAULT 0, created_at TEXT,
              PRIMARY KEY (deck_id, plugin_installation_id)
            );
            """
        )
        source = _write_profile_plugin(Path(self._tmp.name) / "dramalike-src")
        self.artifact = import_tree(source, package_name="dramalike", marketplace="ds")
        self.db.execute(
            """
            INSERT INTO claude_plugin_installations (
                id, requested_package_spec, package_name, marketplace,
                resolved_version, source_type, artifact_digest, artifact_path,
                claude_cli_version, status, operation_id
            ) VALUES ('cpi-1', 'dramalike@ds', 'dramalike', 'ds', '1.0.0',
                      'marketplace', ?, ?, '2.1.220', 'ready', 'cop-1')
            """,
            (self.artifact.digest, str(self.artifact.path)),
        )
        self.db.execute(
            """
            INSERT INTO deck_claude_plugin_refs (
                deck_id, plugin_installation_id, package_spec, resolved_version,
                artifact_digest, enabled, order_index
            ) VALUES ('deck-1', 'cpi-1', 'dramalike@ds', '1.0.0', ?, 1, 0)
            """,
            (self.artifact.digest,),
        )
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self._env.stop()
        self._tmp.cleanup()

    def test_pack_runs_init_and_records_runtime(self) -> None:
        workspace = Path(self._tmp.name) / "ws"
        workspace.mkdir()
        receipt = pack_workspace_plugins(self.db, workspace=workspace, deck_id="deck-1")
        # Workspace skeleton + injected CLAUDE.md
        self.assertTrue((workspace / "stories").is_dir())
        self.assertTrue((workspace / "assets").is_dir())
        self.assertEqual((workspace / "CLAUDE.md").read_text(), "# workspace rules\n")
        # Manifest + receipt carry runtime and init audit
        manifest = json.loads(
            (workspace / ".ink" / "launch-manifest.json").read_text()
        )
        self.assertEqual(len(manifest["runtime"]["venv_dirs"]), 1)
        venv_dir = Path(manifest["runtime"]["venv_dirs"][0])
        self.assertTrue((venv_dir / "bin" / "python3").is_file())
        self.assertTrue(manifest["init_steps"])
        self.assertEqual(receipt["runtime"]["venv_dirs"], manifest["runtime"]["venv_dirs"])
        self.assertEqual(receipt["init_steps"], manifest["init_steps"])

    def test_frozen_workspace_skips_init_but_repairs_venv(self) -> None:
        workspace = Path(self._tmp.name) / "ws"
        workspace.mkdir()
        first = pack_workspace_plugins(self.db, workspace=workspace, deck_id="deck-1")
        venv_dir = Path(first["runtime"]["venv_dirs"][0])
        # User edits must survive a re-pack; init must not re-run.
        (workspace / "CLAUDE.md").write_text("user edits\n")
        (workspace / "stories").rmdir()
        import shutil

        shutil.rmtree(venv_dir.parent)  # wipe the derived runtime cache
        second = pack_workspace_plugins(self.db, workspace=workspace, deck_id="deck-1")
        self.assertTrue(second["frozen"])
        self.assertEqual((workspace / "CLAUDE.md").read_text(), "user edits\n")
        self.assertFalse((workspace / "stories").exists())  # init NOT re-run
        self.assertTrue((venv_dir / "bin" / "python3").is_file())  # venv rebuilt
        self.assertEqual(second["runtime"]["venv_dirs"], first["runtime"]["venv_dirs"])

    def test_invalid_profile_fails_pack(self) -> None:
        # Corrupt the packed copy's profile after first pack? No — corrupt at
        # source: rebuild artifact with a bad profile.
        source = Path(self._tmp.name) / "bad-src"
        (source / ".claude-plugin").mkdir(parents=True)
        (source / ".claude-plugin" / "plugin.json").write_text('{"name":"bad"}')
        (source / ".ink").mkdir()
        (source / ".ink" / "workspace-init.json").write_text(
            json.dumps(
                {"schema_version": "workspace-init/v1", "runtime_dirs": ["../escape"]}
            )
        )
        artifact = import_tree(source, package_name="bad", marketplace="ds")
        self.db.execute(
            """
            INSERT INTO claude_plugin_installations (
                id, requested_package_spec, package_name, marketplace,
                resolved_version, source_type, artifact_digest, artifact_path,
                claude_cli_version, status, operation_id
            ) VALUES ('cpi-bad', 'bad@ds', 'bad', 'ds', '1.0.0', 'marketplace',
                      ?, ?, '2.1.220', 'ready', 'cop-bad')
            """,
            (artifact.digest, str(artifact.path)),
        )
        self.db.execute(
            """
            INSERT INTO deck_claude_plugin_refs (
                deck_id, plugin_installation_id, package_spec, resolved_version,
                artifact_digest, enabled, order_index
            ) VALUES ('deck-bad', 'cpi-bad', 'bad@ds', '1.0.0', ?, 1, 0)
            """,
            (artifact.digest,),
        )
        self.db.commit()
        workspace = Path(self._tmp.name) / "ws-bad"
        workspace.mkdir()
        with self.assertRaises(WorkspacePackError) as caught:
            pack_workspace_plugins(self.db, workspace=workspace, deck_id="deck-bad")
        self.assertEqual(caught.exception.code, "CLAUDE_PLUGIN_INIT_PROFILE_INVALID")


class LauncherRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self._tmp.name) / "ws"
        (self.workspace / ".ink").mkdir(parents=True)
        self.venv = Path(self._tmp.name) / "venv"
        (self.venv / "bin").mkdir(parents=True)
        (self.venv / "bin" / "python3").write_text("#!/bin/sh\n")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write_manifest(self, runtime: dict | None) -> None:
        manifest = {
            "schema_version": "claude-launch/v1",
            "deck_id": "deck-1",
            "written_at": "2026-08-03T00:00:00+00:00",
            "plugins": [],
        }
        if runtime is not None:
            manifest["runtime"] = runtime
        (self.workspace / ".ink" / "launch-manifest.json").write_text(
            json.dumps(manifest)
        )

    def test_no_manifest_or_no_runtime_returns_empty(self) -> None:
        self.assertEqual(read_workspace_runtime_venv_dirs(self.workspace), [])
        self._write_manifest(None)
        self.assertEqual(read_workspace_runtime_venv_dirs(self.workspace), [])

    def test_missing_interpreter_fails_closed(self) -> None:
        self._write_manifest({"venv_dirs": [str(self.workspace / "gone")]})
        with self.assertRaises(PluginLaunchError) as caught:
            read_workspace_runtime_venv_dirs(self.workspace)
        self.assertEqual(caught.exception.code, "CLAUDE_PLUGIN_RUNTIME_MISSING")

    def test_relative_venv_path_rejected(self) -> None:
        self._write_manifest({"venv_dirs": ["relative/venv"]})
        with self.assertRaises(PluginLaunchError) as caught:
            read_workspace_runtime_venv_dirs(self.workspace)
        self.assertEqual(caught.exception.code, "CLAUDE_PLUGIN_MANIFEST_INVALID")

    def test_env_path_injection_preserves_existing(self) -> None:
        options = types.SimpleNamespace(
            plugins=None, env={"PATH": "/usr/bin", "KEEP": "1"}
        )
        with mock.patch(
            "libs.claude_agent_kit.server.plugin_launcher.read_workspace_launch_manifest",
            return_value=[{"package_spec": "dramalike@ds", "absolute_path": "/x"}],
        ), mock.patch(
            "libs.claude_agent_kit.server.plugin_launcher.read_workspace_runtime_venv_dirs",
            return_value=[str(self.venv)],
        ):
            apply_plugin_launch_options(options, self.workspace)
        self.assertEqual(options.plugins, [{"type": "local", "path": "/x"}])
        self.assertEqual(options.env["KEEP"], "1")
        self.assertTrue(options.env["PATH"].startswith(f"{self.venv}/bin"))
        self.assertIn("/usr/bin", options.env["PATH"])
        self.assertEqual(options.env["VIRTUAL_ENV"], str(self.venv))


if __name__ == "__main__":
    unittest.main()
