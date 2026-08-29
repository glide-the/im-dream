# [Input] Synthetic connector policies/candidates and injected Notion facade outcomes.
# [Output] Verify default/desired/effective policy semantics and due-only background synchronization.
# [Pos] Notion scheduled synchronization contract test in backend/tests
# [Sync] 2026-08-28: cover automatic default, monotonic updates, disabled policy, and failure isolation outside Chat.

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from notion.sync_policy import (
    SYNC_POLICY_CONFIG_KEY,
    resolve_sync_policy,
    sync_policy_is_due,
    update_sync_policy,
)
from notion.sync_scheduler import NotionSnapshotSyncWorker


class TestNotionSyncPolicy(unittest.TestCase):
    def test_default_is_automatic_and_exposes_all_policy_layers(self) -> None:
        now = datetime(2026, 8, 28, 12, tzinfo=timezone.utc)
        policy = resolve_sync_policy(None, now=now)
        self.assertEqual(policy["default"], policy["desired"])
        self.assertEqual(policy["desired"], policy["effective"])
        self.assertTrue(policy["effective"]["enabled"])
        self.assertEqual(policy["status"], "applied")
        self.assertTrue(sync_policy_is_due(None, now=now))

    def test_update_advances_revision_and_disabled_policy_is_not_due(self) -> None:
        first = update_sync_policy(None, enabled=False, interval_minutes=60)
        self.assertEqual(first["desired"]["revision"], 2)
        self.assertEqual(first["desired"], first["effective"])
        self.assertEqual(first["status"], "disabled")
        self.assertFalse(sync_policy_is_due(first))


class TestNotionSnapshotSyncWorker(unittest.IsolatedAsyncioTestCase):
    async def test_sweep_runs_only_due_enabled_connectors(self) -> None:
        old = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        disabled = update_sync_policy(None, enabled=False, interval_minutes=60)
        calls: list[tuple[int, str]] = []

        class Facade:
            def __init__(self, actor: int, connector: str) -> None:
                self.actor = actor
                self.connector = connector

            async def sync(self, connector_id: str):
                calls.append((self.actor, connector_id))

        candidates = [
            {
                "id": "due",
                "user_id": 7,
                "last_synced_at": old,
                "config": {},
                "sources": [{"external_id": "db"}],
            },
            {
                "id": "disabled",
                "user_id": 8,
                "last_synced_at": old,
                "config": {SYNC_POLICY_CONFIG_KEY: disabled},
                "sources": [{"external_id": "db"}],
            },
            {
                "id": "empty",
                "user_id": 9,
                "last_synced_at": old,
                "config": {},
                "sources": [],
            },
        ]
        worker = NotionSnapshotSyncWorker(
            candidate_provider=lambda: candidates,
            facade_factory=lambda actor, connector: Facade(actor, connector),
            interval_seconds=999,
        )
        result = await worker.sync_due_once()
        self.assertEqual(calls, [(7, "due")])
        self.assertEqual((result.candidates, result.attempted, result.succeeded, result.failed), (3, 1, 1, 0))

    async def test_one_connector_failure_does_not_abort_later_candidates(self) -> None:
        calls: list[str] = []

        class Facade:
            def __init__(self, connector: str) -> None:
                self.connector = connector

            async def sync(self, connector_id: str):
                calls.append(connector_id)
                if connector_id == "first":
                    raise RuntimeError("synthetic secret must not be logged")

        candidates = [
            {"id": name, "user_id": index, "config": {}, "sources": [{}]}
            for index, name in enumerate(("first", "second"), start=7)
        ]
        worker = NotionSnapshotSyncWorker(
            candidate_provider=lambda: candidates,
            facade_factory=lambda _actor, connector: Facade(connector),
            interval_seconds=999,
        )
        with self.assertLogs("notion.sync_scheduler", level="WARNING") as logs:
            result = await worker.sync_due_once()
        self.assertEqual(calls, ["first", "second"])
        self.assertEqual((result.succeeded, result.failed), (1, 1))
        self.assertNotIn("synthetic secret", "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()
