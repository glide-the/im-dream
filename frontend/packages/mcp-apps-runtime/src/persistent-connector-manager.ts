// [Input] Validated request scope, short-lived Python views, and an injected upstream connector factory.
// [Output] Process-reused, policy-keyed leases with per-request validation, concurrency, and teardown.
// [Pos] Sole upstream connection/catalog lifecycle owner inside the server-only Runtime package.
// [Sync] 2026-09-06: revalidate every request and add Browser/plugin scope, expiry timers, and bounded operations.
// [Sync] 2026-09-06: invalidate leases when per-connection App settings revision changes.

import { randomUUID } from 'node:crypto';

import {
  type ConnectionLease,
  type ConnectionViewProvider,
  type ConnectorFactory,
  type McpAppsRequestContext,
  McpAppsRuntimeError,
  authorizationStateKey,
  connectionKey,
} from './contracts.ts';
import { McpAppsDiagnosticRecorder } from './diagnostics.ts';

type Entry = {
  connector: ConnectionLease['connector'];
  view: ConnectionLease['view'];
  browserSessionScope: string | null;
  manifestRevision: number;
  references: number;
  invalid: boolean;
  expiryTimer: ReturnType<typeof setTimeout> | null;
};

const MAX_TIMER_DELAY_MS = 2_147_483_647;

export class PersistentConnectorManager {
  readonly #entries = new Map<string, Entry>();
  readonly #connecting = new Map<string, Promise<Entry>>();
  readonly #leases = new Map<string, string>();
  readonly #activeOperations = new Map<string, number>();
  readonly #maximumConcurrencyPerScope: number;
  readonly diagnosticsRecorder: McpAppsDiagnosticRecorder;

  constructor(
    readonly provider: ConnectionViewProvider,
    readonly factory: ConnectorFactory,
    options: Readonly<{
      maximumConcurrencyPerScope?: number;
      diagnosticsRecorder?: McpAppsDiagnosticRecorder;
    }> = {},
  ) {
    this.#maximumConcurrencyPerScope = options.maximumConcurrencyPerScope ?? Number.MAX_SAFE_INTEGER;
    if (!Number.isSafeInteger(this.#maximumConcurrencyPerScope) || this.#maximumConcurrencyPerScope < 1) {
      throw new TypeError('maximumConcurrencyPerScope must be a positive safe integer');
    }
    this.diagnosticsRecorder = options.diagnosticsRecorder ?? new McpAppsDiagnosticRecorder();
  }

  async acquire(context: McpAppsRequestContext, manifestRevision = 1): Promise<ConnectionLease> {
    const view = await this.provider.getConnectionView({
      authorization: context.authorization,
      workspaceScope: context.workspaceScope,
      serverRef: context.serverRef,
    });
    const key = connectionKey(view, context.browserSessionScope, manifestRevision);
    const staleKeys = [...this.#entries.entries()]
      .filter(([candidateKey, candidate]) => (
        candidateKey !== key
        && candidate.view.actorScope === view.actorScope
        && candidate.view.workspaceScope === view.workspaceScope
        && candidate.view.serverId === view.serverId
        && candidate.view.serverRef === view.serverRef
        && candidate.browserSessionScope === context.browserSessionScope
      ))
      .map(([candidateKey]) => candidateKey);
    await Promise.all(staleKeys.map((candidateKey) => this.invalidateKey(candidateKey)));
    let entry = this.#entries.get(key);
    if (entry && authorizationStateKey(entry.view) !== authorizationStateKey(view)) {
      await this.invalidateKey(key);
      throw new McpAppsRuntimeError(409, 'SESSION_POLICY_CONFLICT', 'MCP Apps session policy is inconsistent.');
    }
    if (!entry || entry.invalid) {
      let pending = this.#connecting.get(key);
      if (!pending) {
        pending = this.factory.connect(view).then((connector) => ({
          connector,
          view,
          browserSessionScope: context.browserSessionScope,
          manifestRevision,
          references: 0,
          invalid: false,
          expiryTimer: null,
        }));
        this.#connecting.set(key, pending);
      }
      try {
        entry = await pending;
        if (authorizationStateKey(entry.view) !== authorizationStateKey(view)) {
          if (this.#entries.get(key) === entry) await this.invalidateKey(key);
          else await entry.connector.close().catch(() => undefined);
          throw new McpAppsRuntimeError(409, 'SESSION_POLICY_CONFLICT', 'MCP Apps session policy is inconsistent.');
        }
        this.#entries.set(key, entry);
        this.#scheduleExpiry(key, entry);
      } finally {
        if (this.#connecting.get(key) === pending) this.#connecting.delete(key);
      }
    }
    entry.references += 1;
    const id = randomUUID();
    this.#leases.set(id, key);
    return Object.freeze({
      id,
      key,
      view: entry.view,
      connector: entry.connector,
      browserSessionScope: context.browserSessionScope,
      manifestRevision,
    });
  }

  async revalidate(
    lease: ConnectionLease,
    context: McpAppsRequestContext,
    manifestRevision = lease.manifestRevision,
  ): Promise<ConnectionLease> {
    const currentKey = this.#leases.get(lease.id);
    const entry = currentKey ? this.#entries.get(currentKey) : undefined;
    if (!entry || entry.invalid || currentKey !== lease.key) {
      throw new McpAppsRuntimeError(409, 'SESSION_INVALIDATED', 'MCP Apps session is no longer current.');
    }
    if (
      lease.browserSessionScope !== context.browserSessionScope
      || lease.manifestRevision !== manifestRevision
    ) {
      await this.invalidateKey(currentKey);
      throw new McpAppsRuntimeError(409, 'SESSION_LIFECYCLE_CHANGED', 'MCP Apps session lifecycle changed.');
    }
    let refreshed;
    try {
      refreshed = await this.provider.getConnectionView({
        authorization: context.authorization,
        workspaceScope: context.workspaceScope,
        serverRef: context.serverRef,
        expectedConfigRevision: entry.view.configRevision,
        expectedCredentialRevision: entry.view.credentialRevision,
        expectedAppSettingsRevision: entry.view.appSettingsRevision,
        expectedPolicyRevision: entry.view.policy.revision,
      });
    } catch (error) {
      await this.invalidateKey(currentKey);
      throw error;
    }
    if (
      connectionKey(refreshed, context.browserSessionScope, manifestRevision) !== currentKey
      || authorizationStateKey(refreshed) !== authorizationStateKey(entry.view)
    ) {
      await this.invalidateKey(currentKey);
      throw new McpAppsRuntimeError(409, 'SESSION_REVISION_CHANGED', 'MCP Apps session revision changed.');
    }
    entry.view = refreshed;
    this.#scheduleExpiry(currentKey, entry);
    return Object.freeze({ ...lease, view: refreshed });
  }

  async runWithScope<T>(lease: ConnectionLease, operation: () => Promise<T>): Promise<T> {
    const entry = this.#entries.get(lease.key);
    if (!entry || entry.invalid || this.#leases.get(lease.id) !== lease.key) {
      throw new McpAppsRuntimeError(409, 'SESSION_INVALIDATED', 'MCP Apps session is no longer current.');
    }
    const scopeKey = JSON.stringify([
      lease.view.actorScope,
      lease.view.workspaceScope,
      lease.view.serverId,
    ]);
    const active = this.#activeOperations.get(scopeKey) ?? 0;
    if (active >= this.#maximumConcurrencyPerScope) {
      throw new McpAppsRuntimeError(429, 'SCOPE_CONCURRENCY_EXCEEDED', 'MCP Apps scope is busy.');
    }
    this.#activeOperations.set(scopeKey, active + 1);
    try {
      return await operation();
    } finally {
      const remaining = (this.#activeOperations.get(scopeKey) ?? 1) - 1;
      if (remaining <= 0) this.#activeOperations.delete(scopeKey);
      else this.#activeOperations.set(scopeKey, remaining);
    }
  }

  async release(lease: ConnectionLease): Promise<void> {
    const key = this.#leases.get(lease.id);
    if (!key) return;
    this.#leases.delete(lease.id);
    const entry = this.#entries.get(key);
    if (!entry) return;
    entry.references = Math.max(0, entry.references - 1);
    if (entry.references === 0) {
      this.#entries.delete(key);
      if (entry.expiryTimer) clearTimeout(entry.expiryTimer);
      entry.expiryTimer = null;
      await entry.connector.close().catch(() => undefined);
    }
  }

  async invalidateServer(serverRef: string): Promise<void> {
    const keys = [...this.#entries.entries()]
      .filter(([, entry]) => entry.view.serverRef === serverRef)
      .map(([key]) => key);
    await Promise.all(keys.map((key) => this.invalidateKey(key)));
  }

  async invalidateKey(key: string): Promise<void> {
    const entry = this.#entries.get(key);
    if (!entry) return;
    entry.invalid = true;
    this.#entries.delete(key);
    if (entry.expiryTimer) clearTimeout(entry.expiryTimer);
    entry.expiryTimer = null;
    for (const [leaseId, leaseKey] of this.#leases) {
      if (leaseKey === key) this.#leases.delete(leaseId);
    }
    await entry.connector.close().catch(() => undefined);
  }

  async closeAll(): Promise<void> {
    const entries = [...this.#entries.values()];
    this.#entries.clear();
    this.#leases.clear();
    this.#activeOperations.clear();
    for (const entry of entries) {
      if (entry.expiryTimer) clearTimeout(entry.expiryTimer);
      entry.expiryTimer = null;
    }
    await Promise.all(entries.map((entry) => entry.connector.close().catch(() => undefined)));
  }

  #scheduleExpiry(key: string, entry: Entry): void {
    if (entry.expiryTimer) clearTimeout(entry.expiryTimer);
    entry.expiryTimer = null;
    const schedule = () => {
      if (entry.invalid || this.#entries.get(key) !== entry) return;
      const remaining = Date.parse(entry.view.expiresAt) - Date.now();
      if (!Number.isFinite(remaining) || remaining <= 0) {
        void this.invalidateKey(key);
        return;
      }
      const delay = Math.min(remaining, MAX_TIMER_DELAY_MS);
      entry.expiryTimer = setTimeout(() => {
        entry.expiryTimer = null;
        if (delay < remaining) schedule();
        else void this.invalidateKey(key);
      }, delay);
      entry.expiryTimer.unref?.();
    };
    schedule();
  }

  diagnostics(): Readonly<{ connections: number; leases: number }> {
    return Object.freeze({ connections: this.#entries.size, leases: this.#leases.size });
  }
}
