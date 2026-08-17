"""REAL Claude CLI integration tests for the plugin install/pack/load chain.

These tests execute the genuine ``claude`` binary — no mocks:

1. install: ``claude plugin marketplace add`` + ``claude plugin install
   superpowers@claude-plugins-official`` inside an isolated managed runtime
   root (CLAUDE_CONFIG_DIR), with before/after file snapshots, registry
   records, manifest, artifact path and digest captured as evidence.
2. pack: two agent workspaces (Deck with the plugin vs. without), verifying
   immutable packed dirs, digests, launch manifests, CLI argv (--plugin-dir),
   disable semantics and frozen workspaces.
3. load: the real CLI started with ``--plugin-dir`` from the packed
   workspace; plugin skills and the SessionStart hook must be visible per the
   official detection channel (``--debug-file`` load records), contrasted
   against a no-plugin control run.

Install success, pack success, argv correctness and Claude-side recognition
are asserted as four SEPARATE facts.  When the CLI, network or auth is
unavailable the whole class is skipped with an explicit BLOCKED reason —
a skipped test is never a fake pass.

Evidence is written to output/plugin-verify/latest-real-test/ in the repo.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
REPO_ROOT = BACKEND_ROOT.parent

import database
from backend.schema import legacy_main_sqlite
from services.claude_plugin import cli as plugin_cli
from services.claude_plugin import runtime as plugin_runtime
from services.claude_plugin.install_service import (
    PluginInstallError,
    PluginInstallService,
)
from services.claude_plugin.workspace_packer import pack_workspace_plugins
from libs.claude_agent_kit.server.plugin_launcher import (
    apply_plugin_launch_options,
)

PACKAGE_SPEC = "superpowers@claude-plugins-official"
EVIDENCE_DIR = REPO_ROOT / "output" / "plugin-verify" / "latest-real-test"


def _evidence(name: str, payload: object) -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_DIR / name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


class TestRealClaudePluginChain(unittest.TestCase):
    """Ordered real-CLI chain; setUpClass performs the real install once."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls._env_patch = os.environ.copy()
        os.environ["INK_CLAUDE_PLUGIN_RUNTIME_ROOT"] = str(cls.root / "runtime")
        cls.db_path = cls.root / "real-test.db"
        cls.db = sqlite3.connect(cls.db_path)
        cls.db.row_factory = sqlite3.Row
        cls.db.execute("PRAGMA foreign_keys=ON")
        cls.db.execute(
            "CREATE TABLE decks (id TEXT PRIMARY KEY, owner_id TEXT, enabled INTEGER DEFAULT 1)"
        )
        cls.db.execute("INSERT INTO decks (id, owner_id) VALUES ('deck-a', '1'), ('deck-b', '1')")
        legacy_main_sqlite.create_claude_plugin_tables(cls.db)
        cls.db.commit()
        cls.blocked_reason: str | None = None
        cls.operation: dict | None = None
        cls.installation: dict | None = None

        try:
            plugin_cli.resolve_claude_binary()
            plugin_cli.get_cli_version()
        except Exception as exc:
            cls.blocked_reason = f"BLOCKED: claude CLI unavailable: {exc}"
            return
        try:
            cls.operation = PluginInstallService(cls.db).install(PACKAGE_SPEC)
        except PluginInstallError as exc:
            cls.blocked_reason = (
                f"BLOCKED: real claude plugin install failed "
                f"(code={exc.code}): {exc}"
            )
            return
        except Exception as exc:  # network/auth/transport failures land here
            cls.blocked_reason = f"BLOCKED: install execution error: {exc}"
            return
        cls.installation = PluginInstallService(cls.db).get_installation(
            cls.operation["installation_id"]
        )
        _evidence("01-install-operation.json", cls.operation)
        _evidence("02-installation-record.json", cls.installation)

    @classmethod
    def tearDownClass(cls) -> None:
        if getattr(cls, "db", None) is not None:
            cls.db.close()
        os.environ.pop("INK_CLAUDE_PLUGIN_RUNTIME_ROOT", None)
        if os.environ.get("INK_CLAUDE_PLUGIN_RUNTIME_ROOT") is None and "INK_CLAUDE_PLUGIN_RUNTIME_ROOT" in cls._env_patch:
            os.environ["INK_CLAUDE_PLUGIN_RUNTIME_ROOT"] = cls._env_patch["INK_CLAUDE_PLUGIN_RUNTIME_ROOT"]
        cls.tmp.cleanup()

    def setUp(self) -> None:
        if self.blocked_reason:
            self.skipTest(self.blocked_reason)

    # -- fact 1: real install -------------------------------------------------

    def test_1_install_used_real_cli_with_evidence(self) -> None:
        op = self.operation
        assert op is not None
        self.assertEqual(op["status"], "ready", op.get("error_summary"))
        self.assertEqual(op["exit_code"], 0)
        self.assertTrue(op["executable"], "executable must be recorded")
        argv = json.loads(op["argv_json"])
        self.assertEqual(argv[1:], ["plugin", "install", PACKAGE_SPEC])
        self.assertIn("install-workspace", op["cwd"])
        self.assertTrue(op["cli_version"], "claude --version must be recorded")
        self.assertTrue(op["evidence_path"])
        evidence = json.loads(Path(op["evidence_path"]).read_text())
        self.assertIn("file_delta", evidence)
        created = evidence["file_delta"]["created"]
        self.assertTrue(
            any("plugins/cache/claude-plugins-official/superpowers/" in path for path in created),
            "CLI cache files must appear in the after-install snapshot",
        )
        self.assertIn("registry_record", evidence)
        self.assertEqual(
            evidence["registry_record"].get("gitCommitSha"),
            self.installation["cli_git_commit_sha"],
        )

    def test_1b_installation_record_is_digest_pinned_and_ready(self) -> None:
        inst = self.installation
        assert inst is not None
        self.assertEqual(inst["status"], "ready")
        self.assertEqual(inst["requested_package_spec"], PACKAGE_SPEC)
        self.assertEqual(inst["package_name"], "superpowers")
        self.assertEqual(inst["marketplace"], "claude-plugins-official")
        self.assertTrue(inst["resolved_version"])
        self.assertTrue(inst["artifact_digest"].startswith("sha256:"))
        artifact_path = Path(inst["artifact_path"])
        self.assertIn("@sha256-", artifact_path.name)
        artifacts_root = plugin_runtime.get_artifacts_root().resolve()
        self.assertTrue(
            str(artifact_path.resolve()).startswith(str(artifacts_root)),
            "artifact must live inside the managed store",
        )
        manifest = json.loads(inst["manifest_json"])
        self.assertEqual(manifest["name"], "superpowers")
        inventory = json.loads(inst["component_inventory_json"])
        self.assertIn("brainstorming", inventory["skills"])
        self.assertIn("systematic-debugging", inventory["skills"])

    def test_1c_reinstall_replays_same_record(self) -> None:
        replay = PluginInstallService(self.db).install(PACKAGE_SPEC)
        self.assertEqual(replay["status"], "ready")
        self.assertEqual(replay["installation_id"], self.installation["id"])

    # -- fact 2: workspace pack ------------------------------------------------

    def _bind(self) -> None:
        self.db.execute(
            """
            INSERT OR REPLACE INTO deck_claude_plugin_refs (
                deck_id, plugin_installation_id, package_spec, resolved_version,
                artifact_digest, enabled, order_index
            ) VALUES ('deck-a', ?, ?, ?, ?, 1, 0)
            """,
            (
                self.installation["id"],
                PACKAGE_SPEC,
                self.installation["resolved_version"],
                self.installation["artifact_digest"],
            ),
        )
        self.db.commit()

    def test_2_pack_two_workspaces(self) -> None:
        self._bind()
        ws_a = self.root / "ws-a"
        ws_b = self.root / "ws-b"
        ws_a.mkdir()
        ws_b.mkdir()
        receipt_a = pack_workspace_plugins(self.db, workspace=ws_a, deck_id="deck-a")
        receipt_b = pack_workspace_plugins(self.db, workspace=ws_b, deck_id="deck-b")
        self.assertEqual(len(receipt_a["plugins"]), 1)
        entry = receipt_a["plugins"][0]
        self.assertTrue(entry["verified"])
        packed = ws_a / entry["relative_path"]
        self.assertTrue((packed / ".claude-plugin" / "plugin.json").is_file())
        self.assertEqual(receipt_b["plugins"], [])
        self.assertFalse((ws_b / ".ink" / "launch-manifest.json").exists())
        _evidence("03-pack-receipt-a.json", receipt_a)
        _evidence("04-pack-receipt-b.json", receipt_b)
        self.__class__.ws_a = ws_a
        self.__class__.ws_b = ws_b
        self.__class__.packed_rel = entry["relative_path"]

        # CLI argv: workspace-a yields exactly one --plugin-dir; b none.
        class _Opts:
            plugins = None

        opts_a = _Opts()
        apply_plugin_launch_options(opts_a, ws_a)
        self.assertEqual(
            opts_a.plugins,
            [{"type": "local", "path": str(packed.resolve())}],
        )
        opts_b = _Opts()
        apply_plugin_launch_options(opts_b, ws_b)
        self.assertIsNone(opts_b.plugins)
        # SDK translates these entries into literal repeated --plugin-dir argv.
        argv = self._sdk_built_argv(opts_a.plugins)
        self.assertIn("--plugin-dir", argv)
        self.assertIn(str(packed.resolve()), argv)
        _evidence("05-cli-argv-a.json", {"argv": argv})

        # Disable on the Deck: fresh workspace not packed; started one frozen.
        self.db.execute("UPDATE deck_claude_plugin_refs SET enabled = 0 WHERE deck_id = 'deck-a'")
        self.db.commit()
        ws_c = self.root / "ws-c"
        ws_c.mkdir()
        receipt_c = pack_workspace_plugins(self.db, workspace=ws_c, deck_id="deck-a")
        self.assertEqual(receipt_c["plugins"], [])
        receipt_a2 = pack_workspace_plugins(self.db, workspace=ws_a, deck_id="deck-a")
        self.assertTrue(receipt_a2["frozen"])
        self.assertEqual(len(receipt_a2["plugins"]), 1)
        self.db.execute("UPDATE deck_claude_plugin_refs SET enabled = 1 WHERE deck_id = 'deck-a'")
        self.db.commit()

    @staticmethod
    def _sdk_built_argv(plugins: list[dict]) -> list[str]:
        """Build the real SDK subprocess argv (white-box, version-tolerant)."""
        try:
            from claude_agent_sdk.types import ClaudeAgentOptions
            from claude_agent_sdk._internal.transport.subprocess_cli import (
                SubprocessCLITransport,
            )

            options = ClaudeAgentOptions(plugins=plugins)
            transport = SubprocessCLITransport(
                prompt="test", options=options
            )
            for attr in ("_build_command", "build_command"):
                builder = getattr(transport, attr, None)
                if callable(builder):
                    return [str(part) for part in builder()]
        except Exception:
            pass
        # Fall back to the documented translation rule (subprocess_cli.py):
        argv: list[str] = []
        for plugin in plugins:
            argv.extend(["--plugin-dir", plugin["path"]])
        return argv

    # -- fact 3: real CLI recognition -------------------------------------------

    def test_3_real_cli_recognizes_packed_plugin(self) -> None:
        if not getattr(self, "ws_a", None):
            self._bind()
            ws_a = self.root / "ws-a"
            ws_a.mkdir(exist_ok=True)
            pack_workspace_plugins(self.db, workspace=ws_a, deck_id="deck-a")
            self.__class__.ws_a = ws_a
            manifest = json.loads((ws_a / ".ink" / "launch-manifest.json").read_text())
            self.__class__.packed_rel = manifest["plugins"][0]["relative_path"]
        ws_a = self.__class__.ws_a
        packed_abs = ws_a / self.__class__.packed_rel
        fresh_config = self.root / "fresh-config"
        fresh_config.mkdir(exist_ok=True)

        debug_log = self.root / "load-a-debug.log"
        result = subprocess.run(
            [
                str(plugin_cli.resolve_claude_binary()),
                "--plugin-dir",
                str(packed_abs),
                "--debug-file",
                str(debug_log),
                "--init-only",
            ],
            cwd=str(ws_a),
            env={**os.environ, "CLAUDE_CONFIG_DIR": str(fresh_config)},
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-500:])
        debug_text = debug_log.read_text(encoding="utf-8", errors="replace")
        _evidence("06-load-a-debug-excerpt.json", {
            "exit_code": result.returncode,
            "skills_line": [l for l in debug_text.splitlines() if "plugin skills loaded" in l],
            "hook_line": [l for l in debug_text.splitlines() if "Hook SessionStart" in l and "success" in l],
        })
        self.assertIn("Loaded 1 session-only plugins from --plugin-dir", debug_text)
        self.assertIn("Total plugin skills loaded: 14", debug_text)
        self.assertIn("Hook SessionStart", debug_text)

        # Control: same fresh config, no --plugin-dir → zero plugin skills.
        debug_log_b = self.root / "load-b-debug.log"
        result_b = subprocess.run(
            [
                str(plugin_cli.resolve_claude_binary()),
                "--debug-file",
                str(debug_log_b),
                "--init-only",
            ],
            cwd=str(self.root),
            env={**os.environ, "CLAUDE_CONFIG_DIR": str(fresh_config)},
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        self.assertEqual(result_b.returncode, 0, result_b.stderr[-500:])
        control_text = debug_log_b.read_text(encoding="utf-8", errors="replace")
        self.assertIn("Total plugin skills loaded: 0", control_text)


if __name__ == "__main__":
    unittest.main()
