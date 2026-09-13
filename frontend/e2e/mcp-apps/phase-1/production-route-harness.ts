// [Input] Test-owned Vite origins plus production Next Route Handler modules and Browser components.
// [Output] One frontend-origin HTTP adaptation for the real Runtime and CSP-isolated production sandbox route.
// [Pos] Provider-free Phase 1-3 transport harness; the server-only alias only emulates Next's compile guard.
// [Sync] 2026-09-06: adapt exact production routes and suppress only normal cancelled long-poll requests in Vite.
// [Sync] 2026-09-13: serve the production sandbox from the current frontend entry without a separate listener.

import { createServer as createViteServer, type ViteDevServer } from 'vite';


const HOP_BY_HOP_HEADERS = new Set([
  'connection',
  'content-length',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailer',
  'transfer-encoding',
  'upgrade',
]);


async function readBody(request: import('node:http').IncomingMessage): Promise<Buffer> {
  const chunks: Buffer[] = [];
  for await (const chunk of request) chunks.push(Buffer.from(chunk));
  return Buffer.concat(chunks);
}


async function toWebRequest(
  request: import('node:http').IncomingMessage,
  origin: string,
): Promise<Request> {
  const headers = new Headers();
  for (const [name, value] of Object.entries(request.headers)) {
    if (value === undefined || name.toLowerCase() === 'host') continue;
    headers.set(name, Array.isArray(value) ? value.join(', ') : value);
  }
  const method = request.method ?? 'GET';
  const body = method === 'GET' || method === 'HEAD' ? undefined : await readBody(request);
  return new Request(new URL(request.url ?? '/', origin), {
    method,
    headers,
    body,
  });
}


async function writeWebResponse(
  source: Response,
  target: import('node:http').ServerResponse,
): Promise<void> {
  target.statusCode = source.status;
  for (const [name, value] of source.headers) {
    if (!HOP_BY_HOP_HEADERS.has(name.toLowerCase())) target.setHeader(name, value);
  }
  target.end(Buffer.from(await source.arrayBuffer()));
}


function isCancelledLongPoll(error: unknown): boolean {
  return error instanceof Error
    && (error.name === 'AbortError' || error.message === 'aborted');
}


function routeHarnessPlugin(
  origin: string,
  browserConfig?: Record<string, unknown>,
) {
  return {
    name: 'mcp-apps-production-route-harness',
    enforce: 'pre' as const,
    resolveId(id: string) {
      // Next aliases this marker during its server build. The test keeps the
      // production module server-side and emulates only that compile guard.
      if (id === 'server-only') return '\0mcp-apps-server-only';
      return null;
    },
    load(id: string) {
      if (id === '\0mcp-apps-server-only') return 'export {}';
      return null;
    },
    configureServer(server: ViteDevServer) {
      server.middlewares.use(async (request, response, next) => {
        try {
          const url = new URL(request.url ?? '/', origin);
          if (url.pathname === '/mcp-apps-sandbox') {
            const route = await server.ssrLoadModule('/app/mcp-apps-sandbox/route.ts');
            await writeWebResponse(await route.GET(await toWebRequest(request, origin)), response);
            return;
          }
          if (url.pathname === '/api/mcp-apps/phase1-status') {
            const route = await server.ssrLoadModule('/app/api/mcp-apps/phase1-status/route.ts');
            await writeWebResponse(await route.GET(await toWebRequest(request, origin)), response);
            return;
          }
          const match = /^\/api\/mcp-apps\/([^/?]+)$/.exec(url.pathname);
          if (match) {
            const route = await server.ssrLoadModule('/app/api/mcp-apps/[serverRef]/route.ts');
            const handler = route[request.method ?? 'GET'];
            if (typeof handler !== 'function') {
              response.statusCode = 405;
              response.end();
              return;
            }
            await writeWebResponse(await handler(
              await toWebRequest(request, origin),
              { params: Promise.resolve({ serverRef: decodeURIComponent(match[1]!) }) },
            ), response);
            return;
          }
          if (url.pathname === '/mcp-apps-official-harness') {
            const html = await server.transformIndexHtml(url.pathname, `<!doctype html>
              <html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"></head>
              <body><div id="root"></div>
              <script>window.__MCP_APPS_E2E_CONFIG__ = ${JSON.stringify(browserConfig).replaceAll('<', '\\u003c')};</script>
              <script type="module" src="/e2e/mcp-apps/phase-1/official-tool-message-harness.tsx"></script>
              </body></html>`);
            response.statusCode = 200;
            response.setHeader('content-type', 'text/html; charset=utf-8');
            response.setHeader('cache-control', 'no-store');
            response.end(html);
            return;
          }
          next();
        } catch (error) {
          if (isCancelledLongPoll(error)) {
            if (!response.writableEnded && !response.destroyed) response.end();
            return;
          }
          next(error as Error);
        }
      });
    },
  };
}


export async function startProductionRouteHarness({
  frontendRoot,
  hostPort,
  browserConfig,
}: Readonly<{
  frontendRoot: string;
  hostPort: number;
  browserConfig: Record<string, unknown>;
}>) {
  const hostOrigin = `http://127.0.0.1:${hostPort}`;
  const host = await createViteServer({
    root: frontendRoot,
    configFile: false,
    logLevel: 'silent',
    ssr: { noExternal: ['@ink-dream/mcp-apps-runtime', 'server-only'] },
    server: { host: '127.0.0.1', port: hostPort, strictPort: true, hmr: false },
    plugins: [routeHarnessPlugin(hostOrigin, browserConfig)],
  });
  try {
    await host.listen();
  } catch (error) {
    await host.close();
    throw error;
  }
  return {
    host,
    hostOrigin,
    async closeRuntime() {
      const runtime = await host.ssrLoadModule('/packages/mcp-apps-runtime/src/index.ts');
      await runtime.closeMcpAppsRuntime();
    },
    async close() {
      await host.close();
    },
  };
}
