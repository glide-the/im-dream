"""Unit tests for scripts/pack_drama_forge.py (design §3 packaging rules)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "pack_drama_forge.py"

spec = importlib.util.spec_from_file_location("pack_drama_forge", SCRIPT_PATH)
pack_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pack_module)


def _make_source(root: Path) -> Path:
    src = root / "src"
    (src / ".claude-plugin").mkdir(parents=True)
    (src / ".claude-plugin" / "plugin.json").write_text('{"name":"drama-forge"}')
    (src / ".claude" / "skills" / "drama-init").mkdir(parents=True)
    (src / ".claude" / "skills" / "drama-init" / "SKILL.md").write_text(
        "run `python3 scripts/dramaforge.py doctor system`\n"
        "and `bash .claude/hooks/preflight.sh`\n"
        "install: pip install -r scripts/requirements.txt\n"
    )
    (src / ".claude" / "skills" / "skill-gen").mkdir(parents=True)
    (src / ".claude" / "skills" / "skill-gen" / "SKILL.md").write_text("# dev only")
    (src / ".claude" / "skills" / "drama-init" / "evals").mkdir()
    (src / ".claude" / "skills" / "drama-init" / "evals" / "check.py").write_text("# eval")
    (src / ".claude" / "settings.json").write_text("{}")
    (src / "scripts").mkdir()
    (src / "scripts" / "requirements.txt").write_text("PyYAML\n")
    (src / "tests").mkdir()
    (src / "tests" / "test_x.py").write_text("# test")
    return src


class PackDramaForgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.src = _make_source(self.root)
        self.dest = self.root / "marketplaces" / "drama-studio"
        pack_module.pack(self.src, self.dest)
        self.plugin = self.dest / "plugins" / "drama-forge"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_whitelist_excludes_dev_artifacts(self) -> None:
        self.assertTrue((self.plugin / ".claude-plugin" / "plugin.json").is_file())
        self.assertFalse((self.plugin / ".claude" / "settings.json").exists())
        self.assertFalse((self.plugin / ".claude" / "skills" / "skill-gen").exists())
        self.assertFalse((self.plugin / ".claude" / "skills" / "drama-init" / "evals").exists())
        self.assertFalse((self.plugin / "tests").exists())

    def test_c1_rewrites_cwd_relative_invocations(self) -> None:
        text = (self.plugin / ".claude" / "skills" / "drama-init" / "SKILL.md").read_text()
        self.assertIn('python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dramaforge.py', text)
        self.assertIn('bash "${CLAUDE_PLUGIN_ROOT}/.claude/hooks/preflight.sh', text)
        self.assertIn('pip install -r "${CLAUDE_PLUGIN_ROOT}/scripts/requirements.txt', text)

    def test_init_profile_and_workspace_claude_md_injected(self) -> None:
        profile = json.loads((self.plugin / ".ink" / "workspace-init.json").read_text())
        self.assertEqual(profile["schema_version"], "workspace-init/v1")
        self.assertIn("stories", profile["runtime_dirs"])
        self.assertEqual(profile["python"]["requirements"], "scripts/requirements.txt")
        self.assertTrue((self.plugin / ".ink" / "workspace-claude.md").is_file())

    def test_marketplace_json_written(self) -> None:
        marketplace = json.loads(
            (self.dest / ".claude-plugin" / "marketplace.json").read_text()
        )
        self.assertEqual(marketplace["name"], "drama-studio")
        self.assertEqual(marketplace["plugins"][0]["source"], "./plugins/drama-forge")


if __name__ == "__main__":
    unittest.main()
