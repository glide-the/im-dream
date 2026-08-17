"""Explicit transaction boundary for PostgreSQL repositories."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Protocol, TypeVar, runtime_checkable

from .errors import (
    PersistenceError,
    UnitOfWorkStateError,
    is_postgres_error,
    map_postgres_error,
)
from .postgres import ConnectionPool


@runtime_checkable
class UnitOfWork(Protocol):
    """Application-facing transaction contract."""

    @property
    def connection(self) -> Any: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


RepositoryT = TypeVar("RepositoryT")
RepositoryFactory = Callable[[Any], RepositoryT]

_ISOLATION_LEVELS = {
    "read_committed": "READ COMMITTED",
    "repeatable_read": "REPEATABLE READ",
    "serializable": "SERIALIZABLE",
}


class PostgresUnitOfWork:
    """One acquired connection and one explicitly completed transaction.

    A successful context exit does *not* imply commit.  Call ``commit()`` after
    all repository operations succeed; otherwise exit rolls the transaction
    back.  This prevents an innocent early return from publishing a partial
    Dream aggregate update.
    """

    def __init__(
        self,
        pool: ConnectionPool,
        *,
        isolation_level: str | None = None,
        read_only: bool = False,
        connection_timeout: float | None = None,
        repository_factories: Mapping[str, RepositoryFactory[Any]] | None = None,
    ) -> None:
        normalized_isolation = (
            isolation_level.casefold().replace("-", "_").replace(" ", "_")
            if isolation_level is not None
            else None
        )
        if (
            normalized_isolation is not None
            and normalized_isolation not in _ISOLATION_LEVELS
        ):
            raise UnitOfWorkStateError()
        if connection_timeout is not None and connection_timeout <= 0:
            raise UnitOfWorkStateError()

        self._pool = pool
        self._isolation_level = normalized_isolation
        self._read_only = read_only
        self._connection_timeout = connection_timeout
        self._repository_factories = dict(repository_factories or {})
        self._repositories: dict[str, Any] = {}
        self._connection_manager: Any = None
        self._connection: Any = None
        self._active = False
        self._completed = False
        self._committed = False

    @property
    def active(self) -> bool:
        return self._active

    @property
    def completed(self) -> bool:
        return self._completed

    @property
    def committed(self) -> bool:
        return self._committed

    @property
    def connection(self) -> Any:
        if not self._active or self._connection is None:
            raise UnitOfWorkStateError()
        return self._connection

    @property
    def repositories(self) -> Mapping[str, Any]:
        if not self._active:
            raise UnitOfWorkStateError()
        return self._repositories

    def repository(self, name: str) -> Any:
        """Create a transaction-bound repository on first use."""

        if not self._active:
            raise UnitOfWorkStateError()
        if name in self._repositories:
            return self._repositories[name]
        try:
            factory = self._repository_factories[name]
        except KeyError:
            raise UnitOfWorkStateError() from None
        repository = factory(self.connection)
        self._repositories[name] = repository
        return repository

    def __enter__(self) -> "PostgresUnitOfWork":
        if self._active or self._completed:
            raise UnitOfWorkStateError()
        try:
            self._connection_manager = (
                self._pool.connection()
                if self._connection_timeout is None
                else self._pool.connection(timeout=self._connection_timeout)
            )
            self._connection = self._connection_manager.__enter__()
            self._active = True
            self._configure_transaction()
        except BaseException as exc:
            self._release_after_failed_enter(exc)
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            raise map_postgres_error(exc) from None
        return self

    def _configure_transaction(self) -> None:
        clauses: list[str] = []
        if self._isolation_level is not None:
            clauses.append(f"ISOLATION LEVEL {_ISOLATION_LEVELS[self._isolation_level]}")
        if self._read_only:
            clauses.append("READ ONLY")
        if clauses:
            # Every token comes from the closed constants above; caller input is
            # never interpolated into SQL.
            self.connection.execute("SET TRANSACTION " + " ".join(clauses))

    def _release_after_failed_enter(self, exc: BaseException) -> None:
        manager = self._connection_manager
        if manager is not None and self._connection is not None:
            try:
                self._connection.rollback()
            except BaseException:
                pass
            try:
                manager.__exit__(type(exc), exc, exc.__traceback__)
            except BaseException:
                pass
        self._connection = None
        self._connection_manager = None
        self._active = False
        self._completed = True

    def execute(self, query: Any, parameters: Any = None) -> Any:
        """Execute through the active connection with redacted error mapping."""

        if self._completed:
            raise UnitOfWorkStateError()
        try:
            if parameters is None:
                return self.connection.execute(query)
            return self.connection.execute(query, parameters)
        except BaseException as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            raise map_postgres_error(exc) from None

    def commit(self) -> None:
        if not self._active or self._completed:
            raise UnitOfWorkStateError()
        try:
            self.connection.commit()
        except BaseException as exc:
            try:
                self.connection.rollback()
            except BaseException:
                pass
            self._completed = True
            self._committed = False
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            raise map_postgres_error(exc) from None
        self._completed = True
        self._committed = True

    def rollback(self) -> None:
        if not self._active or self._completed:
            raise UnitOfWorkStateError()
        try:
            self.connection.rollback()
        except BaseException as exc:
            self._completed = True
            self._committed = False
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            raise map_postgres_error(exc) from None
        self._completed = True
        self._committed = False

    def __exit__(self, exc_type, exc, traceback) -> bool:
        if not self._active or self._connection_manager is None:
            raise UnitOfWorkStateError()

        pending_error: BaseException | None = None
        if not self._completed:
            try:
                self.connection.rollback()
            except BaseException as rollback_error:
                if isinstance(rollback_error, (KeyboardInterrupt, SystemExit)):
                    pending_error = rollback_error
                elif exc is None:
                    pending_error = map_postgres_error(rollback_error)
            self._completed = True
            self._committed = False

        manager = self._connection_manager
        try:
            manager.__exit__(exc_type, exc, traceback)
        except BaseException as release_error:
            if isinstance(release_error, (KeyboardInterrupt, SystemExit)):
                pending_error = release_error
            elif exc is None and pending_error is None:
                pending_error = map_postgres_error(release_error)
        finally:
            self._repositories.clear()
            self._connection = None
            self._connection_manager = None
            self._active = False

        if pending_error is not None:
            raise pending_error from None
        if exc is not None and is_postgres_error(exc):
            raise map_postgres_error(exc) from None
        return False


__all__ = [
    "PostgresUnitOfWork",
    "RepositoryFactory",
    "UnitOfWork",
]
