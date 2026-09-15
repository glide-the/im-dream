# [Input] Frozen Admin Reflections operation schemas and server-owned launch/runtime facts.
# [Output] Strict Pydantic DTOs for seven OAuth and nine task-bound background operations.
# [Pos] Reflections wire boundary; no operation hashes, SQL, Agent execution, credentials or files.
# [Sync] 2026-09-15: model the Registry99 candidate including worker event high-water recovery.
"""Strict Reflections task, section, event and analysis-report wire DTOs."""

from __future__ import annotations

from datetime import date
import json
from typing import Annotated, Literal

from pydantic import Field, JsonValue, field_validator, model_validator

from .chat_models import (
    ChatMessageDTO,
    ChatStrictDTO,
    NonnegativeSafeInteger,
    PositiveSafeInteger,
    PresentFieldsDTO,
    validate_timestamp_text,
)


ReflectionSection = Literal["echoes", "traits", "patterns"]
ReflectionTaskStatus = Literal[
    "CREATED",
    "ASSEMBLING",
    "QUEUED",
    "RUNNING",
    "COMPLETED",
    "PARTIAL_FAILED",
    "FAILED",
]
ReflectionSectionStatus = Literal["PENDING", "RUNNING", "COMPLETED", "FAILED"]
ReflectionTerminalStatus = Literal["COMPLETED", "PARTIAL_FAILED", "FAILED"]
ReflectionConfidence = Literal["high", "medium", "low"]
ReflectionEventType = Literal[
    "reflection.task.created",
    "reflection.context.ready",
    "reflection.task.started",
    "reflection.section.started",
    "reflection.section.completed",
    "reflection.section.failed",
    "reflection.task.completed",
    "reflection.task.partial_failed",
    "reflection.task.failed",
]

Identifier256 = Annotated[str, Field(min_length=1, max_length=256)]
DateText = Annotated[str, Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")]
ReflectionTaskId = Annotated[
    str,
    Field(
        pattern=(
            r"^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-"
            r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|"
            r"00000000-0000-0000-0000-000000000000|"
            r"ffffffff-ffff-ffff-ffff-ffffffffffff)$"
        )
    ),
]
ReflectionAuthorityToken = Annotated[
    str, Field(pattern=r"^rta_[A-Za-z0-9_-]{43}$", repr=False)
]
ReflectionEventSequence = Annotated[int, Field(ge=1, le=2_147_483_647)]
ReflectionEventHighWater = Annotated[int, Field(ge=0, le=2_147_483_647)]


def _reject_non_json_constant(raw: str) -> None:
    raise ValueError(f"Invalid JSON constant: {raw}")


def decode_nonempty_object_json(raw: str) -> dict[str, JsonValue]:
    """Decode a nonempty JSON object without changing the original wire text."""

    try:
        value = json.loads(raw, parse_constant=_reject_non_json_constant)
    except (TypeError, ValueError, RecursionError):
        raise ValueError("Expected a nonempty JSON object") from None
    if not isinstance(value, dict) or not value:
        raise ValueError("Expected a nonempty JSON object")
    return value


def decode_optional_object_json(raw: str | None) -> dict[str, JsonValue] | None:
    if raw is None:
        return None
    try:
        value = json.loads(raw, parse_constant=_reject_non_json_constant)
    except (TypeError, ValueError, RecursionError):
        raise ValueError("Expected a JSON object") from None
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


class _ReflectionInputBase(ChatStrictDTO):
    session_ids: list[Identifier256]
    start_date: DateText | None
    end_date: DateText | None
    language: Literal["en", "zh"]
    language_label: Literal["English", "Simplified Chinese"]

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date(cls, value: str | None) -> str | None:
        if value is not None:
            date.fromisoformat(value)
        return value

    @field_validator("session_ids")
    @classmethod
    def require_unique_sessions(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("Session identifiers must be unique")
        return value

    @model_validator(mode="after")
    def validate_input_pairing(self):
        expected_label = (
            "Simplified Chinese" if self.language == "zh" else "English"
        )
        if self.language_label != expected_label:
            raise ValueError("Language label does not match language")
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError("Date range is reversed")
        return self


class ReflectionTaskCreateSnapshotDTO(_ReflectionInputBase):
    pass


class ReflectionTaskPublicInputDTO(_ReflectionInputBase, PresentFieldsDTO):
    session_count: NonnegativeSafeInteger | None = None

    @model_validator(mode="after")
    def reject_explicit_null_session_count(self):
        if "session_count" in self.model_fields_set and self.session_count is None:
            raise ValueError("Session count cannot be null")
        return self


class ReflectionResultDTO(ChatStrictDTO):
    id: ReflectionTaskId
    task_id: ReflectionTaskId
    section: ReflectionSection
    title: str
    description: str
    related_session_ids: list[Identifier256]
    evidence: str
    confidence: ReflectionConfidence
    created_at: str | None
    _timestamp = field_validator("created_at")(validate_timestamp_text)

    @field_validator("related_session_ids")
    @classmethod
    def require_unique_related_sessions(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("Related Session identifiers must be unique")
        return value

    @field_validator("title")
    @classmethod
    def validate_title_size(cls, value: str) -> str:
        if len(value) > 200:
            raise ValueError("Result title is too long")
        return value

    @field_validator("description")
    @classmethod
    def validate_description_size(cls, value: str) -> str:
        if len(value) > 4_000:
            raise ValueError("Result description is too long")
        return value

    @field_validator("evidence")
    @classmethod
    def validate_evidence_size(cls, value: str) -> str:
        if len(value) > 2_000:
            raise ValueError("Result evidence is too long")
        return value


class ReflectionSectionStateDTO(ChatStrictDTO):
    section: ReflectionSection
    status: ReflectionSectionStatus
    result_count: NonnegativeSafeInteger
    revision: PositiveSafeInteger
    started_at: str | None
    completed_at: str | None
    error_summary: str | None
    _timestamps = field_validator("started_at", "completed_at")(
        validate_timestamp_text
    )


class ReflectionTaskDTO(ChatStrictDTO):
    id: ReflectionTaskId
    task_id: ReflectionTaskId
    status: ReflectionTaskStatus
    sections: list[ReflectionSection] = Field(min_length=1, max_length=3)
    input_snapshot: ReflectionTaskPublicInputDTO
    workspace_path: str | None
    agent_contract_version: Identifier256 | None
    error_summary: str | None
    revision: PositiveSafeInteger
    created_at: str | None
    started_at: str | None
    completed_at: str | None
    updated_at: str | None
    section_states: list[ReflectionSectionStateDTO]
    _timestamps = field_validator(
        "created_at", "started_at", "completed_at", "updated_at"
    )(validate_timestamp_text)

    @field_validator("sections")
    @classmethod
    def require_unique_sections(
        cls, value: list[ReflectionSection]
    ) -> list[ReflectionSection]:
        if len(set(value)) != len(value):
            raise ValueError("Sections must be unique")
        return value

    @model_validator(mode="after")
    def validate_task_projection(self):
        if self.id != self.task_id:
            raise ValueError("Task aliases must match")
        actual = [item.section for item in self.section_states]
        if actual and actual != self.sections:
            raise ValueError("Section state order must match task sections")
        terminal = self.status in {"COMPLETED", "PARTIAL_FAILED", "FAILED"}
        if terminal != (self.completed_at is not None):
            raise ValueError("Task completion time must match terminal status")
        return self


class ReflectionTaskLookupDTO(ChatStrictDTO):
    task_id: ReflectionTaskId


class ReflectionTaskCreateInputDTO(ChatStrictDTO):
    sections: list[ReflectionSection] = Field(min_length=1, max_length=3)
    input_snapshot: ReflectionTaskCreateSnapshotDTO

    @field_validator("sections")
    @classmethod
    def require_unique_sections(
        cls, value: list[ReflectionSection]
    ) -> list[ReflectionSection]:
        if len(set(value)) != len(value):
            raise ValueError("Sections must be unique")
        return value


class ReflectionTaskGetOutputDTO(ChatStrictDTO):
    task: ReflectionTaskDTO
    results: list[ReflectionResultDTO]


class ReflectionTaskLatestInputDTO(ChatStrictDTO):
    pass


class ReflectionTaskLatestOutputDTO(ChatStrictDTO):
    task: ReflectionTaskDTO | None
    results: list[ReflectionResultDTO]


class ReflectionTaskStartOutputDTO(ChatStrictDTO):
    task: ReflectionTaskDTO
    terminal: bool
    report_missing: bool

    @field_validator("terminal", "report_missing", mode="before")
    @classmethod
    def require_boolean(cls, value):
        if type(value) is not bool:
            raise ValueError("Expected a boolean")
        return value

    @model_validator(mode="after")
    def validate_terminal_state(self):
        terminal = self.task.status in {"COMPLETED", "PARTIAL_FAILED", "FAILED"}
        if self.terminal != terminal or (self.report_missing and not terminal):
            raise ValueError("Start result does not match task status")
        return self


class ReflectionSessionSnapshotDTO(ChatStrictDTO):
    id: Identifier256
    name: str | None
    created_at: str | None
    updated_at: str | None
    labels: list[str]
    first_line: str
    text: str
    _timestamps = field_validator("created_at", "updated_at")(
        validate_timestamp_text
    )


class ReflectionPromptSnapshotDTO(ChatStrictDTO):
    section: ReflectionSection
    prompt_files_json: str | None

    def prompt_files(self) -> dict[str, JsonValue] | None:
        return decode_optional_object_json(self.prompt_files_json)


class ReflectionStatsDTO(ChatStrictDTO):
    days: NonnegativeSafeInteger
    entries: NonnegativeSafeInteger
    words: NonnegativeSafeInteger


class ReflectionLaunchSnapshotDTO(ChatStrictDTO):
    schema_version: Literal[1]
    task_id: ReflectionTaskId
    language: Literal["en", "zh"]
    sessions: list[ReflectionSessionSnapshotDTO]
    custom_prompts: list[ReflectionPromptSnapshotDTO]
    stats: ReflectionStatsDTO

    @field_validator("schema_version", mode="before")
    @classmethod
    def require_integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("Snapshot version must be an integer")
        return value

    @model_validator(mode="after")
    def validate_snapshot(self):
        session_ids = [item.id for item in self.sessions]
        prompt_sections = [item.section for item in self.custom_prompts]
        if len(set(session_ids)) != len(session_ids):
            raise ValueError("Snapshot Session identifiers must be unique")
        if len(set(prompt_sections)) != len(prompt_sections):
            raise ValueError("Snapshot prompt sections must be unique")
        if self.stats.entries != len(self.sessions):
            raise ValueError("Snapshot entry count does not match Sessions")
        return self


class ReflectionWorkerLoadOutputDTO(ChatStrictDTO):
    task: ReflectionTaskDTO
    launch_snapshot: ReflectionLaunchSnapshotDTO
    last_event_sequence: ReflectionEventHighWater

    @model_validator(mode="after")
    def validate_task_binding(self):
        if self.task.task_id != self.launch_snapshot.task_id:
            raise ValueError("Worker snapshot does not match task")
        return self


class ReflectionTaskAdvanceInputDTO(ReflectionTaskLookupDTO, PresentFieldsDTO):
    action: Literal["context-ready", "run-started", "finalize", "fatal-fail"]
    expected_revision: PositiveSafeInteger
    error_summary: Annotated[str, Field(max_length=4_000)] | None = None

    @model_validator(mode="after")
    def validate_action_shape(self):
        supplied = "error_summary" in self.model_fields_set
        if self.action in {"context-ready", "run-started"} and supplied:
            raise ValueError("This task action does not accept an error summary")
        if self.action == "finalize" and not supplied:
            raise ValueError("Finalize requires an explicit nullable error summary")
        if self.action == "fatal-fail" and (
            not supplied or self.error_summary is None or not self.error_summary
        ):
            raise ValueError("Fatal failure requires an error summary")
        return self


class ReflectionTaskAdvanceOutputDTO(ChatStrictDTO):
    status: ReflectionTaskStatus
    revision: PositiveSafeInteger


class ReflectionSectionBeginInputDTO(ReflectionTaskLookupDTO):
    section: ReflectionSection
    expected_revision: PositiveSafeInteger


class ReflectionAuthorityDTO(ChatStrictDTO):
    token: ReflectionAuthorityToken
    purpose: Literal["reflections-worker"]
    task_id: ReflectionTaskId
    section: ReflectionSection
    thread_id: ReflectionTaskId
    scopes: tuple[Literal["dream:read"], Literal["dream:write"]]
    expires_at: str
    maximum_expires_at: str
    _timestamps = field_validator("expires_at", "maximum_expires_at")(
        validate_timestamp_text
    )


class ReflectionSectionBeginOutputDTO(ChatStrictDTO):
    section: ReflectionSection
    thread_id: ReflectionTaskId
    status: Literal["RUNNING"]
    revision: PositiveSafeInteger
    authority: ReflectionAuthorityDTO

    @model_validator(mode="after")
    def validate_authority_binding(self):
        if (
            self.authority.section != self.section
            or self.authority.thread_id != self.thread_id
        ):
            raise ValueError("Section authority binding does not match")
        return self


class ReflectionSectionAuthorityInputDTO(ReflectionTaskLookupDTO):
    section: ReflectionSection


class ReflectionSectionAuthorityRenewOutputDTO(ChatStrictDTO):
    purpose: Literal["reflections-worker"]
    task_id: ReflectionTaskId
    section: ReflectionSection
    thread_id: ReflectionTaskId
    scopes: tuple[Literal["dream:read"], Literal["dream:write"]]
    expires_at: str
    maximum_expires_at: str
    _timestamps = field_validator("expires_at", "maximum_expires_at")(
        validate_timestamp_text
    )


class ReflectionSectionAuthorityRevokeOutputDTO(ChatStrictDTO):
    revoked: Literal[True]

    @field_validator("revoked", mode="before")
    @classmethod
    def require_true_boolean(cls, value):
        if value is not True:
            raise ValueError("Authority was not revoked")
        return value


class ReflectionSectionTranscriptInputDTO(ReflectionTaskLookupDTO):
    section: ReflectionSection


class ReflectionSectionTranscriptOutputDTO(ChatStrictDTO):
    section: ReflectionSection
    messages: list[ChatMessageDTO]


class ReflectionInsightInputDTO(ChatStrictDTO):
    title: str
    description: str
    related_session_ids: list[Identifier256]
    evidence: str
    confidence: ReflectionConfidence

    @field_validator("related_session_ids")
    @classmethod
    def require_unique_related_sessions(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("Related Session identifiers must be unique")
        return value

    @field_validator("title")
    @classmethod
    def validate_title_size(cls, value: str) -> str:
        if len(value) > 200:
            raise ValueError("Result title is too long")
        return value

    @field_validator("description")
    @classmethod
    def validate_description_size(cls, value: str) -> str:
        if len(value) > 4_000:
            raise ValueError("Result description is too long")
        return value

    @field_validator("evidence")
    @classmethod
    def validate_evidence_size(cls, value: str) -> str:
        if len(value) > 2_000:
            raise ValueError("Result evidence is too long")
        return value


class ReflectionSectionFinishInputDTO(ReflectionTaskLookupDTO, PresentFieldsDTO):
    section: ReflectionSection
    expected_revision: PositiveSafeInteger
    outcome: Literal["completed", "failed"]
    results: list[ReflectionInsightInputDTO] | None = None
    error_summary: Annotated[str, Field(max_length=4_000)] | None = None

    @model_validator(mode="after")
    def validate_outcome_shape(self):
        results_supplied = "results" in self.model_fields_set
        error_supplied = "error_summary" in self.model_fields_set
        if self.outcome == "completed":
            if not results_supplied or self.results is None or error_supplied:
                raise ValueError("Completed section requires only results")
        elif (
            results_supplied
            or not error_supplied
            or self.error_summary is None
            or not self.error_summary
        ):
            raise ValueError("Failed section requires only an error summary")
        return self


class ReflectionSectionFinishOutputDTO(ChatStrictDTO):
    section: ReflectionSection
    status: Literal["COMPLETED", "FAILED"]
    result_count: NonnegativeSafeInteger
    revision: PositiveSafeInteger


class ReflectionEventAppendInputDTO(ReflectionTaskLookupDTO):
    event_id: Identifier256
    sequence: ReflectionEventSequence
    event_type: ReflectionEventType
    created_at: str
    payload: dict[str, JsonValue]
    _timestamp = field_validator("created_at")(validate_timestamp_text)

    @model_validator(mode="after")
    def validate_event_identity(self):
        if self.event_id != reflection_event_id(self.task_id, self.sequence):
            raise ValueError("Event identity must bind task and sequence")
        return self


class ReflectionEventDTO(ReflectionTaskLookupDTO):
    id: Identifier256
    sequence: ReflectionEventSequence
    type: ReflectionEventType
    created_at: str
    payload: dict[str, JsonValue]
    _timestamp = field_validator("created_at")(validate_timestamp_text)


class ReflectionEventListInputDTO(ReflectionTaskLookupDTO):
    after_event_id: Identifier256 | None


class ReflectionEventListOutputDTO(ChatStrictDTO):
    events: list[ReflectionEventDTO]


class ReflectionEventAppendOutputDTO(ChatStrictDTO):
    event_id: Identifier256
    accepted: Literal[True]

    @field_validator("accepted", mode="before")
    @classmethod
    def require_true_boolean(cls, value):
        if value is not True:
            raise ValueError("Event was not accepted")
        return value


class ReflectionReportEnsureOutputDTO(ChatStrictDTO):
    report_id: str | None
    report_type: str | None
    created: bool

    @field_validator("created", mode="before")
    @classmethod
    def require_boolean(cls, value):
        if type(value) is not bool:
            raise ValueError("Expected a boolean")
        return value

    @model_validator(mode="after")
    def validate_report_pair(self):
        if (self.report_id is None) != (self.report_type is None):
            raise ValueError("Report identity and type must be paired")
        return self


class AnalysisReportListInputDTO(ChatStrictDTO):
    limit: PositiveSafeInteger = 10


class AnalysisReportDTO(ChatStrictDTO):
    id: Annotated[str, Field(pattern=r"^[1-9][0-9]*$")]
    report_type: Identifier256
    report_data_json: str
    created_at: str | None
    _timestamp = field_validator("created_at")(validate_timestamp_text)

    @field_validator("report_data_json")
    @classmethod
    def validate_report_data(cls, value: str) -> str:
        decode_nonempty_object_json(value)
        return value

    def report_data(self) -> dict[str, JsonValue]:
        return decode_nonempty_object_json(self.report_data_json)


class AnalysisReportListOutputDTO(ChatStrictDTO):
    reports: list[AnalysisReportDTO]


class AnalysisReportSaveInputDTO(ChatStrictDTO):
    report_type: Identifier256
    report_data_json: str
    all_notes_text: str = ""

    @field_validator("report_data_json")
    @classmethod
    def validate_report_data(cls, value: str) -> str:
        decode_nonempty_object_json(value)
        return value


class AnalysisReportSaveOutputDTO(ChatStrictDTO):
    success: Literal[True]

    @field_validator("success", mode="before")
    @classmethod
    def require_true_boolean(cls, value):
        if value is not True:
            raise ValueError("Report was not saved")
        return value


def reflection_event_id(task_id: str, sequence: int) -> str:
    """Return the Admin-owned task/sequence event identity formula."""

    return f"evt_{task_id.replace('-', '')}_{sequence:06d}"


__all__ = [name for name in globals() if name.startswith("Reflection") or name.startswith("Analysis")]
