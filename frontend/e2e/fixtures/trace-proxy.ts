// [Input] Isolated Python listener and OTLP collector supplied by test_observability.py.
// [Output] One Browser-cookie BFF request through ordinary Admin resolution and HTTP proxy.
// [Pos] Deterministic cross-language fixture; no real account, database or model.
import { createApiProxy } from '../../app/api/_auth/api-proxy.ts';
import { AdminBffClient } from '../../app/api/_auth/admin-client.ts';
import { BffLoginBoundary } from '../../app/api/_auth/login-boundary.ts';
const publicOrigin = 'https://dream.example';
const handle = 'dbr_' + 'h'.repeat(43);
const boundary = new BffLoginBoundary({ publicOrigin, callbackUri: publicOrigin + '/auth/callback', cookieSecret: 's'.repeat(32) });
const admin = new AdminBffClient({ origin: 'https://admin.example', transportOrigin: 'https://admin.example',
  issuer: 'https://admin.example/api/auth', resource: publicOrigin + '/api', serviceId: 'fixture-service',
  serviceSecret: 's'.repeat(32), timeoutMilliseconds: 1000, maxResponseBytes: 1048576 }, async (_url, init) => {
  const body = JSON.parse(String(init?.body));
  return Response.json({ request_id: body.request_id, data: { access_token: 'write-token', expires_at: '2027-01-01T00:00:00Z',
    principal: { subject: 'opaque-ba-subject', canonical_user_id: '42', client_id: 'dream-browser', scopes: ['dream:read', 'dream:write'], status: 'active' } } });
}, async () => 'fixture.service');
const proxy = createApiProxy(boundary, admin, new URL(process.env.TRACE_FIXTURE_BACKEND!));
const response = await proxy(new Request(publicOrigin + '/api/decks/defaults/reconcile?secret-query=private', { method: 'POST',
  headers: { cookie: boundary.handleCookieName + '=' + handle + '; other=private-cookie', origin: publicOrigin,
    'x-ink-csrf': boundary.csrfToken(handle), 'traceparent': '00-' + 'a'.repeat(32) + '-' + 'b'.repeat(16) + '-01',
    tracestate: 'vendor=foreign-state', baggage: 'identity=private-body' }, body: 'private-body' }));
await response.text();
// beforeExit flushes the bounded exporter after the body has completed.
console.log(JSON.stringify({ status: response.status, id: response.headers.get('x-trace-id'), linked: response.headers.get('x-trace-linked') }));
