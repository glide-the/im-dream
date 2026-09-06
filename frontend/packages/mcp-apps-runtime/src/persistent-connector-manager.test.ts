// [Input] Injected short-lived views and recording connectors.
// [Output] Provider-free process reuse, concurrent Browser isolation, revision invalidation, and teardown assertions.
// [Pos] task_411-02 manager contract test; no network, credential, database, or Browser state.
// [Sync] 2026-09-06: prove scope isolation, revision revalidation, and automatic short-view expiry teardown.
// [Sync] 2026-09-06: prove canonical hashed profile identity rejects same-revision credential drift.

import assert from 'node:assert/strict';
import test from 'node:test';

import type {
  ConnectionViewProvider,
  ConnectorFactory,
  McpAppsConnectionView,
  McpAppsRequestContext,
} from './contracts.ts';
import {
  McpAppsRuntimeError,
  authorizationStateKey,
  connectionProfileDigest,
} from './contracts.ts';
import { PersistentConnectorManager } from './persistent-connector-manager.ts';

const context: McpAppsRequestContext = Object.freeze({
  authorization: 'Bearer test-only',
  authorizationFingerprint: 'fingerprint',
  workspaceScope: null,
  serverRef: 'official-basic',
  browserSessionScope: 'browser-a',
});

function view(revision = 4, expiresAt = '2099-01-01T00:00:00.000Z'): McpAppsConnectionView {
  return Object.freeze({
    actorScope: 'actor-1',
    workspaceScope: null,
    serverId: 'server-1',
    serverRef: 'official-basic',
    transportKind: 'streamable_http',
    enabled: true,
    configRevision: revision,
    credentialRevision: 2,
    expiresAt,
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
}

class Provider implements ConnectionViewProvider {
  next = view();
  failure: Error | null = null;
  calls: Array<{
    expectedConfigRevision?: number;
    expectedCredentialRevision?: number;
    expectedPolicyRevision?: number;
  }> = [];

  async getConnectionView(input: {
    expectedConfigRevision?: number;
    expectedCredentialRevision?: number;
    expectedPolicyRevision?: number;
  }): Promise<McpAppsConnectionView> {
    if (this.failure) throw this.failure;
    this.calls.push({
      expectedConfigRevision: input.expectedConfigRevision,
      expectedCredentialRevision: input.expectedCredentialRevision,
      expectedPolicyRevision: input.expectedPolicyRevision,
    });
    return this.next;
  }
}

class Factory implements ConnectorFactory {
  connects = 0;
  closes = 0;

  async connect() {
    this.connects += 1;
    return {
      catalog: { tools: [{ name: 'get-time', inputSchema: { type: 'object' as const } }], resources: [{ uri: 'ui://get-time/mcp-app.html', name: 'time' }] },
      async readResource() { return { contents: [] }; },
      async callTool() { return { content: [] }; },
      close: async () => { this.closes += 1; },
    };
  }
}

test('reuses one process connection until the final session lease closes', async () => {
  const provider = new Provider();
  const factory = new Factory();
  const manager = new PersistentConnectorManager(provider, factory);
  const first = await manager.acquire(context);
  const second = await manager.acquire(context);

  assert.equal(factory.connects, 1);
  assert.notEqual(first.id, second.id);
  assert.deepEqual(manager.diagnostics(), { connections: 1, leases: 2 });
  await manager.release(first);
  assert.equal(factory.closes, 0);
  await manager.release(second);
  assert.equal(factory.closes, 1);
  assert.deepEqual(manager.diagnostics(), { connections: 0, leases: 0 });
});

test('coalesces concurrent acquire calls for the same connection key', async () => {
  const provider = new Provider();
  const factory = new Factory();
  const manager = new PersistentConnectorManager(provider, factory);
  const [first, second] = await Promise.all([
    manager.acquire(context),
    manager.acquire(context),
  ]);

  assert.equal(factory.connects, 1);
  assert.equal(first.connector, second.connector);
  assert.deepEqual(manager.diagnostics(), { connections: 1, leases: 2 });
  await Promise.all([manager.release(first), manager.release(second)]);
  assert.equal(factory.closes, 1);
});

test('concurrent Browser scopes keep independent connectors, revalidation, and teardown', async () => {
  const provider = new Provider();
  const factory = new Factory();
  const manager = new PersistentConnectorManager(provider, factory);
  const browserB = Object.freeze({ ...context, browserSessionScope: 'browser-b' });
  const [leaseA, leaseB] = await Promise.all([
    manager.acquire(context),
    manager.acquire(browserB),
  ]);

  assert.notEqual(leaseA.connector, leaseB.connector);
  assert.equal(factory.connects, 2);
  assert.deepEqual(manager.diagnostics(), { connections: 2, leases: 2 });
  await Promise.all([
    manager.revalidate(leaseA, context),
    manager.revalidate(leaseB, browserB),
  ]);
  let finishA!: () => void;
  const activeA = manager.runWithScope(
    leaseA,
    () => new Promise<void>((resolve) => { finishA = resolve; }),
  );
  await Promise.resolve();
  assert.equal(await manager.runWithScope(leaseB, async () => 'b'), 'b');
  finishA();
  await activeA;

  await manager.release(leaseA);
  assert.equal(factory.closes, 1);
  assert.deepEqual(manager.diagnostics(), { connections: 1, leases: 1 });
  const refreshedB = await manager.revalidate(leaseB, browserB);
  assert.equal(await manager.runWithScope(refreshedB, async () => 'still-b'), 'still-b');
  await manager.release(refreshedB);
  assert.equal(factory.closes, 2);
  assert.deepEqual(manager.diagnostics(), { connections: 0, leases: 0 });
});

test('a changed revision invalidates the old lease and connector', async () => {
  const provider = new Provider();
  provider.next = view(4);
  const factory = new Factory();
  const manager = new PersistentConnectorManager(provider, factory);
  const lease = await manager.acquire(context);
  provider.next = view(5);

  await assert.rejects(manager.revalidate(lease, context), /revision changed/);
  assert.equal(provider.calls.at(-1)?.expectedConfigRevision, 4);
  assert.equal(provider.calls.at(-1)?.expectedCredentialRevision, 2);
  assert.equal(provider.calls.at(-1)?.expectedPolicyRevision, 7);
  assert.equal(factory.closes, 1);
  assert.deepEqual(manager.diagnostics(), { connections: 0, leases: 0 });
});

test('every existing request revalidates and a provider denial tears down the connector', async () => {
  const provider = new Provider();
  const factory = new Factory();
  const manager = new PersistentConnectorManager(provider, factory);
  const lease = await manager.acquire(context);

  await manager.revalidate(lease, context);
  assert.equal(provider.calls.length, 2);
  provider.failure = new McpAppsRuntimeError(503, 'CONFIG_PROVIDER_REJECTED', 'unavailable');
  await assert.rejects(manager.revalidate(lease, context), /unavailable/);
  assert.equal(factory.closes, 1);
  assert.deepEqual(manager.diagnostics(), { connections: 0, leases: 0 });
});

test('a retained lease closes automatically when its short-lived view expires', async () => {
  const provider = new Provider();
  provider.next = view(4, new Date(Date.now() + 25).toISOString());
  const factory = new Factory();
  const manager = new PersistentConnectorManager(provider, factory);
  await manager.acquire(context);

  await new Promise((resolve) => setTimeout(resolve, 60));
  assert.equal(factory.closes, 1);
  assert.deepEqual(manager.diagnostics(), { connections: 0, leases: 0 });
});

test('current allowlist changes invalidate even when a policy revision is incorrectly reused', async () => {
  const provider = new Provider();
  const factory = new Factory();
  const manager = new PersistentConnectorManager(provider, factory);
  const lease = await manager.acquire(context);
  provider.next = Object.freeze({ ...view(), appCallableLowRiskTools: [] });

  await assert.rejects(manager.revalidate(lease, context), /revision changed/);
  assert.equal(factory.closes, 1);
});

test('a new acquire cannot reuse a connector after same-revision policy drift', async () => {
  const provider = new Provider();
  const factory = new Factory();
  const manager = new PersistentConnectorManager(provider, factory);
  await manager.acquire(context);
  provider.next = Object.freeze({ ...view(), allowedResources: ['ui://different/app.html'] });

  await assert.rejects(manager.acquire(context), /policy is inconsistent/);
  assert.equal(factory.closes, 1);
  assert.deepEqual(manager.diagnostics(), { connections: 0, leases: 0 });
});

test('same-revision connection profile drift invalidates without exposing credentials', async () => {
  const oldSecret = 'old-upstream-private';
  const newSecret = 'new-upstream-private';
  const provider = new Provider();
  provider.next = Object.freeze({
    ...view(),
    connectionProfile: Object.freeze({
      ...view().connectionProfile,
      headers: Object.freeze({ Authorization: `Bearer ${oldSecret}` }),
    }),
  });
  const factory = new Factory();
  const manager = new PersistentConnectorManager(provider, factory);
  await manager.acquire(context);
  provider.next = Object.freeze({
    ...provider.next,
    connectionProfile: Object.freeze({
      ...provider.next.connectionProfile,
      headers: Object.freeze({ Authorization: `Bearer ${newSecret}` }),
    }),
  });

  await assert.rejects(
    manager.acquire(context),
    (error: unknown) => error instanceof McpAppsRuntimeError
      && !error.message.includes(oldSecret)
      && !error.message.includes(newSecret),
  );
  const stateKey = authorizationStateKey(provider.next);
  assert.equal(stateKey.includes(oldSecret), false);
  assert.equal(stateKey.includes(newSecret), false);
  assert.equal(factory.closes, 1);
});

test('connection profile digest is canonical across header insertion order', () => {
  const first = Object.freeze({
    type: 'streamable_http' as const,
    url: 'https://mcp.example.test/mcp',
    headers: Object.freeze({ 'X-Second': 'two', Authorization: 'Bearer private' }),
  });
  const reordered = Object.freeze({
    type: 'streamable_http' as const,
    url: 'https://mcp.example.test/mcp',
    headers: Object.freeze({ Authorization: 'Bearer private', 'X-Second': 'two' }),
  });
  const changed = Object.freeze({
    ...reordered,
    headers: Object.freeze({ Authorization: 'Bearer rotated', 'X-Second': 'two' }),
  });

  assert.equal(connectionProfileDigest(first), connectionProfileDigest(reordered));
  assert.notEqual(connectionProfileDigest(first), connectionProfileDigest(changed));
  assert.equal(connectionProfileDigest(first).includes('private'), false);
});

test('per-scope concurrency rejects excess work without affecting another Browser scope', async () => {
  const provider = new Provider();
  const factory = new Factory();
  const manager = new PersistentConnectorManager(provider, factory, { maximumConcurrencyPerScope: 1 });
  const lease = await manager.acquire(context);
  let release!: () => void;
  const held = manager.runWithScope(lease, () => new Promise<void>((resolve) => { release = resolve; }));
  await Promise.resolve();

  await assert.rejects(
    manager.runWithScope(lease, async () => undefined),
    (error: unknown) => error instanceof McpAppsRuntimeError && error.status === 429,
  );
  release();
  await held;
  assert.equal(await manager.runWithScope(lease, async () => 'ok'), 'ok');
  await manager.release(lease);
});

test('explicit Server invalidation closes all matching references once', async () => {
  const provider = new Provider();
  const factory = new Factory();
  const manager = new PersistentConnectorManager(provider, factory);
  await manager.acquire(context);
  await manager.acquire(context);

  await manager.invalidateServer('official-basic');
  assert.equal(factory.closes, 1);
  assert.deepEqual(manager.diagnostics(), { connections: 0, leases: 0 });
});
