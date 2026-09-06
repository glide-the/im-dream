// [Input] Injected Python projections and expected config/credential/App-settings/policy revisions.
// [Output] Request-shape, safe settings, scope/static-policy validation, failure normalization, and expiry assertions.
// [Pos] Provider-free Node-to-Python boundary test; no network or credential logging.
// [Sync] 2026-09-06: prove every-revision request and safe 403/409/503 mapping.
// [Sync] 2026-09-06: prove App-settings reads and revision revalidation remain secret-free.

import assert from 'node:assert/strict';
import test from 'node:test';

import { PythonConnectionViewProvider } from './config-provider.ts';
import { McpAppsRuntimeError } from './contracts.ts';

function rawView() {
  return {
    actorScope: 'actor-1',
    workspaceScope: 'workspace-1',
    serverId: 'server-1',
    serverRef: 'official-basic',
    transportKind: 'streamable_http',
    enabled: true,
    configRevision: 4,
    credentialRevision: 2,
    appSettingsRevision: 3,
    expiresAt: '2099-01-01T00:00:00.000Z',
    allowedTools: ['get-time'],
    allowedResources: ['ui://get-time/mcp-app.html'],
    appCallableLowRiskTools: [],
    policy: {
      version: 1,
      revision: 7,
      default: { resourceReads: false, lowRiskToolCalls: false },
      desired: { resourceReads: true, lowRiskToolCalls: false },
      effective: { resourceReads: true, lowRiskToolCalls: false },
    },
    connectionProfile: {
      type: 'streamable_http',
      url: 'https://mcp.example.test/mcp',
      headers: { authorization: 'Bearer upstream-private' },
    },
  };
}

test('sends expected config, credential, and policy revisions on a no-store request', async () => {
  let captured: RequestInit | undefined;
  const provider = new PythonConnectionViewProvider({
    backendBaseUrl: 'https://backend.invalid/',
    serviceToken: 'service-private',
    fetchImpl: async (_url, init) => {
      captured = init;
      return Response.json(rawView());
    },
  });
  const view = await provider.getConnectionView({
    authorization: 'Bearer browser-private',
    workspaceScope: 'workspace-1',
    serverRef: 'official-basic',
    expectedConfigRevision: 4,
    expectedCredentialRevision: 2,
    expectedAppSettingsRevision: 3,
    expectedPolicyRevision: 7,
  });

  assert.equal(view.policy.revision, 7);
  assert.equal(captured?.cache, 'no-store');
  assert.deepEqual(JSON.parse(String(captured?.body)), {
    workspace_scope: 'workspace-1',
    expected_config_revision: 4,
    expected_credential_revision: 2,
    expected_app_settings_revision: 3,
    expected_policy_revision: 7,
  });
});

test('reads a safe connection App-settings projection without the Node service credential', async () => {
  let capturedUrl = '';
  let captured: RequestInit | undefined;
  const provider = new PythonConnectionViewProvider({
    backendBaseUrl: 'https://backend.invalid',
    serviceToken: 'service-private',
    fetchImpl: async (url, init) => {
      capturedUrl = String(url);
      captured = init;
      return Response.json({
        appSettings: {
          version: 1,
          revision: 3,
          default: {
            enabled: false,
            interactions: { lowRiskToolCalls: false, uiMessages: false },
          },
          desired: {
            enabled: true,
            interactions: { lowRiskToolCalls: true, uiMessages: false },
          },
          server: {
            state: 'ready',
            reasonCode: null,
            resourceReads: true,
            lowRiskToolCalls: true,
          },
        },
      });
    },
  });
  const settings = await provider.getAppConnectionSettings({
    authorization: 'Bearer browser-private',
    workspaceScope: 'workspace-1',
    serverRef: 'official-basic',
  });
  assert.equal(settings.revision, 3);
  assert.equal(settings.desired.interactions.lowRiskToolCalls, true);
  assert.equal(capturedUrl, 'https://backend.invalid/api/claude-mcp/servers/official-basic/app-settings?workspace_id=workspace-1');
  assert.deepEqual(captured?.headers, { authorization: 'Bearer browser-private' });
});

test('normalizes Python denial, revision conflict, and unavailability without reading bodies', async () => {
  for (const [upstreamStatus, expectedStatus] of [[403, 403], [409, 409], [500, 503]] as const) {
    const provider = new PythonConnectionViewProvider({
      backendBaseUrl: 'https://backend.invalid',
      serviceToken: 'service-private',
      fetchImpl: async () => new Response('private provider body', { status: upstreamStatus }),
    });
    await assert.rejects(
      provider.getConnectionView({
        authorization: 'Bearer browser-private',
        workspaceScope: 'workspace-1',
        serverRef: 'official-basic',
      }),
      (error: unknown) => error instanceof McpAppsRuntimeError
        && error.status === expectedStatus
        && !error.message.includes('private provider body'),
    );
  }
});

test('rejects a mismatched workspace projection', async () => {
  const provider = new PythonConnectionViewProvider({
    backendBaseUrl: 'https://backend.invalid',
    serviceToken: 'service-private',
    fetchImpl: async () => Response.json({ ...rawView(), workspaceScope: 'workspace-2' }),
  });
  await assert.rejects(
    provider.getConnectionView({
      authorization: 'Bearer browser-private',
      workspaceScope: 'workspace-1',
      serverRef: 'official-basic',
    }),
    (error: unknown) => error instanceof McpAppsRuntimeError && error.status === 403,
  );
});

test('reads only the closed non-secret static policy projection', async () => {
  let capturedUrl = '';
  let captured: RequestInit | undefined;
  const provider = new PythonConnectionViewProvider({
    backendBaseUrl: 'https://backend.invalid',
    serviceToken: 'service-private',
    fetchImpl: async (url, init) => {
      capturedUrl = String(url);
      captured = init;
      return Response.json({
        protocolVersion: '2026-01-26',
        productionAppsEffective: false,
        transports: ['streamable_http'],
        policy: rawView().policy,
      });
    },
  });
  const value = await provider.getStaticView('Bearer browser-private');
  assert.equal(value.policy.revision, 7);
  assert.equal(capturedUrl, 'https://backend.invalid/api/claude-mcp/app-runtime/static');
  assert.equal((captured?.headers as Record<string, string>).authorization, 'Bearer browser-private');
  assert.equal((captured?.headers as Record<string, string>)['x-ink-mcp-apps-service'], 'service-private');
  assert.equal(JSON.stringify(value).includes('upstream-private'), false);
});
