# [Input] One Admin-persisted Registry115 guidance dispatch envelope.
# [Output] Best-effort same-Thread Agent Runtime turn scheduling without database access.
# [Pos] Dream guidance execution seam; Admin owns Run/Thread authorization, idempotency and persistence.
# [Sync] 2026-09-15: remove all Guidance SQL/ORM access while preserving current Runtime dispatch behavior.
"""Story Workspace guidance Runtime dispatcher retained by Dream."""

from __future__ import annotations

import asyncio
import logging
from typing import Callable


logger = logging.getLogger(__name__)

GuidanceDispatcher = Callable[[str, str, str, list, dict], bool]


def build_thread_turn_dispatcher() -> GuidanceDispatcher:
    """Hand one already-persisted guidance message to the same Thread.

    There is no mid-turn injection channel. When the Thread is already running,
    the durable Admin-owned message remains available and this seam reports
    ``False`` without changing persistence or Runtime state.
    """

    def dispatch(
        thread_id: str,
        actor_id: str,
        message_id: str,
        parts: list,
        metadata: dict,
    ) -> bool:
        from agent_factory import claude_agent_thread_factory
        from claude_agent.service import ClaudeAgentRunRequest
        from services.admin_gateway import resolve_platform_model_alias

        snapshot = claude_agent_thread_factory.session_snapshot(thread_id)
        if snapshot and snapshot.get("lifecycle") == "running":
            logger.info(
                "Guidance turn deferred: thread %s already has an in-flight turn; "
                "guidance message %s remains persisted.",
                thread_id,
                message_id,
            )
            return False

        request = ClaudeAgentRunRequest(
            user_id=str(actor_id),
            thread_id=thread_id,
            resume=True,
            model=resolve_platform_model_alias(actor_id),
            message_id=message_id,
            message_parts=parts,
            message_metadata=metadata,
        )

        async def _drain() -> None:
            try:
                async for _frame in claude_agent_thread_factory.run_streaming(request):
                    pass
            except Exception:
                logger.exception(
                    "Guidance turn failed for thread_id=%s message_id=%s",
                    thread_id,
                    message_id,
                )

        asyncio.create_task(_drain())
        return True

    return dispatch
