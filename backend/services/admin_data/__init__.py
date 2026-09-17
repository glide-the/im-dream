# [Input] Unified server-owned Admin configuration and OAuth verifier.
# [Output] Stable authentication/data-consumer imports without PostgreSQL dependencies.
# [Pos] Admin consumer package; domain adapters will expose only published operations.
# [Sync] 2026-09-14: establish a single reusable Admin boundary, pending domain/BFF DTO gates.
"""Admin authentication/data consumers; availability is not inferred from source."""

from .config import AdminDataConfig
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError
from .jwt_verifier import AdminJWTVerifier, OAuthPrincipalClaims

__all__ = ["AdminDataClient", "AdminDataConfig", "AdminDataError", "AdminJWTVerifier", "DomainOperation", "OAuthPrincipalClaims"]
