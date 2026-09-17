// [Input] Standard same-origin MCP GET/POST/DELETE requests and opaque serverRef path selector.
// [Output] Delegation to the process-scoped, revalidating policy/manifest-governed Node runtime.
// [Pos] Next App Router MCP Apps HTTP boundary.
// [Sync] 2026-09-06: retain the thin Node route for hardened Phase 1 and governed Phase 2/3.
// [Sync] 2026-09-14: BFF resolves Browser handle/CSRF before existing Runtime authorization.

import {
  handleMcpAppsDelete,
  handleMcpAppsGet,
  handleMcpAppsPost,
} from '@ink-dream/mcp-apps-runtime';
import { authorizeRuntimeRequest } from '../../_auth/runtime-request';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type RouteContext = { params: Promise<{ serverRef: string }> };

export async function GET(request: Request, context: RouteContext) {
  const authorized = await authorizeRuntimeRequest(request);
  if (authorized instanceof Response) return authorized;
  return handleMcpAppsGet(authorized, (await context.params).serverRef);
}

export async function POST(request: Request, context: RouteContext) {
  const authorized = await authorizeRuntimeRequest(request);
  if (authorized instanceof Response) return authorized;
  return handleMcpAppsPost(authorized, (await context.params).serverRef);
}

export async function DELETE(request: Request, context: RouteContext) {
  const authorized = await authorizeRuntimeRequest(request);
  if (authorized instanceof Response) return authorized;
  return handleMcpAppsDelete(authorized, (await context.params).serverRef);
}
