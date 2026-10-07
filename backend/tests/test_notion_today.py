# [Sync] 2026-10-07: use Admin-accepted strict fixtures and prove late accepted-version changes instead of local pointer recency.
# [Input] Real Calendar router/facade/index Provider, isolated Admin/OAuth fixtures and injected metadata operations.
# [Output] Snapshot-first full read/verify/refresh/date/authorization journey with no Search/body/config writes.
# [Pos] Provider-free technical contracts in backend/tests; no real Notion account or business database.
# [Sync] 2026-10-06: replace Search enumeration tests with selected canonical snapshot and today-update verification.
# [Sync] 2026-10-06: database selection uses the actual query/builder/persistence chain; explicit sync repairs legacy time-less indexes.
from __future__ import annotations

import asyncio
import json
import sys
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, patch

import config
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_notion_connector_router_flow as existing_flow
from notion.credentials import NotionCredentialStore, NOTION_AUTH_FILENAME
from notion.operations import NotionOperationClient
from notion.snapshot_store import NotionSnapshotStore
from notion.today import (NotionTodayError, api_version, day_context, page_identity,
                          read_documents, remote_error, safe_url, timestamp)

NOW = datetime(2026, 10, 6, 12, tzinfo=timezone.utc)
DAY = '2026-10-06'


def record(key='page-a', created='2026-10-06T00:00:00Z', edited='2026-10-06T01:00:00Z', **extra):
    return {'page_id': key, 'title': 'A', 'url': 'https://www.notion.so/a',
            'created_time': created, 'last_edited_time': edited, **extra}


def upstream(row):
    return {**row, 'object': 'page', 'id': row['page_id']}


def snapshot(rows, version='snap-fixture', connector='fixture'):
    return {'metadata': {'workspace_id': connector, 'resource_connector_id': connector,
                         'snapshot_version': version, 'source_revision': version, 'sync_cursor': 'fixture',
                         'fetched_at': '2026-10-06T02:00:00Z'},
            'index': rows, 'databases': [], 'database_pages': {}, 'pages': {}}


def accepted_fixture(rows, connector, version="snap-fixture"):
    identity = {"workspace_id": connector, "resource_connector_id": connector,
        "snapshot_version": version, "source_revision": version, "sync_cursor": "fixture"}
    index = [{"last_edited": row.get("last_edited_time") or "", **row} for row in rows]
    return {"metadata": {**identity, "fetched_at": "2026-10-06T02:00:00Z", "state": "snapshot_ready"},
        "connector": {"id": connector, "name": "Calendar fixture", "platform": "notion",
            "auth_status": "authenticated", "last_synced_at": None, "selected_databases": [],
            "selected_pages": [row["page_id"] for row in rows]},
        "index": index, "databases": [], "database_pages": {}, "pages": {}, "identity": identity}


class SnapshotProjection(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = TemporaryDirectory(prefix='notion-calendar-snapshot-unit-')
        self.client = NotionOperationClient(Path(self.tmp.name), api_version='2026-03-11')
        self.client.get_page_metadata = AsyncMock()
        self.context = day_context('UTC', DAY, NOW)

    async def asyncTearDown(self):
        self.tmp.cleanup()

    async def test_initial_snapshot_is_immediate_without_remote_then_verifies_only_today_updates(self):
        rows = [record(), record('historic', '2026-09-01T00:00:00Z', '2026-09-02T00:00:00Z'),
                record('edited', '2026-09-01T00:00:00Z')]
        initial = await read_documents(None, 'fixture', self.context, snapshot(rows))
        self.assertEqual(initial['counts'], {'created': 1, 'edited': 1, 'total': 2})
        self.assertEqual(initial['verificationState'], 'pending')
        self.assertEqual(initial['snapshotFetchedAt'], '2026-10-06T02:00:00+00:00')
        self.client.get_page_metadata.assert_not_awaited()
        self.client.get_page_metadata.side_effect = lambda key: upstream(next(row for row in rows if row['page_id'] == key))
        final = await read_documents(self.client, 'fixture', self.context, snapshot(rows))
        self.assertEqual([call.args[0] for call in self.client.get_page_metadata.await_args_list], ['page-a', 'edited'])
        self.assertEqual(final['verificationState'], 'complete')
        self.assertEqual(final['counts']['total'], 2)

    async def test_historical_creation_never_calls_remote_even_when_requested(self):
        rows = [record('old', '2026-09-01T00:00:00Z'), record('edited-only', '2026-08-01T00:00:00Z', '2026-09-01T01:00:00Z')]
        result = await read_documents(self.client, 'fixture', day_context('UTC', '2026-09-01', NOW), snapshot(rows))
        self.assertEqual([row['pageId'] for row in result['items']], ['old'])
        self.assertEqual(result['verificationState'], 'not_required')
        self.client.get_page_metadata.assert_not_awaited()

    async def test_half_open_interval_dual_markers_missing_fields_and_stable_identity(self):
        identity = 'bff9f08a-0506-49eb-a6e2-b7ea72b78154'
        rows = [record(identity), record(identity.replace('-', '')), record('b'),
                record('end', '2026-10-07T00:00:00Z', '2026-10-07T00:00:00Z'),
                record('invalid', 'no', None), record('edited-only', None), record('untitled', title='')]
        result = await read_documents(None, 'fixture', self.context, snapshot(rows))
        self.assertEqual(result['counts'], {'created': 3, 'edited': 1, 'total': 4})
        self.assertEqual(result['paginationState'], 'partial')
        self.assertIn('metadata_missing', result['partialReasons'])
        self.assertEqual([row['pageId'] for row in result['items']][:3], ['b', identity, 'untitled'])
        self.assertEqual(result['items'][2]['title'], '未命名文档')
        self.assertTrue(result['items'][0]['createdOnDate'] and result['items'][0]['editedOnDate'])
        self.assertIsNone(result['items'][3]['createdTime'])

    async def test_empty_legacy_and_absent_snapshots_are_not_normal_empty_results(self):
        for value, reason in [(None, 'snapshot_unavailable'), (snapshot([{'page_id': 'legacy', 'last_edited': DAY}]), 'metadata_missing')]:
            result = await read_documents(None, 'fixture', self.context, value)
            self.assertEqual(result['counts']['total'], 0)
            self.assertEqual(result['paginationState'], 'partial')
            self.assertIn(reason, result['partialReasons'])
        empty = await read_documents(None, 'fixture', self.context, snapshot([]))
        self.assertEqual(empty['paginationState'], 'complete')

    async def test_rate_limit_stops_remaining_requests_and_keeps_same_context_snapshot(self):
        self.client.get_page_metadata.side_effect = NotionTodayError('NOTION_RATE_LIMITED', 429, retry_after=3)
        result = await read_documents(self.client, 'fixture', self.context, snapshot([record(), record('b')]))
        self.assertEqual(self.client.get_page_metadata.await_count, 1)
        self.assertEqual(result['retryAfter'], 3)
        self.assertEqual(result['counts']['total'], 2)
        self.assertEqual(result['verificationState'], 'partial')

    async def test_permission_deleted_archived_and_identity_mismatch_do_not_become_successful_rows(self):
        rows = [record(), record('b'), record('c'), record('d')]
        self.client.get_page_metadata.side_effect = [NotionTodayError('NOTION_PERMISSION_DENIED', 403),
            NotionTodayError('NOTION_RESOURCE_UNAVAILABLE', 404), upstream({**rows[2], 'archived': True}),
            upstream(record('wrong'))]
        result = await read_documents(self.client, 'fixture', self.context, snapshot(rows))
        self.assertEqual([row['pageId'] for row in result['items']], ['d'])
        self.assertEqual(result['verificationState'], 'partial')
        self.assertIn('metadata_identity_mismatch', result['partialReasons'])

    async def test_auth_expiry_clears_instead_of_returning_partial_snapshot(self):
        self.client.get_page_metadata.side_effect = NotionTodayError('NOTION_AUTH_EXPIRED', 401)
        with self.assertRaises(NotionTodayError):
            await read_documents(self.client, 'fixture', self.context, snapshot([record()]))

    async def test_total_budget_cancels_a_slow_request_while_snapshot_remains_available(self):
        async def slow(_):
            await asyncio.sleep(1)
        self.client.get_page_metadata.side_effect = slow
        with patch.object(self.client, '_timeout_seconds', return_value=0.01):
            result = await read_documents(self.client, 'fixture', self.context, snapshot([record()]))
        self.assertEqual(result['counts']['total'], 1)
        self.assertEqual(result['verificationState'], 'partial')
        self.assertIn('NOTION_UPSTREAM_UNAVAILABLE', result['partialReasons'])

    async def test_metadata_only_cli_contract_never_reads_body_and_uses_explicit_version(self):
        self.client._run_endpoint = AsyncMock(return_value=upstream(record()))
        del self.client.get_page_metadata
        await self.client.get_page_metadata('page-a')
        self.client._run_endpoint.assert_awaited_once_with('v1/pages/page-a')
        with self.assertRaises(NotionTodayError):
            await self.client.get_page_metadata('../other/markdown')
        with patch.object(config, 'NOTION_TODAY_API_VERSION', ''):
            with self.assertRaises(NotionTodayError):
                await NotionOperationClient(Path(self.tmp.name)).get_page_metadata('page-a')


class TimeAndPolicy(unittest.TestCase):
    def test_dates_timezone_dst_and_invalid_input(self):
        for day, hours in [('2026-03-08', 23), ('2026-11-01', 25)]:
            ctx = day_context('America/New_York', day, NOW)
            self.assertEqual((timestamp(ctx['intervalEnd'])-timestamp(ctx['intervalStart'])).total_seconds()/3600, hours)
        for day in ['invalid', '2026-02-30', '20261006', '9999-12-31']:
            with self.assertRaises(NotionTodayError): day_context('UTC', day, NOW)
        for zone in [None, '', 'invalid/zone']:
            with self.assertRaises(NotionTodayError): day_context(zone, DAY, NOW)
        self.assertIsNone(timestamp('2026-10-06T00:00:00'))
        self.assertEqual(page_identity('BFF9F08A050649EBA6E2B7EA72B78154'), 'bff9f08a-0506-49eb-a6e2-b7ea72b78154')

    def test_explicit_api_policy_url_and_safe_errors(self):
        for value in ['', 'latest', '2026-02-30']:
            with patch.object(config, 'NOTION_TODAY_API_VERSION', value), self.assertRaises(NotionTodayError): api_version()
        with patch.object(config, 'NOTION_ALLOWED_URL_HOSTS', frozenset(['www.notion.so', 'app.notion.com'])):
            self.assertEqual(safe_url('https://app.notion.com/p/example'), 'https://app.notion.com/p/example')
            self.assertEqual(safe_url('https://www.notion.so/a'), 'https://www.notion.so/a')
            for url in ['http://www.notion.so/a', 'https://www.notion.so.evil/a', 'https://@www.notion.so/a', 'https://www.notion.so:444/a', 'javascript:x']:
                self.assertIsNone(safe_url(url))
        for status, code in [(401,'NOTION_AUTH_EXPIRED'),(403,'NOTION_PERMISSION_DENIED'),(404,'NOTION_RESOURCE_UNAVAILABLE'),(429,'NOTION_RATE_LIMITED'),(500,'NOTION_UPSTREAM_UNAVAILABLE')]:
            error = remote_error(json.dumps({'status':status,'message':'secret credential','headers':{'Retry-After':'9'}}), '')
            self.assertEqual(error.code, code)
            self.assertNotIn('secret', str(error))
            if status == 429: self.assertEqual(error.retry_after, 9)


class DatabaseSelectionCalendarJourney(unittest.TestCase):
    """Only the external CLI transport is injected; selection builds the real index."""

    def setUp(self):
        self.flow = existing_flow.TestNotionConnectorRouterFlow()
        self.flow.setUp()
        # The old connector harness replaces the entire snapshot builder. This
        # journey must exercise that production boundary, including row flattening.
        self.flow._patches[4].stop()
        self.client = self.flow.client
        self.connector = self.client.post('/api/connectors', json={'name': 'Database calendar fixture'}).json()['connector']['id']
        self.client.post(f'/api/connectors/{self.connector}/auth/login')
        self.client.post(f'/api/connectors/{self.connector}/auth/poll')
        self.rows = [record('row-created'), record('row-edited', '2026-09-01T00:00:00Z')]
        self.calls = []

        async def transport(endpoint, payload=None):
            self.calls.append((endpoint, deepcopy(payload)))
            if endpoint == 'v1/data_sources/db-calendar/query':
                if not payload.get('start_cursor'):
                    return {'results': [upstream(self.rows[0])], 'has_more': True, 'next_cursor': 'next-row'}
                self.assertEqual(payload['start_cursor'], 'next-row')
                return {'results': [upstream(self.rows[1])], 'has_more': False, 'next_cursor': None}
            for row in self.rows:
                if endpoint == f"v1/pages/{row['page_id']}":
                    return upstream(row)
            raise AssertionError(f'unexpected metadata/body/Search operation: {endpoint}')

        self.transport = patch.object(NotionOperationClient, '_run_endpoint', new=AsyncMock(side_effect=transport))
        self.remote = self.transport.start()
        self.version = patch.object(config, 'NOTION_TODAY_API_VERSION', '2026-03-11')
        self.version.start()
        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None): return NOW
        self.clock = patch('notion.factory.datetime', FixedDateTime)
        self.clock.start()
        selected = self.client.post(f'/api/connectors/{self.connector}/resources/select', json={
            'selected_databases': [{'database_id': 'db-calendar', 'title': 'Selected database'}], 'selected_pages': []})
        self.assertEqual(selected.status_code, 200, selected.text)
        self.assertEqual(selected.json()['pageCount'], 2)
        self.store = NotionSnapshotStore()
        self.endpoint = f'/api/connectors/{self.connector}/notion/documents?date_key={DAY}'

    def tearDown(self):
        self.clock.stop()
        self.version.stop()
        self.transport.stop()
        self.flow.tearDown()

    def test_database_rows_persist_then_read_verify_history_refresh_and_clear(self):
        stored = self.store.load_accepted(7, self.flow._store.get_connector(self.connector, 7))
        self.assertEqual(stored['database_pages']['db-calendar'], stored['index'])
        self.assertEqual(stored['pages'], {})
        self.assertEqual([row['created_time'] for row in stored['index']], [row['created_time'] for row in self.rows])
        self.assertEqual([row['last_edited_time'] for row in stored['index']], [row['last_edited_time'] for row in self.rows])
        self.assertEqual([call[0] for call in self.calls], ['v1/data_sources/db-calendar/query'] * 2)
        before = deepcopy(self.flow._admin_state.connectors)
        initial = self.client.get(self.endpoint)
        self.assertEqual(initial.status_code, 200, initial.text)
        self.assertEqual(initial.json()['candidateCount'], 2)
        self.assertEqual(initial.json()['counts'], {'created': 1, 'edited': 1, 'total': 2})
        self.assertEqual(self.remote.await_count, 2)
        version = stored['metadata']['snapshot_version']
        checked = self.client.get(self.endpoint + f'&validate_remote=true&snapshot_version={version}')
        self.assertEqual(checked.status_code, 200, checked.text)
        self.assertEqual(checked.json()['verificationState'], 'complete')
        self.assertEqual([call[0] for call in self.calls[2:]], ['v1/pages/row-created', 'v1/pages/row-edited'])
        historic = self.client.get(self.endpoint.replace(DAY, '2026-09-01') + f'&validate_remote=true&snapshot_version={version}')
        self.assertEqual(historic.status_code, 200, historic.text)
        self.assertEqual([row['pageId'] for row in historic.json()['items']], ['row-edited'])
        for _ in range(2):
            self.assertEqual(self.client.get(self.endpoint).json()['counts']['total'], 2)
        self.assertEqual(self.remote.await_count, 4)
        self.assertEqual(before, self.flow._admin_state.connectors)
        self.assertEqual(stored, self.store.load_accepted(7, self.flow._store.get_connector(self.connector, 7)))
        cleared = self.client.post(f'/api/connectors/{self.connector}/resources/select', json={'selected_databases': [], 'selected_pages': []})
        self.assertEqual(cleared.status_code, 200, cleared.text)
        self.assertEqual(self.client.get(self.endpoint).json()['candidateCount'], 0)
        self.assertEqual(self.remote.await_count, 4)

    def test_legacy_database_index_is_partial_until_public_explicit_sync_restores_times(self):
        legacy = self.store.load_accepted(7, self.flow._store.get_connector(self.connector, 7))
        for row in legacy['index'] + legacy['database_pages']['db-calendar']:
            row.pop('created_time', None)
            row.pop('last_edited_time', None)
        # A legacy accepted DTO is recovered through the existing Admin read. Local
        # version caches are removed only inside this explicitly isolated fixture.
        self.store.clear_connector(7, self.connector)
        self.flow._admin_state.snapshots[self.connector][-1]["snapshot"] = deepcopy(legacy)
        self.store.publish_current(7, self.connector, legacy)
        missing = self.client.get(self.endpoint)
        self.assertEqual(missing.status_code, 200, missing.text)
        self.assertEqual(missing.json()['candidateCount'], 2)
        self.assertEqual(missing.json()['paginationState'], 'partial')
        self.assertEqual(missing.json()['counts']['total'], 0)
        self.assertIn('metadata_missing', missing.json()['partialReasons'])
        self.assertEqual(self.remote.await_count, 2)
        synced = self.client.post(f'/api/connectors/{self.connector}/sync', json={})
        self.assertEqual(synced.status_code, 200, synced.text)
        self.assertEqual(synced.json()['pageCount'], 2)
        ready = self.client.get(self.endpoint)
        self.assertEqual(ready.status_code, 200, ready.text)
        self.assertEqual(ready.json()['paginationState'], 'complete')
        self.assertEqual(ready.json()['counts']['total'], 2)
        self.assertEqual(self.remote.await_count, 4)


class SnapshotPublicJourney(unittest.TestCase):
    def setUp(self):
        self.flow = existing_flow.TestNotionConnectorRouterFlow(); self.flow.setUp()
        self.client = self.flow.client
        self.version = patch.object(config, 'NOTION_TODAY_API_VERSION', '2026-03-11'); self.version.start()
        self.connector = self.client.post('/api/connectors', json={'name':'Calendar snapshot fixture'}).json()['connector']['id']
        self.client.post(f'/api/connectors/{self.connector}/auth/login')
        self.client.post(f'/api/connectors/{self.connector}/auth/poll')
        self.rows = [record(), record('historic', '2026-09-01T00:00:00Z', '2026-09-02T00:00:00Z')]
        selected = self.client.post(f'/api/connectors/{self.connector}/resources/select', json={
            'selected_databases': [], 'selected_pages': [{'page_id': row['page_id'], 'title': row['title']} for row in self.rows]})
        self.assertEqual(selected.status_code, 200, selected.text)
        self.store = NotionSnapshotStore(); self.payload = accepted_fixture(self.rows, self.connector)
        self.flow._admin_state._save_snapshot(self.connector, {"snapshot": self.payload})
        self.store.cache_accepted(7, self.flow._store.get_connector(self.connector, 7), self.payload)
        self.endpoint = f'/api/connectors/{self.connector}/notion/documents?date_key={DAY}'
        self.verify = self.endpoint + '&validate_remote=true&snapshot_version=snap-fixture'
        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None): return NOW
        self.clock = patch('notion.factory.datetime', FixedDateTime); self.clock.start()

    def tearDown(self):
        self.clock.stop(); self.version.stop(); self.flow.tearDown()

    def test_read_verify_refresh_history_current_scope_and_no_business_writes(self):
        before = deepcopy(self.flow._admin_state.connectors)
        with patch.object(NotionOperationClient, '_run_endpoint', new=AsyncMock(return_value=upstream(self.rows[0]))) as remote:
            initial = self.client.get(self.endpoint)
            self.assertEqual(initial.status_code, 200, initial.text)
            self.assertEqual(initial.json()['verificationState'], 'pending')
            remote.assert_not_awaited()
            checked = self.client.get(self.verify)
            self.assertEqual(checked.status_code, 200, checked.text)
            self.assertEqual(checked.json()['verificationState'], 'complete')
            remote.assert_awaited_once_with('v1/pages/page-a')
            historic = self.client.get(self.endpoint.replace(DAY, '2026-09-01') + '&validate_remote=true&snapshot_version=snap-fixture')
            self.assertEqual(historic.status_code, 200, historic.text)
            self.assertEqual([row['pageId'] for row in historic.json()['items']], ['historic'])
            self.client.get(self.endpoint); self.client.get(self.endpoint)
            self.assertEqual(remote.await_count, 1)
        self.assertEqual(before, self.flow._admin_state.connectors)
        self.assertEqual(self.store.load_accepted(7, self.flow._store.get_connector(self.connector, 7)), self.payload)
        # A removed selection must hide the corresponding cached entry immediately.
        cleared = self.client.post(f'/api/connectors/{self.connector}/resources/select', json={'selected_databases': [], 'selected_pages': []})
        self.assertEqual(cleared.status_code, 200)
        empty = self.client.get(self.endpoint)
        self.assertEqual(empty.json()['items'], [])

    def test_missing_api_version_keeps_snapshot_and_connector_list_available_then_recovers(self):
        with patch.object(NotionOperationClient, '_run_endpoint', new=AsyncMock(return_value=upstream(self.rows[0]))) as remote:
            for value in ['', 'latest', '2026-02-30']:
                with self.subTest(version=value), patch.object(config, 'NOTION_TODAY_API_VERSION', value):
                    self.assertEqual(self.client.get('/api/connectors').status_code, 200)
                    self.assertEqual(self.client.get(self.endpoint).status_code, 200)
                    response = self.client.get(self.verify)
                    self.assertEqual(response.status_code, 503, response.text)
                    self.assertEqual(response.json()['detail']['error_code'], 'NOTION_API_VERSION_UNCONFIGURED')
            remote.assert_not_awaited()
            self.assertEqual(self.client.get(self.verify).status_code, 200)
            remote.assert_awaited_once()

    def test_compatibility_route_ownership_dates_timezone_and_stale_version(self):
        with patch.object(NotionOperationClient, '_run_endpoint', new=AsyncMock()) as remote:
            self.assertEqual(self.client.get(self.endpoint.replace('/documents?', '/today?')).status_code, 200)
            self.assertEqual(self.client.get(self.endpoint.replace(self.connector,'00000000-0000-4000-8000-000000000999')).status_code,404)
            self.assertEqual(self.client.get(self.endpoint.replace(DAY, '2026-02-30')).status_code,400)
            self.assertEqual(self.client.get(self.verify.replace('snap-fixture','old')).status_code,409)
            self.flow._admin_state.timezone = None
            self.assertEqual(self.client.get(self.endpoint).status_code,503)
            remote.assert_not_awaited()

    def test_auth_revocation_rate_limit_and_page_permission_have_distinct_public_outcomes(self):
        for error in [NotionTodayError('NOTION_RATE_LIMITED',429,retry_after=3),NotionTodayError('NOTION_AUTH_EXPIRED',401),NotionTodayError('NOTION_PERMISSION_DENIED',403)]:
            with self.subTest(code=error.code), patch.object(NotionOperationClient,'_run_endpoint',new=AsyncMock(side_effect=error)):
                response = self.client.get(self.verify)
                if error.status == 401:
                    self.assertEqual(response.status_code,401)
                    self.assertNotIn('items',response.json())
                else:
                    self.assertEqual(response.status_code,200,response.text)
                    self.assertEqual(response.json()['verificationState'],'partial')
                    self.assertEqual(response.json()['counts']['total'],0 if error.status == 403 else 1)
                    if error.status == 429: self.assertEqual(response.json()['retryAfter'],3)

    def test_late_responses_recheck_connector_credential_snapshot_and_midnight(self):
        original = deepcopy(self.flow._admin_state.connectors[self.connector])
        auth_file = NotionCredentialStore().effective_home(7) / NOTION_AUTH_FILENAME
        saved = auth_file.read_bytes()
        for change, code in [('connector','NOTION_CONTEXT_CHANGED'), ('credential','NOTION_CONTEXT_CHANGED'), ('snapshot','NOTION_SNAPSHOT_CHANGED'), ('midnight','NOTION_DATE_CONTEXT_CHANGED')]:
            async def read(*_args, **_kwargs):
                if change == 'connector': self.flow._admin_state.connectors[self.connector]['updated_at'] = '2026-10-06T13:00:00Z'
                elif change == 'credential': auth_file.write_bytes(saved+b'\n')
                elif change == 'snapshot': self.flow._admin_state._save_snapshot(self.connector, {'snapshot': accepted_fixture(self.rows,self.connector,'new')})
                return upstream(self.rows[0])
            with patch.object(NotionOperationClient,'_run_endpoint',new=AsyncMock(side_effect=read)):
                if change == 'midnight':
                    with patch('notion.factory.datetime') as clock:
                        clock.now.side_effect = [NOW, datetime(2026,10,7,0,tzinfo=timezone.utc)]
                        response = self.client.get(self.verify)
                else: response = self.client.get(self.verify)
            self.assertEqual(response.status_code,409,response.text)
            self.assertEqual(response.json()['detail']['error_code'],code)
            self.flow._admin_state.connectors[self.connector] = deepcopy(original)
            auth_file.write_bytes(saved); self.store.cache_accepted(7,self.flow._store.get_connector(self.connector,7),self.payload)

    def test_dream_auth_admin_capability_and_ownership_remain_fail_closed(self):
        from fastapi import HTTPException
        from routers import notion as router
        from services.admin_data.errors import AdminDataError
        with patch.object(NotionOperationClient,'_run_endpoint',new=AsyncMock()) as remote:
            with patch.object(router.AdminPreferencesData,'get',side_effect=AdminDataError('ADMIN_CAPABILITY_UNAVAILABLE',503)):
                self.assertEqual(self.client.get(self.endpoint).status_code,503)
            def expired(): raise HTTPException(401,detail={'error_code':'INVALID_ACCESS_TOKEN'})
            self.client.app.dependency_overrides[router.get_current_user] = expired
            self.assertEqual(self.client.get(self.endpoint).status_code,401)
            remote.assert_not_awaited()
