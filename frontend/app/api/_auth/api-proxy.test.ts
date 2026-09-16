// [Input] Actual API credential owner/shared stream transport with explicit fake Admin/backend providers.
// [Output] Cookie precedence, CSRF/origin, header/query isolation, SSE flush and caller-abort contracts.
// [Pos] Provider-free technical tests; no external HTTP, database, account or model calls.
// [Sync] 2026-09-17: prove Browser traffic cannot inject or receive the private service OAuth bearer.
import assert from 'node:assert/strict';
import test from 'node:test';
import { createApiProxy } from './api-proxy.ts';
import { BffLoginBoundary } from './login-boundary.ts';

const publicOrigin = 'https://dream.example';
const handle = 'dbr_' + 'h'.repeat(43);
function fixture() {
  const boundary = new BffLoginBoundary({ publicOrigin, callbackUri: publicOrigin + '/auth/callback', cookieSecret: 's'.repeat(32) });
  const resolves: string[] = [];
  const admin = { resolve: async (value: string) => {
    resolves.push(value);
    return { access_token: 'resolved.admin.token', expires_at: '2026-09-14T12:00:00Z', principal: { subject: 'opaque', canonical_user_id: '42', client_id: 'browser', scopes: ['dream:read', 'dream:write'], status: 'active' as const } };
  } };
  const calls: { url: string; init: RequestInit }[] = [];
  const transport: typeof fetch = async (url, init) => {
    calls.push({ url: String(url), init: init! });
    return new Response('body', { headers: { 'content-type': 'text/plain', 'set-cookie': 'private=secret', 'x-new-access-token': 'secret', 'x-ink-dream-credential': 'secret', 'x-ink-dream-service-authorization': 'Bearer leaked', 'cache-control': 'private, max-age=600', 'content-encoding': 'identity' } });
  };
  return { boundary, resolves, calls, admin, proxy: createApiProxy(boundary, admin, new URL('http://backend.example'), transport) };
}

test('Browser handle takes precedence and strips credential/actor/proxy headers', async () => {
  const { boundary, proxy, calls, resolves } = fixture();
  const response = await proxy(new Request(publicOrigin + '/api/storage/file/key?download=1', { headers: {
    cookie: boundary.handleCookieName + '=' + handle + '; other=private', authorization: 'Bearer attacker',
    'x-ink-dream-service': 'attacker', 'x-ink-dream-credential': 'secret', 'x-ink-dream-service-authorization': 'Bearer attacker', 'x-user-id': '7', 'x-auth-user': '7',
    'x-forwarded-host': 'evil.example', connection: 'x-custom-hop', 'x-custom-hop': 'private',
  } }));
  assert.equal(response.status, 200); assert.deepEqual(resolves, [handle]);
  const headers = new Headers(calls[0].init.headers);
  assert.equal(headers.get('authorization'), 'Bearer resolved.admin.token');
  for (const key of ['cookie', 'x-ink-dream-service', 'x-ink-dream-credential', 'x-ink-dream-service-authorization', 'x-user-id', 'x-auth-user', 'x-forwarded-host', 'connection', 'x-custom-hop']) assert.equal(headers.get(key), null);
  assert.equal(headers.get('accept-encoding'), 'identity');
  assert.equal(calls[0].url, 'http://backend.example/api/storage/file/key?download=1');
  assert.equal(response.headers.get('cache-control'), 'no-store');
  for (const key of ['set-cookie', 'x-new-access-token', 'x-ink-dream-credential', 'x-ink-dream-service-authorization', 'content-encoding']) assert.equal(response.headers.get(key), null);
});

test('invalid, empty and duplicate Browser cookies never fall back to explicit Bearer', async () => {
  for (const value of ['invalid', '', handle + '; __Host-ink-dream-browser=' + handle]) {
    const { boundary, proxy, calls, resolves } = fixture();
    const response = await proxy(new Request(publicOrigin + '/api/me', { headers: { cookie: boundary.handleCookieName + '=' + value, authorization: 'Bearer native.token' } }));
    assert.equal(response.status, 401); assert.equal(calls.length, 0); assert.equal(resolves.length, 0);
  }
});

test('Browser mutation requires exact Origin and handle-bound CSRF before resolve/body forwarding', async () => {
  const { boundary, proxy, calls, resolves } = fixture();
  const base = { cookie: boundary.handleCookieName + '=' + handle, 'content-type': 'application/json' };
  for (const headers of [base, { ...base, origin: publicOrigin }, { ...base, origin: 'https://evil.example', 'x-ink-csrf': boundary.csrfToken(handle) }]) {
    assert.equal((await proxy(new Request(publicOrigin + '/api/claude-agent', { method: 'POST', headers, body: '{}' }))).status, 403);
  }
  assert.equal(resolves.length, 0); assert.equal(calls.length, 0);
  const response = await proxy(new Request(publicOrigin + '/api/claude-agent', { method: 'POST', headers: { ...base, origin: publicOrigin, 'x-ink-csrf': boundary.csrfToken(handle) }, body: '{"id":"thread"}' }));
  assert.equal(response.status, 200);
  assert.equal(await new Response(calls[0].init.body).text(), '{"id":"thread"}');
  assert.equal(new Headers(calls[0].init.headers).get('x-ink-csrf'), null);
});

test('native OAuth Bearer has no Browser CSRF requirement or ambient Cookie forwarding', async () => {
  const { proxy, calls, resolves } = fixture();
  const response = await proxy(new Request(publicOrigin + '/api/claude-agent', { method: 'POST', headers: { authorization: 'Bearer native.oauth.token', cookie: 'unrelated=private' }, body: 'body' }));
  assert.equal(response.status, 200); assert.equal(resolves.length, 0);
  const headers = new Headers(calls[0].init.headers);
  assert.equal(headers.get('authorization'), 'Bearer native.oauth.token'); assert.equal(headers.get('cookie'), null);
});

test('missing auth, foreign Origin, credential queries and foreign path fail before backend', async () => {
  const { proxy, calls } = fixture();
  const requests: [Request, number][] = [
    [new Request(publicOrigin + '/api/me'), 401],
    [new Request(publicOrigin + '/api/me', { headers: { authorization: 'Bearer token', origin: 'https://evil.example' } }), 403],
    [new Request(publicOrigin + '/api/me?token=private', { headers: { authorization: 'Bearer token' } }), 400],
    [new Request(publicOrigin + '/api/me?access_token=private', { headers: { authorization: 'Bearer token' } }), 400],
    [new Request(publicOrigin + '/auth/other', { headers: { authorization: 'Bearer token' } }), 400],
  ];
  for (const [request, status] of requests) assert.equal((await proxy(request)).status, status);
  assert.equal(calls.length, 0);
});

test('SSE forwards first chunk before EOF and propagates caller abort without retry', async () => {
  const { boundary, admin } = fixture();
  let controller!: ReadableStreamDefaultController<Uint8Array>;
  let calls = 0; let signal: AbortSignal | undefined;
  const transport: typeof fetch = async (_url, init) => {
    calls++; signal = init?.signal ?? undefined;
    const stream = new ReadableStream<Uint8Array>({ start(value) {
      controller = value; controller.enqueue(new TextEncoder().encode(': first\n\n'));
      signal?.addEventListener('abort', () => value.error(new Error('aborted')), { once: true });
    } });
    return new Response(stream, { headers: { 'content-type': 'text/event-stream', 'cache-control': 'max-age=300', 'x-accel-buffering': 'yes' } });
  };
  const abort = new AbortController();
  const request = new Request(publicOrigin + '/api/claude-agent/threads/thread/stream', { headers: { authorization: 'Bearer native.token' }, signal: abort.signal });
  const response = await createApiProxy(boundary, admin, new URL('http://backend.example'), transport)(request);
  const reader = response.body!.getReader();
  assert.equal(new TextDecoder().decode((await reader.read()).value), ': first\n\n');
  assert.equal(response.headers.get('cache-control'), 'no-cache, no-transform'); assert.equal(response.headers.get('x-accel-buffering'), 'no');
  assert.equal(signal, request.signal); abort.abort();
  await assert.rejects(reader.read(), /aborted/); assert.equal(calls, 1); assert.ok(controller);
});

test('upstream transport failure returns safe502 without retry or error details', async () => {
  const { boundary, admin } = fixture(); let calls = 0;
  const response = await createApiProxy(boundary, admin, new URL('http://backend.example'), async () => { calls++; throw new Error('secret sql'); })(new Request(publicOrigin + '/api/me', { headers: { authorization: 'Bearer native.token' } }));
  assert.equal(response.status, 502); assert.equal(calls, 1); assert.ok(!(await response.text()).includes('secret'));
});
