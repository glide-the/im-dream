# [Sync] 2026-11-04: share fail-closed, entity-bound continuation persistence.
# [Input] A server-constructed, entity-bound Admin persistence owner.
# [Output] Marker base accepted by the shared Claude Agent Service and ThreadFactory.
# [Sync] 2026-10-23: allow an explicit task-bound Notion Read runtime override.
# [Pos] Internal composition type; browser DTOs and Runtime children cannot construct it.
# [Sync] 2026-10-26: expose a default-empty committed Dream confirmation read for original post-turn recovery.
# [Sync] 2026-09-15: share the Chat grant and Reflections RTA persistence interface.
# [Sync] 2026-10-13: image support is optional; Reflections retains its original six-operation authority.
"""Explicit marker for server-owned Claude turn persistence compositions."""


class AdminAgentTurnPersistence:
    """Marker implemented only by reviewed server-side persistence owners."""

    def _continuation_access_token(self, *, actor_id: str, thread_id: str) -> str:
        raise NotImplementedError("A bound continuation authority is required")

    def continuation_snapshot(self, *, actor_id: str, thread_id: str, message_id: str | None, dispatch_turn_id: str | None):
        from .continuation_data import SnapshotInput, RESUME_SNAPSHOT, execute
        with self._write_lock:
            token = self._continuation_access_token(actor_id=actor_id, thread_id=thread_id)
            return execute(self._client, RESUME_SNAPSHOT, SnapshotInput(thread_id=thread_id, message_id=message_id, dispatch_turn_id=dispatch_turn_id), self._request_id_factory(), access_token=token)

    def continuation_claim(self, *, actor_id: str, input_dto):
        from .continuation_data import CLAIM_CONTINUATION, execute
        with self._write_lock:
            token = self._continuation_access_token(actor_id=actor_id, thread_id=input_dto.thread_id)
            return execute(self._client, CLAIM_CONTINUATION, input_dto, self._request_id_factory(), access_token=token).entry

    def continuation_progress(self, *, actor_id: str, input_dto):
        from .continuation_data import CONTINUATION_PROGRESS, execute
        with self._write_lock:
            token = self._continuation_access_token(actor_id=actor_id, thread_id=input_dto.thread_id)
            return execute(self._client, CONTINUATION_PROGRESS, input_dto, self._request_id_factory(), access_token=token).entry

    def notion_turn_runtime(self, *, actor_id: str, thread_id: str):
        """Return a task-specific Notion adapter, or use normal Chat projection."""
        return None

    def image_turn_data(self, *, actor_id: str, thread_id: str):
        """Return no image capability unless the reviewed owner implements it."""
        return None

    def completed_dream_confirmation_text(self, *, actor_id: str, thread_id: str, message_id: str) -> str | None:
        """Return no committed Dream reply for owners without that domain."""
        return None


__all__ = ["AdminAgentTurnPersistence"]
