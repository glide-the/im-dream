"""Canonical-user lookup boundary backed only by PostgreSQL."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol

try:
    from persistence.postgres import ConnectionPool
    from persistence.unit_of_work import PostgresUnitOfWork
except ModuleNotFoundError:  # pragma: no cover - package import compatibility
    from backend.persistence.postgres import ConnectionPool
    from backend.persistence.unit_of_work import PostgresUnitOfWork


@dataclass(frozen=True)
class CanonicalUserIdentity:
    canonical_user_id: str


class CanonicalUserLookup(Protocol):
    async def find_active(
        self, canonical_user_id: str
    ) -> CanonicalUserIdentity | None: ...


UnitOfWorkFactory = Callable[[], PostgresUnitOfWork]


class PostgresCanonicalUserRepository:
    """Resolve the session subject against canonical ``users``.

    This repository intentionally has no import of ``database`` and no SQLite
    fallback.  A missing pool, table, status column, or row therefore fails
    closed at the BFF service boundary.
    """

    def __init__(
        self,
        pool: ConnectionPool | None = None,
        *,
        unit_of_work_factory: UnitOfWorkFactory | None = None,
    ) -> None:
        if (pool is None) == (unit_of_work_factory is None):
            raise ValueError("exactly one PostgreSQL dependency is required")
        self._unit_of_work_factory = unit_of_work_factory or (
            lambda: PostgresUnitOfWork(pool, read_only=True)  # type: ignore[arg-type]
        )

    async def find_active(
        self, canonical_user_id: str
    ) -> CanonicalUserIdentity | None:
        return await asyncio.to_thread(self._find_active_sync, canonical_user_id)

    def _find_active_sync(
        self, canonical_user_id: str
    ) -> CanonicalUserIdentity | None:
        with self._unit_of_work_factory() as unit_of_work:
            cursor = unit_of_work.execute(
                """
                SELECT id::text AS canonical_user_id
                FROM users
                WHERE id = %s::bigint
                  AND status = 'active'
                LIMIT 1
                """,
                (canonical_user_id,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        value: Any
        if isinstance(row, Mapping):
            value = row.get("canonical_user_id")
        else:
            try:
                value = row[0]
            except (IndexError, KeyError, TypeError):
                return None
        if not isinstance(value, (str, int)):
            return None
        resolved = str(value)
        if resolved != canonical_user_id:
            return None
        return CanonicalUserIdentity(canonical_user_id=resolved)

