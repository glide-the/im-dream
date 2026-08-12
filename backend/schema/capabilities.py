"""Read-only PostgreSQL schema capability checks shared by runtime and import tools."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Final, Mapping


SCHEMA_CAPABILITIES_RELATION: Final = "drizzle.schema_capabilities"
UNIFIED_DREAM_CAPABILITY: Final = "dream.schema.unified.v1"
REQUIRED_RUNTIME_CAPABILITIES: Final[Mapping[str, int]] = {
    UNIFIED_DREAM_CAPABILITY: 1,
    "dream.workflow.thread-lookup.v1": 1,
    "dream.story-artifact-contract.v2": 2,
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class SchemaCapabilityError(RuntimeError):
    """The database cannot prove the schema features required by Dream."""

    code = "DREAM_SCHEMA_CAPABILITY_MISSING"


@dataclass(frozen=True)
class SchemaAuthorityReceipt:
    authority: str
    capabilities: tuple[tuple[str, int], ...] = ()
    contract_sha256: str | None = None

    def safe_dict(self) -> dict[str, object]:
        return {
            "authority": self.authority,
            "capabilities": [
                {"capability": capability, "version": version}
                for capability, version in self.capabilities
            ],
            "contractSha256": self.contract_sha256,
        }


def _values(row: Any) -> tuple[Any, ...]:
    if isinstance(row, Mapping):
        return tuple(row.values())
    return tuple(row)


def _relation_exists(connection: Any, relation: str) -> bool:
    row = connection.execute("SELECT to_regclass(%s)", (relation,)).fetchone()
    return row is not None and _values(row)[0] is not None


def inspect_schema_authority(
    connection: Any,
    *,
    required_capabilities: Mapping[str, int],
) -> SchemaAuthorityReceipt:
    """Inspect capabilities without creating, altering, or migrating any object."""

    required = dict(required_capabilities)
    if not required or any(
        not isinstance(name, str)
        or not name
        or not isinstance(version, int)
        or version < 1
        for name, version in required.items()
    ):
        raise ValueError("required_capabilities must contain positive versions")

    if not _relation_exists(connection, SCHEMA_CAPABILITIES_RELATION):
        raise SchemaCapabilityError()
    rows = connection.execute(
        "SELECT capability, version, contract_sha256 "
        "FROM drizzle.schema_capabilities "
        "WHERE capability = ANY(%s) ORDER BY capability",
        (list(required),),
    ).fetchall()
    observed: dict[str, tuple[int, str]] = {}
    for row in rows:
        capability, version, contract_sha256 = _values(row)
        observed[str(capability)] = (int(version), str(contract_sha256))
    if set(observed) != set(required) or any(
        observed[name][0] < minimum or not _SHA256.fullmatch(observed[name][1])
        for name, minimum in required.items()
    ):
        raise SchemaCapabilityError()
    hashes = {contract_sha256 for _, contract_sha256 in observed.values()}
    if len(hashes) != 1:
        raise SchemaCapabilityError()
    return SchemaAuthorityReceipt(
        authority="admin-drizzle",
        capabilities=tuple((name, observed[name][0]) for name in sorted(observed)),
        contract_sha256=next(iter(hashes)),
    )


__all__ = [
    "REQUIRED_RUNTIME_CAPABILITIES",
    "SCHEMA_CAPABILITIES_RELATION",
    "SchemaAuthorityReceipt",
    "SchemaCapabilityError",
    "UNIFIED_DREAM_CAPABILITY",
    "inspect_schema_authority",
]
