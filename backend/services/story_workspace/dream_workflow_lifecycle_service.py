"""Server-fact coordinator for the Dream Workflow Run lifecycle."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

try:
    from backend.models.workflow_run import (
        AuthenticatedActorContext,
        RunStatus,
        WorkflowRun,
    )
    from backend.services.workflow.run_service import (
        IllegalRunTransition,
        WorkflowRunService,
    )
except ModuleNotFoundError:  # Support the backend directory on PYTHONPATH.
    from models.workflow_run import AuthenticatedActorContext, RunStatus, WorkflowRun
    from services.workflow.run_service import IllegalRunTransition, WorkflowRunService


class StoryWorkspaceDreamWorkflowLifecycleService:
    """Advance Run state only after an owning service proves its domain fact."""

    def __init__(
        self,
        db: Any,
        *,
        token_secret: bytes | str,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._db = db
        self._service = WorkflowRunService(
            db,
            token_secret=token_secret,
            clock=clock,
        )

    async def record_output_ready(
        self,
        workflow_run_id: str,
        actor_context: AuthenticatedActorContext,
        *,
        normalized_result_ready: bool,
    ) -> WorkflowRun:
        if normalized_result_ready is not True:
            raise ValueError("normalized Dream output readiness is required")
        run = self._read_run(workflow_run_id, actor_context)
        status = self._status(run)
        if status == RunStatus.RUNNING:
            run = await self._service.transition_run(
                workflow_run_id,
                RunStatus.OUTPUT_VALIDATING,
                actor_context,
                reason_code="dream_required_stages_present",
            )
            status = self._status(run)
        if status == RunStatus.OUTPUT_VALIDATING:
            return await self._service.transition_run(
                workflow_run_id,
                RunStatus.PENDING_REVIEW,
                actor_context,
                reason_code="dream_output_contract_valid",
                normalized_result_ready=True,
            )
        if status in {
            RunStatus.PENDING_REVIEW,
            RunStatus.CONFIRMED,
            RunStatus.COMPLETED,
        }:
            return run
        raise IllegalRunTransition()

    async def record_confirmation_accepted(
        self,
        workflow_run_id: str,
        actor_context: AuthenticatedActorContext,
        *,
        review_items_approved: bool,
    ) -> WorkflowRun:
        if review_items_approved is not True:
            raise ValueError("authoritative Dream confirmation is required")
        run = self._read_run(workflow_run_id, actor_context)
        status = self._status(run)
        if status == RunStatus.PENDING_REVIEW:
            return await self._service.transition_run(
                workflow_run_id,
                RunStatus.CONFIRMED,
                actor_context,
                reason_code="dream_confirmation_accepted",
                review_items_approved=True,
            )
        if status in {
            RunStatus.CONFIRMED,
            RunStatus.COMPLETED,
        }:
            return run
        raise IllegalRunTransition()

    async def record_post_confirmation_dispatched(
        self,
        workflow_run_id: str,
        actor_context: AuthenticatedActorContext,
    ) -> WorkflowRun:
        run = self._read_run(workflow_run_id, actor_context)
        status = self._status(run)
        # Dispatch is a private Chat command fact, not a Workflow lifecycle
        # transition. The shared Thread reports the active Agent turn while the
        # Workflow remains confirmed until an owning domain terminal fact.
        if status in {RunStatus.CONFIRMED, RunStatus.COMPLETED}:
            return run
        raise IllegalRunTransition()

    @staticmethod
    def _status(run: WorkflowRun) -> RunStatus:
        return RunStatus(str(getattr(run.status, "value", run.status)))

    def _read_run(
        self,
        workflow_run_id: str,
        actor_context: AuthenticatedActorContext,
    ) -> WorkflowRun:
        try:
            return self._service.read_run(workflow_run_id, actor_context)
        finally:
            if self._db.in_transaction:
                self._db.rollback()
