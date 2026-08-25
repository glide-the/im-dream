"""PostgreSQL managed MCP repository contracts with injected fake UoWs.

[Input] Scripted PostgreSQL rows and actor/workspace/CAS inputs.
[Output] Exact capability gating, scoped SQL, CRUD, uniqueness, and revision failure evidence.
[Pos] Provider-free persistence tests; no database connection or runtime DDL.
[Sync] 2026-08-25: define the Admin-owned managed MCP table consumption contract.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from types import SimpleNamespace
from typing import Any

import pytest

from claude_mcp.contracts import (
    ClaudeMcpError,
    ClaudeMcpErrorCode,
    McpAuthKind,
    McpScope,
    McpServerCreate,
    McpServerPatch,
    McpTransport,
)
from claude_mcp.repository import PostgresMcpRepository


@dataclass
class _Cursor:
    rows: list[dict[str, Any]]

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return list(self.rows)


class _Connection:
    def __init__(self, handler: Callable[[str, tuple[Any, ...]], list[dict[str, Any]]]):
        self.handler = handler
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def execute(self, query: str, parameters=()):
        params = tuple(parameters)
        self.calls.append((query, params))
        return _Cursor(self.handler(query, params))


class _Uow:
    def __init__(self, connection: _Connection) -> None:
        self.connection = connection
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query, parameters=()):
        return self.connection.execute(query, parameters)

    def commit(self):
        self.committed = True


def _row(**overrides: Any) -> dict[str, Any]:
    return {
        "id": "server-1",
        "user_id": 7,
        "workspace_id": None,
        "scope": "user",
        "server_key": "alpha",
        "display_name": "Alpha",
        "transport": "streamable_http",
        "remote_url": "https://mcp.example.test/mcp",
        "stdio_profile_key": None,
        "auth_kind": "none",
        "enabled": True,
        "config_revision": 1,
        "credential_revision": 0,
        "credential_id": None,
        "credential_configured": False,
        "created_at": "2026-08-25T00:00:00+00:00",
        "updated_at": "2026-08-25T00:00:00+00:00",
        **overrides,
    }


def _repository(connection: _Connection) -> PostgresMcpRepository:
    return PostgresMcpRepository(
        unit_of_work_factory=lambda **_kwargs: _Uow(connection),
        expected_contract_sha256="a" * 64,
    )


def test_capability_requires_exact_hash_and_never_issues_ddl() -> None:
    connection = _Connection(
        lambda query, _params: (
            [{"version": 1, "contract_sha256": "a" * 64}]
            if "mcp:capability" in query
            else []
        )
    )

    repository = _repository(connection)
    assert repository.capability_available_sync() is True
    assert repository.capability_available_sync() is True
    assert sum("mcp:capability" in query for query, _ in connection.calls) == 1
    assert all(
        not any(keyword in call[0].upper() for keyword in ("CREATE ", "ALTER ", "DROP "))
        for call in connection.calls
    )

    drifted = _Connection(
        lambda query, _params: (
            [{"version": 1, "contract_sha256": "b" * 64}]
            if "mcp:capability" in query
            else []
        )
    )
    assert _repository(drifted).capability_available_sync() is False


def test_list_and_get_are_actor_and_workspace_scoped_reads() -> None:
    connection = _Connection(
        lambda query, params: (
            [_row()]
                if "mcp:list" in query or ("mcp:get" in query and params[2] == "7")
            else []
        )
    )
    repository = _repository(connection)

    assert [item.server_key for item in repository.list_servers_sync("7")] == ["alpha"]
    assert repository.get_server_sync("7", "server-1").server_key == "alpha"
    assert repository.get_server_sync("8", "server-1") is None

    list_query, list_params = next(call for call in connection.calls if "mcp:list" in call[0])
    get_query, get_params = next(call for call in connection.calls if "mcp:get" in call[0])
    assert "server.user_id = %s::bigint" in list_query
    assert "server.user_id = %s::bigint" in get_query
    assert list_params[0] == "7" and get_params[:3] == (
        "server-1", "server-1", "7"
    )


def test_create_update_delete_use_transactions_and_cas_revision() -> None:
    def handler(query: str, _params: tuple[Any, ...]):
        if "mcp:create" in query:
            return [_row()]
        if "mcp:update-lock" in query:
            return [_row()]
        if "mcp:update */" in query:
            return [_row(config_revision=2)]
        if "mcp:delete-lock" in query:
            return [_row(config_revision=2)]
        if "mcp:delete */" in query:
            return [{"id": "server-1"}]
        if "mcp:workspace-owner" in query:
            return [{"owned": True}]
        return []

    connection = _Connection(handler)
    repository = _repository(connection)
    created = repository.create_server_sync(
        "7",
        McpServerCreate(
            server_key="alpha",
            display_name="Alpha",
            transport=McpTransport.STREAMABLE_HTTP,
            auth_kind=McpAuthKind.NONE,
            scope=McpScope.USER,
            remote_url="https://mcp.example.test/mcp",
        ),
    )
    updated = repository.update_server_sync(
        "7", "server-1", McpServerPatch(expected_revision=1, enabled=False)
    )
    removed = repository.delete_server_sync("7", "server-1", expected_revision=2)

    assert created.config_revision == 1
    assert updated.config_revision == 2
    assert removed.id == "server-1"
    write_queries = [query for query, _ in connection.calls if "mcp:" in query and not query.lstrip().upper().startswith("SELECT")]
    assert all("user_id" in query for query in write_queries)
    assert any("config_revision = %s" in query for query in write_queries)


def test_transport_or_auth_change_revokes_bound_credential_and_snapshot() -> None:
    def handler(query: str, _params: tuple[Any, ...]):
        if "mcp:update-lock" in query:
            return [_row(
                credential_revision=3,
                credential_id="credential-old",
                credential_configured=True,
            )]
        if "mcp:update */" in query:
            return [_row(
                remote_url="https://new.example.test/mcp",
                config_revision=2,
                credential_revision=0,
                credential_id=None,
                credential_configured=False,
            )]
        return []

    connection = _Connection(handler)
    updated = _repository(connection).update_server_sync(
        "7",
        "server-1",
        McpServerPatch(
            expected_revision=1,
            remote_url="https://new.example.test/mcp",
        ),
    )
    queries = [query for query, _ in connection.calls]
    assert any("mcp:update-credential-clear" in query for query in queries)
    assert any("mcp:update-snapshot-clear" in query for query in queries)
    assert updated.credential_configured is False
    assert updated.credential_revision == 0


def test_cas_miss_and_workspace_ownership_fail_closed() -> None:
    connection = _Connection(
        lambda query, _params: [_row()] if "mcp:update-lock" in query else []
    )
    repository = _repository(connection)

    with pytest.raises(ClaudeMcpError) as conflict:
        repository.update_server_sync(
            "7", "server-1", McpServerPatch(expected_revision=9, enabled=False)
        )
    assert conflict.value.code is ClaudeMcpErrorCode.SERVER_REVISION_CONFLICT

    with pytest.raises(ClaudeMcpError) as ownership:
        repository.create_server_sync(
            "7",
            McpServerCreate(
                server_key="workspace-alpha",
                display_name="Workspace Alpha",
                transport=McpTransport.STDIO,
                auth_kind=McpAuthKind.NONE,
                scope=McpScope.WORKSPACE,
                workspace_id="foreign-workspace",
                stdio_profile_key="safe-profile",
            ),
        )
    assert ownership.value.code is ClaudeMcpErrorCode.SERVER_OWNERSHIP_CONFLICT


def test_credential_delete_then_reauth_precisely_invalidates_old_revision_cache() -> None:
    old_snapshot = {
        "status": "complete",
        "inventory": {"tools": [{"name": "stale"}], "resources": [], "prompts": []},
        "safe_error_code": None,
        "discovered_at": "2026-08-25T00:00:00+00:00",
    }
    snapshots = [old_snapshot]

    def handler(query: str, _params: tuple[Any, ...]):
        if "mcp:credential-delete-lock" in query:
            return [_row(credential_revision=1, credential_id="credential-old", credential_configured=True)]
        if "mcp:credential-upsert" in query:
            return [{
                "id": "credential-new", "server_id": "server-1", "kind": "oauth",
                "ciphertext": "cipher", "iv": "iv", "tag": "tag",
                "fingerprint": "fingerprint", "key_version": 1,
                "credential_revision": 1, "expires_at": None,
            }]
        if "mcp:credential-snapshot-invalidate" in query:
            snapshots.clear()
            return []
        if "mcp:discovery-get" in query:
            return list(snapshots)
        return []

    connection = _Connection(handler)
    repository = _repository(connection)
    logged_out = repository.delete_credential_sync("7", "server-1")
    credential = repository.upsert_credential_sync(
        "7",
        "server-1",
        kind="oauth",
        envelope=SimpleNamespace(
            ciphertext="cipher", iv="iv", tag="tag",
            fingerprint="fingerprint", key_version=1,
        ),
    )
    reauthed = replace(
        logged_out,
        credential_id=credential.id,
        credential_configured=True,
        credential_revision=credential.credential_revision,
    )
    assert credential.credential_revision == 1
    assert repository.get_discovery_snapshot_sync("7", reauthed) is None
    invalidations = [
        query for query, _ in connection.calls
        if "mcp:credential-snapshot-invalidate" in query
    ]
    assert len(invalidations) == 2


def test_existing_success_receipt_preserves_nullable_target() -> None:
    connection = _Connection(
        lambda query, _params: ([{
            "state": "imported",
            "target_server_id": None,
            "canonical_config_sha256": "b" * 64,
        }] if "mcp:import-lock" in query else [])
    )
    receipt = _repository(connection).import_server_sync(
        "7",
        McpServerCreate(
            server_key="alpha",
            display_name="Alpha",
            transport=McpTransport.STREAMABLE_HTTP,
            auth_kind=McpAuthKind.NONE,
            remote_url="https://mcp.example.test/mcp",
        ),
        "a" * 64,
        "b" * 64,
    )
    assert receipt.state == "noop"
    assert receipt.target_server_id is None
