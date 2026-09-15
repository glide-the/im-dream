# [Input] Explicit authorized SystemConfig snapshots and synthetic Gateway catalogs.
# [Output] Public Chat model-selection conflict, stale alias and Runtime projection evidence.
# [Pos] Provider-free Gateway boundary tests; no database, model call or normal account.
# [Sync] 2026-09-15: model selection consumes an explicitly authorized SystemConfig snapshot.
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
