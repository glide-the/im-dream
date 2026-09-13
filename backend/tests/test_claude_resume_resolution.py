# [Input] Production session probe and SDK adapter with isolated filesystem/client fixtures.
# [Output] Verify identity/layout/access boundaries and connect-only bounded recovery.
# [Pos] Provider-free resume regression tests; never touches business data.
# [Sync] 2026-09-13: cover legacy layouts, access failures, and initialization races.

import asyncio
import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import tests._sdk_stubs  # noqa: F401
from libs.claude_agent_kit.server import session_files as storage
from libs.claude_agent_kit.server import simple_cas_client as adapter


CLAUDE_ID = "44444444-4444-4444-8444-444444444444"


class ResumeStorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="dream-resume-contract-")
        self.addCleanup(self.tmp.cleanup)
        self.cwd = Path(self.tmp.name).resolve() / "dream-thread"
        self.cwd.mkdir()
        self.home = self.cwd / ".claude-home"
        self.project = self.home / "projects" / re.sub(r"[^a-zA-Z0-9]", "-", str(self.cwd))
        self.record = self.project / f"{CLAUDE_ID}.jsonl"

    def probe(self, session_id=CLAUDE_ID, **kwargs):
        return storage.locate_resumable_session(
            session_id, cwd=str(kwargs.get("cwd", self.cwd)),
            config_home=str(kwargs.get("home", self.home)),
        )

    def write_record(self, target=None, **overrides):
        target = target or self.record
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({
            "type": "user", "uuid": "message-id", "sessionId": CLAUDE_ID,
            "cwd": str(self.cwd), "parentUuid": None,
            "message": {"role": "user", "content": "isolated fixture"},
            **overrides,
        }) + "\n")

    def test_missing_project_and_specific_session(self):
        self.assertIsNone(self.probe())
        self.project.mkdir(parents=True)
        self.assertIsNone(self.probe())

    def test_current_record_and_home_cwd_changes(self):
        self.write_record()
        self.assertEqual(self.probe(), str(self.record))
        self.assertIsNone(self.probe(home=self.cwd / "other-home"))
        other = self.cwd / "other-cwd"
        other.mkdir()
        self.assertIsNone(self.probe(cwd=other))

    def test_legacy_sha256_and_foreign_projects_do_not_resume(self):
        legacy = hashlib.sha256(str(self.cwd).encode()).hexdigest()
        self.write_record(self.home / "projects" / legacy / self.record.name)
        self.write_record(self.home / "projects" / "foreign" / self.record.name)
        self.assertIsNone(self.probe())

    def test_empty_and_sidechain_only_are_missing(self):
        self.project.mkdir(parents=True)
        self.record.write_text("")
        self.assertIsNone(self.probe())
        self.write_record(isSidechain=True)
        self.assertIsNone(self.probe())

    def test_invalid_id_and_corrupt_record_fail_closed(self):
        for value in ("../escape", "note-session", "", CLAUDE_ID + ".jsonl", " " + CLAUDE_ID + " "):
            with self.subTest(value=value), self.assertRaises(storage.ClaudeResumeStorageError):
                self.probe(value)
        self.write_record(sessionId="foreign")
        with self.assertRaisesRegex(storage.ClaudeResumeStorageError, "ID_MISMATCH"):
            self.probe()
        self.record.write_text("{broken\n")
        with self.assertRaisesRegex(storage.ClaudeResumeStorageError, "STORAGE_UNAVAILABLE"):
            self.probe()

    def test_permissions_symlink_and_non_directory_fail_closed(self):
        self.write_record()
        with patch.object(storage.os, "open", side_effect=PermissionError("private detail")):
            with self.assertRaisesRegex(storage.ClaudeResumeStorageError, "^CLAUDE_RESUME_STORAGE_UNAVAILABLE$"):
                self.probe()
        self.record.unlink()
        self.record.symlink_to(self.cwd / "absent-target")
        with self.assertRaises(storage.ClaudeResumeStorageError):
            self.probe()
        self.record.unlink()
        self.project.rmdir()
        self.project.write_text("not a directory")
        with self.assertRaises(storage.ClaudeResumeStorageError):
            self.probe()

    def test_invalid_cwd_is_not_missing_session(self):
        with self.assertRaisesRegex(storage.ClaudeResumeStorageError, "INVALID_CWD"):
            self.probe(cwd=self.cwd / "absent")

    def test_relative_or_parent_config_home_is_rejected(self):
        for home in ("relative-home", str(self.home) + "/../other"):
            with self.subTest(home=home), self.assertRaises(storage.ClaudeResumeStorageError):
                self.probe(home=home)

    def test_long_path_missing_record_is_missing(self):
        long_cwd = self.cwd / ("a" * 100) / ("b" * 100)
        long_cwd.mkdir(parents=True)
        self.assertIsNone(self.probe(cwd=long_cwd))


class ResumeConnectTests(unittest.IsolatedAsyncioTestCase):
    async def run_case(self, *, failure_stage="connect", marker=True, record=None, twice=False):
        options = SimpleNamespace(resume=CLAUDE_ID, cwd="/isolated", env={}, stderr=None)
        calls = []
        connects = []
        closed = []

        class Client:
            def __init__(self, options):
                self.options = options
            async def __aenter__(self):
                connects.append(self.options.resume)
                if failure_stage == "connect" and (len(connects) == 1 or twice):
                    if marker == "stderr":
                        self.options.stderr(f"No conversation found with session ID: {CLAUDE_ID}\n")
                        raise RuntimeError("Command failed with exit code 1")
                    raise RuntimeError(
                        f"No conversation found with session ID: {CLAUDE_ID}"
                        if marker else "generic initialization failure"
                    )
                return self
            async def __aexit__(self, *args):
                closed.append(True)
            async def query(self, prompt):
                calls.append(prompt)
                if failure_stage == "query":
                    raise RuntimeError(f"No conversation found with session ID: {CLAUDE_ID}")
            async def receive_response(self):
                if failure_stage == "receive":
                    raise RuntimeError(f"No conversation found with session ID: {CLAUDE_ID}")
                if failure_stage == "cancel":
                    raise asyncio.CancelledError()
                yield "sdk-result"

        error = None
        with (
            patch.object(adapter, "ClaudeSDKClient", Client),
            patch.object(adapter, "apply_project_sdk_runtime_options", side_effect=lambda value: value),
            patch.object(adapter, "ensure_claude_code_tmpdir"),
            patch.object(adapter, "get_options_claude_tmp_workspace", return_value="/isolated"),
            patch.object(adapter, "locate_resumable_session", return_value=record,
                         side_effect=record if isinstance(record, BaseException) else None) as probe,
        ):
            try:
                output = [item async for item in adapter.SimpleClaudeAgentSDKClient().query_stream("one prompt", options)]
                self.assertEqual(output, ["sdk-result"])
            except BaseException as exc:
                error = exc
        self.assertIsNone(options.stderr)
        return connects, calls, error, probe.call_count

    async def test_missing_connect_retries_once_before_single_query(self):
        connects, calls, error, probes = await self.run_case()
        self.assertEqual(connects, [CLAUDE_ID, None])
        self.assertEqual(calls, ["one prompt"])
        self.assertIsNone(error)
        self.assertEqual(probes, 1)

    async def test_second_missing_connect_is_terminal(self):
        connects, calls, error, probes = await self.run_case(twice=True)
        self.assertEqual(connects, [CLAUDE_ID, None])
        self.assertEqual(calls, [])
        self.assertIsInstance(error, RuntimeError)
        self.assertEqual(probes, 1)

    async def test_exact_stderr_marker_can_confirm_missing_initialization(self):
        connects, calls, error, probes = await self.run_case(marker="stderr")
        self.assertEqual(connects, [CLAUDE_ID, None])
        self.assertEqual(calls, ["one prompt"])
        self.assertIsNone(error)
        self.assertEqual(probes, 1)

    async def test_access_failure_during_race_recheck_is_not_replayed(self):
        connects, calls, error, _ = await self.run_case(record=storage.ClaudeResumeStorageError("storage unavailable"))
        self.assertEqual(connects, [CLAUDE_ID])
        self.assertEqual(calls, [])
        self.assertIsInstance(error, storage.ClaudeResumeStorageError)

    async def test_generic_and_still_present_record_do_not_retry(self):
        for kwargs in ({"marker": False}, {"record": "/present-record"}):
            connects, calls, error, _ = await self.run_case(**kwargs)
            self.assertEqual(connects, [CLAUDE_ID])
            self.assertEqual(calls, [])
            self.assertIsInstance(error, RuntimeError)

    async def test_query_receive_and_cancel_are_never_replayed(self):
        for stage in ("query", "receive", "cancel"):
            connects, calls, error, probes = await self.run_case(failure_stage=stage)
            self.assertEqual(connects, [CLAUDE_ID])
            self.assertEqual(calls, ["one prompt"])
            self.assertIsNotNone(error)
            self.assertEqual(probes, 0)
