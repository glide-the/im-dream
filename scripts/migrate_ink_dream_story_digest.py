#!/usr/bin/env python3
"""Refresh the built-in ink-dream-story artifact digest in existing databases.

Context: dream-surface Task 1 Step 0 (E14).  Adding
``plugins/ink-dream-story/.ink/workspace-init.json`` changes the plugin
artifact digest (``plugin_artifact_digest()`` hashes every file in the
artifact tree).  ``seed_builtin_deck_plugin`` is a once-per-database INSERT,
so existing databases keep stale digests in three places and would silently
pack without the dream surface (e2e false positive).

This script performs decision (1) from the implementation plan
(2026-08-03-dream-surface-execution-implementation-plan.md Task 1 Step 0,
review note R1): migrate digests in place.

What it does (UPDATE only — no DDL, ``backend/database.py`` stays read-only):

1. Re-imports the plugin source into the content-addressed artifact store
   (idempotent; registers the new digest's artifact directory).
2. ``claude_plugin_installations``: refreshes ``artifact_digest`` /
   ``artifact_path`` for rows of the built-in package.
3. ``deck_claude_plugin_refs``: refreshes ``artifact_digest`` for refs whose
   installation row was updated (matched by old digest + package spec).
4. ``deck_runtime_plugin_locks.lock_json``: rewrites the built-in entry's
   ``claude_code_plugins[].artifact_digest`` inside the JSON document.

Idempotent: when the stored digest already matches the recomputed digest the
script is a no-op.  Frozen agent workspaces are untouched by design (packed
copies are pinned to their launch manifest; they keep the old artifact —
that is the freeze contract, not a bug).

Usage:
    python scripts/migrate_ink_dream_story_digest.py [--db PATH]

Default DB: ``backend/data/ink-and-memory.db`` (the backend default).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from services.claude_plugin import artifact_store  # noqa: E402
from services.deck.builtin_plugin import (  # noqa: E402
    BUILTIN_CLAUDE_PLUGIN_ID,
    BUILTIN_SOURCE_REF,
    builtin_plugin_path,
    plugin_artifact_digest,
)

_BUILTIN_PACKAGE_SPEC = "ink-dream-story@platform-builtin"


def _default_db_path() -> Path:
    preferred = BACKEND_ROOT / "data" / "ink-and-memory.db"
    if preferred.is_file():
        return preferred
    raise SystemExit(f"database not found: {preferred}; pass --db explicitly")


def migrate(db_path: Path) -> dict[str, int]:
    new_digest = plugin_artifact_digest()
    source = builtin_plugin_path()

    # 1. Register the new digest's artifact in the store (idempotent).
    artifact = artifact_store.import_tree(
        source,
        package_name="ink-dream-story",
        marketplace="platform-builtin",
    )
    if artifact.digest != new_digest:
        raise SystemExit(
            f"store digest {artifact.digest} != recomputed {new_digest}; aborting"
        )

    stats = {"installations": 0, "refs": 0, "locks": 0}
    db = sqlite3.connect(str(db_path))
    try:
        db.row_factory = sqlite3.Row
        tables = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        with db:
            # 2. Installations of the built-in package (any marketplace).
            if "claude_plugin_installations" in tables:
                rows = db.execute(
                    """
                    SELECT id, artifact_digest FROM claude_plugin_installations
                    WHERE package_name = 'ink-dream-story'
                      AND artifact_digest != ?
                    """,
                    (new_digest,),
                ).fetchall()
                for row in rows:
                    db.execute(
                        """
                        UPDATE claude_plugin_installations
                        SET artifact_digest = ?, artifact_path = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (new_digest, str(artifact.path), row["id"]),
                    )
                    stats["installations"] += 1

            # 3. Deck refs carrying a stale digest for the built-in spec.
            if "deck_claude_plugin_refs" in tables:
                cursor = db.execute(
                    """
                    UPDATE deck_claude_plugin_refs
                    SET artifact_digest = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE package_spec IN (?, ?)
                      AND artifact_digest != ?
                    """,
                    (new_digest, _BUILTIN_PACKAGE_SPEC, BUILTIN_CLAUDE_PLUGIN_ID, new_digest),
                )
                stats["refs"] = cursor.rowcount

            # 4. Runtime locks: rewrite the digest inside lock_json.
            if "deck_runtime_plugin_locks" in tables:
                locks = db.execute(
                    "SELECT id, lock_json FROM deck_runtime_plugin_locks"
                ).fetchall()
                for lock in locks:
                    try:
                        payload = json.loads(lock["lock_json"])
                    except (TypeError, json.JSONDecodeError):
                        continue
                    entries = payload.get("claude_code_plugins") or []
                    changed = False
                    for entry in entries:
                        if (
                            entry.get("source_ref") == BUILTIN_SOURCE_REF
                            and entry.get("artifact_digest") != new_digest
                        ):
                            entry["artifact_digest"] = new_digest
                            changed = True
                    if changed:
                        db.execute(
                            "UPDATE deck_runtime_plugin_locks SET lock_json = ? WHERE id = ?",
                            (json.dumps(payload, ensure_ascii=False), lock["id"]),
                        )
                        stats["locks"] += 1
    finally:
        db.close()
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=None, help="SQLite database path")
    args = parser.parse_args()
    db_path = args.db or _default_db_path()
    stats = migrate(db_path)
    print(
        f"migrated {db_path}: installations={stats['installations']} "
        f"refs={stats['refs']} locks={stats['locks']}"
    )


if __name__ == "__main__":
    main()
