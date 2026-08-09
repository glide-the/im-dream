"""Dream-owned Alembic environment; no SQLite or implicit database fallback."""

from __future__ import annotations

from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from persistence.config import require_test_database_url


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def _psycopg_sqlalchemy_url(database_url: str) -> str:
    """Select the installed psycopg 3 SQLAlchemy dialect explicitly.

    SQLAlchemy maps a plain ``postgresql://`` URL to psycopg2 for historical
    compatibility.  Dream deliberately ships psycopg 3 only, so leaving the
    driver implicit makes a valid production/test DSN fail at migration
    startup with an unrelated missing-module error.
    """

    if database_url.startswith("postgresql+psycopg://"):
        return database_url
    if database_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + database_url.removeprefix(
            "postgresql://"
        )
    if database_url.startswith("postgres://"):
        return "postgresql+psycopg://" + database_url.removeprefix("postgres://")
    raise RuntimeError("Dream Alembic requires an explicit PostgreSQL URL")


def _database_url() -> str:
    if os.getenv("TEST_DATABASE_URL"):
        return _psycopg_sqlalchemy_url(require_test_database_url())
    configured = (config.get_main_option("sqlalchemy.url") or "").strip()
    if configured:
        return _psycopg_sqlalchemy_url(configured)
    runtime = (os.getenv("DATABASE_URL") or "").strip()
    if runtime:
        return _psycopg_sqlalchemy_url(runtime)
    raise RuntimeError(
        "Alembic requires an explicit PostgreSQL sqlalchemy.url, TEST_DATABASE_URL, or DATABASE_URL"
    )


def run_migrations_offline() -> None:
    # The first revision's exact baseline-adopt decision requires live catalog
    # inspection.  Producing blind offline SQL would bypass that safety gate.
    raise RuntimeError("offline Dream migrations are disabled by the baseline-adopt contract")


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table="dream_alembic_version",
            include_schemas=False,
            compare_type=True,
            transaction_per_migration=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
