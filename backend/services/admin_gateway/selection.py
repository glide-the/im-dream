# [Input] Consume the authenticated Admin catalog and Dream's saved model preference.
# [Output] Resolve the selected callable GatewayModel and compatibility alias projection.
# [Pos] Server-owned model selection boundary shared by public and internal Dream turns.
# [Sync] 2026-08-28: retain the selected model runtime metadata instead of dropping it to an alias.

"""Server-owned platform model selection for every Claude Agent turn."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Protocol

try:
    import database
except ModuleNotFoundError:  # Support package imports from repository root.
    from backend import database

from .errors import GatewayInferenceError
from .models import GatewayModel, GatewayModelCatalog, GatewayModelCatalogClient


class CatalogClient(Protocol):
    def fetch_catalog(self) -> GatewayModelCatalog: ...


CatalogClientFactory = Callable[[int | str], CatalogClient]
SystemConfigReader = Callable[[int | str], Mapping[str, Any]]


def resolve_platform_model(
    canonical_user_id: int | str,
    client_model_alias: str | None = None,
    *,
    catalog_client_factory: CatalogClientFactory = GatewayModelCatalogClient,
    system_config_reader: SystemConfigReader = database.get_system_config,
) -> GatewayModel:
    """Return the current callable model without trusting browser state.

    The live Admin catalog owns callability. Dream owns only the saved alias
    preference. A client alias may confirm the server selection but can never
    override it.
    """

    catalog = catalog_client_factory(canonical_user_id).fetch_catalog()
    callable_models = {
        model.model_alias: model for model in catalog.models if model.callable
    }
    config = system_config_reader(canonical_user_id)
    saved = str(config.get("model") or "").strip()
    if saved and saved not in callable_models:
        raise GatewayInferenceError("GATEWAY_MODEL_SELECTION_STALE", 409)
    selected = saved or catalog.default_model_alias or ""
    if not selected:
        raise GatewayInferenceError("GATEWAY_MODEL_NOT_AVAILABLE", 403)
    if client_model_alias and client_model_alias != selected:
        raise GatewayInferenceError("GATEWAY_MODEL_SELECTION_CONFLICT", 409)
    return callable_models[selected]


def resolve_platform_model_alias(
    canonical_user_id: int | str,
    client_model_alias: str | None = None,
    *,
    catalog_client_factory: CatalogClientFactory = GatewayModelCatalogClient,
    system_config_reader: SystemConfigReader = database.get_system_config,
) -> str:
    """Compatibility projection for callers that only need the selected alias."""

    return resolve_platform_model(
        canonical_user_id,
        client_model_alias,
        catalog_client_factory=catalog_client_factory,
        system_config_reader=system_config_reader,
    ).model_alias
