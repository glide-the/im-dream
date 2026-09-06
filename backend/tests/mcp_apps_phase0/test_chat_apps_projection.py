# [Input] Existing database.save_chat_message/list_chat_messages functions and a provider-free fake connection.
# [Output] Prove five Apps fields survive save/list/public DTO and browser refresh without schema changes.
# [Pos] Phase 0 Chat compatibility PoC; it calls production persistence entrypoints but never a real database.
# [Sync] 2026-09-04: cover task_301 P0-07 persistence, public route, and redaction boundary.

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import database  # noqa: E402
from routers import claude_agent as claude_agent_router  # noqa: E402

from backend.tests.mcp_apps_phase0.projection import (  # noqa: E402
    build_phase0_chat_part,
)


class _Cursor:
    def __init__(self, *, row=None, rows=None) -> None:
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class _SharedDatabase:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, object]] = {}
        self.statements: list[str] = []


class _Connection:
    def __init__(self, shared: _SharedDatabase) -> None:
        self.shared = shared

    def execute(self, statement, params=()):
        normalized = " ".join(str(statement).split())
        self.shared.statements.append(normalized)
        if normalized.startswith("INSERT INTO chat_message"):
            (
                message_id,
                thread_id,
                role,
                parts,
                metadata,
                history_final_text,
                history_process_available,
                history_projection_version,
            ) = params
            self.shared.rows[message_id] = {
                "id": message_id,
                "thread_id": thread_id,
                "role": role,
                "parts": parts,
                "metadata": metadata,
                "created_at": "2026-09-04T00:00:00Z",
                "history_final_text": history_final_text,
                "history_process_available": history_process_available,
                "history_projection_version": history_projection_version,
            }
            return _Cursor(row={"id": message_id})
        if normalized.startswith("UPDATE chat_thread SET updated_at"):
            return _Cursor()
        if normalized.startswith("SELECT id, role, parts, metadata, created_at"):
            rows = [
                {
                    "id": row["id"],
                    "role": row["role"],
                    "parts": row["parts"],
                    "metadata": row["metadata"],
                    "created_at": row["created_at"],
                }
                for row in self.shared.rows.values()
                if row["thread_id"] == params[0]
            ]
            return _Cursor(rows=rows)
        raise AssertionError(normalized)

    def commit(self) -> None:
        return None

    def close(self) -> None:
        return None


def _call_tool_result() -> dict:
    return {
        "content": [
            {"type": "text", "text": "Phase 0 state: shared-state-v1"},
            {
                "type": "resource_link",
                "name": "phase0-view",
                "uri": "ui://phase0-standard-apps-fixture/view.html",
                "mimeType": "text/html;profile=mcp-app",
            },
        ],
        "structuredContent": {
            "state": "shared-state-v1",
            "items": [{"id": "item-1", "enabled": True}],
        },
        "_meta": {
            "ui": {"resourceUri": "ui://phase0-standard-apps-fixture/view.html"},
            "fixture": "phase0-standard-apps-fixture",
        },
        "isError": False,
    }


def test_existing_chat_save_and_list_round_trip_complete_apps_result() -> None:
    shared = _SharedDatabase()
    expected_result = _call_tool_result()
    expected_part = build_phase0_chat_part(
        server_ref="server-ref-phase0",
        tool_name="phase0_show_shared_state",
        tool_call_id="tool-call-phase0-1",
        tool_input={"request": "read shared state"},
        tool_result=expected_result,
    )

    with patch.object(database, "get_db", side_effect=lambda: _Connection(shared)):
        database.save_chat_message(
            "thread-phase0",
            "assistant",
            [expected_part],
            message_id="message-phase0",
            metadata={"turnId": "turn-phase0", "source": "isolated-poc"},
        )
        restored = database.list_chat_messages("thread-phase0")

    invocation = restored[0]["parts"][0]["toolInvocation"]
    assert invocation == expected_part["toolInvocation"]
    assert invocation["result"] == expected_result
    assert {
        "serverRef",
        "toolName",
        "toolCallId",
        "input",
        "result",
    } == set(invocation)
    assert not any(
        marker in json.dumps(restored, sort_keys=True).lower()
        for marker in ("authorization", "bearer ", "refresh_token", "stdio_command")
    )
    assert not any(
        token in " ".join(shared.statements).upper()
        for token in ("CREATE TABLE", "ALTER TABLE", "CREATE INDEX", "ALEMBIC")
    )

    thread = {
        "id": "thread-phase0",
        "title": "Phase 0 isolated thread",
        "deck_id": None,
        "voice_id": None,
        "created_at": "2026-09-04T00:00:00Z",
        "updated_at": "2026-09-04T00:00:00Z",
    }
    with (
        patch.object(
            claude_agent_router.database,
            "get_chat_thread",
            return_value=thread,
        ),
        patch.object(
            claude_agent_router.database,
            "list_chat_messages",
            return_value=restored,
        ),
    ):
        public_history = asyncio.run(
            claude_agent_router.claude_agent_thread_messages(
                "thread-phase0",
                current_user={"user_id": 1},
            )
        )

    public_invocation = public_history["messages"][0]["parts"][0]["toolInvocation"]
    assert public_invocation == expected_part["toolInvocation"]


def test_sensitive_connection_material_is_rejected_before_persistence() -> None:
    unsafe_result = _call_tool_result()
    unsafe_result["_meta"]["authorization"] = "Bearer test-secret"

    try:
        build_phase0_chat_part(
            server_ref="server-ref-phase0",
            tool_name="phase0_show_shared_state",
            tool_call_id="tool-call-phase0-1",
            tool_input={},
            tool_result=unsafe_result,
        )
    except ValueError as error:
        assert "sensitive Apps projection key rejected" in str(error)
    else:  # pragma: no cover - explicit fail-closed assertion
        raise AssertionError("sensitive Apps material reached the persistence boundary")
