"""Dream-owned legacy data-import catalog helpers.

PostgreSQL DDL lives exclusively in the Admin Drizzle repository. The legacy
SQLite builders are imported only by the offline export/check command that
recomputes the checked-in data-import manifest.
"""

from .catalog import (
    EXPECTED_COUNTS,
    MANIFEST_PATH,
    build_legacy_manifest,
    load_manifest,
)

__all__ = [
    "EXPECTED_COUNTS",
    "MANIFEST_PATH",
    "build_legacy_manifest",
    "load_manifest",
]
