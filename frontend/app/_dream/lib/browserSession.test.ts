// [Input] Actual public Browser session/header/logout functions with explicit fake BFF fetch.
// [Output] Exact decimal/time/CSRF DTO, no OAuth adoption and failure retention contracts.
// [Pos] Provider-free Browser session tests; production helpers execute unchanged.
// [Sync] 2026-09-14: verify real session state rather than a synthetic Bearer marker.
// [Sync] 2026-09-15: deferred fetch/body reads verify abort, supersession and logout without stale CSRF/user adoption.
import assert from 'node:assert/strict';
import test from 'node:test';
import { browserRequestHeaders, clearBrowserSession, getBrowserCsrfToken, isBrowserSessionCurrent, loadBrowserSession, revokeBrowserSession } from './browserSession.ts';

const csrf = 'c'.repeat(43);
function session() {
  return { user: { id: '9223372036854775807', email: 'actor@example.com', display_name: null, avatar_url: null, role: 'user', created_at: '2026-09-14T00:00:00.123456Z' }, csrf_token: csrf };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((accept, deny) => { resolve = accept; reject = deny; });
  return { promise, resolve, reject };
}

function pendingBody() {
  const entered = deferred<void>();
  const body = deferred<unknown>();
  const response = Object.assign(Response.json({}), { json: async () => { entered.resolve(); return await body.promise; } });
  return { entered, body, response };
}

test('loads only strict public user and memory CSRF using Cookie session', async () => {
  clearBrowserSession();
  const result = await loadBrowserSession(async (url, init) => {
    assert.equal(url, '/auth/session'); assert.equal(init?.credentials, 'include'); assert.equal(init?.cache, 'no-store');
    assert.equal(new Headers(init?.headers).get('authorization'), null);
    return Response.json(session());
  });
  assert.equal(result?.user.id, '9223372036854775807'); assert.equal(result?.user.created_at, '2026-09-14T00:00:00.123456Z');
  assert.ok(Object.isFrozen(result?.user)); assert.equal(getBrowserCsrfToken(), csrf);
  assert.deepEqual(browserRequestHeaders({ Authorization: 'Bearer retired', Cookie: 'private', 'content-type': 'application/json' }), { 'content-type': 'application/json', 'x-ink-csrf': csrf });
});

test('rejects extra OAuth fields, unsafe ID, malformed CSRF and invalid profile', async () => {
  for (const mutate of [
    (value: Record<string, unknown>) => { value.access_token = 'private'; },
    (value: Record<string, unknown>) => { (value.user as Record<string, unknown>).id = '9223372036854775808'; },
    (value: Record<string, unknown>) => { value.csrf_token = 'Bearer marker'; },
    (value: Record<string, unknown>) => { (value.user as Record<string, unknown>).created_at = 'invalid'; },
  ]) {
    clearBrowserSession(); const value = session(); mutate(value);
    await assert.rejects(loadBrowserSession(async () => Response.json(value)), /Unable to check/);
    assert.equal(getBrowserCsrfToken(), null);
  }
});

test('401 clears state but dependency failure retains the last validated session', async () => {
  await loadBrowserSession(async () => Response.json(session()));
  await assert.rejects(loadBrowserSession(async () => new Response('', { status: 503 })), /Unable to check/);
  assert.equal(getBrowserCsrfToken(), csrf);
  assert.equal(await loadBrowserSession(async () => new Response('', { status: 401 })), null);
  assert.equal(getBrowserCsrfToken(), null);
});

test('failed revoke retains session and successful revoke clears only after strict receipt', async () => {
  await loadBrowserSession(async () => Response.json(session()));
  await assert.rejects(revokeBrowserSession(async () => new Response('', { status: 503 })), /Unable to log out/);
  assert.equal(getBrowserCsrfToken(), csrf);
  await assert.rejects(revokeBrowserSession(async () => Response.json({ success: false })), /Unable to log out/);
  assert.equal(getBrowserCsrfToken(), csrf);
  await revokeBrowserSession(async (url, init) => {
    assert.equal(url, '/auth/logout'); assert.equal(init?.method, 'POST'); assert.equal(new Headers(init?.headers).get('x-ink-csrf'), csrf);
    assert.equal(new Headers(init?.headers).get('authorization'), null);
    return Response.json({ success: true });
  });
  assert.equal(getBrowserCsrfToken(), null);
});

test('already aborted reads do not dispatch or invalidate a current snapshot', async () => {
  const current = await loadBrowserSession(async () => Response.json(session()));
  const abort = new AbortController(); abort.abort();
  assert.equal(await loadBrowserSession(async () => { assert.fail('aborted read dispatched'); }, abort.signal), null);
  assert.equal(getBrowserCsrfToken(), csrf); assert.ok(isBrowserSessionCurrent(current));
});

for (const result of ['success', '401', 'failure'] as const) {
  test(`aborted pending fetch ${result} cannot alter the current snapshot`, async () => {
    const current = await loadBrowserSession(async () => Response.json(session()));
    const response = deferred<Response>(); const abort = new AbortController();
    const read = loadBrowserSession(async () => response.promise, abort.signal);
    abort.abort();
    if (result === 'failure') response.reject(new Error('private aborted transport'));
    else response.resolve(result === '401' ? new Response('', { status: 401 }) : Response.json({ ...session(), csrf_token: 'd'.repeat(43) }));
    assert.equal(await read, null); assert.ok(isBrowserSessionCurrent(current)); assert.equal(getBrowserCsrfToken(), csrf);
  });
}

test('abort during JSON parsing ignores malformed payload without clearing memory', async () => {
  const current = await loadBrowserSession(async () => Response.json(session()));
  const pending = pendingBody(); const abort = new AbortController();
  const read = loadBrowserSession(async () => pending.response, abort.signal);
  await pending.entered.promise; abort.abort(); pending.body.resolve({ access_token: 'private' });
  assert.equal(await read, null); assert.ok(isBrowserSessionCurrent(current));
});

for (const result of ['success', '401', '503', 'failure'] as const) {
  test(`superseded fetch ${result} cannot overwrite or clear a newer snapshot`, async () => {
    clearBrowserSession(); const response = deferred<Response>();
    const older = loadBrowserSession(async () => response.promise);
    const current = await loadBrowserSession(async () => Response.json({ ...session(), csrf_token: 'd'.repeat(43) }));
    if (result === 'failure') response.reject(new Error('private stale failure'));
    else response.resolve(result === 'success' ? Response.json(session()) : new Response('', { status: result === '401' ? 401 : 503 }));
    assert.equal(await older, null); assert.ok(isBrowserSessionCurrent(current)); assert.equal(getBrowserCsrfToken(), 'd'.repeat(43));
    assert.equal(isBrowserSessionCurrent(null), false);
  });
}

test('superseded JSON failure is ignored and snapshot identity fences equal CSRF results', async () => {
  const pending = pendingBody(); const older = loadBrowserSession(async () => pending.response);
  await pending.entered.promise;
  const first = await loadBrowserSession(async () => Response.json(session()));
  const current = await loadBrowserSession(async () => Response.json(session()));
  pending.body.reject(new Error('private stale JSON'));
  assert.equal(await older, null); assert.equal(isBrowserSessionCurrent(first), false); assert.ok(isBrowserSessionCurrent(current));
  clearBrowserSession(); assert.equal(isBrowserSessionCurrent(current), false); assert.ok(isBrowserSessionCurrent(null));
});

for (const phase of ['fetch', 'json'] as const) {
  test(`clear invalidates a pending ${phase} success`, async () => {
    await loadBrowserSession(async () => Response.json(session()));
    const response = deferred<Response>(); const pending = pendingBody();
    const read = loadBrowserSession(async () => phase === 'fetch' ? response.promise : pending.response);
    if (phase === 'json') await pending.entered.promise;
    clearBrowserSession();
    if (phase === 'fetch') response.resolve(Response.json(session())); else pending.body.resolve(session());
    assert.equal(await read, null); assert.equal(getBrowserCsrfToken(), null);
  });
}

test('failed logout invalidates existing reads and retains the last confirmed snapshot', async () => {
  const current = await loadBrowserSession(async () => Response.json(session()));
  const response = deferred<Response>(); const read = loadBrowserSession(async () => response.promise);
  await assert.rejects(revokeBrowserSession(async () => new Response('', { status: 503 })), /Unable to log out/);
  response.resolve(Response.json({ ...session(), csrf_token: 'd'.repeat(43) }));
  assert.equal(await read, null); assert.ok(isBrowserSessionCurrent(current)); assert.equal(getBrowserCsrfToken(), csrf);
});

test('strict successful logout invalidates reads started before and during its request', async () => {
  await loadBrowserSession(async () => Response.json(session()));
  const first = deferred<Response>(); const last = deferred<Response>(); const logoutResponse = deferred<Response>();
  const before = loadBrowserSession(async () => first.promise);
  const logout = revokeBrowserSession(async (_url, init) => {
    assert.equal(new Headers(init?.headers).get('x-ink-csrf'), csrf); return logoutResponse.promise;
  });
  const during = loadBrowserSession(async () => last.promise);
  logoutResponse.resolve(Response.json({ success: true })); await logout;
  first.resolve(Response.json(session())); last.resolve(Response.json(session()));
  assert.equal(await before, null); assert.equal(await during, null); assert.equal(getBrowserCsrfToken(), null);
});
