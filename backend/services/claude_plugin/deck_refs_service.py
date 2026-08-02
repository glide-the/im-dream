"""Deck → Claude plugin installation reference management.

A Deck stores only references: installation id + package spec + resolved
version + digest + enabled flag + order.  Selectable installations must be:

- really installed (row exists in ``claude_plugin_installations``),
- status ``ready``,
- artifact digest verifies against the immutable store,
- SemVer-compatible with the current Claude CLI version.
"""

from __future__ import annotations

import sqlite3
from typing import Any

try:
    from backend.services.claude_plugin.install_service import PluginInstallService
except ModuleNotFoundError:  # Support backend directory on PYTHONPATH.
    from services.claude_plugin.install_service import PluginInstallService


class DeckPluginRefError(ValueError):
    def __init__(self, code: str, message: str, *, status_code: int = 422):
        self.code = code
        self.status_code = status_code
        super().__init__(message)


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


class DeckPluginRefService:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db
        self.db.row_factory = sqlite3.Row
        self._installations = PluginInstallService(db)

    def assert_deck_owner(self, deck_id: str, actor_id: str) -> None:
        row = self.db.execute(
            "SELECT owner_id, enabled FROM decks WHERE id = ?", (deck_id,)
        ).fetchone()
        if row is None or str(row["owner_id"]) != str(actor_id):
            raise DeckPluginRefError(
                "DECK_ACCESS_DENIED",
                "Deck not found or permission denied.",
                status_code=404,
            )

    def list_refs(self, deck_id: str, actor_id: str) -> list[dict[str, Any]]:
        self.assert_deck_owner(deck_id, actor_id)
        rows = self.db.execute(
            """
            SELECT r.*, i.status AS installation_status, i.source_type,
                   i.claude_cli_version, i.manifest_json,
                   i.component_inventory_json
            FROM deck_claude_plugin_refs r
            JOIN claude_plugin_installations i ON i.id = r.plugin_installation_id
            WHERE r.deck_id = ?
            ORDER BY r.order_index, r.created_at, r.plugin_installation_id
            """,
            (deck_id,),
        ).fetchall()
        return [_row_to_dict(row) for row in rows]

    def replace_refs(
        self,
        deck_id: str,
        actor_id: str,
        refs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Validate and atomically replace the Deck's plugin references."""
        self.assert_deck_owner(deck_id, actor_id)
        validated: list[dict[str, Any]] = []
        seen: set[str] = set()
        for position, ref in enumerate(refs):
            installation_id = str(ref.get("plugin_installation_id") or "").strip()
            if not installation_id:
                raise DeckPluginRefError(
                    "CLAUDE_PLUGIN_REF_INVALID",
                    "each reference requires plugin_installation_id",
                )
            if installation_id in seen:
                raise DeckPluginRefError(
                    "CLAUDE_PLUGIN_REF_INVALID",
                    f"duplicate reference: {installation_id}",
                )
            seen.add(installation_id)
            record = self._installations.get_installation(installation_id)
            if record is None:
                raise DeckPluginRefError(
                    "CLAUDE_PLUGIN_NOT_FOUND",
                    f"installation {installation_id} does not exist",
                    status_code=404,
                )
            if record["status"] != "ready":
                raise DeckPluginRefError(
                    "CLAUDE_PLUGIN_NOT_READY",
                    f"installation {installation_id} is not ready "
                    f"(status={record['status']})",
                    status_code=409,
                )
            if not self._installations.verify_installation_artifact(record):
                raise DeckPluginRefError(
                    "CLAUDE_PLUGIN_INTEGRITY_FAILED",
                    f"artifact digest verification failed for "
                    f"{record['requested_package_spec']}",
                    status_code=409,
                )
            if not self._installations.check_cli_compatibility(record):
                raise DeckPluginRefError(
                    "CLAUDE_PLUGIN_INCOMPATIBLE",
                    f"{record['requested_package_spec']} is not compatible with "
                    "the current Claude Code version",
                    status_code=409,
                )
            validated.append(
                {
                    "plugin_installation_id": installation_id,
                    "package_spec": f"{record['package_name']}@{record['marketplace']}",
                    "resolved_version": record["resolved_version"],
                    "artifact_digest": record["artifact_digest"],
                    "enabled": bool(ref.get("enabled", True)),
                    "order_index": int(ref.get("order_index", position)),
                }
            )
        now_rows = self.db.execute(
            "SELECT 1 FROM decks WHERE id = ?", (deck_id,)
        ).fetchone()
        if now_rows is None:  # pragma: no cover - ownership checked above
            raise DeckPluginRefError(
                "DECK_ACCESS_DENIED", "Deck not found.", status_code=404
            )
        try:
            from backend.database import replace_deck_claude_plugin_refs
        except ModuleNotFoundError:
            from database import replace_deck_claude_plugin_refs
        replace_deck_claude_plugin_refs(self.db, deck_id, validated)
        return self.list_refs(deck_id, actor_id)
