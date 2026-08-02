"""Resolve immutable Deck and plugin context for a ClaudeAgent chat thread.

2026-08-02 (deck-integration-delta): this module no longer produces Claude
Code settings JSON or plugin paths.  The old design resolved Deck Plugin
runtime locks into ``enabledPlugins`` settings and ``~/.claude/plugins/cache``
paths and pushed them through ``AgentRunOptions`` — both removed.

The new boundary:

- Decks store *references* to shared Claude plugin installations
  (``deck_claude_plugin_refs`` → ``claude_plugin_installations``).
- This service validates those references are ``ready`` and returns them as
  informational provenance for the system prompt.
- The actual plugin bytes are packed into the thread workspace at workspace
  bootstrap time (``services.claude_plugin.workspace_packer``) and loaded by
  the real CLI through ``--plugin-dir`` from the server-controlled launch
  manifest.  Nothing here touches per-run agent options.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import sqlite3
from typing import Any

try:
    from backend.services.claude_plugin.workspace_packer import load_deck_plugin_refs
except ModuleNotFoundError:  # Support backend directory on PYTHONPATH.
    from services.claude_plugin.workspace_packer import load_deck_plugin_refs


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
    # Informational only — digest-pinned references displayed in provenance.
    # Plugin bytes flow through the workspace pack, never through here.
    plugin_refs: tuple[dict[str, Any], ...] = ()
    plugin_provenance: dict[str, Any] | None = None


class DeckChatContextService:
    """Load Deck configuration and server-verified plugin references."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db
        self.db.row_factory = sqlite3.Row

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

        plugin_refs: list[dict[str, Any]] = []
        for ref in load_deck_plugin_refs(self.db, deck_id):
            if ref["installation_status"] != "ready":
                raise DeckChatContextError(
                    "DECK_PLUGIN_UNAVAILABLE",
                    "The Deck's configured Claude plugin is not ready: "
                    f"{ref['package_spec']} (status={ref['installation_status']}).",
                    status_code=409,
                )
            plugin_refs.append(
                {
                    "plugin_installation_id": ref["plugin_installation_id"],
                    "package_spec": ref["package_spec"],
                    "resolved_version": ref["resolved_version"],
                    "artifact_digest": ref["artifact_digest"],
                    "order_index": ref["order_index"],
                }
            )
        plugin_provenance = (
            {
                "source": "deck_claude_plugin_refs",
                "plugins": plugin_refs,
            }
            if plugin_refs
            else None
        )

        prompt = self._build_prompt(deck, voices, plugin_provenance)
        return DeckChatContext(
            deck_id=str(deck["id"]),
            deck_name=str(deck["name"]),
            system_prompt=prompt,
            plugin_refs=tuple(plugin_refs),
            plugin_provenance=plugin_provenance,
        )

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
            "Treat Deck voice prompts as instructions. If Deck plugin references "
            "are present, their skills/commands are already available in this "
            "workspace through the Claude plugin loader; use them when relevant. "
            "Agent output is a proposal: present "
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
