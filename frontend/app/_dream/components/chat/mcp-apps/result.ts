// [Input] Optional versioned mcpAppResult plus its enclosing saved tool part identity.
// [Output] A strict complete CallToolResult projection or null for ordinary fallback.
// [Pos] Chat-to-MCP-Apps recognition boundary; it never infers owner/UI identity from output metadata.
// [Sync] 2026-09-06: require trusted workspace scope and a complete non-error v1 result; reject spoofed/mismatched/sensitive projections.

import type { CallToolResult } from '@modelcontextprotocol/sdk/types.js';

const SERVER_REF = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
const PROJECTION_KEYS = Object.freeze([
  'input',
  'resourceUri',
  'result',
  'serverRef',
  'toolCallId',
  'toolName',
  'version',
  'workspaceScope',
] as const);
const SENSITIVE_KEYS = new Set([
  'authorization',
  'connection_profile',
  'connectionprofile',
  'cookie',
  'credential',
  'credentials',
  'env',
  'headers',
  'password',
  'refresh_token',
  'runtime_snapshot',
  'runtimesnapshot',
  'secret',
  'socket',
  'stdio_command',
  'token',
  'upstream_url',
  'url',
]);

export type McpAppsToolResultProjectionV1 = Readonly<{
  version: 1;
  serverRef: string;
  toolName: string;
  toolCallId: string;
  input: Record<string, unknown>;
  workspaceScope: string | null;
  resourceUri: string;
  result: CallToolResult;
}>;

export type SavedMcpAppToolCall = Readonly<{
  serverRef: string;
  resourceUri: string;
  toolName: string;
  toolCallId: string;
  input: Record<string, unknown>;
  workspaceScope: string | null;
  result: CallToolResult;
}>;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function normalizedKey(value: string): string {
  return value.trim().toLowerCase().replaceAll('-', '_');
}

function isSafeJsonValue(
  value: unknown,
  seen: Set<object> = new Set(),
  depth = 0,
): boolean {
  if (depth > 64) return false;
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return true;
  if (typeof value === 'number') return Number.isFinite(value);
  if (typeof value !== 'object') return false;
  if (seen.has(value)) return false;
  seen.add(value);
  const valid = Array.isArray(value)
    ? value.every((item) => isSafeJsonValue(item, seen, depth + 1))
    : Object.entries(value).every(([key, item]) => (
      !SENSITIVE_KEYS.has(normalizedKey(key))
      && isSafeJsonValue(item, seen, depth + 1)
    ));
  seen.delete(value);
  return valid;
}

function jsonEqual(left: unknown, right: unknown, depth = 0): boolean {
  if (Object.is(left, right)) return true;
  if (depth > 64 || typeof left !== typeof right || left === null || right === null) return false;
  if (Array.isArray(left) || Array.isArray(right)) {
    return Array.isArray(left)
      && Array.isArray(right)
      && left.length === right.length
      && left.every((item, index) => jsonEqual(item, right[index], depth + 1));
  }
  if (!isRecord(left) || !isRecord(right)) return false;
  const leftKeys = Object.keys(left).sort();
  const rightKeys = Object.keys(right).sort();
  return leftKeys.length === rightKeys.length
    && leftKeys.every((key, index) => (
      key === rightKeys[index]
      && jsonEqual(left[key], right[key], depth + 1)
    ));
}

function isUiResourceUri(value: unknown): value is string {
  return typeof value === 'string'
    && value.length > 5
    && value.length <= 2048
    && value.startsWith('ui://')
    && !/\s/.test(value)
    && [...value].every((character) => character.codePointAt(0)! >= 0x20);
}

export function parseSavedMcpAppToolCall({
  mcpAppResult,
  output,
  toolName,
  toolCallId,
  input,
}: {
  mcpAppResult?: unknown;
  output: unknown;
  toolName: string;
  toolCallId: string;
  input: unknown;
}): SavedMcpAppToolCall | null {
  if (!isRecord(mcpAppResult)) return null;
  if (Object.keys(mcpAppResult).sort().join('\u0000') !== PROJECTION_KEYS.join('\u0000')) return null;
  const projectedToolName = mcpAppResult.toolName;
  const serverRef = mcpAppResult.serverRef;
  const projectedCallId = mcpAppResult.toolCallId;
  const projectedInput = mcpAppResult.input;
  const workspaceScope = mcpAppResult.workspaceScope;
  const result = mcpAppResult.result;
  const resourceUri = mcpAppResult.resourceUri;
  if (mcpAppResult.version !== 1 || typeof serverRef !== 'string' || !SERVER_REF.test(serverRef)) return null;
  if (typeof projectedToolName !== 'string' || !projectedToolName || projectedToolName.length > 512) return null;
  if (workspaceScope !== null && (typeof workspaceScope !== 'string' || !SERVER_REF.test(workspaceScope))) return null;
  if (typeof projectedCallId !== 'string' || !projectedCallId || projectedCallId !== toolCallId) return null;
  if (!isRecord(projectedInput) || !jsonEqual(projectedInput, input)) return null;
  if (!isRecord(result) || !Array.isArray(result.content) || !jsonEqual(result, output)) return null;
  if ('isError' in result && result.isError !== false) return null;
  if (!isUiResourceUri(resourceUri) || !isSafeJsonValue(mcpAppResult)) return null;
  if (toolName !== projectedToolName && toolName !== `mcp__${serverRef}__${projectedToolName}`) return null;
  return Object.freeze({
    serverRef,
    resourceUri,
    toolName: projectedToolName,
    toolCallId: projectedCallId,
    input: Object.freeze({ ...projectedInput }),
    workspaceScope,
    result: result as CallToolResult,
  });
}
