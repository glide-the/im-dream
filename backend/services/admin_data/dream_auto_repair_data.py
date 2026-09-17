# [Input] Admin Registry169 descriptor, immutable repair identity and exact turn grant.
# [Output] Strict automatic-repair settlement DTOs and original-receipt validation.
# [Pos] Dream consumer boundary; Admin alone owns the message ORM row and transaction.
# [Sync] 2026-09-16: replace Dream SQL settlement with one typed Admin operation.
"""Typed Registry169 consumer for automatic-repair message settlement."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import OperationCapabilityDTO, StrictDTO
from .workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS


RepairEntityId = Annotated[str, Field(min_length=1, max_length=512)]
ProjectSlug = Annotated[
    str,
    Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"),
]
DreamAutoRepairTerminalStatus = Literal["dispatched", "failed"]


class DreamAutoRepairProjectCleanupDTO(StrictDTO):
    trusted_project_slug: ProjectSlug
    stale_project_slugs: Annotated[list[ProjectSlug], Field(min_length=1)]

    @model_validator(mode="after")
    def require_distinct_stale_projects(self):
        if (
            len(set(self.stale_project_slugs)) != len(self.stale_project_slugs)
            or self.trusted_project_slug in self.stale_project_slugs
        ):
            raise ValueError("Project cleanup scope is invalid")
        return self


class DreamAutoRepairIdentityDTO(StrictDTO):
    kind: Literal["story-workspace-dream-auto-repair"]
    schema_version: Literal["story-workspace-dream-auto-repair/v1"]
    originating_message_id: RepairEntityId
    originating_turn_id: RepairEntityId
    workflow_run_id: Annotated[str, Field(pattern=r"^run_[0-9a-f]{32}$")]
    repair_attempt: Literal[1]
    validation_code: Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{0,63}$")]
    idempotency_key: Annotated[
        str,
        Field(pattern=r"^dream-auto-repair/v1:[0-9a-f]{64}$"),
    ]
    project_cleanup: DreamAutoRepairProjectCleanupDTO | None


class DreamAutoRepairSettleInputDTO(StrictDTO):
    thread_id: RepairEntityId
    message_id: RepairEntityId
    expected_identity: DreamAutoRepairIdentityDTO
    status: DreamAutoRepairTerminalStatus


class DreamAutoRepairSettleOutputDTO(StrictDTO):
    message_id: RepairEntityId
    status: DreamAutoRepairTerminalStatus
    changed: bool


SETTLE_DREAM_AUTO_REPAIR = DomainOperation(
    OperationCapabilityDTO(
        name="dream-auto-repair.settle",
        kind="write",
        user_scope="dream:write",
        background_scope=None,
        input_schema_version=1,
        output_schema_version=1,
        contract_sha256=(
            "155adcb6995b63e090cbc2906383ba4b"
            "78525c1f268a430ad6f2ba449b66b159"
        ),
    ),
    DreamAutoRepairSettleInputDTO,
    DreamAutoRepairSettleOutputDTO,
)
DREAM_AUTO_REPAIR_OPERATIONS = (SETTLE_DREAM_AUTO_REPAIR,)


def require_dream_auto_repair_capabilities(
    client: AdminDataClient,
    request_id: str,
) -> None:
    capabilities = client.capabilities(request_id)
    schemas = {
        item.capability: item for item in capabilities.schema_capabilities
    }
    if (
        len(schemas) != len(capabilities.schema_capabilities)
        or any(
            schemas.get(item.capability) != item
            for item in WORKFLOW_SCHEMA_REQUIREMENTS
        )
    ):
        raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)


class AdminDreamAutoRepairProvider:
    """Marker for the exact turn owner allowed to settle a repair message."""

    def settle_dream_auto_repair(
        self,
        *,
        actor_id: str,
        thread_id: str,
        message_id: str,
        expected_identity: DreamAutoRepairIdentityDTO,
        status: DreamAutoRepairTerminalStatus,
    ) -> DreamAutoRepairSettleOutputDTO:
        raise NotImplementedError


class AdminDreamAutoRepairData:
    def __init__(self, client: AdminDataClient) -> None:
        self._client = client

    @staticmethod
    def validate_reply(
        input_dto: DreamAutoRepairSettleInputDTO,
        result: DreamAutoRepairSettleOutputDTO,
        request_id: str,
        *,
        write: bool,
    ) -> DreamAutoRepairSettleOutputDTO:
        if (
            result.message_id != input_dto.message_id
            or result.status != input_dto.status
        ):
            raise invalid_response(request_id, write=write)
        return result

    def settle(
        self,
        input_dto: DreamAutoRepairSettleInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> DreamAutoRepairSettleOutputDTO:
        if type(input_dto) is not DreamAutoRepairSettleInputDTO:
            raise AdminDataError("ADMIN_OPERATION_INPUT_INVALID", 400, request_id)
        require_dream_auto_repair_capabilities(self._client, request_id)
        result = self._client.execute(
            SETTLE_DREAM_AUTO_REPAIR,
            input_dto,
            request_id,
            access_token=access_token,
        )
        return self.validate_reply(input_dto, result, request_id, write=True)

    def receipt(
        self,
        input_dto: DreamAutoRepairSettleInputDTO,
        request_id: str,
        *,
        access_token: str,
    ):
        if type(input_dto) is not DreamAutoRepairSettleInputDTO:
            raise AdminDataError("ADMIN_OPERATION_INPUT_INVALID", 400, request_id)
        require_dream_auto_repair_capabilities(self._client, request_id)
        result = self._client.receipt(
            SETTLE_DREAM_AUTO_REPAIR,
            request_id,
            access_token=access_token,
        )
        if result.status == "committed":
            self.validate_reply(input_dto, result.result, request_id, write=True)
        return result


__all__ = [
    "AdminDreamAutoRepairData",
    "AdminDreamAutoRepairProvider",
    "DREAM_AUTO_REPAIR_OPERATIONS",
    "DreamAutoRepairIdentityDTO",
    "DreamAutoRepairProjectCleanupDTO",
    "DreamAutoRepairSettleInputDTO",
    "DreamAutoRepairSettleOutputDTO",
    "DreamAutoRepairTerminalStatus",
    "SETTLE_DREAM_AUTO_REPAIR",
]
