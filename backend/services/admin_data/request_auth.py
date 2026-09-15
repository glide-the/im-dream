# [Sync] 2026-09-15: register the OAuth-only owner-scoped Preflight read.
# [Sync] 2026-09-15: register the staged OAuth Preflight execute operation.
# [Sync] 2026-09-15: register full Workflow Run read/create/retry OAuth operations.
# [Sync] 2026-09-15: register launch metadata consumers; legacy endpoint wiring remains pending.
# [Sync] 2026-09-15: register nine OAuth-only invitation/friendship operations.
# [Sync] 2026-09-15: register four OAuth-only public Voice operations.
# [Sync] 2026-09-15: register five OAuth-only public Deck mutations.
# [Sync] 2026-09-15: register the OAuth-only owned Deck detail read.
# [Sync] 2026-09-15: register the OAuth-only owned/community Deck list read.
# [Sync] 2026-09-15: construct one OAuth-owned Editor runtime without projecting its credentials to stdio.
# [Input] Server-owned Admin client/verifier and explicit OAuth bearer credentials.
# [Output] Immutable request actors with canonical user IDs and separate typed profile reads.
# [Pos] Request authentication composition; no issuing, renewal, PG or ambient actor context.
# [Sync] 2026-09-15: register five capability-gated public Deck content-version operations.
# [Sync] 2026-09-15: register two OAuth-only user preference operations, separate from system policy.
# [Sync] 2026-09-15: register public refs list/prepare/replace with source-bound local verification.
# [Sync] 2026-09-15: register six typed public Session operations alongside Chat/profile/Workflow consumers.
# [Sync] 2026-09-15: create exact server-persistence purpose grants for immutable Workflow turn bindings.
# [Sync] 2026-09-15: register OAuth-only default Workspace ensure independently of Thread lookup.
# [Sync] 2026-09-15: share the Run operation tuple with the registered public cancel consumer.
# [Sync] 2026-09-15: register fail/envelope consumer types; launch production identity wiring remains pending.
# [Sync] 2026-09-15: provide request-bound Workflow provenance for immutable public Chat turn snapshots.
# [Sync] 2026-09-15: register OAuth and persistence-grant SystemConfig consumers.
# [Sync] 2026-09-14: own production shared request identity/profile connections; full BFF/runtime migration stays active.
from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock

from .chat_data import CHAT_OPERATIONS
from .client import AdminDataClient
from .config import AdminDataConfig
from .errors import AdminDataError, invalid_response
from .jwt_verifier import AdminJWTVerifier
from .profile_data import AdminProfileData, CURRENT_PROFILE, UserProfileDTO
from .workflow_data import AdminWorkflowData, AdminWorkflowResolution, RESOLVE_WORKFLOW_CONTEXT
from .delegation import AdminDelegationCreator, AdminRuntimeClient, DelegationCreateInputDTO, RuntimeHttpConfig
from .editor_runtime import AdminEditorRuntime
from .turn_persistence import AdminTurnPersistence
from .user_message_data import PERSIST_USER_MESSAGE
from .session_data import SESSION_OPERATIONS
from .deck_version_data import DECK_VERSION_OPERATIONS
from .preferences_data import PREFERENCES_OPERATIONS
from .deck_refs_data import DECK_REFS_OPERATIONS
from .social_data import SOCIAL_OPERATIONS
from .voice_data import VOICE_OPERATIONS
from .deck_mutation_data import DECK_MUTATION_OPERATIONS
from .deck_detail_data import READ_DECK_DETAIL
from .deck_list_data import LIST_DECKS
from .preflight_data import EXECUTE_PREFLIGHT, READ_PREFLIGHT
from .run_data import RUN_OPERATIONS
from .launch_metadata_data import LAUNCH_METADATA_OPERATIONS
from .workspace_data import ENSURE_DEFAULT_WORKSPACE
from .system_config_data import SYSTEM_CONFIG_OPERATIONS


@dataclass(frozen=True, slots=True)
class AdminRequestActor:
    subject: str
    canonical_user_id: str
    client_id: str
    scopes: frozenset[str]
    issued_at: int
    expires_at: int
    access_token: str = field(repr=False)

    def current_user_projection(self) -> dict:
        return {
            "user_id": int(self.canonical_user_id),
            "sub": self.subject, "client_id": self.client_id,
            "scopes": self.scopes, "iat": self.issued_at, "exp": self.expires_at,
            "_admin_actor": self,
        }


class AdminRequestAuth:
    """Application-owned connections; each request checks current Admin identity."""

    def __init__(self, config: AdminDataConfig, *, client: AdminDataClient | None = None, verifier: AdminJWTVerifier | None = None) -> None:
        self.client = client or AdminDataClient(config, operations=(*CHAT_OPERATIONS, *SESSION_OPERATIONS, *DECK_VERSION_OPERATIONS, *PREFERENCES_OPERATIONS, *SYSTEM_CONFIG_OPERATIONS, *DECK_REFS_OPERATIONS, *SOCIAL_OPERATIONS, *VOICE_OPERATIONS, *DECK_MUTATION_OPERATIONS, *LAUNCH_METADATA_OPERATIONS, *RUN_OPERATIONS, READ_DECK_DETAIL, LIST_DECKS, READ_PREFLIGHT, EXECUTE_PREFLIGHT, ENSURE_DEFAULT_WORKSPACE, CURRENT_PROFILE, RESOLVE_WORKFLOW_CONTEXT, PERSIST_USER_MESSAGE))
        self._verifier = verifier or AdminJWTVerifier(config)
        self._owns_client = client is None
        self._owns_verifier = verifier is None
        self._profile = AdminProfileData(self.client)
        self._workflow = AdminWorkflowData(self.client)
        self._delegations = AdminDelegationCreator(self.client)
        self._runtime_http_config = RuntimeHttpConfig.from_server_config(config)
        self._capabilities_ready = False
        self._lock = RLock()

    def _ensure_capabilities(self, request_id: str) -> None:
        with self._lock:
            if not self._capabilities_ready or not self.client.capabilities_ready:
                self.client.capabilities(request_id)
                self._capabilities_ready = True

    def authenticate(self, access_token: str, request_id: str, *, required_scopes: frozenset[str]) -> AdminRequestActor:
        claims = self._verifier.verify(access_token, required_scopes=required_scopes)
        self._ensure_capabilities(request_id)
        principal = self.client.principal(access_token, request_id)
        if (
            principal.subject != claims.subject
            or principal.client_id != claims.client_id
            or frozenset(principal.scopes) != claims.scopes
        ):
            raise invalid_response(request_id)
        return AdminRequestActor(
            claims.subject, principal.canonical_user_id, claims.client_id,
            claims.scopes, claims.issued_at, claims.expires_at, access_token,
        )

    def current_profile(self, actor: AdminRequestActor, request_id: str) -> UserProfileDTO:
        if "dream:read" not in actor.scopes:
            raise AdminDataError("INSUFFICIENT_SCOPE", 403, request_id)
        profile = self._profile.current(request_id, access_token=actor.access_token)
        if profile.id != actor.canonical_user_id:
            raise invalid_response(request_id)
        return profile

    def close(self) -> None:
        try:
            if self._owns_client:
                self.client.close()
        finally:
            if self._owns_verifier:
                self._verifier.close()

    def workflow_context(self, actor: AdminRequestActor, thread_id: str, request_id: str) -> AdminWorkflowResolution:
        if "dream:read" not in actor.scopes:
            raise AdminDataError("INSUFFICIENT_SCOPE", 403, request_id)
        try:
            return self._workflow.resolve(thread_id, request_id, access_token=actor.access_token, canonical_user_id=actor.canonical_user_id)
        except AdminDataError:
            # A failed fresh capability fetch clears the client's advertisement.
            # The next request must initialize it again instead of keeping an
            # obsolete ready flag for other Chat/profile operations.
            with self._lock:
                self._capabilities_ready = False
            raise

    def turn_persistence(self, actor: AdminRequestActor, resolution: AdminWorkflowResolution, request_id: str) -> AdminTurnPersistence:
        if not {"dream:read", "dream:write"} <= actor.scopes:
            raise AdminDataError("INSUFFICIENT_SCOPE", 403, request_id)
        context = resolution.context_for(actor_id=actor.canonical_user_id, thread_id=resolution.thread_id)
        requested = DelegationCreateInputDTO(purpose="server-persistence", thread_id=resolution.thread_id,
            run_id=context.workflow_run_id if context is not None else None, editor_session_id=None,
            scopes=["dream:read", "dream:write"])
        try:
            grant = self._delegations.create(requested, access_token=actor.access_token, request_id=request_id)
        except AdminDataError:
            with self._lock:
                self._capabilities_ready = False
            raise
        return AdminTurnPersistence(resolution, grant, self.client,
            runtime_client_factory=lambda: AdminRuntimeClient(self._runtime_http_config))

    def editor_runtime(self, actor: AdminRequestActor, resolution: AdminWorkflowResolution,
        request_id: str, *, initial_session_id: str | None) -> AdminEditorRuntime:
        if not {"dream:read", "dream:write"} <= actor.scopes:
            raise AdminDataError("INSUFFICIENT_SCOPE", 403, request_id)
        try:
            return AdminEditorRuntime(
                resolution,
                actor_id=actor.canonical_user_id,
                access_token=actor.access_token,
                delegation_creator=self._delegations,
                runtime_http_config=self._runtime_http_config,
                initial_session_id=initial_session_id,
                initial_request_id=request_id,
            )
        except AdminDataError:
            with self._lock:
                self._capabilities_ready = False
            raise
