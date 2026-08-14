"""Project Claude Code subagent transcripts into a thread-scoped API payload.

The Claude runtime owns the canonical transcript files under the server-owned
thread workspace. This module reads only the small metadata files plus a
bounded tail of each JSONL transcript. It returns assistant updates and tool
names for a safe execution timeline; raw prompts, thinking, tool inputs,
successful tool outputs, and internal paths are never returned to the browser.
"""

from __future__ import annotations

import json
import hashlib
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


_DEFAULT_MAX_ITEMS = 200
_DEFAULT_TRANSCRIPT_SCAN_BYTES = 512 * 1024
_SUMMARY_MAX_CHARS = 600
_ACTIVITY_MAX_ITEMS = 80
_MESSAGE_MAX_ITEMS = 120
_MESSAGE_TEXT_MAX_CHARS = 12_000
_TOOL_SUMMARY_MAX_CHARS = 2_000
_PROJECTION_VERSION = 2
_SENSITIVE_KEY_RE = re.compile(
    r"(?:authorization|cookie|password|passwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key)",
    re.IGNORECASE,
)
_INTERRUPTED_MARKERS = (
    "[Request interrupted by user]",
    "request interrupted by user",
)


def _positive_env_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, "") or default)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _compact_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    compact = re.sub(r"\s+", " ", value).strip()
    if not compact:
        return None
    return compact[:_SUMMARY_MAX_CHARS]


def _compact_markdown(value: object) -> str | None:
    """Bound assistant Markdown without flattening its block structure."""

    if not isinstance(value, str):
        return None
    compact = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not compact:
        return None
    return compact[:_SUMMARY_MAX_CHARS]


def _bounded_markdown(value: object, limit: int = _MESSAGE_TEXT_MAX_CHARS) -> tuple[str | None, bool]:
    if not isinstance(value, str):
        return None, False
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return None, False
    return normalized[:limit], len(normalized) > limit


def _sanitize_tool_value(value: object, *, depth: int = 0) -> object:
    """Return a JSON-safe, bounded tool summary with credential-like fields redacted."""

    if depth >= 4:
        return "…"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:_TOOL_SUMMARY_MAX_CHARS]
    if isinstance(value, list):
        return [_sanitize_tool_value(item, depth=depth + 1) for item in value[:20]]
    if isinstance(value, dict):
        sanitized: dict[str, object] = {}
        for raw_key, item in list(value.items())[:30]:
            key = str(raw_key)
            sanitized[key] = "[redacted]" if _SENSITIVE_KEY_RE.search(key) else _sanitize_tool_value(item, depth=depth + 1)
        return sanitized
    return str(value)[:_TOOL_SUMMARY_MAX_CHARS]


def _tool_summary(value: object) -> tuple[str | None, bool]:
    if value is None:
        return None, False
    try:
        serialized = json.dumps(_sanitize_tool_value(value), ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        serialized = str(value)
    serialized = serialized.strip()
    if not serialized:
        return None, False
    return serialized[:_TOOL_SUMMARY_MAX_CHARS], len(serialized) > _TOOL_SUMMARY_MAX_CHARS


def _stable_message_id(agent_id: str, record: dict[str, Any] | None, block_index: int, kind: str, text: str | None) -> str:
    record_id = record.get("uuid") if isinstance(record, dict) else None
    seed = "|".join(
        (
            agent_id,
            str(record_id or (record or {}).get("timestamp") or "meta"),
            str(block_index),
            kind,
            text or "",
        )
    )
    return f"message-{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:16]}"


def _project_messages(
    records: list[dict[str, Any]],
    meta: dict[str, Any],
    *,
    agent_id: str,
    status: str,
    terminal_error: str | None,
    transcript_truncated: bool,
) -> tuple[list[dict[str, Any]], bool]:
    """Project a safe, read-only conversation timeline from a subagent transcript."""

    messages: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    tool_names: dict[str, str] = {}
    sequence = 0
    item_limit_hit = False

    def append_message(
        kind: str,
        *,
        record: dict[str, Any] | None = None,
        block_index: int = 0,
        text: str | None = None,
        message_status: str | None = None,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
        input_text: str | None = None,
        output_text: str | None = None,
        redacted: bool = False,
        truncated: bool = False,
    ) -> None:
        nonlocal sequence, item_limit_hit
        if len(messages) >= _MESSAGE_MAX_ITEMS:
            item_limit_hit = True
            return
        message_id = _stable_message_id(agent_id, record, block_index, kind, text or input_text or output_text)
        if message_id in seen_ids:
            return
        seen_ids.add(message_id)
        sequence += 1
        messages.append(
            {
                "id": message_id,
                "sequence": sequence,
                "kind": kind,
                "timestamp": record.get("timestamp") if isinstance(record, dict) and isinstance(record.get("timestamp"), str) else None,
                "text": text,
                "status": message_status,
                "tool_name": tool_name,
                "tool_call_id": tool_call_id,
                "input": input_text,
                "output": output_text,
                "redacted": redacted,
                "truncated": truncated,
            }
        )

    prompt, prompt_truncated = _bounded_markdown(meta.get("prompt"))
    if not prompt:
        for record in records:
            role = (record.get("message") or {}).get("role") if isinstance(record.get("message"), dict) else None
            if role != "user":
                continue
            for block in _iter_content_blocks(record):
                if block.get("type") != "text":
                    continue
                candidate = str(block.get("text") or "")
                if any(marker.lower() in candidate.lower() for marker in _INTERRUPTED_MARKERS):
                    continue
                prompt, prompt_truncated = _bounded_markdown(candidate)
                if prompt:
                    break
            if prompt:
                break
    if prompt:
        append_message("task", text=prompt, truncated=prompt_truncated)

    assistant_message_indexes: list[int] = []
    for record in records:
        message = record.get("message")
        role = message.get("role") if isinstance(message, dict) else None
        for block_index, block in enumerate(_iter_content_blocks(record)):
            block_type = block.get("type")
            if role == "assistant" and block_type == "text":
                text, was_truncated = _bounded_markdown(block.get("text"))
                if text:
                    assistant_message_indexes.append(len(messages))
                    append_message("assistant", record=record, block_index=block_index, text=text, truncated=was_truncated)
                continue
            if role == "assistant" and block_type == "tool_use":
                tool_name = _compact_text(block.get("name")) or "Tool"
                tool_call_id = block.get("id") if isinstance(block.get("id"), str) else None
                if tool_call_id:
                    tool_names[tool_call_id] = tool_name
                input_text, input_truncated = _tool_summary(block.get("input"))
                append_message(
                    "tool_call",
                    record=record,
                    block_index=block_index,
                    message_status="started",
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                    input_text=input_text,
                    redacted=bool(input_text and "[redacted]" in input_text),
                    truncated=input_truncated,
                )
                continue
            if role == "user" and block_type == "tool_result":
                tool_call_id = block.get("tool_use_id") if isinstance(block.get("tool_use_id"), str) else None
                output_text, output_truncated = _tool_summary(block.get("content"))
                append_message(
                    "tool_result",
                    record=record,
                    block_index=block_index,
                    message_status="failed" if block.get("is_error") is True else "completed",
                    tool_name=tool_names.get(tool_call_id or "") or "Tool",
                    tool_call_id=tool_call_id,
                    output_text=output_text,
                    redacted=bool(output_text and "[redacted]" in output_text),
                    truncated=output_truncated,
                )
                continue
            if block_type in {"thinking", "text"}:
                continue
            append_message(
                "system",
                record=record,
                block_index=block_index,
                text=_compact_text(block_type) or "unknown",
                message_status="unknown",
            )

    if status == "completed" and assistant_message_indexes:
        final_index = assistant_message_indexes[-1]
        if final_index < len(messages) and messages[final_index]["kind"] == "assistant":
            messages[final_index]["kind"] = "final"

    terminal_record = records[-1] if records else None
    append_message(
        "status",
        record=terminal_record,
        block_index=10_000,
        text=terminal_error,
        message_status=status,
    )
    return messages, transcript_truncated or item_limit_hit


def _iter_content_blocks(record: dict[str, Any]) -> Iterable[dict[str, Any]]:
    message = record.get("message")
    if not isinstance(message, dict):
        return ()
    content = message.get("content")
    if not isinstance(content, list):
        return ()
    return (block for block in content if isinstance(block, dict))


def _read_bounded_records(path: Path) -> list[dict[str, Any]]:
    """Read a transcript head and bounded tail without loading huge JSONL files."""

    cap = _positive_env_int(
        "INK_AGENT_SUBAGENT_TRANSCRIPT_SCAN_BYTES",
        _DEFAULT_TRANSCRIPT_SCAN_BYTES,
    )
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            head = handle.readline(cap)
            if size <= cap:
                handle.seek(0)
            else:
                handle.seek(max(0, size - cap))
                handle.readline()  # discard a potentially partial JSONL record
            tail = handle.read(cap)
    except OSError:
        return []

    raw_lines = [head, *tail.splitlines()]
    records: list[dict[str, Any]] = []
    seen: set[bytes] = set()
    for raw in raw_lines:
        line = raw.strip()
        if not line or line in seen:
            continue
        seen.add(line)
        try:
            parsed = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(parsed, dict):
            records.append(parsed)
    records.sort(key=lambda record: str(record.get("timestamp") or ""))
    return records


def _project_activity(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a bounded, browser-safe execution timeline.

    User prompts, thinking blocks, tool inputs, and successful tool-result
    payloads stay server-side. The UI receives only assistant text, tool names,
    lifecycle state, and timestamps.
    """

    activity: list[dict[str, Any]] = []
    tool_names: dict[str, str] = {}
    sequence = 0

    def append_item(
        *,
        kind: str,
        timestamp: str | None,
        status: str,
        text: str | None = None,
        tool_name: str | None = None,
    ) -> None:
        nonlocal sequence
        sequence += 1
        activity.append(
            {
                "id": f"activity-{sequence}",
                "kind": kind,
                "timestamp": timestamp,
                "status": status,
                "text": text,
                "tool_name": tool_name,
            }
        )

    for record in records:
        timestamp = record.get("timestamp") if isinstance(record.get("timestamp"), str) else None
        message = record.get("message")
        role = message.get("role") if isinstance(message, dict) else None
        for block in _iter_content_blocks(record):
            block_type = block.get("type")
            if role == "assistant" and block_type == "text":
                text = _compact_text(block.get("text"))
                if text:
                    append_item(
                        kind="message",
                        timestamp=timestamp,
                        status="completed",
                        text=text,
                    )
                continue
            if role == "assistant" and block_type == "tool_use":
                tool_name = _compact_text(block.get("name")) or "Tool"
                tool_use_id = block.get("id")
                if isinstance(tool_use_id, str) and tool_use_id:
                    tool_names[tool_use_id] = tool_name
                append_item(
                    kind="tool",
                    timestamp=timestamp,
                    status="started",
                    tool_name=tool_name,
                )
                continue
            if role == "user" and block_type == "tool_result":
                tool_use_id = block.get("tool_use_id")
                tool_name = tool_names.get(tool_use_id) if isinstance(tool_use_id, str) else None
                append_item(
                    kind="tool",
                    timestamp=timestamp,
                    status="failed" if block.get("is_error") is True else "completed",
                    tool_name=tool_name or "Tool",
                )

    return activity[-_ACTIVITY_MAX_ITEMS:]


def _project_task(meta_path: Path) -> dict[str, Any] | None:
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(meta, dict):
        return None

    stem = meta_path.name.removesuffix(".meta.json")
    agent_id = stem.removeprefix("agent-")
    if not agent_id:
        return None
    transcript_path = meta_path.with_name(f"{stem}.jsonl")
    records = _read_bounded_records(transcript_path) if transcript_path.is_file() else []
    activity = _project_activity(records)
    scan_cap = _positive_env_int(
        "INK_AGENT_SUBAGENT_TRANSCRIPT_SCAN_BYTES",
        _DEFAULT_TRANSCRIPT_SCAN_BYTES,
    )
    try:
        transcript_truncated = transcript_path.stat().st_size > scan_cap
    except OSError:
        transcript_truncated = False

    first_at: datetime | None = None
    last_at: datetime | None = None
    last_record: dict[str, Any] | None = None
    latest_summary: str | None = None
    terminal_error: str | None = None
    interrupted = False

    for record in records:
        timestamp = _parse_timestamp(record.get("timestamp"))
        if timestamp is not None:
            first_at = first_at or timestamp
            last_at = timestamp
        last_record = record
        role = (record.get("message") or {}).get("role") if isinstance(record.get("message"), dict) else None
        for block in _iter_content_blocks(record):
            block_type = block.get("type")
            if role == "assistant" and block_type == "text":
                text = _compact_markdown(block.get("text"))
                if text:
                    latest_summary = text
            if role == "user" and block_type == "text":
                text = str(block.get("text") or "")
                if any(marker.lower() in text.lower() for marker in _INTERRUPTED_MARKERS):
                    interrupted = True
    last_role = None
    last_content_types: list[str] = []
    if last_record is not None and isinstance(last_record.get("message"), dict):
        last_role = last_record["message"].get("role")
        last_content_types = [
            str(block.get("type") or "") for block in _iter_content_blocks(last_record)
        ]
        # An earlier failed tool can be followed by recovery and a successful
        # final answer. Only the terminal record is allowed to mark the whole
        # subagent run as failed.
        terminal_error = next(
            (
                _compact_text(block.get("content"))
                for block in _iter_content_blocks(last_record)
                if block.get("type") == "tool_result" and block.get("is_error") is True
            ),
            None,
        )

    if interrupted:
        status = "cancelled"
    elif last_role == "assistant" and "text" in last_content_types:
        status = "completed"
    elif last_role == "user" and terminal_error:
        status = "failed"
    else:
        status = "running"

    duration_ms: int | None = None
    if first_at is not None and last_at is not None:
        duration_ms = max(0, round((last_at - first_at).total_seconds() * 1000))

    terminal = status in {"completed", "failed", "cancelled"}
    description = _compact_text(meta.get("description")) or _compact_text(meta.get("agentType")) or "Subagent task"
    messages, messages_truncated = _project_messages(
        records,
        meta,
        agent_id=agent_id,
        status=status,
        terminal_error=terminal_error,
        transcript_truncated=transcript_truncated,
    )
    return {
        "task_id": agent_id,
        "agent_id": agent_id,
        "agent_type": _compact_text(meta.get("agentType")) or "Agent",
        "description": description,
        "summary": latest_summary,
        "status": status,
        "tool_call_id": _compact_text(meta.get("toolUseId")),
        "spawn_depth": meta.get("spawnDepth") if isinstance(meta.get("spawnDepth"), int) else None,
        "started_at": first_at.isoformat().replace("+00:00", "Z") if first_at else None,
        "finished_at": last_at.isoformat().replace("+00:00", "Z") if terminal and last_at else None,
        "duration_ms": duration_ms,
        "error": terminal_error if status == "failed" else None,
        "activity": activity,
        "messages": messages,
        "message_count": len(messages),
        "messages_truncated": messages_truncated,
        "projection_version": _PROJECTION_VERSION,
    }


def _reconcile_task_with_inactive_runtime(task: dict[str, Any]) -> dict[str, Any]:
    """Settle an unclosed transcript once its owning thread is no longer live.

    Transcript files are an observation surface, not a process-liveness source.
    A task whose last JSONL record lacks a terminal marker may be running only
    while the owning Agent runtime is running.  After a process restart or an
    already-settled parent turn it is an interrupted historical task.
    """

    if task.get("status") != "running":
        return task
    messages = [
        {
            **message,
            **(
                {"status": "cancelled"}
                if message.get("kind") == "status"
                else {}
            ),
        }
        for message in task.get("messages", [])
        if isinstance(message, dict)
    ]
    return {
        **task,
        "status": "cancelled",
        "messages": messages,
        "message_count": len(messages),
    }


def build_thread_subagents_payload(
    thread_id: str,
    workspace_root: Path,
    *,
    runtime_running: bool | None = None,
) -> dict[str, Any]:
    """Return a safe, newest-first projection for one authenticated thread.

    ``runtime_running`` is supplied by the authenticated HTTP boundary.  The
    default ``None`` preserves the standalone filesystem projection used by
    diagnostics and fixtures; ``False`` settles orphaned running transcripts.
    """

    empty = {
        "thread_id": thread_id,
        "exists": False,
        "tasks": [],
        "counts": {"running": 0, "completed": 0, "ended": 0, "total": 0},
        "updated_at": None,
    }
    try:
        root = workspace_root.resolve(strict=False)
        workspace = (root / thread_id).resolve(strict=False)
        workspace.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return empty
    if not workspace.is_dir():
        return empty

    max_items = _positive_env_int("INK_AGENT_SUBAGENT_MAX_ITEMS", _DEFAULT_MAX_ITEMS)
    meta_paths = list((workspace / ".claude-home" / "projects").glob("**/subagents/*.meta.json"))
    tasks = [task for path in meta_paths if (task := _project_task(path)) is not None]
    tasks.sort(key=lambda task: task.get("started_at") or "", reverse=True)
    tasks = tasks[:max_items]
    if runtime_running is False:
        tasks = [_reconcile_task_with_inactive_runtime(task) for task in tasks]

    running = sum(task["status"] == "running" for task in tasks)
    completed = sum(task["status"] == "completed" for task in tasks)
    ended = sum(task["status"] in {"failed", "cancelled"} for task in tasks)
    updated_at = max(
        (task.get("finished_at") or task.get("started_at") or "" for task in tasks),
        default="",
    ) or None
    return {
        "thread_id": thread_id,
        "exists": bool(tasks),
        "tasks": tasks,
        "counts": {
            "running": running,
            "completed": completed,
            "ended": ended,
            "total": len(tasks),
        },
        "updated_at": updated_at,
    }
