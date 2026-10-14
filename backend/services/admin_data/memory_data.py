# [Input] Frozen Admin memory schemas and authenticated host identity.
# [Output] Strict source-bound memory DTO consumer, with no SQL or actor/path inputs.
# [Pos] Additive Admin memory transport.
# [Sync] 2026-10-15: bind exact artifact and settings operations.
from __future__ import annotations
import json
from pathlib import Path
from typing import Annotated, Literal
from pydantic import Field,field_validator
from .chat_models import ChatStrictDTO,validate_timestamp_text
from .client import DomainOperation, AdminDataClient
from .models import OperationCapabilityDTO, SchemaCapabilityDTO
from .errors import AdminDataError
from .reflection_task_models import ReflectionResultDTO
from .reflection_analysis_content_data import ReflectionAnalysisSummaryDTO

Uuid = Annotated[str, Field(pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')]
Sha = Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]
Revision = Annotated[int, Field(ge=1, le=2147483647)]
Section = Literal['echoes','traits','patterns']
class EmptyDTO(ChatStrictDTO): pass
class ThemeOptionDTO(ChatStrictDTO):
    enabled: bool
    action: Literal['acknowledge_then_help','help_only','ask_support_type','respect_distance','prioritize_actions','connect_goal_to_choice','acknowledge_only']
class ThemesDTO(ChatStrictDTO):
    THEME_FRUSTRATION: ThemeOptionDTO
    THEME_DEFENSE: ThemeOptionDTO
    THEME_PRESSURE: ThemeOptionDTO
    THEME_VALUE: ThemeOptionDTO
class DesiredDTO(ChatStrictDTO):
    enabled: bool
    themes: ThemesDTO
class CatalogDTO(ChatStrictDTO):
    id: str
    label: str
    actions: list[str]
    default_action: str
class SettingsDTO(ChatStrictDTO):
    owner_id: str
    catalog: list[CatalogDTO]
    revision: Annotated[int,Field(ge=0,le=2147483647)]
    taxonomy_revision: Literal['memory-rules-v1']
    default: DesiredDTO
    desired: DesiredDTO
    updated_at: str | None
class SettingsSaveDTO(ChatStrictDTO):
    expected_revision: Annotated[int,Field(ge=0,le=2147483646)]
    desired: DesiredDTO
class MetadataDTO(ChatStrictDTO):
    task_id: Uuid
    report_id: str
    completed_sections: list[Section]
    failed_sections: list[Section]
    item_count: Annotated[int,Field(ge=0)]
    theme_count: Annotated[int,Field(ge=0)]
class ArtifactDTO(ChatStrictDTO):
    artifact_id: Uuid
    revision: Revision
    report_id: str
    state: Literal['pending','running','publishing','ready','empty','failed']
    theme_state: Literal['pending','ready','empty','failed']
    created_at: str
    source_sha256: Sha
    conversion_revision: Literal['memory-rules-v1']
    document: str | None
    document_sha256: Sha | None
    body_sha256: Sha | None
    byte_length: int | None
    theme_document: str | None
    theme_sha256: Sha | None
    metadata: MetadataDTO | None
    error_code: str | None
class LookupDTO(ChatStrictDTO):
    artifact_id: Uuid
    revision: Revision
class ClaimDTO(LookupDTO):
    claim_token: Uuid
class SourceDTO(ChatStrictDTO):
    analysis_content: ReflectionAnalysisSummaryDTO | None
    completed_sections: list[Section]
    task_id: Uuid
    report_id: str
    report_sha256: Sha
    start_date: str | None
    end_date: str | None
    created_at: str
    echoes: list[ReflectionResultDTO]
    traits: list[ReflectionResultDTO]
    patterns: list[ReflectionResultDTO]
    failed_sections: list[Section]
class ClaimResultDTO(ChatStrictDTO):
    artifact: ArtifactDTO | None
    claim_token: Uuid | None
    source: SourceDTO | None
class StageDTO(ClaimDTO):
    document: str | None
    body_sha256: Sha | None
    theme_document: str | None
    metadata: MetadataDTO
    theme_error_code: Literal['MEMORY_THEME_CONVERSION_FAILED'] | None
class PublishDTO(ClaimDTO):
    document_sha256: Sha | None
    theme_sha256: Sha | None
    theme_published: bool
    theme_error_code: Literal['MEMORY_THEME_CONVERSION_FAILED','MEMORY_THEME_PUBLICATION_FAILED'] | None
class FailDTO(ClaimDTO):
    error_code: Literal['MEMORY_CONVERSION_FAILED','MEMORY_PUBLICATION_FAILED']
    retryable: bool
class DiscoverDTO(ChatStrictDTO):
    discovered: Annotated[int,Field(ge=0)]
class CursorDTO(ChatStrictDTO):
    created_at: str
    _timestamp=field_validator("created_at")(validate_timestamp_text)
    artifact_id: Uuid
class ListDTO(ChatStrictDTO):
    limit: Annotated[int,Field(ge=1,le=100)] = 20
    before: CursorDTO | None = None
class ListResultDTO(ChatStrictDTO):
    artifacts: list[ArtifactDTO]
    next_cursor: CursorDTO | None

_CONTRACT=json.loads(Path(__file__).with_name('memory_contract.json').read_text())
_TYPES=[(EmptyDTO,DiscoverDTO),(EmptyDTO,ClaimResultDTO),(StageDTO,ArtifactDTO),(PublishDTO,ArtifactDTO),(FailDTO,ArtifactDTO),(ListDTO,ListResultDTO),(LookupDTO,ArtifactDTO),(EmptyDTO,SettingsDTO),(SettingsSaveDTO,SettingsDTO)]
MEMORY_OPERATIONS=tuple(DomainOperation(OperationCapabilityDTO.model_validate(o['capability']), inp, out) for o,(inp,out) in zip(_CONTRACT['operations'],_TYPES,strict=True))
MEMORY_REQUIREMENTS=tuple(SchemaCapabilityDTO(capability=v['capability'],version=v['version'],contract_sha256=v['contractSha256']) for v in _CONTRACT['operations'][0]['requirements'])
_OPERATIONS={op.capability.name:op for op in MEMORY_OPERATIONS}
class AdminMemoryData:
    def __init__(self,client:AdminDataClient): self.client=client
    def invoke(self,name,input_dto,request_id,*,access_token=None):
        self.client.capabilities_snapshot(request_id)
        if not self.client.supports(MEMORY_OPERATIONS,MEMORY_REQUIREMENTS):
            raise AdminDataError('ADMIN_CAPABILITY_UNAVAILABLE',503,request_id)
        return self.client.execute(_OPERATIONS[name],input_dto,request_id,access_token=access_token)
    def save_receipt(self,request_id,*,access_token):
        return self.client.receipt(_OPERATIONS['memory.behavior.save'],request_id,access_token=access_token)
    def settings(self,input_dto,request_id,*,access_token): return self.invoke('memory.behavior.get',input_dto,request_id,access_token=access_token)
    def save(self,input_dto,request_id,*,access_token): return self.invoke('memory.behavior.save',input_dto,request_id,access_token=access_token)
    def list(self,input_dto,request_id,*,access_token): return self.invoke('memory.distillations.list',input_dto,request_id,access_token=access_token)
    def read(self,input_dto,request_id,*,access_token): return self.invoke('memory.distillations.read',input_dto,request_id,access_token=access_token)
