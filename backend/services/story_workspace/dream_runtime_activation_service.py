# [Input] Admin Registry108 activation failures reported by the Dream Runtime coordinator.
# [Output] Stable product error codes and a bounded activation exception.
# [Pos] Pure Dream Runtime activation contract; Admin owns persistence and transactions.
# [Sync] 2026-09-16: remove the zero-caller SQL activation service after Registry108 adoption.
"""Stable Dream Runtime activation errors shared by the Admin-backed coordinator."""

from __future__ import annotations


DREAM_RUNTIME_INIT_INVALID = "DREAM_RUNTIME_INIT_INVALID"
DREAM_RUNTIME_NOT_READY = "DREAM_RUNTIME_NOT_READY"


class StoryWorkspaceDreamRuntimeActivationError(RuntimeError):
    """Expose bounded Runtime activation failures without persistence details."""

    def __init__(self, code: str, summary: str) -> None:
        self.code = code
        super().__init__(summary)
