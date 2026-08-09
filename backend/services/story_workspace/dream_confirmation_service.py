"""Persist one Dream confirmation and queue the original Chat Agent.

The confirmation is a hidden ``chat_message`` user turn. PostgreSQL persistence
is atomic (message insert plus thread touch) and idempotent without adding a
table or changing DDL. Dream files live on a separate filesystem durability
domain, so their revisions are read once before and once while holding the
PostgreSQL write transaction; the command retains the accepted base revisions so
the Agent must apply them with the file protocol's own compare-and-swap rules.
"""

from __future__ import annotations

from psycopg import Error as PostgresError

import asyncio
from dataclasses import dataclass
import hashlib
import json
import logging
import math
import time
from typing import Any, Awaitable, Callable, Optional, Protocol
from uuid import uuid4

try:
    from models.workflow_run import WorkflowRun
    from story_workspace.contracts import (
        STORY_WORKSPACE_DREAM_RELATIONS_MAX,
        STORY_WORKSPACE_DREAM_REQUIRED_STAGES,
        StoryWorkspaceDreamConfirmationAccepted,
        StoryWorkspaceDreamConfirmationCommand,
        StoryWorkspaceDreamFilesResponse,
        StoryWorkspaceDreamRunContext,
        StoryWorkspaceDreamStage,
    )
except ModuleNotFoundError:  # Support repository-root package imports.
    from backend.models.workflow_run import WorkflowRun
    from backend.story_workspace.contracts import (
        STORY_WORKSPACE_DREAM_RELATIONS_MAX,
        STORY_WORKSPACE_DREAM_REQUIRED_STAGES,
        StoryWorkspaceDreamConfirmationAccepted,
        StoryWorkspaceDreamConfirmationCommand,
        StoryWorkspaceDreamFilesResponse,
        StoryWorkspaceDreamRunContext,
        StoryWorkspaceDreamStage,
    )


_logger = logging.getLogger(__name__)

STORY_WORKSPACE_DREAM_CONFIRMATION_METADATA_KIND = (
    "story-workspace-dream-confirmation"
)
STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCH_PENDING = "pending"
STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCHING = "dispatching"
STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCHED = "dispatched"
_DISPATCH_CLAIM_ID = "dispatch_claim_id"
_DISPATCH_CLAIM_LEASE_UNTIL = "dispatch_claim_lease_until"
_DISPATCH_ACK_CLAIM_SHA256 = "dispatch_ack_claim_sha256"
_EDITABLE_FIELDS = frozenset({"displayName", "summary", "relations"})


class StoryWorkspaceDreamConfirmationError(RuntimeError):
    """Allowlisted public failure for the Dream confirmation boundary."""

    def __init__(self, code: str, status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


class StoryWorkspaceDreamRunReader(Protocol):
    def __call__(self, run_id: str) -> WorkflowRun: ...


class StoryWorkspaceDreamProjectionReader(Protocol):
    def __call__(
        self,
        workflow_run: WorkflowRun,
        thread_id: str,
    ) -> StoryWorkspaceDreamFilesResponse: ...


StoryWorkspaceDreamConfirmationDispatcher = Callable[
    [str, str, str, list, dict],
    Awaitable[bool],
]


@dataclass(frozen=True)
class StoryWorkspaceDreamConfirmationDispatch:
    thread_id: str
    actor_id: str
    message_id: str
    parts: list
    metadata: dict


@dataclass(frozen=True)
class StoryWorkspacePersistedDreamConfirmation:
    accepted: StoryWorkspaceDreamConfirmationAccepted
    dispatch: Optional[StoryWorkspaceDreamConfirmationDispatch]


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sha256(value: Any) -> str:
    return "sha256:" + hashlib.sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def story_workspace_dream_confirmation_message_id(
    actor_id: str,
    run_id: str,
    idempotency_key: str,
) -> str:
    """Return a deterministic PK scoped by actor, run, and client key."""

    digest = hashlib.sha256(
        _canonical_json({
            "actor": str(actor_id),
            "storyWorkspaceRunId": run_id,
            "idempotencyKey": idempotency_key,
        }).encode("utf-8")
    ).hexdigest()
    return f"dream_confirm_{digest}"


def _command_wire(
    payload: StoryWorkspaceDreamConfirmationCommand,
) -> dict[str, Any]:
    return payload.model_dump(mode="json", by_alias=True)


def _command_fingerprint(
    actor_id: str,
    payload: StoryWorkspaceDreamConfirmationCommand,
) -> str:
    return _sha256({"actor": str(actor_id), "command": _command_wire(payload)})


def _hidden_parts(
    payload: StoryWorkspaceDreamConfirmationCommand,
) -> list[dict[str, str]]:
    """Build an Agent-readable text part containing the complete wire command."""

    envelope = {
        "kind": STORY_WORKSPACE_DREAM_CONFIRMATION_METADATA_KIND,
        "command": _command_wire(payload),
        "instructions": {
            "first": (
                "Write the edits to canonical workspace files and update each "
                "affected Dream stage revision."
            ),
            "then": "Continue the same plugin in this Chat thread.",
            "confirmation": "Do not ask for another confirmation.",
        },
    }
    return [{"type": "text", "text": _canonical_json(envelope)}]


def _validate_edit_value(field: str, value: Any) -> None:
    if field == "displayName":
        if (
            not isinstance(value, str)
            or not value.strip()
            or len(value) > 200
        ):
            raise StoryWorkspaceDreamConfirmationError(
                "OUTPUT_CONTRACT_INVALID", 422
            )
        return
    if field == "summary":
        if value is not None and (
            not isinstance(value, str) or len(value) > 4000
        ):
            raise StoryWorkspaceDreamConfirmationError(
                "OUTPUT_CONTRACT_INVALID", 422
            )
        return
    if field == "relations":
        if not isinstance(value, list) or len(value) > STORY_WORKSPACE_DREAM_RELATIONS_MAX:
            raise StoryWorkspaceDreamConfirmationError(
                "OUTPUT_CONTRACT_INVALID", 422
            )
        if any(
            not isinstance(identifier, str)
            or not identifier.strip()
            or len(identifier) > 128
            for identifier in value
        ):
            raise StoryWorkspaceDreamConfirmationError(
                "OUTPUT_CONTRACT_INVALID", 422
            )
        return
    raise StoryWorkspaceDreamConfirmationError("OUTPUT_CONTRACT_INVALID", 422)


def _validate_projection(
    projection: StoryWorkspaceDreamFilesResponse,
    payload: StoryWorkspaceDreamConfirmationCommand,
) -> None:
    if (
        projection.story_workspace_run_id != payload.story_workspace_run_id
        or projection.thread_id != payload.thread_id
    ):
        raise StoryWorkspaceDreamConfirmationError("CONFIG_VERSION_DRIFT", 409)

    required = set(STORY_WORKSPACE_DREAM_REQUIRED_STAGES)
    if set(projection.stages) != required:
        raise StoryWorkspaceDreamConfirmationError("CONFIG_VERSION_DRIFT", 409)
    current_revisions = {
        stage: projection.stages[stage].revision for stage in required
    }
    if current_revisions != payload.base_revisions:
        raise StoryWorkspaceDreamConfirmationError("CONFIG_VERSION_DRIFT", 409)

    entity_ids = {
        stage: {item.entity_id for item in projection.stages[stage].items}
        for stage in required
    }
    for edit in payload.edits:
        if edit.entity_id not in entity_ids[edit.stage]:
            raise StoryWorkspaceDreamConfirmationError(
                "OUTPUT_CONTRACT_INVALID", 422
            )
        if set(edit.fields) - _EDITABLE_FIELDS:
            raise StoryWorkspaceDreamConfirmationError(
                "OUTPUT_CONTRACT_INVALID", 422
            )
        for field, value in edit.fields.items():
            _validate_edit_value(field, value)


def _decode_metadata(raw: Any) -> Optional[dict[str, Any]]:
    if not isinstance(raw, str):
        return None
    try:
        decoded = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return decoded if isinstance(decoded, dict) else None


def _decode_parts(raw: Any) -> Optional[list[Any]]:
    if not isinstance(raw, str):
        return None
    try:
        decoded = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return decoded if isinstance(decoded, list) else None


def _confirmation_metadata_matches_actor_run(
    metadata: Any,
    *,
    actor_id: str,
    run_id: str,
) -> bool:
    return (
        isinstance(metadata, dict)
        and metadata.get("kind")
        == STORY_WORKSPACE_DREAM_CONFIRMATION_METADATA_KIND
        and metadata.get("actor") == actor_id
        and metadata.get("story_workspace_run_id") == run_id
    )


def _confirmation_metadata_matches_scope(
    metadata: Any,
    *,
    actor_id: str,
    thread_id: str,
    run_id: str,
) -> bool:
    return (
        _confirmation_metadata_matches_actor_run(
            metadata,
            actor_id=actor_id,
            run_id=run_id,
        )
        and metadata.get("thread_id") == thread_id
    )


def story_workspace_read_dream_confirmation_fact(
    db: Any,
    *,
    actor_id: str,
    thread_id: str,
    run_id: str,
) -> tuple[bool, bool]:
    """Read the actor/thread/run confirmation fact from existing message audit."""

    rows = db.execute(
        "SELECT metadata FROM chat_message "
        "WHERE thread_id = %s AND role = 'user' ORDER BY created_at ASC, id ASC",
        (thread_id,),
    ).fetchall()
    accepted = False
    dispatched = False
    for row in rows:
        metadata = _decode_metadata(row["metadata"])
        if not _confirmation_metadata_matches_scope(
            metadata,
            actor_id=str(actor_id),
            thread_id=thread_id,
            run_id=run_id,
        ):
            continue
        accepted = True
        dispatched = dispatched or (
            metadata.get("dispatch_status")
            == STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCHED
        )
    return accepted, dispatched


def story_workspace_mark_dream_confirmation_dispatched(
    db: Any,
    dispatch: StoryWorkspaceDreamConfirmationDispatch,
) -> bool:
    """Acknowledge only the coordinator that owns the durable claim."""

    try:
        db.execute("BEGIN")
        row = db.execute(
            "SELECT thread_id, role, metadata FROM chat_message WHERE id = %s",
            (dispatch.message_id,),
        ).fetchone()
        if row is None:
            raise StoryWorkspaceDreamConfirmationError("RESULT_COMMIT_FAILED", 503)
        metadata = _decode_metadata(row["metadata"])
        expected = dispatch.metadata
        expected_claim_id = (
            expected.get(_DISPATCH_CLAIM_ID)
            if isinstance(expected, dict)
            else None
        )
        valid = (
            row["thread_id"] == dispatch.thread_id
            and row["role"] == "user"
            and isinstance(metadata, dict)
            and isinstance(expected, dict)
            and metadata.get("kind")
            == STORY_WORKSPACE_DREAM_CONFIRMATION_METADATA_KIND
            and metadata.get("actor") == dispatch.actor_id
            and metadata.get("thread_id") == dispatch.thread_id
            and metadata.get("story_workspace_run_id")
            == expected.get("story_workspace_run_id")
            and metadata.get("request_id") == expected.get("request_id")
            and metadata.get("command_fingerprint")
            == expected.get("command_fingerprint")
            and isinstance(expected_claim_id, str)
            and bool(expected_claim_id)
        )
        if not valid:
            raise StoryWorkspaceDreamConfirmationError("IDEMPOTENCY_CONFLICT", 409)
        status = metadata.get(
            "dispatch_status",
            STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCH_PENDING,
        )
        if status == STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCHED:
            if metadata.get(_DISPATCH_ACK_CLAIM_SHA256) != _sha256(
                expected_claim_id
            ):
                raise StoryWorkspaceDreamConfirmationError(
                    "IDEMPOTENCY_CONFLICT", 409
                )
            db.commit()
            return True
        if (
            status != STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCHING
            or metadata.get(_DISPATCH_CLAIM_ID) != expected_claim_id
        ):
            raise StoryWorkspaceDreamConfirmationError("IDEMPOTENCY_CONFLICT", 409)
        metadata["dispatch_status"] = STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCHED
        metadata[_DISPATCH_ACK_CLAIM_SHA256] = _sha256(expected_claim_id)
        metadata.pop(_DISPATCH_CLAIM_ID, None)
        metadata.pop(_DISPATCH_CLAIM_LEASE_UNTIL, None)
        updated = db.execute(
            "UPDATE chat_message SET metadata = %s WHERE id = %s",
            (_canonical_json(metadata), dispatch.message_id),
        )
        if updated.rowcount != 1:
            raise StoryWorkspaceDreamConfirmationError("RESULT_COMMIT_FAILED", 503)
        db.commit()
        return True
    except StoryWorkspaceDreamConfirmationError:
        if db.in_transaction:
            db.rollback()
        raise
    except PostgresError as exc:
        if db.in_transaction:
            db.rollback()
        raise StoryWorkspaceDreamConfirmationError(
            "RESULT_COMMIT_FAILED", 503
        ) from exc


def _valid_lease_deadline(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) >= 0
    )


def _decode_confirmation_dispatch_row(
    row: Any,
) -> Optional[StoryWorkspaceDreamConfirmationDispatch]:
    """Decode one durable work item, rejecting forged or malformed audit data."""

    metadata = _decode_metadata(row["metadata"])
    parts = _decode_parts(row["parts"])
    actor_id = str(row["user_id"])
    if not (
        row["role"] == "user"
        and isinstance(metadata, dict)
        and metadata.get("kind")
        == STORY_WORKSPACE_DREAM_CONFIRMATION_METADATA_KIND
        and metadata.get("actor") == actor_id
        and metadata.get("thread_id") == row["thread_id"]
        and isinstance(parts, list)
    ):
        return None
    run_id = metadata.get("story_workspace_run_id")
    idempotency_key = metadata.get("idempotency_key")
    request_id = metadata.get("request_id")
    fingerprint = metadata.get("command_fingerprint")
    if not all(
        isinstance(value, str) and bool(value)
        for value in (run_id, idempotency_key, request_id, fingerprint)
    ):
        return None
    if row["id"] != story_workspace_dream_confirmation_message_id(
        actor_id,
        run_id,
        idempotency_key,
    ):
        return None
    if len(parts) != 1 or not isinstance(parts[0], dict):
        return None
    text = parts[0].get("text")
    if parts[0].get("type") != "text" or not isinstance(text, str):
        return None
    try:
        envelope = json.loads(text)
    except (TypeError, ValueError):
        return None
    command = envelope.get("command") if isinstance(envelope, dict) else None
    if not (
        isinstance(envelope, dict)
        and envelope.get("kind")
        == STORY_WORKSPACE_DREAM_CONFIRMATION_METADATA_KIND
        and isinstance(command, dict)
        and command.get("storyWorkspaceRunId") == run_id
        and command.get("threadId") == row["thread_id"]
        and command.get("idempotencyKey") == idempotency_key
        and _sha256({"actor": actor_id, "command": command}) == fingerprint
    ):
        return None
    return StoryWorkspaceDreamConfirmationDispatch(
        thread_id=row["thread_id"],
        actor_id=actor_id,
        message_id=row["id"],
        parts=parts,
        metadata=metadata,
    )


def _story_workspace_dream_confirmation_has_run_scope(
    db: Any,
    dispatch: StoryWorkspaceDreamConfirmationDispatch,
) -> bool:
    run_scope = db.execute(
        "SELECT run.id FROM workflow_runs AS run "
        "JOIN story_workspace_workspaces AS workspace "
        "ON workspace.id = run.workspace_id "
        "WHERE run.id = %s AND run.created_by = %s "
        "AND run.source_voice_thread_id = %s AND workspace.owner_id = %s",
        (
            dispatch.metadata["story_workspace_run_id"],
            dispatch.actor_id,
            dispatch.thread_id,
            int(dispatch.actor_id),
        ),
    ).fetchone()
    return run_scope is not None


def _story_workspace_dispatch_matches_expected(
    current: StoryWorkspaceDreamConfirmationDispatch,
    expected: StoryWorkspaceDreamConfirmationDispatch,
) -> bool:
    return (
        current.message_id == expected.message_id
        and current.thread_id == expected.thread_id
        and current.actor_id == expected.actor_id
        and current.metadata.get("story_workspace_run_id")
        == expected.metadata.get("story_workspace_run_id")
        and current.metadata.get("request_id")
        == expected.metadata.get("request_id")
        and current.metadata.get("command_fingerprint")
        == expected.metadata.get("command_fingerprint")
    )


def story_workspace_guard_persisted_dream_confirmation_turn(
    db: Any,
    *,
    thread_id: str,
    actor_id: str,
    message_id: str,
    parts: list,
    metadata: Optional[dict],
) -> bool:
    """Classify and verify a server-owned Dream confirmation turn.

    Confirmation messages are already persisted and claimed before the Agent
    starts. The Agent may carry an older lease snapshot while waiting for the
    per-thread lock, so persistence must validate the immutable envelope and
    claim identity without writing that stale snapshot back to PostgreSQL.

    Classification trusts the existing database row and reserved message-id
    namespace, never a request's mutable ``kind`` alone. ``False`` is returned
    only when both database and request are unambiguously ordinary Chat data.
    """

    try:
        row = db.execute(
            "SELECT message.id, message.thread_id, message.role, message.parts, "
            "message.metadata, thread.user_id "
            "FROM chat_message AS message "
            "JOIN chat_thread AS thread ON thread.id = message.thread_id "
            "WHERE message.id = %s",
            (message_id,),
        ).fetchone()
    except PostgresError as exc:
        raise StoryWorkspaceDreamConfirmationError(
            "DECK_RUNTIME_CONFIG_UNAVAILABLE", 503
        ) from exc

    raw_database_metadata = (
        _decode_metadata(row["metadata"]) if row is not None else None
    )
    reserved_message_id = (
        isinstance(message_id, str) and message_id.startswith("dream_confirm_")
    )
    database_claims_dream = reserved_message_id or (
        isinstance(raw_database_metadata, dict)
        and raw_database_metadata.get("kind")
        == STORY_WORKSPACE_DREAM_CONFIRMATION_METADATA_KIND
    )
    request_claims_dream = reserved_message_id or (
        isinstance(metadata, dict)
        and metadata.get("kind")
        == STORY_WORKSPACE_DREAM_CONFIRMATION_METADATA_KIND
    )
    if not database_claims_dream and not request_claims_dream:
        return False

    current = _decode_confirmation_dispatch_row(row) if row is not None else None
    try:
        valid = (
            current is not None
            and current.thread_id == thread_id
            and current.actor_id == str(actor_id)
            and current.message_id == message_id
            and _story_workspace_dream_confirmation_has_run_scope(db, current)
            and isinstance(parts, list)
            and isinstance(metadata, dict)
            and current.metadata.get("dispatch_status")
            == STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCHING
            and metadata.get("dispatch_status")
            == STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCHING
            and _valid_lease_deadline(
                current.metadata.get(_DISPATCH_CLAIM_LEASE_UNTIL)
            )
            and _valid_lease_deadline(
                metadata.get(_DISPATCH_CLAIM_LEASE_UNTIL)
            )
        )
    except PostgresError as exc:
        raise StoryWorkspaceDreamConfirmationError(
            "DECK_RUNTIME_CONFIG_UNAVAILABLE", 503
        ) from exc
    if not valid:
        raise StoryWorkspaceDreamConfirmationError(
            "IDEMPOTENCY_CONFLICT", 409
        )

    current_identity = {
        key: value
        for key, value in current.metadata.items()
        if key != _DISPATCH_CLAIM_LEASE_UNTIL
    }
    request_identity = {
        key: value
        for key, value in metadata.items()
        if key != _DISPATCH_CLAIM_LEASE_UNTIL
    }
    if (
        current_identity != request_identity
        or _canonical_json(current.parts) != _canonical_json(parts)
    ):
        raise StoryWorkspaceDreamConfirmationError(
            "IDEMPOTENCY_CONFLICT", 409
        )
    return True


def story_workspace_claim_dream_confirmation(
    db: Any,
    dispatch: StoryWorkspaceDreamConfirmationDispatch,
    *,
    claim_id: str,
    clock: Callable[[], float],
    lease_duration_s: float,
) -> Optional[StoryWorkspaceDreamConfirmationDispatch]:
    """Atomically acquire pending or expired confirmation work in PostgreSQL."""

    if not isinstance(claim_id, str) or not claim_id:
        raise ValueError("claim_id must be non-empty")
    if (
        not _valid_lease_deadline(lease_duration_s)
        or lease_duration_s <= 0
    ):
        raise ValueError("claim lease must use finite non-negative time")
    try:
        db.execute("BEGIN")
        row = db.execute(
            "SELECT message.id, message.thread_id, message.role, message.parts, "
            "message.metadata, thread.user_id "
            "FROM chat_message AS message "
            "JOIN chat_thread AS thread ON thread.id = message.thread_id "
            "WHERE message.id = %s",
            (dispatch.message_id,),
        ).fetchone()
        current = (
            _decode_confirmation_dispatch_row(row) if row is not None else None
        )
        if (
            current is None
            or not _story_workspace_dispatch_matches_expected(current, dispatch)
            or not _story_workspace_dream_confirmation_has_run_scope(db, current)
        ):
            db.commit()
            return None
        now_s = clock()
        if not _valid_lease_deadline(now_s):
            raise ValueError("claim clock must return finite non-negative time")
        metadata = current.metadata
        status = metadata.get(
            "dispatch_status",
            STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCH_PENDING,
        )
        if status == STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCHING:
            lease_until = metadata.get(_DISPATCH_CLAIM_LEASE_UNTIL)
            if (
                not isinstance(metadata.get(_DISPATCH_CLAIM_ID), str)
                or not _valid_lease_deadline(lease_until)
            ):
                db.commit()
                return None
            if float(lease_until) > float(now_s):
                db.commit()
                return None
        elif status != STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCH_PENDING:
            db.commit()
            return None

        claimed_metadata = dict(metadata)
        claimed_metadata["dispatch_status"] = (
            STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCHING
        )
        claimed_metadata[_DISPATCH_CLAIM_ID] = claim_id
        claimed_metadata[_DISPATCH_CLAIM_LEASE_UNTIL] = (
            float(now_s) + float(lease_duration_s)
        )
        claimed_metadata.pop(_DISPATCH_ACK_CLAIM_SHA256, None)
        updated = db.execute(
            "UPDATE chat_message SET metadata = %s WHERE id = %s",
            (_canonical_json(claimed_metadata), current.message_id),
        )
        if updated.rowcount != 1:
            raise StoryWorkspaceDreamConfirmationError(
                "RESULT_COMMIT_FAILED", 503
            )
        db.commit()
        return StoryWorkspaceDreamConfirmationDispatch(
            thread_id=current.thread_id,
            actor_id=current.actor_id,
            message_id=current.message_id,
            parts=current.parts,
            metadata=claimed_metadata,
        )
    except StoryWorkspaceDreamConfirmationError:
        if db.in_transaction:
            db.rollback()
        raise
    except PostgresError as exc:
        if db.in_transaction:
            db.rollback()
        raise StoryWorkspaceDreamConfirmationError(
            "RESULT_COMMIT_FAILED", 503
        ) from exc
    except Exception:
        if db.in_transaction:
            db.rollback()
        raise


def _story_workspace_set_dream_confirmation_claim_lease(
    db: Any,
    dispatch: StoryWorkspaceDreamConfirmationDispatch,
    *,
    clock: Callable[[], float],
    lease_duration_s: float,
) -> bool:
    """Move an owned lease using time sampled inside the write transaction."""

    expected_claim_id = dispatch.metadata.get(_DISPATCH_CLAIM_ID)
    if (
        not isinstance(expected_claim_id, str)
        or not expected_claim_id
        or not _valid_lease_deadline(lease_duration_s)
    ):
        return False
    try:
        db.execute("BEGIN")
        row = db.execute(
            "SELECT metadata FROM chat_message WHERE id = %s",
            (dispatch.message_id,),
        ).fetchone()
        metadata = _decode_metadata(row["metadata"]) if row is not None else None
        if not (
            isinstance(metadata, dict)
            and metadata.get("dispatch_status")
            == STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCHING
            and metadata.get(_DISPATCH_CLAIM_ID) == expected_claim_id
            and metadata.get("request_id")
            == dispatch.metadata.get("request_id")
            and metadata.get("command_fingerprint")
            == dispatch.metadata.get("command_fingerprint")
        ):
            db.commit()
            return False
        now_s = clock()
        if not _valid_lease_deadline(now_s):
            raise ValueError("lease clock must return finite non-negative time")
        metadata[_DISPATCH_CLAIM_LEASE_UNTIL] = (
            float(now_s) + float(lease_duration_s)
        )
        updated = db.execute(
            "UPDATE chat_message SET metadata = %s WHERE id = %s",
            (_canonical_json(metadata), dispatch.message_id),
        )
        if updated.rowcount != 1:
            raise StoryWorkspaceDreamConfirmationError(
                "RESULT_COMMIT_FAILED", 503
            )
        db.commit()
        return True
    except StoryWorkspaceDreamConfirmationError:
        if db.in_transaction:
            db.rollback()
        raise
    except PostgresError as exc:
        if db.in_transaction:
            db.rollback()
        raise StoryWorkspaceDreamConfirmationError(
            "RESULT_COMMIT_FAILED", 503
        ) from exc
    except Exception:
        if db.in_transaction:
            db.rollback()
        raise


def story_workspace_read_pending_dream_confirmations(
    db: Any,
    *,
    now_s: Optional[float] = None,
) -> list[StoryWorkspaceDreamConfirmationDispatch]:
    """Read pending plus expired-lease work from the hidden-message audit."""

    current_time = time.time() if now_s is None else float(now_s)

    rows = db.execute(
        "SELECT message.id, message.thread_id, message.role, message.parts, "
        "message.metadata, thread.user_id "
        "FROM chat_message AS message "
        "JOIN chat_thread AS thread ON thread.id = message.thread_id "
        "WHERE message.role = 'user' ORDER BY message.created_at ASC, message.id ASC"
    ).fetchall()
    pending: list[StoryWorkspaceDreamConfirmationDispatch] = []
    for row in rows:
        dispatch = _decode_confirmation_dispatch_row(row)
        if dispatch is None:
            continue
        status = dispatch.metadata.get(
            "dispatch_status",
            STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCH_PENDING,
        )
        eligible = status == STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCH_PENDING
        if status == STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCHING:
            lease_until = dispatch.metadata.get(_DISPATCH_CLAIM_LEASE_UNTIL)
            eligible = (
                isinstance(dispatch.metadata.get(_DISPATCH_CLAIM_ID), str)
                and _valid_lease_deadline(lease_until)
                and float(lease_until) <= current_time
            )
        if (
            eligible
            and _story_workspace_dream_confirmation_has_run_scope(db, dispatch)
        ):
            pending.append(dispatch)
    return pending


def story_workspace_build_dream_confirmation_turn_dispatcher(
    factory: Any | None = None,
    *,
    request_factory: Callable[..., Any] | None = None,
    context_loader: Callable[
        [str, str, dict], StoryWorkspaceDreamRunContext
    ] | None = None,
) -> StoryWorkspaceDreamConfirmationDispatcher:
    """Queue a resumed turn even while the same thread is currently running.

    ``ClaudeAgentThreadFactory.run_streaming`` owns a per-thread lock. Starting
    this drain task immediately therefore queues behind an in-flight turn and
    preserves ordering without a lifecycle pre-check that could lose work.
    """

    async def consume(
        thread_id: str,
        actor_id: str,
        message_id: str,
        parts: list,
        metadata: dict,
    ) -> bool:
        try:
            selected_factory = factory
            if selected_factory is None:
                from agent_factory import claude_agent_thread_factory

                selected_factory = claude_agent_thread_factory
            selected_request_factory = request_factory
            if selected_request_factory is None:
                from claude_agent.service import ClaudeAgentRunRequest

                selected_request_factory = ClaudeAgentRunRequest
            dream_context = (
                context_loader(thread_id, str(actor_id), metadata)
                if context_loader is not None
                else _story_workspace_load_confirmation_dream_context(
                    thread_id,
                    str(actor_id),
                    metadata,
                )
            )
            request = selected_request_factory(
                user_id=str(actor_id),
                thread_id=thread_id,
                resume=True,
                message_id=message_id,
                message_parts=parts,
                message_metadata=metadata,
                story_workspace_dream_context=dream_context,
            )
            stream = selected_factory.run_streaming(request)

            saw_message_final = False
            async for frame in stream:
                if not isinstance(frame, str):
                    continue
                data_line = next(
                    (
                        line.removeprefix("data: ")
                        for line in frame.splitlines()
                        if line.startswith("data: ")
                    ),
                    None,
                )
                if data_line is None:
                    continue
                try:
                    event = json.loads(data_line)
                except (TypeError, ValueError):
                    continue
                if not isinstance(event, dict):
                    continue
                if event.get("type") == "error":
                    return False
                if event.get("type") == "message-final":
                    saw_message_final = True
                if event.get("type") == "finish":
                    if event.get("finishReason") == "error":
                        return False
                    return saw_message_final
            return False
        except asyncio.CancelledError:
            raise
        except Exception:
            _logger.exception(
                "Dream confirmation turn failed for thread_id=%s "
                "message_id=%s",
                thread_id,
                message_id,
            )
            return False

    def dispatch(
        thread_id: str,
        actor_id: str,
        message_id: str,
        parts: list,
        metadata: dict,
    ) -> Awaitable[bool]:
        # Preserve the established fire-now callable shape while returning a
        # completion awaitable for the durable coordinator acknowledgement.
        return asyncio.create_task(
            consume(thread_id, actor_id, message_id, parts, metadata),
            name=f"dream-confirmation-turn-{message_id}",
        )

    return dispatch


def _story_workspace_load_confirmation_dream_context(
    thread_id: str,
    actor_id: str,
    metadata: dict,
) -> StoryWorkspaceDreamRunContext:
    """Rebuild trusted Dream provenance for a durable confirmation resume."""

    if metadata.get("kind") != STORY_WORKSPACE_DREAM_CONFIRMATION_METADATA_KIND:
        raise PermissionError("confirmation metadata kind is invalid")
    if (
        metadata.get("thread_id") != thread_id
        or str(metadata.get("actor") or "") != actor_id
    ):
        raise PermissionError("confirmation identity metadata is invalid")
    run_id = metadata.get("story_workspace_run_id")
    if not isinstance(run_id, str):
        raise PermissionError("confirmation workflow run is unavailable")
    if not actor_id.isdigit() or int(actor_id) <= 0:
        raise PermissionError("confirmation actor is invalid")

    import database

    db = database.get_db()
    try:
        row = db.execute(
            """
            SELECT run.id AS workflow_run_id,
                   run.source_voice_thread_id AS thread_id,
                   binding.deck_id AS deck_id,
                   run.deck_plugin_id AS deck_plugin_id,
                   run.deck_plugin_version AS deck_plugin_version,
                   run.deck_plugin_binding_id AS deck_plugin_binding_id,
                   run.binding_revision AS binding_revision,
                   run.deck_runtime_snapshot_id AS deck_runtime_snapshot_id,
                   run.runtime_plugin_lock_id AS runtime_plugin_lock_id
            FROM workflow_runs AS run
            JOIN story_workspace_workspaces AS workspace
              ON workspace.id = run.workspace_id
            JOIN deck_plugin_bindings AS binding
              ON binding.deck_plugin_binding_id = run.deck_plugin_binding_id
             AND binding.binding_revision = run.binding_revision
             AND binding.deck_plugin_id = run.deck_plugin_id
             AND binding.deck_plugin_version = run.deck_plugin_version
            WHERE run.id = %s
              AND run.source_voice_thread_id = %s
              AND run.created_by = %s
              AND workspace.owner_id = %s
            LIMIT 1
            """,
            (run_id, thread_id, actor_id, int(actor_id)),
        ).fetchone()
        if row is None:
            raise PermissionError("confirmation Dream run is unavailable")
        return StoryWorkspaceDreamRunContext.model_validate(dict(row))
    finally:
        db.close()


@dataclass(frozen=True)
class _StoryWorkspaceDreamRetryState:
    failures: int
    not_before: float


class StoryWorkspaceDreamConfirmationCoordinator:
    """Reconcile durable pending confirmations with same-thread Agent turns.

    Delivery is at least once. PostgreSQL atomically moves one message from
    ``pending`` to a leased ``dispatching`` claim before an Agent starts. A
    process crash after stream completion but before acknowledgement can replay
    after lease expiry, but two live coordinators cannot consume one fresh
    claim concurrently.
    """

    def __init__(
        self,
        db_factory: Callable[[], Any],
        *,
        dispatcher_factory: Callable[
            [], StoryWorkspaceDreamConfirmationDispatcher
        ] = (
            story_workspace_build_dream_confirmation_turn_dispatcher
        ),
        reconcile_interval_s: float = 2.0,
        clock: Callable[[], float] = time.monotonic,
        lease_clock: Callable[[], float] = time.time,
        lease_duration_s: float = 120.0,
        lease_renew_interval_s: Optional[float] = None,
        claim_id_factory: Callable[[], str] = lambda: uuid4().hex,
        retry_base_s: float = 2.0,
        retry_max_s: float = 60.0,
    ) -> None:
        self._db_factory = db_factory
        self._dispatcher_factory = dispatcher_factory
        self._reconcile_interval_s = max(float(reconcile_interval_s), 0.01)
        self._clock = clock
        self._lease_clock = lease_clock
        if (
            not _valid_lease_deadline(lease_duration_s)
            or float(lease_duration_s) <= 0
        ):
            raise ValueError("lease_duration_s must be finite and positive")
        self._lease_duration_s = max(float(lease_duration_s), 0.1)
        default_renew_interval_s = max(
            min(self._lease_duration_s / 3.0, 30.0),
            0.01,
        )
        if lease_renew_interval_s is None:
            self._lease_renew_interval_s = default_renew_interval_s
        else:
            if (
                not _valid_lease_deadline(lease_renew_interval_s)
                or float(lease_renew_interval_s) <= 0
            ):
                raise ValueError(
                    "lease_renew_interval_s must be finite and positive"
                )
            self._lease_renew_interval_s = min(
                max(float(lease_renew_interval_s), 0.01),
                default_renew_interval_s,
            )
        self._claim_id_factory = claim_id_factory
        self._retry_base_s = max(float(retry_base_s), 0.01)
        self._retry_max_s = max(float(retry_max_s), self._retry_base_s)
        self._in_flight: dict[str, asyncio.Task[None]] = {}
        self._retry_state: dict[str, _StoryWorkspaceDreamRetryState] = {}
        self._loop_task: Optional[asyncio.Task[None]] = None
        self._stop_event: Optional[asyncio.Event] = None

    def start(self) -> None:
        if self._loop_task is not None and not self._loop_task.done():
            return
        self._stop_event = asyncio.Event()
        self._loop_task = asyncio.create_task(
            self._run(),
            name="dream-confirmation-reconciler",
        )

    async def stop(self) -> None:
        stop_event = self._stop_event
        if stop_event is not None:
            stop_event.set()
        loop_task = self._loop_task
        if loop_task is not None and not loop_task.done():
            loop_task.cancel()
        tasks = list(self._in_flight.values())
        for task in tasks:
            task.cancel()
        if loop_task is not None:
            await asyncio.gather(loop_task, return_exceptions=True)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._loop_task = None
        self._stop_event = None

    def schedule(
        self,
        dispatch: Optional[StoryWorkspaceDreamConfirmationDispatch],
    ) -> bool:
        if dispatch is None or dispatch.message_id in self._in_flight:
            return False
        retry = self._retry_state.get(dispatch.message_id)
        if retry is not None and self._clock() < retry.not_before:
            return False
        claimed = self._claim_sync(dispatch)
        if claimed is None:
            return False
        task = asyncio.create_task(
            self._consume_and_ack(claimed),
            name=f"dream-confirmation-{claimed.message_id}",
        )
        # Occupy the key synchronously before the event loop can run a scan.
        self._in_flight[claimed.message_id] = task
        return True

    async def reconcile_once(self) -> int:
        pending = await asyncio.to_thread(self._read_pending_sync)
        return sum(1 for dispatch in pending if self.schedule(dispatch))

    async def wait_for_idle(self) -> None:
        while self._in_flight:
            await asyncio.gather(
                *list(self._in_flight.values()),
                return_exceptions=True,
            )

    def _read_pending_sync(
        self,
    ) -> list[StoryWorkspaceDreamConfirmationDispatch]:
        db = self._db_factory()
        try:
            return story_workspace_read_pending_dream_confirmations(
                db,
                now_s=self._lease_clock(),
            )
        finally:
            db.close()

    def _claim_sync(
        self,
        dispatch: StoryWorkspaceDreamConfirmationDispatch,
    ) -> Optional[StoryWorkspaceDreamConfirmationDispatch]:
        db = self._db_factory()
        try:
            return story_workspace_claim_dream_confirmation(
                db,
                dispatch,
                claim_id=self._claim_id_factory(),
                clock=self._lease_clock,
                lease_duration_s=self._lease_duration_s,
            )
        finally:
            db.close()

    def _mark_dispatched_sync(
        self,
        dispatch: StoryWorkspaceDreamConfirmationDispatch,
    ) -> bool:
        db = self._db_factory()
        try:
            return story_workspace_mark_dream_confirmation_dispatched(db, dispatch)
        finally:
            db.close()

    def _set_claim_lease_sync(
        self,
        dispatch: StoryWorkspaceDreamConfirmationDispatch,
        lease_duration_s: float,
    ) -> bool:
        db = self._db_factory()
        try:
            return _story_workspace_set_dream_confirmation_claim_lease(
                db,
                dispatch,
                clock=self._lease_clock,
                lease_duration_s=lease_duration_s,
            )
        finally:
            db.close()

    def _record_retry(self, message_id: str) -> float:
        previous = self._retry_state.get(message_id)
        failures = 1 if previous is None else previous.failures + 1
        exponent = min(failures - 1, 30)
        delay = min(
            self._retry_max_s,
            self._retry_base_s * (2 ** exponent),
        )
        self._retry_state[message_id] = _StoryWorkspaceDreamRetryState(
            failures=failures,
            not_before=self._clock() + delay,
        )
        return delay

    async def _defer_owned_claim(
        self,
        dispatch: StoryWorkspaceDreamConfirmationDispatch,
        delay_s: float,
    ) -> None:
        try:
            await asyncio.to_thread(
                self._set_claim_lease_sync,
                dispatch,
                max(float(delay_s), 0.0),
            )
        except Exception:
            _logger.exception(
                "Dream confirmation claim lease update failed for "
                "message_id=%s",
                dispatch.message_id,
            )

    async def _renew_owned_claim(
        self,
        dispatch: StoryWorkspaceDreamConfirmationDispatch,
    ) -> None:
        while True:
            await asyncio.sleep(self._lease_renew_interval_s)
            try:
                renewed = await asyncio.to_thread(
                    self._set_claim_lease_sync,
                    dispatch,
                    self._lease_duration_s,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                _logger.exception(
                    "Dream confirmation claim renewal failed for "
                    "message_id=%s; retrying before lease expiry",
                    dispatch.message_id,
                )
                continue
            if not renewed:
                return

    async def _consume_and_ack(
        self,
        dispatch: StoryWorkspaceDreamConfirmationDispatch,
    ) -> None:
        completion_observed = False
        heartbeat: Optional[asyncio.Task[None]] = asyncio.create_task(
            self._renew_owned_claim(dispatch),
            name=f"dream-confirmation-lease-{dispatch.message_id}",
        )

        async def stop_heartbeat() -> None:
            nonlocal heartbeat
            if heartbeat is None:
                return
            heartbeat.cancel()
            await asyncio.gather(heartbeat, return_exceptions=True)
            heartbeat = None

        try:
            dispatcher = self._dispatcher_factory()
            completed = await dispatcher(
                dispatch.thread_id,
                dispatch.actor_id,
                dispatch.message_id,
                dispatch.parts,
                dispatch.metadata,
            )
            await stop_heartbeat()
            if completed:
                completion_observed = True
                await asyncio.to_thread(self._mark_dispatched_sync, dispatch)
                self._retry_state.pop(dispatch.message_id, None)
            else:
                delay = self._record_retry(dispatch.message_id)
                await self._defer_owned_claim(dispatch, delay)
        except asyncio.CancelledError:
            await stop_heartbeat()
            self._record_retry(dispatch.message_id)
            if not completion_observed:
                await self._defer_owned_claim(dispatch, 0.0)
            raise
        except Exception:
            await stop_heartbeat()
            delay = self._record_retry(dispatch.message_id)
            if not completion_observed:
                await self._defer_owned_claim(dispatch, delay)
            _logger.exception(
                "Dream confirmation remains pending for thread_id=%s "
                "message_id=%s",
                dispatch.thread_id,
                dispatch.message_id,
            )
        finally:
            await stop_heartbeat()
            current = asyncio.current_task()
            if self._in_flight.get(dispatch.message_id) is current:
                self._in_flight.pop(dispatch.message_id, None)

    async def _run(self) -> None:
        try:
            while True:
                try:
                    await self.reconcile_once()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    _logger.exception(
                        "Dream confirmation reconciliation scan failed"
                    )
                stop_event = self._stop_event
                if stop_event is None:
                    return
                try:
                    await asyncio.wait_for(
                        stop_event.wait(),
                        timeout=self._reconcile_interval_s,
                    )
                    return
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            raise


class StoryWorkspaceDreamConfirmationService:
    """Validate and atomically persist a one-shot Dream continuation command."""

    def __init__(
        self,
        db: Any,
        *,
        run_reader: StoryWorkspaceDreamRunReader,
        projection_reader: StoryWorkspaceDreamProjectionReader,
        request_id_factory: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        self._db = db
        self._run_reader = run_reader
        self._projection_reader = projection_reader
        self._request_id_factory = request_id_factory

    def close(self) -> None:
        self._db.close()

    def submit_confirmation(
        self,
        run_id: str,
        payload: StoryWorkspaceDreamConfirmationCommand,
        *,
        actor_id: str,
    ) -> StoryWorkspacePersistedDreamConfirmation:
        if payload.story_workspace_run_id != run_id:
            raise StoryWorkspaceDreamConfirmationError("CONFIG_VERSION_DRIFT", 409)

        workflow_run = self._run_reader(run_id)
        thread_id = workflow_run.source_voice_thread_id
        if not isinstance(thread_id, str) or payload.thread_id != thread_id:
            raise StoryWorkspaceDreamConfirmationError("CONFIG_VERSION_DRIFT", 409)
        try:
            numeric_actor_id = int(actor_id)
        except (TypeError, ValueError) as exc:
            raise StoryWorkspaceDreamConfirmationError(
                "WORKFLOW_PERMISSION_DENIED", 403
            ) from exc

        if not self._thread_owned_by(thread_id, numeric_actor_id):
            raise StoryWorkspaceDreamConfirmationError(
                "WORKFLOW_PERMISSION_DENIED", 403
            )

        message_id = story_workspace_dream_confirmation_message_id(
            str(actor_id),
            run_id,
            payload.idempotency_key,
        )
        fingerprint = _command_fingerprint(str(actor_id), payload)

        # A completed replay remains replayable after the Agent advances stage
        # revisions. Authority and thread ownership are still checked first.
        existing = self._select_message(message_id)
        if existing is not None:
            return self._resolve_existing(
                existing,
                message_id=message_id,
                thread_id=thread_id,
                actor_id=str(actor_id),
                run_id=run_id,
                idempotency_key=payload.idempotency_key,
                fingerprint=fingerprint,
            )
        if self._select_confirmation_for_scope(
            thread_id=thread_id,
            actor_id=str(actor_id),
            run_id=run_id,
        ) is not None:
            raise StoryWorkspaceDreamConfirmationError(
                "IDEMPOTENCY_CONFLICT", 409
            )

        # First read catches ordinary stale drafts without acquiring a PostgreSQL
        # writer lock. A second read immediately before INSERT closes the
        # common check/commit window, but cannot make FS and PostgreSQL one domain.
        _validate_projection(
            self._projection_reader(workflow_run, thread_id),
            payload,
        )

        request_id = self._request_id_factory()
        parts = _hidden_parts(payload)
        wire = _command_wire(payload)
        metadata = {
            "kind": STORY_WORKSPACE_DREAM_CONFIRMATION_METADATA_KIND,
            "actor": str(actor_id),
            "story_workspace_run_id": run_id,
            "thread_id": thread_id,
            "base_revisions": wire["baseRevisions"],
            "edit_count": len(payload.edits),
            "command_fingerprint": fingerprint,
            "idempotency_key": payload.idempotency_key,
            "request_id": request_id,
            "dispatch_status": (
                STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCH_PENDING
            ),
        }

        try:
            self._db.execute("BEGIN")
            existing = self._select_message(message_id)
            if existing is not None:
                result = self._resolve_existing(
                    existing,
                    message_id=message_id,
                    thread_id=thread_id,
                    actor_id=str(actor_id),
                    run_id=run_id,
                    idempotency_key=payload.idempotency_key,
                    fingerprint=fingerprint,
                )
                self._db.commit()
                return result
            if self._select_confirmation_for_scope(
                thread_id=thread_id,
                actor_id=str(actor_id),
                run_id=run_id,
            ) is not None:
                raise StoryWorkspaceDreamConfirmationError(
                    "IDEMPOTENCY_CONFLICT", 409
                )

            _validate_projection(
                self._projection_reader(workflow_run, thread_id),
                payload,
            )
            cursor = self._db.execute(
                "INSERT INTO chat_message "
                "(id, thread_id, role, parts, metadata) VALUES (%s, %s, %s, %s, %s) "
                "ON CONFLICT (id) DO NOTHING",
                (
                    message_id,
                    thread_id,
                    "user",
                    _canonical_json(parts),
                    _canonical_json(metadata),
                ),
            )
            if cursor.rowcount != 1:
                existing = self._select_message(message_id)
                if existing is None:
                    raise StoryWorkspaceDreamConfirmationError(
                        "RESULT_COMMIT_FAILED", 503
                    )
                result = self._resolve_existing(
                    existing,
                    message_id=message_id,
                    thread_id=thread_id,
                    actor_id=str(actor_id),
                    run_id=run_id,
                    idempotency_key=payload.idempotency_key,
                    fingerprint=fingerprint,
                )
                self._db.commit()
                return result

            touched = self._db.execute(
                "UPDATE chat_thread SET updated_at = CURRENT_TIMESTAMP "
                "WHERE id = %s AND user_id = %s",
                (thread_id, numeric_actor_id),
            )
            if touched.rowcount != 1:
                raise StoryWorkspaceDreamConfirmationError(
                    "WORKFLOW_PERMISSION_DENIED", 403
                )
            self._db.commit()
        except StoryWorkspaceDreamConfirmationError:
            if self._db.in_transaction:
                self._db.rollback()
            raise
        except PostgresError as exc:
            if self._db.in_transaction:
                self._db.rollback()
            raise StoryWorkspaceDreamConfirmationError(
                "RESULT_COMMIT_FAILED", 503
            ) from exc
        except Exception:
            if self._db.in_transaction:
                self._db.rollback()
            raise

        accepted = StoryWorkspaceDreamConfirmationAccepted(
            message_id=message_id,
            story_workspace_run_id=run_id,
            thread_id=thread_id,
            status="accepted",
            replayed=False,
            dispatched=False,
            request_id=request_id,
        )
        return StoryWorkspacePersistedDreamConfirmation(
            accepted=accepted,
            dispatch=StoryWorkspaceDreamConfirmationDispatch(
                thread_id=thread_id,
                actor_id=str(actor_id),
                message_id=message_id,
                parts=parts,
                metadata=metadata,
            ),
        )

    def _thread_owned_by(self, thread_id: str, actor_id: int) -> bool:
        try:
            row = self._db.execute(
                "SELECT id FROM chat_thread WHERE id = %s AND user_id = %s",
                (thread_id, actor_id),
            ).fetchone()
        except PostgresError as exc:
            raise StoryWorkspaceDreamConfirmationError(
                "DECK_RUNTIME_CONFIG_UNAVAILABLE", 503
            ) from exc
        return row is not None

    def _select_message(self, message_id: str) -> Optional[dict[str, Any]]:
        try:
            row = self._db.execute(
                "SELECT id, thread_id, role, parts, metadata "
                "FROM chat_message WHERE id = %s",
                (message_id,),
            ).fetchone()
        except PostgresError as exc:
            raise StoryWorkspaceDreamConfirmationError(
                "DECK_RUNTIME_CONFIG_UNAVAILABLE", 503
            ) from exc
        if row is None:
            return None
        return {
            "id": row["id"],
            "thread_id": row["thread_id"],
            "role": row["role"],
            "parts": _decode_parts(row["parts"]),
            "metadata": _decode_metadata(row["metadata"]),
        }

    def _select_confirmation_for_scope(
        self,
        *,
        thread_id: str,
        actor_id: str,
        run_id: str,
    ) -> Optional[dict[str, Any]]:
        try:
            rows = self._db.execute(
                "SELECT id, thread_id, role, parts, metadata FROM chat_message "
                "WHERE role = 'user' "
                "ORDER BY created_at ASC, id ASC",
            ).fetchall()
        except PostgresError as exc:
            raise StoryWorkspaceDreamConfirmationError(
                "DECK_RUNTIME_CONFIG_UNAVAILABLE", 503
            ) from exc
        for row in rows:
            metadata = _decode_metadata(row["metadata"])
            if _confirmation_metadata_matches_actor_run(
                metadata,
                actor_id=actor_id,
                run_id=run_id,
            ):
                return {
                    "id": row["id"],
                    "thread_id": row["thread_id"],
                    "role": row["role"],
                    "parts": _decode_parts(row["parts"]),
                    "metadata": metadata,
                }
        return None

    @staticmethod
    def _resolve_existing(
        existing: dict[str, Any],
        *,
        message_id: str,
        thread_id: str,
        actor_id: str,
        run_id: str,
        idempotency_key: str,
        fingerprint: str,
    ) -> StoryWorkspacePersistedDreamConfirmation:
        metadata = existing.get("metadata")
        valid_scope = (
            existing.get("thread_id") == thread_id
            and existing.get("role") == "user"
            and isinstance(metadata, dict)
            and metadata.get("kind")
            == STORY_WORKSPACE_DREAM_CONFIRMATION_METADATA_KIND
            and metadata.get("actor") == actor_id
            and metadata.get("story_workspace_run_id") == run_id
            and metadata.get("thread_id") == thread_id
            and metadata.get("idempotency_key") == idempotency_key
        )
        if not valid_scope or metadata.get("command_fingerprint") != fingerprint:
            raise StoryWorkspaceDreamConfirmationError(
                "IDEMPOTENCY_CONFLICT", 409
            )
        request_id = metadata.get("request_id")
        if not isinstance(request_id, str) or not request_id:
            raise StoryWorkspaceDreamConfirmationError(
                "IDEMPOTENCY_CONFLICT", 409
            )
        dispatch_status = metadata.get(
            "dispatch_status",
            STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCH_PENDING,
        )
        if dispatch_status not in {
            STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCH_PENDING,
            STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCHING,
            STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCHED,
        }:
            raise StoryWorkspaceDreamConfirmationError(
                "IDEMPOTENCY_CONFLICT", 409
            )
        if dispatch_status == STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCHING:
            if not (
                isinstance(metadata.get(_DISPATCH_CLAIM_ID), str)
                and bool(metadata.get(_DISPATCH_CLAIM_ID))
                and _valid_lease_deadline(
                    metadata.get(_DISPATCH_CLAIM_LEASE_UNTIL)
                )
            ):
                raise StoryWorkspaceDreamConfirmationError(
                    "IDEMPOTENCY_CONFLICT", 409
                )
        dispatched = (
            dispatch_status == STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCHED
        )
        accepted = StoryWorkspaceDreamConfirmationAccepted(
            message_id=message_id,
            story_workspace_run_id=run_id,
            thread_id=thread_id,
            status="accepted",
            replayed=True,
            dispatched=dispatched,
            request_id=request_id,
        )
        if dispatched or (
            dispatch_status == STORY_WORKSPACE_DREAM_CONFIRMATION_DISPATCHING
        ):
            return StoryWorkspacePersistedDreamConfirmation(
                accepted=accepted,
                dispatch=None,
            )
        parts = existing.get("parts")
        if not isinstance(parts, list):
            raise StoryWorkspaceDreamConfirmationError(
                "IDEMPOTENCY_CONFLICT", 409
            )
        return StoryWorkspacePersistedDreamConfirmation(
            accepted=accepted,
            dispatch=StoryWorkspaceDreamConfirmationDispatch(
                thread_id=thread_id,
                actor_id=actor_id,
                message_id=message_id,
                parts=parts,
                metadata=metadata,
            ),
        )
