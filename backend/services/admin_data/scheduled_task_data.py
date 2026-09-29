# [Input] Admin scheduled Chat operation registry, exact schema capabilities and explicit user or service credentials.
# [Output] Typed once/daily definition, date, history, trigger and authority consumers without Dream SQL.
# [Pos] Dream scheduled Chat data port; Admin owns time calculation, revision, claims and persistence.
# [Sync] 2026-09-29: refresh one stale process capability catalog before failing closed on a scheduled operation added by Admin.
# [Sync] 2026-09-28: consume the reviewed Admin 0069-0072 operation contracts and fail closed on missing capabilities.
"""Strict consumers for Admin-owned scheduled Chat operations."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from .chat_models import ChatStrictDTO, TaskSessionDTO, validate_timestamp_text
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError
from .models import OperationCapabilityDTO, SchemaCapabilityDTO

Id = Annotated[str, Field(min_length=1)]
Uuid = Annotated[str, Field(pattern=r"^[0-9a-fA-F-]{36}$")]
Revision = Annotated[int, Field(ge=1, le=9_007_199_254_740_991, strict=True)]
Title = Annotated[str, Field(min_length=1)]
Zone = Annotated[str, Field(min_length=1)]


class OnceRuleDTO(ChatStrictDTO):
    kind: Literal["once"]
    local_date: str
    local_time: str
    time_zone: Zone
    selected_offset_minutes: int | None


class DailyRuleDTO(ChatStrictDTO):
    kind: Literal["daily"]
    local_time: str
    time_zone: Zone


ScheduledRuleDTO = OnceRuleDTO | DailyRuleDTO


class ScheduledTaskDTO(ChatStrictDTO):
    id: Uuid
    source_thread_id: Id
    title: Title
    prompt: Title
    rule: ScheduledRuleDTO
    next_run_at: str | None
    status: Literal["active", "paused", "exhausted", "deleted"]
    revision: Revision
    created_at: str
    updated_at: str
    _timestamps = field_validator("next_run_at", "created_at", "updated_at")(validate_timestamp_text)


class ScheduledTriggerDTO(ChatStrictDTO):
    id: Uuid
    task_id: Uuid
    kind: Literal["scheduled", "manual"]
    scheduled_at: str | None
    definition_revision: Revision
    title: Title
    source_thread_id: Id
    time_zone: Zone
    status: Literal["claimed", "queued", "running", "succeeded", "failed", "state_unknown", "skipped"]
    task_session_id: str | None
    target_thread_id: str | None
    input_message_id: str | None
    target_turn_id: str | None
    final_message_id: str | None
    error_code: str | None
    skipped_from_at: str | None
    skipped_through_at: str | None
    created_at: str
    updated_at: str
    _timestamps = field_validator("scheduled_at", "skipped_from_at", "skipped_through_at", "created_at", "updated_at")(validate_timestamp_text)


class CreateScheduledTaskInputDTO(ChatStrictDTO):
    source_thread_id: Id
    create_request_key: Id
    title: Title
    prompt: Title
    rule: ScheduledRuleDTO


class ScheduledTaskIdInputDTO(ChatStrictDTO):
    task_id: Uuid


class ScheduledTaskRevisionInputDTO(ScheduledTaskIdInputDTO):
    expected_revision: Revision


class EditScheduledTaskInputDTO(ScheduledTaskRevisionInputDTO):
    title: Title
    prompt: Title
    rule: ScheduledRuleDTO


class RunScheduledTaskInputDTO(ScheduledTaskIdInputDTO):
    manual_request_key: Id


class DayScheduledTaskInputDTO(ChatStrictDTO):
    local_date: str
    display_time_zone: Zone


class HistoryScheduledTaskInputDTO(ScheduledTaskIdInputDTO):
    limit: Annotated[int, Field(ge=1)]
    before_created_at: str | None
    _timestamp = field_validator("before_created_at")(validate_timestamp_text)


class ScheduledTaskResultDTO(ChatStrictDTO):
    task: ScheduledTaskDTO


class ScheduledTaskNullableResultDTO(ChatStrictDTO):
    task: ScheduledTaskDTO | None


class ScheduledTriggerResultDTO(ChatStrictDTO):
    trigger: ScheduledTriggerDTO


class ScheduledTaskDayResultDTO(ChatStrictDTO):
    tasks: list[ScheduledTaskDTO]
    triggers: list[ScheduledTriggerDTO]


class ScheduledTaskHistoryResultDTO(ChatStrictDTO):
    triggers: list[ScheduledTriggerDTO]


class ClaimScheduledTriggerInputDTO(ChatStrictDTO):
    pass


class ClaimScheduledTriggerResultDTO(ChatStrictDTO):
    trigger: ScheduledTriggerDTO | None
    claim_id: Uuid | None


class TriggerClaimInputDTO(ChatStrictDTO):
    trigger_id: Uuid
    claim_id: Uuid


class PrepareScheduledTriggerResultDTO(ChatStrictDTO):
    prepared: bool
    trigger: ScheduledTriggerDTO
    task_session: TaskSessionDTO | None = None
    authority_token: str | None = Field(default=None, repr=False)
    authority_expires_at: str | None = None
    error_code: str | None = None
    _timestamp = field_validator("authority_expires_at")(validate_timestamp_text)

    @model_validator(mode="after")
    def validate_prepared_result(self):
        if self.prepared != (self.task_session is not None and self.authority_token is not None and self.authority_expires_at is not None):
            raise ValueError("Invalid scheduled trigger prepare response")
        if self.prepared == (self.error_code is not None):
            raise ValueError("Invalid scheduled trigger prepare error")
        return self


class RenewScheduledTriggerResultDTO(ChatStrictDTO):
    trigger: ScheduledTriggerDTO
    authority_token: str = Field(repr=False)
    authority_expires_at: str
    _timestamp = field_validator("authority_expires_at")(validate_timestamp_text)


class StartScheduledTriggerInputDTO(TriggerClaimInputDTO):
    target_turn_id: Id


class FinishScheduledTriggerInputDTO(TriggerClaimInputDTO):
    status: Literal["succeeded", "failed", "state_unknown"]
    final_message_id: str | None
    error_code: str | None


class ReconcileScheduledTriggerInputDTO(ChatStrictDTO):
    trigger_id: Uuid


class ResolveScheduledAuthorityInputDTO(ChatStrictDTO):
    pass


class ResolveScheduledAuthorityResultDTO(ChatStrictDTO):
    trigger_id: Uuid
    claim_id: Uuid
    service_client_id: Id
    client_id: Id
    subject: Id
    canonical_user_id: Id
    source_thread_id: Id
    target_thread_id: Id
    scopes: list[Literal["dream:read", "dream:write"]]
    purpose: Literal["scheduled-chat-persistence"]
    issued_at: str
    expires_at: str
    _timestamps = field_validator("issued_at", "expires_at")(validate_timestamp_text)


def _operation(name: str, kind: Literal["read", "write"], digest: str, input_dto, output_dto,
               *, user_scope: str | None = None, background_scope: str | None = None):
    return DomainOperation(OperationCapabilityDTO(
        name=name, kind=kind, user_scope=user_scope, background_scope=background_scope,
        input_schema_version=1, output_schema_version=1, contract_sha256=digest,
    ), input_dto, output_dto)


# Digests are from Admin operationRegistry.ts at the reviewed 0069-0072 contract.
CREATE_TASK = _operation("scheduled-task.create", "write", "f13c18ad16080dd0962297bee88b766ba27c0e40b1bba99b8e0a05a49cecb4f6", CreateScheduledTaskInputDTO, ScheduledTaskResultDTO, user_scope="dream:write")
GET_TASK = _operation("scheduled-task.get", "read", "d327a7e5a2064c291da01a8d62cb2e1de3739e53b0139c93a94cc6a47df8cafe", ScheduledTaskIdInputDTO, ScheduledTaskNullableResultDTO, user_scope="dream:read")
DAY_TASK = _operation("scheduled-task.day", "read", "060347d05762aa9b21993f1b6a98339bcaacb930f6c99b2ef8b5c2cc0a784fea", DayScheduledTaskInputDTO, ScheduledTaskDayResultDTO, user_scope="dream:read")
HISTORY_TASK = _operation("scheduled-task.history", "read", "5c4349acd1ab1e2bb657911bf97d794c45a67a0aa5ea9bf1b4d8be75166184c8", HistoryScheduledTaskInputDTO, ScheduledTaskHistoryResultDTO, user_scope="dream:read")
EDIT_TASK = _operation("scheduled-task.edit", "write", "d9ec00ff33d6b040b3c67b888abaa1bb0b22b0b636f9e3c21689db73c1a5e6cd", EditScheduledTaskInputDTO, ScheduledTaskResultDTO, user_scope="dream:write")
PAUSE_TASK = _operation("scheduled-task.pause", "write", "de9ba8227ef0c5157cbdd5f0589150d88a12b40d108470965aa308cb8e856e7b", ScheduledTaskRevisionInputDTO, ScheduledTaskResultDTO, user_scope="dream:write")
RESUME_TASK = _operation("scheduled-task.resume", "write", "06c2626c74071aa2c3a5b1edf671343c1053170e766712bca8fca129b285c108", ScheduledTaskRevisionInputDTO, ScheduledTaskResultDTO, user_scope="dream:write")
DELETE_TASK = _operation("scheduled-task.delete", "write", "e797c81661a6084469a496199a73839809d59c9feab5c18c139b9f63b13af122", ScheduledTaskRevisionInputDTO, ScheduledTaskResultDTO, user_scope="dream:write")
RESTORE_TASK = _operation("scheduled-task.restore", "write", "298b7e02005d4568044481e5c244edd11ccba111a8953ac594704bff4d0ce967", ScheduledTaskRevisionInputDTO, ScheduledTaskResultDTO, user_scope="dream:write")
RUN_TASK = _operation("scheduled-task.run", "write", "a18e5991b2fdcc307ae896675a0ab8a0f68d721a363c253b46e2937fcfe8d90c", RunScheduledTaskInputDTO, ScheduledTriggerResultDTO, user_scope="dream:write")
CLAIM_TRIGGER = _operation("scheduled-trigger.claim", "write", "70e44f8d431c414a5d35fcdd7ee307dd73f034011e3770eb450aec5f30a9aebf", ClaimScheduledTriggerInputDTO, ClaimScheduledTriggerResultDTO, background_scope="schedule:execute")
PREPARE_TRIGGER = _operation("scheduled-trigger.prepare", "write", "53321f0b3be07c06940eafb885f18f9d50d72d48b83a760997604072edac562e", TriggerClaimInputDTO, PrepareScheduledTriggerResultDTO, background_scope="schedule:execute")
RENEW_TRIGGER = _operation("scheduled-trigger.renew", "write", "6c6d768eef30f4929328b7e349ca30389ef221d387cf7079fc179ca5809f7d34", TriggerClaimInputDTO, RenewScheduledTriggerResultDTO, background_scope="schedule:execute")
START_TRIGGER = _operation("scheduled-trigger.start", "write", "020af99b371885b451b1c5aeb6fce5778d425971cc0a3a7bd6cd4ddca2035395", StartScheduledTriggerInputDTO, ScheduledTriggerResultDTO, background_scope="schedule:execute")
FINISH_TRIGGER = _operation("scheduled-trigger.finish", "write", "1e71e7e7699007f894addbd3af67c86f367ba399fb4bf40ff6362deafc394849", FinishScheduledTriggerInputDTO, ScheduledTriggerResultDTO, background_scope="schedule:execute")
RECONCILE_TRIGGER = _operation("scheduled-trigger.reconcile", "write", "9e401ae34d0c2db88446985ca4856c40a731d5ed1847964356162265b78d4181", ReconcileScheduledTriggerInputDTO, ScheduledTriggerResultDTO, background_scope="schedule:execute")
RESOLVE_AUTHORITY = _operation("scheduled-trigger.authority.resolve", "read", "238d55b8f5a8ac395d5d1017ee04e57248418ad761bd3b21a582a786cb79d00c", ResolveScheduledAuthorityInputDTO, ResolveScheduledAuthorityResultDTO, background_scope="schedule:execute")

SCHEDULED_TASK_OPERATIONS = (CREATE_TASK, GET_TASK, DAY_TASK, HISTORY_TASK, EDIT_TASK, PAUSE_TASK, RESUME_TASK, DELETE_TASK, RESTORE_TASK, RUN_TASK,
                             CLAIM_TRIGGER, PREPARE_TRIGGER, RENEW_TRIGGER, START_TRIGGER, FINISH_TRIGGER, RECONCILE_TRIGGER, RESOLVE_AUTHORITY)
SCHEDULED_BACKGROUND_OPERATIONS = (CLAIM_TRIGGER, PREPARE_TRIGGER, RENEW_TRIGGER, START_TRIGGER,
                                   FINISH_TRIGGER, RECONCILE_TRIGGER, RESOLVE_AUTHORITY)
SCHEDULED_SCHEMA_REQUIREMENTS = (
    SchemaCapabilityDTO(capability="dream.chat-scheduled-task.v1", version=1, contract_sha256="bc9773921f07f894508be4baa19e5b625dba1091559f6ec3c5267d5d12080fb0"),
    SchemaCapabilityDTO(capability="dream.chat-scheduled-turn-binding.v1", version=1, contract_sha256="67c8f545d4c4ba4eaaf32f7f5eb281c26b1a27da1a0c26fa517c1c93cdbb7482"),
    SchemaCapabilityDTO(capability="dream.chat-scheduled-link-lifecycle.v1", version=1, contract_sha256="f2c197e58ef80cc2ef69f4af9a623389f6c2461e1ac3130ef3ad7976874a16cd"),
    SchemaCapabilityDTO(capability="identity.scheduled-chat-runtime.v1", version=1, contract_sha256="f84bcd8588c399121a9fd71f6ea4e14bf718a9d6443c5d82f28769300cf2494b"),
)


class AdminScheduledTaskData:
    """Call one exact operation with the caller's existing authorization."""

    def __init__(self, client: AdminDataClient):
        self.client = client

    def execute(self, operation: DomainOperation, input_dto: ChatStrictDTO, request_id: str, *, access_token: str | None = None):
        if operation not in SCHEDULED_TASK_OPERATIONS:
            raise ValueError("Unknown scheduled Chat operation")
        self.client.capabilities_snapshot(request_id)
        required = SCHEDULED_SCHEMA_REQUIREMENTS if operation in SCHEDULED_BACKGROUND_OPERATIONS else SCHEDULED_SCHEMA_REQUIREMENTS[:3]
        if not self.client.supports((operation,), required):
            # A long-lived Dream process may have authenticated and frozen its
            # catalog before Admin published the scheduled-task operations.
            # Refresh exactly once at this read-only contract boundary; the
            # operation itself still follows the existing no-retry policy.
            self.client.capabilities(request_id)
        if not self.client.supports((operation,), required):
            raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)
        return self.client.execute(operation, input_dto, request_id, access_token=access_token)
