"""Activate one queued Dream Workflow Run from assembled server evidence.

The workspace packer proves the frozen plugin bytes before the Claude subprocess
starts. Context assembly joins those verified bytes, the actor-owned canonical
Thread and the frozen Workflow binding into the existing immutable runtime load
receipt and Agent Session contracts before Session Execution. It never accepts
browser provenance and never controls the Claude query.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any, Callable
import uuid

try:
    from backend.models.agent_session import SessionStartResult
    from backend.models.deck_plugin import DeckRuntimePluginLock
    from backend.models.runtime_plugin import (
        HeadlessPluginState,
        ReconcileResult,
        RuntimePlacementContext,
        RuntimePluginMaterialization,
        compute_artifact_set_hash,
    )
    from backend.models.workflow_run import (
        AuthenticatedActorContext,
        RunStatus,
        WorkflowRun,
    )
    from backend.services.claude_agent.session_manager import SessionManager
    from backend.services.runtime_plugin.local_placement import LocalRuntimePlacement
    from backend.services.runtime_plugin.reconcile_service import ReconcileService
    from backend.services.workflow.run_service import WorkflowRunService
except ModuleNotFoundError:  # Support the backend directory on PYTHONPATH.
    from models.agent_session import SessionStartResult
    from models.deck_plugin import DeckRuntimePluginLock
    from models.runtime_plugin import (
        HeadlessPluginState,
        ReconcileResult,
        RuntimePlacementContext,
        RuntimePluginMaterialization,
        compute_artifact_set_hash,
    )
    from models.workflow_run import AuthenticatedActorContext, RunStatus, WorkflowRun
    from services.claude_agent.session_manager import SessionManager
    from services.runtime_plugin.local_placement import LocalRuntimePlacement
    from services.runtime_plugin.reconcile_service import ReconcileService
    from services.workflow.run_service import WorkflowRunService


DREAM_RUNTIME_INIT_INVALID = "DREAM_RUNTIME_INIT_INVALID"
DREAM_RUNTIME_NOT_READY = "DREAM_RUNTIME_NOT_READY"
_REQUIRED_DREAM_TOOL = "mcp__story_workspace__write_dream_run"
_DREAM_MATERIALIZATION_POLICY_REVISION = "dream-launch/v1"


class StoryWorkspaceDreamRuntimeActivationError(RuntimeError):
    def __init__(self, code: str, summary: str) -> None:
        self.code = code
        super().__init__(summary)


class _ObservedRuntimePolicy:
    """Policy projection used only by ReconcileService's receipt validator."""

    def __init__(self, policy_revision: str) -> None:
        self.policy_revision = policy_revision

    def marketplace_for(self, _plugin_id: str, _source_ref: str) -> Any:
        raise RuntimeError("SDK-init receipt activation does not resolve marketplaces")


class _UnavailableReconcileDependency:
    """Fail closed if a receipt-only ReconcileService is used for execution."""

    policy_revision = "unavailable"

    def __getattr__(self, _name: str) -> Any:
        raise RuntimeError("receipt-only reconcile dependency is unavailable")


class _AssembledThreadSessionAdapter:
    """Bind the runtime receipt to the canonical Thread assembled for the turn."""

    def __init__(self, remote_session_ref: str) -> None:
        self._remote_session_ref = remote_session_ref

    async def start_session(
        self,
        *,
        agent_session_id: str,
        session_request_key: str,
        settings_json: str,
        runtime_node_id: str,
        allow_query: bool,
    ) -> SessionStartResult:
        del settings_json, runtime_node_id
        if allow_query is not False:
            raise RuntimeError("Dream runtime activation cannot issue a query")
        return SessionStartResult(
            agent_session_id=agent_session_id,
            session_request_key=session_request_key,
            active=True,
            remote_session_ref=self._remote_session_ref,
        )

    async def terminate_session(
        self,
        *,
        agent_session_id: str,
        reason_code: str,
    ) -> None:
        del agent_session_id, reason_code
        # The callback observes an already-running SDK stream.  It cannot claim
        # remote termination if the following database commit fails.
        raise RuntimeError("observed SDK session termination is unconfirmed")


class StoryWorkspaceDreamRuntimeActivationService:
    """Join verified workspace bytes and Thread authority to start one Run."""

    def __init__(
        self,
        db: Any,
        *,
        token_secret: bytes | str,
        runtime_placement: LocalRuntimePlacement | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.db = db
        self._token_secret = token_secret
        self._runtime_placement = runtime_placement or LocalRuntimePlacement()
        self._clock = clock or (lambda: datetime.now(UTC))

    async def activate_from_assembled_context(
        self,
        *,
        workflow_run_id: str,
        actor_context: AuthenticatedActorContext,
        remote_session_ref: str,
        verified_plugins: list[dict[str, Any]],
    ) -> WorkflowRun:
        remote_session_ref = self._validate_remote_session_ref(remote_session_ref)
        run_reader = WorkflowRunService(
            self.db,
            token_secret=self._token_secret,
            clock=self._clock,
        )
        run = run_reader.read_run(workflow_run_id, actor_context)
        run_status = str(getattr(run.status, "value", run.status))
        if run_status in {
            RunStatus.RUNNING.value,
            RunStatus.OUTPUT_VALIDATING.value,
            RunStatus.PENDING_REVIEW.value,
            RunStatus.CONFIRMED.value,
        }:
            runtime_lock, _materializations, _policy_revision = self._load_evidence(
                run
            )
            self._validate_verified_plugins(runtime_lock, verified_plugins)
            return self._validate_active_runtime(run)
        if run_status != RunStatus.QUEUED.value:
            self._rollback_read()
            raise StoryWorkspaceDreamRuntimeActivationError(
                DREAM_RUNTIME_NOT_READY,
                "Workflow Run is not available for Dream runtime activation",
            )

        runtime_lock, materializations, policy_revision = self._load_evidence(run)
        self._validate_verified_plugins(runtime_lock, verified_plugins)
        now = self._now()
        placement = RuntimePlacementContext(
            workflow_run_id=run.workflow_run_id,
            runtime_environment_id=self._runtime_placement.runtime_environment_id,
            runtime_pool_id=self._runtime_placement.runtime_pool_id,
            distribution_mode=self._runtime_placement.distribution_mode,
            runtime_node_id=self._runtime_placement.runtime_node_id,
            artifact_set_hash=compute_artifact_set_hash(runtime_lock),
            policy_revision=policy_revision,
            deployment_tier=self._runtime_placement.deployment_tier,
        )
        observed = ReconcileResult(
            attempt_id="rpa_" + uuid.uuid4().hex,
            workflow_run_id=run.workflow_run_id,
            runtime_node_id=self._runtime_placement.runtime_node_id,
            policy_revision=policy_revision,
            settings_intent={
                "evidence": "verified-workspace-manifest+assembled-thread-context",
                "requiredTool": _REQUIRED_DREAM_TOOL,
            },
            plugins=[
                HeadlessPluginState(
                    claude_code_plugin_id=entry.claude_code_plugin_id,
                    resolved_version=entry.resolved_version,
                    artifact_digest=entry.artifact_digest,
                    loaded_capabilities=sorted(set(entry.capability_bindings)),
                    load_status="loaded",
                    loaded_at=now,
                )
                for entry in runtime_lock.claude_code_plugins
            ],
            completed_before_first_query=True,
            created_at=now,
        )
        unavailable = _UnavailableReconcileDependency()
        receipt_service = ReconcileService(
            self.db,
            source_policy=_ObservedRuntimePolicy(policy_revision),
            settings_writer=unavailable,
            headless_runner=unavailable,
            cli_source_policy=unavailable,
            cli_runner=unavailable,
            clock=self._clock,
        )
        receipt = receipt_service.create_load_receipt(
            runtime_lock=runtime_lock,
            placement_context=placement,
            reconcile_result=observed,
            materializations=materializations,
        )
        run_service = WorkflowRunService(
            self.db,
            token_secret=self._token_secret,
            receipt_reader=receipt_service.read_workflow_readiness,
            clock=self._clock,
        )
        session_manager = SessionManager(
            self.db,
            receipt_reader=receipt_service,
            adapter=_AssembledThreadSessionAdapter(remote_session_ref),
            workflow_run_service=run_service,
            clock=self._clock,
        )
        session = await session_manager.create_or_resume_session(
            workflow_run_id=run.workflow_run_id,
            runtime_load_receipt_id=receipt.receipt_id,
            runtime_lock=runtime_lock,
            approved_capabilities=sorted(
                {
                    capability
                    for entry in runtime_lock.claude_code_plugins
                    for capability in entry.capability_bindings
                }
            ),
            trusted_marketplaces={
                entry.claude_code_plugin_id.rsplit("@", 1)[1]: entry.source_ref
                for entry in runtime_lock.claude_code_plugins
            },
            actor_context=actor_context,
        )
        activated = run_service.read_run(run.workflow_run_id, actor_context)
        if (
            str(getattr(activated.status, "value", activated.status))
            != RunStatus.RUNNING.value
            or activated.agent_session_id != session.agent_session_id
            or activated.runtime_load_receipt_id != receipt.receipt_id
        ):
            raise StoryWorkspaceDreamRuntimeActivationError(
                DREAM_RUNTIME_NOT_READY,
                "Dream runtime activation did not commit the authoritative bindings",
            )
        return activated

    def _load_evidence(
        self,
        run: WorkflowRun,
    ) -> tuple[DeckRuntimePluginLock, list[RuntimePluginMaterialization], str]:
        lock_row = self.db.execute(
            "SELECT lock_json FROM deck_runtime_plugin_locks WHERE id = %s",
            (run.runtime_plugin_lock_id,),
        ).fetchone()
        if lock_row is None:
            self._rollback_read()
            raise StoryWorkspaceDreamRuntimeActivationError(
                DREAM_RUNTIME_NOT_READY,
                "Dream runtime lock is unavailable",
            )
        raw_lock = lock_row["lock_json"]
        runtime_lock = (
            DeckRuntimePluginLock.model_validate(raw_lock)
            if isinstance(raw_lock, dict)
            else DeckRuntimePluginLock.model_validate_json(str(raw_lock))
        )
        rows = self.db.execute(
            """
            SELECT * FROM runtime_plugin_materializations
            WHERE runtime_environment_id = %s AND runtime_pool_id = %s
              AND runtime_node_id = %s AND artifact_set_hash = %s
              AND policy_revision = %s
              AND declaration_status = 'declared'
              AND materialization_status = 'materialized'
              AND activation_status IN ('loadable', 'loaded')
            ORDER BY claude_code_plugin_id
            """,
            (
                self._runtime_placement.runtime_environment_id,
                self._runtime_placement.runtime_pool_id,
                self._runtime_placement.runtime_node_id,
                compute_artifact_set_hash(runtime_lock),
                _DREAM_MATERIALIZATION_POLICY_REVISION,
            ),
        ).fetchall()
        self._rollback_read()
        try:
            materializations = [
                RuntimePluginMaterialization.model_validate(dict(row)) for row in rows
            ]
        except Exception as exc:
            raise StoryWorkspaceDreamRuntimeActivationError(
                DREAM_RUNTIME_NOT_READY,
                "Dream runtime materialization evidence is invalid",
            ) from exc
        expected_ids = {
            entry.claude_code_plugin_id for entry in runtime_lock.claude_code_plugins
        }
        materialized_ids = {
            entry.claude_code_plugin_id for entry in materializations
        }
        policy_revisions = {entry.policy_revision for entry in materializations}
        if materialized_ids != expected_ids or len(policy_revisions) != 1:
            raise StoryWorkspaceDreamRuntimeActivationError(
                DREAM_RUNTIME_NOT_READY,
                "Dream runtime materialization evidence is incomplete",
            )
        return runtime_lock, materializations, next(iter(policy_revisions))

    @staticmethod
    def _validate_remote_session_ref(remote_session_ref: object) -> str:
        if (
            not isinstance(remote_session_ref, str)
            or not remote_session_ref.strip()
            or len(remote_session_ref) > 255
        ):
            raise StoryWorkspaceDreamRuntimeActivationError(
                DREAM_RUNTIME_INIT_INVALID,
                "Assembled Dream Thread identity is invalid",
            )
        return remote_session_ref.strip()

    @staticmethod
    def _validate_verified_plugins(
        runtime_lock: DeckRuntimePluginLock,
        verified_plugins: list[dict[str, Any]],
    ) -> None:
        # A Dream workspace manifest contains both Deck-selected plugins and
        # server-selected runtime adapters.  The runtime lock owns only the
        # latter, so activation must require every locked adapter exactly while
        # allowing the other digest-verified, frozen Deck entries to coexist.
        # Reject duplicate package identities instead of letting a dict
        # comprehension hide a second CLI --plugin-dir entry.
        observed: dict[str, tuple[Any, Any, Any]] = {}
        for item in verified_plugins:
            package_spec = item.get("package_spec") if isinstance(item, dict) else None
            if not isinstance(package_spec, str) or package_spec in observed:
                raise StoryWorkspaceDreamRuntimeActivationError(
                    DREAM_RUNTIME_INIT_INVALID,
                    "Verified workspace plugins do not match the frozen runtime lock",
                )
            observed[package_spec] = (
                item.get("resolved_version"),
                item.get("artifact_digest"),
                item.get("has_manifest"),
            )
        expected = {
            entry.claude_code_plugin_id: (
                entry.resolved_version,
                entry.artifact_digest,
                True,
            )
            for entry in runtime_lock.claude_code_plugins
        }
        if any(observed.get(package_spec) != identity for package_spec, identity in expected.items()):
            raise StoryWorkspaceDreamRuntimeActivationError(
                DREAM_RUNTIME_INIT_INVALID,
                "Verified workspace plugins do not match the frozen runtime lock",
            )

    def _validate_active_runtime(self, run: WorkflowRun) -> WorkflowRun:
        """Prove durable runtime authority without controlling Chat resume.

        ``remote_session_ref`` records the SDK acknowledgement observed during
        the initial queued->running activation. It is not the canonical Chat
        transcript cursor: Chat intentionally allocates a fresh SDK session
        when the local transcript is unavailable. Keep the original reference
        immutable as audit evidence and validate the authoritative run/session/
        receipt/lock join for every active turn instead.
        """

        row = self.db.execute(
            "SELECT workflow_run_id, runtime_load_receipt_id, "
            "runtime_plugin_lock_id, status FROM agent_sessions "
            "WHERE agent_session_id = %s AND workflow_run_id = %s",
            (run.agent_session_id, run.workflow_run_id),
        ).fetchone()
        self._rollback_read()
        if (
            row is None
            or row["status"] != "active"
            or row["workflow_run_id"] != run.workflow_run_id
            or row["runtime_load_receipt_id"] != run.runtime_load_receipt_id
            or row["runtime_plugin_lock_id"] != run.runtime_plugin_lock_id
        ):
            raise StoryWorkspaceDreamRuntimeActivationError(
                DREAM_RUNTIME_INIT_INVALID,
                "Active Dream runtime bindings are inconsistent",
            )
        return run

    def _rollback_read(self) -> None:
        if self.db.in_transaction:
            self.db.rollback()

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
