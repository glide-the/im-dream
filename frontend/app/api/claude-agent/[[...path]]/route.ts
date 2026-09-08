// [Input] Standard same-origin Claude Agent requests handled by the private streaming proxy.
// [Output] Thin Next App Router delegation for all supported HTTP methods.
// [Pos] Public /api/claude-agent Route Handler; Python remains the API owner.
// [Sync] 2026-09-07: keep only Next-supported route exports and delegate streaming unchanged.

import { proxyClaudeAgentRequest } from '../_proxy';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET(request: Request): Promise<Response> {
  return proxyClaudeAgentRequest(request);
}

export function HEAD(request: Request): Promise<Response> {
  return proxyClaudeAgentRequest(request);
}

export function POST(request: Request): Promise<Response> {
  return proxyClaudeAgentRequest(request);
}

export function PUT(request: Request): Promise<Response> {
  return proxyClaudeAgentRequest(request);
}

export function PATCH(request: Request): Promise<Response> {
  return proxyClaudeAgentRequest(request);
}

export function DELETE(request: Request): Promise<Response> {
  return proxyClaudeAgentRequest(request);
}

export function OPTIONS(request: Request): Promise<Response> {
  return proxyClaudeAgentRequest(request);
}
