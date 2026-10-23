# [Input] Published Admin Reflections v2 scope/evidence operations and the existing content schema.
# [Output] Strict metadata-only creation, actual-read evidence and task-bound authorization DTOs.
# [Pos] Admin-only persistence adapter; no remote Notion I/O or SQL.
# [Sync] 2026-10-23: append v2 consumers while retaining v1 frozen-body compatibility.
from __future__ import annotations
from typing import Annotated, Literal
from pydantic import Field
from .chat_models import ChatStrictDTO
from .client import AdminDataClient
from .errors import AdminDataError
from .models import CommittedReceiptDTO
from .notion_connector_data import NotionLightSnapshotDTO
from .reflection_task_models import ReflectionTaskCreateInputDTO, ReflectionTaskGetOutputDTO, ReflectionTaskLookupDTO
from .reflection_analysis_content_data import (
    CONTENT_SCHEMA, ReflectionAgentInputDTO, ReflectionAnalysisSnapshotDTO,
    ReflectionAnalysisSummaryOutputDTO, ReflectionNotionInputDTO, _operation,
)
SCOPE_CONTRACT_VERSION = "reflections-analysis-content-v2"

class ReflectionNotionScopeSelectionDTO(ChatStrictDTO):
    connector_id: Annotated[str, Field(min_length=1, max_length=256)]
    snapshot_version: Annotated[str, Field(min_length=1, max_length=256)]

class ReflectionNotionReadDTO(ChatStrictDTO):
    page_id: str
    title: str
    url: str | None
    markdown: str
    content_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    read_at: str

class ReflectionNotionScopeDTO(ReflectionNotionInputDTO):
    snapshot: NotionLightSnapshotDTO
    pages: list[ReflectionNotionReadDTO]

class ReflectionScopeSelectionDTO(ChatStrictDTO):
    diary_session_ids: list[str] | None
    notion: ReflectionNotionScopeSelectionDTO | None
    agent: ReflectionAgentInputDTO | None

class ReflectionScopeCreateDTO(ReflectionTaskCreateInputDTO):
    analysis_content: ReflectionScopeSelectionDTO

class ReflectionScopeSnapshotDTO(ReflectionAnalysisSnapshotDTO):
    notion: ReflectionNotionScopeDTO | None

class ReflectionScopeLoadDTO(ChatStrictDTO):
    analysis_content: ReflectionScopeSnapshotDTO

class ReflectionNotionBindingDTO(ChatStrictDTO):
    task_id: str
    section: Literal["echoes", "traits", "patterns"]
    thread_id: str
    section_revision: Annotated[int, Field(gt=0)]
    page_id: str

class ReflectionNotionEvidenceDTO(ReflectionNotionBindingDTO):
    page: ReflectionNotionReadDTO

class ReflectionNotionReadOutputDTO(ChatStrictDTO):
    page: ReflectionNotionReadDTO | None

CREATE_SCOPE = _operation("reflection-task.v2.create-with-content", "write", ReflectionScopeCreateDTO, ReflectionTaskGetOutputDTO, "5516077992d083e644147ccf4e93decaded32d8aeef55e643c42b68d64d9cd7a")
SUMMARY_SCOPE = _operation("reflection-task.v2.analysis-content", "read", ReflectionTaskLookupDTO, ReflectionAnalysisSummaryOutputDTO, "967c136b6a167f9c23cfdff476a8a4228fd12096163eb2a2b54a4d120626f375")
LOAD_SCOPE = _operation("reflection-task.v2.analysis-content-load", "read", ReflectionTaskLookupDTO, ReflectionScopeLoadDTO, "143383a872a963218d9ce6a1bd3d1d984980084011067e83904853c8a09a1527", background=True)
READ_CONTEXT = _operation("reflection-task.v2.notion-context", "read", ReflectionNotionBindingDTO, ReflectionNotionReadOutputDTO, "a86c7edebd90944ee16ca6a0ca9418fb57d084cf72b36a83bf626ff3e92a4440", background=True)
RECORD_EVIDENCE = _operation("reflection-task.v2.notion-evidence", "write", ReflectionNotionEvidenceDTO, ReflectionNotionReadOutputDTO, "4e2fad42990db960b92aedd74fdfc3b1dbba5d605e47b9b858515f39bdd84517", background=True)
SCOPE_OPERATIONS = (CREATE_SCOPE, SUMMARY_SCOPE, LOAD_SCOPE, READ_CONTEXT, RECORD_EVIDENCE)

def require_scope_capability(client, request_id):
    snapshot = client.capabilities_snapshot(request_id)
    schemas = {item.capability: item for item in snapshot.schema_capabilities}
    operations = {item.name: item for item in snapshot.operations}
    if len(schemas) != len(snapshot.schema_capabilities) or len(operations) != len(snapshot.operations) or schemas.get(CONTENT_SCHEMA.capability) != CONTENT_SCHEMA or any(operations.get(op.capability.name) != op.capability for op in SCOPE_OPERATIONS):
        raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)

class AdminReflectionNotionScopeData:
    def __init__(self, client: AdminDataClient):
        self.client = client

    def create(self, value: ReflectionScopeCreateDTO, request_id: str, *, access_token: str):
        require_scope_capability(self.client, request_id)
        try:
            return self.client.execute(CREATE_SCOPE, value, request_id, access_token=access_token)
        except AdminDataError as exc:
            if not exc.outcome_unknown:
                raise
        receipt = self.client.receipt(CREATE_SCOPE, request_id, access_token=access_token)
        if not isinstance(receipt, CommittedReceiptDTO) or type(receipt.result) is not ReflectionTaskGetOutputDTO:
            raise AdminDataError("ADMIN_RESPONSE_INVALID", 503, request_id, outcome_unknown=True)
        return receipt.result

    def summary(self, value: ReflectionTaskLookupDTO, request_id: str, *, access_token: str):
        require_scope_capability(self.client, request_id)
        return self.client.execute(SUMMARY_SCOPE, value, request_id, access_token=access_token)

    def load(self, value: ReflectionTaskLookupDTO, request_id: str):
        require_scope_capability(self.client, request_id)
        return self.client.execute(LOAD_SCOPE, value, request_id)

    def read_context(self, value: ReflectionNotionBindingDTO, request_id: str):
        require_scope_capability(self.client, request_id)
        return self.client.execute(READ_CONTEXT, value, request_id)

    def record(self, value: ReflectionNotionEvidenceDTO, request_id: str):
        require_scope_capability(self.client, request_id)
        return self.client.execute(RECORD_EVIDENCE, value, request_id)
