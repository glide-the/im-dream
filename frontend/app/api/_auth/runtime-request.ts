// [Sync] 2026-11-19: Web authentication uses explicit OAuth credentials while native retains its platform contract.
// [Input] Web/native Bearer MCP Apps requests or native handles and opaque selectors.
// [Output] Cookie-free Request carrying the selected Admin Bearer and original Runtime selectors.
// [Pos] Explicit Node Apps BFF adapter; existing Runtime continues to validate policy/ownership.
// [Sync] 2026-10-11: preserve the per-request browser origin through the original Apps adapter.
// [Sync] 2026-09-14: share API session/CSRF precedence without exposing server credentials to Browser.
import { apiAuthorization, configuredApiCredentials } from './api-proxy.ts';
import { forwardRequestHeaders } from '../_http-proxy.ts';
import { BffBoundaryError, BffLoginBoundary } from './login-boundary.ts';
import { AdminBffClient } from './admin-client.ts';
import { bffFailure } from './handlers.ts';

export async function runtimeRequest(request: Request, boundary: BffLoginBoundary, admin: Pick<AdminBffClient, 'resolve'>): Promise<Request> {
  if (['token', 'access_token', 'refresh_token', 'id_token'].some(name => new URL(request.url).searchParams.has(name))) throw new BffBoundaryError('BFF_TOKEN_QUERY_DENIED', 400);
  const authorization = await apiAuthorization(request, boundary, admin);
  const headers = forwardRequestHeaders(request, authorization);
  // These are opaque Runtime selectors, never user/service identity assertions.
  // Existing Node/Python policy boundaries validate the selected ownership.
  for (const name of ['x-ink-mcp-apps-browser-session', 'x-ink-workspace-scope']) {
    const value = request.headers.get(name); if (value !== null) headers.set(name, value);
  }
  const init: RequestInit & { duplex?: 'half' } = { method: request.method, headers, signal: request.signal, redirect: 'manual' };
  if (!['GET', 'HEAD'].includes(request.method) && request.body !== null) { init.body = request.body; init.duplex = 'half'; }
  return new Request(request.url, init);
}

export async function authorizeRuntimeRequest(request: Request): Promise<Request | Response> {
  try { const { boundary, admin } = configuredApiCredentials(request); return await runtimeRequest(request, boundary, admin); }
  catch (error) { return bffFailure(error); }
}
