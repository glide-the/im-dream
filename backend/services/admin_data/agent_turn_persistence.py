# [Input] A server-constructed, entity-bound Admin persistence owner.
# [Output] Marker base accepted by the shared Claude Agent Service and ThreadFactory.
# [Sync] 2026-10-23: allow an explicit task-bound Notion Read runtime override.
# [Pos] Internal composition type; browser DTOs and Runtime children cannot construct it.
# [Sync] 2026-09-15: share the Chat grant and Reflections RTA persistence interface.
# [Sync] 2026-10-13: image support is optional; Reflections retains its original six-operation authority.
"""Explicit marker for server-owned Claude turn persistence compositions."""


class AdminAgentTurnPersistence:
    """Marker implemented only by reviewed server-side persistence owners."""

    def notion_turn_runtime(self, *, actor_id: str, thread_id: str):
        """Return a task-specific Notion adapter, or use normal Chat projection."""
        return None

    def image_turn_data(self, *, actor_id: str, thread_id: str):
        """Return no image capability unless the reviewed owner implements it."""
        return None


__all__ = ["AdminAgentTurnPersistence"]
