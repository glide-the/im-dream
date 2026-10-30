# [Input] The already composed production ASGI application and its persistent event loop.
# [Output] One application-owned Uvicorn/h11 listener bound only to an ephemeral IPv4 loopback port.
# [Pos] Existing Next-to-Python HTTP transport on iOS; no business handlers or authentication are replaced.
# [Sync] 2026-10-25: close owned sockets after startup/serve failures and preserve an active listener on observation retries.
# [Sync] 2026-10-26: observe only registered Dream launch error codes after forwarding unchanged ASGI frames.
from __future__ import annotations

import asyncio
import json
import socket

import uvicorn


def _observe_dream_launch_errors(app):
    """Keep original HTTP semantics; emit no request or response content."""
    async def observed(scope, receive, send):
        if (scope.get("type"), scope.get("method"), scope.get("path")) != (
            "http", "POST", "/api/story-workspace/dream-runs/start"
        ):
            return await app(scope, receive, send)
        status = 0
        body = bytearray()
        oversized = False

        async def forward(message):
            nonlocal status, oversized
            await send(message)
            if message["type"] == "http.response.start":
                status = message["status"]
            elif message["type"] == "http.response.body" and 400 <= status < 600:
                chunk = message.get("body", b"")
                if not oversized and len(body) + len(chunk) <= 4096:
                    body.extend(chunk)
                else:
                    oversized = True
                    body.clear()
                if not message.get("more_body", False):
                    code = "UNCLASSIFIED"
                    try:
                        from services.errors.error_registry import registered_error_codes
                        payload = json.loads(body) if not oversized else None
                        if isinstance(payload, dict):
                            error = payload.get("error", payload.get("detail", payload))
                            candidate = error.get("code", error.get("error_code")) if isinstance(error, dict) else error
                            if isinstance(candidate, str) and candidate in registered_error_codes():
                                code = candidate
                    except (ValueError, TypeError, RecursionError):
                        pass
                    try:
                        print("IOS_DREAM_HTTP_FAILURE " + json.dumps({
                            "operation": "dream.launch", "status": status, "code": code,
                        }), flush=True)
                    except Exception:
                        # A diagnostics sink failure cannot change the response.
                        pass

        return await app(scope, receive, forward)
    return observed


class IOSHTTPServer:
    def __init__(self, app):
        self._app = _observe_dream_launch_errors(app)
        self._server = None
        self._task = None
        self._socket = None
        self.origin = None

    async def start(self):
        if self._task is not None:
            if self._task.done():
                await self._task
                raise RuntimeError("DREAM_HTTP_SERVER_STOPPED")
            return
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            listener.bind(("127.0.0.1", 0))
        except BaseException:
            listener.close()
            raise
        listener.setblocking(False)
        self._socket = listener
        self._server = uvicorn.Server(uvicorn.Config(
            self._app, host="127.0.0.1", port=0, loop="asyncio", http="h11", ws="none",
            # The same application's ASGI lifespan has already been entered.
            lifespan="off", access_log=False, log_config=None,
        ))
        self._task = asyncio.create_task(self._server.serve(sockets=[listener]), name="DreamApplicationHTTP")

        async def ready():
            while not self._server.started:
                if self._task.done():
                    await self._task
                    raise RuntimeError("DREAM_HTTP_SERVER_START_FAILED")
                await asyncio.sleep(0.01)

        try:
            await asyncio.wait_for(ready(), timeout=10)
        except BaseException:
            await self.close()
            raise
        self.origin = "http://127.0.0.1:" + str(listener.getsockname()[1])

    async def close(self):
        try:
            if self._server is not None:
                self._server.should_exit = True
            if self._task is not None:
                try:
                    await asyncio.wait_for(asyncio.shield(self._task), timeout=5)
                except TimeoutError:
                    self._task.cancel()
                    await asyncio.gather(self._task, return_exceptions=True)
        finally:
            if self._socket is not None:
                self._socket.close()
            self._task = self._server = self._socket = self.origin = None
