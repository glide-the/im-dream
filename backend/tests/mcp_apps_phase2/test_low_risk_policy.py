"""Server-owned MCP Apps low-risk policy contracts.

[Input] Actor-scoped records, discovery inventories, and versioned policy fixtures.
[Output] Positive low-risk projection plus pre-decryption denial/revision evidence.
[Pos] Provider-free Phase 2 backend tests; Node owns actual tools/call execution.
[Sync] 2026-09-06: prove annotations alone never authorize an App tool call.
[Sync] 2026-09-06: intersect low-risk policy with the actor's connection App choice.
[Sync] 2026-09-06: accept missing optional MCP risk hints only when the server positive list explicitly classifies the tool; explicit unsafe hints still veto.
"""

from datetime import datetime, timezone

import pytest

from backend.claude_mcp.contracts import ClaudeMcpError, ClaudeMcpErrorCode
from backend.claude_mcp.service import ClaudeMcpService
from backend.tests.mcp_apps_phase1.test_connection_view import (
    INVENTORY,
    POLICY,
    SERVER,
    RecordingLoader,
    Repository,
)


def _service(policy, inventory=INVENTORY):
    class InventoryRepository(Repository):
        async def get_discovery_snapshot(self, actor_id, record):
            assert actor_id == record.user_id
            return inventory

    loader = RecordingLoader()
    return ClaudeMcpService(
        repository=InventoryRepository(),
        discovery=object(),
        oauth=object(),
        runtime_snapshot_loader=loader,
        mcp_apps_policy_provider=lambda: policy,
    ), loader


@pytest.mark.asyncio
async def test_positive_low_risk_tool_is_projected_from_policy_and_safe_inventory():
    service, loader = _service(POLICY)
    view = await service.mcp_apps_connection_view(
        SERVER.user_id,
        SERVER.server_key,
        SERVER.workspace_id,
        expected_config_revision=SERVER.config_revision,
        expected_credential_revision=SERVER.credential_revision,
        expected_policy_revision=7,
        ttl_seconds=10,
        now=datetime(2026, 9, 6, tzinfo=timezone.utc),
    )

    payload = view.to_dict()
    assert payload["appCallableLowRiskTools"] == ["get-time"]
    assert set(payload) == {
        "actorScope",
        "workspaceScope",
        "serverId",
        "serverRef",
        "transportKind",
        "enabled",
        "configRevision",
        "credentialRevision",
        "appSettingsRevision",
        "expiresAt",
        "allowedTools",
        "allowedResources",
        "appCallableLowRiskTools",
        "policy",
        "connectionProfile",
    }
    assert "inventory" not in payload and "annotations" not in payload
    assert loader.calls == 1


@pytest.mark.asyncio
async def test_phase1_state_keeps_resources_but_projects_no_callable_tools():
    phase1_policy = {
        **POLICY,
        "revision": 8,
        "desired": {"resourceReads": True, "lowRiskToolCalls": False},
        "effective": {"resourceReads": True, "lowRiskToolCalls": False},
    }
    official_inventory = {
        **INVENTORY,
        "inventory": {
            **INVENTORY["inventory"],
            "tools": [{"name": "get-time"}],
        },
    }
    service, _ = _service(phase1_policy, official_inventory)
    view = await service.mcp_apps_connection_view(
        SERVER.user_id,
        SERVER.server_key,
        SERVER.workspace_id,
        expected_config_revision=4,
        expected_credential_revision=2,
        expected_policy_revision=8,
        ttl_seconds=10,
    )
    assert view.allowed_resources == ("ui://get-time/mcp-app.html",)
    assert view.allowed_tools == ("get-time",)
    assert view.app_callable_low_risk_tools == ()


@pytest.mark.asyncio
async def test_upstream_annotation_without_server_positive_list_is_denied_before_decrypt():
    policy = {
        **POLICY,
        "revision": 8,
        "servers": {
            SERVER.server_key: {
                "allowedTools": [],
                "allowedResources": ["ui://get-time/mcp-app.html"],
                "appCallableLowRiskTools": [],
            }
        },
    }
    service, loader = _service(policy)
    with pytest.raises(ClaudeMcpError) as caught:
        await service.mcp_apps_connection_view(
            SERVER.user_id,
            SERVER.server_key,
            SERVER.workspace_id,
            expected_config_revision=4,
            expected_credential_revision=2,
            expected_policy_revision=8,
            ttl_seconds=10,
        )
    assert caught.value.code is ClaudeMcpErrorCode.INVENTORY_UNAVAILABLE
    assert loader.calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "annotations",
    [
        {"readOnlyHint": False, "destructiveHint": False},
        {"read_only": False, "destructive": False},
        {"readOnlyHint": True, "destructiveHint": True},
        {"read_only": True, "destructive": True},
        {"readOnlyHint": True, "confirmationRequired": True},
    ],
)
async def test_explicitly_unsafe_or_confirmation_required_tools_stay_denied(
    annotations,
):
    inventory = {
        **INVENTORY,
        "inventory": {
            **INVENTORY["inventory"],
            "tools": [{"name": "get-time", "annotations": annotations}],
        },
    }
    service, loader = _service(POLICY, inventory)
    view = await service.mcp_apps_connection_view(
        SERVER.user_id,
        SERVER.server_key,
        SERVER.workspace_id,
        expected_config_revision=4,
        expected_credential_revision=2,
        expected_policy_revision=7,
        ttl_seconds=10,
    )
    assert view.allowed_tools == ("get-time",)
    assert view.app_callable_low_risk_tools == ()
    assert loader.calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("annotations", [{}, None])
async def test_server_positive_list_classifies_tools_without_optional_risk_hints(
    annotations,
):
    tool = {"name": "get-time"}
    if annotations is not None:
        tool["annotations"] = annotations
    inventory = {
        **INVENTORY,
        "inventory": {
            **INVENTORY["inventory"],
            "tools": [tool],
        },
    }
    service, loader = _service(POLICY, inventory)
    view = await service.mcp_apps_connection_view(
        SERVER.user_id,
        SERVER.server_key,
        SERVER.workspace_id,
        expected_config_revision=4,
        expected_credential_revision=2,
        expected_policy_revision=7,
        ttl_seconds=10,
    )
    assert view.app_callable_low_risk_tools == ("get-time",)
    assert loader.calls == 1


@pytest.mark.asyncio
async def test_policy_revision_conflict_precedes_config_and_credential_projection():
    service, loader = _service(POLICY)
    with pytest.raises(ClaudeMcpError) as caught:
        await service.mcp_apps_connection_view(
            SERVER.user_id,
            SERVER.server_key,
            SERVER.workspace_id,
            expected_config_revision=4,
            expected_credential_revision=2,
            expected_policy_revision=6,
            ttl_seconds=10,
        )
    assert caught.value.code is ClaudeMcpErrorCode.APP_RUNTIME_REVISION_CONFLICT
    assert loader.calls == 0


@pytest.mark.asyncio
async def test_policy_provider_is_read_on_every_connection_view():
    current = dict(POLICY)
    service, loader = _service(current)
    await service.mcp_apps_connection_view(
        SERVER.user_id,
        SERVER.server_key,
        SERVER.workspace_id,
        expected_config_revision=4,
        expected_credential_revision=2,
        expected_policy_revision=7,
        ttl_seconds=10,
    )
    current["revision"] = 8
    with pytest.raises(ClaudeMcpError) as caught:
        await service.mcp_apps_connection_view(
            SERVER.user_id,
            SERVER.server_key,
            SERVER.workspace_id,
            expected_config_revision=4,
            expected_credential_revision=2,
            expected_policy_revision=7,
            ttl_seconds=10,
        )
    assert caught.value.code is ClaudeMcpErrorCode.APP_RUNTIME_REVISION_CONFLICT
    assert loader.calls == 1
