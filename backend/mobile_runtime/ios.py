# [Input] Bundled CPython, pinned dependencies, production business routers and shared transport policy.
# [Output] One in-process ASGI application, native pull transport and application-owned HTTP for original Next.
# [Pos] iOS backend composition; data authority and Claude execution require qualified owners.
# [Sync] 2026-10-25: keep one persistent ASGI event loop and use bounded pull streaming/cancellation.
# [Sync] 2026-10-25: bind the actual original Factory before mounting the canonical 24-router inventory.
# [Sync] 2026-10-25: bind the native-owned original Runtime endpoint without exposing its authentication metadata.
# [Sync] 2026-10-25: start original Next against the same ASGI application; retry observation preserves bound owners.
# [Sync] 2026-10-25: load the application's regular .env before importing the original configuration consumers.
# [Sync] 2026-10-25: bind the original production request/data owner and managed MCP composition before protected routes.
# [Sync] 2026-10-25: bind the existing plugin runtime root to the same application data container as workspaces/files.
# [Sync] 2026-10-26: restore bundled immutable plugin artifacts and bind original CLI checks to the native Runtime.
# [Sync] 2026-10-26: bind the original confirmation worker for explicit message dispatch without a global claim scan.

import asyncio
import base64
import json
import os
from pathlib import Path
import platform
import sys
import threading
import tomllib
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[1] / ".env", override=False)
# Preserve the original FastAPI/Next ownership for the BFF's Cookie key.
# Node retains the original frontend/.env.local for its own configuration consumers.
os.environ.pop("INK_DREAM_BFF_COOKIE_SECRET", None)

from fastapi import FastAPI
from routers.public import create_public_router
from .asgi_transport import NativeASGITransport

_contract = json.loads((Path(__file__).parents[2] / "mobile/shared/bridge/contract.json").read_text())
_policy = _contract["transportPolicy"]
_business_routers = ()
_loop = None
_app = None
_lifespan = None
_transport = None
_claude_endpoint = None
_factory_owner = None
_admin_request_owner = None
_http_owner = None
_web_origin = None
_startup_lock = threading.Lock()


def _submit(coroutine):
    if _loop is None:
        coroutine.close()
        raise RuntimeError("Dream Python backend has not started")
    return asyncio.run_coroutine_threadsafe(coroutine, _loop).result()


async def _initialize():
    global _app, _lifespan, _transport
    if sys.platform == "ios":
        # Match the original backend process's default directory using bundled
        # sources. Workspace Mode still owns its separate optional per-turn cwd.
        os.chdir(Path(__file__).parents[1])
    with (Path(__file__).parents[1] / "pyproject.toml").open("rb") as source:
        version = tomllib.load(source)["project"]["version"]
    _app = FastAPI(title="Ink & Memory API", docs_url=None, redoc_url=None, openapi_url=None)
    _app.include_router(create_public_router(backend_version=version, cors_allow_origins=[],
                                              public_base_url="/", backend_public_base_url="/"))
    _lifespan = _app.router.lifespan_context(_app)
    await _lifespan.__aenter__()
    _transport = NativeASGITransport(_app, _contract)


async def _bind_runtime(endpoint):
    global _claude_endpoint, _factory_owner, _admin_request_owner, _business_routers, _http_owner, _web_origin
    if _claude_endpoint is not None:
        if endpoint != _claude_endpoint:
            raise RuntimeError("DREAM_AGENT_OWNER_ALREADY_BOUND")
    else:
        from .ios_claude_transport import read_native_endpoint
        native = read_native_endpoint(endpoint)
        root = Path(native["workspaceRoot"])
        # These values are owned by this application sandbox before any router or
        # storage singleton imports them. Files stay in this application's sandbox.
        os.environ["AGENT_CWD"] = str(root)
        storage = root.parent / "files"
        storage.mkdir(mode=0o700, exist_ok=True)
        os.chmod(storage, 0o700)
        os.environ["FILE_STORAGE_LOCAL_DIR"] = str(storage)
        os.environ["INK_CLAUDE_PLUGIN_RUNTIME_ROOT"] = str(root.parent / "claude-plugin-runtime")
        from .ios_plugin_runtime import prepare_plugin_runtime
        prepare_plugin_runtime(endpoint)
        if _admin_request_owner is None:
            from services.admin_data import AdminDataConfig
            from services.admin_data.request_auth import create_production_admin_request_auth
            from claude_mcp.service import configure_default_claude_mcp_service
            owner = create_production_admin_request_auth(AdminDataConfig.from_env())
            try:
                configure_default_claude_mcp_service(owner.client)
            except BaseException:
                owner.close()
                raise
            _admin_request_owner = owner
            _app.state.admin_request_auth = owner
        from .ios_factory import IOSFactoryOwner
        from claude_agent.runtime_owner import bind_thread_factory
        from routers import load_business_routers
        if _factory_owner is None:
            _factory_owner = IOSFactoryOwner(endpoint)
            bind_thread_factory(_factory_owner.factory)
        if _factory_owner.endpoint != endpoint:
            raise RuntimeError("DREAM_AGENT_OWNER_ALREADY_BOUND")
        modules = load_business_routers()
        for module in modules:
            _app.include_router(module.router)
        from services.deck.story_workflow_application import story_workspace_get_dream_confirmation_coordinator
        story_workspace_get_dream_confirmation_coordinator().bind_worker(
            _admin_request_owner.story_workspace_confirmation_worker()
        )
        _factory_owner.start()
        _business_routers = modules
        _claude_endpoint = endpoint
    from .ios_http import IOSHTTPServer
    if _http_owner is None:
        _http_owner = IOSHTTPServer(_app)
    await _http_owner.start()
    from .ios_claude_transport import start_native_web
    _web_origin = await start_native_web(endpoint, _http_owner.origin)


async def _complete(value):
    owner = "native_" + uuid4().hex
    try:
        head = await _transport.open(owner, {**value, "clientRequestId": uuid4().hex})
        body = bytearray()
        while True:
            chunk = await _transport.read(owner, {"requestId": head["requestId"], "streamId": head["streamId"]})
            body.extend(base64.b64decode(chunk["dataBase64"]))
            if chunk["done"]:
                break
        return {"status": head["status"], "headers": head["headers"], "body": body.decode("utf-8")}
    finally:
        await _transport.cancel_owner(owner)


def start(payload: str | None = None) -> str:
    global _loop
    with _startup_lock:
        if _loop is None:
            _loop = asyncio.new_event_loop()
            threading.Thread(target=_loop.run_forever, name="DreamASGI", daemon=True).start()
            try:
                _submit(_initialize())
            except BaseException:
                _loop.call_soon_threadsafe(_loop.stop)
                _loop = None
                raise
    health = _submit(_complete({"method": "GET", "path": "/api/health"}))
    if health["status"] != 200:
        raise RuntimeError("Dream health handler did not return HTTP 200")
    runtime = None
    if payload is not None:
        from .ios_claude_transport import query_native_status
        endpoint = json.loads(payload)["runtimeEndpoint"]
        runtime = _submit(query_native_status(endpoint))
        with _startup_lock:
            _submit(_bind_runtime(endpoint))
    return json.dumps({
        "pythonVersion": platform.python_version(), "platform": sys.platform,
        "simulator": platform.ios_ver().is_simulator if sys.platform == "ios" else None,
        "health": json.loads(health["body"]),
        "routes": sorted(route.path for route in _app.routes),
        "businessRouterModules": [module.__name__ for module in _business_routers],
        "businessReady": False,
        "resourcePolicyStatus": _factory_owner.policy.status if _factory_owner else None,
        "localBackendOrigin": _http_owner.origin if _http_owner else None,
        "localWebOrigin": _web_origin,
        "embeddedNode": runtime,
    })


def request(payload: str) -> str:
    if _transport is None:
        raise RuntimeError("Dream Python backend has not started")
    return json.dumps(_submit(_complete(json.loads(payload))))


def bridge(payload: str) -> str:
    """Native-owned envelope dispatch; no new HTTP endpoint is registered."""
    if _transport is None:
        raise RuntimeError("Dream Python backend has not started")
    value = json.loads(payload)
    operation = {"runtime.request": _transport.open, "runtime.response.read": _transport.read,
                 "runtime.cancel": _transport.cancel}.get(value["method"])
    if operation is None:
        raise ValueError("Invalid native transport operation")
    return json.dumps(_submit(operation(value["pageGeneration"], value["params"])))


def close_document(payload: str) -> str:
    value = json.loads(payload)
    _submit(_transport.cancel_owner(value["pageGeneration"]))
    return "{}"
