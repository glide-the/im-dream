# [Input] Registry130-132 fake DTO service, request OAuth bearer and local verifier result.
# [Output] Current/replay operation order, strict identities and closed Admin error mapping.
# [Pos] Provider-free Dream launch Runtime coordinator test; no database or shared filesystem.
# [Sync] 2026-09-16: cover the request-scoped Admin Runtime port introduced for launch.
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from services.admin_data.deck_plugin_binding_data import AgentTypeVerifiedPluginDTO
from services.admin_data.errors import AdminDataError
from services.story_workspace.dream_launch_runtime import (
    AdminDreamLaunchRuntime,
    DreamLaunchRuntimeError,
)


DECK_ID = "deck-launch-runtime"
WORKSPACE_ID = "workspace-launch-runtime"
BINDING_ID = "dpb_" + "1" * 32
RUN_ID = "run_" + "2" * 32
THREAD_ID = "thread-launch-runtime"


def binding():
    return SimpleNamespace(
        deck_plugin_binding_id=BINDING_ID,
        deck_plugin_id="example.story",
        deck_plugin_version="1.0.0",
        binding_revision=3,
    )


def target():
    return SimpleNamespace(
        plugin_installation_id="cpi_" + "3" * 32,
        package_spec="example.runtime",
        resolved_version="1.0.0",
        artifact_digest="sha256:" + "4" * 64,
    )


class FakeData:
    def __init__(self) -> None:
        self.calls = []
        self.error: AdminDataError | None = None
        self.mismatch = False

    def launch_runtime_scope(self, input_dto, request_id, *, access_token):
        self.calls.append(("scope", input_dto, request_id, access_token))
        self._raise()
        return SimpleNamespace(**input_dto.model_dump(), authorized=True)

    def launch_runtime_plan(self, input_dto, request_id, *, access_token):
        self.calls.append(("plan", input_dto, request_id, access_token))
        self._raise()
        return SimpleNamespace(**input_dto.model_dump(), binding=binding(), target=target())

    def launch_runtime_prepare(self, input_dto, request_id, *, access_token):
        self.calls.append(("prepare", input_dto, request_id, access_token))
        self._raise()
        selected = binding()
        if self.mismatch:
            selected = SimpleNamespace(**{**vars(selected), "binding_revision": 4})
        return SimpleNamespace(**{
            **input_dto.model_dump(exclude={"expected_binding_revision", "verified_plugin"}),
            "binding": selected,
            "runtime_ready": True,
        })

    def _raise(self):
        if self.error is not None:
            raise self.error


@patch(
    "services.story_workspace.dream_launch_runtime.verify_agent_type_runtime",
    return_value=AgentTypeVerifiedPluginDTO(
        plugin_installation_id="cpi_" + "3" * 32,
        package_spec="example.runtime",
        resolved_version="1.0.0",
        artifact_digest="sha256:" + "4" * 64,
        has_manifest=True,
    ),
)
def test_current_and_replay_use_exact_admin_dtos(mock_verify):
    data = FakeData()
    runtime = AdminDreamLaunchRuntime(data, "oauth-access-token")

    asyncio.run(runtime.authorize(deck_id=DECK_ID, workspace_id=WORKSPACE_ID, agent_id=None))
    current = asyncio.run(runtime.prepare(
        deck_id=DECK_ID, workspace_id=WORKSPACE_ID, agent_id=None, existing_run=None,
    ))
    replay = asyncio.run(runtime.prepare(
        deck_id=DECK_ID,
        workspace_id=WORKSPACE_ID,
        agent_id="voice-1",
        existing_run={"id": RUN_ID, "source_voice_thread_id": THREAD_ID},
    ))

    assert current == replay
    assert [call[0] for call in data.calls] == ["scope", "plan", "prepare", "plan", "prepare"]
    assert data.calls[1][1].model_dump() == {
        "deck_id": DECK_ID,
        "workspace_id": WORKSPACE_ID,
        "agent_id": None,
        "mode": "current",
        "workflow_run_id": None,
        "thread_id": None,
    }
    assert data.calls[3][1].model_dump() == {
        "deck_id": DECK_ID,
        "workspace_id": WORKSPACE_ID,
        "agent_id": "voice-1",
        "mode": "replay",
        "workflow_run_id": RUN_ID,
        "thread_id": THREAD_ID,
    }
    assert all(call[3] == "oauth-access-token" for call in data.calls)
    assert mock_verify.call_count == 2


def test_admin_error_and_prepare_mismatch_fail_closed():
    data = FakeData()
    runtime = AdminDreamLaunchRuntime(data, "oauth-access-token")
    data.error = AdminDataError("ADMIN_UNAVAILABLE", 503, "request", False)
    with pytest.raises(DreamLaunchRuntimeError) as unavailable:
        asyncio.run(runtime.authorize(deck_id=DECK_ID, workspace_id=WORKSPACE_ID, agent_id=None))
    assert (unavailable.value.code, unavailable.value.status_code) == (
        "ADMIN_UNAVAILABLE", 503,
    )

    data.error = None
    data.mismatch = True
    evidence = AgentTypeVerifiedPluginDTO(
        plugin_installation_id="cpi_" + "3" * 32,
        package_spec="example.runtime",
        resolved_version="1.0.0",
        artifact_digest="sha256:" + "4" * 64,
        has_manifest=True,
    )
    with (
        patch(
            "services.story_workspace.dream_launch_runtime.verify_agent_type_runtime",
            return_value=evidence,
        ),
        pytest.raises(DreamLaunchRuntimeError) as mismatch,
    ):
        asyncio.run(runtime.prepare(
            deck_id=DECK_ID, workspace_id=WORKSPACE_ID, agent_id=None, existing_run=None,
        ))
    assert (mismatch.value.code, mismatch.value.status_code) == (
        "ADMIN_RESPONSE_INVALID", 503,
    )


def test_access_token_is_required_and_never_in_repr():
    data = FakeData()
    with pytest.raises(DreamLaunchRuntimeError):
        AdminDreamLaunchRuntime(data, "bad token")
    runtime = AdminDreamLaunchRuntime(data, "private-token")
    assert "private-token" not in repr(runtime)
