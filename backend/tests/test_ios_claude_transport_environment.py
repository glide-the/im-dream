# [Input] Production iOS transport, original SDK options and one fixture-owned loopback Worker handshake.
# [Output] PATH default/override and parent-secret isolation evidence without a Runtime, account or provider.
# [Pos] Provider-free iOS transport environment contract tests.
import asyncio
import json
import os
import sys

import pytest


@pytest.mark.parametrize(
    ("parent_path", "explicit_path", "expected_path"),
    [
        ("/server/verified-notion/bin:/bin", None, "/server/verified-notion/bin:/bin"),
        ("/server/verified-notion/bin:/bin", "/sdk/explicit/bin", "/sdk/explicit/bin"),
        ("/server/verified-notion/bin:/bin", "", ""),
        (None, None, None),
    ],
    ids=["server-path-default", "sdk-path-override", "explicit-empty-path", "missing-path"],
)
def test_owned_worker_environment_preserves_path_authority(
    tmp_path, monkeypatch, parent_path, explicit_path, expected_path,
):
    from claude_agent_sdk import ClaudeAgentOptions
    from mobile_runtime.ios_claude_transport import IOSClaudeTransport

    if parent_path is None:
        monkeypatch.delenv("PATH", raising=False)
    else:
        monkeypatch.setenv("PATH", parent_path)
    monkeypatch.setenv("INK_GATEWAY_SERVICE_KEY", "fixture-parent-secret-must-stay-out")
    workspace = tmp_path / "workspaces" / "thread-environment"
    workspace.mkdir(parents=True)
    cli = tmp_path / "runtime-entry.js"
    cli.write_text("// Fixture resource; execution is never requested.\n")
    overlay = {} if explicit_path is None else {"PATH": explicit_path}
    original_overlay = dict(overlay)
    packets = []

    async def scenario():
        async def worker(reader, writer):
            try:
                packets.append(json.loads(await reader.readline()))
                writer.write(b'{"type":"connected"}\n')
                await writer.drain()
                await reader.read()
            finally:
                writer.close()
                await writer.wait_closed()

        async with await asyncio.start_server(worker, "127.0.0.1", 0) as server:
            endpoint = tmp_path / "endpoint.json"
            endpoint.write_text(json.dumps({
                "version": 1, "pid": os.getpid(),
                "port": server.sockets[0].getsockname()[1],
                "token": "f" * 64, "runtimeEntry": str(cli),
                "workspaceRoot": str(workspace.parent),
            }))
            endpoint.chmod(0o600)
            options = ClaudeAgentOptions(cwd=str(workspace), cli_path=str(cli), env=overlay)
            with monkeypatch.context() as platform_patch:
                platform_patch.setattr(sys, "platform", "ios")
                transport = IOSClaudeTransport(endpoint_path=endpoint, options=options)
            try:
                await transport.connect()
                assert packets[0]["type"] == "connect"
                environment = packets[0]["env"]
                if expected_path is None:
                    assert "PATH" not in environment
                else:
                    assert environment["PATH"] == expected_path
                assert "INK_GATEWAY_SERVICE_KEY" not in environment
                assert overlay == original_overlay
                assert os.environ.get("PATH") == parent_path
            finally:
                # This fixture implements only the connection handshake, with
                # no guest process or stream requiring a production EOF grace.
                if transport._socket is not None:
                    await transport._socket.aclose()
                transport._mcp_scope.close()

    asyncio.run(scenario())
