# [Input] Server-only persistence grant, immutable Workflow resolution and typed Admin client.
# [Output] Atomic turn/auto-repair persistence, delegated Notion DTO store, and provider-bound Session/current-Run broker.
# [Pos] One factory-owned turn persistence owner; credentials never enter CLI/Editor/browser options.
# [Sync] 2026-09-15: share the unknown-write barrier across user reservations and SDK Session updates; drain Thread reads.
# [Sync] 2026-09-15: bind server persistence to the authoritative Thread/Run and preserve unknown writes.
# [Sync] 2026-09-15: share the unknown barrier with complete/partial assistant writes and exact history schemas.
# [Sync] 2026-09-15: read fresh Thread SystemConfig through the same draining persistence grant.
# [Sync] 2026-09-15: read three UTC days of recent Sessions through the current draining grant.
# [Sync] 2026-09-15: bind arbitrary-date Session projections to a private broker and close it before grant resources.
# [Sync] 2026-09-15: implement the shared server-owned Agent persistence marker used by Reflections RTA turns.
# [Sync] 2026-09-15: reuse the exact Thread/Run grant and unknown-write barrier for Registry108 activation.
# [Sync] 2026-09-15: persist Registry109 Story proposals through the same Thread grant and unknown-write barrier.
# [Sync] 2026-09-16: construct an actor/Thread-bound Notion DTO store from the current grant.
# [Sync] 2026-09-16: share the write barrier with Registry169 repair settlement.
# [Sync] 2026-09-16: consume Registry185-191 authority/lifecycle/index through the exact turn grant.
# [Sync] 2026-09-16: project the current authoritative WorkflowRun through existing Admin DTO reads.
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from threading import Lock, RLock
from typing import Callable
from uuid import uuid4

from models.workflow_run import WorkflowRun

from .agent_turn_persistence import AdminAgentTurnPersistence
from .chat_data import AdminChatData, PERSIST_MESSAGE, UPDATE_SESSION
from .chat_models import ChatThreadDTO, ChangedResultDTO, MessagePersistInputDTO, MessagePersistResultDTO, ThreadIdInputDTO, ThreadSessionInputDTO
from .client import AdminDataClient, DomainOperation
from .delegation import AdminRuntimeClient, RuntimeGrant
from .delegation_keeper import RuntimeGrantKeeper, RuntimeRenewalSettings
from .errors import AdminDataError, configuration_invalid, invalid_response
from .models import CommittedReceiptDTO, StrictDTO
from .session_data import AdminSessionData, require_session_list_capabilities
from .session_models import SessionListInputDTO, SessionListResultDTO, SessionPreviewDTO
from .session_projection_broker import (
    SessionProjectionBroker,
    SessionProjectionBrokerSettings,
)
from .run_data import AdminRunData, RunLookupInputDTO
from .user_message_data import AdminUserMessageData, PERSIST_USER_MESSAGE, UserMessageInputDTO, UserMessageOutputDTO, user_message_input
from .workflow_data import AdminWorkflowResolution
from .deck_workspace_plugins_data import (
    AdminDeckWorkspacePluginsResolution,
    AdminDeckWorkspacePluginsData,
    AdminDeckWorkspacePluginsProvider,
    DeckWorkspacePluginsInputDTO,
    WorkspaceProfile,
)
from .workflow_managed_mcp_scope_data import (
    AdminWorkflowManagedMcpScopeData,
    AdminWorkflowManagedMcpScopeProvider,
    AdminWorkflowManagedMcpScopeResolution,
    WorkflowManagedMcpScopeInputDTO,
)
from .workflow_runtime_activation_data import (
    ACTIVATE_WORKFLOW_RUNTIME,
    AdminWorkflowRuntimeActivationData,
    AdminWorkflowRuntimeActivationProvider,
    WorkflowRuntimeActivationInputDTO,
    WorkflowRuntimeActivationOutputDTO,
)
from .workspace_data import require_workspace_capabilities
from .story_workspace_output_data import (
    STORE_STORY_WORKSPACE_OUTPUT,
    AdminStoryWorkspaceOutputData,
    AdminStoryWorkspaceOutputProvider,
    StoryWorkspaceOutputInputDTO,
    StoryWorkspaceOutputResultDTO,
)
from .story_workspace_artifact_data import (
    ENSURE_STORY_WORKSPACE_EPISODE_AUTHORITY,
    MARK_STORY_WORKSPACE_ARTIFACT_OUTPUT_READY,
    MATERIALIZE_STORY_WORKSPACE_ARTIFACT_INDEX,
    READ_STORY_WORKSPACE_ARTIFACT_AUTHORITY,
    AdminStoryWorkspaceArtifactData,
    AdminStoryWorkspaceArtifactProvider,
    StoryWorkspaceArtifactAuthorityInputDTO,
    StoryWorkspaceArtifactProjectionDTO,
    StoryWorkspaceEpisodeAuthorityEnsureInputDTO,
    StoryWorkspaceArtifactOutputReadyInputDTO,
)
from .dream_auto_repair_data import (
    SETTLE_DREAM_AUTO_REPAIR,
    AdminDreamAutoRepairData,
    AdminDreamAutoRepairProvider,
    DreamAutoRepairIdentityDTO,
    DreamAutoRepairSettleInputDTO,
    DreamAutoRepairSettleOutputDTO,
    DreamAutoRepairTerminalStatus,
)
from .system_config_data import AdminSystemConfigData


@dataclass(frozen=True)
class _UserWrite:
    input_dto: UserMessageInputDTO
    request_id: str
    result: UserMessageOutputDTO


@dataclass(frozen=True)
class _PendingWrite:
    operation: DomainOperation
    input_dto: StrictDTO
    request_id: str


class AdminTurnSessionProjectionProvider:
    """Bind child projections to one immutable Chat actor, Thread and Run owner."""

    def __init__(self, owner: "AdminTurnPersistence") -> None:
        self._owner = owner

    def list_sessions(
        self, input_dto: SessionListInputDTO, request_id: str
    ) -> SessionListResultDTO:
        return self._owner._project_sessions(
            actor_id=self._owner._resolution.canonical_user_id,
            thread_id=self._owner._resolution.thread_id,
            input_dto=input_dto,
            request_id=request_id,
        )

    def current_workflow_run(self, request_id: str) -> WorkflowRun:
        return self._owner._project_current_workflow_run(
            actor_id=self._owner._resolution.canonical_user_id,
            thread_id=self._owner._resolution.thread_id,
            request_id=request_id,
        )


class AdminTurnPersistence(
    AdminAgentTurnPersistence,
    AdminDeckWorkspacePluginsProvider,
    AdminWorkflowManagedMcpScopeProvider,
    AdminWorkflowRuntimeActivationProvider,
    AdminStoryWorkspaceOutputProvider,
    AdminStoryWorkspaceArtifactProvider,
    AdminDreamAutoRepairProvider,
):
    def __init__(self, resolution: AdminWorkflowResolution, grant: RuntimeGrant, client: AdminDataClient, *,
        runtime_client_factory: Callable[[], AdminRuntimeClient],
        clock: Callable[[], datetime] | None = None,
        renewal_settings: RuntimeRenewalSettings | None = None,
        request_id_factory: Callable[[], str] | None = None,
        session_broker_settings: SessionProjectionBrokerSettings):
        expected_run = resolution.context.workflow_run_id if resolution.context is not None else None
        if (grant.purpose != "server-persistence" or grant.thread_id != resolution.thread_id
            or grant.run_id != expected_run or grant.editor_session_id is not None
            or frozenset(grant.scopes) != frozenset({"dream:read", "dream:write"})):
            raise configuration_invalid()
        self._resolution = resolution
        self._grant = grant
        self._client = client
        self._user_messages = AdminUserMessageData(client)
        self._chat = AdminChatData(client)
        self._sessions = AdminSessionData(client)
        self._system_config = AdminSystemConfigData(client)
        self._workspace_plugin_data = AdminDeckWorkspacePluginsData(
            client,
            canonical_user_id=resolution.canonical_user_id,
        )
        self._managed_mcp_scope_data = AdminWorkflowManagedMcpScopeData(
            client,
            canonical_user_id=resolution.canonical_user_id,
        )
        self._run_data = AdminRunData(
            client,
            canonical_user_id=resolution.canonical_user_id,
        )
        self._workflow_runtime_activation_data = (
            AdminWorkflowRuntimeActivationData(client)
        )
        self._story_workspace_output_data = AdminStoryWorkspaceOutputData(client)
        self._story_workspace_artifact_data = AdminStoryWorkspaceArtifactData(
            client,
            canonical_user_id=resolution.canonical_user_id,
        )
        self._dream_auto_repair_data = AdminDreamAutoRepairData(client)
        self._runtime_client_factory = runtime_client_factory
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._settings = renewal_settings
        self._request_id_factory = request_id_factory or (lambda: str(uuid4()))
        self._keeper: RuntimeGrantKeeper | None = None
        self._runtime_client: AdminRuntimeClient | None = None
        self._closed = False
        self._lock = RLock()
        self._write_lock = Lock()
        self._close_lock = Lock()
        self._writes: dict[str, _UserWrite] = {}
        self._pending: _PendingWrite | None = None
        self._session_write: tuple[ThreadSessionInputDTO, ChangedResultDTO] | None = None
        self._session_projection_provider = AdminTurnSessionProjectionProvider(self)
        self._session_projection_broker = SessionProjectionBroker(
            self._session_projection_provider,
            settings=session_broker_settings,
            workflow_run_provider=self._session_projection_provider,
        )

    def start(self) -> None:
        with self._lock:
            if self._closed:
                raise AdminDataError("DELEGATION_EXPIRED", 401)
            if self._keeper is None:
                client = self._runtime_client_factory()
                keeper = RuntimeGrantKeeper(self._grant, client, clock=self._clock, settings=self._settings)
                self._runtime_client, self._keeper = client, keeper
                keeper.start()
        try:
            self._session_projection_broker.start()
        except Exception:
            self.close()
            raise

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

    def notion_connector_store(self, *, actor_id: str, thread_id: str):
        """Build a short-lived Notion adapter from the current exact turn grant."""

        from notion.store import NotionConnectorStore

        from .notion_connector_data import (
            AdminNotionConnectorData,
            NotionAuthorityDTO,
        )

        context = self._resolution.context_for(
            actor_id=actor_id,
            thread_id=thread_id,
        )
        with self._write_lock:
            grant = self.current_grant(actor_id=actor_id, thread_id=thread_id)
        return NotionConnectorStore(
            AdminNotionConnectorData(self._client),
            access_token=grant.token,
            authority=NotionAuthorityDTO(
                thread_id=thread_id,
                workflow_run_id=(
                    context.workflow_run_id if context is not None else None
                ),
            ),
            expected_user_id=actor_id,
        )

    def persist_user(self, *, actor_id: str, thread_id: str, message_id: str, parts: list, metadata: dict | None) -> UserMessageOutputDTO:
        input_dto = user_message_input(thread_id, message_id, parts, metadata)
        with self._write_lock:
            grant = self.current_grant(actor_id=actor_id, thread_id=thread_id)
            known = self._writes.get(message_id) if self._pending is None else None
            if known is not None:
                if known.input_dto != input_dto:
                    raise AdminDataError("CHAT_MESSAGE_IDENTITY_CONFLICT", 409, known.request_id)
                return known.result
            return self._write(PERSIST_USER_MESSAGE, input_dto, grant)

    def thread(self, *, actor_id: str, thread_id: str) -> ChatThreadDTO | None:
        with self._write_lock:
            grant = self.current_grant(actor_id=actor_id, thread_id=thread_id)
            request_id = self._request_id_factory()
            result = self._chat.get_thread(ThreadIdInputDTO(thread_id=thread_id), request_id, access_token=grant.token)
            if result.thread is not None and (result.thread.id != thread_id or result.thread.user_id != str(actor_id)):
                raise invalid_response(request_id)
            return result.thread

    def system_config(self, *, actor_id: str, thread_id: str) -> dict:
        """Read the current Thread owner's config through this exact grant."""

        with self._write_lock:
            grant = self.current_grant(actor_id=actor_id, thread_id=thread_id)
            request_id = self._request_id_factory()
            return self._system_config.get_thread(
                ThreadIdInputDTO(thread_id=thread_id),
                request_id,
                access_token=grant.token,
            )

    def recent_sessions(
        self, *, actor_id: str, thread_id: str
    ) -> tuple[SessionPreviewDTO, ...]:
        """Read the current actor's recent Session projection through this grant."""

        today = self._clock().astimezone(timezone.utc).date()
        result = self._project_sessions(
            actor_id=actor_id,
            thread_id=thread_id,
            input_dto=SessionListInputDTO(
                start_date=(today - timedelta(days=2)).isoformat(),
                end_date=today.isoformat(),
                include_text=False,
            ),
            request_id=self._request_id_factory(),
        )
        return tuple(result.sessions)

    def workspace_plugins(
        self,
        *,
        actor_id: str,
        thread_id: str,
        profile: WorkspaceProfile,
    ) -> AdminDeckWorkspacePluginsResolution:
        """Read pack metadata with this owner's current exact Thread grant."""

        with self._write_lock:
            grant = self.current_grant(actor_id=actor_id, thread_id=thread_id)
            return self._workspace_plugin_data.resolve(
                DeckWorkspacePluginsInputDTO(
                    thread_id=thread_id,
                    profile=profile,
                ),
                self._request_id_factory(),
                access_token=grant.token,
            )

    def managed_mcp_workspace_scope(
        self,
        *,
        actor_id: str,
        thread_id: str,
        workflow_run_id: str,
    ) -> AdminWorkflowManagedMcpScopeResolution:
        """Resolve the Run workspace through this exact renewable grant."""

        context = self._resolution.context_for(
            actor_id=actor_id,
            thread_id=thread_id,
        )
        if context is None or context.workflow_run_id != workflow_run_id:
            raise AdminDataError("DREAM_DELEGATION_ENTITY_DENIED", 403)
        with self._write_lock:
            grant = self.current_grant(actor_id=actor_id, thread_id=thread_id)
            return self._managed_mcp_scope_data.resolve(
                WorkflowManagedMcpScopeInputDTO(
                    thread_id=thread_id,
                    workflow_run_id=workflow_run_id,
                ),
                self._request_id_factory(),
                access_token=grant.token,
            )

    def activate_workflow_runtime(
        self,
        *,
        actor_id: str,
        thread_id: str,
        workflow_run_id: str,
        remote_session_ref: str,
        verified_plugins: list[dict],
    ) -> WorkflowRuntimeActivationOutputDTO:
        """Persist verified Runtime bindings in one Admin transaction."""

        context = self._resolution.context_for(
            actor_id=actor_id,
            thread_id=thread_id,
        )
        if context is None or context.workflow_run_id != workflow_run_id:
            raise AdminDataError("DREAM_DELEGATION_ENTITY_DENIED", 403)
        try:
            input_dto = WorkflowRuntimeActivationInputDTO(
                thread_id=thread_id,
                workflow_run_id=workflow_run_id,
                remote_session_ref=remote_session_ref,
                verified_plugins=verified_plugins,
            )
        except Exception:
            raise AdminDataError("DREAM_RUNTIME_INIT_INVALID", 409) from None
        with self._write_lock:
            grant = self.current_grant(actor_id=actor_id, thread_id=thread_id)
            result = self._write(ACTIVATE_WORKFLOW_RUNTIME, input_dto, grant)
            return result

    def store_story_workspace_output(
        self,
        *,
        actor_id: str,
        thread_id: str,
        story: dict,
    ) -> StoryWorkspaceOutputResultDTO:
        """Persist one parsed standalone Story proposal in Admin."""

        self._resolution.context_for(actor_id=actor_id, thread_id=thread_id)
        if self._resolution.context is not None:
            raise AdminDataError("DREAM_DELEGATION_ENTITY_DENIED", 403)
        try:
            input_dto = StoryWorkspaceOutputInputDTO(
                thread_id=thread_id,
                story=story,
            )
        except Exception:
            raise AdminDataError("ADMIN_OPERATION_INPUT_INVALID", 400) from None
        with self._write_lock:
            grant = self.current_grant(actor_id=actor_id, thread_id=thread_id)
            return self._write(STORE_STORY_WORKSPACE_OUTPUT, input_dto, grant)

    def story_workspace_artifact_authority(
        self,
        *,
        actor_id: str,
        thread_id: str,
        workflow_run_id: str,
    ):
        """Read exact Run/launch authority through the renewable turn grant."""

        context = self._resolution.context_for(
            actor_id=actor_id,
            thread_id=thread_id,
        )
        if context is None or context.workflow_run_id != workflow_run_id:
            raise AdminDataError("DREAM_DELEGATION_ENTITY_DENIED", 403)
        input_dto = StoryWorkspaceArtifactAuthorityInputDTO(
            workflow_run_id=workflow_run_id
        )
        with self._write_lock:
            grant = self.current_grant(actor_id=actor_id, thread_id=thread_id)
            request_id = self._request_id_factory()
            result = self._story_workspace_artifact_data.execute(
                READ_STORY_WORKSPACE_ARTIFACT_AUTHORITY,
                input_dto,
                request_id,
                access_token=grant.token,
            )
        if result.authority.thread_id != thread_id:
            raise invalid_response(request_id)
        return result.authority

    def ensure_story_workspace_episode_authority(
        self,
        *,
        actor_id: str,
        thread_id: str,
        workflow_run_id: str,
        story_slug: str,
        episode_code: str,
    ):
        """Establish the source-message Episode identity in one Admin UOW."""

        context = self._resolution.context_for(
            actor_id=actor_id,
            thread_id=thread_id,
        )
        if context is None or context.workflow_run_id != workflow_run_id:
            raise AdminDataError("DREAM_DELEGATION_ENTITY_DENIED", 403)
        input_dto = StoryWorkspaceEpisodeAuthorityEnsureInputDTO(
            workflow_run_id=workflow_run_id,
            story_slug=story_slug,
            episode_code=episode_code,
        )
        with self._write_lock:
            grant = self.current_grant(actor_id=actor_id, thread_id=thread_id)
            return self._write(
                ENSURE_STORY_WORKSPACE_EPISODE_AUTHORITY,
                input_dto,
                grant,
            )

    def mark_story_workspace_artifact_output_ready(
        self,
        *,
        actor_id: str,
        thread_id: str,
        workflow_run_id: str,
    ):
        """Advance only the Admin-owned output-ready lifecycle transitions."""

        context = self._resolution.context_for(
            actor_id=actor_id,
            thread_id=thread_id,
        )
        if context is None or context.workflow_run_id != workflow_run_id:
            raise AdminDataError("DREAM_DELEGATION_ENTITY_DENIED", 403)
        input_dto = StoryWorkspaceArtifactOutputReadyInputDTO(
            workflow_run_id=workflow_run_id,
            normalized_result_ready=True,
        )
        with self._write_lock:
            grant = self.current_grant(actor_id=actor_id, thread_id=thread_id)
            return self._write(
                MARK_STORY_WORKSPACE_ARTIFACT_OUTPUT_READY,
                input_dto,
                grant,
            )

    def materialize_story_workspace_artifact_index(
        self,
        *,
        actor_id: str,
        thread_id: str,
        workflow_run_id: str,
        projection: StoryWorkspaceArtifactProjectionDTO,
    ):
        """Persist a Dream-computed normalized file projection in Admin."""

        context = self._resolution.context_for(
            actor_id=actor_id,
            thread_id=thread_id,
        )
        if context is None or context.workflow_run_id != workflow_run_id:
            raise AdminDataError("DREAM_DELEGATION_ENTITY_DENIED", 403)
        from .story_workspace_artifact_data import (
            StoryWorkspaceArtifactIndexInputDTO,
        )

        input_dto = StoryWorkspaceArtifactIndexInputDTO(
            workflow_run_id=workflow_run_id,
            projection=projection,
        )
        with self._write_lock:
            grant = self.current_grant(actor_id=actor_id, thread_id=thread_id)
            return self._write(
                MATERIALIZE_STORY_WORKSPACE_ARTIFACT_INDEX,
                input_dto,
                grant,
            )

    def settle_dream_auto_repair(
        self,
        *,
        actor_id: str,
        thread_id: str,
        message_id: str,
        expected_identity: DreamAutoRepairIdentityDTO,
        status: DreamAutoRepairTerminalStatus,
    ) -> DreamAutoRepairSettleOutputDTO:
        """Settle one persisted repair message through its Admin ORM owner."""

        context = self._resolution.context_for(
            actor_id=actor_id,
            thread_id=thread_id,
        )
        if (
            context is None
            or context.workflow_run_id != expected_identity.workflow_run_id
        ):
            raise AdminDataError("DREAM_DELEGATION_ENTITY_DENIED", 403)
        try:
            input_dto = DreamAutoRepairSettleInputDTO(
                thread_id=thread_id,
                message_id=message_id,
                expected_identity=expected_identity,
                status=status,
            )
        except Exception:
            raise AdminDataError("ADMIN_OPERATION_INPUT_INVALID", 400) from None
        with self._write_lock:
            grant = self.current_grant(actor_id=actor_id, thread_id=thread_id)
            result = self._write(SETTLE_DREAM_AUTO_REPAIR, input_dto, grant)
            # The repair continuation replays the same user message through
            # the normal turn path. Advance the local reservation to the
            # Admin-confirmed terminal metadata so that replay remains exact.
            known = self._writes.get(message_id)
            if known is not None and known.input_dto.metadata_json is not None:
                # UserMessageInputDTO already proved this is a JSON object;
                # updating one closed status cannot introduce non-JSON data.
                metadata = json.loads(known.input_dto.metadata_json)
                assert isinstance(metadata, dict)
                metadata["dispatch_status"] = result.status
                refreshed = known.input_dto.model_copy(update={
                    "metadata_json": json.dumps(
                        metadata,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        allow_nan=False,
                    )
                })
                self._writes[message_id] = _UserWrite(
                    refreshed,
                    known.request_id,
                    known.result,
                )
            return result

    def _project_sessions(
        self,
        *,
        actor_id: str,
        thread_id: str,
        input_dto: SessionListInputDTO,
        request_id: str,
    ) -> SessionListResultDTO:
        """Read a strict Session projection using this owner's current grant."""

        if type(input_dto) is not SessionListInputDTO:
            raise AdminDataError("ADMIN_OPERATION_INPUT_INVALID", 400, request_id)
        with self._write_lock:
            grant = self.current_grant(actor_id=actor_id, thread_id=thread_id)
            require_session_list_capabilities(self._client, request_id)
            return self._sessions.list(
                input_dto,
                request_id,
                access_token=grant.token,
            )

    def _project_current_workflow_run(
        self,
        *,
        actor_id: str,
        thread_id: str,
        request_id: str,
    ) -> WorkflowRun:
        """Read the exact turn Run through Admin scope and Run DTO operations."""

        context = self._resolution.context_for(
            actor_id=actor_id,
            thread_id=thread_id,
        )
        if context is None:
            raise AdminDataError(
                "STORY_WORKSPACE_PROJECTION_DENIED", 403, request_id
            )
        with self._write_lock:
            grant = self.current_grant(actor_id=actor_id, thread_id=thread_id)
            scope = self._managed_mcp_scope_data.resolve(
                WorkflowManagedMcpScopeInputDTO(
                    thread_id=thread_id,
                    workflow_run_id=context.workflow_run_id,
                ),
                request_id,
                access_token=grant.token,
            )
            workspace_id = scope.workspace_for(
                actor_id=actor_id,
                thread_id=thread_id,
                workflow_run_id=context.workflow_run_id,
            )
            run = WorkflowRun.model_validate(
                self._run_data.read(
                    RunLookupInputDTO(
                        workspace_id=workspace_id,
                        workflow_run_id=context.workflow_run_id,
                    ),
                    request_id,
                    access_token=grant.token,
                )
            )
        if (
            run.workflow_run_id != context.workflow_run_id
            or run.workspace_id != workspace_id
            or run.created_by != actor_id
            or run.source_voice_thread_id != thread_id
            or run.deck_plugin_id != context.deck_plugin_id
            or run.deck_plugin_version != context.deck_plugin_version
            or run.deck_plugin_binding_id != context.deck_plugin_binding_id
            or run.binding_revision != context.binding_revision
            or run.deck_runtime_snapshot_id != context.deck_runtime_snapshot_id
            or run.runtime_plugin_lock_id != context.runtime_plugin_lock_id
        ):
            raise invalid_response(request_id)
        return run

    def session_projection_child_env(self) -> dict[str, str]:
        """Return only the started broker tuple for the user MCP child."""

        return self._session_projection_broker.child_env()

    def persist_assistant(self, *, actor_id: str, thread_id: str, message_id: str, parts: list,
        metadata: dict | None, history_final_text: str | None = None,
        history_process_available: bool = False, history_projection_version: int | None = None) -> MessagePersistResultDTO:
        input_dto = MessagePersistInputDTO(thread_id=thread_id, message_id=message_id, role="assistant", parts=parts,
            metadata=metadata, history_final_text=history_final_text, history_process_available=history_process_available,
            history_projection_version=history_projection_version)
        with self._write_lock:
            grant = self.current_grant(actor_id=actor_id, thread_id=thread_id)
            return self._write(PERSIST_MESSAGE, input_dto, grant)

    def update_session(self, *, actor_id: str, thread_id: str, session_id: str, contract_version: str) -> ChangedResultDTO:
        input_dto = ThreadSessionInputDTO(thread_id=thread_id, claude_session_id=session_id, agent_contract_version=contract_version)
        with self._write_lock:
            grant = self.current_grant(actor_id=actor_id, thread_id=thread_id)
            if self._pending is None and self._session_write is not None and self._session_write[0] == input_dto:
                return self._session_write[1]
            return self._write(UPDATE_SESSION, input_dto, grant)

    def _write(self, operation: DomainOperation, input_dto: StrictDTO, grant: RuntimeGrant):
        # Every caller holds the same activity lock. Unknown results block a
        # different operation as well as a different input; receipts retain
        # the original operation and immutable input held by this owner.
        if operation is not PERSIST_USER_MESSAGE and operation is not UPDATE_SESSION and operation is not PERSIST_MESSAGE and operation is not ACTIVATE_WORKFLOW_RUNTIME and operation is not STORE_STORY_WORKSPACE_OUTPUT and operation is not SETTLE_DREAM_AUTO_REPAIR and operation is not ENSURE_STORY_WORKSPACE_EPISODE_AUTHORITY and operation is not MARK_STORY_WORKSPACE_ARTIFACT_OUTPUT_READY and operation is not MATERIALIZE_STORY_WORKSPACE_ARTIFACT_INDEX:
            raise configuration_invalid()
        pending = self._pending
        if pending is not None:
            if pending.operation is not operation or pending.input_dto != input_dto:
                raise AdminDataError("ADMIN_WRITE_RESULT_UNKNOWN", 503, pending.request_id, True)
            try:
                if operation is PERSIST_MESSAGE:
                    require_workspace_capabilities(self._client, pending.request_id)
                receipt = (
                    self._workflow_runtime_activation_data.receipt(
                        pending.input_dto,
                        pending.request_id,
                        access_token=grant.token,
                    )
                    if operation is ACTIVATE_WORKFLOW_RUNTIME
                    else self._dream_auto_repair_data.receipt(
                        pending.input_dto,
                        pending.request_id,
                        access_token=grant.token,
                    )
                    if operation is SETTLE_DREAM_AUTO_REPAIR
                    else self._story_workspace_output_data.receipt(
                        pending.input_dto,
                        pending.request_id,
                        access_token=grant.token,
                    )
                    if operation is STORE_STORY_WORKSPACE_OUTPUT
                    else self._story_workspace_artifact_data.receipt(
                        operation,
                        pending.input_dto,
                        pending.request_id,
                        access_token=grant.token,
                    )
                    if any(operation is item for item in (
                        ENSURE_STORY_WORKSPACE_EPISODE_AUTHORITY,
                        MARK_STORY_WORKSPACE_ARTIFACT_OUTPUT_READY,
                        MATERIALIZE_STORY_WORKSPACE_ARTIFACT_INDEX,
                    ))
                    else self._client.receipt(
                        operation,
                        pending.request_id,
                        access_token=grant.token,
                    )
                )
            except AdminDataError as error:
                raise AdminDataError(error.code, error.status_code, pending.request_id, True) from None
            if not isinstance(receipt, CommittedReceiptDTO):
                raise AdminDataError("ADMIN_WRITE_RESULT_UNKNOWN", 503, pending.request_id, True)
            return self._confirm(pending, receipt.result)
        pending = _PendingWrite(operation, input_dto, self._request_id_factory())
        self._pending = pending
        try:
            if operation is PERSIST_USER_MESSAGE:
                result = self._user_messages.persist(input_dto, pending.request_id, access_token=grant.token)
            elif operation is PERSIST_MESSAGE:
                require_workspace_capabilities(self._client, pending.request_id)
                result = self._chat.persist_message(input_dto, pending.request_id, access_token=grant.token)
            elif operation is ACTIVATE_WORKFLOW_RUNTIME:
                result = self._workflow_runtime_activation_data.activate(
                    input_dto,
                    pending.request_id,
                    access_token=grant.token,
                )
            elif operation is STORE_STORY_WORKSPACE_OUTPUT:
                result = self._story_workspace_output_data.store(
                    input_dto,
                    pending.request_id,
                    access_token=grant.token,
                )
            elif operation is SETTLE_DREAM_AUTO_REPAIR:
                result = self._dream_auto_repair_data.settle(
                    input_dto,
                    pending.request_id,
                    access_token=grant.token,
                )
            elif any(operation is item for item in (
                ENSURE_STORY_WORKSPACE_EPISODE_AUTHORITY,
                MARK_STORY_WORKSPACE_ARTIFACT_OUTPUT_READY,
                MATERIALIZE_STORY_WORKSPACE_ARTIFACT_INDEX,
            )):
                result = self._story_workspace_artifact_data.execute(
                    operation,
                    input_dto,
                    pending.request_id,
                    access_token=grant.token,
                )
            else:
                result = self._chat.update_session(input_dto, pending.request_id, access_token=grant.token)
        except AdminDataError as error:
            if not error.outcome_unknown:
                self._pending = None
            raise
        except Exception:
            raise AdminDataError("ADMIN_UNAVAILABLE", 503, pending.request_id, True) from None
        return self._confirm(pending, result)

    def _confirm(self, pending: _PendingWrite, result):
        if pending.operation is PERSIST_USER_MESSAGE:
            if result.message_id != pending.input_dto.message_id:
                raise invalid_response(pending.request_id, write=True)
            self._writes[result.message_id] = _UserWrite(pending.input_dto, pending.request_id, result)
        elif pending.operation is PERSIST_MESSAGE:
            if result.message_id != pending.input_dto.message_id:
                raise invalid_response(pending.request_id, write=True)
        elif pending.operation is STORE_STORY_WORKSPACE_OUTPUT:
            if result.chat_thread_id != self._resolution.thread_id:
                raise invalid_response(pending.request_id, write=True)
        elif pending.operation is SETTLE_DREAM_AUTO_REPAIR:
            if (
                result.message_id != pending.input_dto.message_id
                or result.status != pending.input_dto.status
            ):
                raise invalid_response(pending.request_id, write=True)
        elif pending.operation is ACTIVATE_WORKFLOW_RUNTIME:
            context = self._resolution.context
            if (
                context is None
                or result.thread_id != context.thread_id
                or result.workflow_run_id != context.workflow_run_id
                or result.runtime_plugin_lock_id
                != context.runtime_plugin_lock_id
            ):
                raise invalid_response(pending.request_id, write=True)
        elif pending.operation is ENSURE_STORY_WORKSPACE_EPISODE_AUTHORITY:
            if (
                result.authority.workflow_run_id
                != pending.input_dto.workflow_run_id
                or result.authority.story_slug != pending.input_dto.story_slug
                or result.authority.episode_code != pending.input_dto.episode_code
            ):
                raise invalid_response(pending.request_id, write=True)
        elif pending.operation is MARK_STORY_WORKSPACE_ARTIFACT_OUTPUT_READY:
            if result.workflow_run_id != pending.input_dto.workflow_run_id:
                raise invalid_response(pending.request_id, write=True)
        elif pending.operation is MATERIALIZE_STORY_WORKSPACE_ARTIFACT_INDEX:
            if (
                result.observation.run_id != pending.input_dto.workflow_run_id
                or result.observation.project_id
                != pending.input_dto.projection.source_project_id
            ):
                raise invalid_response(pending.request_id, write=True)
        else:
            # Session identity is mutable: A -> B -> A must write A again.
            self._session_write = (pending.input_dto, result)
        self._pending = None
        return result

    def close(self) -> None:
        with self._close_lock:
            with self._lock:
                if self._closed:
                    return
            # Stop new child requests and drain a provider call while the
            # grant and Admin HTTP resources are still valid.
            self._session_projection_broker.close()
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
