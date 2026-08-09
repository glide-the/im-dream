"""Dream-owned PostgreSQL schema catalog and migration helpers.

The package deliberately contains no application connection fallback.  The
legacy SQLite builders are imported only by the offline export/check command
that recomputes the checked-in schema manifest.
"""

from .catalog import (
    EXPECTED_COUNTS,
    MANIFEST_PATH,
    POSTGRES_SCHEMA_PATH,
    build_legacy_manifest,
    load_manifest,
)

__all__ = [
    "EXPECTED_COUNTS",
    "MANIFEST_PATH",
    "POSTGRES_SCHEMA_PATH",
    "build_legacy_manifest",
    "load_manifest",
]
