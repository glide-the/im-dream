"""Lazy runtime composition for the Admin Product HTTP boundary."""

# [Input] Server-owned Admin Product configuration and HTTP client.
# [Output] One lazy Product BFF service with no Dream database dependency.
# [Pos] Production Product composition; Admin validates canonical identity and owns persistence.
# [Sync] 2026-09-16: compose OAuth-forwarding Product service without Dream signing or PostgreSQL.

from __future__ import annotations

import asyncio
from typing import Any

from .client import AdminProductClient
from .config import AdminProductConfig
from .errors import ProductBffError, configuration_unavailable
from .models import (
    ExecuteSubscriptionCommand,
    PaymentIntentCreate,
    PlansQuery,
    PreviewSubscriptionCommand,
    UsageQuery,
)
from .service import ProductBff, ProductBffService, ProductSessionActor


class LazyProductBffService:
    """Build runtime dependencies on first use, never during module import."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._delegate_service: ProductBffService | None = None
        self._client: AdminProductClient | None = None

    async def _delegate(self) -> ProductBffService:
        if self._delegate_service is not None:
            return self._delegate_service
        async with self._lock:
            if self._delegate_service is not None:
                return self._delegate_service
            client: AdminProductClient | None = None
            try:
                configuration = AdminProductConfig.from_env()
                client = AdminProductClient(configuration)
                service = ProductBffService(admin_product=client)
            except ProductBffError:
                if client is not None:
                    await client.aclose()
                raise
            except Exception:
                if client is not None:
                    await client.aclose()
                raise configuration_unavailable() from None
            self._client = client
            self._delegate_service = service
            return service

    async def plans(
        self, actor: ProductSessionActor, query: PlansQuery, request_id: str
    ) -> dict[str, Any]:
        return await (await self._delegate()).plans(
            actor, query, request_id
        )

    async def subscription_context(
        self, actor: ProductSessionActor, request_id: str
    ) -> dict[str, Any]:
        return await (await self._delegate()).subscription_context(
            actor, request_id
        )

    async def usage(
        self, actor: ProductSessionActor, query: UsageQuery, request_id: str
    ) -> dict[str, Any]:
        return await (await self._delegate()).usage(
            actor, query, request_id
        )

    async def model_catalog(
        self, actor: ProductSessionActor, request_id: str
    ) -> dict[str, Any]:
        return await (await self._delegate()).model_catalog(
            actor, request_id
        )

    async def subscription_command(
        self,
        actor: ProductSessionActor,
        command: PreviewSubscriptionCommand | ExecuteSubscriptionCommand,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        return await (await self._delegate()).subscription_command(
            actor, command, request_id, idempotency_key
        )

    async def create_payment_intent(
        self,
        actor: ProductSessionActor,
        payment: PaymentIntentCreate,
        request_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        return await (await self._delegate()).create_payment_intent(
            actor, payment, request_id, idempotency_key
        )

    async def payment_intent(
        self, actor: ProductSessionActor, payment_intent_id: str, request_id: str
    ) -> dict[str, Any]:
        return await (await self._delegate()).payment_intent(
            actor, payment_intent_id, request_id
        )

    async def aclose(self) -> None:
        async with self._lock:
            client = self._client
            self._client = None
            self._delegate_service = None
        if client is not None:
            await client.aclose()


_default_service = LazyProductBffService()


def get_default_product_bff_service() -> ProductBff:
    return _default_service


async def close_default_product_bff_service() -> None:
    await _default_service.aclose()
