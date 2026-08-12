from __future__ import annotations

from dataclasses import dataclass

import pytest

from schema.capabilities import (
    REQUIRED_RUNTIME_CAPABILITIES,
    SchemaCapabilityError,
    UNIFIED_DREAM_CAPABILITY,
    inspect_schema_authority,
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
            requested = set(parameters[0])
            return _Cursor(
                [
                    (name, version, contract_hash)
                    for name, (version, contract_hash) in sorted(
                        (self.capabilities or {}).items()
                    )
                    if name in requested
                ]
            )
        raise AssertionError(f"unexpected schema authority query: {query}")


_HASH = "a" * 64


def test_capability_authority_allows_higher_unrelated_global_head() -> None:
    connection = _Connection(
        capabilities={
            **{name: (version, _HASH) for name, version in REQUIRED_RUNTIME_CAPABILITIES.items()},
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
