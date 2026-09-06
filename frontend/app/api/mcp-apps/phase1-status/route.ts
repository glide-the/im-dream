// [Input] Server-owned MCP Apps preview, lifecycle, sandbox, and capability configuration.
// [Output] Non-sensitive default/desired/effective Host snapshot; production Apps remain disabled.
// [Pos] Next policy projection for the Browser Host; it grants no upstream authority.
// [Sync] 2026-09-06: derive Browser and window.im capabilities from one actor-effective runtime-policy snapshot in app/_dream.

import {
  readCurrentMcpAppsStaticView,
  readMcpAppsPluginManifest,
  type McpAppsPluginManifest,
  type McpAppsStaticView,
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

export async function GET(request: Request) {
  const applicationOrigin = new URL(request.url).origin;
  const plugin = currentPluginManifest();
  const runtimePolicy = await currentRuntimePolicy(request);
  const previewRequested = enabled(process.env.INK_MCP_APPS_PHASE1_PREVIEW);
  const desiredEnabled = previewRequested && plugin?.lifecycle === 'enabled';
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
  const desiredFeatures = Object.freeze({
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
    && runtimePolicy?.policy.effective.resourceReads === true;
  const effectiveReadResource = effectiveEnabled
    && desiredFeatures.readResource
    && runtimePolicy?.policy.effective.resourceReads === true;
  const effectiveAppToolCalls = effectiveEnabled
    && desiredFeatures.appToolCalls
    && runtimePolicy?.policy.effective.lowRiskToolCalls === true;
  const effectiveUiMessage = effectiveEnabled && desiredFeatures.uiMessage;
  const effectiveFeatures = Object.freeze({
    readResource: effectiveReadResource,
    appToolCalls: effectiveAppToolCalls,
    uiMessage: effectiveUiMessage,
    windowIm: effectiveEnabled
      && desiredFeatures.windowIm
      && (effectiveAppToolCalls || effectiveUiMessage),
  });

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
          ? 'enabled'
          : previewRequested && plugin?.lifecycle === 'enabled'
            ? 'invalid'
            : plugin?.lifecycle ?? 'unavailable',
      },
      policy: configurationValid && runtimePolicy ? {
        revision: `${revision}:${runtimePolicy.policy.revision}`,
        pluginRevision: revision,
        runtimePolicyRevision: runtimePolicy.policy.revision,
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
