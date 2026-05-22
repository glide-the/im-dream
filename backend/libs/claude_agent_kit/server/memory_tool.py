# [Input] Consume server-bound PAWKEYLAND_MEM0_* env and the current user message.
# [Output] Provide zero-argument shared-story recall for the Claude Agent memory MCP namespace.
# [Pos] tool-definition node in libs/claude_agent_kit/server
# [Sync] 2026-05-09: expose app Mem0 recall as a server-owned zero-argument tool.
# [Sync] 2026-05-10: report missing Mem0 runtime config as an unavailable tool, not zero recall.
# [Sync] 2026-05-10: use policy-expanded current-turn query for explicit shared-story recall.

from __future__ import annotations

import json
import os

from pydantic import BaseModel, ConfigDict

from infrastructure.mem0_gateway import get_default_mem0_gateway
from libs.utils.env import read_int_env
from libs.utils.policy_loader import expand_memory_recall_query


MEMORY_TOOL_NAME = "recall_shared_stories"


class MemoryNoInput(BaseModel):
    """No Agent-facing parameters; server env binds the memory namespace and query."""

    model_config = ConfigDict(extra="forbid")


def allowed_memory_tool_names() -> list[str]:
    """Return fully-qualified allowed tool names for Claude Code options."""

    return [f"mcp__memory__{MEMORY_TOOL_NAME}"]


async def recall_shared_stories_handler() -> str:
    """Search Mem0 for current user/pet shared stories and return compact JSON."""

    mem0_user_id = str(os.getenv("PAWKEYLAND_MEM0_USER_ID", "")).strip()
    user_message = str(os.getenv("PAWKEYLAND_AGENT_USER_MESSAGE", "")).strip()
    top_k = max(1, read_int_env("PAWKEYLAND_MEM0_TOP_K", 5))
    if not mem0_user_id or not user_message:
        return json.dumps(
            {
                "ok": False,
                "tool_intent": MEMORY_TOOL_NAME,
                "error": "memory_context_missing",
                "shared_stories": [],
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )

    gateway = get_default_mem0_gateway()
    if not gateway.is_configured():
        return json.dumps(
            {
                "ok": False,
                "tool_intent": MEMORY_TOOL_NAME,
                "error": "mem0_not_configured",
                "shared_stories": [],
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )

    stories = gateway.search_shared_stories(
        mem0_user_id=mem0_user_id,
        query=expand_memory_recall_query(user_message),
        top_k=top_k,
    )
    return json.dumps(
        {
            "ok": True,
            "tool_intent": MEMORY_TOOL_NAME,
            "shared_stories": stories,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


__all__ = [
    "MEMORY_TOOL_NAME",
    "MemoryNoInput",
    "allowed_memory_tool_names",
    "recall_shared_stories_handler",
]
