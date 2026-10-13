# [Input] Additive Admin task content contracts and published forward schema capability.
# [Output] Strict immutable analysis input, owner summary and service-task-bound reads.
# [Pos] Reflections input consumer; no SQL, model, credentials, sync or local persistence.
# [Sync] 2026-10-13: preserve Registry99 while freezing Notion bodies and Agent instructions.
"""Additive Reflections content contracts; old diary-only tasks remain on Registry99."""
from __future__ import annotations

from typing import Annotated
from pydantic import Field, model_validator

from .chat_models import ChatStrictDTO
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import CommittedReceiptDTO, OperationCapabilityDTO, SchemaCapabilityDTO
from .reflection_task_models import (
    Identifier256, ReflectionTaskCreateInputDTO, ReflectionTaskGetOutputDTO,
    ReflectionTaskLookupDTO,
)

ANALYSIS_CONTENT_CONTRACT_VERSION = "reflections-analysis-content-v1"
CONTENT_SCHEMA = SchemaCapabilityDTO(
    capability="dream.reflection-analysis-content.v1", version=1,
    contract_sha256="29e5fbc327dff07c65ce4be8be1e42e520f0408b38062ecfdaec866838d55afe",
)

class ReflectionNotionPageDTO(ChatStrictDTO):
    page_id: Identifier256
    title: str
    url: str | None
    markdown: Annotated[str, Field(min_length=1)]
    content_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    read_at: str

class ReflectionNotionInputDTO(ChatStrictDTO):
    connector_id: Identifier256
    snapshot_version: Identifier256
    pages: list[ReflectionNotionPageDTO]
    empty_page_ids: list[Identifier256]

    @model_validator(mode="after")
    def unique_pages(self):
        ids = [page.page_id for page in self.pages] + self.empty_page_ids
        if len(set(ids)) != len(ids):
            raise ValueError("Notion page identities must be unique")
        return self

class ReflectionAgentInputDTO(ChatStrictDTO):
    deck_id: Identifier256
    agent_id: Identifier256

class ReflectionAgentSnapshotDTO(ReflectionAgentInputDTO):
    deck_name: str
    agent_name: str
    system_prompt: str

class ReflectionAnalysisSelectionDTO(ChatStrictDTO):
    diary_session_ids: list[Identifier256] | None
    notion: ReflectionNotionInputDTO | None
    agent: ReflectionAgentInputDTO | None

class ReflectionAnalysisSnapshotDTO(ChatStrictDTO):
    diary_session_ids: list[Identifier256] | None
    notion: ReflectionNotionInputDTO | None
    agent: ReflectionAgentSnapshotDTO | None

class ReflectionAnalysisCreateDTO(ReflectionTaskCreateInputDTO):
    analysis_content: ReflectionAnalysisSelectionDTO

    @model_validator(mode="after")
    def matching_diary_selection(self):
        selected = self.analysis_content.diary_session_ids
        if (selected is None and self.input_snapshot.session_ids) or (selected is not None and selected != self.input_snapshot.session_ids):
            raise ValueError("Diary selection must match the task input")
        return self

class ReflectionNotionPageSummaryDTO(ChatStrictDTO):
    page_id: Identifier256
    title: str
    url: str | None
    content_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    read_at: str

class ReflectionNotionSummaryDTO(ChatStrictDTO):
    connector_id: Identifier256
    snapshot_version: Identifier256
    pages: list[ReflectionNotionPageSummaryDTO]
    empty_page_count: Annotated[int, Field(ge=0, le=9_007_199_254_740_991)]

class ReflectionAgentSummaryDTO(ReflectionAgentInputDTO):
    deck_name: str
    agent_name: str

class ReflectionAnalysisSummaryDTO(ChatStrictDTO):
    diary_session_ids: list[Identifier256] | None
    notion: ReflectionNotionSummaryDTO | None
    agent: ReflectionAgentSummaryDTO | None

class ReflectionAnalysisSummaryOutputDTO(ChatStrictDTO):
    analysis_content: ReflectionAnalysisSummaryDTO | None

class ReflectionAnalysisLoadOutputDTO(ChatStrictDTO):
    analysis_content: ReflectionAnalysisSnapshotDTO

def _operation(name, kind, input_dto, output_dto, digest, *, background=False):
    return DomainOperation(OperationCapabilityDTO(
        name=name, kind=kind, user_scope=None if background else "dream:write" if kind == "write" else "dream:read",
        background_scope="reflections:execute" if background else None,
        input_schema_version=1, output_schema_version=1, contract_sha256=digest,
    ), input_dto, output_dto)

CREATE_WITH_CONTENT = _operation("reflection-task.create-with-content", "write", ReflectionAnalysisCreateDTO, ReflectionTaskGetOutputDTO, "f19c343561dbf9273ffb38b815f0b3685e94ee9876892dd25382d2646d1080a2")
READ_CONTENT_SUMMARY = _operation("reflection-task.analysis-content", "read", ReflectionTaskLookupDTO, ReflectionAnalysisSummaryOutputDTO, "21a76e109a6afd060545ffd6bacdc4c0632d7983cb9befdd7443727ac6814022")
LOAD_CONTENT = _operation("reflection-task.analysis-content-load", "read", ReflectionTaskLookupDTO, ReflectionAnalysisLoadOutputDTO, "f3b8f18199c8a65e80c5c8f20816480d625071a26b900813886d5a5be0caf9cb", background=True)
ANALYSIS_CONTENT_OPERATIONS = (CREATE_WITH_CONTENT, READ_CONTENT_SUMMARY, LOAD_CONTENT)

def require_analysis_content_capability(client: AdminDataClient, request_id: str):
    capabilities = client.capabilities_snapshot(request_id)
    schemas = {item.capability: item for item in capabilities.schema_capabilities}
    operations = {item.name: item for item in capabilities.operations}
    if (len(schemas) != len(capabilities.schema_capabilities) or len(operations) != len(capabilities.operations)
        or schemas.get(CONTENT_SCHEMA.capability) != CONTENT_SCHEMA
        or any(operations.get(operation.capability.name) != operation.capability for operation in ANALYSIS_CONTENT_OPERATIONS)):
        raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)

class AdminReflectionAnalysisContentData:
    def __init__(self, client: AdminDataClient):
        self.client = client

    def create(self, input_dto: ReflectionAnalysisCreateDTO, request_id: str, *, access_token: str):
        require_analysis_content_capability(self.client, request_id)
        try:
            return self.client.execute(CREATE_WITH_CONTENT, input_dto, request_id, access_token=access_token)
        except AdminDataError as exc:
            if not exc.outcome_unknown:
                raise
        receipt = self.client.receipt(CREATE_WITH_CONTENT, request_id, access_token=access_token)
        if not isinstance(receipt, CommittedReceiptDTO) or type(receipt.result) is not ReflectionTaskGetOutputDTO:
            raise invalid_response(request_id, write=True)
        return receipt.result

    def summary(self, input_dto: ReflectionTaskLookupDTO, request_id: str, *, access_token: str):
        require_analysis_content_capability(self.client, request_id)
        return self.client.execute(READ_CONTENT_SUMMARY, input_dto, request_id, access_token=access_token)

    def load(self, input_dto: ReflectionTaskLookupDTO, request_id: str):
        require_analysis_content_capability(self.client, request_id)
        return self.client.execute(LOAD_CONTENT, input_dto, request_id)
