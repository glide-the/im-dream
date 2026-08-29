// [Input] Injected fetch/localStorage boundaries and server-owned Notion connector responses.
// [Output] Verify fail-closed transport, truthful snapshot status, selection sync, policy DTOs, and read-only capability/Skill/file projections.
// [Pos] Notion resource connector browser API contract test in frontend/src/api/__tests__
// [Sync] 2026-08-28: prevent backend failures from becoming browser-local authenticated/synced state.
// [Sync] 2026-08-28: keep pending index resources and active policy refreshes visibly syncing.
// [Sync] 2026-08-29: cover recoverable failed-reauth warnings and compact selection payloads without raw upstream data.
// [Sync] 2026-08-29: validate server-owned Notion Skill plus real Hook/workspace operation, stable file ID, and revision transport contracts.
// [Sync] 2026-08-30: require the ntn installation contract and connected notion-cli availability.

import { expect, test } from '@playwright/test';
import {
  ResourceConnectorApiError,
  getNotionCapabilityCatalog,
  getNotionSkillDetail,
  getNotionSkillFile,
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

test('failed reauthorization warning does not mask the effective credential', () => {
  const connector = normalizeResourceConnectorFallback(connectorPayload({
    config: {
      auth_error: 'The new authorization attempt expired.',
      auth_session: { auth_session_status: 'expired' },
    },
  }));

  expect(connector.auth.status).toBe('authenticated');
  expect(connector.auth.warning).toBe('The new authorization attempt expired.');
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
    databaseOptions: [{
      id: 'database-1',
      title: 'Database',
      propertiesSchema: { Name: { type: 'title' } },
    }],
  });
  expect(calls[0]?.url).toContain('/api/connectors/connector-1/resources/select');
  expect(calls[0]?.body).toEqual({
    selected_databases: [{
      database_id: 'database-1',
      title: 'Database',
      properties_schema: { Name: { type: 'title' } },
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

test('capability catalog preserves real Hook and workspace entrypoints', async () => {
  globalThis.fetch = (async () => jsonResponse({
    catalog: {
      schema_version: 4,
      package_revision: 'revision-1',
      cli_installation: {
        status: 'installed',
        required_version: '0.15.1',
        install_command: 'npm install -g ntn@0.15.1',
      },
      mcp_inventory: {
        status: 'not_integrated',
        revision: null,
        read_status: 'not_integrated',
        write_status: 'not_integrated',
      },
      skills: [
        {
          id: 'notion-session',
          title: 'Notion 工作空间助手',
          description: '只读访问已挂载内容',
          source: 'builtin',
          availability: 'available',
        },
        {
          id: 'notion-cli',
          title: 'Notion CLI 工作空间数据助手',
          description: '通过 ntn CLI 访问 Notion',
          source: 'builtin',
          availability: 'available',
        },
      ],
      operations: [
        {
          id: 'notion-page-read-hook',
          title: '按需读取页面正文',
          description: '按需读取一个页面',
          kind: 'read',
          source: 'runtime_hook',
          entrypoint: 'apply_notion_page_read_redirect',
          availability: 'available',
        },
        {
          id: 'notion-workspace-snapshot-materialize',
          title: '挂载工作区轻量索引',
          description: '挂载轻量索引',
          kind: 'write',
          source: 'workspace_materializer',
          entrypoint: 'materialize_workspace_snapshot',
          availability: 'available',
        },
      ],
    },
  })) as typeof fetch;

  const catalog = await getNotionCapabilityCatalog();
  expect(catalog.packageRevision).toBe('revision-1');
  expect(catalog.cliInstallation).toEqual({
    status: 'installed',
    requiredVersion: '0.15.1',
    installCommand: 'npm install -g ntn@0.15.1',
  });
  expect(catalog.mcpInventory.writeStatus).toBe('not_integrated');
  expect(catalog.skills.map((skill) => skill.id)).toEqual(['notion-session', 'notion-cli']);
  expect(catalog.skills[1]?.availability).toBe('available');
  expect(catalog.operations).toEqual(expect.arrayContaining([
    expect.objectContaining({ kind: 'read', source: 'runtime_hook', entrypoint: 'apply_notion_page_read_redirect' }),
    expect.objectContaining({ kind: 'write', source: 'workspace_materializer', entrypoint: 'materialize_workspace_snapshot' }),
  ]));
});

test('capability catalog rejects synthetic Skill operation sources', async () => {
  globalThis.fetch = (async () => jsonResponse({
    catalog: {
      schema_version: 4,
      package_revision: 'revision-1',
      cli_installation: {
        status: 'installed',
        required_version: '0.15.1',
        install_command: 'npm install -g ntn@0.15.1',
      },
      mcp_inventory: {
        status: 'not_integrated',
        revision: null,
        read_status: 'not_integrated',
        write_status: 'not_integrated',
      },
      skills: [{
        id: 'notion-session',
        title: 'Notion 工作空间助手',
        description: '只读访问已挂载内容',
        source: 'builtin',
        availability: 'available',
      }],
      operations: [{
        id: 'synthetic-read',
        title: 'Synthetic read',
        description: 'Not a real backend stage',
        kind: 'read',
        source: 'builtin_skill',
        entrypoint: 'invented_operation',
        availability: 'available',
      }],
    },
  })) as typeof fetch;

  await expect(getNotionCapabilityCatalog()).rejects.toMatchObject({ status: 502 });
});

test('Skill detail and stable file reads keep package revision in the request', async () => {
  const urls: string[] = [];
  globalThis.fetch = (async (input) => {
    const url = String(input);
    urls.push(url);
    if (url.includes('/files/')) {
      return jsonResponse({
        package_revision: 'revision-1',
        file: {
          id: 'notion-search',
          relative_path: 'references/notion-search.md',
          media_type: 'text/markdown',
          size_bytes: 128,
          content: '# Search',
        },
      });
    }
    return jsonResponse({
      package_revision: 'revision-1',
      skill: {
        id: 'notion-session',
        title: 'Notion 工作空间助手',
        description: '只读访问已挂载内容',
        source: 'builtin',
        availability: 'available',
        tools: ['Read'],
        body: '# Notion 工作空间助手',
      },
      files: [{
        id: 'notion-search',
        relative_path: 'references/notion-search.md',
        media_type: 'text/markdown',
        size_bytes: 128,
      }],
    });
  }) as typeof fetch;

  const detail = await getNotionSkillDetail('notion-session');
  const file = await getNotionSkillFile('notion-session', detail.files[0]!.id, detail.packageRevision);
  expect(file.file.content).toBe('# Search');
  expect(urls[1]).toContain('/files/notion-search?package_revision=revision-1');
});

test('renamed notion-cli detail preserves its Bash tool boundary', async () => {
  globalThis.fetch = (async () => jsonResponse({
    package_revision: 'cli-revision-1',
    skill: {
      id: 'notion-cli',
      title: 'Notion CLI 工作空间数据助手',
      description: '通过 ntn CLI 访问 Notion',
      source: 'builtin',
      availability: 'available',
      tools: ['Bash'],
      body: '# Notion CLI 工作空间数据助手\n\n`ntn api v1/search`',
    },
    files: [{
      id: 'notion-search',
      relative_path: 'references/notion-search.md',
      media_type: 'text/markdown',
      size_bytes: 1024,
    }],
  })) as typeof fetch;

  const detail = await getNotionSkillDetail('notion-cli');
  expect(detail.skill.tools).toEqual(['Bash']);
  expect(detail.skill.availability).toBe('available');
  expect(detail.skill.body).toContain('ntn api v1/search');
});

test('Skill file DTO rejects traversal-like relative paths', async () => {
  globalThis.fetch = (async () => jsonResponse({
    package_revision: 'revision-1',
    file: {
      id: 'notion-search',
      relative_path: '../private.md',
      media_type: 'text/markdown',
      size_bytes: 128,
      content: '# no',
    },
  })) as typeof fetch;

  await expect(getNotionSkillFile('notion-session', 'notion-search', 'revision-1')).rejects.toMatchObject({
    status: 502,
  });
});
