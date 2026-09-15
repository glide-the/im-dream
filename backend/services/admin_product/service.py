"""Subject-binding application service for the Dream Product API BFF.

[Input] Canonical subject already verified by the shared Admin OAuth dependency and strict Product DTOs.
[Output] Subject-bound calls to the authoritative Admin Product API.
[Pos] Dream orchestration boundary; Admin revalidates active identity and owns all Product persistence.
[Sync] 2026-09-16: remove the redundant Dream PostgreSQL identity lookup.
"""

from __future__ import annotations

import re
from typing import Any, Protocol

from .client import AdminProductGateway
from .errors import ProductBffError, invalid_product_response
from .models import (
    ExecuteSubscriptionCommand,
    PaymentIntentCreate,
    PlansQuery,
    PreviewSubscriptionCommand,
    UsageQuery,
)


_SUBJECT_PATTERN = re.compile(r"^[1-9]\d{0,18}$")
_POSTGRES_BIGINT_MAXIMUM = 9_223_372_036_854_775_807


class ProductBff(Protocol):
    async def plans(
        self, session_subject: str, query: PlansQuery, request_id: str
    ) -> dict[str, Any]: ...

    async def subscription_context(
        self, session_subject: str, request_id: str
    ) -> dict[str, Any]: ...

    async def usage(
        self, session_subject: str, query: UsageQuery, request_id: str
    ) -> dict[str, Any]: ...

    async def model_catalog(
        self, session_subject: str, request_id: str
    ) -> dict[str, Any]: ...

    async def subscription_command(
        self,
        session_subject: str,
        command: PreviewSubscriptionCommand | ExecuteSubscriptionCommand,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]: ...

    async def create_payment_intent(
        self,
        session_subject: str,
        payment: PaymentIntentCreate,
        request_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]: ...

    async def payment_intent(
        self, session_subject: str, payment_intent_id: str, request_id: str
    ) -> dict[str, Any]: ...


class ProductBffService:
    def __init__(
        self,
        *,
        admin_product: AdminProductGateway,
    ) -> None:
        self._admin_product = admin_product

    async def _canonical_subject(self, session_subject: str) -> str:
        if (
            not _SUBJECT_PATTERN.fullmatch(session_subject)
            or int(session_subject) > _POSTGRES_BIGINT_MAXIMUM
        ):
            raise ProductBffError(
                code="PRODUCT_AUTH_REQUIRED",
                message="A valid Dream session is required.",
                status_code=401,
            )
        # The public route obtains this value only from the shared Admin OAuth
        # principal. The Admin Product endpoint verifies the signed subject
        # against active canonical/platform identity again before data access.
        return session_subject

    async def plans(
        self, session_subject: str, query: PlansQuery, request_id: str
    ) -> dict[str, Any]:
        subject = await self._canonical_subject(session_subject)
        return await self._admin_product.plans(subject, query, request_id)

    async def subscription_context(
        self, session_subject: str, request_id: str
    ) -> dict[str, Any]:
        subject = await self._canonical_subject(session_subject)
        result = await self._admin_product.subscription_context(subject, request_id)
        try:
            returned_subject = result["data"]["canonicalUser"]["id"]
        except (KeyError, TypeError):
            raise invalid_product_response() from None
        if returned_subject != subject:
            raise invalid_product_response()
        return result

    async def usage(
        self, session_subject: str, query: UsageQuery, request_id: str
    ) -> dict[str, Any]:
        subject = await self._canonical_subject(session_subject)
        return await self._admin_product.usage(subject, query, request_id)

    async def model_catalog(
        self, session_subject: str, request_id: str
    ) -> dict[str, Any]:
        subject = await self._canonical_subject(session_subject)
        return await self._admin_product.model_catalog(subject, request_id)

    async def subscription_command(
        self,
        session_subject: str,
        command: PreviewSubscriptionCommand | ExecuteSubscriptionCommand,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        subject = await self._canonical_subject(session_subject)
        return await self._admin_product.subscription_command(
            subject, command, request_id, idempotency_key
        )

    async def create_payment_intent(
        self,
        session_subject: str,
        payment: PaymentIntentCreate,
        request_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        subject = await self._canonical_subject(session_subject)
        return await self._admin_product.create_payment_intent(
            subject, payment, request_id, idempotency_key
        )

    async def payment_intent(
        self, session_subject: str, payment_intent_id: str, request_id: str
    ) -> dict[str, Any]:
        subject = await self._canonical_subject(session_subject)
        return await self._admin_product.payment_intent(
            subject, payment_intent_id, request_id
        )
