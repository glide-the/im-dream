# [Input] Consume database.list_sessions (via database module import).
#         Reads INK_AGENT_CONTEXT_SESSIONS env var.
# [Output] Provide ClaudeAgentContextBuilder to ClaudeAgentService.
# [Pos] context-assembly node in backend/claude_agent
# [Sync] 2026-05-22: rewritten for Ink & Memory; replaces Pawkeyland's pet/persona
#                    context assembly with writing-session context injection.
# [Sync] 2026-05-26: merge build_user_message_content (SDK lib) into build_user_message
#                    so that the SDK no longer participates in context processing.
# [Sync] 2026-05-26: use extract_text_from_parts (message_parts.py) for full UIMessage
#                    parts protocol (text + file + source-url + workspace-file).

"""Context builder for the Ink & Memory Claude Agent.

Assembles the system prompt that grounds the Claude agent in the user's
Ink & Memory writing context.  Unlike the Pawkeyland version (which injects
pet persona, Mem0 memories, and necklace sensor data), this builder:

1. Loads the user's recent writing sessions from the database.
2. Renders a system prompt that positions Claude as a reflective writing
   assistant with knowledge of the user's recent entries.
3. Provides a ``build_user_message`` helper that builds the full list of
   content blocks for a user turn: attachment image blocks, a lightweight
   ``<runtime_context>`` block, and the user's message text extracted from
   the full AI-SDK UIMessage parts list.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from libs.claude_agent_kit.messages.message_parts import extract_text_from_parts

logger = logging.getLogger(__name__)

# MIME types that can be rendered inline within chat transcripts.
_INLINE_IMAGE_MIME_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/gif", "image/webp"}
)

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
        system_prompt = await builder.build_system_prompt(user_id)
        content_blocks = builder.build_user_message(raw_message, attachments=attachments)
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
        message_parts: Optional[list],
        *,
        attachments: Optional[list[Any]] = None,
        model: Optional[str] = None,
        max_turns: Optional[int] = None,
        thread_id: Optional[str] = None,
        resume: bool = False,
        include_runtime_context: bool = True,
        local_time: Optional[str] = None,
        local_timezone: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Build the content blocks for a user turn.

        *message_parts* is the AI-SDK UIMessage ``parts`` list
        (e.g. ``[{"type": "text", "text": "..."}]``).  Text is extracted from
        all ``type == "text"`` entries and appended as the final content block.

        Returns a list of content blocks in the order expected by Claude:
        attachment image blocks first, then the ``<runtime_context>`` block
        (unless *include_runtime_context* is False), then the user's message
        text.

        This method absorbs the responsibilities of the SDK-level
        ``build_user_message_content`` so the SDK no longer participates in
        context assembly.
        """
        blocks: list[dict[str, Any]] = []

        # Attach any user-supplied image assets.
        if attachments:
            for attachment in attachments:
                try:
                    media_type = getattr(attachment, "media_type", None) or ""
                    base64_data = getattr(attachment, "data", None) or ""
                    name = getattr(attachment, "name", "")
                    if media_type in _INLINE_IMAGE_MIME_TYPES:
                        blocks.append(
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": base64_data,
                                },
                            }
                        )
                    else:
                        logger.warning("Cannot process file: %s", name)
                except Exception as exc:  # noqa: BLE001
                    logger.error("Error processing attachment: %s", exc)

        if include_runtime_context:
            now = datetime.now(tz=timezone.utc)
            env_lines = [
                (
                    f"Date: {now.isoformat()}"
                    f" ({now.strftime('%A, %B %d, %Y')})"
                ),
            ]
            if local_time:
                env_lines.append(f"Local time: {local_time}")
            if local_timezone:
                env_lines.append(f"Timezone: {local_timezone}")
            if model:
                env_lines.append(f"Model: {model}")
            if max_turns is not None:
                env_lines.append(f"Max turns: {max_turns}")
            if thread_id:
                env_lines.append(f"Session ID: {thread_id}")
            if resume:
                env_lines.append("Resumed conversation: yes")

            blocks.append(
                {
                    "type": "text",
                    "text": (
                        "<runtime_context>\n"
                        + "\n".join(env_lines)
                        + "\n</runtime_context>"
                    ),
                }
            )

        # Convert all message_parts (text, file, source-url, workspace-file) to
        # a single text string using the full UIMessage parts protocol.
        user_text = extract_text_from_parts(message_parts)
        blocks.append({"type": "text", "text": user_text})
        return blocks


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
