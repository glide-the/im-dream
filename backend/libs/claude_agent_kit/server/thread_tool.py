# [Input] Model-provided Dream Thread prompt/query/id and the current MCP request identity.
# [Output] Strict Thread and scheduled-task Tool calls through the private turn broker.
# [Pos] User MCP Thread adapter; actor, source Thread and Claude session handles stay in the Dream host.
# [Sync] 2026-09-28: expose Codex-style wait_threads so a parent turn consumes child completion as a tool result.
# [Sync] 2026-09-28: let an authorized Chat turn create one once/daily Admin schedule with an explicit IANA time zone.
# [Sync] 2026-09-28: expose create/list/read/send Thread semantics and retire model-facing task_session_* names.
"""Dream Thread Tools backed by the current host turn owner."""

from __future__ import annotations

import json
import os
from typing import Any

from .session_projection_protocol import (
    SessionProjectionBrokerClient,
    SessionProjectionProtocolError,
    ThreadToolWaitTargetDTO,
)


THREAD_TOOL_SPECS: dict[str, tuple[str, dict[str, Any]]] = {
    "create_scheduled_task": (
        "仅在用户明确要求定时执行时创建 Dream 任务。必须提供提示词、单次本地日期时间或每日本地钟点，以及 IANA 时区；单次重复时刻须明确偏移。",
        {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "任务标题。"},
                "prompt": {"type": "string", "description": "到期时新会话的首条输入。"},
                "rule": {
                    "oneOf": [
                        {"type": "object", "properties": {
                            "kind": {"const": "once"}, "local_date": {"type": "string", "description": "YYYY-MM-DD"},
                            "local_time": {"type": "string", "description": "HH:MM"},
                            "time_zone": {"type": "string", "description": "IANA 时区，例如 Asia/Shanghai"},
                            "selected_offset_minutes": {"type": ["integer", "null"], "description": "重复本地时刻选择的 UTC 偏移分钟；普通时刻填 null。"},
                        }, "required": ["kind", "local_date", "local_time", "time_zone", "selected_offset_minutes"], "additionalProperties": False},
                        {"type": "object", "properties": {
                            "kind": {"const": "daily"}, "local_time": {"type": "string", "description": "每天的 HH:MM"},
                            "time_zone": {"type": "string", "description": "IANA 时区，例如 Asia/Shanghai"},
                        }, "required": ["kind", "local_time", "time_zone"], "additionalProperties": False},
                    ],
                },
            },
            "required": ["title", "prompt", "rule"],
            "additionalProperties": False,
        },
    ),
    "create_thread": (
        "仅在用户明确要求新建独立会话时创建 Dream Thread，并非阻塞启动首轮。",
        {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "新 Thread 的首条输入。"},
                "title": {"type": "string", "description": "可选的会话标题。"},
            },
            "required": ["prompt"],
            "additionalProperties": False,
        },
    ),
    "list_threads": (
        "列出当前用户的 Dream Threads；可用 query 查找特定会话。",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "可选的标题或消息搜索文本。"},
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "最多返回的 Thread 数量。",
                },
            },
            "additionalProperties": False,
        },
    ),
    "read_thread": (
        "读取一个已授权 Dream Thread 的近期消息和服务端运行状态，不启动推理。",
        {
            "type": "object",
            "properties": {
                "thread_id": {"type": "string", "description": "要读取的业务 Thread ID。"},
                "message_limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "最多返回的近期消息数量。",
                },
            },
            "required": ["thread_id"],
            "additionalProperties": False,
        },
    ),
    "send_message_to_thread": (
        "向已授权 Dream Thread 发送后续消息；运行中排队，空闲时恢复同一 Claude 会话。",
        {
            "type": "object",
            "properties": {
                "thread_id": {"type": "string", "description": "要继续的业务 Thread ID。"},
                "prompt": {"type": "string", "description": "后续用户输入。"},
            },
            "required": ["thread_id", "prompt"],
            "additionalProperties": False,
        },
    ),
    "wait_threads": (
        "等待最多 8 个 Dream Threads 中首个完成或需要处理的目标；等待期间父轮次保持运行，回执由当前父 Agent 继续消费。新用户输入会提前结束等待。",
        {
            "type": "object",
            "properties": {
                "targets": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 8,
                    "description": "要等待的业务 Threads。afterCursor 可抑制已经交付过的同一终态正文。",
                    "items": {
                        "type": "object",
                        "properties": {
                            "threadId": {
                                "type": "string",
                                "description": "要等待的业务 Thread ID。",
                            },
                            "afterCursor": {
                                "type": "string",
                                "description": "上一次 wait_threads 回执中的不透明 cursor。",
                            },
                        },
                        "required": ["threadId"],
                        "additionalProperties": False,
                    },
                },
                "timeoutMs": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 120000,
                    "description": "最长等待毫秒数；0 表示立即读取快照，省略时为 120000。",
                },
            },
            "required": ["targets"],
            "additionalProperties": False,
        },
    ),
}

_THREAD_OPERATIONS = {
    "create_scheduled_task": "schedule.create",
    "create_thread": "thread.create",
    "list_threads": "thread.list",
    "read_thread": "thread.read",
    "send_message_to_thread": "thread.send",
    "wait_threads": "thread.wait",
}


def _valid_arguments(name: str, values: dict[str, Any]) -> bool:
    if name == "create_scheduled_task":
        rule = values.get("rule")
        if (set(values) != {"title", "prompt", "rule"}
            or not all(isinstance(values[key], str) and values[key].strip() for key in ("title", "prompt"))
            or not isinstance(rule, dict)):
            return False
        required = ({"kind", "local_date", "local_time", "time_zone", "selected_offset_minutes"}
                    if rule.get("kind") == "once" else {"kind", "local_time", "time_zone"})
        if set(rule) != required or rule.get("kind") not in ("once", "daily"):
            return False
        if not all(isinstance(rule.get(key), str) and rule[key].strip() for key in required - {"kind", "selected_offset_minutes"}):
            return False
        return rule.get("kind") != "once" or rule["selected_offset_minutes"] is None or type(rule["selected_offset_minutes"]) is int
    if name == "create_thread":
        return (
            set(values) <= {"prompt", "title"}
            and isinstance(values.get("prompt"), str)
            and bool(values["prompt"].strip())
            and (
                "title" not in values
                or (isinstance(values["title"], str) and bool(values["title"].strip()))
            )
        )
    if name == "list_threads":
        return (
            set(values) <= {"query", "limit"}
            and (
                "query" not in values
                or (isinstance(values["query"], str) and bool(values["query"].strip()))
            )
            and (
                "limit" not in values
                or (
                    type(values["limit"]) is int
                    and 1 <= values["limit"] <= 100
                )
            )
        )
    if name == "read_thread":
        return (
            set(values) <= {"thread_id", "message_limit"}
            and isinstance(values.get("thread_id"), str)
            and bool(values["thread_id"].strip())
            and (
                "message_limit" not in values
                or (
                    type(values["message_limit"]) is int
                    and 1 <= values["message_limit"] <= 100
                )
            )
        )
    if name == "send_message_to_thread":
        return (
            set(values) == {"thread_id", "prompt"}
            and all(isinstance(values[key], str) and values[key].strip() for key in values)
        )
    if name == "wait_threads":
        if set(values) - {"targets", "timeoutMs"}:
            return False
        targets = values.get("targets")
        if not isinstance(targets, list) or not 1 <= len(targets) <= 8:
            return False
        thread_ids: list[str] = []
        for target in targets:
            if not isinstance(target, dict) or set(target) - {"threadId", "afterCursor"}:
                return False
            thread_id = target.get("threadId")
            after_cursor = target.get("afterCursor")
            if not isinstance(thread_id, str) or not thread_id.strip():
                return False
            if after_cursor is not None and (
                not isinstance(after_cursor, str) or not after_cursor.strip()
            ):
                return False
            thread_ids.append(thread_id)
        timeout_ms = values.get("timeoutMs")
        return (
            len(thread_ids) == len(set(thread_ids))
            and (
                timeout_ms is None
                or (type(timeout_ms) is int and 0 <= timeout_ms <= 120_000)
            )
        )
    return False


def handle_thread_tool(
    name: str,
    arguments: dict[str, Any] | None,
    tool_call_id: str,
) -> str:
    if name not in THREAD_TOOL_SPECS:
        raise ValueError("Unknown Thread Tool")
    values = arguments if isinstance(arguments, dict) else {}
    if not _valid_arguments(name, values):
        return json.dumps({"ok": False, "error_code": "THREAD_TOOL_INPUT_INVALID"})
    try:
        client = SessionProjectionBrokerClient.from_env(dict(os.environ))
        wait_targets = None
        if name == "wait_threads":
            wait_targets = [
                ThreadToolWaitTargetDTO(
                    thread_id=item["threadId"].strip(),
                    after_cursor=(
                        item.get("afterCursor", "").strip() or None
                    ),
                )
                for item in values["targets"]
            ]
        result = client.thread_command(
            operation=_THREAD_OPERATIONS[name],
            tool_call_id=tool_call_id,
            prompt=values.get("prompt"),
            title=values.get("title"),
            query=values.get("query"),
            limit=values.get("limit"),
            thread_id=values.get("thread_id"),
            message_limit=values.get("message_limit"),
            targets=wait_targets,
            timeout_ms=values.get("timeoutMs"),
            schedule_rule=values.get("rule"),
        )
        return json.dumps(
            {"ok": True, **result.model_dump(exclude_none=True)},
            ensure_ascii=False,
        )
    except SessionProjectionProtocolError as exc:
        return json.dumps({"ok": False, "error_code": exc.code}, ensure_ascii=False)


__all__ = ["THREAD_TOOL_SPECS", "handle_thread_tool"]
