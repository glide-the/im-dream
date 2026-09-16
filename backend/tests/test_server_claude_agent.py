# [Input] Consume server.py (FastAPI app) and claude_agent module.
# [Output] Verify that claude-agent and Notion connector routes are registered,
#          factory is initialised, request/response models are correct, and
#          authentication is enforced.
# [Pos] test node in backend/tests
# [Sync] 2026-09-16: assert Admin HTTP owner ordering after removing Dream PostgreSQL lifecycle.
# [Sync] 2026-09-13: expect the package-root Runtime 0.1.9 identity in startup diagnostics.
# [Sync] 2026-09-15: expect the package-root Runtime 0.1.10 identity.
# [Sync] 2026-05-22: initial — smoke tests for /api/claude-agent/* routes in server.py.
#                    Adapted from Pawkeyland scripts/test_demo_server_import.py
#                    (removed pet/persona/sticker/necklace contract tests).
# [Sync] 2026-05-24: cover server startup cleanup of unsupported Agent env keys.
# [Sync] 2026-06-22: cover Claude Agent route attachment handling when Settings
#                    Workspace Mode is disabled.
# [Sync] 2026-06-25: cover thread-scoped stop endpoint registration and routing.
# [Sync] 2026-07-04: cover Notion connector router registration and auth gating.
# [Sync] 2026-08-17: cover same-Deck Agent switching, provenance metadata, and CAS conflicts.
# [Sync] 2026-08-22: cover restored Claude MCP Resources router registration.
# [Sync] 2026-08-22: cover startup preservation of Claude Agent resource-admission keys.
# [Sync] 2026-08-28: cover composition-owned higher-revision replacement,
#                    same-revision diagnostics-only refresh, and lifecycle ordering.
# [Sync] 2026-08-31: remove obsolete legacy-session, image scheduler, and stateless analyzer stubs;
#                    assert pictures are read-only and the legacy mount is absent.
# [Sync] 2026-08-23: cover fail-closed custom SDK distribution validation before
#                    the Claude Agent factory starts.
# [Sync] 2026-08-28: pin startup diagnostics to SDK 0.2.144 and Runtime 0.1.3.
# [Sync] 2026-08-30: advance the production identity receipt to qualified
#                    Runtime 0.1.4 without changing CLI compatibility 2.1.241.
# [Sync] 2026-08-30: preserve deployment-owned disabled Bash sandbox
#                    capability through server startup env cleanup.
# [Sync] 2026-08-24: cover credential-free SDK/CLI startup identity logging.
# [Sync] 2026-08-25: align MCP auth route registration with database server identifiers.
# [Sync] 2026-08-27: cover PostgreSQL resource sampler/sink/publisher lifecycle ordering.
# [Sync] 2026-09-01: cover public Dream auto-repair metadata projection and reserved IDs.
# [Sync] 2026-09-01: preserve exact server-owned projectCleanup facts through
#                    the existing history DTO without adding an SSE protocol.
# [Sync] 2026-09-01: retain already-persisted v1 repair rows that predate the
#                    projectCleanup fact without granting them execution scope.
# [Sync] 2026-09-02: cover stable message cursors, ID-only stabilization,
#                    large-body integrity, and completed-turn metadata projection.
# [Sync] 2026-09-02: cover final-only page flags and owned exact-id process detail.
# [Sync] 2026-09-04: cover the authenticated backend common Skill slash catalog.
# [Sync] 2026-09-15: update direct Chat route tests to explicit typed Admin fakes with Dream database fenced.
# [Sync] 2026-09-15: require Registry105 Deck context before Chat persistence and reuse its immutable DTO.

"""Smoke tests for the Claude Agent HTTP routes in server.py.

Tests run without starting a real uvicorn server; they inspect route registration
and Pydantic model contracts via FastAPI's test client (httpx).

Requirements: server must be importable (database, config, etc. must initialise
without error in the test environment — SQLite is created at first import).
"""
from __future__ import annotations

import json
import os
import sys
import types
import unittest
import unittest.mock
import asyncio
import threading
from datetime import datetime, timezone
from pathlib import Path

from services.admin_data.chat_models import (
    ChangedResultDTO,
    ChatMessageDTO,
    ChatThreadDTO,
    LatestMessageResultDTO,
    MessageDetailResultDTO,
    MessageListResultDTO,
    MessagePageResultDTO,
    ThreadResultDTO,
)
from services.admin_data.errors import AdminDataError
from services.admin_data.deck_chat_context_data import (
    AdminDeckChatContextResolution,
    DeckChatContextInputDTO,
    DeckChatContextOutputDTO,
)
from services.admin_data.request_auth import AdminRequestActor
from services.admin_data.system_config_data import SystemConfigGetInputDTO
from services.admin_data.workflow_data import AdminWorkflowResolution

ROOT = Path(__file__).resolve().parents[1]  # backend/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# Lightweight stubs so server.py imports don't crash without full runtime.
# ---------------------------------------------------------------------------

def _stub_module(name: str, **attrs) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__dict__.update(attrs)
    sys.modules[name] = mod
    return mod


# Stub claude_agent_sdk so runner.py doesn't fail on import
if "claude_agent_sdk" not in sys.modules:
    sdk_types = _stub_module("claude_agent_sdk.types")

    class _SdkStub:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    class AssistantMessage(_SdkStub):
        pass

    class ClaudeAgentOptions(_SdkStub):
        pass

    class HookContext(_SdkStub):
        pass

    class HookJSONOutput(_SdkStub):
        pass

    class HookMatcher(_SdkStub):
        pass

    class McpServerConfig(_SdkStub):
        pass

    class McpStdioServerConfig(_SdkStub):
        pass

    class PermissionResult(_SdkStub):
        pass

    class PermissionResultAllow(_SdkStub):
        pass

    class PermissionResultDeny(_SdkStub):
        pass

    class ResultMessage(_SdkStub):
        pass

    class StreamEvent(_SdkStub):
        pass

    class SystemMessage(_SdkStub):
        pass

    class ToolPermissionContext(_SdkStub):
        pass

    class UserMessage(_SdkStub):
        pass

    for _cls in [
        AssistantMessage,
        ClaudeAgentOptions,
        HookContext,
        HookJSONOutput,
        HookMatcher,
        McpServerConfig,
        McpStdioServerConfig,
        PermissionResult,
        PermissionResultAllow,
        PermissionResultDeny,
        ResultMessage,
        StreamEvent,
        SystemMessage,
        ToolPermissionContext,
        UserMessage,
    ]:
        setattr(sdk_types, _cls.__name__, _cls)

    class ClaudeSDKClient:
        pass

    _stub_module("claude_agent_sdk", ClaudeSDKClient=ClaudeSDKClient, query=None, types=sdk_types)

# Stub heavy optional dependencies so server.py can be imported in minimal envs.

def _stub_deep(dotted_path: str, **attrs):
    """Ensure every segment of dotted_path exists as a stub module."""
    parts = dotted_path.split(".")
    for i in range(1, len(parts) + 1):
        name = ".".join(parts[:i])
        if name not in sys.modules:
            mod = _stub_module(name)
        else:
            mod = sys.modules[name]
    mod.__dict__.update(attrs)
    return mod


# dashscope / speech recognition
if "dashscope" not in sys.modules:
    _stub_deep("dashscope")

# ---------------------------------------------------------------------------
# Try to import server — skip all tests if full deps not installed
# ---------------------------------------------------------------------------

_SERVER_MODULE = None
_SERVER_SKIP_REASON = None

try:
    import server as _SERVER_MODULE  # noqa: E402
except Exception as _e:  # noqa: BLE001
    _SERVER_SKIP_REASON = f"server.py cannot be imported in this environment: {_e}"


def _skip_if_no_server(cls):
    """Class decorator: skip all tests when server.py is not importable."""
    if _SERVER_SKIP_REASON:
        return unittest.skip(_SERVER_SKIP_REASON)(cls)
    return cls


def _admin_user(user_id: int = 7) -> dict:
    actor = AdminRequestActor(
        "test-subject",
        str(user_id),
        "dream-browser",
        frozenset({"dream:read", "dream:write"}),
        1,
        2,
        "test-oauth-token",
    )
    return {"user_id": user_id, "_admin_actor": actor}


def _thread_dto(value: dict | None) -> ChatThreadDTO | None:
    if value is None:
        return None
    return ChatThreadDTO(
        id=str(value["id"]),
        user_id=str(value.get("user_id", 7)),
        title=value.get("title"),
        deck_id=value.get("deck_id"),
        voice_id=value.get("voice_id"),
        claude_session_id=value.get("claude_session_id"),
        agent_contract_version=value.get("agent_contract_version"),
        created_at=value.get("created_at"),
        updated_at=value.get("updated_at"),
    )


def _message_dto(value: dict) -> ChatMessageDTO:
    parts = value.get("parts", [])
    if isinstance(parts, str):
        try:
            parts = json.loads(parts)
        except (TypeError, ValueError):
            parts = []
    metadata = value.get("metadata")
    metadata_decode_error = value.get("metadata_decode_error", False)
    if isinstance(metadata, str):
        try:
            decoded = json.loads(metadata)
        except (TypeError, ValueError):
            decoded = None
            metadata_decode_error = True
        if not isinstance(decoded, dict):
            metadata_decode_error = True
        metadata = decoded if isinstance(decoded, dict) else None
    elif metadata is not None and not isinstance(metadata, dict):
        metadata = None
        metadata_decode_error = True
    created_at = value.get("created_at")
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()
    return ChatMessageDTO(
        id=str(value["id"]),
        role=value["role"],
        parts=parts,
        metadata=metadata,
        metadata_decode_error=metadata_decode_error,
        created_at=created_at,
        history_final_text=value.get("history_final_text"),
        history_process_available=value.get("history_process_available", False),
        history_projection_version=value.get("history_projection_version"),
    )


class _FakeAdminChatData:
    def __init__(self, *, thread: dict | None, messages=None, page=None,
        latest_message_id: str | None = None, detail=None,
        select_voice_changed: bool = True) -> None:
        self.thread = _thread_dto(thread)
        self.messages = list(messages or [])
        self.page = page
        self.latest_message_id = latest_message_id
        self.detail = detail
        self.select_voice_changed = select_voice_changed
        self.calls: list[tuple[str, object]] = []

    def get_thread(self, input_dto, _request_id, *, access_token):
        assert access_token == "test-oauth-token"
        self.calls.append(("get_thread", input_dto))
        return ThreadResultDTO(thread=self.thread)

    def list_messages(self, input_dto, _request_id, *, access_token):
        assert access_token == "test-oauth-token"
        self.calls.append(("list_messages", input_dto))
        return MessageListResultDTO(
            messages=[_message_dto(item) for item in self.messages]
        )

    def message_page(self, input_dto, _request_id, *, access_token):
        assert access_token == "test-oauth-token"
        self.calls.append(("message_page", input_dto))
        page = self.page or {
            "messages": [], "has_more": False,
            "latest_message_id": self.latest_message_id,
        }
        return MessagePageResultDTO(
            messages=[_message_dto(item) for item in page["messages"]],
            has_more=page["has_more"],
            latest_message_id=page.get("latest_message_id"),
        )

    def latest_message(self, input_dto, _request_id, *, access_token):
        assert access_token == "test-oauth-token"
        self.calls.append(("latest_message", input_dto))
        return LatestMessageResultDTO(message_id=self.latest_message_id)

    def process_detail(self, input_dto, _request_id, *, access_token):
        assert access_token == "test-oauth-token"
        self.calls.append(("process_detail", input_dto))
        return MessageDetailResultDTO(
            message=_message_dto(self.detail) if self.detail is not None else None
        )

    def select_voice(self, input_dto, _request_id, *, access_token):
        assert access_token == "test-oauth-token"
        self.calls.append(("select_voice", input_dto))
        return ChangedResultDTO(changed=self.select_voice_changed)


class _FakeClosable:
    def __init__(self) -> None:
        self.closed = 0

    def close(self) -> None:
        self.closed += 1


class _FakeTurnPersistence(_FakeClosable):
    def __init__(self, persist_user=None) -> None:
        super().__init__()
        self.persist_user_calls: list[dict] = []
        self._persist_user = persist_user

    def persist_user(self, **kwargs):
        self.persist_user_calls.append(kwargs)
        if self._persist_user is not None:
            return self._persist_user(**kwargs)
        return kwargs["message_id"]


class _FakeRouteOwner:
    def __init__(self, *, persistence_factory=None) -> None:
        self.client = object()
        self._persistence_factory = persistence_factory or _FakeTurnPersistence
        self.persistences: list[_FakeTurnPersistence] = []
        self.editors: list[_FakeClosable] = []

    def workflow_context(self, actor, thread_id, _request_id):
        return AdminWorkflowResolution(actor.canonical_user_id, thread_id, None)

    def turn_persistence(self, _actor, _resolution, _request_id):
        owner = self._persistence_factory()
        self.persistences.append(owner)
        return owner

    def editor_runtime(self, _actor, _resolution, _request_id, *, initial_session_id):
        del initial_session_id
        owner = _FakeClosable()
        self.editors.append(owner)
        return owner


def _deck_chat_context(
    deck_id: str = "deck-1",
    voice_id: str | None = "voice-2",
) -> DeckChatContextOutputDTO:
    return DeckChatContextOutputDTO.model_validate(
        {
            "deck": {
                "id": deck_id,
                "name": "Deck",
                "name_zh": None,
                "name_en": None,
                "description": None,
                "description_zh": None,
                "description_en": None,
                "enabled": True,
            },
            "voices": (
                [
                    {
                        "id": voice_id,
                        "name": "Story Editor",
                        "name_zh": None,
                        "name_en": None,
                        "system_prompt": "structure agent prompt",
                        "enabled": True,
                    }
                ]
                if voice_id is not None
                else []
            ),
            "plugin_refs": [],
        }
    )


def _deck_chat_resolution(
    deck_id: str = "deck-1",
    voice_id: str | None = "voice-2",
) -> AdminDeckChatContextResolution:
    return AdminDeckChatContextResolution(
        canonical_user_id="7",
        deck_id=deck_id,
        voice_id=voice_id,
        snapshot=_deck_chat_context(deck_id, voice_id),
    )


def _system_config(
    value: dict | None = None,
    *,
    deck_context: AdminDeckChatContextResolution | None = None,
):
    async def invoke(_current_user, _method, input_dto, **_kwargs):
        if isinstance(input_dto, SystemConfigGetInputDTO):
            return value or {"workspace_enabled": True}
        if isinstance(input_dto, DeckChatContextInputDTO):
            return deck_context or _deck_chat_resolution(
                input_dto.deck_id,
                input_dto.voice_id,
            )
        raise AssertionError(f"Unexpected Admin operation DTO: {type(input_dto)!r}")

    return unittest.mock.patch(
        "routers.claude_agent.invoke_admin_operation",
        new=unittest.mock.AsyncMock(side_effect=invoke),
    )


@_skip_if_no_server
class TestServerAgentEnvCleanup(unittest.TestCase):
    """Verify server startup env cleanup preserves only supported Agent keys."""

    def test_cleanup_preserves_mem0_and_session_keys(self):
        with unittest.mock.patch.dict(
            os.environ,
            {
                "INK_AGENT_MEM0_API_KEY": "mem0-test",
                "INK_AGENT_TTL_S": "600",
                "INK_AGENT_UNSUPPORTED": "stale",
                "ANTHROPIC_API_KEY": "legacy",
                "ANTHROPIC_AUTH_TOKEN": "current",
                "CLAUDE_CODE_UNUSED_TOKEN": "stale",
            },
            clear=True,
        ):
            _SERVER_MODULE._drop_unsupported_agent_env()

            self.assertEqual(os.environ["INK_AGENT_MEM0_API_KEY"], "mem0-test")
            self.assertEqual(os.environ["INK_AGENT_TTL_S"], "600")
            self.assertEqual(os.environ["ANTHROPIC_AUTH_TOKEN"], "current")
            self.assertNotIn("INK_AGENT_UNSUPPORTED", os.environ)
            self.assertNotIn("ANTHROPIC_API_KEY", os.environ)
            self.assertNotIn("CLAUDE_CODE_UNUSED_TOKEN", os.environ)

    def test_cleanup_preserves_sandbox_runtime_keys(self):
        # Regression for the 2026-07-26 production miss: the extra sandbox
        # read paths must survive startup cleanup or the sandbox silently
        # loses the contract.  (The apply-seccomp settings override key
        # briefly covered here was removed 2026-07-26 — proven dead in
        # production; Route A reverted to the vendor passthrough patch.)
        with unittest.mock.patch.dict(
            os.environ,
            {
                "INK_AGENT_SANDBOX_ENABLED": "false",
                "INK_AGENT_SANDBOX_EXTRA_ALLOW_READ": "/app/claude_agent:/app/libs",
            },
            clear=True,
        ):
            _SERVER_MODULE._drop_unsupported_agent_env()

            self.assertEqual(os.environ["INK_AGENT_SANDBOX_ENABLED"], "false")
            self.assertEqual(
                os.environ["INK_AGENT_SANDBOX_EXTRA_ALLOW_READ"],
                "/app/claude_agent:/app/libs",
            )

    def test_cleanup_preserves_resource_admission_keys(self):
        expected = {
            "INK_AGENT_MAX_CONCURRENT_RUNS": "1",
            "INK_AGENT_RUN_MEMORY_BUDGET_MIB": "512",
            "INK_AGENT_MEMORY_RESERVE_MIB": "128",
            "INK_AGENT_RESOURCE_POLICY_REFRESH_INTERVAL_S": "7",
        }
        with unittest.mock.patch.dict(os.environ, expected, clear=True):
            _SERVER_MODULE._drop_unsupported_agent_env()
            self.assertEqual(
                {key: os.environ.get(key) for key in expected},
                expected,
            )


# ---------------------------------------------------------------------------
# Route registration tests (import-level, no HTTP calls)
# ---------------------------------------------------------------------------


@_skip_if_no_server
class TestClaudeAgentRouteRegistration(unittest.TestCase):
    """Verify the 6 claude-agent routes are registered in server.py."""

    @classmethod
    def setUpClass(cls):
        cls.app = _SERVER_MODULE.app

        cls.routes = {
            (frozenset(r.methods or set()), r.path)
            for r in cls.app.routes
            if hasattr(r, "path") and "claude-agent" in getattr(r, "path", "")
        }

    def _has_route(self, method: str, path: str) -> bool:
        return any(
            method in (methods or set()) and p == path
            for methods, p in self.routes
        )

    def test_post_claude_agent_stream(self):
        self.assertTrue(self._has_route("POST", "/api/claude-agent"))

    def test_get_chat_history(self):
        self.assertTrue(self._has_route("GET", "/api/claude-agent/chat-history"))

    def test_post_message_latency(self):
        self.assertTrue(self._has_route("POST", "/api/claude-agent/message-latency"))

    def test_get_session_status(self):
        self.assertTrue(self._has_route("GET", "/api/claude-agent/session"))

    def test_delete_session(self):
        self.assertTrue(self._has_route("DELETE", "/api/claude-agent/session"))

    def test_post_tool_confirm(self):
        self.assertTrue(self._has_route("POST", "/api/claude-agent/tool-confirm"))

    def test_post_thread_stop(self):
        self.assertTrue(self._has_route("POST", "/api/claude-agent/threads/{thread_id}/stop"))

    def test_get_common_skill_commands(self):
        self.assertTrue(self._has_route("GET", "/api/claude-agent/skill-commands"))


@_skip_if_no_server
class TestClaudeAgentCommonSkillCommands(unittest.TestCase):
    """The slash catalog must reflect the validated backend common source."""

    def test_returns_every_backend_common_skill_in_canonical_order(self):
        import routers.claude_agent as route_module

        payload = asyncio.run(route_module.claude_agent_skill_commands(
            current_user={"user_id": 7},
        ))

        self.assertEqual(
            [command.model_dump() for command in payload.commands],
            [
                {"command": "/asr", "name": "asr"},
                {"command": "/hhxg-market", "name": "hhxg-market"},
                {"command": "/investment-data", "name": "investment-data"},
                {"command": "/skill-creator", "name": "skill-creator"},
                {"command": "/symbolic-board", "name": "symbolic-board"},
            ],
        )

    def test_invalid_backend_common_catalog_fails_closed(self):
        import routers.claude_agent as route_module
        from fastapi import HTTPException

        with unittest.mock.patch.object(
            route_module,
            "discover_builtin_skill_packages",
            side_effect=route_module.BuiltinSkillPackageError("invalid catalog"),
        ):
            with self.assertRaises(HTTPException) as captured:
                asyncio.run(route_module.claude_agent_skill_commands(
                    current_user={"user_id": 7},
                ))

        self.assertEqual(captured.exception.status_code, 503)
        self.assertEqual(
            captured.exception.detail["error_code"],
            "COMMON_SKILL_CATALOG_UNAVAILABLE",
        )


@_skip_if_no_server
class TestHistoricalPictureRouteRegistration(unittest.TestCase):
    """Historical pictures remain readable without any generation or save route."""

    @classmethod
    def setUpClass(cls):
        cls.routes = {
            (method, route.path)
            for route in _SERVER_MODULE.app.routes
            if hasattr(route, "path")
            for method in (getattr(route, "methods", None) or set())
        }

    def test_historical_picture_reads_remain_registered(self):
        self.assertIn(("GET", "/api/pictures"), self.routes)
        self.assertIn(("GET", "/api/pictures/range"), self.routes)
        self.assertIn(("GET", "/api/pictures/{date}/full"), self.routes)

    def test_picture_mutations_and_legacy_runtime_are_absent(self):
        self.assertNotIn(("POST", "/api/pictures"), self.routes)
        self.assertNotIn(("POST", "/api/pictures/generate"), self.routes)
        self.assertFalse(any(path.startswith("/polycli") for _, path in self.routes))


@_skip_if_no_server
class TestNotionRouteRegistration(unittest.TestCase):
    """Verify the Notion connector routes are registered in server.py."""

    @classmethod
    def setUpClass(cls):
        cls.app = _SERVER_MODULE.app
        cls.routes = {
            (frozenset(r.methods or set()), r.path)
            for r in cls.app.routes
            if hasattr(r, "path") and r.path.startswith("/api/connectors")
        }

    def _has_route(self, method: str, path: str) -> bool:
        return any(
            method in (methods or set()) and p == path
            for methods, p in self.routes
        )

    def test_get_connectors(self):
        self.assertTrue(self._has_route("GET", "/api/connectors"))

    def test_post_connectors(self):
        self.assertTrue(self._has_route("POST", "/api/connectors"))

    def test_get_connector(self):
        self.assertTrue(self._has_route("GET", "/api/connectors/{connector_id}"))

    def test_patch_connector(self):
        self.assertTrue(self._has_route("PATCH", "/api/connectors/{connector_id}"))

    def test_delete_connector(self):
        self.assertTrue(self._has_route("DELETE", "/api/connectors/{connector_id}"))

    def test_auth_login(self):
        self.assertTrue(self._has_route("POST", "/api/connectors/{connector_id}/auth/login"))

    def test_auth_poll(self):
        self.assertTrue(self._has_route("POST", "/api/connectors/{connector_id}/auth/poll"))

    def test_list_databases(self):
        self.assertTrue(self._has_route("GET", "/api/connectors/{connector_id}/databases"))

    def test_list_pages(self):
        self.assertTrue(self._has_route("GET", "/api/connectors/{connector_id}/pages"))

    def test_list_resources(self):
        self.assertTrue(self._has_route("GET", "/api/connectors/{connector_id}/resources"))

    def test_select_resources(self):
        self.assertTrue(self._has_route("POST", "/api/connectors/{connector_id}/resources/select"))

    def test_sync_connector(self):
        self.assertTrue(self._has_route("POST", "/api/connectors/{connector_id}/sync"))

    def test_delete_resource(self):
        self.assertTrue(self._has_route("DELETE", "/api/connectors/{connector_id}/resources/{resource_id}"))


@_skip_if_no_server
class TestClaudeMcpRouteRegistration(unittest.TestCase):
    """Verify the Claude MCP Resources router is mounted in server.py."""

    @classmethod
    def setUpClass(cls):
        cls.routes = {
            (frozenset(route.methods or set()), route.path)
            for route in _SERVER_MODULE.app.routes
            if hasattr(route, "path") and route.path.startswith("/api/claude-mcp")
        }

    def _has_route(self, method: str, path: str) -> bool:
        return any(method in methods and value == path for methods, value in self.routes)

    def test_capability_route(self):
        self.assertTrue(self._has_route("GET", "/api/claude-mcp/capability"))

    def test_servers_routes(self):
        self.assertTrue(self._has_route("GET", "/api/claude-mcp/servers"))
        self.assertTrue(self._has_route("POST", "/api/claude-mcp/servers"))

    def test_auth_operation_route(self):
        self.assertTrue(
            self._has_route(
                "POST",
                "/api/claude-mcp/servers/{identifier}/auth-operations",
            )
        )


# ---------------------------------------------------------------------------
# Pydantic model contract tests
# ---------------------------------------------------------------------------

@_skip_if_no_server
class TestClaudeAgentRequestModel(unittest.TestCase):
    """Verify ClaudeAgentRequestBody defaults and field types."""

    @classmethod
    def setUpClass(cls):
        if True:  # server already imported at module level
            _srv = _SERVER_MODULE
            cls.Model = _srv.ClaudeAgentRequestBody

    def test_message_defaults_to_none(self):
        m = self.Model()
        self.assertIsNone(m.message)

    def test_default_resume_false(self):
        m = self.Model(message="hello")
        self.assertFalse(m.resume)

    def test_default_tool_choice_auto(self):
        m = self.Model(message="hello")
        self.assertEqual(m.tool_choice, "auto")

    def test_default_max_turns_100(self):
        m = self.Model(message="hello")
        self.assertEqual(m.max_turns, 100)

    def test_model_optional(self):
        m = self.Model(message="hello")
        self.assertIsNone(m.model)

    def test_cwd_optional(self):
        m = self.Model(message="hello")
        self.assertIsNone(m.cwd)


@_skip_if_no_server
class TestToolConfirmRequestModel(unittest.TestCase):
    """Verify ToolConfirmRequestBody contract."""

    @classmethod
    def setUpClass(cls):
        if True:  # server already imported at module level
            _srv = _SERVER_MODULE
            cls.Model = _srv.ToolConfirmRequestBody

    def test_requires_tool_call_id(self):
        with self.assertRaises(Exception):
            self.Model(approved=True)

    def test_requires_approved(self):
        with self.assertRaises(Exception):
            self.Model(thread_id="thread-1", tool_call_id="xyz")

    def test_reason_optional(self):
        m = self.Model(thread_id="thread-1", tool_call_id="xyz", approved=True)
        self.assertIsNone(m.reason)

    def test_answers_optional(self):
        m = self.Model(thread_id="thread-1", tool_call_id="xyz", approved=False)
        self.assertIsNone(m.answers)


# ---------------------------------------------------------------------------
# Route behavior tests
# ---------------------------------------------------------------------------

@_skip_if_no_server
class TestClaudeAgentThreadMessageProjection(unittest.TestCase):
    def test_completed_turn_metadata_is_projected_and_invalid_envelope_keeps_diagnostics(self):
        import routers.claude_agent as route_module

        valid, private = route_module._project_public_chat_metadata({
            "turnId": "turn-stable",
            "turnStatus": "completed",
            "finalPartIndex": 3,
            "durationMs": 1250,
        })
        self.assertFalse(private)
        self.assertEqual(valid, {
            "turnId": "turn-stable",
            "turnStatus": "completed",
            "finalPartIndex": 3,
            "durationMs": 1250,
        })

        invalid, private = route_module._project_public_chat_metadata({
            "turnId": "turn-stable",
            "turnStatus": "completed",
        })
        self.assertFalse(private)
        self.assertEqual(invalid, {
            "turnId": "turn-stable",
            "turnProjectionInvalid": True,
        })

    def test_message_page_returns_stable_cursor_and_complete_large_text(self):
        import routers.claude_agent as route_module

        large_text = "长" * 200_000
        created_at = datetime(2026, 9, 2, 7, 0, tzinfo=timezone.utc)
        rows = [{
            "id": "message-large",
            "role": "assistant",
            "parts": [{"type": "text", "text": large_text}],
            "metadata": {
                "turnId": "turn-large",
                "turnStatus": "completed",
                "finalPartIndex": 0,
            },
            "created_at": created_at,
        }]
        chat = _FakeAdminChatData(
            thread={"id": "thread-owned", "user_id": 7},
            page={
                "messages": rows,
                "has_more": True,
                "latest_message_id": "message-large",
            },
        )

        async def call_route():
            return await route_module.claude_agent_thread_messages(
                "thread-owned",
                limit=1,
                current_user=_admin_user(),
                chat=chat,
            )

        with unittest.mock.patch.object(
            route_module,
            "_load_current_user_mcp_app_resource_bindings",
            new=unittest.mock.AsyncMock(return_value={}),
        ):
            payload = asyncio.run(call_route())

        self.assertEqual(payload["messages"][0]["parts"][0]["text"], large_text)
        self.assertEqual(payload["latest_message_id"], "message-large")
        self.assertTrue(payload["has_more"])
        timestamp, message_id, is_null = route_module._decode_chat_message_cursor(
            "thread-owned", payload["next_cursor"]
        )
        self.assertEqual(timestamp, created_at)
        self.assertEqual(message_id, "message-large")
        self.assertFalse(is_null)

    def test_message_page_exposes_final_projection_flags_without_storage_columns(self):
        import routers.claude_agent as route_module

        created_at = datetime(2026, 9, 2, 7, 0, tzinfo=timezone.utc)
        row = {
            "id": "assistant-projected",
            "role": "assistant",
            "parts": [{"type": "text", "text": "visible final"}],
            "metadata": {
                "turnId": "turn-projected",
                "turnStatus": "completed",
                "finalPartIndex": 2,
            },
            "created_at": created_at,
            "history_final_text": "visible final",
            "history_process_available": True,
            "history_projection_version": 1,
        }
        chat = _FakeAdminChatData(
            thread={"id": "thread-owned", "user_id": 7},
            page={
                "messages": [row],
                "has_more": False,
                "latest_message_id": "assistant-projected",
            },
        )

        async def call_route():
            return await route_module.claude_agent_thread_messages(
                "thread-owned",
                limit=20,
                current_user=_admin_user(),
                chat=chat,
            )

        with unittest.mock.patch.object(
            route_module,
            "_load_current_user_mcp_app_resource_bindings",
            new=unittest.mock.AsyncMock(return_value={}),
        ):
            payload = asyncio.run(call_route())

        projected = payload["messages"][0]
        self.assertEqual(projected["parts"], [{"type": "text", "text": "visible final"}])
        self.assertEqual(projected["projection_version"], 1)
        self.assertTrue(projected["process_available"])
        self.assertNotIn("history_final_text", projected)
        self.assertNotIn("history_projection_version", projected)

    def test_message_process_detail_requires_owned_thread_and_exact_assistant(self):
        import routers.claude_agent as route_module
        from fastapi import HTTPException

        full = {
            "id": "assistant-1",
            "role": "assistant",
            "parts": [
                {"type": "reasoning", "text": "work"},
                {"type": "text", "text": "answer"},
            ],
            "metadata": {
                "turnId": "turn-1",
                "turnStatus": "completed",
                "finalPartIndex": 1,
            },
        }
        chat = _FakeAdminChatData(
            thread={"id": "thread-owned", "user_id": 7}, detail=full
        )

        async def call_detail():
            return await route_module.claude_agent_thread_message_process(
                "thread-owned",
                "assistant-1",
                current_user=_admin_user(),
                chat=chat,
            )

        with unittest.mock.patch.object(
            route_module,
            "_load_current_user_mcp_app_resource_bindings",
            new=unittest.mock.AsyncMock(return_value={}),
        ):
            payload = asyncio.run(call_detail())
        self.assertEqual(payload["id"], "assistant-1")
        self.assertEqual(payload["parts"], full["parts"])
        detail_calls = [item for item in chat.calls if item[0] == "process_detail"]
        self.assertEqual(len(detail_calls), 1)
        self.assertEqual(detail_calls[0][1].thread_id, "thread-owned")
        self.assertEqual(detail_calls[0][1].message_id, "assistant-1")

        chat.thread = None
        with self.assertRaises(HTTPException) as captured:
            asyncio.run(call_detail())
        self.assertEqual(captured.exception.status_code, 404)
        self.assertEqual(captured.exception.detail, "Message process not found")

    def test_known_latest_uses_id_only_probe_and_invalid_cursor_is_400(self):
        import routers.claude_agent as route_module
        from fastapi import HTTPException

        chat = _FakeAdminChatData(
            thread={"id": "thread-owned", "user_id": 7},
            latest_message_id="message-latest",
        )

        async def call_known():
            return await route_module.claude_agent_thread_messages(
                "thread-owned",
                limit=20,
                known_latest_message_id="message-latest",
                current_user=_admin_user(),
                chat=chat,
            )

        payload = asyncio.run(call_known())
        self.assertTrue(payload["unchanged"])
        self.assertEqual(payload["messages"], [])
        self.assertNotIn("message_page", [item[0] for item in chat.calls])

        async def call_invalid():
            return await route_module.claude_agent_thread_messages(
                "thread-owned",
                limit=20,
                cursor="not-a-cursor",
                current_user=_admin_user(),
                chat=chat,
            )

        with self.assertRaises(HTTPException) as captured:
            asyncio.run(call_invalid())
        self.assertEqual(captured.exception.status_code, 400)

    def test_auto_repair_history_preserves_exact_visible_message_contract(self):
        import routers.claude_agent as route_module

        metadata = {
            "kind": "story-workspace-dream-auto-repair",
            "schemaVersion": "story-workspace-dream-auto-repair/v1",
            "originatingMessageId": "origin-message",
            "originatingTurnId": "origin-turn",
            "workflowRunId": "run_" + "a" * 32,
            "repairAttempt": 1,
            "validationCode": "PROJECT_STORY_SLUG_MISMATCH",
            "idempotencyKey": "dream-auto-repair/v1:stable",
            "dispatch_status": "dispatched",
            "projectCleanup": {
                "trustedProjectSlug": "server-project",
                "staleProjectSlugs": ["stale-project"],
            },
        }
        message = {
            "id": "dream_repair_stable",
            "role": "user",
            "parts": [{"type": "text", "text": "修正 workspace"}],
            "metadata": metadata,
            "created_at": "2026-09-01T00:00:00Z",
        }

        projected = route_module.PublicChatMessageDto.from_storage(
            message
        ).model_dump(exclude_unset=True, mode="json")

        self.assertEqual(projected, message)

    def test_legacy_v1_auto_repair_history_remains_visible_without_cleanup_fact(self):
        import routers.claude_agent as route_module

        message = {
            "id": "dream_repair_legacy",
            "role": "user",
            "parts": [{"type": "text", "text": "旧自动修正消息"}],
            "metadata": {
                "kind": "story-workspace-dream-auto-repair",
                "schemaVersion": "story-workspace-dream-auto-repair/v1",
                "originatingMessageId": "legacy-origin-message",
                "originatingTurnId": "legacy-origin-turn",
                "workflowRunId": "run_" + "b" * 32,
                "repairAttempt": 1,
                "validationCode": "PROJECT_STORY_SLUG_MISMATCH",
                "idempotencyKey": "dream-auto-repair/v1:legacy",
                "dispatch_status": "failed",
            },
            "created_at": "2026-09-01T00:00:00Z",
        }

        projected = route_module.PublicChatMessageDto.from_storage(
            message
        ).model_dump(exclude_unset=True, mode="json")

        self.assertEqual(projected, message)

    def test_malformed_auto_repair_metadata_hides_instruction_body(self):
        import routers.claude_agent as route_module

        projected = route_module.PublicChatMessageDto.from_storage({
            "id": "dream_repair_malformed",
            "role": "user",
            "parts": [{"type": "text", "text": "SECRET_INSTRUCTION"}],
            "metadata": {
                "kind": "story-workspace-dream-auto-repair",
                "schemaVersion": "story-workspace-dream-auto-repair/v1",
                "dispatch_status": "dispatched",
            },
        }).model_dump(exclude_unset=True, mode="json")

        self.assertEqual(projected["parts"], [])
        self.assertNotIn("SECRET_INSTRUCTION", json.dumps(projected))

    def test_corrupt_stored_metadata_fails_closed_through_admin_decode(self):
        import routers.claude_agent as route_module

        messages = [
            {
                "id": "corrupt-private-row",
                "role": "user",
                "parts": json.dumps(
                    [{"type": "text", "text": "SECRET_CORRUPT_INSTRUCTION"}]
                ),
                "metadata": '{"kind":"story-workspace-dream-launch"',
                "created_at": "2026-08-11T00:00:00Z",
            },
            {
                "id": "json-null-private-row",
                "role": "user",
                "parts": json.dumps(
                    [{"type": "text", "text": "SECRET_JSON_NULL_INSTRUCTION"}]
                ),
                "metadata": "null",
                "created_at": "2026-08-11T00:00:01Z",
            },
        ]
        chat = _FakeAdminChatData(
            thread={"id": "thread-owned", "user_id": 7}, messages=messages
        )

        async def call_route():
            return await route_module.claude_agent_thread_messages(
                "thread-owned",
                current_user=_admin_user(),
                chat=chat,
            )

        with unittest.mock.patch.object(
            route_module,
            "_load_current_user_mcp_app_resource_bindings",
            new=unittest.mock.AsyncMock(return_value={}),
        ):
            payload = asyncio.run(call_route())

        self.assertEqual(
            payload["messages"],
            [
                {
                    "id": "corrupt-private-row",
                    "role": "user",
                    "parts": [],
                    "metadata": {},
                    "created_at": "2026-08-11T00:00:00Z",
                },
                {
                    "id": "json-null-private-row",
                    "role": "user",
                    "parts": [],
                    "metadata": {},
                    "created_at": "2026-08-11T00:00:01Z",
                },
            ],
        )
        self.assertNotIn("SECRET_CORRUPT_INSTRUCTION", json.dumps(payload))
        self.assertNotIn("SECRET_JSON_NULL_INSTRUCTION", json.dumps(payload))

    def test_dream_control_rows_expose_body_with_settlement_projection(self):
        import routers.claude_agent as route_module

        messages = [
            {
                "id": "human-dream-message",
                "role": "user",
                "parts": [{"type": "text", "text": "保留这条用户消息"}],
                "metadata": {
                    "kind": "story-workspace-dream-agent-user",
                    "story_workspace_run_id": "run-visible",
                    "actor_id": "7",
                },
                "created_at": "2026-08-11T00:00:00Z",
                "server_debug": "SECRET_TOP_LEVEL",
            },
            {
                "id": "launch-private",
                "role": "user",
                "parts": [{"type": "text", "text": "SECRET_LAUNCH_INSTRUCTION"}],
                "metadata": {
                    "kind": "story-workspace-dream-launch",
                    "visibility": "system-hidden",
                    "dispatchStatus": "dispatched",
                    "workflowRunId": "run-secret",
                    "dispatchClaimId": "claim-secret",
                    "dreamContext": {"token": "SECRET_CONTEXT"},
                },
                "created_at": "2026-08-11T00:00:01Z",
            },
            {
                "id": "guidance-private",
                "role": "user",
                "parts": [{"type": "text", "text": "SECRET_GUIDANCE"}],
                "metadata": {
                    "kind": "story-workspace-guidance",
                    "command_fingerprint": "SECRET_FINGERPRINT",
                    "request_id": "SECRET_REQUEST",
                },
                "created_at": "2026-08-11T00:00:02Z",
            },
            {
                "id": "confirmation-private",
                "role": "user",
                "parts": [{"type": "text", "text": "SECRET_CONFIRMATION"}],
                "metadata": {
                    "kind": "story-workspace-dream-confirmation",
                    "dispatch_status": "failed",
                    "dispatch_claim_id": "SECRET_CLAIM",
                    "base_revisions": {"facts": "SECRET_REVISION"},
                },
                "created_at": "2026-08-11T00:00:03Z",
            },
            {
                "id": "episode-private",
                "role": "user",
                "parts": [{"type": "text", "text": "SECRET_EPISODE_COMMAND"}],
                "metadata": {
                    "kind": "story-workspace-dream-agent-user",
                    "dispatch_status": "dispatching",
                    "story_workspace_episode_action": {
                        "schema": "story-workspace-episode-action/v1",
                        "workflow_run_id": "run-secret",
                        "actor_id": "7",
                        "input_revision": "SECRET_INPUT_REVISION",
                    },
                },
                "created_at": "2026-08-11T00:00:04Z",
            },
            {
                "id": "assistant-public",
                "role": "assistant",
                "parts": [{"type": "text", "text": "public answer"}],
                "metadata": {
                    "usage": {
                        "inputTokens": 3,
                        "outputTokens": 5,
                        "totalTokens": 8,
                        "session_id": "SECRET_NESTED_SESSION",
                    },
                    "chatModel": {
                        "provider": "gateway",
                        "model": "dream-balanced",
                        "provenance": "SECRET_MODEL_PROVENANCE",
                    },
                    "toolChoice": "manual",
                    "toolCount": 2,
                    "is_partial": False,
                    "story_workspace_dream_source": {
                        "run_id": "SECRET_ASSISTANT_RUN",
                        "actor_id": "7",
                    },
                    "workspaceSessionId": "SECRET_WORKSPACE_SESSION",
                },
                "created_at": "2026-08-11T00:00:05Z",
            },
            {
                "id": "malformed-metadata",
                "role": "user",
                "parts": [{"type": "text", "text": "SECRET_MALFORMED_PARTS"}],
                "metadata": ["not", "an", "object"],
                "created_at": "2026-08-11T00:00:06Z",
            },
        ]

        async def call_route():
            return await route_module.claude_agent_thread_messages(
                "thread-owned",
                current_user=_admin_user(),
                chat=chat,
            )

        chat = _FakeAdminChatData(
            thread={
                "id": "thread-owned",
                "user_id": 7,
                "title": "Owned",
                "deck_id": "deck-public",
                "voice_id": None,
                "claude_session_id": "SECRET_CLAUDE_SESSION",
                "agent_contract_version": "SECRET_CONTRACT_VERSION",
                "created_at": "2026-08-10T00:00:00Z",
                "updated_at": "2026-08-11T00:00:00Z",
            },
            messages=messages,
        )
        with unittest.mock.patch.object(
            route_module,
            "_load_current_user_mcp_app_resource_bindings",
            new=unittest.mock.AsyncMock(return_value={}),
        ):
            payload = asyncio.run(call_route())

        self.assertEqual(
            payload["thread"],
            {
                "id": "thread-owned",
                "title": "Owned",
                "deck_id": "deck-public",
                "voice_id": None,
                "created_at": "2026-08-10T00:00:00Z",
                "updated_at": "2026-08-11T00:00:00Z",
            },
        )
        self.assertEqual(
            payload["messages"][0],
            {
                "id": "human-dream-message",
                "role": "user",
                "parts": [{"type": "text", "text": "保留这条用户消息"}],
                "metadata": {"kind": "story-workspace-dream-agent-user"},
                "created_at": "2026-08-11T00:00:00Z",
            },
        )
        self.assertEqual(
            payload["messages"][1]["metadata"],
            {
                "kind": "story-workspace-dream-launch",
                "visibility": "system-hidden",
                "dispatch_status": "dispatched",
            },
        )
        self.assertEqual(
            payload["messages"][2]["metadata"],
            {"kind": "story-workspace-guidance"},
        )
        self.assertEqual(
            payload["messages"][3]["metadata"],
            {
                "kind": "story-workspace-dream-confirmation",
                "dispatch_status": "failed",
            },
        )
        self.assertEqual(
            payload["messages"][4]["metadata"],
            {
                "kind": "story-workspace-dream-agent-user",
                "dispatch_status": "dispatching",
            },
        )
        self.assertEqual(
            payload["messages"][5]["metadata"],
            {
                "usage": {
                    "inputTokens": 3,
                    "outputTokens": 5,
                    "totalTokens": 8,
                },
                "chatModel": {
                    "provider": "gateway",
                    "model": "dream-balanced",
                },
                "toolChoice": "manual",
                "toolCount": 2,
                "is_partial": False,
            },
        )
        self.assertEqual(
            payload["messages"][5]["parts"],
            [{"type": "text", "text": "public answer"}],
        )
        self.assertEqual(payload["messages"][6]["metadata"], {})
        for index, expected_text in (
            (1, "SECRET_LAUNCH_INSTRUCTION"),
            (2, "SECRET_GUIDANCE"),
            (3, "SECRET_CONFIRMATION"),
            (4, "SECRET_EPISODE_COMMAND"),
        ):
            self.assertEqual(
                payload["messages"][index]["parts"],
                [{"type": "text", "text": expected_text}],
            )
        self.assertEqual(payload["messages"][6]["parts"], [])
        encoded = json.dumps(payload, ensure_ascii=False)
        for secret in (
            "SECRET_TOP_LEVEL",
            "run-visible",
            "SECRET_CLAUDE_SESSION",
            "SECRET_CONTRACT_VERSION",
            "SECRET_CONTEXT",
            "SECRET_FINGERPRINT",
            "SECRET_CLAIM",
            "SECRET_INPUT_REVISION",
            "SECRET_NESTED_SESSION",
            "SECRET_MODEL_PROVENANCE",
            "SECRET_ASSISTANT_RUN",
            "SECRET_WORKSPACE_SESSION",
            "SECRET_MALFORMED_PARTS",
        ):
            self.assertNotIn(secret, encoded)

    def test_foreign_thread_is_rejected_before_message_read(self):
        import routers.claude_agent as route_module
        from fastapi import HTTPException

        chat = _FakeAdminChatData(thread=None, messages=[{
            "id": "must-not-read",
            "role": "user",
            "parts": [],
        }])

        async def call_route():
            return await route_module.claude_agent_thread_messages(
                "thread-foreign",
                current_user=_admin_user(),
                chat=chat,
            )

        with self.assertRaises(HTTPException) as captured:
            asyncio.run(call_route())

        self.assertEqual(captured.exception.status_code, 404)
        self.assertNotIn("list_messages", [item[0] for item in chat.calls])


@_skip_if_no_server
class TestClaudeAgentRouteWorkspaceMode(unittest.TestCase):
    """Workspace Mode disabled should not initialize workspaces from attachments."""

    def test_attachments_do_not_initialize_workspace_when_workspace_mode_disabled(self):
        import routers.claude_agent as route_module

        body = route_module.ClaudeAgentRequestBody(
            thread_id="thread-no-workspace",
            message="hello with attachment",
            attachments=[
                route_module.ChatAttachment(
                    type="file",
                    url="/api/files/file-1",
                    storageKey="file-1",
                    filename="note.txt",
                    mediaType="text/plain",
                )
            ],
        )
        chat = _FakeAdminChatData(
            thread={"id": "thread-no-workspace", "user_id": 7}
        )
        owner = _FakeRouteOwner()

        async def _call_route():
            return await route_module.claude_agent_stream(
                body,
                current_user=_admin_user(),
                chat=chat,
                owner=owner,
            )

        with (
            _system_config({"workspace_enabled": False}),
            unittest.mock.patch.object(
                route_module,
                "get_or_create_workspace",
            ) as get_or_create_workspace,
            unittest.mock.patch.object(
                route_module,
                "sync_attachments_to_workspace_files",
            ) as sync_attachments_to_workspace_files,
            unittest.mock.patch.object(
                route_module,
                "_resolve_platform_model_selection",
                new=unittest.mock.AsyncMock(return_value="dream-balanced"),
            ),
        ):
            response = asyncio.run(_call_route())

        self.assertEqual(response.media_type, "text/event-stream")
        self.assertEqual(
            response.headers["content-type"],
            "text/event-stream; charset=utf-8",
        )
        self.assertEqual(
            response.headers["cache-control"],
            "no-cache, no-transform",
        )
        self.assertEqual(response.headers["x-accel-buffering"], "no")
        self.assertEqual(response.headers["connection"], "keep-alive")
        self.assertNotIn("content-length", response.headers)
        self.assertNotIn("content-encoding", response.headers)
        get_or_create_workspace.assert_not_called()
        sync_attachments_to_workspace_files.assert_not_called()


@_skip_if_no_server
class TestClaudeAgentDreamBindingRoute(unittest.TestCase):
    def test_empty_turn_cannot_change_the_thread_agent(self):
        import routers.claude_agent as route_module

        body = route_module.ClaudeAgentRequestBody(
            thread_id="thread-agent-empty",
            message="",
            deck_id="deck-1",
            voice_id="voice-2",
        )
        chat = _FakeAdminChatData(
            thread={
                "id": "thread-agent-empty",
                "user_id": 7,
                "deck_id": "deck-1",
                "voice_id": "voice-1",
            }
        )

        async def call_route():
            return await route_module.claude_agent_stream(
                body,
                current_user=_admin_user(),
                chat=chat,
            )

        with self.assertRaises(route_module.HTTPException) as raised:
            asyncio.run(call_route())

        self.assertEqual(raised.exception.status_code, 400)
        self.assertNotIn("select_voice", [item[0] for item in chat.calls])

    def test_same_deck_agent_switch_updates_next_turn_with_cas(self):
        import routers.claude_agent as route_module

        body = route_module.ClaudeAgentRequestBody(
            thread_id="thread-agent-switch",
            message="continue with the structure agent",
            deck_id="deck-1",
            voice_id="voice-2",
        )
        chat = _FakeAdminChatData(
            thread={
                "id": "thread-agent-switch",
                "user_id": 7,
                "deck_id": "deck-1",
                "voice_id": "voice-1",
            }
        )
        owner = _FakeRouteOwner()
        captured_requests = []
        deck_snapshot = _deck_chat_resolution("deck-1", "voice-2")

        async def run_streaming(request):
            captured_requests.append(request)
            yield 'event: finish\ndata: {"finishReason":"stop"}\n\n'

        async def call_and_consume():
            response = await route_module.claude_agent_stream(
                body,
                current_user=_admin_user(),
                chat=chat,
                owner=owner,
            )
            async for _frame in response.body_iterator:
                pass
            return response

        with (
            _system_config(deck_context=deck_snapshot),
            unittest.mock.patch(
                "database.get_db",
                side_effect=AssertionError("public Deck context must use Admin"),
            ) as dream_db,
            unittest.mock.patch.object(
                route_module,
                "_resolve_platform_model_selection",
                new=unittest.mock.AsyncMock(return_value="dream-balanced"),
            ),
            unittest.mock.patch.object(
                route_module.claude_agent_thread_factory,
                "run_streaming",
                side_effect=run_streaming,
            ),
        ):
            response = asyncio.run(call_and_consume())

        self.assertEqual(response.media_type, "text/event-stream")
        dream_db.assert_not_called()
        select_calls = [item for item in chat.calls if item[0] == "select_voice"]
        self.assertEqual(len(select_calls), 1)
        self.assertEqual(select_calls[0][1].thread_id, "thread-agent-switch")
        self.assertEqual(select_calls[0][1].deck_id, "deck-1")
        self.assertEqual(select_calls[0][1].voice_id, "voice-2")
        self.assertEqual(select_calls[0][1].expected_voice_id, "voice-1")
        self.assertEqual(len(captured_requests), 1)
        self.assertIs(
            captured_requests[0].admin_deck_chat_context,
            deck_snapshot,
        )
        self.assertIn(
            "structure agent prompt",
            captured_requests[0].system_prompt,
        )
        self.assertEqual(
            captured_requests[0].message_metadata,
            {"deckId": "deck-1", "voiceId": "voice-2"},
        )

    def test_same_deck_agent_switch_cas_conflict_preserves_current_agent(self):
        import routers.claude_agent as route_module

        body = route_module.ClaudeAgentRequestBody(
            thread_id="thread-agent-switch-conflict",
            message="continue",
            deck_id="deck-1",
            voice_id="voice-2",
        )
        chat = _FakeAdminChatData(
            thread={
                "id": "thread-agent-switch-conflict",
                "user_id": 7,
                "deck_id": "deck-1",
                "voice_id": "voice-1",
            },
            select_voice_changed=False,
        )
        owner = _FakeRouteOwner()
        deck_snapshot = _deck_chat_resolution("deck-1", "voice-2")

        async def call_route():
            return await route_module.claude_agent_stream(
                body,
                current_user=_admin_user(),
                chat=chat,
                owner=owner,
            )

        with (
            _system_config(deck_context=deck_snapshot),
            unittest.mock.patch(
                "database.get_db",
                side_effect=AssertionError("public Deck context must use Admin"),
            ) as dream_db,
            unittest.mock.patch.object(
                route_module.claude_agent_thread_factory,
                "run_streaming",
            ) as run_streaming,
        ):
            with self.assertRaises(route_module.HTTPException) as raised:
                asyncio.run(call_route())

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(
            raised.exception.detail["error_code"],
            "CHAT_AGENT_CONFLICT",
        )
        dream_db.assert_not_called()
        select_calls = [item for item in chat.calls if item[0] == "select_voice"]
        self.assertEqual(len(select_calls), 1)
        self.assertEqual(select_calls[0][1].thread_id, "thread-agent-switch-conflict")
        self.assertEqual(select_calls[0][1].deck_id, "deck-1")
        self.assertEqual(select_calls[0][1].voice_id, "voice-2")
        self.assertEqual(select_calls[0][1].expected_voice_id, "voice-1")
        run_streaming.assert_not_called()

    def test_admin_deck_context_failure_stops_before_bind_persistence_and_sse(self):
        import routers.claude_agent as route_module

        body = route_module.ClaudeAgentRequestBody(
            thread_id="thread-new-deck",
            message="start",
            deck_id="deck-1",
            voice_id="voice-2",
        )
        chat = _FakeAdminChatData(
            thread={
                "id": "thread-new-deck",
                "user_id": 7,
                "deck_id": None,
                "voice_id": None,
            }
        )
        owner = _FakeRouteOwner()

        async def invoke(_current_user, _method, input_dto, **_kwargs):
            if isinstance(input_dto, SystemConfigGetInputDTO):
                return {"workspace_enabled": True}
            if isinstance(input_dto, DeckChatContextInputDTO):
                raise route_module.HTTPException(
                    status_code=503,
                    detail={"error_code": "ADMIN_CAPABILITY_UNAVAILABLE"},
                )
            raise AssertionError(type(input_dto))

        async def call_route():
            return await route_module.claude_agent_stream(
                body,
                current_user=_admin_user(),
                chat=chat,
                owner=owner,
            )

        with (
            unittest.mock.patch.object(
                route_module,
                "invoke_admin_operation",
                new=unittest.mock.AsyncMock(side_effect=invoke),
            ),
            unittest.mock.patch(
                "database.get_db",
                side_effect=AssertionError("public Deck context must use Admin"),
            ) as dream_db,
            unittest.mock.patch.object(
                route_module.claude_agent_thread_factory,
                "run_streaming",
            ) as run_streaming,
        ):
            with self.assertRaises(route_module.HTTPException) as raised:
                asyncio.run(call_route())

        self.assertEqual(raised.exception.status_code, 503)
        dream_db.assert_not_called()
        self.assertEqual(
            [item[0] for item in chat.calls],
            ["get_thread"],
        )
        self.assertEqual(owner.persistences, [])
        self.assertEqual(owner.editors, [])
        run_streaming.assert_not_called()

    def test_admin_deck_policy_failure_stops_before_bind_persistence_and_sse(self):
        import routers.claude_agent as route_module

        body = route_module.ClaudeAgentRequestBody(
            thread_id="thread-disabled-deck",
            message="start",
            deck_id="deck-1",
            voice_id="voice-2",
        )
        chat = _FakeAdminChatData(
            thread={
                "id": "thread-disabled-deck",
                "user_id": 7,
                "deck_id": None,
                "voice_id": None,
            }
        )
        owner = _FakeRouteOwner()
        ready = _deck_chat_resolution("deck-1", "voice-2")
        disabled = AdminDeckChatContextResolution(
            canonical_user_id=ready.canonical_user_id,
            deck_id=ready.deck_id,
            voice_id=ready.voice_id,
            snapshot=ready.snapshot.model_copy(
                update={
                    "deck": ready.snapshot.deck.model_copy(
                        update={"enabled": False}
                    )
                }
            ),
        )

        async def call_route():
            return await route_module.claude_agent_stream(
                body,
                current_user=_admin_user(),
                chat=chat,
                owner=owner,
            )

        with (
            _system_config(deck_context=disabled),
            unittest.mock.patch(
                "database.get_db",
                side_effect=AssertionError("public Deck context must use Admin"),
            ) as dream_db,
            unittest.mock.patch.object(
                route_module.claude_agent_thread_factory,
                "run_streaming",
            ) as run_streaming,
        ):
            with self.assertRaises(route_module.HTTPException) as raised:
                asyncio.run(call_route())

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["error_code"], "DECK_DISABLED")
        dream_db.assert_not_called()
        self.assertEqual([item[0] for item in chat.calls], ["get_thread"])
        self.assertEqual(owner.persistences, [])
        self.assertEqual(owner.editors, [])
        run_streaming.assert_not_called()

    def test_terminal_dream_leaf_continues_as_canonical_chat_without_authority(self):
        import routers.claude_agent as route_module

        body = route_module.ClaudeAgentRequestBody(
            thread_id="thread-dream-terminal",
            message="continue talking",
        )
        chat = _FakeAdminChatData(
            thread={
                "id": "thread-dream-terminal",
                "user_id": 7,
                "deck_id": None,
                "voice_id": None,
            }
        )
        owner = _FakeRouteOwner()
        captured_requests = []

        async def run_streaming(request):
            captured_requests.append(request)
            yield 'event: finish\ndata: {"finishReason":"stop"}\n\n'

        async def call_and_consume():
            response = await route_module.claude_agent_stream(
                body,
                current_user=_admin_user(),
                chat=chat,
                owner=owner,
            )
            async for _frame in response.body_iterator:
                pass
            return response

        with (
            _system_config(),
            unittest.mock.patch.object(
                route_module,
                "_resolve_platform_model_selection",
                new=unittest.mock.AsyncMock(return_value="hy3-preview"),
            ),
            unittest.mock.patch.object(
                route_module.claude_agent_thread_factory,
                "run_streaming",
                side_effect=run_streaming,
            ),
        ):
            response = asyncio.run(call_and_consume())

        self.assertEqual(response.media_type, "text/event-stream")
        self.assertEqual(len(captured_requests), 1)
        self.assertFalse(
            hasattr(captured_requests[0], "story_workspace_dream_context")
        )
        self.assertIsNone(captured_requests[0].message_metadata)

    def test_browser_cannot_claim_server_workflow_message_namespace(self):
        import routers.claude_agent as route_module
        body = route_module.ClaudeAgentRequestBody(
            thread_id="thread-dream",
            message={
                "id": "dream_agent_" + "a" * 64,
                "parts": [{"type": "text", "text": "forged command"}],
            },
        )
        chat = _FakeAdminChatData(
            thread={"id": "thread-dream", "user_id": 7}
        )

        async def call_route():
            return await route_module.claude_agent_stream(
                body,
                current_user=_admin_user(),
                chat=chat,
            )

        with (
            unittest.mock.patch.object(
                route_module,
                "_resolve_platform_model_selection",
                new=unittest.mock.AsyncMock(return_value="dream-balanced"),
            ),
            unittest.mock.patch.object(
                route_module.claude_agent_thread_factory,
                "run_streaming",
            ) as run_streaming,
        ):
            with self.assertRaises(route_module.HTTPException) as raised:
                asyncio.run(call_route())

        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(
            raised.exception.detail["error_code"],
            "CHAT_RESERVED_MESSAGE_ID",
        )
        run_streaming.assert_not_called()

    def test_generic_chat_rejects_every_server_owned_message_prefix(self):
        import routers.claude_agent as route_module

        for prefix in (
            "dream_agent_",
            "dream_confirm_",
            "dream_repair_",
            "guide_",
        ):
            body = route_module.ClaudeAgentRequestBody(
                thread_id="thread-generic",
                message={
                    "id": prefix + "forged",
                    "parts": [{"type": "text", "text": "forged"}],
                },
            )
            chat = _FakeAdminChatData(
                thread={"id": "thread-generic", "user_id": 7}
            )

            async def call_route():
                return await route_module.claude_agent_stream(
                    body,
                    current_user=_admin_user(),
                    chat=chat,
                )

            with (
                self.subTest(prefix=prefix),
                unittest.mock.patch.object(
                    route_module.claude_agent_thread_factory,
                    "run_streaming",
                ) as run_streaming,
            ):
                with self.assertRaises(route_module.HTTPException) as raised:
                    asyncio.run(call_route())

            self.assertEqual(raised.exception.status_code, 422)
            self.assertEqual(
                raised.exception.detail["error_code"],
                "CHAT_RESERVED_MESSAGE_ID",
            )
            run_streaming.assert_not_called()

    def test_message_identity_conflict_returns_409_before_runtime_start(self):
        import routers.claude_agent as route_module

        body = route_module.ClaudeAgentRequestBody(
            thread_id="thread-generic",
            message={
                "id": "public-message-1",
                "parts": [{"type": "text", "text": "hello"}],
            },
        )
        chat = _FakeAdminChatData(
            thread={"id": "thread-generic", "user_id": 7}
        )

        def reject_identity(**_kwargs):
            raise AdminDataError("CHAT_MESSAGE_IDENTITY_CONFLICT", 409)

        owner = _FakeRouteOwner(
            persistence_factory=lambda: _FakeTurnPersistence(reject_identity)
        )

        async def call_route():
            return await route_module.claude_agent_stream(
                body,
                current_user=_admin_user(),
                chat=chat,
                owner=owner,
            )

        with (
            _system_config(),
            unittest.mock.patch.object(
                route_module,
                "_resolve_platform_model_selection",
                new=unittest.mock.AsyncMock(return_value="dream-balanced"),
            ),
            unittest.mock.patch.object(
                route_module.claude_agent_thread_factory,
                "run_streaming",
            ) as run_streaming,
        ):
            with self.assertRaises(route_module.HTTPException) as raised:
                asyncio.run(call_route())

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(
            raised.exception.detail["error_code"],
            "CHAT_MESSAGE_IDENTITY_CONFLICT",
        )
        self.assertEqual(len(owner.persistences), 1)
        self.assertEqual(
            owner.persistences[0].persist_user_calls,
            [{
                "actor_id": "7",
                "thread_id": "thread-generic",
                "parts": [{"type": "text", "text": "hello"}],
                "message_id": "public-message-1",
                "metadata": None,
            }],
        )
        self.assertEqual(owner.persistences[0].closed, 1)
        self.assertEqual(owner.editors[0].closed, 1)
        run_streaming.assert_not_called()

    def test_concurrent_public_posts_same_id_have_one_cas_winner(self):
        import routers.claude_agent as route_module

        bodies = [
            route_module.ClaudeAgentRequestBody(
                thread_id="thread-race",
                message={
                    "id": "public-race-1",
                    "parts": [{"type": "text", "text": text}],
                },
            )
            for text in ("one", "two")
        ]
        winner: list[tuple] = []
        winner_lock = threading.Lock()

        def cas_save(**kwargs):
            envelope = tuple(
                (key, json.dumps(value, sort_keys=True))
                for key, value in sorted(kwargs.items())
            )
            with winner_lock:
                if not winner:
                    winner.append(envelope)
                    return "public-race-1"
                if winner[0] != envelope:
                    raise AdminDataError("CHAT_MESSAGE_IDENTITY_CONFLICT", 409)
                return "public-race-1"

        chat = _FakeAdminChatData(
            thread={"id": "thread-race", "user_id": 7}
        )
        owner = _FakeRouteOwner(
            persistence_factory=lambda: _FakeTurnPersistence(cas_save)
        )

        async def call_routes():
            async def call(body):
                try:
                    return await route_module.claude_agent_stream(
                        body,
                        current_user=_admin_user(),
                        chat=chat,
                        owner=owner,
                    )
                except route_module.HTTPException as exc:
                    return exc

            return await asyncio.gather(*(call(body) for body in bodies))

        with (
            _system_config(),
            unittest.mock.patch.object(
                route_module,
                "_resolve_platform_model_selection",
                new=unittest.mock.AsyncMock(return_value="dream-balanced"),
            ),
            unittest.mock.patch.object(
                route_module.claude_agent_thread_factory,
                "run_streaming",
            ) as run_streaming,
        ):
            outcomes = asyncio.run(call_routes())

        conflicts = [
            outcome
            for outcome in outcomes
            if isinstance(outcome, route_module.HTTPException)
        ]
        streams = [outcome for outcome in outcomes if outcome not in conflicts]
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].status_code, 409)
        self.assertEqual(
            conflicts[0].detail["error_code"],
            "CHAT_MESSAGE_IDENTITY_CONFLICT",
        )
        self.assertEqual(len(streams), 1)
        self.assertEqual(streams[0].media_type, "text/event-stream")
        self.assertEqual(
            sum(len(item.persist_user_calls) for item in owner.persistences),
            2,
        )
        run_streaming.assert_not_called()


@_skip_if_no_server
class TestClaudeAgentRouteStop(unittest.TestCase):
    """Thread stop route should validate ownership before cancelling runtime state."""

    def test_stop_thread_validates_owner_and_calls_factory(self):
        import routers.claude_agent as route_module
        chat = _FakeAdminChatData(
            thread={"id": "thread-stop", "user_id": 7}
        )

        async def _call_route():
            return await route_module.claude_agent_stop_thread(
                "thread-stop",
                current_user=_admin_user(),
                chat=chat,
            )

        with unittest.mock.patch.object(
                route_module.claude_agent_thread_factory,
                "stop_thread",
                new=unittest.mock.AsyncMock(
                    return_value={
                        "stop_requested": True,
                        "running": False,
                        "lifecycle": "idle",
                    }
                ),
            ) as stop_thread:
            response = asyncio.run(_call_route())

        get_calls = [item for item in chat.calls if item[0] == "get_thread"]
        self.assertEqual(len(get_calls), 1)
        self.assertEqual(get_calls[0][1].thread_id, "thread-stop")
        stop_thread.assert_awaited_once_with("thread-stop")
        self.assertEqual(
            response,
            {
                "ok": True,
                "thread_id": "thread-stop",
                "stop_requested": True,
                "running": False,
                "lifecycle": "idle",
            },
        )


@_skip_if_no_server
class TestClaudeAgentToolConfirmationRoute(unittest.TestCase):
    """Tool confirmation must distinguish stale state from thread ownership."""

    def test_tool_confirm_rejects_an_unowned_thread_before_runtime_dispatch(self):
        import routers.claude_agent as route_module

        body = route_module.ToolConfirmRequestBody(
            thread_id="thread-foreign",
            tool_call_id="call-foreign",
            approved=True,
        )
        chat = _FakeAdminChatData(thread=None)

        async def _call_route():
            return await route_module.claude_agent_tool_confirm(
                body,
                current_user=_admin_user(),
                chat=chat,
            )

        with unittest.mock.patch.object(
                route_module.claude_agent_thread_factory,
                "confirm_tool",
            ) as confirm_tool:
            with self.assertRaises(route_module.HTTPException) as raised:
                asyncio.run(_call_route())

        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(raised.exception.detail, "Thread not found")
        get_calls = [item for item in chat.calls if item[0] == "get_thread"]
        self.assertEqual(len(get_calls), 1)
        self.assertEqual(get_calls[0][1].thread_id, "thread-foreign")
        confirm_tool.assert_not_called()

    def test_tool_confirm_reports_a_typed_not_pending_conflict(self):
        import routers.claude_agent as route_module

        body = route_module.ToolConfirmRequestBody(
            thread_id="thread-owned",
            tool_call_id="call-stale",
            approved=True,
        )
        chat = _FakeAdminChatData(
            thread={"id": "thread-owned", "user_id": 7}
        )

        async def _call_route():
            return await route_module.claude_agent_tool_confirm(
                body,
                current_user=_admin_user(),
                chat=chat,
            )

        with unittest.mock.patch.object(
                route_module.claude_agent_thread_factory,
                "confirm_tool",
                new=unittest.mock.AsyncMock(return_value=None),
            ):
            with self.assertRaises(route_module.HTTPException) as raised:
                asyncio.run(_call_route())

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(
            raised.exception.detail,
            {
                "code": "TOOL_CONFIRMATION_NOT_PENDING",
                "tool_call_id": "call-stale",
            },
        )

    def test_tool_confirm_resolves_an_owned_pending_confirmation(self):
        import routers.claude_agent as route_module
        from claude_agent.tool_confirmation_store import ToolConfirmationResult

        body = route_module.ToolConfirmRequestBody(
            thread_id="thread-owned",
            tool_call_id="call-pending",
            approved=False,
            reason="user declined",
        )
        chat = _FakeAdminChatData(
            thread={"id": "thread-owned", "user_id": 7}
        )

        async def _call_route():
            return await route_module.claude_agent_tool_confirm(
                body,
                current_user=_admin_user(),
                chat=chat,
            )

        with unittest.mock.patch.object(
                route_module.claude_agent_thread_factory,
                "confirm_tool",
                new=unittest.mock.AsyncMock(
                    return_value=route_module.ToolConfirmationResolution(
                        ToolConfirmationResult(
                            approved=False,
                            reason="user declined",
                        )
                    )
                ),
            ) as confirm_tool:
            response = asyncio.run(_call_route())

        get_calls = [item for item in chat.calls if item[0] == "get_thread"]
        self.assertEqual(len(get_calls), 1)
        self.assertEqual(get_calls[0][1].thread_id, "thread-owned")
        confirm_tool.assert_awaited_once_with(
            session_id="thread-owned",
            tool_call_id="call-pending",
            approved=False,
            reason="user declined",
            answers=None,
            actor_id="7",
        )
        self.assertEqual(response, {"ok": True, "approved": False})


@_skip_if_no_server
class TestClaudeAgentThreadStatusRoute(unittest.TestCase):
    """Thread status exposes the actor-owned runtime confirmation snapshot."""

    def test_status_rejects_an_unowned_thread_before_runtime_observation(self):
        import routers.claude_agent as route_module
        chat = _FakeAdminChatData(thread=None)

        async def _call_route():
            return await route_module.claude_agent_thread_status(
                "thread-foreign",
                current_user=_admin_user(),
                chat=chat,
            )

        with unittest.mock.patch.object(
                route_module.claude_agent_thread_factory,
                "tool_confirmation_snapshot",
            ) as tool_confirmation_snapshot:
            with self.assertRaises(route_module.HTTPException) as raised:
                asyncio.run(_call_route())

        self.assertEqual(raised.exception.status_code, 404)
        tool_confirmation_snapshot.assert_not_called()

    def test_status_returns_runtime_pending_confirmation_ids(self):
        import routers.claude_agent as route_module
        chat = _FakeAdminChatData(
            thread={"id": "thread-owned", "user_id": 7}
        )

        async def _call_route():
            return await route_module.claude_agent_thread_status(
                "thread-owned",
                current_user=_admin_user(),
                chat=chat,
            )

        with (
            unittest.mock.patch.object(
                route_module.claude_agent_thread_factory,
                "session_snapshot",
                return_value={"lifecycle": "running", "turn_count": 3},
            ),
            unittest.mock.patch.object(
                route_module.claude_agent_thread_factory,
                "tool_confirmation_snapshot",
                return_value={
                    "pending_tool_call_ids": ["call-pending"],
                    "tool_confirmation_observation": "known",
                },
            ),
        ):
            response = asyncio.run(_call_route())

        self.assertEqual(
            response,
            {
                "running": True,
                "lifecycle": "running",
                "turn_count": 3,
                "pending_tool_call_ids": ["call-pending"],
                "tool_confirmation_observation": "known",
            },
        )

    def test_status_not_found_is_known_empty_for_confirmations(self):
        import routers.claude_agent as route_module
        chat = _FakeAdminChatData(
            thread={"id": "thread-owned", "user_id": 7}
        )

        async def _call_route():
            return await route_module.claude_agent_thread_status(
                "thread-owned",
                current_user=_admin_user(),
                chat=chat,
            )

        with (
            unittest.mock.patch.object(
                route_module.claude_agent_thread_factory,
                "session_snapshot",
                return_value=None,
            ),
            unittest.mock.patch.object(
                route_module.claude_agent_thread_factory,
                "tool_confirmation_snapshot",
                return_value={
                    "pending_tool_call_ids": [],
                    "tool_confirmation_observation": "known",
                },
            ),
        ):
            response = asyncio.run(_call_route())

        self.assertEqual(response["tool_confirmation_observation"], "known")
        self.assertEqual(response["pending_tool_call_ids"], [])


@_skip_if_no_server
class TestLegacySessionOwnershipRoutes(unittest.TestCase):
    """Deprecated session aliases must retain the canonical thread owner gate."""

    def test_get_foreign_thread_never_observes_runtime(self):
        import routers.claude_agent as route_module
        chat = _FakeAdminChatData(thread=None)

        with unittest.mock.patch.object(
                route_module.claude_agent_thread_factory,
                "session_snapshot",
            ) as snapshot:
            with self.assertRaises(route_module.HTTPException) as raised:
                asyncio.run(
                    route_module.claude_agent_session_status(
                        "thread-foreign",
                        current_user=_admin_user(),
                        chat=chat,
                    )
                )
        self.assertEqual(raised.exception.status_code, 404)
        snapshot.assert_not_called()

    def test_delete_foreign_thread_never_closes_runtime(self):
        import routers.claude_agent as route_module
        chat = _FakeAdminChatData(thread=None)

        with unittest.mock.patch.object(
                route_module.claude_agent_thread_factory,
                "close_thread",
            ) as close_thread:
            with self.assertRaises(route_module.HTTPException) as raised:
                asyncio.run(
                    route_module.claude_agent_session_close(
                        "thread-foreign",
                        current_user=_admin_user(),
                        chat=chat,
                    )
                )
        self.assertEqual(raised.exception.status_code, 404)
        close_thread.assert_not_called()

    def test_owned_get_and_delete_use_same_thread_identity(self):
        import routers.claude_agent as route_module
        chat = _FakeAdminChatData(
            thread={"id": "thread-owned", "user_id": 7}
        )

        with (
            unittest.mock.patch.object(
                route_module.claude_agent_thread_factory,
                "session_snapshot",
                return_value={"lifecycle": "idle"},
            ),
            unittest.mock.patch.object(
                route_module.claude_agent_thread_factory,
                "close_thread",
            ) as close_thread,
        ):
            status = asyncio.run(
                route_module.claude_agent_session_status(
                    "thread-owned",
                    current_user=_admin_user(),
                    chat=chat,
                )
            )
            closed = asyncio.run(
                route_module.claude_agent_session_close(
                    "thread-owned",
                    current_user=_admin_user(),
                    chat=chat,
                )
            )
        self.assertEqual(status, {"lifecycle": "idle"})
        self.assertEqual(closed, {"ok": True, "session_id": "thread-owned"})
        get_calls = [item for item in chat.calls if item[0] == "get_thread"]
        self.assertEqual(len(get_calls), 2)
        self.assertTrue(all(item[1].thread_id == "thread-owned" for item in get_calls))
        close_thread.assert_called_once_with("thread-owned")


# ---------------------------------------------------------------------------
# Factory lifecycle tests
# ---------------------------------------------------------------------------

@_skip_if_no_server
class TestFactoryLifecycle(unittest.TestCase):
    """Verify the factory singleton is created and wired to startup/shutdown."""

    @classmethod
    def setUpClass(cls):
        if True:  # server already imported at module level
            _srv = _SERVER_MODULE
            cls.srv = _srv

    def test_factory_instance_exists(self):
        self.assertIsNotNone(self.srv.claude_agent_thread_factory)

    def test_factory_is_thread_factory_type(self):
        from claude_agent import ClaudeAgentThreadFactory
        self.assertIsInstance(
            self.srv.claude_agent_thread_factory,
            ClaudeAgentThreadFactory,
        )

    def test_startup_handler_registered(self):
        handler_names = [
            h.__name__
            for h in self.srv.app.router.on_startup
        ]
        self.assertIn("startup_claude_agent", handler_names)

    def test_composition_applies_config_before_recording_diagnostics(self):
        import agent_factory
        from claude_agent.admission import AgentAdmissionConfig
        from claude_agent.resource_policy import (
            RESOURCE_POLICY_DEFAULTS,
            ResourcePolicyLoadResult,
        )

        config = AgentAdmissionConfig(2, 640, 192, 90)
        result = ResourcePolicyLoadResult(
            config=config,
            defaults=RESOURCE_POLICY_DEFAULTS,
            status="applied",
            revision=11,
            updated_at="2026-08-27T03:00:00Z",
            loaded_at="2026-08-27T03:00:01Z",
        )
        calls: list[str] = []

        with (
            unittest.mock.patch.object(
                agent_factory.claude_agent_admission_controller,
                "replace_config",
                side_effect=lambda applied: calls.append("replace"),
            ) as replace_config,
            unittest.mock.patch.object(
                agent_factory.claude_agent_resource_diagnostics,
                "update_policy",
                side_effect=lambda *_args, **_kwargs: calls.append("record"),
            ) as update_policy,
        ):
            agent_factory._apply_claude_agent_resource_policy(result, True)

        self.assertEqual(calls, ["replace", "record"])
        replace_config.assert_called_once_with(config)
        update_policy.assert_called_once_with(result, effective_config=config)

    def test_composition_same_revision_refresh_does_not_replace_config(self):
        import agent_factory
        from claude_agent.resource_policy import (
            RESOURCE_POLICY_DEFAULTS,
            ResourcePolicyLoadResult,
        )

        config = agent_factory.claude_agent_admission_controller.config
        result = ResourcePolicyLoadResult(
            config=config,
            defaults=RESOURCE_POLICY_DEFAULTS,
            status="applied",
            revision=12,
            updated_at="2026-08-28T03:00:00Z",
            loaded_at="2026-08-28T03:00:01Z",
        )

        with (
            unittest.mock.patch.object(
                agent_factory.claude_agent_admission_controller,
                "replace_config",
            ) as replace_config,
            unittest.mock.patch.object(
                agent_factory.claude_agent_resource_diagnostics,
                "update_policy",
            ) as update_policy,
        ):
            agent_factory._apply_claude_agent_resource_policy(result, False)

        replace_config.assert_not_called()
        update_policy.assert_called_once_with(result, effective_config=config)

    def test_startup_validates_custom_sdk_before_factory(self):
        calls: list[str] = []
        distribution = types.SimpleNamespace(
            metadata={"Name": "ink-claude-dream-agent-sdk"},
            version="0.2.145",
        )
        with (
            unittest.mock.patch.object(
                self.srv,
                "require_dream_claude_sdk_distribution",
                side_effect=lambda: calls.append("sdk") or distribution,
            ),
            unittest.mock.patch.object(
                self.srv,
                "resolve_claude_cli_path",
                side_effect=lambda: calls.append("runtime")
                or "/runtime/cli.js",
            ),
            unittest.mock.patch.object(
                self.srv,
                "_claude_sdk_cli_compatibility_version",
                return_value="2.1.241",
            ),
            unittest.mock.patch.object(
                self.srv.claude_agent_thread_factory,
                "start",
                side_effect=lambda: calls.append("factory"),
            ),
            unittest.mock.patch.object(
                self.srv.claude_agent_resource_sampler,
                "start",
                side_effect=lambda: calls.append("sampler"),
            ),
            unittest.mock.patch.object(
                self.srv.claude_agent_resource_policy_refresher,
                "start",
                side_effect=lambda: calls.append("refresher"),
            ),
            unittest.mock.patch.object(
                self.srv.claude_agent_resource_postgres_sink,
                "start",
                side_effect=lambda: calls.append("sink"),
            ),
            unittest.mock.patch.object(
                self.srv.claude_agent_resource_publisher,
                "start",
                side_effect=lambda: calls.append("publisher"),
            ),
            unittest.mock.patch("builtins.print") as print_mock,
        ):
            asyncio.run(self.srv.startup_claude_agent())
        self.assertEqual(
            calls,
            [
                "sdk",
                "runtime",
                "factory",
                "sampler",
                "refresher",
                "sink",
                "publisher",
            ],
        )
        runtime_line = next(
            call.args[0]
            for call in print_mock.call_args_list
            if call.args and str(call.args[0]).startswith("🤖 Claude Agent runtime: ")
        )
        identity = json.loads(runtime_line.split(": ", 1)[1])
        self.assertEqual(
            identity,
            {
                "cli_mode": "dream_runtime",
                "cli_path": "/runtime/cli.js",
                "cli_runtime_release": "0.1.10",
                "sdk_cli_compatibility_version": "2.1.241",
                "sdk_distribution": "ink-claude-dream-agent-sdk",
                "sdk_import": "claude_agent_sdk",
                "sdk_version": "0.2.145",
            },
        )

    def test_startup_identity_marks_explicit_cli_override(self):
        distribution = types.SimpleNamespace(
            metadata={"Name": "ink-claude-dream-agent-sdk"},
            version="0.2.145",
        )
        with (
            unittest.mock.patch.dict(
                os.environ,
                {"CLAUDE_CODE_CLI_PATH": "/usr/local/bin/claude"},
            ),
            unittest.mock.patch.object(
                self.srv,
                "_claude_sdk_cli_compatibility_version",
                return_value="2.1.241",
            ),
            unittest.mock.patch("builtins.print") as print_mock,
        ):
            self.srv._print_claude_runtime_identity(
                distribution,
                "/usr/local/bin/claude",
            )
        runtime_line = print_mock.call_args.args[0]
        identity = json.loads(runtime_line.split(": ", 1)[1])
        self.assertEqual(identity["cli_mode"], "explicit_override")
        self.assertEqual(identity["cli_runtime_release"], "external")
        self.assertEqual(identity["cli_path"], "/usr/local/bin/claude")

    def test_shutdown_handler_registered(self):
        handler_names = [
            h.__name__
            for h in self.srv.app.router.on_shutdown
        ]
        self.assertIn("shutdown_claude_agent", handler_names)

    def test_dream_confirmation_coordinator_lifecycle_is_ordered(self):
        startup_names = [h.__name__ for h in self.srv.app.router.on_startup]
        shutdown_names = [h.__name__ for h in self.srv.app.router.on_shutdown]
        self.assertLess(
            startup_names.index("startup_admin_request_auth"),
            startup_names.index(
                "story_workspace_startup_dream_confirmation_coordinator"
            ),
        )
        self.assertLess(
            startup_names.index("startup_claude_agent"),
            startup_names.index(
                "story_workspace_startup_dream_confirmation_coordinator"
            ),
        )
        self.assertLess(
            shutdown_names.index(
                "story_workspace_shutdown_dream_confirmation_coordinator"
            ),
            shutdown_names.index("shutdown_claude_agent"),
        )

    def test_event_bus_startup_validation_is_strict_and_redis_is_pinged(self):
        validate = unittest.mock.AsyncMock()
        with (
            unittest.mock.patch.dict(
                os.environ,
                {"INK_AGENT_EVENT_BUS_BACKEND": "redis"},
            ),
            unittest.mock.patch.object(
                self.srv.RedisStreamEventBus,
                "validate_connection",
                new=validate,
            ),
        ):
            asyncio.run(self.srv.startup_validate_claude_agent_event_bus())
        validate.assert_awaited_once_with()

        with unittest.mock.patch.dict(
            os.environ,
            {"INK_AGENT_EVENT_BUS_BACKEND": "redsi"},
        ):
            with self.assertRaisesRegex(RuntimeError, "either 'memory' or 'redis'"):
                asyncio.run(self.srv.startup_validate_claude_agent_event_bus())

    def test_shutdown_awaits_business_owners_and_factory(self):
        calls: list[str] = []
        confirmation = unittest.mock.Mock()
        confirmation.stop = unittest.mock.AsyncMock(
            side_effect=lambda: calls.append("confirmation")
        )

        async def close_factory():
            calls.append("factory")

        async def close_redis():
            calls.append("redis")

        def resource_stop(name):
            return unittest.mock.AsyncMock(side_effect=lambda: calls.append(name))

        with (
            unittest.mock.patch.object(
                self.srv,
                "story_workspace_get_dream_confirmation_coordinator",
                return_value=confirmation,
            ),
            unittest.mock.patch.object(
                self.srv.claude_agent_thread_factory,
                "aclose",
                side_effect=close_factory,
            ),
            unittest.mock.patch.object(
                self.srv.claude_agent_resource_publisher,
                "stop",
                new=resource_stop("publisher"),
            ),
            unittest.mock.patch.object(
                self.srv.claude_agent_resource_policy_refresher,
                "stop",
                new=resource_stop("refresher"),
            ),
            unittest.mock.patch.object(
                self.srv.claude_agent_resource_postgres_sink,
                "stop",
                new=resource_stop("sink"),
            ),
            unittest.mock.patch.object(
                self.srv.claude_agent_resource_sampler,
                "stop",
                new=resource_stop("sampler"),
            ),
            unittest.mock.patch.object(
                self.srv.RedisStreamEventBus,
                "aclose",
                new=unittest.mock.AsyncMock(side_effect=close_redis),
            ) as close_event_bus,
        ):
            async def exercise():
                await self.srv.story_workspace_shutdown_dream_confirmation_coordinator()
                await self.srv.shutdown_claude_agent()

            asyncio.run(exercise())

        self.assertEqual(
            calls,
            [
                "confirmation",
                "publisher",
                "refresher",
                "sink",
                "sampler",
                "factory",
                "redis",
            ],
        )
        close_event_bus.assert_awaited_once_with()

    def test_agent_shutdown_isolates_factory_and_redis_close_failures(self):
        calls: list[str] = []

        async def fail_factory():
            calls.append("factory")
            raise RuntimeError("factory close failed")

        async def fail_redis():
            calls.append("redis")
            raise RuntimeError("redis close failed")

        with (
            unittest.mock.patch.object(
                self.srv.claude_agent_thread_factory,
                "aclose",
                side_effect=fail_factory,
            ),
            unittest.mock.patch.object(
                self.srv.RedisStreamEventBus,
                "aclose",
                new=unittest.mock.AsyncMock(side_effect=fail_redis),
            ),
        ):
            asyncio.run(self.srv.shutdown_claude_agent())

        self.assertEqual(calls, ["factory", "redis"])


# ---------------------------------------------------------------------------
# Authentication enforcement (401 without token)
# ---------------------------------------------------------------------------

@_skip_if_no_server
class TestBrowserResponseHeaders(unittest.TestCase):
    """Cross-origin browser clients must be able to verify artifact ETags."""

    @classmethod
    def setUpClass(cls):
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            raise unittest.SkipTest("httpx not installed — skipping CORS tests")
        cls.client = TestClient(_SERVER_MODULE.app, raise_server_exceptions=False)

    def test_cors_exposes_etag_and_sliding_auth_header(self):
        response = self.client.get(
            "/api/me",
            headers={"Origin": "http://127.0.0.1:5173"},
        )

        exposed = {
            value.strip().lower()
            for value in response.headers["access-control-expose-headers"].split(",")
        }
        self.assertEqual(exposed, {"etag", "x-new-access-token"})


@_skip_if_no_server
class TestClaudeAgentAuth(unittest.TestCase):
    """Claude agent routes must require JWT authentication."""

    @classmethod
    def setUpClass(cls):
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            raise unittest.SkipTest("httpx not installed — skipping HTTP auth tests")
        if True:  # server already imported at module level
            _srv = _SERVER_MODULE
            cls.client = TestClient(_srv.app, raise_server_exceptions=False)

    def test_stream_requires_auth(self):
        resp = self.client.post(
            "/api/claude-agent",
            json={"message": "hi"},
        )
        self.assertEqual(resp.status_code, 401)

    def test_chat_history_requires_auth(self):
        resp = self.client.get("/api/claude-agent/chat-history")
        self.assertEqual(resp.status_code, 401)

    def test_common_skill_commands_require_auth(self):
        resp = self.client.get("/api/claude-agent/skill-commands")
        self.assertEqual(resp.status_code, 401)

    def test_session_status_requires_auth(self):
        resp = self.client.get("/api/claude-agent/session")
        self.assertEqual(resp.status_code, 401)

    def test_tool_confirm_requires_auth(self):
        resp = self.client.post(
            "/api/claude-agent/tool-confirm",
            json={"tool_call_id": "x", "approved": True},
        )
        self.assertEqual(resp.status_code, 401)


@_skip_if_no_server
class TestNotionAuth(unittest.TestCase):
    """Notion connector routes must require JWT authentication."""

    @classmethod
    def setUpClass(cls):
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            raise unittest.SkipTest("httpx not installed — skipping HTTP auth tests")
        cls.client = TestClient(_SERVER_MODULE.app, raise_server_exceptions=False)

    def test_list_connectors_requires_auth(self):
        resp = self.client.get("/api/connectors")
        self.assertEqual(resp.status_code, 401)

    def test_create_connector_requires_auth(self):
        resp = self.client.post(
            "/api/connectors",
            json={"name": "Notion"},
        )
        self.assertEqual(resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()
