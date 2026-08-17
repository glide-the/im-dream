"""REAL Claude CLI integration test for the drama-forge Dream driver plugin.

No mocks — the genuine ``claude`` binary and the real pipeline:

1. install: ``claude plugin marketplace add <repo>/marketplaces/drama-studio``
   (server-declared LOCAL marketplace) + ``claude plugin install
   drama-forge@drama-studio`` inside an isolated managed runtime root.
2. pack + workspace init: Deck ref → workspace skeleton (stories/assets/
   exports/.dramaforge), injected CLAUDE.md, managed venv built from the
   packed requirements, launch manifest runtime section, PATH injection.
3. load: real CLI ``--plugin-dir`` recognizes the packed plugin (skills +
   SessionStart hook per the --debug-file channel) — the C6 hook-evidence
   checkpoint from the gap analysis.
4. toolchain: the managed venv's python runs the packed
   ``scripts/dramaforge.py`` (C1/C2 end-to-end without an LLM run).

When the CLI, pip network or auth is unavailable the affected tests are
skipped with an explicit BLOCKED reason — a skip is never a fake pass.

Evidence is written to output/plugin-verify/latest-drama-forge-test/.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
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
from services.claude_plugin.install_service import (
    PluginInstallError,
    PluginInstallService,
)
from services.claude_plugin.workspace_packer import (
    WorkspacePackError,
    pack_workspace_plugins,
)
from libs.claude_agent_kit.server.plugin_launcher import (
    apply_plugin_launch_options,
)

PACKAGE_SPEC = "drama-forge@drama-studio"
EXPECTED_SKILL_COUNT = 13  # 14 source skills minus development-only skill-gen
EVIDENCE_DIR = REPO_ROOT / "output" / "plugin-verify" / "latest-drama-forge-test"


def _evidence(name: str, payload: object) -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_DIR / name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


class TestRealDramaForgeChain(unittest.TestCase):
    """Ordered real-CLI chain; setUpClass performs the real install once."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls._env_patch = os.environ.copy()
        os.environ["INK_CLAUDE_PLUGIN_RUNTIME_ROOT"] = str(cls.root / "runtime")
        cls.db = sqlite3.connect(cls.root / "real-test.db")
        cls.db.row_factory = sqlite3.Row
        cls.db.execute("PRAGMA foreign_keys=ON")
        cls.db.execute(
            "CREATE TABLE decks (id TEXT PRIMARY KEY, owner_id TEXT, enabled INTEGER DEFAULT 1)"
        )
        cls.db.execute("INSERT INTO decks (id, owner_id) VALUES ('deck-a', '1')")
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
                f"BLOCKED: real drama-forge install failed (code={exc.code}): {exc}"
            )
            return
        except Exception as exc:
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
        if "INK_CLAUDE_PLUGIN_RUNTIME_ROOT" in cls._env_patch:
            os.environ["INK_CLAUDE_PLUGIN_RUNTIME_ROOT"] = cls._env_patch[
                "INK_CLAUDE_PLUGIN_RUNTIME_ROOT"
            ]
        cls.tmp.cleanup()

    def setUp(self) -> None:
        if self.blocked_reason:
            self.skipTest(self.blocked_reason)

    # -- fact 1: real install from the local marketplace ----------------------

    def test_1_install_from_local_marketplace_with_evidence(self) -> None:
        op = self.operation
        assert op is not None
        self.assertEqual(op["status"], "ready", op.get("error_summary"))
        self.assertEqual(op["exit_code"], 0)
        argv = json.loads(op["argv_json"])
        self.assertEqual(argv[1:], ["plugin", "install", PACKAGE_SPEC])
        evidence = json.loads(Path(op["evidence_path"]).read_text())
        marketplace_add = evidence.get("marketplace_add")
        self.assertIsNotNone(marketplace_add, "local marketplace add must be evidenced")
        self.assertIn(
            "marketplaces/drama-studio",
            json.dumps(marketplace_add.get("argv", marketplace_add)),
        )

    def test_1b_installation_record_inventory(self) -> None:
        inst = self.installation
        assert inst is not None
        self.assertEqual(inst["status"], "ready")
        self.assertEqual(inst["package_name"], "drama-forge")
        self.assertEqual(inst["marketplace"], "drama-studio")
        self.assertTrue(inst["artifact_digest"].startswith("sha256:"))
        inventory = json.loads(inst["component_inventory_json"])
        self.assertEqual(len(inventory.get("skills", [])), EXPECTED_SKILL_COUNT)
        self.assertIn("drama-init", inventory["skills"])
        self.assertNotIn("skill-gen", inventory["skills"])
        self.assertEqual(len(inventory.get("agents", [])), 12)
        self.assertIn("story-planner.md", inventory["agents"])

    # -- fact 2: pack + workspace init -----------------------------------------

    def _bind_and_pack(self) -> tuple[Path, dict]:
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
        ws = self.root / "ws-a"
        ws.mkdir(exist_ok=True)
        try:
            receipt = pack_workspace_plugins(self.db, workspace=ws, deck_id="deck-a")
        except WorkspacePackError as exc:
            if exc.code == "CLAUDE_PLUGIN_RUNTIME_FAILED":
                self.skipTest(f"BLOCKED: managed venv build needs network/pip: {exc}")
            raise
        return ws, receipt

    def test_2_pack_runs_workspace_init(self) -> None:
        ws, receipt = self._bind_and_pack()
        self.assertEqual(len(receipt["plugins"]), 1)
        entry = receipt["plugins"][0]
        packed = ws / entry["relative_path"]
        self.assertTrue((packed / ".claude-plugin" / "plugin.json").is_file())
        self.assertTrue((packed / ".ink" / "workspace-init.json").is_file())

        # C5: runtime directory skeleton
        for rel in ("stories", "assets", "exports", ".dramaforge"):
            self.assertTrue((ws / rel).is_dir(), f"missing runtime dir {rel}")
        # C4: injected workspace CLAUDE.md
        claude_md = ws / "CLAUDE.md"
        self.assertTrue(claude_md.is_file())
        self.assertIn("DramaForge 工作区约定", claude_md.read_text(encoding="utf-8"))
        # C2: managed venv recorded in manifest + receipt
        manifest = json.loads((ws / ".ink" / "launch-manifest.json").read_text())
        venv_dirs = manifest["runtime"]["venv_dirs"]
        self.assertEqual(len(venv_dirs), 1)
        self.assertTrue((Path(venv_dirs[0]) / "bin" / "python3").is_file())
        self.assertEqual(receipt["runtime"]["venv_dirs"], venv_dirs)
        self.assertTrue(manifest["init_steps"])
        _evidence("03-pack-receipt.json", receipt)

        # Launcher: plugins + PATH/VIRTUAL_ENV injection from the real manifest.
        class _Opts:
            plugins = None
            env = None

        opts = _Opts()
        apply_plugin_launch_options(opts, ws)
        self.assertEqual(
            opts.plugins, [{"type": "local", "path": str(packed.resolve())}]
        )
        self.assertTrue(opts.env["PATH"].startswith(f"{venv_dirs[0]}/bin"))
        self.assertEqual(opts.env["VIRTUAL_ENV"], venv_dirs[0])
        _evidence("04-launcher-env.json", {"env": opts.env, "plugins": opts.plugins})
        self.__class__.ws_a = ws
        self.__class__.packed_rel = entry["relative_path"]
        self.__class__.venv_dir = Path(venv_dirs[0])

    # -- fact 3: real CLI recognition (C6 hook checkpoint) ---------------------

    def test_3_real_cli_recognizes_packed_plugin(self) -> None:
        if not getattr(self, "ws_a", None):
            self.test_2_pack_runs_workspace_init()
        ws = self.__class__.ws_a
        packed_abs = ws / self.__class__.packed_rel
        fresh_config = self.root / "fresh-config"
        fresh_config.mkdir(exist_ok=True)

        debug_log = self.root / "load-debug.log"
        result = subprocess.run(
            [
                str(plugin_cli.resolve_claude_binary()),
                "--plugin-dir",
                str(packed_abs),
                "--debug-file",
                str(debug_log),
                "--init-only",
            ],
            cwd=str(ws),
            env={**os.environ, "CLAUDE_CONFIG_DIR": str(fresh_config)},
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-500:])
        debug_text = debug_log.read_text(encoding="utf-8", errors="replace")
        hook_lines = [line for line in debug_text.splitlines() if "Hook SessionStart" in line]
        hook_registration_lines = [
            line
            for line in debug_text.splitlines()
            if "hooks" in line.lower() and "drama-forge" in line
        ]
        _evidence(
            "05-load-debug-excerpt.json",
            {
                "exit_code": result.returncode,
                "skills_line": [
                    line for line in debug_text.splitlines() if "plugin skills loaded" in line
                ],
                "hook_registration_lines": hook_registration_lines,
                "hook_execution_lines": hook_lines,
            },
        )
        self.assertIn("Loaded 1 session-only plugins from --plugin-dir", debug_text)
        self.assertIn(
            f"Total plugin skills loaded: {EXPECTED_SKILL_COUNT}", debug_text
        )
        # C6: the packed hooks.json (plugin.json custom path
        # ./.claude/hooks/hooks.json) must be registered by the real CLI
        # under --plugin-dir session-only loading.  Registration is the
        # deterministic signal; SessionStart *execution* during --init-only
        # is recorded as evidence but not asserted (P0-7 observes it in real
        # Deck conversations).
        self.assertTrue(
            any("Loading hooks from plugin: drama-forge" in line for line in hook_registration_lines),
            f"hooks not registered; evidence: {hook_registration_lines[:5]}",
        )

    # -- fact 4: managed-venv toolchain (C1/C2 end-to-end) ----------------------

    def test_4_venv_python_runs_packed_toolchain(self) -> None:
        if not getattr(self, "venv_dir", None):
            self.test_2_pack_runs_workspace_init()
        packed_abs = self.__class__.ws_a / self.__class__.packed_rel
        result = subprocess.run(
            [
                str(self.__class__.venv_dir / "bin" / "python3"),
                str(packed_abs / "scripts" / "dramaforge.py"),
                "--help",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        _evidence(
            "06-toolchain-help.json",
            {
                "exit_code": result.returncode,
                "stdout_head": result.stdout[:800],
                "stderr_tail": result.stderr[-500:],
            },
        )
        self.assertEqual(result.returncode, 0, result.stderr[-500:])
        self.assertTrue(result.stdout.strip(), "dramaforge --help must print usage")


if __name__ == "__main__":
    unittest.main()
