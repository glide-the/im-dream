# [Input] Frozen Admin Reflections consumers, worker-load snapshots, section RTA persistence, and Claude Agent ThreadFactory.
# [Output] Admin-backed Reflections task engine, durable ordered events, snapshot workspaces, and child Agent execution.
# [Pos] Reflections background execution node; Dream performs no Reflections SQL or schema management.
# [Sync] 2026-09-15: replace Dream database persistence with the sixteen-operation Admin Reflections boundary.
"""Run Reflections tasks from an immutable Admin worker snapshot."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Protocol
from uuid import uuid4

from claude_agent.service import ClaudeAgentRunRequest
from llm_json_parser import try_parse_json_array, try_parse_json_object
from reflections_config import get_section_config
from services.admin_data.client import AdminDataClient
from services.admin_data.errors import AdminDataError
from services.admin_data.reflection_section_persistence import AdminReflectionSectionPersistence
from services.admin_data.reflection_task_data import AdminReflectionsWorkerData
from services.admin_data.reflection_task_models import (
    ReflectionEventAppendInputDTO,
    ReflectionInsightInputDTO,
    ReflectionLaunchSnapshotDTO,
    ReflectionSectionBeginInputDTO,
    ReflectionSectionBeginOutputDTO,
    ReflectionSectionFinishInputDTO,
    ReflectionSectionTranscriptInputDTO,
    ReflectionTaskAdvanceInputDTO,
    ReflectionTaskLookupDTO,
    ReflectionWorkerLoadOutputDTO,
    reflection_event_id,
)
from services.admin_data.reflection_task_runtime import (
    prepare_reflection_memory_workspace,
    prepare_reflection_workspace_directory,
    reflection_workspace_root,
    validate_reflection_workspace_path,
    write_reflection_workspace_text,
)
from services.admin_data.session_projection_broker import SessionProjectionBrokerSettings
from services.admin_data.workflow_data import AdminWorkflowResolution

logger = logging.getLogger(__name__)

TERMINAL_TASK_STATUSES = {"COMPLETED", "PARTIAL_FAILED", "FAILED"}
_TERMINAL_EVENT_TYPES = {
    "reflection.task.completed",
    "reflection.task.partial_failed",
    "reflection.task.failed",
}
_VALID_PROMPT_FILES = frozenset({
    "WORKFLOW.md", "MEMORY_QUERY_PROMPT.md", "MEMORY_Distiller_PROMPT.md",
    "MEMORY_ANSWER_PROMPT.md", "DEFAULT_UPDATE_MEMORY_PROMPT.md",
})


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _request_id() -> str:
    return str(uuid4())


def _summary(error: BaseException) -> str:
    return (str(error).strip() or type(error).__name__)[:4_000]


@dataclass(slots=True)
class ReflectionTaskEvent:
    id: str
    task_id: str
    type: str
    sequence: int
    created_at: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "task_id": self.task_id, "type": self.type,
            "sequence": self.sequence, "created_at": self.created_at,
            "payload": self.payload,
        }

    def to_sse_frame(self) -> str:
        return (
            f"event: {self.type}\n"
            f"id: {self.id}\n"
            f"data: {json.dumps(self.to_dict(), ensure_ascii=False)}\n\n"
        )


class ReflectionTaskObserver(Protocol):
    async def on_event(self, event: ReflectionTaskEvent) -> None: ...


class TaskPersistenceObserver:
    """Append an allocated event through task-bound service identity."""

    required = True

    def __init__(self, worker: AdminReflectionsWorkerData) -> None:
        self._worker = worker

    async def on_event(self, event: ReflectionTaskEvent) -> None:
        await asyncio.to_thread(
            self._worker.append_event,
            ReflectionEventAppendInputDTO(
                task_id=event.task_id,
                event_id=event.id,
                sequence=event.sequence,
                event_type=event.type,
                created_at=event.created_at,
                payload=event.payload,
            ),
            _request_id(),
        )


class ReflectionEventBus:
    """Serialize event allocation, persistence order, replay, and fan-out."""

    def __init__(self, task_id: str, *, initial_sequence: int,
        observers: list[ReflectionTaskObserver] | None = None) -> None:
        if initial_sequence < 0 or initial_sequence > 2_147_483_647:
            raise ValueError("Invalid Reflections event high-water")
        self.task_id = task_id
        self._events: list[ReflectionTaskEvent] = []
        self._subscribers: list[asyncio.Queue[ReflectionTaskEvent | None]] = []
        self._done = False
        self._sequence = initial_sequence
        self._lock = asyncio.Lock()
        self._observers = list(observers or [])

    @property
    def is_done(self) -> bool:
        return self._done

    @property
    def sequence(self) -> int:
        return self._sequence

    async def publish(self, event_type: str,
        payload: dict[str, Any] | None = None) -> ReflectionTaskEvent:
        async with self._lock:
            if self._sequence >= 2_147_483_647:
                raise AdminDataError("REFLECTION_EVENT_SEQUENCE_EXHAUSTED", 409)
            sequence = self._sequence + 1
            event = ReflectionTaskEvent(
                id=reflection_event_id(self.task_id, sequence),
                task_id=self.task_id,
                type=event_type,
                sequence=sequence,
                created_at=_utcnow_iso(),
                payload=payload or {},
            )
            # Required persistence completes before the sequence becomes visible.
            # This keeps Admin high-water, replay, and SSE on one committed order.
            for observer in self._observers:
                if getattr(observer, "required", False):
                    await observer.on_event(event)
            self._sequence = sequence
            for observer in self._observers:
                if getattr(observer, "required", False):
                    continue
                try:
                    await observer.on_event(event)
                except Exception:
                    logger.exception(
                        "Reflection observer failed task_id=%s sequence=%s",
                        self.task_id, event.sequence,
                    )
            self._events.append(event)
            self._done = event_type in _TERMINAL_EVENT_TYPES
            for queue in list(self._subscribers):
                await queue.put(event)
            if self._done:
                for queue in list(self._subscribers):
                    await queue.put(None)
                self._subscribers.clear()
            return event

    async def subscribe(self,
        after_event_id: str | None = None) -> asyncio.Queue[ReflectionTaskEvent | None]:
        queue: asyncio.Queue[ReflectionTaskEvent | None] = asyncio.Queue()
        async with self._lock:
            replay = self._events
            if after_event_id:
                for index, event in enumerate(self._events):
                    if event.id == after_event_id:
                        replay = self._events[index + 1:]
                        break
            for event in replay:
                await queue.put(event)
            if self._done:
                await queue.put(None)
            else:
                self._subscribers.append(queue)
        return queue

    async def unsubscribe(self, token: object) -> None:
        async with self._lock:
            try:
                self._subscribers.remove(token)  # type: ignore[arg-type]
            except ValueError:
                pass

    async def read(self, token: object) -> AsyncIterator[ReflectionTaskEvent]:
        queue: asyncio.Queue[ReflectionTaskEvent | None] = token  # type: ignore[assignment]
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=15.0)
            except asyncio.TimeoutError:
                continue
            if event is None:
                return
            yield event


_BUSES: dict[str, ReflectionEventBus] = {}
_BUSES_LOCK = asyncio.Lock()
_RUNNING_TASKS: dict[str, asyncio.Task[None]] = {}
_TASK_LOCKS: dict[str, asyncio.Lock] = {}


async def _get_or_create_reflection_event_bus(task_id: str, *,
    initial_sequence: int, worker: AdminReflectionsWorkerData) -> ReflectionEventBus:
    async with _BUSES_LOCK:
        bus = _BUSES.get(task_id)
        if bus is None:
            bus = ReflectionEventBus(
                task_id,
                initial_sequence=initial_sequence,
                observers=[TaskPersistenceObserver(worker)],
            )
            _BUSES[task_id] = bus
        elif bus.sequence != initial_sequence:
            raise AdminDataError("REFLECTION_EVENT_HIGH_WATER_CONFLICT", 409)
        return bus


async def get_reflection_event_bus(task_id: str) -> ReflectionEventBus | None:
    async with _BUSES_LOCK:
        return _BUSES.get(task_id)


async def prepare_reflection_event_bus(task_id: str, *,
    worker: AdminReflectionsWorkerData) -> ReflectionEventBus:
    """Prepare a newly-created task bus before an explicit later start."""
    return await _get_or_create_reflection_event_bus(
        task_id, initial_sequence=0, worker=worker
    )


def _language_instruction(language: str) -> str:
    if language == "zh":
        return (
            "\n\n## Runtime Language Requirement\n"
            "The current frontend UI language is Simplified Chinese (`zh`).\n"
            "Write every user-facing `title`, `description`, and `evidence` value in Simplified Chinese.\n"
            "Keep JSON keys and enum values such as `confidence` in English."
        )
    return (
        "\n\n## Runtime Language Requirement\n"
        "The current frontend UI language is English (`en`).\n"
        "Write every user-facing `title`, `description`, and `evidence` value in English.\n"
        "Keep JSON keys and enum values such as `confidence` in English."
    )


def _session_metadata(session) -> dict[str, Any]:
    return {
        "sessionId": session.id,
        "date": str(session.created_at or session.updated_at or "")[:10],
        "title": str(session.name or "Untitled")[:120],
        "labels": list(session.labels),
    }


def _build_sessions_context(snapshot: ReflectionLaunchSnapshotDTO) -> str:
    lines = [
        "Full note bodies are intentionally omitted from this prompt.",
        "Use only these frozen session IDs in related_session_ids.",
        "Fetch needed content with mcp__user__get_sessions_range; its server projection is bound to this task snapshot.",
    ]
    lines.extend(
        json.dumps(_session_metadata(session), ensure_ascii=False)
        for session in snapshot.sessions
    )
    return "<sessions_context>\n" + "\n".join(lines) + "\n</sessions_context>"


def _effective_prompt_files(snapshot: ReflectionLaunchSnapshotDTO,
    section: str) -> dict[str, str]:
    static_files = dict(get_section_config(section).get("prompt_files", {}))
    custom = next(item for item in snapshot.custom_prompts if item.section == section)
    for filename, content in (custom.prompt_files() or {}).items():
        if (filename in _VALID_PROMPT_FILES and isinstance(content, str)
                and content.strip()):
            static_files[filename] = content.strip()
    return static_files


def _prepare_task_workspace(load: ReflectionWorkerLoadOutputDTO) -> Path:
    advertised = load.task.workspace_path
    if advertised is None:
        raise AdminDataError("REFLECTION_WORKSPACE_BINDING_CONFLICT", 409)
    memory_dir = prepare_reflection_memory_workspace(
        identifier=load.task.task_id,
        advertised_path=advertised,
    )
    procedural = prepare_reflection_workspace_directory(memory_dir / "procedural")
    write_reflection_workspace_text(
        memory_dir / "sessions_context.md",
        _build_sessions_context(load.launch_snapshot) + "\n",
    )
    write_reflection_workspace_text(
        memory_dir / "sessions_context.json",
        json.dumps(
            [_session_metadata(item) for item in load.launch_snapshot.sessions],
            ensure_ascii=False,
            indent=2,
        ),
    )
    for section in load.task.sections:
        section_dir = prepare_reflection_workspace_directory(memory_dir / section)
        for filename, content in _effective_prompt_files(
            load.launch_snapshot, section
        ).items():
            if filename not in _VALID_PROMPT_FILES or not isinstance(content, str):
                continue
            prompt = content.strip()
            if not prompt:
                continue
            if filename == "MEMORY_ANSWER_PROMPT.md":
                prompt += _language_instruction(load.launch_snapshot.language)
            write_reflection_workspace_text(section_dir / filename, prompt + "\n")
    write_reflection_workspace_text(
        procedural / "analysis_state.json",
        json.dumps(
            {
                "task_id": load.task.task_id,
                "sections": load.task.sections,
                "completed_sections": [],
                "failed_sections": [],
                "results_count": 0,
                "language": load.launch_snapshot.language,
            },
            ensure_ascii=False,
            indent=2,
        ),
    )
    return memory_dir


def _prepare_section_workspace(load: ReflectionWorkerLoadOutputDTO,
    begin: ReflectionSectionBeginOutputDTO) -> Path:
    root = reflection_workspace_root()
    advertised = str(Path(root) / begin.thread_id / "memory")
    memory_dir = prepare_reflection_memory_workspace(
        identifier=begin.thread_id,
        advertised_path=advertised,
    )
    for filename, content in _effective_prompt_files(
        load.launch_snapshot, begin.section
    ).items():
        if filename not in _VALID_PROMPT_FILES or not isinstance(content, str):
            continue
        prompt = content.strip()
        if not prompt:
            continue
        if filename == "MEMORY_ANSWER_PROMPT.md":
            prompt += _language_instruction(load.launch_snapshot.language)
        write_reflection_workspace_text(memory_dir / filename, prompt + "\n")
    procedural = prepare_reflection_workspace_directory(memory_dir / "procedural")
    write_reflection_workspace_text(
        procedural / "analysis_state.json",
        json.dumps({"completed": False, "results_count": 0}, indent=2),
    )
    return memory_dir


def _update_analysis_state(workspace_path: Path, **updates: Any) -> None:
    path = workspace_path / "procedural" / "analysis_state.json"
    validate_reflection_workspace_path(path)
    try:
        state = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, ValueError, TypeError):
        state = {}
    state.update(updates)
    write_reflection_workspace_text(
        path, json.dumps(state, ensure_ascii=False, indent=2)
    )


def _build_claude_agent_run_request(**kwargs: Any) -> Any:
    return ClaudeAgentRunRequest(**kwargs)


async def _run_claude_agent_stream(request: Any) -> AsyncIterator[str]:
    from agent_factory import claude_agent_thread_factory
    async for frame in claude_agent_thread_factory.run_streaming(request):
        yield frame


def _parse_json_array_from_text(text: str) -> list[dict[str, Any]] | None:
    _cleaned, value = try_parse_json_array(text)
    if value:
        parsed = [item for item in value if isinstance(item, dict)]
        return parsed or None
    _cleaned, obj = try_parse_json_object(text)
    return [obj] if obj else None


class ClaudeAgentReflectionsRunner:
    async def run_section(self, section: str, load: ReflectionWorkerLoadOutputDTO,
        begin: ReflectionSectionBeginOutputDTO, *, client: AdminDataClient,
        worker: AdminReflectionsWorkerData,
        session_broker_settings: SessionProjectionBrokerSettings,
    ) -> list[dict[str, Any]]:
        owner = AdminReflectionSectionPersistence(
            begin, load.launch_snapshot, client, worker,
            session_broker_settings=session_broker_settings,
        )
        try:
            owner.start()
            actor_id = owner.resolve_actor_id()
            memory_path = _prepare_section_workspace(load, begin)
            cfg = get_section_config(section)
            request = _build_claude_agent_run_request(
                user_id=actor_id,
                thread_id=begin.thread_id,
                resume=False,
                tool_choice="auto",
                max_turns=1000,
                message_id=str(uuid4()),
                message_parts=[{"type": "text", "text": self._build_user_message(load.launch_snapshot)}],
                system_prompt=self._build_system_prompt(
                    section, str(memory_path), str(cfg.get("display_name") or section)
                ),
                admin_workflow_resolution=AdminWorkflowResolution(actor_id, begin.thread_id, None),
                admin_turn_persistence=owner,
            )
            async for _frame in _run_claude_agent_stream(request):
                pass
        finally:
            owner.close()
        transcript = await asyncio.to_thread(
            worker.transcript,
            ReflectionSectionTranscriptInputDTO(task_id=load.task.task_id, section=section),
            _request_id(),
        )
        texts: list[str] = []
        for message in transcript.messages:
            if message.role != "assistant":
                continue
            for part in message.parts:
                if (isinstance(part, dict) and part.get("type") == "text"
                        and part.get("text")):
                    texts.append(str(part["text"]))
        for text in reversed(texts):
            parsed = _parse_json_array_from_text(text)
            if parsed is not None:
                return parsed
        return []

    @staticmethod
    def _build_system_prompt(section: str, memory_path: str, display: str) -> str:
        return (
            f'You are performing a "{display}" analysis for the Ink & Memory Reflections page.\n'
            f"Section key: {section}.\n"
            f"The procedural memory workspace has been initialised at: {memory_path}\n"
            "Follow memory/WORKFLOW.md for the analysis procedure.\n"
            "Output ONLY a JSON array as your final response."
        )

    @staticmethod
    def _build_user_message(snapshot: ReflectionLaunchSnapshotDTO) -> str:
        return (
            f"{_build_sessions_context(snapshot)}\n\n"
            "Read memory/WORKFLOW.md before analysis. Fetch only the frozen Sessions you need. "
            "Then output ONLY a JSON array."
        )


@dataclass(slots=True)
class _TaskContext:
    load: ReflectionWorkerLoadOutputDTO
    workspace: Path
    task_revision: int


class ReflectionsTaskEngine:
    def __init__(self, worker: AdminReflectionsWorkerData,
        client: AdminDataClient,
        session_broker_settings: SessionProjectionBrokerSettings,
        runner: ClaudeAgentReflectionsRunner | None = None) -> None:
        self.worker = worker
        self.client = client
        self.session_broker_settings = session_broker_settings
        self.runner = runner or ClaudeAgentReflectionsRunner()
        self._task_revision: int | None = None
        self._task_terminal = False

    async def run(self, task_id: str, *,
        load: ReflectionWorkerLoadOutputDTO | None = None) -> None:
        lock = _TASK_LOCKS.setdefault(task_id, asyncio.Lock())
        async with lock:
            current = load or await self._call(
                self.worker.worker_load, ReflectionTaskLookupDTO(task_id=task_id)
            )
            self._task_revision = current.task.revision
            if current.task.status in TERMINAL_TASK_STATUSES:
                try:
                    await self._ensure_report(task_id)
                except Exception:
                    logger.exception(
                        "Reflections report recovery failed task_id=%s", task_id
                    )
                finally:
                    if _RUNNING_TASKS.get(task_id) is asyncio.current_task():
                        _RUNNING_TASKS.pop(task_id, None)
                return
            bus = await _get_or_create_reflection_event_bus(
                task_id,
                initial_sequence=current.last_event_sequence,
                worker=self.worker,
            )
            try:
                context = await self._assemble_context(current, bus)
                await self._start_run(context, bus)
                outcome = await self._execute_sections(context, bus)
                await self._finalize(context, bus, outcome)
            except AdminDataError as error:
                logger.exception(
                    "Reflections Admin boundary failed task_id=%s code=%s",
                    task_id, error.code,
                )
                if not error.outcome_unknown and not self._task_terminal:
                    await self._fatal_fail(current, bus, error)
            except Exception as error:
                logger.exception("Reflections task failed task_id=%s", task_id)
                if not self._task_terminal:
                    await self._fatal_fail(current, bus, error)
            finally:
                if _RUNNING_TASKS.get(task_id) is asyncio.current_task():
                    _RUNNING_TASKS.pop(task_id, None)

    async def _call(self, method, input_dto):
        return await asyncio.to_thread(method, input_dto, _request_id())

    async def _assemble_context(self, load: ReflectionWorkerLoadOutputDTO,
        bus: ReflectionEventBus) -> _TaskContext:
        if load.last_event_sequence == 0:
            await bus.publish(
                "reflection.task.created",
                {"task_id": load.task.task_id, "sections": load.task.sections},
            )
        workspace = _prepare_task_workspace(load)
        revision = load.task.revision
        if load.task.status == "ASSEMBLING":
            advanced = await self._call(
                self.worker.advance,
                ReflectionTaskAdvanceInputDTO(
                    task_id=load.task.task_id,
                    action="context-ready",
                    expected_revision=revision,
                ),
            )
            revision = advanced.revision
            self._task_revision = revision
            await bus.publish(
                "reflection.context.ready",
                {"workspace_path": str(workspace),
                 "session_count": len(load.launch_snapshot.sessions)},
            )
        return _TaskContext(load, workspace, revision)

    async def _start_run(self, context: _TaskContext,
        bus: ReflectionEventBus) -> None:
        if context.load.task.status in {"ASSEMBLING", "QUEUED"}:
            advanced = await self._call(
                self.worker.advance,
                ReflectionTaskAdvanceInputDTO(
                    task_id=context.load.task.task_id,
                    action="run-started",
                    expected_revision=context.task_revision,
                ),
            )
            context.task_revision = advanced.revision
            self._task_revision = advanced.revision
            await bus.publish(
                "reflection.task.started", {"started_at": _utcnow_iso()}
            )

    async def _execute_sections(self, context: _TaskContext,
        bus: ReflectionEventBus) -> dict[str, Any]:
        completed: list[str] = []
        failed: list[str] = []
        total_results = 0
        states = {item.section: item for item in context.load.task.section_states}
        for section in context.load.task.sections:
            state = states[section]
            if state.status == "COMPLETED":
                completed.append(section)
                total_results += state.result_count
                continue
            if state.status == "FAILED":
                failed.append(section)
                continue
            begin: ReflectionSectionBeginOutputDTO | None = None
            try:
                begin = await self._call(
                    self.worker.begin,
                    ReflectionSectionBeginInputDTO(
                        task_id=context.load.task.task_id,
                        section=section,
                        expected_revision=state.revision,
                    ),
                )
                await bus.publish("reflection.section.started", {"section": section})
                raw = await self.runner.run_section(
                    section, context.load, begin,
                    client=self.client,
                    worker=self.worker,
                    session_broker_settings=self.session_broker_settings,
                )
                results = self._validate_results(raw, context.load.launch_snapshot)
                finished = await self._call(
                    self.worker.finish,
                    ReflectionSectionFinishInputDTO(
                        task_id=context.load.task.task_id,
                        section=section,
                        expected_revision=begin.revision,
                        outcome="completed",
                        results=results,
                    ),
                )
                completed.append(section)
                total_results += finished.result_count
                await bus.publish(
                    "reflection.section.completed",
                    {"section": section, "result_count": finished.result_count},
                )
            except AdminDataError as error:
                if error.outcome_unknown:
                    raise
                failed.append(section)
                await self._finish_known_failure(
                    context.load.task.task_id, section, begin, error
                )
                await bus.publish(
                    "reflection.section.failed",
                    {"section": section, "error_code": error.code,
                     "message": _summary(error),
                     "retryable": error.status_code >= 500},
                )
            except Exception as error:
                failed.append(section)
                await self._finish_known_failure(
                    context.load.task.task_id, section, begin, error
                )
                await bus.publish(
                    "reflection.section.failed",
                    {"section": section, "error_code": "SECTION_FAILED",
                     "message": _summary(error), "retryable": True},
                )
            _update_analysis_state(
                context.workspace,
                completed_sections=completed,
                failed_sections=failed,
                results_count=total_results,
            )
        return {
            "completed_sections": completed,
            "failed_sections": failed,
            "total_results": total_results,
        }

    async def _finish_known_failure(self, task_id: str, section: str,
        begin: ReflectionSectionBeginOutputDTO | None,
        error: BaseException) -> None:
        if begin is None:
            return
        await self._call(
            self.worker.finish,
            ReflectionSectionFinishInputDTO(
                task_id=task_id,
                section=section,
                expected_revision=begin.revision,
                outcome="failed",
                error_summary=_summary(error),
            ),
        )

    async def _finalize(self, context: _TaskContext,
        bus: ReflectionEventBus, outcome: dict[str, Any]) -> None:
        failed = outcome["failed_sections"]
        advanced = await self._call(
            self.worker.advance,
            ReflectionTaskAdvanceInputDTO(
                task_id=context.load.task.task_id,
                action="finalize",
                expected_revision=context.task_revision,
                error_summary=(
                    None if not failed else f"Failed sections: {', '.join(failed)}"
                ),
            ),
        )
        self._task_revision = advanced.revision
        self._task_terminal = advanced.status in TERMINAL_TASK_STATUSES
        await self._ensure_report(context.load.task.task_id)
        event_type = {
            "COMPLETED": "reflection.task.completed",
            "PARTIAL_FAILED": "reflection.task.partial_failed",
            "FAILED": "reflection.task.failed",
        }[advanced.status]
        await bus.publish(
            event_type,
            {"completed_sections": outcome["completed_sections"],
             "failed_sections": failed,
             "result_count": outcome["total_results"]},
        )

    async def _ensure_report(self, task_id: str) -> None:
        await self._call(
            self.worker.ensure_report, ReflectionTaskLookupDTO(task_id=task_id)
        )

    async def _fatal_fail(self, load: ReflectionWorkerLoadOutputDTO,
        bus: ReflectionEventBus, error: BaseException) -> None:
        try:
            if self._task_revision is None:
                raise AdminDataError("REFLECTION_TASK_REVISION_UNAVAILABLE", 409)
            await self._call(
                self.worker.advance,
                ReflectionTaskAdvanceInputDTO(
                    task_id=load.task.task_id,
                    action="fatal-fail",
                    expected_revision=self._task_revision,
                    error_summary=_summary(error),
                ),
            )
            await bus.publish(
                "reflection.task.failed",
                {"error_code": getattr(error, "code", "TASK_FAILED"),
                 "message": _summary(error), "retryable": True},
            )
        except Exception:
            logger.exception(
                "Reflections fatal-fail persistence failed task_id=%s",
                load.task.task_id,
            )

    @staticmethod
    def _validate_results(results: list[dict[str, Any]],
        snapshot: ReflectionLaunchSnapshotDTO) -> list[ReflectionInsightInputDTO]:
        session_ids = {item.id for item in snapshot.sessions}
        validated: list[ReflectionInsightInputDTO] = []
        for item in results:
            raw_related = item.get("related_session_ids", [])
            related = list(dict.fromkeys(
                str(value) for value in raw_related
                if str(value) in session_ids
            )) if isinstance(raw_related, list) else []
            if not related:
                continue
            confidence = item.get("confidence")
            if confidence not in {"high", "medium", "low"}:
                confidence = "low"
            validated.append(ReflectionInsightInputDTO(
                title=str(item.get("title") or "Insight")[:200],
                description=str(item.get("description") or "")[:4_000],
                related_session_ids=related,
                evidence=str(item.get("evidence") or "")[:2_000],
                confidence=confidence,
            ))
        return validated


async def start_reflections_task(task_id: str, *,
    worker: AdminReflectionsWorkerData, client: AdminDataClient,
    session_broker_settings: SessionProjectionBrokerSettings) -> None:
    """Load the Admin snapshot once, then start one local task owner."""
    lock = _TASK_LOCKS.setdefault(task_id, asyncio.Lock())
    async with lock:
        existing = _RUNNING_TASKS.get(task_id)
        if existing is not None and not existing.done():
            return
        load = await asyncio.to_thread(
            worker.worker_load,
            ReflectionTaskLookupDTO(task_id=task_id),
            _request_id(),
        )
        if load.task.status not in TERMINAL_TASK_STATUSES:
            await _get_or_create_reflection_event_bus(
                task_id,
                initial_sequence=load.last_event_sequence,
                worker=worker,
            )
        engine = ReflectionsTaskEngine(
            worker, client, session_broker_settings
        )
        task = asyncio.create_task(
            engine.run(task_id, load=load), name=f"reflections-task-{task_id}"
        )
        _RUNNING_TASKS[task_id] = task


__all__ = [
    "ClaudeAgentReflectionsRunner",
    "ReflectionEventBus",
    "ReflectionTaskEvent",
    "ReflectionsTaskEngine",
    "TaskPersistenceObserver",
    "get_reflection_event_bus",
    "prepare_reflection_event_bus",
    "start_reflections_task",
]
