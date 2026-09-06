// [Input] Mutable/scaffold plugin manifests, isolated scopes, configured limits, and sensitive fixtures.
// [Output] Scaffold identity, lifecycle teardown, compatibility, limits, and diagnostic redaction evidence.
// [Pos] Provider-free Phase 3 Node governance tests; no Browser, database, credential, or MCP provider.
// [Sync] 2026-09-06: cover disabled lifecycle, bounded pagination, no-redirect networking, and safety policy.
// [Sync] 2026-09-06: carry the connection App-settings revision in governance fixtures.

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createServer } from 'node:http';
import test from 'node:test';
import type { Tool } from '@modelcontextprotocol/sdk/types.js';

import type {
  ConnectionViewProvider,
  ConnectorFactory,
  McpAppsConnectionView,
  McpAppsRequestContext,
} from './contracts.ts';
import { MCP_APPS_PROTOCOL_VERSION } from './contracts.ts';
import { connectionKey } from './contracts.ts';
import { McpAppsDiagnosticRecorder } from './diagnostics.ts';
import { McpAppsHttpAdapter } from './http-adapter.ts';
import { PersistentConnectorManager } from './persistent-connector-manager.ts';
import { listAllowedCatalog, SdkConnectorFactory } from './sdk-connector.ts';
import {
  MCP_APPS_NODE_ENTRY,
  MCP_APPS_EXT_APPS_VERSION,
  MCP_APPS_MCP_UI_VERSION,
  MCP_APPS_SDK_VERSION,
  parsePluginManifest,
  type McpAppsPluginManifest,
  type PluginManifestProvider,
} from './plugin-manifest.ts';
import {
  networkHostAllowed,
  parseNetworkHostAllowlist,
  requireAllowedConnection,
  requireResourceWithinLimit,
  runtimeLimitsFromEnvironment,
} from './runtime-policy.ts';

const pluginScaffoldDocument = JSON.parse(readFileSync(
  new URL('../plugin/manifest.example.json', import.meta.url),
  'utf8',
)) as Record<string, unknown>;

function compatibleTestPluginManifest(revision = 1): McpAppsPluginManifest {
  return parsePluginManifest({
    ...pluginScaffoldDocument,
    revision,
    lifecycle: 'enabled',
  });
}

const connectionView: McpAppsConnectionView = Object.freeze({
  actorScope: 'actor-sensitive',
  workspaceScope: 'workspace-sensitive',
  serverId: 'server-1',
  serverRef: 'official-basic',
  transportKind: 'streamable_http',
  enabled: true,
  configRevision: 4,
  credentialRevision: 2,
  appSettingsRevision: 3,
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
  connectionProfile: Object.freeze({
    type: 'streamable_http',
    url: 'https://secret-upstream.invalid/mcp?credential=private',
    headers: { authorization: 'Bearer private' },
  }),
});

const context: McpAppsRequestContext = Object.freeze({
  authorization: 'Bearer browser-private',
  authorizationFingerprint: 'authorization-fingerprint',
  workspaceScope: 'workspace-sensitive',
  serverRef: 'official-basic',
  browserSessionScope: 'browser-a',
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
  return new Request('https://ink.invalid/api/mcp-apps/official-basic', {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });
}

async function initialize(adapter: McpAppsHttpAdapter): Promise<string> {
  const response = await adapter.handle(rpcRequest({
    jsonrpc: '2.0', id: 1, method: 'initialize', params: {
      protocolVersion: '2025-11-25', capabilities: {}, clientInfo: { name: 'test', version: '1' },
    },
  }), context);
  assert.equal(response.status, 200);
  const sessionId = response.headers.get('mcp-session-id');
  assert.ok(sessionId);
  return sessionId;
}

class MutableManifestProvider implements PluginManifestProvider {
  manifest = compatibleTestPluginManifest();
  failure: Error | null = null;
  current(): McpAppsPluginManifest {
    if (this.failure) throw this.failure;
    return this.manifest;
  }
}

function harness() {
  let closes = 0;
  let toolCalls = 0;
  const provider: ConnectionViewProvider = {
    async getConnectionView() { return connectionView; },
  };
  const factory: ConnectorFactory = {
    async connect() {
      return {
        catalog: {
          tools: [{ name: 'get-time', inputSchema: { type: 'object' } }],
          resources: [{ uri: 'ui://get-time/mcp-app.html', name: 'app' }],
        },
        async readResource(uri) { return { contents: [{ uri, text: '<main>secret html</main>' }] }; },
        async callTool() {
          toolCalls += 1;
          return { content: [{ type: 'text', text: 'private result' }] };
        },
        async close() { closes += 1; },
      };
    },
  };
  const manifestProvider = new MutableManifestProvider();
  const manager = new PersistentConnectorManager(provider, factory);
  const adapter = new McpAppsHttpAdapter(manager, manifestProvider);
  return {
    adapter,
    manager,
    manifestProvider,
    closes: () => closes,
    toolCalls: () => toolCalls,
  };
}

test('plugin upgrade and disable invalidate existing sessions and close unreferenced connectors', async () => {
  const subject = harness();
  const firstSession = await initialize(subject.adapter);
  subject.manifestProvider.manifest = compatibleTestPluginManifest(2);

  const upgraded = await subject.adapter.handle(
    rpcRequest({ jsonrpc: '2.0', id: 2, method: 'tools/list', params: {} }, firstSession),
    context,
  );
  assert.equal(upgraded.status, 409);
  assert.equal(subject.closes(), 1);
  assert.deepEqual(subject.adapter.diagnostics(), { sessions: 0 });

  const secondSession = await initialize(subject.adapter);
  subject.manifestProvider.manifest = parsePluginManifest({
    ...compatibleTestPluginManifest(3),
    lifecycle: 'disabled',
  });
  const disabled = await subject.adapter.handle(
    rpcRequest({ jsonrpc: '2.0', id: 3, method: 'tools/list', params: {} }, secondSession),
    context,
  );
  assert.equal(disabled.status, 503);
  assert.equal(subject.closes(), 2);
  assert.deepEqual(subject.manager.diagnostics(), { connections: 0, leases: 0 });
});

test('manifest declares entries/ranges/features and incompatible SDK fails closed', () => {
  const manifest = compatibleTestPluginManifest();
  assert.equal(manifest.nodeEntry, MCP_APPS_NODE_ENTRY);
  assert.equal(manifest.protocol.minimum, MCP_APPS_PROTOCOL_VERSION);
  assert.equal(manifest.sdk.mcp.minimum, MCP_APPS_SDK_VERSION);
  assert.equal(manifest.sdk.extApps.minimum, MCP_APPS_EXT_APPS_VERSION);
  assert.equal(manifest.sdk.mcpUi.minimum, MCP_APPS_MCP_UI_VERSION);
  assert.deepEqual(manifest.features, {
    resourceReads: true,
    lowRiskToolCalls: true,
    uiMessage: true,
    windowIm: true,
  });

  assert.throws(() => parsePluginManifest({
    ...manifest,
    sdk: {
      ...manifest.sdk,
      mcp: { minimum: '99.0.0', maximum: '99.0.0' },
    },
  }), /incompatible/i);
  assert.throws(() => parsePluginManifest({
    ...manifest,
    features: {
      resourceReads: true,
      lowRiskToolCalls: false,
      uiMessage: false,
      windowIm: true,
    },
  }), /features are invalid/i);
});

test('secret-free plugin scaffold matches the deployed Browser and Node identities', () => {
  const scaffold = parsePluginManifest(pluginScaffoldDocument);
  assert.equal(scaffold.lifecycle, 'disabled');
  assert.equal(scaffold.pluginId, 'im.mcp-apps-host');
  assert.equal(scaffold.pluginVersion, '1.0.0');
  assert.equal(
    scaffold.browserEntry,
    'frontend/app/_dream/components/chat/mcp-apps/McpAppHostPanel.tsx',
  );
  assert.equal(scaffold.nodeEntry, MCP_APPS_NODE_ENTRY);
  assert.equal(scaffold.sdk.mcp.minimum, MCP_APPS_SDK_VERSION);
  assert.equal(scaffold.sdk.extApps.minimum, MCP_APPS_EXT_APPS_VERSION);
  assert.equal(scaffold.sdk.mcpUi.minimum, MCP_APPS_MCP_UI_VERSION);
  assert.deepEqual(scaffold.features, {
    resourceReads: true,
    lowRiskToolCalls: true,
    uiMessage: true,
    windowIm: true,
  });
});

test('an incompatible manifest observation invalidates an existing session', async () => {
  const subject = harness();
  const sessionId = await initialize(subject.adapter);
  try {
    parsePluginManifest({
      ...compatibleTestPluginManifest(2),
      sdk: {
        ...compatibleTestPluginManifest(2).sdk,
        mcp: { minimum: '99.0.0', maximum: '99.0.0' },
      },
    });
    assert.fail('incompatible manifest must fail');
  } catch (error) {
    assert.ok(error instanceof Error);
    subject.manifestProvider.failure = error;
  }

  const response = await subject.adapter.handle(
    rpcRequest({ jsonrpc: '2.0', id: 2, method: 'tools/list', params: {} }, sessionId),
    context,
  );
  assert.equal(response.status, 503);
  assert.equal(subject.closes(), 1);
  assert.deepEqual(subject.adapter.diagnostics(), { sessions: 0 });
});

test('Phase 1 manifest feature keeps tools/call denied with zero upstream calls', async () => {
  const subject = harness();
  subject.manifestProvider.manifest = parsePluginManifest({
    ...compatibleTestPluginManifest(),
    features: {
      ...compatibleTestPluginManifest().features,
      lowRiskToolCalls: false,
    },
  });
  const sessionId = await initialize(subject.adapter);
  const response = await subject.adapter.handle(
    rpcRequest({
      jsonrpc: '2.0', id: 2, method: 'tools/call', params: { name: 'get-time', arguments: {} },
    }, sessionId),
    context,
  );
  const body = await response.json() as { result: { isError: boolean } };
  assert.equal(body.result.isError, true);
  assert.equal(subject.toolCalls(), 0);
  await subject.adapter.closeAll();
});

test('Browser scope is part of the connector key and prevents cross-Browser reuse', async () => {
  let connects = 0;
  const manager = new PersistentConnectorManager(
    { async getConnectionView() { return connectionView; } },
    {
      async connect() {
        connects += 1;
        return {
          catalog: { tools: [], resources: [] },
          async readResource() { return { contents: [] }; },
          async callTool() { return { content: [] }; },
          async close() {},
        };
      },
    },
  );
  const browserA = await manager.acquire(context, 1);
  const browserB = await manager.acquire({ ...context, browserSessionScope: 'browser-b' }, 1);
  assert.notEqual(browserA.key, browserB.key);
  assert.equal(connects, 2);
  await Promise.all([manager.release(browserA), manager.release(browserB)]);
});

test('actor, workspace, Server, Browser, and plugin revision are independent key dimensions', () => {
  const baseline = connectionKey(connectionView, 'browser-a', 1);
  const variants = [
    connectionKey({ ...connectionView, actorScope: 'actor-b' }, 'browser-a', 1),
    connectionKey({ ...connectionView, workspaceScope: 'workspace-b' }, 'browser-a', 1),
    connectionKey({ ...connectionView, serverId: 'server-b' }, 'browser-a', 1),
    connectionKey({ ...connectionView, serverRef: 'server-b' }, 'browser-a', 1),
    connectionKey(connectionView, 'browser-b', 1),
    connectionKey(connectionView, 'browser-a', 2),
  ];
  assert.equal(new Set([baseline, ...variants]).size, variants.length + 1);
});

test('resource bytes and network hosts use configured positive-list policy', () => {
  const hosts = parseNetworkHostAllowlist('mcp.example.test,*.apps.example.test,127.0.0.1');
  assert.equal(networkHostAllowed('mcp.example.test', hosts), true);
  assert.equal(networkHostAllowed('tenant.apps.example.test', hosts), true);
  assert.equal(networkHostAllowed('apps.example.test', hosts), false);
  assert.equal(networkHostAllowed('evil.example.test', hosts), false);
  assert.throws(() => parseNetworkHostAllowlist('*'), /invalid/i);
  assert.equal(requireAllowedConnection({
    ...connectionView,
    connectionProfile: { type: 'streamable_http', url: 'https://mcp.example.test/mcp', headers: {} },
  }, hosts).hostname, 'mcp.example.test');
  assert.throws(() => requireAllowedConnection(connectionView, hosts), /unavailable/i);

  const result = { contents: [{ uri: 'ui://app', text: '12345' }] };
  assert.equal(requireResourceWithinLimit(result, 5), result);
  assert.throws(() => requireResourceWithinLimit(result, 4), /exceeds policy/i);
});

test('resource, timeout, concurrency, and hosts are resolved from server configuration', () => {
  const names = [
    'INK_MCP_APPS_MAX_RESOURCE_BYTES',
    'INK_MCP_APPS_MAX_CATALOG_PAGES',
    'INK_MCP_APPS_UPSTREAM_TIMEOUT_MS',
    'INK_MCP_APPS_MAX_CONCURRENCY_PER_SCOPE',
    'INK_MCP_APPS_NETWORK_HOST_ALLOWLIST',
  ] as const;
  const previous = Object.fromEntries(names.map((name) => [name, process.env[name]]));
  try {
    process.env.INK_MCP_APPS_MAX_RESOURCE_BYTES = '4096';
    process.env.INK_MCP_APPS_MAX_CATALOG_PAGES = '8';
    process.env.INK_MCP_APPS_UPSTREAM_TIMEOUT_MS = '250';
    process.env.INK_MCP_APPS_MAX_CONCURRENCY_PER_SCOPE = '3';
    process.env.INK_MCP_APPS_NETWORK_HOST_ALLOWLIST = 'mcp.example.test';
    assert.deepEqual(runtimeLimitsFromEnvironment(), {
      maximumResourceBytes: 4096,
      maximumCatalogPages: 8,
      upstreamTimeoutMs: 250,
      maximumConcurrencyPerScope: 3,
      networkHostAllowlist: ['mcp.example.test'],
    });
    process.env.INK_MCP_APPS_MAX_RESOURCE_BYTES = '0';
    assert.throws(() => runtimeLimitsFromEnvironment(), /invalid/i);
  } finally {
    for (const name of names) {
      const value = previous[name];
      if (value === undefined) delete process.env[name];
      else process.env[name] = value;
    }
  }
});

test('allowlisted catalogs traverse bounded pages and reject cursor cycles or overflow', async () => {
  const pages = new Map<string, { values: Tool[]; nextCursor?: string }>([
    ['', { values: [{ name: 'ignored', inputSchema: { type: 'object' } }], nextCursor: 'page-2' }],
    ['page-2', { values: [{ name: 'get-time', inputSchema: { type: 'object' } }] }],
  ]);
  const catalog = await listAllowedCatalog({
    maximumPages: 2,
    allowed: new Set(['get-time']),
    listPage: async (cursor) => pages.get(cursor ?? '')!,
    identity: (tool) => tool.name,
  });
  assert.deepEqual(catalog.map((tool) => tool.name), ['get-time']);

  await assert.rejects(listAllowedCatalog({
    maximumPages: 3,
    allowed: new Set(['missing']),
    listPage: async () => ({ values: [], nextCursor: 'same' }),
    identity: (tool: Tool) => tool.name,
  }), /catalog is invalid/i);

  let page = 0;
  await assert.rejects(listAllowedCatalog({
    maximumPages: 2,
    allowed: new Set(['missing']),
    listPage: async () => ({ values: [], nextCursor: `page-${page += 1}` }),
    identity: (tool: Tool) => tool.name,
  }), /exceeds policy/i);
});

test('configured upstream timeout bounds a stalled MCP connection', async () => {
  const server = createServer(() => undefined);
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  try {
    const address = server.address();
    assert.ok(address && typeof address === 'object');
    const factory = new SdkConnectorFactory({
      maximumResourceBytes: 1024,
      maximumCatalogPages: 4,
      upstreamTimeoutMs: 25,
      maximumConcurrencyPerScope: 1,
      networkHostAllowlist: ['127.0.0.1'],
    });
    const started = Date.now();
    await assert.rejects(
      factory.connect({
        ...connectionView,
        connectionProfile: {
          type: 'streamable_http',
          url: `http://127.0.0.1:${address.port}/mcp`,
          headers: {},
        },
      }),
      /upstream connection timed out/i,
    );
    assert.ok(Date.now() - started < 1_000);
  } finally {
    server.closeAllConnections();
    await new Promise<void>((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  }
});

test('upstream redirects are rejected before any request reaches the redirected host', async () => {
  let redirectedRequests = 0;
  const target = createServer((_request, response) => {
    redirectedRequests += 1;
    response.statusCode = 200;
    response.end();
  });
  const redirect = createServer((_request, response) => {
    const targetAddress = target.address();
    assert.ok(targetAddress && typeof targetAddress === 'object');
    response.statusCode = 307;
    response.setHeader('location', `http://127.0.0.1:${targetAddress.port}/private`);
    response.end();
  });
  await Promise.all([
    new Promise<void>((resolve) => target.listen(0, '127.0.0.1', resolve)),
    new Promise<void>((resolve) => redirect.listen(0, '127.0.0.1', resolve)),
  ]);
  try {
    const address = redirect.address();
    assert.ok(address && typeof address === 'object');
    const factory = new SdkConnectorFactory({
      maximumResourceBytes: 1024,
      maximumCatalogPages: 4,
      upstreamTimeoutMs: 250,
      maximumConcurrencyPerScope: 1,
      networkHostAllowlist: ['127.0.0.1'],
    });
    await assert.rejects(
      factory.connect({
        ...connectionView,
        connectionProfile: {
          type: 'streamable_http',
          url: `http://127.0.0.1:${address.port}/mcp`,
          headers: { authorization: 'Bearer must-not-follow' },
        },
      }),
      /redirect is unavailable/i,
    );
    assert.equal(redirectedRequests, 0);
  } finally {
    redirect.closeAllConnections();
    target.closeAllConnections();
    await Promise.all([
      new Promise<void>((resolve, reject) => redirect.close((error) => error ? reject(error) : resolve())),
      new Promise<void>((resolve, reject) => target.close((error) => error ? reject(error) : resolve())),
    ]);
  }
});

test('structured diagnostics never serialize URL, query, header, credential, body, or HTML', () => {
  const recorder = new McpAppsDiagnosticRecorder(2);
  recorder.record({
    stage: 'resource',
    view: connectionView,
    serverRef: connectionView.serverRef,
    sessionId: 'private-session-id',
    outcome: 'failed',
    errorCode: 'RESOURCE_TOO_LARGE',
    manifestRevision: 3,
  });
  const serialized = JSON.stringify(recorder.snapshot());
  for (const secret of [
    'actor-sensitive',
    'workspace-sensitive',
    'private-session-id',
    'secret-upstream',
    'credential=private',
    'authorization',
    'Bearer private',
    '<main>',
  ]) {
    assert.equal(serialized.includes(secret), false, secret);
  }
  assert.deepEqual(Object.keys(recorder.snapshot()[0]!).sort(), [
    'actorScopeHash',
    'errorCode',
    'manifestRevision',
    'outcome',
    'serverRef',
    'sessionRef',
    'stage',
    'workspaceScopeHash',
  ]);
});
