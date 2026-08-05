"""Project Claude Code subagent transcripts into a thread-scoped API payload.

The Claude runtime owns the canonical transcript files under the server-owned
thread workspace. This module reads only the small metadata files plus a
bounded tail of each JSONL transcript. It returns assistant updates and tool
names for a safe execution timeline; raw prompts, thinking, tool inputs,
successful tool outputs, and internal paths are never returned to the browser.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


_DEFAULT_MAX_ITEMS = 200
_DEFAULT_TRANSCRIPT_SCAN_BYTES = 512 * 1024
_SUMMARY_MAX_CHARS = 600
_ACTIVITY_MAX_ITEMS = 80
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
                text = _compact_text(block.get("text"))
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
    }


def build_thread_subagents_payload(
    thread_id: str,
    workspace_root: Path,
) -> dict[str, Any]:
    """Return a safe, newest-first projection for one authenticated thread."""

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
