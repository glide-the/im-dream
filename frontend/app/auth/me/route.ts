// [Sync] 2026-11-19: Web authentication uses explicit OAuth credentials while native retains its platform contract.
// [Input] Existing public profile alias with Web/native OAuth Bearer or native handle.
// [Output] Existing Python-owned profile DTO through the shared authenticated BFF proxy.
// [Pos] Next /auth/me alias; no token authority or database access.
// [Sync] 2026-09-14: preserve the public alias after removing generic auth rewrites.
import { proxyApiRequest } from '../../api/_auth/api-proxy';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const GET = proxyApiRequest;
