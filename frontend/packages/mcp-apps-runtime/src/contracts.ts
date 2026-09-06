// [Input] Untrusted HTTP selectors and the Python single-Server connection projection.
// [Output] Strict Node-only route, policy, view, catalog, lease, and redacted failure contracts.
// [Pos] Runtime package validation boundary; no Browser, React, DOM, or root-Web imports.
// [Sync] 2026-09-06: add strict static policy, finite expiry, per-request calls, and Browser/plugin/workspace isolation.
// [Sync] 2026-09-06: hash canonical connection profiles into same-revision drift identity.

import { createHash } from 'node:crypto';

import type {
  CallToolResult,
  ReadResourceResult,
  Resource,
  Tool,
} from '@modelcontextprotocol/sdk/types.js';

export const PRODUCTION_APPS_EFFECTIVE = false;
export const MCP_APPS_PROTOCOL_VERSION = '2026-01-26';

export type McpAppsRequestContext = Readonly<{
  authorization: string;
  authorizationFingerprint: string;
  workspaceScope: string | null;
  serverRef: string;
  browserSessionScope: string | null;
}>;

export type McpAppsPolicyState = Readonly<{
  resourceReads: boolean;
  lowRiskToolCalls: boolean;
}>;

export type McpAppsPolicyView = Readonly<{
  version: 1;
  revision: number;
  default: McpAppsPolicyState;
  desired: McpAppsPolicyState;
  effective: McpAppsPolicyState;
}>;

export type McpAppsStaticView = Readonly<{
  protocolVersion: typeof MCP_APPS_PROTOCOL_VERSION;
  productionAppsEffective: false;
  transports: readonly ['streamable_http'];
  policy: McpAppsPolicyView;
}>;

export type ConnectionProfile = Readonly<{
  type: 'streamable_http';
  url: string;
  headers: Readonly<Record<string, string>>;
}>;

export type McpAppsConnectionView = Readonly<{
  actorScope: string;
  workspaceScope: string | null;
  serverId: string;
  serverRef: string;
  transportKind: 'streamable_http';
  enabled: true;
  configRevision: number;
  credentialRevision: number;
  expiresAt: string;
  allowedTools: readonly string[];
  allowedResources: readonly string[];
  appCallableLowRiskTools: readonly string[];
  policy: McpAppsPolicyView;
  connectionProfile: ConnectionProfile;
}>;

export type ConnectorCatalog = Readonly<{
  tools: readonly Tool[];
  resources: readonly Resource[];
}>;

export interface ManagedConnector {
  readonly catalog: ConnectorCatalog;
  readResource(uri: string): Promise<ReadResourceResult>;
  callTool(name: string, args: Readonly<Record<string, unknown>>): Promise<CallToolResult>;
  close(): Promise<void>;
}

export interface ConnectorFactory {
  connect(view: McpAppsConnectionView): Promise<ManagedConnector>;
}

export interface ConnectionViewProvider {
  getConnectionView(input: Readonly<{
    authorization: string;
    workspaceScope: string | null;
    serverRef: string;
    expectedConfigRevision?: number;
    expectedCredentialRevision?: number;
    expectedPolicyRevision?: number;
  }>): Promise<McpAppsConnectionView>;
}

export type ConnectionLease = Readonly<{
  id: string;
  key: string;
  view: McpAppsConnectionView;
  connector: ManagedConnector;
  browserSessionScope: string | null;
  manifestRevision: number;
}>;

export class McpAppsRuntimeError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = 'McpAppsRuntimeError';
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function requireString(value: unknown, field: string): string {
  if (typeof value !== 'string' || value.length === 0) {
    throw new McpAppsRuntimeError(502, 'INVALID_CONNECTION_VIEW', `Invalid ${field}.`);
  }
  return value;
}

function requireRevision(value: unknown, field: string, minimum: number): number {
  if (!Number.isSafeInteger(value) || (value as number) < minimum) {
    throw new McpAppsRuntimeError(502, 'INVALID_CONNECTION_VIEW', `Invalid ${field}.`);
  }
  return value as number;
}

function requireStringArray(value: unknown, field: string): readonly string[] {
  if (!Array.isArray(value) || value.some((item) => typeof item !== 'string' || item.length === 0)) {
    throw new McpAppsRuntimeError(502, 'INVALID_CONNECTION_VIEW', `Invalid ${field}.`);
  }
  return Object.freeze([...new Set(value)]);
}

function requirePolicyState(value: unknown, field: string): McpAppsPolicyState {
  if (
    !isRecord(value)
    || typeof value.resourceReads !== 'boolean'
    || typeof value.lowRiskToolCalls !== 'boolean'
  ) {
    throw new McpAppsRuntimeError(502, 'INVALID_CONNECTION_VIEW', `Invalid ${field}.`);
  }
  return Object.freeze({
    resourceReads: value.resourceReads,
    lowRiskToolCalls: value.lowRiskToolCalls,
  });
}

export function parseMcpAppsPolicyView(value: unknown): McpAppsPolicyView {
  if (!isRecord(value) || value.version !== 1) {
    throw new McpAppsRuntimeError(502, 'INVALID_CONNECTION_VIEW', 'Invalid policy.');
  }
  const defaultState = requirePolicyState(value.default, 'policy.default');
  const desired = requirePolicyState(value.desired, 'policy.desired');
  const effective = requirePolicyState(value.effective, 'policy.effective');
  if (
    defaultState.resourceReads
    || defaultState.lowRiskToolCalls
    || (effective.resourceReads && !desired.resourceReads)
    || (effective.lowRiskToolCalls && !desired.lowRiskToolCalls)
  ) {
    throw new McpAppsRuntimeError(502, 'INVALID_CONNECTION_VIEW', 'Invalid policy state transition.');
  }
  return Object.freeze({
    version: 1,
    revision: requireRevision(value.revision, 'policy.revision', 1),
    default: defaultState,
    desired,
    effective,
  });
}

export function parseMcpAppsStaticView(value: unknown): McpAppsStaticView {
  if (
    !isRecord(value)
    || value.protocolVersion !== MCP_APPS_PROTOCOL_VERSION
    || value.productionAppsEffective !== false
    || !Array.isArray(value.transports)
    || value.transports.length !== 1
    || value.transports[0] !== 'streamable_http'
  ) {
    throw new McpAppsRuntimeError(502, 'INVALID_STATIC_VIEW', 'MCP Apps policy view is invalid.');
  }
  return Object.freeze({
    protocolVersion: MCP_APPS_PROTOCOL_VERSION,
    productionAppsEffective: false,
    transports: Object.freeze(['streamable_http'] as const),
    policy: parseMcpAppsPolicyView(value.policy),
  });
}

export function parseConnectionView(value: unknown): McpAppsConnectionView {
  if (!isRecord(value) || !isRecord(value.connectionProfile)) {
    throw new McpAppsRuntimeError(502, 'INVALID_CONNECTION_VIEW', 'Connection view is invalid.');
  }
  const profile = value.connectionProfile;
  if (value.enabled !== true || value.transportKind !== 'streamable_http' || profile.type !== 'streamable_http') {
    throw new McpAppsRuntimeError(403, 'CONNECTION_VIEW_DENIED', 'MCP Apps connection is unavailable.');
  }
  const rawHeaders = profile.headers === undefined ? {} : profile.headers;
  if (!isRecord(rawHeaders) || Object.entries(rawHeaders).some(([key, item]) => !key || typeof item !== 'string')) {
    throw new McpAppsRuntimeError(502, 'INVALID_CONNECTION_VIEW', 'Connection headers are invalid.');
  }
  const expiresAt = requireString(value.expiresAt, 'expiresAt');
  const expiry = Date.parse(expiresAt);
  if (!Number.isFinite(expiry) || expiry <= Date.now()) {
    throw new McpAppsRuntimeError(409, 'CONNECTION_VIEW_EXPIRED', 'MCP Apps connection view expired.');
  }
  const allowedTools = requireStringArray(value.allowedTools, 'allowedTools');
  const allowedResources = requireStringArray(value.allowedResources, 'allowedResources');
  const appCallableLowRiskTools = requireStringArray(
    value.appCallableLowRiskTools,
    'appCallableLowRiskTools',
  );
  const policy = parseMcpAppsPolicyView(value.policy);
  if (
    appCallableLowRiskTools.some((name) => !allowedTools.includes(name))
    || (!policy.effective.lowRiskToolCalls && appCallableLowRiskTools.length > 0)
    || !policy.effective.resourceReads
  ) {
    throw new McpAppsRuntimeError(403, 'CONNECTION_VIEW_DENIED', 'MCP Apps connection is unavailable.');
  }
  return Object.freeze({
    actorScope: requireString(value.actorScope, 'actorScope'),
    workspaceScope: value.workspaceScope === null ? null : requireString(value.workspaceScope, 'workspaceScope'),
    serverId: requireString(value.serverId, 'serverId'),
    serverRef: normalizeServerRef(value.serverRef),
    transportKind: 'streamable_http',
    enabled: true,
    configRevision: requireRevision(value.configRevision, 'configRevision', 1),
    credentialRevision: requireRevision(value.credentialRevision, 'credentialRevision', 0),
    expiresAt,
    allowedTools,
    allowedResources,
    appCallableLowRiskTools,
    policy,
    connectionProfile: Object.freeze({
      type: 'streamable_http',
      url: requireString(profile.url, 'connectionProfile.url'),
      headers: Object.freeze(Object.fromEntries(Object.entries(rawHeaders) as [string, string][])),
    }),
  });
}

export function normalizeServerRef(value: unknown): string {
  if (typeof value !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(value)) {
    throw new McpAppsRuntimeError(400, 'INVALID_SERVER_REF', 'MCP Apps server selector is invalid.');
  }
  return value;
}

export function normalizeWorkspaceScope(value: string | null): string | null {
  if (value === null || value === '') return null;
  if (!/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(value)) {
    throw new McpAppsRuntimeError(400, 'INVALID_WORKSPACE_SCOPE', 'Workspace selector is invalid.');
  }
  return value;
}

export function normalizeBrowserSessionScope(value: string | null): string | null {
  if (value === null || value === '') return null;
  if (!/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(value)) {
    throw new McpAppsRuntimeError(400, 'INVALID_BROWSER_SESSION_SCOPE', 'Browser session selector is invalid.');
  }
  return value;
}

export function authorizationFingerprint(authorization: string): string {
  return createHash('sha256').update(authorization).digest('hex');
}

export function connectionKey(
  view: McpAppsConnectionView,
  browserSessionScope: string | null,
  manifestRevision: number,
): string {
  return JSON.stringify([
    view.actorScope,
    view.workspaceScope,
    view.serverId,
    view.serverRef,
    view.configRevision,
    view.credentialRevision,
    view.policy.revision,
    browserSessionScope,
    manifestRevision,
  ]);
}


export function connectionProfileDigest(profile: ConnectionProfile): string {
  const canonical = JSON.stringify([
    profile.type,
    profile.url,
    Object.entries(profile.headers).sort(([left], [right]) => (
      left < right ? -1 : left > right ? 1 : 0
    )),
  ]);
  return createHash('sha256').update(canonical).digest('hex');
}


export function authorizationStateKey(view: McpAppsConnectionView): string {
  return JSON.stringify([
    view.actorScope,
    view.workspaceScope,
    view.serverId,
    view.serverRef,
    view.configRevision,
    view.credentialRevision,
    view.policy,
    [...view.allowedTools].sort(),
    [...view.allowedResources].sort(),
    [...view.appCallableLowRiskTools].sort(),
    connectionProfileDigest(view.connectionProfile),
  ]);
}

export function isViewFresh(view: McpAppsConnectionView, now = Date.now(), skewMs = 1_000): boolean {
  return Date.parse(view.expiresAt) - skewMs > now;
}

export function deniedToolResult(): CallToolResult {
  return {
    content: [{ type: 'text', text: 'This MCP App tool is not allowed.' }],
    isError: true,
  };
}
