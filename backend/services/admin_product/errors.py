"""Public, redacted errors for the Dream Product API BFF."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProductBffError(Exception):
    """A safe error that can cross the Dream browser boundary.

    The exception deliberately never stores an upstream URL, bearer token, or
    raw dependency exception.  Callers may therefore render it without
    accidentally serialising credentials from an ``httpx`` error.
    """

    code: str
    message: str
    status_code: int
    details: dict[str, Any] | None = None
    retry_after_seconds: int | None = None

    def __str__(self) -> str:
        return f"{self.code} ({self.status_code})"


def configuration_unavailable() -> ProductBffError:
    return ProductBffError(
        code="PRODUCT_DEPENDENCY_UNAVAILABLE",
        message="The subscription service is not safely configured.",
        status_code=503,
    )


def dependency_unavailable() -> ProductBffError:
    return ProductBffError(
        code="PRODUCT_DEPENDENCY_UNAVAILABLE",
        message="The subscription service is temporarily unavailable.",
        status_code=503,
    )


def invalid_product_response() -> ProductBffError:
    return ProductBffError(
        code="PRODUCT_DEPENDENCY_UNAVAILABLE",
        message="The subscription service returned an invalid response.",
        status_code=503,
    )


def invalid_input(*, field: str | None = None) -> ProductBffError:
    details = {"field": field} if field else None
    return ProductBffError(
        code="PRODUCT_INPUT_INVALID",
        message="The request input is invalid.",
        status_code=400,
        details=details,
    )

