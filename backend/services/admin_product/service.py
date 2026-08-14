"""Subject-binding application service for the Dream Product API BFF."""

from __future__ import annotations

import re
from typing import Any, Protocol

from .client import AdminProductGateway
from .errors import ProductBffError, dependency_unavailable, invalid_product_response
from .identity import CanonicalUserLookup
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
        canonical_users: CanonicalUserLookup,
        admin_product: AdminProductGateway,
    ) -> None:
        self._canonical_users = canonical_users
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
        try:
            identity = await self._canonical_users.find_active(session_subject)
        except ProductBffError:
            raise
        except Exception:
            raise dependency_unavailable() from None
        if identity is None or identity.canonical_user_id != session_subject:
            raise ProductBffError(
                code="CANONICAL_USER_REQUIRED",
                message="The Dream session is not bound to an active canonical user.",
                status_code=403,
            )
        return identity.canonical_user_id

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
