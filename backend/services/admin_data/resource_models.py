# [Input] Admin resourceDto.ts and the existing positive-safe-integer/exact-memory contract.
# [Output] Closed resource policy state DTOs; no database row or effective-policy calculation.
# [Pos] Strict consumer projections for the Admin resource-policy domain.
# [Sync] 2026-09-14: preserve configured/not_configured/invalid states separately from transport failure.
"""Resource wire projections, independent of Admin ORM entities."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, RootModel, field_validator, model_validator

from .models import StrictDTO

# JSON/TypeScript serialization boundaries from the published resource contract.
PositiveSafeInteger = Annotated[int, Field(ge=1, le=9_007_199_254_740_991)]


class ResourcePolicyReadInputDTO(StrictDTO):
    pass


class DesiredResourcePolicyDTO(StrictDTO):
    schemaVersion: Literal[1]
    revision: PositiveSafeInteger
    maxConcurrentRuns: PositiveSafeInteger
    runMemoryBudgetMib: PositiveSafeInteger
    memoryReserveMib: PositiveSafeInteger
    retryAfterSeconds: PositiveSafeInteger
    claudeCodeEffortLevel: Literal["low", "medium", "high", "xhigh", "max"] | None

    @field_validator("schemaVersion", mode="before")
    @classmethod
    def require_integer_schema_version(cls, value):
        if type(value) is not int:
            raise ValueError("Schema version must be an integer")
        return value

    @model_validator(mode="after")
    def require_exact_combined_memory(self) -> DesiredResourcePolicyDTO:
        if (self.runMemoryBudgetMib + self.memoryReserveMib) * 1_048_576 > 9_007_199_254_740_991:
            raise ValueError("Combined memory exceeds the exact JSON integer range")
        return self


class ConfiguredResourcePolicyDTO(StrictDTO):
    status: Literal["configured"]
    value: DesiredResourcePolicyDTO
    updated_at: datetime

    @field_validator("updated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timestamp must have a timezone")
        return value


class UnconfiguredResourcePolicyDTO(StrictDTO):
    status: Literal["not_configured", "invalid"]
    value: None
    updated_at: None


ResourcePolicyReadOutputDTO = Annotated[
    ConfiguredResourcePolicyDTO | UnconfiguredResourcePolicyDTO,
    Field(discriminator="status"),
]


class ResourcePolicyReadResultDTO(RootModel[ResourcePolicyReadOutputDTO]):
    model_config = ConfigDict(strict=True, frozen=True, hide_input_in_errors=True)
