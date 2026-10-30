# [Input] Native-owned in-process endpoint and original ClaudeAgentOptions.
# [Output] Original SDK command encoding and JSONL/control parsing over a private local socket.
# [Pos] iOS execution transport; the SDK and original Runtime retain Agent behavior.
# [Sync] 2026-10-25: retain the application container HOME when the original Runner supplies only its thread config home.
# [Sync] 2026-10-25: qualify original Next through same-PID worker listening ownership and an actual page response.
# [Sync] 2026-10-26: await Worker exit after bounded EOF grace before releasing the private socket and owned MCP scope.
from __future__ import annotations

import base64
import codecs
from contextlib import suppress
from contextlib import ExitStack
import json
import os
from pathlib import Path
import stat
import sys
import tomllib

import anyio
from anyio.streams.buffered import BufferedByteReceiveStream
from claude_agent_sdk._errors import CLIConnectionError
from claude_agent_sdk._internal.transport.subprocess_cli import SubprocessCLITransport, _LineFramer
from claude_agent_sdk._version import __version__
from claude_agent_sdk.types import _configure_can_use_tool


def read_native_endpoint(path: str | Path) -> dict:
    source = Path(path)
    info = source.lstat()
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600:
        raise CLIConnectionError("IOS_RUNTIME_ENDPOINT_INVALID")
    endpoint = json.loads(source.read_text())
    if (endpoint.get("version") != 1 or endpoint.get("pid") != os.getpid()
            or type(endpoint.get("port")) is not int or not 0 < endpoint["port"] < 65536
            or not isinstance(endpoint.get("token"), str) or len(endpoint["token"]) != 64):
        raise CLIConnectionError("IOS_RUNTIME_ENDPOINT_INVALID")
    return endpoint


async def query_native_status(path: str | Path) -> dict:
    endpoint = read_native_endpoint(path)
    async with await anyio.connect_tcp("127.0.0.1", endpoint["port"]) as connection:
        await connection.send((json.dumps({"version": 1, "type": "status", "token": endpoint["token"]}) + "\n").encode())
        response = json.loads(await BufferedByteReceiveStream(connection).receive_until(b"\n", 4096))
    if response.get("type") != "status" or response.get("pid") != os.getpid():
        raise CLIConnectionError("IOS_RUNTIME_PROCESS_MISMATCH")
    return {key: value for key, value in response.items() if key not in {"type", "pid"}}


async def start_native_web(path: str | Path, backend_origin: str) -> str:
    endpoint = read_native_endpoint(path)
    async with await anyio.connect_tcp("127.0.0.1", endpoint["port"]) as connection:
        await connection.send((json.dumps({"version": 1, "type": "start_web", "token": endpoint["token"],
                                          "backendOrigin": backend_origin}) + "\n").encode())
        response = json.loads(await BufferedByteReceiveStream(connection).receive_until(b"\n", 4096))
    if response.get("type") != "web_started" or response.get("pid") != os.getpid():
        raise CLIConnectionError(response.get("code", "IOS_NEXT_PROCESS_MISMATCH"))
    import httpx
    async with httpx.AsyncClient(trust_env=False, follow_redirects=False, timeout=5) as client:
        with anyio.fail_after(25):
            while True:
                status = (await query_native_status(path)).get("web", {})
                if status.get("state") == "failed":
                    raise CLIConnectionError(status.get("code", "IOS_NEXT_WORKER_FAILED"))
                if (status.get("state") != "listening" or status.get("origin") != response["origin"]
                        or status.get("backendOrigin") != backend_origin):
                    await anyio.sleep(0.1)
                    continue
                try:
                    result = await client.get(response["origin"] + "/")
                    if result.status_code == 200:
                        return response["origin"]
                except httpx.TransportError:
                    pass
                await anyio.sleep(0.1)


def create_agent_runner(endpoint_path: str | Path):
    """Bind the existing Dream Runner to the qualified application-process Runtime."""
    from libs.claude_agent_kit.server.agent_runner import ClaudeAgentRunner
    from libs.claude_agent_kit.server.simple_cas_client import SimpleClaudeAgentSDKClient

    endpoint = read_native_endpoint(endpoint_path)
    client = SimpleClaudeAgentSDKClient(
        transport_factory=lambda options: IOSClaudeTransport(endpoint_path=endpoint_path, options=options),
    )
    return ClaudeAgentRunner(client, cli_path=endpoint["runtimeEntry"])


class _ThreadSession:
    def __init__(self):
        self.returncode = None
        self.finished = anyio.Event()

    async def wait(self):
        await self.finished.wait()
        return self.returncode


class _WorkerOutput:
    def __init__(self, owner):
        self.owner = owner
        self.stdout = codecs.getincrementaldecoder("utf-8")()
        self.stderr = codecs.getincrementaldecoder("utf-8")()
        self.stderr_lines = _LineFramer()

    async def __aiter__(self):
        while self.owner._process.returncode is None:
            packet = await self.owner._read_packet()
            kind = packet.get("type")
            if kind == "stdout":
                yield self.stdout.decode(base64.b64decode(packet["data"], validate=True))
            elif kind == "stderr":
                text = self.stderr.decode(base64.b64decode(packet["data"], validate=True))
                for line in self.stderr_lines.push(text):
                    if self.owner._options.stderr:
                        with suppress(Exception):
                            self.owner._options.stderr(line.rstrip())
            elif kind == "exit":
                self.owner._process.returncode = packet["code"]
                self.owner._process.finished.set()
                tail = self.stdout.decode(b"", final=True)
                if tail:
                    yield tail
                return
            elif kind == "error":
                raise CLIConnectionError(packet.get("message") or packet.get("code", "IOS_RUNTIME_FAILED"))
            else:
                raise CLIConnectionError("IOS_RUNTIME_PACKET_INVALID")


class _WorkerInput:
    def __init__(self, owner):
        self.owner = owner

    async def send(self, value: str):
        await self.owner._send_packet({"type": "stdin", "data": base64.b64encode(value.encode()).decode()})

    async def aclose(self):
        await self.owner._send_packet({"type": "end_input"})


class IOSClaudeTransport(SubprocessCLITransport):
    """Reuse the pinned SDK's argv encoder and output parser without process creation."""
    def __init__(self, *, endpoint_path: str | Path, options):
        if sys.platform != "ios":
            raise CLIConnectionError("IOS_RUNTIME_TARGET_REQUIRED")
        project = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text())
        if f"ink-claude-dream-agent-sdk=={__version__}" not in project["project"]["dependencies"]:
            raise CLIConnectionError("IOS_RUNTIME_SDK_VERSION_MISMATCH")
        # The SDK owns the argument builder, framing, validation and control parser.
        # No subprocess transport connect/close method is invoked on this class.
        super().__init__(prompt="", options=_configure_can_use_tool(options))
        self._sdk_options = options
        self._mcp_scope = ExitStack()
        self.endpoint = read_native_endpoint(endpoint_path)
        self._cli_path = self.endpoint["runtimeEntry"]
        self._socket = None
        self._reader = None

    async def _send_packet(self, packet):
        await self._socket.send((json.dumps(packet) + "\n").encode())

    async def _read_packet(self):
        line = await self._reader.receive_until(b"\n", max_bytes=16 * 1024 * 1024)
        return json.loads(line)

    async def connect(self):
        if self._ready:
            return
        if not self._cwd:
            raise CLIConnectionError("IOS_RUNTIME_WORKSPACE_REQUIRED")
        from .ios_mcp import adapt_owned_mcp
        try:
            cli_options = self._mcp_scope.enter_context(adapt_owned_mcp(self._sdk_options, workspace_root=self.endpoint["workspaceRoot"]))
            self._options = _configure_can_use_tool(cli_options)
            env = dict(self._options.env or {})
            env.setdefault("HOME", str(Path.home()))
            if not env.get("HOME"):
                raise CLIConnectionError("IOS_RUNTIME_SESSION_HOME_REQUIRED")
            env.update(CLAUDE_CODE_ENTRYPOINT="sdk-py", CLAUDE_AGENT_SDK_VERSION=__version__)
            self._socket = await anyio.connect_tcp("127.0.0.1", self.endpoint["port"])
            self._reader = BufferedByteReceiveStream(self._socket)
            await self._send_packet({"type": "connect", "version": 1, "token": self.endpoint["token"],
                                     "cwd": str(Path(self._cwd).resolve()), "env": env,
                                     "argv": self._build_command()[1:]})
            packet = await self._read_packet()
            if packet.get("type") != "connected":
                raise CLIConnectionError(packet.get("code", "IOS_RUNTIME_CONNECT_FAILED"))
            self._process = _ThreadSession()
            self._stdout_stream = _WorkerOutput(self)
            self._stdin_stream = _WorkerInput(self)
            self._ready = True
        except BaseException:
            await self.close()
            raise

    async def close(self):
        if self._socket is None:
            self._ready = False
            self._mcp_scope.close()
            return
        # Match the SDK's bounded EOF grace period so the Runtime can flush JSONL.
        with anyio.CancelScope(shield=True):
            try:
                with anyio.move_on_after(5):
                    async with self._write_lock:
                        self._ready = False
                        if self._stdin_stream:
                            await self._stdin_stream.aclose()
                            self._stdin_stream = None
                    if self._stdout_stream and self._process.returncode is None:
                        async for _ in self._stdout_stream:
                            pass
                if self._process is not None and self._process.returncode is None:
                    try:
                        with anyio.fail_after(5):
                            await self._send_packet({"type": "terminate"})
                            if self._stdout_stream:
                                async for _ in self._stdout_stream:
                                    pass
                        if self._process.returncode is None:
                            raise CLIConnectionError("IOS_RUNTIME_CLOSE_UNCONFIRMED")
                    except TimeoutError as failure:
                        raise CLIConnectionError("IOS_RUNTIME_CLOSE_TIMEOUT") from failure
            finally:
                try:
                    await self._socket.aclose()
                finally:
                    self._socket = None
                    self._ready = False
                    self._mcp_scope.close()
