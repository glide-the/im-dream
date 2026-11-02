# [Input] Existing Dream ASGI application, shared transport policy and document-owned requests.
# [Output] Response heads and bounded pull streams with ASGI disconnect/cancellation.
# [Pos] Native-to-Dream HTTP transport; Agent tasks retain their existing business lifecycle.
from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass, field
import re
from typing import Any
from urllib.parse import unquote, urlsplit
from uuid import uuid4


@dataclass
class _Response:
    owner: str
    request_id: str
    stream_id: str
    head: asyncio.Future
    body: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=1))
    disconnected: asyncio.Event = field(default_factory=asyncio.Event)
    task: asyncio.Task | None = None
    pending: bytes = b""
    done: bool = False
    ended: bool = False
    reading: bool = False
    failure: BaseException | None = None


class NativeASGITransport:
    """Run on the application's persistent Python event loop."""
    chunk_bytes = 65_536  # Shared bridge v1 maximum response chunk.

    def __init__(self, app, contract: dict):
        self.app = app
        self.policy = contract["transportPolicy"]
        self.identifier = re.compile(contract["requestIdPattern"])
        self.generation = re.compile(contract["pageGenerationPattern"])
        self.responses: dict[tuple[str, str], _Response] = {}
        self.seen: dict[str, set[str]] = {}

    def _owner(self, owner):
        if not isinstance(owner, str) or not self.generation.fullmatch(owner):
            raise ValueError("Invalid document generation")

    def _decode(self, value):
        method, path = value["method"], value["path"]
        if (method not in self.policy["allowedMethods"] or not isinstance(path, str)
                or not path.startswith("/") or path.startswith("//") or "\\" in path or "#" in path
                or any(ord(character) < 32 or ord(character) == 127 for character in path)
                or re.search(r"%(?:2e|2f|5c)", path, re.I)):
            raise ValueError("A local path and allowed HTTP method are required")
        raw_headers = value.get("headers", {})
        if not isinstance(raw_headers, dict):
            raise ValueError("Invalid request headers")
        headers = []
        for name, content in raw_headers.items():
            if (not isinstance(name, str) or not isinstance(content, str)
                    or not re.fullmatch(r"[A-Za-z0-9!#$%&'*+.^_`|~-]+", name)
                    or any(ord(character) < 32 or ord(character) == 127 for character in content)):
                raise ValueError("Invalid request headers")
            normalized = name.lower()
            if normalized in self.policy["forbiddenHeaderNames"] or any(
                normalized.startswith(prefix) for prefix in self.policy["forbiddenHeaderPrefixes"]
            ):
                raise ValueError("Request header is owned by the native runtime")
            headers.append((normalized.encode("ascii"), content.encode("latin-1")))
        encoded = value.get("bodyBase64")
        maximum = self.policy["maximumInlineRequestBytes"]
        if encoded is not None and (not isinstance(encoded, str) or len(encoded) > 4 * ((maximum + 2) // 3)):
            raise ValueError("Inline request body exceeds the shared policy")
        body = base64.b64decode(encoded, validate=True) if encoded is not None else b""
        if len(body) > maximum:
            raise ValueError("Inline request body exceeds the shared policy")
        url = urlsplit(path)
        scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"},
                 "http_version": "1.1", "method": method, "scheme": "https", "path": unquote(url.path, errors="strict"),
                 "raw_path": url.path.encode(), "query_string": url.query.encode(), "root_path": "", "headers": headers,
                 "client": None, "server": ("app", None)}
        return scope, body

    async def open(self, owner: str, value: dict) -> dict:
        self._owner(owner)
        request_id = value.get("clientRequestId")
        if not isinstance(request_id, str) or not self.identifier.fullmatch(request_id):
            raise ValueError("Invalid client request identifier")
        scope, body = self._decode(value)
        seen = self.seen.setdefault(owner, set())
        if request_id in seen:
            raise ValueError("Client request identifier has already been dispatched")
        seen.add(request_id)
        state = _Response(owner, request_id, uuid4().hex, asyncio.get_running_loop().create_future())
        self.responses[(owner, request_id)] = state
        state.task = asyncio.create_task(self._run(state, scope, body))
        return await state.head

    async def _run(self, state, scope, body):
        delivered = False

        async def receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            await state.disconnected.wait()
            return {"type": "http.disconnect"}

        async def send(message):
            if message["type"] == "http.response.start":
                if state.head.done():
                    raise RuntimeError("Duplicate ASGI response head")
                # Native owns response cookies; WebView receives no HttpOnly value.
                headers = {key.decode("latin-1"): value.decode("latin-1") for key, value in message.get("headers", [])
                           if key.lower() != b"set-cookie"}
                cookies = [value.decode("latin-1") for key, value in message.get("headers", []) if key.lower() == b"set-cookie"]
                state.head.set_result({"requestId": state.request_id, "streamId": state.stream_id,
                                       "status": message["status"], "headers": headers, "nativeCookies": cookies})
            elif message["type"] == "http.response.body":
                if not state.head.done() or state.ended:
                    raise RuntimeError("Invalid ASGI response body order")
                data = memoryview(message.get("body", b""))
                for offset in range(0, len(data), self.chunk_bytes):
                    await state.body.put(bytes(data[offset:offset + self.chunk_bytes]))
                if not message.get("more_body", False):
                    await state.body.put(None)
                    state.ended = True

        try:
            await self.app(scope, receive, send)
            if not state.head.done():
                raise RuntimeError("ASGI application returned without a response head")
            if not state.ended:
                raise RuntimeError("ASGI application returned without a final response body")
        except asyncio.CancelledError:
            if not state.head.done():
                state.head.cancel()
            raise
        except BaseException as failure:
            state.failure = failure
            if not state.head.done():
                state.head.set_exception(failure)
            else:
                await state.body.put(None)

    def _get(self, owner, value):
        self._owner(owner)
        state = self.responses.get((owner, value.get("requestId")))
        if state is None or value.get("streamId", state.stream_id) != state.stream_id:
            raise KeyError("Local response stream is unavailable")
        return state

    async def read(self, owner: str, value: dict) -> dict:
        state = self._get(owner, value)
        if value.get("streamId") != state.stream_id:
            raise KeyError("Local response stream is unavailable")
        maximum = value.get("maximumBytes", self.chunk_bytes)
        if type(maximum) is not int or not 0 < maximum <= self.chunk_bytes:
            raise ValueError("Invalid response chunk limit")
        if state.reading:
            raise ValueError("A response read is already pending")
        state.reading = True
        try:
            if not state.pending and not state.done:
                data = await state.body.get()
                if data is None:
                    state.done = True
                else:
                    state.pending = data
            data, state.pending = state.pending[:maximum], state.pending[maximum:]
            if state.done:
                self.responses.pop((owner, state.request_id), None)
                if state.failure:
                    raise state.failure
            return {"dataBase64": base64.b64encode(data).decode(), "done": state.done}
        finally:
            state.reading = False

    async def cancel(self, owner: str, value: dict) -> dict:
        self._owner(owner)
        state = self.responses.pop((owner, value.get("requestId")), None)
        if state is None:
            return {"cancelled": False}
        if value.get("streamId", state.stream_id) != state.stream_id:
            self.responses[(owner, state.request_id)] = state
            raise KeyError("Local response stream is unavailable")
        state.disconnected.set()
        state.failure = asyncio.CancelledError()
        state.pending = b""
        state.done = True
        while not state.body.empty():
            state.body.get_nowait()
        state.body.put_nowait(None)
        state.task.cancel()
        await asyncio.gather(state.task, return_exceptions=True)
        return {"cancelled": True}

    async def cancel_owner(self, owner: str):
        self._owner(owner)
        requests = [request_id for document, request_id in self.responses if document == owner]
        for request_id in requests:
            await self.cancel(owner, {"requestId": request_id})
        self.seen.pop(owner, None)
