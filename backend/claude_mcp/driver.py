"""Official Claude Code MCP argv and PTY driver.

[Input] Exact runtime identity plus `mcp list/get/add/remove/login/logout` argv arguments.
[Output] Bounded command results or a live login PTY with stdin and process-group control.
[Pos] Only module allowed to spawn Claude MCP subprocesses; never invokes a shell.
[Sync] 2026-08-19: add timeout-safe short commands and same-process headless OAuth PTY exchange.
[Sync] 2026-08-19: add restricted user-scope HTTP add/remove argv wrappers.
[Sync] 2026-08-20: bind config and secure-storage selectors to the same platform-user identity.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import errno
import os
from pathlib import Path
import pty
import signal
import termios
from typing import Sequence

from .contracts import ClaudeMcpRuntimeIdentity
from .parser import redact_sensitive
from .settings import ClaudeMcpSettings


@dataclass(frozen=True)
class ClaudeMcpCommandResult:
    argv: tuple[str, ...]
    exit_code: int
    output: str
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


async def _terminate_process(
    process: asyncio.subprocess.Process,
    *,
    grace_seconds: int,
) -> None:
    if process.returncode is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        process.terminate()
    try:
        await asyncio.wait_for(process.wait(), timeout=grace_seconds)
        return
    except asyncio.TimeoutError:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        process.kill()
    await process.wait()


class ClaudeMcpLoginHandle:
    """One live `claude mcp login --no-browser` process and its PTY master."""

    def __init__(
        self,
        process: asyncio.subprocess.Process,
        master_fd: int,
        settings: ClaudeMcpSettings,
    ) -> None:
        self.process = process
        self._master_fd = master_fd
        self._settings = settings
        self._closed = False

    async def read(self) -> bytes:
        if self._closed:
            return b""
        loop = asyncio.get_running_loop()
        future: asyncio.Future[bytes] = loop.create_future()

        def ready() -> None:
            if future.done():
                return
            try:
                data = os.read(self._master_fd, 4096)
            except OSError as exc:
                if exc.errno == errno.EIO:
                    data = b""
                else:
                    future.set_exception(exc)
                    return
            future.set_result(data)

        loop.add_reader(self._master_fd, ready)
        try:
            return await future
        finally:
            loop.remove_reader(self._master_fd)

    async def write_redirect(self, redirect_url: str) -> None:
        if self._closed or self.process.returncode is not None:
            raise BrokenPipeError("Claude MCP login process is no longer running")
        payload = (redirect_url + "\n").encode("utf-8")
        await asyncio.to_thread(os.write, self._master_fd, payload)

    async def wait(self) -> int:
        return await self.process.wait()

    async def terminate(self) -> None:
        await _terminate_process(
            self.process,
            grace_seconds=self._settings.terminate_grace_seconds,
        )
        self.close()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            os.close(self._master_fd)
        except OSError:
            pass


class ClaudeMcpCliDriver:
    """Execute the supported public Claude Code MCP commands with argv arrays."""

    def __init__(self, settings: ClaudeMcpSettings | None = None) -> None:
        self.settings = settings or ClaudeMcpSettings.from_env()

    @staticmethod
    def _argv(
        identity: ClaudeMcpRuntimeIdentity,
        parts: Sequence[str],
    ) -> tuple[str, ...]:
        if not parts or not all(isinstance(part, str) and part for part in parts):
            raise ValueError("command parts must be non-empty strings")
        return (*identity.command, *parts)

    @staticmethod
    def _env(identity: ClaudeMcpRuntimeIdentity) -> dict[str, str]:
        env = dict(identity.env)
        env["CLAUDE_CONFIG_DIR"] = str(identity.config_dir)
        # Claude Code stores OAuth secrets in a config-dir-keyed Keychain item
        # on macOS and in `.credentials.json` on Linux.  Pin both selectors to
        # the server-owned platform-user directory so login/get/logout and the
        # Agent runtime address exactly the same credential identity.  This is
        # deliberately assigned, not inherited from backend or browser input.
        env["CLAUDE_SECURESTORAGE_CONFIG_DIR"] = str(identity.config_dir)
        return env

    async def run(
        self,
        identity: ClaudeMcpRuntimeIdentity,
        parts: Sequence[str],
    ) -> ClaudeMcpCommandResult:
        argv = self._argv(identity, parts)
        process = await asyncio.create_subprocess_exec(
            *argv,
            cwd=str(identity.cwd),
            env=self._env(identity),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            start_new_session=True,
        )
        timed_out = False
        try:
            output, _ = await asyncio.wait_for(
                process.communicate(),
                timeout=self.settings.command_timeout_seconds,
            )
        except asyncio.TimeoutError:
            timed_out = True
            await _terminate_process(
                process,
                grace_seconds=self.settings.terminate_grace_seconds,
            )
            output = b""
        return ClaudeMcpCommandResult(
            argv=argv,
            exit_code=process.returncode if process.returncode is not None else -1,
            output=redact_sensitive(
                output.decode("utf-8", errors="replace"),
                max_bytes=self.settings.max_capture_bytes,
            ),
            timed_out=timed_out,
        )

    async def version(self, identity: ClaudeMcpRuntimeIdentity) -> ClaudeMcpCommandResult:
        return await self.run(identity, ("--version",))

    async def list_servers(
        self, identity: ClaudeMcpRuntimeIdentity
    ) -> ClaudeMcpCommandResult:
        return await self.run(identity, ("mcp", "list"))

    async def login_help(
        self, identity: ClaudeMcpRuntimeIdentity
    ) -> ClaudeMcpCommandResult:
        return await self.run(identity, ("mcp", "login", "--help"))

    async def logout_help(
        self, identity: ClaudeMcpRuntimeIdentity
    ) -> ClaudeMcpCommandResult:
        return await self.run(identity, ("mcp", "logout", "--help"))

    async def add_help(
        self, identity: ClaudeMcpRuntimeIdentity
    ) -> ClaudeMcpCommandResult:
        return await self.run(identity, ("mcp", "add", "--help"))

    async def remove_help(
        self, identity: ClaudeMcpRuntimeIdentity
    ) -> ClaudeMcpCommandResult:
        return await self.run(identity, ("mcp", "remove", "--help"))

    async def get_server(
        self,
        identity: ClaudeMcpRuntimeIdentity,
        server_name: str,
    ) -> ClaudeMcpCommandResult:
        return await self.run(identity, ("mcp", "get", server_name))

    async def logout(
        self,
        identity: ClaudeMcpRuntimeIdentity,
        server_name: str,
    ) -> ClaudeMcpCommandResult:
        return await self.run(identity, ("mcp", "logout", server_name))

    async def add_http_user_server(
        self,
        identity: ClaudeMcpRuntimeIdentity,
        server_name: str,
        server_url: str,
    ) -> ClaudeMcpCommandResult:
        return await self.run(
            identity,
            (
                "mcp",
                "add",
                "--transport",
                "http",
                "--scope",
                "user",
                server_name,
                server_url,
            ),
        )

    async def remove_user_server(
        self,
        identity: ClaudeMcpRuntimeIdentity,
        server_name: str,
    ) -> ClaudeMcpCommandResult:
        return await self.run(
            identity,
            ("mcp", "remove", "--scope", "user", server_name),
        )

    async def start_login(
        self,
        identity: ClaudeMcpRuntimeIdentity,
        server_name: str,
    ) -> ClaudeMcpLoginHandle:
        argv = self._argv(
            identity,
            ("mcp", "login", server_name, "--no-browser"),
        )
        master_fd, slave_fd = pty.openpty()
        terminal_attributes = termios.tcgetattr(slave_fd)
        terminal_attributes[3] &= ~termios.ECHO
        termios.tcsetattr(slave_fd, termios.TCSANOW, terminal_attributes)
        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                cwd=str(identity.cwd),
                env=self._env(identity),
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                start_new_session=True,
            )
        except Exception:
            os.close(master_fd)
            os.close(slave_fd)
            raise
        os.close(slave_fd)
        return ClaudeMcpLoginHandle(process, master_fd, self.settings)
