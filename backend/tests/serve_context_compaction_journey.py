# [Sync] 2026-10-12: inject public assistant usage and CLI Result window for the normal metadata path.
# [Input] Fresh named runtime root and production public Chat/Stop/history composition.
# [Output] Isolated HTTP fixture emitting public SDK DTOs through the real Factory/Service.
# [Pos] Provider-free technical browser harness; no normal account/database/model acceptance.
# [Sync] 2026-10-12: cover held compaction, actual boundaries, errors and ordinary text at SDK injection seam.
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import socket
from types import SimpleNamespace
from uuid import uuid4

import pytest
import uvicorn

from tests.test_image_chat_public_journey import build_public_journey_app
from claude_agent_sdk.types import AssistantMessage, ResultMessage, StreamEvent, SystemMessage, TextBlock
from libs.claude_agent_kit.types import AgentRunResult
import claude_agent.thread_factory as factory_module
from routers import storage as storage_route, system_config as settings_route
from services.admin_data.chat_models import LatestMessageResultDTO, QueueListResultDTO, TaskSessionLinksResultDTO


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    root = Path(parser.parse_args().root).resolve()
    if root.name != "context-compaction-browser-fixture" or root.exists():
        raise RuntimeError("Use a fresh named context-compaction-browser-fixture directory")
    root.mkdir(parents=True, mode=0o700)
    patches = pytest.MonkeyPatch()
    app, fixture, config, _, _, factory = build_public_journey_app(patches, root)
    config.update(model="available-text", workspace_enabled=False)
    config.pop("image_model", None)
    def latest_message(dto, _request_id, *, access_token):
        assert access_token == "test-oauth-token"
        messages = [item for item in fixture.messages if item["thread_id"] == dto.thread_id]
        return LatestMessageResultDTO(message_id=messages[-1]["id"] if messages else None)
    patches.setattr(fixture, "latest_message", latest_message, raising=False)
    patches.setattr(fixture, "list_inputs", lambda dto, request_id, *, access_token: QueueListResultDTO(entries=[]), raising=False)
    patches.setattr(fixture, "list_task_session_links", lambda dto, request_id, *, access_token: TaskSessionLinksResultDTO(source=None, created=[]), raising=False)
    class SettingsData:
        def __init__(self, _):
            pass
        def get_user(self, dto, request_id, *, access_token):
            return dict(config)
        def patch_user(self, dto, request_id, *, access_token):
            config.update(dto.model_dump(mode="json"))
            return SimpleNamespace(success=True)
    patches.setattr(settings_route, "AdminSystemConfigData", SettingsData)
    patches.setattr(storage_route, "storage_driver", "unknown")
    patches.setattr(storage_route, "_check_storage_configuration", lambda: {"is_valid": True})
    app.include_router(settings_route.router)
    app.include_router(storage_route.router)
    state = {"mode": "ordinary", "hold": False}
    release = asyncio.Event()
    calls = []

    class Runner:
        async def run_streaming(self, options, callbacks):
            mode, hold = state["mode"], state["hold"]
            calls.append({"mode": mode, "model": options.model})
            if mode not in ("ordinary", "literal"):
                await callbacks.on_message(SystemMessage(subtype="status", data={"uuid": str(uuid4()), "status": "compacting"}))
                if hold:
                    release.clear()
                    await release.wait()
                if mode == "failed":
                    error = RuntimeError("Injected SDK compaction failure")
                    await callbacks.on_error(error)
                    return AgentRunResult("", None, False, error=error, protocol_completed=False)
                await callbacks.on_message(SystemMessage(subtype="status", data={"uuid": str(uuid4()), "status": None}))
                if mode in ("manual", "auto"):
                    boundary = SystemMessage(subtype="compact_boundary", data={"uuid": str(uuid4()), "compact_metadata": {"trigger": mode, "pre_tokens": 120}})
                    await callbacks.on_message(boundary)
                    await callbacks.on_message(boundary)  # SDK replay must remain idempotent.
            text = "Compacted" if mode in ("manual", "literal") else "Continue normally."
            if mode != "manual":
                await callbacks.on_message(StreamEvent(event={"type": "message_start", "message": {"model": "available-text", "usage": {"input_tokens": 0}}}))
            message = AssistantMessage(content=[TextBlock(text=text)])
            message.model = "<synthetic>" if mode == "manual" else "available-text"
            message.usage = {"input_tokens": 0}
            await callbacks.on_message(message)
            # The actual Runner text channel follows raw SDK callbacks.
            await callbacks.on_text_delta(text)
            await callbacks.on_text_done(text)
            if mode != "manual":
                await callbacks.on_message(StreamEvent(event={"type": "message_delta", "usage": {"input_tokens": 400, "cache_creation_input_tokens": 10, "cache_read_input_tokens": 10, "output_tokens": 90}}))
                await callbacks.on_message(StreamEvent(event={"type": "message_stop"}))
            result_message = ResultMessage()
            result_message.is_error = False
            result_message.model_usage = {"available-text": {"contextWindow": 1000, "inputTokens": 99999}}
            await callbacks.on_message(result_message)
            return AgentRunResult(text, None, True, protocol_completed=True)

        async def close(self):
            pass

    patches.setattr(factory_module, "ClaudeAgentRunner", Runner)

    @app.get("/auth/session")
    async def session():
        return {"user": {"id": "7", "email": "compaction-browser@example.test", "display_name": "Isolated fixture", "avatar_url": None, "role": "user", "created_at": None}, "csrf_token": "s" * 43}

    @app.post("/_fixture/mode")
    async def mode(values: dict):
        selected = values.get("mode", state["mode"])
        if selected not in ("ordinary", "literal", "manual", "auto", "failed", "unconfirmed"):
            raise ValueError("Unknown injected SDK mode")
        state.update(mode=selected, hold=bool(values.get("hold", False)))
        if not state["hold"]:
            release.set()
        return {"ok": True}

    @app.get("/_fixture/receipt")
    async def receipt():
        return {"calls": calls, "messages": fixture.messages}

    @app.on_event("shutdown")
    async def shutdown():
        await factory.aclose()

    owned = socket.socket()
    owned.bind(("127.0.0.1", 0))
    owned.listen(128)
    print(json.dumps({"port": owned.getsockname()[1]}), flush=True)
    try:
        uvicorn.Server(uvicorn.Config(app, log_level="warning")).run(sockets=[owned])
    finally:
        owned.close()
        patches.undo()


if __name__ == "__main__":
    main()
