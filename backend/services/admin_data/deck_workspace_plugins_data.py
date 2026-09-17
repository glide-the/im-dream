# [Input] Admin Registry106 Thread-bound workspace plugin metadata and an exact actor grant.
# [Output] Strict Deck ref and Story adapter status snapshot bound to one actor, Thread and profile.
# [Pos] Agent workspace metadata consumer; Admin owns ORM/access and Dream owns artifact/filesystem policy.
# [Sync] 2026-09-15: pin Admin d7ba9c6 and expose no PostgreSQL, path, artifact bytes or Runtime selector.
"""Typed Registry106 consumer for immutable workspace plugin metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import TypeAdapter

from .chat_models import ChatStrictDTO, EntityId
from .client import AdminDataClient, DomainOperation
from .deck_refs_data import ArtifactDigest, InstallationStatus, PgOrder
from .errors import AdminDataError, invalid_response
from .models import CanonicalUserId, OperationCapabilityDTO, PrincipalDTO
from .workflow_data import require_workflow_capabilities


WorkspaceProfile = Literal["standard", "story_workspace"]


class DeckWorkspacePluginsInputDTO(ChatStrictDTO):
    thread_id: EntityId
    profile: WorkspaceProfile


class WorkspacePluginDTO(ChatStrictDTO):
    plugin_installation_id: EntityId
    package_spec: EntityId
    package_name: EntityId
    marketplace: EntityId
    resolved_version: EntityId
    artifact_digest: ArtifactDigest
    installation_status: InstallationStatus


class WorkspaceDeckPluginRefDTO(WorkspacePluginDTO):
    order_index: PgOrder


class StoryWorkspaceAdapterCandidateDTO(ChatStrictDTO):
    latest_status: InstallationStatus | None
    ready: WorkspacePluginDTO | None


class DeckWorkspacePluginsOutputDTO(ChatStrictDTO):
    thread_id: EntityId
    deck_id: EntityId | None
    refs: list[WorkspaceDeckPluginRefDTO]
    story_workspace_adapter: StoryWorkspaceAdapterCandidateDTO | None


RESOLVE_DECK_WORKSPACE_PLUGINS = DomainOperation(
    OperationCapabilityDTO(
        name="deck-workspace-plugins.resolve",
        kind="read",
        user_scope="dream:read",
        background_scope=None,
        input_schema_version=1,
        output_schema_version=1,
        contract_sha256=(
            "79eca8295a3a1611b2459af26f0a9e05"
            "dd01eae97bdd4928d1982e77a524425e"
        ),
    ),
    DeckWorkspacePluginsInputDTO,
    DeckWorkspacePluginsOutputDTO,
)
DECK_WORKSPACE_PLUGIN_OPERATIONS = (RESOLVE_DECK_WORKSPACE_PLUGINS,)


@dataclass(frozen=True, slots=True)
class AdminDeckWorkspacePluginsResolution:
    canonical_user_id: str
    thread_id: str
    profile: WorkspaceProfile
    snapshot: DeckWorkspacePluginsOutputDTO

    def __post_init__(self) -> None:
        PrincipalDTO.validate_canonical_id(
            TypeAdapter(CanonicalUserId).validate_python(
                self.canonical_user_id,
                strict=True,
            )
        )
        if self.snapshot.thread_id != self.thread_id:
            raise ValueError("Workspace plugin snapshot does not match Thread")

    def snapshot_for(
        self,
        *,
        actor_id: str,
        thread_id: str,
        profile: WorkspaceProfile,
        deck_id: str,
    ) -> DeckWorkspacePluginsOutputDTO:
        if (
            self.canonical_user_id != str(actor_id)
            or self.thread_id != thread_id
            or self.profile != profile
        ):
            raise AdminDataError("DREAM_DELEGATION_ENTITY_DENIED", 403)
        if self.snapshot.deck_id != deck_id:
            raise AdminDataError("ADMIN_RESPONSE_INVALID", 503)
        return self.snapshot


class AdminDeckWorkspacePluginsProvider:
    """Marker for server owners that can read Registry106 metadata."""

    def workspace_plugins(
        self,
        *,
        actor_id: str,
        thread_id: str,
        profile: WorkspaceProfile,
    ) -> AdminDeckWorkspacePluginsResolution:
        raise NotImplementedError


class AdminDeckWorkspacePluginsData:
    def __init__(
        self,
        client: AdminDataClient,
        *,
        canonical_user_id: str,
    ) -> None:
        self._client = client
        self._canonical_user_id = PrincipalDTO.validate_canonical_id(
            TypeAdapter(CanonicalUserId).validate_python(
                canonical_user_id,
                strict=True,
            )
        )

    def resolve(
        self,
        input_dto: DeckWorkspacePluginsInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> AdminDeckWorkspacePluginsResolution:
        require_workflow_capabilities(self._client, request_id)
        result = self._client.execute(
            RESOLVE_DECK_WORKSPACE_PLUGINS,
            input_dto,
            request_id,
            access_token=access_token,
        )
        ref_ids = [ref.plugin_installation_id for ref in result.refs]
        adapter = result.story_workspace_adapter
        if (
            result.thread_id != input_dto.thread_id
            or len(ref_ids) != len(set(ref_ids))
            or [ref.order_index for ref in result.refs]
            != sorted(ref.order_index for ref in result.refs)
            or (
                result.deck_id is None
                and (result.refs or adapter is not None)
            )
            or (input_dto.profile == "standard" and adapter is not None)
            or (
                input_dto.profile == "story_workspace"
                and result.deck_id is not None
                and adapter is None
            )
            or (
                adapter is not None
                and adapter.ready is not None
                and adapter.ready.installation_status != "ready"
            )
        ):
            raise invalid_response(request_id)
        return AdminDeckWorkspacePluginsResolution(
            canonical_user_id=self._canonical_user_id,
            thread_id=input_dto.thread_id,
            profile=input_dto.profile,
            snapshot=result,
        )
