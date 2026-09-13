// [Input] Authenticated fetch boundary and managed discovery JSON with the backend's serverInfo wire field.
// [Output] Verify inventory metadata, null Server info, capability counts, revisions, cache flags, and safe errors.
// [Pos] Claude MCP API contract regression; no browser, real backend, MCP Server, or credentials.
// [Sync] 2026-09-13: lock the serverInfo → server_info adaptation without changing the public API or page model.

import { expect, test } from '@playwright/test';
import { ClaudeMcpApiError, getClaudeMcpServerInventory } from '../claudeMcpApi';

const originalFetch = globalThis.fetch;
let previousLocalStorage: PropertyDescriptor | undefined;
let previousWindow: PropertyDescriptor | undefined;

test.describe.configure({ mode: 'serial' });

test.beforeEach(() => {
  previousLocalStorage = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
  previousWindow = Object.getOwnPropertyDescriptor(globalThis, 'window');
  Object.defineProperty(globalThis, 'localStorage', {
    value: { getItem: (key: string) => key === 'auth_token' ? 'mcp-contract-token' : null },
    configurable: true,
  });
  Object.defineProperty(globalThis, 'window', {
    value: { __INK_RUNTIME_CONFIG__: { apiBaseUrl: 'https://dream.test' } },
    configurable: true,
  });
});

test.afterEach(() => {
  globalThis.fetch = originalFetch;
  if (previousLocalStorage) Object.defineProperty(globalThis, 'localStorage', previousLocalStorage);
  else delete (globalThis as { localStorage?: Storage }).localStorage;
  if (previousWindow) Object.defineProperty(globalThis, 'window', previousWindow);
  else delete (globalThis as { window?: Window }).window;
});

function discoveryPayload() {
  return {
    server_id: 'server-1',
    status: 'complete',
    config_revision: 3,
    credential_revision: 2,
    serverInfo: { name: 'Technical MCP', version: '1.0.0' },
    tools: [{ name: 'read_time', description: 'Read time', annotations: { read_only: true, destructive: false, open_world: false } }],
    resources: [{ uri: 'ui://clock', name: 'Clock', description: null, mime_type: 'text/html' }],
    prompts: [{ name: 'inspect_clock', description: null, argument_count: 0 }],
    error: null,
    discovered_at: '2026-09-13T00:00:00Z',
    cached: true,
    truncated: true,
  };
}

function respond(discovery: unknown) {
  globalThis.fetch = async () => new Response(JSON.stringify({ discovery }), {
    headers: { 'content-type': 'application/json' },
  });
}

test('maps backend serverInfo to page server_info and preserves the inventory contract', async () => {
  const discovery = discoveryPayload();
  globalThis.fetch = async (input, init) => {
    expect(input).toBe('https://dream.test/api/claude-mcp/servers/team%2Fclock/discoveries');
    expect(init?.method).toBe('POST');
    expect(JSON.parse(String(init?.body))).toEqual({ force: false });
    expect(init?.credentials).toBe('include');
    expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer mcp-contract-token');
    return new Response(JSON.stringify({ discovery }), { headers: { 'content-type': 'application/json' } });
  };

  expect(await getClaudeMcpServerInventory('team/clock')).toEqual({
    server_name: 'team/clock',
    config_revision: 3,
    credential_revision: 2,
    status: 'connected',
    config_scope: 'managed_db',
    runtime_scope: null,
    transport: null,
    url: null,
    server_info: discovery.serverInfo,
    tools: discovery.tools,
    resources: discovery.resources,
    prompts: discovery.prompts,
    tool_count: 1,
    tools_truncated: true,
    capabilities: {
      tools: { status: 'available', count: 1 },
      resources: { status: 'available', count: 1 },
      prompts: { status: 'available', count: 1 },
    },
    refreshed_at: discovery.discovered_at,
    cached: true,
    error: null,
  });
});

test('preserves explicit null Server info on an otherwise successful discovery', async () => {
  respond({ ...discoveryPayload(), serverInfo: null });
  const inventory = await getClaudeMcpServerInventory('server-1');
  expect(inventory.server_info).toBeNull();
  expect(inventory.status).toBe('connected');
  expect(inventory.tool_count).toBe(1);
  expect(inventory.resources).toHaveLength(1);
  expect(inventory.prompts).toHaveLength(1);
});

for (const code of ['CLAUDE_MCP_CREDENTIAL_REQUIRED', 'CLAUDE_MCP_PROTOCOL_ERROR']) {
  test(`retains ${code} classification with null Server info`, async () => {
    const error = { code, retryable: code !== 'CLAUDE_MCP_CREDENTIAL_REQUIRED' };
    respond({ ...discoveryPayload(), status: 'failed', serverInfo: null, tools: [], resources: [], prompts: [], error });
    const inventory = await getClaudeMcpServerInventory('server-1');
    expect(inventory.server_info).toBeNull();
    expect(inventory.status).toBe(code === 'CLAUDE_MCP_CREDENTIAL_REQUIRED' ? 'needs_auth' : 'failed');
    expect(inventory.error).toEqual(error);
    expect(inventory.tool_count).toBe(0);
  });
}

test('HTTP discovery errors still reject instead of returning a connected inventory', async () => {
  globalThis.fetch = async () => new Response(JSON.stringify({
    error: { code: 'CLAUDE_MCP_SCHEMA_CAPABILITY_UNAVAILABLE', message: 'Unavailable' },
  }), { status: 503, headers: { 'content-type': 'application/json' } });
  await expect(getClaudeMcpServerInventory('server-1')).rejects.toBeInstanceOf(ClaudeMcpApiError);
});
