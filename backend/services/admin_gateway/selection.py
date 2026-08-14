"""Server-owned platform model selection for every Claude Agent turn."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Protocol

try:
    import database
except ModuleNotFoundError:  # Support package imports from repository root.
    from backend import database

from .inference import GatewayInferenceError
from .models import GatewayModelCatalog, GatewayModelCatalogClient


class CatalogClient(Protocol):
    def fetch_catalog(self) -> GatewayModelCatalog: ...


CatalogClientFactory = Callable[[int | str], CatalogClient]
SystemConfigReader = Callable[[int | str], Mapping[str, Any]]


def resolve_platform_model_alias(
    canonical_user_id: int | str,
    client_model_alias: str | None = None,
    *,
    catalog_client_factory: CatalogClientFactory = GatewayModelCatalogClient,
    system_config_reader: SystemConfigReader = database.get_system_config,
) -> str:
    """Return the current callable alias without trusting browser state.

    The live Admin catalog owns callability. Dream owns only the saved alias
    preference. A client alias may confirm the server selection but can never
    override it.
    """

    catalog = catalog_client_factory(canonical_user_id).fetch_catalog()
    callable_aliases = {
        model.model_alias for model in catalog.models if model.callable
    }
    config = system_config_reader(canonical_user_id)
    saved = str(config.get("model") or "").strip()
    if saved and saved not in callable_aliases:
        raise GatewayInferenceError("GATEWAY_MODEL_SELECTION_STALE", 409)
    selected = saved or catalog.default_model_alias or ""
    if not selected:
        raise GatewayInferenceError("GATEWAY_MODEL_NOT_AVAILABLE", 403)
    if client_model_alias and client_model_alias != selected:
        raise GatewayInferenceError("GATEWAY_MODEL_SELECTION_CONFLICT", 409)
    return selected
