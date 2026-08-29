# [Input] Explicit server-owned Notion auth homes and mocked ntn command results.
# [Output] Verify ntn installation state, minimal env, device login parsing, safe poll mapping, doctor verification, and redaction.
# [Pos] auth boundary test node in backend/tests.
# [Sync] 2026-08-28: replace request-controlled home tests with server-owned file-store and no-ambient-token contracts.
# [Sync] 2026-08-28: normalize context-manager style during the agentdata audit.
# [Sync] 2026-08-30: cover installed/missing ntn prerequisite projection without exposing an executable path.

from __future__ import annotations

import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from notion import auth as notion_auth
from notion.errors import NotionAuthError


class TestNotionAuthHelpers(unittest.IsolatedAsyncioTestCase):
    def test_cli_installation_status_is_path_free_and_actionable(self):
        with unittest.mock.patch.object(
            notion_auth,
            "resolve_ntn_executable",
            return_value="/private/server/bin/ntn",
        ):
            installed = notion_auth.get_notion_cli_installation()
        self.assertEqual(installed.status, "installed")
        self.assertEqual(installed.required_version, "0.15.1")
        self.assertEqual(installed.install_command, "npm install -g ntn@0.15.1")
        self.assertNotIn("/private", repr(installed))

        with unittest.mock.patch.object(
            notion_auth,
            "resolve_ntn_executable",
            side_effect=notion_auth.NotionCLIUnavailableError("missing"),
        ):
            missing = notion_auth.get_notion_cli_installation()
        self.assertEqual(missing.status, "missing")

    def test_build_notion_env_uses_explicit_home_and_drops_ambient_credentials(self):
        with tempfile.TemporaryDirectory() as tmp_dir, unittest.mock.patch.dict(
            os.environ,
            {
                "NOTION_HOME": "/attacker/home",
                "NOTION_API_TOKEN": "secret-token-must-not-propagate",
                "HOME": "/attacker/process-home",
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            },
            clear=False,
        ):
            env = notion_auth.build_notion_env(Path(tmp_dir))

        self.assertEqual(env["NOTION_HOME"], str(Path(tmp_dir).resolve()))
        self.assertEqual(env["NOTION_KEYRING"], "0")
        self.assertNotIn("NOTION_API_TOKEN", env)
        self.assertNotIn("HOME", env)
        self.assertIn("PATH", env)

    async def test_start_login_parses_verification_url_and_code(self):
        async def fake_run(*args, **kwargs):
            self.assertEqual(args, ("login", "--no-browser"))
            self.assertTrue(Path(kwargs["notion_home"]).is_absolute())
            return 0, (
                "Open this URL in your browser to log in:\n"
                "https://www.notion.so/workers/cli-login?verificationCode=VAF-HWY\n"
                "Confirm that this verification code matches: VAF-HWY\n"
            ), ""

        with tempfile.TemporaryDirectory() as tmp_dir, unittest.mock.patch.object(
            notion_auth, "_run_ntn_command", side_effect=fake_run
        ):
            result = await notion_auth.start_login(Path(tmp_dir))

        self.assertEqual(
            result.verification_url,
            "https://www.notion.so/workers/cli-login?verificationCode=VAF-HWY",
        )
        self.assertEqual(result.verification_code, "VAF-HWY")
        self.assertNotIn("notionHome", notion_auth.normalize_login_result(result))

    async def test_poll_login_maps_pending_without_raw_cli_detail(self):
        async def fake_run(*args, **kwargs):
            del kwargs
            self.assertEqual(args, ("login", "poll"))
            return 1, "", "authorization_pending token=secret-value"

        with tempfile.TemporaryDirectory() as tmp_dir, unittest.mock.patch.object(
            notion_auth, "_run_ntn_command", side_effect=fake_run
        ):
            result = await notion_auth.poll_login(Path(tmp_dir))

        self.assertEqual(result.status, "pending")
        self.assertEqual(result.detail, "Waiting for confirmation in Notion.")
        self.assertNotIn("secret-value", result.detail)

    async def test_poll_login_maps_no_pending_to_consumed(self):
        async def fake_run(*args, **kwargs):
            del args, kwargs
            return 4, "", "No pending login session found. token=secret-value"

        with tempfile.TemporaryDirectory() as tmp_dir, unittest.mock.patch.object(
            notion_auth, "_run_ntn_command", side_effect=fake_run
        ):
            result = await notion_auth.poll_login(Path(tmp_dir))

        self.assertEqual(result.status, "consumed")
        self.assertNotIn("secret-value", result.detail)

    async def test_verify_status_uses_supported_doctor_command(self):
        async def fake_run(*args, **kwargs):
            del kwargs
            self.assertEqual(args, ("doctor",))
            return 0, "authenticated workspace", ""

        with tempfile.TemporaryDirectory() as tmp_dir, unittest.mock.patch.object(
            notion_auth, "_run_ntn_command", side_effect=fake_run
        ):
            result = await notion_auth.verify_status(Path(tmp_dir))

        self.assertEqual(result.status, "authenticated")
        self.assertEqual(result.detail, "Notion is connected.")

    async def test_login_failure_does_not_expose_cli_output(self):
        async def fake_run(*args, **kwargs):
            del args, kwargs
            return 2, "auth.json secret-token", "token=secret-token"

        with (
            tempfile.TemporaryDirectory() as tmp_dir,
            unittest.mock.patch.object(
                notion_auth, "_run_ntn_command", side_effect=fake_run
            ),
            self.assertRaises(NotionAuthError) as caught,
        ):
            await notion_auth.start_login(Path(tmp_dir))

        self.assertNotIn("secret-token", str(caught.exception))
        self.assertNotIn("auth.json", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
