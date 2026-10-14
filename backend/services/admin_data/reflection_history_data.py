# [Input] Additive Admin history-page descriptor and existing published Reflections schema capabilities.
# [Output] Strict owner history-page consumer with exact ISO instants and decimal report identities.
# [Pos] Reflections read-only history boundary; no SQL, task state or schema writes.
# [Sync] 2026-10-14: preserve Registry99 while exposing complete creation-time history.
from __future__ import annotations

from typing import Annotated
from pydantic import Field, field_validator
from .chat_models import ChatStrictDTO, PositiveSafeInteger, validate_timestamp_text
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError
from .models import OperationCapabilityDTO
from .reflection_task_models import AnalysisReportDTO, ReflectionTaskId
from .reflection_task_data import FROZEN_REFLECTION_TASK_SCHEMA_REQUIREMENTS

ReportId = Annotated[str, Field(pattern=r"^[1-9][0-9]{0,18}$")]

class ReflectionHistoryCursorDTO(ChatStrictDTO):
    created_at: str
    id: ReportId
    _timestamp = field_validator("created_at")(validate_timestamp_text)

    @field_validator("id")
    @classmethod
    def postgres_identity(cls, value: str) -> str:
        if int(value) > 9_223_372_036_854_775_807:
            raise ValueError("Invalid report identity")
        return value

class ReflectionHistoryInputDTO(ChatStrictDTO):
    limit: PositiveSafeInteger = 10
    before: ReflectionHistoryCursorDTO | None = None

class ReflectionHistoryReportDTO(AnalysisReportDTO):
    task_id: ReflectionTaskId | None
    analysis_created_at: str
    _created = field_validator("analysis_created_at")(validate_timestamp_text)

class ReflectionHistoryOutputDTO(ChatStrictDTO):
    reports: list[ReflectionHistoryReportDTO]
    next_cursor: ReflectionHistoryCursorDTO | None

HISTORY_PAGE = DomainOperation(OperationCapabilityDTO(
    name="analysis-report.history-page", kind="read", user_scope="dream:read", background_scope=None,
    input_schema_version=1, output_schema_version=1,
    contract_sha256="a946906d179dc9d7b0b920d21f8b6d4d8a198730114514c99fd0fbc586bcc710",
), ReflectionHistoryInputDTO, ReflectionHistoryOutputDTO)
HISTORY_OPERATIONS = (HISTORY_PAGE,)

class AdminReflectionHistoryData:
    def __init__(self, client: AdminDataClient):
        self.client = client

    def page(self, input_dto: ReflectionHistoryInputDTO, request_id: str, *, access_token: str):
        self.client.capabilities_snapshot(request_id)
        if not self.client.supports(HISTORY_OPERATIONS, FROZEN_REFLECTION_TASK_SCHEMA_REQUIREMENTS):
            raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)
        return self.client.execute(HISTORY_PAGE, input_dto, request_id, access_token=access_token)
