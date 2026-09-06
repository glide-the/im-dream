// [Input] Server-owned environment plus thin Route Handler requests and selectors.
// [Output] One process-scoped policy/manifest-governed Runtime while production Apps stay off.
// [Pos] Server-only composition root; no request-local manager and no Browser-visible configuration.
// [Sync] 2026-09-06: compose configured limits plus authenticated static/connection policy for Browser/session isolation.

import {
  PRODUCTION_APPS_EFFECTIVE,
  McpAppsRuntimeError,
  type McpAppsStaticView,
  authorizationFingerprint,
  normalizeBrowserSessionScope,
  normalizeServerRef,
  normalizeWorkspaceScope,
} from './contracts.ts';
import { PythonConnectionViewProvider } from './config-provider.ts';
import { McpAppsHttpAdapter } from './http-adapter.ts';
import { PersistentConnectorManager } from './persistent-connector-manager.ts';
import { SdkConnectorFactory } from './sdk-connector.ts';
import { EnvironmentPluginManifestProvider } from './plugin-manifest.ts';
import { runtimeLimitsFromEnvironment } from './runtime-policy.ts';

declare global {
  var __inkDreamMcpAppsRuntime: McpAppsHttpAdapter | undefined;
}

function createRuntime(): McpAppsHttpAdapter {
  const provider = configuredProvider();
  const limits = runtimeLimitsFromEnvironment();
  return new McpAppsHttpAdapter(
    new PersistentConnectorManager(
      provider,
      new SdkConnectorFactory(limits),
      { maximumConcurrencyPerScope: limits.maximumConcurrencyPerScope },
    ),
    new EnvironmentPluginManifestProvider(),
  );
}

function configuredProvider(): PythonConnectionViewProvider {
  const backendBaseUrl = process.env.INK_BACKEND_INTERNAL_URL;
  const serviceToken = process.env.INK_MCP_APPS_NODE_SERVICE_TOKEN;
  if (!backendBaseUrl || !serviceToken) {
    throw new McpAppsRuntimeError(503, 'RUNTIME_CONFIG_UNAVAILABLE', 'MCP Apps Runtime is unavailable.');
  }
  return new PythonConnectionViewProvider({ backendBaseUrl, serviceToken });
}

export async function readCurrentMcpAppsStaticView(
  authorization: string,
): Promise<McpAppsStaticView> {
  return configuredProvider().getStaticView(authorization);
}

function processRuntime(): McpAppsHttpAdapter {
  globalThis.__inkDreamMcpAppsRuntime ??= createRuntime();
  return globalThis.__inkDreamMcpAppsRuntime;
}

function safeFailure(error: unknown): Response {
  const known = error instanceof McpAppsRuntimeError ? error : null;
  return Response.json(
    { error: known?.code ?? 'MCP_APPS_UNAVAILABLE' },
    { status: known?.status ?? 500, headers: { 'cache-control': 'no-store' } },
  );
}

export async function handleMcpAppsRequest(request: Request, rawServerRef: string): Promise<Response> {
  try {
    if (PRODUCTION_APPS_EFFECTIVE || process.env.INK_MCP_APPS_PHASE1_PREVIEW !== 'true') {
      await closeMcpAppsRuntime();
      throw new McpAppsRuntimeError(404, 'MCP_APPS_DISABLED', 'MCP Apps are unavailable.');
    }
    const requestUrl = new URL(request.url);
    const origin = request.headers.get('origin');
    if (origin && origin !== requestUrl.origin) {
      throw new McpAppsRuntimeError(403, 'CROSS_ORIGIN_DENIED', 'Cross-origin MCP Apps requests are denied.');
    }
    if (requestUrl.search) {
      throw new McpAppsRuntimeError(400, 'QUERY_SELECTOR_DENIED', 'MCP Apps query selectors are denied.');
    }
    const authorization = request.headers.get('authorization');
    if (!authorization?.startsWith('Bearer ') || authorization.length <= 7) {
      throw new McpAppsRuntimeError(401, 'AUTH_REQUIRED', 'MCP Apps authentication is required.');
    }
    const serverRef = normalizeServerRef(rawServerRef);
    const workspaceScope = normalizeWorkspaceScope(request.headers.get('x-ink-workspace-scope'));
    const browserSessionScope = normalizeBrowserSessionScope(
      request.headers.get('x-ink-mcp-apps-browser-session'),
    );
    return await processRuntime().handle(request, {
      authorization,
      authorizationFingerprint: authorizationFingerprint(authorization),
      workspaceScope,
      serverRef,
      browserSessionScope,
    });
  } catch (error) {
    return safeFailure(error);
  }
}

export async function closeMcpAppsRuntime(): Promise<void> {
  const runtime = globalThis.__inkDreamMcpAppsRuntime;
  globalThis.__inkDreamMcpAppsRuntime = undefined;
  await runtime?.closeAll();
}
