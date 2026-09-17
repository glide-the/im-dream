"""PostgreSQL configuration with fail-closed test-database validation.

[Input] Explicit process/database env and optional Admin-owned env file.
[Output] Validated PostgreSQL targets without importing unrelated credentials.
[Pos] Persistence configuration boundary for Dream runtime and test tooling.
[Sync] 2026-08-22: allow the explicit Admin env file to replace only a
                   dotenv-sourced runtime URL; process-injected URLs still win.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import stat
from typing import Final
from urllib.parse import parse_qsl, unquote, urlsplit

from .errors import PersistenceConfigurationError


TEST_DATABASE_URL_ENV: Final = "TEST_DATABASE_URL"
DATABASE_URL_ENV: Final = "DATABASE_URL"
DATABASE_ENV_FILE_ENV: Final = "INK_DATABASE_ENV_FILE"

# Isolation labels must be distinct tokens in the database name.  Accepting a
# substring such as ``contest`` would turn a typo into authorization to run
# destructive migration tests against an unrelated database.
DEFAULT_TEST_DATABASE_MARKERS: Final[frozenset[str]] = frozenset(
    {"codex", "test", "tests", "testing", "tmp", "temp", "ci", "sandbox"}
)
_SHARED_DATABASE_NAMES: Final[frozenset[str]] = frozenset(
    {"ink-memory", "ink_memory", "inkmemory", "postgres", "template0", "template1"}
)
_POSTGRES_SCHEMES: Final[frozenset[str]] = frozenset({"postgres", "postgresql"})
_AMBIGUOUS_QUERY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "database",
        "dbname",
        "host",
        "hostaddr",
        "port",
        "service",
        "servicefile",
    }
)


class TestDatabaseSafetyError(PersistenceConfigurationError):
    """A redacted, machine-readable refusal to use a test database target."""

    __test__ = False
    code = "TEST_DATABASE_TARGET_REJECTED"
    public_message = "The test database target failed the isolation safety check."

    def __init__(self, reason: str = "unsafe_target") -> None:
        self.reason = reason
        super().__init__()


@dataclass(frozen=True, repr=False)
class PostgresTarget:
    """Parsed PostgreSQL target whose repr/str never reveals its URI."""

    _dsn: str = field(repr=False)
    database_name: str
    host: str | None
    port: int
    scheme: str

    @property
    def dsn(self) -> str:
        return self._dsn

    @property
    def url(self) -> str:
        """Compatibility spelling for callers that pass a connection URL."""

        return self._dsn

    @property
    def database(self) -> str:
        return self.database_name

    @property
    def target_identity(self) -> tuple[str, int, str]:
        host = (self.host or "").casefold()
        if host in {"", "localhost", "127.0.0.1", "::1"}:
            host = "<local>"
        return (host, self.port, self.database_name.casefold())

    def __repr__(self) -> str:
        return "PostgresTarget(<redacted>)"

    def __str__(self) -> str:
        return "<postgres-target:redacted>"


TestDatabaseTarget = PostgresTarget


def _parse_postgres_target(value: object, *, reason_prefix: str) -> PostgresTarget:
    if not isinstance(value, str) or not value.strip():
        raise TestDatabaseSafetyError(f"{reason_prefix}_missing")
    if value != value.strip() or any(character in value for character in "\r\n\x00"):
        raise TestDatabaseSafetyError(f"{reason_prefix}_malformed")

    try:
        parsed = urlsplit(value)
        scheme = parsed.scheme.casefold()
        port = parsed.port or 5432
        host = parsed.hostname
        query = parse_qsl(parsed.query, keep_blank_values=True)
    except (TypeError, ValueError):
        raise TestDatabaseSafetyError(f"{reason_prefix}_malformed") from None

    if scheme not in _POSTGRES_SCHEMES:
        raise TestDatabaseSafetyError(f"{reason_prefix}_not_postgresql")
    if parsed.fragment:
        raise TestDatabaseSafetyError(f"{reason_prefix}_malformed")
    if any(key.casefold() in _AMBIGUOUS_QUERY_KEYS for key, _ in query):
        raise TestDatabaseSafetyError(f"{reason_prefix}_ambiguous_database")

    encoded_database = parsed.path[1:] if parsed.path.startswith("/") else ""
    database_name = unquote(encoded_database)
    if not database_name or "/" in database_name or "\\" in database_name:
        raise TestDatabaseSafetyError(f"{reason_prefix}_database_missing")

    return PostgresTarget(
        _dsn=value,
        database_name=database_name,
        host=host.casefold() if host else None,
        port=port,
        scheme=scheme,
    )


def parse_postgres_target(value: str) -> PostgresTarget:
    """Parse a PostgreSQL URL without emitting the URL in any failure path."""

    return _parse_postgres_target(value, reason_prefix="database_url")


def load_database_url_from_env_file(
    *,
    environ: MutableMapping[str, str] | None = None,
    override: bool = False,
) -> bool:
    """Load only ``DATABASE_URL`` from an explicitly configured env file.

    Existing values remain authoritative unless the caller explicitly marks
    them as replaceable.  Dream uses replacement only when the value came from
    its own dotenv file; a URL injected by the parent process always wins.
    """

    values = os.environ if environ is None else environ
    existing = values.get(DATABASE_URL_ENV)
    if isinstance(existing, str) and existing.strip() and not override:
        parse_postgres_target(existing)
        return False
    configured_path = values.get(DATABASE_ENV_FILE_ENV)
    if not isinstance(configured_path, str) or not configured_path.strip():
        return False
    path = Path(configured_path)
    if not path.is_absolute():
        raise PersistenceConfigurationError()
    try:
        metadata = path.lstat()
    except OSError:
        raise PersistenceConfigurationError() from None
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise PersistenceConfigurationError()
    try:
        from dotenv import dotenv_values

        selected = dotenv_values(path).get(DATABASE_URL_ENV)
    except Exception:
        raise PersistenceConfigurationError() from None
    target = parse_postgres_target(selected if isinstance(selected, str) else "")
    values[DATABASE_URL_ENV] = target.dsn
    return True


def _database_name_tokens(database_name: str) -> frozenset[str]:
    return frozenset(
        token
        for token in re.split(r"[^a-z0-9]+", database_name.casefold())
        if token
    )


def validate_test_database_url(
    test_database_url: str | None,
    *,
    database_url: str | None = None,
    expected_database_name: str | None = None,
    allowed_markers: frozenset[str] = DEFAULT_TEST_DATABASE_MARKERS,
) -> PostgresTarget:
    """Validate a test DSN using only fail-closed, non-secret comparisons.

    The test URI must be supplied directly.  This function never substitutes
    ``DATABASE_URL`` when it is missing.
    """

    target = _parse_postgres_target(test_database_url, reason_prefix="test_database_url")
    normalized_database = target.database_name.casefold()

    if normalized_database in _SHARED_DATABASE_NAMES:
        raise TestDatabaseSafetyError("shared_database")
    normalized_markers = frozenset(marker.casefold() for marker in allowed_markers)
    if not (_database_name_tokens(target.database_name) & normalized_markers):
        raise TestDatabaseSafetyError("isolation_marker_missing")

    if expected_database_name is not None:
        if not isinstance(expected_database_name, str) or not expected_database_name:
            raise TestDatabaseSafetyError("expected_database_name_invalid")
        # PostgreSQL can contain quoted, case-sensitive database names.  The
        # expected-name guard therefore uses exact decoded names.
        if target.database_name != expected_database_name:
            raise TestDatabaseSafetyError("unexpected_database_name")

    if isinstance(database_url, str) and database_url.strip():
        try:
            production_target = _parse_postgres_target(
                database_url,
                reason_prefix="database_url",
            )
        except TestDatabaseSafetyError:
            try:
                production_scheme = urlsplit(database_url).scheme.casefold()
            except (TypeError, ValueError):
                production_scheme = ""
            if production_scheme not in {"sqlite", "sqlite3"}:
                # A PostgreSQL service/host override or malformed production
                # target makes equality impossible to prove.  Destructive
                # test tooling must fail closed in that case.
                raise TestDatabaseSafetyError("database_url_unverifiable") from None
            production_target = None
        if (
            production_target is not None
            and target.target_identity == production_target.target_identity
        ):
            raise TestDatabaseSafetyError("matches_database_url")

    return target


def require_test_database_target(
    expected_database_name: str | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    allowed_markers: frozenset[str] = DEFAULT_TEST_DATABASE_MARKERS,
) -> PostgresTarget:
    """Read and validate an explicitly configured ``TEST_DATABASE_URL``."""

    values = os.environ if environ is None else environ
    return validate_test_database_url(
        values.get(TEST_DATABASE_URL_ENV),
        database_url=values.get(DATABASE_URL_ENV),
        expected_database_name=expected_database_name,
        allowed_markers=allowed_markers,
    )


def require_test_database_url(
    expected_database_name: str | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    allowed_markers: frozenset[str] = DEFAULT_TEST_DATABASE_MARKERS,
) -> str:
    """Return the validated raw URL for a test-only connection factory."""

    return require_test_database_target(
        expected_database_name,
        environ=environ,
        allowed_markers=allowed_markers,
    ).dsn


__all__ = [
    "DATABASE_ENV_FILE_ENV",
    "DATABASE_URL_ENV",
    "DEFAULT_TEST_DATABASE_MARKERS",
    "PostgresTarget",
    "TEST_DATABASE_URL_ENV",
    "TestDatabaseSafetyError",
    "TestDatabaseTarget",
    "load_database_url_from_env_file",
    "parse_postgres_target",
    "require_test_database_target",
    "require_test_database_url",
    "validate_test_database_url",
]
