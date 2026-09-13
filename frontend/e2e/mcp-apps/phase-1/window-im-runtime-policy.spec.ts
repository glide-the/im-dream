// [Input] Production status/sandbox Route Handlers, one authenticated fake policy service, and an opaque iframe handshake.
// [Output] Regression proof that window.im methods follow the actor-effective Host capabilities across a runtime-only downgrade.
// [Pos] Provider-free Browser policy test; it starts only isolated loopback services and never touches business data.
// [Sync] 2026-09-06: lock tool-only fail-closed projection and remove window.im after an effective-policy downgrade.
// [Sync] 2026-09-06: retain two-part identity for the connection-free status probe; connection-scoped Host tests cover App-settings revisions.
// [Sync] 2026-09-13: serve the sandbox through the actual frontend entry and ignore stale sandbox/parent environment values.

import { expect, test, type Page } from '@playwright/test';
import { fileURLToPath } from 'node:url';

// @ts-expect-error The provider-free process helper is intentionally plain ESM.
import {
  reserveEphemeralPort,
  startConnectionViewService,
} from './node-harness.mjs';
import { startProductionRouteHarness } from './production-route-harness';


test.use({ channel: 'chrome', locale: 'en-US' });

const FRONTEND_ROOT = fileURLToPath(new URL('../../../', import.meta.url));
const SERVER_REF = 'window-im-policy-server';
const WORKSPACE_SCOPE = 'window-im-policy-workspace';
const BROWSER_AUTHORIZATION = 'Bearer window-im-policy-actor';
const SERVICE_TOKEN = 'window-im-policy-service-token';


type FeatureSnapshot = Readonly<{
  readResource: boolean;
  appToolCalls: boolean;
  uiMessage: boolean;
  windowIm: boolean;
}>;

type StatusSnapshot = Readonly<{
  desired: Readonly<{ enabled: boolean; features: FeatureSnapshot }>;
  effective: Readonly<{ enabled: boolean; features: FeatureSnapshot; state: string }>;
  policy: Readonly<{ revision: string; sandboxUrl: string }> | null;
}>;

type WindowImDetection = Readonly<{
  before: Readonly<{ windowIm: string; callTool: string }>;
  after: Readonly<{
    windowIm: string;
    callTool: string;
    sendFollowUpMessage: string;
    keys: readonly string[];
  }>;
}>;


function pluginManifest(): string {
  return JSON.stringify({
    manifestVersion: 1,
    pluginId: 'im.mcp-apps-host',
    pluginVersion: '1.0.0',
    revision: 1,
    lifecycle: 'enabled',
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


async function readStatus(hostOrigin: string, authorization: string): Promise<StatusSnapshot> {
  const response = await fetch(`${hostOrigin}/api/mcp-apps/phase1-status`, {
    headers: { authorization },
  });
  expect(response.status).toBe(200);
  return await response.json() as StatusSnapshot;
}


async function inspectWindowIm(
  page: Page,
  sandboxUrl: string,
  features: FeatureSnapshot,
): Promise<WindowImDetection> {
  return await page.evaluate(({ sandboxUrl: url, features: effective }) => (
    new Promise<WindowImDetection>((resolve, reject) => {
      document.body.replaceChildren();
      const outer = document.createElement('iframe');
      outer.setAttribute('sandbox', 'allow-scripts');
      outer.referrerPolicy = 'origin';
      outer.src = url;
      const timeout = window.setTimeout(() => {
        window.removeEventListener('message', onMessage);
        outer.remove();
        reject(new Error('window.im policy probe timed out.'));
      }, 5_000);
      const finish = (value: WindowImDetection) => {
        window.clearTimeout(timeout);
        window.removeEventListener('message', onMessage);
        outer.remove();
        resolve(value);
      };
      const onMessage = (event: MessageEvent) => {
        if (event.source !== outer.contentWindow || event.origin !== 'null') return;
        const message = event.data as {
          id?: string;
          method?: string;
          params?: WindowImDetection;
        } | null;
        if (!message) return;
        if (message.method === 'ui/notifications/sandbox-proxy-ready') {
          outer.contentWindow?.postMessage({
            jsonrpc: '2.0',
            method: 'ui/notifications/sandbox-resource-ready',
            params: {
              html: `<!doctype html><html><head></head><body><script>
                const beforeCandidate = window.im;
                const before = {
                  windowIm: typeof beforeCandidate,
                  callTool: typeof beforeCandidate?.callTool,
                };
                window.addEventListener('message', (event) => {
                  if (event.source !== parent || event.data?.id !== 'actor-policy-initialize') return;
                  const candidate = window.im;
                  parent.postMessage({
                    jsonrpc: '2.0',
                    method: 'test/window-im-detection',
                    params: {
                      before,
                      after: {
                        windowIm: typeof candidate,
                        callTool: typeof candidate?.callTool,
                        sendFollowUpMessage: typeof candidate?.sendFollowUpMessage,
                        keys: candidate ? Object.keys(candidate).sort() : [],
                      },
                    },
                  }, '*');
                });
                parent.postMessage({
                  jsonrpc: '2.0',
                  id: 'actor-policy-initialize',
                  method: 'ui/initialize',
                  params: {
                    appInfo: { name: 'window-im-policy-probe', version: '1.0.0' },
                    appCapabilities: {},
                    protocolVersion: '2026-01-26',
                  },
                }, '*');
              </script></body></html>`,
              sandbox: 'allow-scripts',
              permissions: {},
              csp: {
                connectDomains: [],
                resourceDomains: [],
                frameDomains: [],
                baseUriDomains: [],
              },
            },
          }, '*');
          return;
        }
        if (message.method === 'ui/initialize' && message.id === 'actor-policy-initialize') {
          outer.contentWindow?.postMessage({
            jsonrpc: '2.0',
            id: message.id,
            result: {
              protocolVersion: '2026-01-26',
              hostInfo: { name: 'actor-effective-policy-host', version: '1.0.0' },
              hostCapabilities: {
                serverResources: {},
                ...(effective.appToolCalls ? { serverTools: {} } : {}),
                ...(effective.uiMessage ? { message: { text: {} } } : {}),
              },
              hostContext: {},
            },
          }, '*');
          return;
        }
        if (message.method === 'test/window-im-detection' && message.params) {
          finish(message.params);
        }
      };
      window.addEventListener('message', onMessage);
      document.body.appendChild(outer);
    })
  ), { sandboxUrl, features });
}


test('runtime-policy-only downgrade removes window.im.callTool while manifest and flags stay enabled', async ({ page }) => {
  const originalEnvironment = Object.fromEntries([
    'INK_BACKEND_INTERNAL_URL',
    'INK_MCP_APPS_NODE_SERVICE_TOKEN',
    'INK_MCP_APPS_PHASE1_PREVIEW',
    'INK_MCP_APPS_SANDBOX_URL',
    'INK_MCP_APPS_PARENT_ORIGINS',
    'INK_MCP_APPS_PHASE2_TOOL_CALLS',
    'INK_MCP_APPS_PHASE2_UI_MESSAGE',
    'INK_MCP_APPS_WINDOW_IM',
    'INK_MCP_APPS_PLUGIN_MANIFEST_JSON',
  ].map((name) => [name, process.env[name]]));
  const connectionView = await startConnectionViewService({
    serverRef: SERVER_REF,
    workspaceScope: WORKSPACE_SCOPE,
    upstreamEndpointUrl: 'http://127.0.0.1:9/mcp',
    serviceToken: SERVICE_TOKEN,
    browserAuthorization: BROWSER_AUTHORIZATION,
    upstreamSecret: 'unused-window-im-policy-upstream-secret',
  });
  let routes: Awaited<ReturnType<typeof startProductionRouteHarness>> | null = null;

  try {
    connectionView.state.lowRiskToolCalls = true;
    const hostPort = await reserveEphemeralPort();
    const hostOrigin = `http://127.0.0.1:${hostPort}`;
    Object.assign(process.env, {
      INK_BACKEND_INTERNAL_URL: connectionView.origin,
      INK_MCP_APPS_NODE_SERVICE_TOKEN: SERVICE_TOKEN,
      INK_MCP_APPS_PHASE1_PREVIEW: 'true',
      INK_MCP_APPS_SANDBOX_URL: 'http://127.0.0.1:9/mcp-apps-sandbox',
      INK_MCP_APPS_PARENT_ORIGINS: 'http://stale.example.test',
      INK_MCP_APPS_PHASE2_TOOL_CALLS: 'true',
      INK_MCP_APPS_PHASE2_UI_MESSAGE: 'false',
      INK_MCP_APPS_WINDOW_IM: 'true',
      INK_MCP_APPS_PLUGIN_MANIFEST_JSON: pluginManifest(),
    });
    routes = await startProductionRouteHarness({
      frontendRoot: FRONTEND_ROOT,
      hostPort,
      browserConfig: {},
    });

    const enabled = await readStatus(hostOrigin, BROWSER_AUTHORIZATION);
    expect(enabled.policy).toEqual(expect.objectContaining({ revision: '1:1' }));
    expect(enabled.effective.features).toEqual(expect.objectContaining({
      appToolCalls: true,
      uiMessage: false,
      windowIm: true,
    }));
    await page.goto(`${hostOrigin}/api/mcp-apps/phase1-status`);
    const beforeDowngrade = await inspectWindowIm(
      page,
      enabled.policy!.sandboxUrl,
      enabled.effective.features,
    );
    expect(beforeDowngrade.before).toEqual({ windowIm: 'undefined', callTool: 'undefined' });
    expect(beforeDowngrade.after).toEqual(expect.objectContaining({
      windowIm: 'object',
      callTool: 'function',
      sendFollowUpMessage: 'undefined',
    }));
    expect(beforeDowngrade.after.keys).toContain('callTool');

    connectionView.state.lowRiskToolCalls = false;
    connectionView.state.policyRevision = 2;
    const downgraded = await readStatus(hostOrigin, BROWSER_AUTHORIZATION);
    expect(process.env.INK_MCP_APPS_PHASE2_TOOL_CALLS).toBe('true');
    expect(process.env.INK_MCP_APPS_PLUGIN_MANIFEST_JSON).toBe(pluginManifest());
    expect(downgraded.policy).toEqual(expect.objectContaining({ revision: '1:2' }));
    expect(downgraded.policy?.sandboxUrl).toBe(enabled.policy?.sandboxUrl);
    expect(downgraded.desired.features.appToolCalls).toBe(false);
    expect(downgraded.effective.features).toEqual(expect.objectContaining({
      appToolCalls: false,
      uiMessage: false,
      windowIm: false,
    }));
    const afterDowngrade = await inspectWindowIm(
      page,
      downgraded.policy!.sandboxUrl,
      downgraded.effective.features,
    );
    expect(afterDowngrade.after).toEqual(expect.objectContaining({
      windowIm: 'undefined',
      callTool: 'undefined',
      sendFollowUpMessage: 'undefined',
    }));
    expect(afterDowngrade.after.keys).not.toContain('callTool');

    const otherActor = await readStatus(hostOrigin, 'Bearer actor-without-policy');
    expect(otherActor.effective.enabled).toBe(false);
    expect(otherActor.effective.features.appToolCalls).toBe(false);
    expect(otherActor.policy).toBeNull();
  } finally {
    if (routes) {
      await routes.closeRuntime().catch(() => undefined);
      await routes.close();
    }
    for (const [name, value] of Object.entries(originalEnvironment)) {
      if (value === undefined) delete process.env[name];
      else process.env[name] = value;
    }
    await connectionView.close();
  }
});
