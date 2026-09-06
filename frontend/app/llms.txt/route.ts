// [Input] A public llms.txt request and the runtime-configured Python backend origin.
// [Output] The backend-owned dynamic AI-discovery guidance without SPA fallback.
// [Pos] Canonical root App Router handler for /llms.txt.
// [Sync] 2026-09-05: preserve the Python crawler-resource owner after the Vite default exit.

import { proxyPublicResource } from '../_public-resource-proxy';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET(request: Request) {
  return proxyPublicResource('/llms.txt', request);
}
