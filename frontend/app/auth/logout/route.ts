// [Sync] 2026-11-19: Web authentication uses explicit OAuth credentials while native retains its platform contract.
// [Input] Web JSON refresh credential or native handle-bound CSRF logout.
// [Output] Admin refresh revocation for Web or success-only native handle Cookie clearing.
// [Pos] Sole Dream browser logout BFF; unavailable revocation retains recovery context.
// [Sync] 2026-10-11: select the existing BFF boundary from this request address.
// [Sync] 2026-09-14: delegate to the sole private BFF handler.
import { bffFailure, configuredBffHandlers } from '../../api/_auth/handlers';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export async function POST(request: Request): Promise<Response> {
  try { return await configuredBffHandlers(request).logout(request); } catch (error) { return bffFailure(error); }
}
