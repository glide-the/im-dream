# [Input] Production Facade/Store/DTOs, actual CredentialStore and bounded scripted HTTP providers.
# [Output] Verify scan-renew, in-flight claim and committed-finish cancellation without replay or unsafe terminal writes.
# [Pos] Isolated Dream consumer technical edge journeys; no Admin locking/fencing imitation or real account writes.
# [Sync] 2026-10-07: supplement the frozen core suite in a separately named file while preserving its running inputs.
# [Sync] 2026-10-07: use the existing tests package import for the exact project command without PYTHONPATH overrides.
from __future__ import annotations

import asyncio
import threading
import unittest
from unittest.mock import patch

from tests.test_notion_sync_ownership import _ExecutionFixture


class CancellationEdges(_ExecutionFixture, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        # Establish a nonempty scope through the real resource adapter before the
        # operation under test; the scripted claim never invents selected sources.
        self.flow._store.replace_connector_resources(self.connector, 7,
            [{'external_id': 'db-team', 'title': 'Team', 'metadata': {}}], [])
        self.state.calls.clear()

    async def test_scan_second_renew_cancel_late_budget_result_never_finishes(self):
        entered, release = threading.Event(), threading.Event()
        cancelled = asyncio.Event()
        original_renew = self.flow._store.renew_sync_run
        original_reply = self.state._sync_reply
        renewal_count = 0

        def replies(name, value):
            result = original_reply(name, value)
            if 'execution_policy' in result:
                result['execution_policy'] = {'lease_seconds': 4, 'heartbeat_seconds': 1, 'renewal_budget_seconds': 1}
            return result

        def renew(*args):
            nonlocal renewal_count
            renewal_count += 1
            if renewal_count == 2:
                entered.set()
                if not release.wait(5):
                    raise AssertionError('Owned second renewal release timed out')
            return original_renew(*args)

        async def build(**_kwargs):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        with patch.object(self.state, '_sync_reply', side_effect=replies), \
                patch.object(self.flow._store, 'renew_sync_run', side_effect=renew), \
                patch('notion.sync.build_canonical_snapshot', new=build):
            task = asyncio.create_task(self.facade().sync())
            try:
                self.assertTrue(await asyncio.wait_for(asyncio.to_thread(entered.wait, 4), 5))
                task.cancel()
                # The waiter is cancelled before the budget expires; the original
                # finite DTO/receipt still returns only after that server policy budget.
                await asyncio.sleep(1.1)
                release.set()
                with self.assertRaises(asyncio.CancelledError):
                    await asyncio.wait_for(task, 5)
            finally:
                release.set()
                if not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
        self.assertTrue(cancelled.is_set())
        self.assertEqual(self.sync_names(), ['notion.sync-run.request', 'notion.sync-run.renew', 'notion.sync-run.renew'])
        self.assertFalse(list(self.store._connector_root(7, self.connector).glob('snapshot-*.json')))

    async def test_in_flight_claim_cancel_waits_but_does_not_build_or_finish(self):
        entered, release = threading.Event(), threading.Event()
        original = self.flow._store.begin_sync_run

        def claim(*args):
            result = original(*args)  # Scripted real DTO response; claim may already commit.
            entered.set()
            if not release.wait(5):
                raise AssertionError('Owned claim release timed out')
            return result

        with patch.object(self.flow._store, 'begin_sync_run', side_effect=claim):
            task = asyncio.create_task(self.facade().sync())
            try:
                self.assertTrue(await asyncio.wait_for(asyncio.to_thread(entered.wait, 4), 5))
                task.cancel()
                await asyncio.sleep(0)
                self.assertFalse(task.done())
                release.set()
                with self.assertRaises(asyncio.CancelledError):
                    await asyncio.wait_for(task, 5)
            finally:
                release.set()
                if not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
        self.assertEqual(self.sync_names(), ['notion.sync-run.request'])
        self.assertEqual(len(self.flow.snapshot_calls), 0)
        self.assertIsNone(self.state.connectors[self.connector]['current_snapshot_version'])
        # There is no unconfirmed terminal write; Admin owns any resulting lease.

    async def test_committed_finish_in_flight_cancel_waits_without_replay_then_read_recovers(self):
        entered, release = threading.Event(), threading.Event()
        original = self.flow._store.finish_sync_run

        def finish(*args):
            result = original(*args)  # Existing strict transport/receipt result accepted.
            entered.set()
            if not release.wait(5):
                raise AssertionError('Owned terminal release timed out')
            return result

        with patch.object(self.flow._store, 'finish_sync_run', side_effect=finish):
            task = asyncio.create_task(self.facade().sync())
            try:
                self.assertTrue(await asyncio.wait_for(asyncio.to_thread(entered.wait, 4), 5))
                task.cancel()
                await asyncio.sleep(0)
                self.assertFalse(task.done())
                release.set()
                with self.assertRaises(asyncio.CancelledError):
                    await asyncio.wait_for(task, 5)
            finally:
                release.set()
                if not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
        finishes = [value['outcome'] for name, value, _ in self.state.calls if name == 'notion.sync-run.finish']
        self.assertEqual(len(finishes), 1)
        self.assertEqual(finishes[0]['status'], 'succeeded')
        self.assertFalse(list(self.store._connector_root(7, self.connector).glob('snapshot-*.json')))
        snapshot = await asyncio.to_thread(self.facade().get_current_snapshot)
        self.assertEqual(snapshot['metadata']['snapshot_version'], self.state.connectors[self.connector]['current_snapshot_version'])
        self.assertEqual(snapshot['pages'], {})
        self.assertTrue(any(name == 'notion.snapshot.current' for name, *_ in self.state.calls))
        self.assertEqual(len([name for name, *_ in self.state.calls if name == 'notion.sync-run.finish']), 1)


if __name__ == '__main__':
    unittest.main()
