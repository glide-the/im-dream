# [Input] Production public/business routers, lazy package exports and the iOS ASGI entry.
# [Output] Real route responses, original authentication, transport validation and import/export regression.
# [Pos] Provider-free tests; no full server import or external service starts.
# [Sync] 2026-10-25: cover extracted routes and the same embedded backend entry.
# [Sync] 2026-10-25: bootstrap only public handlers before the native Runtime owner binds the full router graph.
import json
from importlib import import_module
from pathlib import Path
import subprocess
import sys

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from mobile_runtime import ios
from routers.public import create_public_router
from seo_content import build_llms_txt, build_robots_txt, build_sitemap_xml


def test_shared_public_routes_keep_existing_responses():
    app = FastAPI()
    app.include_router(create_public_router(
        backend_version="current-version", cors_allow_origins=["https://frontend.example"],
        public_base_url="https://frontend.example", backend_public_base_url="https://backend.example",
    ))
    with TestClient(app) as client:
        assert client.get("/").text == (
            "The server is configured with a public base URL of https://backend.example/"
            " - did you mean to visit https://backend.example/api/claude-agent/threads instead?"
        )
        assert client.get("/api/health").json() == {
            "status": "ok", "version": "current-version", "cors_allow_origins": ["https://frontend.example"],
        }
        assert client.get("/robots.txt").text == build_robots_txt("https://frontend.example")
        assert client.get("/sitemap.xml").text == build_sitemap_xml("https://frontend.example")
        assert client.get("/llms.txt").text == build_llms_txt("https://frontend.example", "https://backend.example")


def test_embedded_entry_executes_real_asgi_handlers():
    facts = json.loads(ios.start())
    assert facts["businessReady"] is False
    assert facts["health"]["status"] == "ok"
    assert {"/", "/api/health", "/robots.txt", "/sitemap.xml", "/llms.txt"} <= set(facts["routes"])
    assert facts["businessRouterModules"] == []
    assert "/api/claude-agent/threads" not in facts["routes"]
    assert json.loads(ios.request(json.dumps({"method": "GET", "path": "/api/health"})))["status"] == 200
    assert json.loads(ios.request(json.dumps({"method": "GET", "path": "/unknown"})))["status"] == 404


def test_existing_business_configuration_and_authentication_boundaries():
    # Host fixture checks original handlers without pretending to own a native
    # Runtime endpoint. The target XCTest verifies the complete 24-router entry.
    app = FastAPI()
    for name in ("auth", "oauth", "device_oauth", "sessions", "pictures", "preferences",
                 "reports", "voices", "friends", "deck_versions", "memory"):
        app.include_router(import_module("routers." + name).router)
    with TestClient(app) as client:
        defaults = client.get("/api/default-voices")
        voices = defaults.json()
        assert defaults.status_code == 200
        assert set(voices) == {"holder", "starter", "mirror", "weaver", "absurdist"}
        assert all(voice["systemPrompt"] for voice in voices.values())
        for path in ("/api/me", "/api/sessions?limit=2", "/api/decks", "/api/preferences", "/api/reports"):
            response = client.get(path)
            assert response.status_code == 401
            assert response.json()["detail"] == "Missing authorization token"
        assert client.post("/api/sessions", json={}).status_code == 401


@pytest.mark.parametrize("value", [
    {"method": "CONNECT", "path": "/api/sessions"},
    {"method": "GET", "path": "https://outside.example/api/sessions"},
    {"method": "GET", "path": "//outside.example/api/sessions"},
    {"method": "GET", "path": "/api/%2e%2e/private"},
    {"method": "GET", "path": "/api/sessions", "headers": {"Authorization": "not-a-credential"}},
    {"method": "GET", "path": "/api/sessions", "headers": {"x-ink-dream-service-authorization": "not-a-credential"}},
    {"method": "GET", "path": "/api/sessions", "headers": {"x-user-id": "test"}},
    {"method": "GET", "path": "/api/sessions", "headers": {"Accept": "json\r\nInjected: value"}},
    {"method": "POST", "path": "/api/sessions", "bodyBase64": "!invalid!"},
    {"method": "POST", "path": "/api/sessions", "bodyBase64": "A" * (4 * ((ios._policy["maximumInlineRequestBytes"] + 2) // 3) + 4)},
])
def test_embedded_request_rejects_invalid_transport_inputs(value):
    ios.start()
    with pytest.raises(ValueError):
        ios.request(json.dumps(value))


def test_business_imports_do_not_load_executable_agent_services():
    backend = Path(__file__).resolve().parents[1]
    script = '''
import importlib.abc, sys
sys.path.insert(0, sys.argv[1])
class BlockAgent(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'claude_agent_sdk', 'mcp', 'agent_factory'}:
            raise AssertionError('Unexpected executable Agent import: ' + fullname)
        if fullname == 'services.claude_plugin.install_service':
            raise AssertionError('Unexpected executable plugin import')
sys.meta_path.insert(0, BlockAgent())
from mobile_runtime import ios
from libs.claude_agent_kit import AttachmentPayload
from libs.claude_agent_kit.messages import AttachmentPayload as expected
assert AttachmentPayload is expected
assert 'libs.claude_agent_kit.server.agent_runner' not in sys.modules
assert ios._business_routers == ()
'''
    result = subprocess.run([sys.executable, "-I", "-c", script, str(backend)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_lazy_public_exports_keep_existing_execution_objects():
    import libs.claude_agent_kit as kit
    from libs.claude_agent_kit.server.agent_runner import ClaudeAgentRunner
    from libs.claude_agent_kit.server.simple_cas_client import SimpleClaudeAgentSDKClient
    from libs.claude_agent_kit.server.workspace import get_or_create_workspace

    assert kit.ClaudeAgentRunner is ClaudeAgentRunner
    assert kit.SimpleClaudeAgentSDKClient is SimpleClaudeAgentSDKClient
    assert kit.get_or_create_workspace is get_or_create_workspace
