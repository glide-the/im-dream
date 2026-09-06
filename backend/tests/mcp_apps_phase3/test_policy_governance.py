"""MCP Apps versioned policy governance contracts.

[Input] Server-owned policy mappings across valid and invalid transitions.
[Output] Strict state, canonical server-key, path/TTL rejection, and production-off assertions.
[Pos] Provider-free Phase 3 Python contract coverage; no database or plugin process.
[Sync] 2026-09-06: align policy server refs with canonical keys and reject invalid view TTLs.
"""

import pytest

from backend.claude_mcp.contracts import McpAppsRuntimePolicy
from backend.routers import claude_mcp as claude_mcp_router
from backend.tests.mcp_apps_phase1.test_connection_view import POLICY, service


def test_policy_v1_preserves_independent_states_and_production_off():
    parsed = McpAppsRuntimePolicy.from_mapping(POLICY)
    assert parsed.revision == 7
    assert parsed.default.low_risk_tool_calls is False
    assert parsed.desired.low_risk_tool_calls is True
    assert parsed.effective.low_risk_tool_calls is True
    subject, _ = service()
    static = subject.mcp_apps_static_view().to_dict()
    assert static["productionAppsEffective"] is False
    assert static["policy"] == parsed.state_dict()


@pytest.mark.parametrize(
    "change",
    [
        {"version": 2},
        {"revision": 0},
        {"default": {"resourceReads": True, "lowRiskToolCalls": False}},
        {
            "desired": {"resourceReads": False, "lowRiskToolCalls": False},
            "effective": {"resourceReads": True, "lowRiskToolCalls": False},
        },
    ],
)
def test_invalid_version_or_state_fails_closed(change):
    candidate = {**POLICY, **change}
    with pytest.raises(ValueError):
        McpAppsRuntimePolicy.from_mapping(candidate)


def test_missing_server_policy_defaults_to_deny():
    parsed = McpAppsRuntimePolicy.deny_all()
    assert parsed.servers == {}
    assert parsed.default == parsed.desired == parsed.effective


def test_policy_accepts_canonical_colon_server_key_and_rejects_paths():
    server_policy = POLICY["servers"]["official-basic"]
    with_colon = {
        **POLICY,
        "servers": {"official:basic-v1": server_policy},
    }
    assert "official:basic-v1" in McpAppsRuntimePolicy.from_mapping(with_colon).servers

    for invalid in ("official/basic", "../official-basic", "official%2Fbasic"):
        with pytest.raises(ValueError):
            McpAppsRuntimePolicy.from_mapping(
                {**POLICY, "servers": {invalid: server_policy}}
            )


@pytest.mark.parametrize("configured", ["", "0", "-1", "nan", "inf", "-inf"])
def test_connection_view_ttl_rejects_non_positive_or_non_finite_values(
    monkeypatch, configured
):
    monkeypatch.setenv("INK_MCP_APPS_CONNECTION_VIEW_TTL_SECONDS", configured)
    with pytest.raises(claude_mcp_router.ClaudeMcpError) as caught:
        claude_mcp_router._mcp_apps_view_ttl_seconds()
    assert caught.value.code.value == "CLAUDE_MCP_APP_RUNTIME_DENIED"
