"""Server-only Admin Gateway integration for canonical Dream users."""

from .sdk import apply_gateway_sdk_env_to_options, gateway_enabled

__all__ = ["apply_gateway_sdk_env_to_options", "gateway_enabled"]
