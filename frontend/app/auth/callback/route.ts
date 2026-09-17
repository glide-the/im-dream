// [Input] Exact registered Admin code callback and the original encrypted login transaction.
// [Output] Opaque handle cookie and relative return; unknown exchanges preserve transaction recovery.
// [Pos] Public same-origin OAuth callback, with tokens restricted to the Admin/server boundary.
// [Sync] 2026-09-14: delegate to the sole private BFF handler.
import { bffFailure, configuredBffHandlers } from '../../api/_auth/handlers';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export async function GET(request: Request): Promise<Response> {
  try { return await configuredBffHandlers().callback(request); } catch (error) { return bffFailure(error); }
}
