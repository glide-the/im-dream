# [Input] Registry106 immutable metadata, public turn owner and workspace pack loader seam.
# [Output] PostgreSQL fence, Story adapter decisions, deduplication and frozen-manifest no-I/O evidence.
# [Pos] Provider-free public Agent workspace pack test; no real Admin, artifact store, Runtime or model.
# [Sync] 2026-09-15: keep filesystem execution in Dream while public metadata comes only from Admin.
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import pytest

import claude_agent.service as service_module
from services.admin_data.agent_turn_persistence import AdminAgentTurnPersistence
from services.admin_data.deck_workspace_plugins_data import (
    AdminDeckWorkspacePluginsResolution,
    AdminDeckWorkspacePluginsProvider,
    DeckWorkspacePluginsOutputDTO,
)
from services.claude_plugin.workspace_packer import (
    WorkspacePackError,
    pack_workspace_plugins_with_refs_loader,
)


def _snapshot(*, adapter=None):
    return DeckWorkspacePluginsOutputDTO.model_validate(
        {
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
            "story_workspace_adapter": adapter,
        }
    )


class _Owner(AdminAgentTurnPersistence, AdminDeckWorkspacePluginsProvider):
    def __init__(self, snapshot, profile):
        self.calls = []
        self.resolution = AdminDeckWorkspacePluginsResolution(
            canonical_user_id="42",
            thread_id="thread-1",
            profile=profile,
            snapshot=snapshot,
        )

    def workspace_plugins(self, *, actor_id, thread_id, profile):
        self.calls.append((actor_id, thread_id, profile))
        return self.resolution


def _capture_loaded_refs(owner, *, dream_mode):
    captured = []

    def consume(*, workspace, deck_id, refs_loader):
        captured.extend(refs_loader())
        return {"workspace": str(workspace), "deck_id": deck_id}

    with patch.object(
        service_module,
        "pack_workspace_plugins_with_refs_loader",
        side_effect=consume,
    ) as pack:
        service_module._pack_thread_workspace_plugins(
            "/workspace/thread-1",
            "deck-1",
            actor_id="42",
            thread_id="thread-1",
            admin_turn_persistence=owner,
            dream_mode=dream_mode,
        )
    assert pack.call_count == 1
    return captured


def test_public_standard_pack_uses_registry106_and_never_opens_dream_db():
    owner = _Owner(_snapshot(), "standard")
    refs = _capture_loaded_refs(owner, dream_mode=False)
    assert owner.calls == [("42", "thread-1", "standard")]
    assert [item["package_spec"] for item in refs] == [
        "drama-forge@drama-studio"
    ]


def test_public_story_pack_appends_ready_adapter_and_deduplicates_by_package():
    adapter = {
        "latest_status": "error",
        "ready": {
            "plugin_installation_id": "install-story",
            "package_spec": "ink-dream-story@platform-builtin",
            "package_name": "ink-dream-story",
            "marketplace": "platform-builtin",
            "resolved_version": "1.0.0",
            "artifact_digest": "sha256:" + "b" * 64,
            "installation_status": "ready",
        },
    }
    owner = _Owner(_snapshot(adapter=adapter), "story_workspace")
    refs = _capture_loaded_refs(owner, dream_mode=True)
    assert owner.calls == [("42", "thread-1", "story_workspace")]
    assert [item["package_spec"] for item in refs] == [
        "drama-forge@drama-studio",
        "ink-dream-story@platform-builtin",
    ]

    duplicated = _snapshot(
        adapter={
            **adapter,
            "ready": {
                **adapter["ready"],
                "plugin_installation_id": "install-other",
                "package_spec": "drama-forge@drama-studio",
            },
        }
    )
    assert len(_capture_loaded_refs(
        _Owner(duplicated, "story_workspace"),
        dream_mode=True,
    )) == 1


@pytest.mark.parametrize(
    "adapter,code",
    [
        ({"latest_status": None, "ready": None}, "CLAUDE_PLUGIN_NOT_FOUND"),
        (
            {"latest_status": "installing", "ready": None},
            "CLAUDE_PLUGIN_NOT_READY",
        ),
    ],
)
def test_public_story_pack_preserves_missing_and_not_ready_business_errors(
    adapter,
    code,
):
    owner = _Owner(_snapshot(adapter=adapter), "story_workspace")
    with pytest.raises(WorkspacePackError) as caught:
        _capture_loaded_refs(owner, dream_mode=True)
    assert caught.value.code == code


def test_frozen_workspace_validates_before_metadata_loader_io():
    loader = Mock(side_effect=AssertionError("frozen pack performed metadata I/O"))
    with TemporaryDirectory() as raw:
        workspace = Path(raw)
        manifest_path = workspace / ".ink" / "launch-manifest.json"
        manifest_path.parent.mkdir()
        manifest_path.write_text(
            json.dumps(
                {
                    "schema_version": "claude-launch/v1",
                    "deck_id": "deck-1",
                    "written_at": "2026-09-15T00:00:00+00:00",
                    "plugins": [],
                }
            ),
            encoding="utf-8",
        )
        receipt = pack_workspace_plugins_with_refs_loader(
            workspace=workspace,
            deck_id="deck-1",
            refs_loader=loader,
        )
    assert receipt["frozen"] is True
    loader.assert_not_called()
