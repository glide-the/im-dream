// [Input] Production Web credential owner with isolated tab storage, clock and injected HTTP.
// [Output] Bearer/cookie isolation, renewal concurrency, cancellation, revocation and logout race evidence.
// [Pos] Provider-free OAuth transport contracts; no accounts, persistence or model calls.
import assert from 'node:assert/strict';
import test from 'node:test';

let sequence = 0;
const profile = { user: { id: '42', email: 'web@example.test', display_name: null, avatar_url: null, role: 'user', created_at: null } };
const storageKey = 'ink-dream-web-oauth';
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(accept => { resolve = accept; }); return { promise, resolve }; }
async function tab(value: object = { access_token: 'access.initial', refresh_token: 'refresh.initial', expires_at: Date.now() + 60_000 }) {
  const values = new Map<string, string>([[storageKey, JSON.stringify(value)]]);
  const events = new EventTarget();
  Object.defineProperty(globalThis, 'window', { configurable: true, value: {
    sessionStorage: { getItem: (key: string) => values.get(key) ?? null, setItem: (key: string, value: string) => values.set(key, value), removeItem: (key: string) => values.delete(key) },
    location: { origin: 'https://dream.example' }, dispatchEvent: events.dispatchEvent.bind(events),
  } });
  const owner: typeof import('./browserSession.web.ts') = await import(new URL('./browserSession.web.ts?tab=' + sequence++, import.meta.url).href);
  return { owner, values, events };
}
function renewed(access = 'access.renewed', refresh = 'refresh.renewed') { return Response.json({ access_token: access, refresh_token: refresh, expires_at: Date.now() + 60_000 }); }
test.afterEach(() => { Reflect.deleteProperty(globalThis, 'window'); });

test('memory access, refresh-only tab storage, strict public profile and cookie-free Bearer requests', async () => {
  const { owner, values } = await tab();
  const calls: { path: string; init?: RequestInit }[] = [];
  const raw: typeof fetch = async (input, init) => { calls.push({ path: String(input), init }); return Response.json(profile); };
  const session = await owner.loadBrowserSession(raw);
  assert.equal(session?.user.id, '42'); assert.ok(Object.isFrozen(session?.user));
  assert.notEqual(owner.getBrowserCsrfToken(), 'access.initial');
  assert.deepEqual(JSON.parse(values.get(storageKey)!), { refresh_token: 'refresh.initial' });
  const request = owner.createBrowserBearerFetch(raw, 'https://dream.example');
  await request('/api/decks', { headers: { Cookie: 'stale=private', Authorization: 'Bearer override', 'x-ink-csrf': 'retired' }, credentials: 'include' });
  for (const call of calls) {
    assert.equal(call.init?.credentials, 'omit');
    assert.equal(new Headers(call.init?.headers).get('authorization'), 'Bearer access.initial');
    assert.equal(new Headers(call.init?.headers).get('cookie'), null);
    assert.equal(new Headers(call.init?.headers).get('x-ink-csrf'), null);
  }
  assert.deepEqual(calls.map(call => call.path), ['/auth/session', '/api/decks']);
});

test('reload rotates one refresh for twelve concurrent requests; aborted caller does not cancel shared renewal', async () => {
  const { owner, values } = await tab({ refresh_token: 'refresh.initial' });
  const gate = deferred<Response>(); let refreshes = 0; let requests = 0;
  const raw: typeof fetch = async (input, init) => {
    if (input === '/auth/refresh') { refreshes++; assert.equal(init?.credentials, 'omit'); return gate.promise; }
    requests++; assert.equal(new Headers(init?.headers).get('authorization'), 'Bearer access.renewed'); return Response.json({ ok: true });
  };
  const request = owner.createBrowserBearerFetch(raw, 'https://dream.example');
  const abort = new AbortController();
  const cancelled = request('/api/cancelled', { signal: abort.signal });
  const cancellation = assert.rejects(cancelled, { name: 'AbortError' });
  const reads = Array.from({ length: 12 }, () => request('/api/decks'));
  abort.abort(); await cancellation;
  assert.equal(refreshes, 1); assert.equal(requests, 0);
  gate.resolve(renewed()); await Promise.all(reads);
  assert.equal(requests, 12); assert.deepEqual(JSON.parse(values.get(storageKey)!), { refresh_token: 'refresh.renewed' });
});

test('refresh failure retains credentials and invalid grant clears identity without restoring stale profile', async () => {
  const { owner, values } = await tab();
  const session = await owner.loadBrowserSession(async () => Response.json(profile));
  await assert.rejects(owner.ensureBrowserAccessToken(async () => { throw Error('private upstream body'); }, true), /Unable to renew/);
  assert.ok(owner.isBrowserSessionCurrent(session)); assert.ok(values.has(storageKey));
  const body = deferred<Response>();
  const stale = owner.loadBrowserSession(async () => body.promise);
  assert.equal(await owner.ensureBrowserAccessToken(async () => new Response(null, { status: 401 }), true), null);
  body.resolve(Response.json(profile)); assert.equal(await stale, null);
  assert.equal(owner.getBrowserCsrfToken(), null); assert.equal(values.has(storageKey), false);
});

test('GET retries once after 401 while ordinary mutations preserve their single dispatch', async () => {
  for (const method of ['GET', 'POST']) {
    const { owner } = await tab(); let calls = 0; let refreshes = 0;
    const raw: typeof fetch = async input => {
      if (input === '/auth/refresh') { refreshes++; return renewed(); }
      return ++calls === 1 ? new Response(null, { status: 401 }) : Response.json({ ok: true });
    };
    const response = await owner.createBrowserBearerFetch(raw, 'https://dream.example')('/api/claude-agent', { method });
    assert.equal(refreshes, 1); assert.equal(calls, method === 'GET' ? 2 : 1); assert.equal(response.status, method === 'GET' ? 200 : 401);
  }
});

test('definite Notion pre-create rejection preserves the same request bytes and idempotency key', async () => {
  const { owner } = await tab(); const bodies: (BodyInit | null | undefined)[] = [];
  const raw: typeof fetch = async (input, init) => {
    if (input === '/auth/refresh') return renewed();
    bodies.push(init?.body);
    return bodies.length === 1 ? Response.json({ detail: { error_code: 'ACCESS_TOKEN_REQUIRED', outcome_unknown: false } }, { status: 401 }) : Response.json({ task_id: 'created' });
  };
  const body = JSON.stringify({ request_key: 'stable', analysis_content: { include_notion: true } });
  const response = await owner.createBrowserBearerFetch(raw, 'https://dream.example')('/api/reflections/tasks', { method: 'POST', body });
  assert.equal(response.status, 200); assert.deepEqual(bodies, [body, body]);
});

test('logout waits for rotation, revokes the latest refresh, blocks dispatch and invalidates pending profile reads', async () => {
  const { owner, values } = await tab();
  await owner.loadBrowserSession(async () => Response.json(profile));
  const refresh = deferred<Response>(); const revoke = deferred<Response>(); let revoked: unknown;
  const rotation = owner.ensureBrowserAccessToken(async () => refresh.promise, true);
  const logout = owner.revokeBrowserSession(async (_input, init) => { revoked = JSON.parse(String(init?.body)); return revoke.promise; });
  await assert.rejects(owner.ensureBrowserAccessToken(), /Please log in again/);
  assert.equal(await owner.loadBrowserSession(), null);
  refresh.resolve(renewed()); await rotation;
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(revoked, { refresh_token: 'refresh.renewed' });
  revoke.resolve(Response.json({ success: true })); await logout;
  assert.equal(values.has(storageKey), false); assert.equal(owner.getBrowserCsrfToken(), null);
});

test('failed revoke retains the confirmed user; foreign and signed storage URLs receive no injected credential', async () => {
  const { owner, values } = await tab(); const session = await owner.loadBrowserSession(async () => Response.json(profile));
  await assert.rejects(owner.revokeBrowserSession(async () => new Response(null, { status: 503 })), /Unable to log out/);
  assert.ok(owner.isBrowserSessionCurrent(session)); assert.ok(values.has(storageKey));
  const init = { method: 'PUT', headers: { 'content-type': 'image/png' }, body: 'bytes' };
  const raw: typeof fetch = async (input, options) => { assert.equal(String(input), 'https://storage.example/api/upload'); assert.equal(options, init); return new Response(); };
  await owner.createBrowserBearerFetch(raw, 'https://dream.example')('https://storage.example/api/upload', init);
});

test('invalid refresh stops all waiting protected requests before dispatch and public paths keep their transport', async () => {
  const { owner } = await tab({ refresh_token: 'revoked.refresh' });
  let refreshes = 0; let business = 0; let publicReads = 0;
  const raw: typeof fetch = async input => {
    if (input === '/auth/refresh') { refreshes++; return new Response(null, { status: 401 }); }
    if (input === '/api/health') { publicReads++; return Response.json({ status: 'ok' }); }
    business++; return Response.json({});
  };
  const request = owner.createBrowserBearerFetch(raw, 'https://dream.example');
  const results = await Promise.allSettled(Array.from({ length: 12 }, () => request('/api/decks')));
  assert.ok(results.every(result => result.status === 'rejected'));
  assert.equal(refreshes, 1); assert.equal(business, 0);
  await assert.rejects(request('/api/decks'), /Please log in again/);
  await request('/api/health'); assert.equal(publicReads, 1); assert.equal(business, 0);
});
