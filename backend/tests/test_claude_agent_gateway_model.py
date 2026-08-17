from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from backend.routers import claude_agent as route_module
from backend.services.admin_gateway.models import GatewayModel, GatewayModelCatalog


def model(alias: str = "dream-balanced") -> GatewayModel:
    return GatewayModel(
        model_alias=alias,
        display_name="Dream Balanced",
        protocol="anthropic",
        capabilities={"tools": True},
        context_window=200000,
        max_output_tokens=8192,
        enabled=True,
        callable=True,
        availability="included",
        required_plan_code="free",
        upgrade_hint=None,
    )


def test_server_side_selection_drives_claude_agent_model(monkeypatch) -> None:
    catalog = type("Catalog", (), {"fetch_catalog": lambda self: GatewayModelCatalog((model(),), "dream-balanced")})()
    monkeypatch.setattr(route_module, "GatewayModelCatalogClient", lambda _user_id: catalog)
    monkeypatch.setattr(route_module.database, "get_system_config", lambda _user_id: {"model": "dream-balanced"})

    result = asyncio.run(route_module._resolve_platform_model_alias(7, None))
    assert result == "dream-balanced"


def test_client_cannot_override_server_side_platform_selection(monkeypatch) -> None:
    catalog = type("Catalog", (), {"fetch_catalog": lambda self: GatewayModelCatalog((model(), model("dream-fast")), "dream-balanced")})()
    monkeypatch.setattr(route_module, "GatewayModelCatalogClient", lambda _user_id: catalog)
    monkeypatch.setattr(route_module.database, "get_system_config", lambda _user_id: {"model": "dream-balanced"})

    with pytest.raises(HTTPException) as captured:
        asyncio.run(route_module._resolve_platform_model_alias(7, "dream-fast"))
    assert captured.value.status_code == 409
    assert captured.value.detail["error_code"] == "GATEWAY_MODEL_SELECTION_CONFLICT"


def test_complete_http_turn_passes_saved_platform_alias_to_agent_runner(monkeypatch) -> None:
    captured_requests = []
    catalog = type("Catalog", (), {"fetch_catalog": lambda self: GatewayModelCatalog((model(),), "dream-balanced")})()
    monkeypatch.setattr(route_module, "GatewayModelCatalogClient", lambda _user_id: catalog)
    monkeypatch.setattr(route_module.database, "get_system_config", lambda _user_id: {"model": "dream-balanced"})
    monkeypatch.setattr(route_module.database, "get_chat_thread", lambda _thread_id, _user_id: {"id": "thread-1"})

    async def run_streaming(request):
        captured_requests.append(request)
        yield 'data: {"type":"finish"}\n\n'

    monkeypatch.setattr(route_module.claude_agent_thread_factory, "run_streaming", run_streaming)

    async def exercise() -> None:
        response = await route_module.claude_agent_stream(
            route_module.ClaudeAgentRequestBody(
                thread_id="thread-1",
                message="hello",
            ),
            current_user={"user_id": 7},
        )
        async for _chunk in response.body_iterator:
            pass

    asyncio.run(exercise())
    assert captured_requests[0].model == "dream-balanced"
    assert captured_requests[0].user_id == "7"


def test_complete_http_turn_keeps_dream_binding_out_of_public_request(monkeypatch) -> None:
    captured_requests = []
    catalog = type(
        "Catalog",
        (),
        {"fetch_catalog": lambda self: GatewayModelCatalog((model(),), "dream-balanced")},
    )()
    monkeypatch.setattr(route_module, "GatewayModelCatalogClient", lambda _user_id: catalog)
    monkeypatch.setattr(
        route_module.database,
        "get_system_config",
        lambda _user_id: {"model": "dream-balanced"},
    )
    monkeypatch.setattr(
        route_module.database,
        "get_chat_thread",
        lambda _thread_id, _user_id: {
            "id": "thread-dream",
            "user_id": 7,
            "deck_id": None,
            "voice_id": None,
        },
    )
    monkeypatch.setattr(
        route_module.database,
        "save_chat_message",
        lambda *_args, **_kwargs: "browser-message-1",
    )

    async def run_streaming(request):
        captured_requests.append(request)
        yield 'data: {"type":"finish"}\n\n'

    monkeypatch.setattr(route_module.claude_agent_thread_factory, "run_streaming", run_streaming)

    async def exercise() -> None:
        response = await route_module.claude_agent_stream(
            route_module.ClaudeAgentRequestBody(
                thread_id="thread-dream",
                message={
                    "id": "browser-message-1",
                    "parts": [{"type": "text", "text": "continue"}],
                },
            ),
            current_user={"user_id": 7},
        )
        async for _chunk in response.body_iterator:
            pass

    asyncio.run(exercise())
    request = captured_requests[0]
    assert not hasattr(request, "story_workspace_dream_context")
    assert request.message_metadata is None


def test_free_default_is_used_when_user_has_no_saved_model(monkeypatch) -> None:
    catalog = type("Catalog", (), {"fetch_catalog": lambda self: GatewayModelCatalog((model(),), "dream-balanced")})()
    monkeypatch.setattr(route_module, "GatewayModelCatalogClient", lambda _user_id: catalog)
    monkeypatch.setattr(route_module.database, "get_system_config", lambda _user_id: {})

    assert asyncio.run(route_module._resolve_platform_model_alias(7, None)) == "dream-balanced"


def test_stale_saved_model_returns_conflict_when_no_callable_default(monkeypatch) -> None:
    unavailable = GatewayModel(
        model_alias="dream-retired", display_name="Retired", protocol="anthropic",
        capabilities={}, context_window=None, max_output_tokens=None, enabled=True,
        callable=False, availability="maintenance", required_plan_code=None,
        upgrade_hint=None,
    )
    catalog = type("Catalog", (), {"fetch_catalog": lambda self: GatewayModelCatalog((unavailable,), None)})()
    monkeypatch.setattr(route_module, "GatewayModelCatalogClient", lambda _user_id: catalog)
    monkeypatch.setattr(route_module.database, "get_system_config", lambda _user_id: {"model": "dream-retired"})

    with pytest.raises(HTTPException) as captured:
        asyncio.run(route_module._resolve_platform_model_alias(7, None))
    assert captured.value.status_code == 409
    assert captured.value.detail["error_code"] == "GATEWAY_MODEL_SELECTION_STALE"
