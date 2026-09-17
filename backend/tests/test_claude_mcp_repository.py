"""Admin DTO adapter contracts for managed MCP persistence.

[Input] Exact Registry134-147 Pydantic operations and a scripted Admin client.
[Output] OAuth/delegation binding, DTO mapping, receipt recovery and DB-closure evidence.
[Pos] Provider-free Dream consumer tests; no SQL, ORM, pool or database connection.
[Sync] 2026-09-16: replace PostgreSQL repository tests with Admin DTO adapter contracts.
[Sync] 2026-09-16: include the retained credential compatibility module in the
                   production database-access source fence.
"""

from __future__ import annotations

import json
from pathlib import Path
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
from claude_mcp.repository import AdminManagedMcpRepository, McpDataAuthorization
from services.admin_data.errors import AdminDataError
from services.admin_data.managed_mcp_data import (
    CREATE_MANAGED_MCP_SERVER,
    GET_MANAGED_MCP_SERVER,
    LIST_MANAGED_MCP_SERVERS,
    MANAGED_MCP_OPERATIONS,
    MANAGED_MCP_SCHEMA_REQUIREMENTS,
    UPDATE_MANAGED_MCP_SERVER,
)
from services.admin_data.models import AbsentReceiptDTO, CommittedReceiptDTO


SERVER_ID = "123e4567-e89b-42d3-a456-426614174000"
THREAD_ID = "223e4567-e89b-42d3-a456-426614174000"
RUN_ID = "run_" + "a" * 32


def _server(**overrides: Any) -> dict[str, Any]:
    return {
        "id": SERVER_ID,
        "user_id": "7",
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
        "created_at": "2026-09-16T00:00:00Z",
        "updated_at": "2026-09-16T00:00:00Z",
        **overrides,
    }


class _AdminClient:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, Any, str, str]] = []
        self.supported = True
        self.fail_write_unknown = False
        self.receipt_committed = True

    def supports(self, operations, schemas) -> bool:
        assert operations == MANAGED_MCP_OPERATIONS
        assert schemas == MANAGED_MCP_SCHEMA_REQUIREMENTS
        return self.supported

    def execute(self, operation, input_dto, request_id, *, access_token):
        self.calls.append((operation, input_dto, request_id, access_token))
        if self.fail_write_unknown and operation.capability.kind == "write":
            raise AdminDataError(
                "ADMIN_WRITE_RESULT_UNKNOWN",
                503,
                request_id,
                outcome_unknown=True,
            )
        payload: dict[str, Any]
        if operation is LIST_MANAGED_MCP_SERVERS:
            payload = {"servers": [_server()]}
        elif operation is GET_MANAGED_MCP_SERVER:
            payload = {"server": _server()}
        elif operation is UPDATE_MANAGED_MCP_SERVER:
            payload = {"server": _server(config_revision=2, display_name="Beta")}
        else:
            payload = {"server": _server()}
        return operation.output_dto.model_validate(payload)

    def receipt(self, operation, request_id, *, access_token):
        assert access_token == "idg_runtime"
        if not self.receipt_committed:
            return AbsentReceiptDTO(
                request_id=request_id,
                status="absent",
                operation=operation.capability.name,
            )
        return CommittedReceiptDTO[operation.output_dto](
            request_id=request_id,
            status="committed",
            operation=operation.capability.name,
            result=operation.output_dto.model_validate(
                {"server": _server(config_revision=2, display_name="Recovered")}
            ),
        )


@pytest.mark.asyncio
async def test_capability_is_local_exact_catalog_check_under_explicit_authority() -> None:
    client = _AdminClient()
    repository = AdminManagedMcpRepository(client)
    with pytest.raises(ClaudeMcpError) as missing:
        await repository.capability_available()
    assert missing.value.code is ClaudeMcpErrorCode.IDENTITY_UNAVAILABLE

    with repository.authorize(McpDataAuthorization("7", "oauth_access")):
        assert await repository.capability_available() is True
        client.supported = False
        assert await repository.app_settings_capability_available() is False
    assert client.calls == []


@pytest.mark.asyncio
async def test_oauth_reads_use_actor_free_strict_dto_and_map_domain_records() -> None:
    client = _AdminClient()
    repository = AdminManagedMcpRepository(client)
    with repository.authorize(McpDataAuthorization("7", "oauth_access")):
        rows = await repository.list_servers("7")
        found = await repository.get_server("7", SERVER_ID)

    assert [row.server_key for row in rows] == ["alpha"]
    assert found is not None and found.remote_url == "https://mcp.example.test/mcp"
    assert [call[0] for call in client.calls] == [
        LIST_MANAGED_MCP_SERVERS,
        GET_MANAGED_MCP_SERVER,
    ]
    for _operation, input_dto, _request_id, token in client.calls:
        assert token == "oauth_access"
        assert input_dto.authority is None
        assert "actor" not in input_dto.model_dump()
        assert "user_id" not in input_dto.model_dump()


@pytest.mark.asyncio
async def test_runtime_write_carries_exact_thread_run_authority_and_dto_patch() -> None:
    client = _AdminClient()
    repository = AdminManagedMcpRepository(client)
    authorization = McpDataAuthorization(
        "7",
        "idg_runtime",
        thread_id=THREAD_ID,
        workflow_run_id=RUN_ID,
    )
    with repository.authorize(authorization):
        created = await repository.create_server(
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
        updated = await repository.update_server(
            "7",
            SERVER_ID,
            McpServerPatch(expected_revision=1, display_name="Beta"),
        )

    assert created.config_revision == 1
    assert updated.config_revision == 2 and updated.display_name == "Beta"
    create_call, update_call = client.calls
    assert create_call[0] is CREATE_MANAGED_MCP_SERVER
    assert update_call[0] is UPDATE_MANAGED_MCP_SERVER
    assert create_call[1].authority.model_dump() == {
        "thread_id": THREAD_ID,
        "workflow_run_id": RUN_ID,
    }
    assert update_call[1].model_dump(exclude={"authority"}) == {
        "server_id": SERVER_ID,
        "expected_revision": 1,
        "display_name": "Beta",
        "transport": None,
        "auth_kind": None,
        "remote_url": None,
        "stdio_profile_key": None,
        "enabled": None,
    }


@pytest.mark.asyncio
async def test_actor_mismatch_stops_before_admin_http() -> None:
    client = _AdminClient()
    repository = AdminManagedMcpRepository(client)
    with repository.authorize(McpDataAuthorization("7", "oauth_access")):
        with pytest.raises(ClaudeMcpError) as denied:
            await repository.list_servers("8")
    assert denied.value.code is ClaudeMcpErrorCode.IDENTITY_UNAVAILABLE
    assert client.calls == []


@pytest.mark.asyncio
async def test_unknown_write_reads_only_original_receipt_and_never_retries() -> None:
    client = _AdminClient()
    client.fail_write_unknown = True
    repository = AdminManagedMcpRepository(client)
    with repository.authorize(McpDataAuthorization("7", "idg_runtime")):
        recovered = await repository.update_server(
            "7", SERVER_ID, McpServerPatch(expected_revision=1, display_name="Beta")
        )
    assert recovered.display_name == "Recovered"
    assert len(client.calls) == 1

    client.receipt_committed = False
    with repository.authorize(McpDataAuthorization("7", "idg_runtime")):
        with pytest.raises(ClaudeMcpError) as unknown:
            await repository.update_server(
                "7", SERVER_ID, McpServerPatch(expected_revision=1, display_name="Beta")
            )
    assert unknown.value.code is ClaudeMcpErrorCode.SCHEMA_CAPABILITY_UNAVAILABLE
    assert len(client.calls) == 2


def test_registry134_147_contract_hashes_match_shared_admin_artifact() -> None:
    artifact_path = Path(__file__).resolve().parents[2] / "docs" / "architecture" / "admin-dream-operation-contracts.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    published = {item["capability"]["name"]: item["capability"] for item in artifact}
    for operation in MANAGED_MCP_OPERATIONS:
        assert published[operation.capability.name] == operation.capability.model_dump()


def test_production_managed_mcp_composition_contains_no_database_access() -> None:
    root = Path(__file__).resolve().parents[1]
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [
            root / "claude_mcp" / "repository.py",
            root / "claude_mcp" / "service.py",
            root / "claude_mcp" / "credentials.py",
            root / "script" / "import_claude_mcp_config.py",
        ]
    )
    forbidden = (
        "PostgresMcpRepository",
        "PostgresPool",
        "DATABASE_URL",
        "persistence.postgres",
        "persistence.config",
        "import database",
        "backend.database",
        "SELECT ",
        "INSERT ",
        "UPDATE ",
        "DELETE ",
    )
    assert not [value for value in forbidden if value in sources]
