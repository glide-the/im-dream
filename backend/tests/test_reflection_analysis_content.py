# [Input] Production Reflections source assembly, typed content contracts, router and actual section Runner.
# [Output] Provider-free coverage of scope, frozen bodies, references, Agent instructions and task report recovery.
# [Pos] Technical harness only; boundary replies are synthetic and no model or business database is used.
# [Sync] 2026-10-23: retain v1 source helpers while checking v2 route gates and actual-read citation evidence.
# [Sync] 2026-10-13: verify the complete affected backend execution path and fail-closed source assembly.
# [Sync] 2026-10-13: canonical normalized turn failures close reflection owners before transcript parsing.
# [Sync] 2026-10-13: cover bounded request-bound source preparation cache recovery,
#                    eviction, clock/timer races, and definite OAuth renewal retention.
# [Sync] 2026-10-13: lock final assistant-text parsing, explicit empty-array output,
#                    and rejection of earlier JSON embedded in final prose.
# [Sync] 2026-10-13: verify complete effective workflow/answer contracts follow
#                    frozen source context while custom workflow overrides remain effective.
# [Sync] 2026-10-13: verify Reflections runner selects the authenticated Gateway catalog model,
#                    preserves server-owned Claude Code runtime caps, rejects invalid/denied catalogs,
#                    and closes the Gateway/section owners before transcript access.
# [Sync] 2026-10-13: keep the final Notion citation allowlist complete for every frozen page,
#                    without deriving IDs from empty pages or links embedded in frozen bodies.
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

import reflections_agent as runtime
import routers.reflections as routes
from notion.factory import NotionConnectorFacade
from notion.operations import OperationResult
from services.admin_data.errors import AdminDataError
from services.admin_gateway.errors import GatewayInferenceError
from services.admin_gateway.models import GatewayModel, GatewayModelCatalog
from services.admin_data.delegation import RuntimeGrant
from services.admin_data.gateway_runtime import AdminGatewayRuntime
from notion.errors import NotionSnapshotNotReadyError
from services.admin_data.chat_models import ChatMessageDTO
from services.admin_data.models import AbsentReceiptDTO, CommittedReceiptDTO
import services.admin_data.reflection_analysis_content as content_module
from services.admin_data.reflection_analysis_content import (
    NotionPreparationCache, _PreparedNotionSource, analysis_content_candidates,
    clear_notion_analysis_preparation, freeze_notion_analysis_input,
)
from services.admin_data.reflection_analysis_content_data import (
    ANALYSIS_CONTENT_CONTRACT_VERSION, ANALYSIS_CONTENT_OPERATIONS, CONTENT_SCHEMA,
    AdminReflectionAnalysisContentData, ReflectionAnalysisSnapshotDTO,
    ReflectionAnalysisSummaryDTO, ReflectionAnalysisSummaryOutputDTO, ReflectionAnalysisLoadOutputDTO,
    ReflectionAnalysisCreateDTO, ReflectionAgentSnapshotDTO, ReflectionNotionInputDTO, ReflectionNotionPageDTO,
    require_analysis_content_capability,
)
from services.admin_data.reflection_task_models import (
    ReflectionTaskGetOutputDTO, ReflectionTaskPublicInputDTO, ReflectionSectionTranscriptOutputDTO,
    ReflectionTaskAdvanceOutputDTO, ReflectionSectionFinishOutputDTO, ReflectionTaskStartOutputDTO, ReflectionReportEnsureOutputDTO,
    ReflectionPromptSnapshotDTO,
)
from services.admin_data.request_auth import AdminRequestActor
from tests.test_reflections_agent import (
    TASK_ID, _load, _begin, _snapshot, _task, _runtime_http_config, _RouteOwner, _AppendWorker,
)
from services.admin_data.session_projection_broker import SessionProjectionBrokerSettings
from services.story_workspace.dream_lifecycle_observer import NormalizedTurnOutcome, NormalizedTurnResult

BODY = "I recorded the same worry on Monday and Friday."
PAGE_ID = "page-analysis"
CONNECTOR = "connector-analysis"
VERSION = "snapshot-analysis"


def selected_gateway_model() -> GatewayModel:
    return GatewayModel(
        model_alias="deepseek-analysis",
        display_name="DeepSeek Analysis",
        protocol="anthropic",
        capabilities={"chat": True, "tools": True},
        context_window=900_000,
        max_output_tokens=384_000,
        enabled=True,
        callable=True,
        availability="included",
        required_plan_code="pro",
        upgrade_hint=None,
        claude_code_auto_compact_window=800_000,
        claude_code_max_context_tokens=900_000,
    )


def frozen_content(*, notion=True, agent=True, diary=None):
    return ReflectionAnalysisSnapshotDTO(diary_session_ids=diary,
        notion=ReflectionNotionInputDTO(connector_id=CONNECTOR, snapshot_version=VERSION, empty_page_ids=[],
            pages=[ReflectionNotionPageDTO(page_id=PAGE_ID, title="Weekly notes", url="https://www.notion.so/analysis",
                markdown=BODY, content_sha256=hashlib.sha256(BODY.encode()).hexdigest(), read_at="2026-10-13T03:00:00Z")]) if notion else None,
        agent=ReflectionAgentSnapshotDTO(deck_id="deck-analysis", agent_id="agent-analysis", deck_name="Review",
            agent_name="Reflective analyst", system_prompt="Examine repeated assumptions carefully.") if agent else None)


class SourceFacade:
    """Only the existing external facade boundary is scripted; source logic stays in production."""
    _read_context = staticmethod(NotionConnectorFacade._read_context)

    def __init__(self, home):
        self.user_id = 7
        self.credential_store = SimpleNamespace(effective_home=lambda user_id: Path(home))
        self.connector = {"id": CONNECTOR, "user_id": 7, "auth_status": "authenticated", "platform": "notion",
            "updated_at": "2026-10-13T02:00:00Z", "sources": [{"resource_type": "notion_page", "external_id": PAGE_ID}]}
        self.snapshot = {"metadata": {"snapshot_version": VERSION},
            "connector": {"selected_pages": [PAGE_ID], "selected_databases": []},
            "index": [{"page_id": PAGE_ID, "title": "Weekly notes", "url": "https://www.notion.so/analysis"}], "pages": {}}
        self.identity = 1

    def get_connector(self):
        return deepcopy(self.connector)

    def get_current_snapshot(self):
        return deepcopy(self.snapshot)

    def _credential_identity(self):
        return self.identity


class SourceAssemblyTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ink-reflection-analysis-source-test-")
        self.facade = SourceFacade(self.temp.name)

    async def asyncTearDown(self):
        self.temp.cleanup()

    async def test_preview_uses_index_only_and_submission_freezes_actual_body_once(self):
        with patch("services.admin_data.reflection_analysis_content.NotionOperationClient") as client:
            self.assertEqual(analysis_content_candidates(self.facade)["page_count"], 1)
            client.assert_not_called()
            client.return_value.get_page_markdown = AsyncMock(return_value=OperationResult(success=True, data={"markdown": BODY}))
            value = await freeze_notion_analysis_input(self.facade, VERSION, CONNECTOR)
            self.assertEqual(value.pages[0].markdown, BODY)
            self.assertEqual(value.pages[0].content_sha256, hashlib.sha256(BODY.encode()).hexdigest())
            client.return_value.get_page_markdown.assert_awaited_once_with(PAGE_ID)
            self.assertNotIn("markdown", json.dumps(analysis_content_candidates(self.facade)))

    async def test_archived_index_pages_are_excluded_from_preview_and_body_reads(self):
        self.facade.snapshot["index"].append({"page_id": "archived-page", "title": "Old journal", "url": "", "archived": True})
        self.assertEqual(analysis_content_candidates(self.facade)["page_count"], 1)
        with patch("services.admin_data.reflection_analysis_content.NotionOperationClient") as client:
            client.return_value.get_page_markdown = AsyncMock(return_value=OperationResult(success=True, data={"markdown": BODY}))
            value = await freeze_notion_analysis_input(self.facade, VERSION, CONNECTOR)
            self.assertEqual([page.page_id for page in value.pages], [PAGE_ID])
            client.return_value.get_page_markdown.assert_awaited_once_with(PAGE_ID)

    async def test_identical_duplicate_index_pages_are_read_once(self):
        self.facade.snapshot["index"] *= 2
        with patch("services.admin_data.reflection_analysis_content.NotionOperationClient") as client:
            client.return_value.get_page_markdown = AsyncMock(return_value=OperationResult(success=True, data={"markdown": BODY}))
            result = await freeze_notion_analysis_input(self.facade, VERSION, CONNECTOR)
            self.assertEqual(len(result.pages), 1)
            self.assertEqual(client.return_value.get_page_markdown.await_count, 1)

    async def test_empty_bodies_are_distinguished_from_read_failures(self):
        with patch("services.admin_data.reflection_analysis_content.NotionOperationClient") as client:
            client.return_value.get_page_markdown = AsyncMock(return_value=OperationResult(success=True, data={"markdown": " \n"}))
            result = await freeze_notion_analysis_input(self.facade, VERSION, CONNECTOR)
            self.assertEqual(result.pages, [])
            self.assertEqual(result.empty_page_ids, [PAGE_ID])
            client.return_value.get_page_markdown = AsyncMock(side_effect=AdminDataError("NOTION_PERMISSION_DENIED", 403))
            with self.assertRaises(AdminDataError):
                await freeze_notion_analysis_input(self.facade, VERSION, CONNECTOR)

    async def test_changed_mount_version_connector_and_credential_fail_before_creation(self):
        for connector, version, code in [("other-connector", VERSION, "NOTION_CONNECTOR_CHANGED"),
                                        (CONNECTOR, "other-version", "NOTION_SNAPSHOT_CHANGED")]:
            with self.subTest(code=code), patch("services.admin_data.reflection_analysis_content.NotionOperationClient") as client:
                with self.assertRaises(AdminDataError) as error:
                    await freeze_notion_analysis_input(self.facade, version, connector)
                self.assertEqual(error.exception.code, code)
                client.assert_not_called()
        self.facade.connector["sources"] = []
        with self.assertRaises(AdminDataError) as error:
            analysis_content_candidates(self.facade)
        self.assertEqual(error.exception.code, "NOTION_ANALYSIS_SCOPE_CHANGED")
        self.facade.connector["sources"] = [{"resource_type": "notion_page", "external_id": PAGE_ID}]
        async def changed(_):
            self.facade.identity += 1
            return OperationResult(success=True, data={"markdown": BODY})
        with patch("services.admin_data.reflection_analysis_content.NotionOperationClient") as client:
            client.return_value.get_page_markdown = changed
            with self.assertRaises(Exception):
                await freeze_notion_analysis_input(self.facade, VERSION, CONNECTOR)

    async def test_no_snapshot_and_conflicting_duplicates_cannot_become_empty_success(self):
        self.facade.snapshot = None
        self.assertEqual(analysis_content_candidates(self.facade)["status"], "no_snapshot")
        with self.assertRaises(AdminDataError):
            await freeze_notion_analysis_input(self.facade, VERSION, CONNECTOR)
        self.facade.snapshot = {"metadata": {"snapshot_version": VERSION}, "connector": {"selected_pages": [PAGE_ID]},
            "index": [{"page_id": PAGE_ID, "title": "A"}, {"page_id": PAGE_ID, "title": "B"}]}
        with self.assertRaises(AdminDataError) as error:
            analysis_content_candidates(self.facade)
        self.assertEqual(error.exception.code, "NOTION_ANALYSIS_INDEX_INVALID")


class PreparationCacheTest(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.scheduled = []

        def schedule(delay, callback):
            item = SimpleNamespace(delay=delay, callback=callback, cancelled=False)
            item.cancel = lambda: setattr(item, "cancelled", True)
            self.scheduled.append(item)
            return item

        self.cache = NotionPreparationCache(
            ttl_seconds=10,
            max_entries=2,
            max_bytes=100_000,
            clock=lambda: self.now,
            schedule=schedule,
        )

    def prepared(self, body=BODY, *, identity=1):
        notion = frozen_content().notion.model_copy(update={
            "pages": [frozen_content().notion.pages[0].model_copy(update={"markdown": body})],
        })
        return _PreparedNotionSource(
            content=notion,
            context=("connector-context",),
            metadata={"snapshot_version": VERSION},
            credential_identity=identity,
        )

    def test_actor_and_request_key_are_isolated_and_fingerprint_conflicts(self):
        value = self.prepared()
        self.cache.put(("7", "same-key"), "fingerprint-a", value)
        self.cache.put(("8", "same-key"), "fingerprint-b", value)
        self.assertIs(self.cache.get(("7", "same-key"), "fingerprint-a"), value)
        self.assertIs(self.cache.get(("8", "same-key"), "fingerprint-b"), value)
        with self.assertRaises(AdminDataError) as failure:
            self.cache.get(("7", "same-key"), "fingerprint-other")
        self.assertEqual((failure.exception.code, failure.exception.status_code), ("REFLECTION_SUBMISSION_CONFLICT", 409))

        replacement = self.prepared("replacement")
        self.assertIs(self.cache.put(("7", "same-key"), "fingerprint-a", replacement), value)
        with self.assertRaises(AdminDataError) as failure:
            self.cache.put(("7", "same-key"), "fingerprint-other", replacement)
        self.assertEqual((failure.exception.code, failure.exception.status_code), ("REFLECTION_SUBMISSION_CONFLICT", 409))
        self.assertIs(self.cache.get(("7", "same-key"), "fingerprint-a"), value)

    def test_ttl_and_stale_timer_cannot_remove_a_replaced_entry(self):
        first = self.prepared("first")
        second = self.prepared("second")
        key = ("7", "timer-key")
        self.cache.put(key, "fingerprint-a", first)
        old_timer = self.scheduled[-1]
        self.cache.discard(key)
        self.cache.put(key, "fingerprint-b", second)
        old_timer.callback()
        self.assertIs(self.cache.get(key, "fingerprint-b"), second)
        self.now += 11
        self.assertIsNone(self.cache.get(key, "fingerprint-b"))

    def test_entry_and_byte_limits_evict_oldest_without_partial_content(self):
        first = self.prepared("a" * 1200)
        second = self.prepared("b" * 1200)
        third = self.prepared("c" * 1200)
        byte_size = lambda value: len(value.content.model_dump_json().encode()) + len(json.dumps(value.metadata).encode())
        cache = NotionPreparationCache(
            ttl_seconds=10,
            max_entries=2,
            max_bytes=byte_size(first) + byte_size(second),
            clock=lambda: self.now,
            schedule=self.cache._schedule,
        )
        cache.put(("7", "one"), "a", first)
        cache.put(("7", "two"), "b", second)
        cache.put(("7", "three"), "c", third)
        self.assertIsNone(cache.get(("7", "one"), "a"))
        self.assertIs(cache.get(("7", "two"), "b"), second)
        self.assertIs(cache.get(("7", "three"), "c"), third)

    def test_failed_source_read_never_leaves_partial_candidate_and_clear_removes_complete_one(self):
        value = self.prepared()
        key = ("7", "clear-key")
        self.cache.put(key, "fingerprint", value)
        clear_notion_analysis_preparation("7", "clear-key")
        # The production global cache is intentionally separate; exercise the
        # public clear contract with the same owned cache instance.
        with patch.object(content_module, "_PREPARATION_CACHE", self.cache):
            clear_notion_analysis_preparation("7", "clear-key")
        self.assertIsNone(self.cache.get(key, "fingerprint"))

        async def failed_read(*args):
            del args
            raise AdminDataError("NOTION_ANALYSIS_READ_FAILED", 502)

        with patch.object(content_module, "_PREPARATION_CACHE", self.cache), \
                patch.object(content_module, "_read_notion_analysis_input", failed_read), \
                patch.object(content_module, "_preparation_cache", return_value=self.cache):
            with self.assertRaises(AdminDataError):
                asyncio.run(freeze_notion_analysis_input(
                    SourceFacade("/tmp"), VERSION, CONNECTOR,
                    request_key="failed-key", request_fingerprint="failed-fingerprint",
                ))
        self.assertIsNone(self.cache.get(("7", "failed-key"), "failed-fingerprint"))

    def test_definite_oauth_rejection_keeps_complete_candidate_but_revalidates_before_reuse(self):
        facade = SourceFacade("/tmp")
        base = self.prepared()
        value = _PreparedNotionSource(
            content=base.content,
            context=facade._read_context(facade.connector),
            metadata=facade.snapshot["metadata"],
            credential_identity=1,
        )
        key = ("7", "renew-key")
        read = AsyncMock(return_value=value)
        original_cache = content_module._PREPARATION_CACHE
        content_module._PREPARATION_CACHE = self.cache
        try:
            facade._credential_identity = MagicMock(side_effect=[AdminDataError("ACCESS_TOKEN_REQUIRED", 401), 1, 2])
            with patch.object(content_module, "_read_notion_analysis_input", read):
                with self.assertRaises(AdminDataError):
                    asyncio.run(freeze_notion_analysis_input(
                        facade, VERSION, CONNECTOR,
                        request_key="renew-key", request_fingerprint="renew-fingerprint",
                    ))
                self.assertIs(self.cache.get(key, "renew-fingerprint"), value)
                result = asyncio.run(freeze_notion_analysis_input(
                    facade, VERSION, CONNECTOR,
                    request_key="renew-key", request_fingerprint="renew-fingerprint",
                ))
                self.assertIs(result, value.content)
                read.assert_awaited_once()
                with self.assertRaises(NotionSnapshotNotReadyError):
                    asyncio.run(freeze_notion_analysis_input(
                        facade, VERSION, CONNECTOR,
                        request_key="renew-key", request_fingerprint="renew-fingerprint",
                    ))
                self.assertIsNone(self.cache.get(key, "renew-fingerprint"))
        finally:
            content_module._PREPARATION_CACHE = original_cache


class ContentContractTest(unittest.TestCase):
    def test_source_and_diary_identity_contracts_stay_separate(self):
        raw = {"sections": ["echoes"], "input_snapshot": {"session_ids": [], "start_date": None, "end_date": None,
            "language": "en", "language_label": "English"}, "analysis_content": {"notion": None, "agent": None, "diary_session_ids": []}}
        self.assertEqual(ReflectionAnalysisCreateDTO.model_validate(raw).analysis_content.diary_session_ids, [])
        raw["analysis_content"]["diary_session_ids"] = ["session-other"]
        with self.assertRaises(ValidationError):
            ReflectionAnalysisCreateDTO.model_validate(raw)
        raw["analysis_content"]["agent"] = {"deck_id": "deck", "agent_id": "agent", "system_prompt": "browser override"}
        with self.assertRaises(ValidationError):
            ReflectionAnalysisCreateDTO.model_validate(raw)

    def test_missing_or_wrong_capability_fails_closed(self):
        client = MagicMock()
        client.capabilities_snapshot.return_value = SimpleNamespace(schema_capabilities=[CONTENT_SCHEMA],
            operations=[operation.capability for operation in ANALYSIS_CONTENT_OPERATIONS])
        require_analysis_content_capability(client, "request")
        client.capabilities_snapshot.return_value.schema_capabilities = []
        with self.assertRaises(AdminDataError):
            require_analysis_content_capability(client, "request")
        valid_operations = [operation.capability for operation in ANALYSIS_CONTENT_OPERATIONS]
        for schemas, operations in [
            ([CONTENT_SCHEMA, CONTENT_SCHEMA], valid_operations),
            ([CONTENT_SCHEMA], valid_operations + [valid_operations[0]]),
            ([CONTENT_SCHEMA.model_copy(update={"version": 2})], valid_operations),
            ([CONTENT_SCHEMA], [valid_operations[0].model_copy(update={"contract_sha256": "0" * 64}), *valid_operations[1:]]),
        ]:
            client.capabilities_snapshot.return_value = SimpleNamespace(schema_capabilities=schemas, operations=operations)
            with self.assertRaises(AdminDataError):
                require_analysis_content_capability(client, "request")

    def test_notion_only_results_cite_known_pages_and_do_not_become_session_ids(self):
        content = frozen_content()
        result = runtime.ReflectionsTaskEngine._validate_results([{ "title": "Pattern", "description": "Repeated concern",
            "related_session_ids": [], "related_notion_page_ids": [PAGE_ID], "evidence": "Monday and Friday", "confidence": "high" }], _snapshot(), content)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].related_session_ids, [])
        self.assertIn("Weekly notes", result[0].evidence)
        self.assertIn(content.notion.pages[0].content_sha256, result[0].evidence)
        with self.assertRaises(AdminDataError):
            runtime.ReflectionsTaskEngine._validate_results([{ "related_session_ids": ["session-a"], "related_notion_page_ids": ["other-page"] }], _snapshot(), content)
        with self.assertRaises(AdminDataError):
            runtime.ReflectionsTaskEngine._validate_results([{ "related_session_ids": ["session-a"], "related_notion_page_ids": [PAGE_ID] }], _snapshot())


class RealRunnerInputTest(unittest.IsolatedAsyncioTestCase):
    async def test_actual_runner_uses_server_selected_model_runtime_and_frozen_bodies(self):
        with tempfile.TemporaryDirectory(prefix="ink-reflection-runner-input-test-") as root:
            root = str(Path(root).resolve())
            load, content = _load(root), frozen_content()
            requests = []
            async def turn(request):
                requests.append(request)
                return NormalizedTurnResult(
                    outcome=NormalizedTurnOutcome.COMPLETED,
                    saw_message_final=True,
                    saw_finish=True,
                    finish_reason="stop",
                )
            worker = MagicMock()
            raw = [{"title": "Pattern", "description": "Repeated concern", "related_session_ids": ["session-a"],
                "related_notion_page_ids": [PAGE_ID], "evidence": "Quote", "confidence": "high"}]
            worker.transcript.return_value = ReflectionSectionTranscriptOutputDTO(section="echoes", messages=[ChatMessageDTO(
                id="message-fixture", role="assistant", parts=[{"type": "text", "text": json.dumps(raw)}],
                metadata=None, metadata_decode_error=False, created_at=None, history_final_text=None,
                history_process_available=False, history_projection_version=None)])
            model = selected_gateway_model()
            token = "idg_" + "a" * 43
            gateway_client = MagicMock()
            gateway = AdminGatewayRuntime(RuntimeGrant(
                token=token, purpose="gateway-cli", thread_id=_begin().thread_id,
                run_id=None, editor_session_id=None,
                scopes=("messages:create", "messages:count_tokens", "models:list"),
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
                maximum_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            ), gateway_client)
            catalog_calls = []
            class CatalogClient:
                def __init__(self, *, access_token):
                    catalog_calls.append(access_token)

                def fetch_catalog(self):
                    return GatewayModelCatalog((model,), model.model_alias)

            with (patch.dict(os.environ, {"AGENT_CWD": root}), patch.object(runtime, "AdminReflectionSectionPersistence") as owner,
                  patch.object(runtime, "_run_claude_agent_turn", turn),
                  patch.object(runtime, "GatewayModelCatalogClient", CatalogClient)):
                owner.return_value.resolve_actor_id.return_value = "7"
                owner.return_value.gateway_runtime.return_value = gateway
                owner.return_value.system_config.return_value = {"model": model.model_alias}
                result = await runtime.ClaudeAgentReflectionsRunner().run_section("echoes", load, _begin(),
                    client=MagicMock(), worker=worker, session_broker_settings=SessionProjectionBrokerSettings(timeout_seconds=1, max_bytes=1024),
                    runtime_http_config=_runtime_http_config(), analysis_content=content)
                self.assertEqual(result, raw)
                self.assertIn(BODY, requests[0].message_parts[0]["text"])
                self.assertIn(content.agent.system_prompt, requests[0].system_prompt)
                self.assertEqual(catalog_calls, [token])
                self.assertEqual(owner.return_value.system_config.call_args.kwargs,
                    {"actor_id": "7", "thread_id": _begin().thread_id})
                self.assertEqual(requests[0].model, model.model_alias)
                self.assertNotEqual(requests[0].model, content.agent.agent_id)
                self.assertEqual(requests[0].model_runtime_env, model.claude_code_runtime_env())
                self.assertIn("related_notion_page_ids", (Path(root) / _begin().thread_id / "memory/MEMORY_ANSWER_PROMPT.md").read_text())
                owner.return_value.close.assert_called_once()
            gateway_client.close.assert_called_once()
            self.assertNotIn(BODY, runtime.ClaudeAgentReflectionsRunner._build_user_message(_snapshot()))

    async def test_catalog_invalid_or_denied_closes_owner_before_turn(self):
        for code, status_code in (("GATEWAY_MODEL_CATALOG_INVALID", 502), ("GATEWAY_FORBIDDEN", 403)):
            with self.subTest(code=code), tempfile.TemporaryDirectory(prefix="ink-reflection-runner-catalog-failure-test-") as root:
                load, content = _load(str(Path(root).resolve())), frozen_content()
                owner = MagicMock()
                gateway = MagicMock()
                owner.return_value.resolve_actor_id.return_value = "7"
                owner.return_value.gateway_runtime.return_value = gateway
                worker = MagicMock()
                worker.transcript = MagicMock(side_effect=AssertionError("transcript must not be queried"))
                turn = AsyncMock()

                class FailingCatalogClient:
                    def __init__(self, *, access_token):
                        self.access_token = access_token

                    def fetch_catalog(self):
                        raise GatewayInferenceError(code, status_code)

                with patch.dict(os.environ, {"AGENT_CWD": str(Path(root).resolve())}), \
                        patch.object(runtime, "AdminReflectionSectionPersistence", owner), \
                        patch.object(runtime, "GatewayModelCatalogClient", FailingCatalogClient), \
                        patch.object(runtime, "_run_claude_agent_turn", turn):
                    with self.assertRaises(GatewayInferenceError) as captured:
                        await runtime.ClaudeAgentReflectionsRunner().run_section(
                            "echoes", load, _begin(), client=MagicMock(), worker=worker,
                            session_broker_settings=SessionProjectionBrokerSettings(timeout_seconds=1, max_bytes=1024),
                            runtime_http_config=_runtime_http_config(), analysis_content=content,
                        )
                self.assertEqual((captured.exception.code, captured.exception.status_code), (code, status_code))
                turn.assert_not_awaited()
                worker.transcript.assert_not_called()
                gateway.close.assert_called_once()
                owner.return_value.close.assert_called_once()

    def test_request_assembly_keeps_complete_default_contract_and_custom_effective_workflow(self):
        content = frozen_content()
        snapshot = _snapshot()
        default_prompts = runtime._effective_prompt_files(snapshot, "echoes")
        message = runtime.ClaudeAgentReflectionsRunner._build_user_message(
            snapshot, content, section="echoes"
        )
        self.assertIn(default_prompts["WORKFLOW.md"], message)
        self.assertIn(default_prompts["MEMORY_ANSWER_PROMPT.md"], message)
        self.assertIn("mcp__user__get_sessions_range", message)
        self.assertIn("current frontend UI language is English (`en`)", message)
        self.assertIn(BODY, message)
        self.assertIn("session-a", message)
        self.assertIn(PAGE_ID, message)
        self.assertIn("related_notion_page_ids", message)
        self.assertLess(message.index(default_prompts["WORKFLOW.md"]), message.index(default_prompts["MEMORY_ANSWER_PROMPT.md"]))

        custom_workflow = "# Effective custom workflow\nUse only the frozen session projection."
        custom_snapshot = snapshot.model_copy(update={
            "custom_prompts": [ReflectionPromptSnapshotDTO(
                section="echoes",
                prompt_files_json=json.dumps({"WORKFLOW.md": custom_workflow}),
            )],
        })
        custom_message = runtime.ClaudeAgentReflectionsRunner._build_user_message(
            custom_snapshot, content, section="echoes"
        )
        self.assertIn(custom_workflow, custom_message)
        self.assertNotIn(default_prompts["WORKFLOW.md"], custom_message)
        self.assertIn(default_prompts["MEMORY_ANSWER_PROMPT.md"], custom_message)
        for value in (BODY, "session-a", PAGE_ID, "related_notion_page_ids", "current frontend UI language is English (`en`)"):
            self.assertIn(value, custom_message)

    def test_notion_prompt_lists_all_frozen_pages_without_body_link_id_expansion(self):
        foreign_id = "123e4567-e89b-12d3-a456-426614174000"
        second_body = f"A second frozen note links to https://www.notion.so/{foreign_id}."
        second_page = ReflectionNotionPageDTO(
            page_id="page-analysis-second", title="Monthly notes", url="https://www.notion.so/monthly",
            markdown=second_body, content_sha256=hashlib.sha256(second_body.encode()).hexdigest(),
            read_at="2026-10-13T03:01:00Z",
        )
        content = frozen_content()
        content = content.model_copy(update={
            "notion": content.notion.model_copy(update={
                "empty_page_ids": ["empty-page-analysis"],
                "pages": [*content.notion.pages, second_page],
            }),
        })
        message = runtime.ClaudeAgentReflectionsRunner._build_user_message(
            _snapshot(), content, section="echoes"
        )
        citation_list = json.dumps([PAGE_ID, second_page.page_id], ensure_ascii=False)
        allowlist = "Allowed Notion citation page IDs for this task:\n" + citation_list
        self.assertIn(allowlist, message)
        self.assertNotIn("empty-page-analysis", allowlist)
        self.assertNotIn(foreign_id, allowlist)
        for page in content.notion.pages:
            for value in (page.page_id, page.title, page.url, page.markdown, page.content_sha256):
                self.assertIn(value, message)

        accepted = runtime.ReflectionsTaskEngine._validate_results([{
            "title": "Two sources", "description": "Both frozen pages support this.",
            "related_session_ids": [], "related_notion_page_ids": [PAGE_ID, second_page.page_id],
            "evidence": "Frozen evidence", "confidence": "high",
        }], _snapshot(), content)
        self.assertEqual(accepted[0].related_session_ids, [])
        self.assertIn("Weekly notes", accepted[0].evidence)
        self.assertIn("Monthly notes", accepted[0].evidence)
        for unsupported in ("empty-page-analysis", foreign_id):
            with self.subTest(unsupported=unsupported), self.assertRaisesRegex(
                AdminDataError, r"^REFLECTION_NOTION_REFERENCE_DENIED \(422\)$"
            ):
                runtime.ReflectionsTaskEngine._validate_results([{
                    "related_session_ids": [], "related_notion_page_ids": [unsupported],
                }], _snapshot(), content)

        no_notion_message = runtime.ClaudeAgentReflectionsRunner._build_user_message(
            _snapshot(), frozen_content(notion=False), section="echoes"
        )
        self.assertNotIn("<notion_analysis_context>", no_notion_message)
        self.assertNotIn("Allowed Notion citation page IDs for this task:", no_notion_message)

    async def test_non_completed_canonical_turn_closes_owners_before_transcript_parse(self):
        outcomes = (
            NormalizedTurnOutcome.FAILED,
            NormalizedTurnOutcome.CANCELLED,
            NormalizedTurnOutcome.INCOMPLETE,
        )
        for outcome in outcomes:
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory(prefix="ink-reflection-runner-failure-test-") as root:
                load, content = _load(str(Path(root).resolve())), frozen_content()
                owner = MagicMock()
                gateway = MagicMock()
                owner.return_value.resolve_actor_id.return_value = "7"
                owner.return_value.gateway_runtime.return_value = gateway
                worker = MagicMock()
                worker.transcript = MagicMock(side_effect=AssertionError("transcript must not be queried"))
                turn = AsyncMock(return_value=NormalizedTurnResult(
                    outcome=outcome,
                    saw_message_final=outcome is NormalizedTurnOutcome.COMPLETED,
                    saw_finish=outcome is not NormalizedTurnOutcome.INCOMPLETE,
                    finish_reason="error" if outcome is NormalizedTurnOutcome.FAILED else None,
                ))
                with patch.dict(os.environ, {"AGENT_CWD": str(Path(root).resolve())}), \
                        patch.object(runtime, "AdminReflectionSectionPersistence", owner), \
                        patch.object(runtime, "_run_claude_agent_turn", turn), \
                        patch.object(runtime, "resolve_platform_model", return_value=selected_gateway_model()):
                    with self.assertRaisesRegex(AdminDataError, r"^REFLECTION_AGENT_TURN_FAILED \(502\)$"):
                        await runtime.ClaudeAgentReflectionsRunner().run_section(
                            "echoes", load, _begin(), client=MagicMock(), worker=worker,
                            session_broker_settings=SessionProjectionBrokerSettings(timeout_seconds=1, max_bytes=1024),
                            runtime_http_config=_runtime_http_config(), analysis_content=content,
                        )
                owner.return_value.close.assert_called_once()
                gateway.close.assert_called_once()
                worker.transcript.assert_not_called()

    async def test_completed_turn_rejects_final_prose_instead_of_reusing_an_earlier_assistant_json(self):
        with tempfile.TemporaryDirectory(prefix="ink-reflection-runner-final-prose-test-") as root:
            root = str(Path(root).resolve())
            load, content = _load(root), frozen_content()
            raw = [{"title": "Draft", "description": "Earlier draft", "related_session_ids": [],
                "related_notion_page_ids": [PAGE_ID], "evidence": "Draft evidence", "confidence": "high"}]
            worker = MagicMock()
            worker.transcript.return_value = ReflectionSectionTranscriptOutputDTO(section="echoes", messages=[
                ChatMessageDTO(
                    id="message-draft", role="assistant",
                    parts=[{"type": "text", "text": json.dumps(raw)}],
                    metadata=None, metadata_decode_error=False, created_at=None, history_final_text=None,
                    history_process_available=False, history_projection_version=None),
                ChatMessageDTO(
                    id="message-final", role="assistant",
                    parts=[{"type": "text", "text": "Final analysis prose without a result array."}],
                    metadata=None, metadata_decode_error=False, created_at=None, history_final_text=None,
                    history_process_available=False, history_projection_version=None),
            ])
            owner = MagicMock()
            gateway = MagicMock()
            owner.return_value.resolve_actor_id.return_value = "7"
            owner.return_value.gateway_runtime.return_value = gateway
            turn = AsyncMock(return_value=NormalizedTurnResult(
                outcome=NormalizedTurnOutcome.COMPLETED, saw_message_final=True,
                saw_finish=True, finish_reason="stop"))
            with patch.dict(os.environ, {"AGENT_CWD": root}), \
                    patch.object(runtime, "AdminReflectionSectionPersistence", owner), \
                    patch.object(runtime, "_run_claude_agent_turn", turn), \
                    patch.object(runtime, "resolve_platform_model", return_value=selected_gateway_model()):
                with self.assertRaisesRegex(AdminDataError, r"^REFLECTION_ANALYSIS_OUTPUT_INVALID \(502\)$"):
                    await runtime.ClaudeAgentReflectionsRunner().run_section(
                        "echoes", load, _begin(), client=MagicMock(), worker=worker,
                        session_broker_settings=SessionProjectionBrokerSettings(timeout_seconds=1, max_bytes=1024),
                        runtime_http_config=_runtime_http_config(), analysis_content=content,
                    )
            worker.transcript.assert_called_once()
            gateway.close.assert_called_once()
            owner.return_value.close.assert_called_once()

    async def test_completed_turn_keeps_fenced_and_mixed_json_compatibility(self):
        with tempfile.TemporaryDirectory(prefix="ink-reflection-runner-json-compat-test-") as root:
            root = str(Path(root).resolve())
            load, content = _load(root), frozen_content()
            raw = [{"title": "Pattern", "description": "Repeated concern", "related_session_ids": [],
                "related_notion_page_ids": [PAGE_ID], "evidence": "Monday and Friday", "confidence": "high"}]
            worker = MagicMock()
            worker.transcript.return_value = ReflectionSectionTranscriptOutputDTO(section="echoes", messages=[ChatMessageDTO(
                id="message-final", role="assistant",
                parts=[{"type": "text", "text": "Final result follows:\n```json\n" + json.dumps(raw) +
                    "\n```\nNo additional result is intended."}],
                metadata=None, metadata_decode_error=False, created_at=None, history_final_text=None,
                history_process_available=False, history_projection_version=None)])
            owner = MagicMock()
            gateway = MagicMock()
            owner.return_value.resolve_actor_id.return_value = "7"
            owner.return_value.gateway_runtime.return_value = gateway
            turn = AsyncMock(return_value=NormalizedTurnResult(
                outcome=NormalizedTurnOutcome.COMPLETED, saw_message_final=True,
                saw_finish=True, finish_reason="stop"))
            with patch.dict(os.environ, {"AGENT_CWD": root}), \
                    patch.object(runtime, "AdminReflectionSectionPersistence", owner), \
                    patch.object(runtime, "_run_claude_agent_turn", turn), \
                    patch.object(runtime, "resolve_platform_model", return_value=selected_gateway_model()):
                result = await runtime.ClaudeAgentReflectionsRunner().run_section(
                    "echoes", load, _begin(), client=MagicMock(), worker=worker,
                    session_broker_settings=SessionProjectionBrokerSettings(timeout_seconds=1, max_bytes=1024),
                    runtime_http_config=_runtime_http_config(), analysis_content=content,
                )
            self.assertEqual(result, raw)
            gateway.close.assert_called_once()
            owner.return_value.close.assert_called_once()

    async def test_completed_turn_with_no_assistant_text_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="ink-reflection-runner-empty-text-test-") as root:
            root = str(Path(root).resolve())
            load, content = _load(root), frozen_content()
            worker = MagicMock()
            worker.transcript.return_value = ReflectionSectionTranscriptOutputDTO(section="echoes", messages=[ChatMessageDTO(
                id="message-fixture", role="assistant", parts=[], metadata=None,
                metadata_decode_error=False, created_at=None, history_final_text=None,
                history_process_available=False, history_projection_version=None)])
            owner = MagicMock()
            gateway = MagicMock()
            owner.return_value.resolve_actor_id.return_value = "7"
            owner.return_value.gateway_runtime.return_value = gateway
            turn = AsyncMock(return_value=NormalizedTurnResult(
                outcome=NormalizedTurnOutcome.COMPLETED, saw_message_final=True,
                saw_finish=True, finish_reason="stop"))
            with patch.dict(os.environ, {"AGENT_CWD": root}), \
                    patch.object(runtime, "AdminReflectionSectionPersistence", owner), \
                    patch.object(runtime, "_run_claude_agent_turn", turn), \
                    patch.object(runtime, "resolve_platform_model", return_value=selected_gateway_model()):
                with self.assertRaisesRegex(AdminDataError, r"^REFLECTION_ANALYSIS_OUTPUT_INVALID \(502\)$"):
                    await runtime.ClaudeAgentReflectionsRunner().run_section(
                        "echoes", load, _begin(), client=MagicMock(), worker=worker,
                        session_broker_settings=SessionProjectionBrokerSettings(timeout_seconds=1, max_bytes=1024),
                        runtime_http_config=_runtime_http_config(), analysis_content=content,
                    )
            worker.transcript.assert_called_once()
            gateway.close.assert_called_once()
            owner.return_value.close.assert_called_once()

    async def test_completed_turn_accepts_explicit_empty_array_without_changing_output_contract(self):
        with tempfile.TemporaryDirectory(prefix="ink-reflection-runner-empty-array-test-") as root:
            root = str(Path(root).resolve())
            load, content = _load(root), frozen_content()
            worker = MagicMock()
            worker.transcript.return_value = ReflectionSectionTranscriptOutputDTO(section="echoes", messages=[ChatMessageDTO(
                id="message-fixture", role="assistant", parts=[{"type": "text", "text": "[]"}],
                metadata=None, metadata_decode_error=False, created_at=None, history_final_text=None,
                history_process_available=False, history_projection_version=None)])
            owner = MagicMock()
            gateway = MagicMock()
            owner.return_value.resolve_actor_id.return_value = "7"
            owner.return_value.gateway_runtime.return_value = gateway
            turn = AsyncMock(return_value=NormalizedTurnResult(
                outcome=NormalizedTurnOutcome.COMPLETED, saw_message_final=True,
                saw_finish=True, finish_reason="stop"))
            with patch.dict(os.environ, {"AGENT_CWD": root}), \
                    patch.object(runtime, "AdminReflectionSectionPersistence", owner), \
                    patch.object(runtime, "_run_claude_agent_turn", turn), \
                    patch.object(runtime, "resolve_platform_model", return_value=selected_gateway_model()):
                result = await runtime.ClaudeAgentReflectionsRunner().run_section(
                    "echoes", load, _begin(), client=MagicMock(), worker=worker,
                    session_broker_settings=SessionProjectionBrokerSettings(timeout_seconds=1, max_bytes=1024),
                    runtime_http_config=_runtime_http_config(), analysis_content=content,
                )
            self.assertEqual(result, [])
            gateway.close.assert_called_once()
            owner.return_value.close.assert_called_once()


class RouterInputTest(unittest.TestCase):
    def test_public_dto_rejects_runtime_prompt_and_path_override(self):
        app = FastAPI(); app.include_router(routes.router)
        app.dependency_overrides[routes.get_current_user] = lambda: {"user_id": 7}
        app.dependency_overrides[routes.get_admin_request_auth] = lambda: _RouteOwner(_AppendWorker())
        with TestClient(app) as client:
            for extra in ({"system_prompt": "override"}, {"notion_home": "/tmp/elsewhere"}):
                response = client.post("/api/reflections/tasks", json={"analysis_content": {"include_notion": True, **extra}})
                self.assertEqual(response.status_code, 422)

    def test_default_public_create_does_not_read_notion_or_require_new_capability(self):
        async def case():
            owner = _RouteOwner(_AppendWorker())
            with (tempfile.TemporaryDirectory() as root, patch.object(routes, "invoke_admin_operation", AsyncMock(return_value=ReflectionTaskGetOutputDTO(task=_task(root), results=[]))),
                  patch.object(content_module, "NotionOperationClient", side_effect=AssertionError("Notion must be excluded")),
                  patch.object(routes, "require_scope_capability", side_effect=AssertionError("legacy capability only"))):
                response = await routes.create_reflections_task_endpoint(routes.ReflectionsTaskCreateRequest(auto_start=False), current_user={"user_id": "7"}, owner=owner)
                self.assertEqual(response.status_code, 202)
        asyncio.run(case())

    def test_missing_scope_capability_is_a_definite_rejection_before_any_task_write(self):
        async def case():
            from fastapi import HTTPException
            owner = _RouteOwner(_AppendWorker())
            with (patch.object(routes, "require_scope_capability", side_effect=AdminDataError("ADMIN_CAPABILITY_UNAVAILABLE", 503)),
                  patch.object(routes, "invoke_admin_operation", AsyncMock(side_effect=AssertionError("No task write is allowed"))) as write):
                with self.assertRaises(HTTPException) as failure:
                    await routes.create_reflections_task_endpoint(routes.ReflectionsTaskCreateRequest(auto_start=False,
                        analysis_content=routes.ReflectionsAnalysisContentRequest(include_notion=True, connector_id=CONNECTOR, snapshot_version=VERSION)), current_user={}, owner=owner)
                self.assertEqual(failure.exception.status_code, 503)
                self.assertEqual(failure.exception.detail, {"error_code": "ADMIN_CAPABILITY_UNAVAILABLE", "outcome_unknown": False})
                write.assert_not_awaited()
        asyncio.run(case())

    def test_committed_creation_response_recovery_never_reads_new_notion_bodies(self):
        async def case():
            with tempfile.TemporaryDirectory() as root:
                task = _task(root).model_copy(update={"agent_contract_version": ANALYSIS_CONTENT_CONTRACT_VERSION})
                created = ReflectionTaskGetOutputDTO(task=task, results=[])
                key = "reflection-create-recover-once"
                owner = _RouteOwner(_AppendWorker())
                owner.client = MagicMock()
                owner.client.receipt.return_value = CommittedReceiptDTO[ReflectionTaskGetOutputDTO](status="committed",
                    operation="reflection-task.create-with-content", request_id=key, result=created)
                content = frozen_content(diary=["session-a"])
                public = ReflectionAnalysisSummaryDTO(diary_session_ids=content.diary_session_ids,
                    notion={**content.notion.model_dump(exclude={"pages", "empty_page_ids"}), "empty_page_count": 0,
                        "pages": [page.model_dump(exclude={"markdown"}) for page in content.notion.pages]},
                    agent=content.agent.model_dump(exclude={"system_prompt"}))
                actor = AdminRequestActor("fixture-subject", "7", "fixture-browser", frozenset({"dream:read", "dream:write"}), 1, 9999999999, "fixture-access")
                body = routes.ReflectionsTaskCreateRequest(auto_start=False, request_key=key, sections=["echoes"], language="en", session_ids=["session-a"],
                    analysis_content=routes.ReflectionsAnalysisContentRequest(include_notion=True, connector_id=CONNECTOR,
                        snapshot_version=VERSION, deck_id="deck-analysis", agent_id="agent-analysis"))
                with (patch.object(routes, "require_scope_capability"),
                      patch.object(routes, "invoke_admin_operation", AsyncMock(return_value=ReflectionAnalysisSummaryOutputDTO(analysis_content=public))) as invoke,
                      patch.object(routes, "prepare_reflection_event_bus", AsyncMock()),
                      patch.object(content_module, "NotionOperationClient", side_effect=AssertionError("Original receipt must avoid re-reading")) as read):
                    response = await routes.create_reflections_task_endpoint(body, current_user=actor.current_user_projection(), owner=owner)
                    self.assertEqual(response.status_code, 202)
                    self.assertEqual(json.loads(response.body)["task_id"], task.task_id)
                    read.assert_not_called()
                    self.assertTrue(all(call.args[1].__name__ == "summary" for call in invoke.call_args_list))
        asyncio.run(case())

    def test_public_report_retry_only_ensures_the_owned_terminal_task(self):
        async def case():
            with tempfile.TemporaryDirectory() as root:
                owner = _RouteOwner(MagicMock())
                owner.data.start = MagicMock()
                owner.worker.ensure_report.return_value = ReflectionReportEnsureOutputDTO(report_id="42", report_type="full_analysis", created=False)
                with (patch.object(routes, "invoke_admin_operation", AsyncMock(return_value=ReflectionTaskStartOutputDTO(task=_task(root, status="COMPLETED"), terminal=True, report_missing=True))) as owned,
                      patch.object(routes, "_start_worker", AsyncMock(side_effect=AssertionError("A save retry must not rerun the model"))) as model):
                    result = await routes.ensure_reflections_report_endpoint(TASK_ID, current_user={}, owner=owner)
                    self.assertEqual(result["report_id"], "42")
                    owned.assert_awaited_once(); owner.worker.ensure_report.assert_called_once(); model.assert_not_awaited()
        asyncio.run(case())

    def tearDown(self):
        runtime._BUSES.clear(); runtime._TASK_LOCKS.clear(); runtime._RUNNING_TASKS.clear()


class EngineInputJourneyTest(unittest.IsolatedAsyncioTestCase):
    async def test_content_load_execution_events_results_and_terminal_report_retry_use_same_task(self):
        with tempfile.TemporaryDirectory(prefix="ink-reflection-engine-content-test-") as root:
            root = str(Path(root).resolve())
            load = _load(root)
            load = load.model_copy(update={"task": load.task.model_copy(update={"agent_contract_version": ANALYSIS_CONTENT_CONTRACT_VERSION})})
            content = frozen_content()
            worker = MagicMock()
            worker.advance.side_effect = [ReflectionTaskAdvanceOutputDTO(status=status, revision=revision)
                for status, revision in [("QUEUED", 3), ("RUNNING", 4), ("COMPLETED", 5)]]
            worker.begin.return_value = _begin()
            worker.finish.return_value = ReflectionSectionFinishOutputDTO(section="echoes", status="COMPLETED", result_count=1, revision=3)
            worker.ensure_report.side_effect = [AdminDataError("ADMIN_UNAVAILABLE", 503), object()]
            runner = MagicMock()
            runner.run_section = AsyncMock(return_value=[{"title": "Repeated worry", "description": "Same concern",
                "related_session_ids": [], "related_notion_page_ids": [PAGE_ID], "evidence": "Monday and Friday", "confidence": "high"}])
            engine = runtime.ReflectionsTaskEngine(worker, MagicMock(), SessionProjectionBrokerSettings(timeout_seconds=1, max_bytes=1024),
                _runtime_http_config(), runner=runner)
            with patch.dict(os.environ, {"AGENT_CWD": root}), patch.object(AdminReflectionAnalysisContentData, "load", return_value=ReflectionAnalysisLoadOutputDTO(analysis_content=content)) as source:
                await engine.run(TASK_ID, load=load)
                source.assert_called_once()
                runner.run_section.assert_awaited_once()
                self.assertEqual(runner.run_section.call_args.kwargs["analysis_content"], content)
                result = worker.finish.call_args.args[0].results[0]
                self.assertEqual(result.related_session_ids, [])
                self.assertIn("Weekly notes", result.evidence)
                self.assertEqual([call.args[0].event_type for call in worker.append_event.call_args_list], [
                    "reflection.task.created", "reflection.context.ready", "reflection.task.started", "reflection.section.started", "reflection.section.completed"])
                terminal = _load(root, status="COMPLETED")
                terminal = terminal.model_copy(update={"task": terminal.task.model_copy(update={"agent_contract_version": ANALYSIS_CONTENT_CONTRACT_VERSION})})
                await engine.run(TASK_ID, load=terminal)
                self.assertEqual(worker.ensure_report.call_count, 2)
                self.assertEqual(runner.run_section.await_count, 1)
                self.assertEqual(source.call_count, 1)

    async def test_no_diary_or_notion_text_stops_before_runner(self):
        with tempfile.TemporaryDirectory(prefix="ink-reflection-empty-input-test-") as root:
            load = _load(str(Path(root).resolve()))
            load = load.model_copy(update={"launch_snapshot": load.launch_snapshot.model_copy(update={"sessions": [load.launch_snapshot.sessions[0].model_copy(update={"text": ""})]})})
            worker, runner = MagicMock(), MagicMock()
            worker.advance.return_value = ReflectionTaskAdvanceOutputDTO(status="FAILED", revision=3)
            runner.run_section = AsyncMock()
            engine = runtime.ReflectionsTaskEngine(worker, MagicMock(), SessionProjectionBrokerSettings(timeout_seconds=1, max_bytes=1024),
                _runtime_http_config(), runner=runner)
            await engine.run(TASK_ID, load=load)
            runner.run_section.assert_not_awaited()
            self.assertEqual(worker.advance.call_args.args[0].action, "fatal-fail")

    async def asyncTearDown(self):
        runtime._BUSES.clear(); runtime._TASK_LOCKS.clear(); runtime._RUNNING_TASKS.clear()
