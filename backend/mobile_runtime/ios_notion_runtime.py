# [Input] Original Notion argv/env and the application-owned Node endpoint and pinned executable.
# [Output] Original communicate/wait/kill contract through the existing authenticated command Worker.
# [Pos] iOS Notion process adapter; actor credentials, OAuth, queries and synchronization retain their original owners.
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
from pathlib import Path

from notion.auth import bind_notion_process_factory
from notion.errors import NotionCLIUnavailableError
from .ios_claude_transport import read_native_endpoint

_endpoint_path = None
_executable = None


def prepare_notion_runtime(endpoint_path):
    global _endpoint_path, _executable
    endpoint = read_native_endpoint(endpoint_path)
    resource = Path(endpoint["runtimeEntry"]).parents[1] / "notion"
    manifest = json.loads((resource / "manifest.json").read_text())
    guest_manifest = json.loads((resource.parents[1] / "guest/manifest.json").read_text())
    executable = (Path(endpoint_path).parent / "guest" / guest_manifest["rootDigest"] / "usr/local/bin/ntn").resolve(strict=True)
    from notion.auth import NOTION_CLI_VERSION
    if manifest["version"] != NOTION_CLI_VERSION or hashlib.sha256(executable.read_bytes()).hexdigest() != manifest["binarySha256"]:
        raise NotionCLIUnavailableError("Notion service is temporarily unavailable.")
    canonical = Path(endpoint_path).resolve(strict=True)
    if _endpoint_path is not None and _endpoint_path != canonical:
        raise NotionCLIUnavailableError("Notion command execution is already bound.")
    _endpoint_path, _executable = canonical, executable
    os.environ["INK_NOTION_CLI_PATH"] = str(executable)
    os.environ["PATH"] = str(executable.parent) + os.pathsep + os.environ.get("PATH", "")
    bind_notion_process_factory(_create_process)


async def _create_process(*argv, env, stdout, stderr):
    if not _endpoint_path or not argv or Path(argv[0]).resolve() != _executable or stdout != asyncio.subprocess.PIPE or stderr != asyncio.subprocess.PIPE:
        raise NotionCLIUnavailableError("Notion service is temporarily unavailable.")
    endpoint = read_native_endpoint(_endpoint_path)
    reader, writer = await asyncio.open_connection("127.0.0.1", endpoint["port"], limit=128 * 1024)
    try:
        writer.write((json.dumps({"type": "connect", "version": 1, "token": endpoint["token"],
            "purpose": "notion-cli", "cwd": env["NOTION_HOME"], "env": env, "argv": list(argv)}) + "\n").encode())
        await writer.drain()
    except BaseException:
        writer.close(); await writer.wait_closed(); raise
    return _NativeNotionProcess(reader, writer)


class _NativeNotionProcess:
    def __init__(self, reader, writer):
        self.reader, self.writer = reader, writer
        self.returncode = None
        self._completion = asyncio.create_task(self._read())

    async def communicate(self):
        return await asyncio.shield(self._completion)

    async def _read(self):
        output = {"stdout": bytearray(), "stderr": bytearray()}
        connected = False
        try:
            while line := await self.reader.readline():
                packet = json.loads(line)
                kind = packet.get("type")
                if kind == "connected" and not connected:
                    connected = True; self.writer.write(b'{"type":"end_input"}\n'); await self.writer.drain()
                elif connected and kind in output:
                    output[kind].extend(base64.b64decode(packet["data"], validate=True))
                elif connected and kind == "exit" and type(packet.get("code")) is int:
                    self.returncode = packet["code"]
                    return bytes(output["stdout"]), bytes(output["stderr"])
                else:
                    raise NotionCLIUnavailableError("Notion command execution failed.")
            raise NotionCLIUnavailableError("Notion command execution stopped.")
        finally:
            self.writer.close(); await self.writer.wait_closed()

    def kill(self):
        if self.returncode is not None:
            return
        if not self.writer.is_closing():
            self.writer.write(b'{"type":"terminate"}\n')

    async def wait(self):
        await asyncio.shield(self._completion)
        return self.returncode
