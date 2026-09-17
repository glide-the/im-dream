// [Input] Existing public profile alias with Browser session or explicit OAuth Bearer.
// [Output] Existing Python-owned profile DTO through the shared authenticated BFF proxy.
// [Pos] Next /auth/me alias; no token authority or database access.
// [Sync] 2026-09-14: preserve the public alias after removing generic auth rewrites.
import { proxyApiRequest } from '../../api/_auth/api-proxy';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const GET = proxyApiRequest;
