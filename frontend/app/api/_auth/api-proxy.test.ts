// [Input] Actual API credential owner/shared stream transport with explicit fake Admin/backend providers.
// [Output] Cookie precedence, CSRF/origin, header/query isolation, SSE flush and caller-abort contracts.
// [Pos] Provider-free technical tests; no external HTTP, database, account or model calls.
// [Sync] 2026-09-17: prove Browser traffic cannot inject or receive the private service OAuth bearer.
// [Sync] 2026-10-13: long source preparation keeps caller abort/body/header isolation and uses only the create dispatcher.
// [Sync] 2026-10-13: definite pre-create Notion 401 renews one Browser handle
//                    and replays the same body/key, while unknown/committed/native
//                    and incomplete selections never retry.
// [Sync] 2026-10-13: loopback Undici transport reproduces GET SSE body timeout after
//                    an initial connected chunk while preserving non-SSE and abort semantics.
import { createServer } from 'node:http';
import { Agent, fetch as undiciFetch } from 'undici';
import assert from 'node:assert/strict';
import test from 'node:test';
import { createApiProxy } from './api-proxy.ts';
import { BffLoginBoundary } from './login-boundary.ts';
import { forwardBackendRequest } from '../_http-proxy.ts';

const publicOrigin = 'https://dream.example';
const handle = 'dbr_' + 'h'.repeat(43);
const loopbackPort = 55177;
const eventTaskId = '123e4567-e89b-42d3-a456-426614174000';

type DispatcherRequestInit = RequestInit & { dispatcher?: unknown };

function installedUndiciFetch(url: URL | RequestInfo, init?: DispatcherRequestInit): Promise<Response> {
  const target = typeof url === 'string' ? url : url instanceof URL ? url.toString() : url.url;
  return undiciFetch(target, init as never) as unknown as Promise<Response>;
}

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

test('only task creation receives the preparation dispatcher after Browser CSRF validation', async () => {
  const { boundary, proxy, calls } = fixture();
  const headers = { cookie: boundary.handleCookieName + '=' + handle, origin: publicOrigin,
    'x-ink-csrf': boundary.csrfToken(handle), 'content-type': 'application/json' };
  const abort = new AbortController();
  const request = new Request(publicOrigin + '/api/reflections/tasks', { method: 'POST', headers,
    body: '{"analysis_content":{"include_notion":true}}', signal: abort.signal });
  assert.equal((await proxy(request)).status, 200);
  const create = calls[0].init as RequestInit & { dispatcher?: unknown };
  assert.ok(create.dispatcher);
  assert.equal(create.signal, request.signal);
  assert.equal(await new Response(create.body).text(), '{"analysis_content":{"include_notion":true}}');
  assert.equal(new Headers(create.headers).get('cookie'), null);
  await proxy(new Request(publicOrigin + '/api/reflections/tasks/task-id/start', { method: 'POST', headers, body: '{}' }));
  await proxy(new Request(publicOrigin + '/api/reflections/tasks', { headers: { authorization: 'Bearer native.token' } }));
  assert.equal((calls[1].init as typeof create).dispatcher, undefined);
  assert.equal((calls[2].init as typeof create).dispatcher, undefined);
  const invalid = new Request(publicOrigin + '/api/reflections/tasks', { method: 'POST', headers: { cookie: headers.cookie }, body: '{}' });
  assert.equal((await proxy(invalid)).status, 403);
  assert.equal(calls.length, 3);
});

test('production GET events dispatcher survives sparse SSE while invalid and adjacent routes keep default timeout and abort', async () => {
  const forwardedHeaders: Array<{ authorization: string | undefined; cookie: string | undefined; encoding: string | undefined }> = [];
  const server = createServer((request, response) => {
    const path = request.url?.split('?')[0];
    forwardedHeaders.push({
      authorization: request.headers.authorization,
      cookie: request.headers.cookie,
      encoding: request.headers['accept-encoding'],
    });
    if (path === `/api/reflections/tasks/${eventTaskId}/events`) {
      response.writeHead(200, { 'content-type': 'text/event-stream' });
      response.write(': connected\n\n');
      const timer = setTimeout(() => response.end('event: terminal\ndata: late\n\n'), 1_300);
      request.on('close', () => clearTimeout(timer));
      return;
    }
    if (path === '/api/reflections/tasks/invalid-task/events') {
      response.writeHead(200, { 'content-type': 'text/event-stream' });
      response.write(': connected\n\n');
      const timer = setTimeout(() => response.write('event: terminal\ndata: invalid\n\n'), 3_000);
      request.on('close', () => clearTimeout(timer));
      return;
    }
    if (path === '/api/reflections/tasks/control-task/events') {
      response.writeHead(200, { 'content-type': 'text/event-stream' });
      response.write(': connected\n\n');
      setTimeout(() => response.end('event: terminal\ndata: complete\n\n'), 120);
      return;
    }
    if (path === '/api/reflections/tasks/abort-task/events') {
      response.writeHead(200, { 'content-type': 'text/event-stream' });
      response.write(': connected\n\n');
      request.on('close', () => response.destroy());
      return;
    }
    response.writeHead(200, { 'content-type': 'application/json' });
    response.end(JSON.stringify({ status: 'ok' }));
  });
  await new Promise<void>((resolve, reject) => {
    server.once('error', reject);
    server.listen(loopbackPort, '127.0.0.1', resolve);
  });
  const origin = new URL(`http://127.0.0.1:${loopbackPort}`);
  const fallbackDispatcher = new Agent({ bodyTimeout: 1_000, headersTimeout: 2_000 });
  const observedDispatchers: Array<unknown> = [];
  try {
    const transport: typeof fetch = (url, init) => {
      const supplied = (init as RequestInit & { dispatcher?: unknown }).dispatcher;
      observedDispatchers.push(supplied);
      return installedUndiciFetch(url, { ...init, dispatcher: supplied ?? fallbackDispatcher });
    };
    const validRequest = new Request(publicOrigin + `/api/reflections/tasks/${eventTaskId}/events`, {
      headers: { authorization: 'Bearer incoming', cookie: 'private=secret', 'x-admin-secret': 'private' },
    });
    const validResponse = await forwardBackendRequest(validRequest, origin, 'Bearer fixture', transport);
    assert.equal(validResponse.status, 200);
    assert.equal(await validResponse.text(), ': connected\n\nevent: terminal\ndata: late\n\n');
    assert.ok(observedDispatchers[0]);

    const invalidRequest = new Request(publicOrigin + '/api/reflections/tasks/invalid-task/events');
    const invalidResponse = await forwardBackendRequest(invalidRequest, origin, 'Bearer fixture', transport);
    const invalidReader = invalidResponse.body!.getReader();
    assert.equal(new TextDecoder().decode((await invalidReader.read()).value), ': connected\n\n');
    await assert.rejects(invalidReader.read(), error => error instanceof TypeError && error.message === 'terminated');
    assert.equal(observedDispatchers[1], undefined);

    const controlResponse = await forwardBackendRequest(
      new Request(publicOrigin + '/api/reflections/tasks/control-task/events'), origin, 'Bearer fixture', transport,
    );
    assert.equal(await controlResponse.text(), ': connected\n\nevent: terminal\ndata: complete\n\n');
    assert.equal(observedDispatchers[2], undefined);

    const nonSseResponse = await forwardBackendRequest(
      new Request(publicOrigin + '/api/reflections/tasks/control-task'), origin, 'Bearer fixture',
      transport,
    );
    assert.deepEqual(await nonSseResponse.json(), { status: 'ok' });
    assert.equal(observedDispatchers[3], undefined);

    const abort = new AbortController();
    const abortRequest = new Request(publicOrigin + `/api/reflections/tasks/${eventTaskId}/events`, { signal: abort.signal });
    const abortResponse = await forwardBackendRequest(abortRequest, origin, 'Bearer fixture', transport);
    const abortReader = abortResponse.body!.getReader();
    assert.equal(new TextDecoder().decode((await abortReader.read()).value), ': connected\n\n');
    assert.equal(observedDispatchers[4] !== undefined, true);
    abort.abort();
    await assert.rejects(abortReader.read());
    assert.equal(observedDispatchers.length, 5);
    for (const headers of forwardedHeaders) {
      assert.equal(headers.authorization, 'Bearer fixture');
      assert.equal(headers.cookie, undefined);
      assert.equal(headers.encoding, 'identity');
    }
  } finally {
    await fallbackDispatcher.close();
    await new Promise<void>(resolve => server.close(() => resolve()));
  }
});

function definiteNotionExpiry() {
  return { error_code: 'ACCESS_TOKEN_REQUIRED', outcome_unknown: false };
}

function browserTaskRequest(boundary: BffLoginBoundary, body: string, signal?: AbortSignal, path = '/api/reflections/tasks') {
  return new Request(publicOrigin + path, {
    method: 'POST',
    headers: {
      cookie: boundary.handleCookieName + '=' + handle,
      origin: publicOrigin,
      'x-ink-csrf': boundary.csrfToken(handle),
      'content-type': 'application/json',
    },
    body,
    signal,
  });
}

test('definite Notion task expiry renews Browser auth once and replays exact body and headers', async () => {
  const boundary = new BffLoginBoundary({ publicOrigin, callbackUri: publicOrigin + '/auth/callback', cookieSecret: 's'.repeat(32) });
  const resolves: string[] = [];
  const admin = { resolve: async (value: string) => {
    resolves.push(value);
    return { access_token: resolves.length === 1 ? 'expired.admin.token' : 'renewed.admin.token', expires_at: '2026-09-14T12:00:00Z', principal: { subject: 'opaque', canonical_user_id: '42', client_id: 'browser', scopes: ['dream:read', 'dream:write'], status: 'active' as const } };
  } };
  const forwarded: { headers: Headers; body: string }[] = [];
  const transport: typeof fetch = async (_url, init) => {
    forwarded.push({ headers: new Headers(init?.headers), body: await new Response(init?.body).text() });
    if (forwarded.length === 1) return Response.json({ detail: definiteNotionExpiry() }, { status: 401 });
    return Response.json({ task_id: 'created-task' }, { status: 202 });
  };
  const body = JSON.stringify({ request_key: 'request-key-1', analysis_content: { include_notion: true, connector_id: 'connector-1' } });
  const response = await createApiProxy(boundary, admin, new URL('http://backend.example'), transport)(browserTaskRequest(boundary, body));

  assert.equal(response.status, 202);
  assert.deepEqual(resolves, [handle, handle]);
  assert.equal(forwarded.length, 2);
  assert.deepEqual(forwarded.map(item => item.body), [body, body]);
  assert.equal(forwarded[0].headers.get('authorization'), 'Bearer expired.admin.token');
  assert.equal(forwarded[1].headers.get('authorization'), 'Bearer renewed.admin.token');
  for (const item of forwarded) {
    assert.equal(item.headers.get('origin'), publicOrigin);
    assert.equal(item.headers.get('x-ink-csrf'), null);
    assert.equal(item.headers.get('cookie'), null);
  }
});

test('Notion renewal never loops after a second definite 401', async () => {
  const boundary = new BffLoginBoundary({ publicOrigin, callbackUri: publicOrigin + '/auth/callback', cookieSecret: 's'.repeat(32) });
  let resolves = 0;
  let calls = 0;
  const admin = { resolve: async () => {
    resolves++;
    return { access_token: `renewed-${resolves}`, expires_at: '2026-09-14T12:00:00Z', principal: { subject: 'opaque', canonical_user_id: '42', client_id: 'browser', scopes: ['dream:read', 'dream:write'], status: 'active' as const } };
  } };
  const response = await createApiProxy(boundary, admin, new URL('http://backend.example'), async () => {
    calls++;
    return Response.json({ detail: definiteNotionExpiry() }, { status: 401 });
  })(browserTaskRequest(boundary, JSON.stringify({ request_key: 'request-key-2', analysis_content: { include_notion: true } })));
  assert.equal(response.status, 401);
  assert.equal(calls, 2);
  assert.equal(resolves, 2);
});

test('unknown, committed, native, incomplete, and aborted submissions do not renew', async () => {
  const cases = [
    { name: 'unknown', body: { request_key: 'unknown', analysis_content: { include_notion: true } }, detail: { ...definiteNotionExpiry(), outcome_unknown: true } },
    { name: 'committed', body: { request_key: 'committed', analysis_content: { include_notion: true } }, detail: { ...definiteNotionExpiry(), creation_committed: true } },
    { name: 'task-id', body: { request_key: 'task-id', analysis_content: { include_notion: true } }, detail: { ...definiteNotionExpiry(), task_id: 'already-created' } },
    { name: 'no-notion', body: { request_key: 'no-notion', analysis_content: { include_notion: false } }, detail: definiteNotionExpiry() },
    { name: 'no-key', body: { analysis_content: { include_notion: true } }, detail: definiteNotionExpiry() },
  ];
  for (const item of cases) {
    const boundary = new BffLoginBoundary({ publicOrigin, callbackUri: publicOrigin + '/auth/callback', cookieSecret: 's'.repeat(32) });
    let calls = 0;
    let resolves = 0;
    const admin = { resolve: async () => {
      resolves++;
      return { access_token: 'browser.token', expires_at: '2026-09-14T12:00:00Z', principal: { subject: 'opaque', canonical_user_id: '42', client_id: 'browser', scopes: ['dream:read', 'dream:write'], status: 'active' as const } };
    } };
    const response = await createApiProxy(boundary, admin, new URL('http://backend.example'), async () => {
      calls++;
      return Response.json({ detail: item.detail }, { status: 401 });
    })(browserTaskRequest(boundary, JSON.stringify(item.body)));
    assert.equal(response.status, 401, item.name);
    assert.equal(calls, 1, item.name);
    assert.equal(resolves, 1, item.name);
  }

  const nativeBoundary = new BffLoginBoundary({ publicOrigin, callbackUri: publicOrigin + '/auth/callback', cookieSecret: 's'.repeat(32) });
  let nativeCalls = 0;
  const nativeResponse = await createApiProxy(nativeBoundary, { resolve: async () => { throw new Error('native must not resolve'); } }, new URL('http://backend.example'), async () => {
    nativeCalls++;
    return Response.json({ detail: definiteNotionExpiry() }, { status: 401 });
  })(new Request(publicOrigin + '/api/reflections/tasks', { method: 'POST', headers: { authorization: 'Bearer native.token', 'content-type': 'application/json' }, body: JSON.stringify({ request_key: 'native', analysis_content: { include_notion: true } }) }));
  assert.equal(nativeResponse.status, 401);
  assert.equal(nativeCalls, 1);

  const abortBoundary = new BffLoginBoundary({ publicOrigin, callbackUri: publicOrigin + '/auth/callback', cookieSecret: 's'.repeat(32) });
  const abort = new AbortController();
  let abortCalls = 0;
  const abortResponse = await createApiProxy(abortBoundary, { resolve: async () => ({ access_token: 'browser.token', expires_at: '2026-09-14T12:00:00Z', principal: { subject: 'opaque', canonical_user_id: '42', client_id: 'browser', scopes: ['dream:read', 'dream:write'], status: 'active' as const } }) }, new URL('http://backend.example'), async () => {
    abortCalls++;
    abort.abort();
    return Response.json({ detail: definiteNotionExpiry() }, { status: 401 });
  })(browserTaskRequest(abortBoundary, JSON.stringify({ request_key: 'aborted', analysis_content: { include_notion: true } }), abort.signal));
  assert.equal(abortResponse.status, 401);
  assert.equal(abortCalls, 1);

  const routeBoundary = new BffLoginBoundary({ publicOrigin, callbackUri: publicOrigin + '/auth/callback', cookieSecret: 's'.repeat(32) });
  let routeCalls = 0;
  const routeResponse = await createApiProxy(routeBoundary, { resolve: async () => ({ access_token: 'browser.token', expires_at: '2026-09-14T12:00:00Z', principal: { subject: 'opaque', canonical_user_id: '42', client_id: 'browser', scopes: ['dream:read', 'dream:write'], status: 'active' as const } }) }, new URL('http://backend.example'), async () => {
    routeCalls++;
    return Response.json({ detail: definiteNotionExpiry() }, { status: 401 });
  })(browserTaskRequest(routeBoundary, JSON.stringify({ request_key: 'route', analysis_content: { include_notion: true } }), undefined, '/api/reflections/tasks/task-id/start'));
  assert.equal(routeResponse.status, 401);
  assert.equal(routeCalls, 1);
});
