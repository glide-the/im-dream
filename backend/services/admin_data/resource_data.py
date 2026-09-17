# [Input] Frozen Admin resource operation contracts, service identity and existing diagnostics DTO.
# [Output] Typed HTTP desired-policy reader and serialized observer writer with receipt recovery.
# [Pos] Admin resource domain consumer; composition root owns its lifetime, never the Agent turn.
# [Sync] 2026-09-14: consume real input/output contract hashes and retain unknown writes by original ID.
# [Sync] 2026-09-15: serialize policy reads, observer writes and final close; closed owners cannot reopen.
"""Resource-domain adapter; no SQL, remote UOW, user impersonation or automatic replay."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from threading import Lock
from uuid import UUID, uuid4

from pydantic import field_validator, model_validator

from claude_agent.resource_diagnostics import ClaudeAgentResourceDiagnosticsDTO
from .client import AdminDataClient, DomainOperation
from .config import AdminDataConfig
from .errors import AdminDataError
from .models import AbsentReceiptDTO, OperationCapabilityDTO, StrictDTO
from .resource_models import ResourcePolicyReadInputDTO, ResourcePolicyReadOutputDTO, ResourcePolicyReadResultDTO


class ResourceObserverPublishInputDTO(StrictDTO):
    instance_id: UUID
    process_started_at: datetime
    sampled_at: datetime | None
    snapshot: ClaudeAgentResourceDiagnosticsDTO

    @field_validator("process_started_at", "sampled_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Timestamp must have a timezone")
        return value

    @model_validator(mode="after")
    def require_matching_sample(self) -> ResourceObserverPublishInputDTO:
        payload = self.model_dump(mode="json")
        if payload["sampled_at"] != payload["snapshot"]["sample"]["sampled_at"]:
            raise ValueError("Sample timestamp must match diagnostics")
        return self


class ResourceObserverPublishOutputDTO(StrictDTO):
    accepted: bool
    heartbeat_at: datetime
    sampled_at: datetime | None

    @field_validator("accepted")
    @classmethod
    def require_accepted(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("Observer write was not accepted")
        return value

    @field_validator("heartbeat_at", "sampled_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Timestamp must have a timezone")
        return value


# Exact candidates supplied by Admin's admin-dream-operation-contracts.json.
# Advertisement must match before dispatch; these pins do not claim publication.
RESOURCE_POLICY_READ = DomainOperation(
    OperationCapabilityDTO(name="resource-policy.read", kind="read", user_scope=None,
        background_scope="resource-policy:read", input_schema_version=1, output_schema_version=1,
        contract_sha256="1559c28cd5fbfbbf1b01a35fe6853ba5ccec2f26f45a428ac26ce22d005b3c78"),
    ResourcePolicyReadInputDTO, ResourcePolicyReadResultDTO,
)
RESOURCE_OBSERVER_PUBLISH = DomainOperation(
    OperationCapabilityDTO(name="resource-observer.publish", kind="write", user_scope=None,
        background_scope="resource-observer:write", input_schema_version=1, output_schema_version=1,
        contract_sha256="409dfce5218c0471d9612016305698bba7388eb8d37c34be40b50b10488c1114"),
    ResourceObserverPublishInputDTO, ResourceObserverPublishOutputDTO,
)
RESOURCE_OPERATIONS = (RESOURCE_POLICY_READ, RESOURCE_OBSERVER_PUBLISH)


@dataclass(frozen=True)
class _PendingObserverWrite:
    request_id: str
    input_sha256: str


class AdminResourceData:
    def __init__(self, client: AdminDataClient | None = None) -> None:
        self._client = client
        self._client_lock = Lock()
        self._writer_lock = Lock()
        self._closed = False
        self._pending: _PendingObserverWrite | None = None

    def _get_client(self) -> AdminDataClient:
        with self._client_lock:
            if self._closed:
                raise AdminDataError("ADMIN_CONFIGURATION_INVALID", 503)
            if self._client is None:
                self._client = AdminDataClient(AdminDataConfig.from_env(), operations=RESOURCE_OPERATIONS)
            return self._client

    def close(self) -> None:
        # Drain dispatched background requests before closing their transport.
        with self._writer_lock:
            with self._client_lock:
                if self._closed:
                    return
                self._closed = True
                if self._client is not None:
                    self._client.close()

    def read_policy(self) -> ResourcePolicyReadOutputDTO:
        with self._writer_lock:
            client = self._get_client()
            client.capabilities(str(uuid4()))
            return client.execute(RESOURCE_POLICY_READ, ResourcePolicyReadInputDTO(), str(uuid4())).root

    def publish_observer(self, request_id: str, input_dto: ResourceObserverPublishInputDTO) -> None:
        # Only background I/O/shutdown enters this lock; submit and Agent turns never wait.
        with self._writer_lock:
            client = self._get_client()
            if self._pending is not None:
                receipt = client.receipt(RESOURCE_OBSERVER_PUBLISH, self._pending.request_id)
                if isinstance(receipt, AbsentReceiptDTO):
                    raise AdminDataError("ADMIN_WRITE_OUTCOME_UNKNOWN", 503, self._pending.request_id, True)
                self._pending = None
            client.capabilities(str(uuid4()))
            serialized = json.dumps(input_dto.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            try:
                client.execute(RESOURCE_OBSERVER_PUBLISH, input_dto, request_id)
            except AdminDataError as error:
                if error.outcome_unknown:
                    self._pending = _PendingObserverWrite(request_id, sha256(serialized.encode()).hexdigest())
                raise
