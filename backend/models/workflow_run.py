"""Strict contracts for Workflow Run state, history, and load readiness."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


SHA256_PATTERN = r"^sha256:[0-9a-f]{64}$"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )


class RunStatus(str, Enum):
    PREFLIGHT = "preflight"
    QUEUED = "queued"
    RUNNING = "running"
    OUTPUT_VALIDATING = "output_validating"
    PENDING_REVIEW = "pending_review"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    CONTINUING = "continuing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_RUN_STATUSES = frozenset(
    {
        RunStatus.REJECTED,
        RunStatus.COMPLETED,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    }
)


class AuthenticatedActorContext(_StrictFrozenModel):
    """Trusted server-side identity; never construct from request body fields."""

    workspace_id: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)


class RuntimeLoadReceiptReadiness(_StrictFrozenModel):
    """The complete DECK-008 projection consumed by the run state guard."""

    receipt_id: str = Field(min_length=1)
    workflow_run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    runtime_plugin_lock_id: str = Field(min_length=1)
    runtime_plugin_lock_digest: str = Field(pattern=SHA256_PATTERN)
    required_entries_ready: bool


class WorkflowRun(_StrictFrozenModel):
    # SUO-198 fields.
    workflow_run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    deck_plugin_id: str = Field(min_length=1)
    deck_plugin_version: str = Field(min_length=1)
    workflow_definition_ref: str = Field(min_length=1)
    deck_runtime_snapshot_id: str = Field(min_length=1)
    status: RunStatus
    failed_step: str | None = None
    error_code: str | None = None
    retry_of_run_id: str | None = Field(
        default=None,
        pattern=r"^run_[0-9a-f]{32}$",
    )

    # Frozen Deck/Workflow provenance and idempotency fields.
    deck_plugin_manifest_hash: str = Field(pattern=SHA256_PATTERN)
    deck_plugin_binding_id: str = Field(min_length=1)
    binding_revision: int = Field(ge=1)
    runtime_plugin_lock_id: str = Field(min_length=1)
    runtime_load_receipt_id: str | None = None
    workflow_preflight_id: str = Field(pattern=r"^pf_[0-9a-f]{32}$")
    agent_session_id: str | None = Field(
        default=None,
        pattern=r"^as_[0-9a-f]{32}$",
    )
    source_voice_thread_id: str | None = None
    source_message_id: str | None = None
    source_message_time: datetime | None = None
    workspace_id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1, max_length=255)
    input_hash: str = Field(pattern=SHA256_PATTERN)
    semantic_fingerprint: str = Field(pattern=SHA256_PATTERN)
    status_version: int = Field(ge=1)

    created_by: str = Field(min_length=1)
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def lifecycle_fields_are_consistent(self) -> "WorkflowRun":
        if self.status is RunStatus.FAILED:
            if self.failed_step is None or self.error_code is None:
                raise ValueError("failed runs require failed_step and error_code")
        elif self.failed_step is not None or self.error_code is not None:
            raise ValueError("only failed runs may carry failure fields")

        has_receipt = self.runtime_load_receipt_id is not None
        has_session = self.agent_session_id is not None
        if has_receipt != has_session:
            raise ValueError("receipt and agent session bindings must be joint")
        requires_start_bindings = self.status in {
            RunStatus.RUNNING,
            RunStatus.OUTPUT_VALIDATING,
            RunStatus.PENDING_REVIEW,
            RunStatus.CONFIRMED,
            RunStatus.REJECTED,
            RunStatus.CONTINUING,
            RunStatus.COMPLETED,
        }
        if requires_start_bindings and not has_receipt:
            raise ValueError("started runs require receipt and agent session bindings")
        if self.status in {RunStatus.PREFLIGHT, RunStatus.QUEUED}:
            if has_receipt:
                raise ValueError("unstarted runs cannot bind receipt or session")

        source_values = (
            self.source_voice_thread_id,
            self.source_message_id,
            self.source_message_time,
        )
        source_count = sum(value is not None for value in source_values)
        if source_count not in {0, 3} and not (
            source_count == 1 and self.source_voice_thread_id is not None
        ):
            raise ValueError("Voice sources require a complete message tuple")
        if self.source_message_time is not None:
            if self.source_message_time.tzinfo is None:
                raise ValueError("source_message_time must include a timezone")
        if self.agent_session_id is not None and self.agent_session_id in {
            self.source_voice_thread_id,
            self.source_message_id,
        }:
            raise ValueError("Voice source identifiers cannot be session identifiers")

        if self.started_at is not None and self.started_at < self.created_at:
            raise ValueError("started_at cannot precede created_at")
        if self.completed_at is not None:
            if self.completed_at < self.created_at:
                raise ValueError("completed_at cannot precede created_at")
            if self.started_at is not None and self.completed_at < self.started_at:
                raise ValueError("completed_at cannot precede started_at")
        if self.status in TERMINAL_RUN_STATUSES and self.completed_at is None:
            raise ValueError("terminal runs require completed_at")
        if self.status not in TERMINAL_RUN_STATUSES and self.completed_at is not None:
            raise ValueError("non-terminal runs cannot have completed_at")
        return self


class WorkflowRunTransition(_StrictFrozenModel):
    transition_id: str = Field(pattern=r"^wrt_[0-9a-f]{32}$")
    workflow_run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    transition_seq: int = Field(ge=1)
    from_status: RunStatus | None
    to_status: RunStatus
    actor_id: str = Field(min_length=1)
    reason_code: str | None = None
    failed_step: str | None = None
    error_code: str | None = None
    occurred_at: datetime

    @model_validator(mode="after")
    def transition_is_real_and_well_formed(self) -> "WorkflowRunTransition":
        if self.from_status is None:
            if self.transition_seq != 1 or self.to_status is not RunStatus.PREFLIGHT:
                raise ValueError("the only initial transition is NULL -> preflight")
        elif self.from_status is self.to_status:
            raise ValueError("a transition must change status")
        if self.to_status is RunStatus.FAILED:
            if self.failed_step is None or self.error_code is None:
                raise ValueError("failed transitions require failure details")
        elif self.failed_step is not None or self.error_code is not None:
            raise ValueError("only failed transitions may carry failure details")
        return self
