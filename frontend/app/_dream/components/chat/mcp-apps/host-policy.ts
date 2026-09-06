// [Input] Server-owned MCP Apps status JSON and the current Browser origin.
// [Output] Immutable, compatibility-checked Browser Host policy or a fail-closed null.
// [Pos] Browser-side Phase 1-3 plugin/policy boundary; contains no upstream selector or secret.
// [Sync] 2026-09-06: bind the app/_dream Browser entry identity to independent server-owned plugin and runtime-policy revisions.
// [Sync] 2026-09-06: bind Host policy to the current connection App-settings revision.

export const MCP_APPS_HOST_MANIFEST = Object.freeze({
  schemaVersion: 'im.mcp-apps-host-manifest/v1',
  pluginId: 'im.mcp-apps-host',
  version: '1.0.0',
  protocolVersion: '2026-01-26',
  browserEntry: 'frontend/app/_dream/components/chat/mcp-apps/McpAppHostPanel.tsx',
  nodeEntry: '@ink-dream/mcp-apps-runtime',
  sdk: Object.freeze({
    mcp: '1.30.x',
    extApps: '1.7.x',
    mcpUi: '7.1.x',
  }),
  defaults: Object.freeze({
    hostReadyTimeoutMs: 10_000,
    policyPollMs: 2_000,
    compatibilityRequestTimeoutMs: 10_000,
  }),
  features: Object.freeze({
    readResource: true,
    appToolCalls: true,
    uiMessage: true,
    windowIm: true,
    openLinks: false,
    fileDownload: false,
    modal: false,
    displayModeRequest: false,
  }),
} as const);

export type McpAppsHostFeatureState = Readonly<{
  readResource: boolean;
  appToolCalls: boolean;
  uiMessage: boolean;
  windowIm: boolean;
}>;

export type McpAppsHostPolicy = Readonly<{
  revision: string;
  pluginRevision: string;
  runtimePolicyRevision: number;
  appSettingsRevision: number | null;
  manifestVersion: string;
  sandboxUrl: string;
  sandboxOrigin: string;
  sandboxTokens: readonly ['allow-scripts'];
  desiredPermissions: readonly [];
  effectivePermissions: readonly [];
  features: McpAppsHostFeatureState;
  readyTimeoutMs: number;
  policyPollMs: number;
}>;

type McpAppsPluginSnapshot = Readonly<{
  manifestVersion: 1;
  pluginId: string;
  pluginVersion: string;
  revision: number;
  lifecycle: 'enabled';
  browserEntry: string;
  nodeEntry: string;
  features: Readonly<{
    resourceReads: true;
    lowRiskToolCalls: boolean;
    uiMessage: boolean;
    windowIm: boolean;
  }>;
}>;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isPositiveSafeInteger(value: unknown): value is number {
  return Number.isSafeInteger(value) && (value as number) > 0;
}

function parseFeatures(value: unknown): McpAppsHostFeatureState | null {
  if (!isRecord(value)) return null;
  const keys = ['readResource', 'appToolCalls', 'uiMessage', 'windowIm'] as const;
  if (keys.some((key) => typeof value[key] !== 'boolean')) return null;
  if (value.readResource !== true) return null;
  if (value.windowIm === true && value.appToolCalls !== true && value.uiMessage !== true) return null;
  return Object.freeze({
    readResource: true,
    appToolCalls: value.appToolCalls as boolean,
    uiMessage: value.uiMessage as boolean,
    windowIm: value.windowIm as boolean,
  });
}

function hasDisabledFeatures(value: unknown): boolean {
  return isRecord(value)
    && value.readResource === false
    && value.appToolCalls === false
    && value.uiMessage === false
    && value.windowIm === false;
}

function parsePlugin(value: unknown): McpAppsPluginSnapshot | null {
  if (!isRecord(value)
    || value.manifestVersion !== 1
    || value.pluginId !== MCP_APPS_HOST_MANIFEST.pluginId
    || value.pluginVersion !== MCP_APPS_HOST_MANIFEST.version
    || !Number.isSafeInteger(value.revision)
    || (value.revision as number) < 1
    || value.lifecycle !== 'enabled'
    || value.browserEntry !== MCP_APPS_HOST_MANIFEST.browserEntry
    || value.nodeEntry !== MCP_APPS_HOST_MANIFEST.nodeEntry
    || !isRecord(value.features)
    || value.features.resourceReads !== true
    || typeof value.features.lowRiskToolCalls !== 'boolean'
    || typeof value.features.uiMessage !== 'boolean'
    || typeof value.features.windowIm !== 'boolean'
    || (value.features.windowIm === true
      && value.features.uiMessage !== true
      && value.features.lowRiskToolCalls !== true)) return null;
  return Object.freeze({
    manifestVersion: 1,
    pluginId: value.pluginId,
    pluginVersion: value.pluginVersion,
    revision: value.revision as number,
    lifecycle: 'enabled',
    browserEntry: value.browserEntry,
    nodeEntry: value.nodeEntry,
    features: Object.freeze({
      resourceReads: true,
      lowRiskToolCalls: value.features.lowRiskToolCalls,
      uiMessage: value.features.uiMessage,
      windowIm: value.features.windowIm,
    }),
  });
}

export function parseMcpAppsHostPolicy(
  value: unknown,
  browserOrigin: string,
): McpAppsHostPolicy | null {
  if (!isRecord(value)
    || value.productionAppsEffective !== false
    || !isRecord(value.manifest)
    || !isRecord(value.default)
    || !isRecord(value.desired)
    || !isRecord(value.effective)
    || !isRecord(value.policy)) return null;
  const manifest = value.manifest;
  if (manifest.schemaVersion !== MCP_APPS_HOST_MANIFEST.schemaVersion
    || manifest.pluginId !== MCP_APPS_HOST_MANIFEST.pluginId
    || manifest.version !== MCP_APPS_HOST_MANIFEST.version
    || manifest.protocolVersion !== MCP_APPS_HOST_MANIFEST.protocolVersion
    || !isRecord(manifest.sdk)
    || manifest.sdk.mcp !== MCP_APPS_HOST_MANIFEST.sdk.mcp
    || manifest.sdk.extApps !== MCP_APPS_HOST_MANIFEST.sdk.extApps
    || manifest.sdk.mcpUi !== MCP_APPS_HOST_MANIFEST.sdk.mcpUi
    || !isRecord(manifest.defaults)
    || manifest.defaults.hostReadyTimeoutMs !== MCP_APPS_HOST_MANIFEST.defaults.hostReadyTimeoutMs
    || manifest.defaults.policyPollMs !== MCP_APPS_HOST_MANIFEST.defaults.policyPollMs
    || manifest.defaults.compatibilityRequestTimeoutMs !== MCP_APPS_HOST_MANIFEST.defaults.compatibilityRequestTimeoutMs) return null;
  const plugin = parsePlugin(value.plugin);
  if (!plugin
    || value.default.enabled !== false
    || !hasDisabledFeatures(value.default.features)
    || value.desired.enabled !== true
    || value.effective.enabled !== true) return null;
  const desiredFeatures = parseFeatures(value.desired.features);
  const features = parseFeatures(value.effective.features);
  if (!desiredFeatures || !features) return null;
  if ((features.appToolCalls && (!desiredFeatures.appToolCalls || !plugin.features.lowRiskToolCalls))
    || (features.uiMessage && (!desiredFeatures.uiMessage || !plugin.features.uiMessage))
    || (features.windowIm && (!desiredFeatures.windowIm || !plugin.features.windowIm))) return null;
  const policy = value.policy;
  if (typeof policy.revision !== 'string' || !policy.revision
    || policy.pluginRevision !== String(plugin.revision)
    || !isPositiveSafeInteger(policy.runtimePolicyRevision)
    || (policy.appSettingsRevision !== null
      && !isPositiveSafeInteger(policy.appSettingsRevision))
    || policy.revision !== `${policy.pluginRevision}:${policy.runtimePolicyRevision}${policy.appSettingsRevision === null ? '' : `:${policy.appSettingsRevision}`}`
    || policy.manifestVersion !== MCP_APPS_HOST_MANIFEST.version
    || typeof policy.sandboxUrl !== 'string'
    || !Array.isArray(policy.sandboxTokens)
    || policy.sandboxTokens.length !== 1
    || policy.sandboxTokens[0] !== 'allow-scripts'
    || !Array.isArray(policy.desiredPermissions)
    || policy.desiredPermissions.length !== 0
    || !Array.isArray(policy.effectivePermissions)
    || policy.effectivePermissions.length !== 0
    || !isPositiveSafeInteger(policy.readyTimeoutMs)
    || !isPositiveSafeInteger(policy.policyPollMs)) return null;
  let sandbox: URL;
  let host: URL;
  try {
    sandbox = new URL(policy.sandboxUrl);
    host = new URL(browserOrigin);
  } catch {
    return null;
  }
  if (!['http:', 'https:'].includes(sandbox.protocol)
    || sandbox.origin === host.origin
    || sandbox.username !== ''
    || sandbox.password !== ''
    || sandbox.hash !== ''
    || sandbox.searchParams.get('v') !== MCP_APPS_HOST_MANIFEST.version
    || sandbox.searchParams.get('revision') !== policy.pluginRevision) return null;
  return Object.freeze({
    revision: policy.revision,
    pluginRevision: policy.pluginRevision,
    runtimePolicyRevision: policy.runtimePolicyRevision,
    appSettingsRevision: policy.appSettingsRevision as number | null,
    manifestVersion: MCP_APPS_HOST_MANIFEST.version,
    sandboxUrl: sandbox.href,
    sandboxOrigin: sandbox.origin,
    sandboxTokens: Object.freeze(['allow-scripts'] as const),
    desiredPermissions: Object.freeze([] as const),
    effectivePermissions: Object.freeze([] as const),
    features,
    readyTimeoutMs: policy.readyTimeoutMs,
    policyPollMs: policy.policyPollMs,
  });
}

export function mcpAppsPolicyIdentity(policy: McpAppsHostPolicy): string {
  return JSON.stringify([
    policy.manifestVersion,
    policy.revision,
    policy.pluginRevision,
    policy.runtimePolicyRevision,
    policy.appSettingsRevision,
    policy.sandboxUrl,
    policy.features,
  ]);
}
