"""Lazy runtime composition for PostgreSQL identity and Admin Product HTTP."""

from __future__ import annotations

import asyncio
from typing import Any

try:
    from persistence.postgres import PostgresPool
except ModuleNotFoundError:  # pragma: no cover - package import compatibility
    from backend.persistence.postgres import PostgresPool

from .client import AdminProductClient
from .config import AdminProductConfig
from .errors import ProductBffError, configuration_unavailable
from .identity import PostgresCanonicalUserRepository
from .models import (
    ExecuteSubscriptionCommand,
    PaymentIntentCreate,
    PlansQuery,
    PreviewSubscriptionCommand,
    UsageQuery,
)
from .service import ProductBff, ProductBffService


class LazyProductBffService:
    """Build runtime dependencies on first use, never during module import."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._delegate_service: ProductBffService | None = None
        self._pool: PostgresPool | None = None
        self._client: AdminProductClient | None = None

    async def _delegate(self) -> ProductBffService:
        if self._delegate_service is not None:
            return self._delegate_service
        async with self._lock:
            if self._delegate_service is not None:
                return self._delegate_service
            pool: PostgresPool | None = None
            client: AdminProductClient | None = None
            try:
                configuration = AdminProductConfig.from_env()
                pool = PostgresPool.from_env(application_name="ink-dream-product-bff")
                await asyncio.to_thread(pool.open)
                client = AdminProductClient(configuration)
                service = ProductBffService(
                    canonical_users=PostgresCanonicalUserRepository(pool),
                    admin_product=client,
                )
            except ProductBffError:
                if pool is not None:
                    try:
                        await asyncio.to_thread(pool.close)
                    except Exception:
                        pass
                if client is not None:
                    await client.aclose()
                raise
            except Exception:
                if pool is not None:
                    try:
                        await asyncio.to_thread(pool.close)
                    except Exception:
                        pass
                if client is not None:
                    await client.aclose()
                raise configuration_unavailable() from None
            self._pool = pool
            self._client = client
            self._delegate_service = service
            return service

    async def plans(
        self, session_subject: str, query: PlansQuery, request_id: str
    ) -> dict[str, Any]:
        return await (await self._delegate()).plans(
            session_subject, query, request_id
        )

    async def subscription_context(
        self, session_subject: str, request_id: str
    ) -> dict[str, Any]:
        return await (await self._delegate()).subscription_context(
            session_subject, request_id
        )

    async def usage(
        self, session_subject: str, query: UsageQuery, request_id: str
    ) -> dict[str, Any]:
        return await (await self._delegate()).usage(
            session_subject, query, request_id
        )

    async def model_catalog(
        self, session_subject: str, request_id: str
    ) -> dict[str, Any]:
        return await (await self._delegate()).model_catalog(
            session_subject, request_id
        )

    async def subscription_command(
        self,
        session_subject: str,
        command: PreviewSubscriptionCommand | ExecuteSubscriptionCommand,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        return await (await self._delegate()).subscription_command(
            session_subject, command, request_id, idempotency_key
        )

    async def create_payment_intent(
        self,
        session_subject: str,
        payment: PaymentIntentCreate,
        request_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        return await (await self._delegate()).create_payment_intent(
            session_subject, payment, request_id, idempotency_key
        )

    async def payment_intent(
        self, session_subject: str, payment_intent_id: str, request_id: str
    ) -> dict[str, Any]:
        return await (await self._delegate()).payment_intent(
            session_subject, payment_intent_id, request_id
        )

    async def aclose(self) -> None:
        async with self._lock:
            client, pool = self._client, self._pool
            self._client = None
            self._pool = None
            self._delegate_service = None
        if client is not None:
            await client.aclose()
        if pool is not None:
            try:
                await asyncio.to_thread(pool.close)
            except Exception:
                pass


_default_service = LazyProductBffService()


def get_default_product_bff_service() -> ProductBff:
    return _default_service


async def close_default_product_bff_service() -> None:
    await _default_service.aclose()
