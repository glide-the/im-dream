// [Input] Actual public Browser session/header/logout functions with explicit fake BFF fetch.
// [Output] Exact decimal/time/CSRF DTO, no OAuth adoption and failure retention contracts.
// [Pos] Provider-free Browser session tests; production helpers execute unchanged.
// [Sync] 2026-09-14: verify real session state rather than a synthetic Bearer marker.
import assert from 'node:assert/strict';
import test from 'node:test';
import { browserRequestHeaders, clearBrowserSession, getBrowserCsrfToken, loadBrowserSession, revokeBrowserSession } from './browserSession.ts';

const csrf = 'c'.repeat(43);
function session() {
  return { user: { id: '9223372036854775807', email: 'actor@example.com', display_name: null, avatar_url: null, role: 'user', created_at: '2026-09-14T00:00:00.123456Z' }, csrf_token: csrf };
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
