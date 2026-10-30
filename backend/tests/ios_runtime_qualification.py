# [Input] App-hosted original SDK/Runtime, a private endpoint and a provider-free HTTP fixture.
# [Output] Target receipts for real Runtime streaming, files, SDK MCP, permissions, resume and interrupt.
# [Pos] Explicit iOS validation harness; copied only into the XCTest bundle.
# [Sync] 2026-10-25: qualify the original Dream Runner and its SDK adapter against the same application-owned provider fixture.
# [Sync] 2026-10-25: qualify packaged Bash with the existing sandbox-disabled deployment and original tool approvals.
# [Sync] 2026-10-25: interrupt an actual running Bash after its own file marker and verify original Worker descriptor cleanup.
# [Sync] 2026-10-25: qualify Dream's exact resume probe against the original Runtime's long UTF-16 project directory.
# [Sync] 2026-10-25: inject an old container UUID only into the owned fixture and verify native exclusive relocation before original SDK resume.
# [Sync] 2026-10-25: verify a second container relocation without rewriting the fixture's original cwd records.
# [Sync] 2026-10-26: report only closed failure types/errno and owned descriptor flags during physical-device qualification.
from __future__ import annotations

from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import fcntl
import resource
import stat
from pathlib import Path
import shutil
import socket
from threading import Event, Thread
import uuid

import anyio
from claude_agent_sdk import (
    AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, PermissionResultAllow,
    PermissionResultDeny, ResultMessage, StreamEvent, TextBlock, create_sdk_mcp_server, tool,
)
from mobile_runtime.ios_claude_transport import IOSClaudeTransport, read_native_endpoint


def _event(kind, body):
    return ("event: " + kind + "\ndata: " + json.dumps({"type": kind, **body}, ensure_ascii=False) + "\n\n").encode()


def _report_target_failure(failure):
    chain = []
    while failure is not None and len(chain) < 8:
        chain.append({"type": type(failure).__name__, "errno": getattr(failure, "errno", None)})
        failure = failure.__cause__ or failure.__context__
    print("IOS_TARGET_FAILURE_TYPES " + json.dumps(chain), flush=True)


def _assert_workspace_files_closed(workspace):
    # F_GETPATH=50 is defined by the target SDK's sys/fcntl.h. Inspect only
    # descriptors for this harness-owned workspace and never read file bodies.
    leaked = []
    maximum = min(resource.getrlimit(resource.RLIMIT_NOFILE)[0], 4096)
    for descriptor in range(maximum):
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                continue
        except OSError:
            continue
        try:
            buffer = fcntl.fcntl(descriptor, 50, bytes(1024))
        except OSError:
            continue
        if buffer:
            path = Path(os.fsdecode(buffer.split(b"\0", 1)[0]))
            if path.is_relative_to(workspace):
                leaked.append({"path": path.relative_to(workspace).as_posix(), "flags": fcntl.fcntl(descriptor, fcntl.F_GETFL)})
    assert not leaked, ("Runtime workspace descriptors remain open after SDK disconnect", leaked)


def _events(number, *, text=None, tool_name=None, tool_input=None, slow=False):
    output = [_event("message_start", {"message": {"id": "msg_ios_" + str(number), "type": "message",
        "role": "assistant", "content": [], "model": "claude-ios-qualification", "stop_reason": None,
        "stop_sequence": None, "usage": {"input_tokens": 1, "output_tokens": 0}}})]
    if tool_name:
        output += [_event("content_block_start", {"index": 0, "content_block": {"type": "tool_use",
                       "id": "toolu_ios_" + str(number), "name": tool_name, "input": {}}}),
                   _event("content_block_delta", {"index": 0, "delta": {"type": "input_json_delta",
                       "partial_json": json.dumps(tool_input)}})]
    else:
        output += [_event("content_block_start", {"index": 0, "content_block": {"type": "text", "text": ""}})]
        for piece in (["stream-start"] if slow else [text[:2], text[2:]]):
            output += [_event("content_block_delta", {"index": 0, "delta": {"type": "text_delta", "text": piece}})]
    if not slow:
        output += [_event("content_block_stop", {"index": 0}),
                   _event("message_delta", {"delta": {"stop_reason": "tool_use" if tool_name else "end_turn",
                       "stop_sequence": None}, "usage": {"output_tokens": 2}}), _event("message_stop", {})]
    return b"".join(output)


def _latest_text(payload):
    for item in reversed(payload.get("messages", [])):
        if item.get("role") != "user":
            continue
        content = item.get("content", [])
        if isinstance(content, str):
            return content
        text = " ".join(block.get("text", "") for block in content if isinstance(block, dict))
        if text:
            return text
    return ""


@dataclass
class Fixture:
    workspace: Path
    requests: list = field(default_factory=list)
    completed_tools: set = field(default_factory=set)
    tool_results: list = field(default_factory=list)
    stop: Event = field(default_factory=Event)


class FixtureHTTPServer(ThreadingHTTPServer):
    daemon_threads = False

    def __init__(self, address, handler):
        super().__init__(address, handler)
        self.close_failures = []

    def shutdown_request(self, request):
        try:
            super().shutdown_request(request)
        except OSError as error:
            self.close_failures.append((request.fileno(), error.errno))


def _handler(fixture):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["content-length"])))
            if self.path.endswith("count_tokens"):
                data = b'{"input_tokens":1}'
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            fixture.requests.append(body)
            assert len(fixture.requests) <= 16, "Bounded provider fixture request count"
            text = _latest_text(body)
            case = next((name for name in ("IOS_WRITE", "IOS_READ", "IOS_BASH_STOP", "IOS_BASH", "IOS_MCP", "IOS_DENY", "IOS_RESUME", "IOS_SLOW", "IOS_RUNNER", "IOS_OWNED_MCP") if name in text), "unknown")
            fixture.tool_results = [block for message in body.get("messages", [])
                for block in (message.get("content", []) if isinstance(message.get("content"), list) else [])
                if isinstance(block, dict) and block.get("type") == "tool_result"]
            # A case marker occurs in its own user turn; track dispatched fixture tools.
            if case in {"IOS_WRITE", "IOS_READ", "IOS_BASH", "IOS_BASH_STOP", "IOS_MCP", "IOS_DENY", "IOS_OWNED_MCP"} and case not in fixture.completed_tools:
                fixture.completed_tools.add(case)
                name = "mcp__ios_qualification__echo" if case == "IOS_MCP" else "Write"
                value = ({"text": "ios-mcp-result"} if case == "IOS_MCP" else {
                    "file_path": str(fixture.workspace / ("denied.txt" if case == "IOS_DENY" else "written.txt")),
                    "content": "iOS Runtime 实际写入\n",
                })
                if case == "IOS_OWNED_MCP":
                    name, value = "mcp__user__get_sessions_range", {"start_date": "2026-01-01", "end_date": "2026-01-02"}
                if case == "IOS_READ":
                    name, value = "Read", {"file_path": "written.txt"}
                if case == "IOS_BASH":
                    name, value = "Bash", {"command": "printf guest-shared > command-written.txt; cat command-written.txt; printf ios-platform-command", "description": "Verify packaged command execution and shared workspace files"}
                if case == "IOS_BASH_STOP":
                    name, value = "Bash", {"command": "printf running > command-running.txt; sleep 30; printf unexpected > command-after-stop.txt", "description": "Verify cancellation of an actual running packaged command"}
                data = _events(len(fixture.requests), tool_name=name, tool_input=value)
            else:
                data = _events(len(fixture.requests), text=case + "完成✅", slow=case == "IOS_SLOW")
            self.send_response(200)
            self.send_header("content-type", "text/event-stream")
            self.send_header("connection", "close")
            if case != "IOS_SLOW":
                self.send_header("content-length", str(len(data)))
            self.end_headers()
            with suppress_disconnect():
                self.wfile.write(data)
                self.wfile.flush()
                if case == "IOS_SLOW":
                    fixture.stop.wait(10)
            self.close_connection = True
    return Handler


class suppress_disconnect:
    def __enter__(self):
        return self

    def __exit__(self, kind, value, traceback):
        return kind is not None and issubclass(kind, (BrokenPipeError, ConnectionResetError))


def run(endpoint_path):
    endpoint = read_native_endpoint(endpoint_path)
    assert endpoint["pid"] == os.getpid()
    workspace = Path(endpoint["workspaceRoot"]) / ("protocol-qualification-" + uuid.uuid4().hex + "-项目😀-" + "a" * 80)
    workspace.mkdir(mode=0o700)
    home = workspace / ".home"
    home.mkdir(mode=0o700)
    temporary = workspace / ".claude-tmp"
    temporary.mkdir(mode=0o700)
    print("IOS_PROTOCOL_TEMP_METADATA " + json.dumps({
        "parentTempInsideApplication": os.environ.get("TMPDIR", "").startswith(str(Path.home()) + "/"),
        "threadTempMode": temporary.stat().st_mode & 0o777,
    }), flush=True)
    fixture = Fixture(workspace)
    guard_read, guard_write = socket.socketpair()
    server = FixtureHTTPServer(("127.0.0.1", 0), _handler(fixture))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    permissions = []
    mcp_calls = []

    @tool("echo", "Return the provided text.", {"text": str})
    async def echo(arguments):
        mcp_calls.append(arguments["text"])
        return {"content": [{"type": "text", "text": arguments["text"]}]}

    async def permission(name, value, context):
        permissions.append((name, value))
        if str(value.get("file_path", "")).endswith("denied.txt"):
            return PermissionResultDeny(message="Qualification denied this write")
        return PermissionResultAllow(updated_input=value)

    def options(resume=None):
        from libs.claude_agent_kit.server.workspace import resolve_sandbox_enabled
        enabled = resolve_sandbox_enabled()
        assert enabled is False, "Qualification requires the configured sandbox-disabled deployment"
        return ClaudeAgentOptions(cwd=str(workspace), model="claude-ios-qualification", max_turns=3,
            include_partial_messages=True, resume=resume, can_use_tool=permission,
            settings=json.dumps({"sandbox": {"enabled": enabled, "failIfUnavailable": enabled,
                "autoAllowBashIfSandboxed": enabled, "allowUnsandboxedCommands": not enabled,
                "filesystem": {"allowWrite": [str(workspace), str(temporary)]}}}),
            mcp_servers={"ios_qualification": create_sdk_mcp_server(name="ios_qualification", tools=[echo])},
            env={"HOME": str(home), "CLAUDE_CONFIG_DIR": str(home / ".claude"), "CLAUDE_CODE_TMPDIR": str(temporary),
                 "ANTHROPIC_BASE_URL": "http://127.0.0.1:" + str(server.server_port),
                 "ANTHROPIC_API_KEY": "ios-provider-free-fixture", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"},
            stderr=lambda line: print("IOS_PROTOCOL_STDERR " + line, flush=True))

    async def collect(client, prompt, *, interrupt=False):
        await client.query(prompt)
        messages = []
        interrupted = False
        async def interrupt_command():
            nonlocal interrupted
            while not (workspace / "command-running.txt").exists():
                await anyio.sleep(0.02)
            await client.interrupt()
            interrupted = True
        with anyio.fail_after(25):
            async with anyio.create_task_group() as group:
                if interrupt == "command":
                    group.start_soon(interrupt_command)
                async for message in client.receive_response():
                    messages.append(message)
                    if interrupt is True and isinstance(message, StreamEvent) and message.event.get("type") == "content_block_delta" and not interrupted:
                        await client.interrupt()
                        interrupted = True
                group.cancel_scope.cancel()
        assert messages and isinstance(messages[-1], ResultMessage), "Runtime terminal result required"
        assert any(isinstance(item, StreamEvent) for item in messages), "Original streaming events required"
        if interrupt:
            assert interrupted, "Interrupt must follow actual stream output"
        else:
            assert not messages[-1].is_error, messages[-1]
            rendered = "".join(block.text for item in messages if isinstance(item, AssistantMessage)
                for block in item.content if isinstance(block, TextBlock))
            assert prompt + "完成✅" in rendered, rendered
        return messages[-1].session_id

    async def qualify():
        config = options()
        async with ClaudeSDKClient(options=config, transport=IOSClaudeTransport(endpoint_path=endpoint_path, options=config)) as client:
            session = await collect(client, "IOS_WRITE")
            assert (workspace / "written.txt").exists(), json.dumps({"fixtureToolResults": fixture.tool_results, "permissionCalls": permissions}, ensure_ascii=False)
            assert (workspace / "written.txt").read_text() == "iOS Runtime 实际写入\n"
            await collect(client, "IOS_READ")
            assert any("iOS Runtime 实际写入" in json.dumps(item, ensure_ascii=False) for item in fixture.tool_results), fixture.tool_results
            await collect(client, "IOS_BASH")
            assert not any(item.get("is_error") for item in fixture.tool_results), fixture.tool_results
            assert any("ios-platform-command" in json.dumps(item) for item in fixture.tool_results), fixture.tool_results
            assert (workspace / "command-written.txt").read_text() == "guest-shared"
            await collect(client, "IOS_MCP")
            assert mcp_calls == ["ios-mcp-result"], mcp_calls
            await collect(client, "IOS_DENY")
            assert not (workspace / "denied.txt").exists()
            assert any(str(value.get("file_path", "")).endswith("denied.txt") for _, value in permissions)
        guard_write.sendall(b"worker-closed")
        assert guard_read.recv(64) == b"worker-closed", "A Runtime worker closed a Python-owned socket"
        from libs.claude_agent_kit.server.session_files import locate_resumable_session
        assert len(str(workspace).encode("utf-16-le")) // 2 > 200
        from libs.claude_agent_kit.server.session_files import _runtime_project_name
        from mobile_runtime.ios_session_storage import _rename_no_replace
        parts = list(workspace.parts)
        marker = next(index for index in range(len(parts) - 3)
                      if tuple(parts[index:index + 3]) == ("Containers", "Data", "Application"))
        parts[marker + 3] = str(uuid.uuid4())
        previous_cwd = str(Path(*parts))
        projects = home / ".claude/projects"
        current_project = projects / _runtime_project_name(str(workspace))
        previous_project = projects / _runtime_project_name(previous_cwd)
        # Fault injection is confined to this fixture's own transcript.
        record = current_project / (session + ".jsonl")
        records = [json.loads(line) for line in record.read_text().splitlines() if line.strip()]
        for item in records:
            if item.get("cwd") == str(workspace):
                item["cwd"] = previous_cwd
        record.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records))
        expected_transcript = record.read_bytes()
        current_project.rename(previous_project)
        located = locate_resumable_session(session, cwd=str(workspace), config_home=str(home / ".claude"))
        assert located is not None, "Dream must locate the original Node Runtime transcript before resume"
        assert Path(located).read_bytes() == expected_transcript and not previous_project.exists()
        transcript_inode = Path(located).stat().st_ino
        parts[marker + 3] = str(uuid.uuid4())
        intermediate_project = projects / _runtime_project_name(str(Path(*parts)))
        current_project.rename(intermediate_project)
        located = locate_resumable_session(session, cwd=str(workspace), config_home=str(home / ".claude"))
        assert located is not None, "Dream must locate a repeatedly relocated original Session"
        assert Path(located).read_bytes() == expected_transcript
        assert Path(located).stat().st_ino == transcript_inode and not intermediate_project.exists()
        exclusive_source = projects / "exclusive-rename-fixture"
        exclusive_source.mkdir()
        parent = os.open(projects, os.O_RDONLY | os.O_DIRECTORY)
        try:
            try:
                _rename_no_replace(parent, exclusive_source.name, current_project.name)
            except FileExistsError:
                pass
            else:
                raise AssertionError("iOS native rename must refuse an existing project")
        finally:
            os.close(parent)
            exclusive_source.rmdir()
        config = options(resume=session)
        async with ClaudeSDKClient(options=config, transport=IOSClaudeTransport(endpoint_path=endpoint_path, options=config)) as client:
            restored = await collect(client, "IOS_RESUME")
            assert restored == session
            assert "IOS_WRITE" in json.dumps(fixture.requests[-1]["messages"]), "Persisted context must survive a new Runtime worker"
            await collect(client, "IOS_BASH_STOP", interrupt="command")
            assert (workspace / "command-running.txt").read_text() == "running"
            assert not (workspace / "command-after-stop.txt").exists()
            await collect(client, "IOS_SLOW", interrupt=True)
        guard_write.sendall(b"resumed-worker-closed")
        assert guard_read.recv(64) == b"resumed-worker-closed"
        _assert_workspace_files_closed(workspace)
        print("IOS_RUNTIME_PROTOCOL_PROOF " + json.dumps({"sameApplicationProcess": endpoint["pid"] == os.getpid(),
            "stream": True, "fileWrite": True, "relativeFileRead": True, "packagedBash": True, "sharedCommandFiles": True,
            "sandboxEnabled": False, "sandboxFailIfUnavailable": False, "allowUnsandboxedCommands": True,
            "sdkMcp": True, "permissionDeny": True,
            "dreamResumeProbe": True, "containerRelocation": True, "repeatedContainerRelocation": True,
            "transcriptBytesPreserved": True,
            "exclusiveRename": True, "resume": True, "interrupt": True, "runningBashInterrupt": True,
            "providerRequests": len(fixture.requests)}), flush=True)

    qualified = False
    try:
        anyio.run(qualify)
        qualified = True
    except BaseException as failure:
        _report_target_failure(failure)
        raise
    finally:
        fixture.stop.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        guard_read.close()
        guard_write.close()
        if qualified:
            shutil.rmtree(workspace)
        else:
            print("IOS_PROTOCOL_FAILURE_FILES " + json.dumps({
                "commandFileExists": (workspace / "command-written.txt").is_file(),
                "snapshotFiles": len(list((home / ".claude/shell-snapshots").glob("*.sh"))),
                "taskOutputs": [item.stat().st_size for item in temporary.rglob("*.output")],
                "retainedOwnedFixture": workspace.name,
            }), flush=True)
        assert not server.close_failures, ("Provider fixture sockets were closed by another owner", server.close_failures)


def run_runner(endpoint_path):
    """Keep only provider selection and disposable resources in this test harness."""
    from mobile_runtime.ios_claude_transport import create_agent_runner
    from libs.claude_agent_kit.types import AgentRunOptions, AgentStreamingCallbacks
    from services.admin_data.session_projection_broker import SessionProjectionBroker, SessionProjectionBrokerSettings
    from services.admin_data.session_models import SessionListResultDTO

    endpoint = read_native_endpoint(endpoint_path)
    workspace = Path(endpoint["workspaceRoot"]) / ("runner-qualification-" + uuid.uuid4().hex)
    workspace.mkdir(mode=0o700)
    fixture = Fixture(workspace)
    server = FixtureHTTPServer(("127.0.0.1", 0), _handler(fixture))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    environment = {"INK_GATEWAY_ENABLED": "1", "INK_GATEWAY_BASE_URL": "http://127.0.0.1:" + str(server.server_port),
                   "INK_GATEWAY_SERVICE_KEY": "gw_" + "ios-provider-free-fixture-0000", "AGENT_CWD": endpoint["workspaceRoot"]}
    previous = {key: os.environ.get(key) for key in environment}
    os.environ.update(environment)
    text, errors = [], []
    broker_calls = []

    class SessionProvider:
        def list_sessions(self, input_dto, request_id):
            broker_calls.append((input_dto, request_id))
            return SessionListResultDTO(sessions=[])

    broker = SessionProjectionBroker(SessionProvider(), settings=SessionProjectionBrokerSettings(timeout_seconds=5, max_bytes=1_048_576))
    broker.start()

    async def qualify():
        runner = create_agent_runner(endpoint_path)
        with anyio.fail_after(25):
            result = await runner.run_streaming(AgentRunOptions(thread_id=None, user_message="IOS_RUNNER",
                cwd=str(workspace), claude_tmp_workspace=str(workspace), max_turns=2,
                tool_choice="none", allowed_tools=[], gateway_access_token="idg_" + "a" * 43,
                model="claude-ios-qualification"),
                AgentStreamingCallbacks(on_text_delta=text.append, on_error=errors.append))
        assert result.success and result.protocol_completed, (str(result.error), errors)
        assert result.session_id and result.sdk_terminal_received
        assert "IOS_RUNNER完成✅" in result.full_text, result.full_text
        assert "IOS_RUNNER完成✅" in "".join(text)
        assert len(fixture.requests) == 1
        with anyio.fail_after(25):
            mcp_result = await runner.run_streaming(AgentRunOptions(thread_id=None, user_message="IOS_OWNED_MCP",
                cwd=str(workspace), claude_tmp_workspace=str(workspace), max_turns=3,
                tool_choice="auto", allowed_tools=["mcp__user__get_sessions_range"], mcp_env=broker.child_env(),
                gateway_access_token="idg_" + "a" * 43, model="claude-ios-qualification"),
                AgentStreamingCallbacks(on_text_delta=text.append, on_error=errors.append))
        assert mcp_result.success and mcp_result.protocol_completed, (str(mcp_result.error), errors)
        assert "IOS_OWNED_MCP完成✅" in mcp_result.full_text
        assert len(broker_calls) == 1, (broker_calls, fixture.tool_results)
        assert any('"ok": true' in json.dumps(item, ensure_ascii=False).replace('\\"', '"') for item in fixture.tool_results), fixture.tool_results
        # Original Workspace Mode-off options keep cwd absent and bind only the
        # existing thread runtime tmp root. The original Runner chooses the
        # backend's process default; iOS must not manufacture a user workspace.
        with anyio.fail_after(25):
            no_workspace = await runner.run_streaming(AgentRunOptions(thread_id=None, user_message="IOS_RUNNER",
                cwd=None, claude_tmp_workspace=str(workspace), claude_config_home=str(workspace / '.fixture-config'),
                max_turns=2, tool_choice="none", allowed_tools=[], gateway_access_token="idg_" + "a" * 43,
                model="claude-ios-qualification"), AgentStreamingCallbacks(on_text_delta=text.append, on_error=errors.append))
        assert no_workspace.success and no_workspace.protocol_completed, (str(no_workspace.error), errors)
        assert not (workspace / '.claude').exists() and not (workspace / '.workspace').exists()
        _assert_workspace_files_closed(workspace)
        print("IOS_DREAM_RUNNER_PROOF " + json.dumps({"sameApplicationProcess": endpoint["pid"] == os.getpid(),
            "runner": type(runner).__name__, "protocolCompleted": result.protocol_completed,
            "stream": True, "ownedMcp": True, "workspaceOff": True, "providerRequests": len(fixture.requests)}), flush=True)
    try:
        anyio.run(qualify)
    except BaseException as failure:
        _report_target_failure(failure)
        raise
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        fixture.stop.set()
        broker.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        shutil.rmtree(workspace)
        assert not server.close_failures, ("Provider fixture sockets were closed by another owner", server.close_failures)
