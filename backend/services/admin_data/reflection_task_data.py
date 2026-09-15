# [Input] Strict Reflections DTOs plus Registry99 frozen Admin operation/schema capabilities.
# [Output] Production contract binding, OAuth consumer, and service worker with exact receipt recovery.
# [Pos] Reflections Admin composition boundary; constants match the reviewed Registry99 artifact digest.
# [Sync] 2026-09-15: freeze and compose all sixteen registered operations and three schema capabilities.
"""Typed Admin Reflections consumers bound to the reviewed Registry99 artifact."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping

from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import CommittedReceiptDTO, OperationCapabilityDTO, SchemaCapabilityDTO
from . import reflection_task_models as dto


@dataclass(frozen=True, slots=True)
class ReflectionTaskOperationSpec:
    name: str
    audience: str
    kind: str
    user_scope: str | None
    background_scope: str | None
    input_dto: type
    output_dto: type


REFLECTION_TASK_OPERATION_SPECS = (
    ReflectionTaskOperationSpec(
        "reflection-task.create", "oauth", "write", "dream:write", None,
        dto.ReflectionTaskCreateInputDTO, dto.ReflectionTaskGetOutputDTO,
    ),
    ReflectionTaskOperationSpec(
        "reflection-task.start", "oauth", "write", "dream:write", None,
        dto.ReflectionTaskLookupDTO, dto.ReflectionTaskStartOutputDTO,
    ),
    ReflectionTaskOperationSpec(
        "reflection-task.get", "oauth", "read", "dream:read", None,
        dto.ReflectionTaskLookupDTO, dto.ReflectionTaskGetOutputDTO,
    ),
    ReflectionTaskOperationSpec(
        "reflection-task.latest", "oauth", "read", "dream:read", None,
        dto.ReflectionTaskLatestInputDTO, dto.ReflectionTaskLatestOutputDTO,
    ),
    ReflectionTaskOperationSpec(
        "reflection-task.events", "oauth", "read", "dream:read", None,
        dto.ReflectionEventListInputDTO, dto.ReflectionEventListOutputDTO,
    ),
    ReflectionTaskOperationSpec(
        "analysis-report.list", "oauth", "read", "dream:read", None,
        dto.AnalysisReportListInputDTO, dto.AnalysisReportListOutputDTO,
    ),
    ReflectionTaskOperationSpec(
        "analysis-report.save", "oauth", "write", "dream:write", None,
        dto.AnalysisReportSaveInputDTO, dto.AnalysisReportSaveOutputDTO,
    ),
    ReflectionTaskOperationSpec(
        "reflection-task.worker-load", "background", "write", None,
        "reflections:execute", dto.ReflectionTaskLookupDTO,
        dto.ReflectionWorkerLoadOutputDTO,
    ),
    ReflectionTaskOperationSpec(
        "reflection-task.advance", "background", "write", None,
        "reflections:execute", dto.ReflectionTaskAdvanceInputDTO,
        dto.ReflectionTaskAdvanceOutputDTO,
    ),
    ReflectionTaskOperationSpec(
        "reflection-section.begin", "background", "write", None,
        "reflections:execute", dto.ReflectionSectionBeginInputDTO,
        dto.ReflectionSectionBeginOutputDTO,
    ),
    ReflectionTaskOperationSpec(
        "reflection-section.authority-renew", "background", "write", None,
        "reflections:execute", dto.ReflectionSectionAuthorityInputDTO,
        dto.ReflectionSectionAuthorityRenewOutputDTO,
    ),
    ReflectionTaskOperationSpec(
        "reflection-section.authority-revoke", "background", "write", None,
        "reflections:execute", dto.ReflectionSectionAuthorityInputDTO,
        dto.ReflectionSectionAuthorityRevokeOutputDTO,
    ),
    ReflectionTaskOperationSpec(
        "reflection-section.transcript", "background", "read", None,
        "reflections:execute", dto.ReflectionSectionTranscriptInputDTO,
        dto.ReflectionSectionTranscriptOutputDTO,
    ),
    ReflectionTaskOperationSpec(
        "reflection-section.finish", "background", "write", None,
        "reflections:execute", dto.ReflectionSectionFinishInputDTO,
        dto.ReflectionSectionFinishOutputDTO,
    ),
    ReflectionTaskOperationSpec(
        "reflection-event.append", "background", "write", None,
        "reflections:execute", dto.ReflectionEventAppendInputDTO,
        dto.ReflectionEventAppendOutputDTO,
    ),
    ReflectionTaskOperationSpec(
        "reflection-report.ensure", "background", "write", None,
        "reflections:execute", dto.ReflectionTaskLookupDTO,
        dto.ReflectionReportEnsureOutputDTO,
    ),
)

REFLECTION_TASK_ADMIN_ARTIFACT_SHA256 = "2af7477c424a92c39a1d323b301ef698da147dfa4f1aeb4e8a2166f146981365"
REFLECTION_TASK_ADMIN_SOURCE_COMMIT = "16a3d9b2796254fa525a966ca851de96d4373445"
REFLECTION_TASK_ADMIN_SOURCE_TREE = "4ea27088b777163b0e615f963d4e63c32785d69f"
_FROZEN_OPERATION_HASHES = MappingProxyType({
    "reflection-task.create": "c15d1675c16fec60c5c2959dd77913b45ce2fd896a7f34b323112a591b6649af",
    "reflection-task.start": "0a48caa7fb2b25c25162bb5bc493dfe41016023de100eeab0f3f67362726610f",
    "reflection-task.get": "aa53e2b8689cb836e852d6abba39a8842358af64b64d017e5f39df51cb75290e",
    "reflection-task.latest": "ff632283e74a9d8d1d9a42b1641dbcd3e89d5b2bd0993be2878cdea0a85cc709",
    "reflection-task.events": "229d9646d60f27fb284b0be14d3567dfbc231f5909d1af328e72a32be0651e8e",
    "analysis-report.list": "d3507e7ae1cd644bed39f516965cd3a9844ec52c17544f7d6c843dfb0181dcf1",
    "analysis-report.save": "10a26b2fa8af292d5280a86657c6a1dc50a85f52806f9912cf13feaf0f0240c4",
    "reflection-task.worker-load": "4c146054a3d850898582ea1fa303c8039c8ae463cceb7819392450a03ee3c625",
    "reflection-task.advance": "1decdb10f19e0f9cfe16d34f082926e674f9e6cad9a456ac27a0c42ead910516",
    "reflection-section.begin": "b08b0d2b57f03ead192ad47bd478c1b5334666d8e14be860ea4b480fcdc877ee",
    "reflection-section.authority-renew": "f75ac8776ab2ea663594ee11b6f7fff9c2d0cc5a473f27de0ddf6bf88f4c65f0",
    "reflection-section.authority-revoke": "bee7e82dcaefe42ae9e7821265f980eb07cf29d17a067a7987ba98d5fdb5c826",
    "reflection-section.transcript": "27775c5bb6c5510a384a964181419f73d7c42505ea137a833c624aeb8213d00c",
    "reflection-section.finish": "692adcd9cf5c2f622c508f26eec3cebafc2d8ab44b5cc592ecc71d20e4fa666c",
    "reflection-event.append": "68f77f0927e78c6abd71e4dafd42a1ae6ae0f2c62178de50bcd22ceb62cdad66",
    "reflection-report.ensure": "91ec47469be17a39e36ebc9aa493489337a6e8d0d42dbff79da3cc979ca35864",
})
FROZEN_REFLECTION_TASK_OPERATION_CAPABILITIES = tuple(
    OperationCapabilityDTO(
        name=spec.name,
        kind=spec.kind,
        user_scope=spec.user_scope,
        background_scope=spec.background_scope,
        input_schema_version=1,
        output_schema_version=1,
        contract_sha256=_FROZEN_OPERATION_HASHES[spec.name],
    )
    for spec in REFLECTION_TASK_OPERATION_SPECS
)
FROZEN_REFLECTION_TASK_SCHEMA_REQUIREMENTS = (
    SchemaCapabilityDTO(
        capability="identity.better-auth.v1",
        version=1,
        contract_sha256="1dc05e229d3f4147923fcdfe117c4c4930a43bf9f31439d7b4bc83d2a0d04cd3",
    ),
    SchemaCapabilityDTO(
        capability="dream.schema.unified.v1",
        version=1,
        contract_sha256="8b71cf5687f61dee884c3e6f2fb109c7a951b0789066a0f13583a7b67757fa71",
    ),
    SchemaCapabilityDTO(
        capability="dream.reflection-task-persistence.v1",
        version=1,
        contract_sha256="52340d24e76db9ee91dfbe8748ebaf3b0f3c2d20f15367c1c096d2e869d4753f",
    ),
)
_SPECS_BY_NAME = MappingProxyType(
    {spec.name: spec for spec in REFLECTION_TASK_OPERATION_SPECS}
)
_SCHEMA_NAMES = frozenset(
    {
        "identity.better-auth.v1",
        "dream.schema.unified.v1",
        "dream.reflection-task-persistence.v1",
    }
)


@dataclass(frozen=True, slots=True)
class ReflectionTaskContracts:
    """Source-owned frozen capabilities bound to the code-owned DTO shapes."""

    operations: tuple[DomainOperation, ...]
    schema_requirements: tuple[SchemaCapabilityDTO, ...]
    _by_name: Mapping[str, DomainOperation]

    def __post_init__(self) -> None:
        operation_by_name = {
            operation.capability.name: operation for operation in self.operations
        }
        schema_by_name = {
            requirement.capability: requirement
            for requirement in self.schema_requirements
        }
        if (
            len(operation_by_name) != len(self.operations)
            or set(operation_by_name) != set(_SPECS_BY_NAME)
            or len(schema_by_name) != len(self.schema_requirements)
            or set(schema_by_name) != _SCHEMA_NAMES
            or any(
                self._by_name.get(name) is not operation
                for name, operation in operation_by_name.items()
            )
        ):
            raise AdminDataError("ADMIN_OPERATION_CONTRACT_INVALID", 503)
        for name, operation in operation_by_name.items():
            spec = _SPECS_BY_NAME[name]
            capability = operation.capability
            if (
                capability.kind != spec.kind
                or capability.user_scope != spec.user_scope
                or capability.background_scope != spec.background_scope
                or operation.input_dto is not spec.input_dto
                or operation.output_dto is not spec.output_dto
            ):
                raise AdminDataError("ADMIN_OPERATION_CONTRACT_INVALID", 503)

    def operation(self, name: str) -> DomainOperation:
        try:
            return self._by_name[name]
        except KeyError:
            raise AdminDataError("ADMIN_OPERATION_CONTRACT_INVALID", 503) from None


def bind_frozen_reflection_task_contracts(
    operation_capabilities: Iterable[OperationCapabilityDTO],
    schema_requirements: Iterable[SchemaCapabilityDTO],
) -> ReflectionTaskContracts:
    """Bind reviewed constants; callers must never pass live discovery output here."""

    capabilities = tuple(operation_capabilities)
    capability_by_name = {item.name: item for item in capabilities}
    schemas = tuple(schema_requirements)
    schema_by_name = {item.capability: item for item in schemas}
    if (
        len(capability_by_name) != len(capabilities)
        or set(capability_by_name) != set(_SPECS_BY_NAME)
        or len(schema_by_name) != len(schemas)
        or set(schema_by_name) != _SCHEMA_NAMES
    ):
        raise AdminDataError("ADMIN_OPERATION_CONTRACT_INVALID", 503)

    operations: list[DomainOperation] = []
    for spec in REFLECTION_TASK_OPERATION_SPECS:
        capability = capability_by_name[spec.name]
        if (
            capability.kind != spec.kind
            or capability.user_scope != spec.user_scope
            or capability.background_scope != spec.background_scope
            or capability.input_schema_version != 1
            or capability.output_schema_version != 1
        ):
            raise AdminDataError("ADMIN_OPERATION_CONTRACT_INVALID", 503)
        operations.append(
            DomainOperation(capability, spec.input_dto, spec.output_dto)
        )
    by_name = MappingProxyType(
        {operation.capability.name: operation for operation in operations}
    )
    return ReflectionTaskContracts(tuple(operations), schemas, by_name)


FROZEN_REFLECTION_TASK_CONTRACTS = bind_frozen_reflection_task_contracts(
    FROZEN_REFLECTION_TASK_OPERATION_CAPABILITIES,
    FROZEN_REFLECTION_TASK_SCHEMA_REQUIREMENTS,
)


def require_reflection_task_capabilities(
    client: AdminDataClient,
    contracts: ReflectionTaskContracts,
    request_id: str,
) -> None:
    capabilities = client.capabilities(request_id)
    schemas = {item.capability: item for item in capabilities.schema_capabilities}
    if len(schemas) != len(capabilities.schema_capabilities) or any(
        schemas.get(required.capability) != required
        for required in contracts.schema_requirements
    ):
        raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)


def _validate_task_results(
    result: dto.ReflectionTaskGetOutputDTO,
    request_id: str,
    *,
    task_id: str | None = None,
    write: bool = False,
) -> dto.ReflectionTaskGetOutputDTO:
    expected = task_id or result.task.task_id
    if result.task.task_id != expected or any(
        item.task_id != result.task.task_id for item in result.results
    ):
        raise invalid_response(request_id, write=write)
    return result


class _ReflectionConsumerBase:
    def __init__(
        self, client: AdminDataClient, contracts: ReflectionTaskContracts
    ) -> None:
        self._client = client
        self._contracts = contracts

    def _execute(
        self,
        name: str,
        input_dto,
        request_id: str,
        *,
        access_token: str | None = None,
    ):
        require_reflection_task_capabilities(
            self._client, self._contracts, request_id
        )
        return self._client.execute(
            self._contracts.operation(name),
            input_dto,
            request_id,
            access_token=access_token,
        )

    def _write(
        self,
        name: str,
        input_dto,
        request_id: str,
        *,
        access_token: str | None = None,
        task_id: str | None = None,
    ):
        operation = self._contracts.operation(name)
        try:
            return self._execute(
                name, input_dto, request_id, access_token=access_token
            )
        except AdminDataError as error:
            if not error.outcome_unknown:
                raise
        try:
            if task_id is None:
                receipt = self._client.receipt(
                    operation, request_id, access_token=access_token
                )
            else:
                if access_token is not None:
                    raise AdminDataError(
                        "ADMIN_OPERATION_CONTRACT_INVALID", 503, request_id
                    )
                receipt = self._client.reflection_task_receipt(
                    operation, request_id, task_id=task_id
                )
        except AdminDataError as error:
            raise AdminDataError(
                error.code,
                error.status_code,
                request_id,
                True,
                error.details,
            ) from None
        if not isinstance(receipt, CommittedReceiptDTO):
            raise AdminDataError(
                "ADMIN_WRITE_RESULT_UNKNOWN", 503, request_id, True
            )
        if type(receipt.result) is not operation.output_dto:
            raise invalid_response(request_id, write=True)
        return receipt.result


class AdminReflectionsData(_ReflectionConsumerBase):
    """Request OAuth consumer for tasks, event history and manual reports."""

    def create(
        self,
        input_dto: dto.ReflectionTaskCreateInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> dto.ReflectionTaskGetOutputDTO:
        result = self._write(
            "reflection-task.create",
            input_dto,
            request_id,
            access_token=access_token,
        )
        _validate_task_results(result, request_id, write=True)
        snapshot = result.task.input_snapshot
        requested = input_dto.input_snapshot
        if result.task.sections != input_dto.sections or any(
            getattr(snapshot, name) != getattr(requested, name)
            for name in (
                "session_ids",
                "start_date",
                "end_date",
                "language",
                "language_label",
            )
        ):
            raise invalid_response(request_id, write=True)
        return result

    def start(
        self,
        input_dto: dto.ReflectionTaskLookupDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> dto.ReflectionTaskStartOutputDTO:
        result = self._write(
            "reflection-task.start",
            input_dto,
            request_id,
            access_token=access_token,
        )
        if result.task.task_id != input_dto.task_id:
            raise invalid_response(request_id, write=True)
        return result

    def get(
        self,
        input_dto: dto.ReflectionTaskLookupDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> dto.ReflectionTaskGetOutputDTO:
        result = self._execute(
            "reflection-task.get",
            input_dto,
            request_id,
            access_token=access_token,
        )
        return _validate_task_results(
            result, request_id, task_id=input_dto.task_id
        )

    def latest(
        self,
        input_dto: dto.ReflectionTaskLatestInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> dto.ReflectionTaskLatestOutputDTO:
        return self._execute(
            "reflection-task.latest",
            input_dto,
            request_id,
            access_token=access_token,
        )

    def events(
        self,
        input_dto: dto.ReflectionEventListInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> dto.ReflectionEventListOutputDTO:
        result = self._execute(
            "reflection-task.events",
            input_dto,
            request_id,
            access_token=access_token,
        )
        previous = 0
        for event in result.events:
            if (
                event.task_id != input_dto.task_id
                or event.id
                != dto.reflection_event_id(event.task_id, event.sequence)
                or event.sequence <= previous
            ):
                raise invalid_response(request_id)
            previous = event.sequence
        return result

    def list_reports(
        self,
        input_dto: dto.AnalysisReportListInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> dto.AnalysisReportListOutputDTO:
        return self._execute(
            "analysis-report.list",
            input_dto,
            request_id,
            access_token=access_token,
        )

    def save_report(
        self,
        input_dto: dto.AnalysisReportSaveInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> dto.AnalysisReportSaveOutputDTO:
        return self._write(
            "analysis-report.save",
            input_dto,
            request_id,
            access_token=access_token,
        )


class AdminReflectionsWorkerData(_ReflectionConsumerBase):
    """Service-identity consumer for one task-bound background worker."""

    def _background_write(self, name: str, input_dto, request_id: str):
        return self._write(
            name,
            input_dto,
            request_id,
            task_id=input_dto.task_id,
        )

    def worker_load(
        self, input_dto: dto.ReflectionTaskLookupDTO, request_id: str
    ) -> dto.ReflectionWorkerLoadOutputDTO:
        result = self._background_write(
            "reflection-task.worker-load", input_dto, request_id
        )
        if (
            result.task.task_id != input_dto.task_id
            or result.launch_snapshot.task_id != input_dto.task_id
            or result.launch_snapshot.language
            != result.task.input_snapshot.language
            or [item.section for item in result.launch_snapshot.custom_prompts]
            != result.task.sections
            or result.launch_snapshot.stats.entries
            != len(result.launch_snapshot.sessions)
            or (
                result.task.input_snapshot.session_count is not None
                and result.task.input_snapshot.session_count
                != len(result.launch_snapshot.sessions)
            )
        ):
            raise invalid_response(request_id, write=True)
        return result

    def advance(
        self, input_dto: dto.ReflectionTaskAdvanceInputDTO, request_id: str
    ) -> dto.ReflectionTaskAdvanceOutputDTO:
        return self._background_write(
            "reflection-task.advance", input_dto, request_id
        )

    def begin(
        self, input_dto: dto.ReflectionSectionBeginInputDTO, request_id: str
    ) -> dto.ReflectionSectionBeginOutputDTO:
        result = self._background_write(
            "reflection-section.begin", input_dto, request_id
        )
        if (
            result.section != input_dto.section
            or result.authority.task_id != input_dto.task_id
            or result.authority.section != input_dto.section
        ):
            raise invalid_response(request_id, write=True)
        return result

    def renew_authority(
        self,
        input_dto: dto.ReflectionSectionAuthorityInputDTO,
        request_id: str,
    ) -> dto.ReflectionSectionAuthorityRenewOutputDTO:
        result = self._background_write(
            "reflection-section.authority-renew", input_dto, request_id
        )
        if result.task_id != input_dto.task_id or result.section != input_dto.section:
            raise invalid_response(request_id, write=True)
        return result

    def revoke_authority(
        self,
        input_dto: dto.ReflectionSectionAuthorityInputDTO,
        request_id: str,
    ) -> dto.ReflectionSectionAuthorityRevokeOutputDTO:
        return self._background_write(
            "reflection-section.authority-revoke", input_dto, request_id
        )

    def transcript(
        self,
        input_dto: dto.ReflectionSectionTranscriptInputDTO,
        request_id: str,
    ) -> dto.ReflectionSectionTranscriptOutputDTO:
        result = self._execute(
            "reflection-section.transcript", input_dto, request_id
        )
        if result.section != input_dto.section:
            raise invalid_response(request_id)
        return result

    def finish(
        self, input_dto: dto.ReflectionSectionFinishInputDTO, request_id: str
    ) -> dto.ReflectionSectionFinishOutputDTO:
        result = self._background_write(
            "reflection-section.finish", input_dto, request_id
        )
        if result.section != input_dto.section:
            raise invalid_response(request_id, write=True)
        return result

    def append_event(
        self, input_dto: dto.ReflectionEventAppendInputDTO, request_id: str
    ) -> dto.ReflectionEventAppendOutputDTO:
        result = self._background_write(
            "reflection-event.append", input_dto, request_id
        )
        if result.event_id != input_dto.event_id:
            raise invalid_response(request_id, write=True)
        return result

    def ensure_report(
        self, input_dto: dto.ReflectionTaskLookupDTO, request_id: str
    ) -> dto.ReflectionReportEnsureOutputDTO:
        return self._background_write(
            "reflection-report.ensure", input_dto, request_id
        )


__all__ = [
    "AdminReflectionsData",
    "AdminReflectionsWorkerData",
    "FROZEN_REFLECTION_TASK_CONTRACTS",
    "FROZEN_REFLECTION_TASK_OPERATION_CAPABILITIES",
    "FROZEN_REFLECTION_TASK_SCHEMA_REQUIREMENTS",
    "REFLECTION_TASK_OPERATION_SPECS",
    "REFLECTION_TASK_ADMIN_ARTIFACT_SHA256",
    "REFLECTION_TASK_ADMIN_SOURCE_COMMIT",
    "REFLECTION_TASK_ADMIN_SOURCE_TREE",
    "ReflectionTaskContracts",
    "bind_frozen_reflection_task_contracts",
    "require_reflection_task_capabilities",
]
