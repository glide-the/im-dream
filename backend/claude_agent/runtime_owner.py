# [Input] The application's existing ThreadFactory or the server composition root.
# [Output] The actual process-owned Factory for unchanged HTTP and workflow consumers.
# [Pos] Startup ownership seam; iOS binds its factory before route assembly without importing server credentials.
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .thread_factory import ClaudeAgentThreadFactory

_bound_factory: ClaudeAgentThreadFactory | None = None


def bind_thread_factory(factory: ClaudeAgentThreadFactory) -> None:
    global _bound_factory
    if factory is None or (_bound_factory is not None and _bound_factory is not factory):
        raise RuntimeError("DREAM_AGENT_OWNER_ALREADY_BOUND")
    _bound_factory = factory


def get_thread_factory() -> ClaudeAgentThreadFactory:
    if _bound_factory is not None:
        return _bound_factory
    if sys.platform == "ios":
        raise RuntimeError("DREAM_AGENT_OWNER_UNAVAILABLE")
    from agent_factory import claude_agent_thread_factory
    return claude_agent_thread_factory
