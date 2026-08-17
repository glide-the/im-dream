"""Dream server-only integration with the Token-only Admin Product API."""

from .client import AdminProductClient, AdminProductGateway
from .errors import ProductBffError
from .identity import (
    CanonicalUserIdentity,
    CanonicalUserLookup,
    PostgresCanonicalUserRepository,
)
from .runtime import (
    close_default_product_bff_service,
    get_default_product_bff_service,
)
from .service import ProductBff, ProductBffService

__all__ = [
    "AdminProductClient",
    "AdminProductGateway",
    "CanonicalUserIdentity",
    "CanonicalUserLookup",
    "PostgresCanonicalUserRepository",
    "ProductBff",
    "ProductBffError",
    "ProductBffService",
    "close_default_product_bff_service",
    "get_default_product_bff_service",
]

