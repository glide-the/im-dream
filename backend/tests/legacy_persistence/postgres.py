"""Lifecycle-managed psycopg 3 connection pool.

``psycopg`` is loaded only when the default factory is used.  Tests and schema
tooling can therefore inject a fake pool without importing or contacting a
database driver.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
import os
from typing import Any, Protocol, runtime_checkable

from .config import DATABASE_URL_ENV, parse_postgres_target
from .errors import (
    PersistenceConfigurationError,
    PersistenceDependencyError,
    is_postgres_error,
    map_postgres_error,
)


@runtime_checkable
class ConnectionPool(Protocol):
    """Small pool surface consumed by repositories and units of work."""

    def connection(self, timeout: float | None = None): ...


PoolFactory = Callable[..., Any]


@dataclass(frozen=True, repr=False)
class PostgresPoolConfig:
    """Validated pool configuration; repr intentionally omits ``dsn``."""

    dsn: str = field(repr=False)
    min_size: int = 1
    max_size: int = 10
    timeout: float = 10.0
    max_lifetime: float = 3600.0
    max_idle: float = 600.0
    reconnect_timeout: float = 30.0
    application_name: str = "ink-dream-memory"

    def __post_init__(self) -> None:
        parse_postgres_target(self.dsn)
        if self.min_size < 0:
            raise PersistenceConfigurationError()
        if self.max_size < 1 or self.max_size < self.min_size:
            raise PersistenceConfigurationError()
        if any(
            value <= 0
            for value in (
                self.timeout,
                self.max_lifetime,
                self.max_idle,
                self.reconnect_timeout,
            )
        ):
            raise PersistenceConfigurationError()
        if not self.application_name or any(
            character in self.application_name for character in "\r\n\x00"
        ):
            raise PersistenceConfigurationError()

    def __repr__(self) -> str:
        return (
            "PostgresPoolConfig(dsn=<redacted>, "
            f"min_size={self.min_size}, max_size={self.max_size})"
        )

    @classmethod
    def from_env(
        cls,
        *,
        environ: Mapping[str, str] | None = None,
        url_variable: str = DATABASE_URL_ENV,
        **overrides: Any,
    ) -> "PostgresPoolConfig":
        values = os.environ if environ is None else environ
        dsn = values.get(url_variable)
        if not isinstance(dsn, str) or not dsn.strip():
            raise PersistenceConfigurationError()
        return cls(dsn=dsn, **overrides)


def _default_pool_factory(**kwargs: Any):
    try:
        from psycopg_pool import ConnectionPool as PsycopgConnectionPool
    except (ImportError, ModuleNotFoundError):
        raise PersistenceDependencyError() from None
    return PsycopgConnectionPool(**kwargs)


def _default_connection_kwargs(application_name: str) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        # Transaction completion belongs to PostgresUnitOfWork.
        "autocommit": False,
        "application_name": application_name,
    }
    try:
        from psycopg.rows import dict_row
    except (ImportError, ModuleNotFoundError):
        # A fake pool does not need psycopg installed.  Production installations
        # receive dict rows, which are what the catalog reader consumes.
        return kwargs
    kwargs["row_factory"] = dict_row
    return kwargs


class PostgresPool:
    """A safe wrapper around ``psycopg_pool.ConnectionPool``.

    Construction never opens network connections.  Startup must call ``open``
    explicitly, making readiness and shutdown order observable.
    """

    def __init__(
        self,
        dsn: str | PostgresPoolConfig,
        *,
        min_size: int = 1,
        max_size: int = 10,
        timeout: float = 10.0,
        max_lifetime: float = 3600.0,
        max_idle: float = 600.0,
        reconnect_timeout: float = 30.0,
        application_name: str = "ink-dream-memory",
        connection_kwargs: Mapping[str, Any] | None = None,
        pool_factory: PoolFactory | None = None,
        name: str = "ink-dream-memory-postgres",
    ) -> None:
        if isinstance(dsn, PostgresPoolConfig):
            config = dsn
        else:
            config = PostgresPoolConfig(
                dsn=dsn,
                min_size=min_size,
                max_size=max_size,
                timeout=timeout,
                max_lifetime=max_lifetime,
                max_idle=max_idle,
                reconnect_timeout=reconnect_timeout,
                application_name=application_name,
            )
        self._config = config
        self._opened = False
        self._closed = False

        connect_kwargs = _default_connection_kwargs(config.application_name)
        if connection_kwargs:
            connect_kwargs.update(connection_kwargs)
        # Explicit UoW completion is a boundary invariant, not a caller option.
        connect_kwargs["autocommit"] = False

        factory = pool_factory or _default_pool_factory
        try:
            self._pool = factory(
                conninfo=config.dsn,
                min_size=config.min_size,
                max_size=config.max_size,
                timeout=config.timeout,
                max_lifetime=config.max_lifetime,
                max_idle=config.max_idle,
                reconnect_timeout=config.reconnect_timeout,
                kwargs=connect_kwargs,
                name=name,
                open=False,
            )
        except PersistenceDependencyError:
            raise
        except BaseException as exc:
            # Pool constructors sometimes include conninfo in their errors.
            # Replace it with a fixed configuration error and suppress cause.
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            raise PersistenceConfigurationError() from None

    @classmethod
    def from_env(
        cls,
        *,
        environ: Mapping[str, str] | None = None,
        url_variable: str = DATABASE_URL_ENV,
        pool_factory: PoolFactory | None = None,
        **overrides: Any,
    ) -> "PostgresPool":
        config_keys = {
            "min_size",
            "max_size",
            "timeout",
            "max_lifetime",
            "max_idle",
            "reconnect_timeout",
            "application_name",
        }
        config_overrides = {
            key: value for key, value in overrides.items() if key in config_keys
        }
        pool_overrides = {
            key: value for key, value in overrides.items() if key not in config_keys
        }
        config = PostgresPoolConfig.from_env(
            environ=environ,
            url_variable=url_variable,
            **config_overrides,
        )
        return cls(config, pool_factory=pool_factory, **pool_overrides)

    @property
    def config(self) -> PostgresPoolConfig:
        return self._config

    @property
    def raw_pool(self) -> Any:
        """Expose the driver pool for lifecycle instrumentation only."""

        return self._pool

    @property
    def opened(self) -> bool:
        return self._opened and not self._closed

    @property
    def closed(self) -> bool:
        return self._closed

    def __repr__(self) -> str:
        state = "closed" if self._closed else "open" if self._opened else "new"
        return f"PostgresPool(state={state!r}, dsn=<redacted>)"

    def open(self, *, wait: bool = True, timeout: float | None = None) -> None:
        if self._closed:
            raise PersistenceConfigurationError()
        if self._opened:
            return
        effective_timeout = self._config.timeout if timeout is None else timeout
        if effective_timeout <= 0:
            raise PersistenceConfigurationError()
        try:
            self._pool.open(wait=wait, timeout=effective_timeout)
        except BaseException as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            raise map_postgres_error(exc) from None
        self._opened = True

    def close(self, *, timeout: float | None = None) -> None:
        if self._closed:
            return
        try:
            if timeout is None:
                self._pool.close()
            else:
                self._pool.close(timeout=timeout)
        except BaseException as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            raise map_postgres_error(exc) from None
        finally:
            self._opened = False
            self._closed = True

    @contextmanager
    def connection(self, timeout: float | None = None) -> Iterator[Any]:
        """Acquire a connection while preserving non-database body errors."""

        if self._closed:
            raise PersistenceConfigurationError()
        try:
            manager = (
                self._pool.connection()
                if timeout is None
                else self._pool.connection(timeout=timeout)
            )
            connection = manager.__enter__()
        except BaseException as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            raise map_postgres_error(exc) from None

        try:
            yield connection
        except BaseException as body_error:
            try:
                manager.__exit__(
                    type(body_error),
                    body_error,
                    body_error.__traceback__,
                )
            except BaseException as release_error:
                if isinstance(release_error, (KeyboardInterrupt, SystemExit)):
                    raise
                # Never mask the exception that caused the transaction to fail.
            if is_postgres_error(body_error):
                raise map_postgres_error(body_error) from None
            raise
        else:
            try:
                manager.__exit__(None, None, None)
            except BaseException as exc:
                if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                    raise
                raise map_postgres_error(exc) from None

    def check(self) -> None:
        """Ask psycopg-pool to validate idle connections."""

        try:
            self._pool.check()
        except BaseException as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            raise map_postgres_error(exc) from None

    def get_stats(self) -> dict[str, Any]:
        try:
            stats = self._pool.get_stats()
        except BaseException as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            raise map_postgres_error(exc) from None
        return dict(stats)

    def unit_of_work(self, **kwargs: Any):
        from .unit_of_work import PostgresUnitOfWork

        return PostgresUnitOfWork(self, **kwargs)

    def __enter__(self) -> "PostgresPool":
        self.open()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()


PsycopgPool = PostgresPool


__all__ = [
    "ConnectionPool",
    "PoolFactory",
    "PostgresPool",
    "PostgresPoolConfig",
    "PsycopgPool",
]
