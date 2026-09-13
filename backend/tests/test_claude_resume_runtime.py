# [Input] Real installed SDK/qualified Runtime, production Runner, and local fake Provider.
# [Output] Process-isolated proof that fresh receipts match storage and actually resume.
# [Pos] Provider-free Runtime contract; execute separately from SDK-stub unit suites.
# [Sync] 2026-09-13: verify actual Runtime project encoding and two-turn continuity.

import asyncio
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch


class RealRuntimeResumeContract(unittest.TestCase):
    def test_fresh_receipt_storage_and_second_turn_resume(self):
        self._run_contract()

    def test_200_utf16_cwd_storage_and_resume(self):
        self._run_contract(cwd_units=200)

    def test_201_utf16_non_ascii_non_bmp_cwd_storage_and_resume(self):
        self._run_contract(cwd_units=201, prefix="项目😀")

    def test_transcript_disappears_before_connect_retries_fresh(self):
        self._run_contract(disappear=True)

    def _run_contract(self, *, cwd_units=None, prefix="", disappear=False):
        from libs.claude_agent_kit import AgentRunOptions, AgentStreamingCallbacks
        from libs.claude_agent_kit.server.agent_runner import ClaudeAgentRunner
        from libs.claude_agent_kit.server.session_files import locate_resumable_session
        from libs.claude_agent_kit.server.workspace import init_workspace
        from tests.fixtures.claude_agent_sandbox_fake_provider import build_handler

        requests = []
        server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(
            command="pwd", final_text="isolated resume contract complete",
            requests_seen=requests, announce_requests=False,
        ))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory(prefix="dream-resume-runtime-") as tmp:
                root = Path(tmp).resolve()
                if cwd_units is not None:
                    base = str(root / "workspaces" / "dream-resume-fixture")
                    padding = cwd_units - len(base.encode("utf-16-le")) // 2 - 1 - len(prefix.encode("utf-16-le")) // 2
                    self.assertGreater(padding, 0)
                    root = root / (prefix + "a" * padding)
                    root.mkdir(parents=True)
                provider = f"http://127.0.0.1:{server.server_port}"
                with patch.dict(os.environ, {
                    "AGENT_CWD": str(root / "workspaces"),
                    "INK_GATEWAY_ENABLED": "0",
                    "INK_GATEWAY_CLAUDE_AGENT_ENABLED": "0",
                    "INK_LOAD_DATABASE_URL_FROM_ENV_FILE": "0",
                    "ANTHROPIC_API_KEY": "",
                    "CLAUDE_CODE_OAUTH_TOKEN": "",
                    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
                    "ANTHROPIC_BASE_URL": provider,
                    "ANTHROPIC_AUTH_TOKEN": "isolated-resume-fixture-token",
                    "CLAUDE_CONFIG_DIR": str(root / "claude-home"),
                }):
                    workspace = init_workspace("dream-resume-fixture", sandbox_enabled=True)
                    if cwd_units is not None:
                        self.assertEqual(len(str(workspace).encode("utf-16-le")) // 2, cwd_units)
                    confirmations = []

                    async def confirm(payload):
                        self.assertEqual(payload["input"].get("command"), "pwd")
                        confirmations.append(payload)
                        return {"approved": True}

                    async def run(session_id=None):
                        async with asyncio.timeout(60):
                            return await ClaudeAgentRunner().run_streaming(
                                AgentRunOptions(
                                    thread_id=session_id,
                                    resume=session_id is not None,
                                    user_message="Read the current folder for this isolated fixture.",
                                    cwd=str(workspace), claude_tmp_workspace=str(workspace),
                                    claude_config_home=str(root / "claude-home"),
                                    max_turns=3,
                                    user_sdk_env={"ANTHROPIC_BASE_URL": provider, "ANTHROPIC_AUTH_TOKEN": "isolated-resume-fixture-token"},
                                ),
                                AgentStreamingCallbacks(
                                    on_text_delta=lambda _text: None,
                                    on_tool_confirmation_request=confirm,
                                ),
                            )

                    first = asyncio.run(run())
                    self.assertTrue(first.success)
                    self.assertTrue(first.session_id)
                    self.assertEqual(first.full_text, "isolated resume contract complete")
                    actual_projects = list((root / "claude-home" / "projects").iterdir())
                    self.assertEqual(len(actual_projects), 1)
                    located = locate_resumable_session(
                        first.session_id, cwd=str(workspace), config_home=str(root / "claude-home"),
                    )
                    self.assertEqual(located, str(actual_projects[0] / f"{first.session_id}.jsonl"))
                    other_cwd = workspace / "different-cwd"
                    other_cwd.mkdir()
                    self.assertIsNone(locate_resumable_session(
                        first.session_id, cwd=str(other_cwd), config_home=str(root / "claude-home"),
                    ))
                    if disappear:
                        # This exact record was created in this disposable test;
                        # never inject disappearance into a business workspace.
                        Path(located).unlink()
                    second = asyncio.run(run(first.session_id))
                    self.assertTrue(second.success)
                    if disappear:
                        self.assertNotEqual(second.session_id, first.session_id)
                        self.assertIsNotNone(locate_resumable_session(
                            second.session_id, cwd=str(workspace), config_home=str(root / "claude-home"),
                        ))
                    else:
                        self.assertEqual(second.session_id, first.session_id)
                    self.assertEqual(second.full_text, first.full_text)
                    # pwd is explicitly in the production read-only navigation
                    # allowlist; requiring a dialog would change policy.
                    self.assertEqual(confirmations, [])
                    tool_results = [
                        block.get("content") for request in requests
                        for message in request.get("messages", [])
                        if isinstance(message, dict)
                        for block in (message.get("content") if isinstance(message.get("content"), list) else [])
                        if isinstance(block, dict) and block.get("type") == "tool_result"
                    ]
                    self.assertTrue(any(isinstance(value, str) and str(workspace) in value for value in tool_results))
                    self.assertGreaterEqual(len(requests), 3)
                    print({"runtime_storage_receipt": {
                        "cwd_utf16_units": len(str(workspace).encode("utf-16-le")) // 2,
                        "actual_project": actual_projects[0].name,
                        "same_session_resumed": first.session_id == second.session_id,
                        "missing_race_recovered": disappear,
                        "tool_executed": True,
                    }})
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
