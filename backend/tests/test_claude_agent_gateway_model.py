# [Input] Explicit authorized SystemConfig snapshots and synthetic Gateway catalogs.
# [Output] Public Chat model-selection conflict, stale alias and Runtime projection evidence.
# [Pos] Provider-free Gateway boundary tests; no database, model call or normal account.
# [Sync] 2026-09-15: model selection consumes an explicitly authorized SystemConfig snapshot.
# [Sync] 2026-09-17: Dream turns reuse only their current Admin gateway-cli grant for catalog reads.
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from backend.claude_agent import service as service_module
from backend.routers import claude_agent as route_module
from backend.services.admin_gateway.models import GatewayModel, GatewayModelCatalog
from services.admin_data.delegation import RuntimeGrant
from services.admin_data.errors import AdminDataError
from services.admin_data.gateway_runtime import AdminGatewayRuntime


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
    result = asyncio.run(route_module._resolve_platform_model_alias(7, None, {"model": "dream-balanced"}))
    assert result == "dream-balanced"


def test_client_cannot_override_server_side_platform_selection(monkeypatch) -> None:
    catalog = type("Catalog", (), {"fetch_catalog": lambda self: GatewayModelCatalog((model(), model("dream-fast")), "dream-balanced")})()
    monkeypatch.setattr(route_module, "GatewayModelCatalogClient", lambda _user_id: catalog)
    with pytest.raises(HTTPException) as captured:
        asyncio.run(route_module._resolve_platform_model_alias(7, "dream-fast", {"model": "dream-balanced"}))
    assert captured.value.status_code == 409
    assert captured.value.detail["error_code"] == "GATEWAY_MODEL_SELECTION_CONFLICT"


def test_selected_model_retains_runtime_projection(monkeypatch) -> None:
    catalog = type("Catalog", (), {"fetch_catalog": lambda self: GatewayModelCatalog((model(),), "dream-balanced")})()
    monkeypatch.setattr(route_module, "GatewayModelCatalogClient", lambda _user_id: catalog)
    selected = asyncio.run(route_module._resolve_platform_model_selection(7, None, {"model": "dream-balanced"}))
    assert selected.model_alias == "dream-balanced"
    assert selected.claude_code_runtime_env() == {
        "INK_CLAUDE_CODE_MODEL_MAX_OUTPUT_TOKENS": "8192",
    }


def test_selection_uses_only_supplied_config_snapshot(monkeypatch) -> None:
    catalog = type(
        "Catalog",
        (),
        {"fetch_catalog": lambda self: GatewayModelCatalog((model(),), "dream-balanced")},
    )()
    monkeypatch.setattr(route_module, "GatewayModelCatalogClient", lambda _user_id: catalog)
    selected = asyncio.run(route_module._resolve_platform_model_selection(7, None, {"model": "dream-balanced", "private": "kept-local"}))
    assert selected.model_alias == "dream-balanced"


def test_free_default_is_used_when_user_has_no_saved_model(monkeypatch) -> None:
    catalog = type("Catalog", (), {"fetch_catalog": lambda self: GatewayModelCatalog((model(),), "dream-balanced")})()
    monkeypatch.setattr(route_module, "GatewayModelCatalogClient", lambda _user_id: catalog)
    assert asyncio.run(route_module._resolve_platform_model_alias(7, None, {})) == "dream-balanced"


def test_stale_saved_model_returns_conflict_when_no_callable_default(monkeypatch) -> None:
    unavailable = GatewayModel(
        model_alias="dream-retired", display_name="Retired", protocol="anthropic",
        capabilities={}, context_window=None, max_output_tokens=None, enabled=True,
        callable=False, availability="maintenance", required_plan_code=None,
        upgrade_hint=None,
    )
    catalog = type("Catalog", (), {"fetch_catalog": lambda self: GatewayModelCatalog((unavailable,), None)})()
    monkeypatch.setattr(route_module, "GatewayModelCatalogClient", lambda _user_id: catalog)
    with pytest.raises(HTTPException) as captured:
        asyncio.run(route_module._resolve_platform_model_alias(7, None, {"model": "dream-retired"}))
    assert captured.value.status_code == 409
    assert captured.value.detail["error_code"] == "GATEWAY_MODEL_SELECTION_STALE"


def test_dream_turn_catalog_uses_current_gateway_runtime_grant(monkeypatch) -> None:
    token = "idg_" + "a" * 43
    now = datetime.now(timezone.utc)
    runtime = AdminGatewayRuntime(
        RuntimeGrant(
            token=token,
            purpose="gateway-cli",
            thread_id="thread-1",
            run_id="run-1",
            editor_session_id=None,
            scopes=("messages:create", "messages:count_tokens", "models:list"),
            expires_at=now + timedelta(minutes=5),
            maximum_expires_at=now + timedelta(minutes=10),
        ),
        Mock(),
    )
    observed_tokens: list[str] = []

    class CatalogClient:
        def __init__(self, *, access_token: str) -> None:
            observed_tokens.append(access_token)

        def fetch_catalog(self) -> GatewayModelCatalog:
            return GatewayModelCatalog((model(),), "dream-balanced")

    monkeypatch.setattr(service_module, "GatewayModelCatalogClient", CatalogClient)
    request = service_module.ClaudeAgentRunRequest(
        user_id="7",
        thread_id="thread-1",
        admin_gateway_runtime=runtime,
    )
    selected = service_module.ClaudeAgentService()._resolve_turn_platform_model(
        request,
        {"model": "dream-balanced"},
    )
    assert selected.model_alias == "dream-balanced"
    assert observed_tokens == [token]


def test_dream_turn_catalog_fails_closed_without_gateway_runtime(monkeypatch) -> None:
    monkeypatch.setattr(
        service_module,
        "GatewayModelCatalogClient",
        lambda **_kwargs: pytest.fail("catalog must not open without a runtime owner"),
    )
    request = service_module.ClaudeAgentRunRequest(
        user_id="7",
        thread_id="thread-1",
    )
    with pytest.raises(AdminDataError) as captured:
        service_module.ClaudeAgentService()._resolve_turn_platform_model(
            request,
            {"model": "dream-balanced"},
        )
    assert captured.value.code == "ADMIN_CONFIGURATION_INVALID"
