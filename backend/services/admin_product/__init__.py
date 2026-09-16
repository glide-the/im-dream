"""Dream server-only integration with the Token-only Admin Product API.

[Sync] 2026-09-16: forward Admin OAuth actor DTOs and retire Dream Product token signing.
"""

from .client import AdminProductClient, AdminProductGateway
from .errors import ProductBffError
from .runtime import (
    close_default_product_bff_service,
    get_default_product_bff_service,
)
from .service import ProductBff, ProductBffService, ProductSessionActor

__all__ = [
    "AdminProductClient",
    "AdminProductGateway",
    "ProductBff",
    "ProductBffError",
    "ProductBffService",
    "ProductSessionActor",
    "close_default_product_bff_service",
    "get_default_product_bff_service",
]
