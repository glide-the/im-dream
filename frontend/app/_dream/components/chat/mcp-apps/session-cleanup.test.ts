// [Input] Fake SDK transports covering successful termination, connect-aborted DELETE, and stalled recovery fetches.
// [Output] Deterministic assertions for fresh-signal standard DELETE and unconditional bounded local close.
// [Pos] Provider-free Browser cleanup unit test; it starts no service and contains no real credential.
// [Sync] 2026-09-06: reproduce SDK 1.30 connect-failure abort semantics without leaking a server session.

import assert from 'node:assert/strict';
import test from 'node:test';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';

import {
  cleanupFailedMcpAppsConnection,
  closeMcpAppsClientSession,
} from './session-cleanup.ts';

test('uses SDK termination on the normal path and always closes the client', async () => {
  let terminated = 0;
  let closed = 0;
  let fetched = 0;
  await closeMcpAppsClientSession({
    client: { async close() { closed += 1; } },
    transport: {
      sessionId: 'normal-session',
      async terminateSession() { terminated += 1; },
    },
    endpoint: new URL('https://ink.test/api/mcp-apps/server'),
    headers: { authorization: 'Bearer browser-token' },
    timeoutMs: 50,
    fetcher: async () => {
      fetched += 1;
      return new Response(null, { status: 200 });
    },
  });
  assert.equal(terminated, 1);
  assert.equal(fetched, 0);
  assert.equal(closed, 1);
});

test('recovers a connect-aborted SDK transport with a fresh-signal standard DELETE', async () => {
  let closed = 0;
  const requests: Request[] = [];
  await closeMcpAppsClientSession({
    client: { async close() { closed += 1; } },
    transport: {
      sessionId: 'leaked-session',
      protocolVersion: '2025-11-25',
      async terminateSession() { throw new DOMException('aborted', 'AbortError'); },
    },
    endpoint: new URL('https://ink.test/api/mcp-apps/server'),
    headers: {
      authorization: 'Bearer browser-token',
      'x-ink-mcp-apps-browser-session': 'browser-scope',
    },
    timeoutMs: 50,
    fetcher: async (url, init) => {
      const request = new Request(url, init);
      requests.push(request);
      assert.equal(request.signal.aborted, false);
      return new Response(null, { status: 200 });
    },
  });
  assert.equal(requests.length, 1);
  assert.equal(requests[0]?.method, 'DELETE');
  assert.equal(requests[0]?.headers.get('mcp-session-id'), 'leaked-session');
  assert.equal(requests[0]?.headers.get('mcp-protocol-version'), '2025-11-25');
  assert.equal(requests[0]?.headers.get('authorization'), 'Bearer browser-token');
  assert.equal(closed, 1);
});

test('recovers the real SDK 1.30 session assigned before initialize validation fails', async () => {
  const endpoint = new URL('https://ink.test/api/mcp-apps/server');
  const deletes: boolean[] = [];
  const fetcher = async (_url: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    if (init?.method === 'DELETE') {
      deletes.push(init.signal?.aborted === true);
      if (init.signal?.aborted) throw new DOMException('aborted', 'AbortError');
      return new Response(null, { status: 200 });
    }
    const request = JSON.parse(String(init?.body)) as { id: string | number };
    return new Response(JSON.stringify({
      jsonrpc: '2.0',
      id: request.id,
      result: {
        protocolVersion: 'unsupported-version',
        capabilities: {},
        serverInfo: { name: 'invalid-initialize-server', version: '1.0.0' },
      },
    }), {
      status: 200,
      headers: {
        'content-type': 'application/json',
        'mcp-session-id': 'sdk-assigned-session',
      },
    });
  };
  const transport = new StreamableHTTPClientTransport(endpoint, {
    fetch: fetcher,
    requestInit: { headers: { authorization: 'Bearer browser-token' } },
  });
  const client = new Client({ name: 'cleanup-regression', version: '1.0.0' });

  await assert.rejects(client.connect(transport), /protocol version is not supported/i);
  assert.equal(transport.sessionId, 'sdk-assigned-session');
  await closeMcpAppsClientSession({
    client,
    transport,
    endpoint,
    headers: { authorization: 'Bearer browser-token' },
    timeoutMs: 50,
    fetcher,
  });

  assert.deepEqual(deletes, [true, false]);
});

test('aborts a stalled recovery DELETE and still closes the client', async () => {
  let closed = 0;
  await closeMcpAppsClientSession({
    client: { async close() { closed += 1; } },
    transport: {
      sessionId: 'stalled-session',
      async terminateSession() { throw new Error('transport already closed'); },
    },
    endpoint: new URL('https://ink.test/api/mcp-apps/server'),
    headers: {},
    timeoutMs: 5,
    fetcher: async (_url, init) => await new Promise<Response>((_resolve, reject) => {
      init?.signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')));
    }),
  });
  assert.equal(closed, 1);
});

test('does not report an obsolete failure after cleanup crosses a lifecycle switch', async () => {
  let active = true;
  let finishCleanup: (() => void) | null = null;
  let reports = 0;
  const cleanup = new Promise<void>((resolve) => { finishCleanup = resolve; });
  const handling = cleanupFailedMcpAppsConnection({
    cleanup: async () => await cleanup,
    isActive: () => active,
    report: () => { reports += 1; },
  });

  active = false;
  finishCleanup?.();
  await handling;

  assert.equal(reports, 0);
});
