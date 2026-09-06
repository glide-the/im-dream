// [Input] A public sitemap.xml request and the runtime-configured Python backend origin.
// [Output] The backend-owned dynamic XML sitemap without SPA fallback.
// [Pos] Canonical root App Router handler for /sitemap.xml.
// [Sync] 2026-09-05: preserve the Python crawler-resource owner after the Vite default exit.

import { proxyPublicResource } from '../_public-resource-proxy';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET(request: Request) {
  return proxyPublicResource('/sitemap.xml', request);
}
