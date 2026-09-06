// [Input] Standard JSON-RPC requests plus an injected process manager and recording read-only connector.
// [Output] GET/POST/DELETE session, resource allowlist, negative zero-call, scope, and teardown assertions.
// [Pos] Provider-free Runtime HTTP contract; it does not start or imitate an upstream MCP Server.
// [Sync] 2026-09-06: cover server-owned calls, per-request revalidation, and no-request session expiry.

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import type {
  ConnectionViewProvider,
  ConnectorFactory,
  McpAppsConnectionView,
  McpAppsRequestContext,
} from './contracts.ts';
import { McpAppsRuntimeError } from './contracts.ts';
import { McpAppsHttpAdapter } from './http-adapter.ts';
import { PersistentConnectorManager } from './persistent-connector-manager.ts';
import { parsePluginManifest } from './plugin-manifest.ts';

const requestContext: McpAppsRequestContext = Object.freeze({
  authorization: 'Bearer browser-session',
  authorizationFingerprint: 'auth-fingerprint',
  workspaceScope: null,
  serverRef: 'official-basic',
  browserSessionScope: 'browser-a',
});

const connectionView: McpAppsConnectionView = Object.freeze({
  actorScope: 'actor-1',
  workspaceScope: null,
  serverId: 'server-1',
  serverRef: 'official-basic',
  transportKind: 'streamable_http',
  enabled: true,
  configRevision: 4,
  credentialRevision: 2,
  expiresAt: '2099-01-01T00:00:00.000Z',
  allowedTools: ['get-time'],
  allowedResources: ['ui://get-time/mcp-app.html'],
  appCallableLowRiskTools: ['get-time'],
  policy: Object.freeze({
    version: 1,
    revision: 7,
    default: Object.freeze({ resourceReads: false, lowRiskToolCalls: false }),
    desired: Object.freeze({ resourceReads: true, lowRiskToolCalls: true }),
    effective: Object.freeze({ resourceReads: true, lowRiskToolCalls: true }),
  }),
  connectionProfile: Object.freeze({ type: 'streamable_http', url: 'http://127.0.0.1.invalid/mcp', headers: {} }),
});

const pluginScaffoldDocument = JSON.parse(readFileSync(
  new URL('../plugin/manifest.example.json', import.meta.url),
  'utf8',
)) as Record<string, unknown>;
const manifestProvider = Object.freeze({
  current: () => parsePluginManifest({
    ...pluginScaffoldDocument,
    lifecycle: 'enabled',
  }),
});

function rpcRequest(body: unknown, sessionId?: string): Request {
  const headers: Record<string, string> = {
    accept: 'application/json, text/event-stream',
    'content-type': 'application/json',
  };
  if (sessionId) {
    headers['mcp-session-id'] = sessionId;
    headers['mcp-protocol-version'] = '2025-11-25';
  }
  return new Request('http://im.test/api/mcp-apps/official-basic', {
    method: 'POST', headers, body: JSON.stringify(body),
  });
}

async function json(response: Response): Promise<Record<string, unknown>> {
  return response.json() as Promise<Record<string, unknown>>;
}

test('serves one standard read-only session and rejects reverse capabilities with zero upstream calls', async () => {
  let resourceReads = 0;
  let upstreamToolCalls = 0;
  let closes = 0;
  const provider: ConnectionViewProvider = { async getConnectionView() { return connectionView; } };
  const factory: ConnectorFactory = {
    async connect() {
      return {
        catalog: {
          tools: [{ name: 'get-time', inputSchema: { type: 'object' }, _meta: { ui: { resourceUri: 'ui://get-time/mcp-app.html' } } }],
          resources: [{ uri: 'ui://get-time/mcp-app.html', name: 'get-time', mimeType: 'text/html;profile=mcp-app' }],
        },
        async readResource(uri) {
          resourceReads += 1;
          return { contents: [{ uri, mimeType: 'text/html;profile=mcp-app', text: '<main>time</main>' }] };
        },
        async callTool(name) {
          upstreamToolCalls += 1;
          return { content: [{ type: 'text', text: name }] };
        },
        async close() { closes += 1; },
      };
    },
  };
  const manager = new PersistentConnectorManager(provider, factory);
  const adapter = new McpAppsHttpAdapter(manager, manifestProvider);

  const initialized = await adapter.handle(rpcRequest({
    jsonrpc: '2.0', id: 1, method: 'initialize', params: {
      protocolVersion: '2025-11-25', capabilities: {}, clientInfo: { name: 'test-client', version: '1.0.0' },
    },
  }), requestContext);
  assert.equal(initialized.status, 200);
  const sessionId = initialized.headers.get('mcp-session-id');
  assert.ok(sessionId);

  const listed = await json(await adapter.handle(rpcRequest({ jsonrpc: '2.0', id: 2, method: 'tools/list', params: {} }, sessionId), requestContext));
  assert.equal(((listed.result as { tools: unknown[] }).tools).length, 1);

  const resource = await json(await adapter.handle(rpcRequest({
    jsonrpc: '2.0', id: 3, method: 'resources/read', params: { uri: 'ui://get-time/mcp-app.html' },
  }, sessionId), requestContext));
  assert.equal(((resource.result as { contents: unknown[] }).contents).length, 1);
  assert.equal(resourceReads, 1);

  const wrongResource = await json(await adapter.handle(rpcRequest({
    jsonrpc: '2.0', id: 31, method: 'resources/read', params: { uri: 'ui://foreign/private.html' },
  }, sessionId), requestContext));
  assert.ok(wrongResource.error);
  assert.equal(resourceReads, 1);

  const called = await json(await adapter.handle(rpcRequest({
    jsonrpc: '2.0', id: 4, method: 'tools/call', params: { name: 'get-time', arguments: {} },
  }, sessionId), requestContext));
  assert.equal(((called.result as { content: Array<{ text: string }> }).content[0]?.text), 'get-time');
  assert.equal(upstreamToolCalls, 1);

  for (const [index, name] of ['write_not_allowed', 'unclassified', 'confirmation_required'].entries()) {
    const denied = await json(await adapter.handle(rpcRequest({
      jsonrpc: '2.0', id: 41 + index, method: 'tools/call', params: { name, arguments: {} },
    }, sessionId), requestContext));
    assert.equal((denied.result as { isError: boolean }).isError, true);
    assert.equal(upstreamToolCalls, 1);
  }

  const unknown = await json(await adapter.handle(rpcRequest({
    jsonrpc: '2.0', id: 5, method: 'ui/message', params: { role: 'user', content: [] },
  }, sessionId), requestContext));
  assert.ok(unknown.error);
  assert.equal(upstreamToolCalls, 1);

  const getResponse = await adapter.handle(new Request('http://im.test/api/mcp-apps/official-basic', {
    method: 'GET',
    headers: { accept: 'text/event-stream', 'mcp-session-id': sessionId, 'mcp-protocol-version': '2025-11-25' },
  }), requestContext);
  assert.equal(getResponse.status, 200);
  await getResponse.body?.cancel();

  const deleted = await adapter.handle(new Request('http://im.test/api/mcp-apps/official-basic', {
    method: 'DELETE',
    headers: { 'mcp-session-id': sessionId, 'mcp-protocol-version': '2025-11-25' },
  }), requestContext);
  assert.equal(deleted.status, 200);
  assert.equal(closes, 1);
  assert.deepEqual(adapter.diagnostics(), { sessions: 0 });
  assert.deepEqual(manager.diagnostics(), { connections: 0, leases: 0 });
});

test('rejects a forged session scope and tears down the invalidated session', async () => {
  const provider: ConnectionViewProvider = { async getConnectionView() { return connectionView; } };
  const factory: ConnectorFactory = {
    async connect() {
      return {
        catalog: { tools: [], resources: [] },
        async readResource() { return { contents: [] }; },
        async callTool() { return { content: [] }; },
        async close() {},
      };
    },
  };
  const adapter = new McpAppsHttpAdapter(
    new PersistentConnectorManager(provider, factory),
    manifestProvider,
  );
  const initialized = await adapter.handle(rpcRequest({
    jsonrpc: '2.0', id: 1, method: 'initialize', params: {
      protocolVersion: '2025-11-25', capabilities: {}, clientInfo: { name: 'test-client', version: '1.0.0' },
    },
  }), requestContext);
  const sessionId = initialized.headers.get('mcp-session-id');
  assert.ok(sessionId);

  const forged = await adapter.handle(rpcRequest({ jsonrpc: '2.0', id: 2, method: 'tools/list', params: {} }, sessionId), {
    ...requestContext,
    authorizationFingerprint: 'foreign-auth',
  });
  assert.equal(forged.status, 403);
  assert.deepEqual(adapter.diagnostics(), { sessions: 0 });
  await adapter.closeAll();
});

test('failed initialization cannot invalidate another actor or workspace connection', async () => {
  let closes = 0;
  const provider: ConnectionViewProvider = {
    async getConnectionView(input) {
      if (input.authorization !== requestContext.authorization) {
        throw new McpAppsRuntimeError(403, 'CONFIG_PROVIDER_REJECTED', 'unavailable');
      }
      return connectionView;
    },
  };
  const factory: ConnectorFactory = {
    async connect() {
      return {
        catalog: { tools: [], resources: [] },
        async readResource() { return { contents: [] }; },
        async callTool() { return { content: [] }; },
        async close() { closes += 1; },
      };
    },
  };
  const adapter = new McpAppsHttpAdapter(
    new PersistentConnectorManager(provider, factory),
    manifestProvider,
  );
  const initialize = {
    jsonrpc: '2.0', id: 1, method: 'initialize', params: {
      protocolVersion: '2025-11-25', capabilities: {}, clientInfo: { name: 'test-client', version: '1.0.0' },
    },
  };
  const legitimate = await adapter.handle(rpcRequest(initialize), requestContext);
  const sessionId = legitimate.headers.get('mcp-session-id');
  assert.ok(sessionId);

  const attacker = await adapter.handle(rpcRequest(initialize), {
    ...requestContext,
    authorization: 'Bearer attacker',
    authorizationFingerprint: 'attacker-fingerprint',
    workspaceScope: 'foreign-workspace',
  });
  assert.equal(attacker.status, 403);
  assert.equal(closes, 0);

  const stillCurrent = await adapter.handle(rpcRequest({
    jsonrpc: '2.0', id: 2, method: 'tools/list', params: {},
  }, sessionId), requestContext);
  assert.equal(stillCurrent.status, 200);
  await adapter.closeAll();
  assert.equal(closes, 1);
});

test('an abandoned adapter session closes when its short-lived view expires', async () => {
  let closes = 0;
  const provider: ConnectionViewProvider = {
    async getConnectionView() {
      return Object.freeze({
        ...connectionView,
        expiresAt: new Date(Date.now() + 30).toISOString(),
      });
    },
  };
  const factory: ConnectorFactory = {
    async connect() {
      return {
        catalog: { tools: [], resources: [] },
        async readResource() { return { contents: [] }; },
        async callTool() { return { content: [] }; },
        async close() { closes += 1; },
      };
    },
  };
  const manager = new PersistentConnectorManager(provider, factory);
  const adapter = new McpAppsHttpAdapter(manager, manifestProvider);
  const initialized = await adapter.handle(rpcRequest({
    jsonrpc: '2.0', id: 1, method: 'initialize', params: {
      protocolVersion: '2025-11-25', capabilities: {}, clientInfo: { name: 'test-client', version: '1.0.0' },
    },
  }), requestContext);
  assert.equal(initialized.status, 200);
  assert.deepEqual(adapter.diagnostics(), { sessions: 1 });

  await new Promise((resolve) => setTimeout(resolve, 60));

  assert.deepEqual(adapter.diagnostics(), { sessions: 0 });
  assert.deepEqual(manager.diagnostics(), { connections: 0, leases: 0 });
  assert.equal(closes, 1);
});
