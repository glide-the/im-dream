// [Input] Explicit official 1.7.5/1.7.4 artifacts, production Browser/Route-Handler/Runtime modules, and isolated policy services.
// [Output] Provider-free Phase 1-3 protocol, UI, security, lifecycle, and compatibility evidence.
// [Pos] Local-Chrome technical lane only; it neither invokes a model nor mutates real Ink & Memory business state.
// [Sync] 2026-09-06: prove Browser teardown sends DELETE and releases server sessions/connectors across lifecycle changes.
// [Sync] 2026-09-06: mount the production Host from the persisted tool-invocation/direct-projection shape.
// [Sync] 2026-09-06: include the connection App-settings revision in every Host policy identity assertion.
// [Sync] 2026-09-06: prove ordinary parent rerenders do not remount the App or discard in-progress App input before ui/message.
// [Sync] 2026-09-06: optionally capture the collapsed-process/visible-App user-guide image from the production tree.

import { expect, test } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { RESOURCE_MIME_TYPE } from '@modelcontextprotocol/ext-apps';

// @ts-expect-error The provider-free process helper is intentionally plain ESM.
import {
  reserveEphemeralPort,
  startAuditedUpstreamRelay,
  startConnectionViewService,
  startOfficialArtifact,
} from './node-harness.mjs';
import { startProductionRouteHarness } from './production-route-harness';


test.use({ channel: 'chrome', locale: 'en-US', viewport: { width: 1100, height: 900 } });
test.describe.configure({ mode: 'serial' });

const FRONTEND_ROOT = fileURLToPath(new URL('../../../', import.meta.url));
const CURRENT_VERSION = '1.7.5';
const PREVIOUS_VERSION = '1.7.4';
const SERVER_REF = 'official-basic-vanillajs';
const WORKSPACE_SCOPE = 'mcp-apps-e2e-workspace';
const TOOL_NAME = 'get-time';
const RESOURCE_URI = 'ui://get-time/mcp-app.html';
const BROWSER_TOKEN = 'mcp-apps-e2e-browser-token';
const BROWSER_AUTHORIZATION = `Bearer ${BROWSER_TOKEN}`;
const SERVICE_TOKEN = 'mcp-apps-e2e-node-service-token';
const UPSTREAM_SECRET = 'mcp-apps-e2e-upstream-only-secret';
const POLICY_REVISION_1 = '1:1:1';
const RUNTIME_POLICY_REVISION_2 = '1:2:1';
const POLICY_REVISION_2 = '2:2:1';
const POLICY_REVISION_3 = '3:3:1';
const POLICY_REVISION_5 = '5:3:1';
const UI_EXTENSION_CAPABILITIES = {
  'io.modelcontextprotocol/ui': { mimeTypes: [RESOURCE_MIME_TYPE] },
};

type RuntimeAdapterProbe = Readonly<{
  diagnostics: () => Readonly<{ sessions: number }>;
  manager: Readonly<{
    diagnostics: () => Readonly<{ connections: number; leases: number }>;
  }>;
}>;

function runtimeCounts(): Readonly<{ sessions: number; connectors: number; leases: number }> {
  const runtime = (globalThis as typeof globalThis & {
    __inkDreamMcpAppsRuntime?: RuntimeAdapterProbe;
  }).__inkDreamMcpAppsRuntime;
  return Object.freeze({
    sessions: runtime?.diagnostics().sessions ?? 0,
    connectors: runtime?.manager.diagnostics().connections ?? 0,
    leases: runtime?.manager.diagnostics().leases ?? 0,
  });
}

// Provider-free business-impact brief required before browser execution.
// | Concept/fact | Source of truth | Write/sync owner | Visible consumer | Expected impact |
// | Project/Episode/canonical artifacts | normal Dream data | Agent/Hook | Dream pages | out of scope; absent |
// | Run-private publication/Thread | normal runtime | Agent service | Chat/Dream | out of scope; absent |
// | Initial official tool result | unmodified official AppServer | Node-side simulator | ToolMessagePart + App | changes exactly once |
// | Browser MCP transport | production Next Route/Runtime | Host policy | official App iframe | isolated technical change |
// | Existing Chat ingress | ToolMessagePart sendMessage prop | existing Chat transport | next user turn | one call per ui/message |


function requiredArtifact(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`${name} must explicitly name the prepared official artifact root.`);
  return value;
}


function pluginManifest(
  revision: number,
  lifecycle: 'enabled' | 'disabled' = 'enabled',
) {
  return JSON.stringify({
    manifestVersion: 1,
    pluginId: 'im.mcp-apps-host',
    pluginVersion: '1.0.0',
    revision,
    lifecycle,
    browserEntry: 'frontend/app/_dream/components/chat/mcp-apps/McpAppHostPanel.tsx',
    nodeEntry: '@ink-dream/mcp-apps-runtime',
    protocol: { minimum: '2026-01-26', maximum: '2026-01-26' },
    sdk: {
      mcp: { minimum: '1.30.0', maximum: '1.30.0' },
      extApps: { minimum: '1.7.5', maximum: '1.7.5' },
      mcpUi: { minimum: '7.1.1', maximum: '7.1.1' },
    },
    features: {
      resourceReads: true,
      lowRiskToolCalls: true,
      uiMessage: true,
      windowIm: true,
    },
  });
}


async function connectClient(endpointUrl: string, name: string) {
  const client = new Client(
    { name, version: '1.0.0' },
    { capabilities: { extensions: UI_EXTENSION_CAPABILITIES } },
  );
  await client.connect(new StreamableHTTPClientTransport(new URL(endpointUrl)));
  return client;
}


for (const version of [PREVIOUS_VERSION, CURRENT_VERSION]) {
  test(`official ${version} protocol smoke remains compatible`, async () => {
    const artifact = await startOfficialArtifact({
      artifactRoot: requiredArtifact(
        version === CURRENT_VERSION
          ? 'INK_MCP_APPS_OFFICIAL_ARTIFACT_CURRENT'
          : 'INK_MCP_APPS_OFFICIAL_ARTIFACT_PREVIOUS',
      ),
      expectedVersion: version,
    });
    let client: Client | null = null;
    try {
      client = await connectClient(artifact.endpointUrl, `official-${version}-compatibility`);
      const tools = await client.listTools();
      expect(tools.tools).toEqual(expect.arrayContaining([
        expect.objectContaining({
          name: TOOL_NAME,
          _meta: expect.objectContaining({
            ui: expect.objectContaining({ resourceUri: RESOURCE_URI }),
          }),
        }),
      ]));
      const resources = await client.listResources();
      expect(resources.resources).toEqual(expect.arrayContaining([
        expect.objectContaining({ uri: RESOURCE_URI, mimeType: RESOURCE_MIME_TYPE }),
      ]));
      const resource = await client.readResource({ uri: RESOURCE_URI });
      expect(resource.contents).toHaveLength(1);
      expect(resource.contents[0]).toEqual(expect.objectContaining({
        uri: RESOURCE_URI,
        mimeType: RESOURCE_MIME_TYPE,
        text: expect.stringContaining('Get Server Time'),
      }));
      const result = await client.callTool({ name: TOOL_NAME, arguments: {} });
      expect(result).toEqual(expect.objectContaining({
        structuredContent: { time: expect.stringMatching(/^\d{4}-\d{2}-\d{2}T/) },
      }));
      expect(artifact.manifest.version).toBe(version);
    } finally {
      await client?.close().catch(() => undefined);
      await artifact.close();
    }
  });
}


test('official 1.7.5 renders through production Host, stays isolated, and follows lifecycle policy', async ({ page }) => {
  test.setTimeout(90_000);
  const official = await startOfficialArtifact({
    artifactRoot: requiredArtifact('INK_MCP_APPS_OFFICIAL_ARTIFACT_CURRENT'),
    expectedVersion: CURRENT_VERSION,
  });
  let relay: Awaited<ReturnType<typeof startAuditedUpstreamRelay>> | null = null;
  let connectionView: Awaited<ReturnType<typeof startConnectionViewService>> | null = null;
  let initialClient: Client | null = null;
  let routes: Awaited<ReturnType<typeof startProductionRouteHarness>> | null = null;
  const originalEnvironment = Object.fromEntries([
    'INK_BACKEND_INTERNAL_URL',
    'INK_MCP_APPS_NODE_SERVICE_TOKEN',
    'INK_MCP_APPS_PHASE1_PREVIEW',
    'INK_MCP_APPS_SANDBOX_URL',
    'INK_MCP_APPS_PARENT_ORIGINS',
    'INK_MCP_APPS_HOST_READY_TIMEOUT_MS',
    'INK_MCP_APPS_POLICY_POLL_MS',
    'INK_MCP_APPS_PHASE2_TOOL_CALLS',
    'INK_MCP_APPS_PHASE2_UI_MESSAGE',
    'INK_MCP_APPS_WINDOW_IM',
    'INK_MCP_APPS_WINDOW_IM_REQUEST_TIMEOUT_MS',
    'INK_MCP_APPS_PLUGIN_MANIFEST_JSON',
    'INK_MCP_APPS_MAX_RESOURCE_BYTES',
    'INK_MCP_APPS_MAX_CATALOG_PAGES',
    'INK_MCP_APPS_UPSTREAM_TIMEOUT_MS',
    'INK_MCP_APPS_MAX_CONCURRENCY_PER_SCOPE',
    'INK_MCP_APPS_NETWORK_HOST_ALLOWLIST',
  ].map((name) => [name, process.env[name]]));

  try {
  relay = await startAuditedUpstreamRelay({
    targetEndpointUrl: official.endpointUrl,
    upstreamSecret: UPSTREAM_SECRET,
  });
  connectionView = await startConnectionViewService({
    serverRef: SERVER_REF,
    workspaceScope: WORKSPACE_SCOPE,
    upstreamEndpointUrl: relay.endpointUrl,
    serviceToken: SERVICE_TOKEN,
    browserAuthorization: BROWSER_AUTHORIZATION,
    upstreamSecret: UPSTREAM_SECRET,
  });
  // Node policy permits this low-risk tool from the outset. Browser Phase 1
  // independently withholds tools/call, so a forged App request must still
  // stop before reaching the Runtime or upstream relay.
  connectionView.state.lowRiskToolCalls = true;
  initialClient = await connectClient(relay.endpointUrl, 'mcp-apps-e2e-initial-tool-call');
  const initialResult = await initialClient.callTool({ name: TOOL_NAME, arguments: {} });
  await initialClient.close();
  initialClient = null;
  expect(initialResult).toEqual(expect.objectContaining({
    structuredContent: { time: expect.stringMatching(/^\d{4}-\d{2}-\d{2}T/) },
  }));
  expect(relay.methods.filter((method: string) => method === 'tools/call')).toHaveLength(1);
  const initialTime = (initialResult.structuredContent as { time: string }).time;

  const hostPort = await reserveEphemeralPort();
  const sandboxPort = await reserveEphemeralPort();
  const hostOrigin = `http://127.0.0.1:${hostPort}`;
  const sandboxOrigin = `http://127.0.0.1:${sandboxPort}`;
  Object.assign(process.env, {
    INK_BACKEND_INTERNAL_URL: connectionView.origin,
    INK_MCP_APPS_NODE_SERVICE_TOKEN: SERVICE_TOKEN,
    INK_MCP_APPS_PHASE1_PREVIEW: 'true',
    INK_MCP_APPS_SANDBOX_URL: `${sandboxOrigin}/mcp-apps-sandbox`,
    INK_MCP_APPS_PARENT_ORIGINS: hostOrigin,
    INK_MCP_APPS_HOST_READY_TIMEOUT_MS: '5000',
    INK_MCP_APPS_POLICY_POLL_MS: '100',
    INK_MCP_APPS_PHASE2_TOOL_CALLS: 'false',
    INK_MCP_APPS_PHASE2_UI_MESSAGE: 'true',
    INK_MCP_APPS_WINDOW_IM: 'true',
    INK_MCP_APPS_WINDOW_IM_REQUEST_TIMEOUT_MS: '5000',
    INK_MCP_APPS_PLUGIN_MANIFEST_JSON: pluginManifest(1),
    INK_MCP_APPS_MAX_RESOURCE_BYTES: '4194304',
    INK_MCP_APPS_MAX_CATALOG_PAGES: '8',
    INK_MCP_APPS_UPSTREAM_TIMEOUT_MS: '5000',
    INK_MCP_APPS_MAX_CONCURRENCY_PER_SCOPE: '4',
    INK_MCP_APPS_NETWORK_HOST_ALLOWLIST: '127.0.0.1',
  });
  const toolCallId = 'official-get-time-call-1';
  const input = {};
  const browserConfig = {
    threadId: 'mcp-apps-e2e-thread',
    part: {
      type: 'tool-invocation',
      toolName: `mcp__${SERVER_REF}__${TOOL_NAME}`,
      toolCallId,
      state: 'output-available',
      input,
      output: initialResult,
      mcpAppResult: {
        version: 1,
        serverRef: SERVER_REF,
        toolName: TOOL_NAME,
        toolCallId,
        input,
        workspaceScope: WORKSPACE_SCOPE,
        resourceUri: RESOURCE_URI,
        result: initialResult,
      },
    },
  };
  const browserRequests: Array<{ url: string; method: string; postData: string | null }> = [];
  const browserMcpResponses: Array<{ method: string; status: number }> = [];
  const unexpectedDiagnostics: string[] = [];
  const expectedProbeDiagnostics: string[] = [];
  const expectedLifecycleDiagnostics: string[] = [];
  const expectedSandboxStorageDenials: string[] = [];
  const sandboxHeaders: Record<string, string> = {};
  let pluginDisableActive = false;

    routes = await startProductionRouteHarness({
      frontendRoot: FRONTEND_ROOT,
      hostPort,
      sandboxPort,
      browserConfig,
    });
    await page.addInitScript(
      ({ key, token }) => localStorage.setItem(key, token),
      { key: 'auth_token', token: BROWSER_TOKEN },
    );
    page.on('request', (request) => browserRequests.push({
      url: request.url(),
      method: request.method(),
      postData: request.postData(),
    }));
    page.on('response', (response) => {
      const pathname = new URL(response.url()).pathname;
      if (pathname === `/api/mcp-apps/${SERVER_REF}`) {
        browserMcpResponses.push({
          method: response.request().method(),
          status: response.status(),
        });
      }
      if (pathname === '/mcp-apps-sandbox') Object.assign(sandboxHeaders, response.headers());
    });
    page.on('console', (message) => {
      if (message.type() !== 'error') return;
      const text = message.text();
      const locationUrl = message.location().url;
      if (text.includes('Received a response for an unknown message ID')
        && text.includes('phase1-forged-tool-call')
        && text.includes('Method not found')) {
        expectedProbeDiagnostics.push(`console: ${text}`);
        return;
      }
      if (/Failed to load resource:.*status of (404|409)/.test(text)
        && locationUrl.includes(`/api/mcp-apps/${SERVER_REF}`)) {
        expectedLifecycleDiagnostics.push(`console: ${text}`);
        return;
      }
      if (pluginDisableActive
        && /Failed to load resource:.*status of 503/.test(text)
        && locationUrl.includes(`/api/mcp-apps/${SERVER_REF}`)) {
        expectedLifecycleDiagnostics.push(`console: ${text}`);
        return;
      }
      unexpectedDiagnostics.push(`console: ${text}`);
    });
    page.on('pageerror', (error) => {
      if (error.message === "Failed to read the 'localStorage' property from 'Window': The document is sandboxed and lacks the 'allow-same-origin' flag.") {
        expectedSandboxStorageDenials.push(error.message);
        return;
      }
      unexpectedDiagnostics.push(`pageerror: ${error.message}`);
    });
    page.on('requestfailed', (request) => {
      if (request.failure()?.errorText === 'net::ERR_ABORTED'
        && new URL(request.url()).pathname.startsWith('/api/mcp-apps/')) return;
      unexpectedDiagnostics.push(`requestfailed: ${request.failure()?.errorText ?? 'unknown'} ${request.url()}`);
    });

    await page.goto(`${hostOrigin}/mcp-apps-official-harness`);
    await expect(page.getByRole('heading', { name: 'Official MCP App production-path harness' })).toBeVisible();
    await expect(page.getByTestId('mcp-app-panel')).toHaveAttribute('data-policy-revision', POLICY_REVISION_1);
    await expect.poll(async () => {
      const status = await page.getByTestId('im-mcp-app-host').getAttribute('data-status');
      return status === 'ready' ? status : JSON.stringify({
        status,
        diagnostics: unexpectedDiagnostics,
        sandboxHeaders,
        mcpResponses: browserMcpResponses,
      });
    }).toBe('ready');
    await expect.poll(runtimeCounts).toEqual({ sessions: 1, connectors: 1, leases: 1 });

    const outer = page.getByTestId('im-mcp-app-host-frame');
    await expect(outer).toHaveAttribute('sandbox', 'allow-scripts');
    await expect(outer).toHaveAttribute(
      'allow',
      "camera 'none'; microphone 'none'; geolocation 'none'; clipboard-write 'none'",
    );
    expect(new URL(await outer.getAttribute('src') ?? '').origin).toBe(sandboxOrigin);
    expect(sandboxOrigin).not.toBe(hostOrigin);
    const innerLocator = outer.contentFrame().getByTestId('im-mcp-app-resource-frame');
    await expect(innerLocator).toHaveAttribute('sandbox', 'allow-scripts');
    await expect(innerLocator).toHaveAttribute(
      'allow',
      "camera 'none'; microphone 'none'; geolocation 'none'; clipboard-write 'none'",
    );
    const app = innerLocator.contentFrame();
    await expect(app.getByRole('button', { name: 'Get Server Time' })).toBeVisible();
    await expect(app.locator('#server-time')).toHaveText(initialTime);
    const innerCsp = await app.locator('meta[http-equiv="Content-Security-Policy"]').getAttribute('content');
    expect(innerCsp).toContain("default-src 'none'");
    expect(innerCsp).toContain("connect-src 'none'");
    expect(sandboxHeaders['content-security-policy']).toContain("default-src 'none'");
    expect(sandboxHeaders['permissions-policy']).toBe(
      'camera=(), microphone=(), geolocation=(), clipboard-write=()',
    );

    await page.getByText(`mcp__${SERVER_REF}__${TOOL_NAME}`).click();
    await expect(page.getByText(initialTime, { exact: false })).toBeVisible();
    await expect(page.getByText('Output', { exact: true })).toBeVisible();
    expect(relay.methods.filter((method: string) => method === 'tools/call')).toHaveLength(1);

    const windowIm = await app.locator('body').evaluate(() => {
      const candidate = (window as unknown as { im?: Record<string, unknown> }).im;
      return {
        keys: candidate ? Object.keys(candidate).sort() : [],
        sendFollowUpMessage: typeof candidate?.sendFollowUpMessage,
        callTool: typeof candidate?.callTool,
        openLink: typeof candidate?.openLink,
        requestDisplayMode: typeof candidate?.requestDisplayMode,
        toolInput: candidate?.toolInput,
        toolOutput: candidate?.toolOutput,
        theme: candidate?.theme,
        locale: candidate?.locale,
        displayMode: candidate?.displayMode,
      };
    });
    expect(windowIm.keys).toEqual([
      'displayMode',
      'locale',
      'sendFollowUpMessage',
      'theme',
      'toolInput',
      'toolOutput',
      'toolResponseMetadata',
    ]);
    expect(windowIm).toEqual(expect.objectContaining({
      sendFollowUpMessage: 'function',
      callTool: 'undefined',
      openLink: 'undefined',
      requestDisplayMode: 'undefined',
      toolInput: input,
      toolOutput: initialResult,
      theme: expect.stringMatching(/^(light|dark)$/),
      locale: expect.any(String),
      displayMode: 'inline',
    }));

    const forgedToolResponse = await app.locator('body').evaluate(() => new Promise<unknown>((resolve) => {
      const id = 'phase1-forged-tool-call';
      const timeout = window.setTimeout(() => {
        window.removeEventListener('message', onMessage, true);
        resolve(null);
      }, 1_000);
      const onMessage = (event: MessageEvent) => {
        const data = event.data as { id?: unknown } | null;
        if (!data || data.id !== id) return;
        event.stopImmediatePropagation();
        window.clearTimeout(timeout);
        window.removeEventListener('message', onMessage, true);
        resolve(data);
      };
      window.addEventListener('message', onMessage, true);
      window.parent.postMessage({
        jsonrpc: '2.0',
        id,
        method: 'tools/call',
        params: { name: 'get-time', arguments: {} },
      }, '*');
    }));
    expect(forgedToolResponse).toEqual(expect.objectContaining({
      jsonrpc: '2.0',
      id: 'phase1-forged-tool-call',
      error: expect.any(Object),
    }));
    expect(relay.methods.filter((method: string) => method === 'tools/call')).toHaveLength(1);

    await app.locator('#message-text').fill('Official App message through the existing Chat ingress.');
    await page.getByTestId('mcp-app-parent-rerender').click();
    await expect(app.locator('#message-text')).toHaveValue(
      'Official App message through the existing Chat ingress.',
    );
    await app.getByRole('button', { name: 'Send Message' }).click();
    await expect(page.getByTestId('existing-chat-ingress-count')).toHaveText('1');
    expect(await page.evaluate(() => window.mcpAppsE2e.messages)).toEqual([
      expect.objectContaining({
        role: 'user',
        parts: [{ type: 'text', text: 'Official App message through the existing Chat ingress.' }],
      }),
    ]);
    await app.locator('body').evaluate(async () => {
      const im = (window as unknown as {
        im: { sendFollowUpMessage(input: { prompt: string; scrollToBottom: boolean }): Promise<unknown> };
      }).im;
      await im.sendFollowUpMessage({ prompt: 'window.im follow-up through the same ingress.', scrollToBottom: true });
    });
    await expect(page.getByTestId('existing-chat-ingress-count')).toHaveText('2');
    expect(await page.evaluate(() => window.mcpAppsE2e.sendMessageCalls)).toBe(2);
    expect(relay.methods.filter((method: string) => method === 'tools/call')).toHaveLength(1);

    connectionView.state.policyRevision = 2;
    await expect(page.getByTestId('mcp-app-panel')).toHaveAttribute(
      'data-policy-revision',
      RUNTIME_POLICY_REVISION_2,
    );
    await expect(page.getByTestId('im-mcp-app-host')).toHaveAttribute('data-status', 'ready');
    expect(relay.methods.filter((method: string) => method === 'tools/call')).toHaveLength(1);

    process.env.INK_MCP_APPS_PHASE2_TOOL_CALLS = 'true';
    process.env.INK_MCP_APPS_PLUGIN_MANIFEST_JSON = pluginManifest(2);
    await expect.poll(async () => {
      const response = await fetch(`${hostOrigin}/api/mcp-apps/phase1-status`, { cache: 'no-store' });
      const status = await response.json() as { plugin?: { revision?: number } };
      return status.plugin?.revision;
    }).toBe(2);
    await expect.poll(() => page.evaluate(async () => {
      const response = await fetch('/api/mcp-apps/phase1-status', { cache: 'no-store' });
      const status = await response.json() as { plugin?: { revision?: number } };
      return status.plugin?.revision;
    })).toBe(2);
    await expect.poll(() => browserRequests.filter(
      (request) => new URL(request.url).pathname === '/api/mcp-apps/phase1-status',
    ).length).toBeGreaterThanOrEqual(2);
    await expect.poll(async () => {
      const panel = page.getByTestId('mcp-app-panel');
      if (await panel.count()) return `panel:${await panel.getAttribute('data-policy-revision')}`;
      const fallback = page.getByTestId('mcp-app-fallback');
      if (await fallback.count()) {
        return JSON.stringify({
          state: `fallback:${await fallback.getAttribute('data-diagnostic-stage')}:${await fallback.getAttribute('data-diagnostic-code')}`,
          responses: browserMcpResponses.slice(-8),
        });
      }
      return 'missing';
    }).toBe(`panel:${POLICY_REVISION_2}`);
    await expect(page.getByTestId('im-mcp-app-host')).toHaveAttribute('data-status', 'ready');
    const interactiveApp = page.getByTestId('im-mcp-app-host-frame')
      .contentFrame()
      .getByTestId('im-mcp-app-resource-frame')
      .contentFrame();
    await interactiveApp.getByRole('button', { name: 'Get Server Time' }).click();
    await expect.poll(
      () => relay!.methods.filter((method: string) => method === 'tools/call').length,
    ).toBe(2);
    expect(await page.evaluate(() => window.mcpAppsE2e.sendMessageCalls)).toBe(2);

    const methodsBeforeForgedSource = relay.methods.length;
    await page.evaluate(() => {
      const rogue = document.createElement('iframe');
      rogue.src = 'about:blank';
      document.body.appendChild(rogue);
      const source = `top.document.querySelector('[data-testid="im-mcp-app-host-frame"]')
        .contentWindow.postMessage({jsonrpc:'2.0',method:'resources/read',params:{uri:'ui://forged'}}, '*')`;
      rogue.contentWindow?.eval(source);
      return new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => {
        rogue.remove();
        resolve();
      })));
    });
    await expect(interactiveApp.getByRole('button', { name: 'Get Server Time' })).toBeVisible();
    expect(relay.methods).toHaveLength(methodsBeforeForgedSource);

    await page.screenshot({
      path: 'output/playwright/mcp-apps/official-1.7.5-production-host.png',
      fullPage: true,
    });
    if (process.env.INK_CAPTURE_MCP_APPS_GUIDE === '1') {
      await page.getByText(`mcp__${SERVER_REF}__${TOOL_NAME}`, { exact: true }).click();
      await expect(page.getByText('Output', { exact: true })).toHaveCount(0);
      await page.getByTestId('mcp-app-guide-result').screenshot({
        path: 'output/playwright/mcp-apps-guide/use-mcp-app-in-chat.png',
      });
      await page.getByText(`mcp__${SERVER_REF}__${TOOL_NAME}`, { exact: true }).click();
      await expect(page.getByText('Output', { exact: true })).toBeVisible();
    }

    const deletesBeforeClose = browserMcpResponses.filter(({ method }) => method === 'DELETE').length;
    await page.getByTestId('mcp-app-close').click();
    await expect(page.getByTestId('im-mcp-app-host-frame')).toHaveCount(0);
    await expect(page.getByTestId('mcp-app-reopen')).toBeVisible();
    await expect.poll(() => browserMcpResponses.filter(({ method }) => method === 'DELETE').length)
      .toBe(deletesBeforeClose + 1);
    expect(browserMcpResponses.filter(({ method }) => method === 'DELETE').at(-1)?.status).toBe(200);
    await expect.poll(runtimeCounts).toEqual({ sessions: 0, connectors: 0, leases: 0 });

    await page.getByTestId('mcp-app-reopen').click();
    await expect(page.getByTestId('im-mcp-app-host')).toHaveAttribute('data-status', 'ready');
    await expect.poll(runtimeCounts).toEqual({ sessions: 1, connectors: 1, leases: 1 });
    expect(relay.methods.filter((method: string) => method === 'tools/call')).toHaveLength(2);

    const deletesBeforeThreadSwitch = browserMcpResponses.filter(({ method }) => method === 'DELETE').length;
    await page.evaluate(() => window.mcpAppsE2e.switchThread('mcp-apps-e2e-thread-2'));
    await expect.poll(() => browserMcpResponses.filter(({ method }) => method === 'DELETE').length)
      .toBe(deletesBeforeThreadSwitch + 1);
    await expect(page.getByTestId('im-mcp-app-host')).toHaveAttribute('data-status', 'ready');
    await expect.poll(runtimeCounts).toEqual({ sessions: 1, connectors: 1, leases: 1 });

    await page.reload();
    await expect(page.getByTestId('im-mcp-app-host')).toHaveAttribute('data-status', 'ready');
    const refreshedOuter = page.getByTestId('im-mcp-app-host-frame');
    await expect(refreshedOuter.contentFrame()
      .getByTestId('im-mcp-app-resource-frame')
      .contentFrame()
      .locator('#server-time')).toHaveText(initialTime);
    expect(relay.methods.filter((method: string) => method === 'tools/call')).toHaveLength(2);

    connectionView.state.policyRevision = 3;
    process.env.INK_MCP_APPS_PLUGIN_MANIFEST_JSON = pluginManifest(3);
    await expect.poll(async () => {
      const response = await fetch(`${hostOrigin}/api/mcp-apps/phase1-status`, { cache: 'no-store' });
      const status = await response.json() as { plugin?: { revision?: number } };
      return status.plugin?.revision;
    }).toBe(3);
    await expect(page.getByTestId('mcp-app-panel')).toHaveAttribute(
      'data-policy-revision',
      POLICY_REVISION_3,
    );
    await expect(page.getByTestId('im-mcp-app-host')).toHaveAttribute('data-status', 'ready');
    await expect(page.getByTestId('im-mcp-app-host-frame')).toHaveAttribute(
      'data-policy-revision',
      POLICY_REVISION_3,
    );
    expect(relay.methods.filter((method: string) => method === 'tools/call')).toHaveLength(2);
    const responsesBeforePluginDisable = browserMcpResponses.length;
    const deletesBeforePluginDisable = browserMcpResponses.filter(({ method }) => method === 'DELETE').length;
    pluginDisableActive = true;
    process.env.INK_MCP_APPS_PLUGIN_MANIFEST_JSON = pluginManifest(4, 'disabled');
    await expect(page.getByTestId('mcp-app-fallback')).toBeVisible();
    await expect(page.getByTestId('im-mcp-app-host-frame')).toHaveCount(0);
    await expect.poll(() => browserMcpResponses.filter(({ method }) => method === 'DELETE').length)
      .toBeGreaterThan(deletesBeforePluginDisable);
    await expect.poll(runtimeCounts).toEqual({ sessions: 0, connectors: 0, leases: 0 });
    process.env.INK_MCP_APPS_PLUGIN_MANIFEST_JSON = pluginManifest(5);
    await expect(page.getByTestId('mcp-app-panel')).toHaveAttribute(
      'data-policy-revision',
      POLICY_REVISION_5,
    );
    await expect(page.getByTestId('im-mcp-app-host')).toHaveAttribute('data-status', 'ready');
    await expect.poll(runtimeCounts).toEqual({ sessions: 1, connectors: 1, leases: 1 });
    const pluginDisableResponses = browserMcpResponses.slice(responsesBeforePluginDisable);
    expect(pluginDisableResponses).toEqual(expect.arrayContaining([
      expect.objectContaining({ method: 'DELETE', status: 503 }),
    ]));
    pluginDisableActive = false;

    const allowedOrigins = new Set([hostOrigin, sandboxOrigin]);
    expect(browserRequests.length).toBeGreaterThan(0);
    expect(browserRequests.every((request) => allowedOrigins.has(new URL(request.url).origin))).toBe(true);
    const browserMcpRequests = browserRequests.filter(
      (request) => new URL(request.url).pathname === `/api/mcp-apps/${SERVER_REF}`,
    );
    expect(browserMcpRequests.length).toBeGreaterThanOrEqual(3);
    expect(browserMcpRequests.every((request) => request.url.startsWith(hostOrigin))).toBe(true);
    expect(browserRequests.some((request) => request.url.startsWith(relay.origin))).toBe(false);
    expect(browserRequests.some((request) => request.url.startsWith(official.endpointUrl))).toBe(false);
    expect(JSON.stringify(browserRequests)).not.toContain(UPSTREAM_SECRET);
    expect(JSON.stringify(browserConfig)).not.toContain(UPSTREAM_SECRET);
    expect(await page.locator('body').innerText()).not.toContain(UPSTREAM_SECRET);
    expect(await page.content()).not.toContain(relay.endpointUrl);
    expect(connectionView.requests.length).toBeGreaterThanOrEqual(3);
    expect(connectionView.requests.every((request: { workspaceScope: string | null }) => (
      request.workspaceScope === WORKSPACE_SCOPE
    ))).toBe(true);
    expect(connectionView.requests.some((request: { expectedConfigRevision: number | null }) => (
      request.expectedConfigRevision === 1
    ))).toBe(true);
    expect(relay.requests.some((request: { upstreamSecretPresent: boolean }) => (
      request.upstreamSecretPresent
    ))).toBe(true);
    expect(expectedSandboxStorageDenials.length).toBeGreaterThan(0);
    expect(expectedProbeDiagnostics).toHaveLength(1);
    expect(expectedLifecycleDiagnostics.length).toBeGreaterThan(0);
    expect(unexpectedDiagnostics).toEqual([]);
  } finally {
    await initialClient?.close().catch(() => undefined);
    if (routes) {
      await routes.closeRuntime().catch(() => undefined);
      await routes.close();
    }
    for (const [name, value] of Object.entries(originalEnvironment)) {
      if (value === undefined) delete process.env[name];
      else process.env[name] = value;
    }
    await Promise.allSettled([
      connectionView?.close(),
      relay?.close(),
      official.close(),
    ]);
  }
});
