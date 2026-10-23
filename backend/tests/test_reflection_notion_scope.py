# [Input] Production Reflections v2 client, creation route and task-owned Notion Read adapter.
# [Output] Provider-free registration, lazy reads, evidence recovery and authority regression evidence.
# [Pos] Technical contracts using isolated temporary workspaces and injected Admin/Notion boundaries.
# [Sync] 2026-10-23: cover create 503 registration and on-demand source evidence without real accounts or models.
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from libs.claude_agent_kit.server.notion_read_hook import apply_notion_page_read_redirect
from notion.operations import OperationResult
from services.admin_data.config import AdminDataConfig
from services.admin_data.errors import AdminDataError
from services.admin_data.reflection_notion_runtime import ReflectionNotionRuntime
from services.admin_data.reflection_notion_scope_data import (
    CONTENT_SCHEMA, LOAD_SCOPE, SCOPE_OPERATIONS, SCOPE_CONTRACT_VERSION,
    AdminReflectionNotionScopeData, ReflectionNotionReadDTO, ReflectionNotionReadOutputDTO,
    ReflectionScopeSnapshotDTO, ReflectionScopeCreateDTO, ReflectionScopeSelectionDTO,
    ReflectionNotionScopeSelectionDTO, require_scope_capability,
)
from services.admin_data.reflection_task_models import ReflectionTaskLookupDTO
from services.admin_data.request_auth import create_production_admin_request_auth
from tests.test_reflections_agent import TASK_ID, _snapshot, _task, _RouteOwner
import routers.reflections as routes

CONNECTOR = "11111111-1111-4111-8111-111111111111"
PAGE = "fixture-page"
BODY = "I practised summarising my learning twice this week."


@pytest.fixture(autouse=True)
def isolated_notion_credentials(tmp_path):
    with patch("services.admin_data.reflection_notion_runtime.NotionCredentialStore") as credentials:
        credentials.return_value.effective_home.return_value = tmp_path / "synthetic-notion-home"
        yield


def content():
    identity = dict(snapshot_version="fixture-v2", source_revision="source-1", sync_cursor="cursor-1",
                    workspace_id="workspace-1", resource_connector_id=CONNECTOR)
    return ReflectionScopeSnapshotDTO.model_validate({
        "diary_session_ids": [], "agent": None,
        "notion": {"connector_id": CONNECTOR, "snapshot_version": "fixture-v2", "pages": [], "empty_page_ids": [],
            "snapshot": {"metadata": {**identity, "fetched_at": "2026-10-23T00:00:00Z", "state": "snapshot_ready"},
                "identity": identity,
                "connector": {"id": CONNECTOR, "name": "Learning", "platform": "notion", "auth_status": "authenticated",
                    "last_synced_at": None, "selected_pages": [PAGE], "selected_databases": []},
                "index": [{"page_id": PAGE, "title": "Learning diary", "url": "https://www.notion.so/fixture-page",
                    "last_edited": "", "created_time": None, "last_edited_time": None}],
                "databases": [], "database_pages": {}, "pages": {}}}})


def page(markdown=BODY):
    return ReflectionNotionReadDTO(page_id=PAGE, title="Learning diary", url="https://www.notion.so/fixture-page",
        markdown=markdown, content_sha256=hashlib.sha256(markdown.encode()).hexdigest(), read_at="2026-10-23T00:00:01Z")


def runtime(value=None):
    authorize = MagicMock()
    host = ReflectionNotionRuntime(value or content(), actor_id="7001", task_id=TASK_ID,
        begin=SimpleNamespace(section="echoes", thread_id="fixture-thread", revision=2), client=MagicMock(), authorize=authorize)
    host.data = MagicMock()
    host.data.read_context.return_value = ReflectionNotionReadOutputDTO(page=None)
    host.data.record.side_effect = lambda value, request_id: ReflectionNotionReadOutputDTO(page=value.page)
    return host, authorize


def config():
    return AdminDataConfig(base_url="https://admin.example", issuer="https://admin.example/api/auth",
        resource="https://dream.example/api", service_secret="synthetic-service-" + "x" * 32, service_client_id="dream-fixture")


def test_production_client_registers_and_dispatches_all_scope_operations():
    cfg = config()
    owner = create_production_admin_request_auth(cfg)
    calls = []
    def handler(request):
        calls.append(request)
        if request.url.path.endswith("/capabilities"):
            value = {"version": "1", "auth": {"issuer": cfg.issuer, "jwks_uri": cfg.jwks_uri, "algorithm": "ES256",
                "resource": cfg.resource, "clients": {"browser": "browser", "device": "device"},
                "scopes": ["dream:read", "dream:write"], "delegations": []},
                "schema_capabilities": [CONTENT_SCHEMA.model_dump()], "operations": [op.capability.model_dump() for op in SCOPE_OPERATIONS]}
        else:
            assert request.url.path.endswith("/operations/" + LOAD_SCOPE.capability.name)
            assert json.loads(request.content)["input"] == {"task_id": TASK_ID}
            assert request.headers["authorization"] == "Bearer fixture.service.access.token"
            assert "x-ink-dream-service-authorization" not in request.headers
            value = {"analysis_content": content().model_dump(mode="json")}
        return httpx.Response(200, json={"request_id": request.headers["x-request-id"], "data": value})
    owner.client._http.close()
    owner.client._http = httpx.Client(transport=httpx.MockTransport(handler))
    try:
        require_scope_capability(owner.client, "fixture-catalog")
        assert owner.client.supports(SCOPE_OPERATIONS, (CONTENT_SCHEMA,))
        loaded = AdminReflectionNotionScopeData(owner.client).load(ReflectionTaskLookupDTO(task_id=TASK_ID), "fixture-load")
        assert loaded.analysis_content.notion.pages == []
        assert len(calls) == 2
    finally:
        owner.client.close()


@pytest.mark.parametrize("missing", SCOPE_OPERATIONS, ids=lambda op: op.capability.name)
def test_scope_requires_every_exact_operation_before_any_dispatch(missing):
    client = MagicMock()
    client.capabilities_snapshot.return_value = SimpleNamespace(schema_capabilities=[CONTENT_SCHEMA],
        operations=[op.capability for op in SCOPE_OPERATIONS if op is not missing])
    with pytest.raises(AdminDataError, match="ADMIN_CAPABILITY_UNAVAILABLE"):
        require_scope_capability(client, "fixture-catalog")
    client.execute.assert_not_called()


@pytest.mark.asyncio
async def test_create_only_submits_scope_then_keeps_original_start_boundary(tmp_path):
    owner = _RouteOwner(MagicMock())
    task = _task(str(tmp_path)).model_copy(update={"agent_contract_version": SCOPE_CONTRACT_VERSION})
    created = SimpleNamespace(task=task)
    async def invoke(user, operation, value, **kwargs):
        assert operation.__name__ == "create"
        assert type(value) is ReflectionScopeCreateDTO
        assert value.analysis_content.notion.model_dump() == {"connector_id": CONNECTOR, "snapshot_version": "fixture-v2"}
        assert "markdown" not in json.dumps(value.model_dump())
        return created
    with (patch.object(routes, "require_scope_capability"),
          patch.object(routes, "invoke_admin_operation", AsyncMock(side_effect=invoke)),
          patch.object(routes, "prepare_reflection_event_bus", AsyncMock()) as bus,
          patch.object(routes, "_content_task_response", AsyncMock(return_value={"task_id": task.task_id})),
          patch("services.admin_data.reflection_analysis_content.NotionOperationClient") as remote):
        response = await routes.create_reflections_task_endpoint(routes.ReflectionsTaskCreateRequest(auto_start=False,
            session_ids=[], analysis_content=routes.ReflectionsAnalysisContentRequest(include_notion=True,
                connector_id=CONNECTOR, snapshot_version="fixture-v2")), current_user={}, owner=owner)
        assert response.status_code == 202
        remote.assert_not_called()
        bus.assert_awaited_once()


@pytest.mark.asyncio
async def test_first_read_is_persisted_before_return_and_has_section_authority():
    host, authorize = runtime()
    with patch("services.admin_data.reflection_notion_runtime.NotionOperationClient") as remote:
        remote.return_value.get_page_markdown = AsyncMock(return_value=OperationResult(success=True, data={"markdown": BODY}))
        result = await host.read_page(PAGE)
    assert result["markdown"] == BODY
    assert result["content_sha256"] == page().content_sha256
    assert host.read_page_ids == {PAGE} and host.content.notion.pages[0].markdown == BODY
    binding = host.data.record.call_args.args[0]
    assert (binding.section, binding.thread_id, binding.section_revision) == ("echoes", "fixture-thread", 2)
    assert authorize.call_count == 3
    remote.return_value.get_page_markdown.assert_awaited_once_with(PAGE)


@pytest.mark.asyncio
async def test_later_section_reads_original_evidence_without_remote_fetch():
    host, authorize = runtime()
    host.begin.section = "traits"
    host.data.read_context.return_value = ReflectionNotionReadOutputDTO(page=page())
    with patch("services.admin_data.reflection_notion_runtime.NotionOperationClient") as remote:
        assert (await host.read_page(PAGE))["markdown"] == BODY
    remote.assert_not_called()
    host.data.record.assert_not_called()
    assert host.read_page_ids == {PAGE} and authorize.call_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("confirmed", [True, False])
async def test_unknown_evidence_write_reads_back_without_replaying_post(confirmed):
    host, _ = runtime()
    host.data.read_context.side_effect = [ReflectionNotionReadOutputDTO(page=None), ReflectionNotionReadOutputDTO(page=page() if confirmed else None)]
    host.data.record.side_effect = AdminDataError("ADMIN_UNAVAILABLE", 503, outcome_unknown=True)
    with patch("services.admin_data.reflection_notion_runtime.NotionOperationClient") as remote:
        remote.return_value.get_page_markdown = AsyncMock(return_value=OperationResult(success=True, data={"markdown": BODY}))
        if confirmed:
            assert (await host.read_page(PAGE))["ok"]
        else:
            with pytest.raises(AdminDataError, match="REFLECTION_NOTION_EVIDENCE_UNCONFIRMED"):
                await host.read_page(PAGE)
            assert host.read_page_ids == set()
    assert host.data.read_context.call_count == 2
    host.data.record.assert_called_once()


@pytest.mark.asyncio
async def test_failed_provider_read_keeps_evidence_empty_and_retry_reads_again():
    host, _ = runtime()
    with patch("services.admin_data.reflection_notion_runtime.NotionOperationClient") as remote:
        remote.return_value.get_page_markdown = AsyncMock(side_effect=[OperationResult(success=False, error="fixture unavailable"), OperationResult(success=True, data={"markdown": BODY})])
        with pytest.raises(AdminDataError, match="NOTION_ANALYSIS_READ_FAILED"):
            await host.read_page(PAGE)
        assert not host.read_page_ids and not host.content.notion.pages
        host.data.record.assert_not_called()
        assert (await host.read_page(PAGE))["ok"]


@pytest.mark.asyncio
async def test_scope_and_revoked_authority_stop_before_evidence_or_citations():
    host, authorize = runtime()
    with patch("services.admin_data.reflection_notion_runtime.NotionOperationClient") as remote:
        with pytest.raises(AdminDataError, match="REFLECTION_NOTION_REFERENCE_DENIED"):
            await host.read_page("outside-page")
        host.data.read_context.assert_not_called()
        remote.assert_not_called()
        authorize.side_effect = [None, AdminDataError("RUNTIME_DELEGATION_REVOKED", 403)]
        remote.return_value.get_page_markdown = AsyncMock(return_value=OperationResult(success=True, data={"markdown": BODY}))
        with pytest.raises(AdminDataError, match="RUNTIME_DELEGATION_REVOKED"):
            await host.read_page(PAGE)
    host.data.record.assert_not_called()
    assert not host.read_page_ids


@pytest.mark.asyncio
async def test_corrupt_cached_body_never_returns_or_becomes_a_citation():
    host, _ = runtime()
    host.data.read_context.return_value = ReflectionNotionReadOutputDTO(page=page().model_copy(update={"markdown": "changed"}))
    with pytest.raises(AdminDataError, match="ADMIN_RESPONSE_INVALID"):
        await host.read_page(PAGE)
    assert not host.read_page_ids and not host.content.notion.pages


@pytest.mark.asyncio
async def test_empty_read_is_recorded_and_excluded_from_insight_references():
    from reflections_agent import ReflectionsTaskEngine
    host, _ = runtime()
    host.data.read_context.return_value = ReflectionNotionReadOutputDTO(page=page(""))
    assert (await host.read_page(PAGE))["markdown"] == ""
    assert host.content.notion.pages[0].content_sha256 == hashlib.sha256(b"").hexdigest()
    assert ReflectionsTaskEngine._validate_results([], _snapshot(), host.content) == []
    with pytest.raises(AdminDataError, match="REFLECTION_NOTION_REFERENCE_DENIED"):
        ReflectionsTaskEngine._validate_results([{"related_session_ids": [], "related_notion_page_ids": [PAGE]}], _snapshot(), host.content)


@pytest.mark.asyncio
async def test_existing_read_hook_uses_host_without_projected_credentials(tmp_path):
    notion = tmp_path / ".notion"
    (notion / "pages").mkdir(parents=True)
    (notion / "index.json").write_text(json.dumps({"pages": [{"page_id": PAGE}]}))
    (notion / "snapshot.json").write_text("{}")
    read = AsyncMock(return_value={"ok": True, **page().model_dump()})
    paths = []
    result = await apply_notion_page_read_redirect("Read", {"file_path": f".notion/pages/{PAGE}.json"},
        workspace_path=str(tmp_path), credential_home=None, tmp_workspace=str(tmp_path), tmp_paths=paths, page_reader=read)
    redirect = result["hookSpecificOutput"]["updatedInput"]["file_path"]
    assert json.loads(Path(redirect).read_text())["markdown"] == BODY
    read.assert_awaited_once_with(PAGE)
    assert Path(redirect).is_relative_to(tmp_path / ".claude-tmp")


def test_v2_prompt_contains_only_index_and_requires_successful_reads():
    from reflections_agent import ClaudeAgentReflectionsRunner
    message = ClaudeAgentReflectionsRunner._build_user_message(_snapshot(), content(), section="echoes")
    assert ".notion/index.json" in message and BODY not in message
    assert "read" in message.lower() and "related_notion_page_ids" in message


@pytest.mark.asyncio
@pytest.mark.parametrize("read_in_section", [True, False])
async def test_actual_section_runner_requires_current_section_read_before_citing(tmp_path, monkeypatch, read_in_section):
    import reflections_agent as engine
    from services.admin_data.chat_models import ChatMessageDTO
    from services.admin_data.reflection_task_models import ReflectionSectionTranscriptOutputDTO
    from services.admin_data.session_projection_broker import SessionProjectionBrokerSettings
    from services.story_workspace.dream_lifecycle_observer import NormalizedTurnOutcome, NormalizedTurnResult
    from tests.test_reflection_analysis_content import selected_gateway_model
    from tests.test_reflections_agent import _load, _begin, _runtime_http_config
    monkeypatch.setenv("AGENT_CWD", str(tmp_path))
    worker = MagicMock()
    raw = [{"title": "Learning pattern", "description": "Repeated practice", "related_session_ids": [],
        "related_notion_page_ids": [PAGE], "evidence": "Repeated practice", "confidence": "high"}]
    worker.transcript.return_value = ReflectionSectionTranscriptOutputDTO(section="echoes", messages=[ChatMessageDTO(
        id="fixture-message", role="assistant", parts=[{"type": "text", "text": json.dumps(raw)}], metadata=None,
        metadata_decode_error=False, created_at=None, history_final_text=None, history_process_available=False, history_projection_version=None)])
    with (patch.object(engine, "AdminReflectionSectionPersistence") as owner,
          patch.object(engine, "resolve_platform_model", return_value=selected_gateway_model()),
          patch("services.admin_data.reflection_notion_runtime.NotionOperationClient") as remote,
          patch.object(AdminReflectionNotionScopeData, "read_context", return_value=ReflectionNotionReadOutputDTO(page=None)),
          patch.object(AdminReflectionNotionScopeData, "record", side_effect=lambda value, request_id: ReflectionNotionReadOutputDTO(page=value.page))):
        owner.return_value.resolve_actor_id.return_value = "7001"
        owner.return_value.system_config.return_value = {"workspace_enabled": True}
        remote.return_value.get_page_markdown = AsyncMock(return_value=OperationResult(success=True, data={"markdown": BODY}))
        async def turn(request):
            host = owner.return_value.bind_notion_runtime.call_args.args[0]
            assert BODY not in request.message_parts[0]["text"]
            if read_in_section:
                await host.read_page(PAGE)
            return NormalizedTurnResult(outcome=NormalizedTurnOutcome.COMPLETED, saw_message_final=True, saw_finish=True, finish_reason="stop")
        with patch.object(engine, "_run_claude_agent_turn", turn):
            execute = engine.ClaudeAgentReflectionsRunner().run_section("echoes", _load(str(tmp_path)), _begin(),
                client=MagicMock(), worker=worker, session_broker_settings=SessionProjectionBrokerSettings(timeout_seconds=1,max_bytes=1024),
                runtime_http_config=_runtime_http_config(), analysis_content=content())
            if read_in_section:
                result = await execute
                assert result == raw
                evidence = engine.ReflectionsTaskEngine._validate_results(result, _snapshot(), owner.return_value.bind_notion_runtime.call_args.args[0].content)
                assert page().content_sha256 in evidence[0].evidence
            else:
                with pytest.raises(AdminDataError, match="REFLECTION_NOTION_REFERENCE_DENIED"):
                    await execute
        owner.return_value.close.assert_called_once()
