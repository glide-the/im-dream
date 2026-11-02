# [Input] Original owned MCP factories, private projections, production broker and real DTOs.
# [Output] Per-server context isolation, original schema/results, projection restoration and input rejection.
# [Pos] Provider-free iOS MCP adapter tests; only disposable local files and broker sockets.
from dataclasses import dataclass
import asyncio
import json
import os

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mobile_runtime.ios_mcp import adapt_owned_mcp
from libs.claude_agent_kit.server.agent_runner import _user_mcp_stdio_config, _write_mcp_config_projection
from libs.claude_agent_kit.server.mcp_server import USER_MCP_TOOL_NAMES
from services.admin_data.session_models import SessionListResultDTO
from services.admin_data.session_projection_broker import SessionProjectionBroker, SessionProjectionBrokerSettings


@dataclass
class Options:
    mcp_servers: object


class Provider:
    def __init__(self, label):
        self.label = label
        self.calls = []

    def list_sessions(self, value, request_id):
        self.calls.append((value, request_id))
        return SessionListResultDTO.model_validate({"sessions": [{"id": self.label, "name": self.label,
            "labels": [], "created_at": None, "updated_at": None, "first_line": self.label, "text": None}]})


def test_original_user_mcp_handlers_keep_two_brokers_and_remote_headers_isolated(tmp_path):
    providers = [Provider("one"), Provider("two")]
    brokers = [SessionProjectionBroker(provider, settings=SessionProjectionBrokerSettings(timeout_seconds=5, max_bytes=1_048_576))
               for provider in providers]
    environment = dict(os.environ)
    for broker in brokers:
        broker.start()
    try:
        options, originals = [], []
        for number, broker in enumerate(brokers):
            root = tmp_path / str(number)
            root.mkdir(mode=0o700)
            path = _write_mcp_config_projection({"user": _user_mcp_stdio_config(broker.child_env()),
                "remote": {"type": "http", "url": "https://example.invalid/mcp", "headers": {"Authorization": "fixture-only"}}},
                thread_workspace=str(root))
            options.append(Options(path))
            originals.append(path.read_bytes())
        with adapt_owned_mcp(options[0], workspace_root=str(tmp_path)) as cli_one:
            with adapt_owned_mcp(options[1], workspace_root=str(tmp_path)) as cli_two:
                for option, cli in zip(options, [cli_one, cli_two]):
                    assert list(option.mcp_servers) == ["user"]
                    document = json.loads(cli.mcp_servers.read_text())
                    assert document["mcpServers"]["user"] == {"type": "sdk", "name": "user"}
                    assert document["mcpServers"]["remote"]["headers"] == {"Authorization": "fixture-only"}
                async def call(option, label):
                    async with create_connected_server_and_client_session(option.mcp_servers["user"]["instance"]) as client:
                        tools = await client.list_tools()
                        assert {item.name for item in tools.tools} == USER_MCP_TOOL_NAMES
                        result = await client.call_tool("get_sessions_range", {"start_date": "2026-01-01", "end_date": "2026-01-02"})
                        assert not result.isError
                        data = json.loads(result.content[0].text)
                        assert data["ok"] is True and data["sessions"][0]["sessionId"] == label
                async def run():
                    await asyncio.gather(call(options[0], "one"), call(options[1], "two"))
                asyncio.run(run())
        assert all(option.mcp_servers.read_bytes() == original for option, original in zip(options, originals))
        assert all(len(provider.calls) == 1 for provider in providers)
        assert dict(os.environ) == environment
    finally:
        for broker in brokers:
            broker.close()


@pytest.mark.parametrize("failure", ["command", "permissions", "symlink", "outside"])
def test_invalid_owned_projection_is_rejected_without_rewriting_it(tmp_path, failure):
    root = tmp_path / "workspace"
    root.mkdir(mode=0o700)
    source = root / "private.json"
    document = {"mcpServers": {"user": _user_mcp_stdio_config({})}}
    if failure == "command":
        document["mcpServers"]["user"]["args"] = ["-c", "raise AssertionError()"]
    source.write_text(json.dumps(document))
    source.chmod(0o644 if failure == "permissions" else 0o600)
    original = source.read_bytes()
    selected = source
    if failure == "symlink":
        selected = root / "alias.json"
        selected.symlink_to(source)
    if failure == "outside":
        root = tmp_path / "other"
        root.mkdir()
    options = Options(selected)
    with pytest.raises(ValueError, match="IOS_MCP_"):
        with adapt_owned_mcp(options, workspace_root=str(root)):
            pytest.fail("Invalid projection reached SDK startup")
    assert source.read_bytes() == original and options.mcp_servers == selected


def test_projection_is_restored_after_connect_failure(tmp_path):
    source = _write_mcp_config_projection({"user": _user_mcp_stdio_config({})}, thread_workspace=str(tmp_path))
    original = source.read_bytes()
    options = Options(source)
    with pytest.raises(RuntimeError, match="fixture connection failure"):
        with adapt_owned_mcp(options, workspace_root=str(tmp_path)):
            assert isinstance(options.mcp_servers, dict)
            raise RuntimeError("fixture connection failure")
    assert source.read_bytes() == original and options.mcp_servers == source
