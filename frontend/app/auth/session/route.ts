// [Input] Host-only opaque Dream browser handle.
// [Output] Strict public user fields and handle-bound CSRF; no OAuth credentials.
// [Pos] Browser auth-state hydration endpoint using Admin resolve/profile APIs.
// [Sync] 2026-10-11: select the existing BFF boundary from this request address.
// [Sync] 2026-09-14: preserve canonical IDs as decimal strings in this new session DTO.
import { bffFailure, configuredBffHandlers } from '../../api/_auth/handlers';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export async function GET(request: Request): Promise<Response> {
  try { return await configuredBffHandlers(request).session(request); } catch (error) { return bffFailure(error); }
}
