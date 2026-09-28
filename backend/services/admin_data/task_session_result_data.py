# [Input] Admin task-result capability, exact operation DTOs and source-claim grants.
# [Output] Typed completion/list/claim/settle consumers and one source turn owner.
# [Pos] Dream data port; Admin owns result state, SQL, claim authorization and receipts.
# [Sync] 2026-09-27: bind independent task completion to a source Thread claim.
# [Sync] 2026-09-28: recover an unknown claim only by replaying its exact original request ID and input.
"""Admin-owned task-result operations consumed by Dream."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_serializer, model_validator

from .chat_models import ChatStrictDTO, validate_timestamp_text
from .client import AdminDataClient, DomainOperation
from .delegation import (
    AdminRuntimeClient,
    DelegationCreateInputDTO,
    DelegationCreatedDTO,
    RuntimeGrant,
    RuntimeHttpConfig,
)
from .errors import AdminDataError, invalid_response
from .gateway_runtime import AdminGatewayRuntime
from .models import CommittedReceiptDTO, OperationCapabilityDTO, SchemaCapabilityDTO
from .session_projection_broker import SessionProjectionBrokerSettings
from .turn_persistence import AdminTurnPersistence
from .workflow_data import AdminWorkflowData, AdminWorkflowResolution

ResultId = Annotated[str, Field(min_length=1, max_length=255)]
Revision = Annotated[int, Field(ge=1, le=9_007_199_254_740_991, strict=True)]
ResultStatus = Literal["pending", "dispatching", "delivered", "failed", "state_unknown"]
ResultError = Literal[
    "TASK_SESSION_RETURN_NOT_SUBMITTED", "TASK_SESSION_RETURN_OWNER_UNKNOWN",
    "TASK_SESSION_RETURN_STATE_UNKNOWN", "TASK_SESSION_RETURN_PERSISTENCE_FAILED",
]


class TaskResultDTO(ChatStrictDTO):
    notification_id: ResultId
    task_id: ResultId
    source_thread_id: ResultId
    target_thread_id: ResultId
    target_turn_id: ResultId
    target_final_message_id: ResultId
    title: str
    final_text: Annotated[str, Field(min_length=1)]
    status: ResultStatus
    revision: Revision
    claim_id: ResultId | None
    source_turn_id: ResultId | None
    source_input_message_id: ResultId | None
    source_final_message_id: ResultId | None
    error_code: ResultError | None
    created_at: str
    updated_at: str

    _timestamps = field_validator("created_at", "updated_at")(validate_timestamp_text)


class TaskResultCommitInputDTO(ChatStrictDTO):
    target_thread_id: ResultId
    target_turn_id: ResultId
    target_final_message_id: ResultId


class TaskResultCommitOutputDTO(ChatStrictDTO):
    result: TaskResultDTO | None


class TaskResultListInputDTO(ChatStrictDTO):
    source_thread_id: ResultId


class TaskResultListOutputDTO(ChatStrictDTO):
    results: list[TaskResultDTO]


class TaskResultClaimInputDTO(ChatStrictDTO):
    notification_id: ResultId
    expected_revision: Revision
    source_turn_id: ResultId


class TaskResultClaimOutputDTO(ChatStrictDTO):
    result: TaskResultDTO
    actor_id: ResultId
    source_session_id: ResultId
    source_input_message_id: ResultId
    source_input_text: Annotated[str, Field(min_length=1)]
    source_persistence_authorization: DelegationCreatedDTO
    source_gateway_authorization: DelegationCreatedDTO


class TaskResultClaimNextInputDTO(ChatStrictDTO):
    pass


class TaskResultClaimNextOutputDTO(ChatStrictDTO):
    claim: TaskResultClaimOutputDTO | None


class TaskResultSettleInputDTO(ChatStrictDTO):
    notification_id: ResultId
    expected_revision: Revision
    claim_id: ResultId
    action: Literal["delivered", "failed", "mark_unknown"]
    error_code: ResultError | None = None

    @model_validator(mode="after")
    def validate_action(self):
        if self.action == "delivered" and self.error_code is not None:
            raise ValueError("Delivered result cannot carry an error")
        if self.action == "failed" and self.error_code != "TASK_SESSION_RETURN_NOT_SUBMITTED":
            raise ValueError("Failed result requires proof that the source turn was not submitted")
        if self.action == "mark_unknown" and self.error_code in (None, "TASK_SESSION_RETURN_NOT_SUBMITTED"):
            raise ValueError("Unknown result requires an uncertainty code")
        return self

    @model_serializer(mode="plain")
    def serialize_action(self):
        value = {
            "notification_id": self.notification_id,
            "expected_revision": self.expected_revision,
            "claim_id": self.claim_id,
            "action": self.action,
        }
        if self.error_code is not None:
            value["error_code"] = self.error_code
        return value


class TaskResultSettleOutputDTO(ChatStrictDTO):
    result: TaskResultDTO


def _operation(name: str, kind: str, user_scope: str | None,
               background_scope: str | None, digest: str, input_dto, output_dto):
    return DomainOperation(
        OperationCapabilityDTO(
            name=name, kind=kind, user_scope=user_scope,
            background_scope=background_scope, input_schema_version=1,
            output_schema_version=1, contract_sha256=digest,
        ), input_dto, output_dto,
    )


COMMIT_TASK_RESULT = _operation(
    "task-session.result-commit", "write", "dream:write", None,
    "eb39e34ca35c9d28719768dc72b70ab7b4f83b2d6ebf34dcfbb347ce67a07e24",
    TaskResultCommitInputDTO, TaskResultCommitOutputDTO,
)
LIST_TASK_RESULTS = _operation(
    "task-session.result-list", "read", "dream:read", None,
    "edbe99f6b6001d8f3684eb8b6881a567bc1b14ef9ae406c5830d61a0bd171f4a",
    TaskResultListInputDTO, TaskResultListOutputDTO,
)
CLAIM_TASK_RESULT = _operation(
    "task-session.result-claim", "write", None, "task-return:dispatch",
    "0da2e968d8b58634ee51dda2f11c14c596ca496a88e72d64dff9bb34cd3fc00d",
    TaskResultClaimInputDTO, TaskResultClaimOutputDTO,
)
CLAIM_NEXT_TASK_RESULT = _operation(
    "task-session.result-claim-next", "write", None, "task-return:dispatch",
    "8d5758403ddd14c90568a4b2e06d14d68150822d6cf675967b5218907d3fd732",
    TaskResultClaimNextInputDTO, TaskResultClaimNextOutputDTO,
)
SETTLE_TASK_RESULT = _operation(
    "task-session.result-settle", "write", None, "task-return:dispatch",
    "9245077bb8d71ba7212eb47b4850e98d3a89a1dc0850466ead4aee2db99f8d4e",
    TaskResultSettleInputDTO, TaskResultSettleOutputDTO,
)
TASK_RESULT_OPERATIONS = (
    COMMIT_TASK_RESULT, LIST_TASK_RESULTS, CLAIM_TASK_RESULT,
    CLAIM_NEXT_TASK_RESULT, SETTLE_TASK_RESULT,
)
TASK_RESULT_SCHEMA_REQUIREMENT = SchemaCapabilityDTO(
    capability="dream.chat-task-result.v1", version=1,
    contract_sha256="9534e484926e69f2f284a4d785b770a5f347d044063a71ab29d08d59d8fa320c",
)


def require_task_result_capability(client: AdminDataClient, request_id: str) -> None:
    snapshot = client.capabilities_snapshot(request_id)
    schemas = {item.capability: item for item in snapshot.schema_capabilities}
    if (len(schemas) != len(snapshot.schema_capabilities)
        or schemas.get(TASK_RESULT_SCHEMA_REQUIREMENT.capability) != TASK_RESULT_SCHEMA_REQUIREMENT):
        raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)


def _execute_recovering(client: AdminDataClient, operation, input_dto, request_id: str,
                        *, access_token: str | None = None):
    try:
        return client.execute(operation, input_dto, request_id, access_token=access_token)
    except AdminDataError as error:
        if not error.outcome_unknown:
            raise
    try:
        receipt = client.receipt(operation, request_id, access_token=access_token)
    except AdminDataError as error:
        raise AdminDataError(error.code, error.status_code, request_id, True, error.details) from None
    if not isinstance(receipt, CommittedReceiptDTO):
        raise AdminDataError("ADMIN_WRITE_RESULT_UNKNOWN", 503, request_id, True)
    return receipt.result


def _claim_recovering(client: AdminDataClient, operation, input_dto, request_id: str):
    """Read the Admin claim's encrypted-grant replay with the original identity.

    A generic operation receipt cannot store the returned bearer tokens. Admin
    fences the same request ID and returns its original claim or an explicit
    unknown terminal; this is never a second source-SDK dispatch.
    """
    try:
        return client.execute(operation, input_dto, request_id)
    except AdminDataError as error:
        if not error.outcome_unknown:
            raise
    try:
        return client.execute(operation, input_dto, request_id)
    except AdminDataError as error:
        raise AdminDataError(error.code, error.status_code, request_id, True, error.details) from None


class AdminTaskResultData:
    """OAuth or exact target-turn delegation operations; no Dream state copies."""

    def __init__(self, client: AdminDataClient) -> None:
        self._client = client

    def commit(self, input_dto: TaskResultCommitInputDTO, request_id: str,
               *, access_token: str) -> TaskResultCommitOutputDTO:
        require_task_result_capability(self._client, request_id)
        result = _execute_recovering(self._client, COMMIT_TASK_RESULT, input_dto,
                                     request_id, access_token=access_token)
        if result.result is not None and (
            result.result.target_thread_id != input_dto.target_thread_id
            or result.result.target_turn_id != input_dto.target_turn_id
            or result.result.target_final_message_id != input_dto.target_final_message_id
        ):
            raise invalid_response(request_id, write=True)
        return result

    def list(self, input_dto: TaskResultListInputDTO, request_id: str,
             *, access_token: str) -> TaskResultListOutputDTO:
        require_task_result_capability(self._client, request_id)
        result = self._client.execute(LIST_TASK_RESULTS, input_dto, request_id,
                                      access_token=access_token)
        if any(item.source_thread_id != input_dto.source_thread_id for item in result.results):
            raise invalid_response(request_id)
        return result


@dataclass(frozen=True, slots=True)
class AdminTaskResultClaim:
    result: TaskResultDTO
    actor_id: str
    source_session_id: str
    source_input_message_id: str
    source_input_text: str
    persistence_grant: RuntimeGrant
    gateway_grant: RuntimeGrant


@dataclass(frozen=True, slots=True)
class AdminTaskResultTurnOwner:
    claim: AdminTaskResultClaim
    workflow: AdminWorkflowResolution
    persistence: AdminTurnPersistence
    gateway_runtime: AdminGatewayRuntime


class AdminTaskResultWorkerData:
    """Service-only claim and settlement for source continuation."""

    def __init__(self, client: AdminDataClient, *, runtime_http_config: RuntimeHttpConfig,
                 session_broker_settings: SessionProjectionBrokerSettings,
                 clock=None) -> None:
        self._client = client
        self._runtime_http_config = runtime_http_config
        self._session_broker_settings = session_broker_settings
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    @property
    def client(self) -> AdminDataClient:
        """Expose the same exact-operation client for source Deck context reads."""
        return self._client

    def claim(self, input_dto: TaskResultClaimInputDTO, request_id: str) -> AdminTaskResultClaim:
        require_task_result_capability(self._client, request_id)
        output = _claim_recovering(self._client, CLAIM_TASK_RESULT, input_dto, request_id)
        return self._validate_claim(output, request_id, expected_input=input_dto)

    def claim_next(self, request_id: str) -> AdminTaskResultClaim | None:
        require_task_result_capability(self._client, request_id)
        output = _claim_recovering(
            self._client, CLAIM_NEXT_TASK_RESULT, TaskResultClaimNextInputDTO(), request_id,
        )
        if output.claim is None:
            return None
        return self._validate_claim(output.claim, request_id)

    def _validate_claim(self, output: TaskResultClaimOutputDTO, request_id: str,
                        *, expected_input: TaskResultClaimInputDTO | None = None) -> AdminTaskResultClaim:
        result = output.result
        if (
            result.status != "dispatching"
            or not result.claim_id
            or not result.source_turn_id
            or (expected_input is not None and (
                result.notification_id != expected_input.notification_id
                or result.revision != expected_input.expected_revision + 1
                or result.source_turn_id != expected_input.source_turn_id
            ))
        ):
            raise invalid_response(request_id, write=True)
        persistence_request = DelegationCreateInputDTO(
            purpose="server-persistence", thread_id=result.source_thread_id,
            run_id=None, editor_session_id=None, scopes=["dream:read", "dream:write"],
        )
        gateway_request = DelegationCreateInputDTO(
            purpose="gateway-cli", thread_id=result.source_thread_id,
            run_id=None, editor_session_id=None,
            scopes=["messages:create", "messages:count_tokens", "models:list"],
        )
        persistence_grant = RuntimeGrant.from_created(
            output.source_persistence_authorization, persistence_request,
            request_id, now=self._clock(),
        )
        gateway_grant = RuntimeGrant.from_created(
            output.source_gateway_authorization, gateway_request,
            request_id, now=self._clock(),
        )
        if output.source_input_message_id != result.source_input_message_id:
            raise invalid_response(request_id, write=True)
        return AdminTaskResultClaim(
            result=result, actor_id=output.actor_id,
            source_session_id=output.source_session_id,
            source_input_message_id=output.source_input_message_id,
            source_input_text=output.source_input_text,
            persistence_grant=persistence_grant, gateway_grant=gateway_grant,
        )

    def turn_owner(self, claim: AdminTaskResultClaim, request_id: str) -> AdminTaskResultTurnOwner:
        workflow = AdminWorkflowData(self._client).resolve(
            claim.result.source_thread_id, request_id,
            access_token=claim.persistence_grant.token,
            canonical_user_id=claim.actor_id,
        )
        persistence = AdminTurnPersistence(
            workflow, claim.persistence_grant, self._client,
            runtime_client_factory=lambda: AdminRuntimeClient(self._runtime_http_config),
            session_broker_settings=self._session_broker_settings,
        )
        gateway_runtime = AdminGatewayRuntime(
            claim.gateway_grant, AdminRuntimeClient(self._runtime_http_config),
        )
        return AdminTaskResultTurnOwner(claim, workflow, persistence, gateway_runtime)

    def settle(self, input_dto: TaskResultSettleInputDTO, request_id: str) -> TaskResultSettleOutputDTO:
        require_task_result_capability(self._client, request_id)
        output = _execute_recovering(self._client, SETTLE_TASK_RESULT, input_dto, request_id)
        if (output.result.notification_id != input_dto.notification_id
            or output.result.claim_id != input_dto.claim_id):
            raise invalid_response(request_id, write=True)
        return output
