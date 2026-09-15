# [Input] Launch command, Admin Runtime port and existing Dream workflow/dispatch collaborators.
# [Output] Source/Run dispatch plus an Admin-prepared immutable Runtime binding projection.
# [Pos] Dream launch application adapters; remaining source/Run SQL is an explicit later migration scope.
# [Sync] 2026-09-16: remove local Runtime provisioning and require Registry130-132 at request scope.
"""Production persistence and runtime adapters for Dream launch.

The browser supplies only a Deck, goal, and idempotency key. This module owns
all persisted source facts, requires an Admin-prepared Dream binding,
creates the workflow, and dispatches the
durable first-turn envelope.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import inspect
import json
import logging
import re
from functools import partial
from typing import Any, Callable, Protocol
import uuid

logger = logging.getLogger(__name__)

try:
    from models.workflow_run import AuthenticatedActorContext, RunStatus
    from services.admin_gateway import (
        GatewayInferenceError,
        resolve_platform_model_alias,
    )
    from services.story_workspace.dream_launch_application_service import (
        DreamLaunchApplicationService,
        DreamLaunchIdempotencyConflict,
        DreamLaunchSource,
    )
    from services.story_workspace.dream_launch_runtime import (
        DreamLaunchRuntimeError,
        PreparedDreamLaunchBinding,
    )
    from services.story_workspace.canonical_project_instruction import (
        STORY_WORKSPACE_CANONICAL_PROJECT_INSTRUCTION,
        story_workspace_canonical_project_fallback_slug,
    )
    from services.story_workspace.dream_lifecycle_observer import (
        NormalizedTurnOutcome,
        drain_chat_agent_turn,
    )
    from services.workflow.preflight_service import PreflightService, PreflightStatus
    from services.workflow.run_service import WorkflowRunError, WorkflowRunService
    from story_workspace.contracts import (
        StoryWorkspaceDreamLaunchCommand,
        StoryWorkspaceDreamRunContext,
    )
except ModuleNotFoundError:  # Support package imports from repository root.
    from backend.models.workflow_run import AuthenticatedActorContext, RunStatus
    from backend.services.admin_gateway import (
        GatewayInferenceError,
        resolve_platform_model_alias,
    )
    from backend.services.story_workspace.dream_launch_application_service import (
        DreamLaunchApplicationService,
        DreamLaunchIdempotencyConflict,
        DreamLaunchSource,
    )
    from backend.services.story_workspace.dream_launch_runtime import (
        DreamLaunchRuntimeError,
        PreparedDreamLaunchBinding,
    )
    from backend.services.story_workspace.canonical_project_instruction import (
        STORY_WORKSPACE_CANONICAL_PROJECT_INSTRUCTION,
        story_workspace_canonical_project_fallback_slug,
    )
    from backend.services.story_workspace.dream_lifecycle_observer import (
        NormalizedTurnOutcome,
        drain_chat_agent_turn,
    )
    from backend.services.workflow.preflight_service import (
        PreflightService,
        PreflightStatus,
    )
    from backend.services.workflow.run_service import (
        WorkflowRunError,
        WorkflowRunService,
    )
    from backend.story_workspace.contracts import (
        StoryWorkspaceDreamLaunchCommand,
        StoryWorkspaceDreamRunContext,
    )


STORY_WORKSPACE_DREAM_LAUNCH_METADATA_KIND = "story-workspace-dream-launch"
STORY_WORKSPACE_DREAM_DISPATCH_CLAIM_TTL = timedelta(minutes=5)


class DreamLaunchApplicationError(RuntimeError):
    def __init__(self, code: str, status_code: int) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(code)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _decode_json_object(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    try:
        value = json.loads(str(raw or "{}"))
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _parse_time(raw: Any) -> datetime:
    value = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value


@dataclass(frozen=True)
class DreamLaunchBinding:
    deck_plugin_id: str
    deck_plugin_version: str
    deck_plugin_binding_id: str
    binding_revision: int


class DreamLaunchRuntimePort(Protocol):
    """Authorize and prepare launch Runtime metadata through the Admin API."""

    async def authorize(
        self,
        *,
        deck_id: str,
        workspace_id: str,
        agent_id: str | None,
    ) -> None: ...

    async def prepare(
        self,
        *,
        deck_id: str,
        workspace_id: str,
        agent_id: str | None,
        existing_run: Any | None,
    ) -> PreparedDreamLaunchBinding: ...


class DreamLaunchSourceRepository:
    """Atomically ensure one hidden Deck-bound source thread and message."""

    def __init__(self, db: Any) -> None:
        self.db = db
    async def ensure_source(
        self,
        *,
        actor_id: str,
        workspace_id: str,
        deck_id: str,
        agent_id: str | None,
        goal: str,
        idempotency_key: str,
        request_fingerprint: str,
        thread_id: str,
        message_id: str,
    ) -> DreamLaunchSource:
        try:
            numeric_actor_id = int(actor_id)
        except (TypeError, ValueError) as exc:
            raise PermissionError("invalid Dream launch actor") from exc
        now = datetime.now(UTC)
        metadata = {
            "kind": STORY_WORKSPACE_DREAM_LAUNCH_METADATA_KIND,
            "schemaVersion": "story-workspace-dream-launch/v1",
            "visibility": "system-hidden",
            "actorId": actor_id,
            "workspaceId": workspace_id,
            "deckId": deck_id,
            "agentId": agent_id,
            "goal": goal,
            "idempotencyKey": idempotency_key,
            "requestFingerprint": request_fingerprint,
            "dispatchStatus": "pending",
        }
        try:
            self.db.execute("BEGIN")
            self._require_scope(
                actor_id=numeric_actor_id,
                workspace_id=workspace_id,
                deck_id=deck_id,
            )
            existing_message = self.db.execute(
                "SELECT message.*, thread.user_id, thread.deck_id, thread.voice_id "
                "FROM chat_message AS message JOIN chat_thread AS thread "
                "ON thread.id = message.thread_id WHERE message.id = %s",
                (message_id,),
            ).fetchone()
            if existing_message is not None:
                self._validate_existing(
                    existing_message,
                    actor_id=numeric_actor_id,
                    deck_id=deck_id,
                    agent_id=agent_id,
                    thread_id=thread_id,
                    request_fingerprint=request_fingerprint,
                    idempotency_key=idempotency_key,
                )
                self.db.commit()
                existing_metadata = _decode_json_object(
                    existing_message["metadata"]
                )
                return DreamLaunchSource(
                    thread_id=thread_id,
                    message_id=message_id,
                    message_time=_parse_time(existing_message["created_at"]),
                    request_fingerprint=str(
                        existing_metadata["requestFingerprint"]
                    ),
                    created=False,
                )

            existing_thread = self.db.execute(
                "SELECT id, user_id, deck_id, voice_id FROM chat_thread WHERE id = %s",
                (thread_id,),
            ).fetchone()
            if existing_thread is None:
                self.db.execute(
                    "INSERT INTO chat_thread (id, user_id, title, deck_id, voice_id) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (
                        thread_id,
                        numeric_actor_id,
                        f"Dream · {goal[:80]}",
                        deck_id,
                        agent_id,
                    ),
                )
            elif (
                int(existing_thread["user_id"]) != numeric_actor_id
                or existing_thread["deck_id"] != deck_id
                or existing_thread["voice_id"] != agent_id
            ):
                raise PermissionError("Dream backing thread scope mismatch")

            self.db.execute(
                "INSERT INTO chat_message "
                "(id, thread_id, role, parts, metadata, created_at) "
                "VALUES (%s, %s, 'user', %s, %s, %s)",
                (
                    message_id,
                    thread_id,
                    _canonical_json([{"type": "text", "text": goal}]),
                    _canonical_json(metadata),
                    now.isoformat(),
                ),
            )
            self.db.execute(
                "UPDATE chat_thread SET updated_at = %s WHERE id = %s",
                (now.isoformat(), thread_id),
            )
            self.db.commit()
        except Exception:
            if self.db.in_transaction:
                self.db.rollback()
            raise
        return DreamLaunchSource(
            thread_id=thread_id,
            message_id=message_id,
            message_time=now,
            request_fingerprint=request_fingerprint,
            created=True,
        )

    def _require_scope(
        self,
        *,
        actor_id: int,
        workspace_id: str,
        deck_id: str,
    ) -> None:
        row = self.db.execute(
            "SELECT deck.id FROM decks AS deck "
            "JOIN story_workspace_workspaces AS workspace "
            "ON workspace.id = %s AND workspace.owner_id = deck.owner_id "
            "WHERE deck.id = %s AND deck.owner_id = %s AND deck.enabled IS TRUE",
            (workspace_id, deck_id, actor_id),
        ).fetchone()
        if row is None:
            raise PermissionError("Deck not found or permission denied")

    @staticmethod
    def _validate_existing(
        row: Any,
        *,
        actor_id: int,
        deck_id: str,
        agent_id: str | None,
        thread_id: str,
        request_fingerprint: str,
        idempotency_key: str,
    ) -> None:
        metadata = _decode_json_object(row["metadata"])
        scope_matches = (
            row["thread_id"] == thread_id
            and int(row["user_id"]) == actor_id
            and row["role"] == "user"
            and metadata.get("kind")
            == STORY_WORKSPACE_DREAM_LAUNCH_METADATA_KIND
            and metadata.get("idempotencyKey") == idempotency_key
        )
        if not scope_matches:
            raise PermissionError("Dream launch source scope mismatch")
        if (
            row["deck_id"] != deck_id
            or row["voice_id"] != agent_id
            or metadata.get("deckId") != deck_id
            or metadata.get("agentId") != agent_id
            or metadata.get("requestFingerprint") != request_fingerprint
        ):
            raise DreamLaunchIdempotencyConflict()


def _launch_instruction(goal: str) -> str:
    project_slug = story_workspace_canonical_project_fallback_slug(goal)
    return (
        f"{goal}\n\n"
        "你正在执行首次 Dream 的最小工作台初始化。不要运行或研究完整 drama 命令。\n"
        f"服务器已分配 project_id/project_slug：{project_slug}。必须原样使用，"
        "不要计算、查询或验证哈希。\n"
        "只完成以下工作：\n"
        "1. 使用内建 Write 工具直接写文件；不要读取/搜索插件源码、CLAUDE.md、模板，"
        "不要调用 Agent、WebFetch、WebSearch、AskUserQuestion 或 Dream MCP。\n"
        "2. 至少创建 assets/characters/lead-a.md 与 assets/characters/lead-b.md；"
        "每个文件用 YAML "
        "frontmatter 提供 char_id、char_name，正文写简短人物关系和动机。\n"
        "3. 至少创建 assets/scenes/terminal.md；用 YAML frontmatter 提供 "
        "scene_id、scene_name，正文写简短场景氛围和空间信息。\n"
        f"4. 创建 stories/{project_slug}/project.yaml，其中 project_id 与 "
        f"project_slug 都严格等于 {project_slug}，project_name 使用本次创作的中文短标题。\n"
        f"5. 创建 stories/{project_slug}/episodes/EP01/storyboard.yaml，至少提供 "
        "total_shots、total_duration_sec 和 shots 列表，形成可编辑的简洁分镜草稿。\n"
        "6. 不要写 .dream；宿主会在 root turn 成功结束后自动同步。"
        "五类工作台文件写完后立即结束，不做联网调查、额外规划或自检循环。\n"
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

    def create_task(
        self,
        task_factory: Callable[[], Any],
        *,
        name: str,
    ) -> asyncio.Task[Any]:
        """Create and own a drain, or reject it before its coroutine exists."""

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
            logger.error(
                "Dream launch drain failed",
                exc_info=(type(failure), failure, failure.__traceback__),
            )

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
        return {
            "launch_owned_tasks": len(self._tasks),
            "launch_running_tasks": sum(
                not task.done() for task in self._tasks
            ),
        }


@dataclass(slots=True)
class _DreamLaunchFailureTracker:
    error_code: str | None = None

    def observe(self, event: Any) -> None:
        candidate = _dream_launch_event_error_code(event)
        if self.error_code is None and candidate is not None:
            self.error_code = candidate


class DreamAgentTurnDispatcher:
    """Start and settle a launch turn through the canonical Chat entrypoint."""

    def __init__(
        self,
        factory: Any | None = None,
        *,
        request_factory: Callable[..., Any] | None = None,
        failure_handler: Callable[..., Any] | None = None,
        task_registry: DreamLaunchTaskRegistry | None = None,
    ) -> None:
        self._factory = factory
        self._request_factory = request_factory
        self._failure_handler = failure_handler
        self._task_registry = task_registry

    def __call__(self, **values: Any) -> Any:
        request = self._build_request(values)
        task_name = f"dream-launch-turn-{values['message_id']}"
        if self._task_registry is not None:
            return self._task_registry.create_task(
                partial(self._consume, request, values),
                name=task_name,
            )
        return asyncio.create_task(
            self._consume(request, values),
            name=task_name,
        )

    def _build_request(self, values: dict[str, Any]) -> Any:
        request_factory = self._request_factory
        if request_factory is None:
            from claude_agent.service import ClaudeAgentRunRequest

            request_factory = ClaudeAgentRunRequest
        return request_factory(
            user_id=values["actor_id"],
            thread_id=values["thread_id"],
            resume=False,
            message_id=values["message_id"],
            message_parts=values["parts"],
            message_metadata=values["metadata"],
            system_prompt=values.get("system_prompt"),
        )

    def _selected_factory(self) -> Any:
        if self._factory is not None:
            return self._factory
        from agent_factory import claude_agent_thread_factory

        return claude_agent_thread_factory

    async def _consume(self, request: Any, values: dict[str, Any]) -> None:
        tracker = _DreamLaunchFailureTracker()
        cancelled = False
        try:
            result = await drain_chat_agent_turn(
                self._selected_factory(),
                request,
                on_event=tracker.observe,
            )
            if (
                tracker.error_code is None
                and result.outcome
                in {NormalizedTurnOutcome.FAILED, NormalizedTurnOutcome.INCOMPLETE}
            ):
                tracker.error_code = "DREAM_AGENT_DISPATCH_FAILED"
        except asyncio.CancelledError:
            tracker.error_code = "DREAM_AGENT_DISPATCH_CANCELLED"
            cancelled = True
        except Exception:
            tracker.error_code = "DREAM_AGENT_DISPATCH_FAILED"
        if tracker.error_code is not None and self._failure_handler is not None:
            recorded = self._failure_handler(
                workflow_run_id=values["context"].workflow_run_id,
                actor_id=str(values["actor_id"]),
                message_id=str(values["message_id"]),
                error_code=tracker.error_code,
            )
            if inspect.isawaitable(recorded):
                await recorded
        if cancelled:
            raise asyncio.CancelledError


def build_dream_agent_turn_dispatcher(
    factory: Any | None = None,
    *,
    request_factory: Callable[..., Any] | None = None,
    failure_handler: Callable[..., Any] | None = None,
    task_registry: DreamLaunchTaskRegistry | None = None,
) -> DreamAgentTurnDispatcher:
    return DreamAgentTurnDispatcher(
        factory,
        request_factory=request_factory,
        failure_handler=failure_handler,
        task_registry=task_registry,
    )


class DreamLaunchEnvelopeDispatcher:
    """Persist the complete launch envelope and schedule it at most once."""

    def __init__(
        self,
        db: Any,
        *,
        turn_dispatcher: Callable[..., Any] | None = None,
        before_claim: Callable[[], Any] | None = None,
    ) -> None:
        self.db = db
        self._turn_dispatcher = (
            turn_dispatcher or build_dream_agent_turn_dispatcher()
        )
        self._before_claim = before_claim

    def __call__(
        self,
        *,
        actor_id: str,
        goal: str,
        source: DreamLaunchSource,
        context: StoryWorkspaceDreamRunContext,
    ) -> bool:
        if self._before_claim is not None:
            self._before_claim()
        now = datetime.now(UTC)
        claim_id = "dlc_" + uuid.uuid4().hex
        try:
            self.db.execute("BEGIN")
            row = self._message_row(source)
            if row is None or str(row["user_id"]) != actor_id:
                raise PermissionError("Dream launch message scope mismatch")
            metadata = _decode_json_object(row["metadata"])
            if metadata.get("kind") != STORY_WORKSPACE_DREAM_LAUNCH_METADATA_KIND:
                raise PermissionError("Dream launch message kind mismatch")
            existing_run_id = metadata.get("workflowRunId")
            if existing_run_id not in {None, context.workflow_run_id}:
                raise DreamLaunchApplicationError(
                    "IDEMPOTENCY_CONFLICT", 409
                )
            if metadata.get("dispatchStatus") == "dispatched":
                self.db.commit()
                return False
            if self._claim_is_fresh(metadata, now=now):
                self.db.commit()
                return False

            parts = [{"type": "text", "text": _launch_instruction(goal)}]
            metadata.update({
                "workflowRunId": context.workflow_run_id,
                "threadId": context.thread_id,
                "dreamContext": context.model_dump(mode="json"),
                "projectStorySlug": (
                    story_workspace_canonical_project_fallback_slug(goal)
                ),
                "dispatchStatus": "dispatching",
                "dispatchClaimId": claim_id,
                "dispatchClaimedAt": now.isoformat(),
            })
            self.db.execute(
                "UPDATE chat_message SET parts = %s, metadata = %s WHERE id = %s",
                (
                    _canonical_json(parts),
                    _canonical_json(metadata),
                    source.message_id,
                ),
            )
            self.db.commit()
        except Exception:
            if self.db.in_transaction:
                self.db.rollback()
            raise

        agent_metadata = dict(metadata)
        agent_metadata["dispatchStatus"] = "dispatched"
        agent_metadata.pop("dispatchClaimId", None)
        agent_metadata.pop("dispatchClaimedAt", None)
        try:
            system_prompt = None
            if context.agent_id:
                voice = self.db.execute(
                    "SELECT system_prompt FROM voices WHERE id = %s AND deck_id = %s AND enabled IS TRUE",
                    (context.agent_id, context.deck_id),
                ).fetchone()
                if voice is None:
                    raise DreamLaunchApplicationError("AGENT_ACCESS_DENIED", 404)
                system_prompt = str(voice["system_prompt"])
            accepted = self._turn_dispatcher(
                actor_id=actor_id,
                thread_id=source.thread_id,
                message_id=source.message_id,
                parts=parts,
                metadata=agent_metadata,
                context=context,
                system_prompt=system_prompt,
                resume=False,
            )
        except Exception:
            self._finish_claim(
                source.message_id,
                claim_id=claim_id,
                status="pending",
            )
            raise
        if accepted is False:
            self._finish_claim(
                source.message_id,
                claim_id=claim_id,
                status="pending",
            )
            return False
        return self._finish_claim(
            source.message_id,
            claim_id=claim_id,
            status="dispatched",
        )

    def _message_row(
        self,
        source: DreamLaunchSource,
    ) -> Any | None:
        return self.db.execute(
            "SELECT message.parts, message.metadata, thread.user_id "
            "FROM chat_message AS message JOIN chat_thread AS thread "
            "ON thread.id = message.thread_id "
            "WHERE message.id = %s AND message.thread_id = %s",
            (source.message_id, source.thread_id),
        ).fetchone()

    @staticmethod
    def _claim_is_fresh(metadata: dict[str, Any], *, now: datetime) -> bool:
        if metadata.get("dispatchStatus") != "dispatching":
            return False
        claimed_at = metadata.get("dispatchClaimedAt")
        if not isinstance(claimed_at, str):
            return False
        try:
            claimed_time = _parse_time(claimed_at)
        except (TypeError, ValueError):
            return False
        return now - claimed_time < STORY_WORKSPACE_DREAM_DISPATCH_CLAIM_TTL

    def _finish_claim(
        self,
        message_id: str,
        *,
        claim_id: str,
        status: str,
    ) -> bool:
        try:
            self.db.execute("BEGIN")
            row = self.db.execute(
                "SELECT metadata FROM chat_message WHERE id = %s",
                (message_id,),
            ).fetchone()
            metadata = _decode_json_object(row["metadata"] if row else None)
            if (
                metadata.get("dispatchStatus") != "dispatching"
                or metadata.get("dispatchClaimId") != claim_id
            ):
                self.db.commit()
                return False
            metadata["dispatchStatus"] = status
            metadata.pop("dispatchClaimId", None)
            metadata.pop("dispatchClaimedAt", None)
            self.db.execute(
                "UPDATE chat_message SET metadata = %s WHERE id = %s",
                (_canonical_json(metadata), message_id),
            )
            self.db.commit()
            return True
        except Exception:
            if self.db.in_transaction:
                self.db.rollback()
            raise


class DreamLaunchFailureRecorder:
    """Persist a launch-turn failure without owning the launch use case."""

    def __init__(self, token_secret: bytes | str) -> None:
        self._token_secret = token_secret

    async def record(
        self,
        *,
        workflow_run_id: str,
        actor_id: str,
        message_id: str,
        error_code: str,
    ) -> None:
        """Persist a safe terminal Agent failure using a fresh connection."""

        import database as runtime_database

        db = runtime_database.get_db()
        try:
            row = db.execute(
                "SELECT workspace_id, source_voice_thread_id, source_message_id "
                "FROM workflow_runs WHERE id = %s AND created_by = %s",
                (workflow_run_id, actor_id),
            ).fetchone()
            if row is None or row["source_message_id"] != message_id:
                if db.in_transaction:
                    db.rollback()
                return
            actor_context = AuthenticatedActorContext(
                actor_id=actor_id,
                workspace_id=str(row["workspace_id"]),
            )
            if db.in_transaction:
                db.rollback()
            try:
                failed = await WorkflowRunService(
                    db,
                    token_secret=self._token_secret,
                ).transition_run(
                    workflow_run_id,
                    RunStatus.FAILED,
                    actor_context,
                    failed_step="dream_agent_dispatch",
                    error_code=error_code,
                    reason_code="dream_agent_terminal_error",
                )
            except WorkflowRunError:
                return
            if str(getattr(failed.status, "value", failed.status)) != RunStatus.FAILED.value:
                return
            db.execute("BEGIN")
            message = db.execute(
                "SELECT metadata FROM chat_message "
                "WHERE id = %s AND thread_id = %s",
                (message_id, row["source_voice_thread_id"]),
            ).fetchone()
            metadata = _decode_json_object(message["metadata"] if message else None)
            if message is not None:
                metadata["dispatchStatus"] = "failed"
                metadata["dispatchErrorCode"] = error_code
                metadata.pop("dispatchClaimId", None)
                metadata.pop("dispatchClaimedAt", None)
                db.execute(
                    "UPDATE chat_message SET metadata = %s WHERE id = %s",
                    (_canonical_json(metadata), message_id),
                )
            db.commit()
        except Exception:
            if db.in_transaction:
                db.rollback()
            logger.exception(
                "Failed to persist Dream launch terminal error for run_id=%s",
                workflow_run_id,
            )
        finally:
            db.close()

class DreamLaunchWorkflowOperationsAdapter:
    """Production implementation of the launch service's named operations.

    One adapter instance belongs to one launch request. It carries the resolved
    idempotent Run between prepare/preflight/run steps, replacing the former
    local callback closures without becoming another application entry point.
    """

    def __init__(
        self,
        db: Any,
        *,
        preflight_service: PreflightService,
        token_secret: bytes | str,
        runtime_port: DreamLaunchRuntimePort,
        platform_model_resolver: Callable[[int | str, str | None], str] = (
            resolve_platform_model_alias
        ),
    ) -> None:
        self.db = db
        self._preflight_service = preflight_service
        self._run_service = WorkflowRunService(db, token_secret=token_secret)
        self._platform_model_resolver = platform_model_resolver
        self._runtime_port = runtime_port
        self._existing_run: Any | None = None
        self._actor_context: AuthenticatedActorContext | None = None

    async def prepare(
        self,
        command: StoryWorkspaceDreamLaunchCommand,
        *,
        actor_id: str,
        workspace_id: str,
    ) -> DreamLaunchBinding:
        actor_context = AuthenticatedActorContext(
            actor_id=actor_id,
            workspace_id=workspace_id,
        )
        self._actor_context = actor_context
        if self.db.in_transaction:
            self.db.rollback()
        try:
            await self._runtime_port.authorize(
                deck_id=command.deck_id,
                workspace_id=workspace_id,
                agent_id=command.agent_id,
            )
        except DreamLaunchRuntimeError as exc:
            raise DreamLaunchApplicationError(exc.code, exc.status_code) from exc
        existing_run = self._existing_replay_run(command, actor_context)
        self._existing_run = existing_run
        if self.db.in_transaction:
            self.db.rollback()
        if existing_run is None:
            # Do not hold a database read transaction across the Admin call.
            # A replay returns its already-created authoritative run even when
            # the catalog is temporarily unavailable; a new run must prove
            # current model eligibility before any source/run write occurs.
            if self.db.in_transaction:
                self.db.rollback()
            try:
                await asyncio.to_thread(
                    self._platform_model_resolver,
                    actor_id,
                    None,
                )
            except GatewayInferenceError as exc:
                raise DreamLaunchApplicationError(
                    exc.code,
                    exc.status_code,
                ) from exc
        try:
            prepared = await self._runtime_port.prepare(
                deck_id=command.deck_id,
                workspace_id=workspace_id,
                agent_id=command.agent_id,
                existing_run=existing_run,
            )
        except DreamLaunchRuntimeError as exc:
            raise DreamLaunchApplicationError(exc.code, exc.status_code) from exc
        return DreamLaunchBinding(
            deck_plugin_id=prepared.deck_plugin_id,
            deck_plugin_version=prepared.deck_plugin_version,
            deck_plugin_binding_id=prepared.deck_plugin_binding_id,
            binding_revision=prepared.binding_revision,
        )

    async def create_preflight(self, **values: Any) -> Any:
        actor_context = self._require_prepared_actor(values)
        existing_run = self._existing_run
        if existing_run is not None:
            row = self.db.execute(
                "SELECT * FROM workflow_preflights "
                "WHERE workflow_preflight_id = %s AND created_by = %s",
                (
                    existing_run["workflow_preflight_id"],
                    actor_context.actor_id,
                ),
            ).fetchone()
            if row is None:
                raise DreamLaunchApplicationError(
                    "DECK_RUNTIME_CONFIG_INVALID", 409
                )
            token = self._preflight_service._token_from_row(row)
            return self._preflight_service._row_to_model(row, token=token)
        preflight = await self._preflight_service.execute_preflight(
            values["deck_id"],
            values["binding_revision"],
            values["input_data"],
            values["actor_id"],
        )
        if preflight.status is not PreflightStatus.PASSED:
            raise DreamLaunchApplicationError(
                preflight.error_code or "DECK_RUNTIME_CONFIG_INVALID",
                409,
            )
        return preflight

    async def create_run(self, **values: Any) -> Any:
        actor_context = self._require_prepared_actor(values)
        # Preflight returns its authoritative row through a final SELECT.
        # psycopg opens a read transaction for that SELECT, while the run
        # service deliberately requires ownership of a clean write boundary.
        if self.db.in_transaction:
            self.db.rollback()
        return await self._run_service.create_run(
            values["preflight_id"],
            values["preflight_token"],
            values["idempotency_key"],
            values["source_thread_id"],
            actor_context,
            source_message_id=values["source_message_id"],
            source_message_time=values["source_message_time"],
        )

    def _require_prepared_actor(
        self,
        values: dict[str, Any],
    ) -> AuthenticatedActorContext:
        actor = self._actor_context
        if (
            actor is None
            or actor.actor_id != values["actor_id"]
            or actor.workspace_id != values["workspace_id"]
        ):
            raise PermissionError("Dream launch workflow scope mismatch")
        return actor

    def _existing_replay_run(
        self,
        request: StoryWorkspaceDreamLaunchCommand,
        actor: AuthenticatedActorContext,
    ) -> Any | None:
        run = self.db.execute(
            "SELECT run.*, preflight.deck_id AS preflight_deck_id "
            "FROM workflow_runs AS run "
            "JOIN workflow_preflights AS preflight "
            "ON preflight.workflow_preflight_id = run.workflow_preflight_id "
            "WHERE run.workspace_id = %s AND run.created_by = %s "
            "AND run.idempotency_key = %s",
            (actor.workspace_id, actor.actor_id, request.idempotency_key),
        ).fetchone()
        if run is None:
            return None

        source = self.db.execute(
            "SELECT message.id AS message_id, message.metadata, "
            "thread.id AS thread_id, thread.user_id, thread.deck_id, thread.voice_id "
            "FROM chat_message AS message JOIN chat_thread AS thread "
            "ON thread.id = message.thread_id "
            "WHERE message.id = %s AND thread.id = %s",
            (run["source_message_id"], run["source_voice_thread_id"]),
        ).fetchone()
        metadata = _decode_json_object(source["metadata"] if source else None)
        fingerprint_payload = {
            "deck_id": request.deck_id,
            "goal": request.goal,
        }
        if request.agent_id is not None:
            fingerprint_payload["agent_id"] = request.agent_id
        expected_fingerprint = "sha256:" + hashlib.sha256(
            _canonical_json(fingerprint_payload).encode("utf-8")
        ).hexdigest()
        valid = (
            source is not None
            and run["preflight_deck_id"] == request.deck_id
            and source["thread_id"] == run["source_voice_thread_id"]
            and source["message_id"] == run["source_message_id"]
            and str(source["user_id"]) == actor.actor_id
            and source["deck_id"] == request.deck_id
            and source["voice_id"] == request.agent_id
            and metadata.get("kind")
            == STORY_WORKSPACE_DREAM_LAUNCH_METADATA_KIND
            and metadata.get("actorId") == actor.actor_id
            and metadata.get("workspaceId") == actor.workspace_id
            and metadata.get("deckId") == request.deck_id
            and metadata.get("agentId") == request.agent_id
            and metadata.get("goal") == request.goal
            and metadata.get("idempotencyKey") == request.idempotency_key
            and metadata.get("requestFingerprint") == expected_fingerprint
        )
        if not valid:
            raise DreamLaunchIdempotencyConflict()
        return run


def build_dream_launch_application_service(
    db: Any,
    *,
    preflight_service: PreflightService,
    token_secret: bytes | str,
    runtime_port: DreamLaunchRuntimePort,
    turn_dispatcher: Callable[..., Any] | None = None,
    launch_task_registry: DreamLaunchTaskRegistry | None = None,
    dispatch_before_claim: Callable[[], Any] | None = None,
    platform_model_resolver: Callable[[int | str, str | None], str] = (
        resolve_platform_model_alias
    ),
) -> DreamLaunchApplicationService:
    """Compose the single Dream launch application service for one DB scope."""

    failure_recorder = DreamLaunchFailureRecorder(token_secret)
    selected_turn_dispatcher = turn_dispatcher
    if selected_turn_dispatcher is None:
        selected_turn_dispatcher = build_dream_agent_turn_dispatcher(
            failure_handler=failure_recorder.record,
            task_registry=launch_task_registry,
        )
    return DreamLaunchApplicationService(
        source_repository=DreamLaunchSourceRepository(db),
        workflow=DreamLaunchWorkflowOperationsAdapter(
            db,
            preflight_service=preflight_service,
            token_secret=token_secret,
            runtime_port=runtime_port,
            platform_model_resolver=platform_model_resolver,
        ),
        dispatcher=DreamLaunchEnvelopeDispatcher(
            db,
            turn_dispatcher=selected_turn_dispatcher,
            before_claim=dispatch_before_claim,
        ),
    )
