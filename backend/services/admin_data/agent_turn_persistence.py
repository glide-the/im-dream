# [Input] A server-constructed, entity-bound Admin persistence owner.
# [Output] Marker base accepted by the shared Claude Agent Service and ThreadFactory.
# [Pos] Internal composition type; browser DTOs and Runtime children cannot construct it.
# [Sync] 2026-09-15: share the Chat grant and Reflections RTA persistence interface.
"""Explicit marker for server-owned Claude turn persistence compositions."""


class AdminAgentTurnPersistence:
    """Marker implemented only by reviewed server-side persistence owners."""


__all__ = ["AdminAgentTurnPersistence"]
