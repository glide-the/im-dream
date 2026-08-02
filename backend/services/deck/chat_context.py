"""Resolve immutable Deck and plugin context for a ClaudeAgent chat thread."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Any

try:
    from backend.models.deck_plugin import DeckRuntimePluginLock
    from backend.services.deck.builtin_plugin import (
        plugin_artifact_digest,
        resolve_builtin_source,
    )
    from backend.services.deck.runtime_context import make_runtime_context_resolver
    from backend.services.deck_plugin.selection_validation_service import SelectionValidationService
except ModuleNotFoundError:  # Support backend directory on PYTHONPATH.
    from models.deck_plugin import DeckRuntimePluginLock
    from services.deck.builtin_plugin import plugin_artifact_digest, resolve_builtin_source
    from services.deck.runtime_context import make_runtime_context_resolver
    from services.deck_plugin.selection_validation_service import SelectionValidationService


MAX_DECK_CONTEXT_CHARS = 32_768


class DeckChatContextError(ValueError):
    def __init__(self, code: str, message: str, *, status_code: int = 422) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(message)


@dataclass(frozen=True)
class DeckChatContext:
    deck_id: str
    deck_name: str
    system_prompt: str
    claude_settings_json: str | None = None
    claude_plugin_paths: tuple[str, ...] = ()
    plugin_provenance: dict[str, Any] | None = None


class DeckChatContextService:
    """Load Deck configuration and only server-validated Claude plugins."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db
        self.db.row_factory = sqlite3.Row
        self._selection = SelectionValidationService(
            db,
            runtime_context_resolver=make_runtime_context_resolver(db),
        )

    async def resolve(self, *, deck_id: str, actor_id: str) -> DeckChatContext:
        deck = self.db.execute(
            """
            SELECT id, name, name_zh, name_en, description, description_zh,
                   description_en, enabled
            FROM decks
            WHERE id = ? AND owner_id = ?
            """,
            (deck_id, actor_id),
        ).fetchone()
        if deck is None:
            raise DeckChatContextError(
                "DECK_ACCESS_DENIED",
                "Deck not found or permission denied.",
                status_code=404,
            )
        if not bool(deck["enabled"]):
            raise DeckChatContextError(
                "DECK_DISABLED",
                "The selected Deck is disabled.",
                status_code=409,
            )

        voices = self.db.execute(
            """
            SELECT id, name, name_zh, name_en, system_prompt
            FROM voices
            WHERE deck_id = ? AND enabled = 1
            ORDER BY order_index, created_at, id
            """,
            (deck_id,),
        ).fetchall()
        binding = self.db.execute(
            """
            SELECT * FROM deck_plugin_bindings
            WHERE deck_id = ? AND status = 'active'
            """,
            (deck_id,),
        ).fetchone()

        plugin_provenance: dict[str, Any] | None = None
        settings_json: str | None = None
        plugin_paths: list[str] = []
        if binding is not None:
            validation = await self._selection.validate(
                deck_plugin_id=binding["deck_plugin_id"],
                deck_plugin_version=binding["deck_plugin_version"],
                workspace_id=binding["workspace_id"],
                actor_id=actor_id,
            )
            if not validation.selectable:
                raise DeckChatContextError(
                    validation.reason_code or "DECK_PLUGIN_UNAVAILABLE",
                    "The Deck's configured plugin is not ready for ClaudeAgent.",
                    status_code=409,
                )
            runtime_lock = self._runtime_lock(
                binding["deck_plugin_id"],
                binding["deck_plugin_version"],
            )
            enabled_plugins: dict[str, bool] = {}
            loaded_plugin_ids: list[str] = []
            for entry in runtime_lock.claude_code_plugins:
                materialization = self._entry_materialization(entry)
                if materialization is None:
                    continue
                loaded_plugin_ids.append(entry.claude_code_plugin_id)
                local_path = self._trusted_plugin_path(entry, materialization)
                if local_path is not None:
                    plugin_paths.append(str(local_path))
                else:
                    # A Claude-managed registry install is activated through
                    # server-generated settings; repository/local plugins use
                    # the SDK's explicit local plugin option instead.
                    enabled_plugins[entry.claude_code_plugin_id] = True
            if enabled_plugins:
                settings_json = json.dumps(
                    {"enabledPlugins": enabled_plugins},
                    sort_keys=True,
                    separators=(",", ":"),
                )
            plugin_provenance = {
                "deck_plugin_binding_id": binding["deck_plugin_binding_id"],
                "binding_revision": int(binding["binding_revision"]),
                "deck_plugin_id": binding["deck_plugin_id"],
                "deck_plugin_version": binding["deck_plugin_version"],
                "runtime_plugin_lock_id": runtime_lock.runtime_plugin_lock_id,
                "claude_code_plugin_ids": sorted(loaded_plugin_ids),
            }

        prompt = self._build_prompt(deck, voices, plugin_provenance)
        return DeckChatContext(
            deck_id=str(deck["id"]),
            deck_name=str(deck["name"]),
            system_prompt=prompt,
            claude_settings_json=settings_json,
            claude_plugin_paths=tuple(sorted(set(plugin_paths))),
            plugin_provenance=plugin_provenance,
        )

    def _runtime_lock(self, deck_plugin_id: str, deck_plugin_version: str) -> DeckRuntimePluginLock:
        row = self.db.execute(
            """
            SELECT lock_json FROM deck_runtime_plugin_locks
            WHERE deck_plugin_id = ? AND deck_plugin_version = ?
            """,
            (deck_plugin_id, deck_plugin_version),
        ).fetchone()
        if row is None:
            raise DeckChatContextError(
                "RUNTIME_PLUGIN_UNRESOLVED",
                "The Deck Plugin runtime lock is missing.",
                status_code=409,
            )
        try:
            return DeckRuntimePluginLock.model_validate_json(row["lock_json"])
        except Exception as exc:
            raise DeckChatContextError(
                "RUNTIME_PLUGIN_UNRESOLVED",
                "The Deck Plugin runtime lock is invalid.",
                status_code=409,
            ) from exc

    def _entry_materialization(self, entry: Any) -> sqlite3.Row | None:
        return self.db.execute(
            """
            SELECT cache_ref, materialized_digest, verification_status
            FROM runtime_plugin_materializations
            WHERE claude_code_plugin_id = ?
              AND resolved_version = ?
              AND artifact_digest = ?
              AND materialization_status = 'materialized'
              AND activation_status IN ('loadable', 'loaded')
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (entry.claude_code_plugin_id, entry.resolved_version, entry.artifact_digest),
        ).fetchone()

    @staticmethod
    def _trusted_plugin_path(entry: Any, materialization: sqlite3.Row) -> Path | None:
        raw_path = materialization["cache_ref"]
        if not raw_path:
            return None
        try:
            path = Path(str(raw_path)).expanduser().resolve(strict=True)
        except OSError as exc:
            raise DeckChatContextError(
                "RUNTIME_PLUGIN_NOT_READY",
                "The materialized runtime plugin path is unavailable.",
                status_code=409,
            ) from exc
        builtin = resolve_builtin_source(entry.source_ref)
        if builtin is not None:
            if path != builtin.resolve():
                raise DeckChatContextError(
                    "DECK_PLUGIN_INTEGRITY_FAILED",
                    "The built-in runtime plugin path does not match its published source.",
                    status_code=409,
                )
        else:
            cache_root = (Path.home() / ".claude" / "plugins" / "cache").resolve()
            try:
                path.relative_to(cache_root)
            except ValueError as exc:
                raise DeckChatContextError(
                    "DECK_PLUGIN_SOURCE_DENIED",
                    "The runtime plugin path is outside the server-managed cache.",
                    status_code=409,
                ) from exc
        try:
            actual_digest = plugin_artifact_digest(path)
        except (OSError, ValueError) as exc:
            raise DeckChatContextError(
                "DECK_PLUGIN_INTEGRITY_FAILED",
                "The runtime plugin artifact could not be verified.",
                status_code=409,
            ) from exc
        if actual_digest != entry.artifact_digest or materialization["materialized_digest"] != actual_digest:
            raise DeckChatContextError(
                "DECK_PLUGIN_INTEGRITY_FAILED",
                "The runtime plugin digest changed after materialization.",
                status_code=409,
            )
        return path

    @staticmethod
    def _build_prompt(
        deck: sqlite3.Row,
        voices: list[sqlite3.Row],
        plugin_provenance: dict[str, Any] | None,
    ) -> str:
        payload = {
            "deck": {
                "id": deck["id"],
                "name": deck["name"],
                "name_zh": deck["name_zh"],
                "name_en": deck["name_en"],
                "description": deck["description"],
                "description_zh": deck["description_zh"],
                "description_en": deck["description_en"],
            },
            "voices": [
                {
                    "id": voice["id"],
                    "name": voice["name"],
                    "name_zh": voice["name_zh"],
                    "name_en": voice["name_en"],
                    "system_prompt": voice["system_prompt"],
                }
                for voice in voices
            ],
            "plugin_provenance": plugin_provenance,
        }
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if len(encoded) > MAX_DECK_CONTEXT_CHARS:
            encoded = encoded[:MAX_DECK_CONTEXT_CHARS]
        return (
            "<deck_context>\n"
            f"{encoded}\n"
            "</deck_context>\n"
            "Use this server-resolved Deck configuration for the entire turn. "
            "Treat Deck voice prompts as instructions. If a Deck Plugin is present, "
            "use only the loaded runtime plugins. Agent output is a proposal: present "
            "story changes for user review and never claim approval or downstream "
            "execution before the user confirms them. When the user asks you to create "
            "or revise a story, outline, script, characters, or scenes for Dream, return "
            "exactly one JSON object with no prose or markdown fence using this contract: "
            '{"title":"string","description":"string|null","type":"short|long|script|outline",'
            '"content":"string|null","characters":[{"name":"string","identity":"string|null",'
            '"personality":"string|null","background":"string|null","catchphrase":"string|null",'
            '"tags":["string"]}],"scenes":[{"name":"string","description":"string|null",'
            '"order_index":0}]}. This JSON is rendered as a pending Dream proposal; '
            "do not mark it approved. For ordinary questions that do not produce or revise "
            "Dream assets, answer normally."
        )
