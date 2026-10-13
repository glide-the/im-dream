// [Input] Same-origin browser logout with the exact handle-bound CSRF token.
// [Output] Admin handle revocation followed by cookie clearing on success.
// [Pos] Sole Dream browser logout BFF; unavailable revocation retains recovery context.
// [Sync] 2026-10-11: select the existing BFF boundary from this request address.
// [Sync] 2026-09-14: delegate to the sole private BFF handler.
import { bffFailure, configuredBffHandlers } from '../../api/_auth/handlers';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export async function POST(request: Request): Promise<Response> {
  try { return await configuredBffHandlers(request).logout(request); } catch (error) { return bffFailure(error); }
}
