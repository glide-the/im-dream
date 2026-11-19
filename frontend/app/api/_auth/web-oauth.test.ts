// [Input] Production Admin OAuth transport and BFF Web handlers with strict synthetic provider replies.
// [Output] PKCE/client/resource binding, Origin/DTO rejection, Bearer principal/profile and safe failure evidence.
// [Pos] Provider-free security contracts; no network, accounts, database or model calls.
import assert from 'node:assert/strict';
import test from 'node:test';
import { AdminBffClient, type AdminBffConfig } from './admin-client.ts';
import { BffLoginBoundary } from './login-boundary.ts';
import { createBffHandlers } from './handlers.ts';

process.env.INK_TRACE_ENABLED = 'false';
const origin = 'https://dream.example';
const issuer = 'https://admin.example/api/auth';
function fixture() {
  const config: AdminBffConfig = { origin: 'https://admin.example', transportOrigin: 'http://localhost:3000', issuer, resource: origin + '/api', serviceId: 'service', serviceSecret: 's'.repeat(32), timeoutMilliseconds: 500, maxResponseBytes: 50_000 };
  const calls: { path: string; headers: Headers; body: string }[] = [];
  let oauthResponse = () => Response.json({ access_token: 'web.access', refresh_token: 'web.refresh', token_type: 'Bearer', expires_in: 300, id_token: 'ignored' });
  const fetcher: typeof fetch = async (input, init) => {
    const path = new URL(String(input)).pathname; const headers = new Headers(init?.headers);
    calls.push({ path, headers, body: String(init?.body ?? '') });
    assert.equal(init?.redirect, 'manual'); assert.equal(init?.cache, 'no-store');
    if (path.includes('/oauth2/')) { assert.equal(headers.has('authorization'), false); assert.equal(headers.has('x-ink-dream-service-authorization'), false); assert.equal(init?.credentials, 'omit'); return oauthResponse(); }
    let data: unknown;
    if (path.endsWith('/capabilities')) data = { version: '1', auth: { issuer, jwks_uri: issuer + '/jwks', algorithm: 'ES256', resource: config.resource,
      clients: { browser: 'browser', device: 'device' }, scopes: ['openid', 'offline_access', 'dream:read', 'dream:write'], delegations: [] }, schema_capabilities: [],
      operations: [{ name: 'user-profile.current', kind: 'read', user_scope: 'dream:read', background_scope: null, input_schema_version: 1, output_schema_version: 1, contract_sha256: '01011316efa10475dd1d1aa8856c82cb17ddbeb404125ebcd80af5f250f2a9d0' }] };
    else if (path.endsWith('/principal')) data = { subject: 'subject', canonical_user_id: '42', client_id: 'browser', scopes: ['dream:read'], status: 'active' };
    else if (path.endsWith('/user-profile.current')) data = { user: { id: '42', email: 'fixture@example.test', display_name: null, avatar_url: null, role: 'user', created_at: null, updated_at: null, auth_providers: ['credential'] } };
    else throw Error('UNEXPECTED_RESOLVE_OR_HANDLE_OPERATION');
    return Response.json({ request_id: headers.get('x-request-id'), data });
  };
  const boundary = new BffLoginBoundary({ publicOrigin: origin, callbackUri: origin + '/auth/callback', cookieSecret: 's'.repeat(32) });
  const admin = new AdminBffClient(config, fetcher, async () => 'service.access');
  return { boundary, calls, handlers: createBffHandlers(boundary, admin), setOAuth: (value: () => Response) => { oauthResponse = value; } };
}
function mutation(path: string, body: unknown = { refresh_token: 'refresh.credential' }, requestOrigin = origin) {
  return new Request(origin + path, { method: 'POST', headers: { origin: requestOrigin, 'content-type': 'application/json' }, body: JSON.stringify(body) });
}

test('Web callback exchanges the original code/PKCE/redirect without a handle and confines tokens to a CSP completion document', async () => {
  const { boundary, calls, handlers } = fixture();
  const transaction = boundary.createTransaction('/story-workspace/chat');
  const query = new URLSearchParams({ code: 'authorization.code', state: transaction.state, iss: issuer });
  const callback = new Request(origin + '/auth/callback?' + query, { headers: { cookie: boundary.transactionCookie(transaction).split(';')[0] } });
  const response = await handlers.webCallback(callback);
  assert.equal(response.status, 200); assert.equal(response.headers.get('cache-control'), 'no-store');
  assert.match(response.headers.get('content-security-policy')!, /default-src 'none'.*script-src 'nonce-/);
  assert.equal(response.headers.get('referrer-policy'), 'no-referrer');
  const grant = new URLSearchParams(calls.find(call => call.path.endsWith('/oauth2/token'))!.body);
  assert.equal(grant.get('code_verifier'), transaction.code_verifier); assert.equal(grant.get('redirect_uri'), boundary.callbackUri);
  assert.equal(grant.get('client_id'), 'browser'); assert.equal(grant.get('resource'), origin + '/api');
  const html = await response.text(); assert.match(html, /history.replaceState/); assert.match(html, /sessionStorage/); assert.doesNotMatch(html, /ignored|dbr_|localStorage/);
  assert.ok(response.headers.getSetCookie().every(value => value.includes('Max-Age=0')));
  assert.equal(calls.some(call => call.path.includes('/browser-sessions/')), false);
});

test('Origin, JSON shape and callback state fail before provider calls', async () => {
  const { boundary, calls, handlers } = fixture();
  assert.equal((await handlers.refresh(mutation('/auth/refresh', { refresh_token: 'private' }, 'https://evil.example'))).status, 403);
  assert.equal((await handlers.logout(mutation('/auth/logout', { refresh_token: 'private' }, 'https://evil.example'))).status, 403);
  assert.equal((await handlers.refresh(mutation('/auth/refresh', { refresh_token: 'private', user_id: '42' }))).status, 400);
  const tx = boundary.createTransaction('/');
  const request = new Request(origin + '/auth/callback?' + new URLSearchParams({ code: 'code', state: 'wrong', iss: issuer }), { headers: { cookie: boundary.transactionCookie(tx).split(';')[0] } });
  assert.equal((await handlers.webCallback(request)).status, 400); assert.equal(calls.length, 0);
});

test('refresh projects only credentials; invalid grant clears login while upstream failures expose safe codes', async () => {
  const { handlers, setOAuth } = fixture();
  const result = await handlers.refresh(mutation('/auth/refresh'));
  assert.deepEqual(Object.keys(await result.json()).sort(), ['access_token', 'expires_at', 'refresh_token']);
  for (const [providerStatus, error, expected] of [[400, 'invalid_grant', 401], [503, 'private_upstream_error', 503]] as const) {
    setOAuth(() => Response.json({ error, private_secret: 'never reflect' }, { status: providerStatus }));
    const response = await handlers.refresh(mutation('/auth/refresh'));
    assert.equal(response.status, expected); assert.doesNotMatch(await response.text(), /never reflect|private_upstream_error/);
  }
  setOAuth(() => Response.json({ access_token: 'invalid token', expires_in: 300, token_type: 'Bearer' }));
  assert.equal((await handlers.refresh(mutation('/auth/refresh'))).status, 503);
});

test('Bearer profile verifies principal and profile without resolving a stale Cookie', async () => {
  const { handlers, calls } = fixture();
  const response = await handlers.session(new Request(origin + '/auth/session', { headers: { authorization: 'Bearer web.access', cookie: '__Host-ink-dream-browser=invalid' } }));
  assert.equal(response.status, 200); assert.equal((await response.json()).user.id, '42');
  assert.equal(calls.some(call => call.path.includes('/browser-sessions/')), false);
  assert.ok(calls.some(call => call.path.endsWith('/principal')));
  assert.ok(calls.some(call => call.path.endsWith('/user-profile.current')));
});
