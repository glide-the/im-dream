# [Input] Legacy unit persistence adapter and its already assembled Thread binding.
# [Output] Explicit fake Admin continuation replies and in-memory storage for legacy callback tests.
# [Pos] Test-only dependency injection; actual continuation protocol uses separate Runtime/PG contracts.
# [Sync] 2026-11-04: keep legacy persistence/SSE assertions independent of new filesystem and Admin fixtures.
import json
from types import SimpleNamespace


class UnitContinuationStorage:
    def __init__(self, **kwargs):
        pass
    def prepare(self, *args, **kwargs):
        pass
    def checkpoint(self, *args, **kwargs):
        pass
    def close(self):
        pass


def bind_continuation_fixture(execution, *, persist_user=True):
    owner = execution.request.admin_turn_persistence
    from claude_agent.service import _AGENT_RUNTIME_CONTRACT_VERSION
    values = execution.resume_existing_session or {}
    def snapshot(**kwargs):
        return SimpleNamespace(thread=SimpleNamespace(claude_session_id=values.get("claude_session_id"), agent_contract_version=values.get("agent_contract_version", _AGENT_RUNTIME_CONTRACT_VERSION)), messages=[], history_digest="0" * 64)
    def claim(*, actor_id, input_dto):
        if persist_user and not execution.request.user_message_pre_persisted:
            owner.persist_user(actor_id=actor_id, thread_id=input_dto.thread_id, message_id=input_dto.message_id,
                parts=json.loads(input_dto.parts_json), metadata=json.loads(input_dto.metadata_json) if input_dto.metadata_json else None)
        return SimpleNamespace(dispatch_turn_id=input_dto.dispatch_turn_id, revision=1)
    def progress(*, actor_id, input_dto):
        return SimpleNamespace(dispatch_turn_id=input_dto.dispatch_turn_id, revision=input_dto.expected_revision + 1)
    owner.continuation_snapshot = snapshot
    owner.continuation_claim = claim
    owner.continuation_progress = progress
