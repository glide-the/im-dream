# [Input] Admin userProfileDto.ts and the actual user-profile.current operation artifact.
# [Output] Strict current-user DTO consumer and the existing Dream public profile projection.
# [Pos] Profile domain boundary; identity is derived only from the authenticated Admin caller.
# [Sync] 2026-09-14: pin the candidate contract and preserve decimal IDs and ISO microseconds.
from __future__ import annotations

import re
from typing import Literal

from pydantic import field_validator

from .chat_models import validate_timestamp_text
from .client import AdminDataClient, DomainOperation
from .models import CanonicalUserId, OperationCapabilityDTO, PrincipalDTO, StrictDTO


class ProfileInputDTO(StrictDTO):
    pass


class UserProfileDTO(StrictDTO):
    id: CanonicalUserId
    email: str
    display_name: str | None
    avatar_url: str | None
    role: str
    created_at: str | None
    updated_at: str | None
    auth_providers: list[Literal["google", "credential"]]
    _timestamps = field_validator("created_at", "updated_at")(validate_timestamp_text)

    @field_validator("id")
    @classmethod
    def validate_user_id(cls, value: str) -> str:
        return PrincipalDTO.validate_canonical_id(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        # Exact z.email() pattern from Admin's operation JSON schema.
        if re.fullmatch(r"(?!\.)(?!.*\.\.)([A-Za-z0-9_'+\-\.]*)[A-Za-z0-9_+-]@([A-Za-z0-9][A-Za-z0-9\-]*\.)+[A-Za-z]{2,}", value) is None:
            raise ValueError("Invalid profile email")
        return value

    def dream_public_profile(self) -> dict:
        return {
            "id": int(self.id), "email": self.email,
            "display_name": self.display_name, "avatar_url": self.avatar_url,
            "role": self.role, "created_at": self.created_at,
        }


class ProfileResultDTO(StrictDTO):
    user: UserProfileDTO


CURRENT_PROFILE = DomainOperation(
    OperationCapabilityDTO(
        name="user-profile.current", kind="read", user_scope="dream:read",
        background_scope=None, input_schema_version=1, output_schema_version=1,
        contract_sha256="01011316efa10475dd1d1aa8856c82cb17ddbeb404125ebcd80af5f250f2a9d0",
    ),
    ProfileInputDTO, ProfileResultDTO,
)


class AdminProfileData:
    def __init__(self, client: AdminDataClient) -> None:
        self._client = client

    def current(self, request_id: str, *, access_token: str) -> UserProfileDTO:
        return self._client.execute(CURRENT_PROFILE, ProfileInputDTO(), request_id, access_token=access_token).user
