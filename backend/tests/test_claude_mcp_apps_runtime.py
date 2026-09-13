# [Input] Installed SDK/Runtime, explicitly selected loopback MCP fixture, local fake Provider and disposable workspace.
# [Output] Raw SDK shape and production Runner-to-SSE-to-public-DTO MCP Apps compatibility evidence.
# [Pos] Process-isolated technical lane; run separately from SDK-stub suites, no real model or database.
# [Sync] 2026-09-13: cover original Runtime processed text/content MCP results rather than a constructed envelope.

import asyncio
import os
import tempfile
import threading
from copy import deepcopy
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

import pytest


@pytest.mark.skipif(not os.environ.get("INK_MCP_APPS_RUNTIME_FIXTURE_URL"), reason="explicit loopback MCP fixture required")
@pytest.mark.parametrize("permission_mode", ["auto-confirm", "manual-confirm", "full-access"])
def test_installed_runtime_processed_result_preserves_app_identity(permission_mode):
    from claude_agent.service import (
        ClaudeAgentService,
        _sse_events_to_ui_parts,
        _TurnContext,
    )
    from claude_agent.tool_confirmation_store import ToolConfirmationStore
    from libs.claude_agent_kit import AgentRunOptions, AgentStreamingCallbacks
    from libs.claude_agent_kit.server.agent_runner import ClaudeAgentRunner
    from libs.claude_agent_kit.server.workspace import init_workspace
    from routers.claude_agent import PublicChatMessageDto
    from tests.fixtures.claude_agent_sandbox_fake_provider import build_handler

    fixture_url = os.environ["INK_MCP_APPS_RUNTIME_FIXTURE_URL"]
    parsed = urlsplit(fixture_url)
    assert parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}
    assert parsed.port and not (parsed.username or parsed.password or parsed.query or parsed.fragment)
    server_ref, tool_name = "official-basic", "get-time"
    registered = f"mcp__{server_ref}__{tool_name}"
    requests, raw_results, confirmations = [], [], []
    provider = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(
        tool_name=registered, tool_input={}, final_text="MCP array fixture complete",
        requests_seen=requests, announce_requests=False,
    ))
    worker = threading.Thread(target=provider.serve_forever, daemon=True)
    worker.start()
    try:
        with tempfile.TemporaryDirectory(prefix="dream-mcp-array-runtime-") as tmp:
            root = Path(tmp).resolve()
            provider_url = f"http://127.0.0.1:{provider.server_port}"
            with patch.dict(os.environ, {
                "AGENT_CWD": str(root / "workspaces"), "CLAUDE_CONFIG_DIR": str(root / "claude-home"),
                "INK_GATEWAY_ENABLED": "0", "INK_GATEWAY_CLAUDE_AGENT_ENABLED": "0",
                "INK_LOAD_DATABASE_URL_FROM_ENV_FILE": "0", "ANTHROPIC_API_KEY": "", "CLAUDE_CODE_OAUTH_TOKEN": "",
                "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", "ANTHROPIC_BASE_URL": provider_url,
                "ANTHROPIC_AUTH_TOKEN": "isolated-mcp-array-provider-token",
            }):
                workspace = init_workspace("mcp-array-fixture", sandbox_enabled=True)

                async def run():
                    queue = asyncio.Queue()
                    context = _TurnContext(
                        queue=queue, confirmation_store=ToolConfirmationStore(),
                        managed_mcp_server_keys=(server_ref,),
                        managed_mcp_app_resource_bindings={server_ref: {tool_name: "ui://get-time/mcp-app.html"}},
                    )
                    def observe(message):
                        value = getattr(message, "tool_use_result", None)
                        if value is not None:
                            raw_results.append(deepcopy(value))
                    async def approve(payload):
                        assert payload["tool_name"] == registered
                        confirmations.append(payload["tool_name"])
                        return {"approved": True}
                    async with asyncio.timeout(60):
                        result = await ClaudeAgentRunner().run_streaming(
                            AgentRunOptions(
                                thread_id=None, user_message="Run the explicitly selected read-only MCP fixture.",
                                cwd=str(workspace), claude_tmp_workspace=str(workspace),
                                claude_config_home=str(root / "claude-home"), max_turns=3,
                                tool_choice="manual" if permission_mode == "manual-confirm" else "auto",
                                im_full_access_enabled=permission_mode == "full-access",
                                claude_mcp_servers={server_ref: {"type": "http", "url": fixture_url}},
                                user_sdk_env={"ANTHROPIC_BASE_URL": provider_url, "ANTHROPIC_AUTH_TOKEN": "isolated-mcp-array-provider-token"},
                            ),
                            AgentStreamingCallbacks(
                                on_text_delta=lambda _text: None, on_message=observe,
                                on_tool_confirmation_request=approve,
                                on_tool_event=ClaudeAgentService._make_tool_event_cb(queue, context),
                            ),
                        )
                    assert result.success and result.full_text == "MCP array fixture complete"
                    assert confirmations == ([] if permission_mode == "full-access" else [registered])
                    events = [queue.get_nowait().payload() for _ in range(queue.qsize())]
                    output = next(event for event in events if event["type"] == "tool-output-available")
                    assert len(raw_results) == 1
                    raw = raw_results[0]
                    # The official example returns structuredContent; original
                    # Runtime serializes it into the SDK envelope's content.
                    assert isinstance(raw, dict) and isinstance(raw.get("content"), str)
                    projection = output.get("mcpAppResult")
                    assert projection is not None, {"raw_sdk_result_type": type(raw).__name__, "app_projection": False}
                    assert projection["result"] == {**raw, "content": [{"type": "text", "text": raw["content"]}]}
                    assert projection["resourceUri"] == "ui://get-time/mcp-app.html"
                    public = PublicChatMessageDto.from_storage({
                        "id": "isolated-runtime-array", "role": "assistant",
                        "parts": _sse_events_to_ui_parts(context.collected_parts), "metadata": {},
                    }).model_dump(mode="json")
                    assert public["parts"][0]["mcpAppResult"] == deepcopy(projection)
                    print({"permission_mode": permission_mode, "raw_sdk_result_type": type(raw).__name__, "raw_content_type": type(raw["content"]).__name__, "live_app_projection": True, "public_refresh": True, "model_network": "loopback-fake-only"})
                asyncio.run(run())
    finally:
        provider.shutdown()
        provider.server_close()
        worker.join(timeout=5)
