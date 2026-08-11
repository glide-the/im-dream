"""Run-scoped ClaudeAgent Session orchestration over task_008 readers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime, timedelta
import inspect
import json
from typing import Any, Literal, Protocol
import uuid

try:
    from backend.models.agent_session import (
        AgentSession,
        AgentSessionStatus,
        SessionStartResult,
        canonical_json,
        compute_plugin_set_hash,
        compute_session_request_key,
        sha256_digest,
    )
    from backend.models.deck_plugin import DeckRuntimePluginLock
    from backend.models.runtime_plugin import (
        RuntimeLoadReceipt,
        compute_artifact_set_hash,
        runtime_lock_digest,
    )
    from backend.models.workflow_run import (
        AuthenticatedActorContext,
        RunStatus,
        RuntimeLoadReceiptReadiness,
        WorkflowRun,
    )
    from backend.services.workflow.run_service import WorkflowRunService
except ModuleNotFoundError:  # Support the backend directory on PYTHONPATH.
    from models.agent_session import (
        AgentSession,
        AgentSessionStatus,
        SessionStartResult,
        canonical_json,
        compute_plugin_set_hash,
        compute_session_request_key,
        sha256_digest,
    )
    from models.deck_plugin import DeckRuntimePluginLock
    from models.runtime_plugin import (
        RuntimeLoadReceipt,
        compute_artifact_set_hash,
        runtime_lock_digest,
    )
    from models.workflow_run import (
        AuthenticatedActorContext,
        RunStatus,
        RuntimeLoadReceiptReadiness,
        WorkflowRun,
    )
    from services.workflow.run_service import WorkflowRunService


AGENT_SESSION_CREATE_CONFLICT = "AGENT_SESSION_CREATE_CONFLICT"
AGENT_SESSION_RECEIPT_INVALID = "AGENT_SESSION_RECEIPT_INVALID"
AGENT_SESSION_SETTINGS_INVALID = "AGENT_SESSION_SETTINGS_INVALID"
AGENT_SESSION_START_FAILED = "AGENT_SESSION_START_FAILED"
AGENT_SESSION_COMMIT_FAILED = "AGENT_SESSION_COMMIT_FAILED"
AGENT_SESSION_TERMINATE_UNCONFIRMED = "AGENT_SESSION_TERMINATE_UNCONFIRMED"


class AgentSessionError(RuntimeError):
    def __init__(self, code: str, summary: str) -> None:
        self.code = code
        self.summary = summary
        super().__init__(summary)


class RunSessionAdapter(Protocol):
    async def start_session(
        self,
        *,
        agent_session_id: str,
        session_request_key: str,
        settings_json: str,
        runtime_node_id: str,
        allow_query: Literal[False],
    ) -> SessionStartResult | Mapping[str, object]: ...

    async def terminate_session(
        self,
        *,
        agent_session_id: str,
        reason_code: str,
    ) -> None: ...


class ReceiptReader(Protocol):
    def read_receipt(
        self,
        receipt_id: str,
    ) -> RuntimeLoadReceipt | Awaitable[RuntimeLoadReceipt]: ...

    def read_workflow_readiness(
        self,
        receipt_id: str,
    ) -> dict[str, object] | Awaitable[dict[str, object]]: ...


class SessionManager:
    """Validate immutable evidence, acquire one owner, and activate atomically."""

    def __init__(
        self,
        db: Any,
        *,
        receipt_reader: ReceiptReader,
        adapter: RunSessionAdapter,
        workflow_run_service: WorkflowRunService,
        clock: Callable[[], datetime] | None = None,
        creating_lease_seconds: int = 30,
    ) -> None:
        if not 1 <= creating_lease_seconds <= 300:
            raise ValueError("creating lease must be within 1..300 seconds")
        if db.in_transaction:
            raise RuntimeError("session manager requires a clean transaction boundary")
        self.db = db
        self._receipt_reader = receipt_reader
        self._adapter = adapter
        self._run_service = workflow_run_service
        self._clock = clock or (lambda: datetime.now(UTC))
        self._creating_lease_seconds = creating_lease_seconds

    async def create_or_resume_session(
        self,
        *,
        workflow_run_id: str,
        runtime_load_receipt_id: str,
        runtime_lock: DeckRuntimePluginLock,
        approved_capabilities: list[str],
        trusted_marketplaces: Mapping[str, str],
        actor_context: AuthenticatedActorContext,
    ) -> AgentSession:
        """Create or replay a Session without ever sending the first query."""

        try:
            receipt_raw = self._receipt_reader.read_receipt(runtime_load_receipt_id)
            receipt = RuntimeLoadReceipt.model_validate(await _resolve(receipt_raw))
            readiness_raw = await _resolve(
                self._receipt_reader.read_workflow_readiness(
                    runtime_load_receipt_id
                )
            )
            if set(readiness_raw) != {
                "receipt_id",
                "workflow_run_id",
                "runtime_plugin_lock_id",
                "runtime_plugin_lock_digest",
                "required_entries_ready",
            }:
                raise ValueError("readiness projection must contain exactly five keys")
            readiness = RuntimeLoadReceiptReadiness.model_validate(readiness_raw)
            run = self._load_scoped_queued_run(workflow_run_id, actor_context)
            self._validate_receipt(
                run=run,
                receipt=receipt,
                readiness=readiness,
                runtime_lock=runtime_lock,
            )
            settings_json, settings_hash, plugin_set_hash = self._build_settings(
                runtime_lock=runtime_lock,
                receipt=receipt,
                approved_capabilities=approved_capabilities,
                trusted_marketplaces=trusted_marketplaces,
            )
        except AgentSessionError:
            self._rollback_read_transaction()
            raise
        except Exception as exc:
            self._rollback_read_transaction()
            raise AgentSessionError(
                AGENT_SESSION_RECEIPT_INVALID,
                "runtime load receipt or frozen Session inputs are invalid",
            ) from exc

        self._rollback_read_transaction()
        request_key = compute_session_request_key(
            workflow_run_id,
            runtime_load_receipt_id,
            settings_hash,
        )
        session, is_owner, owner_token = self._acquire_attempt(
            run=run,
            receipt=receipt,
            settings_json=settings_json,
            settings_hash=settings_hash,
            plugin_set_hash=plugin_set_hash,
            session_request_key=request_key,
        )
        if not is_owner:
            return session
        if session.agent_session_id in {
            run.source_voice_thread_id,
            run.source_message_id,
        }:
            self._mark_failed(
                session.agent_session_id,
                error_code=AGENT_SESSION_SETTINGS_INVALID,
                reason_code="SESSION_SOURCE_ID_COLLISION",
            )
            raise AgentSessionError(
                AGENT_SESSION_SETTINGS_INVALID,
                "Voice source identifiers cannot be reused as Session identifiers",
            )

        try:
            raw_result = await self._adapter.start_session(
                agent_session_id=session.agent_session_id,
                session_request_key=session.session_request_key,
                settings_json=session.settings_json,
                runtime_node_id=session.runtime_node_id,
                allow_query=False,
            )
            result = SessionStartResult.model_validate(raw_result)
            if (
                result.agent_session_id != session.agent_session_id
                or result.session_request_key != session.session_request_key
            ):
                raise ValueError("adapter acknowledgement does not match Session")
            self._record_remote_start(result, owner_token)
        except Exception as exc:
            self._mark_failed(
                session.agent_session_id,
                error_code=AGENT_SESSION_START_FAILED,
                reason_code="ADAPTER_START_FAILED",
            )
            try:
                await self._run_service.transition_run(
                    workflow_run_id,
                    RunStatus.FAILED,
                    actor_context,
                    failed_step="agent_session_start",
                    error_code=AGENT_SESSION_START_FAILED,
                )
            except Exception:
                pass
            raise AgentSessionError(
                AGENT_SESSION_START_FAILED,
                "run-scoped adapter failed before Session activation",
            ) from exc

        try:
            await self._run_service.transition_run(
                workflow_run_id,
                RunStatus.RUNNING,
                actor_context,
                runtime_load_receipt_id=runtime_load_receipt_id,
                agent_session_id=session.agent_session_id,
                reason_code="agent_session_active",
            )
        except Exception as exc:
            try:
                await self._adapter.terminate_session(
                    agent_session_id=session.agent_session_id,
                    reason_code=AGENT_SESSION_COMMIT_FAILED,
                )
            except Exception as terminate_exc:
                self._mark_compensation_pending(session.agent_session_id)
                raise AgentSessionError(
                    AGENT_SESSION_TERMINATE_UNCONFIRMED,
                    "database commit failed and remote termination is unconfirmed",
                ) from terminate_exc
            self._mark_failed(
                session.agent_session_id,
                error_code=AGENT_SESSION_COMMIT_FAILED,
                reason_code="REMOTE_TERMINATED_AFTER_COMMIT_FAILURE",
            )
            raise AgentSessionError(
                AGENT_SESSION_COMMIT_FAILED,
                "Session activation transaction failed and was compensated",
            ) from exc
        return self.read_session(session.agent_session_id)

    async def terminate_session(
        self,
        agent_session_id: str,
        *,
        reason_code: str,
        failed_error_code: str | None = None,
        actor_context: AuthenticatedActorContext | None = None,
    ) -> AgentSession:
        session = self.read_session(agent_session_id)
        if session.status in {
            AgentSessionStatus.TERMINATED,
            AgentSessionStatus.FAILED,
        }:
            return session
        await self._adapter.terminate_session(
            agent_session_id=agent_session_id,
            reason_code=reason_code,
        )
        now = self._iso(self._now())
        if failed_error_code is None and session.status is AgentSessionStatus.ACTIVE:
            self.db.execute(
                """
                UPDATE agent_sessions
                SET status = 'terminated', terminated_at = %s,
                    termination_reason_code = %s, lease_expires_at = NULL,
                    owner_token = NULL
                WHERE agent_session_id = %s AND status = 'active'
                """,
                (now, reason_code, agent_session_id),
            )
        else:
            self._mark_failed(
                agent_session_id,
                error_code=failed_error_code or "AGENT_SESSION_TERMINATED_DURING_CREATE",
                reason_code=reason_code,
            )
        if self.db.in_transaction:
            self.db.commit()
        terminated = self.read_session(agent_session_id)
        if actor_context is not None:
            if reason_code == "USER_CANCELLED":
                await self._run_service.transition_run(
                    session.workflow_run_id,
                    RunStatus.CANCELLED,
                    actor_context,
                    reason_code=reason_code,
                )
            elif failed_error_code is not None:
                await self._run_service.transition_run(
                    session.workflow_run_id,
                    RunStatus.FAILED,
                    actor_context,
                    failed_step="agent_session_runtime",
                    error_code=failed_error_code,
                    reason_code=reason_code,
                )
        return terminated

    def read_session(self, agent_session_id: str) -> AgentSession:
        row = self.db.execute(
            "SELECT * FROM agent_sessions WHERE agent_session_id = %s",
            (agent_session_id,),
        ).fetchone()
        if row is None:
            raise KeyError(agent_session_id)
        return self._row_to_session(row)

    def _load_scoped_queued_run(
        self,
        workflow_run_id: str,
        actor_context: AuthenticatedActorContext,
    ) -> WorkflowRun:
        row = self.db.execute(
            """
            SELECT * FROM workflow_runs
            WHERE id = %s AND workspace_id = %s AND created_by = %s
            """,
            (
                workflow_run_id,
                actor_context.workspace_id,
                actor_context.actor_id,
            ),
        ).fetchone()
        if row is None:
            raise AgentSessionError(
                AGENT_SESSION_RECEIPT_INVALID,
                "queued Workflow Run was not found",
            )
        run = self._run_service._row_to_run(row)
        if (
            run.status is not RunStatus.QUEUED
            or run.runtime_load_receipt_id is not None
            or run.agent_session_id is not None
        ):
            existing = self.db.execute(
                """
                SELECT * FROM agent_sessions
                WHERE workflow_run_id = %s AND status = 'active'
                """,
                (workflow_run_id,),
            ).fetchone()
            if (
                run.status is RunStatus.RUNNING
                and existing is not None
                and run.agent_session_id == existing["agent_session_id"]
            ):
                return run
            raise AgentSessionError(
                AGENT_SESSION_CREATE_CONFLICT,
                "Workflow Run is not available for Session creation",
            )
        return run

    def _validate_receipt(
        self,
        *,
        run: WorkflowRun,
        receipt: RuntimeLoadReceipt,
        readiness: RuntimeLoadReceiptReadiness,
        runtime_lock: DeckRuntimePluginLock,
    ) -> None:
        lock_row = self.db.execute(
            "SELECT lock_json FROM deck_runtime_plugin_locks WHERE id = %s",
            (run.runtime_plugin_lock_id,),
        ).fetchone()
        receipt_row = self.db.execute(
            "SELECT * FROM runtime_load_receipts WHERE receipt_id = %s",
            (receipt.receipt_id,),
        ).fetchone()
        if lock_row is None or receipt_row is None:
            raise AgentSessionError(
                AGENT_SESSION_RECEIPT_INVALID,
                "frozen runtime lock was not found",
            )
        authoritative_digest = runtime_lock_digest(lock_row["lock_json"])
        expected_artifact_set = compute_artifact_set_hash(runtime_lock)
        persisted_lock = json.loads(lock_row["lock_json"])
        persisted_plugins = {
            item["claude_code_plugin_id"]: {
                "artifact_digest": item["artifact_digest"],
                "capability_bindings": sorted(
                    set(item.get("capability_bindings", []))
                ),
                "required": bool(item["required"]),
                "resolved_version": item["resolved_version"],
                "source_ref": item.get("source_ref"),
            }
            for item in persisted_lock.get("claude_code_plugins", [])
        }
        supplied_plugins = {
            item.claude_code_plugin_id: {
                "artifact_digest": item.artifact_digest,
                "capability_bindings": sorted(set(item.capability_bindings)),
                "required": item.required,
                "resolved_version": item.resolved_version,
                "source_ref": item.source_ref,
            }
            for item in runtime_lock.claude_code_plugins
        }
        persisted_fields = {
            "workflow_run_id": receipt.workflow_run_id,
            "runtime_plugin_lock_id": receipt.runtime_plugin_lock_id,
            "runtime_plugin_lock_digest": receipt.runtime_plugin_lock_digest,
            "runtime_environment_id": receipt.runtime_environment_id,
            "runtime_pool_id": receipt.runtime_pool_id,
            "distribution_mode": receipt.distribution_mode,
            "runtime_node_id": receipt.runtime_node_id,
            "artifact_set_hash": receipt.artifact_set_hash,
            "policy_revision": receipt.policy_revision,
            "deployment_tier": receipt.deployment_tier,
            "scope": receipt.scope,
            "readiness_state": receipt.readiness_state,
        }
        persisted_entry_rows = self.db.execute(
            """
            SELECT * FROM runtime_load_receipt_entries
            WHERE receipt_id = %s ORDER BY claude_code_plugin_id
            """,
            (receipt.receipt_id,),
        ).fetchall()
        persisted_entry_projection = [
            {
                "artifact_digest": row["artifact_digest"],
                "claude_code_plugin_id": row["claude_code_plugin_id"],
                "load_status": row["load_status"],
                "loaded_capabilities": json.loads(
                    row["loaded_capabilities_json"]
                ),
                "materialized_digest": row["materialized_digest"],
                "required": bool(row["required"]),
                "resolved_version": row["resolved_version"],
            }
            for row in persisted_entry_rows
        ]
        receipt_entry_projection = [
            {
                "artifact_digest": entry.artifact_digest,
                "claude_code_plugin_id": entry.claude_code_plugin_id,
                "load_status": entry.load_status,
                "loaded_capabilities": entry.loaded_capabilities,
                "materialized_digest": entry.materialized_digest,
                "required": entry.required,
                "resolved_version": entry.resolved_version,
            }
            for entry in sorted(
                receipt.entries,
                key=lambda item: item.claude_code_plugin_id,
            )
        ]
        if (
            runtime_lock.runtime_plugin_lock_id != run.runtime_plugin_lock_id
            or persisted_lock.get("runtime_plugin_lock_id")
            != runtime_lock.runtime_plugin_lock_id
            or persisted_plugins != supplied_plugins
            or receipt.receipt_id != readiness.receipt_id
            or receipt.workflow_run_id != run.workflow_run_id
            or readiness.workflow_run_id != run.workflow_run_id
            or receipt.runtime_plugin_lock_id != run.runtime_plugin_lock_id
            or readiness.runtime_plugin_lock_id != run.runtime_plugin_lock_id
            or receipt.runtime_plugin_lock_digest != authoritative_digest
            or readiness.runtime_plugin_lock_digest != authoritative_digest
            or not receipt.required_entries_ready
            or not readiness.required_entries_ready
            or receipt.runtime_pool_id != receipt.runtime_environment_id
            or receipt.distribution_mode != "local_persistent"
            or receipt.artifact_set_hash != expected_artifact_set
            or receipt.scope != "session"
            or receipt.readiness_state != "session_loaded"
            or receipt.deployment_tier not in {"development", "test"}
            or any(
                receipt_row[key] != value
                for key, value in persisted_fields.items()
            )
            or bool(receipt_row["required_entries_ready"])
            != receipt.required_entries_ready
            or persisted_entry_projection != receipt_entry_projection
        ):
            raise AgentSessionError(
                AGENT_SESSION_RECEIPT_INVALID,
                "Receipt does not match the frozen run, lock, or placement",
            )

        receipt_entries = {
            item.claude_code_plugin_id: item for item in receipt.entries
        }
        locked_entries = {
            item.claude_code_plugin_id: item
            for item in runtime_lock.claude_code_plugins
        }
        if set(receipt_entries) != set(locked_entries):
            raise AgentSessionError(
                AGENT_SESSION_RECEIPT_INVALID,
                "Receipt plugin set does not match the frozen lock",
            )
        for plugin_id, locked in locked_entries.items():
            item = receipt_entries[plugin_id]
            if (
                item.resolved_version != locked.resolved_version
                or item.artifact_digest != locked.artifact_digest
                or item.materialized_digest != locked.artifact_digest
                or item.required != locked.required
                or item.load_status != "loaded"
                or item.loaded_capabilities != sorted(set(locked.capability_bindings))
            ):
                raise AgentSessionError(
                    AGENT_SESSION_RECEIPT_INVALID,
                    "Receipt entry does not match locked plugin evidence",
                )

    def _build_settings(
        self,
        *,
        runtime_lock: DeckRuntimePluginLock,
        receipt: RuntimeLoadReceipt,
        approved_capabilities: list[str],
        trusted_marketplaces: Mapping[str, str],
    ) -> tuple[str, str, str]:
        approved = sorted(set(approved_capabilities))
        if approved != approved_capabilities:
            raise AgentSessionError(
                AGENT_SESSION_SETTINGS_INVALID,
                "approved capabilities must be sorted and unique",
            )
        locked_capabilities = sorted(
            {
                capability
                for entry in runtime_lock.claude_code_plugins
                for capability in entry.capability_bindings
            }
        )
        if approved != locked_capabilities:
            raise AgentSessionError(
                AGENT_SESSION_SETTINGS_INVALID,
                "approved capabilities must equal the frozen capability projection",
            )
        aliases = {
            entry.claude_code_plugin_id.rsplit("@", 1)[1]
            for entry in runtime_lock.claude_code_plugins
            if "@" in entry.claude_code_plugin_id
        }
        if not aliases or aliases != set(trusted_marketplaces):
            raise AgentSessionError(
                AGENT_SESSION_SETTINGS_INVALID,
                "trusted marketplace projection must exactly cover locked plugins",
            )
        if any(
            not value
            or len(value) > 512
            or any(
                marker in value.lower()
                for marker in ("secret", "token", "credential", "password")
            )
            for value in trusted_marketplaces.values()
        ):
            raise AgentSessionError(
                AGENT_SESSION_SETTINGS_INVALID,
                "trusted marketplace references cannot be empty",
            )
        settings = {
            "enabledPlugins": {
                entry.claude_code_plugin_id: True
                for entry in sorted(
                    runtime_lock.claude_code_plugins,
                    key=lambda item: item.claude_code_plugin_id,
                )
            },
            "extraKnownMarketplaces": {
                alias: {"source": trusted_marketplaces[alias]}
                for alias in sorted(aliases)
            },
            "pluginPolicy": {"allowedCapabilities": approved},
        }
        settings_json = canonical_json(settings).decode("utf-8")
        plugin_entries = [
            {
                "artifact_digest": entry.artifact_digest,
                "capabilities": sorted(set(entry.capability_bindings)),
                "claude_code_plugin_id": entry.claude_code_plugin_id,
                "required": entry.required,
                "resolved_version": entry.resolved_version,
            }
            for entry in runtime_lock.claude_code_plugins
        ]
        return (
            settings_json,
            sha256_digest(settings_json.encode("utf-8")),
            compute_plugin_set_hash(plugin_entries),
        )

    def _acquire_attempt(
        self,
        *,
        run: WorkflowRun,
        receipt: RuntimeLoadReceipt,
        settings_json: str,
        settings_hash: str,
        plugin_set_hash: str,
        session_request_key: str,
    ) -> tuple[AgentSession, bool, str]:
        now = self._now()
        lease_expires = now + timedelta(seconds=self._creating_lease_seconds)
        owner_token = uuid.uuid4().hex
        try:
            self.db.execute("BEGIN")
            existing_key = self.db.execute(
                "SELECT * FROM agent_sessions WHERE session_request_key = %s",
                (session_request_key,),
            ).fetchone()
            if existing_key is not None:
                existing = self._row_to_session(existing_key)
                if existing.status is not AgentSessionStatus.CREATING:
                    self.db.commit()
                    return existing, False, owner_token
                if (
                    existing.lease_expires_at is not None
                    and existing.lease_expires_at > now
                ):
                    self.db.commit()
                    return existing, False, owner_token
                cursor = self.db.execute(
                    """
                    UPDATE agent_sessions
                    SET lease_expires_at = %s, owner_token = %s
                    WHERE agent_session_id = %s AND status = 'creating'
                      AND lease_expires_at <= %s
                    """,
                    (
                        self._iso(lease_expires),
                        owner_token,
                        existing.agent_session_id,
                        self._iso(now),
                    ),
                )
                if cursor.rowcount != 1:
                    raise AgentSessionError(
                        AGENT_SESSION_CREATE_CONFLICT,
                        "Session ownership changed during recovery",
                    )
                row = self.db.execute(
                    "SELECT * FROM agent_sessions WHERE agent_session_id = %s",
                    (existing.agent_session_id,),
                ).fetchone()
                assert row is not None
                self.db.commit()
                return self._row_to_session(row), True, owner_token

            live = self.db.execute(
                """
                SELECT * FROM agent_sessions
                WHERE workflow_run_id = %s AND status IN ('creating', 'active')
                """,
                (run.workflow_run_id,),
            ).fetchone()
            if live is not None:
                raise AgentSessionError(
                    AGENT_SESSION_CREATE_CONFLICT,
                    "a competing Receipt or settings set already owns the run",
                )
            attempt_number = int(
                self.db.execute(
                    """
                    SELECT COALESCE(MAX(attempt_number), 0) + 1
                    FROM agent_sessions WHERE workflow_run_id = %s
                    """,
                    (run.workflow_run_id,),
                ).fetchone()[0]
            )
            agent_session_id = "as_" + uuid.uuid4().hex
            self.db.execute(
                """
                INSERT INTO agent_sessions (
                    agent_session_id, workflow_run_id, runtime_load_receipt_id,
                    runtime_environment_id, runtime_pool_id, distribution_mode,
                    runtime_node_id, artifact_set_hash, policy_revision,
                    deployment_tier, runtime_plugin_lock_id,
                    runtime_plugin_lock_digest, settings_json, settings_hash,
                    plugin_set_hash, session_request_key, attempt_number, status,
                    created_at, lease_expires_at, owner_token
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                          'creating', %s, %s, %s)
                """,
                (
                    agent_session_id,
                    run.workflow_run_id,
                    receipt.receipt_id,
                    receipt.runtime_environment_id,
                    receipt.runtime_pool_id,
                    receipt.distribution_mode,
                    receipt.runtime_node_id,
                    receipt.artifact_set_hash,
                    receipt.policy_revision,
                    receipt.deployment_tier,
                    receipt.runtime_plugin_lock_id,
                    receipt.runtime_plugin_lock_digest,
                    settings_json,
                    settings_hash,
                    plugin_set_hash,
                    session_request_key,
                    attempt_number,
                    self._iso(now),
                    self._iso(lease_expires),
                    owner_token,
                ),
            )
            row = self.db.execute(
                "SELECT * FROM agent_sessions WHERE agent_session_id = %s",
                (agent_session_id,),
            ).fetchone()
            assert row is not None
            self.db.commit()
            return self._row_to_session(row), True, owner_token
        except Exception:
            if self.db.in_transaction:
                self.db.rollback()
            raise

    def _record_remote_start(
        self,
        result: SessionStartResult,
        owner_token: str,
    ) -> None:
        cursor = self.db.execute(
            """
            UPDATE agent_sessions
            SET remote_session_ref = %s
            WHERE agent_session_id = %s AND status = 'creating' AND owner_token = %s
            """,
            (result.remote_session_ref, result.agent_session_id, owner_token),
        )
        if cursor.rowcount != 1:
            self.db.rollback()
            raise AgentSessionError(
                AGENT_SESSION_CREATE_CONFLICT,
                "Session owner lease changed during adapter start",
            )
        self.db.commit()

    def _mark_failed(
        self,
        agent_session_id: str,
        *,
        error_code: str,
        reason_code: str,
    ) -> None:
        self.db.execute(
            """
            UPDATE agent_sessions
            SET status = 'failed', error_code = %s, termination_reason_code = %s,
                terminated_at = %s, lease_expires_at = NULL, owner_token = NULL
            WHERE agent_session_id = %s AND status IN ('creating', 'active')
            """,
            (error_code, reason_code, self._iso(self._now()), agent_session_id),
        )
        self.db.commit()

    def _mark_compensation_pending(self, agent_session_id: str) -> None:
        lease = self._now() + timedelta(seconds=self._creating_lease_seconds)
        self.db.execute(
            """
            UPDATE agent_sessions
            SET lease_expires_at = %s, owner_token = 'compensation_pending'
            WHERE agent_session_id = %s AND status = 'creating'
            """,
            (self._iso(lease), agent_session_id),
        )
        self.db.commit()

    def _row_to_session(self, row: Any) -> AgentSession:
        return AgentSession(
            agent_session_id=row["agent_session_id"],
            workflow_run_id=row["workflow_run_id"],
            runtime_load_receipt_id=row["runtime_load_receipt_id"],
            runtime_environment_id=row["runtime_environment_id"],
            runtime_pool_id=row["runtime_pool_id"],
            distribution_mode=row["distribution_mode"],
            runtime_node_id=row["runtime_node_id"],
            artifact_set_hash=row["artifact_set_hash"],
            policy_revision=row["policy_revision"],
            deployment_tier=row["deployment_tier"],
            runtime_plugin_lock_id=row["runtime_plugin_lock_id"],
            runtime_plugin_lock_digest=row["runtime_plugin_lock_digest"],
            settings_json=row["settings_json"],
            settings_hash=row["settings_hash"],
            plugin_set_hash=row["plugin_set_hash"],
            session_request_key=row["session_request_key"],
            attempt_number=row["attempt_number"],
            status=AgentSessionStatus(row["status"]),
            error_code=row["error_code"],
            termination_reason_code=row["termination_reason_code"],
            created_at=self._parse_datetime(row["created_at"]),
            started_at=self._parse_datetime(row["started_at"])
            if row["started_at"]
            else None,
            terminated_at=self._parse_datetime(row["terminated_at"])
            if row["terminated_at"]
            else None,
            lease_expires_at=self._parse_datetime(row["lease_expires_at"])
            if row["lease_expires_at"]
            else None,
            remote_session_ref=row["remote_session_ref"],
        )

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _rollback_read_transaction(self) -> None:
        if self.db.in_transaction:
            self.db.rollback()

    @staticmethod
    def _parse_datetime(value: datetime | str) -> datetime:
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            raise TypeError("agent session timestamp must be datetime or ISO-8601 text")
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    @staticmethod
    def _iso(value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat(timespec="microseconds")


async def _resolve(value: Any | Awaitable[Any]) -> Any:
    return await value if inspect.isawaitable(value) else value
