# [Input] Original Notion command helper and explicit in-process Worker protocol fixtures.
# [Output] Argument/environment identity, exit/error and cancel-and-wait qualification without Notion credentials.
# [Pos] Provider-free transport tests; packaged binary execution is separately tested on the iOS target.
import asyncio
import base64
import json

import pytest


@pytest.mark.parametrize("mode", ["success", "error", "cancel"])
def test_original_notion_command_uses_owned_worker_and_preserves_cancellation(tmp_path, monkeypatch, mode):
    from mobile_runtime import ios_notion_runtime as native
    from notion import auth
    from notion.errors import NotionCLIUnavailableError

    executable = tmp_path / "ntn"
    executable.write_bytes(b"explicit fixture; never executed")
    executable.chmod(0o700)
    home = tmp_path / "actor-home"
    packets = []
    ready = None

    async def scenario():
        nonlocal ready
        ready = asyncio.Event()

        async def worker(reader, writer):
            try:
                packet = json.loads(await reader.readline())
                packets.append(packet)
                assert packet["argv"] == [str(executable), "--version"]
                assert packet["cwd"] == str(home)
                assert packet["env"]["NOTION_HOME"] == str(home)
                assert packet["env"]["NOTION_KEYRING"] == "0"
                assert "HOME" not in packet["env"] and "NOTION_API_TOKEN" not in packet["env"]
                if mode == "error":
                    writer.write(b'{"type":"error","code":"IOS_NOTION_CLI_EXECUTABLE_INVALID"}\n')
                    await writer.drain()
                    return
                writer.write(b'{"type":"connected"}\n'); await writer.drain()
                assert json.loads(await reader.readline()) == {"type": "end_input"}
                ready.set()
                if mode == "cancel":
                    assert json.loads(await reader.readline()) == {"type": "terminate"}
                    packets.append({"terminated": True})
                    writer.write(b'{"type":"exit","code":137}\n')
                else:
                    writer.write((json.dumps({"type": "stdout", "data": base64.b64encode(b"ntn 0.15.1\n").decode()}) + "\n").encode())
                    writer.write(b'{"type":"exit","code":0}\n')
                await writer.drain()
            finally:
                writer.close(); await writer.wait_closed()

        async with await asyncio.start_server(worker, "127.0.0.1", 0) as server:
            endpoint = {"port": server.sockets[0].getsockname()[1], "token": "protocol-fixture-only"}
            monkeypatch.setattr(native, "read_native_endpoint", lambda _path: endpoint)
            monkeypatch.setattr(native, "_endpoint_path", tmp_path / "fixture-endpoint")
            monkeypatch.setattr(native, "_executable", executable)
            monkeypatch.setattr(auth, "_process_factory", native._create_process)
            monkeypatch.setenv("INK_NOTION_CLI_PATH", str(executable))
            monkeypatch.setenv("NOTION_API_TOKEN", "ambient-token-must-not-reach-child")
            operation = asyncio.create_task(auth._run_ntn_command("--version", notion_home=home, timeout_seconds=5))
            if mode == "error":
                with pytest.raises(NotionCLIUnavailableError):
                    await operation
            elif mode == "cancel":
                await asyncio.wait_for(ready.wait(), 5)
                operation.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await operation
                assert packets[-1] == {"terminated": True}
            else:
                assert await operation == (0, "ntn 0.15.1\n", "")
        assert packets[0]["purpose"] == "notion-cli"

    asyncio.run(scenario())
