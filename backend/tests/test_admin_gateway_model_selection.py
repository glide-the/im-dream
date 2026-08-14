# [Input] Admin Gateway catalog responses and saved Dream system config.
# [Output] Verify server-owned explicit/default model selection and stale-state denial.
# [Pos] Admin Gateway model-selection contract test in backend/tests
# [Sync] 2026-08-14: prove users without a saved alias use Admin's callable default.

from __future__ import annotations

import pytest

from backend.services.admin_gateway.inference import GatewayInferenceError
from backend.services.admin_gateway.models import GatewayModel, GatewayModelCatalog
from backend.services.admin_gateway.selection import resolve_platform_model_alias


def _model(alias: str, *, callable: bool = True) -> GatewayModel:
    return GatewayModel(
        model_alias=alias,
        display_name=alias,
        protocol="anthropic",
        capabilities={"tools": True},
        context_window=200_000,
        max_output_tokens=8_192,
        enabled=True,
        callable=callable,
        availability="included" if callable else "maintenance",
        required_plan_code="free" if callable else None,
        upgrade_hint=None,
    )


class _CatalogClient:
    def __init__(self, catalog: GatewayModelCatalog) -> None:
        self.catalog = catalog

    def fetch_catalog(self) -> GatewayModelCatalog:
        return self.catalog


def test_saved_callable_alias_is_the_server_selected_model() -> None:
    result = resolve_platform_model_alias(
        7,
        None,
        catalog_client_factory=lambda _user_id: _CatalogClient(
            GatewayModelCatalog((_model("dream-balanced"),), "dream-balanced")
        ),
        system_config_reader=lambda _user_id: {"model": "dream-balanced"},
    )
    assert result == "dream-balanced"


def test_no_saved_alias_uses_admin_callable_default() -> None:
    result = resolve_platform_model_alias(
        7,
        None,
        catalog_client_factory=lambda _user_id: _CatalogClient(
            GatewayModelCatalog((_model("dream-balanced"),), "dream-balanced")
        ),
        system_config_reader=lambda _user_id: {},
    )
    assert result == "dream-balanced"


def test_client_alias_cannot_override_server_preference() -> None:
    with pytest.raises(GatewayInferenceError) as captured:
        resolve_platform_model_alias(
            7,
            "dream-fast",
            catalog_client_factory=lambda _user_id: _CatalogClient(
                GatewayModelCatalog(
                    (_model("dream-balanced"), _model("dream-fast")),
                    "dream-balanced",
                )
            ),
            system_config_reader=lambda _user_id: {"model": "dream-balanced"},
        )
    assert captured.value.status_code == 409
    assert captured.value.code == "GATEWAY_MODEL_SELECTION_CONFLICT"


def test_stale_saved_alias_fails_closed_instead_of_silently_switching_default() -> None:
    with pytest.raises(GatewayInferenceError) as captured:
        resolve_platform_model_alias(
            7,
            None,
            catalog_client_factory=lambda _user_id: _CatalogClient(
                GatewayModelCatalog(
                    (
                        _model("dream-balanced"),
                        _model("dream-retired", callable=False),
                    ),
                    "dream-balanced",
                )
            ),
            system_config_reader=lambda _user_id: {"model": "dream-retired"},
        )
    assert captured.value.status_code == 409
    assert captured.value.code == "GATEWAY_MODEL_SELECTION_STALE"


def test_no_saved_alias_and_no_callable_default_is_forbidden() -> None:
    with pytest.raises(GatewayInferenceError) as captured:
        resolve_platform_model_alias(
            7,
            None,
            catalog_client_factory=lambda _user_id: _CatalogClient(
                GatewayModelCatalog((_model("dream-maintenance", callable=False),), None)
            ),
            system_config_reader=lambda _user_id: {},
        )
    assert captured.value.status_code == 403
    assert captured.value.code == "GATEWAY_MODEL_NOT_AVAILABLE"
