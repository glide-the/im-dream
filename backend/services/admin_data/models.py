# [Sync] 2026-09-15: validate code-owned closed Deck deletion reasons alongside existing conflict revisions.
# [Input] Admin canonical authentication/service DTO definitions supplied on 2026-09-14.
# [Output] Strict Pydantic request/response DTOs, separate from database entities.
# [Pos] Unified Admin consumer wire-schema boundary, preserving canonical IDs as strings.
# [Sync] 2026-09-14: require operation/delegation discovery digests and retain only exact Deck conflict details.
"""Only exact Admin wire DTOs; no PostgresRow, ORM entity or column projection."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Identifier = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")]
OperationName = Annotated[str, Field(min_length=1)]
CanonicalUserId = Annotated[str, Field(pattern=r"^[1-9][0-9]{0,18}$")]
BrowserHandle = Annotated[str, Field(pattern=r"^dbr_[A-Za-z0-9_-]{43}$")]


class StrictDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, hide_input_in_errors=True)


class RequestDTO(StrictDTO):
    request_id: Identifier


class PrincipalDTO(StrictDTO):
    subject: str = Field(min_length=1, max_length=160)
    canonical_user_id: CanonicalUserId
    client_id: str = Field(min_length=1, max_length=160)
    scopes: list[str]
    status: Literal["active"]

    @field_validator("canonical_user_id")
    @classmethod
    def validate_canonical_id(cls, value: str) -> str:
        if int(value) > 9_223_372_036_854_775_807:
            raise ValueError("Invalid canonical user identifier")
        return value


class AuthClientsDTO(StrictDTO):
    browser: str = Field(min_length=1)
    device: str = Field(min_length=1)


class DelegationCapabilityDTO(StrictDTO):
    name: Literal["runtime-delegation.create", "runtime-delegation.renew", "runtime-delegation.revoke", "runtime-delegation.receipt"]
    method: Literal["GET", "POST"]
    path: str
    input_schema_version: Literal[1]
    output_schema_version: Literal[1]
    contract_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @field_validator("input_schema_version", "output_schema_version", mode="before")
    @classmethod
    def require_integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("Contract version must be an integer")
        return value


class AuthCapabilityDTO(StrictDTO):
    issuer: str
    jwks_uri: str
    algorithm: Literal["ES256"]
    resource: str
    clients: AuthClientsDTO
    scopes: list[str]
    delegations: list[DelegationCapabilityDTO]


class SchemaCapabilityDTO(StrictDTO):
    capability: str = Field(min_length=1)
    version: int = Field(ge=1)
    contract_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class OperationCapabilityDTO(StrictDTO):
    name: OperationName
    kind: Literal["read", "write"]
    user_scope: str | None
    background_scope: str | None
    input_schema_version: Literal[1]
    output_schema_version: Literal[1]
    contract_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @field_validator("input_schema_version", "output_schema_version", mode="before")
    @classmethod
    def require_integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("Contract version must be an integer")
        return value


class CapabilitiesDTO(StrictDTO):
    version: Literal["1"]
    auth: AuthCapabilityDTO
    schema_capabilities: list[SchemaCapabilityDTO]
    operations: list[OperationCapabilityDTO]


class BrowserExchangeDTO(RequestDTO):
    transaction_id: Identifier
    code: str = Field(min_length=1, max_length=2048, repr=False)
    code_verifier: str = Field(min_length=43, max_length=128, pattern=r"^[A-Za-z0-9._~-]+$", repr=False)
    redirect_uri: str = Field(min_length=1, max_length=2048)


class BrowserHandleRequestDTO(RequestDTO):
    handle: BrowserHandle = Field(repr=False)


class ExpiringDTO(StrictDTO):
    expires_at: datetime

    @field_validator("expires_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Expiry must have a timezone")
        return value


class BrowserHandleDTO(ExpiringDTO):
    handle: BrowserHandle = Field(repr=False)


class BrowserResolutionDTO(ExpiringDTO):
    access_token: str = Field(min_length=1, repr=False)
    principal: PrincipalDTO


class BrowserRevokedDTO(StrictDTO):
    revoked: Literal[True]


class DeckVersionConflictDetailsDTO(StrictDTO):
    current_draft_revision: int = Field(ge=0, le=9_007_199_254_740_991)
    current_version: int | None = Field(ge=0, le=9_007_199_254_740_991)


class DeckDeleteBlockedDetailsDTO(StrictDTO):
    reason: Literal["child_decks", "related_threads", "runtime_history", "referenced_records"]


class ErrorDTO(StrictDTO):
    code: Identifier
    message: str
    details: DeckVersionConflictDetailsDTO | DeckDeleteBlockedDetailsDTO | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_details_owner(cls, value):
        if isinstance(value, dict) and "details" in value:
            owner = {"DECK_VERSION_CONFLICT": DeckVersionConflictDetailsDTO,
                     "DECK_DELETE_BLOCKED": DeckDeleteBlockedDetailsDTO}.get(value.get("code"))
            if owner is None or value["details"] is None:
                raise ValueError("Unsupported domain error details")
            owner.model_validate(value["details"])
        return value


class ErrorEnvelopeDTO(RequestDTO):
    error: ErrorDTO


DataT = TypeVar("DataT")


class ResponseEnvelopeDTO(RequestDTO, Generic[DataT]):
    data: DataT


class AbsentReceiptDTO(RequestDTO):
    status: Literal["absent"]
    operation: OperationName


class CommittedReceiptDTO(RequestDTO, Generic[DataT]):
    status: Literal["committed"]
    operation: OperationName
    result: DataT
