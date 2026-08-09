"""Stable, redacted persistence errors for the PostgreSQL boundary.

The database driver is deliberately not imported here.  Keeping the mapper
dependency-free makes configuration checks and unit tests usable before the
optional PostgreSQL runtime is installed, while SQLSTATE remains the source of
truth when a driver exception is available.
"""

from __future__ import annotations

from typing import Final


class PersistenceError(RuntimeError):
    """Base class for errors safe to return across the application boundary.

    Messages are class-owned constants.  Driver exception strings can contain
    SQL text, connection URIs, or passwords, so callers cannot inject an
    arbitrary message into these exceptions.
    """

    code: str = "PERSISTENCE_ERROR"
    public_message: str = "The persistence operation failed."
    retryable: bool = False

    def __init__(self) -> None:
        super().__init__(self.public_message)


class PersistenceConfigurationError(PersistenceError):
    code = "PERSISTENCE_CONFIGURATION_ERROR"
    public_message = "The persistence configuration is invalid."


class PersistenceDependencyError(PersistenceConfigurationError):
    code = "PERSISTENCE_DEPENDENCY_MISSING"
    public_message = "The PostgreSQL runtime dependency is unavailable."


class PersistenceUnavailableError(PersistenceError):
    code = "PERSISTENCE_UNAVAILABLE"
    public_message = "The persistence service is unavailable."
    retryable = True


class PersistenceTimeoutError(PersistenceUnavailableError):
    code = "PERSISTENCE_TIMEOUT"
    public_message = "The persistence operation timed out."


class PersistenceConstraintError(PersistenceError):
    code = "PERSISTENCE_CONSTRAINT_VIOLATION"
    public_message = "The requested change violates a persistence constraint."


class UniqueConstraintError(PersistenceConstraintError):
    code = "PERSISTENCE_UNIQUE_VIOLATION"
    public_message = "The requested resource already exists."


class ForeignKeyConstraintError(PersistenceConstraintError):
    code = "PERSISTENCE_FOREIGN_KEY_VIOLATION"
    public_message = "The requested change references an unavailable resource."


class CheckConstraintError(PersistenceConstraintError):
    code = "PERSISTENCE_CHECK_VIOLATION"
    public_message = "The requested change violates a data rule."


class NotNullConstraintError(PersistenceConstraintError):
    code = "PERSISTENCE_NOT_NULL_VIOLATION"
    public_message = "A required persistence value is missing."


class PersistenceConcurrencyError(PersistenceError):
    code = "PERSISTENCE_CONCURRENCY_ERROR"
    public_message = "The persistence operation conflicted with another change."
    retryable = True


class SerializationFailureError(PersistenceConcurrencyError):
    code = "PERSISTENCE_SERIALIZATION_FAILURE"
    public_message = "The persistence operation must be retried."


class DeadlockError(PersistenceConcurrencyError):
    code = "PERSISTENCE_DEADLOCK"
    public_message = "The persistence operation was interrupted by a deadlock."


class CatalogMismatchError(PersistenceConfigurationError):
    code = "PERSISTENCE_CATALOG_MISMATCH"
    public_message = "The PostgreSQL catalog does not match the expected schema."


class UnitOfWorkStateError(PersistenceError):
    code = "PERSISTENCE_UNIT_OF_WORK_STATE"
    public_message = "The unit of work is not in a valid state for this operation."


# PostgreSQL SQLSTATE is more stable than psycopg's concrete exception layout.
_SQLSTATE_ERROR_TYPES: Final[dict[str, type[PersistenceError]]] = {
    "23505": UniqueConstraintError,
    "23503": ForeignKeyConstraintError,
    "23514": CheckConstraintError,
    "23502": NotNullConstraintError,
    "40001": SerializationFailureError,
    "40P01": DeadlockError,
    "57014": PersistenceTimeoutError,  # query_canceled / statement_timeout
    "55P03": PersistenceTimeoutError,  # lock_not_available / lock_timeout
}

_CLASS_NAME_ERROR_TYPES: Final[dict[str, type[PersistenceError]]] = {
    "UniqueViolation": UniqueConstraintError,
    "ForeignKeyViolation": ForeignKeyConstraintError,
    "CheckViolation": CheckConstraintError,
    "NotNullViolation": NotNullConstraintError,
    "SerializationFailure": SerializationFailureError,
    "DeadlockDetected": DeadlockError,
    "QueryCanceled": PersistenceTimeoutError,
    "PoolTimeout": PersistenceTimeoutError,
    "ConnectionTimeout": PersistenceTimeoutError,
    "ConnectionFailure": PersistenceUnavailableError,
    "OperationalError": PersistenceUnavailableError,
    "InterfaceError": PersistenceUnavailableError,
}

_POSTGRES_CLASS_NAMES: Final[frozenset[str]] = frozenset(
    {
        *_CLASS_NAME_ERROR_TYPES,
        "DatabaseError",
        "DataError",
        "IntegrityError",
        "InternalError",
        "ProgrammingError",
        "Error",
    }
)


def _exception_chain(exc: BaseException):
    """Yield a short exception chain without formatting any exception."""

    seen: set[int] = set()
    current: BaseException | None = exc
    for _ in range(6):
        if current is None or id(current) in seen:
            break
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def postgres_sqlstate(exc: BaseException) -> str | None:
    """Extract a five-character SQLSTATE without inspecting exception text."""

    for current in _exception_chain(exc):
        for value in (
            getattr(current, "sqlstate", None),
            getattr(current, "pgcode", None),
            getattr(getattr(current, "diag", None), "sqlstate", None),
        ):
            if isinstance(value, str) and len(value) == 5:
                return value.upper()
    return None


def is_postgres_error(exc: BaseException) -> bool:
    """Return whether *exc* looks like a driver/pool error worth translating."""

    if isinstance(exc, PersistenceError | TimeoutError):
        return True
    if postgres_sqlstate(exc) is not None:
        return True
    for current in _exception_chain(exc):
        cls = type(current)
        if cls.__name__ in _POSTGRES_CLASS_NAMES:
            return True
        if cls.__module__.split(".", 1)[0] in {"psycopg", "psycopg_pool"}:
            return True
    return False


def map_postgres_error(exc: BaseException) -> PersistenceError:
    """Translate a driver error to a stable error without retaining its text."""

    if isinstance(exc, PersistenceError):
        return exc
    if isinstance(exc, TimeoutError):
        return PersistenceTimeoutError()

    state = postgres_sqlstate(exc)
    if state in _SQLSTATE_ERROR_TYPES:
        return _SQLSTATE_ERROR_TYPES[state]()
    if state is not None:
        if state.startswith("08") or state in {"57P01", "57P02", "57P03"}:
            return PersistenceUnavailableError()
        if state.startswith("23"):
            return PersistenceConstraintError()
        if state.startswith("40"):
            return PersistenceConcurrencyError()

    for current in _exception_chain(exc):
        error_type = _CLASS_NAME_ERROR_TYPES.get(type(current).__name__)
        if error_type is not None:
            return error_type()
    return PersistenceError()


def raise_mapped_postgres_error(exc: BaseException) -> None:
    """Raise the redacted domain equivalent, suppressing the unsafe cause."""

    raise map_postgres_error(exc) from None


# Compatibility aliases use domain wording while retaining one concrete type.
UniqueViolationError = UniqueConstraintError
ForeignKeyViolationError = ForeignKeyConstraintError
CheckViolationError = CheckConstraintError
NotNullViolationError = NotNullConstraintError
SerializationError = SerializationFailureError
DeadlockDetectedError = DeadlockError


__all__ = [
    "CatalogMismatchError",
    "CheckConstraintError",
    "CheckViolationError",
    "DeadlockDetectedError",
    "DeadlockError",
    "ForeignKeyConstraintError",
    "ForeignKeyViolationError",
    "NotNullConstraintError",
    "NotNullViolationError",
    "PersistenceConcurrencyError",
    "PersistenceConfigurationError",
    "PersistenceConstraintError",
    "PersistenceDependencyError",
    "PersistenceError",
    "PersistenceTimeoutError",
    "PersistenceUnavailableError",
    "SerializationError",
    "SerializationFailureError",
    "UniqueConstraintError",
    "UniqueViolationError",
    "UnitOfWorkStateError",
    "is_postgres_error",
    "map_postgres_error",
    "postgres_sqlstate",
    "raise_mapped_postgres_error",
]
