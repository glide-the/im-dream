// [Sync] 2026-11-19: qualify startup via a private file without process-exported credentials.
// [Input] Production traced BFF factory with synthetic transports and a loopback OTLP receiver.
// [Output] Enabled-stream, abort, rejection and privacy contracts.
// [Pos] Deterministic Node test; no real Admin, database, user or model.
// [Sync] 2026-11-19: check OTLP protobuf and startup sampling.
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { once } from 'node:events';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { startTracing } from '../app/api/_trace.ts';
import { createApiProxy } from '../app/api/_auth/api-proxy.ts';
import { BffLoginBoundary } from '../app/api/_auth/login-boundary.ts';

test('enabled tracing keeps SSE first chunk, caller abort, rejection and metadata privacy', async () => {
  const batches: Buffer[] = [];
  const receiver = createServer((request, response) => {
    assert.equal(request.headers['content-type'], 'application/x-protobuf');
    const chunks: Buffer[] = [];
    request.on('data', chunk => { chunks.push(chunk); });
    request.on('end', () => { batches.push(Buffer.concat(chunks)); response.end(); });
  }).listen(0, '127.0.0.1');
  await once(receiver, 'listening');
  const address = receiver.address();
  assert.ok(address && typeof address !== 'string');
  const directory = mkdtempSync(join(tmpdir(), 'dream-trace-contract-'));
  const path = join(directory, 'private.env');
  delete process.env.INK_TRACE_ENABLED;
  process.env.INK_DREAM_WEB_TRACE_ENV_FILE = path;
  writeFileSync(path, `INK_TRACE_ENABLED=true\nINK_TRACE_CONTEXT_SECRET=${'synthetic-key-'.repeat(4)}\nOTEL_SERVICE_NAME=ink-memory-dream-web\nOTEL_TRACES_SAMPLER_ARG=1\nOTEL_BSP_SCHEDULE_DELAY=10\nOTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://127.0.0.1:${address.port}/v1/traces\nINK_TRACE_HOST_NAME=isolated-host\n`, { mode: 0o600 });
  try {
    await startTracing();
    const origin = 'https://dream.example';
    const boundary = new BffLoginBoundary({ publicOrigin: origin, callbackUri: origin + '/auth/callback', cookieSecret: 's'.repeat(32) });
    const admin = { resolve: async () => { throw Error('native must not resolve'); } };
    let calls = 0;
    let receivedSignal: AbortSignal | null | undefined;
    const encoder = new TextEncoder();
    const transport: typeof fetch = async (_input, init) => {
      calls++; receivedSignal = init?.signal;
      return new Response(new ReadableStream({ start(controller) {
        controller.enqueue(encoder.encode(': first\n\n'));
        init?.signal?.addEventListener('abort', () => controller.error(Error('synthetic-aborted')), { once: true });
      } }), { headers: { 'content-type': 'text/event-stream' } });
    };
    const abort = new AbortController();
    const request = new Request(origin + '/api/claude-agent/threads/private-thread/events?private-query=private-value', {
      headers: { authorization: 'Bearer private-token', traceparent: '00-' + 'a'.repeat(32) + '-' + 'b'.repeat(16) + '-01' }, signal: abort.signal });
    const response = await createApiProxy(boundary, admin, new URL('http://backend.example'), transport)(request);
    const reader = response.body!.getReader();
    assert.equal(new TextDecoder().decode((await reader.read()).value), ': first\n\n');
    assert.equal(response.headers.get('cache-control'), 'no-cache, no-transform');
    assert.notEqual(response.headers.get('x-trace-id'), 'a'.repeat(32));
    assert.equal(receivedSignal, request.signal);
    abort.abort();
    await assert.rejects(reader.read(), /synthetic-aborted/);
    assert.equal(calls, 1);
    const rejected = await createApiProxy(boundary, admin, new URL('http://backend.example'), transport)(new Request(origin + '/api/decks'));
    assert.equal(rejected.status, 401); assert.match(rejected.headers.get('x-trace-id')!, /^[a-f0-9]{32}$/);
    await rejected.text();
    const failed = await createApiProxy(boundary, admin, new URL('http://backend.example'), async () => { throw Error('private-transport-error'); })(
      new Request(origin + '/api/decks', { headers: { authorization: 'Bearer private-token' } }));
    assert.equal(failed.status, 502); await failed.text();
    const deadline = Date.now() + 3000;
    while (!Buffer.concat(batches).includes('dream.http') && Date.now() < deadline) await new Promise(resolve => setTimeout(resolve, 10));
    assert.ok(batches.length > 0);
    const serialized = Buffer.concat(batches).toString();
    assert.ok(serialized.includes('dream.startup.web.next'));
    assert.ok(serialized.includes('dream.http'));
    assert.ok(serialized.includes('ink-memory-dream-web-next'));
    assert.ok(serialized.includes('isolated-host'));
    for (const privateValue of ['private-query', 'private-value', 'private-token', 'private-thread', 'private-transport-error']) assert.ok(!serialized.includes(privateValue));
  } finally {
    rmSync(directory, { recursive: true });
    receiver.closeAllConnections();
    await new Promise<void>((resolve, reject) => receiver.close(error => error ? reject(error) : resolve()));
  }
});
