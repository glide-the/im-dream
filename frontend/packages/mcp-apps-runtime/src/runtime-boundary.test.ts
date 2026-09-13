// [Input] Untrusted same-origin route requests with no configured upstream Runtime.
// [Output] Pre-composition rejection, public-Host origin validation, and canonical colon-bearing serverRef acceptance/path rejection.
// [Pos] task_411-02 thin-route security test; rejected requests cannot create an upstream connector.
// [Sync] 2026-09-06: align route selectors with canonical managed-server keys while rejecting paths.
// [Sync] 2026-09-06: cover the Next internal-host/public-Host same-origin boundary.
// [Sync] 2026-09-13: cover public-origin reuse for dynamic sandbox binding and invalid Host rejection.

import assert from 'node:assert/strict';
import test from 'node:test';

import { normalizeServerRef } from './contracts.ts';
import { closeMcpAppsRuntime, handleMcpAppsRequest, publicRequestOrigin, requestHasSameOrigin } from './runtime.ts';

const origin = 'https://ink-memory.invalid';

async function rejected(request: Request, serverRef = 'official-basic') {
  const response = await handleMcpAppsRequest(request, serverRef);
  assert.equal(globalThis.__inkDreamMcpAppsRuntime, undefined);
  return response;
}

test('rejects disabled preview before composing the process Runtime', async () => {
  const previous = process.env.INK_MCP_APPS_PHASE1_PREVIEW;
  delete process.env.INK_MCP_APPS_PHASE1_PREVIEW;
  try {
    assert.equal((await rejected(new Request(`${origin}/api/mcp-apps/official-basic`, {
      method: 'POST',
      headers: { authorization: 'Bearer test-only' },
    }))).status, 404);
  } finally {
    if (previous === undefined) delete process.env.INK_MCP_APPS_PHASE1_PREVIEW;
    else process.env.INK_MCP_APPS_PHASE1_PREVIEW = previous;
    await closeMcpAppsRuntime();
  }
});

test('sandbox parent origin follows the public frontend Host, protocol and port', () => {
  assert.equal(publicRequestOrigin(new Request('http://127.0.0.1:5173/mcp-apps-sandbox', {
    headers: { host: 'localhost:41827' },
  })), 'http://localhost:41827');
  assert.equal(publicRequestOrigin(new Request('http://127.0.0.1:5173/mcp-apps-sandbox', {
    headers: { host: 'dream.example.test', 'x-forwarded-proto': 'https' },
  })), 'https://dream.example.test');
  assert.equal(publicRequestOrigin(new Request('https://dream.example.test/mcp-apps-sandbox')), 'https://dream.example.test');
  assert.equal(publicRequestOrigin(new Request('http://127.0.0.1:5173/mcp-apps-sandbox', {
    headers: { host: 'name@other.example.test' },
  })), null);
});

test('rejects origin, query, authentication, and serverRef violations before upstream composition', async () => {
  const previous = process.env.INK_MCP_APPS_PHASE1_PREVIEW;
  process.env.INK_MCP_APPS_PHASE1_PREVIEW = 'true';
  try {
    assert.equal((await rejected(new Request(`${origin}/api/mcp-apps/official-basic`, {
      method: 'POST',
      headers: { origin: 'https://other.invalid', authorization: 'Bearer test-only' },
    }))).status, 403);
    assert.equal((await rejected(new Request(`${origin}/api/mcp-apps/official-basic?url=https://upstream.invalid`, {
      method: 'POST',
      headers: { authorization: 'Bearer test-only' },
    }))).status, 400);
    assert.equal((await rejected(new Request(`${origin}/api/mcp-apps/official-basic`, { method: 'POST' }))).status, 401);
    assert.equal((await rejected(new Request(`${origin}/api/mcp-apps/not-valid`, {
      method: 'POST',
      headers: { authorization: 'Bearer test-only' },
    }), '../not-valid')).status, 400);
  } finally {
    if (previous === undefined) delete process.env.INK_MCP_APPS_PHASE1_PREVIEW;
    else process.env.INK_MCP_APPS_PHASE1_PREVIEW = previous;
    await closeMcpAppsRuntime();
  }
});

test('accepts canonical colon-bearing server refs and rejects path-shaped selectors', () => {
  assert.equal(normalizeServerRef('official:basic-v1'), 'official:basic-v1');
  for (const candidate of ['official/basic', '../official-basic', 'official%2Fbasic']) {
    assert.throws(() => normalizeServerRef(candidate), /server selector is invalid/i);
  }
});

test('accepts the public Host when Next canonicalizes its internal request URL', () => {
  assert.equal(requestHasSameOrigin(new Request(
    'http://localhost:5173/api/mcp-apps/official-basic',
    { headers: { host: '127.0.0.1:5173', origin: 'http://127.0.0.1:5173' } },
  )), true);
  assert.equal(requestHasSameOrigin(new Request(
    'http://localhost:5173/api/mcp-apps/official-basic',
    { headers: { host: '127.0.0.1:5173', origin: 'https://other.invalid' } },
  )), false);
});
