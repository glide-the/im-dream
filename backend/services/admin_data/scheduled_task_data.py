# [Input] Admin scheduled Chat v1-v3 registry, exact schema capabilities and explicit user or service credentials.
# [Output] Typed recurrence, Thread mode, model snapshot and reconcile consumers without Dream SQL.
# [Pos] Dream scheduled Chat data port; Admin owns time calculation, revision, claims and persistence.
# [Sync] 2026-10-07: consume v3 structured recurrence, source/new Thread mode and immutable model aliases.
# [Sync] 2026-10-07: consume additive v2 operations while retaining the exact v1 DTOs and hashes.
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
ModelAlias = Annotated[str, Field(min_length=1, max_length=120,
                                  pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,119}$")]


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


class IntervalRuleDTO(ChatStrictDTO):
    kind: Literal["interval"]
    interval_minutes: Annotated[int, Field(ge=1, le=2_147_483_647, strict=True)]
    time_zone: Zone


ScheduledRuleV2DTO = OnceRuleDTO | DailyRuleDTO | IntervalRuleDTO


class HourlyRuleDTO(ChatStrictDTO):
    kind: Literal["hourly"]
    interval_hours: Annotated[int, Field(ge=1, le=35_791_394, strict=True)]
    minute: Annotated[int, Field(ge=0, le=59, strict=True)]
    time_zone: Zone


class WeeklyRuleDTO(ChatStrictDTO):
    kind: Literal["weekly"]
    weekdays: Annotated[list[Literal["MO", "TU", "WE", "TH", "FR", "SA", "SU"]],
                        Field(min_length=1, max_length=7)]
    local_time: str
    time_zone: Zone

    @field_validator("weekdays")
    @classmethod
    def require_unique_weekdays(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("weekdays must be unique")
        return value


ScheduledRuleV3DTO = ScheduledRuleV2DTO | HourlyRuleDTO | WeeklyRuleDTO


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


class CreateScheduledTaskV2InputDTO(ChatStrictDTO):
    source_thread_id: Id
    create_request_key: Id
    title: Title
    prompt: Title
    rule: ScheduledRuleV2DTO
    target_editor_session_id: Id | None


class CreateScheduledTaskV3InputDTO(ChatStrictDTO):
    source_thread_id: Id
    create_request_key: Id
    title: Title
    prompt: Title
    rule: ScheduledRuleV3DTO
    target_editor_session_id: Id | None
    run_thread_mode: Literal["source_thread", "new_thread_each_run"]
    model_alias: ModelAlias


class ScheduledTaskIdInputDTO(ChatStrictDTO):
    task_id: Uuid


class ScheduledTaskRevisionInputDTO(ScheduledTaskIdInputDTO):
    expected_revision: Revision


class EditScheduledTaskInputDTO(ScheduledTaskRevisionInputDTO):
    title: Title
    prompt: Title
    rule: ScheduledRuleDTO


class EditScheduledTaskV2InputDTO(ScheduledTaskRevisionInputDTO):
    title: Title
    prompt: Title
    rule: ScheduledRuleV2DTO


class EditScheduledTaskV3InputDTO(ScheduledTaskRevisionInputDTO):
    title: Title
    prompt: Title
    rule: ScheduledRuleV3DTO
    run_thread_mode: Literal["source_thread", "new_thread_each_run"]
    model_alias: ModelAlias


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


class ScheduledTaskV2DTO(ScheduledTaskDTO):
    rule: ScheduledRuleV2DTO


class ScheduledTaskV3DTO(ScheduledTaskV2DTO):
    rule: ScheduledRuleV3DTO
    run_thread_mode: Literal["source_thread", "new_thread_each_run"]
    model_alias: ModelAlias | None


class ScheduledTriggerV3DTO(ScheduledTriggerDTO):
    run_thread_mode_snapshot: Literal["source_thread", "new_thread_each_run"]
    model_alias_snapshot: ModelAlias | None


class ScheduledTaskV2ResultDTO(ChatStrictDTO):
    task: ScheduledTaskV2DTO


class ScheduledTaskV2NullableResultDTO(ChatStrictDTO):
    task: ScheduledTaskV2DTO | None


class ScheduledTaskV3ResultDTO(ChatStrictDTO):
    task: ScheduledTaskV3DTO


class ScheduledTaskV3NullableResultDTO(ChatStrictDTO):
    task: ScheduledTaskV3DTO | None


class ScheduledTriggerV3ResultDTO(ChatStrictDTO):
    trigger: ScheduledTriggerV3DTO


class ScheduledTaskThreadInputDTO(ChatStrictDTO):
    thread_id: Id


class ScheduledTaskThreadSourceDTO(ChatStrictDTO):
    task: ScheduledTaskV2DTO
    trigger: ScheduledTriggerDTO

    @model_validator(mode="after")
    def require_task_binding(self):
        if self.trigger.task_id != self.task.id:
            raise ValueError("Scheduled source task does not match trigger")
        return self


class ScheduledTaskThreadResultDTO(ChatStrictDTO):
    created: list[ScheduledTaskV2DTO]
    source: ScheduledTaskThreadSourceDTO | None


class ScheduledTaskThreadSourceV3DTO(ChatStrictDTO):
    task: ScheduledTaskV3DTO
    trigger: ScheduledTriggerV3DTO

    @model_validator(mode="after")
    def require_task_binding(self):
        if self.trigger.task_id != self.task.id:
            raise ValueError("Scheduled source task does not match trigger")
        return self


class ScheduledTaskThreadV3ResultDTO(ChatStrictDTO):
    created: list[ScheduledTaskV3DTO]
    source: ScheduledTaskThreadSourceV3DTO | None


class ScheduledTaskDayV2ResultDTO(ChatStrictDTO):
    tasks: list[ScheduledTaskV2DTO]
    triggers: list[ScheduledTriggerDTO]


class ScheduledTaskDayV3ResultDTO(ChatStrictDTO):
    tasks: list[ScheduledTaskV3DTO]
    triggers: list[ScheduledTriggerV3DTO]


class ScheduledTaskHistoryV3ResultDTO(ChatStrictDTO):
    triggers: list[ScheduledTriggerV3DTO]


class ClaimScheduledTriggerInputDTO(ChatStrictDTO):
    pass


class ClaimScheduledTriggerResultDTO(ChatStrictDTO):
    trigger: ScheduledTriggerDTO | None
    claim_id: Uuid | None


class ClaimScheduledTriggerV2ResultDTO(ChatStrictDTO):
    action: Literal["idle", "dispatch", "reconcile"]
    trigger: ScheduledTriggerDTO | None = None
    claim_id: Uuid | None = None
    trigger_id: Uuid | None = None

    @model_validator(mode="after")
    def validate_action(self):
        if self.action == "dispatch" and (self.trigger is None or self.claim_id is None or self.trigger_id is not None):
            raise ValueError("Invalid dispatch action")
        if self.action == "reconcile" and (self.trigger_id is None or self.trigger is not None or self.claim_id is not None):
            raise ValueError("Invalid reconcile action")
        if self.action == "idle" and (self.trigger is not None or self.claim_id is not None or self.trigger_id is not None):
            raise ValueError("Invalid idle action")
        return self


class ClaimScheduledTriggerV3ResultDTO(ClaimScheduledTriggerV2ResultDTO):
    trigger: ScheduledTriggerV3DTO | None = None


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


class PrepareScheduledTriggerV2ResultDTO(PrepareScheduledTriggerResultDTO):
    target_editor_session_id: Id | None = None


class PrepareScheduledTriggerV3ResultDTO(ChatStrictDTO):
    prepared: bool
    trigger: ScheduledTriggerV3DTO
    task_session: TaskSessionDTO | None = None
    target_thread_id: Id | None = None
    input_message_id: Id | None = None
    resume_existing_thread: bool | None = None
    model_alias: ModelAlias | None = None
    authority_token: str | None = Field(default=None, repr=False)
    authority_expires_at: str | None = None
    target_editor_session_id: Id | None = None
    error_code: str | None = None
    _timestamp = field_validator("authority_expires_at")(validate_timestamp_text)

    @model_validator(mode="after")
    def validate_prepared_result(self):
        required = (self.target_thread_id is not None and self.input_message_id is not None
                    and self.resume_existing_thread is not None and self.authority_token is not None
                    and self.authority_expires_at is not None)
        if self.prepared != required:
            raise ValueError("Invalid scheduled trigger prepare response")
        if self.prepared == (self.error_code is not None):
            raise ValueError("Invalid scheduled trigger prepare error")
        if not self.prepared and (self.task_session is not None or self.model_alias is not None
                                  or self.target_editor_session_id is not None):
            raise ValueError("Invalid failed scheduled trigger prepare response")
        return self


class RenewScheduledTriggerResultDTO(ChatStrictDTO):
    trigger: ScheduledTriggerDTO
    authority_token: str = Field(repr=False)
    authority_expires_at: str
    _timestamp = field_validator("authority_expires_at")(validate_timestamp_text)


class RenewScheduledTriggerV3ResultDTO(RenewScheduledTriggerResultDTO):
    trigger: ScheduledTriggerV3DTO


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


class ResolveScheduledAuthorityV2ResultDTO(ResolveScheduledAuthorityResultDTO):
    target_editor_session_id: Id | None


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

CREATE_TASK_V2 = _operation("scheduled-task.v2.create", "write", "4a6713f745d7442635c528e47b7cfa081cc4b7943043add19b68f6d2e61ef6f0", CreateScheduledTaskV2InputDTO, ScheduledTaskV2ResultDTO, user_scope="dream:write")
GET_TASK_V2 = _operation("scheduled-task.v2.get", "read", "e94d453ace1494a557b6e5b2c0e90efac412133715cd65a722bddeb0e77ee506", ScheduledTaskIdInputDTO, ScheduledTaskV2NullableResultDTO, user_scope="dream:read")
DAY_TASK_V2 = _operation("scheduled-task.v2.day", "read", "e0495aec9c1858f563c518647feb23c692d80a67c7dc4b43af7c3bd8f93807dd", DayScheduledTaskInputDTO, ScheduledTaskDayV2ResultDTO, user_scope="dream:read")
HISTORY_TASK_V2 = _operation("scheduled-task.v2.history", "read", "184c7b58751959b917915c1d79e1d1c17d1552b2139269765f25c0361465eccf", HistoryScheduledTaskInputDTO, ScheduledTaskHistoryResultDTO, user_scope="dream:read")
EDIT_TASK_V2 = _operation("scheduled-task.v2.edit", "write", "d6e2c28763fccfdfcfd066eaa0f915128d00553e267d461eb993af2f0d13777e", EditScheduledTaskV2InputDTO, ScheduledTaskV2ResultDTO, user_scope="dream:write")
PAUSE_TASK_V2 = _operation("scheduled-task.v2.pause", "write", "6db6b385119e83fab9988545f24aa6138ece1b58100d77585870bdc82a4905bf", ScheduledTaskRevisionInputDTO, ScheduledTaskV2ResultDTO, user_scope="dream:write")
RESUME_TASK_V2 = _operation("scheduled-task.v2.resume", "write", "2d753c1c1080e60a3305f367ac651a736364ca90ee13020cb71d2f3872569fd1", ScheduledTaskRevisionInputDTO, ScheduledTaskV2ResultDTO, user_scope="dream:write")
DELETE_TASK_V2 = _operation("scheduled-task.v2.delete", "write", "f41b0b09d2ba8a5e7a01265b317a5dcd85997d65c284b8079490d0ee204f00e1", ScheduledTaskRevisionInputDTO, ScheduledTaskV2ResultDTO, user_scope="dream:write")
RESTORE_TASK_V2 = _operation("scheduled-task.v2.restore", "write", "15b084d04db2a2e2116fc9e7314459ac40fcc5173373cac320befbe8e12ec320", ScheduledTaskRevisionInputDTO, ScheduledTaskV2ResultDTO, user_scope="dream:write")
RUN_TASK_V2 = _operation("scheduled-task.v2.run", "write", "7e1d6242c87020c4e0f42e1e009550578f998efd6a672acd1365b14194d8ae22", RunScheduledTaskInputDTO, ScheduledTriggerResultDTO, user_scope="dream:write")
CLAIM_TRIGGER_V2 = _operation("scheduled-trigger.v2.claim", "write", "9991a758e9a4e22df5aa1c011180a612186c7951e2ce91139a4035bfa883c500", ClaimScheduledTriggerInputDTO, ClaimScheduledTriggerV2ResultDTO, background_scope="schedule:execute")
PREPARE_TRIGGER_V2 = _operation("scheduled-trigger.v2.prepare", "write", "85fad1daca86cf76fa58dc377b5d3d8f597efb0f79de172f77e6c91ddeb38905", TriggerClaimInputDTO, PrepareScheduledTriggerV2ResultDTO, background_scope="schedule:execute")
RENEW_TRIGGER_V2 = _operation("scheduled-trigger.v2.renew", "write", "5b52c61e006bf179aff473a357b8d4bfc5a40deb0cb7669c1d76e6e1740cd160", TriggerClaimInputDTO, RenewScheduledTriggerResultDTO, background_scope="schedule:execute")
START_TRIGGER_V2 = _operation("scheduled-trigger.v2.start", "write", "6f3b5ff536d7b3642039fb39b80e27335a6e49cb0ef759972b1d2561366bbd9a", StartScheduledTriggerInputDTO, ScheduledTriggerResultDTO, background_scope="schedule:execute")
FINISH_TRIGGER_V2 = _operation("scheduled-trigger.v2.finish", "write", "5b257e9965fbe467889f0c199c5e40c47105138305abc2c02bd93cd15ab558ab", FinishScheduledTriggerInputDTO, ScheduledTriggerResultDTO, background_scope="schedule:execute")
RECONCILE_TRIGGER_V2 = _operation("scheduled-trigger.v2.reconcile", "write", "8119e07f2998055f4e00c31b8f8ed8cee66ac896f619b931741a287750748cf1", ReconcileScheduledTriggerInputDTO, ScheduledTriggerResultDTO, background_scope="schedule:execute")
RESOLVE_AUTHORITY_V2 = _operation("scheduled-trigger.v2.authority.resolve", "read", "95dcbe90c06c292d1289a9d88655ec27a4f54701a336519ad4ed43a7a217b3de", ResolveScheduledAuthorityInputDTO, ResolveScheduledAuthorityV2ResultDTO, background_scope="schedule:execute")
THREAD_TASKS_V2 = _operation("scheduled-task.v2.thread", "read", "8a49ad6c633e89d2272e187fb3ad85239fad22bbaa6fef823c2b0c22f565b389", ScheduledTaskThreadInputDTO, ScheduledTaskThreadResultDTO, user_scope="dream:read")

CREATE_TASK_V3 = _operation("scheduled-task.v3.create", "write", "0d476106bb25db0807130710a2b8cf23911c0c9dc848bf5bed510202f108dda0", CreateScheduledTaskV3InputDTO, ScheduledTaskV3ResultDTO, user_scope="dream:write")
GET_TASK_V3 = _operation("scheduled-task.v3.get", "read", "f3d0213eb345ea3930daf935b8bcb29113b5631d7ddc86557a4dcfa091eeb797", ScheduledTaskIdInputDTO, ScheduledTaskV3NullableResultDTO, user_scope="dream:read")
DAY_TASK_V3 = _operation("scheduled-task.v3.day", "read", "44ffd315e49e26707a80f620646adc79e5b4fbc3999d23894b72dc526a16578c", DayScheduledTaskInputDTO, ScheduledTaskDayV3ResultDTO, user_scope="dream:read")
HISTORY_TASK_V3 = _operation("scheduled-task.v3.history", "read", "cb5698f57ca43892102599f5f4a2f3ab5f234a862642b01667d3527344e5d432", HistoryScheduledTaskInputDTO, ScheduledTaskHistoryV3ResultDTO, user_scope="dream:read")
EDIT_TASK_V3 = _operation("scheduled-task.v3.edit", "write", "022bdbb7137bd6fe316c134831b1c5cf41f365b4680aae0b7524a333de729b0c", EditScheduledTaskV3InputDTO, ScheduledTaskV3ResultDTO, user_scope="dream:write")
PAUSE_TASK_V3 = _operation("scheduled-task.v3.pause", "write", "b602c5a2ab43b6b389c5e8fdcc9a2eb1be209c2b4f03b1efee8a248c274d821b", ScheduledTaskRevisionInputDTO, ScheduledTaskV3ResultDTO, user_scope="dream:write")
RESUME_TASK_V3 = _operation("scheduled-task.v3.resume", "write", "b55aed77ac8fd56566ddd1ea6af7ac93dde4329e48d5dcd9a61ef2d6a36f16f3", ScheduledTaskRevisionInputDTO, ScheduledTaskV3ResultDTO, user_scope="dream:write")
DELETE_TASK_V3 = _operation("scheduled-task.v3.delete", "write", "f9bbfeb60786ce6099e025ff602f169189dd7878fc3e4a4b0abf6afd0e3ffb93", ScheduledTaskRevisionInputDTO, ScheduledTaskV3ResultDTO, user_scope="dream:write")
RESTORE_TASK_V3 = _operation("scheduled-task.v3.restore", "write", "1e04844dc2db1a3d9967dd2141e43b5d19326734d03d4eccdab3d0508b80f9e4", ScheduledTaskRevisionInputDTO, ScheduledTaskV3ResultDTO, user_scope="dream:write")
RUN_TASK_V3 = _operation("scheduled-task.v3.run", "write", "64374ee99b6a28e5f9a8661e85e2aaad3c035f859c0e5b287f65482f3f79e3e0", RunScheduledTaskInputDTO, ScheduledTriggerV3ResultDTO, user_scope="dream:write")
CLAIM_TRIGGER_V3 = _operation("scheduled-trigger.v3.claim", "write", "a8ab8e4c6f8fdf8a07754cc9b3e64b6bc5792103256ddd595099401cbfdb090e", ClaimScheduledTriggerInputDTO, ClaimScheduledTriggerV3ResultDTO, background_scope="schedule:execute")
PREPARE_TRIGGER_V3 = _operation("scheduled-trigger.v3.prepare", "write", "a41ee1d9d98b652d4c84622424b00f483efacb0da8b284f085303ecde3db504b", TriggerClaimInputDTO, PrepareScheduledTriggerV3ResultDTO, background_scope="schedule:execute")
RENEW_TRIGGER_V3 = _operation("scheduled-trigger.v3.renew", "write", "4db03dc3e5ed4c20ae7107d73876073f5084604368ce95cf11ca89a5b790e0d3", TriggerClaimInputDTO, RenewScheduledTriggerV3ResultDTO, background_scope="schedule:execute")
START_TRIGGER_V3 = _operation("scheduled-trigger.v3.start", "write", "ba37093b20fbd47973ae87d25688781acde14f57257acd50b311accfed927828", StartScheduledTriggerInputDTO, ScheduledTriggerV3ResultDTO, background_scope="schedule:execute")
FINISH_TRIGGER_V3 = _operation("scheduled-trigger.v3.finish", "write", "77953b000b00141a6eaafc74f1f8eb9188340dc1cc9298cf055f886042cd9e8d", FinishScheduledTriggerInputDTO, ScheduledTriggerV3ResultDTO, background_scope="schedule:execute")
RECONCILE_TRIGGER_V3 = _operation("scheduled-trigger.v3.reconcile", "write", "849f1ed5665af83e9bd70a4042538de516fe427a7978ad1d3e4054b6ea35ec9c", ReconcileScheduledTriggerInputDTO, ScheduledTriggerV3ResultDTO, background_scope="schedule:execute")
RESOLVE_AUTHORITY_V3 = _operation("scheduled-trigger.v3.authority.resolve", "read", "530ab507d30a660e6c99a43d8e76a86a0208096df538fa8a376b0ea288f02c8f", ResolveScheduledAuthorityInputDTO, ResolveScheduledAuthorityV2ResultDTO, background_scope="schedule:execute")
THREAD_TASKS_V3 = _operation("scheduled-task.v3.thread", "read", "059f068a107c5d8a025b2742ab510d52eea8143c2d679699ee8368d9349f47c1", ScheduledTaskThreadInputDTO, ScheduledTaskThreadV3ResultDTO, user_scope="dream:read")

SCHEDULED_TASK_OPERATIONS = (CREATE_TASK, GET_TASK, DAY_TASK, HISTORY_TASK, EDIT_TASK, PAUSE_TASK, RESUME_TASK, DELETE_TASK, RESTORE_TASK, RUN_TASK,
                             CLAIM_TRIGGER, PREPARE_TRIGGER, RENEW_TRIGGER, START_TRIGGER, FINISH_TRIGGER, RECONCILE_TRIGGER, RESOLVE_AUTHORITY)
SCHEDULED_BACKGROUND_OPERATIONS = (CLAIM_TRIGGER, PREPARE_TRIGGER, RENEW_TRIGGER, START_TRIGGER,
                                   FINISH_TRIGGER, RECONCILE_TRIGGER, RESOLVE_AUTHORITY)
SCHEDULED_TASK_V2_OPERATIONS = (CREATE_TASK_V2, GET_TASK_V2, DAY_TASK_V2, HISTORY_TASK_V2, EDIT_TASK_V2,
                                PAUSE_TASK_V2, RESUME_TASK_V2, DELETE_TASK_V2, RESTORE_TASK_V2, RUN_TASK_V2,
                                CLAIM_TRIGGER_V2, PREPARE_TRIGGER_V2, RENEW_TRIGGER_V2, START_TRIGGER_V2,
                                FINISH_TRIGGER_V2, RECONCILE_TRIGGER_V2, RESOLVE_AUTHORITY_V2, THREAD_TASKS_V2)
SCHEDULED_BACKGROUND_V2_OPERATIONS = (CLAIM_TRIGGER_V2, PREPARE_TRIGGER_V2, RENEW_TRIGGER_V2,
                                      START_TRIGGER_V2, FINISH_TRIGGER_V2, RECONCILE_TRIGGER_V2,
                                      RESOLVE_AUTHORITY_V2)
SCHEDULED_TASK_V3_OPERATIONS = (CREATE_TASK_V3, GET_TASK_V3, DAY_TASK_V3, HISTORY_TASK_V3, EDIT_TASK_V3,
                                PAUSE_TASK_V3, RESUME_TASK_V3, DELETE_TASK_V3, RESTORE_TASK_V3, RUN_TASK_V3,
                                CLAIM_TRIGGER_V3, PREPARE_TRIGGER_V3, RENEW_TRIGGER_V3, START_TRIGGER_V3,
                                FINISH_TRIGGER_V3, RECONCILE_TRIGGER_V3, RESOLVE_AUTHORITY_V3, THREAD_TASKS_V3)
SCHEDULED_BACKGROUND_V3_OPERATIONS = (CLAIM_TRIGGER_V3, PREPARE_TRIGGER_V3, RENEW_TRIGGER_V3,
                                      START_TRIGGER_V3, FINISH_TRIGGER_V3, RECONCILE_TRIGGER_V3,
                                      RESOLVE_AUTHORITY_V3)
SCHEDULED_SCHEMA_REQUIREMENTS = (
    SchemaCapabilityDTO(capability="dream.chat-scheduled-task.v1", version=1, contract_sha256="bc9773921f07f894508be4baa19e5b625dba1091559f6ec3c5267d5d12080fb0"),
    SchemaCapabilityDTO(capability="dream.chat-scheduled-turn-binding.v1", version=1, contract_sha256="67c8f545d4c4ba4eaaf32f7f5eb281c26b1a27da1a0c26fa517c1c93cdbb7482"),
    SchemaCapabilityDTO(capability="dream.chat-scheduled-link-lifecycle.v1", version=1, contract_sha256="f2c197e58ef80cc2ef69f4af9a623389f6c2461e1ac3130ef3ad7976874a16cd"),
    SchemaCapabilityDTO(capability="identity.scheduled-chat-runtime.v1", version=1, contract_sha256="f84bcd8588c399121a9fd71f6ea4e14bf718a9d6443c5d82f28769300cf2494b"),
)
SCHEDULED_V2_SCHEMA_REQUIREMENTS = (
    SchemaCapabilityDTO(capability="dream.chat-scheduled-task.v2", version=2, contract_sha256="41de2c831e60a0365a8d9fb99b64e224a677f730de9f4d1a783b15cb6478d2e5"),
    *SCHEDULED_SCHEMA_REQUIREMENTS[1:],
)
SCHEDULED_V3_SCHEMA_REQUIREMENTS = (
    SchemaCapabilityDTO(capability="dream.chat-scheduled-task.v3", version=3, contract_sha256="b96dbec6e1fafe249c9e545b3aa5d8549e6e02d17b968e7dcf164bde814d7f91"),
    *SCHEDULED_SCHEMA_REQUIREMENTS[1:],
)


class AdminScheduledTaskData:
    """Call one exact operation with the caller's existing authorization."""

    def __init__(self, client: AdminDataClient):
        self.client = client

    def execute(self, operation: DomainOperation, input_dto: ChatStrictDTO, request_id: str, *, access_token: str | None = None):
        if operation not in (*SCHEDULED_TASK_OPERATIONS, *SCHEDULED_TASK_V2_OPERATIONS, *SCHEDULED_TASK_V3_OPERATIONS):
            raise ValueError("Unknown scheduled Chat operation")
        self.client.capabilities_snapshot(request_id)
        if operation in SCHEDULED_TASK_V3_OPERATIONS:
            required = SCHEDULED_V3_SCHEMA_REQUIREMENTS if operation in SCHEDULED_BACKGROUND_V3_OPERATIONS else SCHEDULED_V3_SCHEMA_REQUIREMENTS[:3]
        elif operation in SCHEDULED_TASK_V2_OPERATIONS:
            required = SCHEDULED_V2_SCHEMA_REQUIREMENTS if operation in SCHEDULED_BACKGROUND_V2_OPERATIONS else SCHEDULED_V2_SCHEMA_REQUIREMENTS[:3]
        else:
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
