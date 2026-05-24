# [Input] Consume database.list_sessions (via database module import).
#         Reads INK_AGENT_CONTEXT_SESSIONS env var.
# [Output] Provide ClaudeAgentContextBuilder to ClaudeAgentService.
# [Pos] context-assembly node in backend/claude_agent
# [Sync] 2026-05-22: rewritten for Ink & Memory; replaces Pawkeyland's pet/persona
#                    context assembly with writing-session context injection.

"""Context builder for the Ink & Memory Claude Agent.

Assembles the system prompt that grounds the Claude agent in the user's
Ink & Memory writing context.  Unlike the Pawkeyland version (which injects
pet persona, Mem0 memories, and necklace sensor data), this builder:

1. Loads the user's recent writing sessions from the database.
2. Renders a system prompt that positions Claude as a reflective writing
   assistant with knowledge of the user's recent entries.
3. Provides a ``build_user_message`` helper that prepends lightweight
   runtime context (current date/time) to the raw user message.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Number of recent sessions injected into system prompt.
# Configurable via INK_AGENT_CONTEXT_SESSIONS (default 5).
_CONTEXT_SESSIONS_DEFAULT = 5


def _context_session_count() -> int:
    try:
        return max(1, int(os.getenv("INK_AGENT_CONTEXT_SESSIONS", str(_CONTEXT_SESSIONS_DEFAULT)) or str(_CONTEXT_SESSIONS_DEFAULT)))
    except (ValueError, TypeError):
        return _CONTEXT_SESSIONS_DEFAULT


# ---------------------------------------------------------------------------
# System prompt template
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_TEMPLATE = """\
You are a thoughtful writing assistant for Ink & Memory — a reflective journaling app.

Your role is to help the user explore their thoughts, memories, and creative writing with \
curiosity, care, and depth.  You can reference the user's recent journal entries below to \
provide grounded, personalised support.

Principles:
- Be warm, reflective, and non-judgmental.
- When the user mentions a past experience, you may gently connect it to relevant recent entries.
- Encourage the user to go deeper, not wider — depth over breadth.
- Do not lecture or give unsolicited advice; ask questions that open new avenues.
- Respect privacy: treat all journal content as confidential.
- Respond in the same language the user writes in.

{recent_sessions_block}\
"""

_SESSIONS_HEADER = "## Recent Journal Entries\n\n"
_SESSION_ENTRY_TEMPLATE = "### {date} — {title}\n{excerpt}\n"
_NO_SESSIONS_TEXT = "_No recent entries found._\n"


def _render_session_entry(session: dict[str, Any]) -> str:
    """Render one database session row into a Markdown entry block.

    database.list_sessions returns rows with keys:
    id, name, created_at, updated_at, first_line.
    """
    raw_date = str(session.get("updated_at") or session.get("created_at") or "")[:10]
    title = (session.get("name") or "Untitled").strip()
    excerpt = (session.get("first_line") or "").strip()
    if not excerpt:
        excerpt = "_[Empty entry]_"
    return _SESSION_ENTRY_TEMPLATE.format(date=raw_date, title=title, excerpt=excerpt)


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


class ClaudeAgentContextBuilder:
    """Assembles system prompt and user message for a Claude Agent turn.

    Usage::

        builder = ClaudeAgentContextBuilder()
        system_prompt = await builder.build_system_prompt(user_id, db_conn_or_None)
        user_msg = builder.build_user_message(raw_message)
    """

    def __init__(self, context_session_count: Optional[int] = None) -> None:
        self._context_session_count = (
            context_session_count
            if context_session_count is not None
            else _context_session_count()
        )

    async def build_system_prompt(self, user_id: str) -> str:
        """Build the system prompt for *user_id* by injecting recent journal entries."""
        recent_sessions_block = await self._load_recent_sessions_block(user_id)
        return _SYSTEM_PROMPT_TEMPLATE.format(
            recent_sessions_block=recent_sessions_block
        )

    def build_user_message(
        self,
        raw_message: str,
        *,
        timezone_name: str = "UTC",
    ) -> str:
        """Prepend a lightweight runtime context block to *raw_message*.

        The runtime block informs Claude of the current date so it can use
        temporal references naturally (e.g. "yesterday's entry").
        """
        now = datetime.now(tz=timezone.utc)
        date_str = now.strftime("%Y-%m-%d %H:%M UTC")
        runtime_block = f"[Current time: {date_str} / Timezone hint: {timezone_name}]\n\n"
        return runtime_block + raw_message

    async def _load_recent_sessions_block(self, user_id: str) -> str:
        """Return a Markdown block with the user's recent journal entries."""
        try:
            sessions = await self._fetch_sessions(user_id)
        except Exception:  # noqa: BLE001
            logger.exception(
                "Failed to load recent sessions for user_id=%s; skipping context.", user_id
            )
            return _SESSIONS_HEADER + _NO_SESSIONS_TEXT + "\n"

        if not sessions:
            return _SESSIONS_HEADER + _NO_SESSIONS_TEXT + "\n"

        entries = "".join(
            _render_session_entry(s) for s in sessions[: self._context_session_count]
        )
        return _SESSIONS_HEADER + entries + "\n"

    async def _fetch_sessions(self, user_id: str) -> list[dict[str, Any]]:
        """Fetch recent sessions from the database using the project's database module.

        ``database.list_sessions(user_id)`` is synchronous and manages its own
        connection; we call it in a thread executor to avoid blocking the event loop.
        """
        import asyncio
        import database  # local import; database module lives in backend/

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, database.list_sessions, user_id
        )
        rows = list(result or [])
        # Respect context_session_count limit (DB returns all sessions)
        return rows[: self._context_session_count]
