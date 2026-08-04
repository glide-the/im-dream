"""Persist one Dream confirmation and queue the original Chat Agent.

The confirmation is a hidden ``chat_message`` user turn. SQLite persistence
is atomic (message insert plus thread touch) and idempotent without adding a
table or changing DDL. Dream files live on a separate filesystem durability
domain, so their revisions are read once before and once while holding the
SQLite write transaction; the command retains the accepted base revisions so
the Agent must apply them with the file protocol's own compare-and-swap rules.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib
import json
import logging
import sqlite3
from typing import Any, Callable, Optional, Protocol
from uuid import uuid4

try:
    from models.workflow_run import WorkflowRun
    from story_workspace.contracts import (
        STORY_WORKSPACE_DREAM_RELATIONS_MAX,
        STORY_WORKSPACE_DREAM_REQUIRED_STAGES,
        StoryWorkspaceDreamConfirmationAccepted,
        StoryWorkspaceDreamConfirmationCommand,
        StoryWorkspaceDreamFilesResponse,
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
        StoryWorkspaceDreamStage,
    )


logger = logging.getLogger(__name__)

DREAM_CONFIRMATION_METADATA_KIND = "story-workspace-dream-confirmation"
DREAM_CONFIRMATION_DISPATCH_PENDING = "pending"
DREAM_CONFIRMATION_DISPATCHED = "dispatched"
_EDITABLE_FIELDS = frozenset({"displayName", "summary", "relations"})


class StoryWorkspaceDreamConfirmationError(RuntimeError):
    """Allowlisted public failure for the Dream confirmation boundary."""

    def __init__(self, code: str, status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


class RunReader(Protocol):
    def __call__(self, run_id: str) -> WorkflowRun: ...


class ProjectionReader(Protocol):
    def __call__(
        self,
        workflow_run: WorkflowRun,
        thread_id: str,
    ) -> StoryWorkspaceDreamFilesResponse: ...


DreamConfirmationDispatcher = Callable[[str, str, str, list, dict], bool]


@dataclass(frozen=True)
class DreamConfirmationDispatch:
    thread_id: str
    actor_id: str
    message_id: str
    parts: list
    metadata: dict


@dataclass(frozen=True)
class PersistedDreamConfirmation:
    accepted: StoryWorkspaceDreamConfirmationAccepted
    dispatch: Optional[DreamConfirmationDispatch]


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


def dream_confirmation_message_id(
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
        "kind": DREAM_CONFIRMATION_METADATA_KIND,
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
        and metadata.get("kind") == DREAM_CONFIRMATION_METADATA_KIND
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


def read_dream_confirmation_fact(
    db: sqlite3.Connection,
    *,
    actor_id: str,
    thread_id: str,
    run_id: str,
) -> tuple[bool, bool]:
    """Read the actor/thread/run confirmation fact from existing message audit."""

    rows = db.execute(
        "SELECT metadata FROM chat_message "
        "WHERE thread_id = ? AND role = 'user' ORDER BY created_at ASC, id ASC",
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
            metadata.get("dispatch_status") == DREAM_CONFIRMATION_DISPATCHED
        )
    return accepted, dispatched


def mark_dream_confirmation_dispatched(
    db: sqlite3.Connection,
    dispatch: DreamConfirmationDispatch,
) -> bool:
    """Durably mark a scheduled continuation; repeated marking is idempotent."""

    try:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT thread_id, role, metadata FROM chat_message WHERE id = ?",
            (dispatch.message_id,),
        ).fetchone()
        if row is None:
            raise StoryWorkspaceDreamConfirmationError("RESULT_COMMIT_FAILED", 503)
        metadata = _decode_metadata(row["metadata"])
        expected = dispatch.metadata
        valid = (
            row["thread_id"] == dispatch.thread_id
            and row["role"] == "user"
            and isinstance(metadata, dict)
            and isinstance(expected, dict)
            and metadata.get("kind") == DREAM_CONFIRMATION_METADATA_KIND
            and metadata.get("actor") == dispatch.actor_id
            and metadata.get("thread_id") == dispatch.thread_id
            and metadata.get("story_workspace_run_id")
            == expected.get("story_workspace_run_id")
            and metadata.get("request_id") == expected.get("request_id")
            and metadata.get("command_fingerprint")
            == expected.get("command_fingerprint")
        )
        if not valid:
            raise StoryWorkspaceDreamConfirmationError("IDEMPOTENCY_CONFLICT", 409)
        status = metadata.get(
            "dispatch_status",
            DREAM_CONFIRMATION_DISPATCH_PENDING,
        )
        if status == DREAM_CONFIRMATION_DISPATCHED:
            db.commit()
            return True
        if status != DREAM_CONFIRMATION_DISPATCH_PENDING:
            raise StoryWorkspaceDreamConfirmationError("IDEMPOTENCY_CONFLICT", 409)
        metadata["dispatch_status"] = DREAM_CONFIRMATION_DISPATCHED
        updated = db.execute(
            "UPDATE chat_message SET metadata = ? WHERE id = ?",
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
    except sqlite3.Error as exc:
        if db.in_transaction:
            db.rollback()
        raise StoryWorkspaceDreamConfirmationError(
            "RESULT_COMMIT_FAILED", 503
        ) from exc


def build_thread_turn_dispatcher(
    factory: Any | None = None,
    *,
    request_factory: Callable[..., Any] | None = None,
) -> DreamConfirmationDispatcher:
    """Queue a resumed turn even while the same thread is currently running.

    ``ClaudeAgentThreadFactory.run_streaming`` owns a per-thread lock. Starting
    this drain task immediately therefore queues behind an in-flight turn and
    preserves ordering without a lifecycle pre-check that could lose work.
    """

    def dispatch(
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
            request = selected_request_factory(
                user_id=str(actor_id),
                thread_id=thread_id,
                resume=True,
                message_id=message_id,
                message_parts=parts,
                message_metadata=metadata,
            )
            stream = selected_factory.run_streaming(request)

            async def _drain() -> None:
                try:
                    async for _frame in stream:
                        pass
                except Exception:
                    logger.exception(
                        "Dream confirmation turn failed for thread_id=%s "
                        "message_id=%s",
                        thread_id,
                        message_id,
                    )

            asyncio.create_task(
                _drain(),
                name=f"dream-confirmation-{message_id}",
            )
            return True
        except Exception:
            logger.exception(
                "Dream confirmation dispatch failed for thread_id=%s "
                "message_id=%s",
                thread_id,
                message_id,
            )
            return False

    return dispatch


class StoryWorkspaceDreamConfirmationService:
    """Validate and atomically persist a one-shot Dream continuation command."""

    def __init__(
        self,
        db: sqlite3.Connection,
        *,
        run_reader: RunReader,
        projection_reader: ProjectionReader,
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
    ) -> PersistedDreamConfirmation:
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

        message_id = dream_confirmation_message_id(
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

        # First read catches ordinary stale drafts without acquiring a SQLite
        # writer lock. A second read immediately before INSERT closes the
        # common check/commit window, but cannot make FS and SQLite one domain.
        _validate_projection(
            self._projection_reader(workflow_run, thread_id),
            payload,
        )

        request_id = self._request_id_factory()
        parts = _hidden_parts(payload)
        wire = _command_wire(payload)
        metadata = {
            "kind": DREAM_CONFIRMATION_METADATA_KIND,
            "actor": str(actor_id),
            "story_workspace_run_id": run_id,
            "thread_id": thread_id,
            "base_revisions": wire["baseRevisions"],
            "edit_count": len(payload.edits),
            "command_fingerprint": fingerprint,
            "idempotency_key": payload.idempotency_key,
            "request_id": request_id,
            "dispatch_status": DREAM_CONFIRMATION_DISPATCH_PENDING,
        }

        try:
            self._db.execute("BEGIN IMMEDIATE")
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
                "INSERT OR IGNORE INTO chat_message "
                "(id, thread_id, role, parts, metadata) VALUES (?, ?, ?, ?, ?)",
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
                "WHERE id = ? AND user_id = ?",
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
        except sqlite3.Error as exc:
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
        return PersistedDreamConfirmation(
            accepted=accepted,
            dispatch=DreamConfirmationDispatch(
                thread_id=thread_id,
                actor_id=str(actor_id),
                message_id=message_id,
                parts=parts,
                metadata={
                    **metadata,
                    "dispatch_status": DREAM_CONFIRMATION_DISPATCHED,
                },
            ),
        )

    def _thread_owned_by(self, thread_id: str, actor_id: int) -> bool:
        try:
            row = self._db.execute(
                "SELECT id FROM chat_thread WHERE id = ? AND user_id = ?",
                (thread_id, actor_id),
            ).fetchone()
        except sqlite3.Error as exc:
            raise StoryWorkspaceDreamConfirmationError(
                "DECK_RUNTIME_CONFIG_UNAVAILABLE", 503
            ) from exc
        return row is not None

    def _select_message(self, message_id: str) -> Optional[dict[str, Any]]:
        try:
            row = self._db.execute(
                "SELECT id, thread_id, role, parts, metadata "
                "FROM chat_message WHERE id = ?",
                (message_id,),
            ).fetchone()
        except sqlite3.Error as exc:
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
        except sqlite3.Error as exc:
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
    ) -> PersistedDreamConfirmation:
        metadata = existing.get("metadata")
        valid_scope = (
            existing.get("thread_id") == thread_id
            and existing.get("role") == "user"
            and isinstance(metadata, dict)
            and metadata.get("kind") == DREAM_CONFIRMATION_METADATA_KIND
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
            DREAM_CONFIRMATION_DISPATCH_PENDING,
        )
        if dispatch_status not in {
            DREAM_CONFIRMATION_DISPATCH_PENDING,
            DREAM_CONFIRMATION_DISPATCHED,
        }:
            raise StoryWorkspaceDreamConfirmationError(
                "IDEMPOTENCY_CONFLICT", 409
            )
        dispatched = dispatch_status == DREAM_CONFIRMATION_DISPATCHED
        accepted = StoryWorkspaceDreamConfirmationAccepted(
            message_id=message_id,
            story_workspace_run_id=run_id,
            thread_id=thread_id,
            status="accepted",
            replayed=True,
            dispatched=dispatched,
            request_id=request_id,
        )
        if dispatched:
            return PersistedDreamConfirmation(accepted=accepted, dispatch=None)
        parts = existing.get("parts")
        if not isinstance(parts, list):
            raise StoryWorkspaceDreamConfirmationError(
                "IDEMPOTENCY_CONFLICT", 409
            )
        return PersistedDreamConfirmation(
            accepted=accepted,
            dispatch=DreamConfirmationDispatch(
                thread_id=thread_id,
                actor_id=actor_id,
                message_id=message_id,
                parts=parts,
                metadata={
                    **metadata,
                    "dispatch_status": DREAM_CONFIRMATION_DISPATCHED,
                },
            ),
        )
