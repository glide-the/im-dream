"""Crash-recovery contracts for server-only Dream Episode commands."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from services.deck import story_workflow_gateway as gateway_module
from services.story_workspace.dream_internal_command_service import (
    StoryWorkspaceDreamInternalCommandError,
)
from story_workspace.contracts import StoryWorkspaceDreamRunContext


RUN_ID = "run_" + "a" * 32
LEAF_RUN_ID = "run_" + "b" * 32
THREAD_ID = "thread-recovery"
ACTOR_ID = "7"


def _context(run_id: str = RUN_ID) -> StoryWorkspaceDreamRunContext:
    return StoryWorkspaceDreamRunContext(
        workflow_run_id=run_id,
        thread_id=THREAD_ID,
        deck_id="deck-1",
        deck_plugin_id="drama-forge",
        deck_plugin_version="1.0.0",
        deck_plugin_binding_id="binding-1",
        binding_revision=1,
        deck_runtime_snapshot_id="snapshot-1",
        runtime_plugin_lock_id="lock-1",
    )


def _provenance() -> dict:
    return {
        "schema": "story-workspace-episode-action/v1",
        "workflow_run_id": RUN_ID,
        "thread_id": THREAD_ID,
        "actor_id": ACTOR_ID,
        "action": "write_script",
        "episode_uid": "c" * 32,
        "input_revision": None,
        "expected_facts_revision": None,
        "expected_manifest_revision": None,
        "expected_workflow_revision": None,
    }


def _row(*, provenance: object = None) -> dict:
    metadata = {
        "kind": "story-workspace-dream-agent-user",
        "visibility": "system-hidden",
        "story_workspace_run_id": RUN_ID,
        "actor_id": ACTOR_ID,
        "thread_id": THREAD_ID,
        "idempotency_key": "recover-key",
        "command_fingerprint": "sha256:" + "1" * 64,
        "dispatch_status": "dispatching",
        "dispatch_claim_id": "claim-expired",
        "dispatch_claim_lease_until": 0,
    }
    if provenance is not None:
        metadata["story_workspace_episode_action"] = provenance
    return {
        "id": "dream_agent_" + "d" * 64,
        "thread_id": THREAD_ID,
        "parts": json.dumps([{"type": "text", "text": "继续第一集"}]),
        "metadata": json.dumps(metadata, sort_keys=True, separators=(",", ":")),
        "created_at": "2026-08-11T00:00:00Z",
    }


class _Result:
    def __init__(self, *, rows=None, row=None, rowcount: int = 0) -> None:
        self._rows = list(rows or [])
        self._row = row
        self.rowcount = rowcount

    def fetchall(self):
        return list(self._rows)

    def fetchone(self):
        return self._row


class _RecoveryDB:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.in_transaction = False
        self.calls: list[tuple[str, tuple]] = []
        self.quarantined: list[dict] = []
        self.closed = False

    def execute(self, statement: str, params: tuple = ()):
        normalized = " ".join(statement.split())
        self.calls.append((normalized, params))
        if normalized.startswith("SELECT id, thread_id, parts, metadata, created_at"):
            self.in_transaction = True
            return _Result(rows=self.rows)
        if normalized.startswith("SELECT id, user_id, deck_id, voice_id"):
            self.in_transaction = True
            return _Result(
                row={
                    "id": THREAD_ID,
                    "user_id": int(ACTOR_ID),
                    "deck_id": "deck-1",
                    "voice_id": None,
                }
            )
        if normalized == "BEGIN":
            self.in_transaction = True
            return _Result()
        if normalized.startswith("UPDATE chat_message SET metadata"):
            self.quarantined.append(json.loads(params[0]))
            return _Result(rowcount=1)
        raise AssertionError(normalized)

    def rollback(self) -> None:
        self.in_transaction = False

    def commit(self) -> None:
        self.in_transaction = False

    def close(self) -> None:
        self.closed = True


def _gateway() -> gateway_module.StoryWorkflowApplicationGateway:
    return gateway_module.StoryWorkflowApplicationGateway()


def test_recovery_scans_reserved_prefix_with_bound_and_passes_atomic_provenance() -> None:
    db = _RecoveryDB([_row(provenance=_provenance())])
    pending = SimpleNamespace(message_id="pending-valid")
    service = Mock()
    service.claim_message.return_value = (object(), pending)
    resolver = Mock()
    resolver.resolve.return_value = _context()
    gateway = _gateway()

    with (
        patch.object(gateway_module.database, "get_db", return_value=db),
        patch.object(
            gateway_module,
            "StoryWorkspaceDreamInternalCommandService",
            return_value=service,
        ),
        patch.object(
            gateway_module,
            "DreamRunBindingResolver",
            return_value=resolver,
        ),
        patch.object(gateway, "_dream_agent_thread_factory", return_value=object()),
    ):
        recovered = gateway._recover_dream_internal_commands_sync(1)

    assert recovered == [pending]
    claim = service.claim_message.call_args.kwargs
    assert claim["provenance"] == _provenance()
    assert claim["context"].workflow_run_id == RUN_ID
    scan_sql, scan_params = db.calls[0]
    assert "id >= %s AND id < %s" in scan_sql
    assert scan_params[:2] == ("dream_agent_", "dream_agent`")
    assert 1 <= scan_params[-1] <= 64
    assert gateway._dream_internal_recovery_cursor == (
        "2026-08-11T00:00:00Z",
        "dream_agent_" + "d" * 64,
    )
    assert db.closed


def test_recovery_quarantines_old_crash_row_without_provenance_and_never_dispatches() -> None:
    db = _RecoveryDB([_row()])
    service = Mock()
    service.claim_message.side_effect = StoryWorkspaceDreamInternalCommandError(
        "WORKFLOW_PERMISSION_DENIED",
        403,
    )
    resolver = Mock()
    resolver.resolve.return_value = _context()
    gateway = _gateway()

    with (
        patch.object(gateway_module.database, "get_db", return_value=db),
        patch.object(
            gateway_module,
            "StoryWorkspaceDreamInternalCommandService",
            return_value=service,
        ),
        patch.object(
            gateway_module,
            "DreamRunBindingResolver",
            return_value=resolver,
        ),
    ):
        assert gateway._recover_dream_internal_commands_sync(4) == []

    assert len(db.quarantined) == 1
    assert db.quarantined[0]["visibility"] == "system-hidden"
    assert db.quarantined[0]["dispatch_status"] == "failed"
    assert db.quarantined[0]["dispatch_error_code"] == (
        "DREAM_AGENT_PROVENANCE_INVALID"
    )


def test_recovery_never_revives_a_superseded_retry_ancestor() -> None:
    db = _RecoveryDB([_row(provenance=_provenance())])
    service = Mock()
    resolver = Mock()
    resolver.resolve.return_value = _context(LEAF_RUN_ID)
    gateway = _gateway()

    with (
        patch.object(gateway_module.database, "get_db", return_value=db),
        patch.object(
            gateway_module,
            "StoryWorkspaceDreamInternalCommandService",
            return_value=service,
        ),
        patch.object(
            gateway_module,
            "DreamRunBindingResolver",
            return_value=resolver,
        ),
    ):
        assert gateway._recover_dream_internal_commands_sync(4) == []

    service.claim_message.assert_not_called()
    assert db.quarantined[0]["dispatch_error_code"] == (
        "DREAM_AGENT_BINDING_INVALID"
    )
