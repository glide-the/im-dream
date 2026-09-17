# [Sync] 2026-09-16: prove claimed confirmation user/assistant persistence never calls Dream PostgreSQL.
# [Sync] 2026-09-16: exercise managed MCP with explicit test authorization matching production composition.
# [Sync] 2026-09-16: keep legacy fixtures behind a test-only persistence adapter while production requires Admin.
# [Sync] 2026-09-16: inject Notion persistence through the current Admin turn owner.
# [Sync] 2026-09-15: validate standalone Story output uses Admin and never the removed Dream transaction helper.
# [Sync] 2026-09-15: verify Editor result refresh uses the Admin runtime cache without Dream DB access.
# [Sync] 2026-09-15: pass the server-owned workspace metadata owner into Deck packing.
# [Sync] 2026-09-15: validate Registry108 activation provider and Dream PostgreSQL fence.
# [Sync] 2026-09-16: retire the zero-caller local activation transaction and keep Registry108 as the only writer.
# [Input] Consume ClaudeAgentService, ClaudeAgentRunRequest, AgentRunState,
#         service callback factories, and ToolEventPayload.
# [Output] Verify context assembly maps system_config into AgentRunOptions and
#          service-level SSE event mapping remains correct.
# [Pos] test node in backend/tests
# [Sync] 2026-09-13: verify three identity scopes, resume intent, and DB failure boundaries.
# [Sync] 2026-06-14: combine system_config assembly coverage with tool_input_delta
#                    -> tool-input-delta SSE forwarding coverage.
# [Sync] 2026-08-28: carry selected model max-output capability into the immutable Runtime env snapshot.
# [Sync] 2026-09-02: verify completed assistant persistence writes the matching final projection.
# [Sync] 2026-06-14: cover Edit Session event publication after successful
#                    editor MCP write tool results.
# [Sync] 2026-06-17: cover SSE error formatting that includes exception notes
#                    from runner diagnostics.
# [Sync] 2026-06-21: cover sandbox network policy handoff to workspace init.
# [Sync] 2026-06-22: cover Settings SYSTEM_PROMPT handoff into system_prompt
#                    assembly, config-change cache rebuild, and config-load
#                    failure termination.
# [Sync] 2026-09-15: cover Session broker env/fail-closed and recent projection cache behavior.
# [Sync] 2026-06-25: cover CancelledError stop path emitting finish and stream sentinel.
# [Sync] 2026-07-04: cover workspace-local Notion snapshot attach and
#                    workspace_context Notion block rendering.
# [Sync] 2026-07-05: cover explicit Notion connector identity / sync cursor
#                    rendering in the workspace context summary.
# [Sync] 2026-07-26: assert sandbox_fs_allowed_write_paths passes from
#                    system_config through assemble_context into
#                    get_or_create_workspace.
# [Sync] 2026-08-12: cover shared Chat/Dream SDK-native Session ID persistence
#                    through on_message before a cancelled turn can skip the
#                    successful assistant persistence path.
# [Sync] 2026-09-01: cover exact repair SSE-part persistence, assistant-before-
#                    Hook ordering, and fail-closed persistence failure.
# [Sync] 2026-08-14: cover trusted Dream binding selecting the Deck
#                    workspace-file prompt without changing Chat/session DTOs.
# [Sync] 2026-08-22: cover thread-local Claude CLI temp binding while
#                    Workspace Mode remains disabled for context and files.
# [Sync] 2026-08-22: cover per-turn user MCP definition/secure-store delivery
#                    and Workspace Mode disabled fail-closed behavior.
# [Sync] 2026-08-25: cover managed PostgreSQL MCP snapshots on new/resume turns
#                    and the same ephemeral projection path with Workspace Mode off.
# [Sync] 2026-08-13: cover editor MCP structured business failures as tool errors.
# [Sync] 2026-08-29: cover stdio result-envelope normalization, actor/session-
#                    matched cache refresh on success/failure, and success-only events.
# [Sync] 2026-08-28: cover model plus global server-owned Claude Code Runtime env assembly.
# [Sync] 2026-08-28: cover per-turn Notion credential projection handoff without
#                    exposing credential bytes to AgentRunOptions or workspace context.
# [Sync] 2026-08-29: require attached workspace context to index the installed
#                    notion-session Skill and its canonical instruction path.
# [Sync] 2026-08-30: require workspace context to consume the dynamic README
#                    Skill section instead of a hard-coded notion-session row.
# [Sync] 2026-08-30: prove Chat context assembly passes the deployment-owned
#                    disabled sandbox capability independently of Workspace Mode.
# [Sync] 2026-09-01: prove current actor/thread Notion projection selects the
#                    Notion builtin platform and refreshes exact directory-source
#                    sandbox reads; degraded projection keeps common only.
# [Sync] 2026-09-01: prove a dispatched server auto-repair message receives the
#                    fresh typed stale-root scope consumed by the single Bash guard.
# [Sync] 2026-09-01: require persisted cleanup metadata, fresh Hook scope, and
#                    .dream WORKBENCH facts to agree before an automatic turn.
# [Sync] 2026-09-02: cover protocol-safe completed-turn projection metadata and duration.
# [Sync] 2026-09-04: require unexpected Dream post-turn synchronization
#                    failures to retain the committed assistant and use the
#                    existing typed workbench-sync error contract.
# [Sync] 2026-09-15: inject SystemConfig only through the explicit test harness boundary.
# [Sync] 2026-09-15: reuse the public Registry105 Deck DTO for Dream-mode prompt assembly without a second DB read.

"""Tests for ClaudeAgentService context assembly and SSE event mapping."""
from __future__ import annotations

import asyncio
from contextlib import nullcontext
import hashlib
import inspect
import json
import os
import re
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]  # backend/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tests._sdk_stubs  # noqa: F401 — stub claude_agent_sdk before service import

import database as _db
import claude_agent.service as service_module
import claude_mcp.service as claude_mcp_service_module
import claude_agent.workspace_context as workspace_context_module
from claude_agent.service import (
    ClaudeAgentRunRequest,
    ClaudeAgentService as _ProductionClaudeAgentService,
    _TurnContext,
)
from claude_agent.thread_pool import AgentRunState
from claude_agent.tool_confirmation_store import ToolConfirmationStore
from claude_agent.stream_events import NormalizedAgentEvent
from libs.claude_agent_kit.types import (
    AgentRunResult,
    DREAM_AUTO_REPAIR_EXECUTION_SCHEMA_VERSION,
    DreamAutoRepairExecutionScope,
    ToolEventPayload,
)
from services.admin_gateway.models import GatewayModel
from services.admin_data.session_models import SessionPreviewDTO
from services.admin_data.agent_turn_persistence import AdminAgentTurnPersistence
from services.admin_data.story_workspace_artifact_data import (
    AdminStoryWorkspaceArtifactProvider,
)
from services.admin_data.deck_chat_context_data import (
    AdminDeckChatContextResolution,
    DeckChatContextOutputDTO,
)
from services.admin_data.turn_persistence import AdminTurnPersistence
from services.admin_data.workflow_data import AdminWorkflowResolution
from story_workspace.contracts import (
    StoryWorkspaceAgentStoryPayload,
    StoryWorkspaceDreamRunContext,
)


def _managed_loader(snapshot=None):
    loader = unittest.mock.Mock()
    loader.load = unittest.mock.AsyncMock(
        return_value={} if snapshot is None else snapshot
    )
    loader.authorize.side_effect = lambda _authorization: nullcontext()
    return loader


def _bind_test_grant(owner, *, run_id=None):
    owner.current_grant.return_value = SimpleNamespace(
        token="idg_test-managed-mcp",
        run_id=run_id,
    )
    return owner


class _LegacyTurnPersistence(
    AdminAgentTurnPersistence,
    AdminStoryWorkspaceArtifactProvider,
):
    """Test-only adapter for historical fixtures that still patch database.py."""

    def system_config(self, *, actor_id, thread_id):
        del thread_id
        return _db.get_system_config(int(actor_id))

    def recent_sessions(self, *, actor_id, thread_id):
        del actor_id, thread_id
        return ()

    def session_projection_child_env(self):
        return {}

    def current_grant(self, *, actor_id, thread_id):
        del actor_id, thread_id
        return SimpleNamespace(token="idg_test-managed-mcp", run_id=None)

    def notion_connector_store(self, *, actor_id, thread_id):
        del actor_id, thread_id
        return SimpleNamespace(test_only_admin_notion_store=True)

    def thread(self, *, actor_id, thread_id):
        row = _db.get_chat_thread(thread_id, int(actor_id))
        if row is None:
            return None
        return SimpleNamespace(model_dump=lambda: dict(row))

    def update_session(
        self,
        *,
        actor_id,
        thread_id,
        session_id,
        contract_version,
    ):
        del actor_id
        _db.update_chat_thread_claude_session(
            thread_id,
            session_id,
            contract_version,
        )

    def persist_user(
        self,
        *,
        actor_id,
        thread_id,
        message_id,
        parts,
        metadata,
    ):
        _db.save_chat_message(
            thread_id,
            "user",
            parts=parts,
            message_id=message_id,
            metadata=metadata,
        )
        thread = _db.get_chat_thread(thread_id, int(actor_id))
        if thread and not thread.get("title"):
            text = "".join(
                str(part.get("text") or "")
                for part in parts
                if isinstance(part, dict) and part.get("type") == "text"
            ).strip()
            _db.update_chat_thread_title(thread_id, text[:50])
        return SimpleNamespace(message_id=message_id)

    def persist_assistant(
        self,
        *,
        actor_id,
        thread_id,
        message_id,
        parts,
        metadata,
        history_final_text,
        history_process_available,
        history_projection_version,
    ):
        del actor_id
        return _db.save_chat_message(
            thread_id,
            "assistant",
            parts=parts,
            message_id=message_id,
            metadata=metadata,
            history_final_text=history_final_text,
            history_process_available=history_process_available,
            history_projection_version=history_projection_version,
        )


class ClaudeAgentService(_ProductionClaudeAgentService):
    """Test-only DI for historical fixtures without a real Admin server."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "system_config_reader",
            lambda user_id: _db.get_system_config(int(user_id)),
        )
        super().__init__(*args, **kwargs)

    async def assemble_context(self, request, **kwargs):
        if request.admin_turn_persistence is None:
            request.admin_turn_persistence = _LegacyTurnPersistence()
        if (
            request.admin_workflow_resolution is None
            and self._dream_context_mapper is None
        ):
            request.admin_workflow_resolution = AdminWorkflowResolution(
                str(request.user_id),
                request.thread_id,
                None,
            )
        return await super().assemble_context(request, **kwargs)


class _FakeContextBuilder:
    def __init__(self) -> None:
        self.system_prompt_calls: list[tuple[list[dict[str, Any]], str | None]] = []
        self.user_message_calls: list[dict[str, Any]] = []

    async def build_system_prompt(
        self,
        recent_sessions: list[dict[str, Any]],
        *,
        configured_system_prompt: str | None = None,
    ) -> str:
        self.system_prompt_calls.append((recent_sessions, configured_system_prompt))
        suffix = f":{configured_system_prompt}" if configured_system_prompt else ""
        return f"system-prompt:{len(recent_sessions)}{suffix}"

    def build_user_message(self, message_parts: list | None, **kwargs: Any) -> list[dict[str, Any]]:
        self.user_message_calls.append(kwargs)
        return [{"type": "text", "text": "assembled"}]


class _FakeBus:
    async def publish(self, frame: str | None) -> None:
        pass


def _admin_deck_snapshot(
    deck_id: str = "deck-dream",
) -> DeckChatContextOutputDTO:
    return DeckChatContextOutputDTO.model_validate(
        {
            "deck": {
                "id": deck_id,
                "name": "Dream Deck",
                "name_zh": None,
                "name_en": None,
                "description": None,
                "description_zh": None,
                "description_en": None,
                "enabled": True,
            },
            "voices": [],
            "plugin_refs": [],
        }
    )


def _admin_deck_resolution(
    deck_id: str = "deck-dream",
) -> AdminDeckChatContextResolution:
    return AdminDeckChatContextResolution(
        canonical_user_id="7",
        deck_id=deck_id,
        voice_id=None,
        snapshot=_admin_deck_snapshot(deck_id),
    )


class _StaticDreamContextMapper:
    def __init__(self, context: StoryWorkspaceDreamRunContext | None) -> None:
        self.context = context
        self.calls: list[tuple[str, str]] = []

    def resolve(self, *, actor_id: str, thread_id: str):
        self.calls.append((str(actor_id), thread_id))
        return self.context


class _FakeAdminEditorRuntime(service_module.AdminEditorRuntime):
    def __init__(self, states: dict[str, dict] | None = None) -> None:
        self.states = states or {}
        self.load_calls: list[str] = []

    def child_env(self) -> dict[str, str]:
        return {
            "INK_EDITOR_BROKER_HOST": "127.0.0.1",
            "INK_EDITOR_BROKER_PORT": "31415",
            "INK_EDITOR_BROKER_CAPABILITY": "a" * 43,
            "INK_EDITOR_BROKER_TIMEOUT_SECONDS": "10.0",
            "INK_EDITOR_BROKER_MAX_BYTES": "1048576",
        }

    def cached_state(self, session_id: str) -> dict | None:
        value = self.states.get(session_id)
        return dict(value) if value is not None else None

    def load(self, input_dto, request_id: str):
        del request_id
        self.load_calls.append(input_dto.session_id)
        state = self.states.get(input_dto.session_id)
        return service_module.EditorLoadOutputDTO(
            session_id=input_dto.session_id,
            editor_state=state,
            updated_at="2026-09-15T00:00:00Z" if state is not None else None,
        )


class TestStoryWorkspaceOutputTransaction(unittest.IsolatedAsyncioTestCase):
    async def test_persists_the_story_bundle_through_the_turn_admin_owner(self):
        provider = unittest.mock.Mock(
            spec=service_module.AdminStoryWorkspaceOutputProvider
        )
        provider.store_story_workspace_output.return_value = {
            "story_id": "story-1",
            "review_status": "pending",
        }
        payload = StoryWorkspaceAgentStoryPayload(title="标题")
        request = SimpleNamespace(
            user_id="7",
            thread_id="thread-1",
            admin_turn_persistence=provider,
        )
        with (
            unittest.mock.patch.object(
                service_module, "parse_agent_story_output", return_value=payload
            ),
            unittest.mock.patch.object(_db, "get_db") as database,
        ):
            result = await ClaudeAgentService()._store_story_workspace_output(
                SimpleNamespace(request=request, dream_context=None),
                '{"title":"标题"}',
            )

        self.assertEqual(result["story_id"], "story-1")
        provider.store_story_workspace_output.assert_called_once_with(
            actor_id="7",
            thread_id="thread-1",
            story=payload.model_dump(mode="json"),
        )
        database.assert_not_called()

    async def test_admin_failure_keeps_chat_outcome_and_never_falls_back_to_database(self):
        provider = unittest.mock.Mock(
            spec=service_module.AdminStoryWorkspaceOutputProvider
        )
        provider.store_story_workspace_output.side_effect = RuntimeError(
            "fixture persistence failure"
        )
        request = SimpleNamespace(
            user_id="7",
            thread_id="thread-1",
            admin_turn_persistence=provider,
        )
        with (
            unittest.mock.patch.object(_db, "get_db") as database,
            self.assertLogs(service_module.logger, level="ERROR") as logs,
        ):
            result = await ClaudeAgentService()._store_story_workspace_output(
                SimpleNamespace(request=request, dream_context=None),
                '{"title":"标题"}',
            )

        self.assertIsNone(result)
        database.assert_not_called()
        self.assertIn(
            "Admin Story Workspace output persistence failed",
            "\n".join(logs.output),
        )


class TestClaudeAgentServiceAssembleContext(unittest.IsolatedAsyncioTestCase):
    async def test_fresh_init_receipt_is_the_next_turn_resume_identity(self):
        from claude_agent_sdk.types import SystemMessage

        builder = _FakeContextBuilder()
        service = ClaudeAgentService(
            context_builder=builder,
            platform_model_resolver=lambda *_: "dream-balanced",
            dream_context_mapper=_StaticDreamContextMapper(None),
        )
        request = ClaudeAgentRunRequest(user_id="7", thread_id="same-dream-thread", resume=True)
        row = {}
        new_id = "44444444-4444-4444-8444-444444444444"

        def save_id(thread_id, session_id, version):
            self.assertEqual(thread_id, request.thread_id)
            row.update(claude_session_id=session_id, agent_contract_version=version)

        with (
            tempfile.TemporaryDirectory(prefix="dream-resume-next-turn-") as tmp,
            unittest.mock.patch.object(_db, "get_system_config", return_value={"workspace_enabled": True}),
            unittest.mock.patch.object(_db, "get_chat_thread", side_effect=lambda *_: dict(row)),
            unittest.mock.patch.object(_db, "update_chat_thread_claude_session", side_effect=save_id) as save,
            unittest.mock.patch.object(service_module, "get_or_create_workspace", return_value=Path(tmp).resolve()),
        ):
            state = AgentRunState(session_id=request.thread_id)
            fresh = await service.assemble_context(request, state=state, bus=_FakeBus(), runner=unittest.mock.Mock())
            self.assertIsNone(fresh.run_options.thread_id)
            await service._persist_sdk_session_from_message(fresh, SimpleNamespace(data={"session_id": request.thread_id}))
            await service._persist_sdk_session_from_message(fresh, SystemMessage(subtype="error", data={"session_id": new_id}))
            save.assert_not_called()
            await service._persist_sdk_session_from_message(fresh, SystemMessage(subtype="init", data={"session_id": new_id}))
            project = Path(tmp).resolve() / ".claude-home" / "projects" / re.sub(r"[^a-zA-Z0-9]", "-", str(Path(tmp).resolve()))
            project.mkdir(parents=True)
            (project / f"{new_id}.jsonl").write_text(json.dumps({
                "type": "user", "uuid": "fixture", "sessionId": new_id,
                "message": {"role": "user", "content": "fixture"},
            }) + "\n")
            resumed = await service.assemble_context(request, state=state, bus=_FakeBus(), runner=unittest.mock.Mock())
            self.assertTrue(resumed.run_options.resume)
            self.assertEqual(resumed.run_options.thread_id, new_id)
            self.assertEqual(resumed.request.thread_id, request.thread_id)

    async def test_resume_intent_and_database_identity_matrix(self):
        from libs.claude_agent_kit.server import session_files

        claude_id = "44444444-4444-4444-8444-444444444444"
        row = {
            "claude_session_id": claude_id,
            "agent_contract_version": service_module._AGENT_RUNTIME_CONTRACT_VERSION,
        }
        for resume, stored, located, expected in (
            (True, {}, None, False),
            (True, row, None, False),
            (True, row, "/verified-transcript", True),
            (False, row, "/verified-transcript", False),
            (True, {**row, "agent_contract_version": "old"}, None, False),
        ):
            with self.subTest(resume=resume, stored=stored, located=located):
                builder = _FakeContextBuilder()
                service = ClaudeAgentService(
                    context_builder=builder,
                    platform_model_resolver=lambda *_: "dream-balanced",
                    dream_context_mapper=_StaticDreamContextMapper(None),
                )
                request = ClaudeAgentRunRequest(
                    user_id="7", thread_id="dream-business-thread", resume=resume,
                    editor_state={"id": "note-business-session"},
                    admin_editor_runtime=_FakeAdminEditorRuntime(),
                    message_parts=[{"type": "text", "text": "isolated fixture"}],
                )
                with (
                    tempfile.TemporaryDirectory(prefix="dream-resume-service-") as tmp,
                    unittest.mock.patch.object(_db, "get_system_config", return_value={"workspace_enabled": True}),
                    unittest.mock.patch.object(_db, "get_chat_thread", return_value=stored) as loader,
                    unittest.mock.patch.object(service_module, "get_or_create_workspace", return_value=Path(tmp).resolve()),
                    unittest.mock.patch.object(session_files, "locate_resumable_session", return_value=located) as probe,
                ):
                    execution = await service.assemble_context(
                        request, state=AgentRunState(session_id=request.thread_id),
                        bus=_FakeBus(), runner=unittest.mock.Mock(),
                    )
                loader.assert_called_once_with(request.thread_id, 7)
                self.assertEqual(execution.run_options.resume, expected)
                self.assertEqual(execution.run_options.thread_id, claude_id if expected else None)
                self.assertEqual(builder.user_message_calls[0]["thread_id"], request.thread_id)
                self.assertEqual(builder.user_message_calls[0]["editor_session_id"], "note-business-session")
                self.assertEqual(builder.user_message_calls[0]["resume"], expected)
                if not resume or not stored or stored.get("agent_contract_version") == "old":
                    probe.assert_not_called()

    async def test_resume_database_failure_does_not_become_fresh(self):
        service = ClaudeAgentService(
            context_builder=_FakeContextBuilder(),
            platform_model_resolver=lambda *_: "dream-balanced",
            dream_context_mapper=_StaticDreamContextMapper(None),
        )
        request = ClaudeAgentRunRequest(user_id="7", thread_id="dream-db-error", resume=True)
        with (
            tempfile.TemporaryDirectory(prefix="dream-resume-db-error-") as tmp,
            unittest.mock.patch.object(_db, "get_system_config", return_value={"workspace_enabled": True}),
            unittest.mock.patch.object(_db, "get_chat_thread", side_effect=RuntimeError("secret database details")),
            unittest.mock.patch.object(service_module, "get_or_create_workspace", return_value=Path(tmp).resolve()),
            self.assertRaisesRegex(RuntimeError, "^CLAUDE_RESUME_DATABASE_UNAVAILABLE$"),
        ):
            await service.assemble_context(
                request, state=AgentRunState(session_id=request.thread_id),
                bus=_FakeBus(), runner=unittest.mock.Mock(),
            )

    def setUp(self) -> None:
        self._dream_thread_loader = unittest.mock.patch.object(
            _db,
            "get_chat_thread",
            return_value=None,
        )
        self._dream_thread_loader.start()
        self.managed_mcp_loader = _managed_loader()
        self._managed_mcp_loader_patch = unittest.mock.patch.object(
            claude_mcp_service_module,
            "get_default_managed_mcp_runtime_snapshot_loader",
            return_value=self.managed_mcp_loader,
        )
        self._managed_mcp_loader_patch.start()
        self._managed_mcp_workspace_patch = unittest.mock.patch.object(
            service_module,
            "_resolve_managed_mcp_workspace_scope_sync",
            side_effect=lambda *, actor_id, context, provider=None: (
                "workspace-1" if context is not None else None
            ),
        )
        self._managed_mcp_workspace_patch.start()

    def tearDown(self) -> None:
        self._managed_mcp_workspace_patch.stop()
        self._managed_mcp_loader_patch.stop()
        self._dream_thread_loader.stop()

    @staticmethod
    def _dream_context() -> StoryWorkspaceDreamRunContext:
        return StoryWorkspaceDreamRunContext(
            workflow_run_id="run_" + "1" * 32,
            thread_id="thread_dream_turn",
            deck_id="deck-dream",
            deck_plugin_id="ink.dream.story-workflow",
            deck_plugin_version="1.0.0",
            deck_plugin_binding_id="dpb_" + "2" * 32,
            binding_revision=3,
            deck_runtime_snapshot_id="drs_" + "4" * 32,
            runtime_plugin_lock_id="rpl_" + "5" * 32,
        )

    async def test_dream_turn_packs_adapter_and_propagates_only_its_run_context(self):
        builder = _FakeContextBuilder()
        selected_models: list[tuple[str, str | None]] = []

        def resolve_model(user_id: str, client_alias: str | None) -> GatewayModel:
            selected_models.append((user_id, client_alias))
            return GatewayModel(
                model_alias="dream-balanced",
                display_name="Dream Balanced",
                protocol="anthropic",
                capabilities={"tools": True},
                context_window=200_000,
                max_output_tokens=8_192,
                enabled=True,
                callable=True,
                availability="included",
                required_plan_code="free",
                upgrade_hint=None,
                claude_code_auto_compact_window=262_144,
                claude_code_max_context_tokens=262_144,
            )

        activator = unittest.mock.AsyncMock()
        mapper = _StaticDreamContextMapper(self._dream_context())
        service = ClaudeAgentService(
            context_builder=builder,
            platform_model_resolver=resolve_model,
            dream_context_mapper=mapper,
            dream_runtime_init_activator=activator,
            claude_code_runtime_env_provider=lambda: {
                "CLAUDE_CODE_EFFORT_LEVEL": "high",
            },
        )
        state = AgentRunState(session_id="thread_dream_turn")
        context = mapper.context
        assert context is not None
        deck_snapshot = _admin_deck_resolution()
        request = ClaudeAgentRunRequest(
            user_id="7",
            thread_id="thread_dream_turn",
            message_id="dream_agent_" + "a" * 64,
            message_parts=[{"type": "text", "text": "create Dream"}],
            admin_deck_chat_context=deck_snapshot,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_path = Path(tmp_dir) / "thread_dream_turn"
            workspace_path.mkdir()
            (workspace_path / ".dream").mkdir()
            with (
                unittest.mock.patch.object(
                    _db,
                    "get_system_config",
                    return_value={"workspace_enabled": True},
                ),
                unittest.mock.patch.object(
                    _db,
                    "get_chat_thread",
                    return_value={"deck_id": "deck-dream"},
                ),
                unittest.mock.patch.object(
                    service_module,
                    "get_or_create_workspace",
                    return_value=workspace_path,
                ),
                unittest.mock.patch.object(
                    service_module,
                    "_pack_thread_workspace_plugins",
                ) as pack,
                unittest.mock.patch.object(
                    service_module,
                    "_resolve_story_workspace_dream_deck_prompt",
                    new=unittest.mock.AsyncMock(
                        return_value="dream-workspace-file-prompt"
                    ),
                ) as resolve_dream_prompt,
            ):
                execution = await service.assemble_context(
                    request,
                    state=state,
                    bus=_FakeBus(),
                    runner=unittest.mock.Mock(),
                )

        pack.assert_called_once_with(
            str(workspace_path),
            "deck-dream",
            actor_id="7",
            thread_id="thread_dream_turn",
            admin_turn_persistence=unittest.mock.ANY,
            dream_mode=True,
        )
        self.assertIsInstance(
            pack.call_args.kwargs["admin_turn_persistence"],
            _LegacyTurnPersistence,
        )
        self.assertIs(
            builder.user_message_calls[0]["story_workspace_dream_context"],
            context,
        )
        self.assertIn(
            str(workspace_path.resolve() / ".dream" / "WORKBENCH.md"),
            builder.user_message_calls[0][
                "story_workspace_dream_workbench_instruction"
            ],
        )
        self.assertIn(
            str(
                workspace_path.resolve()
                / ".dream"
                / "ASSET-COLLABORATION.md"
            ),
            builder.user_message_calls[0][
                "story_workspace_dream_workbench_instruction"
            ],
        )
        self.assertIn(
            "必须使用 Read 工具读取",
            builder.user_message_calls[0][
                "story_workspace_dream_workbench_instruction"
            ],
        )
        self.assertEqual(
            execution.run_options.mcp_env["INK_AGENT_WORKFLOW_RUN_ID"],
            context.workflow_run_id,
        )
        self.assertEqual(
            execution.run_options.mcp_env[
                "INK_AGENT_STORY_WORKSPACE_MESSAGE_ID"
            ],
            request.message_id,
        )
        self.assertEqual(selected_models, [("7", None)])
        resolve_dream_prompt.assert_awaited_once_with(
            context=context,
            actor_id="7",
            admin_deck_chat_context=deck_snapshot,
        )
        self.assertEqual(
            builder.user_message_calls[0]["voice_system_prompt"],
            "dream-workspace-file-prompt",
        )
        self.assertEqual(mapper.calls, [("7", "thread_dream_turn")])
        activator.assert_awaited_once_with(
            context=context,
            actor_id="7",
            cwd=str(workspace_path),
            remote_session_ref="thread_dream_turn",
            provider=None,
        )
        self.assertEqual(execution.run_options.model, "dream-balanced")
        self.assertEqual(execution.run_options.server_runtime_env, {
            "INK_CLAUDE_CODE_MODEL_MAX_OUTPUT_TOKENS": "8192",
            "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "262144",
            "CLAUDE_CODE_MAX_CONTEXT_TOKENS": "262144",
            "CLAUDE_CODE_EFFORT_LEVEL": "high",
        })
        expected_gateway_key = "dream-turn-" + hashlib.sha256(
            f"7\nthread_dream_turn\n{request.message_id}".encode("utf-8")
        ).hexdigest()
        self.assertEqual(
            execution.run_options.gateway_idempotency_key,
            expected_gateway_key,
        )
        self.assertFalse(execution.run_options.resume)
        self.assertIsNone(execution.resume_existing_session)
        self.assertEqual(
            builder.user_message_calls[0]["model"],
            "dream-balanced",
        )

    async def test_public_dream_prompt_reuses_admin_snapshot_without_database(self):
        context = self._dream_context()
        snapshot = _admin_deck_resolution()
        with unittest.mock.patch.object(
            _db,
            "get_db",
            side_effect=AssertionError("Registry105 snapshot must be reused"),
        ) as dream_db:
            prompt = await service_module._resolve_story_workspace_dream_deck_prompt(
                context=context,
                actor_id="7",
                admin_deck_chat_context=snapshot,
            )
        dream_db.assert_not_called()
        self.assertIn("Dream workspace-file turn", prompt)
        self.assertIn("Dream Deck", prompt)
        self.assertNotIn("exactly one JSON object", prompt)

    async def test_dispatched_auto_repair_turn_receives_fresh_cleanup_scope(self):
        context = self._dream_context()
        mapper = _StaticDreamContextMapper(context)
        artifact_hook = unittest.mock.Mock()
        ticket = unittest.mock.sentinel.auto_repair_ticket
        artifact_hook.before_main_turn.return_value = ticket
        artifact_hook.resolve_auto_repair_project_cleanup_scope.return_value = (
            "server-project",
            ("stale-project",),
        )
        service = ClaudeAgentService(
            context_builder=_FakeContextBuilder(),
            platform_model_resolver=lambda _user_id, _alias: "dream-balanced",
            dream_context_mapper=mapper,
            dream_artifact_turn_hook=artifact_hook,
            dream_runtime_init_activator=unittest.mock.AsyncMock(),
        )
        message_id = "dream_repair_" + ("a" * 40)
        request = ClaudeAgentRunRequest(
            user_id="7",
            thread_id=context.thread_id,
            resume=False,
            message_id=message_id,
            message_parts=[{"type": "text", "text": "repair"}],
            message_metadata={
                "kind": "story-workspace-dream-auto-repair",
                "schemaVersion": "story-workspace-dream-auto-repair/v1",
                "originatingMessageId": "message-origin",
                "originatingTurnId": "turn-origin",
                "workflowRunId": context.workflow_run_id,
                "repairAttempt": 1,
                "validationCode": "PROJECT_STORY_SLUG_MISMATCH",
                "idempotencyKey": "repair-key",
                "dispatch_status": "dispatched",
                "projectCleanup": {
                    "trustedProjectSlug": "server-project",
                    "staleProjectSlugs": ["stale-project"],
                },
            },
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_path = Path(tmp_dir) / context.thread_id
            workspace_path.mkdir()
            (workspace_path / ".dream").mkdir()
            for slug in ("server-project", "stale-project"):
                project = workspace_path / "stories" / slug / "project.yaml"
                project.parent.mkdir(parents=True)
                project.write_text(
                    f"project_id: {slug}\nproject_slug: {slug}\n",
                    encoding="utf-8",
                )
            with (
                unittest.mock.patch.object(
                    _db,
                    "get_system_config",
                    return_value={"workspace_enabled": True},
                ),
                unittest.mock.patch.object(
                    _db,
                    "get_chat_thread",
                    return_value={"deck_id": context.deck_id},
                ),
                unittest.mock.patch.object(
                    service_module,
                    "get_or_create_workspace",
                    return_value=workspace_path,
                ),
                unittest.mock.patch.object(
                    service_module,
                    "_pack_thread_workspace_plugins",
                ),
                unittest.mock.patch.object(
                    service_module,
                    "_resolve_story_workspace_dream_deck_prompt",
                    new=unittest.mock.AsyncMock(return_value="dream prompt"),
                ),
            ):
                execution = await service.assemble_context(
                    request,
                    state=AgentRunState(session_id=context.thread_id),
                    bus=_FakeBus(),
                    runner=unittest.mock.Mock(),
                )
                workbench_text = (
                    workspace_path / ".dream" / "WORKBENCH.md"
                ).read_text(encoding="utf-8")

        scope = execution.run_options.dream_auto_repair_scope
        self.assertIsInstance(scope, DreamAutoRepairExecutionScope)
        assert scope is not None
        self.assertEqual(
            scope.schema_version,
            DREAM_AUTO_REPAIR_EXECUTION_SCHEMA_VERSION,
        )
        self.assertEqual(scope.message_id, message_id)
        self.assertEqual(scope.workflow_run_id, context.workflow_run_id)
        self.assertEqual(scope.thread_id, context.thread_id)
        self.assertEqual(scope.actor_id, "7")
        self.assertEqual(scope.trusted_project_slug, "server-project")
        self.assertEqual(scope.stale_project_slugs, ("stale-project",))
        self.assertIn(
            '"trusted_project_slug": "server-project"',
            workbench_text,
        )
        self.assertIn(
            '"stale_project_slugs": [\n      "stale-project"',
            workbench_text,
        )
        artifact_hook.resolve_auto_repair_project_cleanup_scope.assert_called_once_with(
            ticket,
            validation_code="PROJECT_STORY_SLUG_MISMATCH",
        )

    async def test_shared_thread_resume_uses_persisted_claude_session(self):
        managed_loader = _managed_loader({
            "remote-readonly": {
                "type": "http",
                "url": "https://mcp.example.test",
            }
        })
        service = ClaudeAgentService(
            context_builder=_FakeContextBuilder(),
            platform_model_resolver=lambda _user_id, _alias: "dream-balanced",
            dream_context_mapper=_StaticDreamContextMapper(None),
            managed_mcp_runtime_snapshot_loader=managed_loader,
        )
        session_id = "11111111-1111-4111-8111-111111111111"
        request = ClaudeAgentRunRequest(
            user_id="7",
            thread_id="thread-shared-resume",
            resume=True,
            message_parts=[{"type": "text", "text": "继续"}],
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_path = Path(tmp_dir).resolve() / request.thread_id
            transcript = (
                workspace_path
                / ".claude-home"
                / "projects"
                / re.sub(r"[^a-zA-Z0-9]", "-", str(workspace_path.resolve()))
                / f"{session_id}.jsonl"
            )
            transcript.parent.mkdir(parents=True)
            transcript.write_text(json.dumps({
                "type": "user", "uuid": "fixture-message", "sessionId": session_id,
                "message": {"role": "user", "content": "isolated fixture"},
            }) + "\n", encoding="utf-8")
            with (
                unittest.mock.patch.object(
                    _db,
                    "get_system_config",
                    return_value={"workspace_enabled": True},
                ),
                unittest.mock.patch.object(
                    _db,
                    "get_chat_thread",
                    return_value={
                        "claude_session_id": session_id,
                        "agent_contract_version": service_module._AGENT_RUNTIME_CONTRACT_VERSION,
                    },
                ),
                unittest.mock.patch.object(
                    service_module,
                    "get_or_create_workspace",
                    return_value=workspace_path,
                ),
            ):
                execution = await service.assemble_context(
                    request,
                    state=AgentRunState(session_id=request.thread_id),
                    bus=_FakeBus(),
                    runner=unittest.mock.Mock(),
                )

        self.assertTrue(execution.run_options.resume)
        self.assertEqual(execution.run_options.thread_id, session_id)
        self.assertEqual(
            execution.resume_existing_session["claude_session_id"],
            session_id,
        )
        managed_loader.load.assert_awaited_once_with("7", None)
        self.assertIsNone(execution.run_options.claude_secure_storage_home)
        self.assertEqual(
            execution.run_options.claude_mcp_servers,
            {
                "remote-readonly": {
                    "type": "http",
                    "url": "https://mcp.example.test",
                }
            },
        )

    def test_dream_runtime_has_no_stream_message_callback(self):
        service = ClaudeAgentService(
            dream_context_mapper=_StaticDreamContextMapper(None),
        )
        self.assertFalse(hasattr(service, "_make_dream_runtime_init_cb"))

    def test_dream_runtime_activation_contract_has_no_local_persistence_service(self):
        from services.story_workspace import dream_runtime_activation_service

        source = inspect.getsource(dream_runtime_activation_service)
        self.assertFalse(
            hasattr(
                dream_runtime_activation_service,
                "StoryWorkspaceDreamRuntimeActivationService",
            )
        )
        for forbidden in (
            "WorkflowRunService",
            "SessionManager",
            "ReconcileService",
            ".execute(",
        ):
            self.assertNotIn(forbidden, source)

    async def test_dream_sdk_init_uses_admin_activation_after_local_manifest_verification(self):
        from services.admin_data.workflow_runtime_activation_data import (
            AdminWorkflowRuntimeActivationProvider,
        )

        context = self._dream_context()
        provider = AdminWorkflowRuntimeActivationProvider()
        provider.activate_workflow_runtime = unittest.mock.Mock()
        verified = {
            "package_spec": "ink-dream-story@platform-builtin",
            "resolved_version": "1.0.0",
            "artifact_digest": "sha256:" + "a" * 64,
            "has_manifest": True,
            "physical_path": "/must-not-cross-the-interface",
        }

        with (
            unittest.mock.patch.object(
                _db,
                "get_db",
                side_effect=AssertionError(
                    "Dream Runtime activation opened PostgreSQL"
                ),
            ),
            unittest.mock.patch(
                "libs.claude_agent_kit.server.plugin_launcher.read_workspace_launch_manifest",
                return_value=[verified],
            ),
        ):
            await service_module._activate_story_workspace_dream_runtime(
                context=context,
                actor_id="7",
                cwd="/server-owned/thread-workspace",
                remote_session_ref="claude-session-runtime-repair",
                provider=provider,
            )

        provider.activate_workflow_runtime.assert_called_once_with(
            actor_id="7",
            thread_id=context.thread_id,
            workflow_run_id=context.workflow_run_id,
            remote_session_ref="claude-session-runtime-repair",
            verified_plugins=[
                {
                    key: verified[key]
                    for key in (
                        "package_spec",
                        "resolved_version",
                        "artifact_digest",
                        "has_manifest",
                    )
                }
            ],
        )

    async def test_dream_sdk_init_fails_closed_without_admin_activation_provider(self):
        from services.story_workspace.dream_runtime_activation_service import (
            StoryWorkspaceDreamRuntimeActivationError,
        )

        with (
            unittest.mock.patch.object(
                _db,
                "get_db",
                side_effect=AssertionError(
                    "Dream Runtime activation opened PostgreSQL"
                ),
            ),
            unittest.mock.patch(
                "libs.claude_agent_kit.server.plugin_launcher.read_workspace_launch_manifest",
                return_value=[],
            ),
        ):
            with self.assertRaises(StoryWorkspaceDreamRuntimeActivationError):
                await service_module._activate_story_workspace_dream_runtime(
                    context=self._dream_context(),
                    actor_id="7",
                    cwd="/server-owned/thread-workspace",
                    remote_session_ref="sdk-thread",
                )

    async def test_dream_turn_skips_legacy_standalone_proposal_persistence(self):
        service = ClaudeAgentService(
            context_builder=_FakeContextBuilder(),
            dream_context_mapper=_StaticDreamContextMapper(self._dream_context()),
        )
        request = ClaudeAgentRunRequest(
            user_id="7",
            thread_id="thread_dream_turn",
        )
        with unittest.mock.patch.object(
            service_module,
            "parse_agent_story_output",
        ) as parse:
            result = await service._store_story_workspace_output(
                SimpleNamespace(request=request, dream_context=self._dream_context()),
                '{"title":"legacy"}',
            )
        self.assertIsNone(result)
        parse.assert_not_called()

    async def test_workspace_pack_fails_closed_without_the_admin_metadata_owner(self):
        with unittest.mock.patch.object(
            service_module,
            "pack_workspace_plugins_with_refs_loader",
        ) as pack:
            with self.assertRaisesRegex(
                service_module.AdminDataError,
                "ADMIN_CONFIGURATION_INVALID",
            ):
                service_module._pack_thread_workspace_plugins(
                    "/workspace/thread",
                    "deck-dream",
                    actor_id="7",
                    thread_id="thread-dream",
                    admin_turn_persistence=object(),  # type: ignore[arg-type]
                    dream_mode=True,
                )
        pack.assert_not_called()

    async def test_system_config_is_loaded_before_resume_db_lookup(self):
        builder = _FakeContextBuilder()
        service = ClaudeAgentService(
            context_builder=builder,
            dream_context_mapper=_StaticDreamContextMapper(None),
        )
        state = AgentRunState(session_id="thread_service_config")
        request = ClaudeAgentRunRequest(
            user_id="7",
            thread_id="thread_service_config",
            message_parts=[{"type": "text", "text": "hello"}],
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_path = Path(tmp_dir) / "thread_service_config"
            with (
                unittest.mock.patch.dict(
                    os.environ,
                    {"INK_AGENT_SANDBOX_ENABLED": "false"},
                ),
                unittest.mock.patch.object(
                    _db,
                    "get_system_config",
                    return_value={
                        "system_prompt": "Settings page prompt",
                        "im_full_access_enabled": True,
                        "workspace_enabled": True,
                        "sandbox_network_mode": "allowlist",
                        "sandbox_network_allowed_domains": [
                            "raw.githubusercontent.com",
                            "*.npmjs.org",
                        ],
                        "sandbox_fs_allowed_write_paths": [
                            "/data/out",
                            "/var/cache",
                        ],
                        "env_vars": {
                            "ANTHROPIC_AUTH_TOKEN": "user-token",
                            "INK_AGENT_WORKFLOW_RUN_ID": "run_" + "9" * 32,
                            "INK_AGENT_STORY_WORKSPACE_MESSAGE_ID": (
                                "dream_agent_" + "9" * 64
                            ),
                            "EMPTY": None,
                            "  CUSTOM_KEY  ": "custom-value",
                        },
                    },
                ) as get_system_config,
                unittest.mock.patch.object(
                    _db,
                    "get_chat_thread",
                    return_value=None,
                ) as get_chat_thread,
                unittest.mock.patch.object(
                    service_module,
                    "get_or_create_workspace",
                    return_value=workspace_path,
                ) as get_or_create_workspace,
            ):
                execution = await service.assemble_context(
                    request,
                    state=state,
                    bus=_FakeBus(),
                    runner=unittest.mock.Mock(),
                )

        get_system_config.assert_called_once_with(7)
        self.assertEqual(builder.system_prompt_calls, [([], "Settings page prompt")])
        get_chat_thread.assert_called_once_with("thread_service_config", 7)
        get_or_create_workspace.assert_called_once_with(
            "thread_service_config",
            sandbox_enabled=False,
            sandbox_network_mode="allowlist",
            sandbox_network_allowed_domains=[
                "raw.githubusercontent.com",
                "*.npmjs.org",
            ],
            sandbox_fs_allowed_write_paths=[
                "/data/out",
                "/var/cache",
            ],
        )

        self.assertTrue(execution.run_options.im_full_access_enabled)
        self.assertEqual(execution.run_options.sandbox_network_mode, "allowlist")
        self.assertEqual(
            execution.run_options.system_prompt,
            "system-prompt:0:Settings page prompt",
        )
        self.assertEqual(str(workspace_path), execution.run_options.cwd)
        self.assertEqual(
            str(workspace_path),
            execution.run_options.claude_tmp_workspace,
        )
        self.assertEqual(
            execution.run_options.mcp_env,
            {
                "ANTHROPIC_AUTH_TOKEN": "user-token",
                "CUSTOM_KEY": "custom-value",
                "INK_AGENT_USER_ID": "7",
                "INK_AGENT_THREAD_ID": "thread_service_config",
            },
        )
        self.assertEqual(
            execution.run_options.user_sdk_env["ANTHROPIC_AUTH_TOKEN"],
            "user-token",
        )
        self.assertNotIn(
            "INK_AGENT_WORKFLOW_RUN_ID",
            execution.run_options.user_sdk_env,
        )
        self.assertNotIn(
            "INK_AGENT_STORY_WORKSPACE_MESSAGE_ID",
            execution.run_options.user_sdk_env,
        )

    async def test_workspace_mode_disabled_skips_workspace_initialization(self):
        builder = _FakeContextBuilder()
        managed_loader = _managed_loader()
        service = ClaudeAgentService(
            context_builder=builder,
            managed_mcp_runtime_snapshot_loader=managed_loader,
        )
        state = AgentRunState(session_id="thread_workspace_disabled")
        state.with_cwd("/tmp/stale-workspace")
        request = ClaudeAgentRunRequest(
            user_id="7",
            thread_id="thread_workspace_disabled",
            cwd="/tmp/client-workspace",
            message_parts=[{"type": "text", "text": "hello"}],
        )
        with (
            unittest.mock.patch.object(
                _db,
                "get_system_config",
                return_value={"workspace_enabled": False},
            ),
            unittest.mock.patch.object(
                _db,
                "get_chat_thread",
                return_value=None,
            ),
            unittest.mock.patch.object(
                service_module,
                "get_or_create_workspace",
            ) as get_or_create_workspace,
            unittest.mock.patch.object(
                service_module,
                "get_or_create_thread_runtime_workspace",
                return_value=Path("/tmp/thread-runtime/thread_workspace_disabled"),
            ) as get_or_create_thread_runtime_workspace,
        ):
            execution = await service.assemble_context(
                request,
                state=state,
                bus=_FakeBus(),
                runner=unittest.mock.Mock(),
            )

        get_or_create_workspace.assert_not_called()
        get_or_create_thread_runtime_workspace.assert_called_once_with(
            "thread_workspace_disabled"
        )
        self.assertEqual(state.cwd, "")
        self.assertIsNone(execution.run_options.cwd)
        self.assertEqual(
            execution.run_options.claude_tmp_workspace,
            "/tmp/thread-runtime/thread_workspace_disabled",
        )
        self.assertIsNone(execution.run_options.notion_credential_home)
        self.assertEqual(builder.user_message_calls[0]["cwd"], "")
        managed_loader.load.assert_awaited_once_with("7", None)

    async def test_workspace_mode_disabled_injects_managed_mcp_snapshot(self):
        managed_loader = _managed_loader({
            "remote-readonly": {
                "type": "http",
                "url": "https://mcp.example.test/mcp",
            }
        })
        service = ClaudeAgentService(
            context_builder=_FakeContextBuilder(),
            managed_mcp_runtime_snapshot_loader=managed_loader,
        )
        request = ClaudeAgentRunRequest(
            user_id="7",
            thread_id="thread_workspace_disabled_mcp",
            message_parts=[{"type": "text", "text": "hello"}],
        )

        with (
            unittest.mock.patch.object(
                _db,
                "get_system_config",
                return_value={"workspace_enabled": False},
            ),
            unittest.mock.patch.object(
                service_module,
                "get_or_create_thread_runtime_workspace",
                return_value=Path("/tmp/thread-runtime/thread_workspace_disabled_mcp"),
            ),
        ):
            execution = await service.assemble_context(
                request,
                state=AgentRunState(session_id=request.thread_id),
                bus=_FakeBus(),
                runner=unittest.mock.Mock(),
            )

        managed_loader.load.assert_awaited_once_with("7", None)
        self.assertEqual(
            execution.run_options.claude_mcp_servers,
            {
                "remote-readonly": {
                    "type": "http",
                    "url": "https://mcp.example.test/mcp",
                }
            },
        )

    async def test_settings_system_prompt_change_rebuilds_cached_system_prompt(self):
        builder = _FakeContextBuilder()
        service = ClaudeAgentService(context_builder=builder)
        state = AgentRunState(session_id="thread_service_prompt_change")
        state.with_system_prompt(
            "cached-old-prompt",
            system_config_system_prompt="old settings prompt",
        )
        state.is_context_initialized = True
        request = ClaudeAgentRunRequest(
            user_id="7",
            thread_id="thread_service_prompt_change",
            message_parts=[{"type": "text", "text": "hello"}],
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_path = Path(tmp_dir) / "thread_service_prompt_change"
            with (
                unittest.mock.patch.object(
                    _db,
                    "get_system_config",
                    return_value={"system_prompt": "new settings prompt"},
                ),
                unittest.mock.patch.object(
                    _db,
                    "get_chat_thread",
                    return_value=None,
                ),
                unittest.mock.patch.object(
                    service_module,
                    "get_or_create_workspace",
                    return_value=workspace_path,
                ),
            ):
                execution = await service.assemble_context(
                    request,
                    state=state,
                    bus=_FakeBus(),
                    runner=unittest.mock.Mock(),
                )

        self.assertEqual(builder.system_prompt_calls, [([], "new settings prompt")])
        self.assertEqual(state.system_config_system_prompt, "new settings prompt")
        self.assertEqual(
            execution.run_options.system_prompt,
            "system-prompt:0:new settings prompt",
        )

    async def test_admin_recent_sessions_load_only_on_first_build_and_settings_rebuild(self):
        builder = _FakeContextBuilder()
        owner = _bind_test_grant(unittest.mock.Mock(spec=AdminTurnPersistence))
        broker_env = {
            "INK_SESSION_BROKER_HOST": "127.0.0.1",
            "INK_SESSION_BROKER_PORT": "31415",
            "INK_SESSION_BROKER_CAPABILITY": "a" * 43,
            "INK_SESSION_BROKER_TIMEOUT_SECONDS": "10.0",
            "INK_SESSION_BROKER_MAX_BYTES": "1048576",
        }
        owner.session_projection_child_env.return_value = broker_env
        owner.system_config.side_effect = [
            {"workspace_enabled": False, "system_prompt": "old"},
            {"workspace_enabled": False, "system_prompt": "old"},
            {"workspace_enabled": False, "system_prompt": "new"},
        ]
        owner.thread.return_value = None
        owner.recent_sessions.side_effect = [
            (SessionPreviewDTO(
                id="session-a",
                name="第一篇",
                labels=["日记"],
                created_at="2026-09-14T08:00:00Z",
                updated_at="2026-09-15T09:00:00Z",
                first_line="早晨",
                text=None,
            ),),
            (SessionPreviewDTO(
                id="session-b",
                name="第二篇",
                labels=[],
                created_at="2026-09-15T08:00:00Z",
                updated_at="2026-09-15T10:00:00Z",
                first_line="夜晚",
                text=None,
            ),),
        ]
        service = _ProductionClaudeAgentService(
            context_builder=builder,
            managed_mcp_runtime_snapshot_loader=_managed_loader(),
        )
        request = ClaudeAgentRunRequest(
            user_id="7",
            thread_id="thread_admin_recent_context",
            message_parts=[{"type": "text", "text": "hello"}],
            admin_workflow_resolution=AdminWorkflowResolution(
                "7", "thread_admin_recent_context", None
            ),
            admin_turn_persistence=owner,
        )

        with tempfile.TemporaryDirectory() as tmp_dir, unittest.mock.patch.object(
            service_module,
            "get_or_create_thread_runtime_workspace",
            return_value=Path(tmp_dir),
        ):
            state = AgentRunState(session_id=request.thread_id)
            first = await service.assemble_context(
                request, state=state, bus=_FakeBus(), runner=unittest.mock.Mock()
            )
            cached = await service.assemble_context(
                request, state=state, bus=_FakeBus(), runner=unittest.mock.Mock()
            )
            rebuilt = await service.assemble_context(
                request, state=state, bus=_FakeBus(), runner=unittest.mock.Mock()
            )

        self.assertEqual(owner.recent_sessions.call_count, 2)
        self.assertTrue(broker_env.items() <= first.run_options.mcp_env.items())
        self.assertEqual(
            [call[0][0]["id"] for call in builder.system_prompt_calls],
            ["session-a", "session-b"],
        )
        self.assertEqual(first.run_options.system_prompt, "system-prompt:1:old")
        self.assertEqual(cached.run_options.system_prompt, "system-prompt:1:old")
        self.assertEqual(rebuilt.run_options.system_prompt, "system-prompt:1:new")

    async def test_admin_recent_session_failure_stops_before_context_without_db_fallback(self):
        builder = _FakeContextBuilder()
        owner = _bind_test_grant(unittest.mock.Mock(spec=AdminTurnPersistence))
        owner.system_config.return_value = {"workspace_enabled": False}
        owner.thread.return_value = None
        owner.recent_sessions.side_effect = RuntimeError("synthetic Admin failure")
        service = _ProductionClaudeAgentService(
            context_builder=builder,
            managed_mcp_runtime_snapshot_loader=_managed_loader(),
        )
        request = ClaudeAgentRunRequest(
            user_id="7",
            thread_id="thread_admin_recent_failure",
            message_parts=[{"type": "text", "text": "hello"}],
            admin_workflow_resolution=AdminWorkflowResolution(
                "7", "thread_admin_recent_failure", None
            ),
            admin_turn_persistence=owner,
        )

        with (
            tempfile.TemporaryDirectory() as tmp_dir,
            unittest.mock.patch.object(
                service_module,
                "get_or_create_thread_runtime_workspace",
                return_value=Path(tmp_dir),
            ) as runtime_workspace,
            unittest.mock.patch.object(
                _db,
                "list_sessions_in_range",
                side_effect=AssertionError("legacy range helper must not run"),
            ) as legacy_range,
            unittest.mock.patch.object(
                _db,
                "list_sessions",
                side_effect=AssertionError("legacy Session helper must not run"),
            ) as legacy_all,
        ):
            with self.assertRaisesRegex(RuntimeError, "synthetic Admin failure"):
                await service.assemble_context(
                    request,
                    state=AgentRunState(session_id=request.thread_id),
                    bus=_FakeBus(),
                    runner=unittest.mock.Mock(),
                )

        self.assertEqual(builder.system_prompt_calls, [])
        runtime_workspace.assert_not_called()
        legacy_range.assert_not_called()
        legacy_all.assert_not_called()

    async def test_session_broker_unavailable_stops_before_context_or_runtime_workspace(self):
        builder = _FakeContextBuilder()
        owner = _bind_test_grant(unittest.mock.Mock(spec=AdminTurnPersistence))
        owner.system_config.return_value = {"workspace_enabled": False}
        owner.session_projection_child_env.side_effect = RuntimeError(
            "SESSION_BROKER_UNAVAILABLE"
        )
        service = _ProductionClaudeAgentService(context_builder=builder)
        request = ClaudeAgentRunRequest(
            user_id="7",
            thread_id="thread_session_broker_failure",
            message_parts=[{"type": "text", "text": "hello"}],
            admin_workflow_resolution=AdminWorkflowResolution(
                "7", "thread_session_broker_failure", None
            ),
            admin_turn_persistence=owner,
        )

        with unittest.mock.patch.object(
            service_module, "get_or_create_thread_runtime_workspace"
        ) as runtime_workspace:
            with self.assertRaisesRegex(RuntimeError, "SESSION_BROKER_UNAVAILABLE"):
                await service.assemble_context(
                    request,
                    state=AgentRunState(session_id=request.thread_id),
                    bus=_FakeBus(),
                    runner=unittest.mock.Mock(),
                )

        self.assertEqual(builder.system_prompt_calls, [])
        runtime_workspace.assert_not_called()

    async def test_system_config_load_failure_stops_before_context_or_workspace(self):
        builder = _FakeContextBuilder()
        service = ClaudeAgentService(context_builder=builder)
        state = AgentRunState(session_id="thread_service_config_failure")
        request = ClaudeAgentRunRequest(
            user_id="7",
            thread_id="thread_service_config_failure",
            message_parts=[{"type": "text", "text": "hello"}],
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_path = Path(tmp_dir) / "thread_service_config_failure"
            with (
                unittest.mock.patch.object(
                    _db,
                    "get_system_config",
                    side_effect=RuntimeError("system_config unavailable"),
                ),
                unittest.mock.patch.object(
                    _db,
                    "get_chat_thread",
                    return_value=None,
                ) as get_chat_thread,
                unittest.mock.patch.object(
                    service_module,
                    "get_or_create_workspace",
                    return_value=workspace_path,
                ) as get_or_create_workspace,
            ):
                with self.assertRaisesRegex(RuntimeError, "system_config unavailable"):
                    await service.assemble_context(
                        request,
                        state=state,
                        bus=_FakeBus(),
                        runner=unittest.mock.Mock(),
                    )

        self.assertEqual(builder.system_prompt_calls, [])
        get_chat_thread.assert_not_called()
        get_or_create_workspace.assert_not_called()

    async def test_production_service_without_turn_owner_fails_before_legacy_or_context(self):
        builder = _FakeContextBuilder()
        service = _ProductionClaudeAgentService(context_builder=builder)
        state = AgentRunState(session_id="thread_service_ownerless")
        request = ClaudeAgentRunRequest(
            user_id="7",
            thread_id="thread_service_ownerless",
            message_parts=[{"type": "text", "text": "hello"}],
        )

        with (
            unittest.mock.patch.object(
                _db,
                "get_system_config",
                side_effect=AssertionError("legacy SystemConfig must not run"),
            ) as legacy_config,
            unittest.mock.patch.object(
                service_module,
                "get_or_create_workspace",
                side_effect=AssertionError("workspace must not run"),
            ) as get_or_create_workspace,
        ):
            with self.assertRaisesRegex(Exception, "ADMIN_CONFIGURATION_INVALID"):
                await service.assemble_context(
                    request,
                    state=state,
                    bus=_FakeBus(),
                    runner=unittest.mock.Mock(),
                )

        legacy_config.assert_not_called()
        get_or_create_workspace.assert_not_called()
        self.assertEqual(builder.system_prompt_calls, [])


class TestClaudeAgentServiceNotionAttach(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        loader = _managed_loader()
        self._managed_mcp_loader_patch = unittest.mock.patch.object(
            claude_mcp_service_module,
            "get_default_managed_mcp_runtime_snapshot_loader",
            return_value=loader,
        )
        self._managed_mcp_loader_patch.start()

    def tearDown(self) -> None:
        self._managed_mcp_loader_patch.stop()

    async def test_workspace_attach_materializes_notion_snapshot_into_workspace_files(self):
        builder = _FakeContextBuilder()
        service = ClaudeAgentService(
            context_builder=builder,
            dream_context_mapper=_StaticDreamContextMapper(None),
        )
        state = AgentRunState(session_id="thread_notion_attach")
        request = ClaudeAgentRunRequest(
            user_id="7",
            thread_id="thread_notion_attach",
            message_parts=[{"type": "text", "text": "hello"}],
        )

        snapshot_metadata = {
            "workspace_id": "thread_notion_attach",
            "resource_connector_id": "connector-attach",
            "snapshot_version": "snap-attach-001",
            "source_revision": "rev-attach-001",
            "sync_cursor": "cursor-attach-001",
            "fetched_at": "2026-07-04T00:00:00Z",
            "state": "snapshot_ready",
        }
        snapshot_payload = {
            "metadata": snapshot_metadata,
            "connector": {
                "id": "connector-attach",
                "platform": "notion",
                "auth_status": "authenticated",
            },
            "index": [{"page_id": "page-attach", "title": "Attach Page"}],
            "databases": [{"database_id": "db-attach", "title": "Attach Database"}],
            "database_pages": {
                "db-attach": [{"page_id": "page-attach", "title": "Attach Page"}],
            },
            "pages": {},
        }

        class _FakeFacade:
            def materialize_workspace(self, workspace_path: Path, connector_id=None, workspace_id=None):
                del connector_id, workspace_id
                notion_dir = workspace_path / ".notion"
                notion_dir.mkdir(parents=True, exist_ok=True)
                (notion_dir / "README.md").write_text(
                    """# Notion connector index

## Skill index

- Catalog revision: `catalog-attach-001`
- Skill: `notion-session` — Notion 工作空间助手
  - Availability: `available`
  - Instructions: workspace-root `skills/notion-session/SKILL.md`
  - Runtime discovery: `.claude/skills/notion-session`
- Skill: `notion-cli` — Notion CLI 工作空间数据助手
  - Availability: `available`
  - Instructions: workspace-root `skills/notion-cli/SKILL.md`
  - Runtime discovery: `.claude/skills/notion-cli`
- Use an available Skill whenever a request requires the connected Notion.
- Follow the selected Skill's index-first workflow before reading or changing remote content.
- If the selected Skill is unavailable, report the Notion limitation and continue any answer that does not depend on Notion.
""",
                    encoding="utf-8",
                )
                (notion_dir / "connector.json").write_text(
                    json.dumps(
                        {
                            "id": "connector-attach",
                            "platform": "notion",
                            "auth_status": "authenticated",
                            "selected_databases": ["db-attach"],
                            "selected_pages": ["page-attach"],
                            "snapshot": snapshot_metadata,
                        },
                        ensure_ascii=False,
                        indent=2,
                        sort_keys=True,
                    ),
                    encoding="utf-8",
                )
                (notion_dir / "snapshot.json").write_text(
                    json.dumps(snapshot_metadata, ensure_ascii=False, indent=2, sort_keys=True),
                    encoding="utf-8",
                )
                (notion_dir / "index.json").write_text(
                    json.dumps(
                        {"pages": snapshot_payload["index"], "snapshot": snapshot_metadata},
                        ensure_ascii=False,
                        indent=2,
                        sort_keys=True,
                    ),
                    encoding="utf-8",
                )
                (notion_dir / "databases.json").write_text(
                    json.dumps(
                        {"databases": snapshot_payload["databases"], "snapshot": snapshot_metadata},
                        ensure_ascii=False,
                        indent=2,
                        sort_keys=True,
                    ),
                    encoding="utf-8",
                )

            def project_runtime_credentials(self, workspace_path: Path, connector_id=None):
                del connector_id
                notion_home = workspace_path / ".notion-home"
                notion_home.mkdir(mode=0o700, parents=True, exist_ok=True)
                notion_home.chmod(0o700)
                auth_path = notion_home / "auth.json"
                auth_path.write_text('{"access_token":"test-only-secret"}\n', encoding="utf-8")
                auth_path.chmod(0o600)
                return SimpleNamespace(available=True, thread_home=notion_home)

        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_path = Path(tmp_dir) / "thread_notion_attach"
            with (
                unittest.mock.patch.object(
                    _db,
                    "get_system_config",
                    return_value={"workspace_enabled": True},
                ),
                unittest.mock.patch.object(
                    _db,
                    "get_chat_thread",
                    return_value=None,
                ),
                unittest.mock.patch.object(
                    service_module,
                    "get_or_create_workspace",
                    return_value=workspace_path,
                ),
                unittest.mock.patch(
                    "notion.build_notion_facade",
                    return_value=_FakeFacade(),
                ) as build_notion_facade,
                unittest.mock.patch.object(
                    service_module,
                    "sync_builtin_workspace_skills",
                    return_value=SimpleNamespace(linked_source_paths=("/builtin/common", "/builtin/notion")),
                ) as sync_builtin_workspace_skills,
                unittest.mock.patch.object(
                    service_module,
                    "sync_workspace_sandbox_settings",
                ) as sync_workspace_sandbox_settings,
            ):
                execution = await service.assemble_context(
                    request,
                    state=state,
                    bus=_FakeBus(),
                    runner=unittest.mock.Mock(),
                )

            build_notion_facade.assert_called_once_with(
                7,
                connector_store=unittest.mock.ANY,
            )
            sync_builtin_workspace_skills.assert_called_once_with(
                workspace_path,
                enabled_platforms={"notion"},
                prune_inactive_platforms=True,
            )
            self.assertEqual(
                sync_workspace_sandbox_settings.call_args.kwargs[
                    "builtin_skill_read_paths"
                ],
                ("/builtin/common", "/builtin/notion"),
            )
            self.assertEqual(execution.run_options.cwd, str(workspace_path))
            self.assertEqual(
                execution.run_options.notion_credential_home,
                str(workspace_path / ".notion-home"),
            )
            self.assertNotIn(
                "test-only-secret",
                repr(execution.run_options),
            )
            self.assertEqual(builder.user_message_calls[0]["cwd"], str(workspace_path))
            notion_block = workspace_context_module.build_workspace_context_block(
                str(workspace_path),
                editor_session_id="session-attach",
            )
            self.assertIn("Notion lightweight index (.notion/):", notion_block)
            self.assertIn(
                "Notion Skill index (from .notion/README.md):",
                notion_block,
            )
            self.assertIn("Skill: `notion-session`", notion_block)
            self.assertIn(
                "Instructions: workspace-root `skills/notion-session/SKILL.md`",
                notion_block,
            )
            self.assertIn(
                "Runtime discovery: `.claude/skills/notion-session`",
                notion_block,
            )
            self.assertIn("Skill: `notion-cli`", notion_block)
            self.assertIn(
                "Instructions: workspace-root `skills/notion-cli/SKILL.md`",
                notion_block,
            )
            self.assertIn(
                "Runtime discovery: `.claude/skills/notion-cli`",
                notion_block,
            )
            self.assertIn(
                "continue any answer that does not depend on Notion",
                notion_block,
            )
            self.assertIn(
                "Read .notion/pages/<page_id>.json to fetch that page's current Markdown on demand.",
                notion_block,
            )
            self.assertIn("Connector ID: connector-attach", notion_block)
            self.assertIn("snapshot snap-attach-001", notion_block)
            self.assertIn("Source Revision: rev-attach-001", notion_block)
            self.assertIn("Sync Cursor: cursor-attach-001", notion_block)
            self.assertIn("Last Synced: 2026-07-04T00:00:00Z", notion_block)

    async def test_notion_initialization_failure_is_redacted_and_turn_context_survives(self):
        builder = _FakeContextBuilder()
        service = ClaudeAgentService(
            context_builder=builder,
            dream_context_mapper=_StaticDreamContextMapper(None),
        )
        state = AgentRunState(session_id="thread_notion_degraded")
        request = ClaudeAgentRunRequest(
            user_id="7",
            thread_id="thread_notion_degraded",
            message_parts=[{"type": "text", "text": "continue without Notion"}],
        )
        secret = "credential-text-must-not-enter-log"

        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_path = Path(tmp_dir) / "thread_notion_degraded"
            workspace_path.mkdir()
            stale_snapshot = workspace_path / ".notion"
            stale_snapshot.mkdir()
            (stale_snapshot / "index.json").write_text(
                '{"pages":[{"title":"stale"}]}',
                encoding="utf-8",
            )
            with (
                unittest.mock.patch.object(
                    _db,
                    "get_system_config",
                    return_value={"workspace_enabled": True},
                ),
                unittest.mock.patch.object(
                    _db,
                    "get_chat_thread",
                    return_value=None,
                ),
                unittest.mock.patch.object(
                    service_module,
                    "get_or_create_workspace",
                    return_value=workspace_path,
                ),
                unittest.mock.patch(
                    "notion.build_notion_facade",
                    side_effect=RuntimeError(secret),
                ),
                unittest.mock.patch.object(
                    service_module,
                    "sync_builtin_workspace_skills",
                    return_value=SimpleNamespace(linked_source_paths=("/builtin/common",)),
                ) as sync_builtin_workspace_skills,
                unittest.mock.patch.object(
                    service_module,
                    "sync_workspace_sandbox_settings",
                ),
                self.assertLogs(service_module.logger, level="WARNING") as logs,
            ):
                execution = await service.assemble_context(
                    request,
                    state=state,
                    bus=_FakeBus(),
                    runner=unittest.mock.Mock(),
                )
            stale_snapshot_removed = not stale_snapshot.exists()

        self.assertEqual(execution.run_options.cwd, str(workspace_path))
        self.assertIsNone(execution.run_options.notion_credential_home)
        self.assertTrue(stale_snapshot_removed)
        sync_builtin_workspace_skills.assert_called_once_with(
            workspace_path,
            enabled_platforms=set(),
            prune_inactive_platforms=True,
        )
        self.assertNotIn(secret, "\n".join(logs.output))
        self.assertIn("Notion Runtime projection failed safely", "\n".join(logs.output))


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def _parse_sse(frame: str | NormalizedAgentEvent) -> dict:
    if isinstance(frame, NormalizedAgentEvent):
        return frame.payload()
    assert frame.startswith("data: ")
    return json.loads(frame[len("data: "):].strip())


class TestClaudeAgentServiceToolInputDelta(unittest.TestCase):
    def test_tool_input_delta_emits_start_then_delta_without_collecting(self):
        async def scenario():
            queue: asyncio.Queue[str] = asyncio.Queue()
            turn_ctx = _TurnContext(
                queue=queue,
                confirmation_store=ToolConfirmationStore(),
            )
            turn_ctx.tool_input_by_id["tool-call-1"] = {
                "editor_session_id": "session-editor-write",
                "cellId": "cell-1",
            }
            callback = ClaudeAgentService._make_tool_event_cb(queue, turn_ctx)

            await callback(
                ToolEventPayload(
                    type="tool_input_delta",
                    tool_name="Write",
                    tool_call_id="call-write",
                    output='{"file_path":"files/note.md"',
                )
            )

            first = _parse_sse(queue.get_nowait())
            second = _parse_sse(queue.get_nowait())

            return first, second, turn_ctx

        first, second, turn_ctx = _run(scenario())

        self.assertEqual(first["type"], "tool-input-start")
        self.assertEqual(first["toolCallId"], "call-write")
        self.assertEqual(first["toolName"], "Write")
        self.assertEqual(second["type"], "tool-input-delta")
        self.assertEqual(second["toolCallId"], "call-write")
        self.assertEqual(second["toolName"], "Write")
        self.assertEqual(second["delta"], '{"file_path":"files/note.md"')
        self.assertEqual(turn_ctx.collected_parts, [])


class TestClaudeAgentServiceEditorWriteEvents(unittest.TestCase):
    def test_editor_write_tool_result_publishes_session_event(self):
        async def scenario():
            queue: asyncio.Queue[str] = asyncio.Queue()
            turn_ctx = _TurnContext(
                queue=queue,
                confirmation_store=ToolConfirmationStore(),
            )
            turn_ctx.tool_name_by_id["tool-call-1"] = "mcp__editor__write_segment"
            turn_ctx.tool_input_by_id["tool-call-1"] = {
                "editor_session_id": "session-editor-write",
                "cellId": "cell-1",
            }
            turn_ctx.registered_tool_call_ids.add("tool-call-1")
            state = AgentRunState(session_id="thread-editor-write")
            state.with_editor_state({"id": "session-editor-write"}, 7)
            refreshed_state = {
                "id": "session-editor-write",
                "cells": [{"id": "cell-1", "type": "text", "content": "new"}],
            }
            runtime = _FakeAdminEditorRuntime(
                {"session-editor-write": refreshed_state}
            )
            callback = ClaudeAgentService._make_tool_event_cb(
                queue, turn_ctx, state, runtime
            )
            subscription = await service_module.session_event_bus.subscribe("7")

            try:
                await callback(
                    ToolEventPayload(
                        type="tool_result",
                        tool_name="mcp__editor__write_segment",
                        tool_call_id="tool-call-1",
                        output={"ok": True, "cellId": "cell-1"},
                        is_error=False,
                    )
                )

                event = await asyncio.wait_for(subscription.get(), timeout=1.0)
            finally:
                await service_module.session_event_bus.unsubscribe("7", subscription)

            self.assertEqual(runtime.load_calls, [])
            self.assertEqual(event.type, "session_updated")
            self.assertEqual(event.session_id, "session-editor-write")
            self.assertEqual(event.source, "agent")
            self.assertEqual(event.tool_call_id, "tool-call-1")
            self.assertEqual(event.tool_name, "mcp__editor__write_segment")
            self.assertEqual(state.editor_state["cells"][0]["content"], "new")

        _run(scenario())

    def test_editor_write_business_failure_is_tool_error_without_side_effects(self):
        async def scenario(error: str):
            queue: asyncio.Queue = asyncio.Queue()
            turn_ctx = _TurnContext(queue=queue, confirmation_store=ToolConfirmationStore())
            turn_ctx.tool_name_by_id["tool-call-failed"] = "mcp__editor__write_segment"
            turn_ctx.tool_input_by_id["tool-call-failed"] = {
                "editor_session_id": "session-editor-write",
                "cellId": "cell-1",
            }
            turn_ctx.registered_tool_call_ids.add("tool-call-failed")
            state = AgentRunState(session_id="thread-editor-write-failed")
            original_state = {
                "id": "session-editor-write",
                "cells": [{"id": "cell-1", "type": "text", "content": "old"}],
            }
            state.with_editor_state(original_state, 7)
            refreshed_state = {
                "id": "session-editor-write",
                "cells": [],
            }
            runtime = _FakeAdminEditorRuntime(
                {"session-editor-write": refreshed_state}
            )
            callback = ClaudeAgentService._make_tool_event_cb(
                queue, turn_ctx, state, runtime
            )
            subscription = await service_module.session_event_bus.subscribe("7")

            try:
                output = {"ok": False, "error": error, "cellId": "cell-1"}
                await callback(ToolEventPayload(
                    type="tool_result",
                    tool_name="mcp__editor__write_segment",
                    tool_call_id="tool-call-failed",
                    output=output,
                    is_error=False,
                ))
                frame = await queue.get()
                with self.assertRaises(asyncio.TimeoutError):
                    await asyncio.wait_for(subscription.get(), timeout=0.01)
            finally:
                await service_module.session_event_bus.unsubscribe("7", subscription)

            self.assertEqual(frame.type, "tool-output-available")
            self.assertTrue(frame.data["isError"])
            self.assertEqual(frame.data["output"], output)
            self.assertEqual(turn_ctx.collected_parts[-1]["isError"], True)
            self.assertEqual(state.editor_state, refreshed_state)
            self.assertEqual(runtime.load_calls, [])

        for error in ("cell_not_found", "save_failed"):
            with self.subTest(error=error):
                _run(scenario(error))

    def test_stdio_editor_business_failure_is_unwrapped_and_reclassified(self):
        output = {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "ok": False,
                    "error": "cell_not_found",
                    "cellId": "cell-1",
                }),
            }],
            "isError": False,
        }
        self.assertFalse(service_module._tool_result_ok(output))
        self.assertTrue(service_module._is_editor_tool_result_error(
            "mcp__editor__write_segment",
            output,
        ))

    def test_non_editor_structured_output_is_not_reclassified(self):
        self.assertFalse(service_module._is_editor_tool_result_error(
            "mcp__other__tool", {"ok": False, "error": "domain_result"}
        ))


class TestClaudeAgentServiceStopCancellation(unittest.TestCase):
    def test_execute_session_cancel_flushes_partial_and_closes_stream(self):
        async def scenario():
            artifact_hook = unittest.mock.Mock()
            service = ClaudeAgentService(dream_artifact_turn_hook=artifact_hook)
            queue: asyncio.Queue[str | None] = asyncio.Queue()
            turn_ctx = _TurnContext(
                queue=queue,
                confirmation_store=ToolConfirmationStore(),
            )
            state = AgentRunState(session_id="thread-stop-service")
            request = ClaudeAgentRunRequest(
                user_id="7",
                thread_id="thread-stop-service",
                message_parts=[{"type": "text", "text": "hello"}],
                admin_turn_persistence=_LegacyTurnPersistence(),
            )
            session_id = "44444444-4444-4444-8444-444444444444"

            class _CancelRunner:
                async def run_streaming(self, opts, callbacks):
                    del opts
                    assert callbacks.on_message is not None
                    from claude_agent_sdk.types import SystemMessage
                    await callbacks.on_message(
                        SystemMessage(subtype="init", data={"session_id": session_id})
                    )
                    await callbacks.on_text_delta("partial")
                    raise asyncio.CancelledError()

            execution = service_module._TurnExecution(
                request=request,
                state=state,
                runner=_CancelRunner(),
                run_options=unittest.mock.Mock(),
                turn_context=turn_ctx,
                dream_artifact_turn_ticket=unittest.mock.sentinel.dream_ticket,
            )

            with (
                unittest.mock.patch.object(
                    service,
                    "_persist_user_message",
                    new=unittest.mock.AsyncMock(),
                ) as persist_user,
                unittest.mock.patch.object(
                    service,
                    "_persist_partial_assistant",
                    new=unittest.mock.AsyncMock(),
                ) as persist_partial,
                unittest.mock.patch.object(
                    _db,
                    "update_chat_thread_claude_session",
                ) as persist_session,
            ):
                with self.assertRaises(asyncio.CancelledError):
                    await service.execute_session(execution)

            frames: list[str | None] = []
            while not queue.empty():
                frames.append(queue.get_nowait())
            return persist_user, persist_partial, persist_session, frames, artifact_hook

        persist_user, persist_partial, persist_session, frames, artifact_hook = _run(scenario())

        persist_user.assert_awaited_once()
        persist_partial.assert_awaited_once()
        self.assertEqual(persist_partial.await_args.kwargs["turn_status"], "cancelled")
        persist_session.assert_called_once_with(
            "thread-stop-service",
            "44444444-4444-4444-8444-444444444444",
            service_module._AGENT_RUNTIME_CONTRACT_VERSION,
        )
        parsed_frames = [_parse_sse(frame) for frame in frames if frame is not None]
        metadata_frame = next(
            frame for frame in parsed_frames if frame["type"] == "message-metadata"
        )
        self.assertTrue(metadata_frame["turnId"])
        self.assertEqual(parsed_frames[-1]["type"], "finish")
        self.assertEqual(parsed_frames[-1]["finishReason"], "stop")
        self.assertIs(parsed_frames[-1]["cancelled"], True)
        self.assertIsNone(frames[-1])
        artifact_hook.after_main_turn.assert_not_called()


class TestClaudeAgentMessageIdentityPersistence(unittest.TestCase):
    def test_completed_final_projection_requires_one_text_suffix_after_process(self):
        self.assertEqual(
            service_module._completed_turn_final_part_index([
                {"type": "reasoning", "text": "分析"},
                {"type": "text", "text": "中间说明"},
                {"type": "tool-invocation", "toolCallId": "tool-1"},
                {"type": "text", "text": "最终正文"},
            ]),
            3,
        )
        self.assertIsNone(service_module._completed_turn_final_part_index([
            {"type": "tool-invocation", "toolCallId": "tool-1"},
        ]))
        self.assertIsNone(service_module._completed_turn_final_part_index([
            {"type": "reasoning", "text": "分析"},
            {"type": "text", "text": "正文一"},
            {"type": "text", "text": "正文二"},
        ]))

    def test_completed_repair_persists_collected_sse_parts_and_source(self):
        async def scenario():
            import database

            service = ClaudeAgentService()
            turn_ctx = _TurnContext(
                queue=asyncio.Queue(),
                confirmation_store=ToolConfirmationStore(),
            )
            turn_ctx.collected_parts.extend([
                {"type": "reasoning-start", "id": "reasoning-1"},
                {"type": "reasoning-delta", "id": "reasoning-1", "delta": "检查工作区"},
                {"type": "reasoning-end", "id": "reasoning-1"},
                {"type": "text-start", "id": "text-1"},
                {"type": "text-delta", "id": "text-1", "delta": "修正完成"},
                {"type": "text-end", "id": "text-1"},
            ])
            execution = service_module._TurnExecution(
                request=ClaudeAgentRunRequest(
                    user_id="7",
                    thread_id="thread-persist-repair",
                    message_id="dream_repair_stable",
                    message_parts=[{"type": "text", "text": "自动修正"}],
                    message_metadata={
                        "kind": "story-workspace-dream-auto-repair",
                    },
                    model="claude-test",
                    admin_turn_persistence=_LegacyTurnPersistence(),
                ),
                state=AgentRunState(session_id="thread-persist-repair"),
                runner=unittest.mock.Mock(),
                run_options=unittest.mock.Mock(),
                turn_context=turn_ctx,
                dream_context=SimpleNamespace(
                    workflow_run_id="run_" + "a" * 32,
                    thread_id="thread-persist-repair",
                ),
            )
            result = AgentRunResult(
                full_text="修正完成",
                session_id="claude-session",
                success=True,
                usage={"input_tokens": 3, "output_tokens": 2},
                duration_ms=1250,
            )
            with (
                unittest.mock.patch.object(database, "save_chat_message") as save,
                unittest.mock.patch.object(
                    database,
                    "update_chat_thread_claude_session",
                ),
            ):
                await service._persist_assistant_turn(execution, result)
            return save.call_args

        call = _run(scenario())
        self.assertEqual(call.args[:2], ("thread-persist-repair", "assistant"))
        self.assertEqual(call.kwargs["parts"], [
            {"type": "reasoning", "id": "reasoning-1", "text": "检查工作区"},
            {"type": "text", "text": "修正完成"},
        ])
        metadata = call.kwargs["metadata"]
        self.assertEqual(metadata["usage"]["totalTokens"], 5)
        self.assertEqual(metadata["turnStatus"], "completed")
        self.assertEqual(metadata["finalPartIndex"], 1)
        self.assertEqual(metadata["durationMs"], 1250)
        self.assertTrue(metadata["turnId"])
        self.assertEqual(call.kwargs["history_final_text"], "修正完成")
        self.assertTrue(call.kwargs["history_process_available"])
        self.assertEqual(call.kwargs["history_projection_version"], 1)
        self.assertEqual(
            metadata["story_workspace_dream_source"]["kind"],
            "story-workspace-dream-auto-repair",
        )

    def test_claimed_confirmation_uses_admin_owner_without_postgres(self):
        async def scenario():
            import database

            service = ClaudeAgentService()
            owner = _bind_test_grant(unittest.mock.Mock(spec=AdminTurnPersistence))
            request = ClaudeAgentRunRequest(
                user_id="7",
                thread_id="thread-confirmation-owner",
                message_id="dream_confirm_" + "a" * 64,
                message_parts=[{"type": "text", "text": "confirm"}],
                message_metadata={
                    "kind": "story-workspace-dream-confirmation",
                    "dispatch_status": "dispatching",
                    "dispatch_claim_id": "claim-owner",
                },
                user_message_pre_persisted=True,
                admin_turn_persistence=owner,
            )
            execution = service_module._TurnExecution(
                request=request,
                state=AgentRunState(session_id=request.thread_id),
                runner=unittest.mock.Mock(),
                run_options=unittest.mock.Mock(),
                turn_context=_TurnContext(
                    queue=asyncio.Queue(),
                    confirmation_store=ToolConfirmationStore(),
                ),
            )
            with (
                unittest.mock.patch.object(
                    database,
                    "get_db",
                    side_effect=AssertionError("confirmation must not open PostgreSQL"),
                ) as get_db,
                unittest.mock.patch.object(
                    database,
                    "save_chat_message",
                    side_effect=AssertionError("confirmation must not save through PostgreSQL"),
                ) as save_chat_message,
            ):
                await service._persist_user_message(execution)
                service._save_assistant_message(
                    request,
                    parts=[{"type": "text", "text": "done"}],
                    metadata={"turnStatus": "completed", "finalPartIndex": 0},
                    history_final_text="done",
                    history_process_available=False,
                    history_projection_version=1,
                )
            get_db.assert_not_called()
            save_chat_message.assert_not_called()
            return owner

        owner = _run(scenario())
        owner.persist_user.assert_not_called()
        owner.persist_assistant.assert_called_once()

    def test_admin_identity_and_transport_failures_stop_before_inference(self):
        async def scenario(failure: service_module.AdminDataError):
            service = ClaudeAgentService()
            queue: asyncio.Queue = asyncio.Queue()
            turn_ctx = _TurnContext(
                queue=queue,
                confirmation_store=ToolConfirmationStore(
                    thread_id="thread-identity",
                    turn_id="turn-identity",
                ),
            )
            state = AgentRunState(session_id="thread-identity")
            class RejectingPersistence(AdminAgentTurnPersistence):
                def persist_user(self, **_kwargs):
                    raise failure

            request = ClaudeAgentRunRequest(
                user_id="7",
                thread_id="thread-identity",
                message_id="public-message-1",
                message_parts=[{"type": "text", "text": "hello"}],
                admin_turn_persistence=RejectingPersistence(),
            )
            runner = unittest.mock.Mock()
            runner.run_streaming = unittest.mock.AsyncMock()
            execution = service_module._TurnExecution(
                request=request,
                state=state,
                runner=runner,
                run_options=unittest.mock.Mock(),
                turn_context=turn_ctx,
            )
            with self.assertRaises(service_module.AdminDataError) as caught:
                await service.execute_session(execution)
            self.assertIs(caught.exception, failure)
            return runner

        for failure in (
            service_module.AdminDataError("CHAT_MESSAGE_IDENTITY_CONFLICT", 409),
            service_module.AdminDataError("ADMIN_UNAVAILABLE", 503),
        ):
            with self.subTest(failure=failure.code):
                runner = _run(scenario(failure))
                runner.run_streaming.assert_not_awaited()


class TestClaudeAgentServiceErrorFormatting(unittest.TestCase):
    def test_execute_session_emits_one_error_when_runner_also_calls_on_error(self):
        async def scenario():
            artifact_hook = unittest.mock.Mock()
            service = ClaudeAgentService(dream_artifact_turn_hook=artifact_hook)
            queue: asyncio.Queue[str | None] = asyncio.Queue()
            turn_ctx = _TurnContext(
                queue=queue,
                confirmation_store=ToolConfirmationStore(),
            )
            state = AgentRunState(session_id="thread-error-service")
            request = ClaudeAgentRunRequest(
                user_id="7",
                thread_id="thread-error-service",
                message_parts=[{"type": "text", "text": "hello"}],
            )

            class _CallbackAndResultErrorRunner:
                async def run_streaming(self, opts, callbacks):
                    del opts
                    error = RuntimeError(
                        "Claude SDK AssistantMessage error: authentication_failed "
                        "| provider_detail: 403 usage limit exceeded"
                    )
                    await callbacks.on_error(error)
                    return AgentRunResult(
                        full_text="",
                        session_id=None,
                        success=False,
                        error=error,
                    )

            execution = service_module._TurnExecution(
                request=request,
                state=state,
                runner=_CallbackAndResultErrorRunner(),
                run_options=unittest.mock.Mock(),
                turn_context=turn_ctx,
                dream_artifact_turn_ticket=unittest.mock.sentinel.dream_ticket,
            )

            with (
                unittest.mock.patch.object(
                    service,
                    "_persist_user_message",
                    new=unittest.mock.AsyncMock(),
                ),
                unittest.mock.patch.object(
                    service,
                    "_persist_partial_assistant",
                    new=unittest.mock.AsyncMock(),
                ),
            ):
                await service.execute_session(execution)

            frames: list[str | None] = []
            while not queue.empty():
                frames.append(queue.get_nowait())
            return frames, artifact_hook

        frames, artifact_hook = _run(scenario())
        parsed_frames = [_parse_sse(frame) for frame in frames if frame is not None]

        self.assertEqual(
            sum(frame["type"] == "error" for frame in parsed_frames),
            1,
        )
        self.assertEqual(
            sum(
                frame["type"] == "finish" and frame["finishReason"] == "error"
                for frame in parsed_frames
            ),
            1,
        )
        self.assertEqual(sum(frame is None for frame in frames), 1)
        self.assertIsNone(frames[-1])
        artifact_hook.after_main_turn.assert_not_called()

    def test_successful_root_turn_synchronizes_before_terminal_finish(self):
        async def scenario():
            order: list[str] = []
            artifact_hook = unittest.mock.Mock()
            artifact_hook.after_main_turn.side_effect = lambda _ticket: (
                order.append("hook")
                or SimpleNamespace(
                    changed_stages=("characters",),
                    private_artifact_changed=True,
                    private_files=("stories/demo/project.yaml",),
                    story_index_status="updated",
                )
            )
            service = ClaudeAgentService(dream_artifact_turn_hook=artifact_hook)
            queue: asyncio.Queue[str | None] = asyncio.Queue()
            turn_ctx = _TurnContext(
                queue=queue,
                confirmation_store=ToolConfirmationStore(),
            )
            state = AgentRunState(session_id="thread-success-service")
            request = ClaudeAgentRunRequest(
                user_id="7",
                thread_id="thread-success-service",
                message_parts=[{"type": "text", "text": "hello"}],
            )

            class _SuccessRunner:
                async def run_streaming(self, opts, callbacks):
                    del opts, callbacks
                    return AgentRunResult(
                        full_text="done",
                        session_id="55555555-5555-4555-8555-555555555555",
                        success=True,
                    )

            execution = service_module._TurnExecution(
                request=request,
                state=state,
                runner=_SuccessRunner(),
                run_options=unittest.mock.Mock(),
                turn_context=turn_ctx,
                dream_artifact_turn_ticket=unittest.mock.sentinel.dream_ticket,
            )
            with (
                unittest.mock.patch.object(
                    service,
                    "_persist_user_message",
                    new=unittest.mock.AsyncMock(),
                ),
                unittest.mock.patch.object(
                    service,
                    "_persist_assistant_turn",
                    new=unittest.mock.AsyncMock(
                        side_effect=lambda *_args: order.append("assistant")
                    ),
                ),
                unittest.mock.patch.object(
                    service,
                    "_store_story_workspace_output",
                    new=unittest.mock.AsyncMock(return_value=None),
                ),
            ):
                await service.execute_session(execution)
            frames: list[str | None] = []
            while not queue.empty():
                frames.append(queue.get_nowait())
            return artifact_hook, frames, order

        artifact_hook, frames, order = _run(scenario())
        self.assertEqual(order, ["assistant", "hook"])
        artifact_hook.after_main_turn.assert_called_once_with(
            unittest.mock.sentinel.dream_ticket
        )
        parsed_frames = [_parse_sse(frame) for frame in frames if frame is not None]
        self.assertEqual(parsed_frames[-1]["type"], "finish")
        self.assertIsNone(frames[-1])

    def test_unexpected_post_hook_failure_is_typed_after_assistant_commit(self):
        async def scenario():
            order: list[str] = []
            artifact_hook = unittest.mock.Mock()

            def fail_after_main_turn(_ticket):
                order.append("hook")
                raise RuntimeError("fixture database detail must stay private")

            artifact_hook.after_main_turn.side_effect = fail_after_main_turn
            service = ClaudeAgentService(dream_artifact_turn_hook=artifact_hook)
            execution = service_module._TurnExecution(
                request=ClaudeAgentRunRequest(
                    user_id="7",
                    thread_id="thread-post-hook-failure",
                    message_parts=[{"type": "text", "text": "同步角色卡"}],
                ),
                state=AgentRunState(session_id="thread-post-hook-failure"),
                runner=unittest.mock.Mock(
                    run_streaming=unittest.mock.AsyncMock(
                        return_value=AgentRunResult(
                            full_text="角色卡已写入。",
                            session_id="claude-session",
                            success=True,
                        )
                    )
                ),
                run_options=unittest.mock.Mock(),
                turn_context=_TurnContext(
                    queue=asyncio.Queue(),
                    confirmation_store=ToolConfirmationStore(),
                ),
                dream_artifact_turn_ticket=unittest.mock.sentinel.dream_ticket,
            )
            with (
                unittest.mock.patch.object(
                    service,
                    "_persist_user_message",
                    new=unittest.mock.AsyncMock(),
                ),
                unittest.mock.patch.object(
                    service,
                    "_persist_assistant_turn",
                    new=unittest.mock.AsyncMock(
                        side_effect=lambda *_args: order.append("assistant")
                    ),
                ) as persist_assistant,
            ):
                with self.assertRaises(
                    service_module.DreamArtifactSyncAfterCommitError
                ) as raised:
                    await service.execute_session(execution)
            return raised.exception, persist_assistant, order

        error, persist_assistant, order = _run(scenario())

        persist_assistant.assert_awaited_once()
        self.assertEqual(order, ["assistant", "hook"])
        self.assertEqual(error.code, "DREAM_ARTIFACT_SYNC_FAILED_AFTER_COMMIT")
        self.assertEqual(error.sync_error_code, "DREAM_ARTIFACT_SYNC_FAILED")
        self.assertEqual(
            error.public_message,
            "Agent 回复已保存，但 Dream 工作区同步未完成。"
            "请重新加载对话核对工作台状态，无需重发消息。",
        )
        self.assertNotIn("fixture database detail", error.public_message)
        self.assertIsInstance(error.__cause__, RuntimeError)

    def test_assistant_persistence_failure_prevents_post_hook(self):
        async def scenario():
            artifact_hook = unittest.mock.Mock()
            service = ClaudeAgentService(dream_artifact_turn_hook=artifact_hook)
            execution = service_module._TurnExecution(
                request=ClaudeAgentRunRequest(
                    user_id="7",
                    thread_id="thread-persist-failure",
                    message_parts=[{"type": "text", "text": "hello"}],
                ),
                state=AgentRunState(session_id="thread-persist-failure"),
                runner=unittest.mock.Mock(
                    run_streaming=unittest.mock.AsyncMock(
                        return_value=AgentRunResult(
                            full_text="done",
                            session_id="claude-session",
                            success=True,
                        )
                    )
                ),
                run_options=unittest.mock.Mock(),
                turn_context=_TurnContext(
                    queue=asyncio.Queue(),
                    confirmation_store=ToolConfirmationStore(),
                ),
                dream_artifact_turn_ticket=unittest.mock.sentinel.dream_ticket,
            )
            with (
                unittest.mock.patch.object(
                    service,
                    "_persist_user_message",
                    new=unittest.mock.AsyncMock(),
                ),
                unittest.mock.patch.object(
                    service,
                    "_persist_assistant_turn",
                    new=unittest.mock.AsyncMock(
                        side_effect=service_module.ClaudeAgentAssistantPersistenceError()
                    ),
                ),
            ):
                with self.assertRaises(
                    service_module.ClaudeAgentAssistantPersistenceError
                ):
                    await service.execute_session(execution)
            return artifact_hook

        artifact_hook = _run(scenario())
        artifact_hook.after_main_turn.assert_not_called()

    def test_make_error_cb_includes_exception_notes(self):
        async def scenario():
            queue: asyncio.Queue[str] = asyncio.Queue()
            callback = ClaudeAgentService._make_error_cb(queue)
            exc = RuntimeError("Command failed with exit code 1")
            exc.add_note("[claude_agent_kit] sandbox_hint: apply-seccomp denied")
            await callback(exc)
            return _parse_sse(queue.get_nowait())

        frame = _run(scenario())
        self.assertEqual(frame["type"], "error")
        self.assertIn("Command failed with exit code 1", frame["errorText"])
        self.assertIn("sandbox_hint", frame["errorText"])


if __name__ == "__main__":
    unittest.main()
