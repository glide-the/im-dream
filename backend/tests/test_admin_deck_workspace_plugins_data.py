# [Sync] 2026-09-17: exercise domain gates through the reusable validated capability snapshot.
# [Input] Registry106 DTO consumer, capability catalog and fixed Admin metadata responses.
# [Output] Exact hash, actor/Thread/profile binding, strict status validation and owner registration evidence.
# [Pos] Provider-free workspace plugin metadata contract test; no PostgreSQL, filesystem or Runtime.
# [Sync] 2026-09-15: pin Admin d7ba9c6 before replacing the public packer database path.
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from services.admin_data.config import AdminDataConfig
from services.admin_data.deck_workspace_plugins_data import (
    AdminDeckWorkspacePluginsData,
    DECK_WORKSPACE_PLUGIN_OPERATIONS,
    DeckWorkspacePluginsInputDTO,
    DeckWorkspacePluginsOutputDTO,
    RESOLVE_DECK_WORKSPACE_PLUGINS,
)
from services.admin_data.errors import AdminDataError
from services.admin_data.request_auth import AdminRequestAuth
from services.admin_data.workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS


def _output(**updates) -> DeckWorkspacePluginsOutputDTO:
    value = {
        "thread_id": "thread-1",
        "deck_id": "deck-1",
        "refs": [
            {
                "plugin_installation_id": "install-1",
                "package_spec": "drama-forge@drama-studio",
                "package_name": "drama-forge",
                "marketplace": "drama-studio",
                "resolved_version": "1.2.3",
                "artifact_digest": "sha256:" + "a" * 64,
                "installation_status": "ready",
                "order_index": 0,
            }
        ],
        "story_workspace_adapter": None,
        **updates,
    }
    return DeckWorkspacePluginsOutputDTO.model_validate(value)


def _data(output: DeckWorkspacePluginsOutputDTO | None = None):
    client = Mock()
    client.capabilities_snapshot.return_value = SimpleNamespace(
        schema_capabilities=list(WORKFLOW_SCHEMA_REQUIREMENTS)
    )
    client.execute.return_value = output or _output()
    return AdminDeckWorkspacePluginsData(
        client,
        canonical_user_id="42",
    ), client


def test_registry106_contract_and_strict_dtos_are_exact():
    assert DECK_WORKSPACE_PLUGIN_OPERATIONS == (
        RESOLVE_DECK_WORKSPACE_PLUGINS,
    )
    assert RESOLVE_DECK_WORKSPACE_PLUGINS.capability.model_dump() == {
        "name": "deck-workspace-plugins.resolve",
        "kind": "read",
        "user_scope": "dream:read",
        "background_scope": None,
        "input_schema_version": 1,
        "output_schema_version": 1,
        "contract_sha256": (
            "79eca8295a3a1611b2459af26f0a9e05"
            "dd01eae97bdd4928d1982e77a524425e"
        ),
    }
    with pytest.raises(ValidationError):
        DeckWorkspacePluginsInputDTO.model_validate(
            {
                "thread_id": "thread-1",
                "profile": "standard",
                "actor_id": "42",
            }
        )
    with pytest.raises(ValidationError):
        DeckWorkspacePluginsOutputDTO.model_validate(
            {**_output().model_dump(), "artifact_path": "/private/store"}
        )


def test_resolve_checks_capability_and_binds_actor_thread_profile_and_deck():
    data, client = _data()
    selection = DeckWorkspacePluginsInputDTO(
        thread_id="thread-1",
        profile="standard",
    )
    resolution = data.resolve(
        selection,
        "workspace-plugin-request",
        access_token="idg-token",
    )
    assert resolution.snapshot is client.execute.return_value
    assert resolution.snapshot_for(
        actor_id="42",
        thread_id="thread-1",
        profile="standard",
        deck_id="deck-1",
    ) is client.execute.return_value
    client.capabilities_snapshot.assert_called_once_with("workspace-plugin-request")
    client.execute.assert_called_once_with(
        RESOLVE_DECK_WORKSPACE_PLUGINS,
        selection,
        "workspace-plugin-request",
        access_token="idg-token",
    )
    for change in (
        {"actor_id": "43"},
        {"thread_id": "thread-other"},
        {"profile": "story_workspace"},
        {"deck_id": "deck-other"},
    ):
        values = {
            "actor_id": "42",
            "thread_id": "thread-1",
            "profile": "standard",
            "deck_id": "deck-1",
            **change,
        }
        with pytest.raises(AdminDataError):
            resolution.snapshot_for(**values)


@pytest.mark.parametrize(
    "input_dto,output",
    [
        (
            DeckWorkspacePluginsInputDTO(
                thread_id="thread-1", profile="standard"
            ),
            _output(thread_id="thread-other"),
        ),
        (
            DeckWorkspacePluginsInputDTO(
                thread_id="thread-1", profile="standard"
            ),
            _output(refs=[*_output().refs, *_output().refs]),
        ),
        (
            DeckWorkspacePluginsInputDTO(
                thread_id="thread-1", profile="standard"
            ),
            _output(
                refs=[
                    {**_output().refs[0].model_dump(), "order_index": 2},
                    {
                        **_output().refs[0].model_dump(),
                        "plugin_installation_id": "install-2",
                        "order_index": 1,
                    },
                ]
            ),
        ),
        (
            DeckWorkspacePluginsInputDTO(
                thread_id="thread-1", profile="story_workspace"
            ),
            _output(),
        ),
        (
            DeckWorkspacePluginsInputDTO(
                thread_id="thread-1", profile="standard"
            ),
            _output(
                story_workspace_adapter={
                    "latest_status": None,
                    "ready": None,
                }
            ),
        ),
    ],
)
def test_resolve_rejects_mismatched_or_ambiguous_admin_data(
    input_dto,
    output,
):
    data, _client = _data(output)
    with pytest.raises(AdminDataError) as caught:
        data.resolve(
            input_dto,
            "workspace-plugin-request",
            access_token="idg-token",
        )
    assert caught.value.code == "ADMIN_RESPONSE_INVALID"


def test_production_request_owner_registers_registry106_operation():
    config = AdminDataConfig(
        base_url="https://admin.example",
        issuer="https://admin.example/api/auth",
        resource="https://dream.example/api",
        service_client_id="dream-service",
        service_secret="s" * 32,
    )
    owner = AdminRequestAuth(config)
    try:
        assert (
            owner.client._operations[
                RESOLVE_DECK_WORKSPACE_PLUGINS.capability.name
            ]
            is RESOLVE_DECK_WORKSPACE_PLUGINS
        )
    finally:
        owner.close()
