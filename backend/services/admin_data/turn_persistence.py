# [Input] Server-only persistence grant, immutable Workflow resolution and typed Admin client.
# [Output] Atomic user reservations, original-ID recovery and independently renewed server credential.
# [Pos] One factory-owned turn persistence owner; credentials never enter CLI/Editor/browser options.
# [Sync] 2026-09-15: bind server persistence to the authoritative Thread/Run and preserve unknown writes.
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock, RLock
from typing import Callable
from uuid import uuid4

from .client import AdminDataClient
from .delegation import AdminRuntimeClient, RuntimeGrant
from .delegation_keeper import RuntimeGrantKeeper, RuntimeRenewalSettings
from .errors import AdminDataError, configuration_invalid, invalid_response
from .models import CommittedReceiptDTO
from .user_message_data import AdminUserMessageData, PERSIST_USER_MESSAGE, UserMessageInputDTO, UserMessageOutputDTO, user_message_input
from .workflow_data import AdminWorkflowResolution


@dataclass(frozen=True)
class _UserWrite:
    input_dto: UserMessageInputDTO
    request_id: str
    result: UserMessageOutputDTO | None = None


class AdminTurnPersistence:
    def __init__(self, resolution: AdminWorkflowResolution, grant: RuntimeGrant, client: AdminDataClient, *,
        runtime_client_factory: Callable[[], AdminRuntimeClient],
        clock: Callable[[], datetime] | None = None,
        renewal_settings: RuntimeRenewalSettings | None = None,
        request_id_factory: Callable[[], str] | None = None):
        expected_run = resolution.context.workflow_run_id if resolution.context is not None else None
        if (grant.purpose != "server-persistence" or grant.thread_id != resolution.thread_id
            or grant.run_id != expected_run or grant.editor_session_id is not None
            or frozenset(grant.scopes) != frozenset({"dream:read", "dream:write"})):
            raise configuration_invalid()
        self._resolution = resolution
        self._grant = grant
        self._client = client
        self._user_messages = AdminUserMessageData(client)
        self._runtime_client_factory = runtime_client_factory
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._settings = renewal_settings
        self._request_id_factory = request_id_factory or (lambda: str(uuid4()))
        self._keeper: RuntimeGrantKeeper | None = None
        self._runtime_client: AdminRuntimeClient | None = None
        self._closed = False
        self._lock = RLock()
        self._write_lock = Lock()
        self._writes: dict[str, _UserWrite] = {}
        self._pending: _UserWrite | None = None

    def start(self) -> None:
        with self._lock:
            if self._closed:
                raise AdminDataError("DELEGATION_EXPIRED", 401)
            if self._keeper is None:
                client = self._runtime_client_factory()
                keeper = RuntimeGrantKeeper(self._grant, client, clock=self._clock, settings=self._settings)
                self._runtime_client, self._keeper = client, keeper
                keeper.start()

    def current_grant(self, *, actor_id: str, thread_id: str) -> RuntimeGrant:
        self._resolution.context_for(actor_id=actor_id, thread_id=thread_id)
        with self._lock:
            if self._closed:
                raise AdminDataError("DELEGATION_EXPIRED", 401)
            keeper = self._keeper
            grant = self._grant
        if keeper is not None:
            return keeper.current("server-persistence")
        if self._clock() >= grant.expires_at:
            raise AdminDataError("DELEGATION_EXPIRED", 401)
        return grant

    def persist_user(self, *, actor_id: str, thread_id: str, message_id: str, parts: list, metadata: dict | None) -> UserMessageOutputDTO:
        input_dto = user_message_input(thread_id, message_id, parts, metadata)
        with self._write_lock:
            grant = self.current_grant(actor_id=actor_id, thread_id=thread_id)
            if self._pending is not None:
                pending = self._pending
                if pending.input_dto != input_dto:
                    raise AdminDataError("ADMIN_WRITE_RESULT_UNKNOWN", 503, pending.request_id, True)
                try:
                    receipt = self._client.receipt(PERSIST_USER_MESSAGE, pending.request_id, access_token=grant.token)
                except AdminDataError as error:
                    raise AdminDataError(error.code, error.status_code, pending.request_id, True) from None
                if not isinstance(receipt, CommittedReceiptDTO):
                    raise AdminDataError("ADMIN_WRITE_RESULT_UNKNOWN", 503, pending.request_id, True)
                return self._confirm(pending, receipt.result)
            known = self._writes.get(message_id)
            if known is not None:
                if known.input_dto != input_dto:
                    raise AdminDataError("CHAT_MESSAGE_IDENTITY_CONFLICT", 409, known.request_id)
                return known.result
            pending = _UserWrite(input_dto, self._request_id_factory())
            self._pending = pending
            try:
                result = self._user_messages.persist(input_dto, pending.request_id, access_token=grant.token)
            except AdminDataError as error:
                if not error.outcome_unknown:
                    self._pending = None
                raise
            except Exception:
                raise AdminDataError("ADMIN_UNAVAILABLE", 503, pending.request_id, True) from None
            return self._confirm(pending, result)

    def _confirm(self, pending: _UserWrite, result: UserMessageOutputDTO) -> UserMessageOutputDTO:
        if result.message_id != pending.input_dto.message_id:
            raise invalid_response(pending.request_id, write=True)
        self._writes[result.message_id] = _UserWrite(pending.input_dto, pending.request_id, result)
        self._pending = None
        return result

    def close(self) -> None:
        with self._lock:
            self._closed = True
            keeper, client = self._keeper, self._runtime_client
        # Cancellation cannot stop an already-dispatched synchronous command.
        # Phase 4 drains it before application-owned HTTP connections close.
        with self._write_lock:
            pass
        if keeper is not None:
            keeper.close()
        if client is not None:
            client.close()
