# [Input] Production private host control transport with explicit in-memory endpoint frames.
# [Output] Full original startup errors and existing failure-code fallback without HTTP/model calls.
# [Pos] Provider-free iOS startup error propagation contract.
# [Sync] 2026-11-01: retain Next error text beyond the former status-frame size.
import asyncio
import json
import os

import pytest

from mobile_runtime import ios_claude_transport as native


@pytest.mark.parametrize("original", [None, "Error: listen EADDRINUSE: address already in use ::1:5173\n" + "original stack\n" * 800])
def test_startup_returns_original_host_error(monkeypatch, original):
    sent = []
    replies = [
        {"type": "web_started", "pid": os.getpid(), "origin": "http://localhost:5173"},
        {"type": "status", "pid": os.getpid(), "web": {"state": "failed", "code": "IOS_NEXT_WORKER_STOPPED", "error": original}},
    ]

    class Connection:
        def __init__(self, response):
            self.remaining = (json.dumps(response) + "\n").encode()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

        async def send(self, data):
            sent.append(json.loads(data))

        async def receive(self, max_bytes=65536):
            part, self.remaining = self.remaining[:max_bytes], self.remaining[max_bytes:]
            return part

    async def connect(host, port):
        assert host == "127.0.0.1" and port == 5199
        return Connection(replies.pop(0))

    monkeypatch.setattr(native, "read_native_endpoint", lambda _: {"port": 5199, "token": "synthetic-control-token"})
    monkeypatch.setattr(native.anyio, "connect_tcp", connect)

    async def scenario():
        with pytest.raises(native.CLIConnectionError) as failure:
            await native.start_native_web("fixture-only", "http://127.0.0.1:5200")
        assert str(failure.value) == (original or "IOS_NEXT_WORKER_STOPPED")

    asyncio.run(scenario())
    assert [packet["type"] for packet in sent] == ["start_web", "status"]
    assert all(packet["token"] == "synthetic-control-token" for packet in sent)
    assert not replies
