# [Input] Registry104 default-plugin candidate, current OAuth and locally verified immutable evidence.
# [Output] Strict resolve/create/reconcile/provision consumers with original-request receipt recovery.
# [Pos] Deck-default Admin DTO boundary; Admin owns policy/transactions while Dream verifies shared artifact bytes and CLI.
# [Sync] 2026-09-15: replace the two public Dream PostgreSQL default-Deck paths without browser-authored evidence.
"""Typed Registry104 consumers for default Deck plugin resolution and writes."""

from __future__ import annotations

from typing import Literal

from .chat_models import ChatStrictDTO, EntityId
from .client import AdminDataClient, DomainOperation
from .deck_version_data import require_deck_capabilities
from .deck_version_models import Digest, SafeInteger
from .errors import AdminDataError, invalid_response
from .models import CommittedReceiptDTO, OperationCapabilityDTO


class DefaultPluginResolveInputDTO(ChatStrictDTO):
    pass


class DefaultPluginInstallationDTO(ChatStrictDTO):
    plugin_installation_id: EntityId
    package_name: EntityId
    marketplace: EntityId
    resolved_version: EntityId
    artifact_digest: Digest
    compatibility_json: str


class DefaultPluginResolveOutputDTO(ChatStrictDTO):
    installation: DefaultPluginInstallationDTO | None


class DefaultPluginEvidenceDTO(ChatStrictDTO):
    plugin_installation_id: EntityId
    package_name: EntityId
    resolved_version: EntityId
    artifact_digest: Digest


class DeckCreateInputDTO(ChatStrictDTO):
    name: str
    name_zh: str | None
    name_en: str | None
    description: str | None
    description_zh: str | None
    description_en: str | None
    icon: str | None
    color: str | None
    order_index: SafeInteger | None
    default_plugin_evidence: DefaultPluginEvidenceDTO


class DeckDefaultInputDTO(ChatStrictDTO):
    default_plugin_evidence: DefaultPluginEvidenceDTO


class DeckCreatedDTO(ChatStrictDTO):
    deck_id: EntityId


class DeckDefaultReconciledDTO(DeckCreatedDTO):
    reconciled: bool
    reason: Literal["default_created", "refs_preserved", "missing_ref"]


def _operation(name, kind, scope, input_dto, output_dto, digest):
    return DomainOperation(
        OperationCapabilityDTO(
            name=name,
            kind=kind,
            user_scope=scope,
            background_scope=None,
            input_schema_version=1,
            output_schema_version=1,
            contract_sha256=digest,
        ),
        input_dto,
        output_dto,
    )


RESOLVE_DEFAULT_PLUGIN = _operation(
    "deck.default-plugin.resolve",
    "read",
    "dream:read",
    DefaultPluginResolveInputDTO,
    DefaultPluginResolveOutputDTO,
    "9ae17f5c334a14f04363705b55701cbcc7ccd8a12070f9548adbf67746535b83",
)
CREATE_DECK = _operation(
    "deck.create",
    "write",
    "dream:write",
    DeckCreateInputDTO,
    DeckCreatedDTO,
    "8217131588b76f36b8705f4a4ee4dc609bda35970a292d93e2fead1a4b0cdcbb",
)
RECONCILE_DEFAULT_DECK = _operation(
    "deck.reconcile-default",
    "write",
    "dream:write",
    DeckDefaultInputDTO,
    DeckDefaultReconciledDTO,
    "0ae6b3b88a0d9e19c16c95b93f55504b3beb64a178c9ea78dc662d063954a6d3",
)
PROVISION_DEFAULT_DECK = _operation(
    "deck.provision-default",
    "write",
    "dream:write",
    DeckDefaultInputDTO,
    DeckCreatedDTO,
    "111cea42be2be64bd65e5206250078740db1f0886ad05585cb434da8d0185719",
)
DECK_DEFAULT_OPERATIONS = (
    RESOLVE_DEFAULT_PLUGIN,
    CREATE_DECK,
    RECONCILE_DEFAULT_DECK,
    PROVISION_DEFAULT_DECK,
)


class AdminDeckDefaultData:
    def __init__(self, client: AdminDataClient) -> None:
        self._client = client

    def _execute(self, operation, input_dto, request_id: str, access_token: str):
        require_deck_capabilities(self._client, request_id)
        return self._client.execute(
            operation,
            input_dto,
            request_id,
            access_token=access_token,
        )

    def _write(self, operation, input_dto, request_id: str, access_token: str):
        try:
            return self._execute(operation, input_dto, request_id, access_token)
        except AdminDataError as error:
            if not error.outcome_unknown:
                raise
        try:
            receipt = self._client.receipt(
                operation,
                request_id,
                access_token=access_token,
            )
        except AdminDataError as error:
            raise AdminDataError(
                error.code,
                error.status_code,
                request_id,
                True,
                error.details,
            ) from None
        if not isinstance(receipt, CommittedReceiptDTO):
            raise AdminDataError(
                "ADMIN_WRITE_RESULT_UNKNOWN",
                503,
                request_id,
                True,
            )
        if type(receipt.result) is not operation.output_dto:
            raise invalid_response(request_id, write=True)
        return receipt.result

    def resolve(
        self,
        input_dto: DefaultPluginResolveInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> DefaultPluginResolveOutputDTO:
        return self._execute(
            RESOLVE_DEFAULT_PLUGIN,
            input_dto,
            request_id,
            access_token,
        )

    def create(
        self,
        input_dto: DeckCreateInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> DeckCreatedDTO:
        return self._write(CREATE_DECK, input_dto, request_id, access_token)

    def reconcile(
        self,
        input_dto: DeckDefaultInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> DeckDefaultReconciledDTO:
        return self._write(
            RECONCILE_DEFAULT_DECK,
            input_dto,
            request_id,
            access_token,
        )

    def provision(
        self,
        input_dto: DeckDefaultInputDTO,
        request_id: str,
        *,
        access_token: str,
    ) -> DeckCreatedDTO:
        return self._write(
            PROVISION_DEFAULT_DECK,
            input_dto,
            request_id,
            access_token,
        )
