"""Server-owned identity for the local persistent Agent runtime.

Runtime placement describes where verified plugin bytes are materialized.  It
is deliberately independent from deployment labels such as development,
testing, or production: the same local persistent runtime contract is used in
every deployment that enables this backend.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class LocalRuntimePlacement:
    """Immutable placement facts shared by provisioning and activation."""

    runtime_environment_id: str = "ink-local"
    runtime_pool_id: str = "ink-local"
    runtime_node_id: str = "local"
    distribution_mode: Literal["local_persistent"] = "local_persistent"
    deployment_tier: Literal["local"] = "local"

    def __post_init__(self) -> None:
        if self.runtime_pool_id != self.runtime_environment_id:
            raise ValueError("local runtime pool must equal runtime environment")


__all__ = ["LocalRuntimePlacement"]
