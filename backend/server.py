#!/usr/bin/env python3
# [Input] Consume backend/.env, HTTP requests, database/auth/config modules.
# [Output] Publish FastAPI application and REST/SSE routes, including a
#          credential-free Claude SDK/CLI identity line during startup.
# [Pos] backend API entrypoint
# [Sync] 2026-05-24: load backend/.env before importing config and route modules.
# [Sync] 2026-05-24: keep only current Ink Agent env keys after dotenv loading.
# [Sync] 2026-05-25: split REST API routes into backend/routers modules.
# [Sync] 2026-06-09: allowlist INK_AGENT_EVENT_BUS_* / INK_AGENT_REDIS_URL for SSE EventBus config.
# [Sync] 2026-06-12: make CORS origin/credential policy environment-driven for cross-origin deployments.
# [Sync] 2026-06-14: expose robots.txt, sitemap.xml, and llms.txt from shared SEO content generators.
# [Sync] 2026-06-14: separate frontend public app URL from backend public API origin for SEO files.
# [Sync] 2026-06-23: register Google OAuth and Device Flow routers, initialize
#                    auth tables at startup, and add SessionMiddleware for
#                    Authlib OAuth state.
# [Sync] 2026-07-04: register the Notion resource connector router so connector
#                    auth, discovery, selection, and canonical snapshot sync
#                    endpoints are exposed alongside the rest of the backend API.
# [Sync] 2026-08-14: the mounted Deck router includes explicit default-plugin reconciliation.
# [Sync] 2026-08-22: prefer the explicitly configured Admin database env file
#                    over a stale backend/.env DATABASE_URL while preserving
#                    process-injected deployment configuration.
# [Sync] 2026-08-22: mount the fail-closed Claude MCP Resources router restored
#                    onto the current develop application graph.
# [Sync] 2026-08-22: preserve the centralized Claude Agent concurrency and
#                    host/cgroup memory-admission configuration keys.
# [Sync] 2026-08-26: fail startup closed unless the installed SDK metadata is
#                    ink-claude-dream-agent-sdk 0.2.144 and its preserved
#                    claude_agent_sdk import has no competing provider.
# [Sync] 2026-08-23: resolve the qualified Dream Runtime (or explicit absolute
#                    official rollback) before starting the Agent factory.
# [Sync] 2026-08-24: print validated SDK distribution and resolved CLI identity
#                    before the Claude Agent factory starts.
# [Sync] 2026-08-27: own the isolated Claude resource sampler, policy refresher,
#                    PostgreSQL sink, and publisher lifecycle around the database.
# [Sync] 2026-08-30: preserve the deployment-owned Claude Bash sandbox
#                    capability through startup Agent-env cleanup.
# [Sync] 2026-08-31: retire the PolyCLI get_writing_suggestion session; Writing
#                    inspiration now uses the existing Claude Agent SSE voice thread.
# [Sync] 2026-08-31: retire analyze_text after EditorEngine stops automatic
#                    model calls on ordinary Writing edits.
# [Sync] 2026-08-31: remove uncalled PolyCLI voice-chat and deep-analysis
#                    sessions; Voice Threads and Reflections tasks own those flows.
# [Sync] 2026-08-31: retire daily-picture generation, its scheduler, and the
#                    now-empty PolyCLI runtime; historical picture reads remain.
"""FastAPI application for Writing, Story Workspace, and Claude Agent APIs."""

import os
import time
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_ENV_FILE = Path(__file__).resolve().with_name(".env")
_DATABASE_URL_WAS_INHERITED = bool(os.environ.get("DATABASE_URL", "").strip())
load_dotenv(_BACKEND_ENV_FILE, override=False)

try:
    from persistence.config import load_database_url_from_env_file
except ModuleNotFoundError:  # pragma: no cover - package import compatibility
    from backend.persistence.config import load_database_url_from_env_file

if os.environ.get("INK_LOAD_DATABASE_URL_FROM_ENV_FILE") == "1":
    load_database_url_from_env_file(override=not _DATABASE_URL_WAS_INHERITED)


def _drop_unsupported_agent_env() -> None:
    """Remove stale Agent env aliases that are outside this project's contract."""

    allowed_ink_names = {
        "INK_AGENT_ENABLE_MEMORY_MCP",
        "INK_AGENT_MAX_CONCURRENT_RUNS",
        "INK_AGENT_RUN_MEMORY_BUDGET_MIB",
        "INK_AGENT_MEMORY_RESERVE_MIB",
        "INK_AGENT_RESOURCE_POLICY_REFRESH_INTERVAL_S",
        "INK_AGENT_TTL_S",
        "INK_AGENT_SWEEP_INTERVAL_S",
        "INK_AGENT_SSE_KEEPALIVE_S",
        "INK_AGENT_MAX_TURNS",
        "INK_AGENT_CONTEXT_SESSIONS",
        "INK_AGENT_EVENT_BUS_BACKEND",
        "INK_AGENT_REDIS_URL",
        "INK_AGENT_EVENT_BUS_TTL_S",
        # Sandbox runtime env contract (workspace.py).  Previously dropped
        # here at startup, which silently disabled the extra sandbox read
        # paths (the apply-seccomp settings override listed here briefly was
        # removed 2026-07-26 — proven dead in production; see workspace.py).
        "INK_AGENT_SANDBOX_ENABLED",
        "INK_AGENT_SANDBOX_EXTRA_ALLOW_READ",
    }
    os.environ.pop("ANTHROPIC_API_KEY", None)
    for key in list(os.environ):
        if key.startswith("INK_AGENT_MEM0_") or key in allowed_ink_names:
            continue
        if key.startswith("INK_AGENT_"):
            os.environ.pop(key, None)
            continue
        if key.startswith("CLAUDE_CODE_") and key.endswith("_TOKEN"):
            os.environ.pop(key, None)


_drop_unsupported_agent_env()

os.environ.setdefault("TZ", "UTC")
if hasattr(time, "tzset"):
    time.tzset()

import asyncio
import json
import logging
from datetime import datetime
import httpx
from fastapi import FastAPI, HTTPException, Depends, Header, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.sessions import SessionMiddleware
from seo_content import build_llms_txt, build_robots_txt, build_sitemap_xml
from typing import Any

# Import database module
import database

BACKEND_VERSION = os.environ.get("BACKEND_VERSION", "unknown")
PUBLIC_BASE_URL = os.environ.get("INK_PUBLIC_BASE_URL", "/")
BACKEND_PUBLIC_BASE_URL = os.environ.get("INK_BACKEND_PUBLIC_BASE_URL", PUBLIC_BASE_URL)


def _split_csv_env(name: str, default: str) -> list[str]:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        raw = default
    values = [value.strip() for value in raw.split(",") if value.strip()]
    return values


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


DEFAULT_CORS_ALLOW_ORIGINS = (
    "http://localhost,"
    "http://localhost:5173,"
    "http://127.0.0.1,"
    "http://127.0.0.1:5173"
)
CORS_ALLOW_ORIGINS = _split_csv_env("INK_CORS_ALLOW_ORIGINS", DEFAULT_CORS_ALLOW_ORIGINS)
CORS_ALLOW_CREDENTIALS = _bool_env("INK_CORS_ALLOW_CREDENTIALS", False)
SESSION_SECRET_KEY = (
    os.environ.get("SESSION_SECRET_KEY")
    or os.environ.get("JWT_SECRET")
    or os.environ.get("JWT_SECRET_KEY")
    or "dev-session-secret-change-in-production"
)
COOKIE_SECURE = _bool_env("COOKIE_SECURE", False)
COOKIE_SAMESITE = os.environ.get("COOKIE_SAMESITE", "lax").strip().lower()
if COOKIE_SAMESITE not in {"lax", "strict", "none"}:
    COOKIE_SAMESITE = "lax"


# ========== FastAPI Application ==========

app = FastAPI(
    title="Ink & Memory API",
    description="Writing, Story Workspace, and Claude Agent API",
    version="2.0.0",
)

print(f"🧾 Backend version: {BACKEND_VERSION}")

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET_KEY,
    same_site=COOKIE_SAMESITE,
    https_only=COOKIE_SECURE,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-New-Access-Token", "ETag"],
)

@app.on_event("startup")
async def startup_database():
    """Open PostgreSQL and verify the required Admin/Drizzle capabilities."""
    database.init_db()


# ========== Claude Agent Factory ==========

from agent_factory import (
    claude_agent_resource_postgres_sink,
    claude_agent_resource_policy_refresher,
    claude_agent_resource_publisher,
    claude_agent_resource_sampler,
    claude_agent_thread_factory,
)
from claude_agent.event_bus_redis import RedisStreamEventBus
from libs.claude_agent_kit.server.sdk_env import (
    DREAM_CLAUDE_CLI_EXECUTABLE,
    DREAM_CLAUDE_CLI_VERSION,
    DREAM_CLAUDE_SDK_IMPORT,
    require_dream_claude_sdk_distribution,
    resolve_claude_cli_path,
)
from services.deck.story_workflow_application import (
    story_workspace_get_dream_confirmation_coordinator,
)
from services.story_workspace.dream_launch_endpoint_service import (
    get_dream_launch_endpoint_service,
)
from routers.auth import (
    ImportDataRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    router as auth_router,
)
from routers.claude_agent import (
    ClaudeAgentRequestBody,
    CreateThreadResponseBody,
    ToolConfirmRequestBody,
    router as claude_agent_router,
)
from routers.device_oauth import OAuthProtocolError, router as device_oauth_router
from routers.friends import (
    FriendRequestActionRequest,
    UseInviteCodeRequest,
    router as friends_router,
)
from routers.oauth import router as oauth_router
from routers.pictures import router as pictures_router
from routers.preferences import router as preferences_router
from routers.notion import router as notion_router
from routers.product import router as product_router
from routers.reports import router as reports_router
from routers.sessions import SessionBatchRequest, router as sessions_router
from routers.storage import UploadUrlRequest, router as storage_router
from routers.deck_plugins import router as deck_plugins_router
from routers.claude_plugins import router as claude_plugins_router
from routers.claude_mcp import router as claude_mcp_router
from routers.deck_plugin_binding import router as deck_plugin_binding_router
from routers.deck_versions import router as deck_versions_router
from routers.story_workspace import router as story_workspace_router
from routers.system_config import router as system_config_router
from routers.gateway_models import router as gateway_models_router
from routers.workspace import router as workspace_router
from routers.reflections import router as reflections_router
from routers.voices import (
    DeckCreateRequest,
    DeckUpdateRequest,
    VoiceCreateRequest,
    VoiceForkRequest,
    VoiceUpdateRequest,
    router as voices_router,
)

@app.exception_handler(OAuthProtocolError)
async def oauth_protocol_error_handler(request, exc: OAuthProtocolError):
    """Return Device Flow token errors in RFC-style top-level JSON shape."""

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error,
            "error_description": exc.description,
        },
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )


@app.on_event("startup")
async def startup_validate_claude_agent_event_bus():
    """Reject invalid/unreachable shared EventBus configuration before turns."""

    backend = (
        os.environ.get("INK_AGENT_EVENT_BUS_BACKEND") or "memory"
    ).strip().lower()
    if backend not in {"memory", "redis"}:
        raise RuntimeError(
            "INK_AGENT_EVENT_BUS_BACKEND must be either 'memory' or 'redis'"
        )
    if backend == "redis":
        await RedisStreamEventBus.validate_connection()


def _claude_sdk_cli_compatibility_version() -> str:
    """Return the SDK-pinned Claude CLI version for startup diagnostics."""

    try:
        from claude_agent_sdk._cli_version import __cli_version__
    except (ImportError, AttributeError):
        return "unknown"
    return str(__cli_version__).strip() or "unknown"


def _print_claude_runtime_identity(distribution: Any, cli_path: str) -> None:
    """Print validated, non-secret SDK and CLI identity as one JSON log line."""

    installed_name = str(
        distribution.metadata.get("Name") or "unknown"
    ).strip() or "unknown"
    resolved_cli = Path(cli_path).resolve()
    override = str(os.environ.get("CLAUDE_CODE_CLI_PATH") or "").strip()
    override_active = False
    if override:
        try:
            override_active = Path(override).resolve() == resolved_cli
        except (OSError, RuntimeError):
            override_active = False
    is_dream_runtime = resolved_cli.name == DREAM_CLAUDE_CLI_EXECUTABLE
    identity = {
        "sdk_distribution": installed_name,
        "sdk_version": str(distribution.version),
        "sdk_import": DREAM_CLAUDE_SDK_IMPORT,
        "sdk_cli_compatibility_version": (
            _claude_sdk_cli_compatibility_version()
        ),
        "cli_path": str(resolved_cli),
        "cli_mode": "explicit_override" if override_active else "dream_runtime",
        "cli_runtime_release": (
            DREAM_CLAUDE_CLI_VERSION if is_dream_runtime else "external"
        ),
    }
    print(
        "🤖 Claude Agent runtime: "
        + json.dumps(identity, ensure_ascii=False, sort_keys=True),
        flush=True,
    )


@app.on_event("startup")
async def startup_claude_agent():
    """Start the Claude Agent session pool sweeper."""
    distribution = require_dream_claude_sdk_distribution()
    cli_path = resolve_claude_cli_path()
    if not cli_path:
        raise RuntimeError(
            "Claude Agent Runtime is unavailable; install a production-qualified "
            "ink-claude-code-dream release or configure an explicit absolute "
            "CLAUDE_CODE_CLI_PATH rollback."
        )
    _print_claude_runtime_identity(distribution, cli_path)
    claude_agent_thread_factory.start()
    for resource_owner in (
        claude_agent_resource_sampler,
        claude_agent_resource_policy_refresher,
        claude_agent_resource_postgres_sink,
        claude_agent_resource_publisher,
    ):
        try:
            resource_owner.start()
        except Exception:
            logging.getLogger(__name__).exception(
                "Claude Agent resource observer owner failed to start"
            )
    print("✅ Claude Agent factory started\n")


@app.on_event("startup")
async def story_workspace_startup_dream_confirmation_coordinator():
    """Reconcile accepted Dream confirmations after the Agent is ready."""

    story_workspace_get_dream_confirmation_coordinator().start()


@app.on_event("startup")
async def story_workspace_startup_dream_launch_dispatches():
    """Enable process-owned launch turn drains."""

    get_dream_launch_endpoint_service().start()


@app.on_event("startup")
async def startup_claude_plugin_seed():
    """Seed platform-builtin Claude plugins and backfill Deck references.

    Uses the real CLI (``claude plugin validate``) for evidence.  Failure is
    non-fatal: the app starts normally and the operation record carries the
    error; installs can be retried from Settings → Plugins.
    """

    def _seed() -> None:
        import database as _database
        from services.claude_plugin.builtin_sources import PLATFORM_BUILTIN_SOURCES
        from services.claude_plugin.install_service import (
            PluginInstallError,
            PluginInstallService,
        )

        db = _database.get_db()
        try:
            service = PluginInstallService(db)
            for canonical in PLATFORM_BUILTIN_SOURCES:
                existing = db.execute(
                    "SELECT id, resolved_version, artifact_digest FROM "
                    "claude_plugin_installations WHERE package_name = %s AND "
                    "marketplace = %s AND status = 'ready' ORDER BY created_at DESC "
                    "LIMIT 1",
                    (canonical.split("@")[0], canonical.split("@")[1]),
                ).fetchone()
                if existing is None:
                    try:
                        service.install(canonical, source_type="platform-builtin")
                    except PluginInstallError as exc:
                        logging.getLogger(__name__).warning(
                            "platform-builtin plugin seed failed for %s: %s",
                            canonical,
                            exc,
                        )
                        continue
                    existing = db.execute(
                        "SELECT id, resolved_version, artifact_digest FROM "
                        "claude_plugin_installations WHERE package_name = %s AND "
                        "marketplace = %s AND status = 'ready' ORDER BY created_at "
                        "DESC LIMIT 1",
                        (canonical.split("@")[0], canonical.split("@")[1]),
                    ).fetchone()
                if existing is None:
                    continue
                created = _database.backfill_builtin_deck_plugin_refs(
                    db,
                    builtin_installation_id=existing[0],
                    package_spec=canonical,
                    resolved_version=existing[1],
                    artifact_digest=existing[2],
                )
                if created:
                    logging.getLogger(__name__).info(
                        "backfilled %d deck Claude plugin refs for %s",
                        created,
                        canonical,
                    )
        finally:
            db.close()

    try:
        await asyncio.to_thread(_seed)
    except Exception:  # noqa: BLE001 - seeding must never block startup
        logging.getLogger(__name__).exception("claude plugin seed failed")


@app.on_event("shutdown")
async def story_workspace_shutdown_dream_confirmation_coordinator():
    """Stop reconciliation before closing the Claude Agent factory."""

    await story_workspace_get_dream_confirmation_coordinator().stop()


@app.on_event("shutdown")
async def story_workspace_shutdown_dream_launch_dispatches():
    """Await launch turn drains before closing the Claude Agent factory."""

    await get_dream_launch_endpoint_service().aclose()


@app.on_event("shutdown")
async def shutdown_claude_agent():
    """Gracefully close all Claude Agent sessions."""
    for resource_owner in (
        claude_agent_resource_publisher,
        claude_agent_resource_policy_refresher,
        claude_agent_resource_postgres_sink,
        claude_agent_resource_sampler,
    ):
        try:
            await resource_owner.stop()
        except Exception:
            logging.getLogger(__name__).exception(
                "Claude Agent resource observer owner failed to close"
            )
    try:
        await claude_agent_thread_factory.aclose()
    except Exception:
        logging.getLogger(__name__).exception("Claude Agent factory close failed")
    try:
        # No producer may retain the process-wide Redis connection after the
        # factory drain. ``aclose`` resets its slot for test/app reloads.
        await RedisStreamEventBus.aclose()
    except Exception:
        logging.getLogger(__name__).exception("Agent Redis EventBus close failed")
    print("✅ Claude Agent factory closed\n")


@app.on_event("shutdown")
async def shutdown_database():
    """Close PostgreSQL only after every Agent/business owner has settled."""

    database.close_db()



# ========== Custom API Endpoints (Clean Interface) ==========


@app.get("/")
def root():
    """Root endpoint"""
    base = BACKEND_PUBLIC_BASE_URL.rstrip("/") + "/"
    return PlainTextResponse(
        f"The server is configured with a public base URL of {base}"
        f" - did you mean to visit {base}api/claude-agent/threads instead?"
    )


@app.get("/robots.txt", include_in_schema=False)
def robots_txt():
    """Machine-readable crawler access policy for the public app."""
    return PlainTextResponse(
        build_robots_txt(PUBLIC_BASE_URL),
        media_type="text/plain; charset=utf-8",
    )


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap_xml():
    """XML sitemap for the public app surface."""
    return Response(
        build_sitemap_xml(PUBLIC_BASE_URL),
        media_type="application/xml; charset=utf-8",
    )


@app.get("/llms.txt", include_in_schema=False)
def llms_txt():
    """Structured app summary for AI search and LLM crawlers."""
    return PlainTextResponse(
        build_llms_txt(PUBLIC_BASE_URL, BACKEND_PUBLIC_BASE_URL),
        media_type="text/plain; charset=utf-8",
    )


@app.get("/api/health")
def health():
    """Health endpoint for deploy scripts, Compose healthchecks, and Cloud Run probes."""
    return {
        "status": "ok",
        "version": BACKEND_VERSION,
        "cors_allow_origins": CORS_ALLOW_ORIGINS,
    }


# ========== Router Registration ==========

app.include_router(auth_router)
app.include_router(oauth_router)
app.include_router(device_oauth_router)
app.include_router(sessions_router)
app.include_router(pictures_router)
app.include_router(preferences_router)
app.include_router(notion_router)
app.include_router(product_router)
app.include_router(reports_router)
app.include_router(voices_router)
app.include_router(friends_router)
app.include_router(claude_agent_router)
app.include_router(storage_router)
app.include_router(deck_plugins_router)
app.include_router(claude_plugins_router)
app.include_router(claude_mcp_router)
app.include_router(deck_plugin_binding_router)
app.include_router(deck_versions_router)
app.include_router(story_workspace_router)
app.include_router(system_config_router)
app.include_router(gateway_models_router)
app.include_router(workspace_router)
app.include_router(reflections_router)


@app.websocket("/ws/speech-recognition")
async def speech_recognition(websocket: WebSocket):
    # ASR Gateway is explicitly deferred for the Token-only release. Keep the
    # legacy route fail-closed so no browser can stream audio or trigger a
    # third-party request without the future authentication/limit design.
    await websocket.close(code=1008, reason="Speech recognition is not enabled")


# ========== Main ==========

if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 60)
    print("🎭 Ink & Memory FastAPI Server")
    print(f"🧾 Version: {BACKEND_VERSION}")
    print("=" * 60)
    print("\n📚 API Endpoints:")
    print("    GET  /api/health         - Health check")
    print("  Auth & User:")
    print("    POST /api/register        - Register new user")
    print("    POST /api/login           - Login")
    print("    GET  /api/me              - Get current user")
    print("  Data Storage:")
    print("    POST /api/sessions        - Save session")
    print("    GET  /api/sessions        - List sessions")
    print("    GET  /api/sessions/{id}   - Get session")
    print("    DELETE /api/sessions/{id} - Delete session")
    print("    GET  /api/pictures        - List pictures")
    print("    GET  /api/pictures/{date}/full - Get full picture by date")
    print("    GET  /api/preferences     - Get user preferences")
    print("    POST /api/preferences     - Save preferences")
    print("    GET  /api/reports         - Get analysis reports")
    print("    POST /api/reports         - Save report")
    print("  Configuration:")
    print("    GET  /api/default-voices  - Get default voice configs")
    print("  Deck & Voice Management:")
    print("    GET  /api/decks           - List all decks")
    print("    GET  /api/decks/{id}      - Get deck with voices")
    print("    POST /api/decks           - Create deck")
    print("    PUT  /api/decks/{id}      - Update deck")
    print("    DELETE /api/decks/{id}    - Delete deck")
    print("    POST /api/decks/{id}/fork - Fork deck")
    print("    POST /api/voices          - Create voice")
    print("    PUT  /api/voices/{id}     - Update voice")
    print("    DELETE /api/voices/{id}   - Delete voice")
    print("    POST /api/voices/{id}/fork - Fork voice")
    print("  Friend System:")
    print("    POST /api/friends/invite/generate - Generate invite code")
    print("    POST /api/friends/invite/use      - Use invite code")
    print("    GET  /api/friends/requests        - Get friend requests")
    print("    POST /api/friends/requests/{id}/accept - Accept request")
    print("    POST /api/friends/requests/{id}/reject - Reject request")
    print("    GET  /api/friends                 - Get friends list")
    print("    DELETE /api/friends/{id}          - Remove friend")
    print("    GET  /api/friends/{id}/timeline   - Get friend's timeline")
    print("    GET  /api/friends/{id}/pictures/{date}/full - Get friend's full picture")
    print("\n  Claude Agent:")
    print("    POST /api/claude-agent                 - Stream agent response (SSE)")
    print("    GET  /api/claude-agent/chat-history    - Get recent sessions for context")
    print("    POST /api/claude-agent/message-latency - Record message latency metrics")
    print("    GET  /api/claude-agent/session         - Get active session snapshot")
    print("    DELETE /api/claude-agent/session       - Close active session")
    print("    POST /api/claude-agent/tool-confirm    - Resolve pending tool confirmation")
    print("\n  Documentation:")
    print("    /docs                     - Auto-generated API docs")
    print("=" * 60 + "\n")

    uvicorn.run(app, host="127.0.0.1", port=8765)
