// [Input] Server-owned versioned plugin manifest and installed Node protocol/SDK identities.
// [Output] Strict lifecycle/compatibility decisions used to create or invalidate sessions.
// [Pos] Phase 3 plugin governance boundary; Browser input can never supply this manifest.
// [Sync] 2026-09-06: define manifest v1, lifecycle, features, and fail-closed compatibility.

import {
  MCP_APPS_PROTOCOL_VERSION,
  McpAppsRuntimeError,
} from './contracts.ts';

export const MCP_APPS_SDK_VERSION = '1.30.0';
export const MCP_APPS_EXT_APPS_VERSION = '1.7.5';
export const MCP_APPS_MCP_UI_VERSION = '7.1.1';
export const MCP_APPS_NODE_ENTRY = '@ink-dream/mcp-apps-runtime';
export const MCP_APPS_PLUGIN_MANIFEST_ENV = 'INK_MCP_APPS_PLUGIN_MANIFEST_JSON';

export type McpAppsPluginManifest = Readonly<{
  manifestVersion: 1;
  pluginId: string;
  pluginVersion: string;
  revision: number;
  lifecycle: 'enabled' | 'disabled' | 'destroyed';
  browserEntry: string;
  nodeEntry: typeof MCP_APPS_NODE_ENTRY;
  protocol: Readonly<{ minimum: string; maximum: string }>;
  sdk: Readonly<{
    mcp: Readonly<{ minimum: string; maximum: string }>;
    extApps: Readonly<{ minimum: string; maximum: string }>;
    mcpUi: Readonly<{ minimum: string; maximum: string }>;
  }>;
  features: Readonly<{
    resourceReads: boolean;
    lowRiskToolCalls: boolean;
    uiMessage: boolean;
    windowIm: boolean;
  }>;
}>;

export interface PluginManifestProvider {
  current(): McpAppsPluginManifest;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function requireString(value: unknown, field: string): string {
  if (typeof value !== 'string' || value.length === 0 || value.includes('\0')) {
    throw new McpAppsRuntimeError(503, 'PLUGIN_MANIFEST_INVALID', `Invalid plugin ${field}.`);
  }
  return value;
}

function requireRange(
  value: unknown,
  field: string,
  validVersion: (candidate: string) => boolean,
): Readonly<{ minimum: string; maximum: string }> {
  if (!isRecord(value)) {
    throw new McpAppsRuntimeError(503, 'PLUGIN_MANIFEST_INVALID', `Invalid plugin ${field}.`);
  }
  const range = Object.freeze({
    minimum: requireString(value.minimum, `${field}.minimum`),
    maximum: requireString(value.maximum, `${field}.maximum`),
  });
  if (!validVersion(range.minimum) || !validVersion(range.maximum) || compareVersions(range.minimum, range.maximum) > 0) {
    throw new McpAppsRuntimeError(503, 'PLUGIN_MANIFEST_INVALID', `Invalid plugin ${field}.`);
  }
  return range;
}

function semverParts(value: string): readonly number[] | null {
  const match = /^(\d+)\.(\d+)\.(\d+)(?:-[0-9A-Za-z.-]+)?$/.exec(value);
  return match ? match.slice(1).map(Number) : null;
}

function compareVersions(left: string, right: string): number {
  const leftSemver = semverParts(left);
  const rightSemver = semverParts(right);
  if (leftSemver && rightSemver) {
    for (let index = 0; index < 3; index += 1) {
      const difference = leftSemver[index]! - rightSemver[index]!;
      if (difference !== 0) return difference;
    }
    return 0;
  }
  return left.localeCompare(right);
}

function within(version: string, range: Readonly<{ minimum: string; maximum: string }>): boolean {
  return compareVersions(version, range.minimum) >= 0 && compareVersions(version, range.maximum) <= 0;
}

export function parsePluginManifest(value: unknown): McpAppsPluginManifest {
  if (!isRecord(value) || value.manifestVersion !== 1) {
    throw new McpAppsRuntimeError(503, 'PLUGIN_MANIFEST_INVALID', 'MCP Apps plugin manifest is invalid.');
  }
  const revision = value.revision;
  if (!Number.isSafeInteger(revision) || (revision as number) < 1) {
    throw new McpAppsRuntimeError(503, 'PLUGIN_MANIFEST_INVALID', 'MCP Apps plugin revision is invalid.');
  }
  if (!['enabled', 'disabled', 'destroyed'].includes(String(value.lifecycle))) {
    throw new McpAppsRuntimeError(503, 'PLUGIN_MANIFEST_INVALID', 'MCP Apps plugin lifecycle is invalid.');
  }
  if (value.nodeEntry !== MCP_APPS_NODE_ENTRY || !isRecord(value.features)) {
    throw new McpAppsRuntimeError(503, 'PLUGIN_MANIFEST_INVALID', 'MCP Apps plugin entry or features are invalid.');
  }
  if (!isRecord(value.sdk)) {
    throw new McpAppsRuntimeError(503, 'PLUGIN_MANIFEST_INVALID', 'MCP Apps plugin SDK ranges are invalid.');
  }
  if (
    typeof value.features.resourceReads !== 'boolean'
    || typeof value.features.lowRiskToolCalls !== 'boolean'
    || typeof value.features.uiMessage !== 'boolean'
    || typeof value.features.windowIm !== 'boolean'
    || (
      value.features.windowIm
      && !value.features.uiMessage
      && !value.features.lowRiskToolCalls
    )
  ) {
    throw new McpAppsRuntimeError(503, 'PLUGIN_MANIFEST_INVALID', 'MCP Apps plugin features are invalid.');
  }
  const pluginVersion = requireString(value.pluginVersion, 'pluginVersion');
  if (!semverParts(pluginVersion)) {
    throw new McpAppsRuntimeError(503, 'PLUGIN_MANIFEST_INVALID', 'MCP Apps plugin version is invalid.');
  }
  const pluginId = requireString(value.pluginId, 'pluginId');
  const browserEntry = requireString(value.browserEntry, 'browserEntry');
  if (
    !/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(pluginId)
    || browserEntry.startsWith('/')
    || browserEntry.split('/').includes('..')
    || !/^[A-Za-z0-9][A-Za-z0-9._/-]{0,255}$/.test(browserEntry)
  ) {
    throw new McpAppsRuntimeError(503, 'PLUGIN_MANIFEST_INVALID', 'MCP Apps plugin identity or entry is invalid.');
  }
  const manifest = Object.freeze({
    manifestVersion: 1 as const,
    pluginId,
    pluginVersion,
    revision: revision as number,
    lifecycle: value.lifecycle as McpAppsPluginManifest['lifecycle'],
    browserEntry,
    nodeEntry: MCP_APPS_NODE_ENTRY,
    protocol: requireRange(value.protocol, 'protocol', (candidate) => /^\d{4}-\d{2}-\d{2}$/.test(candidate)),
    sdk: Object.freeze({
      mcp: requireRange(value.sdk.mcp, 'sdk.mcp', (candidate) => semverParts(candidate) !== null),
      extApps: requireRange(value.sdk.extApps, 'sdk.extApps', (candidate) => semverParts(candidate) !== null),
      mcpUi: requireRange(value.sdk.mcpUi, 'sdk.mcpUi', (candidate) => semverParts(candidate) !== null),
    }),
    features: Object.freeze({
      resourceReads: value.features.resourceReads,
      lowRiskToolCalls: value.features.lowRiskToolCalls,
      uiMessage: value.features.uiMessage,
      windowIm: value.features.windowIm,
    }),
  });
  if (
    !within(MCP_APPS_PROTOCOL_VERSION, manifest.protocol)
    || !within(MCP_APPS_SDK_VERSION, manifest.sdk.mcp)
    || !within(MCP_APPS_EXT_APPS_VERSION, manifest.sdk.extApps)
    || !within(MCP_APPS_MCP_UI_VERSION, manifest.sdk.mcpUi)
  ) {
    throw new McpAppsRuntimeError(503, 'PLUGIN_INCOMPATIBLE', 'MCP Apps plugin is incompatible.');
  }
  return manifest;
}

export function requireEnabledPlugin(provider: PluginManifestProvider): McpAppsPluginManifest {
  const manifest = provider.current();
  if (manifest.lifecycle !== 'enabled' || !manifest.features.resourceReads) {
    throw new McpAppsRuntimeError(503, 'PLUGIN_DISABLED', 'MCP Apps plugin is unavailable.');
  }
  return manifest;
}

export function manifestIdentity(manifest: McpAppsPluginManifest): string {
  return JSON.stringify([
    manifest.pluginId,
    manifest.pluginVersion,
    manifest.revision,
    manifest.lifecycle,
    manifest.browserEntry,
    manifest.nodeEntry,
    manifest.protocol,
    manifest.sdk,
    manifest.features,
  ]);
}

export class EnvironmentPluginManifestProvider implements PluginManifestProvider {
  current(): McpAppsPluginManifest {
    const raw = process.env[MCP_APPS_PLUGIN_MANIFEST_ENV];
    if (!raw) {
      throw new McpAppsRuntimeError(503, 'PLUGIN_MANIFEST_UNAVAILABLE', 'MCP Apps plugin is unavailable.');
    }
    try {
      return parsePluginManifest(JSON.parse(raw));
    } catch (error) {
      if (error instanceof McpAppsRuntimeError) throw error;
      throw new McpAppsRuntimeError(503, 'PLUGIN_MANIFEST_INVALID', 'MCP Apps plugin manifest is invalid.');
    }
  }
}
