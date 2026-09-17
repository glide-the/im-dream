// [Input] Real BFF boundary functions with explicit test-owned origin/secret/clock.
// [Output] Deterministic cookie/PKCE/callback/return/origin/CSRF validation without services or browser.
// [Pos] Provider-free Node contracts for Next BFF login security.
// [Sync] 2026-09-17: cover explicit loopback proxy origin recovery without trusting arbitrary internal URLs.
// [Sync] 2026-09-16: cover exact public Host recovery from Next's normalized internal request URL.
// [Sync] 2026-09-14: verify the production helper; no alternative OAuth/session implementation.

import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import test from 'node:test';
import { BffBoundaryError, BffLoginBoundary, relativeReturnLocation } from './login-boundary.ts';

const cookieSecret = 'test-owned-cookie-secret-' + 'x'.repeat(32);
const handle = 'dbr_' + 'a'.repeat(43);

function boundary(clock: () => number = () => 1_000): BffLoginBoundary {
  return new BffLoginBoundary({ publicOrigin: 'https://dream.example', callbackUri: 'https://dream.example/auth/callback', cookieSecret }, clock);
}

function cookieHeader(cookie: string): string { return cookie.split(';')[0]; }

test('encrypted transaction cookie round trips without exposing PKCE and uses host-only flags', () => {
  const bff = boundary(); const tx = bff.createTransaction('/story?name=hello%20world');
  const cookie = bff.transactionCookie(tx);
  assert.equal(cookie.includes(tx.code_verifier), false);
  assert.match(cookie, /^__Host-ink-dream-login=/);
  for (const flag of ['Path=/', 'HttpOnly', 'SameSite=Lax', 'Secure']) assert(cookie.includes(flag));
  assert.equal(cookie.includes('Domain='), false);
  const request = new Request('https://dream.example/auth/callback', { headers: { cookie: cookieHeader(cookie) } });
  assert.deepEqual(bff.readTransaction(request), tx);
  assert.equal(bff.codeChallenge(tx), createHash('sha256').update(tx.code_verifier).digest('base64url'));
  assert.equal(JSON.stringify(bff).includes(cookieSecret), false);
});

test('expired, tampered, duplicate and wrong-origin login cookies fail closed', () => {
  const now = [1_000]; const bff = boundary(() => now[0]); const tx = bff.createTransaction('/');
  const cookie = cookieHeader(bff.transactionCookie(tx));
  const req = (value: string, url = 'https://dream.example/auth/callback') => new Request(url, { headers: { cookie: value } });
  assert.throws(() => bff.readTransaction(req(cookie + '; ' + cookie)), BffBoundaryError);
  const [name, value] = cookie.split('=');
  const tampered = name + '=' + (value[0] === 'A' ? 'B' : 'A') + value.slice(1);
  assert.throws(() => bff.readTransaction(req(tampered)), BffBoundaryError);
  assert.throws(() => bff.readTransaction(req(cookie, 'https://attacker.example/auth/callback')), BffBoundaryError);
  now[0] = tx.expires_at;
  assert.throws(() => bff.readTransaction(req(cookie)), BffBoundaryError);
});

test('OAuth callback requires exact state/issuer and one code', () => {
  const bff = boundary(); const tx = bff.createTransaction('/story');
  const cookie = cookieHeader(bff.transactionCookie(tx));
  const callback = (query: string) => new Request('https://dream.example/auth/callback?' + query, { headers: { cookie } });
  const params = new URLSearchParams({ code: 'private-code', state: tx.state, iss: 'https://admin.example/api/auth' });
  assert.deepEqual(bff.validateCallback(callback(params.toString()), 'https://admin.example/api/auth'), tx);
  for (const [name, value] of [['state', 'wrong'], ['iss', 'https://google.example'], ['code', '']]) {
    const modified = new URLSearchParams(params); modified.set(name, value);
    assert.throws(() => bff.validateCallback(callback(modified.toString()), 'https://admin.example/api/auth'), BffBoundaryError);
  }
  assert.throws(() => bff.validateCallback(callback(params + '&code=duplicate'), 'https://admin.example/api/auth'), BffBoundaryError);
  assert.throws(() => bff.validateCallback(new Request('https://dream.example/wrong-callback?' + params, { headers: { cookie } }), 'https://admin.example/api/auth'), BffBoundaryError);
});

test('exact public Host preserves login and callback when Next normalizes the internal request URL', () => {
  const bff = boundary(); const tx = bff.createTransaction('/story');
  const cookie = cookieHeader(bff.transactionCookie(tx));
  const params = new URLSearchParams({ code: 'private-code', state: tx.state, iss: 'https://admin.example/api/auth' });
  const normalized = new Request('http://localhost:3000/auth/callback?' + params, {
    headers: { cookie, host: 'dream.example' },
  });
  assert.deepEqual(bff.readTransaction(normalized), tx);
  assert.deepEqual(bff.validateCallback(normalized, 'https://admin.example/api/auth'), tx);
  assert.throws(() => bff.readTransaction(new Request(normalized.url, {
    headers: { cookie, host: 'attacker.example' },
  })), BffBoundaryError);
});

test('configured loopback proxy origin preserves login and callback when AutoDL rewrites URL and Host', () => {
  const bff = new BffLoginBoundary({
    publicOrigin: 'https://dream.example', internalOrigin: 'http://127.0.0.1:6006',
    callbackUri: 'https://dream.example/auth/callback', cookieSecret,
  });
  const tx = bff.createTransaction('/story');
  const cookie = cookieHeader(bff.transactionCookie(tx));
  const params = new URLSearchParams({ code: 'private-code', state: tx.state, iss: 'https://admin.example/api/auth' });
  const normalized = new Request('http://127.0.0.1:6006/auth/callback?' + params, { headers: { cookie, host: '127.0.0.1:6006' } });
  assert.deepEqual(bff.readTransaction(normalized), tx);
  assert.deepEqual(bff.validateCallback(normalized, 'https://admin.example/api/auth'), tx);
  assert.throws(() => bff.readTransaction(new Request('http://127.0.0.1:7000/auth/callback', { headers: { cookie } })), BffBoundaryError);
  assert.throws(() => new BffLoginBoundary({
    publicOrigin: 'https://dream.example', internalOrigin: 'https://proxy.example',
    callbackUri: 'https://dream.example/auth/callback', cookieSecret,
  }), BffBoundaryError);
});

test('return locations preserve ordinary pages and reject open redirect and nested encoding', () => {
  for (const safe of ['/', '/story?step=2', '/story?name=hello%20world', '/%E4%B8%AD%E6%96%87']) assert.equal(relativeReturnLocation(safe), safe);
  for (const bad of ['https://attacker.example', '//attacker.example', '/\\attacker.example', '/%2f%2fattacker.example', '/%252f%252fattacker.example', '/%250aevil', '/\nevil']) {
    assert.throws(() => relativeReturnLocation(bad), BffBoundaryError);
  }
});

test('mutations require exact Origin and CSRF bound to the active handle', () => {
  const bff = boundary();
  const cookie = cookieHeader(bff.handleCookie(handle, 2_000));
  const mutation = (origin?: string, csrf?: string) => new Request('https://dream.example/api/sessions', {
    method: 'POST', headers: { cookie, ...(origin ? { origin } : {}), ...(csrf ? { 'x-ink-csrf': csrf } : {}) },
  });
  assert.equal(bff.requireMutation(mutation('https://dream.example', bff.csrfToken(handle))), handle);
  for (const request of [mutation(), mutation('https://attacker.example', bff.csrfToken(handle)), mutation('https://dream.example', 'wrong'), mutation('https://dream.example', bff.csrfToken('dbr_' + 'b'.repeat(43)))]) {
    assert.throws(() => bff.requireMutation(request), BffBoundaryError);
  }
  assert.match(bff.clearTransactionCookie(), /Max-Age=0/);
  assert.match(bff.clearHandleCookie(), /Max-Age=0/);
});

test('explicit loopback HTTP has no Secure host-prefix, unsafe config never falls back', () => {
  const local = new BffLoginBoundary({ publicOrigin: 'http://localhost:5173', callbackUri: 'http://localhost:5173/auth/callback', cookieSecret });
  assert.match(local.handleCookie(handle, Date.now() / 1_000 + 60), /^ink-dream-browser=/);
  for (const origin of ['http://remote.example', 'https://dream.example/path', 'https://user:secret@dream.example', 'https://dream.example?query=1']) {
    assert.throws(() => new BffLoginBoundary({ publicOrigin: origin, callbackUri: origin + '/auth/callback', cookieSecret }), BffBoundaryError);
  }
  assert.throws(() => BffLoginBoundary.fromEnvironment({}), BffBoundaryError);
  assert.throws(() => new BffLoginBoundary({ publicOrigin: 'https://dream.example', callbackUri: 'https://dream.example/auth/callback', cookieSecret: 'short' }), BffBoundaryError);
});
