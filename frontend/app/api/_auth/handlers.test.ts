// [Input] Actual BFF handlers/private transport with explicit configuration and fake Admin fetch.
// [Output] Public PKCE/handle/profile/logout, exact DTO and original-transaction recovery contracts.
// [Pos] Provider-free technical validation, no account/database/model or external HTTP calls.
// [Sync] 2026-09-18: verify public browser authority with a separate loopback server transport.
// [Sync] 2026-09-17: verify configured Admin form actions and confidential-client transport.
import assert from 'node:assert/strict';
import test from 'node:test';
import { AdminBffClient, adminBffConfig, configuredAdminBffClient } from './admin-client.ts';
import { BffLoginBoundary } from './login-boundary.ts';
import { createBffHandlers } from './handlers.ts';

const publicOrigin = 'https://dream.example';
const adminOrigin = 'https://admin.example';
const adminTransportOrigin = 'http://127.0.0.1:3000';
const browserHandle = 'dbr_' + 'h'.repeat(43);
const env = { INK_ADMIN_DREAM_BASE_URL: adminOrigin, INK_ADMIN_DREAM_TRANSPORT_BASE_URL: adminTransportOrigin, INK_ADMIN_AUTH_ISSUER: adminOrigin + '/api/auth',
  INK_DREAM_API_RESOURCE: publicOrigin + '/api', INK_ADMIN_DREAM_SERVICE_CLIENT_ID: 'dream-service', INK_ADMIN_DREAM_SERVICE_SECRET: 's'.repeat(32) };

function fixture() {
  const boundary = new BffLoginBoundary({ publicOrigin, callbackUri: publicOrigin + '/auth/callback', cookieSecret: 'c'.repeat(32) });
  const calls: { path: string; body: Record<string, unknown> | undefined; headers: Headers; init: RequestInit }[] = [];
  const outputs: Record<string, unknown> = {
    '/capabilities': { version: '1', auth: { issuer: env.INK_ADMIN_AUTH_ISSUER, jwks_uri: env.INK_ADMIN_AUTH_ISSUER + '/jwks', algorithm: 'ES256', resource: env.INK_DREAM_API_RESOURCE,
      clients: { browser: 'registered-browser', device: 'registered-device' }, scopes: ['openid', 'dream:read', 'dream:write'], delegations: [] }, schema_capabilities: [],
      operations: [{ name: 'user-profile.current', kind: 'read', user_scope: 'dream:read', background_scope: null, input_schema_version: 1, output_schema_version: 1, contract_sha256: '01011316efa10475dd1d1aa8856c82cb17ddbeb404125ebcd80af5f250f2a9d0' }] },
    '/browser-sessions/exchange': { handle: browserHandle, expires_at: new Date(Date.now() + 3_600_000).toISOString() },
    '/browser-sessions/resolve': { access_token: 'server.only.token', expires_at: new Date(Date.now() + 120_000).toISOString(),
      principal: { subject: 'opaque', canonical_user_id: '9223372036854775807', client_id: 'registered-browser', scopes: ['dream:read', 'dream:write'], status: 'active' } },
    '/browser-sessions/revoke': { revoked: true },
    '/operations/user-profile.current': { user: { id: '9223372036854775807', email: 'actor@example.com', display_name: null, avatar_url: null, role: 'user', created_at: '2026-09-14T00:00:00.123456Z', updated_at: null, auth_providers: ['credential'] } },
  };
  const transport: typeof fetch = async (url, init) => {
    const parsedUrl = new URL(String(url));
    assert.equal(parsedUrl.origin, adminTransportOrigin);
    const path = parsedUrl.pathname.replace('/api/internal/dream/v1', '');
    const headers = new Headers(init?.headers);
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;
    calls.push({ path, body, headers, init: init! });
    assert.equal(headers.get('x-ink-dream-service'), null);
    assert.equal(headers.get('x-ink-dream-credential'), null);
    assert.equal(init?.redirect, 'manual'); assert.equal(init?.cache, 'no-store');
    const output = outputs[path];
    if (output instanceof Error) throw output;
    return Response.json({ data: output, request_id: headers.get('x-request-id') });
  };
  const admin = new AdminBffClient(adminBffConfig(env), transport, async () => 'service.access.token');
  return { boundary, calls, outputs, admin, handlers: createBffHandlers(boundary, admin) };
}

test('start discovers exact registered client and creates encrypted original PKCE transaction', async () => {
  const { boundary, calls, handlers } = fixture();
  const response = await handlers.start(new Request(publicOrigin + '/auth/start?return_to=%2Fchat%3Fdeck%3D1'));
  assert.equal(response.status, 303);
  const authorize = new URL(response.headers.get('location')!);
  assert.equal(authorize.origin, adminOrigin); assert.equal(authorize.pathname, '/api/auth/oauth2/authorize');
  assert.equal(authorize.searchParams.get('client_id'), 'registered-browser');
  const transaction = boundary.readTransaction(new Request(publicOrigin + '/auth/callback', { headers: { cookie: response.headers.get('set-cookie')!.split(';')[0] } }));
  assert.equal(transaction.return_to, '/chat?deck=1');
  assert.equal(authorize.searchParams.get('code_challenge'), boundary.codeChallenge(transaction));
  assert.equal(authorize.searchParams.get('state'), transaction.state);
  assert.equal(authorize.searchParams.get('code_challenge_method'), 'S256');
  assert.equal(calls.length, 1); assert.equal(calls[0].headers.get('authorization'), 'Bearer service.access.token');
  assert.match(response.headers.get('set-cookie')!, /HttpOnly; SameSite=Lax/);
  assert.ok(!response.headers.get('set-cookie')!.includes(transaction.code_verifier));
});

test('options exposes only configured Admin browser form actions to the exact Dream origin', async () => {
  const { handlers, calls } = fixture();
  const response = await handlers.options(new Request(publicOrigin + '/auth/options'));
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), {
    password_action: adminOrigin + '/auth/dream/password',
    google_action: adminOrigin + '/auth/dream/google',
  });
  assert.equal(response.headers.get('cache-control'), 'no-store');
  assert.equal(calls.length, 0);

  const denied = await handlers.options(new Request('https://other.example/auth/options'));
  assert.equal(denied.status, 403);
  assert.equal(calls.length, 0);
});

test('callback preserves request/transaction identity and only changes cookies after successful exchange', async () => {
  const { boundary, calls, handlers, outputs } = fixture();
  const transaction = boundary.createTransaction('/chat');
  const url = publicOrigin + '/auth/callback?' + new URLSearchParams({ code: 'original-code', state: transaction.state, iss: env.INK_ADMIN_AUTH_ISSUER });
  const request = new Request(url, { headers: { cookie: boundary.transactionCookie(transaction).split(';')[0] } });
  outputs['/browser-sessions/exchange'] = new Error('private upstream detail');
  const failed = await handlers.callback(request);
  assert.equal(failed.status, 503); assert.equal(failed.headers.get('set-cookie'), null);
  assert.ok(!(await failed.text()).includes('private upstream detail'));
  outputs['/browser-sessions/exchange'] = { handle: browserHandle, expires_at: new Date(Date.now() + 3_600_000).toISOString() };
  const success = await handlers.callback(request);
  assert.equal(success.status, 303); assert.equal(success.headers.get('location'), '/chat');
  assert.deepEqual(calls[0].body, calls[1].body);
  assert.equal(calls[0].body?.request_id, transaction.transaction_id);
  assert.equal(calls[0].body?.transaction_id, transaction.transaction_id);
  assert.equal(calls[0].body?.code_verifier, transaction.code_verifier);
  assert.ok(success.headers.getSetCookie().some(cookie => cookie.includes(browserHandle)));
  assert.ok(success.headers.getSetCookie().some(cookie => cookie.startsWith(boundary.transactionCookieName + '=;')));
});

test('callback mismatch is rejected before Admin exchange', async () => {
  const { boundary, calls, handlers } = fixture();
  const transaction = boundary.createTransaction('/');
  const response = await handlers.callback(new Request(publicOrigin + '/auth/callback?code=x&state=wrong&iss=' + encodeURIComponent(env.INK_ADMIN_AUTH_ISSUER), { headers: { cookie: boundary.transactionCookie(transaction).split(';')[0] } }));
  assert.equal(response.status, 400); assert.equal(calls.length, 0);
});

test('session exposes exact decimal user ID and CSRF without OAuth credentials', async () => {
  const { boundary, calls, handlers } = fixture();
  const response = await handlers.session(new Request(publicOrigin + '/auth/session', { headers: { cookie: boundary.handleCookieName + '=' + browserHandle } }));
  assert.equal(response.status, 200);
  const text = await response.text(); const payload = JSON.parse(text);
  assert.equal(payload.user.id, '9223372036854775807');
  assert.equal(payload.user.created_at, '2026-09-14T00:00:00.123456Z');
  assert.equal(payload.csrf_token, boundary.csrfToken(browserHandle));
  assert.ok(!text.includes('server.only.token') && !text.includes(browserHandle) && !text.includes('auth_providers'));
  assert.equal(calls.at(-1)?.headers.get('authorization'), 'Bearer server.only.token');
  assert.equal(calls.at(-1)?.headers.get('x-ink-dream-service-authorization'), 'Bearer service.access.token');
  assert.equal(response.headers.get('cache-control'), 'no-store');
});

test('profile ID mismatch and extra secret fields fail closed', async () => {
  for (const mutate of [(user: Record<string, unknown>) => { user.id = '42'; }, (user: Record<string, unknown>) => { user.password_hash = 'secret'; }]) {
    const { boundary, handlers, outputs } = fixture();
    mutate((outputs['/operations/user-profile.current'] as { user: Record<string, unknown> }).user);
    const response = await handlers.session(new Request(publicOrigin + '/auth/session', { headers: { cookie: boundary.handleCookieName + '=' + browserHandle } }));
    assert.equal(response.status, 503); assert.ok(!(await response.text()).includes('secret'));
  }
});

test('logout enforces Origin/CSRF and retains handle on failed revoke', async () => {
  const { boundary, calls, handlers, outputs } = fixture();
  const request = new Request(publicOrigin + '/auth/logout', { method: 'POST', headers: { cookie: boundary.handleCookieName + '=' + browserHandle, origin: publicOrigin, 'x-ink-csrf': boundary.csrfToken(browserHandle) } });
  const denied = await handlers.logout(new Request(publicOrigin + '/auth/logout', { method: 'POST', headers: { cookie: boundary.handleCookieName + '=' + browserHandle } }));
  assert.equal(denied.status, 403); assert.equal(calls.length, 0);
  outputs['/browser-sessions/revoke'] = new Error('safe');
  assert.equal((await handlers.logout(request)).headers.get('set-cookie'), null);
  outputs['/browser-sessions/revoke'] = { revoked: true };
  const response = await handlers.logout(request);
  assert.equal(response.status, 200); assert.ok(response.headers.getSetCookie().some(cookie => cookie.startsWith(boundary.handleCookieName + '=;')));
});

test('response correlation and response-size bounds fail closed', async () => {
  const config = adminBffConfig({ ...env, INK_ADMIN_DREAM_MAX_RESPONSE_BYTES: '32' });
  const client = new AdminBffClient(config, async () => new Response('x'.repeat(33)), async () => 'service.access.token');
  await assert.rejects(client.capabilities('request-1'), { code: 'BFF_ADMIN_RESPONSE_INVALID' });
  const mismatched = new AdminBffClient(adminBffConfig(env), async () => Response.json({ request_id: 'wrong', data: { handle: browserHandle, expires_at: new Date().toISOString() } }), async () => 'service.access.token');
  await assert.rejects(mismatched.exchange('request-1', 'code', 'v'.repeat(43), publicOrigin + '/auth/callback'), { code: 'BFF_ADMIN_RESPONSE_INVALID' });
});

test('device entry preserves only user_code and redirects to the exact Admin UI', async () => {
  const { handlers, calls } = fixture();
  const response = await handlers.device(new Request(publicOrigin + '/auth/device?user_code=ABCD-EFGH&return_to=https://evil.example'));
  assert.equal(response.status, 303);
  assert.equal(response.headers.get('location'), adminOrigin + '/auth/device?user_code=ABCD-EFGH');
  assert.equal(calls.length, 1); assert.equal(calls[0].path, '/capabilities');
});

test('default service token provider performs client_credentials once and caches the short-lived token', async () => {
  let tokenCalls = 0; let apiCalls = 0;
  const transport: typeof fetch = async (url, init) => {
    const parsed = new URL(String(url));
    assert.equal(parsed.origin, adminTransportOrigin);
    if (parsed.pathname === '/api/auth/oauth2/token') {
      tokenCalls++;
      assert.match(new Headers(init?.headers).get('authorization') ?? '', /^Basic /);
      assert.equal(String(init?.body), `grant_type=client_credentials&resource=${encodeURIComponent(env.INK_DREAM_API_RESOURCE)}`);
      return Response.json({ access_token: 'issued.service.token', token_type: 'Bearer', expires_in: 300, expires_at: Math.floor(Date.now() / 1000) + 300, scope: 'capabilities:read' });
    }
    apiCalls++;
    const headers = new Headers(init?.headers);
    assert.equal(headers.get('authorization'), 'Bearer issued.service.token');
    return Response.json({ request_id: headers.get('x-request-id'), data: {
      version: '1', auth: { issuer: env.INK_ADMIN_AUTH_ISSUER, jwks_uri: env.INK_ADMIN_AUTH_ISSUER + '/jwks', algorithm: 'ES256', resource: env.INK_DREAM_API_RESOURCE,
        clients: { browser: 'registered-browser', device: 'registered-device' }, scopes: ['openid'], delegations: [] }, schema_capabilities: [], operations: [],
    } });
  };
  const client = new AdminBffClient(adminBffConfig(env), transport);
  await client.capabilities('request-1');
  await client.capabilities('request-2');
  assert.equal(tokenCalls, 1); assert.equal(apiCalls, 2);
});

test('configured Admin client is shared across Next route invocations', () => {
  const first = configuredAdminBffClient(env);
  const second = configuredAdminBffClient({ ...env });
  assert.equal(first, second);
});
