// [Input] Server process configuration and validated upstream connection/resource values.
// [Output] Positive safe-integer limits, network allowlist decisions, and resource byte accounting.
// [Pos] Phase 3 resource/network policy boundary; no deployment-name or business-value branches.
// [Sync] 2026-09-06: add configurable catalog pages, bytes, timeout, per-scope concurrency, and host policy.

import type { ReadResourceResult } from '@modelcontextprotocol/sdk/types.js';

import {
  McpAppsRuntimeError,
  type McpAppsConnectionView,
} from './contracts.ts';

export type McpAppsRuntimeLimits = Readonly<{
  maximumResourceBytes: number;
  maximumCatalogPages: number;
  upstreamTimeoutMs: number;
  maximumConcurrencyPerScope: number;
  networkHostAllowlist: readonly string[];
}>;

function positiveSafeInteger(raw: string | undefined, name: string): number {
  if (!raw || !/^\d+$/.test(raw)) {
    throw new McpAppsRuntimeError(503, 'RUNTIME_POLICY_UNAVAILABLE', `MCP Apps ${name} policy is unavailable.`);
  }
  const value = Number(raw);
  if (!Number.isSafeInteger(value) || value < 1) {
    throw new McpAppsRuntimeError(503, 'RUNTIME_POLICY_INVALID', `MCP Apps ${name} policy is invalid.`);
  }
  return value;
}

export function parseNetworkHostAllowlist(raw: string | undefined): readonly string[] {
  if (!raw) {
    throw new McpAppsRuntimeError(503, 'RUNTIME_POLICY_UNAVAILABLE', 'MCP Apps network policy is unavailable.');
  }
  const entries = raw.split(',').map((item) => item.trim().toLowerCase());
  if (
    entries.length === 0
    || entries.some((item) => !item || item === '*' || !/^(?:\*\.)?[a-z0-9:[\]._-]+$/.test(item))
  ) {
    throw new McpAppsRuntimeError(503, 'RUNTIME_POLICY_INVALID', 'MCP Apps network policy is invalid.');
  }
  return Object.freeze([...new Set(entries)]);
}

export function runtimeLimitsFromEnvironment(): McpAppsRuntimeLimits {
  return Object.freeze({
    maximumResourceBytes: positiveSafeInteger(
      process.env.INK_MCP_APPS_MAX_RESOURCE_BYTES,
      'resource byte',
    ),
    maximumCatalogPages: positiveSafeInteger(
      process.env.INK_MCP_APPS_MAX_CATALOG_PAGES,
      'catalog page',
    ),
    upstreamTimeoutMs: positiveSafeInteger(
      process.env.INK_MCP_APPS_UPSTREAM_TIMEOUT_MS,
      'upstream timeout',
    ),
    maximumConcurrencyPerScope: positiveSafeInteger(
      process.env.INK_MCP_APPS_MAX_CONCURRENCY_PER_SCOPE,
      'concurrency',
    ),
    networkHostAllowlist: parseNetworkHostAllowlist(
      process.env.INK_MCP_APPS_NETWORK_HOST_ALLOWLIST,
    ),
  });
}

export function networkHostAllowed(hostname: string, allowlist: readonly string[]): boolean {
  const candidate = hostname.toLowerCase();
  return allowlist.some((entry) => {
    if (!entry.startsWith('*.')) return candidate === entry;
    const suffix = entry.slice(1);
    return candidate.endsWith(suffix) && candidate.length > suffix.length;
  });
}

export function requireAllowedConnection(
  view: McpAppsConnectionView,
  allowlist: readonly string[],
): URL {
  let url: URL;
  try {
    url = new URL(view.connectionProfile.url);
  } catch {
    throw new McpAppsRuntimeError(503, 'UPSTREAM_ENDPOINT_DENIED', 'MCP Apps upstream is unavailable.');
  }
  if (
    !['http:', 'https:'].includes(url.protocol)
    || url.username !== ''
    || url.password !== ''
    || !networkHostAllowed(url.hostname, allowlist)
  ) {
    throw new McpAppsRuntimeError(503, 'UPSTREAM_ENDPOINT_DENIED', 'MCP Apps upstream is unavailable.');
  }
  return url;
}

export function resourceResultBytes(result: ReadResourceResult): number {
  return result.contents.reduce((total, content) => {
    if ('text' in content) return total + Buffer.byteLength(content.text, 'utf8');
    if ('blob' in content) return total + Buffer.byteLength(content.blob, 'base64');
    return total;
  }, 0);
}

export function requireResourceWithinLimit(
  result: ReadResourceResult,
  maximumResourceBytes: number,
): ReadResourceResult {
  if (resourceResultBytes(result) > maximumResourceBytes) {
    throw new McpAppsRuntimeError(413, 'RESOURCE_TOO_LARGE', 'MCP App resource exceeds policy.');
  }
  return result;
}
