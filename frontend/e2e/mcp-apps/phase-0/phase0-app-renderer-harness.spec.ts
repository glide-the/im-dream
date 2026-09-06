// [Input] Exact MCP packages, named isolated server, DEC-002 Host adapter, and sandbox proxy.
// [Output] Browser evidence for P0-02/P0-03/P0-07 plus positive/negative P0-04 enforcement.
// [Pos] Provider-free task_301 Playwright lane using local Chrome only; no production API or data.
// [Sync] 2026-09-04: rerun P0-04 with revision-bound two-iframe permission probes.
// [Sync] 2026-09-06: remove stale imports/escaping so the retained Phase 0 lane passes root lint.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
import { mkdir, readFile, writeFile } from 'node:fs/promises';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
import { createServer as createNetServer } from 'node:net';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
import { fileURLToPath } from 'node:url';
import { createServer as createViteServer, type ViteDevServer } from 'vite';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { RESOURCE_MIME_TYPE } from '@modelcontextprotocol/ext-apps';
// @ts-expect-error The shared fixture is intentionally plain ESM outside the frontend TypeScript project.
import {
  PHASE0_PERMISSIONS,
  PHASE0_TOOL_NAME,
  createPhase0State,
  expectedPhase0ToolResult,
  startPhase0HttpFixture,
} from '../../../../backend/tests/fixtures/mcp_apps_phase0/phase0_standard_apps_fixture.mjs';
// @ts-expect-error The sandbox server is an isolated Node-side ESM harness helper.
import {
  PHASE0_PROXY_CSP,
  startPhase0SandboxServer,
} from './phase0_sandbox_server.mjs';


test.use({ channel: 'chrome', locale: 'en-US', viewport: { width: 1100, height: 820 } });

const POLICY_REVISION = 'phase0-policy-revision-2';
const SANDBOX_TOKENS = 'allow-scripts allow-same-origin';
const UI_EXTENSION_CAPABILITIES = {
  'io.modelcontextprotocol/ui': { mimeTypes: [RESOURCE_MIME_TYPE] },
};
const GEOLOCATION_ALLOW = "camera 'none'; microphone 'none'; geolocation; clipboard-write 'none'";
const DENY_ALL_ALLOW = "camera 'none'; microphone 'none'; geolocation 'none'; clipboard-write 'none'";

const REPOSITORY_ROOT = fileURLToPath(new URL('../../../../', import.meta.url));
const FRONTEND_ROOT = fileURLToPath(new URL('../../../', import.meta.url));
const EVIDENCE_DIRECTORY = fileURLToPath(
  new URL('../../../../docs/exec/mcp-apps/phase-0/evidence/', import.meta.url),
);

// Provider-free business-impact brief required before browser execution.
// | Fact/surface | Baseline | Expected | Classification |
// | Project/Episode/artifacts | untouched | unchanged | out of scope |
// | Run/Thread/database | absent | absent | out of scope |
// | Synthetic tool call | zero | exactly one upstream call | changes once |
// | Browser network | none | same-origin IM endpoint only | isolated change |
// | Sandbox | absent | separate origin, denied capabilities | isolated change |


async function reserveEphemeralPort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const probe = createNetServer();
    probe.once('error', reject);
    probe.listen(0, '127.0.0.1', () => {
      const address = probe.address();
      if (address === null || typeof address === 'string') {
        probe.close();
        reject(new Error('Could not reserve an isolated browser-harness port.'));
        return;
      }
      probe.close((error?: Error) => (error ? reject(error) : resolve(address.port)));
    });
  });
}


test('Host adapter grants only requested geolocation and preserves the standard Apps loop', async ({ page }) => {
  test.setTimeout(45_000);
  const hostPort = await reserveEphemeralPort();
  const hostOrigin = `http://127.0.0.1:${hostPort}`;
  const sandbox = await startPhase0SandboxServer({
    effectivePermissions: PHASE0_PERMISSIONS,
    revision: POLICY_REVISION,
    sandboxTokens: SANDBOX_TOKENS,
  });
  const fixtureState = createPhase0State();
  const fixture = await startPhase0HttpFixture({
    allowedOrigin: hostOrigin,
    state: fixtureState,
  });
  let vite: ViteDevServer | null = null;

  const agentClient = new Client(
    { name: 'phase0-agent-call-simulator', version: '1.0.0' },
    { capabilities: { extensions: UI_EXTENSION_CAPABILITIES } },
  );
  await agentClient.connect(
    new StreamableHTTPClientTransport(new URL(fixture.upstreamEndpointUrl)),
  );
  const initialResult = await agentClient.callTool({
    name: PHASE0_TOOL_NAME,
    arguments: { request: 'read shared state' },
  });
  await agentClient.close();
  expect(initialResult).toEqual(expectedPhase0ToolResult('shared-state-v1'));
  expect(fixtureState.originatingToolCalls).toBe(1);
  const methodBaseline = fixtureState.methods.length;

  const config = {
    endpointUrl: `${hostOrigin}/phase0/im/mcp`,
    sandboxUrl: sandbox.proxyUrl,
    sandboxTokens: SANDBOX_TOKENS,
    permissionPolicy: {
      revision: POLICY_REVISION,
      desired: PHASE0_PERMISSIONS,
    },
    toolName: PHASE0_TOOL_NAME,
    toolInput: { request: 'read shared state' },
    toolResult: initialResult,
  };

  try {
    vite = await createViteServer({
      root: FRONTEND_ROOT,
      configFile: false,
      logLevel: 'silent',
      server: {
        host: '127.0.0.1',
        port: hostPort,
        strictPort: true,
        proxy: {
          '/phase0/im/mcp': {
            target: fixture.baseUrl,
            changeOrigin: false,
          },
        },
      },
      plugins: [{
        name: 'phase0-app-renderer-harness',
        configureServer(server) {
          server.middlewares.use(async (request, response, next) => {
            if (request.url !== '/phase0-app-renderer-harness') return next();
            try {
              const html = await server.transformIndexHtml(request.url, `<!doctype html>
                <html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"></head>
                <body><div id="root"></div>
                <script>window.__PHASE0_CONFIG__ = ${JSON.stringify(config)};</script>
                <script type="module" src="/e2e/mcp-apps/phase-0/phase0-app-renderer-harness.tsx"></script>
                </body></html>`);
              response.statusCode = 200;
              response.setHeader('Content-Type', 'text/html; charset=utf-8');
              response.end(html);
            } catch (error) {
              next(error as Error);
            }
          });
        },
      }],
    });
    await vite.listen();

    const browserMcpRequests: Array<{ url: string; postData: string | null }> = [];
    const unexpectedDiagnostics: string[] = [];
    let sandboxCspHeader: string | undefined;
    let sandboxPermissionsPolicy: string | undefined;
    page.on('request', (request) => {
      if (new URL(request.url()).pathname === '/phase0/im/mcp') {
        browserMcpRequests.push({ url: request.url(), postData: request.postData() });
      }
    });
    page.on('response', (response) => {
      if (new URL(response.url()).pathname === '/phase0/sandbox-proxy.html') {
        sandboxCspHeader = response.headers()['content-security-policy'];
        sandboxPermissionsPolicy = response.headers()['permissions-policy'];
      }
    });
    page.on('console', (message) => {
      if (message.type() !== 'error') return;
      const text = message.text();
      if (
        text.includes('Content Security Policy')
        || text.includes('Permissions policy')
        || text.includes('Geolocation')
        || text.includes('phase0-forbidden.invalid')
      ) return;
      unexpectedDiagnostics.push(text);
    });
    page.on('pageerror', (error) => unexpectedDiagnostics.push(error.message));
    page.on('requestfailed', (request) => {
      if (request.url().startsWith('https://phase0-forbidden.invalid/')) return;
      const failedPath = new URL(request.url()).pathname;
      if (
        request.failure()?.errorText === 'net::ERR_ABORTED'
        && (failedPath === '/phase0/im/mcp' || failedPath === '/phase0/proxy-evidence')
      ) return;
      unexpectedDiagnostics.push(`${request.failure()?.errorText ?? 'failed'} ${request.url()}`);
    });

    await page.context().setGeolocation({ latitude: 31.2304, longitude: 121.4737 });
    await page.context().grantPermissions(['geolocation'], { origin: hostOrigin });
    await page.context().grantPermissions(['geolocation'], { origin: sandbox.origin });
    await page.goto(`${hostOrigin}/phase0-app-renderer-harness`);
    await expect(page.getByTestId('connection-state')).toHaveText('connected');
    await expect.poll(async () => page.evaluate(() => window.phase0Harness.logs)).toEqual(
      expect.arrayContaining([
        'initialized',
        'parent_dom=denied',
        'network=blocked',
        'tool_result=received',
        'host_permissions=geolocation',
        'geolocation=granted',
      ]),
    );
    await expect.poll(async () => page.evaluate(() => window.phase0Harness.logs)).toEqual(
      expect.arrayContaining([expect.stringMatching(/^camera=(denied|unavailable)$/)]),
    );

    const browserMethods = fixtureState.methods.slice(methodBaseline);
    expect(browserMethods).toEqual(expect.arrayContaining([
      'initialize',
      'tools/list',
      'resources/read',
    ]));
    expect(fixtureState.originatingToolCalls).toBe(1);
    expect(fixtureState.resourceReads).toBe(1);
    expect(fixtureState.proxyForwardedToolCalls).toBe(0);
    expect(fixtureState.proxyForwardedResourceReads).toBe(1);
    expect(new Set(browserMcpRequests.map((entry) => new URL(entry.url).pathname))).toEqual(
      new Set(['/phase0/im/mcp']),
    );
    expect(browserMcpRequests.length).toBeGreaterThanOrEqual(3);
    expect(browserMcpRequests.every((entry) => entry.url.startsWith(hostOrigin))).toBe(true);
    expect(browserMcpRequests.some((entry) => (
      new URL(entry.url).pathname === '/phase0/upstream/mcp'
    ))).toBe(false);
    expect(browserMcpRequests.map((entry) => `${entry.url}\n${entry.postData ?? ''}`).join('\n'))
      .not.toMatch(/authorization|bearer |credential|stdio_command|upstream_url/i);
    expect(browserMcpRequests.some((entry) => entry.url.startsWith('ui://'))).toBe(false);

    const rendererFrame = page.getByTestId('im-mcp-app-host-frame');
    await expect(rendererFrame).toHaveAttribute('sandbox', SANDBOX_TOKENS);
    await expect(rendererFrame).toHaveAttribute('allow', GEOLOCATION_ALLOW);
    expect(new URL(await rendererFrame.getAttribute('src') ?? '').origin).toBe(sandbox.origin);
    expect(sandbox.origin).not.toBe(hostOrigin);
    expect(sandboxCspHeader).toBe(PHASE0_PROXY_CSP);
    expect(sandboxPermissionsPolicy).toBe(sandbox.permissionsPolicy);
    expect(sandboxPermissionsPolicy).toBe(
      'camera=(), microphone=(), geolocation=(self), clipboard-write=()',
    );
    const innerFrame = rendererFrame.contentFrame().locator('iframe');
    await expect(innerFrame).toHaveAttribute('sandbox', SANDBOX_TOKENS);
    await expect(innerFrame).toHaveAttribute('allow', GEOLOCATION_ALLOW);
    await expect.poll(() => sandbox.evidence).toEqual(expect.arrayContaining([
      expect.objectContaining({
        kind: 'resource-ready',
        cspPresent: true,
        permissionsPresent: true,
        sandboxOverridePresent: true,
        requestedPermissions: ['geolocation'],
        effectivePermissions: ['geolocation'],
        revision: POLICY_REVISION,
        innerAllow: GEOLOCATION_ALLOW,
        sandboxTokens: SANDBOX_TOKENS,
      }),
    ]));
    expect(await page.evaluate(() => window.phase0Harness.policyEvidence)).toEqual({
      requestedPermissions: ['geolocation'],
      effectivePermissions: ['geolocation'],
      policyRevision: POLICY_REVISION,
      outerAllow: GEOLOCATION_ALLOW,
      sandboxTokens: SANDBOX_TOKENS,
      hostCapabilitiesPermissions: ['geolocation'],
    });

    await page.evaluate(() => {
      window.postMessage({
        jsonrpc: '2.0',
        id: 'forged-call',
        method: 'tools/call',
        params: { name: 'phase0_show_shared_state', arguments: {} },
      }, '*');
      window.postMessage({ jsonrpc: '2.0', id: 'bad-schema' }, '*');
      const proxyWindow = document.querySelector('iframe')?.contentWindow;
      proxyWindow?.postMessage({ phase0: 'invalid-jsonrpc-schema' }, '*');
      proxyWindow?.postMessage({
        jsonrpc: '2.0',
        method: 'ui/notifications/sandbox-resource-ready',
        params: {
          html: '<p>forged</p>',
          sandbox: 'allow-scripts allow-same-origin allow-forms',
          csp: {},
          permissions: { camera: {} },
        },
      }, '*');
      const foreignFrame = document.createElement('iframe');
      foreignFrame.dataset.phase0Intruder = 'true';
      foreignFrame.srcdoc = `<script>
        parent.document.querySelector('iframe').contentWindow.postMessage({
          jsonrpc: '2.0', id: 'foreign-source', method: 'tools/call', params: {}
        }, '*');
      </script>`;
      document.body.appendChild(foreignFrame);
    });
    await page.waitForTimeout(150);
    expect(fixtureState.originatingToolCalls).toBe(1);
    expect(sandbox.evidence).toEqual(expect.arrayContaining([
      expect.objectContaining({ kind: 'rejected-schema' }),
      expect.objectContaining({ kind: 'rejected-message-source' }),
      expect.objectContaining({ kind: 'rejected-policy-mismatch', revision: POLICY_REVISION }),
    ]));
    await expect(innerFrame).toHaveAttribute('sandbox', SANDBOX_TOKENS);
    await expect(innerFrame).toHaveAttribute('allow', GEOLOCATION_ALLOW);
    await page.locator('iframe[data-phase0-intruder="true"]').evaluateAll((frames) => {
      frames.forEach((frame) => frame.remove());
    });

    await mkdir(EVIDENCE_DIRECTORY, { recursive: true });
    await page.getByRole('button', { name: 'Close isolated app' }).click();
    await expect.poll(async () => page.evaluate(() => window.phase0Harness.logs)).toEqual(
      expect.arrayContaining(['teardown=received']),
    );
    await expect.poll(() => sandbox.evidence).toEqual(expect.arrayContaining([
      expect.objectContaining({ kind: 'teardown-request-forwarded' }),
    ]));
    await expect(page.locator('iframe')).toHaveCount(0);
    expect(await page.evaluate(() => window.phase0Harness.closed)).toBe(true);
    expect(await page.evaluate(() => window.phase0Harness.errors)).toEqual([]);
    expect(unexpectedDiagnostics).toEqual([]);
    expect(fixtureState.originatingToolCalls).toBe(1);
    await writeFile(
      `${EVIDENCE_DIRECTORY}/p0-02-p0-04-browser-trace.json`,
      `${JSON.stringify({
        schemaVersion: 1,
        serverRef: 'phase0-standard-apps-fixture',
        browserEndpointPaths: [...new Set(browserMcpRequests.map(
          (entry) => new URL(entry.url).pathname,
        ))],
        browserMethods,
        originatingToolCalls: fixtureState.originatingToolCalls,
        proxyForwardedToolCalls: fixtureState.proxyForwardedToolCalls,
        resourceReads: fixtureState.resourceReads,
        sandboxEvidenceKinds: sandbox.evidence.map((entry) => entry.kind),
        separateOrigin: true,
        cspHeaderMatched: sandboxCspHeader === PHASE0_PROXY_CSP,
        requestedPermissions: ['geolocation'],
        effectivePermissions: ['geolocation'],
        policyRevision: POLICY_REVISION,
        outerAllow: GEOLOCATION_ALLOW,
        innerAllow: GEOLOCATION_ALLOW,
        permissionsPolicy: sandboxPermissionsPolicy,
        probes: {
          geolocation: 'granted',
          camera: 'denied-or-unavailable',
          forgedPolicyMessage: 'rejected',
          foreignSource: 'rejected',
        },
        appPermissionsPropagated: true,
        appSandboxOverridePropagated: true,
        parentDomAccess: 'denied',
        externalNetwork: 'blocked',
        teardown: 'received-and-frame-removed',
      }, null, 2)}\n`,
      'utf8',
    );
  } finally {
    await vite?.close();
    await fixture.close();
    await sandbox.close();
  }
});

test('Host adapter denies missing/ungranted permissions and rejects invalid metadata', async ({ page }) => {
  test.setTimeout(60_000);
  const scenarios = [
    {
      name: 'no-permissions',
      resourcePermissions: PHASE0_PERMISSIONS,
      omitResourcePermissions: true,
      desired: undefined,
      expectedStatus: 'ready',
      expectedResourceReads: 1,
      error: null,
    },
    {
      name: 'ungranted-camera',
      resourcePermissions: { camera: {} },
      omitResourcePermissions: false,
      desired: PHASE0_PERMISSIONS,
      expectedStatus: 'ready',
      expectedResourceReads: 1,
      error: null,
    },
    {
      name: 'invalid-metadata',
      resourcePermissions: { geolocation: true },
      omitResourcePermissions: false,
      desired: PHASE0_PERMISSIONS,
      expectedStatus: 'degraded',
      expectedResourceReads: 1,
      error: /invalid permission structure|metadata is invalid/i,
    },
    {
      name: 'unknown-permission',
      resourcePermissions: { geolocation: {}, usb: {} },
      omitResourcePermissions: false,
      desired: PHASE0_PERMISSIONS,
      expectedStatus: 'degraded',
      expectedResourceReads: 1,
      error: /unknown permission key/i,
    },
    {
      name: 'invalid-desired-policy',
      resourcePermissions: PHASE0_PERMISSIONS,
      omitResourcePermissions: false,
      desired: { geolocation: true },
      expectedStatus: 'degraded',
      expectedResourceReads: 0,
      error: /invalid permission structure/i,
    },
  ];

  for (const scenario of scenarios) {
    const hostPort = await reserveEphemeralPort();
    const hostOrigin = `http://127.0.0.1:${hostPort}`;
    const revision = `${POLICY_REVISION}-${scenario.name}`;
    const sandbox = await startPhase0SandboxServer({
      effectivePermissions: {},
      revision,
      sandboxTokens: SANDBOX_TOKENS,
    });
    const fixtureState = createPhase0State();
    const fixture = await startPhase0HttpFixture({
      allowedOrigin: hostOrigin,
      state: fixtureState,
      resourcePermissions: scenario.resourcePermissions,
      omitResourcePermissions: scenario.omitResourcePermissions,
    });
    const config = {
      endpointUrl: `${hostOrigin}/phase0/im/mcp`,
      sandboxUrl: sandbox.proxyUrl,
      sandboxTokens: SANDBOX_TOKENS,
      permissionPolicy: { revision, desired: scenario.desired },
      toolName: PHASE0_TOOL_NAME,
      toolInput: { request: 'read shared state' },
      toolResult: expectedPhase0ToolResult('shared-state-v1'),
    };
    let vite: ViteDevServer | null = null;
    try {
      vite = await createViteServer({
        root: FRONTEND_ROOT,
        configFile: false,
        logLevel: 'silent',
        server: {
          host: '127.0.0.1',
          port: hostPort,
          strictPort: true,
          proxy: {
            '/phase0/im/mcp': { target: fixture.baseUrl, changeOrigin: false },
          },
        },
        plugins: [{
          name: `phase0-permission-${scenario.name}`,
          configureServer(server) {
            server.middlewares.use(async (request, response, next) => {
              if (request.url !== '/phase0-app-renderer-harness') return next();
              try {
                const html = await server.transformIndexHtml(request.url, `<!doctype html>
                  <html><body><div id="root"></div>
                  <script>window.__PHASE0_CONFIG__ = ${JSON.stringify(config)};</script>
                  <script type="module" src="/e2e/mcp-apps/phase-0/phase0-app-renderer-harness.tsx"></script>
                  </body></html>`);
                response.statusCode = 200;
                response.setHeader('Content-Type', 'text/html; charset=utf-8');
                response.end(html);
              } catch (error) {
                next(error as Error);
              }
            });
          },
        }],
      });
      await vite.listen();
      await page.goto(`${hostOrigin}/phase0-app-renderer-harness`);
      await expect(page.getByTestId('connection-state')).toHaveText('connected');
      await expect(page.getByTestId('im-mcp-app-host')).toHaveAttribute(
        'data-status',
        scenario.expectedStatus,
      );
      expect(fixtureState.resourceReads).toBe(scenario.expectedResourceReads);
      expect(fixtureState.proxyForwardedToolCalls).toBe(0);

      if (scenario.expectedStatus === 'ready') {
        const outer = page.getByTestId('im-mcp-app-host-frame');
        await expect(outer).toHaveAttribute('allow', DENY_ALL_ALLOW);
        await expect(outer.contentFrame().locator('iframe')).toHaveAttribute('allow', DENY_ALL_ALLOW);
        await expect.poll(async () => page.evaluate(() => window.phase0Harness.logs)).toEqual(
          expect.arrayContaining([
            'host_permissions=',
            expect.stringMatching(/^geolocation=(denied|unavailable)$/),
            expect.stringMatching(/^camera=(denied|unavailable)$/),
          ]),
        );
        expect(await page.evaluate(() => window.phase0Harness.errors)).toEqual([]);
      } else {
        await expect(page.getByTestId('im-mcp-app-host-frame')).toHaveCount(0);
        const errors = await page.evaluate(() => window.phase0Harness.errors);
        expect(errors.join('\n')).toMatch(scenario.error as RegExp);
      }
    } finally {
      await vite?.close();
      await fixture.close();
      await sandbox.close();
    }
  }

  const tracePath = `${EVIDENCE_DIRECTORY}/p0-02-p0-04-browser-trace.json`;
  const trace = JSON.parse(await readFile(tracePath, 'utf8'));
  trace.probes = {
    ...trace.probes,
    noPermissions: 'denied',
    ungrantedCamera: 'denied-or-unavailable',
    invalidMetadata: 'degraded',
    unknownPermission: 'degraded',
    invalidDesiredPolicy: 'degraded',
  };
  await writeFile(tracePath, `${JSON.stringify(trace, null, 2)}\n`, 'utf8');
});

test('test source path stays inside the repository evidence boundary', () => {
  expect(REPOSITORY_ROOT.endsWith('ink-dream-memory/')).toBe(true);
  expect(EVIDENCE_DIRECTORY.startsWith(REPOSITORY_ROOT)).toBe(true);
});

test('existing hydration preserves the complete Apps result after refresh', async ({ page }) => {
  const calls: string[] = [];
  const diagnostics: string[] = [];
  const hostPort = await reserveEphemeralPort();
  const hostOrigin = `http://127.0.0.1:${hostPort}`;
  let vite: ViteDevServer | null = null;
  const toolInvocation = {
    serverRef: 'server-ref-phase0',
    toolName: 'phase0_show_shared_state',
    toolCallId: 'tool-call-phase0-1',
    input: { request: 'read shared state' },
    result: expectedPhase0ToolResult('shared-state-v1'),
  };

  page.on('pageerror', (error) => diagnostics.push(error.message));
  await page.addInitScript(() => {
    localStorage.setItem('auth_token', 'phase0-isolated-token');
  });
  await page.route('**/api/claude-agent/threads/thread-phase0/**', async (route) => {
    const url = route.request().url();
    calls.push(url);
    if (url.includes('/status')) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
        running: false,
        lifecycle: 'idle',
        turn_count: 1,
        pending_tool_call_ids: [],
        tool_confirmation_observation: 'known',
      }) });
      return;
    }
    if (url.includes('known_latest_message_id=message-phase0')) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
        messages: [],
        next_cursor: null,
        has_more: false,
        latest_message_id: 'message-phase0',
        unchanged: true,
      }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
      thread: { id: 'thread-phase0', title: 'Phase 0 isolated thread' },
      messages: [{
        id: 'message-phase0',
        role: 'assistant',
        parts: [{ type: 'tool-invocation', toolInvocation }],
        metadata: {},
        created_at: '2026-09-04T00:00:00Z',
      }],
      next_cursor: null,
      has_more: false,
      latest_message_id: 'message-phase0',
      unchanged: false,
    }) });
  });

  try {
    vite = await createViteServer({
      root: FRONTEND_ROOT,
      configFile: false,
      logLevel: 'silent',
      server: { host: '127.0.0.1', port: hostPort, strictPort: true },
      plugins: [{
        name: 'phase0-hydration-harness',
        configureServer(server) {
          server.middlewares.use(async (request, response, next) => {
            if (request.url !== '/phase0-hydration-harness') return next();
            const html = await server.transformIndexHtml(request.url, `<!doctype html>
              <html><body><div id="ready">loading</div><script type="module">
                import { hydrateClaudeThreadSession } from '/app/_dream/components/chat/threadSessionHydration.ts';
                window.phase0Hydrated = await hydrateClaudeThreadSession('thread-phase0');
                document.getElementById('ready').textContent = 'ready';
              </script></body></html>`);
            response.statusCode = 200;
            response.setHeader('Content-Type', 'text/html; charset=utf-8');
            response.end(html);
          });
        },
      }],
    });
    await vite.listen();
    await page.goto(`${hostOrigin}/phase0-hydration-harness`);
    await expect(page.locator('#ready')).toHaveText('ready');
    expect(calls.map((url) => new URL(url, 'http://phase0.invalid').pathname)).toEqual([
      '/api/claude-agent/threads/thread-phase0/messages',
      '/api/claude-agent/threads/thread-phase0/status',
      '/api/claude-agent/threads/thread-phase0/messages',
    ]);
    const hydratedPart = await page.evaluate(() => (
      (window as typeof window & {
        phase0Hydrated: { messages: Array<{ parts: unknown[] }> };
      }).phase0Hydrated.messages[0]?.parts[0]
    ));
    expect(hydratedPart).toEqual({
      type: 'tool-invocation',
      toolInvocation,
    });
    expect(diagnostics).toEqual([]);
  } finally {
    await vite?.close();
  }
});
