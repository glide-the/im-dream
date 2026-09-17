# [Input] Registry107 DTO consumer, capability catalog and fixed Admin scope responses.
# [Output] Exact hash, strict selectors, actor/Run/Thread binding and public PG fence evidence.
# [Pos] Provider-free managed MCP scope contract test; no PostgreSQL, MCP provider or Runtime.
# [Sync] 2026-09-15: consume Registry107 through the current turn authority.
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from claude_agent import service as service_module
from services.admin_data.config import AdminDataConfig
from services.admin_data.errors import AdminDataError
from services.admin_data.request_auth import AdminRequestAuth
from services.admin_data.workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS
from services.admin_data.workflow_managed_mcp_scope_data import (
    AdminWorkflowManagedMcpScopeData,
    AdminWorkflowManagedMcpScopeProvider,
    AdminWorkflowManagedMcpScopeResolution,
    RESOLVE_WORKFLOW_MANAGED_MCP_SCOPE,
    WORKFLOW_MANAGED_MCP_SCOPE_OPERATIONS,
    WorkflowManagedMcpScopeInputDTO,
    WorkflowManagedMcpScopeOutputDTO,
)
from story_workspace.contracts import StoryWorkspaceDreamRunContext

RUN_ID = "run_" + "a" * 32


def _context() -> StoryWorkspaceDreamRunContext:
    return StoryWorkspaceDreamRunContext(
        workflow_run_id=RUN_ID,
        thread_id="thread-1",
        deck_id="deck-1",
        deck_plugin_id="ink.dream.story-workflow",
        deck_plugin_version="1.0.0",
        deck_plugin_binding_id="binding-1",
        binding_revision=1,
        deck_runtime_snapshot_id="snapshot-1",
        runtime_plugin_lock_id="lock-1",
    )


def _output(**updates) -> WorkflowManagedMcpScopeOutputDTO:
    return WorkflowManagedMcpScopeOutputDTO.model_validate(
        {
            "thread_id": "thread-1",
            "workflow_run_id": RUN_ID,
            "workspace_id": "workspace-1",
            **updates,
        }
    )


def _data(output=None):
    client = Mock()
    client.capabilities.return_value = SimpleNamespace(
        schema_capabilities=list(WORKFLOW_SCHEMA_REQUIREMENTS)
    )
    client.execute.return_value = output or _output()
    return AdminWorkflowManagedMcpScopeData(
        client,
        canonical_user_id="42",
    ), client


def test_registry107_contract_and_strict_dtos_are_exact():
    assert WORKFLOW_MANAGED_MCP_SCOPE_OPERATIONS == (
        RESOLVE_WORKFLOW_MANAGED_MCP_SCOPE,
    )
    assert RESOLVE_WORKFLOW_MANAGED_MCP_SCOPE.capability.contract_sha256 == (
        "c996f3bf5fc2bfcc8fa9a7c3b90ae039"
        "800109a56ec2159882cfd921d6f74bdc"
    )
    with pytest.raises(ValidationError):
        WorkflowManagedMcpScopeInputDTO.model_validate(
            {
                "thread_id": "thread-1",
                "workflow_run_id": RUN_ID,
                "workspace_id": "caller",
            }
        )
    with pytest.raises(ValidationError):
        WorkflowManagedMcpScopeOutputDTO.model_validate(
            {**_output().model_dump(), "database_url": "private"}
        )


def test_resolve_checks_capability_and_binds_actor_run_thread():
    data, client = _data()
    selection = WorkflowManagedMcpScopeInputDTO(
        thread_id="thread-1",
        workflow_run_id=RUN_ID,
    )
    resolution = data.resolve(
        selection,
        "scope-request",
        access_token="idg-token",
    )
    assert resolution.workspace_for(
        actor_id="42",
        thread_id="thread-1",
        workflow_run_id=RUN_ID,
    ) == "workspace-1"
    client.capabilities.assert_called_once_with("scope-request")
    client.execute.assert_called_once_with(
        RESOLVE_WORKFLOW_MANAGED_MCP_SCOPE,
        selection,
        "scope-request",
        access_token="idg-token",
    )
    for values in (
        {"actor_id": "43", "thread_id": "thread-1", "workflow_run_id": RUN_ID},
        {"actor_id": "42", "thread_id": "other", "workflow_run_id": RUN_ID},
        {"actor_id": "42", "thread_id": "thread-1", "workflow_run_id": "run_" + "b" * 32},
    ):
        with pytest.raises(AdminDataError, match="DREAM_DELEGATION_ENTITY_DENIED"):
            resolution.workspace_for(**values)


@pytest.mark.parametrize(
    "output",
    [_output(thread_id="other"), _output(workflow_run_id="run_" + "b" * 32)],
)
def test_resolve_rejects_mismatched_admin_entities(output):
    data, _ = _data(output)
    with pytest.raises(AdminDataError, match="ADMIN_RESPONSE_INVALID"):
        data.resolve(
            WorkflowManagedMcpScopeInputDTO(
                thread_id="thread-1",
                workflow_run_id=RUN_ID,
            ),
            "scope-request",
            access_token="idg-token",
        )


class _Provider(AdminWorkflowManagedMcpScopeProvider):
    def managed_mcp_workspace_scope(self, **_kwargs):
        return AdminWorkflowManagedMcpScopeResolution("42", _output())


def test_public_scope_resolver_uses_provider_with_dream_pg_fenced(monkeypatch):
    assert service_module._resolve_managed_mcp_workspace_scope_sync(
        actor_id="42",
        context=_context(),
        provider=_Provider(),
    ) == "workspace-1"


def test_production_request_owner_registers_registry107_operation():
    owner = AdminRequestAuth(
        AdminDataConfig(
            base_url="https://admin.example",
            issuer="https://admin.example/api/auth",
            resource="https://dream.example/api",
            service_client_id="dream-service",
            service_secret="s" * 32,
        )
    )
    try:
        assert (
            owner.client._operations[
                RESOLVE_WORKFLOW_MANAGED_MCP_SCOPE.capability.name
            ]
            is RESOLVE_WORKFLOW_MANAGED_MCP_SCOPE
        )
    finally:
        owner.close()
