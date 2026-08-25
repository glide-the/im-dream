"""Read-only PostgreSQL schema capability checks shared by runtime and import tools.

[Input] Admin-owned ``drizzle.schema_capabilities`` rows.
[Output] Validated schema authority receipts and exact feature capability constants.
[Pos] No-DDL Dream boundary for shared PostgreSQL schema publication.
[Sync] 2026-08-19: add the exact ClaudePlugin Remote Marketplace v1 contract hash.
[Sync] 2026-08-25: add the exact Admin-published managed MCP Resources v1 capability check.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Final, Mapping


SCHEMA_CAPABILITIES_RELATION: Final = "drizzle.schema_capabilities"
UNIFIED_DREAM_CAPABILITY: Final = "dream.schema.unified.v1"
DREAM_WORKFLOW_NO_CONTINUING_CAPABILITY: Final = (
    "dream.workflow.no-continuing.v1"
)
DECK_CONTENT_VERSIONS_CAPABILITY: Final = "dream.deck-content-versions.v1"
CLAUDE_PLUGIN_REMOTE_MARKETPLACE_CAPABILITY: Final = (
    "dream.claude-plugin.remote-marketplace.v1"
)
CLAUDE_PLUGIN_REMOTE_MARKETPLACE_CONTRACT_SHA256: Final = (
    "d215cb2764f656ab32e364a4900b3aac73fca60c77ef4c9f3a914fd192a8c314"
)
MANAGED_MCP_RESOURCES_CAPABILITY: Final = "dream.managed-mcp-resources.v1"
MANAGED_MCP_RESOURCES_VERSION: Final = 1
MANAGED_MCP_RESOURCES_CONTRACT_SHA256: Final = (
    "746dfcb1343c485bee9fb7cc3fa363424db4a66ad31cd6824ed2024be049614a"
)
REQUIRED_RUNTIME_CAPABILITIES: Final[Mapping[str, int]] = {
    UNIFIED_DREAM_CAPABILITY: 1,
    "dream.workflow.thread-lookup.v1": 1,
    "dream.story-artifact-contract.v2": 2,
    DREAM_WORKFLOW_NO_CONTINUING_CAPABILITY: 1,
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


def managed_mcp_resources_capability_available(connection: Any) -> bool:
    """Return whether the exact Admin-published managed MCP contract exists.

    This helper issues one read-only query and deliberately treats every
    database/catalog failure as unavailable. Callers never migrate or infer
    compatibility from the global Drizzle journal head.
    """

    try:
        row = connection.execute(
            "SELECT version, contract_sha256 "
            "FROM drizzle.schema_capabilities WHERE capability = %s",
            (MANAGED_MCP_RESOURCES_CAPABILITY,),
        ).fetchone()
    except Exception:
        return False
    if row is None:
        return False
    if isinstance(row, Mapping):
        version = row.get("version")
        contract_sha256 = row.get("contract_sha256")
    else:
        try:
            version, contract_sha256 = row[0], row[1]
        except (IndexError, KeyError, TypeError):
            return False
    return (
        isinstance(version, int)
        and version == MANAGED_MCP_RESOURCES_VERSION
        and contract_sha256 == MANAGED_MCP_RESOURCES_CONTRACT_SHA256
    )


__all__ = [
    "CLAUDE_PLUGIN_REMOTE_MARKETPLACE_CAPABILITY",
    "CLAUDE_PLUGIN_REMOTE_MARKETPLACE_CONTRACT_SHA256",
    "DECK_CONTENT_VERSIONS_CAPABILITY",
    "DREAM_WORKFLOW_NO_CONTINUING_CAPABILITY",
    "MANAGED_MCP_RESOURCES_CAPABILITY",
    "MANAGED_MCP_RESOURCES_CONTRACT_SHA256",
    "MANAGED_MCP_RESOURCES_VERSION",
    "REQUIRED_RUNTIME_CAPABILITIES",
    "SCHEMA_CAPABILITIES_RELATION",
    "SchemaAuthorityReceipt",
    "SchemaCapabilityError",
    "UNIFIED_DREAM_CAPABILITY",
    "inspect_schema_authority",
    "managed_mcp_resources_capability_available",
]
