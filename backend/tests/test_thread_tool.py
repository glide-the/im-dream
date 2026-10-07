# [Input] Production user MCP Thread schemas and private broker adapter.
# [Output] Verify create/list/read/send/wait and scheduled creation tools, strict inputs, and safe broker failures.
# [Pos] Provider-free Thread Tool contract test; no real model or business data.
# [Sync] 2026-09-28: add Codex-style wait_threads targets, cursor and timeout validation.
# [Sync] 2026-10-07: verify explicit once/daily/interval/hourly/weekly fields and reject model-authored identities.
# [Sync] 2026-09-28: replace model task_session_* names with Thread-oriented tools.
from __future__ import annotations

import json
from unittest.mock import patch

from libs.claude_agent_kit.server.session_projection_protocol import (
    SessionProjectionProtocolError,
    ThreadToolCommandResultDTO,
)
from libs.claude_agent_kit.server.thread_tool import (
    THREAD_TOOL_SPECS,
    handle_thread_tool,
)


class FakeBroker:
    def __init__(self):
        self.calls = []

    def thread_command(self, **kwargs):
        self.calls.append(kwargs)
        return ThreadToolCommandResultDTO(
            status="queued", thread_id="thread-one"
        )


def test_five_thread_tools_use_business_thread_arguments_and_mcp_call_id():
    broker = FakeBroker()
    inputs = {
        "create_thread": {"prompt": "检查文件", "title": "独立任务"},
        "list_threads": {"query": "检查", "limit": 5},
        "read_thread": {"thread_id": "thread-one", "message_limit": 10},
        "send_message_to_thread": {"thread_id": "thread-one", "prompt": "继续"},
        "wait_threads": {
            "targets": [{"threadId": "thread-one", "afterCursor": "cursor_one"}],
            "timeoutMs": 1200,
        },
    }
    expected_operations = [
        "thread.create",
        "thread.list",
        "thread.read",
        "thread.send",
        "thread.wait",
    ]
    with patch(
        "libs.claude_agent_kit.server.thread_tool.SessionProjectionBrokerClient.from_env",
        return_value=broker,
    ):
        for name, arguments in inputs.items():
            result = json.loads(handle_thread_tool(name, arguments, "mcp-call-1"))
            assert result == {
                "ok": True,
                "status": "queued",
                "thread_id": "thread-one",
            }
        assert all(call["tool_call_id"] == "mcp-call-1" for call in broker.calls)
        assert [call["operation"] for call in broker.calls] == expected_operations
        denied = json.loads(
            handle_thread_tool(
                "create_thread",
                {"prompt": "private", "user_id": "forged"},
                "mcp-call-2",
            )
        )
        assert denied == {"ok": False, "error_code": "THREAD_TOOL_INPUT_INVALID"}
        assert len(broker.calls) == 5
        wait_call = broker.calls[-1]
        assert wait_call["timeout_ms"] == 1200
        assert wait_call["targets"][0].model_dump() == {
            "thread_id": "thread-one",
            "after_cursor": "cursor_one",
        }


def test_optional_inputs_and_integer_limits_remain_strict():
    broker = FakeBroker()
    with patch(
        "libs.claude_agent_kit.server.thread_tool.SessionProjectionBrokerClient.from_env",
        return_value=broker,
    ):
        assert json.loads(handle_thread_tool("create_thread", {"prompt": "新任务"}, "call"))["ok"]
        assert json.loads(handle_thread_tool("list_threads", {}, "call"))["ok"]
        assert json.loads(
            handle_thread_tool("read_thread", {"thread_id": "thread-one"}, "call")
        )["ok"]
        for invalid in ({"limit": True}, {"limit": 0}, {"query": ""}):
            assert json.loads(handle_thread_tool("list_threads", invalid, "call")) == {
                "ok": False,
                "error_code": "THREAD_TOOL_INPUT_INVALID",
            }
        for invalid in (
            {"targets": []},
            {"targets": [{"threadId": "thread-one"}, {"threadId": "thread-one"}]},
            {"targets": [{"threadId": "thread-one", "hostId": "forged"}]},
            {"targets": [{"threadId": "thread-one"}], "timeoutMs": True},
            {"targets": [{"threadId": "thread-one"}], "timeoutMs": 120001},
        ):
            assert json.loads(handle_thread_tool("wait_threads", invalid, "call")) == {
                "ok": False,
                "error_code": "THREAD_TOOL_INPUT_INVALID",
            }


def test_broker_error_is_safe_and_does_not_echo_arguments():
    with patch(
        "libs.claude_agent_kit.server.thread_tool.SessionProjectionBrokerClient.from_env",
        side_effect=SessionProjectionProtocolError("THREAD_TOOL_UNAVAILABLE", 503),
    ):
        result = handle_thread_tool(
            "create_thread", {"prompt": "private text"}, "mcp-call-1"
        )
    assert json.loads(result) == {"ok": False, "error_code": "THREAD_TOOL_UNAVAILABLE"}
    assert "private" not in result


def test_model_tool_registry_contains_no_legacy_task_session_names():
    assert set(THREAD_TOOL_SPECS) == {
        "create_scheduled_task",
        "create_thread",
        "list_threads",
        "read_thread",
        "send_message_to_thread",
        "wait_threads",
    }
    assert not any(name.startswith("task_session_") for name in THREAD_TOOL_SPECS)


def test_scheduled_creation_requires_explicit_rule_and_stays_on_host_broker():
    broker = FakeBroker()
    valid = {"title": "Morning note", "prompt": "Summarize my notes", "rule": {
        "kind": "daily", "local_time": "09:00", "time_zone": "Asia/Shanghai",
    }}
    with patch("libs.claude_agent_kit.server.thread_tool.SessionProjectionBrokerClient.from_env",
               return_value=broker):
        assert json.loads(handle_thread_tool("create_scheduled_task", valid, "call-1"))["ok"]
        assert broker.calls[-1]["operation"] == "schedule.create"
        assert broker.calls[-1]["schedule_rule"] == valid["rule"]
        for rule in (
            {"kind": "hourly", "interval_hours": 2, "minute": 15, "time_zone": "Asia/Shanghai"},
            {"kind": "weekly", "weekdays": ["MO", "FR"], "local_time": "09:00", "time_zone": "Asia/Shanghai"},
        ):
            candidate = {**valid, "rule": rule}
            assert json.loads(handle_thread_tool("create_scheduled_task", candidate, "call-v3"))["ok"]
            assert broker.calls[-1]["schedule_rule"] == rule
        for invalid in (
            {**valid, "user_id": "42"},
            {**valid, "rule": {"kind": "daily", "local_time": "09:00"}},
            {**valid, "rule": {**valid["rule"], "credential": "forged"}},
            {**valid, "rule": {"kind": "once", "local_date": "2026-09-29",
                               "local_time": "09:00", "time_zone": "Asia/Shanghai"}},
            {**valid, "rule": {"kind": "hourly", "interval_hours": 0, "minute": 0,
                               "time_zone": "Asia/Shanghai"}},
            {**valid, "rule": {"kind": "weekly", "weekdays": [], "local_time": "09:00",
                               "time_zone": "Asia/Shanghai"}},
        ):
            assert json.loads(handle_thread_tool("create_scheduled_task", invalid, "call-1")) == {
                "ok": False, "error_code": "THREAD_TOOL_INPUT_INVALID",
            }
