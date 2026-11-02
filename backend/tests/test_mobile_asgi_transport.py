# [Input] Shared bridge policy and real ASGI/Starlette responses without a database or provider.
# [Output] Streaming, backpressure, document ownership, validation and disconnect evidence.
# [Pos] Focused native transport contracts; production adapter handles all HTTP frames.
# [Sync] 2026-10-26: cover unchanged HTTP frames and bounded registered-code-only launch diagnostics.
import asyncio
import base64
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from starlette.responses import StreamingResponse

from mobile_runtime.asgi_transport import NativeASGITransport
from mobile_runtime.ios_http import _observe_dream_launch_errors
from routers.public import create_public_router

CONTRACT = json.loads((Path(__file__).parents[2] / "mobile/shared/bridge/contract.json").read_text())


def request(identifier="request1", **values):
    return {"clientRequestId": identifier, "method": "GET", "path": "/api/health", **values}


def test_existing_public_route_uses_the_production_transport():
    async def run():
        app = FastAPI()
        app.include_router(create_public_router(backend_version="contract", cors_allow_origins=[],
            public_base_url="/", backend_public_base_url="/"))
        transport = NativeASGITransport(app, CONTRACT)
        head = await transport.open("page1", request())
        assert head["status"] == 200
        content = bytearray()
        while True:
            chunk = await transport.read("page1", {**head, "maximumBytes": 7})
            content.extend(base64.b64decode(chunk["dataBase64"]))
            if chunk["done"]:
                break
        assert json.loads(content)["version"] == "contract"
        assert not transport.responses
        await transport.cancel_owner("page1")
    asyncio.run(run())


def test_response_head_and_binary_chunks_arrive_before_generator_completion():
    async def run():
        ready = asyncio.Event()
        finish = asyncio.Event()
        complete = asyncio.Event()
        payload = bytes(range(256)) * 400

        async def content():
            ready.set()
            yield payload
            await finish.wait()
            yield "结束✅".encode()
            complete.set()

        async def app(scope, receive, send):
            await StreamingResponse(content(), media_type="text/event-stream")(scope, receive, send)

        transport = NativeASGITransport(app, CONTRACT)
        head = await asyncio.wait_for(transport.open("page1", request()), 2)
        await ready.wait()
        first = await transport.read("page1", {**head, "maximumBytes": 1024})
        output = bytearray(base64.b64decode(first["dataBase64"]))
        assert len(output) == 1024 and not first["done"] and not complete.is_set()
        finish.set()
        while True:
            part = await transport.read("page1", {**head, "maximumBytes": 1024})
            decoded = base64.b64decode(part["dataBase64"])
            assert len(decoded) <= 1024
            output.extend(decoded)
            if part["done"]:
                break
        assert output == payload + "结束✅".encode()
        assert complete.is_set()
        await transport.cancel_owner("page1")
    asyncio.run(run())


def test_document_ownership_and_duplicate_dispatch_are_enforced():
    async def run():
        calls = []
        async def app(scope, receive, send):
            calls.append(scope)
            await send({"type": "http.response.start", "status": 200})
            await send({"type": "http.response.body", "body": b"one"})
        transport = NativeASGITransport(app, CONTRACT)
        head = await transport.open("page1", request())
        with pytest.raises(KeyError):
            await transport.read("page2", head)
        with pytest.raises(KeyError):
            await transport.cancel("page1", {**head, "streamId": "other"})
        with pytest.raises(ValueError, match="already"):
            await transport.open("page1", request())
        assert len(calls) == 1
        await transport.cancel_owner("page1")
        assert not transport.responses and not transport.seen
    asyncio.run(run())


def test_cancel_before_response_head_unblocks_the_pending_open():
    async def run():
        entered = asyncio.Event()
        cancelled = asyncio.Event()
        async def app(scope, receive, send):
            entered.set()
            try:
                await asyncio.Future()
            finally:
                cancelled.set()
        transport = NativeASGITransport(app, CONTRACT)
        pending = asyncio.create_task(transport.open("page1", request()))
        await entered.wait()
        assert await transport.cancel("page1", {"requestId": "request1"}) == {"cancelled": True}
        with pytest.raises(asyncio.CancelledError):
            await pending
        assert cancelled.is_set() and not transport.responses
    asyncio.run(run())


def test_transport_disconnect_leaves_independent_application_task_running():
    async def run():
        task_started = asyncio.Event()
        task_release = asyncio.Event()
        async def business_task():
            task_started.set()
            await task_release.wait()
            return "existing task finished"
        background = asyncio.create_task(business_task())
        async def app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200})
            while True:
                await send({"type": "http.response.body", "body": b"data: live\n\n", "more_body": True})
        transport = NativeASGITransport(app, CONTRACT)
        await task_started.wait()
        head = await transport.open("page1", request())
        await transport.cancel("page1", head)
        assert not background.done()
        task_release.set()
        assert await background == "existing task finished"
    asyncio.run(run())


def test_cancel_unblocks_a_pending_read_without_replaying_the_request():
    async def run():
        entered = asyncio.Event()
        async def app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200})
            entered.set()
            await asyncio.Future()
        transport = NativeASGITransport(app, CONTRACT)
        head = await transport.open("page1", request())
        await entered.wait()
        pending = asyncio.create_task(transport.read("page1", head))
        await asyncio.sleep(0)
        with pytest.raises(ValueError, match="already pending"):
            await transport.read("page1", head)
        await transport.cancel("page1", head)
        with pytest.raises(asyncio.CancelledError):
            await pending
        with pytest.raises(ValueError, match="already"):
            await transport.open("page1", request())
    asyncio.run(run())


@pytest.mark.parametrize("value", [
    request(path="https://example.invalid/api/me"), request(path="//other/api/me"),
    request(path="/api/%2e%2e/me"), request(headers={"Authorization": "fixture-only"}),
    request(headers={"Cookie": "fixture-only"}), request(headers={"x-user-id": "fixture-only"}),
    request(bodyBase64="!invalid!"), request(method="CONNECT"),
])
def test_native_header_path_and_body_policy_rejects_before_dispatch(value):
    async def run():
        async def app(*args):
            pytest.fail("Rejected transport input reached the application")
        with pytest.raises(ValueError):
            await NativeASGITransport(app, CONTRACT).open("page1", value)
    asyncio.run(run())


def test_native_response_cookies_are_separate_from_web_headers():
    async def run():
        async def app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": [
                (b"set-cookie", b"first=fixture; HttpOnly"), (b"set-cookie", b"second=fixture; HttpOnly"),
                (b"content-type", b"application/json"),
            ]})
            await send({"type": "http.response.body", "body": b"{}"})
        transport = NativeASGITransport(app, CONTRACT)
        head = await transport.open("page1", request())
        assert "set-cookie" not in head["headers"]
        assert head["nativeCookies"] == ["first=fixture; HttpOnly", "second=fixture; HttpOnly"]
        await transport.cancel_owner("page1")
    asyncio.run(run())


@pytest.mark.parametrize("payload,expected", [
    (b'{"error":{"code":"DECK_RUNTIME_CONFIG_UNAVAILABLE","message":"private-body"}}', "DECK_RUNTIME_CONFIG_UNAVAILABLE"),
    (b'{"detail":"WORKFLOW_PERMISSION_DENIED"}', "WORKFLOW_PERMISSION_DENIED"),
    (b'{"detail":{"error_code":"WORKFLOW_PERMISSION_DENIED"}}', "WORKFLOW_PERMISSION_DENIED"),
    (b'{"error":{"code":"private-body"}}', "UNCLASSIFIED"),
    (b'private-body', "UNCLASSIFIED"),
    (b'{"error":{"code":"DECK_RUNTIME_CONFIG_UNAVAILABLE"}}' + b' ' * 4096, "UNCLASSIFIED"),
])
def test_launch_error_diagnostics_preserve_frames_and_exclude_content(payload, expected, capsys):
    async def run():
        scope = {"type": "http", "method": "POST", "path": "/api/story-workspace/dream-runs/start",
                 "query_string": b"private-query", "headers": [(b"authorization", b"private-auth")]}
        frames = [
            {"type": "http.response.start", "status": 503, "headers": [
                (b"set-cookie", b"private-cookie-one"), (b"set-cookie", b"private-cookie-two")]},
            {"type": "http.response.body", "body": payload[:11], "more_body": True},
            {"type": "http.response.body", "body": payload[11:]},
        ]
        sent = []
        async def receive():
            return {"type": "http.request", "body": b"private-request"}
        async def send(frame):
            sent.append(frame)
        async def app(actual_scope, actual_receive, actual_send):
            assert actual_scope is scope and actual_receive is receive
            for frame in frames:
                await actual_send(frame)
        await _observe_dream_launch_errors(app)(scope, receive, send)
        assert len(sent) == len(frames) and all(left is right for left, right in zip(sent, frames))
    asyncio.run(run())
    output = capsys.readouterr()
    assert output.err == ""
    assert json.loads(output.out.removeprefix("IOS_DREAM_HTTP_FAILURE ")) == {
        "operation": "dream.launch", "status": 503, "code": expected,
    }
    assert "private-" not in output.out


@pytest.mark.parametrize("method,path,status", [
    ("POST", "/api/story-workspace/dream-runs/start", 201),
    ("GET", "/api/story-workspace/dream-runs/start", 503),
    ("POST", "/api/other", 503),
])
def test_launch_observer_ignores_success_and_other_operations(method, path, status, capsys):
    async def run():
        async def app(scope, receive, send):
            await send({"type": "http.response.start", "status": status})
            await send({"type": "http.response.body", "body": b'private-body'})
        async def send(frame):
            pass
        await _observe_dream_launch_errors(app)({"type": "http", "method": method, "path": path}, None, send)
    asyncio.run(run())
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("failure", [RuntimeError("send failed"), asyncio.CancelledError()])
def test_launch_observer_propagates_original_transport_failures(failure, capsys):
    async def run():
        async def app(scope, receive, send):
            await send({"type": "http.response.start", "status": 503})
        async def send(frame):
            raise failure
        with pytest.raises(type(failure)) as raised:
            await _observe_dream_launch_errors(app)({
                "type": "http", "method": "POST", "path": "/api/story-workspace/dream-runs/start",
            }, None, send)
        assert raised.value is failure
    asyncio.run(run())
    assert capsys.readouterr().out == ""


def test_launch_observer_diagnostics_sink_failure_leaves_original_response(monkeypatch):
    async def run():
        frames = [{"type": "http.response.start", "status": 503},
                  {"type": "http.response.body", "body": b'{"detail":"WORKFLOW_PERMISSION_DENIED"}'}]
        sent = []
        async def app(scope, receive, send):
            for frame in frames:
                await send(frame)
        async def send(frame):
            sent.append(frame)
        def broken_print(*args, **kwargs):
            raise OSError("sink unavailable")
        monkeypatch.setattr("builtins.print", broken_print)
        await _observe_dream_launch_errors(app)({
            "type": "http", "method": "POST", "path": "/api/story-workspace/dream-runs/start",
        }, None, send)
        assert sent == frames
    asyncio.run(run())
