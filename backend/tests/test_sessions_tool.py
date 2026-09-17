# [Input] Strict Session broker projections and existing retrieval arguments.
# [Output] Compatibility evidence for date, fuzzy, labels, limits, Unicode, vector/auto and explicit broker failure.
# [Pos] Provider-free user MCP tool tests; production DB helpers must never participate.
# [Sync] 2026-09-15: replace actor/DB fixtures with the private Session projection client boundary.
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import unittest
import unittest.mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tests._sdk_stubs  # noqa: F401 — stub SDK before importing kit package

import database
from libs.claude_agent_kit.server.session_projection_protocol import (
    SessionProjectionBrokerClient,
    SessionProjectionResultDTO,
)
from libs.claude_agent_kit.server.sessions_tool import handle_get_sessions_range


def _projection(rows: list[dict]) -> SessionProjectionResultDTO:
    return SessionProjectionResultDTO.model_validate(
        {
            "sessions": [
                {
                    "id": row["id"],
                    "name": row.get("name"),
                    "labels": row.get("labels", []),
                    "created_at": row.get("created_at"),
                    "updated_at": row.get("updated_at"),
                    "first_line": row.get("first_line", ""),
                    "text": row.get("text"),
                }
                for row in rows
            ]
        },
        strict=True,
    )


class TestGetSessionsRangeTool(unittest.TestCase):
    def _call(self, args: dict, rows: list[dict]) -> tuple[dict, unittest.mock.Mock]:
        client = unittest.mock.Mock(spec=SessionProjectionBrokerClient)
        client.list_sessions.return_value = _projection(rows)
        with unittest.mock.patch.object(
            SessionProjectionBrokerClient, "from_env", return_value=client
        ) as factory:
            data = json.loads(handle_get_sessions_range(args))
        factory.assert_called_once()
        return data, client

    def test_date_only_call_keeps_range_listing_compatibility(self):
        data, client = self._call(
            {"start_date": "2026-01-01", "end_date": "2026-01-31"},
            [{
                "id": "s1",
                "name": "Old note",
                "labels": ["成长"],
                "updated_at": "2026-01-02T10:00:00Z",
                "first_line": "A lightweight preview.",
            }],
        )

        self.assertTrue(data["ok"])
        self.assertEqual(data["sessions"][0]["sessionId"], "s1")
        self.assertNotIn("match", data["sessions"][0])
        client.list_sessions.assert_called_once_with(
            start_date="2026-01-01", end_date="2026-01-31", include_text=False
        )

    def test_query_uses_full_text_fuzzy_match_and_filters_irrelevant_rows(self):
        data, client = self._call(
            {
                "start_date": "2026-02-01",
                "end_date": "2026-02-28",
                "query": "孤独 散步",
            },
            [
                {
                    "id": "semantic",
                    "name": "普通标题",
                    "updated_at": "2026-02-02T10:00:00Z",
                    "first_line": "今天我很累。",
                    "text": "今天我很累。\n\n后来写到一次孤独的夜间散步。",
                },
                {
                    "id": "unrelated",
                    "name": "快乐晚餐",
                    "labels": ["社交"],
                    "updated_at": "2026-02-01T10:00:00Z",
                    "first_line": "和朋友吃饭。",
                    "text": "和朋友吃饭，心情很好。",
                },
            ],
        )

        self.assertTrue(data["ok"])
        self.assertEqual([s["sessionId"] for s in data["sessions"]], ["semantic"])
        self.assertEqual(data["sessions"][0]["match"]["fields"], ["text"])
        client.list_sessions.assert_called_once_with(
            start_date="2026-02-01", end_date="2026-02-28", include_text=True
        )

    def test_labels_unicode_and_limit_keep_all_match_filter(self):
        data, _client = self._call(
            {
                "start_date": "2026-03-01",
                "end_date": "2026-03-31",
                "labels": ["孤独", "成长"],
                "label_match": "all",
                "limit": 1,
            },
            [
                {
                    "id": "both",
                    "name": "甲",
                    "labels": ["孤独", "成长"],
                    "updated_at": "2026-03-02T00:00:00Z",
                    "first_line": "匹配",
                },
                {
                    "id": "one",
                    "name": "乙",
                    "labels": ["孤独"],
                    "updated_at": "2026-03-01T00:00:00Z",
                    "first_line": "部分",
                },
            ],
        )

        self.assertTrue(data["ok"])
        self.assertEqual([s["sessionId"] for s in data["sessions"]], ["both"])
        self.assertEqual(data["sessions"][0]["match"]["fields"], ["labels"])

    def test_auto_mode_degrades_vector_query_to_fuzzy(self):
        data, _client = self._call(
            {
                "start_date": "2026-04-01",
                "end_date": "2026-04-30",
                "retrieval_mode": "auto",
                "query": "孤独",
                "vector_query": {"text": "孤独"},
            },
            [{
                "id": "s1",
                "name": "关于孤独",
                "updated_at": "2026-04-01T00:00:00Z",
                "first_line": "孤独的一天。",
                "text": "孤独的一天。",
            }],
        )

        self.assertTrue(data["ok"])
        self.assertEqual(data["retrieval"]["mode"], "fuzzy")
        self.assertIn(
            "vector_retrieval_unconfigured_falling_back_to_fuzzy", data["warnings"]
        )

    def test_vector_mode_reports_unavailable_without_broker_call(self):
        with unittest.mock.patch.object(
            SessionProjectionBrokerClient, "from_env"
        ) as factory:
            data = json.loads(
                handle_get_sessions_range({
                    "start_date": "2026-05-01",
                    "end_date": "2026-05-31",
                    "retrieval_mode": "vector",
                    "vector_query": {"text": "孤独"},
                })
            )

        self.assertFalse(data["ok"])
        self.assertEqual(data["error"], "vector_retrieval_unavailable")
        factory.assert_not_called()

    def test_missing_broker_fails_explicitly_without_actor_or_database_fallback(self):
        with (
            unittest.mock.patch.dict(os.environ, {}, clear=True),
            unittest.mock.patch.object(
                database,
                "list_sessions_in_range",
                side_effect=AssertionError("legacy range helper must not run"),
            ) as legacy_range,
            unittest.mock.patch.object(
                database,
                "list_sessions",
                side_effect=AssertionError("legacy Session helper must not run"),
            ) as legacy_all,
        ):
            data = json.loads(
                handle_get_sessions_range({
                    "start_date": "2026-06-01",
                    "end_date": "2026-06-30",
                })
            )

        self.assertEqual(
            data,
            {
                "ok": False,
                "error": "session_projection_unavailable",
                "service_error_code": "SESSION_BROKER_CONFIGURATION_INVALID",
            },
        )
        legacy_range.assert_not_called()
        legacy_all.assert_not_called()


if __name__ == "__main__":
    unittest.main()
