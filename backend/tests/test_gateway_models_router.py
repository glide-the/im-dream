from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers import gateway_models as route_module
from backend.services.admin_gateway.models import GatewayModel, GatewayModelCatalog


def test_bff_returns_all_visible_models_with_callability(monkeypatch) -> None:
    app = FastAPI()
    app.dependency_overrides[route_module.get_current_user] = lambda: {"user_id": 7}
    app.include_router(route_module.router)

    catalog = type("Catalog", (), {
        "fetch_catalog": lambda self: GatewayModelCatalog((
            GatewayModel(
                model_alias="dream-balanced",
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
            ),
            GatewayModel(
                model_alias="image-only",
                display_name="Image Only",
                protocol="openai",
                capabilities={"image": True},
                context_window=None,
                max_output_tokens=None,
                enabled=True,
                callable=False,
                availability="upgrade_required",
                required_plan_code="dream",
                upgrade_hint="升级 Dream 后可用",
            ),
        ), "dream-balanced"),
    })()
    monkeypatch.setattr(route_module, "GatewayModelCatalogClient", lambda _user_id: catalog)

    with TestClient(app) as client:
        response = client.get("/api/gateway/models")
    assert response.status_code == 200
    assert [item["modelAlias"] for item in response.json()["data"]] == ["dream-balanced", "image-only"]
    assert response.json()["data"][1]["callable"] is False
    assert response.json()["defaultModelAlias"] == "dream-balanced"
    assert "ownedBy" not in response.text
