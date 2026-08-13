# [Input] Consume ClaudeAgentService, ClaudeAgentRunRequest, AgentRunState,
#         service callback factories, and ToolEventPayload.
# [Output] Verify context assembly maps system_config into AgentRunOptions and
#          service-level SSE event mapping remains correct.
# [Pos] test node in backend/tests
# [Sync] 2026-06-14: combine system_config assembly coverage with tool_input_delta
#                    -> tool-input-delta SSE forwarding coverage.
# [Sync] 2026-06-14: cover Edit Session event publication after successful
#                    editor MCP write tool results.
# [Sync] 2026-06-17: cover SSE error formatting that includes exception notes
#                    from runner diagnostics.
# [Sync] 2026-06-21: cover sandbox network policy handoff to workspace init.
# [Sync] 2026-06-22: cover Settings SYSTEM_PROMPT handoff into system_prompt
#                    assembly, config-change cache rebuild, and config-load
#                    failure fallback.
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

"""Tests for ClaudeAgentService context assembly and SSE event mapping."""
from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
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

import claude_agent.service as service_module
import claude_agent.workspace_context as workspace_context_module
from claude_agent.service import (
    ClaudeAgentRunRequest,
    ClaudeAgentService,
    _TurnContext,
)
from claude_agent.thread_pool import AgentRunState
from claude_agent.tool_confirmation_store import ToolConfirmationStore
from claude_agent.stream_events import NormalizedAgentEvent
from libs.claude_agent_kit.types import AgentRunResult, ToolEventPayload
from story_workspace.contracts import StoryWorkspaceDreamRunContext
class _FakeContextBuilder:
    def __init__(self) -> None:
        self.system_prompt_calls: list[tuple[str, str | None]] = []
        self.user_message_calls: list[dict[str, Any]] = []

    async def build_system_prompt(
        self,
        user_id: str,
        *,
        configured_system_prompt: str | None = None,
    ) -> str:
        self.system_prompt_calls.append((user_id, configured_system_prompt))
        suffix = f":{configured_system_prompt}" if configured_system_prompt else ""
        return f"system-prompt:{user_id}{suffix}"

    def build_user_message(self, message_parts: list | None, **kwargs: Any) -> list[dict[str, Any]]:
        self.user_message_calls.append(kwargs)
        return [{"type": "text", "text": "assembled"}]


class _FakeBus:
    async def publish(self, frame: str | None) -> None:
        pass


class _StaticDreamContextMapper:
    def __init__(self, context: StoryWorkspaceDreamRunContext | None) -> None:
        self.context = context
        self.calls: list[tuple[str, str]] = []

    def resolve(self, *, actor_id: str, thread_id: str):
        self.calls.append((str(actor_id), thread_id))
        return self.context


class TestStoryWorkspaceOutputTransaction(unittest.TestCase):
    def test_commits_the_story_bundle_before_emitting_success(self):
        db = unittest.mock.Mock()
        db.execute.return_value.fetchone.return_value = None
        payload = unittest.mock.Mock()
        with (
            unittest.mock.patch.object(service_module._db, "get_db", return_value=db),
            unittest.mock.patch.object(
                service_module, "get_or_create_default_workspace", return_value="workspace-1"
            ),
            unittest.mock.patch.object(
                service_module,
                "store_agent_story_output",
                return_value={"story_id": "story-1"},
            ),
        ):
            result = service_module._store_story_workspace_output_sync(
                7, "thread-1", payload
            )

        self.assertEqual(result["story_id"], "story-1")
        db.commit.assert_called_once_with()
        db.rollback.assert_not_called()
        db.close.assert_called_once_with()

    def test_rolls_back_the_story_bundle_when_persistence_fails(self):
        db = unittest.mock.Mock()
        failure = RuntimeError("fixture persistence failure")
        with (
            unittest.mock.patch.object(service_module._db, "get_db", return_value=db),
            unittest.mock.patch.object(
                service_module, "get_or_create_default_workspace", return_value="workspace-1"
            ),
            unittest.mock.patch.object(
                service_module, "store_agent_story_output", side_effect=failure
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "fixture persistence failure"):
                service_module._store_story_workspace_output_sync(
                    7, "thread-1", unittest.mock.Mock()
                )

        db.rollback.assert_called_once_with()
        db.commit.assert_not_called()
        db.close.assert_called_once_with()


class TestClaudeAgentServiceAssembleContext(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._dream_thread_loader = unittest.mock.patch.object(
            service_module._db,
            "get_chat_thread",
            return_value=None,
        )
        self._dream_thread_loader.start()

    def tearDown(self) -> None:
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

        def resolve_model(user_id: str, client_alias: str | None) -> str:
            selected_models.append((user_id, client_alias))
            return "dream-balanced"

        activator = unittest.mock.AsyncMock()
        mapper = _StaticDreamContextMapper(self._dream_context())
        service = ClaudeAgentService(
            context_builder=builder,
            platform_model_resolver=resolve_model,
            dream_context_mapper=mapper,
            dream_runtime_init_activator=activator,
        )
        state = AgentRunState(session_id="thread_dream_turn")
        context = mapper.context
        assert context is not None
        request = ClaudeAgentRunRequest(
            user_id="7",
            thread_id="thread_dream_turn",
            message_id="dream_agent_" + "a" * 64,
            message_parts=[{"type": "text", "text": "create Dream"}],
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_path = Path(tmp_dir) / "thread_dream_turn"
            workspace_path.mkdir()
            with (
                unittest.mock.patch.object(
                    service_module._db,
                    "get_system_config",
                    return_value={"workspace_enabled": True},
                ),
                unittest.mock.patch.object(
                    service_module._db,
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
            dream_mode=True,
        )
        self.assertIs(
            builder.user_message_calls[0]["story_workspace_dream_context"],
            context,
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
        self.assertEqual(mapper.calls, [("7", "thread_dream_turn")])
        activator.assert_awaited_once_with(
            context=context,
            actor_id="7",
            cwd=str(workspace_path),
            remote_session_ref="thread_dream_turn",
        )
        self.assertEqual(execution.run_options.model, "dream-balanced")
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

    async def test_shared_thread_resume_uses_persisted_claude_session(self):
        service = ClaudeAgentService(
            context_builder=_FakeContextBuilder(),
            platform_model_resolver=lambda _user_id, _alias: "dream-balanced",
            dream_context_mapper=_StaticDreamContextMapper(None),
        )
        session_id = "11111111-1111-4111-8111-111111111111"
        request = ClaudeAgentRunRequest(
            user_id="7",
            thread_id="thread-shared-resume",
            resume=True,
            message_parts=[{"type": "text", "text": "继续"}],
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_path = Path(tmp_dir) / request.thread_id
            transcript = (
                workspace_path
                / ".claude-home"
                / "projects"
                / "project"
                / f"{session_id}.jsonl"
            )
            transcript.parent.mkdir(parents=True)
            transcript.write_text("{}\n", encoding="utf-8")
            with (
                unittest.mock.patch.object(
                    service_module._db,
                    "get_system_config",
                    return_value={"workspace_enabled": True},
                ),
                unittest.mock.patch.object(
                    service_module._db,
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

    def test_dream_runtime_has_no_stream_message_callback(self):
        service = ClaudeAgentService(
            dream_context_mapper=_StaticDreamContextMapper(None),
        )
        self.assertFalse(hasattr(service, "_make_dream_runtime_init_cb"))

    def test_dream_runtime_has_no_deployment_environment_gate(self):
        from services.story_workspace.dream_runtime_activation_service import (
            StoryWorkspaceDreamRuntimeActivationService,
        )

        parameters = inspect.signature(
            StoryWorkspaceDreamRuntimeActivationService
        ).parameters
        self.assertNotIn("environment_id", parameters)
        self.assertNotIn("deployment_tier", parameters)

    async def test_dream_sdk_init_reprovisions_frozen_runtime_evidence_before_activation(self):
        context = self._dream_context()
        db = unittest.mock.Mock()
        db.in_transaction = True
        db.execute.return_value.fetchone.return_value = {
            "workspace_id": "workspace-dream",
            "source_voice_thread_id": context.thread_id,
        }
        provisioner = unittest.mock.Mock()
        provisioner_factory = unittest.mock.Mock(return_value=provisioner)
        activation = unittest.mock.Mock()
        activation.activate_from_assembled_context = unittest.mock.AsyncMock()
        activation_factory = unittest.mock.Mock(return_value=activation)
        init = {
            "session_id": "claude-session-runtime-repair",
            "tools": ["mcp__story_workspace__write_dream_run"],
        }

        with (
            unittest.mock.patch.object(
                service_module._db, "get_db", return_value=db
            ),
            unittest.mock.patch(
                "libs.claude_agent_kit.server.plugin_launcher.read_workspace_launch_manifest",
                return_value=[{"package_spec": "ink-dream-story@platform-builtin"}],
            ),
            unittest.mock.patch(
                "services.story_workspace.dream_launch_infrastructure.DreamRuntimeProvisioningService",
                provisioner_factory,
            ),
            unittest.mock.patch(
                "services.story_workspace.dream_runtime_activation_service.StoryWorkspaceDreamRuntimeActivationService",
                activation_factory,
            ),
            unittest.mock.patch(
                "services.story_workspace.workflow_security.story_workspace_workflow_token_secret",
                return_value=b"runtime-test-secret",
            ),
        ):
            await service_module._activate_story_workspace_dream_runtime(
                context=context,
                actor_id="7",
                cwd="/server-owned/thread-workspace",
                remote_session_ref=init["session_id"],
            )

        provisioner_factory.assert_called_once_with(db)
        provisioner.ensure_frozen_runtime_evidence.assert_called_once_with(
            context.runtime_plugin_lock_id
        )
        activation.activate_from_assembled_context.assert_awaited_once()
        self.assertNotIn("deployment_tier", activation_factory.call_args.kwargs)
        self.assertNotIn("environment_id", activation_factory.call_args.kwargs)
        db.close.assert_called_once_with()

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

    async def test_workspace_pack_adds_server_adapter_only_for_dream_turn(self):
        db = unittest.mock.Mock()
        with (
            unittest.mock.patch.object(
                service_module._db, "get_db", return_value=db
            ),
            unittest.mock.patch.object(
                service_module, "pack_workspace_plugins"
            ) as pack,
        ):
            service_module._pack_thread_workspace_plugins(
                "/workspace/thread", "deck-dream"
            )
            service_module._pack_thread_workspace_plugins(
                "/workspace/thread", "deck-dream", dream_mode=True
            )

        self.assertEqual(
            pack.call_args_list,
            [
                unittest.mock.call(
                    db,
                    workspace=Path("/workspace/thread"),
                    deck_id="deck-dream",
                    server_adapter_package_specs=(),
                ),
                unittest.mock.call(
                    db,
                    workspace=Path("/workspace/thread"),
                    deck_id="deck-dream",
                    server_adapter_package_specs=(
                        "ink-dream-story@platform-builtin",
                    ),
                ),
            ],
        )

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
                unittest.mock.patch.object(
                    service_module._db,
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
                    service_module._db,
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
        self.assertEqual(builder.system_prompt_calls, [("7", "Settings page prompt")])
        get_chat_thread.assert_called_once_with("thread_service_config", 7)
        get_or_create_workspace.assert_called_once_with(
            "thread_service_config",
            sandbox_enabled=True,
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
            "system-prompt:7:Settings page prompt",
        )
        self.assertEqual(str(workspace_path), execution.run_options.cwd)
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
        service = ClaudeAgentService(context_builder=builder)
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
                service_module._db,
                "get_system_config",
                return_value={"workspace_enabled": False},
            ),
            unittest.mock.patch.object(
                service_module._db,
                "get_chat_thread",
                return_value=None,
            ),
            unittest.mock.patch.object(
                service_module,
                "get_or_create_workspace",
            ) as get_or_create_workspace,
        ):
            execution = await service.assemble_context(
                request,
                state=state,
                bus=_FakeBus(),
                runner=unittest.mock.Mock(),
            )

        get_or_create_workspace.assert_not_called()
        self.assertEqual(state.cwd, "")
        self.assertIsNone(execution.run_options.cwd)
        self.assertEqual(builder.user_message_calls[0]["cwd"], "")

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
                    service_module._db,
                    "get_system_config",
                    return_value={"system_prompt": "new settings prompt"},
                ),
                unittest.mock.patch.object(
                    service_module._db,
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

        self.assertEqual(builder.system_prompt_calls, [("7", "new settings prompt")])
        self.assertEqual(state.system_config_system_prompt, "new settings prompt")
        self.assertEqual(
            execution.run_options.system_prompt,
            "system-prompt:7:new settings prompt",
        )

    async def test_system_config_load_failure_builds_prompt_without_settings_prompt(self):
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
                    service_module._db,
                    "get_system_config",
                    side_effect=RuntimeError("system_config unavailable"),
                ),
                unittest.mock.patch.object(
                    service_module._db,
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

        self.assertEqual(builder.system_prompt_calls, [("7", None)])
        self.assertEqual(execution.run_options.system_prompt, "system-prompt:7")
        self.assertEqual(
            execution.run_options.mcp_env,
            {
                "INK_AGENT_USER_ID": "7",
                "INK_AGENT_THREAD_ID": "thread_service_config_failure",
            },
        )


class TestClaudeAgentServiceNotionAttach(unittest.IsolatedAsyncioTestCase):
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
            "pages": {
                "page-attach": {
                    "page_id": "page-attach",
                    "title": "Attach Page",
                    "url": "https://www.notion.so/page-attach",
                    "last_edited": "2026-07-04T00:00:00Z",
                    "properties": {"Name": {"title": [{"plain_text": "Attach Page"}]}},
                    "blocks": [{"type": "paragraph", "text": "Canonical snapshot"}],
                }
            },
        }

        class _FakeFacade:
            def materialize_workspace(self, workspace_path: Path, connector_id=None, workspace_id=None):
                del connector_id, workspace_id
                notion_dir = workspace_path / ".notion"
                notion_dir.mkdir(parents=True, exist_ok=True)
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

        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_path = Path(tmp_dir) / "thread_notion_attach"
            with (
                unittest.mock.patch.object(
                    service_module._db,
                    "get_system_config",
                    return_value={"workspace_enabled": True},
                ),
                unittest.mock.patch.object(
                    service_module._db,
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
            ):
                execution = await service.assemble_context(
                    request,
                    state=state,
                    bus=_FakeBus(),
                    runner=unittest.mock.Mock(),
                )

            build_notion_facade.assert_called_once_with(7)
            self.assertEqual(execution.run_options.cwd, str(workspace_path))
            self.assertEqual(builder.user_message_calls[0]["cwd"], str(workspace_path))
            notion_block = workspace_context_module.build_workspace_context_block(
                str(workspace_path),
                editor_session_id="session-attach",
            )
            self.assertIn("Notion device index (.notion/):", notion_block)
            self.assertIn("Connector ID: connector-attach", notion_block)
            self.assertIn("snapshot snap-attach-001", notion_block)
            self.assertIn("Source Revision: rev-attach-001", notion_block)
            self.assertIn("Sync Cursor: cursor-attach-001", notion_block)
            self.assertIn("Last Synced: 2026-07-04T00:00:00Z", notion_block)


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
            state = AgentRunState(session_id="thread-editor-write")
            state.with_editor_state({"id": "session-editor-write"}, 7)
            callback = ClaudeAgentService._make_tool_event_cb(queue, turn_ctx, state)
            subscription = await service_module.session_event_bus.subscribe("7")

            try:
                with unittest.mock.patch.object(
                    service_module._db,
                    "get_session",
                    return_value={
                        "id": "session-editor-write",
                        "editor_state": {
                            "id": "session-editor-write",
                            "cells": [{"id": "cell-1", "type": "text", "content": "new"}],
                        },
                    },
                ) as get_session:
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

            self.assertEqual(get_session.call_args.args, (7, "session-editor-write"))
            self.assertEqual(event.type, "session_updated")
            self.assertEqual(event.session_id, "session-editor-write")
            self.assertEqual(event.source, "agent")
            self.assertEqual(event.tool_call_id, "tool-call-1")
            self.assertEqual(event.tool_name, "mcp__editor__write_segment")
            self.assertEqual(state.editor_state["cells"][0]["content"], "new")

        _run(scenario())


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
            )
            session_id = "44444444-4444-4444-8444-444444444444"

            class _CancelRunner:
                async def run_streaming(self, opts, callbacks):
                    del opts
                    assert callbacks.on_message is not None
                    await callbacks.on_message(
                        SimpleNamespace(data={"session_id": session_id})
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
                    service_module._db,
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
        persist_session.assert_called_once_with(
            "thread-stop-service",
            "44444444-4444-4444-8444-444444444444",
            service_module._AGENT_RUNTIME_CONTRACT_VERSION,
        )
        parsed_frames = [_parse_sse(frame) for frame in frames if frame is not None]
        self.assertEqual(parsed_frames[-1]["type"], "finish")
        self.assertEqual(parsed_frames[-1]["finishReason"], "stop")
        self.assertIs(parsed_frames[-1]["cancelled"], True)
        self.assertIsNone(frames[-1])
        artifact_hook.after_main_turn.assert_not_called()


class TestClaudeAgentMessageIdentityPersistence(unittest.TestCase):
    def test_identity_and_postgres_failures_are_rethrown_before_inference(self):
        import database

        async def scenario(failure: BaseException):
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
            request = ClaudeAgentRunRequest(
                user_id="7",
                thread_id="thread-identity",
                message_id="public-message-1",
                message_parts=[{"type": "text", "text": "hello"}],
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
            guard_db = unittest.mock.Mock()
            with (
                unittest.mock.patch.object(database, "get_db", return_value=guard_db),
                unittest.mock.patch.object(
                    database,
                    "save_chat_message",
                    side_effect=failure,
                ),
                unittest.mock.patch(
                    "services.story_workspace.dream_confirmation_service."
                    "story_workspace_guard_persisted_dream_confirmation_turn",
                    return_value=False,
                ),
            ):
                with self.assertRaises(type(failure)):
                    await service.execute_session(execution)
            return runner

        for failure in (
            database.ChatMessageIdentityConflict("public-message-1"),
            database.PostgresError("database unavailable"),
        ):
            with self.subTest(failure=type(failure).__name__):
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
            artifact_hook = unittest.mock.Mock()
            artifact_hook.after_main_turn.return_value = SimpleNamespace(
                changed_stages=("characters",),
                private_artifact_changed=True,
                private_files=("stories/demo/project.yaml",),
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
                    new=unittest.mock.AsyncMock(),
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
            return artifact_hook, frames

        artifact_hook, frames = _run(scenario())
        artifact_hook.after_main_turn.assert_called_once_with(
            unittest.mock.sentinel.dream_ticket
        )
        parsed_frames = [_parse_sse(frame) for frame in frames if frame is not None]
        self.assertEqual(parsed_frames[-1]["type"], "finish")
        self.assertIsNone(frames[-1])

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
