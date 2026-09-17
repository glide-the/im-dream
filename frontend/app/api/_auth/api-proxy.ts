// [Input] Public API requests with opaque Browser handle or explicit native OAuth Bearer.
// [Output] Credential-selected, origin-checked, cache-free Python HTTP/SSE responses.
// [Pos] BFF API authentication owner; Python verifies every Admin access token/principal.
// [Sync] 2026-09-17: reuse the process-owned Admin client instead of exchanging a service token per API request.
import { randomUUID } from 'node:crypto';
import { configuredBackendOrigin, forwardBackendRequest } from '../_http-proxy.ts';
import { AdminBffClient, configuredAdminBffClient } from './admin-client.ts';
import { BffBoundaryError, BffLoginBoundary } from './login-boundary.ts';
import { bffFailure } from './handlers.ts';

export async function apiAuthorization(request: Request, boundary: BffLoginBoundary, admin: Pick<AdminBffClient, 'resolve'>): Promise<string> {
  boundary.requireRequestOrigin(request);
  const origin = request.headers.get('origin');
  if (origin !== null && origin !== boundary.publicOrigin) throw new BffBoundaryError('BFF_ORIGIN_DENIED', 403);
  if (boundary.hasHandleCookie(request)) {
    const readOnly = ['GET', 'HEAD', 'OPTIONS'].includes(request.method.toUpperCase());
    const handle = readOnly ? boundary.readHandle(request) : boundary.requireMutation(request);
    const resolved = await admin.resolve(handle, randomUUID(), request.signal);
    return 'Bearer ' + resolved.access_token;
  }
  const authorization = request.headers.get('authorization');
  if (!authorization || !/^Bearer [A-Za-z0-9._~-]+$/.test(authorization)) throw new BffBoundaryError('BFF_SESSION_REQUIRED', 401);
  return authorization;
}

export function configuredApiCredentials() {
  const boundary = BffLoginBoundary.fromEnvironment();
  const admin = configuredAdminBffClient();
  return { boundary, admin };
}

export function createApiProxy(boundary: BffLoginBoundary, admin: Pick<AdminBffClient, 'resolve'>, origin: URL, transport: typeof fetch = fetch) {
  return async (request: Request): Promise<Response> => {
    try {
      const incoming = new URL(request.url);
      if (!incoming.pathname.startsWith('/api/') && incoming.pathname !== '/api' && incoming.pathname !== '/auth/me') throw new BffBoundaryError('BFF_API_PATH_INVALID', 400);
      if (incoming.searchParams.has('token') || incoming.searchParams.has('access_token')) throw new BffBoundaryError('BFF_TOKEN_QUERY_DENIED', 400);
      const authorization = await apiAuthorization(request, boundary, admin);
      return await forwardBackendRequest(request, origin, authorization, transport);
    } catch (error) {
      return bffFailure(error instanceof BffBoundaryError ? error : new BffBoundaryError('BFF_BACKEND_UNAVAILABLE', 502));
    }
  };
}

export async function proxyApiRequest(request: Request): Promise<Response> {
  try {
    const origin = configuredBackendOrigin();
    if (!origin) throw new BffBoundaryError('BFF_BACKEND_NOT_CONFIGURED', 503);
    const { boundary, admin } = configuredApiCredentials();
    // Explicit native Bearer verification belongs to Python; only Browser handles
    // require the private Admin service transport/configuration here.
    return await createApiProxy(boundary, admin, origin)(request);
  } catch (error) { return bffFailure(error); }
}
