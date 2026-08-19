# [Input] Consume libs/claude_agent_kit/server/sdk_env.py CLI path and SDK buffer policy helpers.
# [Output] Verify CLI binary resolution: CLAUDE_CODE_CLI_PATH override (existing path),
#          missing-path warning + fallthrough, shutil.which hit, bundled fallback
#          (unset), explicit cli_path preserved; verify bounded message-buffer defaults/overrides.
# [Pos] test node in backend/tests
# [Sync] 2026-07-26: initial — cli_path resolution coverage for the Docker
#                    apply-seccomp-patched npm CLI pinning (claude-sdk-env-design).
# [Sync] 2026-08-20: cover the server-owned 1–64 MiB SDK stdout message buffer policy.

"""Tests for sdk_env.apply_cli_path_to_options (2026-07-26)."""
from __future__ import annotations

import os
import sys
import tempfile
import types
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # backend/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tests._sdk_stubs  # noqa: F401
import libs.claude_agent_kit.server.sdk_env as sdk_env_module
from libs.claude_agent_kit.server.sdk_env import (
    CLAUDE_AGENT_MAX_BUFFER_SIZE_DEFAULT,
    CLAUDE_AGENT_MAX_BUFFER_SIZE_ENV_NAME,
    apply_cli_path_to_options,
    resolve_claude_agent_max_buffer_size,
)


def _make_options(cli_path=None) -> types.SimpleNamespace:
    return types.SimpleNamespace(cli_path=cli_path)


class TestApplyCliPathToOptions(unittest.TestCase):
    def _env(self, **vars: str):
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_CLI_PATH"}
        env.update(vars)
        return unittest.mock.patch.dict(os.environ, env, clear=True)

    def test_env_override_honored_when_path_exists(self):
        with tempfile.NamedTemporaryFile() as cli:
            os.chmod(cli.name, 0o700)
            options = _make_options()
            with self._env(CLAUDE_CODE_CLI_PATH=cli.name):
                result = apply_cli_path_to_options(options)
        self.assertIs(result, options)
        self.assertEqual(options.cli_path, str(Path(cli.name).resolve()))

    def test_missing_env_path_falls_through_to_which_with_warning(self):
        with tempfile.NamedTemporaryFile() as cli:
            os.chmod(cli.name, 0o700)
            options = _make_options()
            with (
                self._env(CLAUDE_CODE_CLI_PATH="/nonexistent/claude"),
                unittest.mock.patch.object(
                    sdk_env_module.shutil, "which", return_value=cli.name
                ),
                self.assertLogs(sdk_env_module.logger, level="WARNING") as logs,
            ):
                apply_cli_path_to_options(options)
            self.assertEqual(options.cli_path, str(Path(cli.name).resolve()))
        self.assertTrue(any("CLAUDE_CODE_CLI_PATH" in m for m in logs.output))

    def test_which_hit_sets_cli_path_when_env_unset(self):
        with tempfile.NamedTemporaryFile() as cli:
            os.chmod(cli.name, 0o700)
            options = _make_options()
            with (
                self._env(),
                unittest.mock.patch.object(
                    sdk_env_module.shutil, "which", return_value=cli.name
                ),
            ):
                apply_cli_path_to_options(options)
            self.assertEqual(options.cli_path, str(Path(cli.name).resolve()))

    def test_no_system_claude_leaves_cli_path_unset(self):
        """Bundled fallback: no env, no which() hit → cli_path stays None."""
        options = _make_options()
        with (
            self._env(),
            unittest.mock.patch.object(
                sdk_env_module.shutil, "which", return_value=None
            ),
        ):
            apply_cli_path_to_options(options)
        self.assertIsNone(options.cli_path)

    def test_explicit_cli_path_preserved(self):
        options = _make_options(cli_path="/explicit/claude")
        with tempfile.NamedTemporaryFile() as cli:
            with self._env(CLAUDE_CODE_CLI_PATH=cli.name):
                apply_cli_path_to_options(options)
        self.assertEqual(options.cli_path, "/explicit/claude")

    def test_explicit_cli_path_preserved_over_which(self):
        options = _make_options(cli_path="/explicit/claude")
        with (
            self._env(),
            unittest.mock.patch.object(
                sdk_env_module.shutil, "which", return_value="/usr/local/bin/claude"
            ),
        ):
            apply_cli_path_to_options(options)
        self.assertEqual(options.cli_path, "/explicit/claude")

    def test_which_checked_with_claude_name(self):
        options = _make_options()
        with (
            self._env(),
            unittest.mock.patch.object(
                sdk_env_module.shutil, "which", return_value=None
            ) as which_mock,
        ):
            apply_cli_path_to_options(options)
        which_mock.assert_called_once_with("claude", path=None)


class TestResolveClaudeAgentMaxBufferSize(unittest.TestCase):
    def test_default_covers_observed_image_read_message(self):
        value = resolve_claude_agent_max_buffer_size({})
        self.assertEqual(value, 8 * 1024 * 1024)
        self.assertGreater(value, 1_202_954)

    def test_valid_server_override_is_used(self):
        value = resolve_claude_agent_max_buffer_size(
            {CLAUDE_AGENT_MAX_BUFFER_SIZE_ENV_NAME: str(4 * 1024 * 1024)}
        )
        self.assertEqual(value, 4 * 1024 * 1024)

    def test_invalid_or_unbounded_override_falls_back_with_warning(self):
        for raw in ("invalid", "1048575", str(64 * 1024 * 1024 + 1)):
            with self.subTest(raw=raw), self.assertLogs(
                sdk_env_module.logger,
                level="WARNING",
            ):
                value = resolve_claude_agent_max_buffer_size(
                    {CLAUDE_AGENT_MAX_BUFFER_SIZE_ENV_NAME: raw}
                )
            self.assertEqual(value, CLAUDE_AGENT_MAX_BUFFER_SIZE_DEFAULT)


if __name__ == "__main__":
    unittest.main()
