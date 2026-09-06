// [Input] Locked MCP SDK/ext-apps packages and an isolated test-owned transport.
// [Output] One deterministic provider-free read-only AppServer identity and UI resource.
// [Pos] task_302 fixture only; never selected by production composition roots.
// [Sync] 2026-09-05: create the canonical Phase 1 AppServer with stdio lifecycle.

import { randomUUID } from 'node:crypto';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

const frontendRequire = createRequire(
  new URL('../../../../frontend/package.json', import.meta.url),
);
const loadFrontendModule = async (specifier) => (
  import(pathToFileURL(frontendRequire.resolve(specifier)).href)
);

const [
  { McpServer },
  { StreamableHTTPServerTransport },
  { StdioServerTransport },
  { createMcpExpressApp },
  { isInitializeRequest },
  { registerAppResource, registerAppTool, RESOURCE_MIME_TYPE },
  z,
] = await Promise.all([
  loadFrontendModule('@modelcontextprotocol/sdk/server/mcp.js'),
  loadFrontendModule('@modelcontextprotocol/sdk/server/streamableHttp.js'),
  loadFrontendModule('@modelcontextprotocol/sdk/server/stdio.js'),
  loadFrontendModule('@modelcontextprotocol/sdk/server/express.js'),
  loadFrontendModule('@modelcontextprotocol/sdk/types.js'),
  loadFrontendModule('@modelcontextprotocol/ext-apps/server'),
  loadFrontendModule('zod/v4'),
]);

export const PHASE1_SERVER_REF = 'phase1-readonly-fixture';
export const PHASE1_SERVER_INFO = Object.freeze({
  name: 'ink-memory-phase1-readonly-appserver',
  version: '1.0.0',
});
export const PHASE1_PROTOCOL_VERSION = '2026-01-26';
export const PHASE1_TOOL_NAME = 'phase1_read_shared_state';
export const PHASE1_RESOURCE_URI = 'ui://ink-memory/phase1/readonly-state.html';
export const PHASE1_STATE = 'phase1-provider-free-ready';
export const PHASE1_CSP = Object.freeze({
  connectDomains: [],
  resourceDomains: [],
  frameDomains: [],
  baseUriDomains: [],
});

export const PHASE1_APP_HTML = String.raw`<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Phase 1 read-only state</title></head>
<body>
  <main id="phase1-app" data-ready="false">
    <h2>Ink &amp; Memory read-only status</h2>
    <output id="phase1-result">Waiting for the saved tool result.</output>
  </main>
  <script>
    (() => {
      const root = document.getElementById('phase1-app');
      const output = document.getElementById('phase1-result');
      const send = (message) => parent.postMessage(message, '*');
      window.addEventListener('message', (event) => {
        const message = event.data;
        if (!message || message.jsonrpc !== '2.0') return;
        if (message.id === 1 && message.result) {
          root.dataset.ready = 'true';
          send({ jsonrpc: '2.0', method: 'ui/notifications/initialized', params: {} });
          return;
        }
        if (message.method === 'ui/notifications/tool-result') {
          output.textContent = message.params?.structuredContent?.state ?? 'Unavailable';
          return;
        }
        if (message.method === 'ui/resource-teardown' && message.id !== undefined) {
          send({ jsonrpc: '2.0', id: message.id, result: {} });
        }
      });
      send({
        jsonrpc: '2.0',
        id: 1,
        method: 'ui/initialize',
        params: {
          protocolVersion: '${PHASE1_PROTOCOL_VERSION}',
          appInfo: { name: 'ink-memory-phase1-readonly-app', version: '1.0.0' },
          appCapabilities: {},
        },
      });
    })();
  </script>
</body>
</html>`;

export function createPhase1State() {
  return {
    originatingToolCalls: 0,
    resourceReads: 0,
    methods: [],
    initializedSessions: [],
  };
}

export function expectedPhase1ToolResult(callCount = 1) {
  return {
    content: [{ type: 'text', text: `Read-only state: ${PHASE1_STATE}` }],
    structuredContent: {
      state: PHASE1_STATE,
      source: 'repo-owned-appserver',
      callCount,
    },
    _meta: {
      ui: {
        resourceUri: PHASE1_RESOURCE_URI,
        serverRef: PHASE1_SERVER_REF,
      },
    },
    isError: false,
  };
}

export function createPhase1McpServer(state = createPhase1State()) {
  const server = new McpServer(
    PHASE1_SERVER_INFO,
    {
      capabilities: {
        tools: {},
        resources: {},
        extensions: {
          'io.modelcontextprotocol/ui': {
            mimeTypes: [RESOURCE_MIME_TYPE],
          },
        },
      },
    },
  );

  registerAppTool(
    server,
    PHASE1_TOOL_NAME,
    {
      title: 'Read shared Phase 1 state',
      description: 'Returns deterministic provider-free read-only state.',
      inputSchema: { request: z.string().optional() },
      _meta: {
        ui: {
          resourceUri: PHASE1_RESOURCE_URI,
          visibility: ['model'],
        },
      },
    },
    async () => {
      state.originatingToolCalls += 1;
      return expectedPhase1ToolResult(state.originatingToolCalls);
    },
  );

  registerAppResource(
    server,
    'Ink & Memory Phase 1 read-only App',
    PHASE1_RESOURCE_URI,
    {
      description: 'Provider-free read-only MCP App HTML.',
      _meta: {
        ui: {
          csp: PHASE1_CSP,
          permissions: {},
        },
      },
    },
    async () => {
      state.resourceReads += 1;
      return {
        contents: [{
          uri: PHASE1_RESOURCE_URI,
          mimeType: RESOURCE_MIME_TYPE,
          text: PHASE1_APP_HTML,
          _meta: {
            ui: {
              csp: PHASE1_CSP,
              permissions: {},
            },
          },
        }],
      };
    },
  );

  return { server, state };
}

export async function runPhase1StdioServer() {
  const { server } = createPhase1McpServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
  const close = async () => {
    await server.close();
  };
  process.once('SIGINT', () => void close().finally(() => process.exit(0)));
  process.once('SIGTERM', () => void close().finally(() => process.exit(0)));
  return { server, transport, close };
}

export async function startPhase1HttpServer({
  host = '127.0.0.1',
  state = createPhase1State(),
} = {}) {
  const app = createMcpExpressApp();
  const transports = new Map();
  const servers = new Set();

  app.all('/mcp', async (request, response) => {
    try {
      if (request.body?.method) state.methods.push(request.body.method);
      const sessionId = request.headers['mcp-session-id'];
      let transport = sessionId ? transports.get(sessionId) : undefined;
      if (!transport && request.method === 'POST' && isInitializeRequest(request.body)) {
        transport = new StreamableHTTPServerTransport({
          sessionIdGenerator: () => randomUUID(),
          enableJsonResponse: true,
          onsessioninitialized: (newSessionId) => {
            state.initializedSessions.push(newSessionId);
            transports.set(newSessionId, transport);
          },
        });
        transport.onclose = () => {
          if (transport.sessionId) transports.delete(transport.sessionId);
        };
        const created = createPhase1McpServer(state);
        servers.add(created.server);
        await created.server.connect(transport);
      }
      if (!transport) {
        response.status(400).json({
          jsonrpc: '2.0',
          id: null,
          error: { code: -32000, message: 'Missing or invalid MCP session.' },
        });
        return;
      }
      await transport.handleRequest(request, response, request.body);
    } catch {
      if (!response.headersSent) {
        response.status(500).json({
          jsonrpc: '2.0',
          id: null,
          error: { code: -32603, message: 'Isolated fixture failure.' },
        });
      }
    }
  });

  const listener = await new Promise((resolve, reject) => {
    const pending = app.listen(0, host, () => resolve(pending));
    pending.once('error', reject);
  });
  const address = listener.address();
  if (address === null || typeof address === 'string') {
    throw new Error('Could not resolve Phase 1 fixture address.');
  }
  return {
    endpointUrl: `http://${host}:${address.port}/mcp`,
    state,
    async close() {
      await Promise.allSettled([
        ...[...transports.values()].map((transport) => transport.close()),
        ...[...servers].map((server) => server.close()),
      ]);
      await new Promise((resolve, reject) => listener.close((error) => (
        error ? reject(error) : resolve()
      )));
    },
  };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await runPhase1StdioServer();
}
