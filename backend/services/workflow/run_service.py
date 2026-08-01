"""Atomic Workflow Run creation, idempotency, transitions, and retry."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
import hashlib
import hmac
import inspect
import json
import sqlite3
from typing import Any
import uuid

try:
    from backend.database import create_agent_session_tables
    from backend.models.workflow_run import (
        AuthenticatedActorContext,
        RunStatus,
        RuntimeLoadReceiptReadiness,
        TERMINAL_RUN_STATUSES,
        WorkflowRun,
        WorkflowRunTransition,
    )
except ModuleNotFoundError:  # Support the backend directory on PYTHONPATH.
    from database import create_agent_session_tables
    from models.workflow_run import (
        AuthenticatedActorContext,
        RunStatus,
        RuntimeLoadReceiptReadiness,
        TERMINAL_RUN_STATUSES,
        WorkflowRun,
        WorkflowRunTransition,
    )


IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
RUN_NOT_FOUND = "WORKFLOW_RUN_NOT_FOUND"
ILLEGAL_RUN_TRANSITION = "ILLEGAL_RUN_TRANSITION"
RUNTIME_LOAD_RECEIPT_NOT_READY = "RUNTIME_LOAD_RECEIPT_NOT_READY"
AGENT_SESSION_NOT_READY = "AGENT_SESSION_NOT_READY"
RETRY_SOURCE_MISMATCH = "RETRY_SOURCE_MISMATCH"


class WorkflowRunError(RuntimeError):
    def __init__(self, code: str, summary: str) -> None:
        self.code = code
        self.summary = summary
        super().__init__(summary)


class IdempotencyConflict(WorkflowRunError):
    def __init__(self) -> None:
        # Deliberately contains no original run identifier or source details.
        super().__init__(IDEMPOTENCY_CONFLICT, "idempotency request conflicts")


class RunNotFound(WorkflowRunError):
    def __init__(self) -> None:
        super().__init__(RUN_NOT_FOUND, "workflow run was not found")


class IllegalRunTransition(WorkflowRunError):
    def __init__(self) -> None:
        super().__init__(ILLEGAL_RUN_TRANSITION, "workflow run transition is not allowed")


class RuntimeLoadReceiptNotReady(WorkflowRunError):
    def __init__(self) -> None:
        super().__init__(
            RUNTIME_LOAD_RECEIPT_NOT_READY,
            "runtime load receipt is missing, mismatched, or not ready",
        )


class AgentSessionNotReady(WorkflowRunError):
    def __init__(self) -> None:
        super().__init__(
            AGENT_SESSION_NOT_READY,
            "agent session is missing, mismatched, or not ready",
        )


class RetrySourceMismatch(WorkflowRunError):
    def __init__(self, summary: str = "retry must preserve the frozen run source") -> None:
        super().__init__(RETRY_SOURCE_MISMATCH, summary)


ReceiptReader = Callable[
    [str],
    RuntimeLoadReceiptReadiness
    | dict[str, Any]
    | Awaitable[RuntimeLoadReceiptReadiness | dict[str, Any]],
]
FailureInjector = Callable[[str], None]


_ALLOWED_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.PREFLIGHT: frozenset(
        {RunStatus.QUEUED, RunStatus.FAILED, RunStatus.CANCELLED}
    ),
    RunStatus.QUEUED: frozenset(
        {RunStatus.RUNNING, RunStatus.FAILED, RunStatus.CANCELLED}
    ),
    RunStatus.RUNNING: frozenset(
        {RunStatus.OUTPUT_VALIDATING, RunStatus.FAILED, RunStatus.CANCELLED}
    ),
    RunStatus.OUTPUT_VALIDATING: frozenset(
        {RunStatus.PENDING_REVIEW, RunStatus.FAILED, RunStatus.CANCELLED}
    ),
    RunStatus.PENDING_REVIEW: frozenset(
        {
            RunStatus.CONFIRMED,
            RunStatus.REJECTED,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
        }
    ),
    RunStatus.CONFIRMED: frozenset(
        {RunStatus.CONTINUING, RunStatus.COMPLETED}
    ),
    RunStatus.CONTINUING: frozenset(
        {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}
    ),
}


class WorkflowRunService:
    """Own the run tables; external services provide only immutable projections."""

    def __init__(
        self,
        db: sqlite3.Connection,
        *,
        token_secret: bytes | str,
        receipt_reader: ReceiptReader | None = None,
        clock: Callable[[], datetime] | None = None,
        failure_injector: FailureInjector | None = None,
    ) -> None:
        secret = token_secret.encode("utf-8") if isinstance(token_secret, str) else token_secret
        if len(secret) < 32:
            raise ValueError("token_secret must contain at least 32 bytes")
        if db.in_transaction:
            raise RuntimeError("workflow run service requires a clean transaction boundary")
        create_agent_session_tables(db)
        self.db = db
        self.db.row_factory = sqlite3.Row
        self._token_secret = secret
        self._receipt_reader = receipt_reader
        self._clock = clock or (lambda: datetime.now(UTC))
        self._failure_injector = failure_injector

    async def create_run(
        self,
        preflight_id: str,
        preflight_token: str,
        idempotency_key: str,
        source_voice_thread_id: str | None,
        actor_context: AuthenticatedActorContext,
        *,
        source_message_id: str | None = None,
        source_message_time: datetime | None = None,
    ) -> WorkflowRun:
        """Create or replay one run without trusting client provenance fields."""

        return self._create_run(
            preflight_id=preflight_id,
            preflight_token=preflight_token,
            idempotency_key=idempotency_key,
            source_voice_thread_id=source_voice_thread_id,
            source_message_id=source_message_id,
            source_message_time=source_message_time,
            actor_context=actor_context,
            retry_of_run_id=None,
            expected_retry_source=None,
        )

    async def retry_run(
        self,
        workflow_run_id: str,
        actor_context: AuthenticatedActorContext,
        *,
        preflight_id: str,
        preflight_token: str,
        idempotency_key: str,
    ) -> WorkflowRun:
        """Create a new attempt after a fresh preflight, preserving all sources."""

        original_row = self._select_scoped_run(workflow_run_id, actor_context)
        if original_row is None:
            raise RunNotFound()
        original = self._row_to_run(original_row)
        if original.status not in {
            RunStatus.FAILED,
            RunStatus.REJECTED,
            RunStatus.CANCELLED,
        }:
            raise RetrySourceMismatch("only a terminated unsuccessful run can be retried")
        if idempotency_key == original.idempotency_key:
            raise RetrySourceMismatch("retry requires a new idempotency key")

        expected_source = self._frozen_source_from_run(original)
        return self._create_run(
            preflight_id=preflight_id,
            preflight_token=preflight_token,
            idempotency_key=idempotency_key,
            source_voice_thread_id=original.source_voice_thread_id,
            source_message_id=original.source_message_id,
            source_message_time=original.source_message_time,
            actor_context=actor_context,
            retry_of_run_id=original.workflow_run_id,
            expected_retry_source=expected_source,
        )

    async def transition_run(
        self,
        workflow_run_id: str,
        to_status: RunStatus | str,
        actor_context: AuthenticatedActorContext,
        *,
        reason_code: str | None = None,
        failed_step: str | None = None,
        error_code: str | None = None,
        runtime_load_receipt_id: str | None = None,
        agent_session_id: str | None = None,
        normalized_result_ready: bool = False,
        review_items_approved: bool = False,
    ) -> WorkflowRun:
        """Atomically update current state and append exactly one transition."""

        target = RunStatus(to_status)
        receipt: RuntimeLoadReceiptReadiness | None = None
        observed = self._select_scoped_run(workflow_run_id, actor_context)
        if observed is None:
            raise RunNotFound()
        observed_status = RunStatus(observed["status"])
        if observed_status is target:
            if target is RunStatus.RUNNING and (
                observed["runtime_load_receipt_id"] != runtime_load_receipt_id
                or observed["agent_session_id"] != agent_session_id
            ):
                raise AgentSessionNotReady()
            return self._row_to_run(observed)
        if target is RunStatus.RUNNING:
            if (
                runtime_load_receipt_id is None
                or agent_session_id is None
                or self._receipt_reader is None
            ):
                raise RuntimeLoadReceiptNotReady()
            raw_receipt = self._receipt_reader(runtime_load_receipt_id)
            if inspect.isawaitable(raw_receipt):
                raw_receipt = await raw_receipt
            receipt = RuntimeLoadReceiptReadiness.model_validate(raw_receipt)

        self._require_clean_transaction()
        try:
            self.db.execute("BEGIN IMMEDIATE")
            row = self._select_scoped_run(workflow_run_id, actor_context)
            if row is None:
                raise RunNotFound()
            current = RunStatus(row["status"])
            if current is target:
                self.db.commit()
                return self._row_to_run(row)
            self._validate_transition(
                row,
                target,
                receipt=receipt,
                normalized_result_ready=normalized_result_ready,
                review_items_approved=review_items_approved,
                failed_step=failed_step,
                error_code=error_code,
            )

            now = self._now()
            next_version = int(row["status_version"]) + 1
            terminal = target in TERMINAL_RUN_STATUSES
            receipt_id = (
                receipt.receipt_id if receipt is not None else row["runtime_load_receipt_id"]
            )
            session_id = (
                agent_session_id if target is RunStatus.RUNNING else row["agent_session_id"]
            )
            if target is RunStatus.RUNNING:
                assert receipt is not None and session_id is not None
                self._validate_agent_session_binding(row, receipt, session_id)
                session_cursor = self.db.execute(
                    """
                    UPDATE agent_sessions
                    SET status = 'active', started_at = ?, lease_expires_at = NULL,
                        owner_token = NULL
                    WHERE agent_session_id = ? AND status = 'creating'
                    """,
                    (self._iso(now), session_id),
                )
                if session_cursor.rowcount != 1:
                    raise AgentSessionNotReady()
                self._checkpoint("session_updated")
            cursor = self.db.execute(
                """
                UPDATE workflow_runs
                SET status = ?, status_version = ?, runtime_load_receipt_id = ?,
                    agent_session_id = ?, failed_step = ?, error_code = ?,
                    started_at = CASE
                        WHEN ? = 'running' THEN COALESCE(started_at, ?)
                        ELSE started_at
                    END,
                    completed_at = CASE WHEN ? THEN ? ELSE completed_at END
                WHERE id = ? AND status = ? AND status_version = ?
                """,
                (
                    target.value,
                    next_version,
                    receipt_id,
                    session_id,
                    failed_step if target is RunStatus.FAILED else None,
                    error_code if target is RunStatus.FAILED else None,
                    target.value,
                    self._iso(now),
                    int(terminal),
                    self._iso(now),
                    workflow_run_id,
                    current.value,
                    row["status_version"],
                ),
            )
            if cursor.rowcount != 1:
                raise IllegalRunTransition()
            self._checkpoint("status_updated")
            self._insert_transition(
                workflow_run_id=workflow_run_id,
                transition_seq=next_version,
                from_status=current,
                to_status=target,
                actor_id=actor_context.actor_id,
                reason_code=reason_code,
                failed_step=failed_step if target is RunStatus.FAILED else None,
                error_code=error_code if target is RunStatus.FAILED else None,
                occurred_at=now,
            )
            self._checkpoint("status_transition_written")
            updated = self._select_scoped_run(workflow_run_id, actor_context)
            assert updated is not None
            self.db.commit()
            return self._row_to_run(updated)
        except Exception:
            if self.db.in_transaction:
                self.db.rollback()
            raise

    def list_transitions(
        self,
        workflow_run_id: str,
        actor_context: AuthenticatedActorContext,
    ) -> list[WorkflowRunTransition]:
        if self._select_scoped_run(workflow_run_id, actor_context) is None:
            raise RunNotFound()
        rows = self.db.execute(
            """
            SELECT * FROM workflow_run_transitions
            WHERE workflow_run_id = ?
            ORDER BY transition_seq
            """,
            (workflow_run_id,),
        ).fetchall()
        return [self._row_to_transition(row) for row in rows]

    def _create_run(
        self,
        *,
        preflight_id: str,
        preflight_token: str,
        idempotency_key: str,
        source_voice_thread_id: str | None,
        source_message_id: str | None,
        source_message_time: datetime | None,
        actor_context: AuthenticatedActorContext,
        retry_of_run_id: str | None,
        expected_retry_source: dict[str, Any] | None,
    ) -> WorkflowRun:
        if not preflight_id or not preflight_token or not idempotency_key.strip():
            raise WorkflowRunError("INVALID_RUN_REQUEST", "required run input is missing")
        if len(idempotency_key) > 255:
            raise WorkflowRunError("INVALID_RUN_REQUEST", "idempotency key is too long")
        source_tuple = (
            source_voice_thread_id,
            source_message_id,
            source_message_time,
        )
        if any(value is not None for value in source_tuple) and not all(
            value is not None for value in source_tuple
        ):
            raise WorkflowRunError(
                "INVALID_RUN_REQUEST",
                "Voice source requires thread, message, and time",
            )
        if source_message_time is not None and source_message_time.tzinfo is None:
            raise WorkflowRunError(
                "INVALID_RUN_REQUEST",
                "source_message_time must include a timezone",
            )
        self._require_clean_transaction()

        try:
            self.db.execute("BEGIN IMMEDIATE")
            context = self._load_preflight_context(preflight_id)
            self._verify_preflight_token_signature(context, preflight_token)
            token_digest = self._token_digest(preflight_token)
            consumption = self.db.execute(
                """
                SELECT * FROM workflow_run_token_consumptions
                WHERE token_digest = ?
                """,
                (token_digest,),
            ).fetchone()
            if not self._context_is_authorized(context, actor_context):
                if consumption is not None:
                    raise IdempotencyConflict()
                raise WorkflowRunError(
                    "PREFLIGHT_NOT_FOUND_OR_NOT_AUTHORIZED",
                    "preflight was not found or is not authorized",
                )
            lock_digest = self._lock_digest(context["lock_json"])
            fingerprint = self._semantic_fingerprint(
                context,
                lock_digest=lock_digest,
                source_voice_thread_id=source_voice_thread_id,
                source_message_id=source_message_id,
                source_message_time=source_message_time,
                retry_of_run_id=retry_of_run_id,
            )
            frozen_source = self._frozen_source_from_context(
                context,
                source_voice_thread_id=source_voice_thread_id,
                source_message_id=source_message_id,
                source_message_time=source_message_time,
            )
            if expected_retry_source is not None and frozen_source != expected_retry_source:
                raise RetrySourceMismatch()

            scoped_run = self.db.execute(
                """
                SELECT * FROM workflow_runs
                WHERE workspace_id = ? AND created_by = ? AND idempotency_key = ?
                """,
                (
                    actor_context.workspace_id,
                    actor_context.actor_id,
                    idempotency_key,
                ),
            ).fetchone()

            if consumption is not None:
                if not self._consumption_matches(
                    consumption,
                    context=context,
                    actor_context=actor_context,
                    idempotency_key=idempotency_key,
                    fingerprint=fingerprint,
                ):
                    raise IdempotencyConflict()
                if (
                    scoped_run is None
                    or scoped_run["id"] != consumption["workflow_run_id"]
                    or scoped_run["semantic_fingerprint"] != fingerprint
                    or scoped_run["retry_of_run_id"] != retry_of_run_id
                ):
                    raise IdempotencyConflict()
                self.db.commit()
                return self._row_to_run(scoped_run)

            self._require_current_unconsumed_preflight(context, preflight_token)
            if scoped_run is not None:
                if (
                    scoped_run["semantic_fingerprint"] != fingerprint
                    or scoped_run["retry_of_run_id"] != retry_of_run_id
                ):
                    raise IdempotencyConflict()
                self._consume_token_for_run(
                    token_digest=token_digest,
                    workflow_run_id=scoped_run["id"],
                    context=context,
                    actor_context=actor_context,
                    idempotency_key=idempotency_key,
                    fingerprint=fingerprint,
                )
                self.db.commit()
                return self._row_to_run(scoped_run)

            now = self._now()
            run_id = "run_" + uuid.uuid4().hex
            self.db.execute(
                """
                INSERT INTO workflow_runs (
                    id, workspace_id, deck_plugin_id, deck_plugin_version,
                    workflow_definition_ref, deck_runtime_snapshot_id, status,
                    retry_of_run_id, deck_plugin_manifest_hash,
                    deck_plugin_binding_id, binding_revision,
                    runtime_plugin_lock_id, workflow_preflight_id,
                    source_voice_thread_id, source_message_id, source_message_time,
                    idempotency_key, input_hash,
                    semantic_fingerprint, status_version, created_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'preflight', ?, ?, ?, ?, ?, ?, ?, ?, ?,
                          ?, ?, ?, 1, ?, ?)
                """,
                (
                    run_id,
                    actor_context.workspace_id,
                    context["deck_plugin_id"],
                    context["deck_plugin_version"],
                    context["workflow_definition_ref"],
                    context["deck_runtime_snapshot_id"],
                    retry_of_run_id,
                    context["manifest_hash"],
                    context["deck_plugin_binding_id"],
                    context["binding_revision"],
                    context["runtime_plugin_lock_id"],
                    context["workflow_preflight_id"],
                    source_voice_thread_id,
                    source_message_id,
                    self._iso(source_message_time) if source_message_time else None,
                    idempotency_key,
                    context["input_hash"],
                    fingerprint,
                    actor_context.actor_id,
                    self._iso(now),
                ),
            )
            self._checkpoint("run_written")
            self._consume_token_for_run(
                token_digest=token_digest,
                workflow_run_id=run_id,
                context=context,
                actor_context=actor_context,
                idempotency_key=idempotency_key,
                fingerprint=fingerprint,
            )
            self._checkpoint("token_mapped")
            self._insert_transition(
                workflow_run_id=run_id,
                transition_seq=1,
                from_status=None,
                to_status=RunStatus.PREFLIGHT,
                actor_id=actor_context.actor_id,
                reason_code="run_created",
                occurred_at=now,
            )
            self._checkpoint("initial_transition_written")
            self.db.execute(
                """
                UPDATE workflow_runs
                SET status = 'queued', status_version = 2
                WHERE id = ? AND status = 'preflight' AND status_version = 1
                """,
                (run_id,),
            )
            self._insert_transition(
                workflow_run_id=run_id,
                transition_seq=2,
                from_status=RunStatus.PREFLIGHT,
                to_status=RunStatus.QUEUED,
                actor_id=actor_context.actor_id,
                reason_code="preflight_passed",
                occurred_at=now,
            )
            self._checkpoint("queued_transition_written")
            created = self.db.execute(
                "SELECT * FROM workflow_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
            assert created is not None
            self.db.commit()
            return self._row_to_run(created)
        except Exception:
            if self.db.in_transaction:
                self.db.rollback()
            raise

    def _load_preflight_context(
        self,
        preflight_id: str,
    ) -> sqlite3.Row:
        row = self.db.execute(
            """
            SELECT pf.*, b.deck_plugin_binding_id,
                   b.workspace_id AS binding_workspace_id,
                   b.creator_id AS binding_creator_id,
                   release.manifest_hash, release.workflow_definition_ref,
                   runtime_lock.lock_json,
                   runtime_lock.deck_plugin_manifest_hash AS lock_manifest_hash
            FROM workflow_preflights AS pf
            JOIN deck_plugin_bindings AS b
              ON b.deck_id = pf.deck_id
             AND b.binding_revision = pf.binding_revision
             AND b.deck_plugin_id = pf.deck_plugin_id
             AND b.deck_plugin_version = pf.deck_plugin_version
            JOIN deck_plugin_releases AS release
              ON release.deck_plugin_id = pf.deck_plugin_id
             AND release.deck_plugin_version = pf.deck_plugin_version
            JOIN deck_runtime_plugin_locks AS runtime_lock
              ON runtime_lock.id = pf.runtime_plugin_lock_id
             AND runtime_lock.deck_plugin_id = pf.deck_plugin_id
             AND runtime_lock.deck_plugin_version = pf.deck_plugin_version
            WHERE pf.workflow_preflight_id = ?
            """,
            (preflight_id,),
        ).fetchone()
        if row is None:
            raise WorkflowRunError(
                "PREFLIGHT_NOT_FOUND_OR_NOT_AUTHORIZED",
                "preflight was not found or is not authorized",
            )
        if row["manifest_hash"] != row["lock_manifest_hash"]:
            raise WorkflowRunError(
                "PREFLIGHT_NOT_FOUND_OR_NOT_AUTHORIZED",
                "preflight was not found or is not authorized",
            )
        return row

    @staticmethod
    def _context_is_authorized(
        context: sqlite3.Row,
        actor_context: AuthenticatedActorContext,
    ) -> bool:
        return bool(
            context["created_by"] == actor_context.actor_id
            and context["binding_creator_id"] == actor_context.actor_id
            and context["binding_workspace_id"] == actor_context.workspace_id
        )

    def _verify_preflight_token_signature(
        self,
        context: sqlite3.Row,
        token: str,
    ) -> None:
        payload = self._canonical_json(
            {
                "preflight_id": context["workflow_preflight_id"],
                "binding_revision": context["binding_revision"],
                "input_hash": context["input_hash"],
                "deck_runtime_snapshot_id": context["deck_runtime_snapshot_id"],
                "runtime_plugin_lock_id": context["runtime_plugin_lock_id"],
                "expires_at": self._iso(self._parse_datetime(context["expires_at"])),
            }
        )
        digest = hmac.new(self._token_secret, payload, hashlib.sha256).digest()
        import base64

        encoded = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        if not hmac.compare_digest(token, "pft_" + encoded):
            raise WorkflowRunError("PREFLIGHT_TOKEN_INVALID", "preflight token is invalid")

    def _require_current_unconsumed_preflight(
        self,
        context: sqlite3.Row,
        token: str,
    ) -> None:
        if context["status"] != "passed":
            raise WorkflowRunError("PREFLIGHT_TOKEN_INVALID", "preflight did not pass")
        if self._parse_datetime(context["expires_at"]) <= self._now():
            raise WorkflowRunError("PREFLIGHT_TOKEN_EXPIRED", "preflight token has expired")
        if context["consumed_at"] is not None:
            raise WorkflowRunError("PREFLIGHT_TOKEN_REPLAYED", "preflight token was consumed")
        token_hash = "sha256:" + hashlib.sha256(token.encode("utf-8")).hexdigest()
        if context["preflight_token_hash"] is None or not hmac.compare_digest(
            token_hash,
            context["preflight_token_hash"],
        ):
            raise WorkflowRunError("PREFLIGHT_TOKEN_INVALID", "preflight token is invalid")

    def _consume_token_for_run(
        self,
        *,
        token_digest: str,
        workflow_run_id: str,
        context: sqlite3.Row,
        actor_context: AuthenticatedActorContext,
        idempotency_key: str,
        fingerprint: str,
    ) -> None:
        self.db.execute(
            """
            INSERT INTO workflow_run_token_consumptions (
                token_digest, workflow_run_id, workflow_preflight_id,
                workspace_id, actor_id, idempotency_key, semantic_fingerprint
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                token_digest,
                workflow_run_id,
                context["workflow_preflight_id"],
                actor_context.workspace_id,
                actor_context.actor_id,
                idempotency_key,
                fingerprint,
            ),
        )
        cursor = self.db.execute(
            """
            UPDATE workflow_preflights
            SET consumed_at = ?, updated_at = ?
            WHERE workflow_preflight_id = ? AND status = 'passed'
              AND consumed_at IS NULL
            """,
            (
                self._iso(self._now()),
                self._iso(self._now()),
                context["workflow_preflight_id"],
            ),
        )
        if cursor.rowcount != 1:
            raise WorkflowRunError("PREFLIGHT_TOKEN_REPLAYED", "preflight token was consumed")

    @staticmethod
    def _consumption_matches(
        consumption: sqlite3.Row,
        *,
        context: sqlite3.Row,
        actor_context: AuthenticatedActorContext,
        idempotency_key: str,
        fingerprint: str,
    ) -> bool:
        return bool(
            consumption["workflow_preflight_id"] == context["workflow_preflight_id"]
            and consumption["workspace_id"] == actor_context.workspace_id
            and consumption["actor_id"] == actor_context.actor_id
            and consumption["idempotency_key"] == idempotency_key
            and consumption["semantic_fingerprint"] == fingerprint
        )

    def _validate_transition(
        self,
        row: sqlite3.Row,
        target: RunStatus,
        *,
        receipt: RuntimeLoadReceiptReadiness | None,
        normalized_result_ready: bool,
        review_items_approved: bool,
        failed_step: str | None,
        error_code: str | None,
    ) -> None:
        current = RunStatus(row["status"])
        if current in TERMINAL_RUN_STATUSES or target not in _ALLOWED_TRANSITIONS.get(
            current,
            frozenset(),
        ):
            raise IllegalRunTransition()
        if target is RunStatus.FAILED:
            if not failed_step or not error_code:
                raise IllegalRunTransition()
        elif failed_step is not None or error_code is not None:
            raise IllegalRunTransition()
        if current is RunStatus.OUTPUT_VALIDATING and target is RunStatus.PENDING_REVIEW:
            if not normalized_result_ready:
                raise IllegalRunTransition()
        if current is RunStatus.PENDING_REVIEW and target is RunStatus.CONFIRMED:
            if not review_items_approved:
                raise IllegalRunTransition()
        if current is RunStatus.QUEUED and target is RunStatus.RUNNING:
            if receipt is None or not receipt.required_entries_ready:
                raise RuntimeLoadReceiptNotReady()
            expected_digest = self._runtime_lock_digest(row["runtime_plugin_lock_id"])
            if (
                receipt.workflow_run_id != row["id"]
                or receipt.runtime_plugin_lock_id != row["runtime_plugin_lock_id"]
                or receipt.runtime_plugin_lock_digest != expected_digest
                or row["runtime_load_receipt_id"] is not None
                or row["agent_session_id"] is not None
            ):
                raise RuntimeLoadReceiptNotReady()

    def _validate_agent_session_binding(
        self,
        run: sqlite3.Row,
        readiness: RuntimeLoadReceiptReadiness,
        agent_session_id: str,
    ) -> None:
        row = self.db.execute(
            """
            SELECT session.*, receipt.workflow_run_id AS receipt_run_id,
                   receipt.runtime_plugin_lock_id AS receipt_lock_id,
                   receipt.runtime_plugin_lock_digest AS receipt_lock_digest,
                   receipt.runtime_environment_id AS receipt_environment_id,
                   receipt.runtime_pool_id AS receipt_pool_id,
                   receipt.distribution_mode AS receipt_distribution_mode,
                   receipt.runtime_node_id AS receipt_node_id,
                   receipt.artifact_set_hash AS receipt_artifact_set_hash,
                   receipt.policy_revision AS receipt_policy_revision,
                   receipt.deployment_tier AS receipt_deployment_tier,
                   receipt.required_entries_ready AS receipt_ready
            FROM agent_sessions AS session
            JOIN runtime_load_receipts AS receipt
              ON receipt.receipt_id = session.runtime_load_receipt_id
            WHERE session.agent_session_id = ?
            """,
            (agent_session_id,),
        ).fetchone()
        if row is None:
            raise AgentSessionNotReady()
        expected = {
            "workflow_run_id": run["id"],
            "runtime_load_receipt_id": readiness.receipt_id,
            "runtime_plugin_lock_id": run["runtime_plugin_lock_id"],
            "runtime_plugin_lock_digest": readiness.runtime_plugin_lock_digest,
            "runtime_environment_id": row["receipt_environment_id"],
            "runtime_pool_id": row["receipt_pool_id"],
            "distribution_mode": row["receipt_distribution_mode"],
            "runtime_node_id": row["receipt_node_id"],
            "artifact_set_hash": row["receipt_artifact_set_hash"],
            "policy_revision": row["receipt_policy_revision"],
            "deployment_tier": row["receipt_deployment_tier"],
        }
        if (
            row["status"] != "creating"
            or not bool(row["receipt_ready"])
            or row["receipt_run_id"] != run["id"]
            or row["receipt_lock_id"] != run["runtime_plugin_lock_id"]
            or row["receipt_lock_digest"] != readiness.runtime_plugin_lock_digest
            or any(row[key] != value for key, value in expected.items())
        ):
            raise AgentSessionNotReady()

    def _runtime_lock_digest(self, runtime_plugin_lock_id: str) -> str:
        row = self.db.execute(
            "SELECT lock_json FROM deck_runtime_plugin_locks WHERE id = ?",
            (runtime_plugin_lock_id,),
        ).fetchone()
        if row is None:
            raise RuntimeLoadReceiptNotReady()
        return self._lock_digest(row["lock_json"])

    def _insert_transition(
        self,
        *,
        workflow_run_id: str,
        transition_seq: int,
        from_status: RunStatus | None,
        to_status: RunStatus,
        actor_id: str,
        reason_code: str | None,
        occurred_at: datetime,
        failed_step: str | None = None,
        error_code: str | None = None,
    ) -> None:
        self.db.execute(
            """
            INSERT INTO workflow_run_transitions (
                id, workflow_run_id, transition_seq, from_status, to_status,
                actor_id, reason_code, failed_step, error_code, occurred_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "wrt_" + uuid.uuid4().hex,
                workflow_run_id,
                transition_seq,
                from_status.value if from_status is not None else None,
                to_status.value,
                actor_id,
                reason_code,
                failed_step,
                error_code,
                self._iso(occurred_at),
            ),
        )

    def _select_scoped_run(
        self,
        workflow_run_id: str,
        actor_context: AuthenticatedActorContext,
    ) -> sqlite3.Row | None:
        return self.db.execute(
            """
            SELECT * FROM workflow_runs
            WHERE id = ? AND workspace_id = ? AND created_by = ?
            """,
            (
                workflow_run_id,
                actor_context.workspace_id,
                actor_context.actor_id,
            ),
        ).fetchone()

    @classmethod
    def _frozen_source_from_context(
        cls,
        context: sqlite3.Row,
        *,
        source_voice_thread_id: str | None,
        source_message_id: str | None,
        source_message_time: datetime | None,
    ) -> dict[str, Any]:
        return {
            "deck_plugin_id": context["deck_plugin_id"],
            "deck_plugin_version": context["deck_plugin_version"],
            "workflow_definition_ref": context["workflow_definition_ref"],
            "deck_runtime_snapshot_id": context["deck_runtime_snapshot_id"],
            "deck_plugin_manifest_hash": context["manifest_hash"],
            "deck_plugin_binding_id": context["deck_plugin_binding_id"],
            "binding_revision": context["binding_revision"],
            "runtime_plugin_lock_id": context["runtime_plugin_lock_id"],
            "input_hash": context["input_hash"],
            "source_voice_thread_id": source_voice_thread_id,
            "source_message_id": source_message_id,
            "source_message_time": cls._iso(source_message_time)
            if source_message_time is not None
            else None,
        }

    @classmethod
    def _frozen_source_from_run(cls, run: WorkflowRun) -> dict[str, Any]:
        return {
            "deck_plugin_id": run.deck_plugin_id,
            "deck_plugin_version": run.deck_plugin_version,
            "workflow_definition_ref": run.workflow_definition_ref,
            "deck_runtime_snapshot_id": run.deck_runtime_snapshot_id,
            "deck_plugin_manifest_hash": run.deck_plugin_manifest_hash,
            "deck_plugin_binding_id": run.deck_plugin_binding_id,
            "binding_revision": run.binding_revision,
            "runtime_plugin_lock_id": run.runtime_plugin_lock_id,
            "input_hash": run.input_hash,
            "source_voice_thread_id": run.source_voice_thread_id,
            "source_message_id": run.source_message_id,
            "source_message_time": cls._iso(run.source_message_time)
            if run.source_message_time is not None
            else None,
        }

    @classmethod
    def _semantic_fingerprint(
        cls,
        context: sqlite3.Row,
        *,
        lock_digest: str,
        source_voice_thread_id: str | None,
        source_message_id: str | None,
        source_message_time: datetime | None,
        retry_of_run_id: str | None,
    ) -> str:
        # Token and preflight record identifiers are intentionally absent.
        semantic = cls._frozen_source_from_context(
            context,
            source_voice_thread_id=source_voice_thread_id,
            source_message_id=source_message_id,
            source_message_time=source_message_time,
        )
        semantic["runtime_plugin_lock_digest"] = lock_digest
        semantic["retry_of_run_id"] = retry_of_run_id
        return "sha256:" + hashlib.sha256(cls._canonical_json(semantic)).hexdigest()

    def _token_digest(self, token: str) -> str:
        digest = hmac.new(
            self._token_secret,
            b"workflow-run-token\x00" + token.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return "hmac-sha256:" + digest

    @classmethod
    def _lock_digest(cls, lock_json: str) -> str:
        parsed = json.loads(lock_json)
        return "sha256:" + hashlib.sha256(cls._canonical_json(parsed)).hexdigest()

    @staticmethod
    def _canonical_json(value: Any) -> bytes:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

    def _row_to_run(self, row: sqlite3.Row) -> WorkflowRun:
        return WorkflowRun(
            workflow_run_id=row["id"],
            deck_plugin_id=row["deck_plugin_id"],
            deck_plugin_version=row["deck_plugin_version"],
            workflow_definition_ref=row["workflow_definition_ref"],
            deck_runtime_snapshot_id=row["deck_runtime_snapshot_id"],
            status=RunStatus(row["status"]),
            failed_step=row["failed_step"],
            error_code=row["error_code"],
            retry_of_run_id=row["retry_of_run_id"],
            deck_plugin_manifest_hash=row["deck_plugin_manifest_hash"],
            deck_plugin_binding_id=row["deck_plugin_binding_id"],
            binding_revision=row["binding_revision"],
            runtime_plugin_lock_id=row["runtime_plugin_lock_id"],
            runtime_load_receipt_id=row["runtime_load_receipt_id"],
            workflow_preflight_id=row["workflow_preflight_id"],
            agent_session_id=row["agent_session_id"],
            source_voice_thread_id=row["source_voice_thread_id"],
            source_message_id=row["source_message_id"],
            source_message_time=self._parse_datetime(row["source_message_time"])
            if row["source_message_time"]
            else None,
            workspace_id=row["workspace_id"],
            idempotency_key=row["idempotency_key"],
            input_hash=row["input_hash"],
            semantic_fingerprint=row["semantic_fingerprint"],
            status_version=row["status_version"],
            created_by=row["created_by"],
            created_at=self._parse_datetime(row["created_at"]),
            started_at=self._parse_datetime(row["started_at"])
            if row["started_at"]
            else None,
            completed_at=self._parse_datetime(row["completed_at"])
            if row["completed_at"]
            else None,
        )

    def _row_to_transition(self, row: sqlite3.Row) -> WorkflowRunTransition:
        return WorkflowRunTransition(
            transition_id=row["id"],
            workflow_run_id=row["workflow_run_id"],
            transition_seq=row["transition_seq"],
            from_status=RunStatus(row["from_status"])
            if row["from_status"]
            else None,
            to_status=RunStatus(row["to_status"]),
            actor_id=row["actor_id"],
            reason_code=row["reason_code"],
            failed_step=row["failed_step"],
            error_code=row["error_code"],
            occurred_at=self._parse_datetime(row["occurred_at"]),
        )

    def _checkpoint(self, name: str) -> None:
        if self._failure_injector is not None:
            self._failure_injector(name)

    def _require_clean_transaction(self) -> None:
        if self.db.in_transaction:
            raise RuntimeError("workflow run service requires a clean transaction boundary")

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    @staticmethod
    def _iso(value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat(timespec="microseconds")
