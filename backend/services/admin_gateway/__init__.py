"""Server-only Admin Gateway integration for canonical Dream users."""

from .sdk import apply_gateway_sdk_env_to_options, gateway_enabled
from .inference import (
    GatewayInferenceClient,
    GatewayInferenceError,
    GatewayInferenceModels,
    GatewayPolyAgent,
)
from .models import GatewayModel, GatewayModelCatalogClient

__all__ = [
    "apply_gateway_sdk_env_to_options",
    "gateway_enabled",
    "GatewayInferenceClient",
    "GatewayInferenceError",
    "GatewayInferenceModels",
    "GatewayPolyAgent",
    "GatewayModel",
    "GatewayModelCatalogClient",
]
