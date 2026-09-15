"""Dream server-only integration with the Token-only Admin Product API.

[Sync] 2026-09-16: remove the retired Dream PostgreSQL identity Repository.
"""

from .client import AdminProductClient, AdminProductGateway
from .errors import ProductBffError
from .runtime import (
    close_default_product_bff_service,
    get_default_product_bff_service,
)
from .service import ProductBff, ProductBffService

__all__ = [
    "AdminProductClient",
    "AdminProductGateway",
    "ProductBff",
    "ProductBffError",
    "ProductBffService",
    "close_default_product_bff_service",
    "get_default_product_bff_service",
]
