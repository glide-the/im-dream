from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers import gateway_models as route_module
from backend.services.admin_gateway.models import GatewayModel


def test_bff_returns_only_claude_agent_scoped_models(monkeypatch) -> None:
    app = FastAPI()
    app.dependency_overrides[route_module.get_current_user] = lambda: {"user_id": 7}
    app.include_router(route_module.router)

    catalog = type("Catalog", (), {
        "list_models": lambda self: [
            GatewayModel(
                model_alias="dream-balanced",
                display_name="Dream Balanced",
                protocol="anthropic",
                capabilities={"tools": True},
                gateway_scopes=("messages:create", "models:list"),
                context_window=200000,
                max_output_tokens=8192,
            ),
            GatewayModel(
                model_alias="image-only",
                display_name="Image Only",
                protocol="openai",
                capabilities={"image": True},
                gateway_scopes=("images:create", "models:list"),
                context_window=None,
                max_output_tokens=None,
            ),
        ],
    })()
    monkeypatch.setattr(route_module, "GatewayModelCatalogClient", lambda _user_id: catalog)

    with TestClient(app) as client:
        response = client.get("/api/gateway/models")
    assert response.status_code == 200
    assert [item["modelAlias"] for item in response.json()["data"]] == ["dream-balanced"]
    assert "ownedBy" not in response.text

