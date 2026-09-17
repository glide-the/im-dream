"""Actor-binding application service for the Dream Product API BFF.

[Input] Immutable Admin OAuth actor and strict Product DTOs.
[Output] Scope-checked calls using the same bearer plus canonical response binding.
[Pos] Dream orchestration boundary; Admin revalidates active identity and owns all Product persistence.
[Sync] 2026-09-16: retire Dream Product signing and forward the verified OAuth actor.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
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


@dataclass(frozen=True, slots=True)
class ProductSessionActor:
    """Verified Admin OAuth actor; its bearer never enters Product DTO bodies."""

    canonical_user_id: str
    scopes: frozenset[str]
    access_token: str = field(repr=False)


class ProductBff(Protocol):
    async def plans(
        self, actor: ProductSessionActor, query: PlansQuery, request_id: str
    ) -> dict[str, Any]: ...

    async def subscription_context(
        self, actor: ProductSessionActor, request_id: str
    ) -> dict[str, Any]: ...

    async def usage(
        self, actor: ProductSessionActor, query: UsageQuery, request_id: str
    ) -> dict[str, Any]: ...

    async def model_catalog(
        self, actor: ProductSessionActor, request_id: str
    ) -> dict[str, Any]: ...

    async def subscription_command(
        self,
        actor: ProductSessionActor,
        command: PreviewSubscriptionCommand | ExecuteSubscriptionCommand,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]: ...

    async def create_payment_intent(
        self,
        actor: ProductSessionActor,
        payment: PaymentIntentCreate,
        request_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]: ...

    async def payment_intent(
        self, actor: ProductSessionActor, payment_intent_id: str, request_id: str
    ) -> dict[str, Any]: ...


class ProductBffService:
    def __init__(
        self,
        *,
        admin_product: AdminProductGateway,
    ) -> None:
        self._admin_product = admin_product

    async def _canonical_actor(
        self, actor: ProductSessionActor, required_scope: str
    ) -> ProductSessionActor:
        if (
            not isinstance(actor, ProductSessionActor)
            or not _SUBJECT_PATTERN.fullmatch(actor.canonical_user_id)
            or int(actor.canonical_user_id) > _POSTGRES_BIGINT_MAXIMUM
            or required_scope not in actor.scopes
            or not actor.access_token
        ):
            raise ProductBffError(
                code="PRODUCT_AUTH_REQUIRED",
                message="A valid Dream session is required.",
                status_code=401,
            )
        return actor

    async def plans(
        self, actor: ProductSessionActor, query: PlansQuery, request_id: str
    ) -> dict[str, Any]:
        actor = await self._canonical_actor(actor, "product:read")
        return await self._admin_product.plans(actor.access_token, query, request_id)

    async def subscription_context(
        self, actor: ProductSessionActor, request_id: str
    ) -> dict[str, Any]:
        actor = await self._canonical_actor(actor, "product:read")
        result = await self._admin_product.subscription_context(actor.access_token, request_id)
        try:
            returned_subject = result["data"]["canonicalUser"]["id"]
        except (KeyError, TypeError):
            raise invalid_product_response() from None
        if returned_subject != actor.canonical_user_id:
            raise invalid_product_response()
        return result

    async def usage(
        self, actor: ProductSessionActor, query: UsageQuery, request_id: str
    ) -> dict[str, Any]:
        actor = await self._canonical_actor(actor, "product:read")
        return await self._admin_product.usage(actor.access_token, query, request_id)

    async def model_catalog(
        self, actor: ProductSessionActor, request_id: str
    ) -> dict[str, Any]:
        actor = await self._canonical_actor(actor, "product:read")
        return await self._admin_product.model_catalog(actor.access_token, request_id)

    async def subscription_command(
        self,
        actor: ProductSessionActor,
        command: PreviewSubscriptionCommand | ExecuteSubscriptionCommand,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        actor = await self._canonical_actor(actor, "product:write")
        return await self._admin_product.subscription_command(
            actor.access_token, command, request_id, idempotency_key
        )

    async def create_payment_intent(
        self,
        actor: ProductSessionActor,
        payment: PaymentIntentCreate,
        request_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        actor = await self._canonical_actor(actor, "product:write")
        return await self._admin_product.create_payment_intent(
            actor.access_token, payment, request_id, idempotency_key
        )

    async def payment_intent(
        self, actor: ProductSessionActor, payment_intent_id: str, request_id: str
    ) -> dict[str, Any]:
        actor = await self._canonical_actor(actor, "product:read")
        return await self._admin_product.payment_intent(
            actor.access_token, payment_intent_id, request_id
        )
