// [Input] Standard same-origin MCP Streamable HTTP GET/POST/DELETE requests and a validated route context.
// [Output] Manifest-governed downstream sessions with revalidated resources and low-risk calls.
// [Pos] Runtime HTTP adapter; page tools/call and unknown capabilities fail before any upstream tool call.
// [Sync] 2026-09-06: expire adapter sessions with their short-lived views and revalidate policy/manifest before bounded calls.

import { randomUUID } from 'node:crypto';

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { WebStandardStreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/webStandardStreamableHttp.js';
import {
  CallToolRequestSchema,
  ListResourcesRequestSchema,
  ListToolsRequestSchema,
  ReadResourceRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

import {
  type ConnectionLease,
  type McpAppsRequestContext,
  McpAppsRuntimeError,
  deniedToolResult,
} from './contracts.ts';
import type { PersistentConnectorManager } from './persistent-connector-manager.ts';
import {
  manifestIdentity,
  requireEnabledPlugin,
  type McpAppsPluginManifest,
  type PluginManifestProvider,
} from './plugin-manifest.ts';

type RuntimeSession = {
  id: string | null;
  authorizationFingerprint: string;
  context: McpAppsRequestContext;
  lease: ConnectionLease;
  server: Server;
  transport: WebStandardStreamableHTTPServerTransport;
  manifestIdentity: string;
  manifestRevision: number;
  manifestFeatures: McpAppsPluginManifest['features'];
  expiryTimer: ReturnType<typeof setTimeout> | null;
  closed: boolean;
};

const MAX_TIMER_DELAY_MS = 2_147_483_647;

function safeErrorResponse(error: unknown): Response {
  const known = error instanceof McpAppsRuntimeError ? error : null;
  return Response.json(
    {
      jsonrpc: '2.0',
      error: { code: -32000, message: known?.message ?? 'MCP Apps request failed.' },
      id: null,
    },
    {
      status: known?.status ?? 500,
      headers: { 'cache-control': 'no-store' },
    },
  );
}

async function parsePostBody(request: Request): Promise<unknown> {
  try {
    const body = await request.clone().json();
    if (Array.isArray(body)) throw new Error('Batch requests are unavailable.');
    return body;
  } catch {
    throw new McpAppsRuntimeError(400, 'INVALID_MCP_BODY', 'MCP request body is invalid.');
  }
}

export class McpAppsHttpAdapter {
  readonly #sessions = new Map<string, RuntimeSession>();

  constructor(
    readonly manager: PersistentConnectorManager,
    readonly manifestProvider: PluginManifestProvider,
  ) {}

  async handle(request: Request, context: McpAppsRequestContext): Promise<Response> {
    const sessionId = request.headers.get('mcp-session-id');
    try {
      const manifest = requireEnabledPlugin(this.manifestProvider);
      const invalidatedSessions = await this.#reconcileManifest(manifest);
      if (sessionId && invalidatedSessions.has(sessionId)) {
        throw new McpAppsRuntimeError(409, 'PLUGIN_REVISION_CHANGED', 'MCP Apps plugin revision changed.');
      }
      if (sessionId) return await this.#handleExisting(request, context, sessionId, manifest);
      if (request.method !== 'POST') {
        throw new McpAppsRuntimeError(400, 'SESSION_REQUIRED', 'MCP session is required.');
      }
      const body = await parsePostBody(request);
      if (!body || typeof body !== 'object' || (body as { method?: unknown }).method !== 'initialize') {
        throw new McpAppsRuntimeError(400, 'INITIALIZE_REQUIRED', 'MCP initialize is required.');
      }
      return await this.#initialize(request, context, body, manifest);
    } catch (error) {
      const failedSession = sessionId ? this.#sessions.get(sessionId) : undefined;
      const known = error instanceof McpAppsRuntimeError ? error : null;
      this.manager.diagnosticsRecorder.record({
        stage: known?.code.startsWith('PLUGIN_') ? 'plugin_lifecycle' : 'connection_view',
        view: failedSession?.lease.view,
        serverRef: context.serverRef,
        sessionId,
        outcome: known?.status === 403 || known?.status === 409 ? 'denied' : 'failed',
        errorCode: known?.code ?? 'REQUEST_FAILED',
        manifestRevision: failedSession?.manifestRevision ?? null,
      });
      if (
        sessionId
        && error instanceof McpAppsRuntimeError
        && [403, 409, 503].includes(error.status)
      ) {
        await this.#drop(sessionId, true);
      }
      if (
        error instanceof McpAppsRuntimeError
        && error.status === 503
        && error.code.startsWith('PLUGIN_')
      ) {
        await this.#dropAllSessions();
      }
      return safeErrorResponse(error);
    }
  }

  async #initialize(
    request: Request,
    context: McpAppsRequestContext,
    parsedBody: unknown,
    manifest: McpAppsPluginManifest,
  ): Promise<Response> {
    const lease = await this.manager.acquire(context, manifest.revision);
    let session: RuntimeSession | null = null;
    try {
      const server = new Server(
        { name: 'ink-dream-mcp-apps-runtime', version: '1.0.0' },
        { capabilities: { tools: {}, resources: {} } },
      );
      const transport = new WebStandardStreamableHTTPServerTransport({
        sessionIdGenerator: randomUUID,
        enableJsonResponse: true,
        onsessioninitialized: (id) => {
          if (!session) return;
          session.id = id;
          this.#sessions.set(id, session);
          this.#scheduleSessionExpiry(session);
        },
        onsessionclosed: async (id) => {
          await this.#drop(id, false);
        },
      });
      session = {
        id: null,
        authorizationFingerprint: context.authorizationFingerprint,
        context,
        lease,
        server,
        transport,
        manifestIdentity: manifestIdentity(manifest),
        manifestRevision: manifest.revision,
        manifestFeatures: manifest.features,
        expiryTimer: null,
        closed: false,
      };
      this.#registerHandlers(session);
      await server.connect(transport);
      const response = await transport.handleRequest(request, { parsedBody });
      if (!session.id) await this.#closeSession(session, true);
      return response;
    } catch (error) {
      if (session) await this.#closeSession(session, true);
      else await this.manager.release(lease);
      throw error;
    }
  }

  async #handleExisting(
    request: Request,
    context: McpAppsRequestContext,
    sessionId: string,
    manifest: McpAppsPluginManifest,
  ): Promise<Response> {
    const session = this.#sessions.get(sessionId);
    if (!session || session.closed) {
      throw new McpAppsRuntimeError(404, 'SESSION_NOT_FOUND', 'MCP Apps session is unavailable.');
    }
    if (
      session.authorizationFingerprint !== context.authorizationFingerprint
      || session.context.serverRef !== context.serverRef
      || session.context.workspaceScope !== context.workspaceScope
      || session.context.browserSessionScope !== context.browserSessionScope
    ) {
      throw new McpAppsRuntimeError(403, 'SESSION_SCOPE_MISMATCH', 'MCP Apps session scope is invalid.');
    }
    if (session.manifestIdentity !== manifestIdentity(manifest)) {
      await this.#drop(sessionId, true);
      throw new McpAppsRuntimeError(409, 'PLUGIN_REVISION_CHANGED', 'MCP Apps plugin revision changed.');
    }
    try {
      session.lease = await this.manager.revalidate(session.lease, context, manifest.revision);
      this.#scheduleSessionExpiry(session);
      const parsedBody = request.method === 'POST' ? await parsePostBody(request) : undefined;
      return await session.transport.handleRequest(request, { parsedBody });
    } catch (error) {
      if (error instanceof McpAppsRuntimeError && [403, 409, 503].includes(error.status)) {
        await this.#drop(sessionId, true);
      }
      throw error;
    }
  }

  #registerHandlers(session: RuntimeSession): void {
    session.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: session.lease.connector.catalog.tools.filter((tool) => session.lease.view.allowedTools.includes(tool.name)),
    }));
    session.server.setRequestHandler(ListResourcesRequestSchema, async () => ({
      resources: session.lease.connector.catalog.resources.filter((resource) => session.lease.view.allowedResources.includes(resource.uri)),
    }));
    session.server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
      const uri = request.params.uri;
      if (
        !session.manifestFeatures.resourceReads
        || !session.lease.view.policy.effective.resourceReads
        || !session.lease.view.allowedResources.includes(uri)
      ) {
        this.manager.diagnosticsRecorder.record({
          stage: 'authorization',
          view: session.lease.view,
          serverRef: session.context.serverRef,
          sessionId: session.id,
          outcome: 'denied',
          errorCode: 'RESOURCE_DENIED',
          manifestRevision: session.manifestRevision,
        });
        throw new McpAppsRuntimeError(403, 'RESOURCE_DENIED', 'MCP App resource is not allowed.');
      }
      try {
        const result = await this.manager.runWithScope(
          session.lease,
          () => session.lease.connector.readResource(uri),
        );
        this.manager.diagnosticsRecorder.record({
          stage: 'resource',
          view: session.lease.view,
          serverRef: session.context.serverRef,
          sessionId: session.id,
          outcome: 'allowed',
          manifestRevision: session.manifestRevision,
        });
        return result;
      } catch (error) {
        this.manager.diagnosticsRecorder.record({
          stage: 'resource',
          view: session.lease.view,
          serverRef: session.context.serverRef,
          sessionId: session.id,
          outcome: 'failed',
          errorCode: error instanceof McpAppsRuntimeError ? error.code : 'RESOURCE_FAILED',
          manifestRevision: session.manifestRevision,
        });
        throw error;
      }
    });
    session.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const name = request.params.name;
      const args = request.params.arguments ?? {};
      if (
        !session.manifestFeatures.lowRiskToolCalls
        || !session.lease.view.policy.effective.lowRiskToolCalls
        || !session.lease.view.allowedTools.includes(name)
        || !session.lease.view.appCallableLowRiskTools.includes(name)
        || !session.lease.connector.catalog.tools.some((tool) => tool.name === name)
      ) {
        this.manager.diagnosticsRecorder.record({
          stage: 'authorization',
          view: session.lease.view,
          serverRef: session.context.serverRef,
          sessionId: session.id,
          outcome: 'denied',
          errorCode: 'TOOL_DENIED',
          manifestRevision: session.manifestRevision,
        });
        return deniedToolResult();
      }
      let result;
      try {
        result = await this.manager.runWithScope(
          session.lease,
          () => session.lease.connector.callTool(name, args),
        );
      } catch (error) {
        this.manager.diagnosticsRecorder.record({
          stage: 'upstream',
          view: session.lease.view,
          serverRef: session.context.serverRef,
          sessionId: session.id,
          outcome: 'failed',
          errorCode: error instanceof McpAppsRuntimeError ? error.code : 'UPSTREAM_FAILED',
          manifestRevision: session.manifestRevision,
        });
        throw error;
      }
      this.manager.diagnosticsRecorder.record({
        stage: 'upstream',
        view: session.lease.view,
        serverRef: session.context.serverRef,
        sessionId: session.id,
        outcome: 'allowed',
        manifestRevision: session.manifestRevision,
      });
      return result;
    });
  }

  async #reconcileManifest(manifest: McpAppsPluginManifest): Promise<ReadonlySet<string>> {
    const identity = manifestIdentity(manifest);
    const stale = [...this.#sessions.entries()]
      .filter(([, session]) => session.manifestIdentity !== identity)
      .map(([sessionId]) => sessionId);
    for (const sessionId of stale) {
      const session = this.#sessions.get(sessionId);
      if (!session) continue;
      this.manager.diagnosticsRecorder.record({
        stage: 'plugin_lifecycle',
        view: session.lease.view,
        serverRef: session.context.serverRef,
        sessionId,
        outcome: 'closed',
        errorCode: 'PLUGIN_REVISION_CHANGED',
        manifestRevision: manifest.revision,
      });
    }
    await Promise.all(stale.map((sessionId) => this.#drop(sessionId, true)));
    return new Set(stale);
  }

  async #dropAllSessions(): Promise<void> {
    await Promise.all([...this.#sessions.keys()].map((sessionId) => this.#drop(sessionId, true)));
  }

  async #drop(sessionId: string, closeTransport: boolean): Promise<void> {
    const session = this.#sessions.get(sessionId);
    if (!session) return;
    this.#sessions.delete(sessionId);
    await this.#closeSession(session, closeTransport);
  }

  async #closeSession(session: RuntimeSession, closeTransport: boolean): Promise<void> {
    if (session.closed) return;
    session.closed = true;
    if (session.expiryTimer) clearTimeout(session.expiryTimer);
    session.expiryTimer = null;
    if (closeTransport) await session.transport.close().catch(() => undefined);
    await session.server.close().catch(() => undefined);
    await this.manager.release(session.lease);
  }

  #scheduleSessionExpiry(session: RuntimeSession): void {
    if (session.expiryTimer) clearTimeout(session.expiryTimer);
    session.expiryTimer = null;
    const schedule = () => {
      const sessionId = session.id;
      if (!sessionId || session.closed || this.#sessions.get(sessionId) !== session) return;
      const remaining = Date.parse(session.lease.view.expiresAt) - Date.now();
      if (!Number.isFinite(remaining) || remaining <= 0) {
        this.manager.diagnosticsRecorder.record({
          stage: 'connection_view',
          view: session.lease.view,
          serverRef: session.context.serverRef,
          sessionId,
          outcome: 'closed',
          errorCode: 'SESSION_EXPIRED',
          manifestRevision: session.manifestRevision,
        });
        void this.#drop(sessionId, true);
        return;
      }
      const delay = Math.min(remaining, MAX_TIMER_DELAY_MS);
      session.expiryTimer = setTimeout(() => {
        session.expiryTimer = null;
        if (delay < remaining) schedule();
        else void this.#drop(sessionId, true);
      }, delay);
      session.expiryTimer.unref?.();
    };
    schedule();
  }

  async closeAll(): Promise<void> {
    const sessions = [...this.#sessions.values()];
    this.#sessions.clear();
    await Promise.all(sessions.map((session) => this.#closeSession(session, true)));
    await this.manager.closeAll();
  }

  diagnostics(): Readonly<{ sessions: number }> {
    return Object.freeze({ sessions: this.#sessions.size });
  }

  diagnosticEvents() {
    return this.manager.diagnosticsRecorder.snapshot();
  }
}
