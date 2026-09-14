// [Input] Same-origin Claude Agent HTTP/SSE requests and server-owned BFF configuration.
// [Output] Authenticated, cache-free, abort-aware forwarding without buffering the response body.
// [Pos] Existing private Claude Agent proxy import boundary; Python remains the business API owner.
// [Sync] 2026-09-14: reuse the generic BFF credential owner and extracted original stream transport.
import { proxyApiRequest } from '../_auth/api-proxy.ts';
import { bffFailure } from '../_auth/handlers.ts';
import { BffBoundaryError } from '../_auth/login-boundary.ts';

export async function proxyClaudeAgentRequest(request: Request): Promise<Response> {
  const pathname = new URL(request.url).pathname;
  if (pathname !== '/api/claude-agent' && !pathname.startsWith('/api/claude-agent/')) {
    return bffFailure(new BffBoundaryError('BFF_API_PATH_INVALID', 400));
  }
  return proxyApiRequest(request);
}
