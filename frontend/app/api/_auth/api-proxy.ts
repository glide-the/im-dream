// [Sync] 2026-10-11: keep native Bearer canonical origin and current-cookie precedence while resolving Browser addresses.
// [Input] Public Web/native OAuth Bearer requests or native legacy handles.
// [Output] Credential-selected, origin-checked, cache-free Python HTTP/SSE responses.
// [Pos] BFF API authentication owner; Python verifies every Admin access token/principal.
// [Sync] 2026-10-11: use the same request origin for cookie/CSRF and Admin handle resolution.
// [Sync] 2026-09-17: reuse the process-owned Admin client instead of exchanging a service token per API request.
// [Sync] 2026-10-13: renew only definite pre-create Notion authorization rejection once, replaying the original request/key.
// [Sync] 2026-11-18: trace shared BFF entry and authentication before streaming.
// [Sync] 2026-11-19: explicit Bearer bypasses ambient legacy cookies and Admin session resolution.
import { traceApiRequest, traceAuthentication } from '../_trace.ts';
import { randomUUID } from 'node:crypto';
import { configuredBackendOrigin, forwardBackendRequest } from '../_http-proxy.ts';
import { AdminBffClient, configuredAdminBffClient } from './admin-client.ts';
import { BffBoundaryError, BffLoginBoundary } from './login-boundary.ts';
import { bffFailure } from './handlers.ts';

export async function apiAuthorization(request: Request, boundary: BffLoginBoundary, admin: Pick<AdminBffClient, 'resolve'>): Promise<string> {
  boundary.requireRequestOrigin(request);
  const origin = request.headers.get('origin');
  if (origin !== null && origin !== boundary.publicOrigin) throw new BffBoundaryError('BFF_ORIGIN_DENIED', 403);
  const authorization = request.headers.get('authorization');
  if (authorization !== null) {
    if (!/^Bearer [A-Za-z0-9._~-]+$/.test(authorization) || authorization.length > 16_391) throw new BffBoundaryError('BFF_SESSION_REQUIRED', 401);
    return authorization;
  }
  if (boundary.hasHandleCookie(request)) {
    const readOnly = ['GET', 'HEAD', 'OPTIONS'].includes(request.method.toUpperCase());
    const handle = readOnly ? boundary.readHandle(request) : boundary.requireMutation(request);
    const resolved = await admin.resolve(handle, randomUUID(), request.signal);
    return 'Bearer ' + resolved.access_token;
  }
  throw new BffBoundaryError('BFF_SESSION_REQUIRED', 401);
}

export function configuredApiCredentials(request: Request) {
  const boundary = apiRequestBoundary(request);
  const admin = configuredAdminBffClient().forBrowserOrigin(boundary.publicOrigin);
  return { boundary, admin };
}

/** Web requests use their published address; native Bearer retains its canonical origin contract. */
export function apiRequestBoundary(request: Request, environment: Readonly<Record<string, string | undefined>> = process.env) {
  const browser = BffLoginBoundary.fromRequest(request, environment);
  return browser.hasHandleCookie(request) || request.headers.has('origin') || request.headers.has('sec-fetch-site') ? browser : BffLoginBoundary.fromEnvironment(environment);
}

export function createApiProxy(boundary: BffLoginBoundary, admin: Pick<AdminBffClient, 'resolve'>, origin: URL, transport: typeof fetch = fetch) {
  return async (request: Request): Promise<Response> => traceApiRequest(request, async () => {
    try {
      const incoming = new URL(request.url);
      if (!incoming.pathname.startsWith('/api/') && incoming.pathname !== '/api' && incoming.pathname !== '/auth/me') throw new BffBoundaryError('BFF_API_PATH_INVALID', 400);
      if (['token', 'access_token', 'refresh_token', 'id_token'].some(name => incoming.searchParams.has(name))) throw new BffBoundaryError('BFF_TOKEN_QUERY_DENIED', 400);
      const authorization = await traceAuthentication(() => apiAuthorization(request, boundary, admin));
      const canReplay = request.method.toUpperCase() === 'POST' && incoming.pathname === '/api/reflections/tasks'
        && !request.headers.has('authorization') && boundary.hasHandleCookie(request);
      const replay = canReplay ? request.clone() : undefined;
      const response = await forwardBackendRequest(request, origin, authorization, transport);
      if (replay && response.status === 401 && !request.signal.aborted
        && response.headers.get('content-type')?.includes('application/json')) {
        let detail: unknown;
        let input: unknown;
        try {
          detail = (await response.clone().json())?.detail;
          input = await replay.clone().json();
        } catch { /* Non-contract errors are returned unchanged. */ }
        const rejection = detail as Record<string, unknown> | undefined;
        const submission = input as { request_key?: unknown; analysis_content?: { include_notion?: unknown } } | undefined;
        if (rejection?.error_code === 'ACCESS_TOKEN_REQUIRED' && rejection.outcome_unknown === false
          && rejection.creation_committed !== true && rejection.task_id === undefined
          && typeof submission?.request_key === 'string' && submission.request_key.length > 0
          && submission.analysis_content?.include_notion === true) {
          const renewed = await traceAuthentication(() => apiAuthorization(replay, boundary, admin));
          // This is a definite rejection before any task write, using the same
          // handle, bytes and idempotency key. No other operation is retried.
          return await forwardBackendRequest(replay, origin, renewed, transport);
        }
      }
      if (replay?.body) void replay.body.cancel().catch(() => {});
      return response;
    } catch (error) {
      return bffFailure(error instanceof BffBoundaryError ? error : new BffBoundaryError('BFF_BACKEND_UNAVAILABLE', 502));
    }
  });
}

export async function proxyApiRequest(request: Request): Promise<Response> {
  try {
    const origin = configuredBackendOrigin();
    if (!origin) throw new BffBoundaryError('BFF_BACKEND_NOT_CONFIGURED', 503);
    const { boundary, admin } = configuredApiCredentials(request);
    // Explicit Web/native Bearer verification belongs to Python; only legacy handles
    // require the private Admin service transport/configuration here.
    return await createApiProxy(boundary, admin, origin)(request);
  } catch (error) { return traceApiRequest(request, async () => bffFailure(error)); }
}
