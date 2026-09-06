// [Input] Persisted ordinary tool fields plus optional McpAppsToolResultProjectionV1.
// [Output] Contract checks for strict, lossless, spoof-resistant MCP Apps recognition.
// [Pos] Focused result-identity/refresh boundary test; no Browser or network state.
// [Sync] 2026-09-06: require versioned workspace identity and preserve ordinary fallback on every rejection.
// [Sync] 2026-09-06: match the official data-only CallToolResult; the resource URI belongs to the trusted descriptor projection.
// [Sync] 2026-09-06: distinguish semantically identical history hydration from a changed saved call.

import assert from 'node:assert/strict';
import test from 'node:test';

import { parseSavedMcpAppToolCall, sameSavedMcpAppToolCall } from './result.ts';

function fixture() {
  const result = {
    content: [{ type: 'text', text: 'Read-only state: ready' }],
    structuredContent: { state: 'ready', callCount: 1 },
    extensionResult: { supported: true },
  };
  const projection = {
    version: 1,
    serverRef: 'official-basic',
    toolName: 'get-time',
    toolCallId: 'call-1',
    input: { requested: true },
    workspaceScope: 'workspace-1',
    resourceUri: 'ui://get-time/mcp-app.html',
    result,
  };
  return { result, projection };
}

test('consumes the versioned projection and preserves the complete CallToolResult', () => {
  const { result, projection } = fixture();
  const parsed = parseSavedMcpAppToolCall({
    mcpAppResult: projection,
    output: structuredClone(result),
    toolName: 'mcp__official-basic__get-time',
    toolCallId: 'call-1',
    input: { requested: true },
  });

  assert.ok(parsed);
  assert.deepEqual(parsed.result, result);
  assert.deepEqual(
    (parsed.result as unknown as Record<string, unknown>).extensionResult,
    { supported: true },
  );
  assert.equal(parsed.toolName, 'get-time');
  assert.deepEqual(parsed.input, { requested: true });
  assert.equal(parsed.workspaceScope, 'workspace-1');
});

test('treats cloned saved calls as the same identity but detects result changes', () => {
  const { result, projection } = fixture();
  const first = parseSavedMcpAppToolCall({
    mcpAppResult: projection,
    output: result,
    toolName: 'mcp__official-basic__get-time',
    toolCallId: 'call-1',
    input: { requested: true },
  });
  const clonedResult = structuredClone(result);
  const second = parseSavedMcpAppToolCall({
    mcpAppResult: structuredClone(projection),
    output: clonedResult,
    toolName: 'mcp__official-basic__get-time',
    toolCallId: 'call-1',
    input: { requested: true },
  });
  assert.ok(first && second);
  assert.equal(sameSavedMcpAppToolCall(first, second), true);
  const changed = {
    ...second,
    result: { ...second.result, structuredContent: { state: 'changed' } },
  };
  assert.equal(sameSavedMcpAppToolCall(first, changed), false);
});

test('never derives identity from spoofed ordinary output metadata', () => {
  const output = {
    content: [],
    _meta: {
      ui: {
        serverRef: 'attacker-server',
        resourceUri: 'ui://attacker/view.html',
      },
    },
  };
  assert.equal(parseSavedMcpAppToolCall({
    mcpAppResult: undefined,
    output,
    toolName: 'mcp__attacker-server__tool',
    toolCallId: 'call-spoof',
    input: {},
  }), null);
});

test('rejects unknown versions and every enclosing identity/result mismatch', () => {
  const mutations: Array<(projection: Record<string, unknown>) => void> = [
    (projection) => { projection.version = 2; },
    (projection) => { projection.serverRef = 'other'; },
    (projection) => { projection.toolName = 'other'; },
    (projection) => { projection.toolCallId = 'other'; },
    (projection) => { projection.input = { requested: false }; },
    (projection) => { projection.workspaceScope = '../foreign'; },
    (projection) => { projection.resourceUri = 'https://not-ui.invalid/app'; },
    (projection) => { projection.result = { content: [{ type: 'text', text: 'changed' }] }; },
    (projection) => { projection.extra = true; },
  ];
  for (const mutate of mutations) {
    const { result, projection } = fixture();
    mutate(projection as unknown as Record<string, unknown>);
    assert.equal(parseSavedMcpAppToolCall({
      mcpAppResult: projection,
      output: result,
      toolName: 'mcp__official-basic__get-time',
      toolCallId: 'call-1',
      input: { requested: true },
    }), null);
  }
});

test('rejects sensitive connection material while leaving ordinary output caller-owned', () => {
  const { result, projection } = fixture();
  const unsafeResult: Record<string, unknown> = {
    ...projection.result,
    _meta: { ...projection.result._meta, headers: { Authorization: 'Bearer secret' } },
  };
  (projection as unknown as Record<string, unknown>).result = unsafeResult;
  const ordinary = structuredClone(unsafeResult);
  assert.equal(parseSavedMcpAppToolCall({
    mcpAppResult: projection,
    output: ordinary,
    toolName: 'mcp__official-basic__get-time',
    toolCallId: 'call-1',
    input: { requested: true },
  }), null);
  const ordinaryMeta = ordinary._meta as Record<string, unknown>;
  const ordinaryHeaders = ordinaryMeta.headers as Record<string, unknown>;
  assert.equal(ordinaryHeaders.Authorization, 'Bearer secret');
  assert.equal(result.content[0].text, 'Read-only state: ready');
});

test('rejects an error result projection while leaving the ordinary error output caller-owned', () => {
  const { result, projection } = fixture();
  result.isError = true;
  assert.equal(parseSavedMcpAppToolCall({
    mcpAppResult: projection,
    output: result,
    toolName: 'mcp__official-basic__get-time',
    toolCallId: 'call-1',
    input: { requested: true },
  }), null);
  assert.equal(result.isError, true);
});
