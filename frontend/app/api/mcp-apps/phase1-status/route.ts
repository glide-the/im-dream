// [Input] Server-owned MCP Apps preview plus optional actor-owned connection settings selector.
// [Output] Non-sensitive connection-scoped default/desired/effective Host snapshot with safe unavailability reason.
// [Pos] Next policy projection for the Browser Host; it grants no upstream authority.
// [Sync] 2026-09-06: derive Browser and window.im capabilities from one actor-effective runtime-policy snapshot in app/_dream.
// [Sync] 2026-09-06: intersect per-connection user choices with hidden deployment and server capabilities.

import {
  readCurrentMcpAppsStaticView,
  readCurrentMcpAppConnectionSettings,
  readMcpAppsPluginManifest,
  type McpAppsPluginManifest,
  type McpAppsStaticView,
  type McpAppConnectionSettingsView,
} from '@ink-dream/mcp-apps-runtime';
import { MCP_APPS_HOST_MANIFEST } from '../../../_dream/components/chat/mcp-apps/host-policy';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

function currentPluginManifest(): McpAppsPluginManifest | null {
  try {
    const plugin = readMcpAppsPluginManifest();
    if (plugin.pluginId !== MCP_APPS_HOST_MANIFEST.pluginId
      || plugin.pluginVersion !== MCP_APPS_HOST_MANIFEST.version
      || plugin.browserEntry !== MCP_APPS_HOST_MANIFEST.browserEntry
      || plugin.nodeEntry !== MCP_APPS_HOST_MANIFEST.nodeEntry) return null;
    return plugin;
  } catch {
    return null;
  }
}

function configuredPositiveInteger(value: string | undefined, fallback: number): number | null {
  if (value === undefined || value === '') return fallback;
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null;
}

function enabled(value: string | undefined): boolean {
  return value === 'true';
}

function resolveSandboxUrl(
  value: string | undefined,
  applicationOrigin: string,
  revision: string | null,
): string | null {
  if (!value || !revision) return null;
  try {
    const candidate = new URL(value);
    if (!['http:', 'https:'].includes(candidate.protocol) || candidate.origin === applicationOrigin) return null;
    candidate.searchParams.set('v', MCP_APPS_HOST_MANIFEST.version);
    candidate.searchParams.set('revision', revision);
    return candidate.href;
  } catch {
    return null;
  }
}

async function currentRuntimePolicy(request: Request): Promise<McpAppsStaticView | null> {
  const authorization = request.headers.get('authorization');
  if (!authorization) return null;
  try {
    return await readCurrentMcpAppsStaticView(authorization);
  } catch {
    return null;
  }
}

async function currentConnectionSettings(
  request: Request,
  serverRef: string | null,
  workspaceScope: string | null,
): Promise<McpAppConnectionSettingsView | null> {
  if (!serverRef) return null;
  const authorization = request.headers.get('authorization');
  if (!authorization) return null;
  try {
    return await readCurrentMcpAppConnectionSettings(
      authorization,
      serverRef,
      workspaceScope,
    );
  } catch {
    return null;
  }
}

export async function GET(request: Request) {
  const requestUrl = new URL(request.url);
  const applicationOrigin = requestUrl.origin;
  const serverRef = requestUrl.searchParams.get('serverRef');
  const workspaceScope = requestUrl.searchParams.get('workspaceScope');
  const connectionRequested = serverRef !== null;
  const plugin = currentPluginManifest();
  const [runtimePolicy, connectionSettings] = await Promise.all([
    currentRuntimePolicy(request),
    currentConnectionSettings(request, serverRef, workspaceScope),
  ]);
  const previewRequested = enabled(process.env.INK_MCP_APPS_PHASE1_PREVIEW);
  const desiredEnabled = connectionRequested
    ? connectionSettings?.desired.enabled === true
    : previewRequested && plugin?.lifecycle === 'enabled';
  const revision = plugin ? String(plugin.revision) : null;
  const sandboxUrl = resolveSandboxUrl(
    process.env.INK_MCP_APPS_SANDBOX_URL,
    applicationOrigin,
    revision,
  );
  const readyTimeoutMs = configuredPositiveInteger(
    process.env.INK_MCP_APPS_HOST_READY_TIMEOUT_MS,
    MCP_APPS_HOST_MANIFEST.defaults.hostReadyTimeoutMs,
  );
  const policyPollMs = configuredPositiveInteger(
    process.env.INK_MCP_APPS_POLICY_POLL_MS,
    MCP_APPS_HOST_MANIFEST.defaults.policyPollMs,
  );
  const desiredFeatures = Object.freeze(connectionRequested ? {
    readResource: desiredEnabled,
    appToolCalls: connectionSettings?.desired.interactions.lowRiskToolCalls === true,
    uiMessage: connectionSettings?.desired.interactions.uiMessages === true,
    windowIm: connectionSettings?.desired.interactions.lowRiskToolCalls === true
      || connectionSettings?.desired.interactions.uiMessages === true,
  } : {
    readResource: plugin?.features.resourceReads === true
      && runtimePolicy?.policy.desired.resourceReads === true,
    appToolCalls: plugin?.features.lowRiskToolCalls === true
      && runtimePolicy?.policy.desired.lowRiskToolCalls === true
      && enabled(process.env.INK_MCP_APPS_PHASE2_TOOL_CALLS),
    uiMessage: plugin?.features.uiMessage === true
      && enabled(process.env.INK_MCP_APPS_PHASE2_UI_MESSAGE),
    windowIm: plugin?.features.windowIm === true
      && enabled(process.env.INK_MCP_APPS_WINDOW_IM),
  });
  const configurationValid = Boolean(
    plugin?.lifecycle === 'enabled'
      && runtimePolicy
      && revision
      && sandboxUrl
      && readyTimeoutMs
      && policyPollMs,
  );
  const effectiveEnabled = desiredEnabled
    && configurationValid
    && runtimePolicy?.policy.effective.resourceReads === true
    && (!connectionRequested || connectionSettings?.server.resourceReads === true);
  const effectiveReadResource = effectiveEnabled
    && desiredFeatures.readResource
    && runtimePolicy?.policy.effective.resourceReads === true;
  const effectiveAppToolCalls = effectiveEnabled
    && desiredFeatures.appToolCalls
    && plugin?.features.lowRiskToolCalls === true
    && enabled(process.env.INK_MCP_APPS_PHASE2_TOOL_CALLS)
    && (!connectionRequested || connectionSettings?.server.lowRiskToolCalls === true)
    && runtimePolicy?.policy.effective.lowRiskToolCalls === true;
  const effectiveUiMessage = effectiveEnabled
    && desiredFeatures.uiMessage
    && plugin?.features.uiMessage === true
    && enabled(process.env.INK_MCP_APPS_PHASE2_UI_MESSAGE);
  const effectiveFeatures = Object.freeze({
    readResource: effectiveReadResource,
    appToolCalls: effectiveAppToolCalls,
    uiMessage: effectiveUiMessage,
    windowIm: effectiveEnabled
      && desiredFeatures.windowIm
      && plugin?.features.windowIm === true
      && enabled(process.env.INK_MCP_APPS_WINDOW_IM)
      && (effectiveAppToolCalls || effectiveUiMessage),
  });
  const requestedFeatureUnavailable = effectiveEnabled && (
    (desiredFeatures.appToolCalls && !effectiveFeatures.appToolCalls)
    || (desiredFeatures.uiMessage && !effectiveFeatures.uiMessage)
  );
  const reasonCode = !desiredEnabled
    ? (connectionRequested ? 'user_disabled' : 'service_not_enabled')
    : connectionRequested && !connectionSettings
      ? 'connection_settings_unavailable'
      : connectionRequested && connectionSettings?.server.state !== 'ready'
        ? connectionSettings?.server.reasonCode ?? connectionSettings?.server.state
        : !previewRequested
          ? 'service_not_enabled'
          : !plugin
            ? 'plugin_unavailable'
            : !runtimePolicy
              ? 'runtime_policy_unavailable'
              : !sandboxUrl
                ? 'sandbox_not_configured'
                : !readyTimeoutMs || !policyPollMs
                  ? 'host_policy_invalid'
                  : runtimePolicy.policy.effective.resourceReads !== true
                    ? 'runtime_policy_denied'
                    : requestedFeatureUnavailable
                      ? 'interaction_partially_available'
                      : null;
  const policyRevision = revision && runtimePolicy
    ? `${revision}:${runtimePolicy.policy.revision}${connectionSettings ? `:${connectionSettings.revision}` : ''}`
    : null;

  return Response.json(
    {
      productionAppsEffective: false,
      manifest: MCP_APPS_HOST_MANIFEST,
      plugin,
      default: {
        enabled: false,
        features: {
          readResource: false,
          appToolCalls: false,
          uiMessage: false,
          windowIm: false,
        },
      },
      desired: { enabled: desiredEnabled, features: desiredFeatures },
      effective: {
        enabled: effectiveEnabled,
        features: effectiveFeatures,
        state: effectiveEnabled
          ? requestedFeatureUnavailable ? 'partially_enabled' : 'enabled'
          : desiredEnabled ? 'unavailable' : 'disabled',
        reasonCode,
      },
      connection: connectionRequested ? connectionSettings : null,
      policy: configurationValid && runtimePolicy ? {
        revision: policyRevision,
        pluginRevision: revision,
        runtimePolicyRevision: runtimePolicy.policy.revision,
        appSettingsRevision: connectionSettings?.revision ?? null,
        manifestVersion: MCP_APPS_HOST_MANIFEST.version,
        sandboxUrl,
        sandboxTokens: ['allow-scripts'],
        desiredPermissions: [],
        effectivePermissions: [],
        readyTimeoutMs,
        policyPollMs,
      } : null,
    },
    { headers: { 'cache-control': 'no-store' } },
  );
}
