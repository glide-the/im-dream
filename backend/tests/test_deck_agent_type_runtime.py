# [Input] Registry128 Runtime candidate and mocked shared-artifact/CLI verification results.
# [Output] Exact Registry129 evidence or closed Runtime-unavailable failures.
# [Pos] Provider-free local-verifier test; no PostgreSQL, network or real CLI.
# [Sync] 2026-09-16: verify the Dream-owned filesystem boundary for Agent type.
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from services.admin_data.deck_plugin_binding_data import (
    AgentTypeRuntimeCandidateDTO,
)
from services.deck import agent_type_runtime


def candidate() -> AgentTypeRuntimeCandidateDTO:
    return AgentTypeRuntimeCandidateDTO(
        deck_plugin_id="example.story",
        deck_plugin_version="1.0.0",
        runtime_plugin_lock_id="rpl_" + "a" * 32,
        plugin_installation_id="cpi_" + "b" * 32,
        package_spec="example.runtime",
        package_name="runtime",
        marketplace="platform-builtin",
        resolved_version="1.0.0",
        artifact_digest="sha256:" + "c" * 64,
        compatibility_json="{}",
    )


def test_verified_artifact_manifest_and_cli_produce_only_immutable_evidence(
    monkeypatch,
):
    value = candidate()
    monkeypatch.setattr(
        agent_type_runtime.PluginInstallService,
        "verify_installation_artifact",
        lambda record: True,
    )
    monkeypatch.setattr(
        agent_type_runtime.PluginInstallService,
        "check_cli_compatibility",
        lambda record: True,
    )
    monkeypatch.setattr(
        agent_type_runtime.artifact_store,
        "get_artifact",
        lambda *args: SimpleNamespace(path=Path("/derived/shared/artifact")),
    )
    monkeypatch.setattr(
        agent_type_runtime,
        "read_manifest",
        lambda path: {"name": "runtime"},
    )
    result = agent_type_runtime.verify_agent_type_runtime(value)
    assert result.model_dump() == {
        "plugin_installation_id": value.plugin_installation_id,
        "package_spec": value.package_spec,
        "resolved_version": value.resolved_version,
        "artifact_digest": value.artifact_digest,
        "has_manifest": True,
    }
    assert "artifact_path" not in result.model_dump()


@pytest.mark.parametrize("failed_gate", ["artifact", "cli", "manifest"])
def test_each_local_verification_gate_fails_closed(monkeypatch, failed_gate):
    monkeypatch.setattr(
        agent_type_runtime.PluginInstallService,
        "verify_installation_artifact",
        lambda record: failed_gate != "artifact",
    )
    monkeypatch.setattr(
        agent_type_runtime.PluginInstallService,
        "check_cli_compatibility",
        lambda record: failed_gate != "cli",
    )
    monkeypatch.setattr(
        agent_type_runtime.artifact_store,
        "get_artifact",
        lambda *args: SimpleNamespace(path=Path("/derived/shared/artifact")),
    )
    monkeypatch.setattr(
        agent_type_runtime,
        "read_manifest",
        lambda path: None if failed_gate == "manifest" else {"name": "runtime"},
    )
    with pytest.raises(agent_type_runtime.AgentTypeRuntimeUnavailable):
        agent_type_runtime.verify_agent_type_runtime(candidate())


def test_public_agent_type_closure_has_no_database_or_legacy_provisioner_symbols():
    backend_root = Path(__file__).resolve().parents[1]
    targets = (
        backend_root / "routers" / "deck_plugin_binding.py",
        backend_root / "services" / "deck" / "agent_type_runtime.py",
    )
    forbidden_imports = {
        "database",
        "backend.database",
        "services.deck_plugin.binding_service",
        "backend.services.deck_plugin.binding_service",
        "services.deck_plugin.selection_validation_service",
        "backend.services.deck_plugin.selection_validation_service",
        "services.story_workspace.dream_launch_infrastructure",
        "backend.services.story_workspace.dream_launch_infrastructure",
    }
    forbidden_names = {
        "_binding_db",
        "_binding_service",
        "_selection_service",
        "BindingService",
        "SelectionValidationService",
        "DreamRuntimeProvisioningService",
        "get_db",
    }
    for path in targets:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports = {
            name.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for name in node.names
        } | {
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        names = {
            node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
        } | {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
        }
        assert imports.isdisjoint(forbidden_imports), path
        assert names.isdisjoint(forbidden_names), path
