# [Input] Admin section.begin RTA, worker service consumer and immutable launch snapshot.
# [Output] Server-only child Thread persistence/config owner with snapshot Session broker and renewal.
# [Pos] Reflections Agent turn authority; RTA never enters CLI, MCP, env, workspace, logs or public DTOs.
# [Sync] 2026-09-16: exchange the live RTA for a separate source-fenced Gateway runtime grant.
# [Sync] 2026-09-15: add exact six-operation RTA composition and original-request write recovery.
# [Sync] 2026-09-15: make shutdown drain each owner and always attempt RTA revocation.
"""Task/section/Thread-bound persistence for one Reflections child Agent turn."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from threading import Event, Lock, RLock, Thread, current_thread
from typing import Callable
from uuid import uuid4

from .agent_turn_persistence import AdminAgentTurnPersistence
from .chat_data import AdminChatData, PERSIST_MESSAGE, UPDATE_SESSION
from .chat_models import (
    ChangedResultDTO,
    ChatThreadDTO,
    MessagePersistInputDTO,
    MessagePersistResultDTO,
    ThreadIdInputDTO,
    ThreadSessionInputDTO,
)
from .client import AdminDataClient, DomainOperation
from .delegation import (
    AdminDelegationCreator,
    AdminRuntimeClient,
    DelegationCreateInputDTO,
    RuntimeHttpConfig,
)
from .delegation_keeper import RuntimeRenewalSettings
from .errors import AdminDataError, invalid_response
from .models import CommittedReceiptDTO, StrictDTO
from .gateway_runtime import AdminGatewayRuntime
from .reflection_task_data import AdminReflectionsWorkerData
from .reflection_task_models import (
    ReflectionAuthorityDTO,
    ReflectionLaunchSnapshotDTO,
    ReflectionSectionAuthorityInputDTO,
    ReflectionSectionBeginOutputDTO,
)
from .reflection_task_runtime import ReflectionSnapshotSessionProjectionProvider
from .session_models import SessionListInputDTO, SessionPreviewDTO
from .session_projection_broker import (
    SessionProjectionBroker,
    SessionProjectionBrokerSettings,
)
from .system_config_data import AdminSystemConfigData
from .user_message_data import (
    AdminUserMessageData,
    PERSIST_USER_MESSAGE,
    UserMessageInputDTO,
    UserMessageOutputDTO,
    user_message_input,
)
from .workspace_data import require_workspace_capabilities


logger = logging.getLogger(__name__)


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass(frozen=True, slots=True)
class _PendingWrite:
    operation: DomainOperation
    input_dto: StrictDTO
    request_id: str


@dataclass(frozen=True, slots=True)
class _KnownUserWrite:
    input_dto: UserMessageInputDTO
    request_id: str
    result: UserMessageOutputDTO


class ReflectionAuthorityKeeper:
    """Renew one unchanged RTA through background service identity only."""

    def __init__(
        self,
        authority: ReflectionAuthorityDTO,
        worker: AdminReflectionsWorkerData,
        *,
        settings: RuntimeRenewalSettings | None = None,
        clock: Callable[[], datetime] | None = None,
        request_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._authority = authority
        self._worker = worker
        self._settings = settings or RuntimeRenewalSettings()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._request_id_factory = request_id_factory or (lambda: str(uuid4()))
        self._expires_at = _timestamp(authority.expires_at)
        self._maximum_expires_at = _timestamp(authority.maximum_expires_at)
        if self._expires_at > self._maximum_expires_at:
            raise AdminDataError("ADMIN_RESPONSE_INVALID", 503)
        self._renew_at = self._deadline(self._clock())
        self._last_error_code: str | None = None
        self._unknown_blocked = False
        self._lock = RLock()
        self._action_lock = Lock()
        self._stop = Event()
        self._thread: Thread | None = None

    def _deadline(self, now: datetime) -> datetime:
        if self._expires_at == self._maximum_expires_at:
            return self._maximum_expires_at
        remaining = self._expires_at - now
        return now + remaining * (1 - self._settings.advance_fraction)

    def current_token(self) -> str:
        with self._lock:
            if self._stop.is_set() or self._clock() >= self._expires_at:
                raise AdminDataError("DELEGATION_EXPIRED", 401)
            return self._authority.token

    def tick(self) -> None:
        with self._action_lock:
            with self._lock:
                if (
                    self._stop.is_set()
                    or self._unknown_blocked
                    or self._clock() < self._renew_at
                    or self._expires_at >= self._maximum_expires_at
                ):
                    return
                request_id = self._request_id_factory()
            try:
                renewed = self._worker.renew_authority(
                    ReflectionSectionAuthorityInputDTO(
                        task_id=self._authority.task_id,
                        section=self._authority.section,
                    ),
                    request_id,
                )
                renewed_expiry = _timestamp(renewed.expires_at)
                maximum = _timestamp(renewed.maximum_expires_at)
                if (
                    renewed.purpose != self._authority.purpose
                    or renewed.task_id != self._authority.task_id
                    or renewed.section != self._authority.section
                    or renewed.thread_id != self._authority.thread_id
                    or renewed.scopes != self._authority.scopes
                    or maximum != self._maximum_expires_at
                    or renewed_expiry <= self._expires_at
                    or renewed_expiry > maximum
                ):
                    raise invalid_response(request_id, write=True)
                with self._lock:
                    self._expires_at = renewed_expiry
                    self._renew_at = self._deadline(self._clock())
                    self._last_error_code = None
            except AdminDataError as error:
                with self._lock:
                    self._last_error_code = error.code
                    if error.outcome_unknown:
                        # No later tick may issue a second POST after an
                        # unresolved original-request receipt.
                        self._unknown_blocked = True
            except Exception:
                with self._lock:
                    self._last_error_code = "REFLECTION_AUTHORITY_BACKGROUND_FAILURE"

    def start(self) -> None:
        with self._lock:
            if self._stop.is_set() or self._thread is not None:
                return
            self._thread = Thread(
                target=self._run,
                name="dream-reflections-authority-renewal",
                daemon=True,
            )
            self._thread.start()

    def _run(self) -> None:
        while not self._stop.wait(self._settings.check_interval_seconds):
            self.tick()

    def close(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread is not current_thread():
            thread.join()


class AdminReflectionSectionPersistence(AdminAgentTurnPersistence):
    """Own one RTA and expose only the shared Agent persistence methods."""

    def __init__(
        self,
        begin: ReflectionSectionBeginOutputDTO,
        snapshot: ReflectionLaunchSnapshotDTO,
        client: AdminDataClient,
        worker: AdminReflectionsWorkerData,
        *,
        session_broker_settings: SessionProjectionBrokerSettings,
        clock: Callable[[], datetime] | None = None,
        renewal_settings: RuntimeRenewalSettings | None = None,
        request_id_factory: Callable[[], str] | None = None,
    ) -> None:
        authority = begin.authority
        if (
            authority.task_id != snapshot.task_id
            or authority.section != begin.section
            or authority.thread_id != begin.thread_id
            or authority.purpose != "reflections-worker"
            or authority.scopes != ("dream:read", "dream:write")
        ):
            raise AdminDataError("ADMIN_RESPONSE_INVALID", 503)
        self._begin = begin
        self._snapshot = snapshot
        self._client = client
        self._worker = worker
        self._chat = AdminChatData(client)
        self._system_config = AdminSystemConfigData(client)
        self._user_messages = AdminUserMessageData(client)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._request_id_factory = request_id_factory or (lambda: str(uuid4()))
        self._keeper = ReflectionAuthorityKeeper(
            authority,
            worker,
            settings=renewal_settings,
            clock=self._clock,
            request_id_factory=self._request_id_factory,
        )
        self._session_provider = ReflectionSnapshotSessionProjectionProvider(snapshot)
        self._session_broker = SessionProjectionBroker(
            self._session_provider, settings=session_broker_settings
        )
        self._actor_id: str | None = None
        self._known_user_writes: dict[str, _KnownUserWrite] = {}
        self._pending: _PendingWrite | None = None
        self._session_write: tuple[ThreadSessionInputDTO, ChangedResultDTO] | None = None
        self._lock = RLock()
        self._write_lock = RLock()
        self._close_lock = Lock()
        self._closed = False

    @property
    def task_id(self) -> str:
        return self._begin.authority.task_id

    @property
    def section(self) -> str:
        return self._begin.section

    @property
    def thread_id(self) -> str:
        return self._begin.thread_id

    def start(self) -> None:
        with self._lock:
            if self._closed:
                raise AdminDataError("DELEGATION_EXPIRED", 401)
        self._keeper.start()
        try:
            self._session_broker.start()
        except Exception:
            self.close()
            raise

    def _token(self) -> str:
        with self._lock:
            if self._closed:
                raise AdminDataError("DELEGATION_EXPIRED", 401)
        return self._keeper.current_token()

    def resolve_actor_id(self) -> str:
        with self._write_lock:
            if self._actor_id is not None:
                return self._actor_id
            request_id = self._request_id_factory()
            result = self._chat.get_thread(
                ThreadIdInputDTO(thread_id=self.thread_id),
                request_id,
                access_token=self._token(),
            )
            if result.thread is None or result.thread.id != self.thread_id:
                raise invalid_response(request_id)
            self._actor_id = result.thread.user_id
            return self._actor_id

    def _require_binding(self, *, actor_id: str, thread_id: str) -> None:
        if thread_id != self.thread_id or str(actor_id) != self.resolve_actor_id():
            raise AdminDataError("DREAM_DELEGATION_ENTITY_DENIED", 403)

    def thread(self, *, actor_id: str, thread_id: str) -> ChatThreadDTO | None:
        with self._write_lock:
            self._require_binding(actor_id=actor_id, thread_id=thread_id)
            request_id = self._request_id_factory()
            result = self._chat.get_thread(
                ThreadIdInputDTO(thread_id=thread_id),
                request_id,
                access_token=self._token(),
            )
            if (
                result.thread is None
                or result.thread.id != thread_id
                or result.thread.user_id != str(actor_id)
            ):
                raise invalid_response(request_id)
            return result.thread

    def system_config(self, *, actor_id: str, thread_id: str) -> dict:
        with self._write_lock:
            self._require_binding(actor_id=actor_id, thread_id=thread_id)
            return self._system_config.get_thread(
                ThreadIdInputDTO(thread_id=thread_id),
                self._request_id_factory(),
                access_token=self._token(),
            )

    def recent_sessions(
        self, *, actor_id: str, thread_id: str
    ) -> tuple[SessionPreviewDTO, ...]:
        self._require_binding(actor_id=actor_id, thread_id=thread_id)
        today = self._clock().astimezone(timezone.utc).date()
        result = self._session_provider.list_sessions(
            SessionListInputDTO(
                start_date=(today - timedelta(days=2)).isoformat(),
                end_date=today.isoformat(),
                include_text=False,
            ),
            self._request_id_factory(),
        )
        return tuple(result.sessions)

    def session_projection_child_env(self) -> dict[str, str]:
        return self._session_broker.child_env()

    def gateway_runtime(
        self,
        runtime_http_config: RuntimeHttpConfig,
        request_id: str,
    ) -> AdminGatewayRuntime:
        """Exchange the server-only RTA without projecting it into the child."""

        grant = AdminDelegationCreator(self._client).create(
            DelegationCreateInputDTO(
                purpose="gateway-cli",
                thread_id=self.thread_id,
                run_id=None,
                editor_session_id=None,
                scopes=["messages:create", "messages:count_tokens", "models:list"],
            ),
            access_token=self._token(),
            request_id=request_id,
        )
        return AdminGatewayRuntime(
            grant,
            AdminRuntimeClient(runtime_http_config),
        )

    def persist_user(
        self,
        *,
        actor_id: str,
        thread_id: str,
        message_id: str,
        parts: list,
        metadata: dict | None,
    ) -> UserMessageOutputDTO:
        input_dto = user_message_input(thread_id, message_id, parts, metadata)
        with self._write_lock:
            self._require_binding(actor_id=actor_id, thread_id=thread_id)
            known = self._known_user_writes.get(message_id) if self._pending is None else None
            if known is not None:
                if known.input_dto != input_dto:
                    raise AdminDataError(
                        "CHAT_MESSAGE_IDENTITY_CONFLICT", 409, known.request_id
                    )
                return known.result
            return self._write(PERSIST_USER_MESSAGE, input_dto)

    def persist_assistant(
        self,
        *,
        actor_id: str,
        thread_id: str,
        message_id: str,
        parts: list,
        metadata: dict | None,
        history_final_text: str | None = None,
        history_process_available: bool = False,
        history_projection_version: int | None = None,
    ) -> MessagePersistResultDTO:
        input_dto = MessagePersistInputDTO(
            thread_id=thread_id,
            message_id=message_id,
            role="assistant",
            parts=parts,
            metadata=metadata,
            history_final_text=history_final_text,
            history_process_available=history_process_available,
            history_projection_version=history_projection_version,
        )
        with self._write_lock:
            self._require_binding(actor_id=actor_id, thread_id=thread_id)
            return self._write(PERSIST_MESSAGE, input_dto)

    def update_session(
        self,
        *,
        actor_id: str,
        thread_id: str,
        session_id: str,
        contract_version: str,
    ) -> ChangedResultDTO:
        input_dto = ThreadSessionInputDTO(
            thread_id=thread_id,
            claude_session_id=session_id,
            agent_contract_version=contract_version,
        )
        with self._write_lock:
            self._require_binding(actor_id=actor_id, thread_id=thread_id)
            if (
                self._pending is None
                and self._session_write is not None
                and self._session_write[0] == input_dto
            ):
                return self._session_write[1]
            return self._write(UPDATE_SESSION, input_dto)

    def _write(self, operation: DomainOperation, input_dto: StrictDTO):
        if all(
            operation is not allowed
            for allowed in (PERSIST_USER_MESSAGE, PERSIST_MESSAGE, UPDATE_SESSION)
        ):
            raise AdminDataError("ADMIN_OPERATION_CONTRACT_INVALID", 503)
        token = self._token()
        pending = self._pending
        if pending is not None:
            if pending.operation is not operation or pending.input_dto != input_dto:
                raise AdminDataError(
                    "ADMIN_WRITE_RESULT_UNKNOWN", 503, pending.request_id, True
                )
            try:
                if operation is PERSIST_MESSAGE:
                    require_workspace_capabilities(self._client, pending.request_id)
                receipt = self._client.receipt(
                    operation, pending.request_id, access_token=token
                )
            except AdminDataError as error:
                raise AdminDataError(
                    error.code, error.status_code, pending.request_id, True, error.details
                ) from None
            if not isinstance(receipt, CommittedReceiptDTO):
                raise AdminDataError(
                    "ADMIN_WRITE_RESULT_UNKNOWN", 503, pending.request_id, True
                )
            return self._confirm(pending, receipt.result)

        pending = _PendingWrite(operation, input_dto, self._request_id_factory())
        self._pending = pending
        try:
            if operation is PERSIST_USER_MESSAGE:
                result = self._user_messages.persist(
                    input_dto, pending.request_id, access_token=token
                )
            elif operation is PERSIST_MESSAGE:
                require_workspace_capabilities(self._client, pending.request_id)
                result = self._chat.persist_message(
                    input_dto, pending.request_id, access_token=token
                )
            else:
                result = self._chat.update_session(
                    input_dto, pending.request_id, access_token=token
                )
        except AdminDataError as error:
            if not error.outcome_unknown:
                self._pending = None
            raise
        except Exception:
            raise AdminDataError(
                "ADMIN_UNAVAILABLE", 503, pending.request_id, True
            ) from None
        return self._confirm(pending, result)

    def _confirm(self, pending: _PendingWrite, result):
        if pending.operation is PERSIST_USER_MESSAGE:
            if result.message_id != pending.input_dto.message_id:
                raise invalid_response(pending.request_id, write=True)
            self._known_user_writes[result.message_id] = _KnownUserWrite(
                pending.input_dto, pending.request_id, result
            )
        elif pending.operation is PERSIST_MESSAGE:
            if result.message_id != pending.input_dto.message_id:
                raise invalid_response(pending.request_id, write=True)
        else:
            self._session_write = (pending.input_dto, result)
        self._pending = None
        return result

    def close(self) -> None:
        with self._close_lock:
            with self._lock:
                if self._closed:
                    return
                self._closed = True
            first_error: BaseException | None = None
            try:
                self._session_broker.close()
            except BaseException as error:
                first_error = error
            finally:
                try:
                    with self._write_lock:
                        pass
                except BaseException as error:
                    first_error = first_error or error
                finally:
                    try:
                        self._keeper.close()
                    except BaseException as error:
                        first_error = first_error or error
                    finally:
                        try:
                            self._worker.revoke_authority(
                                ReflectionSectionAuthorityInputDTO(
                                    task_id=self.task_id, section=self.section
                                ),
                                self._request_id_factory(),
                            )
                        except AdminDataError as error:
                            logger.error(
                                "Reflections authority revoke failed task_id=%s section=%s code=%s",
                                self.task_id, self.section, error.code,
                            )
                        except BaseException as error:
                            first_error = first_error or error
            if first_error is not None:
                raise first_error


__all__ = [
    "AdminReflectionSectionPersistence",
    "ReflectionAuthorityKeeper",
]
