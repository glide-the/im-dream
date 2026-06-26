# [Input] database.py, reflections_config.py, user sessions, and Reflections prompt config.
# [Output] Persistence-first Reflections-agent task engine, EventBus, Observer, and
#          deterministic section runner for backend async Reflections tasks.
# [Pos] reflections-agent runtime node in backend
# [Sync] 2026-06-25: implement first-release Reflections-agent flow: task/result
#                    persistence, four-phase task engine, in-memory EventBus, and
#                    TaskPersistenceObserver.
"""Backend Reflections-agent runtime.

This module intentionally implements the first-release design only:
- DB-backed ``reflection_task`` / ``reflection_result`` are the truth source.
- A lightweight Task Engine owns the four lifecycle phases.
- In-memory EventBus provides same-process realtime status fan-out.
- Observer is minimal; audio/video consumers are not implemented here.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, AsyncIterator, Protocol

import database
from reflections_config import get_section_config, list_sections

logger = logging.getLogger(__name__)

VALID_TASK_STATUSES = {
    "CREATED",
    "ASSEMBLING",
    "QUEUED",
    "RUNNING",
    "COMPLETED",
    "PARTIAL_FAILED",
    "FAILED",
}

TERMINAL_TASK_STATUSES = {"COMPLETED", "PARTIAL_FAILED", "FAILED"}


def _utcnow_iso() -> str:
    """Return a compact UTC ISO timestamp with a trailing Z."""

    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(slots=True)
class ReflectionTaskEvent:
    """Task-scoped event envelope used by SSE and Observers."""

    id: str
    task_id: str
    type: str
    sequence: int
    created_at: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "type": self.type,
            "sequence": self.sequence,
            "created_at": self.created_at,
            "payload": self.payload,
        }

    def to_sse_frame(self) -> str:
        return (
            f"event: {self.type}\n"
            f"id: {self.id}\n"
            f"data: {json.dumps(self.to_dict(), ensure_ascii=False)}\n\n"
        )


class ReflectionTaskObserver(Protocol):
    """Observer contract for Reflections task events."""

    async def on_event(self, event: ReflectionTaskEvent) -> None: ...


class TaskPersistenceObserver:
    """Persist task events for audit and replay support."""

    async def on_event(self, event: ReflectionTaskEvent) -> None:
        database.append_reflection_task_event(
            event.task_id,
            event.type,
            event.payload,
            event_id=event.id,
            sequence=event.sequence,
            created_at=event.created_at,
        )


class ReflectionEventBus:
    """Task-scoped in-memory EventBus with replay and fan-out semantics."""

    def __init__(self, task_id: str, observers: list[ReflectionTaskObserver] | None = None) -> None:
        self.task_id = task_id
        self._events: list[ReflectionTaskEvent] = []
        self._subscribers: list[asyncio.Queue[ReflectionTaskEvent | None]] = []
        self._done = False
        self._sequence = 0
        self._lock = asyncio.Lock()
        self._observers = list(observers or [])

    @property
    def is_done(self) -> bool:
        return self._done

    async def publish(self, event_type: str, payload: dict[str, Any] | None = None) -> ReflectionTaskEvent:
        async with self._lock:
            self._sequence += 1
            event = ReflectionTaskEvent(
                id=f"evt_{self._sequence:06d}",
                task_id=self.task_id,
                type=event_type,
                sequence=self._sequence,
                created_at=_utcnow_iso(),
                payload=payload or {},
            )
            self._events.append(event)
            if event_type in {
                "reflection.task.completed",
                "reflection.task.partial_failed",
                "reflection.task.failed",
            }:
                self._done = True
            for queue in list(self._subscribers):
                await queue.put(event)
            if self._done:
                for queue in list(self._subscribers):
                    await queue.put(None)
                self._subscribers.clear()

        for observer in self._observers:
            try:
                await observer.on_event(event)
            except Exception:
                logger.exception("Reflection observer failed for event %s", event.type)
        return event

    async def subscribe(self, after_event_id: str | None = None) -> asyncio.Queue[ReflectionTaskEvent | None]:
        queue: asyncio.Queue[ReflectionTaskEvent | None] = asyncio.Queue()
        async with self._lock:
            replay = self._events
            if after_event_id:
                for index, event in enumerate(self._events):
                    if event.id == after_event_id:
                        replay = self._events[index + 1 :]
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
                break
            yield event


_BUSES: dict[str, ReflectionEventBus] = {}
_BUSES_LOCK = asyncio.Lock()
_RUNNING_TASKS: dict[str, asyncio.Task[None]] = {}
_TASK_LOCKS: dict[str, asyncio.Lock] = {}


def _workspace_root() -> Path:
    agent_cwd = os.environ.get("AGENT_CWD", "").strip()
    if agent_cwd:
        return Path(agent_cwd)
    return Path(tempfile.gettempdir()) / "ink-agent-workspaces"


async def get_or_create_reflection_event_bus(task_id: str) -> ReflectionEventBus:
    async with _BUSES_LOCK:
        bus = _BUSES.get(task_id)
        if bus is None:
            bus = ReflectionEventBus(task_id, observers=[TaskPersistenceObserver()])
            _BUSES[task_id] = bus
        return bus


async def get_reflection_event_bus(task_id: str) -> ReflectionEventBus | None:
    async with _BUSES_LOCK:
        return _BUSES.get(task_id)


def _effective_prompt_files(user_id: int, section: str) -> dict[str, str]:
    static_cfg = get_section_config(section)
    static_files: dict[str, str] = static_cfg.get("prompt_files", {})
    user_files = database.get_reflections_section_config(user_id, section)
    if not user_files:
        return dict(static_files)
    merged = dict(static_files)
    for filename, content in user_files.items():
        if isinstance(content, str) and content.strip():
            merged[filename] = content.strip()
    return merged


def _normalize_task_language(language: Any) -> tuple[str, str]:
    code = str(language or "en").strip().lower()
    if code.startswith("zh"):
        return "zh", "Simplified Chinese"
    return "en", "English"


def _language_instruction(language: Any) -> str:
    code, label = _normalize_task_language(language)
    if code == "zh":
        return (
            "\n\n## Runtime Language Requirement\n"
            "The current frontend UI language is Simplified Chinese (`zh`).\n"
            "Write every user-facing `title`, `description`, and `evidence` value in Simplified Chinese.\n"
            "Keep JSON keys and enum values such as `confidence` in English."
        )
    return (
        "\n\n## Runtime Language Requirement\n"
        f"The current frontend UI language is {label} (`en`).\n"
        "Write every user-facing `title`, `description`, and `evidence` value in English.\n"
        "Keep JSON keys and enum values such as `confidence` in English."
    )


def _build_sessions_context(sessions: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for session in sessions:
        text = (session.get("text") or session.get("first_line") or "").strip()
        if not text:
            continue
        parts.append(
            "\n".join(
                [
                    f"Session ID: {session.get('id')}",
                    f"Name: {session.get('name') or 'Untitled'}",
                    f"Created: {session.get('created_at') or ''}",
                    f"Updated: {session.get('updated_at') or ''}",
                    "Text:",
                    text,
                ]
            )
        )
    return "\n\n---\n\n".join(parts)


def _prepare_workspace(task_id: str, user_id: int, sections: list[str], sessions: list[dict[str, Any]], language: str = "en") -> str:
    root = _workspace_root().resolve()
    task_dir = (root / task_id).resolve()
    if not str(task_dir).startswith(str(root)):
        raise ValueError("task workspace resolves outside workspace root")

    memory_dir = task_dir / "memory"
    procedural_dir = memory_dir / "procedural"
    procedural_dir.mkdir(parents=True, exist_ok=True)

    sessions_context = _build_sessions_context(sessions)
    (memory_dir / "sessions_context.md").write_text(sessions_context + "\n", encoding="utf-8")
    (memory_dir / "sessions_context.json").write_text(
        json.dumps(sessions, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    language_code, language_label = _normalize_task_language(language)
    (memory_dir / "language_context.md").write_text(
        f"# Runtime Language Context\n\nFrontend UI language: {language_label} (`{language_code}`).\n"
        "All user-facing Reflections output should follow this language unless a section prompt says otherwise.\n",
        encoding="utf-8",
    )

    for section in sections:
        section_dir = memory_dir / section
        section_dir.mkdir(exist_ok=True)
        for filename, content in _effective_prompt_files(user_id, section).items():
            if isinstance(content, str) and content.strip():
                prompt_content = content.strip()
                if filename == "MEMORY_ANSWER_PROMPT.md":
                    prompt_content += _language_instruction(language_code)
                (section_dir / filename).write_text(prompt_content + "\n", encoding="utf-8")

    (procedural_dir / "analysis_state.json").write_text(
        json.dumps(
            {
                "task_id": task_id,
                "sections": sections,
                "completed_sections": [],
                "failed_sections": [],
                "results_count": 0,
                "language": language_code,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return str(memory_dir)


def _update_analysis_state(workspace_path: str, **updates: Any) -> None:
    state_path = Path(workspace_path) / "procedural" / "analysis_state.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    except Exception:
        state = {}
    state.update(updates)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


class HeuristicReflectionsRunner:
    """Deterministic local runner used for first-release functional behavior.

    It keeps tests and local runs independent of external LLM credentials while
    preserving the JSON result contract expected by the Reflections UI.
    """

    async def run_section(self, section: str, sessions: list[dict[str, Any]], language: str = "en") -> list[dict[str, Any]]:
        await asyncio.sleep(0)
        source_sessions = [s for s in sessions if (s.get("text") or "").strip()]
        related_ids = [str(s.get("id")) for s in source_sessions[:3] if s.get("id")]
        evidence = self._evidence(source_sessions)
        if not related_ids:
            return []
        if _normalize_task_language(language)[0] == "zh":
            title_map = {
                "echoes": "反复出现的情绪回响",
                "traits": "稳定的自我觉察",
                "patterns": "可识别的写作节律",
            }
            description_map = {
                "echoes": "这些笔记里反复出现的表达，显示出一个持续回到内心的情绪主题。",
                "traits": "这些记录呈现出一种稳定倾向：认真观察自己的感受、选择与行动。",
                "patterns": "写作历史显示出一种可识别的反思习惯与回应节奏。",
            }
        else:
            title_map = {
                "echoes": "Recurring Emotional Echo",
                "traits": "Reflective Self Awareness",
                "patterns": "Writing Rhythm Pattern",
            }
            description_map = {
                "echoes": "Repeated journal language suggests a recurring emotional theme across the selected notes.",
                "traits": "The notes show a stable tendency to observe feelings and choices with care.",
                "patterns": "The writing history indicates a recognizable reflective routine and response pattern.",
            }
        return [
            {
                "title": title_map.get(section, f"{section.title()} Insight"),
                "description": description_map.get(section, "A recurring signal was found in the selected writing sessions."),
                "related_session_ids": related_ids,
                "evidence": evidence,
                "confidence": "medium" if len(related_ids) >= 2 else "low",
            }
        ]

    @staticmethod
    def _evidence(sessions: list[dict[str, Any]]) -> str:
        for session in sessions:
            text = re.sub(r"\s+", " ", (session.get("text") or "").strip())
            if text:
                return text[:240]
        return "No strong textual evidence available."


class ReflectionsTaskEngine:
    """Four-phase backend Task Engine for Reflections analysis."""

    def __init__(self, runner: HeuristicReflectionsRunner | None = None) -> None:
        self.runner = runner or HeuristicReflectionsRunner()

    async def run(self, task_id: str) -> None:
        lock = _TASK_LOCKS.setdefault(task_id, asyncio.Lock())
        async with lock:
            bus = await get_or_create_reflection_event_bus(task_id)
            task = database.get_reflection_task(task_id)
            if not task:
                return
            if task.get("status") in TERMINAL_TASK_STATUSES:
                return
            try:
                context = await self._assemble_context(task, bus)
                await self._create_executor(context, bus)
                outcome = await self._execute_task(context, bus)
                await self._finalize_task(context, bus, outcome)
            except Exception as exc:
                logger.exception("Reflections task failed task_id=%s", task_id)
                database.update_reflection_task_status(
                    task_id,
                    "FAILED",
                    error_summary=str(exc),
                    completed_at=_utcnow_iso(),
                )
                await bus.publish(
                    "reflection.task.failed",
                    {"error_code": "TASK_FAILED", "message": str(exc), "retryable": True},
                )
            finally:
                _RUNNING_TASKS.pop(task_id, None)

    async def _assemble_context(self, task: dict[str, Any], bus: ReflectionEventBus) -> dict[str, Any]:
        task_id = task["id"]
        user_id = int(task["user_id"])
        database.update_reflection_task_status(task_id, "ASSEMBLING")
        await bus.publish("reflection.task.created", {"task_id": task_id, "sections": task.get("sections", [])})

        snapshot = task.get("input_snapshot") or {}
        start_date = snapshot.get("start_date")
        end_date = snapshot.get("end_date")
        language = snapshot.get("language") or "en"
        sessions = database.list_sessions_in_range(user_id, start_date, end_date, include_text=True)
        session_ids = snapshot.get("session_ids") or []
        if session_ids:
            allowed = {str(sid) for sid in session_ids}
            sessions = [s for s in sessions if str(s.get("id")) in allowed]

        sections = [s for s in (task.get("sections") or []) if s in set(list_sections())]
        workspace_path = _prepare_workspace(task_id, user_id, sections, sessions, language)
        database.update_reflection_task_status(
            task_id,
            "QUEUED",
            workspace_path=workspace_path,
            input_snapshot={**snapshot, "language": _normalize_task_language(language)[0], "session_count": len(sessions)},
        )
        await bus.publish(
            "reflection.context.ready",
            {"workspace_path": workspace_path, "session_count": len(sessions)},
        )
        return {"task_id": task_id, "user_id": user_id, "sections": sections, "sessions": sessions, "workspace_path": workspace_path, "language": _normalize_task_language(language)[0]}

    async def _create_executor(self, context: dict[str, Any], bus: ReflectionEventBus) -> None:
        database.update_reflection_task_status(
            context["task_id"],
            "RUNNING",
            started_at=_utcnow_iso(),
        )
        await bus.publish("reflection.task.started", {"started_at": _utcnow_iso()})

    async def _execute_task(self, context: dict[str, Any], bus: ReflectionEventBus) -> dict[str, Any]:
        completed: list[str] = []
        failed: list[str] = []
        total_results = 0
        for section in context["sections"]:
            await bus.publish("reflection.section.started", {"section": section})
            try:
                results = await self.runner.run_section(section, context["sessions"], context.get("language", "en"))
                validated = self._validate_results(results, section, context["sessions"])
                database.replace_reflection_section_results(
                    context["task_id"], context["user_id"], section, validated
                )
                completed.append(section)
                total_results += len(validated)
                _update_analysis_state(
                    context["workspace_path"],
                    completed_sections=completed,
                    failed_sections=failed,
                    results_count=total_results,
                )
                await bus.publish(
                    "reflection.section.completed",
                    {"section": section, "result_count": len(validated)},
                )
            except Exception as exc:
                failed.append(section)
                _update_analysis_state(
                    context["workspace_path"],
                    completed_sections=completed,
                    failed_sections=failed,
                    last_error=str(exc),
                )
                await bus.publish(
                    "reflection.section.failed",
                    {"section": section, "error_code": "SECTION_FAILED", "message": str(exc), "retryable": True},
                )
        return {"completed_sections": completed, "failed_sections": failed, "total_results": total_results}

    async def _finalize_task(self, context: dict[str, Any], bus: ReflectionEventBus, outcome: dict[str, Any]) -> None:
        completed = outcome["completed_sections"]
        failed = outcome["failed_sections"]
        if completed and failed:
            status = "PARTIAL_FAILED"
            event_type = "reflection.task.partial_failed"
        elif completed:
            status = "COMPLETED"
            event_type = "reflection.task.completed"
        else:
            status = "FAILED"
            event_type = "reflection.task.failed"
        error_summary = None if status == "COMPLETED" else f"Failed sections: {', '.join(failed) or 'all'}"
        database.update_reflection_task_status(
            context["task_id"],
            status,
            error_summary=error_summary,
            completed_at=_utcnow_iso(),
        )
        await bus.publish(
            event_type,
            {
                "completed_sections": completed,
                "failed_sections": failed,
                "result_count": outcome["total_results"],
            },
        )

    @staticmethod
    def _validate_results(results: list[dict[str, Any]], section: str, sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        session_ids = {str(s.get("id")) for s in sessions if s.get("id")}
        validated: list[dict[str, Any]] = []
        for item in results:
            related = [str(sid) for sid in item.get("related_session_ids", []) if str(sid) in session_ids]
            if not related:
                continue
            confidence = item.get("confidence") if item.get("confidence") in {"high", "medium", "low"} else "low"
            validated.append(
                {
                    "section": section,
                    "title": str(item.get("title") or f"{section.title()} Insight")[:200],
                    "description": str(item.get("description") or "")[:4000],
                    "related_session_ids": related,
                    "evidence": str(item.get("evidence") or "")[:2000],
                    "confidence": confidence,
                }
            )
        return validated


async def start_reflections_task(task_id: str) -> None:
    """Start a task in the background if it is not already running."""
    existing = _RUNNING_TASKS.get(task_id)
    if existing and not existing.done():
        return
    await get_or_create_reflection_event_bus(task_id)
    task = asyncio.create_task(ReflectionsTaskEngine().run(task_id))
    _RUNNING_TASKS[task_id] = task


def create_reflections_task(user_id: int, sections: list[str] | None = None, input_snapshot: dict[str, Any] | None = None) -> str:
    valid_sections = set(list_sections())
    normalized = [s for s in (sections or list_sections()) if s in valid_sections]
    if not normalized:
        normalized = list(list_sections())
    return database.create_reflection_task(
        user_id=user_id,
        sections=normalized,
        input_snapshot=input_snapshot or {},
        agent_contract_version="reflections-agent-v1",
    )
