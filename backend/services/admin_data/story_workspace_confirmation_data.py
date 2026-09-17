# [Sync] 2026-09-17: reuse the validated immutable Admin capability snapshot instead of repeating discovery per domain call.
# [Input] Admin Registry120/121 contracts, OAuth bearer or service-only claim identity.
# [Output] Strict confirmation DTO consumers plus a claim-bound Admin turn owner.
# [Pos] Dream data port; PostgreSQL, ORM, lifecycle, permissions and durable claims stay in Admin.
# [Sync] 2026-09-16: bind confirmation Runtime to a Registry121 server-persistence grant.
"""Typed Registry120 consumer for Story Workspace confirmation persistence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from .chat_models import ChatStrictDTO
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError, invalid_response
from .models import (
    CanonicalUserId,
    CommittedReceiptDTO,
    Identifier,
    OperationCapabilityDTO,
    SchemaCapabilityDTO,
)
from .workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS
from .workflow_data import AdminWorkflowData, AdminWorkflowResolution
from .deck_chat_context_data import (
    AdminDeckChatContextData,
    AdminDeckChatContextResolution,
    DeckChatContextInputDTO,
)
from .delegation import (
    AdminRuntimeClient,
    DelegationCreatedDTO,
    DelegationCreateInputDTO,
    RuntimeGrant,
    RuntimeHttpConfig,
)
from .session_projection_broker import SessionProjectionBrokerSettings
from .turn_persistence import AdminTurnPersistence

RunId = Annotated[str, Field(pattern=r"^run_[0-9a-f]{32}$")]
MessageId = Annotated[str, Field(pattern=r"^dream_confirm_[0-9a-f]{64}$")]
Hash = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


class StoryWorkspaceConfirmationSubmitInputDTO(ChatStrictDTO):
    command_json: Annotated[str, Field(min_length=1)]


class StoryWorkspaceConfirmationFactInputDTO(ChatStrictDTO):
    workflow_run_id: RunId


class StoryWorkspaceConfirmationClaimInputDTO(ChatStrictDTO):
    message_id: MessageId | None
    claim_id: Identifier


class StoryWorkspaceConfirmationLeaseInputDTO(ChatStrictDTO):
    message_id: MessageId
    claim_id: Identifier
    duration_seconds: Annotated[float, Field(ge=0, allow_inf_nan=False, strict=True)] | None


class StoryWorkspaceConfirmationAckInputDTO(ChatStrictDTO):
    message_id: MessageId
    claim_id: Identifier


class StoryWorkspaceConfirmationMetadataDTO(ChatStrictDTO):
    kind: Literal["story-workspace-dream-confirmation"]
    actor: CanonicalUserId
    story_workspace_run_id: RunId
    thread_id: Annotated[str, Field(min_length=1, max_length=255)]
    base_revisions: dict[Literal["characters", "scenes", "storyboards"], Annotated[int, Field(gt=0, strict=True)]]
    edit_count: Annotated[int, Field(ge=0, strict=True)]
    command_fingerprint: Hash
    idempotency_key: Annotated[str, Field(pattern=r"^swc_[A-Za-z0-9._:-]+$", min_length=5, max_length=255)]
    request_id: Identifier
    dispatch_status: Literal["pending", "dispatching", "dispatched"]
    dispatch_claim_id: Identifier | None = None
    dispatch_claim_lease_until: Annotated[float, Field(ge=0, allow_inf_nan=False, strict=True)] | None = None
    dispatch_ack_claim_sha256: Hash | None = None

    @field_validator("base_revisions")
    @classmethod
    def exact_stages(cls, value):
        if set(value) != {"characters", "scenes", "storyboards"}:
            raise ValueError("All confirmation stage revisions are required")
        return value

    @model_validator(mode="after")
    def valid_claim_state(self):
        claiming = self.dispatch_status == "dispatching"
        if claiming != (
            self.dispatch_claim_id is not None
            and self.dispatch_claim_lease_until is not None
        ):
            raise ValueError("Dispatching requires one complete claim")
        if (self.dispatch_status == "dispatched") != (
            self.dispatch_ack_claim_sha256 is not None
        ):
            raise ValueError("Dispatched requires one acknowledgement hash")
        return self


class StoryWorkspaceConfirmationDispatchDTO(ChatStrictDTO):
    thread_id: Annotated[str, Field(min_length=1, max_length=255)]
    actor_id: CanonicalUserId
    message_id: MessageId
    parts_json: Annotated[str, Field(min_length=1)]
    metadata_json: Annotated[str, Field(min_length=1)]


class StoryWorkspaceConfirmationSubmitOutputDTO(ChatStrictDTO):
    message_id: MessageId
    story_workspace_run_id: RunId
    thread_id: Annotated[str, Field(min_length=1, max_length=255)]
    status: Literal["accepted"]
    replayed: bool
    dispatched: bool
    request_id: Identifier
    dispatch: StoryWorkspaceConfirmationDispatchDTO | None


class StoryWorkspaceConfirmationFactOutputDTO(ChatStrictDTO):
    workflow_run_id: RunId
    thread_id: Annotated[str, Field(min_length=1, max_length=255)]
    confirmation_accepted: bool
    confirmation_dispatched: bool

    @model_validator(mode="after")
    def dispatched_requires_accepted(self):
        if self.confirmation_dispatched and not self.confirmation_accepted:
            raise ValueError("Dispatched confirmation must be accepted")
        return self


class StoryWorkspaceConfirmationClaimOutputDTO(ChatStrictDTO):
    dispatch: StoryWorkspaceConfirmationDispatchDTO | None


class StoryWorkspaceConfirmationClaimTurnOutputDTO(ChatStrictDTO):
    dispatch: StoryWorkspaceConfirmationDispatchDTO | None
    authority: DelegationCreatedDTO | None

    @model_validator(mode="after")
    def authority_matches_dispatch(self):
        if (self.dispatch is None) != (self.authority is None):
            raise ValueError("Dispatch and authority must be present together")
        return self


class StoryWorkspaceConfirmationLeaseOutputDTO(ChatStrictDTO):
    renewed: bool
    lease_until: Annotated[float, Field(ge=0, allow_inf_nan=False, strict=True)] | None


class StoryWorkspaceConfirmationAckOutputDTO(ChatStrictDTO):
    acked: bool


def _operation(name, kind, user_scope, background_scope, digest, input_dto, output_dto):
    return DomainOperation(
        OperationCapabilityDTO(
            name=name,
            kind=kind,
            user_scope=user_scope,
            background_scope=background_scope,
            input_schema_version=1,
            output_schema_version=1,
            contract_sha256=digest,
        ),
        input_dto,
        output_dto,
    )


SUBMIT_STORY_WORKSPACE_CONFIRMATION = _operation(
    "story-workspace-confirmation.submit", "write", "dream:write", None,
    "2571aa2cc9c19656c4ac90d33221da65e8a631657adebf9f535ab0fe3c76bb12",
    StoryWorkspaceConfirmationSubmitInputDTO, StoryWorkspaceConfirmationSubmitOutputDTO,
)
READ_STORY_WORKSPACE_CONFIRMATION_FACT = _operation(
    "story-workspace-confirmation.fact", "read", "dream:read", None,
    "f455a6075161751d25a229dd64479e2a6d6ca781ea7aacfa5575ec4561f52beb",
    StoryWorkspaceConfirmationFactInputDTO, StoryWorkspaceConfirmationFactOutputDTO,
)
CLAIM_STORY_WORKSPACE_CONFIRMATION = _operation(
    "story-workspace-confirmation.claim", "write", None, "story-confirmation:dispatch",
    "c049317c4383584a7574b11daea1b8c626875d589e0dbbd45dfb739c4ca8cde1",
    StoryWorkspaceConfirmationClaimInputDTO, StoryWorkspaceConfirmationClaimOutputDTO,
)
CLAIM_STORY_WORKSPACE_CONFIRMATION_TURN = _operation(
    "story-workspace-confirmation.claim-turn", "write", None, "story-confirmation:dispatch",
    "c971b5f2ee3517eb9c078d70544bfaa46d74a293afc44b1b8386496d9d081e62",
    StoryWorkspaceConfirmationClaimInputDTO, StoryWorkspaceConfirmationClaimTurnOutputDTO,
)
LEASE_STORY_WORKSPACE_CONFIRMATION = _operation(
    "story-workspace-confirmation.lease", "write", None, "story-confirmation:dispatch",
    "a5720992e5a0cbc39773481dd3f98a32e6b535c34ea24df230de6ad5646817e6",
    StoryWorkspaceConfirmationLeaseInputDTO, StoryWorkspaceConfirmationLeaseOutputDTO,
)
ACK_STORY_WORKSPACE_CONFIRMATION = _operation(
    "story-workspace-confirmation.ack", "write", None, "story-confirmation:dispatch",
    "12aeed9beb6584354aa584ebadf7ce352d68084632c0d2c90a2c768c3a8626c6",
    StoryWorkspaceConfirmationAckInputDTO, StoryWorkspaceConfirmationAckOutputDTO,
)
STORY_WORKSPACE_CONFIRMATION_OPERATIONS = (
    SUBMIT_STORY_WORKSPACE_CONFIRMATION,
    READ_STORY_WORKSPACE_CONFIRMATION_FACT,
    CLAIM_STORY_WORKSPACE_CONFIRMATION,
    CLAIM_STORY_WORKSPACE_CONFIRMATION_TURN,
    LEASE_STORY_WORKSPACE_CONFIRMATION,
    ACK_STORY_WORKSPACE_CONFIRMATION,
)


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True)


def canonical_confirmation_command(command: object) -> str:
    if hasattr(command, "model_dump"):
        command = command.model_dump(mode="json", by_alias=True)
    return _canonical(command)


def _expected_identity(actor_id: str, command_json: str):
    try:
        command = json.loads(command_json, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        run_id = command["storyWorkspaceRunId"]
        thread_id = command["threadId"]
        key = command["idempotencyKey"]
    except (KeyError, TypeError, ValueError):
        raise ValueError("Invalid confirmation command") from None
    fingerprint = "sha256:" + hashlib.sha256(_canonical({"actor": actor_id, "command": command}).encode()).hexdigest()
    message_id = "dream_confirm_" + hashlib.sha256(_canonical({
        "actor": actor_id, "storyWorkspaceRunId": run_id, "idempotencyKey": key,
    }).encode()).hexdigest()
    return command, run_id, thread_id, key, fingerprint, message_id


def _validate_dispatch(dispatch: StoryWorkspaceConfirmationDispatchDTO, request_id: str,
                       *, expected_actor: str | None = None,
                       expected_command_json: str | None = None):
    try:
        metadata = StoryWorkspaceConfirmationMetadataDTO.model_validate_json(dispatch.metadata_json)
        parts = json.loads(dispatch.parts_json)
        if not isinstance(parts, list) or len(parts) != 1 or not isinstance(parts[0], dict):
            raise ValueError("Invalid parts")
        text = parts[0].get("text") if parts[0].get("type") == "text" else None
        envelope = json.loads(text) if isinstance(text, str) else None
        command = envelope.get("command") if isinstance(envelope, dict) else None
        if not isinstance(command, dict) or envelope.get("kind") != "story-workspace-dream-confirmation":
            raise ValueError("Invalid envelope")
        command_json = _canonical(command)
        actor = expected_actor or dispatch.actor_id
        _, run_id, thread_id, key, fingerprint, message_id = _expected_identity(actor, command_json)
        if expected_command_json is not None and command_json != expected_command_json:
            raise ValueError("Command mismatch")
        if (
            dispatch.actor_id != actor
            or dispatch.message_id != message_id
            or dispatch.thread_id != thread_id
            or metadata.actor != actor
            or metadata.thread_id != thread_id
            or metadata.story_workspace_run_id != run_id
            or metadata.idempotency_key != key
            or metadata.command_fingerprint != fingerprint
        ):
            raise ValueError("Confirmation identity mismatch")
    except (TypeError, ValueError):
        raise invalid_response(request_id, write=True) from None
    return metadata


def _ensure_capabilities(client: AdminDataClient, request_id: str) -> None:
    capabilities = None
    if not client.capabilities_ready:
        capabilities = client.capabilities_snapshot(request_id)
    if capabilities is not None:
        schemas = {item.capability: item for item in capabilities.schema_capabilities}
        if len(schemas) != len(capabilities.schema_capabilities) or any(
            schemas.get(item.capability) != item for item in WORKFLOW_SCHEMA_REQUIREMENTS
        ):
            raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)


CONFIRMATION_TURN_SCHEMA_REQUIREMENT = SchemaCapabilityDTO(
    capability="identity.runtime-confirmation-claim.v1",
    version=1,
    contract_sha256="d9de67655e6d8d5ae9654d6502a2cf5d9ab1bb6d829975b243eb25e239b08919",
)


def _ensure_turn_capability(client: AdminDataClient, request_id: str) -> None:
    capabilities = client.capabilities_snapshot(request_id)
    schemas = {item.capability: item for item in capabilities.schema_capabilities}
    if (
        len(schemas) != len(capabilities.schema_capabilities)
        or any(
            schemas.get(item.capability) != item
            for item in (
                *WORKFLOW_SCHEMA_REQUIREMENTS,
                CONFIRMATION_TURN_SCHEMA_REQUIREMENT,
            )
        )
    ):
        raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)


class AdminStoryWorkspaceConfirmationData:
    def __init__(self, client: AdminDataClient, *, canonical_user_id: str) -> None:
        self._client = client
        self._canonical_user_id = canonical_user_id

    def submit_recovering(self, input_dto: StoryWorkspaceConfirmationSubmitInputDTO,
                          request_id: str, *, access_token: str):
        _ensure_capabilities(self._client, request_id)
        try:
            result = self._client.execute(SUBMIT_STORY_WORKSPACE_CONFIRMATION, input_dto, request_id, access_token=access_token)
        except AdminDataError as error:
            if not error.outcome_unknown:
                raise
            try:
                receipt = self._client.receipt(SUBMIT_STORY_WORKSPACE_CONFIRMATION, request_id, access_token=access_token)
            except AdminDataError as receipt_error:
                raise AdminDataError(receipt_error.code, receipt_error.status_code, request_id, True, receipt_error.details) from None
            if not isinstance(receipt, CommittedReceiptDTO):
                raise AdminDataError("ADMIN_WRITE_RESULT_UNKNOWN", 503, request_id, True)
            result = receipt.result
        try:
            command_json = _canonical(json.loads(input_dto.command_json))
            _, run_id, thread_id, _, _, message_id = _expected_identity(self._canonical_user_id, command_json)
            if result.message_id != message_id or result.story_workspace_run_id != run_id or result.thread_id != thread_id:
                raise ValueError("Result identity mismatch")
            if result.dispatch is not None:
                metadata = _validate_dispatch(result.dispatch, request_id, expected_actor=self._canonical_user_id,
                                              expected_command_json=command_json)
                if metadata.request_id != result.request_id or metadata.dispatch_status != "pending":
                    raise ValueError("Result dispatch mismatch")
            elif not result.replayed and not result.dispatched:
                raise ValueError("New pending result requires dispatch")
            return result
        except (TypeError, ValueError):
            raise invalid_response(request_id, write=True) from None

    def fact(self, input_dto: StoryWorkspaceConfirmationFactInputDTO, request_id: str, *, access_token: str):
        _ensure_capabilities(self._client, request_id)
        result = self._client.execute(READ_STORY_WORKSPACE_CONFIRMATION_FACT, input_dto, request_id, access_token=access_token)
        if result.workflow_run_id != input_dto.workflow_run_id:
            raise invalid_response(request_id)
        return result


class AdminStoryWorkspaceConfirmationWorkerData:
    def __init__(
        self,
        client: AdminDataClient,
        *,
        runtime_http_config: RuntimeHttpConfig | None = None,
        session_broker_settings: SessionProjectionBrokerSettings | None = None,
        clock=None,
    ) -> None:
        self._client = client
        self._runtime_http_config = runtime_http_config
        self._session_broker_settings = session_broker_settings
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _execute_recovering(self, operation, input_dto, request_id: str):
        _ensure_capabilities(self._client, request_id)
        try:
            return self._client.execute(operation, input_dto, request_id)
        except AdminDataError as error:
            if not error.outcome_unknown:
                raise
        # All three background commands bind an exact claim ID. Repeating the
        # same DTO is their defined unknown-result recovery, never a new action.
        return self._client.execute(operation, input_dto, request_id)

    def claim(self, input_dto: StoryWorkspaceConfirmationClaimInputDTO, request_id: str):
        result = self._execute_recovering(CLAIM_STORY_WORKSPACE_CONFIRMATION, input_dto, request_id)
        if result.dispatch is not None:
            metadata = _validate_dispatch(result.dispatch, request_id)
            if metadata.dispatch_status != "dispatching" or metadata.dispatch_claim_id != input_dto.claim_id:
                raise invalid_response(request_id, write=True)
        return result

    def claim_turn(
        self, input_dto: StoryWorkspaceConfirmationClaimInputDTO, request_id: str
    ) -> "AdminStoryWorkspaceConfirmationTurnClaim | None":
        _ensure_turn_capability(self._client, request_id)
        result = self._execute_recovering(
            CLAIM_STORY_WORKSPACE_CONFIRMATION_TURN, input_dto, request_id
        )
        if result.dispatch is None or result.authority is None:
            if result.dispatch is not None or result.authority is not None:
                raise invalid_response(request_id, write=True)
            return None
        metadata = _validate_dispatch(result.dispatch, request_id)
        if (
            metadata.dispatch_status != "dispatching"
            or metadata.dispatch_claim_id != input_dto.claim_id
        ):
            raise invalid_response(request_id, write=True)
        requested = DelegationCreateInputDTO(
            purpose="server-persistence",
            thread_id=result.dispatch.thread_id,
            run_id=metadata.story_workspace_run_id,
            editor_session_id=None,
            scopes=["dream:read", "dream:write"],
        )
        grant = RuntimeGrant.from_created(
            result.authority,
            requested,
            request_id,
            now=self._clock(),
        )
        return AdminStoryWorkspaceConfirmationTurnClaim(
            dispatch=result.dispatch,
            grant=grant,
        )

    def turn_owner(
        self,
        claim: "AdminStoryWorkspaceConfirmationTurnClaim",
        request_id: str,
    ) -> "AdminStoryWorkspaceConfirmationTurnOwner":
        if (
            self._runtime_http_config is None
            or self._session_broker_settings is None
        ):
            raise AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503, request_id)
        metadata = _validate_dispatch(claim.dispatch, request_id)
        actor_id = claim.dispatch.actor_id
        workflow = AdminWorkflowData(self._client).resolve(
            claim.dispatch.thread_id,
            request_id,
            access_token=claim.grant.token,
            canonical_user_id=actor_id,
        )
        context = workflow.context_for(
            actor_id=actor_id,
            thread_id=claim.dispatch.thread_id,
        )
        if (
            context is None
            or context.workflow_run_id != metadata.story_workspace_run_id
        ):
            raise invalid_response(request_id)
        deck = AdminDeckChatContextData(
            self._client,
            canonical_user_id=actor_id,
        ).resolve(
            DeckChatContextInputDTO(
                deck_id=context.deck_id,
                voice_id=context.agent_id,
            ),
            request_id,
            access_token=claim.grant.token,
        )
        persistence = AdminTurnPersistence(
            workflow,
            claim.grant,
            self._client,
            runtime_client_factory=lambda: AdminRuntimeClient(
                self._runtime_http_config
            ),
            session_broker_settings=self._session_broker_settings,
        )
        return AdminStoryWorkspaceConfirmationTurnOwner(
            persistence=persistence,
            workflow=workflow,
            deck=deck,
        )

    def lease(self, input_dto: StoryWorkspaceConfirmationLeaseInputDTO, request_id: str):
        return self._execute_recovering(LEASE_STORY_WORKSPACE_CONFIRMATION, input_dto, request_id)

    def ack(self, input_dto: StoryWorkspaceConfirmationAckInputDTO, request_id: str):
        return self._execute_recovering(ACK_STORY_WORKSPACE_CONFIRMATION, input_dto, request_id)


@dataclass(frozen=True, slots=True)
class AdminStoryWorkspaceConfirmationTurnClaim:
    dispatch: StoryWorkspaceConfirmationDispatchDTO
    grant: RuntimeGrant


@dataclass(frozen=True, slots=True)
class AdminStoryWorkspaceConfirmationTurnOwner:
    persistence: AdminTurnPersistence
    workflow: AdminWorkflowResolution
    deck: AdminDeckChatContextResolution
