# [Input] Reflections public config/memory-init routes with explicit Admin actor and deterministic adapters.
# [Output] Original merge/filter/reset responses and Thread-to-config-to-filesystem ordering evidence.
# [Pos] Provider-free route tests; background Reflections task persistence is outside this suite.
# [Sync] 2026-09-15: replace public section-config database mocks with the Admin boundary.
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers import reflections as router_module
from services.admin_data.request_auth import AdminRequestActor


class _SectionData:
    def __init__(self) -> None:
        self.custom: dict | None = None
        self.calls: list[tuple[str, str, object]] = []

    def get(self, input_dto, _request_id, *, access_token):
        self.calls.append(("get", input_dto.section, access_token))
        return None if self.custom is None else dict(self.custom)

    def save(self, input_dto, _request_id, *, access_token):
        self.calls.append(("save", input_dto.section, access_token))
        self.custom = json.loads(input_dto.prompt_files_json)
        return SimpleNamespace(saved=True)

    def delete(self, input_dto, _request_id, *, access_token):
        self.calls.append(("delete", input_dto.section, access_token))
        existed = self.custom is not None
        self.custom = None
        return SimpleNamespace(deleted=existed)


class _ChatData:
    def __init__(self, order: list[str], *, exists: bool = True) -> None:
        self.order = order
        self.exists = exists

    def get_thread(self, input_dto, _request_id, *, access_token):
        self.order.append("thread")
        assert access_token == "reflections-token"
        row = SimpleNamespace(id=input_dto.thread_id) if self.exists else None
        return SimpleNamespace(thread=row)


def _harness(monkeypatch, *, thread_exists: bool = True):
    data = _SectionData()
    order: list[str] = []
    chat = _ChatData(order, exists=thread_exists)
    actor = AdminRequestActor(
        "subject",
        "7",
        "browser",
        frozenset({"dream:read", "dream:write"}),
        1,
        2,
        "reflections-token",
    )
    owner = SimpleNamespace(client=object())
    app = FastAPI()
    app.dependency_overrides[router_module.get_current_user] = lambda: {
        "user_id": 7,
        "_admin_actor": actor,
    }
    app.dependency_overrides[router_module.get_admin_request_auth] = lambda: owner
    monkeypatch.setattr(
        router_module,
        "AdminReflectionsSectionConfigData",
        lambda _client: data,
    )
    monkeypatch.setattr(router_module, "AdminChatData", lambda _client: chat)

    def fail_direct_database(*_args, **_kwargs):
        raise AssertionError("public Reflections config must not use Dream database helpers")

    for name in (
        "get_reflections_section_config",
        "save_reflections_section_config",
        "delete_reflections_section_config",
    ):
        monkeypatch.setattr(router_module.database, name, fail_direct_database)

    original_get = data.get

    def ordered_get(*args, **kwargs):
        order.append("config")
        return original_get(*args, **kwargs)

    data.get = ordered_get
    app.include_router(router_module.router)
    return TestClient(app), data, order


def test_public_get_merges_custom_files_and_keeps_display_fields(monkeypatch) -> None:
    client, data, _ = _harness(monkeypatch)
    try:
        data.custom = {"WORKFLOW.md": " custom workflow ", "unknown": "ignored", "number": 1}
        response = client.get("/api/reflections/config/echoes")
    finally:
        client.close()
    assert response.status_code == 200
    body = response.json()
    assert body["section"] == "echoes" and body["usedCustomConfig"] is True
    assert body["prompt_files"]["WORKFLOW.md"] == "custom workflow"
    assert "unknown" not in body["prompt_files"] and "number" not in body["prompt_files"]
    assert data.calls == [("get", "echoes", "reflections-token")]


def test_put_filters_to_original_filenames_and_delete_preserves_reset_response(monkeypatch) -> None:
    client, data, _ = _harness(monkeypatch)
    try:
        saved = client.put(
            "/api/reflections/config/traits",
            json={"prompt_files": {"WORKFLOW.md": "  custom  ", "unknown": "drop", "MEMORY_QUERY_PROMPT.md": ""}},
        )
        reset = client.delete("/api/reflections/config/traits")
        reset_again = client.delete("/api/reflections/config/traits")
    finally:
        client.close()
    assert saved.status_code == 200
    assert saved.json() == {"saved": True, "section": "traits", "updatedFiles": ["WORKFLOW.md"]}
    assert reset.json() == reset_again.json() == {"reset": True, "section": "traits"}
    assert [item[0] for item in data.calls] == ["save", "delete", "delete"]


def test_memory_init_checks_thread_then_config_before_filesystem(monkeypatch) -> None:
    client, data, order = _harness(monkeypatch)
    data.custom = {"WORKFLOW.md": "custom"}

    def write(thread_id: str, prompt_files: dict[str, str]) -> Path:
        order.append("filesystem")
        assert thread_id == "thread-1" and prompt_files["WORKFLOW.md"] == "custom"
        return Path("/workspace/thread-1/memory")

    monkeypatch.setattr(router_module, "_write_section_memory_workspace", write)
    try:
        response = client.post(
            "/api/reflections/memory-init",
            json={"threadId": "thread-1", "section": "patterns"},
        )
    finally:
        client.close()
    assert response.status_code == 200
    assert response.json()["usedCustomConfig"] is True
    assert order == ["thread", "config", "filesystem"]


def test_missing_thread_stops_before_config_and_filesystem(monkeypatch) -> None:
    client, data, order = _harness(monkeypatch, thread_exists=False)
    monkeypatch.setattr(
        router_module,
        "_write_section_memory_workspace",
        lambda *_args: (_ for _ in ()).throw(AssertionError("filesystem must not run")),
    )
    try:
        response = client.post(
            "/api/reflections/memory-init",
            json={"threadId": "thread-missing", "section": "echoes"},
        )
    finally:
        client.close()
    assert response.status_code == 404
    assert data.calls == [] and order == ["thread"]
