# [Input] Consume read-only Admin schema capability inspectors with injected PostgreSQL rows.
# [Output] Verify runtime authority and exact managed-MCP/resource-Observer/Runtime contracts.
# [Pos] Provider-free schema capability consumer tests in backend/tests.
# [Sync] 2026-08-28: require the exact Claude Agent resource and Claude Code Runtime hashes.

from __future__ import annotations

from dataclasses import dataclass

import pytest
from schema.capabilities import (
    CLAUDE_AGENT_RESOURCE_OBSERVER_CAPABILITY,
    CLAUDE_AGENT_RESOURCE_OBSERVER_CONTRACT_SHA256,
    CLAUDE_AGENT_RESOURCE_OBSERVER_VERSION,
    CLAUDE_CODE_RUNTIME_CONFIG_CAPABILITY,
    CLAUDE_CODE_RUNTIME_CONFIG_CONTRACT_SHA256,
    MANAGED_MCP_RESOURCES_CAPABILITY,
    MANAGED_MCP_RESOURCES_CONTRACT_SHA256,
    MANAGED_MCP_RESOURCES_VERSION,
    REQUIRED_RUNTIME_CAPABILITIES,
    UNIFIED_DREAM_CAPABILITY,
    SchemaCapabilityError,
    claude_agent_resource_observer_capability_available,
    inspect_schema_authority,
    managed_mcp_resources_capability_available,
)


@dataclass
class _Cursor:
    rows: list[tuple[object, ...]]

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return list(self.rows)


class _Connection:
    def __init__(
        self,
        *,
        capabilities: dict[str, tuple[int, str]] | None = None,
    ) -> None:
        self.capabilities = capabilities
        self.queries: list[str] = []

    def execute(self, query: str, parameters=()):
        self.queries.append(query)
        if "to_regclass" in query:
            relation = parameters[0]
            if relation == "drizzle.schema_capabilities":
                return _Cursor([(relation if self.capabilities is not None else None,)])
        if "FROM drizzle.schema_capabilities" in query:
            requested_raw = parameters[0]
            requested = (
                {requested_raw}
                if isinstance(requested_raw, str)
                else set(requested_raw)
            )
            exact_mcp_query = "SELECT version, contract_sha256" in query
            return _Cursor(
                [
                    ((version, contract_hash) if exact_mcp_query else (name, version, contract_hash))
                    for name, (version, contract_hash) in sorted(
                        (self.capabilities or {}).items()
                    )
                    if name in requested
                ]
            )
        raise AssertionError(f"unexpected schema authority query: {query}")


_HASH = "a" * 64


def _required_capabilities() -> dict[str, tuple[int, str]]:
    return {
        name: (
            version,
            CLAUDE_AGENT_RESOURCE_OBSERVER_CONTRACT_SHA256
            if name == CLAUDE_AGENT_RESOURCE_OBSERVER_CAPABILITY
            else CLAUDE_CODE_RUNTIME_CONFIG_CONTRACT_SHA256
            if name == CLAUDE_CODE_RUNTIME_CONFIG_CAPABILITY
            else _HASH,
        )
        for name, version in REQUIRED_RUNTIME_CAPABILITIES.items()
    }


def test_capability_authority_allows_higher_unrelated_global_head() -> None:
    connection = _Connection(
        capabilities={
            **_required_capabilities(),
            "billing.unrelated.v99": (99, "b" * 64),
        }
    )

    receipt = inspect_schema_authority(
        connection,
        required_capabilities=REQUIRED_RUNTIME_CAPABILITIES,
    )

    assert receipt.authority == "admin-drizzle"
    assert receipt.contract_sha256 == _HASH
    assert dict(receipt.capabilities) == dict(REQUIRED_RUNTIME_CAPABILITIES)
    assert all(query.lstrip().upper().startswith("SELECT") for query in connection.queries)


@pytest.mark.parametrize(
    "connection",
    [
        _Connection(),
        _Connection(capabilities={UNIFIED_DREAM_CAPABILITY: (0, _HASH)}),
        _Connection(capabilities={UNIFIED_DREAM_CAPABILITY: (1, "not-a-hash")}),
        _Connection(
            capabilities={
                name: (version, "a" * 64 if index == 0 else "b" * 64)
                for index, (name, version) in enumerate(REQUIRED_RUNTIME_CAPABILITIES.items())
            }
        ),
    ],
)
def test_missing_or_inconsistent_authority_fails_closed(connection: _Connection) -> None:
    with pytest.raises(SchemaCapabilityError):
        inspect_schema_authority(
            connection,
            required_capabilities=REQUIRED_RUNTIME_CAPABILITIES,
        )
    assert all("alembic" not in query.casefold() for query in connection.queries)


def test_managed_mcp_capability_requires_the_exact_admin_hash() -> None:
    exact = _Connection(
        capabilities={
            MANAGED_MCP_RESOURCES_CAPABILITY: (
                MANAGED_MCP_RESOURCES_VERSION,
                MANAGED_MCP_RESOURCES_CONTRACT_SHA256,
            )
        }
    )
    drifted = _Connection(
        capabilities={
            MANAGED_MCP_RESOURCES_CAPABILITY: (
                MANAGED_MCP_RESOURCES_VERSION,
                "b" * 64,
            )
        }
    )
    newer_version = _Connection(
        capabilities={
            MANAGED_MCP_RESOURCES_CAPABILITY: (
                MANAGED_MCP_RESOURCES_VERSION + 1,
                MANAGED_MCP_RESOURCES_CONTRACT_SHA256,
            )
        }
    )

    assert managed_mcp_resources_capability_available(exact) is True
    assert managed_mcp_resources_capability_available(drifted) is False
    assert managed_mcp_resources_capability_available(newer_version) is False
    assert MANAGED_MCP_RESOURCES_CONTRACT_SHA256 == (
        "746dfcb1343c485bee9fb7cc3fa363424db4a66ad31cd6824ed2024be049614a"
    )


def test_resource_observer_capability_requires_exact_version_and_hash() -> None:
    exact = _Connection(
        capabilities={
            CLAUDE_AGENT_RESOURCE_OBSERVER_CAPABILITY: (
                CLAUDE_AGENT_RESOURCE_OBSERVER_VERSION,
                CLAUDE_AGENT_RESOURCE_OBSERVER_CONTRACT_SHA256,
            )
        }
    )
    drifted = _Connection(
        capabilities={
            CLAUDE_AGENT_RESOURCE_OBSERVER_CAPABILITY: (
                CLAUDE_AGENT_RESOURCE_OBSERVER_VERSION,
                "b" * 64,
            )
        }
    )

    assert claude_agent_resource_observer_capability_available(exact) is True
    assert claude_agent_resource_observer_capability_available(drifted) is False
