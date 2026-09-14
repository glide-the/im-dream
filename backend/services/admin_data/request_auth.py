# [Input] Server-owned Admin client/verifier and explicit OAuth bearer credentials.
# [Output] Immutable request actors with canonical user IDs and separate typed profile reads.
# [Pos] Request authentication composition; no issuing, renewal, PG or ambient actor context.
# [Sync] 2026-09-15: provide request-bound Workflow provenance for immutable public Chat turn snapshots.
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
        self.client = client or AdminDataClient(config, operations=(*CHAT_OPERATIONS, CURRENT_PROFILE, RESOLVE_WORKFLOW_CONTEXT))
        self._verifier = verifier or AdminJWTVerifier(config)
        self._owns_client = client is None
        self._owns_verifier = verifier is None
        self._profile = AdminProfileData(self.client)
        self._workflow = AdminWorkflowData(self.client)
        self._capabilities_ready = False
        self._lock = RLock()

    def _ensure_capabilities(self, request_id: str) -> None:
        with self._lock:
            if not self._capabilities_ready:
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
