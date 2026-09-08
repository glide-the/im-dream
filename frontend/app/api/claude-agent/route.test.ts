// [Input] The production Claude Agent Route Handler and a test-owned streaming Python-shaped server.
// [Output] Deterministic proof of immediate SSE flush, request fidelity, and fail-closed configuration.
// [Pos] Provider-free transport contract for the Next-to-Python Claude Agent boundary.
// [Sync] 2026-09-06: cover reconnect GET and turn POST without a model, database, or browser.
// [Sync] 2026-09-07: make test-server cleanup idempotent after streamed-request teardown.

import assert from 'node:assert/strict';
import { createServer, type Server } from 'node:http';
import test from 'node:test';
import { proxyClaudeAgentRequest } from './_proxy.ts';

async function listen(server: Server): Promise<string> {
  await new Promise<void>((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  const address = server.address();
  assert(address && typeof address !== 'string');
  return `http://127.0.0.1:${address.port}`;
}

async function close(server: Server): Promise<void> {
  if (!server.listening) return;
  await new Promise<void>((resolve, reject) => {
    server.close((error) => error ? reject(error) : resolve());
  });
}

async function within<T>(promise: Promise<T>, timeoutMs: number): Promise<T> {
  let timer: NodeJS.Timeout | undefined;
  try {
    return await Promise.race([
      promise,
      new Promise<never>((_, reject) => {
        timer = setTimeout(
          () => reject(new Error(`Timed out after ${timeoutMs}ms waiting for a streamed response.`)),
          timeoutMs,
        );
      }),
    ]);
  } finally {
    if (timer) clearTimeout(timer);
  }
}

test('Claude Agent Route Handler streams reconnect GET before upstream completion and forwards POST', async () => {
  let releaseReconnect: (() => void) | undefined;
  const reconnectReleased = new Promise<void>((resolve) => { releaseReconnect = resolve; });
  let reconnectCompleted = false;
  const requests: Array<{
    method: string;
    path: string;
    authorization?: string;
    acceptEncoding?: string;
    body: string;
  }> = [];
  const server = createServer(async (request, response) => {
    let body = '';
    for await (const chunk of request) body += Buffer.from(chunk).toString('utf8');
    requests.push({
      method: request.method ?? '',
      path: request.url ?? '',
      authorization: request.headers.authorization,
      acceptEncoding: request.headers['accept-encoding'],
      body,
    });
    response.writeHead(200, {
      'Content-Type': 'text/event-stream; charset=utf-8',
      'Cache-Control': 'private, max-age=600',
      'Content-Encoding': 'identity',
      'X-Accel-Buffering': 'yes',
    });
    response.flushHeaders();
    if (request.method === 'GET') {
      response.write(': reconnect-ready\n\n');
      await reconnectReleased;
      reconnectCompleted = true;
      response.end('data: {"type":"finish","finishReason":"stop"}\n\n');
      return;
    }
    response.end(': post-ready\n\n');
  });

  const previousInternal = process.env.INK_BACKEND_INTERNAL_URL;
  const previousFallback = process.env.BACKEND_URL;
  try {
    process.env.INK_BACKEND_INTERNAL_URL = await listen(server);
    delete process.env.BACKEND_URL;

    const reconnectResponse = await within(proxyClaudeAgentRequest(new Request(
      'https://frontend.example/api/claude-agent/threads/thread-1/stream?cursor=event-7',
      { headers: { authorization: 'Bearer route-test-token' } },
    )), 1_000);
    assert.equal(reconnectResponse.status, 200);
    assert.equal(reconnectResponse.headers.get('content-type'), 'text/event-stream; charset=utf-8');
    assert.equal(reconnectResponse.headers.get('cache-control'), 'no-cache, no-transform');
    assert.equal(reconnectResponse.headers.get('x-accel-buffering'), 'no');
    assert.equal(reconnectResponse.headers.has('content-encoding'), false);
    const reader = reconnectResponse.body?.getReader();
    assert(reader);
    const firstChunk = await within(reader.read(), 1_000);
    assert.equal(new TextDecoder().decode(firstChunk.value), ': reconnect-ready\n\n');
    assert.equal(reconnectCompleted, false, 'the proxy must not wait for upstream EOF');
    releaseReconnect?.();
    const terminalChunk = await within(reader.read(), 1_000);
    assert.match(new TextDecoder().decode(terminalChunk.value), /"type":"finish"/);
    await within(reader.read(), 1_000);

    const postResponse = await within(proxyClaudeAgentRequest(new Request(
      'https://frontend.example/api/claude-agent',
      {
        method: 'POST',
        headers: {
          authorization: 'Bearer route-test-token',
          'content-type': 'application/json',
        },
        body: JSON.stringify({ id: 'thread-1', reconnect: false }),
      },
    )), 1_000);
    assert.equal(postResponse.status, 200);
    assert.equal(await postResponse.text(), ': post-ready\n\n');

    assert.deepEqual(requests, [
      {
        method: 'GET',
        path: '/api/claude-agent/threads/thread-1/stream?cursor=event-7',
        authorization: 'Bearer route-test-token',
        acceptEncoding: 'identity',
        body: '',
      },
      {
        method: 'POST',
        path: '/api/claude-agent',
        authorization: 'Bearer route-test-token',
        acceptEncoding: 'identity',
        body: '{"id":"thread-1","reconnect":false}',
      },
    ]);
  } finally {
    if (previousInternal === undefined) delete process.env.INK_BACKEND_INTERNAL_URL;
    else process.env.INK_BACKEND_INTERNAL_URL = previousInternal;
    if (previousFallback === undefined) delete process.env.BACKEND_URL;
    else process.env.BACKEND_URL = previousFallback;
    releaseReconnect?.();
    await close(server);
  }
});

test('Claude Agent Route Handler fails closed without a backend origin', async () => {
  const previousInternal = process.env.INK_BACKEND_INTERNAL_URL;
  const previousFallback = process.env.BACKEND_URL;
  try {
    delete process.env.INK_BACKEND_INTERNAL_URL;
    delete process.env.BACKEND_URL;
    const response = await proxyClaudeAgentRequest(new Request(
      'https://frontend.example/api/claude-agent/threads/thread-1/status',
    ));
    assert.equal(response.status, 503);
    assert.match(await response.text(), /not configured/);
  } finally {
    if (previousInternal === undefined) delete process.env.INK_BACKEND_INTERNAL_URL;
    else process.env.INK_BACKEND_INTERNAL_URL = previousInternal;
    if (previousFallback === undefined) delete process.env.BACKEND_URL;
    else process.env.BACKEND_URL = previousFallback;
  }
});
