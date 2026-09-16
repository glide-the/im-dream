// [Input] Actual BFF Node Runtime request adapter and explicit fake Admin resolution.
// [Output] Server-only Bearer, opaque selector preservation and Cookie/identity isolation contracts.
// [Pos] Provider-free boundary test, no Node upstream session or business mutation.
// [Sync] 2026-09-17: strip Browser-injected service OAuth headers before Runtime forwarding.
import assert from 'node:assert/strict';
import test from 'node:test';
import { BffLoginBoundary } from './login-boundary.ts';
import { runtimeRequest } from './runtime-request.ts';

test('Runtime receives resolved OAuth token and owned selectors without ambient credentials', async () => {
  const boundary = new BffLoginBoundary({ publicOrigin: 'https://dream.example', callbackUri: 'https://dream.example/auth/callback', cookieSecret: 's'.repeat(32) });
  const handle = 'dbr_' + 'h'.repeat(43);
  const admin = { resolve: async () => ({ access_token: 'server.admin.token', expires_at: '2026-09-14T12:00:00Z', principal: { subject: 'opaque', canonical_user_id: '42', client_id: 'browser', scopes: ['dream:write'], status: 'active' as const } }) };
  const request = new Request('https://dream.example/api/mcp-apps/server-1', { method: 'POST', headers: {
    cookie: boundary.handleCookieName + '=' + handle, origin: boundary.publicOrigin, 'x-ink-csrf': boundary.csrfToken(handle), authorization: 'Bearer attacker',
    'x-ink-dream-credential': 'secret', 'x-ink-dream-service-authorization': 'Bearer attacker', 'x-user-id': '7', 'x-ink-mcp-apps-browser-session': 'opaque-session', 'x-ink-workspace-scope': 'owned-thread', 'mcp-session-id': 'upstream-session',
  }, body: '{"jsonrpc":"2.0","id":1,"method":"initialize"}' });
  const result = await runtimeRequest(request, boundary, admin);
  assert.equal(result.headers.get('authorization'), 'Bearer server.admin.token');
  for (const name of ['cookie', 'x-ink-csrf', 'x-ink-dream-credential', 'x-ink-dream-service-authorization', 'x-user-id']) assert.equal(result.headers.get(name), null);
  assert.equal(result.headers.get('x-ink-mcp-apps-browser-session'), 'opaque-session');
  assert.equal(result.headers.get('x-ink-workspace-scope'), 'owned-thread'); assert.equal(result.headers.get('mcp-session-id'), 'upstream-session');
  assert.equal(await result.text(), '{"jsonrpc":"2.0","id":1,"method":"initialize"}');
});
