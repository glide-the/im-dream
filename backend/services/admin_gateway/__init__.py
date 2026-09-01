"""Server-only Admin Gateway integration for canonical Dream users.

[Input] Focused Gateway SDK, error, model-catalog, and model-selection modules.
[Output] Stable public imports for authenticated model resolution and Runtime metadata.
[Pos] Package facade; it owns no database schema or browser DTO.
[Sync] 2026-08-28: export full GatewayModel selection for server-owned Runtime projection.
[Sync] 2026-08-31: keep shared Gateway errors independent from the retired
                   non-Claude inference adapter, which has now been deleted.
"""

from .sdk import apply_gateway_sdk_env_to_options, gateway_enabled
from .errors import GatewayInferenceError
from .models import GatewayModel, GatewayModelCatalog, GatewayModelCatalogClient
from .selection import resolve_platform_model, resolve_platform_model_alias

__all__ = [
    "apply_gateway_sdk_env_to_options",
    "gateway_enabled",
    "GatewayInferenceError",
    "GatewayModel",
    "GatewayModelCatalog",
    "GatewayModelCatalogClient",
    "resolve_platform_model",
    "resolve_platform_model_alias",
]
