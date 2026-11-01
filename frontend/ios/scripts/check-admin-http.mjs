// [Input] Original iOS Admin fetch adapter, synthetic native binding and Request/AbortSignal contracts.
// [Output] Provider-free routing, DTO response, cancellation and fail-closed diagnostics.
// [Pos] iOS Admin HTTP script check; Swift/C++ ABI and real Admin remain separately qualified.
// [Sync] 2026-10-31: add native Admin HTTP provider-free contract coverage without network calls.
// [Sync] 2026-10-31: verify quiet successful calls and failure/recovery phase logs without synthetic credentials or content.
// [Sync] 2026-11-01: distinguish caller deadline from ordinary cancellation at the native boundary.
import assert from 'node:assert/strict';

const { installIOSAdminHTTP } = await import(new URL('../runtime/ios-admin-http.mjs', import.meta.url));
const originalFetch = globalThis.fetch;
const env = {
  INK_ADMIN_DREAM_TRANSPORT_BASE_URL: 'https://admin.example',
  INK_ADMIN_DREAM_TIMEOUT_SECONDS: '3',
  INK_ADMIN_DREAM_MAX_RESPONSE_BYTES: '4',
};
const b64 = (value) => Buffer.from(value).toString('base64');
const calls = [];
const callbacks = new Map();
const cancelled = [];
let nextHandle = 0;

function fakeBinding() {
  return {
    adminHTTP(packet, callback) {
      const handle = `handle-${++nextHandle}`;
      calls.push({ handle, packet: JSON.parse(packet) });
      callbacks.set(handle, callback);
      return handle;
    },
    cancelAdminHTTP(handle, timedOut) {
      cancelled.push({handle, timedOut});
      callbacks.get(handle)?.(JSON.stringify({ ok: false, error: 'cancelled' }));
    },
  };
}

function result(status, body, headers = { 'content-type': 'application/json' }) {
  return JSON.stringify({ ok: true, status, headers, bodyBase64: b64(body) });
}

async function reset() {
  globalThis.fetch = originalFetch;
  calls.length = 0;
  callbacks.clear();
  cancelled.length = 0;
  nextHandle = 0;
}

const failures = [];
const pass = [];
async function check(name, fn) {
  try {
    await reset();
    await fn();
    pass.push(name);
  } catch (error) {
    failures.push({ name, error: String(error?.stack || error) });
  } finally {
    await reset();
  }
}

await check('normal JSON/headers/body/Retry-After', async () => {
  const binding = fakeBinding();
  installIOSAdminHTTP(env, binding);
  const request = new Request('https://admin.example/api/internal/dream/v1/fixture', {
    method: 'POST', headers: { 'x-request-id': 'req_1' }, body: 'payload',
  });
  const pending = fetch(request, { redirect: 'manual' });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(calls.length, 1);
  assert.equal(calls[0].packet.method, 'POST');
  assert.equal(calls[0].packet.url, request.url);
  assert.equal(calls[0].packet.bodyBase64, b64('payload'));
  assert.equal(calls[0].packet.timeoutSeconds, 3);
  assert.equal(calls[0].packet.maxResponseBytes, 4);
  callbacks.get(calls[0].handle)(result(429, '{"ok":true}', { 'content-type': 'application/json', 'retry-after': '2' }));
  const response = await pending;
  assert.equal(response.status, 429);
  assert.equal(response.headers.get('retry-after'), '2');
  assert.deepEqual(await response.json(), { ok: true });
  assert.equal(response.url, request.url);
});

await check('Gateway/SSE and auth paths use native transport', async () => {
  const binding = fakeBinding();
  installIOSAdminHTTP(env, binding);
  const paths = ['/api/internal/dream/v1/events', '/api/auth/oauth2/token', '/api/auth/jwks'];
  const pending = paths.map((path) => fetch(`https://admin.example${path}`, { redirect: 'manual' }));
  assert.equal(calls.length, 3);
  for (const call of calls) callbacks.get(call.handle)(result(200, '{}', { 'content-type': 'text/event-stream' }));
  const responses = await Promise.all(pending);
  assert.deepEqual(responses.map((response) => response.status), [200, 200, 200]);
});

await check('other origin and non-manual Request preserve original body', async () => {
  const fallbackCalls = [];
  const fallback = async (input, init) => {
    fallbackCalls.push({ input, init, bodyUsed: input instanceof Request ? input.bodyUsed : undefined });
    return new Response('fallback', { status: 200 });
  };
  globalThis.fetch = fallback;
  installIOSAdminHTTP(env, fakeBinding());
  const other = new Request('https://other.example/api/internal/dream/v1/fixture', { method: 'POST', body: 'other-body' });
  const sameNonManual = new Request('https://admin.example/api/internal/dream/v1/fixture', { method: 'POST', body: 'same-body' });
  assert.equal((await fetch(other, { redirect: 'manual' })).status, 200);
  assert.equal((await fetch(sameNonManual, { redirect: 'follow' })).status, 200);
  assert.equal(calls.length, 0);
  assert.equal(fallbackCalls.length, 2);
  assert.equal(fallbackCalls[0].input, other);
  assert.equal(fallbackCalls[0].bodyUsed, false);
  assert.equal(fallbackCalls[1].input, sameNonManual);
  assert.equal(fallbackCalls[1].bodyUsed, false);
});

await check('abort cancels only the current native handle', async () => {
  const binding = fakeBinding();
  installIOSAdminHTTP(env, binding);
  const firstController = new AbortController();
  const secondController = new AbortController();
  const first = fetch('https://admin.example/api/internal/dream/v1/first', { redirect: 'manual', signal: firstController.signal });
  const second = fetch('https://admin.example/api/internal/dream/v1/second', { redirect: 'manual', signal: secondController.signal });
  assert.equal(calls.length, 2);
  firstController.abort('first-cancel');
  await assert.rejects(first);
  assert.deepEqual(cancelled, [{handle: calls[0].handle, timedOut: false}]);
  callbacks.get(calls[1].handle)(result(200, '{}'));
  assert.equal((await second).status, 200);
});

await check('caller timeout preserves its reason and flags native deadline', async () => {
  installIOSAdminHTTP(env, fakeBinding());
  const controller = new AbortController();
  const pending = fetch('https://admin.example/api/internal/dream/v1/fixture', {redirect: 'manual', signal: controller.signal});
  const reason = new DOMException('fixture deadline', 'TimeoutError');
  controller.abort(reason);
  await assert.rejects(pending, error => error === reason);
  assert.deepEqual(cancelled, [{handle: calls[0].handle, timedOut: true}]);
  assert.equal(calls.length, 1);
});

await check('bad native JSON/status/body fails closed', async () => {
  const binding = fakeBinding();
  installIOSAdminHTTP(env, binding);
  const malformed = fetch('https://admin.example/api/internal/dream/v1/malformed', { redirect: 'manual' });
  callbacks.get(calls[0].handle)('{');
  await assert.rejects(malformed);
  await reset();
  installIOSAdminHTTP(env, binding);
  const invalidStatus = fetch('https://admin.example/api/internal/dream/v1/status', { redirect: 'manual' });
  callbacks.get(calls[0].handle)(JSON.stringify({ ok: true, status: 99, headers: {}, bodyBase64: '' }));
  await assert.rejects(invalidStatus);
  await reset();
  installIOSAdminHTTP(env, binding);
  const invalidBody = fetch('https://admin.example/api/internal/dream/v1/body', { redirect: 'manual' });
  callbacks.get(calls[0].handle)(JSON.stringify({ ok: true, status: 200, headers: {}, bodyBase64: '%%%'}));
  await assert.rejects(invalidBody);
});

await check('missing native binding fails closed', async () => {
  assert.throws(() => installIOSAdminHTTP(env, {}), /IOS_ADMIN_HTTP_CONFIGURATION_INVALID/);
});

await check('diagnostics stay quiet on success and exclude request/response content', async () => {
  installIOSAdminHTTP(env, fakeBinding());
  const lines = [];
  const originalWrite = process.stderr.write;
  process.stderr.write = chunk => { lines.push(String(chunk)); return true; };
  try {
    for (const recoveryCount of [0, 1]) {
      lines.length = 0;
      const pending = fetch('https://admin.example/api/internal/dream/v1/browser-sessions/resolve?code=fixture-private-query', {
        method: 'POST', redirect: 'manual', headers: { authorization: 'Bearer fixture-private-credential', 'x-request-id': 'fixture-request' },
        body: 'fixture-private-request-body',
      });
      await new Promise(resolve => setImmediate(resolve));
      callbacks.get(calls.at(-1).handle)(JSON.stringify({ ...JSON.parse(result(200, 'fixture-private-response-body')), recoveryCount }));
      assert.equal(await (await pending).text(), 'fixture-private-response-body');
      if (recoveryCount === 0) assert.equal(lines.length, 0);
      else {
        const events = lines.join('').trim().split('\n').map(line => JSON.parse(line.slice('IOS_ADMIN_HTTP '.length)));
        assert.deepEqual(events.map(event => event.phase), ['selected-native', 'serialized', 'enqueued', 'native-callback', 'next-result']);
        assert.equal(events.at(-1).recoveryCount, 1);
      }
      assert.doesNotMatch(lines.join(''), /fixture-private|Bearer|authorization|bodyBase64/);
    }
    lines.length = 0;
    const pending = fetch('https://admin.example/api/internal/dream/v1/browser-sessions/resolve', { redirect: 'manual' });
    callbacks.get(calls.at(-1).handle)(JSON.stringify({ ok: false, error: 'transport' }));
    await assert.rejects(pending);
    assert.match(lines.join(''), /native-error/);
    assert.match(lines.join(''), /next-result/);
    assert.doesNotMatch(lines.join(''), /fixture-private|Bearer|authorization|bodyBase64/);
  } finally { process.stderr.write = originalWrite; }
});

console.log(JSON.stringify({
  passed: pass,
  failures,
  calls: calls.length,
  cancelledHandles: cancelled,
  networkRequests: 0,
  accountCredentialsUsed: false,
  modelCalls: 0,
}));
if (failures.length) process.exitCode = 1;
