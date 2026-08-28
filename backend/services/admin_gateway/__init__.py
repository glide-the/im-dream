"""Server-only Admin Gateway integration for canonical Dream users.

[Input] Focused Gateway config/inference/model-selection modules.
[Output] Stable public imports for authenticated model resolution and Runtime metadata.
[Pos] Package facade; it owns no database schema or browser DTO.
[Sync] 2026-08-28: export full GatewayModel selection for server-owned Runtime projection.
"""

from .sdk import apply_gateway_sdk_env_to_options, gateway_enabled
from .inference import (
    GatewayInferenceClient,
    GatewayInferenceError,
    GatewayInferenceModels,
    GatewayPolyAgent,
)
from .models import GatewayModel, GatewayModelCatalog, GatewayModelCatalogClient
from .selection import resolve_platform_model, resolve_platform_model_alias

__all__ = [
    "apply_gateway_sdk_env_to_options",
    "gateway_enabled",
    "GatewayInferenceClient",
    "GatewayInferenceError",
    "GatewayInferenceModels",
    "GatewayPolyAgent",
    "GatewayModel",
    "GatewayModelCatalog",
    "GatewayModelCatalogClient",
    "resolve_platform_model",
    "resolve_platform_model_alias",
]
