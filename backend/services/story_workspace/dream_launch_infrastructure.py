# [Input] Authenticated Admin actor/client, launch command and request-scoped Runtime port.
# [Output] Admin-owned source/Preflight/Run/dispatch persistence plus Dream-owned Agent turn execution.
# [Pos] Dream launch composition; contains no PostgreSQL client, SQL, ORM, DDL or database fallback.
# [Sync] 2026-09-16: replace every production launch persistence path with strict Admin DTO operations.
"""Production Dream launch orchestration over Admin business operations."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import partial
import inspect
import json
import logging
import re
from typing import Any, Callable, Mapping, Protocol
from uuid import uuid4

try:
    from services.admin_data.client import AdminDataClient
    from services.admin_data.deck_detail_data import AdminDeckDetailData
    from services.admin_data.deck_version_models import DeckIdInputDTO
    from services.admin_data.errors import AdminDataError
    from services.admin_data.launch_metadata_data import (
        AdminLaunchMetadataData,
        AdminLaunchSourceRepository,
        CLAIM_LAUNCH,
        FAIL_LAUNCH_ENVELOPE,
        FINISH_LAUNCH,
        LOOKUP_LAUNCH_REPLAY,
        LaunchClaimInputDTO,
        LaunchFailureExpectation,
        LaunchFailureInputDTO,
        LaunchFinishInputDTO,
        LaunchSourceInputDTO,
    )
    from services.admin_data.preflight_data import AdminPreflightData, PreflightExecutionInputDTO, PreflightInputDTO
    from services.admin_data.request_auth import AdminRequestActor
    from services.admin_data.run_data import (
        AdminRunData,
        CREATE_RUN,
        FAIL_RUN,
        RunCreateInputDTO,
        RunFailInputDTO,
        RunLookupInputDTO,
    )
    from services.admin_gateway import GatewayInferenceError, resolve_platform_model_alias
    from services.story_workspace.canonical_project_instruction import (
        STORY_WORKSPACE_CANONICAL_PROJECT_INSTRUCTION,
        story_workspace_canonical_project_fallback_slug,
    )
    from services.story_workspace.dream_launch_application_service import (
        DreamLaunchApplicationService,
        DreamLaunchIdempotencyConflict,
        DreamLaunchSource,
    )
    from services.story_workspace.dream_launch_runtime import DreamLaunchRuntimeError, PreparedDreamLaunchBinding
    from services.story_workspace.dream_lifecycle_observer import NormalizedTurnOutcome, drain_chat_agent_turn
    from story_workspace.contracts import StoryWorkspaceDreamLaunchCommand, StoryWorkspaceDreamRunContext
except ModuleNotFoundError:  # Support package imports from repository root.
    from backend.services.admin_data.client import AdminDataClient
    from backend.services.admin_data.deck_detail_data import AdminDeckDetailData
    from backend.services.admin_data.deck_version_models import DeckIdInputDTO
    from backend.services.admin_data.errors import AdminDataError
    from backend.services.admin_data.launch_metadata_data import (
        AdminLaunchMetadataData,
        AdminLaunchSourceRepository,
        CLAIM_LAUNCH,
        FAIL_LAUNCH_ENVELOPE,
        FINISH_LAUNCH,
        LOOKUP_LAUNCH_REPLAY,
        LaunchClaimInputDTO,
        LaunchFailureExpectation,
        LaunchFailureInputDTO,
        LaunchFinishInputDTO,
        LaunchSourceInputDTO,
    )
    from backend.services.admin_data.preflight_data import AdminPreflightData, PreflightExecutionInputDTO, PreflightInputDTO
    from backend.services.admin_data.request_auth import AdminRequestActor
    from backend.services.admin_data.run_data import (
        AdminRunData,
        CREATE_RUN,
        FAIL_RUN,
        RunCreateInputDTO,
        RunFailInputDTO,
        RunLookupInputDTO,
    )
    from backend.services.admin_gateway import GatewayInferenceError, resolve_platform_model_alias
    from backend.services.story_workspace.canonical_project_instruction import (
        STORY_WORKSPACE_CANONICAL_PROJECT_INSTRUCTION,
        story_workspace_canonical_project_fallback_slug,
    )
    from backend.services.story_workspace.dream_launch_application_service import (
        DreamLaunchApplicationService,
        DreamLaunchIdempotencyConflict,
        DreamLaunchSource,
    )
    from backend.services.story_workspace.dream_launch_runtime import DreamLaunchRuntimeError, PreparedDreamLaunchBinding
    from backend.services.story_workspace.dream_lifecycle_observer import NormalizedTurnOutcome, drain_chat_agent_turn
    from backend.story_workspace.contracts import StoryWorkspaceDreamLaunchCommand, StoryWorkspaceDreamRunContext

logger = logging.getLogger(__name__)


class DreamLaunchApplicationError(RuntimeError):
    def __init__(self, code: str, status_code: int) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(code)


def _translate_admin_error(error: AdminDataError) -> None:
    if error.code in {"DREAM_LAUNCH_IDEMPOTENCY_CONFLICT", "IDEMPOTENCY_CONFLICT"}:
        raise DreamLaunchIdempotencyConflict() from error
    raise DreamLaunchApplicationError(error.code, error.status_code) from error


def _decode_json_object(raw: Any) -> dict[str, Any]:
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError, RecursionError):
        return {}
    return dict(value) if isinstance(value, dict) else {}


@dataclass(frozen=True)
class DreamLaunchBinding:
    deck_plugin_id: str
    deck_plugin_version: str
    deck_plugin_binding_id: str
    binding_revision: int


class DreamLaunchRuntimePort(Protocol):
    async def authorize(self, *, deck_id: str, workspace_id: str, agent_id: str | None) -> None: ...
    async def prepare(self, *, deck_id: str, workspace_id: str, agent_id: str | None,
        existing_run: Mapping[str, Any] | None) -> PreparedDreamLaunchBinding: ...


def _launch_instruction(goal: str) -> str:
    project_slug = story_workspace_canonical_project_fallback_slug(goal)
    return (
        f"{goal}\n\n"
        "你正在执行首次 Dream 的最小工作台初始化。不要运行或研究完整 drama 命令。\n"
        f"服务器已分配 project_id/project_slug：{project_slug}。必须原样使用，不要计算、查询或验证哈希。\n"
        "只完成以下工作：\n"
        "1. 使用内建 Write 工具直接写文件；不要读取/搜索插件源码、CLAUDE.md、模板，不要调用 Agent、WebFetch、WebSearch、AskUserQuestion 或 Dream MCP。\n"
        "2. 至少创建 assets/characters/lead-a.md 与 assets/characters/lead-b.md；每个文件用 YAML frontmatter 提供 char_id、char_name，正文写简短人物关系和动机。\n"
        "3. 至少创建 assets/scenes/terminal.md；用 YAML frontmatter 提供 scene_id、scene_name，正文写简短场景氛围和空间信息。\n"
        f"4. 创建 stories/{project_slug}/project.yaml，其中 project_id 与 project_slug 都严格等于 {project_slug}，project_name 使用本次创作的中文短标题。\n"
        f"5. 创建 stories/{project_slug}/episodes/EP01/storyboard.yaml，至少提供 total_shots、total_duration_sec 和 shots 列表，形成可编辑的简洁分镜草稿。\n"
        "6. 不要写 .dream；宿主会在 root turn 成功结束后自动同步。五类工作台文件写完后立即结束，不做联网调查、额外规划或自检循环。\n"
        f"{STORY_WORKSPACE_CANONICAL_PROJECT_INSTRUCTION}"
    )


_SAFE_AGENT_ERROR_CODE = re.compile(r"^\[([A-Z][A-Z0-9_]{2,79})\]")


def _dream_launch_event_error_code(event: Any) -> str | None:
    if event.type == "error":
        match = _SAFE_AGENT_ERROR_CODE.match(str(event.data.get("errorText") or ""))
        return match.group(1) if match else "DREAM_AGENT_DISPATCH_FAILED"
    if event.type == "finish" and event.data.get("finishReason") == "error":
        return "DREAM_AGENT_DISPATCH_FAILED"
    return None


class DreamLaunchTaskRegistry:
    """Process owner for launch drains that outlive their HTTP request."""

    def __init__(self) -> None:
        self._tasks: set[asyncio.Task[Any]] = set()
        self._accepting = True

    def start(self) -> None:
        self._accepting = True

    def create_task(self, task_factory: Callable[[], Any], *, name: str) -> asyncio.Task[Any]:
        if not self._accepting:
            raise RuntimeError("Dream launch task registry is closed")
        task = asyncio.create_task(task_factory(), name=name)
        self._tasks.add(task)
        task.add_done_callback(self._task_done)
        return task

    def _task_done(self, task: asyncio.Task[Any]) -> None:
        if task not in self._tasks:
            return
        self._tasks.discard(task)
        if task.cancelled():
            return
        try:
            failure = task.exception()
        except asyncio.CancelledError:
            return
        if failure is not None:
            logger.error("Dream launch drain failed", exc_info=(type(failure), failure, failure.__traceback__))

    async def aclose(self) -> None:
        self._accepting = False
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        for task in tasks:
            self._task_done(task)

    def diagnostics(self) -> dict[str, int]:
        return {"launch_owned_tasks": len(self._tasks), "launch_running_tasks": sum(not task.done() for task in self._tasks)}


@dataclass(slots=True)
class _DreamLaunchFailureTracker:
    error_code: str | None = None

    def observe(self, event: Any) -> None:
        candidate = _dream_launch_event_error_code(event)
        if self.error_code is None and candidate is not None:
            self.error_code = candidate


class DreamAgentTurnDispatcher:
    """Start and settle a launch turn through the canonical Chat entrypoint."""

    def __init__(self, factory: Any | None = None, *, request_factory: Callable[..., Any] | None = None,
        failure_handler: Callable[..., Any] | None = None, task_registry: DreamLaunchTaskRegistry | None = None) -> None:
        self._factory = factory
        self._request_factory = request_factory
        self._failure_handler = failure_handler
        self._task_registry = task_registry

    def __call__(self, **values: Any) -> Any:
        request = self._build_request(values)
        task_name = f"dream-launch-turn-{values['message_id']}"
        factory = partial(self._consume, request, values)
        if self._task_registry is not None:
            return self._task_registry.create_task(factory, name=task_name)
        return asyncio.create_task(factory(), name=task_name)

    def _build_request(self, values: dict[str, Any]) -> Any:
        request_factory = self._request_factory
        if request_factory is None:
            from claude_agent.service import ClaudeAgentRunRequest
            request_factory = ClaudeAgentRunRequest
        return request_factory(user_id=values["actor_id"], thread_id=values["thread_id"], resume=False,
            message_id=values["message_id"], message_parts=values["parts"], message_metadata=values["metadata"],
            system_prompt=values.get("system_prompt"))

    def _selected_factory(self) -> Any:
        if self._factory is not None:
            return self._factory
        from agent_factory import claude_agent_thread_factory
        return claude_agent_thread_factory

    async def _consume(self, request: Any, values: dict[str, Any]) -> None:
        tracker = _DreamLaunchFailureTracker()
        cancelled = False
        try:
            result = await drain_chat_agent_turn(self._selected_factory(), request, on_event=tracker.observe)
            if tracker.error_code is None and result.outcome in {NormalizedTurnOutcome.FAILED, NormalizedTurnOutcome.INCOMPLETE}:
                tracker.error_code = "DREAM_AGENT_DISPATCH_FAILED"
        except asyncio.CancelledError:
            tracker.error_code = "DREAM_AGENT_DISPATCH_CANCELLED"
            cancelled = True
        except Exception:
            tracker.error_code = "DREAM_AGENT_DISPATCH_FAILED"
        if tracker.error_code is not None and self._failure_handler is not None:
            recorded = self._failure_handler(workflow_run_id=values["context"].workflow_run_id,
                actor_id=str(values["actor_id"]), thread_id=str(values["thread_id"]),
                message_id=str(values["message_id"]), error_code=tracker.error_code)
            if inspect.isawaitable(recorded):
                await recorded
        if cancelled:
            raise asyncio.CancelledError


def build_dream_agent_turn_dispatcher(factory: Any | None = None, *, request_factory: Callable[..., Any] | None = None,
    failure_handler: Callable[..., Any] | None = None, task_registry: DreamLaunchTaskRegistry | None = None) -> DreamAgentTurnDispatcher:
    return DreamAgentTurnDispatcher(factory, request_factory=request_factory, failure_handler=failure_handler, task_registry=task_registry)


class AdminDreamLaunchWorkflowOperations:
    """Use strict Admin DTOs for replay, Preflight and Run persistence."""

    def __init__(self, client: AdminDataClient, *, actor: AdminRequestActor, runtime_port: DreamLaunchRuntimePort,
        platform_model_resolver: Callable[[int | str, str | None], str] = resolve_platform_model_alias) -> None:
        if not {"dream:read", "dream:write"} <= actor.scopes:
            raise AdminDataError("DREAM_SCOPE_REQUIRED", 403)
        self._actor = actor
        self._runtime_port = runtime_port
        self._launch = AdminLaunchMetadataData(client, canonical_user_id=actor.canonical_user_id)
        self._preflight = AdminPreflightData(client, canonical_user_id=actor.canonical_user_id)
        self._runs = AdminRunData(client, canonical_user_id=actor.canonical_user_id)
        self._platform_model_resolver = platform_model_resolver
        self._replay: Any | None = None
        self._scope: tuple[str, str] | None = None

    async def prepare(self, command: StoryWorkspaceDreamLaunchCommand, *, actor_id: str, workspace_id: str) -> DreamLaunchBinding:
        self._require_actor(actor_id)
        try:
            await self._runtime_port.authorize(deck_id=command.deck_id, workspace_id=workspace_id, agent_id=command.agent_id)
            lookup = LaunchSourceInputDTO(workspace_id=workspace_id, deck_id=command.deck_id, agent_id=command.agent_id,
                goal=command.goal, idempotency_key=command.idempotency_key)
            result = await asyncio.to_thread(self._launch.execute, LOOKUP_LAUNCH_REPLAY, lookup, str(uuid4()),
                access_token=self._actor.access_token)
            self._replay = result.replay
            self._scope = (actor_id, workspace_id)
            if self._replay is None:
                await asyncio.to_thread(self._platform_model_resolver, actor_id, None)
                existing = None
            else:
                existing = {"id": self._replay.workflow_run_id, "source_voice_thread_id": self._replay.thread_id}
            prepared = await self._runtime_port.prepare(deck_id=command.deck_id, workspace_id=workspace_id,
                agent_id=command.agent_id, existing_run=existing)
        except AdminDataError as error:
            _translate_admin_error(error)
        except DreamLaunchRuntimeError as error:
            raise DreamLaunchApplicationError(error.code, error.status_code) from error
        except GatewayInferenceError as error:
            raise DreamLaunchApplicationError(error.code, error.status_code) from error
        return DreamLaunchBinding(prepared.deck_plugin_id, prepared.deck_plugin_version,
            prepared.deck_plugin_binding_id, prepared.binding_revision)

    async def create_preflight(self, **values: Any) -> dict[str, Any]:
        self._require_scope(values)
        try:
            if self._replay is not None:
                result = await asyncio.to_thread(self._preflight.read,
                    PreflightInputDTO(workflow_preflight_id=self._replay.workflow_preflight_id), str(uuid4()),
                    access_token=self._actor.access_token)
                if result.get("status") != "passed":
                    raise DreamLaunchApplicationError("DECK_RUNTIME_CONFIG_INVALID", 409)
                return result
            input_json = json.dumps(values["input_data"], ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))
            result = await asyncio.to_thread(self._preflight.execute_recovering,
                PreflightExecutionInputDTO(workspace_id=values["workspace_id"], deck_id=values["deck_id"],
                    binding_revision=values["binding_revision"], input_json=input_json), str(uuid4()),
                access_token=self._actor.access_token)
            if result.get("status") != "passed":
                raise DreamLaunchApplicationError(result.get("error_code") or "DECK_RUNTIME_CONFIG_INVALID", 409)
            return result
        except AdminDataError as error:
            _translate_admin_error(error)

    async def create_run(self, **values: Any) -> dict[str, Any]:
        self._require_scope(values)
        try:
            if self._replay is not None:
                return await asyncio.to_thread(self._runs.read,
                    RunLookupInputDTO(workspace_id=values["workspace_id"], workflow_run_id=self._replay.workflow_run_id),
                    str(uuid4()), access_token=self._actor.access_token)
            return await asyncio.to_thread(self._runs.write_recovering, CREATE_RUN,
                RunCreateInputDTO(workspace_id=values["workspace_id"], workflow_preflight_id=values["preflight_id"],
                    preflight_token=values["preflight_token"], idempotency_key=values["idempotency_key"],
                    source_voice_thread_id=values["source_thread_id"], source_message_id=values["source_message_id"],
                    source_message_time=values["source_message_time"].isoformat()), str(uuid4()),
                access_token=self._actor.access_token)
        except AdminDataError as error:
            _translate_admin_error(error)

    def _require_actor(self, actor_id: str) -> None:
        if actor_id != self._actor.canonical_user_id:
            raise PermissionError("Dream launch actor mismatch")

    def _require_scope(self, values: Mapping[str, Any]) -> None:
        if self._scope != (values.get("actor_id"), values.get("workspace_id")):
            raise PermissionError("Dream launch workflow scope mismatch")


class DreamLaunchFailureRecorder:
    """Persist terminal launch failure using Admin Run and envelope operations."""

    def __init__(self, client: AdminDataClient, *, actor: AdminRequestActor, workspace_id: str) -> None:
        self._actor = actor
        self._workspace_id = workspace_id
        self._runs = AdminRunData(client, canonical_user_id=actor.canonical_user_id)
        self._launch = AdminLaunchMetadataData(client, canonical_user_id=actor.canonical_user_id)

    async def record(self, *, workflow_run_id: str, actor_id: str, thread_id: str,
        message_id: str, error_code: str) -> None:
        if actor_id != self._actor.canonical_user_id:
            return
        try:
            failed = await asyncio.to_thread(self._runs.write_recovering, FAIL_RUN,
                RunFailInputDTO(workspace_id=self._workspace_id, workflow_run_id=workflow_run_id,
                    reason_code="dream_agent_terminal_error", failed_step="dream_agent_dispatch", error_code=error_code),
                str(uuid4()), access_token=self._actor.access_token)
            if failed.get("status") != "failed":
                return
            source = LaunchFailureExpectation(thread_id, message_id)
            await asyncio.to_thread(self._launch.execute_recovering, FAIL_LAUNCH_ENVELOPE,
                LaunchFailureInputDTO(workspace_id=self._workspace_id, workflow_run_id=workflow_run_id, error_code=error_code),
                str(uuid4()), access_token=self._actor.access_token, source=source)
        except AdminDataError as error:
            logger.error("Admin failed to persist Dream launch terminal state: %s", error.code)


class DreamLaunchEnvelopeDispatcher:
    """Claim/finish launch metadata in Admin and schedule the Dream-owned turn."""

    def __init__(self, client: AdminDataClient, *, actor: AdminRequestActor, workspace_id: str,
        turn_dispatcher: Callable[..., Any], before_claim: Callable[[], Any] | None = None) -> None:
        self._actor = actor
        self._workspace_id = workspace_id
        self._launch = AdminLaunchMetadataData(client, canonical_user_id=actor.canonical_user_id)
        self._decks = AdminDeckDetailData(client)
        self._turn_dispatcher = turn_dispatcher
        self._before_claim = before_claim

    async def __call__(self, *, actor_id: str, goal: str, source: DreamLaunchSource,
        context: StoryWorkspaceDreamRunContext) -> bool:
        if actor_id != self._actor.canonical_user_id:
            raise PermissionError("Dream launch actor mismatch")
        if self._before_claim is not None:
            called = self._before_claim()
            if inspect.isawaitable(called):
                await called
        instruction = _launch_instruction(goal)
        claim_input = LaunchClaimInputDTO(workspace_id=self._workspace_id,
            workflow_run_id=context.workflow_run_id, instruction_text=instruction)
        try:
            result = await asyncio.to_thread(self._launch.execute_recovering, CLAIM_LAUNCH, claim_input,
                str(uuid4()), access_token=self._actor.access_token, source=source, context=context)
            claim = result.root
            if not claim.claimed:
                return False
            system_prompt = await self._system_prompt(context)
            parts = json.loads(claim.parts_json)
            metadata = _decode_json_object(claim.metadata_json)
            try:
                accepted = self._turn_dispatcher(actor_id=actor_id, thread_id=source.thread_id,
                    message_id=source.message_id, parts=parts, metadata=metadata, context=context,
                    system_prompt=system_prompt, resume=False)
            except Exception:
                await self._finish(context, source, claim.claim_id, False)
                raise
            if accepted is False:
                await self._finish(context, source, claim.claim_id, False)
                return False
            return await self._finish(context, source, claim.claim_id, True)
        except AdminDataError as error:
            _translate_admin_error(error)

    async def _system_prompt(self, context: StoryWorkspaceDreamRunContext) -> str | None:
        if context.agent_id is None:
            return None
        try:
            detail = await asyncio.to_thread(self._decks.detail, DeckIdInputDTO(deck_id=context.deck_id),
                str(uuid4()), access_token=self._actor.access_token)
        except AdminDataError as error:
            _translate_admin_error(error)
        voices = detail.get("voices", []) if detail is not None else []
        selected = [voice for voice in voices if voice.get("id") == context.agent_id
            and voice.get("deck_id") == context.deck_id and voice.get("enabled") is True]
        if len(selected) != 1:
            raise DreamLaunchApplicationError("AGENT_ACCESS_DENIED", 404)
        return str(selected[0]["system_prompt"])

    async def _finish(self, context: StoryWorkspaceDreamRunContext, source: DreamLaunchSource,
        claim_id: str, accepted: bool) -> bool:
        result = await asyncio.to_thread(self._launch.execute_recovering, FINISH_LAUNCH,
            LaunchFinishInputDTO(workspace_id=self._workspace_id, workflow_run_id=context.workflow_run_id,
                claim_id=claim_id, accepted=accepted), str(uuid4()), access_token=self._actor.access_token,
            source=source, context=context)
        return bool(result.finished)


def build_dream_launch_application_service(client: AdminDataClient, *, actor: AdminRequestActor,
    workspace_id: str, runtime_port: DreamLaunchRuntimePort, turn_dispatcher: Callable[..., Any] | None = None,
    launch_task_registry: DreamLaunchTaskRegistry | None = None, dispatch_before_claim: Callable[[], Any] | None = None,
    platform_model_resolver: Callable[[int | str, str | None], str] = resolve_platform_model_alias) -> DreamLaunchApplicationService:
    """Compose one request-scoped launch without a Dream database credential."""
    failure_recorder = DreamLaunchFailureRecorder(client, actor=actor, workspace_id=workspace_id)
    selected_turn_dispatcher = turn_dispatcher or build_dream_agent_turn_dispatcher(
        failure_handler=failure_recorder.record, task_registry=launch_task_registry)
    return DreamLaunchApplicationService(
        source_repository=AdminLaunchSourceRepository(client, actor=actor),
        workflow=AdminDreamLaunchWorkflowOperations(client, actor=actor, runtime_port=runtime_port,
            platform_model_resolver=platform_model_resolver),
        dispatcher=DreamLaunchEnvelopeDispatcher(client, actor=actor, workspace_id=workspace_id,
            turn_dispatcher=selected_turn_dispatcher, before_claim=dispatch_before_claim),
    )


__all__ = [
    "AdminDreamLaunchWorkflowOperations", "DreamAgentTurnDispatcher", "DreamLaunchApplicationError",
    "DreamLaunchBinding", "DreamLaunchEnvelopeDispatcher", "DreamLaunchFailureRecorder",
    "DreamLaunchRuntimePort", "DreamLaunchTaskRegistry", "build_dream_agent_turn_dispatcher",
    "build_dream_launch_application_service",
]
