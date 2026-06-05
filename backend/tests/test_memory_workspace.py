# [Input] Consume init_memory_workspace, apply_memory_config, get_memory_context_block,
#         _sync_memory_templates, MEMORY_PROMPT_FILES from
#         libs/claude_agent_kit/server/memory_workspace.py.
# [Output] Validate memory workspace initialisation, template source rules,
#          procedural-only starter files, context block labelling, and the
#          no-filesystem-fallback contract for the four configurable prompts.
# [Pos] test node in backend/tests
# [Sync] 2026-06-05: initial implementation — covers design fixes:
#         (1) configurable template files sourced exclusively from partition config,
#         (2) WORKFLOW.md still sourced from .claude/memory/ filesystem,
#         (3) memory workspace labelled as "procedural" memory type.

"""Regression tests for libs/claude_agent_kit/server/memory_workspace.py."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # backend/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tests._sdk_stubs  # noqa: F401
from libs.claude_agent_kit.server.memory_workspace import (
    MEMORY_PROMPT_FILES,
    PROCEDURAL_MEMORY_FILES,
    _CONFIG_KEY_TO_FILE,
    _FILE_TO_CONFIG_KEY,
    apply_memory_config,
    get_memory_context_block,
    init_memory_workspace,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_workspace(tmp_dir: str) -> Path:
    """Create a minimal workspace directory and patch AGENT_CWD."""
    ws = Path(tmp_dir) / "test-session"
    ws.mkdir()
    os.environ["AGENT_CWD"] = tmp_dir
    return ws


# ---------------------------------------------------------------------------
# init_memory_workspace — basic structure
# ---------------------------------------------------------------------------


class TestInitMemoryWorkspaceStructure(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._ws = _make_workspace(self._tmp.name)

    def tearDown(self):
        os.environ.pop("AGENT_CWD", None)
        self._tmp.cleanup()

    def test_memory_dir_created(self):
        memory_dir = init_memory_workspace(self._ws)
        self.assertTrue(memory_dir.is_dir())
        self.assertEqual(memory_dir.name, "memory")

    def test_procedural_subdir_created(self):
        init_memory_workspace(self._ws)
        self.assertTrue((self._ws / "memory" / "procedural").is_dir())

    def test_long_term_memory_created(self):
        init_memory_workspace(self._ws)
        ltm = self._ws / "memory" / "long_term_memory.md"
        self.assertTrue(ltm.is_file())

    def test_procedural_starter_files_created(self):
        init_memory_workspace(self._ws)
        proc_dir = self._ws / "memory" / "procedural"
        for fname in PROCEDURAL_MEMORY_FILES:
            self.assertTrue((proc_dir / fname).is_file(), f"Missing {fname}")

    def test_procedural_json_files_are_valid_json(self):
        init_memory_workspace(self._ws)
        proc_dir = self._ws / "memory" / "procedural"
        for fname in PROCEDURAL_MEMORY_FILES:
            content = (proc_dir / fname).read_text(encoding="utf-8")
            try:
                json.loads(content)
            except json.JSONDecodeError:
                self.fail(f"{fname} is not valid JSON")

    def test_idempotent_on_repeat_calls(self):
        init_memory_workspace(self._ws)
        ltm = self._ws / "memory" / "long_term_memory.md"
        ltm.write_text("custom content", encoding="utf-8")
        init_memory_workspace(self._ws)
        # Existing runtime file must NOT be overwritten.
        self.assertEqual(ltm.read_text(encoding="utf-8"), "custom content")

    def test_returns_memory_path(self):
        memory_dir = init_memory_workspace(self._ws)
        self.assertEqual(memory_dir, self._ws / "memory")


# ---------------------------------------------------------------------------
# Template source rules — configurable files from partition config only
# ---------------------------------------------------------------------------


class TestTemplateSources(unittest.TestCase):
    """Verify template source contract:
    - WORKFLOW.md: always from .claude/memory/ filesystem.
    - 4 configurable files: partition config ONLY; no filesystem fallback.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._ws = _make_workspace(self._tmp.name)
        # Create a fake project .claude/memory/ with all 5 files.
        self._fake_project_root = Path(self._tmp.name) / "project"
        fake_memory = self._fake_project_root / ".claude" / "memory"
        fake_memory.mkdir(parents=True)
        for filename in MEMORY_PROMPT_FILES:
            (fake_memory / filename).write_text(
                f"FILESYSTEM:{filename}", encoding="utf-8"
            )

    def tearDown(self):
        os.environ.pop("AGENT_CWD", None)
        self._tmp.cleanup()

    def _init_with_config(self, memory_config=None):
        with unittest.mock.patch(
            "libs.claude_agent_kit.server.memory_workspace._project_root",
            return_value=self._fake_project_root,
        ):
            return init_memory_workspace(self._ws, memory_config)

    # --- WORKFLOW.md always from filesystem ---

    def test_workflow_md_from_filesystem_when_no_config(self):
        self._init_with_config(None)
        content = (self._ws / "memory" / "WORKFLOW.md").read_text(encoding="utf-8")
        self.assertEqual(content.strip(), "FILESYSTEM:WORKFLOW.md")

    def test_workflow_md_from_filesystem_even_with_config(self):
        # Partition config has no key for WORKFLOW.md — it is always filesystem.
        config = {
            "query_prompt_override": "CONFIG:MEMORY_QUERY_PROMPT.md",
        }
        self._init_with_config(config)
        content = (self._ws / "memory" / "WORKFLOW.md").read_text(encoding="utf-8")
        self.assertEqual(content.strip(), "FILESYSTEM:WORKFLOW.md")

    # --- Configurable files: partition config only; no fallback ---

    def test_configurable_files_written_from_partition_config(self):
        config = {
            "query_prompt_override": "CONFIG:query",
            "distiller_prompt_override": "CONFIG:distiller",
            "answer_prompt_override": "CONFIG:answer",
            "update_prompt_override": "CONFIG:update",
        }
        self._init_with_config(config)
        for config_key, filename in _CONFIG_KEY_TO_FILE.items():
            content = (self._ws / "memory" / filename).read_text(encoding="utf-8")
            expected = f"CONFIG:{config_key.split('_')[0]}"
            self.assertIn("CONFIG:", content, f"{filename} should come from partition config")

    def test_configurable_files_NOT_written_when_absent_from_config(self):
        """When a configurable file is missing from partition config it must NOT
        be sourced from the filesystem (no fallback)."""
        self._init_with_config({})  # empty config — no override keys present
        for config_key, filename in _CONFIG_KEY_TO_FILE.items():
            dest = self._ws / "memory" / filename
            self.assertFalse(
                dest.exists(),
                f"{filename} should NOT be written when not in partition config",
            )

    def test_configurable_files_NOT_written_when_config_is_none(self):
        """When memory_config is None, only WORKFLOW.md is written."""
        self._init_with_config(None)
        for config_key, filename in _CONFIG_KEY_TO_FILE.items():
            dest = self._ws / "memory" / filename
            self.assertFalse(
                dest.exists(),
                f"{filename} should NOT be written when memory_config is None",
            )

    def test_partial_config_writes_only_present_keys(self):
        """Only keys actually present in the config are written."""
        config = {"query_prompt_override": "CONFIG:query_only"}
        self._init_with_config(config)
        # query should be written
        self.assertTrue((self._ws / "memory" / "MEMORY_QUERY_PROMPT.md").is_file())
        # others should NOT be written
        for config_key, filename in _CONFIG_KEY_TO_FILE.items():
            if config_key == "query_prompt_override":
                continue
            dest = self._ws / "memory" / filename
            self.assertFalse(
                dest.exists(),
                f"{filename} should NOT be written when its key is absent from config",
            )

    def test_filesystem_fallback_never_used_for_configurable_files(self):
        """Even when filesystem templates exist, configurable files must not use them."""
        # All 5 filesystem templates exist (set up in setUp).
        # Config has no override keys — configurable files must remain absent.
        self._init_with_config({})
        for config_key, filename in _CONFIG_KEY_TO_FILE.items():
            dest = self._ws / "memory" / filename
            self.assertFalse(
                dest.exists(),
                f"{filename}: filesystem must NOT be used as fallback; file should be absent",
            )


# ---------------------------------------------------------------------------
# apply_memory_config
# ---------------------------------------------------------------------------


class TestApplyMemoryConfig(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._ws = _make_workspace(self._tmp.name)
        memory_dir = self._ws / "memory"
        memory_dir.mkdir()

    def tearDown(self):
        os.environ.pop("AGENT_CWD", None)
        self._tmp.cleanup()

    def test_applies_override_keys(self):
        config = {"query_prompt_override": "OVERRIDE:query"}
        apply_memory_config(self._ws, config)
        content = (self._ws / "memory" / "MEMORY_QUERY_PROMPT.md").read_text(encoding="utf-8")
        self.assertIn("OVERRIDE:query", content)

    def test_noop_when_config_is_none(self):
        apply_memory_config(self._ws, None)  # must not raise

    def test_noop_when_config_is_empty(self):
        apply_memory_config(self._ws, {})  # must not raise

    def test_workflow_md_is_never_overridden(self):
        """WORKFLOW.md must remain absent (or unchanged) after apply_memory_config."""
        config = {"query_prompt_override": "OVERRIDE:query"}
        apply_memory_config(self._ws, config)
        # WORKFLOW.md was never created — it should still not exist.
        self.assertFalse((self._ws / "memory" / "WORKFLOW.md").is_file())


# ---------------------------------------------------------------------------
# get_memory_context_block — procedural memory type label
# ---------------------------------------------------------------------------


class TestGetMemoryContextBlock(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._ws = _make_workspace(self._tmp.name)

    def tearDown(self):
        os.environ.pop("AGENT_CWD", None)
        self._tmp.cleanup()

    def test_returns_empty_string_when_memory_dir_absent(self):
        block = get_memory_context_block(self._ws)
        self.assertEqual(block, "")

    def test_contains_procedural_type_label(self):
        init_memory_workspace(self._ws)
        block = get_memory_context_block(self._ws)
        self.assertIn("procedural", block.lower())

    def test_contains_memory_context_tags(self):
        init_memory_workspace(self._ws)
        block = get_memory_context_block(self._ws)
        self.assertIn("<memory_context>", block)
        self.assertIn("</memory_context>", block)

    def test_mentions_long_term_memory_when_present(self):
        init_memory_workspace(self._ws)
        block = get_memory_context_block(self._ws)
        self.assertIn("long_term_memory.md", block)

    def test_mentions_procedural_files_when_present(self):
        init_memory_workspace(self._ws)
        block = get_memory_context_block(self._ws)
        self.assertIn("procedural", block)


# ---------------------------------------------------------------------------
# workspace.py — memory/ NOT created by init_workspace
# ---------------------------------------------------------------------------


class TestInitWorkspaceDoesNotCreateMemoryDir(unittest.TestCase):
    """Verify that init_workspace no longer auto-creates the memory/ directory.

    memory/ is now initialised by the agent service (assemble_context) or
    explicitly via POST /api/workspace/memory-init.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["AGENT_CWD"] = self._tmp.name

    def tearDown(self):
        os.environ.pop("AGENT_CWD", None)
        self._tmp.cleanup()

    def test_memory_dir_not_created_by_init_workspace(self):
        from libs.claude_agent_kit.server.workspace import init_workspace
        ws = init_workspace("no-memory-auto-init")
        self.assertFalse(
            (ws / "memory").exists(),
            "memory/ must NOT be created by init_workspace; "
            "it requires a partition config and must be initialised separately",
        )


if __name__ == "__main__":
    unittest.main()
