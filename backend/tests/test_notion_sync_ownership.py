# [Input] Frozen execution DTOs, public Notion router, and named isolated DI providers.
# [Output] Verify ownership orchestration, strict accepted snapshots and honest Settings recovery.
# [Pos] Dream consumer technical journeys; Admin DB receipts prove locking/fencing separately.
# [Sync] 2026-10-07: public manual/select/scheduled paths share request/renew/finish with no legacy write fallback.
# [Sync] 2026-10-07: assert service Authorization rather than an absent HTTP Bearer on service-only operations.
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from notion.credentials import NotionCredentialStore
from notion.errors import NotionOperationError, NotionSnapshotNotReadyError
from notion.factory import NotionConnectorFacade
from notion.snapshot_store import NotionSnapshotStore
from notion.sync_scheduler import NotionSnapshotSyncWorker
from services.admin_data.errors import AdminDataError
from services.admin_data.models import CommittedReceiptDTO, AbsentReceiptDTO
from services.admin_data.notion_connector_data import (
    AdminNotionConnectorData, REQUEST_NOTION_SYNC_RUN, RENEW_NOTION_SYNC_RUN,
    FINISH_NOTION_SYNC_RUN, NOTION_SYNC_RUN_OPERATIONS, NOTION_SYNC_RUN_SCHEMA_REQUIREMENTS,
    NotionSyncRunOutputDTO, NotionLightSnapshotDTO,
)
from test_notion_connector_router_flow import TestNotionConnectorRouterFlow as _Flow


class _ExecutionFixture(unittest.TestCase):
    def setUp(self):
        self.flow = _Flow()
        self.flow.setUp()
        self.client = self.flow.client
        self.state = self.flow._admin_state
        self.connector = self.client.post('/api/connectors', json={'name': 'Ownership technical fixture'}).json()['connector']['id']
        self.client.post(f'/api/connectors/{self.connector}/auth/login')
        self.client.post(f'/api/connectors/{self.connector}/auth/poll')
        self.base = f'/api/connectors/{self.connector}'
        self.scope = {'selected_databases': [{'database_id': 'db-team', 'title': 'Team'}], 'selected_pages': []}
        self.store = NotionSnapshotStore()

    def tearDown(self):
        self.flow.tearDown()

    def facade(self):
        return NotionConnectorFacade(7, self.flow._store, self.connector)

    def sync_names(self):
        return [name for name, *_ in self.state.calls if name.startswith('notion.sync-run.')]

    def select(self):
        response = self.client.post(self.base + '/resources/select', json=self.scope)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def busy(self, retry='2026-09-16T00:00:02Z'):
        return {'status': 'busy', 'connector': self.state._connector(self.connector), 'run': None,
            'server_now': '2026-09-16T00:00:00.123456Z', 'retry_at': retry,
            'execution_policy': {'lease_seconds': 30, 'heartbeat_seconds': 10, 'renewal_budget_seconds': 1},
            'snapshot': None}



class ExecutionJourney(_ExecutionFixture):
    def test_save_manual_restart_and_read_use_accepted_version_without_legacy_writes(self):
        # Use the actual private-file provider: repeated reads harden permissions and
        # change ctime, but must not be mistaken for a credential replacement.
        before = self.facade()._credential_identity()
        NotionCredentialStore().effective_home(7)
        self.assertEqual(self.facade()._credential_identity(), before)
        result = self.select()
        self.assertEqual(self.sync_names(), ['notion.sync-run.request', 'notion.sync-run.renew', 'notion.sync-run.finish'])
        for name, _, auth in self.state.calls:
            if name in ('notion.sync-run.renew', 'notion.sync-run.finish'):
                self.assertEqual(auth, f'Bearer {self.state.service_token}')
                self.assertNotEqual(auth, f'Bearer {self.flow._actor.access_token}')
            elif name == 'notion.sync-run.request':
                self.assertEqual(auth, 'Bearer notion-oauth-token')
        self.assertFalse(any(name in ('notion.snapshot.save', 'notion.sync-snapshot.save', 'notion.sync-connector.patch') for name, *_ in self.state.calls))
        self.store.clear_connector(7, self.connector)
        snapshot = self.facade().get_current_snapshot()
        self.assertEqual(snapshot['identity'], result['snapshotIdentity'])
        self.assertTrue(any(name == 'notion.snapshot.current' for name, *_ in self.state.calls))
        manual = self.client.post(self.base + '/sync', json={})
        self.assertEqual(manual.status_code, 200, manual.text)
        self.assertTrue(manual.json()['synced'])

    def test_manual_busy_uses_server_time_and_does_not_build_or_mark_selection_saved(self):
        self.state.sync_scripts['notion.sync-run.request'] = [self.busy()]
        response = self.client.post(self.base + '/sync', json={})
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()['detail'], {'error_code': 'NOTION_SYNC_BUSY'})
        self.assertEqual(response.headers['Retry-After'], '2')
        self.assertEqual(len(self.flow.snapshot_calls), 0)
        self.assertEqual(self.sync_names(), ['notion.sync-run.request'])
        self.state.sync_scripts['notion.sync-run.request'] = [self.busy(None)]
        missing = self.client.post(self.base + '/sync', json={})
        self.assertEqual(missing.status_code, 409)
        self.assertNotIn('retry-after', missing.headers)

    def test_saved_selection_busy_and_upstream_failure_have_provable_marker(self):
        self.state.sync_scripts['notion.sync-run.request'] = [self.busy()]
        busy = self.client.post(self.base + '/resources/select', json=self.scope)
        self.assertEqual(busy.status_code, 409, busy.text)
        self.assertIs(busy.json()['detail']['selection_saved'], True)
        self.assertEqual(busy.headers['Retry-After'], '2')
        current = self.client.get(self.base).json()['connector']
        self.assertEqual(current['selected_databases'], ['db-team'])
        with patch('notion.sync.build_canonical_snapshot', new=AsyncMock(side_effect=NotionOperationError('private upstream output'))):
            failed = self.client.post(self.base + '/resources/select', json=self.scope)
        self.assertEqual(failed.status_code, 502, failed.text)
        self.assertIs(failed.json()['detail']['selection_saved'], True)
        self.assertNotIn('private upstream output', failed.text)
        self.assertEqual(self.state.calls[-1][0], 'notion.sync-run.finish')
        self.assertEqual(self.state.calls[-1][1]['outcome']['status'], 'failed')

    def test_replace_unknown_and_manual_failure_never_claim_selection_saved(self):
        with patch('notion.store.NotionConnectorStore.replace_connector_resources',
                   side_effect=AdminDataError('ADMIN_WRITE_RESULT_UNKNOWN', 503, outcome_unknown=True)):
            unknown = self.client.post(self.base + '/resources/select', json=self.scope)
        self.assertEqual(unknown.status_code, 503)
        self.assertNotIn('selection_saved', unknown.text)
        with patch('notion.sync.build_canonical_snapshot', new=AsyncMock(side_effect=NotionOperationError('redact me'))):
            failed = self.client.post(self.base + '/sync', json={})
        self.assertEqual(failed.status_code, 502, failed.text)
        self.assertNotIn('selection_saved', failed.text)

    def test_execution_capability_absent_fails_closed_but_old_reads_continue(self):
        self.state.execution_capability = False
        # Force the production catalog to observe the missing released capability.
        self.flow._owner.client.capabilities('00000000-0000-4000-8000-000000000777')
        response = self.client.post(self.base + '/sync', json={})
        self.assertEqual(response.status_code, 503, response.text)
        self.assertIn('ADMIN_CAPABILITY_UNAVAILABLE', response.text)
        self.assertEqual(self.sync_names(), [])
        self.assertEqual(self.client.get(self.base).status_code, 200)
        self.assertEqual(len(self.flow.snapshot_calls), 0)
        saved = self.client.post(self.base + '/resources/select', json=self.scope)
        self.assertEqual(saved.status_code, 503)
        self.assertIs(saved.json()['detail']['selection_saved'], True)

    def test_finish_rejected_preserves_lkg_and_never_publishes_unaccepted_version(self):
        self.select()
        connector = self.flow._store.get_connector(self.connector, 7)
        previous = self.store.load_accepted(7, connector)
        self.flow._snapshot_version = 'unaccepted-candidate'
        self.state.sync_scripts['notion.sync-run.finish'] = [{'__http_error__': 'NOTION_SYNC_CONTEXT_CHANGED'}]
        response = self.client.post(self.base + '/sync', json={})
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.store.load_accepted(7, self.flow._store.get_connector(self.connector, 7)), previous)
        finish = [value for name, value, _ in self.state.calls if name == 'notion.sync-run.finish']
        self.assertEqual(len(finish), 2)
        self.assertEqual(finish[-1]['outcome']['status'], 'succeeded')
        self.assertFalse((self.store._version_path(7, self.connector, 'unaccepted-candidate')).exists())

    def test_cache_failure_after_acceptance_recovers_through_admin_read(self):
        with patch.object(NotionSnapshotStore, 'cache_accepted', side_effect=OSError('synthetic disk failure')):
            result = self.select()
        self.assertTrue(result['synced'])
        recovered = self.facade().get_current_snapshot()
        self.assertEqual(recovered['identity'], result['snapshotIdentity'])
        self.assertTrue(any(name == 'notion.snapshot.current' for name, *_ in self.state.calls))

    def test_legacy_pointer_unknown_body_fields_and_corrupt_cache_cannot_enter_thread(self):
        self.select()
        connector = self.flow._store.get_connector(self.connector, 7)
        snapshot = self.store.load_accepted(7, connector)
        stale = deepcopy(snapshot)
        stale['metadata']['snapshot_version'] = stale['identity']['snapshot_version'] = 'late-old-writer'
        self.store.publish_current(7, self.connector, stale)
        self.assertEqual(self.store.load_accepted(7, connector), snapshot)
        for mutate in ('body', 'config', 'page-body', 'identity', 'fetched'):
            bad = deepcopy(snapshot)
            if mutate == 'body': bad['pages'] = {'page-team': {'markdown': 'secret'}}
            elif mutate == 'config': bad['connector']['config'] = {'private': 'secret'}
            elif mutate == 'page-body': bad['index'][0]['markdown'] = 'secret'
            elif mutate == 'identity': bad['identity']['sync_cursor'] = 'wrong'
            else: bad['metadata']['fetched_at'] = '2026-07-04T15:00:00Z'
            with self.subTest(mutate=mutate), self.assertRaises(NotionSnapshotNotReadyError):
                self.store.accepted_payload(bad, connector)
        path = self.store._version_path(7, self.connector, snapshot['metadata']['snapshot_version'])
        path.write_text('{broken', encoding='utf-8')
        self.assertEqual(self.facade().get_current_snapshot(), snapshot)
        self.assertEqual(self.store.load_accepted(7, connector), snapshot)
        # Legacy Admin read envelopes are wide JSON; strict validation still blocks them.
        self.store.clear_connector(7, self.connector)
        self.state.snapshots[self.connector][-1]['snapshot']['index'][0]['markdown'] = 'secret'
        with self.assertRaises(NotionSnapshotNotReadyError):
            self.facade().get_current_snapshot()

    def test_opaque_version_key_is_bounded_and_selected_thread_projection_stays_metadata_only(self):
        self.flow._snapshot_version = '../opaque/version'
        self.select()
        connector = self.flow._store.get_connector(self.connector, 7)
        snapshot = self.store.load_accepted(7, connector)
        path = self.store._version_path(7, self.connector, '../opaque/version')
        self.assertEqual(path.parent, self.store._connector_root(7, self.connector))
        self.assertEqual(len(path.name), len('snapshot-.json') + 64)
        workspace = Path(self.flow._tmp.name) / 'agentdata' / 'agent-workspaces' / 'ownership-thread'
        workspace.mkdir(parents=True)
        credentials = NotionCredentialStore(workspace_root_provider=lambda: workspace.parent)
        projected_store = NotionSnapshotStore(credentials)
        facade = NotionConnectorFacade(7, self.flow._store, self.connector,
            credential_store=credentials, snapshot_store=projected_store)
        facade.materialize_workspace(workspace)
        self.assertFalse((workspace / '.notion' / 'pages' / 'page-team.json').exists())
        self.assertEqual(snapshot['pages'], {})
        connector['sources'] = []
        result = projected_store.project_thread(7, connector, workspace, snapshot=snapshot)
        self.assertFalse(result.available)


class AsyncExecutionJourney(_ExecutionFixture, unittest.IsolatedAsyncioTestCase):
    # Explicit async cases use the same normal public-facade method; no shadow entry.
    async def test_scheduler_busy_and_not_due_skip_without_build_or_failure(self):
        self.select()
        for status in ('busy', 'not_due'):
            reply = self.busy(None)
            reply['status'] = status
            self.state.sync_scripts['notion.sync-run.claim'] = [reply]
            count = len(self.flow.snapshot_calls)
            worker = NotionSnapshotSyncWorker(candidate_provider=self.flow._background_store.list_sync_candidates,
                facade_factory=lambda actor, connector: NotionConnectorFacade(actor, self.flow._background_store, connector))
            outcome = await worker.sync_due_once()
            self.assertEqual((outcome.attempted, outcome.succeeded, outcome.failed), (1, 0, 0))
            self.assertEqual(len(self.flow.snapshot_calls), count)

    async def test_renew_rejection_stops_before_remote_and_never_finishes(self):
        self.state.sync_scripts['notion.sync-run.renew'] = [{'__http_error__': 'NOTION_SYNC_RUN_INVALID'}]
        facade = NotionConnectorFacade(7, self.flow._store, self.connector)
        with self.assertRaises(AdminDataError):
            await facade.sync()
        self.assertEqual(len(self.flow.snapshot_calls), 0)
        self.assertEqual(self.sync_names(), ['notion.sync-run.request', 'notion.sync-run.renew'])

    async def test_cancel_builder_waits_for_owned_work_and_finishes_once(self):
        entered, cancelled = asyncio.Event(), asyncio.Event()
        async def build(**_kwargs):
            entered.set()
            try: await asyncio.Event().wait()
            finally: cancelled.set()
        facade = NotionConnectorFacade(7, self.flow._store, self.connector)
        with patch('notion.sync.build_canonical_snapshot', new=build):
            task = asyncio.create_task(facade.sync())
            await asyncio.wait_for(entered.wait(), 3)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError): await task
        self.assertTrue(cancelled.is_set())
        finishes = [value['outcome'] for name, value, _ in self.state.calls if name == 'notion.sync-run.finish']
        self.assertEqual(finishes, [{'status': 'cancelled', 'error_code': 'NOTION_SYNC_CANCELLED'}])
        self.assertFalse(list(self.store._connector_root(7, self.connector).glob('snapshot-*.json')))

    async def test_serial_heartbeat_uses_server_policy_while_scan_is_active(self):
        self.select()
        original = self.state._sync_reply
        def replies(name, value):
            result = original(name, value)
            if 'execution_policy' in result:
                result['execution_policy'] = {'lease_seconds': 4, 'heartbeat_seconds': 1, 'renewal_budget_seconds': 1}
            return result
        async def slow(**kwargs):
            await asyncio.sleep(1.1)
            return self.flow._mock_build_snapshot(**kwargs)
        before = len(self.sync_names())
        with patch.object(self.state, '_sync_reply', side_effect=replies), patch('notion.sync.build_canonical_snapshot', new=slow):
            result = await NotionConnectorFacade(7, self.flow._store, self.connector).sync()
        self.assertTrue(result['synced'])
        self.assertEqual(self.sync_names()[before:], ['notion.sync-run.request', 'notion.sync-run.renew',
            'notion.sync-run.renew', 'notion.sync-run.finish'])

    async def test_cancel_during_renewal_waits_for_original_result_but_expired_budget_never_finishes(self):
        import threading
        import time
        entered = threading.Event()
        original = self.flow._store.renew_sync_run
        def delayed(*args):
            entered.set()
            time.sleep(1.1)  # Admin fixture's server-owned renewal budget is exactly one second.
            return original(*args)
        facade = self.facade()
        with patch.object(self.flow._store, 'renew_sync_run', side_effect=delayed):
            task = asyncio.create_task(facade.sync())
            await asyncio.wait_for(asyncio.to_thread(entered.wait), 3)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(self.sync_names(), ['notion.sync-run.request', 'notion.sync-run.renew'])
        self.assertEqual(len(self.flow.snapshot_calls), 0)

    async def test_renew_budget_timeout_stops_without_retry_or_terminal_write(self):
        import time
        original = self.flow._store.renew_sync_run
        def delayed(*args):
            time.sleep(1.1)
            return original(*args)
        with patch.object(self.flow._store, 'renew_sync_run', side_effect=delayed):
            with self.assertRaises(AdminDataError) as error:
                await self.facade().sync()
        self.assertEqual(error.exception.code, 'NOTION_SYNC_RENEWAL_TIMEOUT')
        self.assertTrue(error.exception.outcome_unknown)
        self.assertEqual(self.sync_names(), ['notion.sync-run.request', 'notion.sync-run.renew'])
        self.assertEqual(len(self.flow.snapshot_calls), 0)


class ExecutionReceiptContracts(_ExecutionFixture):
    def test_unknown_write_recovers_only_original_strict_user_or_background_receipt(self):
        from types import SimpleNamespace
        from notion.store import _process_worker_id
        worker = _process_worker_id()
        response = self.state._sync_reply('notion.sync-run.request', {'connector_id': self.connector, 'worker_id': worker})
        output = NotionSyncRunOutputDTO.model_validate(response)
        class ReceiptClient:
            _config = SimpleNamespace(service_client_id='dream-service')
            def __init__(self, result):
                self.result, self.executions, self.receipts = result, [], []
            def supports(self, operations, requirements):
                return operations is NOTION_SYNC_RUN_OPERATIONS and requirements is NOTION_SYNC_RUN_SCHEMA_REQUIREMENTS
            def execute(self, operation, payload, request_id, **kwargs):
                self.executions.append((operation, payload, request_id, kwargs))
                raise AdminDataError('ADMIN_TIMEOUT', 504, request_id, True)
            def receipt(self, operation, request_id, **kwargs):
                self.receipts.append((operation, request_id, kwargs))
                return CommittedReceiptDTO(status='committed', operation=operation.capability.name, request_id=request_id, result=self.result)
            background_receipt = receipt
        from services.admin_data.notion_connector_data import NotionSyncRunRequestInputDTO, NotionSyncRunKeyDTO
        request = NotionSyncRunRequestInputDTO(connector_id=self.connector, worker_id=worker, authority=None)
        client = ReceiptClient(output)
        actual = AdminNotionConnectorData(client).execute(REQUEST_NOTION_SYNC_RUN, request,
            '00000000-0000-4000-8000-000000000777', access_token='user-fixture')
        self.assertEqual(actual, output)
        self.assertEqual(len(client.executions), 1)
        self.assertEqual(client.receipts[0][2], {'access_token': 'user-fixture'})
        renewed = deepcopy(response); renewed['status'] = 'renewed'
        client = ReceiptClient(NotionSyncRunOutputDTO.model_validate(renewed))
        key = NotionSyncRunKeyDTO(connector_id=self.connector, worker_id=worker,
            run_id=output.run.run_id, fence_epoch=output.run.fence_epoch)
        AdminNotionConnectorData(client).execute(RENEW_NOTION_SYNC_RUN, key,
            '00000000-0000-4000-8000-000000000888', access_token=None, background_connector_id=self.connector)
        self.assertEqual(client.receipts[0][2], {'connector_id': self.connector})
        self.assertEqual(len(client.executions), 1)
        # A committed terminal receipt recovers the original accepted payload, not a
        # newly dispatched finish or a wider legacy JSON snapshot.
        snapshot = self.flow._mock_build_snapshot(self.state._connector(self.connector), [], self.connector, None)
        outcome = {'status': 'succeeded', 'workspace_id': self.connector, 'snapshot': snapshot, 'synced_resources': []}
        finished = self.state._sync_reply('notion.sync-run.finish', {'connector_id': self.connector, 'outcome': outcome})
        from services.admin_data.notion_connector_data import NotionSyncRunFinishInputDTO
        payload = NotionSyncRunFinishInputDTO(**key.model_dump(), outcome=outcome)
        client = ReceiptClient(NotionSyncRunOutputDTO.model_validate(finished))
        accepted = AdminNotionConnectorData(client).execute(FINISH_NOTION_SYNC_RUN, payload,
            '00000000-0000-4000-8000-000000000999', access_token=None, background_connector_id=self.connector)
        self.assertEqual(accepted.snapshot.model_dump(mode='json'), snapshot)
        self.assertEqual(len(client.executions), 1)
        class AbsentClient(ReceiptClient):
            def receipt(self, operation, request_id, **kwargs):
                self.receipts.append((operation, request_id, kwargs))
                return AbsentReceiptDTO(status='absent', operation=operation.capability.name, request_id=request_id)
        client = AbsentClient(output)
        with self.assertRaises(AdminDataError) as error:
            AdminNotionConnectorData(client).execute(REQUEST_NOTION_SYNC_RUN, request,
                '00000000-0000-4000-8000-000000000777', access_token='user-fixture')
        self.assertTrue(error.exception.outcome_unknown)
        self.assertEqual(len(client.executions), 1)
        self.assertEqual(len(client.receipts), 1)

    def test_strict_new_snapshot_dto_rejects_nested_unknown_and_malformed_shape(self):
        self.select()
        connector = self.flow._store.get_connector(self.connector, 7)
        good = self.store.load_accepted(7, connector)
        from pydantic import ValidationError
        for mutate in ('index', 'pages', 'connector', 'count', 'coverage'):
            bad = deepcopy(good)
            if mutate == 'index': bad['index'][0]['unknown'] = 'body'
            elif mutate == 'pages': bad['pages'] = {'page-team': {}}
            elif mutate == 'connector': bad['connector']['config'] = {}
            elif mutate == 'count': bad['databases'][0]['page_count'] = 2
            else: bad['index'] = []
            with self.subTest(mutate=mutate), self.assertRaises(ValidationError):
                NotionLightSnapshotDTO.model_validate(bad)


if __name__ == '__main__':
    unittest.main()
