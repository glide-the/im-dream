// [Input] Injected fetch/localStorage boundaries and server-owned Notion connector responses.
// [Output] Verify fail-closed transport, truthful snapshot status, selection sync, and policy DTO projection.
// [Pos] Notion resource connector browser API contract test in frontend/src/api/__tests__
// [Sync] 2026-08-28: prevent backend failures from becoming browser-local authenticated/synced state.
// [Sync] 2026-08-28: keep pending index resources and active policy refreshes visibly syncing.

import { expect, test } from '@playwright/test';
import {
  ResourceConnectorApiError,
  listConnectors,
  normalizeResourceConnectorFallback,
  selectConnectorResources,
  updateConnectorSyncPolicy,
} from '../resourceConnectorApi';

const originalFetch = globalThis.fetch;
const storageValues = new Map<string, string>();
let storageWrites = 0;

const storage: Storage = {
  get length() { return storageValues.size; },
  clear() { storageValues.clear(); },
  getItem(key) { return storageValues.get(key) ?? null; },
  key(index) { return [...storageValues.keys()][index] ?? null; },
  removeItem(key) { storageValues.delete(key); },
  setItem(key, value) { storageWrites += 1; storageValues.set(key, value); },
};

function connectorPayload(overrides: Record<string, unknown> = {}) {
  return {
    id: 'connector-1',
    name: 'Notion Resource Connector',
    platform: 'notion',
    auth_status: 'authenticated',
    created_at: '2026-08-28T12:00:00Z',
    updated_at: '2026-08-28T12:00:00Z',
    last_synced_at: null,
    resources: [{
      external_id: 'database-1',
      resource_type: 'notion_database',
      title: 'Database',
      updated_at: '2026-08-28T12:00:00Z',
    }],
    sync_policy: {
      schema_version: 1,
      default: { enabled: true, interval_minutes: 15, revision: 1 },
      desired: { enabled: true, interval_minutes: 15, revision: 1 },
      effective: { enabled: true, interval_minutes: 15, revision: 1 },
      status: 'applied',
      last_attempt_at: null,
      last_success_at: null,
      next_sync_at: '2026-08-28T12:15:00Z',
      last_error_code: null,
      allowed_interval_minutes: [15, 60, 360, 1440],
    },
    ...overrides,
  };
}

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}

test.describe.configure({ mode: 'serial' });

test.beforeEach(() => {
  storageValues.clear();
  storageWrites = 0;
  Object.defineProperty(globalThis, 'localStorage', {
    value: storage,
    configurable: true,
  });
  Object.defineProperty(globalThis, 'window', {
    value: { __INK_RUNTIME_CONFIG__: { apiBaseUrl: 'https://dream.test' } },
    configurable: true,
  });
});

test.afterEach(() => {
  globalThis.fetch = originalFetch;
});

test('authenticated selection without a snapshot is not normalized as synced', () => {
  const connector = normalizeResourceConnectorFallback(connectorPayload());
  expect(connector.status).toBe('authenticated');
  expect(connector.lastSyncedAt).toBeUndefined();
  expect(connector.syncPolicy?.effective.intervalMinutes).toBe(15);
});

test('pending resource remains syncing even when an older index exists', () => {
  const connector = normalizeResourceConnectorFallback(connectorPayload({
    last_synced_at: '2026-08-28T12:05:00Z',
    resources: [{
      external_id: 'database-2',
      resource_type: 'notion_database',
      title: 'New Database',
      sync_status: 'pending',
      updated_at: '2026-08-28T12:06:00Z',
    }],
  }));
  expect(connector.status).toBe('syncing');
  expect(connector.sources[0]?.status).toBe('syncing');
});

test('active sync policy takes precedence over an older successful index', () => {
  const connector = normalizeResourceConnectorFallback(connectorPayload({
    last_synced_at: '2026-08-28T12:05:00Z',
    sync_policy: {
      schema_version: 1,
      default: { enabled: true, interval_minutes: 15, revision: 1 },
      desired: { enabled: true, interval_minutes: 15, revision: 1 },
      effective: { enabled: true, interval_minutes: 15, revision: 1 },
      status: 'syncing',
      allowed_interval_minutes: [15, 60, 360, 1440],
    },
  }));
  expect(connector.status).toBe('syncing');
});

test('backend failure remains actionable and never writes connector state to localStorage', async () => {
  globalThis.fetch = (async () => jsonResponse({
    detail: 'Notion could not complete the request. Retry later.',
  }, 502)) as typeof fetch;

  await expect(listConnectors()).rejects.toEqual(expect.objectContaining({
    name: 'ResourceConnectorApiError',
    status: 502,
    message: 'Notion could not complete the request. Retry later.',
  } satisfies Partial<ResourceConnectorApiError>));
  expect(storageWrites).toBe(0);
});

test('resource selection returns only server-confirmed snapshot status', async () => {
  const calls: Array<{ url: string; body: unknown }> = [];
  globalThis.fetch = (async (input, init) => {
    calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
    return jsonResponse({
      connector: connectorPayload({
        last_synced_at: '2026-08-28T12:05:00Z',
      }),
      synced: true,
    });
  }) as typeof fetch;

  const connector = await selectConnectorResources('connector-1', {
    databaseIds: ['database-1'],
    pageIds: [],
    databaseOptions: [{ id: 'database-1', title: 'Database' }],
  });
  expect(calls[0]?.url).toContain('/api/connectors/connector-1/resources/select');
  expect(calls[0]?.body).toEqual({
    selected_databases: [{
      database_id: 'database-1',
      title: 'Database',
    }],
    selected_pages: [],
  });
  expect(connector?.status).toBe('synced');
  expect(connector?.lastSyncedAt).toBe('2026-08-28T12:05:00Z');
  expect(storageWrites).toBe(0);
});

test('policy updates preserve backend desired/effective revision', async () => {
  globalThis.fetch = (async (_input, init) => {
    expect(JSON.parse(String(init?.body))).toEqual({
      enabled: false,
      interval_minutes: 60,
    });
    return jsonResponse({
      connector: connectorPayload({
        sync_policy: {
          schema_version: 1,
          default: { enabled: true, interval_minutes: 15, revision: 1 },
          desired: { enabled: false, interval_minutes: 60, revision: 2 },
          effective: { enabled: false, interval_minutes: 60, revision: 2 },
          status: 'disabled',
          allowed_interval_minutes: [15, 60, 360, 1440],
        },
      }),
    });
  }) as typeof fetch;

  const connector = await updateConnectorSyncPolicy('connector-1', {
    enabled: false,
    intervalMinutes: 60,
  });
  expect(connector.syncPolicy?.desired).toEqual(connector.syncPolicy?.effective);
  expect(connector.syncPolicy?.status).toBe('disabled');
});
