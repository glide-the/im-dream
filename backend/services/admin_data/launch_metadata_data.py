# [Input] Registered launch persistence contracts, original source/context seams and current OAuth owner.
# [Output] Typed replay/source/claim/finish/failure consumers with bounded unknown-write recovery.
# [Pos] Dream launch data boundary; Admin owns every SQL statement and database transaction.
# [Sync] 2026-09-16: consume Registry133 and recover writes only through their original receipts.
from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass
from functools import partial
import json
import math
from typing import Annotated, Literal, TYPE_CHECKING
from uuid import uuid4

import anyio
from pydantic import ConfigDict, Field, RootModel, StringConstraints, field_validator, model_validator

from story_workspace.contracts import StoryWorkspaceDreamLaunchCommand, StoryWorkspaceDreamRunContext
from services.story_workspace.dream_launch_application_service import DreamLaunchSource
from .chat_models import ChatStrictDTO, EntityId, PositiveSafeInteger, validate_timestamp_text
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import OperationCapabilityDTO
from .run_data import RunLookupInputDTO
from .workflow_data import require_workflow_capabilities

if TYPE_CHECKING:
    from .request_auth import AdminRequestActor

LaunchIdentifier = Annotated[str, *StoryWorkspaceDreamLaunchCommand.model_fields["deck_id"].metadata]
LaunchGoal = Annotated[str, *StoryWorkspaceDreamLaunchCommand.model_fields["goal"].metadata]
LaunchKey = Annotated[str, *StoryWorkspaceDreamLaunchCommand.model_fields["idempotency_key"].metadata]
UUIDText = Annotated[str, Field(pattern=r"^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|00000000-0000-0000-0000-000000000000|ffffffff-ffff-ffff-ffff-ffffffffffff)$")]
RunId = Annotated[str, Field(pattern=r"^run_[0-9a-f]{32}$")]
ClaimId = Annotated[str, StringConstraints(strip_whitespace=False), Field(pattern=r"^dlc_[0-9a-f]{32}$")]


class LaunchSourceInputDTO(ChatStrictDTO):
    workspace_id: LaunchIdentifier
    deck_id: LaunchIdentifier
    agent_id: LaunchIdentifier | None
    goal: LaunchGoal = Field(repr=False)
    idempotency_key: LaunchKey
    _boundary = field_validator("workspace_id", "deck_id", "agent_id", "goal", "idempotency_key")(StoryWorkspaceDreamLaunchCommand.launch_values_have_no_boundary_whitespace.__func__)


class LaunchSourceDTO(ChatStrictDTO):
    thread_id: UUIDText
    message_id: UUIDText
    message_time: str
    request_fingerprint: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    created: bool
    _time = field_validator("message_time")(validate_timestamp_text)


class LaunchSourceOutputDTO(ChatStrictDTO):
    source: LaunchSourceDTO


class LaunchReplayDTO(ChatStrictDTO):
    workflow_run_id: RunId
    workflow_preflight_id: Annotated[str, Field(pattern=r"^pf_[0-9a-f]{32}$")]
    thread_id: UUIDText
    message_id: UUIDText


class LaunchReplayOutputDTO(ChatStrictDTO):
    replay: LaunchReplayDTO | None


class LaunchContextDTO(ChatStrictDTO):
    model_config = ConfigDict(str_strip_whitespace=True)
    workflow_run_id: RunId
    thread_id: LaunchIdentifier
    deck_id: LaunchIdentifier
    agent_id: LaunchIdentifier | None
    deck_plugin_id: LaunchIdentifier
    deck_plugin_version: LaunchIdentifier
    deck_plugin_binding_id: LaunchIdentifier
    binding_revision: PositiveSafeInteger
    deck_runtime_snapshot_id: LaunchIdentifier
    runtime_plugin_lock_id: LaunchIdentifier

    @model_validator(mode="after")
    def validate_original_context(self):
        StoryWorkspaceDreamRunContext.model_validate(self.model_dump())
        return self


class LaunchClaimInputDTO(RunLookupInputDTO):
    # Only lookup strings inherit the original trim; instruction text stays raw.
    instruction_text: Annotated[EntityId, StringConstraints(strip_whitespace=False)] = Field(repr=False)


class LaunchFinishInputDTO(RunLookupInputDTO):
    claim_id: ClaimId
    accepted: bool


class LaunchFailureInputDTO(RunLookupInputDTO):
    error_code: Annotated[EntityId, StringConstraints(strip_whitespace=False)] = Field(repr=False)


class LaunchFailureOutputDTO(ChatStrictDTO):
    updated: bool
    workflow_run_id: RunId
    thread_id: str | None
    message_id: str | None
    error_code: EntityId = Field(repr=False)


class LaunchUnclaimedDTO(ChatStrictDTO):
    claimed: Literal[False]
    workflow_run_id: RunId
    thread_id: UUIDText
    message_id: UUIDText


class LaunchClaimedDTO(ChatStrictDTO):
    claimed: Literal[True]
    workflow_run_id: RunId
    thread_id: UUIDText
    message_id: UUIDText
    claim_id: ClaimId
    context: LaunchContextDTO
    parts_json: str = Field(repr=False)
    metadata_json: str = Field(repr=False)


class LaunchClaimOutputDTO(RootModel[Annotated[LaunchUnclaimedDTO | LaunchClaimedDTO, Field(discriminator="claimed")]]):
    model_config = ConfigDict(strict=True, frozen=True, hide_input_in_errors=True)

    @model_validator(mode="before")
    @classmethod
    def require_boolean_flag(cls, value):
        if isinstance(value, dict) and type(value.get("claimed")) is not bool:
            raise ValueError("Claim flag must be boolean")
        return value


class LaunchFinishOutputDTO(ChatStrictDTO):
    finished: bool
    workflow_run_id: RunId
    thread_id: UUIDText
    message_id: UUIDText


ENSURE_LAUNCH_SOURCE = DomainOperation(OperationCapabilityDTO(name="dream-launch-source.ensure", kind="write", user_scope="dream:write", background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256="cb498be127a6aca92c9e6e0cde099c9c80cf78ca2486186e9d043457c2263503"), LaunchSourceInputDTO, LaunchSourceOutputDTO)
LOOKUP_LAUNCH_REPLAY = DomainOperation(OperationCapabilityDTO(name="dream-launch-replay.lookup", kind="read", user_scope="dream:read", background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256="af4d06490d6d030d9aa0a3b68460c15813786130a85c5133b438439a3fcb11fb"), LaunchSourceInputDTO, LaunchReplayOutputDTO)
CLAIM_LAUNCH = DomainOperation(OperationCapabilityDTO(name="dream-launch-dispatch.claim", kind="write", user_scope="dream:write", background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256="958549a9bfe4b02d8b31e1e538c81ffad020bb4525a328f542f865b377e8ec43"), LaunchClaimInputDTO, LaunchClaimOutputDTO)
FINISH_LAUNCH = DomainOperation(OperationCapabilityDTO(name="dream-launch-dispatch.finish", kind="write", user_scope="dream:write", background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256="5aa3b738bef5319ee705f5851d83588e1d18dcaf37bdc5789267494fec480f2e"), LaunchFinishInputDTO, LaunchFinishOutputDTO)
FAIL_LAUNCH_ENVELOPE = DomainOperation(OperationCapabilityDTO(name="dream-launch-failure.envelope", kind="write", user_scope="dream:write", background_scope=None,
    input_schema_version=1, output_schema_version=1, contract_sha256="5967ae40f60858553f27f43dd83f021f93928e7c25c582d2e711d68df4d4e042"), LaunchFailureInputDTO, LaunchFailureOutputDTO)
LAUNCH_METADATA_OPERATIONS = (ENSURE_LAUNCH_SOURCE, CLAIM_LAUNCH, FINISH_LAUNCH, FAIL_LAUNCH_ENVELOPE, LOOKUP_LAUNCH_REPLAY)


def _parse_json(value):
    def reject_constant(_constant):
        raise ValueError("JSON contains a nonfinite constant")
    def finite_float(raw):
        parsed = float(raw)
        if not math.isfinite(parsed):
            raise ValueError("JSON contains a nonfinite number")
        return parsed
    return json.loads(value, parse_constant=reject_constant, parse_float=finite_float)


@dataclass(frozen=True, slots=True)
class LaunchSourceExpectation:
    thread_id: str
    message_id: str
    request_fingerprint: str


@dataclass(frozen=True, slots=True)
class LaunchFailureExpectation:
    thread_id: str | None
    message_id: str | None


class AdminLaunchMetadataData:
    def __init__(self, client: AdminDataClient, *, canonical_user_id: str):
        self._client = client
        self._canonical_user_id = canonical_user_id

    def _validate_reply(self, operation, input_dto, result, request_id, *, source=None, context=None, write=False):
        if operation is LOOKUP_LAUNCH_REPLAY:
            return result
        if operation is FAIL_LAUNCH_ENVELOPE:
            valid = isinstance(source, LaunchFailureExpectation) and result.workflow_run_id == input_dto.workflow_run_id
            valid = valid and result.error_code == input_dto.error_code and (result.thread_id, result.message_id) == (source.thread_id, source.message_id)
            valid = valid and (not result.updated or (result.thread_id is not None and result.message_id is not None))
            if not valid:
                raise invalid_response(request_id, write=write)
            return result
        if operation is ENSURE_LAUNCH_SOURCE:
            if source is None or (result.source.thread_id, result.source.message_id, result.source.request_fingerprint) != (source.thread_id, source.message_id, source.request_fingerprint):
                raise invalid_response(request_id, write=write)
            return result
        value = result.root if operation is CLAIM_LAUNCH else result
        if source is None or value.workflow_run_id != input_dto.workflow_run_id or (value.thread_id, value.message_id) != (source.thread_id, source.message_id):
            raise invalid_response(request_id, write=write)
        if operation is CLAIM_LAUNCH and value.claimed:
            if context is None or value.context.model_dump() != context.model_dump() or value.context.thread_id != value.thread_id:
                raise invalid_response(request_id, write=write)
            try:
                parts, metadata = _parse_json(value.parts_json), _parse_json(value.metadata_json)
                valid = parts == [{"type": "text", "text": input_dto.instruction_text}] and isinstance(metadata, dict)
                valid = valid and metadata.get("actorId") == self._canonical_user_id and metadata.get("workspaceId") == input_dto.workspace_id
                valid = valid and metadata.get("workflowRunId") == value.workflow_run_id and metadata.get("threadId") == value.thread_id
                valid = valid and metadata.get("dreamContext") == context.model_dump(mode="json") and metadata.get("dispatchStatus") == "dispatched"
                valid = valid and "dispatchClaimId" not in metadata and "dispatchClaimedAt" not in metadata
            except (ValueError, RecursionError):
                valid = False
            if not valid:
                raise invalid_response(request_id, write=write)
        return result

    def execute(self, operation, input_dto, request_id: str, *, access_token: str, source: DreamLaunchSource | LaunchSourceExpectation | LaunchFailureExpectation | None = None, context: StoryWorkspaceDreamRunContext | None = None):
        if not any(operation is item for item in LAUNCH_METADATA_OPERATIONS):
            raise AdminDataError("ADMIN_OPERATION_CONTRACT_INVALID", 503, request_id)
        require_workflow_capabilities(self._client, request_id)
        result = self._client.execute(operation, input_dto, request_id, access_token=access_token)
        return self._validate_reply(operation, input_dto, result, request_id, source=source, context=context, write=operation.capability.kind == "write")

    def receipt(self, operation, input_dto, request_id: str, *, access_token: str, source: DreamLaunchSource | LaunchSourceExpectation | LaunchFailureExpectation, context: StoryWorkspaceDreamRunContext | None = None):
        if not any(operation is item for item in LAUNCH_METADATA_OPERATIONS):
            raise AdminDataError("ADMIN_OPERATION_CONTRACT_INVALID", 503, request_id)
        if type(input_dto) is not operation.input_dto:
            raise AdminDataError("ADMIN_OPERATION_INPUT_INVALID", 400, request_id)
        require_workflow_capabilities(self._client, request_id)
        result = self._client.receipt(operation, request_id, access_token=access_token)
        if result.status == "committed":
            self._validate_reply(operation, input_dto, result.result, request_id, source=source, context=context)
        return result

    def execute_recovering(self, operation, input_dto, request_id: str, *, access_token: str,
        source: DreamLaunchSource | LaunchSourceExpectation | LaunchFailureExpectation, context: StoryWorkspaceDreamRunContext | None = None):
        if operation.capability.kind != "write":
            raise AdminDataError("ADMIN_OPERATION_CONTRACT_INVALID", 503, request_id)
        try:
            return self.execute(operation, input_dto, request_id, access_token=access_token, source=source, context=context)
        except AdminDataError as error:
            if not error.outcome_unknown:
                raise
            receipt = self.receipt(operation, input_dto, request_id, access_token=access_token, source=source, context=context)
            if receipt.status == "committed":
                return self._validate_reply(operation, input_dto, receipt.result, request_id, source=source, context=context)
            raise error


class AdminLaunchSourceRepository:
    """Original application seam; only a server-authenticated actor can compose it."""

    def __init__(self, client: AdminDataClient, *, actor: AdminRequestActor):
        from .request_auth import AdminRequestActor
        if not isinstance(actor, AdminRequestActor) or "dream:write" not in actor.scopes:
            raise AdminDataError("DREAM_SCOPE_REQUIRED", 403)
        self._actor = actor
        self._data = AdminLaunchMetadataData(client, canonical_user_id=actor.canonical_user_id)

    async def ensure_source(self, *, actor_id: str, workspace_id: str, deck_id: str, agent_id: str | None,
        goal: str, idempotency_key: str, request_fingerprint: str, thread_id: str, message_id: str) -> DreamLaunchSource:
        request_id = str(uuid4())
        if actor_id != self._actor.canonical_user_id:
            raise AdminDataError("DREAM_SCOPE_REQUIRED", 403, request_id)
        input_dto = LaunchSourceInputDTO(workspace_id=workspace_id, deck_id=deck_id, agent_id=agent_id, goal=goal, idempotency_key=idempotency_key)
        # The original application supplied these expected facts before this seam.
        expected = LaunchSourceExpectation(thread_id, message_id, request_fingerprint)
        result = await anyio.to_thread.run_sync(partial(self._data.execute_recovering, ENSURE_LAUNCH_SOURCE, input_dto, request_id,
            access_token=self._actor.access_token, source=expected))
        wire = result.source
        return DreamLaunchSource(wire.thread_id, wire.message_id, datetime.fromisoformat(wire.message_time.replace("Z", "+00:00")), wire.request_fingerprint, wire.created)
