# [Input] Canonical synthetic history, isolated workspaces and the installed production SDK/Runtime.
# [Output] Mapping/no-follow/corruption checks and actual same-ID cross-cwd resume receipts.
# [Pos] Provider-free contract; no normal database, real account or external model traffic.
# [Sync] 2026-11-04: prove Admin-history JSONL is read by the installed Runtime.
# [Sync] 2026-11-08: qualify parallel tool recovery, skill meta rows and saved stopped text without replay.
import asyncio
import copy
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from libs.claude_agent_kit.server.resume_transcript import ResumeTranscriptLease, history_records, validate_transcript
from libs.claude_agent_kit.server.session_files import ClaudeResumeStorageError


def history(tool=False):
    parts = [{"type": "text", "text": "Historical agreement: cobalt-seven."}]
    if tool:
        parts.insert(0, {"type": "tool-invocation", "toolCallId": "historical_tool_1", "toolName": "Bash", "input": {"command": "touch historical-tool-must-not-run"}, "state": "output-available", "output": "historical completed output"})
    return [{"id": "user-1", "role": "user", "parts": [{"type": "text", "text": "Remember cobalt-seven."}], "metadata": None, "created_at": "2026-11-01T00:00:00Z"}, {"id": "assistant-1", "role": "assistant", "parts": parts, "metadata": {"turnStatus": "completed", "turnId": "old-turn"}, "created_at": "2026-11-01T00:00:01Z"}]


def parallel_native_history(sid, cwd, *, stopped=False):
    """The locked Runtime's same-message siblings and off-parent-path results."""
    shared = history(True)
    original = history_records(shared, thread_id="thread", session_id=sid, cwd=cwd)
    records = [original[0]]
    calls, results, parts = [], [], []
    for index in range(3):
        call, result = copy.deepcopy(original[1]), copy.deepcopy(original[2])
        call.update(uuid=str(uuid4()), parentUuid=calls[-1]["uuid"] if calls else original[0]["uuid"])
        call["message"]["content"][0]["id"] = f"historical_tool_{index + 1}"
        call["timestamp"] = f"2026-11-01T00:00:0{index + 1}Z"
        result.update(uuid=str(uuid4()), parentUuid=call["uuid"], timestamp=f"2026-11-01T00:00:0{index + 4}Z")
        result["message"]["content"][0]["tool_use_id"] = call["message"]["content"][0]["id"]
        calls.append(call); results.append(result)
        parts.append({**copy.deepcopy(shared[1]["parts"][0]), "toolCallId": call["message"]["content"][0]["id"]})
    records.extend(calls + results)
    meta = {**copy.deepcopy(original[0]), "uuid": str(uuid4()), "parentUuid": results[1]["uuid"], "isMeta": True,
            "timestamp": "2026-11-01T00:00:08Z", "message": {"role": "user", "content": [{"type": "text", "text": "Base directory for this skill: fixture skill instructions"}]}}
    final = {**original[-1], "parentUuid": meta["uuid"], "timestamp": "2026-11-01T00:00:09Z"}
    records.extend([meta, final])
    shared[1]["parts"] = parts + shared[1]["parts"][1:]
    if stopped:
        user = {**copy.deepcopy(original[0]), "uuid": str(uuid4()), "parentUuid": final["uuid"], "timestamp": "2026-11-01T00:00:10Z",
                "message": {"role": "user", "content": [{"type": "text", "text": "Continue the agreement."}]}}
        thinking = {**copy.deepcopy(final), "uuid": str(uuid4()), "parentUuid": user["uuid"], "timestamp": "2026-11-01T00:00:11Z"}
        thinking["message"].update(id=str(uuid4()), content=[{"type": "thinking", "thinking": "fixture", "signature": "fixture"}])
        interrupt = {**copy.deepcopy(user), "uuid": str(uuid4()), "parentUuid": thinking["uuid"], "timestamp": "2026-11-01T00:00:12Z",
                     "message": {"role": "user", "content": "[Request interrupted by user]"}}
        records.extend([user, thinking, interrupt])
        shared.extend([{"id": "user-stop", "role": "user", "parts": [{"type": "text", "text": "Continue the agreement."}], "metadata": None, "created_at": user["timestamp"]},
                       {"id": "assistant-stop", "role": "assistant", "parts": [{"type": "text", "text": "Saved partial response."}], "metadata": {"turnStatus": "cancelled", "is_partial": True}, "created_at": interrupt["timestamp"]}])
    return records, shared


class TranscriptContract(unittest.TestCase):
    def test_parallel_results_and_meta_rows_adopt_native_bytes(self):
        from libs.claude_agent_kit.server.resume_transcript import _projection
        with tempfile.TemporaryDirectory(prefix="ink-cross-resume-parallel-") as tmp:
            root = Path(tmp).resolve(); sid = str(uuid4())
            lease = ResumeTranscriptLease(thread_id="thread", session_id=sid, cwd=str(root), config_home=str(root / "home"), lock_root=str(root))
            try:
                records, shared = parallel_native_history(sid, str(root))
                raw = ("\n".join(json.dumps(v) for v in records) + "\n").encode()
                lease._write(sid + ".jsonl", raw)
                projected = _projection(validate_transcript(raw, sid))
                self.assertEqual(len(projected), 1)
                self.assertEqual(len(projected[0][2]), 3)
                self.assertEqual(len(projected[0][3]), 3)
                lease.prepare(shared, "parallel")
                self.assertEqual(lease._read(sid + ".jsonl"), raw)
                shared[1]["parts"][0]["output"] = "different result"
                next((root / "home/projects").glob("*/" + sid + ".jsonl.ink-continuation.json")).unlink()
                with self.assertRaisesRegex(ClaudeResumeStorageError, "HISTORY_DIVERGED"):
                    lease.prepare(shared, "changed")
                self.assertEqual(lease._read(sid + ".jsonl"), raw)
            finally:
                lease.close()

    def test_saved_stopped_text_is_appended_once_with_original_archive(self):
        with tempfile.TemporaryDirectory(prefix="ink-cross-resume-stopped-") as tmp:
            root = Path(tmp).resolve(); sid = str(uuid4())
            lease = ResumeTranscriptLease(thread_id="thread", session_id=sid, cwd=str(root), config_home=str(root / "home"), lock_root=str(root))
            try:
                records, shared = parallel_native_history(sid, str(root), stopped=True)
                raw = ("\n".join(json.dumps(v) for v in records) + "\n").encode()
                lease._write(sid + ".jsonl", raw)
                lease.prepare(shared, "stopped")
                restored = lease._read(sid + ".jsonl")
                self.assertTrue(restored.startswith(raw))
                self.assertEqual(len(list((root / "home/projects").glob("*/*.archive-*"))), 1)
                self.assertEqual(next((root / "home/projects").glob("*/*.archive-*")).read_bytes(), raw)
                self.assertEqual(validate_transcript(restored, sid)[-1]["message"]["content"], [{"type": "text", "text": "Saved partial response."}])
                lease.prepare(shared, "stopped")
                self.assertEqual(lease._read(sid + ".jsonl"), restored)
            finally:
                lease.close()

    def test_mapping_and_complete_tool_pair(self):
        sid = str(uuid4())
        records = history_records(history(True), thread_id="thread", session_id=sid, cwd="/fixture")
        raw = ("\n".join(json.dumps(v) for v in records)).encode()
        self.assertEqual(len(validate_transcript(raw, sid)), 4)
        self.assertEqual(records, history_records(history(True), thread_id="thread", session_id=sid, cwd="/fixture"))
        broken = records.copy()
        broken[-1] = {**broken[-1], "parentUuid": "missing"}
        with self.assertRaises(ClaudeResumeStorageError):
            validate_transcript("\n".join(json.dumps(v) for v in broken).encode(), sid)

    def test_reject_incomplete_and_structured_tool_output(self):
        for mutate in (lambda v: v[1]["metadata"].update(turnStatus="failed"), lambda v: v[1]["parts"][0].update(output={"lossy": True})):
            value = history(True)
            mutate(value)
            with self.assertRaises(ClaudeResumeStorageError):
                history_records(value, thread_id="thread", session_id=str(uuid4()), cwd="/fixture")

    def test_atomic_reuse_archive_and_symlink(self):
        with tempfile.TemporaryDirectory(prefix="ink-cross-resume-contract-") as tmp:
            root = Path(tmp).resolve()
            sid = str(uuid4())
            kwargs = dict(thread_id="thread", session_id=sid, cwd=str(root), config_home=str(root / "home"), lock_root=str(root / "thread"))
            with_lease = ResumeTranscriptLease(**kwargs)
            try:
                with_lease.prepare(history(), "first")
                with_lease.prepare(history(), "first")
                with self.assertRaisesRegex(ClaudeResumeStorageError, "CHAT_CONTINUATION_BUSY"):
                    ResumeTranscriptLease(**kwargs)
                with_lease.prepare(history(), "second")
                self.assertEqual(len(list((root / "home" / "projects").glob("*/*.archive-*"))), 1)
            finally:
                with_lease.close()
            (root / "evil").symlink_to(root / "home", target_is_directory=True)
            with self.assertRaisesRegex(ClaudeResumeStorageError, "SYMLINK_DENIED"):
                ResumeTranscriptLease(**{**kwargs, "lock_root": str(root / "evil" / "thread")})

    def test_storage_failures_and_session_path_are_classified(self):
        with tempfile.TemporaryDirectory(prefix="ink-cross-resume-storage-") as tmp:
            root = Path(tmp).resolve()
            kwargs = dict(thread_id="thread", session_id=str(uuid4()), cwd=str(root), config_home=str(root / "home"), lock_root=str(root / "thread"))
            with self.assertRaisesRegex(ClaudeResumeStorageError, "INVALID_SESSION_ID"):
                ResumeTranscriptLease(**{**kwargs, "session_id": "../../outside"})
            with patch("libs.claude_agent_kit.server.resume_transcript._directory", side_effect=PermissionError()):
                with self.assertRaisesRegex(ClaudeResumeStorageError, "PERMISSION_DENIED"):
                    ResumeTranscriptLease(**kwargs)

    def test_native_structured_result_adopts_without_synthesizing_blocks(self):
        with tempfile.TemporaryDirectory(prefix="ink-cross-resume-native-") as tmp:
            root = Path(tmp).resolve()
            sid = str(uuid4())
            lease = ResumeTranscriptLease(thread_id="thread", session_id=sid, cwd=str(root), config_home=str(root / "home"), lock_root=str(root / "thread"))
            try:
                lease.prepare(history(True), "first")
                target = next((root / "home/projects").glob("*/*.jsonl"))
                records = [json.loads(line) for line in target.read_text().splitlines()]
                records[2]["message"]["content"][0]["content"] = [{"type": "text", "text": '{"saved":true}'}]
                native = "\n".join(json.dumps(record) for record in records) + "\n"
                target.write_text(native)
                target.with_name(target.name + ".ink-continuation.json").unlink()
                shared = history(True)
                shared[1]["parts"][0]["output"] = {"saved": True}
                lease.prepare(shared, "structured-native")
                self.assertEqual(target.read_text(), native)
                with self.assertRaisesRegex(ClaudeResumeStorageError, "HISTORY_UNSUPPORTED"):
                    history_records(shared, thread_id="thread", session_id=sid, cwd=str(root))
            finally:
                lease.close()


class PreparationFailureContract(unittest.IsolatedAsyncioTestCase):
    async def test_armed_failure_retains_unknown_outcome(self):
        from types import SimpleNamespace
        from claude_agent.service import ClaudeAgentService, ClaudeAgentRunRequest, _TurnExecution, _TurnContext
        from claude_agent.thread_pool import AgentRunState
        from claude_agent.tool_confirmation_store import ToolConfirmationStore
        from services.admin_data.agent_turn_persistence import AdminAgentTurnPersistence
        from tests.fixtures.continuation_persistence import UnitContinuationStorage
        phases = []
        class Persistence(AdminAgentTurnPersistence):
            def continuation_snapshot(self, **kwargs):
                return SimpleNamespace(thread=SimpleNamespace(claude_session_id=None), messages=[], history_digest="e" * 64)
            def continuation_claim(self, **kwargs):
                return SimpleNamespace(dispatch_turn_id=kwargs["input_dto"].dispatch_turn_id, revision=1)
            def continuation_progress(self, **kwargs):
                phases.append(kwargs["input_dto"].action)
                return SimpleNamespace(revision=2)
        state = AgentRunState(session_id="armed-thread"); state.current_turn_id = str(uuid4())
        execution = _TurnExecution(request=ClaudeAgentRunRequest(user_id="1", thread_id=state.session_id, message_id="armed-message",
            message_parts=[{"type": "text", "text": "submitted once"}], admin_turn_persistence=Persistence()), state=state, runner=None,
            run_options=SimpleNamespace(cwd=None, claude_config_home=None, claude_tmp_workspace=None),
            turn_context=_TurnContext(queue=asyncio.Queue(), confirmation_store=ToolConfirmationStore()))
        service = ClaudeAgentService(continuation_storage_factory=UnitContinuationStorage)
        async def uncertain(_execution):
            _execution.continuation_armed = True
            raise RuntimeError("fixture query outcome unknown")
        service._execute_session_inner = uncertain
        with self.assertRaisesRegex(RuntimeError, "query outcome unknown"):
            await service.execute_session(execution)
        self.assertEqual(phases, ["mark_unknown"])

    async def test_claimed_pre_query_failure_authorizes_retry_only_after_admin_ack(self):
        from types import SimpleNamespace
        from claude_agent.service import ClaudeAgentService, ClaudeAgentRunRequest, _TurnExecution, _TurnContext
        from claude_agent.thread_pool import AgentRunState
        from claude_agent.tool_confirmation_store import ToolConfirmationStore
        from services.admin_data.agent_turn_persistence import AdminAgentTurnPersistence
        from tests.fixtures.continuation_persistence import UnitContinuationStorage

        phases = []
        class Persistence(AdminAgentTurnPersistence):
            def continuation_snapshot(self, **kwargs):
                return SimpleNamespace(thread=SimpleNamespace(claude_session_id=None), messages=[], history_digest="e" * 64)
            def continuation_claim(self, **kwargs):
                phases.append("claim")
                return SimpleNamespace(dispatch_turn_id=kwargs["input_dto"].dispatch_turn_id, revision=1)
            def continuation_progress(self, **kwargs):
                phases.append(kwargs["input_dto"].action)
                return SimpleNamespace(revision=2)
        state = AgentRunState(session_id="preparation-thread")
        state.current_turn_id = str(uuid4())
        execution = _TurnExecution(
            request=ClaudeAgentRunRequest(user_id="1", thread_id=state.session_id, message_id="preparation-message", message_parts=[{"type": "text", "text": "retained draft"}], admin_turn_persistence=Persistence()),
            state=state, runner=None,
            run_options=SimpleNamespace(cwd=None, claude_config_home=None, claude_tmp_workspace=None),
            turn_context=_TurnContext(queue=asyncio.Queue(), confirmation_store=ToolConfirmationStore()),
        )
        service = ClaudeAgentService(continuation_storage_factory=UnitContinuationStorage)
        failure = RuntimeError("fixture failure before Runner")
        service._execute_session_inner = AsyncMock(side_effect=failure)
        with self.assertRaises(RuntimeError) as raised:
            await service.execute_session(execution)
        self.assertIs(raised.exception, failure)
        self.assertTrue(failure.retryable)
        self.assertEqual(phases, ["claim", "fail_before_query"])
        self.assertFalse(execution.continuation_armed)
        execution.continuation_claim = None
        execution.continuation_managed = False
        unacknowledged = RuntimeError("fixture failure with unknown Admin settlement")
        service._execute_session_inner.side_effect = unacknowledged
        with patch.object(execution.request.admin_turn_persistence, "continuation_progress", side_effect=RuntimeError("fixture lost acknowledgement")):
            with self.assertRaisesRegex(RuntimeError, "lost acknowledgement"):
                await service.execute_session(execution)
        self.assertFalse(getattr(unacknowledged, "retryable", False))


class InstalledRuntimeContract(unittest.TestCase):
    def test_parallel_meta_and_saved_stopped_text_resume_without_replay(self):
        self._resume(False, stopped_text=True)
    def test_text_resume(self):
        self._resume(False)

    def test_closed_tool_resume_without_replay(self):
        self._resume(True)

    def test_service_prepares_before_claim_and_submits_once(self):
        self._resume(False, service=True)

    def test_interrupted_native_tail_resumes_without_tool_replay(self):
        self._resume(False, interrupted=True)

    def _resume(self, tool, service=False, interrupted=False, stopped_text=False):
        from http.server import ThreadingHTTPServer
        from libs.claude_agent_kit import AgentRunOptions, AgentStreamingCallbacks
        from libs.claude_agent_kit.server.agent_runner import ClaudeAgentRunner
        from tests.fixtures.claude_agent_sandbox_fake_provider import build_handler
        requests = []
        server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(command="pwd", final_text="cross-platform fixture complete", requests_seen=requests, announce_requests=False))
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with tempfile.TemporaryDirectory(prefix="ink-cross-resume-runtime-") as tmp:
                root = Path(tmp).resolve()
                cwd = root / "web-workspace"
                cwd.mkdir()
                original = root / "mobile-workspace"
                original.mkdir()
                (original / "keep.txt").write_text("original mobile file")
                sid = str(uuid4())
                home = str(cwd / ".claude-home")
                env = {"INK_LOAD_DATABASE_URL_FROM_ENV_FILE": "0", "INK_GATEWAY_ENABLED": "0", "INK_GATEWAY_CLAUDE_AGENT_ENABLED": "0", "ANTHROPIC_API_KEY": "", "CLAUDE_CODE_OAUTH_TOKEN": "", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{server.server_port}", "ANTHROPIC_AUTH_TOKEN": "isolated-cross-resume-fixture", "CLAUDE_CONFIG_DIR": home}
                with patch.dict(os.environ, env):
                    lease = ResumeTranscriptLease(thread_id="original-thread", session_id=sid, cwd=str(cwd), config_home=home, lock_root=str(cwd))
                    try:
                        lease.prepare(history(tool or interrupted), "fixture-history")
                        if stopped_text:
                            records, shared = parallel_native_history(sid, str(cwd), stopped=True)
                            target = next((cwd / ".claude-home/projects").glob("*/*.jsonl"))
                            target.write_text("\n".join(json.dumps(v) for v in records) + "\n")
                            lease.prepare(shared, "stopped-text-history")
                        if interrupted:
                            records = history_records(history(True), thread_id="original-thread", session_id=sid, cwd=str(cwd))[:2]
                            target = next((cwd / ".claude-home/projects").glob("*/*.jsonl"))
                            target.write_text("\n".join(json.dumps(v) for v in records) + "\n")
                            stopped = history(True)
                            stopped[1]["parts"] = [stopped[1]["parts"][0]]
                            stopped[1]["parts"][0].update(state="call")
                            stopped[1]["parts"][0].pop("output")
                            stopped[1]["metadata"].update(turnStatus="cancelled", is_partial=True)
                            lease.prepare(stopped, "stopped-history")
                        async def run():
                            async with asyncio.timeout(60):
                                return await ClaudeAgentRunner().run_streaming(AgentRunOptions(thread_id=sid, resume=True, require_existing_session=True, model="fixture-model", user_message="Current message exactly once.", cwd=str(cwd), claude_tmp_workspace=str(cwd), claude_config_home=home, max_turns=3, user_sdk_env={"ANTHROPIC_BASE_URL": env["ANTHROPIC_BASE_URL"], "ANTHROPIC_AUTH_TOKEN": env["ANTHROPIC_AUTH_TOKEN"]}), AgentStreamingCallbacks(on_text_delta=lambda _: None))
                        if service:
                            from types import SimpleNamespace
                            from claude_agent.service import ClaudeAgentService, ClaudeAgentRunRequest, _TurnExecution, _TurnContext, _AGENT_RUNTIME_CONTRACT_VERSION
                            from claude_agent.thread_pool import AgentRunState
                            from claude_agent.tool_confirmation_store import ToolConfirmationStore
                            from services.admin_data.agent_turn_persistence import AdminAgentTurnPersistence
                            from services.admin_data.continuation_data import Snapshot
                            from services.admin_data.chat_models import ChatMessageDTO, ChatThreadDTO
                            events = []
                            user = {"id": "current", "role": "user", "parts": [{"type": "text", "text": "Current message exactly once."}], "metadata": None, "created_at": "2026-11-02T00:00:00Z"}
                            def message(value):
                                return ChatMessageDTO(**value, metadata_decode_error=False, history_final_text=None, history_process_available=False, history_projection_version=None)
                            bound = ChatThreadDTO(id="original-thread", user_id="1", title=None, deck_id=None, voice_id=None, claude_session_id=sid, agent_contract_version=_AGENT_RUNTIME_CONTRACT_VERSION, created_at=None, updated_at=None)
                            class Persistence(AdminAgentTurnPersistence):
                                saved = None
                                def continuation_claim(self, **kwargs):
                                    events.append("claim")
                                    self_outer.assertTrue(list((cwd / ".claude-home/projects").glob("*/*.jsonl")))
                                    return SimpleNamespace(dispatch_turn_id=kwargs["input_dto"].dispatch_turn_id, revision=1)
                                def continuation_progress(self, **kwargs):
                                    value = kwargs["input_dto"]
                                    events.append(value.action)
                                    return SimpleNamespace(dispatch_turn_id=value.dispatch_turn_id, revision=value.expected_revision + 1)
                                def continuation_snapshot(self, **kwargs):
                                    return Snapshot(thread=bound, messages=[message(v) for v in history()] + ([message(user), self.saved] if self.saved else []), history_digest=("f" if self.saved else "e") * 64)
                                def persist_user(self, **kwargs):
                                    raise AssertionError("The atomic claim owns input persistence")
                                def persist_assistant(self, **kwargs):
                                    events.append("assistant_saved")
                                    self.saved = message({"id":kwargs["message_id"], "role":"assistant", "parts":kwargs["parts"], "metadata":kwargs["metadata"], "created_at":"2026-11-02T00:00:01Z"})
                                def update_session(self, **kwargs):
                                    self_outer.assertEqual(kwargs["session_id"], sid)
                            self_outer = self
                            persistence = Persistence()
                            state = AgentRunState(session_id="original-thread")
                            state.current_turn_id = str(uuid4())
                            options = AgentRunOptions(thread_id=sid, resume=True, require_existing_session=True, model="fixture-model", user_message="Current message exactly once.", cwd=str(cwd), claude_tmp_workspace=str(cwd), claude_config_home=home, max_turns=3, user_sdk_env={"ANTHROPIC_BASE_URL": env["ANTHROPIC_BASE_URL"], "ANTHROPIC_AUTH_TOKEN": env["ANTHROPIC_AUTH_TOKEN"]})
                            execution = _TurnExecution(request=ClaudeAgentRunRequest(user_id="1",thread_id="original-thread",message_id="current",message_parts=user["parts"],admin_turn_persistence=persistence),state=state,runner=ClaudeAgentRunner(),run_options=options,turn_context=_TurnContext(queue=asyncio.Queue(),confirmation_store=ToolConfirmationStore()),resume_existing_session={"claude_session_id":sid},continuation_snapshot=Snapshot(thread=bound,messages=[message(v) for v in history()],history_digest="e"*64))
                            # Use a separate root lock: this caller releases its qualification lock first.
                            lease.close()
                            asyncio.run(ClaudeAgentService().execute_session(execution))
                            self.assertTrue(execution.user_response_committed)
                            self.assertEqual(events, ["claim", "arm_query", "assistant_saved", "complete"])
                            # An existing pre-upgrade transcript has no Ink marker.
                            # Reuse the real Runtime bytes through its UI projection.
                            lease = ResumeTranscriptLease(thread_id="original-thread", session_id=sid, cwd=str(cwd), config_home=home, lock_root=str(cwd))
                            target = next((cwd / ".claude-home/projects").glob("*/*.jsonl"))
                            target.with_name(target.name + ".ink-continuation.json").unlink()
                            latest = persistence.continuation_snapshot()
                            lease.prepare([item.model_dump() for item in latest.messages], latest.history_digest)
                            result = SimpleNamespace(success=True,error=None,session_id=sid,full_text="cross-platform fixture complete")
                        else:
                            result = asyncio.run(run())
                        self.assertTrue(result.success, str(result.error))
                        self.assertEqual(result.session_id, sid)
                        lease.checkpoint("completed-fixture")
                        self.assertEqual(result.full_text, "cross-platform fixture complete")
                        self.assertTrue(requests)
                        first = json.dumps(requests[0].get("messages"))
                        self.assertIn("cobalt-seven", first)
                        if stopped_text:
                            self.assertIn("Saved partial response.", first)
                        self.assertEqual(first.count("Current message exactly once."), 1)
                        self.assertFalse((cwd / "historical-tool-must-not-run").exists())
                        self.assertEqual((original / "keep.txt").read_text(), "original mobile file")
                        print({"same_session_id": True, "restored_history": True, "current_message_once": True, "historical_tools_replayed": False, "fake_provider_requests": len(requests)})
                    finally:
                        lease.close()
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)
